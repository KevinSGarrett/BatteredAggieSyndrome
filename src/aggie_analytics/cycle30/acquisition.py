"""Atomic acquisition states and contest-scoped terminal status.

Neighborhood-string Final detection is not terminal proof. Literal
upstream_success=True is not admission evidence.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from aggie_analytics.cycle30.hashing import sha256_json
from aggie_analytics.cycle30.temporal import TemporalError, parse_aware_utc

TRANSPORT_CAPTURED = "TRANSPORT_CAPTURED"
UPSTREAM_SUCCESS = "UPSTREAM_SUCCESS"
UPSTREAM_FAILED = "UPSTREAM_FAILED"
HTTP_CAPTURED_SEMANTIC_NOT_AVAILABLE = "HTTP_CAPTURED_SEMANTIC_NOT_AVAILABLE"
OFFICIAL_CONTEST_IDENTIFIED = "OFFICIAL_CONTEST_IDENTIFIED"
TERMINAL_STATUS_ESTABLISHED = "TERMINAL_STATUS_ESTABLISHED"
SCORE_ADMITTED = "SCORE_ADMITTED"
GENERIC_ERROR_HTML = "GENERIC_ERROR_HTML"
BOX_SCORE_NOT_AVAILABLE = "BOX_SCORE_NOT_AVAILABLE"
NOT_TERMINAL = "NOT_TERMINAL"

REDACTED = "***REDACTED***"
SECRET_HEADER_NAMES = {
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "api-key",
}

_FINAL_TOKEN = re.compile(r"\bfinal\b", re.IGNORECASE)
_STATUS_NODE = re.compile(
    r"""(?:id|data-contest-id|data-game-id)\s*=\s*["'](?:livestream_status_|contest-status-|game-status-)?(?P<id>[^"']+)["'][^>]*>(?P<body>[^<]+)""",
    re.IGNORECASE,
)


class AcquisitionError(ValueError):
    """Raised when acquisition or official-final admission fails closed."""


def redact_headers(headers: Mapping[str, Any] | None) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in dict(headers or {}).items():
        name = str(key)
        if name.lower() in SECRET_HEADER_NAMES:
            redacted[name] = REDACTED
        else:
            redacted[name] = str(value)
    return redacted


def request_identity(
    *,
    method: str,
    uri: str,
    parameters: Mapping[str, Any] | None = None,
    headers: Mapping[str, Any] | None = None,
    source_contract: str,
) -> str:
    payload = {
        "headers_redacted": redact_headers(headers),
        "method": str(method).upper(),
        "parameters": dict(parameters or {}),
        "source_contract": str(source_contract),
        "uri": str(uri),
    }
    return sha256_json(payload)


def reject_volatile_request_identity(identity_fields: Mapping[str, Any]) -> None:
    forbidden = {"pid", "process_id", "wall_clock", "now_utc", "uuid", "random"}
    present = {str(key).lower() for key in identity_fields}
    overlap = present.intersection(forbidden)
    if overlap:
        raise AcquisitionError(
            f"request identity must not include volatile fields: {sorted(overlap)}"
        )


def receipt_identity(
    *,
    request_identity_sha256: str,
    start_utc: str,
    end_utc: str,
    time_authority: str,
    raw_sha256: str,
) -> str:
    parse_aware_utc(start_utc)
    parse_aware_utc(end_utc)
    return sha256_json(
        {
            "end_utc": end_utc,
            "raw_sha256": raw_sha256,
            "request_identity_sha256": request_identity_sha256,
            "start_utc": start_utc,
            "time_authority": time_authority,
        }
    )


def classify_transport_and_upstream(
    *,
    http_status: int | None,
    upstream_status: int | None,
    body: bytes,
) -> dict[str, str | bool]:
    transport = (
        TRANSPORT_CAPTURED if body or http_status is not None else "TRANSPORT_MISSING"
    )
    upstream = UPSTREAM_SUCCESS
    if upstream_status is None:
        upstream = "UPSTREAM_STATUS_MISSING"
    elif int(upstream_status) < 200 or int(upstream_status) >= 300:
        upstream = UPSTREAM_FAILED
    if http_status is not None and (int(http_status) < 200 or int(http_status) >= 300):
        upstream = UPSTREAM_FAILED
    return {
        "transport_state": transport,
        "upstream_state": upstream,
        "nonempty_error_is_not_success": True,
    }


def classify_semantic_page(body: bytes | str, *, content_type: str = "") -> str:
    text = (
        body.decode("utf-8", errors="replace") if isinstance(body, bytes) else str(body)
    )
    lowered = text.lower()
    if "box score not available" in lowered:
        return HTTP_CAPTURED_SEMANTIC_NOT_AVAILABLE
    if _generic_error_html(lowered, content_type):
        return GENERIC_ERROR_HTML
    if "<html" in lowered and "contest" not in lowered and "score" not in lowered:
        return HTTP_CAPTURED_SEMANTIC_NOT_AVAILABLE
    if not text.strip():
        return HTTP_CAPTURED_SEMANTIC_NOT_AVAILABLE
    return "SEMANTIC_PAGE_AVAILABLE"


def _generic_error_html(lowered: str, content_type: str) -> bool:
    if "text/html" in content_type.lower() or "<html" in lowered:
        markers = (
            "internal server error",
            "503 service unavailable",
            "404 not found",
            "access denied",
            "an error occurred",
        )
        return any(marker in lowered for marker in markers)
    return False


def require_upstream_success(classification: Mapping[str, Any]) -> None:
    if classification.get("upstream_state") != UPSTREAM_SUCCESS:
        raise AcquisitionError("non-2xx upstream response is not official evidence")
    if classification.get("semantic_state") in {
        GENERIC_ERROR_HTML,
        HTTP_CAPTURED_SEMANTIC_NOT_AVAILABLE,
        BOX_SCORE_NOT_AVAILABLE,
    }:
        raise AcquisitionError(
            "generic or empty semantic shell is not contest evidence"
        )


def bind_actual_upstream(
    *,
    http_status: int | None,
    upstream_status: int | None,
    body: bytes,
    semantic_state: str | None = None,
) -> dict[str, Any]:
    """Bind observed transport/upstream evidence. No literal success injection."""

    classification = classify_transport_and_upstream(
        http_status=http_status, upstream_status=upstream_status, body=body
    )
    semantic = semantic_state or classify_semantic_page(body)
    classification["semantic_state"] = semantic
    if classification["upstream_state"] != UPSTREAM_SUCCESS:
        raise AcquisitionError(
            "final admission requires actual upstream 2xx evidence, "
            "not a literal upstream_success=True"
        )
    if semantic in {
        GENERIC_ERROR_HTML,
        HTTP_CAPTURED_SEMANTIC_NOT_AVAILABLE,
        BOX_SCORE_NOT_AVAILABLE,
    }:
        raise AcquisitionError("semantic failure cannot admit a final")
    return classification


def contest_scoped_terminal(
    *,
    page_text: str,
    contest_id: str,
    contest_hint: str,
    score_element_ids: Sequence[str],
    ordered_participant_ids: Sequence[str],
    page_url: str,
    embedded_contest_id: str,
) -> str:
    if str(contest_hint) != str(contest_id):
        raise AcquisitionError("contest hint/page mismatch")
    if str(embedded_contest_id) != str(contest_id):
        raise AcquisitionError("embedded contest ID does not match target contest")
    if contest_id not in page_url and contest_id not in page_text:
        raise AcquisitionError("page/URL hint does not bind the contest")
    if len(ordered_participant_ids) != 2:
        raise AcquisitionError(
            "ordered participant IDs must contain exactly two identities"
        )
    if not score_element_ids:
        raise AcquisitionError("score element IDs are required")
    matched: list[str] = []
    for match in _STATUS_NODE.finditer(page_text):
        if match.group("id") == str(contest_id) and _FINAL_TOKEN.search(
            match.group("body")
        ):
            matched.append(match.group("body").strip())
    if matched:
        return TERMINAL_STATUS_ESTABLISHED
    scoped = re.search(
        rf"livestream_status_{re.escape(contest_id)}\s+livestream_status\s+"
        rf"livestream_game_over\s*\">\s*([^<]+)",
        page_text,
        re.I,
    )
    if scoped and _FINAL_TOKEN.search(scoped.group(1)):
        return TERMINAL_STATUS_ESTABLISHED
    if _FINAL_TOKEN.search(page_text):
        return NOT_TERMINAL
    return NOT_TERMINAL


_NCAA_COM_CONTEST = re.compile(
    r'"contestId":(?P<contest_id>\d+),"url":"(?P<url>[^"]*)",'
    r'"gameState":"(?P<game_state>[^"]*)","statusCodeDisplay":"(?P<status>[^"]*)"'
    r".{0,4000}?"
    r'"teams":\[(?P<t1>\{.*?\}),(?P<t2>\{.*?\})\]',
    re.S,
)
_NCAA_COM_IS_HOME = re.compile(r'"isHome"\s*:\s*(true|false)')
_NCAA_COM_SEO = re.compile(r'"seoname"\s*:\s*"([^"]+)"')
_NCAA_COM_NAME = re.compile(r'"nameShort"\s*:\s*"([^"]+)"')
_NCAA_COM_SCORE = re.compile(r'"score"\s*:\s*(\d+)')


def _ncaa_com_team(blob: str) -> dict[str, Any] | None:
    is_home = _NCAA_COM_IS_HOME.search(blob or "")
    name = _NCAA_COM_NAME.search(blob or "")
    score = _NCAA_COM_SCORE.search(blob or "")
    seo = _NCAA_COM_SEO.search(blob or "")
    if is_home is None or name is None or score is None:
        return None
    return {
        "is_home": is_home.group(1) == "true",
        "seoname": seo.group(1) if seo else "",
        "name_short": name.group(1),
        "score": int(score.group(1)),
    }


def parse_ncaa_com_scoreboard_contests(page_text: str) -> list[dict[str, Any]]:
    """Contest-scoped NCAA.com scoreboard objects. Neighborhood Final is not used."""

    contests: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in _NCAA_COM_CONTEST.finditer(page_text or ""):
        contest_id = match.group("contest_id")
        if contest_id in seen:
            continue
        seen.add(contest_id)
        home = away = None
        for blob in (match.group("t1"), match.group("t2")):
            team = _ncaa_com_team(blob)
            if team is None:
                home = away = None
                break
            if team["is_home"]:
                home = team
            else:
                away = team
        if home is None or away is None:
            continue
        status = str(match.group("status") or "").strip().casefold()
        state = str(match.group("game_state") or "").strip().upper()
        terminal = (
            TERMINAL_STATUS_ESTABLISHED
            if state == "F" and status == "final"
            else NOT_TERMINAL
        )
        contests.append(
            {
                "ncaa_com_contest_id": contest_id,
                "url": match.group("url").replace("\\/", "/"),
                "game_state": state,
                "status_code_display": match.group("status"),
                "home_name": home["name_short"],
                "away_name": away["name_short"],
                "home_seoname": home["seoname"],
                "away_seoname": away["seoname"],
                "home_points": home["score"],
                "away_points": away["score"],
                "terminal_state": terminal,
                "source": "NCAA_COM_SCOREBOARD",
                "not_stats_ncaa_org": True,
                "artifact_class": "REAL_EVIDENCE",
            }
        )
    return contests


def match_ncaa_com_contest(
    contests: Sequence[Mapping[str, Any]],
    *,
    home_names: Sequence[str],
    away_names: Sequence[str],
) -> dict[str, Any] | None:
    home_keys = {str(item).casefold().rstrip(".") for item in home_names}
    away_keys = {str(item).casefold().rstrip(".") for item in away_names}
    for row in contests:
        home = str(row.get("home_name") or "").casefold().rstrip(".")
        away = str(row.get("away_name") or "").casefold().rstrip(".")
        home_seo = str(row.get("home_seoname") or "").casefold()
        away_seo = str(row.get("away_seoname") or "").casefold()
        if (home in home_keys or home_seo in home_keys) and (
            away in away_keys or away_seo in away_keys
        ):
            return dict(row)
    return None


def bind_participants(
    *,
    canonical_home_id: str,
    canonical_away_id: str,
    ordered_participant_ids: Sequence[str],
    displayed_home_name: str,
    displayed_away_name: str,
    name_only: bool,
) -> dict[str, str]:
    if name_only:
        raise AcquisitionError("name-only final join is not identity authority")
    if not canonical_home_id or not canonical_away_id:
        raise AcquisitionError("canonical team identities are required")
    if canonical_home_id == canonical_away_id:
        raise AcquisitionError("home and away canonical IDs cannot be identical")
    ordered = [str(item) for item in ordered_participant_ids]
    if set(ordered) != {canonical_home_id, canonical_away_id}:
        raise AcquisitionError("score-element/team mismatch")
    if ordered[0] != canonical_home_id or ordered[1] != canonical_away_id:
        raise AcquisitionError("home/away swap or orientation mismatch")
    return {
        "home_canonical_id": canonical_home_id,
        "away_canonical_id": canonical_away_id,
        "home_display_name": displayed_home_name,
        "away_display_name": displayed_away_name,
        "display_names_are_not_canonical": "true",
    }


def reuse_existing_capture(
    *,
    candidates: Sequence[Mapping[str, Any]],
    required_request_identity: str,
    required_raw_hash: str,
    required_receipt_identity: str,
    required_semantic_state: str,
    declared_freshness: str,
) -> Mapping[str, Any]:
    if not candidates:
        raise AcquisitionError(
            "no existing capture; last-receipt fallback is forbidden"
        )
    matches = [
        row
        for row in candidates
        if row.get("request_identity_sha256") == required_request_identity
        and row.get("raw_sha256") == required_raw_hash
        and row.get("receipt_identity") == required_receipt_identity
        and row.get("semantic_state") == required_semantic_state
        and row.get("declared_freshness") == declared_freshness
    ]
    if not matches:
        raise AcquisitionError(
            "existing-capture reuse requires matching request, raw hash, receipt, "
            "semantic state, and freshness; arbitrary glob/first-file is forbidden"
        )
    if len(matches) != 1:
        raise AcquisitionError("multiple matching captures; do not pick arbitrarily")
    return matches[0]


def cutoff_span_truth(
    *,
    request_start_utc: str,
    request_end_utc: str,
    cutoff_utc: str,
) -> dict[str, Any]:
    start = parse_aware_utc(request_start_utc)
    end = parse_aware_utc(request_end_utc)
    cutoff = parse_aware_utc(cutoff_utc)
    if start > end:
        raise TemporalError("request end precedes request start")
    spanned = start <= cutoff < end
    wholly_known = end <= cutoff
    return {
        "start_before_cutoff": start <= cutoff,
        "end_after_cutoff": end > cutoff,
        "spanned_cutoff": spanned,
        "wholly_known_at_cutoff": wholly_known,
        "claim": (
            "ENDED_AT_OR_BEFORE_CUTOFF"
            if wholly_known
            else (
                "START_BEFORE_CUTOFF_END_AFTER_CUTOFF"
                if spanned
                else "STARTED_AFTER_CUTOFF"
            )
        ),
    }


def reject_wholly_known_without_proof(truth: Mapping[str, Any], claimed: bool) -> None:
    if claimed and not truth.get("wholly_known_at_cutoff"):
        raise AcquisitionError(
            "acquisition spanning the cutoff cannot be labeled wholly known at cutoff"
        )

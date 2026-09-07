"""Acquire remaining Week 1 official pages with Cycle 29 request identity.

Does not rewrite frozen forecasts. Does not backfill missed checkpoints.
Late captures are classified truthfully and are not relabeled as on-time.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle29.acquisition import (  # noqa: E402
    classify_semantic_page,
    classify_transport_and_upstream,
    contest_scoped_terminal,
    cutoff_span_truth,
    receipt_identity,
    request_identity,
)
from aggie_analytics.cycle29.hashing import sha256_bytes  # noqa: E402
from aggie_analytics.cycle29.scoring import admit_official_final  # noqa: E402
from aggie_analytics.scientific_reference.ncaa_scoreboard_cards import (  # noqa: E402
    reconstruct_box_score_header,
    reconstruct_scoreboard_cards,
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
DATA = Path(
    os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
)
OUT = DATA / "ops" / "cycle29_work" / "outputs"
RAW = DATA / "raw" / "CYCLE29"
ART = ROOT / "artifacts" / "scientific_integrity" / "cycle29"

TARGETS = (
    {
        "target_id": "ncaa_scoreboard_2026_09_06",
        "uri": (
            "https://stats.ncaa.org/contests/livestream_scoreboards"
            "?utf8=%E2%9C%93&sport_code=MFB&academic_year=2027&division=1"
            "&game_date=09%2F06%2F2026"
        ),
        "source_contract": "NCAA_LIVESTREAM_SCOREBOARD_2026_09_06",
        "ncaa_contest_id": None,
        "purpose": "official_ncaa_scoreboard",
    },
    {
        "target_id": "ncaa_scoreboard_2026_09_07",
        "uri": (
            "https://stats.ncaa.org/contests/livestream_scoreboards"
            "?utf8=%E2%9C%93&sport_code=MFB&academic_year=2027&division=1"
            "&game_date=09%2F07%2F2026"
        ),
        "source_contract": "NCAA_LIVESTREAM_SCOREBOARD_2026_09_07",
        "ncaa_contest_id": None,
        "purpose": "official_ncaa_scoreboard",
    },
    {
        "target_id": "ncaa_contest_6602874",
        "uri": "https://stats.ncaa.org/contests/6602874/box_score",
        "source_contract": "NCAA_CONTEST_BOX_6602874",
        "ncaa_contest_id": "6602874",
        "purpose": "official_ncaa_box_or_status",
    },
    {
        "target_id": "ncaa_contest_6620581",
        "uri": "https://stats.ncaa.org/contests/6620581/box_score",
        "source_contract": "NCAA_CONTEST_BOX_6620581",
        "ncaa_contest_id": "6620581",
        "purpose": "official_ncaa_box_or_status",
    },
    {
        "target_id": "ncaa_contest_6594400",
        "uri": "https://stats.ncaa.org/contests/6594400/box_score",
        "source_contract": "NCAA_CONTEST_BOX_6594400",
        "ncaa_contest_id": "6594400",
        "purpose": "official_ncaa_box_or_status",
    },
)

REMAINING = {
    "6602874": {
        "matchup": "Notre Dame vs Wisconsin at Lambeau Field",
        "kickoff_utc": "2026-09-06T23:30:00Z",
        "canonical_home_id": "NCAA_TEAM:622260",
        "canonical_away_id": "NCAA_TEAM:622206",
        "displayed_home_name": "Wisconsin",
        "displayed_away_name": "Notre Dame",
        "scoreboard_home_id": "622260",
        "scoreboard_away_id": "622206",
    },
    "6620581": {
        "matchup": "Louisville vs Ole Miss at Nissan Stadium",
        "kickoff_utc": "2026-09-06T23:30:00Z",
        "canonical_home_id": "NCAA_TEAM:622192",
        "canonical_away_id": "NCAA_TEAM:622313",
        "displayed_home_name": "Ole Miss",
        "displayed_away_name": "Louisville",
        "scoreboard_home_id": "622192",
        "scoreboard_away_id": "622313",
    },
    "6594400": {
        "matchup": "SMU at Florida State",
        "kickoff_utc": "2026-09-07T23:30:00Z",
        "canonical_home_id": "NCAA_TEAM:622295",
        "canonical_away_id": "NCAA_TEAM:622228",
        "displayed_home_name": "Florida St.",
        "displayed_away_name": "SMU",
        "scoreboard_home_id": "622295",
        "scoreboard_away_id": "622228",
        "t90m_cutoff_utc": "2026-09-07T22:00:00Z",
    },
}


def pending_contest_ids() -> set[str]:
    path = ART / "CYCLE29_REMAINING_WEEK1_OFFICIAL_FINAL_SUCCESSOR.json"
    if not path.is_file():
        return set(REMAINING)
    payload = json.loads(path.read_text(encoding="utf-8"))
    pending: set[str] = set()
    for row in payload.get("contests", []):
        if row.get("state") != "SCORED_OFFICIAL_FINAL_ATOMIC_RECEIPT":
            pending.add(str(row.get("ncaa_contest_id")))
    return pending or set(REMAINING)


def capture_reusable_for_target(target: dict[str, Any], pending: set[str]) -> bool:
    contest_id = target.get("ncaa_contest_id")
    if contest_id and str(contest_id) in pending:
        return False
    if target.get("purpose") == "official_ncaa_scoreboard":
        date_pending = {
            "ncaa_scoreboard_2026_09_06": {"6602874", "6620581"},
            "ncaa_scoreboard_2026_09_07": {"6594400"},
        }
        needed = date_pending.get(str(target["target_id"]), set())
        if needed.intersection(pending):
            return False
    return True


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_env(env_path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not env_path.is_file():
        return env
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def scrapfly_token() -> str:
    env = load_env(Path(r"C:\BatteredAggieSyndrome\.env"))
    return (
        env.get("SCRAPFLY_API_TOKEN")
        or env.get("SCRAPFLY_API_KEY")
        or os.environ.get("SCRAPFLY_API_TOKEN")
        or os.environ.get("SCRAPFLY_API_KEY")
        or ""
    )


def fetch_direct(uri: str) -> tuple[bytes | None, int | None, str, str]:
    request = urllib.request.Request(uri, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read(), int(response.status), "SUCCESS", "direct_http"
    except urllib.error.HTTPError as exc:
        body = exc.read() if exc.fp else b""
        return body or None, int(exc.code), f"HTTP_{exc.code}", "direct_http"
    except Exception as exc:  # noqa: BLE001
        return None, None, f"ERROR_{type(exc).__name__}", "direct_http"


def fetch_scrapfly(uri: str, token: str) -> tuple[bytes | None, int | None, str, str]:
    parameters = {
        "key": token,
        "url": uri,
        "render_js": "true",
        "asp": "true",
        "country": "us",
    }
    endpoint = "https://api.scrapfly.io/scrape?" + urllib.parse.urlencode(parameters)
    request = urllib.request.Request(endpoint, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            payload = json.loads(response.read().decode("utf-8", "replace"))
    except Exception as exc:  # noqa: BLE001
        return None, None, f"TRANSPORT_ERROR_{type(exc).__name__}", "scrapfly_rendering"
    result = payload.get("result", {})
    status = int(result.get("status_code") or 0)
    content = result.get("content")
    if not content:
        return (
            None,
            status or None,
            f"NO_CONTENT_UPSTREAM_{status}",
            "scrapfly_rendering",
        )
    body = content.encode("utf-8") if isinstance(content, str) else content
    return body, status or 200, "SUCCESS", "scrapfly_rendering"


def find_receipt_for_raw(
    target_id: str, raw_hash: str, request_identity_sha256: str
) -> dict[str, Any] | None:
    root = DATA / "receipts" / "CYCLE29" / target_id
    if not root.is_dir():
        return None
    matches: list[dict[str, Any]] = []
    for path in root.glob("*/source_acquisition_receipt.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            str(payload.get("raw_sha256")) == raw_hash
            and str(payload.get("request_identity_sha256")) == request_identity_sha256
            and str(payload.get("target_id")) == target_id
        ):
            matches.append(payload)
    if not matches:
        return None
    matches.sort(key=lambda row: str(row.get("acquisition_started_at_utc") or ""))
    return matches[0]


def acquire_one(target: dict[str, Any], pending: set[str]) -> dict[str, Any]:
    started = utc_now()
    req_id = request_identity(
        method="GET",
        uri=str(target["uri"]),
        parameters={},
        headers={"User-Agent": USER_AGENT},
        source_contract=str(target["source_contract"]),
    )
    dest_dir = RAW / str(target["target_id"])
    dest_dir.mkdir(parents=True, exist_ok=True)
    reused_receipt: dict[str, Any] | None = None
    reusable: list[tuple[Path, dict[str, Any], bytes]] = []
    for path in dest_dir.glob("*.html"):
        raw = path.read_bytes()
        rec = find_receipt_for_raw(str(target["target_id"]), sha256_bytes(raw), req_id)
        if rec is not None:
            reusable.append((path, rec, raw))
    token = scrapfly_token()
    token_present = bool(token)
    allow_reuse = capture_reusable_for_target(target, pending)
    if reusable and allow_reuse:
        reusable.sort(
            key=lambda item: (
                0 if item[1].get("semantic_state") == "SEMANTIC_PAGE_AVAILABLE" else 1,
                0 if item[1].get("condition") == "SUCCESS" else 1,
                str(item[1].get("acquisition_started_at_utc") or ""),
            )
        )
        _path, reused_receipt, body = reusable[0]
        status = reused_receipt.get("network_response_status")
        condition = str(reused_receipt.get("condition") or "REUSED_EXISTING_CAPTURE")
        route = str(reused_receipt.get("route_id") or "existing_cycle29_raw_hash_bound")
        started = str(reused_receipt["acquisition_started_at_utc"])
        ended = str(reused_receipt["acquisition_ended_at_utc"])
    else:
        body, status, condition, route = fetch_direct(str(target["uri"]))
        if (body is None or condition != "SUCCESS" or (status or 0) >= 300) and token:
            time.sleep(0.5)
            body, status, condition, route = fetch_scrapfly(str(target["uri"]), token)
        ended = utc_now()
    payload = body or b""
    raw_hash = sha256_bytes(payload) if payload else None
    transport = classify_transport_and_upstream(
        http_status=status,
        upstream_status=status,
        body=payload,
    )
    semantic = classify_semantic_page(payload, content_type="text/html")
    rec_id = None
    if raw_hash and reused_receipt is not None:
        rec_id = str(reused_receipt["receipt_identity"])
        if str(reused_receipt.get("semantic_state")) != semantic:
            raise SystemExit("existing capture semantic state does not match rehash")
    elif raw_hash:
        rec_id = receipt_identity(
            request_identity_sha256=req_id,
            start_utc=started,
            end_utc=ended,
            time_authority="UTC_SYSTEM_CLOCK_RECEIPT",
            raw_sha256=raw_hash,
        )
        dest = RAW / str(target["target_id"])
        dest.mkdir(parents=True, exist_ok=True)
        (dest / f"{raw_hash}.html").write_bytes(payload)
        receipt_dir = DATA / "receipts" / "CYCLE29" / str(target["target_id"]) / rec_id
        receipt_dir.mkdir(parents=True, exist_ok=True)
        receipt = {
            "receipt_kind": "SOURCE_ACQUISITION_RECEIPT",
            "request_identity_sha256": req_id,
            "receipt_identity": rec_id,
            "raw_sha256": raw_hash,
            "source_uri": target["uri"],
            "network_response_status": status,
            "acquisition_started_at_utc": started,
            "acquisition_ended_at_utc": ended,
            "transport_state": transport["transport_state"],
            "upstream_state": transport["upstream_state"],
            "semantic_state": semantic,
            "volatile_pid_time_not_in_request_identity": True,
            "target_id": target["target_id"],
            "ncaa_contest_id": target.get("ncaa_contest_id"),
            "condition": condition,
            "route_id": route,
            "transport_is_not_result_authority": route == "scrapfly_rendering",
            "scrapfly_token_present": token_present,
        }
        (receipt_dir / "source_acquisition_receipt.json").write_bytes(
            (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
        )
    return {
        "target_id": target["target_id"],
        "condition": condition,
        "http_status": status,
        "request_identity_sha256": req_id,
        "receipt_identity": rec_id,
        "raw_sha256": raw_hash,
        "started_at_utc": started,
        "ended_at_utc": ended,
        "transport_state": transport["transport_state"],
        "upstream_state": transport["upstream_state"],
        "semantic_state": semantic,
        "bytes": len(payload),
        "route_id": route,
        "transport_is_not_result_authority": route == "scrapfly_rendering",
        "scrapfly_token_present": token_present,
        "body": payload,
    }


def card_for(cards: list[dict[str, Any]], contest_id: str) -> dict[str, Any] | None:
    for card in cards:
        if str(card.get("ncaa_contest_id")) == contest_id:
            return card
    return None


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    now = utc_now()
    pending = pending_contest_ids()
    acquisitions = [acquire_one(target, pending) for target in TARGETS]
    by_id = {row["target_id"]: row for row in acquisitions}
    sep6 = by_id["ncaa_scoreboard_2026_09_06"]
    sep7 = by_id["ncaa_scoreboard_2026_09_07"]
    cards6 = (
        reconstruct_scoreboard_cards(sep6["body"].decode("utf-8", "replace"))
        if sep6.get("body")
        else []
    )
    cards7 = (
        reconstruct_scoreboard_cards(sep7["body"].decode("utf-8", "replace"))
        if sep7.get("body")
        else []
    )
    contests: list[dict[str, Any]] = []
    for contest_id, meta in REMAINING.items():
        box = by_id[f"ncaa_contest_{contest_id}"]
        page = (sep7["body"] if contest_id == "6594400" else sep6["body"]).decode(
            "utf-8", "replace"
        )
        cards = cards7 if contest_id == "6594400" else cards6
        card = card_for(cards, contest_id)
        box_header = reconstruct_box_score_header(
            box["body"].decode("utf-8", "replace") if box.get("body") else "",
            contest_id,
        )
        terminal_state = "NOT_TERMINAL"
        admitted = None
        blocker = None
        try:
            if card is None:
                raise ValueError("contest card absent from official scoreboard")
            canonical_home = str(meta["canonical_home_id"])
            canonical_away = str(meta["canonical_away_id"])
            card_home = f"NCAA_TEAM:{card['home_source_team_id']}"
            card_away = f"NCAA_TEAM:{card['away_source_team_id']}"
            if {card_home, card_away} != {canonical_home, canonical_away}:
                raise ValueError("scoreboard team IDs do not match contest authority")
            points_by_id = {
                card_home: int(card["home_points"])
                if card.get("home_points") is not None
                else None,
                card_away: int(card["away_points"])
                if card.get("away_points") is not None
                else None,
            }
            home_id = canonical_home
            away_id = canonical_away
            score_ids = [
                str(card.get("home_source_team_id")),
                str(card.get("away_source_team_id")),
            ]
            terminal_state = contest_scoped_terminal(
                page_text=page,
                contest_id=contest_id,
                contest_hint=contest_id,
                score_element_ids=score_ids,
                ordered_participant_ids=[home_id, away_id],
                page_url=str(
                    sep7["target_id"] if contest_id == "6594400" else sep6["target_id"]
                ),
                embedded_contest_id=contest_id,
            )
            if terminal_state == "TERMINAL_STATUS_ESTABLISHED" and card.get(
                "final_status_is_terminal"
            ):
                home_points = points_by_id[home_id]
                away_points = points_by_id[away_id]
                if home_points is None or away_points is None:
                    raise ValueError("terminal card missing bound points")
                admitted = admit_official_final(
                    page_text=page,
                    contest_id=contest_id,
                    contest_hint=contest_id,
                    score_element_ids=score_ids,
                    ordered_participant_ids=[home_id, away_id],
                    page_url=str(contest_id),
                    embedded_contest_id=contest_id,
                    canonical_home_id=home_id,
                    canonical_away_id=away_id,
                    displayed_home_name=str(meta.get("displayed_home_name") or ""),
                    displayed_away_name=str(meta.get("displayed_away_name") or ""),
                    name_only=False,
                    home_points=int(home_points),
                    away_points=int(away_points),
                    kickoff_utc=str(meta["kickoff_utc"]),
                    retrieval_utc=str(
                        sep7["ended_at_utc"]
                        if contest_id == "6594400"
                        else sep6["ended_at_utc"]
                    ),
                    upstream_ok=True,
                )
        except Exception as exc:  # noqa: BLE001
            blocker = f"{type(exc).__name__}:{exc}"
        state = "AWAITING_OFFICIAL_FINAL"
        if admitted:
            state = "SCORED_OFFICIAL_FINAL_ATOMIC_RECEIPT"
        elif (
            card is None
            and box.get("semantic_state") == "HTTP_CAPTURED_SEMANTIC_NOT_AVAILABLE"
        ):
            state = "HTTP_CAPTURED_SEMANTIC_NOT_AVAILABLE"
        row = {
            "ncaa_contest_id": contest_id,
            "matchup": meta["matchup"],
            "kickoff_utc": meta["kickoff_utc"],
            "state": state,
            "terminal_state": terminal_state,
            "scoreboard_card": {
                "present": card is not None,
                "final_status_is_terminal": None
                if card is None
                else card.get("final_status_is_terminal"),
                "final_status_text": None
                if card is None
                else card.get("final_status_text"),
                "home_points": None if card is None else card.get("home_points"),
                "away_points": None if card is None else card.get("away_points"),
                "home_source_team_id": None
                if card is None
                else card.get("home_source_team_id"),
                "away_source_team_id": None
                if card is None
                else card.get("away_source_team_id"),
                "home_source_team_name": None
                if card is None
                else card.get("home_source_team_name"),
                "away_source_team_name": None
                if card is None
                else card.get("away_source_team_name"),
            },
            "box_header": {
                "parse_state": box_header.get("parse_state"),
                "final_status_is_terminal": box_header.get("final_status_is_terminal"),
                "final_status_text": box_header.get("final_status_text"),
                "home_points": box_header.get("home_points"),
                "away_points": box_header.get("away_points"),
            },
            "display_names_are_not_canonical": True,
            "admitted_score": admitted,
            "blocker": blocker,
            "tuning": False,
            "backfill": False,
            "forecast_rewritten": False,
        }
        if contest_id == "6594400":
            span = cutoff_span_truth(
                request_start_utc=str(sep7["started_at_utc"]),
                request_end_utc=str(sep7["ended_at_utc"]),
                cutoff_utc="2026-09-07T22:00:00Z",
            )
            row["t90m_cutoff_span"] = span
            row["t90m_disposition"] = (
                "LATE_POST_CUTOFF_EVIDENCE_NOT_RELABELED"
                if not span["wholly_known_at_cutoff"]
                else "EVIDENCE_CAPTURED_AT_OR_BEFORE_CUTOFF"
            )
            if datetime.now(timezone.utc) < datetime.fromisoformat(
                "2026-09-07T23:30:00+00:00"
            ):
                row["state"] = "AWAITING_OFFICIAL_FINAL"
                row["pre_kickoff"] = True
        contests.append(row)
    payload = {
        "artifact_type": "CYCLE29_REMAINING_WEEK1_OFFICIAL_FINAL_SUCCESSOR",
        "issued_at_utc": now,
        "operator_hold": "ACTIVE",
        "trusted_forecasts": False,
        "acquisitions": [
            {k: v for k, v in row.items() if k != "body"} for row in acquisitions
        ],
        "contests": contests,
        "no_backfill": True,
        "no_tuning": True,
        "predecessor_forecasts_preserved": True,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    (OUT / "CYCLE29_REMAINING_WEEK1_OFFICIAL_FINAL_SUCCESSOR.json").write_text(
        body, encoding="utf-8", newline="\n"
    )
    (ART / "CYCLE29_REMAINING_WEEK1_OFFICIAL_FINAL_SUCCESSOR.json").write_bytes(
        body.encode("utf-8")
    )
    print(
        json.dumps(
            {
                "ok": True,
                "contests": [(c["ncaa_contest_id"], c["state"]) for c in contests],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

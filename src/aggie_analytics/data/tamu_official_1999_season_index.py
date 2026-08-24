"""Official SRC-014 1999 Texas A&M season-index capture and box-URL discovery (BAT-630)."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urljoin, urlsplit

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash
from aggie_analytics.data.tamu_official_historical_archive import (
    ANCHOR_RE,
    CELL_RE,
    ROW_RE,
    TABLE_RE,
    AuthorityViolation,
    classify_capture,
    compact_capture,
    direct_http_get,
    fragment_text,
    persist_capture,
    sha256_file,
    validate_official_url,
)
from aggie_analytics.data.tamu_official_historical_coverage_inventory import (
    is_box_score_url,
    parse_box_score_urls,
    parse_history_index_seasons,
    parse_season_stat_urls,
    resolve_official_href,
)


SCHEMA_VERSION = "aggie.data.tamu_official_1999_season_index.v1"
CONTRACT_RELATIVE = "configs/tamu_official_1999_season_index_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_1999_season_index_gate.json"
EVIDENCE_RELATIVE = (
    "artifacts/jira_evidence/POST-TASK-SRC014-1999-OFFICIAL-INDEX-001.json"
)
CONTRACT_ID = "BAT-630-TAMU-OFFICIAL-1999-SEASON-INDEX-V1"
DECISION_UNIT = "POST-TASK-SRC014-1999-OFFICIAL-INDEX-001"
JIRA_KEY = "BAT-630"
SOURCE_ID = "SRC-014"
SEASON = 1999
DISCOVERY_PARENT_URL = "https://files.12thman.com/history/football/history/index.html"
OFFICIAL_SEASON_INDEX_URL = "https://files.12thman.com/history/football/years/1999.html"
PINNED_INVENTORY_IDENTITY = (
    "d39d35ff7cfacf2e39a524d0f1fdb97072158c50f84225ed8413771140efaa37"
)
PINNED_HISTORY_INDEX_SHA256 = (
    "1d3b44c95af913e94548a22e7eeef930fb485a472de362ca1f9c137fb759a17a"
)
PINNED_REGISTRY_SHA256 = (
    "6b90ef6fb09abd89d7a82a8b5835b00615671a7742839269c7401a2d0af5f764"
)
PINNED_BAT621_GATE_IDENTITY = (
    "24b3dd8e800c74885899af1c479cc9c15457eeb6d93b2ab0772825d856f68094"
)
PINNED_BAT621_PAYLOAD_IDENTITY = (
    "e04f7d3e3700729d63d805be95e934aa211f9233e2c69d234b95691d63a8ab6a"
)
PINNED_BAT625_GATE_IDENTITY = (
    "38cf419510306d17c203a660051f96da9e186e275833bb763a517cf735b07546"
)
PINNED_BAT625_PAYLOAD_IDENTITY = (
    "37257a291547283225fac0f9771607557a789d65f40d64ba7b2fefecfbb0a616"
)
HISTORY_INDEX_RELATIVE = (
    "raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive/"
    f"history_index/sha256_{PINNED_HISTORY_INDEX_SHA256}.html"
)
INVENTORY_GATE_RELATIVE = (
    "artifacts/data_lake/tamu_official_historical_coverage_inventory_gate.json"
)
BAT621_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2001_season_index_gate.json"
BAT625_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2000_season_index_gate.json"
MODULE_RELATIVE = "src/aggie_analytics/data/tamu_official_1999_season_index.py"
CODE_BUNDLE_RELATIVE = (MODULE_RELATIVE,)

PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_1999_SEASON_INDEX_CAPTURE_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_1999_SEASON_INDEX_CAPTURED_BOX_URLS_DISCOVERED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PAYLOAD_ROOT = "features/tamu_official_1999_season_index/sha256"
HEADER_ALIASES = {
    "date": "date",
    "opponent": "opponent",
    "opponent_event": "opponent",
    "location": "location",
    "result": "result",
    "result_box_score": "result",
    "result_boxscore": "result",
    "box_score": "box_score",
    "boxscore": "box_score",
    "recap": "recap",
}
BOX_LABEL_RE = re.compile(r"^box\s*score$", re.IGNORECASE)
YEAR_RE = re.compile(r"(?:18|19|20)\d{2}")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def expected_authority() -> dict[str, bool]:
    return {
        "availability_claim": False,
        "bas_or_aggie_excess_claims": False,
        "champion_or_production_promotion": False,
        "completeness_claim": False,
        "contest_id_fabrication": False,
        "guessed_season_url": False,
        "historical_known_at_from_capture_time": False,
        "historical_pit_admission": False,
        "membership_as_availability": False,
        "ncaa_contest_identity": False,
        "participation_as_availability": False,
        "protected_outcome_authority": False,
        "tamu_specialization_lift_claims": False,
        "union_admission": False,
        "wmt_payload_mutated_in_place": False,
    }


def expected_scientific_nonclaims() -> dict[str, bool]:
    return {
        "champion_or_production_promotion": False,
        "completeness_claimed": False,
        "games_admitted_to_union": False,
        "guessed_year_urls": False,
        "historical_known_at_established": False,
        "historical_population_ready": False,
        "ncaa_contest_ids_created": False,
        "numeric_ncaa_contest_id_sweep": False,
        "pregame_availability_admitted": False,
        "protected_lane_opened": False,
        "retrieval_time_used_as_historical_known_at": False,
    }


def expected_admissions() -> dict[str, str]:
    return {
        "bat_401": "DONE_VERIFIED_RETAIN_PROTECTED_LANE_BLOCKED",
        "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
        "bat_523": "IN_PROGRESS",
        "bat_585_inventory": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_621_2001_index": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_625_2000_index": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "gap_005": "OPEN",
        "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "ncaa_contest_identity": "NOT_CREATED",
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "source_authority": "SRC-014_OFFICIAL_SCHOOL_EVIDENCE",
        "union_admission": "NOT_ADMITTED",
    }


def discover_official_1999_url(data_root: Path) -> dict[str, Any]:
    history_path = data_root / HISTORY_INDEX_RELATIVE
    if not history_path.is_file():
        raise AuthorityViolation("verified official history index capture is missing")
    digest = sha256_file(history_path)
    if digest != PINNED_HISTORY_INDEX_SHA256:
        raise AuthorityViolation(
            "official history index hash changed; refusing guessed 1999 URL"
        )
    seasons = parse_history_index_seasons(
        history_path.read_bytes(), DISCOVERY_PARENT_URL
    )
    match = next((item for item in seasons if int(item["season"]) == SEASON), None)
    if match is None:
        raise AuthorityViolation(
            "official history index did not emit a 1999 Results link"
        )
    url = validate_official_url(str(match["official_index_url"]))
    years = {int(item) for item in YEAR_RE.findall(urlsplit(url).path)}
    if years != {SEASON}:
        raise AuthorityViolation(
            f"official 1999 URL path years {years} are not exactly {{{SEASON}}}"
        )
    if not match.get("url_directly_emitted_by_official_page"):
        raise AuthorityViolation(
            "1999 URL was not directly emitted by the official history index"
        )
    return {
        "official_index_url": url,
        "discovery": match,
        "history_index_sha256": digest,
    }


def assert_official_1999_url(url: str, expected_url: str) -> str:
    validated = validate_official_url(url)
    if validated != expected_url:
        raise AuthorityViolation(
            f"refusing non-official or guessed 1999 URL: {validated}"
        )
    years = {int(item) for item in YEAR_RE.findall(urlsplit(validated).path)}
    if years != {SEASON}:
        raise AuthorityViolation(
            f"official 1999 URL path years {years} are not exactly {{{SEASON}}}"
        )
    return validated


def compute_code_identity(repo_root: Path) -> str:
    hasher = hashlib.sha256()
    hasher.update(b"aggie.season_index.code_bundle.v1\n")
    for relative in CODE_BUNDLE_RELATIVE:
        path = repo_root / relative
        if not path.is_file():
            raise AuthorityViolation(f"code bundle member missing: {relative}")
        hasher.update(b"PATH:")
        hasher.update(relative.replace("\\", "/").encode("utf-8"))
        hasher.update(b"\n")
        hasher.update(path.read_bytes())
        hasher.update(b"\n")
    return hasher.hexdigest()


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    mutable = {key: value for key, value in gate.items() if key != "gate_identity"}
    return hashlib.sha256(
        json.dumps(
            mutable,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def compute_capture_identity(capture: Mapping[str, Any]) -> str:
    return stable_hash(
        {
            "historical_publication_time": capture.get("historical_publication_time"),
            "parent_url": capture.get("parent_url"),
            "parser_disposition": capture.get("parser_disposition"),
            "raw_byte_count": capture.get("raw_byte_count"),
            "raw_sha256": capture.get("raw_sha256"),
            "source_season": capture.get("source_season"),
            "temporal_authority": capture.get("temporal_authority"),
            "url": capture.get("url"),
        }
    )


def compute_box_url_identity(urls: list[str]) -> str:
    return stable_hash({"box_score_urls": urls})


def compute_game_row_identity(rows: list[Mapping[str, Any]]) -> str:
    return stable_hash(
        {
            "game_rows": [
                {
                    "box_score_url": row.get("box_score_url"),
                    "link_disposition": row.get("link_disposition"),
                    "ncaa_contest_id": row.get("ncaa_contest_id"),
                    "page_url": row.get("page_url"),
                    "raw_sha256": row.get("raw_sha256"),
                    "source_date": row.get("source_date"),
                    "source_location": row.get("source_location"),
                    "source_opponent": row.get("source_opponent"),
                    "source_result": row.get("source_result"),
                    "source_row_order": row.get("source_row_order"),
                }
                for row in rows
            ]
        }
    )


def _header_key(cell: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", fragment_text(cell).lower()).strip("_")
    return HEADER_ALIASES.get(normalized, normalized)


def _normalize_legacy_box_url(candidate: str) -> str | None:
    parsed = urlsplit(candidate)
    if parsed.netloc.lower() not in {"sports.tamu.edu", "www.sports.tamu.edu"}:
        return None
    prefix = "/cbs/football/stats/"
    if not parsed.path.lower().startswith(prefix):
        return None
    suffix = parsed.path[len(prefix) :].lstrip("/")
    rewritten = f"https://files.12thman.com/history/football/stats/{suffix}"
    return validate_official_url(rewritten)


def _is_legend_or_footnote_row(source_date: str, source_opponent: str) -> bool:
    date = source_date.strip()
    opponent = source_opponent.strip()
    if not date and not opponent:
        return True
    return date.startswith("@ :") or opponent.startswith("* :")


def parse_season_game_rows(
    *, body: bytes, page_url: str, raw_sha256: str
) -> dict[str, Any]:
    text = body.decode("latin-1", errors="replace")
    schedule_rows: list[str] | None = None
    headers: list[str] = []
    for table in TABLE_RE.findall(text):
        rows = ROW_RE.findall(table)
        if not rows:
            continue
        for header_idx, row in enumerate(rows):
            candidate_headers = [_header_key(cell) for cell in CELL_RE.findall(row)]
            header_set = set(candidate_headers)
            if {"date", "opponent"}.issubset(header_set) and (
                "box_score" in header_set or "result" in header_set
            ):
                headers = candidate_headers
                schedule_rows = rows[header_idx + 1 :]
                break
        if schedule_rows is not None:
            break
    if schedule_rows is None:
        raise AuthorityViolation(
            "official 1999 season index emitted no Date/Opponent/Box Score table"
        )
    admitted: list[str] = []
    seen: set[str] = set()
    game_rows: list[dict[str, Any]] = []
    emitted_urls: list[str] = []
    ambiguous_rows = 0
    duplicate_links = 0
    malformed_links = 0
    missing_links = 0
    for order, raw_row in enumerate(schedule_rows, start=1):
        cells = [fragment_text(cell) for cell in CELL_RE.findall(raw_row)]
        mapped = {
            headers[index]: cells[index] if index < len(cells) else ""
            for index in range(len(headers))
        }
        source_date = mapped.get("date", "")
        source_opponent = mapped.get("opponent", "")
        if _is_legend_or_footnote_row(source_date, source_opponent):
            ambiguous_rows += 1
            continue
        row_box_urls: list[str] = []
        row_malformed = 0
        for href, label in ANCHOR_RE.findall(raw_row):
            del label
            emitted_urls.append(urljoin(page_url, href.strip()))
            try:
                candidate = resolve_official_href(page_url, href)
            except (ValueError, AuthorityViolation):
                fallback = _normalize_legacy_box_url(urljoin(page_url, href.strip()))
                if fallback is None:
                    row_malformed += 1
                    continue
                candidate = fallback
            if not is_box_score_url(candidate):
                row_malformed += 1
                continue
            row_box_urls.append(candidate)
        link_disposition = "ADMITTED"
        box_url: str | None = None
        if row_malformed:
            malformed_links += row_malformed
            link_disposition = "MALFORMED"
        elif not row_box_urls:
            missing_links += 1
            link_disposition = "MISSING"
        else:
            first = row_box_urls[0]
            extras = row_box_urls[1:]
            if first in seen:
                duplicate_links += 1
                link_disposition = "DUPLICATE"
            else:
                seen.add(first)
                admitted.append(first)
                box_url = first
            for extra in extras:
                if extra in seen:
                    duplicate_links += 1
                else:
                    seen.add(extra)
                    admitted.append(extra)
                    duplicate_links += 1
        game_rows.append(
            {
                "box_score_url": box_url,
                "link_disposition": link_disposition,
                "ncaa_contest_id": None,
                "page_url": page_url,
                "raw_sha256": raw_sha256,
                "source_date": source_date,
                "source_location": mapped.get("location", ""),
                "source_opponent": source_opponent,
                "source_result": mapped.get("result", ""),
                "source_row_order": order,
            }
        )
    if not game_rows:
        raise AuthorityViolation("official 1999 season index emitted no game rows")
    if len(admitted) != len(set(admitted)):
        raise AuthorityViolation("duplicate admitted box URL")
    return {
        "box_score_urls": admitted,
        "counts": {
            "box_score_urls": len(admitted),
            "duplicate_links": duplicate_links,
            "games_admitted_to_union": 0,
            "ambiguous_rows": ambiguous_rows,
            "malformed_links": malformed_links,
            "missing_links": missing_links,
            "ncaa_contest_ids_created": 0,
            "scheduled_games": len(game_rows),
            "seasons_captured": 1,
        },
        "emitted_box_score_urls": emitted_urls,
        "game_rows": game_rows,
    }


def _assert_preserved_2001_index(repo_root: Path) -> None:
    bat621 = load_json(repo_root / BAT621_GATE_RELATIVE)
    if bat621.get("gate_identity") != PINNED_BAT621_GATE_IDENTITY:
        raise AuthorityViolation("BAT-621 2001 gate identity rewritten")
    if bat621.get("payload_identity") != PINNED_BAT621_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-621 2001 payload identity rewritten")


def _assert_preserved_2000_index(repo_root: Path) -> None:
    bat625 = load_json(repo_root / BAT625_GATE_RELATIVE)
    if bat625.get("gate_identity") != PINNED_BAT625_GATE_IDENTITY:
        raise AuthorityViolation("BAT-625 2000 gate identity rewritten")
    if bat625.get("payload_identity") != PINNED_BAT625_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-625 2000 payload identity rewritten")


def fetch_official_1999_season_index(data_root: Path) -> dict[str, Any]:
    discovered = discover_official_1999_url(data_root)
    url = discovered["official_index_url"]
    record = direct_http_get(url)
    body = record.pop("body")
    if int(record["status"]) != 200:
        raise AuthorityViolation(f"official 1999 season index HTTP {record['status']}")
    disposition = classify_capture(
        url, body, record.get("content_type"), int(record["status"])
    )
    if disposition != "VERIFIED_OFFICIAL_SCHOOL_PAGE":
        raise AuthorityViolation(
            f"official 1999 season index not verified: {disposition}"
        )
    return {
        **record,
        "body": body,
        "discovery": discovered,
        "historical_publication_time": None,
        "page_family": "season_index",
        "parent_url": DISCOVERY_PARENT_URL,
        "parser_disposition": disposition,
        "rights_disposition": "PRIVATE_RESEARCH_METADATA_ONLY_NONBLOCKING",
        "source_season": SEASON,
        "temporal_authority": "UNKNOWN_RETRIEVAL_TIME_ONLY",
    }


def build_objects(
    *, body: bytes, capture: Mapping[str, Any], repo_root: Path, data_root: Path
) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    inventory_gate = load_json(repo_root / INVENTORY_GATE_RELATIVE)
    if inventory_gate.get("inventory_identity") != PINNED_INVENTORY_IDENTITY:
        raise AuthorityViolation("BAT-585 inventory identity changed")
    _assert_preserved_2001_index(repo_root)
    _assert_preserved_2000_index(repo_root)
    url = assert_official_1999_url(
        str(capture.get("url") or ""), OFFICIAL_SEASON_INDEX_URL
    )
    history_path = data_root / HISTORY_INDEX_RELATIVE
    if history_path.is_file():
        discovered = discover_official_1999_url(data_root)
        if discovered["official_index_url"] != url:
            raise AuthorityViolation(
                "history index no longer emits the pinned 1999 official URL"
            )
    if capture.get("parent_url") != DISCOVERY_PARENT_URL:
        raise AuthorityViolation(
            "1999 capture parent is not the official history index"
        )
    if int(capture.get("source_season") or 0) != SEASON:
        raise AuthorityViolation("1999 capture season is not 1999")
    if capture.get("temporal_authority") != "UNKNOWN_RETRIEVAL_TIME_ONLY":
        raise AuthorityViolation("1999 capture must remain retrieval-time only")
    raw_sha256 = str(capture.get("raw_sha256") or "")
    if not raw_sha256 or len(raw_sha256) != 64:
        raise AuthorityViolation("1999 capture is missing raw SHA-256")
    parsed = parse_season_game_rows(body=body, page_url=url, raw_sha256=raw_sha256)
    page_box_urls = parse_box_score_urls(body, url)
    if page_box_urls and page_box_urls != parsed["box_score_urls"]:
        raise AuthorityViolation(
            "page-level box URLs drifted from source-ordered game rows"
        )
    try:
        season_stat_urls = parse_season_stat_urls(body, url)
    except AuthorityViolation:
        # 1999 season stat links include legacy host aliases; preserve rows without promoting those URLs.
        season_stat_urls = []
    compact = compact_capture(capture)
    compact["historical_publication_time"] = None
    compact["parent_url"] = DISCOVERY_PARENT_URL
    compact["source_season"] = SEASON
    compact["temporal_authority"] = "UNKNOWN_RETRIEVAL_TIME_ONLY"
    compact["url"] = url
    code_identity = compute_code_identity(repo_root)
    capture_identity = compute_capture_identity(compact)
    box_url_identity = compute_box_url_identity(parsed["box_score_urls"])
    game_row_identity = compute_game_row_identity(parsed["game_rows"])
    payload = {
        "artifact_type": "TAMU_OFFICIAL_1999_SEASON_INDEX_CAPTURE",
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "source_id": SOURCE_ID,
        "season": SEASON,
        "official_index_url": url,
        "discovery_parent_url": DISCOVERY_PARENT_URL,
        "history_index_sha256": PINNED_HISTORY_INDEX_SHA256,
        "inventory_identity": PINNED_INVENTORY_IDENTITY,
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "admissions": expected_admissions(),
        "capture": compact,
        "capture_identity": capture_identity,
        "box_score_urls": parsed["box_score_urls"],
        "emitted_box_score_urls": parsed["emitted_box_score_urls"],
        "box_url_identity": box_url_identity,
        "game_rows": parsed["game_rows"],
        "game_row_identity": game_row_identity,
        "counts": parsed["counts"],
        "season_stat_urls": season_stat_urls,
        "validator_code_identity": code_identity,
    }
    payload["payload_identity"] = stable_hash(
        {
            "official_index_url": url,
            "capture_identity": capture_identity,
            "box_url_identity": box_url_identity,
            "game_row_identity": game_row_identity,
            "counts": payload["counts"],
            "inventory_identity": PINNED_INVENTORY_IDENTITY,
            "validator_code_identity": code_identity,
        }
    )
    gate = {
        "artifact_type": "TAMU_OFFICIAL_1999_SEASON_INDEX_GATE",
        "schema_version": SCHEMA_VERSION,
        "classification": PASS_CLASSIFICATION,
        "result": PASS_RESULT,
        "disposition": "INDEX_CAPTURE_AND_BOX_URL_DISCOVERY_ONLY",
        "protected_lane": PROTECTED_LANE,
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "source_id": SOURCE_ID,
        "season": SEASON,
        "official_index_url": url,
        "discovery_parent_url": DISCOVERY_PARENT_URL,
        "history_index_sha256": PINNED_HISTORY_INDEX_SHA256,
        "inventory_identity": PINNED_INVENTORY_IDENTITY,
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "admissions": expected_admissions(),
        "capture": {
            "url": compact["url"],
            "response_status": compact.get("response_status") or compact.get("status"),
            "raw_relative_path": compact.get("raw_relative_path"),
            "raw_sha256": compact.get("raw_sha256"),
            "raw_byte_count": compact.get("raw_byte_count"),
            "parent_url": compact["parent_url"],
            "parser_disposition": compact.get("parser_disposition"),
            "historical_publication_time": None,
            "source_season": SEASON,
            "temporal_authority": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        },
        "capture_identity": capture_identity,
        "box_score_urls": parsed["box_score_urls"],
        "emitted_box_score_urls": parsed["emitted_box_score_urls"],
        "box_url_identity": box_url_identity,
        "game_rows": parsed["game_rows"],
        "game_row_identity": game_row_identity,
        "counts": parsed["counts"],
        "payload_identity": payload["payload_identity"],
        "validator_code_identity": code_identity,
        "upstream_identities": {
            "bat621_gate_identity": PINNED_BAT621_GATE_IDENTITY,
            "bat621_payload_identity": PINNED_BAT621_PAYLOAD_IDENTITY,
            "bat625_gate_identity": PINNED_BAT625_GATE_IDENTITY,
            "bat625_payload_identity": PINNED_BAT625_PAYLOAD_IDENTITY,
            "history_index_sha256": PINNED_HISTORY_INDEX_SHA256,
            "inventory_identity": PINNED_INVENTORY_IDENTITY,
            "protected_split_registry_sha256": PINNED_REGISTRY_SHA256,
        },
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    if contract.get("jira_key") != JIRA_KEY:
        raise AuthorityViolation("contract Jira key is not BAT-630")
    if any(row.get("ncaa_contest_id") not in {None, ""} for row in parsed["game_rows"]):
        raise AuthorityViolation("NCAA contest IDs invented")
    return {"contract": contract, "payload": payload, "gate": gate}


def materialize(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    fetched = fetch_official_1999_season_index(data_root)
    body = fetched.pop("body")
    fetched.pop("discovery", None)
    stored = persist_capture(data_root, fetched, body)
    objects = build_objects(
        body=body, capture=stored, repo_root=repo_root, data_root=data_root
    )
    payload = objects["payload"]
    gate = objects["gate"]
    payload_root = data_root / PAYLOAD_ROOT / payload["payload_identity"]
    write_json(payload_root / "payload.json", payload)
    write_json(repo_root / GATE_RELATIVE, gate)
    return {
        "gate_path": GATE_RELATIVE,
        "gate_identity": gate["gate_identity"],
        "payload_identity": payload["payload_identity"],
        "payload_path": str(payload_root / "payload.json"),
        "raw_sha256": stored["raw_sha256"],
        "scheduled_games": gate["counts"]["scheduled_games"],
        "box_score_urls": gate["box_score_urls"],
    }


def reconstruct(
    *, repo_root: Path, data_root: Path, gate: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    committed = dict(gate or load_json(repo_root / GATE_RELATIVE))
    raw_rel = (committed.get("capture") or {}).get("raw_relative_path")
    if not raw_rel:
        raise AuthorityViolation("committed 1999 gate is missing raw_relative_path")
    raw_path = data_root / raw_rel
    if not raw_path.is_file():
        raise AuthorityViolation(
            f"1999 official season index capture is missing: {raw_rel}"
        )
    digest = sha256_file(raw_path)
    expected = (committed.get("capture") or {}).get("raw_sha256")
    if digest != expected:
        raise AuthorityViolation("1999 official season index hash mismatch")
    capture = {
        "content_type": "text/html",
        "final_url": committed.get("official_index_url"),
        "historical_publication_time": None,
        "method": "GET",
        "page_family": "season_index",
        "parent_url": committed.get("discovery_parent_url"),
        "parser_disposition": (committed.get("capture") or {}).get(
            "parser_disposition"
        ),
        "raw_byte_count": raw_path.stat().st_size,
        "raw_relative_path": raw_rel,
        "raw_sha256": digest,
        "redirect_chain": [],
        "response_status": (committed.get("capture") or {}).get("response_status"),
        "rights_disposition": "PRIVATE_RESEARCH_METADATA_ONLY_NONBLOCKING",
        "source_id": SOURCE_ID,
        "source_season": SEASON,
        "status": (committed.get("capture") or {}).get("response_status"),
        "temporal_authority": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "timestamp": None,
        "url": committed.get("official_index_url"),
    }
    return build_objects(
        body=raw_path.read_bytes(),
        capture=capture,
        repo_root=repo_root,
        data_root=data_root,
    )


def validate_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    gate: Mapping[str, Any] | None = None,
    require_rebuild: bool = True,
) -> dict[str, Any]:
    committed = dict(gate or load_json(repo_root / GATE_RELATIVE))
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("official_index_url") != OFFICIAL_SEASON_INDEX_URL:
        raise AuthorityViolation("guessed or substituted 1999 official URL")
    if committed.get("history_index_sha256") != PINNED_HISTORY_INDEX_SHA256:
        raise AuthorityViolation("changed parent index")
    if committed.get("authority") != expected_authority():
        raise AuthorityViolation("authority claims drifted")
    if committed.get("scientific_nonclaims") != expected_scientific_nonclaims():
        raise AuthorityViolation("scientific nonclaims drifted")
    if committed.get("validator_code_identity") != compute_code_identity(repo_root):
        raise AuthorityViolation("changed code with stale code identity")
    if (committed.get("counts") or {}).get("ncaa_contest_ids_created") != 0:
        raise AuthorityViolation("NCAA contest IDs created")
    if (committed.get("counts") or {}).get("games_admitted_to_union") != 0:
        raise AuthorityViolation("1999 games admitted to a union")
    admitted = list(committed.get("box_score_urls") or [])
    if len(admitted) != len(set(admitted)):
        raise AuthorityViolation("duplicate admitted box URL")
    if require_rebuild:
        rebuilt = reconstruct(repo_root=repo_root, data_root=data_root, gate=committed)
        if compute_gate_identity(committed) != committed.get("gate_identity"):
            raise AuthorityViolation("committed gate identity does not recompute")
        if rebuilt["gate"]["box_score_urls"] != committed.get("box_score_urls"):
            raise AuthorityViolation("box URLs are not the official 1999 page discovery set")
        if rebuilt["gate"]["game_rows"] != committed.get("game_rows"):
            raise AuthorityViolation("game rows were inserted, removed, or reordered")
        if rebuilt["gate"]["gate_identity"] != committed.get("gate_identity"):
            raise AuthorityViolation("gate identity changed after reconstruction")
    elif compute_gate_identity(committed) != committed.get("gate_identity"):
        raise AuthorityViolation("committed gate identity does not recompute")
    return {
        "result": "PASS",
        "gate_identity": committed.get("gate_identity"),
        "payload_identity": committed.get("payload_identity"),
        "scheduled_games": (committed.get("counts") or {}).get("scheduled_games"),
    }


def lake_is_ready(data_root: Path, repo_root: Path | None = None) -> bool:
    if not (data_root / HISTORY_INDEX_RELATIVE).is_file():
        return False
    if repo_root is not None:
        gate_path = repo_root / GATE_RELATIVE
        if gate_path.is_file():
            raw_rel = (load_json(gate_path).get("capture") or {}).get("raw_relative_path")
            if raw_rel and (data_root / raw_rel).is_file():
                return True
    return False


def default_data_root() -> Path:
    return Path(
        os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
    )


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]

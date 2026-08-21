"""Official SRC-014 2001 Texas A&M season-index capture and box-URL discovery (BAT-621)."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

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


SCHEMA_VERSION = "aggie.data.tamu_official_2001_season_index.v1"
CONTRACT_RELATIVE = "configs/tamu_official_2001_season_index_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_2001_season_index_gate.json"
EVIDENCE_RELATIVE = "artifacts/jira_evidence/POST-TASK-SRC014-2001-OFFICIAL-INDEX-001.json"
CONTRACT_ID = "BAT-621-TAMU-OFFICIAL-2001-SEASON-INDEX-V1"
DECISION_UNIT = "POST-TASK-SRC014-2001-OFFICIAL-INDEX-001"
JIRA_KEY = "BAT-621"
SOURCE_ID = "SRC-014"
SEASON = 2001
DISCOVERY_PARENT_URL = "https://files.12thman.com/history/football/history/index.html"
OFFICIAL_SEASON_INDEX_URL = "https://files.12thman.com/history/football/years/2001.html"
PINNED_INVENTORY_IDENTITY = "d39d35ff7cfacf2e39a524d0f1fdb97072158c50f84225ed8413771140efaa37"
PINNED_INVENTORY_GATE_IDENTITY = "f1a5821ad081dce7058848ccc453344f0a2827030959049133b69db15689c851"
PINNED_HISTORY_INDEX_SHA256 = "1d3b44c95af913e94548a22e7eeef930fb485a472de362ca1f9c137fb759a17a"
PINNED_REGISTRY_SHA256 = "6b90ef6fb09abd89d7a82a8b5835b00615671a7742839269c7401a2d0af5f764"
PINNED_BAT588_GATE_IDENTITY = "60fc69c136332de876d511f2020ffbd08282bc4e02256e547d3bcb46222c5ea9"
PINNED_BAT588_PAYLOAD_IDENTITY = "a5abf4326d3429ba580d74d3f9d36aaa8267ea0b789af8966ab54f3b55ea792a"
PINNED_BAT594_GATE_IDENTITY = "d1f765a73abf0107fcf200562590bfd0212a521df47f9c6b27bb336ad737635c"
PINNED_BAT594_PAYLOAD_IDENTITY = "8fd30b3275af348b84c49f90e01fa0e9594c652ecccd5be75154a8e496638b3e"
PINNED_BAT599_GATE_IDENTITY = "17868efadbc5cc6ec04869d194b8b8a205089c3050b069eec3e5ba9c1d25c301"
PINNED_BAT599_PAYLOAD_IDENTITY = "71b57040514f4d61f89809fc7bd15270b993ddcd4728ba981c6f1cbdfac015cb"
PINNED_BAT604_GATE_IDENTITY = "3169f6b14e9f2e78e5af2c3dfa33419d80b37c791968fa39e0ddcf91f3643836"
PINNED_BAT604_PAYLOAD_IDENTITY = "65b6c83d9946eadc3db5fede73bed7e64b620406ca5655ad93d75346dcbe6422"
PINNED_BAT609_GATE_IDENTITY = "1a2b16c74bcfc27ba0afc83611fd817d34aa6a2a71a326fd385721b779d9411e"
PINNED_BAT609_PAYLOAD_IDENTITY = "9f58c220fe44e8c75835d0dced6dc6571ee7592249eaa6fa209fa181f25fdfa6"
HISTORY_INDEX_RELATIVE = (
    "raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive/"
    f"history_index/sha256_{PINNED_HISTORY_INDEX_SHA256}.html"
)
INVENTORY_GATE_RELATIVE = "artifacts/data_lake/tamu_official_historical_coverage_inventory_gate.json"
BAT588_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2007_season_index_gate.json"
BAT594_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2006_season_index_gate.json"
BAT599_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2005_season_index_gate.json"
BAT604_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2004_season_index_gate.json"
BAT609_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2003_season_index_gate.json"
PINNED_BAT613_GATE_IDENTITY = "07cae0a9ce32422706907fa81b9aeb428781c3f76a0ac3c27d9964613793580a"
PINNED_BAT613_PAYLOAD_IDENTITY = "71e518cabe070defa9f5a4551f22d97434a4ff1a9ba13c00159f37cbb3f6d46a"
BAT613_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2002_season_index_gate.json"
MODULE_RELATIVE = "src/aggie_analytics/data/tamu_official_2001_season_index.py"
CODE_BUNDLE_RELATIVE = (MODULE_RELATIVE,)

PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_2001_SEASON_INDEX_CAPTURE_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_2001_SEASON_INDEX_CAPTURED_BOX_URLS_DISCOVERED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PAYLOAD_ROOT = "features/tamu_official_2001_season_index/sha256"
HEADER_ALIASES = {
    "date": "date",
    "opponent": "opponent",
    "location": "location",
    "result": "result",
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
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
        "bat_588_2007_index": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_594_2006_index": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_599_2005_index": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_604_2004_index": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_609_2003_index": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_613_2002_index": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "gap_005": "OPEN",
        "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "ncaa_contest_identity": "NOT_CREATED",
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "source_authority": "SRC-014_OFFICIAL_SCHOOL_EVIDENCE",
        "union_admission": "NOT_ADMITTED",
    }


def discover_official_2001_url(data_root: Path) -> dict[str, Any]:
    history_path = data_root / HISTORY_INDEX_RELATIVE
    if not history_path.is_file():
        raise AuthorityViolation("verified official history index capture is missing")
    digest = sha256_file(history_path)
    if digest != PINNED_HISTORY_INDEX_SHA256:
        raise AuthorityViolation("official history index hash changed; refusing guessed 2001 URL")
    seasons = parse_history_index_seasons(history_path.read_bytes(), DISCOVERY_PARENT_URL)
    match = next((item for item in seasons if int(item["season"]) == SEASON), None)
    if match is None:
        raise AuthorityViolation("official history index did not emit a 2001 Results link")
    url = validate_official_url(str(match["official_index_url"]))
    years = {int(item) for item in YEAR_RE.findall(urlsplit(url).path)}
    if years != {SEASON}:
        raise AuthorityViolation(f"official 2001 URL path years {years} are not exactly {{{SEASON}}}")
    if not match.get("url_directly_emitted_by_official_page"):
        raise AuthorityViolation("2001 URL was not directly emitted by the official history index")
    return {"official_index_url": url, "discovery": match, "history_index_sha256": digest}


def assert_official_2001_url(url: str, expected_url: str) -> str:
    validated = validate_official_url(url)
    if validated != expected_url:
        raise AuthorityViolation(f"refusing non-official or guessed 2001 URL: {validated}")
    years = {int(item) for item in YEAR_RE.findall(urlsplit(validated).path)}
    if years != {SEASON}:
        raise AuthorityViolation(f"official 2001 URL path years {years} are not exactly {{{SEASON}}}")
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
        json.dumps(mutable, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
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


def parse_season_game_rows(*, body: bytes, page_url: str, raw_sha256: str) -> dict[str, Any]:
    text = body.decode("latin-1", errors="replace")
    schedule_rows: list[str] | None = None
    headers: list[str] = []
    for table in TABLE_RE.findall(text):
        rows = ROW_RE.findall(table)
        if not rows:
            continue
        candidate_headers = [_header_key(cell) for cell in CELL_RE.findall(rows[0])]
        if {"date", "opponent", "box_score"}.issubset(set(candidate_headers)):
            headers = candidate_headers
            schedule_rows = rows[1:]
            break
    if schedule_rows is None:
        raise AuthorityViolation("official 2001 season index emitted no Date/Opponent/Box Score table")
    admitted: list[str] = []
    seen: set[str] = set()
    game_rows: list[dict[str, Any]] = []
    duplicate_links = 0
    malformed_links = 0
    missing_links = 0
    for order, raw_row in enumerate(schedule_rows, start=1):
        cells = [fragment_text(cell) for cell in CELL_RE.findall(raw_row)]
        mapped = {headers[index]: cells[index] if index < len(cells) else "" for index in range(len(headers))}
        source_date = mapped.get("date", "")
        source_opponent = mapped.get("opponent", "")
        if not source_date and not source_opponent:
            continue
        row_box_urls: list[str] = []
        row_malformed = 0
        for href, label in ANCHOR_RE.findall(raw_row):
            if not BOX_LABEL_RE.match(fragment_text(label)):
                continue
            try:
                candidate = resolve_official_href(page_url, href)
            except (ValueError, AuthorityViolation):
                row_malformed += 1
                continue
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
        raise AuthorityViolation("official 2001 season index emitted no game rows")
    if len(admitted) != len(set(admitted)):
        raise AuthorityViolation("duplicate admitted box URL")
    return {
        "box_score_urls": admitted,
        "counts": {
            "box_score_urls": len(admitted),
            "duplicate_links": duplicate_links,
            "games_admitted_to_union": 0,
            "malformed_links": malformed_links,
            "missing_links": missing_links,
            "ncaa_contest_ids_created": 0,
            "scheduled_games": len(game_rows),
            "seasons_captured": 1,
        },
        "game_rows": game_rows,
    }


def fetch_official_2001_season_index(data_root: Path) -> dict[str, Any]:
    discovered = discover_official_2001_url(data_root)
    url = discovered["official_index_url"]
    record = direct_http_get(url)
    body = record.pop("body")
    if int(record["status"]) != 200:
        raise AuthorityViolation(f"official 2001 season index HTTP {record['status']}")
    disposition = classify_capture(url, body, record.get("content_type"), int(record["status"]))
    if disposition != "VERIFIED_OFFICIAL_SCHOOL_PAGE":
        raise AuthorityViolation(f"official 2001 season index not verified: {disposition}")
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






def _assert_preserved_2002_index(repo_root: Path) -> None:
    bat613 = load_json(repo_root / BAT613_GATE_RELATIVE)
    if bat613.get("gate_identity") != PINNED_BAT613_GATE_IDENTITY:
        raise AuthorityViolation("BAT-613 2002 gate identity rewritten")
    if bat613.get("payload_identity") != PINNED_BAT613_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-613 2002 payload identity rewritten")
    if bat613.get("official_index_url") != "https://files.12thman.com/history/football/years/2002.html":
        raise AuthorityViolation("BAT-613 official 2002 URL rewritten")


def _assert_preserved_2003_index(repo_root: Path) -> None:
    bat609 = load_json(repo_root / BAT609_GATE_RELATIVE)
    if bat609.get("gate_identity") != PINNED_BAT609_GATE_IDENTITY:
        raise AuthorityViolation("BAT-609 2003 gate identity rewritten")
    if bat609.get("payload_identity") != PINNED_BAT609_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-609 2003 payload identity rewritten")
    if bat609.get("official_index_url") != "https://files.12thman.com/history/football/years/2003.html":
        raise AuthorityViolation("BAT-609 official 2003 URL rewritten")


def _assert_preserved_2004_index(repo_root: Path) -> None:
    bat604 = load_json(repo_root / BAT604_GATE_RELATIVE)
    if bat604.get("gate_identity") != PINNED_BAT604_GATE_IDENTITY:
        raise AuthorityViolation("BAT-604 2004 gate identity rewritten")
    if bat604.get("payload_identity") != PINNED_BAT604_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-604 2004 payload identity rewritten")
    if bat604.get("official_index_url") != "https://files.12thman.com/history/football/years/2004.html":
        raise AuthorityViolation("BAT-604 official 2004 URL rewritten")


def _assert_preserved_2005_index(repo_root: Path) -> None:
    bat599 = load_json(repo_root / BAT599_GATE_RELATIVE)
    if bat599.get("gate_identity") != PINNED_BAT599_GATE_IDENTITY:
        raise AuthorityViolation("BAT-599 2005 gate identity rewritten")
    if bat599.get("payload_identity") != PINNED_BAT599_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-599 2005 payload identity rewritten")
    if bat599.get("official_index_url") != "https://files.12thman.com/history/football/years/2005.html":
        raise AuthorityViolation("BAT-599 official 2005 URL rewritten")


def _assert_preserved_2006_index(repo_root: Path) -> None:
    bat594 = load_json(repo_root / BAT594_GATE_RELATIVE)
    if bat594.get("gate_identity") != PINNED_BAT594_GATE_IDENTITY:
        raise AuthorityViolation("BAT-594 2006 gate identity rewritten")
    if bat594.get("payload_identity") != PINNED_BAT594_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-594 2006 payload identity rewritten")
    if bat594.get("official_index_url") != "https://files.12thman.com/history/football/years/2006.html":
        raise AuthorityViolation("BAT-594 official 2006 URL rewritten")


def _assert_preserved_2007_index(repo_root: Path) -> None:
    bat588 = load_json(repo_root / BAT588_GATE_RELATIVE)
    if bat588.get("gate_identity") != PINNED_BAT588_GATE_IDENTITY:
        raise AuthorityViolation("BAT-588 2007 gate identity rewritten")
    if bat588.get("payload_identity") != PINNED_BAT588_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-588 2007 payload identity rewritten")
    if bat588.get("official_index_url") != "https://files.12thman.com/history/football/years/2007.html":
        raise AuthorityViolation("BAT-588 official 2007 URL rewritten")


def build_objects(*, body: bytes, capture: Mapping[str, Any], repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    inventory_gate = load_json(repo_root / INVENTORY_GATE_RELATIVE)
    if inventory_gate.get("inventory_identity") != PINNED_INVENTORY_IDENTITY:
        raise AuthorityViolation("BAT-585 inventory identity changed; refusing rewrite or rebound")
    if inventory_gate.get("gate_identity") != PINNED_INVENTORY_GATE_IDENTITY:
        raise AuthorityViolation("BAT-585 inventory gate identity changed; refusing rewrite")
    _assert_preserved_2007_index(repo_root)
    _assert_preserved_2006_index(repo_root)
    _assert_preserved_2005_index(repo_root)
    _assert_preserved_2004_index(repo_root)
    _assert_preserved_2003_index(repo_root)
    _assert_preserved_2002_index(repo_root)
    url = assert_official_2001_url(str(capture.get("url") or ""), OFFICIAL_SEASON_INDEX_URL)
    history_path = data_root / HISTORY_INDEX_RELATIVE
    if history_path.is_file():
        discovered = discover_official_2001_url(data_root)
        if discovered["official_index_url"] != url:
            raise AuthorityViolation("history index no longer emits the pinned 2001 official URL")
    if capture.get("parent_url") != DISCOVERY_PARENT_URL:
        raise AuthorityViolation("2001 capture parent is not the official history index")
    if int(capture.get("source_season") or 0) != SEASON:
        raise AuthorityViolation("2001 capture season is not 2001")
    if capture.get("temporal_authority") != "UNKNOWN_RETRIEVAL_TIME_ONLY":
        raise AuthorityViolation("2001 capture must remain retrieval-time only")
    if capture.get("historical_publication_time") not in {None, ""}:
        raise AuthorityViolation("historical publication time invented from retrieval")
    if capture.get("parser_disposition") != "VERIFIED_OFFICIAL_SCHOOL_PAGE":
        raise AuthorityViolation("2001 capture is not a verified official school page")
    raw_sha256 = str(capture.get("raw_sha256") or "")
    if not raw_sha256 or len(raw_sha256) != 64:
        raise AuthorityViolation("2001 capture is missing raw SHA-256")
    parsed = parse_season_game_rows(body=body, page_url=url, raw_sha256=raw_sha256)
    page_box_urls = parse_box_score_urls(body, url)
    if page_box_urls != parsed["box_score_urls"]:
        raise AuthorityViolation("page-level box URLs drifted from source-ordered game rows")
    if not parsed["box_score_urls"]:
        raise AuthorityViolation("official 2001 season index emitted no box-score URLs")
    for box_url in parsed["box_score_urls"]:
        validate_official_url(box_url)
        if "years/2001.html" in box_url or box_url.rstrip("/").endswith("/2001.html"):
            raise AuthorityViolation("season index presented as a box-score URL")
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
        "admissions": expected_admissions(),
        "authority": expected_authority(),
        "box_score_urls": parsed["box_score_urls"],
        "box_url_identity": box_url_identity,
        "capture": compact,
        "capture_identity": capture_identity,
        "contract_id": CONTRACT_ID,
        "counts": parsed["counts"],
        "decision_unit": DECISION_UNIT,
        "discovery_parent_url": DISCOVERY_PARENT_URL,
        "game_row_identity": game_row_identity,
        "game_rows": parsed["game_rows"],
        "history_index_sha256": PINNED_HISTORY_INDEX_SHA256,
        "inventory_identity": PINNED_INVENTORY_IDENTITY,
        "jira_key": JIRA_KEY,
        "official_index_url": url,
        "schema_version": SCHEMA_VERSION,
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "season": SEASON,
        "season_stat_urls": parse_season_stat_urls(body, url),
        "source_id": SOURCE_ID,
        "artifact_type": "TAMU_OFFICIAL_2001_SEASON_INDEX_CAPTURE",
        "validator_code_identity": code_identity,
    }
    payload["payload_identity"] = stable_hash(
        {
            "box_url_identity": box_url_identity,
            "capture_identity": capture_identity,
            "counts": payload["counts"],
            "game_row_identity": game_row_identity,
            "inventory_identity": PINNED_INVENTORY_IDENTITY,
            "official_index_url": url,
            "validator_code_identity": code_identity,
        }
    )
    gate = {
        "admissions": expected_admissions(),
        "artifact_type": "TAMU_OFFICIAL_2001_SEASON_INDEX_GATE",
        "authority": expected_authority(),
        "box_score_urls": parsed["box_score_urls"],
        "box_url_identity": box_url_identity,
        "capture": {
            "historical_publication_time": None,
            "parent_url": compact["parent_url"],
            "parser_disposition": compact.get("parser_disposition"),
            "raw_byte_count": compact.get("raw_byte_count"),
            "raw_relative_path": compact.get("raw_relative_path"),
            "raw_sha256": compact.get("raw_sha256"),
            "response_status": compact.get("response_status") or compact.get("status"),
            "source_season": SEASON,
            "temporal_authority": "UNKNOWN_RETRIEVAL_TIME_ONLY",
            "url": compact["url"],
        },
        "capture_identity": capture_identity,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "counts": parsed["counts"],
        "decision_unit": DECISION_UNIT,
        "discovery_parent_url": DISCOVERY_PARENT_URL,
        "disposition": "INDEX_CAPTURE_AND_BOX_URL_DISCOVERY_ONLY",
        "game_row_identity": game_row_identity,
        "game_rows": parsed["game_rows"],
        "history_index_sha256": PINNED_HISTORY_INDEX_SHA256,
        "inventory_identity": PINNED_INVENTORY_IDENTITY,
        "jira_key": JIRA_KEY,
        "official_index_url": url,
        "payload_identity": payload["payload_identity"],
        "protected_lane": PROTECTED_LANE,
        "result": PASS_RESULT,
        "schema_version": SCHEMA_VERSION,
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "season": SEASON,
        "source_id": SOURCE_ID,
        "validator_code_identity": code_identity,
        "upstream_identities": {
            "bat588_gate_identity": PINNED_BAT588_GATE_IDENTITY,
            "bat588_payload_identity": PINNED_BAT588_PAYLOAD_IDENTITY,
            "bat594_gate_identity": PINNED_BAT594_GATE_IDENTITY,
            "bat594_payload_identity": PINNED_BAT594_PAYLOAD_IDENTITY,
            "bat599_gate_identity": PINNED_BAT599_GATE_IDENTITY,
            "bat599_payload_identity": PINNED_BAT599_PAYLOAD_IDENTITY,
            "bat604_gate_identity": PINNED_BAT604_GATE_IDENTITY,
            "bat604_payload_identity": PINNED_BAT604_PAYLOAD_IDENTITY,
            "bat609_gate_identity": PINNED_BAT609_GATE_IDENTITY,
            "bat609_payload_identity": PINNED_BAT609_PAYLOAD_IDENTITY,
            "bat613_gate_identity": PINNED_BAT613_GATE_IDENTITY,
            "bat613_payload_identity": PINNED_BAT613_PAYLOAD_IDENTITY,
            "history_index_sha256": PINNED_HISTORY_INDEX_SHA256,
            "inventory_gate_identity": PINNED_INVENTORY_GATE_IDENTITY,
            "inventory_identity": PINNED_INVENTORY_IDENTITY,
            "protected_split_registry_sha256": PINNED_REGISTRY_SHA256,
        },
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    if contract.get("jira_key") != JIRA_KEY:
        raise AuthorityViolation("contract Jira key is not BAT-621")
    if any(row.get("ncaa_contest_id") not in {None, ""} for row in parsed["game_rows"]):
        raise AuthorityViolation("NCAA contest IDs invented")
    return {"body": body, "contract": contract, "gate": gate, "payload": payload}


def materialize(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    fetched = fetch_official_2001_season_index(data_root)
    body = fetched.pop("body")
    fetched.pop("discovery", None)
    stored = persist_capture(data_root, fetched, body)
    objects = build_objects(body=body, capture=stored, repo_root=repo_root, data_root=data_root)
    payload = objects["payload"]
    gate = objects["gate"]
    payload_root = data_root / PAYLOAD_ROOT / payload["payload_identity"]
    write_json(payload_root / "payload.json", payload)
    write_json(repo_root / GATE_RELATIVE, gate)
    return {
        "box_score_urls": gate["box_score_urls"],
        "box_url_identity": gate["box_url_identity"],
        "capture_identity": gate["capture_identity"],
        "game_row_identity": gate["game_row_identity"],
        "gate_identity": gate["gate_identity"],
        "gate_path": GATE_RELATIVE,
        "payload_identity": payload["payload_identity"],
        "payload_path": str(payload_root / "payload.json"),
        "raw_sha256": stored["raw_sha256"],
        "scheduled_games": gate["counts"]["scheduled_games"],
    }


def reconstruct(*, repo_root: Path, data_root: Path, gate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    committed = dict(gate or load_json(repo_root / GATE_RELATIVE))
    raw_rel = (committed.get("capture") or {}).get("raw_relative_path")
    if not raw_rel:
        raise AuthorityViolation("committed 2001 gate is missing raw_relative_path")
    raw_path = data_root / raw_rel
    if not raw_path.is_file():
        raise AuthorityViolation(f"2001 official season index capture is missing: {raw_rel}")
    digest = sha256_file(raw_path)
    expected = (committed.get("capture") or {}).get("raw_sha256")
    if digest != expected:
        raise AuthorityViolation("2001 official season index hash mismatch")
    capture = {
        "content_type": "text/html",
        "final_url": committed.get("official_index_url"),
        "historical_publication_time": None,
        "method": "GET",
        "page_family": "season_index",
        "parent_url": committed.get("discovery_parent_url"),
        "parser_disposition": (committed.get("capture") or {}).get("parser_disposition"),
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
    return build_objects(body=raw_path.read_bytes(), capture=capture, repo_root=repo_root, data_root=data_root)


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
        raise AuthorityViolation("guessed or substituted 2001 official URL")
    if committed.get("discovery_parent_url") != DISCOVERY_PARENT_URL:
        raise AuthorityViolation("changed parent index")
    if committed.get("history_index_sha256") != PINNED_HISTORY_INDEX_SHA256:
        raise AuthorityViolation("changed parent index")
    if (committed.get("capture") or {}).get("parent_url") != DISCOVERY_PARENT_URL:
        raise AuthorityViolation("changed parent index")
    history_path = data_root / HISTORY_INDEX_RELATIVE
    if history_path.is_file():
        discovered = discover_official_2001_url(data_root)
        if discovered["official_index_url"] != OFFICIAL_SEASON_INDEX_URL:
            raise AuthorityViolation("history index no longer emits the pinned 2001 official URL")
    elif require_rebuild:
        raise AuthorityViolation("verified official history index capture is missing")
    if committed.get("inventory_identity") != PINNED_INVENTORY_IDENTITY:
        raise AuthorityViolation("BAT-585 inventory identity rewritten")
    if (committed.get("upstream_identities") or {}).get("inventory_identity") != PINNED_INVENTORY_IDENTITY:
        raise AuthorityViolation("BAT-585 inventory identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat588_gate_identity") != PINNED_BAT588_GATE_IDENTITY:
        raise AuthorityViolation("BAT-588 2007 gate identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat594_gate_identity") != PINNED_BAT594_GATE_IDENTITY:
        raise AuthorityViolation("BAT-594 2006 gate identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat594_payload_identity") != PINNED_BAT594_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-594 2006 payload identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat599_gate_identity") != PINNED_BAT599_GATE_IDENTITY:
        raise AuthorityViolation("BAT-599 2005 gate identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat599_payload_identity") != PINNED_BAT599_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-599 2005 payload identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat604_gate_identity") != PINNED_BAT604_GATE_IDENTITY:
        raise AuthorityViolation("BAT-604 2004 gate identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat604_payload_identity") != PINNED_BAT604_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-604 2004 payload identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat609_gate_identity") != PINNED_BAT609_GATE_IDENTITY:
        raise AuthorityViolation("BAT-609 2003 gate identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat609_payload_identity") != PINNED_BAT609_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-609 2003 payload identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat613_gate_identity") != PINNED_BAT613_GATE_IDENTITY:
        raise AuthorityViolation("BAT-613 2002 gate identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat613_payload_identity") != PINNED_BAT613_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-613 2002 payload identity rewritten")
    if committed.get("validator_code_identity") != compute_code_identity(repo_root):
        raise AuthorityViolation("changed code with stale code identity")
    if (committed.get("counts") or {}).get("ncaa_contest_ids_created") != 0:
        raise AuthorityViolation("NCAA contest IDs created")
    if (committed.get("counts") or {}).get("games_admitted_to_union") != 0:
        raise AuthorityViolation("2001 games admitted to a union")
    if committed.get("authority") != expected_authority():
        raise AuthorityViolation("authority claims drifted")
    if committed.get("scientific_nonclaims") != expected_scientific_nonclaims():
        raise AuthorityViolation("scientific nonclaims drifted")
    if committed.get("result") != PASS_RESULT or committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("forged completion after identity recomputation")
    admitted = list(committed.get("box_score_urls") or [])
    if len(admitted) != len(set(admitted)):
        raise AuthorityViolation("duplicate admitted box URL")
    if any(row.get("ncaa_contest_id") not in {None, ""} for row in committed.get("game_rows") or []):
        raise AuthorityViolation("NCAA contest IDs invented")
    if require_rebuild:
        rebuilt = reconstruct(repo_root=repo_root, data_root=data_root, gate=committed)
        if compute_gate_identity(committed) != committed.get("gate_identity"):
            raise AuthorityViolation("committed gate identity does not recompute")
        if rebuilt["gate"]["box_score_urls"] != committed.get("box_score_urls"):
            raise AuthorityViolation("box URLs are not the official 2001 page discovery set")
        if rebuilt["gate"]["game_rows"] != committed.get("game_rows"):
            raise AuthorityViolation("game rows were inserted, removed, or reordered")
        if rebuilt["gate"]["capture_identity"] != committed.get("capture_identity"):
            raise AuthorityViolation("capture identity changed")
        if rebuilt["gate"]["box_url_identity"] != committed.get("box_url_identity"):
            raise AuthorityViolation("box URL identity changed")
        if rebuilt["gate"]["game_row_identity"] != committed.get("game_row_identity"):
            raise AuthorityViolation("game-row identity changed")
        if rebuilt["gate"]["gate_identity"] != committed.get("gate_identity"):
            raise AuthorityViolation("gate identity changed after reconstruction")
        live_inventory = load_json(repo_root / INVENTORY_GATE_RELATIVE)
        if live_inventory.get("inventory_identity") != PINNED_INVENTORY_IDENTITY:
            raise AuthorityViolation("BAT-585 inventory identity rewritten")
        _assert_preserved_2007_index(repo_root)
        _assert_preserved_2006_index(repo_root)
        _assert_preserved_2005_index(repo_root)
        _assert_preserved_2004_index(repo_root)
        _assert_preserved_2003_index(repo_root)
        _assert_preserved_2002_index(repo_root)
    elif compute_gate_identity(committed) != committed.get("gate_identity"):
        raise AuthorityViolation("committed gate identity does not recompute")
    return {
        "box_score_url_count": (committed.get("counts") or {}).get("box_score_urls"),
        "box_url_identity": committed.get("box_url_identity"),
        "capture_identity": committed.get("capture_identity"),
        "game_row_identity": committed.get("game_row_identity"),
        "gate_identity": committed.get("gate_identity"),
        "inventory_identity": PINNED_INVENTORY_IDENTITY,
        "payload_identity": committed.get("payload_identity"),
        "result": "PASS",
        "scheduled_games": (committed.get("counts") or {}).get("scheduled_games"),
        "validator_code_identity": committed.get("validator_code_identity"),
    }


def lake_is_ready(data_root: Path, repo_root: Path | None = None) -> bool:
    if not (data_root / HISTORY_INDEX_RELATIVE).is_file():
        return False
    if repo_root is not None:
        gate_path = repo_root / GATE_RELATIVE
        if gate_path.is_file():
            gate = load_json(gate_path)
            raw_rel = (gate.get("capture") or {}).get("raw_relative_path")
            if raw_rel and (data_root / raw_rel).is_file():
                return True
    return False


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]

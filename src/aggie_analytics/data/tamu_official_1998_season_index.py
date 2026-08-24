"""Official SRC-014 1998 season-index capture and box-URL discovery (BAT-634)."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash
from aggie_analytics.data.tamu_official_1999_season_index import (
    PINNED_BAT621_GATE_IDENTITY,
    PINNED_BAT621_PAYLOAD_IDENTITY,
    PINNED_BAT625_GATE_IDENTITY,
    PINNED_BAT625_PAYLOAD_IDENTITY,
    PINNED_HISTORY_INDEX_SHA256,
    PINNED_INVENTORY_IDENTITY,
    PINNED_REGISTRY_SHA256,
    compute_capture_identity,
    compute_game_row_identity,
    parse_season_game_rows,
)
from aggie_analytics.data.tamu_official_historical_archive import (
    AuthorityViolation,
    classify_capture,
    compact_capture,
    direct_http_get,
    persist_capture,
    sha256_file,
    validate_official_url,
)
from aggie_analytics.data.tamu_official_historical_coverage_inventory import (
    parse_history_index_seasons,
    parse_season_stat_urls,
)

SCHEMA_VERSION = "aggie.data.tamu_official_1998_season_index.v1"
CONTRACT_RELATIVE = "configs/tamu_official_1998_season_index_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_1998_season_index_gate.json"
CONTRACT_ID = "BAT-634-TAMU-OFFICIAL-1998-SEASON-INDEX-V1"
DECISION_UNIT = "POST-TASK-SRC014-1998-OFFICIAL-INDEX-001"
JIRA_KEY = "BAT-634"
SOURCE_ID = "SRC-014"
SEASON = 1998
DISCOVERY_PARENT_URL = "https://files.12thman.com/history/football/history/index.html"
OFFICIAL_SEASON_INDEX_URL = "https://files.12thman.com/history/football/years/1998.html"
HISTORY_INDEX_RELATIVE = (
    "raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive/"
    f"history_index/sha256_{PINNED_HISTORY_INDEX_SHA256}.html"
)
INVENTORY_GATE_RELATIVE = (
    "artifacts/data_lake/tamu_official_historical_coverage_inventory_gate.json"
)
BAT621_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2001_season_index_gate.json"
BAT625_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2000_season_index_gate.json"
MODULE_RELATIVE = "src/aggie_analytics/data/tamu_official_1998_season_index.py"
CODE_BUNDLE_RELATIVE = (MODULE_RELATIVE,)
PAYLOAD_ROOT = "features/tamu_official_1998_season_index/sha256"
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_1998_SEASON_INDEX_CAPTURE_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_1998_SEASON_INDEX_CAPTURED_BOX_URLS_DISCOVERED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
YEAR_RE = re.compile(r"(?:18|19|20)\d{2}")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def expected_authority() -> dict[str, bool]:
    return {
        "availability_claim": False,
        "champion_or_production_promotion": False,
        "completeness_claim": False,
        "contest_id_fabrication": False,
        "guessed_season_url": False,
        "historical_known_at_from_capture_time": False,
        "historical_pit_admission": False,
        "membership_as_availability": False,
        "ncaa_contest_identity": False,
        "participation_as_availability": False,
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
        "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "ncaa_contest_identity": "NOT_CREATED",
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "source_authority": "SRC-014_OFFICIAL_SCHOOL_EVIDENCE",
        "union_admission": "NOT_ADMITTED",
    }


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


def compute_box_url_identity(urls: list[str]) -> str:
    return stable_hash({"box_score_urls": urls})


def discover_official_1998_url(data_root: Path) -> dict[str, Any]:
    history_path = data_root / HISTORY_INDEX_RELATIVE
    if not history_path.is_file():
        raise AuthorityViolation("verified official history index capture is missing")
    digest = sha256_file(history_path)
    if digest != PINNED_HISTORY_INDEX_SHA256:
        raise AuthorityViolation("official history index hash changed; refusing guessed 1998 URL")
    text = history_path.read_text(encoding="latin-1", errors="replace")
    if "../years/1998.html" not in text:
        raise AuthorityViolation("official history index did not emit ../years/1998.html")
    seasons = parse_history_index_seasons(history_path.read_bytes(), DISCOVERY_PARENT_URL)
    match = next((item for item in seasons if int(item["season"]) == SEASON), None)
    if match is None:
        raise AuthorityViolation("official history index did not emit a 1998 Results link")
    url = validate_official_url(str(match["official_index_url"]))
    years = {int(item) for item in YEAR_RE.findall(urlsplit(url).path)}
    if years != {SEASON}:
        raise AuthorityViolation(f"official 1998 URL path years {years} are not exactly {{{SEASON}}}")
    return {
        "official_index_url": url,
        "discovery": match,
        "history_index_sha256": digest,
        "history_href_proof": "../years/1998.html",
    }


def _assert_preserved_priors(repo_root: Path) -> None:
    inventory_gate = load_json(repo_root / INVENTORY_GATE_RELATIVE)
    if inventory_gate.get("inventory_identity") != PINNED_INVENTORY_IDENTITY:
        raise AuthorityViolation("BAT-585 inventory identity changed")
    bat621 = load_json(repo_root / BAT621_GATE_RELATIVE)
    if bat621.get("gate_identity") != PINNED_BAT621_GATE_IDENTITY:
        raise AuthorityViolation("BAT-621 identity rewritten")
    if bat621.get("payload_identity") != PINNED_BAT621_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-621 payload identity rewritten")
    bat625 = load_json(repo_root / BAT625_GATE_RELATIVE)
    if bat625.get("gate_identity") != PINNED_BAT625_GATE_IDENTITY:
        raise AuthorityViolation("BAT-625 identity rewritten")
    if bat625.get("payload_identity") != PINNED_BAT625_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-625 payload identity rewritten")


def fetch_official_1998_season_index(data_root: Path) -> dict[str, Any]:
    discovered = discover_official_1998_url(data_root)
    url = discovered["official_index_url"]
    record = direct_http_get(url)
    body = record.pop("body")
    if int(record["status"]) != 200:
        raise AuthorityViolation(f"official 1998 season index HTTP {record['status']}")
    disposition = classify_capture(url, body, record.get("content_type"), int(record["status"]))
    if disposition != "VERIFIED_OFFICIAL_SCHOOL_PAGE":
        raise AuthorityViolation(f"official 1998 season index not verified: {disposition}")
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


def build_objects(*, body: bytes, capture: Mapping[str, Any], repo_root: Path, data_root: Path) -> dict[str, Any]:
    _assert_preserved_priors(repo_root)
    discovered = discover_official_1998_url(data_root)
    url = validate_official_url(str(capture.get("url") or ""))
    if url != OFFICIAL_SEASON_INDEX_URL:
        raise AuthorityViolation(f"refusing non-official or guessed 1998 URL: {url}")
    if capture.get("parent_url") != DISCOVERY_PARENT_URL:
        raise AuthorityViolation("1998 capture parent is not the official history index")
    if int(capture.get("source_season") or 0) != SEASON:
        raise AuthorityViolation("1998 capture season is not 1998")
    raw_sha256 = str(capture.get("raw_sha256") or "")
    parsed = parse_season_game_rows(body=body, page_url=url, raw_sha256=raw_sha256)
    compact = compact_capture(capture)
    compact["historical_publication_time"] = None
    compact["parent_url"] = DISCOVERY_PARENT_URL
    compact["source_season"] = SEASON
    compact["temporal_authority"] = "UNKNOWN_RETRIEVAL_TIME_ONLY"
    compact["url"] = url
    code_identity = compute_code_identity(repo_root)
    try:
        season_stat_urls = parse_season_stat_urls(body, url)
    except AuthorityViolation:
        # 1998 season stat links include legacy host aliases; preserve rows without promoting those URLs.
        season_stat_urls = []
    payload = {
        "artifact_type": "TAMU_OFFICIAL_1998_SEASON_INDEX_CAPTURE",
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "source_id": SOURCE_ID,
        "season": SEASON,
        "official_index_url": url,
        "discovery_parent_url": DISCOVERY_PARENT_URL,
        "history_index_sha256": PINNED_HISTORY_INDEX_SHA256,
        "history_href_proof": discovered["history_href_proof"],
        "inventory_identity": PINNED_INVENTORY_IDENTITY,
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "admissions": expected_admissions(),
        "capture": compact,
        "capture_identity": compute_capture_identity(compact),
        "box_score_urls": parsed["box_score_urls"],
        "emitted_box_score_urls": parsed["emitted_box_score_urls"],
        "box_url_identity": compute_box_url_identity(parsed["box_score_urls"]),
        "game_rows": parsed["game_rows"],
        "game_row_identity": compute_game_row_identity(parsed["game_rows"]),
        "counts": parsed["counts"],
        "season_stat_urls": season_stat_urls,
        "validator_code_identity": code_identity,
    }
    payload["payload_identity"] = stable_hash(
        {
            "official_index_url": url,
            "capture_identity": payload["capture_identity"],
            "box_url_identity": payload["box_url_identity"],
            "game_row_identity": payload["game_row_identity"],
            "counts": payload["counts"],
            "inventory_identity": PINNED_INVENTORY_IDENTITY,
            "validator_code_identity": code_identity,
        }
    )
    gate = {
        "artifact_type": "TAMU_OFFICIAL_1998_SEASON_INDEX_GATE",
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
        "history_href_proof": discovered["history_href_proof"],
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
        "capture_identity": payload["capture_identity"],
        "box_score_urls": parsed["box_score_urls"],
        "emitted_box_score_urls": parsed["emitted_box_score_urls"],
        "box_url_identity": payload["box_url_identity"],
        "game_rows": parsed["game_rows"],
        "game_row_identity": payload["game_row_identity"],
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
    return {"payload": payload, "gate": gate}


def materialize(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    fetched = fetch_official_1998_season_index(data_root)
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
        "gate_path": GATE_RELATIVE,
        "gate_identity": gate["gate_identity"],
        "payload_identity": payload["payload_identity"],
        "payload_path": str(payload_root / "payload.json"),
        "raw_sha256": stored["raw_sha256"],
        "scheduled_games": gate["counts"]["scheduled_games"],
        "box_score_urls": gate["box_score_urls"],
    }


def reconstruct(*, repo_root: Path, data_root: Path, gate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    committed = dict(gate or load_json(repo_root / GATE_RELATIVE))
    raw_rel = (committed.get("capture") or {}).get("raw_relative_path")
    if not raw_rel:
        raise AuthorityViolation("committed 1998 gate is missing raw_relative_path")
    raw_path = data_root / raw_rel
    if not raw_path.is_file():
        raise AuthorityViolation(f"1998 official season index capture missing: {raw_rel}")
    digest = sha256_file(raw_path)
    if digest != (committed.get("capture") or {}).get("raw_sha256"):
        raise AuthorityViolation("1998 official season index hash mismatch")
    capture = {
        "content_type": "text/html",
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


def validate_artifact(*, repo_root: Path, data_root: Path, gate: Mapping[str, Any] | None = None, require_rebuild: bool = True) -> dict[str, Any]:
    committed = dict(gate or load_json(repo_root / GATE_RELATIVE))
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("official_index_url") != OFFICIAL_SEASON_INDEX_URL:
        raise AuthorityViolation("guessed or substituted 1998 official URL")
    if committed.get("history_href_proof") != "../years/1998.html":
        raise AuthorityViolation("1998 history href proof missing or changed")
    if committed.get("validator_code_identity") != compute_code_identity(repo_root):
        raise AuthorityViolation("changed code with stale code identity")
    if compute_gate_identity(committed) != committed.get("gate_identity"):
        raise AuthorityViolation("committed gate identity does not recompute")
    if require_rebuild:
        rebuilt = reconstruct(repo_root=repo_root, data_root=data_root, gate=committed)
        if rebuilt["gate"] != committed:
            raise AuthorityViolation("committed 1998 gate does not match reconstruction")
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
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))

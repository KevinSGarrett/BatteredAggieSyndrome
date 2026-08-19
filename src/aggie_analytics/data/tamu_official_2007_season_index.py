"""Official SRC-014 2007 Texas A&M season-index capture and box-URL discovery (BAT-588)."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash
from aggie_analytics.data.tamu_official_historical_archive import (
    classify_capture,
    compact_capture,
    direct_http_get,
    persist_capture,
    sha256_file,
    validate_official_url,
)
from aggie_analytics.data.tamu_official_historical_coverage_inventory import (
    parse_box_score_urls,
    parse_season_stat_urls,
)

SCHEMA_VERSION = "aggie.data.tamu_official_2007_season_index.v1"
CONTRACT_RELATIVE = "configs/tamu_official_2007_season_index_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_2007_season_index_gate.json"
EVIDENCE_RELATIVE = "artifacts/jira_evidence/POST-TASK-SRC014-2007-OFFICIAL-INDEX-001.json"
CONTRACT_ID = "BAT-588-TAMU-OFFICIAL-2007-SEASON-INDEX-V1"
DECISION_UNIT = "POST-TASK-SRC014-2007-OFFICIAL-INDEX-001"
JIRA_KEY = "BAT-588"
SOURCE_ID = "SRC-014"
SEASON = 2007
OFFICIAL_SEASON_INDEX_URL = "https://files.12thman.com/history/football/years/2007.html"
DISCOVERY_PARENT_URL = "https://files.12thman.com/history/football/history/index.html"
PINNED_INVENTORY_IDENTITY = "d39d35ff7cfacf2e39a524d0f1fdb97072158c50f84225ed8413771140efaa37"
PINNED_INVENTORY_GATE_IDENTITY = "f1a5821ad081dce7058848ccc453344f0a2827030959049133b69db15689c851"
PINNED_HISTORY_INDEX_SHA256 = "1d3b44c95af913e94548a22e7eeef930fb485a472de362ca1f9c137fb759a17a"
PINNED_REGISTRY_SHA256 = "6b90ef6fb09abd89d7a82a8b5835b00615671a7742839269c7401a2d0af5f764"
INVENTORY_GATE_RELATIVE = "artifacts/data_lake/tamu_official_historical_coverage_inventory_gate.json"
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_2007_SEASON_INDEX_CAPTURE_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_2007_SEASON_INDEX_CAPTURED_BOX_URLS_DISCOVERED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PAYLOAD_ROOT = "features/tamu_official_2007_season_index/sha256"
GATE_IDENTITY_FIELDS = (
    "schema_version",
    "artifact_type",
    "result",
    "classification",
    "contract_id",
    "decision_unit",
    "jira_key",
    "disposition",
    "source_id",
    "season",
    "official_index_url",
    "discovery_parent_url",
    "inventory_identity",
    "history_index_sha256",
    "capture_identity",
    "box_url_identity",
    "counts",
    "upstream_identities",
    "admissions",
    "authority",
    "scientific_nonclaims",
    "protected_lane",
)


class AuthorityViolation(ValueError):
    """Raised when the 2007 official-index capture would invent a URL, claim, or identity."""


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
        "gap_005": "OPEN",
        "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "ncaa_contest_identity": "NOT_CREATED",
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "source_authority": "SRC-014_OFFICIAL_SCHOOL_EVIDENCE",
        "union_admission": "NOT_ADMITTED",
    }


def assert_official_2007_url(url: str) -> str:
    validated = validate_official_url(url)
    if validated != OFFICIAL_SEASON_INDEX_URL:
        raise AuthorityViolation(f"refusing non-official or guessed 2007 URL: {validated}")
    years = {int(item) for item in __import__("re").findall(r"(?:18|19|20)\d{2}", urlsplit(validated).path)}
    if years != {SEASON}:
        raise AuthorityViolation(f"official 2007 URL path years {years} are not exactly {{{SEASON}}}")
    return validated


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    mutable = {key: value for key, value in gate.items() if key != "gate_identity"}
    return hashlib.sha256(
        json.dumps(mutable, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    ).hexdigest()


def compute_capture_identity(capture: Mapping[str, Any]) -> str:
    return stable_hash(
        {
            "url": capture.get("url"),
            "raw_sha256": capture.get("raw_sha256"),
            "raw_byte_count": capture.get("raw_byte_count"),
            "parser_disposition": capture.get("parser_disposition"),
            "parent_url": capture.get("parent_url"),
            "source_season": capture.get("source_season"),
            "temporal_authority": capture.get("temporal_authority"),
        }
    )


def compute_box_url_identity(urls: list[str]) -> str:
    return stable_hash({"box_score_urls": urls})


def fetch_official_2007_season_index() -> dict[str, Any]:
    url = assert_official_2007_url(OFFICIAL_SEASON_INDEX_URL)
    record = direct_http_get(url)
    body = record.pop("body")
    if int(record["status"]) != 200:
        raise AuthorityViolation(f"official 2007 season index HTTP {record['status']}")
    disposition = classify_capture(url, body, record.get("content_type"), int(record["status"]))
    if disposition != "VERIFIED_OFFICIAL_SCHOOL_PAGE":
        raise AuthorityViolation(f"official 2007 season index not verified: {disposition}")
    return {
        **record,
        "page_family": "season_index",
        "parent_url": DISCOVERY_PARENT_URL,
        "parser_disposition": disposition,
        "source_season": SEASON,
        "temporal_authority": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "historical_publication_time": None,
        "rights_disposition": "PRIVATE_RESEARCH_METADATA_ONLY_NONBLOCKING",
        "body": body,
    }


def build_objects(*, body: bytes, capture: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    inventory_gate = load_json(repo_root / INVENTORY_GATE_RELATIVE)
    if inventory_gate.get("inventory_identity") != PINNED_INVENTORY_IDENTITY:
        raise AuthorityViolation("BAT-585 inventory identity changed; refusing rewrite or rebound")
    if inventory_gate.get("gate_identity") != PINNED_INVENTORY_GATE_IDENTITY:
        raise AuthorityViolation("BAT-585 inventory gate identity changed; refusing rewrite")
    url = assert_official_2007_url(str(capture.get("url") or ""))
    if capture.get("parent_url") != DISCOVERY_PARENT_URL:
        raise AuthorityViolation("2007 capture parent is not the official history index")
    if int(capture.get("source_season") or 0) != SEASON:
        raise AuthorityViolation("2007 capture season is not 2007")
    if capture.get("temporal_authority") != "UNKNOWN_RETRIEVAL_TIME_ONLY":
        raise AuthorityViolation("2007 capture must remain retrieval-time only")
    if capture.get("historical_publication_time") not in {None, ""}:
        raise AuthorityViolation("historical publication time invented from retrieval")
    if capture.get("parser_disposition") != "VERIFIED_OFFICIAL_SCHOOL_PAGE":
        raise AuthorityViolation("2007 capture is not a verified official school page")
    box_urls = parse_box_score_urls(body, url)
    if not box_urls:
        raise AuthorityViolation("official 2007 season index emitted no box-score URLs")
    for box_url in box_urls:
        validate_official_url(box_url)
        if "years/2007.html" in box_url or box_url.rstrip("/").endswith("/2007.html"):
            raise AuthorityViolation("season index presented as a box-score URL")
    compact = compact_capture(capture)
    compact["url"] = url
    compact["parent_url"] = DISCOVERY_PARENT_URL
    compact["source_season"] = SEASON
    compact["temporal_authority"] = "UNKNOWN_RETRIEVAL_TIME_ONLY"
    compact["historical_publication_time"] = None
    capture_identity = compute_capture_identity(compact)
    box_url_identity = compute_box_url_identity(box_urls)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_2007_SEASON_INDEX_CAPTURE",
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "source_id": SOURCE_ID,
        "season": SEASON,
        "official_index_url": url,
        "discovery_parent_url": DISCOVERY_PARENT_URL,
        "inventory_identity": PINNED_INVENTORY_IDENTITY,
        "history_index_sha256": PINNED_HISTORY_INDEX_SHA256,
        "capture": compact,
        "capture_identity": capture_identity,
        "box_score_urls": box_urls,
        "box_url_identity": box_url_identity,
        "season_stat_urls": parse_season_stat_urls(body, url),
        "counts": {
            "box_score_urls": len(box_urls),
            "games_admitted_to_union": 0,
            "ncaa_contest_ids_created": 0,
            "seasons_captured": 1,
        },
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "admissions": expected_admissions(),
    }
    payload["payload_identity"] = stable_hash(
        {
            "capture_identity": capture_identity,
            "box_url_identity": box_url_identity,
            "official_index_url": url,
            "inventory_identity": PINNED_INVENTORY_IDENTITY,
            "counts": payload["counts"],
        }
    )
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_2007_SEASON_INDEX_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "disposition": "INDEX_CAPTURE_AND_BOX_URL_DISCOVERY_ONLY",
        "source_id": SOURCE_ID,
        "season": SEASON,
        "official_index_url": url,
        "discovery_parent_url": DISCOVERY_PARENT_URL,
        "inventory_identity": PINNED_INVENTORY_IDENTITY,
        "history_index_sha256": PINNED_HISTORY_INDEX_SHA256,
        "capture_identity": capture_identity,
        "box_url_identity": box_url_identity,
        "payload_identity": payload["payload_identity"],
        "counts": payload["counts"],
        "upstream_identities": {
            "inventory_identity": PINNED_INVENTORY_IDENTITY,
            "inventory_gate_identity": PINNED_INVENTORY_GATE_IDENTITY,
            "history_index_sha256": PINNED_HISTORY_INDEX_SHA256,
            "protected_split_registry_sha256": PINNED_REGISTRY_SHA256,
        },
        "admissions": expected_admissions(),
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "protected_lane": PROTECTED_LANE,
        "capture": {
            "url": compact["url"],
            "parent_url": compact["parent_url"],
            "raw_sha256": compact.get("raw_sha256"),
            "raw_byte_count": compact.get("raw_byte_count"),
            "raw_relative_path": compact.get("raw_relative_path"),
            "parser_disposition": compact.get("parser_disposition"),
            "response_status": compact.get("response_status") or compact.get("status"),
            "temporal_authority": "UNKNOWN_RETRIEVAL_TIME_ONLY",
            "historical_publication_time": None,
            "source_season": SEASON,
        },
        "box_score_urls": box_urls,
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    if contract.get("jira_key") != JIRA_KEY:
        raise AuthorityViolation("contract Jira key is not BAT-588")
    return {"contract": contract, "payload": payload, "gate": gate, "body": body}


def materialize(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    fetched = fetch_official_2007_season_index()
    body = fetched.pop("body")
    stored = persist_capture(data_root, fetched, body)
    objects = build_objects(body=body, capture=stored, repo_root=repo_root)
    payload = objects["payload"]
    gate = objects["gate"]
    payload_root = data_root / PAYLOAD_ROOT / payload["payload_identity"]
    write_json(payload_root / "payload.json", payload)
    write_json(repo_root / GATE_RELATIVE, gate)
    return {
        "payload_identity": payload["payload_identity"],
        "gate_identity": gate["gate_identity"],
        "capture_identity": gate["capture_identity"],
        "box_url_identity": gate["box_url_identity"],
        "raw_sha256": stored["raw_sha256"],
        "box_score_urls": gate["box_score_urls"],
        "payload_path": str(payload_root / "payload.json"),
        "gate_path": GATE_RELATIVE,
    }


def reconstruct(*, repo_root: Path, data_root: Path, gate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    committed = dict(gate or load_json(repo_root / GATE_RELATIVE))
    raw_rel = (committed.get("capture") or {}).get("raw_relative_path")
    if not raw_rel:
        raise AuthorityViolation("committed 2007 gate is missing raw_relative_path")
    raw_path = data_root / raw_rel
    if not raw_path.is_file():
        raise AuthorityViolation(f"2007 official season index capture is missing: {raw_rel}")
    digest = sha256_file(raw_path)
    expected = (committed.get("capture") or {}).get("raw_sha256")
    if digest != expected:
        raise AuthorityViolation("2007 official season index hash mismatch")
    capture = {
        "url": committed.get("official_index_url"),
        "final_url": committed.get("official_index_url"),
        "parent_url": committed.get("discovery_parent_url"),
        "page_family": "season_index",
        "parser_disposition": (committed.get("capture") or {}).get("parser_disposition"),
        "raw_sha256": digest,
        "raw_byte_count": raw_path.stat().st_size,
        "raw_relative_path": raw_rel,
        "response_status": (committed.get("capture") or {}).get("response_status"),
        "status": (committed.get("capture") or {}).get("response_status"),
        "source_season": SEASON,
        "temporal_authority": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "historical_publication_time": None,
        "rights_disposition": "PRIVATE_RESEARCH_METADATA_ONLY_NONBLOCKING",
        "timestamp": None,
        "method": "GET",
        "content_type": "text/html",
        "redirect_chain": [],
        "source_id": SOURCE_ID,
    }
    return build_objects(body=raw_path.read_bytes(), capture=capture, repo_root=repo_root)


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
        raise AuthorityViolation("guessed or substituted 2007 official URL")
    if committed.get("inventory_identity") != PINNED_INVENTORY_IDENTITY:
        raise AuthorityViolation("BAT-585 inventory identity rewritten")
    if (committed.get("upstream_identities") or {}).get("inventory_identity") != PINNED_INVENTORY_IDENTITY:
        raise AuthorityViolation("BAT-585 inventory identity rewritten")
    if (committed.get("counts") or {}).get("ncaa_contest_ids_created") != 0:
        raise AuthorityViolation("NCAA contest IDs created")
    if (committed.get("counts") or {}).get("games_admitted_to_union") != 0:
        raise AuthorityViolation("2007 games admitted to a union")
    if committed.get("authority") != expected_authority():
        raise AuthorityViolation("authority claims drifted")
    if committed.get("scientific_nonclaims") != expected_scientific_nonclaims():
        raise AuthorityViolation("scientific nonclaims drifted")
    if committed.get("result") != PASS_RESULT or committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("forged completion after identity recomputation")
    if require_rebuild:
        rebuilt = reconstruct(repo_root=repo_root, data_root=data_root, gate=committed)
        if rebuilt["gate"]["gate_identity"] != compute_gate_identity(committed) and compute_gate_identity(committed) != committed.get("gate_identity"):
            raise AuthorityViolation("committed gate identity does not recompute")
        if rebuilt["gate"]["box_score_urls"] != committed.get("box_score_urls"):
            raise AuthorityViolation("box URLs are not the official 2007 page discovery set")
        if rebuilt["gate"]["capture_identity"] != committed.get("capture_identity"):
            raise AuthorityViolation("capture identity changed")
        if rebuilt["gate"]["box_url_identity"] != committed.get("box_url_identity"):
            raise AuthorityViolation("box URL identity changed")
        if rebuilt["gate"]["gate_identity"] != committed.get("gate_identity"):
            raise AuthorityViolation("gate identity changed after reconstruction")
        live_inventory = load_json(repo_root / INVENTORY_GATE_RELATIVE)
        if live_inventory.get("inventory_identity") != PINNED_INVENTORY_IDENTITY:
            raise AuthorityViolation("BAT-585 inventory identity rewritten")
    elif compute_gate_identity(committed) != committed.get("gate_identity"):
        raise AuthorityViolation("committed gate identity does not recompute")
    return {
        "result": "PASS",
        "gate_identity": committed.get("gate_identity"),
        "payload_identity": committed.get("payload_identity"),
        "capture_identity": committed.get("capture_identity"),
        "box_url_identity": committed.get("box_url_identity"),
        "box_score_url_count": (committed.get("counts") or {}).get("box_score_urls"),
        "inventory_identity": PINNED_INVENTORY_IDENTITY,
    }


def lake_is_ready(data_root: Path, repo_root: Path | None = None) -> bool:
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




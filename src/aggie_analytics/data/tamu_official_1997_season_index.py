"""Official SRC-014 1997 season-index capture and box-URL discovery."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash
from aggie_analytics.data.tamu_official_1999_season_index import (
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
from aggie_analytics.data.tamu_official_historical_coverage_inventory import parse_history_index_seasons

SCHEMA_VERSION = "aggie.data.tamu_official_1997_season_index.v1"
CONTRACT_RELATIVE = "configs/tamu_official_1997_season_index_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_1997_season_index_gate.json"
CONTRACT_ID = "BAT-XXX-TAMU-OFFICIAL-1997-SEASON-INDEX-V1"
DECISION_UNIT = "POST-TASK-SRC014-1997-OFFICIAL-INDEX-001"
JIRA_KEY = "BAT-XXX"
SOURCE_ID = "SRC-014"
SEASON = 1997
DISCOVERY_PARENT_URL = "https://files.12thman.com/history/football/history/index.html"
OFFICIAL_SEASON_INDEX_URL = "https://files.12thman.com/history/football/years/1997.html"
HISTORY_INDEX_RELATIVE = (
    "raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive/"
    f"history_index/sha256_{PINNED_HISTORY_INDEX_SHA256}.html"
)
INVENTORY_GATE_RELATIVE = "artifacts/data_lake/tamu_official_historical_coverage_inventory_gate.json"
MODULE_RELATIVE = "src/aggie_analytics/data/tamu_official_1997_season_index.py"
CODE_BUNDLE_RELATIVE = (MODULE_RELATIVE,)
PAYLOAD_ROOT = "features/tamu_official_1997_season_index/sha256"
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_1997_SEASON_INDEX_CAPTURE_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_1997_SEASON_INDEX_CAPTURED_BOX_URLS_DISCOVERED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
HISTORY_HREF_PROOF = "../years/1997.html"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


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


def discover_official_1997_url(data_root: Path) -> dict[str, Any]:
    history_path = data_root / HISTORY_INDEX_RELATIVE
    if not history_path.is_file():
        raise AuthorityViolation("verified official history index capture is missing")
    digest = sha256_file(history_path)
    if digest != PINNED_HISTORY_INDEX_SHA256:
        raise AuthorityViolation("official history index hash changed; refusing guessed 1997 URL")
    text = history_path.read_text(encoding="latin-1", errors="replace")
    if HISTORY_HREF_PROOF not in text:
        raise AuthorityViolation("official history index did not emit ../years/1997.html")
    seasons = parse_history_index_seasons(history_path.read_bytes(), DISCOVERY_PARENT_URL)
    match = next((item for item in seasons if int(item["season"]) == SEASON), None)
    if match is None:
        raise AuthorityViolation("official history index did not emit a 1997 Results link")
    url = validate_official_url(str(match["official_index_url"]))
    if url != OFFICIAL_SEASON_INDEX_URL:
        raise AuthorityViolation("resolved official 1997 URL drifted from expected authority chain")
    return {"official_index_url": url, "history_index_sha256": digest, "history_href_proof": HISTORY_HREF_PROOF}


def fetch_official_1997_season_index(data_root: Path) -> dict[str, Any]:
    discovered = discover_official_1997_url(data_root)
    record = direct_http_get(discovered["official_index_url"])
    body = record.pop("body")
    if int(record["status"]) != 200:
        raise AuthorityViolation(f"official 1997 season index HTTP {record['status']}")
    disposition = classify_capture(discovered["official_index_url"], body, record.get("content_type"), int(record["status"]))
    if disposition != "VERIFIED_OFFICIAL_SCHOOL_PAGE":
        raise AuthorityViolation(f"official 1997 season index not verified: {disposition}")
    return {
        **record,
        "body": body,
        "historical_publication_time": None,
        "page_family": "season_index",
        "parent_url": DISCOVERY_PARENT_URL,
        "parser_disposition": disposition,
        "rights_disposition": "PRIVATE_RESEARCH_METADATA_ONLY_NONBLOCKING",
        "source_season": SEASON,
        "temporal_authority": "UNKNOWN_RETRIEVAL_TIME_ONLY",
    }


def build_objects(*, body: bytes, capture: Mapping[str, Any], repo_root: Path, data_root: Path) -> dict[str, Any]:
    discovered = discover_official_1997_url(data_root)
    compact = compact_capture(capture)
    compact["historical_publication_time"] = None
    compact["parent_url"] = DISCOVERY_PARENT_URL
    compact["source_season"] = SEASON
    compact["temporal_authority"] = "UNKNOWN_RETRIEVAL_TIME_ONLY"
    compact["url"] = OFFICIAL_SEASON_INDEX_URL
    parsed = parse_season_game_rows(body=body, page_url=OFFICIAL_SEASON_INDEX_URL, raw_sha256=str(compact.get("raw_sha256") or ""))
    code_identity = compute_code_identity(repo_root)
    payload = {
        "artifact_type": "TAMU_OFFICIAL_1997_SEASON_INDEX_CAPTURE",
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "source_id": SOURCE_ID,
        "season": SEASON,
        "official_index_url": OFFICIAL_SEASON_INDEX_URL,
        "discovery_parent_url": DISCOVERY_PARENT_URL,
        "history_index_sha256": PINNED_HISTORY_INDEX_SHA256,
        "history_href_proof": discovered["history_href_proof"],
        "inventory_identity": PINNED_INVENTORY_IDENTITY,
        "capture": compact,
        "capture_identity": compute_capture_identity(compact),
        "box_score_urls": parsed["box_score_urls"],
        "emitted_box_score_urls": parsed["emitted_box_score_urls"],
        "game_rows": parsed["game_rows"],
        "box_url_identity": stable_hash({"box_score_urls": parsed["box_score_urls"]}),
        "game_row_identity": compute_game_row_identity(parsed["game_rows"]),
        "counts": parsed["counts"],
        "validator_code_identity": code_identity,
    }
    payload["payload_identity"] = stable_hash(
        {
            "official_index_url": OFFICIAL_SEASON_INDEX_URL,
            "capture_identity": payload["capture_identity"],
            "box_url_identity": payload["box_url_identity"],
            "game_row_identity": payload["game_row_identity"],
            "counts": payload["counts"],
            "validator_code_identity": code_identity,
        }
    )
    gate = {
        "artifact_type": "TAMU_OFFICIAL_1997_SEASON_INDEX_GATE",
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
        "official_index_url": OFFICIAL_SEASON_INDEX_URL,
        "discovery_parent_url": DISCOVERY_PARENT_URL,
        "history_index_sha256": PINNED_HISTORY_INDEX_SHA256,
        "history_href_proof": discovered["history_href_proof"],
        "inventory_identity": PINNED_INVENTORY_IDENTITY,
        "capture": compact,
        "box_score_urls": parsed["box_score_urls"],
        "emitted_box_score_urls": parsed["emitted_box_score_urls"],
        "game_rows": parsed["game_rows"],
        "counts": parsed["counts"],
        "payload_identity": payload["payload_identity"],
        "validator_code_identity": code_identity,
        "upstream_identities": {
            "history_index_sha256": PINNED_HISTORY_INDEX_SHA256,
            "inventory_identity": PINNED_INVENTORY_IDENTITY,
            "protected_split_registry_sha256": PINNED_REGISTRY_SHA256,
        },
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    return {"payload": payload, "gate": gate}


def materialize(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    fetched = fetch_official_1997_season_index(data_root)
    body = fetched.pop("body")
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


def validate_artifact(*, repo_root: Path, data_root: Path, gate: Mapping[str, Any] | None = None, require_rebuild: bool = True) -> dict[str, Any]:
    committed = dict(gate or load_json(repo_root / GATE_RELATIVE))
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("official_index_url") != OFFICIAL_SEASON_INDEX_URL:
        raise AuthorityViolation("guessed or substituted 1997 official URL")
    if committed.get("history_href_proof") != HISTORY_HREF_PROOF:
        raise AuthorityViolation("1997 history href proof missing or changed")
    if committed.get("validator_code_identity") != compute_code_identity(repo_root):
        raise AuthorityViolation("changed code with stale code identity")
    if compute_gate_identity(committed) != committed.get("gate_identity"):
        raise AuthorityViolation("committed gate identity does not recompute")
    if require_rebuild:
        raw_rel = (committed.get("capture") or {}).get("raw_relative_path")
        if not raw_rel:
            raise AuthorityViolation("committed 1997 gate missing raw capture path")
        raw_path = data_root / raw_rel
        if not raw_path.is_file():
            raise AuthorityViolation("1997 raw capture missing")
        capture = dict(committed["capture"])
        capture["response_status"] = int(capture.get("response_status") or 0)
        capture["status"] = capture["response_status"]
        capture["content_type"] = "text/html"
        rebuilt = build_objects(body=raw_path.read_bytes(), capture=capture, repo_root=repo_root, data_root=data_root)
        if rebuilt["gate"] != committed:
            raise AuthorityViolation("committed 1997 gate does not match reconstruction")
    return {
        "result": "PASS",
        "gate_identity": committed.get("gate_identity"),
        "payload_identity": committed.get("payload_identity"),
        "scheduled_games": (committed.get("counts") or {}).get("scheduled_games"),
    }


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))

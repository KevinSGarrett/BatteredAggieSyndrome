"""Immutable 1997-expanded union successor from Phase 1 rejection-complete predecessor."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash
from aggie_analytics.data.tamu_official_historical_boxscores import AuthorityViolation
from aggie_analytics.validation.artifact_binding import compute_identity

SCHEMA_VERSION = "aggie.data.tamu_official_gamebook_union_1997_expanded.v1"
CONTRACT_RELATIVE = "configs/tamu_official_gamebook_union_1997_expanded_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_gamebook_union_1997_expanded_gate.json"
CONTRACT_ID = "BAT-XXX-TAMU-OFFICIAL-1997-EXPANDED-UNION-V1"
DECISION_UNIT = "POST-TASK-SRC014-1997-EXPANDED-ENRICHED-UNION-001"
JIRA_KEY = "BAT-XXX"
SOURCE_ID = "SRC-014"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PINNED_PREDECESSOR_GATE_IDENTITY = "c7d92b31a78a966af97be71845665486b7a9d5009a4943e6256f97c6faff1ba6"
PINNED_PREDECESSOR_UNION_IDENTITY = "8b9859388d2c46b934e11175775d528dde47352ecc1787189cd632b21bd6f842"
PINNED_REJECTION_LEDGER_IDENTITY = "d88ccffcabb70cd218b0aa40d395dba49c5dca3bcbf9c9ed139422fe20dc3051"
PINNED_1997_BOXSCORE_DATASET_IDENTITY = "ca7bbf2e78dd028d647ff3abc77392c91d956c96ab7d9a93b2ca6f5e8953598a"
PINNED_1997_BOXSCORE_GATE_IDENTITY = "09a0c2cc295c1b8c5cb03e392e7bb38d637f48b4d7090b69766e69b89ca808f3"
UNION_MANIFEST_NAME = "union_manifest.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    predecessor_gate = load_json(repo_root / "artifacts/data_lake/tamu_official_gamebook_union_1998_rejection_complete_gate.json")
    if predecessor_gate.get("gate_identity") != PINNED_PREDECESSOR_GATE_IDENTITY:
        raise AuthorityViolation("predecessor rejection-complete union gate identity drifted")
    if predecessor_gate.get("union_identity") != PINNED_PREDECESSOR_UNION_IDENTITY:
        raise AuthorityViolation("predecessor rejection-complete union identity drifted")
    predecessor_manifest = (
        data_root
        / "features/tamu_official_gamebook_union_1998_rejection_complete/sha256"
        / PINNED_PREDECESSOR_UNION_IDENTITY
        / UNION_MANIFEST_NAME
    )
    if not predecessor_manifest.is_file():
        raise AuthorityViolation("predecessor rejection-complete union manifest missing")
    predecessor_payload = load_json(predecessor_manifest)
    if predecessor_payload.get("union_identity") != PINNED_PREDECESSOR_UNION_IDENTITY:
        raise AuthorityViolation("predecessor union payload identity drifted")
    boxscore_gate = load_json(repo_root / "artifacts/data_lake/tamu_official_1997_boxscore_gate.json")
    if boxscore_gate.get("gate_identity") != PINNED_1997_BOXSCORE_GATE_IDENTITY:
        raise AuthorityViolation("1997 boxscore gate identity drifted")
    if boxscore_gate.get("dataset_identity") != PINNED_1997_BOXSCORE_DATASET_IDENTITY:
        raise AuthorityViolation("1997 boxscore dataset identity drifted")
    boxscore_payload_path = data_root / contract["upstream"]["boxscore_root"] / PINNED_1997_BOXSCORE_DATASET_IDENTITY / "payload.json"
    if not boxscore_payload_path.is_file():
        raise AuthorityViolation("1997 boxscore payload missing")
    boxscore_payload = load_json(boxscore_payload_path)
    rejected_ledger = list(predecessor_payload.get("complete_rejection_ledger") or [])
    existing_rejected = {str(item.get("url") or "") for item in rejected_ledger}
    captures = list(boxscore_payload.get("captures") or [])
    appended_1997: list[dict[str, Any]] = []
    for capture in captures:
        url = str(capture.get("url") or "")
        if not url or url in existing_rejected:
            continue
        appended_1997.append(
            {
                "url": url,
                "origin_issue": "BAT-XXX",
                "origin_gate_identity": PINNED_1997_BOXSCORE_GATE_IDENTITY,
                "source_season": 1997,
                "source_url": url,
                "source_sha256": str(capture.get("raw_sha256") or "") or None,
                "match_status": "UNMATCHED_STRONG_TUPLE",
                "rejection_reason": "PHASE3_PARSE_REJECTED_OR_UNMATCHED",
                "rejection_source": "BAT-XXX.rejected_official_1997_games",
                "capture_disposition": str(capture.get("parser_disposition") or "UNCLASSIFIED"),
                "membership_admitted": False,
                "availability": "NOT_ESTABLISHED",
                "availability_claim": False,
                "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
                "ncaa_contest_id": None,
            }
        )
    complete_rejection_ledger = sorted(rejected_ledger + appended_1997, key=lambda row: row["url"])
    unique_urls = {row["url"] for row in complete_rejection_ledger}
    if len(unique_urls) != len(complete_rejection_ledger):
        raise AuthorityViolation("duplicate rejected URLs in 1997 union successor")
    admitted_games = list(predecessor_payload.get("enriched_official_games") or [])
    admitted_urls = {str(item.get("url") or "") for item in admitted_games}
    if admitted_urls & unique_urls:
        raise AuthorityViolation("rejection/admission overlap in 1997 union successor")
    counts = dict(predecessor_payload.get("counts") or {})
    counts["official_1997_admitted"] = 0
    counts["official_1997_rejected"] = len(appended_1997)
    counts["new_games_added"] = 0
    counts["unmatched_rejected"] = len(complete_rejection_ledger)
    counts["rejected_urls_complete"] = len(complete_rejection_ledger)
    counts["ncaa_contest_ids_created"] = 0
    payload = {
        "schema_version": SCHEMA_VERSION,
        "predecessor_union_identity": PINNED_PREDECESSOR_UNION_IDENTITY,
        "predecessor_gate_identity": PINNED_PREDECESSOR_GATE_IDENTITY,
        "rejection_ledger_identity": PINNED_REJECTION_LEDGER_IDENTITY,
        "upstream_1997_boxscore_gate_identity": PINNED_1997_BOXSCORE_GATE_IDENTITY,
        "upstream_1997_boxscore_dataset_identity": PINNED_1997_BOXSCORE_DATASET_IDENTITY,
        "enriched_official_games": admitted_games,
        "admitted_official_1997_games": [],
        "rejected_official_1997_games": appended_1997,
        "complete_rejection_ledger": complete_rejection_ledger,
        "admitted_row_gap_urls": list(predecessor_payload.get("admitted_row_gap_urls") or []),
        "counts": counts,
        "protected_lane": PROTECTED_LANE,
    }
    payload["union_identity"] = stable_hash(
        {
            "predecessor_union_identity": payload["predecessor_union_identity"],
            "admitted_urls": sorted(admitted_urls),
            "rejected_urls": sorted(unique_urls),
            "counts": counts,
        }
    )
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_GAMEBOOK_UNION_1997_EXPANDED_GATE",
        "result": "PARTIAL_OFFICIAL_1997_EXPANDED_UNION_NO_NEW_ADMISSIONS",
        "classification": "TAMU_OFFICIAL_GAMEBOOK_UNION_1997_EXPANDED_CANDIDATE_ONLY",
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "source_id": SOURCE_ID,
        "disposition": "PRESERVE_MEMBERSHIP_APPEND_1997_REJECTIONS_ONLY",
        "predecessor_union_identity": PINNED_PREDECESSOR_UNION_IDENTITY,
        "predecessor_gate_identity": PINNED_PREDECESSOR_GATE_IDENTITY,
        "union_identity": payload["union_identity"],
        "counts": counts,
        "admitted_row_gap_urls": payload["admitted_row_gap_urls"],
        "rejection_ledger_identity": PINNED_REJECTION_LEDGER_IDENTITY,
        "upstream_1997_boxscore_gate_identity": PINNED_1997_BOXSCORE_GATE_IDENTITY,
        "upstream_1997_boxscore_dataset_identity": PINNED_1997_BOXSCORE_DATASET_IDENTITY,
        "protected_lane": PROTECTED_LANE,
        "validation_contract_version": SCHEMA_VERSION,
    }
    gate["gate_identity"] = compute_identity(gate, "gate_identity")
    root = data_root / contract["payloads"]["union_root"] / payload["union_identity"]
    return {"contract": contract, "payload": payload, "gate": gate, "manifest_path": root / UNION_MANIFEST_NAME}


def materialize_union(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    write_json(objects["manifest_path"], objects["payload"])
    write_json(repo_root / GATE_RELATIVE, objects["gate"])
    return {
        "gate_identity": objects["gate"]["gate_identity"],
        "union_identity": objects["payload"]["union_identity"],
        "manifest_path": str(objects["manifest_path"]),
        "official_1997_rejected": objects["payload"]["counts"]["official_1997_rejected"],
    }


def validate_artifact(*, repo_root: Path, data_root: Path, gate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    if committed != expected["gate"]:
        raise AuthorityViolation("committed 1997-expanded union gate does not match independent reconstruction")
    if committed.get("gate_identity") != compute_identity(committed, "gate_identity"):
        raise AuthorityViolation("gate identity does not recompute")
    if not expected["manifest_path"].is_file():
        raise AuthorityViolation("external 1997 union manifest missing")
    if load_json(expected["manifest_path"]) != expected["payload"]:
        raise AuthorityViolation("external 1997 union manifest mismatch")
    return {"result": "PASS", "gate_identity": committed["gate_identity"], "union_identity": committed["union_identity"]}


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))

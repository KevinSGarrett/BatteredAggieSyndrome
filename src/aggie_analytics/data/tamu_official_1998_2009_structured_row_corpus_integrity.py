"""Integrity successor that binds BAT-638 corpus payload hashes to complete rejection ledger."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import sha256_file, stable_hash
from aggie_analytics.data.tamu_official_2002_2009_structured_row_corpus import CHILD_FILENAMES
from aggie_analytics.data.tamu_official_historical_boxscores import AuthorityViolation
from aggie_analytics.validation.artifact_binding import compute_identity

SCHEMA_VERSION = "aggie.data.tamu_official_1998_2009_structured_row_corpus_integrity.v1"
VALIDATION_CONTRACT_VERSION = SCHEMA_VERSION
CONTRACT_RELATIVE = "configs/tamu_official_1998_2009_structured_row_corpus_integrity_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_1998_2009_structured_row_corpus_integrity_gate.json"
CONTRACT_ID = "BAT-649-TAMU-OFFICIAL-1998-2009-ROW-CORPUS-INTEGRITY-V1"
DECISION_UNIT = "POST-TASK-SRC014-1998-2009-REJECTION-INTEGRITY-001"
JIRA_KEY = "BAT-649"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_1998_2009_STRUCTURED_ROW_CORPUS_INTEGRITY_CANDIDATE_ONLY"
PASS_RESULT = "PASS_IMMUTABLE_CORPUS_INTEGRITY_SUCCESSOR"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PINNED_BAT638_GATE_IDENTITY = "a251b95714bed59de8aa593fe1466fce603858b30108c447c53fe6f3b8ee4e54"
PINNED_BAT638_DATASET_IDENTITY = "0ff650b1b691299d2b14fd252b8b938a9afe1d02cfd1eefdcd4d53bde2947ca8"
MANIFEST_NAME = "corpus_manifest.json"
SERIALIZED_DOMAINS = (
    "team_statistics",
    "individual_player_statistics",
    "drives",
    "play_by_play",
    "scoring_summary",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def compute_code_identity(repo_root: Path) -> str:
    path = repo_root / "src/aggie_analytics/data/tamu_official_1998_2009_structured_row_corpus_integrity.py"
    if not path.is_file():
        raise AuthorityViolation("code bundle member missing")
    hasher = hashlib.sha256()
    hasher.update(b"aggie.1998_2009.corpus_integrity.code_bundle.v1\n")
    hasher.update(path.read_bytes())
    return hasher.hexdigest()


def _child_payload_hashes(data_root: Path, rejected_urls: set[str]) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    root = data_root / "features/tamu_official_1998_2009_structured_row_corpus/sha256" / PINNED_BAT638_DATASET_IDENTITY
    child_payloads: dict[str, dict[str, Any]] = {}
    rejected_rows_by_domain: dict[str, int] = {}
    for domain in SERIALIZED_DOMAINS:
        filename = CHILD_FILENAMES[domain]
        path = root / filename
        if not path.is_file():
            raise AuthorityViolation(f"missing BAT-638 child payload: {filename}")
        rows = 0
        rejected_hits = 0
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            rows += 1
            row = json.loads(line)
            if str(row.get("source_url") or "") in rejected_urls:
                rejected_hits += 1
        rejected_rows_by_domain[domain] = rejected_hits
        child_payloads[domain] = {
            "filename": filename,
            "row_count": rows,
            "sha256": sha256_file(path),
        }
    return child_payloads, rejected_rows_by_domain


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    g638 = load_json(repo_root / "artifacts/data_lake/tamu_official_1998_2009_structured_row_corpus_gate.json")
    if g638.get("gate_identity") != PINNED_BAT638_GATE_IDENTITY:
        raise AuthorityViolation("BAT-638 gate identity drifted")
    if g638.get("dataset_identity") != PINNED_BAT638_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-638 dataset identity drifted")
    rej_gate = load_json(repo_root / "artifacts/data_lake/tamu_official_1998_2009_rejection_integrity_gate.json")
    rejection_gate_identity = str(rej_gate.get("gate_identity") or "")
    rejection_ledger_identity = str(rej_gate.get("ledger_identity") or "")
    if not rejection_gate_identity:
        raise AuthorityViolation("rejection-integrity gate identity missing")
    if not rejection_ledger_identity:
        raise AuthorityViolation("rejection ledger identity missing")
    ledger_path = (
        data_root
        / "features/tamu_official_1998_2009_rejection_integrity/sha256"
        / rejection_ledger_identity
        / "rejection_ledger.json"
    )
    if not ledger_path.is_file():
        raise AuthorityViolation("external rejection ledger missing")
    ledger = load_json(ledger_path)
    complete_rejected_urls = {str(item.get("url") or "") for item in (ledger.get("complete_rejection_ledger") or [])}
    active_rejected_urls = {str(item.get("url") or "") for item in (ledger.get("active_rejections") or [])}
    if len(active_rejected_urls) != 17:
        raise AuthorityViolation("expected exactly 17 active rejected URLs")
    child_payloads, rejected_rows = _child_payload_hashes(data_root, active_rejected_urls)
    if any(rejected_rows.values()):
        raise AuthorityViolation("rejected URLs leaked into BAT-638 child payloads")
    code_identity = compute_code_identity(repo_root)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
        "predecessor_dataset_identity": PINNED_BAT638_DATASET_IDENTITY,
        "predecessor_gate_identity": PINNED_BAT638_GATE_IDENTITY,
        "rejection_integrity_gate_identity": rejection_gate_identity,
        "rejection_ledger_identity": rejection_ledger_identity,
        "selected_seasons": list(g638.get("selected_seasons") or []),
        "child_payloads": child_payloads,
        "admitted_row_gap_urls": list(ledger.get("admitted_row_gap_urls") or []),
        "rejected_rows_by_domain": rejected_rows,
        "counts": {
            "games": int((g638.get("counts") or {}).get("games") or 0),
            "seasons": int((g638.get("counts") or {}).get("seasons") or 0),
            "serialized_rows_total": sum(meta["row_count"] for meta in child_payloads.values()),
            "complete_rejection_count": len(complete_rejected_urls),
            "active_rejection_count": len(active_rejected_urls),
            "ncaa_contest_ids_created": 0,
        },
        "validator_code_identity": code_identity,
    }
    manifest["dataset_identity"] = stable_hash(
        {
            "predecessor_dataset_identity": manifest["predecessor_dataset_identity"],
            "rejection_ledger_identity": manifest["rejection_ledger_identity"],
            "child_payloads": manifest["child_payloads"],
            "counts": manifest["counts"],
        }
    )
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_1998_2009_STRUCTURED_ROW_CORPUS_INTEGRITY_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "source_id": SOURCE_ID,
        "disposition": "NEW_IMMUTABLE_CORPUS_INTEGRITY_SUCCESSOR",
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
        "dataset_identity": manifest["dataset_identity"],
        "predecessor_dataset_identity": PINNED_BAT638_DATASET_IDENTITY,
        "predecessor_gate_identity": PINNED_BAT638_GATE_IDENTITY,
        "rejection_integrity_gate_identity": rejection_gate_identity,
        "rejection_ledger_identity": rejection_ledger_identity,
        "selected_seasons": manifest["selected_seasons"],
        "counts": manifest["counts"],
        "child_payloads": manifest["child_payloads"],
        "admitted_row_gap_urls": manifest["admitted_row_gap_urls"],
        "rejected_rows_by_domain": manifest["rejected_rows_by_domain"],
        "protected_lane": PROTECTED_LANE,
        "upstream_identities": {
            "bat638_gate_identity": PINNED_BAT638_GATE_IDENTITY,
            "bat638_dataset_identity": PINNED_BAT638_DATASET_IDENTITY,
            "rejection_integrity_gate_identity": rejection_gate_identity,
            "rejection_ledger_identity": rejection_ledger_identity,
        },
    }
    gate["gate_identity"] = compute_identity(gate, "gate_identity")
    root = data_root / contract["payloads"]["corpus_root"] / manifest["dataset_identity"]
    return {"contract": contract, "manifest": manifest, "gate": gate, "manifest_path": root / MANIFEST_NAME}


def materialize_corpus(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    write_json(objects["manifest_path"], objects["manifest"])
    write_json(repo_root / GATE_RELATIVE, objects["gate"])
    return {
        "gate_identity": objects["gate"]["gate_identity"],
        "dataset_identity": objects["manifest"]["dataset_identity"],
        "manifest_path": str(objects["manifest_path"]),
    }


def validate_artifact(*, repo_root: Path, data_root: Path, gate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    if committed != expected["gate"]:
        raise AuthorityViolation("committed corpus-integrity gate does not match independent reconstruction")
    if committed.get("gate_identity") != compute_identity(committed, "gate_identity"):
        raise AuthorityViolation("gate identity does not recompute")
    if not expected["manifest_path"].is_file():
        raise AuthorityViolation("external corpus-integrity manifest missing")
    if load_json(expected["manifest_path"]) != expected["manifest"]:
        raise AuthorityViolation("external corpus-integrity manifest mismatch")
    return {"result": "PASS", "dataset_identity": committed["dataset_identity"], "gate_identity": committed["gate_identity"]}


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))

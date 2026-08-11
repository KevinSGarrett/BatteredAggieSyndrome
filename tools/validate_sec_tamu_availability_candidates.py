from __future__ import annotations

"""Validate immutable SEC/A&M availability candidates and deterministic replay."""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.sec_availability import (  # noqa: E402
    ALLOWED_STATUSES,
    extract_candidate_rows,
    sha256_bytes,
    stable_hash,
)


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=REPO_ROOT / "configs" / "sec_tamu_availability_recovery_contract.json")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    data_root = args.data_root.resolve()
    manifest_path = args.candidate_manifest.resolve()
    contract_path = args.contract.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    acquisition_path = (
        data_root
        / "manifests"
        / "historical_known_at"
        / "sha256"
        / manifest["acquisition_identity"]
        / "sec_tamu_availability_acquisition_manifest.json"
    )
    acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        checks.append({"check": name, "pass": bool(condition), "detail": detail})
        if not condition:
            raise RuntimeError(f"validation failed: {name}: {detail}")

    check("contract_hash", manifest["contract_sha256"] == sha256_file(contract_path))
    check("acquisition_hash", manifest["acquisition_manifest_sha256"] == sha256_file(acquisition_path))
    check("decision_unit", manifest["decision_unit"] == "POST-SUBTASK-182")
    check("jira_key", manifest["jira_key"] == "BAT-539")
    core = {
        key: value
        for key, value in manifest.items()
        if key not in {"dataset_identity", "issued_at_utc", "payloads"}
    }
    check("dataset_identity", stable_hash(core) == manifest["dataset_identity"])
    payload_rows: dict[str, list[dict[str, Any]]] = {}
    for name, payload in manifest["payloads"].items():
        path = data_root / Path(*payload["path"].split("/"))
        check(f"{name}_exists", path.is_file(), str(path))
        check(f"{name}_sha256", sha256_file(path) == payload["sha256"])
        check(f"{name}_bytes", path.stat().st_size == payload["bytes"])
        payload_rows[name] = read_jsonl(path)
        check(f"{name}_rows", len(payload_rows[name]) == payload["rows"])
    candidates = payload_rows["candidates"]
    quarantine = payload_rows["quarantine"]
    check("candidate_count", len(candidates) == manifest["candidate_rows"])
    check("quarantine_count", len(quarantine) == manifest["quarantine_rows"])
    check("candidate_hashes", [stable_hash(row) for row in candidates] == manifest["candidate_row_hashes"])
    check("quarantine_hashes", [stable_hash(row) for row in quarantine] == manifest["quarantine_row_hashes"])
    ids = [row["availability_candidate_id"] for row in candidates]
    check("candidate_ids_unique", len(ids) == len(set(ids)))
    grain = [
        (row["source_record_id"], row["report_version"], row["evidence_locator"]["row_number"])
        for row in candidates
    ]
    check("source_version_row_grain_unique", len(grain) == len(set(grain)))
    check("status_vocabulary", all(row["status"] in ALLOWED_STATUSES for row in candidates))
    check("chronology_pass", all(row["chronology_pass"] for row in candidates))
    check("candidate_known_at_matches_chronology", all(row["historical_known_at_candidate"] == row["chronology_pass"] for row in candidates))
    check("canonical_player_ids_null", all(row["canonical_player_id"] is None for row in candidates))
    check("no_canonical_admission", all(not row["canonical_admission"] for row in candidates))
    check("no_pit_admission", all(not row["pit_state_admission"] for row in candidates))
    check("no_training_admission", all(not row["training_feature_admission"] for row in candidates))
    check("no_protected_admission", all(not row["protected_evaluation_admission"] for row in candidates))
    check("no_absence_inference", all(row["absence_means_available"] is False for row in candidates))
    check("authority_contract", all(value is False for key, value in manifest["authority"].items() if key != "candidate_layer"))
    check("candidate_layer_true", manifest["authority"]["candidate_layer"] is True)
    source_config = {source["source_record_id"]: source for source in contract["sources"]}
    rebuilt_candidates: list[dict[str, Any]] = []
    rebuilt_quarantine: list[dict[str, Any]] = []
    for record in acquisition["sources"]:
        source = source_config[record["source_record_id"]]
        if source["route_type"] != "TIMESTAMPED_ARTICLE_TABLE":
            continue
        captures = record.get("captures") or []
        if record["state"] != "CAPTURED" or len(captures) != 1:
            rebuilt_quarantine.append(
                {
                    "reason": "SOURCE_NOT_CAPTURED",
                    "source_record_id": source["source_record_id"],
                    "acquisition_state": record["state"],
                }
            )
            continue
        capture = captures[0]
        path = data_root / Path(*capture["immutable_path"].split("/"))
        rows, findings, _ = extract_candidate_rows(
            document=path.read_text(encoding="utf-8", errors="replace"),
            source=source,
            capture_sha256=capture["response_sha256"],
            captured_at_utc=capture["captured_at_utc"],
        )
        rebuilt_candidates.extend(rows)
        rebuilt_quarantine.extend(findings)
    rebuilt_candidates.sort(
        key=lambda row: (
            row["season"], row["target_game_date"], row["report_version"],
            row["player_name_normalized"], row["availability_candidate_id"],
        )
    )
    rebuilt_quarantine.sort(key=lambda row: (row["source_record_id"], row["reason"], stable_hash(row)))
    check("deterministic_candidate_replay", rebuilt_candidates == candidates)
    check("deterministic_quarantine_replay", rebuilt_quarantine == quarantine)
    serialized = manifest_path.read_text(encoding="utf-8").casefold()
    check("no_api_key_header_serialized", "x-api-key" not in serialized)
    result = {
        "validator": "validate_sec_tamu_availability_candidates.py",
        "status": "PASS",
        "dataset_identity": manifest["dataset_identity"],
        "candidate_rows": len(candidates),
        "quarantine_rows": len(quarantine),
        "checks": checks,
    }
    report_path = args.report or (
        data_root / "validation" / "POST-SUBTASK-182" / manifest["dataset_identity"] / "sec_tamu_availability_validation.json"
    )
    report_path = report_path.resolve()
    body = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if report_path.is_file():
        if report_path.read_bytes() != body:
            raise RuntimeError(f"immutable validation report collision: {report_path}")
    else:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = report_path.with_name(report_path.name + f".tmp-{os.getpid()}")
        try:
            temporary.write_bytes(body)
            os.replace(temporary, report_path)
        finally:
            if temporary.is_file():
                temporary.unlink()
    result["report_path"] = str(report_path)
    result["report_sha256"] = sha256_file(report_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Build the prospective 2026 national shadow cohort from immutable captures.

This command performs no network access. It reads the capture manifest produced by
``acquire_2026_prospective_schedule.py``, replays the offline parser over the
captured pages, and publishes a compact repository gate plus an external
content-addressed payload and manifest.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.national_foundation_reconciliation import (  # noqa: E402
    binding_identity,
    sha256_file,
)
from aggie_analytics.data.prospective_shadow_cohort import (  # noqa: E402
    CONTRACT_RELATIVE,
    EVIDENCE_RELATIVE,
    GATE_RELATIVE,
    build_cohort,
    build_gate,
    dataset_manifest,
    iso_utc,
    load_alias_population,
    load_contract,
    parse_utc,
    validate_artifact,
)

PAYLOAD_ROOT = "canonical/prospective_2026_shadow_cohort"


def write_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    body = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body.encode("utf-8"))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--data-root", type=Path, required=True)
    result.add_argument("--capture-manifest", type=Path, required=True)
    result.add_argument("--alias-payload", type=Path, required=True)
    result.add_argument("--spine-gate", type=Path, required=True)
    result.add_argument("--matrix-gate", type=Path, required=True)
    result.add_argument("--baseline-gate", type=Path, required=True)
    result.add_argument("--execution-time-utc", required=True)
    result.add_argument("--issued-at-utc", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    contract = load_contract(repo_root)
    execution_time = parse_utc(args.execution_time_utc)
    issued_at = parse_utc(args.issued_at_utc)
    if execution_time > datetime.now(timezone.utc):
        raise ValueError("execution time must not be in the future")
    capture_manifest = json.loads(args.capture_manifest.resolve().read_text(encoding="utf-8-sig"))
    if capture_manifest.get("contract_id") != contract["contract_id"]:
        raise ValueError("capture manifest was produced under a different contract")
    captures = [row for row in capture_manifest["captures"] if row["state"] == "CAPTURED"]
    documents = {
        capture["game_date"]: (data_root / capture["raw_relative_path"]).read_text(
            encoding="utf-8", errors="replace"
        )
        for capture in captures
    }
    population = load_alias_population(
        args.alias_payload.resolve(),
        minimum_most_recent_season=int(contract["supported_scope"]["minimum_most_recent_observed_season"]),
    )
    cohort = build_cohort(
        contract=contract,
        captures=captures,
        documents=documents,
        population=population,
        execution_time=execution_time,
        data_root=data_root,
    )
    rows = cohort["rows"]
    payload_stem = f"{PAYLOAD_ROOT}/pending"
    payload_path = data_root / payload_stem / "prospective_2026_shadow_cohort.jsonl"
    write_jsonl(payload_path, rows)
    payload_sha256 = sha256_file(payload_path)
    final_relative = f"{PAYLOAD_ROOT}/sha256/{payload_sha256}/prospective_2026_shadow_cohort.jsonl"
    final_path = data_root / final_relative
    final_path.parent.mkdir(parents=True, exist_ok=True)
    os.replace(payload_path, final_path)
    manifest = dataset_manifest(
        contract=contract,
        cohort=cohort,
        payload_relative_path=final_relative,
        payload_sha256=payload_sha256,
        payload_bytes=final_path.stat().st_size,
        payload_rows=len(rows),
    )
    manifest_relative = (
        "manifests/prospective_2026_shadow_cohort/sha256/"
        f"{manifest['dataset_identity']}/prospective_2026_shadow_cohort_manifest.json"
    )
    manifest_path = data_root / manifest_relative
    write_json(manifest_path, manifest)
    gate = build_gate(
        contract=contract,
        contract_sha256=sha256_file(repo_root / CONTRACT_RELATIVE),
        cohort=cohort,
        manifest_relative_path=manifest_relative,
        manifest_sha256=sha256_file(manifest_path),
        dataset_identity=manifest["dataset_identity"],
        spine_gate_sha256=sha256_file(args.spine_gate.resolve()),
        matrix_gate_sha256=sha256_file(args.matrix_gate.resolve()),
        baseline_gate_sha256=sha256_file(args.baseline_gate.resolve()),
    )
    gate = {
        **gate,
        "issued_at_utc": iso_utc(issued_at),
        "producer": {"python": sys.version.split()[0], "platform": platform.platform()},
    }
    gate["gate_identity"] = binding_identity(gate, "gate_identity")
    write_json(repo_root / GATE_RELATIVE, gate)
    verification = validate_artifact(repo_root, data_root)
    write_json(
        repo_root / EVIDENCE_RELATIVE,
        {
            "schema_version": gate["schema_version"],
            "artifact_type": "PROSPECTIVE_2026_NATIONAL_SHADOW_COHORT_REPLAY",
            "contract_id": gate["contract_id"],
            "decision_unit": gate["decision_unit"],
            "jira_key": gate["jira_key"],
            "gate_identity": gate["gate_identity"],
            "independent_validation": verification,
            "capture_identity": capture_manifest["capture_identity"],
            "execution_time_utc": gate["execution_time_utc"],
            "issued_at_utc": iso_utc(issued_at),
        },
    )
    print(
        json.dumps(
            {
                "result": gate["result"],
                "gate_identity": gate["gate_identity"],
                "dataset_identity": manifest["dataset_identity"],
                "row_count": gate["row_count"],
                "state_counts": gate["state_counts"],
                "eligible_contest_ids": gate["eligible_contest_ids"],
                "independent_validation": verification["result"],
                "findings": verification["findings"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if verification["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

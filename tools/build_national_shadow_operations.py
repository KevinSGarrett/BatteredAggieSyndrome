"""Replay the merged shadow evidence through the append-only state machine.

This command performs no network access and fits nothing. It reads the merged
Cycle #20 gates plus the frozen Phase 8 payloads, drives every contest and every
forecast row through the append-only ledger, reevaluates GAP-002 through GAP-009
against those same gates, and publishes a compact repository gate plus an external
content-addressed ledger payload.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.national_foundation_reconciliation import (  # noqa: E402
    binding_identity,
    sha256_file,
)
from aggie_analytics.data.prospective_shadow_cohort import iso_utc, parse_utc  # noqa: E402
from aggie_analytics.modeling.national_shadow_state_machine import (  # noqa: E402
    CONTRACT_RELATIVE,
    EVIDENCE_RELATIVE,
    GATE_RELATIVE,
    build_bundle,
    build_gate,
    dataset_manifest,
    load_contract,
    validate_artifact,
)

PAYLOAD_ROOT = "canonical/national_shadow_operations"
SNAPSHOT_ROLE = "PROSPECTIVE_2026_SHADOW_SNAPSHOT_ROWS"
FORECAST_ROLE = "PROSPECTIVE_2026_SHADOW_FORECAST_ROWS"

GATE_KEYS = {
    "foundation": "foundation_gate_relative_path",
    "spine": "spine_gate_relative_path",
    "domain_matrix": "domain_matrix_gate_relative_path",
    "matrix": "matrix_gate_relative_path",
    "baseline": "baseline_gate_relative_path",
    "cohort": "cohort_gate_relative_path",
    "forecast": "forecast_gate_relative_path",
    "scoring": "scoring_gate_relative_path",
    "rehearsal": "rehearsal_gate_relative_path",
}


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: object) -> None:
    payload = (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    body = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body.encode("utf-8"))
    return sha256_file(path)


def load_rows(data_root: Path, manifest: dict[str, Any], role: str) -> list[dict[str, Any]]:
    entry = next(item for item in manifest["payloads"] if item["role"] == role)
    path = data_root / entry["relative_path"]
    if sha256_file(path) != entry["sha256"]:
        raise ValueError(f"frozen payload hash drift: {role}")
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--data-root", type=Path, required=True)
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

    bound = contract["bound_predecessors"]
    gates = {name: read_json(repo_root / bound[key]) for name, key in GATE_KEYS.items()}
    baseline_contract = read_json(repo_root / bound["baseline_contract_relative_path"])
    frozen_candidate_ids = [str(item["candidate_id"]) for item in baseline_contract["candidates"]]

    manifest_path = data_root / gates["forecast"]["manifest"]["relative_path"]
    if sha256_file(manifest_path) != gates["forecast"]["manifest"]["sha256"]:
        raise ValueError("the bound Phase 8 dataset manifest hash drifted")
    forecast_manifest = read_json(manifest_path)
    snapshots = load_rows(data_root, forecast_manifest, SNAPSHOT_ROLE)
    forecasts = load_rows(data_root, forecast_manifest, FORECAST_ROLE)

    bundle = build_bundle(
        contract=contract,
        gates=gates,
        snapshots=snapshots,
        forecasts=forecasts,
        frozen_candidate_ids=frozen_candidate_ids,
        capture_identity=str(gates["forecast"]["capture_identity"]),
        execution_time=execution_time,
    )

    name = "national_shadow_operations_ledger.jsonl"
    pending = data_root / PAYLOAD_ROOT / "pending" / name
    digest = write_jsonl(pending, bundle["ledger_entries"])
    final_relative = f"{PAYLOAD_ROOT}/sha256/{digest}/{name}"
    final_path = data_root / final_relative
    final_path.parent.mkdir(parents=True, exist_ok=True)
    os.replace(pending, final_path)
    payloads = [
        {
            "name": name,
            "relative_path": final_relative,
            "role": "NATIONAL_SHADOW_OPERATIONS_LEDGER_ROWS",
            "rows": len(bundle["ledger_entries"]),
            "bytes": final_path.stat().st_size,
            "sha256": digest,
        }
    ]

    manifest = dataset_manifest(contract=contract, bundle=bundle, payloads=payloads)
    manifest_relative = (
        "manifests/national_shadow_operations/sha256/"
        f"{manifest['dataset_identity']}/national_shadow_operations_manifest.json"
    )
    ledger_manifest_path = data_root / manifest_relative
    write_json(ledger_manifest_path, manifest)

    gate = build_gate(
        contract=contract,
        contract_sha256=sha256_file(repo_root / CONTRACT_RELATIVE),
        bundle=bundle,
        predecessor_sha256={
            key.replace("_relative_path", "_sha256"): sha256_file(repo_root / relative)
            for key, relative in bound.items()
            if key.endswith("_relative_path")
        },
        manifest_relative_path=manifest_relative,
        manifest_sha256=sha256_file(ledger_manifest_path),
        dataset_identity=manifest["dataset_identity"],
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
            "artifact_type": "NATIONAL_SHADOW_OPERATIONS_REPLAY",
            "contract_id": gate["contract_id"],
            "decision_unit": gate["decision_unit"],
            "jira_key": gate["jira_key"],
            "gate_identity": gate["gate_identity"],
            "dataset_identity": manifest["dataset_identity"],
            "execution_time_utc": gate["execution_time_utc"],
            "independent_validation": verification,
            "issued_at_utc": iso_utc(issued_at),
        },
    )
    print(
        json.dumps(
            {
                "result": gate["result"],
                "gate_identity": gate["gate_identity"],
                "dataset_identity": manifest["dataset_identity"],
                "counts": gate["counts"],
                "terminal_state_counts": gate["terminal_state_counts"],
                "gap_states": {
                    item["gap_id"]: item["state"] for item in gate["gap_reevaluation"]
                },
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

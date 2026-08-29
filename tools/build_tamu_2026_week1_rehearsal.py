"""Build the Texas A&M Week One 2026 rehearsal gate from frozen Phase 8 evidence.

This command performs no network access and fits nothing. It reads the frozen
Phase 8 snapshot and forecast payloads, isolates the single declared target
contest, restates the mandatory no-adjustment national path, and enumerates the
Texas A&M evidence routes that could or could not augment that path.
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
from aggie_analytics.modeling.tamu_week1_rehearsal import (  # noqa: E402
    CONTRACT_RELATIVE,
    EVIDENCE_RELATIVE,
    GATE_RELATIVE,
    build_gate,
    build_rehearsal_bundle,
    load_contract,
    validate_artifact,
)

SNAPSHOT_ROLE = "PROSPECTIVE_2026_SHADOW_SNAPSHOT_ROWS"
FORECAST_ROLE = "PROSPECTIVE_2026_SHADOW_FORECAST_ROWS"


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


def load_rows(data_root: Path, manifest: dict[str, Any], role: str) -> list[dict[str, Any]]:
    entry = next(item for item in manifest["payloads"] if item["role"] == role)
    path = data_root / entry["relative_path"]
    if sha256_file(path) != entry["sha256"]:
        raise ValueError(f"frozen payload hash drift: {role}")
    with path.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    if len(rows) != int(entry["rows"]):
        raise ValueError(f"frozen payload row count drift: {role}")
    return rows


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
    forecast_gate = read_json(repo_root / bound["forecast_gate_relative_path"])
    baseline_contract = read_json(repo_root / bound["baseline_contract_relative_path"])
    domain_gate = read_json(repo_root / bound["domain_matrix_gate_relative_path"])
    tamu_gates = {
        Path(relative).stem: read_json(repo_root / relative)
        for relative in bound["tamu_specialization_gate_relative_paths"]
    }

    manifest_path = data_root / forecast_gate["manifest"]["relative_path"]
    if sha256_file(manifest_path) != forecast_gate["manifest"]["sha256"]:
        raise ValueError("the bound Phase 8 dataset manifest hash drifted")
    manifest = read_json(manifest_path)
    snapshots = load_rows(data_root, manifest, SNAPSHOT_ROLE)
    forecasts = load_rows(data_root, manifest, FORECAST_ROLE)

    bundle = build_rehearsal_bundle(
        contract=contract,
        baseline_contract=baseline_contract,
        snapshots=snapshots,
        forecasts=forecasts,
        domain_gate=domain_gate,
        tamu_gates=tamu_gates,
        execution_time=execution_time,
    )
    gate = build_gate(
        contract=contract,
        contract_sha256=sha256_file(repo_root / CONTRACT_RELATIVE),
        bundle=bundle,
        predecessor_sha256={
            "forecast_gate_sha256": sha256_file(repo_root / bound["forecast_gate_relative_path"]),
            "cohort_gate_sha256": sha256_file(repo_root / bound["cohort_gate_relative_path"]),
            "baseline_gate_sha256": sha256_file(repo_root / bound["baseline_gate_relative_path"]),
            "domain_matrix_gate_sha256": sha256_file(
                repo_root / bound["domain_matrix_gate_relative_path"]
            ),
        },
    )
    gate = {
        **gate,
        "bound_forecast_gate_identity": forecast_gate["gate_identity"],
        "bound_dataset_identity": manifest["dataset_identity"],
        "issued_at_utc": iso_utc(issued_at),
        "producer": {"python": sys.version.split()[0], "platform": platform.platform()},
    }
    gate["gate_identity"] = binding_identity(gate, "gate_identity")
    write_json(repo_root / GATE_RELATIVE, gate)

    verification = validate_artifact(repo_root)
    write_json(
        repo_root / EVIDENCE_RELATIVE,
        {
            "schema_version": gate["schema_version"],
            "artifact_type": "TAMU_2026_WEEK1_NATIONAL_BASELINE_REHEARSAL_REPLAY",
            "contract_id": gate["contract_id"],
            "decision_unit": gate["decision_unit"],
            "jira_key": gate["jira_key"],
            "gate_identity": gate["gate_identity"],
            "bound_forecast_gate_identity": gate["bound_forecast_gate_identity"],
            "bound_dataset_identity": gate["bound_dataset_identity"],
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
                "target_contest": gate["target_contest_identity"]["ncaa_contest_id"],
                "counts": gate["counts"],
                "frozen_candidate_ids": gate["no_adjustment_national_path"][
                    "frozen_candidate_ids"
                ],
                "augmentation_summary": gate["augmentation_summary"],
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

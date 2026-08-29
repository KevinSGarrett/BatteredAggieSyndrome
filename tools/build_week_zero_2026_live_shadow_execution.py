"""Materialize the Week Zero 2026 live shadow execution and eligible scoring gate."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.modeling.week_zero_live_shadow_execution import (  # noqa: E402
    EVIDENCE_RELATIVE,
    GATE_RELATIVE,
    execute_week_zero,
    latest_capture_manifest,
    load_contract,
    parse_utc,
    reconstruct_frozen_population,
    validate_artifact,
)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT"))
    parser.add_argument("--execution-time-utc", default=None)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    if not args.data_root:
        raise SystemExit("AGGIE_ANALYTICS_DATA_ROOT must be set")
    repo_root, data_root = Path(args.repo_root).resolve(), Path(args.data_root).resolve()

    if args.validate_only:
        print(json.dumps(validate_artifact(repo_root, data_root), indent=2, sort_keys=True))
        return 0

    contract = load_contract(repo_root)
    capture_manifest = latest_capture_manifest(data_root)
    execution_time = (
        parse_utc(args.execution_time_utc)
        if args.execution_time_utc
        else parse_utc(capture_manifest["issued_at_utc"])
    )
    if execution_time > datetime.now(timezone.utc):
        raise SystemExit("the execution time must not be in the future")

    population = reconstruct_frozen_population(repo_root, data_root)
    gate = execute_week_zero(
        population, capture_manifest, contract, execution_time=execution_time
    )

    write_json(repo_root / GATE_RELATIVE, gate)
    write_json(
        repo_root / EVIDENCE_RELATIVE,
        {
            "capture_identity": gate["capture_identity"],
            "contest_state_counts": gate["contest_state_counts"],
            "execution_time_utc": gate["execution_time_utc"],
            "forecast_state_counts": gate["forecast_state_counts"],
            "gate_identity": gate["gate_identity"],
            "gate_relative_path": GATE_RELATIVE,
            "metrics": gate["metrics"],
            "replay_command": (
                "python tools/build_week_zero_2026_live_shadow_execution.py --validate-only"
            ),
            "result": gate["result"],
        },
    )

    print(
        json.dumps(
            {
                "contest_state_counts": gate["contest_state_counts"],
                "forecast_state_counts": gate["forecast_state_counts"],
                "gate_identity": gate["gate_identity"],
                "metrics": {k: v for k, v in gate["metrics"].items() if k != "calibration_bins"},
                "refreshed_capture_summary": gate["refreshed_capture_summary"],
                "result": gate["result"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

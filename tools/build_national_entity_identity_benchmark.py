"""Build the national entity-identity benchmark and the 2026 cohort successor."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.national_entity_identity_benchmark import (  # noqa: E402
    ARTIFACT_ID,
    CONTRACT_ID,
    EntityBenchmarkViolation,
    build_artifact,
    load_inputs,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--acquisition", type=Path, required=True)
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--output-gate", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    data_root = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
    if not data_root:
        print("AGGIE_ANALYTICS_DATA_ROOT must be mounted", file=sys.stderr)
        return 2

    try:
        inputs = load_inputs(
            contract_path=args.contract,
            acquisition_path=args.acquisition,
            targets_path=args.targets,
            data_root=Path(data_root),
        )
        artifact = build_artifact(**inputs)
    except EntityBenchmarkViolation as error:
        print(f"ENTITY_BENCHMARK_VIOLATION: {error}", file=sys.stderr)
        return 1

    gate = artifact["gate"]
    if args.validate_only:
        existing = json.loads(args.output_gate.read_text(encoding="utf-8-sig"))
        if existing.get("payload_root_sha256") != gate.get("payload_root_sha256"):
            print(
                "payload identity drifted:"
                f" committed={existing.get('payload_root_sha256')}"
                f" rebuilt={gate.get('payload_root_sha256')}",
                file=sys.stderr,
            )
            return 1
        print(f"{ARTIFACT_ID} reproduced {gate['payload_root_sha256']}")
        return 0

    args.output_directory.mkdir(parents=True, exist_ok=True)
    for name, rows in artifact["payloads"].items():
        target = args.output_directory / name
        with target.open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    args.output_gate.parent.mkdir(parents=True, exist_ok=True)
    args.output_gate.write_text(
        json.dumps(gate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    summary = gate["benchmark_metrics"]
    print(f"contract {CONTRACT_ID}")
    print(f"payload identity {gate['payload_root_sha256']}")
    print(
        "benchmark:"
        f" coverage={summary['exact_match_coverage']}"
        f" precision={summary['precision']}"
        f" recall={summary['recall']}"
        f" abstention={summary['abstention_rate']}"
        f" conflict={summary['conflict_rate']}"
    )
    rebound = gate["coverage_rebound"]
    print(
        "rebound:"
        f" newly_supported_participants={rebound['newly_supported_participants']}"
        f" newly_supported_contests={rebound['newly_supported_contests']}"
        f" frozen_coverage_changed={rebound['frozen_or_scorable_coverage_changed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

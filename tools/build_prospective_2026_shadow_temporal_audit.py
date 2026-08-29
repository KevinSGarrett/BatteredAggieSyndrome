"""Materialize the independent temporal-proof audit of the frozen 2026 shadow forecasts."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.modeling.shadow_forecast_temporal_audit import (  # noqa: E402
    EVIDENCE_RELATIVE,
    GATE_RELATIVE,
    build_audit,
    canonical_json_bytes,
    load_contract,
    reconstruct_population,
    validate_artifact,
)


def default_data_root() -> Path:
    configured = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
    if not configured:
        raise SystemExit("AGGIE_ANALYTICS_DATA_ROOT must be set to reconstruct the population")
    return Path(configured)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", default=None)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="re-derive the audit and compare it to the committed gate without writing",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    data_root = Path(args.data_root).resolve() if args.data_root else default_data_root()

    if args.validate_only:
        summary = validate_artifact(repo_root, data_root)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0

    contract = load_contract(repo_root)
    population = reconstruct_population(repo_root, data_root)
    gate = build_audit(population, contract)

    write_json(repo_root / GATE_RELATIVE, gate)
    write_json(
        repo_root / EVIDENCE_RELATIVE,
        {
            "audited_predecessor_identities": gate["audited_predecessor_identities"],
            "gate_identity": gate["gate_identity"],
            "gate_relative_path": GATE_RELATIVE,
            "reconstructed_population": gate["reconstructed_population"],
            "replay_command": (
                "python tools/build_prospective_2026_shadow_temporal_audit.py --validate-only"
            ),
            "result": gate["result"],
            "verdict_counts": gate["verdict_counts"],
        },
    )

    print(
        json.dumps(
            {
                "bytes": len(canonical_json_bytes(gate)),
                "gate_identity": gate["gate_identity"],
                "reconstructed_population": gate["reconstructed_population"],
                "result": gate["result"],
                "verdict_counts": gate["verdict_counts"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

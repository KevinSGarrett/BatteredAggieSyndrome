from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.tamu_official_2000_2009_structured_row_corpus import (  # noqa: E402
    materialize_corpus,
    reconstruct_objects,
    validate_artifact,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize or reconstruct the 2000-2009 official structured row corpus successor."
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(
            os.environ.get(
                "AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"
            )
        ),
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    if args.validate_only:
        reconstructed = reconstruct_objects(repo_root=repo_root, data_root=data_root)
        validated = validate_artifact(
            repo_root=repo_root, data_root=data_root, require_rebuild=True
        )
        print(
            json.dumps(
                {
                    "dataset_identity": reconstructed["manifest"]["dataset_identity"],
                    "gate_identity": reconstructed["gate"]["gate_identity"],
                    "code_identity": reconstructed["gate"]["validator_code_identity"],
                    "counts": reconstructed["gate"]["counts"],
                    "validated_dataset_identity": validated["dataset_identity"],
                    "mode": "validate-only",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    result = materialize_corpus(repo_root=repo_root, data_root=data_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.experimentation.walk_forward import (  # noqa: E402
    compute_artifact_identity,
    execute_dry_run,
    validate_walk_forward_artifact,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="BAT-400 development-safe walk-forward dry run")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Repository-relative or absolute artifact path",
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    output = args.output
    if output is None:
        output = repo_root / "artifacts" / "pit" / "protected_replay_dry_run.json"
    elif not output.is_absolute():
        output = repo_root / output
    if args.validate_only:
        payload = json.loads(output.read_text(encoding="utf-8"))
        validate_walk_forward_artifact(payload, repo_root)
        if payload.get("artifact_identity") != compute_artifact_identity(payload):
            raise SystemExit("artifact identity mismatch")
        print(f"PASS validate-only identity={payload['artifact_identity']}")
        return 0
    artifact = execute_dry_run(repo_root=repo_root, data_root=args.data_root, output_path=output)
    print(
        json.dumps(
            {
                "status": artifact["status"],
                "artifact_identity": artifact["artifact_identity"],
                "folds": len(artifact["folds"]),
                "development_label_status": artifact["development_label_status"],
                "protected_outcomes_inaccessible": artifact["protected_outcomes_inaccessible"],
                "protected_metrics_produced": artifact["protected_metrics_produced"],
                "output": str(output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

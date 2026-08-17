from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.operations.incidents import run_incident_drill, validate_incident_artifact


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic incident drill.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/operations/drift_incident_game_day.json"),
    )
    parser.add_argument("--work-root", type=Path, default=None)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    if args.validate_only:
        payload = json.loads(args.output.read_text(encoding="utf-8"))
        validate_incident_artifact(payload, repo_root=repo_root)
        print(json.dumps({"result": "PASS", "artifact_identity": payload["artifact_identity"]}, indent=2))
        return 0

    payload = run_incident_drill(
        output_path=args.output,
        work_root=args.work_root,
        repo_root=repo_root,
    )
    print(json.dumps({"result": "PASS", "artifact_identity": payload["artifact_identity"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

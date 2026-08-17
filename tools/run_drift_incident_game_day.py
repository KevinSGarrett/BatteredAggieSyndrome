from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.operations.incidents import run_incident_drill


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic incident drill.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/operations/drift_incident_game_day.json"),
    )
    parser.add_argument("--work-root", type=Path, default=None)
    args = parser.parse_args()

    payload = run_incident_drill(output_path=args.output, work_root=args.work_root)
    print(json.dumps({"result": "PASS", "artifact_identity": payload["artifact_identity"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

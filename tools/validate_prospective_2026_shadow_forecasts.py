"""Independently validate the published 2026 shadow forecast gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.modeling.prospective_shadow_forecasts import validate_artifact  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args()
    verification = validate_artifact(args.repo_root.resolve(), args.data_root.resolve())
    print(json.dumps(verification, indent=2, sort_keys=True))
    return 0 if verification["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

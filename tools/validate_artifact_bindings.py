from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.validation.artifact_binding import (  # noqa: E402
    ArtifactBindingError,
    validate_artifact_bindings,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate cross-surface artifact identity bindings")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        report = validate_artifact_bindings(args.repo_root.resolve())
    except ArtifactBindingError as exc:
        print(f"FAIL: {exc}")
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Pure, non-mutating validator for official rich-structure consistency."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.tamu_official_rich_structure import (  # noqa: E402
    RichStructureViolation,
    validate_rich_structure_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate official rich-structure definitions.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    try:
        result = validate_rich_structure_artifacts(repo_root=repo_root)
    except RichStructureViolation as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

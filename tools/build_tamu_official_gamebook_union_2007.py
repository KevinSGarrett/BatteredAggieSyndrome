from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.tamu_official_gamebook_union_2007 import (  # noqa: E402
    default_data_root,
    materialize_union,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize the 2007 official Texas A&M gamebook union.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--data-root", type=Path, default=default_data_root())
    args = parser.parse_args()
    result = materialize_union(repo_root=args.repo_root.resolve(), data_root=args.data_root.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

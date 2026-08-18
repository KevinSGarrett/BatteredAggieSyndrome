from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.tamu_official_gamebook_union import default_data_root, materialize  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize the official Texas A&M gamebook union.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--data-root", type=Path, default=default_data_root())
    args = parser.parse_args()
    result = materialize(data_root=args.data_root.resolve(), repo_root=args.repo_root.resolve())
    gate = result["gate"]
    print(
        json.dumps(
            {
                "result": gate["result"],
                "gate_identity": gate["gate_identity"],
                "union_identity": gate["union_identity"],
                "counts": gate["counts"],
                "texas_2011": gate["texas_2011"]["disposition"],
                "lsu_2010": gate["lsu_2010"]["disposition"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

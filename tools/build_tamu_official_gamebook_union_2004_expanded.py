from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.tamu_official_gamebook_union_2004_expanded import (  # noqa: E402
    materialize_union,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize the 2004-expanded official enriched union.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")),
    )
    args = parser.parse_args()
    result = materialize_union(repo_root=args.repo_root.resolve(), data_root=args.data_root.resolve())
    print(
        json.dumps(
            {
                "gate_identity": result["gate_identity"],
                "union_identity": result["union_identity"],
                "counts": result["counts"],
                "recomputed_upstream": result["recomputed_upstream"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

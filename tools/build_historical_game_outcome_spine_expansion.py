from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.historical_game_outcome_spine_expansion import (  # noqa: E402
    materialize_expansion,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize a pinned expansion of the historical game/outcome reference spine."
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "configs/historical_game_outcome_spine_expansion_contract.json",
    )
    parser.add_argument(
        "--input-data-root",
        type=Path,
        default=Path(
            os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
        ),
    )
    parser.add_argument("--output-data-root", type=Path)
    parser.add_argument(
        "--issued-at-utc",
        default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    args = parser.parse_args()
    result = materialize_expansion(
        input_data_root=args.input_data_root.resolve(),
        output_data_root=(args.output_data_root or args.input_data_root).resolve(),
        repo_root=args.repo_root.resolve(),
        contract_path=args.contract.resolve(),
        issued_at_utc=args.issued_at_utc,
    )
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "manifest"},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

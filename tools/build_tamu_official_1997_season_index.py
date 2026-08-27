from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.tamu_official_1997_season_index import materialize  # noqa: E402  # pylint: disable=import-error


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture the official 1997 SRC-014 season index and discover box URLs.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")),
    )
    args = parser.parse_args()
    result = materialize(repo_root=args.repo_root.resolve(), data_root=args.data_root.resolve())
    printable = {key: value for key, value in result.items() if key != "box_score_urls"}
    printable["box_score_url_count"] = len(result["box_score_urls"])
    print(json.dumps(printable, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

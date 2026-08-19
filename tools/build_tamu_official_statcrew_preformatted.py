from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.tamu_official_statcrew_preformatted import materialize  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize the StatCrew preformatted-domain payload.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")),
    )
    args = parser.parse_args()
    result = materialize(repo_root=args.repo_root.resolve(), data_root=args.data_root.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

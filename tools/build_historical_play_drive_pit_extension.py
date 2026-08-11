from __future__ import annotations

import argparse
import json
from pathlib import Path

from aggie_analytics.temporal.play_drive_pit import materialize


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-data-root", type=Path, required=True)
    parser.add_argument("--output-data-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--issued-at-utc", required=True)
    args = parser.parse_args()
    result = materialize(
        input_data_root=args.input_data_root,
        output_data_root=args.output_data_root,
        repo_root=args.repo_root,
        issued_at_utc=args.issued_at_utc,
        contract_name="historical_play_drive_pit_extension_contract.json",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

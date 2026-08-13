from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data.ncaa_contest_reconciliation_expansion import resolve_and_reconcile  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-data-root", type=Path, required=True)
    parser.add_argument("--output-data-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--policy", type=Path, default=ROOT / "configs/ncaa_contest_reconciliation_expansion_policy.json")
    parser.add_argument("--discovery-manifest", type=Path, required=True)
    parser.add_argument("--issued-at-utc", default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    args = parser.parse_args()
    result = resolve_and_reconcile(
        input_data_root=args.input_data_root.resolve(),
        output_data_root=args.output_data_root.resolve(),
        repo_root=args.repo_root.resolve(),
        policy_path=args.policy.resolve(),
        discovery_manifest_path=args.discovery_manifest.resolve(),
        issued_at_utc=args.issued_at_utc,
    )
    print(json.dumps({key: value for key, value in result.items() if key != "manifest"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations
import argparse
import json
from second_pass_hardening import load_records, strict_validate

parser = argparse.ArgumentParser(description="Strict second-pass Jira validation.")
parser.add_argument("--repo-root", default=None)
parser.add_argument("--mode", choices=("validate", "materialize"), default="validate", help="validate is byte-read-only; materialize rewrites SECOND_PASS_* derivatives")
args = parser.parse_args()
errors, metrics = strict_validate(load_records(), write_reports=args.mode == "materialize")
print(json.dumps(metrics, indent=2, sort_keys=True))
raise SystemExit(1 if errors else 0)

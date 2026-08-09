from __future__ import annotations
import argparse
import json
from second_pass_hardening import validate_source_anchors, load_records, regenerate_source_manifests, import_lib
parser = argparse.ArgumentParser(description="Validate source hashes, line ranges, excerpts, and anchors; optionally repair only after deterministic relocation.")
parser.add_argument("--repair", action="store_true")
parser.add_argument("--repo-root", type=str, default=None, help="Authoritative BAS repository root for standalone Jira-pack validation.")
args = parser.parse_args()
errors, rows = validate_source_anchors(repair=args.repair)
if args.repair:
    regenerate_source_manifests(load_records())
    import_lib().rebuild_file_manifest()
print(json.dumps({"result": "PASS" if not errors else "FAIL", "references": len(rows), "repair": args.repair, "relocated": sum(bool(r.get("relocated")) for r in rows), "errors": errors}, indent=2, sort_keys=True))
raise SystemExit(1 if errors else 0)

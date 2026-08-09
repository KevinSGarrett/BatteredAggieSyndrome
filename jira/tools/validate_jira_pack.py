from __future__ import annotations
import json
import shutil
from second_pass_hardening import JIRA_ROOT, load_records, strict_validate, import_lib
for cache in JIRA_ROOT.rglob("__pycache__"):
    shutil.rmtree(cache, ignore_errors=True)
errors, metrics = strict_validate(load_records(), write_reports=True)
lib = import_lib()
lib.rebuild_file_manifest()
manifest_errors = lib.validate_file_manifest()
all_errors = errors + manifest_errors
result = {"result": "PASS" if not all_errors else "FAIL", "strict": metrics, "manifest_errors": manifest_errors, "errors": all_errors}
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(1 if all_errors else 0)

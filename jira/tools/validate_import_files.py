from __future__ import annotations
import json
from second_pass_hardening import load_records, strict_validate
errors, metrics = strict_validate(load_records(), write_reports=True)
import_errors = [error for error in errors if "IMPORT" in error.upper() or "CSV" in error.upper() or "PAYLOAD" in error.upper() or "PARENT" in error.upper()]
print(json.dumps({"result": "PASS" if not errors else "FAIL", "issue_count": metrics["issue_count"], "import_error_count": len(import_errors), "all_error_count": len(errors), "errors": errors}, indent=2, sort_keys=True))
raise SystemExit(1 if errors else 0)

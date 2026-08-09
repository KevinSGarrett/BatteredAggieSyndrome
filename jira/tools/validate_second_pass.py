from __future__ import annotations
import json
from second_pass_hardening import load_records, strict_validate
errors, metrics = strict_validate(load_records(), write_reports=True)
print(json.dumps(metrics, indent=2, sort_keys=True))
raise SystemExit(1 if errors else 0)

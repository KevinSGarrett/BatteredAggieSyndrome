from __future__ import annotations
import json
from jira_pack_lib import load_records, cycles
records = load_records()
by_id = {record["local_id"]: record for record in records}
errors = []
for record in records:
    for dependency in record.get("dependencies", []):
        if dependency not in by_id:
            errors.append(f"{record['local_id']}: missing dependency {dependency}")
        elif record["local_id"] not in by_id[dependency].get("blocks", []):
            errors.append(f"{record['local_id']}: inverse blocks relationship missing on {dependency}")
    for blocked in record.get("blocks", []):
        if blocked not in by_id:
            errors.append(f"{record['local_id']}: missing blocked issue {blocked}")
        elif record["local_id"] not in by_id[blocked].get("dependencies", []):
            errors.append(f"{record['local_id']}: inverse dependency relationship missing on {blocked}")
found_cycles = cycles(records)
for cycle in found_cycles:
    errors.append("cycle: " + " -> ".join(cycle))
print(json.dumps({"result": "PASS" if not errors else "FAIL", "issues": len(records), "cycles": len(found_cycles), "errors": errors}, indent=2, sort_keys=True))
raise SystemExit(1 if errors else 0)

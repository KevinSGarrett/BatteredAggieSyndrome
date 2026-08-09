from __future__ import annotations
from second_pass_hardening import validate_source_anchors, load_records, regenerate_source_manifests, import_lib
errors, rows = validate_source_anchors(repair=True)
regenerate_source_manifests(load_records())
import_lib().rebuild_file_manifest()
print(f'refs={len(rows)} errors={len(errors)}')
raise SystemExit(1 if errors else 0)

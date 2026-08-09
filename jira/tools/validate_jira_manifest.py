import sys
sys.dont_write_bytecode = True
import csv,hashlib
from pathlib import Path
JIRA_ROOT=Path(__file__).resolve().parents[1]
manifest=JIRA_ROOT/'validation'/'JIRA_FILE_MANIFEST.csv'
excluded={'validation/JIRA_FILE_MANIFEST.csv','validation/JIRA_FILE_HASHES.sha256'}
errors=[]
if not manifest.exists():
    errors.append('missing Jira file manifest')
    rows=[]
else:
    with manifest.open(encoding='utf-8',newline='') as f: rows=list(csv.DictReader(f))
    seen=set()
    for row in rows:
        rel=row['path'];seen.add(rel);p=JIRA_ROOT/rel
        if not p.exists(): errors.append(f'missing {rel}')
        elif p.stat().st_size!=int(row['bytes']): errors.append(f'size mismatch {rel}')
        elif hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']: errors.append(f'hash mismatch {rel}')
    expected={p.relative_to(JIRA_ROOT).as_posix() for p in JIRA_ROOT.rglob('*') if p.is_file() and p.relative_to(JIRA_ROOT).as_posix() not in excluded}
    for rel in sorted(expected-seen): errors.append(f'unrepresented {rel}')
    for rel in sorted(seen-expected): errors.append(f'extra {rel}')
print(f"Jira file manifest: {'PASS' if not errors else 'FAIL'} | files={len(rows)} errors={len(errors)}")
for e in errors: print('ERROR:',e)
raise SystemExit(1 if errors else 0)

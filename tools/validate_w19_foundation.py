from __future__ import annotations
from pathlib import Path
import csv, json, argparse

def validate(root:Path):
    findings=[]
    required=['src/aggie_analytics/data/adapters.py','src/aggie_analytics/data/snapshots.py','src/aggie_analytics/entities/resolution.py','src/aggie_analytics/temporal/state.py','src/aggie_analytics/features/factory.py','tests/test_w19_foundation.py','docs/101_W19_FOUNDATION_IMPLEMENTATION.md']
    for rel in required:
        if not (root/rel).exists(): findings.append(f'missing:{rel}')
    with (root/'governance/IMPLEMENTATION_WBS.csv').open(encoding='utf-8', newline='') as fh:
        rows={r['task_id']:r for r in csv.DictReader(fh)}
    for tid in ['TASK-041','TASK-042','TASK-043','TASK-044','TASK-045','TASK-046']:
        if rows.get(tid,{}).get('status')!='DONE': findings.append(f'{tid}:not_done')
    state=(root/'governance/CURRENT_STATE.yaml').read_text(encoding='utf-8')
    current=None
    for line in state.splitlines():
        if line.startswith('current_wave:'):
            current=line.split(':',1)[1].strip(); break
    try:
        if current is None or int(current[1:]) < 19: findings.append('current_state:pre_w19')
    except (ValueError,TypeError):
        findings.append('current_state:invalid_wave')
    return findings
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',type=Path,default=Path.cwd()); a=ap.parse_args(); f=validate(a.repo_root.resolve());
    if f: raise SystemExit('FAIL: '+'; '.join(f))
    print('PASS: W19 foundation implementation gate')

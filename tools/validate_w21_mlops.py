from __future__ import annotations
from pathlib import Path
import argparse,csv,json

DONE=[f'TASK-{i:03d}' for i in range(146,152)]
REQUIRED=[
 'src/aggie_analytics/orchestration/contracts.py','src/aggie_analytics/orchestration/checkpoints.py',
 'src/aggie_analytics/orchestration/weekly.py','src/aggie_analytics/orchestration/promotion.py',
 'src/aggie_analytics/orchestration/publication.py','src/aggie_analytics/orchestration/postmortem.py',
 'tests/test_w21_weekly_mlops.py','docs/105_W21_AUTONOMOUS_WEEKLY_MLOPS.md','docs/106_W21_IMPLEMENTATION_INVENTORY.md',
 'governance/W21_ADAPTIVE_REVIEW.md','governance/W21_VALIDATION_REPORT.md']

def validate(root:Path):
    findings=[]
    for rel in REQUIRED:
        if not (root/rel).exists(): findings.append('missing:'+rel)
    with (root/'governance/IMPLEMENTATION_WBS.csv').open(encoding='utf-8',newline='') as handle:
        rows={r['task_id']:r for r in csv.DictReader(handle)}
    for tid in DONE:
        if rows.get(tid,{}).get('status')!='DONE': findings.append(f'{tid}:not_done')
    state=(root/'governance/CURRENT_STATE.yaml').read_text(encoding='utf-8')
    current=None
    for line in state.splitlines():
        if line.startswith('current_wave:'):
            current=line.split(':',1)[1].strip(); break
    try:
        current_number = int(current[1:]) if current is not None else None
        if current_number is None or current_number < 21: findings.append('current_state:pre_w21')
        elif current_number == 21 and rows.get('TASK-152',{}).get('status')!='READY': findings.append('TASK-152:not_ready_for_w22')
        elif current_number > 21 and rows.get('TASK-152',{}).get('status')!='DONE': findings.append('TASK-152:not_done_after_w21')
    except (ValueError,TypeError):
        findings.append('current_state:invalid_wave')
    for needle in ('w21_weekly_mlops_gate: CLEARED_W21_FUNCTIONAL_STARTER','protected_results_exposed_to_research_w21: false','trained_model_metrics_claimed_w21: false'):
        if needle not in state: findings.append('current_state_missing:'+needle)
    with (root/'governance/ADR_INDEX.csv').open(encoding='utf-8',newline='') as handle:
        adr={r['adr_id'] for r in csv.DictReader(handle)}
    for a in ('ADR-326','ADR-327','ADR-328','ADR-329','ADR-330'):
        if a not in adr: findings.append('missing:'+a)
    return findings

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',type=Path,default=Path.cwd()); a=ap.parse_args(); f=validate(a.repo_root.resolve())
    if f: raise SystemExit('FAIL: '+'; '.join(f))
    print('PASS: W21 autonomous weekly MLOps functional-starter gate')

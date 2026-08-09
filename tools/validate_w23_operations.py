from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
sys.dont_write_bytecode=True

def _rows(path):
    with path.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))

def validate(root:Path):
    required=[
      '.github/workflows/ci.yml','.github/workflows/security.yml','requirements/product.lock',
      'src/aggie_analytics/operations/observability.py','src/aggie_analytics/operations/environment.py',
      'src/aggie_analytics/operations/benchmark.py','src/aggie_analytics/operations/backup.py',
      'src/aggie_analytics/operations/retention.py','tests/test_w23_operations.py',
      'docs/operations/CI_SECURITY_SUPPLY_CHAIN.md','docs/operations/OBSERVABILITY.md',
      'docs/operations/BACKUP_RESTORE_RETENTION_RUNBOOK.md','docs/operations/TARGET_HARDWARE_BENCHMARK.md',
      'governance/W23_NON_TARGET_BENCHMARK_SMOKE.json'
    ]
    findings=[]
    for rel in required:
        if not (root/rel).is_file():findings.append(f'missing {rel}')
    tasks={r['task_id']:r for r in _rows(root/'governance/IMPLEMENTATION_WBS.csv')}
    for tid in ('TASK-158','TASK-159','TASK-160','TASK-162'):
        if tasks.get(tid,{}).get('status')!='DONE':findings.append(f'{tid} not DONE')
    if tasks.get('TASK-161',{}).get('status')!='BLOCKED_TARGET_HARDWARE':findings.append('TASK-161 must remain target-hardware blocked in this checkpoint')
    if tasks.get('TASK-163',{}).get('status')!='BLOCKED_AC038_TARGET_HARDWARE':findings.append('TASK-163 must remain blocked by AC-038')
    b=json.loads((root/'governance/W23_NON_TARGET_BENCHMARK_SMOKE.json').read_text(encoding='utf-8'))
    if b.get('authoritative_for_thr_011_012') is not False or b.get('target_match') is not False:findings.append('non-target smoke artifact is mislabeled authoritative')
    req={r['requirement_id'] for r in _rows(root/'governance/REQUIREMENTS_INDEX.csv')}
    adr={r['adr_id'] for r in _rows(root/'governance/ADR_INDEX.csv')}
    if not {f'REQ-{i:03d}' for i in range(730,737)}.issubset(req):findings.append('W23 requirements incomplete')
    if not {f'ADR-{i:03d}' for i in range(336,341)}.issubset(adr):findings.append('W23 ADRs incomplete')
    return findings,b

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,default=Path.cwd());ap.add_argument('--allow-target-benchmark-pending',action='store_true');a=ap.parse_args()
    f,b=validate(a.repo_root.resolve())
    if f:
      print(f'FAIL: {len(f)} W23 finding(s)');[print('-',x) for x in f];return 1
    if not b['authoritative_for_thr_011_012']:
      msg='IMPLEMENTATION PASS / RELEASE BLOCKED: AC-038 awaits representative target-hardware benchmark; THR-011/012 remain TBD'
      print(msg); return 0 if a.allow_target_benchmark_pending else 2
    print('PASS: W23 local production operations gate'); return 0
if __name__=='__main__':raise SystemExit(main())

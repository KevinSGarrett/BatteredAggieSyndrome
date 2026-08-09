from __future__ import annotations
import csv,json,sys,tempfile
from pathlib import Path
sys.dont_write_bytecode=True
if __package__ in {None,''}: sys.path.insert(0,str(Path(__file__).resolve().parents[1])); sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))

from aggie_analytics.readiness import run_synthetic_e2e,run_leakage_battery,replay_readiness_report


def _rows(path:Path):
    with path.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))

def validate(root:Path)->list[str]:
    root=Path(root).resolve(); g=root/'governance'; findings=[]
    required=[
      'src/aggie_analytics/readiness/__init__.py','src/aggie_analytics/readiness/e2e.py',
      'tests/test_w24_readiness.py','tools/bootstrap_readiness.py','scripts/bootstrap_readiness.ps1',
      'docs/readiness/W24_END_TO_END_READINESS.md','docs/data_research/w24/SOURCE_REFRESH_DELTA.csv',
      'docs/data_research/w24/SOURCE_RESEARCH_LOG.csv','docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md',
      'docs/architecture/W24_FINAL_ARCHITECTURE_CHALLENGE.md','governance/W24_ADAPTIVE_REVIEW.md'
    ]
    for rel in required:
        if not (root/rel).is_file():findings.append(f'missing {rel}')
    tasks={r['task_id']:r for r in _rows(g/'IMPLEMENTATION_WBS.csv')}
    for tid in ('TASK-173','TASK-174','TASK-175','TASK-176','TASK-177','TASK-178','TASK-199'):
        if tasks.get(tid,{}).get('status')!='DONE': findings.append(f'{tid} not DONE')
    if tasks.get('TASK-161',{}).get('status')!='BLOCKED_TARGET_HARDWARE':findings.append('TASK-161 target benchmark blocker was lost')
    if tasks.get('TASK-163',{}).get('status')!='BLOCKED_AC038_TARGET_HARDWARE':findings.append('TASK-163 AC-038 blocker was lost')
    state=(g/'CURRENT_STATE.yaml').read_text(encoding='utf-8')
    current_wave='W24'
    for line in state.splitlines():
        if line.startswith('current_wave:'):
            current_wave=line.split(':',1)[1].strip().strip("'\"")
            break
    expected_179='READY' if current_wave=='W24' else 'DONE'
    if tasks.get('TASK-179',{}).get('status')!=expected_179:
        findings.append(f'TASK-179 must be {expected_179} for repository state {current_wave}')
    req={r['requirement_id'] for r in _rows(g/'REQUIREMENTS_INDEX.csv')}
    adr={r['adr_id'] for r in _rows(g/'ADR_INDEX.csv')}
    if not {f'REQ-{i:03d}' for i in range(737,746)}.issubset(req):findings.append('W24 requirements incomplete')
    if not {f'ADR-{i:03d}' for i in range(341,347)}.issubset(adr):findings.append('W24 ADRs incomplete')
    if current_wave=='W24':
        required_state=('current_wave: W24','next_wave: W25','w23_target_hardware_blocker_carried: true','w25_allowed: true')
    else:
        required_state=('current_wave: W25','next_wave: CODEX_IMPLEMENTATION_HANDOFF','target_benchmark_authoritative: false')
    for phrase in required_state:
        if phrase not in state:findings.append(f'CURRENT_STATE missing {phrase}')
    refresh=_rows(root/'docs/data_research/w24/SOURCE_REFRESH_DELTA.csv') if (root/'docs/data_research/w24/SOURCE_REFRESH_DELTA.csv').is_file() else []
    ids={r.get('source_id') for r in refresh}
    if not {'SRC-061','SRC-062'}.issubset(ids):findings.append('W24 source additions missing SRC-061/SRC-062')
    try:
        with tempfile.TemporaryDirectory() as td:
            e2e=run_synthetic_e2e(Path(td)/'e2e')
            replay=replay_readiness_report(Path(td)/'replay')
        leak=run_leakage_battery()
        if not all(e2e['checks'].values()):findings.append('synthetic E2E checks not all true')
        if replay['empirical_historical_replay_completed'] is not False:findings.append('replay readiness overclaims empirical replay')
        if not leak['all_expected']:findings.append('leakage battery failed')
    except Exception as exc:
        findings.append(f'executable readiness battery failed: {type(exc).__name__}: {exc}')
    return findings

def main()->int:
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,default=Path.cwd());args=ap.parse_args()
    f=validate(args.repo_root)
    if f:
        print(f'FAIL: {len(f)} W24 finding(s)');[print('-',x) for x in f];return 1
    print('PASS: W24 synthetic E2E/replay readiness, leakage, source refresh, architecture challenge and carried-blocker controls')
    return 0
if __name__=='__main__':raise SystemExit(main())

from __future__ import annotations
from pathlib import Path
import argparse, csv, json

DONE=['TASK-083','TASK-084','TASK-085','TASK-086','TASK-087','TASK-111','TASK-112','TASK-113','TASK-114','TASK-115','TASK-140','TASK-141','TASK-142','TASK-143','TASK-144','TASK-145']
REQUIRED=[
 'src/aggie_analytics/modeling/runtime.py','src/aggie_analytics/modeling/baselines.py','src/aggie_analytics/modeling/joint.py',
 'src/aggie_analytics/modeling/calibration.py','src/aggie_analytics/modeling/ensemble.py','src/aggie_analytics/modeling/registry.py',
 'src/aggie_analytics/modeling/forecast.py','src/aggie_analytics/tamu/runtime.py','src/aggie_analytics/bas/runtime.py',
 'src/aggie_analytics/player_intelligence/advanced_state.py','tests/test_w20_model_starter.py','docs/103_W20_MODEL_CALIBRATION_BAS_IMPLEMENTATION.md']

def validate(root:Path):
 findings=[]
 for rel in REQUIRED:
  if not (root/rel).exists(): findings.append('missing:'+rel)
 with (root/'governance/IMPLEMENTATION_WBS.csv').open(encoding='utf-8',newline='') as handle:
  rows={r['task_id']:r for r in csv.DictReader(handle)}
 for tid in DONE:
  if rows.get(tid,{}).get('status')!='DONE': findings.append(f'{tid}:not_done')
 state=(root/'governance/CURRENT_STATE.yaml').read_text(encoding='utf-8')
 if 'w20_model_calibration_bas_gate: CLEARED_W20_FUNCTIONAL_STARTER' not in state: findings.append('current_state:w20_gate_missing')
 if 'trained_model_metrics_claimed_w20: false' not in state and 'trained_model_metrics_claimed_w21: false' not in state: findings.append('honesty_flag:missing')
 return findings
if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',type=Path,default=Path.cwd()); a=ap.parse_args(); f=validate(a.repo_root.resolve())
 if f: raise SystemExit('FAIL: '+'; '.join(f))
 print('PASS: W20 model/calibration/BAS starter integration gate')

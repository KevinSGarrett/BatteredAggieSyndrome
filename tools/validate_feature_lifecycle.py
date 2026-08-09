from __future__ import annotations
import argparse,csv,json,sys
sys.dont_write_bytecode=True
from pathlib import Path

def rows(p):
    with p.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))

def validate(root:Path):
    out=[]; cfg=json.loads((root/'configs/feature_lifecycle_registry.json').read_text())
    raw=rows(root/'governance/RAW_FIELD_REGISTRY.csv'); seeds=rows(root/'governance/FEATURE_CANDIDATE_SEEDS.csv')
    trans=rows(root/'governance/FEATURE_TRANSFORMATION_CATALOG.csv'); screen=rows(root/'governance/FEATURE_SCREENING_METHODS.csv')
    states=rows(root/'governance/FEATURE_LIFECYCLE_STATES.csv'); transitions=rows(root/'governance/FEATURE_LIFECYCLE_TRANSITIONS.csv')
    fam=rows(root/'governance/FEATURE_FAMILY_EXPERIMENT_PLAN.csv'); targets=rows(root/'governance/TARGET_FEATURE_POLICY.csv')
    decisions=rows(root/'governance/FEATURE_LIFECYCLE_DECISION_LOG.csv')
    allowed={r['raw_field_id'] for r in raw if r['w10_candidate_experiment_allowed']=='true'}
    if len(raw)!=1197:out.append('raw W09 field baseline changed')
    if len(seeds)!=cfg['counts']['candidate_seeds'] or len(seeds)!=736:out.append('candidate seed count mismatch')
    if {r['raw_field_id'] for r in seeds}!=allowed:out.append('candidate seeds differ from W09 handoff-permitted set')
    if any(r['initial_lifecycle_state']!='EXPERIMENTAL' or r['production_approved']!='false' for r in seeds):out.append('W10 candidate seed prematurely promoted')
    if len(fam)!=cfg['counts']['candidate_families'] or any(r['initial_lifecycle_state']!='EXPERIMENTAL' for r in fam):out.append('family plan premature lifecycle state')
    if len(trans)!=cfg['counts']['transform_templates']:out.append('transform count mismatch')
    if any(r['same_game_input_allowed']!='false' for r in trans):out.append('transform allows same-game pregame input')
    if len(screen)!=cfg['counts']['screening_methods']:out.append('screening count mismatch')
    if {r['state'] for r in states}!={'CORE','SUPPORTED','CONDITIONAL','EXPERIMENTAL','REJECTED','BANNED'}:out.append('lifecycle state set mismatch')
    if any(r['automatic']!='false' for r in transitions):out.append('automatic lifecycle transition enabled')
    if decisions:out.append('W10 contains empirical lifecycle decisions despite no real-data evaluation')
    if any(r['target_policy']!='TARGET_SPECIFIC_EVALUATION_REQUIRED' for r in seeds):out.append('candidate target-specific policy missing')
    if not any(r['candidate_lane']=='MARKET_AUGMENTED_ONLY' for r in seeds):out.append('market lane isolation absent')
    thr=rows(root/'governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv'); t={r['threshold_id']:r for r in thr}.get('THR-007')
    if not t or t['status'] not in {'TBD_BY_EVIDENCE','METHOD_FROZEN_VALUE_PENDING_DEVELOPMENT_EVIDENCE'} or t['value'].strip():out.append('THR-007 numeric value was fabricated')
    wbs=rows(root/'governance/IMPLEMENTATION_WBS.csv'); by={r['task_id']:r for r in wbs}
    for tid in [f'TASK-{i:03d}' for i in range(24,30)]:
        if by.get(tid,{}).get('status')!='DONE':out.append(f'{tid} not DONE')
    if by.get('TASK-030',{}).get('status') not in {'READY','DONE'}:out.append('TASK-030 neither READY nor DONE')
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,default=Path.cwd());a=ap.parse_args();f=validate(a.repo_root.resolve())
    if f:
        print(f'FAIL: {len(f)} feature-lifecycle finding(s)');[print('-',x) for x in f];return 1
    print('PASS: W10 PIT-safe transforms, candidate seeds, screening, lifecycle and W11 handoff contracts')
    return 0
if __name__=='__main__':raise SystemExit(main())

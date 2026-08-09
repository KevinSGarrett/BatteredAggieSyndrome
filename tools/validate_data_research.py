from __future__ import annotations
import argparse,csv,json,re
from pathlib import Path

def rows(path:Path):
    with path.open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))

def validate(root:Path):
    base=root/'docs/data_research/w06'; g=root/'governance'; f=[]
    required=['DATA_UNIVERSE_MASTER.csv','SOURCE_RESEARCH_LOG.csv','DATA_DOMAIN_COVERAGE_MATRIX.csv','DATASET_ENDPOINT_COLUMN_INVENTORY.csv','POINT_IN_TIME_FEASIBILITY_MATRIX.csv','SOURCE_ACCESS_LICENSE_MATRIX.csv','SOURCE_REDUNDANCY_MAP.csv','SOURCE_PRIORITY_DECISIONS.md','DATA_ACQUISITION_PLAN.md','DATA_MISSINGNESS_STRATEGY.md','DATA_SOURCE_RISK_REGISTER.csv','DATA_RESEARCH_FINDINGS.md','WAVE_06_ARCHITECTURE_IMPACT.md','DATA_RESEARCH_METHOD.md','RESEARCH_EVIDENCE_INDEX.csv']
    for name in required:
        if not (base/name).is_file():f.append(f'missing W06 artifact {name}')
    if f:return f
    src=rows(base/'DATA_UNIVERSE_MASTER.csv'); research=rows(base/'SOURCE_RESEARCH_LOG.csv'); dom=rows(base/'DATA_DOMAIN_COVERAGE_MATRIX.csv'); inv=rows(base/'DATASET_ENDPOINT_COLUMN_INVENTORY.csv'); pit=rows(base/'POINT_IN_TIME_FEASIBILITY_MATRIX.csv'); lic=rows(base/'SOURCE_ACCESS_LICENSE_MATRIX.csv'); red=rows(base/'SOURCE_REDUNDANCY_MAP.csv'); evid=rows(base/'RESEARCH_EVIDENCE_INDEX.csv')
    ids=[r['source_id'] for r in src]
    expected=[f'SRC-{i:03d}' for i in range(1,len(ids)+1)]
    if ids!=expected:f.append('source IDs must be unique/sequential')
    if len(src)<50:f.append('source universe too small for comprehensive practical W06 coverage')
    if len(dom)<40:f.append('domain coverage matrix too small')
    if len(inv)<100:f.append('endpoint/dataset inventory did not preserve/extend recon detail')
    if len(research)<20:f.append('research log lacks multi-pass depth')
    if len(evid)<20:f.append('research evidence index lacks primary/provider evidence breadth')
    passes={r['pass'].split('_',1)[0] if '_' in r['pass'] else r['pass'] for r in research}
    # Explicit A-J pass evidence; research labels may be A_DOMAIN, B_SOURCE etc.
    letters={r['pass'][:1] for r in research if r['pass']}
    if not set('ABCDEFGHIJ').issubset(letters):f.append(f'missing research passes {sorted(set("ABCDEFGHIJ")-letters)}')
    sid=set(ids)
    if {r['source_id'] for r in pit}!=sid:f.append('PIT matrix must cover source universe exactly')
    if {r['source_id'] for r in lic}!=sid:f.append('access/license matrix must cover source universe exactly')
    for r in src:
        for k in ['owner','dataset','domain','url','access_method','historical_coverage','point_in_time_feasibility','acquisition_priority','fallback_source','project_role','inclusion_status']:
            if not r.get(k,'').strip():f.append(f"{r['source_id']} missing {k}")
    required_source_tokens=['Southeastern Conference','Big Ten','Atlantic Coast Conference','Big 12','HRRR','NCAA Statistics','NAIA','NJCAA','The Odds API']
    blob='\n'.join((r['owner']+' '+r['dataset']) for r in src)
    for tok in required_source_tokens:
        if tok.lower() not in blob.lower():f.append(f'missing material W06 source class: {tok}')
    domains='\n'.join(r['domain'] for r in dom).lower()
    domain_groups=[('availability',['availability']),('weather',['weather']),('markets',['market']),('lower division',['fcs','d-ii','d-iii','naia','njcaa','lower-division']),('rules',['rule era','regulatory']),('coaching',['coach','coordinator']),('resources',['resource','financial']),('transfers',['transfer'])]
    for label,toks in domain_groups:
        if not any(tok in domains for tok in toks):f.append(f'missing W06 domain coverage: {label}')
    impact=(base/'WAVE_06_ARCHITECTURE_IMPACT.md').read_text(encoding='utf-8')
    if 'KEEP the W03 offline-first modular-monolith' not in impact:f.append('architecture impact does not record W03 keep/revise decision')
    plan=json.loads((root/'configs/implementation_plan.json').read_text(encoding='utf-8'))
    version=str(plan.get('version',''))
    m=re.match(r'^w(\d{2})',version)
    if not m or int(m.group(1))<6:f.append('implementation plan does not preserve W06-or-later replan state')
    policy=json.loads((root/'configs/backlog_policy.json').read_text(encoding='utf-8'))
    if policy.get('w06_replan_status')!='CLEARED_W06':f.append('W06 replan not cleared')
    tasks=rows(g/'IMPLEMENTATION_WBS.csv')
    t={r['task_id']:r for r in tasks}
    if t.get('TASK-006',{}).get('status') not in {'DONE','COMPLETE_W06','DONE_W06'}:f.append('TASK-006 replan gate not complete')
    if t.get('TASK-007',{}).get('status') not in {'READY','DONE','COMPLETE_W07','DONE_W07'}:f.append('TASK-007 must be READY or complete after W06 gate')
    if len(tasks)<201:f.append('W06 task additions missing')
    return sorted(set(f))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,default=Path.cwd());a=ap.parse_args();findings=validate(a.repo_root.resolve())
    if findings:
        print(f'FAIL: {len(findings)} W06 data-research finding(s)');[print('-',x) for x in findings];return 1
    print('PASS: W06 source universe, A-J research method, PIT/access matrices, evidence breadth and replan gate')
    return 0
if __name__=='__main__':raise SystemExit(main())

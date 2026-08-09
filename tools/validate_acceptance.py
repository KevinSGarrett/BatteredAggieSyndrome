from __future__ import annotations
import argparse, csv, json, re, sys
from pathlib import Path


def _csv(path: Path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _seq(ids, prefix):
    nums=[]
    for value in ids:
        m=re.fullmatch(rf"{re.escape(prefix)}-(\d{{3}})", value)
        if not m: return False
        nums.append(int(m.group(1)))
    return nums == list(range(1, len(nums)+1))


def validate(root: Path) -> list[str]:
    g=root/"governance"
    req=_csv(g/"REQUIREMENTS_INDEX.csv")
    adr=_csv(g/"ADR_INDEX.csv")
    risk=_csv(g/"RISK_REGISTER.csv")
    controls=_csv(g/"ACCEPTANCE_CONTROL_CATALOG.csv")
    matrix=_csv(g/"REQUIREMENT_ACCEPTANCE_MATRIX.csv")
    amap=_csv(g/"ADR_ACCEPTANCE_TRACEABILITY.csv")
    rmap=_csv(g/"RISK_ACCEPTANCE_TRACEABILITY.csv")
    thresholds=_csv(g/"ACCEPTANCE_THRESHOLD_REGISTRY.csv")
    registry=json.loads((root/"configs/acceptance_registry.json").read_text(encoding="utf-8"))
    findings=[]
    def exact(label, left, right):
        if set(left)!=set(right): findings.append(f"{label} coverage mismatch missing={sorted(set(left)-set(right))[:5]} extra={sorted(set(right)-set(left))[:5]}")
    req_ids=[x['requirement_id'] for x in req]; adr_ids=[x['adr_id'] for x in adr]; risk_ids=[x['risk_id'] for x in risk]
    cids=[x['control_id'] for x in controls]; tids=[x['threshold_id'] for x in thresholds]
    if len(cids)!=len(set(cids)) or not _seq(cids,'AC'): findings.append('acceptance control IDs are not unique/sequential')
    if len(tids)!=len(set(tids)) or not _seq(tids,'THR'): findings.append('threshold IDs are not unique/sequential')
    exact('requirement acceptance', req_ids, [x['requirement_id'] for x in matrix])
    exact('ADR acceptance', adr_ids, [x['adr_id'] for x in amap])
    exact('risk acceptance', risk_ids, [x['risk_id'] for x in rmap])
    known_c=set(cids); known_t=set(tids)
    for label, rows, key in [('requirement',matrix,'acceptance_control_ids'),('adr',amap,'acceptance_control_ids'),('risk',rmap,'acceptance_control_ids')]:
        for row in rows:
            refs={x for x in row[key].split(';') if x}
            bad=refs-known_c
            if bad: findings.append(f"{label} unknown controls {sorted(bad)}")
    for c in controls:
        refs={x for x in c['threshold_refs'].split(';') if x}
        bad=refs-known_t
        if bad: findings.append(f"control {c['control_id']} unknown thresholds {sorted(bad)}")
    for t in thresholds:
        if t['status'].startswith('TBD_') and t['value'].strip():
            findings.append(f"{t['threshold_id']} is TBD but has a value")
    protected=set(registry['protected_control_ids'])
    if protected-known_c: findings.append('registry references unknown protected controls')
    ctl={x['control_id']:x for x in controls}
    for cid in protected:
        if str(ctl[cid]['release_blocking']).lower() not in {'true','1','yes'}:
            findings.append(f"protected control {cid} is not release_blocking")
    mm={x['requirement_id']:x for x in matrix}
    for r in req:
        m=mm[r['requirement_id']]
        if r['constraint_class']=='C' and 'CURRENTLY_VERIFIED_W04' in m['acceptance_state']:
            findings.append(f"Level-C {r['requirement_id']} incorrectly marked currently verified")
        if r['constraint_class']=='A' and r['status']=='ACTIVE' and not m['acceptance_control_ids']:
            findings.append(f"active Level-A {r['requirement_id']} has no acceptance control")
    reg_c={x['control_id'] for x in registry['controls']}
    if reg_c!=known_c: findings.append('JSON registry control set differs from CSV catalog')
    return findings


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',type=Path,default=Path.cwd()); args=ap.parse_args()
    findings=validate(args.repo_root.resolve())
    if findings:
        print(f"FAIL: {len(findings)} acceptance finding(s)")
        for x in findings: print('-',x)
        return 1
    print('PASS: acceptance controls, thresholds, requirement/ADR/risk mappings and protected semantics')
    return 0

if __name__=='__main__': raise SystemExit(main())

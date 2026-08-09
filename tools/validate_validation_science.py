from __future__ import annotations
import argparse,csv,json,re,sys
from pathlib import Path

def _rows(path: Path):
    with path.open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def validate(root: Path) -> list[str]:
    g=root/"governance"
    findings=[]
    reg=json.loads((root/"configs/validation_science_registry.json").read_text(encoding="utf-8"))
    if reg.get("maturity")!="PROTECTED_VALIDATION_AND_PROMOTION_PROTOCOLS_ONLY":
        findings.append("unexpected W17 maturity")
    sp=reg["split_protocol"]
    if sp["protected_holdout"] != {"season_start":2024,"season_end":2025}:
        findings.append("protected holdout is not frozen to 2024-2025")
    if sp["forward_shadow"].get("season_start")!=2026:
        findings.append("forward shadow does not begin in 2026")
    if not sp.get("canonical_game_atomic") or not sp.get("mirrored_rows_same_split"):
        findings.append("canonical-game split protection missing")
    if sp.get("protected_results_for_tuning") is not False:
        findings.append("protected results may be used for tuning")
    if reg.get("protected_empirical_results_inspected_w17") is not False:
        findings.append("W17 claims protected empirical result inspection")
    if reg.get("trained_model_metrics_claimed_w17") is not False:
        findings.append("W17 claims trained metrics")
    if reg.get("selected_model_family_w17") is not False:
        findings.append("W17 selected a model family")

    splits=_rows(g/"PROTECTED_SPLIT_REGISTRY.csv")
    sid={r["split_id"]:r for r in splits}
    for needed in {"SPLIT-DEV-HIST","SPLIT-DEV-SEL","SPLIT-PROTECTED","SPLIT-FORWARD"}:
        if needed not in sid: findings.append(f"missing split {needed}")
    if sid.get("SPLIT-PROTECTED",{}).get("tuning_allowed")!="false":
        findings.append("protected split allows tuning")
    if sid.get("SPLIT-PROTECTED",{}).get("threshold_setting_allowed")!="false":
        findings.append("protected split allows threshold setting")

    metrics=_rows(g/"METRIC_REGISTRY.csv")
    mids=[r["metric_id"] for r in metrics]
    if mids != [f"MTR-{i:03d}" for i in range(1,len(metrics)+1)]:
        findings.append("metric IDs not sequential")
    names={r["metric"] for r in metrics}
    for needed in {"Brier score","Log loss","MAE","RMSE"}:
        if needed not in names: findings.append(f"missing metric {needed}")

    thrs=_rows(g/"ACCEPTANCE_THRESHOLD_REGISTRY.csv")
    needed_thrs={"THR-001","THR-002","THR-003","THR-004","THR-005","THR-006","THR-007","THR-014","THR-015"}
    for r in thrs:
        if r["threshold_id"] in needed_thrs:
            if r["value"].strip():
                findings.append(f"{r['threshold_id']} has fabricated W17 value")
            if r["status"]!="METHOD_FROZEN_VALUE_PENDING_DEVELOPMENT_EVIDENCE":
                findings.append(f"{r['threshold_id']} method status not frozen")
    pre=_rows(g/"THRESHOLD_PRECOMMITMENT_REGISTRY.csv")
    if {r["threshold_id"] for r in pre} != needed_thrs:
        findings.append("threshold precommitment set mismatch")
    if any(r["protected_results_allowed"]!="false" for r in pre):
        findings.append("protected results allowed for threshold setting")
    if any(r["fail_closed_if_blank"]!="true" for r in pre):
        findings.append("blank threshold does not fail closed")

    states={r["state"] for r in _rows(g/"PROMOTION_DECISION_STATES.csv")}
    for needed in {"BLOCKED_THRESHOLD_UNSET","PROTECTED_READY","REJECT","INCONCLUSIVE","PROMOTE"}:
        if needed not in states: findings.append(f"missing promotion state {needed}")

    wbs=_rows(g/"IMPLEMENTATION_WBS.csv")
    t={r["task_id"]:r for r in wbs}
    w17={"TASK-039","TASK-040","TASK-109","TASK-110","TASK-126","TASK-127","TASK-128","TASK-129","TASK-130","TASK-131","TASK-132","TASK-133"}
    for tid in w17:
        if t.get(tid,{}).get("status")!="DONE":
            findings.append(f"{tid} not DONE")
    if t.get("TASK-134",{}).get("status") not in {"READY","DONE"}:
        findings.append("TASK-134 neither READY nor later DONE")

    ctrls={r["control_id"]:r for r in _rows(g/"ACCEPTANCE_CONTROL_CATALOG.csv")}
    for cid in [f"AC-{i:03d}" for i in range(163,177)]:
        if cid not in ctrls: findings.append(f"missing W17 acceptance control {cid}")

    return findings

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo-root",type=Path,default=Path.cwd())
    root=ap.parse_args().repo_root.resolve()
    findings=validate(root)
    if findings:
        print(f"FAIL: {len(findings)} W17 validation-science finding(s)")
        for x in findings: print("-",x)
        return 1
    print("PASS: W17 protected split/metrics/threshold/promotion protocols are frozen with no fabricated empirical values")
    return 0

if __name__=="__main__":
    raise SystemExit(main())

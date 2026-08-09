from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
def rows(p:Path):
    with p.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def validate(root:Path)->list[str]:
    g=root/"governance";out=[];cfg=json.loads((root/"configs/bas_science_registry.json").read_text())
    labels=rows(g/"BAS_LABEL_CONTRACT.csv");xf=rows(g/"BAS_EXPECTATION_CROSSFIT_CONTRACTS.csv");anti=rows(g/"BAS_ANTI_CIRCULARITY_RULES.csv")
    base=rows(g/"BAS_GENERAL_FBS_BASELINE_CONTRACTS.csv");ex=rows(g/"BAS_AGGIE_EXCESS_TEST_PLAN.csv");comp=rows(g/"BAS_COMPONENT_CANDIDATES.csv")
    stab=rows(g/"BAS_REGIME_STABILITY_CALIBRATION_PLAN.csv");null=rows(g/"BAS_NULL_RESULT_POLICY.csv");gate=rows(g/"BAS_GATE_STATUS.csv")
    wbs=rows(g/"IMPLEMENTATION_WBS.csv");req=rows(g/"REQUIREMENTS_INDEX.csv");adr=rows(g/"ADR_INDEX.csv");risk=rows(g/"RISK_REGISTER.csv")
    ac=rows(g/"ACCEPTANCE_CONTROL_CATALOG.csv");hyp=rows(g/"HYPOTHESIS_LEDGER.csv");th=rows(g/"ACCEPTANCE_THRESHOLD_REGISTRY.csv");feats=rows(g/"FEATURE_CANDIDATE_SEEDS.csv")
    if cfg.get("version")!="w15-v1.0" or cfg.get("maturity")!="SCIENTIFIC_BAS_CONTRACTS_SYNTHETIC_ONLY":out.append("registry version/maturity")
    if cfg["primary_headline_definition"].get("headline_threshold_points")!=7 or cfg["primary_headline_definition"].get("severity_thresholds_points")!=[3,7,14,21]:out.append("headline/severity definition")
    for k in ["component_candidates_promoted_w15","aggie_excess_claimed_w15","significance_claimed_w15","effect_size_claimed_w15","thr_006_value_frozen_w15"]:
        if cfg["scientific_guards"].get(k) is not False:out.append(k)
    if cfg["scientific_guards"].get("null_result_must_be_reportable") is not True:out.append("null path")
    by={x["name"]:x for x in labels}
    if set(by)!={"performance_residual","bas_ge_3","bas_ge_7","bas_ge_14","bas_ge_21"}:out.append("label set")
    if by["bas_ge_7"]["headline"]!="true" or by["bas_ge_7"]["definition"]!="performance_residual <= -7":out.append("headline label")
    if any(x["protected"]!="true" for x in xf) or any(x["w15_status"]!="PROTECTED" for x in anti):out.append("crossfit/anti")
    if any(x["game_clustering"]!="canonical_game" for x in base):out.append("game clustering")
    if not any(x["test_id"]=="BAS-EX-008" and x["null_result_allowed"]=="true" for x in ex):out.append("null excess path")
    if any(x["production_selected_w15"]!="false" for x in comp):out.append("component promoted")
    if any(x["result_required_w15"]!="false" for x in stab):out.append("empirical result required W15")
    if len(null)<4 or any(x["protected"]!="true" for x in null):out.append("null policy")
    if len(gate)!=1 or gate[0]["status"]!="CLEARED_W15_CONTRACT_ONLY" or gate[0]["aggie_excess_claimed"]!="false":out.append("gate")
    task={x["task_id"]:x for x in wbs}
    for tid in [f"TASK-{i:03d}" for i in range(100,109)]:
        if task.get(tid,{}).get("status")!="DONE":out.append(f"{tid} not DONE")
    if task["TASK-109"]["status"] not in {"PLANNED","DONE"} or task["TASK-110"]["status"] not in {"PLANNED","DONE"}:out.append("W17 BAS task state invalid")
    if task["TASK-116"]["status"] not in {"READY","DONE"}:out.append("TASK-116 handoff invalid")
    if len(req)<528 or len(adr)<220 or len(risk)<211 or len(ac)<151:out.append("W15 governance minimum count")
    for hid in [f"HYP-{i:03d}" for i in range(47,54)]:
        h=[x for x in hyp if x["hypothesis_id"]==hid]
        if len(h)!=1 or h[0]["status"]!="PENDING":out.append(hid)
    t=next(x for x in th if x["threshold_id"]=="THR-006")
    if t["value"].strip() or t["status"] not in {"TBD_BY_EVIDENCE","METHOD_FROZEN_VALUE_PENDING_DEVELOPMENT_EVIDENCE"}:out.append("THR-006")
    if len(feats)!=736 or any(x["initial_lifecycle_state"]!="EXPERIMENTAL" or x["production_approved"]!="false" for x in feats):out.append("feature promotions")
    return out
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",type=Path,default=Path.cwd());a=ap.parse_args();f=validate(a.repo_root.resolve())
    if f:print(f"FAIL: {len(f)} W15 BAS finding(s)");[print("-",x) for x in f];return 1
    print("PASS: W15 scientific BAS label, cross-fit, anti-circularity, null-result and evaluation contracts");return 0
if __name__=="__main__":raise SystemExit(main())

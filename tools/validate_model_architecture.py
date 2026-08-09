
from __future__ import annotations
import argparse,csv,json
from pathlib import Path

def rows(p:Path):
    with p.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))

def validate(root:Path)->list[str]:
    g=root/"governance"; out=[]
    cfg=json.loads((root/"configs/model_architecture_registry.json").read_text(encoding="utf-8"))
    targets=rows(g/"MODEL_TARGET_CONTRACT.csv"); deriv=rows(g/"MODEL_DERIVATION_CONTRACT.csv")
    models=rows(g/"MODEL_ARCHITECTURE_CANDIDATES.csv"); joint=rows(g/"JOINT_SCORE_CANDIDATES.csv")
    bases=rows(g/"BASELINE_MODEL_CANDIDATES.csv"); scn=rows(g/"SIMULATION_SCENARIO_CONTRACTS.csv")
    unc=rows(g/"UNCERTAINTY_COMPONENTS.csv"); ood=rows(g/"OOD_DETECTION_CANDIDATES.csv")
    dis=rows(g/"MODEL_DISAGREEMENT_CONTRACTS.csv"); lanes=rows(g/"FORECAST_LANES.csv")
    mr=rows(g/"MARKET_LANE_RULES.csv"); gate=rows(g/"MODEL_ARCHITECTURE_GATE_STATUS.csv")
    wbs=rows(g/"IMPLEMENTATION_WBS.csv"); th=rows(g/"ACCEPTANCE_THRESHOLD_REGISTRY.csv")
    feats=rows(g/"FEATURE_CANDIDATE_SEEDS.csv")
    if cfg.get("version")!="w16-v1.0" or cfg.get("maturity")!="MODEL_ARCHITECTURE_AND_SIMULATION_CONTRACTS_SYNTHETIC_ONLY":
        out.append("registry version/maturity")
    if len(targets)!=14 or len(models)!=11 or len(joint)!=7 or len(bases)!=5: out.append("candidate/target counts")
    if any(x["production_selected_w16"]!="false" for x in models): out.append("model selected")
    if any(x["production_selected_w16"]!="false" for x in joint): out.append("joint family selected")
    if any(x["empirically_benchmarked_w16"]!="false" for x in bases): out.append("baseline empirically benchmarked")
    if any(x["w16_calibrated"]!="false" for x in unc): out.append("uncertainty calibrated")
    if any(x["production_selected_w16"]!="false" for x in ood+dis): out.append("OOD/disagreement selected")
    lane={x["name"]:x for x in lanes}
    if lane.get("PURE_FOOTBALL",{}).get("market_features_allowed")!="false": out.append("pure lane market contamination")
    if lane.get("MARKET_AUGMENTED",{}).get("market_features_allowed")!="true": out.append("market lane disabled")
    if len(mr)<5 or any(x["protected"]!="true" for x in mr): out.append("market rules")
    t={x["threshold_id"]:x for x in th}
    for tid in ("THR-014","THR-015"):
        if t[tid]["value"].strip() or t[tid]["status"] not in {"TBD_BY_EVIDENCE","METHOD_FROZEN_VALUE_PENDING_DEVELOPMENT_EVIDENCE"}: out.append(tid)
    tasks={x["task_id"]:x for x in wbs}
    w16=["TASK-036","TASK-037","TASK-038"]+[f"TASK-{i:03d}" for i in range(116,126)]+["TASK-196"]
    for tid in w16:
        if tasks.get(tid,{}).get("status")!="DONE": out.append(f"{tid} not DONE")
    if tasks.get("TASK-128",{}).get("status") not in {"READY","DONE"}: out.append("TASK-128 handoff invalid")
    if len(gate)!=1 or gate[0]["status"]!="CLEARED_W16_CONTRACT_ONLY": out.append("W16 gate")
    if gate and (gate[0]["selected_model_family"]!="false" or gate[0]["trained_model_metrics_claimed"]!="false"): out.append("empirical/winner gate")
    if len(feats)!=736 or any(x["initial_lifecycle_state"]!="EXPERIMENTAL" or x["production_approved"]!="false" for x in feats): out.append("feature promotions")
    bas_names={x["name"] for x in targets if x["target_id"] in {"TGT-010","TGT-011","TGT-012","TGT-013"}}
    if bas_names!={"bas_ge_3","bas_ge_7","bas_ge_14","bas_ge_21"}: out.append("BAS target semantics")
    if not any(x["candidate_id"]=="MOD-003" and x["mandatory_baseline"]=="true" for x in models): out.append("simple score baseline missing")
    if not any(x["lane_id"]=="LANE-004" for x in lanes): out.append("BAS scientific anchor lane missing")
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",type=Path,default=Path.cwd());a=ap.parse_args()
    f=validate(a.repo_root.resolve())
    if f:
        print(f"FAIL: {len(f)} W16 model-architecture finding(s)")
        [print("-",x) for x in f]
        return 1
    print("PASS: W16 model targets, coherent joint-score, baselines, simulation, uncertainty/OOD and market-lane contracts")
    return 0

if __name__=="__main__": raise SystemExit(main())

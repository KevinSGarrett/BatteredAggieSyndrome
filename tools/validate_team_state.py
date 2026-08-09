from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
sys.dont_write_bytecode=True

def rows(p:Path):
    with p.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))

def validate(root:Path)->list[str]:
    out=[]
    cfg=json.loads((root/"configs/team_state_registry.json").read_text(encoding="utf-8"))
    comps=rows(root/"governance/TEAM_STATE_COMPONENTS.csv")
    priors=rows(root/"governance/TEAM_STATE_PRIOR_COMPONENTS.csv")
    weights=rows(root/"governance/HISTORICAL_WEIGHTING_CANDIDATES.csv")
    regimes=rows(root/"governance/REGIME_SIMILARITY_FACTORS.csv")
    cps=rows(root/"governance/CHANGE_POINT_CANDIDATES.csv")
    blends=rows(root/"governance/EARLY_SEASON_BLEND_CANDIDATES.csv")
    hier=rows(root/"governance/OPPONENT_STRENGTH_HIERARCHY.csv")
    trans=rows(root/"governance/LOWER_DIVISION_TRANSLATION_CONTRACTS.csv")
    unc=rows(root/"governance/TEAM_STATE_UNCERTAINTY_CATALOG.csv")
    compare=rows(root/"governance/TEAM_STATE_COMPARISON_PLAN.csv")
    gate=rows(root/"governance/TEAM_STATE_GATE_STATUS.csv")
    wbs=rows(root/"governance/IMPLEMENTATION_WBS.csv")
    lifecycle=rows(root/"governance/FEATURE_CANDIDATE_SEEDS.csv")

    if cfg.get("version")!="w11-v1.0":out.append("team-state registry version mismatch")
    if len(comps)!=8:out.append("expected 8 team-state components")
    names={x["name"] for x in comps}
    for need in {"prior_strength","underlying_strength","available_strength","current_form_signal","uncertainty"}:
        if need not in names:out.append(f"missing state component {need}")
    if len(priors)!=12 or any(x["w11_weight_frozen"]!="false" for x in priors):out.append("prior component/weight contract mismatch")
    if len(weights)!=7 or any(x["production_selected"]!="false" for x in weights):out.append("historical weighting prematurely selected")
    if any(x["default_weight"].strip() for x in regimes):out.append("regime factor default weight frozen")
    if any(x["threshold"].strip() or x["automatic_reset"]!="false" for x in cps):out.append("change-point threshold/reset prematurely frozen")
    if len(blends)!=5 or any(x["numeric_parameter_frozen"]!="false" or x["fixed_week_schedule"]!="false" for x in blends):out.append("early-season blend schedule frozen")
    levels=[x["division"] for x in hier]
    if levels!=["FBS","FCS","DII","DIII","NAIA","JUCO","OTHER"]:out.append("bounded division hierarchy mismatch")
    if any(x["fixed_fbs_equivalent_penalty"]!="false" or x["recursive_full_model_required"]!="false" for x in hier):out.append("lower-division fixed penalty/recursion violation")
    if any(x["fixed_penalty"].strip() or x["uncertainty_required"]!="true" for x in trans):out.append("translation contract fixed penalty/uncertainty violation")
    if any(x["directional_strength_adjustment"]!="false" or x["w11_numeric_calibration"]!="false" for x in unc):out.append("uncertainty prematurely directional/calibrated")
    if any(x["winner_selected_w11"]!="false" for x in compare):out.append("team-state winner selected in W11")
    if len(gate)!=1 or gate[0]["status"]!="CLEARED_W11_CONTRACT_ONLY" or gate[0]["empirical_parameterization_frozen"]!="false":out.append("W11 gate mismatch")
    task={x["task_id"]:x for x in wbs}
    for tid in ["TASK-030","TASK-031","TASK-032","TASK-033","TASK-034","TASK-035","TASK-194"]:
        if task.get(tid,{}).get("status")!="DONE":out.append(f"{tid} not DONE")
    if task.get("TASK-047",{}).get("status") not in {"READY","DONE"}:out.append("TASK-047 regressed before/after W12")
    if len(lifecycle)!=736 or any(x["initial_lifecycle_state"]!="EXPERIMENTAL" or x["production_approved"]!="false" for x in lifecycle):
        out.append("W10 feature lifecycle baseline changed/promoted")
    if cfg.get("empirical_winner_selected_w11") is not False or cfg.get("numeric_decay_or_blend_parameters_frozen_w11") is not False:
        out.append("W11 registry claims empirical winner/parameters")
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",type=Path,default=Path.cwd());a=ap.parse_args()
    f=validate(a.repo_root.resolve())
    if f:
        print(f"FAIL: {len(f)} team-state finding(s)");[print("-",x) for x in f];return 1
    print("PASS: W11 team-state, early-season, historical-weighting and bounded lower-division contracts")
    return 0
if __name__=="__main__":raise SystemExit(main())

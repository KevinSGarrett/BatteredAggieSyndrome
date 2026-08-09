from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
sys.dont_write_bytecode=True

def rows(p:Path):
    with p.open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def validate(root:Path)->list[str]:
    g=root/"governance"; out=[]
    cfg=json.loads((root/"configs/player_intelligence_registry.json").read_text(encoding="utf-8"))
    comps=rows(g/"PLAYER_STATE_COMPONENTS.csv")
    rd=rows(g/"ROSTER_DEPTH_STATE_CONTRACTS.csv")
    pv=rows(g/"PLAYER_VALUE_EVIDENCE_CATALOG.csv")
    av=rows(g/"AVAILABILITY_STATE_CONTRACT.csv")
    conf=rows(g/"AVAILABILITY_EVIDENCE_CONFIDENCE.csv")
    repl=rows(g/"REPLACEMENT_VALUE_CONTRACTS.csv")
    priors=rows(g/"RECRUITING_PROSPECT_PRIOR_CATALOG.csv")
    te=rows(g/"TRANSFER_EPISODE_CONTRACTS.csv")
    tt=rows(g/"TRANSFER_TRANSLATION_EXPERIMENT_PLAN.csv")
    unc=rows(g/"TRANSFER_FRESHMAN_UNCERTAINTY_CATALOG.csv")
    honors=rows(g/"PRESEASON_HONOR_CANDIDATE_CONTRACTS.csv")
    draft=rows(g/"DRAFT_DEVELOPMENT_CANDIDATE_CONTRACTS.csv")
    avail_sources=rows(g/"AVAILABILITY_SOURCE_LANE.csv")
    audit=rows(g/"TRANSFER_RECRUITING_PROVENANCE_AUDIT.csv")
    ds=rows(g/"DATASET_SCHEMA_REGISTRY.csv")
    gate=rows(g/"PLAYER_INTELLIGENCE_GATE_STATUS.csv")
    wbs=rows(g/"IMPLEMENTATION_WBS.csv")
    features=rows(g/"FEATURE_CANDIDATE_SEEDS.csv")
    teamgate=rows(g/"TEAM_STATE_GATE_STATUS.csv")
    req=rows(g/"REQUIREMENTS_INDEX.csv")
    adr=rows(g/"ADR_INDEX.csv"); risks=rows(g/"RISK_REGISTER.csv"); ac=rows(g/"ACCEPTANCE_CONTROL_CATALOG.csv")
    hyps=rows(g/"HYPOTHESIS_LEDGER.csv")

    if cfg.get("version")!="w12-v1.0": out.append("player registry version mismatch")
    if len(comps)!=10: out.append("expected 10 player-state components")
    if len(rd)!=5: out.append("expected 5 roster/depth contracts")
    if any(x["state_type"]=="ROSTER_MEMBERSHIP" and "starter" not in x["prohibited_inference"] for x in rd):
        out.append("roster membership does not explicitly prohibit starter inference")
    if len(pv)!=9 or any(x["manual_fixed_weight"].strip() or x["production_selected"]!="false" for x in pv):
        out.append("player value prematurely weighted/selected")
    if len(av)!=8 or any(x["numeric_default"].strip() for x in av):
        out.append("availability numeric default frozen")
    if len(conf)!=7 or any(x["auto_healthy_if_missing"]!="false" or x["fixed_numeric_weight"].strip() for x in conf):
        out.append("availability evidence auto-health/numeric weight violation")
    if any(x["fixed_position_penalty"]!="false" or x["uncertainty_required"]!="true" for x in repl):
        out.append("replacement fixed position penalty/uncertainty violation")
    if any(x["manual_weight"].strip() for x in priors):
        out.append("prospect prior manual weight frozen")
    if any(x["identity_rule"]=="DO_NOT_CREATE_NEW_PLAYER_ON_TRANSFER" for x in te) is False:
        out.append("transfer identity persistence missing")
    if len(tt)!=6 or any(x["fixed_conference_penalty"]!="false" or x["winner_selected_w12"]!="false" for x in tt):
        out.append("transfer fixed conference penalty/winner violation")
    if any(x["directional_adjustment"]!="false" or x["numeric_calibration_w12"]!="false" for x in unc):
        out.append("transfer/freshman uncertainty prematurely directional/calibrated")
    if any(x["manual_bonus"].strip() or x["production_selected"]!="false" for x in honors):
        out.append("preseason honor manual bonus/selection violation")
    if any(x["future_outcome_as_same_season_feature"]!="false" or x["production_selected"]!="false" for x in draft):
        out.append("future draft leakage/selection violation")
    sec=[x for x in avail_sources if x["source_id"]=="SRC-017"]
    if len(sec)!=1 or sec[0]["project_priority"]!="A&M_PRIMARY":
        out.append("SEC availability lane not A&M primary")
    if any(x["missing_report_means_healthy"]!="false" or x["materialization_status"]!="PLAN_ONLY_W12" for x in avail_sources):
        out.append("availability source materialization/noncoverage honesty violation")
    if len(audit)<4 or any(not x["terms_or_license"] or not x["w12_decision"] for x in audit):
        out.append("transfer/recruiting provenance audit incomplete")
    required_ds_fields={"source_owner","source_url","source_access_method","source_terms_or_license","source_redistribution","source_rights_review_status","provenance_augmented_wave"}
    if not ds or not required_ds_fields.issubset(ds[0]):
        out.append("dataset source provenance columns missing")
    elif any(not x["source_owner"] or not x["source_terms_or_license"] or x["provenance_augmented_wave"]!="W12_CATCHUP_TASK197" for x in ds):
        out.append("dataset source provenance augmentation incomplete")
    if len(gate)!=1 or gate[0]["status"]!="CLEARED_W12_CONTRACT_ONLY":
        out.append("W12 gate mismatch")
    if any(gate[0][k]!="false" for k in ["empirical_player_value_selected","empirical_availability_calibration_selected","empirical_transfer_translation_selected","numeric_position_penalty_frozen","numeric_transfer_penalty_frozen"]):
        out.append("W12 gate claims empirical/fixed values")
    task={x["task_id"]:x for x in wbs}
    for tid in [f"TASK-{i:03d}" for i in range(47,59)]+["TASK-193","TASK-197","TASK-200"]:
        if task.get(tid,{}).get("status")!="DONE": out.append(f"{tid} not DONE")
    if task.get("TASK-059",{}).get("status") not in {"READY","DONE"}: out.append("TASK-059 W12 handoff disappeared")
    if len(features)!=736 or any(x["initial_lifecycle_state"]!="EXPERIMENTAL" or x["production_approved"]!="false" for x in features):
        out.append("W10 feature baseline changed/promoted")
    if len(teamgate)!=1 or teamgate[0]["status"]!="CLEARED_W11_CONTRACT_ONLY":
        out.append("W11 team-state gate not preserved")
    if cfg.get("empirical_player_value_model_selected_w12") is not False or cfg.get("numeric_position_penalties_frozen_w12") is not False or cfg.get("empirical_transfer_translation_selected_w12") is not False or cfg.get("numeric_transfer_penalties_frozen_w12") is not False:
        out.append("W12 registry claims empirical winner/penalty")
    if len(req)<421 or len(adr)<167 or len(risks)<161 or len(ac)<112:
        out.append("W12 governance baseline disappeared")
    for hid in ["HYP-031","HYP-032","HYP-033"]:
        h=[x for x in hyps if x["hypothesis_id"]==hid]
        if len(h)!=1 or h[0]["status"]!="PENDING":
            out.append(f"{hid} hypothesis missing/not pending")
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",type=Path,default=Path.cwd());a=ap.parse_args()
    f=validate(a.repo_root.resolve())
    if f:
        print(f"FAIL: {len(f)} player-intelligence finding(s)")
        [print("-",x) for x in f]
        return 1
    print("PASS: W12 player/roster/depth/availability/replacement/recruiting/transfer contracts")
    return 0
if __name__=="__main__": raise SystemExit(main())

from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
sys.dont_write_bytecode=True

def rows(p:Path):
    with p.open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def validate(root:Path)->list[str]:
    g=root/"governance"; out=[]
    cfg=json.loads((root/"configs/context_intelligence_registry.json").read_text(encoding="utf-8"))
    role=rows(g/"COACH_ROLE_EPISODE_CONTRACTS.csv")
    residual=rows(g/"COACH_DEVELOPMENT_RESIDUAL_CONTRACTS.csv")
    scheme=rows(g/"SCHEME_PLAY_CALLER_TENDENCY_CONTRACTS.csv")
    dec=rows(g/"COACH_DECISION_EVIDENCE_CANDIDATES.csv")
    conf=rows(g/"COACH_CONFOUND_CONTROL_CATALOG.csv")
    weather=rows(g/"WEATHER_CONTEXT_CONTRACTS.csv")
    travel=rows(g/"VENUE_TRAVEL_REST_CONTRACTS.csv")
    res=rows(g/"PROGRAM_RESOURCE_LANES.csv")
    home=rows(g/"HOME_FIELD_EXPERIMENT_PLAN.csv")
    game=rows(g/"GAME_CONTEXT_CONTRACTS.csv")
    reg=rows(g/"REGULATORY_ENVIRONMENT_CONTRACTS.csv")
    poss=rows(g/"POSSESSION_TEMPO_CONTRACTS.csv")
    fp=rows(g/"FIELD_POSITION_HIDDEN_YARDS_CONTRACTS.csv")
    st=rows(g/"SPECIAL_TEAMS_COMPONENT_CONTRACTS.csv")
    score=rows(g/"SCORE_STATE_POLICY_CANDIDATES.csv")
    inter=rows(g/"MECHANICS_INTERACTION_CANDIDATES.csv")
    opp=rows(g/"OPPONENT_ADJUSTMENT_CANDIDATES.csv")
    style=rows(g/"STYLE_SIMILARITY_CANDIDATES.csv")
    stress=rows(g/"SCHEDULE_STRESS_CONTRACTS.csv")
    off=rows(g/"OFFICIATING_EXPERIMENT_POLICY.csv")
    priv=rows(g/"PRIVATE_RESOURCE_PROXY_CONTRACTS.csv")
    cg=rows(g/"COACHING_INTELLIGENCE_GATE_STATUS.csv")
    xg=rows(g/"CONTEXT_GATE_STATUS.csv")
    mg=rows(g/"MECHANICS_GATE_STATUS.csv")
    og=rows(g/"MATCHUP_CONTEXT_GATE_STATUS.csv")
    wbs=rows(g/"IMPLEMENTATION_WBS.csv")
    req=rows(g/"REQUIREMENTS_INDEX.csv"); adr=rows(g/"ADR_INDEX.csv"); risk=rows(g/"RISK_REGISTER.csv"); ac=rows(g/"ACCEPTANCE_CONTROL_CATALOG.csv")
    hyp=rows(g/"HYPOTHESIS_LEDGER.csv")
    feats=rows(g/"FEATURE_CANDIDATE_SEEDS.csv")

    if cfg.get("version")!="w13-v1.0": out.append("W13 registry version mismatch")
    if cfg.get("maturity")!="COACHING_CONTEXT_MECHANICS_CONTRACTS_SYNTHETIC_ONLY": out.append("W13 maturity mismatch")
    for k in ["empirical_coach_effect_selected_w13","numeric_coach_bonus_frozen_w13","empirical_home_field_selected_w13",
              "numeric_home_field_bonus_frozen_w13","garbage_time_policy_selected_w13","opponent_adjustment_winner_selected_w13",
              "officiating_feature_promoted_w13"]:
        if cfg.get(k) is not False: out.append(f"{k} must remain false")
    if len(role)!=6 or any(x["manual_effect_allowed"]!="false" for x in role): out.append("coach role contract mismatch/manual effect")
    if len(residual)!=6 or any(x["production_selected"]!="false" for x in residual): out.append("coach residual prematurely selected")
    if len(conf)<8: out.append("coach confound controls incomplete")
    if any(x["manual_strength_bonus"]!="false" for x in scheme): out.append("scheme manual bonus present")
    if any(x["manual_bonus"]!="false" or x["winner_selected_w13"]!="false" for x in dec): out.append("coach decision candidate prematurely selected")
    if any(x["observed_weather_allowed_pregame"]!="false" for x in weather): out.append("observed weather allowed as pregame")
    if len(travel)<7 or any(x["fixed_effect"]!="false" for x in travel): out.append("travel contract fixed effect/missing")
    if {x["lane_id"] for x in res}!={"RES-R0","RES-R1","RES-R2","RES-R3"}: out.append("resource lanes mismatch")
    if any(x["fabricate_private_values"]!="false" for x in res): out.append("resource fabrication allowed")
    if any(x["manual_bonus"]!="false" or x["winner_selected_w13"]!="false" for x in home): out.append("home effect prematurely selected")
    if any(x["manual_bonus"]!="false" for x in game): out.append("game-context narrative bonus present")
    if len(reg)!=5: out.append("regulatory environment incomplete")
    if any(x["fixed_formula"]!="false" for x in poss): out.append("possession formula frozen")
    if len(fp)!=6 or len(st)!=6: out.append("mechanics component catalog incomplete")
    if any(x["numeric_threshold_frozen"]!="false" or x["production_selected"]!="false" for x in score): out.append("score-state policy prematurely frozen")
    if any(x["manual_effect"]!="false" for x in inter): out.append("mechanics interaction manual effect")
    if any(x["winner_selected_w13"]!="false" for x in opp+style): out.append("opponent/style winner selected")
    if any(x["future_outcomes_allowed"]!="false" for x in stress): out.append("schedule stress allows future outcomes")
    if not any(x["policy_id"]=="OFF-04" and x["pregame_feature"]=="false" for x in off): out.append("officiating fail-closed policy missing")
    if any(x["dollar_spend_estimate"]!="false" for x in priv): out.append("private proxy claims dollar spend")
    for gate,name in [(cg,"coaching"),(xg,"context"),(mg,"mechanics"),(og,"matchup")]:
        if len(gate)!=1 or gate[0]["status"]!="CLEARED_W13_CONTRACT_ONLY": out.append(f"{name} gate mismatch")
    task={x["task_id"]:x for x in wbs}
    for tid in [f"TASK-{i:03d}" for i in range(59,83)]+["TASK-195","TASK-198","TASK-201"]:
        if task.get(tid,{}).get("status")!="DONE": out.append(f"{tid} not DONE")
    if task.get("TASK-088",{}).get("status") not in {"READY","DONE"}: out.append("TASK-088 not preserved as READY/DONE")
    if "TASK-087" in task.get("TASK-088",{}).get("depends_on","").split(";"): out.append("W14 dependency inversion not repaired")
    if len(req)<461 or len(adr)<186 or len(risk)<180 or len(ac)<126: out.append("W13 governance baseline missing")
    for hid in [f"HYP-{i:03d}" for i in range(34,41)]:
        h=[x for x in hyp if x["hypothesis_id"]==hid]
        if len(h)!=1 or h[0]["status"]!="PENDING": out.append(f"{hid} missing/not pending")
    if len(feats)!=736 or any(x["initial_lifecycle_state"]!="EXPERIMENTAL" or x["production_approved"]!="false" for x in feats):
        out.append("W10 feature baseline changed/promoted")
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo-root",type=Path,default=Path.cwd()); a=ap.parse_args()
    f=validate(a.repo_root.resolve())
    if f:
        print(f"FAIL: {len(f)} W13 context-intelligence finding(s)")
        [print("-",x) for x in f]
        return 1
    print("PASS: W13 coaching/context/mechanics/opponent/style/officiating contracts")
    return 0
if __name__=="__main__": raise SystemExit(main())

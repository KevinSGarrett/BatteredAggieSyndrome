from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
sys.dont_write_bytecode=True

def rows(p:Path):
    with p.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))

def validate(root:Path)->list[str]:
    g=root/"governance"; out=[]
    cfg=json.loads((root/"configs/tamu_specialization_registry.json").read_text(encoding="utf-8"))
    state=rows(g/"TAMU_STATE_COMPONENTS.csv"); lanes=rows(g/"TAMU_EVIDENCE_RESOLUTION_LANES.csv")
    units=rows(g/"TAMU_UNIT_STATE_CONTRACTS.csv"); snaps=rows(g/"TAMU_SNAPSHOT_CADENCE_CANDIDATES.csv")
    peers=rows(g/"TAMU_PEER_COHORT_CONTRACTS.csv"); analogs=rows(g/"TAMU_ANALOG_CONTRACTS.csv")
    candidates=rows(g/"TAMU_SPECIALIZATION_CANDIDATES.csv"); guards=rows(g/"TAMU_SPECIALIZATION_OVERFIT_GUARDS.csv")
    slices=rows(g/"TAMU_EVALUATION_SLICES.csv"); sg=rows(g/"TAMU_STATE_GATE_STATUS.csv"); pg=rows(g/"TAMU_SPECIALIZATION_GATE_STATUS.csv")
    wbs=rows(g/"IMPLEMENTATION_WBS.csv"); req=rows(g/"REQUIREMENTS_INDEX.csv"); adr=rows(g/"ADR_INDEX.csv"); risk=rows(g/"RISK_REGISTER.csv"); ac=rows(g/"ACCEPTANCE_CONTROL_CATALOG.csv")
    hyp=rows(g/"HYPOTHESIS_LEDGER.csv"); feats=rows(g/"FEATURE_CANDIDATE_SEEDS.csv"); th=rows(g/"ACCEPTANCE_THRESHOLD_REGISTRY.csv")
    if cfg.get("version")!="w14-v1.0" or cfg.get("maturity")!="TAMU_SPECIALIZATION_CONTRACTS_SYNTHETIC_ONLY":out.append("W14 registry version/maturity mismatch")
    for k in ["empirical_specialization_winner_selected_w14","numeric_tamu_bonus_frozen_w14","snapshot_cadence_selected_w14","peer_cohort_definition_selected_w14","analog_method_selected_w14","thr_005_value_frozen_w14","bas_definition_changed_w14"]:
        if cfg.get(k) is not False:out.append(f"{k} must remain false")
    if cfg.get("no_adjustment_baseline_required") is not True:out.append("no-adjustment baseline not required")
    if len(state)!=16 or any(x["separate_canonical_truth"]!="false" for x in lanes):out.append("A&M state/evidence truth contract mismatch")
    if any(x["manual_strength_bonus"]!="false" or x["winner_selected_w14"]!="false" for x in units):out.append("manual unit bonus or W14 unit winner")
    if any(x["immutable"]!="true" or x["production_selected_w14"]!="false" for x in snaps):out.append("snapshot cadence prematurely selected/mutable")
    if any(x["outcome_conditioned"]!="false" or x["manual_adjustment_allowed"]!="false" or x["production_selected_w14"]!="false" for x in peers):out.append("peer cohort unsafe/promoted")
    if any(x["strict_prior_only"]!="true" or x["same_game_outcome_allowed"]!="false" or x["automatic_prediction_adjustment"]!="false" for x in analogs):out.append("analog contract unsafe")
    if len(candidates)<5 or not any(x["candidate_id"]=="TAMU-SP-00" and x["required_baseline"]=="true" for x in candidates):out.append("mandatory no-adjust baseline missing")
    if any(x["production_selected_w14"]!="false" for x in candidates):out.append("specialization candidate selected in W14")
    if any(x["numeric_threshold_frozen"]!="false" or x["protected"]!="true" for x in guards):out.append("overfit guard threshold/protection mismatch")
    if any(x["weight_frozen_w14"]!="false" for x in slices):out.append("A&M evaluation weights frozen")
    if len(sg)!=1 or sg[0]["status"]!="CLEARED_W14_CONTRACT_ONLY":out.append("A&M state gate mismatch")
    if len(pg)!=1 or pg[0]["status"]!="CLEARED_W14_CONTRACT_ONLY" or pg[0]["winner_selected"]!="false":out.append("specialization gate mismatch")
    task={x["task_id"]:x for x in wbs}
    for tid in [f"TASK-{i:03d}" for i in range(88,100)]:
        if task.get(tid,{}).get("status")!="DONE":out.append(f"{tid} not DONE")
    if task.get("TASK-100",{}).get("status") not in {"READY","DONE"}:out.append("TASK-100 neither READY nor DONE")
    if len(req)<493 or len(adr)<202 or len(risk)<194 or len(ac)<138:out.append("W14 governance baseline count regressed")
    for hid in [f"HYP-{i:03d}" for i in range(41,47)]:
        h=[x for x in hyp if x["hypothesis_id"]==hid]
        if len(h)!=1 or h[0]["status"]!="PENDING":out.append(f"{hid} missing/not pending")
    t5=[x for x in th if x["threshold_id"]=="THR-005"]
    if len(t5)!=1 or t5[0]["value"].strip() or t5[0]["status"] not in {"TBD_BY_EVIDENCE","METHOD_FROZEN_VALUE_PENDING_DEVELOPMENT_EVIDENCE"}:out.append("THR-005 must remain blank with protected method state")
    if len(feats)!=736 or any(x["initial_lifecycle_state"]!="EXPERIMENTAL" or x["production_approved"]!="false" for x in feats):out.append("W10 candidates changed/promoted")
    # verify W13 shifted rows were repaired
    badids={"REQ-427","REQ-428","REQ-429","REQ-430","REQ-439","REQ-442","REQ-443","REQ-444","REQ-445","REQ-446","REQ-447","REQ-451","REQ-452","REQ-453"}
    for r in req:
        if r["requirement_id"] in badids and (r["planned_wave"]!="W13" or r["wave_introduced"]!="W13" or r["description"]=="W13"):out.append(f"{r['requirement_id']} W13 row not repaired")
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",type=Path,default=Path.cwd());a=ap.parse_args();f=validate(a.repo_root.resolve())
    if f:
        print(f"FAIL: {len(f)} W14 Tamu-specialization finding(s)");[print("-",x) for x in f];return 1
    print("PASS: W14 Texas A&M high-resolution state, peers/analogs, snapshot and specialization-candidate contracts")
    return 0
if __name__=="__main__":raise SystemExit(main())

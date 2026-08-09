from __future__ import annotations
import argparse,csv,json,sys,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))

from aggie_analytics.experimentation.governance import (
    verify_judging_rule_seal, hpo_objective_allowed, advanced_challenger_admission
)
from aggie_analytics.experimentation.queue import TRANSITIONS
from aggie_analytics.experimentation.hpo import HPOStudySpec, SearchParameter
from aggie_analytics.experimentation.tournaments import TournamentSpec, validate_research_decision

def rows(p):
    with p.open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def validate(root: Path) -> list[str]:
    g=root/"governance"; findings=[]
    reg=json.loads((root/"configs/experiment_research_registry.json").read_text(encoding="utf-8"))
    if reg.get("maturity")!="EXPERIMENTATION_AUTONOMOUS_RESEARCH_FULL_REFERENCE_IMPLEMENTATION":
        findings.append("unexpected corrected W18 maturity")
    if reg.get("version")!="w18-v2.0-full-rebuild":
        findings.append("corrected W18 registry version missing")
    for key in ["protected_empirical_results_inspected_w18","trained_model_metrics_claimed_w18","advanced_challenger_empirical_winner_w18"]:
        if reg.get(key) is not False: findings.append(f"W18 honesty flag {key} is not false")
    if verify_judging_rule_seal(root):
        findings.extend("judging seal "+x for x in verify_judging_rule_seal(root))

    # Tools / HPO
    tools={r["tool_id"]:r for r in rows(g/"EXPERIMENT_TOOL_DECISION_MATRIX.csv")}
    if tools.get("TOOL-EXP-001",{}).get("status")!="SELECTED_DEFAULT_ADAPTER": findings.append("MLflow not selected default adapter")
    if tools.get("TOOL-HPO-001",{}).get("status")!="SELECTED_DEFAULT_ADAPTER": findings.append("Optuna not selected default adapter")
    if hpo_objective_allowed("SPLIT-PROTECTED") or hpo_objective_allowed("SPLIT-FORWARD"): findings.append("protected/forward split allowed in HPO")
    if not hpo_objective_allowed("SPLIT-DEV-HIST") or not hpo_objective_allowed("SPLIT-DEV-SEL"): findings.append("development HPO split denied")
    try:
        HPOStudySpec(
            candidate_family="boosted",search_space_version="v1",
            parameters=[SearchParameter("depth","int",{"low":2,"high":8,"step":1})],
            development_split="SPLIT-DEV-SEL",objective_metrics=["brier"],trial_budget=3
        ).validate()
    except Exception as e:
        findings.append(f"valid HPO reference rejected: {e}")

    # Queue / roles
    if "PROMOTE" in TRANSITIONS or any("PROMOTE" in nxt for nxts in TRANSITIONS.values() for nxt in nxts):
        findings.append("PROMOTE exists in research queue")
    roles={r["role"]:r for r in rows(g/"RESEARCH_ROLE_CAPABILITIES.csv")}
    ra=roles.get("research_agent",{})
    for key in ["may_read_protected_metrics","may_change_protected_rules","may_change_champion"]:
        if ra.get(key)!="false": findings.append(f"research_agent {key} not false")

    # Advanced challenger
    admission={r["candidate_class"]:r for r in rows(g/"ADVANCED_CHALLENGER_ADMISSION.csv")}
    for c in ["SMALL_NEURAL_TABULAR","SEQUENCE_TRANSFORMER","GRAPH_NEURAL_NETWORK"]:
        if not admission.get(c,{}).get("admission_state","").startswith("BLOCKED_"):
            findings.append(f"advanced challenger {c} not blocked")
    if advanced_challenger_admission(candidate_class="SEQUENCE_TRANSFORMER",baseline_empirical_evidence=False,protocol_sealed=True,resource_budget_declared=True)!="BLOCKED_BASELINE_EMPIRICAL_EVIDENCE_MISSING":
        findings.append("advanced challenger reference gate wrong")

    # Tournament first-class coverage
    feature=rows(g/"FEATURE_TOURNAMENT_POLICY.csv")
    model=rows(g/"MODEL_TOURNAMENT_POLICY.csv")
    stages=rows(g/"TOURNAMENT_STAGE_CATALOG.csv")
    if len(feature)<8 or not any(r["stage"]=="ABLATION" for r in feature):
        findings.append("feature tournament incomplete")
    if any("PROMOTE" in r["allowed_outputs"].split(";") for r in feature):
        findings.append("feature tournament can promote")
    if len(model)<6 or not any("TAMU-SP-00" in r["mandatory_comparators"] for r in model):
        findings.append("model tournament incomplete/no TAMU no-adjustment baseline")
    if any("PROMOTE" in r["allowed_decisions"].split(";") for r in model):
        findings.append("model tournament can promote")
    if not any(r["name"]=="W17_PROMOTION_REVIEW" and r["promotion_authority"]=="W17_EXTERNAL" for r in stages):
        findings.append("external W17 promotion review missing from tournament stages")
    try:
        TournamentSpec("T","MODEL","tamu_margin","SPLIT-DEV-SEL","mae","min",
                       ["TAMU-SP-00","X"],"TAMU-SP-00",tamu_specialization=True).validate()
        validate_research_decision("ADOPT_AS_CHALLENGER")
    except Exception as e:
        findings.append(f"valid tournament reference rejected: {e}")
    try:
        validate_research_decision("PROMOTE")
        findings.append("research tournament accepted PROMOTE")
    except ValueError:
        pass

    # Master W18 requirement coverage
    coverage=rows(g/"W18_MASTER_REQUIREMENT_COVERAGE.csv")
    expected={
      "experiment tracking","hyperparameter optimization","feature tournament","model tournament",
      "experiment queue","research hypotheses","branches/worktrees","automatic replay",
      "promotion gates","rejection","experiment lineage","immutable judging rules","Phase-5 challenger framework"
    }
    present={r["master_requirement"] for r in coverage}
    if present!=expected:
        findings.append(f"W18 master coverage mismatch missing={sorted(expected-present)} extra={sorted(present-expected)}")

    # Corrected IDs/controls present
    reqids={r["requirement_id"] for r in rows(g/"REQUIREMENTS_INDEX.csv")}
    for i in range(641,701):
        if f"REQ-{i:03d}" not in reqids: findings.append(f"missing corrected W18 requirement REQ-{i:03d}")
    ctrls={r["control_id"] for r in rows(g/"ACCEPTANCE_CONTROL_CATALOG.csv")}
    for i in range(191,229):
        if f"AC-{i:03d}" not in ctrls: findings.append(f"missing corrected W18 control AC-{i:03d}")

    # Thresholds remain blank
    th=rows(g/"ACCEPTANCE_THRESHOLD_REGISTRY.csv")
    for r in th:
        if r["threshold_id"] in {"THR-001","THR-002","THR-003","THR-004","THR-005","THR-006","THR-007","THR-014","THR-015"} and r["value"].strip():
            findings.append(f"{r['threshold_id']} has value in W18")

    # Tasks and W19 handoff
    wbs={r["task_id"]:r for r in rows(g/"IMPLEMENTATION_WBS.csv")}
    for i in range(134,140):
        if wbs.get(f"TASK-{i:03d}",{}).get("status")!="DONE": findings.append(f"TASK-{i:03d} not DONE")
    if wbs.get("TASK-164",{}).get("status")!="DONE": findings.append("TASK-164 not DONE")
    if wbs.get("TASK-041",{}).get("status") not in {"READY","DONE"}: findings.append("TASK-041 neither READY nor DONE for W19+")

    # Correction audit and draft supersession
    audit=(g/"W18_CORRECTION_AUDIT.md").read_text(encoding="utf-8")
    if "c9c690c20aa40bfe7e952b0b94a3eb0fabe27f080afc13354d66d02d2b2b7bc9" not in audit:
        findings.append("thin W18 draft cumulative hash not superseded in correction audit")
    return findings

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo-root",type=Path,default=Path.cwd())
    root=ap.parse_args().repo_root.resolve()
    f=validate(root)
    if f:
        print(f"FAIL: {len(f)} corrected W18 experimentation finding(s)")
        for x in f: print("-",x)
        return 1
    print("PASS: corrected W18 identity/queue/HPO/feature+model tournaments/seal/replay/admission governance")
    return 0
if __name__=="__main__": raise SystemExit(main())

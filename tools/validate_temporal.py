from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path
sys.dont_write_bytecode = True


def rows(path: Path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def validate(root: Path) -> list[str]:
    findings=[]
    reg=json.loads((root/"configs/temporal_registry.json").read_text(encoding="utf-8"))
    if reg.get("maturity") != "POINT_IN_TIME_CONTRACTS_AND_SYNTHETIC_TESTS_ONLY":
        findings.append("temporal maturity over/understated")
    fields={x["field"] for x in rows(root/"governance/TEMPORAL_FIELD_SEMANTICS.csv")}
    required={"published_at","retrieved_at","first_known_at","valid_from","valid_to","effective_at","prediction_eligible_at"}
    if required-fields: findings.append(f"missing temporal fields {sorted(required-fields)}")
    if reg["validity_policy"].get("effective_at_does_not_establish_knowability") is not True:
        findings.append("knowledge/validity axes are not separated")
    if reg["asof_query"].get("fail_closed") is not True:
        findings.append("PIT ambiguity must fail closed")
    domains={x["domain"] for x in rows(root/"governance/PIT_DOMAIN_POLICY.csv")}
    needed={"MARKET","WEATHER_FORECAST","WEATHER_OBSERVED","AVAILABILITY_REPORT","REGULATORY_ENVIRONMENT","RESOURCE_REPORT","HISTORICAL_GAME_OUTPUT","RETROSPECTIVE_DOCUMENT"}
    if needed-domains: findings.append(f"missing domain policies {sorted(needed-domains)}")
    rules=rows(root/"governance/PIT_GATEWAY_RULES.csv")
    if len(rules)<10 or not any(x["rule_id"]=="PIT-001" for x in rules): findings.append("PIT gateway rules incomplete")
    cases=json.loads((root/"fixtures/pit/leakage_cases.json").read_text(encoding="utf-8"))
    if len(cases)<14: findings.append("synthetic leakage fixture set too small")
    try:
        sys.path.insert(0,str(root/"src"))
        from aggie_analytics.temporal.eligibility import evaluate_fixture
        for case in cases:
            got=evaluate_fixture(case)
            if got.eligible is not bool(case["expected_eligible"]):
                findings.append(f"fixture {case['scenario_id']} eligibility mismatch {got.eligible}")
            if got.reason != case["expected_reason"]:
                # Known-after-cutoff is the canonical reason before domain-specific later checks.
                findings.append(f"fixture {case['scenario_id']} reason mismatch {got.reason} != {case['expected_reason']}")
    except Exception as exc:
        findings.append(f"fixture execution error: {exc}")
    schema_dir=root/"schemas/temporal"
    for name in ["observation.json","forecast_cutoff.json","availability_observation.json","weather_forecast_observation.json","market_observation.json","regulatory_observation.json"]:
        p=schema_dir/name
        if not p.is_file(): findings.append(f"missing schema {name}")
        else:
            try: json.loads(p.read_text(encoding="utf-8"))
            except Exception as exc: findings.append(f"invalid schema {name}: {exc}")
    wbs={x["task_id"]:x for x in rows(root/"governance/IMPLEMENTATION_WBS.csv")}
    for tid in ["TASK-013","TASK-014","TASK-015","TASK-016","TASK-017","TASK-018","TASK-191","TASK-192"]:
        if wbs.get(tid,{}).get("status") != "DONE": findings.append(f"{tid} not DONE")
    if wbs.get("TASK-019",{}).get("status") not in {"READY","DONE"}: findings.append("TASK-019 must be READY or DONE after W08 PIT gate")
    return findings


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',type=Path,default=Path.cwd()); a=ap.parse_args()
    f=validate(a.repo_root.resolve())
    if f:
        print(f"FAIL: {len(f)} temporal finding(s)")
        for x in f: print('-',x)
        return 1
    print('PASS: bitemporal semantics, domain PIT policies, protected gateway and synthetic leakage replay')
    return 0
if __name__=='__main__': raise SystemExit(main())

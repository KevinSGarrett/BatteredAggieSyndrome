# Aggie Analytics Engine

Current state: **Wave 25 final handoff complete. The 25-wave program is finished; post-wave work is Codex implementation. AC-038 target-hardware validation remains unresolved.**

This is one cumulative repository developed across the 25-wave program. W24 preserves all accepted W01–W23 work and adds end-to-end readiness, leakage/source/packaging checks, a current source refresh, and the final architecture challenge required before W25.

## Current maturity

Functional starter boundaries now exist for:

`source acquisition → immutable raw evidence → canonical entity/PIT state → features → model/joint-score/BAS → weekly orchestration → immutable forecast publication → read-only API/dashboard → local operations/readiness`

That does **not** mean the complete historical data lake has been materialized or that production model quality has been established. No trained-model winner, protected metric, BAS/Aggie Excess effect, A&M adjustment magnitude or production accuracy is claimed.

## W24 findings

- Cross-layer synthetic E2E and deterministic replay-readiness tests exercise the real W19–W22 starter interfaces.
- PIT now explicitly rejects the target game's own `HISTORICAL_GAME_OUTPUT` by game identity as defense in depth.
- Current source refresh keeps CollegeFootballData, SportsDataverse, Open-Meteo and official availability/rules lanes, while refining provenance/access semantics.
- `cfbfastR-cfb-raw` is explicitly upstream of `cfbfastR-cfb-data`; those sibling layers are not independent corroboration.
- Open-Meteo ensemble mean/spread remains optional recent/current weather-uncertainty research, not a mandatory historical feature.
- Final architecture challenge recommends mostly **KEEP**, with focused provenance/PIT/access **REVISE** items and high-complexity infrastructure **DEFER/REJECT** absent evidence.

## Carried W23 condition

The user explicitly directed W24 to proceed before the W23 target-hardware benchmark could be executed. That changes wave sequencing only.

Still unresolved:

- `TASK-161` — target-hardware benchmark
- `TASK-163` — W23 local-production gate
- `AC-038`
- `THR-011` peak-RAM budget
- `THR-012` runtime budget

W25 must preserve these as **awaiting target-hardware validation** unless valid representative evidence is supplied.

## Start here

1. `AGENTS.md`
2. `governance/NEXT_WAVE.md`
3. `governance/CURRENT_STATE.yaml`
4. `governance/W24_ADAPTIVE_REVIEW.md`
5. `docs/readiness/W24_END_TO_END_READINESS.md`
6. `docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md`
7. `docs/architecture/W24_FINAL_ARCHITECTURE_CHALLENGE.md`
8. `governance/PROTECTED_JUDGING_RULE_SEAL.csv`
9. `governance/OPEN_ISSUES.md`

## Validate

```text
python -B -m unittest discover -s tests -v
python -B tools/validate_w24_readiness.py --repo-root .
python -B tools/validate_acceptance.py --repo-root .
python -B tools/validate_backlog.py --repo-root .
python -B tools/validate_repository.py --repo-root . --strict
```

Non-mutating bootstrap/readiness probe:

```text
python tools/bootstrap_readiness.py --repo-root . --profile core
```

Optional product adapter:

```text
pip install -e ".[product]"
python tools/run_product.py --snapshot-root <published-forecast-root>
```

Project ID: `aggie-analytics-engine`  
Repository program version: `0.24.0-w24-readiness-audit`  
Next permitted work: **Wave 25 — Final consolidation & Codex handoff.**

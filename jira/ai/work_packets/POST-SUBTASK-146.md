# AI Work Packet — POST-SUBTASK-146

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Run bounded tuning, ablation, calibration, OOD, robustness, stability, runtime, memory, maintainability, and simple-baseline comparisons retaining all failures

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-049: Bounded implementation, tuning, ablation, and protected admission.

## Atomic execution scope

Execute the atomic 2 of 3 step in Story POST-STORY-049 (Bounded implementation, tuning, ablation, and protected admission): Run bounded tuning, ablation, calibration, OOD, robustness, stability, runtime, memory, maintainability, and simple-baseline comparisons retaining all failures. Consume only verified prerequisite outputs from `POST-SUBTASK-144`, `POST-SUBTASK-145`. Produce `artifacts/advanced/challenger_tuning_scorecard.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-147.

### In scope

- Perform the exact action: Run bounded tuning, ablation, calibration, OOD, robustness, stability, runtime, memory, maintainability, and simple-baseline comparisons retaining all failures.
- Consume only verified prerequisite outputs from `POST-SUBTASK-144`, `POST-SUBTASK-145`.
- Demonstrate with saved evidence: Search/budget is fixed before results, protected outcomes stay sealed, all trials/negative results persist, and complexity/resource penalties accompany apparent lift.
- Demonstrate with saved evidence: The declared output `artifacts/advanced/challenger_tuning_scorecard.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/advanced/challenger_tuning_scorecard.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Implement the admitted neural/Bayesian/graph/sequence challenger against pinned matrices/splits within fixed scope and compute; Decide whether tuning evidence warrants a one-time sealed protected comparison.
- Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `DEFERRED`
- Ready: `false`
- Priority: `P3`
- Critical path: `false`
- Execution lane: `RESEARCH_LANE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `CONDITIONAL` → `EMPIRICALLY_VALIDATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-150`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-146_run_bounded_tuning_ablation_calibration_ood_robustness_stability_runtime_memory_.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-146.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-146`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/IMPLEMENTATION_WBS.csv
- tests/test_advanced_challenger_full.py
- src/aggie_analytics/experimentation/advanced_challengers.py
- docs/72_ADVANCED_CHALLENGER_ADMISSION.md
- docs/91_ADVANCED_CHALLENGER_GATE.md
- governance/ADVANCED_CHALLENGER_ADMISSION.csv

## Dependencies that must already be complete

- POST-SUBTASK-144
- POST-SUBTASK-145

## Files I may modify or create

- artifacts/advanced/challenger_tuning_scorecard.json
- artifacts/jira_evidence/POST-SUBTASK-146.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- advanced-challengers
- advanced

## What I must not modify or weaken

- AGENTS.md
- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_ACCEPTANCE_RULES.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv
- governance/THRESHOLD_PRECOMMITMENT_REGISTRY.csv
- configs/judging_rule_seal.json
- docs/45_SCIENTIFIC_BAS_SPECIFICATION.md

## Exact outputs / integrated artifacts

Produce and validate these outputs within this atomic work unit:

- artifacts/advanced/challenger_tuning_scorecard.json

## Acceptance criteria

1. Search/budget is fixed before results, protected outcomes stay sealed, all trials/negative results persist, and complexity/resource penalties accompany apparent lift.
2. The declared output `artifacts/advanced/challenger_tuning_scorecard.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_advanced_challenger_full.py — Run as a regression check after completing POST-SUBTASK-146; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/check_advanced_challenger_admission.py — Run as a regression check after completing POST-SUBTASK-146; retain command, exit code, and relevant output.
- BENCHMARK / BENCHMARK: artifacts/advanced/challenger_tuning_scorecard.json — Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.
- SCIENTIFIC / SCIENTIFIC: artifacts/advanced/challenger_tuning_scorecard.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- CALIBRATION / CALIBRATION: artifacts/advanced/challenger_tuning_scorecard.json — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- INTEGRATION / INTEGRATION: artifacts/advanced/challenger_tuning_scorecard.json — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/advanced/challenger_tuning_scorecard.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/advanced/challenger_tuning_scorecard.json` can be parsed and consumed by `POST-SUBTASK-147` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

## Stop instead of improvising when

- Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.
- Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.
- Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence.

## Completion protocol

1. Produce an acceptance-evidence matrix for every criterion.
2. Run every applicable validation entry; implement each declared new automated test.
3. Hash and register every output and all source/data/code/config/tool/runtime identities.
4. Preserve negative, null, blocked, and failed results.
5. Confirm that the claimed maturity—not merely code or files—exists.
6. Update canonical/local Jira state and live Jira operational fields according to `jira/SYNC_CONTRACT.md`.
7. Rebuild all derivatives with `python -B jira/tools/rebuild_all_derivatives.py`.
8. Recompute READY/BLOCKED state and run `python -B jira/tools/validate_second_pass.py`.
9. Reevaluate every downstream issue in `blocks`.

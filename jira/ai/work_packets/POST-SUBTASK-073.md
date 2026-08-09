# AI Work Packet — POST-SUBTASK-073

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Train naive, historical-average, home-field, rating, regularized linear, tree-boosting, market-free, and market-aware baselines with bounded searches

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-025: Simple, rating, linear, tree, market, and coherent joint-score candidates.

## Atomic execution scope

Execute the atomic 1 of 3 step in Story POST-STORY-025 (Simple, rating, linear, tree, market, and coherent joint-score candidates): Train naive, historical-average, home-field, rating, regularized linear, tree-boosting, market-free, and market-aware baselines with bounded searches. Consume only verified prerequisite outputs from `POST-SUBTASK-072`. Produce `artifacts/modeling/baseline_candidate_runs.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-074.

### In scope

- Perform the exact action: Train naive, historical-average, home-field, rating, regularized linear, tree-boosting, market-free, and market-aware baselines with bounded searches.
- Consume only verified prerequisite outputs from `POST-SUBTASK-072`.
- Demonstrate with saved evidence: Every run pins data/config/code/seed/runtime, fits recency/home-field/shrinkage only on permitted history, separates market lanes/cutoffs, and retains failed or negative trials.
- Demonstrate with saved evidence: The declared output `artifacts/modeling/baseline_candidate_runs.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/modeling/baseline_candidate_runs.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Train joint/separate score-distribution candidates and deterministic-seed simulations deriving margin, win, score, total, interval, and severity outputs coherently; Validate artifacts, tuning predictions, orientation, distribution tails, score-margin-win coherence, runtime, and candidate admission.
- Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P1`
- Critical path: `false`
- Execution lane: `RESEARCH_LANE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `IMPLEMENTED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-078`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-073_train_naive_historical_average_home_field_rating_regularized_linear_tree_boostin.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-073.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-073`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/modeling/baselines.py
- src/aggie_analytics/modeling/joint.py
- src/aggie_analytics/modeling/runtime.py
- docs/103_W20_MODEL_CALIBRATION_BAS_IMPLEMENTATION.md
- docs/51_MODEL_TARGETS_AND_OUTPUT_COHERENCE.md
- docs/54_UNCERTAINTY_OOD_AND_MARKET_LANES.md

## Dependencies that must already be complete

- POST-SUBTASK-072

## Files I may modify or create

- artifacts/modeling/baseline_candidate_runs.json
- artifacts/jira_evidence/POST-SUBTASK-073.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- modeling

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

- artifacts/modeling/baseline_candidate_runs.json

## Acceptance criteria

1. Every run pins data/config/code/seed/runtime, fits recency/home-field/shrinkage only on permitted history, separates market lanes/cutoffs, and retains failed or negative trials.
2. The declared output `artifacts/modeling/baseline_candidate_runs.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_model_architecture_governance.py — Run as a regression check after completing POST-SUBTASK-073; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w20_model_starter.py — Run as a regression check after completing POST-SUBTASK-073; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_model_architecture.py — Run as a regression check after completing POST-SUBTASK-073; retain command, exit code, and relevant output.
- BENCHMARK / BENCHMARK: artifacts/modeling/baseline_candidate_runs.json — Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/modeling/baseline_candidate_runs.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SCIENTIFIC / SCIENTIFIC: artifacts/modeling/baseline_candidate_runs.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- STATIC_VALIDATION / STATIC_VALIDATION: artifacts/modeling/baseline_candidate_runs.json — Validate schema, required fields, unique identifiers, cross-references, provenance, and explicit unresolved states.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/modeling/baseline_candidate_runs.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/modeling/baseline_candidate_runs.json` can be parsed and consumed by `POST-SUBTASK-074` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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

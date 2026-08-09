# AI Work Packet — POST-SUBTASK-070

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Materialize official score, margin, win, distribution, market-lane, and BAS-support target tables with game lineage

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-024: Model-ready targets, splits, weights, and datasets.

## Atomic execution scope

Execute the atomic 1 of 3 step in Story POST-STORY-024 (Model-ready targets, splits, weights, and datasets): Materialize official score, margin, win, distribution, market-lane, and BAS-support target tables with game lineage. Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-060`. Produce `artifacts/modeling/target_dataset_manifest.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-071.

### In scope

- Perform the exact action: Materialize official score, margin, win, distribution, market-lane, and BAS-support target tables with game lineage.
- Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-060`.
- Demonstrate with saved evidence: Targets declare cancellations, overtime, missing scores, neutral sites, lower divisions, and official outcome source; every row links to canonical game evidence.
- Demonstrate with saved evidence: The declared output `artifacts/modeling/target_dataset_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/modeling/target_dataset_manifest.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Materialize chronological train/tune/protected assignments, sample weights, cold-start rules, and feature/target separation; Approve model dataset identity, leakage isolation, duplicate handling, and reproducibility.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P1`
- Critical path: `true`
- Execution lane: `DATA_MATERIALIZATION`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `IMPLEMENTED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-078`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-070_materialize_official_score_margin_win_distribution_market_lane_and_bas_support_t.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-070.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-070`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- src/aggie_analytics/modeling/baselines.py
- src/aggie_analytics/modeling/joint.py
- src/aggie_analytics/modeling/runtime.py
- docs/51_MODEL_TARGETS_AND_OUTPUT_COHERENCE.md
- docs/103_W20_MODEL_CALIBRATION_BAS_IMPLEMENTATION.md
- docs/52_MODEL_ARCHITECTURE_CANDIDATES.md
- docs/53_JOINT_SCORE_AND_SIMULATION.md

## Dependencies that must already be complete

- POST-SUBTASK-051
- POST-SUBTASK-060

## Files I may modify or create

- artifacts/modeling/target_dataset_manifest.json
- artifacts/jira_evidence/POST-SUBTASK-070.json

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

- artifacts/modeling/target_dataset_manifest.json

## Acceptance criteria

1. Targets declare cancellations, overtime, missing scores, neutral sites, lower divisions, and official outcome source; every row links to canonical game evidence.
2. The declared output `artifacts/modeling/target_dataset_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_model_architecture_governance.py — Run as a regression check after completing POST-SUBTASK-070; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w20_model_starter.py — Run as a regression check after completing POST-SUBTASK-070; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_model_architecture.py — Run as a regression check after completing POST-SUBTASK-070; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: artifacts/modeling/target_dataset_manifest.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- INTEGRATION / INTEGRATION: artifacts/modeling/target_dataset_manifest.json — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- NEW_AUTOMATED_TEST_REQUIRED / NEW_AUTOMATED_TEST_REQUIRED: NEW_TEST_REQUIRED::POST-SUBTASK-070 — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Evidence to return

- `artifacts/modeling/target_dataset_manifest.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/modeling/target_dataset_manifest.json` can be parsed and consumed by `POST-SUBTASK-071` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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

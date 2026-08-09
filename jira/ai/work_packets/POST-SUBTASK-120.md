# AI Work Packet — POST-SUBTASK-120

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Validate prediction-first hierarchy, accessibility, responsive/loading/stale/blocked/no-data states, and snapshot-only values

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-040: Prediction-first dashboard and BAS experience.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-040 (Prediction-first dashboard and BAS experience): Validate prediction-first hierarchy, accessibility, responsive/loading/stale/blocked/no-data states, and snapshot-only values. Consume only verified prerequisite outputs from `POST-SUBTASK-117`, `POST-SUBTASK-118`, `POST-SUBTASK-119`. Produce `artifacts/product/dashboard_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Validate prediction-first hierarchy, accessibility, responsive/loading/stale/blocked/no-data states, and snapshot-only values.
- Consume only verified prerequisite outputs from `POST-SUBTASK-117`, `POST-SUBTASK-118`, `POST-SUBTASK-119`.
- Demonstrate with saved evidence: Main views make prediction and uncertainty primary, show specialization only if admitted or global-only otherwise, and never calculate independent client-side percentages/scores.
- Demonstrate with saved evidence: BAS is explicitly underperformance versus valid pregame expected margin—not loss probability—witty copy is separate from science, and thresholds/components appear only when supported with uncertainty.
- Demonstrate with saved evidence: Every displayed value traces to a snapshot field and loading/stale/blocked/missing/no-champion/null-effect/source-outage states are accessible and keyboard/screen-reader understandable.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/product/dashboard_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Build game/A&M views for score, win probability, margin, distributions, intervals, scenarios, cutoff, freshness, and model identity; Build BAS ≥3/7/14/21, component, witty-copy, scientific caveat, no-effect, and unavailable presentation.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P2`
- Critical path: `false`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-123`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-120_validate_prediction_first_hierarchy_accessibility_responsive_loading_stale_block.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-120.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-120`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_w22_product_serving.py
- src/aggie_analytics/api/fastapi_app.py
- src/aggie_analytics/product/freshness.py
- src/aggie_analytics/product/repository.py
- docs/107_W22_SNAPSHOT_SERVING_PRODUCT.md
- docs/product/API_CONTRACT.md

## Dependencies that must already be complete

- POST-SUBTASK-117
- POST-SUBTASK-118
- POST-SUBTASK-119

## Files I may modify or create

- artifacts/product/dashboard_gate.json
- artifacts/jira_evidence/POST-SUBTASK-120.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- serving-product
- product

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

- artifacts/product/dashboard_gate.json

## Acceptance criteria

1. Main views make prediction and uncertainty primary, show specialization only if admitted or global-only otherwise, and never calculate independent client-side percentages/scores.
2. BAS is explicitly underperformance versus valid pregame expected margin—not loss probability—witty copy is separate from science, and thresholds/components appear only when supported with uncertainty.
3. Every displayed value traces to a snapshot field and loading/stale/blocked/missing/no-champion/null-effect/source-outage states are accessible and keyboard/screen-reader understandable.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w22_product_serving.py — Run as a regression check after completing POST-SUBTASK-120; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w22_product.py — Run as a regression check after completing POST-SUBTASK-120; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: artifacts/product/dashboard_gate.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- CALIBRATION / CALIBRATION: artifacts/product/dashboard_gate.json — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- OPERATIONS / OPERATIONS: artifacts/product/dashboard_gate.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- END_TO_END / END_TO_END: artifacts/product/dashboard_gate.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/product/dashboard_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

The user sees a serious predictive product with honest uncertainty and freshness, plus clearly separated witty BAS framing that never overstates scientific evidence. The gate decision must explicitly reevaluate downstream issues: POST-STORY-041, POST-SUBTASK-121, POST-SUBTASK-122, POST-SUBTASK-123.

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

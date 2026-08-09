# AI Work Packet — POST-SUBTASK-138

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Validate outputs, lineage, protected decisions, rollback, clean re-execution, target performance/resources/freshness, and all release-blocking controls

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-046: Clean-target real-data release candidate.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-046 (Clean-target real-data release candidate): Validate outputs, lineage, protected decisions, rollback, clean re-execution, target performance/resources/freshness, and all release-blocking controls. Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-135`, `POST-SUBTASK-136`, `POST-SUBTASK-137`. Produce `artifacts/release/release_candidate_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Validate outputs, lineage, protected decisions, rollback, clean re-execution, target performance/resources/freshness, and all release-blocking controls.
- Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-135`, `POST-SUBTASK-136`, `POST-SUBTASK-137`.
- Demonstrate with saved evidence: The stage pins repository/dependencies/Jira/source-rights/schema/data/entity/PIT/feature/model/product/runbook identities, keeps credentials external, enforces restrictions, and fails on dirty protected state or blockers.
- Demonstrate with saved evidence: Every production stage uses real approved data/code/paths and emits complete lineage/tests/resources/freshness/failure evidence; fixtures, samples, fabricated metrics, or manual file swaps cannot claim success.
- Demonstrate with saved evidence: Independent validators trace forecasts/product to the signed run and A&M/BAS/promotion decisions, rollback succeeds, clean re-run reproduces declared outputs, and AC-038/target gates use authoritative host evidence.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/release/release_candidate_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Stage the signed release candidate, dependency/runtime, Jira pack, approved source/rights configuration, and clean external roots; Execute approved-source acquisition through immutable raw, entities, PIT, features, champion/no-champion handling, predictions, publication, API, and dashboard on representative real weekly data.
- Automatically granting legal approval, assuming public accessibility permits retention/redistribution, or bypassing human terms review.
- Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P2`
- Critical path: `false`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `DESIGN_ONLY` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-141`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-138_validate_outputs_lineage_protected_decisions_rollback_clean_re_execution_target_.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-138.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-138`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- docs/final/FINAL_RISK_REGISTER.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- tests/test_w24_readiness.py
- tests/test_w25_final_handoff.py

## Dependencies that must already be complete

- POST-SUBTASK-009
- POST-SUBTASK-135
- POST-SUBTASK-136
- POST-SUBTASK-137

## Files I may modify or create

- artifacts/release/release_candidate_gate.json
- artifacts/jira_evidence/POST-SUBTASK-138.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- release-readiness
- release

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

- artifacts/release/release_candidate_gate.json

## Acceptance criteria

1. The stage pins repository/dependencies/Jira/source-rights/schema/data/entity/PIT/feature/model/product/runbook identities, keeps credentials external, enforces restrictions, and fails on dirty protected state or blockers.
2. Every production stage uses real approved data/code/paths and emits complete lineage/tests/resources/freshness/failure evidence; fixtures, samples, fabricated metrics, or manual file swaps cannot claim success.
3. Independent validators trace forecasts/product to the signed run and A&M/BAS/promotion decisions, rollback succeeds, clean re-run reproduces declared outputs, and AC-038/target gates use authoritative host evidence.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w24_readiness.py — Run as a regression check after completing POST-SUBTASK-138; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w25_final_handoff.py — Run as a regression check after completing POST-SUBTASK-138; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/release/release_candidate_gate.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SCIENTIFIC / SCIENTIFIC: artifacts/release/release_candidate_gate.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- SECURITY / SECURITY: artifacts/release/release_candidate_gate.json — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- OPERATIONS / OPERATIONS: artifacts/release/release_candidate_gate.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- END_TO_END / END_TO_END: artifacts/release/release_candidate_gate.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/release/release_candidate_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Human rights-review record containing reviewer, provider/terms version, access purpose, retention, model-training use, publication, redistribution, deletion, and allow/block decision.
- Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

A clean authoritative target host runs the signed real-data product from acquisition to dashboard and proves reproducibility, rollback, resource, security, and scientific integrity. The gate decision must explicitly reevaluate downstream issues: POST-STORY-047, POST-SUBTASK-139, POST-SUBTASK-140, POST-SUBTASK-141.

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

# AI Work Packet — POST-SUBTASK-098

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Establish protected-outcome access isolation, audit logging, one-way evidence, and failure preservation

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-033: Protected split, judging rule, threshold, candidate, and access seal.

## Atomic execution scope

Execute the atomic 2 of 3 step in Story POST-STORY-033 (Protected split, judging rule, threshold, candidate, and access seal): Establish protected-outcome access isolation, audit logging, one-way evidence, and failure preservation. Consume only verified prerequisite outputs from `POST-SUBTASK-078`, `POST-SUBTASK-084`, `POST-SUBTASK-090`, `POST-SUBTASK-097`. Produce `artifacts/validation/protected_access_protocol_test.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-099.

### In scope

- Perform the exact action: Establish protected-outcome access isolation, audit logging, one-way evidence, and failure preservation.
- Consume only verified prerequisite outputs from `POST-SUBTASK-078`, `POST-SUBTASK-084`, `POST-SUBTASK-090`, `POST-SUBTASK-097`.
- Demonstrate with saved evidence: Only evaluation code can access protected outcomes, every access is attributable, training/tuning cannot read labels/scorecards, and partial failures do not return outcomes for iterative tuning.
- Demonstrate with saved evidence: The declared output `artifacts/validation/protected_access_protocol_test.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/validation/protected_access_protocol_test.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Verify protected split, judging-rule, threshold, feature, model, A&M, BAS, peer, and candidate seal hashes; Authorize or block the exact sealed protected evaluation run.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P1`
- Critical path: `true`
- Execution lane: `SECURITY`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `EMPIRICALLY_VALIDATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-105`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-098_establish_protected_outcome_access_isolation_audit_logging_one_way_evidence_and_.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-098.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-098`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- src/aggie_analytics/validation/promotion.py
- docs/56_VALIDATION_AND_PROTECTED_SPLITS.md
- src/aggie_analytics/validation/protected.py
- docs/57_SCORING_CALIBRATION_AND_SCORECARDS.md
- docs/58_MODEL_PROMOTION_AND_THRESHOLD_PRECOMMITMENT.md

## Dependencies that must already be complete

- POST-SUBTASK-078
- POST-SUBTASK-084
- POST-SUBTASK-090
- POST-SUBTASK-097

## Files I may modify or create

- artifacts/validation/protected_access_protocol_test.json
- artifacts/jira_evidence/POST-SUBTASK-098.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- validation-promotion
- validation

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

- artifacts/validation/protected_access_protocol_test.json

## Acceptance criteria

1. Only evaluation code can access protected outcomes, every access is attributable, training/tuning cannot read labels/scorecards, and partial failures do not return outcomes for iterative tuning.
2. The declared output `artifacts/validation/protected_access_protocol_test.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_validation_science_governance.py — Run as a regression check after completing POST-SUBTASK-098; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w25_final_handoff.py — Run as a regression check after completing POST-SUBTASK-098; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_validation_science.py — Run as a regression check after completing POST-SUBTASK-098; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: artifacts/validation/protected_access_protocol_test.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- STATIC_VALIDATION / STATIC_VALIDATION: artifacts/validation/protected_access_protocol_test.json — Validate schema, required fields, unique identifiers, cross-references, provenance, and explicit unresolved states.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/validation/protected_access_protocol_test.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/validation/protected_access_protocol_test.json` can be parsed and consumed by `POST-SUBTASK-099` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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

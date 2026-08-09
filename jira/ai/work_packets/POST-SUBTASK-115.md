# AI Work Packet — POST-SUBTASK-115

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Implement approved active/archive snapshot repository, model/run lookup, and atomic read behavior

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-039: Read-only forecast repository and versioned API.

## Atomic execution scope

Execute the atomic 1 of 3 step in Story POST-STORY-039 (Read-only forecast repository and versioned API): Implement approved active/archive snapshot repository, model/run lookup, and atomic read behavior. Consume only verified prerequisite outputs from `POST-SUBTASK-111`. Produce `artifacts/product/snapshot_repository_test.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-116.

### In scope

- Perform the exact action: Implement approved active/archive snapshot repository, model/run lookup, and atomic read behavior.
- Consume only verified prerequisite outputs from `POST-SUBTASK-111`.
- Demonstrate with saved evidence: Reads resolve only signed snapshots and exact model/run/state identities; missing/stale/corrupt/unapproved state is explicit and no request path retrains or recomputes uncontrolled features.
- Demonstrate with saved evidence: The declared output `artifacts/product/snapshot_repository_test.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/product/snapshot_repository_test.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Implement versioned forecast/game/team/A&M/BAS/health/freshness endpoints and OpenAPI contract; Validate schema, authorization, snapshot consistency, stale/no-champion/null-BAS states, and restricted-data protection.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P2`
- Critical path: `false`
- Execution lane: `SOLO_WORKTREE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `IMPLEMENTED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-123`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-115_implement_approved_active_archive_snapshot_repository_model_run_lookup_and_atomi.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-115.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-115`.
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

- POST-SUBTASK-111

## Files I may modify or create

- src/aggie_analytics/product/repository.py
- tests/test_w22_product_serving.py
- artifacts/product/snapshot_repository_test.json
- artifacts/jira_evidence/POST-SUBTASK-115.json

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

- artifacts/product/snapshot_repository_test.json

## Acceptance criteria

1. Reads resolve only signed snapshots and exact model/run/state identities; missing/stale/corrupt/unapproved state is explicit and no request path retrains or recomputes uncontrolled features.
2. The declared output `artifacts/product/snapshot_repository_test.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w22_product_serving.py — Run as a regression check after completing POST-SUBTASK-115; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w22_product.py — Run as a regression check after completing POST-SUBTASK-115; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: artifacts/product/snapshot_repository_test.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- OPERATIONS / OPERATIONS: artifacts/product/snapshot_repository_test.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- INTEGRATION / INTEGRATION: artifacts/product/snapshot_repository_test.json — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- NEW_AUTOMATED_TEST_REQUIRED / NEW_AUTOMATED_TEST_REQUIRED: NEW_TEST_REQUIRED::POST-SUBTASK-115 — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Evidence to return

- `artifacts/product/snapshot_repository_test.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/product/snapshot_repository_test.json` can be parsed and consumed by `POST-SUBTASK-116` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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

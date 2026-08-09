# AI Work Packet — POST-SUBTASK-117

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Validate schema, authorization, snapshot consistency, stale/no-champion/null-BAS states, and restricted-data protection

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-039: Read-only forecast repository and versioned API.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-039 (Read-only forecast repository and versioned API): Validate schema, authorization, snapshot consistency, stale/no-champion/null-BAS states, and restricted-data protection. Consume only verified prerequisite outputs from `POST-SUBTASK-111`, `POST-SUBTASK-115`, `POST-SUBTASK-116`. Produce `artifacts/product/api_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Validate schema, authorization, snapshot consistency, stale/no-champion/null-BAS states, and restricted-data protection.
- Consume only verified prerequisite outputs from `POST-SUBTASK-111`, `POST-SUBTASK-115`, `POST-SUBTASK-116`.
- Demonstrate with saved evidence: Reads resolve only signed snapshots and exact model/run/state identities; missing/stale/corrupt/unapproved state is explicit and no request path retrains or recomputes uncontrolled features.
- Demonstrate with saved evidence: Responses expose supported score/probability/distribution/uncertainty/A&M/BAS/lineage/freshness fields and mark scientifically unsupported outputs unavailable rather than defaulting values.
- Demonstrate with saved evidence: All endpoints for a snapshot agree on identities, handle archive/current/errors/no-champion/null decisions, and never expose credentials, restricted raw payloads, or protected outcomes.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/product/api_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Implement approved active/archive snapshot repository, model/run lookup, and atomic read behavior; Implement versioned forecast/game/team/A&M/BAS/health/freshness endpoints and OpenAPI contract.
- Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.
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

1. `jira/records/issues/subtasks/POST-SUBTASK-117_validate_schema_authorization_snapshot_consistency_stale_no_champion_null_bas_st.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-117.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-117`.
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
- POST-SUBTASK-115
- POST-SUBTASK-116

## Files I may modify or create

- artifacts/product/api_gate.json
- artifacts/jira_evidence/POST-SUBTASK-117.json

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

- artifacts/product/api_gate.json

## Acceptance criteria

1. Reads resolve only signed snapshots and exact model/run/state identities; missing/stale/corrupt/unapproved state is explicit and no request path retrains or recomputes uncontrolled features.
2. Responses expose supported score/probability/distribution/uncertainty/A&M/BAS/lineage/freshness fields and mark scientifically unsupported outputs unavailable rather than defaulting values.
3. All endpoints for a snapshot agree on identities, handle archive/current/errors/no-champion/null decisions, and never expose credentials, restricted raw payloads, or protected outcomes.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w22_product_serving.py — Run as a regression check after completing POST-SUBTASK-117; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w22_product.py — Run as a regression check after completing POST-SUBTASK-117; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: artifacts/product/api_gate.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- CALIBRATION / CALIBRATION: artifacts/product/api_gate.json — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- SECURITY / SECURITY: artifacts/product/api_gate.json — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- OPERATIONS / OPERATIONS: artifacts/product/api_gate.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- END_TO_END / END_TO_END: artifacts/product/api_gate.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/product/api_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

A client can retrieve a current or archived signed forecast and exact freshness/lineage without triggering model drift or seeing partial/restricted state. The gate decision must explicitly reevaluate downstream issues: POST-STORY-040, POST-SUBTASK-118, POST-SUBTASK-119, POST-SUBTASK-120.

## Stop instead of improvising when

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

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

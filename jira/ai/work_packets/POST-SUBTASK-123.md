# AI Work Packet — POST-SUBTASK-123

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Publish product readiness, freshness/cache transitions, supported envelope, and safe failure decision

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-041: Faithful drivers, historical analogs, provenance, and target performance.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-041 (Faithful drivers, historical analogs, provenance, and target performance): Publish product readiness, freshness/cache transitions, supported envelope, and safe failure decision. Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-120`, `POST-SUBTASK-121`, `POST-SUBTASK-122`. Produce `artifacts/product/PRODUCT_READINESS.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Publish product readiness, freshness/cache transitions, supported envelope, and safe failure decision.
- Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-120`, `POST-SUBTASK-121`, `POST-SUBTASK-122`.
- Demonstrate with saved evidence: Explanations use exact model/feature versions, expose direction/baseline/missingness/interactions/limits, analogs exclude same/future outcomes and expose distance/sample, and neither implies causality or replaces probability.
- Demonstrate with saved evidence: Benchmarks run on the declared target with repeated workload identity and measure real resources/latency; unsupported/OOD explanations qualify or abstain and restricted data never leaks.
- Demonstrate with saved evidence: Fresh/current/stale/blocked/unavailable/superseded transitions, cache activation/rollback, API/dashboard/security/explanation/performance evidence all pass; product cannot be ready on mutable/unapproved forecasts.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/product/PRODUCT_READINESS.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Generate model-compatible global/per-game driver explanations and serve prior-only historical analog/peer/regime context; Run explanation faithfulness/stability/privacy tests plus target-host cold/warm load, API, snapshot, dashboard, concurrency, memory, CPU, and disk benchmarks.
- Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.
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

1. `jira/records/issues/subtasks/POST-SUBTASK-123_publish_product_readiness_freshness_cache_transitions_supported_envelope_and_saf.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-123.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-123`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- governance/ADR_INDEX.csv
- governance/REQUIREMENTS_INDEX.csv
- tests/test_w22_product_serving.py
- docs/product/API_CONTRACT.md
- src/aggie_analytics/product/freshness.py
- docs/107_W22_SNAPSHOT_SERVING_PRODUCT.md
- src/aggie_analytics/api/fastapi_app.py

## Dependencies that must already be complete

- POST-SUBTASK-009
- POST-SUBTASK-120
- POST-SUBTASK-121
- POST-SUBTASK-122

## Files I may modify or create

- artifacts/product/PRODUCT_READINESS.json
- artifacts/jira_evidence/POST-SUBTASK-123.json

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

- artifacts/product/PRODUCT_READINESS.json

## Acceptance criteria

1. Explanations use exact model/feature versions, expose direction/baseline/missingness/interactions/limits, analogs exclude same/future outcomes and expose distance/sample, and neither implies causality or replaces probability.
2. Benchmarks run on the declared target with repeated workload identity and measure real resources/latency; unsupported/OOD explanations qualify or abstain and restricted data never leaks.
3. Fresh/current/stale/blocked/unavailable/superseded transitions, cache activation/rollback, API/dashboard/security/explanation/performance evidence all pass; product cannot be ready on mutable/unapproved forecasts.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w22_product_serving.py — Run as a regression check after completing POST-SUBTASK-123; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w22_product.py — Run as a regression check after completing POST-SUBTASK-123; retain command, exit code, and relevant output.
- BENCHMARK / BENCHMARK: artifacts/product/PRODUCT_READINESS.json — Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.
- SCIENTIFIC / SCIENTIFIC: artifacts/product/PRODUCT_READINESS.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- CALIBRATION / CALIBRATION: artifacts/product/PRODUCT_READINESS.json — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- SECURITY / SECURITY: artifacts/product/PRODUCT_READINESS.json — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- OPERATIONS / OPERATIONS: artifacts/product/PRODUCT_READINESS.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- END_TO_END / END_TO_END: artifacts/product/PRODUCT_READINESS.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/product/PRODUCT_READINESS.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

A consumer receives faithful snapshot-grounded explanations/analogs and a responsive target-hardware product with explicit safe failure and freshness states. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-015, POST-STORY-045, POST-SUBTASK-133, POST-SUBTASK-134, POST-SUBTASK-135.

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

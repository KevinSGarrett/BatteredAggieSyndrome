# AI Work Packet — POST-SUBTASK-201

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Implement the unified ready-work inventory, routing, readiness, budget, provenance, bypass, utilization, and completeness foundation

## Why?

The mandatory OpenAI assistive-plane contract requires an executable, independently evidenced work unit rather than an untracked direct API call.

## Atomic execution scope

Preserve the merged provider-neutral foundation, then implement and deploy the persistent OS-supervised controller, SQLite WAL state machine, independent read-only watchdog, 204-row ownership/evidence evaluator, live inventory, budgets, retries, reconciliation, control CLI/API, backup, rollback, and cleanup.

### In scope

- Perform the exact action: Implement the governed OpenAI controller, storage, budget, provenance, schema, security, and cleanup foundation.
- Use one governed controller, strict Structured Outputs, minimized cited evidence, content-addressed external storage, deterministic validation, and locally enforced cost admission.
- Preserve abstentions, conflicts, schema failures, unsupported facts, partial batch failures, and negative empirical results.

### Out of scope

- Any direct model write to canonical data, PIT state, labels, protected evaluation, promotion, forecasts, BAS, Aggie Excess, or publication state.
- Scattered OpenAI API calls, hosted-Evals dependence, prompt ingestion of secrets or whole data lakes, or bypass of the USD 100 ledger hard stop.
- Changing protected requirements, judging rules, split seals, or scientific acceptance thresholds merely to obtain a passing result.
- Blocking historical expansion or deterministic/local work when the optional provider is unavailable.

## Current gate state

- Workflow: `IN_PROGRESS`
- Ready: `false`
- Priority: `P0`
- Critical path: `false`
- Execution lane: `SHARED_CONTRACT`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `NOT_STARTED` → `INTEGRATED`
- Evidence state: `PARTIAL`
- Governance traceability gate: `POST-SUBTASK-201`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-201_implement_the_unified_ready_work_inventory_routing_readiness_budget_provenance_bypass_utiliz.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-201.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-201`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/OPENAI_ASSISTIVE_PLANE.md
- configs/openai_assist_policy.json
- configs/openai_task_registry.json
- schemas/openai/assistive_candidate.schema.json
- docs/final/CODEX_HANDOFF.md

## Dependencies that must already be complete

- POST-SUBTASK-160
- POST-SUBTASK-198

## Files I may modify or create

- configs/assistive_provider_registry.json
- configs/assistive_route_readiness.json
- configs/unified_assistive_policy.json
- configs/unified_assistive_ready_work.json
- configs/unified_assistive_operational_claims.json
- configs/unified_assistive_acceptance_ownership.json
- src/aggie_analytics/assistive_plane
- tools/adopt_unified_enforcement_package.py
- tools/validate_unified_acceptance_ownership.py
- tools/run_unified_assistive_controller.py
- tools/run_unified_assistive_watchdog.py
- tools/materialize_unified_assistive_inventory.py
- tools/validate_unified_assistive_plane.py
- tools/validate_unified_assistive_completeness.py
- tools/refresh_cursor_catalog.py
- tools/refresh_local_assistive_runtime.py
- tests/test_unified_controller_state.py
- tests/test_unified_assistive_plane.py
- tests/test_unified_assistive_completeness.py
- governance/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md
- governance/SOURCE_OF_TRUTH_MAP.md
- docs/architecture/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md
- docs/operations/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md
- tests/test_unified_inventory_materializer.py
- tests/test_unified_inventory_scheduler.py
- tests/test_unified_runtime_inventory_dispatch.py
- jira/tools/import_bat_live.py
- tests/test_jira_evidence_state_mapping.py
- artifacts/jira_evidence/POST-SUBTASK-201.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- operations-security
- assistive-plane
- orchestration

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

- artifacts/jira_evidence/POST-SUBTASK-201.json

## Acceptance criteria

1. Inventory validation enforces effort points 1/2/3/5/8, stable identities, anti-padding, one disposition, and complete count/point reconciliation.
2. Readiness binds provider, resolved model and digest, task format, prompt/schema identity, policy version, and execution surface; empirical rejection cannot be overridden by a status edit.
3. Cursor, loopback Ollama, and exact CPU-worker identity policies fail closed; direct endpoint bypasses are detected.
4. A refreshable content-addressed ready-work inventory and separate evidence-derived operational-completeness validator fail stale or overstated dispositions.
5. Credential-safe live catalog/runtime evidence is content-addressed outside Git and all focused/full validators pass through protected integration.
6. The controller and independent watchdog are OS-supervised outside Codex Desktop, recover from crash/restart, agree on maximum justified state, and cannot overclaim partial operation.
7. All 204 acceptance rows map to one canonical/live owner and the runtime validator exits zero only when every mandatory row passes.
8. Undispatched inventory revisions are preserved and may be superseded append-only; active or externally consequential identity changes fail closed without terminating the controller.
9. Inventory derivation semantically validates exact local-model, CPU-worker, Cursor, usage, review, and dispatch-origin evidence instead of treating directory hashes as readiness.
10. The persistent scheduler discovers granular BAS units and durably leases, dispatches, validates, reviews, settles, cleans, closes or requeues them without an active Codex turn.
11. The independent watchdog reports process health separately and fails operational completeness on stale inventory, idle admitted work, zero dispatch, reconciliation gaps, abandoned leases, or unsupported claims.

## Tests / validation

- EXISTING_AUTOMATED_TEST / SECURITY: tests/test_openai_assist.py — Credential redaction, store:false, candidate-only authority, strict schemas, budget hard stop, and isolation gates pass.
- END_TO_END / END_TO_END: artifacts/jira_evidence/POST-SUBTASK-160.json — Use fake synchronous and Batch clients to prove a registered cited job is admitted, store:false, strict-schema validated, externally content-addressed, candidate-disposed, cost-settled, cached, and unable to touch protected truth.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Pin policy, prompt, schema, model, reasoning, source, request/response, cost, code, and runtime identities.

## Evidence to return

- `artifacts/jira_evidence/POST-SUBTASK-160.json` with one evidence row per acceptance criterion and exact artifact hashes.
- Request/job/Jira/source/capture/prompt/schema/model/reasoning identities; estimated and actual tokens/cost; validation and disposition.
- Cleanup record for remote files where practical and abandoned local temporary files, plus remaining review/quarantine items.
- Exact commands, exit codes, relevant output, failed/negative cases, and downstream readiness changes.

## End-to-end handoff

Use fake synchronous and Batch clients to prove a registered cited job is admitted, store:false, strict-schema validated, externally content-addressed, candidate-disposed, cost-settled, cached, and unable to touch protected truth.

## Stop instead of improvising when

- Stop only the affected API job on missing evidence, invalid schema, unsupported fact, credential exposure, budget rejection, provider failure, or inaccessible source; continue independent work.
- Quarantine the affected result on contradiction, refusal, malformed output, provenance mismatch, PIT/target leakage, or identity risk.
- Stop and preserve evidence rather than inventing facts, timestamps, metrics, identities, or maturity.

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

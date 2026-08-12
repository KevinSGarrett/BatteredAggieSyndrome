# AI Work Packet — POST-SUBTASK-205

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Run cross-plane comparison, utilization floors, 21 scheduler cycles, restart/outage exercises, and seven-day sustained assurance

## Why?

The mandatory OpenAI assistive-plane contract requires an executable, independently evidenced work unit rather than an untracked direct API call.

## Atomic execution scope

Derive final utilization/completeness from real route evidence, not counters, after applicable providers qualify; preserve explicit budget/capability incompleteness.

### In scope

- Perform the exact action: Operate continuing governed OpenAI candidate assistance on dependency-ready real project work.
- Use one governed controller, strict Structured Outputs, minimized cited evidence, content-addressed external storage, deterministic validation, and locally enforced cost admission.
- Preserve abstentions, conflicts, schema failures, unsupported facts, partial batch failures, and negative empirical results.

### Out of scope

- Any direct model write to canonical data, PIT state, labels, protected evaluation, promotion, forecasts, BAS, Aggie Excess, or publication state.
- Scattered OpenAI API calls, hosted-Evals dependence, prompt ingestion of secrets or whole data lakes, or bypass of the USD 100 ledger hard stop.
- Changing protected requirements, judging rules, split seals, or scientific acceptance thresholds merely to obtain a passing result.
- Blocking historical expansion or deterministic/local work when the optional provider is unavailable.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P0`
- Critical path: `false`
- Execution lane: `RESEARCH_LANE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `NOT_STARTED` → `EMPIRICALLY_VALIDATED`
- Evidence state: `BLOCKED`
- Governance traceability gate: `POST-SUBTASK-205`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-205_run_cross_plane_comparison_utilization_floors_21_scheduler_cycles_restart_outage_exercises_a.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-205.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-205`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/OPENAI_ASSISTIVE_PLANE.md
- configs/openai_assist_policy.json
- configs/openai_task_registry.json
- schemas/openai/assistive_candidate.schema.json
- docs/final/CODEX_HANDOFF.md

## Dependencies that must already be complete

- POST-SUBTASK-202
- POST-SUBTASK-203
- POST-SUBTASK-204
- POST-SUBTASK-168
- POST-SUBTASK-199

## Files I may modify or create

- artifacts/jira_evidence/POST-SUBTASK-205.json

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

- artifacts/jira_evidence/POST-SUBTASK-205.json

## Acceptance criteria

1. One common-support gold comparison reports quality, evidence, abstention, review time, rework, throughput, cost, and dispositions across admitted routes.
2. At least seven consecutive calendar days, 21 real scheduler cycles, 25 soak-only units/100 points, controller/watchdog restart evidence, and provider/worker outage exercises reconcile with inventory/dispatch/usage/result/cleanup ledgers.
3. The continuing campaigns total at least 135 assignments, 450 points, 125 distinct base units, 85% weighted attempted offload, and 60% weighted accepted offload without padding.
4. All invariants remain unviolated and exact incomplete provider requirements are reported without fabricated backfill.

## Tests / validation

- EXISTING_AUTOMATED_TEST / SECURITY: tests/test_openai_assist.py — Credential redaction, store:false, candidate-only authority, strict schemas, budget hard stop, and isolation gates pass.
- END_TO_END / END_TO_END: artifacts/jira_evidence/POST-SUBTASK-168.json — Run a bounded real-work candidate-only workload across Nano, Luna, Terra, and Sol after deterministic source selection, validate every output without canonical/PIT authority, reconcile exact usage, and leave the continuing lane active for the next eligible workload.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Pin policy, prompt, schema, model, reasoning, source, request/response, cost, code, and runtime identities.

## Evidence to return

- `artifacts/jira_evidence/POST-SUBTASK-168.json` with one evidence row per acceptance criterion and exact artifact hashes.
- Request/job/Jira/source/capture/prompt/schema/model/reasoning identities; estimated and actual tokens/cost; validation and disposition.
- Cleanup record for remote files where practical and abandoned local temporary files, plus remaining review/quarantine items.
- Exact commands, exit codes, relevant output, failed/negative cases, and downstream readiness changes.

## End-to-end handoff

Run a bounded real-work candidate-only workload across Nano, Luna, Terra, and Sol after deterministic source selection, validate every output without canonical/PIT authority, reconcile exact usage, and leave the continuing lane active for the next eligible workload.

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

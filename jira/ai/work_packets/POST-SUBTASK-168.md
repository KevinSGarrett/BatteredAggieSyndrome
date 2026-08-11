# AI Work Packet — POST-SUBTASK-168

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Operate continuing governed OpenAI candidate assistance on dependency-ready real project work

## Why?

The mandatory OpenAI assistive-plane contract requires an executable, independently evidenced work unit rather than an untracked direct API call.

## Atomic execution scope

Execute POST-SUBTASK-168 within the optional OpenAI assistive plane. Consume `POST-SUBTASK-160`; produce `artifacts/openai_assist/continuous_operations.json`, `artifacts/jira_evidence/POST-SUBTASK-168.json`; preserve the deterministic forecast path and candidate-only authority boundary.

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

- Workflow: `IN_PROGRESS`
- Ready: `false`
- Priority: `P0`
- Critical path: `false`
- Execution lane: `RESEARCH_LANE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `NOT_STARTED` → `OPERATING`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-168`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-168_operate_continuing_governed_openai_candidate_assistance_on_dependency_ready_real_project_wor.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-168.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-168`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/OPENAI_ASSISTIVE_PLANE.md
- configs/openai_assist_policy.json
- configs/openai_task_registry.json
- schemas/openai/assistive_candidate.schema.json
- docs/final/CODEX_HANDOFF.md

## Dependencies that must already be complete

- POST-SUBTASK-160

## Files I may modify or create

- configs/openai_task_registry.json
- configs/openai_availability_source_triage.json
- configs/tamu_availability_source_sample.json
- configs/openai_gamebook_schema_mapping.json
- prompts/openai_assist/availability_source_triage_v1.txt
- prompts/openai_assist/gamebook_schema_mapping_v1.txt
- src/aggie_analytics/openai_assist/credentials.py
- tools/prepare_tamu_availability_source_sample.py
- tools/validate_tamu_availability_source_sample.py
- tools/run_openai_availability_source_triage.py
- tools/prepare_openai_gamebook_schema_mapping.py
- tools/run_openai_gamebook_schema_mapping.py
- tools/validate_openai_gamebook_schema_mapping.py
- tools/validate_openai_assist.py
- artifacts/openai_assist/continuous_operations.json
- tests/test_openai_assist.py
- artifacts/jira_evidence/POST-SUBTASK-168.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- data-sources
- openai-assist

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

- artifacts/openai_assist/continuous_operations.json
- artifacts/jira_evidence/POST-SUBTASK-168.json

## Acceptance criteria

1. Bulk/canonical promotion authority remains separate from candidate-only assistance: a failed Nano or exact-format Batch gate never blocks bounded Luna, Terra, or Sol candidate analysis when task admission passes.
2. Dependency-ready historical documents, entity ambiguities, quarantine/schema drift, reconciliation findings, and timestamped availability evidence receive value-selected governed assistance while deterministic/local work continues first where sufficient.
3. Every request uses the single controller, store:false, strict Structured Outputs, minimized cited evidence, content-addressed external storage, budget admission, deterministic validation, and candidate/review/quarantine-only disposition.
4. Each handoff reports calls and spend by model, cumulative and remaining budget, last successful use, active assisted tasks, dispositions, Batch count or exact no-Batch reason, next eligible workload, and cleanup.

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

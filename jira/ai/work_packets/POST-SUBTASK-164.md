# AI Work Packet — POST-SUBTASK-164

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Pilot quarantine and schema-drift classification with deterministic remediation routing

## Why?

The mandatory OpenAI assistive-plane contract requires an executable, independently evidenced work unit rather than an untracked direct API call.

## Atomic execution scope

Execute POST-SUBTASK-164 within the optional OpenAI assistive plane. First adopt governing plan SHA-256 651bbff29cb929cdc441178f67df59e87600a3bc8a54516a942562c7d09aa523 across the controller, staged budget, router, validators, documentation, and Jira graph without rewriting historical settled usage. Then consume `POST-SUBTASK-161`; compare Nano and any justified 4o Mini/Luna route with meaningful Terra/Sol hard cases; produce `artifacts/openai_assist/quarantine_schema_pilot.json`, `artifacts/jira_evidence/POST-SUBTASK-164.json`; preserve the deterministic forecast path and candidate-only authority boundary.

### In scope

- Perform the exact action: Pilot quarantine and schema-drift classification with deterministic remediation routing.
- Use one governed controller, strict Structured Outputs, minimized cited evidence, content-addressed external storage, deterministic validation, and locally enforced cost admission.
- Preserve abstentions, conflicts, schema failures, unsupported facts, partial batch failures, and negative empirical results.
- Adopt the superseding balanced Nano-to-Sol router and budget policy before any BAT-520 paid call, without rewriting settled historical usage.
- Give Terra and Sol meaningful complex/hard/high-risk evidence-backed cases while measuring whether they improve hard-case acceptance, review savings, or risk reduction.

### Out of scope

- Any direct model write to canonical data, PIT state, labels, protected evaluation, promotion, forecasts, BAS, Aggie Excess, or publication state.
- Scattered OpenAI API calls, hosted-Evals dependence, prompt ingestion of secrets or whole data lakes, or bypass of the USD 100 ledger hard stop.
- Changing protected requirements, judging rules, split seals, or scientific acceptance thresholds merely to obtain a passing result.
- Blocking historical expansion or deterministic/local work when the optional provider is unavailable.

## Current gate state

- Workflow: `IN_PROGRESS`
- Ready: `true`
- Priority: `P0`
- Critical path: `false`
- Execution lane: `RESEARCH_LANE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `NOT_STARTED` → `EMPIRICALLY_VALIDATED`
- Evidence state: `PARTIAL`
- Governance traceability gate: `POST-SUBTASK-164`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-164_pilot_quarantine_and_schema_drift_classification_with_deterministic_remediation_routing.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-164.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-164`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/OPENAI_ASSISTIVE_PLANE.md
- configs/openai_assist_policy.json
- configs/openai_task_registry.json
- schemas/openai/assistive_candidate.schema.json
- docs/final/CODEX_HANDOFF.md

## Dependencies that must already be complete

- POST-SUBTASK-161

## Files I may modify or create

- configs/openai_assist_policy.json
- configs/openai_task_registry.json
- configs/openai_quarantine_schema_pilot.json
- src/aggie_analytics/openai_assist/budget.py
- src/aggie_analytics/openai_assist/policy.py
- src/aggie_analytics/openai_assist/controller.py
- tools/openai_assist.py
- tools/validate_openai_assist.py
- governance/OPENAI_ASSISTIVE_PLANE.md
- docs/architecture/OPENAI_ASSISTIVE_PLANE.md
- docs/operations/OPENAI_ASSISTIVE_PLANE.md
- prompts/openai_assist/quarantine_schema_v1.txt
- tools/prepare_openai_quarantine_pilot.py
- tools/run_openai_quarantine_pilot.py
- tools/run_openai_gamebook_pilot.py
- artifacts/openai_assist/router_rebalance.json
- artifacts/openai_assist/quarantine_schema_pilot.json
- tests/test_openai_assist.py
- artifacts/jira_evidence/POST-SUBTASK-164.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- validation-promotion
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

- artifacts/openai_assist/router_rebalance.json
- artifacts/openai_assist/quarantine_schema_pilot.json
- artifacts/jira_evidence/POST-SUBTASK-164.json

## Acceptance criteria

1. Representative corruption, missingness, schema drift, incompatible mapping, evidence absence, conflict, PIT risk, and target-leakage cases are classified without changing source truth.
2. Every remediation route is deterministic-reviewable and affected records/domains remain quarantined until authoritative validators accept them.
3. Validated routine classifications begin with GPT-5 Nano Batch; 4o Mini or Luna is used only for a task-specific measured need, complex ambiguity routes to Terra, and only a hard/high-risk residue routes to Sol.
4. The pilot includes meaningful Terra and Sol hard cases, records accepted evidence-verified results per dollar, and enforces the verified 651bbf...aa523 staged budget and $15/$10 base plus $25/$17 maximum Terra/Sol caps.

## Tests / validation

- EXISTING_AUTOMATED_TEST / SECURITY: tests/test_openai_assist.py — Credential redaction, store:false, candidate-only authority, strict schemas, budget hard stop, and isolation gates pass.
- END_TO_END / END_TO_END: artifacts/jira_evidence/POST-SUBTASK-164.json — Classify a pinned quarantine/schema-drift sample, compare deterministic and model routes, and prove outputs only prioritize remediation while authoritative quarantine remains unchanged.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Pin policy, prompt, schema, model, reasoning, source, request/response, cost, code, and runtime identities.

## Evidence to return

- `artifacts/jira_evidence/POST-SUBTASK-164.json` with one evidence row per acceptance criterion and exact artifact hashes.
- Request/job/Jira/source/capture/prompt/schema/model/reasoning identities; estimated and actual tokens/cost; validation and disposition.
- Plan-hash, stage-release, allocation/model-cap, historical-usage mapping, Nano/4o Mini/Luna/Terra/Sol comparison, and Terra/Sol hard-case value evidence.
- Cleanup record for remote files where practical and abandoned local temporary files, plus remaining review/quarantine items.
- Exact commands, exit codes, relevant output, failed/negative cases, and downstream readiness changes.

## End-to-end handoff

Classify a pinned quarantine/schema-drift sample, compare deterministic and model routes, and prove outputs only prioritize remediation while authoritative quarantine remains unchanged.

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

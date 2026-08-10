# AI Work Packet — POST-SUBTASK-166

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Scale empirically validated formats, reconcile usage, clean payloads, and publish the OpenAI handoff

## Why?

The mandatory OpenAI assistive-plane contract requires an executable, independently evidenced work unit rather than an untracked direct API call.

## Atomic execution scope

Execute POST-SUBTASK-166 within the optional OpenAI assistive plane. Consume `POST-SUBTASK-162`, `POST-SUBTASK-163`, `POST-SUBTASK-164`; produce `artifacts/openai_assist/final_handoff.json`, `artifacts/jira_evidence/POST-SUBTASK-166.json`; preserve the deterministic forecast path and candidate-only authority boundary.

### In scope

- Perform the exact action: Scale empirically validated formats, reconcile usage, clean payloads, and publish the OpenAI handoff.
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
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `NOT_STARTED` → `OPERATING`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-166`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-166_scale_empirically_validated_formats_reconcile_usage_clean_payloads_and_publish_the_openai_ha.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-166.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-166`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/OPENAI_ASSISTIVE_PLANE.md
- configs/openai_assist_policy.json
- configs/openai_task_registry.json
- schemas/openai/assistive_candidate.schema.json
- docs/final/CODEX_HANDOFF.md

## Dependencies that must already be complete

- POST-SUBTASK-162
- POST-SUBTASK-163
- POST-SUBTASK-164

## Files I may modify or create

- artifacts/openai_assist/final_handoff.json
- docs/operations/OPENAI_ASSISTIVE_PLANE.md
- artifacts/jira_evidence/POST-SUBTASK-166.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- release-readiness
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

- artifacts/openai_assist/final_handoff.json
- artifacts/jira_evidence/POST-SUBTASK-166.json

## Acceptance criteria

1. Only pilot formats meeting predeclared empirical rules scale; failed, uneconomic, unsupported, unstable, or high-review formats remain shadow/quarantined/rejected.
2. Usage reconciles every reservation, synchronous/Batch job, model/effort, token, dollar, allocation, threshold alert, remaining budget, disposition, improvement, and unresolved review.
3. Remote Batch files are removed after verified local preservation where practical; abandoned local tmp/partial files are removed; immutable accepted evidence remains content-addressed.
4. All downstream Jira, PR, repository, provenance, secret, PIT/leakage/identity, and full-suite gates pass without any scientific-readiness overclaim.

## Tests / validation

- EXISTING_AUTOMATED_TEST / SECURITY: tests/test_openai_assist.py — Credential redaction, store:false, candidate-only authority, strict schemas, budget hard stop, and isolation gates pass.
- END_TO_END / END_TO_END: artifacts/jira_evidence/POST-SUBTASK-166.json — Run the validated scale-out and final reconciliation, demonstrate deterministic fallback on provider failure, clean reconstructible artifacts, and publish an exact resumable handoff with remaining budget.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Pin policy, prompt, schema, model, reasoning, source, request/response, cost, code, and runtime identities.

## Evidence to return

- `artifacts/jira_evidence/POST-SUBTASK-166.json` with one evidence row per acceptance criterion and exact artifact hashes.
- Request/job/Jira/source/capture/prompt/schema/model/reasoning identities; estimated and actual tokens/cost; validation and disposition.
- Cleanup record for remote files where practical and abandoned local temporary files, plus remaining review/quarantine items.
- Exact commands, exit codes, relevant output, failed/negative cases, and downstream readiness changes.

## End-to-end handoff

Run the validated scale-out and final reconciliation, demonstrate deterministic fallback on provider failure, clean reconstructible artifacts, and publish an exact resumable handoff with remaining budget.

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

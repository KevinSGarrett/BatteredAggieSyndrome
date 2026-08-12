# AI Work Packet — POST-SUBTASK-198

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Implement the non-billable provider-neutral OpenRouter foundation, USD 0 hard stop, privacy controls, storage, schemas, and worker isolation

## Why?

The mandatory OpenAI assistive-plane contract requires an executable, independently evidenced work unit rather than an untracked direct API call.

## Atomic execution scope

Implement and integrate the governed foundation and public capability evidence. Paid inference is out of scope and must be rejected locally before network dispatch.

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
- Governance traceability gate: `POST-SUBTASK-198`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-198_implement_the_non_billable_provider_neutral_openrouter_foundation_usd_0_hard_stop_privacy_co.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-198.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-198`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/OPENAI_ASSISTIVE_PLANE.md
- configs/openai_assist_policy.json
- configs/openai_task_registry.json
- schemas/openai/assistive_candidate.schema.json
- docs/final/CODEX_HANDOFF.md

## Dependencies that must already be complete

- POST-SUBTASK-160

## Files I may modify or create

- configs/assistive_provider_registry.json
- configs/openrouter_assist_policy.json
- configs/openrouter_task_registry.json
- schemas/assistive
- src/aggie_analytics/assistive_plane
- tools/openrouter_assist.py
- tools/refresh_openrouter_model_catalog.py
- tools/sync_openrouter_jira_graph.py
- tools/validate_openrouter_assist.py
- tools/validate_repository.py
- tests/test_openrouter_assist.py
- governance/OPENROUTER_ASSISTIVE_PLANE.md
- governance/SOURCE_OF_TRUTH_MAP.md
- docs/architecture/OPENROUTER_ASSISTIVE_PLANE.md
- docs/operations/OPENROUTER_ASSISTIVE_PLANE.md
- jira/tools/import_bat_live.py
- jira/tools/jira_pack_lib.py
- jira/records/issues/subtasks/POST-SUBTASK-196_capture_and_gate_post_2022_national_play_drive_history.json
- artifacts/jira_evidence/POST-SUBTASK-198.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- operations-security
- assistive-plane
- openrouter

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

- artifacts/jira_evidence/POST-SUBTASK-198.json

## Acceptance criteria

1. One provider-neutral dispatcher and one OpenRouter backend own admission, credential loading, redaction, strict schemas, request identity, retries, storage, provenance, usage/cost validation, and disposition.
2. The production ledger hard-stops every billable request at exactly USD 0.00 before network dispatch and transfers no direct OpenAI funds.
3. Provider defaults require parameter support, deny data collection, require ZDR, and disable fallback; exact routes remain unapproved pending endpoint and empirical evidence.
4. Public official documentation and model catalog are content-addressed outside Git; qwen/qwen3-coder-next remains a capability candidate only.
5. Worker packets and patch paths cannot access .env, .git, protected truth, external data, or out-of-scope paths; deterministic validators retain all authority.
6. Focused, repository, provenance, Jira, secret, and full-suite validation pass through normal PR integration.

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

# AI Work Packet — POST-SUBTASK-203

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Qualify local Ollama Qwen on real strict-schema, reconciliation, and code-review work

## Why?

The mandatory OpenAI assistive-plane contract requires an executable, independently evidenced work unit rather than an untracked direct API call.

## Atomic execution scope

Preserve the completed negative qualification for the exact qwen2.5:7b-instruct and qwen3-vl evidence-critical routes, enforce those rejections at admission, and run separately keyed shadow qualifications for qwen2.5-coder and bge-m3 on better-matched workloads.

### In scope

- Perform the exact action: Build the local gold corpus and evaluation harness and compare Luna, Terra, and Sol.
- Use one governed controller, strict Structured Outputs, minimized cited evidence, content-addressed external storage, deterministic validation, and locally enforced cost admission.
- Preserve abstentions, conflicts, schema failures, unsupported facts, partial batch failures, and negative empirical results.

### Out of scope

- Any direct model write to canonical data, PIT state, labels, protected evaluation, promotion, forecasts, BAS, Aggie Excess, or publication state.
- Scattered OpenAI API calls, hosted-Evals dependence, prompt ingestion of secrets or whole data lakes, or bypass of the USD 100 ledger hard stop.
- Changing protected requirements, judging rules, split seals, or scientific acceptance thresholds merely to obtain a passing result.
- Blocking historical expansion or deterministic/local work when the optional provider is unavailable.

## Current gate state

- Workflow: `DONE`
- Ready: `false`
- Priority: `P0`
- Critical path: `false`
- Execution lane: `RESEARCH_LANE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `NOT_STARTED` → `EMPIRICALLY_VALIDATED`
- Evidence state: `VERIFIED`
- Governance traceability gate: `POST-SUBTASK-203`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-203_qualify_local_ollama_qwen_on_real_strict_schema_reconciliation_and_code_review_work.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-203.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-203`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/OPENAI_ASSISTIVE_PLANE.md
- configs/openai_assist_policy.json
- configs/openai_task_registry.json
- schemas/openai/assistive_candidate.schema.json
- docs/final/CODEX_HANDOFF.md

## Dependencies that must already be complete

- POST-SUBTASK-201

## Files I may modify or create

- artifacts/assistive/local_qwen_qualification.json
- configs/assistive_route_readiness.json
- artifacts/jira_evidence/POST-SUBTASK-203.json

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

- artifacts/assistive/local_qwen_qualification.json
- configs/assistive_route_readiness.json
- artifacts/jira_evidence/POST-SUBTASK-203.json

## Acceptance criteria

1. Model/runtime/digest/hardware identities and prompt/schema/result dispositions are content-addressed.
2. Strict schema, evidence, abstention, consistency, time/rework, and unsupported-fact results are measured on real work.
3. Candidate outputs cannot bypass deterministic validation or enter canonical/protected truth directly.

## Tests / validation

- EXISTING_AUTOMATED_TEST / SECURITY: tests/test_openai_assist.py — Credential redaction, store:false, candidate-only authority, strict schemas, budget hard stop, and isolation gates pass.
- END_TO_END / END_TO_END: artifacts/jira_evidence/POST-SUBTASK-161.json — Run the versioned local harness over capable-model reference and cheaper routes, preserve raw external results and costs, and publish only a small comparison manifest and empirical route decision.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Pin policy, prompt, schema, model, reasoning, source, request/response, cost, code, and runtime identities.

## Evidence to return

- `artifacts/jira_evidence/POST-SUBTASK-161.json` with one evidence row per acceptance criterion and exact artifact hashes.
- Request/job/Jira/source/capture/prompt/schema/model/reasoning identities; estimated and actual tokens/cost; validation and disposition.
- Cleanup record for remote files where practical and abandoned local temporary files, plus remaining review/quarantine items.
- Exact commands, exit codes, relevant output, failed/negative cases, and downstream readiness changes.

## End-to-end handoff

Run the versioned local harness over capable-model reference and cheaper routes, preserve raw external results and costs, and publish only a small comparison manifest and empirical route decision.

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

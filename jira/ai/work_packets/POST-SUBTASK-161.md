# AI Work Packet — POST-SUBTASK-161

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Build the local gold corpus and evaluation harness and compare Luna, Terra, and Sol

## Why?

The mandatory OpenAI assistive-plane contract requires an executable, independently evidenced work unit rather than an untracked direct API call.

## Atomic execution scope

Execute POST-SUBTASK-161 within the optional OpenAI assistive plane. Consume `POST-SUBTASK-160`; produce `fixtures/openai_assist/eval_gold.jsonl`, `artifacts/openai_assist/model_comparison.json`, `artifacts/jira_evidence/POST-SUBTASK-161.json`; preserve the deterministic forecast path and candidate-only authority boundary.

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

- Workflow: `READY`
- Ready: `true`
- Priority: `P0`
- Critical path: `false`
- Execution lane: `RESEARCH_LANE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `NOT_STARTED` → `EMPIRICALLY_VALIDATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-161`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-161_build_the_local_gold_corpus_and_evaluation_harness_and_compare_luna_terra_and_sol.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-161.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-161`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/OPENAI_ASSISTIVE_PLANE.md
- configs/openai_assist_policy.json
- configs/openai_task_registry.json
- schemas/openai/assistive_candidate.schema.json
- docs/final/CODEX_HANDOFF.md

## Dependencies that must already be complete

- POST-SUBTASK-160

## Files I may modify or create

- fixtures/openai_assist
- src/aggie_analytics/openai_assist/evals.py
- artifacts/openai_assist/model_comparison.json
- tests/test_openai_assist.py
- artifacts/jira_evidence/POST-SUBTASK-161.json

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

- fixtures/openai_assist/eval_gold.jsonl
- artifacts/openai_assist/model_comparison.json
- artifacts/jira_evidence/POST-SUBTASK-161.json

## Acceptance criteria

1. The corpus covers positive, negative, ambiguous, conflicting, schema-drift, PIT-sensitive, target-leakage, abstention, evidence, and entity-merge cases.
2. Luna, Terra, and Sol run at explicit allowed efforts on identical pinned cases and report schema validity, precision/recall, evidence accuracy, abstention, unsupported facts, top-k recall, false merges, repeat consistency, disagreement, cost, review time, and quarantine.
3. Task-specific acceptance rules are predeclared from empirical distributions; no threshold is invented merely to approve a model.

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

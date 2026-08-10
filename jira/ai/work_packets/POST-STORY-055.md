# AI Work Packet — POST-STORY-055

## Packet mode

`AGGREGATE_GATE`

**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets.

## What capability or closure gate am I coordinating?

Bounded OpenAI assistive extraction, entity, quarantine, and availability pilots

## Why?

The mandatory OpenAI assistive-plane contract requires an executable, independently evidenced work unit rather than an untracked direct API call.

## Aggregate integration and closure scope

Execute POST-STORY-055 within the optional OpenAI assistive plane. Consume `POST-SUBTASK-161`; produce `artifacts/jira_evidence/POST-STORY-055.json`; preserve the deterministic forecast path and candidate-only authority boundary.

### In scope

- Perform the exact action: Bounded OpenAI assistive extraction, entity, quarantine, and availability pilots.
- Use one governed controller, strict Structured Outputs, minimized cited evidence, content-addressed external storage, deterministic validation, and locally enforced cost admission.
- Preserve abstentions, conflicts, schema failures, unsupported facts, partial batch failures, and negative empirical results.

### Out of scope

- Any direct model write to canonical data, PIT state, labels, protected evaluation, promotion, forecasts, BAS, Aggie Excess, or publication state.
- Scattered OpenAI API calls, hosted-Evals dependence, prompt ingestion of secrets or whole data lakes, or bypass of the USD 100 ledger hard stop.
- Changing protected requirements, judging rules, split seals, or scientific acceptance thresholds merely to obtain a passing result.
- Blocking historical expansion or deterministic/local work when the optional provider is unavailable.

## Current gate state

- Workflow: `BACKLOG`
- Ready: `false`
- Priority: `P0`
- Critical path: `false`
- Execution lane: `RESEARCH_LANE`
- Execution mode: `AGGREGATE_GATE`
- Maturity before → after: `NOT_STARTED` → `EMPIRICALLY_VALIDATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-161`

## Read first

1. `jira/records/issues/stories/POST-STORY-055_bounded_openai_assistive_extraction_entity_quarantine_and_availability_pilots.json`
2. `jira/sources/issue_source_manifests/POST-STORY-055.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-STORY-055`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/OPENAI_ASSISTIVE_PLANE.md
- configs/openai_assist_policy.json
- configs/openai_task_registry.json
- schemas/openai/assistive_candidate.schema.json
- docs/final/CODEX_HANDOFF.md

## Dependencies that must already be complete

- POST-SUBTASK-161

## Aggregate packet modification authority

- artifacts/jira_evidence/POST-STORY-055.json

Only aggregate evidence/Jira-state artifacts listed above may be written. Do not edit production code, data, contracts, or child outputs from this packet; open the responsible atomic Subtask packet instead.

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

Review and integrate these child-produced outputs; do not recreate them directly from this aggregate packet:

- artifacts/jira_evidence/POST-STORY-055.json

## Acceptance criteria

1. Pilots A-C receive empirical gold/reference/cheaper-model comparisons, including meaningful Terra/Sol references and Nano/task-specific inexpensive routes, with candidate-only dispositions; Pilot D remains conditional until timestamped evidence exists.
2. Unsupported facts, false merges, leakage, and fabricated timestamps/statistics remain zero for accepted candidates.

## Tests / validation

- EXISTING_AUTOMATED_TEST / SECURITY: tests/test_openai_assist.py — Credential redaction, store:false, candidate-only authority, strict schemas, budget hard stop, and isolation gates pass.
- END_TO_END / END_TO_END: artifacts/jira_evidence/POST-STORY-055.json — Compare all bounded pilot evidence, preserve failures and abstentions, and decide per format whether Luna Batch, Terra review, Sol residue, deterministic-only, or rejection is justified.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Pin policy, prompt, schema, model, reasoning, source, request/response, cost, code, and runtime identities.

## Evidence to return

- `artifacts/jira_evidence/POST-STORY-055.json` with one evidence row per acceptance criterion and exact artifact hashes.
- Request/job/Jira/source/capture/prompt/schema/model/reasoning identities; estimated and actual tokens/cost; validation and disposition.
- Cleanup record for remote files where practical and abandoned local temporary files, plus remaining review/quarantine items.
- Exact commands, exit codes, relevant output, failed/negative cases, and downstream readiness changes.

## End-to-end handoff

Compare all bounded pilot evidence, preserve failures and abstentions, and decide per format whether Nano Batch, a measured 4o Mini/Luna route, Terra complex review, Sol hard residue, deterministic-only, or rejection is justified by accepted evidence-verified records per dollar.

## Stop instead of improvising when

- Stop only the affected API job on missing evidence, invalid schema, unsupported fact, credential exposure, budget rejection, provider failure, or inaccessible source; continue independent work.
- Quarantine the affected result on contradiction, refusal, malformed output, provenance mismatch, PIT/target leakage, or identity risk.
- Stop and preserve evidence rather than inventing facts, timestamps, metrics, identities, or maturity.

## Completion protocol

1. Verify every required child issue is complete at its claimed maturity with verified evidence; do not infer completion from file or code existence.
2. Run or review the declared integrated end-to-end gate and downstream-consumption proof.
3. Create the aggregate evidence manifest with pinned source/data/code/config/model/runtime identities, residual blockers, accepted risks, null/negative results, and gate decisions.
4. Keep this Epic/Story non-READY and non-executable; route any implementation change to a specific atomic Subtask or create a controlled backlog proposal.
5. Update canonical/local Jira state and live Jira operational fields according to `jira/SYNC_CONTRACT.md` only after the aggregate gate is truthfully satisfied.
6. Rebuild all derivatives with `python -B jira/tools/rebuild_all_derivatives.py`, recompute queues, and run `python -B jira/tools/validate_second_pass.py`.
7. Reevaluate downstream gates without weakening protected requirements or hiding incomplete child evidence.

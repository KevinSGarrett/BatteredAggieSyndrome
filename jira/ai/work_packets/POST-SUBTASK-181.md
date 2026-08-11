# AI Work Packet — POST-SUBTASK-181

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Resolve the exact 2022-2023 official A&M depth-chart page noncoverage honestly, add governed visual evidence support, and preserve absence as a validated negative finding rather than fabricating depth-chart data.

## Why?

POST-SUBTASK-167 deliberately preserved 25 official 2022-2023 documents without deterministic depth-chart pages. This unit resolves whether visual layout hid useful depth-chart evidence, adds a governed image-input route for future layout-heavy work, and records the evidence-backed negative result without inventing coverage.

## Atomic execution scope

Build and independently validate a deterministic and governed visual negative review of the exact 25 official A&M 2022-2023 depth-chart page noncoverage documents.

### In scope

- Exact immutable 25-document noncoverage population from the 2022-2023 official A&M weekly game-note captures.
- Deterministic page classification, visual rendering, replay, governed image-input controller support, two-case GPT-4o Mini QA, strict output correction, negative-finding preservation, provenance, budget reporting, and cleanup.

### Out of scope

- Treating prior-game starting-lineup tables, start charts, roster pages, or career starts as pregame depth charts or current availability evidence.
- Fabricating historical publication timestamps, depth-chart order, player availability, injuries, identities, or facts absent from the cited page.
- Automatic Batch scale-out, canonical/PIT/training/protected admission, production promotion, forecast publication, final historical readiness, A&M lift, BAS, Aggie Excess, or any scientific claim.

## Current gate state

- Workflow: `IN_PROGRESS`
- Ready: `false`
- Priority: `P0`
- Critical path: `false`
- Execution lane: `RESEARCH_LANE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `VALIDATED_TEXT_ONLY_DEPTH_PAGE_PILOT_WITH_25_DOCUMENT_NONCOVERAGE` → `EMPIRICALLY_VALIDATED_VISUAL_NEGATIVE_FINDING_AND_GOVERNED_IMAGE_INPUT`
- Evidence state: `PARTIAL`
- Governance traceability gate: `POST-SUBTASK-167`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-181_recover_2022_2023_official_a_m_depth_chart_page_noncoverage_in_governed_shadow_mode.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-181.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-181`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- artifacts/pit/historical_tamu_official_depth_chart_evidence_gate.json
- artifacts/openai_assist/depth_chart_pilot.json
- configs/openai_depth_chart_pilot.json
- docs/final/CODEX_HANDOFF.md
- governance/PROTECTED_ACCEPTANCE_RULES.md

## Dependencies that must already be complete

- POST-SUBTASK-167

## Files I may modify or create

- configs/openai_depth_chart_noncoverage_review.json
- configs/openai_task_registry.json
- configs/openai_assist_policy.json
- schemas/openai/depth_chart_noncoverage_visual.schema.json
- prompts/openai_assist/depth_chart_noncoverage_visual_v1.txt
- src/aggie_analytics/openai_assist/controller.py
- tools/build_tamu_depth_chart_noncoverage_review.py
- tools/validate_tamu_depth_chart_noncoverage_review.py
- tools/run_openai_depth_chart_noncoverage_visual_review.py
- tools/validate_openai_assist.py
- tests/test_openai_assist.py
- tests/test_historical_known_at_recovery_contract.py
- artifacts/openai_assist/depth_chart_noncoverage_visual_review.json
- artifacts/openai_assist/continuous_operations.json
- artifacts/pit/historical_tamu_official_depth_chart_noncoverage_gate.json
- artifacts/pit/historical_known_at_replay_gate.json
- configs/historical_known_at_recovery_contract.json
- artifacts/jira_evidence/POST-SUBTASK-181.json
- docs/architecture/OPENAI_ASSISTIVE_PLANE.md
- docs/operations/OPENAI_ASSISTIVE_PLANE.md
- governance/OPENAI_ASSISTIVE_PLANE.md
- jira

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- player-context-intelligence
- data-ingestion
- pit-temporal
- validation-promotion

## What I must not modify or weaken

- governance/PROTECTED_ACCEPTANCE_RULES.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv
- governance/THRESHOLD_PRECOMMITMENT_REGISTRY.csv

## Exact outputs / integrated artifacts

Produce and validate these outputs within this atomic work unit:

- configs/openai_depth_chart_noncoverage_review.json
- schemas/openai/depth_chart_noncoverage_visual.schema.json
- prompts/openai_assist/depth_chart_noncoverage_visual_v1.txt
- tools/build_tamu_depth_chart_noncoverage_review.py
- tools/validate_tamu_depth_chart_noncoverage_review.py
- tools/run_openai_depth_chart_noncoverage_visual_review.py
- artifacts/openai_assist/depth_chart_noncoverage_visual_review.json
- artifacts/pit/historical_tamu_official_depth_chart_noncoverage_gate.json
- artifacts/jira_evidence/POST-SUBTASK-181.json
- <external-data-root>/quarantine/historical_known_at/sha256/e67558ab5a406e7394c2759e39ad6d2cec1ec04227b37b5441c340f09170e027
- <external-data-root>/validation/BAT-538/depth_chart_noncoverage_review_e67558ab_validation.json
- <external-data-root>/openai/evals/sha256

## Acceptance criteria

1. The exact 25 immutable official Texas A&M 2022-2023 weekly game-note documents recorded as deterministic depth-chart page noncoverage by POST-SUBTASK-167 remain the only admitted population; no source, season, document, page, or authority is silently broadened.
2. Every source PDF, acquisition manifest, prior depth-page candidate, selected review page, rendered page image, prompt, schema, request, response, and result is content-addressed and stored outside Git where bulk or operational.
3. Deterministic full-population review distinguishes historical STARTING LINEUPS tables from pregame depth charts, preserves an UNKNOWN historical publication time, and never fabricates a depth chart from a roster, start chart, or prior-game lineup table.
4. Governed OpenAI visual QA uses the Responses API with store:false, strict task-specific Structured Outputs, budget admission, source hashes, exact page locators, evidence validation, and candidate-only authority.
5. The first generic-schema duplicate-field failure remains preserved as a negative finding; the corrected fixed-object schema must pass both predeclared 2022 and 2023 format cases exactly before its candidates are accepted for review evidence.
6. No result writes canonical entities, PIT state, training features, labels, protected evaluation, model promotion, forecasts, publication state, BAS, or Aggie Excess, and the absence of depth-chart evidence remains an explicit domain gap rather than an inferred fact population.

## Tests / validation

- NEW_AUTOMATED_TEST_REQUIRED / SECURITY: tests/test_openai_assist.py — External visual evidence admission, PNG identity/dimensions, multimodal request structure, image token/cost estimate, redaction, store:false, strict schema, and invalid attachment rejection remain deterministic.
- END_TO_END / END_TO_END: artifacts/jira_evidence/POST-SUBTASK-181.json — All 25 immutable PDFs, selected historical lineup pages, rendered images, negative classifications, mutation checks, byte-identical replay, OpenAI visual candidates, authority boundaries, and budget evidence pass independently.

## Evidence to return

- Exact acquisition, depth-page candidate, 25 source PDF, selected page text, rendered image, payload, manifest, prompt, schema, request, response, usage-ledger, validation, replay, and cleanup hashes.
- Documents and pages by season, deterministic classifications, visual sample identities, initial failed-output disposition, corrected exact-output results, calls/tokens/cost by model, remaining budget, and Batch nonadmission reason.
- Repository/OpenAI/provenance/Jira/secret/full-suite validator results, PR and merge identities, live Jira comments/transitions/links, and explicit protected nonclaims.

## End-to-end handoff

Rejoin POST-SUBTASK-167 noncoverage rows to the exact acquisition manifest and immutable PDFs; verify 25 documents, 12/13 season counts, one STARTING LINEUPS page per document, zero explicit depth-chart headings, deterministic rendering, payload/image identities, mutation rejection, byte-identical replay, strict OpenAI visual schema behavior, budget settlement, candidate-only authority, and no canonical/PIT/training/protected writes.

## Stop instead of improvising when

- Stop and quarantine the affected document or model result on source hash, page count, heading, image, schema, evidence, budget, provenance, replay, credential, or authority failure.
- Preserve valid negative findings and continue unrelated historical expansion and modeling; partial source or OpenAI failure must not globally block the project.
- Do not weaken the distinction between historical lineups and pregame depth charts or any PIT/protected boundary to manufacture coverage.

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

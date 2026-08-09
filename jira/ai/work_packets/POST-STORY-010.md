# AI Work Packet — POST-STORY-010

## Packet mode

`AGGREGATE_GATE`

**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets.

## What capability or closure gate am I coordinating?

Acquire, profile, and assign tiered eligibility to the expanded national core and supporting-domain history

## Why?

This coherent capability closes a defined portion of Immutable national historical data materialization and creates a verifiable output for the next dependency stage.

## Aggregate integration and closure scope

Execute POST-SUBTASK-028 through POST-SUBTASK-030 as the expanded-history acquisition/profile/eligibility chain. Target approximately 2010-2025 and earlier supported seasons, preserve the bounded 2022-2025 tranche as nonterminal, and hand explicit season/domain/use tiers plus negative evidence to immutable national-lake work.

### In scope

- Complete and verify POST-SUBTASK-028 expanded immutable acquisition across every useful approved core and supporting domain.
- Complete and verify POST-SUBTASK-029 independent population profiling across all required source/season/team/domain/schema/provenance/PIT dimensions.
- Complete and verify POST-SUBTASK-030 tiered season/domain/use eligibility without global rejection of partial older seasons or unsupported promotion.
- Preserve the bounded 2022-2025 tranche as nonterminal and target approximately 2010-2025 plus earlier quality-supported seasons.
- Integrate child outputs through final gate POST-SUBTASK-030 with all partial, negative, and provider-limitation evidence preserved.

### Out of scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/rights/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

## Current gate state

- Workflow: `BACKLOG`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `SHARED_CONTRACT`
- Execution mode: `AGGREGATE_GATE`
- Maturity before → after: `SCAFFOLD` → `INTEGRATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-033`

## Read first

1. `jira/records/issues/stories/POST-STORY-010_player_roster_recruiting_market_weather_and_contextual_raw_domains.json`
2. `jira/sources/issue_source_manifests/POST-STORY-010.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-STORY-010`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_w19_foundation.py
- src/aggie_analytics/data/adapters.py
- src/aggie_analytics/data/contracts.py
- src/aggie_analytics/data/snapshots.py
- docs/101_W19_FOUNDATION_IMPLEMENTATION.md
- docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md

## Dependencies that must already be complete

- POST-SUBTASK-027

## Aggregate packet modification authority

- artifacts/jira_evidence/POST-STORY-010.json

Only aggregate evidence/Jira-state artifacts listed above may be written. Do not edit production code, data, contracts, or child outputs from this packet; open the responsible atomic Subtask packet instead.

## Components in scope

- raw-snapshots
- raw-data

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

- artifacts/data_lake/historical_expansion_acquisition_manifest.json
- artifacts/data_lake/historical_expansion_population_profile.json
- artifacts/data_lake/historical_expansion_eligibility_gate.json

## Acceptance criteria

1. All child Subtasks satisfy their expanded-history issue-specific observable checks and preserve required positive, partial, and negative evidence.
2. The final child gate POST-SUBTASK-030 verifies the combined output and explicitly approves, partially approves by tier, blocks, rejects, or defers downstream use.
3. The bounded 2022-2025 tranche is preserved as nonterminal, no incomplete domain globally discards otherwise useful history, and no unsupported domain is silently promoted.
4. No child or aggregate completion resolves GAP-002 or authorizes model/scientific claims before all applicable downstream chronological/PIT and protected gates pass.

## Tests / validation

- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tests/test_w19_foundation.py — Run and retain the result when this issue touches the covered contract.
- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tools/validate_w19_foundation.py — Run and retain the result when this issue touches the covered contract.
- END_TO_END / END_TO_END: POST-SUBTASK-030 — The final child gate `POST-SUBTASK-030` must prove the integrated Story outcome and downstream-consumable output.
- REPRODUCIBILITY / REPRODUCIBILITY: STORY_EVIDENCE_MANIFEST — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Evidence to return

- Verified child completion/evidence manifests for POST-SUBTASK-028, POST-SUBTASK-029, POST-SUBTASK-030.
- Final gate decision from `POST-SUBTASK-030` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## End-to-end handoff

A clean expanded-history run produces immutable captures, deterministic cross-domain profile and tiered eligibility, preserved negative evidence, and a non-bypassable downstream readiness decision.

## Stop instead of improvising when

- Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs.

## Completion protocol

1. Verify every required child issue is complete at its claimed maturity with verified evidence; do not infer completion from file or code existence.
2. Run or review the declared integrated end-to-end gate and downstream-consumption proof.
3. Create the aggregate evidence manifest with pinned source/data/code/config/model/runtime identities, residual blockers, accepted risks, null/negative results, and gate decisions.
4. Keep this Epic/Story non-READY and non-executable; route any implementation change to a specific atomic Subtask or create a controlled backlog proposal.
5. Update canonical/local Jira state and live Jira operational fields according to `jira/SYNC_CONTRACT.md` only after the aggregate gate is truthfully satisfied.
6. Rebuild all derivatives with `python -B jira/tools/rebuild_all_derivatives.py`, recompute queues, and run `python -B jira/tools/validate_second_pass.py`.
7. Reevaluate downstream gates without weakening protected requirements or hiding incomplete child evidence.

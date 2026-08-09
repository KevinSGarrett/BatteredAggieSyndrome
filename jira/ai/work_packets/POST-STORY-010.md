# AI Work Packet — POST-STORY-010

## Packet mode

`AGGREGATE_GATE`

**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets.

## What capability or closure gate am I coordinating?

Expand the validated contemporary tranche to the maximum quality-supported national history, targeting approximately 2010-2025 and earlier seasons while preserving tiered domain eligibility.

## Why?

This coherent capability closes a defined portion of Immutable national historical data materialization and creates a verifiable output for the next dependency stage.

## Aggregate integration and closure scope

Deliver Story POST-STORY-010 (Historical expansion across core and supporting domains) as one coherent, gated capability inside Epic POST-EPIC-003. Execute child subtasks POST-SUBTASK-028, POST-SUBTASK-029, POST-SUBTASK-030 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-030` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### In scope

- Complete and verify child `POST-SUBTASK-028` — Expand immutable national core and supporting-domain history to the maximum quality-supported seasons.
- Complete and verify child `POST-SUBTASK-029` — Profile supporting-domain schema, historical coverage, timestamp quality, upstream lineage, and nonblocking source-policy metadata.
- Complete and verify child `POST-SUBTASK-030` — Gate domain-by-domain production, experimental, conditional, rejected, or unavailable eligibility.
- Integrate the child outputs and execute final gate `POST-SUBTASK-030`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Out of scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

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

1. Preserve 2022-2025 as a bounded nonterminal tranche; target approximately 2010-2025 and earlier quality-supported seasons across teams, schedules, games, outcomes, drives, plays, team/player box scores, rosters, rankings, venues, advanced statistics, structured gamebook equivalents, and useful context. Record source/endpoint, season/type, team/game, domain/grain, schema/version, immutable identity, missingness, provider failures, and historical known-at/PIT state without discarding a useful season because another domain is incomplete.
2. The declared output `artifacts/data_lake/historical_expansion_acquisition_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
4. Coverage and timestamp quality are measured by season/team/source/domain, with A&M detail reported separately and upstream-equivalent feeds not miscounted as independent corroboration.
5. The declared output `artifacts/data_lake/context_population_profile.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
6. Closing market, realized weather, final participation, restricted, thin, or unsupported domains cannot enter earlier production cutoffs or block the core v1 without explicit evidence.
7. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

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

The expanded manifest is deterministic and consumable by the profiling step, preserves partial seasons and missing domains, and never treats rights metadata or the 2022-2025 tranche as a terminal-history gate.

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

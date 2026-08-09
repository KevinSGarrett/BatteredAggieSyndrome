# AI Work Packet — POST-SUBTASK-028

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Acquire immutable expanded national core and supporting-domain history, targeting approximately 2010-2025 and earlier quality-supported seasons

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-010: Player, roster, recruiting, market, weather, and contextual raw domains.

## Atomic execution scope

Execute the critical-path historical-expansion acquisition entrypoint after the validated bounded 2022-2025 tranche. Inventory and acquire the maximum quality-supported national history, targeting approximately 2010-2025 and extending earlier where supported, across teams, schedules, games, official outcomes, drives, plays, team/player box scores, rosters, rankings, venues, advanced game statistics, structured gamebook-equivalent data, and useful supporting context. Preserve source/endpoint, request, season/type, team/game, domain/grain, schema/version, immutable hash/path, retrieval/known-at, provider-failure, and rights identities; hand the deterministic manifest to POST-SUBTASK-029.

### In scope

- Preserve the validated 2022-2025 tranche unchanged as a bounded input and expand beyond it.
- Acquire every useful approved domain available per season: teams, schedules, games, official outcomes, drives, plays, team/player box scores, rosters, rankings, venues, advanced game statistics, structured gamebook equivalents, and useful approved supporting context.
- Use approved direct APIs/downloads and permitted Scrapfly, ScraperAPI, browser, Docker, or equivalent routes autonomously; substitute sources when a preferred route fails.
- Write bulk raw and normalized payloads only below AGGIE_ANALYTICS_DATA_ROOT as immutable content-addressed captures.
- Record partial seasons, missing domains, schema drift, failed endpoints, reconciliation candidates, and historical known-at/PIT limitations as evidence.
- Produce and validate `artifacts/data_lake/historical_expansion_acquisition_manifest.json` and hand it to POST-SUBTASK-029.

### Out of scope

- Claiming that the bounded 2022-2025 tranche is terminal national history or the default final training population.
- Discarding an otherwise useful season solely because player, roster, play-by-play, gamebook, box-score, or advanced-stat coverage is incomplete.
- Promoting incomplete evidence into an unsupported domain, fabricating completeness thresholds, or weakening protected PIT/target-game rules.
- Committing bulk raw/normalized source data, credentials, or restricted payloads to Git, Jira, logs, screenshots, or model prompts.
- Claiming production model readiness, champion performance, A&M lift, BAS, Aggie Excess, or GAP-002 resolution.

## Current gate state

- Workflow: `READY`
- Ready: `true`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `DATA_MATERIALIZATION`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `SCAFFOLD` → `IMPLEMENTED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-033`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-028_acquire_timestamped_roster_depth_participation_injury_recruiting_transfer_coachi.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-028.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-028`.
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
- docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md

## Dependencies that must already be complete

- POST-SUBTASK-027

## Files I may modify or create

- artifacts/data_lake/historical_expansion_acquisition_manifest.json
- artifacts/jira_evidence/POST-SUBTASK-028.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

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

Produce and validate these outputs within this atomic work unit:

- artifacts/data_lake/historical_expansion_acquisition_manifest.json

## Acceptance criteria

1. The bounded 2022-2025 population remains identified as the first validated contemporary tranche and is not represented as terminal history, the complete lake, or GAP-002 resolution.
2. The acquisition targets at least approximately 2010-2025, extends earlier where source/domain quality supports it, and records every attempted source/endpoint/season/type/domain outcome without discarding an otherwise useful season because another domain is incomplete.
3. Every capture or failed attempt records source and endpoint, request identity, season and season type, team/game scope where applicable, domain and grain, schema/version, retrieval and known-at state, content hash and immutable external path, pagination, rights class, and provider limitation.
4. The declared output `artifacts/data_lake/historical_expansion_acquisition_manifest.json` is deterministic, provenance-complete, stored without bulk raw data in Git, and consumable by POST-SUBTASK-029.
5. No source availability, completeness threshold, empirical result, model readiness, A&M lift, BAS, Aggie Excess, or GAP-002 closure is fabricated or implied.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w19_foundation.py — Run as a regression check after completing POST-SUBTASK-028; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/data_lake/historical_expansion_acquisition_manifest.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SCIENTIFIC / SCIENTIFIC: artifacts/data_lake/historical_expansion_acquisition_manifest.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- INTEGRATION / INTEGRATION: artifacts/data_lake/historical_expansion_acquisition_manifest.json — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- NEW_AUTOMATED_TEST_REQUIRED / NEW_AUTOMATED_TEST_REQUIRED: NEW_TEST_REQUIRED::POST-SUBTASK-028 — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Evidence to return

- `artifacts/data_lake/historical_expansion_acquisition_manifest.json` with SHA-256, producer command/version, source/endpoint request identities, season/type and domain/grain coverage, schema versions, immutable external paths/hashes, known-at/PIT state, provider failures, and negative findings.
- An acceptance matrix proving the bounded 2022-2025 tranche is nonterminal and every attempted acquisition has a PASS, FAIL, PARTIAL, UNAVAILABLE, or BLOCKED disposition without fabricated completeness.
- Disk/cleanup evidence showing bulk data remained under AGGIE_ANALYTICS_DATA_ROOT and reconstructible temporary or abandoned payloads were removed after validation.
- Exact commands/tool versions, exit codes, redacted credential checks, and downstream POST-SUBTASK-029 consumer validation.

## End-to-end handoff

Validate that the expanded acquisition manifest independently enumerates source/endpoint, season/type, team/game, domain/grain, schema/version, missing/failure, immutable provenance, and historical known-at/PIT state, and that POST-SUBTASK-029 rejects missing, stale, hash-invalid, rights-blocked, or silently terminal-2022-2025 inputs.

## Stop instead of improvising when

- Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.
- Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.
- Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence.

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

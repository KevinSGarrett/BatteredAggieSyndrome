# AI Work Packet — POST-SUBTASK-197

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Acquire and independently gate the maximum quality-supported national NCAA official football gamebook-equivalent evidence without discarding partial domains or broadening protected authority.

## Why?

The historical lake has broad aggregator-derived structured gamebook equivalents and A&M-only official WMT evidence, but no independently acquired national official NCAA contest population. The reviewed SportsDataverse implementation provides mature parsers and an explicit transport strategy that can materially accelerate this missing domain.

## Atomic execution scope

Discover, acquire, normalize, reconcile, validate, and independently domain-gate national official NCAA MFB contest evidence, preserving partial coverage and strict candidate/PIT/provenance boundaries.

### In scope

- Official stats.ncaa.org MFB contest discovery and national identity mapping.
- Immutable acquisition through ordinary HTTP, Scrapfly, ScraperAPI, or browser transport selected by measured technical success.
- Linescore/game information, venue, attendance, officials, drives, team statistics by period, individual player statistics, and play-by-play.
- Independent domain/season/game coverage, schema, reconciliation, provenance, historical known-at/PIT, and candidate-authority gates.
- Approximately 2010-2025 coverage target with earlier extension when source and domain quality support it.

### Out of scope

- Fabricating missing official facts, publication times, contest identities, player identities, statistics, or completeness.
- Treating postgame records as same-game pregame inputs or using target-game outcomes/features at their own forecast cutoff.
- Publishing or committing bulk third-party raw payloads.
- Protected model promotion, champion selection, production forecasts, final historical-population readiness, GAP resolution, protected performance, A&M specialization lift, BAS, Aggie Excess, or scientific claims.

## Current gate state

- Workflow: `IN_PROGRESS`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `DATA_MATERIALIZATION`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `SOURCE_ROUTE_AND_PARSER_CONTRACT_VERIFIED_NO_NATIONAL_OFFICIAL_POPULATION` → `EMPIRICALLY_VALIDATED_DOMAIN_GATED_CANDIDATE_ONLY`
- Evidence state: `PARTIAL`
- Governance traceability gate: `POST-SUBTASK-069`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-197_acquire_and_gate_national_ncaa_official_gamebook_equivalent_evidence.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-197.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-197`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- configs/open_source_integration_registry.json
- src/aggie_analytics/data/open_source.py
- artifacts/data_lake/historical_expansion_acquisition_manifest.json
- artifacts/pit/historical_tamu_official_gamebook_reconciliation_gate.json

## Dependencies that must already be complete

- POST-SUBTASK-025
- POST-SUBTASK-029

## Files I may modify or create

- configs/ncaa_official_gamebook_contract.json
- configs/historical_game_outcome_spine_expansion_contract.json
- configs/ncaa_contest_outcome_reference_adapter_contract.json
- configs/ncaa_contest_reconciliation_expansion_policy.json
- configs/feature_source_research_program.json
- artifacts/data_lake/ncaa_official_gamebook_acquisition_gate.json
- artifacts/data_lake/ncaa_official_outcome_spine_reconciliation_checkpoint.json
- artifacts/jira_evidence/POST-SUBTASK-197.json
- jira/project/JIRA_TARGET_PROFILE.yaml
- src/aggie_analytics/data/historical_game_outcome_spine_expansion.py
- src/aggie_analytics/data/historical_game_outcome_spine_expansion_support.py
- src/aggie_analytics/data/ncaa_contest_outcome_reference_adapter.py
- src/aggie_analytics/data/ncaa_contest_reconciliation_expansion.py
- tools/acquire_ncaa_official_gamebooks.py
- tools/build_historical_game_outcome_spine_expansion.py
- tools/build_ncaa_contest_outcome_reference_adapter.py
- tools/build_ncaa_contest_reconciliation_expansion.py
- tools/validate_historical_game_outcome_spine_expansion.py
- tools/validate_ncaa_contest_outcome_reference_adapter.py
- tools/validate_ncaa_contest_reconciliation.py
- tools/validate_ncaa_official_gamebooks.py
- tests/test_historical_game_outcome_spine_expansion.py
- tests/test_ncaa_contest_outcome_reference_adapter.py
- tests/test_ncaa_contest_reconciliation_expansion.py
- tests/test_ncaa_official_gamebooks.py

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- data-sources
- raw-snapshots
- entity-resolution
- pit
- validation
- jira

## What I must not modify or weaken

- AGENTS.md
- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_ACCEPTANCE_RULES.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv
- src/aggie_analytics/data/snapshots.py
- src/aggie_analytics/entities/contracts.py

## Exact outputs / integrated artifacts

Produce and validate these outputs within this atomic work unit:

- configs/ncaa_official_gamebook_contract.json
- configs/historical_game_outcome_spine_expansion_contract.json
- configs/ncaa_contest_outcome_reference_adapter_contract.json
- configs/ncaa_contest_reconciliation_expansion_policy.json
- configs/feature_source_research_program.json
- artifacts/data_lake/ncaa_official_gamebook_acquisition_gate.json
- artifacts/data_lake/ncaa_official_outcome_spine_reconciliation_checkpoint.json
- artifacts/jira_evidence/POST-SUBTASK-197.json
- jira/project/JIRA_TARGET_PROFILE.yaml
- src/aggie_analytics/data/historical_game_outcome_spine_expansion.py
- src/aggie_analytics/data/ncaa_contest_outcome_reference_adapter.py
- src/aggie_analytics/data/ncaa_contest_reconciliation_expansion.py
- tools/acquire_ncaa_official_gamebooks.py
- tools/build_historical_game_outcome_spine_expansion.py
- tools/build_ncaa_contest_outcome_reference_adapter.py
- tools/build_ncaa_contest_reconciliation_expansion.py
- tools/validate_ncaa_official_gamebooks.py
- tools/validate_historical_game_outcome_spine_expansion.py
- tools/validate_ncaa_contest_outcome_reference_adapter.py
- tools/validate_ncaa_contest_reconciliation.py
- tests/test_historical_game_outcome_spine_expansion.py
- tests/test_ncaa_contest_outcome_reference_adapter.py
- tests/test_ncaa_contest_reconciliation_expansion.py
- tests/test_ncaa_official_gamebooks.py

## Acceptance criteria

1. Discover and pin exact stats.ncaa.org MFB contest identities and source URLs for the maximum quality-supported national population, targeting approximately 2010-2025 and extending earlier only where source quality supports it.
2. Acquire immutable content-addressed official contest captures outside Git for every technically available domain: linescore/game information, venue, attendance, officials, drives, team statistics by period, player statistics, and play-by-play.
3. Reconcile NCAA contest, team, and game identities deterministically to the canonical registry; name-only matches remain candidates or quarantine and may not silently promote canonical identity.
4. Measure and gate source route, endpoint, season/type, game/team, domain/grain, schema/version, missingness, reconciliation, immutable provenance, and historical known-at/PIT eligibility independently.
5. Preserve partial games, seasons, missing tabs, anti-bot failures, schema drift, contradictions, and negative findings without fabricating facts or weakening thresholds.
6. Pass deterministic rebuild, parser, provenance, identity, leakage, PIT, coverage, strict repository, Jira, secret, and external-storage validation before any downstream authority is granted.

## Tests / validation

- NEW_AUTOMATED_TEST_REQUIRED / SOURCE_SCHEMA_AND_NEGATIVE_PATHS: tests/test_ncaa_official_gamebooks.py — Deterministic parser fixtures cover every NCAA contest tab, missing tabs, schema drift, malformed HTML, anti-bot/interstitial payload rejection, and no-fabrication behavior.
- END_TO_END / REAL_DATA_REPRODUCIBILITY: artifacts/data_lake/ncaa_official_gamebook_acquisition_gate.json — A bounded real official-contest sample is fetched, hashed, parsed, reconciled, domain-gated, rebuilt byte-identically, and rejected under unsafe identity/PIT/provenance mutations.

## Evidence to return

- Pinned upstream parser/repository identity and exact source-route capability probes.
- Immutable contest-discovery, raw-capture, and normalization manifests with hashes, timestamps, routes, bytes, and source URLs.
- Per-season/game/domain coverage, missingness, schema drift, conflict, reconciliation, and PIT eligibility ledgers.
- Byte-identical independent rebuild, mutation controls, parser fixtures, and full repository/Jira/secret/provenance validation.
- Protected PR, hosted checks, live Jira integration evidence, and cleanup report.

## End-to-end handoff

Rebuild discovery from pinned source routes; refetch a bounded deterministic sample through each admitted transport; parse every official contest domain; reconcile to canonical games/teams; compare counts, hashes, schemas, missingness, conflicts, chronology, PIT state, and protected exclusions; reproduce all admitted payloads byte-identically; reject unsafe mutations; and remove reconstructible rebuild and browser/proxy temporary artifacts.

## Stop instead of improvising when

- Quarantine a route, contest, season, division, or domain when identity, schema, integrity, malware, credential, private-personal-information, PIT, or leakage validation fails; continue unrelated valid scope.
- Do not claim completeness or downstream authority from a successful bounded sample or from a single provider.
- Never weaken no-fabrication, immutable provenance, target-game exclusion, protected judging, credential, or publication boundaries.

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

<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-197_acquire_and_gate_national_ncaa_official_gamebook_equivalent_evidence.json -->
# POST-SUBTASK-197 — [POST-SUBTASK-197] Acquire and gate national NCAA official gamebook-equivalent evidence

## Canonical metadata

```json
{
  "acceptance_control_ids": [
    "AC-061",
    "AC-073",
    "AC-079"
  ],
  "acceptance_criteria": [
    "Discover and pin exact stats.ncaa.org MFB contest identities and source URLs for the maximum quality-supported national population, targeting approximately 2010-2025 and extending earlier only where source quality supports it.",
    "Acquire immutable content-addressed official contest captures outside Git for every technically available domain: linescore/game information, venue, attendance, officials, drives, team statistics by period, player statistics, and play-by-play.",
    "Reconcile NCAA contest, team, and game identities deterministically to the canonical registry; name-only matches remain candidates or quarantine and may not silently promote canonical identity.",
    "Measure and gate source route, endpoint, season/type, game/team, domain/grain, schema/version, missingness, reconciliation, immutable provenance, and historical known-at/PIT eligibility independently.",
    "Preserve partial games, seasons, missing tabs, anti-bot failures, schema drift, contradictions, and negative findings without fabricating facts or weakening thresholds.",
    "Pass deterministic rebuild, parser, provenance, identity, leakage, PIT, coverage, strict repository, Jira, secret, and external-storage validation before any downstream authority is granted."
  ],
  "adr_ids": [
    "ADR-005",
    "ADR-006",
    "ADR-094"
  ],
  "ai_context_notes": [
    "Use deterministic discovery, transport, parsing, reconciliation, and validation first. Governed OpenAI assistance is eligible only for bounded candidate extraction or schema interpretation when source evidence exists and deterministic parsing is insufficient.",
    "No model may invent records, publication times, identities, statistics, completeness, or canonical acceptance.",
    "Current empirical detail is preserved in artifacts/jira_evidence/POST-SUBTASK-197.json; the canonical Jira Evidence State remains the live-compatible PARTIAL option until the full population and acceptance contract pass.",
    "The current 2022 checkpoint covers 205 exact reconciled contests and 1,230 endpoint identities; 1,155 are captured, 75 remain technical failures, and 75,695 parsed rows remain candidate-only under coverage identity d9c19dee56baac990bf32afd7fca50ae486c064cbf26117644b812a0695133cc."
  ],
  "allowed_modification_paths": [
    "configs/ncaa_official_gamebook_contract.json",
    "configs/historical_game_outcome_spine_expansion_contract.json",
    "configs/ncaa_contest_outcome_reference_adapter_contract.json",
    "configs/ncaa_contest_reconciliation_expansion_policy.json",
    "configs/feature_source_research_program.json",
    "artifacts/data_lake/ncaa_official_gamebook_acquisition_gate.json",
    "artifacts/data_lake/ncaa_official_outcome_spine_reconciliation_checkpoint.json",
    "artifacts/jira_evidence/POST-SUBTASK-197.json",
    "jira/project/JIRA_TARGET_PROFILE.yaml",
    "src/aggie_analytics/data/historical_game_outcome_spine_expansion.py",
    "src/aggie_analytics/data/historical_game_outcome_spine_expansion_support.py",
    "src/aggie_analytics/data/ncaa_contest_outcome_reference_adapter.py",
    "src/aggie_analytics/data/ncaa_contest_reconciliation_expansion.py",
    "tools/acquire_ncaa_official_gamebooks.py",
    "tools/build_historical_game_outcome_spine_expansion.py",
    "tools/build_ncaa_contest_outcome_reference_adapter.py",
    "tools/build_ncaa_contest_reconciliation_expansion.py",
    "tools/validate_historical_game_outcome_spine_expansion.py",
    "tools/validate_ncaa_contest_outcome_reference_adapter.py",
    "tools/validate_ncaa_contest_reconciliation.py",
    "tools/validate_ncaa_official_gamebooks.py",
    "tests/test_historical_game_outcome_spine_expansion.py",
    "tests/test_ncaa_contest_outcome_reference_adapter.py",
    "tests/test_ncaa_contest_reconciliation_expansion.py",
    "tests/test_ncaa_official_gamebooks.py"
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-197_acquire_and_gate_national_ncaa_official_gamebook_equivalent_evidence.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "candidate_only": true,
    "negative_results_preserved": true,
    "protected_nonclaims_required": true,
    "provenance_dimensions": [
      "source_route",
      "endpoint",
      "season_type",
      "game_team",
      "domain_grain",
      "schema_version",
      "capture",
      "known_at_pit",
      "code",
      "config",
      "runtime"
    ]
  },
  "component": "data-sources",
  "components_expected_to_be_touched": [
    "data-sources",
    "raw-snapshots",
    "entity-resolution",
    "pit",
    "validation",
    "jira"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "A content-addressed external discovery and acquisition manifest records exact contest identities, endpoints, timestamps, routes, hashes, bytes, HTTP/provider outcomes, and cleanup disposition.",
    "Every acquired domain has a versioned deterministic normalization schema, explicit coverage and missingness, canonical reconciliation state, and independent eligibility decision.",
    "Official NCAA evidence is reconciled against existing aggregator and A&M-only evidence without treating same-lineage or partial evidence as independent completeness proof.",
    "All accepted factual records retain source evidence; absent, contradictory, or unsupported fields remain missing, conflict, review, or quarantine.",
    "Protected PR integration, exact-main hosted validation, live Jira evidence, canonical completion synchronization, and verified worktree/temp cleanup are complete before Done."
  ],
  "dependencies": [
    "POST-SUBTASK-025",
    "POST-SUBTASK-029"
  ],
  "end_to_end_validation": "Rebuild discovery from pinned source routes; refetch a bounded deterministic sample through each admitted transport; parse every official contest domain; reconcile to canonical games/teams; compare counts, hashes, schemas, missingness, conflicts, chronology, PIT state, and protected exclusions; reproduce all admitted payloads byte-identically; reject unsafe mutations; and remove reconstructible rebuild and browser/proxy temporary artifacts.",
  "epic_id": "POST-EPIC-004",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-197.json",
  "evidence_state": "PARTIAL",
  "execution_lane": "DATA_MATERIALIZATION",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "EMPIRICALLY_VALIDATED_DOMAIN_GATED_CANDIDATE_ONLY",
  "expected_outputs": [
    "configs/ncaa_official_gamebook_contract.json",
    "configs/historical_game_outcome_spine_expansion_contract.json",
    "configs/ncaa_contest_outcome_reference_adapter_contract.json",
    "configs/ncaa_contest_reconciliation_expansion_policy.json",
    "configs/feature_source_research_program.json",
    "artifacts/data_lake/ncaa_official_gamebook_acquisition_gate.json",
    "artifacts/data_lake/ncaa_official_outcome_spine_reconciliation_checkpoint.json",
    "artifacts/jira_evidence/POST-SUBTASK-197.json",
    "jira/project/JIRA_TARGET_PROFILE.yaml",
    "src/aggie_analytics/data/historical_game_outcome_spine_expansion.py",
    "src/aggie_analytics/data/ncaa_contest_outcome_reference_adapter.py",
    "src/aggie_analytics/data/ncaa_contest_reconciliation_expansion.py",
    "tools/acquire_ncaa_official_gamebooks.py",
    "tools/build_historical_game_outcome_spine_expansion.py",
    "tools/build_ncaa_contest_outcome_reference_adapter.py",
    "tools/build_ncaa_contest_reconciliation_expansion.py",
    "tools/validate_ncaa_official_gamebooks.py",
    "tools/validate_historical_game_outcome_spine_expansion.py",
    "tools/validate_ncaa_contest_outcome_reference_adapter.py",
    "tools/validate_ncaa_contest_reconciliation.py",
    "tests/test_historical_game_outcome_spine_expansion.py",
    "tests/test_ncaa_contest_outcome_reference_adapter.py",
    "tests/test_ncaa_contest_reconciliation_expansion.py",
    "tests/test_ncaa_official_gamebooks.py"
  ],
  "files_expected_to_be_read": [
    "artifacts/source_governance/production_source_inventory.csv",
    "configs/open_source_integration_registry.json",
    "docs/OPEN_SOURCE_INTEGRATION_STRATEGY.md",
    "artifacts/data_lake/historical_expansion_acquisition_manifest.json",
    "artifacts/data_lake/historical_expansion_eligibility_gate.json",
    "artifacts/pit/historical_tamu_official_gamebook_reconciliation_gate.json",
    "artifacts/pit/historical_team_box_snapshot_gate.json",
    "artifacts/pit/historical_player_box_snapshot_gate.json"
  ],
  "files_expected_to_be_touched": [
    "configs/ncaa_official_gamebook_contract.json",
    "configs/historical_game_outcome_spine_expansion_contract.json",
    "configs/ncaa_contest_outcome_reference_adapter_contract.json",
    "configs/ncaa_contest_reconciliation_expansion_policy.json",
    "artifacts/data_lake/ncaa_official_gamebook_acquisition_gate.json",
    "artifacts/data_lake/ncaa_official_outcome_spine_reconciliation_checkpoint.json",
    "artifacts/jira_evidence/POST-SUBTASK-197.json",
    "src/aggie_analytics/data/historical_game_outcome_spine_expansion.py",
    "src/aggie_analytics/data/historical_game_outcome_spine_expansion_support.py",
    "src/aggie_analytics/data/ncaa_contest_outcome_reference_adapter.py",
    "src/aggie_analytics/data/ncaa_contest_reconciliation_expansion.py",
    "tools/acquire_ncaa_official_gamebooks.py",
    "tools/build_historical_game_outcome_spine_expansion.py",
    "tools/build_ncaa_contest_outcome_reference_adapter.py",
    "tools/build_ncaa_contest_reconciliation_expansion.py",
    "tools/validate_historical_game_outcome_spine_expansion.py",
    "tools/validate_ncaa_contest_outcome_reference_adapter.py",
    "tools/validate_ncaa_contest_reconciliation.py",
    "tools/validate_ncaa_official_gamebooks.py",
    "tests/test_historical_game_outcome_spine_expansion.py",
    "tests/test_ncaa_contest_outcome_reference_adapter.py",
    "tests/test_ncaa_contest_reconciliation_expansion.py",
    "tests/test_ncaa_official_gamebooks.py"
  ],
  "files_to_inspect": [
    "configs/open_source_integration_registry.json",
    "src/aggie_analytics/data/open_source.py",
    "artifacts/data_lake/historical_expansion_acquisition_manifest.json",
    "artifacts/pit/historical_tamu_official_gamebook_reconciliation_gate.json"
  ],
  "gap_ids": [
    "GAP-002",
    "GAP-006"
  ],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-197_acquire_and_gate_national_ncaa_official_gamebook_equivalent_evidence.md",
  "governance_traceability_gate": "POST-SUBTASK-069",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100505,
  "in_scope": [
    "Official stats.ncaa.org MFB contest discovery and national identity mapping.",
    "Immutable acquisition through ordinary HTTP, Scrapfly, ScraperAPI, or browser transport selected by measured technical success.",
    "Linescore/game information, venue, attendance, officials, drives, team statistics by period, individual player statistics, and play-by-play.",
    "Independent domain/season/game coverage, schema, reconciliation, provenance, historical known-at/PIT, and candidate-authority gates.",
    "Approximately 2010-2025 coverage target with earlier extension when source and domain quality support it."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-554",
  "labels": [
    "post-wave",
    "subtask",
    "historical-expansion",
    "ncaa-official",
    "gamebook-equivalent",
    "stats-ncaa-org",
    "candidate-only",
    "immutable-raw",
    "provenance",
    "pit-gated",
    "partial-domain-admission",
    "local-id-post-subtask-197"
  ],
  "last_content_audit": "2026-08-15",
  "local_id": "POST-SUBTASK-197",
  "maturity_before": "SOURCE_ROUTE_AND_PARSER_CONTRACT_VERIFIED_NO_NATIONAL_OFFICIAL_POPULATION",
  "objective": "Acquire and independently gate the maximum quality-supported national NCAA official football gamebook-equivalent evidence without discarding partial domains or broadening protected authority.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24947",
    "jira_updated_at": "2026-08-15T10:10:03.692-0500",
    "last_synced_at": "2026-08-15T15:10:49.794673+00:00",
    "resolution": "",
    "source_export": "jira/reconciliation/BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "In Progress"
  },
  "out_of_scope": [
    "Fabricating missing official facts, publication times, contest identities, player identities, statistics, or completeness.",
    "Treating postgame records as same-game pregame inputs or using target-game outcomes/features at their own forecast cutoff.",
    "Publishing or committing bulk third-party raw payloads.",
    "Protected model promotion, champion selection, production forecasts, final historical-population readiness, GAP resolution, protected performance, A&M specialization lift, BAS, Aggie Excess, or scientific claims."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-010",
  "phase": "PHASE-1",
  "prerequisites": [
    "BAT-511 / POST-TASK-REPO-REVIEW-001 reviewed and integrated the pinned SportsDataverse NCAA parser boundary.",
    "POST-SUBTASK-025 / BAT-375 and POST-SUBTASK-029 / BAT-379 provide the existing acquisition and population-profile foundations.",
    "Authoritative project credentials and proxy transports are loaded from the ignored root .env without exposure."
  ],
  "primary_source_refs": [
    "SRCREF-02013",
    "SRCREF-02014",
    "SRCREF-02015",
    "SRCREF-02016"
  ],
  "priority": "P0",
  "protected_files_and_interfaces": [
    "AGENTS.md",
    "governance/DO_NOT_DRIFT.md",
    "governance/PROTECTED_ACCEPTANCE_RULES.md",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "src/aggie_analytics/data/snapshots.py",
    "src/aggie_analytics/entities/contracts.py"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [
    "POST-SUBTASK-162",
    "POST-SUBTASK-178",
    "POST-SUBTASK-191",
    "POST-SUBTASK-193"
  ],
  "required_evidence": [
    "Pinned upstream parser/repository identity and exact source-route capability probes.",
    "Immutable contest-discovery, raw-capture, and normalization manifests with hashes, timestamps, routes, bytes, and source URLs.",
    "Per-season/game/domain coverage, missingness, schema drift, conflict, reconciliation, and PIT eligibility ledgers.",
    "Byte-identical independent rebuild, mutation controls, parser fixtures, and full repository/Jira/secret/provenance validation.",
    "Protected PR, hosted checks, live Jira integration evidence, and cleanup report."
  ],
  "required_tests": [
    {
      "classification": "NEW_AUTOMATED_TEST_REQUIRED",
      "expectation": "Deterministic parser fixtures cover every NCAA contest tab, missing tabs, schema drift, malformed HTML, anti-bot/interstitial payload rejection, and no-fabrication behavior.",
      "path": "tests/test_ncaa_official_gamebooks.py",
      "validation_class": "SOURCE_SCHEMA_AND_NEGATIVE_PATHS"
    },
    {
      "classification": "END_TO_END",
      "expectation": "A bounded real official-contest sample is fetched, hashed, parsed, reconciled, domain-gated, rebuilt byte-identically, and rejected under unsafe identity/PIT/provenance mutations.",
      "path": "artifacts/data_lake/ncaa_official_gamebook_acquisition_gate.json",
      "validation_class": "REAL_DATA_REPRODUCIBILITY"
    }
  ],
  "requirement_ids": [
    "REQ-020",
    "REQ-038",
    "REQ-052",
    "REQ-319"
  ],
  "risk_failure_conditions": [
    "NCAA contest IDs are name-only mapped or mismatched to canonical games/teams.",
    "An anti-bot, login, error, or interstitial page is persisted or parsed as a valid gamebook.",
    "Missing tabs, seasons, divisions, or fields are silently zero-filled or promoted as complete.",
    "Capture time is relabeled as historical publication time or postgame target evidence leaks into same-game inputs.",
    "Credentials, proxy tokens, cookies, or authentication headers enter logs, manifests, Git, prompts, or payloads.",
    "Raw third-party payloads enter Git or reconstructible temporary artifacts are abandoned after validation."
  ],
  "risk_ids": [
    "RISK-038",
    "RISK-050",
    "RISK-075",
    "RISK-241"
  ],
  "schema_version": 2,
  "scope": "Discover, acquire, normalize, reconcile, validate, and independently domain-gate national official NCAA MFB contest evidence, preserving partial coverage and strict candidate/PIT/provenance boundaries.",
  "source_ids": [
    "SRC-014",
    "SRC-015",
    "SRC-048",
    "GAP-002",
    "GAP-006",
    "HANDOFF-008"
  ],
  "source_refs": [
    "SRCREF-02013",
    "SRCREF-02014",
    "SRCREF-02015",
    "SRCREF-02016",
    "SRCREF-02017",
    "SRCREF-02018",
    "SRCREF-01564",
    "SRCREF-01565",
    "SRCREF-01566",
    "SRCREF-01651"
  ],
  "stop_conditions": [
    "Quarantine a route, contest, season, division, or domain when identity, schema, integrity, malware, credential, private-personal-information, PIT, or leakage validation fails; continue unrelated valid scope.",
    "Do not claim completeness or downstream authority from a successful bounded sample or from a single provider.",
    "Never weaken no-fabrication, immutable provenance, target-game exclusion, protected judging, credential, or publication boundaries."
  ],
  "supporting_source_refs": [
    "SRCREF-02017",
    "SRCREF-02018",
    "SRCREF-01564",
    "SRCREF-01565",
    "SRCREF-01566",
    "SRCREF-01651"
  ],
  "title": "[POST-SUBTASK-197] Acquire and gate national NCAA official gamebook-equivalent evidence",
  "traceability_inherited_from": [
    "POST-SUBTASK-069"
  ],
  "traceability_resolution": "DIRECT_PLUS_INHERITED_DOMAIN_GATE",
  "unblock_condition": "Source-route capability and contest identity discovery are executable now; partial route/domain failures do not globally block independent valid acquisition.",
  "validation_classes": [
    "REAL_DATA_REPRODUCIBILITY",
    "SOURCE_SCHEMA_AND_NEGATIVE_PATHS"
  ],
  "why_this_exists": "The historical lake has broad aggregator-derived structured gamebook equivalents and A&M-only official WMT evidence, but no independently acquired national official NCAA contest population. The reviewed SportsDataverse implementation provides mature parsers and an explicit transport strategy that can materially accelerate this missing domain.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-197.md",
  "workflow_state": "IN_PROGRESS"
}
```

## Objective

Acquire and independently gate the maximum quality-supported national NCAA official football gamebook-equivalent evidence without discarding partial domains or broadening protected authority.

## Why This Exists

The historical lake has broad aggregator-derived structured gamebook equivalents and A&M-only official WMT evidence, but no independently acquired national official NCAA contest population. The reviewed SportsDataverse implementation provides mature parsers and an explicit transport strategy that can materially accelerate this missing domain.

## Scope

Discover, acquire, normalize, reconcile, validate, and independently domain-gate national official NCAA MFB contest evidence, preserving partial coverage and strict candidate/PIT/provenance boundaries.

### Explicit In Scope

- Official stats.ncaa.org MFB contest discovery and national identity mapping.
- Immutable acquisition through ordinary HTTP, Scrapfly, ScraperAPI, or browser transport selected by measured technical success.
- Linescore/game information, venue, attendance, officials, drives, team statistics by period, individual player statistics, and play-by-play.
- Independent domain/season/game coverage, schema, reconciliation, provenance, historical known-at/PIT, and candidate-authority gates.
- Approximately 2010-2025 coverage target with earlier extension when source and domain quality support it.

### Explicit Out of Scope

- Fabricating missing official facts, publication times, contest identities, player identities, statistics, or completeness.
- Treating postgame records as same-game pregame inputs or using target-game outcomes/features at their own forecast cutoff.
- Publishing or committing bulk third-party raw payloads.
- Protected model promotion, champion selection, production forecasts, final historical-population readiness, GAP resolution, protected performance, A&M specialization lift, BAS, Aggie Excess, or scientific claims.

## Prerequisites

- BAT-511 / POST-TASK-REPO-REVIEW-001 reviewed and integrated the pinned SportsDataverse NCAA parser boundary.
- POST-SUBTASK-025 / BAT-375 and POST-SUBTASK-029 / BAT-379 provide the existing acquisition and population-profile foundations.
- Authoritative project credentials and proxy transports are loaded from the ignored root .env without exposure.

## Hard Dependencies

- POST-SUBTASK-025
- POST-SUBTASK-029

## Blocks

- None.

## Read / Inspect First

- configs/open_source_integration_registry.json
- src/aggie_analytics/data/open_source.py
- artifacts/data_lake/historical_expansion_acquisition_manifest.json
- artifacts/pit/historical_tamu_official_gamebook_reconciliation_gate.json

## Files Expected To Be Modified

- configs/ncaa_official_gamebook_contract.json
- configs/historical_game_outcome_spine_expansion_contract.json
- configs/ncaa_contest_outcome_reference_adapter_contract.json
- configs/ncaa_contest_reconciliation_expansion_policy.json
- artifacts/data_lake/ncaa_official_gamebook_acquisition_gate.json
- artifacts/data_lake/ncaa_official_outcome_spine_reconciliation_checkpoint.json
- artifacts/jira_evidence/POST-SUBTASK-197.json
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

## Components Expected To Be Touched

- data-sources
- raw-snapshots
- entity-resolution
- pit
- validation
- jira

## Protected Files / Interfaces

- AGENTS.md
- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_ACCEPTANCE_RULES.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv
- src/aggie_analytics/data/snapshots.py
- src/aggie_analytics/entities/contracts.py

## Expected Outputs / Artifacts

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

## Direct Requirements

- REQ-020
- REQ-038
- REQ-052
- REQ-319

## Direct Acceptance Controls

- AC-061
- AC-073
- AC-079

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-069`
- Inherited from: POST-SUBTASK-069
- Resolution: `DIRECT_PLUS_INHERITED_DOMAIN_GATE`
- Effective counts: `{}`

## Acceptance Criteria

1. Discover and pin exact stats.ncaa.org MFB contest identities and source URLs for the maximum quality-supported national population, targeting approximately 2010-2025 and extending earlier only where source quality supports it.
2. Acquire immutable content-addressed official contest captures outside Git for every technically available domain: linescore/game information, venue, attendance, officials, drives, team statistics by period, player statistics, and play-by-play.
3. Reconcile NCAA contest, team, and game identities deterministically to the canonical registry; name-only matches remain candidates or quarantine and may not silently promote canonical identity.
4. Measure and gate source route, endpoint, season/type, game/team, domain/grain, schema/version, missingness, reconciliation, immutable provenance, and historical known-at/PIT eligibility independently.
5. Preserve partial games, seasons, missing tabs, anti-bot failures, schema drift, contradictions, and negative findings without fabricating facts or weakening thresholds.
6. Pass deterministic rebuild, parser, provenance, identity, leakage, PIT, coverage, strict repository, Jira, secret, and external-storage validation before any downstream authority is granted.

## Definition of Done

1. A content-addressed external discovery and acquisition manifest records exact contest identities, endpoints, timestamps, routes, hashes, bytes, HTTP/provider outcomes, and cleanup disposition.
2. Every acquired domain has a versioned deterministic normalization schema, explicit coverage and missingness, canonical reconciliation state, and independent eligibility decision.
3. Official NCAA evidence is reconciled against existing aggregator and A&M-only evidence without treating same-lineage or partial evidence as independent completeness proof.
4. All accepted factual records retain source evidence; absent, contradictory, or unsupported fields remain missing, conflict, review, or quarantine.
5. Protected PR integration, exact-main hosted validation, live Jira evidence, canonical completion synchronization, and verified worktree/temp cleanup are complete before Done.

## Required Tests / Validation

- **NEW_AUTOMATED_TEST_REQUIRED** / `SOURCE_SCHEMA_AND_NEGATIVE_PATHS` — `tests/test_ncaa_official_gamebooks.py` — Deterministic parser fixtures cover every NCAA contest tab, missing tabs, schema drift, malformed HTML, anti-bot/interstitial payload rejection, and no-fabrication behavior.
- **END_TO_END** / `REAL_DATA_REPRODUCIBILITY` — `artifacts/data_lake/ncaa_official_gamebook_acquisition_gate.json` — A bounded real official-contest sample is fetched, hashed, parsed, reconciled, domain-gated, rebuilt byte-identically, and rejected under unsafe identity/PIT/provenance mutations.

## Required Evidence

- Pinned upstream parser/repository identity and exact source-route capability probes.
- Immutable contest-discovery, raw-capture, and normalization manifests with hashes, timestamps, routes, bytes, and source URLs.
- Per-season/game/domain coverage, missingness, schema drift, conflict, reconciliation, and PIT eligibility ledgers.
- Byte-identical independent rebuild, mutation controls, parser fixtures, and full repository/Jira/secret/provenance validation.
- Protected PR, hosted checks, live Jira integration evidence, and cleanup report.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "candidate_only": true,
  "negative_results_preserved": true,
  "protected_nonclaims_required": true,
  "provenance_dimensions": [
    "source_route",
    "endpoint",
    "season_type",
    "game_team",
    "domain_grain",
    "schema_version",
    "capture",
    "known_at_pit",
    "code",
    "config",
    "runtime"
  ]
}
```

## End-to-End Validation Requirement

Rebuild discovery from pinned source routes; refetch a bounded deterministic sample through each admitted transport; parse every official contest domain; reconcile to canonical games/teams; compare counts, hashes, schemas, missingness, conflicts, chronology, PIT state, and protected exclusions; reproduce all admitted payloads byte-identically; reject unsafe mutations; and remove reconstructible rebuild and browser/proxy temporary artifacts.

## Expected Maturity After Completion

`EMPIRICALLY_VALIDATED_DOMAIN_GATED_CANDIDATE_ONLY`

## Risk / Failure Conditions

- NCAA contest IDs are name-only mapped or mismatched to canonical games/teams.
- An anti-bot, login, error, or interstitial page is persisted or parsed as a valid gamebook.
- Missing tabs, seasons, divisions, or fields are silently zero-filled or promoted as complete.
- Capture time is relabeled as historical publication time or postgame target evidence leaks into same-game inputs.
- Credentials, proxy tokens, cookies, or authentication headers enter logs, manifests, Git, prompts, or payloads.
- Raw third-party payloads enter Git or reconstructible temporary artifacts are abandoned after validation.

## Stop Conditions

- Quarantine a route, contest, season, division, or domain when identity, schema, integrity, malware, credential, private-personal-information, PIT, or leakage validation fails; continue unrelated valid scope.
- Do not claim completeness or downstream authority from a successful bounded sample or from a single provider.
- Never weaken no-fabrication, immutable provenance, target-game exclusion, protected judging, credential, or publication boundaries.

## Source References

- SRCREF-02013
- SRCREF-02014
- SRCREF-02015
- SRCREF-02016
- SRCREF-02017
- SRCREF-02018
- SRCREF-01564
- SRCREF-01565
- SRCREF-01566
- SRCREF-01651

## AI Context Notes

- Use deterministic discovery, transport, parsing, reconciliation, and validation first. Governed OpenAI assistance is eligible only for bounded candidate extraction or schema interpretation when source evidence exists and deterministic parsing is insufficient.
- No model may invent records, publication times, identities, statistics, completeness, or canonical acceptance.
- Current empirical detail is preserved in artifacts/jira_evidence/POST-SUBTASK-197.json; the canonical Jira Evidence State remains the live-compatible PARTIAL option until the full population and acceptance contract pass.
- The current 2022 checkpoint covers 205 exact reconciled contests and 1,230 endpoint identities; 1,155 are captured, 75 remain technical failures, and 75,695 parsed rows remain candidate-only under coverage identity d9c19dee56baac990bf32afd7fca50ae486c064cbf26117644b812a0695133cc.

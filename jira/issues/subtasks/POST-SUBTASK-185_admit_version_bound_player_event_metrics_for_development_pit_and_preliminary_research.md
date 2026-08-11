<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-185_admit_version_bound_player_event_metrics_for_development_pit_and_preliminary_research.json -->
# POST-SUBTASK-185 — [POST-SUBTASK-185] Admit version-bound player-event metrics for development PIT and preliminary research

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Only exact 2014-2022 event-derived player metric rows from the pinned sportsdataverse/cfbfastR-data commit b865176f908cb6b791dc8e14562c52676f456275 and its 2023-05-05T03:50:21Z public committer time are eligible; source-only, ambiguous-identity, membership-pending, and conflicting rows remain excluded or quarantined.",
    "Eligibility is measured independently by season, metric, canonical game/player/team identity, reconciliation disposition, source known-at time, target cutoff, and missingness; the partial 2020 season remains explicit and no player-box completeness claim is made.",
    "Every admitted source row is known before every 2023-2025 target cutoff, target-game overlap is zero, and no target, outcome, post-cutoff, or fabricated field enters the feature payload.",
    "The output preserves immutable content-addressed source, profile, feature, manifest, validation, and quarantine identities and passes an isolated byte-identical rebuild plus mutation controls.",
    "Authority remains development-only historical known-at player-event metrics and preliminary unprotected feature research; protected training or evaluation, champion or production promotion, forecasts, final historical completeness, A&M lift, BAS, Aggie Excess, and scientific claims remain closed."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "The source is sparse event-derived evidence rather than an official or complete player box score domain.",
    "Cross-route agreement may share ESPN upstream lineage and therefore does not establish independent-source confirmation.",
    "No OpenAI output or model-generated fact participates in acquisition, identity, timing, reconciliation, aggregation, validation, or admission."
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-185_admit_version_bound_player_event_metrics_for_development_pit_and_preliminary_research.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "component": "pit-temporal",
  "components_expected_to_be_touched": [
    "data",
    "pit-temporal",
    "provenance",
    "validation-promotion"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "All 354,082 derived game-player-category-stat aggregates are deterministically dispositioned: 289,897 exact rows are admitted and 64,185 conflict, identity-gap, membership-gap, source-only, or name-conflict rows remain excluded or quarantined.",
    "The immutable c6baa76b development-PIT state contains 7,079 games, 14,073 players, 132 teams, and explicit partial-2020 status; its 5,528 target-game/team rows retain 489 cold starts and 12 feature columns without silent imputation.",
    "All 51 source, mapping, chronology, target exclusion, schema, hash, population, provenance checks, seven mutation controls, and four-payload byte-identical isolated rebuild checks pass.",
    "Canonical Jira, repository evidence, historical recovery gate, and governing goal preserve development-only authority and protected nonclaims.",
    "Historical acquisition and independently useful preliminary modeling continue without declaring final historical-population or production readiness."
  ],
  "dependencies": [
    "POST-SUBTASK-029"
  ],
  "end_to_end_validation": "Re-read the exact pinned reconciliation manifest and source payloads; independently rebuild admitted player-event metrics, canonical team profiles, and target-cutoff features; verify identity, reconciliation disposition, chronology, target exclusion, schemas, counts, quarantines, hashes, authority, and byte identity; then remove reconstructible rebuild output.",
  "epic_id": "POST-EPIC-003",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-185.json",
  "evidence_state": "VERIFIED",
  "execution_lane": "DATA",
  "execution_mode": "HISTORICAL_REFERENCE",
  "expected_maturity_after_completion": "DEVELOPMENT_ONLY_PIT_ADMITTED",
  "expected_outputs": [
    "configs/historical_player_event_metric_pit_contract.json",
    "artifacts/pit/historical_player_event_metric_pit_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-185.json",
    "<external-data-root>/pit_state/historical_known_at/sha256/<dataset_identity>/player_event_metrics.parquet",
    "<external-data-root>/features/historical_known_at/sha256/<dataset_identity>/target_game_team_player_event_features.parquet",
    "<external-data-root>/manifests/historical_known_at/sha256/<dataset_identity>/player_event_metric_pit_manifest.json",
    "<external-data-root>/validation/POST-SUBTASK-185/player_event_metric_pit_validation.json"
  ],
  "files_expected_to_be_read": [
    "configs/historical_known_at_recovery_contract.json",
    "artifacts/pit/historical_known_at_replay_gate.json",
    "configs/historical_player_event_metric_pit_contract.json"
  ],
  "files_expected_to_be_touched": [
    "configs/historical_player_event_metric_pit_contract.json",
    "configs/historical_known_at_recovery_contract.json",
    "src/aggie_analytics/temporal/player_event_metric_pit.py",
    "tools/build_historical_player_event_metric_pit.py",
    "tools/validate_historical_player_event_metric_pit.py",
    "tests/test_historical_player_event_metric_pit.py",
    "tests/test_historical_known_at_recovery_contract.py",
    "artifacts/pit/historical_player_event_metric_pit_gate.json",
    "artifacts/pit/historical_known_at_replay_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-185.json"
  ],
  "gap_ids": [
    "GAP-002",
    "GAP-003"
  ],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-185_admit_version_bound_player_event_metrics_for_development_pit_and_preliminary_research.md",
  "governance_traceability_gate": "POST-SUBTASK-033",
  "historical_classification": "POST_W25_IMPLEMENTATION",
  "import_id": 100493,
  "in_scope": [
    "Exact version-bound 2014-2022 sparse event-derived passing, rushing, receiving, and interception player metrics with defensible pre-target publication time.",
    "Canonical game, player, and team identity validation; reconciliation-disposition gating; explicit quarantine; target-cutoff aggregation; content-addressed provenance; deterministic replay; and development-only PIT admission.",
    "Preliminary unprotected feature candidacy with per-season and per-metric coverage and missingness preserved."
  ],
  "issue_type": "Sub-task",
  "jira_key": "BAT-542",
  "labels": [
    "actionable",
    "post-wave",
    "subtask",
    "historical-expansion",
    "player-stats",
    "pit",
    "development-only",
    "preliminary-unprotected",
    "provenance",
    "local-id-post-subtask-185"
  ],
  "last_content_audit": "2026-08-11",
  "local_id": "POST-SUBTASK-185",
  "maturity_before": "VALIDATED_RECONCILED_CANDIDATE_ONLY",
  "objective": "Admit exact version-bound sparse player-event metrics into a development-only PIT state and preliminary feature layer without overstating player-box completeness or protected authority.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24933",
    "jira_updated_at": "2026-08-11T09:29:08.704-0500",
    "last_synced_at": "2026-08-11T14:43:50.492525+00:00",
    "source_export": "jira/reconciliation/BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "Done"
  },
  "out_of_scope": [
    "Promoting rows with unresolved canonical identity, membership, source-only disposition, or cross-route value/name conflict.",
    "Representing sparse event-derived metrics as complete official player box scores or inventing missing values, publication times, outcomes, identities, or statistics.",
    "Protected training or evaluation, champion or production promotion, forecast publication, final historical readiness, A&M lift, BAS, Aggie Excess, or any scientific result."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-010",
  "phase": "PHASE-1",
  "prerequisites": [
    "Pinned candidate identity 869818c5 and reconciliation manifest 4e20e5a2.",
    "Pinned version-bound repository commit b865176f908cb6b791dc8e14562c52676f456275 and public committer time.",
    "Pinned canonical game, player, and source-team identity evidence plus 2023-2025 target cutoff matrix.",
    "Configured standardized external data root."
  ],
  "primary_source_refs": [
    "SRCREF-02013",
    "SRCREF-02016",
    "SRCREF-02018"
  ],
  "priority": "P0",
  "protected_files_and_interfaces": [
    "AGENTS.md",
    "governance/DO_NOT_DRIFT.md",
    "governance/PROTECTED_ACCEPTANCE_RULES.md",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    "governance/PROTECTED_SPLIT_REGISTRY.csv"
  ],
  "ready": false,
  "record_revision": "1.0",
  "required_evidence": [
    "Exact source commit, candidate manifest, mapping, target replay, contract, code, dataset, payload, manifest, validation, and rollback identities.",
    "Per-season and per-metric source rows, eligible rows, exact identities, conflicts, quarantines, missingness, targets, features, cold starts, bytes, and hashes.",
    "Maximum source known-at/effective times, minimum target cutoff, zero target overlap, no target/outcome fields, mutation controls, and byte-identical rebuild.",
    "Explicit sparse event-derived limitation, development-only PIT/preliminary authority, shared-upstream caveat, and protected/production/scientific nonclaims."
  ],
  "required_tests": [
    {
      "classification": "NEW_AUTOMATED_TEST_REQUIRED",
      "expectation": "Disposition gating, exact canonical identity, sparse metric aggregation, chronology, cold starts, missingness, and protected nonauthority remain deterministic.",
      "path": "tests/test_historical_player_event_metric_pit.py",
      "validation_class": "PIT_LEAKAGE"
    },
    {
      "classification": "END_TO_END",
      "expectation": "The complete external admitted population passes identity, chronology, schema, provenance, mutation, and byte-identical rebuild checks.",
      "path": "artifacts/jira_evidence/POST-SUBTASK-185.json",
      "validation_class": "END_TO_END"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "Any source, reconciliation, mapping, chronology, target overlap, schema, authority, population, hash, or deterministic rebuild identity drifts.",
    "Any target game, outcome field, post-cutoff row, unresolved identity, conflicting value, or fabricated fact enters the admitted payload.",
    "Any sparse development-only artifact is represented as complete player-box, protected, champion, production, forecast, or scientific authority."
  ],
  "risk_ids": [
    "RISK-227",
    "RISK-241"
  ],
  "schema_version": 2,
  "scope": "Convert only exact, version-bound, pre-cutoff, reconciled sparse player-event metric evidence into canonical development-PIT state and target-game/team features with explicit partial coverage.",
  "source_ids": [
    "GAP-002",
    "GAP-003",
    "HANDOFF-003"
  ],
  "source_refs": [
    "SRCREF-02013",
    "SRCREF-02014",
    "SRCREF-02016",
    "SRCREF-02018",
    "SRCREF-02006",
    "SRCREF-01889",
    "SRCREF-01564"
  ],
  "stop_conditions": [
    "Stop the affected row, metric, season, or artifact on source, reconciliation, mapping, chronology, target overlap, schema, authority, population, hash, or deterministic rebuild failure.",
    "Exclude or quarantine only affected evidence; do not block independent domains, acquisition, or preliminary modeling.",
    "Do not open protected promotion until expanded quality-supported history and all applicable W17 gates pass."
  ],
  "supporting_source_refs": [
    "SRCREF-02014",
    "SRCREF-02006",
    "SRCREF-01889",
    "SRCREF-01564"
  ],
  "title": "[POST-SUBTASK-185] Admit version-bound player-event metrics for development PIT and preliminary research",
  "traceability_inherited_from": [
    "POST-SUBTASK-033"
  ],
  "traceability_resolution": "DIRECT_PLUS_INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "END_TO_END",
    "PROVENANCE",
    "REPRODUCIBILITY",
    "PIT_LEAKAGE"
  ],
  "why_this_exists": "The exact 2014-2022 repository player-stat evidence was publicly committed before every 2023-2025 target cutoff, allowing its reconciled sparse player-event metrics to advance development PIT without inventing completeness or protected authority.",
  "work_packet_path": "",
  "workflow_state": "DONE"
}
```

## Objective

Admit exact version-bound sparse player-event metrics into a development-only PIT state and preliminary feature layer without overstating player-box completeness or protected authority.

## Why This Exists

The exact 2014-2022 repository player-stat evidence was publicly committed before every 2023-2025 target cutoff, allowing its reconciled sparse player-event metrics to advance development PIT without inventing completeness or protected authority.

## Scope

Convert only exact, version-bound, pre-cutoff, reconciled sparse player-event metric evidence into canonical development-PIT state and target-game/team features with explicit partial coverage.

### Explicit In Scope

- Exact version-bound 2014-2022 sparse event-derived passing, rushing, receiving, and interception player metrics with defensible pre-target publication time.
- Canonical game, player, and team identity validation; reconciliation-disposition gating; explicit quarantine; target-cutoff aggregation; content-addressed provenance; deterministic replay; and development-only PIT admission.
- Preliminary unprotected feature candidacy with per-season and per-metric coverage and missingness preserved.

### Explicit Out of Scope

- Promoting rows with unresolved canonical identity, membership, source-only disposition, or cross-route value/name conflict.
- Representing sparse event-derived metrics as complete official player box scores or inventing missing values, publication times, outcomes, identities, or statistics.
- Protected training or evaluation, champion or production promotion, forecast publication, final historical readiness, A&M lift, BAS, Aggie Excess, or any scientific result.

## Prerequisites

- Pinned candidate identity 869818c5 and reconciliation manifest 4e20e5a2.
- Pinned version-bound repository commit b865176f908cb6b791dc8e14562c52676f456275 and public committer time.
- Pinned canonical game, player, and source-team identity evidence plus 2023-2025 target cutoff matrix.
- Configured standardized external data root.

## Hard Dependencies

- POST-SUBTASK-029

## Blocks

- None.

## Read / Inspect First

- None.

## Files Expected To Be Modified

- configs/historical_player_event_metric_pit_contract.json
- configs/historical_known_at_recovery_contract.json
- src/aggie_analytics/temporal/player_event_metric_pit.py
- tools/build_historical_player_event_metric_pit.py
- tools/validate_historical_player_event_metric_pit.py
- tests/test_historical_player_event_metric_pit.py
- tests/test_historical_known_at_recovery_contract.py
- artifacts/pit/historical_player_event_metric_pit_gate.json
- artifacts/pit/historical_known_at_replay_gate.json
- artifacts/jira_evidence/POST-SUBTASK-185.json

## Components Expected To Be Touched

- data
- pit-temporal
- provenance
- validation-promotion

## Protected Files / Interfaces

- AGENTS.md
- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_ACCEPTANCE_RULES.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv

## Expected Outputs / Artifacts

- configs/historical_player_event_metric_pit_contract.json
- artifacts/pit/historical_player_event_metric_pit_gate.json
- artifacts/jira_evidence/POST-SUBTASK-185.json
- <external-data-root>/pit_state/historical_known_at/sha256/<dataset_identity>/player_event_metrics.parquet
- <external-data-root>/features/historical_known_at/sha256/<dataset_identity>/target_game_team_player_event_features.parquet
- <external-data-root>/manifests/historical_known_at/sha256/<dataset_identity>/player_event_metric_pit_manifest.json
- <external-data-root>/validation/POST-SUBTASK-185/player_event_metric_pit_validation.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-033`
- Inherited from: POST-SUBTASK-033
- Resolution: `DIRECT_PLUS_INHERITED_DOMAIN_GATE`
- Effective counts: `{}`

## Acceptance Criteria

1. Only exact 2014-2022 event-derived player metric rows from the pinned sportsdataverse/cfbfastR-data commit b865176f908cb6b791dc8e14562c52676f456275 and its 2023-05-05T03:50:21Z public committer time are eligible; source-only, ambiguous-identity, membership-pending, and conflicting rows remain excluded or quarantined.
2. Eligibility is measured independently by season, metric, canonical game/player/team identity, reconciliation disposition, source known-at time, target cutoff, and missingness; the partial 2020 season remains explicit and no player-box completeness claim is made.
3. Every admitted source row is known before every 2023-2025 target cutoff, target-game overlap is zero, and no target, outcome, post-cutoff, or fabricated field enters the feature payload.
4. The output preserves immutable content-addressed source, profile, feature, manifest, validation, and quarantine identities and passes an isolated byte-identical rebuild plus mutation controls.
5. Authority remains development-only historical known-at player-event metrics and preliminary unprotected feature research; protected training or evaluation, champion or production promotion, forecasts, final historical completeness, A&M lift, BAS, Aggie Excess, and scientific claims remain closed.

## Definition of Done

1. All 354,082 derived game-player-category-stat aggregates are deterministically dispositioned: 289,897 exact rows are admitted and 64,185 conflict, identity-gap, membership-gap, source-only, or name-conflict rows remain excluded or quarantined.
2. The immutable c6baa76b development-PIT state contains 7,079 games, 14,073 players, 132 teams, and explicit partial-2020 status; its 5,528 target-game/team rows retain 489 cold starts and 12 feature columns without silent imputation.
3. All 51 source, mapping, chronology, target exclusion, schema, hash, population, provenance checks, seven mutation controls, and four-payload byte-identical isolated rebuild checks pass.
4. Canonical Jira, repository evidence, historical recovery gate, and governing goal preserve development-only authority and protected nonclaims.
5. Historical acquisition and independently useful preliminary modeling continue without declaring final historical-population or production readiness.

## Required Tests / Validation

- **NEW_AUTOMATED_TEST_REQUIRED** / `PIT_LEAKAGE` — `tests/test_historical_player_event_metric_pit.py` — Disposition gating, exact canonical identity, sparse metric aggregation, chronology, cold starts, missingness, and protected nonauthority remain deterministic.
- **END_TO_END** / `END_TO_END` — `artifacts/jira_evidence/POST-SUBTASK-185.json` — The complete external admitted population passes identity, chronology, schema, provenance, mutation, and byte-identical rebuild checks.

## Required Evidence

- Exact source commit, candidate manifest, mapping, target replay, contract, code, dataset, payload, manifest, validation, and rollback identities.
- Per-season and per-metric source rows, eligible rows, exact identities, conflicts, quarantines, missingness, targets, features, cold starts, bytes, and hashes.
- Maximum source known-at/effective times, minimum target cutoff, zero target overlap, no target/outcome fields, mutation controls, and byte-identical rebuild.
- Explicit sparse event-derived limitation, development-only PIT/preliminary authority, shared-upstream caveat, and protected/production/scientific nonclaims.

## Completion Evidence Contract

```json
{}
```

## End-to-End Validation Requirement

Re-read the exact pinned reconciliation manifest and source payloads; independently rebuild admitted player-event metrics, canonical team profiles, and target-cutoff features; verify identity, reconciliation disposition, chronology, target exclusion, schemas, counts, quarantines, hashes, authority, and byte identity; then remove reconstructible rebuild output.

## Expected Maturity After Completion

`DEVELOPMENT_ONLY_PIT_ADMITTED`

## Risk / Failure Conditions

- Any source, reconciliation, mapping, chronology, target overlap, schema, authority, population, hash, or deterministic rebuild identity drifts.
- Any target game, outcome field, post-cutoff row, unresolved identity, conflicting value, or fabricated fact enters the admitted payload.
- Any sparse development-only artifact is represented as complete player-box, protected, champion, production, forecast, or scientific authority.

## Stop Conditions

- Stop the affected row, metric, season, or artifact on source, reconciliation, mapping, chronology, target overlap, schema, authority, population, hash, or deterministic rebuild failure.
- Exclude or quarantine only affected evidence; do not block independent domains, acquisition, or preliminary modeling.
- Do not open protected promotion until expanded quality-supported history and all applicable W17 gates pass.

## Source References

- SRCREF-02013
- SRCREF-02014
- SRCREF-02016
- SRCREF-02018
- SRCREF-02006
- SRCREF-01889
- SRCREF-01564

## AI Context Notes

- The source is sparse event-derived evidence rather than an official or complete player box score domain.
- Cross-route agreement may share ESPN upstream lineage and therefore does not establish independent-source confirmation.
- No OpenAI output or model-generated fact participates in acquisition, identity, timing, reconciliation, aggregation, validation, or admission.

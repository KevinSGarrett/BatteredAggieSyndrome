<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-183_recover_2011_2020_version_bound_play_drive_pit_gaps.json -->
# POST-SUBTASK-183 — [POST-SUBTASK-183] Recover 2011/2020 version-bound play/drive PIT gaps

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "The exact 2011 and 2020 repository payloads are captured outside Git at immutable content-addressed paths and bound to commit b9b838e44f16131b897489e6ae3da355f8c99865 and its 2022-07-25T17:33:07Z public committer time.",
    "Only rows with exact canonical game identity, verified source-team identity, nonempty source effective time, and pre-cutoff source known-at time enter development PIT; affected ambiguous rows are quarantined without discarding otherwise useful seasons or domains.",
    "Cross-route row-count, identifier, content, drive-result, and missing-game differences against the later CFBD supplemental population are measured and preserved; no false one-to-one or completeness claim is created.",
    "The superseding aggregate covers source seasons 2010-2022 at the same target-game/team grain, has zero target-game overlap, excludes target/outcome columns, preserves cold starts and nulls, and passes a byte-identical isolated rebuild.",
    "Authority remains development-only PIT and preliminary unprotected feature research; protected training/evaluation, champion or production promotion, forecast publication, historical completeness, and scientific claims remain closed."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "The immutable repository payload is primary historical evidence; the 2026 CFBD supplemental captures provide reconciliation evidence but do not supply or replace historical known-at timestamps.",
    "This unit supersedes the POST-SUBTASK-176 aggregate while preserving it as the first validated partial-season checkpoint.",
    "No OpenAI output or model-generated fact participates in acquisition, identity, timing, normalization, aggregation, validation, or admission."
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-183_recover_2011_2020_version_bound_play_drive_pit_gaps.json",
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
    "The two source Parquet payloads, exact commit API response, capture manifests, normalized candidate layers, and reconciliation manifest are content-addressed outside Git with verified hashes.",
    "All 234,857 repository plays and 34,810 repository drives are dispositioned; two ambiguous 2020 drives are quarantined and all other eligible rows retain exact canonical game and verified team identity.",
    "The superseding development-only aggregate identity 1bd6f4c6 contains 1,840,951 plays, 264,812 drives, 243 profiles, and 5,528 target-game/team rows over dense 2010-2022 source seasons.",
    "All 46 validation checks, six mutation controls, three-file byte-identical rebuild, relevant tests, repository validators, and integration checks pass.",
    "The next separately lineaged preliminary replay is enabled without claiming protected readiness or final historical completeness."
  ],
  "dependencies": [
    "POST-SUBTASK-174",
    "POST-SUBTASK-176"
  ],
  "end_to_end_validation": "Verify exact raw bytes and commit metadata; rebuild normalized 2011/2020 plays and drives; reconcile against the supplemental population; rebuild the combined 2010-2022 PIT layer; verify identity, chronology, target exclusion, schemas, hashes, counts, quarantines, authority, and byte identity; then remove reconstructible rebuild output.",
  "epic_id": "POST-EPIC-003",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-183.json",
  "evidence_state": "PARTIAL",
  "execution_lane": "DATA",
  "execution_mode": "HISTORICAL_REFERENCE",
  "expected_maturity_after_completion": "DEVELOPMENT_ONLY_PIT_ADMITTED",
  "expected_outputs": [
    "configs/versioned_play_drive_gap_contract.json",
    "configs/historical_play_drive_pit_extension_contract.json",
    "artifacts/pit/historical_play_drive_pit_aggregate_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-183.json",
    "<external-data-root>/raw/historical_known_at/github/sha256/<payload_sha256>/payload.parquet",
    "<external-data-root>/quarantine/historical_known_at/sha256/33f3f3ab/",
    "<external-data-root>/pit_state/historical_known_at/sha256/1bd6f4c6/team_play_drive_profiles.parquet",
    "<external-data-root>/features/historical_known_at/sha256/1bd6f4c6/target_game_team_play_drive_features.parquet",
    "<external-data-root>/validation/POST-SUBTASK-183/play_drive_pit_extension_validation.json"
  ],
  "files_expected_to_be_read": [
    "configs/historical_play_drive_pit_aggregate_contract.json",
    "configs/supplemental_play_drive_gap_contract.json",
    "configs/historical_known_at_recovery_contract.json"
  ],
  "files_expected_to_be_touched": [
    "configs/versioned_play_drive_gap_contract.json",
    "configs/historical_play_drive_pit_extension_contract.json",
    "configs/historical_known_at_recovery_contract.json",
    "src/aggie_analytics/temporal/play_drive_pit.py",
    "tools/build_versioned_play_drive_gap.py",
    "tools/build_historical_play_drive_pit_extension.py",
    "tools/validate_historical_play_drive_pit_extension.py",
    "tests/test_historical_play_drive_pit_extension.py",
    "tests/test_historical_known_at_recovery_contract.py",
    "artifacts/pit/historical_play_drive_pit_aggregate_gate.json",
    "artifacts/pit/historical_known_at_replay_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-183.json"
  ],
  "gap_ids": [
    "GAP-002",
    "GAP-003"
  ],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-183_recover_2011_2020_version_bound_play_drive_pit_gaps.md",
  "governance_traceability_gate": "POST-SUBTASK-033",
  "historical_classification": "POST_W25_IMPLEMENTATION",
  "import_id": 100491,
  "in_scope": [
    "Exact immutable 2011 and 2020 version-bound repository plays and drives with public pre-target commit time.",
    "Canonical game and team identity validation, cross-route reconciliation, explicit quarantine, content-addressed provenance, deterministic replay, and development-only PIT admission.",
    "Dense 2010-2022 play/drive feature candidacy for a separately lineaged preliminary unprotected replay."
  ],
  "issue_type": "Sub-task",
  "jira_key": "BAT-540",
  "labels": [
    "actionable",
    "post-wave",
    "subtask",
    "historical-expansion",
    "plays",
    "drives",
    "pit",
    "development-only",
    "preliminary-unprotected",
    "provenance",
    "local-id-post-subtask-183"
  ],
  "last_content_audit": "2026-08-11",
  "local_id": "POST-SUBTASK-183",
  "maturity_before": "DEVELOPMENT_ONLY_PIT_ADMITTED",
  "objective": "Recover the exact 2011 and 2020 version-bound play/drive populations, reconcile their source differences, and supersede the partial development-only PIT aggregate without broadening protected authority.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24931",
    "jira_updated_at": "2026-08-11T07:21:35.750-0500",
    "last_synced_at": "2026-08-11T12:22:01.000481+00:00",
    "source_export": "jira/reconciliation/BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "In Progress"
  },
  "out_of_scope": [
    "Promoting unmatched later supplemental rows by borrowing the repository commit time.",
    "Inventing missing values, identifiers, publication times, target outcomes, or source completeness.",
    "Protected training/evaluation, champion or production promotion, forecast publication, final historical readiness, A&M lift, BAS, Aggie Excess, or any scientific result."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-010",
  "phase": "PHASE-1",
  "prerequisites": [
    "POST-SUBTASK-174 supplemental candidate reconciliation.",
    "POST-SUBTASK-176 development-only PIT aggregate and target replay.",
    "Pinned BAT-387 canonical game and source-team assignment ledger.",
    "Configured standardized external data root."
  ],
  "primary_source_refs": [
    "SRCREF-02013",
    "SRCREF-02014",
    "SRCREF-02016"
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
    "Exact commit, raw payload, capture, schema, registry, supplemental, builder, contract, dataset, manifest, payload, validation, and rollback identities.",
    "Per-season source rows, games, drives, exact identifier/content/result matches, source-only/supplemental-only differences, dispositions, quarantines, and known-at/effective times.",
    "Combined source seasons, plays, drives, games, mappings, profiles, target rows, features, cold starts, bytes, hashes, target overlap, mutation controls, and byte-identical rebuild.",
    "Explicit development-only/preliminary authority and protected/production/scientific nonclaims."
  ],
  "required_tests": [
    {
      "classification": "NEW_AUTOMATED_TEST_REQUIRED",
      "expectation": "Multiple exact source dispositions combine while quarantine is excluded and protected authority remains closed.",
      "path": "tests/test_historical_play_drive_pit_extension.py",
      "validation_class": "PIT_LEAKAGE"
    },
    {
      "classification": "END_TO_END",
      "expectation": "The complete external population passes 46 checks, six mutation controls, and a three-file byte-identical isolated rebuild.",
      "path": "artifacts/jira_evidence/POST-SUBTASK-183.json",
      "validation_class": "END_TO_END"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "Any raw source, commit, canonical identity, chronology, target overlap, schema, authority, population, hash, or deterministic rebuild identity drifts.",
    "Any target game, outcome field, post-cutoff row, ambiguous identity, or fabricated cross-route match enters the admitted payload.",
    "Any development-only artifact is represented as protected, champion, production, forecast, complete-history, or scientific authority."
  ],
  "risk_ids": [
    "RISK-227",
    "RISK-241"
  ],
  "schema_version": 2,
  "scope": "Close the 2011 and 2020 season-level play/drive PIT gaps using exact immutable repository evidence while preserving row-level partial coverage and protected nonauthority.",
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
    "SRCREF-02006"
  ],
  "stop_conditions": [
    "Stop the affected row, domain, or artifact on source, identity, chronology, target overlap, schema, authority, population, hash, or deterministic rebuild failure.",
    "Quarantine only affected rows or domains; do not block independent acquisition or preliminary modeling.",
    "Do not open protected promotion until expanded quality-supported history and all applicable W17 gates pass."
  ],
  "supporting_source_refs": [
    "SRCREF-02018",
    "SRCREF-02006"
  ],
  "title": "[POST-SUBTASK-183] Recover 2011/2020 version-bound play/drive PIT gaps",
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
  "why_this_exists": "The exact repository versions for 2011 and 2020 were publicly committed before every 2023-2025 target cutoff, allowing those partial source populations to close season-level development PIT gaps without inventing current-capture timestamps or protected authority.",
  "work_packet_path": "",
  "workflow_state": "IN_PROGRESS"
}
```

## Objective

Recover the exact 2011 and 2020 version-bound play/drive populations, reconcile their source differences, and supersede the partial development-only PIT aggregate without broadening protected authority.

## Why This Exists

The exact repository versions for 2011 and 2020 were publicly committed before every 2023-2025 target cutoff, allowing those partial source populations to close season-level development PIT gaps without inventing current-capture timestamps or protected authority.

## Scope

Close the 2011 and 2020 season-level play/drive PIT gaps using exact immutable repository evidence while preserving row-level partial coverage and protected nonauthority.

### Explicit In Scope

- Exact immutable 2011 and 2020 version-bound repository plays and drives with public pre-target commit time.
- Canonical game and team identity validation, cross-route reconciliation, explicit quarantine, content-addressed provenance, deterministic replay, and development-only PIT admission.
- Dense 2010-2022 play/drive feature candidacy for a separately lineaged preliminary unprotected replay.

### Explicit Out of Scope

- Promoting unmatched later supplemental rows by borrowing the repository commit time.
- Inventing missing values, identifiers, publication times, target outcomes, or source completeness.
- Protected training/evaluation, champion or production promotion, forecast publication, final historical readiness, A&M lift, BAS, Aggie Excess, or any scientific result.

## Prerequisites

- POST-SUBTASK-174 supplemental candidate reconciliation.
- POST-SUBTASK-176 development-only PIT aggregate and target replay.
- Pinned BAT-387 canonical game and source-team assignment ledger.
- Configured standardized external data root.

## Hard Dependencies

- POST-SUBTASK-174
- POST-SUBTASK-176

## Blocks

- None.

## Read / Inspect First

- None.

## Files Expected To Be Modified

- configs/versioned_play_drive_gap_contract.json
- configs/historical_play_drive_pit_extension_contract.json
- configs/historical_known_at_recovery_contract.json
- src/aggie_analytics/temporal/play_drive_pit.py
- tools/build_versioned_play_drive_gap.py
- tools/build_historical_play_drive_pit_extension.py
- tools/validate_historical_play_drive_pit_extension.py
- tests/test_historical_play_drive_pit_extension.py
- tests/test_historical_known_at_recovery_contract.py
- artifacts/pit/historical_play_drive_pit_aggregate_gate.json
- artifacts/pit/historical_known_at_replay_gate.json
- artifacts/jira_evidence/POST-SUBTASK-183.json

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

- configs/versioned_play_drive_gap_contract.json
- configs/historical_play_drive_pit_extension_contract.json
- artifacts/pit/historical_play_drive_pit_aggregate_gate.json
- artifacts/jira_evidence/POST-SUBTASK-183.json
- <external-data-root>/raw/historical_known_at/github/sha256/<payload_sha256>/payload.parquet
- <external-data-root>/quarantine/historical_known_at/sha256/33f3f3ab/
- <external-data-root>/pit_state/historical_known_at/sha256/1bd6f4c6/team_play_drive_profiles.parquet
- <external-data-root>/features/historical_known_at/sha256/1bd6f4c6/target_game_team_play_drive_features.parquet
- <external-data-root>/validation/POST-SUBTASK-183/play_drive_pit_extension_validation.json

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

1. The exact 2011 and 2020 repository payloads are captured outside Git at immutable content-addressed paths and bound to commit b9b838e44f16131b897489e6ae3da355f8c99865 and its 2022-07-25T17:33:07Z public committer time.
2. Only rows with exact canonical game identity, verified source-team identity, nonempty source effective time, and pre-cutoff source known-at time enter development PIT; affected ambiguous rows are quarantined without discarding otherwise useful seasons or domains.
3. Cross-route row-count, identifier, content, drive-result, and missing-game differences against the later CFBD supplemental population are measured and preserved; no false one-to-one or completeness claim is created.
4. The superseding aggregate covers source seasons 2010-2022 at the same target-game/team grain, has zero target-game overlap, excludes target/outcome columns, preserves cold starts and nulls, and passes a byte-identical isolated rebuild.
5. Authority remains development-only PIT and preliminary unprotected feature research; protected training/evaluation, champion or production promotion, forecast publication, historical completeness, and scientific claims remain closed.

## Definition of Done

1. The two source Parquet payloads, exact commit API response, capture manifests, normalized candidate layers, and reconciliation manifest are content-addressed outside Git with verified hashes.
2. All 234,857 repository plays and 34,810 repository drives are dispositioned; two ambiguous 2020 drives are quarantined and all other eligible rows retain exact canonical game and verified team identity.
3. The superseding development-only aggregate identity 1bd6f4c6 contains 1,840,951 plays, 264,812 drives, 243 profiles, and 5,528 target-game/team rows over dense 2010-2022 source seasons.
4. All 46 validation checks, six mutation controls, three-file byte-identical rebuild, relevant tests, repository validators, and integration checks pass.
5. The next separately lineaged preliminary replay is enabled without claiming protected readiness or final historical completeness.

## Required Tests / Validation

- **NEW_AUTOMATED_TEST_REQUIRED** / `PIT_LEAKAGE` — `tests/test_historical_play_drive_pit_extension.py` — Multiple exact source dispositions combine while quarantine is excluded and protected authority remains closed.
- **END_TO_END** / `END_TO_END` — `artifacts/jira_evidence/POST-SUBTASK-183.json` — The complete external population passes 46 checks, six mutation controls, and a three-file byte-identical isolated rebuild.

## Required Evidence

- Exact commit, raw payload, capture, schema, registry, supplemental, builder, contract, dataset, manifest, payload, validation, and rollback identities.
- Per-season source rows, games, drives, exact identifier/content/result matches, source-only/supplemental-only differences, dispositions, quarantines, and known-at/effective times.
- Combined source seasons, plays, drives, games, mappings, profiles, target rows, features, cold starts, bytes, hashes, target overlap, mutation controls, and byte-identical rebuild.
- Explicit development-only/preliminary authority and protected/production/scientific nonclaims.

## Completion Evidence Contract

```json
{}
```

## End-to-End Validation Requirement

Verify exact raw bytes and commit metadata; rebuild normalized 2011/2020 plays and drives; reconcile against the supplemental population; rebuild the combined 2010-2022 PIT layer; verify identity, chronology, target exclusion, schemas, hashes, counts, quarantines, authority, and byte identity; then remove reconstructible rebuild output.

## Expected Maturity After Completion

`DEVELOPMENT_ONLY_PIT_ADMITTED`

## Risk / Failure Conditions

- Any raw source, commit, canonical identity, chronology, target overlap, schema, authority, population, hash, or deterministic rebuild identity drifts.
- Any target game, outcome field, post-cutoff row, ambiguous identity, or fabricated cross-route match enters the admitted payload.
- Any development-only artifact is represented as protected, champion, production, forecast, complete-history, or scientific authority.

## Stop Conditions

- Stop the affected row, domain, or artifact on source, identity, chronology, target overlap, schema, authority, population, hash, or deterministic rebuild failure.
- Quarantine only affected rows or domains; do not block independent acquisition or preliminary modeling.
- Do not open protected promotion until expanded quality-supported history and all applicable W17 gates pass.

## Source References

- SRCREF-02013
- SRCREF-02014
- SRCREF-02016
- SRCREF-02018
- SRCREF-02006

## AI Context Notes

- The immutable repository payload is primary historical evidence; the 2026 CFBD supplemental captures provide reconciliation evidence but do not supply or replace historical known-at timestamps.
- This unit supersedes the POST-SUBTASK-176 aggregate while preserving it as the first validated partial-season checkpoint.
- No OpenAI output or model-generated fact participates in acquisition, identity, timing, normalization, aggregation, validation, or admission.

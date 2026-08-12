<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-195_materialize_1963_2009_national_game_outcome_spine_and_tiered_eligibility_gate.json -->
# POST-SUBTASK-195 — [POST-SUBTASK-195] Materialize 1963-2009 national game/outcome spine and tiered eligibility gate

## Canonical metadata

```json
{
  "acceptance_control_ids": [
    "AC-011",
    "AC-017",
    "AC-061",
    "AC-073",
    "AC-075",
    "AC-079",
    "AC-080"
  ],
  "acceptance_criteria": [
    "All 47 immutable 1963-2009 CFBD game captures, their capture manifests, source payload hashes, source row counts, and canonical game mappings verify before any row is admitted.",
    "Exactly 33,278 canonical schedule identities are dispositioned without double counting: 33,272 CFBD games plus six SportsDataverse-only canonical schedules; only the 33,276 completed score-bearing games are outcome-reference eligible and the two canceled schedules remain nonoutcomes.",
    "The 2004-2009 supplement reconciliation preserves 4,650 source rows, 4,630 canonical identities, 4,624 canonical overlaps, 18 postponed aliases, two duplicate-final aliases, six supplement-only identities, and every conflict or limitation at source-row and canonical-game grain.",
    "Only canonical identity, season, season type, week, kickoff, participants, schedule state, completed flag, and official final score/outcome fields may enter the admitted spine; postgame Elo, win probability, excitement, highlights, line scores, attendance, and other derived or out-of-scope fields are excluded.",
    "No exact historical publication time, final-whistle time, same-day availability, pregame PIT authority, protected eligibility, production readiness, champion, A&M lift, BAS, Aggie Excess, or scientific result is inferred or claimed.",
    "Outputs pass deterministic reconstruction, immutable identity, schema, canonical mapping, source reconciliation, missingness, quarantine, mutation, byte-rebuild, Jira, repository, provenance, secret, and full-suite validation before Done."
  ],
  "adr_ids": [
    "ADR-005",
    "ADR-006",
    "ADR-042",
    "ADR-089",
    "ADR-094",
    "ADR-111"
  ],
  "ai_context_notes": [
    "Deterministic provider and canonical identifiers fully define this work; OpenAI is not required and may not invent outcomes, timestamps, identities, scores, completion state, or source conflicts.",
    "SportsDataverse schedule data is ESPN-derived and is reproducibility/supplement evidence, not an independent confirmation of CFBD upstream truth.",
    "Historical capture time is known, but source publication and final-whistle times are unknown; the artifact therefore remains an outcome-reference candidate rather than general pregame PIT truth."
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-195_materialize_1963_2009_national_game_outcome_spine_and_tiered_eligibility_gate.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "component": "data-sources",
  "components_expected_to_be_touched": [
    "data",
    "entities",
    "pit-temporal",
    "provenance",
    "validation-promotion"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "Completed outcomes, canceled schedule-only rows, and source aliases are separately immutable, content-addressed, reproducible, and stored outside Git.",
    "Independent reconstruction verifies source and canonical hashes, per-season population, natural keys, status/outcome disposition, alias reconciliation, field allowlist, forbidden-field exclusion, mutations, and byte identity.",
    "Canonical/live Jira, Git/PR evidence, governing goal, active plan, cleanup, OpenAI non-use rationale, and protected/scientific nonclaims agree before Done."
  ],
  "dependencies": [
    "POST-SUBTASK-028",
    "POST-SUBTASK-029",
    "POST-SUBTASK-037",
    "POST-SUBTASK-042"
  ],
  "end_to_end_validation": "Re-read and hash the BAT-378 CFBD acquisition manifest, 47 game payloads and capture manifests, the SportsDataverse supplement manifest and six schedule payloads, and the BAT-387 canonical registry; rebuild in an isolated external root; verify exact source, canonical-union, completed-outcome, canceled-schedule, alias, per-season, natural-key, field-allowlist, authority, mutation, and byte identities; then remove only reconstructible rebuild output after success.",
  "epic_id": "POST-EPIC-004",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-195.json",
  "evidence_state": "VERIFIED",
  "execution_lane": "DATA",
  "execution_mode": "HISTORICAL_REFERENCE",
  "expected_maturity_after_completion": "VALIDATED_RECONCILED_CANDIDATE_ONLY",
  "expected_outputs": [
    "configs/historical_game_outcome_spine_contract.json",
    "artifacts/data/historical_game_outcome_spine_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-195.json",
    "<external-data-root>/canonical/historical_game_outcome_spine/sha256/<dataset_identity>/completed_game_outcomes.parquet",
    "<external-data-root>/quarantine/historical_game_outcome_spine/sha256/<dataset_identity>/schedule_only_nonoutcomes.parquet",
    "<external-data-root>/quarantine/historical_game_outcome_spine/sha256/<dataset_identity>/source_alias_reconciliation.parquet",
    "<external-data-root>/manifests/historical_game_outcome_spine/sha256/<dataset_identity>/historical_game_outcome_spine_manifest.json",
    "<external-data-root>/validation/POST-SUBTASK-195/<dataset_identity>/historical_game_outcome_spine_validation.json"
  ],
  "files_expected_to_be_read": [
    "<external-data-root>/manifests/acquisition/bat378-cfbd-historical-expansion-v1/historical_expansion_acquisition_manifest.full.json",
    "<external-data-root>/manifests/acquisition/bat378-sportsdataverse-supplement-v1/sportsdataverse_supplement_manifest.full.json",
    "<external-data-root>/canonical/BAT-387/sha256/10d0bd0adcef3fc1ba22fb9932f353cc59b0e5d4508c7891a1472d0221a454ac/canonical_core_registry.csv"
  ],
  "files_expected_to_be_touched": [
    "configs/historical_game_outcome_spine_contract.json",
    "src/aggie_analytics/data/historical_game_outcome_spine.py",
    "tools/build_historical_game_outcome_spine.py",
    "tools/validate_historical_game_outcome_spine.py",
    "tests/test_historical_game_outcome_spine.py",
    "artifacts/data/historical_game_outcome_spine_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-195.json"
  ],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-195_materialize_1963_2009_national_game_outcome_spine_and_tiered_eligibility_gate.md",
  "governance_traceability_gate": "POST-SUBTASK-069",
  "historical_classification": "POST_W25_IMPLEMENTATION",
  "import_id": 100503,
  "in_scope": [
    "Immutable 1963-2009 national FBS game/schedule/outcome source captures, canonical identities, completed outcomes, canceled schedule-only records, cross-source aliases, per-season coverage, and explicit domain eligibility.",
    "Outcome-reference use for long-run program context, outcome labels, rating research, and future separately governed chronology work without silently granting same-day or pregame PIT eligibility."
  ],
  "issue_type": "Sub-task",
  "jira_key": "BAT-552",
  "labels": [
    "actionable",
    "post-wave",
    "subtask",
    "historical-expansion",
    "games",
    "outcomes",
    "1963-2009",
    "tiered-eligibility",
    "candidate-only",
    "provenance",
    "local-id-post-subtask-195"
  ],
  "last_content_audit": "2026-08-11",
  "local_id": "POST-SUBTASK-195",
  "maturity_before": "VALIDATED_RECONCILED_CANDIDATE_ONLY",
  "objective": "Materialize and independently validate an immutable 1963-2009 national canonical game/outcome spine with completed outcomes, schedule-only nonoutcomes, source aliases, and tiered chronological eligibility kept explicitly separate.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24945",
    "jira_updated_at": "2026-08-11T17:31:18.585-0500",
    "last_synced_at": "2026-08-11T22:31:41.657762+00:00",
    "source_export": "jira/reconciliation/BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "Done"
  },
  "out_of_scope": [
    "Player, roster, play-by-play, drive, box-score, advanced-stat, weather, injury, depth-chart, availability, or exact publication-time completion for these seasons.",
    "Treating canceled or postponed placeholders as outcomes; treating aliases as distinct games; inferring missing scores, times, participants, or identities; or importing provider-derived postgame features.",
    "Protected training/evaluation, champion or production promotion, forecast publication, final historical completeness, A&M lift, BAS, Aggie Excess, or scientific claims."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-010",
  "phase": "PHASE-1",
  "prerequisites": [
    "BAT-378 immutable CFBD acquisition manifest SHA-256 bb5ace34c41cfc886f928119b53d495b9870ec1d7c7caff559d3a9e9d178fba7 and raw game aggregate SHA-256 663cf655124cb87184c0f03f17c350ea27cb3064a4c4831e63bc89124924cb69.",
    "BAT-387 canonical registry identity 10d0bd0adcef3fc1ba22fb9932f353cc59b0e5d4508c7891a1472d0221a454ac with exact provider-ID game mappings.",
    "Read-only population profile: 33,272 unique completed CFBD games, 33,278 canonical schedule union, 33,276 completed outcome candidates, and explicit SportsDataverse alias/supplement dispositions.",
    "Verified recovery checkpoint C:/BatteredAggieSyndrome.data/backups/POST-SUBTASK-195-PRECHANGE-20260811T215652Z.",
    "Integrated dataset identity 8e639d010b4808fe279e97e5ff79adf31a2b04cd8ee1ece1dcf2f09ec7343296 and immutable validation report SHA-256 d946e0e2972c5f5ffff0cf923faa708e33dcf1e8867b8a8e38015252d16868a4.",
    "Implementation PR 207 merged as dca218f81d316c4ccffb786fc184670eaf166d80 after all hosted repository and security checks passed."
  ],
  "primary_source_refs": [
    "SRCREF-02013",
    "SRCREF-02019",
    "SRCREF-02020"
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
  "record_revision": "1.1",
  "related_to": [
    "POST-SUBTASK-169",
    "POST-SUBTASK-172"
  ],
  "required_evidence": [
    "Exact acquisition, capture, raw, canonical-registry, contract, code, dataset, manifest, validation, Git, PR, hosted-check, and live Jira identities.",
    "Per-season source and canonical counts; completed, canceled, postponed, duplicate-final, supplement-only, tie, missingness, natural-key, source-field, and alias dispositions.",
    "Explicit outcome-reference-only, no exact historical publication/final-whistle inference, no same-day/pre-game PIT authority, and protected/production/completeness/scientific nonclaims."
  ],
  "required_tests": [
    {
      "classification": "NEW_AUTOMATED_TEST_REQUIRED",
      "expectation": "Game/outcome materialization, canonical union, status disposition, source alias reconciliation, field allowlist, and authority boundaries remain deterministic.",
      "path": "tests/test_historical_game_outcome_spine.py",
      "validation_class": "PIT_LEAKAGE"
    },
    {
      "classification": "END_TO_END",
      "expectation": "The complete external population passes source identity, canonical mapping, reconstruction, schema, provenance, quarantine, mutation, and byte-identity checks.",
      "path": "artifacts/jira_evidence/POST-SUBTASK-195.json",
      "validation_class": "END_TO_END"
    }
  ],
  "requirement_ids": [
    "REQ-020",
    "REQ-038",
    "REQ-039",
    "REQ-041",
    "REQ-052",
    "REQ-053",
    "REQ-063",
    "REQ-199",
    "REQ-319",
    "REQ-323"
  ],
  "risk_failure_conditions": [
    "Any source hash, canonical mapping, game identity, season, participant, completed state, final score, alias, natural key, population, schema, or rebuild identity drifts.",
    "Any canceled/postponed placeholder is admitted as an outcome, any alias is double counted, or any forbidden postgame/provider-derived field enters the admitted spine.",
    "Any fabricated publication/final-whistle time, same-day availability, protected decision, production claim, or scientific result enters the artifact."
  ],
  "risk_ids": [
    "RISK-038",
    "RISK-050",
    "RISK-081",
    "RISK-099",
    "RISK-106",
    "RISK-227",
    "RISK-241"
  ],
  "schema_version": 2,
  "scope": "Build the canonical 1963-2009 game/outcome spine from immutable CFBD captures plus the exact SportsDataverse schedule supplement; materialize 33,276 completed outcomes, preserve two canceled schedules and 20 source-alias groups separately, and publish a tiered eligibility gate without broadening PIT or protected authority.",
  "source_ids": [
    "GAP-002",
    "GAP-003",
    "HANDOFF-008"
  ],
  "source_refs": [
    "SRCREF-02013",
    "SRCREF-02014",
    "SRCREF-02015",
    "SRCREF-02016",
    "SRCREF-02019",
    "SRCREF-02020",
    "SRCREF-02021",
    "SRCREF-02022",
    "SRCREF-02023",
    "SRCREF-02024",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01564",
    "SRCREF-01565",
    "SRCREF-01566",
    "SRCREF-01568"
  ],
  "stop_conditions": [
    "Stop the affected source row, alias, canonical game, season, domain, or artifact on source, identity, status, score, schema, missingness, chronology, authority, hash, population, or rebuild failure.",
    "Do not weaken outcome-reference-only, no-duplicate, no-placeholder-outcome, field-allowlist, no-publication-time-inference, no-PIT-promotion, or scientific boundaries merely to obtain approval."
  ],
  "supporting_source_refs": [
    "SRCREF-02014",
    "SRCREF-02015",
    "SRCREF-02016",
    "SRCREF-02021",
    "SRCREF-02022",
    "SRCREF-02023",
    "SRCREF-02024",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01564",
    "SRCREF-01565",
    "SRCREF-01566",
    "SRCREF-01568"
  ],
  "title": "[POST-SUBTASK-195] Materialize 1963-2009 national game/outcome spine and tiered eligibility gate",
  "traceability_inherited_from": [
    "POST-SUBTASK-069"
  ],
  "traceability_resolution": "DIRECT_PLUS_INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "why_this_exists": "BAT-378 acquired a complete 1963-2009 CFBD game/outcome tranche and BAT-387 reconciled provider game identities, but no dedicated immutable artifact currently exposes the long national outcome history with completed, canceled, postponed, duplicate, supplement-only, field, chronology, and authority boundaries enforced for downstream consumers.",
  "work_packet_path": "",
  "workflow_state": "DONE"
}
```

## Objective

Materialize and independently validate an immutable 1963-2009 national canonical game/outcome spine with completed outcomes, schedule-only nonoutcomes, source aliases, and tiered chronological eligibility kept explicitly separate.

## Why This Exists

BAT-378 acquired a complete 1963-2009 CFBD game/outcome tranche and BAT-387 reconciled provider game identities, but no dedicated immutable artifact currently exposes the long national outcome history with completed, canceled, postponed, duplicate, supplement-only, field, chronology, and authority boundaries enforced for downstream consumers.

## Scope

Build the canonical 1963-2009 game/outcome spine from immutable CFBD captures plus the exact SportsDataverse schedule supplement; materialize 33,276 completed outcomes, preserve two canceled schedules and 20 source-alias groups separately, and publish a tiered eligibility gate without broadening PIT or protected authority.

### Explicit In Scope

- Immutable 1963-2009 national FBS game/schedule/outcome source captures, canonical identities, completed outcomes, canceled schedule-only records, cross-source aliases, per-season coverage, and explicit domain eligibility.
- Outcome-reference use for long-run program context, outcome labels, rating research, and future separately governed chronology work without silently granting same-day or pregame PIT eligibility.

### Explicit Out of Scope

- Player, roster, play-by-play, drive, box-score, advanced-stat, weather, injury, depth-chart, availability, or exact publication-time completion for these seasons.
- Treating canceled or postponed placeholders as outcomes; treating aliases as distinct games; inferring missing scores, times, participants, or identities; or importing provider-derived postgame features.
- Protected training/evaluation, champion or production promotion, forecast publication, final historical completeness, A&M lift, BAS, Aggie Excess, or scientific claims.

## Prerequisites

- BAT-378 immutable CFBD acquisition manifest SHA-256 bb5ace34c41cfc886f928119b53d495b9870ec1d7c7caff559d3a9e9d178fba7 and raw game aggregate SHA-256 663cf655124cb87184c0f03f17c350ea27cb3064a4c4831e63bc89124924cb69.
- BAT-387 canonical registry identity 10d0bd0adcef3fc1ba22fb9932f353cc59b0e5d4508c7891a1472d0221a454ac with exact provider-ID game mappings.
- Read-only population profile: 33,272 unique completed CFBD games, 33,278 canonical schedule union, 33,276 completed outcome candidates, and explicit SportsDataverse alias/supplement dispositions.
- Verified recovery checkpoint C:/BatteredAggieSyndrome.data/backups/POST-SUBTASK-195-PRECHANGE-20260811T215652Z.
- Integrated dataset identity 8e639d010b4808fe279e97e5ff79adf31a2b04cd8ee1ece1dcf2f09ec7343296 and immutable validation report SHA-256 d946e0e2972c5f5ffff0cf923faa708e33dcf1e8867b8a8e38015252d16868a4.
- Implementation PR 207 merged as dca218f81d316c4ccffb786fc184670eaf166d80 after all hosted repository and security checks passed.

## Hard Dependencies

- POST-SUBTASK-028
- POST-SUBTASK-029
- POST-SUBTASK-037
- POST-SUBTASK-042

## Blocks

- None.

## Read / Inspect First

- None.

## Files Expected To Be Modified

- configs/historical_game_outcome_spine_contract.json
- src/aggie_analytics/data/historical_game_outcome_spine.py
- tools/build_historical_game_outcome_spine.py
- tools/validate_historical_game_outcome_spine.py
- tests/test_historical_game_outcome_spine.py
- artifacts/data/historical_game_outcome_spine_gate.json
- artifacts/jira_evidence/POST-SUBTASK-195.json

## Components Expected To Be Touched

- data
- entities
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

- configs/historical_game_outcome_spine_contract.json
- artifacts/data/historical_game_outcome_spine_gate.json
- artifacts/jira_evidence/POST-SUBTASK-195.json
- <external-data-root>/canonical/historical_game_outcome_spine/sha256/<dataset_identity>/completed_game_outcomes.parquet
- <external-data-root>/quarantine/historical_game_outcome_spine/sha256/<dataset_identity>/schedule_only_nonoutcomes.parquet
- <external-data-root>/quarantine/historical_game_outcome_spine/sha256/<dataset_identity>/source_alias_reconciliation.parquet
- <external-data-root>/manifests/historical_game_outcome_spine/sha256/<dataset_identity>/historical_game_outcome_spine_manifest.json
- <external-data-root>/validation/POST-SUBTASK-195/<dataset_identity>/historical_game_outcome_spine_validation.json

## Direct Requirements

- REQ-020
- REQ-038
- REQ-039
- REQ-041
- REQ-052
- REQ-053
- REQ-063
- REQ-199
- REQ-319
- REQ-323

## Direct Acceptance Controls

- AC-011
- AC-017
- AC-061
- AC-073
- AC-075
- AC-079
- AC-080

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-069`
- Inherited from: POST-SUBTASK-069
- Resolution: `DIRECT_PLUS_INHERITED_DOMAIN_GATE`
- Effective counts: `{}`

## Acceptance Criteria

1. All 47 immutable 1963-2009 CFBD game captures, their capture manifests, source payload hashes, source row counts, and canonical game mappings verify before any row is admitted.
2. Exactly 33,278 canonical schedule identities are dispositioned without double counting: 33,272 CFBD games plus six SportsDataverse-only canonical schedules; only the 33,276 completed score-bearing games are outcome-reference eligible and the two canceled schedules remain nonoutcomes.
3. The 2004-2009 supplement reconciliation preserves 4,650 source rows, 4,630 canonical identities, 4,624 canonical overlaps, 18 postponed aliases, two duplicate-final aliases, six supplement-only identities, and every conflict or limitation at source-row and canonical-game grain.
4. Only canonical identity, season, season type, week, kickoff, participants, schedule state, completed flag, and official final score/outcome fields may enter the admitted spine; postgame Elo, win probability, excitement, highlights, line scores, attendance, and other derived or out-of-scope fields are excluded.
5. No exact historical publication time, final-whistle time, same-day availability, pregame PIT authority, protected eligibility, production readiness, champion, A&M lift, BAS, Aggie Excess, or scientific result is inferred or claimed.
6. Outputs pass deterministic reconstruction, immutable identity, schema, canonical mapping, source reconciliation, missingness, quarantine, mutation, byte-rebuild, Jira, repository, provenance, secret, and full-suite validation before Done.

## Definition of Done

1. Completed outcomes, canceled schedule-only rows, and source aliases are separately immutable, content-addressed, reproducible, and stored outside Git.
2. Independent reconstruction verifies source and canonical hashes, per-season population, natural keys, status/outcome disposition, alias reconciliation, field allowlist, forbidden-field exclusion, mutations, and byte identity.
3. Canonical/live Jira, Git/PR evidence, governing goal, active plan, cleanup, OpenAI non-use rationale, and protected/scientific nonclaims agree before Done.

## Required Tests / Validation

- **NEW_AUTOMATED_TEST_REQUIRED** / `PIT_LEAKAGE` — `tests/test_historical_game_outcome_spine.py` — Game/outcome materialization, canonical union, status disposition, source alias reconciliation, field allowlist, and authority boundaries remain deterministic.
- **END_TO_END** / `END_TO_END` — `artifacts/jira_evidence/POST-SUBTASK-195.json` — The complete external population passes source identity, canonical mapping, reconstruction, schema, provenance, quarantine, mutation, and byte-identity checks.

## Required Evidence

- Exact acquisition, capture, raw, canonical-registry, contract, code, dataset, manifest, validation, Git, PR, hosted-check, and live Jira identities.
- Per-season source and canonical counts; completed, canceled, postponed, duplicate-final, supplement-only, tie, missingness, natural-key, source-field, and alias dispositions.
- Explicit outcome-reference-only, no exact historical publication/final-whistle inference, no same-day/pre-game PIT authority, and protected/production/completeness/scientific nonclaims.

## Completion Evidence Contract

```json
{}
```

## End-to-End Validation Requirement

Re-read and hash the BAT-378 CFBD acquisition manifest, 47 game payloads and capture manifests, the SportsDataverse supplement manifest and six schedule payloads, and the BAT-387 canonical registry; rebuild in an isolated external root; verify exact source, canonical-union, completed-outcome, canceled-schedule, alias, per-season, natural-key, field-allowlist, authority, mutation, and byte identities; then remove only reconstructible rebuild output after success.

## Expected Maturity After Completion

`VALIDATED_RECONCILED_CANDIDATE_ONLY`

## Risk / Failure Conditions

- Any source hash, canonical mapping, game identity, season, participant, completed state, final score, alias, natural key, population, schema, or rebuild identity drifts.
- Any canceled/postponed placeholder is admitted as an outcome, any alias is double counted, or any forbidden postgame/provider-derived field enters the admitted spine.
- Any fabricated publication/final-whistle time, same-day availability, protected decision, production claim, or scientific result enters the artifact.

## Stop Conditions

- Stop the affected source row, alias, canonical game, season, domain, or artifact on source, identity, status, score, schema, missingness, chronology, authority, hash, population, or rebuild failure.
- Do not weaken outcome-reference-only, no-duplicate, no-placeholder-outcome, field-allowlist, no-publication-time-inference, no-PIT-promotion, or scientific boundaries merely to obtain approval.

## Source References

- SRCREF-02013
- SRCREF-02014
- SRCREF-02015
- SRCREF-02016
- SRCREF-02019
- SRCREF-02020
- SRCREF-02021
- SRCREF-02022
- SRCREF-02023
- SRCREF-02024
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01564
- SRCREF-01565
- SRCREF-01566
- SRCREF-01568

## AI Context Notes

- Deterministic provider and canonical identifiers fully define this work; OpenAI is not required and may not invent outcomes, timestamps, identities, scores, completion state, or source conflicts.
- SportsDataverse schedule data is ESPN-derived and is reproducibility/supplement evidence, not an independent confirmation of CFBD upstream truth.
- Historical capture time is known, but source publication and final-whistle times are unknown; the artifact therefore remains an outcome-reference candidate rather than general pregame PIT truth.

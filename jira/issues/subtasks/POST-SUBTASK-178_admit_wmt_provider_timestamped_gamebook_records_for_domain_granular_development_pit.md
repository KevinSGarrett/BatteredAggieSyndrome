<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-178_admit_wmt_provider_timestamped_gamebook_records_for_domain_granular_development_pit.json -->
# POST-SUBTASK-178 — Admit WMT provider-timestamped gamebook records for domain-granular development PIT

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Only records from the pinned Texas A&M official WMT gamebook acquisition identity d227b6cf are eligible, and every admitted record retains its source capture, payload, game, domain, record, and provider timestamp identity.",
    "Known-at time is the maximum parseable provider created/updated/version timestamp on the exact record; game time, current capture time, PDF metadata, model output, and inferred publication time are never substituted.",
    "Eligibility is computed independently by game, action, play, drive, and player domain at each target cutoff; a missing or post-cutoff timestamp excludes only the affected record or domain.",
    "Target-game records and future records are excluded from every target feature; identity joins remain canonical and no name-only merge, factual imputation, or timestamp fabrication is permitted.",
    "Authority is limited to development-only PIT and preliminary unprotected research; protected evaluation, champion promotion, production forecasts, A&M lift, BAS, Aggie Excess, final historical readiness, and scientific claims remain closed."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "The provider timestamps are deterministic source metadata already present in immutable raw WMT payloads; OpenAI has no role in timestamp selection, identity, admission, or canonical truth.",
    "A later provider update makes the current record version eligible only after that update; this unit never backcasts current payload content to game date.",
    "Partial source seasons and domains remain explicit and do not globally block historical expansion or preliminary modeling."
  ],
  "blocked_reason": "",
  "blocks": [
    "POST-SUBTASK-179"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-178_admit_wmt_provider_timestamped_gamebook_records_for_domain_granular_development_pit.json",
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
    "All 177 pinned WMT payloads are replayed and every game, action, play, drive, and player record is classified independently by provider timestamp coverage, source season, target cutoff eligibility, and exclusion reason.",
    "Immutable content-addressed candidate/PIT payloads and manifests are stored outside Git with exact population, schema, missingness, timestamp distribution, and provenance identities.",
    "Target-cutoff joins prove strict source-known-at-before-cutoff ordering, zero target-game overlap, no target or outcome fields, domain-specific partial coverage, and deterministic byte-identical replay.",
    "Repository, provenance, Jira second-pass, PIT/leakage, secret, and full automated test gates pass, and reconstructible temporary output is cleaned.",
    "The historical recovery contract, replay gate, Jira evidence, governing goal, and active plan preserve development-only authority and all protected nonclaims."
  ],
  "dependencies": [
    "POST-SUBTASK-029",
    "POST-SUBTASK-175"
  ],
  "end_to_end_validation": "Re-read the pinned d227b6cf acquisition manifest and every referenced immutable WMT payload; independently derive the maximum record-level provider timestamp, rebuild domain rows and target-cutoff eligibility, verify hashes, schemas, counts, chronology, target exclusion, authority, and byte identity, then remove the reconstructible rebuild.",
  "epic_id": "POST-EPIC-003",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-178.json",
  "evidence_state": "VERIFIED",
  "execution_lane": "DATA",
  "execution_mode": "HISTORICAL_REFERENCE",
  "expected_maturity_after_completion": "DEVELOPMENT_ONLY_PIT_ADMITTED",
  "expected_outputs": [
    "configs/wmt_provider_timestamp_pit_contract.json",
    "src/aggie_analytics/temporal/wmt_provider_timestamp_pit.py",
    "tools/build_wmt_provider_timestamp_pit.py",
    "tools/validate_wmt_provider_timestamp_pit.py",
    "artifacts/pit/wmt_provider_timestamp_pit_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-178.json",
    "<external-data-root>/pit_state/historical_known_at/sha256/<dataset_identity>/wmt_provider_timestamp_records.parquet",
    "<external-data-root>/features/historical_known_at/sha256/<dataset_identity>/target_cutoff_wmt_domain_features.parquet",
    "<external-data-root>/manifests/historical_known_at/sha256/<dataset_identity>/wmt_provider_timestamp_pit_manifest.json",
    "<external-data-root>/validation/POST-SUBTASK-178/wmt_provider_timestamp_pit_validation.json"
  ],
  "files_expected_to_be_read": [
    "configs/historical_known_at_recovery_contract.json",
    "artifacts/pit/historical_tamu_official_gamebook_reconciliation_gate.json",
    "artifacts/pit/historical_known_at_replay_gate.json",
    "configs/expanded_event_chronology_preliminary_contract.json"
  ],
  "files_expected_to_be_touched": [
    "configs/wmt_provider_timestamp_pit_contract.json",
    "configs/historical_known_at_recovery_contract.json",
    "src/aggie_analytics/temporal/wmt_provider_timestamp_pit.py",
    "tools/build_wmt_provider_timestamp_pit.py",
    "tools/validate_wmt_provider_timestamp_pit.py",
    "tests/test_wmt_provider_timestamp_pit.py",
    "tests/test_historical_known_at_recovery_contract.py",
    "tests/test_jira_control_plane.py",
    "artifacts/pit/wmt_provider_timestamp_pit_gate.json",
    "artifacts/pit/historical_known_at_replay_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-178.json",
    "jira/project/JIRA_TARGET_PROFILE.yaml"
  ],
  "gap_ids": [
    "GAP-002",
    "GAP-003"
  ],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-178_admit_wmt_provider_timestamped_gamebook_records_for_domain_granular_development_pit.md",
  "governance_traceability_gate": "POST-SUBTASK-033",
  "historical_classification": "POST_W25_IMPLEMENTATION",
  "import_id": 100486,
  "in_scope": [
    "Provider-timestamp extraction from exact immutable Texas A&M official WMT game, action, play, drive, and player records.",
    "Domain-granular target-cutoff eligibility, canonical identity joins, partial-coverage reporting, provenance, deterministic replay, and development-only PIT admission.",
    "A separately lineaged feature candidate for a later preliminary unprotected replay without protected or production authority."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-535",
  "labels": [
    "actionable",
    "post-wave",
    "subtask",
    "historical-expansion",
    "gamebook",
    "wmt",
    "plays",
    "drives",
    "players",
    "pit",
    "preliminary-unprotected",
    "provenance"
  ],
  "last_content_audit": "2026-08-11",
  "local_id": "POST-SUBTASK-178",
  "maturity_before": "VALIDATED_OFFICIAL_CANDIDATE_UNKNOWN_EXACT_HISTORICAL_TIME",
  "objective": "Admit only exact official WMT gamebook records whose provider version timestamps are before each target cutoff into a domain-granular development-only PIT layer.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24925",
    "jira_updated_at": "2026-08-12T11:20:29.390-0500",
    "last_synced_at": "2026-08-12T16:21:58.376101+00:00",
    "source_export": "jira/reconciliation/BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "Done"
  },
  "out_of_scope": [
    "Treating event/game time, current 2026 capture time, PDF creation metadata, or a model-generated value as historical publication time.",
    "Admitting records with missing, invalid, or post-cutoff provider timestamps, or silently promoting incomplete domains.",
    "Protected training/evaluation, champion or production promotion, publication, final historical readiness, A&M lift, BAS, Aggie Excess, or any scientific result."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-010",
  "phase": "PHASE-1",
  "prerequisites": [
    "Pinned d227b6cf official WMT gamebook acquisition manifest and immutable raw captures.",
    "Pinned expanded target replay and exact target-game cutoff matrix.",
    "Canonical game/team identities and protected PIT/leakage rules.",
    "Configured standardized external data root."
  ],
  "primary_source_refs": [
    "SRCREF-02013",
    "SRCREF-02006",
    "SRCREF-01889"
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
  "record_revision": "2.0",
  "required_evidence": [
    "Exact acquisition, capture, payload, game, record, timestamp, target-cutoff, code, contract, dataset, manifest, validation, and rollback identities.",
    "Counts by source season, domain, schema, timestamp field, timestamp year, target season, eligibility, exclusion, missingness, and reconciliation disposition.",
    "Zero target-game overlap, strict known-at ordering, no target/outcome fields, mutation controls, byte-identical rebuild, and cleanup evidence.",
    "Explicit development-only PIT/preliminary authority and protected/production/scientific nonclaims."
  ],
  "required_tests": [
    {
      "classification": "NEW_AUTOMATED_TEST_REQUIRED",
      "expectation": "Provider timestamp parsing, maximum-version selection, domain isolation, cutoff ordering, target exclusion, invalid timestamp quarantine, and protected nonauthority remain deterministic.",
      "path": "tests/test_wmt_provider_timestamp_pit.py",
      "validation_class": "PIT_LEAKAGE"
    },
    {
      "classification": "END_TO_END",
      "expectation": "The complete 177-payload population, external artifacts, identities, hashes, target-cutoff eligibility, mutation controls, and byte-identical isolated rebuild pass independent validation.",
      "path": "artifacts/jira_evidence/POST-SUBTASK-178.json",
      "validation_class": "END_TO_END"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "Any source, record, timestamp, mapping, target, schema, population, hash, or deterministic rebuild identity drifts.",
    "Any event-time substitution, target game, future record, outcome field, missing timestamp, invalid identity, or fabricated value enters an admitted payload.",
    "Any development-only artifact is represented as protected, champion, production, forecast-publication, or scientific authority."
  ],
  "risk_ids": [
    "RISK-227",
    "RISK-241",
    "RISK-242"
  ],
  "schema_version": 2,
  "scope": "Convert exact provider-version metadata in the pinned official WMT gamebook payloads into record- and domain-granular development PIT eligibility without backcasting or global completeness claims.",
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
    "Stop the affected record or artifact on provider timestamp, source identity, schema, mapping, chronology, target overlap, authority, hash, or deterministic rebuild failure.",
    "Exclude or quarantine only affected rows or domains; do not block independent historical acquisition, preliminary modeling, or other source routes.",
    "Do not weaken PIT, leakage, identity, validation, or protected gates to obtain apparent coverage."
  ],
  "supporting_source_refs": [
    "SRCREF-02014",
    "SRCREF-02016",
    "SRCREF-02018",
    "SRCREF-01564"
  ],
  "title": "Admit WMT provider-timestamped gamebook records for domain-granular development PIT",
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
  "why_this_exists": "The official WMT payloads contain record-level provider creation and update metadata that can recover conservative known-at eligibility for substantial historical gamebook domains without inventing publication times.",
  "work_packet_path": "",
  "workflow_state": "DONE"
}
```

## Objective

Admit only exact official WMT gamebook records whose provider version timestamps are before each target cutoff into a domain-granular development-only PIT layer.

## Why This Exists

The official WMT payloads contain record-level provider creation and update metadata that can recover conservative known-at eligibility for substantial historical gamebook domains without inventing publication times.

## Scope

Convert exact provider-version metadata in the pinned official WMT gamebook payloads into record- and domain-granular development PIT eligibility without backcasting or global completeness claims.

### Explicit In Scope

- Provider-timestamp extraction from exact immutable Texas A&M official WMT game, action, play, drive, and player records.
- Domain-granular target-cutoff eligibility, canonical identity joins, partial-coverage reporting, provenance, deterministic replay, and development-only PIT admission.
- A separately lineaged feature candidate for a later preliminary unprotected replay without protected or production authority.

### Explicit Out of Scope

- Treating event/game time, current 2026 capture time, PDF creation metadata, or a model-generated value as historical publication time.
- Admitting records with missing, invalid, or post-cutoff provider timestamps, or silently promoting incomplete domains.
- Protected training/evaluation, champion or production promotion, publication, final historical readiness, A&M lift, BAS, Aggie Excess, or any scientific result.

## Prerequisites

- Pinned d227b6cf official WMT gamebook acquisition manifest and immutable raw captures.
- Pinned expanded target replay and exact target-game cutoff matrix.
- Canonical game/team identities and protected PIT/leakage rules.
- Configured standardized external data root.

## Hard Dependencies

- POST-SUBTASK-029
- POST-SUBTASK-175

## Blocks

- POST-SUBTASK-179

## Read / Inspect First

- None.

## Files Expected To Be Modified

- configs/wmt_provider_timestamp_pit_contract.json
- configs/historical_known_at_recovery_contract.json
- src/aggie_analytics/temporal/wmt_provider_timestamp_pit.py
- tools/build_wmt_provider_timestamp_pit.py
- tools/validate_wmt_provider_timestamp_pit.py
- tests/test_wmt_provider_timestamp_pit.py
- tests/test_historical_known_at_recovery_contract.py
- tests/test_jira_control_plane.py
- artifacts/pit/wmt_provider_timestamp_pit_gate.json
- artifacts/pit/historical_known_at_replay_gate.json
- artifacts/jira_evidence/POST-SUBTASK-178.json
- jira/project/JIRA_TARGET_PROFILE.yaml

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

- configs/wmt_provider_timestamp_pit_contract.json
- src/aggie_analytics/temporal/wmt_provider_timestamp_pit.py
- tools/build_wmt_provider_timestamp_pit.py
- tools/validate_wmt_provider_timestamp_pit.py
- artifacts/pit/wmt_provider_timestamp_pit_gate.json
- artifacts/jira_evidence/POST-SUBTASK-178.json
- <external-data-root>/pit_state/historical_known_at/sha256/<dataset_identity>/wmt_provider_timestamp_records.parquet
- <external-data-root>/features/historical_known_at/sha256/<dataset_identity>/target_cutoff_wmt_domain_features.parquet
- <external-data-root>/manifests/historical_known_at/sha256/<dataset_identity>/wmt_provider_timestamp_pit_manifest.json
- <external-data-root>/validation/POST-SUBTASK-178/wmt_provider_timestamp_pit_validation.json

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

1. Only records from the pinned Texas A&M official WMT gamebook acquisition identity d227b6cf are eligible, and every admitted record retains its source capture, payload, game, domain, record, and provider timestamp identity.
2. Known-at time is the maximum parseable provider created/updated/version timestamp on the exact record; game time, current capture time, PDF metadata, model output, and inferred publication time are never substituted.
3. Eligibility is computed independently by game, action, play, drive, and player domain at each target cutoff; a missing or post-cutoff timestamp excludes only the affected record or domain.
4. Target-game records and future records are excluded from every target feature; identity joins remain canonical and no name-only merge, factual imputation, or timestamp fabrication is permitted.
5. Authority is limited to development-only PIT and preliminary unprotected research; protected evaluation, champion promotion, production forecasts, A&M lift, BAS, Aggie Excess, final historical readiness, and scientific claims remain closed.

## Definition of Done

1. All 177 pinned WMT payloads are replayed and every game, action, play, drive, and player record is classified independently by provider timestamp coverage, source season, target cutoff eligibility, and exclusion reason.
2. Immutable content-addressed candidate/PIT payloads and manifests are stored outside Git with exact population, schema, missingness, timestamp distribution, and provenance identities.
3. Target-cutoff joins prove strict source-known-at-before-cutoff ordering, zero target-game overlap, no target or outcome fields, domain-specific partial coverage, and deterministic byte-identical replay.
4. Repository, provenance, Jira second-pass, PIT/leakage, secret, and full automated test gates pass, and reconstructible temporary output is cleaned.
5. The historical recovery contract, replay gate, Jira evidence, governing goal, and active plan preserve development-only authority and all protected nonclaims.

## Required Tests / Validation

- **NEW_AUTOMATED_TEST_REQUIRED** / `PIT_LEAKAGE` — `tests/test_wmt_provider_timestamp_pit.py` — Provider timestamp parsing, maximum-version selection, domain isolation, cutoff ordering, target exclusion, invalid timestamp quarantine, and protected nonauthority remain deterministic.
- **END_TO_END** / `END_TO_END` — `artifacts/jira_evidence/POST-SUBTASK-178.json` — The complete 177-payload population, external artifacts, identities, hashes, target-cutoff eligibility, mutation controls, and byte-identical isolated rebuild pass independent validation.

## Required Evidence

- Exact acquisition, capture, payload, game, record, timestamp, target-cutoff, code, contract, dataset, manifest, validation, and rollback identities.
- Counts by source season, domain, schema, timestamp field, timestamp year, target season, eligibility, exclusion, missingness, and reconciliation disposition.
- Zero target-game overlap, strict known-at ordering, no target/outcome fields, mutation controls, byte-identical rebuild, and cleanup evidence.
- Explicit development-only PIT/preliminary authority and protected/production/scientific nonclaims.

## Completion Evidence Contract

```json
{}
```

## End-to-End Validation Requirement

Re-read the pinned d227b6cf acquisition manifest and every referenced immutable WMT payload; independently derive the maximum record-level provider timestamp, rebuild domain rows and target-cutoff eligibility, verify hashes, schemas, counts, chronology, target exclusion, authority, and byte identity, then remove the reconstructible rebuild.

## Expected Maturity After Completion

`DEVELOPMENT_ONLY_PIT_ADMITTED`

## Risk / Failure Conditions

- Any source, record, timestamp, mapping, target, schema, population, hash, or deterministic rebuild identity drifts.
- Any event-time substitution, target game, future record, outcome field, missing timestamp, invalid identity, or fabricated value enters an admitted payload.
- Any development-only artifact is represented as protected, champion, production, forecast-publication, or scientific authority.

## Stop Conditions

- Stop the affected record or artifact on provider timestamp, source identity, schema, mapping, chronology, target overlap, authority, hash, or deterministic rebuild failure.
- Exclude or quarantine only affected rows or domains; do not block independent historical acquisition, preliminary modeling, or other source routes.
- Do not weaken PIT, leakage, identity, validation, or protected gates to obtain apparent coverage.

## Source References

- SRCREF-02013
- SRCREF-02014
- SRCREF-02016
- SRCREF-02018
- SRCREF-02006
- SRCREF-01889
- SRCREF-01564

## AI Context Notes

- The provider timestamps are deterministic source metadata already present in immutable raw WMT payloads; OpenAI has no role in timestamp selection, identity, admission, or canonical truth.
- A later provider update makes the current record version eligible only after that update; this unit never backcasts current payload content to game date.
- Partial source seasons and domains remain explicit and do not globally block historical expansion or preliminary modeling.

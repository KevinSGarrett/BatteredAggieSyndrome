<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-193_materialize_capture_time_player_box_snapshot_and_stat_cell_eligibility_gate.json -->
# POST-SUBTASK-193 — [POST-SUBTASK-193] Materialize capture-time player-box snapshot and stat-cell eligibility gate

## Canonical metadata

```json
{
  "acceptance_control_ids": [
    "AC-011",
    "AC-073",
    "AC-075",
    "AC-079",
    "AC-080"
  ],
  "acceptance_criteria": [
    "All 5,279,775 source stat cells and sixteen season payloads are hash-verified and deterministically dispositioned without changing the corrected candidate population.",
    "The exact candidate contains only current-game multiset-exact or unique play-derived metric-exact cells; team-box-only, invalid-core, and play-derived conflict cells remain separately nonadmitted at stat-cell grain.",
    "Every retained cell preserves exact game/team/provider-player/category/type/value, raw and normalized player labels, capture coordinates, source evidence, identity candidates, reconciliation evidence, and lineage without name-only player merges.",
    "The three one-team games, 246 invalid-core cells, 34,006 play-derived value conflicts, 47,446 whitespace-drift cells, partial seasons, and all provider limitations remain explicit.",
    "Historical known-at remains unknown, no pre-capture PIT or preliminary replay feature is admitted, and outputs pass identity, schema, missingness, quarantine, mutation, byte-rebuild, Jira, repository, provenance, and full-suite validation before Done."
  ],
  "adr_ids": [
    "ADR-005",
    "ADR-006",
    "ADR-042",
    "ADR-111",
    "ADR-119"
  ],
  "ai_context_notes": [
    "No OpenAI output or generated fact may participate in game/team/player identity, category/type/value, publication timing, conflict resolution, missingness, or validation.",
    "Provider athlete IDs remain canonical-player candidates only; no name-only or model-only merge is allowed.",
    "Current 2022-2025 same-provider multiset matches validate reproducibility, not independent truth; play-derived exact matches validate only six bounded metrics and may share ESPN upstream origin.",
    "This unit is a capture-time candidate snapshot prerequisite, not official primary gamebook truth, historical PIT, preliminary-model, protected, production, or scientific authority."
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-193_materialize_capture_time_player_box_snapshot_and_stat_cell_eligibility_gate.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "component": "pit-temporal",
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
    "Per-season capture-time exact-candidate and nonadmitted artifacts are immutable, content-addressed, reproducible, and externally stored.",
    "Independent reconstruction verifies source hashes, exact population, natural keys, dispositions, player-label preservation, missingness, one-team games, conflicts, capture-time authority, mutations, and byte identity.",
    "Canonical/live Jira, Git/PR evidence, governing goal, active plan, cleanup, OpenAI non-use rationale, and all scientific nonclaims agree before Done."
  ],
  "dependencies": [
    "POST-SUBTASK-029",
    "POST-SUBTASK-042",
    "POST-SUBTASK-185",
    "POST-SUBTASK-191"
  ],
  "end_to_end_validation": "Re-read the corrected candidate manifest, source captures, team-box and player-event prerequisites, current multiset evidence, and all sixteen season payloads; rebuild in an isolated external root; verify hashes, populations, natural keys, dispositions, label whitespace, missingness, one-team games, conflicts, capture-time authority, quarantine, forbidden fields, mutation controls, and byte identity; then remove only reconstructible output after validation.",
  "epic_id": "POST-EPIC-003",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-193.json",
  "evidence_state": "VERIFIED",
  "execution_lane": "DATA",
  "execution_mode": "HISTORICAL_REFERENCE",
  "expected_maturity_after_completion": "VALIDATED_RECONCILED_CANDIDATE_ONLY",
  "expected_outputs": [
    "configs/historical_player_box_snapshot_contract.json",
    "artifacts/pit/historical_player_box_snapshot_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-193.json",
    "<external-data-root>/quarantine/historical_capture_time/sha256/<dataset_identity>/exact_reconciled_player_box_stat_cells.parquet",
    "<external-data-root>/quarantine/historical_capture_time/sha256/<dataset_identity>/nonadmitted_player_box_stat_cells.parquet",
    "<external-data-root>/manifests/historical_capture_time/sha256/<dataset_identity>/historical_player_box_snapshot_manifest.json",
    "<external-data-root>/validation/POST-SUBTASK-193/<dataset_identity>/historical_player_box_snapshot_validation.json"
  ],
  "files_expected_to_be_read": [
    "artifacts/pit/historical_team_box_snapshot_gate.json",
    "artifacts/pit/historical_player_event_metric_pit_gate.json",
    "artifacts/entities/CANONICAL_ENTITY_SNAPSHOT.json"
  ],
  "files_expected_to_be_touched": [
    "configs/historical_player_box_snapshot_contract.json",
    "src/aggie_analytics/temporal/player_box_snapshot.py",
    "tools/build_historical_player_box_snapshot.py",
    "tools/validate_historical_player_box_snapshot.py",
    "tests/test_historical_player_box_snapshot.py",
    "artifacts/pit/historical_player_box_snapshot_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-193.json"
  ],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-193_materialize_capture_time_player_box_snapshot_and_stat_cell_eligibility_gate.md",
  "governance_traceability_gate": "POST-SUBTASK-033",
  "historical_classification": "POST_W25_IMPLEMENTATION",
  "import_id": 100501,
  "in_scope": [
    "Corrected immutable candidate d866f2ba94b9c19a966e0eaf8326259b5761b64386f9829a95d43b9e2831069d across 2010-2025, 13,670 games, 27,337 team rows, 5,279,775 stat cells, 63,407 provider player IDs, and sixteen source seasons.",
    "Current-game multiset-exact and unique play-derived metric-exact candidate cells, team-box-only and conflict quarantine, provider-ID player candidates, raw/normalized label evidence, partiality, capture provenance, deterministic replay, and capture-time-only eligibility."
  ],
  "issue_type": "Sub-task",
  "jira_key": "BAT-550",
  "labels": [
    "actionable",
    "post-wave",
    "subtask",
    "historical-expansion",
    "player-box",
    "capture-time",
    "candidate-only",
    "entity-resolution",
    "conflict-quarantine",
    "provenance",
    "local-id-post-subtask-193"
  ],
  "last_content_audit": "2026-08-11",
  "local_id": "POST-SUBTASK-193",
  "maturity_before": "VALIDATED_RECONCILED_CANDIDATE_ONLY",
  "objective": "Materialize and independently validate the corrected 2010-2025 player-box candidate as an immutable capture-time stat-cell snapshot while preserving provider-player identity boundaries, exact current/play-derived evidence, invalid core, conflicts, label whitespace, incomplete game sides, and the prohibition on historical PIT backcast.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24942",
    "jira_updated_at": "2026-08-12T11:20:29.844-0500",
    "last_synced_at": "2026-08-12T16:21:58.376101+00:00",
    "source_export": "jira/reconciliation/BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "Done"
  },
  "out_of_scope": [
    "Historical publication-time inference, pre-capture PIT backcast, same-provider overlap as independent confirmation, name-only player merges, conflict-value selection, zero-filling, rewriting immutable source captures, or representing aggregator boxes as official primary gamebooks.",
    "Protected training/evaluation, champion or production promotion, forecast publication, final historical completeness, A&M lift, BAS, Aggie Excess, or scientific claims."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-010",
  "phase": "PHASE-1",
  "prerequisites": [
    "Corrected player-box candidate manifest SHA-256 bcc3ef592d3a586934cab141e772c2f74843964533bd23fa8765eacad9206ca4 and all referenced season/capture payload hashes verify.",
    "BAT-548 capture-time team-box identity f2e8fae89ca3659adad710b4b9b952cdb391a1b3c0c44956803b0e29c219a733 remains immutable and candidate-only.",
    "BAT-542 version-bound player-event candidate 869818c5fe312bafbff5139eadb21153069d974ea7f576f154a58ecb6d888f10 remains bounded to six metrics and its known-at contract.",
    "Verified recovery checkpoint C:/BatteredAggieSyndrome.data/backups/POST-SUBTASK-193-PRECHANGE-20260811T202146Z."
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
  "record_revision": "1.2",
  "related_to": [
    "POST-SUBTASK-169",
    "POST-SUBTASK-192"
  ],
  "required_evidence": [
    "Exact corrected-candidate, capture, raw, team-box, player-event, current-multiset, entity, contract, code, dataset, manifest, validation, Git, PR, and hosted-check identities.",
    "Per-season cells/games/players, dispositions, natural-key uniqueness, label whitespace, missing core, one-team games, conflicts, partiality, capture times, quarantine, mutation controls, and byte-identical rebuild.",
    "Explicit capture-time-only, candidate-only, provider-ID-candidate-only, no historical PIT backcast, no name-only merge, no zero-fill, no independent-confirmation, and protected/production/completeness/scientific nonclaims."
  ],
  "required_tests": [
    {
      "classification": "NEW_AUTOMATED_TEST_REQUIRED",
      "expectation": "Exact capture-time player-box snapshot, provider-player identity boundary, cell-level conflicts, label preservation, incomplete games, and no-backcast authority remain deterministic.",
      "path": "tests/test_historical_player_box_snapshot.py",
      "validation_class": "PIT_LEAKAGE"
    },
    {
      "classification": "END_TO_END",
      "expectation": "The complete external population passes source identity, reconstruction, schema, provenance, quarantine, mutation, and byte-identity checks.",
      "path": "artifacts/jira_evidence/POST-SUBTASK-193.json",
      "validation_class": "END_TO_END"
    }
  ],
  "requirement_ids": [
    "REQ-039",
    "REQ-041",
    "REQ-052",
    "REQ-053",
    "REQ-063",
    "REQ-199",
    "REQ-319",
    "REQ-323",
    "REQ-345"
  ],
  "risk_failure_conditions": [
    "Any source hash, row count, game/team/player/category/type/value identity, natural key, label form, conflict disposition, capture identity, or rebuild identity drifts.",
    "Any historical publication time, name-only player merge, conflict-selected or zero-filled value, target/outcome field, protected decision, or fabricated statistic enters the snapshot."
  ],
  "risk_ids": [
    "RISK-050",
    "RISK-099",
    "RISK-106",
    "RISK-227",
    "RISK-241"
  ],
  "schema_version": 2,
  "scope": "Disposition all 5,279,775 candidate player stat cells, materialize only current-multiset-exact or unique play-derived exact cells, preserve provider player IDs as candidates, quarantine team-box-only/invalid/conflict cells, and publish an explicit capture-time eligibility gate with per-season coverage, incomplete-game, label, missingness, and conflict evidence.",
  "source_ids": [
    "GAP-002",
    "GAP-003",
    "HANDOFF-003"
  ],
  "source_refs": [
    "SRCREF-02013",
    "SRCREF-02016",
    "SRCREF-02018",
    "SRCREF-02014",
    "SRCREF-02006",
    "SRCREF-01889",
    "SRCREF-01564",
    "SRCREF-02042"
  ],
  "stop_conditions": [
    "Stop the affected cell, player, game, season, disposition, or artifact on identity, source, reconciliation, schema, missingness, incomplete-side, conflict, authority, hash, population, or rebuild failure.",
    "Do not weaken capture-time-only, candidate-only, provider-ID-candidate-only, no-name-merge, no-backcast, no-zero-fill, or scientific boundaries merely to obtain approval."
  ],
  "supporting_source_refs": [
    "SRCREF-02014",
    "SRCREF-02006",
    "SRCREF-01889",
    "SRCREF-01564",
    "SRCREF-02042"
  ],
  "title": "[POST-SUBTASK-193] Materialize capture-time player-box snapshot and stat-cell eligibility gate",
  "traceability_inherited_from": [
    "POST-SUBTASK-033"
  ],
  "traceability_resolution": "DIRECT_PLUS_INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "why_this_exists": "The corrected player-box candidate is the last direct bulk dependent of the team-box capture-time snapshot. It offers exact reproducibility for 2022-2025 and exact six-metric play-derived evidence for 2014-2022, but historical publication times are unknown, provider athlete IDs remain candidates, conflicting cells and incomplete games exist, and every weaker link must remain explicitly nonadmitted.",
  "work_packet_path": "",
  "workflow_state": "DONE"
}
```

## Objective

Materialize and independently validate the corrected 2010-2025 player-box candidate as an immutable capture-time stat-cell snapshot while preserving provider-player identity boundaries, exact current/play-derived evidence, invalid core, conflicts, label whitespace, incomplete game sides, and the prohibition on historical PIT backcast.

## Why This Exists

The corrected player-box candidate is the last direct bulk dependent of the team-box capture-time snapshot. It offers exact reproducibility for 2022-2025 and exact six-metric play-derived evidence for 2014-2022, but historical publication times are unknown, provider athlete IDs remain candidates, conflicting cells and incomplete games exist, and every weaker link must remain explicitly nonadmitted.

## Scope

Disposition all 5,279,775 candidate player stat cells, materialize only current-multiset-exact or unique play-derived exact cells, preserve provider player IDs as candidates, quarantine team-box-only/invalid/conflict cells, and publish an explicit capture-time eligibility gate with per-season coverage, incomplete-game, label, missingness, and conflict evidence.

### Explicit In Scope

- Corrected immutable candidate d866f2ba94b9c19a966e0eaf8326259b5761b64386f9829a95d43b9e2831069d across 2010-2025, 13,670 games, 27,337 team rows, 5,279,775 stat cells, 63,407 provider player IDs, and sixteen source seasons.
- Current-game multiset-exact and unique play-derived metric-exact candidate cells, team-box-only and conflict quarantine, provider-ID player candidates, raw/normalized label evidence, partiality, capture provenance, deterministic replay, and capture-time-only eligibility.

### Explicit Out of Scope

- Historical publication-time inference, pre-capture PIT backcast, same-provider overlap as independent confirmation, name-only player merges, conflict-value selection, zero-filling, rewriting immutable source captures, or representing aggregator boxes as official primary gamebooks.
- Protected training/evaluation, champion or production promotion, forecast publication, final historical completeness, A&M lift, BAS, Aggie Excess, or scientific claims.

## Prerequisites

- Corrected player-box candidate manifest SHA-256 bcc3ef592d3a586934cab141e772c2f74843964533bd23fa8765eacad9206ca4 and all referenced season/capture payload hashes verify.
- BAT-548 capture-time team-box identity f2e8fae89ca3659adad710b4b9b952cdb391a1b3c0c44956803b0e29c219a733 remains immutable and candidate-only.
- BAT-542 version-bound player-event candidate 869818c5fe312bafbff5139eadb21153069d974ea7f576f154a58ecb6d888f10 remains bounded to six metrics and its known-at contract.
- Verified recovery checkpoint C:/BatteredAggieSyndrome.data/backups/POST-SUBTASK-193-PRECHANGE-20260811T202146Z.

## Hard Dependencies

- POST-SUBTASK-029
- POST-SUBTASK-042
- POST-SUBTASK-185
- POST-SUBTASK-191

## Blocks

- None.

## Read / Inspect First

- None.

## Files Expected To Be Modified

- configs/historical_player_box_snapshot_contract.json
- src/aggie_analytics/temporal/player_box_snapshot.py
- tools/build_historical_player_box_snapshot.py
- tools/validate_historical_player_box_snapshot.py
- tests/test_historical_player_box_snapshot.py
- artifacts/pit/historical_player_box_snapshot_gate.json
- artifacts/jira_evidence/POST-SUBTASK-193.json

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

- configs/historical_player_box_snapshot_contract.json
- artifacts/pit/historical_player_box_snapshot_gate.json
- artifacts/jira_evidence/POST-SUBTASK-193.json
- <external-data-root>/quarantine/historical_capture_time/sha256/<dataset_identity>/exact_reconciled_player_box_stat_cells.parquet
- <external-data-root>/quarantine/historical_capture_time/sha256/<dataset_identity>/nonadmitted_player_box_stat_cells.parquet
- <external-data-root>/manifests/historical_capture_time/sha256/<dataset_identity>/historical_player_box_snapshot_manifest.json
- <external-data-root>/validation/POST-SUBTASK-193/<dataset_identity>/historical_player_box_snapshot_validation.json

## Direct Requirements

- REQ-039
- REQ-041
- REQ-052
- REQ-053
- REQ-063
- REQ-199
- REQ-319
- REQ-323
- REQ-345

## Direct Acceptance Controls

- AC-011
- AC-073
- AC-075
- AC-079
- AC-080

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-033`
- Inherited from: POST-SUBTASK-033
- Resolution: `DIRECT_PLUS_INHERITED_DOMAIN_GATE`
- Effective counts: `{}`

## Acceptance Criteria

1. All 5,279,775 source stat cells and sixteen season payloads are hash-verified and deterministically dispositioned without changing the corrected candidate population.
2. The exact candidate contains only current-game multiset-exact or unique play-derived metric-exact cells; team-box-only, invalid-core, and play-derived conflict cells remain separately nonadmitted at stat-cell grain.
3. Every retained cell preserves exact game/team/provider-player/category/type/value, raw and normalized player labels, capture coordinates, source evidence, identity candidates, reconciliation evidence, and lineage without name-only player merges.
4. The three one-team games, 246 invalid-core cells, 34,006 play-derived value conflicts, 47,446 whitespace-drift cells, partial seasons, and all provider limitations remain explicit.
5. Historical known-at remains unknown, no pre-capture PIT or preliminary replay feature is admitted, and outputs pass identity, schema, missingness, quarantine, mutation, byte-rebuild, Jira, repository, provenance, and full-suite validation before Done.

## Definition of Done

1. Per-season capture-time exact-candidate and nonadmitted artifacts are immutable, content-addressed, reproducible, and externally stored.
2. Independent reconstruction verifies source hashes, exact population, natural keys, dispositions, player-label preservation, missingness, one-team games, conflicts, capture-time authority, mutations, and byte identity.
3. Canonical/live Jira, Git/PR evidence, governing goal, active plan, cleanup, OpenAI non-use rationale, and all scientific nonclaims agree before Done.

## Required Tests / Validation

- **NEW_AUTOMATED_TEST_REQUIRED** / `PIT_LEAKAGE` — `tests/test_historical_player_box_snapshot.py` — Exact capture-time player-box snapshot, provider-player identity boundary, cell-level conflicts, label preservation, incomplete games, and no-backcast authority remain deterministic.
- **END_TO_END** / `END_TO_END` — `artifacts/jira_evidence/POST-SUBTASK-193.json` — The complete external population passes source identity, reconstruction, schema, provenance, quarantine, mutation, and byte-identity checks.

## Required Evidence

- Exact corrected-candidate, capture, raw, team-box, player-event, current-multiset, entity, contract, code, dataset, manifest, validation, Git, PR, and hosted-check identities.
- Per-season cells/games/players, dispositions, natural-key uniqueness, label whitespace, missing core, one-team games, conflicts, partiality, capture times, quarantine, mutation controls, and byte-identical rebuild.
- Explicit capture-time-only, candidate-only, provider-ID-candidate-only, no historical PIT backcast, no name-only merge, no zero-fill, no independent-confirmation, and protected/production/completeness/scientific nonclaims.

## Completion Evidence Contract

```json
{}
```

## End-to-End Validation Requirement

Re-read the corrected candidate manifest, source captures, team-box and player-event prerequisites, current multiset evidence, and all sixteen season payloads; rebuild in an isolated external root; verify hashes, populations, natural keys, dispositions, label whitespace, missingness, one-team games, conflicts, capture-time authority, quarantine, forbidden fields, mutation controls, and byte identity; then remove only reconstructible output after validation.

## Expected Maturity After Completion

`VALIDATED_RECONCILED_CANDIDATE_ONLY`

## Risk / Failure Conditions

- Any source hash, row count, game/team/player/category/type/value identity, natural key, label form, conflict disposition, capture identity, or rebuild identity drifts.
- Any historical publication time, name-only player merge, conflict-selected or zero-filled value, target/outcome field, protected decision, or fabricated statistic enters the snapshot.

## Stop Conditions

- Stop the affected cell, player, game, season, disposition, or artifact on identity, source, reconciliation, schema, missingness, incomplete-side, conflict, authority, hash, population, or rebuild failure.
- Do not weaken capture-time-only, candidate-only, provider-ID-candidate-only, no-name-merge, no-backcast, no-zero-fill, or scientific boundaries merely to obtain approval.

## Source References

- SRCREF-02013
- SRCREF-02016
- SRCREF-02018
- SRCREF-02014
- SRCREF-02006
- SRCREF-01889
- SRCREF-01564
- SRCREF-02042

## AI Context Notes

- No OpenAI output or generated fact may participate in game/team/player identity, category/type/value, publication timing, conflict resolution, missingness, or validation.
- Provider athlete IDs remain canonical-player candidates only; no name-only or model-only merge is allowed.
- Current 2022-2025 same-provider multiset matches validate reproducibility, not independent truth; play-derived exact matches validate only six bounded metrics and may share ESPN upstream origin.
- This unit is a capture-time candidate snapshot prerequisite, not official primary gamebook truth, historical PIT, preliminary-model, protected, production, or scientific authority.

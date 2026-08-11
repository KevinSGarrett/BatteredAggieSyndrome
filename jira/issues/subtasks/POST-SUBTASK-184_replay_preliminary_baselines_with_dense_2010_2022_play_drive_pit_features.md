<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-184_replay_preliminary_baselines_with_dense_2010_2022_play_drive_pit_features.json -->
# POST-SUBTASK-184 — Replay preliminary baselines with dense 2010-2022 play/drive PIT features

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "The immutable POST-SUBTASK-172 baseline ladder and POST-SUBTASK-177 play/drive replay remain unchanged and are consumed only through their pinned identities and manifests.",
    "Only exact POST-SUBTASK-183 development-PIT identity 1bd6f4c6 is joined to the unchanged 2023-2025 target population by canonical game and team identity; no name-only merge or fabricated label is permitted.",
    "Chronology remains closed to backcasting: 2023 is the frozen baseline fallback, 2024 fits only 2023 outcomes, and 2025 fits only 2023-2024 outcomes.",
    "Cold starts and null feature cells remain explicit under fit-only median imputation with indicators; the extra feature game without a pinned target is excluded rather than labeled.",
    "New artifacts compare against both the frozen baseline and POST-SUBTASK-177, preserve negative results, and remain PRELIMINARY_UNPROTECTED with no protected or production authority.",
    "The external datasets, models, forecasts, manifest, metrics, and dispositions pass schema, provenance, PIT, leakage, numerical replay, and byte-identical deterministic rebuild validation."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "This is a separately lineaged replay, not a mutation of POST-SUBTASK-172, POST-SUBTASK-177, or POST-SUBTASK-183.",
    "The dense profile summarizes exact 2010-2022 version-bound evidence but is known only by May 2023 and cannot be backcast into the 2010-2022 fit population.",
    "No OpenAI output or model-generated fact participates in features, labels, splits, timestamps, fitting, evaluation, or acceptance."
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-184_replay_preliminary_baselines_with_dense_2010_2022_play_drive_pit_features.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "component": "modeling",
  "components_expected_to_be_touched": [
    "modeling",
    "pit-temporal",
    "validation-promotion"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "A new immutable external dataset identity joins exact POST-SUBTASK-172 targets and splits to exact POST-SUBTASK-183 development-PIT features without rewriting any predecessor.",
    "The complete preliminary baseline foundation remains pinned and the two play/drive stackers run with chronological fit windows, fit-only imputation, cold-start handling, serialization, prediction replay, calibration diagnostics, and per-season/slice metrics.",
    "Paired comparisons against the frozen baseline and POST-SUBTASK-177 preserve improvement, degradation, and mixed results without changing thresholds to force adoption.",
    "Independent validation and an isolated rebuild reproduce every accepted payload byte-for-byte; reconstructible staging/rebuild/superseded-run artifacts are cleaned where host policy permits or retained under an exact blocked cleanup finding without bypass.",
    "Protected promotion remains closed and the approximately 2010-2025 historical-expansion workstream continues independently."
  ],
  "dependencies": [
    "POST-SUBTASK-172",
    "POST-SUBTASK-177",
    "POST-SUBTASK-183"
  ],
  "end_to_end_validation": "Re-read the exact POST-SUBTASK-172 baseline manifest, POST-SUBTASK-177 comparison manifest, and POST-SUBTASK-183 feature payload; rebuild the separately lineaged matrix, targets, splits, models, predictions, metrics, manifest, and validation report; verify all identities, chronology, target exclusion, protected closure, model replay, and byte identity; then clean reconstructible output where permitted or preserve the exact host-policy limitation.",
  "epic_id": "POST-EPIC-008",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-184.json",
  "evidence_state": "VERIFIED",
  "execution_lane": "MODEL_RESEARCH",
  "execution_mode": "HISTORICAL_REFERENCE",
  "expected_maturity_after_completion": "EMPIRICALLY_VALIDATED_PRELIMINARY_UNPROTECTED",
  "expected_outputs": [
    "configs/preliminary_dense_play_drive_replay_contract.json",
    "tools/run_preliminary_play_drive_augmented.py",
    "tools/validate_preliminary_play_drive_augmented.py",
    "tests/test_preliminary_play_drive_augmented.py",
    "artifacts/pit/preliminary_dense_play_drive_replay_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-184.json",
    "<external-data-root>/training/preliminary_dense_play_drive_replay/sha256/<dataset_identity>",
    "<external-data-root>/model_artifacts/preliminary_dense_play_drive_replay/sha256/<model_identity>",
    "<external-data-root>/forecast_snapshots/preliminary_dense_play_drive_replay/sha256/<forecast_identity>",
    "<external-data-root>/manifests/preliminary_dense_play_drive_replay/sha256/<run_identity>/run_manifest.json",
    "<external-data-root>/validation/POST-SUBTASK-184"
  ],
  "files_expected_to_be_read": [
    "artifacts/jira_evidence/POST-SUBTASK-172.json",
    "artifacts/jira_evidence/POST-SUBTASK-177.json",
    "artifacts/jira_evidence/POST-SUBTASK-183.json",
    "artifacts/pit/historical_play_drive_pit_aggregate_gate.json"
  ],
  "files_expected_to_be_touched": [
    "configs/preliminary_dense_play_drive_replay_contract.json",
    "tools/run_preliminary_play_drive_augmented.py",
    "tools/validate_preliminary_play_drive_augmented.py",
    "tests/test_preliminary_play_drive_augmented.py",
    "artifacts/pit/preliminary_dense_play_drive_replay_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-184.json",
    "jira/project/JIRA_TARGET_PROFILE.yaml"
  ],
  "gap_ids": [
    "GAP-002",
    "GAP-003",
    "GAP-005"
  ],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-184_replay_preliminary_baselines_with_dense_2010_2022_play_drive_pit_features.md",
  "governance_traceability_gate": "TASK-036",
  "historical_classification": "POST_W25_IMPLEMENTATION",
  "import_id": 100492,
  "in_scope": [
    "Exact canonical game/team join for the 2023-2025 POST-SUBTASK-183 feature population.",
    "Chronological replay that never backcasts the May 2023 publication horizon.",
    "Paired preliminary comparison, calibration diagnostics, serialization replay, deterministic reconstruction, provenance, and negative-result preservation."
  ],
  "issue_type": "Sub-task",
  "jira_key": "BAT-541",
  "labels": [
    "actionable",
    "post-wave",
    "subtask",
    "preliminary-unprotected",
    "baseline-modeling",
    "play-drive",
    "pit",
    "local-id-post-subtask-184"
  ],
  "last_content_audit": "2026-08-11",
  "local_id": "POST-SUBTASK-184",
  "maturity_before": "EMPIRICALLY_VALIDATED_PRELIMINARY_UNPROTECTED",
  "objective": "Replay the preliminary model pipeline with exact dense 2010-2022 POST-SUBTASK-183 play/drive development-PIT features without mutating predecessors or opening protected promotion.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24932",
    "jira_updated_at": "2026-08-11T08:30:02.875-0500",
    "last_synced_at": "2026-08-11T13:30:25.367888+00:00",
    "source_export": "jira/reconciliation/BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "Done"
  },
  "out_of_scope": [
    "Backcasting the dense features into 2010-2022 fit rows or fabricating an earlier known-at timestamp.",
    "Changing any immutable predecessor dataset, model, forecast, split, metric, or conclusion.",
    "Protected evaluation, champion or production promotion, forecast publication, A&M specialization lift, BAS, Aggie Excess, or any scientific claim."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-025",
  "phase": "PHASE-1",
  "prerequisites": [
    "POST-SUBTASK-172 exact preliminary event-chronology baseline ladder and immutable identities.",
    "POST-SUBTASK-177 exact earlier play/drive comparison run.",
    "POST-SUBTASK-183 exact dense development-only PIT feature identity and independent validation.",
    "Verified pre-change recovery checkpoint C:/BatteredAggieSyndrome.data/backups/POST-SUBTASK-184-PRECHANGE-20260811T125447Z."
  ],
  "primary_source_refs": [
    "SRCREF-00069",
    "SRCREF-02049",
    "SRCREF-02050"
  ],
  "priority": "P0",
  "protected_files_and_interfaces": [
    "governance/PROTECTED_ACCEPTANCE_RULES.md",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "governance/THRESHOLD_PRECOMMITMENT_REGISTRY.csv",
    "configs/judging_rule_seal.json"
  ],
  "ready": false,
  "record_revision": "2.0",
  "required_evidence": [
    "Exact POST-SUBTASK-172, POST-SUBTASK-177, and POST-SUBTASK-183 input hashes plus new dataset, feature, target, split, model, forecast, run, code, config, and validation identities.",
    "Rows, games, seasons, feature counts, cold starts, missingness, exclusions, fit windows, leakage checks, per-season/slice metrics, and paired deltas.",
    "Deterministic rebuild, numerical model replay, cleanup, live Jira/GitHub integration, and explicit protected nonclaims."
  ],
  "required_tests": [
    {
      "classification": "NEW_AUTOMATED_TEST_REQUIRED",
      "expectation": "Dense input pinning, separate lineage, chronology, cold starts, target exclusion, and protected nonauthority remain deterministic.",
      "path": "tests/test_preliminary_play_drive_augmented.py",
      "validation_class": "PIT_LEAKAGE"
    },
    {
      "classification": "END_TO_END",
      "expectation": "The joined dataset, models, predictions, metrics, hashes, numerical replay, and isolated byte-identical rebuild pass independent validation.",
      "path": "artifacts/jira_evidence/POST-SUBTASK-184.json",
      "validation_class": "END_TO_END"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "Any dense feature is backdated or used to fit an outcome at or after its target season.",
    "Any target event, future outcome, name-only identity, missing fact, label, or timestamp is fabricated.",
    "Any result is represented as protected, champion, production, forecast-publication, A&M-lift, BAS, Aggie Excess, or scientific authority."
  ],
  "risk_ids": [
    "RISK-227",
    "RISK-241",
    "RISK-242"
  ],
  "schema_version": "2.0",
  "scope": "Build and independently validate a separately lineaged PRELIMINARY_UNPROTECTED replay using only the exact POST-SUBTASK-183 dense development-PIT feature population at its defensible known-at horizon.",
  "source_ids": [
    "TASK-036",
    "GAP-002",
    "GAP-003",
    "GAP-005"
  ],
  "source_refs": [
    "SRCREF-00069",
    "SRCREF-02049",
    "SRCREF-02050"
  ],
  "stop_conditions": [
    "Stop the affected artifact on input hash, identity, chronology, target overlap, schema, missingness, serialization, numerical replay, metric, or byte-rebuild failure.",
    "Quarantine only affected rows or model families and continue independently valid historical acquisition and baseline work.",
    "Do not weaken chronology, imputation, comparison, validation, or scientific boundaries merely to obtain improvement."
  ],
  "supporting_source_refs": [],
  "title": "Replay preliminary baselines with dense 2010-2022 play/drive PIT features",
  "traceability_inherited_from": [
    "TASK-036"
  ],
  "traceability_resolution": "DIRECT_PLUS_INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "END_TO_END",
    "PIT_LEAKAGE",
    "PROVENANCE",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "POST-SUBTASK-183 superseded the earlier partial play/drive PIT feature identity. Its denser evidence must be evaluated through a new immutable replay rather than silently replacing POST-SUBTASK-177 or being assumed beneficial.",
  "work_packet_path": "",
  "workflow_state": "DONE"
}
```

## Objective

Replay the preliminary model pipeline with exact dense 2010-2022 POST-SUBTASK-183 play/drive development-PIT features without mutating predecessors or opening protected promotion.

## Why This Exists

POST-SUBTASK-183 superseded the earlier partial play/drive PIT feature identity. Its denser evidence must be evaluated through a new immutable replay rather than silently replacing POST-SUBTASK-177 or being assumed beneficial.

## Scope

Build and independently validate a separately lineaged PRELIMINARY_UNPROTECTED replay using only the exact POST-SUBTASK-183 dense development-PIT feature population at its defensible known-at horizon.

### Explicit In Scope

- Exact canonical game/team join for the 2023-2025 POST-SUBTASK-183 feature population.
- Chronological replay that never backcasts the May 2023 publication horizon.
- Paired preliminary comparison, calibration diagnostics, serialization replay, deterministic reconstruction, provenance, and negative-result preservation.

### Explicit Out of Scope

- Backcasting the dense features into 2010-2022 fit rows or fabricating an earlier known-at timestamp.
- Changing any immutable predecessor dataset, model, forecast, split, metric, or conclusion.
- Protected evaluation, champion or production promotion, forecast publication, A&M specialization lift, BAS, Aggie Excess, or any scientific claim.

## Prerequisites

- POST-SUBTASK-172 exact preliminary event-chronology baseline ladder and immutable identities.
- POST-SUBTASK-177 exact earlier play/drive comparison run.
- POST-SUBTASK-183 exact dense development-only PIT feature identity and independent validation.
- Verified pre-change recovery checkpoint C:/BatteredAggieSyndrome.data/backups/POST-SUBTASK-184-PRECHANGE-20260811T125447Z.

## Hard Dependencies

- POST-SUBTASK-172
- POST-SUBTASK-177
- POST-SUBTASK-183

## Blocks

- None.

## Read / Inspect First

- None.

## Files Expected To Be Modified

- configs/preliminary_dense_play_drive_replay_contract.json
- tools/run_preliminary_play_drive_augmented.py
- tools/validate_preliminary_play_drive_augmented.py
- tests/test_preliminary_play_drive_augmented.py
- artifacts/pit/preliminary_dense_play_drive_replay_gate.json
- artifacts/jira_evidence/POST-SUBTASK-184.json
- jira/project/JIRA_TARGET_PROFILE.yaml

## Components Expected To Be Touched

- modeling
- pit-temporal
- validation-promotion

## Protected Files / Interfaces

- governance/PROTECTED_ACCEPTANCE_RULES.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv
- governance/THRESHOLD_PRECOMMITMENT_REGISTRY.csv
- configs/judging_rule_seal.json

## Expected Outputs / Artifacts

- configs/preliminary_dense_play_drive_replay_contract.json
- tools/run_preliminary_play_drive_augmented.py
- tools/validate_preliminary_play_drive_augmented.py
- tests/test_preliminary_play_drive_augmented.py
- artifacts/pit/preliminary_dense_play_drive_replay_gate.json
- artifacts/jira_evidence/POST-SUBTASK-184.json
- <external-data-root>/training/preliminary_dense_play_drive_replay/sha256/<dataset_identity>
- <external-data-root>/model_artifacts/preliminary_dense_play_drive_replay/sha256/<model_identity>
- <external-data-root>/forecast_snapshots/preliminary_dense_play_drive_replay/sha256/<forecast_identity>
- <external-data-root>/manifests/preliminary_dense_play_drive_replay/sha256/<run_identity>/run_manifest.json
- <external-data-root>/validation/POST-SUBTASK-184

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `TASK-036`
- Inherited from: TASK-036
- Resolution: `DIRECT_PLUS_INHERITED_DOMAIN_GATE`
- Effective counts: `{}`

## Acceptance Criteria

1. The immutable POST-SUBTASK-172 baseline ladder and POST-SUBTASK-177 play/drive replay remain unchanged and are consumed only through their pinned identities and manifests.
2. Only exact POST-SUBTASK-183 development-PIT identity 1bd6f4c6 is joined to the unchanged 2023-2025 target population by canonical game and team identity; no name-only merge or fabricated label is permitted.
3. Chronology remains closed to backcasting: 2023 is the frozen baseline fallback, 2024 fits only 2023 outcomes, and 2025 fits only 2023-2024 outcomes.
4. Cold starts and null feature cells remain explicit under fit-only median imputation with indicators; the extra feature game without a pinned target is excluded rather than labeled.
5. New artifacts compare against both the frozen baseline and POST-SUBTASK-177, preserve negative results, and remain PRELIMINARY_UNPROTECTED with no protected or production authority.
6. The external datasets, models, forecasts, manifest, metrics, and dispositions pass schema, provenance, PIT, leakage, numerical replay, and byte-identical deterministic rebuild validation.

## Definition of Done

1. A new immutable external dataset identity joins exact POST-SUBTASK-172 targets and splits to exact POST-SUBTASK-183 development-PIT features without rewriting any predecessor.
2. The complete preliminary baseline foundation remains pinned and the two play/drive stackers run with chronological fit windows, fit-only imputation, cold-start handling, serialization, prediction replay, calibration diagnostics, and per-season/slice metrics.
3. Paired comparisons against the frozen baseline and POST-SUBTASK-177 preserve improvement, degradation, and mixed results without changing thresholds to force adoption.
4. Independent validation and an isolated rebuild reproduce every accepted payload byte-for-byte; reconstructible staging/rebuild/superseded-run artifacts are cleaned where host policy permits or retained under an exact blocked cleanup finding without bypass.
5. Protected promotion remains closed and the approximately 2010-2025 historical-expansion workstream continues independently.

## Required Tests / Validation

- **NEW_AUTOMATED_TEST_REQUIRED** / `PIT_LEAKAGE` — `tests/test_preliminary_play_drive_augmented.py` — Dense input pinning, separate lineage, chronology, cold starts, target exclusion, and protected nonauthority remain deterministic.
- **END_TO_END** / `END_TO_END` — `artifacts/jira_evidence/POST-SUBTASK-184.json` — The joined dataset, models, predictions, metrics, hashes, numerical replay, and isolated byte-identical rebuild pass independent validation.

## Required Evidence

- Exact POST-SUBTASK-172, POST-SUBTASK-177, and POST-SUBTASK-183 input hashes plus new dataset, feature, target, split, model, forecast, run, code, config, and validation identities.
- Rows, games, seasons, feature counts, cold starts, missingness, exclusions, fit windows, leakage checks, per-season/slice metrics, and paired deltas.
- Deterministic rebuild, numerical model replay, cleanup, live Jira/GitHub integration, and explicit protected nonclaims.

## Completion Evidence Contract

```json
{}
```

## End-to-End Validation Requirement

Re-read the exact POST-SUBTASK-172 baseline manifest, POST-SUBTASK-177 comparison manifest, and POST-SUBTASK-183 feature payload; rebuild the separately lineaged matrix, targets, splits, models, predictions, metrics, manifest, and validation report; verify all identities, chronology, target exclusion, protected closure, model replay, and byte identity; then clean reconstructible output where permitted or preserve the exact host-policy limitation.

## Expected Maturity After Completion

`EMPIRICALLY_VALIDATED_PRELIMINARY_UNPROTECTED`

## Risk / Failure Conditions

- Any dense feature is backdated or used to fit an outcome at or after its target season.
- Any target event, future outcome, name-only identity, missing fact, label, or timestamp is fabricated.
- Any result is represented as protected, champion, production, forecast-publication, A&M-lift, BAS, Aggie Excess, or scientific authority.

## Stop Conditions

- Stop the affected artifact on input hash, identity, chronology, target overlap, schema, missingness, serialization, numerical replay, metric, or byte-rebuild failure.
- Quarantine only affected rows or model families and continue independently valid historical acquisition and baseline work.
- Do not weaken chronology, imputation, comparison, validation, or scientific boundaries merely to obtain improvement.

## Source References

- SRCREF-00069
- SRCREF-02049
- SRCREF-02050

## AI Context Notes

- This is a separately lineaged replay, not a mutation of POST-SUBTASK-172, POST-SUBTASK-177, or POST-SUBTASK-183.
- The dense profile summarizes exact 2010-2022 version-bound evidence but is known only by May 2023 and cannot be backcast into the 2010-2022 fit population.
- No OpenAI output or model-generated fact participates in features, labels, splits, timestamps, fitting, evaluation, or acceptance.

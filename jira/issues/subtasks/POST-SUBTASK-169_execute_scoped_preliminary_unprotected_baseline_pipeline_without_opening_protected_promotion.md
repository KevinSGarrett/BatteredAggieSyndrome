<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-169_execute_scoped_preliminary_unprotected_baseline_pipeline_without_opening_protected_promotion.json -->
# POST-SUBTASK-169 — [POST-SUBTASK-169] Execute scoped PRELIMINARY_UNPROTECTED baseline pipeline without opening protected promotion

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Every input identity matches the exact BAT-523 scoped replay and approved contemporary outcome payload; eligibility is not broadened.",
    "Feature, target, split, training, model, forecast, and run identities are immutable, reproducible, external-storage-only, and independently rehashed.",
    "The 2023/2024/2025 fit/tune/unprotected-evaluation chronology passes target-game, future-feature, duplicate, missing-label, and protected-split checks.",
    "All six simple baselines serialize and replay before histogram tree boosting is admitted.",
    "Every metric and conclusion is labeled PRELIMINARY_UNPROTECTED and all production/protected/A&M/BAS nonclaims remain false."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "This unit is complete only for the exact scoped preliminary lane; it does not alter protected Story dependencies.",
    "Use no OpenAI calls and never invent missing facts, labels, publication times, or features.",
    "Bulk training/model/forecast payloads remain outside Git under the configured data root."
  ],
  "blocked_reason": "",
  "blocks": [
    "POST-SUBTASK-171"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-169_execute_scoped_preliminary_unprotected_baseline_pipeline_without_opening_protected_promotion.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "classification": "PRELIMINARY_UNPROTECTED",
    "negative_results_preserved": true,
    "protected_nonclaims_required": true
  },
  "component": "modeling",
  "components_expected_to_be_touched": [
    "modeling",
    "experimentation",
    "provenance"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The immutable dataset contains separate feature, outcome-target, split-assignment, and joined training payloads with exact hashes.",
    "Naive, home-field, Elo, regularized logistic/linear, and Poisson/Skellam models train and replay; tree boosting runs only after the simple gate passes.",
    "Per-season and relevant-slice probability, calibration, and score diagnostics are preserved with missingness and exclusions.",
    "The independent validator passes artifact hashes, rows, classification, chronology, target isolation, bounded probabilities, model replay, and mutation controls.",
    "Protected promotion still depends on expanded quality-supported history and W17 validation; no champion is promoted."
  ],
  "dependencies": [
    "POST-SUBTASK-048",
    "POST-SUBTASK-049"
  ],
  "dependency_scope_contract": {
    "bat_398_eligible_dataset_identity": "cf732b78db6deff2e2cca51364a18e03219a5ceda88d2f5efa475dad1f7e3fe7",
    "bat_398_local_id": "POST-SUBTASK-048",
    "bat_398_replay_manifest_sha256": "7383dd69d4165d0e18f89ad690d155305e062d7f81ad9b0087233a90a044a888",
    "bat_399_authority": "SCOPED_PIPELINE_AND_LEAKAGE_REPLAY_ONLY",
    "bat_399_local_id": "POST-SUBTASK-049",
    "preliminary_lane_may_execute_before_expanded_history": true,
    "protected_downstream_dependency_satisfied_by_this_unit": false,
    "protected_downstream_requires_expanded_quality_supported_history": true
  },
  "end_to_end_validation": "Rebuild the same immutable training and forecast identities, independently rehash all payloads and models, replay serialized artifacts, and verify 2025 unprotected evaluation uses only 2023-2024 fitting and 2024 calibration evidence.",
  "epic_id": "POST-EPIC-008",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-169.json",
  "evidence_state": "VERIFIED",
  "execution_lane": "MODEL_RESEARCH",
  "execution_mode": "HISTORICAL_REFERENCE",
  "expected_maturity_after_completion": "EMPIRICALLY_VALIDATED_PRELIMINARY_UNPROTECTED",
  "expected_outputs": [
    "configs/preliminary_unprotected_baseline_contract.json",
    "artifacts/jira_evidence/POST-SUBTASK-169.json",
    "<external-data-root>/training/preliminary_unprotected/sha256/<dataset_identity>",
    "<external-data-root>/model_artifacts/preliminary_unprotected/sha256/<model_identity>",
    "<external-data-root>/forecast_snapshots/preliminary_unprotected/sha256/<forecast_identity>",
    "<external-data-root>/manifests/preliminary_unprotected/sha256/<run_identity>/run_manifest.json"
  ],
  "files_expected_to_be_read": [
    "artifacts/pit/historical_known_at_replay_gate.json",
    "configs/preliminary_unprotected_baseline_contract.json",
    "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "docs/60_W17_EXPERIMENT_BOUNDARIES_AND_W18_HANDOFF.md"
  ],
  "files_expected_to_be_touched": [
    "configs/preliminary_unprotected_baseline_contract.json",
    "src/aggie_analytics/modeling/preliminary.py",
    "tools/run_preliminary_unprotected_baselines.py",
    "tools/validate_preliminary_unprotected_baselines.py",
    "tests/test_preliminary_unprotected_baselines.py",
    "artifacts/jira_evidence/POST-SUBTASK-169.json"
  ],
  "gap_ids": [
    "GAP-003",
    "GAP-005"
  ],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-169_execute_scoped_preliminary_unprotected_baseline_pipeline_without_opening_protected_promotion.md",
  "governance_traceability_gate": "TASK-036",
  "historical_classification": "POST_W25_IMPLEMENTATION",
  "import_id": 100477,
  "in_scope": [
    "Exact replay dataset cf732b78db6deff2e2cca51364a18e03219a5ceda88d2f5efa475dad1f7e3fe7 only.",
    "2010-2022 team-outcome priors and 2023-2025 completed outcome targets only.",
    "Naive, home-field, Elo, regularized logistic/linear, Poisson/Skellam, and post-simple-gate histogram tree baselines.",
    "Development fit/tune/unprotected-evaluation chronology, missingness, cold starts, calibration diagnostics, serialization, replay, provenance, and cleanup."
  ],
  "issue_type": "Sub-task",
  "jira_key": "BAT-526",
  "labels": [
    "actionable",
    "post-wave",
    "subtask",
    "preliminary-unprotected",
    "baseline-modeling",
    "chronological-replay"
  ],
  "last_content_audit": "2026-08-10",
  "local_id": "POST-SUBTASK-169",
  "maturity_before": "CONTRACT_DEFINED",
  "objective": "Use only the exact BAT-398/BAT-399 scoped team-outcome replay and pinned contemporary completed outcomes to exercise a fully lineaged preliminary modeling pipeline while final historical expansion continues independently.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24666",
    "jira_updated_at": "2026-08-11T01:09:23.260-0500",
    "last_synced_at": "2026-08-11T06:30:01.758065+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\POST-SUBTASK-177-play-drive-preliminary\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "Done"
  },
  "out_of_scope": [
    "Any final historical-readiness or GAP-002 completion claim.",
    "Protected W17 evaluation, production promotion, champion selection, A&M specialization lift, BAS, Aggie Excess, or publication.",
    "Any play, drive, roster, ranking, venue, weather, gamebook, player, or advanced-stat candidate not separately admitted for training."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-025",
  "phase": "PHASE-1",
  "prerequisites": [
    "BAT-398 expanded scoped team-outcome approval recorded by the BAT-523 replay gate.",
    "BAT-399 scoped pipeline/leakage eligibility only, not production approval.",
    "Pinned contemporary completed-outcome payload SHA-256 1d8b52e0ed409b9d7648d2a8fa89cf1bb0be1e037d5aea92642cf555378ae06a."
  ],
  "primary_source_refs": [
    "SRCREF-00069",
    "SRCREF-02116",
    "SRCREF-02117"
  ],
  "priority": "P0",
  "protected_files_and_interfaces": [
    "AGENTS.md",
    "governance/DO_NOT_DRIFT.md",
    "governance/PROTECTED_ACCEPTANCE_RULES.md",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "governance/THRESHOLD_PRECOMMITMENT_REGISTRY.csv",
    "configs/judging_rule_seal.json",
    "docs/45_SCIENTIFIC_BAS_SPECIFICATION.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "required_evidence": [
    "Exact BAT-398/BAT-399 scoped input identities and hashes.",
    "Dataset, feature, target, split, model, forecast, and run identities with external paths and SHA-256 values.",
    "Season/game/row/feature/missingness/exclusion counts and chronological leakage results.",
    "Per-season and relevant-slice metrics with PRELIMINARY_UNPROTECTED classification and protected nonclaims.",
    "Deterministic rebuild, serialization replay, cleanup, focused/full tests, repository, provenance, and Jira validation."
  ],
  "required_tests": [
    {
      "classification": "NEW_AUTOMATED_TEST_REQUIRED",
      "expectation": "Synthetic feature pairing, cold start, imputation-fit boundary, leakage failure, Elo determinism, metric, and scoped-contract tests pass.",
      "path": "tests/test_preliminary_unprotected_baselines.py",
      "validation_class": "PIT_LEAKAGE"
    },
    {
      "classification": "END_TO_END",
      "expectation": "The external run manifest and every data/model/forecast artifact pass the independent preliminary validator.",
      "path": "artifacts/jira_evidence/POST-SUBTASK-169.json",
      "validation_class": "END_TO_END"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "Any target-game or future outcome appears in feature evidence.",
    "Any candidate-only historical domain is silently admitted as a feature.",
    "Any protected split, metric, promotion, champion, A&M lift, BAS, or Aggie Excess claim is opened.",
    "Any missing target or feature is fabricated rather than excluded, imputed by the declared training-only rule, or retained as missing."
  ],
  "risk_ids": [
    "RISK-227",
    "RISK-241",
    "RISK-242"
  ],
  "schema_version": 2,
  "scope": "Materialize separate feature, target, split, and training identities; train the simple baseline ladder; permit tree boosting only after the simple pipeline passes; persist and replay immutable external artifacts; and report preliminary metrics and negative findings without a champion or protected claim.",
  "source_ids": [
    "TASK-036",
    "GAP-003",
    "GAP-005"
  ],
  "source_refs": [
    "SRCREF-00069",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02049",
    "SRCREF-02050"
  ],
  "stop_conditions": [
    "Stop this lane if an input hash or approved scope drifts.",
    "Stop the affected model if chronology, serialization replay, or provenance validation fails; do not block independent historical acquisition.",
    "Do not use protected results to revise this preliminary pipeline."
  ],
  "supporting_source_refs": [
    "SRCREF-02049",
    "SRCREF-02050"
  ],
  "title": "[POST-SUBTASK-169] Execute scoped PRELIMINARY_UNPROTECTED baseline pipeline without opening protected promotion",
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
  "why_this_exists": "Final expanded-history and protected-promotion gates must remain binding without preventing an explicitly unprotected pipeline and baseline proof on the already approved scoped population.",
  "work_packet_path": "",
  "workflow_state": "DONE"
}
```

## Objective

Use only the exact BAT-398/BAT-399 scoped team-outcome replay and pinned contemporary completed outcomes to exercise a fully lineaged preliminary modeling pipeline while final historical expansion continues independently.

## Why This Exists

Final expanded-history and protected-promotion gates must remain binding without preventing an explicitly unprotected pipeline and baseline proof on the already approved scoped population.

## Scope

Materialize separate feature, target, split, and training identities; train the simple baseline ladder; permit tree boosting only after the simple pipeline passes; persist and replay immutable external artifacts; and report preliminary metrics and negative findings without a champion or protected claim.

### Explicit In Scope

- Exact replay dataset cf732b78db6deff2e2cca51364a18e03219a5ceda88d2f5efa475dad1f7e3fe7 only.
- 2010-2022 team-outcome priors and 2023-2025 completed outcome targets only.
- Naive, home-field, Elo, regularized logistic/linear, Poisson/Skellam, and post-simple-gate histogram tree baselines.
- Development fit/tune/unprotected-evaluation chronology, missingness, cold starts, calibration diagnostics, serialization, replay, provenance, and cleanup.

### Explicit Out of Scope

- Any final historical-readiness or GAP-002 completion claim.
- Protected W17 evaluation, production promotion, champion selection, A&M specialization lift, BAS, Aggie Excess, or publication.
- Any play, drive, roster, ranking, venue, weather, gamebook, player, or advanced-stat candidate not separately admitted for training.

## Prerequisites

- BAT-398 expanded scoped team-outcome approval recorded by the BAT-523 replay gate.
- BAT-399 scoped pipeline/leakage eligibility only, not production approval.
- Pinned contemporary completed-outcome payload SHA-256 1d8b52e0ed409b9d7648d2a8fa89cf1bb0be1e037d5aea92642cf555378ae06a.

## Hard Dependencies

- POST-SUBTASK-048
- POST-SUBTASK-049

## Blocks

- POST-SUBTASK-171

## Read / Inspect First

- None.

## Files Expected To Be Modified

- configs/preliminary_unprotected_baseline_contract.json
- src/aggie_analytics/modeling/preliminary.py
- tools/run_preliminary_unprotected_baselines.py
- tools/validate_preliminary_unprotected_baselines.py
- tests/test_preliminary_unprotected_baselines.py
- artifacts/jira_evidence/POST-SUBTASK-169.json

## Components Expected To Be Touched

- modeling
- experimentation
- provenance

## Protected Files / Interfaces

- AGENTS.md
- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_ACCEPTANCE_RULES.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv
- governance/THRESHOLD_PRECOMMITMENT_REGISTRY.csv
- configs/judging_rule_seal.json
- docs/45_SCIENTIFIC_BAS_SPECIFICATION.md

## Expected Outputs / Artifacts

- configs/preliminary_unprotected_baseline_contract.json
- artifacts/jira_evidence/POST-SUBTASK-169.json
- <external-data-root>/training/preliminary_unprotected/sha256/<dataset_identity>
- <external-data-root>/model_artifacts/preliminary_unprotected/sha256/<model_identity>
- <external-data-root>/forecast_snapshots/preliminary_unprotected/sha256/<forecast_identity>
- <external-data-root>/manifests/preliminary_unprotected/sha256/<run_identity>/run_manifest.json

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

1. Every input identity matches the exact BAT-523 scoped replay and approved contemporary outcome payload; eligibility is not broadened.
2. Feature, target, split, training, model, forecast, and run identities are immutable, reproducible, external-storage-only, and independently rehashed.
3. The 2023/2024/2025 fit/tune/unprotected-evaluation chronology passes target-game, future-feature, duplicate, missing-label, and protected-split checks.
4. All six simple baselines serialize and replay before histogram tree boosting is admitted.
5. Every metric and conclusion is labeled PRELIMINARY_UNPROTECTED and all production/protected/A&M/BAS nonclaims remain false.

## Definition of Done

1. The immutable dataset contains separate feature, outcome-target, split-assignment, and joined training payloads with exact hashes.
2. Naive, home-field, Elo, regularized logistic/linear, and Poisson/Skellam models train and replay; tree boosting runs only after the simple gate passes.
3. Per-season and relevant-slice probability, calibration, and score diagnostics are preserved with missingness and exclusions.
4. The independent validator passes artifact hashes, rows, classification, chronology, target isolation, bounded probabilities, model replay, and mutation controls.
5. Protected promotion still depends on expanded quality-supported history and W17 validation; no champion is promoted.

## Required Tests / Validation

- **NEW_AUTOMATED_TEST_REQUIRED** / `PIT_LEAKAGE` — `tests/test_preliminary_unprotected_baselines.py` — Synthetic feature pairing, cold start, imputation-fit boundary, leakage failure, Elo determinism, metric, and scoped-contract tests pass.
- **END_TO_END** / `END_TO_END` — `artifacts/jira_evidence/POST-SUBTASK-169.json` — The external run manifest and every data/model/forecast artifact pass the independent preliminary validator.

## Required Evidence

- Exact BAT-398/BAT-399 scoped input identities and hashes.
- Dataset, feature, target, split, model, forecast, and run identities with external paths and SHA-256 values.
- Season/game/row/feature/missingness/exclusion counts and chronological leakage results.
- Per-season and relevant-slice metrics with PRELIMINARY_UNPROTECTED classification and protected nonclaims.
- Deterministic rebuild, serialization replay, cleanup, focused/full tests, repository, provenance, and Jira validation.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "classification": "PRELIMINARY_UNPROTECTED",
  "negative_results_preserved": true,
  "protected_nonclaims_required": true
}
```

## End-to-End Validation Requirement

Rebuild the same immutable training and forecast identities, independently rehash all payloads and models, replay serialized artifacts, and verify 2025 unprotected evaluation uses only 2023-2024 fitting and 2024 calibration evidence.

## Expected Maturity After Completion

`EMPIRICALLY_VALIDATED_PRELIMINARY_UNPROTECTED`

## Risk / Failure Conditions

- Any target-game or future outcome appears in feature evidence.
- Any candidate-only historical domain is silently admitted as a feature.
- Any protected split, metric, promotion, champion, A&M lift, BAS, or Aggie Excess claim is opened.
- Any missing target or feature is fabricated rather than excluded, imputed by the declared training-only rule, or retained as missing.

## Stop Conditions

- Stop this lane if an input hash or approved scope drifts.
- Stop the affected model if chronology, serialization replay, or provenance validation fails; do not block independent historical acquisition.
- Do not use protected results to revise this preliminary pipeline.

## Source References

- SRCREF-00069
- SRCREF-02116
- SRCREF-02117
- SRCREF-02049
- SRCREF-02050

## AI Context Notes

- This unit is complete only for the exact scoped preliminary lane; it does not alter protected Story dependencies.
- Use no OpenAI calls and never invent missing facts, labels, publication times, or features.
- Bulk training/model/forecast payloads remain outside Git under the configured data root.

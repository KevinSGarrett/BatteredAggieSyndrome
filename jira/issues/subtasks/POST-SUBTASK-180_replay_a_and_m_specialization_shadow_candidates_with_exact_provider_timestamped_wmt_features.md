<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-180_replay_a_and_m_specialization_shadow_candidates_with_exact_provider_timestamped_wmt_features.json -->
# POST-SUBTASK-180 — Replay A&M specialization shadow candidates with exact provider-timestamped WMT features

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "The exact POST-SUBTASK-177 national reference run and POST-SUBTASK-179 WMT feature identity remain immutable pinned inputs and are not silently broadened.",
    "Exactly 39 canonical Texas A&M games, thirteen per 2023-2025 season, join by exact game/team/opponent identity with no name-only mapping, missing target fabrication, or protected input.",
    "Chronology is fixed: 2023 is an exact frozen fallback, 2024 fits only 2023 A&M outcomes, and 2025 fits only 2023-2024 A&M outcomes; no target-game, same-season, or future outcome enters fit.",
    "Only the four predeclared low-dimensional WMT signals and corresponding frozen national prediction enter strongly regularized logistic and ridge-margin shadow candidates; tree boosting is not admitted.",
    "All datasets, models, predictions, metrics, and conclusions remain PRELIMINARY_UNPROTECTED and cannot open protected evaluation, champion/production promotion, forecast publication, A&M lift, BAS, Aggie Excess, or scientific authority.",
    "Independent validation and isolated deterministic rebuild reproduce every content-addressed payload, model replay, identity, metric, disposition, and cleanup finding."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "This is the separately lineaged replay required by POST-SUBTASK-179 and does not mutate the frozen national reference.",
    "Thirty-nine A&M games are intentionally treated as a short shadow horizon; negative or unstable results are valid evidence and must be preserved.",
    "No OpenAI output or other model-generated fact may enter source evidence, features, labels, identities, timestamps, splits, or acceptance."
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-180_replay_a_and_m_specialization_shadow_candidates_with_exact_provider_timestamped_wmt_features.json",
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
    "A new immutable external training-dataset identity separately materializes feature, target, split, and joined training payloads without rewriting either source input.",
    "The complete shadow pipeline executes canonical joining, chronological assignments, fit-only transformation, strong regularization, prediction, probability/calibration and margin diagnostics, artifact serialization, replay, and provenance verification.",
    "The same-row frozen comparison reports positive, mixed, negative, or unstable results without post-hoc threshold changes; nonadoption is preserved when the candidate degrades the reference.",
    "All external payloads pass identity, schema, source cutoff, PIT, target-leakage, model replay, immutable hash, and deterministic rebuild validation; reconstructible staging and rebuild output are removed.",
    "Protected promotion remains closed and the approximately 2010-2025 historical expansion continues independently."
  ],
  "dependencies": [
    "POST-SUBTASK-177",
    "POST-SUBTASK-179"
  ],
  "end_to_end_validation": "Re-read exact POST-SUBTASK-177 reference predictions and POST-SUBTASK-179 WMT target-cutoff features; rebuild the 39-game feature/target/split population, chronological estimators, predictions, metrics, frozen comparisons, model artifacts, manifest, and identities; verify strict cutoff ordering, target exclusion, serialization replay, protected closure, byte-identical summary, and cleanup.",
  "epic_id": "POST-EPIC-008",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-180.json",
  "evidence_state": "VERIFIED",
  "execution_lane": "MODEL_RESEARCH",
  "execution_mode": "HISTORICAL_REFERENCE",
  "expected_maturity_after_completion": "EMPIRICALLY_VALIDATED_PRELIMINARY_UNPROTECTED",
  "expected_outputs": [
    "configs/preliminary_wmt_tamu_shadow_contract.json",
    "src/aggie_analytics/modeling/wmt_tamu_shadow.py",
    "tools/run_preliminary_wmt_tamu_shadow.py",
    "tools/validate_preliminary_wmt_tamu_shadow.py",
    "artifacts/pit/preliminary_wmt_tamu_shadow_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-180.json",
    "<external-data-root>/training/preliminary_wmt_tamu_shadow/sha256/<dataset_identity>",
    "<external-data-root>/model_artifacts/preliminary_wmt_tamu_shadow/sha256/<model_identity>",
    "<external-data-root>/forecast_snapshots/preliminary_wmt_tamu_shadow/sha256/<forecast_identity>",
    "<external-data-root>/manifests/preliminary_wmt_tamu_shadow/sha256/<run_identity>/run_manifest.json",
    "<external-data-root>/validation/POST-SUBTASK-180"
  ],
  "files_expected_to_be_read": [
    "configs/preliminary_play_drive_augmented_contract.json",
    "configs/wmt_tamu_specialization_feature_pit_contract.json",
    "artifacts/jira_evidence/POST-SUBTASK-177.json",
    "artifacts/jira_evidence/POST-SUBTASK-179.json"
  ],
  "files_expected_to_be_touched": [
    "configs/preliminary_wmt_tamu_shadow_contract.json",
    "configs/historical_known_at_recovery_contract.json",
    "src/aggie_analytics/modeling/wmt_tamu_shadow.py",
    "tools/run_preliminary_wmt_tamu_shadow.py",
    "tools/validate_preliminary_wmt_tamu_shadow.py",
    "tests/test_preliminary_wmt_tamu_shadow.py",
    "artifacts/pit/preliminary_wmt_tamu_shadow_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-180.json",
    "jira/project/JIRA_TARGET_PROFILE.yaml"
  ],
  "gap_ids": [
    "GAP-002",
    "GAP-003",
    "GAP-005"
  ],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-180_replay_a_and_m_specialization_shadow_candidates_with_exact_provider_timestamped_wmt_features.md",
  "governance_traceability_gate": "TASK-036",
  "historical_classification": "POST_W25_IMPLEMENTATION",
  "import_id": 100488,
  "in_scope": [
    "Exact canonical game/team/opponent joins for the 39-game 2023-2025 WMT A&M target-cutoff population.",
    "Chronological low-dimensional logistic and ridge-margin shadow fitting against the exact frozen national reference.",
    "Immutable external matrices/models/predictions/manifests, calibration and error diagnostics, negative-result preservation, deterministic replay, provenance, and cleanup."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-537",
  "labels": [
    "actionable",
    "post-wave",
    "subtask",
    "preliminary-unprotected",
    "tamu-specialization",
    "wmt",
    "baseline-modeling",
    "pit",
    "provenance"
  ],
  "last_content_audit": "2026-08-11",
  "local_id": "POST-SUBTASK-180",
  "maturity_before": "DEVELOPMENT_ONLY_PIT_FEATURE_CANDIDATE_ADMITTED",
  "objective": "Replay A&M specialization shadow candidates with the exact provider-timestamped WMT feature identity without opening protected promotion or overstating a 39-game result.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24927",
    "jira_updated_at": "2026-08-11T04:12:54.154-0500",
    "last_synced_at": "2026-08-11T09:12:54.154000+00:00",
    "source_export": "LIVE_REST_POST_SUBTASK_180_POSTMERGE_DONE_EVIDENCE",
    "sprint": "",
    "status_raw": "Done"
  },
  "out_of_scope": [
    "Broadening the exact 39-game WMT population, using non-pinned source records, adding opponent gamebook facts, or rewriting POST-SUBTASK-177/179 artifacts.",
    "Tree boosting, neural models, broad HPO, post-hoc feature selection, or favorable-threshold fabrication on the short A&M horizon.",
    "Protected evaluation, champion or production promotion, forecast publication, final historical readiness, A&M specialization lift, BAS, Aggie Excess, or any scientific claim."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-025",
  "phase": "PHASE-1",
  "prerequisites": [
    "POST-SUBTASK-177 exact frozen national reference predictions and immutable identities.",
    "POST-SUBTASK-179 exact provider-timestamped WMT A&M target-cutoff feature identity and independent validation.",
    "Configured standardized external data root and successful live Jira authentication."
  ],
  "primary_source_refs": [
    "SRCREF-02013",
    "SRCREF-02049",
    "SRCREF-02050"
  ],
  "priority": "P0",
  "protected_files_and_interfaces": [
    "governance/PROTECTED_ACCEPTANCE_RULES.md",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "governance/THRESHOLD_PRECOMMITMENT_REGISTRY.csv"
  ],
  "ready": false,
  "record_revision": "2.0",
  "required_evidence": [
    "Exact POST-SUBTASK-177 and POST-SUBTASK-179 input hashes plus new dataset, feature, target, split, model, forecast, run, code, config, validation, and rollback identities.",
    "Seasons, games, rows, feature count, exclusions, missingness, chronological cutoffs, fit windows, leakage checks, and probability/calibration/margin metrics by season.",
    "Frozen-reference deltas, empirical disposition, serialized model replay, byte-identical isolated rebuild summary, cleanup, and explicit protected nonclaims."
  ],
  "required_tests": [
    {
      "classification": "NEW_AUTOMATED_TEST_REQUIRED",
      "expectation": "Exact game/team orientation, cutoff ordering, walk-forward fit windows, feature precommitment, protected nonauthority, and metric behavior remain deterministic.",
      "path": "tests/test_preliminary_wmt_tamu_shadow.py",
      "validation_class": "PIT_LEAKAGE"
    },
    {
      "classification": "END_TO_END",
      "expectation": "External matrices, models, predictions, metrics, manifest, hashes, serialization replay, chronology, deterministic rebuild, cleanup, and protected closure pass independent validation.",
      "path": "artifacts/jira_evidence/POST-SUBTASK-180.json",
      "validation_class": "END_TO_END"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "Any source, feature, reference prediction, game/team/opponent, target, split, schema, population, timestamp, hash, or deterministic replay identity drifts.",
    "Any target-game, same-season, future outcome, post-cutoff source row, protected input, name-only merge, or fabricated value enters the replay.",
    "Any negative or unstable result is suppressed or represented as protected, champion, production, A&M lift, BAS, Aggie Excess, completeness, or scientific authority."
  ],
  "risk_ids": [
    "RISK-227",
    "RISK-241",
    "RISK-242"
  ],
  "schema_version": "2.0",
  "scope": "Build and independently validate one exact 39-game A&M shadow replay from the pinned WMT development-PIT feature candidate and frozen national reference.",
  "source_ids": [
    "TASK-036",
    "GAP-002",
    "GAP-003",
    "GAP-005"
  ],
  "source_refs": [
    "SRCREF-02013",
    "SRCREF-02049",
    "SRCREF-02050",
    "SRCREF-01889"
  ],
  "stop_conditions": [
    "Stop the affected artifact on input hash, identity, source cutoff, target overlap, chronology, schema, model replay, metric, immutable destination, or deterministic rebuild failure.",
    "Quarantine only affected rows or families and continue independently valid historical acquisition, baseline research, and OpenAI candidate assistance.",
    "Do not weaken feature scope, regularization, chronology, comparison, validation, or scientific boundaries to obtain apparent improvement."
  ],
  "supporting_source_refs": [
    "SRCREF-01889"
  ],
  "title": "Replay A&M specialization shadow candidates with exact provider-timestamped WMT features",
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
  "why_this_exists": "POST-SUBTASK-179 deliberately stopped at a feature candidate. This separate replay measures its incremental value honestly against the national reference without mutating either source identity or opening protected promotion.",
  "work_packet_path": "",
  "workflow_state": "DONE"
}
```

## Objective

Replay A&M specialization shadow candidates with the exact provider-timestamped WMT feature identity without opening protected promotion or overstating a 39-game result.

## Why This Exists

POST-SUBTASK-179 deliberately stopped at a feature candidate. This separate replay measures its incremental value honestly against the national reference without mutating either source identity or opening protected promotion.

## Scope

Build and independently validate one exact 39-game A&M shadow replay from the pinned WMT development-PIT feature candidate and frozen national reference.

### Explicit In Scope

- Exact canonical game/team/opponent joins for the 39-game 2023-2025 WMT A&M target-cutoff population.
- Chronological low-dimensional logistic and ridge-margin shadow fitting against the exact frozen national reference.
- Immutable external matrices/models/predictions/manifests, calibration and error diagnostics, negative-result preservation, deterministic replay, provenance, and cleanup.

### Explicit Out of Scope

- Broadening the exact 39-game WMT population, using non-pinned source records, adding opponent gamebook facts, or rewriting POST-SUBTASK-177/179 artifacts.
- Tree boosting, neural models, broad HPO, post-hoc feature selection, or favorable-threshold fabrication on the short A&M horizon.
- Protected evaluation, champion or production promotion, forecast publication, final historical readiness, A&M specialization lift, BAS, Aggie Excess, or any scientific claim.

## Prerequisites

- POST-SUBTASK-177 exact frozen national reference predictions and immutable identities.
- POST-SUBTASK-179 exact provider-timestamped WMT A&M target-cutoff feature identity and independent validation.
- Configured standardized external data root and successful live Jira authentication.

## Hard Dependencies

- POST-SUBTASK-177
- POST-SUBTASK-179

## Blocks

- None.

## Read / Inspect First

- None.

## Files Expected To Be Modified

- configs/preliminary_wmt_tamu_shadow_contract.json
- configs/historical_known_at_recovery_contract.json
- src/aggie_analytics/modeling/wmt_tamu_shadow.py
- tools/run_preliminary_wmt_tamu_shadow.py
- tools/validate_preliminary_wmt_tamu_shadow.py
- tests/test_preliminary_wmt_tamu_shadow.py
- artifacts/pit/preliminary_wmt_tamu_shadow_gate.json
- artifacts/jira_evidence/POST-SUBTASK-180.json
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

## Expected Outputs / Artifacts

- configs/preliminary_wmt_tamu_shadow_contract.json
- src/aggie_analytics/modeling/wmt_tamu_shadow.py
- tools/run_preliminary_wmt_tamu_shadow.py
- tools/validate_preliminary_wmt_tamu_shadow.py
- artifacts/pit/preliminary_wmt_tamu_shadow_gate.json
- artifacts/jira_evidence/POST-SUBTASK-180.json
- <external-data-root>/training/preliminary_wmt_tamu_shadow/sha256/<dataset_identity>
- <external-data-root>/model_artifacts/preliminary_wmt_tamu_shadow/sha256/<model_identity>
- <external-data-root>/forecast_snapshots/preliminary_wmt_tamu_shadow/sha256/<forecast_identity>
- <external-data-root>/manifests/preliminary_wmt_tamu_shadow/sha256/<run_identity>/run_manifest.json
- <external-data-root>/validation/POST-SUBTASK-180

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

1. The exact POST-SUBTASK-177 national reference run and POST-SUBTASK-179 WMT feature identity remain immutable pinned inputs and are not silently broadened.
2. Exactly 39 canonical Texas A&M games, thirteen per 2023-2025 season, join by exact game/team/opponent identity with no name-only mapping, missing target fabrication, or protected input.
3. Chronology is fixed: 2023 is an exact frozen fallback, 2024 fits only 2023 A&M outcomes, and 2025 fits only 2023-2024 A&M outcomes; no target-game, same-season, or future outcome enters fit.
4. Only the four predeclared low-dimensional WMT signals and corresponding frozen national prediction enter strongly regularized logistic and ridge-margin shadow candidates; tree boosting is not admitted.
5. All datasets, models, predictions, metrics, and conclusions remain PRELIMINARY_UNPROTECTED and cannot open protected evaluation, champion/production promotion, forecast publication, A&M lift, BAS, Aggie Excess, or scientific authority.
6. Independent validation and isolated deterministic rebuild reproduce every content-addressed payload, model replay, identity, metric, disposition, and cleanup finding.

## Definition of Done

1. A new immutable external training-dataset identity separately materializes feature, target, split, and joined training payloads without rewriting either source input.
2. The complete shadow pipeline executes canonical joining, chronological assignments, fit-only transformation, strong regularization, prediction, probability/calibration and margin diagnostics, artifact serialization, replay, and provenance verification.
3. The same-row frozen comparison reports positive, mixed, negative, or unstable results without post-hoc threshold changes; nonadoption is preserved when the candidate degrades the reference.
4. All external payloads pass identity, schema, source cutoff, PIT, target-leakage, model replay, immutable hash, and deterministic rebuild validation; reconstructible staging and rebuild output are removed.
5. Protected promotion remains closed and the approximately 2010-2025 historical expansion continues independently.

## Required Tests / Validation

- **NEW_AUTOMATED_TEST_REQUIRED** / `PIT_LEAKAGE` — `tests/test_preliminary_wmt_tamu_shadow.py` — Exact game/team orientation, cutoff ordering, walk-forward fit windows, feature precommitment, protected nonauthority, and metric behavior remain deterministic.
- **END_TO_END** / `END_TO_END` — `artifacts/jira_evidence/POST-SUBTASK-180.json` — External matrices, models, predictions, metrics, manifest, hashes, serialization replay, chronology, deterministic rebuild, cleanup, and protected closure pass independent validation.

## Required Evidence

- Exact POST-SUBTASK-177 and POST-SUBTASK-179 input hashes plus new dataset, feature, target, split, model, forecast, run, code, config, validation, and rollback identities.
- Seasons, games, rows, feature count, exclusions, missingness, chronological cutoffs, fit windows, leakage checks, and probability/calibration/margin metrics by season.
- Frozen-reference deltas, empirical disposition, serialized model replay, byte-identical isolated rebuild summary, cleanup, and explicit protected nonclaims.

## Completion Evidence Contract

```json
{}
```

## End-to-End Validation Requirement

Re-read exact POST-SUBTASK-177 reference predictions and POST-SUBTASK-179 WMT target-cutoff features; rebuild the 39-game feature/target/split population, chronological estimators, predictions, metrics, frozen comparisons, model artifacts, manifest, and identities; verify strict cutoff ordering, target exclusion, serialization replay, protected closure, byte-identical summary, and cleanup.

## Expected Maturity After Completion

`EMPIRICALLY_VALIDATED_PRELIMINARY_UNPROTECTED`

## Risk / Failure Conditions

- Any source, feature, reference prediction, game/team/opponent, target, split, schema, population, timestamp, hash, or deterministic replay identity drifts.
- Any target-game, same-season, future outcome, post-cutoff source row, protected input, name-only merge, or fabricated value enters the replay.
- Any negative or unstable result is suppressed or represented as protected, champion, production, A&M lift, BAS, Aggie Excess, completeness, or scientific authority.

## Stop Conditions

- Stop the affected artifact on input hash, identity, source cutoff, target overlap, chronology, schema, model replay, metric, immutable destination, or deterministic rebuild failure.
- Quarantine only affected rows or families and continue independently valid historical acquisition, baseline research, and OpenAI candidate assistance.
- Do not weaken feature scope, regularization, chronology, comparison, validation, or scientific boundaries to obtain apparent improvement.

## Source References

- SRCREF-02013
- SRCREF-02049
- SRCREF-02050
- SRCREF-01889

## AI Context Notes

- This is the separately lineaged replay required by POST-SUBTASK-179 and does not mutate the frozen national reference.
- Thirty-nine A&M games are intentionally treated as a short shadow horizon; negative or unstable results are valid evidence and must be preserved.
- No OpenAI output or other model-generated fact may enter source evidence, features, labels, identities, timestamps, splits, or acceptance.

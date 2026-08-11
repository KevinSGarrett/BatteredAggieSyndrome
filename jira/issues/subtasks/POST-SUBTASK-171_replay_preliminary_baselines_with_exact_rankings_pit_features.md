<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-171_replay_preliminary_baselines_with_exact_rankings_pit_features.json -->
# POST-SUBTASK-171 — [POST-SUBTASK-171] Replay preliminary baselines with exact rankings PIT features

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "The exact POST-SUBTASK-169 target rows and splits are retained and only POST-SUBTASK-170 rankings PIT features are added.",
    "Missing numeric ranks remain missing and use fit-only imputation with explicit evidence indicators.",
    "The same model ladder is replayed and paired 2025 metrics are compared without champion or protected authority.",
    "All external payloads rebuild to identical content-addressed identities and pass independent leakage/provenance validation."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "This unit is PRELIMINARY_UNPROTECTED only.",
    "No OpenAI facts or imputed source values are permitted."
  ],
  "blocked_reason": "",
  "blocks": [
    "POST-SUBTASK-172"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-171_replay_preliminary_baselines_with_exact_rankings_pit_features.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "component": "modeling",
  "components_expected_to_be_touched": [
    "modeling",
    "features",
    "provenance"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "Exact row/split identity is preserved.",
    "Sparse rankings features and missingness are lineaged.",
    "All seven models serialize and replay.",
    "Paired metrics and limitations are reported.",
    "Protected promotion remains closed."
  ],
  "dependencies": [
    "POST-SUBTASK-169",
    "POST-SUBTASK-170"
  ],
  "end_to_end_validation": "Rebuild dataset, models, predictions, manifest, and paired metrics in a separate external root and independently verify hashes, rows, chronology, missingness, target isolation, and protected closure.",
  "epic_id": "POST-EPIC-008",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-171.json",
  "evidence_state": "VERIFIED",
  "execution_lane": "MODEL_RESEARCH",
  "execution_mode": "HISTORICAL_REFERENCE",
  "expected_maturity_after_completion": "EMPIRICALLY_VALIDATED_PRELIMINARY_UNPROTECTED",
  "expected_outputs": [
    "configs/preliminary_rankings_augmented_contract.json",
    "artifacts/jira_evidence/POST-SUBTASK-171.json",
    "<external-data-root>/training/preliminary_unprotected/sha256/<dataset_identity>",
    "<external-data-root>/model_artifacts/preliminary_unprotected/sha256/<model_identity>",
    "<external-data-root>/forecast_snapshots/preliminary_unprotected/sha256/<forecast_identity>"
  ],
  "files_expected_to_be_read": [
    "configs/preliminary_unprotected_baseline_contract.json",
    "configs/historical_rankings_pit_contract.json",
    "governance/PROTECTED_SPLIT_REGISTRY.csv"
  ],
  "files_expected_to_be_touched": [
    "configs/preliminary_rankings_augmented_contract.json",
    "src/aggie_analytics/modeling/preliminary_rankings.py",
    "tools/run_preliminary_rankings_augmented_baselines.py",
    "tools/validate_preliminary_rankings_augmented_baselines.py",
    "tests/test_preliminary_rankings_augmented_contract.py",
    "artifacts/jira_evidence/POST-SUBTASK-171.json"
  ],
  "gap_ids": [
    "GAP-003",
    "GAP-005"
  ],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-171_replay_preliminary_baselines_with_exact_rankings_pit_features.md",
  "governance_traceability_gate": "TASK-036",
  "historical_classification": "POST_W25_IMPLEMENTATION",
  "import_id": 100479,
  "in_scope": [
    "Exact POST-SUBTASK-169 rows and splits.",
    "Exact POST-SUBTASK-170 rankings feature identity.",
    "Same seven-model ladder and paired preliminary metrics."
  ],
  "issue_type": "Sub-task",
  "jira_key": "BAT-528",
  "labels": [
    "actionable",
    "post-wave",
    "subtask",
    "preliminary-unprotected",
    "rankings",
    "baseline-modeling"
  ],
  "last_content_audit": "2026-08-11",
  "local_id": "POST-SUBTASK-171",
  "maturity_before": "CONTRACT_DEFINED",
  "objective": "Measure the incremental preliminary value of the exact admitted rankings PIT domain on the unchanged baseline population without opening protected promotion.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24668",
    "jira_updated_at": "2026-08-11T01:09:24.593-0500",
    "last_synced_at": "2026-08-11T07:44:24.297472+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\BAT-523-tamu-availability-pages\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "Done"
  },
  "out_of_scope": [
    "Protected evaluation or champion promotion.",
    "Any broader historical population or non-admitted domain.",
    "Any fabricated unranked value or publication timestamp."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-025",
  "phase": "PHASE-1",
  "prerequisites": [
    "POST-SUBTASK-169 immutable baseline run.",
    "POST-SUBTASK-170 exact rankings PIT feature admission."
  ],
  "primary_source_refs": [
    "SRCREF-02049",
    "SRCREF-02050"
  ],
  "priority": "P0",
  "protected_files_and_interfaces": [
    "governance/DO_NOT_DRIFT.md",
    "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv"
  ],
  "ready": false,
  "record_revision": "2.0",
  "required_evidence": [
    "Exact input/output identities and hashes.",
    "Rows, seasons, features, missingness, exclusions, and leakage checks.",
    "Paired model metrics and negative findings.",
    "Deterministic rebuild and complete validation."
  ],
  "required_tests": [
    {
      "classification": "NEW_AUTOMATED_TEST_REQUIRED",
      "expectation": "Exact scope, missing rank, future evidence, and protected nonclaim tests pass.",
      "path": "tests/test_preliminary_rankings_augmented_contract.py",
      "validation_class": "PIT_LEAKAGE"
    },
    {
      "classification": "END_TO_END",
      "expectation": "External artifacts pass independent validation and deterministic rebuild.",
      "path": "artifacts/jira_evidence/POST-SUBTASK-171.json",
      "validation_class": "END_TO_END"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "Target rows or splits differ from POST-SUBTASK-169.",
    "Future rankings evidence or fabricated numeric ranks enter features.",
    "Preliminary metrics are treated as protected or promotional."
  ],
  "risk_ids": [
    "RISK-227",
    "RISK-241",
    "RISK-242"
  ],
  "schema_version": 2,
  "scope": "Join exact rankings PIT features, replay the unchanged ladder, preserve immutable artifacts, and compare paired preliminary metrics.",
  "source_ids": [
    "TASK-036",
    "GAP-003",
    "GAP-005"
  ],
  "source_refs": [
    "SRCREF-02049",
    "SRCREF-02050"
  ],
  "stop_conditions": [
    "Stop on input identity drift, row/split drift, chronology failure, or deterministic rebuild mismatch."
  ],
  "supporting_source_refs": [],
  "title": "[POST-SUBTASK-171] Replay preliminary baselines with exact rankings PIT features",
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
  "why_this_exists": "Newly admitted historical domains must supersede preliminary artifacts through measured replay rather than narrative assumption.",
  "work_packet_path": "",
  "workflow_state": "DONE"
}
```

## Objective

Measure the incremental preliminary value of the exact admitted rankings PIT domain on the unchanged baseline population without opening protected promotion.

## Why This Exists

Newly admitted historical domains must supersede preliminary artifacts through measured replay rather than narrative assumption.

## Scope

Join exact rankings PIT features, replay the unchanged ladder, preserve immutable artifacts, and compare paired preliminary metrics.

### Explicit In Scope

- Exact POST-SUBTASK-169 rows and splits.
- Exact POST-SUBTASK-170 rankings feature identity.
- Same seven-model ladder and paired preliminary metrics.

### Explicit Out of Scope

- Protected evaluation or champion promotion.
- Any broader historical population or non-admitted domain.
- Any fabricated unranked value or publication timestamp.

## Prerequisites

- POST-SUBTASK-169 immutable baseline run.
- POST-SUBTASK-170 exact rankings PIT feature admission.

## Hard Dependencies

- POST-SUBTASK-169
- POST-SUBTASK-170

## Blocks

- POST-SUBTASK-172

## Read / Inspect First

- None.

## Files Expected To Be Modified

- configs/preliminary_rankings_augmented_contract.json
- src/aggie_analytics/modeling/preliminary_rankings.py
- tools/run_preliminary_rankings_augmented_baselines.py
- tools/validate_preliminary_rankings_augmented_baselines.py
- tests/test_preliminary_rankings_augmented_contract.py
- artifacts/jira_evidence/POST-SUBTASK-171.json

## Components Expected To Be Touched

- modeling
- features
- provenance

## Protected Files / Interfaces

- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_SPLIT_REGISTRY.csv
- governance/PROTECTED_JUDGING_RULE_SEAL.csv

## Expected Outputs / Artifacts

- configs/preliminary_rankings_augmented_contract.json
- artifacts/jira_evidence/POST-SUBTASK-171.json
- <external-data-root>/training/preliminary_unprotected/sha256/<dataset_identity>
- <external-data-root>/model_artifacts/preliminary_unprotected/sha256/<model_identity>
- <external-data-root>/forecast_snapshots/preliminary_unprotected/sha256/<forecast_identity>

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

1. The exact POST-SUBTASK-169 target rows and splits are retained and only POST-SUBTASK-170 rankings PIT features are added.
2. Missing numeric ranks remain missing and use fit-only imputation with explicit evidence indicators.
3. The same model ladder is replayed and paired 2025 metrics are compared without champion or protected authority.
4. All external payloads rebuild to identical content-addressed identities and pass independent leakage/provenance validation.

## Definition of Done

1. Exact row/split identity is preserved.
2. Sparse rankings features and missingness are lineaged.
3. All seven models serialize and replay.
4. Paired metrics and limitations are reported.
5. Protected promotion remains closed.

## Required Tests / Validation

- **NEW_AUTOMATED_TEST_REQUIRED** / `PIT_LEAKAGE` — `tests/test_preliminary_rankings_augmented_contract.py` — Exact scope, missing rank, future evidence, and protected nonclaim tests pass.
- **END_TO_END** / `END_TO_END` — `artifacts/jira_evidence/POST-SUBTASK-171.json` — External artifacts pass independent validation and deterministic rebuild.

## Required Evidence

- Exact input/output identities and hashes.
- Rows, seasons, features, missingness, exclusions, and leakage checks.
- Paired model metrics and negative findings.
- Deterministic rebuild and complete validation.

## Completion Evidence Contract

```json
{}
```

## End-to-End Validation Requirement

Rebuild dataset, models, predictions, manifest, and paired metrics in a separate external root and independently verify hashes, rows, chronology, missingness, target isolation, and protected closure.

## Expected Maturity After Completion

`EMPIRICALLY_VALIDATED_PRELIMINARY_UNPROTECTED`

## Risk / Failure Conditions

- Target rows or splits differ from POST-SUBTASK-169.
- Future rankings evidence or fabricated numeric ranks enter features.
- Preliminary metrics are treated as protected or promotional.

## Stop Conditions

- Stop on input identity drift, row/split drift, chronology failure, or deterministic rebuild mismatch.

## Source References

- SRCREF-02049
- SRCREF-02050

## AI Context Notes

- This unit is PRELIMINARY_UNPROTECTED only.
- No OpenAI facts or imputed source values are permitted.

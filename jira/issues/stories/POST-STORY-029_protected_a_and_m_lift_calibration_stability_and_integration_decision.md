<!-- GENERATED VIEW. Canonical record: jira/records/issues/stories/POST-STORY-029_protected_a_and_m_lift_calibration_stability_and_integration_decision.json -->
# POST-STORY-029 — [POST-STORY-029] Protected A&M lift, calibration, stability, and integration decision

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Sealed candidates receive identical games, cutoffs, state, missingness, metrics, and no post-hoc changes; partial failures preserve evidence without feeding outcomes back to tuning.",
    "The declared output `artifacts/tamu/tamu_protected_predictions.parquet` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "Evaluation reports confidence/sample/segments and accepts null, negative, unstable, or harmful results without subgroup shopping, relabeling, or unsupported causal claims.",
    "The declared output `artifacts/tamu/tamu_protected_evaluation.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The signed decision admits only bounded supported specialization or selects global-only/no adjustment, updates model/product semantics, preserves rejected evidence, and closes GAP-009 only empirically.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Open only this Story, its selected child, and referenced source sections; do not load the entire Jira pack.",
    "Story completion requires the gate Subtask, not only implementation children."
  ],
  "allowed_modification_paths": [
    "artifacts/jira_evidence/POST-STORY-029.json"
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/stories/POST-STORY-029_protected_a_and_m_lift_calibration_stability_and_integration_decision.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "all_child_evidence_required": true,
    "child_gate": "POST-SUBTASK-087",
    "governance_traceability_gate": "POST-SUBTASK-087",
    "integrated_proof_required": true
  },
  "component": "tamu-specialization",
  "components_expected_to_be_touched": [
    "tamu-specialization",
    "tamu"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "All child subtasks POST-SUBTASK-085, POST-SUBTASK-086, POST-SUBTASK-087 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.",
    "The final gate `POST-SUBTASK-087` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.",
    "All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.",
    "The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.",
    "Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation."
  ],
  "dependencies": [
    "POST-SUBTASK-084",
    "POST-SUBTASK-102"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 9,
    "adr_ids": 9,
    "gap_ids": 1,
    "requirement_ids": 42,
    "risk_ids": 7
  },
  "effective_traceability_total": 68,
  "end_to_end_validation": "An identical sealed replay yields an auditable A&M-specialization-or-no-adjustment decision consumed by the production forecast.",
  "epic_id": "POST-EPIC-009",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-STORY-029.json",
  "evidence_state": "PLANNED",
  "execution_lane": "SHARED_CONTRACT",
  "execution_mode": "AGGREGATE_GATE",
  "expected_maturity_after_completion": "INTEGRATED",
  "expected_outputs": [
    "artifacts/tamu/tamu_protected_predictions.parquet",
    "artifacts/tamu/tamu_protected_evaluation.json",
    "artifacts/tamu/tamu_specialization_decision.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_tamu_specialization_governance.py",
    "src/aggie_analytics/tamu/specialization.py",
    "src/aggie_analytics/tamu/state.py",
    "docs/40_TEXAS_AM_SPECIALIZATION_ARCHITECTURE.md",
    "docs/41_TAMU_HIGH_RESOLUTION_STATE.md",
    "docs/42_TAMU_PEERS_ANALOGS_AND_SNAPSHOTS.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_tamu_specialization_governance.py",
    "src/aggie_analytics/tamu/specialization.py",
    "src/aggie_analytics/tamu/state.py",
    "docs/40_TEXAS_AM_SPECIALIZATION_ARCHITECTURE.md",
    "docs/41_TAMU_HIGH_RESOLUTION_STATE.md",
    "docs/42_TAMU_PEERS_ANALOGS_AND_SNAPSHOTS.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/stories/POST-STORY-029_protected_a_and_m_lift_calibration_stability_and_integration_decision.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-087",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100079,
  "in_scope": [
    "Complete and verify child `POST-SUBTASK-085` — Generate sealed global-only and A&M candidate predictions inside identical protected chronological replay.",
    "Complete and verify child `POST-SUBTASK-086` — Measure incremental accuracy, calibration, stability, uncertainty, data-quality sensitivity, and multiple-comparison context.",
    "Complete and verify child `POST-SUBTASK-087` — Publish the protected A&M specialization admission or no-adjustment decision and integrate it consistently.",
    "Integrate the child outputs and execute final gate `POST-SUBTASK-087`.",
    "Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence."
  ],
  "issue_type": "Story",
  "jira_key": "BAT-79",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "story",
    "tamu"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-STORY-029",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Determine whether specialization genuinely improves forecasts and preserve a no-lift result.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24219",
    "jira_updated_at": "2026-08-09T23:23:57.014-0500",
    "last_synced_at": "2026-08-11T06:07:11.607568+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\JIRA-LIVE-CATCHUP-20260811\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Work assigned to sibling Stories or another Epic.",
    "Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.",
    "Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-EPIC-009",
  "phase": "PHASE-3",
  "prerequisites": [
    "Hard dependency POST-SUBTASK-084",
    "Hard dependency POST-SUBTASK-102"
  ],
  "primary_source_refs": [
    "SRCREF-02057",
    "SRCREF-02058",
    "SRCREF-02059",
    "SRCREF-02060"
  ],
  "priority": "P1",
  "protected_change_required": false,
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
  "read_only_context_paths": [
    "AGENTS.md",
    "governance/DO_NOT_DRIFT.md",
    "governance/PROTECTED_ACCEPTANCE_RULES.md",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "governance/THRESHOLD_PRECOMMITMENT_REGISTRY.csv",
    "configs/judging_rule_seal.json",
    "docs/45_SCIENTIFIC_BAS_SPECIFICATION.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_tamu_specialization_governance.py",
    "src/aggie_analytics/tamu/specialization.py",
    "src/aggie_analytics/tamu/state.py",
    "docs/40_TEXAS_AM_SPECIALIZATION_ARCHITECTURE.md",
    "docs/41_TAMU_HIGH_RESOLUTION_STATE.md",
    "docs/42_TAMU_PEERS_ANALOGS_AND_SNAPSHOTS.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "Verified child completion/evidence manifests for POST-SUBTASK-085, POST-SUBTASK-086, POST-SUBTASK-087.",
    "Final gate decision from `POST-SUBTASK-087` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.",
    "Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_tamu_specialization_governance.py"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_w20_model_starter.py"
    },
    {
      "classification": "END_TO_END",
      "expectation": "The final child gate `POST-SUBTASK-087` must prove the integrated Story outcome and downstream-consumable output.",
      "path": "POST-SUBTASK-087",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "REPRODUCIBILITY",
      "expectation": "Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.",
      "path": "STORY_EVIDENCE_MANIFEST",
      "validation_class": "REPRODUCIBILITY"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "Parallel child outputs may use inconsistent source or schema identities",
    "Gate task may be bypassed after implementation tasks finish"
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Deliver Story POST-STORY-029 (Protected A&M lift, calibration, stability, and integration decision) as one coherent, gated capability inside Epic POST-EPIC-009. Execute child subtasks POST-SUBTASK-085, POST-SUBTASK-086, POST-SUBTASK-087 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-087` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.",
  "source_ids": [
    "GAP-009",
    "HANDOFF-007"
  ],
  "source_refs": [
    "SRCREF-02057",
    "SRCREF-02058",
    "SRCREF-02059",
    "SRCREF-02060",
    "SRCREF-02061",
    "SRCREF-02062",
    "SRCREF-02063",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01893",
    "SRCREF-01571"
  ],
  "specificity_fingerprint": "a582f7c98a131f0ca13aec1cdb0855038e51888d19a156147d70f8a8fb22ef07",
  "stop_conditions": [
    "Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs."
  ],
  "supporting_source_refs": [
    "SRCREF-02061",
    "SRCREF-02062",
    "SRCREF-02063",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01893",
    "SRCREF-01571"
  ],
  "title": "[POST-STORY-029] Protected A&M lift, calibration, stability, and integration decision",
  "traceability_inherited_from": [
    "POST-SUBTASK-087"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "END_TO_END",
    "EXISTING_AUTOMATED_TEST",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "This coherent capability closes a defined portion of Texas A&M high-resolution specialization and no-lift-safe evaluation and creates a verifiable output for the next dependency stage.",
  "work_packet_path": "jira/ai/work_packets/POST-STORY-029.md",
  "workflow_state": "BACKLOG"
}
```

## Objective

Determine whether specialization genuinely improves forecasts and preserve a no-lift result.

## Why This Exists

This coherent capability closes a defined portion of Texas A&M high-resolution specialization and no-lift-safe evaluation and creates a verifiable output for the next dependency stage.

## Scope

Deliver Story POST-STORY-029 (Protected A&M lift, calibration, stability, and integration decision) as one coherent, gated capability inside Epic POST-EPIC-009. Execute child subtasks POST-SUBTASK-085, POST-SUBTASK-086, POST-SUBTASK-087 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-087` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### Explicit In Scope

- Complete and verify child `POST-SUBTASK-085` — Generate sealed global-only and A&M candidate predictions inside identical protected chronological replay.
- Complete and verify child `POST-SUBTASK-086` — Measure incremental accuracy, calibration, stability, uncertainty, data-quality sensitivity, and multiple-comparison context.
- Complete and verify child `POST-SUBTASK-087` — Publish the protected A&M specialization admission or no-adjustment decision and integrate it consistently.
- Integrate the child outputs and execute final gate `POST-SUBTASK-087`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Explicit Out of Scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

## Prerequisites

- Hard dependency POST-SUBTASK-084
- Hard dependency POST-SUBTASK-102

## Hard Dependencies

- POST-SUBTASK-084
- POST-SUBTASK-102

## Blocks

- None.

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_tamu_specialization_governance.py
- src/aggie_analytics/tamu/specialization.py
- src/aggie_analytics/tamu/state.py
- docs/40_TEXAS_AM_SPECIALIZATION_ARCHITECTURE.md
- docs/41_TAMU_HIGH_RESOLUTION_STATE.md
- docs/42_TAMU_PEERS_ANALOGS_AND_SNAPSHOTS.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- tamu-specialization
- tamu

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

- artifacts/tamu/tamu_protected_predictions.parquet
- artifacts/tamu/tamu_protected_evaluation.json
- artifacts/tamu/tamu_specialization_decision.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-087`
- Inherited from: POST-SUBTASK-087
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 9, "adr_ids": 9, "gap_ids": 1, "requirement_ids": 42, "risk_ids": 7}`

## Acceptance Criteria

1. Sealed candidates receive identical games, cutoffs, state, missingness, metrics, and no post-hoc changes; partial failures preserve evidence without feeding outcomes back to tuning.
2. The declared output `artifacts/tamu/tamu_protected_predictions.parquet` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
4. Evaluation reports confidence/sample/segments and accepts null, negative, unstable, or harmful results without subgroup shopping, relabeling, or unsupported causal claims.
5. The declared output `artifacts/tamu/tamu_protected_evaluation.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
6. The signed decision admits only bounded supported specialization or selects global-only/no adjustment, updates model/product semantics, preserves rejected evidence, and closes GAP-009 only empirically.
7. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. All child subtasks POST-SUBTASK-085, POST-SUBTASK-086, POST-SUBTASK-087 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.
2. The final gate `POST-SUBTASK-087` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.
3. All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.
4. The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.
5. Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_tamu_specialization_governance.py` — Run and retain the result when this issue touches the covered contract.
- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_w20_model_starter.py` — Run and retain the result when this issue touches the covered contract.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-087` — The final child gate `POST-SUBTASK-087` must prove the integrated Story outcome and downstream-consumable output.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `STORY_EVIDENCE_MANIFEST` — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Required Evidence

- Verified child completion/evidence manifests for POST-SUBTASK-085, POST-SUBTASK-086, POST-SUBTASK-087.
- Final gate decision from `POST-SUBTASK-087` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## Completion Evidence Contract

```json
{
  "all_child_evidence_required": true,
  "child_gate": "POST-SUBTASK-087",
  "governance_traceability_gate": "POST-SUBTASK-087",
  "integrated_proof_required": true
}
```

## End-to-End Validation Requirement

An identical sealed replay yields an auditable A&M-specialization-or-no-adjustment decision consumed by the production forecast.

## Expected Maturity After Completion

`INTEGRATED`

## Risk / Failure Conditions

- Parallel child outputs may use inconsistent source or schema identities
- Gate task may be bypassed after implementation tasks finish

## Stop Conditions

- Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs.

## Source References

- SRCREF-02057
- SRCREF-02058
- SRCREF-02059
- SRCREF-02060
- SRCREF-02061
- SRCREF-02062
- SRCREF-02063
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01893
- SRCREF-01571

## AI Context Notes

- Open only this Story, its selected child, and referenced source sections; do not load the entire Jira pack.
- Story completion requires the gate Subtask, not only implementation children.

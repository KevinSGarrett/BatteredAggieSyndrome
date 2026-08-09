<!-- GENERATED VIEW. Canonical record: jira/records/issues/stories/POST-STORY-035_calibration_robustness_gates_a_and_m_bas_decisions_and_champion_promotion.json -->
# POST-STORY-035 — [POST-STORY-035] Calibration/robustness gates, A&M/BAS decisions, and champion promotion

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "All child Subtasks satisfy their issue-specific observable checks and save their required evidence.",
    "The final child gate verifies the combined output and explicitly approves, blocks, rejects, or defers downstream use.",
    "No child completion is accepted if a hard prerequisite, PIT/right/security/protected-control requirement, or evidence identity is missing."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Open only this Story, its selected child, and referenced source sections; do not load the entire Jira pack.",
    "Story completion requires the gate Subtask, not only implementation children."
  ],
  "allowed_modification_paths": [
    "artifacts/jira_evidence/POST-STORY-035.json"
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/stories/POST-STORY-035_calibration_robustness_gates_a_and_m_bas_decisions_and_champion_promotion.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "all_child_evidence_required": true,
    "child_gate": "POST-SUBTASK-105",
    "governance_traceability_gate": "POST-SUBTASK-105",
    "integrated_proof_required": true
  },
  "component": "validation-promotion",
  "components_expected_to_be_touched": [
    "validation-promotion",
    "validation"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "All child subtasks POST-SUBTASK-103, POST-SUBTASK-104, POST-SUBTASK-105 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.",
    "The final gate `POST-SUBTASK-105` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.",
    "All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.",
    "The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.",
    "Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation."
  ],
  "dependencies": [
    "POST-SUBTASK-087",
    "POST-SUBTASK-096",
    "POST-SUBTASK-102"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 62,
    "adr_ids": 26,
    "gap_ids": 0,
    "requirement_ids": 70,
    "risk_ids": 25
  },
  "effective_traceability_total": 183,
  "end_to_end_validation": "All sealed candidates receive complete reproducible protected evaluation and the system produces a signed champion or explicit no-champion result without fabricated performance.",
  "epic_id": "POST-EPIC-011",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-STORY-035.json",
  "evidence_state": "PLANNED",
  "execution_lane": "SHARED_CONTRACT",
  "execution_mode": "AGGREGATE_GATE",
  "expected_maturity_after_completion": "INTEGRATED",
  "expected_outputs": [
    "artifacts/validation/calibration_robustness_report.json",
    "artifacts/validation/promotion_ranking.json",
    "artifacts/validation/PROMOTION_DECISION.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/validation/promotion.py",
    "src/aggie_analytics/validation/protected.py",
    "docs/56_VALIDATION_AND_PROTECTED_SPLITS.md",
    "docs/57_SCORING_CALIBRATION_AND_SCORECARDS.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/validation/promotion.py",
    "src/aggie_analytics/validation/protected.py",
    "docs/56_VALIDATION_AND_PROTECTED_SPLITS.md",
    "docs/57_SCORING_CALIBRATION_AND_SCORECARDS.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/stories/POST-STORY-035_calibration_robustness_gates_a_and_m_bas_decisions_and_champion_promotion.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-105",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100085,
  "in_scope": [
    "Complete and verify child `POST-SUBTASK-103` — Evaluate task-specific calibration, intervals, tails, coherence, OOD, missingness, season/regime/source shift, market ablation, and resource robustness.",
    "Complete and verify child `POST-SUBTASK-104` — Apply the precommitted multi-task promotion policy, uncertainty, simplicity, operational compatibility, A&M decision, and BAS scientific decision.",
    "Complete and verify child `POST-SUBTASK-105` — Publish signed champion/retain-incumbent/no-champion artifacts and the full promotion gate matrix.",
    "Integrate the child outputs and execute final gate `POST-SUBTASK-105`.",
    "Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence."
  ],
  "issue_type": "Story",
  "jira_key": "BAT-85",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "story",
    "validation"
  ],
  "last_content_audit": "2026-08-08",
  "local_id": "POST-STORY-035",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Apply every release-blocking gate and sign a champion only when protected evidence supports one.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24225",
    "jira_updated_at": "2026-08-09T00:03:57.565-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Work assigned to sibling Stories or another Epic.",
    "Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.",
    "Weakening protected requirements, PIT/rights/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-EPIC-011",
  "phase": "PHASE-4",
  "prerequisites": [
    "Hard dependency POST-SUBTASK-102",
    "Hard dependency POST-SUBTASK-087",
    "Hard dependency POST-SUBTASK-096"
  ],
  "primary_source_refs": [
    "SRCREF-02071",
    "SRCREF-02072",
    "SRCREF-02073",
    "SRCREF-02074"
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
    "src/aggie_analytics/validation/promotion.py",
    "src/aggie_analytics/validation/protected.py",
    "docs/56_VALIDATION_AND_PROTECTED_SPLITS.md",
    "docs/57_SCORING_CALIBRATION_AND_SCORECARDS.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "Verified child completion/evidence manifests for POST-SUBTASK-103, POST-SUBTASK-104, POST-SUBTASK-105.",
    "Final gate decision from `POST-SUBTASK-105` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.",
    "Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_validation_science_governance.py"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_w25_final_handoff.py"
    },
    {
      "classification": "END_TO_END",
      "expectation": "The final child gate `POST-SUBTASK-105` must prove the integrated Story outcome and downstream-consumable output.",
      "path": "POST-SUBTASK-105",
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
  "scope": "Deliver Story POST-STORY-035 (Calibration/robustness gates, A&M/BAS decisions, and champion promotion) as one coherent, gated capability inside Epic POST-EPIC-011. Execute child subtasks POST-SUBTASK-103, POST-SUBTASK-104, POST-SUBTASK-105 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-105` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.",
  "source_ids": [
    "GAP-008",
    "GAP-009",
    "HANDOFF-006"
  ],
  "source_refs": [
    "SRCREF-02071",
    "SRCREF-02072",
    "SRCREF-02073",
    "SRCREF-02074",
    "SRCREF-02075",
    "SRCREF-02076",
    "SRCREF-02077",
    "SRCREF-02078",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01892",
    "SRCREF-01570",
    "SRCREF-01571"
  ],
  "specificity_fingerprint": "83ed1e115c68e17a3ecab7a13efd9321003bcf2001d5989504b925495e423c49",
  "stop_conditions": [
    "Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs."
  ],
  "supporting_source_refs": [
    "SRCREF-02075",
    "SRCREF-02076",
    "SRCREF-02077",
    "SRCREF-02078",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01892",
    "SRCREF-01570",
    "SRCREF-01571"
  ],
  "title": "[POST-STORY-035] Calibration/robustness gates, A&M/BAS decisions, and champion promotion",
  "traceability_inherited_from": [
    "POST-SUBTASK-105"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "END_TO_END",
    "EXISTING_AUTOMATED_TEST",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "This coherent capability closes a defined portion of Protected chronological evaluation, calibration, and champion promotion and creates a verifiable output for the next dependency stage.",
  "work_packet_path": "jira/ai/work_packets/POST-STORY-035.md",
  "workflow_state": "BACKLOG"
}
```

## Objective

Apply every release-blocking gate and sign a champion only when protected evidence supports one.

## Why This Exists

This coherent capability closes a defined portion of Protected chronological evaluation, calibration, and champion promotion and creates a verifiable output for the next dependency stage.

## Scope

Deliver Story POST-STORY-035 (Calibration/robustness gates, A&M/BAS decisions, and champion promotion) as one coherent, gated capability inside Epic POST-EPIC-011. Execute child subtasks POST-SUBTASK-103, POST-SUBTASK-104, POST-SUBTASK-105 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-105` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### Explicit In Scope

- Complete and verify child `POST-SUBTASK-103` — Evaluate task-specific calibration, intervals, tails, coherence, OOD, missingness, season/regime/source shift, market ablation, and resource robustness.
- Complete and verify child `POST-SUBTASK-104` — Apply the precommitted multi-task promotion policy, uncertainty, simplicity, operational compatibility, A&M decision, and BAS scientific decision.
- Complete and verify child `POST-SUBTASK-105` — Publish signed champion/retain-incumbent/no-champion artifacts and the full promotion gate matrix.
- Integrate the child outputs and execute final gate `POST-SUBTASK-105`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Explicit Out of Scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/rights/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

## Prerequisites

- Hard dependency POST-SUBTASK-102
- Hard dependency POST-SUBTASK-087
- Hard dependency POST-SUBTASK-096

## Hard Dependencies

- POST-SUBTASK-087
- POST-SUBTASK-096
- POST-SUBTASK-102

## Blocks

- None.

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/validation/promotion.py
- src/aggie_analytics/validation/protected.py
- docs/56_VALIDATION_AND_PROTECTED_SPLITS.md
- docs/57_SCORING_CALIBRATION_AND_SCORECARDS.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- validation-promotion
- validation

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

- artifacts/validation/calibration_robustness_report.json
- artifacts/validation/promotion_ranking.json
- artifacts/validation/PROMOTION_DECISION.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-105`
- Inherited from: POST-SUBTASK-105
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 62, "adr_ids": 26, "gap_ids": 0, "requirement_ids": 70, "risk_ids": 25}`

## Acceptance Criteria

1. All child Subtasks satisfy their issue-specific observable checks and save their required evidence.
2. The final child gate verifies the combined output and explicitly approves, blocks, rejects, or defers downstream use.
3. No child completion is accepted if a hard prerequisite, PIT/right/security/protected-control requirement, or evidence identity is missing.

## Definition of Done

1. All child subtasks POST-SUBTASK-103, POST-SUBTASK-104, POST-SUBTASK-105 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.
2. The final gate `POST-SUBTASK-105` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.
3. All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.
4. The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.
5. Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_validation_science_governance.py` — Run and retain the result when this issue touches the covered contract.
- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_w25_final_handoff.py` — Run and retain the result when this issue touches the covered contract.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-105` — The final child gate `POST-SUBTASK-105` must prove the integrated Story outcome and downstream-consumable output.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `STORY_EVIDENCE_MANIFEST` — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Required Evidence

- Verified child completion/evidence manifests for POST-SUBTASK-103, POST-SUBTASK-104, POST-SUBTASK-105.
- Final gate decision from `POST-SUBTASK-105` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## Completion Evidence Contract

```json
{
  "all_child_evidence_required": true,
  "child_gate": "POST-SUBTASK-105",
  "governance_traceability_gate": "POST-SUBTASK-105",
  "integrated_proof_required": true
}
```

## End-to-End Validation Requirement

All sealed candidates receive complete reproducible protected evaluation and the system produces a signed champion or explicit no-champion result without fabricated performance.

## Expected Maturity After Completion

`INTEGRATED`

## Risk / Failure Conditions

- Parallel child outputs may use inconsistent source or schema identities
- Gate task may be bypassed after implementation tasks finish

## Stop Conditions

- Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs.

## Source References

- SRCREF-02071
- SRCREF-02072
- SRCREF-02073
- SRCREF-02074
- SRCREF-02075
- SRCREF-02076
- SRCREF-02077
- SRCREF-02078
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01892
- SRCREF-01570
- SRCREF-01571

## AI Context Notes

- Open only this Story, its selected child, and referenced source sections; do not load the entire Jira pack.
- Story completion requires the gate Subtask, not only implementation children.

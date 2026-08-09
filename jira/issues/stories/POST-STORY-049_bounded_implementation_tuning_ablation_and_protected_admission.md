<!-- GENERATED VIEW. Canonical record: jira/records/issues/stories/POST-STORY-049_bounded_implementation_tuning_ablation_and_protected_admission.json -->
# POST-STORY-049 — [POST-STORY-049] Bounded implementation, tuning, ablation, and protected admission

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
    "artifacts/jira_evidence/POST-STORY-049.json"
  ],
  "blocked_reason": "DEFERRED_OR_CONDITIONAL_BY_FINAL_HANDOFF",
  "blocks": [],
  "canonical_record": "jira/records/issues/stories/POST-STORY-049_bounded_implementation_tuning_ablation_and_protected_admission.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "all_child_evidence_required": true,
    "child_gate": "POST-SUBTASK-147",
    "governance_traceability_gate": "POST-SUBTASK-150",
    "integrated_proof_required": true
  },
  "component": "advanced-challengers",
  "components_expected_to_be_touched": [
    "advanced-challengers",
    "advanced"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "All child subtasks POST-SUBTASK-145, POST-SUBTASK-146, POST-SUBTASK-147 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.",
    "The final gate `POST-SUBTASK-147` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.",
    "All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.",
    "The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.",
    "Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation."
  ],
  "dependencies": [
    "POST-SUBTASK-144"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 1,
    "adr_ids": 2,
    "gap_ids": 1,
    "requirement_ids": 5,
    "risk_ids": 1
  },
  "effective_traceability_total": 10,
  "end_to_end_validation": "An admitted challenger produces bounded, reproducible, fully logged tuning evidence without changing production or leaking protected outcomes.",
  "epic_id": "POST-EPIC-016",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-STORY-049.json",
  "evidence_state": "PLANNED",
  "execution_lane": "SHARED_CONTRACT",
  "execution_mode": "AGGREGATE_GATE",
  "expected_maturity_after_completion": "INTEGRATED",
  "expected_outputs": [
    "artifacts/advanced/challenger_build_manifest.json",
    "artifacts/advanced/challenger_tuning_scorecard.json",
    "artifacts/advanced/challenger_protected_admission.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "tests/test_advanced_challenger_full.py",
    "src/aggie_analytics/experimentation/advanced_challengers.py",
    "docs/72_ADVANCED_CHALLENGER_ADMISSION.md",
    "docs/91_ADVANCED_CHALLENGER_GATE.md",
    "governance/ADVANCED_CHALLENGER_ADMISSION.csv"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "tests/test_advanced_challenger_full.py",
    "src/aggie_analytics/experimentation/advanced_challengers.py",
    "docs/72_ADVANCED_CHALLENGER_ADMISSION.md",
    "docs/91_ADVANCED_CHALLENGER_GATE.md",
    "governance/ADVANCED_CHALLENGER_ADMISSION.csv"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/stories/POST-STORY-049_bounded_implementation_tuning_ablation_and_protected_admission.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-150",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100099,
  "in_scope": [
    "Complete and verify child `POST-SUBTASK-145` — Implement the admitted neural/Bayesian/graph/sequence challenger against pinned matrices/splits within fixed scope and compute.",
    "Complete and verify child `POST-SUBTASK-146` — Run bounded tuning, ablation, calibration, OOD, robustness, stability, runtime, memory, maintainability, and simple-baseline comparisons retaining all failures.",
    "Complete and verify child `POST-SUBTASK-147` — Decide whether tuning evidence warrants a one-time sealed protected comparison.",
    "Integrate the child outputs and execute final gate `POST-SUBTASK-147`.",
    "Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence."
  ],
  "issue_type": "Story",
  "jira_key": "BAT-99",
  "labels": [
    "actionable",
    "advanced",
    "conditional",
    "post-wave",
    "story"
  ],
  "last_content_audit": "2026-08-08",
  "local_id": "POST-STORY-049",
  "maturity_before": "CONDITIONAL",
  "objective": "Run an admitted challenger in isolation without contaminating production or the protected test.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24239",
    "jira_updated_at": "2026-08-09T00:04:11.637-0500",
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
  "parent_id": "POST-EPIC-016",
  "phase": "PHASE-5",
  "prerequisites": [
    "Hard dependency POST-SUBTASK-144"
  ],
  "primary_source_refs": [
    "SRCREF-02107",
    "SRCREF-02108",
    "SRCREF-02109",
    "SRCREF-02110"
  ],
  "priority": "P3",
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
    "governance/IMPLEMENTATION_WBS.csv",
    "tests/test_advanced_challenger_full.py",
    "src/aggie_analytics/experimentation/advanced_challengers.py",
    "docs/72_ADVANCED_CHALLENGER_ADMISSION.md",
    "docs/91_ADVANCED_CHALLENGER_GATE.md",
    "governance/ADVANCED_CHALLENGER_ADMISSION.csv"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "Verified child completion/evidence manifests for POST-SUBTASK-145, POST-SUBTASK-146, POST-SUBTASK-147.",
    "Final gate decision from `POST-SUBTASK-147` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.",
    "Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_advanced_challenger_full.py"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tools/check_advanced_challenger_admission.py"
    },
    {
      "classification": "END_TO_END",
      "expectation": "The final child gate `POST-SUBTASK-147` must prove the integrated Story outcome and downstream-consumable output.",
      "path": "POST-SUBTASK-147",
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
  "scope": "Deliver Story POST-STORY-049 (Bounded implementation, tuning, ablation, and protected admission) as one coherent, gated capability inside Epic POST-EPIC-016. Execute child subtasks POST-SUBTASK-145, POST-SUBTASK-146, POST-SUBTASK-147 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-147` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.",
  "source_ids": [
    "GAP-013",
    "HANDOFF-013",
    "TASK-165",
    "TASK-166",
    "TASK-167",
    "TASK-168"
  ],
  "source_refs": [
    "SRCREF-02107",
    "SRCREF-02108",
    "SRCREF-02109",
    "SRCREF-02110",
    "SRCREF-02111",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01899",
    "SRCREF-01575",
    "SRCREF-00198",
    "SRCREF-00199",
    "SRCREF-00200",
    "SRCREF-00201"
  ],
  "specificity_fingerprint": "228f959f1faeccfd12913007200bfe9bf602ec932300a62e554d066aadf38728",
  "stop_conditions": [
    "Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs."
  ],
  "supporting_source_refs": [
    "SRCREF-02111",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01899",
    "SRCREF-01575",
    "SRCREF-00198",
    "SRCREF-00199",
    "SRCREF-00200",
    "SRCREF-00201"
  ],
  "title": "[POST-STORY-049] Bounded implementation, tuning, ablation, and protected admission",
  "traceability_inherited_from": [
    "POST-SUBTASK-150"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "A documented admission/replanning decision must explicitly activate this work after all stated prerequisites pass.",
  "validation_classes": [
    "END_TO_END",
    "EXISTING_AUTOMATED_TEST",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "This coherent capability closes a defined portion of Conditional advanced challenger research and admission and creates a verifiable output for the next dependency stage.",
  "work_packet_path": "jira/ai/work_packets/POST-STORY-049.md",
  "workflow_state": "DEFERRED"
}
```

## Objective

Run an admitted challenger in isolation without contaminating production or the protected test.

## Why This Exists

This coherent capability closes a defined portion of Conditional advanced challenger research and admission and creates a verifiable output for the next dependency stage.

## Scope

Deliver Story POST-STORY-049 (Bounded implementation, tuning, ablation, and protected admission) as one coherent, gated capability inside Epic POST-EPIC-016. Execute child subtasks POST-SUBTASK-145, POST-SUBTASK-146, POST-SUBTASK-147 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-147` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### Explicit In Scope

- Complete and verify child `POST-SUBTASK-145` — Implement the admitted neural/Bayesian/graph/sequence challenger against pinned matrices/splits within fixed scope and compute.
- Complete and verify child `POST-SUBTASK-146` — Run bounded tuning, ablation, calibration, OOD, robustness, stability, runtime, memory, maintainability, and simple-baseline comparisons retaining all failures.
- Complete and verify child `POST-SUBTASK-147` — Decide whether tuning evidence warrants a one-time sealed protected comparison.
- Integrate the child outputs and execute final gate `POST-SUBTASK-147`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Explicit Out of Scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/rights/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

## Prerequisites

- Hard dependency POST-SUBTASK-144

## Hard Dependencies

- POST-SUBTASK-144

## Blocks

- None.

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/IMPLEMENTATION_WBS.csv
- tests/test_advanced_challenger_full.py
- src/aggie_analytics/experimentation/advanced_challengers.py
- docs/72_ADVANCED_CHALLENGER_ADMISSION.md
- docs/91_ADVANCED_CHALLENGER_GATE.md
- governance/ADVANCED_CHALLENGER_ADMISSION.csv

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- advanced-challengers
- advanced

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

- artifacts/advanced/challenger_build_manifest.json
- artifacts/advanced/challenger_tuning_scorecard.json
- artifacts/advanced/challenger_protected_admission.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-150`
- Inherited from: POST-SUBTASK-150
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 1, "adr_ids": 2, "gap_ids": 1, "requirement_ids": 5, "risk_ids": 1}`

## Acceptance Criteria

1. All child Subtasks satisfy their issue-specific observable checks and save their required evidence.
2. The final child gate verifies the combined output and explicitly approves, blocks, rejects, or defers downstream use.
3. No child completion is accepted if a hard prerequisite, PIT/right/security/protected-control requirement, or evidence identity is missing.

## Definition of Done

1. All child subtasks POST-SUBTASK-145, POST-SUBTASK-146, POST-SUBTASK-147 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.
2. The final gate `POST-SUBTASK-147` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.
3. All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.
4. The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.
5. Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_advanced_challenger_full.py` — Run and retain the result when this issue touches the covered contract.
- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tools/check_advanced_challenger_admission.py` — Run and retain the result when this issue touches the covered contract.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-147` — The final child gate `POST-SUBTASK-147` must prove the integrated Story outcome and downstream-consumable output.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `STORY_EVIDENCE_MANIFEST` — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Required Evidence

- Verified child completion/evidence manifests for POST-SUBTASK-145, POST-SUBTASK-146, POST-SUBTASK-147.
- Final gate decision from `POST-SUBTASK-147` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## Completion Evidence Contract

```json
{
  "all_child_evidence_required": true,
  "child_gate": "POST-SUBTASK-147",
  "governance_traceability_gate": "POST-SUBTASK-150",
  "integrated_proof_required": true
}
```

## End-to-End Validation Requirement

An admitted challenger produces bounded, reproducible, fully logged tuning evidence without changing production or leaking protected outcomes.

## Expected Maturity After Completion

`INTEGRATED`

## Risk / Failure Conditions

- Parallel child outputs may use inconsistent source or schema identities
- Gate task may be bypassed after implementation tasks finish

## Stop Conditions

- Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs.

## Source References

- SRCREF-02107
- SRCREF-02108
- SRCREF-02109
- SRCREF-02110
- SRCREF-02111
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01899
- SRCREF-01575
- SRCREF-00198
- SRCREF-00199
- SRCREF-00200
- SRCREF-00201

## AI Context Notes

- Open only this Story, its selected child, and referenced source sections; do not load the entire Jira pack.
- Story completion requires the gate Subtask, not only implementation children.

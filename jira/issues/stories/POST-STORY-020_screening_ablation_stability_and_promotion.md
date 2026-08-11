<!-- GENERATED VIEW. Canonical record: jira/records/issues/stories/POST-STORY-020_screening_ablation_stability_and_promotion.json -->
# POST-STORY-020 — [POST-STORY-020] Screening, ablation, stability, and promotion

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Every experiment pins matrix/split/registry/code/model/seed identities and compares incremental value, compute cost, missingness, leakage risk, and stability without protected outcomes.",
    "The declared output `artifacts/features/feature_screening_results.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "Ablations retain null/negative results and report task/season/regime/A&M/peer/market-lane uncertainty, redundancy, and instability rather than cherry-picking one favorable slice.",
    "The declared output `artifacts/features/feature_ablation_stability.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Only policy-compliant candidates receive production eligibility; GAP-007 remains open until real protected evidence supports the selected set.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Open only this Story, its selected child, and referenced source sections; do not load the entire Jira pack.",
    "Story completion requires the gate Subtask, not only implementation children."
  ],
  "allowed_modification_paths": [
    "artifacts/jira_evidence/POST-STORY-020.json"
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/stories/POST-STORY-020_screening_ablation_stability_and_promotion.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "all_child_evidence_required": true,
    "child_gate": "POST-SUBTASK-060",
    "governance_traceability_gate": "POST-SUBTASK-060",
    "integrated_proof_required": true
  },
  "component": "feature-engineering",
  "components_expected_to_be_touched": [
    "feature-engineering",
    "features"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "All child subtasks POST-SUBTASK-058, POST-SUBTASK-059, POST-SUBTASK-060 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.",
    "The final gate `POST-SUBTASK-060` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.",
    "All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.",
    "The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.",
    "Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation."
  ],
  "dependencies": [
    "POST-SUBTASK-057"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 5,
    "adr_ids": 12,
    "gap_ids": 1,
    "requirement_ids": 50,
    "risk_ids": 19
  },
  "effective_traceability_total": 87,
  "end_to_end_validation": "A pinned registry feeds reproducible screening and ablation, yielding task-specific production lifecycle states while preserving bans and negative results.",
  "epic_id": "POST-EPIC-006",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-STORY-020.json",
  "evidence_state": "PLANNED",
  "execution_lane": "SHARED_CONTRACT",
  "execution_mode": "AGGREGATE_GATE",
  "expected_maturity_after_completion": "INTEGRATED",
  "expected_outputs": [
    "artifacts/features/feature_screening_results.json",
    "artifacts/features/feature_ablation_stability.json",
    "configs/feature_lifecycle_registry.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/features/factory.py",
    "src/aggie_analytics/features/lifecycle.py",
    "src/aggie_analytics/features/screening.py",
    "docs/22_RAW_FEATURE_REGISTRY_ARCHITECTURE.md",
    "docs/25_FEATURE_ENGINEERING_ARCHITECTURE.md",
    "docs/26_FEATURE_SCREENING_AND_SELECTION.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/features/factory.py",
    "src/aggie_analytics/features/lifecycle.py",
    "src/aggie_analytics/features/screening.py",
    "docs/22_RAW_FEATURE_REGISTRY_ARCHITECTURE.md",
    "docs/25_FEATURE_ENGINEERING_ARCHITECTURE.md",
    "docs/26_FEATURE_SCREENING_AND_SELECTION.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/stories/POST-STORY-020_screening_ablation_stability_and_promotion.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-060",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100070,
  "in_scope": [
    "Complete and verify child `POST-SUBTASK-058` — Run staged univariate/multivariate screening and bounded feature tournaments on permitted tuning history.",
    "Complete and verify child `POST-SUBTASK-059` — Run ablation, interaction, redundancy, missingness sensitivity, regime stability, A&M/peer, and market-lane analyses.",
    "Complete and verify child `POST-SUBTASK-060` — Publish the evidence-backed production feature lifecycle decision.",
    "Integrate the child outputs and execute final gate `POST-SUBTASK-060`.",
    "Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence."
  ],
  "issue_type": "Story",
  "jira_key": "BAT-70",
  "labels": [
    "actionable",
    "core-release",
    "features",
    "post-wave",
    "story"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-STORY-020",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Empirically determine which features contribute stable tuning/protected value and preserve negative evidence.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24210",
    "jira_updated_at": "2026-08-09T23:23:56.182-0500",
    "last_synced_at": "2026-08-11T07:25:49.170544+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\POST-SUBTASK-178-wmt-known-at\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Work assigned to sibling Stories or another Epic.",
    "Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.",
    "Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-EPIC-006",
  "phase": "PHASE-1",
  "prerequisites": [
    "Hard dependency POST-SUBTASK-057"
  ],
  "primary_source_refs": [
    "SRCREF-02033",
    "SRCREF-02034",
    "SRCREF-02035",
    "SRCREF-02036"
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
    "src/aggie_analytics/features/factory.py",
    "src/aggie_analytics/features/lifecycle.py",
    "src/aggie_analytics/features/screening.py",
    "docs/22_RAW_FEATURE_REGISTRY_ARCHITECTURE.md",
    "docs/25_FEATURE_ENGINEERING_ARCHITECTURE.md",
    "docs/26_FEATURE_SCREENING_AND_SELECTION.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "Verified child completion/evidence manifests for POST-SUBTASK-058, POST-SUBTASK-059, POST-SUBTASK-060.",
    "Final gate decision from `POST-SUBTASK-060` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.",
    "Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_feature_registry_governance.py"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_feature_lifecycle_governance.py"
    },
    {
      "classification": "END_TO_END",
      "expectation": "The final child gate `POST-SUBTASK-060` must prove the integrated Story outcome and downstream-consumable output.",
      "path": "POST-SUBTASK-060",
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
  "scope": "Deliver Story POST-STORY-020 (Screening, ablation, stability, and promotion) as one coherent, gated capability inside Epic POST-EPIC-006. Execute child subtasks POST-SUBTASK-058, POST-SUBTASK-059, POST-SUBTASK-060 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-060` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.",
  "source_ids": [
    "GAP-007",
    "HANDOFF-005"
  ],
  "source_refs": [
    "SRCREF-02033",
    "SRCREF-02034",
    "SRCREF-02035",
    "SRCREF-02036",
    "SRCREF-02037",
    "SRCREF-02038",
    "SRCREF-02039",
    "SRCREF-02040",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01891",
    "SRCREF-01569"
  ],
  "specificity_fingerprint": "0736dda389b74a1fe79cbc485a9758fe51b3c978df870ce53a9b6c616f3d3708",
  "stop_conditions": [
    "Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs."
  ],
  "supporting_source_refs": [
    "SRCREF-02037",
    "SRCREF-02038",
    "SRCREF-02039",
    "SRCREF-02040",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01891",
    "SRCREF-01569"
  ],
  "title": "[POST-STORY-020] Screening, ablation, stability, and promotion",
  "traceability_inherited_from": [
    "POST-SUBTASK-060"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "END_TO_END",
    "EXISTING_AUTOMATED_TEST",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "This coherent capability closes a defined portion of Production feature materialization and lifecycle and creates a verifiable output for the next dependency stage.",
  "work_packet_path": "jira/ai/work_packets/POST-STORY-020.md",
  "workflow_state": "BACKLOG"
}
```

## Objective

Empirically determine which features contribute stable tuning/protected value and preserve negative evidence.

## Why This Exists

This coherent capability closes a defined portion of Production feature materialization and lifecycle and creates a verifiable output for the next dependency stage.

## Scope

Deliver Story POST-STORY-020 (Screening, ablation, stability, and promotion) as one coherent, gated capability inside Epic POST-EPIC-006. Execute child subtasks POST-SUBTASK-058, POST-SUBTASK-059, POST-SUBTASK-060 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-060` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### Explicit In Scope

- Complete and verify child `POST-SUBTASK-058` — Run staged univariate/multivariate screening and bounded feature tournaments on permitted tuning history.
- Complete and verify child `POST-SUBTASK-059` — Run ablation, interaction, redundancy, missingness sensitivity, regime stability, A&M/peer, and market-lane analyses.
- Complete and verify child `POST-SUBTASK-060` — Publish the evidence-backed production feature lifecycle decision.
- Integrate the child outputs and execute final gate `POST-SUBTASK-060`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Explicit Out of Scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

## Prerequisites

- Hard dependency POST-SUBTASK-057

## Hard Dependencies

- POST-SUBTASK-057

## Blocks

- None.

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/features/factory.py
- src/aggie_analytics/features/lifecycle.py
- src/aggie_analytics/features/screening.py
- docs/22_RAW_FEATURE_REGISTRY_ARCHITECTURE.md
- docs/25_FEATURE_ENGINEERING_ARCHITECTURE.md
- docs/26_FEATURE_SCREENING_AND_SELECTION.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- feature-engineering
- features

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

- artifacts/features/feature_screening_results.json
- artifacts/features/feature_ablation_stability.json
- configs/feature_lifecycle_registry.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-060`
- Inherited from: POST-SUBTASK-060
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 5, "adr_ids": 12, "gap_ids": 1, "requirement_ids": 50, "risk_ids": 19}`

## Acceptance Criteria

1. Every experiment pins matrix/split/registry/code/model/seed identities and compares incremental value, compute cost, missingness, leakage risk, and stability without protected outcomes.
2. The declared output `artifacts/features/feature_screening_results.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
4. Ablations retain null/negative results and report task/season/regime/A&M/peer/market-lane uncertainty, redundancy, and instability rather than cherry-picking one favorable slice.
5. The declared output `artifacts/features/feature_ablation_stability.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
6. Only policy-compliant candidates receive production eligibility; GAP-007 remains open until real protected evidence supports the selected set.
7. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. All child subtasks POST-SUBTASK-058, POST-SUBTASK-059, POST-SUBTASK-060 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.
2. The final gate `POST-SUBTASK-060` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.
3. All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.
4. The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.
5. Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_feature_registry_governance.py` — Run and retain the result when this issue touches the covered contract.
- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_feature_lifecycle_governance.py` — Run and retain the result when this issue touches the covered contract.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-060` — The final child gate `POST-SUBTASK-060` must prove the integrated Story outcome and downstream-consumable output.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `STORY_EVIDENCE_MANIFEST` — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Required Evidence

- Verified child completion/evidence manifests for POST-SUBTASK-058, POST-SUBTASK-059, POST-SUBTASK-060.
- Final gate decision from `POST-SUBTASK-060` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## Completion Evidence Contract

```json
{
  "all_child_evidence_required": true,
  "child_gate": "POST-SUBTASK-060",
  "governance_traceability_gate": "POST-SUBTASK-060",
  "integrated_proof_required": true
}
```

## End-to-End Validation Requirement

A pinned registry feeds reproducible screening and ablation, yielding task-specific production lifecycle states while preserving bans and negative results.

## Expected Maturity After Completion

`INTEGRATED`

## Risk / Failure Conditions

- Parallel child outputs may use inconsistent source or schema identities
- Gate task may be bypassed after implementation tasks finish

## Stop Conditions

- Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs.

## Source References

- SRCREF-02033
- SRCREF-02034
- SRCREF-02035
- SRCREF-02036
- SRCREF-02037
- SRCREF-02038
- SRCREF-02039
- SRCREF-02040
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01891
- SRCREF-01569

## AI Context Notes

- Open only this Story, its selected child, and referenced source sections; do not load the entire Jira pack.
- Story completion requires the gate Subtask, not only implementation children.

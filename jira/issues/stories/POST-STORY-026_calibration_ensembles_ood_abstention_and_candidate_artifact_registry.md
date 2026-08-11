<!-- GENERATED VIEW. Canonical record: jira/records/issues/stories/POST-STORY-026_calibration_ensembles_ood_abstention_and_candidate_artifact_registry.json -->
# POST-STORY-026 — [POST-STORY-026] Calibration, ensembles, OOD, abstention, and candidate artifact registry

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Calibrators and ensemble weights are fit only on allowed tuning data, retain member/diversity/failure identities, and cannot use protected outcomes for selection.",
    "The declared output `artifacts/modeling/calibration_ensemble_runs.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "Evidence-derived tuning thresholds identify unsupported conditions and return wider uncertainty/abstention reasons rather than confident defaults when required inputs are unavailable.",
    "The declared output `artifacts/modeling/ood_abstention_validation.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Every admitted candidate pins data/feature/split/code/dependency/model/calibrator/seed identities, supported modes, OOD policy, resource envelope, and caveats; GAP-008 remains open pending protected replay.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Open only this Story, its selected child, and referenced source sections; do not load the entire Jira pack.",
    "Story completion requires the gate Subtask, not only implementation children."
  ],
  "allowed_modification_paths": [
    "artifacts/jira_evidence/POST-STORY-026.json"
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/stories/POST-STORY-026_calibration_ensembles_ood_abstention_and_candidate_artifact_registry.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "all_child_evidence_required": true,
    "child_gate": "POST-SUBTASK-078",
    "governance_traceability_gate": "POST-SUBTASK-078",
    "integrated_proof_required": true
  },
  "component": "modeling",
  "components_expected_to_be_touched": [
    "modeling"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "All child subtasks POST-SUBTASK-076, POST-SUBTASK-077, POST-SUBTASK-078 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.",
    "The final gate `POST-SUBTASK-078` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.",
    "All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.",
    "The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.",
    "Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation."
  ],
  "dependencies": [
    "POST-SUBTASK-075"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 21,
    "adr_ids": 72,
    "gap_ids": 1,
    "requirement_ids": 139,
    "risk_ids": 53
  },
  "effective_traceability_total": 286,
  "end_to_end_validation": "All candidates enter protected evaluation as immutable reproducible artifacts with precommitted calibration, uncertainty, OOD, and abstention behavior.",
  "epic_id": "POST-EPIC-008",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-STORY-026.json",
  "evidence_state": "PLANNED",
  "execution_lane": "SHARED_CONTRACT",
  "execution_mode": "AGGREGATE_GATE",
  "expected_maturity_after_completion": "INTEGRATED",
  "expected_outputs": [
    "artifacts/modeling/calibration_ensemble_runs.json",
    "artifacts/modeling/ood_abstention_validation.json",
    "artifacts/modeling/CANDIDATE_MODEL_REGISTRY.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/modeling/baselines.py",
    "src/aggie_analytics/modeling/joint.py",
    "src/aggie_analytics/modeling/runtime.py",
    "docs/103_W20_MODEL_CALIBRATION_BAS_IMPLEMENTATION.md",
    "docs/51_MODEL_TARGETS_AND_OUTPUT_COHERENCE.md",
    "docs/52_MODEL_ARCHITECTURE_CANDIDATES.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/modeling/baselines.py",
    "src/aggie_analytics/modeling/joint.py",
    "src/aggie_analytics/modeling/runtime.py",
    "docs/103_W20_MODEL_CALIBRATION_BAS_IMPLEMENTATION.md",
    "docs/51_MODEL_TARGETS_AND_OUTPUT_COHERENCE.md",
    "docs/52_MODEL_ARCHITECTURE_CANDIDATES.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/stories/POST-STORY-026_calibration_ensembles_ood_abstention_and_candidate_artifact_registry.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-078",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100076,
  "in_scope": [
    "Complete and verify child `POST-SUBTASK-076` — Train precommitted task/cutoff/lane calibration and ensemble candidates using permitted tuning predictions.",
    "Complete and verify child `POST-SUBTASK-077` — Implement sparse-history, missingness, source/regime shift, feature-pattern OOD, uncertainty, and abstention diagnostics.",
    "Complete and verify child `POST-SUBTASK-078` — Publish the immutable candidate artifact registry for sealed protected evaluation.",
    "Integrate the child outputs and execute final gate `POST-SUBTASK-078`.",
    "Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence."
  ],
  "issue_type": "Story",
  "jira_key": "BAT-76",
  "labels": [
    "actionable",
    "core-release",
    "modeling",
    "post-wave",
    "story"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-STORY-026",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Represent uncertainty and seal all admitted candidate identities before protected evaluation.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24216",
    "jira_updated_at": "2026-08-09T23:23:56.696-0500",
    "last_synced_at": "2026-08-11T07:44:24.297472+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\BAT-523-tamu-availability-pages\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Work assigned to sibling Stories or another Epic.",
    "Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.",
    "Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-EPIC-008",
  "phase": "PHASE-1",
  "prerequisites": [
    "Hard dependency POST-SUBTASK-075"
  ],
  "primary_source_refs": [
    "SRCREF-02049",
    "SRCREF-02050",
    "SRCREF-02051",
    "SRCREF-02052"
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
    "src/aggie_analytics/modeling/baselines.py",
    "src/aggie_analytics/modeling/joint.py",
    "src/aggie_analytics/modeling/runtime.py",
    "docs/103_W20_MODEL_CALIBRATION_BAS_IMPLEMENTATION.md",
    "docs/51_MODEL_TARGETS_AND_OUTPUT_COHERENCE.md",
    "docs/52_MODEL_ARCHITECTURE_CANDIDATES.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "Verified child completion/evidence manifests for POST-SUBTASK-076, POST-SUBTASK-077, POST-SUBTASK-078.",
    "Final gate decision from `POST-SUBTASK-078` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.",
    "Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_model_architecture_governance.py"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_w20_model_starter.py"
    },
    {
      "classification": "END_TO_END",
      "expectation": "The final child gate `POST-SUBTASK-078` must prove the integrated Story outcome and downstream-consumable output.",
      "path": "POST-SUBTASK-078",
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
  "scope": "Deliver Story POST-STORY-026 (Calibration, ensembles, OOD, abstention, and candidate artifact registry) as one coherent, gated capability inside Epic POST-EPIC-008. Execute child subtasks POST-SUBTASK-076, POST-SUBTASK-077, POST-SUBTASK-078 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-078` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.",
  "source_ids": [
    "GAP-008",
    "HANDOFF-006"
  ],
  "source_refs": [
    "SRCREF-02049",
    "SRCREF-02050",
    "SRCREF-02051",
    "SRCREF-02052",
    "SRCREF-02053",
    "SRCREF-02054",
    "SRCREF-02055",
    "SRCREF-02056",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01892",
    "SRCREF-01570"
  ],
  "specificity_fingerprint": "beab620b6ab609f50ca4b95ebf8c77265698fc0c63b48c5f55bc3967493fad17",
  "stop_conditions": [
    "Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs."
  ],
  "supporting_source_refs": [
    "SRCREF-02053",
    "SRCREF-02054",
    "SRCREF-02055",
    "SRCREF-02056",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01892",
    "SRCREF-01570"
  ],
  "title": "[POST-STORY-026] Calibration, ensembles, OOD, abstention, and candidate artifact registry",
  "traceability_inherited_from": [
    "POST-SUBTASK-078"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "END_TO_END",
    "EXISTING_AUTOMATED_TEST",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "This coherent capability closes a defined portion of Reproducible baseline, coherent score, probability, and uncertainty modeling and creates a verifiable output for the next dependency stage.",
  "work_packet_path": "jira/ai/work_packets/POST-STORY-026.md",
  "workflow_state": "BACKLOG"
}
```

## Objective

Represent uncertainty and seal all admitted candidate identities before protected evaluation.

## Why This Exists

This coherent capability closes a defined portion of Reproducible baseline, coherent score, probability, and uncertainty modeling and creates a verifiable output for the next dependency stage.

## Scope

Deliver Story POST-STORY-026 (Calibration, ensembles, OOD, abstention, and candidate artifact registry) as one coherent, gated capability inside Epic POST-EPIC-008. Execute child subtasks POST-SUBTASK-076, POST-SUBTASK-077, POST-SUBTASK-078 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-078` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### Explicit In Scope

- Complete and verify child `POST-SUBTASK-076` — Train precommitted task/cutoff/lane calibration and ensemble candidates using permitted tuning predictions.
- Complete and verify child `POST-SUBTASK-077` — Implement sparse-history, missingness, source/regime shift, feature-pattern OOD, uncertainty, and abstention diagnostics.
- Complete and verify child `POST-SUBTASK-078` — Publish the immutable candidate artifact registry for sealed protected evaluation.
- Integrate the child outputs and execute final gate `POST-SUBTASK-078`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Explicit Out of Scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

## Prerequisites

- Hard dependency POST-SUBTASK-075

## Hard Dependencies

- POST-SUBTASK-075

## Blocks

- None.

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/modeling/baselines.py
- src/aggie_analytics/modeling/joint.py
- src/aggie_analytics/modeling/runtime.py
- docs/103_W20_MODEL_CALIBRATION_BAS_IMPLEMENTATION.md
- docs/51_MODEL_TARGETS_AND_OUTPUT_COHERENCE.md
- docs/52_MODEL_ARCHITECTURE_CANDIDATES.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- modeling

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

- artifacts/modeling/calibration_ensemble_runs.json
- artifacts/modeling/ood_abstention_validation.json
- artifacts/modeling/CANDIDATE_MODEL_REGISTRY.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-078`
- Inherited from: POST-SUBTASK-078
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 21, "adr_ids": 72, "gap_ids": 1, "requirement_ids": 139, "risk_ids": 53}`

## Acceptance Criteria

1. Calibrators and ensemble weights are fit only on allowed tuning data, retain member/diversity/failure identities, and cannot use protected outcomes for selection.
2. The declared output `artifacts/modeling/calibration_ensemble_runs.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
4. Evidence-derived tuning thresholds identify unsupported conditions and return wider uncertainty/abstention reasons rather than confident defaults when required inputs are unavailable.
5. The declared output `artifacts/modeling/ood_abstention_validation.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
6. Every admitted candidate pins data/feature/split/code/dependency/model/calibrator/seed identities, supported modes, OOD policy, resource envelope, and caveats; GAP-008 remains open pending protected replay.
7. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. All child subtasks POST-SUBTASK-076, POST-SUBTASK-077, POST-SUBTASK-078 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.
2. The final gate `POST-SUBTASK-078` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.
3. All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.
4. The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.
5. Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_model_architecture_governance.py` — Run and retain the result when this issue touches the covered contract.
- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_w20_model_starter.py` — Run and retain the result when this issue touches the covered contract.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-078` — The final child gate `POST-SUBTASK-078` must prove the integrated Story outcome and downstream-consumable output.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `STORY_EVIDENCE_MANIFEST` — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Required Evidence

- Verified child completion/evidence manifests for POST-SUBTASK-076, POST-SUBTASK-077, POST-SUBTASK-078.
- Final gate decision from `POST-SUBTASK-078` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## Completion Evidence Contract

```json
{
  "all_child_evidence_required": true,
  "child_gate": "POST-SUBTASK-078",
  "governance_traceability_gate": "POST-SUBTASK-078",
  "integrated_proof_required": true
}
```

## End-to-End Validation Requirement

All candidates enter protected evaluation as immutable reproducible artifacts with precommitted calibration, uncertainty, OOD, and abstention behavior.

## Expected Maturity After Completion

`INTEGRATED`

## Risk / Failure Conditions

- Parallel child outputs may use inconsistent source or schema identities
- Gate task may be bypassed after implementation tasks finish

## Stop Conditions

- Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs.

## Source References

- SRCREF-02049
- SRCREF-02050
- SRCREF-02051
- SRCREF-02052
- SRCREF-02053
- SRCREF-02054
- SRCREF-02055
- SRCREF-02056
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01892
- SRCREF-01570

## AI Context Notes

- Open only this Story, its selected child, and referenced source sections; do not load the entire Jira pack.
- Story completion requires the gate Subtask, not only implementation children.

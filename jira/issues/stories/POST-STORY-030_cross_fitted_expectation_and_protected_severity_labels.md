<!-- GENERATED VIEW. Canonical record: jira/records/issues/stories/POST-STORY-030_cross_fitted_expectation_and_protected_severity_labels.json -->
# POST-STORY-030 — [POST-STORY-030] Cross-fitted expectation and protected severity labels

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Each game expectation comes from a model fit without that outcome, inside permitted chronology, with model/fold/data/feature/cutoff/calibration identities per row.",
    "The declared output `artifacts/bas/crossfit_expectation_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "Labels use actual performance versus valid expected margin with ≥7 as headline, so a win may be BAS and a loss may not; thresholds/direction are sealed before A&M results.",
    "The declared output `artifacts/bas/bas_label_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Synthetic sign cases and real spot checks prove semantics, every label links to expectation/outcome evidence, and any implementation equating BAS with loss probability fails.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "A null, non-significant, unstable, or directionally unsupported Aggie-specific excess result is accepted and reported without forcing a nonzero BAS effect; general FBS surprise and Texas A&M-specific excess remain distinct."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Open only this Story, its selected child, and referenced source sections; do not load the entire Jira pack.",
    "Story completion requires the gate Subtask, not only implementation children."
  ],
  "allowed_modification_paths": [
    "artifacts/jira_evidence/POST-STORY-030.json"
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/stories/POST-STORY-030_cross_fitted_expectation_and_protected_severity_labels.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "all_child_evidence_required": true,
    "child_gate": "POST-SUBTASK-090",
    "governance_traceability_gate": "POST-SUBTASK-096",
    "integrated_proof_required": true
  },
  "component": "bas-science",
  "components_expected_to_be_touched": [
    "bas-science",
    "bas"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "All child subtasks POST-SUBTASK-088, POST-SUBTASK-089, POST-SUBTASK-090 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.",
    "The final gate `POST-SUBTASK-090` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.",
    "All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.",
    "The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.",
    "Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation."
  ],
  "dependencies": [
    "POST-SUBTASK-051",
    "POST-SUBTASK-078"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 19,
    "adr_ids": 21,
    "gap_ids": 1,
    "requirement_ids": 66,
    "risk_ids": 13
  },
  "effective_traceability_total": 120,
  "end_to_end_validation": "Every BAS label is a traceable out-of-sample residual severity event rather than a renamed loss or circular model residual.",
  "epic_id": "POST-EPIC-010",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-STORY-030.json",
  "evidence_state": "PLANNED",
  "execution_lane": "SHARED_CONTRACT",
  "execution_mode": "AGGREGATE_GATE",
  "expected_maturity_after_completion": "INTEGRATED",
  "expected_outputs": [
    "artifacts/bas/crossfit_expectation_manifest.json",
    "artifacts/bas/bas_label_manifest.json",
    "artifacts/bas/bas_label_gate.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "tests/test_bas_science_governance.py",
    "src/aggie_analytics/bas/labels.py",
    "src/aggie_analytics/bas/runtime.py",
    "docs/45_SCIENTIFIC_BAS_SPECIFICATION.md",
    "docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "tests/test_bas_science_governance.py",
    "src/aggie_analytics/bas/labels.py",
    "src/aggie_analytics/bas/runtime.py",
    "docs/45_SCIENTIFIC_BAS_SPECIFICATION.md",
    "docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/stories/POST-STORY-030_cross_fitted_expectation_and_protected_severity_labels.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-096",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100080,
  "in_scope": [
    "Complete and verify child `POST-SUBTASK-088` — Generate out-of-fold or chronological cross-fitted pregame expected margins for every eligible historical game.",
    "Complete and verify child `POST-SUBTASK-089` — Materialize general surprise and A&M BAS severity labels at protected ≥3, ≥7, ≥14, and ≥21 thresholds.",
    "Complete and verify child `POST-SUBTASK-090` — Validate direction, thresholds, row lineage, fold isolation, and anti-circularity.",
    "Integrate the child outputs and execute final gate `POST-SUBTASK-090`.",
    "Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence."
  ],
  "issue_type": "Story",
  "jira_key": "BAT-80",
  "labels": [
    "actionable",
    "bas",
    "core-release",
    "post-wave",
    "story"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-STORY-030",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Generate leakage-safe expected margins and ≥3/7/14/21 residual labels with anti-circularity.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24220",
    "jira_updated_at": "2026-08-09T23:23:57.228-0500",
    "last_synced_at": "2026-08-11T06:07:11.607568+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\JIRA-LIVE-CATCHUP-20260811\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Work assigned to sibling Stories or another Epic.",
    "Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.",
    "Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.",
    "Redefining BAS as generic Texas A&M loss probability or selecting specifications merely to manufacture a nonzero Aggie-specific effect."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-EPIC-010",
  "phase": "PHASE-3",
  "prerequisites": [
    "Hard dependency POST-SUBTASK-078",
    "Hard dependency POST-SUBTASK-051"
  ],
  "primary_source_refs": [
    "SRCREF-02064",
    "SRCREF-02065",
    "SRCREF-02066",
    "SRCREF-02067"
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
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "tests/test_bas_science_governance.py",
    "src/aggie_analytics/bas/labels.py",
    "src/aggie_analytics/bas/runtime.py",
    "docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "Verified child completion/evidence manifests for POST-SUBTASK-088, POST-SUBTASK-089, POST-SUBTASK-090.",
    "Final gate decision from `POST-SUBTASK-090` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.",
    "Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_bas_science_governance.py"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_w20_model_starter.py"
    },
    {
      "classification": "END_TO_END",
      "expectation": "The final child gate `POST-SUBTASK-090` must prove the integrated Story outcome and downstream-consumable output.",
      "path": "POST-SUBTASK-090",
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
  "scope": "Deliver Story POST-STORY-030 (Cross-fitted expectation and protected severity labels) as one coherent, gated capability inside Epic POST-EPIC-010. Execute child subtasks POST-SUBTASK-088, POST-SUBTASK-089, POST-SUBTASK-090 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-090` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.",
  "source_ids": [
    "AC-020",
    "AC-021",
    "GAP-009",
    "HANDOFF-009"
  ],
  "source_refs": [
    "SRCREF-02064",
    "SRCREF-02065",
    "SRCREF-02066",
    "SRCREF-02067",
    "SRCREF-02068",
    "SRCREF-02069",
    "SRCREF-02070",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01895",
    "SRCREF-01571",
    "SRCREF-00999",
    "SRCREF-01000"
  ],
  "specificity_fingerprint": "1108866aeaaa4738770561c63e1cf827406fbe0a34ebff9debd040190aa58063",
  "stop_conditions": [
    "Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs.",
    "Stop if the proposed method, threshold, peer set, fold construction, or product wording would conceal, reject, or overwrite a valid null/no-effect result."
  ],
  "supporting_source_refs": [
    "SRCREF-02068",
    "SRCREF-02069",
    "SRCREF-02070",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01895",
    "SRCREF-01571",
    "SRCREF-00999",
    "SRCREF-01000"
  ],
  "title": "[POST-STORY-030] Cross-fitted expectation and protected severity labels",
  "traceability_inherited_from": [
    "POST-SUBTASK-096"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "END_TO_END",
    "EXISTING_AUTOMATED_TEST",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "This coherent capability closes a defined portion of Scientific BAS, general FBS surprise, Aggie excess, and component validation and creates a verifiable output for the next dependency stage.",
  "work_packet_path": "jira/ai/work_packets/POST-STORY-030.md",
  "workflow_state": "BACKLOG"
}
```

## Objective

Generate leakage-safe expected margins and ≥3/7/14/21 residual labels with anti-circularity.

## Why This Exists

This coherent capability closes a defined portion of Scientific BAS, general FBS surprise, Aggie excess, and component validation and creates a verifiable output for the next dependency stage.

## Scope

Deliver Story POST-STORY-030 (Cross-fitted expectation and protected severity labels) as one coherent, gated capability inside Epic POST-EPIC-010. Execute child subtasks POST-SUBTASK-088, POST-SUBTASK-089, POST-SUBTASK-090 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-090` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### Explicit In Scope

- Complete and verify child `POST-SUBTASK-088` — Generate out-of-fold or chronological cross-fitted pregame expected margins for every eligible historical game.
- Complete and verify child `POST-SUBTASK-089` — Materialize general surprise and A&M BAS severity labels at protected ≥3, ≥7, ≥14, and ≥21 thresholds.
- Complete and verify child `POST-SUBTASK-090` — Validate direction, thresholds, row lineage, fold isolation, and anti-circularity.
- Integrate the child outputs and execute final gate `POST-SUBTASK-090`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Explicit Out of Scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.
- Redefining BAS as generic Texas A&M loss probability or selecting specifications merely to manufacture a nonzero Aggie-specific effect.

## Prerequisites

- Hard dependency POST-SUBTASK-078
- Hard dependency POST-SUBTASK-051

## Hard Dependencies

- POST-SUBTASK-051
- POST-SUBTASK-078

## Blocks

- None.

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- tests/test_bas_science_governance.py
- src/aggie_analytics/bas/labels.py
- src/aggie_analytics/bas/runtime.py
- docs/45_SCIENTIFIC_BAS_SPECIFICATION.md
- docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- bas-science
- bas

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

- artifacts/bas/crossfit_expectation_manifest.json
- artifacts/bas/bas_label_manifest.json
- artifacts/bas/bas_label_gate.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-096`
- Inherited from: POST-SUBTASK-096
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 19, "adr_ids": 21, "gap_ids": 1, "requirement_ids": 66, "risk_ids": 13}`

## Acceptance Criteria

1. Each game expectation comes from a model fit without that outcome, inside permitted chronology, with model/fold/data/feature/cutoff/calibration identities per row.
2. The declared output `artifacts/bas/crossfit_expectation_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
4. Labels use actual performance versus valid expected margin with ≥7 as headline, so a win may be BAS and a loss may not; thresholds/direction are sealed before A&M results.
5. The declared output `artifacts/bas/bas_label_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
6. Synthetic sign cases and real spot checks prove semantics, every label links to expectation/outcome evidence, and any implementation equating BAS with loss probability fails.
7. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
8. A null, non-significant, unstable, or directionally unsupported Aggie-specific excess result is accepted and reported without forcing a nonzero BAS effect; general FBS surprise and Texas A&M-specific excess remain distinct.

## Definition of Done

1. All child subtasks POST-SUBTASK-088, POST-SUBTASK-089, POST-SUBTASK-090 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.
2. The final gate `POST-SUBTASK-090` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.
3. All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.
4. The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.
5. Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_bas_science_governance.py` — Run and retain the result when this issue touches the covered contract.
- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_w20_model_starter.py` — Run and retain the result when this issue touches the covered contract.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-090` — The final child gate `POST-SUBTASK-090` must prove the integrated Story outcome and downstream-consumable output.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `STORY_EVIDENCE_MANIFEST` — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Required Evidence

- Verified child completion/evidence manifests for POST-SUBTASK-088, POST-SUBTASK-089, POST-SUBTASK-090.
- Final gate decision from `POST-SUBTASK-090` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## Completion Evidence Contract

```json
{
  "all_child_evidence_required": true,
  "child_gate": "POST-SUBTASK-090",
  "governance_traceability_gate": "POST-SUBTASK-096",
  "integrated_proof_required": true
}
```

## End-to-End Validation Requirement

Every BAS label is a traceable out-of-sample residual severity event rather than a renamed loss or circular model residual.

## Expected Maturity After Completion

`INTEGRATED`

## Risk / Failure Conditions

- Parallel child outputs may use inconsistent source or schema identities
- Gate task may be bypassed after implementation tasks finish

## Stop Conditions

- Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs.
- Stop if the proposed method, threshold, peer set, fold construction, or product wording would conceal, reject, or overwrite a valid null/no-effect result.

## Source References

- SRCREF-02064
- SRCREF-02065
- SRCREF-02066
- SRCREF-02067
- SRCREF-02068
- SRCREF-02069
- SRCREF-02070
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01895
- SRCREF-01571
- SRCREF-00999
- SRCREF-01000

## AI Context Notes

- Open only this Story, its selected child, and referenced source sections; do not load the entire Jira pack.
- Story completion requires the gate Subtask, not only implementation children.

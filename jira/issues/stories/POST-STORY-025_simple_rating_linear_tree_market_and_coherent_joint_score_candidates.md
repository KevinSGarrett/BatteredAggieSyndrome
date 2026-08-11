<!-- GENERATED VIEW. Canonical record: jira/records/issues/stories/POST-STORY-025_simple_rating_linear_tree_market_and_coherent_joint_score_candidates.json -->
# POST-STORY-025 — [POST-STORY-025] Simple, rating, linear, tree, market, and coherent joint-score candidates

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Every run pins data/config/code/seed/runtime, fits recency/home-field/shrinkage only on permitted history, separates market lanes/cutoffs, and retains failed or negative trials.",
    "The declared output `artifacts/modeling/baseline_candidate_runs.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "Derived outputs come from coherent score distributions, persist simulation identities, handle overtime/ties/extremes, and widen uncertainty under missing/OOD inputs rather than becoming confident.",
    "The declared output `artifacts/modeling/joint_distribution_runs.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Candidates regenerate identical predictions within declared numerical limits and no model enters protected replay with reproducibility, range, orientation, coherence, or resource failures.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Open only this Story, its selected child, and referenced source sections; do not load the entire Jira pack.",
    "Story completion requires the gate Subtask, not only implementation children."
  ],
  "allowed_modification_paths": [
    "artifacts/jira_evidence/POST-STORY-025.json"
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/stories/POST-STORY-025_simple_rating_linear_tree_market_and_coherent_joint_score_candidates.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "all_child_evidence_required": true,
    "child_gate": "POST-SUBTASK-075",
    "governance_traceability_gate": "POST-SUBTASK-078",
    "integrated_proof_required": true
  },
  "component": "modeling",
  "components_expected_to_be_touched": [
    "modeling"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "All child subtasks POST-SUBTASK-073, POST-SUBTASK-074, POST-SUBTASK-075 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.",
    "The final gate `POST-SUBTASK-075` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.",
    "All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.",
    "The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.",
    "Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation."
  ],
  "dependencies": [
    "POST-SUBTASK-072"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 21,
    "adr_ids": 72,
    "gap_ids": 1,
    "requirement_ids": 139,
    "risk_ids": 53
  },
  "effective_traceability_total": 286,
  "end_to_end_validation": "Pinned real datasets train simple and coherent distributional candidates that reproduce all outputs and remain honest about failures and compute.",
  "epic_id": "POST-EPIC-008",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-STORY-025.json",
  "evidence_state": "PLANNED",
  "execution_lane": "SHARED_CONTRACT",
  "execution_mode": "AGGREGATE_GATE",
  "expected_maturity_after_completion": "INTEGRATED",
  "expected_outputs": [
    "artifacts/modeling/baseline_candidate_runs.json",
    "artifacts/modeling/joint_distribution_runs.json",
    "artifacts/modeling/baseline_joint_gate.json"
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
  "generated_markdown": "jira/issues/stories/POST-STORY-025_simple_rating_linear_tree_market_and_coherent_joint_score_candidates.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-078",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100075,
  "in_scope": [
    "Complete and verify child `POST-SUBTASK-073` — Train naive, historical-average, home-field, rating, regularized linear, tree-boosting, market-free, and market-aware baselines with bounded searches.",
    "Complete and verify child `POST-SUBTASK-074` — Train joint/separate score-distribution candidates and deterministic-seed simulations deriving margin, win, score, total, interval, and severity outputs coherently.",
    "Complete and verify child `POST-SUBTASK-075` — Validate artifacts, tuning predictions, orientation, distribution tails, score-margin-win coherence, runtime, and candidate admission.",
    "Integrate the child outputs and execute final gate `POST-SUBTASK-075`.",
    "Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence."
  ],
  "issue_type": "Story",
  "jira_key": "BAT-75",
  "labels": [
    "actionable",
    "core-release",
    "modeling",
    "post-wave",
    "story"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-STORY-025",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Establish strong reproducible references and internally coherent distributional candidates before advanced challengers.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24215",
    "jira_updated_at": "2026-08-09T23:23:56.619-0500",
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
  "parent_id": "POST-EPIC-008",
  "phase": "PHASE-1",
  "prerequisites": [
    "Hard dependency POST-SUBTASK-072"
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
    "Verified child completion/evidence manifests for POST-SUBTASK-073, POST-SUBTASK-074, POST-SUBTASK-075.",
    "Final gate decision from `POST-SUBTASK-075` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.",
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
      "expectation": "The final child gate `POST-SUBTASK-075` must prove the integrated Story outcome and downstream-consumable output.",
      "path": "POST-SUBTASK-075",
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
  "scope": "Deliver Story POST-STORY-025 (Simple, rating, linear, tree, market, and coherent joint-score candidates) as one coherent, gated capability inside Epic POST-EPIC-008. Execute child subtasks POST-SUBTASK-073, POST-SUBTASK-074, POST-SUBTASK-075 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-075` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.",
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
  "specificity_fingerprint": "fbae3e2602d1065181394a86ac2b3981caf6ebfb8d86ad8538fd03f29c66dbb8",
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
  "title": "[POST-STORY-025] Simple, rating, linear, tree, market, and coherent joint-score candidates",
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
  "work_packet_path": "jira/ai/work_packets/POST-STORY-025.md",
  "workflow_state": "BACKLOG"
}
```

## Objective

Establish strong reproducible references and internally coherent distributional candidates before advanced challengers.

## Why This Exists

This coherent capability closes a defined portion of Reproducible baseline, coherent score, probability, and uncertainty modeling and creates a verifiable output for the next dependency stage.

## Scope

Deliver Story POST-STORY-025 (Simple, rating, linear, tree, market, and coherent joint-score candidates) as one coherent, gated capability inside Epic POST-EPIC-008. Execute child subtasks POST-SUBTASK-073, POST-SUBTASK-074, POST-SUBTASK-075 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-075` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### Explicit In Scope

- Complete and verify child `POST-SUBTASK-073` — Train naive, historical-average, home-field, rating, regularized linear, tree-boosting, market-free, and market-aware baselines with bounded searches.
- Complete and verify child `POST-SUBTASK-074` — Train joint/separate score-distribution candidates and deterministic-seed simulations deriving margin, win, score, total, interval, and severity outputs coherently.
- Complete and verify child `POST-SUBTASK-075` — Validate artifacts, tuning predictions, orientation, distribution tails, score-margin-win coherence, runtime, and candidate admission.
- Integrate the child outputs and execute final gate `POST-SUBTASK-075`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Explicit Out of Scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

## Prerequisites

- Hard dependency POST-SUBTASK-072

## Hard Dependencies

- POST-SUBTASK-072

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

- artifacts/modeling/baseline_candidate_runs.json
- artifacts/modeling/joint_distribution_runs.json
- artifacts/modeling/baseline_joint_gate.json

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

1. Every run pins data/config/code/seed/runtime, fits recency/home-field/shrinkage only on permitted history, separates market lanes/cutoffs, and retains failed or negative trials.
2. The declared output `artifacts/modeling/baseline_candidate_runs.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
4. Derived outputs come from coherent score distributions, persist simulation identities, handle overtime/ties/extremes, and widen uncertainty under missing/OOD inputs rather than becoming confident.
5. The declared output `artifacts/modeling/joint_distribution_runs.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
6. Candidates regenerate identical predictions within declared numerical limits and no model enters protected replay with reproducibility, range, orientation, coherence, or resource failures.
7. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. All child subtasks POST-SUBTASK-073, POST-SUBTASK-074, POST-SUBTASK-075 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.
2. The final gate `POST-SUBTASK-075` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.
3. All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.
4. The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.
5. Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_model_architecture_governance.py` — Run and retain the result when this issue touches the covered contract.
- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_w20_model_starter.py` — Run and retain the result when this issue touches the covered contract.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-075` — The final child gate `POST-SUBTASK-075` must prove the integrated Story outcome and downstream-consumable output.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `STORY_EVIDENCE_MANIFEST` — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Required Evidence

- Verified child completion/evidence manifests for POST-SUBTASK-073, POST-SUBTASK-074, POST-SUBTASK-075.
- Final gate decision from `POST-SUBTASK-075` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## Completion Evidence Contract

```json
{
  "all_child_evidence_required": true,
  "child_gate": "POST-SUBTASK-075",
  "governance_traceability_gate": "POST-SUBTASK-078",
  "integrated_proof_required": true
}
```

## End-to-End Validation Requirement

Pinned real datasets train simple and coherent distributional candidates that reproduce all outputs and remain honest about failures and compute.

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

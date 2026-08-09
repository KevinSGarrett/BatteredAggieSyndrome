<!-- GENERATED VIEW. Canonical record: jira/records/issues/stories/POST-STORY-039_read_only_forecast_repository_and_versioned_api.json -->
# POST-STORY-039 — [POST-STORY-039] Read-only forecast repository and versioned API

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
    "artifacts/jira_evidence/POST-STORY-039.json"
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/stories/POST-STORY-039_read_only_forecast_repository_and_versioned_api.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "all_child_evidence_required": true,
    "child_gate": "POST-SUBTASK-117",
    "governance_traceability_gate": "POST-SUBTASK-123",
    "integrated_proof_required": true
  },
  "component": "serving-product",
  "components_expected_to_be_touched": [
    "serving-product",
    "product"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "All child subtasks POST-SUBTASK-115, POST-SUBTASK-116, POST-SUBTASK-117 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.",
    "The final gate `POST-SUBTASK-117` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.",
    "All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.",
    "The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.",
    "Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation."
  ],
  "dependencies": [
    "POST-SUBTASK-111"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 10,
    "adr_ids": 24,
    "gap_ids": 1,
    "requirement_ids": 38,
    "risk_ids": 12
  },
  "effective_traceability_total": 85,
  "end_to_end_validation": "A client can retrieve a current or archived signed forecast and exact freshness/lineage without triggering model drift or seeing partial/restricted state.",
  "epic_id": "POST-EPIC-013",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-STORY-039.json",
  "evidence_state": "PLANNED",
  "execution_lane": "SHARED_CONTRACT",
  "execution_mode": "AGGREGATE_GATE",
  "expected_maturity_after_completion": "INTEGRATED",
  "expected_outputs": [
    "artifacts/product/snapshot_repository_test.json",
    "docs/product/OPENAPI_SNAPSHOT.json",
    "artifacts/product/api_gate.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_w22_product_serving.py",
    "src/aggie_analytics/api/fastapi_app.py",
    "src/aggie_analytics/product/freshness.py",
    "src/aggie_analytics/product/repository.py",
    "src/aggie_analytics/product/service.py",
    "docs/107_W22_SNAPSHOT_SERVING_PRODUCT.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_w22_product_serving.py",
    "src/aggie_analytics/api/fastapi_app.py",
    "src/aggie_analytics/product/freshness.py",
    "src/aggie_analytics/product/repository.py",
    "src/aggie_analytics/product/service.py",
    "docs/107_W22_SNAPSHOT_SERVING_PRODUCT.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/stories/POST-STORY-039_read_only_forecast_repository_and_versioned_api.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-123",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100089,
  "in_scope": [
    "Complete and verify child `POST-SUBTASK-115` — Implement approved active/archive snapshot repository, model/run lookup, and atomic read behavior.",
    "Complete and verify child `POST-SUBTASK-116` — Implement versioned forecast/game/team/A&M/BAS/health/freshness endpoints and OpenAPI contract.",
    "Complete and verify child `POST-SUBTASK-117` — Validate schema, authorization, snapshot consistency, stale/no-champion/null-BAS states, and restricted-data protection.",
    "Integrate the child outputs and execute final gate `POST-SUBTASK-117`.",
    "Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence."
  ],
  "issue_type": "Story",
  "jira_key": "BAT-89",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "product",
    "story"
  ],
  "last_content_audit": "2026-08-08",
  "local_id": "POST-STORY-039",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Turn the serving starter into a production snapshot API with health/freshness and explicit unavailable states.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24229",
    "jira_updated_at": "2026-08-09T00:04:01.292-0500",
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
  "parent_id": "POST-EPIC-013",
  "phase": "PHASE-4",
  "prerequisites": [
    "Hard dependency POST-SUBTASK-111"
  ],
  "primary_source_refs": [
    "SRCREF-02085",
    "SRCREF-02086",
    "SRCREF-02087",
    "SRCREF-02088"
  ],
  "priority": "P2",
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
    "tests/test_w22_product_serving.py",
    "src/aggie_analytics/api/fastapi_app.py",
    "src/aggie_analytics/product/freshness.py",
    "src/aggie_analytics/product/repository.py",
    "src/aggie_analytics/product/service.py",
    "docs/107_W22_SNAPSHOT_SERVING_PRODUCT.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "Verified child completion/evidence manifests for POST-SUBTASK-115, POST-SUBTASK-116, POST-SUBTASK-117.",
    "Final gate decision from `POST-SUBTASK-117` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.",
    "Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_w22_product_serving.py"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tools/validate_w22_product.py"
    },
    {
      "classification": "END_TO_END",
      "expectation": "The final child gate `POST-SUBTASK-117` must prove the integrated Story outcome and downstream-consumable output.",
      "path": "POST-SUBTASK-117",
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
  "scope": "Deliver Story POST-STORY-039 (Read-only forecast repository and versioned API) as one coherent, gated capability inside Epic POST-EPIC-013. Execute child subtasks POST-SUBTASK-115, POST-SUBTASK-116, POST-SUBTASK-117 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-117` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.",
  "source_ids": [
    "GAP-012",
    "HANDOFF-011"
  ],
  "source_refs": [
    "SRCREF-02085",
    "SRCREF-02086",
    "SRCREF-02087",
    "SRCREF-02088",
    "SRCREF-02089",
    "SRCREF-02090",
    "SRCREF-02091",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01897",
    "SRCREF-01574"
  ],
  "specificity_fingerprint": "8886b9bfb7b5e915632192320dfa8cfd12e1c10e3e960fd3a921a6bfd4d35f95",
  "stop_conditions": [
    "Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs."
  ],
  "supporting_source_refs": [
    "SRCREF-02089",
    "SRCREF-02090",
    "SRCREF-02091",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01897",
    "SRCREF-01574"
  ],
  "title": "[POST-STORY-039] Read-only forecast repository and versioned API",
  "traceability_inherited_from": [
    "POST-SUBTASK-123"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "END_TO_END",
    "EXISTING_AUTOMATED_TEST",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "This coherent capability closes a defined portion of Snapshot API, dashboard, explanations, analogs, and freshness-safe product and creates a verifiable output for the next dependency stage.",
  "work_packet_path": "jira/ai/work_packets/POST-STORY-039.md",
  "workflow_state": "BACKLOG"
}
```

## Objective

Turn the serving starter into a production snapshot API with health/freshness and explicit unavailable states.

## Why This Exists

This coherent capability closes a defined portion of Snapshot API, dashboard, explanations, analogs, and freshness-safe product and creates a verifiable output for the next dependency stage.

## Scope

Deliver Story POST-STORY-039 (Read-only forecast repository and versioned API) as one coherent, gated capability inside Epic POST-EPIC-013. Execute child subtasks POST-SUBTASK-115, POST-SUBTASK-116, POST-SUBTASK-117 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-117` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### Explicit In Scope

- Complete and verify child `POST-SUBTASK-115` — Implement approved active/archive snapshot repository, model/run lookup, and atomic read behavior.
- Complete and verify child `POST-SUBTASK-116` — Implement versioned forecast/game/team/A&M/BAS/health/freshness endpoints and OpenAPI contract.
- Complete and verify child `POST-SUBTASK-117` — Validate schema, authorization, snapshot consistency, stale/no-champion/null-BAS states, and restricted-data protection.
- Integrate the child outputs and execute final gate `POST-SUBTASK-117`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Explicit Out of Scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/rights/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

## Prerequisites

- Hard dependency POST-SUBTASK-111

## Hard Dependencies

- POST-SUBTASK-111

## Blocks

- None.

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_w22_product_serving.py
- src/aggie_analytics/api/fastapi_app.py
- src/aggie_analytics/product/freshness.py
- src/aggie_analytics/product/repository.py
- src/aggie_analytics/product/service.py
- docs/107_W22_SNAPSHOT_SERVING_PRODUCT.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- serving-product
- product

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

- artifacts/product/snapshot_repository_test.json
- docs/product/OPENAPI_SNAPSHOT.json
- artifacts/product/api_gate.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-123`
- Inherited from: POST-SUBTASK-123
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 10, "adr_ids": 24, "gap_ids": 1, "requirement_ids": 38, "risk_ids": 12}`

## Acceptance Criteria

1. All child Subtasks satisfy their issue-specific observable checks and save their required evidence.
2. The final child gate verifies the combined output and explicitly approves, blocks, rejects, or defers downstream use.
3. No child completion is accepted if a hard prerequisite, PIT/right/security/protected-control requirement, or evidence identity is missing.

## Definition of Done

1. All child subtasks POST-SUBTASK-115, POST-SUBTASK-116, POST-SUBTASK-117 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.
2. The final gate `POST-SUBTASK-117` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.
3. All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.
4. The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.
5. Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_w22_product_serving.py` — Run and retain the result when this issue touches the covered contract.
- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tools/validate_w22_product.py` — Run and retain the result when this issue touches the covered contract.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-117` — The final child gate `POST-SUBTASK-117` must prove the integrated Story outcome and downstream-consumable output.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `STORY_EVIDENCE_MANIFEST` — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Required Evidence

- Verified child completion/evidence manifests for POST-SUBTASK-115, POST-SUBTASK-116, POST-SUBTASK-117.
- Final gate decision from `POST-SUBTASK-117` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## Completion Evidence Contract

```json
{
  "all_child_evidence_required": true,
  "child_gate": "POST-SUBTASK-117",
  "governance_traceability_gate": "POST-SUBTASK-123",
  "integrated_proof_required": true
}
```

## End-to-End Validation Requirement

A client can retrieve a current or archived signed forecast and exact freshness/lineage without triggering model drift or seeing partial/restricted state.

## Expected Maturity After Completion

`INTEGRATED`

## Risk / Failure Conditions

- Parallel child outputs may use inconsistent source or schema identities
- Gate task may be bypassed after implementation tasks finish

## Stop Conditions

- Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs.

## Source References

- SRCREF-02085
- SRCREF-02086
- SRCREF-02087
- SRCREF-02088
- SRCREF-02089
- SRCREF-02090
- SRCREF-02091
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01897
- SRCREF-01574

## AI Context Notes

- Open only this Story, its selected child, and referenced source sections; do not load the entire Jira pack.
- Story completion requires the gate Subtask, not only implementation children.

<!-- GENERATED VIEW. Canonical record: jira/records/issues/epics/POST-EPIC-013_snapshot_api_dashboard_explanations_analogs_and_freshness_safe_product.json -->
# POST-EPIC-013 — [POST-EPIC-013] Snapshot API, dashboard, explanations, analogs, and freshness-safe product

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Every child issue completes at its declared maturity and evidence state, or has an explicit accepted-risk/deferred disposition.",
    "The Epic's end-to-end gate proves the integrated capability on the required real data, target host, protected chronology, or operating path; file existence alone is insufficient.",
    "All requirement, acceptance-control, ADR, risk, gap, test, artifact, and source references remain valid and no protected invariant is weakened."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Select child Subtasks from READY_QUEUE.csv; do not execute an Epic directly.",
    "Epic Done requires the final child gate and downstream-consumption evidence, not merely closed children."
  ],
  "allowed_modification_paths": [
    "artifacts/jira_evidence/POST-EPIC-013.json"
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/epics/POST-EPIC-013_snapshot_api_dashboard_explanations_analogs_and_freshness_safe_product.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "governance_traceability_gate": "POST-SUBTASK-123",
    "integrated_proof_required": true,
    "story_gates": [
      "POST-SUBTASK-117",
      "POST-SUBTASK-120",
      "POST-SUBTASK-123"
    ]
  },
  "component": "serving-product",
  "components_expected_to_be_touched": [
    "serving-product",
    "product"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "Every child Story POST-STORY-039, POST-STORY-040, POST-STORY-041 is completed through its explicit end-to-end gate or has an explicit accepted-risk/deferred/cancelled disposition consistent with release governance.",
    "The Epic integrated capability is demonstrated on the required real data, chronology, target host, product path, or operating path; planning, code, fixtures, or unit tests alone cannot satisfy it.",
    "All direct and inherited requirement/control/ADR/risk/gap mappings resolve, all release-blocking controls have current evidence, and no protected invariant is weakened.",
    "The Epic evidence manifest pins all relevant source/data/code/config/model/calibrator/split/cutoff/runtime/hardware identities and preserves failures, null results, and unresolved limitations.",
    "Canonical/derived Jira views, live operational fields when connected, links, queues, release gates, and downstream states are synchronized and pass strict validation."
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
  "end_to_end_validation": "Exercise all child Story gates for Snapshot API, dashboard, explanations, analogs, and freshness-safe product and prove the integrated capability is safe and consumable by its downstream Epic/release path.",
  "epic_id": "",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-EPIC-013.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "AGGREGATE_GATE",
  "expected_maturity_after_completion": "OPERATING",
  "expected_outputs": [
    "artifacts/product/snapshot_repository_test.json",
    "docs/product/OPENAPI_SNAPSHOT.json",
    "artifacts/product/api_gate.json",
    "artifacts/product/dashboard_contract_test.json",
    "artifacts/product/bas_presentation_validation.json",
    "artifacts/product/dashboard_gate.json",
    "artifacts/product/explanation_analog_validation.json",
    "artifacts/product/product_performance_benchmark.json",
    "artifacts/product/PRODUCT_READINESS.json"
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
  "generated_markdown": "jira/issues/epics/POST-EPIC-013_snapshot_api_dashboard_explanations_analogs_and_freshness_safe_product.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-123",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100046,
  "in_scope": [
    "Child implementation and evidence work",
    "Cross-domain hard dependencies",
    "Integrated end-to-end gate",
    "Preservation of source authority and protected controls"
  ],
  "issue_type": "Epic",
  "jira_key": "BAT-46",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "product"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-EPIC-013",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Serve the predictive system and witty BAS experience from immutable approved snapshots with truthful freshness, uncertainty, provenance, accessibility, and no live recomputation drift.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24186",
    "jira_updated_at": "2026-08-09T23:23:53.809-0500",
    "last_synced_at": "2026-08-11T06:07:11.607568+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\JIRA-LIVE-CATCHUP-20260811\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Declaring child code sufficient without integrated evidence",
    "Changing protected requirements or ADRs without governance review",
    "Creating Wave 26"
  ],
  "owner_wave": "POST_W25",
  "parent_id": "",
  "phase": "PHASE-4",
  "prerequisites": [
    "Completion of POST-SUBTASK-111"
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
    "Verified Story gate decisions for POST-SUBTASK-117, POST-SUBTASK-120, POST-SUBTASK-123.",
    "Epic-level integrated execution/review evidence demonstrating actual downstream consumption and safe failure behavior.",
    "A residual-risk/blocker disposition and maturity/evidence claim audit tied to exact artifact and runtime identities."
  ],
  "required_tests": [
    {
      "classification": "END_TO_END",
      "expectation": "Story gate `POST-SUBTASK-117` must complete with verified evidence before Epic completion.",
      "path": "POST-SUBTASK-117",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Story gate `POST-SUBTASK-120` must complete with verified evidence before Epic completion.",
      "path": "POST-SUBTASK-120",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Story gate `POST-SUBTASK-123` must complete with verified evidence before Epic completion.",
      "path": "POST-SUBTASK-123",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "REPRODUCIBILITY",
      "expectation": "Aggregate all Story gates, artifact identities, residual blockers, accepted risks, and downstream readiness.",
      "path": "EPIC_EVIDENCE_MANIFEST",
      "validation_class": "REPRODUCIBILITY"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "Children may appear complete while integration remains unproven",
    "Upstream data/rights/hardware evidence may remain unavailable"
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "All Stories and Subtasks under this Epic for the product domain, including its explicit integrated completion gate.",
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
  "specificity_fingerprint": "88c1712bfc7e1d9e5864a32df07dfd84b365194eeb187632021c354de4b9ef7a",
  "stop_conditions": [
    "Stop before execution if any hard dependency, protected gate, source-rights decision, or target-resource precondition is unresolved."
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
  "title": "[POST-EPIC-013] Snapshot API, dashboard, explanations, analogs, and freshness-safe product",
  "traceability_inherited_from": [
    "POST-SUBTASK-123"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "END_TO_END",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "The final W25 handoff identifies this capability as necessary to move from accepted design/functional starters to evidence-backed implementation, empirical validation, production readiness, or operation.",
  "work_packet_path": "jira/ai/work_packets/POST-EPIC-013.md",
  "workflow_state": "BACKLOG"
}
```

## Objective

Serve the predictive system and witty BAS experience from immutable approved snapshots with truthful freshness, uncertainty, provenance, accessibility, and no live recomputation drift.

## Why This Exists

The final W25 handoff identifies this capability as necessary to move from accepted design/functional starters to evidence-backed implementation, empirical validation, production readiness, or operation.

## Scope

All Stories and Subtasks under this Epic for the product domain, including its explicit integrated completion gate.

### Explicit In Scope

- Child implementation and evidence work
- Cross-domain hard dependencies
- Integrated end-to-end gate
- Preservation of source authority and protected controls

### Explicit Out of Scope

- Declaring child code sufficient without integrated evidence
- Changing protected requirements or ADRs without governance review
- Creating Wave 26

## Prerequisites

- Completion of POST-SUBTASK-111

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
- artifacts/product/dashboard_contract_test.json
- artifacts/product/bas_presentation_validation.json
- artifacts/product/dashboard_gate.json
- artifacts/product/explanation_analog_validation.json
- artifacts/product/product_performance_benchmark.json
- artifacts/product/PRODUCT_READINESS.json

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

1. Every child issue completes at its declared maturity and evidence state, or has an explicit accepted-risk/deferred disposition.
2. The Epic's end-to-end gate proves the integrated capability on the required real data, target host, protected chronology, or operating path; file existence alone is insufficient.
3. All requirement, acceptance-control, ADR, risk, gap, test, artifact, and source references remain valid and no protected invariant is weakened.

## Definition of Done

1. Every child Story POST-STORY-039, POST-STORY-040, POST-STORY-041 is completed through its explicit end-to-end gate or has an explicit accepted-risk/deferred/cancelled disposition consistent with release governance.
2. The Epic integrated capability is demonstrated on the required real data, chronology, target host, product path, or operating path; planning, code, fixtures, or unit tests alone cannot satisfy it.
3. All direct and inherited requirement/control/ADR/risk/gap mappings resolve, all release-blocking controls have current evidence, and no protected invariant is weakened.
4. The Epic evidence manifest pins all relevant source/data/code/config/model/calibrator/split/cutoff/runtime/hardware identities and preserves failures, null results, and unresolved limitations.
5. Canonical/derived Jira views, live operational fields when connected, links, queues, release gates, and downstream states are synchronized and pass strict validation.

## Required Tests / Validation

- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-117` — Story gate `POST-SUBTASK-117` must complete with verified evidence before Epic completion.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-120` — Story gate `POST-SUBTASK-120` must complete with verified evidence before Epic completion.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-123` — Story gate `POST-SUBTASK-123` must complete with verified evidence before Epic completion.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `EPIC_EVIDENCE_MANIFEST` — Aggregate all Story gates, artifact identities, residual blockers, accepted risks, and downstream readiness.

## Required Evidence

- Verified Story gate decisions for POST-SUBTASK-117, POST-SUBTASK-120, POST-SUBTASK-123.
- Epic-level integrated execution/review evidence demonstrating actual downstream consumption and safe failure behavior.
- A residual-risk/blocker disposition and maturity/evidence claim audit tied to exact artifact and runtime identities.

## Completion Evidence Contract

```json
{
  "governance_traceability_gate": "POST-SUBTASK-123",
  "integrated_proof_required": true,
  "story_gates": [
    "POST-SUBTASK-117",
    "POST-SUBTASK-120",
    "POST-SUBTASK-123"
  ]
}
```

## End-to-End Validation Requirement

Exercise all child Story gates for Snapshot API, dashboard, explanations, analogs, and freshness-safe product and prove the integrated capability is safe and consumable by its downstream Epic/release path.

## Expected Maturity After Completion

`OPERATING`

## Risk / Failure Conditions

- Children may appear complete while integration remains unproven
- Upstream data/rights/hardware evidence may remain unavailable

## Stop Conditions

- Stop before execution if any hard dependency, protected gate, source-rights decision, or target-resource precondition is unresolved.

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

- Select child Subtasks from READY_QUEUE.csv; do not execute an Epic directly.
- Epic Done requires the final child gate and downstream-consumption evidence, not merely closed children.

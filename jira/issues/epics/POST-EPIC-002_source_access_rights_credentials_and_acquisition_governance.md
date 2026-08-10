<!-- GENERATED VIEW. Canonical record: jira/records/issues/epics/POST-EPIC-002_source_access_rights_credentials_and_acquisition_governance.json -->
# POST-EPIC-002 — [POST-EPIC-002] Source access, credentials, private-research acquisition, and publication governance

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
    "artifacts/jira_evidence/POST-EPIC-002.json"
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/epics/POST-EPIC-002_source_access_rights_credentials_and_acquisition_governance.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "governance_traceability_gate": "POST-SUBTASK-024",
    "integrated_proof_required": true,
    "story_gates": [
      "POST-SUBTASK-015",
      "POST-SUBTASK-018",
      "POST-SUBTASK-021",
      "POST-SUBTASK-024"
    ]
  },
  "component": "data-sources",
  "components_expected_to_be_touched": [
    "data-sources",
    "sources"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "Every child Story POST-STORY-005, POST-STORY-006, POST-STORY-007, POST-STORY-008 is completed through its explicit end-to-end gate or has an explicit accepted-risk/deferred/cancelled disposition consistent with release governance.",
    "The Epic integrated capability is demonstrated on the required real data, chronology, target host, product path, or operating path; planning, code, fixtures, or unit tests alone cannot satisfy it.",
    "All direct and inherited requirement/control/ADR/risk/gap mappings resolve, all release-blocking controls have current evidence, and no protected invariant is weakened.",
    "The Epic evidence manifest pins all relevant source/data/code/config/model/calibrator/split/cutoff/runtime/hardware identities and preserves failures, null results, and unresolved limitations.",
    "Canonical/derived Jira views, live operational fields when connected, links, queues, release gates, and downstream states are synchronized and pass strict validation."
  ],
  "dependencies": [],
  "effective_traceability_counts": {
    "acceptance_control_ids": 1,
    "adr_ids": 4,
    "gap_ids": 1,
    "requirement_ids": 9,
    "risk_ids": 1
  },
  "effective_traceability_total": 16,
  "end_to_end_validation": "Exercise all child Story gates for Source access, credentials, private-research acquisition, and publication governance and prove the integrated capability is safe and consumable by its downstream Epic/release path.",
  "epic_id": "",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-EPIC-002.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "AGGREGATE_GATE",
  "expected_maturity_after_completion": "EMPIRICALLY_VALIDATED",
  "expected_outputs": [
    "artifacts/source_governance/production_source_inventory.csv",
    "artifacts/source_governance/source_priority_decisions.json",
    "artifacts/source_governance/source_inventory_validation.json",
    "artifacts/source_governance/tier1_rights_decisions.csv",
    "artifacts/source_governance/supplemental_rights_decisions.csv",
    "configs/source_rights_registry.json",
    "artifacts/source_governance/source_rights_gate_test.json",
    "docs/operations/SOURCE_CREDENTIAL_CONTRACT.md",
    "artifacts/source_governance/credential_contract.redacted.json",
    "artifacts/source_governance/source_access_smoke_results.json",
    "artifacts/source_governance/source_access_readiness.csv",
    "configs/source_acquisition_registry.json",
    "artifacts/source_governance/acquisition_resilience_test.json",
    "artifacts/source_governance/source_drift_baseline.json",
    "configs/source_drift_registry.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/data/adapters.py",
    "docs/data_research/w06/DATA_ACQUISITION_PLAN.md",
    "docs/data_research/w06/SOURCE_ACCESS_LICENSE_MATRIX.csv",
    "docs/data_research/w06/SOURCE_PRIORITY_DECISIONS.md",
    "docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/data/adapters.py",
    "docs/data_research/w06/DATA_ACQUISITION_PLAN.md",
    "docs/data_research/w06/SOURCE_ACCESS_LICENSE_MATRIX.csv",
    "docs/data_research/w06/SOURCE_PRIORITY_DECISIONS.md",
    "docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/epics/POST-EPIC-002_source_access_rights_credentials_and_acquisition_governance.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-024",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100035,
  "in_scope": [
    "Child implementation and evidence work",
    "Cross-domain hard dependencies",
    "Integrated end-to-end gate",
    "Preservation of source authority and protected controls"
  ],
  "issue_type": "Epic",
  "jira_key": "BAT-35",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "sources"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-EPIC-002",
  "maturity_before": "CONTRACT_DEFINED",
  "objective": "Convert the researched source universe into technically operable private-research acquisition lanes with explicit credentials, provenance, rate limits, fallbacks, quality gates, and a no-raw-publication boundary.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24175",
    "jira_updated_at": "2026-08-09T15:42:07.867-0500",
    "last_synced_at": "2026-08-10T04:24:34.496382+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\BAT-516-openai-foundation-complete\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
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
  "phase": "PHASE-1",
  "prerequisites": [],
  "primary_source_refs": [
    "SRCREF-02007",
    "SRCREF-02008",
    "SRCREF-02009",
    "SRCREF-02010"
  ],
  "priority": "P0",
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
    "src/aggie_analytics/data/adapters.py",
    "docs/data_research/w06/DATA_ACQUISITION_PLAN.md",
    "docs/data_research/w06/SOURCE_ACCESS_LICENSE_MATRIX.csv",
    "docs/data_research/w06/SOURCE_PRIORITY_DECISIONS.md",
    "docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "Verified Story gate decisions for POST-SUBTASK-015, POST-SUBTASK-018, POST-SUBTASK-021, POST-SUBTASK-024.",
    "Epic-level integrated execution/review evidence demonstrating actual downstream consumption and safe failure behavior.",
    "A residual-risk/blocker disposition and maturity/evidence claim audit tied to exact artifact and runtime identities."
  ],
  "required_tests": [
    {
      "classification": "END_TO_END",
      "expectation": "Story gate `POST-SUBTASK-015` must complete with verified evidence before Epic completion.",
      "path": "POST-SUBTASK-015",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Story gate `POST-SUBTASK-018` must complete with verified evidence before Epic completion.",
      "path": "POST-SUBTASK-018",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Story gate `POST-SUBTASK-021` must complete with verified evidence before Epic completion.",
      "path": "POST-SUBTASK-021",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Story gate `POST-SUBTASK-024` must complete with verified evidence before Epic completion.",
      "path": "POST-SUBTASK-024",
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
  "scope": "All Stories and Subtasks under this Epic for the sources domain, including its explicit integrated completion gate.",
  "source_ids": [
    "GAP-010",
    "HANDOFF-002",
    "HANDOFF-012"
  ],
  "source_refs": [
    "SRCREF-02007",
    "SRCREF-02008",
    "SRCREF-02009",
    "SRCREF-02010",
    "SRCREF-02011",
    "SRCREF-02012",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01888",
    "SRCREF-01898",
    "SRCREF-01572"
  ],
  "specificity_fingerprint": "c0d04dd727e0f628ce0909817f8bfb361695776a19c6ed568438edc81edd47ad",
  "stop_conditions": [
    "Stop before execution if any hard dependency, protected gate, source-rights decision, or target-resource precondition is unresolved."
  ],
  "supporting_source_refs": [
    "SRCREF-02011",
    "SRCREF-02012",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01888",
    "SRCREF-01898",
    "SRCREF-01572"
  ],
  "title": "[POST-EPIC-002] Source access, credentials, private-research acquisition, and publication governance",
  "traceability_inherited_from": [
    "POST-SUBTASK-024"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "END_TO_END",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "The final W25 handoff identifies this capability as necessary to move from accepted design/functional starters to evidence-backed implementation, empirical validation, production readiness, or operation.",
  "work_packet_path": "jira/ai/work_packets/POST-EPIC-002.md",
  "workflow_state": "BACKLOG"
}
```

## Objective

Convert the researched source universe into technically operable private-research acquisition lanes with explicit credentials, provenance, rate limits, fallbacks, quality gates, and a no-raw-publication boundary.

## Why This Exists

The final W25 handoff identifies this capability as necessary to move from accepted design/functional starters to evidence-backed implementation, empirical validation, production readiness, or operation.

## Scope

All Stories and Subtasks under this Epic for the sources domain, including its explicit integrated completion gate.

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

- None.

## Hard Dependencies

- None.

## Blocks

- None.

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/data/adapters.py
- docs/data_research/w06/DATA_ACQUISITION_PLAN.md
- docs/data_research/w06/SOURCE_ACCESS_LICENSE_MATRIX.csv
- docs/data_research/w06/SOURCE_PRIORITY_DECISIONS.md
- docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- data-sources
- sources

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

- artifacts/source_governance/production_source_inventory.csv
- artifacts/source_governance/source_priority_decisions.json
- artifacts/source_governance/source_inventory_validation.json
- artifacts/source_governance/tier1_rights_decisions.csv
- artifacts/source_governance/supplemental_rights_decisions.csv
- configs/source_rights_registry.json
- artifacts/source_governance/source_rights_gate_test.json
- docs/operations/SOURCE_CREDENTIAL_CONTRACT.md
- artifacts/source_governance/credential_contract.redacted.json
- artifacts/source_governance/source_access_smoke_results.json
- artifacts/source_governance/source_access_readiness.csv
- configs/source_acquisition_registry.json
- artifacts/source_governance/acquisition_resilience_test.json
- artifacts/source_governance/source_drift_baseline.json
- configs/source_drift_registry.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-024`
- Inherited from: POST-SUBTASK-024
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 1, "adr_ids": 4, "gap_ids": 1, "requirement_ids": 9, "risk_ids": 1}`

## Acceptance Criteria

1. Every child issue completes at its declared maturity and evidence state, or has an explicit accepted-risk/deferred disposition.
2. The Epic's end-to-end gate proves the integrated capability on the required real data, target host, protected chronology, or operating path; file existence alone is insufficient.
3. All requirement, acceptance-control, ADR, risk, gap, test, artifact, and source references remain valid and no protected invariant is weakened.

## Definition of Done

1. Every child Story POST-STORY-005, POST-STORY-006, POST-STORY-007, POST-STORY-008 is completed through its explicit end-to-end gate or has an explicit accepted-risk/deferred/cancelled disposition consistent with release governance.
2. The Epic integrated capability is demonstrated on the required real data, chronology, target host, product path, or operating path; planning, code, fixtures, or unit tests alone cannot satisfy it.
3. All direct and inherited requirement/control/ADR/risk/gap mappings resolve, all release-blocking controls have current evidence, and no protected invariant is weakened.
4. The Epic evidence manifest pins all relevant source/data/code/config/model/calibrator/split/cutoff/runtime/hardware identities and preserves failures, null results, and unresolved limitations.
5. Canonical/derived Jira views, live operational fields when connected, links, queues, release gates, and downstream states are synchronized and pass strict validation.

## Required Tests / Validation

- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-015` — Story gate `POST-SUBTASK-015` must complete with verified evidence before Epic completion.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-018` — Story gate `POST-SUBTASK-018` must complete with verified evidence before Epic completion.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-021` — Story gate `POST-SUBTASK-021` must complete with verified evidence before Epic completion.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-024` — Story gate `POST-SUBTASK-024` must complete with verified evidence before Epic completion.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `EPIC_EVIDENCE_MANIFEST` — Aggregate all Story gates, artifact identities, residual blockers, accepted risks, and downstream readiness.

## Required Evidence

- Verified Story gate decisions for POST-SUBTASK-015, POST-SUBTASK-018, POST-SUBTASK-021, POST-SUBTASK-024.
- Epic-level integrated execution/review evidence demonstrating actual downstream consumption and safe failure behavior.
- A residual-risk/blocker disposition and maturity/evidence claim audit tied to exact artifact and runtime identities.

## Completion Evidence Contract

```json
{
  "governance_traceability_gate": "POST-SUBTASK-024",
  "integrated_proof_required": true,
  "story_gates": [
    "POST-SUBTASK-015",
    "POST-SUBTASK-018",
    "POST-SUBTASK-021",
    "POST-SUBTASK-024"
  ]
}
```

## End-to-End Validation Requirement

Exercise all child Story gates for Source access, credentials, private-research acquisition, and publication governance and prove the integrated capability is safe and consumable by its downstream Epic/release path.

## Expected Maturity After Completion

`EMPIRICALLY_VALIDATED`

## Risk / Failure Conditions

- Children may appear complete while integration remains unproven
- Upstream data/rights/hardware evidence may remain unavailable

## Stop Conditions

- Stop before execution if any hard dependency, protected gate, source-rights decision, or target-resource precondition is unresolved.

## Source References

- SRCREF-02007
- SRCREF-02008
- SRCREF-02009
- SRCREF-02010
- SRCREF-02011
- SRCREF-02012
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01888
- SRCREF-01898
- SRCREF-01572

## AI Context Notes

- Select child Subtasks from READY_QUEUE.csv; do not execute an Epic directly.
- Epic Done requires the final child gate and downstream-consumption evidence, not merely closed children.

<!-- GENERATED VIEW. Canonical record: jira/records/issues/epics/POST-EPIC-003_immutable_national_historical_data_materialization.json -->
# POST-EPIC-003 — [POST-EPIC-003] Immutable national historical data materialization

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
    "artifacts/jira_evidence/POST-EPIC-003.json"
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/epics/POST-EPIC-003_immutable_national_historical_data_materialization.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "governance_traceability_gate": "POST-SUBTASK-033",
    "integrated_proof_required": true,
    "story_gates": [
      "POST-SUBTASK-027",
      "POST-SUBTASK-030",
      "POST-SUBTASK-033"
    ]
  },
  "component": "raw-snapshots",
  "components_expected_to_be_touched": [
    "raw-snapshots",
    "raw-data"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "Every child Story POST-STORY-009, POST-STORY-010, POST-STORY-011 is completed through its explicit end-to-end gate or has an explicit accepted-risk/deferred/cancelled disposition consistent with release governance.",
    "The Epic integrated capability is demonstrated on the required real data, chronology, target host, product path, or operating path; planning, code, fixtures, or unit tests alone cannot satisfy it.",
    "All direct and inherited requirement/control/ADR/risk/gap mappings resolve, all release-blocking controls have current evidence, and no protected invariant is weakened.",
    "The Epic evidence manifest pins all relevant source/data/code/config/model/calibrator/split/cutoff/runtime/hardware identities and preserves failures, null results, and unresolved limitations.",
    "Canonical/derived Jira views, live operational fields when connected, links, queues, release gates, and downstream states are synchronized and pass strict validation."
  ],
  "dependencies": [
    "POST-SUBTASK-024"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 4,
    "adr_ids": 6,
    "gap_ids": 1,
    "requirement_ids": 8,
    "risk_ids": 5
  },
  "effective_traceability_total": 24,
  "end_to_end_validation": "Exercise all child Story gates for Immutable national historical data materialization and prove the integrated capability is safe and consumable by its downstream Epic/release path.",
  "epic_id": "",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-EPIC-003.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "AGGREGATE_GATE",
  "expected_maturity_after_completion": "EMPIRICALLY_VALIDATED",
  "expected_outputs": [
    "artifacts/data_lake/core_acquisition_manifest.json",
    "artifacts/data_lake/core_normalization_report.json",
    "artifacts/data_lake/core_coverage_gate.json",
    "artifacts/data_lake/context_acquisition_manifest.json",
    "artifacts/data_lake/context_population_profile.json",
    "artifacts/data_lake/context_eligibility_gate.json",
    "artifacts/data_lake/immutability_and_correction_test.json",
    "artifacts/data_lake/NATIONAL_DATA_LAKE_MANIFEST.json",
    "artifacts/data_lake/national_lake_readiness.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_w19_foundation.py",
    "src/aggie_analytics/data/adapters.py",
    "src/aggie_analytics/data/contracts.py",
    "src/aggie_analytics/data/snapshots.py",
    "docs/101_W19_FOUNDATION_IMPLEMENTATION.md",
    "docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_w19_foundation.py",
    "src/aggie_analytics/data/adapters.py",
    "src/aggie_analytics/data/contracts.py",
    "src/aggie_analytics/data/snapshots.py",
    "docs/101_W19_FOUNDATION_IMPLEMENTATION.md",
    "docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/epics/POST-EPIC-003_immutable_national_historical_data_materialization.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-033",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100036,
  "in_scope": [
    "Child implementation and evidence work",
    "Cross-domain hard dependencies",
    "Integrated end-to-end gate",
    "Preservation of source authority and protected controls"
  ],
  "issue_type": "Epic",
  "jira_key": "BAT-36",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "raw-data"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-EPIC-003",
  "maturity_before": "SCAFFOLD",
  "objective": "Acquire maximum quality-supported national history into immutable, content-addressed raw snapshots with population-level coverage and provenance evidence; source rights metadata is nonblocking for private research.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24176",
    "jira_updated_at": "2026-08-09T00:03:27.230-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
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
  "prerequisites": [
    "Completion of POST-SUBTASK-024"
  ],
  "primary_source_refs": [
    "SRCREF-02013",
    "SRCREF-02014",
    "SRCREF-02015",
    "SRCREF-02016"
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
    "tests/test_w19_foundation.py",
    "src/aggie_analytics/data/adapters.py",
    "src/aggie_analytics/data/contracts.py",
    "src/aggie_analytics/data/snapshots.py",
    "docs/101_W19_FOUNDATION_IMPLEMENTATION.md",
    "docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "Verified Story gate decisions for POST-SUBTASK-027, POST-SUBTASK-030, POST-SUBTASK-033.",
    "Epic-level integrated execution/review evidence demonstrating actual downstream consumption and safe failure behavior.",
    "A residual-risk/blocker disposition and maturity/evidence claim audit tied to exact artifact and runtime identities."
  ],
  "required_tests": [
    {
      "classification": "END_TO_END",
      "expectation": "Story gate `POST-SUBTASK-027` must complete with verified evidence before Epic completion.",
      "path": "POST-SUBTASK-027",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Story gate `POST-SUBTASK-030` must complete with verified evidence before Epic completion.",
      "path": "POST-SUBTASK-030",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Story gate `POST-SUBTASK-033` must complete with verified evidence before Epic completion.",
      "path": "POST-SUBTASK-033",
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
  "scope": "All Stories and Subtasks under this Epic for the raw-data domain, including its explicit integrated completion gate.",
  "source_ids": [
    "GAP-002",
    "HANDOFF-003"
  ],
  "source_refs": [
    "SRCREF-02013",
    "SRCREF-02014",
    "SRCREF-02015",
    "SRCREF-02016",
    "SRCREF-02017",
    "SRCREF-02018",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01889",
    "SRCREF-01564"
  ],
  "specificity_fingerprint": "7bf97215d4766340d9a9d1c4b65bea8ead27c0c6dc8acfaf8688baa53a207654",
  "stop_conditions": [
    "Stop before execution if any hard dependency, protected gate, source-rights decision, or target-resource precondition is unresolved."
  ],
  "supporting_source_refs": [
    "SRCREF-02017",
    "SRCREF-02018",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01889",
    "SRCREF-01564"
  ],
  "title": "[POST-EPIC-003] Immutable national historical data materialization",
  "traceability_inherited_from": [
    "POST-SUBTASK-033"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "END_TO_END",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "The final W25 handoff identifies this capability as necessary to move from accepted design/functional starters to evidence-backed implementation, empirical validation, production readiness, or operation.",
  "work_packet_path": "jira/ai/work_packets/POST-EPIC-003.md",
  "workflow_state": "BACKLOG"
}
```

## Objective

Acquire maximum quality-supported national history into immutable, content-addressed raw snapshots with population-level coverage and provenance evidence; source rights metadata is nonblocking for private research.

## Why This Exists

The final W25 handoff identifies this capability as necessary to move from accepted design/functional starters to evidence-backed implementation, empirical validation, production readiness, or operation.

## Scope

All Stories and Subtasks under this Epic for the raw-data domain, including its explicit integrated completion gate.

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

- Completion of POST-SUBTASK-024

## Hard Dependencies

- POST-SUBTASK-024

## Blocks

- None.

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_w19_foundation.py
- src/aggie_analytics/data/adapters.py
- src/aggie_analytics/data/contracts.py
- src/aggie_analytics/data/snapshots.py
- docs/101_W19_FOUNDATION_IMPLEMENTATION.md
- docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- raw-snapshots
- raw-data

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

- artifacts/data_lake/core_acquisition_manifest.json
- artifacts/data_lake/core_normalization_report.json
- artifacts/data_lake/core_coverage_gate.json
- artifacts/data_lake/context_acquisition_manifest.json
- artifacts/data_lake/context_population_profile.json
- artifacts/data_lake/context_eligibility_gate.json
- artifacts/data_lake/immutability_and_correction_test.json
- artifacts/data_lake/NATIONAL_DATA_LAKE_MANIFEST.json
- artifacts/data_lake/national_lake_readiness.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-033`
- Inherited from: POST-SUBTASK-033
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 4, "adr_ids": 6, "gap_ids": 1, "requirement_ids": 8, "risk_ids": 5}`

## Acceptance Criteria

1. Every child issue completes at its declared maturity and evidence state, or has an explicit accepted-risk/deferred disposition.
2. The Epic's end-to-end gate proves the integrated capability on the required real data, target host, protected chronology, or operating path; file existence alone is insufficient.
3. All requirement, acceptance-control, ADR, risk, gap, test, artifact, and source references remain valid and no protected invariant is weakened.

## Definition of Done

1. Every child Story POST-STORY-009, POST-STORY-010, POST-STORY-011 is completed through its explicit end-to-end gate or has an explicit accepted-risk/deferred/cancelled disposition consistent with release governance.
2. The Epic integrated capability is demonstrated on the required real data, chronology, target host, product path, or operating path; planning, code, fixtures, or unit tests alone cannot satisfy it.
3. All direct and inherited requirement/control/ADR/risk/gap mappings resolve, all release-blocking controls have current evidence, and no protected invariant is weakened.
4. The Epic evidence manifest pins all relevant source/data/code/config/model/calibrator/split/cutoff/runtime/hardware identities and preserves failures, null results, and unresolved limitations.
5. Canonical/derived Jira views, live operational fields when connected, links, queues, release gates, and downstream states are synchronized and pass strict validation.

## Required Tests / Validation

- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-027` — Story gate `POST-SUBTASK-027` must complete with verified evidence before Epic completion.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-030` — Story gate `POST-SUBTASK-030` must complete with verified evidence before Epic completion.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-033` — Story gate `POST-SUBTASK-033` must complete with verified evidence before Epic completion.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `EPIC_EVIDENCE_MANIFEST` — Aggregate all Story gates, artifact identities, residual blockers, accepted risks, and downstream readiness.

## Required Evidence

- Verified Story gate decisions for POST-SUBTASK-027, POST-SUBTASK-030, POST-SUBTASK-033.
- Epic-level integrated execution/review evidence demonstrating actual downstream consumption and safe failure behavior.
- A residual-risk/blocker disposition and maturity/evidence claim audit tied to exact artifact and runtime identities.

## Completion Evidence Contract

```json
{
  "governance_traceability_gate": "POST-SUBTASK-033",
  "integrated_proof_required": true,
  "story_gates": [
    "POST-SUBTASK-027",
    "POST-SUBTASK-030",
    "POST-SUBTASK-033"
  ]
}
```

## End-to-End Validation Requirement

Exercise all child Story gates for Immutable national historical data materialization and prove the integrated capability is safe and consumable by its downstream Epic/release path.

## Expected Maturity After Completion

`EMPIRICALLY_VALIDATED`

## Risk / Failure Conditions

- Children may appear complete while integration remains unproven
- Upstream data/rights/hardware evidence may remain unavailable

## Stop Conditions

- Stop before execution if any hard dependency, protected gate, source-rights decision, or target-resource precondition is unresolved.

## Source References

- SRCREF-02013
- SRCREF-02014
- SRCREF-02015
- SRCREF-02016
- SRCREF-02017
- SRCREF-02018
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01889
- SRCREF-01564

## AI Context Notes

- Select child Subtasks from READY_QUEUE.csv; do not execute an Epic directly.
- Epic Done requires the final child gate and downstream-consumption evidence, not merely closed children.

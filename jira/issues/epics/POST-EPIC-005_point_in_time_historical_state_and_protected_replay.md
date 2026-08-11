<!-- GENERATED VIEW. Canonical record: jira/records/issues/epics/POST-EPIC-005_point_in_time_historical_state_and_protected_replay.json -->
# POST-EPIC-005 — [POST-EPIC-005] Point-in-time historical state and protected replay

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
    "artifacts/jira_evidence/POST-EPIC-005.json"
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/epics/POST-EPIC-005_point_in_time_historical_state_and_protected_replay.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "governance_traceability_gate": "POST-SUBTASK-051",
    "integrated_proof_required": true,
    "story_gates": [
      "POST-SUBTASK-045",
      "POST-SUBTASK-048",
      "POST-SUBTASK-051"
    ]
  },
  "component": "pit-temporal",
  "components_expected_to_be_touched": [
    "pit-temporal",
    "pit"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "Every child Story POST-STORY-015, POST-STORY-016, POST-STORY-017 is completed through its explicit end-to-end gate or has an explicit accepted-risk/deferred/cancelled disposition consistent with release governance.",
    "The Epic integrated capability is demonstrated on the required real data, chronology, target host, product path, or operating path; planning, code, fixtures, or unit tests alone cannot satisfy it.",
    "All direct and inherited requirement/control/ADR/risk/gap mappings resolve, all release-blocking controls have current evidence, and no protected invariant is weakened.",
    "The Epic evidence manifest pins all relevant source/data/code/config/model/calibrator/split/cutoff/runtime/hardware identities and preserves failures, null results, and unresolved limitations.",
    "Canonical/derived Jira views, live operational fields when connected, links, queues, release gates, and downstream states are synchronized and pass strict validation."
  ],
  "dependencies": [
    "POST-SUBTASK-042"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 1,
    "adr_ids": 8,
    "gap_ids": 1,
    "requirement_ids": 14,
    "risk_ids": 7
  },
  "effective_traceability_total": 31,
  "end_to_end_validation": "Exercise all child Story gates for Point-in-time historical state and protected replay and prove the integrated capability is safe and consumable by its downstream Epic/release path.",
  "epic_id": "",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-EPIC-005.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "AGGREGATE_GATE",
  "expected_maturity_after_completion": "EMPIRICALLY_VALIDATED",
  "expected_outputs": [
    "configs/known_at_registry.json",
    "artifacts/pit/timestamp_normalization_report.json",
    "artifacts/pit/known_at_gate.json",
    "artifacts/pit/asof_state_manifest.json",
    "artifacts/pit/pregame_matrix_manifest.json",
    "artifacts/pit/matrix_gate_decision.json",
    "artifacts/pit/leakage_battery_results.json",
    "artifacts/pit/protected_replay_dry_run.json",
    "artifacts/pit/PIT_REPLAY_READINESS.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_temporal_governance.py",
    "tests/test_w24_readiness.py",
    "src/aggie_analytics/temporal/eligibility.py",
    "src/aggie_analytics/temporal/state.py",
    "docs/readiness/W24_END_TO_END_READINESS.md",
    "docs/18_POINT_IN_TIME_DATA_ARCHITECTURE.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_temporal_governance.py",
    "tests/test_w24_readiness.py",
    "src/aggie_analytics/temporal/eligibility.py",
    "src/aggie_analytics/temporal/state.py",
    "docs/readiness/W24_END_TO_END_READINESS.md",
    "docs/18_POINT_IN_TIME_DATA_ARCHITECTURE.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/epics/POST-EPIC-005_point_in_time_historical_state_and_protected_replay.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-051",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100038,
  "in_scope": [
    "Child implementation and evidence work",
    "Cross-domain hard dependencies",
    "Integrated end-to-end gate",
    "Preservation of source authority and protected controls"
  ],
  "issue_type": "Epic",
  "jira_key": "BAT-38",
  "labels": [
    "actionable",
    "core-release",
    "pit",
    "post-wave"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-EPIC-005",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Build fail-closed known-at semantics, append-only as-of state, pregame matrices, leakage batteries, and chronological replay from real history.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24178",
    "jira_updated_at": "2026-08-09T23:23:52.819-0500",
    "last_synced_at": "2026-08-11T06:30:01.758065+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\POST-SUBTASK-177-play-drive-preliminary\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
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
    "Completion of POST-SUBTASK-042"
  ],
  "primary_source_refs": [
    "SRCREF-02025",
    "SRCREF-02026",
    "SRCREF-02027",
    "SRCREF-02028"
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
    "tests/test_temporal_governance.py",
    "tests/test_w24_readiness.py",
    "src/aggie_analytics/temporal/eligibility.py",
    "src/aggie_analytics/temporal/state.py",
    "docs/readiness/W24_END_TO_END_READINESS.md",
    "docs/18_POINT_IN_TIME_DATA_ARCHITECTURE.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "Verified Story gate decisions for POST-SUBTASK-045, POST-SUBTASK-048, POST-SUBTASK-051.",
    "Epic-level integrated execution/review evidence demonstrating actual downstream consumption and safe failure behavior.",
    "A residual-risk/blocker disposition and maturity/evidence claim audit tied to exact artifact and runtime identities."
  ],
  "required_tests": [
    {
      "classification": "END_TO_END",
      "expectation": "Story gate `POST-SUBTASK-045` must complete with verified evidence before Epic completion.",
      "path": "POST-SUBTASK-045",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Story gate `POST-SUBTASK-048` must complete with verified evidence before Epic completion.",
      "path": "POST-SUBTASK-048",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Story gate `POST-SUBTASK-051` must complete with verified evidence before Epic completion.",
      "path": "POST-SUBTASK-051",
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
  "scope": "All Stories and Subtasks under this Epic for the pit domain, including its explicit integrated completion gate.",
  "source_ids": [
    "GAP-005",
    "HANDOFF-004"
  ],
  "source_refs": [
    "SRCREF-02025",
    "SRCREF-02026",
    "SRCREF-02027",
    "SRCREF-02028",
    "SRCREF-02029",
    "SRCREF-02030",
    "SRCREF-02031",
    "SRCREF-02032",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01890",
    "SRCREF-01567"
  ],
  "specificity_fingerprint": "a3478250085b4ebbdb77910610c5361cb432796b5ec613d3fddf814a58ad1861",
  "stop_conditions": [
    "Stop before execution if any hard dependency, protected gate, source-rights decision, or target-resource precondition is unresolved."
  ],
  "supporting_source_refs": [
    "SRCREF-02029",
    "SRCREF-02030",
    "SRCREF-02031",
    "SRCREF-02032",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01890",
    "SRCREF-01567"
  ],
  "title": "[POST-EPIC-005] Point-in-time historical state and protected replay",
  "traceability_inherited_from": [
    "POST-SUBTASK-051"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "END_TO_END",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "The final W25 handoff identifies this capability as necessary to move from accepted design/functional starters to evidence-backed implementation, empirical validation, production readiness, or operation.",
  "work_packet_path": "jira/ai/work_packets/POST-EPIC-005.md",
  "workflow_state": "BACKLOG"
}
```

## Objective

Build fail-closed known-at semantics, append-only as-of state, pregame matrices, leakage batteries, and chronological replay from real history.

## Why This Exists

The final W25 handoff identifies this capability as necessary to move from accepted design/functional starters to evidence-backed implementation, empirical validation, production readiness, or operation.

## Scope

All Stories and Subtasks under this Epic for the pit domain, including its explicit integrated completion gate.

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

- Completion of POST-SUBTASK-042

## Hard Dependencies

- POST-SUBTASK-042

## Blocks

- None.

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_temporal_governance.py
- tests/test_w24_readiness.py
- src/aggie_analytics/temporal/eligibility.py
- src/aggie_analytics/temporal/state.py
- docs/readiness/W24_END_TO_END_READINESS.md
- docs/18_POINT_IN_TIME_DATA_ARCHITECTURE.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- pit-temporal
- pit

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

- configs/known_at_registry.json
- artifacts/pit/timestamp_normalization_report.json
- artifacts/pit/known_at_gate.json
- artifacts/pit/asof_state_manifest.json
- artifacts/pit/pregame_matrix_manifest.json
- artifacts/pit/matrix_gate_decision.json
- artifacts/pit/leakage_battery_results.json
- artifacts/pit/protected_replay_dry_run.json
- artifacts/pit/PIT_REPLAY_READINESS.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-051`
- Inherited from: POST-SUBTASK-051
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 1, "adr_ids": 8, "gap_ids": 1, "requirement_ids": 14, "risk_ids": 7}`

## Acceptance Criteria

1. Every child issue completes at its declared maturity and evidence state, or has an explicit accepted-risk/deferred disposition.
2. The Epic's end-to-end gate proves the integrated capability on the required real data, target host, protected chronology, or operating path; file existence alone is insufficient.
3. All requirement, acceptance-control, ADR, risk, gap, test, artifact, and source references remain valid and no protected invariant is weakened.

## Definition of Done

1. Every child Story POST-STORY-015, POST-STORY-016, POST-STORY-017 is completed through its explicit end-to-end gate or has an explicit accepted-risk/deferred/cancelled disposition consistent with release governance.
2. The Epic integrated capability is demonstrated on the required real data, chronology, target host, product path, or operating path; planning, code, fixtures, or unit tests alone cannot satisfy it.
3. All direct and inherited requirement/control/ADR/risk/gap mappings resolve, all release-blocking controls have current evidence, and no protected invariant is weakened.
4. The Epic evidence manifest pins all relevant source/data/code/config/model/calibrator/split/cutoff/runtime/hardware identities and preserves failures, null results, and unresolved limitations.
5. Canonical/derived Jira views, live operational fields when connected, links, queues, release gates, and downstream states are synchronized and pass strict validation.

## Required Tests / Validation

- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-045` — Story gate `POST-SUBTASK-045` must complete with verified evidence before Epic completion.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-048` — Story gate `POST-SUBTASK-048` must complete with verified evidence before Epic completion.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-051` — Story gate `POST-SUBTASK-051` must complete with verified evidence before Epic completion.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `EPIC_EVIDENCE_MANIFEST` — Aggregate all Story gates, artifact identities, residual blockers, accepted risks, and downstream readiness.

## Required Evidence

- Verified Story gate decisions for POST-SUBTASK-045, POST-SUBTASK-048, POST-SUBTASK-051.
- Epic-level integrated execution/review evidence demonstrating actual downstream consumption and safe failure behavior.
- A residual-risk/blocker disposition and maturity/evidence claim audit tied to exact artifact and runtime identities.

## Completion Evidence Contract

```json
{
  "governance_traceability_gate": "POST-SUBTASK-051",
  "integrated_proof_required": true,
  "story_gates": [
    "POST-SUBTASK-045",
    "POST-SUBTASK-048",
    "POST-SUBTASK-051"
  ]
}
```

## End-to-End Validation Requirement

Exercise all child Story gates for Point-in-time historical state and protected replay and prove the integrated capability is safe and consumable by its downstream Epic/release path.

## Expected Maturity After Completion

`EMPIRICALLY_VALIDATED`

## Risk / Failure Conditions

- Children may appear complete while integration remains unproven
- Upstream data/rights/hardware evidence may remain unavailable

## Stop Conditions

- Stop before execution if any hard dependency, protected gate, source-rights decision, or target-resource precondition is unresolved.

## Source References

- SRCREF-02025
- SRCREF-02026
- SRCREF-02027
- SRCREF-02028
- SRCREF-02029
- SRCREF-02030
- SRCREF-02031
- SRCREF-02032
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01890
- SRCREF-01567

## AI Context Notes

- Select child Subtasks from READY_QUEUE.csv; do not execute an Epic directly.
- Epic Done requires the final child gate and downstream-consumption evidence, not merely closed children.

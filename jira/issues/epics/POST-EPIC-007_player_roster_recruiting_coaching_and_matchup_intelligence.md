<!-- GENERATED VIEW. Canonical record: jira/records/issues/epics/POST-EPIC-007_player_roster_recruiting_coaching_and_matchup_intelligence.json -->
# POST-EPIC-007 — [POST-EPIC-007] Player, roster, recruiting, coaching, and matchup intelligence

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
    "artifacts/jira_evidence/POST-EPIC-007.json"
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/epics/POST-EPIC-007_player_roster_recruiting_coaching_and_matchup_intelligence.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "governance_traceability_gate": "POST-SUBTASK-069",
    "integrated_proof_required": true,
    "story_gates": [
      "POST-SUBTASK-063",
      "POST-SUBTASK-066",
      "POST-SUBTASK-069"
    ]
  },
  "component": "player-context-intelligence",
  "components_expected_to_be_touched": [
    "player-context-intelligence",
    "advanced-football"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "Every child Story POST-STORY-021, POST-STORY-022, POST-STORY-023 is completed through its explicit end-to-end gate or has an explicit accepted-risk/deferred/cancelled disposition consistent with release governance.",
    "The Epic integrated capability is demonstrated on the required real data, chronology, target host, product path, or operating path; planning, code, fixtures, or unit tests alone cannot satisfy it.",
    "All direct and inherited requirement/control/ADR/risk/gap mappings resolve, all release-blocking controls have current evidence, and no protected invariant is weakened.",
    "The Epic evidence manifest pins all relevant source/data/code/config/model/calibrator/split/cutoff/runtime/hardware identities and preserves failures, null results, and unresolved limitations.",
    "Canonical/derived Jira views, live operational fields when connected, links, queues, release gates, and downstream states are synchronized and pass strict validation."
  ],
  "dependencies": [
    "POST-SUBTASK-030",
    "POST-SUBTASK-048"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 11,
    "adr_ids": 21,
    "gap_ids": 2,
    "requirement_ids": 59,
    "risk_ids": 23
  },
  "effective_traceability_total": 116,
  "end_to_end_validation": "Exercise all child Story gates for Player, roster, recruiting, coaching, and matchup intelligence and prove the integrated capability is safe and consumable by its downstream Epic/release path.",
  "epic_id": "",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-EPIC-007.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "AGGREGATE_GATE",
  "expected_maturity_after_completion": "EMPIRICALLY_VALIDATED",
  "expected_outputs": [
    "artifacts/player_intelligence/player_state_manifest.json",
    "artifacts/player_intelligence/player_value_availability_report.json",
    "artifacts/player_intelligence/player_intelligence_gate.json",
    "artifacts/player_intelligence/program_event_manifest.json",
    "artifacts/context_intelligence/program_feature_manifest.json",
    "artifacts/context_intelligence/program_intelligence_gate.json",
    "artifacts/context_intelligence/game_context_state_manifest.json",
    "artifacts/context_intelligence/mechanics_sparse_opponent_manifest.json",
    "artifacts/context_intelligence/context_gate.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/context_intelligence/context.py",
    "src/aggie_analytics/player_intelligence/advanced_state.py",
    "docs/29_COACHING_INTELLIGENCE_ARCHITECTURE.md",
    "docs/29_TEAM_STATE_ARCHITECTURE.md",
    "docs/32_GAME_MECHANICS_ARCHITECTURE.md",
    "docs/34_PLAYER_ROSTER_DEPTH_ARCHITECTURE.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/context_intelligence/context.py",
    "src/aggie_analytics/player_intelligence/advanced_state.py",
    "docs/29_COACHING_INTELLIGENCE_ARCHITECTURE.md",
    "docs/29_TEAM_STATE_ARCHITECTURE.md",
    "docs/32_GAME_MECHANICS_ARCHITECTURE.md",
    "docs/34_PLAYER_ROSTER_DEPTH_ARCHITECTURE.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/epics/POST-EPIC-007_player_roster_recruiting_coaching_and_matchup_intelligence.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-069",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100040,
  "in_scope": [
    "Child implementation and evidence work",
    "Cross-domain hard dependencies",
    "Integrated end-to-end gate",
    "Preservation of source authority and protected controls"
  ],
  "issue_type": "Epic",
  "jira_key": "BAT-40",
  "labels": [
    "actionable",
    "advanced-football",
    "core-release",
    "post-wave"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-EPIC-007",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Materialize higher-resolution football state required for credible availability-aware forecasts and A&M specialization while preserving uncertainty and source limits.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24180",
    "jira_updated_at": "2026-08-09T23:23:53.381-0500",
    "last_synced_at": "2026-08-11T07:44:24.297472+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\BAT-523-tamu-availability-pages\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
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
  "phase": "PHASE-2",
  "prerequisites": [
    "Completion of POST-SUBTASK-030",
    "Completion of POST-SUBTASK-048"
  ],
  "primary_source_refs": [
    "SRCREF-02041",
    "SRCREF-02042",
    "SRCREF-02043",
    "SRCREF-02044"
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
    "src/aggie_analytics/context_intelligence/context.py",
    "src/aggie_analytics/player_intelligence/advanced_state.py",
    "docs/29_COACHING_INTELLIGENCE_ARCHITECTURE.md",
    "docs/29_TEAM_STATE_ARCHITECTURE.md",
    "docs/32_GAME_MECHANICS_ARCHITECTURE.md",
    "docs/34_PLAYER_ROSTER_DEPTH_ARCHITECTURE.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "Verified Story gate decisions for POST-SUBTASK-063, POST-SUBTASK-066, POST-SUBTASK-069.",
    "Epic-level integrated execution/review evidence demonstrating actual downstream consumption and safe failure behavior.",
    "A residual-risk/blocker disposition and maturity/evidence claim audit tied to exact artifact and runtime identities."
  ],
  "required_tests": [
    {
      "classification": "END_TO_END",
      "expectation": "Story gate `POST-SUBTASK-063` must complete with verified evidence before Epic completion.",
      "path": "POST-SUBTASK-063",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Story gate `POST-SUBTASK-066` must complete with verified evidence before Epic completion.",
      "path": "POST-SUBTASK-066",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Story gate `POST-SUBTASK-069` must complete with verified evidence before Epic completion.",
      "path": "POST-SUBTASK-069",
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
  "scope": "All Stories and Subtasks under this Epic for the advanced-football domain, including its explicit integrated completion gate.",
  "source_ids": [
    "GAP-006",
    "HANDOFF-008"
  ],
  "source_refs": [
    "SRCREF-02041",
    "SRCREF-02042",
    "SRCREF-02043",
    "SRCREF-02044",
    "SRCREF-02045",
    "SRCREF-02046",
    "SRCREF-02047",
    "SRCREF-02048",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01894",
    "SRCREF-01568"
  ],
  "specificity_fingerprint": "4441b07b529fb416c6a1690e8cd9c0c5bdd276dd5fcc23d6c7e1ad000485d639",
  "stop_conditions": [
    "Stop before execution if any hard dependency, protected gate, source-rights decision, or target-resource precondition is unresolved."
  ],
  "supporting_source_refs": [
    "SRCREF-02045",
    "SRCREF-02046",
    "SRCREF-02047",
    "SRCREF-02048",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01894",
    "SRCREF-01568"
  ],
  "title": "[POST-EPIC-007] Player, roster, recruiting, coaching, and matchup intelligence",
  "traceability_inherited_from": [
    "POST-SUBTASK-069"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "END_TO_END",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "The final W25 handoff identifies this capability as necessary to move from accepted design/functional starters to evidence-backed implementation, empirical validation, production readiness, or operation.",
  "work_packet_path": "jira/ai/work_packets/POST-EPIC-007.md",
  "workflow_state": "BACKLOG"
}
```

## Objective

Materialize higher-resolution football state required for credible availability-aware forecasts and A&M specialization while preserving uncertainty and source limits.

## Why This Exists

The final W25 handoff identifies this capability as necessary to move from accepted design/functional starters to evidence-backed implementation, empirical validation, production readiness, or operation.

## Scope

All Stories and Subtasks under this Epic for the advanced-football domain, including its explicit integrated completion gate.

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

- Completion of POST-SUBTASK-030
- Completion of POST-SUBTASK-048

## Hard Dependencies

- POST-SUBTASK-030
- POST-SUBTASK-048

## Blocks

- None.

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/context_intelligence/context.py
- src/aggie_analytics/player_intelligence/advanced_state.py
- docs/29_COACHING_INTELLIGENCE_ARCHITECTURE.md
- docs/29_TEAM_STATE_ARCHITECTURE.md
- docs/32_GAME_MECHANICS_ARCHITECTURE.md
- docs/34_PLAYER_ROSTER_DEPTH_ARCHITECTURE.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- player-context-intelligence
- advanced-football

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

- artifacts/player_intelligence/player_state_manifest.json
- artifacts/player_intelligence/player_value_availability_report.json
- artifacts/player_intelligence/player_intelligence_gate.json
- artifacts/player_intelligence/program_event_manifest.json
- artifacts/context_intelligence/program_feature_manifest.json
- artifacts/context_intelligence/program_intelligence_gate.json
- artifacts/context_intelligence/game_context_state_manifest.json
- artifacts/context_intelligence/mechanics_sparse_opponent_manifest.json
- artifacts/context_intelligence/context_gate.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-069`
- Inherited from: POST-SUBTASK-069
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 11, "adr_ids": 21, "gap_ids": 2, "requirement_ids": 59, "risk_ids": 23}`

## Acceptance Criteria

1. Every child issue completes at its declared maturity and evidence state, or has an explicit accepted-risk/deferred disposition.
2. The Epic's end-to-end gate proves the integrated capability on the required real data, target host, protected chronology, or operating path; file existence alone is insufficient.
3. All requirement, acceptance-control, ADR, risk, gap, test, artifact, and source references remain valid and no protected invariant is weakened.

## Definition of Done

1. Every child Story POST-STORY-021, POST-STORY-022, POST-STORY-023 is completed through its explicit end-to-end gate or has an explicit accepted-risk/deferred/cancelled disposition consistent with release governance.
2. The Epic integrated capability is demonstrated on the required real data, chronology, target host, product path, or operating path; planning, code, fixtures, or unit tests alone cannot satisfy it.
3. All direct and inherited requirement/control/ADR/risk/gap mappings resolve, all release-blocking controls have current evidence, and no protected invariant is weakened.
4. The Epic evidence manifest pins all relevant source/data/code/config/model/calibrator/split/cutoff/runtime/hardware identities and preserves failures, null results, and unresolved limitations.
5. Canonical/derived Jira views, live operational fields when connected, links, queues, release gates, and downstream states are synchronized and pass strict validation.

## Required Tests / Validation

- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-063` — Story gate `POST-SUBTASK-063` must complete with verified evidence before Epic completion.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-066` — Story gate `POST-SUBTASK-066` must complete with verified evidence before Epic completion.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-069` — Story gate `POST-SUBTASK-069` must complete with verified evidence before Epic completion.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `EPIC_EVIDENCE_MANIFEST` — Aggregate all Story gates, artifact identities, residual blockers, accepted risks, and downstream readiness.

## Required Evidence

- Verified Story gate decisions for POST-SUBTASK-063, POST-SUBTASK-066, POST-SUBTASK-069.
- Epic-level integrated execution/review evidence demonstrating actual downstream consumption and safe failure behavior.
- A residual-risk/blocker disposition and maturity/evidence claim audit tied to exact artifact and runtime identities.

## Completion Evidence Contract

```json
{
  "governance_traceability_gate": "POST-SUBTASK-069",
  "integrated_proof_required": true,
  "story_gates": [
    "POST-SUBTASK-063",
    "POST-SUBTASK-066",
    "POST-SUBTASK-069"
  ]
}
```

## End-to-End Validation Requirement

Exercise all child Story gates for Player, roster, recruiting, coaching, and matchup intelligence and prove the integrated capability is safe and consumable by its downstream Epic/release path.

## Expected Maturity After Completion

`EMPIRICALLY_VALIDATED`

## Risk / Failure Conditions

- Children may appear complete while integration remains unproven
- Upstream data/rights/hardware evidence may remain unavailable

## Stop Conditions

- Stop before execution if any hard dependency, protected gate, source-rights decision, or target-resource precondition is unresolved.

## Source References

- SRCREF-02041
- SRCREF-02042
- SRCREF-02043
- SRCREF-02044
- SRCREF-02045
- SRCREF-02046
- SRCREF-02047
- SRCREF-02048
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01894
- SRCREF-01568

## AI Context Notes

- Select child Subtasks from READY_QUEUE.csv; do not execute an Epic directly.
- Epic Done requires the final child gate and downstream-consumption evidence, not merely closed children.

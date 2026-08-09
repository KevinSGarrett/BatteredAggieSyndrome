<!-- GENERATED VIEW. Canonical record: jira/records/issues/stories/POST-STORY-023_weather_travel_rest_venue_schedule_sequence_mechanics_officiating_and_sparse_opp.json -->
# POST-STORY-023 — [POST-STORY-023] Weather, travel, rest, venue, schedule sequence, mechanics, officiating, and sparse-opponent priors

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Weather uses forecast snapshots available at each cutoff; travel/rest/sequence derive from canonical schedules/venues and update for postponements/neutral sites with unknown coordinates left uncertain.",
    "The declared output `artifacts/context_intelligence/game_context_state_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "Mechanics/officiating/resource data are used only where rights/depth/timing support them, and lower-division opponents receive explicit decreasing-information priors rather than zero strength or dropped games.",
    "The declared output `artifacts/context_intelligence/mechanics_sparse_opponent_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Source spot checks, orientation, timing, sparse-opponent uncertainty, and unsupported-lane isolation pass before the context state is production eligible.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Open only this Story, its selected child, and referenced source sections; do not load the entire Jira pack.",
    "Story completion requires the gate Subtask, not only implementation children."
  ],
  "allowed_modification_paths": [
    "artifacts/jira_evidence/POST-STORY-023.json"
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/stories/POST-STORY-023_weather_travel_rest_venue_schedule_sequence_mechanics_officiating_and_sparse_opp.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "all_child_evidence_required": true,
    "child_gate": "POST-SUBTASK-069",
    "governance_traceability_gate": "POST-SUBTASK-069",
    "integrated_proof_required": true
  },
  "component": "player-context-intelligence",
  "components_expected_to_be_touched": [
    "player-context-intelligence",
    "advanced-football"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "All child subtasks POST-SUBTASK-067, POST-SUBTASK-068, POST-SUBTASK-069 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.",
    "The final gate `POST-SUBTASK-069` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.",
    "All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.",
    "The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.",
    "Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation."
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
  "end_to_end_validation": "A matchup snapshot reconstructs weather forecast, venue/travel/rest/sequence, supported mechanics, and sparse-opponent priors with honest uncertainty.",
  "epic_id": "POST-EPIC-007",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-STORY-023.json",
  "evidence_state": "PLANNED",
  "execution_lane": "SHARED_CONTRACT",
  "execution_mode": "AGGREGATE_GATE",
  "expected_maturity_after_completion": "INTEGRATED",
  "expected_outputs": [
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
  "generated_markdown": "jira/issues/stories/POST-STORY-023_weather_travel_rest_venue_schedule_sequence_mechanics_officiating_and_sparse_opp.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-069",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100073,
  "in_scope": [
    "Complete and verify child `POST-SUBTASK-067` — Materialize forecast-time weather, venue, coordinates, travel, rest, opponent sequence, neutral-site, schedule-change, and local-time state.",
    "Complete and verify child `POST-SUBTASK-068` — Materialize supported mechanics/officiating/resource candidates and FCS/DII/DIII/NAIA decreasing-information opponent priors.",
    "Complete and verify child `POST-SUBTASK-069` — Validate context correctness, forecast-versus-realized isolation, fallback behavior, and production eligibility.",
    "Integrate the child outputs and execute final gate `POST-SUBTASK-069`.",
    "Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence."
  ],
  "issue_type": "Story",
  "jira_key": "BAT-73",
  "labels": [
    "actionable",
    "advanced-football",
    "core-release",
    "post-wave",
    "story"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-STORY-023",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Build robust matchup context and special handling for low-information opponents.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24213",
    "jira_updated_at": "2026-08-09T00:03:36.888-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Work assigned to sibling Stories or another Epic.",
    "Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.",
    "Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-EPIC-007",
  "phase": "PHASE-2",
  "prerequisites": [
    "Hard dependency POST-SUBTASK-030",
    "Hard dependency POST-SUBTASK-048"
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
    "Verified child completion/evidence manifests for POST-SUBTASK-067, POST-SUBTASK-068, POST-SUBTASK-069.",
    "Final gate decision from `POST-SUBTASK-069` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.",
    "Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_player_intelligence_governance.py"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_context_intelligence_governance.py"
    },
    {
      "classification": "END_TO_END",
      "expectation": "The final child gate `POST-SUBTASK-069` must prove the integrated Story outcome and downstream-consumable output.",
      "path": "POST-SUBTASK-069",
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
  "scope": "Deliver Story POST-STORY-023 (Weather, travel, rest, venue, schedule sequence, mechanics, officiating, and sparse-opponent priors) as one coherent, gated capability inside Epic POST-EPIC-007. Execute child subtasks POST-SUBTASK-067, POST-SUBTASK-068, POST-SUBTASK-069 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-069` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.",
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
  "specificity_fingerprint": "f131c3c1e3a3264cb85e76fbec14c57389dabd33372ea712eac7450e5f653a3c",
  "stop_conditions": [
    "Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs."
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
  "title": "[POST-STORY-023] Weather, travel, rest, venue, schedule sequence, mechanics, officiating, and sparse-opponent priors",
  "traceability_inherited_from": [
    "POST-SUBTASK-069"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "END_TO_END",
    "EXISTING_AUTOMATED_TEST",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "This coherent capability closes a defined portion of Player, roster, recruiting, coaching, and matchup intelligence and creates a verifiable output for the next dependency stage.",
  "work_packet_path": "jira/ai/work_packets/POST-STORY-023.md",
  "workflow_state": "BACKLOG"
}
```

## Objective

Build robust matchup context and special handling for low-information opponents.

## Why This Exists

This coherent capability closes a defined portion of Player, roster, recruiting, coaching, and matchup intelligence and creates a verifiable output for the next dependency stage.

## Scope

Deliver Story POST-STORY-023 (Weather, travel, rest, venue, schedule sequence, mechanics, officiating, and sparse-opponent priors) as one coherent, gated capability inside Epic POST-EPIC-007. Execute child subtasks POST-SUBTASK-067, POST-SUBTASK-068, POST-SUBTASK-069 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-069` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### Explicit In Scope

- Complete and verify child `POST-SUBTASK-067` — Materialize forecast-time weather, venue, coordinates, travel, rest, opponent sequence, neutral-site, schedule-change, and local-time state.
- Complete and verify child `POST-SUBTASK-068` — Materialize supported mechanics/officiating/resource candidates and FCS/DII/DIII/NAIA decreasing-information opponent priors.
- Complete and verify child `POST-SUBTASK-069` — Validate context correctness, forecast-versus-realized isolation, fallback behavior, and production eligibility.
- Integrate the child outputs and execute final gate `POST-SUBTASK-069`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Explicit Out of Scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

## Prerequisites

- Hard dependency POST-SUBTASK-030
- Hard dependency POST-SUBTASK-048

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

1. Weather uses forecast snapshots available at each cutoff; travel/rest/sequence derive from canonical schedules/venues and update for postponements/neutral sites with unknown coordinates left uncertain.
2. The declared output `artifacts/context_intelligence/game_context_state_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
4. Mechanics/officiating/resource data are used only where rights/depth/timing support them, and lower-division opponents receive explicit decreasing-information priors rather than zero strength or dropped games.
5. The declared output `artifacts/context_intelligence/mechanics_sparse_opponent_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
6. Source spot checks, orientation, timing, sparse-opponent uncertainty, and unsupported-lane isolation pass before the context state is production eligible.
7. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. All child subtasks POST-SUBTASK-067, POST-SUBTASK-068, POST-SUBTASK-069 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.
2. The final gate `POST-SUBTASK-069` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.
3. All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.
4. The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.
5. Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_player_intelligence_governance.py` — Run and retain the result when this issue touches the covered contract.
- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_context_intelligence_governance.py` — Run and retain the result when this issue touches the covered contract.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-069` — The final child gate `POST-SUBTASK-069` must prove the integrated Story outcome and downstream-consumable output.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `STORY_EVIDENCE_MANIFEST` — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Required Evidence

- Verified child completion/evidence manifests for POST-SUBTASK-067, POST-SUBTASK-068, POST-SUBTASK-069.
- Final gate decision from `POST-SUBTASK-069` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## Completion Evidence Contract

```json
{
  "all_child_evidence_required": true,
  "child_gate": "POST-SUBTASK-069",
  "governance_traceability_gate": "POST-SUBTASK-069",
  "integrated_proof_required": true
}
```

## End-to-End Validation Requirement

A matchup snapshot reconstructs weather forecast, venue/travel/rest/sequence, supported mechanics, and sparse-opponent priors with honest uncertainty.

## Expected Maturity After Completion

`INTEGRATED`

## Risk / Failure Conditions

- Parallel child outputs may use inconsistent source or schema identities
- Gate task may be bypassed after implementation tasks finish

## Stop Conditions

- Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs.

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

- Open only this Story, its selected child, and referenced source sections; do not load the entire Jira pack.
- Story completion requires the gate Subtask, not only implementation children.

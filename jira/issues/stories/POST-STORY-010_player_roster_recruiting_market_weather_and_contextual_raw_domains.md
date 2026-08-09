<!-- GENERATED VIEW. Canonical record: jira/records/issues/stories/POST-STORY-010_player_roster_recruiting_market_weather_and_contextual_raw_domains.json -->
# POST-STORY-010 — [POST-STORY-010] Expanded national core and supporting-domain acquisition and tiered eligibility

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "All child Subtasks satisfy their expanded-history issue-specific observable checks and preserve required positive, partial, and negative evidence.",
    "The final child gate POST-SUBTASK-030 verifies the combined output and explicitly approves, partially approves by tier, blocks, rejects, or defers downstream use.",
    "The bounded 2022-2025 tranche is preserved as nonterminal, no incomplete domain globally discards otherwise useful history, and no unsupported domain is silently promoted.",
    "No child or aggregate completion resolves GAP-002 or authorizes model/scientific claims before all applicable downstream chronological/PIT and protected gates pass."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Open only this Story, its selected child, and referenced source sections; do not load the entire Jira pack.",
    "Story completion requires the gate Subtask, not only implementation children."
  ],
  "allowed_modification_paths": [
    "artifacts/jira_evidence/POST-STORY-010.json"
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/stories/POST-STORY-010_player_roster_recruiting_market_weather_and_contextual_raw_domains.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "all_child_evidence_required": true,
    "child_gate": "POST-SUBTASK-030",
    "governance_traceability_gate": "POST-SUBTASK-033",
    "integrated_proof_required": true
  },
  "component": "raw-snapshots",
  "components_expected_to_be_touched": [
    "raw-snapshots",
    "raw-data"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "All child subtasks POST-SUBTASK-028, POST-SUBTASK-029, POST-SUBTASK-030 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.",
    "The final gate `POST-SUBTASK-030` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.",
    "All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.",
    "The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.",
    "Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation."
  ],
  "dependencies": [
    "POST-SUBTASK-027"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 4,
    "adr_ids": 6,
    "gap_ids": 1,
    "requirement_ids": 8,
    "risk_ids": 5
  },
  "effective_traceability_total": 24,
  "end_to_end_validation": "A clean expanded-history run produces immutable captures, deterministic cross-domain profile and tiered eligibility, preserved negative evidence, and a non-bypassable downstream readiness decision.",
  "epic_id": "POST-EPIC-003",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-STORY-010.json",
  "evidence_state": "PLANNED",
  "execution_lane": "SHARED_CONTRACT",
  "execution_mode": "AGGREGATE_GATE",
  "expected_maturity_after_completion": "INTEGRATED",
  "expected_outputs": [
    "artifacts/data_lake/historical_expansion_acquisition_manifest.json",
    "artifacts/data_lake/historical_expansion_population_profile.json",
    "artifacts/data_lake/historical_expansion_eligibility_gate.json"
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
  "generated_markdown": "jira/issues/stories/POST-STORY-010_player_roster_recruiting_market_weather_and_contextual_raw_domains.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-033",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100060,
  "in_scope": [
    "Complete and verify POST-SUBTASK-028 expanded immutable acquisition across every useful approved core and supporting domain.",
    "Complete and verify POST-SUBTASK-029 independent population profiling across all required source/season/team/domain/schema/provenance/PIT dimensions.",
    "Complete and verify POST-SUBTASK-030 tiered season/domain/use eligibility without global rejection of partial older seasons or unsupported promotion.",
    "Preserve the bounded 2022-2025 tranche as nonterminal and target approximately 2010-2025 plus earlier quality-supported seasons.",
    "Integrate child outputs through final gate POST-SUBTASK-030 with all partial, negative, and provider-limitation evidence preserved."
  ],
  "issue_type": "Story",
  "jira_key": "BAT-60",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "raw-data",
    "story",
    "historical-expansion"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-STORY-010",
  "maturity_before": "SCAFFOLD",
  "objective": "Acquire, profile, and assign tiered eligibility to the expanded national core and supporting-domain history",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24200",
    "jira_updated_at": "2026-08-09T00:03:28.734-0500",
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
  "parent_id": "POST-EPIC-003",
  "phase": "PHASE-1",
  "prerequisites": [
    "Hard dependency POST-SUBTASK-027"
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
    "Verified child completion/evidence manifests for POST-SUBTASK-028, POST-SUBTASK-029, POST-SUBTASK-030.",
    "Final gate decision from `POST-SUBTASK-030` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.",
    "Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_w19_foundation.py"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tools/validate_w19_foundation.py"
    },
    {
      "classification": "END_TO_END",
      "expectation": "The final child gate `POST-SUBTASK-030` must prove the integrated Story outcome and downstream-consumable output.",
      "path": "POST-SUBTASK-030",
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
  "scope": "Execute POST-SUBTASK-028 through POST-SUBTASK-030 as the expanded-history acquisition/profile/eligibility chain. Target approximately 2010-2025 and earlier supported seasons, preserve the bounded 2022-2025 tranche as nonterminal, and hand explicit season/domain/use tiers plus negative evidence to immutable national-lake work.",
  "source_ids": [
    "GAP-002",
    "GAP-006",
    "GAP-010",
    "GAP-011",
    "HANDOFF-003",
    "HANDOFF-008"
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
    "SRCREF-01564",
    "SRCREF-01894",
    "SRCREF-01568",
    "SRCREF-01572",
    "SRCREF-01573"
  ],
  "specificity_fingerprint": "7d010c12897542953c6317ae08891fded9857e550462b5a87b00ba0f9852cac5",
  "stop_conditions": [
    "Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs."
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
    "SRCREF-01564",
    "SRCREF-01894",
    "SRCREF-01568",
    "SRCREF-01572",
    "SRCREF-01573"
  ],
  "title": "[POST-STORY-010] Expanded national core and supporting-domain acquisition and tiered eligibility",
  "traceability_inherited_from": [
    "POST-SUBTASK-033"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "END_TO_END",
    "EXISTING_AUTOMATED_TEST",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "This coherent capability closes a defined portion of Immutable national historical data materialization and creates a verifiable output for the next dependency stage.",
  "work_packet_path": "jira/ai/work_packets/POST-STORY-010.md",
  "workflow_state": "BACKLOG"
}
```

## Objective

Acquire, profile, and assign tiered eligibility to the expanded national core and supporting-domain history

## Why This Exists

This coherent capability closes a defined portion of Immutable national historical data materialization and creates a verifiable output for the next dependency stage.

## Scope

Execute POST-SUBTASK-028 through POST-SUBTASK-030 as the expanded-history acquisition/profile/eligibility chain. Target approximately 2010-2025 and earlier supported seasons, preserve the bounded 2022-2025 tranche as nonterminal, and hand explicit season/domain/use tiers plus negative evidence to immutable national-lake work.

### Explicit In Scope

- Complete and verify POST-SUBTASK-028 expanded immutable acquisition across every useful approved core and supporting domain.
- Complete and verify POST-SUBTASK-029 independent population profiling across all required source/season/team/domain/schema/provenance/PIT dimensions.
- Complete and verify POST-SUBTASK-030 tiered season/domain/use eligibility without global rejection of partial older seasons or unsupported promotion.
- Preserve the bounded 2022-2025 tranche as nonterminal and target approximately 2010-2025 plus earlier quality-supported seasons.
- Integrate child outputs through final gate POST-SUBTASK-030 with all partial, negative, and provider-limitation evidence preserved.

### Explicit Out of Scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/rights/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

## Prerequisites

- Hard dependency POST-SUBTASK-027

## Hard Dependencies

- POST-SUBTASK-027

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

- artifacts/data_lake/historical_expansion_acquisition_manifest.json
- artifacts/data_lake/historical_expansion_population_profile.json
- artifacts/data_lake/historical_expansion_eligibility_gate.json

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

1. All child Subtasks satisfy their expanded-history issue-specific observable checks and preserve required positive, partial, and negative evidence.
2. The final child gate POST-SUBTASK-030 verifies the combined output and explicitly approves, partially approves by tier, blocks, rejects, or defers downstream use.
3. The bounded 2022-2025 tranche is preserved as nonterminal, no incomplete domain globally discards otherwise useful history, and no unsupported domain is silently promoted.
4. No child or aggregate completion resolves GAP-002 or authorizes model/scientific claims before all applicable downstream chronological/PIT and protected gates pass.

## Definition of Done

1. All child subtasks POST-SUBTASK-028, POST-SUBTASK-029, POST-SUBTASK-030 have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.
2. The final gate `POST-SUBTASK-030` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.
3. All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.
4. The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.
5. Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_w19_foundation.py` — Run and retain the result when this issue touches the covered contract.
- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tools/validate_w19_foundation.py` — Run and retain the result when this issue touches the covered contract.
- **END_TO_END** / `END_TO_END` — `POST-SUBTASK-030` — The final child gate `POST-SUBTASK-030` must prove the integrated Story outcome and downstream-consumable output.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `STORY_EVIDENCE_MANIFEST` — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Required Evidence

- Verified child completion/evidence manifests for POST-SUBTASK-028, POST-SUBTASK-029, POST-SUBTASK-030.
- Final gate decision from `POST-SUBTASK-030` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## Completion Evidence Contract

```json
{
  "all_child_evidence_required": true,
  "child_gate": "POST-SUBTASK-030",
  "governance_traceability_gate": "POST-SUBTASK-033",
  "integrated_proof_required": true
}
```

## End-to-End Validation Requirement

A clean expanded-history run produces immutable captures, deterministic cross-domain profile and tiered eligibility, preserved negative evidence, and a non-bypassable downstream readiness decision.

## Expected Maturity After Completion

`INTEGRATED`

## Risk / Failure Conditions

- Parallel child outputs may use inconsistent source or schema identities
- Gate task may be bypassed after implementation tasks finish

## Stop Conditions

- Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs.

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
- SRCREF-01894
- SRCREF-01568
- SRCREF-01572
- SRCREF-01573

## AI Context Notes

- Open only this Story, its selected child, and referenced source sections; do not load the entire Jira pack.
- Story completion requires the gate Subtask, not only implementation children.

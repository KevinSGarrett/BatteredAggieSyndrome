<!-- GENERATED VIEW. Canonical record: jira/records/issues/stories/POST-STORY-010_player_roster_recruiting_market_weather_and_contextual_raw_domains.json -->
# POST-STORY-010 — [POST-STORY-010] Historical expansion across core and supporting domains

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Preserve 2022-2025 as a bounded nonterminal tranche; target approximately 2010-2025 and earlier quality-supported seasons across teams, schedules, games, outcomes, drives, plays, team/player box scores, rosters, rankings, venues, advanced statistics, structured gamebook equivalents, and useful context. Record source/endpoint, season/type, team/game, domain/grain, schema/version, immutable identity, missingness, provider failures, and historical known-at/PIT state without discarding a useful season because another domain is incomplete.",
    "The declared output `artifacts/data_lake/historical_expansion_acquisition_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "Coverage and timestamp quality are measured by season/team/source/domain, with A&M detail reported separately and upstream-equivalent feeds not miscounted as independent corroboration.",
    "The declared output `artifacts/data_lake/context_population_profile.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Closing market, realized weather, final participation, restricted, thin, or unsupported domains cannot enter earlier production cutoffs or block the core v1 without explicit evidence.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
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
  "end_to_end_validation": "The expanded manifest is deterministic and consumable by the profiling step, preserves partial seasons and missing domains, and never treats rights metadata or the 2022-2025 tranche as a terminal-history gate.",
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
    "Complete and verify child `POST-SUBTASK-028` — Expand immutable national core and supporting-domain history to the maximum quality-supported seasons.",
    "Complete and verify child `POST-SUBTASK-029` — Profile supporting-domain schema, historical coverage, timestamp quality, upstream lineage, and nonblocking source-policy metadata.",
    "Complete and verify child `POST-SUBTASK-030` — Gate domain-by-domain production, experimental, conditional, rejected, or unavailable eligibility.",
    "Integrate the child outputs and execute final gate `POST-SUBTASK-030`.",
    "Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence."
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
  "objective": "Expand the validated contemporary tranche to the maximum quality-supported national history, targeting approximately 2010-2025 and earlier seasons while preserving tiered domain eligibility.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24200",
    "jira_updated_at": "2026-08-09T23:23:55.058-0500",
    "last_synced_at": "2026-08-11T06:07:11.607568+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\JIRA-LIVE-CATCHUP-20260811\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Work assigned to sibling Stories or another Epic.",
    "Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.",
    "Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate."
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
  "scope": "Deliver Story POST-STORY-010 (Historical expansion across core and supporting domains) as one coherent, gated capability inside Epic POST-EPIC-003. Execute child subtasks POST-SUBTASK-028, POST-SUBTASK-029, POST-SUBTASK-030 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-030` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.",
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
  "specificity_fingerprint": "52c86e3543b5c834fbe184fb532cd97a43180b6f0f70fd4c248e69d5b3ebd84c",
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
  "title": "[POST-STORY-010] Historical expansion across core and supporting domains",
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

Expand the validated contemporary tranche to the maximum quality-supported national history, targeting approximately 2010-2025 and earlier seasons while preserving tiered domain eligibility.

## Why This Exists

This coherent capability closes a defined portion of Immutable national historical data materialization and creates a verifiable output for the next dependency stage.

## Scope

Deliver Story POST-STORY-010 (Historical expansion across core and supporting domains) as one coherent, gated capability inside Epic POST-EPIC-003. Execute child subtasks POST-SUBTASK-028, POST-SUBTASK-029, POST-SUBTASK-030 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-030` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### Explicit In Scope

- Complete and verify child `POST-SUBTASK-028` — Expand immutable national core and supporting-domain history to the maximum quality-supported seasons.
- Complete and verify child `POST-SUBTASK-029` — Profile supporting-domain schema, historical coverage, timestamp quality, upstream lineage, and nonblocking source-policy metadata.
- Complete and verify child `POST-SUBTASK-030` — Gate domain-by-domain production, experimental, conditional, rejected, or unavailable eligibility.
- Integrate the child outputs and execute final gate `POST-SUBTASK-030`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Explicit Out of Scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

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

1. Preserve 2022-2025 as a bounded nonterminal tranche; target approximately 2010-2025 and earlier quality-supported seasons across teams, schedules, games, outcomes, drives, plays, team/player box scores, rosters, rankings, venues, advanced statistics, structured gamebook equivalents, and useful context. Record source/endpoint, season/type, team/game, domain/grain, schema/version, immutable identity, missingness, provider failures, and historical known-at/PIT state without discarding a useful season because another domain is incomplete.
2. The declared output `artifacts/data_lake/historical_expansion_acquisition_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
4. Coverage and timestamp quality are measured by season/team/source/domain, with A&M detail reported separately and upstream-equivalent feeds not miscounted as independent corroboration.
5. The declared output `artifacts/data_lake/context_population_profile.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
6. Closing market, realized weather, final participation, restricted, thin, or unsupported domains cannot enter earlier production cutoffs or block the core v1 without explicit evidence.
7. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

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

The expanded manifest is deterministic and consumable by the profiling step, preserves partial seasons and missing domains, and never treats rights metadata or the 2022-2025 tranche as a terminal-history gate.

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

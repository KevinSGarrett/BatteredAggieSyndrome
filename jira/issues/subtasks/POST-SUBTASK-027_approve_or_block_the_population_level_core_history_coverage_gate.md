<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-027_approve_or_block_the_population_level_core_history_coverage_gate.json -->
# POST-SUBTASK-027 — [POST-SUBTASK-027] Approve or block the population-level core-history coverage gate

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Every configured season/source request records source identity, retrieval/known-at time, request identity, response hash, immutable path, pagination, and provider failure state.",
    "Normalized games, scores, drives, plays, and box totals reconcile to canonical identities and official outcomes; every rejected/partial record is quarantined with reason.",
    "Coverage is measured by source, domain, season, team, and game; reconnaissance samples or fixtures cannot satisfy population readiness.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-009. Governance traceability gate: POST-SUBTASK-033. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-027.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/data_lake/core_coverage_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-027.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-006;POST-SUBTASK-018;POST-SUBTASK-021;POST-SUBTASK-022;POST-SUBTASK-025;POST-SUBTASK-026",
  "blocks": [
    "POST-STORY-010",
    "POST-STORY-011",
    "POST-SUBTASK-028",
    "POST-SUBTASK-029",
    "POST-SUBTASK-030",
    "POST-SUBTASK-031",
    "POST-SUBTASK-032",
    "POST-SUBTASK-033"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-027_approve_or_block_the_population_level_core_history_coverage_gate.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-009",
    "governance_traceability_gate": "POST-SUBTASK-033",
    "negative_results_preserved": true,
    "provenance_dimensions": [
      "source",
      "data",
      "code",
      "config",
      "tool",
      "runtime",
      "split/cutoff when applicable"
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
    "The atomic scope in POST-SUBTASK-027 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-009."
  ],
  "dependencies": [
    "POST-SUBTASK-006",
    "POST-SUBTASK-018",
    "POST-SUBTASK-021",
    "POST-SUBTASK-022",
    "POST-SUBTASK-025",
    "POST-SUBTASK-026"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 4,
    "adr_ids": 6,
    "gap_ids": 1,
    "requirement_ids": 8,
    "risk_ids": 5
  },
  "effective_traceability_total": 24,
  "end_to_end_validation": "A clean acquisition run produces immutable national game history, deterministic normalized evidence, and an honest coverage decision. The gate decision must explicitly reevaluate downstream issues: POST-STORY-010, POST-STORY-011, POST-SUBTASK-028, POST-SUBTASK-029, POST-SUBTASK-030, POST-SUBTASK-031, POST-SUBTASK-032, POST-SUBTASK-033.",
  "epic_id": "POST-EPIC-003",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-027.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/data_lake/core_coverage_gate.json"
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
    "docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-027_approve_or_block_the_population_level_core_history_coverage_gate.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-033",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100331,
  "in_scope": [
    "Perform the exact action: Approve or block the population-level core-history coverage gate.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-006`, `POST-SUBTASK-018`, `POST-SUBTASK-021`, `POST-SUBTASK-022`, `POST-SUBTASK-025`, `POST-SUBTASK-026`.",
    "Demonstrate with saved evidence: Every configured season/source request records source identity, retrieval/known-at time, request identity, response hash, immutable path, pagination, and provider failure state.",
    "Demonstrate with saved evidence: Normalized games, scores, drives, plays, and box totals reconcile to canonical identities and official outcomes; every rejected/partial record is quarantined with reason.",
    "Demonstrate with saved evidence: Coverage is measured by source, domain, season, team, and game; reconnaissance samples or fixtures cannot satisfy population readiness.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `artifacts/data_lake/core_coverage_gate.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-377",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "protected-gate",
    "raw-data",
    "subtask"
  ],
  "last_content_audit": "2026-08-08",
  "local_id": "POST-SUBTASK-027",
  "maturity_before": "SCAFFOLD",
  "objective": "Approve or block the population-level core-history coverage gate",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24517",
    "jira_updated_at": "2026-08-09T00:03:29.553-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.",
    "Work assigned to sibling subtasks: Acquire approved national team, schedule, game, score, drive, play, box-score, and gamebook history; Normalize and reconcile core/game-event records while preserving immutable source evidence."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-009",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-021 complete at required maturity",
    "Dependency POST-SUBTASK-018 complete at required maturity",
    "Dependency POST-SUBTASK-022 complete at required maturity",
    "Dependency POST-SUBTASK-006 complete at required maturity",
    "Dependency POST-SUBTASK-025 complete at required maturity",
    "Dependency POST-SUBTASK-026 complete at required maturity"
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
    "docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/data_lake/core_coverage_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-027; retain command, exit code, and relevant output.",
      "path": "tests/test_w19_foundation.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "CHRONOLOGICAL_REPLAY",
      "expectation": "Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.",
      "path": "artifacts/data_lake/core_coverage_gate.json",
      "validation_class": "CHRONOLOGICAL_REPLAY"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/data_lake/core_coverage_gate.json",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "REPRODUCIBILITY",
      "expectation": "Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.",
      "path": "ISSUE_COMPLETION_MANIFEST",
      "validation_class": "REPRODUCIBILITY"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-027.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that every configured season/source request records source identity, retrieval/known-at time, request identity, response hash, immutable path, pagination, and provider failure state.",
    "Acceptance failure: the evidence cannot demonstrate that normalized games, scores, drives, plays, and box totals reconcile to canonical identities and official outcomes; every rejected/partial record is quarantined with reason.",
    "Acceptance failure: the evidence cannot demonstrate that coverage is measured by source, domain, season, team, and game; reconnaissance samples or fixtures cannot satisfy population readiness.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-009 (Core national game spine): Approve or block the population-level core-history coverage gate. Consume only verified prerequisite outputs from `POST-SUBTASK-006`, `POST-SUBTASK-018`, `POST-SUBTASK-021`, `POST-SUBTASK-022`, `POST-SUBTASK-025`, `POST-SUBTASK-026`. Produce `artifacts/data_lake/core_coverage_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
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
  "specificity_fingerprint": "fc5ca568474147507dadf69f3f363ee3249d8af6c357e039e5e949bfc974d591",
  "stop_conditions": [
    "Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.",
    "Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.",
    "Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence."
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
  "title": "[POST-SUBTASK-027] Approve or block the population-level core-history coverage gate",
  "traceability_inherited_from": [
    "POST-SUBTASK-033"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "CHRONOLOGICAL_REPLAY",
    "END_TO_END",
    "REGRESSION",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-009: Core national game spine.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-027.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Approve or block the population-level core-history coverage gate

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-009: Core national game spine.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-009 (Core national game spine): Approve or block the population-level core-history coverage gate. Consume only verified prerequisite outputs from `POST-SUBTASK-006`, `POST-SUBTASK-018`, `POST-SUBTASK-021`, `POST-SUBTASK-022`, `POST-SUBTASK-025`, `POST-SUBTASK-026`. Produce `artifacts/data_lake/core_coverage_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Approve or block the population-level core-history coverage gate.
- Consume only verified prerequisite outputs from `POST-SUBTASK-006`, `POST-SUBTASK-018`, `POST-SUBTASK-021`, `POST-SUBTASK-022`, `POST-SUBTASK-025`, `POST-SUBTASK-026`.
- Demonstrate with saved evidence: Every configured season/source request records source identity, retrieval/known-at time, request identity, response hash, immutable path, pagination, and provider failure state.
- Demonstrate with saved evidence: Normalized games, scores, drives, plays, and box totals reconcile to canonical identities and official outcomes; every rejected/partial record is quarantined with reason.
- Demonstrate with saved evidence: Coverage is measured by source, domain, season, team, and game; reconnaissance samples or fixtures cannot satisfy population readiness.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/data_lake/core_coverage_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Acquire approved national team, schedule, game, score, drive, play, box-score, and gamebook history; Normalize and reconcile core/game-event records while preserving immutable source evidence.

## Prerequisites

- Dependency POST-SUBTASK-021 complete at required maturity
- Dependency POST-SUBTASK-018 complete at required maturity
- Dependency POST-SUBTASK-022 complete at required maturity
- Dependency POST-SUBTASK-006 complete at required maturity
- Dependency POST-SUBTASK-025 complete at required maturity
- Dependency POST-SUBTASK-026 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-006
- POST-SUBTASK-018
- POST-SUBTASK-021
- POST-SUBTASK-022
- POST-SUBTASK-025
- POST-SUBTASK-026

## Blocks

- POST-STORY-010
- POST-STORY-011
- POST-SUBTASK-028
- POST-SUBTASK-029
- POST-SUBTASK-030
- POST-SUBTASK-031
- POST-SUBTASK-032
- POST-SUBTASK-033

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

- artifacts/data_lake/core_coverage_gate.json

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

1. Every configured season/source request records source identity, retrieval/known-at time, request identity, response hash, immutable path, pagination, and provider failure state.
2. Normalized games, scores, drives, plays, and box totals reconcile to canonical identities and official outcomes; every rejected/partial record is quarantined with reason.
3. Coverage is measured by source, domain, season, team, and game; reconnaissance samples or fixtures cannot satisfy population readiness.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. The atomic scope in POST-SUBTASK-027 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-009.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w19_foundation.py` — Run as a regression check after completing POST-SUBTASK-027; retain command, exit code, and relevant output.
- **CHRONOLOGICAL_REPLAY** / `CHRONOLOGICAL_REPLAY` — `artifacts/data_lake/core_coverage_gate.json` — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- **END_TO_END** / `END_TO_END` — `artifacts/data_lake/core_coverage_gate.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/data_lake/core_coverage_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "PRODUCTION_READY",
  "downstream_consumer": "POST-STORY-009",
  "governance_traceability_gate": "POST-SUBTASK-033",
  "negative_results_preserved": true,
  "provenance_dimensions": [
    "source",
    "data",
    "code",
    "config",
    "tool",
    "runtime",
    "split/cutoff when applicable"
  ]
}
```

## End-to-End Validation Requirement

A clean acquisition run produces immutable national game history, deterministic normalized evidence, and an honest coverage decision. The gate decision must explicitly reevaluate downstream issues: POST-STORY-010, POST-STORY-011, POST-SUBTASK-028, POST-SUBTASK-029, POST-SUBTASK-030, POST-SUBTASK-031, POST-SUBTASK-032, POST-SUBTASK-033.

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-027.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that every configured season/source request records source identity, retrieval/known-at time, request identity, response hash, immutable path, pagination, and provider failure state.
- Acceptance failure: the evidence cannot demonstrate that normalized games, scores, drives, plays, and box totals reconcile to canonical identities and official outcomes; every rejected/partial record is quarantined with reason.
- Acceptance failure: the evidence cannot demonstrate that coverage is measured by source, domain, season, team, and game; reconnaissance samples or fixtures cannot satisfy population readiness.
- Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Stop Conditions

- Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.
- Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.
- Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence.

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

- Canonical parent Story: POST-STORY-009. Governance traceability gate: POST-SUBTASK-033. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-027.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-084_validate_peer_analog_anti_selection_tuning_lift_stability_uncertainty_and_seal_a.json -->
# POST-SUBTASK-084 — [POST-SUBTASK-084] Validate peer/analog anti-selection, tuning lift/stability/uncertainty, and seal admissible candidates plus the no-adjustment fallback

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Peer/regime/analog definitions use only pinned pregame features, exclude same/future outcomes, expose distance/sample/uncertainty, and retain alternative sensitivity specifications.",
    "Every candidate includes global-only/no adjustment, uses shrinkage/minimum data, avoids protected A&M outcomes and favorable-regime selection, and preserves null/negative/unstable tuning evidence.",
    "Outcome-label removal/future-append stability and multiple-comparison diagnostics pass; only precommitted candidates are sealed and no candidate is labeled production-improving yet.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-028. Governance traceability gate: POST-SUBTASK-087. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-084.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/tamu/TAMU_CANDIDATE_REGISTRY.json",
    "artifacts/jira_evidence/POST-SUBTASK-084.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-078;POST-SUBTASK-081;POST-SUBTASK-082;POST-SUBTASK-083",
  "blocks": [
    "POST-EPIC-010",
    "POST-EPIC-011",
    "POST-STORY-029",
    "POST-STORY-031",
    "POST-STORY-033",
    "POST-SUBTASK-085",
    "POST-SUBTASK-086",
    "POST-SUBTASK-087",
    "POST-SUBTASK-091",
    "POST-SUBTASK-092",
    "POST-SUBTASK-093",
    "POST-SUBTASK-097",
    "POST-SUBTASK-098",
    "POST-SUBTASK-099"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-084_validate_peer_analog_anti_selection_tuning_lift_stability_uncertainty_and_seal_a.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-028",
    "governance_traceability_gate": "POST-SUBTASK-087",
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
  "component": "tamu-specialization",
  "components_expected_to_be_touched": [
    "tamu-specialization",
    "tamu"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-084 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-028."
  ],
  "dependencies": [
    "POST-SUBTASK-078",
    "POST-SUBTASK-081",
    "POST-SUBTASK-082",
    "POST-SUBTASK-083"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 9,
    "adr_ids": 9,
    "gap_ids": 1,
    "requirement_ids": 42,
    "risk_ids": 7
  },
  "effective_traceability_total": 68,
  "end_to_end_validation": "A&M candidates and peer/analog definitions are frozen before protected outcomes and always retain a valid global-only/no-adjustment choice. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-010, POST-EPIC-011, POST-STORY-029, POST-STORY-031, POST-STORY-033, POST-SUBTASK-085, POST-SUBTASK-086, POST-SUBTASK-087, POST-SUBTASK-091, POST-SUBTASK-092, POST-SUBTASK-093, POST-SUBTASK-097….",
  "epic_id": "POST-EPIC-009",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-084.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/tamu/TAMU_CANDIDATE_REGISTRY.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_tamu_specialization_governance.py",
    "src/aggie_analytics/tamu/specialization.py",
    "src/aggie_analytics/tamu/state.py",
    "docs/40_TEXAS_AM_SPECIALIZATION_ARCHITECTURE.md",
    "docs/43_TAMU_SPECIALIZATION_CANDIDATES_AND_OVERFIT_GUARDS.md",
    "docs/41_TAMU_HIGH_RESOLUTION_STATE.md",
    "docs/42_TAMU_PEERS_ANALOGS_AND_SNAPSHOTS.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_tamu_specialization_governance.py",
    "src/aggie_analytics/tamu/specialization.py",
    "src/aggie_analytics/tamu/state.py",
    "docs/40_TEXAS_AM_SPECIALIZATION_ARCHITECTURE.md",
    "docs/43_TAMU_SPECIALIZATION_CANDIDATES_AND_OVERFIT_GUARDS.md",
    "docs/41_TAMU_HIGH_RESOLUTION_STATE.md",
    "docs/42_TAMU_PEERS_ANALOGS_AND_SNAPSHOTS.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-084_validate_peer_analog_anti_selection_tuning_lift_stability_uncertainty_and_seal_a.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-087",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100388,
  "in_scope": [
    "Perform the exact action: Validate peer/analog anti-selection, tuning lift/stability/uncertainty, and seal admissible candidates plus the no-adjustment fallback.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-078`, `POST-SUBTASK-081`, `POST-SUBTASK-082`, `POST-SUBTASK-083`.",
    "Demonstrate with saved evidence: Peer/regime/analog definitions use only pinned pregame features, exclude same/future outcomes, expose distance/sample/uncertainty, and retain alternative sensitivity specifications.",
    "Demonstrate with saved evidence: Every candidate includes global-only/no adjustment, uses shrinkage/minimum data, avoids protected A&M outcomes and favorable-regime selection, and preserves null/negative/unstable tuning evidence.",
    "Demonstrate with saved evidence: Outcome-label removal/future-append stability and multiple-comparison diagnostics pass; only precommitted candidates are sealed and no candidate is labeled production-improving yet.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `artifacts/tamu/TAMU_CANDIDATE_REGISTRY.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-434",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "protected-gate",
    "subtask",
    "tamu"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-084",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Validate peer/analog anti-selection, tuning lift/stability/uncertainty, and seal admissible candidates plus the no-adjustment fallback",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24574",
    "jira_updated_at": "2026-08-09T00:03:52.513-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Materialize pregame-observable peer/regime candidates and prior-only historical analog index with distance diagnostics; Train global-only, no-adjustment, residual, hierarchical, calibration, shrinkage, and feature-interaction A&M candidates on permitted history."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-028",
  "phase": "PHASE-3",
  "prerequisites": [
    "Dependency POST-SUBTASK-078 complete at required maturity",
    "Dependency POST-SUBTASK-081 complete at required maturity",
    "Dependency POST-SUBTASK-082 complete at required maturity",
    "Dependency POST-SUBTASK-083 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02057",
    "SRCREF-02058",
    "SRCREF-02059",
    "SRCREF-02060"
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
    "tests/test_tamu_specialization_governance.py",
    "src/aggie_analytics/tamu/specialization.py",
    "src/aggie_analytics/tamu/state.py",
    "docs/40_TEXAS_AM_SPECIALIZATION_ARCHITECTURE.md",
    "docs/43_TAMU_SPECIALIZATION_CANDIDATES_AND_OVERFIT_GUARDS.md",
    "docs/41_TAMU_HIGH_RESOLUTION_STATE.md",
    "docs/42_TAMU_PEERS_ANALOGS_AND_SNAPSHOTS.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/tamu/TAMU_CANDIDATE_REGISTRY.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-084; retain command, exit code, and relevant output.",
      "path": "tests/test_tamu_specialization_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-084; retain command, exit code, and relevant output.",
      "path": "tools/validate_tamu_specialization.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/tamu/TAMU_CANDIDATE_REGISTRY.json",
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
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-084.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that peer/regime/analog definitions use only pinned pregame features, exclude same/future outcomes, expose distance/sample/uncertainty, and retain alternative sensitivity specifications.",
    "Acceptance failure: the evidence cannot demonstrate that every candidate includes global-only/no adjustment, uses shrinkage/minimum data, avoids protected A&M outcomes and favorable-regime selection, and preserves null/negative/unstable tuning evidence.",
    "Acceptance failure: the evidence cannot demonstrate that outcome-label removal/future-append stability and multiple-comparison diagnostics pass; only precommitted candidates are sealed and no candidate is labeled production-improving yet.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-028 (Peers, regimes, historical analogs, and specialization candidates): Validate peer/analog anti-selection, tuning lift/stability/uncertainty, and seal admissible candidates plus the no-adjustment fallback. Consume only verified prerequisite outputs from `POST-SUBTASK-078`, `POST-SUBTASK-081`, `POST-SUBTASK-082`, `POST-SUBTASK-083`. Produce `artifacts/tamu/TAMU_CANDIDATE_REGISTRY.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
  "source_ids": [
    "GAP-009",
    "HANDOFF-007"
  ],
  "source_refs": [
    "SRCREF-02057",
    "SRCREF-02058",
    "SRCREF-02059",
    "SRCREF-02060",
    "SRCREF-02061",
    "SRCREF-02062",
    "SRCREF-02063",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01893",
    "SRCREF-01571"
  ],
  "specificity_fingerprint": "c69b9109051f3a9913fe05a10c2aed7931a33b9b1af088f14bf29dfd1a95c38c",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
  ],
  "supporting_source_refs": [
    "SRCREF-02061",
    "SRCREF-02062",
    "SRCREF-02063",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01893",
    "SRCREF-01571"
  ],
  "title": "[POST-SUBTASK-084] Validate peer/analog anti-selection, tuning lift/stability/uncertainty, and seal admissible candidates plus the no-adjustment fallback",
  "traceability_inherited_from": [
    "POST-SUBTASK-087"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "END_TO_END",
    "REGRESSION",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-028: Peers, regimes, historical analogs, and specialization candidates.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-084.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Validate peer/analog anti-selection, tuning lift/stability/uncertainty, and seal admissible candidates plus the no-adjustment fallback

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-028: Peers, regimes, historical analogs, and specialization candidates.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-028 (Peers, regimes, historical analogs, and specialization candidates): Validate peer/analog anti-selection, tuning lift/stability/uncertainty, and seal admissible candidates plus the no-adjustment fallback. Consume only verified prerequisite outputs from `POST-SUBTASK-078`, `POST-SUBTASK-081`, `POST-SUBTASK-082`, `POST-SUBTASK-083`. Produce `artifacts/tamu/TAMU_CANDIDATE_REGISTRY.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Validate peer/analog anti-selection, tuning lift/stability/uncertainty, and seal admissible candidates plus the no-adjustment fallback.
- Consume only verified prerequisite outputs from `POST-SUBTASK-078`, `POST-SUBTASK-081`, `POST-SUBTASK-082`, `POST-SUBTASK-083`.
- Demonstrate with saved evidence: Peer/regime/analog definitions use only pinned pregame features, exclude same/future outcomes, expose distance/sample/uncertainty, and retain alternative sensitivity specifications.
- Demonstrate with saved evidence: Every candidate includes global-only/no adjustment, uses shrinkage/minimum data, avoids protected A&M outcomes and favorable-regime selection, and preserves null/negative/unstable tuning evidence.
- Demonstrate with saved evidence: Outcome-label removal/future-append stability and multiple-comparison diagnostics pass; only precommitted candidates are sealed and no candidate is labeled production-improving yet.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/tamu/TAMU_CANDIDATE_REGISTRY.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Materialize pregame-observable peer/regime candidates and prior-only historical analog index with distance diagnostics; Train global-only, no-adjustment, residual, hierarchical, calibration, shrinkage, and feature-interaction A&M candidates on permitted history.

## Prerequisites

- Dependency POST-SUBTASK-078 complete at required maturity
- Dependency POST-SUBTASK-081 complete at required maturity
- Dependency POST-SUBTASK-082 complete at required maturity
- Dependency POST-SUBTASK-083 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-078
- POST-SUBTASK-081
- POST-SUBTASK-082
- POST-SUBTASK-083

## Blocks

- POST-EPIC-010
- POST-EPIC-011
- POST-STORY-029
- POST-STORY-031
- POST-STORY-033
- POST-SUBTASK-085
- POST-SUBTASK-086
- POST-SUBTASK-087
- POST-SUBTASK-091
- POST-SUBTASK-092
- POST-SUBTASK-093
- POST-SUBTASK-097
- POST-SUBTASK-098
- POST-SUBTASK-099

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_tamu_specialization_governance.py
- src/aggie_analytics/tamu/specialization.py
- src/aggie_analytics/tamu/state.py
- docs/40_TEXAS_AM_SPECIALIZATION_ARCHITECTURE.md
- docs/43_TAMU_SPECIALIZATION_CANDIDATES_AND_OVERFIT_GUARDS.md
- docs/41_TAMU_HIGH_RESOLUTION_STATE.md
- docs/42_TAMU_PEERS_ANALOGS_AND_SNAPSHOTS.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- tamu-specialization
- tamu

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

- artifacts/tamu/TAMU_CANDIDATE_REGISTRY.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-087`
- Inherited from: POST-SUBTASK-087
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 9, "adr_ids": 9, "gap_ids": 1, "requirement_ids": 42, "risk_ids": 7}`

## Acceptance Criteria

1. Peer/regime/analog definitions use only pinned pregame features, exclude same/future outcomes, expose distance/sample/uncertainty, and retain alternative sensitivity specifications.
2. Every candidate includes global-only/no adjustment, uses shrinkage/minimum data, avoids protected A&M outcomes and favorable-regime selection, and preserves null/negative/unstable tuning evidence.
3. Outcome-label removal/future-append stability and multiple-comparison diagnostics pass; only precommitted candidates are sealed and no candidate is labeled production-improving yet.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. The atomic scope in POST-SUBTASK-084 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-028.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_tamu_specialization_governance.py` — Run as a regression check after completing POST-SUBTASK-084; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_tamu_specialization.py` — Run as a regression check after completing POST-SUBTASK-084; retain command, exit code, and relevant output.
- **END_TO_END** / `END_TO_END` — `artifacts/tamu/TAMU_CANDIDATE_REGISTRY.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/tamu/TAMU_CANDIDATE_REGISTRY.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "PRODUCTION_READY",
  "downstream_consumer": "POST-STORY-028",
  "governance_traceability_gate": "POST-SUBTASK-087",
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

A&M candidates and peer/analog definitions are frozen before protected outcomes and always retain a valid global-only/no-adjustment choice. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-010, POST-EPIC-011, POST-STORY-029, POST-STORY-031, POST-STORY-033, POST-SUBTASK-085, POST-SUBTASK-086, POST-SUBTASK-087, POST-SUBTASK-091, POST-SUBTASK-092, POST-SUBTASK-093, POST-SUBTASK-097….

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-084.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that peer/regime/analog definitions use only pinned pregame features, exclude same/future outcomes, expose distance/sample/uncertainty, and retain alternative sensitivity specifications.
- Acceptance failure: the evidence cannot demonstrate that every candidate includes global-only/no adjustment, uses shrinkage/minimum data, avoids protected A&M outcomes and favorable-regime selection, and preserves null/negative/unstable tuning evidence.
- Acceptance failure: the evidence cannot demonstrate that outcome-label removal/future-append stability and multiple-comparison diagnostics pass; only precommitted candidates are sealed and no candidate is labeled production-improving yet.
- Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

## Source References

- SRCREF-02057
- SRCREF-02058
- SRCREF-02059
- SRCREF-02060
- SRCREF-02061
- SRCREF-02062
- SRCREF-02063
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01893
- SRCREF-01571

## AI Context Notes

- Canonical parent Story: POST-STORY-028. Governance traceability gate: POST-SUBTASK-087. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-084.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

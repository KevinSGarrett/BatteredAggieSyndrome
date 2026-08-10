<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-038_build_coach_staff_player_roster_recruiting_and_transfer_identity_registries_with.json -->
# POST-SUBTASK-038 — [POST-SUBTASK-038] Build coach, staff, player, roster, recruiting, and transfer identity registries with confidence and review state

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Person mappings preserve source IDs, name/team/season/position evidence, transfers, duplicate names, suffixes, and uncertainty; low-confidence cases enter review instead of forced name-only merges.",
    "The declared output `artifacts/entities/canonical_people_registry.csv` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-013. Governance traceability gate: POST-SUBTASK-042. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-038.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/entities/canonical_people_registry.csv",
    "artifacts/jira_evidence/POST-SUBTASK-038.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-037",
  "blocks": [
    "POST-SUBTASK-039"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-038_build_coach_staff_player_roster_recruiting_and_transfer_identity_registries_with.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "EMPIRICALLY_VALIDATED",
    "downstream_consumer": "POST-SUBTASK-039",
    "governance_traceability_gate": "POST-SUBTASK-042",
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
  "component": "entities",
  "components_expected_to_be_touched": [
    "entities"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-038 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The output set `artifacts/entities/canonical_people_registry.csv` is demonstrably consumable by POST-SUBTASK-039 without manual reconstruction or undocumented state."
  ],
  "dependencies": [
    "POST-SUBTASK-036",
    "POST-SUBTASK-037"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 11,
    "adr_ids": 13,
    "gap_ids": 1,
    "requirement_ids": 22,
    "risk_ids": 9
  },
  "effective_traceability_total": 56,
  "end_to_end_validation": "Validate that `artifacts/entities/canonical_people_registry.csv` can be parsed and consumed by `POST-SUBTASK-039` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.",
  "epic_id": "POST-EPIC-004",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-038.json",
  "evidence_state": "PLANNED",
  "execution_lane": "SHARED_CONTRACT",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "EMPIRICALLY_VALIDATED",
  "expected_outputs": [
    "artifacts/entities/canonical_people_registry.csv"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_entity_governance.py",
    "src/aggie_analytics/entities/resolution.py",
    "docs/14_CANONICAL_ENTITY_ARCHITECTURE.md",
    "docs/16_ENTITY_RESOLUTION_AND_REVIEW.md",
    "governance/ENTITY_RESOLUTION_STATES.csv"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_entity_governance.py",
    "src/aggie_analytics/entities/resolution.py",
    "docs/14_CANONICAL_ENTITY_ARCHITECTURE.md",
    "docs/16_ENTITY_RESOLUTION_AND_REVIEW.md",
    "governance/ENTITY_RESOLUTION_STATES.csv"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-038_build_coach_staff_player_roster_recruiting_and_transfer_identity_registries_with.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-042",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100342,
  "in_scope": [
    "Perform the exact action: Build coach, staff, player, roster, recruiting, and transfer identity registries with confidence and review state.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-036`, `POST-SUBTASK-037`.",
    "Demonstrate with saved evidence: Person mappings preserve source IDs, name/team/season/position evidence, transfers, duplicate names, suffixes, and uncertainty; low-confidence cases enter review instead of forced name-only merges.",
    "Demonstrate with saved evidence: The declared output `artifacts/entities/canonical_people_registry.csv` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "Produce, validate, content-hash, and register `artifacts/entities/canonical_people_registry.csv`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-388",
  "labels": [
    "actionable",
    "core-release",
    "entities",
    "post-wave",
    "shared-contract",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-038",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Build coach, staff, player, roster, recruiting, and transfer identity registries with confidence and review state",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24528",
    "jira_updated_at": "2026-08-09T00:03:33.571-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Build canonical team, conference, venue, game, season, and source registries with effective-dated aliases; Validate registry uniqueness, temporal consistency, collisions, and referential completeness.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-013",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-036 complete at required maturity",
    "Dependency POST-SUBTASK-037 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02019",
    "SRCREF-02020",
    "SRCREF-02021",
    "SRCREF-02022"
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
    "tests/test_entity_governance.py",
    "src/aggie_analytics/entities/resolution.py",
    "docs/14_CANONICAL_ENTITY_ARCHITECTURE.md",
    "docs/16_ENTITY_RESOLUTION_AND_REVIEW.md",
    "governance/ENTITY_RESOLUTION_STATES.csv"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/entities/canonical_people_registry.csv` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-038; retain command, exit code, and relevant output.",
      "path": "tests/test_entity_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-038; retain command, exit code, and relevant output.",
      "path": "tools/validate_entities.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/entities/canonical_people_registry.csv",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "INTEGRATION",
      "expectation": "Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.",
      "path": "artifacts/entities/canonical_people_registry.csv",
      "validation_class": "INTEGRATION"
    },
    {
      "classification": "REPRODUCIBILITY",
      "expectation": "Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.",
      "path": "ISSUE_COMPLETION_MANIFEST",
      "validation_class": "REPRODUCIBILITY"
    },
    {
      "classification": "NEW_AUTOMATED_TEST_REQUIRED",
      "expectation": "Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.",
      "path": "NEW_TEST_REQUIRED::POST-SUBTASK-038",
      "validation_class": "NEW_AUTOMATED_TEST_REQUIRED"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-038.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that person mappings preserve source IDs, name/team/season/position evidence, transfers, duplicate names, suffixes, and uncertainty; low-confidence cases enter review instead of forced name-only merges.",
    "Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/entities/canonical_people_registry.csv` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 2 of 3 step in Story POST-STORY-013 (Canonical registries, aliases, and temporal relationships): Build coach, staff, player, roster, recruiting, and transfer identity registries with confidence and review state. Consume only verified prerequisite outputs from `POST-SUBTASK-036`, `POST-SUBTASK-037`. Produce `artifacts/entities/canonical_people_registry.csv`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-039.",
  "source_ids": [
    "GAP-003",
    "GAP-004",
    "GAP-006"
  ],
  "source_refs": [
    "SRCREF-02019",
    "SRCREF-02020",
    "SRCREF-02021",
    "SRCREF-02022",
    "SRCREF-02023",
    "SRCREF-02024",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01565",
    "SRCREF-01566",
    "SRCREF-01568"
  ],
  "specificity_fingerprint": "98a45bb4bebe82f9bbb22cd351658edaf421ed3dc6a8c5bec8b74ed3ca6c585c",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
  ],
  "supporting_source_refs": [
    "SRCREF-02023",
    "SRCREF-02024",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01565",
    "SRCREF-01566",
    "SRCREF-01568"
  ],
  "title": "[POST-SUBTASK-038] Build coach, staff, player, roster, recruiting, and transfer identity registries with confidence and review state",
  "traceability_inherited_from": [
    "POST-SUBTASK-042"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "INTEGRATION",
    "NEW_AUTOMATED_TEST_REQUIRED",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-013: Canonical registries, aliases, and temporal relationships.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-038.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Build coach, staff, player, roster, recruiting, and transfer identity registries with confidence and review state

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-013: Canonical registries, aliases, and temporal relationships.

## Scope

Execute the atomic 2 of 3 step in Story POST-STORY-013 (Canonical registries, aliases, and temporal relationships): Build coach, staff, player, roster, recruiting, and transfer identity registries with confidence and review state. Consume only verified prerequisite outputs from `POST-SUBTASK-036`, `POST-SUBTASK-037`. Produce `artifacts/entities/canonical_people_registry.csv`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-039.

### Explicit In Scope

- Perform the exact action: Build coach, staff, player, roster, recruiting, and transfer identity registries with confidence and review state.
- Consume only verified prerequisite outputs from `POST-SUBTASK-036`, `POST-SUBTASK-037`.
- Demonstrate with saved evidence: Person mappings preserve source IDs, name/team/season/position evidence, transfers, duplicate names, suffixes, and uncertainty; low-confidence cases enter review instead of forced name-only merges.
- Demonstrate with saved evidence: The declared output `artifacts/entities/canonical_people_registry.csv` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/entities/canonical_people_registry.csv`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Build canonical team, conference, venue, game, season, and source registries with effective-dated aliases; Validate registry uniqueness, temporal consistency, collisions, and referential completeness.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-036 complete at required maturity
- Dependency POST-SUBTASK-037 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-036
- POST-SUBTASK-037

## Blocks

- POST-SUBTASK-039

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_entity_governance.py
- src/aggie_analytics/entities/resolution.py
- docs/14_CANONICAL_ENTITY_ARCHITECTURE.md
- docs/16_ENTITY_RESOLUTION_AND_REVIEW.md
- governance/ENTITY_RESOLUTION_STATES.csv

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- entities

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

- artifacts/entities/canonical_people_registry.csv

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-042`
- Inherited from: POST-SUBTASK-042
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 11, "adr_ids": 13, "gap_ids": 1, "requirement_ids": 22, "risk_ids": 9}`

## Acceptance Criteria

1. Person mappings preserve source IDs, name/team/season/position evidence, transfers, duplicate names, suffixes, and uncertainty; low-confidence cases enter review instead of forced name-only merges.
2. The declared output `artifacts/entities/canonical_people_registry.csv` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Definition of Done

1. The atomic scope in POST-SUBTASK-038 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The output set `artifacts/entities/canonical_people_registry.csv` is demonstrably consumable by POST-SUBTASK-039 without manual reconstruction or undocumented state.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_entity_governance.py` — Run as a regression check after completing POST-SUBTASK-038; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_entities.py` — Run as a regression check after completing POST-SUBTASK-038; retain command, exit code, and relevant output.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/entities/canonical_people_registry.csv` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **INTEGRATION** / `INTEGRATION` — `artifacts/entities/canonical_people_registry.csv` — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- **NEW_AUTOMATED_TEST_REQUIRED** / `NEW_AUTOMATED_TEST_REQUIRED` — `NEW_TEST_REQUIRED::POST-SUBTASK-038` — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Required Evidence

- `artifacts/entities/canonical_people_registry.csv` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "EMPIRICALLY_VALIDATED",
  "downstream_consumer": "POST-SUBTASK-039",
  "governance_traceability_gate": "POST-SUBTASK-042",
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

Validate that `artifacts/entities/canonical_people_registry.csv` can be parsed and consumed by `POST-SUBTASK-039` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.

## Expected Maturity After Completion

`EMPIRICALLY_VALIDATED`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-038.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that person mappings preserve source IDs, name/team/season/position evidence, transfers, duplicate names, suffixes, and uncertainty; low-confidence cases enter review instead of forced name-only merges.
- Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/entities/canonical_people_registry.csv` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

## Source References

- SRCREF-02019
- SRCREF-02020
- SRCREF-02021
- SRCREF-02022
- SRCREF-02023
- SRCREF-02024
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01565
- SRCREF-01566
- SRCREF-01568

## AI Context Notes

- Canonical parent Story: POST-STORY-013. Governance traceability gate: POST-SUBTASK-042. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-038.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

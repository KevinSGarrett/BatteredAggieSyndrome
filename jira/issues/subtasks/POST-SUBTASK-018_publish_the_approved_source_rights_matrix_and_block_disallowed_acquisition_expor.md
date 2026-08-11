<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-018_publish_the_approved_source_rights_matrix_and_block_disallowed_acquisition_expor.json -->
# POST-SUBTASK-018 — [POST-SUBTASK-018] Publish the private-research source-use matrix and block raw third-party publication

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "The registry is machine-readable and contains no credentials.",
    "All registered sources and caller-declared public sources admit private acquisition and local training without a rights prerequisite.",
    "Raw third-party export remains independently denied and validity/safety gates remain scoped."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-006. Governance traceability gate: POST-SUBTASK-024. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-018.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "src/aggie_analytics/data/contracts.py",
    "tests/test_data_research.py",
    "configs/source_rights_registry.json",
    "artifacts/source_governance/source_rights_gate_test.json",
    "artifacts/jira_evidence/POST-SUBTASK-018.json"
  ],
  "blocked_reason": "",
  "blocks": [
    "POST-STORY-008",
    "POST-STORY-009",
    "POST-SUBTASK-022",
    "POST-SUBTASK-023",
    "POST-SUBTASK-024",
    "POST-SUBTASK-025",
    "POST-SUBTASK-026",
    "POST-SUBTASK-027"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-018_publish_the_approved_source_rights_matrix_and_block_disallowed_acquisition_expor.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "INTEGRATED",
    "downstream_consumer": "POST-STORY-006",
    "governance_traceability_gate": "POST-SUBTASK-024",
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
  "component": "data-sources",
  "components_expected_to_be_touched": [
    "data-sources",
    "sources"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-018 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-006."
  ],
  "dependencies": [
    "POST-SUBTASK-015",
    "POST-SUBTASK-016",
    "POST-SUBTASK-017"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 1,
    "adr_ids": 4,
    "gap_ids": 1,
    "requirement_ids": 9,
    "risk_ids": 1
  },
  "effective_traceability_total": 16,
  "end_to_end_validation": "Private local acquisition and training succeed independently of rights ambiguity, raw third-party publication remains denied, and actual technical/quality/PIT/safety failures affect only their exact scope. The gate decision must explicitly reevaluate downstream issues: POST-STORY-008, POST-STORY-009, POST-SUBTASK-022, POST-SUBTASK-023, POST-SUBTASK-024, POST-SUBTASK-025, POST-SUBTASK-026, POST-SUBTASK-027.",
  "epic_id": "POST-EPIC-002",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-018.json",
  "evidence_state": "VERIFIED",
  "execution_lane": "SHARED_CONTRACT",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "INTEGRATED",
  "expected_outputs": [
    "configs/source_rights_registry.json",
    "artifacts/source_governance/source_rights_gate_test.json"
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
    "src/aggie_analytics/data/contracts.py",
    "tests/test_data_research.py",
    "docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md"
  ],
  "files_expected_to_be_touched": [
    "src/aggie_analytics/data/contracts.py",
    "tests/test_data_research.py",
    "configs/source_rights_registry.json"
  ],
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
    "src/aggie_analytics/data/contracts.py",
    "tests/test_data_research.py",
    "docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-018_publish_the_approved_source_rights_matrix_and_block_disallowed_acquisition_expor.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-024",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100322,
  "in_scope": [
    "Perform the exact action: Publish the private-research source-use matrix and block raw third-party publication.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-015`, `POST-SUBTASK-016`, `POST-SUBTASK-017`.",
    "Demonstrate with saved evidence: The registry is machine-readable and contains no credentials.",
    "Demonstrate with saved evidence: All registered sources and caller-declared public sources admit private acquisition and local training without a rights prerequisite.",
    "Demonstrate with saved evidence: Raw third-party export remains independently denied and validity/safety gates remain scoped.",
    "Produce, validate, content-hash, and register `configs/source_rights_registry.json`.",
    "Produce, validate, content-hash, and register `artifacts/source_governance/source_rights_gate_test.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-368",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "shared-contract",
    "sources",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-018",
  "maturity_before": "CONTRACT_DEFINED",
  "objective": "Publish the private-research source-use matrix and block raw third-party publication",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24508",
    "jira_updated_at": "2026-08-09T15:42:11.155-0500",
    "last_synced_at": "2026-08-11T06:30:01.758065+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\POST-SUBTASK-177-play-drive-preliminary\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "Done"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Reissue CFBD, SportsDataverse, Open-Meteo, and official A&M/SEC/NCAA decisions under private-research policy; Reissue recruiting, transfer, market, resources, gamebook, and officiating decisions under private-research policy.",
    "Reintroducing a license/terms/redistribution gate for private acquisition or training, or publishing raw third-party payloads without a separate future review.",
    "Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-006",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-015 complete at required maturity",
    "Dependency POST-SUBTASK-016 complete at required maturity",
    "Dependency POST-SUBTASK-017 complete at required maturity"
  ],
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
    "src/aggie_analytics/data/contracts.py",
    "tests/test_data_research.py",
    "docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`configs/source_rights_registry.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "`artifacts/source_governance/source_rights_gate_test.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Nonblocking source-policy metadata recording provider/terms version, access purpose, retention, model-training use, publication boundary, redistribution metadata, source URL, acquisition time, and private-research allow decision.",
    "Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-018; retain command, exit code, and relevant output.",
      "path": "tests/test_data_research.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-018; retain command, exit code, and relevant output.",
      "path": "configs/source_rights_registry.json",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-018; retain command, exit code, and relevant output.",
      "path": "artifacts/source_governance/source_rights_gate_test.json",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "SECURITY",
      "expectation": "Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.",
      "path": "configs/source_rights_registry.json",
      "validation_class": "SECURITY"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/source_governance/source_rights_gate_test.json",
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
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-018.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that the registry is machine-readable and contains no credentials.",
    "Acceptance failure: the evidence cannot demonstrate that all registered sources and caller-declared public sources admit private acquisition and local training without a rights prerequisite.",
    "Acceptance failure: the evidence cannot demonstrate that raw third-party export remains independently denied and validity/safety gates remain scoped."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-006 (Universal private-research acquisition and future-publication boundary): Publish the private-research source-use matrix and block raw third-party publication. Consume only verified prerequisite outputs from `POST-SUBTASK-015`, `POST-SUBTASK-016`, `POST-SUBTASK-017`. Produce `configs/source_rights_registry.json`, `artifacts/source_governance/source_rights_gate_test.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
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
  "specificity_fingerprint": "aa9a265c6cbe609267d567e31720fa2de1ccfe4c9e5850309b8973872d8ad7ff",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
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
  "title": "[POST-SUBTASK-018] Publish the private-research source-use matrix and block raw third-party publication",
  "traceability_inherited_from": [
    "POST-SUBTASK-024"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "END_TO_END",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SECURITY"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-006: Per-source license, terms, and redistribution decisions.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-018.md",
  "workflow_state": "DONE"
}
```

## Objective

Publish the private-research source-use matrix and block raw third-party publication

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-006: Per-source license, terms, and redistribution decisions.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-006 (Universal private-research acquisition and future-publication boundary): Publish the private-research source-use matrix and block raw third-party publication. Consume only verified prerequisite outputs from `POST-SUBTASK-015`, `POST-SUBTASK-016`, `POST-SUBTASK-017`. Produce `configs/source_rights_registry.json`, `artifacts/source_governance/source_rights_gate_test.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Publish the private-research source-use matrix and block raw third-party publication.
- Consume only verified prerequisite outputs from `POST-SUBTASK-015`, `POST-SUBTASK-016`, `POST-SUBTASK-017`.
- Demonstrate with saved evidence: The registry is machine-readable and contains no credentials.
- Demonstrate with saved evidence: All registered sources and caller-declared public sources admit private acquisition and local training without a rights prerequisite.
- Demonstrate with saved evidence: Raw third-party export remains independently denied and validity/safety gates remain scoped.
- Produce, validate, content-hash, and register `configs/source_rights_registry.json`.
- Produce, validate, content-hash, and register `artifacts/source_governance/source_rights_gate_test.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Reissue CFBD, SportsDataverse, Open-Meteo, and official A&M/SEC/NCAA decisions under private-research policy; Reissue recruiting, transfer, market, resources, gamebook, and officiating decisions under private-research policy.
- Reintroducing a license/terms/redistribution gate for private acquisition or training, or publishing raw third-party payloads without a separate future review.
- Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.

## Prerequisites

- Dependency POST-SUBTASK-015 complete at required maturity
- Dependency POST-SUBTASK-016 complete at required maturity
- Dependency POST-SUBTASK-017 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-015
- POST-SUBTASK-016
- POST-SUBTASK-017

## Blocks

- POST-STORY-008
- POST-STORY-009
- POST-SUBTASK-022
- POST-SUBTASK-023
- POST-SUBTASK-024
- POST-SUBTASK-025
- POST-SUBTASK-026
- POST-SUBTASK-027

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
- src/aggie_analytics/data/contracts.py
- tests/test_data_research.py
- docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md

## Files Expected To Be Modified

- src/aggie_analytics/data/contracts.py
- tests/test_data_research.py
- configs/source_rights_registry.json

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

- configs/source_rights_registry.json
- artifacts/source_governance/source_rights_gate_test.json

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

1. The registry is machine-readable and contains no credentials.
2. All registered sources and caller-declared public sources admit private acquisition and local training without a rights prerequisite.
3. Raw third-party export remains independently denied and validity/safety gates remain scoped.

## Definition of Done

1. The atomic scope in POST-SUBTASK-018 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-006.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_data_research.py` — Run as a regression check after completing POST-SUBTASK-018; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `configs/source_rights_registry.json` — Run as a regression check after completing POST-SUBTASK-018; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `artifacts/source_governance/source_rights_gate_test.json` — Run as a regression check after completing POST-SUBTASK-018; retain command, exit code, and relevant output.
- **SECURITY** / `SECURITY` — `configs/source_rights_registry.json` — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- **END_TO_END** / `END_TO_END` — `artifacts/source_governance/source_rights_gate_test.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `configs/source_rights_registry.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- `artifacts/source_governance/source_rights_gate_test.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Nonblocking source-policy metadata recording provider/terms version, access purpose, retention, model-training use, publication boundary, redistribution metadata, source URL, acquisition time, and private-research allow decision.
- Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "INTEGRATED",
  "downstream_consumer": "POST-STORY-006",
  "governance_traceability_gate": "POST-SUBTASK-024",
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

Private local acquisition and training succeed independently of rights ambiguity, raw third-party publication remains denied, and actual technical/quality/PIT/safety failures affect only their exact scope. The gate decision must explicitly reevaluate downstream issues: POST-STORY-008, POST-STORY-009, POST-SUBTASK-022, POST-SUBTASK-023, POST-SUBTASK-024, POST-SUBTASK-025, POST-SUBTASK-026, POST-SUBTASK-027.

## Expected Maturity After Completion

`INTEGRATED`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-018.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that the registry is machine-readable and contains no credentials.
- Acceptance failure: the evidence cannot demonstrate that all registered sources and caller-declared public sources admit private acquisition and local training without a rights prerequisite.
- Acceptance failure: the evidence cannot demonstrate that raw third-party export remains independently denied and validity/safety gates remain scoped.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

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

- Canonical parent Story: POST-STORY-006. Governance traceability gate: POST-SUBTASK-024. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-018.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

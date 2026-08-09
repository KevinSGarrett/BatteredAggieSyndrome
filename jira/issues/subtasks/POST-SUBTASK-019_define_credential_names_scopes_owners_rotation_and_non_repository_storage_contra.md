<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-019_define_credential_names_scopes_owners_rotation_and_non_repository_storage_contra.json -->
# POST-SUBTASK-019 — [POST-SUBTASK-019] Define credential names, scopes, owners, rotation, and non-repository storage contract

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Credential variables are source-scoped and least-privilege where the provider supports scopes.",
    "Rotation/revocation ownership and expiry handling are documented.",
    "No credential value appears in Git-tracked files or evidence."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-007. Governance traceability gate: POST-SUBTASK-024. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-019.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "docs/operations/SOURCE_CREDENTIAL_CONTRACT.md",
    "artifacts/source_governance/credential_contract.redacted.json",
    "artifacts/jira_evidence/POST-SUBTASK-019.json"
  ],
  "blocked_reason": "",
  "blocks": [
    "POST-SUBTASK-020",
    "POST-SUBTASK-021"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-019_define_credential_names_scopes_owners_rotation_and_non_repository_storage_contra.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "IMPLEMENTED",
    "downstream_consumer": "POST-SUBTASK-020",
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
    "The atomic scope in POST-SUBTASK-019 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The output set `docs/operations/SOURCE_CREDENTIAL_CONTRACT.md`, `artifacts/source_governance/credential_contract.redacted.json` is demonstrably consumable by POST-SUBTASK-020 without manual reconstruction or undocumented state."
  ],
  "dependencies": [
    "POST-SUBTASK-015"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 1,
    "adr_ids": 4,
    "gap_ids": 1,
    "requirement_ids": 9,
    "risk_ids": 1
  },
  "effective_traceability_total": 16,
  "end_to_end_validation": "Validate that `docs/operations/SOURCE_CREDENTIAL_CONTRACT.md`, `artifacts/source_governance/credential_contract.redacted.json` can be parsed and consumed by `POST-SUBTASK-020` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.",
  "epic_id": "POST-EPIC-002",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-019.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "IMPLEMENTED",
  "expected_outputs": [
    "docs/operations/SOURCE_CREDENTIAL_CONTRACT.md",
    "artifacts/source_governance/credential_contract.redacted.json"
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
    "docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md"
  ],
  "files_expected_to_be_touched": [
    "docs/operations/SOURCE_CREDENTIAL_CONTRACT.md"
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
    "docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-019_define_credential_names_scopes_owners_rotation_and_non_repository_storage_contra.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-024",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100323,
  "in_scope": [
    "Perform the exact action: Define credential names, scopes, owners, rotation, and non-repository storage contract.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-015`.",
    "Demonstrate with saved evidence: Credential variables are source-scoped and least-privilege where the provider supports scopes.",
    "Demonstrate with saved evidence: Rotation/revocation ownership and expiry handling are documented.",
    "Demonstrate with saved evidence: No credential value appears in Git-tracked files or evidence.",
    "Produce, validate, content-hash, and register `docs/operations/SOURCE_CREDENTIAL_CONTRACT.md`.",
    "Produce, validate, content-hash, and register `artifacts/source_governance/credential_contract.redacted.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-369",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "protected-gate",
    "sources",
    "subtask"
  ],
  "last_content_audit": "2026-08-08",
  "local_id": "POST-SUBTASK-019",
  "maturity_before": "CONTRACT_DEFINED",
  "objective": "Define credential names, scopes, owners, rotation, and non-repository storage contract",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24509",
    "jira_updated_at": "2026-08-09T00:03:25.031-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.",
    "Work assigned to sibling subtasks: Run authenticated and no-key source access smoke tests with rate-limit capture; Validate access readiness and generate source-specific unblock conditions.",
    "Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-007",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-015 complete at required maturity",
    "External credential condition verified by protected POST-SUBTASK-005 redacted inventory and authenticated read-only smoke evidence"
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
    "docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md"
  ],
  "ready": true,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`docs/operations/SOURCE_CREDENTIAL_CONTRACT.md` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "`artifacts/source_governance/credential_contract.redacted.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-019; retain command, exit code, and relevant output.",
      "path": "tests/test_data_research.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-019; retain command, exit code, and relevant output.",
      "path": "tools/validate_repository.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "SECURITY",
      "expectation": "Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.",
      "path": "docs/operations/SOURCE_CREDENTIAL_CONTRACT.md",
      "validation_class": "SECURITY"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/source_governance/credential_contract.redacted.json",
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
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-019.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that credential variables are source-scoped and least-privilege where the provider supports scopes.",
    "Acceptance failure: the evidence cannot demonstrate that rotation/revocation ownership and expiry handling are documented.",
    "Acceptance failure: the evidence cannot demonstrate that no credential value appears in Git-tracked files or evidence.",
    "The verified external credential condition must remain value-free, non-repository, source-scoped, and fail closed if its protected evidence identity drifts."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 1 of 3 step in Story POST-STORY-007 (Credential configuration and access smoke tests): Define credential names, scopes, owners, rotation, and non-repository storage contract. Consume only verified prerequisite outputs from `POST-SUBTASK-015`. Produce `docs/operations/SOURCE_CREDENTIAL_CONTRACT.md`, `artifacts/source_governance/credential_contract.redacted.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-020.",
  "source_ids": [
    "GAP-010",
    "HANDOFF-002",
    "HANDOFF-012",
    "ISSUE-003",
    "ISSUE-004"
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
    "SRCREF-01572",
    "SRCREF-01903",
    "SRCREF-01904"
  ],
  "specificity_fingerprint": "b1c26804c0dcb397da83b6cccbfeefaecfb6d7d0022a5acbae0bc6f82eca03f4",
  "stop_conditions": [
    "Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.",
    "Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.",
    "Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence."
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
    "SRCREF-01572",
    "SRCREF-01903",
    "SRCREF-01904"
  ],
  "title": "[POST-SUBTASK-019] Define credential names, scopes, owners, rotation, and non-repository storage contract",
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
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-007: Credential configuration and access smoke tests.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-019.md",
  "workflow_state": "READY"
}
```

## Objective

Define credential names, scopes, owners, rotation, and non-repository storage contract

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-007: Credential configuration and access smoke tests.

## Scope

Execute the atomic 1 of 3 step in Story POST-STORY-007 (Credential configuration and access smoke tests): Define credential names, scopes, owners, rotation, and non-repository storage contract. Consume only verified prerequisite outputs from `POST-SUBTASK-015`. Produce `docs/operations/SOURCE_CREDENTIAL_CONTRACT.md`, `artifacts/source_governance/credential_contract.redacted.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-020.

### Explicit In Scope

- Perform the exact action: Define credential names, scopes, owners, rotation, and non-repository storage contract.
- Consume only verified prerequisite outputs from `POST-SUBTASK-015`.
- Demonstrate with saved evidence: Credential variables are source-scoped and least-privilege where the provider supports scopes.
- Demonstrate with saved evidence: Rotation/revocation ownership and expiry handling are documented.
- Demonstrate with saved evidence: No credential value appears in Git-tracked files or evidence.
- Produce, validate, content-hash, and register `docs/operations/SOURCE_CREDENTIAL_CONTRACT.md`.
- Produce, validate, content-hash, and register `artifacts/source_governance/credential_contract.redacted.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Run authenticated and no-key source access smoke tests with rate-limit capture; Validate access readiness and generate source-specific unblock conditions.
- Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.

## Prerequisites

- Dependency POST-SUBTASK-015 complete at required maturity
- External credential condition verified by protected POST-SUBTASK-005 redacted inventory and authenticated read-only smoke evidence

## Hard Dependencies

- POST-SUBTASK-015

## Blocks

- POST-SUBTASK-020
- POST-SUBTASK-021

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
- docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md

## Files Expected To Be Modified

- docs/operations/SOURCE_CREDENTIAL_CONTRACT.md

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

- docs/operations/SOURCE_CREDENTIAL_CONTRACT.md
- artifacts/source_governance/credential_contract.redacted.json

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

1. Credential variables are source-scoped and least-privilege where the provider supports scopes.
2. Rotation/revocation ownership and expiry handling are documented.
3. No credential value appears in Git-tracked files or evidence.

## Definition of Done

1. The atomic scope in POST-SUBTASK-019 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The output set `docs/operations/SOURCE_CREDENTIAL_CONTRACT.md`, `artifacts/source_governance/credential_contract.redacted.json` is demonstrably consumable by POST-SUBTASK-020 without manual reconstruction or undocumented state.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_data_research.py` — Run as a regression check after completing POST-SUBTASK-019; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_repository.py` — Run as a regression check after completing POST-SUBTASK-019; retain command, exit code, and relevant output.
- **SECURITY** / `SECURITY` — `docs/operations/SOURCE_CREDENTIAL_CONTRACT.md` — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- **END_TO_END** / `END_TO_END` — `artifacts/source_governance/credential_contract.redacted.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `docs/operations/SOURCE_CREDENTIAL_CONTRACT.md` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- `artifacts/source_governance/credential_contract.redacted.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "IMPLEMENTED",
  "downstream_consumer": "POST-SUBTASK-020",
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

Validate that `docs/operations/SOURCE_CREDENTIAL_CONTRACT.md`, `artifacts/source_governance/credential_contract.redacted.json` can be parsed and consumed by `POST-SUBTASK-020` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

## Expected Maturity After Completion

`IMPLEMENTED`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-019.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that credential variables are source-scoped and least-privilege where the provider supports scopes.
- Acceptance failure: the evidence cannot demonstrate that rotation/revocation ownership and expiry handling are documented.
- Acceptance failure: the evidence cannot demonstrate that no credential value appears in Git-tracked files or evidence.
- The verified external credential condition must remain value-free, non-repository, source-scoped, and fail closed if its protected evidence identity drifts.

## Stop Conditions

- Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.
- Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.
- Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence.

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
- SRCREF-01903
- SRCREF-01904

## AI Context Notes

- Canonical parent Story: POST-STORY-007. Governance traceability gate: POST-SUBTASK-024. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-019.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-017_complete_rights_review_for_recruiting_transfer_market_resources_gamebook_and_off.json -->
# POST-SUBTASK-017 — [POST-SUBTASK-017] Reissue recruiting, transfer, market, resources, gamebook, and officiating decisions under private-research policy

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Every supplemental source is acquisition-eligible for private research; technical readiness and domain quality remain independent.",
    "Genuinely private resources needing unsupplied credentials remain technically unavailable and public substitutes are sought.",
    "Raw third-party publication is denied by project policy."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-006. Governance traceability gate: POST-SUBTASK-024. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-017.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/source_governance/supplemental_rights_decisions.csv",
    "artifacts/jira_evidence/POST-SUBTASK-017.json"
  ],
  "blocked_reason": "",
  "blocks": [
    "POST-SUBTASK-018"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-017_complete_rights_review_for_recruiting_transfer_market_resources_gamebook_and_off.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "IMPLEMENTED",
    "downstream_consumer": "POST-SUBTASK-018",
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
    "The atomic scope in POST-SUBTASK-017 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The output set `artifacts/source_governance/supplemental_rights_decisions.csv` is demonstrably consumable by POST-SUBTASK-018 without manual reconstruction or undocumented state."
  ],
  "dependencies": [
    "POST-SUBTASK-015",
    "POST-SUBTASK-016"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 1,
    "adr_ids": 4,
    "gap_ids": 1,
    "requirement_ids": 9,
    "risk_ids": 1
  },
  "effective_traceability_total": 16,
  "end_to_end_validation": "Validate that `artifacts/source_governance/supplemental_rights_decisions.csv` can be parsed and consumed by `POST-SUBTASK-018` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.",
  "epic_id": "POST-EPIC-002",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-017.json",
  "evidence_state": "VERIFIED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "IMPLEMENTED",
  "expected_outputs": [
    "artifacts/source_governance/supplemental_rights_decisions.csv"
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
  "files_expected_to_be_touched": [],
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
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-017_complete_rights_review_for_recruiting_transfer_market_resources_gamebook_and_off.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-024",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100321,
  "in_scope": [
    "Perform the exact action: Reissue recruiting, transfer, market, resources, gamebook, and officiating decisions under private-research policy.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-015`, `POST-SUBTASK-016`.",
    "Demonstrate with saved evidence: Every supplemental source is acquisition-eligible for private research; technical readiness and domain quality remain independent.",
    "Demonstrate with saved evidence: Genuinely private resources needing unsupplied credentials remain technically unavailable and public substitutes are sought.",
    "Demonstrate with saved evidence: Raw third-party publication is denied by project policy.",
    "Produce, validate, content-hash, and register `artifacts/source_governance/supplemental_rights_decisions.csv`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-367",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "protected-gate",
    "sources",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-017",
  "maturity_before": "CONTRACT_DEFINED",
  "objective": "Reissue recruiting, transfer, market, resources, gamebook, and officiating decisions under private-research policy",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24507",
    "jira_updated_at": "2026-08-09T15:42:10.305-0500",
    "last_synced_at": "2026-08-11T06:30:01.758065+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\POST-SUBTASK-177-play-drive-preliminary\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "Done"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Reissue CFBD, SportsDataverse, Open-Meteo, and official A&M/SEC/NCAA decisions under private-research policy; Publish the private-research source-use matrix and block raw third-party publication.",
    "Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-006",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-015 complete at required maturity",
    "Dependency POST-SUBTASK-016 complete at required maturity"
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
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/source_governance/supplemental_rights_decisions.csv` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-017; retain command, exit code, and relevant output.",
      "path": "tests/test_data_research.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-017; retain command, exit code, and relevant output.",
      "path": "artifacts/source_governance/supplemental_rights_decisions.csv",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "SECURITY",
      "expectation": "Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.",
      "path": "artifacts/source_governance/supplemental_rights_decisions.csv",
      "validation_class": "SECURITY"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/source_governance/supplemental_rights_decisions.csv",
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
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-017.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that every supplemental source is acquisition-eligible for private research; technical readiness and domain quality remain independent.",
    "Acceptance failure: the evidence cannot demonstrate that genuinely private resources needing unsupplied credentials remain technically unavailable and public substitutes are sought.",
    "Acceptance failure: the evidence cannot demonstrate that raw third-party publication is denied by project policy."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 2 of 3 step in Story POST-STORY-006 (Universal private-research acquisition and future-publication boundary): Reissue recruiting, transfer, market, resources, gamebook, and officiating decisions under private-research policy. Consume only verified prerequisite outputs from `POST-SUBTASK-015`, `POST-SUBTASK-016`. Produce `artifacts/source_governance/supplemental_rights_decisions.csv`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-018.",
  "source_ids": [
    "GAP-010",
    "GAP-011",
    "HANDOFF-002",
    "HANDOFF-012",
    "ISSUE-023",
    "ISSUE-025",
    "ISSUE-081"
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
    "SRCREF-01923",
    "SRCREF-01925",
    "SRCREF-01948",
    "SRCREF-01573"
  ],
  "specificity_fingerprint": "566e96fab4da72fa38ae3f71fa17f048b860996dd50c1af8b19386c81db64c17",
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
    "SRCREF-01572",
    "SRCREF-01923",
    "SRCREF-01925",
    "SRCREF-01948",
    "SRCREF-01573"
  ],
  "title": "[POST-SUBTASK-017] Reissue recruiting, transfer, market, resources, gamebook, and officiating decisions under private-research policy",
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
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-017.md",
  "workflow_state": "DONE"
}
```

## Objective

Reissue recruiting, transfer, market, resources, gamebook, and officiating decisions under private-research policy

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-006: Per-source license, terms, and redistribution decisions.

## Scope

Execute the atomic 2 of 3 step in Story POST-STORY-006 (Universal private-research acquisition and future-publication boundary): Reissue recruiting, transfer, market, resources, gamebook, and officiating decisions under private-research policy. Consume only verified prerequisite outputs from `POST-SUBTASK-015`, `POST-SUBTASK-016`. Produce `artifacts/source_governance/supplemental_rights_decisions.csv`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-018.

### Explicit In Scope

- Perform the exact action: Reissue recruiting, transfer, market, resources, gamebook, and officiating decisions under private-research policy.
- Consume only verified prerequisite outputs from `POST-SUBTASK-015`, `POST-SUBTASK-016`.
- Demonstrate with saved evidence: Every supplemental source is acquisition-eligible for private research; technical readiness and domain quality remain independent.
- Demonstrate with saved evidence: Genuinely private resources needing unsupplied credentials remain technically unavailable and public substitutes are sought.
- Demonstrate with saved evidence: Raw third-party publication is denied by project policy.
- Produce, validate, content-hash, and register `artifacts/source_governance/supplemental_rights_decisions.csv`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Reissue CFBD, SportsDataverse, Open-Meteo, and official A&M/SEC/NCAA decisions under private-research policy; Publish the private-research source-use matrix and block raw third-party publication.
- Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.

## Prerequisites

- Dependency POST-SUBTASK-015 complete at required maturity
- Dependency POST-SUBTASK-016 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-015
- POST-SUBTASK-016

## Blocks

- POST-SUBTASK-018

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

- None.

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

- artifacts/source_governance/supplemental_rights_decisions.csv

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

1. Every supplemental source is acquisition-eligible for private research; technical readiness and domain quality remain independent.
2. Genuinely private resources needing unsupplied credentials remain technically unavailable and public substitutes are sought.
3. Raw third-party publication is denied by project policy.

## Definition of Done

1. The atomic scope in POST-SUBTASK-017 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The output set `artifacts/source_governance/supplemental_rights_decisions.csv` is demonstrably consumable by POST-SUBTASK-018 without manual reconstruction or undocumented state.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_data_research.py` — Run as a regression check after completing POST-SUBTASK-017; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `artifacts/source_governance/supplemental_rights_decisions.csv` — Run as a regression check after completing POST-SUBTASK-017; retain command, exit code, and relevant output.
- **SECURITY** / `SECURITY` — `artifacts/source_governance/supplemental_rights_decisions.csv` — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- **END_TO_END** / `END_TO_END` — `artifacts/source_governance/supplemental_rights_decisions.csv` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/source_governance/supplemental_rights_decisions.csv` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
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
  "downstream_consumer": "POST-SUBTASK-018",
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

Validate that `artifacts/source_governance/supplemental_rights_decisions.csv` can be parsed and consumed by `POST-SUBTASK-018` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.

## Expected Maturity After Completion

`IMPLEMENTED`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-017.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that every supplemental source is acquisition-eligible for private research; technical readiness and domain quality remain independent.
- Acceptance failure: the evidence cannot demonstrate that genuinely private resources needing unsupplied credentials remain technically unavailable and public substitutes are sought.
- Acceptance failure: the evidence cannot demonstrate that raw third-party publication is denied by project policy.

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
- SRCREF-01923
- SRCREF-01925
- SRCREF-01948
- SRCREF-01573

## AI Context Notes

- Canonical parent Story: POST-STORY-006. Governance traceability gate: POST-SUBTASK-024. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-017.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

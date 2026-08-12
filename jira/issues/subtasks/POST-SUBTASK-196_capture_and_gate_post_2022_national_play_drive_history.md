<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-196_capture_and_gate_post_2022_national_play_drive_history.json -->
# POST-SUBTASK-196 — [POST-SUBTASK-196] Duplicate audit: post-2022 national play/drive history already covered by POST-SUBTASK-174

## Canonical metadata

```json
{
  "acceptance_control_ids": [
    "AC-061",
    "AC-073",
    "AC-079"
  ],
  "acceptance_criteria": [
    "Prove whether the proposed 2023-2025 national play/drive scope is already represented by an immutable validated dataset before authorizing new implementation.",
    "Pin the existing dataset, manifest, validation, season, play-row, and drive-row identities that establish the duplicate disposition.",
    "Close the live and canonical work unit as a duplicate without creating a second dataset, code path, or scientific claim."
  ],
  "adr_ids": [
    "ADR-005",
    "ADR-006",
    "ADR-094"
  ],
  "ai_context_notes": [
    "The duplicate determination is fully deterministic; no OpenAI request was needed or made.",
    "No model may invent records, timestamps, identities, statistics, or evidence."
  ],
  "blocked_reason": "DUPLICATE_OF_POST-SUBTASK-174 / BAT-531; no new implementation is authorized or required.",
  "blocks": [],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-196_capture_and_gate_post_2022_national_play_drive_history.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "component": "data-sources",
  "components_expected_to_be_touched": [
    "jira",
    "governance"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The exact duplicate evidence is recorded in canonical Jira, generated Jira, repository evidence, and live Jira.",
    "BAT-553 links to BAT-531 as a duplicate and is Done without claiming new historical coverage.",
    "Repository and Jira consistency validators accept the administrative audit record."
  ],
  "dependencies": [],
  "duplicate_of": [
    "POST-SUBTASK-174"
  ],
  "end_to_end_validation": "Verify the existing POST-SUBTASK-174 dataset, manifest, validation, and per-season row identities; verify the live duplicate link, comment, and Done transition; then run Jira consistency gates without materializing data.",
  "epic_id": "POST-EPIC-004",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-196.json",
  "evidence_state": "VERIFIED",
  "execution_lane": "GOVERNANCE",
  "execution_mode": "HISTORICAL_REFERENCE",
  "expected_maturity_after_completion": "DUPLICATE_SCOPE_VERIFIED_NO_NEW_MATURITY",
  "expected_outputs": [
    "jira/records/issues/subtasks/POST-SUBTASK-196_capture_and_gate_post_2022_national_play_drive_history.json",
    "jira/issues/subtasks/POST-SUBTASK-196_capture_and_gate_post_2022_national_play_drive_history.md",
    "artifacts/jira_evidence/POST-SUBTASK-196.json"
  ],
  "files_expected_to_be_read": [
    "artifacts/jira_evidence/POST-SUBTASK-174.json",
    "tools/build_supplemental_play_drive_gap.py",
    "<external-data-root>/manifests/supplemental_play_drive_gap/sha256/813276328568574a1d19173018ba328fd1c4a63a8aa34b34255ef1a2d880020f/supplemental_play_drive_gap_manifest.json"
  ],
  "files_expected_to_be_touched": [
    "jira/records/issues/subtasks/POST-SUBTASK-196_capture_and_gate_post_2022_national_play_drive_history.json",
    "jira/issues/subtasks/POST-SUBTASK-196_capture_and_gate_post_2022_national_play_drive_history.md",
    "artifacts/jira_evidence/POST-SUBTASK-196.json"
  ],
  "files_to_inspect": [
    "artifacts/jira_evidence/POST-SUBTASK-174.json",
    "tools/build_supplemental_play_drive_gap.py"
  ],
  "gap_ids": [
    "GAP-002"
  ],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-196_capture_and_gate_post_2022_national_play_drive_history.md",
  "governance_traceability_gate": "POST-SUBTASK-069",
  "historical_classification": "POST_W25_IMPLEMENTATION",
  "import_id": 100504,
  "in_scope": [
    "Read-only comparison of the proposed 2023-2025 play/drive population with POST-SUBTASK-174 / BAT-531.",
    "Administrative duplicate disposition and preservation of exact evidence identities."
  ],
  "issue_type": "Sub-task",
  "jira_key": "BAT-553",
  "labels": [
    "post-wave",
    "subtask",
    "historical-expansion",
    "duplicate-scope",
    "duplicate-of-bat-531",
    "audit-only",
    "local-id-post-subtask-196"
  ],
  "last_content_audit": "2026-08-11",
  "local_id": "POST-SUBTASK-196",
  "maturity_before": "VALIDATED_RECONCILED_CANDIDATE_ONLY",
  "objective": "Record that the proposed post-2022 national play/drive work is an exact duplicate of POST-SUBTASK-174 / BAT-531 and prevent redundant implementation.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24946",
    "jira_updated_at": "2026-08-12T11:19:31.893-0500",
    "last_synced_at": "2026-08-12T16:21:58.376101+00:00",
    "resolution": "",
    "source_export": "jira/reconciliation/BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "Done"
  },
  "out_of_scope": [
    "Creating another 2023-2025 play/drive dataset, schema, builder, validator, or model input.",
    "Changing the authority, PIT eligibility, or scientific claims of POST-SUBTASK-174.",
    "Protected promotion, forecasts, final completeness, GAP resolution, protected performance, A&M lift, BAS, Aggie Excess, or any scientific claim."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-010",
  "phase": "PHASE-1",
  "prerequisites": [
    "POST-SUBTASK-174 / BAT-531 is merged, validated, and evidence-backed.",
    "The read-only source profile is compared to the existing immutable dataset before any mutation."
  ],
  "primary_source_refs": [
    "SRCREF-02013",
    "SRCREF-02019",
    "SRCREF-02020"
  ],
  "priority": "P0",
  "protected_files_and_interfaces": [
    "AGENTS.md",
    "governance/DO_NOT_DRIFT.md",
    "governance/PROTECTED_ACCEPTANCE_RULES.md",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    "governance/PROTECTED_SPLIT_REGISTRY.csv"
  ],
  "ready": false,
  "record_revision": "1.1",
  "related_to": [
    "POST-SUBTASK-176",
    "POST-SUBTASK-195"
  ],
  "required_evidence": [
    "Existing POST-SUBTASK-174 dataset, manifest, and validation hashes.",
    "Exact 2023-2025 play and drive row-count match.",
    "Live BAT-553 duplicate link, evidence comment, and Done transition."
  ],
  "required_tests": [
    {
      "classification": "END_TO_END",
      "expectation": "The duplicate evidence identities, live Jira disposition, and canonical/generated views agree without any new data artifact.",
      "path": "artifacts/jira_evidence/POST-SUBTASK-196.json",
      "validation_class": "GOVERNANCE_CONSISTENCY"
    }
  ],
  "requirement_ids": [
    "REQ-020",
    "REQ-038",
    "REQ-052",
    "REQ-319"
  ],
  "risk_failure_conditions": [
    "A duplicate dataset or code path is created despite existing complete coverage.",
    "The duplicate disposition omits or mismatches the existing immutable identities or per-season row counts.",
    "The administrative closure is misreported as new historical readiness or a scientific result."
  ],
  "risk_ids": [
    "RISK-038",
    "RISK-050",
    "RISK-241"
  ],
  "schema_version": 2,
  "scope": "Perform a read-only duplicate audit, pin the matching POST-SUBTASK-174 identities, reconcile BAT-553 as a duplicate, and return historical expansion planning to a genuinely missing domain.",
  "source_ids": [
    "GAP-002",
    "HANDOFF-008"
  ],
  "source_refs": [
    "SRCREF-02013",
    "SRCREF-02019",
    "SRCREF-02020",
    "SRCREF-01564",
    "SRCREF-01565",
    "SRCREF-01566"
  ],
  "stop_conditions": [
    "Do not materialize or implement when the proposed population is already fully represented by the verified POST-SUBTASK-174 dataset.",
    "Never weaken no-fabrication, provenance, PIT, target-game, protected-promotion, or scientific boundaries."
  ],
  "supporting_source_refs": [
    "SRCREF-01564",
    "SRCREF-01565",
    "SRCREF-01566"
  ],
  "title": "[POST-SUBTASK-196] Duplicate audit: post-2022 national play/drive history already covered by POST-SUBTASK-174",
  "traceability_inherited_from": [
    "POST-SUBTASK-069"
  ],
  "traceability_resolution": "DIRECT_PLUS_INHERITED_DOMAIN_GATE",
  "unblock_condition": "No implementation unblock exists; this unit is completed as a verified duplicate audit.",
  "why_this_exists": "The initial gap inventory proposed a redundant work unit. Preserving the corrected disposition prevents duplicate data, code, Jira scope, and false coverage claims while retaining an auditable record.",
  "work_packet_path": "",
  "workflow_state": "DONE"
}
```

## Objective

Record that the proposed post-2022 national play/drive work is an exact duplicate of POST-SUBTASK-174 / BAT-531 and prevent redundant implementation.

## Why This Exists

The initial gap inventory proposed a redundant work unit. Preserving the corrected disposition prevents duplicate data, code, Jira scope, and false coverage claims while retaining an auditable record.

## Scope

Perform a read-only duplicate audit, pin the matching POST-SUBTASK-174 identities, reconcile BAT-553 as a duplicate, and return historical expansion planning to a genuinely missing domain.

### Explicit In Scope

- Read-only comparison of the proposed 2023-2025 play/drive population with POST-SUBTASK-174 / BAT-531.
- Administrative duplicate disposition and preservation of exact evidence identities.

### Explicit Out of Scope

- Creating another 2023-2025 play/drive dataset, schema, builder, validator, or model input.
- Changing the authority, PIT eligibility, or scientific claims of POST-SUBTASK-174.
- Protected promotion, forecasts, final completeness, GAP resolution, protected performance, A&M lift, BAS, Aggie Excess, or any scientific claim.

## Prerequisites

- POST-SUBTASK-174 / BAT-531 is merged, validated, and evidence-backed.
- The read-only source profile is compared to the existing immutable dataset before any mutation.

## Hard Dependencies

- None.

## Blocks

- None.

## Read / Inspect First

- artifacts/jira_evidence/POST-SUBTASK-174.json
- tools/build_supplemental_play_drive_gap.py

## Files Expected To Be Modified

- jira/records/issues/subtasks/POST-SUBTASK-196_capture_and_gate_post_2022_national_play_drive_history.json
- jira/issues/subtasks/POST-SUBTASK-196_capture_and_gate_post_2022_national_play_drive_history.md
- artifacts/jira_evidence/POST-SUBTASK-196.json

## Components Expected To Be Touched

- jira
- governance

## Protected Files / Interfaces

- AGENTS.md
- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_ACCEPTANCE_RULES.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv

## Expected Outputs / Artifacts

- jira/records/issues/subtasks/POST-SUBTASK-196_capture_and_gate_post_2022_national_play_drive_history.json
- jira/issues/subtasks/POST-SUBTASK-196_capture_and_gate_post_2022_national_play_drive_history.md
- artifacts/jira_evidence/POST-SUBTASK-196.json

## Direct Requirements

- REQ-020
- REQ-038
- REQ-052
- REQ-319

## Direct Acceptance Controls

- AC-061
- AC-073
- AC-079

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-069`
- Inherited from: POST-SUBTASK-069
- Resolution: `DIRECT_PLUS_INHERITED_DOMAIN_GATE`
- Effective counts: `{}`

## Acceptance Criteria

1. Prove whether the proposed 2023-2025 national play/drive scope is already represented by an immutable validated dataset before authorizing new implementation.
2. Pin the existing dataset, manifest, validation, season, play-row, and drive-row identities that establish the duplicate disposition.
3. Close the live and canonical work unit as a duplicate without creating a second dataset, code path, or scientific claim.

## Definition of Done

1. The exact duplicate evidence is recorded in canonical Jira, generated Jira, repository evidence, and live Jira.
2. BAT-553 links to BAT-531 as a duplicate and is Done without claiming new historical coverage.
3. Repository and Jira consistency validators accept the administrative audit record.

## Required Tests / Validation

- **END_TO_END** / `GOVERNANCE_CONSISTENCY` — `artifacts/jira_evidence/POST-SUBTASK-196.json` — The duplicate evidence identities, live Jira disposition, and canonical/generated views agree without any new data artifact.

## Required Evidence

- Existing POST-SUBTASK-174 dataset, manifest, and validation hashes.
- Exact 2023-2025 play and drive row-count match.
- Live BAT-553 duplicate link, evidence comment, and Done transition.

## Completion Evidence Contract

```json
{}
```

## End-to-End Validation Requirement

Verify the existing POST-SUBTASK-174 dataset, manifest, validation, and per-season row identities; verify the live duplicate link, comment, and Done transition; then run Jira consistency gates without materializing data.

## Expected Maturity After Completion

`DUPLICATE_SCOPE_VERIFIED_NO_NEW_MATURITY`

## Risk / Failure Conditions

- A duplicate dataset or code path is created despite existing complete coverage.
- The duplicate disposition omits or mismatches the existing immutable identities or per-season row counts.
- The administrative closure is misreported as new historical readiness or a scientific result.

## Stop Conditions

- Do not materialize or implement when the proposed population is already fully represented by the verified POST-SUBTASK-174 dataset.
- Never weaken no-fabrication, provenance, PIT, target-game, protected-promotion, or scientific boundaries.

## Source References

- SRCREF-02013
- SRCREF-02019
- SRCREF-02020
- SRCREF-01564
- SRCREF-01565
- SRCREF-01566

## AI Context Notes

- The duplicate determination is fully deterministic; no OpenAI request was needed or made.
- No model may invent records, timestamps, identities, statistics, or evidence.

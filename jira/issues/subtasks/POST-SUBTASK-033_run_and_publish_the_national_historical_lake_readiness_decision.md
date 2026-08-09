<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-033_run_and_publish_the_national_historical_lake_readiness_decision.json -->
# POST-SUBTASK-033 — [POST-SUBTASK-033] Run and publish the national historical-lake readiness decision

## Canonical metadata

```json
{
  "acceptance_control_ids": [
    "AC-075",
    "AC-079",
    "AC-080",
    "AC-182"
  ],
  "acceptance_criteria": [
    "Repeated identical bytes resolve to the same content identity while changed/corrected bytes create a new immutable version without rewriting prior evidence.",
    "The master manifest links every accepted snapshot to source contract, request, hash, parser/schema version, coverage, quality, and nonblocking source-policy metadata and reproduces population counts.",
    "GAP-002 remains open unless actual national history—not fixtures, reconnaissance samples, or starter code—meets immutable, manifest, readback, and coverage requirements.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [
    "ADR-084",
    "ADR-119",
    "ADR-191",
    "ADR-269",
    "ADR-291",
    "ADR-317"
  ],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-011. Governance traceability gate: POST-SUBTASK-033. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-033.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/data_lake/national_lake_readiness.json",
    "artifacts/jira_evidence/POST-SUBTASK-033.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-031;POST-SUBTASK-032",
  "blocks": [
    "POST-EPIC-004",
    "POST-STORY-012",
    "POST-SUBTASK-034",
    "POST-SUBTASK-035",
    "POST-SUBTASK-036",
    "POST-SUBTASK-072"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-033_run_and_publish_the_national_historical_lake_readiness_decision.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-011",
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
    "The atomic scope in POST-SUBTASK-033 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-011."
  ],
  "dependencies": [
    "POST-SUBTASK-027",
    "POST-SUBTASK-030",
    "POST-SUBTASK-031",
    "POST-SUBTASK-032"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 4,
    "adr_ids": 6,
    "gap_ids": 1,
    "requirement_ids": 8,
    "risk_ids": 5
  },
  "effective_traceability_total": 24,
  "end_to_end_validation": "Pinned manifests reconstruct the accepted raw lake from immutable bytes while preserving every missing season, unavailable domain, correction, and technical or quality blocker. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-004, POST-STORY-012, POST-SUBTASK-034, POST-SUBTASK-035, POST-SUBTASK-036, POST-SUBTASK-072.",
  "epic_id": "POST-EPIC-003",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-033.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/data_lake/national_lake_readiness.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/ADR_INDEX.csv",
    "governance/REQUIREMENTS_INDEX.csv",
    "tests/test_w19_foundation.py",
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
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/ADR_INDEX.csv",
    "governance/REQUIREMENTS_INDEX.csv",
    "tests/test_w19_foundation.py",
    "docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md"
  ],
  "gap_ids": [
    "GAP-002"
  ],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-033_run_and_publish_the_national_historical_lake_readiness_decision.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-033",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100337,
  "in_scope": [
    "Perform the exact action: Run and publish the national historical-lake readiness decision.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-027`, `POST-SUBTASK-030`, `POST-SUBTASK-031`, `POST-SUBTASK-032`.",
    "Demonstrate with saved evidence: Repeated identical bytes resolve to the same content identity while changed/corrected bytes create a new immutable version without rewriting prior evidence.",
    "Demonstrate with saved evidence: The master manifest links every accepted snapshot to source contract, request, hash, parser/schema version, coverage, quality, and nonblocking source-policy metadata and reproduces population counts.",
    "Demonstrate with saved evidence: GAP-002 remains open unless actual national history—not fixtures, reconnaissance samples, or starter code—meets immutable, manifest, readback, and coverage requirements.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `artifacts/data_lake/national_lake_readiness.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-383",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "protected-gate",
    "raw-data",
    "subtask",
    "historical-expansion"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-033",
  "maturity_before": "SCAFFOLD",
  "objective": "Run and publish the national historical-lake readiness decision",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24523",
    "jira_updated_at": "2026-08-09T00:05:02.328-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Enforce content-addressed raw snapshots, correction lineage, quarantine, and source-policy storage metadata; Build the cross-domain acquisition, schema, quality, and source-to-snapshot provenance manifests."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-011",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-027 complete at required maturity",
    "Dependency POST-SUBTASK-030 complete at required maturity",
    "Dependency POST-SUBTASK-031 complete at required maturity",
    "Dependency POST-SUBTASK-032 complete at required maturity"
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
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/ADR_INDEX.csv",
    "governance/REQUIREMENTS_INDEX.csv",
    "tests/test_w19_foundation.py",
    "docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/data_lake/national_lake_readiness.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-033; retain command, exit code, and relevant output.",
      "path": "tests/test_w19_foundation.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/data_lake/national_lake_readiness.json",
      "validation_class": "END_TO_END"
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
      "path": "NEW_TEST_REQUIRED::POST-SUBTASK-033",
      "validation_class": "NEW_AUTOMATED_TEST_REQUIRED"
    }
  ],
  "requirement_ids": [
    "REQ-039",
    "REQ-053",
    "REQ-316",
    "REQ-323",
    "REQ-324",
    "REQ-493",
    "REQ-618",
    "REQ-668"
  ],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-033.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that repeated identical bytes resolve to the same content identity while changed/corrected bytes create a new immutable version without rewriting prior evidence.",
    "Acceptance failure: the evidence cannot demonstrate that the master manifest links every accepted snapshot to source contract, request, hash, parser/schema version, coverage, quality, and nonblocking source-policy metadata and reproduces population counts.",
    "Acceptance failure: the evidence cannot demonstrate that gAP-002 remains open unless actual national history—not fixtures, reconnaissance samples, or starter code—meets immutable, manifest, readback, and coverage requirements.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [
    "RISK-074",
    "RISK-108",
    "RISK-113",
    "RISK-124",
    "RISK-248"
  ],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-011 (Immutable raw store, manifests, provenance, and population audit): Run and publish the national historical-lake readiness decision. Consume only verified prerequisite outputs from `POST-SUBTASK-027`, `POST-SUBTASK-030`, `POST-SUBTASK-031`, `POST-SUBTASK-032`. Produce `artifacts/data_lake/national_lake_readiness.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
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
    "SRCREF-01564",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "specificity_fingerprint": "2e65aaff223cdd273341351bb52975e02e88ede6e28f1cadd84a1bbd0596c52a",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
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
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "title": "[POST-SUBTASK-033] Run and publish the national historical-lake readiness decision",
  "traceability_inherited_from": [],
  "traceability_resolution": "DIRECT_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "END_TO_END",
    "NEW_AUTOMATED_TEST_REQUIRED",
    "REGRESSION",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-011: Immutable raw store, manifests, provenance, and population audit.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-033.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Run and publish the national historical-lake readiness decision

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-011: Immutable raw store, manifests, provenance, and population audit.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-011 (Immutable raw store, manifests, provenance, and population audit): Run and publish the national historical-lake readiness decision. Consume only verified prerequisite outputs from `POST-SUBTASK-027`, `POST-SUBTASK-030`, `POST-SUBTASK-031`, `POST-SUBTASK-032`. Produce `artifacts/data_lake/national_lake_readiness.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Run and publish the national historical-lake readiness decision.
- Consume only verified prerequisite outputs from `POST-SUBTASK-027`, `POST-SUBTASK-030`, `POST-SUBTASK-031`, `POST-SUBTASK-032`.
- Demonstrate with saved evidence: Repeated identical bytes resolve to the same content identity while changed/corrected bytes create a new immutable version without rewriting prior evidence.
- Demonstrate with saved evidence: The master manifest links every accepted snapshot to source contract, request, hash, parser/schema version, coverage, quality, and nonblocking source-policy metadata and reproduces population counts.
- Demonstrate with saved evidence: GAP-002 remains open unless actual national history—not fixtures, reconnaissance samples, or starter code—meets immutable, manifest, readback, and coverage requirements.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/data_lake/national_lake_readiness.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Enforce content-addressed raw snapshots, correction lineage, quarantine, and source-policy storage metadata; Build the cross-domain acquisition, schema, quality, and source-to-snapshot provenance manifests.

## Prerequisites

- Dependency POST-SUBTASK-027 complete at required maturity
- Dependency POST-SUBTASK-030 complete at required maturity
- Dependency POST-SUBTASK-031 complete at required maturity
- Dependency POST-SUBTASK-032 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-027
- POST-SUBTASK-030
- POST-SUBTASK-031
- POST-SUBTASK-032

## Blocks

- POST-EPIC-004
- POST-STORY-012
- POST-SUBTASK-034
- POST-SUBTASK-035
- POST-SUBTASK-036
- POST-SUBTASK-072

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- governance/ADR_INDEX.csv
- governance/REQUIREMENTS_INDEX.csv
- tests/test_w19_foundation.py
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

- artifacts/data_lake/national_lake_readiness.json

## Direct Requirements

- REQ-039
- REQ-053
- REQ-316
- REQ-323
- REQ-324
- REQ-493
- REQ-618
- REQ-668

## Direct Acceptance Controls

- AC-075
- AC-079
- AC-080
- AC-182

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-033`
- Inherited from: None
- Resolution: `DIRECT_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 4, "adr_ids": 6, "gap_ids": 1, "requirement_ids": 8, "risk_ids": 5}`

## Acceptance Criteria

1. Repeated identical bytes resolve to the same content identity while changed/corrected bytes create a new immutable version without rewriting prior evidence.
2. The master manifest links every accepted snapshot to source contract, request, hash, parser/schema version, coverage, quality, and nonblocking source-policy metadata and reproduces population counts.
3. GAP-002 remains open unless actual national history—not fixtures, reconnaissance samples, or starter code—meets immutable, manifest, readback, and coverage requirements.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. The atomic scope in POST-SUBTASK-033 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-011.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w19_foundation.py` — Run as a regression check after completing POST-SUBTASK-033; retain command, exit code, and relevant output.
- **END_TO_END** / `END_TO_END` — `artifacts/data_lake/national_lake_readiness.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- **NEW_AUTOMATED_TEST_REQUIRED** / `NEW_AUTOMATED_TEST_REQUIRED` — `NEW_TEST_REQUIRED::POST-SUBTASK-033` — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Required Evidence

- `artifacts/data_lake/national_lake_readiness.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "PRODUCTION_READY",
  "downstream_consumer": "POST-STORY-011",
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

Pinned manifests reconstruct the accepted raw lake from immutable bytes while preserving every missing season, unavailable domain, correction, and technical or quality blocker. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-004, POST-STORY-012, POST-SUBTASK-034, POST-SUBTASK-035, POST-SUBTASK-036, POST-SUBTASK-072.

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-033.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that repeated identical bytes resolve to the same content identity while changed/corrected bytes create a new immutable version without rewriting prior evidence.
- Acceptance failure: the evidence cannot demonstrate that the master manifest links every accepted snapshot to source contract, request, hash, parser/schema version, coverage, quality, and nonblocking source-policy metadata and reproduces population counts.
- Acceptance failure: the evidence cannot demonstrate that gAP-002 remains open unless actual national history—not fixtures, reconnaissance samples, or starter code—meets immutable, manifest, readback, and coverage requirements.
- Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

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
- SRCREF-02116
- SRCREF-02117
- SRCREF-02118

## AI Context Notes

- Canonical parent Story: POST-STORY-011. Governance traceability gate: POST-SUBTASK-033. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-033.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-024_establish_source_api_schema_terms_drift_baselines_and_monitoring_inputs.json -->
# POST-SUBTASK-024 — [POST-SUBTASK-024] Establish source API/schema/terms drift baselines and monitoring inputs

## Canonical metadata

```json
{
  "acceptance_control_ids": [
    "AC-225"
  ],
  "acceptance_criteria": [
    "Baseline captures endpoint/version, schema hash, terms metadata, expected freshness, and upstream dependencies.",
    "A changed contract cannot silently overwrite the prior baseline.",
    "Detected technical/schema/quality drift quarantines only the affected scope before downstream training; terms drift is metadata-only for private use."
  ],
  "adr_ids": [
    "ADR-079",
    "ADR-088",
    "ADR-109",
    "ADR-312"
  ],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-008. Governance traceability gate: POST-SUBTASK-024. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-024.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "configs/source_drift_registry.json",
    "artifacts/source_governance/source_drift_baseline.json",
    "artifacts/jira_evidence/POST-SUBTASK-024.json"
  ],
  "blocked_reason": "",
  "blocks": [
    "POST-EPIC-003",
    "POST-EPIC-014",
    "POST-STORY-036",
    "POST-STORY-043",
    "POST-SUBTASK-106",
    "POST-SUBTASK-107",
    "POST-SUBTASK-108",
    "POST-SUBTASK-127",
    "POST-SUBTASK-128",
    "POST-SUBTASK-129"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-024_establish_source_api_schema_terms_drift_baselines_and_monitoring_inputs.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "OPERATING",
    "downstream_consumer": "POST-STORY-008",
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
  "critical_path": false,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-024 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-008."
  ],
  "dependencies": [
    "POST-SUBTASK-018",
    "POST-SUBTASK-021",
    "POST-SUBTASK-022",
    "POST-SUBTASK-023"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 1,
    "adr_ids": 4,
    "gap_ids": 1,
    "requirement_ids": 9,
    "risk_ids": 1
  },
  "effective_traceability_total": 16,
  "end_to_end_validation": "Exercise the complete Production acquisition contracts, rate limits, fallbacks, and drift hooks path and verify downstream consumption of pinned outputs. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-003, POST-EPIC-014, POST-STORY-036, POST-STORY-043, POST-SUBTASK-106, POST-SUBTASK-107, POST-SUBTASK-108, POST-SUBTASK-127, POST-SUBTASK-128, POST-SUBTASK-129.",
  "epic_id": "POST-EPIC-002",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-024.json",
  "evidence_state": "PLANNED",
  "execution_lane": "OPERATIONS",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "OPERATING",
  "expected_outputs": [
    "artifacts/source_governance/source_drift_baseline.json",
    "configs/source_drift_registry.json"
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
    "src/aggie_analytics/data/adapters.py",
    "docs/data_research/w06/SOURCE_ACCESS_LICENSE_MATRIX.csv",
    "docs/data_research/w06/SOURCE_PRIORITY_DECISIONS.md",
    "docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md"
  ],
  "files_expected_to_be_touched": [
    "configs/source_drift_registry.json"
  ],
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
    "src/aggie_analytics/data/adapters.py",
    "docs/data_research/w06/SOURCE_ACCESS_LICENSE_MATRIX.csv",
    "docs/data_research/w06/SOURCE_PRIORITY_DECISIONS.md",
    "docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md"
  ],
  "gap_ids": [
    "GAP-010"
  ],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-024_establish_source_api_schema_terms_drift_baselines_and_monitoring_inputs.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-024",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100328,
  "in_scope": [
    "Perform the exact action: Establish source API/schema/terms drift baselines and monitoring inputs.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-018`, `POST-SUBTASK-021`, `POST-SUBTASK-022`, `POST-SUBTASK-023`.",
    "Demonstrate with saved evidence: Baseline captures endpoint/version, schema hash, terms metadata, expected freshness, and upstream dependencies.",
    "Demonstrate with saved evidence: A changed contract cannot silently overwrite the prior baseline.",
    "Demonstrate with saved evidence: Detected technical/schema/quality drift quarantines only the affected scope before downstream training; terms drift is metadata-only for private use.",
    "Produce, validate, content-hash, and register `artifacts/source_governance/source_drift_baseline.json`.",
    "Produce, validate, content-hash, and register `configs/source_drift_registry.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-374",
  "labels": [
    "actionable",
    "core-release",
    "operations",
    "post-wave",
    "sources",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-024",
  "maturity_before": "CONTRACT_DEFINED",
  "objective": "Establish source API/schema/terms drift baselines and monitoring inputs",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24514",
    "jira_updated_at": "2026-08-09T00:03:28.248-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Create source-specific endpoint, parameter, pagination, season, and version acquisition specifications; Implement compliant retries, caching, rate-limit handling, and fallback activation.",
    "Reintroducing a license/terms/redistribution gate for private acquisition or training, or publishing raw third-party payloads without a separate future review.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-008",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-018 complete at required maturity",
    "Dependency POST-SUBTASK-021 complete at required maturity",
    "Dependency POST-SUBTASK-022 complete at required maturity",
    "Dependency POST-SUBTASK-023 complete at required maturity"
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
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/ADR_INDEX.csv",
    "governance/REQUIREMENTS_INDEX.csv",
    "src/aggie_analytics/data/adapters.py",
    "docs/data_research/w06/SOURCE_ACCESS_LICENSE_MATRIX.csv",
    "docs/data_research/w06/SOURCE_PRIORITY_DECISIONS.md",
    "docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md"
  ],
  "ready": true,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/source_governance/source_drift_baseline.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "`configs/source_drift_registry.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Nonblocking source-policy metadata recording provider/terms version, access purpose, retention, model-training use, publication boundary, redistribution metadata, source URL, acquisition time, and private-research allow decision.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-024; retain command, exit code, and relevant output.",
      "path": "tests/test_data_research.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "PUBLICATION_BOUNDARY_REVIEW",
      "expectation": "Verify license/terms/redistribution metadata is preserved without blocking private acquisition or training, and that raw third-party publication remains disabled.",
      "path": "MANUAL",
      "validation_class": "PUBLICATION_BOUNDARY_REVIEW"
    },
    {
      "classification": "MANUAL",
      "expectation": "Verify the private-use decision, metadata state, technical/quality scope, and future-publication boundary.",
      "path": "artifacts/source_governance/source_drift_baseline.json",
      "validation_class": "MANUAL"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/source_governance/source_drift_baseline.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "OPERATIONS",
      "expectation": "Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.",
      "path": "artifacts/source_governance/source_drift_baseline.json",
      "validation_class": "OPERATIONS"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "configs/source_drift_registry.json",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "REPRODUCIBILITY",
      "expectation": "Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.",
      "path": "ISSUE_COMPLETION_MANIFEST",
      "validation_class": "REPRODUCIBILITY"
    }
  ],
  "requirement_ids": [
    "REQ-054",
    "REQ-055",
    "REQ-057",
    "REQ-215",
    "REQ-241",
    "REQ-244",
    "REQ-253",
    "REQ-548",
    "REQ-697"
  ],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-024.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that baseline captures endpoint/version, schema hash, terms metadata, expected freshness, and upstream dependencies.",
    "Acceptance failure: the evidence cannot demonstrate that a changed contract cannot silently overwrite the prior baseline.",
    "Acceptance failure: the evidence cannot demonstrate that detected technical/schema/quality drift quarantines only the affected scope before downstream training; terms drift is metadata-only for private use."
  ],
  "risk_ids": [
    "RISK-054"
  ],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-008 (Production acquisition contracts, rate limits, fallbacks, and drift hooks): Establish source API/schema/terms drift baselines and monitoring inputs. Consume only verified prerequisite outputs from `POST-SUBTASK-018`, `POST-SUBTASK-021`, `POST-SUBTASK-022`, `POST-SUBTASK-023`. Produce `artifacts/source_governance/source_drift_baseline.json`, `configs/source_drift_registry.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
  "source_ids": [
    "GAP-010",
    "HANDOFF-002",
    "HANDOFF-003",
    "HANDOFF-012",
    "ISSUE-002",
    "ISSUE-028"
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
    "SRCREF-01889",
    "SRCREF-01902",
    "SRCREF-01928",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "specificity_fingerprint": "d18062f9ba8a1d145c62f72003eaf3b4e9ea299e0b115b58831a1b267e84c1a8",
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
    "SRCREF-01889",
    "SRCREF-01902",
    "SRCREF-01928",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "title": "[POST-SUBTASK-024] Establish source API/schema/terms drift baselines and monitoring inputs",
  "traceability_inherited_from": [],
  "traceability_resolution": "DIRECT_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "END_TO_END",
    "MANUAL",
    "OPERATIONS",
    "PUBLICATION_BOUNDARY_REVIEW",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-008: Production acquisition contracts, rate limits, fallbacks, and drift hooks.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-024.md",
  "workflow_state": "READY"
}
```

## Objective

Establish source API/schema/terms drift baselines and monitoring inputs

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-008: Production acquisition contracts, rate limits, fallbacks, and drift hooks.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-008 (Production acquisition contracts, rate limits, fallbacks, and drift hooks): Establish source API/schema/terms drift baselines and monitoring inputs. Consume only verified prerequisite outputs from `POST-SUBTASK-018`, `POST-SUBTASK-021`, `POST-SUBTASK-022`, `POST-SUBTASK-023`. Produce `artifacts/source_governance/source_drift_baseline.json`, `configs/source_drift_registry.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Establish source API/schema/terms drift baselines and monitoring inputs.
- Consume only verified prerequisite outputs from `POST-SUBTASK-018`, `POST-SUBTASK-021`, `POST-SUBTASK-022`, `POST-SUBTASK-023`.
- Demonstrate with saved evidence: Baseline captures endpoint/version, schema hash, terms metadata, expected freshness, and upstream dependencies.
- Demonstrate with saved evidence: A changed contract cannot silently overwrite the prior baseline.
- Demonstrate with saved evidence: Detected technical/schema/quality drift quarantines only the affected scope before downstream training; terms drift is metadata-only for private use.
- Produce, validate, content-hash, and register `artifacts/source_governance/source_drift_baseline.json`.
- Produce, validate, content-hash, and register `configs/source_drift_registry.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Create source-specific endpoint, parameter, pagination, season, and version acquisition specifications; Implement compliant retries, caching, rate-limit handling, and fallback activation.
- Reintroducing a license/terms/redistribution gate for private acquisition or training, or publishing raw third-party payloads without a separate future review.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-018 complete at required maturity
- Dependency POST-SUBTASK-021 complete at required maturity
- Dependency POST-SUBTASK-022 complete at required maturity
- Dependency POST-SUBTASK-023 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-018
- POST-SUBTASK-021
- POST-SUBTASK-022
- POST-SUBTASK-023

## Blocks

- POST-EPIC-003
- POST-EPIC-014
- POST-STORY-036
- POST-STORY-043
- POST-SUBTASK-106
- POST-SUBTASK-107
- POST-SUBTASK-108
- POST-SUBTASK-127
- POST-SUBTASK-128
- POST-SUBTASK-129

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
- src/aggie_analytics/data/adapters.py
- docs/data_research/w06/SOURCE_ACCESS_LICENSE_MATRIX.csv
- docs/data_research/w06/SOURCE_PRIORITY_DECISIONS.md
- docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md

## Files Expected To Be Modified

- configs/source_drift_registry.json

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

- artifacts/source_governance/source_drift_baseline.json
- configs/source_drift_registry.json

## Direct Requirements

- REQ-054
- REQ-055
- REQ-057
- REQ-215
- REQ-241
- REQ-244
- REQ-253
- REQ-548
- REQ-697

## Direct Acceptance Controls

- AC-225

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-024`
- Inherited from: None
- Resolution: `DIRECT_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 1, "adr_ids": 4, "gap_ids": 1, "requirement_ids": 9, "risk_ids": 1}`

## Acceptance Criteria

1. Baseline captures endpoint/version, schema hash, terms metadata, expected freshness, and upstream dependencies.
2. A changed contract cannot silently overwrite the prior baseline.
3. Detected technical/schema/quality drift quarantines only the affected scope before downstream training; terms drift is metadata-only for private use.

## Definition of Done

1. The atomic scope in POST-SUBTASK-024 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-008.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_data_research.py` — Run as a regression check after completing POST-SUBTASK-024; retain command, exit code, and relevant output.
- **PUBLICATION_BOUNDARY_REVIEW** / `PUBLICATION_BOUNDARY_REVIEW` — `MANUAL` — Verify license/terms/redistribution metadata is preserved without blocking private acquisition or training, and that raw third-party publication remains disabled.
- **MANUAL** / `MANUAL` — `artifacts/source_governance/source_drift_baseline.json` — Verify the private-use decision, metadata state, technical/quality scope, and future-publication boundary.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/source_governance/source_drift_baseline.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **OPERATIONS** / `OPERATIONS` — `artifacts/source_governance/source_drift_baseline.json` — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- **END_TO_END** / `END_TO_END` — `configs/source_drift_registry.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/source_governance/source_drift_baseline.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- `configs/source_drift_registry.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Nonblocking source-policy metadata recording provider/terms version, access purpose, retention, model-training use, publication boundary, redistribution metadata, source URL, acquisition time, and private-research allow decision.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "OPERATING",
  "downstream_consumer": "POST-STORY-008",
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

Exercise the complete Production acquisition contracts, rate limits, fallbacks, and drift hooks path and verify downstream consumption of pinned outputs. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-003, POST-EPIC-014, POST-STORY-036, POST-STORY-043, POST-SUBTASK-106, POST-SUBTASK-107, POST-SUBTASK-108, POST-SUBTASK-127, POST-SUBTASK-128, POST-SUBTASK-129.

## Expected Maturity After Completion

`OPERATING`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-024.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that baseline captures endpoint/version, schema hash, terms metadata, expected freshness, and upstream dependencies.
- Acceptance failure: the evidence cannot demonstrate that a changed contract cannot silently overwrite the prior baseline.
- Acceptance failure: the evidence cannot demonstrate that detected technical/schema/quality drift quarantines only the affected scope before downstream training; terms drift is metadata-only for private use.

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
- SRCREF-01889
- SRCREF-01902
- SRCREF-01928
- SRCREF-02116
- SRCREF-02117
- SRCREF-02118

## AI Context Notes

- Canonical parent Story: POST-STORY-008. Governance traceability gate: POST-SUBTASK-024. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-024.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

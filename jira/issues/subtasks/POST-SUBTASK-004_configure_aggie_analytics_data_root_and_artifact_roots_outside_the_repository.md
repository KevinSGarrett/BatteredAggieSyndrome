<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-004_configure_aggie_analytics_data_root_and_artifact_roots_outside_the_repository.json -->
# POST-SUBTASK-004 — [POST-SUBTASK-004] Configure AGGIE_ANALYTICS_DATA_ROOT and artifact roots outside the repository

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Configured roots are absolute, writable, outside the Git repository, and survive process restart.",
    "Raw, curated, model, forecast, log, backup, and quarantine roots are separated.",
    "A path safety test rejects repository-internal bulk-data roots."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-002. Governance traceability gate: POST-SUBTASK-009. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-004.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "src/aggie_analytics/operations/environment.py",
    "tests/test_w23_operations.py",
    "docs/operations/LOCAL_RUNTIME_PATHS.md",
    "src/aggie_analytics/operations/benchmark.py",
    "artifacts/implementation_preflight/local_path_contract.json",
    "artifacts/jira_evidence/POST-SUBTASK-004.json"
  ],
  "blocked_reason": "",
  "blocks": [
    "POST-SUBTASK-005",
    "POST-SUBTASK-006"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-004_configure_aggie_analytics_data_root_and_artifact_roots_outside_the_repository.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "IMPLEMENTED",
    "downstream_consumer": "POST-SUBTASK-005",
    "governance_traceability_gate": "POST-SUBTASK-009",
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
  "component": "operations-security",
  "components_expected_to_be_touched": [
    "operations-security",
    "environment"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-004 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The output set `artifacts/implementation_preflight/local_path_contract.json`, `docs/operations/LOCAL_RUNTIME_PATHS.md` is demonstrably consumable by POST-SUBTASK-005 without manual reconstruction or undocumented state."
  ],
  "dependencies": [
    "POST-SUBTASK-001"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 3,
    "adr_ids": 4,
    "gap_ids": 1,
    "requirement_ids": 5,
    "risk_ids": 2
  },
  "effective_traceability_total": 15,
  "end_to_end_validation": "Validate that `artifacts/implementation_preflight/local_path_contract.json`, `docs/operations/LOCAL_RUNTIME_PATHS.md` can be parsed and consumed by `POST-SUBTASK-005` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.",
  "epic_id": "POST-EPIC-001",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-004.json",
  "evidence_state": "VERIFIED",
  "execution_lane": "OPERATIONS",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "IMPLEMENTED",
  "expected_outputs": [
    "artifacts/implementation_preflight/local_path_contract.json",
    "docs/operations/LOCAL_RUNTIME_PATHS.md"
  ],
  "files_expected_to_be_read": [
    "AGENTS.md",
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/operations/benchmark.py",
    "docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md",
    "docs/operations/TARGET_HARDWARE_BENCHMARK.md",
    "src/aggie_analytics/operations/environment.py",
    "tests/test_w23_operations.py"
  ],
  "files_expected_to_be_touched": [
    "src/aggie_analytics/operations/environment.py",
    "tests/test_w23_operations.py",
    "docs/operations/LOCAL_RUNTIME_PATHS.md",
    "src/aggie_analytics/operations/benchmark.py"
  ],
  "files_to_inspect": [
    "AGENTS.md",
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/operations/benchmark.py",
    "docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md",
    "docs/operations/TARGET_HARDWARE_BENCHMARK.md",
    "src/aggie_analytics/operations/environment.py",
    "tests/test_w23_operations.py"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-004_configure_aggie_analytics_data_root_and_artifact_roots_outside_the_repository.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-009",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100308,
  "in_scope": [
    "Perform the exact action: Configure AGGIE_ANALYTICS_DATA_ROOT and artifact roots outside the repository.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-001`.",
    "Demonstrate with saved evidence: Configured roots are absolute, writable, outside the Git repository, and survive process restart.",
    "Demonstrate with saved evidence: Raw, curated, model, forecast, log, backup, and quarantine roots are separated.",
    "Demonstrate with saved evidence: A path safety test rejects repository-internal bulk-data roots.",
    "Produce, validate, content-hash, and register `artifacts/implementation_preflight/local_path_contract.json`.",
    "Produce, validate, content-hash, and register `docs/operations/LOCAL_RUNTIME_PATHS.md`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-354",
  "labels": [
    "actionable",
    "core-release",
    "environment",
    "operations",
    "post-wave",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-004",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Configure AGGIE_ANALYTICS_DATA_ROOT and artifact roots outside the repository",
  "operational_jira": {
    "assignee": "kevinsgarrett@gmail.com",
    "jira_issue_id": "24494",
    "jira_updated_at": "2026-08-09T23:23:59.941-0500",
    "last_synced_at": "2026-08-11T06:07:11.607568+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\JIRA-LIVE-CATCHUP-20260811\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "Done"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Define and validate the non-repository credential inventory and redaction rules; Validate target storage permissions, free space, atomic writes, and quarantine behavior.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-002",
  "phase": "PHASE-4",
  "prerequisites": [
    "Dependency POST-SUBTASK-001 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-01994",
    "SRCREF-01995",
    "SRCREF-01996",
    "SRCREF-01997"
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
    "src/aggie_analytics/operations/benchmark.py",
    "docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md",
    "docs/operations/TARGET_HARDWARE_BENCHMARK.md",
    "src/aggie_analytics/operations/environment.py",
    "tests/test_w23_operations.py"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/implementation_preflight/local_path_contract.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "`docs/operations/LOCAL_RUNTIME_PATHS.md` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-004; retain command, exit code, and relevant output.",
      "path": "tests/test_w23_operations.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-004; retain command, exit code, and relevant output.",
      "path": "tools/validate_w23_operations.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-004; retain command, exit code, and relevant output.",
      "path": "tools/validate_repository.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "BENCHMARK",
      "expectation": "Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.",
      "path": "artifacts/implementation_preflight/local_path_contract.json",
      "validation_class": "BENCHMARK"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/implementation_preflight/local_path_contract.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "OPERATIONS",
      "expectation": "Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.",
      "path": "artifacts/implementation_preflight/local_path_contract.json",
      "validation_class": "OPERATIONS"
    },
    {
      "classification": "INTEGRATION",
      "expectation": "Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.",
      "path": "artifacts/implementation_preflight/local_path_contract.json",
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
      "path": "NEW_TEST_REQUIRED::POST-SUBTASK-004",
      "validation_class": "NEW_AUTOMATED_TEST_REQUIRED"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-004.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that configured roots are absolute, writable, outside the Git repository, and survive process restart.",
    "Acceptance failure: the evidence cannot demonstrate that raw, curated, model, forecast, log, backup, and quarantine roots are separated.",
    "Acceptance failure: the evidence cannot demonstrate that a path safety test rejects repository-internal bulk-data roots."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 1 of 3 step in Story POST-STORY-002 (Local data, artifact, and secret boundary bootstrap): Configure AGGIE_ANALYTICS_DATA_ROOT and artifact roots outside the repository. Consume only verified prerequisite outputs from `POST-SUBTASK-001`. Produce `artifacts/implementation_preflight/local_path_contract.json`, `docs/operations/LOCAL_RUNTIME_PATHS.md`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-005.",
  "source_ids": [
    "GAP-001",
    "GAP-010",
    "HANDOFF-001",
    "HANDOFF-002"
  ],
  "source_refs": [
    "SRCREF-01994",
    "SRCREF-01995",
    "SRCREF-01996",
    "SRCREF-01997",
    "SRCREF-01998",
    "SRCREF-01999",
    "SRCREF-02000",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01887",
    "SRCREF-01563",
    "SRCREF-01888",
    "SRCREF-01572"
  ],
  "specificity_fingerprint": "1ecba18c620dd6a23488aa2e698e6bac1b18e6fb201ae5b77c6bcd55694e5dbe",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
  ],
  "supporting_source_refs": [
    "SRCREF-01998",
    "SRCREF-01999",
    "SRCREF-02000",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01887",
    "SRCREF-01563",
    "SRCREF-01888",
    "SRCREF-01572"
  ],
  "title": "[POST-SUBTASK-004] Configure AGGIE_ANALYTICS_DATA_ROOT and artifact roots outside the repository",
  "traceability_inherited_from": [
    "POST-SUBTASK-009"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "BENCHMARK",
    "INTEGRATION",
    "NEW_AUTOMATED_TEST_REQUIRED",
    "OPERATIONS",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-002: Local data, artifact, and secret boundary bootstrap.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-004.md",
  "workflow_state": "DONE"
}
```

## Objective

Configure AGGIE_ANALYTICS_DATA_ROOT and artifact roots outside the repository

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-002: Local data, artifact, and secret boundary bootstrap.

## Scope

Execute the atomic 1 of 3 step in Story POST-STORY-002 (Local data, artifact, and secret boundary bootstrap): Configure AGGIE_ANALYTICS_DATA_ROOT and artifact roots outside the repository. Consume only verified prerequisite outputs from `POST-SUBTASK-001`. Produce `artifacts/implementation_preflight/local_path_contract.json`, `docs/operations/LOCAL_RUNTIME_PATHS.md`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-005.

### Explicit In Scope

- Perform the exact action: Configure AGGIE_ANALYTICS_DATA_ROOT and artifact roots outside the repository.
- Consume only verified prerequisite outputs from `POST-SUBTASK-001`.
- Demonstrate with saved evidence: Configured roots are absolute, writable, outside the Git repository, and survive process restart.
- Demonstrate with saved evidence: Raw, curated, model, forecast, log, backup, and quarantine roots are separated.
- Demonstrate with saved evidence: A path safety test rejects repository-internal bulk-data roots.
- Produce, validate, content-hash, and register `artifacts/implementation_preflight/local_path_contract.json`.
- Produce, validate, content-hash, and register `docs/operations/LOCAL_RUNTIME_PATHS.md`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Define and validate the non-repository credential inventory and redaction rules; Validate target storage permissions, free space, atomic writes, and quarantine behavior.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-001 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-001

## Blocks

- POST-SUBTASK-005
- POST-SUBTASK-006

## Read / Inspect First

- AGENTS.md
- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/operations/benchmark.py
- docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md
- docs/operations/TARGET_HARDWARE_BENCHMARK.md
- src/aggie_analytics/operations/environment.py
- tests/test_w23_operations.py

## Files Expected To Be Modified

- src/aggie_analytics/operations/environment.py
- tests/test_w23_operations.py
- docs/operations/LOCAL_RUNTIME_PATHS.md
- src/aggie_analytics/operations/benchmark.py

## Components Expected To Be Touched

- operations-security
- environment

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

- artifacts/implementation_preflight/local_path_contract.json
- docs/operations/LOCAL_RUNTIME_PATHS.md

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-009`
- Inherited from: POST-SUBTASK-009
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 3, "adr_ids": 4, "gap_ids": 1, "requirement_ids": 5, "risk_ids": 2}`

## Acceptance Criteria

1. Configured roots are absolute, writable, outside the Git repository, and survive process restart.
2. Raw, curated, model, forecast, log, backup, and quarantine roots are separated.
3. A path safety test rejects repository-internal bulk-data roots.

## Definition of Done

1. The atomic scope in POST-SUBTASK-004 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The output set `artifacts/implementation_preflight/local_path_contract.json`, `docs/operations/LOCAL_RUNTIME_PATHS.md` is demonstrably consumable by POST-SUBTASK-005 without manual reconstruction or undocumented state.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w23_operations.py` — Run as a regression check after completing POST-SUBTASK-004; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_w23_operations.py` — Run as a regression check after completing POST-SUBTASK-004; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_repository.py` — Run as a regression check after completing POST-SUBTASK-004; retain command, exit code, and relevant output.
- **BENCHMARK** / `BENCHMARK` — `artifacts/implementation_preflight/local_path_contract.json` — Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/implementation_preflight/local_path_contract.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **OPERATIONS** / `OPERATIONS` — `artifacts/implementation_preflight/local_path_contract.json` — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- **INTEGRATION** / `INTEGRATION` — `artifacts/implementation_preflight/local_path_contract.json` — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- **NEW_AUTOMATED_TEST_REQUIRED** / `NEW_AUTOMATED_TEST_REQUIRED` — `NEW_TEST_REQUIRED::POST-SUBTASK-004` — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Required Evidence

- `artifacts/implementation_preflight/local_path_contract.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- `docs/operations/LOCAL_RUNTIME_PATHS.md` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "IMPLEMENTED",
  "downstream_consumer": "POST-SUBTASK-005",
  "governance_traceability_gate": "POST-SUBTASK-009",
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

Validate that `artifacts/implementation_preflight/local_path_contract.json`, `docs/operations/LOCAL_RUNTIME_PATHS.md` can be parsed and consumed by `POST-SUBTASK-005` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.

## Expected Maturity After Completion

`IMPLEMENTED`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-004.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that configured roots are absolute, writable, outside the Git repository, and survive process restart.
- Acceptance failure: the evidence cannot demonstrate that raw, curated, model, forecast, log, backup, and quarantine roots are separated.
- Acceptance failure: the evidence cannot demonstrate that a path safety test rejects repository-internal bulk-data roots.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

## Source References

- SRCREF-01994
- SRCREF-01995
- SRCREF-01996
- SRCREF-01997
- SRCREF-01998
- SRCREF-01999
- SRCREF-02000
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01887
- SRCREF-01563
- SRCREF-01888
- SRCREF-01572

## AI Context Notes

- Canonical parent Story: POST-STORY-002. Governance traceability gate: POST-SUBTASK-009. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-004.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

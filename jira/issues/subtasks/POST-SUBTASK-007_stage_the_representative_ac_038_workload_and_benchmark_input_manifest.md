<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-007_stage_the_representative_ac_038_workload_and_benchmark_input_manifest.json -->
# POST-SUBTASK-007 — [POST-SUBTASK-007] Stage the representative AC-038 workload and benchmark input manifest

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "The workload matches the benchmark contract and includes representative ingestion, PIT, feature, model, publication, and product-read operations.",
    "Input hashes and data classification are recorded.",
    "Protected holdout outcomes are not exposed to benchmark tuning."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-003. Governance traceability gate: POST-SUBTASK-009. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-007.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/benchmarks/ac038_input_manifest.json",
    "artifacts/jira_evidence/POST-SUBTASK-007.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-006",
  "blocks": [
    "POST-SUBTASK-008",
    "POST-SUBTASK-009"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-007_stage_the_representative_ac_038_workload_and_benchmark_input_manifest.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "IMPLEMENTED",
    "downstream_consumer": "POST-SUBTASK-008",
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
  "critical_path": true,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-007 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The output set `artifacts/benchmarks/ac038_input_manifest.json` is demonstrably consumable by POST-SUBTASK-008 without manual reconstruction or undocumented state."
  ],
  "dependencies": [
    "POST-SUBTASK-002",
    "POST-SUBTASK-006"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 3,
    "adr_ids": 4,
    "gap_ids": 1,
    "requirement_ids": 5,
    "risk_ids": 2
  },
  "effective_traceability_total": 15,
  "end_to_end_validation": "Validate that `artifacts/benchmarks/ac038_input_manifest.json` can be parsed and consumed by `POST-SUBTASK-008` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.",
  "epic_id": "POST-EPIC-001",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-007.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "IMPLEMENTED",
  "expected_outputs": [
    "artifacts/benchmarks/ac038_input_manifest.json"
  ],
  "files_expected_to_be_read": [
    "AGENTS.md",
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "src/aggie_analytics/operations/benchmark.py",
    "docs/operations/TARGET_HARDWARE_BENCHMARK.md",
    "docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md",
    "scripts/benchmark_target.ps1"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "AGENTS.md",
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "src/aggie_analytics/operations/benchmark.py",
    "docs/operations/TARGET_HARDWARE_BENCHMARK.md",
    "docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md",
    "scripts/benchmark_target.ps1"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-007_stage_the_representative_ac_038_workload_and_benchmark_input_manifest.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-009",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100311,
  "in_scope": [
    "Perform the exact action: Stage the representative AC-038 workload and benchmark input manifest.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-002`, `POST-SUBTASK-006`.",
    "Demonstrate with saved evidence: The workload matches the benchmark contract and includes representative ingestion, PIT, feature, model, publication, and product-read operations.",
    "Demonstrate with saved evidence: Input hashes and data classification are recorded.",
    "Demonstrate with saved evidence: Protected holdout outcomes are not exposed to benchmark tuning.",
    "Produce, validate, content-hash, and register `artifacts/benchmarks/ac038_input_manifest.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-357",
  "labels": [
    "actionable",
    "core-release",
    "environment",
    "post-wave",
    "protected-gate",
    "subtask"
  ],
  "last_content_audit": "2026-08-08",
  "local_id": "POST-SUBTASK-007",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Stage the representative AC-038 workload and benchmark input manifest",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24497",
    "jira_updated_at": "2026-08-09T00:03:19.929-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.",
    "Work assigned to sibling subtasks: Run scripts/benchmark_target.ps1 on the declared Windows/Ryzen 7 HX/32 GB/RTX 5060/NVMe target; Govern THR-011 and THR-012 values and clear or retain the W23 local-production gate.",
    "Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.",
    "Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-003",
  "phase": "PHASE-4",
  "prerequisites": [
    "Dependency POST-SUBTASK-002 complete at required maturity",
    "Dependency POST-SUBTASK-006 complete at required maturity"
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
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "src/aggie_analytics/operations/benchmark.py",
    "docs/operations/TARGET_HARDWARE_BENCHMARK.md",
    "docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md",
    "scripts/benchmark_target.ps1"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/benchmarks/ac038_input_manifest.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.",
    "PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-007; retain command, exit code, and relevant output.",
      "path": "tests/test_w23_operations.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-007; retain command, exit code, and relevant output.",
      "path": "tools/validate_w23_operations.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "BENCHMARK",
      "expectation": "Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.",
      "path": "artifacts/benchmarks/ac038_input_manifest.json",
      "validation_class": "BENCHMARK"
    },
    {
      "classification": "CHRONOLOGICAL_REPLAY",
      "expectation": "Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.",
      "path": "artifacts/benchmarks/ac038_input_manifest.json",
      "validation_class": "CHRONOLOGICAL_REPLAY"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/benchmarks/ac038_input_manifest.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/benchmarks/ac038_input_manifest.json",
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
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-007.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that the workload matches the benchmark contract and includes representative ingestion, PIT, feature, model, publication, and product-read operations.",
    "Acceptance failure: the evidence cannot demonstrate that input hashes and data classification are recorded.",
    "Acceptance failure: the evidence cannot demonstrate that protected holdout outcomes are not exposed to benchmark tuning."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 1 of 3 step in Story POST-STORY-003 (Authoritative target-hardware benchmark and threshold governance): Stage the representative AC-038 workload and benchmark input manifest. Consume only verified prerequisite outputs from `POST-SUBTASK-002`, `POST-SUBTASK-006`. Produce `artifacts/benchmarks/ac038_input_manifest.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-008.",
  "source_ids": [
    "AC-038",
    "GAP-001",
    "HANDOFF-001",
    "TASK-161"
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
    "SRCREF-00194",
    "SRCREF-01017"
  ],
  "specificity_fingerprint": "138297f8e53675cdd4fa6342f2baa4ec15016cc945ad18f9f98cfe01e65200bd",
  "stop_conditions": [
    "Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.",
    "Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.",
    "Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence."
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
    "SRCREF-00194",
    "SRCREF-01017"
  ],
  "title": "[POST-SUBTASK-007] Stage the representative AC-038 workload and benchmark input manifest",
  "traceability_inherited_from": [
    "POST-SUBTASK-009"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "BENCHMARK",
    "CHRONOLOGICAL_REPLAY",
    "END_TO_END",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-003: Authoritative target-hardware benchmark and threshold governance.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-007.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Stage the representative AC-038 workload and benchmark input manifest

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-003: Authoritative target-hardware benchmark and threshold governance.

## Scope

Execute the atomic 1 of 3 step in Story POST-STORY-003 (Authoritative target-hardware benchmark and threshold governance): Stage the representative AC-038 workload and benchmark input manifest. Consume only verified prerequisite outputs from `POST-SUBTASK-002`, `POST-SUBTASK-006`. Produce `artifacts/benchmarks/ac038_input_manifest.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-008.

### Explicit In Scope

- Perform the exact action: Stage the representative AC-038 workload and benchmark input manifest.
- Consume only verified prerequisite outputs from `POST-SUBTASK-002`, `POST-SUBTASK-006`.
- Demonstrate with saved evidence: The workload matches the benchmark contract and includes representative ingestion, PIT, feature, model, publication, and product-read operations.
- Demonstrate with saved evidence: Input hashes and data classification are recorded.
- Demonstrate with saved evidence: Protected holdout outcomes are not exposed to benchmark tuning.
- Produce, validate, content-hash, and register `artifacts/benchmarks/ac038_input_manifest.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Run scripts/benchmark_target.ps1 on the declared Windows/Ryzen 7 HX/32 GB/RTX 5060/NVMe target; Govern THR-011 and THR-012 values and clear or retain the W23 local-production gate.
- Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-002 complete at required maturity
- Dependency POST-SUBTASK-006 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-002
- POST-SUBTASK-006

## Blocks

- POST-SUBTASK-008
- POST-SUBTASK-009

## Read / Inspect First

- AGENTS.md
- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- governance/IMPLEMENTATION_WBS.csv
- src/aggie_analytics/operations/benchmark.py
- docs/operations/TARGET_HARDWARE_BENCHMARK.md
- docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md
- scripts/benchmark_target.ps1

## Files Expected To Be Modified

- None.

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

- artifacts/benchmarks/ac038_input_manifest.json

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

1. The workload matches the benchmark contract and includes representative ingestion, PIT, feature, model, publication, and product-read operations.
2. Input hashes and data classification are recorded.
3. Protected holdout outcomes are not exposed to benchmark tuning.

## Definition of Done

1. The atomic scope in POST-SUBTASK-007 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The output set `artifacts/benchmarks/ac038_input_manifest.json` is demonstrably consumable by POST-SUBTASK-008 without manual reconstruction or undocumented state.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w23_operations.py` — Run as a regression check after completing POST-SUBTASK-007; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_w23_operations.py` — Run as a regression check after completing POST-SUBTASK-007; retain command, exit code, and relevant output.
- **BENCHMARK** / `BENCHMARK` — `artifacts/benchmarks/ac038_input_manifest.json` — Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.
- **CHRONOLOGICAL_REPLAY** / `CHRONOLOGICAL_REPLAY` — `artifacts/benchmarks/ac038_input_manifest.json` — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/benchmarks/ac038_input_manifest.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **END_TO_END** / `END_TO_END` — `artifacts/benchmarks/ac038_input_manifest.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/benchmarks/ac038_input_manifest.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "IMPLEMENTED",
  "downstream_consumer": "POST-SUBTASK-008",
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

Validate that `artifacts/benchmarks/ac038_input_manifest.json` can be parsed and consumed by `POST-SUBTASK-008` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

## Expected Maturity After Completion

`IMPLEMENTED`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-007.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that the workload matches the benchmark contract and includes representative ingestion, PIT, feature, model, publication, and product-read operations.
- Acceptance failure: the evidence cannot demonstrate that input hashes and data classification are recorded.
- Acceptance failure: the evidence cannot demonstrate that protected holdout outcomes are not exposed to benchmark tuning.

## Stop Conditions

- Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.
- Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.
- Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence.

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
- SRCREF-00194
- SRCREF-01017

## AI Context Notes

- Canonical parent Story: POST-STORY-003. Governance traceability gate: POST-SUBTASK-009. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-007.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-002_run_the_full_unit_and_governance_validator_suite_on_the_target_host.json -->
# POST-SUBTASK-002 — [POST-SUBTASK-002] Run the full unit and governance validator suite on the target host

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "All 229 baseline unit tests are executed and results are recorded without editing expected outcomes.",
    "W25 final, acceptance, backlog, and strict repository validators run from a clean checkout.",
    "Failures are recorded as blockers; they are not waived or hidden."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-001. Governance traceability gate: POST-SUBTASK-009. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-002.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/implementation_preflight/target_validation_results.json",
    "artifacts/implementation_preflight/target_validation.log",
    "artifacts/jira_evidence/POST-SUBTASK-002.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-001",
  "blocks": [
    "POST-EPIC-014",
    "POST-STORY-003",
    "POST-STORY-042",
    "POST-SUBTASK-003",
    "POST-SUBTASK-007",
    "POST-SUBTASK-008",
    "POST-SUBTASK-009",
    "POST-SUBTASK-124",
    "POST-SUBTASK-125",
    "POST-SUBTASK-126"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-002_run_the_full_unit_and_governance_validator_suite_on_the_target_host.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "IMPLEMENTED",
    "downstream_consumer": "POST-SUBTASK-003",
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
    "The atomic scope in POST-SUBTASK-002 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The output set `artifacts/implementation_preflight/target_validation_results.json`, `artifacts/implementation_preflight/target_validation.log` is demonstrably consumable by POST-SUBTASK-003 without manual reconstruction or undocumented state."
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
  "end_to_end_validation": "Validate that `artifacts/implementation_preflight/target_validation_results.json`, `artifacts/implementation_preflight/target_validation.log` can be parsed and consumed by `POST-SUBTASK-003` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.",
  "epic_id": "POST-EPIC-001",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-002.json",
  "evidence_state": "PLANNED",
  "execution_lane": "OPERATIONS",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "IMPLEMENTED",
  "expected_outputs": [
    "artifacts/implementation_preflight/target_validation_results.json",
    "artifacts/implementation_preflight/target_validation.log"
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
    "src/aggie_analytics/operations/benchmark.py",
    "docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md",
    "docs/operations/TARGET_HARDWARE_BENCHMARK.md",
    "scripts/benchmark_target.ps1"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-002_run_the_full_unit_and_governance_validator_suite_on_the_target_host.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-009",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100306,
  "in_scope": [
    "Perform the exact action: Run the full unit and governance validator suite on the target host.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-001`.",
    "Demonstrate with saved evidence: All 229 baseline unit tests are executed and results are recorded without editing expected outcomes.",
    "Demonstrate with saved evidence: W25 final, acceptance, backlog, and strict repository validators run from a clean checkout.",
    "Demonstrate with saved evidence: Failures are recorded as blockers; they are not waived or hidden.",
    "Produce, validate, content-hash, and register `artifacts/implementation_preflight/target_validation_results.json`.",
    "Produce, validate, content-hash, and register `artifacts/implementation_preflight/target_validation.log`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-352",
  "labels": [
    "actionable",
    "core-release",
    "environment",
    "operations",
    "post-wave",
    "subtask"
  ],
  "last_content_audit": "2026-08-08",
  "local_id": "POST-SUBTASK-002",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Run the full unit and governance validator suite on the target host",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24492",
    "jira_updated_at": "2026-08-09T00:03:18.259-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.",
    "Work assigned to sibling subtasks: Verify W25 repository identity, manifests, and no-Wave-26 state; Capture the authoritative target runtime and dependency manifest.",
    "Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-001",
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
    "scripts/benchmark_target.ps1"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/implementation_preflight/target_validation_results.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "`artifacts/implementation_preflight/target_validation.log` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-002; retain command, exit code, and relevant output.",
      "path": "tests/test_w23_operations.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-002; retain command, exit code, and relevant output.",
      "path": "tools/validate_repository.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "BENCHMARK",
      "expectation": "Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.",
      "path": "artifacts/implementation_preflight/target_validation_results.json",
      "validation_class": "BENCHMARK"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/implementation_preflight/target_validation_results.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "INTEGRATION",
      "expectation": "Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.",
      "path": "artifacts/implementation_preflight/target_validation_results.json",
      "validation_class": "INTEGRATION"
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
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-002.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that all 229 baseline unit tests are executed and results are recorded without editing expected outcomes.",
    "Acceptance failure: the evidence cannot demonstrate that w25 final, acceptance, backlog, and strict repository validators run from a clean checkout.",
    "Acceptance failure: the evidence cannot demonstrate that failures are recorded as blockers; they are not waived or hidden."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 2 of 3 step in Story POST-STORY-001 (Canonical handoff and target-environment preflight): Run the full unit and governance validator suite on the target host. Consume only verified prerequisite outputs from `POST-SUBTASK-001`. Produce `artifacts/implementation_preflight/target_validation_results.json`, `artifacts/implementation_preflight/target_validation.log`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-003.",
  "source_ids": [
    "GAP-001",
    "HANDOFF-001"
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
    "SRCREF-01563"
  ],
  "specificity_fingerprint": "55a7888f72ccf2aa2a3ef9f6c74966e36bca0e907bfb89357e14cfdd527fc06f",
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
    "SRCREF-01563"
  ],
  "title": "[POST-SUBTASK-002] Run the full unit and governance validator suite on the target host",
  "traceability_inherited_from": [
    "POST-SUBTASK-009"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "BENCHMARK",
    "INTEGRATION",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-001: Canonical handoff and target-environment preflight.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-002.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Run the full unit and governance validator suite on the target host

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-001: Canonical handoff and target-environment preflight.

## Scope

Execute the atomic 2 of 3 step in Story POST-STORY-001 (Canonical handoff and target-environment preflight): Run the full unit and governance validator suite on the target host. Consume only verified prerequisite outputs from `POST-SUBTASK-001`. Produce `artifacts/implementation_preflight/target_validation_results.json`, `artifacts/implementation_preflight/target_validation.log`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-003.

### Explicit In Scope

- Perform the exact action: Run the full unit and governance validator suite on the target host.
- Consume only verified prerequisite outputs from `POST-SUBTASK-001`.
- Demonstrate with saved evidence: All 229 baseline unit tests are executed and results are recorded without editing expected outcomes.
- Demonstrate with saved evidence: W25 final, acceptance, backlog, and strict repository validators run from a clean checkout.
- Demonstrate with saved evidence: Failures are recorded as blockers; they are not waived or hidden.
- Produce, validate, content-hash, and register `artifacts/implementation_preflight/target_validation_results.json`.
- Produce, validate, content-hash, and register `artifacts/implementation_preflight/target_validation.log`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Verify W25 repository identity, manifests, and no-Wave-26 state; Capture the authoritative target runtime and dependency manifest.
- Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-001 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-001

## Blocks

- POST-EPIC-014
- POST-STORY-003
- POST-STORY-042
- POST-SUBTASK-003
- POST-SUBTASK-007
- POST-SUBTASK-008
- POST-SUBTASK-009
- POST-SUBTASK-124
- POST-SUBTASK-125
- POST-SUBTASK-126

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

- artifacts/implementation_preflight/target_validation_results.json
- artifacts/implementation_preflight/target_validation.log

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

1. All 229 baseline unit tests are executed and results are recorded without editing expected outcomes.
2. W25 final, acceptance, backlog, and strict repository validators run from a clean checkout.
3. Failures are recorded as blockers; they are not waived or hidden.

## Definition of Done

1. The atomic scope in POST-SUBTASK-002 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The output set `artifacts/implementation_preflight/target_validation_results.json`, `artifacts/implementation_preflight/target_validation.log` is demonstrably consumable by POST-SUBTASK-003 without manual reconstruction or undocumented state.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w23_operations.py` — Run as a regression check after completing POST-SUBTASK-002; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_repository.py` — Run as a regression check after completing POST-SUBTASK-002; retain command, exit code, and relevant output.
- **BENCHMARK** / `BENCHMARK` — `artifacts/implementation_preflight/target_validation_results.json` — Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/implementation_preflight/target_validation_results.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **INTEGRATION** / `INTEGRATION` — `artifacts/implementation_preflight/target_validation_results.json` — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/implementation_preflight/target_validation_results.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- `artifacts/implementation_preflight/target_validation.log` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "IMPLEMENTED",
  "downstream_consumer": "POST-SUBTASK-003",
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

Validate that `artifacts/implementation_preflight/target_validation_results.json`, `artifacts/implementation_preflight/target_validation.log` can be parsed and consumed by `POST-SUBTASK-003` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

## Expected Maturity After Completion

`IMPLEMENTED`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-002.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that all 229 baseline unit tests are executed and results are recorded without editing expected outcomes.
- Acceptance failure: the evidence cannot demonstrate that w25 final, acceptance, backlog, and strict repository validators run from a clean checkout.
- Acceptance failure: the evidence cannot demonstrate that failures are recorded as blockers; they are not waived or hidden.

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

## AI Context Notes

- Canonical parent Story: POST-STORY-001. Governance traceability gate: POST-SUBTASK-009. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-002.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

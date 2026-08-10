<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-009_govern_thr_011_and_thr_012_values_and_clear_or_retain_the_w23_local_production_g.json -->
# POST-SUBTASK-009 — [POST-SUBTASK-009] Govern THR-011 and THR-012 values and clear or retain the W23 local-production gate

## Canonical metadata

```json
{
  "acceptance_control_ids": [
    "AC-038",
    "AC-233",
    "AC-234"
  ],
  "acceptance_criteria": [
    "THR-011 and THR-012 are populated only from the authoritative benchmark evidence.",
    "The decision records evidence hashes, reviewer, timestamp, and pass/block rationale.",
    "TASK-163 remains blocked unless AC-038 genuinely passes; no threshold is relaxed after observing failure."
  ],
  "adr_ids": [
    "ADR-340",
    "ADR-341",
    "ADR-346",
    "ADR-348"
  ],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-003. Governance traceability gate: POST-SUBTASK-009. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-009.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv",
    "artifacts/benchmarks/ac038_gate_decision.json",
    "artifacts/jira_evidence/POST-SUBTASK-009.json"
  ],
  "blocked_reason": "AC038_THRESHOLD_AUTHORITY_BLOCKER: accepted benchmark v1 preserves target_match=false and authoritative_for_thr_011_012=false without override; the six-stage supplement is a synthetic resource proxy, not a material production workflow; no predeclared threshold-derivation/headroom method exists. THR-011/012 remain blank and AC-038/TASK-163 remain blocked.",
  "blocks": [
    "POST-EPIC-015",
    "POST-STORY-004",
    "POST-STORY-041",
    "POST-STORY-046",
    "POST-SUBTASK-010",
    "POST-SUBTASK-011",
    "POST-SUBTASK-012",
    "POST-SUBTASK-121",
    "POST-SUBTASK-122",
    "POST-SUBTASK-123",
    "POST-SUBTASK-136",
    "POST-SUBTASK-137",
    "POST-SUBTASK-138"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-009_govern_thr_011_and_thr_012_values_and_clear_or_retain_the_w23_local_production_g.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-003",
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
    "The atomic scope in POST-SUBTASK-009 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-003."
  ],
  "dependencies": [
    "POST-SUBTASK-002",
    "POST-SUBTASK-006",
    "POST-SUBTASK-007",
    "POST-SUBTASK-008"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 3,
    "adr_ids": 4,
    "gap_ids": 1,
    "requirement_ids": 5,
    "risk_ids": 2
  },
  "effective_traceability_total": 15,
  "end_to_end_validation": "The target host produces authoritative benchmark evidence and the governance layer deterministically resolves or retains AC-038 without fabricated thresholds. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-015, POST-STORY-004, POST-STORY-041, POST-STORY-046, POST-SUBTASK-010, POST-SUBTASK-011, POST-SUBTASK-012, POST-SUBTASK-121, POST-SUBTASK-122, POST-SUBTASK-123, POST-SUBTASK-136, POST-SUBTASK-137….",
  "epic_id": "POST-EPIC-001",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-009.json",
  "evidence_state": "PARTIAL",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/benchmarks/ac038_gate_decision.json",
    "governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv"
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
    "governance/ADR_INDEX.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md",
    "docs/operations/TARGET_HARDWARE_BENCHMARK.md",
    "scripts/benchmark_target.ps1",
    "src/aggie_analytics/operations/benchmark.py"
  ],
  "files_expected_to_be_touched": [
    "governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv"
  ],
  "files_to_inspect": [
    "AGENTS.md",
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/ADR_INDEX.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md",
    "docs/operations/TARGET_HARDWARE_BENCHMARK.md",
    "scripts/benchmark_target.ps1",
    "src/aggie_analytics/operations/benchmark.py"
  ],
  "gap_ids": [
    "GAP-001"
  ],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-009_govern_thr_011_and_thr_012_values_and_clear_or_retain_the_w23_local_production_g.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-009",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100313,
  "in_scope": [
    "Perform the exact action: Govern THR-011 and THR-012 values and clear or retain the W23 local-production gate.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-002`, `POST-SUBTASK-006`, `POST-SUBTASK-007`, `POST-SUBTASK-008`.",
    "Demonstrate with saved evidence: THR-011 and THR-012 are populated only from the authoritative benchmark evidence.",
    "Demonstrate with saved evidence: The decision records evidence hashes, reviewer, timestamp, and pass/block rationale.",
    "Demonstrate with saved evidence: TASK-163 remains blocked unless AC-038 genuinely passes; no threshold is relaxed after observing failure.",
    "Produce, validate, content-hash, and register `artifacts/benchmarks/ac038_gate_decision.json`.",
    "Produce, validate, content-hash, and register `governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-359",
  "labels": [
    "actionable",
    "core-release",
    "environment",
    "post-wave",
    "protected-gate",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-009",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Govern THR-011 and THR-012 values and clear or retain the W23 local-production gate",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24499",
    "jira_updated_at": "2026-08-09T23:24:00.644-0500",
    "last_synced_at": "2026-08-10T04:24:34.496382+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\BAT-516-openai-foundation-complete\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Stage the representative AC-038 workload and benchmark input manifest; Run scripts/benchmark_target.ps1 on the declared Windows/Ryzen 7 HX/32 GB/RTX 5060/NVMe target.",
    "Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.",
    "Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-003",
  "phase": "PHASE-4",
  "prerequisites": [
    "Dependency POST-SUBTASK-002 complete at required maturity",
    "Dependency POST-SUBTASK-006 complete at required maturity",
    "Dependency POST-SUBTASK-007 complete at required maturity",
    "Dependency POST-SUBTASK-008 complete at required maturity"
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
    "governance/ADR_INDEX.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md",
    "docs/operations/TARGET_HARDWARE_BENCHMARK.md",
    "scripts/benchmark_target.ps1",
    "src/aggie_analytics/operations/benchmark.py"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/benchmarks/ac038_gate_decision.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "`governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.",
    "PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-009; retain command, exit code, and relevant output.",
      "path": "tests/test_w23_operations.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-009; retain command, exit code, and relevant output.",
      "path": "tools/validate_w23_operations.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-009; retain command, exit code, and relevant output.",
      "path": "governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "BENCHMARK",
      "expectation": "Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.",
      "path": "artifacts/benchmarks/ac038_gate_decision.json",
      "validation_class": "BENCHMARK"
    },
    {
      "classification": "CHRONOLOGICAL_REPLAY",
      "expectation": "Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.",
      "path": "artifacts/benchmarks/ac038_gate_decision.json",
      "validation_class": "CHRONOLOGICAL_REPLAY"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv",
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
    "REQ-200",
    "REQ-733",
    "REQ-736",
    "REQ-737",
    "REQ-745"
  ],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-009.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that tHR-011 and THR-012 are populated only from the authoritative benchmark evidence.",
    "Acceptance failure: the evidence cannot demonstrate that the decision records evidence hashes, reviewer, timestamp, and pass/block rationale.",
    "Acceptance failure: the evidence cannot demonstrate that tASK-163 remains blocked unless AC-038 genuinely passes; no threshold is relaxed after observing failure."
  ],
  "risk_ids": [
    "RISK-052",
    "RISK-307"
  ],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-003 (Authoritative target-hardware benchmark and threshold governance): Govern THR-011 and THR-012 values and clear or retain the W23 local-production gate. Consume only verified prerequisite outputs from `POST-SUBTASK-002`, `POST-SUBTASK-006`, `POST-SUBTASK-007`, `POST-SUBTASK-008`. Produce `artifacts/benchmarks/ac038_gate_decision.json`, `governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
  "source_ids": [
    "AC-038",
    "GAP-001",
    "HANDOFF-001",
    "ISSUE-113",
    "TASK-163",
    "THR-011",
    "THR-012"
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
    "SRCREF-00196",
    "SRCREF-01017",
    "SRCREF-01959",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "specificity_fingerprint": "76d013dfab02e19925158661a1b391cebd394d797257b73d7a07f79ef74a0f34",
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
    "SRCREF-00196",
    "SRCREF-01017",
    "SRCREF-01959",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "title": "[POST-SUBTASK-009] Govern THR-011 and THR-012 values and clear or retain the W23 local-production gate",
  "traceability_inherited_from": [],
  "traceability_resolution": "DIRECT_DOMAIN_GATE",
  "unblock_condition": "Provide an accepted representative material-workflow benchmark whose declared target authority passes without override, with a threshold derivation/headroom method declared before pass/fail evaluation; then synchronize THR-011/012, AC-038, TASK-161/TASK-163, and the strict W23 validator from protected evidence without relaxing an observed failure.",
  "validation_classes": [
    "BENCHMARK",
    "CHRONOLOGICAL_REPLAY",
    "END_TO_END",
    "REGRESSION",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-003: Authoritative target-hardware benchmark and threshold governance.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-009.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Govern THR-011 and THR-012 values and clear or retain the W23 local-production gate

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-003: Authoritative target-hardware benchmark and threshold governance.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-003 (Authoritative target-hardware benchmark and threshold governance): Govern THR-011 and THR-012 values and clear or retain the W23 local-production gate. Consume only verified prerequisite outputs from `POST-SUBTASK-002`, `POST-SUBTASK-006`, `POST-SUBTASK-007`, `POST-SUBTASK-008`. Produce `artifacts/benchmarks/ac038_gate_decision.json`, `governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Govern THR-011 and THR-012 values and clear or retain the W23 local-production gate.
- Consume only verified prerequisite outputs from `POST-SUBTASK-002`, `POST-SUBTASK-006`, `POST-SUBTASK-007`, `POST-SUBTASK-008`.
- Demonstrate with saved evidence: THR-011 and THR-012 are populated only from the authoritative benchmark evidence.
- Demonstrate with saved evidence: The decision records evidence hashes, reviewer, timestamp, and pass/block rationale.
- Demonstrate with saved evidence: TASK-163 remains blocked unless AC-038 genuinely passes; no threshold is relaxed after observing failure.
- Produce, validate, content-hash, and register `artifacts/benchmarks/ac038_gate_decision.json`.
- Produce, validate, content-hash, and register `governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Stage the representative AC-038 workload and benchmark input manifest; Run scripts/benchmark_target.ps1 on the declared Windows/Ryzen 7 HX/32 GB/RTX 5060/NVMe target.
- Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.

## Prerequisites

- Dependency POST-SUBTASK-002 complete at required maturity
- Dependency POST-SUBTASK-006 complete at required maturity
- Dependency POST-SUBTASK-007 complete at required maturity
- Dependency POST-SUBTASK-008 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-002
- POST-SUBTASK-006
- POST-SUBTASK-007
- POST-SUBTASK-008

## Blocks

- POST-EPIC-015
- POST-STORY-004
- POST-STORY-041
- POST-STORY-046
- POST-SUBTASK-010
- POST-SUBTASK-011
- POST-SUBTASK-012
- POST-SUBTASK-121
- POST-SUBTASK-122
- POST-SUBTASK-123
- POST-SUBTASK-136
- POST-SUBTASK-137
- POST-SUBTASK-138

## Read / Inspect First

- AGENTS.md
- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- governance/ADR_INDEX.csv
- governance/IMPLEMENTATION_WBS.csv
- docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md
- docs/operations/TARGET_HARDWARE_BENCHMARK.md
- scripts/benchmark_target.ps1
- src/aggie_analytics/operations/benchmark.py

## Files Expected To Be Modified

- governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv

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

- artifacts/benchmarks/ac038_gate_decision.json
- governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv

## Direct Requirements

- REQ-200
- REQ-733
- REQ-736
- REQ-737
- REQ-745

## Direct Acceptance Controls

- AC-038
- AC-233
- AC-234

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-009`
- Inherited from: None
- Resolution: `DIRECT_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 3, "adr_ids": 4, "gap_ids": 1, "requirement_ids": 5, "risk_ids": 2}`

## Acceptance Criteria

1. THR-011 and THR-012 are populated only from the authoritative benchmark evidence.
2. The decision records evidence hashes, reviewer, timestamp, and pass/block rationale.
3. TASK-163 remains blocked unless AC-038 genuinely passes; no threshold is relaxed after observing failure.

## Definition of Done

1. The atomic scope in POST-SUBTASK-009 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-003.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w23_operations.py` — Run as a regression check after completing POST-SUBTASK-009; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_w23_operations.py` — Run as a regression check after completing POST-SUBTASK-009; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv` — Run as a regression check after completing POST-SUBTASK-009; retain command, exit code, and relevant output.
- **BENCHMARK** / `BENCHMARK` — `artifacts/benchmarks/ac038_gate_decision.json` — Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.
- **CHRONOLOGICAL_REPLAY** / `CHRONOLOGICAL_REPLAY` — `artifacts/benchmarks/ac038_gate_decision.json` — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- **END_TO_END** / `END_TO_END` — `governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/benchmarks/ac038_gate_decision.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- `governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "PRODUCTION_READY",
  "downstream_consumer": "POST-STORY-003",
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

The target host produces authoritative benchmark evidence and the governance layer deterministically resolves or retains AC-038 without fabricated thresholds. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-015, POST-STORY-004, POST-STORY-041, POST-STORY-046, POST-SUBTASK-010, POST-SUBTASK-011, POST-SUBTASK-012, POST-SUBTASK-121, POST-SUBTASK-122, POST-SUBTASK-123, POST-SUBTASK-136, POST-SUBTASK-137….

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-009.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that tHR-011 and THR-012 are populated only from the authoritative benchmark evidence.
- Acceptance failure: the evidence cannot demonstrate that the decision records evidence hashes, reviewer, timestamp, and pass/block rationale.
- Acceptance failure: the evidence cannot demonstrate that tASK-163 remains blocked unless AC-038 genuinely passes; no threshold is relaxed after observing failure.

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
- SRCREF-00196
- SRCREF-01017
- SRCREF-01959
- SRCREF-02116
- SRCREF-02117
- SRCREF-02118

## AI Context Notes

- Canonical parent Story: POST-STORY-003. Governance traceability gate: POST-SUBTASK-009. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-009.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

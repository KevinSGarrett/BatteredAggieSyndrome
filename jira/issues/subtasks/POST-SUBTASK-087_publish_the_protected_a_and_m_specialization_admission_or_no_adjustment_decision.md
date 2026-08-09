<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-087_publish_the_protected_a_and_m_specialization_admission_or_no_adjustment_decision.json -->
# POST-SUBTASK-087 — [POST-SUBTASK-087] Publish the protected A&M specialization admission or no-adjustment decision and integrate it consistently

## Canonical metadata

```json
{
  "acceptance_control_ids": [
    "AC-030",
    "AC-127",
    "AC-128",
    "AC-129",
    "AC-133",
    "AC-135",
    "AC-160",
    "AC-173",
    "AC-193"
  ],
  "acceptance_criteria": [
    "Sealed candidates receive identical games, cutoffs, state, missingness, metrics, and no post-hoc changes; partial failures preserve evidence without feeding outcomes back to tuning.",
    "Evaluation reports confidence/sample/segments and accepts null, negative, unstable, or harmful results without subgroup shopping, relabeling, or unsupported causal claims.",
    "The signed decision admits only bounded supported specialization or selects global-only/no adjustment, updates model/product semantics, preserves rejected evidence, and closes GAP-009 only empirically.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [
    "ADR-001",
    "ADR-019",
    "ADR-046",
    "ADR-052",
    "ADR-102",
    "ADR-111",
    "ADR-194",
    "ADR-255",
    "ADR-282"
  ],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-029. Governance traceability gate: POST-SUBTASK-087. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-087.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/tamu/tamu_specialization_decision.json",
    "artifacts/jira_evidence/POST-SUBTASK-087.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-084;POST-SUBTASK-085;POST-SUBTASK-086;POST-SUBTASK-102",
  "blocks": [
    "POST-STORY-035",
    "POST-SUBTASK-103",
    "POST-SUBTASK-104",
    "POST-SUBTASK-105"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-087_publish_the_protected_a_and_m_specialization_admission_or_no_adjustment_decision.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-029",
    "governance_traceability_gate": "POST-SUBTASK-087",
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
  "component": "tamu-specialization",
  "components_expected_to_be_touched": [
    "tamu-specialization",
    "tamu"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-087 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-029."
  ],
  "dependencies": [
    "POST-SUBTASK-084",
    "POST-SUBTASK-085",
    "POST-SUBTASK-086",
    "POST-SUBTASK-102"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 9,
    "adr_ids": 9,
    "gap_ids": 1,
    "requirement_ids": 42,
    "risk_ids": 7
  },
  "effective_traceability_total": 68,
  "end_to_end_validation": "An identical sealed replay yields an auditable A&M-specialization-or-no-adjustment decision consumed by the production forecast. The gate decision must explicitly reevaluate downstream issues: POST-STORY-035, POST-SUBTASK-103, POST-SUBTASK-104, POST-SUBTASK-105.",
  "epic_id": "POST-EPIC-009",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-087.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/tamu/tamu_specialization_decision.json"
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
    "tests/test_tamu_specialization_governance.py",
    "docs/43_TAMU_SPECIALIZATION_CANDIDATES_AND_OVERFIT_GUARDS.md",
    "docs/41_TAMU_HIGH_RESOLUTION_STATE.md",
    "src/aggie_analytics/tamu/specialization.py",
    "src/aggie_analytics/tamu/state.py"
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
    "tests/test_tamu_specialization_governance.py",
    "docs/43_TAMU_SPECIALIZATION_CANDIDATES_AND_OVERFIT_GUARDS.md",
    "docs/41_TAMU_HIGH_RESOLUTION_STATE.md",
    "src/aggie_analytics/tamu/specialization.py",
    "src/aggie_analytics/tamu/state.py"
  ],
  "gap_ids": [
    "GAP-006"
  ],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-087_publish_the_protected_a_and_m_specialization_admission_or_no_adjustment_decision.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-087",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100391,
  "in_scope": [
    "Perform the exact action: Publish the protected A&M specialization admission or no-adjustment decision and integrate it consistently.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-084`, `POST-SUBTASK-085`, `POST-SUBTASK-086`, `POST-SUBTASK-102`.",
    "Demonstrate with saved evidence: Sealed candidates receive identical games, cutoffs, state, missingness, metrics, and no post-hoc changes; partial failures preserve evidence without feeding outcomes back to tuning.",
    "Demonstrate with saved evidence: Evaluation reports confidence/sample/segments and accepts null, negative, unstable, or harmful results without subgroup shopping, relabeling, or unsupported causal claims.",
    "Demonstrate with saved evidence: The signed decision admits only bounded supported specialization or selects global-only/no adjustment, updates model/product semantics, preserves rejected evidence, and closes GAP-009 only empirically.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `artifacts/tamu/tamu_specialization_decision.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-437",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "protected-gate",
    "subtask",
    "tamu"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-087",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Publish the protected A&M specialization admission or no-adjustment decision and integrate it consistently",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24577",
    "jira_updated_at": "2026-08-09T00:05:07.989-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Generate sealed global-only and A&M candidate predictions inside identical protected chronological replay; Measure incremental accuracy, calibration, stability, uncertainty, data-quality sensitivity, and multiple-comparison context.",
    "Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-029",
  "phase": "PHASE-3",
  "prerequisites": [
    "Dependency POST-SUBTASK-084 complete at required maturity",
    "Dependency POST-SUBTASK-085 complete at required maturity",
    "Dependency POST-SUBTASK-086 complete at required maturity",
    "Dependency POST-SUBTASK-102 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02057",
    "SRCREF-02058",
    "SRCREF-02059",
    "SRCREF-02060"
  ],
  "priority": "P1",
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
    "tests/test_tamu_specialization_governance.py",
    "docs/43_TAMU_SPECIALIZATION_CANDIDATES_AND_OVERFIT_GUARDS.md",
    "docs/41_TAMU_HIGH_RESOLUTION_STATE.md",
    "src/aggie_analytics/tamu/specialization.py",
    "src/aggie_analytics/tamu/state.py"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/tamu/tamu_specialization_decision.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-087; retain command, exit code, and relevant output.",
      "path": "tests/test_tamu_specialization_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-087; retain command, exit code, and relevant output.",
      "path": "tests/test_w20_model_starter.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-087; retain command, exit code, and relevant output.",
      "path": "tools/validate_tamu_specialization.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "CHRONOLOGICAL_REPLAY",
      "expectation": "Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.",
      "path": "artifacts/tamu/tamu_specialization_decision.json",
      "validation_class": "CHRONOLOGICAL_REPLAY"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/tamu/tamu_specialization_decision.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/tamu/tamu_specialization_decision.json",
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
    "REQ-021",
    "REQ-025",
    "REQ-026",
    "REQ-099",
    "REQ-100",
    "REQ-101",
    "REQ-102",
    "REQ-160",
    "REQ-161",
    "REQ-162",
    "REQ-259",
    "REQ-462",
    "REQ-463",
    "REQ-464",
    "REQ-465",
    "REQ-466",
    "REQ-467",
    "REQ-468",
    "REQ-469",
    "REQ-470",
    "REQ-471",
    "REQ-472",
    "REQ-473",
    "REQ-474",
    "REQ-475",
    "REQ-476",
    "REQ-477",
    "REQ-478",
    "REQ-479",
    "REQ-480",
    "REQ-481",
    "REQ-482",
    "REQ-485",
    "REQ-486",
    "REQ-487",
    "REQ-489",
    "REQ-560",
    "REQ-561",
    "REQ-583",
    "REQ-596",
    "REQ-650",
    "REQ-711"
  ],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-087.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that sealed candidates receive identical games, cutoffs, state, missingness, metrics, and no post-hoc changes; partial failures preserve evidence without feeding outcomes back to tuning.",
    "Acceptance failure: the evidence cannot demonstrate that evaluation reports confidence/sample/segments and accepts null, negative, unstable, or harmful results without subgroup shopping, relabeling, or unsupported causal claims.",
    "Acceptance failure: the evidence cannot demonstrate that the signed decision admits only bounded supported specialization or selects global-only/no adjustment, updates model/product semantics, preserves rejected evidence, and closes GAP-009 only empirically.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [
    "RISK-007",
    "RISK-042",
    "RISK-182",
    "RISK-190",
    "RISK-218",
    "RISK-232",
    "RISK-263"
  ],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-029 (Protected A&M lift, calibration, stability, and integration decision): Publish the protected A&M specialization admission or no-adjustment decision and integrate it consistently. Consume only verified prerequisite outputs from `POST-SUBTASK-084`, `POST-SUBTASK-085`, `POST-SUBTASK-086`, `POST-SUBTASK-102`. Produce `artifacts/tamu/tamu_specialization_decision.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
  "source_ids": [
    "GAP-006",
    "GAP-009",
    "HANDOFF-007",
    "HANDOFF-008",
    "ISSUE-009"
  ],
  "source_refs": [
    "SRCREF-02057",
    "SRCREF-02058",
    "SRCREF-02059",
    "SRCREF-02060",
    "SRCREF-02061",
    "SRCREF-02062",
    "SRCREF-02063",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01893",
    "SRCREF-01571",
    "SRCREF-01568",
    "SRCREF-01894",
    "SRCREF-01909",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "specificity_fingerprint": "4d87fbc2ef02cadc87250b7cf1cd2eccdd4b859ce424bc3ee0869b7fd8a9f0f0",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
  ],
  "supporting_source_refs": [
    "SRCREF-02061",
    "SRCREF-02062",
    "SRCREF-02063",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01893",
    "SRCREF-01571",
    "SRCREF-01568",
    "SRCREF-01894",
    "SRCREF-01909",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "title": "[POST-SUBTASK-087] Publish the protected A&M specialization admission or no-adjustment decision and integrate it consistently",
  "traceability_inherited_from": [],
  "traceability_resolution": "DIRECT_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "CHRONOLOGICAL_REPLAY",
    "END_TO_END",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-029: Protected A&M lift, calibration, stability, and integration decision.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-087.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Publish the protected A&M specialization admission or no-adjustment decision and integrate it consistently

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-029: Protected A&M lift, calibration, stability, and integration decision.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-029 (Protected A&M lift, calibration, stability, and integration decision): Publish the protected A&M specialization admission or no-adjustment decision and integrate it consistently. Consume only verified prerequisite outputs from `POST-SUBTASK-084`, `POST-SUBTASK-085`, `POST-SUBTASK-086`, `POST-SUBTASK-102`. Produce `artifacts/tamu/tamu_specialization_decision.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Publish the protected A&M specialization admission or no-adjustment decision and integrate it consistently.
- Consume only verified prerequisite outputs from `POST-SUBTASK-084`, `POST-SUBTASK-085`, `POST-SUBTASK-086`, `POST-SUBTASK-102`.
- Demonstrate with saved evidence: Sealed candidates receive identical games, cutoffs, state, missingness, metrics, and no post-hoc changes; partial failures preserve evidence without feeding outcomes back to tuning.
- Demonstrate with saved evidence: Evaluation reports confidence/sample/segments and accepts null, negative, unstable, or harmful results without subgroup shopping, relabeling, or unsupported causal claims.
- Demonstrate with saved evidence: The signed decision admits only bounded supported specialization or selects global-only/no adjustment, updates model/product semantics, preserves rejected evidence, and closes GAP-009 only empirically.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/tamu/tamu_specialization_decision.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Generate sealed global-only and A&M candidate predictions inside identical protected chronological replay; Measure incremental accuracy, calibration, stability, uncertainty, data-quality sensitivity, and multiple-comparison context.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-084 complete at required maturity
- Dependency POST-SUBTASK-085 complete at required maturity
- Dependency POST-SUBTASK-086 complete at required maturity
- Dependency POST-SUBTASK-102 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-084
- POST-SUBTASK-085
- POST-SUBTASK-086
- POST-SUBTASK-102

## Blocks

- POST-STORY-035
- POST-SUBTASK-103
- POST-SUBTASK-104
- POST-SUBTASK-105

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
- tests/test_tamu_specialization_governance.py
- docs/43_TAMU_SPECIALIZATION_CANDIDATES_AND_OVERFIT_GUARDS.md
- docs/41_TAMU_HIGH_RESOLUTION_STATE.md
- src/aggie_analytics/tamu/specialization.py
- src/aggie_analytics/tamu/state.py

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- tamu-specialization
- tamu

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

- artifacts/tamu/tamu_specialization_decision.json

## Direct Requirements

- REQ-021
- REQ-025
- REQ-026
- REQ-099
- REQ-100
- REQ-101
- REQ-102
- REQ-160
- REQ-161
- REQ-162
- REQ-259
- REQ-462
- REQ-463
- REQ-464
- REQ-465
- REQ-466
- REQ-467
- REQ-468
- REQ-469
- REQ-470
- REQ-471
- REQ-472
- REQ-473
- REQ-474
- REQ-475
- REQ-476
- REQ-477
- REQ-478
- REQ-479
- REQ-480
- REQ-481
- REQ-482
- REQ-485
- REQ-486
- REQ-487
- REQ-489
- REQ-560
- REQ-561
- REQ-583
- REQ-596
- REQ-650
- REQ-711

## Direct Acceptance Controls

- AC-030
- AC-127
- AC-128
- AC-129
- AC-133
- AC-135
- AC-160
- AC-173
- AC-193

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-087`
- Inherited from: None
- Resolution: `DIRECT_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 9, "adr_ids": 9, "gap_ids": 1, "requirement_ids": 42, "risk_ids": 7}`

## Acceptance Criteria

1. Sealed candidates receive identical games, cutoffs, state, missingness, metrics, and no post-hoc changes; partial failures preserve evidence without feeding outcomes back to tuning.
2. Evaluation reports confidence/sample/segments and accepts null, negative, unstable, or harmful results without subgroup shopping, relabeling, or unsupported causal claims.
3. The signed decision admits only bounded supported specialization or selects global-only/no adjustment, updates model/product semantics, preserves rejected evidence, and closes GAP-009 only empirically.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. The atomic scope in POST-SUBTASK-087 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-029.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_tamu_specialization_governance.py` — Run as a regression check after completing POST-SUBTASK-087; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w20_model_starter.py` — Run as a regression check after completing POST-SUBTASK-087; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_tamu_specialization.py` — Run as a regression check after completing POST-SUBTASK-087; retain command, exit code, and relevant output.
- **CHRONOLOGICAL_REPLAY** / `CHRONOLOGICAL_REPLAY` — `artifacts/tamu/tamu_specialization_decision.json` — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/tamu/tamu_specialization_decision.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **END_TO_END** / `END_TO_END` — `artifacts/tamu/tamu_specialization_decision.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/tamu/tamu_specialization_decision.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "PRODUCTION_READY",
  "downstream_consumer": "POST-STORY-029",
  "governance_traceability_gate": "POST-SUBTASK-087",
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

An identical sealed replay yields an auditable A&M-specialization-or-no-adjustment decision consumed by the production forecast. The gate decision must explicitly reevaluate downstream issues: POST-STORY-035, POST-SUBTASK-103, POST-SUBTASK-104, POST-SUBTASK-105.

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-087.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that sealed candidates receive identical games, cutoffs, state, missingness, metrics, and no post-hoc changes; partial failures preserve evidence without feeding outcomes back to tuning.
- Acceptance failure: the evidence cannot demonstrate that evaluation reports confidence/sample/segments and accepts null, negative, unstable, or harmful results without subgroup shopping, relabeling, or unsupported causal claims.
- Acceptance failure: the evidence cannot demonstrate that the signed decision admits only bounded supported specialization or selects global-only/no adjustment, updates model/product semantics, preserves rejected evidence, and closes GAP-009 only empirically.
- Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

## Source References

- SRCREF-02057
- SRCREF-02058
- SRCREF-02059
- SRCREF-02060
- SRCREF-02061
- SRCREF-02062
- SRCREF-02063
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01893
- SRCREF-01571
- SRCREF-01568
- SRCREF-01894
- SRCREF-01909
- SRCREF-02116
- SRCREF-02117
- SRCREF-02118

## AI Context Notes

- Canonical parent Story: POST-STORY-029. Governance traceability gate: POST-SUBTASK-087. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-087.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

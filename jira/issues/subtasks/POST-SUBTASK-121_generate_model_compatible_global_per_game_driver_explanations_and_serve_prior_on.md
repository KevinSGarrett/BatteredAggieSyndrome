<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-121_generate_model_compatible_global_per_game_driver_explanations_and_serve_prior_on.json -->
# POST-SUBTASK-121 — [POST-SUBTASK-121] Generate model-compatible global/per-game driver explanations and serve prior-only historical analog/peer/regime context

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Explanations use exact model/feature versions, expose direction/baseline/missingness/interactions/limits, analogs exclude same/future outcomes and expose distance/sample, and neither implies causality or replaces probability.",
    "The declared output `artifacts/product/explanation_analog_validation.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-041. Governance traceability gate: POST-SUBTASK-123. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-121.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/product/explanation_analog_validation.json",
    "artifacts/jira_evidence/POST-SUBTASK-121.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-009;POST-SUBTASK-120",
  "blocks": [
    "POST-SUBTASK-122",
    "POST-SUBTASK-123"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-121_generate_model_compatible_global_per_game_driver_explanations_and_serve_prior_on.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "IMPLEMENTED",
    "downstream_consumer": "POST-SUBTASK-122",
    "governance_traceability_gate": "POST-SUBTASK-123",
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
  "component": "serving-product",
  "components_expected_to_be_touched": [
    "serving-product",
    "product"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-121 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The output set `artifacts/product/explanation_analog_validation.json` is demonstrably consumable by POST-SUBTASK-122 without manual reconstruction or undocumented state."
  ],
  "dependencies": [
    "POST-SUBTASK-009",
    "POST-SUBTASK-120"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 10,
    "adr_ids": 24,
    "gap_ids": 1,
    "requirement_ids": 38,
    "risk_ids": 12
  },
  "effective_traceability_total": 85,
  "end_to_end_validation": "Validate that `artifacts/product/explanation_analog_validation.json` can be parsed and consumed by `POST-SUBTASK-122` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.",
  "epic_id": "POST-EPIC-013",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-121.json",
  "evidence_state": "PLANNED",
  "execution_lane": "SOLO_WORKTREE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "IMPLEMENTED",
  "expected_outputs": [
    "artifacts/product/explanation_analog_validation.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_w22_product_serving.py",
    "src/aggie_analytics/api/fastapi_app.py",
    "src/aggie_analytics/product/freshness.py",
    "src/aggie_analytics/product/repository.py",
    "docs/107_W22_SNAPSHOT_SERVING_PRODUCT.md",
    "docs/product/API_CONTRACT.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_w22_product_serving.py",
    "src/aggie_analytics/api/fastapi_app.py",
    "src/aggie_analytics/product/freshness.py",
    "src/aggie_analytics/product/repository.py",
    "docs/107_W22_SNAPSHOT_SERVING_PRODUCT.md",
    "docs/product/API_CONTRACT.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-121_generate_model_compatible_global_per_game_driver_explanations_and_serve_prior_on.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-123",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100425,
  "in_scope": [
    "Perform the exact action: Generate model-compatible global/per-game driver explanations and serve prior-only historical analog/peer/regime context.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-120`.",
    "Demonstrate with saved evidence: Explanations use exact model/feature versions, expose direction/baseline/missingness/interactions/limits, analogs exclude same/future outcomes and expose distance/sample, and neither implies causality or replaces probability.",
    "Demonstrate with saved evidence: The declared output `artifacts/product/explanation_analog_validation.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "Produce, validate, content-hash, and register `artifacts/product/explanation_analog_validation.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-471",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "product",
    "solo-worktree",
    "subtask"
  ],
  "last_content_audit": "2026-08-08",
  "local_id": "POST-SUBTASK-121",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Generate model-compatible global/per-game driver explanations and serve prior-only historical analog/peer/regime context",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24611",
    "jira_updated_at": "2026-08-09T00:04:04.831-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.",
    "Work assigned to sibling subtasks: Run explanation faithfulness/stability/privacy tests plus target-host cold/warm load, API, snapshot, dashboard, concurrency, memory, CPU, and disk benchmarks; Publish product readiness, freshness/cache transitions, supported envelope, and safe failure decision.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-041",
  "phase": "PHASE-4",
  "prerequisites": [
    "Dependency POST-SUBTASK-120 complete at required maturity",
    "Dependency POST-SUBTASK-009 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02085",
    "SRCREF-02086",
    "SRCREF-02087",
    "SRCREF-02088"
  ],
  "priority": "P2",
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
    "tests/test_w22_product_serving.py",
    "src/aggie_analytics/api/fastapi_app.py",
    "src/aggie_analytics/product/freshness.py",
    "src/aggie_analytics/product/repository.py",
    "docs/107_W22_SNAPSHOT_SERVING_PRODUCT.md",
    "docs/product/API_CONTRACT.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/product/explanation_analog_validation.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-121; retain command, exit code, and relevant output.",
      "path": "tests/test_w22_product_serving.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-121; retain command, exit code, and relevant output.",
      "path": "tools/validate_w22_product.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/product/explanation_analog_validation.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "CALIBRATION",
      "expectation": "Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.",
      "path": "artifacts/product/explanation_analog_validation.json",
      "validation_class": "CALIBRATION"
    },
    {
      "classification": "OPERATIONS",
      "expectation": "Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.",
      "path": "artifacts/product/explanation_analog_validation.json",
      "validation_class": "OPERATIONS"
    },
    {
      "classification": "INTEGRATION",
      "expectation": "Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.",
      "path": "artifacts/product/explanation_analog_validation.json",
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
      "path": "NEW_TEST_REQUIRED::POST-SUBTASK-121",
      "validation_class": "NEW_AUTOMATED_TEST_REQUIRED"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-121.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that explanations use exact model/feature versions, expose direction/baseline/missingness/interactions/limits, analogs exclude same/future outcomes and expose distance/sample, and neither implies causality or replaces probability.",
    "Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/product/explanation_analog_validation.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 1 of 3 step in Story POST-STORY-041 (Faithful drivers, historical analogs, provenance, and target performance): Generate model-compatible global/per-game driver explanations and serve prior-only historical analog/peer/regime context. Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-120`. Produce `artifacts/product/explanation_analog_validation.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-122.",
  "source_ids": [
    "GAP-001",
    "GAP-012",
    "HANDOFF-011"
  ],
  "source_refs": [
    "SRCREF-02085",
    "SRCREF-02086",
    "SRCREF-02087",
    "SRCREF-02088",
    "SRCREF-02089",
    "SRCREF-02090",
    "SRCREF-02091",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01897",
    "SRCREF-01574",
    "SRCREF-01563"
  ],
  "specificity_fingerprint": "b297f3bbd569fcc075338743093b9fa34a7ccab1b0655b09450f659b9561a75f",
  "stop_conditions": [
    "Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.",
    "Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.",
    "Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence."
  ],
  "supporting_source_refs": [
    "SRCREF-02089",
    "SRCREF-02090",
    "SRCREF-02091",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01897",
    "SRCREF-01574",
    "SRCREF-01563"
  ],
  "title": "[POST-SUBTASK-121] Generate model-compatible global/per-game driver explanations and serve prior-only historical analog/peer/regime context",
  "traceability_inherited_from": [
    "POST-SUBTASK-123"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "CALIBRATION",
    "INTEGRATION",
    "NEW_AUTOMATED_TEST_REQUIRED",
    "OPERATIONS",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-041: Faithful drivers, historical analogs, provenance, and target performance.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-121.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Generate model-compatible global/per-game driver explanations and serve prior-only historical analog/peer/regime context

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-041: Faithful drivers, historical analogs, provenance, and target performance.

## Scope

Execute the atomic 1 of 3 step in Story POST-STORY-041 (Faithful drivers, historical analogs, provenance, and target performance): Generate model-compatible global/per-game driver explanations and serve prior-only historical analog/peer/regime context. Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-120`. Produce `artifacts/product/explanation_analog_validation.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-122.

### Explicit In Scope

- Perform the exact action: Generate model-compatible global/per-game driver explanations and serve prior-only historical analog/peer/regime context.
- Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-120`.
- Demonstrate with saved evidence: Explanations use exact model/feature versions, expose direction/baseline/missingness/interactions/limits, analogs exclude same/future outcomes and expose distance/sample, and neither implies causality or replaces probability.
- Demonstrate with saved evidence: The declared output `artifacts/product/explanation_analog_validation.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/product/explanation_analog_validation.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Run explanation faithfulness/stability/privacy tests plus target-host cold/warm load, API, snapshot, dashboard, concurrency, memory, CPU, and disk benchmarks; Publish product readiness, freshness/cache transitions, supported envelope, and safe failure decision.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-120 complete at required maturity
- Dependency POST-SUBTASK-009 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-009
- POST-SUBTASK-120

## Blocks

- POST-SUBTASK-122
- POST-SUBTASK-123

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_w22_product_serving.py
- src/aggie_analytics/api/fastapi_app.py
- src/aggie_analytics/product/freshness.py
- src/aggie_analytics/product/repository.py
- docs/107_W22_SNAPSHOT_SERVING_PRODUCT.md
- docs/product/API_CONTRACT.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- serving-product
- product

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

- artifacts/product/explanation_analog_validation.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-123`
- Inherited from: POST-SUBTASK-123
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 10, "adr_ids": 24, "gap_ids": 1, "requirement_ids": 38, "risk_ids": 12}`

## Acceptance Criteria

1. Explanations use exact model/feature versions, expose direction/baseline/missingness/interactions/limits, analogs exclude same/future outcomes and expose distance/sample, and neither implies causality or replaces probability.
2. The declared output `artifacts/product/explanation_analog_validation.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Definition of Done

1. The atomic scope in POST-SUBTASK-121 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The output set `artifacts/product/explanation_analog_validation.json` is demonstrably consumable by POST-SUBTASK-122 without manual reconstruction or undocumented state.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w22_product_serving.py` — Run as a regression check after completing POST-SUBTASK-121; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_w22_product.py` — Run as a regression check after completing POST-SUBTASK-121; retain command, exit code, and relevant output.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/product/explanation_analog_validation.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **CALIBRATION** / `CALIBRATION` — `artifacts/product/explanation_analog_validation.json` — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- **OPERATIONS** / `OPERATIONS` — `artifacts/product/explanation_analog_validation.json` — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- **INTEGRATION** / `INTEGRATION` — `artifacts/product/explanation_analog_validation.json` — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- **NEW_AUTOMATED_TEST_REQUIRED** / `NEW_AUTOMATED_TEST_REQUIRED` — `NEW_TEST_REQUIRED::POST-SUBTASK-121` — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Required Evidence

- `artifacts/product/explanation_analog_validation.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
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
  "downstream_consumer": "POST-SUBTASK-122",
  "governance_traceability_gate": "POST-SUBTASK-123",
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

Validate that `artifacts/product/explanation_analog_validation.json` can be parsed and consumed by `POST-SUBTASK-122` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

## Expected Maturity After Completion

`IMPLEMENTED`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-121.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that explanations use exact model/feature versions, expose direction/baseline/missingness/interactions/limits, analogs exclude same/future outcomes and expose distance/sample, and neither implies causality or replaces probability.
- Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/product/explanation_analog_validation.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Stop Conditions

- Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.
- Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.
- Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence.

## Source References

- SRCREF-02085
- SRCREF-02086
- SRCREF-02087
- SRCREF-02088
- SRCREF-02089
- SRCREF-02090
- SRCREF-02091
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01897
- SRCREF-01574
- SRCREF-01563

## AI Context Notes

- Canonical parent Story: POST-STORY-041. Governance traceability gate: POST-SUBTASK-123. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-121.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

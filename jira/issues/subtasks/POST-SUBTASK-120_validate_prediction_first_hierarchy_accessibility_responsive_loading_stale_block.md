<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-120_validate_prediction_first_hierarchy_accessibility_responsive_loading_stale_block.json -->
# POST-SUBTASK-120 — [POST-SUBTASK-120] Validate prediction-first hierarchy, accessibility, responsive/loading/stale/blocked/no-data states, and snapshot-only values

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Main views make prediction and uncertainty primary, show specialization only if admitted or global-only otherwise, and never calculate independent client-side percentages/scores.",
    "BAS is explicitly underperformance versus valid pregame expected margin—not loss probability—witty copy is separate from science, and thresholds/components appear only when supported with uncertainty.",
    "Every displayed value traces to a snapshot field and loading/stale/blocked/missing/no-champion/null-effect/source-outage states are accessible and keyboard/screen-reader understandable.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-040. Governance traceability gate: POST-SUBTASK-123. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-120.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/product/dashboard_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-120.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-117;POST-SUBTASK-118;POST-SUBTASK-119",
  "blocks": [
    "POST-STORY-041",
    "POST-SUBTASK-121",
    "POST-SUBTASK-122",
    "POST-SUBTASK-123"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-120_validate_prediction_first_hierarchy_accessibility_responsive_loading_stale_block.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-040",
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
    "The atomic scope in POST-SUBTASK-120 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-040."
  ],
  "dependencies": [
    "POST-SUBTASK-117",
    "POST-SUBTASK-118",
    "POST-SUBTASK-119"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 10,
    "adr_ids": 24,
    "gap_ids": 1,
    "requirement_ids": 38,
    "risk_ids": 12
  },
  "effective_traceability_total": 85,
  "end_to_end_validation": "The user sees a serious predictive product with honest uncertainty and freshness, plus clearly separated witty BAS framing that never overstates scientific evidence. The gate decision must explicitly reevaluate downstream issues: POST-STORY-041, POST-SUBTASK-121, POST-SUBTASK-122, POST-SUBTASK-123.",
  "epic_id": "POST-EPIC-013",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-120.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/product/dashboard_gate.json"
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
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-120_validate_prediction_first_hierarchy_accessibility_responsive_loading_stale_block.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-123",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100424,
  "in_scope": [
    "Perform the exact action: Validate prediction-first hierarchy, accessibility, responsive/loading/stale/blocked/no-data states, and snapshot-only values.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-117`, `POST-SUBTASK-118`, `POST-SUBTASK-119`.",
    "Demonstrate with saved evidence: Main views make prediction and uncertainty primary, show specialization only if admitted or global-only otherwise, and never calculate independent client-side percentages/scores.",
    "Demonstrate with saved evidence: BAS is explicitly underperformance versus valid pregame expected margin—not loss probability—witty copy is separate from science, and thresholds/components appear only when supported with uncertainty.",
    "Demonstrate with saved evidence: Every displayed value traces to a snapshot field and loading/stale/blocked/missing/no-champion/null-effect/source-outage states are accessible and keyboard/screen-reader understandable.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `artifacts/product/dashboard_gate.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-470",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "product",
    "protected-gate",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-120",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Validate prediction-first hierarchy, accessibility, responsive/loading/stale/blocked/no-data states, and snapshot-only values",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24610",
    "jira_updated_at": "2026-08-09T23:24:11.861-0500",
    "last_synced_at": "2026-08-11T06:30:01.758065+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\POST-SUBTASK-177-play-drive-preliminary\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Build game/A&M views for score, win probability, margin, distributions, intervals, scenarios, cutoff, freshness, and model identity; Build BAS ≥3/7/14/21, component, witty-copy, scientific caveat, no-effect, and unavailable presentation.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-040",
  "phase": "PHASE-4",
  "prerequisites": [
    "Dependency POST-SUBTASK-117 complete at required maturity",
    "Dependency POST-SUBTASK-118 complete at required maturity",
    "Dependency POST-SUBTASK-119 complete at required maturity"
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
    "`artifacts/product/dashboard_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-120; retain command, exit code, and relevant output.",
      "path": "tests/test_w22_product_serving.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-120; retain command, exit code, and relevant output.",
      "path": "tools/validate_w22_product.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/product/dashboard_gate.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "CALIBRATION",
      "expectation": "Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.",
      "path": "artifacts/product/dashboard_gate.json",
      "validation_class": "CALIBRATION"
    },
    {
      "classification": "OPERATIONS",
      "expectation": "Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.",
      "path": "artifacts/product/dashboard_gate.json",
      "validation_class": "OPERATIONS"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/product/dashboard_gate.json",
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
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-120.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that main views make prediction and uncertainty primary, show specialization only if admitted or global-only otherwise, and never calculate independent client-side percentages/scores.",
    "Acceptance failure: the evidence cannot demonstrate that bAS is explicitly underperformance versus valid pregame expected margin—not loss probability—witty copy is separate from science, and thresholds/components appear only when supported with uncertainty.",
    "Acceptance failure: the evidence cannot demonstrate that every displayed value traces to a snapshot field and loading/stale/blocked/missing/no-champion/null-effect/source-outage states are accessible and keyboard/screen-reader understandable.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-040 (Prediction-first dashboard and BAS experience): Validate prediction-first hierarchy, accessibility, responsive/loading/stale/blocked/no-data states, and snapshot-only values. Consume only verified prerequisite outputs from `POST-SUBTASK-117`, `POST-SUBTASK-118`, `POST-SUBTASK-119`. Produce `artifacts/product/dashboard_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
  "source_ids": [
    "GAP-012",
    "HANDOFF-009",
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
    "SRCREF-01895"
  ],
  "specificity_fingerprint": "06b5521ce1f36748de65eed4626cc3e7d916c2b447a5d2d416f5e3e523fff81c",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
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
    "SRCREF-01895"
  ],
  "title": "[POST-SUBTASK-120] Validate prediction-first hierarchy, accessibility, responsive/loading/stale/blocked/no-data states, and snapshot-only values",
  "traceability_inherited_from": [
    "POST-SUBTASK-123"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "CALIBRATION",
    "END_TO_END",
    "OPERATIONS",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-040: Prediction-first dashboard and BAS experience.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-120.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Validate prediction-first hierarchy, accessibility, responsive/loading/stale/blocked/no-data states, and snapshot-only values

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-040: Prediction-first dashboard and BAS experience.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-040 (Prediction-first dashboard and BAS experience): Validate prediction-first hierarchy, accessibility, responsive/loading/stale/blocked/no-data states, and snapshot-only values. Consume only verified prerequisite outputs from `POST-SUBTASK-117`, `POST-SUBTASK-118`, `POST-SUBTASK-119`. Produce `artifacts/product/dashboard_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Validate prediction-first hierarchy, accessibility, responsive/loading/stale/blocked/no-data states, and snapshot-only values.
- Consume only verified prerequisite outputs from `POST-SUBTASK-117`, `POST-SUBTASK-118`, `POST-SUBTASK-119`.
- Demonstrate with saved evidence: Main views make prediction and uncertainty primary, show specialization only if admitted or global-only otherwise, and never calculate independent client-side percentages/scores.
- Demonstrate with saved evidence: BAS is explicitly underperformance versus valid pregame expected margin—not loss probability—witty copy is separate from science, and thresholds/components appear only when supported with uncertainty.
- Demonstrate with saved evidence: Every displayed value traces to a snapshot field and loading/stale/blocked/missing/no-champion/null-effect/source-outage states are accessible and keyboard/screen-reader understandable.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/product/dashboard_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Build game/A&M views for score, win probability, margin, distributions, intervals, scenarios, cutoff, freshness, and model identity; Build BAS ≥3/7/14/21, component, witty-copy, scientific caveat, no-effect, and unavailable presentation.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-117 complete at required maturity
- Dependency POST-SUBTASK-118 complete at required maturity
- Dependency POST-SUBTASK-119 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-117
- POST-SUBTASK-118
- POST-SUBTASK-119

## Blocks

- POST-STORY-041
- POST-SUBTASK-121
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

- artifacts/product/dashboard_gate.json

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

1. Main views make prediction and uncertainty primary, show specialization only if admitted or global-only otherwise, and never calculate independent client-side percentages/scores.
2. BAS is explicitly underperformance versus valid pregame expected margin—not loss probability—witty copy is separate from science, and thresholds/components appear only when supported with uncertainty.
3. Every displayed value traces to a snapshot field and loading/stale/blocked/missing/no-champion/null-effect/source-outage states are accessible and keyboard/screen-reader understandable.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. The atomic scope in POST-SUBTASK-120 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-040.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w22_product_serving.py` — Run as a regression check after completing POST-SUBTASK-120; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_w22_product.py` — Run as a regression check after completing POST-SUBTASK-120; retain command, exit code, and relevant output.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/product/dashboard_gate.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **CALIBRATION** / `CALIBRATION` — `artifacts/product/dashboard_gate.json` — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- **OPERATIONS** / `OPERATIONS` — `artifacts/product/dashboard_gate.json` — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- **END_TO_END** / `END_TO_END` — `artifacts/product/dashboard_gate.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/product/dashboard_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "PRODUCTION_READY",
  "downstream_consumer": "POST-STORY-040",
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

The user sees a serious predictive product with honest uncertainty and freshness, plus clearly separated witty BAS framing that never overstates scientific evidence. The gate decision must explicitly reevaluate downstream issues: POST-STORY-041, POST-SUBTASK-121, POST-SUBTASK-122, POST-SUBTASK-123.

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-120.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that main views make prediction and uncertainty primary, show specialization only if admitted or global-only otherwise, and never calculate independent client-side percentages/scores.
- Acceptance failure: the evidence cannot demonstrate that bAS is explicitly underperformance versus valid pregame expected margin—not loss probability—witty copy is separate from science, and thresholds/components appear only when supported with uncertainty.
- Acceptance failure: the evidence cannot demonstrate that every displayed value traces to a snapshot field and loading/stale/blocked/missing/no-champion/null-effect/source-outage states are accessible and keyboard/screen-reader understandable.
- Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

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
- SRCREF-01895

## AI Context Notes

- Canonical parent Story: POST-STORY-040. Governance traceability gate: POST-SUBTASK-123. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-120.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-107_implement_deterministic_run_identities_checkpoints_retries_resume_quarantine_rer.json -->
# POST-SUBTASK-107 — [POST-SUBTASK-107] Implement deterministic run identities, checkpoints, retries, resume, quarantine, rerun, and failure propagation

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Identical inputs produce the same run identity/outcomes, resume starts at the last verified checkpoint, duplicates are prevented, and quarantine/failed gates cannot be skipped.",
    "The declared output `artifacts/mlops/checkpoint_resume_test.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-036. Governance traceability gate: POST-SUBTASK-114. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-107.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "tests/test_w21_weekly_mlops.py",
    "src/aggie_analytics/orchestration/checkpoints.py",
    "artifacts/mlops/checkpoint_resume_test.json",
    "artifacts/jira_evidence/POST-SUBTASK-107.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-024;POST-SUBTASK-105;POST-SUBTASK-106",
  "blocks": [
    "POST-SUBTASK-108"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-107_implement_deterministic_run_identities_checkpoints_retries_resume_quarantine_rer.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "EMPIRICALLY_VALIDATED",
    "downstream_consumer": "POST-SUBTASK-108",
    "governance_traceability_gate": "POST-SUBTASK-114",
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
  "component": "mlops",
  "components_expected_to_be_touched": [
    "mlops"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-107 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The output set `artifacts/mlops/checkpoint_resume_test.json` is demonstrably consumable by POST-SUBTASK-108 without manual reconstruction or undocumented state."
  ],
  "dependencies": [
    "POST-SUBTASK-024",
    "POST-SUBTASK-105",
    "POST-SUBTASK-106"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 10,
    "adr_ids": 11,
    "gap_ids": 0,
    "requirement_ids": 29,
    "risk_ids": 7
  },
  "effective_traceability_total": 57,
  "end_to_end_validation": "Validate that `artifacts/mlops/checkpoint_resume_test.json` can be parsed and consumed by `POST-SUBTASK-108` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.",
  "epic_id": "POST-EPIC-012",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-107.json",
  "evidence_state": "PLANNED",
  "execution_lane": "OPERATIONS",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "EMPIRICALLY_VALIDATED",
  "expected_outputs": [
    "artifacts/mlops/checkpoint_resume_test.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_w21_weekly_mlops.py",
    "src/aggie_analytics/orchestration/checkpoints.py",
    "src/aggie_analytics/orchestration/promotion.py",
    "src/aggie_analytics/orchestration/publication.py",
    "docs/105_W21_AUTONOMOUS_WEEKLY_MLOPS.md"
  ],
  "files_expected_to_be_touched": [
    "tests/test_w21_weekly_mlops.py",
    "src/aggie_analytics/orchestration/checkpoints.py"
  ],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_w21_weekly_mlops.py",
    "src/aggie_analytics/orchestration/checkpoints.py",
    "src/aggie_analytics/orchestration/promotion.py",
    "src/aggie_analytics/orchestration/publication.py",
    "docs/105_W21_AUTONOMOUS_WEEKLY_MLOPS.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-107_implement_deterministic_run_identities_checkpoints_retries_resume_quarantine_rer.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-114",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100411,
  "in_scope": [
    "Perform the exact action: Implement deterministic run identities, checkpoints, retries, resume, quarantine, rerun, and failure propagation.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-024`, `POST-SUBTASK-105`, `POST-SUBTASK-106`.",
    "Demonstrate with saved evidence: Identical inputs produce the same run identity/outcomes, resume starts at the last verified checkpoint, duplicates are prevented, and quarantine/failed gates cannot be skipped.",
    "Demonstrate with saved evidence: The declared output `artifacts/mlops/checkpoint_resume_test.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "Produce, validate, content-hash, and register `artifacts/mlops/checkpoint_resume_test.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-457",
  "labels": [
    "actionable",
    "core-release",
    "mlops",
    "operations",
    "post-wave",
    "subtask"
  ],
  "last_content_audit": "2026-08-08",
  "local_id": "POST-SUBTASK-107",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Implement deterministic run identities, checkpoints, retries, resume, quarantine, rerun, and failure propagation",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24597",
    "jira_updated_at": "2026-08-09T00:04:00.175-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.",
    "Work assigned to sibling subtasks: Wire approved adapters through immutable raw capture, normalization, entities, PIT state, features, approved model, calibration, and prediction; Validate representative real end-to-end run lineage, resources, blockers, and no-fixture production behavior.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-036",
  "phase": "PHASE-4",
  "prerequisites": [
    "Dependency POST-SUBTASK-105 complete at required maturity",
    "Dependency POST-SUBTASK-024 complete at required maturity",
    "Dependency POST-SUBTASK-106 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02079",
    "SRCREF-02080",
    "SRCREF-02081",
    "SRCREF-02082"
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
    "tests/test_w21_weekly_mlops.py",
    "src/aggie_analytics/orchestration/checkpoints.py",
    "src/aggie_analytics/orchestration/promotion.py",
    "src/aggie_analytics/orchestration/publication.py",
    "docs/105_W21_AUTONOMOUS_WEEKLY_MLOPS.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/mlops/checkpoint_resume_test.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-107; retain command, exit code, and relevant output.",
      "path": "tests/test_w21_weekly_mlops.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-107; retain command, exit code, and relevant output.",
      "path": "tools/validate_w21_mlops.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/mlops/checkpoint_resume_test.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "OPERATIONS",
      "expectation": "Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.",
      "path": "artifacts/mlops/checkpoint_resume_test.json",
      "validation_class": "OPERATIONS"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/mlops/checkpoint_resume_test.json",
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
      "path": "NEW_TEST_REQUIRED::POST-SUBTASK-107",
      "validation_class": "NEW_AUTOMATED_TEST_REQUIRED"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-107.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that identical inputs produce the same run identity/outcomes, resume starts at the last verified checkpoint, duplicates are prevented, and quarantine/failed gates cannot be skipped.",
    "Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/mlops/checkpoint_resume_test.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 2 of 3 step in Story POST-STORY-036 (Production weekly acquisition-to-prediction chain): Implement deterministic run identities, checkpoints, retries, resume, quarantine, rerun, and failure propagation. Consume only verified prerequisite outputs from `POST-SUBTASK-024`, `POST-SUBTASK-105`, `POST-SUBTASK-106`. Produce `artifacts/mlops/checkpoint_resume_test.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-108.",
  "source_ids": [
    "GAP-012",
    "HANDOFF-010"
  ],
  "source_refs": [
    "SRCREF-02079",
    "SRCREF-02080",
    "SRCREF-02081",
    "SRCREF-02082",
    "SRCREF-02083",
    "SRCREF-02084",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01896",
    "SRCREF-01574"
  ],
  "specificity_fingerprint": "561dc47cce49ea7de947f722b77b6e3b1ee2ff5411ca3b7998d74fb3ac92548e",
  "stop_conditions": [
    "Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.",
    "Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.",
    "Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence."
  ],
  "supporting_source_refs": [
    "SRCREF-02083",
    "SRCREF-02084",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01896",
    "SRCREF-01574"
  ],
  "title": "[POST-SUBTASK-107] Implement deterministic run identities, checkpoints, retries, resume, quarantine, rerun, and failure propagation",
  "traceability_inherited_from": [
    "POST-SUBTASK-114"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "END_TO_END",
    "NEW_AUTOMATED_TEST_REQUIRED",
    "OPERATIONS",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-036: Production weekly acquisition-to-prediction chain.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-107.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Implement deterministic run identities, checkpoints, retries, resume, quarantine, rerun, and failure propagation

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-036: Production weekly acquisition-to-prediction chain.

## Scope

Execute the atomic 2 of 3 step in Story POST-STORY-036 (Production weekly acquisition-to-prediction chain): Implement deterministic run identities, checkpoints, retries, resume, quarantine, rerun, and failure propagation. Consume only verified prerequisite outputs from `POST-SUBTASK-024`, `POST-SUBTASK-105`, `POST-SUBTASK-106`. Produce `artifacts/mlops/checkpoint_resume_test.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-108.

### Explicit In Scope

- Perform the exact action: Implement deterministic run identities, checkpoints, retries, resume, quarantine, rerun, and failure propagation.
- Consume only verified prerequisite outputs from `POST-SUBTASK-024`, `POST-SUBTASK-105`, `POST-SUBTASK-106`.
- Demonstrate with saved evidence: Identical inputs produce the same run identity/outcomes, resume starts at the last verified checkpoint, duplicates are prevented, and quarantine/failed gates cannot be skipped.
- Demonstrate with saved evidence: The declared output `artifacts/mlops/checkpoint_resume_test.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/mlops/checkpoint_resume_test.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Wire approved adapters through immutable raw capture, normalization, entities, PIT state, features, approved model, calibration, and prediction; Validate representative real end-to-end run lineage, resources, blockers, and no-fixture production behavior.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-105 complete at required maturity
- Dependency POST-SUBTASK-024 complete at required maturity
- Dependency POST-SUBTASK-106 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-024
- POST-SUBTASK-105
- POST-SUBTASK-106

## Blocks

- POST-SUBTASK-108

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_w21_weekly_mlops.py
- src/aggie_analytics/orchestration/checkpoints.py
- src/aggie_analytics/orchestration/promotion.py
- src/aggie_analytics/orchestration/publication.py
- docs/105_W21_AUTONOMOUS_WEEKLY_MLOPS.md

## Files Expected To Be Modified

- tests/test_w21_weekly_mlops.py
- src/aggie_analytics/orchestration/checkpoints.py

## Components Expected To Be Touched

- mlops

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

- artifacts/mlops/checkpoint_resume_test.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-114`
- Inherited from: POST-SUBTASK-114
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 10, "adr_ids": 11, "gap_ids": 0, "requirement_ids": 29, "risk_ids": 7}`

## Acceptance Criteria

1. Identical inputs produce the same run identity/outcomes, resume starts at the last verified checkpoint, duplicates are prevented, and quarantine/failed gates cannot be skipped.
2. The declared output `artifacts/mlops/checkpoint_resume_test.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Definition of Done

1. The atomic scope in POST-SUBTASK-107 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The output set `artifacts/mlops/checkpoint_resume_test.json` is demonstrably consumable by POST-SUBTASK-108 without manual reconstruction or undocumented state.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w21_weekly_mlops.py` — Run as a regression check after completing POST-SUBTASK-107; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_w21_mlops.py` — Run as a regression check after completing POST-SUBTASK-107; retain command, exit code, and relevant output.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/mlops/checkpoint_resume_test.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **OPERATIONS** / `OPERATIONS` — `artifacts/mlops/checkpoint_resume_test.json` — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- **END_TO_END** / `END_TO_END` — `artifacts/mlops/checkpoint_resume_test.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- **NEW_AUTOMATED_TEST_REQUIRED** / `NEW_AUTOMATED_TEST_REQUIRED` — `NEW_TEST_REQUIRED::POST-SUBTASK-107` — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Required Evidence

- `artifacts/mlops/checkpoint_resume_test.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "EMPIRICALLY_VALIDATED",
  "downstream_consumer": "POST-SUBTASK-108",
  "governance_traceability_gate": "POST-SUBTASK-114",
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

Validate that `artifacts/mlops/checkpoint_resume_test.json` can be parsed and consumed by `POST-SUBTASK-108` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

## Expected Maturity After Completion

`EMPIRICALLY_VALIDATED`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-107.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that identical inputs produce the same run identity/outcomes, resume starts at the last verified checkpoint, duplicates are prevented, and quarantine/failed gates cannot be skipped.
- Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/mlops/checkpoint_resume_test.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Stop Conditions

- Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.
- Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.
- Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence.

## Source References

- SRCREF-02079
- SRCREF-02080
- SRCREF-02081
- SRCREF-02082
- SRCREF-02083
- SRCREF-02084
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01896
- SRCREF-01574

## AI Context Notes

- Canonical parent Story: POST-STORY-036. Governance traceability gate: POST-SUBTASK-114. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-107.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

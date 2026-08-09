<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-070_materialize_official_score_margin_win_distribution_market_lane_and_bas_support_t.json -->
# POST-SUBTASK-070 — [POST-SUBTASK-070] Materialize official score, margin, win, distribution, market-lane, and BAS-support target tables with game lineage

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Targets declare cancellations, overtime, missing scores, neutral sites, lower divisions, and official outcome source; every row links to canonical game evidence.",
    "The declared output `artifacts/modeling/target_dataset_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-024. Governance traceability gate: POST-SUBTASK-078. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-070.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/modeling/target_dataset_manifest.json",
    "artifacts/jira_evidence/POST-SUBTASK-070.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-051;POST-SUBTASK-060",
  "blocks": [
    "POST-SUBTASK-071",
    "POST-SUBTASK-072"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-070_materialize_official_score_margin_win_distribution_market_lane_and_bas_support_t.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "IMPLEMENTED",
    "downstream_consumer": "POST-SUBTASK-071",
    "governance_traceability_gate": "POST-SUBTASK-078",
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
  "component": "modeling",
  "components_expected_to_be_touched": [
    "modeling"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-070 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The output set `artifacts/modeling/target_dataset_manifest.json` is demonstrably consumable by POST-SUBTASK-071 without manual reconstruction or undocumented state."
  ],
  "dependencies": [
    "POST-SUBTASK-051",
    "POST-SUBTASK-060"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 21,
    "adr_ids": 72,
    "gap_ids": 1,
    "requirement_ids": 139,
    "risk_ids": 53
  },
  "effective_traceability_total": 286,
  "end_to_end_validation": "Validate that `artifacts/modeling/target_dataset_manifest.json` can be parsed and consumed by `POST-SUBTASK-071` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.",
  "epic_id": "POST-EPIC-008",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-070.json",
  "evidence_state": "PLANNED",
  "execution_lane": "DATA_MATERIALIZATION",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "IMPLEMENTED",
  "expected_outputs": [
    "artifacts/modeling/target_dataset_manifest.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "src/aggie_analytics/modeling/baselines.py",
    "src/aggie_analytics/modeling/joint.py",
    "src/aggie_analytics/modeling/runtime.py",
    "docs/51_MODEL_TARGETS_AND_OUTPUT_COHERENCE.md",
    "docs/103_W20_MODEL_CALIBRATION_BAS_IMPLEMENTATION.md",
    "docs/52_MODEL_ARCHITECTURE_CANDIDATES.md",
    "docs/53_JOINT_SCORE_AND_SIMULATION.md"
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
    "src/aggie_analytics/modeling/baselines.py",
    "src/aggie_analytics/modeling/joint.py",
    "src/aggie_analytics/modeling/runtime.py",
    "docs/51_MODEL_TARGETS_AND_OUTPUT_COHERENCE.md",
    "docs/103_W20_MODEL_CALIBRATION_BAS_IMPLEMENTATION.md",
    "docs/52_MODEL_ARCHITECTURE_CANDIDATES.md",
    "docs/53_JOINT_SCORE_AND_SIMULATION.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-070_materialize_official_score_margin_win_distribution_market_lane_and_bas_support_t.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-078",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100374,
  "in_scope": [
    "Perform the exact action: Materialize official score, margin, win, distribution, market-lane, and BAS-support target tables with game lineage.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-060`.",
    "Demonstrate with saved evidence: Targets declare cancellations, overtime, missing scores, neutral sites, lower divisions, and official outcome source; every row links to canonical game evidence.",
    "Demonstrate with saved evidence: The declared output `artifacts/modeling/target_dataset_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "Produce, validate, content-hash, and register `artifacts/modeling/target_dataset_manifest.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-420",
  "labels": [
    "actionable",
    "core-release",
    "data-materialization",
    "modeling",
    "post-wave",
    "subtask"
  ],
  "last_content_audit": "2026-08-08",
  "local_id": "POST-SUBTASK-070",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Materialize official score, margin, win, distribution, market-lane, and BAS-support target tables with game lineage",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24560",
    "jira_updated_at": "2026-08-09T00:03:46.609-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.",
    "Work assigned to sibling subtasks: Materialize chronological train/tune/protected assignments, sample weights, cold-start rules, and feature/target separation; Approve model dataset identity, leakage isolation, duplicate handling, and reproducibility.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-024",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-060 complete at required maturity",
    "Dependency POST-SUBTASK-051 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02049",
    "SRCREF-02050",
    "SRCREF-02051",
    "SRCREF-02052"
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
    "src/aggie_analytics/modeling/baselines.py",
    "src/aggie_analytics/modeling/joint.py",
    "src/aggie_analytics/modeling/runtime.py",
    "docs/51_MODEL_TARGETS_AND_OUTPUT_COHERENCE.md",
    "docs/103_W20_MODEL_CALIBRATION_BAS_IMPLEMENTATION.md",
    "docs/52_MODEL_ARCHITECTURE_CANDIDATES.md",
    "docs/53_JOINT_SCORE_AND_SIMULATION.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/modeling/target_dataset_manifest.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-070; retain command, exit code, and relevant output.",
      "path": "tests/test_model_architecture_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-070; retain command, exit code, and relevant output.",
      "path": "tests/test_w20_model_starter.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-070; retain command, exit code, and relevant output.",
      "path": "tools/validate_model_architecture.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/modeling/target_dataset_manifest.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "INTEGRATION",
      "expectation": "Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.",
      "path": "artifacts/modeling/target_dataset_manifest.json",
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
      "path": "NEW_TEST_REQUIRED::POST-SUBTASK-070",
      "validation_class": "NEW_AUTOMATED_TEST_REQUIRED"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-070.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that targets declare cancellations, overtime, missing scores, neutral sites, lower divisions, and official outcome source; every row links to canonical game evidence.",
    "Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/modeling/target_dataset_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 1 of 3 step in Story POST-STORY-024 (Model-ready targets, splits, weights, and datasets): Materialize official score, margin, win, distribution, market-lane, and BAS-support target tables with game lineage. Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-060`. Produce `artifacts/modeling/target_dataset_manifest.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-071.",
  "source_ids": [
    "AC-013",
    "AC-015",
    "GAP-008",
    "HANDOFF-006"
  ],
  "source_refs": [
    "SRCREF-02049",
    "SRCREF-02050",
    "SRCREF-02051",
    "SRCREF-02052",
    "SRCREF-02053",
    "SRCREF-02054",
    "SRCREF-02055",
    "SRCREF-02056",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01892",
    "SRCREF-01570",
    "SRCREF-00992",
    "SRCREF-00994"
  ],
  "specificity_fingerprint": "dc51c6cf852be742a18c36ab14a01470fcf7dda1d8107b645f6c0a559ed8b7a9",
  "stop_conditions": [
    "Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.",
    "Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.",
    "Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence."
  ],
  "supporting_source_refs": [
    "SRCREF-02053",
    "SRCREF-02054",
    "SRCREF-02055",
    "SRCREF-02056",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01892",
    "SRCREF-01570",
    "SRCREF-00992",
    "SRCREF-00994"
  ],
  "title": "[POST-SUBTASK-070] Materialize official score, margin, win, distribution, market-lane, and BAS-support target tables with game lineage",
  "traceability_inherited_from": [
    "POST-SUBTASK-078"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "INTEGRATION",
    "NEW_AUTOMATED_TEST_REQUIRED",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-024: Model-ready targets, splits, weights, and datasets.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-070.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Materialize official score, margin, win, distribution, market-lane, and BAS-support target tables with game lineage

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-024: Model-ready targets, splits, weights, and datasets.

## Scope

Execute the atomic 1 of 3 step in Story POST-STORY-024 (Model-ready targets, splits, weights, and datasets): Materialize official score, margin, win, distribution, market-lane, and BAS-support target tables with game lineage. Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-060`. Produce `artifacts/modeling/target_dataset_manifest.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-071.

### Explicit In Scope

- Perform the exact action: Materialize official score, margin, win, distribution, market-lane, and BAS-support target tables with game lineage.
- Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-060`.
- Demonstrate with saved evidence: Targets declare cancellations, overtime, missing scores, neutral sites, lower divisions, and official outcome source; every row links to canonical game evidence.
- Demonstrate with saved evidence: The declared output `artifacts/modeling/target_dataset_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/modeling/target_dataset_manifest.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Materialize chronological train/tune/protected assignments, sample weights, cold-start rules, and feature/target separation; Approve model dataset identity, leakage isolation, duplicate handling, and reproducibility.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-060 complete at required maturity
- Dependency POST-SUBTASK-051 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-051
- POST-SUBTASK-060

## Blocks

- POST-SUBTASK-071
- POST-SUBTASK-072

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- src/aggie_analytics/modeling/baselines.py
- src/aggie_analytics/modeling/joint.py
- src/aggie_analytics/modeling/runtime.py
- docs/51_MODEL_TARGETS_AND_OUTPUT_COHERENCE.md
- docs/103_W20_MODEL_CALIBRATION_BAS_IMPLEMENTATION.md
- docs/52_MODEL_ARCHITECTURE_CANDIDATES.md
- docs/53_JOINT_SCORE_AND_SIMULATION.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- modeling

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

- artifacts/modeling/target_dataset_manifest.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-078`
- Inherited from: POST-SUBTASK-078
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 21, "adr_ids": 72, "gap_ids": 1, "requirement_ids": 139, "risk_ids": 53}`

## Acceptance Criteria

1. Targets declare cancellations, overtime, missing scores, neutral sites, lower divisions, and official outcome source; every row links to canonical game evidence.
2. The declared output `artifacts/modeling/target_dataset_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Definition of Done

1. The atomic scope in POST-SUBTASK-070 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The output set `artifacts/modeling/target_dataset_manifest.json` is demonstrably consumable by POST-SUBTASK-071 without manual reconstruction or undocumented state.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_model_architecture_governance.py` — Run as a regression check after completing POST-SUBTASK-070; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w20_model_starter.py` — Run as a regression check after completing POST-SUBTASK-070; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_model_architecture.py` — Run as a regression check after completing POST-SUBTASK-070; retain command, exit code, and relevant output.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/modeling/target_dataset_manifest.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **INTEGRATION** / `INTEGRATION` — `artifacts/modeling/target_dataset_manifest.json` — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- **NEW_AUTOMATED_TEST_REQUIRED** / `NEW_AUTOMATED_TEST_REQUIRED` — `NEW_TEST_REQUIRED::POST-SUBTASK-070` — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Required Evidence

- `artifacts/modeling/target_dataset_manifest.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
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
  "downstream_consumer": "POST-SUBTASK-071",
  "governance_traceability_gate": "POST-SUBTASK-078",
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

Validate that `artifacts/modeling/target_dataset_manifest.json` can be parsed and consumed by `POST-SUBTASK-071` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

## Expected Maturity After Completion

`IMPLEMENTED`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-070.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that targets declare cancellations, overtime, missing scores, neutral sites, lower divisions, and official outcome source; every row links to canonical game evidence.
- Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/modeling/target_dataset_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Stop Conditions

- Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.
- Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.
- Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence.

## Source References

- SRCREF-02049
- SRCREF-02050
- SRCREF-02051
- SRCREF-02052
- SRCREF-02053
- SRCREF-02054
- SRCREF-02055
- SRCREF-02056
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01892
- SRCREF-01570
- SRCREF-00992
- SRCREF-00994

## AI Context Notes

- Canonical parent Story: POST-STORY-024. Governance traceability gate: POST-SUBTASK-078. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-070.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

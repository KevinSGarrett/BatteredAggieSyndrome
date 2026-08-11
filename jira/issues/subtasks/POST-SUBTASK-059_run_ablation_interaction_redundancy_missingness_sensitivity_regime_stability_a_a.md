<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-059_run_ablation_interaction_redundancy_missingness_sensitivity_regime_stability_a_a.json -->
# POST-SUBTASK-059 — [POST-SUBTASK-059] Run ablation, interaction, redundancy, missingness sensitivity, regime stability, A&M/peer, and market-lane analyses

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Ablations retain null/negative results and report task/season/regime/A&M/peer/market-lane uncertainty, redundancy, and instability rather than cherry-picking one favorable slice.",
    "The declared output `artifacts/features/feature_ablation_stability.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-020. Governance traceability gate: POST-SUBTASK-060. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-059.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/features/feature_ablation_stability.json",
    "artifacts/jira_evidence/POST-SUBTASK-059.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-057;POST-SUBTASK-058",
  "blocks": [
    "POST-SUBTASK-060"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-059_run_ablation_interaction_redundancy_missingness_sensitivity_regime_stability_a_a.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "EMPIRICALLY_VALIDATED",
    "downstream_consumer": "POST-SUBTASK-060",
    "governance_traceability_gate": "POST-SUBTASK-060",
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
  "component": "feature-engineering",
  "components_expected_to_be_touched": [
    "feature-engineering",
    "features"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-059 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The output set `artifacts/features/feature_ablation_stability.json` is demonstrably consumable by POST-SUBTASK-060 without manual reconstruction or undocumented state."
  ],
  "dependencies": [
    "POST-SUBTASK-057",
    "POST-SUBTASK-058"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 5,
    "adr_ids": 12,
    "gap_ids": 1,
    "requirement_ids": 50,
    "risk_ids": 19
  },
  "effective_traceability_total": 87,
  "end_to_end_validation": "Validate that `artifacts/features/feature_ablation_stability.json` can be parsed and consumed by `POST-SUBTASK-060` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.",
  "epic_id": "POST-EPIC-006",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-059.json",
  "evidence_state": "PLANNED",
  "execution_lane": "RESEARCH_LANE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "EMPIRICALLY_VALIDATED",
  "expected_outputs": [
    "artifacts/features/feature_ablation_stability.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/features/factory.py",
    "src/aggie_analytics/features/lifecycle.py",
    "src/aggie_analytics/features/screening.py",
    "docs/22_RAW_FEATURE_REGISTRY_ARCHITECTURE.md",
    "docs/28_FEATURE_ABLATION_AND_STABILITY.md",
    "docs/25_FEATURE_ENGINEERING_ARCHITECTURE.md",
    "docs/26_FEATURE_SCREENING_AND_SELECTION.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/features/factory.py",
    "src/aggie_analytics/features/lifecycle.py",
    "src/aggie_analytics/features/screening.py",
    "docs/22_RAW_FEATURE_REGISTRY_ARCHITECTURE.md",
    "docs/28_FEATURE_ABLATION_AND_STABILITY.md",
    "docs/25_FEATURE_ENGINEERING_ARCHITECTURE.md",
    "docs/26_FEATURE_SCREENING_AND_SELECTION.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-059_run_ablation_interaction_redundancy_missingness_sensitivity_regime_stability_a_a.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-060",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100363,
  "in_scope": [
    "Perform the exact action: Run ablation, interaction, redundancy, missingness sensitivity, regime stability, A&M/peer, and market-lane analyses.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-057`, `POST-SUBTASK-058`.",
    "Demonstrate with saved evidence: Ablations retain null/negative results and report task/season/regime/A&M/peer/market-lane uncertainty, redundancy, and instability rather than cherry-picking one favorable slice.",
    "Demonstrate with saved evidence: The declared output `artifacts/features/feature_ablation_stability.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "Produce, validate, content-hash, and register `artifacts/features/feature_ablation_stability.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-409",
  "labels": [
    "actionable",
    "core-release",
    "features",
    "post-wave",
    "research-lane",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-059",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Run ablation, interaction, redundancy, missingness sensitivity, regime stability, A&M/peer, and market-lane analyses",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24549",
    "jira_updated_at": "2026-08-09T23:24:05.193-0500",
    "last_synced_at": "2026-08-11T06:07:11.607568+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\JIRA-LIVE-CATCHUP-20260811\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Run staged univariate/multivariate screening and bounded feature tournaments on permitted tuning history; Publish the evidence-backed production feature lifecycle decision.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-020",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-057 complete at required maturity",
    "Dependency POST-SUBTASK-058 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02033",
    "SRCREF-02034",
    "SRCREF-02035",
    "SRCREF-02036"
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
    "src/aggie_analytics/features/factory.py",
    "src/aggie_analytics/features/lifecycle.py",
    "src/aggie_analytics/features/screening.py",
    "docs/22_RAW_FEATURE_REGISTRY_ARCHITECTURE.md",
    "docs/28_FEATURE_ABLATION_AND_STABILITY.md",
    "docs/25_FEATURE_ENGINEERING_ARCHITECTURE.md",
    "docs/26_FEATURE_SCREENING_AND_SELECTION.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/features/feature_ablation_stability.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-059; retain command, exit code, and relevant output.",
      "path": "tests/test_feature_registry_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-059; retain command, exit code, and relevant output.",
      "path": "tests/test_feature_lifecycle_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-059; retain command, exit code, and relevant output.",
      "path": "tests/test_feature_tournament_full.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/features/feature_ablation_stability.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "INTEGRATION",
      "expectation": "Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.",
      "path": "artifacts/features/feature_ablation_stability.json",
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
      "path": "NEW_TEST_REQUIRED::POST-SUBTASK-059",
      "validation_class": "NEW_AUTOMATED_TEST_REQUIRED"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-059.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that ablations retain null/negative results and report task/season/regime/A&M/peer/market-lane uncertainty, redundancy, and instability rather than cherry-picking one favorable slice.",
    "Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/features/feature_ablation_stability.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 2 of 3 step in Story POST-STORY-020 (Screening, ablation, stability, and promotion): Run ablation, interaction, redundancy, missingness sensitivity, regime stability, A&M/peer, and market-lane analyses. Consume only verified prerequisite outputs from `POST-SUBTASK-057`, `POST-SUBTASK-058`. Produce `artifacts/features/feature_ablation_stability.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-060.",
  "source_ids": [
    "GAP-007",
    "HANDOFF-005"
  ],
  "source_refs": [
    "SRCREF-02033",
    "SRCREF-02034",
    "SRCREF-02035",
    "SRCREF-02036",
    "SRCREF-02037",
    "SRCREF-02038",
    "SRCREF-02039",
    "SRCREF-02040",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01891",
    "SRCREF-01569"
  ],
  "specificity_fingerprint": "9395946e7a73c4bcca46ccc07c446364c582b341fecd09a6459ac3ee6dac47d1",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
  ],
  "supporting_source_refs": [
    "SRCREF-02037",
    "SRCREF-02038",
    "SRCREF-02039",
    "SRCREF-02040",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01891",
    "SRCREF-01569"
  ],
  "title": "[POST-SUBTASK-059] Run ablation, interaction, redundancy, missingness sensitivity, regime stability, A&M/peer, and market-lane analyses",
  "traceability_inherited_from": [
    "POST-SUBTASK-060"
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
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-020: Screening, ablation, stability, and promotion.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-059.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Run ablation, interaction, redundancy, missingness sensitivity, regime stability, A&M/peer, and market-lane analyses

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-020: Screening, ablation, stability, and promotion.

## Scope

Execute the atomic 2 of 3 step in Story POST-STORY-020 (Screening, ablation, stability, and promotion): Run ablation, interaction, redundancy, missingness sensitivity, regime stability, A&M/peer, and market-lane analyses. Consume only verified prerequisite outputs from `POST-SUBTASK-057`, `POST-SUBTASK-058`. Produce `artifacts/features/feature_ablation_stability.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-060.

### Explicit In Scope

- Perform the exact action: Run ablation, interaction, redundancy, missingness sensitivity, regime stability, A&M/peer, and market-lane analyses.
- Consume only verified prerequisite outputs from `POST-SUBTASK-057`, `POST-SUBTASK-058`.
- Demonstrate with saved evidence: Ablations retain null/negative results and report task/season/regime/A&M/peer/market-lane uncertainty, redundancy, and instability rather than cherry-picking one favorable slice.
- Demonstrate with saved evidence: The declared output `artifacts/features/feature_ablation_stability.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/features/feature_ablation_stability.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Run staged univariate/multivariate screening and bounded feature tournaments on permitted tuning history; Publish the evidence-backed production feature lifecycle decision.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-057 complete at required maturity
- Dependency POST-SUBTASK-058 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-057
- POST-SUBTASK-058

## Blocks

- POST-SUBTASK-060

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/features/factory.py
- src/aggie_analytics/features/lifecycle.py
- src/aggie_analytics/features/screening.py
- docs/22_RAW_FEATURE_REGISTRY_ARCHITECTURE.md
- docs/28_FEATURE_ABLATION_AND_STABILITY.md
- docs/25_FEATURE_ENGINEERING_ARCHITECTURE.md
- docs/26_FEATURE_SCREENING_AND_SELECTION.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- feature-engineering
- features

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

- artifacts/features/feature_ablation_stability.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-060`
- Inherited from: POST-SUBTASK-060
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 5, "adr_ids": 12, "gap_ids": 1, "requirement_ids": 50, "risk_ids": 19}`

## Acceptance Criteria

1. Ablations retain null/negative results and report task/season/regime/A&M/peer/market-lane uncertainty, redundancy, and instability rather than cherry-picking one favorable slice.
2. The declared output `artifacts/features/feature_ablation_stability.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Definition of Done

1. The atomic scope in POST-SUBTASK-059 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The output set `artifacts/features/feature_ablation_stability.json` is demonstrably consumable by POST-SUBTASK-060 without manual reconstruction or undocumented state.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_feature_registry_governance.py` — Run as a regression check after completing POST-SUBTASK-059; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_feature_lifecycle_governance.py` — Run as a regression check after completing POST-SUBTASK-059; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_feature_tournament_full.py` — Run as a regression check after completing POST-SUBTASK-059; retain command, exit code, and relevant output.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/features/feature_ablation_stability.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **INTEGRATION** / `INTEGRATION` — `artifacts/features/feature_ablation_stability.json` — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- **NEW_AUTOMATED_TEST_REQUIRED** / `NEW_AUTOMATED_TEST_REQUIRED` — `NEW_TEST_REQUIRED::POST-SUBTASK-059` — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Required Evidence

- `artifacts/features/feature_ablation_stability.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
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
  "downstream_consumer": "POST-SUBTASK-060",
  "governance_traceability_gate": "POST-SUBTASK-060",
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

Validate that `artifacts/features/feature_ablation_stability.json` can be parsed and consumed by `POST-SUBTASK-060` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.

## Expected Maturity After Completion

`EMPIRICALLY_VALIDATED`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-059.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that ablations retain null/negative results and report task/season/regime/A&M/peer/market-lane uncertainty, redundancy, and instability rather than cherry-picking one favorable slice.
- Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/features/feature_ablation_stability.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

## Source References

- SRCREF-02033
- SRCREF-02034
- SRCREF-02035
- SRCREF-02036
- SRCREF-02037
- SRCREF-02038
- SRCREF-02039
- SRCREF-02040
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01891
- SRCREF-01569

## AI Context Notes

- Canonical parent Story: POST-STORY-020. Governance traceability gate: POST-SUBTASK-060. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-059.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

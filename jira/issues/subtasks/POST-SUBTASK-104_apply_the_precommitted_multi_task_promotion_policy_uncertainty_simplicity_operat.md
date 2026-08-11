<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-104_apply_the_precommitted_multi_task_promotion_policy_uncertainty_simplicity_operat.json -->
# POST-SUBTASK-104 — [POST-SUBTASK-104] Apply the precommitted multi-task promotion policy, uncertainty, simplicity, operational compatibility, A&M decision, and BAS scientific decision

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "No new metric/weight/threshold/candidate/segment is created after protected results; ties/inconclusive outcomes follow the sealed simpler/incumbent/no-promotion rule and null A&M/BAS findings remain valid.",
    "The declared output `artifacts/validation/promotion_ranking.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-035. Governance traceability gate: POST-SUBTASK-105. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-104.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/validation/promotion_ranking.json",
    "artifacts/jira_evidence/POST-SUBTASK-104.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-087;POST-SUBTASK-096;POST-SUBTASK-102;POST-SUBTASK-103",
  "blocks": [
    "POST-SUBTASK-105"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-104_apply_the_precommitted_multi_task_promotion_policy_uncertainty_simplicity_operat.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "EMPIRICALLY_VALIDATED",
    "downstream_consumer": "POST-SUBTASK-105",
    "governance_traceability_gate": "POST-SUBTASK-105",
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
  "component": "validation-promotion",
  "components_expected_to_be_touched": [
    "validation-promotion",
    "validation"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-104 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The output set `artifacts/validation/promotion_ranking.json` is demonstrably consumable by POST-SUBTASK-105 without manual reconstruction or undocumented state."
  ],
  "dependencies": [
    "POST-SUBTASK-087",
    "POST-SUBTASK-096",
    "POST-SUBTASK-102",
    "POST-SUBTASK-103"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 62,
    "adr_ids": 26,
    "gap_ids": 0,
    "requirement_ids": 70,
    "risk_ids": 25
  },
  "effective_traceability_total": 183,
  "end_to_end_validation": "Validate that `artifacts/validation/promotion_ranking.json` can be parsed and consumed by `POST-SUBTASK-105` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.",
  "epic_id": "POST-EPIC-011",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-104.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "EMPIRICALLY_VALIDATED",
  "expected_outputs": [
    "artifacts/validation/promotion_ranking.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/validation/promotion.py",
    "src/aggie_analytics/validation/protected.py",
    "docs/58_MODEL_PROMOTION_AND_THRESHOLD_PRECOMMITMENT.md",
    "docs/56_VALIDATION_AND_PROTECTED_SPLITS.md",
    "docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/validation/promotion.py",
    "src/aggie_analytics/validation/protected.py",
    "docs/58_MODEL_PROMOTION_AND_THRESHOLD_PRECOMMITMENT.md",
    "docs/56_VALIDATION_AND_PROTECTED_SPLITS.md",
    "docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-104_apply_the_precommitted_multi_task_promotion_policy_uncertainty_simplicity_operat.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-105",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100408,
  "in_scope": [
    "Perform the exact action: Apply the precommitted multi-task promotion policy, uncertainty, simplicity, operational compatibility, A&M decision, and BAS scientific decision.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-087`, `POST-SUBTASK-096`, `POST-SUBTASK-102`, `POST-SUBTASK-103`.",
    "Demonstrate with saved evidence: No new metric/weight/threshold/candidate/segment is created after protected results; ties/inconclusive outcomes follow the sealed simpler/incumbent/no-promotion rule and null A&M/BAS findings remain valid.",
    "Demonstrate with saved evidence: The declared output `artifacts/validation/promotion_ranking.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "Produce, validate, content-hash, and register `artifacts/validation/promotion_ranking.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-454",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "protected-gate",
    "subtask",
    "validation"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-104",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Apply the precommitted multi-task promotion policy, uncertainty, simplicity, operational compatibility, A&M decision, and BAS scientific decision",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24594",
    "jira_updated_at": "2026-08-09T23:24:10.233-0500",
    "last_synced_at": "2026-08-11T07:44:24.297472+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\BAT-523-tamu-availability-pages\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Evaluate task-specific calibration, intervals, tails, coherence, OOD, missingness, season/regime/source shift, market ablation, and resource robustness; Publish signed champion/retain-incumbent/no-champion artifacts and the full promotion gate matrix.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-035",
  "phase": "PHASE-4",
  "prerequisites": [
    "Dependency POST-SUBTASK-087 complete at required maturity",
    "Dependency POST-SUBTASK-096 complete at required maturity",
    "Dependency POST-SUBTASK-102 complete at required maturity",
    "Dependency POST-SUBTASK-103 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02071",
    "SRCREF-02072",
    "SRCREF-02073",
    "SRCREF-02074"
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
    "src/aggie_analytics/validation/promotion.py",
    "src/aggie_analytics/validation/protected.py",
    "docs/58_MODEL_PROMOTION_AND_THRESHOLD_PRECOMMITMENT.md",
    "docs/56_VALIDATION_AND_PROTECTED_SPLITS.md",
    "docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/validation/promotion_ranking.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-104; retain command, exit code, and relevant output.",
      "path": "tests/test_validation_science_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-104; retain command, exit code, and relevant output.",
      "path": "tools/validate_validation_science.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/validation/promotion_ranking.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/validation/promotion_ranking.json",
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
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-104.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that no new metric/weight/threshold/candidate/segment is created after protected results; ties/inconclusive outcomes follow the sealed simpler/incumbent/no-promotion rule and null A&M/BAS findings remain valid.",
    "Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/validation/promotion_ranking.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 2 of 3 step in Story POST-STORY-035 (Calibration/robustness gates, A&M/BAS decisions, and champion promotion): Apply the precommitted multi-task promotion policy, uncertainty, simplicity, operational compatibility, A&M decision, and BAS scientific decision. Consume only verified prerequisite outputs from `POST-SUBTASK-087`, `POST-SUBTASK-096`, `POST-SUBTASK-102`, `POST-SUBTASK-103`. Produce `artifacts/validation/promotion_ranking.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-105.",
  "source_ids": [
    "GAP-008",
    "GAP-009",
    "HANDOFF-006"
  ],
  "source_refs": [
    "SRCREF-02071",
    "SRCREF-02072",
    "SRCREF-02073",
    "SRCREF-02074",
    "SRCREF-02075",
    "SRCREF-02076",
    "SRCREF-02077",
    "SRCREF-02078",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01892",
    "SRCREF-01570",
    "SRCREF-01571"
  ],
  "specificity_fingerprint": "7557ec55965feea1060cdea29ae20cff370fe8497d0f56a3496945cacbd3bbf5",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
  ],
  "supporting_source_refs": [
    "SRCREF-02075",
    "SRCREF-02076",
    "SRCREF-02077",
    "SRCREF-02078",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01892",
    "SRCREF-01570",
    "SRCREF-01571"
  ],
  "title": "[POST-SUBTASK-104] Apply the precommitted multi-task promotion policy, uncertainty, simplicity, operational compatibility, A&M decision, and BAS scientific decision",
  "traceability_inherited_from": [
    "POST-SUBTASK-105"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "END_TO_END",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-035: Calibration/robustness gates, A&M/BAS decisions, and champion promotion.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-104.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Apply the precommitted multi-task promotion policy, uncertainty, simplicity, operational compatibility, A&M decision, and BAS scientific decision

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-035: Calibration/robustness gates, A&M/BAS decisions, and champion promotion.

## Scope

Execute the atomic 2 of 3 step in Story POST-STORY-035 (Calibration/robustness gates, A&M/BAS decisions, and champion promotion): Apply the precommitted multi-task promotion policy, uncertainty, simplicity, operational compatibility, A&M decision, and BAS scientific decision. Consume only verified prerequisite outputs from `POST-SUBTASK-087`, `POST-SUBTASK-096`, `POST-SUBTASK-102`, `POST-SUBTASK-103`. Produce `artifacts/validation/promotion_ranking.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-105.

### Explicit In Scope

- Perform the exact action: Apply the precommitted multi-task promotion policy, uncertainty, simplicity, operational compatibility, A&M decision, and BAS scientific decision.
- Consume only verified prerequisite outputs from `POST-SUBTASK-087`, `POST-SUBTASK-096`, `POST-SUBTASK-102`, `POST-SUBTASK-103`.
- Demonstrate with saved evidence: No new metric/weight/threshold/candidate/segment is created after protected results; ties/inconclusive outcomes follow the sealed simpler/incumbent/no-promotion rule and null A&M/BAS findings remain valid.
- Demonstrate with saved evidence: The declared output `artifacts/validation/promotion_ranking.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/validation/promotion_ranking.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Evaluate task-specific calibration, intervals, tails, coherence, OOD, missingness, season/regime/source shift, market ablation, and resource robustness; Publish signed champion/retain-incumbent/no-champion artifacts and the full promotion gate matrix.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-087 complete at required maturity
- Dependency POST-SUBTASK-096 complete at required maturity
- Dependency POST-SUBTASK-102 complete at required maturity
- Dependency POST-SUBTASK-103 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-087
- POST-SUBTASK-096
- POST-SUBTASK-102
- POST-SUBTASK-103

## Blocks

- POST-SUBTASK-105

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/validation/promotion.py
- src/aggie_analytics/validation/protected.py
- docs/58_MODEL_PROMOTION_AND_THRESHOLD_PRECOMMITMENT.md
- docs/56_VALIDATION_AND_PROTECTED_SPLITS.md
- docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- validation-promotion
- validation

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

- artifacts/validation/promotion_ranking.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-105`
- Inherited from: POST-SUBTASK-105
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 62, "adr_ids": 26, "gap_ids": 0, "requirement_ids": 70, "risk_ids": 25}`

## Acceptance Criteria

1. No new metric/weight/threshold/candidate/segment is created after protected results; ties/inconclusive outcomes follow the sealed simpler/incumbent/no-promotion rule and null A&M/BAS findings remain valid.
2. The declared output `artifacts/validation/promotion_ranking.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Definition of Done

1. The atomic scope in POST-SUBTASK-104 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The output set `artifacts/validation/promotion_ranking.json` is demonstrably consumable by POST-SUBTASK-105 without manual reconstruction or undocumented state.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_validation_science_governance.py` — Run as a regression check after completing POST-SUBTASK-104; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_validation_science.py` — Run as a regression check after completing POST-SUBTASK-104; retain command, exit code, and relevant output.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/validation/promotion_ranking.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **END_TO_END** / `END_TO_END` — `artifacts/validation/promotion_ranking.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/validation/promotion_ranking.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
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
  "downstream_consumer": "POST-SUBTASK-105",
  "governance_traceability_gate": "POST-SUBTASK-105",
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

Validate that `artifacts/validation/promotion_ranking.json` can be parsed and consumed by `POST-SUBTASK-105` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.

## Expected Maturity After Completion

`EMPIRICALLY_VALIDATED`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-104.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that no new metric/weight/threshold/candidate/segment is created after protected results; ties/inconclusive outcomes follow the sealed simpler/incumbent/no-promotion rule and null A&M/BAS findings remain valid.
- Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/validation/promotion_ranking.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

## Source References

- SRCREF-02071
- SRCREF-02072
- SRCREF-02073
- SRCREF-02074
- SRCREF-02075
- SRCREF-02076
- SRCREF-02077
- SRCREF-02078
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01892
- SRCREF-01570
- SRCREF-01571

## AI Context Notes

- Canonical parent Story: POST-STORY-035. Governance traceability gate: POST-SUBTASK-105. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-104.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

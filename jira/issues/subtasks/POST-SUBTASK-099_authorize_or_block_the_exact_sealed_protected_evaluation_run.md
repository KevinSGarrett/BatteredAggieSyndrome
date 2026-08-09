<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-099_authorize_or_block_the_exact_sealed_protected_evaluation_run.json -->
# POST-SUBTASK-099 — [POST-SUBTASK-099] Authorize or block the exact sealed protected evaluation run

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "All seal files/registries/assignments/thresholds/data identities match recorded hashes; a mutation or missing seal blocks evaluation and cannot be waived to make a candidate pass.",
    "Only evaluation code can access protected outcomes, every access is attributable, training/tuning cannot read labels/scorecards, and partial failures do not return outcomes for iterative tuning.",
    "Authorization names exact candidates/tasks/cutoffs/lanes/splits/metrics/thresholds/evidence destinations and verifies all PIT/feature/model/A&M/BAS prerequisites or remains blocked.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-033. Governance traceability gate: POST-SUBTASK-105. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-099.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/validation/protected_run_authorization.json",
    "artifacts/jira_evidence/POST-SUBTASK-099.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-078;POST-SUBTASK-084;POST-SUBTASK-090;POST-SUBTASK-097;POST-SUBTASK-098",
  "blocks": [
    "POST-STORY-034",
    "POST-SUBTASK-100",
    "POST-SUBTASK-101",
    "POST-SUBTASK-102"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-099_authorize_or_block_the_exact_sealed_protected_evaluation_run.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-033",
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
    "The atomic scope in POST-SUBTASK-099 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-033."
  ],
  "dependencies": [
    "POST-SUBTASK-078",
    "POST-SUBTASK-084",
    "POST-SUBTASK-090",
    "POST-SUBTASK-097",
    "POST-SUBTASK-098"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 62,
    "adr_ids": 26,
    "gap_ids": 0,
    "requirement_ids": 70,
    "risk_ids": 25
  },
  "effective_traceability_total": 183,
  "end_to_end_validation": "An immutable, auditable authorization proves what may be evaluated and prevents protected outcomes from influencing candidate construction. The gate decision must explicitly reevaluate downstream issues: POST-STORY-034, POST-SUBTASK-100, POST-SUBTASK-101, POST-SUBTASK-102.",
  "epic_id": "POST-EPIC-011",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-099.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/validation/protected_run_authorization.json"
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
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "src/aggie_analytics/validation/promotion.py",
    "docs/56_VALIDATION_AND_PROTECTED_SPLITS.md",
    "docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md",
    "src/aggie_analytics/validation/protected.py"
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
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "src/aggie_analytics/validation/promotion.py",
    "docs/56_VALIDATION_AND_PROTECTED_SPLITS.md",
    "docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md",
    "src/aggie_analytics/validation/protected.py"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-099_authorize_or_block_the_exact_sealed_protected_evaluation_run.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-105",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100403,
  "in_scope": [
    "Perform the exact action: Authorize or block the exact sealed protected evaluation run.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-078`, `POST-SUBTASK-084`, `POST-SUBTASK-090`, `POST-SUBTASK-097`, `POST-SUBTASK-098`.",
    "Demonstrate with saved evidence: All seal files/registries/assignments/thresholds/data identities match recorded hashes; a mutation or missing seal blocks evaluation and cannot be waived to make a candidate pass.",
    "Demonstrate with saved evidence: Only evaluation code can access protected outcomes, every access is attributable, training/tuning cannot read labels/scorecards, and partial failures do not return outcomes for iterative tuning.",
    "Demonstrate with saved evidence: Authorization names exact candidates/tasks/cutoffs/lanes/splits/metrics/thresholds/evidence destinations and verifies all PIT/feature/model/A&M/BAS prerequisites or remains blocked.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `artifacts/validation/protected_run_authorization.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-449",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "protected-gate",
    "subtask",
    "validation"
  ],
  "last_content_audit": "2026-08-08",
  "local_id": "POST-SUBTASK-099",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Authorize or block the exact sealed protected evaluation run",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24589",
    "jira_updated_at": "2026-08-09T00:03:56.790-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.",
    "Work assigned to sibling subtasks: Verify protected split, judging-rule, threshold, feature, model, A&M, BAS, peer, and candidate seal hashes; Establish protected-outcome access isolation, audit logging, one-way evidence, and failure preservation.",
    "Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-033",
  "phase": "PHASE-4",
  "prerequisites": [
    "Dependency POST-SUBTASK-078 complete at required maturity",
    "Dependency POST-SUBTASK-084 complete at required maturity",
    "Dependency POST-SUBTASK-090 complete at required maturity",
    "Dependency POST-SUBTASK-097 complete at required maturity",
    "Dependency POST-SUBTASK-098 complete at required maturity"
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
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "src/aggie_analytics/validation/promotion.py",
    "docs/56_VALIDATION_AND_PROTECTED_SPLITS.md",
    "docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md",
    "src/aggie_analytics/validation/protected.py"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/validation/protected_run_authorization.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-099; retain command, exit code, and relevant output.",
      "path": "tests/test_validation_science_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-099; retain command, exit code, and relevant output.",
      "path": "tools/validate_validation_science.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "CHRONOLOGICAL_REPLAY",
      "expectation": "Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.",
      "path": "artifacts/validation/protected_run_authorization.json",
      "validation_class": "CHRONOLOGICAL_REPLAY"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/validation/protected_run_authorization.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "SECURITY",
      "expectation": "Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.",
      "path": "artifacts/validation/protected_run_authorization.json",
      "validation_class": "SECURITY"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/validation/protected_run_authorization.json",
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
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-099.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that all seal files/registries/assignments/thresholds/data identities match recorded hashes; a mutation or missing seal blocks evaluation and cannot be waived to make a candidate pass.",
    "Acceptance failure: the evidence cannot demonstrate that only evaluation code can access protected outcomes, every access is attributable, training/tuning cannot read labels/scorecards, and partial failures do not return outcomes for iterative tuning.",
    "Acceptance failure: the evidence cannot demonstrate that authorization names exact candidates/tasks/cutoffs/lanes/splits/metrics/thresholds/evidence destinations and verifies all PIT/feature/model/A&M/BAS prerequisites or remains blocked.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-033 (Protected split, judging rule, threshold, candidate, and access seal): Authorize or block the exact sealed protected evaluation run. Consume only verified prerequisite outputs from `POST-SUBTASK-078`, `POST-SUBTASK-084`, `POST-SUBTASK-090`, `POST-SUBTASK-097`, `POST-SUBTASK-098`. Produce `artifacts/validation/protected_run_authorization.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
  "source_ids": [
    "AC-013",
    "AC-015",
    "AC-017",
    "GAP-008",
    "GAP-009",
    "HANDOFF-006",
    "HANDOFF-007",
    "HANDOFF-009"
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
    "SRCREF-01571",
    "SRCREF-01893",
    "SRCREF-01895",
    "SRCREF-00992",
    "SRCREF-00994",
    "SRCREF-00996"
  ],
  "specificity_fingerprint": "2a117911a8c1f2b7581e0edcb1dd66bd4b75d5abf2868a860f80744b930939cd",
  "stop_conditions": [
    "Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.",
    "Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.",
    "Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence."
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
    "SRCREF-01571",
    "SRCREF-01893",
    "SRCREF-01895",
    "SRCREF-00992",
    "SRCREF-00994",
    "SRCREF-00996"
  ],
  "title": "[POST-SUBTASK-099] Authorize or block the exact sealed protected evaluation run",
  "traceability_inherited_from": [
    "POST-SUBTASK-105"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "CHRONOLOGICAL_REPLAY",
    "END_TO_END",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC",
    "SECURITY"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-033: Protected split, judging rule, threshold, candidate, and access seal.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-099.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Authorize or block the exact sealed protected evaluation run

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-033: Protected split, judging rule, threshold, candidate, and access seal.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-033 (Protected split, judging rule, threshold, candidate, and access seal): Authorize or block the exact sealed protected evaluation run. Consume only verified prerequisite outputs from `POST-SUBTASK-078`, `POST-SUBTASK-084`, `POST-SUBTASK-090`, `POST-SUBTASK-097`, `POST-SUBTASK-098`. Produce `artifacts/validation/protected_run_authorization.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Authorize or block the exact sealed protected evaluation run.
- Consume only verified prerequisite outputs from `POST-SUBTASK-078`, `POST-SUBTASK-084`, `POST-SUBTASK-090`, `POST-SUBTASK-097`, `POST-SUBTASK-098`.
- Demonstrate with saved evidence: All seal files/registries/assignments/thresholds/data identities match recorded hashes; a mutation or missing seal blocks evaluation and cannot be waived to make a candidate pass.
- Demonstrate with saved evidence: Only evaluation code can access protected outcomes, every access is attributable, training/tuning cannot read labels/scorecards, and partial failures do not return outcomes for iterative tuning.
- Demonstrate with saved evidence: Authorization names exact candidates/tasks/cutoffs/lanes/splits/metrics/thresholds/evidence destinations and verifies all PIT/feature/model/A&M/BAS prerequisites or remains blocked.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/validation/protected_run_authorization.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Verify protected split, judging-rule, threshold, feature, model, A&M, BAS, peer, and candidate seal hashes; Establish protected-outcome access isolation, audit logging, one-way evidence, and failure preservation.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-078 complete at required maturity
- Dependency POST-SUBTASK-084 complete at required maturity
- Dependency POST-SUBTASK-090 complete at required maturity
- Dependency POST-SUBTASK-097 complete at required maturity
- Dependency POST-SUBTASK-098 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-078
- POST-SUBTASK-084
- POST-SUBTASK-090
- POST-SUBTASK-097
- POST-SUBTASK-098

## Blocks

- POST-STORY-034
- POST-SUBTASK-100
- POST-SUBTASK-101
- POST-SUBTASK-102

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- src/aggie_analytics/validation/promotion.py
- docs/56_VALIDATION_AND_PROTECTED_SPLITS.md
- docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md
- src/aggie_analytics/validation/protected.py

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

- artifacts/validation/protected_run_authorization.json

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

1. All seal files/registries/assignments/thresholds/data identities match recorded hashes; a mutation or missing seal blocks evaluation and cannot be waived to make a candidate pass.
2. Only evaluation code can access protected outcomes, every access is attributable, training/tuning cannot read labels/scorecards, and partial failures do not return outcomes for iterative tuning.
3. Authorization names exact candidates/tasks/cutoffs/lanes/splits/metrics/thresholds/evidence destinations and verifies all PIT/feature/model/A&M/BAS prerequisites or remains blocked.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. The atomic scope in POST-SUBTASK-099 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-033.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_validation_science_governance.py` — Run as a regression check after completing POST-SUBTASK-099; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_validation_science.py` — Run as a regression check after completing POST-SUBTASK-099; retain command, exit code, and relevant output.
- **CHRONOLOGICAL_REPLAY** / `CHRONOLOGICAL_REPLAY` — `artifacts/validation/protected_run_authorization.json` — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/validation/protected_run_authorization.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **SECURITY** / `SECURITY` — `artifacts/validation/protected_run_authorization.json` — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- **END_TO_END** / `END_TO_END` — `artifacts/validation/protected_run_authorization.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/validation/protected_run_authorization.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
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
  "downstream_consumer": "POST-STORY-033",
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

An immutable, auditable authorization proves what may be evaluated and prevents protected outcomes from influencing candidate construction. The gate decision must explicitly reevaluate downstream issues: POST-STORY-034, POST-SUBTASK-100, POST-SUBTASK-101, POST-SUBTASK-102.

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-099.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that all seal files/registries/assignments/thresholds/data identities match recorded hashes; a mutation or missing seal blocks evaluation and cannot be waived to make a candidate pass.
- Acceptance failure: the evidence cannot demonstrate that only evaluation code can access protected outcomes, every access is attributable, training/tuning cannot read labels/scorecards, and partial failures do not return outcomes for iterative tuning.
- Acceptance failure: the evidence cannot demonstrate that authorization names exact candidates/tasks/cutoffs/lanes/splits/metrics/thresholds/evidence destinations and verifies all PIT/feature/model/A&M/BAS prerequisites or remains blocked.
- Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Stop Conditions

- Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.
- Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.
- Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence.

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
- SRCREF-01893
- SRCREF-01895
- SRCREF-00992
- SRCREF-00994
- SRCREF-00996

## AI Context Notes

- Canonical parent Story: POST-STORY-033. Governance traceability gate: POST-SUBTASK-105. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-099.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-102_validate_prediction_coverage_scorecard_completeness_hashes_ordering_no_early_acc.json -->
# POST-SUBTASK-102 — [POST-SUBTASK-102] Validate prediction coverage, scorecard completeness, hashes, ordering, no-early-access, and independent reproducibility

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Replay advances chronologically with only then-available state/models/calibrators/thresholds, records every identity, and retries cannot change membership or expose partial scores.",
    "All precommitted metrics/segments include baselines, sample sizes, uncertainty, missing predictions, failures, calibration/coherence/OOD and no unfavorable metric is omitted.",
    "Independent recomputation reproduces metrics/candidate ordering, verifies seals/access/row identity, and incomplete/corrupt evaluation cannot be summarized as a winner.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-034. Governance traceability gate: POST-SUBTASK-105. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-102.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/validation/protected_replay_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-102.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-099;POST-SUBTASK-100;POST-SUBTASK-101",
  "blocks": [
    "POST-STORY-029",
    "POST-STORY-032",
    "POST-STORY-035",
    "POST-SUBTASK-085",
    "POST-SUBTASK-086",
    "POST-SUBTASK-087",
    "POST-SUBTASK-094",
    "POST-SUBTASK-095",
    "POST-SUBTASK-096",
    "POST-SUBTASK-103",
    "POST-SUBTASK-104",
    "POST-SUBTASK-105"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-102_validate_prediction_coverage_scorecard_completeness_hashes_ordering_no_early_acc.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-034",
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
    "The atomic scope in POST-SUBTASK-102 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-034."
  ],
  "dependencies": [
    "POST-SUBTASK-099",
    "POST-SUBTASK-100",
    "POST-SUBTASK-101"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 62,
    "adr_ids": 26,
    "gap_ids": 0,
    "requirement_ids": 70,
    "risk_ids": 25
  },
  "effective_traceability_total": 183,
  "end_to_end_validation": "Sealed immutable predictions generate complete scorecards that a separate process can reproduce without reopening tuning. The gate decision must explicitly reevaluate downstream issues: POST-STORY-029, POST-STORY-032, POST-STORY-035, POST-SUBTASK-085, POST-SUBTASK-086, POST-SUBTASK-087, POST-SUBTASK-094, POST-SUBTASK-095, POST-SUBTASK-096, POST-SUBTASK-103, POST-SUBTASK-104, POST-SUBTASK-105.",
  "epic_id": "POST-EPIC-011",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-102.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/validation/protected_replay_gate.json"
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
    "docs/56_VALIDATION_AND_PROTECTED_SPLITS.md",
    "docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md",
    "docs/57_SCORING_CALIBRATION_AND_SCORECARDS.md"
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
    "docs/56_VALIDATION_AND_PROTECTED_SPLITS.md",
    "docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md",
    "docs/57_SCORING_CALIBRATION_AND_SCORECARDS.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-102_validate_prediction_coverage_scorecard_completeness_hashes_ordering_no_early_acc.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-105",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100406,
  "in_scope": [
    "Perform the exact action: Validate prediction coverage, scorecard completeness, hashes, ordering, no-early-access, and independent reproducibility.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-099`, `POST-SUBTASK-100`, `POST-SUBTASK-101`.",
    "Demonstrate with saved evidence: Replay advances chronologically with only then-available state/models/calibrators/thresholds, records every identity, and retries cannot change membership or expose partial scores.",
    "Demonstrate with saved evidence: All precommitted metrics/segments include baselines, sample sizes, uncertainty, missing predictions, failures, calibration/coherence/OOD and no unfavorable metric is omitted.",
    "Demonstrate with saved evidence: Independent recomputation reproduces metrics/candidate ordering, verifies seals/access/row identity, and incomplete/corrupt evaluation cannot be summarized as a winner.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `artifacts/validation/protected_replay_gate.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-452",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "protected-gate",
    "subtask",
    "validation"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-102",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Validate prediction coverage, scorecard completeness, hashes, ordering, no-early-access, and independent reproducibility",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24592",
    "jira_updated_at": "2026-08-09T00:03:58.522-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Execute the sealed national, A&M-candidate, and BAS-support chronological replay once; Compute complete score, margin, win, distribution, calibration, BAS, A&M, OOD, coherence, robustness, market-lane, and segment scorecards.",
    "Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-034",
  "phase": "PHASE-4",
  "prerequisites": [
    "Dependency POST-SUBTASK-099 complete at required maturity",
    "Dependency POST-SUBTASK-100 complete at required maturity",
    "Dependency POST-SUBTASK-101 complete at required maturity"
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
    "docs/56_VALIDATION_AND_PROTECTED_SPLITS.md",
    "docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md",
    "docs/57_SCORING_CALIBRATION_AND_SCORECARDS.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/validation/protected_replay_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-102; retain command, exit code, and relevant output.",
      "path": "tests/test_validation_science_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-102; retain command, exit code, and relevant output.",
      "path": "tools/validate_validation_science.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "CHRONOLOGICAL_REPLAY",
      "expectation": "Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.",
      "path": "artifacts/validation/protected_replay_gate.json",
      "validation_class": "CHRONOLOGICAL_REPLAY"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/validation/protected_replay_gate.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "CALIBRATION",
      "expectation": "Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.",
      "path": "artifacts/validation/protected_replay_gate.json",
      "validation_class": "CALIBRATION"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/validation/protected_replay_gate.json",
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
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-102.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that replay advances chronologically with only then-available state/models/calibrators/thresholds, records every identity, and retries cannot change membership or expose partial scores.",
    "Acceptance failure: the evidence cannot demonstrate that all precommitted metrics/segments include baselines, sample sizes, uncertainty, missing predictions, failures, calibration/coherence/OOD and no unfavorable metric is omitted.",
    "Acceptance failure: the evidence cannot demonstrate that independent recomputation reproduces metrics/candidate ordering, verifies seals/access/row identity, and incomplete/corrupt evaluation cannot be summarized as a winner.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-034 (Sealed walk-forward predictions and complete scorecards): Validate prediction coverage, scorecard completeness, hashes, ordering, no-early-access, and independent reproducibility. Consume only verified prerequisite outputs from `POST-SUBTASK-099`, `POST-SUBTASK-100`, `POST-SUBTASK-101`. Produce `artifacts/validation/protected_replay_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
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
  "specificity_fingerprint": "aa43ab14b492f7d71215157b3f1eb2c072f550f9dd339cc26e9bb8307c74763f",
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
  "title": "[POST-SUBTASK-102] Validate prediction coverage, scorecard completeness, hashes, ordering, no-early-access, and independent reproducibility",
  "traceability_inherited_from": [
    "POST-SUBTASK-105"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "CALIBRATION",
    "CHRONOLOGICAL_REPLAY",
    "END_TO_END",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-034: Sealed walk-forward predictions and complete scorecards.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-102.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Validate prediction coverage, scorecard completeness, hashes, ordering, no-early-access, and independent reproducibility

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-034: Sealed walk-forward predictions and complete scorecards.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-034 (Sealed walk-forward predictions and complete scorecards): Validate prediction coverage, scorecard completeness, hashes, ordering, no-early-access, and independent reproducibility. Consume only verified prerequisite outputs from `POST-SUBTASK-099`, `POST-SUBTASK-100`, `POST-SUBTASK-101`. Produce `artifacts/validation/protected_replay_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Validate prediction coverage, scorecard completeness, hashes, ordering, no-early-access, and independent reproducibility.
- Consume only verified prerequisite outputs from `POST-SUBTASK-099`, `POST-SUBTASK-100`, `POST-SUBTASK-101`.
- Demonstrate with saved evidence: Replay advances chronologically with only then-available state/models/calibrators/thresholds, records every identity, and retries cannot change membership or expose partial scores.
- Demonstrate with saved evidence: All precommitted metrics/segments include baselines, sample sizes, uncertainty, missing predictions, failures, calibration/coherence/OOD and no unfavorable metric is omitted.
- Demonstrate with saved evidence: Independent recomputation reproduces metrics/candidate ordering, verifies seals/access/row identity, and incomplete/corrupt evaluation cannot be summarized as a winner.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/validation/protected_replay_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Execute the sealed national, A&M-candidate, and BAS-support chronological replay once; Compute complete score, margin, win, distribution, calibration, BAS, A&M, OOD, coherence, robustness, market-lane, and segment scorecards.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-099 complete at required maturity
- Dependency POST-SUBTASK-100 complete at required maturity
- Dependency POST-SUBTASK-101 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-099
- POST-SUBTASK-100
- POST-SUBTASK-101

## Blocks

- POST-STORY-029
- POST-STORY-032
- POST-STORY-035
- POST-SUBTASK-085
- POST-SUBTASK-086
- POST-SUBTASK-087
- POST-SUBTASK-094
- POST-SUBTASK-095
- POST-SUBTASK-096
- POST-SUBTASK-103
- POST-SUBTASK-104
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
- docs/56_VALIDATION_AND_PROTECTED_SPLITS.md
- docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md
- docs/57_SCORING_CALIBRATION_AND_SCORECARDS.md

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

- artifacts/validation/protected_replay_gate.json

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

1. Replay advances chronologically with only then-available state/models/calibrators/thresholds, records every identity, and retries cannot change membership or expose partial scores.
2. All precommitted metrics/segments include baselines, sample sizes, uncertainty, missing predictions, failures, calibration/coherence/OOD and no unfavorable metric is omitted.
3. Independent recomputation reproduces metrics/candidate ordering, verifies seals/access/row identity, and incomplete/corrupt evaluation cannot be summarized as a winner.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. The atomic scope in POST-SUBTASK-102 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-034.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_validation_science_governance.py` — Run as a regression check after completing POST-SUBTASK-102; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_validation_science.py` — Run as a regression check after completing POST-SUBTASK-102; retain command, exit code, and relevant output.
- **CHRONOLOGICAL_REPLAY** / `CHRONOLOGICAL_REPLAY` — `artifacts/validation/protected_replay_gate.json` — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/validation/protected_replay_gate.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **CALIBRATION** / `CALIBRATION` — `artifacts/validation/protected_replay_gate.json` — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- **END_TO_END** / `END_TO_END` — `artifacts/validation/protected_replay_gate.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/validation/protected_replay_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
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
  "downstream_consumer": "POST-STORY-034",
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

Sealed immutable predictions generate complete scorecards that a separate process can reproduce without reopening tuning. The gate decision must explicitly reevaluate downstream issues: POST-STORY-029, POST-STORY-032, POST-STORY-035, POST-SUBTASK-085, POST-SUBTASK-086, POST-SUBTASK-087, POST-SUBTASK-094, POST-SUBTASK-095, POST-SUBTASK-096, POST-SUBTASK-103, POST-SUBTASK-104, POST-SUBTASK-105.

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-102.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that replay advances chronologically with only then-available state/models/calibrators/thresholds, records every identity, and retries cannot change membership or expose partial scores.
- Acceptance failure: the evidence cannot demonstrate that all precommitted metrics/segments include baselines, sample sizes, uncertainty, missing predictions, failures, calibration/coherence/OOD and no unfavorable metric is omitted.
- Acceptance failure: the evidence cannot demonstrate that independent recomputation reproduces metrics/candidate ordering, verifies seals/access/row identity, and incomplete/corrupt evaluation cannot be summarized as a winner.
- Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

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

- Canonical parent Story: POST-STORY-034. Governance traceability gate: POST-SUBTASK-105. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-102.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

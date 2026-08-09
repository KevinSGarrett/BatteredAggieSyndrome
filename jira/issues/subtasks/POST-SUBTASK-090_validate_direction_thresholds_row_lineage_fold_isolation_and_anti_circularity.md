<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-090_validate_direction_thresholds_row_lineage_fold_isolation_and_anti_circularity.json -->
# POST-SUBTASK-090 — [POST-SUBTASK-090] Validate direction, thresholds, row lineage, fold isolation, and anti-circularity

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Each game expectation comes from a model fit without that outcome, inside permitted chronology, with model/fold/data/feature/cutoff/calibration identities per row.",
    "Labels use actual performance versus valid expected margin with ≥7 as headline, so a win may be BAS and a loss may not; thresholds/direction are sealed before A&M results.",
    "Synthetic sign cases and real spot checks prove semantics, every label links to expectation/outcome evidence, and any implementation equating BAS with loss probability fails.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "A scientifically valid null result—no persistent Aggie-specific excess after protected out-of-sample testing—must be preserved, reported, and accepted without changing the precommitted BAS definition, peers, thresholds, or evaluation window.",
    "A null, non-significant, unstable, or directionally unsupported Aggie-specific excess result is accepted and reported without forcing a nonzero BAS effect; general FBS surprise and Texas A&M-specific excess remain distinct."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-030. Governance traceability gate: POST-SUBTASK-096. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-090.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/bas/bas_label_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-090.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-051;POST-SUBTASK-078;POST-SUBTASK-088;POST-SUBTASK-089",
  "blocks": [
    "POST-EPIC-011",
    "POST-STORY-031",
    "POST-STORY-033",
    "POST-SUBTASK-091",
    "POST-SUBTASK-092",
    "POST-SUBTASK-093",
    "POST-SUBTASK-097",
    "POST-SUBTASK-098",
    "POST-SUBTASK-099"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-090_validate_direction_thresholds_row_lineage_fold_isolation_and_anti_circularity.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-030",
    "governance_traceability_gate": "POST-SUBTASK-096",
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
  "component": "bas-science",
  "components_expected_to_be_touched": [
    "bas-science",
    "bas"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-090 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-030."
  ],
  "dependencies": [
    "POST-SUBTASK-051",
    "POST-SUBTASK-078",
    "POST-SUBTASK-088",
    "POST-SUBTASK-089"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 19,
    "adr_ids": 21,
    "gap_ids": 1,
    "requirement_ids": 66,
    "risk_ids": 13
  },
  "effective_traceability_total": 120,
  "end_to_end_validation": "Every BAS label is a traceable out-of-sample residual severity event rather than a renamed loss or circular model residual. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-011, POST-STORY-031, POST-STORY-033, POST-SUBTASK-091, POST-SUBTASK-092, POST-SUBTASK-093, POST-SUBTASK-097, POST-SUBTASK-098, POST-SUBTASK-099.",
  "epic_id": "POST-EPIC-010",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-090.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/bas/bas_label_gate.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "tests/test_bas_science_governance.py",
    "src/aggie_analytics/bas/labels.py",
    "src/aggie_analytics/bas/runtime.py",
    "docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md",
    "docs/48_BAS_COMPONENTS_REGIME_STABILITY_AND_CALIBRATION.md",
    "docs/45_SCIENTIFIC_BAS_SPECIFICATION.md"
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
    "tests/test_bas_science_governance.py",
    "src/aggie_analytics/bas/labels.py",
    "src/aggie_analytics/bas/runtime.py",
    "docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md",
    "docs/48_BAS_COMPONENTS_REGIME_STABILITY_AND_CALIBRATION.md",
    "docs/45_SCIENTIFIC_BAS_SPECIFICATION.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-090_validate_direction_thresholds_row_lineage_fold_isolation_and_anti_circularity.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-096",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100394,
  "in_scope": [
    "Perform the exact action: Validate direction, thresholds, row lineage, fold isolation, and anti-circularity.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-078`, `POST-SUBTASK-088`, `POST-SUBTASK-089`.",
    "Demonstrate with saved evidence: Each game expectation comes from a model fit without that outcome, inside permitted chronology, with model/fold/data/feature/cutoff/calibration identities per row.",
    "Demonstrate with saved evidence: Labels use actual performance versus valid expected margin with ≥7 as headline, so a win may be BAS and a loss may not; thresholds/direction are sealed before A&M results.",
    "Demonstrate with saved evidence: Synthetic sign cases and real spot checks prove semantics, every label links to expectation/outcome evidence, and any implementation equating BAS with loss probability fails.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `artifacts/bas/bas_label_gate.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-440",
  "labels": [
    "actionable",
    "bas",
    "core-release",
    "post-wave",
    "protected-gate",
    "subtask"
  ],
  "last_content_audit": "2026-08-08",
  "local_id": "POST-SUBTASK-090",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Validate direction, thresholds, row lineage, fold isolation, and anti-circularity",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24580",
    "jira_updated_at": "2026-08-09T00:03:54.583-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.",
    "Work assigned to sibling subtasks: Generate out-of-fold or chronological cross-fitted pregame expected margins for every eligible historical game; Materialize general surprise and A&M BAS severity labels at protected ≥3, ≥7, ≥14, and ≥21 thresholds.",
    "Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.",
    "Redefining BAS as generic Texas A&M loss probability or selecting specifications merely to manufacture a nonzero Aggie-specific effect."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-030",
  "phase": "PHASE-3",
  "prerequisites": [
    "Dependency POST-SUBTASK-078 complete at required maturity",
    "Dependency POST-SUBTASK-051 complete at required maturity",
    "Dependency POST-SUBTASK-088 complete at required maturity",
    "Dependency POST-SUBTASK-089 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02064",
    "SRCREF-02065",
    "SRCREF-02066",
    "SRCREF-02067"
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
    "tests/test_bas_science_governance.py",
    "src/aggie_analytics/bas/labels.py",
    "src/aggie_analytics/bas/runtime.py",
    "docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md",
    "docs/48_BAS_COMPONENTS_REGIME_STABILITY_AND_CALIBRATION.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/bas/bas_label_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-090; retain command, exit code, and relevant output.",
      "path": "tests/test_bas_science_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-090; retain command, exit code, and relevant output.",
      "path": "tests/test_w20_model_starter.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-090; retain command, exit code, and relevant output.",
      "path": "tools/validate_bas_science.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "CHRONOLOGICAL_REPLAY",
      "expectation": "Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.",
      "path": "artifacts/bas/bas_label_gate.json",
      "validation_class": "CHRONOLOGICAL_REPLAY"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/bas/bas_label_gate.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "CALIBRATION",
      "expectation": "Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.",
      "path": "artifacts/bas/bas_label_gate.json",
      "validation_class": "CALIBRATION"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/bas/bas_label_gate.json",
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
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-090.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that each game expectation comes from a model fit without that outcome, inside permitted chronology, with model/fold/data/feature/cutoff/calibration identities per row.",
    "Acceptance failure: the evidence cannot demonstrate that labels use actual performance versus valid expected margin with ≥7 as headline, so a win may be BAS and a loss may not; thresholds/direction are sealed before A&M results.",
    "Acceptance failure: the evidence cannot demonstrate that synthetic sign cases and real spot checks prove semantics, every label links to expectation/outcome evidence, and any implementation equating BAS with loss probability fails.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-030 (Cross-fitted expectation and protected severity labels): Validate direction, thresholds, row lineage, fold isolation, and anti-circularity. Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-078`, `POST-SUBTASK-088`, `POST-SUBTASK-089`. Produce `artifacts/bas/bas_label_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
  "source_ids": [
    "AC-020",
    "AC-021",
    "GAP-009",
    "HANDOFF-009"
  ],
  "source_refs": [
    "SRCREF-02064",
    "SRCREF-02065",
    "SRCREF-02066",
    "SRCREF-02067",
    "SRCREF-02068",
    "SRCREF-02069",
    "SRCREF-02070",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01895",
    "SRCREF-01571",
    "SRCREF-00999",
    "SRCREF-01000"
  ],
  "specificity_fingerprint": "4877bac992eb9d2541987f5c53ea8fa9739e50453db3fb42e28db86ed856ced2",
  "stop_conditions": [
    "Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.",
    "Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.",
    "Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence.",
    "Stop if the proposed method, threshold, peer set, fold construction, or product wording would conceal, reject, or overwrite a valid null/no-effect result."
  ],
  "supporting_source_refs": [
    "SRCREF-02068",
    "SRCREF-02069",
    "SRCREF-02070",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01895",
    "SRCREF-01571",
    "SRCREF-00999",
    "SRCREF-01000"
  ],
  "title": "[POST-SUBTASK-090] Validate direction, thresholds, row lineage, fold isolation, and anti-circularity",
  "traceability_inherited_from": [
    "POST-SUBTASK-096"
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
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-030: Cross-fitted expectation and protected severity labels.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-090.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Validate direction, thresholds, row lineage, fold isolation, and anti-circularity

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-030: Cross-fitted expectation and protected severity labels.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-030 (Cross-fitted expectation and protected severity labels): Validate direction, thresholds, row lineage, fold isolation, and anti-circularity. Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-078`, `POST-SUBTASK-088`, `POST-SUBTASK-089`. Produce `artifacts/bas/bas_label_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Validate direction, thresholds, row lineage, fold isolation, and anti-circularity.
- Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-078`, `POST-SUBTASK-088`, `POST-SUBTASK-089`.
- Demonstrate with saved evidence: Each game expectation comes from a model fit without that outcome, inside permitted chronology, with model/fold/data/feature/cutoff/calibration identities per row.
- Demonstrate with saved evidence: Labels use actual performance versus valid expected margin with ≥7 as headline, so a win may be BAS and a loss may not; thresholds/direction are sealed before A&M results.
- Demonstrate with saved evidence: Synthetic sign cases and real spot checks prove semantics, every label links to expectation/outcome evidence, and any implementation equating BAS with loss probability fails.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/bas/bas_label_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Generate out-of-fold or chronological cross-fitted pregame expected margins for every eligible historical game; Materialize general surprise and A&M BAS severity labels at protected ≥3, ≥7, ≥14, and ≥21 thresholds.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.
- Redefining BAS as generic Texas A&M loss probability or selecting specifications merely to manufacture a nonzero Aggie-specific effect.

## Prerequisites

- Dependency POST-SUBTASK-078 complete at required maturity
- Dependency POST-SUBTASK-051 complete at required maturity
- Dependency POST-SUBTASK-088 complete at required maturity
- Dependency POST-SUBTASK-089 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-051
- POST-SUBTASK-078
- POST-SUBTASK-088
- POST-SUBTASK-089

## Blocks

- POST-EPIC-011
- POST-STORY-031
- POST-STORY-033
- POST-SUBTASK-091
- POST-SUBTASK-092
- POST-SUBTASK-093
- POST-SUBTASK-097
- POST-SUBTASK-098
- POST-SUBTASK-099

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- tests/test_bas_science_governance.py
- src/aggie_analytics/bas/labels.py
- src/aggie_analytics/bas/runtime.py
- docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md
- docs/48_BAS_COMPONENTS_REGIME_STABILITY_AND_CALIBRATION.md
- docs/45_SCIENTIFIC_BAS_SPECIFICATION.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- bas-science
- bas

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

- artifacts/bas/bas_label_gate.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-096`
- Inherited from: POST-SUBTASK-096
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 19, "adr_ids": 21, "gap_ids": 1, "requirement_ids": 66, "risk_ids": 13}`

## Acceptance Criteria

1. Each game expectation comes from a model fit without that outcome, inside permitted chronology, with model/fold/data/feature/cutoff/calibration identities per row.
2. Labels use actual performance versus valid expected margin with ≥7 as headline, so a win may be BAS and a loss may not; thresholds/direction are sealed before A&M results.
3. Synthetic sign cases and real spot checks prove semantics, every label links to expectation/outcome evidence, and any implementation equating BAS with loss probability fails.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
5. A scientifically valid null result—no persistent Aggie-specific excess after protected out-of-sample testing—must be preserved, reported, and accepted without changing the precommitted BAS definition, peers, thresholds, or evaluation window.
6. A null, non-significant, unstable, or directionally unsupported Aggie-specific excess result is accepted and reported without forcing a nonzero BAS effect; general FBS surprise and Texas A&M-specific excess remain distinct.

## Definition of Done

1. The atomic scope in POST-SUBTASK-090 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-030.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_bas_science_governance.py` — Run as a regression check after completing POST-SUBTASK-090; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w20_model_starter.py` — Run as a regression check after completing POST-SUBTASK-090; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_bas_science.py` — Run as a regression check after completing POST-SUBTASK-090; retain command, exit code, and relevant output.
- **CHRONOLOGICAL_REPLAY** / `CHRONOLOGICAL_REPLAY` — `artifacts/bas/bas_label_gate.json` — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/bas/bas_label_gate.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **CALIBRATION** / `CALIBRATION` — `artifacts/bas/bas_label_gate.json` — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- **END_TO_END** / `END_TO_END` — `artifacts/bas/bas_label_gate.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/bas/bas_label_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
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
  "downstream_consumer": "POST-STORY-030",
  "governance_traceability_gate": "POST-SUBTASK-096",
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

Every BAS label is a traceable out-of-sample residual severity event rather than a renamed loss or circular model residual. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-011, POST-STORY-031, POST-STORY-033, POST-SUBTASK-091, POST-SUBTASK-092, POST-SUBTASK-093, POST-SUBTASK-097, POST-SUBTASK-098, POST-SUBTASK-099.

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-090.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that each game expectation comes from a model fit without that outcome, inside permitted chronology, with model/fold/data/feature/cutoff/calibration identities per row.
- Acceptance failure: the evidence cannot demonstrate that labels use actual performance versus valid expected margin with ≥7 as headline, so a win may be BAS and a loss may not; thresholds/direction are sealed before A&M results.
- Acceptance failure: the evidence cannot demonstrate that synthetic sign cases and real spot checks prove semantics, every label links to expectation/outcome evidence, and any implementation equating BAS with loss probability fails.
- Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Stop Conditions

- Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.
- Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.
- Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence.
- Stop if the proposed method, threshold, peer set, fold construction, or product wording would conceal, reject, or overwrite a valid null/no-effect result.

## Source References

- SRCREF-02064
- SRCREF-02065
- SRCREF-02066
- SRCREF-02067
- SRCREF-02068
- SRCREF-02069
- SRCREF-02070
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01895
- SRCREF-01571
- SRCREF-00999
- SRCREF-01000

## AI Context Notes

- Canonical parent Story: POST-STORY-030. Governance traceability gate: POST-SUBTASK-096. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-090.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

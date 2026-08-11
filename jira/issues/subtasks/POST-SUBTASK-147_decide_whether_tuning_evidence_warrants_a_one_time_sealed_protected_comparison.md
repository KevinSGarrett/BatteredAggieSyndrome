<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-147_decide_whether_tuning_evidence_warrants_a_one_time_sealed_protected_comparison.json -->
# POST-SUBTASK-147 — [POST-SUBTASK-147] Decide whether tuning evidence warrants a one-time sealed protected comparison

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Implementation pins code/config/data/seed/compute and leaves active champion/publication unchanged; scope expansion requires a new admitted proposal.",
    "Search/budget is fixed before results, protected outcomes stay sealed, all trials/negative results persist, and complexity/resource penalties accompany apparent lift.",
    "Precommitted tuning gates admit or reject protected comparison; no-improvement/instability/excess cost closes the experiment and admission does not imply promotion.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-049. Governance traceability gate: POST-SUBTASK-150. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-147.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/advanced/challenger_protected_admission.json",
    "artifacts/jira_evidence/POST-SUBTASK-147.json"
  ],
  "blocked_reason": "DEFERRED_OR_CONDITIONAL_BY_FINAL_HANDOFF",
  "blocks": [
    "POST-STORY-050",
    "POST-SUBTASK-148",
    "POST-SUBTASK-149",
    "POST-SUBTASK-150"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-147_decide_whether_tuning_evidence_warrants_a_one_time_sealed_protected_comparison.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-049",
    "governance_traceability_gate": "POST-SUBTASK-150",
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
  "component": "advanced-challengers",
  "components_expected_to_be_touched": [
    "advanced-challengers",
    "advanced"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-147 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-049."
  ],
  "dependencies": [
    "POST-SUBTASK-144",
    "POST-SUBTASK-145",
    "POST-SUBTASK-146"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 1,
    "adr_ids": 2,
    "gap_ids": 1,
    "requirement_ids": 5,
    "risk_ids": 1
  },
  "effective_traceability_total": 10,
  "end_to_end_validation": "An admitted challenger produces bounded, reproducible, fully logged tuning evidence without changing production or leaking protected outcomes. The gate decision must explicitly reevaluate downstream issues: POST-STORY-050, POST-SUBTASK-148, POST-SUBTASK-149, POST-SUBTASK-150.",
  "epic_id": "POST-EPIC-016",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-147.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/advanced/challenger_protected_admission.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "tests/test_advanced_challenger_full.py",
    "src/aggie_analytics/experimentation/advanced_challengers.py",
    "docs/72_ADVANCED_CHALLENGER_ADMISSION.md",
    "governance/ADVANCED_CHALLENGER_ADMISSION.csv",
    "docs/91_ADVANCED_CHALLENGER_GATE.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "tests/test_advanced_challenger_full.py",
    "src/aggie_analytics/experimentation/advanced_challengers.py",
    "docs/72_ADVANCED_CHALLENGER_ADMISSION.md",
    "governance/ADVANCED_CHALLENGER_ADMISSION.csv",
    "docs/91_ADVANCED_CHALLENGER_GATE.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-147_decide_whether_tuning_evidence_warrants_a_one_time_sealed_protected_comparison.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-150",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100451,
  "in_scope": [
    "Perform the exact action: Decide whether tuning evidence warrants a one-time sealed protected comparison.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-144`, `POST-SUBTASK-145`, `POST-SUBTASK-146`.",
    "Demonstrate with saved evidence: Implementation pins code/config/data/seed/compute and leaves active champion/publication unchanged; scope expansion requires a new admitted proposal.",
    "Demonstrate with saved evidence: Search/budget is fixed before results, protected outcomes stay sealed, all trials/negative results persist, and complexity/resource penalties accompany apparent lift.",
    "Demonstrate with saved evidence: Precommitted tuning gates admit or reject protected comparison; no-improvement/instability/excess cost closes the experiment and admission does not imply promotion.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `artifacts/advanced/challenger_protected_admission.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-497",
  "labels": [
    "actionable",
    "advanced",
    "conditional",
    "post-wave",
    "protected-gate",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-147",
  "maturity_before": "CONDITIONAL",
  "objective": "Decide whether tuning evidence warrants a one-time sealed protected comparison",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24637",
    "jira_updated_at": "2026-08-09T23:24:14.507-0500",
    "last_synced_at": "2026-08-11T07:44:24.297472+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\BAT-523-tamu-availability-pages\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Implement the admitted neural/Bayesian/graph/sequence challenger against pinned matrices/splits within fixed scope and compute; Run bounded tuning, ablation, calibration, OOD, robustness, stability, runtime, memory, maintainability, and simple-baseline comparisons retaining all failures.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-049",
  "phase": "PHASE-5",
  "prerequisites": [
    "Dependency POST-SUBTASK-144 complete at required maturity",
    "Dependency POST-SUBTASK-145 complete at required maturity",
    "Dependency POST-SUBTASK-146 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02107",
    "SRCREF-02108",
    "SRCREF-02109",
    "SRCREF-02110"
  ],
  "priority": "P3",
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
    "governance/IMPLEMENTATION_WBS.csv",
    "tests/test_advanced_challenger_full.py",
    "src/aggie_analytics/experimentation/advanced_challengers.py",
    "docs/72_ADVANCED_CHALLENGER_ADMISSION.md",
    "governance/ADVANCED_CHALLENGER_ADMISSION.csv",
    "docs/91_ADVANCED_CHALLENGER_GATE.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/advanced/challenger_protected_admission.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-147; retain command, exit code, and relevant output.",
      "path": "tests/test_advanced_challenger_full.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-147; retain command, exit code, and relevant output.",
      "path": "tools/check_advanced_challenger_admission.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/advanced/challenger_protected_admission.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/advanced/challenger_protected_admission.json",
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
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-147.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that implementation pins code/config/data/seed/compute and leaves active champion/publication unchanged; scope expansion requires a new admitted proposal.",
    "Acceptance failure: the evidence cannot demonstrate that search/budget is fixed before results, protected outcomes stay sealed, all trials/negative results persist, and complexity/resource penalties accompany apparent lift.",
    "Acceptance failure: the evidence cannot demonstrate that precommitted tuning gates admit or reject protected comparison; no-improvement/instability/excess cost closes the experiment and admission does not imply promotion.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-049 (Bounded implementation, tuning, ablation, and protected admission): Decide whether tuning evidence warrants a one-time sealed protected comparison. Consume only verified prerequisite outputs from `POST-SUBTASK-144`, `POST-SUBTASK-145`, `POST-SUBTASK-146`. Produce `artifacts/advanced/challenger_protected_admission.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
  "source_ids": [
    "GAP-013",
    "HANDOFF-013",
    "TASK-165",
    "TASK-166",
    "TASK-167",
    "TASK-168"
  ],
  "source_refs": [
    "SRCREF-02107",
    "SRCREF-02108",
    "SRCREF-02109",
    "SRCREF-02110",
    "SRCREF-02111",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01899",
    "SRCREF-01575",
    "SRCREF-00198",
    "SRCREF-00199",
    "SRCREF-00200",
    "SRCREF-00201"
  ],
  "specificity_fingerprint": "9afbd59905ba2c98e6248488e8a33d1a461c840eeb1f078991ca848b7150011b",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
  ],
  "supporting_source_refs": [
    "SRCREF-02111",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01899",
    "SRCREF-01575",
    "SRCREF-00198",
    "SRCREF-00199",
    "SRCREF-00200",
    "SRCREF-00201"
  ],
  "title": "[POST-SUBTASK-147] Decide whether tuning evidence warrants a one-time sealed protected comparison",
  "traceability_inherited_from": [
    "POST-SUBTASK-150"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "A documented admission/replanning decision must explicitly activate this work after all stated prerequisites pass.",
  "validation_classes": [
    "END_TO_END",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-049: Bounded implementation, tuning, ablation, and protected admission.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-147.md",
  "workflow_state": "DEFERRED"
}
```

## Objective

Decide whether tuning evidence warrants a one-time sealed protected comparison

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-049: Bounded implementation, tuning, ablation, and protected admission.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-049 (Bounded implementation, tuning, ablation, and protected admission): Decide whether tuning evidence warrants a one-time sealed protected comparison. Consume only verified prerequisite outputs from `POST-SUBTASK-144`, `POST-SUBTASK-145`, `POST-SUBTASK-146`. Produce `artifacts/advanced/challenger_protected_admission.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Decide whether tuning evidence warrants a one-time sealed protected comparison.
- Consume only verified prerequisite outputs from `POST-SUBTASK-144`, `POST-SUBTASK-145`, `POST-SUBTASK-146`.
- Demonstrate with saved evidence: Implementation pins code/config/data/seed/compute and leaves active champion/publication unchanged; scope expansion requires a new admitted proposal.
- Demonstrate with saved evidence: Search/budget is fixed before results, protected outcomes stay sealed, all trials/negative results persist, and complexity/resource penalties accompany apparent lift.
- Demonstrate with saved evidence: Precommitted tuning gates admit or reject protected comparison; no-improvement/instability/excess cost closes the experiment and admission does not imply promotion.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/advanced/challenger_protected_admission.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Implement the admitted neural/Bayesian/graph/sequence challenger against pinned matrices/splits within fixed scope and compute; Run bounded tuning, ablation, calibration, OOD, robustness, stability, runtime, memory, maintainability, and simple-baseline comparisons retaining all failures.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-144 complete at required maturity
- Dependency POST-SUBTASK-145 complete at required maturity
- Dependency POST-SUBTASK-146 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-144
- POST-SUBTASK-145
- POST-SUBTASK-146

## Blocks

- POST-STORY-050
- POST-SUBTASK-148
- POST-SUBTASK-149
- POST-SUBTASK-150

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/IMPLEMENTATION_WBS.csv
- tests/test_advanced_challenger_full.py
- src/aggie_analytics/experimentation/advanced_challengers.py
- docs/72_ADVANCED_CHALLENGER_ADMISSION.md
- governance/ADVANCED_CHALLENGER_ADMISSION.csv
- docs/91_ADVANCED_CHALLENGER_GATE.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- advanced-challengers
- advanced

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

- artifacts/advanced/challenger_protected_admission.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-150`
- Inherited from: POST-SUBTASK-150
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 1, "adr_ids": 2, "gap_ids": 1, "requirement_ids": 5, "risk_ids": 1}`

## Acceptance Criteria

1. Implementation pins code/config/data/seed/compute and leaves active champion/publication unchanged; scope expansion requires a new admitted proposal.
2. Search/budget is fixed before results, protected outcomes stay sealed, all trials/negative results persist, and complexity/resource penalties accompany apparent lift.
3. Precommitted tuning gates admit or reject protected comparison; no-improvement/instability/excess cost closes the experiment and admission does not imply promotion.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. The atomic scope in POST-SUBTASK-147 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-049.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_advanced_challenger_full.py` — Run as a regression check after completing POST-SUBTASK-147; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/check_advanced_challenger_admission.py` — Run as a regression check after completing POST-SUBTASK-147; retain command, exit code, and relevant output.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/advanced/challenger_protected_admission.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **END_TO_END** / `END_TO_END` — `artifacts/advanced/challenger_protected_admission.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/advanced/challenger_protected_admission.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
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
  "downstream_consumer": "POST-STORY-049",
  "governance_traceability_gate": "POST-SUBTASK-150",
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

An admitted challenger produces bounded, reproducible, fully logged tuning evidence without changing production or leaking protected outcomes. The gate decision must explicitly reevaluate downstream issues: POST-STORY-050, POST-SUBTASK-148, POST-SUBTASK-149, POST-SUBTASK-150.

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-147.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that implementation pins code/config/data/seed/compute and leaves active champion/publication unchanged; scope expansion requires a new admitted proposal.
- Acceptance failure: the evidence cannot demonstrate that search/budget is fixed before results, protected outcomes stay sealed, all trials/negative results persist, and complexity/resource penalties accompany apparent lift.
- Acceptance failure: the evidence cannot demonstrate that precommitted tuning gates admit or reject protected comparison; no-improvement/instability/excess cost closes the experiment and admission does not imply promotion.
- Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

## Source References

- SRCREF-02107
- SRCREF-02108
- SRCREF-02109
- SRCREF-02110
- SRCREF-02111
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01899
- SRCREF-01575
- SRCREF-00198
- SRCREF-00199
- SRCREF-00200
- SRCREF-00201

## AI Context Notes

- Canonical parent Story: POST-STORY-049. Governance traceability gate: POST-SUBTASK-150. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-147.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

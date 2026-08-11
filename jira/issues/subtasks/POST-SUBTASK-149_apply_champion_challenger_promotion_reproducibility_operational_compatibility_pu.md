<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-149_apply_champion_challenger_promotion_reproducibility_operational_compatibility_pu.json -->
# POST-SUBTASK-149 — [POST-SUBTASK-149] Apply champion/challenger promotion, reproducibility, operational-compatibility, publication, product, and rollback policy

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Promotion requires policy-compliant protected evidence and a signed reproducible artifact; no-promotion retains current champion/negative evidence and any promoted candidate passes full serving/operations/rollback gates.",
    "The declared output `artifacts/advanced/challenger_promotion_decision.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-050. Governance traceability gate: POST-SUBTASK-150. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-149.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/advanced/challenger_promotion_decision.json",
    "artifacts/jira_evidence/POST-SUBTASK-149.json"
  ],
  "blocked_reason": "DEFERRED_OR_CONDITIONAL_BY_FINAL_HANDOFF",
  "blocks": [
    "POST-SUBTASK-150"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-149_apply_champion_challenger_promotion_reproducibility_operational_compatibility_pu.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "EMPIRICALLY_VALIDATED",
    "downstream_consumer": "POST-SUBTASK-150",
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
    "The atomic scope in POST-SUBTASK-149 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The output set `artifacts/advanced/challenger_promotion_decision.json` is demonstrably consumable by POST-SUBTASK-150 without manual reconstruction or undocumented state."
  ],
  "dependencies": [
    "POST-SUBTASK-147",
    "POST-SUBTASK-148"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 1,
    "adr_ids": 2,
    "gap_ids": 1,
    "requirement_ids": 5,
    "risk_ids": 1
  },
  "effective_traceability_total": 10,
  "end_to_end_validation": "Validate that `artifacts/advanced/challenger_promotion_decision.json` can be parsed and consumed by `POST-SUBTASK-150` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.",
  "epic_id": "POST-EPIC-016",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-149.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "EMPIRICALLY_VALIDATED",
  "expected_outputs": [
    "artifacts/advanced/challenger_promotion_decision.json"
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
    "docs/91_ADVANCED_CHALLENGER_GATE.md",
    "governance/ADVANCED_CHALLENGER_ADMISSION.csv"
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
    "docs/91_ADVANCED_CHALLENGER_GATE.md",
    "governance/ADVANCED_CHALLENGER_ADMISSION.csv"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-149_apply_champion_challenger_promotion_reproducibility_operational_compatibility_pu.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-150",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100453,
  "in_scope": [
    "Perform the exact action: Apply champion/challenger promotion, reproducibility, operational-compatibility, publication, product, and rollback policy.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-147`, `POST-SUBTASK-148`.",
    "Demonstrate with saved evidence: Promotion requires policy-compliant protected evidence and a signed reproducible artifact; no-promotion retains current champion/negative evidence and any promoted candidate passes full serving/operations/rollback gates.",
    "Demonstrate with saved evidence: The declared output `artifacts/advanced/challenger_promotion_decision.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "Produce, validate, content-hash, and register `artifacts/advanced/challenger_promotion_decision.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-499",
  "labels": [
    "actionable",
    "advanced",
    "conditional",
    "post-wave",
    "protected-gate",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-149",
  "maturity_before": "CONDITIONAL",
  "objective": "Apply champion/challenger promotion, reproducibility, operational-compatibility, publication, product, and rollback policy",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24639",
    "jira_updated_at": "2026-08-09T23:24:14.708-0500",
    "last_synced_at": "2026-08-11T06:30:01.758065+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\POST-SUBTASK-177-play-drive-preliminary\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Generate challenger predictions on identical sealed protected games/cutoffs/metrics and complete scientific/resource scorecards; Reconcile registries, artifacts, documentation, Jira state, operating baseline, and close-by-disposition evidence.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-050",
  "phase": "PHASE-5",
  "prerequisites": [
    "Dependency POST-SUBTASK-147 complete at required maturity",
    "Dependency POST-SUBTASK-148 complete at required maturity"
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
    "docs/91_ADVANCED_CHALLENGER_GATE.md",
    "governance/ADVANCED_CHALLENGER_ADMISSION.csv"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/advanced/challenger_promotion_decision.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-149; retain command, exit code, and relevant output.",
      "path": "tests/test_advanced_challenger_full.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-149; retain command, exit code, and relevant output.",
      "path": "tools/check_advanced_challenger_admission.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/advanced/challenger_promotion_decision.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "OPERATIONS",
      "expectation": "Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.",
      "path": "artifacts/advanced/challenger_promotion_decision.json",
      "validation_class": "OPERATIONS"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/advanced/challenger_promotion_decision.json",
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
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-149.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that promotion requires policy-compliant protected evidence and a signed reproducible artifact; no-promotion retains current champion/negative evidence and any promoted candidate passes full serving/operations/rollback gates.",
    "Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/advanced/challenger_promotion_decision.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 2 of 3 step in Story POST-STORY-050 (Protected comparison and production disposition): Apply champion/challenger promotion, reproducibility, operational-compatibility, publication, product, and rollback policy. Consume only verified prerequisite outputs from `POST-SUBTASK-147`, `POST-SUBTASK-148`. Produce `artifacts/advanced/challenger_promotion_decision.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-150.",
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
  "specificity_fingerprint": "ec202b77d1023ce3bf7713f0089a486509270b219b34f9ee64dca9855df07f91",
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
  "title": "[POST-SUBTASK-149] Apply champion/challenger promotion, reproducibility, operational-compatibility, publication, product, and rollback policy",
  "traceability_inherited_from": [
    "POST-SUBTASK-150"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "A documented admission/replanning decision must explicitly activate this work after all stated prerequisites pass.",
  "validation_classes": [
    "END_TO_END",
    "OPERATIONS",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-050: Protected comparison and production disposition.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-149.md",
  "workflow_state": "DEFERRED"
}
```

## Objective

Apply champion/challenger promotion, reproducibility, operational-compatibility, publication, product, and rollback policy

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-050: Protected comparison and production disposition.

## Scope

Execute the atomic 2 of 3 step in Story POST-STORY-050 (Protected comparison and production disposition): Apply champion/challenger promotion, reproducibility, operational-compatibility, publication, product, and rollback policy. Consume only verified prerequisite outputs from `POST-SUBTASK-147`, `POST-SUBTASK-148`. Produce `artifacts/advanced/challenger_promotion_decision.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-150.

### Explicit In Scope

- Perform the exact action: Apply champion/challenger promotion, reproducibility, operational-compatibility, publication, product, and rollback policy.
- Consume only verified prerequisite outputs from `POST-SUBTASK-147`, `POST-SUBTASK-148`.
- Demonstrate with saved evidence: Promotion requires policy-compliant protected evidence and a signed reproducible artifact; no-promotion retains current champion/negative evidence and any promoted candidate passes full serving/operations/rollback gates.
- Demonstrate with saved evidence: The declared output `artifacts/advanced/challenger_promotion_decision.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/advanced/challenger_promotion_decision.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Generate challenger predictions on identical sealed protected games/cutoffs/metrics and complete scientific/resource scorecards; Reconcile registries, artifacts, documentation, Jira state, operating baseline, and close-by-disposition evidence.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-147 complete at required maturity
- Dependency POST-SUBTASK-148 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-147
- POST-SUBTASK-148

## Blocks

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
- docs/91_ADVANCED_CHALLENGER_GATE.md
- governance/ADVANCED_CHALLENGER_ADMISSION.csv

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

- artifacts/advanced/challenger_promotion_decision.json

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

1. Promotion requires policy-compliant protected evidence and a signed reproducible artifact; no-promotion retains current champion/negative evidence and any promoted candidate passes full serving/operations/rollback gates.
2. The declared output `artifacts/advanced/challenger_promotion_decision.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Definition of Done

1. The atomic scope in POST-SUBTASK-149 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The output set `artifacts/advanced/challenger_promotion_decision.json` is demonstrably consumable by POST-SUBTASK-150 without manual reconstruction or undocumented state.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_advanced_challenger_full.py` — Run as a regression check after completing POST-SUBTASK-149; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/check_advanced_challenger_admission.py` — Run as a regression check after completing POST-SUBTASK-149; retain command, exit code, and relevant output.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/advanced/challenger_promotion_decision.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **OPERATIONS** / `OPERATIONS` — `artifacts/advanced/challenger_promotion_decision.json` — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- **END_TO_END** / `END_TO_END` — `artifacts/advanced/challenger_promotion_decision.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/advanced/challenger_promotion_decision.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
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
  "downstream_consumer": "POST-SUBTASK-150",
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

Validate that `artifacts/advanced/challenger_promotion_decision.json` can be parsed and consumed by `POST-SUBTASK-150` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.

## Expected Maturity After Completion

`EMPIRICALLY_VALIDATED`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-149.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that promotion requires policy-compliant protected evidence and a signed reproducible artifact; no-promotion retains current champion/negative evidence and any promoted candidate passes full serving/operations/rollback gates.
- Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/advanced/challenger_promotion_decision.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

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

- Canonical parent Story: POST-STORY-050. Governance traceability gate: POST-SUBTASK-150. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-149.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

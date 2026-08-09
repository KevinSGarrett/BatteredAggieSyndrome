<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-111_apply_promotion_rollback_policy_atomically_activate_approved_snapshots_and_valid.json -->
# POST-SUBTASK-111 — [POST-SUBTASK-111] Apply promotion/rollback policy, atomically activate approved snapshots, and validate immutability/freshness/consumer compatibility

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Triggers predeclare evidence/budget/freeze/skip reasons, cannot repeatedly tune on protected outcomes, preserve all failed/no-improvement challengers, and never corrupt the active champion.",
    "Snapshot rows derive only from signed run artifacts, follow protected A&M/BAS null/admission decisions, mark unsupported outputs unavailable, and are immutable/idempotent.",
    "Only complete signed non-stale snapshots activate atomically, rollback restores a verified prior pointer, product reads never see partial state, and no SLA is claimed without observed evidence.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-037. Governance traceability gate: POST-SUBTASK-114. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-111.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/forecasts/publication_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-111.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-108;POST-SUBTASK-109;POST-SUBTASK-110",
  "blocks": [
    "POST-EPIC-013",
    "POST-STORY-038",
    "POST-STORY-039",
    "POST-SUBTASK-112",
    "POST-SUBTASK-113",
    "POST-SUBTASK-114",
    "POST-SUBTASK-115",
    "POST-SUBTASK-116",
    "POST-SUBTASK-117"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-111_apply_promotion_rollback_policy_atomically_activate_approved_snapshots_and_valid.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-037",
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
    "The atomic scope in POST-SUBTASK-111 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-037."
  ],
  "dependencies": [
    "POST-SUBTASK-108",
    "POST-SUBTASK-109",
    "POST-SUBTASK-110"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 10,
    "adr_ids": 11,
    "gap_ids": 0,
    "requirement_ids": 29,
    "risk_ids": 7
  },
  "effective_traceability_total": 57,
  "end_to_end_validation": "A governed run may retain or promote a model, then publishes one immutable coherent snapshot that downstream consumers can reproduce and roll back. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-013, POST-STORY-038, POST-STORY-039, POST-SUBTASK-112, POST-SUBTASK-113, POST-SUBTASK-114, POST-SUBTASK-115, POST-SUBTASK-116, POST-SUBTASK-117.",
  "epic_id": "POST-EPIC-012",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-111.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/forecasts/publication_gate.json"
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
    "src/aggie_analytics/orchestration/publication.py"
  ],
  "files_expected_to_be_touched": [],
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
    "src/aggie_analytics/orchestration/publication.py"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-111_apply_promotion_rollback_policy_atomically_activate_approved_snapshots_and_valid.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-114",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100415,
  "in_scope": [
    "Perform the exact action: Apply promotion/rollback policy, atomically activate approved snapshots, and validate immutability/freshness/consumer compatibility.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-108`, `POST-SUBTASK-109`, `POST-SUBTASK-110`.",
    "Demonstrate with saved evidence: Triggers predeclare evidence/budget/freeze/skip reasons, cannot repeatedly tune on protected outcomes, preserve all failed/no-improvement challengers, and never corrupt the active champion.",
    "Demonstrate with saved evidence: Snapshot rows derive only from signed run artifacts, follow protected A&M/BAS null/admission decisions, mark unsupported outputs unavailable, and are immutable/idempotent.",
    "Demonstrate with saved evidence: Only complete signed non-stale snapshots activate atomically, rollback restores a verified prior pointer, product reads never see partial state, and no SLA is claimed without observed evidence.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `artifacts/forecasts/publication_gate.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-461",
  "labels": [
    "actionable",
    "core-release",
    "mlops",
    "post-wave",
    "protected-gate",
    "subtask"
  ],
  "last_content_audit": "2026-08-08",
  "local_id": "POST-SUBTASK-111",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Apply promotion/rollback policy, atomically activate approved snapshots, and validate immutability/freshness/consumer compatibility",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24601",
    "jira_updated_at": "2026-08-09T00:04:02.124-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.",
    "Work assigned to sibling subtasks: Implement season/week/data-drift/performance retraining triggers and execute reproducible challenger runs against the current champion; Build immutable forecast snapshots containing coherent scores/probabilities/uncertainty/A&M/BAS outputs plus exact state/run/model identities.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-037",
  "phase": "PHASE-4",
  "prerequisites": [
    "Dependency POST-SUBTASK-108 complete at required maturity",
    "Dependency POST-SUBTASK-109 complete at required maturity",
    "Dependency POST-SUBTASK-110 complete at required maturity"
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
    "src/aggie_analytics/orchestration/publication.py"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/forecasts/publication_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-111; retain command, exit code, and relevant output.",
      "path": "tests/test_w21_weekly_mlops.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/forecasts/publication_gate.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "OPERATIONS",
      "expectation": "Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.",
      "path": "artifacts/forecasts/publication_gate.json",
      "validation_class": "OPERATIONS"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/forecasts/publication_gate.json",
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
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-111.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that triggers predeclare evidence/budget/freeze/skip reasons, cannot repeatedly tune on protected outcomes, preserve all failed/no-improvement challengers, and never corrupt the active champion.",
    "Acceptance failure: the evidence cannot demonstrate that snapshot rows derive only from signed run artifacts, follow protected A&M/BAS null/admission decisions, mark unsupported outputs unavailable, and are immutable/idempotent.",
    "Acceptance failure: the evidence cannot demonstrate that only complete signed non-stale snapshots activate atomically, rollback restores a verified prior pointer, product reads never see partial state, and no SLA is claimed without observed evidence.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-037 (Governed retraining, promotion, immutable forecasts, and activation): Apply promotion/rollback policy, atomically activate approved snapshots, and validate immutability/freshness/consumer compatibility. Consume only verified prerequisite outputs from `POST-SUBTASK-108`, `POST-SUBTASK-109`, `POST-SUBTASK-110`. Produce `artifacts/forecasts/publication_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
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
  "specificity_fingerprint": "e244bbb8b9773f8289174d86befc9bdf027d1eeb6c64c1fa1c1015d351d4a4e9",
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
  "title": "[POST-SUBTASK-111] Apply promotion/rollback policy, atomically activate approved snapshots, and validate immutability/freshness/consumer compatibility",
  "traceability_inherited_from": [
    "POST-SUBTASK-114"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "END_TO_END",
    "OPERATIONS",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-037: Governed retraining, promotion, immutable forecasts, and activation.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-111.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Apply promotion/rollback policy, atomically activate approved snapshots, and validate immutability/freshness/consumer compatibility

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-037: Governed retraining, promotion, immutable forecasts, and activation.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-037 (Governed retraining, promotion, immutable forecasts, and activation): Apply promotion/rollback policy, atomically activate approved snapshots, and validate immutability/freshness/consumer compatibility. Consume only verified prerequisite outputs from `POST-SUBTASK-108`, `POST-SUBTASK-109`, `POST-SUBTASK-110`. Produce `artifacts/forecasts/publication_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Apply promotion/rollback policy, atomically activate approved snapshots, and validate immutability/freshness/consumer compatibility.
- Consume only verified prerequisite outputs from `POST-SUBTASK-108`, `POST-SUBTASK-109`, `POST-SUBTASK-110`.
- Demonstrate with saved evidence: Triggers predeclare evidence/budget/freeze/skip reasons, cannot repeatedly tune on protected outcomes, preserve all failed/no-improvement challengers, and never corrupt the active champion.
- Demonstrate with saved evidence: Snapshot rows derive only from signed run artifacts, follow protected A&M/BAS null/admission decisions, mark unsupported outputs unavailable, and are immutable/idempotent.
- Demonstrate with saved evidence: Only complete signed non-stale snapshots activate atomically, rollback restores a verified prior pointer, product reads never see partial state, and no SLA is claimed without observed evidence.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/forecasts/publication_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Implement season/week/data-drift/performance retraining triggers and execute reproducible challenger runs against the current champion; Build immutable forecast snapshots containing coherent scores/probabilities/uncertainty/A&M/BAS outputs plus exact state/run/model identities.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-108 complete at required maturity
- Dependency POST-SUBTASK-109 complete at required maturity
- Dependency POST-SUBTASK-110 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-108
- POST-SUBTASK-109
- POST-SUBTASK-110

## Blocks

- POST-EPIC-013
- POST-STORY-038
- POST-STORY-039
- POST-SUBTASK-112
- POST-SUBTASK-113
- POST-SUBTASK-114
- POST-SUBTASK-115
- POST-SUBTASK-116
- POST-SUBTASK-117

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

## Files Expected To Be Modified

- None.

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

- artifacts/forecasts/publication_gate.json

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

1. Triggers predeclare evidence/budget/freeze/skip reasons, cannot repeatedly tune on protected outcomes, preserve all failed/no-improvement challengers, and never corrupt the active champion.
2. Snapshot rows derive only from signed run artifacts, follow protected A&M/BAS null/admission decisions, mark unsupported outputs unavailable, and are immutable/idempotent.
3. Only complete signed non-stale snapshots activate atomically, rollback restores a verified prior pointer, product reads never see partial state, and no SLA is claimed without observed evidence.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. The atomic scope in POST-SUBTASK-111 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-037.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w21_weekly_mlops.py` — Run as a regression check after completing POST-SUBTASK-111; retain command, exit code, and relevant output.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/forecasts/publication_gate.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **OPERATIONS** / `OPERATIONS` — `artifacts/forecasts/publication_gate.json` — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- **END_TO_END** / `END_TO_END` — `artifacts/forecasts/publication_gate.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/forecasts/publication_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
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
  "downstream_consumer": "POST-STORY-037",
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

A governed run may retain or promote a model, then publishes one immutable coherent snapshot that downstream consumers can reproduce and roll back. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-013, POST-STORY-038, POST-STORY-039, POST-SUBTASK-112, POST-SUBTASK-113, POST-SUBTASK-114, POST-SUBTASK-115, POST-SUBTASK-116, POST-SUBTASK-117.

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-111.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that triggers predeclare evidence/budget/freeze/skip reasons, cannot repeatedly tune on protected outcomes, preserve all failed/no-improvement challengers, and never corrupt the active champion.
- Acceptance failure: the evidence cannot demonstrate that snapshot rows derive only from signed run artifacts, follow protected A&M/BAS null/admission decisions, mark unsupported outputs unavailable, and are immutable/idempotent.
- Acceptance failure: the evidence cannot demonstrate that only complete signed non-stale snapshots activate atomically, rollback restores a verified prior pointer, product reads never see partial state, and no SLA is claimed without observed evidence.
- Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

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

- Canonical parent Story: POST-STORY-037. Governance traceability gate: POST-SUBTASK-114. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-111.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-051_open_or_retain_blocked_the_protected_experimentation_lane_through_the_pit_replay.json -->
# POST-SUBTASK-051 — [POST-SUBTASK-051] Open or retain-blocked the protected experimentation lane through the PIT/replay readiness gate

## Canonical metadata

```json
{
  "acceptance_control_ids": [
    "AC-123"
  ],
  "acceptance_criteria": [
    "Future/postgame injections or appended records cannot change earlier eligible matrix hashes/predictions; every failure names exact source, field, row, transformation, and remediation.",
    "Replay advances chronologically, fits only on permitted history, pins all identities, never returns protected outcomes to tuning code, and resumes without future-fitted state.",
    "GAP-005 remains open until real historical replay—not fixture or synthetic replay—passes with approved matrix, split, seal, entity, source, and runner hashes.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [
    "ADR-104",
    "ADR-117",
    "ADR-125",
    "ADR-129",
    "ADR-140",
    "ADR-177",
    "ADR-183",
    "ADR-243"
  ],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-017. Governance traceability gate: POST-SUBTASK-051. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-051.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/pit/PIT_REPLAY_READINESS.json",
    "artifacts/jira_evidence/POST-SUBTASK-051.json"
  ],
  "blocked_reason": "QUALITY_GATE_BLOCKED_MATRIX_IDENTITY: 7c4b170a85d7aa8053bbbad099b8569cff6676580f18f46f375bbece8a53b3d1; BAT-398 decision BLOCK; zero accepted rows/cells",
  "blocks": [
    "POST-EPIC-008",
    "POST-STORY-019",
    "POST-STORY-024",
    "POST-STORY-030",
    "POST-SUBTASK-055",
    "POST-SUBTASK-056",
    "POST-SUBTASK-057",
    "POST-SUBTASK-070",
    "POST-SUBTASK-071",
    "POST-SUBTASK-072",
    "POST-SUBTASK-088",
    "POST-SUBTASK-089",
    "POST-SUBTASK-090"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-051_open_or_retain_blocked_the_protected_experimentation_lane_through_the_pit_replay.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-017",
    "governance_traceability_gate": "POST-SUBTASK-051",
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
  "component": "pit-temporal",
  "components_expected_to_be_touched": [
    "pit-temporal",
    "pit"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-051 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-017."
  ],
  "dependencies": [
    "POST-SUBTASK-048",
    "POST-SUBTASK-049",
    "POST-SUBTASK-050"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 1,
    "adr_ids": 8,
    "gap_ids": 1,
    "requirement_ids": 14,
    "risk_ids": 7
  },
  "effective_traceability_total": 31,
  "end_to_end_validation": "A sealed chronological run can rebuild every pregame matrix and demonstrate future/postgame mutations cannot alter earlier state or predictions. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-008, POST-STORY-019, POST-STORY-024, POST-STORY-030, POST-SUBTASK-055, POST-SUBTASK-056, POST-SUBTASK-057, POST-SUBTASK-070, POST-SUBTASK-071, POST-SUBTASK-072, POST-SUBTASK-088, POST-SUBTASK-089….",
  "epic_id": "POST-EPIC-005",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-051.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/pit/PIT_REPLAY_READINESS.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/ADR_INDEX.csv",
    "governance/REQUIREMENTS_INDEX.csv",
    "tests/test_temporal_governance.py",
    "docs/21_LEAKAGE_AND_REPLAY_TEST_SPEC.md",
    "docs/readiness/W24_END_TO_END_READINESS.md",
    "src/aggie_analytics/temporal/state.py",
    "tests/test_w24_readiness.py"
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
    "governance/ADR_INDEX.csv",
    "governance/REQUIREMENTS_INDEX.csv",
    "tests/test_temporal_governance.py",
    "docs/21_LEAKAGE_AND_REPLAY_TEST_SPEC.md",
    "docs/readiness/W24_END_TO_END_READINESS.md",
    "src/aggie_analytics/temporal/state.py",
    "tests/test_w24_readiness.py"
  ],
  "gap_ids": [
    "GAP-003"
  ],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-051_open_or_retain_blocked_the_protected_experimentation_lane_through_the_pit_replay.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-051",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100355,
  "in_scope": [
    "Perform the exact action: Open or retain-blocked the protected experimentation lane through the PIT/replay readiness gate.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-048`, `POST-SUBTASK-049`, `POST-SUBTASK-050`.",
    "Demonstrate with saved evidence: Future/postgame injections or appended records cannot change earlier eligible matrix hashes/predictions; every failure names exact source, field, row, transformation, and remediation.",
    "Demonstrate with saved evidence: Replay advances chronologically, fits only on permitted history, pins all identities, never returns protected outcomes to tuning code, and resumes without future-fitted state.",
    "Demonstrate with saved evidence: GAP-005 remains open until real historical replay—not fixture or synthetic replay—passes with approved matrix, split, seal, entity, source, and runner hashes.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `artifacts/pit/PIT_REPLAY_READINESS.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-401",
  "labels": [
    "actionable",
    "core-release",
    "pit",
    "post-wave",
    "protected-gate",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-051",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Open or retain-blocked the protected experimentation lane through the PIT/replay readiness gate",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24541",
    "jira_updated_at": "2026-08-09T23:24:04.386-0500",
    "last_synced_at": "2026-08-10T04:24:34.496382+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\BAT-516-openai-foundation-complete\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Run static, future-append, value-mutation, same-game, normalization, entity-correction, weather, market, roster, and label leakage tests on real matrices; Implement deterministic walk-forward replay with frozen train/tune/protected boundaries, fold-local transforms, checkpoint/resume, and evidence identities.",
    "Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-017",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-048 complete at required maturity",
    "Dependency POST-SUBTASK-049 complete at required maturity",
    "Dependency POST-SUBTASK-050 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02025",
    "SRCREF-02026",
    "SRCREF-02027",
    "SRCREF-02028"
  ],
  "priority": "P0",
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
    "governance/ADR_INDEX.csv",
    "governance/REQUIREMENTS_INDEX.csv",
    "tests/test_temporal_governance.py",
    "docs/21_LEAKAGE_AND_REPLAY_TEST_SPEC.md",
    "docs/readiness/W24_END_TO_END_READINESS.md",
    "src/aggie_analytics/temporal/state.py",
    "tests/test_w24_readiness.py"
  ],
  "ready": false,
  "record_revision": "2.1",
  "related_to": [],
  "required_evidence": [
    "`artifacts/pit/PIT_REPLAY_READINESS.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-051; retain command, exit code, and relevant output.",
      "path": "tests/test_temporal_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-051; retain command, exit code, and relevant output.",
      "path": "tests/test_w24_readiness.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-051; retain command, exit code, and relevant output.",
      "path": "tools/validate_w24_readiness.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "CHRONOLOGICAL_REPLAY",
      "expectation": "Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.",
      "path": "artifacts/pit/PIT_REPLAY_READINESS.json",
      "validation_class": "CHRONOLOGICAL_REPLAY"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/pit/PIT_REPLAY_READINESS.json",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "REPRODUCIBILITY",
      "expectation": "Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.",
      "path": "ISSUE_COMPLETION_MANIFEST",
      "validation_class": "REPRODUCIBILITY"
    }
  ],
  "requirement_ids": [
    "REQ-059",
    "REQ-088",
    "REQ-128",
    "REQ-283",
    "REQ-284",
    "REQ-285",
    "REQ-289",
    "REQ-291",
    "REQ-295",
    "REQ-296",
    "REQ-308",
    "REQ-315",
    "REQ-439",
    "REQ-453"
  ],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-051.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that future/postgame injections or appended records cannot change earlier eligible matrix hashes/predictions; every failure names exact source, field, row, transformation, and remediation.",
    "Acceptance failure: the evidence cannot demonstrate that replay advances chronologically, fits only on permitted history, pins all identities, never returns protected outcomes to tuning code, and resumes without future-fitted state.",
    "Acceptance failure: the evidence cannot demonstrate that gAP-005 remains open until real historical replay—not fixture or synthetic replay—passes with approved matrix, split, seal, entity, source, and runner hashes.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [
    "RISK-044",
    "RISK-050",
    "RISK-090",
    "RISK-105",
    "RISK-118",
    "RISK-158",
    "RISK-181"
  ],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-017 (Leakage battery and chronological replay infrastructure): Open or retain-blocked the protected experimentation lane through the PIT/replay readiness gate. Consume only verified prerequisite outputs from `POST-SUBTASK-048`, `POST-SUBTASK-049`, `POST-SUBTASK-050`. Produce `artifacts/pit/PIT_REPLAY_READINESS.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
  "source_ids": [
    "GAP-003",
    "GAP-005",
    "HANDOFF-004",
    "HANDOFF-005",
    "ISSUE-041"
  ],
  "source_refs": [
    "SRCREF-02025",
    "SRCREF-02026",
    "SRCREF-02027",
    "SRCREF-02028",
    "SRCREF-02029",
    "SRCREF-02030",
    "SRCREF-02031",
    "SRCREF-02032",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01890",
    "SRCREF-01567",
    "SRCREF-01565",
    "SRCREF-01891",
    "SRCREF-01941",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "specificity_fingerprint": "7253ecec874a86a7b767c1d2d3242bfd74bf5b01a0d7440e7f979929c0f20ea3",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
  ],
  "supporting_source_refs": [
    "SRCREF-02029",
    "SRCREF-02030",
    "SRCREF-02031",
    "SRCREF-02032",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01890",
    "SRCREF-01567",
    "SRCREF-01565",
    "SRCREF-01891",
    "SRCREF-01941",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "title": "[POST-SUBTASK-051] Open or retain-blocked the protected experimentation lane through the PIT/replay readiness gate",
  "traceability_inherited_from": [],
  "traceability_resolution": "DIRECT_DOMAIN_GATE",
  "unblock_condition": "Produce a new nonempty content-addressed national pregame matrix with evidence-backed game/cutoff rows, then rerun BAT-398 and obtain an explicit APPROVE decision.",
  "validation_classes": [
    "CHRONOLOGICAL_REPLAY",
    "END_TO_END",
    "REGRESSION",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-017: Leakage battery and chronological replay infrastructure.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-051.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Open or retain-blocked the protected experimentation lane through the PIT/replay readiness gate

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-017: Leakage battery and chronological replay infrastructure.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-017 (Leakage battery and chronological replay infrastructure): Open or retain-blocked the protected experimentation lane through the PIT/replay readiness gate. Consume only verified prerequisite outputs from `POST-SUBTASK-048`, `POST-SUBTASK-049`, `POST-SUBTASK-050`. Produce `artifacts/pit/PIT_REPLAY_READINESS.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Open or retain-blocked the protected experimentation lane through the PIT/replay readiness gate.
- Consume only verified prerequisite outputs from `POST-SUBTASK-048`, `POST-SUBTASK-049`, `POST-SUBTASK-050`.
- Demonstrate with saved evidence: Future/postgame injections or appended records cannot change earlier eligible matrix hashes/predictions; every failure names exact source, field, row, transformation, and remediation.
- Demonstrate with saved evidence: Replay advances chronologically, fits only on permitted history, pins all identities, never returns protected outcomes to tuning code, and resumes without future-fitted state.
- Demonstrate with saved evidence: GAP-005 remains open until real historical replay—not fixture or synthetic replay—passes with approved matrix, split, seal, entity, source, and runner hashes.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/pit/PIT_REPLAY_READINESS.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Run static, future-append, value-mutation, same-game, normalization, entity-correction, weather, market, roster, and label leakage tests on real matrices; Implement deterministic walk-forward replay with frozen train/tune/protected boundaries, fold-local transforms, checkpoint/resume, and evidence identities.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.

## Prerequisites

- Dependency POST-SUBTASK-048 complete at required maturity
- Dependency POST-SUBTASK-049 complete at required maturity
- Dependency POST-SUBTASK-050 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-048
- POST-SUBTASK-049
- POST-SUBTASK-050

## Blocks

- POST-EPIC-008
- POST-STORY-019
- POST-STORY-024
- POST-STORY-030
- POST-SUBTASK-055
- POST-SUBTASK-056
- POST-SUBTASK-057
- POST-SUBTASK-070
- POST-SUBTASK-071
- POST-SUBTASK-072
- POST-SUBTASK-088
- POST-SUBTASK-089
- POST-SUBTASK-090

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- governance/ADR_INDEX.csv
- governance/REQUIREMENTS_INDEX.csv
- tests/test_temporal_governance.py
- docs/21_LEAKAGE_AND_REPLAY_TEST_SPEC.md
- docs/readiness/W24_END_TO_END_READINESS.md
- src/aggie_analytics/temporal/state.py
- tests/test_w24_readiness.py

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- pit-temporal
- pit

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

- artifacts/pit/PIT_REPLAY_READINESS.json

## Direct Requirements

- REQ-059
- REQ-088
- REQ-128
- REQ-283
- REQ-284
- REQ-285
- REQ-289
- REQ-291
- REQ-295
- REQ-296
- REQ-308
- REQ-315
- REQ-439
- REQ-453

## Direct Acceptance Controls

- AC-123

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-051`
- Inherited from: None
- Resolution: `DIRECT_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 1, "adr_ids": 8, "gap_ids": 1, "requirement_ids": 14, "risk_ids": 7}`

## Acceptance Criteria

1. Future/postgame injections or appended records cannot change earlier eligible matrix hashes/predictions; every failure names exact source, field, row, transformation, and remediation.
2. Replay advances chronologically, fits only on permitted history, pins all identities, never returns protected outcomes to tuning code, and resumes without future-fitted state.
3. GAP-005 remains open until real historical replay—not fixture or synthetic replay—passes with approved matrix, split, seal, entity, source, and runner hashes.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. The atomic scope in POST-SUBTASK-051 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-017.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_temporal_governance.py` — Run as a regression check after completing POST-SUBTASK-051; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w24_readiness.py` — Run as a regression check after completing POST-SUBTASK-051; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_w24_readiness.py` — Run as a regression check after completing POST-SUBTASK-051; retain command, exit code, and relevant output.
- **CHRONOLOGICAL_REPLAY** / `CHRONOLOGICAL_REPLAY` — `artifacts/pit/PIT_REPLAY_READINESS.json` — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- **END_TO_END** / `END_TO_END` — `artifacts/pit/PIT_REPLAY_READINESS.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/pit/PIT_REPLAY_READINESS.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "PRODUCTION_READY",
  "downstream_consumer": "POST-STORY-017",
  "governance_traceability_gate": "POST-SUBTASK-051",
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

A sealed chronological run can rebuild every pregame matrix and demonstrate future/postgame mutations cannot alter earlier state or predictions. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-008, POST-STORY-019, POST-STORY-024, POST-STORY-030, POST-SUBTASK-055, POST-SUBTASK-056, POST-SUBTASK-057, POST-SUBTASK-070, POST-SUBTASK-071, POST-SUBTASK-072, POST-SUBTASK-088, POST-SUBTASK-089….

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-051.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that future/postgame injections or appended records cannot change earlier eligible matrix hashes/predictions; every failure names exact source, field, row, transformation, and remediation.
- Acceptance failure: the evidence cannot demonstrate that replay advances chronologically, fits only on permitted history, pins all identities, never returns protected outcomes to tuning code, and resumes without future-fitted state.
- Acceptance failure: the evidence cannot demonstrate that gAP-005 remains open until real historical replay—not fixture or synthetic replay—passes with approved matrix, split, seal, entity, source, and runner hashes.
- Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

## Source References

- SRCREF-02025
- SRCREF-02026
- SRCREF-02027
- SRCREF-02028
- SRCREF-02029
- SRCREF-02030
- SRCREF-02031
- SRCREF-02032
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01890
- SRCREF-01567
- SRCREF-01565
- SRCREF-01891
- SRCREF-01941
- SRCREF-02116
- SRCREF-02117
- SRCREF-02118

## AI Context Notes

- Canonical parent Story: POST-STORY-017. Governance traceability gate: POST-SUBTASK-051. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-051.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

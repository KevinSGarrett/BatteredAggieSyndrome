<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-061_materialize_effective_dated_roster_depth_position_participation_eligibility_tran.json -->
# POST-SUBTASK-061 — [POST-SUBTASK-061] Materialize effective-dated roster, depth, position, participation, eligibility, transfer, and role state

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Player-team-position-depth relationships retain source and known-at/effective time; current rosters cannot retroactively populate history and ambiguous identities remain reviewable.",
    "The declared output `artifacts/player_intelligence/player_state_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-021. Governance traceability gate: POST-SUBTASK-069. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-061.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/player_intelligence/player_state_manifest.json",
    "artifacts/jira_evidence/POST-SUBTASK-061.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-048",
  "blocks": [
    "POST-SUBTASK-062",
    "POST-SUBTASK-063"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-061_materialize_effective_dated_roster_depth_position_participation_eligibility_tran.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "IMPLEMENTED",
    "downstream_consumer": "POST-SUBTASK-062",
    "governance_traceability_gate": "POST-SUBTASK-069",
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
  "component": "player-context-intelligence",
  "components_expected_to_be_touched": [
    "player-context-intelligence",
    "advanced-football"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-061 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The output set `artifacts/player_intelligence/player_state_manifest.json` is demonstrably consumable by POST-SUBTASK-062 without manual reconstruction or undocumented state."
  ],
  "dependencies": [
    "POST-SUBTASK-030",
    "POST-SUBTASK-048"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 11,
    "adr_ids": 21,
    "gap_ids": 2,
    "requirement_ids": 59,
    "risk_ids": 23
  },
  "effective_traceability_total": 116,
  "end_to_end_validation": "Validate that `artifacts/player_intelligence/player_state_manifest.json` can be parsed and consumed by `POST-SUBTASK-062` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.",
  "epic_id": "POST-EPIC-007",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-061.json",
  "evidence_state": "PLANNED",
  "execution_lane": "DATA_MATERIALIZATION",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "IMPLEMENTED",
  "expected_outputs": [
    "artifacts/player_intelligence/player_state_manifest.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/context_intelligence/context.py",
    "src/aggie_analytics/player_intelligence/advanced_state.py",
    "docs/29_COACHING_INTELLIGENCE_ARCHITECTURE.md",
    "docs/29_TEAM_STATE_ARCHITECTURE.md",
    "docs/34_PLAYER_ROSTER_DEPTH_ARCHITECTURE.md",
    "docs/35_PLAYER_VALUE_REPLACEMENT_AND_AVAILABILITY.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/context_intelligence/context.py",
    "src/aggie_analytics/player_intelligence/advanced_state.py",
    "docs/29_COACHING_INTELLIGENCE_ARCHITECTURE.md",
    "docs/29_TEAM_STATE_ARCHITECTURE.md",
    "docs/34_PLAYER_ROSTER_DEPTH_ARCHITECTURE.md",
    "docs/35_PLAYER_VALUE_REPLACEMENT_AND_AVAILABILITY.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-061_materialize_effective_dated_roster_depth_position_participation_eligibility_tran.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-069",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100365,
  "in_scope": [
    "Perform the exact action: Materialize effective-dated roster, depth, position, participation, eligibility, transfer, and role state.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-030`, `POST-SUBTASK-048`.",
    "Demonstrate with saved evidence: Player-team-position-depth relationships retain source and known-at/effective time; current rosters cannot retroactively populate history and ambiguous identities remain reviewable.",
    "Demonstrate with saved evidence: The declared output `artifacts/player_intelligence/player_state_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "Produce, validate, content-hash, and register `artifacts/player_intelligence/player_state_manifest.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-411",
  "labels": [
    "actionable",
    "advanced-football",
    "core-release",
    "data-materialization",
    "post-wave",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-061",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Materialize effective-dated roster, depth, position, participation, eligibility, transfer, and role state",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24551",
    "jira_updated_at": "2026-08-09T23:24:05.661-0500",
    "last_synced_at": "2026-08-10T04:24:34.496382+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\BAT-516-openai-foundation-complete\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Estimate leakage-safe player value, replacement distributions, and timestamped availability probabilities; Validate player-state coverage, uncertainty, double-counting controls, and production eligibility.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-021",
  "phase": "PHASE-2",
  "prerequisites": [
    "Dependency POST-SUBTASK-030 complete at required maturity",
    "Dependency POST-SUBTASK-048 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02041",
    "SRCREF-02042",
    "SRCREF-02043",
    "SRCREF-02044"
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
    "src/aggie_analytics/context_intelligence/context.py",
    "src/aggie_analytics/player_intelligence/advanced_state.py",
    "docs/29_COACHING_INTELLIGENCE_ARCHITECTURE.md",
    "docs/29_TEAM_STATE_ARCHITECTURE.md",
    "docs/34_PLAYER_ROSTER_DEPTH_ARCHITECTURE.md",
    "docs/35_PLAYER_VALUE_REPLACEMENT_AND_AVAILABILITY.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/player_intelligence/player_state_manifest.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-061; retain command, exit code, and relevant output.",
      "path": "tests/test_player_intelligence_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-061; retain command, exit code, and relevant output.",
      "path": "tests/test_context_intelligence_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-061; retain command, exit code, and relevant output.",
      "path": "tests/test_team_state_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "CHRONOLOGICAL_REPLAY",
      "expectation": "Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.",
      "path": "artifacts/player_intelligence/player_state_manifest.json",
      "validation_class": "CHRONOLOGICAL_REPLAY"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/player_intelligence/player_state_manifest.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "INTEGRATION",
      "expectation": "Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.",
      "path": "artifacts/player_intelligence/player_state_manifest.json",
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
      "path": "NEW_TEST_REQUIRED::POST-SUBTASK-061",
      "validation_class": "NEW_AUTOMATED_TEST_REQUIRED"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-061.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that player-team-position-depth relationships retain source and known-at/effective time; current rosters cannot retroactively populate history and ambiguous identities remain reviewable.",
    "Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/player_intelligence/player_state_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 1 of 3 step in Story POST-STORY-021 (Historical player, roster, depth, value, replacement, and availability): Materialize effective-dated roster, depth, position, participation, eligibility, transfer, and role state. Consume only verified prerequisite outputs from `POST-SUBTASK-030`, `POST-SUBTASK-048`. Produce `artifacts/player_intelligence/player_state_manifest.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-062.",
  "source_ids": [
    "GAP-006",
    "HANDOFF-008"
  ],
  "source_refs": [
    "SRCREF-02041",
    "SRCREF-02042",
    "SRCREF-02043",
    "SRCREF-02044",
    "SRCREF-02045",
    "SRCREF-02046",
    "SRCREF-02047",
    "SRCREF-02048",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01894",
    "SRCREF-01568"
  ],
  "specificity_fingerprint": "f098b0118c571bc4897137e58e552c4889554655b74a779b6110f5fed7c4bc44",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
  ],
  "supporting_source_refs": [
    "SRCREF-02045",
    "SRCREF-02046",
    "SRCREF-02047",
    "SRCREF-02048",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01894",
    "SRCREF-01568"
  ],
  "title": "[POST-SUBTASK-061] Materialize effective-dated roster, depth, position, participation, eligibility, transfer, and role state",
  "traceability_inherited_from": [
    "POST-SUBTASK-069"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "CHRONOLOGICAL_REPLAY",
    "INTEGRATION",
    "NEW_AUTOMATED_TEST_REQUIRED",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-021: Historical player, roster, depth, value, replacement, and availability.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-061.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Materialize effective-dated roster, depth, position, participation, eligibility, transfer, and role state

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-021: Historical player, roster, depth, value, replacement, and availability.

## Scope

Execute the atomic 1 of 3 step in Story POST-STORY-021 (Historical player, roster, depth, value, replacement, and availability): Materialize effective-dated roster, depth, position, participation, eligibility, transfer, and role state. Consume only verified prerequisite outputs from `POST-SUBTASK-030`, `POST-SUBTASK-048`. Produce `artifacts/player_intelligence/player_state_manifest.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-062.

### Explicit In Scope

- Perform the exact action: Materialize effective-dated roster, depth, position, participation, eligibility, transfer, and role state.
- Consume only verified prerequisite outputs from `POST-SUBTASK-030`, `POST-SUBTASK-048`.
- Demonstrate with saved evidence: Player-team-position-depth relationships retain source and known-at/effective time; current rosters cannot retroactively populate history and ambiguous identities remain reviewable.
- Demonstrate with saved evidence: The declared output `artifacts/player_intelligence/player_state_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/player_intelligence/player_state_manifest.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Estimate leakage-safe player value, replacement distributions, and timestamped availability probabilities; Validate player-state coverage, uncertainty, double-counting controls, and production eligibility.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-030 complete at required maturity
- Dependency POST-SUBTASK-048 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-030
- POST-SUBTASK-048

## Blocks

- POST-SUBTASK-062
- POST-SUBTASK-063

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/context_intelligence/context.py
- src/aggie_analytics/player_intelligence/advanced_state.py
- docs/29_COACHING_INTELLIGENCE_ARCHITECTURE.md
- docs/29_TEAM_STATE_ARCHITECTURE.md
- docs/34_PLAYER_ROSTER_DEPTH_ARCHITECTURE.md
- docs/35_PLAYER_VALUE_REPLACEMENT_AND_AVAILABILITY.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- player-context-intelligence
- advanced-football

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

- artifacts/player_intelligence/player_state_manifest.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-069`
- Inherited from: POST-SUBTASK-069
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 11, "adr_ids": 21, "gap_ids": 2, "requirement_ids": 59, "risk_ids": 23}`

## Acceptance Criteria

1. Player-team-position-depth relationships retain source and known-at/effective time; current rosters cannot retroactively populate history and ambiguous identities remain reviewable.
2. The declared output `artifacts/player_intelligence/player_state_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Definition of Done

1. The atomic scope in POST-SUBTASK-061 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The output set `artifacts/player_intelligence/player_state_manifest.json` is demonstrably consumable by POST-SUBTASK-062 without manual reconstruction or undocumented state.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_player_intelligence_governance.py` — Run as a regression check after completing POST-SUBTASK-061; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_context_intelligence_governance.py` — Run as a regression check after completing POST-SUBTASK-061; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_team_state_governance.py` — Run as a regression check after completing POST-SUBTASK-061; retain command, exit code, and relevant output.
- **CHRONOLOGICAL_REPLAY** / `CHRONOLOGICAL_REPLAY` — `artifacts/player_intelligence/player_state_manifest.json` — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/player_intelligence/player_state_manifest.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **INTEGRATION** / `INTEGRATION` — `artifacts/player_intelligence/player_state_manifest.json` — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- **NEW_AUTOMATED_TEST_REQUIRED** / `NEW_AUTOMATED_TEST_REQUIRED` — `NEW_TEST_REQUIRED::POST-SUBTASK-061` — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Required Evidence

- `artifacts/player_intelligence/player_state_manifest.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
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
  "downstream_consumer": "POST-SUBTASK-062",
  "governance_traceability_gate": "POST-SUBTASK-069",
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

Validate that `artifacts/player_intelligence/player_state_manifest.json` can be parsed and consumed by `POST-SUBTASK-062` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.

## Expected Maturity After Completion

`IMPLEMENTED`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-061.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that player-team-position-depth relationships retain source and known-at/effective time; current rosters cannot retroactively populate history and ambiguous identities remain reviewable.
- Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/player_intelligence/player_state_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

## Source References

- SRCREF-02041
- SRCREF-02042
- SRCREF-02043
- SRCREF-02044
- SRCREF-02045
- SRCREF-02046
- SRCREF-02047
- SRCREF-02048
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01894
- SRCREF-01568

## AI Context Notes

- Canonical parent Story: POST-STORY-021. Governance traceability gate: POST-SUBTASK-069. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-061.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

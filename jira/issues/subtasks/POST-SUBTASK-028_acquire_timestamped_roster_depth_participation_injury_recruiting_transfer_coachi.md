<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-028_acquire_timestamped_roster_depth_participation_injury_recruiting_transfer_coachi.json -->
# POST-SUBTASK-028 — [POST-SUBTASK-028] Acquire timestamped roster, depth, participation, injury, recruiting, transfer, coaching, weather, venue, travel, market, resource, and mechanics evidence

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Every record retains source/published/observed/retrieved time and canonical identity candidates; absence or ambiguous timing is not converted to healthy, available, or known.",
    "The declared output `artifacts/data_lake/context_acquisition_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-010. Governance traceability gate: POST-SUBTASK-033. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-028.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/data_lake/context_acquisition_manifest.json",
    "artifacts/jira_evidence/POST-SUBTASK-028.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-027",
  "blocks": [
    "POST-SUBTASK-029",
    "POST-SUBTASK-030"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-028_acquire_timestamped_roster_depth_participation_injury_recruiting_transfer_coachi.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "IMPLEMENTED",
    "downstream_consumer": "POST-SUBTASK-029",
    "governance_traceability_gate": "POST-SUBTASK-033",
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
  "component": "raw-snapshots",
  "components_expected_to_be_touched": [
    "raw-snapshots",
    "raw-data"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-028 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The output set `artifacts/data_lake/context_acquisition_manifest.json` is demonstrably consumable by POST-SUBTASK-029 without manual reconstruction or undocumented state."
  ],
  "dependencies": [
    "POST-SUBTASK-027"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 4,
    "adr_ids": 6,
    "gap_ids": 1,
    "requirement_ids": 8,
    "risk_ids": 5
  },
  "effective_traceability_total": 24,
  "end_to_end_validation": "Validate that `artifacts/data_lake/context_acquisition_manifest.json` can be parsed and consumed by `POST-SUBTASK-029` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.",
  "epic_id": "POST-EPIC-003",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-028.json",
  "evidence_state": "PLANNED",
  "execution_lane": "DATA_MATERIALIZATION",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "IMPLEMENTED",
  "expected_outputs": [
    "artifacts/data_lake/context_acquisition_manifest.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_w19_foundation.py",
    "src/aggie_analytics/data/adapters.py",
    "src/aggie_analytics/data/contracts.py",
    "src/aggie_analytics/data/snapshots.py",
    "docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_w19_foundation.py",
    "src/aggie_analytics/data/adapters.py",
    "src/aggie_analytics/data/contracts.py",
    "src/aggie_analytics/data/snapshots.py",
    "docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-028_acquire_timestamped_roster_depth_participation_injury_recruiting_transfer_coachi.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-033",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100332,
  "in_scope": [
    "Perform the exact action: Acquire timestamped roster, depth, participation, injury, recruiting, transfer, coaching, weather, venue, travel, market, resource, and mechanics evidence.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-027`.",
    "Demonstrate with saved evidence: Every record retains source/published/observed/retrieved time and canonical identity candidates; absence or ambiguous timing is not converted to healthy, available, or known.",
    "Demonstrate with saved evidence: The declared output `artifacts/data_lake/context_acquisition_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "Produce, validate, content-hash, and register `artifacts/data_lake/context_acquisition_manifest.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-378",
  "labels": [
    "actionable",
    "core-release",
    "data-materialization",
    "post-wave",
    "raw-data",
    "subtask"
  ],
  "last_content_audit": "2026-08-08",
  "local_id": "POST-SUBTASK-028",
  "maturity_before": "SCAFFOLD",
  "objective": "Acquire timestamped roster, depth, participation, injury, recruiting, transfer, coaching, weather, venue, travel, market, resource, and mechanics evidence",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24518",
    "jira_updated_at": "2026-08-09T00:03:29.806-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.",
    "Work assigned to sibling subtasks: Profile supporting-domain schema, historical coverage, timestamp quality, upstream lineage, and rights class; Approve domain-by-domain production, experimental, conditional, rejected, or banned eligibility.",
    "Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-010",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-027 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02013",
    "SRCREF-02014",
    "SRCREF-02015",
    "SRCREF-02016"
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
    "tests/test_w19_foundation.py",
    "src/aggie_analytics/data/adapters.py",
    "src/aggie_analytics/data/contracts.py",
    "src/aggie_analytics/data/snapshots.py",
    "docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/data_lake/context_acquisition_manifest.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-028; retain command, exit code, and relevant output.",
      "path": "tests/test_w19_foundation.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "CHRONOLOGICAL_REPLAY",
      "expectation": "Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.",
      "path": "artifacts/data_lake/context_acquisition_manifest.json",
      "validation_class": "CHRONOLOGICAL_REPLAY"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/data_lake/context_acquisition_manifest.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "INTEGRATION",
      "expectation": "Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.",
      "path": "artifacts/data_lake/context_acquisition_manifest.json",
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
      "path": "NEW_TEST_REQUIRED::POST-SUBTASK-028",
      "validation_class": "NEW_AUTOMATED_TEST_REQUIRED"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-028.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that every record retains source/published/observed/retrieved time and canonical identity candidates; absence or ambiguous timing is not converted to healthy, available, or known.",
    "Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/data_lake/context_acquisition_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 1 of 3 step in Story POST-STORY-010 (Player, roster, recruiting, market, weather, and contextual raw domains): Acquire timestamped roster, depth, participation, injury, recruiting, transfer, coaching, weather, venue, travel, market, resource, and mechanics evidence. Consume only verified prerequisite outputs from `POST-SUBTASK-027`. Produce `artifacts/data_lake/context_acquisition_manifest.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-029.",
  "source_ids": [
    "GAP-002",
    "GAP-006",
    "GAP-010",
    "GAP-011",
    "HANDOFF-003",
    "HANDOFF-008"
  ],
  "source_refs": [
    "SRCREF-02013",
    "SRCREF-02014",
    "SRCREF-02015",
    "SRCREF-02016",
    "SRCREF-02017",
    "SRCREF-02018",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01889",
    "SRCREF-01564",
    "SRCREF-01894",
    "SRCREF-01568",
    "SRCREF-01572",
    "SRCREF-01573"
  ],
  "specificity_fingerprint": "a3c1d54fce4be726396a79aaf5305e07c026355305d357424e0984ca18518f2a",
  "stop_conditions": [
    "Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.",
    "Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.",
    "Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence."
  ],
  "supporting_source_refs": [
    "SRCREF-02017",
    "SRCREF-02018",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01889",
    "SRCREF-01564",
    "SRCREF-01894",
    "SRCREF-01568",
    "SRCREF-01572",
    "SRCREF-01573"
  ],
  "title": "[POST-SUBTASK-028] Acquire timestamped roster, depth, participation, injury, recruiting, transfer, coaching, weather, venue, travel, market, resource, and mechanics evidence",
  "traceability_inherited_from": [
    "POST-SUBTASK-033"
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
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-010: Player, roster, recruiting, market, weather, and contextual raw domains.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-028.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Acquire timestamped roster, depth, participation, injury, recruiting, transfer, coaching, weather, venue, travel, market, resource, and mechanics evidence

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-010: Player, roster, recruiting, market, weather, and contextual raw domains.

## Scope

Execute the atomic 1 of 3 step in Story POST-STORY-010 (Player, roster, recruiting, market, weather, and contextual raw domains): Acquire timestamped roster, depth, participation, injury, recruiting, transfer, coaching, weather, venue, travel, market, resource, and mechanics evidence. Consume only verified prerequisite outputs from `POST-SUBTASK-027`. Produce `artifacts/data_lake/context_acquisition_manifest.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-029.

### Explicit In Scope

- Perform the exact action: Acquire timestamped roster, depth, participation, injury, recruiting, transfer, coaching, weather, venue, travel, market, resource, and mechanics evidence.
- Consume only verified prerequisite outputs from `POST-SUBTASK-027`.
- Demonstrate with saved evidence: Every record retains source/published/observed/retrieved time and canonical identity candidates; absence or ambiguous timing is not converted to healthy, available, or known.
- Demonstrate with saved evidence: The declared output `artifacts/data_lake/context_acquisition_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/data_lake/context_acquisition_manifest.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Profile supporting-domain schema, historical coverage, timestamp quality, upstream lineage, and rights class; Approve domain-by-domain production, experimental, conditional, rejected, or banned eligibility.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-027 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-027

## Blocks

- POST-SUBTASK-029
- POST-SUBTASK-030

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_w19_foundation.py
- src/aggie_analytics/data/adapters.py
- src/aggie_analytics/data/contracts.py
- src/aggie_analytics/data/snapshots.py
- docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- raw-snapshots
- raw-data

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

- artifacts/data_lake/context_acquisition_manifest.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-033`
- Inherited from: POST-SUBTASK-033
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 4, "adr_ids": 6, "gap_ids": 1, "requirement_ids": 8, "risk_ids": 5}`

## Acceptance Criteria

1. Every record retains source/published/observed/retrieved time and canonical identity candidates; absence or ambiguous timing is not converted to healthy, available, or known.
2. The declared output `artifacts/data_lake/context_acquisition_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Definition of Done

1. The atomic scope in POST-SUBTASK-028 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The output set `artifacts/data_lake/context_acquisition_manifest.json` is demonstrably consumable by POST-SUBTASK-029 without manual reconstruction or undocumented state.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w19_foundation.py` — Run as a regression check after completing POST-SUBTASK-028; retain command, exit code, and relevant output.
- **CHRONOLOGICAL_REPLAY** / `CHRONOLOGICAL_REPLAY` — `artifacts/data_lake/context_acquisition_manifest.json` — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/data_lake/context_acquisition_manifest.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **INTEGRATION** / `INTEGRATION` — `artifacts/data_lake/context_acquisition_manifest.json` — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- **NEW_AUTOMATED_TEST_REQUIRED** / `NEW_AUTOMATED_TEST_REQUIRED` — `NEW_TEST_REQUIRED::POST-SUBTASK-028` — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Required Evidence

- `artifacts/data_lake/context_acquisition_manifest.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
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
  "completion_claim_limit": "IMPLEMENTED",
  "downstream_consumer": "POST-SUBTASK-029",
  "governance_traceability_gate": "POST-SUBTASK-033",
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

Validate that `artifacts/data_lake/context_acquisition_manifest.json` can be parsed and consumed by `POST-SUBTASK-029` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

## Expected Maturity After Completion

`IMPLEMENTED`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-028.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that every record retains source/published/observed/retrieved time and canonical identity candidates; absence or ambiguous timing is not converted to healthy, available, or known.
- Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/data_lake/context_acquisition_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Stop Conditions

- Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.
- Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.
- Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence.

## Source References

- SRCREF-02013
- SRCREF-02014
- SRCREF-02015
- SRCREF-02016
- SRCREF-02017
- SRCREF-02018
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01889
- SRCREF-01564
- SRCREF-01894
- SRCREF-01568
- SRCREF-01572
- SRCREF-01573

## AI Context Notes

- Canonical parent Story: POST-STORY-010. Governance traceability gate: POST-SUBTASK-033. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-028.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

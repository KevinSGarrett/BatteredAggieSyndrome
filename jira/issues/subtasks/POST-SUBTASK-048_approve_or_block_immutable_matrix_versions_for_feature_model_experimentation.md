<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-048_approve_or_block_immutable_matrix_versions_for_feature_model_experimentation.json -->
# POST-SUBTASK-048 — [POST-SUBTASK-048] Approve or block immutable matrix versions for feature/model experimentation

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "State rows retain canonical identity, effective/known-at time, source evidence, and version; corrections append and future observations do not alter prior as-of reads.",
    "Each game/cutoff row uses only eligible state, handles home/away/neutral/lower-division/cancellations deterministically, and separates structural/not-known/source/resolution/pipeline missingness.",
    "Approved matrices are content-hashed, split-blind, reproducible from pinned raw/entity/state versions, and cannot pass on successful file creation alone.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-016. Governance traceability gate: POST-SUBTASK-051. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-048.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/pit/matrix_gate_decision.json",
    "artifacts/jira_evidence/POST-SUBTASK-048.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-045;POST-SUBTASK-046;POST-SUBTASK-047",
  "blocks": [
    "POST-EPIC-006",
    "POST-EPIC-007",
    "POST-STORY-017",
    "POST-STORY-018",
    "POST-STORY-021",
    "POST-STORY-023",
    "POST-STORY-027",
    "POST-SUBTASK-049",
    "POST-SUBTASK-050",
    "POST-SUBTASK-051",
    "POST-SUBTASK-052",
    "POST-SUBTASK-053",
    "POST-SUBTASK-054",
    "POST-SUBTASK-061",
    "POST-SUBTASK-062",
    "POST-SUBTASK-063",
    "POST-SUBTASK-067",
    "POST-SUBTASK-068",
    "POST-SUBTASK-069",
    "POST-SUBTASK-079",
    "POST-SUBTASK-080",
    "POST-SUBTASK-081"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-048_approve_or_block_immutable_matrix_versions_for_feature_model_experimentation.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-016",
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
    "The atomic scope in POST-SUBTASK-048 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-016."
  ],
  "dependencies": [
    "POST-SUBTASK-045",
    "POST-SUBTASK-046",
    "POST-SUBTASK-047"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 1,
    "adr_ids": 8,
    "gap_ids": 1,
    "requirement_ids": 14,
    "risk_ids": 7
  },
  "effective_traceability_total": 31,
  "end_to_end_validation": "A pinned cutoff reconstructs the exact state and matrix row that was legitimately knowable before a historical game. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-006, POST-EPIC-007, POST-STORY-017, POST-STORY-018, POST-STORY-021, POST-STORY-023, POST-STORY-027, POST-SUBTASK-049, POST-SUBTASK-050, POST-SUBTASK-051, POST-SUBTASK-052, POST-SUBTASK-053….",
  "epic_id": "POST-EPIC-005",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-048.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/pit/matrix_gate_decision.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_temporal_governance.py",
    "tests/test_w24_readiness.py",
    "src/aggie_analytics/temporal/eligibility.py",
    "src/aggie_analytics/temporal/state.py",
    "docs/18_POINT_IN_TIME_DATA_ARCHITECTURE.md",
    "docs/19_ASOF_QUERY_AND_CUTOFF_CONTRACT.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_temporal_governance.py",
    "tests/test_w24_readiness.py",
    "src/aggie_analytics/temporal/eligibility.py",
    "src/aggie_analytics/temporal/state.py",
    "docs/18_POINT_IN_TIME_DATA_ARCHITECTURE.md",
    "docs/19_ASOF_QUERY_AND_CUTOFF_CONTRACT.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-048_approve_or_block_immutable_matrix_versions_for_feature_model_experimentation.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-051",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100352,
  "in_scope": [
    "Perform the exact action: Approve or block immutable matrix versions for feature/model experimentation.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-045`, `POST-SUBTASK-046`, `POST-SUBTASK-047`.",
    "Demonstrate with saved evidence: State rows retain canonical identity, effective/known-at time, source evidence, and version; corrections append and future observations do not alter prior as-of reads.",
    "Demonstrate with saved evidence: Each game/cutoff row uses only eligible state, handles home/away/neutral/lower-division/cancellations deterministically, and separates structural/not-known/source/resolution/pipeline missingness.",
    "Demonstrate with saved evidence: Approved matrices are content-hashed, split-blind, reproducible from pinned raw/entity/state versions, and cannot pass on successful file creation alone.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `artifacts/pit/matrix_gate_decision.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-398",
  "labels": [
    "actionable",
    "core-release",
    "pit",
    "post-wave",
    "protected-gate",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-048",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Approve or block immutable matrix versions for feature/model experimentation",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24538",
    "jira_updated_at": "2026-08-09T23:24:04.078-0500",
    "last_synced_at": "2026-08-10T04:24:34.496382+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\BAT-516-openai-foundation-complete\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Materialize append-only game, team, conference, venue, player, roster, staff, availability, weather, market, and context as-of state; Build national pregame matrices at configured cutoffs with row/cell lineage, missingness class, fallback, and pinned versions.",
    "Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-016",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-045 complete at required maturity",
    "Dependency POST-SUBTASK-046 complete at required maturity",
    "Dependency POST-SUBTASK-047 complete at required maturity"
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
    "tests/test_temporal_governance.py",
    "tests/test_w24_readiness.py",
    "src/aggie_analytics/temporal/eligibility.py",
    "src/aggie_analytics/temporal/state.py",
    "docs/18_POINT_IN_TIME_DATA_ARCHITECTURE.md",
    "docs/19_ASOF_QUERY_AND_CUTOFF_CONTRACT.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/pit/matrix_gate_decision.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-048; retain command, exit code, and relevant output.",
      "path": "tests/test_temporal_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "CHRONOLOGICAL_REPLAY",
      "expectation": "Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.",
      "path": "artifacts/pit/matrix_gate_decision.json",
      "validation_class": "CHRONOLOGICAL_REPLAY"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/pit/matrix_gate_decision.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/pit/matrix_gate_decision.json",
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
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-048.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that state rows retain canonical identity, effective/known-at time, source evidence, and version; corrections append and future observations do not alter prior as-of reads.",
    "Acceptance failure: the evidence cannot demonstrate that each game/cutoff row uses only eligible state, handles home/away/neutral/lower-division/cancellations deterministically, and separates structural/not-known/source/resolution/pipeline missingness.",
    "Acceptance failure: the evidence cannot demonstrate that approved matrices are content-hashed, split-blind, reproducible from pinned raw/entity/state versions, and cannot pass on successful file creation alone.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-016 (Append-only as-of state and pregame matrices): Approve or block immutable matrix versions for feature/model experimentation. Consume only verified prerequisite outputs from `POST-SUBTASK-045`, `POST-SUBTASK-046`, `POST-SUBTASK-047`. Produce `artifacts/pit/matrix_gate_decision.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
  "source_ids": [
    "GAP-005",
    "GAP-006",
    "HANDOFF-004"
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
    "SRCREF-01568"
  ],
  "specificity_fingerprint": "87532d338f99289864fd327a5bb4870fcc8a6612a02f1aaeaad3a9f5ff06dbfd",
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
    "SRCREF-01568"
  ],
  "title": "[POST-SUBTASK-048] Approve or block immutable matrix versions for feature/model experimentation",
  "traceability_inherited_from": [
    "POST-SUBTASK-051"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "CHRONOLOGICAL_REPLAY",
    "END_TO_END",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-016: Append-only as-of state and pregame matrices.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-048.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Approve or block immutable matrix versions for feature/model experimentation

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-016: Append-only as-of state and pregame matrices.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-016 (Append-only as-of state and pregame matrices): Approve or block immutable matrix versions for feature/model experimentation. Consume only verified prerequisite outputs from `POST-SUBTASK-045`, `POST-SUBTASK-046`, `POST-SUBTASK-047`. Produce `artifacts/pit/matrix_gate_decision.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Approve or block immutable matrix versions for feature/model experimentation.
- Consume only verified prerequisite outputs from `POST-SUBTASK-045`, `POST-SUBTASK-046`, `POST-SUBTASK-047`.
- Demonstrate with saved evidence: State rows retain canonical identity, effective/known-at time, source evidence, and version; corrections append and future observations do not alter prior as-of reads.
- Demonstrate with saved evidence: Each game/cutoff row uses only eligible state, handles home/away/neutral/lower-division/cancellations deterministically, and separates structural/not-known/source/resolution/pipeline missingness.
- Demonstrate with saved evidence: Approved matrices are content-hashed, split-blind, reproducible from pinned raw/entity/state versions, and cannot pass on successful file creation alone.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/pit/matrix_gate_decision.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Materialize append-only game, team, conference, venue, player, roster, staff, availability, weather, market, and context as-of state; Build national pregame matrices at configured cutoffs with row/cell lineage, missingness class, fallback, and pinned versions.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-045 complete at required maturity
- Dependency POST-SUBTASK-046 complete at required maturity
- Dependency POST-SUBTASK-047 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-045
- POST-SUBTASK-046
- POST-SUBTASK-047

## Blocks

- POST-EPIC-006
- POST-EPIC-007
- POST-STORY-017
- POST-STORY-018
- POST-STORY-021
- POST-STORY-023
- POST-STORY-027
- POST-SUBTASK-049
- POST-SUBTASK-050
- POST-SUBTASK-051
- POST-SUBTASK-052
- POST-SUBTASK-053
- POST-SUBTASK-054
- POST-SUBTASK-061
- POST-SUBTASK-062
- POST-SUBTASK-063
- POST-SUBTASK-067
- POST-SUBTASK-068
- POST-SUBTASK-069
- POST-SUBTASK-079
- POST-SUBTASK-080
- POST-SUBTASK-081

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_temporal_governance.py
- tests/test_w24_readiness.py
- src/aggie_analytics/temporal/eligibility.py
- src/aggie_analytics/temporal/state.py
- docs/18_POINT_IN_TIME_DATA_ARCHITECTURE.md
- docs/19_ASOF_QUERY_AND_CUTOFF_CONTRACT.md

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

- artifacts/pit/matrix_gate_decision.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-051`
- Inherited from: POST-SUBTASK-051
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 1, "adr_ids": 8, "gap_ids": 1, "requirement_ids": 14, "risk_ids": 7}`

## Acceptance Criteria

1. State rows retain canonical identity, effective/known-at time, source evidence, and version; corrections append and future observations do not alter prior as-of reads.
2. Each game/cutoff row uses only eligible state, handles home/away/neutral/lower-division/cancellations deterministically, and separates structural/not-known/source/resolution/pipeline missingness.
3. Approved matrices are content-hashed, split-blind, reproducible from pinned raw/entity/state versions, and cannot pass on successful file creation alone.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. The atomic scope in POST-SUBTASK-048 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-016.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_temporal_governance.py` — Run as a regression check after completing POST-SUBTASK-048; retain command, exit code, and relevant output.
- **CHRONOLOGICAL_REPLAY** / `CHRONOLOGICAL_REPLAY` — `artifacts/pit/matrix_gate_decision.json` — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/pit/matrix_gate_decision.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **END_TO_END** / `END_TO_END` — `artifacts/pit/matrix_gate_decision.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/pit/matrix_gate_decision.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
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
  "downstream_consumer": "POST-STORY-016",
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

A pinned cutoff reconstructs the exact state and matrix row that was legitimately knowable before a historical game. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-006, POST-EPIC-007, POST-STORY-017, POST-STORY-018, POST-STORY-021, POST-STORY-023, POST-STORY-027, POST-SUBTASK-049, POST-SUBTASK-050, POST-SUBTASK-051, POST-SUBTASK-052, POST-SUBTASK-053….

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-048.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that state rows retain canonical identity, effective/known-at time, source evidence, and version; corrections append and future observations do not alter prior as-of reads.
- Acceptance failure: the evidence cannot demonstrate that each game/cutoff row uses only eligible state, handles home/away/neutral/lower-division/cancellations deterministically, and separates structural/not-known/source/resolution/pipeline missingness.
- Acceptance failure: the evidence cannot demonstrate that approved matrices are content-hashed, split-blind, reproducible from pinned raw/entity/state versions, and cannot pass on successful file creation alone.
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
- SRCREF-01568

## AI Context Notes

- Canonical parent Story: POST-STORY-016. Governance traceability gate: POST-SUBTASK-051. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-048.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

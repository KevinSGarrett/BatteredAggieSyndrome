<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-057_validate_feature_values_home_away_orientation_future_append_invariance_lineage_m.json -->
# POST-SUBTASK-057 — [POST-SUBTASK-057] Validate feature values, home/away orientation, future-append invariance, lineage, missingness, and candidate eligibility

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Rolling/expanding/opponent-adjusted statistics fit only on eligible prior history, declare shrinkage/minimum history, and use visible uncertainty for early-season/lower-division cold starts.",
    "Advanced features use versioned PIT state, separate market-free/market-aware lanes, preserve availability uncertainty, and keep thin/unsupported domains isolated.",
    "Representative values reconcile to source/as-of evidence; repeated build, swap, future append, NaN/inf, and unsupported-domain tests pass before experiments.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-019. Governance traceability gate: POST-SUBTASK-060. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-057.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/features/feature_materialization_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-057.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-051;POST-SUBTASK-054;POST-SUBTASK-055;POST-SUBTASK-056",
  "blocks": [
    "POST-STORY-020",
    "POST-SUBTASK-058",
    "POST-SUBTASK-059",
    "POST-SUBTASK-060"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-057_validate_feature_values_home_away_orientation_future_append_invariance_lineage_m.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-019",
    "governance_traceability_gate": "POST-SUBTASK-060",
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
  "component": "feature-engineering",
  "components_expected_to_be_touched": [
    "feature-engineering",
    "features"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-057 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-019."
  ],
  "dependencies": [
    "POST-SUBTASK-051",
    "POST-SUBTASK-054",
    "POST-SUBTASK-055",
    "POST-SUBTASK-056"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 5,
    "adr_ids": 12,
    "gap_ids": 1,
    "requirement_ids": 50,
    "risk_ids": 19
  },
  "effective_traceability_total": 87,
  "end_to_end_validation": "Pinned real PIT matrices deterministically produce foundation and advanced feature candidates with explicit uncertainty and no future information. The gate decision must explicitly reevaluate downstream issues: POST-STORY-020, POST-SUBTASK-058, POST-SUBTASK-059, POST-SUBTASK-060.",
  "epic_id": "POST-EPIC-006",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-057.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/features/feature_materialization_gate.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/features/factory.py",
    "src/aggie_analytics/features/lifecycle.py",
    "src/aggie_analytics/features/screening.py",
    "docs/22_RAW_FEATURE_REGISTRY_ARCHITECTURE.md",
    "docs/25_FEATURE_ENGINEERING_ARCHITECTURE.md",
    "docs/26_FEATURE_SCREENING_AND_SELECTION.md",
    "docs/27_FEATURE_LIFECYCLE_GOVERNANCE.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "src/aggie_analytics/features/factory.py",
    "src/aggie_analytics/features/lifecycle.py",
    "src/aggie_analytics/features/screening.py",
    "docs/22_RAW_FEATURE_REGISTRY_ARCHITECTURE.md",
    "docs/25_FEATURE_ENGINEERING_ARCHITECTURE.md",
    "docs/26_FEATURE_SCREENING_AND_SELECTION.md",
    "docs/27_FEATURE_LIFECYCLE_GOVERNANCE.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-057_validate_feature_values_home_away_orientation_future_append_invariance_lineage_m.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-060",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100361,
  "in_scope": [
    "Perform the exact action: Validate feature values, home/away orientation, future-append invariance, lineage, missingness, and candidate eligibility.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-054`, `POST-SUBTASK-055`, `POST-SUBTASK-056`.",
    "Demonstrate with saved evidence: Rolling/expanding/opponent-adjusted statistics fit only on eligible prior history, declare shrinkage/minimum history, and use visible uncertainty for early-season/lower-division cold starts.",
    "Demonstrate with saved evidence: Advanced features use versioned PIT state, separate market-free/market-aware lanes, preserve availability uncertainty, and keep thin/unsupported domains isolated.",
    "Demonstrate with saved evidence: Representative values reconcile to source/as-of evidence; repeated build, swap, future append, NaN/inf, and unsupported-domain tests pass before experiments.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `artifacts/features/feature_materialization_gate.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-407",
  "labels": [
    "actionable",
    "core-release",
    "features",
    "post-wave",
    "protected-gate",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-057",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Validate feature values, home/away orientation, future-append invariance, lineage, missingness, and candidate eligibility",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24547",
    "jira_updated_at": "2026-08-09T23:24:05.084-0500",
    "last_synced_at": "2026-08-10T04:24:34.496382+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\BAT-516-openai-foundation-complete\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Materialize team/opponent form, efficiency, scoring, schedule strength, recency, continuity, rest, travel, venue, sequence, cold-start, and lower-division prior features; Materialize supported player value/depth/replacement/availability, recruiting/transfer, coaching, weather, market, resource, officiating, and game-mechanics candidates.",
    "Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-019",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-051 complete at required maturity",
    "Dependency POST-SUBTASK-054 complete at required maturity",
    "Dependency POST-SUBTASK-055 complete at required maturity",
    "Dependency POST-SUBTASK-056 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02033",
    "SRCREF-02034",
    "SRCREF-02035",
    "SRCREF-02036"
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
    "src/aggie_analytics/features/factory.py",
    "src/aggie_analytics/features/lifecycle.py",
    "src/aggie_analytics/features/screening.py",
    "docs/22_RAW_FEATURE_REGISTRY_ARCHITECTURE.md",
    "docs/25_FEATURE_ENGINEERING_ARCHITECTURE.md",
    "docs/26_FEATURE_SCREENING_AND_SELECTION.md",
    "docs/27_FEATURE_LIFECYCLE_GOVERNANCE.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/features/feature_materialization_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-057; retain command, exit code, and relevant output.",
      "path": "tests/test_feature_registry_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-057; retain command, exit code, and relevant output.",
      "path": "tests/test_feature_lifecycle_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-057; retain command, exit code, and relevant output.",
      "path": "tests/test_feature_tournament_full.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "CHRONOLOGICAL_REPLAY",
      "expectation": "Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.",
      "path": "artifacts/features/feature_materialization_gate.json",
      "validation_class": "CHRONOLOGICAL_REPLAY"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/features/feature_materialization_gate.json",
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
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-057.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that rolling/expanding/opponent-adjusted statistics fit only on eligible prior history, declare shrinkage/minimum history, and use visible uncertainty for early-season/lower-division cold starts.",
    "Acceptance failure: the evidence cannot demonstrate that advanced features use versioned PIT state, separate market-free/market-aware lanes, preserve availability uncertainty, and keep thin/unsupported domains isolated.",
    "Acceptance failure: the evidence cannot demonstrate that representative values reconcile to source/as-of evidence; repeated build, swap, future append, NaN/inf, and unsupported-domain tests pass before experiments.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-019 (Foundation and advanced feature materialization): Validate feature values, home/away orientation, future-append invariance, lineage, missingness, and candidate eligibility. Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-054`, `POST-SUBTASK-055`, `POST-SUBTASK-056`. Produce `artifacts/features/feature_materialization_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
  "source_ids": [
    "GAP-006",
    "GAP-007",
    "HANDOFF-005",
    "HANDOFF-008"
  ],
  "source_refs": [
    "SRCREF-02033",
    "SRCREF-02034",
    "SRCREF-02035",
    "SRCREF-02036",
    "SRCREF-02037",
    "SRCREF-02038",
    "SRCREF-02039",
    "SRCREF-02040",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01891",
    "SRCREF-01569",
    "SRCREF-01894",
    "SRCREF-01568"
  ],
  "specificity_fingerprint": "b69954e0cec64c2f0ddec20200a0c530ef21b6bc546f3a3ada2c3624f319e3fa",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
  ],
  "supporting_source_refs": [
    "SRCREF-02037",
    "SRCREF-02038",
    "SRCREF-02039",
    "SRCREF-02040",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01891",
    "SRCREF-01569",
    "SRCREF-01894",
    "SRCREF-01568"
  ],
  "title": "[POST-SUBTASK-057] Validate feature values, home/away orientation, future-append invariance, lineage, missingness, and candidate eligibility",
  "traceability_inherited_from": [
    "POST-SUBTASK-060"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "CHRONOLOGICAL_REPLAY",
    "END_TO_END",
    "REGRESSION",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-019: Foundation and advanced feature materialization.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-057.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Validate feature values, home/away orientation, future-append invariance, lineage, missingness, and candidate eligibility

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-019: Foundation and advanced feature materialization.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-019 (Foundation and advanced feature materialization): Validate feature values, home/away orientation, future-append invariance, lineage, missingness, and candidate eligibility. Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-054`, `POST-SUBTASK-055`, `POST-SUBTASK-056`. Produce `artifacts/features/feature_materialization_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Validate feature values, home/away orientation, future-append invariance, lineage, missingness, and candidate eligibility.
- Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-054`, `POST-SUBTASK-055`, `POST-SUBTASK-056`.
- Demonstrate with saved evidence: Rolling/expanding/opponent-adjusted statistics fit only on eligible prior history, declare shrinkage/minimum history, and use visible uncertainty for early-season/lower-division cold starts.
- Demonstrate with saved evidence: Advanced features use versioned PIT state, separate market-free/market-aware lanes, preserve availability uncertainty, and keep thin/unsupported domains isolated.
- Demonstrate with saved evidence: Representative values reconcile to source/as-of evidence; repeated build, swap, future append, NaN/inf, and unsupported-domain tests pass before experiments.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/features/feature_materialization_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Materialize team/opponent form, efficiency, scoring, schedule strength, recency, continuity, rest, travel, venue, sequence, cold-start, and lower-division prior features; Materialize supported player value/depth/replacement/availability, recruiting/transfer, coaching, weather, market, resource, officiating, and game-mechanics candidates.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.

## Prerequisites

- Dependency POST-SUBTASK-051 complete at required maturity
- Dependency POST-SUBTASK-054 complete at required maturity
- Dependency POST-SUBTASK-055 complete at required maturity
- Dependency POST-SUBTASK-056 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-051
- POST-SUBTASK-054
- POST-SUBTASK-055
- POST-SUBTASK-056

## Blocks

- POST-STORY-020
- POST-SUBTASK-058
- POST-SUBTASK-059
- POST-SUBTASK-060

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/features/factory.py
- src/aggie_analytics/features/lifecycle.py
- src/aggie_analytics/features/screening.py
- docs/22_RAW_FEATURE_REGISTRY_ARCHITECTURE.md
- docs/25_FEATURE_ENGINEERING_ARCHITECTURE.md
- docs/26_FEATURE_SCREENING_AND_SELECTION.md
- docs/27_FEATURE_LIFECYCLE_GOVERNANCE.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- feature-engineering
- features

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

- artifacts/features/feature_materialization_gate.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-060`
- Inherited from: POST-SUBTASK-060
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 5, "adr_ids": 12, "gap_ids": 1, "requirement_ids": 50, "risk_ids": 19}`

## Acceptance Criteria

1. Rolling/expanding/opponent-adjusted statistics fit only on eligible prior history, declare shrinkage/minimum history, and use visible uncertainty for early-season/lower-division cold starts.
2. Advanced features use versioned PIT state, separate market-free/market-aware lanes, preserve availability uncertainty, and keep thin/unsupported domains isolated.
3. Representative values reconcile to source/as-of evidence; repeated build, swap, future append, NaN/inf, and unsupported-domain tests pass before experiments.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. The atomic scope in POST-SUBTASK-057 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-019.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_feature_registry_governance.py` — Run as a regression check after completing POST-SUBTASK-057; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_feature_lifecycle_governance.py` — Run as a regression check after completing POST-SUBTASK-057; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_feature_tournament_full.py` — Run as a regression check after completing POST-SUBTASK-057; retain command, exit code, and relevant output.
- **CHRONOLOGICAL_REPLAY** / `CHRONOLOGICAL_REPLAY` — `artifacts/features/feature_materialization_gate.json` — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- **END_TO_END** / `END_TO_END` — `artifacts/features/feature_materialization_gate.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/features/feature_materialization_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
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
  "downstream_consumer": "POST-STORY-019",
  "governance_traceability_gate": "POST-SUBTASK-060",
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

Pinned real PIT matrices deterministically produce foundation and advanced feature candidates with explicit uncertainty and no future information. The gate decision must explicitly reevaluate downstream issues: POST-STORY-020, POST-SUBTASK-058, POST-SUBTASK-059, POST-SUBTASK-060.

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-057.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that rolling/expanding/opponent-adjusted statistics fit only on eligible prior history, declare shrinkage/minimum history, and use visible uncertainty for early-season/lower-division cold starts.
- Acceptance failure: the evidence cannot demonstrate that advanced features use versioned PIT state, separate market-free/market-aware lanes, preserve availability uncertainty, and keep thin/unsupported domains isolated.
- Acceptance failure: the evidence cannot demonstrate that representative values reconcile to source/as-of evidence; repeated build, swap, future append, NaN/inf, and unsupported-domain tests pass before experiments.
- Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

## Source References

- SRCREF-02033
- SRCREF-02034
- SRCREF-02035
- SRCREF-02036
- SRCREF-02037
- SRCREF-02038
- SRCREF-02039
- SRCREF-02040
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01891
- SRCREF-01569
- SRCREF-01894
- SRCREF-01568

## AI Context Notes

- Canonical parent Story: POST-STORY-019. Governance traceability gate: POST-SUBTASK-060. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-057.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

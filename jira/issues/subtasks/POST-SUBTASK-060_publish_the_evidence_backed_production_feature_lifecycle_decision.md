<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-060_publish_the_evidence_backed_production_feature_lifecycle_decision.json -->
# POST-SUBTASK-060 — [POST-SUBTASK-060] Publish the evidence-backed production feature lifecycle decision

## Canonical metadata

```json
{
  "acceptance_control_ids": [
    "AC-048",
    "AC-083",
    "AC-085",
    "AC-109",
    "AC-191"
  ],
  "acceptance_criteria": [
    "Every experiment pins matrix/split/registry/code/model/seed identities and compares incremental value, compute cost, missingness, leakage risk, and stability without protected outcomes.",
    "Ablations retain null/negative results and report task/season/regime/A&M/peer/market-lane uncertainty, redundancy, and instability rather than cherry-picking one favorable slice.",
    "Only policy-compliant candidates receive production eligibility; GAP-007 remains open until real protected evidence supports the selected set.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [
    "ADR-045",
    "ADR-112",
    "ADR-113",
    "ADR-127",
    "ADR-138",
    "ADR-162",
    "ADR-174",
    "ADR-184",
    "ADR-228",
    "ADR-278",
    "ADR-279",
    "ADR-319"
  ],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-020. Governance traceability gate: POST-SUBTASK-060. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-060.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "configs/feature_lifecycle_registry.json",
    "artifacts/jira_evidence/POST-SUBTASK-060.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-057;POST-SUBTASK-058;POST-SUBTASK-059",
  "blocks": [
    "POST-EPIC-008",
    "POST-STORY-024",
    "POST-SUBTASK-070",
    "POST-SUBTASK-071",
    "POST-SUBTASK-072"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-060_publish_the_evidence_backed_production_feature_lifecycle_decision.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-020",
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
  "critical_path": true,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-060 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-020."
  ],
  "dependencies": [
    "POST-SUBTASK-057",
    "POST-SUBTASK-058",
    "POST-SUBTASK-059"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 5,
    "adr_ids": 12,
    "gap_ids": 1,
    "requirement_ids": 50,
    "risk_ids": 19
  },
  "effective_traceability_total": 87,
  "end_to_end_validation": "A pinned registry feeds reproducible screening and ablation, yielding task-specific production lifecycle states while preserving bans and negative results. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-008, POST-STORY-024, POST-SUBTASK-070, POST-SUBTASK-071, POST-SUBTASK-072.",
  "epic_id": "POST-EPIC-006",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-060.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "configs/feature_lifecycle_registry.json"
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
    "src/aggie_analytics/features/factory.py",
    "docs/22_RAW_FEATURE_REGISTRY_ARCHITECTURE.md",
    "docs/27_FEATURE_LIFECYCLE_GOVERNANCE.md",
    "docs/28_FEATURE_ABLATION_AND_STABILITY.md",
    "docs/25_FEATURE_ENGINEERING_ARCHITECTURE.md"
  ],
  "files_expected_to_be_touched": [
    "configs/feature_lifecycle_registry.json"
  ],
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
    "src/aggie_analytics/features/factory.py",
    "docs/22_RAW_FEATURE_REGISTRY_ARCHITECTURE.md",
    "docs/27_FEATURE_LIFECYCLE_GOVERNANCE.md",
    "docs/28_FEATURE_ABLATION_AND_STABILITY.md",
    "docs/25_FEATURE_ENGINEERING_ARCHITECTURE.md"
  ],
  "gap_ids": [
    "GAP-004"
  ],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-060_publish_the_evidence_backed_production_feature_lifecycle_decision.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-060",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100364,
  "in_scope": [
    "Perform the exact action: Publish the evidence-backed production feature lifecycle decision.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-057`, `POST-SUBTASK-058`, `POST-SUBTASK-059`.",
    "Demonstrate with saved evidence: Every experiment pins matrix/split/registry/code/model/seed identities and compares incremental value, compute cost, missingness, leakage risk, and stability without protected outcomes.",
    "Demonstrate with saved evidence: Ablations retain null/negative results and report task/season/regime/A&M/peer/market-lane uncertainty, redundancy, and instability rather than cherry-picking one favorable slice.",
    "Demonstrate with saved evidence: Only policy-compliant candidates receive production eligibility; GAP-007 remains open until real protected evidence supports the selected set.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `configs/feature_lifecycle_registry.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-410",
  "labels": [
    "actionable",
    "core-release",
    "features",
    "post-wave",
    "protected-gate",
    "subtask"
  ],
  "last_content_audit": "2026-08-08",
  "local_id": "POST-SUBTASK-060",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Publish the evidence-backed production feature lifecycle decision",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24550",
    "jira_updated_at": "2026-08-09T00:05:18.422-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.",
    "Work assigned to sibling subtasks: Run staged univariate/multivariate screening and bounded feature tournaments on permitted tuning history; Run ablation, interaction, redundancy, missingness sensitivity, regime stability, A&M/peer, and market-lane analyses.",
    "Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-020",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-057 complete at required maturity",
    "Dependency POST-SUBTASK-058 complete at required maturity",
    "Dependency POST-SUBTASK-059 complete at required maturity"
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
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/ADR_INDEX.csv",
    "governance/REQUIREMENTS_INDEX.csv",
    "src/aggie_analytics/features/factory.py",
    "docs/22_RAW_FEATURE_REGISTRY_ARCHITECTURE.md",
    "docs/27_FEATURE_LIFECYCLE_GOVERNANCE.md",
    "docs/28_FEATURE_ABLATION_AND_STABILITY.md",
    "docs/25_FEATURE_ENGINEERING_ARCHITECTURE.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`configs/feature_lifecycle_registry.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-060; retain command, exit code, and relevant output.",
      "path": "tests/test_feature_registry_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-060; retain command, exit code, and relevant output.",
      "path": "tests/test_feature_lifecycle_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-060; retain command, exit code, and relevant output.",
      "path": "tests/test_feature_tournament_full.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "CHRONOLOGICAL_REPLAY",
      "expectation": "Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.",
      "path": "configs/feature_lifecycle_registry.json",
      "validation_class": "CHRONOLOGICAL_REPLAY"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "configs/feature_lifecycle_registry.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "configs/feature_lifecycle_registry.json",
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
    "REQ-045",
    "REQ-051",
    "REQ-063",
    "REQ-065",
    "REQ-067",
    "REQ-068",
    "REQ-130",
    "REQ-156",
    "REQ-191",
    "REQ-199",
    "REQ-287",
    "REQ-292",
    "REQ-306",
    "REQ-307",
    "REQ-313",
    "REQ-330",
    "REQ-331",
    "REQ-332",
    "REQ-333",
    "REQ-334",
    "REQ-338",
    "REQ-339",
    "REQ-341",
    "REQ-342",
    "REQ-343",
    "REQ-344",
    "REQ-346",
    "REQ-354",
    "REQ-356",
    "REQ-357",
    "REQ-361",
    "REQ-362",
    "REQ-415",
    "REQ-441",
    "REQ-444",
    "REQ-450",
    "REQ-454",
    "REQ-455",
    "REQ-457",
    "REQ-461",
    "REQ-545",
    "REQ-606",
    "REQ-641",
    "REQ-642",
    "REQ-645",
    "REQ-647",
    "REQ-703",
    "REQ-704",
    "REQ-705",
    "REQ-743"
  ],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-060.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that every experiment pins matrix/split/registry/code/model/seed identities and compares incremental value, compute cost, missingness, leakage risk, and stability without protected outcomes.",
    "Acceptance failure: the evidence cannot demonstrate that ablations retain null/negative results and report task/season/regime/A&M/peer/market-lane uncertainty, redundancy, and instability rather than cherry-picking one favorable slice.",
    "Acceptance failure: the evidence cannot demonstrate that only policy-compliant candidates receive production eligibility; GAP-007 remains open until real protected evidence supports the selected set.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [
    "RISK-001",
    "RISK-008",
    "RISK-023",
    "RISK-027",
    "RISK-069",
    "RISK-073",
    "RISK-075",
    "RISK-076",
    "RISK-089",
    "RISK-106",
    "RISK-119",
    "RISK-123",
    "RISK-125",
    "RISK-126",
    "RISK-130",
    "RISK-173",
    "RISK-174",
    "RISK-187",
    "RISK-239"
  ],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-020 (Screening, ablation, stability, and promotion): Publish the evidence-backed production feature lifecycle decision. Consume only verified prerequisite outputs from `POST-SUBTASK-057`, `POST-SUBTASK-058`, `POST-SUBTASK-059`. Produce `configs/feature_lifecycle_registry.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
  "source_ids": [
    "GAP-004",
    "GAP-007",
    "HANDOFF-005",
    "ISSUE-007"
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
    "SRCREF-01566",
    "SRCREF-01907",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "specificity_fingerprint": "8912e0d2b36fd06d3ac2c607686a479c28c2ea56d6839a9b32c7866fbb37dc4f",
  "stop_conditions": [
    "Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.",
    "Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.",
    "Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence."
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
    "SRCREF-01566",
    "SRCREF-01907",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "title": "[POST-SUBTASK-060] Publish the evidence-backed production feature lifecycle decision",
  "traceability_inherited_from": [],
  "traceability_resolution": "DIRECT_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "CHRONOLOGICAL_REPLAY",
    "END_TO_END",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-020: Screening, ablation, stability, and promotion.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-060.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Publish the evidence-backed production feature lifecycle decision

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-020: Screening, ablation, stability, and promotion.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-020 (Screening, ablation, stability, and promotion): Publish the evidence-backed production feature lifecycle decision. Consume only verified prerequisite outputs from `POST-SUBTASK-057`, `POST-SUBTASK-058`, `POST-SUBTASK-059`. Produce `configs/feature_lifecycle_registry.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Publish the evidence-backed production feature lifecycle decision.
- Consume only verified prerequisite outputs from `POST-SUBTASK-057`, `POST-SUBTASK-058`, `POST-SUBTASK-059`.
- Demonstrate with saved evidence: Every experiment pins matrix/split/registry/code/model/seed identities and compares incremental value, compute cost, missingness, leakage risk, and stability without protected outcomes.
- Demonstrate with saved evidence: Ablations retain null/negative results and report task/season/regime/A&M/peer/market-lane uncertainty, redundancy, and instability rather than cherry-picking one favorable slice.
- Demonstrate with saved evidence: Only policy-compliant candidates receive production eligibility; GAP-007 remains open until real protected evidence supports the selected set.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `configs/feature_lifecycle_registry.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Run staged univariate/multivariate screening and bounded feature tournaments on permitted tuning history; Run ablation, interaction, redundancy, missingness sensitivity, regime stability, A&M/peer, and market-lane analyses.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-057 complete at required maturity
- Dependency POST-SUBTASK-058 complete at required maturity
- Dependency POST-SUBTASK-059 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-057
- POST-SUBTASK-058
- POST-SUBTASK-059

## Blocks

- POST-EPIC-008
- POST-STORY-024
- POST-SUBTASK-070
- POST-SUBTASK-071
- POST-SUBTASK-072

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
- src/aggie_analytics/features/factory.py
- docs/22_RAW_FEATURE_REGISTRY_ARCHITECTURE.md
- docs/27_FEATURE_LIFECYCLE_GOVERNANCE.md
- docs/28_FEATURE_ABLATION_AND_STABILITY.md
- docs/25_FEATURE_ENGINEERING_ARCHITECTURE.md

## Files Expected To Be Modified

- configs/feature_lifecycle_registry.json

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

- configs/feature_lifecycle_registry.json

## Direct Requirements

- REQ-045
- REQ-051
- REQ-063
- REQ-065
- REQ-067
- REQ-068
- REQ-130
- REQ-156
- REQ-191
- REQ-199
- REQ-287
- REQ-292
- REQ-306
- REQ-307
- REQ-313
- REQ-330
- REQ-331
- REQ-332
- REQ-333
- REQ-334
- REQ-338
- REQ-339
- REQ-341
- REQ-342
- REQ-343
- REQ-344
- REQ-346
- REQ-354
- REQ-356
- REQ-357
- REQ-361
- REQ-362
- REQ-415
- REQ-441
- REQ-444
- REQ-450
- REQ-454
- REQ-455
- REQ-457
- REQ-461
- REQ-545
- REQ-606
- REQ-641
- REQ-642
- REQ-645
- REQ-647
- REQ-703
- REQ-704
- REQ-705
- REQ-743

## Direct Acceptance Controls

- AC-048
- AC-083
- AC-085
- AC-109
- AC-191

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-060`
- Inherited from: None
- Resolution: `DIRECT_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 5, "adr_ids": 12, "gap_ids": 1, "requirement_ids": 50, "risk_ids": 19}`

## Acceptance Criteria

1. Every experiment pins matrix/split/registry/code/model/seed identities and compares incremental value, compute cost, missingness, leakage risk, and stability without protected outcomes.
2. Ablations retain null/negative results and report task/season/regime/A&M/peer/market-lane uncertainty, redundancy, and instability rather than cherry-picking one favorable slice.
3. Only policy-compliant candidates receive production eligibility; GAP-007 remains open until real protected evidence supports the selected set.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. The atomic scope in POST-SUBTASK-060 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-020.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_feature_registry_governance.py` — Run as a regression check after completing POST-SUBTASK-060; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_feature_lifecycle_governance.py` — Run as a regression check after completing POST-SUBTASK-060; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_feature_tournament_full.py` — Run as a regression check after completing POST-SUBTASK-060; retain command, exit code, and relevant output.
- **CHRONOLOGICAL_REPLAY** / `CHRONOLOGICAL_REPLAY` — `configs/feature_lifecycle_registry.json` — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- **SCIENTIFIC** / `SCIENTIFIC` — `configs/feature_lifecycle_registry.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **END_TO_END** / `END_TO_END` — `configs/feature_lifecycle_registry.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `configs/feature_lifecycle_registry.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
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
  "downstream_consumer": "POST-STORY-020",
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

A pinned registry feeds reproducible screening and ablation, yielding task-specific production lifecycle states while preserving bans and negative results. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-008, POST-STORY-024, POST-SUBTASK-070, POST-SUBTASK-071, POST-SUBTASK-072.

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-060.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that every experiment pins matrix/split/registry/code/model/seed identities and compares incremental value, compute cost, missingness, leakage risk, and stability without protected outcomes.
- Acceptance failure: the evidence cannot demonstrate that ablations retain null/negative results and report task/season/regime/A&M/peer/market-lane uncertainty, redundancy, and instability rather than cherry-picking one favorable slice.
- Acceptance failure: the evidence cannot demonstrate that only policy-compliant candidates receive production eligibility; GAP-007 remains open until real protected evidence supports the selected set.
- Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Stop Conditions

- Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.
- Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.
- Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence.

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
- SRCREF-01566
- SRCREF-01907
- SRCREF-02116
- SRCREF-02117
- SRCREF-02118

## AI Context Notes

- Canonical parent Story: POST-STORY-020. Governance traceability gate: POST-SUBTASK-060. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-060.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

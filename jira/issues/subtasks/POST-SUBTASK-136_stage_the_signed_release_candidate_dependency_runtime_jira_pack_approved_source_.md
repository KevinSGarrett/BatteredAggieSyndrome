<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-136_stage_the_signed_release_candidate_dependency_runtime_jira_pack_approved_source_.json -->
# POST-SUBTASK-136 — [POST-SUBTASK-136] Stage the signed release candidate, dependency/runtime, Jira pack, private-research source configuration, and clean external roots

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "The stage pins repository/dependencies/Jira/source-rights/schema/data/entity/PIT/feature/model/product/runbook identities, keeps credentials external, enforces restrictions, and fails on dirty protected state or blockers.",
    "The declared output `artifacts/release/release_candidate_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-046. Governance traceability gate: POST-SUBTASK-141. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-136.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/release/release_candidate_manifest.json",
    "artifacts/jira_evidence/POST-SUBTASK-136.json"
  ],
  "blocked_reason": "AUTHORITATIVE_TARGET_HOST_AND_PRODUCTION_SOURCE_ACCESS_REQUIRED",
  "blocks": [
    "POST-SUBTASK-137",
    "POST-SUBTASK-138"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-136_stage_the_signed_release_candidate_dependency_runtime_jira_pack_approved_source_.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "IMPLEMENTED",
    "downstream_consumer": "POST-SUBTASK-137",
    "governance_traceability_gate": "POST-SUBTASK-141",
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
  "component": "release-readiness",
  "components_expected_to_be_touched": [
    "release-readiness",
    "release"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-136 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The output set `artifacts/release/release_candidate_manifest.json` is demonstrably consumable by POST-SUBTASK-137 without manual reconstruction or undocumented state."
  ],
  "dependencies": [
    "POST-SUBTASK-009",
    "POST-SUBTASK-135"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 55,
    "adr_ids": 106,
    "gap_ids": 0,
    "requirement_ids": 149,
    "risk_ids": 116
  },
  "effective_traceability_total": 426,
  "end_to_end_validation": "Validate that `artifacts/release/release_candidate_manifest.json` can be parsed and consumed by `POST-SUBTASK-137` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.",
  "epic_id": "POST-EPIC-015",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-136.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "IMPLEMENTED",
  "expected_outputs": [
    "artifacts/release/release_candidate_manifest.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "docs/final/FINAL_RISK_REGISTER.csv",
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "tests/test_w24_readiness.py",
    "tests/test_w25_final_handoff.py",
    "docs/111_W24_END_TO_END_READINESS_AUDIT.md",
    "docs/readiness/W24_END_TO_END_READINESS.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "docs/final/FINAL_RISK_REGISTER.csv",
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "tests/test_w24_readiness.py",
    "tests/test_w25_final_handoff.py",
    "docs/111_W24_END_TO_END_READINESS_AUDIT.md",
    "docs/readiness/W24_END_TO_END_READINESS.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-136_stage_the_signed_release_candidate_dependency_runtime_jira_pack_approved_source_.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-141",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100440,
  "in_scope": [
    "Perform the exact action: Stage the signed release candidate, dependency/runtime, Jira pack, private-research source configuration, and clean external roots.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-135`.",
    "Demonstrate with saved evidence: The stage pins repository/dependencies/Jira/source-rights/schema/data/entity/PIT/feature/model/product/runbook identities, keeps credentials external, enforces restrictions, and fails on dirty protected state or blockers.",
    "Demonstrate with saved evidence: The declared output `artifacts/release/release_candidate_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "Produce, validate, content-hash, and register `artifacts/release/release_candidate_manifest.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-486",
  "labels": [
    "actionable",
    "core-release",
    "external-blocker",
    "post-wave",
    "protected-gate",
    "release",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-136",
  "maturity_before": "DESIGN_ONLY",
  "objective": "Stage the signed release candidate, dependency/runtime, Jira pack, private-research source configuration, and clean external roots",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24626",
    "jira_updated_at": "2026-08-09T23:24:13.316-0500",
    "last_synced_at": "2026-08-11T07:25:49.170544+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\POST-SUBTASK-178-wmt-known-at\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Execute quality-valid source acquisition through immutable raw, entities, PIT, features, champion/no-champion handling, predictions, publication, API, and dashboard on representative real weekly data; Validate outputs, lineage, protected decisions, rollback, clean re-execution, target performance/resources/freshness, and all release-blocking controls.",
    "Reintroducing a license/terms/redistribution gate for private acquisition or training, or publishing raw third-party payloads without a separate future review.",
    "Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.",
    "Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.",
    "Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-046",
  "phase": "PHASE-5",
  "prerequisites": [
    "Dependency POST-SUBTASK-009 complete at required maturity",
    "Dependency POST-SUBTASK-135 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02099",
    "SRCREF-02100",
    "SRCREF-02101",
    "SRCREF-02102"
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
    "docs/final/FINAL_RISK_REGISTER.csv",
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "tests/test_w24_readiness.py",
    "tests/test_w25_final_handoff.py",
    "docs/111_W24_END_TO_END_READINESS_AUDIT.md",
    "docs/readiness/W24_END_TO_END_READINESS.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/release/release_candidate_manifest.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Nonblocking source-policy metadata recording provider/terms version, access purpose, retention, model-training use, publication boundary, redistribution metadata, source URL, acquisition time, and private-research allow decision.",
    "Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts.",
    "Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.",
    "PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-136; retain command, exit code, and relevant output.",
      "path": "tests/test_w24_readiness.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-136; retain command, exit code, and relevant output.",
      "path": "tools/validate_w24_readiness.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "BENCHMARK",
      "expectation": "Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.",
      "path": "artifacts/release/release_candidate_manifest.json",
      "validation_class": "BENCHMARK"
    },
    {
      "classification": "CHRONOLOGICAL_REPLAY",
      "expectation": "Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.",
      "path": "artifacts/release/release_candidate_manifest.json",
      "validation_class": "CHRONOLOGICAL_REPLAY"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/release/release_candidate_manifest.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "SECURITY",
      "expectation": "Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.",
      "path": "artifacts/release/release_candidate_manifest.json",
      "validation_class": "SECURITY"
    },
    {
      "classification": "OPERATIONS",
      "expectation": "Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.",
      "path": "artifacts/release/release_candidate_manifest.json",
      "validation_class": "OPERATIONS"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/release/release_candidate_manifest.json",
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
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-136.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that the stage pins repository/dependencies/Jira/source-rights/schema/data/entity/PIT/feature/model/product/runbook identities, keeps credentials external, enforces restrictions, and fails on dirty protected state or blockers.",
    "Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/release/release_candidate_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "External blocker remains unresolved: AUTHORITATIVE_TARGET_HOST_AND_PRODUCTION_SOURCE_ACCESS_REQUIRED."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 1 of 3 step in Story POST-STORY-046 (Clean-target real-data release candidate): Stage the signed release candidate, dependency/runtime, Jira pack, private-research source configuration, and clean external roots. Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-135`. Produce `artifacts/release/release_candidate_manifest.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-137.",
  "source_ids": [
    "AC-038",
    "GAP-001",
    "GAP-012",
    "HANDOFF-013",
    "HANDOFF-014"
  ],
  "source_refs": [
    "SRCREF-02099",
    "SRCREF-02100",
    "SRCREF-02101",
    "SRCREF-02102",
    "SRCREF-02103",
    "SRCREF-02104",
    "SRCREF-02105",
    "SRCREF-02106",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01899",
    "SRCREF-01900",
    "SRCREF-01563",
    "SRCREF-01574",
    "SRCREF-01017"
  ],
  "specificity_fingerprint": "604dbdfddadfd5f2ca82ffef65ca00400fc72a95cf2a9f1c8b97c06d1a12997e",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
  ],
  "supporting_source_refs": [
    "SRCREF-02103",
    "SRCREF-02104",
    "SRCREF-02105",
    "SRCREF-02106",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01899",
    "SRCREF-01900",
    "SRCREF-01563",
    "SRCREF-01574",
    "SRCREF-01017"
  ],
  "title": "[POST-SUBTASK-136] Stage the signed release candidate, dependency/runtime, Jira pack, private-research source configuration, and clean external roots",
  "traceability_inherited_from": [
    "POST-SUBTASK-141"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "Provide and verify external condition: AUTHORITATIVE_TARGET_HOST_AND_PRODUCTION_SOURCE_ACCESS_REQUIRED",
  "validation_classes": [
    "BENCHMARK",
    "CHRONOLOGICAL_REPLAY",
    "END_TO_END",
    "OPERATIONS",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC",
    "SECURITY"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-046: Clean-target real-data release candidate.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-136.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Stage the signed release candidate, dependency/runtime, Jira pack, private-research source configuration, and clean external roots

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-046: Clean-target real-data release candidate.

## Scope

Execute the atomic 1 of 3 step in Story POST-STORY-046 (Clean-target real-data release candidate): Stage the signed release candidate, dependency/runtime, Jira pack, private-research source configuration, and clean external roots. Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-135`. Produce `artifacts/release/release_candidate_manifest.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-137.

### Explicit In Scope

- Perform the exact action: Stage the signed release candidate, dependency/runtime, Jira pack, private-research source configuration, and clean external roots.
- Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-135`.
- Demonstrate with saved evidence: The stage pins repository/dependencies/Jira/source-rights/schema/data/entity/PIT/feature/model/product/runbook identities, keeps credentials external, enforces restrictions, and fails on dirty protected state or blockers.
- Demonstrate with saved evidence: The declared output `artifacts/release/release_candidate_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/release/release_candidate_manifest.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Execute quality-valid source acquisition through immutable raw, entities, PIT, features, champion/no-champion handling, predictions, publication, API, and dashboard on representative real weekly data; Validate outputs, lineage, protected decisions, rollback, clean re-execution, target performance/resources/freshness, and all release-blocking controls.
- Reintroducing a license/terms/redistribution gate for private acquisition or training, or publishing raw third-party payloads without a separate future review.
- Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.
- Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-009 complete at required maturity
- Dependency POST-SUBTASK-135 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-009
- POST-SUBTASK-135

## Blocks

- POST-SUBTASK-137
- POST-SUBTASK-138

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- docs/final/FINAL_RISK_REGISTER.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- tests/test_w24_readiness.py
- tests/test_w25_final_handoff.py
- docs/111_W24_END_TO_END_READINESS_AUDIT.md
- docs/readiness/W24_END_TO_END_READINESS.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- release-readiness
- release

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

- artifacts/release/release_candidate_manifest.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-141`
- Inherited from: POST-SUBTASK-141
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 55, "adr_ids": 106, "gap_ids": 0, "requirement_ids": 149, "risk_ids": 116}`

## Acceptance Criteria

1. The stage pins repository/dependencies/Jira/source-rights/schema/data/entity/PIT/feature/model/product/runbook identities, keeps credentials external, enforces restrictions, and fails on dirty protected state or blockers.
2. The declared output `artifacts/release/release_candidate_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Definition of Done

1. The atomic scope in POST-SUBTASK-136 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The output set `artifacts/release/release_candidate_manifest.json` is demonstrably consumable by POST-SUBTASK-137 without manual reconstruction or undocumented state.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w24_readiness.py` — Run as a regression check after completing POST-SUBTASK-136; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_w24_readiness.py` — Run as a regression check after completing POST-SUBTASK-136; retain command, exit code, and relevant output.
- **BENCHMARK** / `BENCHMARK` — `artifacts/release/release_candidate_manifest.json` — Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.
- **CHRONOLOGICAL_REPLAY** / `CHRONOLOGICAL_REPLAY` — `artifacts/release/release_candidate_manifest.json` — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/release/release_candidate_manifest.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **SECURITY** / `SECURITY` — `artifacts/release/release_candidate_manifest.json` — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- **OPERATIONS** / `OPERATIONS` — `artifacts/release/release_candidate_manifest.json` — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- **END_TO_END** / `END_TO_END` — `artifacts/release/release_candidate_manifest.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/release/release_candidate_manifest.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Nonblocking source-policy metadata recording provider/terms version, access purpose, retention, model-training use, publication boundary, redistribution metadata, source URL, acquisition time, and private-research allow decision.
- Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts.
- Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "IMPLEMENTED",
  "downstream_consumer": "POST-SUBTASK-137",
  "governance_traceability_gate": "POST-SUBTASK-141",
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

Validate that `artifacts/release/release_candidate_manifest.json` can be parsed and consumed by `POST-SUBTASK-137` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.

## Expected Maturity After Completion

`IMPLEMENTED`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-136.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that the stage pins repository/dependencies/Jira/source-rights/schema/data/entity/PIT/feature/model/product/runbook identities, keeps credentials external, enforces restrictions, and fails on dirty protected state or blockers.
- Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/release/release_candidate_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- External blocker remains unresolved: AUTHORITATIVE_TARGET_HOST_AND_PRODUCTION_SOURCE_ACCESS_REQUIRED.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

## Source References

- SRCREF-02099
- SRCREF-02100
- SRCREF-02101
- SRCREF-02102
- SRCREF-02103
- SRCREF-02104
- SRCREF-02105
- SRCREF-02106
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01899
- SRCREF-01900
- SRCREF-01563
- SRCREF-01574
- SRCREF-01017

## AI Context Notes

- Canonical parent Story: POST-STORY-046. Governance traceability gate: POST-SUBTASK-141. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-136.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

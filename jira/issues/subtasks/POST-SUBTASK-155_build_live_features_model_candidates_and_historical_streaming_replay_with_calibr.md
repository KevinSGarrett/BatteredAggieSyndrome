<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-155_build_live_features_model_candidates_and_historical_streaming_replay_with_calibr.json -->
# POST-SUBTASK-155 — [POST-SUBTASK-155] Build live features/model candidates and historical streaming replay with calibration/OOD/partial-feed/latency/resource evidence

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Candidates use replayable historical sequences and strict event-time cutoffs, separately define outputs/BAS-related semantics, and measure missing/delayed feed, calibration, OOD, latency, and resources.",
    "The declared output `artifacts/live/live_model_prototype.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-052. Governance traceability gate: POST-SUBTASK-159. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-155.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/live/live_model_prototype.json",
    "artifacts/jira_evidence/POST-SUBTASK-155.json"
  ],
  "blocked_reason": "DEFERRED_OR_CONDITIONAL_BY_FINAL_HANDOFF",
  "blocks": [
    "POST-SUBTASK-156"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-155_build_live_features_model_candidates_and_historical_streaming_replay_with_calibr.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "EMPIRICALLY_VALIDATED",
    "downstream_consumer": "POST-SUBTASK-156",
    "governance_traceability_gate": "POST-SUBTASK-159",
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
  "component": "live-modeling",
  "components_expected_to_be_touched": [
    "live-modeling",
    "live"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-155 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The output set `artifacts/live/live_model_prototype.json` is demonstrably consumable by POST-SUBTASK-156 without manual reconstruction or undocumented state."
  ],
  "dependencies": [
    "POST-SUBTASK-153",
    "POST-SUBTASK-154"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 0,
    "adr_ids": 3,
    "gap_ids": 1,
    "requirement_ids": 1,
    "risk_ids": 0
  },
  "effective_traceability_total": 5,
  "end_to_end_validation": "Validate that `artifacts/live/live_model_prototype.json` can be parsed and consumed by `POST-SUBTASK-156` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.",
  "epic_id": "POST-EPIC-017",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-155.json",
  "evidence_state": "PLANNED",
  "execution_lane": "RESEARCH_LANE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "EMPIRICALLY_VALIDATED",
  "expected_outputs": [
    "artifacts/live/live_model_prototype.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "governance/OPEN_ISSUES.md"
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
    "governance/OPEN_ISSUES.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-155_build_live_features_model_candidates_and_historical_streaming_replay_with_calibr.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-159",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100459,
  "in_scope": [
    "Perform the exact action: Build live features/model candidates and historical streaming replay with calibration/OOD/partial-feed/latency/resource evidence.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-153`, `POST-SUBTASK-154`.",
    "Demonstrate with saved evidence: Candidates use replayable historical sequences and strict event-time cutoffs, separately define outputs/BAS-related semantics, and measure missing/delayed feed, calibration, OOD, latency, and resources.",
    "Demonstrate with saved evidence: The declared output `artifacts/live/live_model_prototype.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "Produce, validate, content-hash, and register `artifacts/live/live_model_prototype.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-505",
  "labels": [
    "actionable",
    "deferred",
    "live",
    "post-wave",
    "research-lane",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-155",
  "maturity_before": "DEFERRED",
  "objective": "Build live features/model candidates and historical streaming replay with calibration/OOD/partial-feed/latency/resource evidence",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24645",
    "jira_updated_at": "2026-08-09T23:24:15.428-0500",
    "last_synced_at": "2026-08-11T06:07:11.607568+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\JIRA-LIVE-CATCHUP-20260811\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Build immutable event-stream snapshots and event-time as-of game-state reconstruction handling duplicates, delay, correction, and sequence; Validate event-time integrity, replay determinism, latency, failure behavior, and pregame isolation.",
    "Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.",
    "Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.",
    "Treating deferred live/in-game work as admitted production scope or describing it as Wave 26."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-052",
  "phase": "PHASE-5",
  "prerequisites": [
    "Dependency POST-SUBTASK-153 complete at required maturity",
    "Dependency POST-SUBTASK-154 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02112",
    "SRCREF-02113",
    "SRCREF-02114",
    "SRCREF-02115"
  ],
  "priority": "DEFERRED",
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
    "governance/OPEN_ISSUES.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/live/live_model_prototype.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.",
    "PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "BENCHMARK",
      "expectation": "Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.",
      "path": "artifacts/live/live_model_prototype.json",
      "validation_class": "BENCHMARK"
    },
    {
      "classification": "CHRONOLOGICAL_REPLAY",
      "expectation": "Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.",
      "path": "artifacts/live/live_model_prototype.json",
      "validation_class": "CHRONOLOGICAL_REPLAY"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/live/live_model_prototype.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "CALIBRATION",
      "expectation": "Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.",
      "path": "artifacts/live/live_model_prototype.json",
      "validation_class": "CALIBRATION"
    },
    {
      "classification": "INTEGRATION",
      "expectation": "Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.",
      "path": "artifacts/live/live_model_prototype.json",
      "validation_class": "INTEGRATION"
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
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-155.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that candidates use replayable historical sequences and strict event-time cutoffs, separately define outputs/BAS-related semantics, and measure missing/delayed feed, calibration, OOD, latency, and resources.",
    "Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/live/live_model_prototype.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 2 of 3 step in Story POST-STORY-052 (Isolated event state, features, models, replay, and latency prototype): Build live features/model candidates and historical streaming replay with calibration/OOD/partial-feed/latency/resource evidence. Consume only verified prerequisite outputs from `POST-SUBTASK-153`, `POST-SUBTASK-154`. Produce `artifacts/live/live_model_prototype.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-156.",
  "source_ids": [
    "GAP-014",
    "HANDOFF-014",
    "TASK-169",
    "TASK-170",
    "TASK-171",
    "TASK-172"
  ],
  "source_refs": [
    "SRCREF-02112",
    "SRCREF-02113",
    "SRCREF-02114",
    "SRCREF-02115",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01900",
    "SRCREF-01576",
    "SRCREF-00202",
    "SRCREF-00203",
    "SRCREF-00204",
    "SRCREF-00205"
  ],
  "specificity_fingerprint": "631fa45c57a92458fe1c3f88256a8a95c37dba6745507317cdfc1c722c6c7dd4",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
  ],
  "supporting_source_refs": [
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01900",
    "SRCREF-01576",
    "SRCREF-00202",
    "SRCREF-00203",
    "SRCREF-00204",
    "SRCREF-00205"
  ],
  "title": "[POST-SUBTASK-155] Build live features/model candidates and historical streaming replay with calibration/OOD/partial-feed/latency/resource evidence",
  "traceability_inherited_from": [
    "POST-SUBTASK-159"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "A documented admission/replanning decision must explicitly activate this work after all stated prerequisites pass.",
  "validation_classes": [
    "BENCHMARK",
    "CALIBRATION",
    "CHRONOLOGICAL_REPLAY",
    "INTEGRATION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-052: Isolated event state, features, models, replay, and latency prototype.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-155.md",
  "workflow_state": "DEFERRED"
}
```

## Objective

Build live features/model candidates and historical streaming replay with calibration/OOD/partial-feed/latency/resource evidence

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-052: Isolated event state, features, models, replay, and latency prototype.

## Scope

Execute the atomic 2 of 3 step in Story POST-STORY-052 (Isolated event state, features, models, replay, and latency prototype): Build live features/model candidates and historical streaming replay with calibration/OOD/partial-feed/latency/resource evidence. Consume only verified prerequisite outputs from `POST-SUBTASK-153`, `POST-SUBTASK-154`. Produce `artifacts/live/live_model_prototype.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-156.

### Explicit In Scope

- Perform the exact action: Build live features/model candidates and historical streaming replay with calibration/OOD/partial-feed/latency/resource evidence.
- Consume only verified prerequisite outputs from `POST-SUBTASK-153`, `POST-SUBTASK-154`.
- Demonstrate with saved evidence: Candidates use replayable historical sequences and strict event-time cutoffs, separately define outputs/BAS-related semantics, and measure missing/delayed feed, calibration, OOD, latency, and resources.
- Demonstrate with saved evidence: The declared output `artifacts/live/live_model_prototype.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/live/live_model_prototype.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Build immutable event-stream snapshots and event-time as-of game-state reconstruction handling duplicates, delay, correction, and sequence; Validate event-time integrity, replay determinism, latency, failure behavior, and pregame isolation.
- Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.
- Treating deferred live/in-game work as admitted production scope or describing it as Wave 26.

## Prerequisites

- Dependency POST-SUBTASK-153 complete at required maturity
- Dependency POST-SUBTASK-154 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-153
- POST-SUBTASK-154

## Blocks

- POST-SUBTASK-156

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/IMPLEMENTATION_WBS.csv
- governance/OPEN_ISSUES.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- live-modeling
- live

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

- artifacts/live/live_model_prototype.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-159`
- Inherited from: POST-SUBTASK-159
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 0, "adr_ids": 3, "gap_ids": 1, "requirement_ids": 1, "risk_ids": 0}`

## Acceptance Criteria

1. Candidates use replayable historical sequences and strict event-time cutoffs, separately define outputs/BAS-related semantics, and measure missing/delayed feed, calibration, OOD, latency, and resources.
2. The declared output `artifacts/live/live_model_prototype.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Definition of Done

1. The atomic scope in POST-SUBTASK-155 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The output set `artifacts/live/live_model_prototype.json` is demonstrably consumable by POST-SUBTASK-156 without manual reconstruction or undocumented state.

## Required Tests / Validation

- **BENCHMARK** / `BENCHMARK` — `artifacts/live/live_model_prototype.json` — Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.
- **CHRONOLOGICAL_REPLAY** / `CHRONOLOGICAL_REPLAY` — `artifacts/live/live_model_prototype.json` — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/live/live_model_prototype.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **CALIBRATION** / `CALIBRATION` — `artifacts/live/live_model_prototype.json` — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- **INTEGRATION** / `INTEGRATION` — `artifacts/live/live_model_prototype.json` — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/live/live_model_prototype.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "EMPIRICALLY_VALIDATED",
  "downstream_consumer": "POST-SUBTASK-156",
  "governance_traceability_gate": "POST-SUBTASK-159",
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

Validate that `artifacts/live/live_model_prototype.json` can be parsed and consumed by `POST-SUBTASK-156` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.

## Expected Maturity After Completion

`EMPIRICALLY_VALIDATED`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-155.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that candidates use replayable historical sequences and strict event-time cutoffs, separately define outputs/BAS-related semantics, and measure missing/delayed feed, calibration, OOD, latency, and resources.
- Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/live/live_model_prototype.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

## Source References

- SRCREF-02112
- SRCREF-02113
- SRCREF-02114
- SRCREF-02115
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01900
- SRCREF-01576
- SRCREF-00202
- SRCREF-00203
- SRCREF-00204
- SRCREF-00205

## AI Context Notes

- Canonical parent Story: POST-STORY-052. Governance traceability gate: POST-SUBTASK-159. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-155.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

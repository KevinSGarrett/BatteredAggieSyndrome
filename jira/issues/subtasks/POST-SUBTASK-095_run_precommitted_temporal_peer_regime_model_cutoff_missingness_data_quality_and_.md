<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-095_run_precommitted_temporal_peer_regime_model_cutoff_missingness_data_quality_and_.json -->
# POST-SUBTASK-095 — [POST-SUBTASK-095] Run precommitted temporal, peer, regime, model, cutoff, missingness, data-quality, and specification sensitivity analyses

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "All precommitted sensitivity and negative/sign-changing results are reported, model miscalibration is distinguished from team excess, and no post-hoc choice changes the headline conclusion.",
    "The declared output `artifacts/bas/bas_stability_analysis.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "A scientifically valid null result—no persistent Aggie-specific excess after protected out-of-sample testing—must be preserved, reported, and accepted without changing the precommitted BAS definition, peers, thresholds, or evaluation window.",
    "A null, non-significant, unstable, or directionally unsupported Aggie-specific excess result is accepted and reported without forcing a nonzero BAS effect; general FBS surprise and Texas A&M-specific excess remain distinct."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-032. Governance traceability gate: POST-SUBTASK-096. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-095.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/bas/bas_stability_analysis.json",
    "artifacts/jira_evidence/POST-SUBTASK-095.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-093;POST-SUBTASK-094;POST-SUBTASK-102",
  "blocks": [
    "POST-SUBTASK-096"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-095_run_precommitted_temporal_peer_regime_model_cutoff_missingness_data_quality_and_.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "EMPIRICALLY_VALIDATED",
    "downstream_consumer": "POST-SUBTASK-096",
    "governance_traceability_gate": "POST-SUBTASK-096",
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
  "component": "bas-science",
  "components_expected_to_be_touched": [
    "bas-science",
    "bas"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-095 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The output set `artifacts/bas/bas_stability_analysis.json` is demonstrably consumable by POST-SUBTASK-096 without manual reconstruction or undocumented state."
  ],
  "dependencies": [
    "POST-SUBTASK-093",
    "POST-SUBTASK-094",
    "POST-SUBTASK-102"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 19,
    "adr_ids": 21,
    "gap_ids": 1,
    "requirement_ids": 66,
    "risk_ids": 13
  },
  "effective_traceability_total": 120,
  "end_to_end_validation": "Validate that `artifacts/bas/bas_stability_analysis.json` can be parsed and consumed by `POST-SUBTASK-096` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.",
  "epic_id": "POST-EPIC-010",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-095.json",
  "evidence_state": "PLANNED",
  "execution_lane": "SCIENTIFIC",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "EMPIRICALLY_VALIDATED",
  "expected_outputs": [
    "artifacts/bas/bas_stability_analysis.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_bas_science_governance.py",
    "src/aggie_analytics/bas/labels.py",
    "src/aggie_analytics/bas/runtime.py",
    "docs/45_SCIENTIFIC_BAS_SPECIFICATION.md",
    "docs/48_BAS_COMPONENTS_REGIME_STABILITY_AND_CALIBRATION.md",
    "docs/47_BAS_GENERAL_FBS_AGGIE_EXCESS_AND_PEERS.md",
    "docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_bas_science_governance.py",
    "src/aggie_analytics/bas/labels.py",
    "src/aggie_analytics/bas/runtime.py",
    "docs/45_SCIENTIFIC_BAS_SPECIFICATION.md",
    "docs/48_BAS_COMPONENTS_REGIME_STABILITY_AND_CALIBRATION.md",
    "docs/47_BAS_GENERAL_FBS_AGGIE_EXCESS_AND_PEERS.md",
    "docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-095_run_precommitted_temporal_peer_regime_model_cutoff_missingness_data_quality_and_.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-096",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100399,
  "in_scope": [
    "Perform the exact action: Run precommitted temporal, peer, regime, model, cutoff, missingness, data-quality, and specification sensitivity analyses.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-093`, `POST-SUBTASK-094`, `POST-SUBTASK-102`.",
    "Demonstrate with saved evidence: All precommitted sensitivity and negative/sign-changing results are reported, model miscalibration is distinguished from team excess, and no post-hoc choice changes the headline conclusion.",
    "Demonstrate with saved evidence: The declared output `artifacts/bas/bas_stability_analysis.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.",
    "Produce, validate, content-hash, and register `artifacts/bas/bas_stability_analysis.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-445",
  "labels": [
    "actionable",
    "bas",
    "core-release",
    "post-wave",
    "scientific",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-095",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Run precommitted temporal, peer, regime, model, cutoff, missingness, data-quality, and specification sensitivity analyses",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24585",
    "jira_updated_at": "2026-08-09T23:24:09.186-0500",
    "last_synced_at": "2026-08-11T06:30:01.758065+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\POST-SUBTASK-177-play-drive-preliminary\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Evaluate ≥3/7/14/21 calibration, discrimination, reliability, uncertainty, and national/A&M/peer/regime scorecards on sealed predictions; Publish the final BAS scientific decision and prediction-first product language contract.",
    "Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.",
    "Redefining BAS as generic Texas A&M loss probability or selecting specifications merely to manufacture a nonzero Aggie-specific effect."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-032",
  "phase": "PHASE-3",
  "prerequisites": [
    "Dependency POST-SUBTASK-093 complete at required maturity",
    "Dependency POST-SUBTASK-094 complete at required maturity",
    "Dependency POST-SUBTASK-102 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02064",
    "SRCREF-02065",
    "SRCREF-02066",
    "SRCREF-02067"
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
    "tests/test_bas_science_governance.py",
    "src/aggie_analytics/bas/labels.py",
    "src/aggie_analytics/bas/runtime.py",
    "docs/48_BAS_COMPONENTS_REGIME_STABILITY_AND_CALIBRATION.md",
    "docs/47_BAS_GENERAL_FBS_AGGIE_EXCESS_AND_PEERS.md",
    "docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/bas/bas_stability_analysis.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-095; retain command, exit code, and relevant output.",
      "path": "tests/test_bas_science_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-095; retain command, exit code, and relevant output.",
      "path": "tests/test_w20_model_starter.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-095; retain command, exit code, and relevant output.",
      "path": "tools/validate_bas_science.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "CHRONOLOGICAL_REPLAY",
      "expectation": "Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.",
      "path": "artifacts/bas/bas_stability_analysis.json",
      "validation_class": "CHRONOLOGICAL_REPLAY"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/bas/bas_stability_analysis.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "CALIBRATION",
      "expectation": "Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.",
      "path": "artifacts/bas/bas_stability_analysis.json",
      "validation_class": "CALIBRATION"
    },
    {
      "classification": "INTEGRATION",
      "expectation": "Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.",
      "path": "artifacts/bas/bas_stability_analysis.json",
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
      "path": "NEW_TEST_REQUIRED::POST-SUBTASK-095",
      "validation_class": "NEW_AUTOMATED_TEST_REQUIRED"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-095.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that all precommitted sensitivity and negative/sign-changing results are reported, model miscalibration is distinguished from team excess, and no post-hoc choice changes the headline conclusion.",
    "Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/bas/bas_stability_analysis.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.",
    "Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 2 of 3 step in Story POST-STORY-032 (Protected calibration, stability, scientific decision, and product semantics): Run precommitted temporal, peer, regime, model, cutoff, missingness, data-quality, and specification sensitivity analyses. Consume only verified prerequisite outputs from `POST-SUBTASK-093`, `POST-SUBTASK-094`, `POST-SUBTASK-102`. Produce `artifacts/bas/bas_stability_analysis.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-096.",
  "source_ids": [
    "GAP-009",
    "HANDOFF-009"
  ],
  "source_refs": [
    "SRCREF-02064",
    "SRCREF-02065",
    "SRCREF-02066",
    "SRCREF-02067",
    "SRCREF-02068",
    "SRCREF-02069",
    "SRCREF-02070",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01895",
    "SRCREF-01571"
  ],
  "specificity_fingerprint": "15aa3d20995559df381af8ef885bdeedd84eeb5d71f1dbeac0222d64e56c6655",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.",
    "Stop if the proposed method, threshold, peer set, fold construction, or product wording would conceal, reject, or overwrite a valid null/no-effect result."
  ],
  "supporting_source_refs": [
    "SRCREF-02068",
    "SRCREF-02069",
    "SRCREF-02070",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01895",
    "SRCREF-01571"
  ],
  "title": "[POST-SUBTASK-095] Run precommitted temporal, peer, regime, model, cutoff, missingness, data-quality, and specification sensitivity analyses",
  "traceability_inherited_from": [
    "POST-SUBTASK-096"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "CALIBRATION",
    "CHRONOLOGICAL_REPLAY",
    "INTEGRATION",
    "NEW_AUTOMATED_TEST_REQUIRED",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-032: Protected calibration, stability, scientific decision, and product semantics.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-095.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Run precommitted temporal, peer, regime, model, cutoff, missingness, data-quality, and specification sensitivity analyses

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-032: Protected calibration, stability, scientific decision, and product semantics.

## Scope

Execute the atomic 2 of 3 step in Story POST-STORY-032 (Protected calibration, stability, scientific decision, and product semantics): Run precommitted temporal, peer, regime, model, cutoff, missingness, data-quality, and specification sensitivity analyses. Consume only verified prerequisite outputs from `POST-SUBTASK-093`, `POST-SUBTASK-094`, `POST-SUBTASK-102`. Produce `artifacts/bas/bas_stability_analysis.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-096.

### Explicit In Scope

- Perform the exact action: Run precommitted temporal, peer, regime, model, cutoff, missingness, data-quality, and specification sensitivity analyses.
- Consume only verified prerequisite outputs from `POST-SUBTASK-093`, `POST-SUBTASK-094`, `POST-SUBTASK-102`.
- Demonstrate with saved evidence: All precommitted sensitivity and negative/sign-changing results are reported, model miscalibration is distinguished from team excess, and no post-hoc choice changes the headline conclusion.
- Demonstrate with saved evidence: The declared output `artifacts/bas/bas_stability_analysis.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/bas/bas_stability_analysis.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Evaluate ≥3/7/14/21 calibration, discrimination, reliability, uncertainty, and national/A&M/peer/regime scorecards on sealed predictions; Publish the final BAS scientific decision and prediction-first product language contract.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.
- Redefining BAS as generic Texas A&M loss probability or selecting specifications merely to manufacture a nonzero Aggie-specific effect.

## Prerequisites

- Dependency POST-SUBTASK-093 complete at required maturity
- Dependency POST-SUBTASK-094 complete at required maturity
- Dependency POST-SUBTASK-102 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-093
- POST-SUBTASK-094
- POST-SUBTASK-102

## Blocks

- POST-SUBTASK-096

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_bas_science_governance.py
- src/aggie_analytics/bas/labels.py
- src/aggie_analytics/bas/runtime.py
- docs/45_SCIENTIFIC_BAS_SPECIFICATION.md
- docs/48_BAS_COMPONENTS_REGIME_STABILITY_AND_CALIBRATION.md
- docs/47_BAS_GENERAL_FBS_AGGIE_EXCESS_AND_PEERS.md
- docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- bas-science
- bas

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

- artifacts/bas/bas_stability_analysis.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-096`
- Inherited from: POST-SUBTASK-096
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 19, "adr_ids": 21, "gap_ids": 1, "requirement_ids": 66, "risk_ids": 13}`

## Acceptance Criteria

1. All precommitted sensitivity and negative/sign-changing results are reported, model miscalibration is distinguished from team excess, and no post-hoc choice changes the headline conclusion.
2. The declared output `artifacts/bas/bas_stability_analysis.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
4. A scientifically valid null result—no persistent Aggie-specific excess after protected out-of-sample testing—must be preserved, reported, and accepted without changing the precommitted BAS definition, peers, thresholds, or evaluation window.
5. A null, non-significant, unstable, or directionally unsupported Aggie-specific excess result is accepted and reported without forcing a nonzero BAS effect; general FBS surprise and Texas A&M-specific excess remain distinct.

## Definition of Done

1. The atomic scope in POST-SUBTASK-095 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The output set `artifacts/bas/bas_stability_analysis.json` is demonstrably consumable by POST-SUBTASK-096 without manual reconstruction or undocumented state.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_bas_science_governance.py` — Run as a regression check after completing POST-SUBTASK-095; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w20_model_starter.py` — Run as a regression check after completing POST-SUBTASK-095; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_bas_science.py` — Run as a regression check after completing POST-SUBTASK-095; retain command, exit code, and relevant output.
- **CHRONOLOGICAL_REPLAY** / `CHRONOLOGICAL_REPLAY` — `artifacts/bas/bas_stability_analysis.json` — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/bas/bas_stability_analysis.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **CALIBRATION** / `CALIBRATION` — `artifacts/bas/bas_stability_analysis.json` — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- **INTEGRATION** / `INTEGRATION` — `artifacts/bas/bas_stability_analysis.json` — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- **NEW_AUTOMATED_TEST_REQUIRED** / `NEW_AUTOMATED_TEST_REQUIRED` — `NEW_TEST_REQUIRED::POST-SUBTASK-095` — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Required Evidence

- `artifacts/bas/bas_stability_analysis.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
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
  "completion_claim_limit": "EMPIRICALLY_VALIDATED",
  "downstream_consumer": "POST-SUBTASK-096",
  "governance_traceability_gate": "POST-SUBTASK-096",
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

Validate that `artifacts/bas/bas_stability_analysis.json` can be parsed and consumed by `POST-SUBTASK-096` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.

## Expected Maturity After Completion

`EMPIRICALLY_VALIDATED`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-095.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that all precommitted sensitivity and negative/sign-changing results are reported, model miscalibration is distinguished from team excess, and no post-hoc choice changes the headline conclusion.
- Acceptance failure: the evidence cannot demonstrate that the declared output `artifacts/bas/bas_stability_analysis.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Acceptance failure: the evidence cannot demonstrate that the work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.
- Stop if the proposed method, threshold, peer set, fold construction, or product wording would conceal, reject, or overwrite a valid null/no-effect result.

## Source References

- SRCREF-02064
- SRCREF-02065
- SRCREF-02066
- SRCREF-02067
- SRCREF-02068
- SRCREF-02069
- SRCREF-02070
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01895
- SRCREF-01571

## AI Context Notes

- Canonical parent Story: POST-STORY-032. Governance traceability gate: POST-SUBTASK-096. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-095.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

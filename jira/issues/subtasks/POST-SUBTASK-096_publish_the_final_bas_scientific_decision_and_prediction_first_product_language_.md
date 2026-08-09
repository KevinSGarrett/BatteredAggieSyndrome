<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-096_publish_the_final_bas_scientific_decision_and_prediction_first_product_language_.json -->
# POST-SUBTASK-096 — [POST-SUBTASK-096] Publish the final BAS scientific decision and prediction-first product language contract

## Canonical metadata

```json
{
  "acceptance_control_ids": [
    "AC-026",
    "AC-028",
    "AC-029",
    "AC-137",
    "AC-139",
    "AC-140",
    "AC-141",
    "AC-142",
    "AC-143",
    "AC-144",
    "AC-145",
    "AC-146",
    "AC-147",
    "AC-148",
    "AC-149",
    "AC-150",
    "AC-152",
    "AC-172",
    "AC-214"
  ],
  "acceptance_criteria": [
    "Scorecards include sample sizes, intervals/reliability, all protected thresholds/segments, and no protected refitting; small A&M samples never receive false precision.",
    "All precommitted sensitivity and negative/sign-changing results are reported, model miscalibration is distinguished from team excess, and no post-hoc choice changes the headline conclusion.",
    "The decision states supported/unsupported/inconclusive general and A&M findings with hashes; product keeps prediction primary, permits witty framing, prohibits loss-probability substitution, and never forces nonzero BAS.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "A scientifically valid null result—no persistent Aggie-specific excess after protected out-of-sample testing—must be preserved, reported, and accepted without changing the precommitted BAS definition, peers, thresholds, or evaluation window.",
    "A null, non-significant, unstable, or directionally unsupported Aggie-specific excess result is accepted and reported without forcing a nonzero BAS effect; general FBS surprise and Texas A&M-specific excess remain distinct."
  ],
  "adr_ids": [
    "ADR-002",
    "ADR-013",
    "ADR-016",
    "ADR-047",
    "ADR-058",
    "ADR-201",
    "ADR-203",
    "ADR-205",
    "ADR-206",
    "ADR-208",
    "ADR-212",
    "ADR-213",
    "ADR-214",
    "ADR-215",
    "ADR-216",
    "ADR-223",
    "ADR-239",
    "ADR-254",
    "ADR-302",
    "ADR-323",
    "ADR-325"
  ],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-032. Governance traceability gate: POST-SUBTASK-096. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-096.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/bas/BAS_SCIENTIFIC_DECISION.json",
    "artifacts/jira_evidence/POST-SUBTASK-096.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-093;POST-SUBTASK-094;POST-SUBTASK-095;POST-SUBTASK-102",
  "blocks": [
    "POST-STORY-035",
    "POST-SUBTASK-103",
    "POST-SUBTASK-104",
    "POST-SUBTASK-105"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-096_publish_the_final_bas_scientific_decision_and_prediction_first_product_language_.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-032",
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
    "The atomic scope in POST-SUBTASK-096 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-032."
  ],
  "dependencies": [
    "POST-SUBTASK-093",
    "POST-SUBTASK-094",
    "POST-SUBTASK-095",
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
  "end_to_end_validation": "Calibrated protected evidence yields a scientifically bounded BAS result and product contract that remains valid even when no persistent Aggie-specific excess exists. The gate decision must explicitly reevaluate downstream issues: POST-STORY-035, POST-SUBTASK-103, POST-SUBTASK-104, POST-SUBTASK-105.",
  "epic_id": "POST-EPIC-010",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-096.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/bas/BAS_SCIENTIFIC_DECISION.json"
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
    "tests/test_bas_science_governance.py",
    "docs/47_BAS_GENERAL_FBS_AGGIE_EXCESS_AND_PEERS.md",
    "docs/45_SCIENTIFIC_BAS_SPECIFICATION.md",
    "docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md",
    "docs/48_BAS_COMPONENTS_REGIME_STABILITY_AND_CALIBRATION.md"
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
    "tests/test_bas_science_governance.py",
    "docs/47_BAS_GENERAL_FBS_AGGIE_EXCESS_AND_PEERS.md",
    "docs/45_SCIENTIFIC_BAS_SPECIFICATION.md",
    "docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md",
    "docs/48_BAS_COMPONENTS_REGIME_STABILITY_AND_CALIBRATION.md"
  ],
  "gap_ids": [
    "GAP-007"
  ],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-096_publish_the_final_bas_scientific_decision_and_prediction_first_product_language_.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-096",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100400,
  "in_scope": [
    "Perform the exact action: Publish the final BAS scientific decision and prediction-first product language contract.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-093`, `POST-SUBTASK-094`, `POST-SUBTASK-095`, `POST-SUBTASK-102`.",
    "Demonstrate with saved evidence: Scorecards include sample sizes, intervals/reliability, all protected thresholds/segments, and no protected refitting; small A&M samples never receive false precision.",
    "Demonstrate with saved evidence: All precommitted sensitivity and negative/sign-changing results are reported, model miscalibration is distinguished from team excess, and no post-hoc choice changes the headline conclusion.",
    "Demonstrate with saved evidence: The decision states supported/unsupported/inconclusive general and A&M findings with hashes; product keeps prediction primary, permits witty framing, prohibits loss-probability substitution, and never forces nonzero BAS.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `artifacts/bas/BAS_SCIENTIFIC_DECISION.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-446",
  "labels": [
    "actionable",
    "bas",
    "core-release",
    "post-wave",
    "protected-gate",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-096",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Publish the final BAS scientific decision and prediction-first product language contract",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24586",
    "jira_updated_at": "2026-08-09T00:05:13.129-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Evaluate ≥3/7/14/21 calibration, discrimination, reliability, uncertainty, and national/A&M/peer/regime scorecards on sealed predictions; Run precommitted temporal, peer, regime, model, cutoff, missingness, data-quality, and specification sensitivity analyses.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.",
    "Redefining BAS as generic Texas A&M loss probability or selecting specifications merely to manufacture a nonzero Aggie-specific effect."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-032",
  "phase": "PHASE-3",
  "prerequisites": [
    "Dependency POST-SUBTASK-093 complete at required maturity",
    "Dependency POST-SUBTASK-094 complete at required maturity",
    "Dependency POST-SUBTASK-095 complete at required maturity",
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
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/ADR_INDEX.csv",
    "governance/REQUIREMENTS_INDEX.csv",
    "tests/test_bas_science_governance.py",
    "docs/47_BAS_GENERAL_FBS_AGGIE_EXCESS_AND_PEERS.md",
    "docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md",
    "docs/48_BAS_COMPONENTS_REGIME_STABILITY_AND_CALIBRATION.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/bas/BAS_SCIENTIFIC_DECISION.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-096; retain command, exit code, and relevant output.",
      "path": "tests/test_bas_science_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-096; retain command, exit code, and relevant output.",
      "path": "tests/test_w20_model_starter.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-096; retain command, exit code, and relevant output.",
      "path": "tools/validate_bas_science.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/bas/BAS_SCIENTIFIC_DECISION.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "CALIBRATION",
      "expectation": "Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.",
      "path": "artifacts/bas/BAS_SCIENTIFIC_DECISION.json",
      "validation_class": "CALIBRATION"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/bas/BAS_SCIENTIFIC_DECISION.json",
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
    "REQ-019",
    "REQ-034",
    "REQ-066",
    "REQ-092",
    "REQ-095",
    "REQ-096",
    "REQ-097",
    "REQ-098",
    "REQ-103",
    "REQ-104",
    "REQ-105",
    "REQ-120",
    "REQ-163",
    "REQ-164",
    "REQ-213",
    "REQ-353",
    "REQ-488",
    "REQ-490",
    "REQ-494",
    "REQ-495",
    "REQ-496",
    "REQ-497",
    "REQ-498",
    "REQ-499",
    "REQ-500",
    "REQ-501",
    "REQ-502",
    "REQ-504",
    "REQ-505",
    "REQ-506",
    "REQ-507",
    "REQ-508",
    "REQ-509",
    "REQ-510",
    "REQ-511",
    "REQ-512",
    "REQ-513",
    "REQ-514",
    "REQ-515",
    "REQ-516",
    "REQ-517",
    "REQ-518",
    "REQ-519",
    "REQ-520",
    "REQ-521",
    "REQ-522",
    "REQ-523",
    "REQ-524",
    "REQ-525",
    "REQ-526",
    "REQ-528",
    "REQ-537",
    "REQ-538",
    "REQ-539",
    "REQ-566",
    "REQ-582",
    "REQ-594",
    "REQ-595",
    "REQ-652",
    "REQ-675",
    "REQ-686",
    "REQ-707",
    "REQ-712",
    "REQ-713",
    "REQ-725",
    "REQ-738"
  ],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-096.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that scorecards include sample sizes, intervals/reliability, all protected thresholds/segments, and no protected refitting; small A&M samples never receive false precision.",
    "Acceptance failure: the evidence cannot demonstrate that all precommitted sensitivity and negative/sign-changing results are reported, model miscalibration is distinguished from team excess, and no post-hoc choice changes the headline conclusion.",
    "Acceptance failure: the evidence cannot demonstrate that the decision states supported/unsupported/inconclusive general and A&M findings with hashes; product keeps prediction primary, permits witty framing, prohibits loss-probability substitution, and never forces nonzero BAS.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [
    "RISK-006",
    "RISK-021",
    "RISK-127",
    "RISK-191",
    "RISK-195",
    "RISK-196",
    "RISK-201",
    "RISK-206",
    "RISK-208",
    "RISK-209",
    "RISK-219",
    "RISK-233",
    "RISK-287"
  ],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-032 (Protected calibration, stability, scientific decision, and product semantics): Publish the final BAS scientific decision and prediction-first product language contract. Consume only verified prerequisite outputs from `POST-SUBTASK-093`, `POST-SUBTASK-094`, `POST-SUBTASK-095`, `POST-SUBTASK-102`. Produce `artifacts/bas/BAS_SCIENTIFIC_DECISION.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
  "source_ids": [
    "GAP-007",
    "GAP-009",
    "HANDOFF-009",
    "ISSUE-027",
    "ISSUE-031",
    "ISSUE-043",
    "ISSUE-084",
    "ISSUE-106",
    "ISSUE-107",
    "ISSUE-109",
    "ISSUE-110",
    "ISSUE-111",
    "ISSUE-112",
    "ISSUE-114"
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
    "SRCREF-01571",
    "SRCREF-01569",
    "SRCREF-01927",
    "SRCREF-01931",
    "SRCREF-01943",
    "SRCREF-01951",
    "SRCREF-01952",
    "SRCREF-01953",
    "SRCREF-01955",
    "SRCREF-01956",
    "SRCREF-01957",
    "SRCREF-01958",
    "SRCREF-01960",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "specificity_fingerprint": "784b18d98cc52aca1cd38742b3537a84da9d2168412f31ac13e3f294c69159b2",
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
    "SRCREF-01571",
    "SRCREF-01569",
    "SRCREF-01927",
    "SRCREF-01931",
    "SRCREF-01943",
    "SRCREF-01951",
    "SRCREF-01952",
    "SRCREF-01953",
    "SRCREF-01955",
    "SRCREF-01956",
    "SRCREF-01957",
    "SRCREF-01958",
    "SRCREF-01960",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "title": "[POST-SUBTASK-096] Publish the final BAS scientific decision and prediction-first product language contract",
  "traceability_inherited_from": [],
  "traceability_resolution": "DIRECT_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "CALIBRATION",
    "END_TO_END",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-032: Protected calibration, stability, scientific decision, and product semantics.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-096.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Publish the final BAS scientific decision and prediction-first product language contract

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-032: Protected calibration, stability, scientific decision, and product semantics.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-032 (Protected calibration, stability, scientific decision, and product semantics): Publish the final BAS scientific decision and prediction-first product language contract. Consume only verified prerequisite outputs from `POST-SUBTASK-093`, `POST-SUBTASK-094`, `POST-SUBTASK-095`, `POST-SUBTASK-102`. Produce `artifacts/bas/BAS_SCIENTIFIC_DECISION.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Publish the final BAS scientific decision and prediction-first product language contract.
- Consume only verified prerequisite outputs from `POST-SUBTASK-093`, `POST-SUBTASK-094`, `POST-SUBTASK-095`, `POST-SUBTASK-102`.
- Demonstrate with saved evidence: Scorecards include sample sizes, intervals/reliability, all protected thresholds/segments, and no protected refitting; small A&M samples never receive false precision.
- Demonstrate with saved evidence: All precommitted sensitivity and negative/sign-changing results are reported, model miscalibration is distinguished from team excess, and no post-hoc choice changes the headline conclusion.
- Demonstrate with saved evidence: The decision states supported/unsupported/inconclusive general and A&M findings with hashes; product keeps prediction primary, permits witty framing, prohibits loss-probability substitution, and never forces nonzero BAS.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/bas/BAS_SCIENTIFIC_DECISION.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Evaluate ≥3/7/14/21 calibration, discrimination, reliability, uncertainty, and national/A&M/peer/regime scorecards on sealed predictions; Run precommitted temporal, peer, regime, model, cutoff, missingness, data-quality, and specification sensitivity analyses.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.
- Redefining BAS as generic Texas A&M loss probability or selecting specifications merely to manufacture a nonzero Aggie-specific effect.

## Prerequisites

- Dependency POST-SUBTASK-093 complete at required maturity
- Dependency POST-SUBTASK-094 complete at required maturity
- Dependency POST-SUBTASK-095 complete at required maturity
- Dependency POST-SUBTASK-102 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-093
- POST-SUBTASK-094
- POST-SUBTASK-095
- POST-SUBTASK-102

## Blocks

- POST-STORY-035
- POST-SUBTASK-103
- POST-SUBTASK-104
- POST-SUBTASK-105

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
- tests/test_bas_science_governance.py
- docs/47_BAS_GENERAL_FBS_AGGIE_EXCESS_AND_PEERS.md
- docs/45_SCIENTIFIC_BAS_SPECIFICATION.md
- docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md
- docs/48_BAS_COMPONENTS_REGIME_STABILITY_AND_CALIBRATION.md

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

- artifacts/bas/BAS_SCIENTIFIC_DECISION.json

## Direct Requirements

- REQ-019
- REQ-034
- REQ-066
- REQ-092
- REQ-095
- REQ-096
- REQ-097
- REQ-098
- REQ-103
- REQ-104
- REQ-105
- REQ-120
- REQ-163
- REQ-164
- REQ-213
- REQ-353
- REQ-488
- REQ-490
- REQ-494
- REQ-495
- REQ-496
- REQ-497
- REQ-498
- REQ-499
- REQ-500
- REQ-501
- REQ-502
- REQ-504
- REQ-505
- REQ-506
- REQ-507
- REQ-508
- REQ-509
- REQ-510
- REQ-511
- REQ-512
- REQ-513
- REQ-514
- REQ-515
- REQ-516
- REQ-517
- REQ-518
- REQ-519
- REQ-520
- REQ-521
- REQ-522
- REQ-523
- REQ-524
- REQ-525
- REQ-526
- REQ-528
- REQ-537
- REQ-538
- REQ-539
- REQ-566
- REQ-582
- REQ-594
- REQ-595
- REQ-652
- REQ-675
- REQ-686
- REQ-707
- REQ-712
- REQ-713
- REQ-725
- REQ-738

## Direct Acceptance Controls

- AC-026
- AC-028
- AC-029
- AC-137
- AC-139
- AC-140
- AC-141
- AC-142
- AC-143
- AC-144
- AC-145
- AC-146
- AC-147
- AC-148
- AC-149
- AC-150
- AC-152
- AC-172
- AC-214

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-096`
- Inherited from: None
- Resolution: `DIRECT_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 19, "adr_ids": 21, "gap_ids": 1, "requirement_ids": 66, "risk_ids": 13}`

## Acceptance Criteria

1. Scorecards include sample sizes, intervals/reliability, all protected thresholds/segments, and no protected refitting; small A&M samples never receive false precision.
2. All precommitted sensitivity and negative/sign-changing results are reported, model miscalibration is distinguished from team excess, and no post-hoc choice changes the headline conclusion.
3. The decision states supported/unsupported/inconclusive general and A&M findings with hashes; product keeps prediction primary, permits witty framing, prohibits loss-probability substitution, and never forces nonzero BAS.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
5. A scientifically valid null result—no persistent Aggie-specific excess after protected out-of-sample testing—must be preserved, reported, and accepted without changing the precommitted BAS definition, peers, thresholds, or evaluation window.
6. A null, non-significant, unstable, or directionally unsupported Aggie-specific excess result is accepted and reported without forcing a nonzero BAS effect; general FBS surprise and Texas A&M-specific excess remain distinct.

## Definition of Done

1. The atomic scope in POST-SUBTASK-096 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-032.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_bas_science_governance.py` — Run as a regression check after completing POST-SUBTASK-096; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w20_model_starter.py` — Run as a regression check after completing POST-SUBTASK-096; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_bas_science.py` — Run as a regression check after completing POST-SUBTASK-096; retain command, exit code, and relevant output.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/bas/BAS_SCIENTIFIC_DECISION.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **CALIBRATION** / `CALIBRATION` — `artifacts/bas/BAS_SCIENTIFIC_DECISION.json` — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- **END_TO_END** / `END_TO_END` — `artifacts/bas/BAS_SCIENTIFIC_DECISION.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/bas/BAS_SCIENTIFIC_DECISION.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
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
  "downstream_consumer": "POST-STORY-032",
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

Calibrated protected evidence yields a scientifically bounded BAS result and product contract that remains valid even when no persistent Aggie-specific excess exists. The gate decision must explicitly reevaluate downstream issues: POST-STORY-035, POST-SUBTASK-103, POST-SUBTASK-104, POST-SUBTASK-105.

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-096.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that scorecards include sample sizes, intervals/reliability, all protected thresholds/segments, and no protected refitting; small A&M samples never receive false precision.
- Acceptance failure: the evidence cannot demonstrate that all precommitted sensitivity and negative/sign-changing results are reported, model miscalibration is distinguished from team excess, and no post-hoc choice changes the headline conclusion.
- Acceptance failure: the evidence cannot demonstrate that the decision states supported/unsupported/inconclusive general and A&M findings with hashes; product keeps prediction primary, permits witty framing, prohibits loss-probability substitution, and never forces nonzero BAS.
- Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

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
- SRCREF-01569
- SRCREF-01927
- SRCREF-01931
- SRCREF-01943
- SRCREF-01951
- SRCREF-01952
- SRCREF-01953
- SRCREF-01955
- SRCREF-01956
- SRCREF-01957
- SRCREF-01958
- SRCREF-01960
- SRCREF-02116
- SRCREF-02117
- SRCREF-02118

## AI Context Notes

- Canonical parent Story: POST-STORY-032. Governance traceability gate: POST-SUBTASK-096. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-096.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

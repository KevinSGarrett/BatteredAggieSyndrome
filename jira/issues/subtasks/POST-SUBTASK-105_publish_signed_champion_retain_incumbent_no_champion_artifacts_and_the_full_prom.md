<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-105_publish_signed_champion_retain_incumbent_no_champion_artifacts_and_the_full_prom.json -->
# POST-SUBTASK-105 — [POST-SUBTASK-105] Publish signed champion/retain-incumbent/no-champion artifacts and the full promotion gate matrix

## Canonical metadata

```json
{
  "acceptance_control_ids": [
    "AC-009",
    "AC-012",
    "AC-013",
    "AC-014",
    "AC-015",
    "AC-016",
    "AC-018",
    "AC-019",
    "AC-022",
    "AC-023",
    "AC-024",
    "AC-025",
    "AC-027",
    "AC-035",
    "AC-047",
    "AC-060",
    "AC-069",
    "AC-070",
    "AC-071",
    "AC-073",
    "AC-076",
    "AC-077",
    "AC-082",
    "AC-086",
    "AC-087",
    "AC-088",
    "AC-090",
    "AC-091",
    "AC-092",
    "AC-096",
    "AC-099",
    "AC-100",
    "AC-114",
    "AC-117",
    "AC-118",
    "AC-120",
    "AC-122",
    "AC-124",
    "AC-131",
    "AC-132",
    "AC-134",
    "AC-136",
    "AC-158",
    "AC-163",
    "AC-164",
    "AC-165",
    "AC-166",
    "AC-167",
    "AC-168",
    "AC-169",
    "AC-170",
    "AC-171",
    "AC-174",
    "AC-189",
    "AC-194",
    "AC-201",
    "AC-203",
    "AC-204",
    "AC-215",
    "AC-221",
    "AC-223",
    "AC-227"
  ],
  "acceptance_criteria": [
    "Calibration failures cannot hide behind aggregate accuracy, unsupported conditions abstain/degrade, closing-market skill is separated, and every release-blocking control receives evidence-backed PASS/FAIL/BLOCKED/N-A/INCONCLUSIVE.",
    "No new metric/weight/threshold/candidate/segment is created after protected results; ties/inconclusive outcomes follow the sealed simpler/incumbent/no-promotion rule and null A&M/BAS findings remain valid.",
    "A signed artifact pins data/features/code/dependencies/splits/model/calibrators/A&M/BAS/OOD/scorecards and reproduces predictions, or no champion is written; GAP-008 closes only through genuine protected evidence.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [
    "ADR-015",
    "ADR-017",
    "ADR-024",
    "ADR-025",
    "ADR-049",
    "ADR-059",
    "ADR-083",
    "ADR-091",
    "ADR-126",
    "ADR-134",
    "ADR-136",
    "ADR-170",
    "ADR-199",
    "ADR-200",
    "ADR-249",
    "ADR-252",
    "ADR-258",
    "ADR-260",
    "ADR-262",
    "ADR-270",
    "ADR-275",
    "ADR-280",
    "ADR-287",
    "ADR-305",
    "ADR-324",
    "ADR-330"
  ],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-035. Governance traceability gate: POST-SUBTASK-105. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-105.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/validation/PROMOTION_DECISION.json",
    "artifacts/jira_evidence/POST-SUBTASK-105.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-087;POST-SUBTASK-096;POST-SUBTASK-102;POST-SUBTASK-103;POST-SUBTASK-104",
  "blocks": [
    "POST-EPIC-012",
    "POST-STORY-036",
    "POST-STORY-045",
    "POST-SUBTASK-106",
    "POST-SUBTASK-107",
    "POST-SUBTASK-108",
    "POST-SUBTASK-133",
    "POST-SUBTASK-134",
    "POST-SUBTASK-135"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-105_publish_signed_champion_retain_incumbent_no_champion_artifacts_and_the_full_prom.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-035",
    "governance_traceability_gate": "POST-SUBTASK-105",
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
  "component": "validation-promotion",
  "components_expected_to_be_touched": [
    "validation-promotion",
    "validation"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-105 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-035."
  ],
  "dependencies": [
    "POST-SUBTASK-087",
    "POST-SUBTASK-096",
    "POST-SUBTASK-102",
    "POST-SUBTASK-103",
    "POST-SUBTASK-104"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 62,
    "adr_ids": 26,
    "gap_ids": 0,
    "requirement_ids": 70,
    "risk_ids": 25
  },
  "effective_traceability_total": 183,
  "end_to_end_validation": "All sealed candidates receive complete reproducible protected evaluation and the system produces a signed champion or explicit no-champion result without fabricated performance. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-012, POST-STORY-036, POST-STORY-045, POST-SUBTASK-106, POST-SUBTASK-107, POST-SUBTASK-108, POST-SUBTASK-133, POST-SUBTASK-134, POST-SUBTASK-135.",
  "epic_id": "POST-EPIC-011",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-105.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/validation/PROMOTION_DECISION.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/ADR_INDEX.csv",
    "docs/56_VALIDATION_AND_PROTECTED_SPLITS.md",
    "docs/58_MODEL_PROMOTION_AND_THRESHOLD_PRECOMMITMENT.md",
    "docs/57_SCORING_CALIBRATION_AND_SCORECARDS.md",
    "docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/ADR_INDEX.csv",
    "docs/56_VALIDATION_AND_PROTECTED_SPLITS.md",
    "docs/58_MODEL_PROMOTION_AND_THRESHOLD_PRECOMMITMENT.md",
    "docs/57_SCORING_CALIBRATION_AND_SCORECARDS.md",
    "docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-105_publish_signed_champion_retain_incumbent_no_champion_artifacts_and_the_full_prom.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-105",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100409,
  "in_scope": [
    "Perform the exact action: Publish signed champion/retain-incumbent/no-champion artifacts and the full promotion gate matrix.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-087`, `POST-SUBTASK-096`, `POST-SUBTASK-102`, `POST-SUBTASK-103`, `POST-SUBTASK-104`.",
    "Demonstrate with saved evidence: Calibration failures cannot hide behind aggregate accuracy, unsupported conditions abstain/degrade, closing-market skill is separated, and every release-blocking control receives evidence-backed PASS/FAIL/BLOCKED/N-A/INCONCLUSIVE.",
    "Demonstrate with saved evidence: No new metric/weight/threshold/candidate/segment is created after protected results; ties/inconclusive outcomes follow the sealed simpler/incumbent/no-promotion rule and null A&M/BAS findings remain valid.",
    "Demonstrate with saved evidence: A signed artifact pins data/features/code/dependencies/splits/model/calibrators/A&M/BAS/OOD/scorecards and reproduces predictions, or no champion is written; GAP-008 closes only through genuine protected evidence.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `artifacts/validation/PROMOTION_DECISION.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-455",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "protected-gate",
    "subtask",
    "validation"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-105",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Publish signed champion/retain-incumbent/no-champion artifacts and the full promotion gate matrix",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24595",
    "jira_updated_at": "2026-08-09T23:24:10.268-0500",
    "last_synced_at": "2026-08-11T06:30:01.758065+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\POST-SUBTASK-177-play-drive-preliminary\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Evaluate task-specific calibration, intervals, tails, coherence, OOD, missingness, season/regime/source shift, market ablation, and resource robustness; Apply the precommitted multi-task promotion policy, uncertainty, simplicity, operational compatibility, A&M decision, and BAS scientific decision.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-035",
  "phase": "PHASE-4",
  "prerequisites": [
    "Dependency POST-SUBTASK-087 complete at required maturity",
    "Dependency POST-SUBTASK-096 complete at required maturity",
    "Dependency POST-SUBTASK-102 complete at required maturity",
    "Dependency POST-SUBTASK-103 complete at required maturity",
    "Dependency POST-SUBTASK-104 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02071",
    "SRCREF-02072",
    "SRCREF-02073",
    "SRCREF-02074"
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
    "docs/56_VALIDATION_AND_PROTECTED_SPLITS.md",
    "docs/58_MODEL_PROMOTION_AND_THRESHOLD_PRECOMMITMENT.md",
    "docs/57_SCORING_CALIBRATION_AND_SCORECARDS.md",
    "docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/validation/PROMOTION_DECISION.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-105; retain command, exit code, and relevant output.",
      "path": "tests/test_validation_science_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-105; retain command, exit code, and relevant output.",
      "path": "tools/validate_validation_science.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/validation/PROMOTION_DECISION.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "CALIBRATION",
      "expectation": "Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.",
      "path": "artifacts/validation/PROMOTION_DECISION.json",
      "validation_class": "CALIBRATION"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/validation/PROMOTION_DECISION.json",
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
    "REQ-060",
    "REQ-061",
    "REQ-070",
    "REQ-093",
    "REQ-118",
    "REQ-174",
    "REQ-179",
    "REQ-202",
    "REQ-206",
    "REQ-207",
    "REQ-225",
    "REQ-230",
    "REQ-282",
    "REQ-312",
    "REQ-325",
    "REQ-336",
    "REQ-340",
    "REQ-345",
    "REQ-348",
    "REQ-349",
    "REQ-350",
    "REQ-352",
    "REQ-355",
    "REQ-358",
    "REQ-360",
    "REQ-387",
    "REQ-421",
    "REQ-426",
    "REQ-430",
    "REQ-449",
    "REQ-483",
    "REQ-527",
    "REQ-541",
    "REQ-562",
    "REQ-567",
    "REQ-569",
    "REQ-570",
    "REQ-571",
    "REQ-572",
    "REQ-573",
    "REQ-574",
    "REQ-575",
    "REQ-576",
    "REQ-577",
    "REQ-578",
    "REQ-579",
    "REQ-580",
    "REQ-581",
    "REQ-584",
    "REQ-585",
    "REQ-588",
    "REQ-590",
    "REQ-591",
    "REQ-592",
    "REQ-593",
    "REQ-602",
    "REQ-608",
    "REQ-610",
    "REQ-627",
    "REQ-638",
    "REQ-656",
    "REQ-663",
    "REQ-669",
    "REQ-687",
    "REQ-693",
    "REQ-695",
    "REQ-699",
    "REQ-709",
    "REQ-720",
    "REQ-739"
  ],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-105.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that calibration failures cannot hide behind aggregate accuracy, unsupported conditions abstain/degrade, closing-market skill is separated, and every release-blocking control receives evidence-backed PASS/FAIL/BLOCKED/N-A/INCONCLUSIVE.",
    "Acceptance failure: the evidence cannot demonstrate that no new metric/weight/threshold/candidate/segment is created after protected results; ties/inconclusive outcomes follow the sealed simpler/incumbent/no-promotion rule and null A&M/BAS findings remain valid.",
    "Acceptance failure: the evidence cannot demonstrate that a signed artifact pins data/features/code/dependencies/splits/model/calibrators/A&M/BAS/OOD/scorecards and reproduces predictions, or no champion is written; GAP-008 closes only through genuine protected evidence.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [
    "RISK-005",
    "RISK-022",
    "RISK-030",
    "RISK-041",
    "RISK-049",
    "RISK-051",
    "RISK-103",
    "RISK-110",
    "RISK-112",
    "RISK-120",
    "RISK-121",
    "RISK-184",
    "RISK-188",
    "RISK-204",
    "RISK-210",
    "RISK-229",
    "RISK-231",
    "RISK-240",
    "RISK-242",
    "RISK-244",
    "RISK-252",
    "RISK-266",
    "RISK-289",
    "RISK-290",
    "RISK-310"
  ],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-035 (Calibration/robustness gates, A&M/BAS decisions, and champion promotion): Publish signed champion/retain-incumbent/no-champion artifacts and the full promotion gate matrix. Consume only verified prerequisite outputs from `POST-SUBTASK-087`, `POST-SUBTASK-096`, `POST-SUBTASK-102`, `POST-SUBTASK-103`, `POST-SUBTASK-104`. Produce `artifacts/validation/PROMOTION_DECISION.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
  "source_ids": [
    "GAP-008",
    "GAP-009",
    "HANDOFF-006",
    "HANDOFF-007",
    "ISSUE-030",
    "ISSUE-038"
  ],
  "source_refs": [
    "SRCREF-02071",
    "SRCREF-02072",
    "SRCREF-02073",
    "SRCREF-02074",
    "SRCREF-02075",
    "SRCREF-02076",
    "SRCREF-02077",
    "SRCREF-02078",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01892",
    "SRCREF-01570",
    "SRCREF-01571",
    "SRCREF-01893",
    "SRCREF-01930",
    "SRCREF-01938",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "specificity_fingerprint": "788c9376044bb63699063014ab55e8fd8484f580139d3acefdb8cbb6795e0153",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
  ],
  "supporting_source_refs": [
    "SRCREF-02075",
    "SRCREF-02076",
    "SRCREF-02077",
    "SRCREF-02078",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01892",
    "SRCREF-01570",
    "SRCREF-01571",
    "SRCREF-01893",
    "SRCREF-01930",
    "SRCREF-01938",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "title": "[POST-SUBTASK-105] Publish signed champion/retain-incumbent/no-champion artifacts and the full promotion gate matrix",
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
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-035: Calibration/robustness gates, A&M/BAS decisions, and champion promotion.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-105.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Publish signed champion/retain-incumbent/no-champion artifacts and the full promotion gate matrix

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-035: Calibration/robustness gates, A&M/BAS decisions, and champion promotion.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-035 (Calibration/robustness gates, A&M/BAS decisions, and champion promotion): Publish signed champion/retain-incumbent/no-champion artifacts and the full promotion gate matrix. Consume only verified prerequisite outputs from `POST-SUBTASK-087`, `POST-SUBTASK-096`, `POST-SUBTASK-102`, `POST-SUBTASK-103`, `POST-SUBTASK-104`. Produce `artifacts/validation/PROMOTION_DECISION.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Publish signed champion/retain-incumbent/no-champion artifacts and the full promotion gate matrix.
- Consume only verified prerequisite outputs from `POST-SUBTASK-087`, `POST-SUBTASK-096`, `POST-SUBTASK-102`, `POST-SUBTASK-103`, `POST-SUBTASK-104`.
- Demonstrate with saved evidence: Calibration failures cannot hide behind aggregate accuracy, unsupported conditions abstain/degrade, closing-market skill is separated, and every release-blocking control receives evidence-backed PASS/FAIL/BLOCKED/N-A/INCONCLUSIVE.
- Demonstrate with saved evidence: No new metric/weight/threshold/candidate/segment is created after protected results; ties/inconclusive outcomes follow the sealed simpler/incumbent/no-promotion rule and null A&M/BAS findings remain valid.
- Demonstrate with saved evidence: A signed artifact pins data/features/code/dependencies/splits/model/calibrators/A&M/BAS/OOD/scorecards and reproduces predictions, or no champion is written; GAP-008 closes only through genuine protected evidence.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/validation/PROMOTION_DECISION.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Evaluate task-specific calibration, intervals, tails, coherence, OOD, missingness, season/regime/source shift, market ablation, and resource robustness; Apply the precommitted multi-task promotion policy, uncertainty, simplicity, operational compatibility, A&M decision, and BAS scientific decision.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-087 complete at required maturity
- Dependency POST-SUBTASK-096 complete at required maturity
- Dependency POST-SUBTASK-102 complete at required maturity
- Dependency POST-SUBTASK-103 complete at required maturity
- Dependency POST-SUBTASK-104 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-087
- POST-SUBTASK-096
- POST-SUBTASK-102
- POST-SUBTASK-103
- POST-SUBTASK-104

## Blocks

- POST-EPIC-012
- POST-STORY-036
- POST-STORY-045
- POST-SUBTASK-106
- POST-SUBTASK-107
- POST-SUBTASK-108
- POST-SUBTASK-133
- POST-SUBTASK-134
- POST-SUBTASK-135

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- governance/ADR_INDEX.csv
- docs/56_VALIDATION_AND_PROTECTED_SPLITS.md
- docs/58_MODEL_PROMOTION_AND_THRESHOLD_PRECOMMITMENT.md
- docs/57_SCORING_CALIBRATION_AND_SCORECARDS.md
- docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- validation-promotion
- validation

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

- artifacts/validation/PROMOTION_DECISION.json

## Direct Requirements

- REQ-060
- REQ-061
- REQ-070
- REQ-093
- REQ-118
- REQ-174
- REQ-179
- REQ-202
- REQ-206
- REQ-207
- REQ-225
- REQ-230
- REQ-282
- REQ-312
- REQ-325
- REQ-336
- REQ-340
- REQ-345
- REQ-348
- REQ-349
- REQ-350
- REQ-352
- REQ-355
- REQ-358
- REQ-360
- REQ-387
- REQ-421
- REQ-426
- REQ-430
- REQ-449
- REQ-483
- REQ-527
- REQ-541
- REQ-562
- REQ-567
- REQ-569
- REQ-570
- REQ-571
- REQ-572
- REQ-573
- REQ-574
- REQ-575
- REQ-576
- REQ-577
- REQ-578
- REQ-579
- REQ-580
- REQ-581
- REQ-584
- REQ-585
- REQ-588
- REQ-590
- REQ-591
- REQ-592
- REQ-593
- REQ-602
- REQ-608
- REQ-610
- REQ-627
- REQ-638
- REQ-656
- REQ-663
- REQ-669
- REQ-687
- REQ-693
- REQ-695
- REQ-699
- REQ-709
- REQ-720
- REQ-739

## Direct Acceptance Controls

- AC-009
- AC-012
- AC-013
- AC-014
- AC-015
- AC-016
- AC-018
- AC-019
- AC-022
- AC-023
- AC-024
- AC-025
- AC-027
- AC-035
- AC-047
- AC-060
- AC-069
- AC-070
- AC-071
- AC-073
- AC-076
- AC-077
- AC-082
- AC-086
- AC-087
- AC-088
- AC-090
- AC-091
- AC-092
- AC-096
- AC-099
- AC-100
- AC-114
- AC-117
- AC-118
- AC-120
- AC-122
- AC-124
- AC-131
- AC-132
- AC-134
- AC-136
- AC-158
- AC-163
- AC-164
- AC-165
- AC-166
- AC-167
- AC-168
- AC-169
- AC-170
- AC-171
- AC-174
- AC-189
- AC-194
- AC-201
- AC-203
- AC-204
- AC-215
- AC-221
- AC-223
- AC-227

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-105`
- Inherited from: None
- Resolution: `DIRECT_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 62, "adr_ids": 26, "gap_ids": 0, "requirement_ids": 70, "risk_ids": 25}`

## Acceptance Criteria

1. Calibration failures cannot hide behind aggregate accuracy, unsupported conditions abstain/degrade, closing-market skill is separated, and every release-blocking control receives evidence-backed PASS/FAIL/BLOCKED/N-A/INCONCLUSIVE.
2. No new metric/weight/threshold/candidate/segment is created after protected results; ties/inconclusive outcomes follow the sealed simpler/incumbent/no-promotion rule and null A&M/BAS findings remain valid.
3. A signed artifact pins data/features/code/dependencies/splits/model/calibrators/A&M/BAS/OOD/scorecards and reproduces predictions, or no champion is written; GAP-008 closes only through genuine protected evidence.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. The atomic scope in POST-SUBTASK-105 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-035.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_validation_science_governance.py` — Run as a regression check after completing POST-SUBTASK-105; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_validation_science.py` — Run as a regression check after completing POST-SUBTASK-105; retain command, exit code, and relevant output.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/validation/PROMOTION_DECISION.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **CALIBRATION** / `CALIBRATION` — `artifacts/validation/PROMOTION_DECISION.json` — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- **END_TO_END** / `END_TO_END` — `artifacts/validation/PROMOTION_DECISION.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/validation/PROMOTION_DECISION.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
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
  "downstream_consumer": "POST-STORY-035",
  "governance_traceability_gate": "POST-SUBTASK-105",
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

All sealed candidates receive complete reproducible protected evaluation and the system produces a signed champion or explicit no-champion result without fabricated performance. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-012, POST-STORY-036, POST-STORY-045, POST-SUBTASK-106, POST-SUBTASK-107, POST-SUBTASK-108, POST-SUBTASK-133, POST-SUBTASK-134, POST-SUBTASK-135.

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-105.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that calibration failures cannot hide behind aggregate accuracy, unsupported conditions abstain/degrade, closing-market skill is separated, and every release-blocking control receives evidence-backed PASS/FAIL/BLOCKED/N-A/INCONCLUSIVE.
- Acceptance failure: the evidence cannot demonstrate that no new metric/weight/threshold/candidate/segment is created after protected results; ties/inconclusive outcomes follow the sealed simpler/incumbent/no-promotion rule and null A&M/BAS findings remain valid.
- Acceptance failure: the evidence cannot demonstrate that a signed artifact pins data/features/code/dependencies/splits/model/calibrators/A&M/BAS/OOD/scorecards and reproduces predictions, or no champion is written; GAP-008 closes only through genuine protected evidence.
- Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

## Source References

- SRCREF-02071
- SRCREF-02072
- SRCREF-02073
- SRCREF-02074
- SRCREF-02075
- SRCREF-02076
- SRCREF-02077
- SRCREF-02078
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01892
- SRCREF-01570
- SRCREF-01571
- SRCREF-01893
- SRCREF-01930
- SRCREF-01938
- SRCREF-02116
- SRCREF-02117
- SRCREF-02118

## AI Context Notes

- Canonical parent Story: POST-STORY-035. Governance traceability gate: POST-SUBTASK-105. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-105.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

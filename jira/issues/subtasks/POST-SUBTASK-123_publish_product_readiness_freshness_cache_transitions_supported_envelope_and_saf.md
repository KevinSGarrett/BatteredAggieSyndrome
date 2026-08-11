<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-123_publish_product_readiness_freshness_cache_transitions_supported_envelope_and_saf.json -->
# POST-SUBTASK-123 — [POST-SUBTASK-123] Publish product readiness, freshness/cache transitions, supported envelope, and safe failure decision

## Canonical metadata

```json
{
  "acceptance_control_ids": [
    "AC-005",
    "AC-021",
    "AC-032",
    "AC-037",
    "AC-046",
    "AC-059",
    "AC-062",
    "AC-089",
    "AC-121",
    "AC-185"
  ],
  "acceptance_criteria": [
    "Explanations use exact model/feature versions, expose direction/baseline/missingness/interactions/limits, analogs exclude same/future outcomes and expose distance/sample, and neither implies causality or replaces probability.",
    "Benchmarks run on the declared target with repeated workload identity and measure real resources/latency; unsupported/OOD explanations qualify or abstain and restricted data never leaks.",
    "Fresh/current/stale/blocked/unavailable/superseded transitions, cache activation/rollback, API/dashboard/security/explanation/performance evidence all pass; product cannot be ready on mutable/unapproved forecasts.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [
    "ADR-008",
    "ADR-032",
    "ADR-041",
    "ADR-048",
    "ADR-050",
    "ADR-053",
    "ADR-085",
    "ADR-114",
    "ADR-115",
    "ADR-131",
    "ADR-132",
    "ADR-160",
    "ADR-167",
    "ADR-172",
    "ADR-273",
    "ADR-295",
    "ADR-306",
    "ADR-329",
    "ADR-331",
    "ADR-332",
    "ADR-333",
    "ADR-335",
    "ADR-337",
    "ADR-342"
  ],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-041. Governance traceability gate: POST-SUBTASK-123. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-123.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/product/PRODUCT_READINESS.json",
    "artifacts/jira_evidence/POST-SUBTASK-123.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-009;POST-SUBTASK-120;POST-SUBTASK-121;POST-SUBTASK-122",
  "blocks": [
    "POST-EPIC-015",
    "POST-STORY-045",
    "POST-SUBTASK-133",
    "POST-SUBTASK-134",
    "POST-SUBTASK-135"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-123_publish_product_readiness_freshness_cache_transitions_supported_envelope_and_saf.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-041",
    "governance_traceability_gate": "POST-SUBTASK-123",
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
  "component": "serving-product",
  "components_expected_to_be_touched": [
    "serving-product",
    "product"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-123 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-041."
  ],
  "dependencies": [
    "POST-SUBTASK-009",
    "POST-SUBTASK-120",
    "POST-SUBTASK-121",
    "POST-SUBTASK-122"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 10,
    "adr_ids": 24,
    "gap_ids": 1,
    "requirement_ids": 38,
    "risk_ids": 12
  },
  "effective_traceability_total": 85,
  "end_to_end_validation": "A consumer receives faithful snapshot-grounded explanations/analogs and a responsive target-hardware product with explicit safe failure and freshness states. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-015, POST-STORY-045, POST-SUBTASK-133, POST-SUBTASK-134, POST-SUBTASK-135.",
  "epic_id": "POST-EPIC-013",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-123.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/product/PRODUCT_READINESS.json"
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
    "tests/test_w22_product_serving.py",
    "docs/product/API_CONTRACT.md",
    "src/aggie_analytics/product/freshness.py",
    "docs/107_W22_SNAPSHOT_SERVING_PRODUCT.md",
    "src/aggie_analytics/api/fastapi_app.py"
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
    "tests/test_w22_product_serving.py",
    "docs/product/API_CONTRACT.md",
    "src/aggie_analytics/product/freshness.py",
    "docs/107_W22_SNAPSHOT_SERVING_PRODUCT.md",
    "src/aggie_analytics/api/fastapi_app.py"
  ],
  "gap_ids": [
    "GAP-012"
  ],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-123_publish_product_readiness_freshness_cache_transitions_supported_envelope_and_saf.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-123",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100427,
  "in_scope": [
    "Perform the exact action: Publish product readiness, freshness/cache transitions, supported envelope, and safe failure decision.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-120`, `POST-SUBTASK-121`, `POST-SUBTASK-122`.",
    "Demonstrate with saved evidence: Explanations use exact model/feature versions, expose direction/baseline/missingness/interactions/limits, analogs exclude same/future outcomes and expose distance/sample, and neither implies causality or replaces probability.",
    "Demonstrate with saved evidence: Benchmarks run on the declared target with repeated workload identity and measure real resources/latency; unsupported/OOD explanations qualify or abstain and restricted data never leaks.",
    "Demonstrate with saved evidence: Fresh/current/stale/blocked/unavailable/superseded transitions, cache activation/rollback, API/dashboard/security/explanation/performance evidence all pass; product cannot be ready on mutable/unapproved forecasts.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `artifacts/product/PRODUCT_READINESS.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-473",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "product",
    "protected-gate",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-123",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Publish product readiness, freshness/cache transitions, supported envelope, and safe failure decision",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24613",
    "jira_updated_at": "2026-08-09T23:24:12.103-0500",
    "last_synced_at": "2026-08-11T07:25:49.170544+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\POST-SUBTASK-178-wmt-known-at\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Generate model-compatible global/per-game driver explanations and serve prior-only historical analog/peer/regime context; Run explanation faithfulness/stability/privacy tests plus target-host cold/warm load, API, snapshot, dashboard, concurrency, memory, CPU, and disk benchmarks.",
    "Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.",
    "Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-041",
  "phase": "PHASE-4",
  "prerequisites": [
    "Dependency POST-SUBTASK-009 complete at required maturity",
    "Dependency POST-SUBTASK-120 complete at required maturity",
    "Dependency POST-SUBTASK-121 complete at required maturity",
    "Dependency POST-SUBTASK-122 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02085",
    "SRCREF-02086",
    "SRCREF-02087",
    "SRCREF-02088"
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
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/ADR_INDEX.csv",
    "governance/REQUIREMENTS_INDEX.csv",
    "tests/test_w22_product_serving.py",
    "docs/product/API_CONTRACT.md",
    "src/aggie_analytics/product/freshness.py",
    "docs/107_W22_SNAPSHOT_SERVING_PRODUCT.md",
    "src/aggie_analytics/api/fastapi_app.py"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/product/PRODUCT_READINESS.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.",
    "Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-123; retain command, exit code, and relevant output.",
      "path": "tests/test_w22_product_serving.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-123; retain command, exit code, and relevant output.",
      "path": "tools/validate_w22_product.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "BENCHMARK",
      "expectation": "Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.",
      "path": "artifacts/product/PRODUCT_READINESS.json",
      "validation_class": "BENCHMARK"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/product/PRODUCT_READINESS.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "CALIBRATION",
      "expectation": "Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.",
      "path": "artifacts/product/PRODUCT_READINESS.json",
      "validation_class": "CALIBRATION"
    },
    {
      "classification": "SECURITY",
      "expectation": "Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.",
      "path": "artifacts/product/PRODUCT_READINESS.json",
      "validation_class": "SECURITY"
    },
    {
      "classification": "OPERATIONS",
      "expectation": "Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.",
      "path": "artifacts/product/PRODUCT_READINESS.json",
      "validation_class": "OPERATIONS"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/product/PRODUCT_READINESS.json",
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
    "REQ-016",
    "REQ-047",
    "REQ-052",
    "REQ-064",
    "REQ-075",
    "REQ-115",
    "REQ-122",
    "REQ-124",
    "REQ-152",
    "REQ-153",
    "REQ-169",
    "REQ-171",
    "REQ-172",
    "REQ-183",
    "REQ-198",
    "REQ-212",
    "REQ-254",
    "REQ-266",
    "REQ-267",
    "REQ-279",
    "REQ-329",
    "REQ-335",
    "REQ-347",
    "REQ-351",
    "REQ-359",
    "REQ-405",
    "REQ-413",
    "REQ-628",
    "REQ-629",
    "REQ-646",
    "REQ-654",
    "REQ-722",
    "REQ-723",
    "REQ-724",
    "REQ-726",
    "REQ-728",
    "REQ-729",
    "REQ-730"
  ],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-123.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that explanations use exact model/feature versions, expose direction/baseline/missingness/interactions/limits, analogs exclude same/future outcomes and expose distance/sample, and neither implies causality or replaces probability.",
    "Acceptance failure: the evidence cannot demonstrate that benchmarks run on the declared target with repeated workload identity and measure real resources/latency; unsupported/OOD explanations qualify or abstain and restricted data never leaks.",
    "Acceptance failure: the evidence cannot demonstrate that fresh/current/stale/blocked/unavailable/superseded transitions, cache activation/rollback, API/dashboard/security/explanation/performance evidence all pass; product cannot be ready on mutable/unapproved forecasts.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [
    "RISK-039",
    "RISK-040",
    "RISK-043",
    "RISK-135",
    "RISK-149",
    "RISK-155",
    "RISK-157",
    "RISK-261",
    "RISK-265",
    "RISK-302",
    "RISK-303",
    "RISK-304"
  ],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-041 (Faithful drivers, historical analogs, provenance, and target performance): Publish product readiness, freshness/cache transitions, supported envelope, and safe failure decision. Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-120`, `POST-SUBTASK-121`, `POST-SUBTASK-122`. Produce `artifacts/product/PRODUCT_READINESS.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
  "source_ids": [
    "GAP-001",
    "GAP-012",
    "HANDOFF-011",
    "ISSUE-005",
    "ISSUE-006",
    "ISSUE-011",
    "ISSUE-026",
    "ISSUE-037",
    "ISSUE-040"
  ],
  "source_refs": [
    "SRCREF-02085",
    "SRCREF-02086",
    "SRCREF-02087",
    "SRCREF-02088",
    "SRCREF-02089",
    "SRCREF-02090",
    "SRCREF-02091",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01897",
    "SRCREF-01574",
    "SRCREF-01563",
    "SRCREF-01905",
    "SRCREF-01906",
    "SRCREF-01911",
    "SRCREF-01926",
    "SRCREF-01937",
    "SRCREF-01940",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "specificity_fingerprint": "a6cf99aa5483abae2057a256efe0ee3796128e9017b067af2d1fc0d0c7f28146",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
  ],
  "supporting_source_refs": [
    "SRCREF-02089",
    "SRCREF-02090",
    "SRCREF-02091",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01897",
    "SRCREF-01574",
    "SRCREF-01563",
    "SRCREF-01905",
    "SRCREF-01906",
    "SRCREF-01911",
    "SRCREF-01926",
    "SRCREF-01937",
    "SRCREF-01940",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "title": "[POST-SUBTASK-123] Publish product readiness, freshness/cache transitions, supported envelope, and safe failure decision",
  "traceability_inherited_from": [],
  "traceability_resolution": "DIRECT_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "BENCHMARK",
    "CALIBRATION",
    "END_TO_END",
    "OPERATIONS",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC",
    "SECURITY"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-041: Faithful drivers, historical analogs, provenance, and target performance.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-123.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Publish product readiness, freshness/cache transitions, supported envelope, and safe failure decision

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-041: Faithful drivers, historical analogs, provenance, and target performance.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-041 (Faithful drivers, historical analogs, provenance, and target performance): Publish product readiness, freshness/cache transitions, supported envelope, and safe failure decision. Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-120`, `POST-SUBTASK-121`, `POST-SUBTASK-122`. Produce `artifacts/product/PRODUCT_READINESS.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Publish product readiness, freshness/cache transitions, supported envelope, and safe failure decision.
- Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-120`, `POST-SUBTASK-121`, `POST-SUBTASK-122`.
- Demonstrate with saved evidence: Explanations use exact model/feature versions, expose direction/baseline/missingness/interactions/limits, analogs exclude same/future outcomes and expose distance/sample, and neither implies causality or replaces probability.
- Demonstrate with saved evidence: Benchmarks run on the declared target with repeated workload identity and measure real resources/latency; unsupported/OOD explanations qualify or abstain and restricted data never leaks.
- Demonstrate with saved evidence: Fresh/current/stale/blocked/unavailable/superseded transitions, cache activation/rollback, API/dashboard/security/explanation/performance evidence all pass; product cannot be ready on mutable/unapproved forecasts.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/product/PRODUCT_READINESS.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Generate model-compatible global/per-game driver explanations and serve prior-only historical analog/peer/regime context; Run explanation faithfulness/stability/privacy tests plus target-host cold/warm load, API, snapshot, dashboard, concurrency, memory, CPU, and disk benchmarks.
- Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Prerequisites

- Dependency POST-SUBTASK-009 complete at required maturity
- Dependency POST-SUBTASK-120 complete at required maturity
- Dependency POST-SUBTASK-121 complete at required maturity
- Dependency POST-SUBTASK-122 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-009
- POST-SUBTASK-120
- POST-SUBTASK-121
- POST-SUBTASK-122

## Blocks

- POST-EPIC-015
- POST-STORY-045
- POST-SUBTASK-133
- POST-SUBTASK-134
- POST-SUBTASK-135

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
- tests/test_w22_product_serving.py
- docs/product/API_CONTRACT.md
- src/aggie_analytics/product/freshness.py
- docs/107_W22_SNAPSHOT_SERVING_PRODUCT.md
- src/aggie_analytics/api/fastapi_app.py

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- serving-product
- product

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

- artifacts/product/PRODUCT_READINESS.json

## Direct Requirements

- REQ-016
- REQ-047
- REQ-052
- REQ-064
- REQ-075
- REQ-115
- REQ-122
- REQ-124
- REQ-152
- REQ-153
- REQ-169
- REQ-171
- REQ-172
- REQ-183
- REQ-198
- REQ-212
- REQ-254
- REQ-266
- REQ-267
- REQ-279
- REQ-329
- REQ-335
- REQ-347
- REQ-351
- REQ-359
- REQ-405
- REQ-413
- REQ-628
- REQ-629
- REQ-646
- REQ-654
- REQ-722
- REQ-723
- REQ-724
- REQ-726
- REQ-728
- REQ-729
- REQ-730

## Direct Acceptance Controls

- AC-005
- AC-021
- AC-032
- AC-037
- AC-046
- AC-059
- AC-062
- AC-089
- AC-121
- AC-185

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-123`
- Inherited from: None
- Resolution: `DIRECT_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 10, "adr_ids": 24, "gap_ids": 1, "requirement_ids": 38, "risk_ids": 12}`

## Acceptance Criteria

1. Explanations use exact model/feature versions, expose direction/baseline/missingness/interactions/limits, analogs exclude same/future outcomes and expose distance/sample, and neither implies causality or replaces probability.
2. Benchmarks run on the declared target with repeated workload identity and measure real resources/latency; unsupported/OOD explanations qualify or abstain and restricted data never leaks.
3. Fresh/current/stale/blocked/unavailable/superseded transitions, cache activation/rollback, API/dashboard/security/explanation/performance evidence all pass; product cannot be ready on mutable/unapproved forecasts.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. The atomic scope in POST-SUBTASK-123 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-041.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w22_product_serving.py` — Run as a regression check after completing POST-SUBTASK-123; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_w22_product.py` — Run as a regression check after completing POST-SUBTASK-123; retain command, exit code, and relevant output.
- **BENCHMARK** / `BENCHMARK` — `artifacts/product/PRODUCT_READINESS.json` — Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/product/PRODUCT_READINESS.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **CALIBRATION** / `CALIBRATION` — `artifacts/product/PRODUCT_READINESS.json` — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- **SECURITY** / `SECURITY` — `artifacts/product/PRODUCT_READINESS.json` — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- **OPERATIONS** / `OPERATIONS` — `artifacts/product/PRODUCT_READINESS.json` — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- **END_TO_END** / `END_TO_END` — `artifacts/product/PRODUCT_READINESS.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/product/PRODUCT_READINESS.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "PRODUCTION_READY",
  "downstream_consumer": "POST-STORY-041",
  "governance_traceability_gate": "POST-SUBTASK-123",
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

A consumer receives faithful snapshot-grounded explanations/analogs and a responsive target-hardware product with explicit safe failure and freshness states. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-015, POST-STORY-045, POST-SUBTASK-133, POST-SUBTASK-134, POST-SUBTASK-135.

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-123.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that explanations use exact model/feature versions, expose direction/baseline/missingness/interactions/limits, analogs exclude same/future outcomes and expose distance/sample, and neither implies causality or replaces probability.
- Acceptance failure: the evidence cannot demonstrate that benchmarks run on the declared target with repeated workload identity and measure real resources/latency; unsupported/OOD explanations qualify or abstain and restricted data never leaks.
- Acceptance failure: the evidence cannot demonstrate that fresh/current/stale/blocked/unavailable/superseded transitions, cache activation/rollback, API/dashboard/security/explanation/performance evidence all pass; product cannot be ready on mutable/unapproved forecasts.
- Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

## Source References

- SRCREF-02085
- SRCREF-02086
- SRCREF-02087
- SRCREF-02088
- SRCREF-02089
- SRCREF-02090
- SRCREF-02091
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01897
- SRCREF-01574
- SRCREF-01563
- SRCREF-01905
- SRCREF-01906
- SRCREF-01911
- SRCREF-01926
- SRCREF-01937
- SRCREF-01940
- SRCREF-02116
- SRCREF-02117
- SRCREF-02118

## AI Context Notes

- Canonical parent Story: POST-STORY-041. Governance traceability gate: POST-SUBTASK-123. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-123.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.

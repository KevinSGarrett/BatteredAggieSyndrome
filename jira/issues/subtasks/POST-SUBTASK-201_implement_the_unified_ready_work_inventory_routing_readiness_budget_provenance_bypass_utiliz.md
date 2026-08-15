<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-201_implement_the_unified_ready_work_inventory_routing_readiness_budget_provenance_bypass_utiliz.json -->
# POST-SUBTASK-201 — [POST-SUBTASK-201] Implement the unified ready-work inventory, routing, readiness, budget, provenance, bypass, utilization, and completeness foundation

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Inventory validation enforces effort points 1/2/3/5/8, stable identities, anti-padding, one disposition, and complete count/point reconciliation.",
    "Readiness binds provider, resolved model and digest, task format, prompt/schema identity, policy version, and execution surface; empirical rejection cannot be overridden by a status edit.",
    "Cursor, loopback Ollama, and exact CPU-worker identity policies fail closed; direct endpoint bypasses are detected.",
    "A refreshable content-addressed ready-work inventory and separate evidence-derived operational-completeness validator fail stale or overstated dispositions.",
    "Credential-safe live catalog/runtime evidence is content-addressed outside Git and all focused/full validators pass through protected integration.",
    "The controller and independent watchdog are OS-supervised outside Codex Desktop, recover from crash/restart, agree on maximum justified state, and cannot overclaim partial operation.",
    "All 204 acceptance rows map to one canonical/live owner and the runtime validator exits zero only when every mandatory row passes.",
    "Undispatched inventory revisions are preserved and may be superseded append-only; active or externally consequential identity changes fail closed without terminating the controller.",
    "Inventory derivation semantically validates exact local-model, CPU-worker, Cursor, usage, review, and dispatch-origin evidence instead of treating directory hashes as readiness.",
    "The persistent scheduler discovers granular BAS units and durably leases, dispatches, validates, reviews, settles, cleans, closes or requeues them without an active Codex turn.",
    "The independent watchdog reports process health separately and fails operational completeness on stale inventory, idle admitted work, zero dispatch, reconciliation gaps, abandoned leases, or unsupported claims.",
    "The fail-closed direct-Codex interlock rejects ordinary PROJECT_WORK until an independent two-hour no-Codex black-box test, 24-hour probation, and seven-day soak pass with zero unjustified bypass, positive downstream-consumed useful offload, positive measured savings, and exact-main deployment identity."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical unified assistive contract source is `SRCREF-02121`.",
    "Never expose credentials, .env content, private data, or unnecessary protected evidence.",
    "Codex and deterministic validators retain canonical, scientific, Git/GitHub, Jira, and publication authority.",
    "Live Jira synchronization maps the detailed 2020/2018/2019/2021 acquisition checkpoint to the bounded PARTIAL select option while preserving the exact canonical evidence state; unknown non-enumerated states fail closed."
  ],
  "allowed_modification_paths": [
    "configs/assistive_provider_registry.json",
    "configs/assistive_route_readiness.json",
    "configs/unified_assistive_policy.json",
    "configs/unified_assistive_ready_work.json",
    "configs/unified_assistive_operational_claims.json",
    "configs/unified_assistive_acceptance_ownership.json",
    "configs/codex_usage_interlock_change_manifest.json",
    "configs/unified_assistive_change_routing_binding.json",
    "instructions/25_FORT_KNOX_ASSISTIVE_EXECUTION_INTERLOCK.md",
    "instructions/policies/assistive_execution_interlock.json",
    "tools/activate_codex_usage_interlock.py",
    "tools/validate_codex_usage_interlock.py",
    "tests/test_codex_usage_interlock.py",
    "src/aggie_analytics/assistive_plane",
    "tools/adopt_unified_enforcement_package.py",
    "tools/validate_unified_acceptance_ownership.py",
    "tools/run_unified_assistive_controller.py",
    "tools/run_unified_assistive_watchdog.py",
    "tools/materialize_unified_assistive_inventory.py",
    "tools/validate_unified_assistive_plane.py",
    "tools/validate_unified_assistive_completeness.py",
    "tools/refresh_cursor_catalog.py",
    "tools/refresh_local_assistive_runtime.py",
    "tests/test_unified_controller_state.py",
    "tests/test_unified_assistive_plane.py",
    "tests/test_unified_assistive_completeness.py",
    "governance/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md",
    "governance/SOURCE_OF_TRUTH_MAP.md",
    "docs/architecture/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md",
    "docs/operations/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md",
    "tests/test_unified_inventory_materializer.py",
    "tests/test_unified_inventory_scheduler.py",
    "tests/test_unified_runtime_inventory_dispatch.py",
    "jira/tools/import_bat_live.py",
    "tests/test_jira_evidence_state_mapping.py",
    "tests/test_jira_operational_status_policy.py",
    "artifacts/jira_evidence/POST-SUBTASK-201.json"
  ],
  "blocked_reason": "USER_SCOPE_OVERRIDE_BAS_ONLY: assistive-plane execution is paused; preserve existing evidence and do not resume without a later explicit user instruction.",
  "blocks": [
    "POST-SUBTASK-202",
    "POST-SUBTASK-203",
    "POST-SUBTASK-204"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-201_implement_the_unified_ready_work_inventory_routing_readiness_budget_provenance_bypass_utiliz.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "budget_ledger_required": true,
    "candidate_only": true,
    "negative_results_preserved": true,
    "protected_nonclaims_required": true,
    "provenance_dimensions": [
      "source",
      "capture",
      "prompt",
      "schema",
      "model",
      "reasoning",
      "code",
      "config",
      "runtime",
      "cost"
    ]
  },
  "component": "operations-security",
  "components_expected_to_be_touched": [
    "operations-security",
    "assistive-plane",
    "orchestration"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row and negative findings remain preserved.",
    "Every output is content-hashed with source/data/code/config/model/runtime identities and an explicit candidate/review/quarantine/rejected disposition.",
    "OpenAI remains optional, store:false, external-storage-only, candidate-only, and unable to alter canonical or protected truth directly.",
    "Budget reservations, actual tokens/cost, remaining allocation, cleanup, and unresolved review items are reported without exposing credentials.",
    "Repository, provenance, Jira second-pass, secret, PIT/leakage/identity where applicable, and relevant automated tests pass.",
    "No historical-completeness, production-readiness, protected-performance, A&M-lift, BAS, Aggie Excess, or scientific-result claim is made from this work alone.",
    "Independent immutable evidence passes the two-hour black-box, 24-hour probation, and seven-day soak gates with no manual packet replenishment, no unjustified direct execution, positive downstream-consumed useful offload, positive measured savings, and exact merged-main deployment identity."
  ],
  "dependencies": [
    "POST-SUBTASK-160",
    "POST-SUBTASK-198"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 0,
    "adr_ids": 0,
    "gap_ids": 0,
    "requirement_ids": 0,
    "risk_ids": 0
  },
  "effective_traceability_total": 0,
  "end_to_end_validation": "Use fake synchronous and Batch clients to prove a registered cited job is admitted, store:false, strict-schema validated, externally content-addressed, candidate-disposed, cost-settled, cached, and unable to touch protected truth.",
  "epic_id": "POST-EPIC-018",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-201.json",
  "evidence_state": "PARTIAL",
  "execution_lane": "SHARED_CONTRACT",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "INTEGRATED",
  "expected_outputs": [
    "artifacts/jira_evidence/POST-SUBTASK-201.json"
  ],
  "files_expected_to_be_read": [
    "governance/OPENAI_ASSISTIVE_PLANE.md",
    "configs/openai_assist_policy.json",
    "configs/openai_task_registry.json",
    "schemas/openai/assistive_candidate.schema.json",
    "docs/final/CODEX_HANDOFF.md"
  ],
  "files_expected_to_be_touched": [
    "configs/assistive_provider_registry.json",
    "configs/assistive_route_readiness.json",
    "configs/unified_assistive_policy.json",
    "configs/unified_assistive_ready_work.json",
    "configs/unified_assistive_operational_claims.json",
    "configs/unified_assistive_acceptance_ownership.json",
    "configs/codex_usage_interlock_change_manifest.json",
    "configs/unified_assistive_change_routing_binding.json",
    "instructions/25_FORT_KNOX_ASSISTIVE_EXECUTION_INTERLOCK.md",
    "instructions/policies/assistive_execution_interlock.json",
    "tools/activate_codex_usage_interlock.py",
    "tools/validate_codex_usage_interlock.py",
    "tests/test_codex_usage_interlock.py",
    "src/aggie_analytics/assistive_plane",
    "tools/adopt_unified_enforcement_package.py",
    "tools/validate_unified_acceptance_ownership.py",
    "tools/run_unified_assistive_controller.py",
    "tools/run_unified_assistive_watchdog.py",
    "tools/materialize_unified_assistive_inventory.py",
    "tools/validate_unified_assistive_plane.py",
    "tools/validate_unified_assistive_completeness.py",
    "tools/refresh_cursor_catalog.py",
    "tools/refresh_local_assistive_runtime.py",
    "tests/test_unified_controller_state.py",
    "tests/test_unified_assistive_plane.py",
    "tests/test_unified_assistive_completeness.py",
    "governance/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md",
    "governance/SOURCE_OF_TRUTH_MAP.md",
    "docs/architecture/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md",
    "docs/operations/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md",
    "tests/test_unified_inventory_materializer.py",
    "tests/test_unified_inventory_scheduler.py",
    "tests/test_unified_runtime_inventory_dispatch.py",
    "jira/tools/import_bat_live.py",
    "tests/test_jira_evidence_state_mapping.py",
    "tests/test_jira_operational_status_policy.py"
  ],
  "files_to_inspect": [
    "governance/OPENAI_ASSISTIVE_PLANE.md",
    "configs/openai_assist_policy.json",
    "configs/openai_task_registry.json",
    "schemas/openai/assistive_candidate.schema.json",
    "docs/final/CODEX_HANDOFF.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-201_implement_the_unified_ready_work_inventory_routing_readiness_budget_provenance_bypass_utiliz.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-201",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100511,
  "in_scope": [
    "Perform the exact action: Implement the governed OpenAI controller, storage, budget, provenance, schema, security, and cleanup foundation.",
    "Use one governed controller, strict Structured Outputs, minimized cited evidence, content-addressed external storage, deterministic validation, and locally enforced cost admission.",
    "Preserve abstentions, conflicts, schema failures, unsupported facts, partial batch failures, and negative empirical results."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-560",
  "labels": [
    "actionable",
    "post-wave",
    "unified-assistive",
    "candidate-only",
    "subtask"
  ],
  "last_content_audit": "2026-08-15",
  "local_id": "POST-SUBTASK-201",
  "maturity_before": "NOT_STARTED",
  "objective": "Implement the unified ready-work inventory, routing, readiness, budget, provenance, bypass, utilization, and completeness foundation",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24953",
    "jira_updated_at": "2026-08-14T23:17:02.022-0500",
    "last_synced_at": "2026-08-15T04:17:25.130072+00:00",
    "source_export": "jira/reconciliation/BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Any direct model write to canonical data, PIT state, labels, protected evaluation, promotion, forecasts, BAS, Aggie Excess, or publication state.",
    "Scattered OpenAI API calls, hosted-Evals dependence, prompt ingestion of secrets or whole data lakes, or bypass of the USD 100 ledger hard stop.",
    "Changing protected requirements, judging rules, split seals, or scientific acceptance thresholds merely to obtain a passing result.",
    "Treating ordinary delegable PROJECT_WORK as authorized direct-Codex fallback merely because a provider, packet, inventory, adapter, or budget stage is unavailable; only bounded pipeline repair, authority-only, and fixed deterministic operations remain directly eligible while the interlock is closed."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-058",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-040 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02121"
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
    "governance/OPENAI_ASSISTIVE_PLANE.md",
    "configs/openai_assist_policy.json",
    "configs/openai_task_registry.json",
    "schemas/openai/assistive_candidate.schema.json",
    "docs/final/CODEX_HANDOFF.md"
  ],
  "ready": false,
  "record_revision": "2.2",
  "required_evidence": [
    "`artifacts/jira_evidence/POST-SUBTASK-160.json` with one evidence row per acceptance criterion and exact artifact hashes.",
    "Request/job/Jira/source/capture/prompt/schema/model/reasoning identities; estimated and actual tokens/cost; validation and disposition.",
    "Cleanup record for remote files where practical and abandoned local temporary files, plus remaining review/quarantine items.",
    "Exact commands, exit codes, relevant output, failed/negative cases, and downstream readiness changes."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Credential redaction, store:false, candidate-only authority, strict schemas, budget hard stop, and isolation gates pass.",
      "path": "tests/test_openai_assist.py",
      "validation_class": "SECURITY"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Use fake synchronous and Batch clients to prove a registered cited job is admitted, store:false, strict-schema validated, externally content-addressed, candidate-disposed, cost-settled, cached, and unable to touch protected truth.",
      "path": "artifacts/jira_evidence/POST-SUBTASK-160.json",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "REPRODUCIBILITY",
      "expectation": "Pin policy, prompt, schema, model, reasoning, source, request/response, cost, code, and runtime identities.",
      "path": "ISSUE_COMPLETION_MANIFEST",
      "validation_class": "REPRODUCIBILITY"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "A successful API response is not evidence if schema, evidence, provenance, PIT/leakage, identity, cost, or candidate-authority validation fails.",
    "The unit fails if any unsupported fact enters canonical data or any name-only/model-only merge is approved.",
    "The unit fails if cost is admitted beyond an allocation or the absolute USD 100 committed-cost hard stop.",
    "The unit fails if credentials, .env content, private personal information, or unnecessary protected evidence is exposed."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Preserve the merged provider-neutral foundation, then implement and deploy the persistent OS-supervised controller, SQLite WAL state machine, independent read-only watchdog, fail-closed direct-Codex work interlock, immutable pre-routing and changed-path binding, 204-row ownership/evidence evaluator, live inventory, budgets, retries, reconciliation, control CLI/API, backup, rollback, independent no-Codex black-box proof, probation, soak, and cleanup.",
  "source_ids": [
    "UNIFIED-ASSISTIVE-EXECUTION-PLAN"
  ],
  "source_refs": [
    "SRCREF-02121"
  ],
  "stop_conditions": [
    "Stop only the affected API job on missing evidence, invalid schema, unsupported fact, credential exposure, budget rejection, provider failure, or inaccessible source; continue independent work.",
    "Quarantine the affected result on contradiction, refusal, malformed output, provenance mismatch, PIT/target leakage, or identity risk.",
    "Stop and preserve evidence rather than inventing facts, timestamps, metrics, identities, or maturity."
  ],
  "supporting_source_refs": [],
  "title": "[POST-SUBTASK-201] Implement the unified ready-work inventory, routing, readiness, budget, provenance, bypass, utilization, and completeness foundation",
  "traceability_inherited_from": [],
  "traceability_resolution": "DIRECT_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "END_TO_END",
    "REPRODUCIBILITY",
    "SECURITY"
  ],
  "why_this_exists": "The mandatory OpenAI assistive-plane contract requires an executable, independently evidenced work unit rather than an untracked direct API call.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-201.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Implement the unified ready-work inventory, routing, readiness, budget, provenance, bypass, utilization, and completeness foundation

## Why This Exists

The mandatory OpenAI assistive-plane contract requires an executable, independently evidenced work unit rather than an untracked direct API call.

## Scope

Preserve the merged provider-neutral foundation, then implement and deploy the persistent OS-supervised controller, SQLite WAL state machine, independent read-only watchdog, fail-closed direct-Codex work interlock, immutable pre-routing and changed-path binding, 204-row ownership/evidence evaluator, live inventory, budgets, retries, reconciliation, control CLI/API, backup, rollback, independent no-Codex black-box proof, probation, soak, and cleanup.

### Explicit In Scope

- Perform the exact action: Implement the governed OpenAI controller, storage, budget, provenance, schema, security, and cleanup foundation.
- Use one governed controller, strict Structured Outputs, minimized cited evidence, content-addressed external storage, deterministic validation, and locally enforced cost admission.
- Preserve abstentions, conflicts, schema failures, unsupported facts, partial batch failures, and negative empirical results.

### Explicit Out of Scope

- Any direct model write to canonical data, PIT state, labels, protected evaluation, promotion, forecasts, BAS, Aggie Excess, or publication state.
- Scattered OpenAI API calls, hosted-Evals dependence, prompt ingestion of secrets or whole data lakes, or bypass of the USD 100 ledger hard stop.
- Changing protected requirements, judging rules, split seals, or scientific acceptance thresholds merely to obtain a passing result.
- Treating ordinary delegable PROJECT_WORK as authorized direct-Codex fallback merely because a provider, packet, inventory, adapter, or budget stage is unavailable; only bounded pipeline repair, authority-only, and fixed deterministic operations remain directly eligible while the interlock is closed.

## Prerequisites

- Dependency POST-SUBTASK-040 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-160
- POST-SUBTASK-198

## Blocks

- POST-SUBTASK-202
- POST-SUBTASK-203
- POST-SUBTASK-204

## Read / Inspect First

- governance/OPENAI_ASSISTIVE_PLANE.md
- configs/openai_assist_policy.json
- configs/openai_task_registry.json
- schemas/openai/assistive_candidate.schema.json
- docs/final/CODEX_HANDOFF.md

## Files Expected To Be Modified

- configs/assistive_provider_registry.json
- configs/assistive_route_readiness.json
- configs/unified_assistive_policy.json
- configs/unified_assistive_ready_work.json
- configs/unified_assistive_operational_claims.json
- configs/unified_assistive_acceptance_ownership.json
- configs/codex_usage_interlock_change_manifest.json
- configs/unified_assistive_change_routing_binding.json
- instructions/25_FORT_KNOX_ASSISTIVE_EXECUTION_INTERLOCK.md
- instructions/policies/assistive_execution_interlock.json
- tools/activate_codex_usage_interlock.py
- tools/validate_codex_usage_interlock.py
- tests/test_codex_usage_interlock.py
- src/aggie_analytics/assistive_plane
- tools/adopt_unified_enforcement_package.py
- tools/validate_unified_acceptance_ownership.py
- tools/run_unified_assistive_controller.py
- tools/run_unified_assistive_watchdog.py
- tools/materialize_unified_assistive_inventory.py
- tools/validate_unified_assistive_plane.py
- tools/validate_unified_assistive_completeness.py
- tools/refresh_cursor_catalog.py
- tools/refresh_local_assistive_runtime.py
- tests/test_unified_controller_state.py
- tests/test_unified_assistive_plane.py
- tests/test_unified_assistive_completeness.py
- governance/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md
- governance/SOURCE_OF_TRUTH_MAP.md
- docs/architecture/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md
- docs/operations/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md
- tests/test_unified_inventory_materializer.py
- tests/test_unified_inventory_scheduler.py
- tests/test_unified_runtime_inventory_dispatch.py
- jira/tools/import_bat_live.py
- tests/test_jira_evidence_state_mapping.py
- tests/test_jira_operational_status_policy.py

## Components Expected To Be Touched

- operations-security
- assistive-plane
- orchestration

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

- artifacts/jira_evidence/POST-SUBTASK-201.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-201`
- Inherited from: None
- Resolution: `DIRECT_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 0, "adr_ids": 0, "gap_ids": 0, "requirement_ids": 0, "risk_ids": 0}`

## Acceptance Criteria

1. Inventory validation enforces effort points 1/2/3/5/8, stable identities, anti-padding, one disposition, and complete count/point reconciliation.
2. Readiness binds provider, resolved model and digest, task format, prompt/schema identity, policy version, and execution surface; empirical rejection cannot be overridden by a status edit.
3. Cursor, loopback Ollama, and exact CPU-worker identity policies fail closed; direct endpoint bypasses are detected.
4. A refreshable content-addressed ready-work inventory and separate evidence-derived operational-completeness validator fail stale or overstated dispositions.
5. Credential-safe live catalog/runtime evidence is content-addressed outside Git and all focused/full validators pass through protected integration.
6. The controller and independent watchdog are OS-supervised outside Codex Desktop, recover from crash/restart, agree on maximum justified state, and cannot overclaim partial operation.
7. All 204 acceptance rows map to one canonical/live owner and the runtime validator exits zero only when every mandatory row passes.
8. Undispatched inventory revisions are preserved and may be superseded append-only; active or externally consequential identity changes fail closed without terminating the controller.
9. Inventory derivation semantically validates exact local-model, CPU-worker, Cursor, usage, review, and dispatch-origin evidence instead of treating directory hashes as readiness.
10. The persistent scheduler discovers granular BAS units and durably leases, dispatches, validates, reviews, settles, cleans, closes or requeues them without an active Codex turn.
11. The independent watchdog reports process health separately and fails operational completeness on stale inventory, idle admitted work, zero dispatch, reconciliation gaps, abandoned leases, or unsupported claims.
12. The fail-closed direct-Codex interlock rejects ordinary PROJECT_WORK until an independent two-hour no-Codex black-box test, 24-hour probation, and seven-day soak pass with zero unjustified bypass, positive downstream-consumed useful offload, positive measured savings, and exact-main deployment identity.

## Definition of Done

1. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row and negative findings remain preserved.
2. Every output is content-hashed with source/data/code/config/model/runtime identities and an explicit candidate/review/quarantine/rejected disposition.
3. OpenAI remains optional, store:false, external-storage-only, candidate-only, and unable to alter canonical or protected truth directly.
4. Budget reservations, actual tokens/cost, remaining allocation, cleanup, and unresolved review items are reported without exposing credentials.
5. Repository, provenance, Jira second-pass, secret, PIT/leakage/identity where applicable, and relevant automated tests pass.
6. No historical-completeness, production-readiness, protected-performance, A&M-lift, BAS, Aggie Excess, or scientific-result claim is made from this work alone.
7. Independent immutable evidence passes the two-hour black-box, 24-hour probation, and seven-day soak gates with no manual packet replenishment, no unjustified direct execution, positive downstream-consumed useful offload, positive measured savings, and exact merged-main deployment identity.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `SECURITY` — `tests/test_openai_assist.py` — Credential redaction, store:false, candidate-only authority, strict schemas, budget hard stop, and isolation gates pass.
- **END_TO_END** / `END_TO_END` — `artifacts/jira_evidence/POST-SUBTASK-160.json` — Use fake synchronous and Batch clients to prove a registered cited job is admitted, store:false, strict-schema validated, externally content-addressed, candidate-disposed, cost-settled, cached, and unable to touch protected truth.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Pin policy, prompt, schema, model, reasoning, source, request/response, cost, code, and runtime identities.

## Required Evidence

- `artifacts/jira_evidence/POST-SUBTASK-160.json` with one evidence row per acceptance criterion and exact artifact hashes.
- Request/job/Jira/source/capture/prompt/schema/model/reasoning identities; estimated and actual tokens/cost; validation and disposition.
- Cleanup record for remote files where practical and abandoned local temporary files, plus remaining review/quarantine items.
- Exact commands, exit codes, relevant output, failed/negative cases, and downstream readiness changes.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "budget_ledger_required": true,
  "candidate_only": true,
  "negative_results_preserved": true,
  "protected_nonclaims_required": true,
  "provenance_dimensions": [
    "source",
    "capture",
    "prompt",
    "schema",
    "model",
    "reasoning",
    "code",
    "config",
    "runtime",
    "cost"
  ]
}
```

## End-to-End Validation Requirement

Use fake synchronous and Batch clients to prove a registered cited job is admitted, store:false, strict-schema validated, externally content-addressed, candidate-disposed, cost-settled, cached, and unable to touch protected truth.

## Expected Maturity After Completion

`INTEGRATED`

## Risk / Failure Conditions

- A successful API response is not evidence if schema, evidence, provenance, PIT/leakage, identity, cost, or candidate-authority validation fails.
- The unit fails if any unsupported fact enters canonical data or any name-only/model-only merge is approved.
- The unit fails if cost is admitted beyond an allocation or the absolute USD 100 committed-cost hard stop.
- The unit fails if credentials, .env content, private personal information, or unnecessary protected evidence is exposed.

## Stop Conditions

- Stop only the affected API job on missing evidence, invalid schema, unsupported fact, credential exposure, budget rejection, provider failure, or inaccessible source; continue independent work.
- Quarantine the affected result on contradiction, refusal, malformed output, provenance mismatch, PIT/target leakage, or identity risk.
- Stop and preserve evidence rather than inventing facts, timestamps, metrics, identities, or maturity.

## Source References

- SRCREF-02121

## AI Context Notes

- Canonical unified assistive contract source is `SRCREF-02121`.
- Never expose credentials, .env content, private data, or unnecessary protected evidence.
- Codex and deterministic validators retain canonical, scientific, Git/GitHub, Jira, and publication authority.
- Live Jira synchronization maps the detailed 2020/2018/2019/2021 acquisition checkpoint to the bounded PARTIAL select option while preserving the exact canonical evidence state; unknown non-enumerated states fail closed.

<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-160_implement_the_governed_openai_controller_storage_budget_provenance_schema_security_and_clean.json -->
# POST-SUBTASK-160 — [POST-SUBTASK-160] Implement the governed OpenAI controller, storage, budget, provenance, schema, security, and cleanup foundation

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "One optional controller exclusively owns Responses and Batch calls, model/effort routing, credential loading/redaction, store:false, strict schemas, token/cost estimation, admission, idempotency, retries, caching, provenance, validation, reporting, and cleanup.",
    "Settled plus outstanding reservations hard-stop at USD 100; allocation caps and $25/$50/$75/$90 alerts are locally enforced; low-priority admission stops at $90.",
    "All operational payloads stay under the external OpenAI root; the key is nonempty but never printed, copied, committed, serialized, or prompt-visible.",
    "Fake-client, mutation, secret, isolation, dependency-lock, strict repository, provenance, Jira, and full-suite validation pass before any paid call."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical contract source is `SRCREF-02119`. Read `jira/sources/issue_source_manifests/POST-SUBTASK-160.json` before execution.",
    "Never include an API key, .env content, cookie, authorization header, or whole data lake in prompts, artifacts, logs, worktrees, commits, or Jira.",
    "OpenAI output is candidate evidence only; deterministic project authority retains every acceptance, canonicalization, PIT, scientific, promotion, forecast, and publication decision."
  ],
  "allowed_modification_paths": [
    "pyproject.toml",
    "requirements/openai-assist.lock",
    "configs/openai_assist_policy.json",
    "configs/openai_task_registry.json",
    "schemas/openai/assistive_candidate.schema.json",
    "src/aggie_analytics/openai_assist",
    "tools/openai_assist.py",
    "tools/validate_openai_assist.py",
    "tests/test_openai_assist.py",
    "governance/OPENAI_ASSISTIVE_PLANE.md",
    "docs/architecture/OPENAI_ASSISTIVE_PLANE.md",
    "docs/operations/OPENAI_ASSISTIVE_PLANE.md",
    "artifacts/jira_evidence/POST-SUBTASK-160.json"
  ],
  "blocked_reason": "",
  "blocks": [
    "POST-SUBTASK-161"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-160_implement_the_governed_openai_controller_storage_budget_provenance_schema_security_and_clean.json",
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
    "openai-assist"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row and negative findings remain preserved.",
    "Every output is content-hashed with source/data/code/config/model/runtime identities and an explicit candidate/review/quarantine/rejected disposition.",
    "OpenAI remains optional, store:false, external-storage-only, candidate-only, and unable to alter canonical or protected truth directly.",
    "Budget reservations, actual tokens/cost, remaining allocation, cleanup, and unresolved review items are reported without exposing credentials.",
    "Repository, provenance, Jira second-pass, secret, PIT/leakage/identity where applicable, and relevant automated tests pass.",
    "No historical-completeness, production-readiness, protected-performance, A&M-lift, BAS, Aggie Excess, or scientific-result claim is made from this work alone."
  ],
  "dependencies": [
    "POST-SUBTASK-040"
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
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-160.json",
  "evidence_state": "PLANNED",
  "execution_lane": "SHARED_CONTRACT",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "INTEGRATED",
  "expected_outputs": [
    "configs/openai_assist_policy.json",
    "requirements/openai-assist.lock",
    "src/aggie_analytics/openai_assist/controller.py",
    "artifacts/jira_evidence/POST-SUBTASK-160.json"
  ],
  "files_expected_to_be_read": [
    "governance/OPENAI_ASSISTIVE_PLANE.md",
    "configs/openai_assist_policy.json",
    "configs/openai_task_registry.json",
    "schemas/openai/assistive_candidate.schema.json",
    "docs/final/CODEX_HANDOFF.md"
  ],
  "files_expected_to_be_touched": [
    "pyproject.toml",
    "requirements/openai-assist.lock",
    "configs/openai_assist_policy.json",
    "configs/openai_task_registry.json",
    "schemas/openai/assistive_candidate.schema.json",
    "src/aggie_analytics/openai_assist",
    "tools/openai_assist.py",
    "tools/validate_openai_assist.py",
    "tests/test_openai_assist.py",
    "governance/OPENAI_ASSISTIVE_PLANE.md",
    "docs/architecture/OPENAI_ASSISTIVE_PLANE.md",
    "docs/operations/OPENAI_ASSISTIVE_PLANE.md"
  ],
  "files_to_inspect": [
    "governance/OPENAI_ASSISTIVE_PLANE.md",
    "configs/openai_assist_policy.json",
    "configs/openai_task_registry.json",
    "schemas/openai/assistive_candidate.schema.json",
    "docs/final/CODEX_HANDOFF.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-160_implement_the_governed_openai_controller_storage_budget_provenance_schema_security_and_clean.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-160",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100468,
  "in_scope": [
    "Perform the exact action: Implement the governed OpenAI controller, storage, budget, provenance, schema, security, and cleanup foundation.",
    "Use one governed controller, strict Structured Outputs, minimized cited evidence, content-addressed external storage, deterministic validation, and locally enforced cost admission.",
    "Preserve abstentions, conflicts, schema failures, unsupported facts, partial batch failures, and negative empirical results."
  ],
  "issue_type": "Subtask",
  "jira_key": "",
  "labels": [
    "actionable",
    "openai-assist",
    "post-wave",
    "subtask",
    "controller",
    "security"
  ],
  "last_content_audit": "2026-08-10",
  "local_id": "POST-SUBTASK-160",
  "maturity_before": "NOT_STARTED",
  "objective": "Implement the governed OpenAI controller, storage, budget, provenance, schema, security, and cleanup foundation",
  "out_of_scope": [
    "Any direct model write to canonical data, PIT state, labels, protected evaluation, promotion, forecasts, BAS, Aggie Excess, or publication state.",
    "Scattered OpenAI API calls, hosted-Evals dependence, prompt ingestion of secrets or whole data lakes, or bypass of the USD 100 ledger hard stop.",
    "Changing protected requirements, judging rules, split seals, or scientific acceptance thresholds merely to obtain a passing result.",
    "Blocking historical expansion or deterministic/local work when the optional provider is unavailable."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-054",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-040 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02119"
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
  "record_revision": "2.0",
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
  "scope": "Execute POST-SUBTASK-160 within the optional OpenAI assistive plane. Consume `POST-SUBTASK-040`; produce `configs/openai_assist_policy.json`, `requirements/openai-assist.lock`, `src/aggie_analytics/openai_assist/controller.py`, `artifacts/jira_evidence/POST-SUBTASK-160.json`; preserve the deterministic forecast path and candidate-only authority boundary.",
  "source_ids": [
    "OPENAI-ASSIST-PLAN"
  ],
  "source_refs": [
    "SRCREF-02119"
  ],
  "stop_conditions": [
    "Stop only the affected API job on missing evidence, invalid schema, unsupported fact, credential exposure, budget rejection, provider failure, or inaccessible source; continue independent work.",
    "Quarantine the affected result on contradiction, refusal, malformed output, provenance mismatch, PIT/target leakage, or identity risk.",
    "Stop and preserve evidence rather than inventing facts, timestamps, metrics, identities, or maturity."
  ],
  "supporting_source_refs": [],
  "title": "[POST-SUBTASK-160] Implement the governed OpenAI controller, storage, budget, provenance, schema, security, and cleanup foundation",
  "traceability_inherited_from": [],
  "traceability_resolution": "DIRECT_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "END_TO_END",
    "REPRODUCIBILITY",
    "SECURITY"
  ],
  "why_this_exists": "The mandatory OpenAI assistive-plane contract requires an executable, independently evidenced work unit rather than an untracked direct API call.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-160.md",
  "workflow_state": "IN_PROGRESS"
}
```

## Objective

Implement the governed OpenAI controller, storage, budget, provenance, schema, security, and cleanup foundation

## Why This Exists

The mandatory OpenAI assistive-plane contract requires an executable, independently evidenced work unit rather than an untracked direct API call.

## Scope

Execute POST-SUBTASK-160 within the optional OpenAI assistive plane. Consume `POST-SUBTASK-040`; produce `configs/openai_assist_policy.json`, `requirements/openai-assist.lock`, `src/aggie_analytics/openai_assist/controller.py`, `artifacts/jira_evidence/POST-SUBTASK-160.json`; preserve the deterministic forecast path and candidate-only authority boundary.

### Explicit In Scope

- Perform the exact action: Implement the governed OpenAI controller, storage, budget, provenance, schema, security, and cleanup foundation.
- Use one governed controller, strict Structured Outputs, minimized cited evidence, content-addressed external storage, deterministic validation, and locally enforced cost admission.
- Preserve abstentions, conflicts, schema failures, unsupported facts, partial batch failures, and negative empirical results.

### Explicit Out of Scope

- Any direct model write to canonical data, PIT state, labels, protected evaluation, promotion, forecasts, BAS, Aggie Excess, or publication state.
- Scattered OpenAI API calls, hosted-Evals dependence, prompt ingestion of secrets or whole data lakes, or bypass of the USD 100 ledger hard stop.
- Changing protected requirements, judging rules, split seals, or scientific acceptance thresholds merely to obtain a passing result.
- Blocking historical expansion or deterministic/local work when the optional provider is unavailable.

## Prerequisites

- Dependency POST-SUBTASK-040 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-040

## Blocks

- POST-SUBTASK-161

## Read / Inspect First

- governance/OPENAI_ASSISTIVE_PLANE.md
- configs/openai_assist_policy.json
- configs/openai_task_registry.json
- schemas/openai/assistive_candidate.schema.json
- docs/final/CODEX_HANDOFF.md

## Files Expected To Be Modified

- pyproject.toml
- requirements/openai-assist.lock
- configs/openai_assist_policy.json
- configs/openai_task_registry.json
- schemas/openai/assistive_candidate.schema.json
- src/aggie_analytics/openai_assist
- tools/openai_assist.py
- tools/validate_openai_assist.py
- tests/test_openai_assist.py
- governance/OPENAI_ASSISTIVE_PLANE.md
- docs/architecture/OPENAI_ASSISTIVE_PLANE.md
- docs/operations/OPENAI_ASSISTIVE_PLANE.md

## Components Expected To Be Touched

- operations-security
- openai-assist

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

- configs/openai_assist_policy.json
- requirements/openai-assist.lock
- src/aggie_analytics/openai_assist/controller.py
- artifacts/jira_evidence/POST-SUBTASK-160.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-160`
- Inherited from: None
- Resolution: `DIRECT_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 0, "adr_ids": 0, "gap_ids": 0, "requirement_ids": 0, "risk_ids": 0}`

## Acceptance Criteria

1. One optional controller exclusively owns Responses and Batch calls, model/effort routing, credential loading/redaction, store:false, strict schemas, token/cost estimation, admission, idempotency, retries, caching, provenance, validation, reporting, and cleanup.
2. Settled plus outstanding reservations hard-stop at USD 100; allocation caps and $25/$50/$75/$90 alerts are locally enforced; low-priority admission stops at $90.
3. All operational payloads stay under the external OpenAI root; the key is nonempty but never printed, copied, committed, serialized, or prompt-visible.
4. Fake-client, mutation, secret, isolation, dependency-lock, strict repository, provenance, Jira, and full-suite validation pass before any paid call.

## Definition of Done

1. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row and negative findings remain preserved.
2. Every output is content-hashed with source/data/code/config/model/runtime identities and an explicit candidate/review/quarantine/rejected disposition.
3. OpenAI remains optional, store:false, external-storage-only, candidate-only, and unable to alter canonical or protected truth directly.
4. Budget reservations, actual tokens/cost, remaining allocation, cleanup, and unresolved review items are reported without exposing credentials.
5. Repository, provenance, Jira second-pass, secret, PIT/leakage/identity where applicable, and relevant automated tests pass.
6. No historical-completeness, production-readiness, protected-performance, A&M-lift, BAS, Aggie Excess, or scientific-result claim is made from this work alone.

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

- SRCREF-02119

## AI Context Notes

- Canonical contract source is `SRCREF-02119`. Read `jira/sources/issue_source_manifests/POST-SUBTASK-160.json` before execution.
- Never include an API key, .env content, cookie, authorization header, or whole data lake in prompts, artifacts, logs, worktrees, commits, or Jira.
- OpenAI output is candidate evidence only; deterministic project authority retains every acceptance, canonicalization, PIT, scientific, promotion, forecast, and publication decision.

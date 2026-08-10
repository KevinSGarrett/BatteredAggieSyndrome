<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-166_scale_empirically_validated_formats_reconcile_usage_clean_payloads_and_publish_the_openai_ha.json -->
# POST-SUBTASK-166 — [POST-SUBTASK-166] Scale empirically validated formats, reconcile usage, clean payloads, and publish the OpenAI handoff

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Only pilot formats meeting predeclared empirical rules scale; failed, uneconomic, unsupported, unstable, or high-review formats remain shadow/quarantined/rejected.",
    "Usage reconciles every reservation, synchronous/Batch job, model/effort, token, dollar, allocation, threshold alert, remaining budget, disposition, improvement, and unresolved review.",
    "Remote Batch files are removed after verified local preservation where practical; abandoned local tmp/partial files are removed; immutable accepted evidence remains content-addressed.",
    "All downstream Jira, PR, repository, provenance, secret, PIT/leakage/identity, and full-suite gates pass without any scientific-readiness overclaim."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical contract source is `SRCREF-02119`. Read `jira/sources/issue_source_manifests/POST-SUBTASK-166.json` before execution.",
    "Never include an API key, .env content, cookie, authorization header, or whole data lake in prompts, artifacts, logs, worktrees, commits, or Jira.",
    "OpenAI output is candidate evidence only; deterministic project authority retains every acceptance, canonicalization, PIT, scientific, promotion, forecast, and publication decision."
  ],
  "allowed_modification_paths": [
    "artifacts/openai_assist/final_handoff.json",
    "docs/operations/OPENAI_ASSISTIVE_PLANE.md",
    "artifacts/jira_evidence/POST-SUBTASK-166.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-162;POST-SUBTASK-163;POST-SUBTASK-164",
  "blocks": [],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-166_scale_empirically_validated_formats_reconcile_usage_clean_payloads_and_publish_the_openai_ha.json",
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
  "component": "release-readiness",
  "components_expected_to_be_touched": [
    "release-readiness",
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
    "POST-SUBTASK-162",
    "POST-SUBTASK-163",
    "POST-SUBTASK-164"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 0,
    "adr_ids": 0,
    "gap_ids": 0,
    "requirement_ids": 0,
    "risk_ids": 0
  },
  "effective_traceability_total": 0,
  "end_to_end_validation": "Run the validated scale-out and final reconciliation, demonstrate deterministic fallback on provider failure, clean reconstructible artifacts, and publish an exact resumable handoff with remaining budget.",
  "epic_id": "POST-EPIC-018",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-166.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "OPERATING",
  "expected_outputs": [
    "artifacts/openai_assist/final_handoff.json",
    "artifacts/jira_evidence/POST-SUBTASK-166.json"
  ],
  "files_expected_to_be_read": [
    "governance/OPENAI_ASSISTIVE_PLANE.md",
    "configs/openai_assist_policy.json",
    "configs/openai_task_registry.json",
    "schemas/openai/assistive_candidate.schema.json",
    "docs/final/CODEX_HANDOFF.md"
  ],
  "files_expected_to_be_touched": [
    "artifacts/openai_assist/final_handoff.json",
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
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-166_scale_empirically_validated_formats_reconcile_usage_clean_payloads_and_publish_the_openai_ha.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-166",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100474,
  "in_scope": [
    "Perform the exact action: Scale empirically validated formats, reconcile usage, clean payloads, and publish the OpenAI handoff.",
    "Use one governed controller, strict Structured Outputs, minimized cited evidence, content-addressed external storage, deterministic validation, and locally enforced cost admission.",
    "Preserve abstentions, conflicts, schema failures, unsupported facts, partial batch failures, and negative empirical results."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-522",
  "labels": [
    "actionable",
    "openai-assist",
    "post-wave",
    "subtask",
    "scale-out",
    "handoff"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-166",
  "maturity_before": "NOT_STARTED",
  "objective": "Scale empirically validated formats, reconcile usage, clean payloads, and publish the OpenAI handoff",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24662",
    "jira_updated_at": "2026-08-09T23:18:51.527-0500",
    "last_synced_at": "2026-08-10T04:24:34.496382+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\BAT-516-openai-foundation-complete\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Any direct model write to canonical data, PIT state, labels, protected evaluation, promotion, forecasts, BAS, Aggie Excess, or publication state.",
    "Scattered OpenAI API calls, hosted-Evals dependence, prompt ingestion of secrets or whole data lakes, or bypass of the USD 100 ledger hard stop.",
    "Changing protected requirements, judging rules, split seals, or scientific acceptance thresholds merely to obtain a passing result.",
    "Blocking historical expansion or deterministic/local work when the optional provider is unavailable."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-056",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-162 complete at required maturity",
    "Dependency POST-SUBTASK-163 complete at required maturity",
    "Dependency POST-SUBTASK-164 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02119"
  ],
  "priority": "MUST",
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
    "`artifacts/jira_evidence/POST-SUBTASK-166.json` with one evidence row per acceptance criterion and exact artifact hashes.",
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
      "expectation": "Run the validated scale-out and final reconciliation, demonstrate deterministic fallback on provider failure, clean reconstructible artifacts, and publish an exact resumable handoff with remaining budget.",
      "path": "artifacts/jira_evidence/POST-SUBTASK-166.json",
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
  "scope": "Execute POST-SUBTASK-166 within the optional OpenAI assistive plane. Consume `POST-SUBTASK-162`, `POST-SUBTASK-163`, `POST-SUBTASK-164`; produce `artifacts/openai_assist/final_handoff.json`, `artifacts/jira_evidence/POST-SUBTASK-166.json`; preserve the deterministic forecast path and candidate-only authority boundary.",
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
  "title": "[POST-SUBTASK-166] Scale empirically validated formats, reconcile usage, clean payloads, and publish the OpenAI handoff",
  "traceability_inherited_from": [],
  "traceability_resolution": "DIRECT_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "END_TO_END",
    "REPRODUCIBILITY",
    "SECURITY"
  ],
  "why_this_exists": "The mandatory OpenAI assistive-plane contract requires an executable, independently evidenced work unit rather than an untracked direct API call.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-166.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Scale empirically validated formats, reconcile usage, clean payloads, and publish the OpenAI handoff

## Why This Exists

The mandatory OpenAI assistive-plane contract requires an executable, independently evidenced work unit rather than an untracked direct API call.

## Scope

Execute POST-SUBTASK-166 within the optional OpenAI assistive plane. Consume `POST-SUBTASK-162`, `POST-SUBTASK-163`, `POST-SUBTASK-164`; produce `artifacts/openai_assist/final_handoff.json`, `artifacts/jira_evidence/POST-SUBTASK-166.json`; preserve the deterministic forecast path and candidate-only authority boundary.

### Explicit In Scope

- Perform the exact action: Scale empirically validated formats, reconcile usage, clean payloads, and publish the OpenAI handoff.
- Use one governed controller, strict Structured Outputs, minimized cited evidence, content-addressed external storage, deterministic validation, and locally enforced cost admission.
- Preserve abstentions, conflicts, schema failures, unsupported facts, partial batch failures, and negative empirical results.

### Explicit Out of Scope

- Any direct model write to canonical data, PIT state, labels, protected evaluation, promotion, forecasts, BAS, Aggie Excess, or publication state.
- Scattered OpenAI API calls, hosted-Evals dependence, prompt ingestion of secrets or whole data lakes, or bypass of the USD 100 ledger hard stop.
- Changing protected requirements, judging rules, split seals, or scientific acceptance thresholds merely to obtain a passing result.
- Blocking historical expansion or deterministic/local work when the optional provider is unavailable.

## Prerequisites

- Dependency POST-SUBTASK-162 complete at required maturity
- Dependency POST-SUBTASK-163 complete at required maturity
- Dependency POST-SUBTASK-164 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-162
- POST-SUBTASK-163
- POST-SUBTASK-164

## Blocks

- None.

## Read / Inspect First

- governance/OPENAI_ASSISTIVE_PLANE.md
- configs/openai_assist_policy.json
- configs/openai_task_registry.json
- schemas/openai/assistive_candidate.schema.json
- docs/final/CODEX_HANDOFF.md

## Files Expected To Be Modified

- artifacts/openai_assist/final_handoff.json
- docs/operations/OPENAI_ASSISTIVE_PLANE.md

## Components Expected To Be Touched

- release-readiness
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

- artifacts/openai_assist/final_handoff.json
- artifacts/jira_evidence/POST-SUBTASK-166.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-166`
- Inherited from: None
- Resolution: `DIRECT_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 0, "adr_ids": 0, "gap_ids": 0, "requirement_ids": 0, "risk_ids": 0}`

## Acceptance Criteria

1. Only pilot formats meeting predeclared empirical rules scale; failed, uneconomic, unsupported, unstable, or high-review formats remain shadow/quarantined/rejected.
2. Usage reconciles every reservation, synchronous/Batch job, model/effort, token, dollar, allocation, threshold alert, remaining budget, disposition, improvement, and unresolved review.
3. Remote Batch files are removed after verified local preservation where practical; abandoned local tmp/partial files are removed; immutable accepted evidence remains content-addressed.
4. All downstream Jira, PR, repository, provenance, secret, PIT/leakage/identity, and full-suite gates pass without any scientific-readiness overclaim.

## Definition of Done

1. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row and negative findings remain preserved.
2. Every output is content-hashed with source/data/code/config/model/runtime identities and an explicit candidate/review/quarantine/rejected disposition.
3. OpenAI remains optional, store:false, external-storage-only, candidate-only, and unable to alter canonical or protected truth directly.
4. Budget reservations, actual tokens/cost, remaining allocation, cleanup, and unresolved review items are reported without exposing credentials.
5. Repository, provenance, Jira second-pass, secret, PIT/leakage/identity where applicable, and relevant automated tests pass.
6. No historical-completeness, production-readiness, protected-performance, A&M-lift, BAS, Aggie Excess, or scientific-result claim is made from this work alone.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `SECURITY` — `tests/test_openai_assist.py` — Credential redaction, store:false, candidate-only authority, strict schemas, budget hard stop, and isolation gates pass.
- **END_TO_END** / `END_TO_END` — `artifacts/jira_evidence/POST-SUBTASK-166.json` — Run the validated scale-out and final reconciliation, demonstrate deterministic fallback on provider failure, clean reconstructible artifacts, and publish an exact resumable handoff with remaining budget.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Pin policy, prompt, schema, model, reasoning, source, request/response, cost, code, and runtime identities.

## Required Evidence

- `artifacts/jira_evidence/POST-SUBTASK-166.json` with one evidence row per acceptance criterion and exact artifact hashes.
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

Run the validated scale-out and final reconciliation, demonstrate deterministic fallback on provider failure, clean reconstructible artifacts, and publish an exact resumable handoff with remaining budget.

## Expected Maturity After Completion

`OPERATING`

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

- Canonical contract source is `SRCREF-02119`. Read `jira/sources/issue_source_manifests/POST-SUBTASK-166.json` before execution.
- Never include an API key, .env content, cookie, authorization header, or whole data lake in prompts, artifacts, logs, worktrees, commits, or Jira.
- OpenAI output is candidate evidence only; deterministic project authority retains every acceptance, canonicalization, PIT, scientific, promotion, forecast, and publication decision.

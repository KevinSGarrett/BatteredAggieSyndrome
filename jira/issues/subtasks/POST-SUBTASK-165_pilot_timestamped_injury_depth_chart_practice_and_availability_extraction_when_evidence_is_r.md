<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-165_pilot_timestamped_injury_depth_chart_practice_and_availability_extraction_when_evidence_is_r.json -->
# POST-SUBTASK-165 — [POST-SUBTASK-165] Pilot timestamped injury, depth-chart, practice, and availability extraction when evidence is ready

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Suitable public evidence has source URL, immutable capture, acquisition/known-at timestamp, exact excerpt, player/team identity context, and target-game cutoff eligibility before activation.",
    "The model never fabricates known-at time, status, player identity, role, injury, participation, or missing availability evidence.",
    "Accepted candidate facts pass deterministic identity, provenance, PIT, target-leakage, and availability-domain validation."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical contract source is `SRCREF-02119`. Read `jira/sources/issue_source_manifests/POST-SUBTASK-165.json` before execution.",
    "Never include an API key, .env content, cookie, authorization header, or whole data lake in prompts, artifacts, logs, worktrees, commits, or Jira.",
    "OpenAI output is candidate evidence only; deterministic project authority retains every acceptance, canonicalization, PIT, scientific, promotion, forecast, and publication decision."
  ],
  "allowed_modification_paths": [
    "configs/openai_task_registry.json",
    "artifacts/openai_assist/availability_pilot.json",
    "tests/test_openai_assist.py",
    "artifacts/jira_evidence/POST-SUBTASK-165.json"
  ],
  "blocked_reason": "DEFERRED_PENDING_TIMESTAMPED_EVIDENCE",
  "blocks": [
    "POST-SUBTASK-170"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-165_pilot_timestamped_injury_depth_chart_practice_and_availability_extraction_when_evidence_is_r.json",
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
  "component": "player-context-intelligence",
  "components_expected_to_be_touched": [
    "player-context-intelligence",
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
    "POST-SUBTASK-161",
    "POST-SUBTASK-028"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 0,
    "adr_ids": 0,
    "gap_ids": 0,
    "requirement_ids": 0,
    "risk_ids": 0
  },
  "effective_traceability_total": 0,
  "end_to_end_validation": "When timestamped evidence is ready, run a bounded shadow extraction and prove every accepted availability fact is evidence-backed and cutoff-eligible; otherwise retain the exact deferred finding.",
  "epic_id": "POST-EPIC-018",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-165.json",
  "evidence_state": "PLANNED",
  "execution_lane": "RESEARCH_LANE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "EMPIRICALLY_VALIDATED",
  "expected_outputs": [
    "artifacts/openai_assist/availability_pilot.json",
    "artifacts/jira_evidence/POST-SUBTASK-165.json"
  ],
  "files_expected_to_be_read": [
    "governance/OPENAI_ASSISTIVE_PLANE.md",
    "configs/openai_assist_policy.json",
    "configs/openai_task_registry.json",
    "schemas/openai/assistive_candidate.schema.json",
    "docs/final/CODEX_HANDOFF.md"
  ],
  "files_expected_to_be_touched": [
    "configs/openai_task_registry.json",
    "artifacts/openai_assist/availability_pilot.json",
    "tests/test_openai_assist.py"
  ],
  "files_to_inspect": [
    "governance/OPENAI_ASSISTIVE_PLANE.md",
    "configs/openai_assist_policy.json",
    "configs/openai_task_registry.json",
    "schemas/openai/assistive_candidate.schema.json",
    "docs/final/CODEX_HANDOFF.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-165_pilot_timestamped_injury_depth_chart_practice_and_availability_extraction_when_evidence_is_r.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-165",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100473,
  "in_scope": [
    "Perform the exact action: Pilot timestamped injury, depth-chart, practice, and availability extraction when evidence is ready.",
    "Use one governed controller, strict Structured Outputs, minimized cited evidence, content-addressed external storage, deterministic validation, and locally enforced cost admission.",
    "Preserve abstentions, conflicts, schema failures, unsupported facts, partial batch failures, and negative empirical results."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-521",
  "labels": [
    "actionable",
    "openai-assist",
    "post-wave",
    "subtask",
    "pilot-d",
    "conditional",
    "availability"
  ],
  "last_content_audit": "2026-08-10",
  "local_id": "POST-SUBTASK-165",
  "maturity_before": "NOT_STARTED",
  "objective": "Pilot timestamped injury, depth-chart, practice, and availability extraction when evidence is ready",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24661",
    "jira_updated_at": "2026-08-11T01:07:02.535-0500",
    "last_synced_at": "2026-08-11T07:25:49.170544+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\POST-SUBTASK-178-wmt-known-at\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
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
  "parent_id": "POST-STORY-055",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-161 complete at required maturity",
    "Dependency POST-SUBTASK-028 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02119"
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
    "governance/OPENAI_ASSISTIVE_PLANE.md",
    "configs/openai_assist_policy.json",
    "configs/openai_task_registry.json",
    "schemas/openai/assistive_candidate.schema.json",
    "docs/final/CODEX_HANDOFF.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "required_evidence": [
    "`artifacts/jira_evidence/POST-SUBTASK-165.json` with one evidence row per acceptance criterion and exact artifact hashes.",
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
      "expectation": "When timestamped evidence is ready, run a bounded shadow extraction and prove every accepted availability fact is evidence-backed and cutoff-eligible; otherwise retain the exact deferred finding.",
      "path": "artifacts/jira_evidence/POST-SUBTASK-165.json",
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
  "scope": "Execute POST-SUBTASK-165 within the optional OpenAI assistive plane. Consume `POST-SUBTASK-161`, `POST-SUBTASK-028`; produce `artifacts/openai_assist/availability_pilot.json`, `artifacts/jira_evidence/POST-SUBTASK-165.json`; preserve the deterministic forecast path and candidate-only authority boundary.",
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
  "title": "[POST-SUBTASK-165] Pilot timestamped injury, depth-chart, practice, and availability extraction when evidence is ready",
  "traceability_inherited_from": [],
  "traceability_resolution": "DIRECT_DOMAIN_GATE",
  "unblock_condition": "Activate only when suitable timestamped injury/availability evidence is ready.",
  "validation_classes": [
    "END_TO_END",
    "REPRODUCIBILITY",
    "SECURITY"
  ],
  "why_this_exists": "The mandatory OpenAI assistive-plane contract requires an executable, independently evidenced work unit rather than an untracked direct API call.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-165.md",
  "workflow_state": "DEFERRED"
}
```

## Objective

Pilot timestamped injury, depth-chart, practice, and availability extraction when evidence is ready

## Why This Exists

The mandatory OpenAI assistive-plane contract requires an executable, independently evidenced work unit rather than an untracked direct API call.

## Scope

Execute POST-SUBTASK-165 within the optional OpenAI assistive plane. Consume `POST-SUBTASK-161`, `POST-SUBTASK-028`; produce `artifacts/openai_assist/availability_pilot.json`, `artifacts/jira_evidence/POST-SUBTASK-165.json`; preserve the deterministic forecast path and candidate-only authority boundary.

### Explicit In Scope

- Perform the exact action: Pilot timestamped injury, depth-chart, practice, and availability extraction when evidence is ready.
- Use one governed controller, strict Structured Outputs, minimized cited evidence, content-addressed external storage, deterministic validation, and locally enforced cost admission.
- Preserve abstentions, conflicts, schema failures, unsupported facts, partial batch failures, and negative empirical results.

### Explicit Out of Scope

- Any direct model write to canonical data, PIT state, labels, protected evaluation, promotion, forecasts, BAS, Aggie Excess, or publication state.
- Scattered OpenAI API calls, hosted-Evals dependence, prompt ingestion of secrets or whole data lakes, or bypass of the USD 100 ledger hard stop.
- Changing protected requirements, judging rules, split seals, or scientific acceptance thresholds merely to obtain a passing result.
- Blocking historical expansion or deterministic/local work when the optional provider is unavailable.

## Prerequisites

- Dependency POST-SUBTASK-161 complete at required maturity
- Dependency POST-SUBTASK-028 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-161
- POST-SUBTASK-028

## Blocks

- POST-SUBTASK-170

## Read / Inspect First

- governance/OPENAI_ASSISTIVE_PLANE.md
- configs/openai_assist_policy.json
- configs/openai_task_registry.json
- schemas/openai/assistive_candidate.schema.json
- docs/final/CODEX_HANDOFF.md

## Files Expected To Be Modified

- configs/openai_task_registry.json
- artifacts/openai_assist/availability_pilot.json
- tests/test_openai_assist.py

## Components Expected To Be Touched

- player-context-intelligence
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

- artifacts/openai_assist/availability_pilot.json
- artifacts/jira_evidence/POST-SUBTASK-165.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-165`
- Inherited from: None
- Resolution: `DIRECT_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 0, "adr_ids": 0, "gap_ids": 0, "requirement_ids": 0, "risk_ids": 0}`

## Acceptance Criteria

1. Suitable public evidence has source URL, immutable capture, acquisition/known-at timestamp, exact excerpt, player/team identity context, and target-game cutoff eligibility before activation.
2. The model never fabricates known-at time, status, player identity, role, injury, participation, or missing availability evidence.
3. Accepted candidate facts pass deterministic identity, provenance, PIT, target-leakage, and availability-domain validation.

## Definition of Done

1. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row and negative findings remain preserved.
2. Every output is content-hashed with source/data/code/config/model/runtime identities and an explicit candidate/review/quarantine/rejected disposition.
3. OpenAI remains optional, store:false, external-storage-only, candidate-only, and unable to alter canonical or protected truth directly.
4. Budget reservations, actual tokens/cost, remaining allocation, cleanup, and unresolved review items are reported without exposing credentials.
5. Repository, provenance, Jira second-pass, secret, PIT/leakage/identity where applicable, and relevant automated tests pass.
6. No historical-completeness, production-readiness, protected-performance, A&M-lift, BAS, Aggie Excess, or scientific-result claim is made from this work alone.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `SECURITY` — `tests/test_openai_assist.py` — Credential redaction, store:false, candidate-only authority, strict schemas, budget hard stop, and isolation gates pass.
- **END_TO_END** / `END_TO_END` — `artifacts/jira_evidence/POST-SUBTASK-165.json` — When timestamped evidence is ready, run a bounded shadow extraction and prove every accepted availability fact is evidence-backed and cutoff-eligible; otherwise retain the exact deferred finding.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Pin policy, prompt, schema, model, reasoning, source, request/response, cost, code, and runtime identities.

## Required Evidence

- `artifacts/jira_evidence/POST-SUBTASK-165.json` with one evidence row per acceptance criterion and exact artifact hashes.
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

When timestamped evidence is ready, run a bounded shadow extraction and prove every accepted availability fact is evidence-backed and cutoff-eligible; otherwise retain the exact deferred finding.

## Expected Maturity After Completion

`EMPIRICALLY_VALIDATED`

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

- Canonical contract source is `SRCREF-02119`. Read `jira/sources/issue_source_manifests/POST-SUBTASK-165.json` before execution.
- Never include an API key, .env content, cookie, authorization header, or whole data lake in prompts, artifacts, logs, worktrees, commits, or Jira.
- OpenAI output is candidate evidence only; deterministic project authority retains every acceptance, canonicalization, PIT, scientific, promotion, forecast, and publication decision.

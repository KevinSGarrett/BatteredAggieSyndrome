from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
JIRA = ROOT / "jira"
SOURCE_REF = "SRCREF-02119"
CONTRACT = ROOT / "governance" / "OPENAI_ASSISTIVE_PLANE.md"

COMPLETED_EVIDENCE = {
    "POST-SUBTASK-160": "INTEGRATED",
    "POST-SUBTASK-161": "EMPIRICALLY_VALIDATED",
    "POST-SUBTASK-162": "EMPIRICALLY_VALIDATED",
    "POST-SUBTASK-163": "EMPIRICALLY_VALIDATED",
    "POST-SUBTASK-164": "EMPIRICALLY_VALIDATED",
    "POST-SUBTASK-166": "OPERATING",
}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:92]


def record_path(issue_type: str, local_id: str, objective: str) -> Path:
    folder = {"Epic": "epics", "Story": "stories", "Subtask": "subtasks"}[issue_type]
    return JIRA / "records" / "issues" / folder / f"{local_id}_{slug(objective)}.json"


def artifact(local_id: str) -> str:
    return f"artifacts/jira_evidence/{local_id}.json"


PROTECTED = [
    "AGENTS.md",
    "governance/DO_NOT_DRIFT.md",
    "governance/PROTECTED_ACCEPTANCE_RULES.md",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "governance/THRESHOLD_PRECOMMITMENT_REGISTRY.csv",
    "configs/judging_rule_seal.json",
    "docs/45_SCIENTIFIC_BAS_SPECIFICATION.md",
]

READ = [
    "governance/OPENAI_ASSISTIVE_PLANE.md",
    "configs/openai_assist_policy.json",
    "configs/openai_task_registry.json",
    "schemas/openai/assistive_candidate.schema.json",
    "docs/final/CODEX_HANDOFF.md",
]


def make(
    *,
    local_id: str,
    import_id: int,
    issue_type: str,
    objective: str,
    parent_id: str,
    epic_id: str,
    dependencies: list[str],
    component: str,
    lane: str,
    outputs: list[str],
    touched: list[str],
    acceptance: list[str],
    end_to_end: str,
    maturity: str,
    labels: list[str],
    conditional: bool = False,
) -> dict[str, Any]:
    path = record_path(issue_type, local_id, objective)
    is_atomic = issue_type == "Subtask"
    title = f"[{local_id}] {objective}"
    dependencies_text = ", ".join(f"`{item}`" for item in dependencies) or "no hard prerequisite"
    common_dod = [
        "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row and negative findings remain preserved.",
        "Every output is content-hashed with source/data/code/config/model/runtime identities and an explicit candidate/review/quarantine/rejected disposition.",
        "OpenAI remains optional, store:false, external-storage-only, candidate-only, and unable to alter canonical or protected truth directly.",
        "Budget reservations, actual tokens/cost, remaining allocation, cleanup, and unresolved review items are reported without exposing credentials.",
        "Repository, provenance, Jira second-pass, secret, PIT/leakage/identity where applicable, and relevant automated tests pass.",
        "No historical-completeness, production-readiness, protected-performance, A&M-lift, BAS, Aggie Excess, or scientific-result claim is made from this work alone.",
    ]
    tests = [
        {
            "classification": "EXISTING_AUTOMATED_TEST",
            "validation_class": "SECURITY",
            "path": "tests/test_openai_assist.py",
            "expectation": "Credential redaction, store:false, candidate-only authority, strict schemas, budget hard stop, and isolation gates pass.",
        },
        {
            "classification": "END_TO_END",
            "validation_class": "END_TO_END",
            "path": outputs[-1] if outputs else artifact(local_id),
            "expectation": end_to_end,
        },
        {
            "classification": "REPRODUCIBILITY",
            "validation_class": "REPRODUCIBILITY",
            "path": "ISSUE_COMPLETION_MANIFEST",
            "expectation": "Pin policy, prompt, schema, model, reasoning, source, request/response, cost, code, and runtime identities.",
        },
    ]
    record = {
        "schema_version": 2,
        "record_revision": "2.0",
        "content_contract_version": "2.0",
        "local_id": local_id,
        "jira_key": "",
        "import_id": import_id,
        "issue_type": issue_type,
        "title": title,
        "parent_id": parent_id,
        "epic_id": epic_id,
        "phase": "PHASE-1",
        "workflow_state": "DEFERRED" if conditional else ("IN_PROGRESS" if local_id == "POST-SUBTASK-168" else "BACKLOG"),
        "historical_classification": "ACTIONABLE_POST_WAVE",
        "priority": "P1" if conditional else "P0",
        "critical_path": False,
        "owner_wave": "POST_W25",
        "source_ids": ["OPENAI-ASSIST-PLAN"],
        "objective": objective,
        "why_this_exists": "The mandatory OpenAI assistive-plane contract requires an executable, independently evidenced work unit rather than an untracked direct API call.",
        "scope": f"Execute {local_id} within the optional OpenAI assistive plane. Consume {dependencies_text}; produce {', '.join(f'`{item}`' for item in outputs)}; preserve the deterministic forecast path and candidate-only authority boundary.",
        "in_scope": [
            f"Perform the exact action: {objective}.",
            "Use one governed controller, strict Structured Outputs, minimized cited evidence, content-addressed external storage, deterministic validation, and locally enforced cost admission.",
            "Preserve abstentions, conflicts, schema failures, unsupported facts, partial batch failures, and negative empirical results.",
        ],
        "out_of_scope": [
            "Any direct model write to canonical data, PIT state, labels, protected evaluation, promotion, forecasts, BAS, Aggie Excess, or publication state.",
            "Scattered OpenAI API calls, hosted-Evals dependence, prompt ingestion of secrets or whole data lakes, or bypass of the USD 100 ledger hard stop.",
            "Changing protected requirements, judging rules, split seals, or scientific acceptance thresholds merely to obtain a passing result.",
            "Blocking historical expansion or deterministic/local work when the optional provider is unavailable.",
        ],
        "prerequisites": [f"Dependency {item} complete at required maturity" for item in dependencies],
        "dependencies": dependencies,
        "blocks": [],
        "files_expected_to_be_read": READ,
        "files_to_inspect": READ,
        "files_expected_to_be_touched": touched,
        "protected_files_and_interfaces": PROTECTED,
        "expected_outputs": outputs,
        "requirement_ids": [],
        "acceptance_control_ids": [],
        "adr_ids": [],
        "risk_ids": [],
        "gap_ids": [],
        "acceptance_criteria": acceptance,
        "definition_of_done": common_dod,
        "required_tests": tests,
        "validation_classes": sorted({test["validation_class"] for test in tests}),
        "required_evidence": [
            f"`{artifact(local_id)}` with one evidence row per acceptance criterion and exact artifact hashes.",
            "Request/job/Jira/source/capture/prompt/schema/model/reasoning identities; estimated and actual tokens/cost; validation and disposition.",
            "Cleanup record for remote files where practical and abandoned local temporary files, plus remaining review/quarantine items.",
            "Exact commands, exit codes, relevant output, failed/negative cases, and downstream readiness changes.",
        ],
        "end_to_end_validation": end_to_end,
        "maturity_before": "NOT_STARTED",
        "expected_maturity_after_completion": maturity,
        "evidence_state": "PLANNED",
        "risk_failure_conditions": [
            "A successful API response is not evidence if schema, evidence, provenance, PIT/leakage, identity, cost, or candidate-authority validation fails.",
            "The unit fails if any unsupported fact enters canonical data or any name-only/model-only merge is approved.",
            "The unit fails if cost is admitted beyond an allocation or the absolute USD 100 committed-cost hard stop.",
            "The unit fails if credentials, .env content, private personal information, or unnecessary protected evidence is exposed.",
        ],
        "stop_conditions": [
            "Stop only the affected API job on missing evidence, invalid schema, unsupported fact, credential exposure, budget rejection, provider failure, or inaccessible source; continue independent work.",
            "Quarantine the affected result on contradiction, refusal, malformed output, provenance mismatch, PIT/target leakage, or identity risk.",
            "Stop and preserve evidence rather than inventing facts, timestamps, metrics, identities, or maturity.",
        ],
        "source_refs": [SOURCE_REF],
        "labels": ["actionable", "openai-assist", "post-wave", *( ["subtask"] if is_atomic else []), *labels],
        "component": component,
        "components_expected_to_be_touched": [component, "openai-assist"],
        "execution_lane": lane,
        "execution_mode": "ATOMIC_EXECUTION" if is_atomic else "AGGREGATE_GATE",
        "ready": False,
        "blocked_reason": "DEFERRED_PENDING_TIMESTAMPED_EVIDENCE" if conditional else "",
        "unblock_condition": "Activate only when suitable timestamped injury/availability evidence is ready." if conditional else "",
        "ai_context_notes": [
            f"Canonical contract source is `{SOURCE_REF}`. Read `jira/sources/issue_source_manifests/{local_id}.json` before execution.",
            "Never include an API key, .env content, cookie, authorization header, or whole data lake in prompts, artifacts, logs, worktrees, commits, or Jira.",
            "OpenAI output is candidate evidence only; deterministic project authority retains every acceptance, canonicalization, PIT, scientific, promotion, forecast, and publication decision.",
        ],
        "canonical_record": path.relative_to(ROOT).as_posix(),
        "generated_markdown": f"jira/issues/{path.parent.name}/{path.stem}.md",
        "work_packet_path": f"jira/ai/work_packets/{local_id}.md",
        "evidence_manifest_path": artifact(local_id),
        "allowed_modification_paths": [*touched, artifact(local_id)] if is_atomic else [artifact(local_id)],
        "completion_evidence_contract": {
            "acceptance_matrix_required": True,
            "artifact_hashes_required": True,
            "negative_results_preserved": True,
            "candidate_only": True,
            "budget_ledger_required": True,
            "protected_nonclaims_required": True,
            "provenance_dimensions": ["source", "capture", "prompt", "schema", "model", "reasoning", "code", "config", "runtime", "cost"],
        },
        "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
        "governance_review_required": False,
        "protected_change_required": False,
        "effective_traceability_counts": {"requirement_ids": 0, "acceptance_control_ids": 0, "adr_ids": 0, "risk_ids": 0, "gap_ids": 0},
        "effective_traceability_total": 0,
        "traceability_inherited_from": [],
        "traceability_resolution": "DIRECT_DOMAIN_GATE",
        "primary_source_refs": [SOURCE_REF],
        "supporting_source_refs": [],
        "read_only_context_paths": [*PROTECTED, *READ],
        "last_content_audit": date.today().isoformat(),
    }
    if issue_type == "Epic":
        record["completion_evidence_contract"]["story_gates"] = ["POST-SUBTASK-160", "POST-SUBTASK-161", "POST-SUBTASK-166"]
        record["governance_traceability_gate"] = "POST-SUBTASK-166"
    elif issue_type == "Story":
        record["governance_traceability_gate"] = dependencies[-1] if dependencies else "POST-SUBTASK-166"
    else:
        record["governance_traceability_gate"] = local_id
    if local_id in COMPLETED_EVIDENCE:
        evidence_path = ROOT / artifact(local_id)
        if not evidence_path.is_file():
            raise RuntimeError(f"completion evidence is absent for {local_id}: {evidence_path}")
        record["workflow_state"] = "DONE"
        record["evidence_state"] = "VERIFIED"
        record["maturity_before"] = COMPLETED_EVIDENCE[local_id]
        record["ready"] = False
        record["blocked_reason"] = ""
        record["completion_evidence_manifest_sha256"] = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    return record


def specs() -> list[dict[str, Any]]:
    return [
        make(local_id="POST-EPIC-018", import_id=100464, issue_type="Epic", objective="Governed optional OpenAI assistive research and data engineering plane", parent_id="", epic_id="", dependencies=["POST-SUBTASK-040"], component="data-sources", lane="SHARED_CONTRACT", outputs=[artifact("POST-EPIC-018")], touched=[], acceptance=["Every child foundation, evaluation, pilot, conditional, scale-out, budget, provenance, and cleanup unit has an evidence-backed disposition.", "The optional plane demonstrably improves at least one bounded workflow without entering the deterministic forecast-critical path."], end_to_end="Aggregate the foundation, evaluation, bounded-pilot, scale-out, budget, cleanup, and authority evidence and prove the optional plane remains safe and useful.", maturity="EMPIRICALLY_VALIDATED", labels=["aggregate-gate"]),
        make(local_id="POST-STORY-054", import_id=100465, issue_type="Story", objective="Governance, storage, budget, controller, and local evaluation foundation", parent_id="POST-EPIC-018", epic_id="POST-EPIC-018", dependencies=["POST-SUBTASK-040"], component="operations-security", lane="SHARED_CONTRACT", outputs=[artifact("POST-STORY-054")], touched=[], acceptance=["The single controller and local evaluation harness satisfy the complete Section 16 authority, storage, schema, budget, provenance, isolation, and cleanup contract.", "No paid call occurs until foundation validation and normal review integration pass."], end_to_end="Integrate POST-SUBTASK-160 and POST-SUBTASK-161 and prove every later API job is forced through their controller, ledger, schema, validation, and evaluation boundaries.", maturity="INTEGRATED", labels=["aggregate-gate"]),
        make(local_id="POST-STORY-055", import_id=100466, issue_type="Story", objective="Bounded OpenAI assistive extraction, entity, quarantine, and availability pilots", parent_id="POST-EPIC-018", epic_id="POST-EPIC-018", dependencies=["POST-SUBTASK-161"], component="data-sources", lane="RESEARCH_LANE", outputs=[artifact("POST-STORY-055")], touched=[], acceptance=["Pilots A-C and the official depth-chart document extension receive empirical gold/reference/cheaper-model comparisons, including meaningful Terra/Sol references and Nano/task-specific inexpensive routes, with candidate-only dispositions; Pilot D remains conditional until timestamped evidence exists.", "Unsupported facts, false merges, leakage, and fabricated timestamps/statistics remain zero for accepted candidates."], end_to_end="Compare all bounded pilot evidence, preserve failures and abstentions, and decide per format whether Nano Batch, a measured 4o Mini/Luna route, Terra complex review, Sol hard residue, deterministic-only, or rejection is justified by accepted evidence-verified records per dollar.", maturity="EMPIRICALLY_VALIDATED", labels=["aggregate-gate"]),
        make(local_id="POST-STORY-056", import_id=100467, issue_type="Story", objective="Empirical OpenAI scale-out, continuing operations, usage accounting, cleanup, and handoff", parent_id="POST-EPIC-018", epic_id="POST-EPIC-018", dependencies=["POST-SUBTASK-162", "POST-SUBTASK-163", "POST-SUBTASK-164", "POST-SUBTASK-167", "POST-SUBTASK-168"], component="release-readiness", lane="PROTECTED_GATE", outputs=[artifact("POST-STORY-056")], touched=[], acceptance=["Only empirically validated routine formats scale to GPT-5 Nano Batch, with task-specific 4o Mini/Luna use measured, complex ambiguity routed to Terra, and a small hard/high-risk residue routed to Sol under staged and model-cap admission.", "BAT-522 is a completed scale-out decision, not the terminal end of API use; bounded candidate-only assistance continues whenever the admission contract is satisfied.", "Handoff reports exact jobs, models, efforts, tokens, dollars, remaining budget, dispositions, improvements, cleanup, and unresolved reviews."], end_to_end="Prove scale-out and continuing candidate-only operations remain inside empirical acceptance, candidate authority, staged/model-cap budget, storage, cleanup, and protected-nonclaim boundaries.", maturity="EMPIRICALLY_VALIDATED", labels=["aggregate-gate"]),
        make(local_id="POST-SUBTASK-160", import_id=100468, issue_type="Subtask", objective="Implement the governed OpenAI controller, storage, budget, provenance, schema, security, and cleanup foundation", parent_id="POST-STORY-054", epic_id="POST-EPIC-018", dependencies=["POST-SUBTASK-040"], component="operations-security", lane="SHARED_CONTRACT", outputs=["configs/openai_assist_policy.json", "requirements/openai-assist.lock", "src/aggie_analytics/openai_assist/controller.py", artifact("POST-SUBTASK-160")], touched=["pyproject.toml", "requirements/openai-assist.lock", "configs/openai_assist_policy.json", "configs/openai_task_registry.json", "schemas/openai/assistive_candidate.schema.json", "src/aggie_analytics/openai_assist", "tools/openai_assist.py", "tools/validate_openai_assist.py", "tests/test_openai_assist.py", "governance/OPENAI_ASSISTIVE_PLANE.md", "docs/architecture/OPENAI_ASSISTIVE_PLANE.md", "docs/operations/OPENAI_ASSISTIVE_PLANE.md"], acceptance=["One optional controller exclusively owns Responses and Batch calls, model/effort routing, credential loading/redaction, store:false, strict schemas, token/cost estimation, admission, idempotency, retries, caching, provenance, validation, reporting, and cleanup.", "Settled plus outstanding reservations hard-stop at USD 100; allocation caps and $25/$50/$75/$90 alerts are locally enforced; low-priority admission stops at $90.", "All operational payloads stay under the external OpenAI root; the key is nonempty but never printed, copied, committed, serialized, or prompt-visible.", "Fake-client, mutation, secret, isolation, dependency-lock, strict repository, provenance, Jira, and full-suite validation pass before any paid call."], end_to_end="Use fake synchronous and Batch clients to prove a registered cited job is admitted, store:false, strict-schema validated, externally content-addressed, candidate-disposed, cost-settled, cached, and unable to touch protected truth.", maturity="INTEGRATED", labels=["controller", "security"]),
        make(local_id="POST-SUBTASK-161", import_id=100469, issue_type="Subtask", objective="Build the local gold corpus and evaluation harness and compare Luna, Terra, and Sol", parent_id="POST-STORY-054", epic_id="POST-EPIC-018", dependencies=["POST-SUBTASK-160"], component="validation-promotion", lane="RESEARCH_LANE", outputs=["fixtures/openai_assist/eval_gold.jsonl", "artifacts/openai_assist/model_comparison.json", artifact("POST-SUBTASK-161")], touched=["fixtures/openai_assist", "src/aggie_analytics/openai_assist/evals.py", "artifacts/openai_assist/model_comparison.json", "tests/test_openai_assist.py"], acceptance=["The corpus covers positive, negative, ambiguous, conflicting, schema-drift, PIT-sensitive, target-leakage, abstention, evidence, and entity-merge cases.", "Luna, Terra, and Sol run at explicit allowed efforts on identical pinned cases and report schema validity, precision/recall, evidence accuracy, abstention, unsupported facts, top-k recall, false merges, repeat consistency, disagreement, cost, review time, and quarantine.", "Task-specific acceptance rules are predeclared from empirical distributions; no threshold is invented merely to approve a model."], end_to_end="Run the versioned local harness over capable-model reference and cheaper routes, preserve raw external results and costs, and publish only a small comparison manifest and empirical route decision.", maturity="EMPIRICALLY_VALIDATED", labels=["evaluation", "gold-set"]),
        make(local_id="POST-SUBTASK-162", import_id=100470, issue_type="Subtask", objective="Pilot historical gamebook-equivalent extraction in shadow candidate mode", parent_id="POST-STORY-055", epic_id="POST-EPIC-018", dependencies=["POST-SUBTASK-161", "POST-SUBTASK-028"], component="data-sources", lane="RESEARCH_LANE", outputs=["artifacts/openai_assist/gamebook_pilot.json", artifact("POST-SUBTASK-162")], touched=["configs/openai_task_registry.json", "artifacts/openai_assist/gamebook_pilot.json", "tests/test_openai_assist.py"], acceptance=["A pinned human/deterministic gold sample covers drives, plays, box scores, roster/starter facts, venue, officials, weather, attendance, and source metadata with exact evidence locators.", "Terra capable reference is compared with Luna; only empirically validated routine formats may be proposed for Luna Batch and only ambiguous residue may reach Terra/Sol.", "Accepted candidates retain exact source/capture evidence and pass deterministic schema, provenance, identity, PIT, leakage, and domain validation with zero unsupported facts."], end_to_end="Extract a bounded real historical gamebook sample through the controller, validate every fact against exact source evidence, and measure accepted records, review time, quarantines, cost, and unsupported-fact rate without canonical mutation.", maturity="EMPIRICALLY_VALIDATED", labels=["pilot-a", "gamebook"]),
        make(local_id="POST-SUBTASK-163", import_id=100471, issue_type="Subtask", objective="Pilot unresolved entity candidate ranking and evidence explanation without merge authority", parent_id="POST-STORY-055", epic_id="POST-EPIC-018", dependencies=["POST-SUBTASK-161", "POST-SUBTASK-040"], component="entities", lane="RESEARCH_LANE", outputs=["artifacts/openai_assist/entity_review_pilot.json", artifact("POST-SUBTASK-163")], touched=["configs/openai_task_registry.json", "artifacts/openai_assist/entity_review_pilot.json", "tests/test_openai_assist.py"], acceptance=["BAT-390 unresolved/review candidates are ranked with cited context while BAT-391 retains all merge/split/review authority.", "Name-only/model-only merge approval remains impossible; false-merge risk and top-k recall are measured on a pinned benchmark.", "Ambiguous or unsupported identity evidence remains review/unresolved and cannot be silently promoted."], end_to_end="Run bounded candidate ranking against pinned unresolved identities, compare deterministic ranking and model tiers, and demonstrate useful top-k assistance with zero model-approved merges.", maturity="EMPIRICALLY_VALIDATED", labels=["pilot-b", "entity-resolution"]),
        make(
            local_id="POST-SUBTASK-164",
            import_id=100472,
            issue_type="Subtask",
            objective="Pilot quarantine and schema-drift classification with deterministic remediation routing",
            parent_id="POST-STORY-055",
            epic_id="POST-EPIC-018",
            dependencies=["POST-SUBTASK-161"],
            component="validation-promotion",
            lane="RESEARCH_LANE",
            outputs=[
                "artifacts/openai_assist/router_rebalance.json",
                "artifacts/openai_assist/quarantine_schema_pilot.json",
                artifact("POST-SUBTASK-164"),
            ],
            touched=[
                "configs/openai_assist_policy.json",
                "configs/openai_task_registry.json",
                "configs/openai_quarantine_schema_pilot.json",
                "src/aggie_analytics/openai_assist",
                "tools/openai_assist.py",
                "tools/prepare_openai_quarantine_pilot.py",
                "tools/run_openai_quarantine_pilot.py",
                "tools/run_openai_gamebook_pilot.py",
                "tools/validate_openai_assist.py",
                "prompts/openai_assist/quarantine_schema_v1.txt",
                "governance/OPENAI_ASSISTIVE_PLANE.md",
                "docs/architecture/OPENAI_ASSISTIVE_PLANE.md",
                "docs/operations/OPENAI_ASSISTIVE_PLANE.md",
                "artifacts/openai_assist/router_rebalance.json",
                "artifacts/openai_assist/quarantine_schema_pilot.json",
                "tests/test_openai_assist.py",
            ],
            acceptance=[
                "Representative corruption, missingness, schema drift, incompatible mapping, evidence absence, conflict, PIT risk, and target-leakage cases are classified without changing source truth.",
                "Every remediation route is deterministic-reviewable and affected records/domains remain quarantined until authoritative validators accept them.",
                "Validated routine classifications begin with GPT-5 Nano Batch; 4o Mini or Luna is used only for a measured task need, complex ambiguity routes to Terra, and only a hard/high-risk residue routes to Sol.",
                "Meaningful Terra/Sol hard cases and the verified 651bbf...aa523 staged/base/reserve budget are evidenced before completion.",
            ],
            end_to_end="Adopt the revised router, then classify a pinned quarantine/schema-drift sample across Nano and justified higher tiers, preserving candidate-only authority and measuring evidence-verified acceptance per dollar.",
            maturity="EMPIRICALLY_VALIDATED",
            labels=["pilot-c", "quarantine"],
        ),
        make(local_id="POST-SUBTASK-165", import_id=100473, issue_type="Subtask", objective="Pilot timestamped injury, depth-chart, practice, and availability extraction when evidence is ready", parent_id="POST-STORY-055", epic_id="POST-EPIC-018", dependencies=["POST-SUBTASK-161", "POST-SUBTASK-028"], component="player-context-intelligence", lane="RESEARCH_LANE", outputs=["artifacts/openai_assist/availability_pilot.json", artifact("POST-SUBTASK-165")], touched=["configs/openai_task_registry.json", "artifacts/openai_assist/availability_pilot.json", "tests/test_openai_assist.py"], acceptance=["Suitable public evidence has source URL, immutable capture, acquisition/known-at timestamp, exact excerpt, player/team identity context, and target-game cutoff eligibility before activation.", "The model never fabricates known-at time, status, player identity, role, injury, participation, or missing availability evidence.", "Accepted candidate facts pass deterministic identity, provenance, PIT, target-leakage, and availability-domain validation."], end_to_end="When timestamped evidence is ready, run a bounded shadow extraction and prove every accepted availability fact is evidence-backed and cutoff-eligible; otherwise retain the exact deferred finding.", maturity="EMPIRICALLY_VALIDATED", labels=["pilot-d", "conditional", "availability"], conditional=True),
        make(
            local_id="POST-SUBTASK-167",
            import_id=100475,
            issue_type="Subtask",
            objective="Compare governed extraction of official Texas A&M depth-chart document evidence across Nano, Luna, Terra, and Sol",
            parent_id="POST-STORY-055",
            epic_id="POST-EPIC-018",
            dependencies=["POST-SUBTASK-162", "POST-SUBTASK-028"],
            component="player-context-intelligence",
            lane="RESEARCH_LANE",
            outputs=["artifacts/openai_assist/depth_chart_pilot.json", "artifacts/pit/historical_tamu_official_depth_chart_evidence_gate.json", artifact("POST-SUBTASK-167")],
            touched=["configs/openai_depth_chart_pilot.json", "configs/openai_task_registry.json", "configs/historical_known_at_recovery_contract.json", "prompts/openai_assist/depth_chart_document_v1.txt", "tools/prepare_openai_depth_chart_pilot.py", "tools/run_openai_depth_chart_pilot.py", "artifacts/openai_assist/depth_chart_pilot.json", "artifacts/pit/historical_tamu_official_depth_chart_evidence_gate.json", "artifacts/pit/historical_known_at_replay_gate.json", "tests/test_openai_assist.py", "tests/test_historical_known_at_recovery_contract.py"],
            acceptance=["A deterministic external gold corpus spans representative official 2011-2025 depth-chart layouts, explicit OR chains, name typography, supported fields, NOT_PRESENT injury status, and UNKNOWN historical publication time.", "The same pinned cases receive meaningful Nano-minimal, Luna-none, Terra-low, and Sol-medium work through the single governed Responses/Structured-Outputs controller, with exact request, evidence, token, cost, validation, and disposition identities.", "No chart appearance is promoted to injury, availability, canonical identity, historical-known-at, PIT, training, protected, or forecast truth; 2022-2023 chart-page noncoverage and every model failure remain explicit.", "Any later routine route is selected only from measured strict-schema, precision/recall, evidence, abstention, unsupported-fact, disagreement, review-savings, and cost-per-accepted-record evidence; Terra/Sol reserve use remains value-gated."],
            end_to_end="Prepare and independently bind a seven-case official depth-chart gold corpus, preflight all 28 governed model requests, execute them only when the configured credential is restored, and evaluate identical predictions without any protected or canonical mutation.",
            maturity="EMPIRICALLY_VALIDATED",
            labels=["pilot-a-extension", "depth-chart", "terra-sol-comparison"],
        ),
        make(
            local_id="POST-SUBTASK-168",
            import_id=100476,
            issue_type="Subtask",
            objective="Operate continuing governed OpenAI candidate assistance on dependency-ready real project work",
            parent_id="POST-STORY-056",
            epic_id="POST-EPIC-018",
            dependencies=["POST-SUBTASK-160"],
            component="data-sources",
            lane="RESEARCH_LANE",
            outputs=["artifacts/openai_assist/continuous_operations.json", artifact("POST-SUBTASK-168")],
            touched=["configs/openai_task_registry.json", "configs/openai_availability_source_triage.json", "configs/tamu_availability_source_sample.json", "prompts/openai_assist/availability_source_triage_v1.txt", "src/aggie_analytics/openai_assist/credentials.py", "tools/prepare_tamu_availability_source_sample.py", "tools/validate_tamu_availability_source_sample.py", "tools/run_openai_availability_source_triage.py", "artifacts/openai_assist/continuous_operations.json", "tests/test_openai_assist.py"],
            acceptance=[
                "Bulk/canonical promotion authority remains separate from candidate-only assistance: a failed Nano or exact-format Batch gate never blocks bounded Luna, Terra, or Sol candidate analysis when task admission passes.",
                "Dependency-ready historical documents, entity ambiguities, quarantine/schema drift, reconciliation findings, and timestamped availability evidence receive value-selected governed assistance while deterministic/local work continues first where sufficient.",
                "Every request uses the single controller, store:false, strict Structured Outputs, minimized cited evidence, content-addressed external storage, budget admission, deterministic validation, and candidate/review/quarantine-only disposition.",
                "Each handoff reports calls and spend by model, cumulative and remaining budget, last successful use, active assisted tasks, dispositions, Batch count or exact no-Batch reason, next eligible workload, and cleanup.",
            ],
            end_to_end="Run a bounded real-work candidate-only workload across Nano, Luna, Terra, and Sol after deterministic source selection, validate every output without canonical/PIT authority, reconcile exact usage, and leave the continuing lane active for the next eligible workload.",
            maturity="OPERATING",
            labels=["continuous-operations", "candidate-assistance", "terra-sol-comparison"],
        ),
        make(local_id="POST-SUBTASK-166", import_id=100474, issue_type="Subtask", objective="Scale empirically validated formats, reconcile usage, clean payloads, and publish the OpenAI handoff", parent_id="POST-STORY-056", epic_id="POST-EPIC-018", dependencies=["POST-SUBTASK-162", "POST-SUBTASK-163", "POST-SUBTASK-164", "POST-SUBTASK-167"], component="release-readiness", lane="PROTECTED_GATE", outputs=["artifacts/openai_assist/final_handoff.json", artifact("POST-SUBTASK-166")], touched=["artifacts/openai_assist/final_handoff.json", "docs/operations/OPENAI_ASSISTIVE_PLANE.md"], acceptance=["Only pilot formats meeting predeclared empirical rules scale; failed, uneconomic, unsupported, unstable, or high-review formats remain shadow/quarantined/rejected.", "Routine scale-out is GPT-5 Nano Batch first; 4o Mini/Luna, Terra, and Sol are admitted only for empirically justified roles, with Terra/Sol reserve increases backed by measured hard-case acceptance, review savings, or risk reduction.", "Usage reconciles every reservation, synchronous/Batch job, model/effort, token, dollar, allocation, stage/model-cap event, threshold alert, remaining budget, disposition, improvement, and unresolved review.", "Remote Batch files are removed after verified local preservation where practical; abandoned local tmp/partial files are removed; immutable accepted evidence remains content-addressed.", "All downstream Jira, PR, repository, provenance, secret, PIT/leakage/identity, and full-suite gates pass without any scientific-readiness overclaim."], end_to_end="Run the validated Nano-first scale-out and final reconciliation under staged/model-cap budget enforcement, demonstrate deterministic fallback on provider failure, clean reconstructible artifacts, and publish an exact resumable handoff with remaining budget.", maturity="OPERATING", labels=["scale-out", "handoff"]),
    ]


def ensure_source_ref() -> None:
    data = CONTRACT.read_bytes()
    lines = data.decode("utf-8").splitlines()
    excerpt = re.sub(r"\s+", " ", " ".join(line.strip() for line in lines if line.strip()).strip())[:320]
    row = {
        "source_ref_id": SOURCE_REF,
        "repo_relative_path": CONTRACT.relative_to(ROOT).as_posix(),
        "windows_absolute_path": "C:\\BatteredAggieSyndrome\\governance\\OPENAI_ASSISTIVE_PLANE.md",
        "document_sha256": hashlib.sha256(data).hexdigest(),
        "heading": "OpenAI API Assistive Research and Data Engineering Contract",
        "start_line": "1",
        "end_line": str(len(lines)),
        "anchor_excerpt": excerpt,
        "anchor_hash": hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
        "source_type": "md",
        "authority_level": "GOVERNANCE_DETAIL",
        "why_relevant": "Mandatory local OpenAI assistive-plane authority, budget, safety, evaluation, storage, and completion contract",
        "last_verified": date.today().isoformat(),
    }
    for path in [
        JIRA / "sources" / "SOURCE_ANCHOR_INDEX.csv",
        JIRA / "index" / "SOURCE_REFERENCE_INDEX.csv",
    ]:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = list(reader.fieldnames or [])
            rows = list(reader)
        existing = [item for item in rows if item.get("source_ref_id") == SOURCE_REF]
        if len(existing) > 1:
            raise RuntimeError(f"duplicate {SOURCE_REF} in {path}")
        rows = [item for item in rows if item.get("source_ref_id") != SOURCE_REF] + [row]
        rows.sort(key=lambda item: item["source_ref_id"])
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)


def main() -> int:
    ensure_source_ref()
    new_records = specs()
    new_ids = {record["local_id"] for record in new_records}
    existing: list[dict[str, Any]] = []
    for path in (JIRA / "records" / "issues").rglob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["local_id"] not in new_ids:
            existing.append(record)
        else:
            path.unlink()
    all_import_ids = [int(record.get("import_id", 0)) for record in existing]
    if any(value in set(range(100464, 100477)) for value in all_import_ids):
        raise RuntimeError("OpenAI Jira import ID range collides with an existing issue")
    for record in new_records:
        path = ROOT / record["canonical_record"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    subprocess.run(
        [sys.executable, "-B", str(JIRA / "tools" / "rebuild_all_derivatives.py")],
        cwd=ROOT,
        check=True,
    )
    print(f"PASS: synchronized OpenAI Jira graph issues={len(new_records)} source_ref={SOURCE_REF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

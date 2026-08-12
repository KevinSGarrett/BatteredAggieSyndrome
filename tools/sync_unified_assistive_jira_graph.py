from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
JIRA = ROOT / "jira"
CONTRACT = ROOT / "governance" / "UNIFIED_ASSISTIVE_EXECUTION_PLANE.md"
SOURCE_REF = "SRCREF-02121"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:92]


def load(local_id: str) -> dict[str, Any]:
    matches = list((JIRA / "records/issues").rglob(f"{local_id}_*.json"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one template for {local_id}, found {len(matches)}")
    return json.loads(matches[0].read_text(encoding="utf-8"))


def path_for(record: dict[str, Any]) -> Path:
    folder = {"Story": "stories", "Subtask": "subtasks"}[record["issue_type"]]
    return JIRA / "records/issues" / folder / f"{record['local_id']}_{slug(record['objective'])}.json"


def common(template: dict[str, Any], *, local_id: str, import_id: int, objective: str, issue_type: str, parent: str, dependencies: list[str], workflow: str) -> dict[str, Any]:
    value = deepcopy(template)
    value.update({
        "local_id": local_id,
        "jira_key": "",
        "import_id": import_id,
        "issue_type": issue_type,
        "title": f"[{local_id}] {objective}",
        "objective": objective,
        "parent_id": parent,
        "epic_id": "POST-EPIC-018",
        "dependencies": dependencies,
        "blocks": [],
        "workflow_state": workflow,
        "evidence_state": "PARTIAL" if workflow == "IN_PROGRESS" else ("BLOCKED" if workflow == "BLOCKED" else "PLANNED"),
        "ready": workflow == "READY",
        "priority": "P0",
        "critical_path": False,
        "owner_wave": "POST_W25",
        "source_ids": ["UNIFIED-ASSISTIVE-EXECUTION-PLAN"],
        "source_refs": [SOURCE_REF],
        "primary_source_refs": [SOURCE_REF],
        "supporting_source_refs": [],
        "component": "operations-security",
        "components_expected_to_be_touched": ["operations-security", "assistive-plane", "orchestration"],
        "execution_lane": "SHARED_CONTRACT" if local_id == "POST-SUBTASK-201" else "RESEARCH_LANE",
        "execution_mode": "AGGREGATE_GATE" if issue_type == "Story" else "ATOMIC_EXECUTION",
        "expected_maturity_after_completion": "INTEGRATED" if local_id == "POST-SUBTASK-201" else "EMPIRICALLY_VALIDATED",
        "maturity_before": "NOT_STARTED",
        "historical_classification": "ACTIONABLE_POST_WAVE",
        "last_content_audit": date.today().isoformat(),
        "governance_traceability_gate": local_id if issue_type == "Subtask" else "POST-SUBTASK-201",
        "traceability_inherited_from": [],
        "effective_traceability_counts": {"requirement_ids": 0, "acceptance_control_ids": 0, "adr_ids": 0, "risk_ids": 0, "gap_ids": 0},
        "effective_traceability_total": 0,
        "traceability_resolution": "DIRECT_DOMAIN_GATE",
        "labels": ["actionable", "post-wave", "unified-assistive", "candidate-only", "subtask" if issue_type == "Subtask" else "aggregate-gate"],
        "ai_context_notes": [
            f"Canonical unified assistive contract source is `{SOURCE_REF}`.",
            "Never expose credentials, .env content, private data, or unnecessary protected evidence.",
            "Codex and deterministic validators retain canonical, scientific, Git/GitHub, Jira, and publication authority.",
        ],
    })
    value.pop("operational_jira", None)
    value.pop("completion_evidence_manifest_sha256", None)
    output = f"artifacts/jira_evidence/{local_id}.json"
    value["expected_outputs"] = [output]
    value["evidence_manifest_path"] = output
    value["allowed_modification_paths"] = [output]
    destination = path_for(value)
    value["canonical_record"] = destination.relative_to(ROOT).as_posix()
    value["generated_markdown"] = f"jira/issues/{destination.parent.name}/{destination.stem}.md"
    value["work_packet_path"] = f"jira/ai/work_packets/{local_id}.md"
    return value


def specs() -> list[dict[str, Any]]:
    story = common(load("POST-STORY-057"), local_id="POST-STORY-058", import_id=100510, objective="Operate one unified assistive execution plane across deterministic, OpenAI, OpenRouter, Cursor, local Qwen, and private CPU worker routes", issue_type="Story", parent="POST-EPIC-018", dependencies=["POST-SUBTASK-160", "POST-SUBTASK-198"], workflow="IN_PROGRESS")
    story["scope"] = "Coordinate one provider-neutral ready-work inventory, exact route readiness, independent budgets, candidate authority, utilization evidence, and graceful fallback without replacing provider-specific ledgers or protected project controls."
    story["acceptance_criteria"] = [
        "All eligible ready work has immutable pre-routing effort and exactly one reconciled disposition.",
        "Every provider route is keyed by exact model, task format, schema, policy, security, and budget evidence.",
        "Required real workloads, cross-plane comparison, restart/outage recovery, and seven-day/three-cycle sustained evidence pass or remain precisely incomplete without blocking independent work.",
    ]
    story["blocked_reason"] = ""
    story["unblock_condition"] = ""

    foundation = common(load("POST-SUBTASK-198"), local_id="POST-SUBTASK-201", import_id=100511, objective="Implement the unified ready-work inventory, routing, readiness, budget, provenance, bypass, utilization, and completeness foundation", issue_type="Subtask", parent="POST-STORY-058", dependencies=["POST-SUBTASK-160", "POST-SUBTASK-198"], workflow="IN_PROGRESS")
    foundation["scope"] = "Implement the non-billable provider-neutral foundation and preserve existing direct OpenAI/OpenRouter controllers behind adapters. Live paid/provider qualification volumes are downstream."
    foundation["files_expected_to_be_touched"] = ["configs/assistive_provider_registry.json", "configs/unified_assistive_policy.json", "src/aggie_analytics/assistive_plane", "tools/validate_unified_assistive_plane.py", "tools/refresh_cursor_catalog.py", "tools/refresh_local_assistive_runtime.py", "tests/test_unified_assistive_plane.py", "governance/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md", "governance/SOURCE_OF_TRUTH_MAP.md", "docs/architecture/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md", "docs/operations/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md"]
    foundation["allowed_modification_paths"] = foundation["files_expected_to_be_touched"] + [foundation["evidence_manifest_path"]]
    foundation["acceptance_criteria"] = [
        "Inventory validation enforces effort points 1/2/3/5/8, stable identities, anti-padding, one disposition, and complete count/point reconciliation.",
        "Readiness binds provider, resolved model, task format, schema hash, and policy version; provider budgets remain independent and explicit.",
        "Cursor, loopback Ollama, and exact CPU-worker identity policies fail closed; direct endpoint bypasses are detected.",
        "Credential-safe live catalog/runtime evidence is content-addressed outside Git and all focused/full validators pass through protected integration.",
    ]
    foundation["blocked_reason"] = ""
    foundation["unblock_condition"] = ""
    # The provider-neutral foundation merged through protected PR #242 at
    # exact main d849cc416de2730b589634709e6c0a66add88625 after all hosted
    # and local acceptance gates passed. Preserve terminal evidence on future
    # graph reconciliation rather than regressing the unit to partial work.
    foundation["workflow_state"] = "DONE"
    foundation["evidence_state"] = "VERIFIED"
    foundation["ready"] = False

    cursor = common(load("POST-SUBTASK-199"), local_id="POST-SUBTASK-202", import_id=100512, objective="Qualify Cursor Cloud Agents with exact Codex model, serial safety pilots, bounded concurrency, and reviewed candidate integration", issue_type="Subtask", parent="POST-STORY-058", dependencies=["POST-SUBTASK-201"], workflow="BLOCKED")
    cursor["scope"] = "Execute 10 nontrivial isolated repository units using exact live `gpt-5.3-codex`, low/medium reasoning, Fast disabled, no direct branch/PR/merge authority, and full Codex review."
    cursor["acceptance_criteria"] = [
        "A positive Cursor-only spending envelope and live catalog/repository readiness exist before paid run creation.",
        "Two serial safety pilots pass before at most two concurrent agents; all 10 units use clean exact-base isolation.",
        "Every diff is scope/secret/test/review validated and no Cursor result controls protected truth or integration.",
    ]
    cursor["blocked_reason"] = "PAID_CURSOR_BUDGET_NOT_AUTHORIZED"
    cursor["unblock_condition"] = "User explicitly authorizes a positive Cursor-only envelope and POST-SUBTASK-201 integrates."

    qwen = common(load("POST-SUBTASK-161"), local_id="POST-SUBTASK-203", import_id=100513, objective="Qualify local Ollama Qwen on real strict-schema, reconciliation, and code-review work", issue_type="Subtask", parent="POST-STORY-058", dependencies=["POST-SUBTASK-201"], workflow="DONE")
    qwen["scope"] = "Run at least 100 real records or 10 bounded packets across three task types under loopback-only, one-model, one-parallel, 4K-context initial policy."
    qwen["acceptance_criteria"] = [
        "Model/runtime/digest/hardware identities and prompt/schema/result dispositions are content-addressed.",
        "Strict schema, evidence, abstention, consistency, time/rework, and unsupported-fact results are measured on real work.",
        "Candidate outputs cannot bypass deterministic validation or enter canonical/protected truth directly.",
    ]
    qwen["blocked_reason"] = ""
    qwen["unblock_condition"] = ""
    qwen["evidence_state"] = "VERIFIED"
    qwen["ready"] = False
    qwen["expected_outputs"] = [
        "artifacts/assistive/local_qwen_qualification.json",
        "artifacts/jira_evidence/POST-SUBTASK-203.json",
    ]
    qwen["evidence_manifest_path"] = "artifacts/jira_evidence/POST-SUBTASK-203.json"
    qwen["allowed_modification_paths"] = qwen["expected_outputs"]
    qwen["completion_evidence_manifest_sha256"] = hashlib.sha256(
        (ROOT / qwen["evidence_manifest_path"]).read_bytes()
    ).hexdigest()
    qwen["ai_context_notes"].append(
        "The bounded qualification is complete and verified, but both exact evaluated model identities failed predeclared evidence-quality gates; no local Qwen operational route is admitted."
    )

    worker = common(load("POST-SUBTASK-198"), local_id="POST-SUBTASK-204", import_id=100514, objective="Qualify the private Tailscale CPU worker for deterministic tranches and embedding or deduplication assistance", issue_type="Subtask", parent="POST-STORY-058", dependencies=["POST-SUBTASK-201"], workflow="BLOCKED")
    worker["scope"] = "Establish a private least-privilege deterministic service on exact Windows peer comfy-v4-cpu-01, then run three replayable tranches and one embedding/deduplication or small-model pilot."
    worker["acceptance_criteria"] = [
        "Peer identity, OS, storage, software lock, private binding/grants, heartbeat, timeouts, retry, idempotency, hashes, and cleanup pass before work.",
        "Three deterministic tranches replay byte-identically where applicable and restart recovery succeeds.",
        "No public Funnel exposure, credentials, canonical authority, or unverified remote mutation is introduced.",
    ]
    worker["blocked_reason"] = "NO_AUTHENTICATED_UNATTENDED_REMOTE_MANAGEMENT_CHANNEL; CPU_WORKER_SERVICE_NOT_LISTENING"
    worker["unblock_condition"] = "Establish a recoverable authenticated setup path on exact peer comfy-v4-cpu-01, deploy the private service, then pass heartbeat, three replay tranches, exact-dedup pilot, restart recovery, and cleanup evidence."
    worker["evidence_state"] = "PARTIAL"
    worker["expected_outputs"] = [
        "artifacts/assistive/cpu_worker_readiness.json",
        "artifacts/jira_evidence/POST-SUBTASK-204.json",
    ]
    worker["evidence_manifest_path"] = "artifacts/jira_evidence/POST-SUBTASK-204.json"
    worker["allowed_modification_paths"] = [
        *worker["expected_outputs"],
        "configs/cpu_worker_qualification.json",
        "configs/unified_assistive_policy.json",
        "configs/assistive_provider_registry.json",
        "src/aggie_analytics/assistive_plane/cpu_worker_backend.py",
        "tools/cpu_worker_service.py",
        "tools/install_cpu_worker_service.ps1",
        "tools/qualify_cpu_worker.py",
        "tools/refresh_cpu_worker_readiness.py",
        "tools/validate_cpu_worker_readiness.py",
        "tests/test_cpu_worker_backend.py",
        "docs/architecture/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md",
        "docs/operations/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md",
    ]
    worker["files_expected_to_be_touched"] = worker["allowed_modification_paths"]
    worker["files_expected_to_be_read"] = [
        "configs/unified_assistive_policy.json",
        "governance/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md",
        "docs/operations/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md",
    ]
    worker["files_to_inspect"] = worker["files_expected_to_be_read"]
    worker["in_scope"] = [
        "Exact Tailscale peer and controller identity verification.",
        "A fixed-function deterministic service with no arbitrary shell or path authority.",
        "Three byte-replayable tranches, one exact-dedup pilot, restart recovery, provenance, and cleanup evidence.",
    ]
    worker["out_of_scope"] = [
        "Public Funnel exposure, arbitrary remote code execution, or credential capture.",
        "Canonical, PIT, label, protected-evaluation, model-promotion, forecast, publication, BAS, or Aggie Excess authority.",
        "Claiming route readiness before live exact-peer replay and restart evidence pass.",
    ]
    worker["required_tests"] = [
        {"classification": "EXISTING_AUTOMATED_TEST", "expectation": "Fixed task, identity, endpoint, authority, replay, and malformed-input gates pass.", "path": "tests/test_cpu_worker_backend.py", "validation_class": "SECURITY"},
        {"classification": "END_TO_END", "expectation": "Three exact-peer tranches and one dedup pilot replay byte-identically after a service restart.", "path": "artifacts/jira_evidence/POST-SUBTASK-204.json", "validation_class": "END_TO_END"},
        {"classification": "REPRODUCIBILITY", "expectation": "Peer, controller, code, config, request, result, runtime, and cleanup identities are preserved.", "path": "artifacts/assistive/cpu_worker_readiness.json", "validation_class": "REPRODUCIBILITY"},
    ]
    worker["end_to_end_validation"] = "Deploy only to the exact private Windows peer, verify heartbeat and controller allowlist, execute all fixed tasks twice, restart the service, replay, validate hashes, and clean reconstructible temporary output."

    assurance = common(load("POST-SUBTASK-168"), local_id="POST-SUBTASK-205", import_id=100515, objective="Run cross-plane gold comparison, three scheduler cycles, restart and outage exercises, and seven-day sustained assurance", issue_type="Subtask", parent="POST-STORY-058", dependencies=["POST-SUBTASK-202", "POST-SUBTASK-203", "POST-SUBTASK-204", "POST-SUBTASK-168", "POST-SUBTASK-199"], workflow="BLOCKED")
    assurance["scope"] = "Derive final utilization/completeness from real route evidence, not counters, after applicable providers qualify; preserve explicit budget/capability incompleteness."
    assurance["acceptance_criteria"] = [
        "One common-support gold comparison reports quality, evidence, abstention, review time, rework, throughput, cost, and dispositions across admitted routes.",
        "At least seven calendar days, three real scheduler cycles, one restart exercise, and one outage exercise reconcile with inventory/dispatch/usage/result/cleanup ledgers.",
        "All invariants remain unviolated and exact incomplete provider requirements are reported without fabricated backfill.",
    ]
    assurance["blocked_reason"] = "LOCAL_QWEN_NOT_ADMITTED; CURSOR_BUDGET_BLOCKED; CPU_WORKER_REMOTE_SETUP_AND_SUSTAINED_TIME_WINDOW_PENDING"
    assurance["unblock_condition"] = "A local route passes a newly versioned empirical qualification, POST-SUBTASK-204 qualifies, paid-route budget gates resolve where applicable, and sustained-operation evidence accrues."
    return [story, foundation, cursor, qwen, worker, assurance]


def ensure_source_ref() -> None:
    data = CONTRACT.read_bytes()
    lines = data.decode("utf-8").splitlines()
    excerpt = re.sub(r"\s+", " ", " ".join(line.strip() for line in lines if line.strip()).strip())[:320]
    row = {
        "source_ref_id": SOURCE_REF,
        "repo_relative_path": CONTRACT.relative_to(ROOT).as_posix(),
        "windows_absolute_path": r"C:\BatteredAggieSyndrome\governance\UNIFIED_ASSISTIVE_EXECUTION_PLANE.md",
        "document_sha256": hashlib.sha256(data).hexdigest(),
        "heading": "Unified Assistive Execution Plane",
        "start_line": "1",
        "end_line": str(len(lines)),
        "anchor_excerpt": excerpt,
        "anchor_hash": hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
        "source_type": "md",
        "authority_level": "GOVERNANCE_DETAIL",
        "why_relevant": "Mandatory unified inventory, routing, provider, budget, worker, sustained-operation, and authority contract",
        "last_verified": date.today().isoformat(),
    }
    for path in [JIRA / "sources/SOURCE_ANCHOR_INDEX.csv", JIRA / "index/SOURCE_REFERENCE_INDEX.csv"]:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = list(reader.fieldnames or [])
            rows = [item for item in reader if item.get("source_ref_id") != SOURCE_REF]
        rows.append(row)
        rows.sort(key=lambda item: item["source_ref_id"])
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\r\n")
            writer.writeheader()
            writer.writerows(rows)


def main() -> int:
    ensure_source_ref()
    records = specs()
    ids = {record["local_id"] for record in records}
    preserved: dict[str, dict[str, Any]] = {}
    for path in (JIRA / "records/issues").rglob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("local_id") in ids:
            preserved[payload["local_id"]] = {"jira_key": payload.get("jira_key", ""), "operational_jira": payload.get("operational_jira")}
            path.unlink()
    used_imports = {int(json.loads(path.read_text(encoding="utf-8")).get("import_id", 0)) for path in (JIRA / "records/issues").rglob("*.json")}
    if used_imports.intersection(range(100510, 100516)):
        raise RuntimeError("Unified assistive Jira import ID range collides")
    for record in records:
        live = preserved.get(record["local_id"], {})
        record["jira_key"] = live.get("jira_key", "")
        if live.get("operational_jira"):
            record["operational_jira"] = live["operational_jira"]
        destination = ROOT / record["canonical_record"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    subprocess.run([sys.executable, "-B", str(JIRA / "tools/rebuild_all_derivatives.py")], cwd=ROOT, check=True)
    print(f"PASS: synchronized unified assistive Jira graph issues={len(records)} source_ref={SOURCE_REF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

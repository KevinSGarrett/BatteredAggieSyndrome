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
CONTRACT = ROOT / "governance" / "OPENROUTER_ASSISTIVE_PLANE.md"
SOURCE_REF = "SRCREF-02120"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:92]


def load(local_id: str) -> dict[str, Any]:
    paths = list((JIRA / "records" / "issues").rglob(f"{local_id}_*.json"))
    if len(paths) != 1:
        raise RuntimeError(f"expected one template for {local_id}, found {len(paths)}")
    return json.loads(paths[0].read_text(encoding="utf-8"))


def path_for(record: dict[str, Any]) -> Path:
    folder = {"Story": "stories", "Subtask": "subtasks"}[record["issue_type"]]
    return JIRA / "records" / "issues" / folder / f"{record['local_id']}_{slug(record['objective'])}.json"


def common(record: dict[str, Any], *, local_id: str, import_id: int, objective: str, issue_type: str, parent: str, dependencies: list[str], workflow: str) -> dict[str, Any]:
    value = deepcopy(record)
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
        "evidence_state": "PARTIAL" if local_id == "POST-SUBTASK-198" else "BLOCKED",
        "ready": False,
        "priority": "P0",
        "critical_path": False,
        "owner_wave": "POST_W25",
        "source_ids": ["OPENROUTER-ASSISTIVE-PLANE-PLAN"],
        "source_refs": [SOURCE_REF],
        "primary_source_refs": [SOURCE_REF],
        "supporting_source_refs": [],
        "component": "operations-security",
        "components_expected_to_be_touched": ["operations-security", "assistive-plane", "openrouter"],
        "execution_lane": "SHARED_CONTRACT" if local_id == "POST-SUBTASK-198" else "RESEARCH_LANE",
        "execution_mode": "AGGREGATE_GATE" if issue_type == "Story" else "ATOMIC_EXECUTION",
        "expected_maturity_after_completion": "INTEGRATED" if local_id == "POST-SUBTASK-198" else "EMPIRICALLY_VALIDATED",
        "maturity_before": "NOT_STARTED",
        "historical_classification": "ACTIONABLE_POST_WAVE",
        "last_content_audit": date.today().isoformat(),
        "governance_traceability_gate": local_id if issue_type == "Subtask" else "POST-SUBTASK-198",
        "traceability_inherited_from": [],
        "effective_traceability_counts": {"requirement_ids": 0, "acceptance_control_ids": 0, "adr_ids": 0, "risk_ids": 0, "gap_ids": 0},
        "effective_traceability_total": 0,
        "traceability_resolution": "DIRECT_DOMAIN_GATE",
    })
    value.pop("operational_jira", None)
    value.pop("completion_evidence_manifest_sha256", None)
    output = f"artifacts/jira_evidence/{local_id}.json"
    value["expected_outputs"] = [output]
    value["evidence_manifest_path"] = output
    value["allowed_modification_paths"] = [output]
    value["canonical_record"] = path_for(value).relative_to(ROOT).as_posix()
    value["generated_markdown"] = f"jira/issues/{path_for(value).parent.name}/{path_for(value).stem}.md"
    value["work_packet_path"] = f"jira/ai/work_packets/{local_id}.md"
    value["labels"] = ["actionable", "post-wave", "openrouter-assist", "candidate-only", "budget-isolated", "subtask" if issue_type == "Subtask" else "aggregate-gate"]
    value["ai_context_notes"] = [
        f"Canonical OpenRouter contract source is `{SOURCE_REF}`.",
        "Never expose OPENROUTER_API_KEY, .env content, cookies, authorization headers, private data, or unnecessary protected evidence.",
        "OpenRouter output is candidate-only; Codex and deterministic validators retain implementation, canonical, scientific, Git/GitHub, Jira, and publication authority.",
    ]
    return value


def specs() -> list[dict[str, Any]]:
    story = common(load("POST-STORY-056"), local_id="POST-STORY-057", import_id=100506, objective="Governed complementary OpenRouter assistive development plane with isolated budget and candidate-only authority", issue_type="Story", parent="POST-EPIC-018", dependencies=["POST-SUBTASK-160"], workflow="IN_PROGRESS")
    story["scope"] = "Provide one complementary OpenRouter backend behind a provider-neutral boundary without rewriting direct OpenAI, transferring budgets, or entering forecast-critical or protected authority paths."
    story["acceptance_criteria"] = [
        "The non-billable foundation, paid capability pilot, and continuing-operations gate each have explicit evidence-backed dispositions.",
        "Direct OpenAI remains independently governed and operational; OpenRouter uses its own policy, storage, ledger, model/route qualification, and handoff accounting.",
        "Provider failure or lack of paid authority degrades to deterministic/local work without blocking historical acquisition or modeling."
    ]
    story["blocked_reason"] = ""
    story["unblock_condition"] = ""

    foundation = common(load("POST-SUBTASK-160"), local_id="POST-SUBTASK-198", import_id=100507, objective="Implement the non-billable provider-neutral OpenRouter foundation, USD 0 hard stop, privacy controls, storage, schemas, and worker isolation", issue_type="Subtask", parent="POST-STORY-057", dependencies=["POST-SUBTASK-160"], workflow="IN_PROGRESS")
    foundation["scope"] = "Implement and integrate the governed foundation and public capability evidence. Paid inference is out of scope and must be rejected locally before network dispatch."
    foundation["files_expected_to_be_touched"] = ["configs/assistive_provider_registry.json", "configs/openrouter_assist_policy.json", "configs/openrouter_task_registry.json", "schemas/assistive", "src/aggie_analytics/assistive_plane", "tools/openrouter_assist.py", "tools/refresh_openrouter_model_catalog.py", "tools/sync_openrouter_jira_graph.py", "tools/validate_openrouter_assist.py", "tools/validate_repository.py", "tests/test_openrouter_assist.py", "governance/OPENROUTER_ASSISTIVE_PLANE.md", "governance/SOURCE_OF_TRUTH_MAP.md", "docs/architecture/OPENROUTER_ASSISTIVE_PLANE.md", "docs/operations/OPENROUTER_ASSISTIVE_PLANE.md", "jira/tools/import_bat_live.py", "jira/tools/jira_pack_lib.py", "jira/records/issues/subtasks/POST-SUBTASK-196_capture_and_gate_post_2022_national_play_drive_history.json"]
    foundation["allowed_modification_paths"] = foundation["files_expected_to_be_touched"] + [foundation["evidence_manifest_path"]]
    foundation["acceptance_criteria"] = [
        "One provider-neutral dispatcher and one OpenRouter backend own admission, credential loading, redaction, strict schemas, request identity, retries, storage, provenance, usage/cost validation, and disposition.",
        "The production ledger hard-stops every billable request at exactly USD 0.00 before network dispatch and transfers no direct OpenAI funds.",
        "Provider defaults require parameter support, deny data collection, require ZDR, and disable fallback; exact routes remain unapproved pending endpoint and empirical evidence.",
        "Public official documentation and model catalog are content-addressed outside Git; qwen/qwen3-coder-next remains a capability candidate only.",
        "Worker packets and patch paths cannot access .env, .git, protected truth, external data, or out-of-scope paths; deterministic validators retain all authority.",
        "Focused, repository, provenance, Jira, secret, and full-suite validation pass through normal PR integration."
    ]
    foundation["blocked_reason"] = ""
    foundation["unblock_condition"] = ""
    # The non-billable foundation was merged through PR #240 at exact main
    # eeb3d52698adab4f1e242d7a3ec89fb0e3163e83 after every hosted and local
    # acceptance gate passed. Preserve that terminal evidence on future graph
    # reconciliation instead of regressing the unit to IN_PROGRESS/PARTIAL.
    foundation["workflow_state"] = "DONE"
    foundation["evidence_state"] = "VERIFIED"
    foundation["ready"] = False

    pilot = common(load("POST-SUBTASK-161"), local_id="POST-SUBTASK-199", import_id=100508, objective="Run the bounded Qwen patch-only capability and cross-family quality pilot after separate paid OpenRouter authorization", issue_type="Subtask", parent="POST-STORY-057", dependencies=["POST-SUBTASK-198"], workflow="BLOCKED")
    pilot["scope"] = "After explicit paid authority, compare deterministic-only work with a pinned Qwen candidate and bounded cross-family references on versioned gold cases; no production or canonical authority."
    pilot["acceptance_criteria"] = [
        "The user separately authorizes a positive OpenRouter spending envelope and provider/account hard limits are reconciled before the first paid call.",
        "Exact model and provider endpoints pass strict schema, ZDR, data-collection, fallback, context, usage, and cost capability probes.",
        "A versioned gold corpus reports schema validity, evidence accuracy, unsupported claims, patch applicability, tests, review savings, consistency, disagreement, dispositions, and accepted value per dollar.",
        "Negative findings remain preserved and no route is adopted solely because a response succeeded."
    ]
    pilot["blocked_reason"] = "PAID_OPENROUTER_BUDGET_NOT_AUTHORIZED"
    pilot["unblock_condition"] = "User explicitly authorizes a positive OpenRouter-only spending envelope; foundation is integrated; exact route/privacy/schema/cost gates pass."

    operations = common(load("POST-SUBTASK-168"), local_id="POST-SUBTASK-200", import_id=100509, objective="Operate empirically admitted OpenRouter assistive routes with independent usage, provenance, cleanup, and handoff evidence", issue_type="Subtask", parent="POST-STORY-057", dependencies=["POST-SUBTASK-199"], workflow="BLOCKED")
    operations["scope"] = "Operate only task/model/provider routes that pass the paid pilot and remain inside the separately authorized OpenRouter envelope. Batch Beta stays separately gated."
    operations["acceptance_criteria"] = [
        "Only empirically admitted task/model/provider routes receive continuing work; deterministic/local methods remain preferred when sufficient.",
        "Every request records task/Jira/base/source/prompt/schema/model/reasoning/provider/privacy/cost/output/disposition identities in external content-addressed storage.",
        "OpenRouter and direct OpenAI calls, spend, remaining budgets, models, providers, dispositions, Batch decisions, cleanup, blockers, and next workloads are reported separately at handoff.",
        "Provider failure, rejected admission, or partial task failure never globally blocks independent acquisition, modeling, or deterministic implementation."
    ]
    operations["blocked_reason"] = "PAID_OPENROUTER_BUDGET_NOT_AUTHORIZED_AND_EMPIRICAL_ROUTE_NOT_ADMITTED"
    operations["unblock_condition"] = "POST-SUBTASK-199 passes for at least one exact task/model/provider route within a separately authorized positive budget."
    return [story, foundation, pilot, operations]


def ensure_source_ref() -> None:
    data = CONTRACT.read_bytes()
    lines = data.decode("utf-8").splitlines()
    excerpt = re.sub(r"\s+", " ", " ".join(line.strip() for line in lines if line.strip()).strip())[:320]
    row = {
        "source_ref_id": SOURCE_REF,
        "repo_relative_path": CONTRACT.relative_to(ROOT).as_posix(),
        "windows_absolute_path": r"C:\BatteredAggieSyndrome\governance\OPENROUTER_ASSISTIVE_PLANE.md",
        "document_sha256": hashlib.sha256(data).hexdigest(),
        "heading": "OpenRouter Assistive Development Plane",
        "start_line": "1",
        "end_line": str(len(lines)),
        "anchor_excerpt": excerpt,
        "anchor_hash": hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
        "source_type": "md",
        "authority_level": "GOVERNANCE_DETAIL",
        "why_relevant": "Mandatory OpenRouter authority, isolated budget, privacy, evaluation, storage, and completion contract",
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
    preserved_live: dict[str, dict[str, Any]] = {}
    for path in (JIRA / "records/issues").rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("local_id") in ids:
            preserved_live[data["local_id"]] = {
                "jira_key": data.get("jira_key", ""),
                "operational_jira": data.get("operational_jira"),
            }
            path.unlink()
    existing_imports = {int(json.loads(path.read_text(encoding="utf-8")).get("import_id", 0)) for path in (JIRA / "records/issues").rglob("*.json")}
    if existing_imports.intersection(range(100506, 100510)):
        raise RuntimeError("OpenRouter Jira import ID range collides")
    for record in records:
        live = preserved_live.get(record["local_id"], {})
        record["jira_key"] = live.get("jira_key", "")
        if live.get("operational_jira"):
            record["operational_jira"] = live["operational_jira"]
        destination = ROOT / record["canonical_record"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    subprocess.run([sys.executable, "-B", str(JIRA / "tools/rebuild_all_derivatives.py")], cwd=ROOT, check=True)
    print(f"PASS: synchronized OpenRouter Jira graph issues={len(records)} source_ref={SOURCE_REF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

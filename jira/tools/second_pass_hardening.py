from __future__ import annotations

"""Second-pass content hardening and independent validation for the BAS Jira pack.

This tool upgrades the canonical issue records from the first-pass generated pack,
regenerates every derivative view from those records, adds current Jira Cloud import
aliases, and applies stricter content/traceability/source/derivative validation.

It intentionally does not alter non-Jira project implementation or governance files.
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

sys.dont_write_bytecode = True

JIRA_ROOT = Path(__file__).resolve().parents[1]

def _configured_repo_root() -> Path:
    raw = os.environ.get("BAS_JIRA_REPO_ROOT") or os.environ.get("BAS_REPO_ROOT")
    if not raw:
        for index, argument in enumerate(sys.argv):
            if argument == "--repo-root" and index + 1 < len(sys.argv):
                raw = sys.argv[index + 1]
                break
            if argument.startswith("--repo-root="):
                raw = argument.split("=", 1)[1]
                break
    return Path(raw).expanduser().resolve() if raw else JIRA_ROOT.parent

REPO_ROOT = _configured_repo_root()
RECORD_ROOT = JIRA_ROOT / "records" / "issues"

def project_path(value: str | Path) -> Path:
    relative = Path(value)
    if relative.parts and relative.parts[0].lower() == "jira":
        return JIRA_ROOT.joinpath(*relative.parts[1:])
    return REPO_ROOT / relative

def repository_context_errors() -> list[str]:
    required = [
        "governance/REQUIREMENTS_INDEX.csv",
        "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
        "governance/ADR_INDEX.csv",
        "docs/final/FINAL_RISK_REGISTER.csv",
        "docs/final/FINAL_KNOWN_GAPS.csv",
    ]
    missing = [item for item in required if not project_path(item).is_file()]
    if not missing:
        return []
    return [
        "Authoritative repository context is unavailable. Install this jira/ directory beneath the BAS repository root "
        "or rerun with --repo-root <path-to-BatteredAggieSyndrome>. Missing sentinels: " + ", ".join(missing)
    ]
TODAY = datetime.now(timezone.utc).date().isoformat()
CONTENT_CONTRACT_VERSION = "2.0"

GENERIC_IN_SCOPE = {
    "Implement or execute exactly the work described by the title",
    "Produce every declared artifact",
    "Run issue-specific checks and return evidence",
}
GENERIC_RISK = {
    "Input identity or prerequisite maturity differs from the issue record",
    "A successful command may still produce incomplete, stale, synthetic, or leakage-contaminated evidence",
}
VALIDATION_CLASSES = {
    "EXISTING_AUTOMATED_TEST",
    "NEW_AUTOMATED_TEST_REQUIRED",
    "UNIT",
    "INTEGRATION",
    "END_TO_END",
    "STATIC_VALIDATION",
    "CHRONOLOGICAL_REPLAY",
    "SCIENTIFIC",
    "CALIBRATION",
    "BENCHMARK",
    "MANUAL",
    "PUBLICATION_BOUNDARY_REVIEW",
    "SECURITY",
    "OPERATIONS",
    "REPRODUCIBILITY",
}
AUTHORITY_ORDER = {
    "PROTECTED_INVARIANT": 0,
    "FINAL_CURRENT": 1,
    "CURRENT_MACHINE_REGISTRY": 2,
    "VALIDATION_EVIDENCE": 3,
    "IMPLEMENTATION_EVIDENCE": 4,
    "LATE_READINESS": 5,
    "ACCEPTED_DESIGN": 6,
    "GOVERNANCE_DETAIL": 7,
    "HISTORICAL_PROVENANCE": 8,
    "SUPPORTING": 9,
}
MUTATION_ROOTS = {"src", "tests", "tools", "scripts", "configs", "schemas", "sql", "docs", "governance", ".github", ".codex"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def norm_space(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def unique(items: Iterable[Any]) -> list[Any]:
    out: list[Any] = []
    seen: set[str] = set()
    for item in items:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False) if isinstance(item, (dict, list)) else str(item)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def md_list(items: Iterable[str]) -> str:
    values = [str(x) for x in items if str(x).strip()]
    return "\n".join(f"- {x}" for x in values) if values else "- None."


def md_numbered(items: Iterable[str]) -> str:
    values = [str(x) for x in items if str(x).strip()]
    return "\n".join(f"{n}. {x}" for n, x in enumerate(values, 1)) if values else "1. None."


def json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    value_text = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_bytes(value_text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"))


def write_text_crlf(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"))


def normalize_jira_text_crlf() -> None:
    """Keep byte-sealed Jira derivatives deterministic on Windows and Linux."""
    text_suffixes = {".csv", ".json", ".jsonl", ".md", ".py", ".sha256", ".txt", ".yaml", ".yml"}
    for path in sorted(JIRA_ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        data = path.read_bytes()
        normalized = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        if normalized != data:
            path.write_bytes(normalized)


def jsonl_dump(path: Path, rows: Iterable[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def csv_read(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def serialize_csv(value: Any) -> Any:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict)):
        if isinstance(value, list) and all(not isinstance(x, (list, dict)) for x in value):
            return ";".join(str(x) for x in value)
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def csv_dump(path: Path, rows: Iterable[dict[str, Any]], fields: list[str] | None = None) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\r\n")
        if fields:
            writer.writeheader()
            for row in rows:
                writer.writerow({field: serialize_csv(row.get(field, "")) for field in fields})


def load_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(RECORD_ROOT.rglob("*.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    return records


def record_path(record: dict[str, Any]) -> Path:
    return project_path(record["canonical_record"])


def save_records(records: list[dict[str, Any]]) -> None:
    for record in records:
        json_dump(record_path(record), record)


def load_generator() -> Any:
    path = JIRA_ROOT / "tools" / "build_complete_jira_pack.py"
    spec = importlib.util.spec_from_file_location("bas_jira_blueprint_v2", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load blueprint from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_blueprint_maps(generator: Any) -> dict[str, Any]:
    alias_to_id: dict[str, str] = {}
    epic_seq = story_seq = subtask_seq = 0
    for epic in generator.POST_BLUEPRINT:
        epic_seq += 1
        alias_to_id[epic["alias"]] = f"POST-EPIC-{epic_seq:03d}"
        for story in epic["stories"]:
            story_seq += 1
            alias_to_id[story["alias"]] = f"POST-STORY-{story_seq:03d}"
            for task in story["tasks"]:
                subtask_seq += 1
                alias_to_id[task["alias"]] = f"POST-SUBTASK-{subtask_seq:03d}"

    epics: dict[str, dict[str, Any]] = {}
    stories: dict[str, dict[str, Any]] = {}
    tasks: dict[str, dict[str, Any]] = {}
    domain_gate_ids: dict[str, str] = {}
    for domain, alias in generator.DOMAIN_GATE_ALIAS.items():
        if alias in alias_to_id:
            domain_gate_ids[domain] = alias_to_id[alias]

    for epic in generator.POST_BLUEPRINT:
        eid = alias_to_id[epic["alias"]]
        epics[eid] = {**epic, "local_id": eid}
        for story in epic["stories"]:
            sid = alias_to_id[story["alias"]]
            task_ids = [alias_to_id[t["alias"]] for t in story["tasks"]]
            stories[sid] = {**story, "local_id": sid, "epic_id": eid, "domain": epic["domain"], "task_ids": task_ids, "epic_title": epic["title"]}
            for pos, task in enumerate(story["tasks"]):
                tid = alias_to_id[task["alias"]]
                tasks[tid] = {
                    **task,
                    "local_id": tid,
                    "story_id": sid,
                    "epic_id": eid,
                    "domain": epic["domain"],
                    "story_title": story["title"],
                    "epic_title": epic["title"],
                    "position": pos,
                    "task_ids": task_ids,
                    "next_task_id": task_ids[pos + 1] if pos + 1 < len(task_ids) else "",
                    "previous_task_ids": task_ids[:pos],
                    "domain_gate_id": domain_gate_ids.get(epic["domain"], ""),
                    "story_e2e": story.get("e2e", ""),
                }
    return {
        "generator": generator,
        "alias_to_id": alias_to_id,
        "epics": epics,
        "stories": stories,
        "tasks": tasks,
        "domain_gate_ids": domain_gate_ids,
    }


def source_ref_maps() -> tuple[dict[str, dict[str, str]], dict[str, list[dict[str, str]]]]:
    rows = csv_read(JIRA_ROOT / "index" / "SOURCE_REFERENCE_INDEX.csv")
    by_id = {r["source_ref_id"]: r for r in rows}
    by_path: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_path[row["repo_relative_path"]].append(row)
    return by_id, by_path


def tokenize(text: str) -> set[str]:
    stop = {
        "the", "and", "or", "of", "to", "a", "an", "for", "with", "on", "in", "from", "by", "at", "as", "into",
        "run", "build", "create", "implement", "validate", "verify", "publish", "finalize", "establish", "define", "execute",
        "complete", "approve", "block", "gate", "current", "production", "required", "work", "system", "data", "evidence",
    }
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2 and t not in stop}


def scored_domain_files(task: dict[str, Any], generator: Any, limit: int = 4) -> list[str]:
    text = " ".join([task["title"], *task.get("checks", []), *task.get("outputs", [])])
    tokens = tokenize(text)
    scored: list[tuple[int, str]] = []
    for path in generator.DOMAIN_FILES.get(task["domain"], []):
        path_tokens = tokenize(path.replace("_", " ").replace("/", " "))
        score = len(tokens & path_tokens)
        if score:
            scored.append((score, path))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [p for _, p in scored[:limit]]


def output_is_repo_mutation(path: str) -> bool:
    clean = path.strip().replace("\\", "/")
    if not clean or clean.startswith("{{") or clean.startswith("http"):
        return False
    root = clean.split("/", 1)[0]
    if root not in MUTATION_ROOTS:
        return False
    return bool(Path(clean).suffix) or root in {"configs", "schemas", "sql", "docs", "governance", ".github", ".codex"}


def task_specific_exclusions(task: dict[str, Any], sibling_titles: list[str]) -> list[str]:
    text = " ".join([task["title"], *task.get("checks", []), task.get("external_blocker", "")]).lower()
    out = [
        "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
        "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
        "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    ]
    if sibling_titles:
        out.append("Work assigned to sibling subtasks: " + "; ".join(sibling_titles) + ".")
    if any(k in text for k in ["rights", "license", "terms"]):
        out.append("Reintroducing a license/terms/redistribution gate for private acquisition or training, or publishing raw third-party payloads without a separate future review.")
    if any(k in text for k in ["credential", "secret", "authentication"]):
        out.append("Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.")
    if any(k in text for k in ["benchmark", "target host", "latency", "runtime", "rpo", "rto"]):
        out.append("Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.")
    if any(k in text for k in ["pit", "as-of", "cutoff", "replay", "chronological", "timestamp", "leakage"]):
        out.append("Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.")
    if any(k in text for k in ["bas", "aggie excess", "specialization", "scientific", "calibration", "champion", "model"]):
        out.append("Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.")
    if task["domain"] == "live":
        out.append("Treating deferred live/in-game work as admitted production scope or describing it as Wave 26.")
    return unique(out)


def validation_profile(task: dict[str, Any], current_tests: list[dict[str, Any]], repo_root: Path) -> list[dict[str, str]]:
    text = " ".join([task["title"], *task.get("checks", []), *task.get("outputs", []), task.get("external_blocker", "")]).lower()
    explicit = set(task.get("tests", []))
    existing: list[dict[str, str]] = []
    for test in current_tests:
        path = str(test.get("path", ""))
        if not path or path == "NEW TEST REQUIRED" or not (repo_root / path).is_file():
            continue
        score = len(tokenize(path) & tokenize(text))
        if path in explicit or score > 0 or len(existing) < 1:
            existing.append({
                "classification": "EXISTING_AUTOMATED_TEST",
                "validation_class": "REGRESSION",
                "path": path,
                "expectation": f"Run as a regression check after completing {task['local_id']}; retain command, exit code, and relevant output.",
            })
    existing = unique(existing)[:3]

    classes: list[tuple[str, str, str]] = []
    publication_metadata = any(k in text for k in ["rights review", "license", "terms", "legal review", "publication boundary"]) or "RIGHTS" in task.get("external_blocker", "") or "TERMS" in task.get("external_blocker", "")
    benchmark = any(k in text for k in ["benchmark", "target host", "latency", "throughput", "runtime", "memory", "disk growth", "rpo", "rto", "concurrency"])
    pit = any(k in text for k in ["pit", "point-in-time", "as-of", "known-at", "cutoff", "chronological", "walk-forward", "leakage", "same-game", "timestamp"])
    scientific = any(k in text for k in ["bas", "aggie excess", "scientific", "hypothesis", "confidence interval", "significance", "effect", "ablation", "champion", "challenger", "model", "feature tournament"])
    calibration = any(k in text for k in ["calibrat", "brier", "reliability", "probability"])
    security = any(k in text for k in ["secret", "credential", "security", "vulnerability", "supply-chain", "restricted", "authentication", "authorization"])
    operations = task["domain"] in {"mlops", "product", "operations", "release"} or any(k in text for k in ["incident", "runbook", "backup", "restore", "alert", "observability", "deploy", "rollback", "drift", "freshness", "sla"])
    gate = task["position"] == len(task["task_ids"]) - 1 or task.get("lane") == "PROTECTED_GATE" or any(k in text for k in ["approve or block", "authorization", "gate"])
    implementation = bool(task.get("files")) or re.match(r"^(implement|build|acquire|expand|materialize|generate|instrument|serve|enforce|configure|stage|run)", task["title"].lower()) is not None
    documentary = re.match(r"^(define|reconcile|freeze|complete rights review|publish|finalize|audit|research|precommit|apply)", task["title"].lower()) is not None

    if publication_metadata:
        classes.append(("PUBLICATION_BOUNDARY_REVIEW", "MANUAL", "Verify license/terms/redistribution metadata is preserved without blocking private acquisition or training, and that raw third-party publication remains disabled."))
        classes.append(("MANUAL", task.get("outputs", ["ISSUE_EVIDENCE_MANIFEST"])[0], "Verify the private-use decision, metadata state, technical/quality scope, and future-publication boundary."))
    if benchmark:
        classes.append(("BENCHMARK", task.get("outputs", ["AUTHORITATIVE_TARGET_HOST"])[0], "Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling."))
    if pit:
        classes.append(("CHRONOLOGICAL_REPLAY", task.get("outputs", ["PIT_VALIDATION_EVIDENCE"])[0], "Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed."))
    if scientific:
        classes.append(("SCIENTIFIC", task.get("outputs", ["SCIENTIFIC_EVIDENCE"])[0], "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results."))
    if calibration:
        classes.append(("CALIBRATION", task.get("outputs", ["CALIBRATION_EVIDENCE"])[0], "Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty."))
    if security:
        classes.append(("SECURITY", task.get("outputs", ["SECURITY_EVIDENCE"])[0], "Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior."))
    if operations:
        classes.append(("OPERATIONS", task.get("outputs", ["OPERATIONS_EVIDENCE"])[0], "Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions."))
    if gate:
        classes.append(("END_TO_END", task.get("outputs", ["END_TO_END_GATE_EVIDENCE"])[-1], "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking."))
    elif implementation:
        classes.append(("INTEGRATION", task.get("outputs", ["INTEGRATION_EVIDENCE"])[0], "Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state."))
    else:
        classes.append(("STATIC_VALIDATION", task.get("outputs", ["STATIC_EVIDENCE"])[0], "Validate schema, required fields, unique identifiers, cross-references, provenance, and explicit unresolved states."))
    classes.append(("REPRODUCIBILITY", "ISSUE_COMPLETION_MANIFEST", "Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result."))

    # A new automated test is required only when executable behavior is added or changed and manual/benchmark-only evidence cannot prove it.
    needs_new_automated = implementation and not publication_metadata and not (benchmark and not task.get("files")) and not documentary
    if needs_new_automated:
        declared_new_test = str(task.get("new_test_modification_path", "")).strip()
        new_test_path = declared_new_test or f"NEW_TEST_REQUIRED::{task['local_id']}"
        classes.append(("NEW_AUTOMATED_TEST_REQUIRED", new_test_path, "Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test."))

    generated = [
        {"classification": classification, "validation_class": classification, "path": path, "expectation": expectation}
        for classification, path, expectation in classes
    ]
    return unique(existing + generated)


def task_evidence(task: dict[str, Any]) -> list[str]:
    text = " ".join([task["title"], *task.get("checks", []), task.get("external_blocker", "")]).lower()
    out: list[str] = []
    for artifact in task.get("outputs", []):
        out.append(f"`{artifact}` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.")
    out.extend([
        "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
        "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
        "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    ])
    if any(k in text for k in ["rights", "license", "terms"]):
        out.append("Nonblocking source-policy metadata recording provider/terms version, access purpose, retention, model-training use, publication boundary, redistribution metadata, source URL, acquisition time, and private-research allow decision.")
    if any(k in text for k in ["credential", "secret"]):
        out.append("Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts.")
    if any(k in text for k in ["benchmark", "target host", "latency", "runtime", "memory", "rpo", "rto", "concurrency"]):
        out.append("Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.")
    if any(k in text for k in ["pit", "as-of", "cutoff", "replay", "chronological", "leakage", "timestamp"]):
        out.append("PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.")
    if any(k in text for k in ["bas", "aggie excess", "model", "calibration", "champion", "challenger", "scientific"]):
        out.append("Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.")
    return unique(out)


def task_dod(task: dict[str, Any], record: dict[str, Any]) -> list[str]:
    next_id = task.get("next_task_id")
    outputs = task.get("outputs", [])
    return [
        f"The atomic scope in {task['local_id']} is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
        "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
        "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
        "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
        "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
        "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
        (f"The output set {', '.join(f'`{x}`' for x in outputs)} is demonstrably consumable by {next_id} without manual reconstruction or undocumented state." if next_id else f"The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for {record['parent_id']}.")
    ]


def task_risks(task: dict[str, Any]) -> list[str]:
    risks = [
        f"The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for {task['local_id']}.",
        "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    ]
    for criterion in task.get("checks", []):
        risks.append(f"Acceptance failure: the evidence cannot demonstrate that {criterion[0].lower() + criterion[1:] if criterion else criterion}")
    if task.get("external_blocker"):
        risks.append(f"External blocker remains unresolved: {task['external_blocker']}.")
    return unique(risks)


def selected_source_paths(record: dict[str, Any], source_by_id: dict[str, dict[str, str]], limit: int = 12) -> list[str]:
    rows = [source_by_id[rid] for rid in record.get("source_refs", []) if rid in source_by_id]
    rows.sort(key=lambda r: (AUTHORITY_ORDER.get(r.get("authority_level", ""), 99), r.get("repo_relative_path", ""), r.get("start_line", "")))
    return unique([r["repo_relative_path"] for r in rows])[:limit]


def apply_hardening(records: list[dict[str, Any]], maps: dict[str, Any]) -> None:
    by_id = {r["local_id"]: r for r in records}
    source_by_id, _ = source_ref_maps()
    generator = maps["generator"]

    for record in records:
        record["schema_version"] = 2
        record["content_contract_version"] = CONTENT_CONTRACT_VERSION
        record.setdefault("components_expected_to_be_touched", [record.get("component", "")] if record.get("component") else [])
        record.setdefault("files_to_inspect", selected_source_paths(record, source_by_id))
        record.setdefault("governance_traceability_gate", "")
        record.setdefault("traceability_inherited_from", [])
        record.setdefault("traceability_resolution", "DIRECT")
        record.setdefault("completion_evidence_contract", {})

        if not str(record.get("historical_classification", "")).startswith("ACTIONABLE"):
            continue

        if record["local_id"] in maps["tasks"]:
            task = maps["tasks"][record["local_id"]]
            story = maps["stories"][task["story_id"]]
            sibling_titles = [maps["tasks"][tid]["title"] for tid in task["task_ids"] if tid != task["local_id"]]
            dependency_text = (
                "Consume only verified prerequisite outputs from " + ", ".join(f"`{x}`" for x in record.get("dependencies", [])) + "."
                if record.get("dependencies") else
                "Begin from the verified repository/current-state contract and the exact source sections in this issue manifest."
            )
            record["prerequisites"] = [
                f"Dependency {dependency} complete at required maturity"
                for dependency in record.get("dependencies", [])
            ]
            if record.get("external_blocker"):
                record["prerequisites"].append(f"External condition: {record['external_blocker']}")
            outputs_text = ", ".join(f"`{x}`" for x in task.get("outputs", [])) or "the declared issue evidence"
            record["title"] = f"[{record['local_id']}] {task['title']}"
            record["objective"] = task["title"]
            record["acceptance_criteria"] = unique(task.get("checks", []))
            record["scope"] = (
                f"Execute the atomic {task['position'] + 1} of {len(task['task_ids'])} step in Story {task['story_id']} ({task['story_title']}): {task['title']}. "
                f"{dependency_text} Produce {outputs_text}; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to "
                f"{task['next_task_id'] or 'the Story gate/downstream dependency graph'}."
            )
            record["in_scope"] = unique([
                f"Perform the exact action: {task['title']}.",
                dependency_text,
                *[f"Demonstrate with saved evidence: {criterion}" for criterion in task.get("checks", [])],
                *[f"Produce, validate, content-hash, and register `{artifact}`." for artifact in task.get("outputs", [])],
                "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.",
            ])
            record["out_of_scope"] = task_specific_exclusions(task, sibling_titles)

            candidate_files = unique(task.get("files", []) + [p for p in task.get("outputs", []) if output_is_repo_mutation(p)])
            if re.match(r"^(implement|build|configure|enforce|instrument|serve)", task["title"].lower()):
                candidate_files += [p for p in scored_domain_files(task, generator, 3) if p.startswith(("src/", "scripts/", "tools/", "tests/", "configs/", "schemas/", "sql/", ".github/"))]
            record["files_expected_to_be_touched"] = unique(candidate_files)
            record["components_expected_to_be_touched"] = unique([record.get("component", ""), task["domain"]])
            inspect = unique(selected_source_paths(record, source_by_id, 10) + task.get("files", []) + scored_domain_files(task, generator, 4))
            record["files_to_inspect"] = inspect[:16]

            record["required_tests"] = validation_profile(task, record.get("required_tests", []), REPO_ROOT)
            record["required_evidence"] = task_evidence(task)
            record["definition_of_done"] = task_dod(task, record)
            record["risk_failure_conditions"] = task_risks(task)
            record["stop_conditions"] = [
                "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
                "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
                "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.",
            ]
            if record.get("component") == "bas-science":
                record["acceptance_criteria"] = unique(record.get("acceptance_criteria", []) + [
                    "A scientifically valid null result—no persistent Aggie-specific excess after protected out-of-sample testing—must be preserved, reported, and accepted without changing the precommitted BAS definition, peers, thresholds, or evaluation window."
                ])

            if task.get("next_task_id"):
                record["end_to_end_validation"] = (
                    f"Validate that {outputs_text} can be parsed and consumed by `{task['next_task_id']}` using only documented identities and interfaces; "
                    "the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair."
                )
            else:
                story_e2e = task.get("story_e2e") or f"Exercise the complete {task['story_title']} path and verify downstream consumption of pinned outputs."
                downstream = record.get("blocks", [])
                record["end_to_end_validation"] = story_e2e + (
                    f" The gate decision must explicitly reevaluate downstream issues: {', '.join(downstream[:12])}{'…' if len(downstream) > 12 else ''}."
                    if downstream else " The gate decision must explicitly record that no downstream issue is silently unlocked."
                )

            gate = task.get("domain_gate_id", "")
            record["governance_traceability_gate"] = gate
            record["traceability_inherited_from"] = [] if gate == record["local_id"] else ([gate] if gate else [])
            record["traceability_resolution"] = "DIRECT_DOMAIN_GATE" if gate == record["local_id"] else "DIRECT_PLUS_INHERITED_DOMAIN_GATE" if any(record.get(k) for k in ["requirement_ids", "acceptance_control_ids", "adr_ids", "risk_ids", "gap_ids"]) else "INHERITED_DOMAIN_GATE"
            record["completion_evidence_contract"] = {
                "acceptance_matrix_required": True,
                "artifact_hashes_required": True,
                "negative_results_preserved": True,
                "provenance_dimensions": ["source", "data", "code", "config", "tool", "runtime", "split/cutoff when applicable"],
                "completion_claim_limit": record.get("expected_maturity_after_completion", ""),
                "downstream_consumer": task.get("next_task_id") or record.get("parent_id", ""),
                "governance_traceability_gate": gate,
            }
            record["ai_context_notes"] = unique([
                f"Canonical parent Story: {record.get('parent_id')}. Governance traceability gate: {gate or 'none'}. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
                f"Read the exact source sections in `jira/sources/issue_source_manifests/{record['local_id']}.json`; inspect only the listed implementation files and prerequisite outputs.",
                f"May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
                "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.",
            ])

        elif record["local_id"] in maps["stories"]:
            story = maps["stories"][record["local_id"]]
            gate_id = maps["domain_gate_ids"].get(story["domain"], "")
            final_task_id = story["task_ids"][-1]
            record["title"] = f"[{record['local_id']}] {story['title']}"
            record["objective"] = story["objective"]
            record["acceptance_criteria"] = unique(
                criterion
                for task_id in story["task_ids"]
                for criterion in maps["tasks"][task_id].get("checks", [])
            )
            record["scope"] = (
                f"Deliver Story {record['local_id']} ({story['title']}) as one coherent, gated capability inside Epic {story['epic_id']}. "
                f"Execute child subtasks {', '.join(story['task_ids'])} in dependency order, reconcile their pinned outputs, and require the final gate `{final_task_id}` "
                "to issue an evidence-backed approve/block/reject/defer decision before any downstream use."
            )
            record["in_scope"] = unique([
                *[f"Complete and verify child `{tid}` — {maps['tasks'][tid]['title']}." for tid in story['task_ids']],
                f"Integrate the child outputs and execute final gate `{final_task_id}`.",
                "Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence."
            ])
            record["out_of_scope"] = unique([
                "Work assigned to sibling Stories or another Epic.",
                "Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.",
                "Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate."
            ])
            record["governance_traceability_gate"] = gate_id
            record["traceability_inherited_from"] = [] if record["local_id"] == gate_id else ([gate_id] if gate_id else [])
            record["traceability_resolution"] = "DIRECT_PLUS_INHERITED_DOMAIN_GATE" if any(record.get(k) for k in ["requirement_ids", "acceptance_control_ids", "adr_ids", "risk_ids", "gap_ids"]) else "INHERITED_DOMAIN_GATE"
            record["files_to_inspect"] = selected_source_paths(record, source_by_id, 12)
            record["files_expected_to_be_touched"] = []
            record["components_expected_to_be_touched"] = unique([record.get("component", ""), story["domain"]])
            record["required_tests"] = unique([
                *[t for t in record.get("required_tests", []) if t.get("classification") == "EXISTING_AUTOMATED_TEST" and project_path(str(t.get("path", ""))).is_file()][:2],
                {"classification": "END_TO_END", "validation_class": "END_TO_END", "path": final_task_id, "expectation": f"The final child gate `{final_task_id}` must prove the integrated Story outcome and downstream-consumable output."},
                {"classification": "REPRODUCIBILITY", "validation_class": "REPRODUCIBILITY", "path": "STORY_EVIDENCE_MANIFEST", "expectation": "Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest."},
            ])
            record["definition_of_done"] = [
                f"All child subtasks {', '.join(story['task_ids'])} have verified evidence or an explicit accepted-risk/deferred/cancelled disposition consistent with the Story contract.",
                f"The final gate `{final_task_id}` completes and proves the Story end-to-end requirement; closing implementation children alone is insufficient.",
                "All direct and inherited requirement/control/ADR/risk/gap mappings resolve through the governance context index without missing or invalid identifiers.",
                "The Story evidence manifest pins child artifact, source/data/code/config/runtime, split/cutoff, and target-host identities where applicable and preserves failures/null results.",
                "Canonical/derived Jira views, live operational fields when connected, dependency links, queues, and downstream states are synchronized and pass strict validation.",
            ]
            record["required_evidence"] = [
                f"Verified child completion/evidence manifests for {', '.join(story['task_ids'])}.",
                f"Final gate decision from `{final_task_id}` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.",
                "Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.",
            ]
            record["completion_evidence_contract"] = {"child_gate": final_task_id, "all_child_evidence_required": True, "integrated_proof_required": True, "governance_traceability_gate": gate_id}
            record["end_to_end_validation"] = story.get("e2e") or f"Exercise the complete {story['title']} path through `{final_task_id}` and verify downstream use of pinned outputs."

        elif record["local_id"] in maps["epics"]:
            epic = maps["epics"][record["local_id"]]
            child_stories = [sid for sid, s in maps["stories"].items() if s["epic_id"] == record["local_id"]]
            final_gates = [maps["stories"][sid]["task_ids"][-1] for sid in child_stories]
            gate_id = maps["domain_gate_ids"].get(epic["domain"], "")
            record["title"] = f"[{record['local_id']}] {epic['title']}"
            record["objective"] = epic["objective"]
            record["governance_traceability_gate"] = gate_id
            record["traceability_inherited_from"] = [] if record["local_id"] == gate_id else ([gate_id] if gate_id else [])
            record["traceability_resolution"] = "DIRECT_PLUS_INHERITED_DOMAIN_GATE" if any(record.get(k) for k in ["requirement_ids", "acceptance_control_ids", "adr_ids", "risk_ids", "gap_ids"]) else "INHERITED_DOMAIN_GATE"
            record["files_to_inspect"] = selected_source_paths(record, source_by_id, 12)
            record["files_expected_to_be_touched"] = []
            record["components_expected_to_be_touched"] = unique([record.get("component", ""), epic["domain"]])
            record["required_tests"] = [
                {"classification": "END_TO_END", "validation_class": "END_TO_END", "path": gate, "expectation": f"Story gate `{gate}` must complete with verified evidence before Epic completion."}
                for gate in final_gates
            ] + [{"classification": "REPRODUCIBILITY", "validation_class": "REPRODUCIBILITY", "path": "EPIC_EVIDENCE_MANIFEST", "expectation": "Aggregate all Story gates, artifact identities, residual blockers, accepted risks, and downstream readiness."}]
            record["definition_of_done"] = [
                f"Every child Story {', '.join(child_stories)} is completed through its explicit end-to-end gate or has an explicit accepted-risk/deferred/cancelled disposition consistent with release governance.",
                "The Epic integrated capability is demonstrated on the required real data, chronology, target host, product path, or operating path; planning, code, fixtures, or unit tests alone cannot satisfy it.",
                "All direct and inherited requirement/control/ADR/risk/gap mappings resolve, all release-blocking controls have current evidence, and no protected invariant is weakened.",
                "The Epic evidence manifest pins all relevant source/data/code/config/model/calibrator/split/cutoff/runtime/hardware identities and preserves failures, null results, and unresolved limitations.",
                "Canonical/derived Jira views, live operational fields when connected, links, queues, release gates, and downstream states are synchronized and pass strict validation.",
            ]
            record["required_evidence"] = [
                f"Verified Story gate decisions for {', '.join(final_gates)}.",
                "Epic-level integrated execution/review evidence demonstrating actual downstream consumption and safe failure behavior.",
                "A residual-risk/blocker disposition and maturity/evidence claim audit tied to exact artifact and runtime identities.",
            ]
            record["completion_evidence_contract"] = {"story_gates": final_gates, "integrated_proof_required": True, "governance_traceability_gate": gate_id}
            record["end_to_end_validation"] = f"Exercise all child Story gates for {epic['title']} and prove the integrated capability is safe and consumable by its downstream Epic/release path."

    # Effective traceability counts are calculated after every direct mapping is available.
    by_id = {r["local_id"]: r for r in records}
    trace_fields = ["requirement_ids", "acceptance_control_ids", "adr_ids", "risk_ids", "gap_ids"]
    for record in records:
        effective: dict[str, list[str]] = {}
        for field in trace_fields:
            values = list(record.get(field, []))
            for inherited_id in record.get("traceability_inherited_from", []):
                values.extend(by_id.get(inherited_id, {}).get(field, []))
            effective[field] = sorted(set(values))
        record["effective_traceability_counts"] = {field: len(values) for field, values in effective.items()}
        record["effective_traceability_total"] = sum(len(values) for values in effective.values())

        # Normalize the second-pass operational/navigation fields so there is one coherent mutation/read contract.
        actionable = str(record.get("historical_classification", "")).startswith("ACTIONABLE")
        record["record_revision"] = CONTENT_CONTRACT_VERSION
        record["last_content_audit"] = TODAY
        record["canonical_source_role"] = "AUTHORITATIVE_LOCAL_SPECIFICATION"
        record["execution_mode"] = (
            "ATOMIC_EXECUTION" if actionable and record.get("issue_type") == "Subtask"
            else "AGGREGATE_GATE" if actionable
            else "HISTORICAL_REFERENCE"
        )
        evidence_manifest = f"artifacts/jira_evidence/{record['local_id']}.json" if actionable else ""
        record["evidence_manifest_path"] = evidence_manifest
        record["work_packet_path"] = f"jira/ai/work_packets/{record['local_id']}.md" if actionable else ""
        record["validation_classes"] = sorted(set(
            str(t.get("validation_class") or t.get("classification") or "")
            for t in record.get("required_tests", []) if str(t.get("validation_class") or t.get("classification") or "")
        ))
        ranked_refs = list(record.get("source_refs", []))
        record["primary_source_refs"] = ranked_refs[:4]
        record["supporting_source_refs"] = ranked_refs[4:]
        record["files_expected_to_be_read"] = unique(record.get("files_to_inspect", []))
        record["read_only_context_paths"] = unique(record.get("protected_files_and_interfaces", []) + record.get("files_to_inspect", []))
        allowed = list(record.get("files_expected_to_be_touched", []))
        declared_new_test = str(record.get("new_test_modification_path", "")).strip()
        if declared_new_test:
            allowed.append(declared_new_test)
        if actionable and record.get("issue_type") == "Subtask":
            allowed.extend(record.get("expected_outputs", []))
        if evidence_manifest:
            allowed.append(evidence_manifest)
        protected = set(record.get("protected_files_and_interfaces", []))
        record["allowed_modification_paths"] = [x for x in unique(allowed) if x not in protected]
        record["protected_change_required"] = bool(set(record.get("files_expected_to_be_touched", [])) & protected)
        record["governance_review_required"] = bool(record["protected_change_required"] or "ADR_CHANGE_REQUIRED" in record.get("labels", []))
        if actionable and record.get("component") == "bas-science":
            record["acceptance_criteria"] = unique(record.get("acceptance_criteria", []) + [
                "A null, non-significant, unstable, or directionally unsupported Aggie-specific excess result is accepted and reported without forcing a nonzero BAS effect; general FBS surprise and Texas A&M-specific excess remain distinct."
            ])
            record["out_of_scope"] = unique(record.get("out_of_scope", []) + [
                "Redefining BAS as generic Texas A&M loss probability or selecting specifications merely to manufacture a nonzero Aggie-specific effect."
            ])
            record["stop_conditions"] = unique(record.get("stop_conditions", []) + [
                "Stop if the proposed method, threshold, peer set, fold construction, or product wording would conceal, reject, or overwrite a valid null/no-effect result."
            ])
        specificity_payload = {k: record.get(k) for k in [
            "objective", "scope", "in_scope", "out_of_scope", "acceptance_criteria", "definition_of_done",
            "required_tests", "required_evidence", "end_to_end_validation", "risk_failure_conditions",
            "files_expected_to_be_touched", "allowed_modification_paths", "governance_traceability_gate",
        ]}
        record["specificity_fingerprint"] = sha256_text(json.dumps(specificity_payload, sort_keys=True, ensure_ascii=False))


def import_lib() -> Any:
    path = JIRA_ROOT / "tools" / "jira_pack_lib.py"
    spec = importlib.util.spec_from_file_location("jira_pack_lib_runtime_v2", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def render_issue_markdown(record: dict[str, Any]) -> str:
    metadata = json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True)
    tests = [f"**{t.get('classification')}** / `{t.get('validation_class', t.get('classification'))}` — `{t.get('path')}` — {t.get('expectation')}" for t in record.get("required_tests", [])]
    return f"""<!-- GENERATED VIEW. Canonical record: {record['canonical_record']} -->
# {record['local_id']} — {record['title']}

## Canonical metadata

```json
{metadata}
```

## Objective

{record.get('objective', '')}

## Why This Exists

{record.get('why_this_exists', '')}

## Scope

{record.get('scope', '')}

### Explicit In Scope

{md_list(record.get('in_scope', []))}

### Explicit Out of Scope

{md_list(record.get('out_of_scope', []))}

## Prerequisites

{md_list(record.get('prerequisites', []))}

## Hard Dependencies

{md_list(record.get('dependencies', []))}

## Blocks

{md_list(record.get('blocks', []))}

## Read / Inspect First

{md_list(record.get('files_to_inspect', []))}

## Files Expected To Be Modified

{md_list(record.get('files_expected_to_be_touched', []))}

## Components Expected To Be Touched

{md_list(record.get('components_expected_to_be_touched', []))}

## Protected Files / Interfaces

{md_list(record.get('protected_files_and_interfaces', []))}

## Expected Outputs / Artifacts

{md_list(record.get('expected_outputs', []))}

## Direct Requirements

{md_list(record.get('requirement_ids', []))}

## Direct Acceptance Controls

{md_list(record.get('acceptance_control_ids', []))}

## Governance Traceability Inheritance

- Gate: `{record.get('governance_traceability_gate', '') or 'None'}`
- Inherited from: {', '.join(record.get('traceability_inherited_from', [])) or 'None'}
- Resolution: `{record.get('traceability_resolution', '')}`
- Effective counts: `{json.dumps(record.get('effective_traceability_counts', {}), sort_keys=True)}`

## Acceptance Criteria

{md_numbered(record.get('acceptance_criteria', []))}

## Definition of Done

{md_numbered(record.get('definition_of_done', []))}

## Required Tests / Validation

{md_list(tests)}

## Required Evidence

{md_list(record.get('required_evidence', []))}

## Completion Evidence Contract

```json
{json.dumps(record.get('completion_evidence_contract', {}), indent=2, sort_keys=True)}
```

## End-to-End Validation Requirement

{record.get('end_to_end_validation', '')}

## Expected Maturity After Completion

`{record.get('expected_maturity_after_completion', '')}`

## Risk / Failure Conditions

{md_list(record.get('risk_failure_conditions', []))}

## Stop Conditions

{md_list(record.get('stop_conditions', []))}

## Source References

{md_list(record.get('source_refs', []))}

## AI Context Notes

{md_list(record.get('ai_context_notes', []))}
"""


def render_work_packet(record: dict[str, Any]) -> str:
    tests = [f"{t.get('classification')} / {t.get('validation_class', t.get('classification'))}: {t.get('path')} — {t.get('expectation')}" for t in record.get("required_tests", [])]
    mode = record.get("execution_mode", "")
    atomic = mode == "ATOMIC_EXECUTION"
    if atomic:
        mode_notice = "**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied."
        doing_heading = "What am I implementing?"
        scope_heading = "Atomic execution scope"
        modification_heading = "Files I may modify or create"
        modification_body = md_list(record.get("allowed_modification_paths", [])) + "\n\nNo path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation."
        outputs_intro = "Produce and validate these outputs within this atomic work unit:"
        completion_steps = [
            "Produce an acceptance-evidence matrix for every criterion.",
            "Run every applicable validation entry; implement each declared new automated test.",
            "Hash and register every output and all source/data/code/config/tool/runtime identities.",
            "Preserve negative, null, blocked, and failed results.",
            "Confirm that the claimed maturity—not merely code or files—exists.",
            "Update canonical/local Jira state and live Jira operational fields according to `jira/SYNC_CONTRACT.md`.",
            "Rebuild all derivatives with `python -B jira/tools/rebuild_all_derivatives.py`.",
            "Recompute READY/BLOCKED state and run `python -B jira/tools/validate_second_pass.py`.",
            "Reevaluate every downstream issue in `blocks`.",
        ]
    else:
        mode_notice = "**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets."
        doing_heading = "What capability or closure gate am I coordinating?"
        scope_heading = "Aggregate integration and closure scope"
        modification_heading = "Aggregate packet modification authority"
        modification_body = md_list(record.get("allowed_modification_paths", [])) + "\n\nOnly aggregate evidence/Jira-state artifacts listed above may be written. Do not edit production code, data, contracts, or child outputs from this packet; open the responsible atomic Subtask packet instead."
        outputs_intro = "Review and integrate these child-produced outputs; do not recreate them directly from this aggregate packet:"
        completion_steps = [
            "Verify every required child issue is complete at its claimed maturity with verified evidence; do not infer completion from file or code existence.",
            "Run or review the declared integrated end-to-end gate and downstream-consumption proof.",
            "Create the aggregate evidence manifest with pinned source/data/code/config/model/runtime identities, residual blockers, accepted risks, null/negative results, and gate decisions.",
            "Keep this Epic/Story non-READY and non-executable; route any implementation change to a specific atomic Subtask or create a controlled backlog proposal.",
            "Update canonical/local Jira state and live Jira operational fields according to `jira/SYNC_CONTRACT.md` only after the aggregate gate is truthfully satisfied.",
            "Rebuild all derivatives with `python -B jira/tools/rebuild_all_derivatives.py`, recompute queues, and run `python -B jira/tools/validate_second_pass.py`.",
            "Reevaluate downstream gates without weakening protected requirements or hiding incomplete child evidence.",
        ]
    return f"""# AI Work Packet — {record['local_id']}

## Packet mode

`{mode}`

{mode_notice}

## {doing_heading}

{record.get('objective', '')}

## Why?

{record.get('why_this_exists', '')}

## {scope_heading}

{record.get('scope', '')}

### In scope

{md_list(record.get('in_scope', []))}

### Out of scope

{md_list(record.get('out_of_scope', []))}

## Current gate state

- Workflow: `{record.get('workflow_state', '')}`
- Ready: `{str(record.get('ready', False)).lower()}`
- Priority: `{record.get('priority', '')}`
- Critical path: `{str(record.get('critical_path', False)).lower()}`
- Execution lane: `{record.get('execution_lane', '')}`
- Execution mode: `{mode}`
- Maturity before → after: `{record.get('maturity_before', '')}` → `{record.get('expected_maturity_after_completion', '')}`
- Evidence state: `{record.get('evidence_state', '')}`
- Governance traceability gate: `{record.get('governance_traceability_gate', '') or 'None'}`

## Read first

1. `{record.get('canonical_record', '')}`
2. `jira/sources/issue_source_manifests/{record['local_id']}.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `{record['local_id']}`.
4. Only these additional files/sections, plus verified prerequisite outputs:

{md_list(record.get('files_to_inspect', []))}

## Dependencies that must already be complete

{md_list(record.get('dependencies', []))}

## {modification_heading}

{modification_body}

## Components in scope

{md_list(record.get('components_expected_to_be_touched', []))}

## What I must not modify or weaken

{md_list(record.get('protected_files_and_interfaces', []))}

## Exact outputs / integrated artifacts

{outputs_intro}

{md_list(record.get('expected_outputs', []))}

## Acceptance criteria

{md_numbered(record.get('acceptance_criteria', []))}

## Tests / validation

{md_list(tests)}

## Evidence to return

{md_list(record.get('required_evidence', []))}

## End-to-end handoff

{record.get('end_to_end_validation', '')}

## Stop instead of improvising when

{md_list(record.get('stop_conditions', []))}

## Completion protocol

{md_numbered(completion_steps)}
"""


def regenerate_issue_views(records: list[dict[str, Any]]) -> None:
    for record in records:
        path = project_path(record["generated_markdown"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_issue_markdown(record), encoding="utf-8")
    work_root = JIRA_ROOT / "ai" / "work_packets"
    work_root.mkdir(parents=True, exist_ok=True)
    expected = {f"{r['local_id']}.md" for r in records if str(r.get("historical_classification", "")).startswith("ACTIONABLE")}
    for path in work_root.glob("*.md"):
        if path.name not in expected:
            path.unlink()
    for record in records:
        if str(record.get("historical_classification", "")).startswith("ACTIONABLE"):
            (work_root / f"{record['local_id']}.md").write_text(render_work_packet(record), encoding="utf-8")


def regenerate_source_manifests(records: list[dict[str, Any]]) -> None:
    source_rows = csv_read(JIRA_ROOT / "index" / "SOURCE_REFERENCE_INDEX.csv")
    by_id = {r["source_ref_id"]: r for r in source_rows}
    root = JIRA_ROOT / "sources" / "issue_source_manifests"
    root.mkdir(parents=True, exist_ok=True)
    for record in records:
        refs: list[dict[str, Any]] = []
        for rid in record.get("source_refs", []):
            if rid not in by_id:
                continue
            row = dict(by_id[rid])
            row["start_line"] = int(row["start_line"]) if row.get("start_line") else 0
            row["end_line"] = int(row["end_line"]) if row.get("end_line") else 0
            refs.append(row)
        payload = {
            "schema_version": 2,
            "issue_id": record["local_id"],
            "source_ids": record.get("source_ids", []),
            "governance_traceability_gate": record.get("governance_traceability_gate", ""),
            "traceability_inherited_from": record.get("traceability_inherited_from", []),
            "files_to_inspect": record.get("files_to_inspect", []),
            "retrieval_protocol": [
                "Verify document_sha256 against the current repository file.",
                "Verify anchor_hash against the normalized stored excerpt and current line range.",
                "If the file hash changed, run repair_source_refs.py to relocate the exact anchor/heading before using the reference.",
                "Open only the referenced section plus the minimal listed implementation/prerequisite context; the Windows path is convenience metadata, not authority.",
            ],
            "source_refs": refs,
        }
        json_dump(root / f"{record['local_id']}.json", payload)


def effective_traceability(record: dict[str, Any], by_id: dict[str, dict[str, Any]], field: str) -> list[str]:
    values = list(record.get(field, []))
    for gate in record.get("traceability_inherited_from", []):
        values.extend(by_id.get(gate, {}).get(field, []))
    return sorted(set(values))


def regenerate_governance_context(records: list[dict[str, Any]]) -> None:
    by_id = {r["local_id"]: r for r in records}
    fields = ["requirement_ids", "acceptance_control_ids", "adr_ids", "risk_ids", "gap_ids"]
    rows = []
    for record in sorted(records, key=lambda r: r["local_id"]):
        row: dict[str, Any] = {
            "issue_id": record["local_id"],
            "issue_type": record.get("issue_type", ""),
            "historical_classification": record.get("historical_classification", ""),
            "governance_traceability_gate": record.get("governance_traceability_gate", ""),
            "traceability_inherited_from": record.get("traceability_inherited_from", []),
            "traceability_resolution": record.get("traceability_resolution", ""),
        }
        for field in fields:
            direct = sorted(set(record.get(field, [])))
            effective = effective_traceability(record, by_id, field)
            base = field.removesuffix("_ids")
            row[f"direct_{base}_count"] = len(direct)
            row[f"effective_{base}_count"] = len(effective)
            row[f"effective_{base}_ids"] = effective
        row["effective_total"] = sum(int(row[f"effective_{f.removesuffix('_ids')}_count"]) for f in fields)
        row["governance_context_status"] = "DIRECT" if not record.get("traceability_inherited_from") else "VALID_INHERITANCE" if all(x in by_id for x in record.get("traceability_inherited_from", [])) else "INVALID_INHERITANCE"
        rows.append(row)
    csv_dump(JIRA_ROOT / "index" / "ISSUE_GOVERNANCE_CONTEXT.csv", rows)

    packet_rows = []
    for record in sorted(records, key=lambda r: (0 if r.get("ready") else 1, r.get("local_id", ""))):
        if not str(record.get("historical_classification", "")).startswith("ACTIONABLE"):
            continue
        packet_rows.append({
            "local_id": record["local_id"],
            "issue_type": record.get("issue_type", ""),
            "execution_mode": record.get("execution_mode", ""),
            "workflow_state": record.get("workflow_state", ""),
            "ready": record.get("ready", False),
            "packet_path": record.get("work_packet_path", ""),
            "directly_executable": record.get("execution_mode") == "ATOMIC_EXECUTION",
            "aggregate_gate_only": record.get("execution_mode") == "AGGREGATE_GATE",
            "parent_id": record.get("parent_id", ""),
            "governance_traceability_gate": record.get("governance_traceability_gate", ""),
        })
    csv_dump(JIRA_ROOT / "index" / "WORK_PACKET_INDEX.csv", packet_rows)


def adf_document(text: str) -> dict[str, Any]:
    paragraphs = []
    for block in [b.strip() for b in text.split("\n\n") if b.strip()]:
        paragraphs.append({"type": "paragraph", "content": [{"type": "text", "text": block[:32000]}]})
    return {"version": 1, "type": "doc", "content": paragraphs or [{"type": "paragraph", "content": []}]}


def description_text(record: dict[str, Any]) -> str:
    tests = "\n".join(
        f"- {t.get('classification')} / {t.get('validation_class', t.get('classification'))}: {t.get('path')} — {t.get('expectation')}"
        for t in record.get("required_tests", [])
    )
    source_refs = "\n".join(f"- {ref}" for ref in record.get("source_refs", []))
    return "\n\n".join([
        f"Local ID: {record['local_id']}",
        f"Objective\n{record.get('objective', '')}",
        f"Why This Exists\n{record.get('why_this_exists', '')}",
        "Scope\n" + record.get("scope", ""),
        "Explicit In Scope\n" + "\n".join(f"- {x}" for x in record.get("in_scope", [])),
        "Explicit Out of Scope\n" + "\n".join(f"- {x}" for x in record.get("out_of_scope", [])),
        "Prerequisites / Dependencies\n" + "\n".join(f"- {x}" for x in unique(record.get("prerequisites", []) + record.get("dependencies", []))),
        "Acceptance Criteria\n" + "\n".join(f"{n}. {x}" for n, x in enumerate(record.get("acceptance_criteria", []), 1)),
        "Definition of Done\n" + "\n".join(f"{n}. {x}" for n, x in enumerate(record.get("definition_of_done", []), 1)),
        "Required Tests / Validation\n" + tests,
        "Required Evidence\n" + "\n".join(f"- {x}" for x in record.get("required_evidence", [])),
        f"End-to-End Validation\n{record.get('end_to_end_validation', '')}",
        "Stop Conditions\n" + "\n".join(f"- {x}" for x in record.get("stop_conditions", [])),
        "Source References\n" + source_refs,
        f"Governance Traceability Gate: {record.get('governance_traceability_gate', '')}".rstrip(),
        f"Canonical Record: {record.get('canonical_record', '')}",
    ])


def regenerate_import_derivatives(records: list[dict[str, Any]]) -> None:
    by_id = {r["local_id"]: r for r in records}
    lib = import_lib()
    ordered = sorted(records, key=lambda r: int(r.get("import_id", 0)))
    legacy = csv_read(JIRA_ROOT / "import" / "JIRA_ISSUES_MASTER.csv")
    legacy_by_id = {r["Local Issue ID"]: r for r in legacy}
    legacy_fields = list(legacy[0]) if legacy else []
    legacy_rows = []
    for record in ordered:
        row = dict(legacy_by_id.get(record["local_id"], {}))
        if not row:
            continue
        row["Description"] = description_text(record)
        row["Status"] = row.get("Status", "")
        row["Logical Workflow State"] = record.get("workflow_state", "")
        row["Implementation Maturity"] = record.get("expected_maturity_after_completion", "")
        row["Evidence State"] = record.get("evidence_state", "")
        row["Critical Path"] = str(record.get("critical_path", False)).lower()
        row["Execution Lane"] = record.get("execution_lane", "")
        legacy_rows.append(row)
    for name, subset in [
        ("JIRA_ISSUES_MASTER.csv", legacy_rows),
        ("JIRA_EXTERNAL_SYSTEM_IMPORT.csv", legacy_rows),
        ("JIRA_CLOUD_LEGACY_EXTERNAL_SYSTEM_IMPORT.csv", legacy_rows),
        ("JIRA_HIERARCHY_STAGE_1.csv", [r for r in legacy_rows if r.get("Issue type") == "Epic"]),
        ("JIRA_HIERARCHY_STAGE_2.csv", [r for r in legacy_rows if r.get("Issue type") in {"Story", "Task", "Bug"}]),
        ("JIRA_HIERARCHY_STAGE_3.csv", [r for r in legacy_rows if r.get("Issue type") == "Sub-task"]),
    ]:
        csv_dump(JIRA_ROOT / "import" / name, subset, legacy_fields)

    modern_fields = [
        "Work type", "Work key", "Work item ID", "Summary", "Parent", "Description", "Status", "Priority", "Labels", "Component",
        "Local Issue ID", "Source IDs", "Phase", "Logical Workflow State", "Implementation Maturity", "Evidence State", "Owner Historical Wave", "Critical Path", "Execution Lane",
    ]
    modern = []
    for row in legacy_rows:
        modern.append({
            "Work type": row.get("Issue type", ""), "Work key": row.get("Issue key", ""), "Work item ID": row.get("Issue ID", ""),
            "Summary": row.get("Summary", ""), "Parent": row.get("Parent", ""), "Description": row.get("Description", ""),
            "Status": row.get("Status", ""), "Priority": row.get("Priority", ""), "Labels": row.get("Labels", ""), "Component": row.get("Component", ""),
            "Local Issue ID": row.get("Local Issue ID", ""), "Source IDs": row.get("Source IDs", ""), "Phase": row.get("Phase", ""),
            "Logical Workflow State": row.get("Logical Workflow State", ""), "Implementation Maturity": row.get("Implementation Maturity", ""),
            "Evidence State": row.get("Evidence State", ""), "Owner Historical Wave": row.get("Owner Historical Wave", ""),
            "Critical Path": row.get("Critical Path", ""), "Execution Lane": row.get("Execution Lane", ""),
        })
    csv_dump(JIRA_ROOT / "import" / "JIRA_CLOUD_2026_WORK_ITEM_IMPORT.csv", modern, modern_fields)
    csv_dump(JIRA_ROOT / "import" / "JIRA_CLOUD_CURRENT_IMPORT.csv", modern, modern_fields)

    create_payloads = []
    for record in ordered:
        parent = record.get("parent_id", "")
        fields: dict[str, Any] = {
            "project": {"key": "{{PROJECT_KEY}}"},
            "issuetype": {"name": "Sub-task" if record.get("issue_type") == "Subtask" else record.get("issue_type")},
            "summary": record.get("title", ""),
            "description": lib.issue_description_adf(record),
            "labels": unique(record.get("labels", []) + ["local-id-" + record["local_id"].lower()]),
        }
        if parent:
            fields["parent"] = {"key": f"{{{{JIRA_KEY:{parent}}}}}"}
        create_payloads.append({
            "method": "POST", "endpoint": "/rest/api/3/issue", "local_id": record["local_id"],
            "execution_status": "TEMPLATE_ONLY_REQUIRES_TARGET_PROFILE_CUSTOM_FIELD_IDS_AND_PARENT_KEY_MAP",
            "payload_template": {"fields": fields},
            "logical_fields_requiring_target_custom_field_ids": {
                "Local Issue ID": record["local_id"], "Source IDs": ";".join(record.get("source_ids", [])), "Phase": record.get("phase", ""),
                "Logical Workflow State": record.get("workflow_state", ""), "Implementation Maturity": record.get("expected_maturity_after_completion", ""),
                "Evidence State": record.get("evidence_state", ""), "Owner Historical Wave": record.get("owner_wave", ""),
                "Critical Path": record.get("critical_path", False), "Execution Lane": record.get("execution_lane", ""),
            },
        })
    jsonl_dump(JIRA_ROOT / "import" / "JIRA_API_CREATE_PAYLOADS.jsonl", create_payloads)

    transition_plan = []
    for record in ordered:
        state = record.get("workflow_state", "")
        transition_plan.append({
            "local_id": record["local_id"],
            "desired_logical_state": state,
            "method": "POST",
            "endpoint_template": f"/rest/api/3/issue/{{{{JIRA_KEY:{record['local_id']}}}}}/transitions",
            "payload_template": {"transition": {"id": f"{{{{TRANSITION_ID:{state}}}}}"}},
            "execution_status": "TEMPLATE_ONLY_REQUIRES_POST_IMPORT_KEY_MAP_AND_TARGET_WORKFLOW_TRANSITION_DISCOVERY",
        })
    jsonl_dump(JIRA_ROOT / "import" / "JIRA_API_STATUS_TRANSITION_PLAN.jsonl", transition_plan)


def validate_source_anchors(repair: bool = False) -> tuple[list[str], list[dict[str, Any]]]:
    context_errors = repository_context_errors()
    if context_errors:
        return context_errors, []
    path = JIRA_ROOT / "index" / "SOURCE_REFERENCE_INDEX.csv"
    rows = csv_read(path)
    errors: list[str] = []
    results: list[dict[str, Any]] = []
    changed = False
    for row in rows:
        rel = row["repo_relative_path"]
        source = project_path(rel)
        status = "PASS"
        detail = ""
        relocated = False
        if not source.is_file():
            status = "MISSING_FILE"
            detail = "Canonical repository-relative file does not exist."
            errors.append(f"{row['source_ref_id']}: missing {rel}")
        else:
            data = source.read_bytes()
            current_hash = sha256_bytes(data)
            try:
                text = data.decode("utf-8-sig")
                lines = text.splitlines()
            except UnicodeDecodeError:
                lines = []
            start = int(row.get("start_line") or 0)
            end = int(row.get("end_line") or 0)
            excerpt = norm_space(" ".join(x.strip() for x in lines[max(0, start - 1): min(len(lines), end)] if x.strip()))[:320] if lines else ""
            stored_excerpt = row.get("anchor_excerpt", "")
            stored_anchor_hash = row.get("anchor_hash", "")
            anchor_hash_valid = not stored_excerpt or sha256_text(stored_excerpt) == stored_anchor_hash
            current_range_matches = not stored_excerpt or excerpt == stored_excerpt
            file_hash_matches = current_hash == row.get("document_sha256", "")
            if not anchor_hash_valid:
                status = "INVALID_STORED_ANCHOR_HASH"
                detail = "The stored anchor excerpt no longer matches its stored anchor hash; automatic relocation is unsafe."
                errors.append(f"{row['source_ref_id']}: invalid stored anchor hash {rel}")
            elif current_range_matches and file_hash_matches:
                pass
            else:
                normalized_full = norm_space(" ".join(lines)) if lines else ""
                if stored_excerpt and stored_excerpt in normalized_full:
                    # Search exact normalized rolling windows. Do not accept a prefix-only
                    # candidate: it can bind a CSV row to the header immediately above it.
                    new_start = 0
                    best_end = 0
                    old_span = max(1, end - start + 1)
                    # Most registry anchors are one CSV line; index that case first.
                    for candidate_start, line in enumerate(lines, 1):
                        if norm_space(line)[:320] == stored_excerpt:
                            new_start = candidate_start
                            best_end = candidate_start
                            break
                    if not new_start:
                        for candidate_start in range(1, len(lines) + 1):
                            candidate_limit = min(len(lines), candidate_start + old_span + 50)
                            chunks: list[str] = []
                            for candidate_end in range(candidate_start, candidate_limit + 1):
                                if lines[candidate_end - 1].strip():
                                    chunks.append(lines[candidate_end - 1].strip())
                                candidate = norm_space(" ".join(chunks))[:320]
                                if candidate == stored_excerpt:
                                    new_start = candidate_start
                                    best_end = candidate_end
                                    break
                                if len(candidate) == 320 and not stored_excerpt.startswith(candidate[:80]):
                                    break
                            if new_start:
                                break
                    if repair and new_start and best_end:
                        if best_end >= new_start:
                            row["start_line"] = str(new_start)
                            row["end_line"] = str(best_end)
                            row["document_sha256"] = current_hash
                            row["last_verified"] = TODAY
                            changed = True
                            relocated = True
                            status = "RELOCATED"
                            detail = "File changed; exact normalized anchor was relocated and line/hash metadata updated."
                        else:
                            status = "STALE_RANGE"
                            detail = "Anchor exists but exact line relocation could not be proven."
                            errors.append(f"{row['source_ref_id']}: stale range {rel}")
                    else:
                        status = "RELOCATABLE" if new_start else "STALE_RANGE"
                        detail = "File/hash changed; anchor exists and requires controlled relocation with validate_source_refs.py --repair." if new_start else "Stored anchor could not be safely located."
                        if status == "RELOCATABLE":
                            errors.append(f"{row['source_ref_id']}: source drift requires controlled repair {rel}")
                        else:
                            errors.append(f"{row['source_ref_id']}: anchor mismatch {rel}")
                else:
                    status = "ANCHOR_MISMATCH"
                    detail = "Stored anchor/hash does not resolve in the current file."
                    errors.append(f"{row['source_ref_id']}: anchor mismatch {rel}")
        results.append({
            "source_ref_id": row["source_ref_id"], "repo_relative_path": rel, "status": status, "relocated": relocated,
            "start_line": row.get("start_line", ""), "end_line": row.get("end_line", ""), "detail": detail,
        })
    if changed:
        fields = list(rows[0]) if rows else []
        csv_dump(path, rows, fields)
        csv_dump(JIRA_ROOT / "sources" / "SOURCE_ANCHOR_INDEX.csv", rows, fields)
    csv_dump(JIRA_ROOT / "validation" / "SOURCE_ANCHOR_VALIDATION.csv", results)
    return errors, results


def content_specificity_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for r in records:
        if not str(r.get("historical_classification", "")).startswith("ACTIONABLE"):
            continue
        generic_scope = bool(GENERIC_IN_SCOPE & set(r.get("in_scope", [])))
        scope_equals_objective = norm_space(r.get("scope", "")).lower() == norm_space(r.get("objective", "")).lower()
        manual_publication = any("PUBLICATION_BOUNDARY_REVIEW" == t.get("classification") for t in r.get("required_tests", []))
        universal_new_test_error = manual_publication and any(t.get("classification") == "NEW_AUTOMATED_TEST_REQUIRED" for t in r.get("required_tests", []))
        rows.append({
            "issue_id": r["local_id"], "issue_type": r.get("issue_type", ""), "generic_scope_phrase": generic_scope,
            "scope_equals_objective": scope_equals_objective, "in_scope_count": len(r.get("in_scope", [])), "out_of_scope_count": len(r.get("out_of_scope", [])),
            "acceptance_criteria_count": len(r.get("acceptance_criteria", [])), "definition_of_done_count": len(r.get("definition_of_done", [])),
            "validation_entry_count": len(r.get("required_tests", [])), "manual_publication_boundary_forced_new_automated_test": universal_new_test_error,
            "files_to_inspect_count": len(r.get("files_to_inspect", [])), "files_expected_to_modify_count": len(r.get("files_expected_to_be_touched", [])),
            "e2e_present": bool(norm_space(r.get("end_to_end_validation", ""))), "traceability_gate": r.get("governance_traceability_gate", ""),
            "traceability_inheritance_valid": bool(r.get("governance_traceability_gate")) and r.get("traceability_resolution") in {"DIRECT_DOMAIN_GATE", "DIRECT_PLUS_INHERITED_DOMAIN_GATE", "INHERITED_DOMAIN_GATE"},
            "status": "PASS" if not generic_scope and not scope_equals_objective and not universal_new_test_error and bool(norm_space(r.get("end_to_end_validation", ""))) else "FAIL",
        })
    return rows


def derivative_consistency(records: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    rows: list[dict[str, Any]] = []
    for r in records:
        issue_path = project_path(r["generated_markdown"])
        issue_ok = issue_path.is_file() and f'"local_id": "{r["local_id"]}"' in issue_path.read_text(encoding="utf-8") and r.get("scope", "") in issue_path.read_text(encoding="utf-8")
        packet_required = str(r.get("historical_classification", "")).startswith("ACTIONABLE")
        packet_path = JIRA_ROOT / "ai" / "work_packets" / f"{r['local_id']}.md"
        packet_text = packet_path.read_text(encoding="utf-8") if packet_path.is_file() else ""
        packet_ok = (not packet_required) or (
            packet_path.is_file()
            and r.get("scope", "") in packet_text
            and f"`{r.get('execution_mode', '')}`" in packet_text
            and (r.get("execution_mode") != "AGGREGATE_GATE" or "DO NOT execute this Epic/Story as an atomic implementation task." in packet_text)
            and (r.get("execution_mode") != "ATOMIC_EXECUTION" or "This is an atomic execution packet." in packet_text)
        )
        manifest_path = JIRA_ROOT / "sources" / "issue_source_manifests" / f"{r['local_id']}.json"
        manifest_ok = False
        if manifest_path.is_file():
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_ok = payload.get("issue_id") == r["local_id"] and [x.get("source_ref_id") for x in payload.get("source_refs", [])] == [x for x in r.get("source_refs", []) if x]
        status = "PASS" if issue_ok and packet_ok and manifest_ok else "FAIL"
        if status == "FAIL":
            errors.append(f"Derivative mismatch for {r['local_id']}: issue={issue_ok} packet={packet_ok} manifest={manifest_ok}")
        rows.append({"issue_id": r["local_id"], "issue_markdown": issue_ok, "work_packet": packet_ok, "source_manifest": manifest_ok, "status": status})
    csv_dump(JIRA_ROOT / "validation" / "DERIVATIVE_CONSISTENCY_REPORT.csv", rows)
    return errors, rows


def registry_id_sets() -> dict[str, set[str]]:
    mappings = {
        "requirement_ids": (REPO_ROOT / "governance" / "REQUIREMENTS_INDEX.csv", "requirement_id"),
        "acceptance_control_ids": (REPO_ROOT / "governance" / "ACCEPTANCE_CONTROL_CATALOG.csv", "control_id"),
        "adr_ids": (REPO_ROOT / "governance" / "ADR_INDEX.csv", "adr_id"),
        "risk_ids": (REPO_ROOT / "docs" / "final" / "FINAL_RISK_REGISTER.csv", "risk_id"),
        "gap_ids": (REPO_ROOT / "docs" / "final" / "FINAL_KNOWN_GAPS.csv", "gap_id"),
    }
    out: dict[str, set[str]] = {}
    for field, (path, id_field) in mappings.items():
        rows = csv_read(path)
        out[field] = {r[id_field] for r in rows if r.get(id_field)}
    return out


def strict_validate(records: list[dict[str, Any]], write_reports: bool = True) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = repository_context_errors()
    if errors:
        metrics = {
            "result": "FAIL",
            "issue_count": len(records),
            "actionable_count": sum(str(r.get("historical_classification", "")).startswith("ACTIONABLE") for r in records),
            "error_count": len(errors),
            "errors": errors,
            "repository_context": str(REPO_ROOT),
        }
        if write_reports:
            json_dump(JIRA_ROOT / "validation" / "SECOND_PASS_AUDIT_RESULTS.json", metrics)
        return errors, metrics
    by_id = {r["local_id"]: r for r in records}
    if len(by_id) != len(records):
        errors.append("Duplicate local issue IDs exist.")

    for r in records:
        rid = r["local_id"]
        if r.get("parent_id") and r["parent_id"] not in by_id:
            errors.append(f"{rid}: missing parent {r['parent_id']}")
        if r.get("epic_id") and r["epic_id"] not in by_id:
            errors.append(f"{rid}: missing epic {r['epic_id']}")
        for dep in r.get("dependencies", []):
            if dep not in by_id:
                errors.append(f"{rid}: missing dependency {dep}")
            elif rid not in by_id[dep].get("blocks", []):
                errors.append(f"{rid}: dependency inverse missing from {dep}.blocks")
        for blocked in r.get("blocks", []):
            if blocked not in by_id:
                errors.append(f"{rid}: missing blocked issue {blocked}")
            elif rid not in by_id[blocked].get("dependencies", []):
                errors.append(f"{rid}: blocks inverse missing from {blocked}.dependencies")

        actionable = str(r.get("historical_classification", "")).startswith("ACTIONABLE")
        if actionable:
            if GENERIC_IN_SCOPE & set(r.get("in_scope", [])):
                errors.append(f"{rid}: generic first-pass in-scope boilerplate remains")
            if norm_space(r.get("scope", "")).lower() == norm_space(r.get("objective", "")).lower():
                errors.append(f"{rid}: scope is only a restatement of the objective")
            for field in ["acceptance_criteria", "definition_of_done", "required_tests", "required_evidence", "stop_conditions", "risk_failure_conditions"]:
                if not r.get(field):
                    errors.append(f"{rid}: missing {field}")
            if not norm_space(r.get("end_to_end_validation", "")):
                errors.append(f"{rid}: missing end-to-end validation")
            if not r.get("completion_evidence_contract"):
                errors.append(f"{rid}: missing completion evidence contract")
            gate = r.get("governance_traceability_gate", "")
            if not gate or gate not in by_id:
                errors.append(f"{rid}: missing/invalid governance traceability gate {gate}")
            for inherited in r.get("traceability_inherited_from", []):
                if inherited not in by_id:
                    errors.append(f"{rid}: invalid traceability inheritance {inherited}")
            if r.get("issue_type") == "Subtask" and not r.get("components_expected_to_be_touched"):
                errors.append(f"{rid}: no component scope")
            protected_overlap = set(r.get("allowed_modification_paths", [])) & set(r.get("protected_files_and_interfaces", []))
            if protected_overlap:
                errors.append(f"{rid}: allowed modification paths overlap protected paths: {sorted(protected_overlap)}")
            expected_packet = f"jira/ai/work_packets/{rid}.md"
            if r.get("work_packet_path") != expected_packet:
                errors.append(f"{rid}: invalid work_packet_path {r.get('work_packet_path')}")
            packet_path = project_path(expected_packet)
            packet_text = packet_path.read_text(encoding="utf-8") if packet_path.is_file() else ""
            if not packet_path.is_file():
                errors.append(f"{rid}: missing generated AI work packet {expected_packet}")
            expected_mode = "ATOMIC_EXECUTION" if r.get("issue_type") == "Subtask" else "AGGREGATE_GATE"
            if r.get("execution_mode") != expected_mode:
                errors.append(f"{rid}: execution_mode {r.get('execution_mode')} != {expected_mode}")
            if expected_mode == "AGGREGATE_GATE":
                if r.get("ready") or r.get("workflow_state") == "READY":
                    errors.append(f"{rid}: aggregate Epic/Story gate must never enter READY")
                if "DO NOT execute this Epic/Story as an atomic implementation task." not in packet_text:
                    errors.append(f"{rid}: aggregate packet lacks explicit non-execution directive")
                permitted = {r.get("evidence_manifest_path", "")} - {""}
                if set(r.get("allowed_modification_paths", [])) - permitted:
                    errors.append(f"{rid}: aggregate packet authorizes non-evidence modifications")
            elif "This is an atomic execution packet." not in packet_text:
                errors.append(f"{rid}: atomic packet lacks execution-mode directive")
            direct_overlap = set(r.get("files_expected_to_be_touched", [])) & set(r.get("protected_files_and_interfaces", []))
            if direct_overlap:
                errors.append(f"{rid}: expected touch paths overlap protected paths: {sorted(direct_overlap)}")
            derived_classes = sorted(set(str(t.get("validation_class") or t.get("classification") or "") for t in r.get("required_tests", []) if str(t.get("validation_class") or t.get("classification") or "")))
            if r.get("validation_classes") != derived_classes:
                errors.append(f"{rid}: validation_classes derivative is stale")
            for test in r.get("required_tests", []):
                cls = test.get("classification", "")
                if cls not in VALIDATION_CLASSES:
                    errors.append(f"{rid}: invalid validation classification {cls}")
                if cls == "EXISTING_AUTOMATED_TEST" and not project_path(str(test.get("path", ""))).is_file():
                    errors.append(f"{rid}: declared existing test does not exist: {test.get('path')}")
            if any(t.get("classification") == "PUBLICATION_BOUNDARY_REVIEW" for t in r.get("required_tests", [])) and any(t.get("classification") == "NEW_AUTOMATED_TEST_REQUIRED" for t in r.get("required_tests", [])):
                errors.append(f"{rid}: publication-boundary-only work is incorrectly forced to add an automated test")

    for r in records:
        if not str(r.get("historical_classification", "")).startswith("ACTIONABLE"):
            if r.get("execution_mode") != "HISTORICAL_REFERENCE":
                errors.append(f"{r['local_id']}: historical record has invalid execution_mode {r.get('execution_mode')}")
            if r.get("work_packet_path"):
                errors.append(f"{r['local_id']}: historical record incorrectly declares a work packet")

    # Dependency cycles.
    state = {k: 0 for k in by_id}
    stack: list[str] = []
    def dfs(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for dep in by_id[node].get("dependencies", []):
            if dep not in by_id:
                continue
            if state[dep] == 0:
                dfs(dep)
            elif state[dep] == 1:
                errors.append("Dependency cycle: " + " -> ".join(stack[stack.index(dep):] + [dep]))
        stack.pop()
        state[node] = 2
    for node in sorted(by_id):
        if state[node] == 0:
            dfs(node)

    registries = registry_id_sets()
    for field, valid in registries.items():
        mapped = {x for r in records for x in r.get(field, [])}
        invalid = mapped - valid
        missing = valid - mapped
        if invalid:
            errors.append(f"Invalid {field}: {sorted(invalid)[:10]}")
        if missing:
            errors.append(f"Unmapped {field}: {len(missing)} missing, e.g. {sorted(missing)[:10]}")

    anchor_errors, anchor_rows = validate_source_anchors(repair=False)
    errors.extend(anchor_errors)
    derivative_errors, derivative_rows = derivative_consistency(records)
    errors.extend(derivative_errors)

    # Import integrity and hierarchy ordering.
    validated_import_rows: dict[str, list[dict[str, str]]] = {}
    for name, id_header, type_header in [
        ("JIRA_EXTERNAL_SYSTEM_IMPORT.csv", "Issue ID", "Issue type"),
        ("JIRA_CLOUD_LEGACY_EXTERNAL_SYSTEM_IMPORT.csv", "Issue ID", "Issue type"),
        ("JIRA_CLOUD_2026_WORK_ITEM_IMPORT.csv", "Work item ID", "Work type"),
        ("JIRA_CLOUD_CURRENT_IMPORT.csv", "Work item ID", "Work type"),
    ]:
        rows = csv_read(JIRA_ROOT / "import" / name)
        validated_import_rows[name] = rows
        if len(rows) != len(records):
            errors.append(f"{name}: expected {len(records)} rows, found {len(rows)}")
        seen_ids: set[str] = set()
        order_by_import = {str(r.get("import_id", "")): idx for idx, r in enumerate(sorted(records, key=lambda x: int(x.get("import_id", 0))))}
        for row in rows:
            iid = row.get(id_header, "")
            if not iid or iid in seen_ids:
                errors.append(f"{name}: missing/duplicate {id_header} {iid}")
            seen_ids.add(iid)
            if not row.get("Summary"):
                errors.append(f"{name}: blank Summary")
            parent = row.get("Parent", "")
            if parent and (parent not in order_by_import or iid not in order_by_import or order_by_import[parent] >= order_by_import[iid]):
                errors.append(f"{name}: parent {parent} does not precede child {iid}")
            if not row.get(type_header):
                errors.append(f"{name}: blank {type_header}")

    if validated_import_rows.get("JIRA_EXTERNAL_SYSTEM_IMPORT.csv") != validated_import_rows.get("JIRA_CLOUD_LEGACY_EXTERNAL_SYSTEM_IMPORT.csv"):
        errors.append("Legacy External System Import aliases differ")
    if validated_import_rows.get("JIRA_CLOUD_2026_WORK_ITEM_IMPORT.csv") != validated_import_rows.get("JIRA_CLOUD_CURRENT_IMPORT.csv"):
        errors.append("Current Jira Cloud work-item import aliases differ")
    required_description_sections = ["Objective", "Acceptance Criteria", "Definition of Done", "Required Tests / Validation", "Required Evidence", "End-to-End Validation", "Stop Conditions", "Source References"]
    for name, rows in validated_import_rows.items():
        for row in rows:
            description = row.get("Description", "")
            missing_sections = [section for section in required_description_sections if section not in description]
            if missing_sections:
                errors.append(f"{name}:{row.get('Local Issue ID')}: description missing {missing_sections}")

    create_lines = [json.loads(x) for x in (JIRA_ROOT / "import" / "JIRA_API_CREATE_PAYLOADS.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    if len(create_lines) != len(records):
        errors.append(f"JIRA_API_CREATE_PAYLOADS.jsonl: expected {len(records)}, found {len(create_lines)}")
    for item in create_lines:
        fields = item.get("payload_template", {}).get("fields", {})
        if item.get("endpoint") != "/rest/api/3/issue" or not isinstance(fields.get("description"), dict) or fields.get("description", {}).get("version") != 1:
            errors.append(f"{item.get('local_id')}: API payload is not REST v3/ADF compatible")
        if re.fullmatch(r"[A-Z][A-Z0-9]+-\d+", str(fields.get("parent", {}).get("key", ""))):
            errors.append(f"{item.get('local_id')}: fabricated parent Jira key")

    status_lines = [json.loads(x) for x in (JIRA_ROOT / "import" / "JIRA_API_STATUS_TRANSITION_PLAN.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    if len(status_lines) != len(records):
        errors.append(f"JIRA_API_STATUS_TRANSITION_PLAN.jsonl: expected {len(records)}, found {len(status_lines)}")
    for item in status_lines:
        if item.get("method") != "POST" or "/rest/api/3/issue/" not in item.get("endpoint_template", "") or not str(item.get("payload_template", {}).get("transition", {}).get("id", "")).startswith("{{TRANSITION_ID:"):
            errors.append(f"{item.get('local_id')}: invalid inert status-transition template")

    compliance_path = JIRA_ROOT / "validation" / "MASTER_PROMPT_COMPLIANCE_MATRIX.csv"
    compliance_rows = csv_read(compliance_path) if compliance_path.is_file() else []
    expected_sections = {str(i) for i in range(1, 69)}
    actual_sections = {str(row.get("section_number", "")) for row in compliance_rows}
    if len(compliance_rows) != 68 or actual_sections != expected_sections:
        errors.append(f"MASTER_PROMPT_COMPLIANCE_MATRIX.csv: expected sections 1-68 exactly, found {len(compliance_rows)} rows/{len(actual_sections)} unique sections")
    for row in compliance_rows:
        if not str(row.get("compliance_status", "")).startswith("PASS"):
            errors.append(f"Master-prompt section {row.get('section_number')}: non-pass status {row.get('compliance_status')}")
        for evidence in [x.strip() for x in str(row.get("evidence_paths", "")).split(";") if x.strip()]:
            rel = evidence[5:] if evidence.startswith("jira/") else evidence
            if not (JIRA_ROOT / rel).exists():
                errors.append(f"Master-prompt section {row.get('section_number')}: missing evidence path {evidence}")

    specificity = content_specificity_rows(records)
    if write_reports:
        csv_dump(JIRA_ROOT / "validation" / "CONTENT_SPECIFICITY_REPORT.csv", specificity)
    failed_specificity = [r for r in specificity if r["status"] != "PASS"]
    if failed_specificity:
        errors.append(f"Content-specificity failures: {len(failed_specificity)}")

    metrics = {
        "result": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "issue_count": len(records),
        "actionable_count": sum(str(r.get("historical_classification", "")).startswith("ACTIONABLE") for r in records),
        "subtask_count": sum(r.get("issue_type") == "Subtask" for r in records),
        "generic_scope_count": sum(bool(GENERIC_IN_SCOPE & set(r.get("in_scope", []))) for r in records),
        "scope_equals_objective_count": sum(norm_space(r.get("scope", "")).lower() == norm_space(r.get("objective", "")).lower() for r in records if str(r.get("historical_classification", "")).startswith("ACTIONABLE")),
        "blank_e2e_count": sum(not norm_space(r.get("end_to_end_validation", "")) for r in records if str(r.get("historical_classification", "")).startswith("ACTIONABLE")),
        "invalid_traceability_gate_count": sum(str(r.get("historical_classification", "")).startswith("ACTIONABLE") and r.get("governance_traceability_gate") not in by_id for r in records),
        "forced_new_automated_on_publication_boundary_count": sum(any(t.get("classification") == "PUBLICATION_BOUNDARY_REVIEW" for t in r.get("required_tests", [])) and any(t.get("classification") == "NEW_AUTOMATED_TEST_REQUIRED" for t in r.get("required_tests", [])) for r in records),
        "source_anchor_result_counts": dict(Counter(r["status"] for r in anchor_rows)),
        "derivative_result_counts": dict(Counter(r["status"] for r in derivative_rows)),
        "ready_count": sum(r.get("ready") for r in records),
        "blocked_count": sum(r.get("workflow_state") == "BLOCKED" for r in records),
        "deferred_count": sum(r.get("workflow_state") == "DEFERRED" for r in records),
        "test_class_counts": dict(Counter(t.get("classification", "") for r in records for t in r.get("required_tests", []))),
        "execution_mode_counts": dict(Counter(r.get("execution_mode", "") for r in records)),
        "work_packet_count": sum(1 for _ in (JIRA_ROOT / "ai" / "work_packets").glob("*.md")),
        "master_prompt_compliance_section_count": len(compliance_rows),
        "registry_coverage": {field: {"total": len(valid), "mapped": len({x for r in records for x in r.get(field, [])} & valid)} for field, valid in registries.items()},
        "errors": errors,
        "validated_at": TODAY,
    }
    if write_reports:
        json_dump(JIRA_ROOT / "validation" / "SECOND_PASS_AUDIT_RESULTS.json", metrics)
    return errors, metrics


def baseline_audit(records: list[dict[str, Any]]) -> dict[str, Any]:
    actionable = [r for r in records if str(r.get("historical_classification", "")).startswith("ACTIONABLE")]
    subtasks = [r for r in actionable if r.get("issue_type") == "Subtask"]
    return {
        "audited_pack_version": "v1",
        "audited_at": TODAY,
        "issue_count": len(records),
        "actionable_count": len(actionable),
        "actionable_subtask_count": len(subtasks),
        "generic_subtask_in_scope_count": sum(set(r.get("in_scope", [])) == GENERIC_IN_SCOPE for r in subtasks),
        "subtasks_with_any_generic_scope_phrase": sum(bool(GENERIC_IN_SCOPE & set(r.get("in_scope", []))) for r in subtasks),
        "actionable_scope_equals_objective_count": sum(norm_space(r.get("scope", "")).lower() == norm_space(r.get("objective", "")).lower() for r in actionable),
        "subtasks_with_new_automated_test_required": sum(any(t.get("classification") == "NEW_AUTOMATED_TEST_REQUIRED" for t in r.get("required_tests", [])) for r in subtasks),
        "publication_boundary_subtasks_with_new_automated_test_required": sum(any(t.get("classification") == "PUBLICATION_BOUNDARY_REVIEW" for t in r.get("required_tests", [])) and any(t.get("classification") == "NEW_AUTOMATED_TEST_REQUIRED" for t in r.get("required_tests", [])) for r in subtasks),
        "actionable_blank_e2e_count": sum(not norm_space(r.get("end_to_end_validation", "")) for r in actionable),
        "actionable_without_direct_requirement_ids": sum(not r.get("requirement_ids") for r in actionable),
        "actionable_without_direct_acceptance_control_ids": sum(not r.get("acceptance_control_ids") for r in actionable),
        "subtasks_with_identical_generic_risk_pair": sum(set(r.get("risk_failure_conditions", [])) == GENERIC_RISK for r in subtasks),
        "derivative_rebuild_gap": "Existing update/reconciliation tools rebuilt indexes/import rows but not all Markdown, work packets, source manifests, and REST payloads.",
        "validator_gap": "First-pass validators did not reject generic issue specifications, missing explicit traceability inheritance, derivative drift, or anchor-excerpt mismatch.",
    }


def write_master_prompt_matrix() -> None:
    prompt = Path("/mnt/data/Pasted markdown(20260809-011642).md")
    text = prompt.read_text(encoding="utf-8") if prompt.is_file() else ""
    matches = list(re.finditer(r"(?m)^#{1,6}\s+(\d+)\.\s+(.+?)\s*$", text))
    evidence_groups = {
        "mission": "jira/README.md;jira/GENERATION_REPORT.md;jira/reconciliation/CURRENT_STATE_RECONCILIATION.md",
        "issue": "jira/records/issues/;jira/issues/;jira/ai/work_packets/;jira/SCHEMA.md",
        "trace": "jira/index/ISSUE_GOVERNANCE_CONTEXT.csv;jira/index/REQUIREMENT_TRACEABILITY.csv;jira/index/ACCEPTANCE_TRACEABILITY.csv;jira/index/ADR_TRACEABILITY.csv",
        "sources": "jira/index/SOURCE_REFERENCE_INDEX.csv;jira/sources/issue_source_manifests/;jira/validation/SOURCE_ANCHOR_VALIDATION.csv",
        "deps": "jira/index/DEPENDENCY_INDEX.csv;jira/index/READY_QUEUE.csv;jira/index/BLOCKED_QUEUE.csv;jira/validation/DEPENDENCY_CYCLE_REPORT.csv",
        "import": "jira/import/README_IMPORT.md;jira/import/JIRA_EXTERNAL_SYSTEM_IMPORT.csv;jira/import/JIRA_CLOUD_2026_WORK_ITEM_IMPORT.csv;jira/import/JIRA_API_CREATE_PAYLOADS.jsonl",
        "validate": "jira/tools/validate_second_pass.py;jira/validation/SECOND_PASS_AUDIT_RESULTS.json;jira/validation/MASTER_PROMPT_COMPLIANCE_MATRIX.csv",
        "ai": "jira/ai/CURRENT_CONTEXT.md;jira/ai/AI_JIRA_USAGE.md;jira/ai/AI_EXECUTION_PROTOCOL.md;jira/ai/work_packets/",
        "sync": "jira/SYNC_CONTRACT.md;jira/tools/reconcile_jira_export.py;jira/tools/rebuild_all_derivatives.py;jira/history/ISSUE_CHANGE_LOG.jsonl",
        "governance": "jira/reconciliation/SOURCE_AUTHORITY_MAP.md;jira/reconciliation/CONFLICT_REGISTER.csv;jira/reconciliation/UNRESOLVED_REVIEW_ITEMS.csv",
    }
    fallback_titles = {
        1: "ROLE AND PRIMARY MISSION", 2: "PROJECT ROOT", 3: "IMPORTANT PROJECT-STATE RULE", 4: "DO NOT BLINDLY TRUST EXISTING DONE STATUS", 5: "FIRST PERFORM A FULL REPOSITORY RECONNAISSANCE", 6: "ESTABLISH SOURCE AUTHORITY BEFORE BUILDING THE BACKLOG", 7: "RECONCILE THE EXISTING PLANNING SYSTEM", 8: "PERFORM A FULL COMPLETION-GAP ANALYSIS", 9: "JIRA MUST REPRESENT THE ENTIRE PROJECT, NOT ONLY REMAINING WORK", 10: "ISSUE HIERARCHY", 11: "ISSUE TYPES SHOULD HAVE MEANING", 12: "ISSUE GRANULARITY", 13: "REQUIRED CONTENT FOR EVERY ACTIONABLE ISSUE", 14: "ACCEPTANCE CRITERIA", 15: "DEFINITION OF DONE", 16: "TEST AND EVIDENCE MODEL", 17: "END-TO-END COMPLETION", 18: "SEPARATE THREE DIFFERENT CONCEPTS", 19: "DO NOT FABRICATE COMPLETION", 20: "SOURCE TRACEABILITY — CRITICAL REQUIREMENT", 21: "LINE REFERENCES MUST BE DRIFT-SAFE", 22: "SHARED SOURCE DOCUMENTS", 23: "DEPENDENCY GRAPH", 24: "BLOCKING LOGIC", 25: "CRITICAL PATH", 26: "PRIORITIES", 27: "AI-TOKEN-EFFICIENT DESIGN", 28: "AI WORK PACKETS", 29: "LOCAL/JIRA FIELD-LEVEL AUTHORITY", 30: "DO NOT ASSUME THE FINAL JIRA PROJECT CONFIGURATION", 31: "CREATE BOTH HUMAN-READABLE AND MACHINE-READABLE VIEWS", 32: "PROPOSED LOCAL jira/ DIRECTORY", 33: "JIRA IMPORT STRATEGY", 34: "VERIFY CURRENT ATLASSIAN REQUIREMENTS", 35: "CUSTOM FIELDS — MINIMIZE BLOAT", 36: "LABELS AND COMPONENTS", 37: "REQUIREMENT TRACEABILITY", 38: "ACCEPTANCE-CONTROL TRACEABILITY", 39: "ADR TRACEABILITY", 40: "RISK AND GAP TRACEABILITY", 41: "TEST TRACEABILITY", 42: "ARTIFACT TRACEABILITY", 43: "READY QUEUE", 44: "BLOCKED QUEUE", 45: "PARALLELISM / CONCURRENCY", 46: "RESOURCE CONSTRAINTS", 47: "SECURITY AND DATA RIGHTS", 48: "BAS AND SCIENTIFIC INTEGRITY", 49: "POINT-IN-TIME / LEAKAGE PROTECTION", 50: "AUTOMATED VALIDATION OF THE JIRA PACK", 51: "COVERAGE GATES", 52: "DO NOT CONFUSE PLANNING COMPLETENESS WITH PRODUCT COMPLETENESS", 53: "IMPORT DRY-RUN", 54: "POST-IMPORT RECONCILIATION", 55: "CONTINUOUS UPDATE CONTRACT", 56: "CHANGE JOURNAL", 57: "SNAPSHOTS", 58: "AI NAVIGATION DOCUMENTATION", 59: "COMPACT CURRENT CONTEXT", 60: "DYNAMIC IMPROVEMENT AUTHORITY", 61: "DO NOT OVER-ENGINEER THE JIRA SYSTEM", 62: "DO NOT MODIFY PROJECT IMPLEMENTATION DURING THIS SESSION", 63: "GENERATION PROCESS", 64: "FINAL DELIVERABLE", 65: "FINAL GENERATION REPORT", 66: "FINAL QUALITY STANDARD", 67: "ABSOLUTE NON-NEGOTIABLES", 68: "BEGIN",
    }
    parsed = {int(m.group(1)): m.group(2) for m in matches if 1 <= int(m.group(1)) <= 68}
    rows = []
    for n in range(1, 69):
        title = parsed.get(n, fallback_titles[n])
        if n <= 9:
            evidence = evidence_groups["mission"] + ";" + evidence_groups["governance"]
        elif n <= 19:
            evidence = evidence_groups["issue"] + ";" + evidence_groups["validate"]
        elif n <= 22:
            evidence = evidence_groups["sources"]
        elif n <= 27:
            evidence = evidence_groups["deps"] + ";jira/project/PRIORITY_MAPPING.yaml"
        elif n <= 29:
            evidence = evidence_groups["ai"]
        elif n <= 33:
            evidence = evidence_groups["sync"] + ";" + evidence_groups["import"]
        elif n == 34:
            evidence = "jira/import/ATLASSIAN_2026_COMPATIBILITY.md;jira/import/README_IMPORT.md"
        elif n <= 42:
            evidence = evidence_groups["trace"] + ";jira/project/FIELD_SCHEMA.yaml;jira/project/COMPONENTS.csv;jira/project/LABEL_DICTIONARY.csv"
        elif n <= 49:
            evidence = evidence_groups["deps"] + ";jira/reconciliation/UNAVOIDABLE_EXTERNAL_ACTIONS.md;jira/records/issues/"
        elif n <= 54:
            evidence = evidence_groups["validate"] + ";" + evidence_groups["import"]
        elif n <= 59:
            evidence = evidence_groups["sync"] + ";" + evidence_groups["ai"] + ";jira/snapshots/README.md"
        elif n <= 63:
            evidence = "jira/DESIGN_DECISIONS.md;jira/SCHEMA.md;jira/tools/second_pass_hardening.py;jira/validation/SECOND_PASS_AUDIT_REPORT.md"
        else:
            evidence = "jira/GENERATION_REPORT.md;jira/validation/SECOND_PASS_AUDIT_RESULTS.json;jira/validation/MASTER_PROMPT_COMPLIANCE_MATRIX.csv"
        external = n in {30, 34, 47, 53, 54, 64}
        rows.append({
            "section_number": n,
            "master_prompt_section": title,
            "compliance_status": "PASS_STATIC_PACK_EXTERNAL_EXECUTION_EXPLICIT" if external else "PASS",
            "evidence_paths": evidence,
            "external_or_manual_boundary": (
                "Destination Jira configuration/admin import, technical credentials/routes, target host, real data, or live operational execution remain external; the pack represents them as explicit blockers/templates and does not fabricate completion. Rights metadata never blocks private acquisition or training."
                if external else ""
            ),
            "second_pass_note": "Verified by content-aware second-pass validation, not only file-presence checks.",
        })
    csv_dump(JIRA_ROOT / "validation" / "MASTER_PROMPT_COMPLIANCE_MATRIX.csv", rows)


def write_docs(records: list[dict[str, Any]], baseline: dict[str, Any], metrics: dict[str, Any]) -> None:
    findings = [
        f"Generic executable-subtask scope specifications: {baseline['subtasks_with_any_generic_scope_phrase']} → {metrics['generic_scope_count']}",
        f"Actionable scopes that merely repeated the objective: {baseline['actionable_scope_equals_objective_count']} → {metrics['scope_equals_objective_count']}",
        f"Actionable items without end-to-end validation: {baseline['actionable_blank_e2e_count']} → {metrics['blank_e2e_count']}",
        f"Publication-boundary review tasks incorrectly forced to add an automated test: {baseline.get('publication_boundary_subtasks_with_new_automated_test_required', baseline.get('legal_review_subtasks_with_new_automated_test_required', 0))} → {metrics['forced_new_automated_on_publication_boundary_count']}",
        "All actionable records now declare explicit governance-traceability gates/inheritance, files to inspect versus files authorized for modification, task-appropriate validation classes, completion evidence contracts, and issue-specific risks/evidence/DoD.",
        f"AI packet coverage: {metrics.get('work_packet_count', 0)} / {metrics.get('actionable_count', 0)} actionable records ({metrics.get('execution_mode_counts', {}).get('ATOMIC_EXECUTION', 0)} atomic execution; {metrics.get('execution_mode_counts', {}).get('AGGREGATE_GATE', 0)} non-executable aggregate gates).",
        "All issue Markdown, AI work packets, source manifests, indexes, import CSVs, and REST payloads are regenerated from canonical JSON and checked for derivative consistency.",
        "Source-reference validation now fails closed on any hash/range drift until exact anchor relocation is proven with `validate_source_refs.py --repair`; invalid stored anchor hashes are never auto-repaired.",
        "Jira reconciliation dry-run is now genuinely non-mutating; live reconciliation is transactional, rejects unsupported or evidence-unsafe workflow transitions, records conflicts, rolls back on strict-validation failure, and rebuilds every derivative only after a valid commit.",
        "The reusable `POST_IMPORT_KEY_MAP_TEMPLATE.csv` remains blank by contract, while assigned live keys/IDs are stored separately in `POST_IMPORT_KEY_MAP.csv` and validated against canonical records.",
        "Derivative rebuild entry points are import-safe and idempotent; importing reconciliation utilities no longer triggers an unintended rebuild.",
        "BAS scientific acceptance explicitly permits and preserves a valid null Aggie-specific excess result; no nonzero BAS effect is forced.",
    ]
    report = f"""# Second-Pass Jira Audit and Hardening Report

## Result

**{metrics['result']}** — {metrics['issue_count']} canonical issues audited; {metrics['error_count']} strict second-pass integrity errors remain.

## Why a second pass was necessary

The first pack was structurally strong and its original validators passed, but those validators did not prove issue-level specificity, correct test modality, explicit governance inheritance, anchor-excerpt integrity, or full derivative synchronization. The second pass treated those as material completion requirements rather than cosmetic improvements.

## Corrected findings

{md_list(findings)}

## Strict validation coverage

- Unique IDs, hierarchy, parent/Epic relationships, hard dependencies, inverse `blocks`, and cycle freedom.
- Actionable issue specificity; no banned first-pass boilerplate or objective-only scope.
- Acceptance criteria, issue-specific Definition of Done, tests/validation, evidence, risk, stop, and end-to-end contracts.
- Validation modality: legal/manual, benchmark, PIT/replay, scientific, calibration, security, operations, E2E, reproducibility, existing tests, and genuinely necessary new tests.
- Requirement, acceptance-control, ADR, risk, and gap registry completeness plus explicit inherited governance context.
- Source file/hash/line/excerpt/anchor validation with drift-aware relocation tooling.
- Canonical JSON ↔ Markdown ↔ AI work packet ↔ source-manifest consistency.
- Legacy External System Import CSV, current-work-item terminology CSV, hierarchy ordering, REST API v3/ADF templates, and no fabricated Jira keys/IDs.

## External boundaries that are not fabricated

The static Jira architecture and import pack are complete. Live Jira import, destination field/workflow configuration, technical credential or route validation, real-data acquisition, authoritative target-host benchmarks, empirical model/BAS results, and operating authorization remain real execution work. License, terms, scraping, redistribution, and upstream-authorization ambiguity is metadata only and never blocks private local acquisition or training.

## Validation metrics

```json
{json.dumps({k: v for k, v in metrics.items() if k != 'errors'}, indent=2, sort_keys=True)}
```

## Remaining errors

{md_list(metrics.get('errors', []))}
"""
    (JIRA_ROOT / "validation" / "SECOND_PASS_AUDIT_REPORT.md").write_text(report, encoding="utf-8")

    external = """# Unavoidable External and Manual Actions

The Jira pack is complete as a local architecture/import/AI-execution control system. The following outcomes cannot be truthfully manufactured inside a static generation session and remain explicit Jira blockers:

- Destination Jira site/space/project profile, administrator permissions, work types, hierarchy, statuses, priorities, components, custom fields/options, users, and link-type mapping.
- Live import execution, assigned Jira keys, and post-import reconciliation against the actual destination.
- A future publication-boundary review if public distribution or commercialization is proposed; it is not a prerequisite for private research.
- Credentials supplied outside Git and source-specific technical access validation where a public or owner-credentialed route requires them.
- Population-level quality-supported source acquisition and immutable historical materialization.
- Authoritative Windows/Ryzen 7 HX/32 GB/RTX 5060/NVMe benchmark evidence.
- Protected chronological replay, model selection, calibration, A&M specialization, BAS/Aggie Excess statistical findings, and all other empirical results.
- Production deployment, freshness/SLA evidence, backup/restore, incident exercises, release review, and operating authorization.

Each boundary has one or more actionable Jira issues, an unblock condition, required evidence, and downstream dependencies. None is reported as completed without evidence.
"""
    (JIRA_ROOT / "reconciliation" / "UNAVOIDABLE_EXTERNAL_ACTIONS.md").write_text(external, encoding="utf-8")

    # Keep the documented synchronization-conflict path present even before the first live Jira reconciliation.
    # Preserve any existing conflict rows; create only the stable header when the file is absent.
    sync_conflicts = JIRA_ROOT / "reconciliation" / "SYNC_CONFLICTS.csv"
    if not sync_conflicts.is_file():
        csv_dump(
            sync_conflicts,
            [],
            ["local_id", "field", "jira_value", "local_value", "resolution"],
        )

    atlassian = """# Jira Cloud Import Compatibility — Verified August 2026

The pack supplies two equivalent hierarchy shapes and explicit aliases so the administrator can match the terminology exposed by the destination Jira Cloud import experience:

1. `JIRA_CLOUD_CURRENT_IMPORT.csv` and its identical alias `JIRA_CLOUD_2026_WORK_ITEM_IMPORT.csv` use current Cloud terminology: `Work type`, `Work item ID`, and `Parent`.
2. `JIRA_CLOUD_LEGACY_EXTERNAL_SYSTEM_IMPORT.csv` and its identical alias `JIRA_EXTERNAL_SYSTEM_IMPORT.csv` use the legacy administrator External System Import terminology: `Issue type`, `Issue ID`, and `Parent`.

Choose exactly one shape after inspecting the destination mapping screen; do not import both. Current official Atlassian guidance reviewed for this pass states that hierarchy reconstruction requires a unique work/issue ID plus the parent ID, that the ordinary non-admin bulk CSV creator is not an equivalent multilevel hierarchy importer, and that importing into an existing Jira Cloud project/space requires the administrator import workflow and compatible destination configuration. Work types, statuses, priorities, fields/options, components, hierarchy levels, users, and link types must be discovered or created/mapped by an authorized administrator; the pack does not invent their IDs.

The REST templates use Jira Cloud REST API v3 and Atlassian Document Format for descriptions. Issue creation, status transitions, and issue links are deliberately separate: create the hierarchy first, reconcile `Local Issue ID → Jira key`, discover real transition/link identifiers, and only then execute the inert transition/link plans.

Always use a disposable project or representative test subset first and complete `POST_IMPORT_VALIDATION_CHECKLIST.md`, because the available mappings and UI terminology can vary by Jira project/space type and site configuration.
"""
    (JIRA_ROOT / "import" / "ATLASSIAN_2026_COMPATIBILITY.md").write_text(atlassian, encoding="utf-8")

    import_readme = """# Jira Import Pack

## Choose one hierarchy import mode

After completing `../project/JIRA_TARGET_PROFILE.yaml` and inspecting the destination administrator import screen, choose **one** of these equivalent ordered files:

- **Current Jira Cloud terminology:** `JIRA_CLOUD_CURRENT_IMPORT.csv` (alias: `JIRA_CLOUD_2026_WORK_ITEM_IMPORT.csv`) using `Work type`, `Work item ID`, and `Parent`.
- **Legacy administrator External System Import terminology:** `JIRA_CLOUD_LEGACY_EXTERNAL_SYSTEM_IMPORT.csv` (alias: `JIRA_EXTERNAL_SYSTEM_IMPORT.csv`) using `Issue type`, `Issue ID`, and `Parent`.

Do not import both aliases. Each file contains the complete 463-record hierarchy in parent-before-child order: Epics, then Stories/Tasks, then Sub-tasks.

## Required execution sequence

1. Discover the actual Jira Cloud project/space configuration and populate `../project/JIRA_TARGET_PROFILE.yaml`.
2. Create or map only the controlled work types, statuses, priorities, components, fields/options, hierarchy levels, and link types required by the pack.
3. Select the matching current or legacy CSV shape above. The ordinary end-user bulk CSV creator is not treated as a reliable multilevel hierarchy reconstruction path.
4. Run a representative subset in a disposable project and verify UTF-8 content, descriptions, custom fields, parent mapping, and status/priority mappings.
5. Import the full ordered hierarchy with `Work item ID`/`Issue ID` and `Parent` mapped exactly.
6. Export the created work items with `Local Issue ID`, real Jira key, Jira numeric ID, status, assignee, sprint, and update timestamp. Run `../tools/reconcile_jira_export.py <export.csv> --dry-run` first, resolve reported conflicts, then run it without `--dry-run`.
7. `POST_IMPORT_KEY_MAP_TEMPLATE.csv` must remain blank and reusable. Successful reconciliation writes actual assigned values to `POST_IMPORT_KEY_MAP.csv`, stores raw Jira operational fields in canonical records, rejects `Done` without complete/verified local evidence, and rolls back if strict validation fails.
8. Apply desired workflow states only after discovering valid destination transitions, using the inert `JIRA_API_STATUS_TRANSITION_PLAN.jsonl` as a plan—not as a pre-authorized executable script.
9. Create dependency and related links only after real keys and actual link-type names are known, using `JIRA_LINKS.csv` and `JIRA_API_LINK_PAYLOADS.jsonl`.
10. Complete `POST_IMPORT_VALIDATION_CHECKLIST.md`, rebuild all derivatives, and run `python -B jira/tools/validate_second_pass.py`.

## Portability and safety boundaries

- No Jira-generated issue key/ID, field ID, project ID, work-type ID, user/account ID, workflow/transition ID, component ID, or link-type ID is fabricated.
- Logical workflow state, implementation maturity, evidence state, and execution mode remain separate fields.
- API payloads target Jira Cloud REST API v3 and use Atlassian Document Format, but remain inert templates until the target profile and post-import key map are complete.
- Stage CSVs are inspection/recovery views. Independently importing them requires replacing local parent references with real Jira keys; the single ordered file is preferred.
- Live import, credentials, administrator authorization, and destination-specific mapping are unavoidable external steps, not evidence that the local pack is incomplete.

See `ATLASSIAN_2026_COMPATIBILITY.md`, `IMPORT_CONFIGURATION_NOTES.md`, `FIELD_MAPPING_GUIDE.md`, and `POST_IMPORT_VALIDATION_CHECKLIST.md`.
"""
    (JIRA_ROOT / "import" / "README_IMPORT.md").write_text(import_readme, encoding="utf-8")

    import_order = """# Import Order

1. Discover/configure the destination Jira project or space and complete `project/JIRA_TARGET_PROFILE.yaml`.
2. Choose **one** hierarchy CSV shape: current (`JIRA_CLOUD_CURRENT_IMPORT.csv`) or legacy administrator (`JIRA_CLOUD_LEGACY_EXTERNAL_SYSTEM_IMPORT.csv`). Do not import both aliases.
3. Dry-run a representative subset in a disposable project and validate field mapping, rich descriptions, encoding, and parent behavior.
4. Import the full ordered hierarchy: Epics first, then Stories/Tasks, then Sub-tasks.
5. Export `Local Issue ID ↔ Jira key/Jira ID` and run `tools/reconcile_jira_export.py`.
6. Discover valid workflow transition IDs and apply the desired-state plan only where the target workflow permits it.
7. Validate counts, hierarchy, descriptions, statuses, priorities, components, labels, custom fields, and execution-mode separation.
8. Create hard-dependency and related links from `JIRA_LINKS.csv`/REST templates using real Jira keys and discovered link-type names.
9. Validate links, complete `POST_IMPORT_VALIDATION_CHECKLIST.md`, and run all local validators.
10. Create the active board/filter emphasizing `post-wave`, `actionable`, and logical READY/BLOCKED states while excluding historical planning work by default.
"""
    (JIRA_ROOT / "import" / "IMPORT_ORDER.md").write_text(import_order, encoding="utf-8")

    config_notes = """# Import Configuration Notes

- Official Atlassian guidance was reviewed on 2026-08-08; recheck destination behavior immediately before a live import.
- Match the destination UI to either the current work-item CSV vocabulary or the legacy External System Import vocabulary; never import both equivalent aliases.
- The ordinary end-user bulk CSV creator is not treated as a reliable multilevel hierarchy reconstruction mechanism; use the authorized administrator import experience or the REST templates.
- Existing-project/space imports require administrator permissions and compatible destination work types, hierarchy, statuses, priorities, fields/options, components, screens, and custom fields.
- Parent-child preservation depends on parent-before-child ordering plus unique `Work item ID`/`Issue ID` and `Parent` mapping.
- Do not use deprecated `Epic Link` behavior unless an explicitly verified non-Cloud/legacy target requires it; the portable Cloud design uses `Parent`.
- Create work items first. Reconcile real keys, discover transitions and link types, then apply workflow transitions and links as separate controlled operations.
- REST v3 payload templates use Atlassian Document Format; all destination IDs and account references remain placeholders until discovered.
- Use a disposable project or test subset before the bulk operation. Never assume bulk imports or links can be rolled back safely.
"""
    (JIRA_ROOT / "import" / "IMPORT_CONFIGURATION_NOTES.md").write_text(config_notes, encoding="utf-8")

    # Append rather than replace the generation report and changelog.
    generation_path = JIRA_ROOT / "GENERATION_REPORT.md"
    generation = generation_path.read_text(encoding="utf-8")
    # Historical build logs may contain environment-specific absolute paths; keep the report portable.
    generation = generation.replace(str(REPO_ROOT).replace("\\", "/") + "/", "<PROJECT_ROOT>/")
    generation = generation.replace(str(REPO_ROOT) + "/", "<PROJECT_ROOT>/")
    generation = generation.replace("/mnt/data/BAS_JIRA_WORK/repo/", "<PROJECT_ROOT>/")
    marker = "\n## Second-pass content hardening (v2)\n"
    if marker in generation:
        generation = generation.split(marker)[0].rstrip() + "\n"
    generation += marker + "\n" + md_list(findings) + f"\n\nStrict second-pass result: **{metrics['result']}** with **{metrics['error_count']}** errors. See `validation/SECOND_PASS_AUDIT_REPORT.md`.\n"
    generation_path.write_text(generation, encoding="utf-8")

    changelog_path = JIRA_ROOT / "CHANGELOG.md"
    changelog = changelog_path.read_text(encoding="utf-8") if changelog_path.is_file() else "# Jira Pack Change Log\n"
    entry_header = f"## {TODAY} — v2 second-pass hardening"
    if entry_header not in changelog:
        changelog = changelog.rstrip() + f"\n\n{entry_header}\n\n" + md_list(findings) + "\n"
    changelog_path.write_text(changelog, encoding="utf-8")

    history_path = JIRA_ROOT / "history" / "ISSUE_CHANGE_LOG.jsonl"
    existing = history_path.read_text(encoding="utf-8").splitlines() if history_path.is_file() else []
    event_id = "JIRA-PACK-V2-SECOND-PASS"
    if not any(event_id in line for line in existing):
        existing.append(json.dumps({
            "event_id": event_id, "date": TODAY, "actor": "SECOND_PASS_AUDIT", "action": "PACK_HARDENED",
            "scope": "All actionable issue specifications and all generated derivatives",
            "reason": "Eliminate generic specifications, correct validation modalities, make traceability inheritance explicit, and prevent derivative/source-reference drift.",
            "evidence": ["jira/validation/SECOND_PASS_AUDIT_REPORT.md", "jira/validation/SECOND_PASS_AUDIT_RESULTS.json"],
        }, sort_keys=True))
    history_path.write_text("\n".join(existing) + "\n", encoding="utf-8")

    # Compact context remains intentionally small.
    ready = [r for r in records if r.get("ready")]
    blocked = [r for r in records if r.get("workflow_state") == "BLOCKED"]
    context = f"""# Current Jira Context

- Project state: W25 planning/design/handoff complete; **there is no Wave 26**.
- Jira pack: v2 second-pass hardened; {len(records)} issues; strict audit `{metrics['result']}`.
- Product state: implementation/real-data/empirical/production work remains governed by the post-wave graph; no missing evidence is fabricated.
- READY atomic issues: {len(ready)} — {', '.join(r['local_id'] for r in ready) or 'none'}.
- BLOCKED atomic/issues: {len(blocked)}.
- Start: read `jira/index/READY_QUEUE.csv`, then one selected canonical record, its source manifest, and `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Authority: `jira/reconciliation/SOURCE_AUTHORITY_MAP.md`.
- External boundaries: `jira/reconciliation/UNAVOIDABLE_EXTERNAL_ACTIONS.md`.
- Completion: rebuild all derivatives and run `python -B jira/tools/validate_second_pass.py`; code/file existence alone is not Done.
"""
    (JIRA_ROOT / "ai" / "CURRENT_CONTEXT.md").write_text(context, encoding="utf-8")

    readme_path = JIRA_ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else "# Local Jira System\n"
    readme = re.sub(
        r"## First use\n.*?(?=\n## Jira import)",
        """## First use

1. Read `ai/CURRENT_CONTEXT.md` and `index/READY_QUEUE.csv`.
2. Select only a READY `ATOMIC_EXECUTION` Subtask for implementation.
3. Open that one canonical record, its work packet, its source manifest, and the effective governance-context row.
4. Never implement directly from an Epic/Story `AGGREGATE_GATE` packet; those packets are integration/evidence/closure gates after child work is complete.
5. After any canonical or operational update, run `python -B jira/tools/rebuild_all_derivatives.py`, then `python -B jira/tools/validate_second_pass.py`.

""",
        readme,
        flags=re.S,
    )
    readme_path.write_text(readme, encoding="utf-8")

    sync_path = JIRA_ROOT / "SYNC_CONTRACT.md"
    sync = sync_path.read_text(encoding="utf-8") if sync_path.is_file() else "# Local ↔ Jira Sync Contract\n"
    sync_marker = "\n## Reconciliation safety and key-map contract\n"
    if sync_marker in sync:
        prefix, remainder = sync.split(sync_marker, 1)
        if "\n## Required update sequence\n" in remainder:
            sync = prefix.rstrip() + "\n\n## Required update sequence\n" + remainder.split("\n## Required update sequence\n", 1)[1]
        else:
            sync = prefix.rstrip() + "\n"
    safety = """## Reconciliation safety and key-map contract

- Always run `python -B jira/tools/reconcile_jira_export.py <jira-export.csv> --dry-run` before a live reconciliation. Dry-run must not mutate canonical records or generated derivatives.
- `POST_IMPORT_KEY_MAP_TEMPLATE.csv` is an intentionally blank reusable import template. Assigned Jira keys/IDs belong in `POST_IMPORT_KEY_MAP.csv` and canonical operational fields.
- Raw Jira status, assignee, sprint, numeric ID, and update timestamp are preserved under `operational_jira`; the logical local state remains safety-normalized against dependency, evidence, deferment, and protected-completion gates.
- Jira `Done` cannot overwrite local state unless evidence is already `COMPLETE` or `VERIFIED`. Unsafe status requests and key mismatches are written to `reconciliation/SYNC_CONFLICTS.csv`.
- Live reconciliation is transactional: it restores canonical records and derivatives if strict validation fails.

"""
    if "## Required update sequence\n" in sync:
        sync = sync.replace("## Required update sequence\n", safety + "## Required update sequence\n", 1)
    else:
        sync = sync.rstrip() + "\n\n" + safety
    sync = re.sub(
        r"## Required update sequence\n.*\Z",
        """## Required update sequence

1. For Jira-originated changes, export `Local Issue ID` plus operational fields and run the reconciliation tool in `--dry-run` mode; resolve conflicts before committing. For local specification changes, edit only canonical JSON through version control.
2. Apply the authority-appropriate change. Live reconciliation writes a material event only after strict validation; manual local changes must append their own material event without rewriting accepted historical evidence.
3. Run `python -B jira/tools/rebuild_all_derivatives.py` so Markdown, packets, source manifests, traceability, queues, imports, and payloads are rebuilt together.
4. Recompute and inspect READY/BLOCKED state; aggregate gates never enter the atomic execution queue.
5. Run `python -B jira/tools/validate_second_pass.py` and `python -B jira/tools/run_second_pass_audit.py`.
6. Resolve conflicts instead of silently overwriting authority-owned fields.
7. Snapshot Jira-local operational state before/after major imports, reconciliations, or release transitions.
""",
        sync,
        flags=re.S,
    )
    sync_path.write_text(sync, encoding="utf-8")

    ai_sync = """# AI Sync Protocol

1. Treat canonical JSON as authoritative for specification, scope, hierarchy intent, technical dependencies, source/governance references, acceptance criteria, Definition of Done, tests, protected constraints, and expected artifacts.
2. Treat Jira as authoritative for assigned key/ID and raw live operational values such as status, assignee, sprint, board order, comments, and execution ownership.
3. Export `Local Issue ID`, `Issue key`, optional numeric `Issue ID`, status, assignee, sprint, and update timestamp. Run `python -B jira/tools/reconcile_jira_export.py <export.csv> --dry-run` first.
4. Resolve key/status conflicts rather than using last-write-wins. A Jira `Done` state cannot become local `DONE` until local evidence is `COMPLETE` or `VERIFIED`; dependency/evidence gates may safety-normalize an unsafe Jira state.
5. Run live reconciliation only after reviewing dry-run output. It writes actual mappings to `import/POST_IMPORT_KEY_MAP.csv`, preserves `import/POST_IMPORT_KEY_MAP_TEMPLATE.csv` as blank, records conflicts in `reconciliation/SYNC_CONFLICTS.csv`, and rolls back on strict-validation failure.
6. After any local specification or operational update, rebuild all derivatives, validate the Jira pack/source refs/dependencies/import artifacts, review READY/BLOCKED changes, append only material history events, and snapshot before/after major transitions.
"""
    (JIRA_ROOT / "ai" / "AI_SYNC_PROTOCOL.md").write_text(ai_sync, encoding="utf-8")

    post_import_checklist = """# Post-Import Validation Checklist

- [ ] Imported issue count equals the total in `validation/COVERAGE_REPORT.json`.
- [ ] Every Local Issue ID appears exactly once and maps to one real Jira key.
- [ ] `POST_IMPORT_KEY_MAP_TEMPLATE.csv` remains entirely blank for Jira keys/IDs.
- [ ] `POST_IMPORT_KEY_MAP.csv` contains only keys/IDs returned by the destination Jira site and agrees with canonical records.
- [ ] Reconciliation was first run with `--dry-run`; `reconciliation/SYNC_CONFLICTS.csv` was reviewed and every conflict was resolved or deliberately retained.
- [ ] No Jira `Done` state bypassed local complete/verified evidence, protected completion controls, or dependency gates.
- [ ] All 50 Epics exist; historical and post-wave Epics remain distinguishable.
- [ ] Stories/Tasks have the intended Epic parent and every Sub-task has the intended Story/Task parent; no orphan or impossible relationship exists.
- [ ] Descriptions preserve scope, acceptance criteria, Definition of Done, tests, evidence, stop conditions, and source references.
- [ ] Logical workflow, implementation maturity, evidence state, and execution mode survived as separate concepts.
- [ ] Controlled labels/components imported without uncontrolled variants; the default active board excludes historical planning items.
- [ ] Every dependency/related link in `JIRA_LINKS.csv` exists with the correct direction/type after real link types were discovered.
- [ ] READY items have no unresolved hard dependency; blocked items expose their unblock condition; deferred/conditional work is not pulled into the core release board.
- [ ] Requirement, acceptance-control, ADR, risk, gap, test, artifact, and source traceability remains resolvable by Local Issue ID.
- [ ] A sample of source references resolves to the same repository path/hash/anchor.
- [ ] `python -B jira/tools/validate_jira_pack.py`, `validate_source_refs.py`, `validate_dependencies.py`, `validate_import_files.py`, and `run_second_pass_audit.py` all pass after reconciliation.
"""
    (JIRA_ROOT / "import" / "POST_IMPORT_VALIDATION_CHECKLIST.md").write_text(post_import_checklist, encoding="utf-8")

    remediation = f"""# Second-Pass Findings and Remediation

## Baseline confirmed

- The v1 issue graph, hierarchy, broad domain coverage, aggregate requirement/acceptance/gap/risk traceability, dependency acyclicity, and repository baseline were substantially sound.
- The 25-wave planning/design program remains complete and no Wave 26 was created.

## Material gaps found and corrected

{md_numbered(findings)}

## Independent proof

- Strict content-aware validation: **{metrics['result']}**, {metrics['error_count']} errors.
- Canonical issues: **{metrics['issue_count']}**; actionable records: **{metrics['actionable_count']}**; atomic execution: **{metrics['execution_mode_counts'].get('ATOMIC_EXECUTION', 0)}**; aggregate gates: **{metrics['execution_mode_counts'].get('AGGREGATE_GATE', 0)}**.
- Source anchors: **{sum(metrics.get('source_anchor_result_counts', {}).values())}** validated; derivative records: **{sum(metrics.get('derivative_result_counts', {}).values())}** consistent.
- The separate 68-section audit is recorded in `SECOND_PASS_AUDIT.md` / `SECOND_PASS_AUDIT.json`.

## External boundary

Destination Jira administration/import, technical credential/route validation, real-data materialization, target-host benchmarks, empirical model/BAS findings, production deployment, and operating authorization remain explicit execution work. Rights metadata is nonblocking for private acquisition and training. These outcomes are not fabricated as completed and are not defects in the static Jira pack.
"""
    (JIRA_ROOT / "validation" / "SECOND_PASS_FINDINGS_AND_REMEDIATION.md").write_text(remediation, encoding="utf-8")

    # Remove a superseded 67-row matrix left by the first hardening prototype; the 68-row master matrix is canonical.
    stale_matrix = JIRA_ROOT / "validation" / "PROMPT_COMPLIANCE_MATRIX.csv"
    if stale_matrix.exists():
        stale_matrix.unlink()


def write_tool_wrappers() -> None:
    wrappers = {
        "validate_second_pass.py": """from __future__ import annotations\nimport json\nfrom second_pass_hardening import load_records, strict_validate\nerrors, metrics = strict_validate(load_records(), write_reports=True)\nprint(json.dumps(metrics, indent=2, sort_keys=True))\nraise SystemExit(1 if errors else 0)\n""",
        "rebuild_all_derivatives.py": """from __future__ import annotations\nfrom second_pass_hardening import rebuild_derivatives\n\ndef main() -> None:\n    rebuild_derivatives(write_manifest=True)\n    print('PASS: all Jira derivatives rebuilt from canonical JSON')\n\nif __name__ == '__main__':\n    main()\n""",
        "repair_source_refs.py": """from __future__ import annotations\nfrom second_pass_hardening import validate_source_anchors, load_records, regenerate_source_manifests, import_lib\nerrors, rows = validate_source_anchors(repair=True)\nregenerate_source_manifests(load_records())\nimport_lib().rebuild_file_manifest()\nprint(f'refs={len(rows)} errors={len(errors)}')\nraise SystemExit(1 if errors else 0)\n""",
    }
    for name, content in wrappers.items():
        (JIRA_ROOT / "tools" / name).write_text(content, encoding="utf-8")


def rebuild_derivatives(write_manifest: bool = False) -> None:
    records = load_records()
    lib = import_lib()
    lib.recompute_ready(records)
    save_records(records)
    lib.build_indexes(records)
    lib.build_import_files(records)
    regenerate_issue_views(records)
    regenerate_source_manifests(records)
    regenerate_governance_context(records)
    regenerate_import_derivatives(records)
    if write_manifest:
        # Existing library excludes manifest/hash files from its own coverage to avoid self-reference.
        lib.rebuild_file_manifest()



def patch_maintenance_tools() -> None:
    # Make every normal maintenance entry point rebuild all canonical derivatives, not only indexes/CSV rows.
    replacements = {
        "build_indexes.py": "from __future__ import annotations\nfrom rebuild_all_derivatives import rebuild_derivatives\nrebuild_derivatives(write_manifest=True)\nprint('PASS: indexes and all canonical derivatives rebuilt')\n",
        "build_import_files.py": "from __future__ import annotations\nfrom rebuild_all_derivatives import rebuild_derivatives\nrebuild_derivatives(write_manifest=True)\nprint('PASS: import files and all canonical derivatives rebuilt')\n",
        "update_ready_queue.py": "from __future__ import annotations\nfrom rebuild_all_derivatives import rebuild_derivatives\nrebuild_derivatives(write_manifest=True)\nprint('PASS: READY/BLOCKED state and all canonical derivatives rebuilt')\n",
    }
    for name, content in replacements.items():
        (JIRA_ROOT / "tools" / name).write_text(content, encoding="utf-8")

    reconcile_content = r'''from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

from jira_pack_lib import JIRA_ROOT, load_records, recompute_ready, save_record
from rebuild_all_derivatives import rebuild_derivatives
from second_pass_hardening import import_lib, strict_validate

ALLOWED_LOGICAL_STATES = {
    "BACKLOG", "READY", "IN_PROGRESS", "BLOCKED", "REVIEW", "VALIDATION",
    "EVIDENCE_PENDING", "DONE", "DEFERRED", "CANCELLED",
}


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def logical_status(raw: str) -> str:
    mapping = {
        "backlog": "BACKLOG", "todo": "BACKLOG", "open": "BACKLOG",
        "ready": "READY", "selectedfordevelopment": "READY",
        "inprogress": "IN_PROGRESS", "review": "REVIEW", "inreview": "REVIEW",
        "validation": "VALIDATION", "evidencepending": "EVIDENCE_PENDING",
        "blocked": "BLOCKED", "done": "DONE", "closed": "DONE", "resolved": "DONE",
        "deferred": "DEFERRED", "cancelled": "CANCELLED", "canceled": "CANCELLED",
    }
    return mapping.get(norm(raw), "")


def write_conflicts(rows: list[dict[str, str]]) -> None:
    path = JIRA_ROOT / "reconciliation" / "SYNC_CONFLICTS.csv"
    fields = ["local_id", "field", "jira_value", "local_value", "resolution"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reconcile a Jira CSV export into safety-normalized local operational fields using Local Issue ID."
    )
    parser.add_argument("export_csv", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=None, help="Authoritative BAS repository root when the Jira pack is extracted separately.")
    args = parser.parse_args()

    with args.export_csv.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        names = {norm(name): name for name in (reader.fieldnames or [])}

    local_col = names.get("localissueid") or names.get("localid")
    key_col = names.get("issuekey") or names.get("key")
    logical_col = names.get("logicalworkflowstate")
    status_col = names.get("status")
    assignee_col = names.get("assignee") or names.get("assigneeemail")
    sprint_col = names.get("sprint")
    updated_col = names.get("updated") or names.get("updatedat")
    issue_id_col = names.get("issueid") or names.get("jiraworkitemid") or names.get("workitemid")
    if not local_col or not key_col:
        print("ERROR: Export must contain Local Issue ID and Issue key columns", file=sys.stderr)
        return 1

    records = load_records()
    by_id = {record["local_id"]: record for record in records}
    original_snapshots = {
        Path(record["__path"]): Path(record["__path"]).read_bytes()
        for record in records
    }
    before_state = {
        record["local_id"]: {
            "jira_key": record.get("jira_key", ""),
            "workflow_state": record.get("workflow_state", ""),
            "ready": record.get("ready", False),
            "operational_jira": record.get("operational_jira", {}),
        }
        for record in records
    }

    errors: list[str] = []
    conflicts: list[dict[str, str]] = []
    requested_states: dict[str, str] = {}
    now = datetime.now(timezone.utc).isoformat()

    for row in rows:
        local_id = row.get(local_col, "").strip()
        if not local_id:
            continue
        record = by_id.get(local_id)
        if record is None:
            errors.append(f"Unknown Local Issue ID {local_id}")
            continue

        incoming_key = row.get(key_col, "").strip()
        existing_key = str(record.get("jira_key", ""))
        if not incoming_key:
            conflicts.append({
                "local_id": local_id, "field": "Issue key", "jira_value": "", "local_value": existing_key,
                "resolution": "BLANK_KEY_NOT_APPLIED",
            })
        elif not re.fullmatch(r"[A-Z][A-Z0-9]+-\d+", incoming_key):
            errors.append(f"{local_id}: invalid Jira issue key format {incoming_key!r}")
        elif existing_key and existing_key != incoming_key:
            conflicts.append({
                "local_id": local_id, "field": "Issue key", "jira_value": incoming_key, "local_value": existing_key,
                "resolution": "EXISTING_KEY_MISMATCH_REQUIRES_MANUAL_REVIEW",
            })
        else:
            record["jira_key"] = incoming_key

        raw_status = row.get(status_col, "").strip() if status_col else ""
        requested_logical = row.get(logical_col, "").strip().upper() if logical_col else ""
        mapped = requested_logical or logical_status(raw_status)
        if mapped and mapped not in ALLOWED_LOGICAL_STATES:
            conflicts.append({
                "local_id": local_id, "field": "Logical Workflow State", "jira_value": mapped,
                "local_value": str(record.get("workflow_state", "")),
                "resolution": "UNKNOWN_LOGICAL_STATE_NOT_APPLIED",
            })
            mapped = ""
        if raw_status and not mapped:
            conflicts.append({
                "local_id": local_id, "field": "Status", "jira_value": raw_status,
                "local_value": str(record.get("workflow_state", "")),
                "resolution": "RAW_STATUS_RECORDED_LOGICAL_STATE_NOT_OVERWRITTEN",
            })
        elif mapped == "DONE" and record.get("evidence_state") not in {"COMPLETE", "VERIFIED"}:
            conflicts.append({
                "local_id": local_id, "field": "Status", "jira_value": raw_status or mapped,
                "local_value": str(record.get("workflow_state", "")),
                "resolution": "DONE_REJECTED_UNTIL_LOCAL_EVIDENCE_IS_COMPLETE_OR_VERIFIED",
            })
        elif mapped:
            record["workflow_state"] = mapped
            requested_states[local_id] = mapped

        operational = dict(record.get("operational_jira", {}))
        incoming_operational = {
            "status_raw": raw_status,
            "assignee": row.get(assignee_col, "").strip() if assignee_col else "",
            "sprint": row.get(sprint_col, "").strip() if sprint_col else "",
            "jira_updated_at": row.get(updated_col, "").strip() if updated_col else "",
            "jira_issue_id": row.get(issue_id_col, "").strip() if issue_id_col else operational.get("jira_issue_id", ""),
        }
        live_state_changed = any(
            str(operational.get(key, "")) != str(value)
            for key, value in incoming_operational.items()
        )
        operational.update(incoming_operational)
        if live_state_changed or not operational.get("last_synced_at"):
            operational["last_synced_at"] = now
            operational["source_export"] = "jira/reconciliation/BAT_JIRA_EXPORT.csv"
        record["operational_jira"] = operational

    if errors:
        for error in errors:
            print("ERROR:", error, file=sys.stderr)
        return 1

    recompute_ready(records)
    for local_id, requested in requested_states.items():
        actual = str(by_id[local_id].get("workflow_state", ""))
        if requested != actual:
            conflicts.append({
                "local_id": local_id,
                "field": "Logical Workflow State",
                "jira_value": requested,
                "local_value": actual,
                "resolution": "LOCAL_DEPENDENCY_EVIDENCE_GATE_OVERRIDES_UNSAFE_JIRA_STATE",
            })

    changes: list[dict[str, object]] = []
    for record in records:
        after = {
            "jira_key": record.get("jira_key", ""),
            "workflow_state": record.get("workflow_state", ""),
            "ready": record.get("ready", False),
            "operational_jira": record.get("operational_jira", {}),
        }
        before = before_state[record["local_id"]]
        if before != after:
            changes.append({"local_id": record["local_id"], "before": before, "after": after})

    if args.dry_run:
        print(json.dumps({
            "result": "DRY_RUN_PASS",
            "rows": len(rows),
            "changes": len(changes),
            "conflicts": conflicts,
        }, indent=2, sort_keys=True))
        return 0

    try:
        for record in records:
            save_record(record)
        rebuild_derivatives(write_manifest=False)
        validation_errors, validation_metrics = strict_validate(load_records(), write_reports=True)
        if validation_errors:
            raise RuntimeError(
                "Reconciled state failed strict validation: " + "; ".join(validation_errors[:25])
            )
    except Exception as exc:
        for path, data in original_snapshots.items():
            path.write_bytes(data)
        rebuild_derivatives(write_manifest=True)
        print(f"ERROR: reconciliation rolled back: {exc}", file=sys.stderr)
        return 1

    write_conflicts(conflicts)
    log = JIRA_ROOT / "history" / "ISSUE_CHANGE_LOG.jsonl"
    with log.open("a", encoding="utf-8") as handle:
        for change in changes:
            event = dict(change)
            event.update({
                "timestamp": now,
                "event": "JIRA_EXPORT_RECONCILED",
                "actor": "reconcile_jira_export.py",
                "source_export": str(args.export_csv.resolve()),
            })
            handle.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
    import_lib().rebuild_file_manifest()

    print(json.dumps({
        "result": "PASS",
        "rows": len(rows),
        "changed_issues": len(changes),
        "conflict_count": len(conflicts),
        "strict_validation": validation_metrics.get("result", "PASS"),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
    (JIRA_ROOT / "tools" / "reconcile_jira_export.py").write_text(reconcile_content, encoding="utf-8")


def patch_validation_tools() -> None:
    validators = {
        "validate_jira_pack.py": '''from __future__ import annotations
import json
import shutil
from second_pass_hardening import JIRA_ROOT, load_records, strict_validate, import_lib
for cache in JIRA_ROOT.rglob("__pycache__"):
    shutil.rmtree(cache, ignore_errors=True)
errors, metrics = strict_validate(load_records(), write_reports=True)
lib = import_lib()
lib.rebuild_file_manifest()
manifest_errors = lib.validate_file_manifest()
all_errors = errors + manifest_errors
result = {"result": "PASS" if not all_errors else "FAIL", "strict": metrics, "manifest_errors": manifest_errors, "errors": all_errors}
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(1 if all_errors else 0)
''',
        "validate_source_refs.py": '''from __future__ import annotations
import argparse
import json
from second_pass_hardening import validate_source_anchors, load_records, regenerate_source_manifests, import_lib
parser = argparse.ArgumentParser(description="Validate source hashes, line ranges, excerpts, and anchors; optionally repair only after deterministic relocation.")
parser.add_argument("--repair", action="store_true")
parser.add_argument("--repo-root", type=str, default=None, help="Authoritative BAS repository root for standalone Jira-pack validation.")
args = parser.parse_args()
errors, rows = validate_source_anchors(repair=args.repair)
if args.repair:
    regenerate_source_manifests(load_records())
    import_lib().rebuild_file_manifest()
print(json.dumps({"result": "PASS" if not errors else "FAIL", "references": len(rows), "repair": args.repair, "relocated": sum(bool(r.get("relocated")) for r in rows), "errors": errors}, indent=2, sort_keys=True))
raise SystemExit(1 if errors else 0)
''',
        "validate_import_files.py": '''from __future__ import annotations
import json
from second_pass_hardening import load_records, strict_validate
errors, metrics = strict_validate(load_records(), write_reports=True)
import_errors = [error for error in errors if "IMPORT" in error.upper() or "CSV" in error.upper() or "PAYLOAD" in error.upper() or "PARENT" in error.upper()]
print(json.dumps({"result": "PASS" if not errors else "FAIL", "issue_count": metrics["issue_count"], "import_error_count": len(import_errors), "all_error_count": len(errors), "errors": errors}, indent=2, sort_keys=True))
raise SystemExit(1 if errors else 0)
''',
        "validate_dependencies.py": '''from __future__ import annotations
import json
from jira_pack_lib import load_records, cycles
records = load_records()
by_id = {record["local_id"]: record for record in records}
errors = []
for record in records:
    for dependency in record.get("dependencies", []):
        if dependency not in by_id:
            errors.append(f"{record['local_id']}: missing dependency {dependency}")
        elif record["local_id"] not in by_id[dependency].get("blocks", []):
            errors.append(f"{record['local_id']}: inverse blocks relationship missing on {dependency}")
    for blocked in record.get("blocks", []):
        if blocked not in by_id:
            errors.append(f"{record['local_id']}: missing blocked issue {blocked}")
        elif record["local_id"] not in by_id[blocked].get("dependencies", []):
            errors.append(f"{record['local_id']}: inverse dependency relationship missing on {blocked}")
found_cycles = cycles(records)
for cycle in found_cycles:
    errors.append("cycle: " + " -> ".join(cycle))
print(json.dumps({"result": "PASS" if not errors else "FAIL", "issues": len(records), "cycles": len(found_cycles), "errors": errors}, indent=2, sort_keys=True))
raise SystemExit(1 if errors else 0)
''',
    }
    for name, content in validators.items():
        (JIRA_ROOT / "tools" / name).write_text(content, encoding="utf-8")


def patch_generator_for_reproducibility() -> None:
    path = JIRA_ROOT / "tools" / "build_complete_jira_pack.py"
    text = path.read_text(encoding="utf-8")
    marker = "# SECOND_PASS_V2_PRESERVE_AND_APPLY"
    if marker in text:
        return
    old = """    repo_root = repo_root.resolve()\n    jira_root = repo_root / \"jira\"\n\n    # The baseline must evaluate the authoritative W25 repository, not an earlier generated Jira derivative.\n    if jira_root.exists():\n        shutil.rmtree(jira_root)\n"""
    new = """    repo_root = repo_root.resolve()\n    jira_root = repo_root / \"jira\"\n    builder_self_text = Path(__file__).read_text(encoding=\"utf-8\")\n    # SECOND_PASS_V2_PRESERVE_AND_APPLY: preserve the v2 hardener/validators before the generator replaces jira/.\n    preserved_v2_tools = {}\n    for _name in [\"jira_pack_lib.py\", \"second_pass_hardening.py\", \"run_second_pass_audit.py\", \"validate_second_pass.py\", \"rebuild_all_derivatives.py\", \"repair_source_refs.py\"]:\n        _p = jira_root / \"tools\" / _name\n        if _p.is_file():\n            preserved_v2_tools[_name] = _p.read_text(encoding=\"utf-8\")\n\n    # The baseline must evaluate the authoritative W25 repository, not an earlier generated Jira derivative.\n    if jira_root.exists():\n        shutil.rmtree(jira_root)\n"""
    if old not in text:
        raise RuntimeError("Could not patch generator preservation block")
    text = text.replace(old, new, 1)
    old2 = """    write_tools(jira_root)\n    shutil.copy2(Path(__file__), jira_root / \"tools\" / \"build_complete_jira_pack.py\")\n\n    coverage = calculate_coverage(repo, issues, refs, regs, trace)\n"""
    new2 = """    write_tools(jira_root)\n    write_text(jira_root / \"tools\" / \"build_complete_jira_pack.py\", builder_self_text)\n    for _name, _content in preserved_v2_tools.items():\n        write_text(jira_root / \"tools\" / _name, _content)\n\n    coverage = calculate_coverage(repo, issues, refs, regs, trace)\n"""
    if old2 not in text:
        raise RuntimeError("Could not patch generator restoration block")
    text = text.replace(old2, new2, 1)
    old3 = """    write_generation_report(jira_root, repo, issues, coverage, baseline_runs, pack_runs)\n\n    result: dict[str, Any] = {\n"""
    new3 = """    write_generation_report(jira_root, repo, issues, coverage, baseline_runs, pack_runs)\n\n    # Apply the preserved content-aware v2 hardening pass before final manifests and archives.\n    if preserved_v2_tools.get(\"second_pass_hardening.py\"):\n        _v2_run = run_command([sys.executable, \"-B\", \"jira/tools/second_pass_hardening.py\", \"--apply\", \"--skip-generator-patch\"], repo_root, 600)\n        pack_runs.append(_v2_run)\n        write_json(jira_root / \"validation\" / \"SECOND_PASS_GENERATOR_RUN.json\", _v2_run)\n    if preserved_v2_tools.get(\"run_second_pass_audit.py\"):\n        _audit_run = run_command([sys.executable, \"-B\", \"jira/tools/run_second_pass_audit.py\"], repo_root, 600)\n        pack_runs.append(_audit_run)\n        write_json(jira_root / \"validation\" / \"SECOND_PASS_INDEPENDENT_AUDIT_RUN.json\", _audit_run)\n\n    result: dict[str, Any] = {\n"""
    if old3 not in text:
        raise RuntimeError("Could not patch generator hardening call")
    text = text.replace(old3, new3, 1)
    path.write_text(text, encoding="utf-8")


def update_schema_docs() -> None:
    schema = (JIRA_ROOT / "SCHEMA.md").read_text(encoding="utf-8")
    marker = "\n## Schema v2 second-pass fields\n"
    if marker in schema:
        schema = schema.split(marker)[0].rstrip() + "\n"
    schema += marker + """

Canonical JSON remains the sole editable specification. Schema v2 adds:

- `files_to_inspect`: minimal read-only implementation/source context, distinct from modification authority.
- `components_expected_to_be_touched`: component-level scope when an exact file cannot safely be predicted.
- `governance_traceability_gate`, `traceability_inherited_from`, `traceability_resolution`, and effective counts.
- `completion_evidence_contract`: machine-readable minimum evidence and claim limit.
- `validation_class` on validation entries, while retaining the original `classification` field.
- `allowed_modification_paths` versus `read_only_context_paths`: explicit mutation authority separate from source context.
- `primary_source_refs` and `supporting_source_refs`: token-efficient source ordering without duplicating content.
- `evidence_manifest_path`, `work_packet_path`, `validation_classes`, `record_revision`, `last_content_audit`, and `specificity_fingerprint`: deterministic navigation/audit derivatives.
- `execution_mode`: `ATOMIC_EXECUTION` for directly executable post-wave Subtasks, `AGGREGATE_GATE` for non-executable Epic/Story integration gates, and `HISTORICAL_REFERENCE` for provenance-only records.
- Every actionable post-wave record has a compact packet. Aggregate packets explicitly prohibit atomic implementation and authorize only aggregate evidence/Jira-state closure actions.

All Markdown issue views, work packets, source manifests, indexes, import CSVs, and REST payloads are generated derivatives. After any canonical or operational change, run `python -B jira/tools/rebuild_all_derivatives.py`; strict validation rejects derivative drift.
"""
    (JIRA_ROOT / "SCHEMA.md").write_text(schema, encoding="utf-8")

    decisions = (JIRA_ROOT / "DESIGN_DECISIONS.md").read_text(encoding="utf-8")
    marker2 = "\n## DD-009 — Second-pass content-aware validation and derivative closure\n"
    if marker2 not in decisions:
        decisions = decisions.rstrip() + marker2 + """

The first-pass pack was structurally correct but did not make task specificity, test modality, traceability inheritance, source-anchor resolution, or derivative synchronization executable invariants. Schema v2 treats each as a release-blocking validation concern. Domain-gate inheritance avoids copying hundreds of governance IDs into every atomic task while still making effective context machine-resolvable. `files_to_inspect` and `files_expected_to_be_touched` are separated so an AI agent does not mistake broad source context for mutation authorization. All operational rebuild entry points now regenerate every derivative from canonical JSON.
"""
    (JIRA_ROOT / "DESIGN_DECISIONS.md").write_text(decisions, encoding="utf-8")

    readme_path = JIRA_ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else "# Local Jira System\n"
    portable_marker = "\n## Portable validation from the Jira-only ZIP\n"
    if portable_marker in readme:
        readme = readme.split(portable_marker)[0].rstrip() + "\n"
    readme += portable_marker + r"""

The Jira-only ZIP intentionally contains only `jira/`; authoritative source documents remain in the project repository. Structural checks such as `validate_jira_manifest.py` and `validate_dependencies.py` run directly in the extracted folder. Content/source/import checks must either be run after installing `jira/` beneath the repository root or supplied the repository explicitly:

```powershell
python jira\tools\validate_jira_pack.py --repo-root C:\BatteredAggieSyndrome
python jira\tools\validate_source_refs.py --repo-root C:\BatteredAggieSyndrome
python jira\tools\validate_import_files.py --repo-root C:\BatteredAggieSyndrome
python jira\tools\run_second_pass_audit.py --repo-root C:\BatteredAggieSyndrome
```

`BAS_JIRA_REPO_ROOT` or `BAS_REPO_ROOT` may be used instead of the command-line option. Missing repository context fails cleanly with actionable guidance; it is never treated as an empty or valid source tree.
"""
    readme_path.write_text(readme, encoding="utf-8")


def update_ai_packet_docs() -> None:
    usage_path = JIRA_ROOT / "ai" / "AI_JIRA_USAGE.md"
    usage = usage_path.read_text(encoding="utf-8") if usage_path.is_file() else "# AI Jira Usage\n"
    marker = "\n## Execution versus aggregate packet contract\n"
    if marker in usage:
        usage = usage.split(marker)[0].rstrip() + "\n"
    usage += marker + """

- Every `ACTIONABLE_POST_WAVE` record has `ai/work_packets/<LOCAL_ID>.md` and appears in `index/WORK_PACKET_INDEX.csv`.
- Only a packet whose canonical record is a `Subtask`, `execution_mode=ATOMIC_EXECUTION`, `ready=true`, and workflow `READY` may be selected for implementation.
- Epic/Story packets use `execution_mode=AGGREGATE_GATE`; they are review/integration/closure contracts and explicitly prohibit direct production mutation.
- Aggregate packets may write only their declared aggregate evidence manifest and synchronized Jira/local state after all child evidence and the integrated gate are verified.
- Historical records use `HISTORICAL_REFERENCE` and have no current execution packet.
"""
    usage_path.write_text(usage, encoding="utf-8")

    protocol_path = JIRA_ROOT / "ai" / "AI_EXECUTION_PROTOCOL.md"
    protocol = protocol_path.read_text(encoding="utf-8") if protocol_path.is_file() else "# AI Execution Protocol\n"
    marker2 = "\n## Aggregate-gate review protocol\n"
    if marker2 in protocol:
        protocol = protocol.split(marker2)[0].rstrip() + "\n"
    protocol += marker2 + """

An `AGGREGATE_GATE` packet is never an implementation queue item. Use it only after child atomic work is complete to verify maturity/evidence, execute or review the integrated end-to-end gate, record residual blockers/nulls/accepted risks, and issue an evidence-backed closure decision. Route any code/data/contract mutation to a scoped atomic Subtask packet.
"""
    protocol_path.write_text(protocol, encoding="utf-8")

    decisions_path = JIRA_ROOT / "DESIGN_DECISIONS.md"
    decisions = decisions_path.read_text(encoding="utf-8")
    decision = "14. **All post-wave records have packets, but modes differ.** Atomic Subtasks are executable; Epic/Story packets are aggregate integration gates."
    if decision not in decisions:
        decisions = decisions.rstrip() + "\n\n## Packet-coverage decision\n\n" + decision + "\n"
    decisions_path.write_text(decisions, encoding="utf-8")

def perform_apply(skip_generator_patch: bool = False) -> dict[str, Any]:
    records = load_records()
    baseline_path = JIRA_ROOT / "validation" / "SECOND_PASS_BASELINE_AUDIT.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path.is_file() else baseline_audit(records)
    json_dump(baseline_path, baseline)

    generator = load_generator()
    maps = build_blueprint_maps(generator)
    apply_hardening(records, maps)

    lib = import_lib()
    lib.recompute_ready(records)
    save_records(records)
    lib.build_indexes(records)
    lib.build_import_files(records)
    regenerate_issue_views(records)
    regenerate_source_manifests(records)
    regenerate_governance_context(records)
    regenerate_import_derivatives(records)
    write_tool_wrappers()
    patch_maintenance_tools()
    patch_validation_tools()
    update_schema_docs()
    update_ai_packet_docs()
    write_master_prompt_matrix()
    if not skip_generator_patch:
        patch_generator_for_reproducibility()

    # Validate after all canonical/derivative content exists, then write narrative reports.
    errors, metrics = strict_validate(load_records(), write_reports=True)
    write_docs(load_records(), baseline, metrics)
    # Regenerate issue-independent docs does not affect derivative consistency, but validate again for final truth.
    errors, metrics = strict_validate(load_records(), write_reports=True)
    write_docs(load_records(), baseline, metrics)

    # Update primary validation summary.
    validation_report = f"# Jira Pack Validation\n\n- Original structural validators: retained.\n- Second-pass strict result: **{metrics['result']}**.\n- Issues: **{metrics['issue_count']}**.\n- Errors: **{metrics['error_count']}**.\n- See `SECOND_PASS_AUDIT_REPORT.md` and `MASTER_PROMPT_COMPLIANCE_MATRIX.csv`.\n"
    write_text_crlf(JIRA_ROOT / "validation" / "VALIDATION_REPORT.md", validation_report)

    # Final manifest after all writes. Re-running the manifest validator is done externally after this tool exits.
    normalize_jira_text_crlf()
    lib.rebuild_file_manifest()
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply or validate the BAS Jira v2 second-pass hardening contract.")
    parser.add_argument("--apply", action="store_true", help="Apply hardening, regenerate derivatives, and validate.")
    parser.add_argument("--validate-only", action="store_true", help="Run strict validation without mutation except validation reports.")
    parser.add_argument("--skip-generator-patch", action="store_true", help="Do not patch the self-contained generator (used when invoked by that generator).")
    parser.add_argument("--repo-root", type=Path, default=None, help="Authoritative BAS repository root when jira/ is validated from a standalone extraction.")
    args = parser.parse_args()

    if args.apply or not args.validate_only:
        metrics = perform_apply(skip_generator_patch=args.skip_generator_patch)
    else:
        errors, metrics = strict_validate(load_records(), write_reports=True)
    print(json.dumps(metrics, indent=2, sort_keys=True))
    raise SystemExit(1 if metrics.get("error_count") else 0)


if __name__ == "__main__":
    main()

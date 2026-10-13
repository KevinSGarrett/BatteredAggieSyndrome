"""Explicit planning decisions, separate from historical keyword/gate routing.

This validates preservation and source-to-owner decisions, never implementation
or scientific completion. It has no network or runtime side effects.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

DISPOSITIONS = {
    "IMPLEMENTATION_OBLIGATION", "CANDIDATE_TO_EVALUATE",
    "CONDITIONAL_INVESTIGATION", "DEFERRED", "WITHDRAWN",
}
GOVERNANCE_ROLE = "GOVERNANCE_ROUTING_ONLY"
UNREVIEWED = "NOT_REVIEWED_AT_CHILD_GRAIN"
SOURCE_INVENTORY_SHA256 = "b8b452defdb3c4dda847164460c8fc62a96202394b091e4af83d44d0488886ae"


def load_catalog(repo: Path) -> dict:
    return json.loads((repo / "governance/ORIGINAL_IDEA_DECISIONS.json").read_text(encoding="utf-8-sig"))


def load_source_inventory(repo: Path) -> dict:
    raw = (repo / "governance/ORIGINAL_IDEA_SOURCE_INVENTORY.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_INVENTORY_SHA256:
        raise ValueError("Reviewed original source inventory changed")
    return json.loads(raw)


def dependency_source_binding(source: dict) -> str:
    return hashlib.sha256(json.dumps(source, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def validate_dependency_routes(dependency: dict, label: str) -> list[str]:
    """External coordination references are not BAS owning decision units."""
    errors = []
    if not isinstance(dependency, dict):
        return [f"{label}: dependency block invalid"]
    def valid_source(r):
        if not isinstance(r, dict):
            return False
        repository, path = r.get("repository"), r.get("relative_path")
        if not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or any(p in {".", ".."} for p in repository.split("/")):
            return False
        if not isinstance(path, str) or "\\" in path or ":" in path or any(p in {"", ".", ".."} for p in path.split("/")):
            return False
        return all(isinstance(r.get(k), str) and re.fullmatch(r"[0-9a-f]{" + str(n) + r"}", r[k]) for k, n in (("head", 40), ("sha256", 64)))
    refs = dependency.get("source_refs", [])
    if not isinstance(refs, list) or not refs or not all(valid_source(r) for r in refs):
        return [f"{label}: dependency source identities missing/invalid"]
    bindings = {dependency_source_binding(r) for r in refs}
    routes = dependency.get("owner_route", [])
    seen = set()
    if not isinstance(routes, list):
        return [f"{label}: dependency route collection invalid"]
    if not routes or len(bindings) != len(refs):
        errors.append(f"{label}: dependency routes/sources missing or duplicated")
    for route in routes:
        if not isinstance(route, dict):
            errors.append(f"{label}: dependency route invalid")
            continue
        if not isinstance(route.get("role"), str) or not route["role"].strip():
            errors.append(f"{label}: dependency role missing/invalid")
        references = route.get("source_bindings", [])
        if not isinstance(references, list) or not references or any(not isinstance(v, str) or v not in bindings for v in references) or len(set(references)) != len(references):
            errors.append(f"{label}: dependency route has missing/unbound/duplicate source references")
        if "jira_key" in route:
            key = route["jira_key"]
            if "project_key" in route or "dependency_issue_key" in route or not isinstance(key, str) or not re.fullmatch(r"BAT-[1-9][0-9]*", key):
                errors.append(f"{label}: BAS route cannot supply external dependency authority")
        else:
            project, key = route.get("project_key"), route.get("dependency_issue_key")
            if not isinstance(project, str) or project not in {"CFIP", "CFI", "CFA"} or not isinstance(key, str) or not re.fullmatch(re.escape(project) + r"-[1-9][0-9]*", key):
                errors.append(f"{label}: external dependency namespace/key invalid")
        if isinstance(key, str):
            if key in seen:
                errors.append(f"{label}: dependency route duplicated")
            seen.add(key)
    return errors


def validate_catalog(catalog: dict, records: list[dict], requirement_ids: set[str], source_inventory: dict) -> list[str]:
    errors: list[str] = []
    by_id = {r["local_id"]: r for r in records}
    def check_owner(owner, label):
        record = by_id.get(owner.get("local_id"), {})
        if not record or record.get("jira_key") != owner.get("jira_key"):
            errors.append(f"{label}: not an exact canonical issue")
        if any(not owner.get(k) for k in ("role", "scope_basis", "decision_output")):
            errors.append(f"{label}: semantic scope/output missing")
        if record and owner.get("decision_output") not in record.get("expected_outputs", []):
            errors.append(f"{label}: output is not owned by the canonical issue")
    if catalog.get("schema_version") != "bas.original-idea-decisions.v1":
        errors.append("Original ideas: unsupported catalog schema")
    groups = catalog.get("groups", [])
    by_group = {g.get("idea_id"): g for g in groups}
    for original in source_inventory["groups"]:
        gid = original["idea_id"]
        current = by_group.get(gid, {})
        current_children = {c.get("child_id"): c for c in current.get("children", [])}
        if not current:
            errors.append(f"{gid}: original source group omitted")
        refs = {(r.get("source_id"), r.get("sha256"), r.get("line")) for r in current.get("source_refs", [])}
        expected_refs = {(r["source_id"], r["sha256"], r["line"]) for r in original["source_refs"]}
        if not expected_refs <= refs:
            errors.append(f"{gid}: original source provenance omitted/changed")
        for old in original["children"]:
            child = current_children.get(old["child_id"], {})
            if hashlib.sha256(child.get("concept", "").encode("utf-8")).hexdigest() != old["concept_sha256"]:
                errors.append(f"{old['child_id']}: original source concept omitted/changed")
            if not set(original["requirement_ids"]) <= set(child.get("requirement_ids", [])):
                errors.append(f"{old['child_id']}: original requirement edges omitted")
    group_ids = [g.get("idea_id") for g in groups]
    if len(group_ids) != len(set(group_ids)) or not groups:
        errors.append("Original ideas: duplicate or absent groups")
    children = []
    for group in groups:
        gid = group.get("idea_id", "?")
        actual = [c.get("child_id") for c in group.get("children", [])]
        expected = group.get("expected_child_ids", [])
        if not expected or actual != expected or len(actual) != len(set(actual)):
            errors.append(f"{gid}: exact expected child membership/order not preserved")
        concept_hashes = group.get("expected_child_concept_sha256", {})
        if set(concept_hashes) != set(expected):
            errors.append(f"{gid}: source concept hash population differs")
        if not group.get("decision_checkpoint") or not group.get("prerequisites"):
            errors.append(f"{gid}: decision checkpoint/prerequisites missing")
        refs = group.get("source_refs", [])
        if not refs or any(not r.get("source_id") or not re.fullmatch(r"[0-9a-f]{64}", r.get("sha256", "")) or type(r.get("line")) is not int or r["line"] < 1 for r in refs):
            errors.append(f"{gid}: source identity/line missing")
        for field in ("primary_owner", "evaluation_owner"):
            owner = group.get(field, {})
            check_owner(owner, f"{gid}: {field}")
        if "cross_project_dependencies" in group:
            errors.extend(validate_dependency_routes(group["cross_project_dependencies"], gid))
        for child in group.get("children", []):
            cid = child.get("child_id", "?")
            children.append(child)
            if not re.fullmatch(re.escape(gid) + r"-C\d{2,}", cid):
                errors.append(f"{gid}: child identity invalid")
            if child.get("disposition") not in DISPOSITIONS:
                errors.append(f"{cid}: disposition missing/invalid")
            if any(not child.get(k) for k in ("concept", "rationale", "planned_decision", "checkpoint", "owner")):
                errors.append(f"{cid}: concrete decision or rationale missing")
            if concept_hashes.get(cid) != hashlib.sha256(child.get("concept", "").encode("utf-8")).hexdigest():
                errors.append(f"{cid}: concept differs from retained source inventory")
            location = child.get("decision_location", {})
            if location.get("entry_id") != cid or not location.get("output"):
                errors.append(f"{cid}: exact decision output entry missing")
            for field in ("primary_owner", "evaluation_owner"):
                if field + "_override" in child:
                    check_owner(child[field + "_override"], f"{cid}: {field}")
            primary = child.get("primary_owner_override", group["primary_owner"])
            if location.get("output") != primary.get("decision_output"):
                errors.append(f"{cid}: decision location does not match its owner")
            if child.get("implementation_or_scientific_acceptance") != "NOT_ASSERTED_BY_THIS_PLAN":
                errors.append(f"{cid}: planning entry cannot claim delivered acceptance")
            if not set(child.get("requirement_ids", [])) <= requirement_ids:
                errors.append(f"{cid}: unknown requirement")
        if not set(group.get("requirement_ids", [])) <= requirement_ids:
            errors.append(f"{gid}: unknown group requirement")
    counts = catalog.get("counts", {})
    if type(counts.get("groups")) is not int or counts.get("groups") != len(groups) or type(counts.get("children")) is not int or counts.get("children") != len(children):
        errors.append("Original ideas: source population counts not conserved")
    ids = [c.get("child_id") for c in children]
    if len(ids) != len(set(ids)):
        errors.append("Original ideas: duplicate child identities")
    return errors


def decision_rows(catalog: dict) -> list[dict]:
    rows = []
    for group in catalog["groups"]:
        for child in group["children"]:
            primary = child.get("primary_owner_override", group["primary_owner"])
            evaluator = child.get("evaluation_owner_override", group["evaluation_owner"])
            rows.append({
                "idea_id": group["idea_id"], "child_id": child["child_id"],
                "concept": child["concept"], "disposition": child["disposition"],
                "requirement_ids": ";".join(child["requirement_ids"]),
                "primary_issue_id": primary["local_id"],
                "primary_jira_key": primary["jira_key"],
                "evaluation_issue_id": evaluator["local_id"],
                "decision_output": child["decision_location"]["output"],
                "decision_entry_id": child["decision_location"]["entry_id"],
                "checkpoint": group["decision_checkpoint"] if child["checkpoint"] == "INHERIT_GROUP_DECISION_CHECKPOINT" else child["checkpoint"],
                "completion_claim": "PLANNED_DECISION_ONLY",
            })
    return rows


def annotate_requirements(rows: list[dict], catalog: dict) -> list[dict]:
    decisions: dict[str, set[str]] = {}
    owners: dict[str, set[str]] = {}
    for row in decision_rows(catalog):
        for rid in row["requirement_ids"].split(";"):
            if rid:
                decisions.setdefault(rid, set()).add(row["child_id"])
                owners.setdefault(rid, set()).update((row["primary_issue_id"], row["evaluation_issue_id"]))
    return [dict(row,
        mapping_disposition="PRESERVED_GOVERNANCE_ROUTE_NOT_IMPLEMENTATION_PROOF",
        mapping_role=GOVERNANCE_ROLE,
        original_idea_decision_ids=";".join(sorted(decisions.get(row["requirement_id"], set()))),
        decision_owner_ids=";".join(sorted(owners.get(row["requirement_id"], set()))),
        semantic_planning_coverage="PLANNED_DECISIONS_REGISTERED" if row["requirement_id"] in decisions else UNREVIEWED,
    ) for row in rows]


def validate_mapping(rows: list[dict], catalog: dict, records: list[dict], expected_ids: set[str]) -> list[str]:
    errors = []
    ids = [r.get("requirement_id") for r in rows]
    if len(ids) != len(set(ids)) or set(ids) != expected_ids:
        errors.append("Requirement mapping: exact source membership/uniqueness mismatch")
    known = {r["local_id"] for r in records}
    for row, expected in zip(rows, annotate_requirements(rows, catalog)):
        rid = row["requirement_id"]
        links = set(filter(None, (row.get("post_wave_issue_ids") or row.get("jira_issue_ids") or "").split(";")))
        if not links or not links <= known:
            errors.append(f"{rid}: absent/unknown governance route")
        for key in ("mapping_disposition", "mapping_role", "original_idea_decision_ids", "decision_owner_ids", "semantic_planning_coverage"):
            if row.get(key) != expected[key]:
                errors.append(f"{rid}: {key} does not match explicit decision authority")
    return errors


def validate_all(repo: Path, jira: Path, records: list[dict]) -> tuple[list[str], dict]:
    def csv_rows(path):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    try:
        catalog = load_catalog(repo)
        requirements = csv_rows(repo / "governance/REQUIREMENTS_INDEX.csv")
        ids = {r["requirement_id"] for r in requirements}
        errors = validate_catalog(catalog, records, ids, load_source_inventory(repo))
        actual = csv_rows(jira / "index/ORIGINAL_IDEA_TRACEABILITY.csv")
        if actual != decision_rows(catalog):
            errors.append("Original idea index differs from explicit canonical decisions")
        mapping = csv_rows(jira / "index/REQUIREMENT_TRACEABILITY.csv")
        errors.extend(validate_mapping(mapping, catalog, records, ids))
        metrics = {
            "groups": len(catalog["groups"]), "children": len(actual),
            "dispositions": dict(Counter(r["disposition"] for r in actual)),
            "requirements_with_original_idea_decisions": sum(bool(r.get("original_idea_decision_ids")) for r in mapping),
            "requirements_not_reviewed_at_child_grain": sum(r.get("semantic_planning_coverage") == UNREVIEWED for r in mapping),
            "scope": "Planning preservation/ownership only; not implementation or scientific acceptance",
        }
        return errors, metrics
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return [f"Original idea traceability cannot be validated: {type(exc).__name__}: {exc}"], {}

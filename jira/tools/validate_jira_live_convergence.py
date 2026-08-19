from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Mapping

RETIRED_REGISTRY_REL = "jira/reconciliation/BAT_RETIRED_CANONICAL_ISSUE_REGISTRY.json"
AUXILIARY_REGISTRY_REL = "jira/reconciliation/BAT_AUXILIARY_ISSUE_REGISTRY.json"
VERIFICATION_REL = "jira/validation/BAT_LIVE_IMPORT_VERIFICATION.json"
PROFILE_REL = "jira/project/JIRA_TARGET_PROFILE.yaml"
LEDGER_REL = "jira/reconciliation/BAT_LIVE_IMPORT_LEDGER.json"
LINKS_REL = "jira/import/JIRA_LINKS.csv"
RECORDS_REL = "jira/records/issues"
LIVE_VERIFICATION_SCHEMA_VERSION = 2
STALE_AUXILIARY_SEMANTICS_COUNT = 31
GRAPH_FIELDS = ("dependencies", "blocks", "related_to", "duplicate_of")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_canonical_records(repo_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    root = repo_root / RECORDS_REL
    if not root.is_dir():
        return records
    for path in sorted(root.rglob("*.json")):
        records.append(_load_json(path))
    return records


def load_retired_local_ids(registry: Mapping[str, Any]) -> set[str]:
    return {str(item["local_id"]) for item in registry.get("issues") or [] if item.get("local_id")}


def expected_link_count_from_records(records: list[Mapping[str, Any]]) -> int:
    signatures: set[tuple[str, str, str]] = set()
    for record in records:
        local_id = str(record["local_id"])
        for dependency in record.get("dependencies") or []:
            signatures.add((str(dependency), "BLOCKS", local_id))
        for related in record.get("related_to") or []:
            signatures.add((local_id, "RELATES_TO", str(related)))
        for original in record.get("duplicate_of") or []:
            signatures.add((str(original), "DUPLICATE", local_id))
    return len(signatures)


def validate_count_contracts(
    *,
    auxiliary_registry_count: int,
    canonical_record_count: int,
    current_link_count: int,
    verification: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> list[str]:
    findings: list[str] = []
    schema_version = int(verification.get("schema_version") or 0)
    if schema_version < LIVE_VERIFICATION_SCHEMA_VERSION:
        findings.append(
            f"schema-v1 verification artifact after schema v2 adoption: schema_version={schema_version}"
        )
    auxiliary_expected = int(verification.get("auxiliary_expected_count") or 0)
    canonical_expected = int(verification.get("canonical_expected_count") or 0)
    total_expected = int(verification.get("total_expected_issue_count") or 0)
    total_actual = int(verification.get("total_actual_issue_count") or 0)
    issue_count = int(verification.get("issue_count") or 0)
    if auxiliary_registry_count != auxiliary_expected:
        findings.append(
            f"auxiliary registry count {auxiliary_registry_count} != verification auxiliary_expected_count {auxiliary_expected}"
        )
    if canonical_record_count != canonical_expected:
        findings.append(
            f"canonical record count {canonical_record_count} != verification canonical_expected_count {canonical_expected}"
        )
    if canonical_expected + auxiliary_expected != total_expected:
        findings.append(
            f"total count arithmetic drift: {canonical_expected}+{auxiliary_expected} != {total_expected}"
        )
    if issue_count != total_actual or total_actual != total_expected:
        findings.append(
            f"verification total arithmetic drift: issue_count={issue_count} total_actual={total_actual} total_expected={total_expected}"
        )
    profile_issues = int((profile.get("live_counts") or {}).get("issues") or 0)
    if profile_issues != total_expected:
        findings.append(
            f"profile issue count {profile_issues} != verification total_expected_issue_count {total_expected}"
        )
    profile_links = int((profile.get("live_counts") or {}).get("links") or 0)
    verification_links = int(
        verification.get("actual_expected_link_count")
        or verification.get("expected_link_count")
        or 0
    )
    if current_link_count != profile_links:
        findings.append(
            f"current link count {current_link_count} != profile live_counts.links {profile_links}"
        )
    if current_link_count != verification_links:
        findings.append(
            f"current link count {current_link_count} != verification link contract {verification_links}"
        )
    if verification.get("result") == "PASS" and auxiliary_expected == STALE_AUXILIARY_SEMANTICS_COUNT:
        findings.append("PASS artifact retains stale 31-auxiliary semantics")
    inconsistencies = [item for item in findings if item]
    local_sync = profile.get("local_sync") or {}
    if local_sync.get("state") == "LIVE_SYNCHRONIZED" and (
        verification.get("result") != "PASS"
        or list(verification.get("discrepancies") or [])
        or inconsistencies
    ):
        findings.append("LIVE_SYNCHRONIZED while the committed verification artifact is internally inconsistent")
    return findings


def validate_retired_canonical_registry(
    *,
    registry: Mapping[str, Any],
    records: list[Mapping[str, Any]],
    ledger: Mapping[str, Any],
    links: list[Mapping[str, str]],
) -> list[str]:
    findings: list[str] = []
    issues = list(registry.get("issues") or [])
    if int(registry.get("retired_count") or 0) != 21 or len(issues) != 21:
        findings.append(f"retirement registry must contain exactly 21 issues, found {len(issues)}")
    retired_ids = load_retired_local_ids(registry)
    if len(retired_ids) != 21:
        findings.append("retirement registry Local Issue IDs are not unique or complete")
    active_ids = {str(record.get("local_id")) for record in records}
    leaked = sorted(retired_ids & active_ids)
    if leaked:
        findings.append(f"retired Local Issue IDs remain in the active BAT corpus: {leaked}")
    key_map = ledger.get("issues") or {}
    leaked_keys = sorted(retired_ids & set(key_map))
    if leaked_keys:
        findings.append(f"retired Local Issue IDs remain in the active BAT key map: {leaked_keys}")
    for record in records:
        local_id = str(record.get("local_id"))
        parent = str(record.get("parent_id") or "")
        epic = str(record.get("epic_id") or "")
        if parent in retired_ids:
            findings.append(f"{local_id} retains retired parent {parent}")
        if epic in retired_ids:
            findings.append(f"{local_id} retains retired epic {epic}")
        for field in GRAPH_FIELDS:
            for target in record.get(field) or []:
                if target in retired_ids:
                    findings.append(f"{local_id} retains retired {field} target {target}")
    for row in links:
        source = str(row.get("source_local_id") or "")
        target = str(row.get("target_local_id") or "")
        if source in retired_ids or target in retired_ids:
            findings.append(f"expected BAT board link still names retired node: {source}->{target}")
    required = {
        "local_id",
        "former_bat_key",
        "current_batq_key",
        "current_project",
        "current_status",
        "moved_at",
        "summary",
        "issue_type_at_retirement",
        "parent_disposition",
        "rollback_snapshot_identity",
    }
    for item in issues:
        missing = sorted(required - set(item))
        if missing:
            findings.append(f"{item.get('local_id')}: retirement registry missing {missing}")
        if item.get("current_project") != "BATQ":
            findings.append(f"{item.get('local_id')}: current_project is not BATQ")
        if not str(item.get("current_batq_key") or "").startswith("BATQ-"):
            findings.append(f"{item.get('local_id')}: current_batq_key is not a BATQ key")
    return findings


def validate_committed_jira_live_convergence(repo_root: Path) -> list[str]:
    repo = Path(repo_root)
    findings: list[str] = []
    required_paths = (
        AUXILIARY_REGISTRY_REL,
        VERIFICATION_REL,
        PROFILE_REL,
        LEDGER_REL,
        RETIRED_REGISTRY_REL,
        LINKS_REL,
    )
    for rel in required_paths:
        if not (repo / rel).is_file():
            findings.append(f"missing:{rel}")
    if findings:
        return findings
    auxiliary = _load_json(repo / AUXILIARY_REGISTRY_REL)
    verification = _load_json(repo / VERIFICATION_REL)
    profile = _load_json(repo / PROFILE_REL)
    ledger = _load_json(repo / LEDGER_REL)
    registry = _load_json(repo / RETIRED_REGISTRY_REL)
    records = load_canonical_records(repo)
    with (repo / LINKS_REL).open(encoding="utf-8-sig", newline="") as handle:
        links = list(csv.DictReader(handle))
    findings.extend(
        validate_count_contracts(
            auxiliary_registry_count=len(auxiliary.get("issues") or []),
            canonical_record_count=len(records),
            current_link_count=len(links),
            verification=verification,
            profile=profile,
        )
    )
    findings.extend(
        validate_retired_canonical_registry(
            registry=registry,
            records=records,
            ledger=ledger,
            links=links,
        )
    )
    return findings

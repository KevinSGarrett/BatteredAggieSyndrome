"""Parse source-labeled 2006 official domains and audit the 2007-09-01 HTML table page."""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash
from aggie_analytics.data.tamu_official_historical_archive import sha256_file, validate_official_url
from aggie_analytics.data.tamu_official_historical_boxscores import (
    AuthorityViolation,
    decode_page,
    expected_authority,
    expected_scientific_nonclaims,
    table_rows,
)
from aggie_analytics.data.tamu_official_statcrew_preformatted import (
    DOMAINS,
    parse_preformatted_page,
)
from aggie_analytics.validation.artifact_binding import compute_identity


SCHEMA_VERSION = "aggie.data.tamu_official_2006_structured_domains.v1"
CONTRACT_RELATIVE = "configs/tamu_official_2006_structured_domains_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_2006_structured_domains_gate.json"
CONTRACT_ID = "BAT-596-TAMU-OFFICIAL-2006-STRUCTURED-DOMAINS-V1"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_2006_STRUCTURED_DOMAIN_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_2006_STRUCTURED_DOMAINS_PARSED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
CAPTURE_INDEX_RELATIVE = "features/tamu_official_2006_boxscores/capture_index.json"
BOX_2007_CAPTURE_INDEX = "features/tamu_official_2007_boxscores/capture_index.json"
INVENTORY_IDENTITY = "d39d35ff7cfacf2e39a524d0f1fdb97072158c50f84225ed8413771140efaa37"
INVENTORY_GATE_IDENTITY = "f1a5821ad081dce7058848ccc453344f0a2827030959049133b69db15689c851"
INVENTORY_GATE_RELATIVE = "artifacts/data_lake/tamu_official_historical_coverage_inventory_gate.json"
PINNED_BAT595_GATE_IDENTITY = "2a9c56a10b14cf5fec4dff1c3cd55d0b4440afdb9520fb308317a9ae59c47ed7"
PINNED_BAT595_ACQUISITION_IDENTITY = "1ed988f759f383b62625d582ac70ee306a36c84d92ccded9f70c9fd11bfed269"
PINNED_BAT595_DATASET_IDENTITY = "05ac9ce54a107007b433e52d7a52f85d7e20726d9aaf7ca204332a75f88cd697"
PINNED_BAT591_GATE_IDENTITY = "ed2ce7b95bd046a282116cf50aff84fec1e585f8dee848cc4451bec63bdf668c"
PINNED_BAT591_PAYLOAD_IDENTITY = "c7e061fcafa480f260b8f614ae6481747502ba5d933a786f584da442039fc338"
PINNED_BAT589_GATE_IDENTITY = "f2080b0ebb7815892732b2e600917e00da972edca0379888fa0010ff6bf17e51"
PINNED_BAT586_GATE_IDENTITY = "c62a09d2b3bcf7e69c6b6ea90993084d124a779d7ab779e8ebeab300b2a9c006"
HTML_AUDIT_URL = "https://files.12thman.com/history/football/stats/2007-2008/ta01-msu.htm"
HTML_AUDIT_DATE_LABEL = "2007-09-01"
REQUIRED_GATE_FIELDS = (
    "schema_version",
    "artifact_type",
    "result",
    "classification",
    "contract_id",
    "decision_unit",
    "jira_key",
    "disposition",
    "source_id",
    "inventory_identity",
    "payload_identity",
    "selected_seasons",
    "counts",
    "html_table_audit",
    "admissions",
    "authority",
    "scientific_nonclaims",
    "protected_lane",
    "upstream_identities",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    missing = [key for key in REQUIRED_GATE_FIELDS if key not in gate]
    if missing:
        raise AuthorityViolation("gate is missing required identity fields: " + ", ".join(missing))
    return compute_identity(gate, "gate_identity")


def load_2006_captures(repo_root: Path, data_root: Path) -> list[dict[str, Any]]:
    inventory = load_json(repo_root / INVENTORY_GATE_RELATIVE)
    if inventory.get("inventory_identity") != INVENTORY_IDENTITY or inventory.get("gate_identity") != INVENTORY_GATE_IDENTITY:
        raise AuthorityViolation("BAT-585 inventory identity rewritten")
    bat595 = load_json(repo_root / "artifacts/data_lake/tamu_official_2006_boxscore_gate.json")
    if bat595.get("gate_identity") != PINNED_BAT595_GATE_IDENTITY:
        raise AuthorityViolation("BAT-595 2006 acquisition identity rewritten")
    if bat595.get("acquisition_identity") != PINNED_BAT595_ACQUISITION_IDENTITY:
        raise AuthorityViolation("BAT-595 acquisition identity rewritten")
    if bat595.get("dataset_identity") != PINNED_BAT595_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-595 dataset identity rewritten")
    bat591 = load_json(repo_root / "artifacts/data_lake/tamu_official_statcrew_preformatted_gate.json")
    if bat591.get("gate_identity") != PINNED_BAT591_GATE_IDENTITY:
        raise AuthorityViolation("BAT-591 StatCrew identity rewritten")
    if bat591.get("payload_identity") != PINNED_BAT591_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-591 payload identity rewritten")
    bat589 = load_json(repo_root / "artifacts/data_lake/tamu_official_2007_boxscore_gate.json")
    if bat589.get("gate_identity") != PINNED_BAT589_GATE_IDENTITY:
        raise AuthorityViolation("BAT-589 2007 acquisition identity rewritten")
    bat586 = load_json(repo_root / "artifacts/data_lake/tamu_official_pre2010_boxscore_gate.json")
    if bat586.get("gate_identity") != PINNED_BAT586_GATE_IDENTITY:
        raise AuthorityViolation("BAT-586 2008/2009 acquisition identity rewritten")
    path = data_root / CAPTURE_INDEX_RELATIVE
    if not path.is_file():
        raise AuthorityViolation("BAT-595 capture index missing")
    captures = [dict(item) for item in (load_json(path).get("captures") or []) if int(item["source_season"]) == 2006]
    captures.sort(key=lambda item: item["url"])
    if len(captures) != 13:
        raise AuthorityViolation(f"expected 13 official 2006 captures, found {len(captures)}")
    return captures


def audit_html_table_page(data_root: Path) -> dict[str, Any]:
    index_path = data_root / BOX_2007_CAPTURE_INDEX
    if not index_path.is_file():
        raise AuthorityViolation("BAT-589 capture index missing for HTML-table audit")
    match = next(
        (item for item in (load_json(index_path).get("captures") or []) if item.get("url") == HTML_AUDIT_URL),
        None,
    )
    if match is None:
        raise AuthorityViolation("2007-09-01 HTML audit URL was not in the BAT-589 capture index")
    raw_path = data_root / match["raw_relative_path"]
    if not raw_path.is_file():
        raise AuthorityViolation("2007-09-01 HTML audit raw page missing")
    if sha256_file(raw_path) != match["raw_sha256"]:
        raise AuthorityViolation("2007-09-01 HTML audit raw hash drifted")
    rows = [
        {"row_order": index, "cells": list(cells), "source_url": HTML_AUDIT_URL, "source_sha256": match["raw_sha256"]}
        for index, cells in enumerate(table_rows(decode_page(raw_path.read_bytes())))
    ]
    present = "PRESENT" if rows else "ABSENT"
    return {
        "url": HTML_AUDIT_URL,
        "calendar_date_label": HTML_AUDIT_DATE_LABEL,
        "source_season": 2007,
        "source_sha256": match["raw_sha256"],
        "raw_relative_path": match["raw_relative_path"],
        "html_table_row_count": len(rows),
        "html_table_rows": rows,
        "rows_identity": stable_hash(rows),
        "domain_coverage": {"html_tables": present},
        "present_requires_serialized_hash_bound_rows": True,
        "rewrote_bat591": False,
    }


def _bind_rows(game: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for domain in DOMAINS:
        for item in game[domain]:
            rows.append({"domain": domain, **item})
    return rows


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    captures = load_2006_captures(repo_root, data_root)
    games: list[dict[str, Any]] = []
    for capture in captures:
        raw_path = data_root / capture["raw_relative_path"]
        if not raw_path.is_file():
            raise AuthorityViolation(f"captured raw page missing: {capture['raw_relative_path']}")
        raw_sha256 = str(capture["raw_sha256"])
        if sha256_file(raw_path) != raw_sha256:
            raise AuthorityViolation("raw capture bytes do not match recorded SHA-256")
        parsed = parse_preformatted_page(
            raw_path.read_bytes(),
            url=validate_official_url(str(capture["url"])),
            source_season=2006,
            raw_sha256=raw_sha256,
        )
        games.append(parsed)
    html_audit = audit_html_table_page(data_root)
    coverage_counts = Counter()
    for game in games:
        for domain in DOMAINS:
            if game["domain_coverage"][domain] == "PRESENT":
                coverage_counts[domain] += 1
    compact_games = [
        {
            "url": game["url"],
            "source_sha256": game["source_sha256"],
            "source_season": game["source_season"],
            "domain_coverage": {domain: game["domain_coverage"][domain] for domain in DOMAINS},
            "row_counts": {domain: len(game[domain]) for domain in DOMAINS},
            "rich_structured": game["rich_structured"],
            "warnings": game["warnings"],
        }
        for game in games
    ]
    compact_html = {
        "url": html_audit["url"],
        "calendar_date_label": html_audit["calendar_date_label"],
        "source_sha256": html_audit["source_sha256"],
        "html_table_row_count": html_audit["html_table_row_count"],
        "rows_identity": html_audit["rows_identity"],
        "domain_coverage": html_audit["domain_coverage"],
        "rewrote_bat591": False,
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "source_id": SOURCE_ID,
        "games": games,
        "rows": [_bind_rows(game) for game in games],
        "html_table_audit": html_audit,
        "admissions": {
            "bat_401": "DONE_VERIFIED_RETAIN_PROTECTED_LANE_BLOCKED",
            "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
            "bat_523": "IN_PROGRESS",
            "bat_591_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_595_payload": "CONSUMED_CAPTURES_ONLY",
            "gap_005": "OPEN",
            "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
            "ncaa_contest_identity": "NOT_CREATED",
            "participation_as_availability": "REJECTED",
            "name_only_player_merge": "REJECTED",
            "protected_lane": PROTECTED_LANE,
            "union_admission": "NOT_ADMITTED",
        },
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "protected_lane": PROTECTED_LANE,
    }
    payload["payload_identity"] = compute_identity(payload, "payload_identity")
    counts = {
        "target_games_total": 13,
        "parsed_games": len(games),
        "games_2006": len(games),
        "rich_structured_games": sum(1 for game in games if game["rich_structured"]),
        "metadata_only_games": sum(1 for game in games if not game["rich_structured"]),
        "ambiguous_boundary_games": sum(1 for game in games if game["warnings"]),
        "ncaa_contest_ids_created": 0,
        "name_only_player_merges": 0,
        "availability_claims": 0,
        "html_table_audit_rows": html_audit["html_table_row_count"],
        "html_table_audit_present": 1 if html_audit["domain_coverage"]["html_tables"] == "PRESENT" else 0,
        "games_admitted_to_union": 0,
        "pregame_availability_present": 0,
    }
    for domain in DOMAINS:
        counts[f"{domain}_present_games"] = int(coverage_counts[domain])
        counts[f"{domain}_absent_games"] = len(games) - int(coverage_counts[domain])
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_2006_STRUCTURED_DOMAINS_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": "POST-TASK-SRC014-2006-STRUCTURED-DOMAINS-001",
        "jira_key": "BAT-596",
        "disposition": "NEW_ENRICHED_PAYLOAD_PRIOR_IDENTITIES_PRESERVED",
        "source_id": SOURCE_ID,
        "inventory_identity": INVENTORY_IDENTITY,
        "payload_identity": payload["payload_identity"],
        "selected_seasons": [2006],
        "counts": counts,
        "games": compact_games,
        "html_table_audit": compact_html,
        "admissions": payload["admissions"],
        "authority": payload["authority"],
        "scientific_nonclaims": payload["scientific_nonclaims"],
        "protected_lane": PROTECTED_LANE,
        "upstream_identities": {
            "inventory_identity": INVENTORY_IDENTITY,
            "inventory_gate_identity": INVENTORY_GATE_IDENTITY,
            "bat595_gate_identity": PINNED_BAT595_GATE_IDENTITY,
            "bat595_acquisition_identity": PINNED_BAT595_ACQUISITION_IDENTITY,
            "bat595_dataset_identity": PINNED_BAT595_DATASET_IDENTITY,
            "bat591_gate_identity": PINNED_BAT591_GATE_IDENTITY,
            "bat591_payload_identity": PINNED_BAT591_PAYLOAD_IDENTITY,
            "bat589_gate_identity": PINNED_BAT589_GATE_IDENTITY,
            "bat586_gate_identity": PINNED_BAT586_GATE_IDENTITY,
        },
    }
    if counts["ncaa_contest_ids_created"] or gate["authority"]["ncaa_contest_identity"]:
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if any(game["availability_claim"] for game in games):
        raise AuthorityViolation("postgame participation treated as availability")
    if compact_html["rewrote_bat591"] or html_audit["rewrote_bat591"]:
        raise AuthorityViolation("BAT-591 identity rewritten")
    if html_audit["domain_coverage"]["html_tables"] == "PRESENT" and not html_audit["html_table_rows"]:
        raise AuthorityViolation("HTML-table PRESENT claimed without serialized rows")
    gate["gate_identity"] = compute_gate_identity(gate)
    return {"contract": contract, "gate": gate, "payload": payload, "captures": captures}


def materialize(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    payload = objects["payload"]
    root = data_root / objects["contract"]["payloads"]["enriched_root"] / payload["payload_identity"]
    write_json(root / "payload.json", payload)
    write_json(repo_root / GATE_RELATIVE, objects["gate"])
    return {
        "gate_identity": objects["gate"]["gate_identity"],
        "payload_identity": payload["payload_identity"],
        "parsed_games": objects["gate"]["counts"]["parsed_games"],
        "html_table_audit_rows": objects["gate"]["counts"]["html_table_audit_rows"],
    }


def lake_is_ready(data_root: Path) -> bool:
    return (data_root / CAPTURE_INDEX_RELATIVE).is_file() and (data_root / BOX_2007_CAPTURE_INDEX).is_file()


def validate_compact_gate(committed: Mapping[str, Any]) -> None:
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("authority", {}).get("historical_known_at_from_capture_time"):
        raise AuthorityViolation("retrieval time promoted to historical known-at")
    if committed.get("counts", {}).get("ncaa_contest_ids_created"):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if committed.get("result") != PASS_RESULT or committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("completion or classification forged")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not recompute")
    if committed.get("inventory_identity") != INVENTORY_IDENTITY:
        raise AuthorityViolation("inventory identity rebound incorrectly")
    if (committed.get("counts") or {}).get("pregame_availability_present"):
        raise AuthorityViolation("pregame availability claimed")
    html = committed.get("html_table_audit") or {}
    if (html.get("domain_coverage") or {}).get("html_tables") == "PRESENT":
        if not html.get("rows_identity") or int(html.get("html_table_row_count") or 0) <= 0:
            raise AuthorityViolation("HTML-table PRESENT claimed without serialized rows")
    upstream = committed.get("upstream_identities") or {}
    if upstream.get("bat591_gate_identity") != PINNED_BAT591_GATE_IDENTITY:
        raise AuthorityViolation("BAT-591 StatCrew identity rewritten")
    if upstream.get("bat595_gate_identity") != PINNED_BAT595_GATE_IDENTITY:
        raise AuthorityViolation("BAT-595 2006 acquisition identity rewritten")


def validate_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    gate: Mapping[str, Any] | None = None,
    require_rebuild: bool = True,
) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    validate_compact_gate(committed)
    ready = lake_is_ready(data_root)
    if require_rebuild and not ready:
        raise AuthorityViolation("external 2006 structured-domain reconstruction was required but the data root is not mounted")
    if not ready:
        return {
            "result": "PASS",
            "gate_identity": committed["gate_identity"],
            "external_reconstruction": "NOT_MOUNTED",
        }
    expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    if committed != expected["gate"]:
        raise AuthorityViolation("committed 2006 structured-domain gate does not match independent reconstruction")
    payload_path = (
        data_root
        / expected["contract"]["payloads"]["enriched_root"]
        / expected["payload"]["payload_identity"]
        / "payload.json"
    )
    if not payload_path.is_file():
        raise AuthorityViolation("external enriched payload missing")
    if load_json(payload_path) != expected["payload"]:
        raise AuthorityViolation("external enriched payload does not match reconstruction")
    return {
        "result": "PASS",
        "gate_identity": expected["gate"]["gate_identity"],
        "payload_identity": expected["payload"]["payload_identity"],
        "parsed_games": expected["gate"]["counts"]["parsed_games"],
        "html_table_audit_rows": expected["gate"]["counts"]["html_table_audit_rows"],
        "external_reconstruction": "MOUNTED",
    }


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))

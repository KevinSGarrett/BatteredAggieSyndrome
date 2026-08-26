"""Acquire and normalize official SRC-014 1997 box scores from Phase 2 allowlist."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import normalize_team_name, stable_hash
from aggie_analytics.data.tamu_official_historical_archive import (
    classify_capture,
    compact_capture,
    direct_http_get,
    persist_capture,
    sha256_file,
    validate_official_url,
)
from aggie_analytics.data.tamu_official_historical_boxscores import (
    AuthorityViolation,
    INDEX_RESULT_RE,
    compact_game,
    expected_admissions,
    expected_authority,
    expected_scientific_nonclaims,
    match_to_official_index,
    opponent_candidate,
    parse_official_box_page,
    reconstruct_index_date,
    site_token,
)
from aggie_analytics.data.tamu_official_historical_coverage_inventory import (
    GATE_RELATIVE as INVENTORY_GATE_RELATIVE,
    REGISTRY_SHA256,
)

SCHEMA_VERSION = "aggie.data.tamu_official_1997_boxscores.v1"
CONTRACT_RELATIVE = "configs/tamu_official_1997_boxscore_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_1997_boxscore_gate.json"
CONTRACT_ID = "BAT-XXX-TAMU-OFFICIAL-1997-BOXSCORES-V1"
JIRA_KEY = "BAT-XXX"
SOURCE_ID = "SRC-014"
SEASON = 1997
OFFICIAL_1997_INDEX_URL = "https://files.12thman.com/history/football/years/1997.html"
CAPTURE_INDEX_RELATIVE = "features/tamu_official_1997_boxscores/capture_index.json"
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_1997_BOXSCORE_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_1997_BOXSCORES_NORMALIZED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
INVENTORY_IDENTITY = "d39d35ff7cfacf2e39a524d0f1fdb97072158c50f84225ed8413771140efaa37"
BAT1997_GATE_RELATIVE = "artifacts/data_lake/tamu_official_1997_season_index_gate.json"
MODULE_RELATIVE = "src/aggie_analytics/data/tamu_official_1997_boxscores.py"
CODE_BUNDLE_RELATIVE = (MODULE_RELATIVE,)
RESULT_FALLBACK_RE = re.compile(r"\b([WL])\s*,?\s*(\d+)\s*-\s*(\d+)\b", re.IGNORECASE)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def compute_code_identity(repo_root: Path) -> str:
    hasher = hashlib.sha256()
    hasher.update(b"aggie.boxscores.code_bundle.v1\n")
    for relative in CODE_BUNDLE_RELATIVE:
        path = repo_root / relative
        if not path.is_file():
            raise AuthorityViolation(f"code bundle member missing: {relative}")
        hasher.update(b"PATH:")
        hasher.update(relative.replace("\\", "/").encode("utf-8"))
        hasher.update(b"\n")
        hasher.update(path.read_bytes())
        hasher.update(b"\n")
    return hasher.hexdigest()


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    mutable = {key: value for key, value in gate.items() if key != "gate_identity"}
    return hashlib.sha256(
        json.dumps(mutable, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    ).hexdigest()


def load_source_index(repo_root: Path) -> dict[str, Any]:
    inventory_gate = load_json(repo_root / INVENTORY_GATE_RELATIVE)
    if inventory_gate.get("inventory_identity") != INVENTORY_IDENTITY:
        raise AuthorityViolation("BAT-585 inventory identity rewritten")
    gate = load_json(repo_root / BAT1997_GATE_RELATIVE)
    if gate.get("official_index_url") != OFFICIAL_1997_INDEX_URL:
        raise AuthorityViolation("guessed or substituted 1997 official URL")
    urls = [validate_official_url(str(url)) for url in (gate.get("box_score_urls") or [])]
    if not urls:
        raise AuthorityViolation("1997 allowlist emitted no official box URLs")
    return {
        "gate": gate,
        "season": SEASON,
        "official_index_url": OFFICIAL_1997_INDEX_URL,
        "box_score_urls": urls,
        "game_rows": list(gate.get("game_rows") or []),
    }


def selected_targets(source: Mapping[str, Any]) -> list[dict[str, Any]]:
    parent = validate_official_url(str(source["official_index_url"]))
    return [{"season": SEASON, "official_index_url": parent, "box_url": validate_official_url(str(url))} for url in source["box_score_urls"]]


def load_capture_index(data_root: Path) -> dict[str, Any]:
    path = data_root / CAPTURE_INDEX_RELATIVE
    if not path.is_file():
        return {"captures": []}
    return load_json(path)


def capture_map(index: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["url"]: item for item in index.get("captures") or []}


def compact_capture_row(record: Mapping[str, Any], *, source_order: int) -> dict[str, Any]:
    compact = compact_capture(record)
    compact["response_sha256"] = str(record.get("response_sha256") or compact.get("response_sha256") or "")
    compact["source_order"] = int(source_order)
    if not compact["response_sha256"] or compact["response_sha256"] != compact.get("raw_sha256"):
        raise AuthorityViolation(f"response SHA mismatch for {compact.get('url')}")
    return compact


def acquire_missing(*, data_root: Path, targets: list[Mapping[str, Any]], existing: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    order_by_url = {item["box_url"]: idx for idx, item in enumerate(targets, start=1)}
    allowed = frozenset(order_by_url)
    extra = sorted(set(existing) - allowed)
    if extra:
        raise AuthorityViolation(f"invented or non-allowlisted capture URL: {extra}")
    captures: list[dict[str, Any]] = []
    for target in targets:
        url = target["box_url"]
        source_order = order_by_url[url]
        if url in existing:
            row = dict(existing[url])
            row["source_order"] = source_order
            captures.append(row)
            continue
        fetched = direct_http_get(url)
        body = fetched.pop("body")
        fetched["parent_url"] = target["official_index_url"]
        fetched["page_family"] = "box_scores"
        fetched["source_season"] = target["season"]
        fetched["rights_disposition"] = "PRIVATE_RESEARCH_METADATA_ONLY_NONBLOCKING"
        try:
            fetched["parser_disposition"] = classify_capture(url, body, fetched.get("content_type"), int(fetched["status"]))
        except AuthorityViolation as exc:
            fetched["parser_disposition"] = f"REJECTED:{exc}"
        stored = persist_capture(data_root, fetched, body)
        captures.append(compact_capture_row(stored, source_order=source_order))
    return sorted(captures, key=lambda item: int(item["source_order"]))


def index_rows_from_phase2(source: Mapping[str, Any], allowed: frozenset[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in source["game_rows"]:
        box_url = row.get("box_score_url")
        if not box_url:
            continue
        box_url = validate_official_url(str(box_url))
        if box_url not in allowed:
            raise AuthorityViolation(f"phase2 row emitted non-allowlisted URL: {box_url}")
        result_raw = str(row.get("source_result") or "").strip()
        result = INDEX_RESULT_RE.search(result_raw) or RESULT_FALLBACK_RE.search(result_raw)
        if result is None:
            raise AuthorityViolation(f"phase2 row missing W/L/score: {row}")
        raw_date = str(row.get("source_date") or "").strip()
        rows.append(
            {
                "source_season": SEASON,
                "raw_date": raw_date,
                "index_date_candidate": reconstruct_index_date(raw_date, SEASON),
                "opponent_raw": str(row.get("source_opponent") or ""),
                "opponent_candidate": opponent_candidate(str(row.get("source_opponent") or "")),
                "opponent_normalized": normalize_team_name(str(row.get("source_opponent") or "")),
                "location_raw": str(row.get("source_location") or ""),
                "site_token": site_token(str(row.get("source_location") or "")),
                "result_raw": result_raw,
                "tamu_points": int(result.group(2)),
                "opponent_points": int(result.group(3)),
                "box_url": box_url,
                "venue_state": "NEUTRAL" if "vs." in str(row.get("source_opponent") or "").lower() else "HOME" if "college station" in str(row.get("source_location") or "").lower() else "AWAY",
                "schedule_sequence": int(row.get("source_row_order") or 0),
            }
        )
    found = {item["box_url"] for item in rows}
    missing = sorted(allowed - found)
    if missing:
        raise AuthorityViolation(f"phase2 rows omitted allowlisted box URLs: {missing}")
    return sorted(rows, key=lambda item: int(item["schedule_sequence"]))


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    source = load_source_index(repo_root)
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    targets = selected_targets(source)
    allowed = frozenset(item["box_url"] for item in targets)
    captures_by_url = capture_map(load_capture_index(data_root))
    if sorted(set(captures_by_url) - allowed):
        raise AuthorityViolation("capture index contains non-allowlisted URLs")
    if any(item["box_url"] not in captures_by_url for item in targets):
        raise AuthorityViolation("capture index missing allowlisted URLs")
    index_rows = index_rows_from_phase2(source, allowed)
    games: list[dict[str, Any]] = []
    normalized_rows: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    match_statuses: Counter[str] = Counter()
    for source_order, target in enumerate(targets, start=1):
        record = dict(captures_by_url[target["box_url"]])
        raw_path = data_root / str(record.get("raw_relative_path") or "")
        if not raw_path.is_file():
            blocked.append({**record, "disposition": "RAW_FILE_MISSING"})
            continue
        if sha256_file(raw_path) != record.get("raw_sha256"):
            raise AuthorityViolation(f"raw box-score hash drifted: {target['box_url']}")
        if int(record.get("response_status") or 0) != 200 or record.get("parser_disposition") != "VERIFIED_OFFICIAL_SCHOOL_PAGE":
            blocked.append({**record, "disposition": "OFFICIAL_ROUTE_ACCESS_BLOCKED_OR_REJECTED"})
            continue
        try:
            parsed = parse_official_box_page(
                raw_path.read_bytes(),
                url=target["box_url"],
                source_season=SEASON,
                raw_sha256=str(record["raw_sha256"]),
                allowed_urls=allowed,
                allow_season_header_conflict=True,
            )
        except AuthorityViolation as exc:
            blocked.append({**record, "disposition": "PARSE_REJECTED", "parse_error": str(exc)})
            continue
        match = match_to_official_index(parsed, index_rows)
        match_statuses[str(match["canonical_game_match_status"])] += 1
        compact = compact_game(parsed, match)
        compact["parent_url"] = target["official_index_url"]
        compact["response_status"] = record.get("response_status")
        compact["raw_relative_path"] = record.get("raw_relative_path")
        compact["source_order"] = source_order
        compact["response_sha256"] = record.get("response_sha256")
        compact["raw_sha256"] = record.get("raw_sha256")
        compact["content_type"] = record.get("content_type")
        compact["retrieved_at"] = record.get("timestamp")
        games.append(compact)
        normalized_rows.append(
            {
                "game": compact,
                "officials": parsed["officials"],
                "team_statistics": parsed["team_statistics"],
                "player_stat_candidates": parsed["player_stat_candidates"],
                "scoring_plays": parsed["scoring_plays"],
                "drives": parsed["drives"],
                "play_by_play": parsed["play_by_play"],
                "starters": parsed["starters"],
                "participation": parsed["participation"],
                "domain_coverage": parsed["domain_coverage"],
            }
        )
    games = sorted(games, key=lambda item: (item["calendar_date"], item["url"]))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_1997_BOXSCORES",
        "contract_id": CONTRACT_ID,
        "decision_unit": "POST-TASK-SRC014-1997-OFFICIAL-ACQUISITION-001",
        "jira_key": JIRA_KEY,
        "source_id": SOURCE_ID,
        "inventory_identity": INVENTORY_IDENTITY,
        "selected_seasons": [SEASON],
        "captures": [captures_by_url[item["box_url"]] for item in targets],
        "games": games,
        "normalized_rows": normalized_rows,
        "blocked_or_partial": blocked,
        "conflicts": conflicts,
        "admissions": expected_admissions() | {"union_admission": "NOT_ADMITTED", "bat_523": "IN_PROGRESS"},
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "protected_lane": PROTECTED_LANE,
    }
    payload["dataset_identity"] = stable_hash({"games": games, "captures": payload["captures"], "conflicts": conflicts})
    payload["games_identity"] = stable_hash(games)
    payload["acquisition_identity"] = stable_hash(payload["captures"])
    counts = {
        "target_games_total": len(targets),
        "captured_pages_total": sum(1 for item in payload["captures"] if item.get("response_status") == 200),
        "verified_official_pages": sum(1 for item in payload["captures"] if item.get("parser_disposition") == "VERIFIED_OFFICIAL_SCHOOL_PAGE"),
        "normalized_games": len(games),
        "blocked_or_partial_pages": len(blocked),
        "matched_strong_tuple": int(match_statuses.get("MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE", 0)),
        "date_conflicts": int(match_statuses.get("OFFICIAL_INDEX_DATE_CONFLICT", 0)),
        "name_only_insufficient": int(match_statuses.get("NAME_ONLY_INSUFFICIENT", 0)),
        "unmatched_strong_tuple": int(match_statuses.get("UNMATCHED_STRONG_TUPLE", 0)),
        "ncaa_contest_ids_created": 0,
        "games_admitted_to_union": 0,
    }
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_1997_BOXSCORE_GATE",
        "result": PASS_RESULT if not blocked and counts["normalized_games"] == counts["target_games_total"] else "PARTIAL_OFFICIAL_1997_BOXSCORES",
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": "POST-TASK-SRC014-1997-OFFICIAL-ACQUISITION-001",
        "jira_key": JIRA_KEY,
        "disposition": "NORMALIZED_CANDIDATE_ONLY_NO_UNION_MUTATION",
        "source_id": SOURCE_ID,
        "inventory_identity": INVENTORY_IDENTITY,
        "acquisition_identity": payload["acquisition_identity"],
        "dataset_identity": payload["dataset_identity"],
        "games_identity": payload["games_identity"],
        "selected_seasons": [SEASON],
        "counts": counts,
        "admissions": payload["admissions"],
        "authority": payload["authority"],
        "scientific_nonclaims": payload["scientific_nonclaims"],
        "protected_lane": PROTECTED_LANE,
        "validator_code_identity": compute_code_identity(repo_root),
        "upstream_identities": {"inventory_identity": INVENTORY_IDENTITY, "protected_split_registry_sha256": REGISTRY_SHA256},
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    return {"contract": contract, "gate": gate, "payload": payload}


def materialize_boxscores(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    source = load_source_index(repo_root)
    targets = selected_targets(source)
    captures = acquire_missing(data_root=data_root, targets=targets, existing=capture_map(load_capture_index(data_root)))
    write_json(data_root / CAPTURE_INDEX_RELATIVE, {"schema_version": SCHEMA_VERSION, "captures": captures})
    objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    payload = objects["payload"]
    root = data_root / objects["contract"]["payloads"]["normalized_root"] / payload["dataset_identity"]
    write_json(root / "payload.json", payload)
    write_json(root / "acquisition_manifest.json", {"acquisition_identity": payload["acquisition_identity"], "captures": payload["captures"]})
    write_json(repo_root / GATE_RELATIVE, objects["gate"])
    return {
        "gate_identity": objects["gate"]["gate_identity"],
        "dataset_identity": payload["dataset_identity"],
        "acquisition_identity": payload["acquisition_identity"],
        "normalized_games": objects["gate"]["counts"]["normalized_games"],
    }


def validate_artifact(*, repo_root: Path, data_root: Path, gate: Mapping[str, Any] | None = None, require_rebuild: bool = True) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("completion or classification forged")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not recompute")
    if committed.get("validator_code_identity") != compute_code_identity(repo_root):
        raise AuthorityViolation("changed code with stale code identity")
    if require_rebuild:
        expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
        if committed != expected["gate"]:
            raise AuthorityViolation("committed 1997 box-score gate does not match independent reconstruction")
        payload_path = data_root / expected["contract"]["payloads"]["normalized_root"] / expected["payload"]["dataset_identity"] / "payload.json"
        if not payload_path.is_file():
            raise AuthorityViolation("external normalized payload missing")
        if load_json(payload_path) != expected["payload"]:
            raise AuthorityViolation("external normalized payload does not match reconstruction")
    return {
        "result": "PASS",
        "gate_identity": committed["gate_identity"],
        "dataset_identity": committed["dataset_identity"],
        "acquisition_identity": committed["acquisition_identity"],
    }


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))

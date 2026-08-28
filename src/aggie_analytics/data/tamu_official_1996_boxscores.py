"""Acquire and normalize official SRC-014 1996 box scores from mounted captures."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import normalize_team_name, stable_hash
from aggie_analytics.data.tamu_official_historical_archive import compact_capture, sha256_file, validate_official_url
from aggie_analytics.data.tamu_official_historical_boxscores import (
    AuthorityViolation,
    INDEX_RESULT_RE,
    compact_game,
    decode_page,
    expected_admissions,
    expected_authority,
    expected_scientific_nonclaims,
    match_to_official_index,
    opponent_candidate,
    parse_scoring_plays,
    reconstruct_index_date,
    site_token,
)
from aggie_analytics.data.tamu_official_historical_coverage_inventory import (
    GATE_RELATIVE as INVENTORY_GATE_RELATIVE,
    REGISTRY_SHA256,
)
from aggie_analytics.data.tamu_official_legacy_h2_game_identity import (
    LEGACY_H2_PARSER_VERSION,
    parse_legacy_game_identity,
)
from aggie_analytics.data.tamu_official_statcrew_preformatted import parse_preformatted_page

SCHEMA_VERSION = "aggie.data.tamu_official_1996_boxscores.v1"
CONTRACT_RELATIVE = "configs/tamu_official_1996_boxscore_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_1996_boxscore_gate.json"
CONTRACT_ID = "BAT-649-TAMU-OFFICIAL-1996-BOXSCORES-V1"
JIRA_KEY = "BAT-649"
SOURCE_ID = "SRC-014"
SEASON = 1996
OFFICIAL_1996_INDEX_URL = "https://files.12thman.com/history/football/years/1996.html"
CAPTURE_INDEX_RELATIVE = "features/tamu_official_1996_boxscores/capture_index.json"
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_1996_BOXSCORE_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_1996_BOXSCORES_NORMALIZED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
INVENTORY_IDENTITY = "d39d35ff7cfacf2e39a524d0f1fdb97072158c50f84225ed8413771140efaa37"
BAT1996_GATE_RELATIVE = "artifacts/data_lake/tamu_official_1996_season_index_gate.json"
MODULE_RELATIVE = "src/aggie_analytics/data/tamu_official_1996_boxscores.py"
LEGACY_PARSER_RELATIVE = "src/aggie_analytics/data/tamu_official_legacy_h2_game_identity.py"
CODE_BUNDLE_RELATIVE = (MODULE_RELATIVE, LEGACY_PARSER_RELATIVE)
PREDECESSOR_GATE_IDENTITY = "77997c43e9939a269501e73950487dca26af18de0c331275f2cc56e1c23b9399"
PREDECESSOR_DATASET_IDENTITY = "cfe8af8d3bca4afca15dffcca4514d85626cfadb191af769a69bac8fb2d8b9d7"
PREDECESSOR_ACQUISITION_IDENTITY = "76a5923573b9e8bbb094c7a526d22f2357580acb9093e05cec3f6df4aa4a0816"
PREDECESSOR_GAMES_IDENTITY = "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
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
    gate = load_json(repo_root / BAT1996_GATE_RELATIVE)
    if gate.get("official_index_url") != OFFICIAL_1996_INDEX_URL:
        raise AuthorityViolation("guessed or substituted 1996 official URL")
    urls = [validate_official_url(str(url)) for url in (gate.get("box_score_urls") or [])]
    if not urls:
        raise AuthorityViolation("1996 allowlist emitted no official box URLs")
    return {
        "gate": gate,
        "season": SEASON,
        "official_index_url": OFFICIAL_1996_INDEX_URL,
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
    response_status = int(record.get("response_status") or record.get("status") or 0)
    if response_status <= 0 and str(record.get("parser_disposition") or "") == "VERIFIED_OFFICIAL_SCHOOL_PAGE":
        response_status = 200
    compact["response_status"] = response_status
    compact["parser_disposition"] = str(record.get("parser_disposition") or compact.get("parser_disposition") or "")
    compact["raw_relative_path"] = str(record.get("raw_relative_path") or compact.get("raw_relative_path") or "")
    compact["source_order"] = int(source_order)
    if not compact["response_sha256"] or compact["response_sha256"] != compact.get("raw_sha256"):
        raise AuthorityViolation(f"response SHA mismatch for {compact.get('url')}")
    return compact


def required_capture_rows(*, targets: list[Mapping[str, Any]], existing: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    order_by_url = {item["box_url"]: idx for idx, item in enumerate(targets, start=1)}
    allowed = frozenset(order_by_url)
    extra = sorted(set(existing) - allowed)
    if extra:
        raise AuthorityViolation(f"invented or non-allowlisted capture URL: {extra}")
    missing = sorted(url for url in allowed if url not in existing)
    if missing:
        raise AuthorityViolation(f"capture index missing allowlisted URLs: {missing}")
    captures: list[dict[str, Any]] = []
    for target in targets:
        url = target["box_url"]
        row = dict(existing[url])
        row["source_order"] = int(order_by_url[url])
        captures.append(compact_capture_row(row, source_order=int(row["source_order"])))
    return sorted(captures, key=lambda item: int(item["source_order"]))


def index_rows_from_phase6(source: Mapping[str, Any], allowed: frozenset[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    missing_or_malformed: list[dict[str, Any]] = []
    for row in source["game_rows"]:
        box_url = row.get("box_score_url")
        if not box_url:
            missing_or_malformed.append(dict(row))
            continue
        box_url = validate_official_url(str(box_url))
        if box_url not in allowed:
            raise AuthorityViolation(f"phase6 row emitted non-allowlisted URL: {box_url}")
        result_raw = str(row.get("source_result") or "").strip()
        result = INDEX_RESULT_RE.search(result_raw) or RESULT_FALLBACK_RE.search(result_raw)
        if result is None:
            raise AuthorityViolation(f"phase6 row missing W/L/score: {row}")
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
                "venue_state": "NEUTRAL"
                if "vs." in str(row.get("source_opponent") or "").lower()
                else "HOME"
                if "college station" in str(row.get("source_location") or "").lower()
                else "AWAY",
                "schedule_sequence": int(row.get("source_row_order") or 0),
            }
        )
    found = {item["box_url"] for item in rows}
    missing = sorted(allowed - found)
    if missing:
        raise AuthorityViolation(f"phase6 rows omitted allowlisted box URLs: {missing}")
    return sorted(rows, key=lambda item: int(item["schedule_sequence"])), missing_or_malformed


def _rejected_record(*, record: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {
        "url": str(record.get("url") or ""),
        "source_url": str(record.get("url") or ""),
        "source_sha256": str(record.get("raw_sha256") or "") or None,
        "source_season": SEASON,
        "source_order": int(record.get("source_order") or 0),
        "capture_disposition": str(record.get("parser_disposition") or "UNCLASSIFIED"),
        "rejection_reason": reason,
        "rejection_source": "POST-TASK-SRC014-1996-OFFICIAL-ACQUISITION-SUCCESSOR-001.rejected_official_1996_games",
        "membership_admitted": False,
        "availability": "NOT_ESTABLISHED",
        "availability_claim": False,
        "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "ncaa_contest_id": None,
    }


def _compose_game_surface(
    *,
    identity: Mapping[str, Any],
    structured: Mapping[str, Any],
    scoring_rows: list[dict[str, Any]],
    record: Mapping[str, Any],
) -> dict[str, Any]:
    coverage = {
        "game_identity_metadata": "PRESENT",
        "season": "PRESENT",
        "played_date": "PRESENT",
        "teams": "PRESENT",
        "scores": "PRESENT",
        "quarter_scoring": "PRESENT",
        "site_venue": "PRESENT" if identity.get("site") else "ABSENT",
        "attendance": "ABSENT",
        "kickoff_time": "ABSENT",
        "end_time": "ABSENT",
        "duration": "ABSENT",
        "weather": "ABSENT",
        "officials": "ABSENT",
        "team_statistics": "PRESENT" if structured.get("team_statistics") else "ABSENT",
        "individual_player_statistics": "PRESENT" if structured.get("individual_player_statistics") else "ABSENT",
        "scoring_summary": "PRESENT" if scoring_rows else "ABSENT",
        "drives": "PRESENT" if structured.get("drives") else "ABSENT",
        "play_by_play": "PRESENT" if structured.get("play_by_play") else "ABSENT",
        "participation": "ABSENT",
        "starters": "ABSENT",
        "penalties": "ABSENT",
        "turnovers": "ABSENT",
    }
    return {
        "url": identity["resolved_official_url"],
        "source_sha256": identity["raw_sha256"],
        "source_season": SEASON,
        "football_season": identity["football_season"],
        "calendar_date": identity["calendar_date"],
        "raw_date": identity["raw_date"],
        "raw_game_label": identity["raw_game_label"],
        "visitor_name": identity["visitor_name"],
        "home_name": identity["home_name"],
        "tamu_side": identity["tamu_side"],
        "opponent_candidate": identity["opponent_candidate"],
        "opponent_normalized": identity["opponent_normalized"],
        "tamu_points": identity["tamu_points"],
        "opponent_points": identity["opponent_points"],
        "visitor_points": identity["visitor_points"],
        "home_points": identity["home_points"],
        "site": identity["site"],
        "site_token": identity["site_token"],
        "stadium": None,
        "attendance": None,
        "kickoff_time": None,
        "end_time": None,
        "duration": None,
        "weather": None,
        "officials": [],
        "team_statistics": list(structured.get("team_statistics") or []),
        "player_stat_candidates": list(structured.get("individual_player_statistics") or []),
        "scoring_plays": scoring_rows,
        "drives": list(structured.get("drives") or []),
        "play_by_play": list(structured.get("play_by_play") or []),
        "starters": [],
        "participation": [],
        "domain_coverage": coverage,
        "parser_version": LEGACY_H2_PARSER_VERSION,
        "parser_identity": LEGACY_H2_PARSER_VERSION,
        "temporal_authority": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "historical_publication_time": None,
        "ncaa_contest_id": None,
        "canonical_game_id": None,
        "availability_claim": False,
        "parent_url": str(record.get("parent_url") or OFFICIAL_1996_INDEX_URL),
        "raw_relative_path": str(record.get("raw_relative_path") or ""),
        "response_status": int(record.get("response_status") or 0),
        "response_sha256": str(record.get("response_sha256") or ""),
        "content_type": str(record.get("content_type") or ""),
        "retrieved_at": record.get("timestamp"),
        "source_order": int(record.get("source_order") or 0),
    }


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    source = load_source_index(repo_root)
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    targets = selected_targets(source)
    allowed = frozenset(item["box_url"] for item in targets)
    captures_by_url = capture_map(load_capture_index(data_root))
    captures = required_capture_rows(targets=targets, existing=captures_by_url)
    index_rows, missing_rows = index_rows_from_phase6(source, allowed)
    games: list[dict[str, Any]] = []
    normalized_rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    match_statuses: Counter[str] = Counter()
    for target in targets:
        record = dict(captures_by_url[target["box_url"]])
        source_order = int(record.get("source_order") or 0)
        raw_path = data_root / str(record["raw_relative_path"])
        if not raw_path.is_file():
            rejected.append(_rejected_record(record=record, reason="RAW_FILE_MISSING"))
            continue
        raw_file_sha256 = sha256_file(raw_path)
        if raw_file_sha256 != record.get("raw_sha256"):
            raise AuthorityViolation(f"raw box-score hash drifted: {target['box_url']}")
        if int(record.get("response_status") or 0) != 200 or record.get("parser_disposition") != "VERIFIED_OFFICIAL_SCHOOL_PAGE":
            rejected.append(_rejected_record(record=record, reason="OFFICIAL_ROUTE_ACCESS_BLOCKED_OR_REJECTED"))
            continue
        body = raw_path.read_bytes()
        try:
            identity = parse_legacy_game_identity(
                body=body,
                url=target["box_url"],
                source_season=SEASON,
                source_order=source_order,
                raw_sha256=str(record["raw_sha256"]),
                raw_file_sha256=raw_file_sha256,
                allowed_urls=allowed,
                official_index_url=OFFICIAL_1996_INDEX_URL,
                parent_url=str(record.get("parent_url") or OFFICIAL_1996_INDEX_URL),
            )
        except AuthorityViolation as exc:
            rejected.append(_rejected_record(record=record, reason=f"PARSE_REJECTED:{exc}"))
            continue
        structured = parse_preformatted_page(
            body,
            url=validate_official_url(str(record["url"])),
            source_season=SEASON,
            raw_sha256=str(record["raw_sha256"]),
        )
        parsed = _compose_game_surface(
            identity=identity,
            structured=structured,
            scoring_rows=parse_scoring_plays(decode_page(body)),
            record=record,
        )
        match = match_to_official_index(parsed, index_rows)
        match_statuses[str(match["canonical_game_match_status"])] += 1
        if match["conflict_status"] not in {None, "NONE"}:
            conflicts.append({"url": parsed["url"], "match_status": match["canonical_game_match_status"], "conflict_status": match["conflict_status"]})
        if match["canonical_game_match_status"] not in {
            "MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE",
            "OFFICIAL_INDEX_DATE_CONFLICT",
        }:
            rejected.append(_rejected_record(record=record, reason=f"{match['canonical_game_match_status']}:{match['conflict_status']}"))
            continue
        compact = compact_game(parsed, match)
        compact["parent_url"] = OFFICIAL_1996_INDEX_URL
        compact["response_status"] = int(record.get("response_status") or 0)
        compact["raw_relative_path"] = str(record.get("raw_relative_path") or "")
        compact["source_order"] = source_order
        compact["response_sha256"] = str(record.get("response_sha256") or "")
        compact["raw_sha256"] = str(record.get("raw_sha256") or "")
        compact["content_type"] = str(record.get("content_type") or "")
        compact["retrieved_at"] = record.get("timestamp")
        compact["resolved_official_url"] = str(identity["resolved_official_url"])
        compact["official_season_index_url"] = str(identity["official_season_index_url"])
        compact["emitted_box_href"] = str(identity["emitted_box_href"])
        compact["raw_file_sha256"] = raw_file_sha256
        compact["parser_identity"] = LEGACY_H2_PARSER_VERSION
        games.append(compact)
        normalized_rows.append(
            {
                "game": compact,
                "officials": [],
                "team_statistics": parsed["team_statistics"],
                "individual_player_statistics": parsed["player_stat_candidates"],
                "player_stat_candidates": parsed["player_stat_candidates"],
                "scoring_summary": parsed["scoring_plays"],
                "drives": parsed["drives"],
                "play_by_play": parsed["play_by_play"],
                "starters": [],
                "participation": [],
                "domain_coverage": parsed["domain_coverage"],
                "parser_identity": LEGACY_H2_PARSER_VERSION,
            }
        )
    games = sorted(games, key=lambda item: (item["calendar_date"], item["url"]))
    rejected = sorted(rejected, key=lambda item: item["url"])
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_1996_BOXSCORES",
        "contract_id": CONTRACT_ID,
        "decision_unit": "POST-TASK-SRC014-1996-OFFICIAL-ACQUISITION-SUCCESSOR-001",
        "jira_key": JIRA_KEY,
        "source_id": SOURCE_ID,
        "inventory_identity": INVENTORY_IDENTITY,
        "selected_seasons": [SEASON],
        "captures": captures,
        "games": games,
        "normalized_rows": normalized_rows,
        "rejected_official_1996_games": rejected,
        "malformed_or_missing_index_rows": missing_rows,
        "conflicts": conflicts,
        "predecessor_gate_identity": PREDECESSOR_GATE_IDENTITY,
        "predecessor_dataset_identity": PREDECESSOR_DATASET_IDENTITY,
        "predecessor_acquisition_identity": PREDECESSOR_ACQUISITION_IDENTITY,
        "predecessor_games_identity": PREDECESSOR_GAMES_IDENTITY,
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
        "blocked_or_partial_pages": len(rejected),
        "matched_strong_tuple": int(match_statuses.get("MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE", 0)),
        "date_conflicts": int(match_statuses.get("OFFICIAL_INDEX_DATE_CONFLICT", 0)),
        "name_only_insufficient": int(match_statuses.get("NAME_ONLY_INSUFFICIENT", 0)),
        "unmatched_strong_tuple": int(match_statuses.get("UNMATCHED_STRONG_TUPLE", 0)),
        "ncaa_contest_ids_created": 0,
        "games_admitted_to_union": 0,
    }
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_1996_BOXSCORE_GATE",
        "result": PASS_RESULT if not rejected and counts["normalized_games"] == counts["target_games_total"] else "PARTIAL_OFFICIAL_1996_BOXSCORES",
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": "POST-TASK-SRC014-1996-OFFICIAL-ACQUISITION-SUCCESSOR-001",
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
        "parser_identity": LEGACY_H2_PARSER_VERSION,
        "validator_code_identity": compute_code_identity(repo_root),
        "upstream_identities": {
            "inventory_identity": INVENTORY_IDENTITY,
            "protected_split_registry_sha256": REGISTRY_SHA256,
            "season_index_gate_identity": source["gate"]["gate_identity"],
            "predecessor_gate_identity": PREDECESSOR_GATE_IDENTITY,
            "predecessor_dataset_identity": PREDECESSOR_DATASET_IDENTITY,
        },
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    return {"contract": contract, "gate": gate, "payload": payload}


def materialize_boxscores(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    source = load_source_index(repo_root)
    targets = selected_targets(source)
    captures = required_capture_rows(targets=targets, existing=capture_map(load_capture_index(data_root)))
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
            raise AuthorityViolation("committed 1996 box-score gate does not match independent reconstruction")
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

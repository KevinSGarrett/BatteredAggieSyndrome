"""Acquire and normalize official SRC-014 1999 box scores from BAT-630 allowlist."""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Mapping
import re

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

SCHEMA_VERSION = "aggie.data.tamu_official_1999_boxscores.v1"
CONTRACT_RELATIVE = "configs/tamu_official_1999_boxscore_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_1999_boxscore_gate.json"
CONTRACT_ID = "BAT-631-TAMU-OFFICIAL-1999-BOXSCORES-V1"
SOURCE_ID = "SRC-014"
SEASON = 1999
OFFICIAL_1999_INDEX_URL = "https://files.12thman.com/history/football/years/1999.html"
CAPTURE_INDEX_RELATIVE = "features/tamu_official_1999_boxscores/capture_index.json"
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_1999_BOXSCORE_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_1999_BOXSCORES_NORMALIZED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
INVENTORY_IDENTITY = "d39d35ff7cfacf2e39a524d0f1fdb97072158c50f84225ed8413771140efaa37"
PINNED_BAT630_GATE_IDENTITY = (
    "53726e12b28dcb250bac1327a894f623d094a5d365ee60a2f6af965a35defc3a"
)
PINNED_BAT630_PAYLOAD_IDENTITY = (
    "7673dbf5f053dcc0b747e70c0562265e53046806e9c21d269968ae53e785edd8"
)
PINNED_BAT625_GATE_IDENTITY = (
    "38cf419510306d17c203a660051f96da9e186e275833bb763a517cf735b07546"
)
PINNED_BAT621_GATE_IDENTITY = (
    "24b3dd8e800c74885899af1c479cc9c15457eeb6d93b2ab0772825d856f68094"
)
BAT630_GATE_RELATIVE = "artifacts/data_lake/tamu_official_1999_season_index_gate.json"
BAT625_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2000_season_index_gate.json"
BAT621_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2001_season_index_gate.json"
MODULE_RELATIVE = "src/aggie_analytics/data/tamu_official_1999_boxscores.py"
CODE_BUNDLE_RELATIVE = (MODULE_RELATIVE,)
RESULT_FALLBACK_RE = re.compile(r"\b([WL])\s*,?\s*(\d+)\s*-\s*(\d+)\b", re.IGNORECASE)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


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
        json.dumps(
            mutable,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def load_source_index(repo_root: Path) -> dict[str, Any]:
    inventory_gate = load_json(repo_root / INVENTORY_GATE_RELATIVE)
    if inventory_gate.get("inventory_identity") != INVENTORY_IDENTITY:
        raise AuthorityViolation("BAT-585 inventory identity rewritten")
    gate = load_json(repo_root / BAT630_GATE_RELATIVE)
    if gate.get("gate_identity") != PINNED_BAT630_GATE_IDENTITY:
        raise AuthorityViolation("BAT-630 gate identity drifted")
    if gate.get("payload_identity") != PINNED_BAT630_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-630 payload identity rewritten")
    if gate.get("official_index_url") != OFFICIAL_1999_INDEX_URL:
        raise AuthorityViolation("guessed or substituted 1999 official URL")
    bat625 = load_json(repo_root / BAT625_GATE_RELATIVE)
    if bat625.get("gate_identity") != PINNED_BAT625_GATE_IDENTITY:
        raise AuthorityViolation("BAT-625 2000 index identity rewritten")
    bat621 = load_json(repo_root / BAT621_GATE_RELATIVE)
    if bat621.get("gate_identity") != PINNED_BAT621_GATE_IDENTITY:
        raise AuthorityViolation("BAT-621 2001 index identity rewritten")
    urls = [validate_official_url(str(url)) for url in (gate.get("box_score_urls") or [])]
    if not urls:
        raise AuthorityViolation("BAT-630 allowlist emitted no official 1999 box URLs")
    game_rows = list(gate.get("game_rows") or [])
    return {
        "gate": gate,
        "inventory_gate": inventory_gate,
        "season": SEASON,
        "official_index_url": OFFICIAL_1999_INDEX_URL,
        "box_score_urls": urls,
        "game_rows": game_rows,
    }


def selected_targets(source: Mapping[str, Any]) -> list[dict[str, Any]]:
    parent = validate_official_url(str(source["official_index_url"]))
    return [
        {
            "season": SEASON,
            "official_index_url": parent,
            "box_url": validate_official_url(str(url)),
        }
        for url in source["box_score_urls"]
    ]


def load_capture_index(data_root: Path) -> dict[str, Any]:
    path = data_root / CAPTURE_INDEX_RELATIVE
    if not path.is_file():
        return {"captures": []}
    return load_json(path)


def capture_map(index: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["url"]: item for item in index.get("captures") or []}


def compact_official_1999_capture(record: Mapping[str, Any], *, source_order: int) -> dict[str, Any]:
    compact = compact_capture(record)
    response_sha256 = str(record.get("response_sha256") or compact.get("response_sha256") or "")
    raw_sha256 = str(compact.get("raw_sha256") or "")
    if not response_sha256:
        raise AuthorityViolation(f"response SHA missing for {compact.get('url')}")
    if not raw_sha256:
        raise AuthorityViolation(f"stored file SHA missing for {compact.get('url')}")
    if response_sha256 != raw_sha256:
        raise AuthorityViolation(f"response SHA and stored file SHA disagree: {compact.get('url')}")
    if not compact.get("parent_url"):
        raise AuthorityViolation(f"parent_url missing for {compact.get('url')}")
    compact["response_sha256"] = response_sha256
    compact["source_order"] = int(source_order)
    return compact


def acquire_missing(
    *,
    data_root: Path,
    targets: list[Mapping[str, Any]],
    existing: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    order_by_url = {item["box_url"]: index for index, item in enumerate(targets, start=1)}
    allowed = frozenset(order_by_url)
    extra = sorted(set(existing) - allowed)
    if extra:
        raise AuthorityViolation(f"invented or non-allowlisted capture URL: {extra}")
    captures: list[dict[str, Any]] = []
    for target in targets:
        url = target["box_url"]
        source_order = order_by_url[url]
        if url in existing:
            record = dict(existing[url])
            record["source_order"] = source_order
            captures.append(record)
            continue
        fetched = direct_http_get(url)
        body = fetched.pop("body")
        fetched["parent_url"] = target["official_index_url"]
        fetched["page_family"] = "box_scores"
        fetched["source_season"] = target["season"]
        fetched["rights_disposition"] = "PRIVATE_RESEARCH_METADATA_ONLY_NONBLOCKING"
        try:
            fetched["parser_disposition"] = classify_capture(
                url, body, fetched.get("content_type"), int(fetched["status"])
            )
        except AuthorityViolation as exc:
            fetched["parser_disposition"] = f"REJECTED:{exc}"
        stored = persist_capture(data_root, fetched, body)
        captures.append(compact_official_1999_capture(stored, source_order=source_order))
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
        result = INDEX_RESULT_RE.search(result_raw)
        if result is None:
            result = RESULT_FALLBACK_RE.search(result_raw)
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
                "venue_state": (
                    "NEUTRAL"
                    if "vs." in str(row.get("source_opponent") or "").lower()
                    else "HOME"
                    if "college station" in str(row.get("source_location") or "").lower()
                    else "AWAY"
                ),
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
    selected_seasons = [SEASON]
    index = load_capture_index(data_root)
    captures_by_url = capture_map(index)
    if sorted(set(captures_by_url) - allowed):
        raise AuthorityViolation("capture index contains non-allowlisted URLs")
    if any(item["box_url"] not in captures_by_url for item in targets):
        raise AuthorityViolation("capture index is missing allowlisted box URLs")
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
        actual_file_sha = sha256_file(raw_path)
        if actual_file_sha != record.get("raw_sha256"):
            raise AuthorityViolation(f"raw box-score hash drifted: {target['box_url']}")
        if int(record.get("source_order") or 0) != source_order:
            raise AuthorityViolation(f"source order drifted for {target['box_url']}")
        if record.get("parent_url") != target["official_index_url"]:
            raise AuthorityViolation(f"parent_url substituted for {target['box_url']}")
        if record.get("url") != target["box_url"]:
            raise AuthorityViolation(f"capture URL drifted from allowlisted URL: {target['box_url']}")
        if int(record.get("response_status") or 0) != 200 or record.get("parser_disposition") != "VERIFIED_OFFICIAL_SCHOOL_PAGE":
            blocked.append({**record, "disposition": "OFFICIAL_ROUTE_ACCESS_BLOCKED_OR_REJECTED"})
            continue

        parsed = parse_official_box_page(
            raw_path.read_bytes(),
            url=target["box_url"],
            source_season=SEASON,
            raw_sha256=str(record["raw_sha256"]),
            allowed_urls=allowed,
            allow_season_header_conflict=True,
        )
        match = match_to_official_index(parsed, index_rows)
        match_statuses[str(match["canonical_game_match_status"])] += 1
        if parsed.get("season_header_conflict"):
            conflicts.append(
                {
                    "url": parsed["url"],
                    "conflict_status": "PAGE_HEADER_SEASON_VS_INDEX_SEASON",
                    "match_status": match["canonical_game_match_status"],
                    "calendar_date": parsed["calendar_date"],
                }
            )
        if match["conflict_status"] not in {None, "NONE"}:
            conflicts.append(
                {
                    "url": parsed["url"],
                    "conflict_status": match["conflict_status"],
                    "match_status": match["canonical_game_match_status"],
                    "calendar_date": parsed["calendar_date"],
                }
            )
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
        "artifact_type": "TAMU_OFFICIAL_1999_BOXSCORES",
        "contract_id": CONTRACT_ID,
        "decision_unit": "POST-TASK-SRC014-1999-OFFICIAL-ACQUISITION-001",
        "jira_key": "BAT-631",
        "source_id": SOURCE_ID,
        "inventory_identity": INVENTORY_IDENTITY,
        "selected_seasons": selected_seasons,
        "captures": [captures_by_url[item["box_url"]] for item in targets],
        "games": games,
        "normalized_rows": normalized_rows,
        "blocked_or_partial": blocked,
        "conflicts": conflicts,
        "admissions": expected_admissions()
        | {
            "inventory_identity": INVENTORY_IDENTITY,
            "gap_005": "OPEN",
            "bat_523": "IN_PROGRESS",
            "union_admission": "NOT_ADMITTED",
            "bat_630": "CONSUMED_INDEX_CAPTURE_ONLY",
            "bat_625": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_621": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        },
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "protected_lane": PROTECTED_LANE,
    }
    payload["dataset_identity"] = stable_hash(
        {"games": games, "captures": payload["captures"], "conflicts": conflicts}
    )
    payload["games_identity"] = stable_hash(games)
    payload["acquisition_identity"] = stable_hash(payload["captures"])
    counts = {
        "target_games_total": len(targets),
        "captured_pages_total": sum(1 for item in payload["captures"] if item.get("response_status") == 200),
        "verified_official_pages": sum(
            1 for item in payload["captures"] if item.get("parser_disposition") == "VERIFIED_OFFICIAL_SCHOOL_PAGE"
        ),
        "normalized_games": len(games),
        "blocked_or_partial_pages": len(blocked),
        "matched_strong_tuple": int(match_statuses.get("MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE", 0)),
        "date_conflicts": int(match_statuses.get("OFFICIAL_INDEX_DATE_CONFLICT", 0)),
        "name_only_insufficient": int(match_statuses.get("NAME_ONLY_INSUFFICIENT", 0)),
        "unmatched_strong_tuple": int(match_statuses.get("UNMATCHED_STRONG_TUPLE", 0)),
        "season_header_conflicts": sum(1 for item in conflicts if item.get("conflict_status") == "PAGE_HEADER_SEASON_VS_INDEX_SEASON"),
        "ncaa_contest_ids_created": 0,
        "games_admitted_to_union": 0,
        "pregame_availability_present": 0,
        "expected_box_urls": len(targets),
        "acquired_responses": sum(1 for item in payload["captures"] if item.get("response_status") == 200),
        "rejected_responses": len(blocked),
        "failures": len(blocked),
        "ambiguous_pages": int(match_statuses.get("OFFICIAL_INDEX_DATE_CONFLICT", 0))
        + int(match_statuses.get("NAME_ONLY_INSUFFICIENT", 0))
        + sum(1 for item in conflicts if item.get("conflict_status") == "PAGE_HEADER_SEASON_VS_INDEX_SEASON"),
    }
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_1999_BOXSCORE_GATE",
        "result": PASS_RESULT if not blocked and counts["normalized_games"] == counts["target_games_total"] else "PARTIAL_OFFICIAL_1999_BOXSCORES",
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": "POST-TASK-SRC014-1999-OFFICIAL-ACQUISITION-001",
        "jira_key": "BAT-631",
        "disposition": "NORMALIZED_CANDIDATE_ONLY_NO_UNION_MUTATION",
        "source_id": SOURCE_ID,
        "inventory_identity": INVENTORY_IDENTITY,
        "acquisition_identity": payload["acquisition_identity"],
        "dataset_identity": payload["dataset_identity"],
        "games_identity": payload["games_identity"],
        "selected_seasons": selected_seasons,
        "counts": counts,
        "admissions": payload["admissions"],
        "authority": payload["authority"],
        "scientific_nonclaims": payload["scientific_nonclaims"],
        "protected_lane": PROTECTED_LANE,
        "validator_code_identity": compute_code_identity(repo_root),
        "upstream_identities": {
            "inventory_identity": INVENTORY_IDENTITY,
            "bat630_gate_identity": PINNED_BAT630_GATE_IDENTITY,
            "bat630_payload_identity": PINNED_BAT630_PAYLOAD_IDENTITY,
            "bat625_gate_identity": PINNED_BAT625_GATE_IDENTITY,
            "bat621_gate_identity": PINNED_BAT621_GATE_IDENTITY,
            "protected_split_registry_sha256": REGISTRY_SHA256,
        },
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    return {"contract": contract, "gate": gate, "payload": payload, "selected_seasons": selected_seasons}


def materialize_boxscores(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    source = load_source_index(repo_root)
    targets = selected_targets(source)
    existing = capture_map(load_capture_index(data_root))
    captures = acquire_missing(data_root=data_root, targets=targets, existing=existing)
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
        "selected_seasons": objects["selected_seasons"],
        "normalized_games": objects["gate"]["counts"]["normalized_games"],
    }


def lake_is_ready(data_root: Path) -> bool:
    return (data_root / CAPTURE_INDEX_RELATIVE).is_file()


def validate_compact_gate(committed: Mapping[str, Any], repo_root: Path) -> None:
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("completion or classification forged")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not recompute")
    if committed.get("inventory_identity") != INVENTORY_IDENTITY:
        raise AuthorityViolation("inventory identity rebound incorrectly")
    if (committed.get("counts") or {}).get("ncaa_contest_ids_created"):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if (committed.get("counts") or {}).get("games_admitted_to_union"):
        raise AuthorityViolation("union admission occurred")
    if committed.get("selected_seasons") != [SEASON]:
        raise AuthorityViolation("selected season tampered")
    if committed.get("validator_code_identity") != compute_code_identity(repo_root):
        raise AuthorityViolation("changed code with stale code identity")
    upstream = committed.get("upstream_identities") or {}
    if upstream.get("bat630_gate_identity") != PINNED_BAT630_GATE_IDENTITY:
        raise AuthorityViolation("BAT-630 identity rewritten")
    if upstream.get("bat625_gate_identity") != PINNED_BAT625_GATE_IDENTITY:
        raise AuthorityViolation("BAT-625 identity rewritten")
    if upstream.get("bat621_gate_identity") != PINNED_BAT621_GATE_IDENTITY:
        raise AuthorityViolation("BAT-621 identity rewritten")


def validate_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    gate: Mapping[str, Any] | None = None,
    require_rebuild: bool = True,
) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    validate_compact_gate(committed, repo_root)
    ready = lake_is_ready(data_root)
    if require_rebuild and not ready:
        raise AuthorityViolation("external 1999 reconstruction was required but data root is not mounted")
    if not ready:
        return {
            "result": "PASS",
            "gate_identity": committed["gate_identity"],
            "external_reconstruction": "NOT_MOUNTED",
            "selected_seasons": committed.get("selected_seasons"),
        }
    expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    if committed != expected["gate"]:
        raise AuthorityViolation("committed 1999 box-score gate does not match independent reconstruction")
    payload_path = (
        data_root / expected["contract"]["payloads"]["normalized_root"] / expected["payload"]["dataset_identity"] / "payload.json"
    )
    if not payload_path.is_file():
        raise AuthorityViolation("external normalized payload missing")
    if load_json(payload_path) != expected["payload"]:
        raise AuthorityViolation("external normalized payload does not match reconstruction")
    return {
        "result": "PASS",
        "gate_identity": expected["gate"]["gate_identity"],
        "dataset_identity": expected["payload"]["dataset_identity"],
        "acquisition_identity": expected["payload"]["acquisition_identity"],
        "selected_seasons": expected["selected_seasons"],
        "normalized_games": expected["gate"]["counts"]["normalized_games"],
        "external_reconstruction": "MOUNTED",
    }


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]

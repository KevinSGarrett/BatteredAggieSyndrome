"""Acquire and normalize official SRC-014 2003 box scores from the independently reconstructed BAT-609 index."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urljoin

from aggie_analytics.data.ncaa_contest_reconciliation import normalize_team_name, stable_hash
from aggie_analytics.data.tamu_official_2003_season_index import (
    lake_is_ready as official_2003_index_is_ready,
    reconstruct as reconstruct_official_2003_index,
)
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
    CELL_RE,
    DOMAINS,
    INDEX_RESULT_RE,
    ROW_RE,
    TABLE_RE,
    clean_text,
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
    HISTORY_INDEX_SHA256,
    REGISTRY_SHA256,
    UNION_GATE_IDENTITY,
    UNION_IDENTITY,
)
from aggie_analytics.data.tamu_official_rich_structure import (
    classify_games,
)


SCHEMA_VERSION = "aggie.data.tamu_official_2003_boxscores.v1"
CONTRACT_RELATIVE = "configs/tamu_official_2003_boxscore_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_2003_boxscore_gate.json"
CONTRACT_ID = "BAT-610-TAMU-OFFICIAL-2003-BOXSCORES-V1"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_2003_BOXSCORE_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_2003_BOXSCORES_NORMALIZED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
CAPTURE_INDEX_RELATIVE = "features/tamu_official_2003_boxscores/capture_index.json"
INVENTORY_IDENTITY = "d39d35ff7cfacf2e39a524d0f1fdb97072158c50f84225ed8413771140efaa37"
INVENTORY_GATE_IDENTITY = "f1a5821ad081dce7058848ccc453344f0a2827030959049133b69db15689c851"
BOXSCORE_GATE_IDENTITY = "29e76b1e264387b2195e2fd4c1d04bbb375d448789b4ac64aec701a61eceb1e5"
ANCHOR_RE = re.compile(r'(?is)<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>')
GATE_IDENTITY_FIELDS = (
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
    "acquisition_identity",
    "dataset_identity",
    "games_identity",
    "selected_seasons",
    "counts",
    "domain_coverage",
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
    mutable = {key: value for key, value in gate.items() if key != "gate_identity"}
    return hashlib.sha256(
        json.dumps(mutable, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    ).hexdigest()


BAT604_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2004_season_index_gate.json"
BAT600_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2005_boxscore_gate.json"
BAT599_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2005_season_index_gate.json"
BAT594_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2006_season_index_gate.json"
BAT595_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2006_boxscore_gate.json"
PINNED_BAT594_GATE_IDENTITY = "d1f765a73abf0107fcf200562590bfd0212a521df47f9c6b27bb336ad737635c"
PINNED_BAT594_CAPTURE_IDENTITY = "c4a13a9b96b6b885732b32e7a9d2dc95321c89b604a3b90d69e342316c240aa2"
PINNED_BAT594_BOX_URL_IDENTITY = "57ee217fa34eeb041681ad9552933c4da505ab448ab43cac95bbf73ad6b4bf07"
PINNED_BAT595_GATE_IDENTITY = "2a9c56a10b14cf5fec4dff1c3cd55d0b4440afdb9520fb308317a9ae59c47ed7"
PINNED_BAT599_PAYLOAD_IDENTITY = "71b57040514f4d61f89809fc7bd15270b993ddcd4728ba981c6f1cbdfac015cb"
PINNED_BAT604_GATE_IDENTITY = "3169f6b14e9f2e78e5af2c3dfa33419d80b37c791968fa39e0ddcf91f3643836"
PINNED_BAT604_CAPTURE_IDENTITY = "5a0d8d549c98405a22f891421df7b4513a81132572695da7bdfeb11234f48830"
PINNED_BAT604_BOX_URL_IDENTITY = "9bda3096e9715f574d235b9e2bf96c84e52784695dd3cfea35943f2663a01e84"
PINNED_BAT604_PAYLOAD_IDENTITY = "65b6c83d9946eadc3db5fede73bed7e64b620406ca5655ad93d75346dcbe6422"
PINNED_BAT600_GATE_IDENTITY = "c999af29522096e4ae3a9cdc558679321095c8cf11247ef1ccd23b3114ee18cc"
BAT589_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2007_boxscore_gate.json"
BAT586_GATE_RELATIVE = "artifacts/data_lake/tamu_official_pre2010_boxscore_gate.json"
PINNED_BAT599_GATE_IDENTITY = "17868efadbc5cc6ec04869d194b8b8a205089c3050b069eec3e5ba9c1d25c301"
PINNED_BAT599_CAPTURE_IDENTITY = "18d1e502de0032bc4c0e1e3d36aed0c3814c4612e68201dcf7675ca5c39c899a"
PINNED_BAT599_BOX_URL_IDENTITY = "7564d90c3ada13353b8242fd8891642778abd99c32e1f31fa8f2c389a495544d"
PINNED_BAT589_GATE_IDENTITY = "f2080b0ebb7815892732b2e600917e00da972edca0379888fa0010ff6bf17e51"
PINNED_BAT586_GATE_IDENTITY = "c62a09d2b3bcf7e69c6b6ea90993084d124a779d7ab779e8ebeab300b2a9c006"
BAT609_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2003_season_index_gate.json"
BAT605_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2004_boxscore_gate.json"
PINNED_BAT609_GATE_IDENTITY = "1a2b16c74bcfc27ba0afc83611fd817d34aa6a2a71a326fd385721b779d9411e"
PINNED_BAT609_CAPTURE_IDENTITY = "253a1065192f2e4aa1fa366d967b5c37c0c9586d9b664a3bf0f16079c5105921"
PINNED_BAT609_BOX_URL_IDENTITY = "169ecef65490a5a07889ccd06816fda94db5215e6f1eacf6cb22204286800a99"
PINNED_BAT609_PAYLOAD_IDENTITY = "9f58c220fe44e8c75835d0dced6dc6571ee7592249eaa6fa209fa181f25fdfa6"
PINNED_BAT609_RAW_SHA256 = "b4f48fa72d7658643a3ad44f4cedcdd2e080986b7a7be88bcac3e12c0cdf4e5a"
PINNED_BAT605_GATE_IDENTITY = "c570a33661bf194475693f56b2d21baf9a38e67c5ae568f5a531e374356b5c70"
OFFICIAL_2003_INDEX_URL = "https://files.12thman.com/history/football/years/2003.html"
SEASON = 2003


def load_source_index(repo_root: Path, data_root: Path) -> dict[str, Any]:
    inventory_gate = load_json(repo_root / INVENTORY_GATE_RELATIVE)
    if inventory_gate.get("inventory_identity") != INVENTORY_IDENTITY or inventory_gate.get("gate_identity") != INVENTORY_GATE_IDENTITY:
        raise AuthorityViolation("BAT-585 inventory identity rewritten")
    committed = load_json(repo_root / BAT609_GATE_RELATIVE)
    if committed.get("gate_identity") != PINNED_BAT609_GATE_IDENTITY:
        raise AuthorityViolation("BAT-609 gate identity drifted")
    if committed.get("inventory_identity") != INVENTORY_IDENTITY:
        raise AuthorityViolation("BAT-585 inventory identity rewritten")
    if committed.get("official_index_url") != OFFICIAL_2003_INDEX_URL:
        raise AuthorityViolation("guessed or substituted 2003 official URL")
    if committed.get("payload_identity") != PINNED_BAT609_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-609 payload identity rewritten")
    if committed.get("capture_identity") != PINNED_BAT609_CAPTURE_IDENTITY:
        raise AuthorityViolation("BAT-609 capture identity rewritten")
    if committed.get("box_url_identity") != PINNED_BAT609_BOX_URL_IDENTITY:
        raise AuthorityViolation("BAT-609 box-URL identity rewritten")
    if (committed.get("capture") or {}).get("raw_sha256") != PINNED_BAT609_RAW_SHA256:
        raise AuthorityViolation("BAT-609 season-index raw hash drifted")
    bat605 = load_json(repo_root / BAT605_GATE_RELATIVE)
    if bat605.get("gate_identity") != PINNED_BAT605_GATE_IDENTITY:
        raise AuthorityViolation("BAT-605 2004 acquisition identity rewritten")
    bat604 = load_json(repo_root / BAT604_GATE_RELATIVE)
    if bat604.get("gate_identity") != PINNED_BAT604_GATE_IDENTITY:
        raise AuthorityViolation("BAT-604 2004 index identity rewritten")
    if bat604.get("payload_identity") != PINNED_BAT604_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-604 2004 payload identity rewritten")
    bat600 = load_json(repo_root / BAT600_GATE_RELATIVE)
    if bat600.get("gate_identity") != PINNED_BAT600_GATE_IDENTITY:
        raise AuthorityViolation("BAT-600 2005 acquisition identity rewritten")
    bat599 = load_json(repo_root / BAT599_GATE_RELATIVE)
    if bat599.get("gate_identity") != PINNED_BAT599_GATE_IDENTITY:
        raise AuthorityViolation("BAT-599 2005 index identity rewritten")
    bat594 = load_json(repo_root / BAT594_GATE_RELATIVE)
    if bat594.get("gate_identity") != PINNED_BAT594_GATE_IDENTITY:
        raise AuthorityViolation("BAT-594 2006 index identity rewritten")
    bat595 = load_json(repo_root / BAT595_GATE_RELATIVE)
    if bat595.get("gate_identity") != PINNED_BAT595_GATE_IDENTITY:
        raise AuthorityViolation("BAT-595 2006 acquisition identity rewritten")
    bat589 = load_json(repo_root / BAT589_GATE_RELATIVE)
    if bat589.get("gate_identity") != PINNED_BAT589_GATE_IDENTITY:
        raise AuthorityViolation("BAT-589 2007 acquisition identity rewritten")
    bat586 = load_json(repo_root / BAT586_GATE_RELATIVE)
    if bat586.get("gate_identity") != PINNED_BAT586_GATE_IDENTITY:
        raise AuthorityViolation("BAT-586 2008/2009 acquisition identity rewritten")
    gate = committed
    if official_2003_index_is_ready(data_root, repo_root):
        reconstructed = reconstruct_official_2003_index(repo_root=repo_root, data_root=data_root)
        if reconstructed["gate"] != committed:
            raise AuthorityViolation("BAT-609 committed gate does not match independent reconstruction")
        gate = reconstructed["gate"]
    urls = [validate_official_url(str(url)) for url in (gate.get("box_score_urls") or [])]
    if not urls:
        raise AuthorityViolation("BAT-609 reconstruction emitted no official 2003 box URLs")
    capture = gate.get("capture") or {}
    return {
        "gate": gate,
        "inventory_gate": inventory_gate,
        "season": SEASON,
        "official_index_url": OFFICIAL_2003_INDEX_URL,
        "box_score_urls": urls,
        "season_index_raw_sha256": capture.get("raw_sha256"),
        "season_index_raw_relative_path": capture.get("raw_relative_path"),
    }


def selected_targets(source: Mapping[str, Any]) -> list[dict[str, Any]]:
    parent = validate_official_url(str(source["official_index_url"]))
    return [
        {"season": SEASON, "official_index_url": parent, "box_url": validate_official_url(str(url))}
        for url in source["box_score_urls"]
    ]

def parse_allowlisted_season_index(body: bytes, season: int, parent_url: str, allowed: frozenset[str]) -> list[dict[str, Any]]:
    text = body.decode("latin-1", errors="replace")
    rows: list[dict[str, Any]] = []
    for table in TABLE_RE.findall(text):
        parsed_rows = ROW_RE.findall(table)
        if not parsed_rows:
            continue
        headers = [re.sub(r"[^a-z0-9]+", "_", clean_text(cell).lower()).strip("_") for cell in CELL_RE.findall(parsed_rows[0])]
        if "opponent" not in headers or "box_score" not in headers:
            continue
        for raw_row in parsed_rows[1:]:
            cells = [clean_text(cell) for cell in CELL_RE.findall(raw_row)]
            if len(cells) < 4:
                continue
            record = {headers[index] if index < len(headers) else f"col_{index}": cells[index] for index in range(len(cells))}
            box_url = None
            for href, label in ANCHOR_RE.findall(raw_row):
                if clean_text(label).casefold() != "box score":
                    continue
                candidate = validate_official_url(urljoin(parent_url, href.split("#", 1)[0]))
                if candidate in allowed:
                    box_url = candidate
                    break
            if box_url is None:
                continue
            result = INDEX_RESULT_RE.search(record.get("result") or "")
            if result is None:
                raise AuthorityViolation(f"season index row missing W/L/score: {record}")
            opponent = opponent_candidate(record.get("opponent") or "")
            location = record.get("location") or ""
            rows.append(
                {
                    "source_season": season,
                    "raw_date": record.get("date") or "",
                    "index_date_candidate": reconstruct_index_date(record.get("date") or "", season),
                    "opponent_raw": record.get("opponent") or "",
                    "opponent_candidate": opponent,
                    "opponent_normalized": normalize_team_name(opponent),
                    "location_raw": location,
                    "site_token": site_token(location),
                    "result_raw": record.get("result") or "",
                    "tamu_points": int(result.group(2)),
                    "opponent_points": int(result.group(3)),
                    "box_url": box_url,
                    "venue_state": (
                        "NEUTRAL"
                        if "vs." in (record.get("opponent") or "").lower()
                        else "HOME"
                        if "college station" in location.lower()
                        else "AWAY"
                    ),
                    "schedule_sequence": len(rows) + 1,
                }
            )
    found = {row["box_url"] for row in rows}
    missing = sorted(allowed - found)
    if missing:
        raise AuthorityViolation(f"official season index omitted allowlisted box URLs: {missing}")
    extra = sorted(found - allowed)
    if extra:
        raise AuthorityViolation(f"official season index emitted non-inventory box URLs: {extra}")
    return rows


def load_capture_index(data_root: Path) -> dict[str, Any]:
    path = data_root / CAPTURE_INDEX_RELATIVE
    if not path.is_file():
        return {"captures": []}
    return load_json(path)


def capture_map(index: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["url"]: item for item in index.get("captures") or []}


def acquire_missing(
    *,
    data_root: Path,
    targets: list[Mapping[str, Any]],
    existing: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    captures = [dict(item) for item in existing.values()]
    known = set(existing)
    for target in targets:
        url = target["box_url"]
        if url in known:
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
        captures.append(compact_capture(stored))
        known.add(url)
    return sorted(captures, key=lambda item: (int(item["source_season"]), item["url"]), reverse=True)


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    source = load_source_index(repo_root, data_root)
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    targets = selected_targets(source)
    allowed = frozenset(item["box_url"] for item in targets)
    selected_seasons = []
    seen_seasons: list[int] = []
    for item in targets:
        if item["season"] not in seen_seasons:
            seen_seasons.append(item["season"])
            selected_seasons.append(item["season"])
    index = load_capture_index(data_root)
    captures = capture_map(index)
    if any(item["box_url"] not in captures for item in targets):
        raise AuthorityViolation("capture index is missing one or more inventory box-score URLs")
    season_index_by_year: dict[int, dict[str, Any]] = {}
    for row in [{"season": source["season"], "official_index_url": source["official_index_url"], "season_index_raw_sha256": source["season_index_raw_sha256"], "season_index_raw_relative_path": source["season_index_raw_relative_path"]}]:
        season = int(row["season"])
        digest = row.get("season_index_raw_sha256")
        if not digest:
            raise AuthorityViolation(f"inventory is missing captured season-index hash for {season}")
        raw_rel = (
            row.get("season_index_raw_relative_path")
            or f"raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive/season_index/sha256_{digest}.html"
        )
        season_index_by_year[season] = {
            "url": row["official_index_url"],
            "path": data_root / raw_rel,
            "sha256": digest,
        }
    index_rows: list[dict[str, Any]] = []
    for season in selected_seasons:
        meta = season_index_by_year[season]
        if not meta["path"].is_file():
            raise AuthorityViolation(f"captured official season index missing: {season}")
        if sha256_file(meta["path"]) != meta["sha256"]:
            raise AuthorityViolation(f"season index hash drifted: {season}")
        allowed_for_season = frozenset(item["box_url"] for item in targets if item["season"] == season)
        index_rows.extend(parse_allowlisted_season_index(meta["path"].read_bytes(), season, meta["url"], allowed_for_season))
    games: list[dict[str, Any]] = []
    normalized_rows: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    match_statuses: Counter[str] = Counter()
    conflicts: list[dict[str, Any]] = []
    coverage_counts = Counter({domain: 0 for domain in DOMAINS})
    for target in targets:
        record = captures[target["box_url"]]
        raw_path = data_root / record["raw_relative_path"]
        if not raw_path.is_file():
            blocked.append({**record, "disposition": "RAW_FILE_MISSING"})
            continue
        if sha256_file(raw_path) != record["raw_sha256"]:
            raise AuthorityViolation(f"raw box-score hash drifted: {target['box_url']}")
        if not record.get("parent_url"):
            raise AuthorityViolation(f"parent_url missing for {target['box_url']}")
        if record.get("parent_url") != target["official_index_url"]:
            raise AuthorityViolation(f"parent_url substituted for {target['box_url']}")
        if record.get("url") != target["box_url"]:
            raise AuthorityViolation(f"capture URL drifted from allowlisted box URL: {target['box_url']}")
        if int(record.get("source_season") or 0) != SEASON:
            raise AuthorityViolation(f"capture season drifted: {target['box_url']}")
        if record.get("historical_publication_time") is not None:
            raise AuthorityViolation("current retrieval timestamp used as historical publication time")
        if int(record.get("response_status") or 0) != 200 or record.get("parser_disposition") != "VERIFIED_OFFICIAL_SCHOOL_PAGE":
            blocked.append({**record, "disposition": "OFFICIAL_ROUTE_ACCESS_BLOCKED_OR_REJECTED"})
            continue
        parsed = parse_official_box_page(
            raw_path.read_bytes(),
            url=target["box_url"],
            source_season=target["season"],
            raw_sha256=record["raw_sha256"],
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
                    "page_header_season": parsed.get("page_header_season"),
                    "source_season": parsed["source_season"],
                    "opponent_candidate": parsed["opponent_candidate"],
                }
            )
        if match["conflict_status"] not in {None, "NONE"}:
            conflicts.append(
                {
                    "url": parsed["url"],
                    "conflict_status": match["conflict_status"],
                    "match_status": match["canonical_game_match_status"],
                    "calendar_date": parsed["calendar_date"],
                    "index_date_candidate": match.get("index_date_candidate"),
                    "opponent_candidate": parsed["opponent_candidate"],
                }
            )
        compact = compact_game(parsed, match)
        compact["parent_url"] = target["official_index_url"]
        compact["response_status"] = record.get("response_status")
        compact["raw_relative_path"] = record.get("raw_relative_path")
        games.append(compact)
        for domain, flag in parsed["domain_coverage"].items():
            if flag == "PRESENT":
                coverage_counts[domain] += 1
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
    games = sorted(games, key=lambda item: (item["football_season"], item["calendar_date"], item["url"]))
    season_counts = Counter(int(item["football_season"]) for item in games)
    richness = classify_games(games)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_2003_BOXSCORES",
        "contract_id": CONTRACT_ID,
        "decision_unit": "POST-TASK-SRC014-2003-OFFICIAL-ACQUISITION-001",
        "jira_key": "BAT-610",
        "source_id": SOURCE_ID,
        "inventory_identity": INVENTORY_IDENTITY,
        "selected_seasons": selected_seasons,
        "captures": [captures[item["box_url"]] for item in targets],
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
            "bat_609": "CONSUMED_INDEX_CAPTURE_ONLY",
            "bat_605": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_604": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_600": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_599": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        },
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
        "season_header_conflicts": sum(1 for game in games if game.get("url") and any(
            item.get("url") == game.get("url") and item.get("conflict_status") == "PAGE_HEADER_SEASON_VS_INDEX_SEASON"
            for item in conflicts
        )),
        "rich_structured_games": richness["rich_structured_games"],
        "metadata_only_games": richness["metadata_only_games"],
        "scoring_summary_present_games": richness["scoring_summary_present_games"],
        "ncaa_contest_ids_created": 0,
        "games_admitted_to_union": 0,
        "player_stat_candidates": sum(len(row["player_stat_candidates"]) for row in normalized_rows),
        "participation_candidates": sum(len(row["participation"]) for row in normalized_rows),
        "pregame_availability_present": 0,
    }
    counts["expected_box_urls"] = counts["target_games_total"]
    counts["acquired_responses"] = counts["captured_pages_total"]
    counts["rejected_responses"] = counts["blocked_or_partial_pages"]
    counts["failures"] = counts["blocked_or_partial_pages"]
    counts["ambiguous_pages"] = (
        counts["date_conflicts"] + counts["name_only_insufficient"] + counts["season_header_conflicts"]
    )
    for season in selected_seasons:
        counts[f"target_games_{season}"] = sum(1 for item in targets if item["season"] == season)
        counts[f"normalized_games_{season}"] = int(season_counts.get(season, 0))
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_2003_BOXSCORE_GATE",
        "result": PASS_RESULT if not blocked and counts["normalized_games"] == counts["target_games_total"] else "PARTIAL_OFFICIAL_2003_BOXSCORES",
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": "POST-TASK-SRC014-2003-OFFICIAL-ACQUISITION-001",
        "jira_key": "BAT-610",
        "disposition": "NORMALIZED_CANDIDATE_ONLY_NO_UNION_MUTATION",
        "source_id": SOURCE_ID,
        "inventory_identity": INVENTORY_IDENTITY,
        "acquisition_identity": payload["acquisition_identity"],
        "dataset_identity": payload["dataset_identity"],
        "games_identity": payload["games_identity"],
        "selected_seasons": selected_seasons,
        "counts": counts,
        "domain_coverage": {
            domain: {"present_games": int(coverage_counts[domain]), "absent_games": len(games) - int(coverage_counts[domain])}
            for domain in DOMAINS
        },
        "admissions": payload["admissions"],
        "authority": payload["authority"],
        "scientific_nonclaims": payload["scientific_nonclaims"],
        "protected_lane": PROTECTED_LANE,
        "upstream_identities": {
            "inventory_identity": INVENTORY_IDENTITY,
            "inventory_gate_identity": INVENTORY_GATE_IDENTITY,
            "history_index_sha256": HISTORY_INDEX_SHA256,
            "cycle9_boxscore_gate_identity": BOXSCORE_GATE_IDENTITY,
            "bat609_gate_identity": PINNED_BAT609_GATE_IDENTITY,
            "bat609_capture_identity": PINNED_BAT609_CAPTURE_IDENTITY,
            "bat609_box_url_identity": PINNED_BAT609_BOX_URL_IDENTITY,
            "bat609_payload_identity": PINNED_BAT609_PAYLOAD_IDENTITY,
            "bat605_gate_identity": PINNED_BAT605_GATE_IDENTITY,
            "bat604_gate_identity": PINNED_BAT604_GATE_IDENTITY,
            "bat604_capture_identity": PINNED_BAT604_CAPTURE_IDENTITY,
            "bat604_box_url_identity": PINNED_BAT604_BOX_URL_IDENTITY,
            "bat604_payload_identity": PINNED_BAT604_PAYLOAD_IDENTITY,
            "bat600_gate_identity": PINNED_BAT600_GATE_IDENTITY,
            "bat599_gate_identity": PINNED_BAT599_GATE_IDENTITY,
            "bat599_capture_identity": PINNED_BAT599_CAPTURE_IDENTITY,
            "bat599_box_url_identity": PINNED_BAT599_BOX_URL_IDENTITY,
            "bat594_gate_identity": PINNED_BAT594_GATE_IDENTITY,
            "bat594_capture_identity": PINNED_BAT594_CAPTURE_IDENTITY,
            "bat594_box_url_identity": PINNED_BAT594_BOX_URL_IDENTITY,
            "bat595_gate_identity": PINNED_BAT595_GATE_IDENTITY,
            "bat599_payload_identity": PINNED_BAT599_PAYLOAD_IDENTITY,
            "bat589_gate_identity": PINNED_BAT589_GATE_IDENTITY,
            "bat586_gate_identity": PINNED_BAT586_GATE_IDENTITY,
            "union_gate_identity": UNION_GATE_IDENTITY,
            "union_identity": UNION_IDENTITY,
            "protected_split_registry_sha256": REGISTRY_SHA256,
        },
    }
    if counts["ncaa_contest_ids_created"] or gate["authority"]["ncaa_contest_identity"]:
        raise AuthorityViolation("NCAA contest IDs fabricated")
    gate["gate_identity"] = compute_gate_identity(gate)
    return {
        "contract": contract,
        "gate": gate,
        "payload": payload,
        "captures": payload["captures"],
        "selected_seasons": selected_seasons,
    }


def materialize_boxscores(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    source = load_source_index(repo_root, data_root)
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


def validate_compact_gate(committed: Mapping[str, Any]) -> None:
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("authority", {}).get("historical_known_at_from_capture_time"):
        raise AuthorityViolation("retrieval time promoted to historical known-at")
    if committed.get("counts", {}).get("ncaa_contest_ids_created"):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if committed.get("result") not in {PASS_RESULT, "PARTIAL_OFFICIAL_2003_BOXSCORES"}:
        raise AuthorityViolation("completion or classification forged")
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("completion or classification forged")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not recompute")
    if committed.get("inventory_identity") != INVENTORY_IDENTITY:
        raise AuthorityViolation("inventory identity rebound incorrectly")
    if committed.get("authority", {}).get("availability_claim") or committed.get("authority", {}).get(
        "participation_as_availability"
    ):
        raise AuthorityViolation("participation or membership promoted to availability")
    if (committed.get("counts") or {}).get("pregame_availability_present"):
        raise AuthorityViolation("pregame availability claimed")
    if committed.get("selected_seasons") != [SEASON]:
        raise AuthorityViolation("selected season tampered")
    if (committed.get("upstream_identities") or {}).get("bat589_gate_identity") != PINNED_BAT589_GATE_IDENTITY:
        raise AuthorityViolation("BAT-589 2007 acquisition identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat586_gate_identity") != PINNED_BAT586_GATE_IDENTITY:
        raise AuthorityViolation("BAT-586 2008/2009 acquisition identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat609_gate_identity") != PINNED_BAT609_GATE_IDENTITY:
        raise AuthorityViolation("BAT-609 2003 index identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat605_gate_identity") != PINNED_BAT605_GATE_IDENTITY:
        raise AuthorityViolation("BAT-605 2004 acquisition identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat604_gate_identity") != PINNED_BAT604_GATE_IDENTITY:
        raise AuthorityViolation("BAT-604 2004 index identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat600_gate_identity") != PINNED_BAT600_GATE_IDENTITY:
        raise AuthorityViolation("BAT-600 2005 acquisition identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat599_gate_identity") != PINNED_BAT599_GATE_IDENTITY:
        raise AuthorityViolation("BAT-599 2005 index identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat595_gate_identity") != PINNED_BAT595_GATE_IDENTITY:
        raise AuthorityViolation("BAT-595 2006 acquisition identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat594_gate_identity") != PINNED_BAT594_GATE_IDENTITY:
        raise AuthorityViolation("BAT-594 2006 index identity rewritten")


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
        raise AuthorityViolation("external 2003 box-score reconstruction was required but the data root is not mounted")
    if not ready:
        return {
            "result": "PASS",
            "gate_identity": committed["gate_identity"],
            "external_reconstruction": "NOT_MOUNTED",
            "selected_seasons": committed.get("selected_seasons"),
        }
    expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    if committed != expected["gate"]:
        raise AuthorityViolation("committed 2003 box-score gate does not match independent reconstruction")
    payload_path = (
        data_root
        / expected["contract"]["payloads"]["normalized_root"]
        / expected["payload"]["dataset_identity"]
        / "payload.json"
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

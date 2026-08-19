"""Official SRC-014 historical coverage inventory and next pre-2010 season selection."""

from __future__ import annotations

import html
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urljoin, urlsplit

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash
from aggie_analytics.data.tamu_official_gamebook_union import (
    GATE_RELATIVE as UNION_GATE_RELATIVE,
    load_wmt_compact_games,
)
from aggie_analytics.data.tamu_official_historical_archive import (
    ANCHOR_RE,
    CELL_RE,
    OFFICIAL_HOSTS,
    RAW_ROOT as ARCHIVE_RAW_ROOT,
    ROW_RE,
    TABLE_RE,
    classify_capture,
    compact_capture,
    direct_http_get,
    persist_capture,
    sha256_bytes,
    sha256_file,
    validate_official_url,
)


SCHEMA_VERSION = "aggie.data.tamu_official_historical_coverage_inventory.v1"
CONTRACT_RELATIVE = "configs/tamu_official_historical_coverage_inventory_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_historical_coverage_inventory_gate.json"
EVIDENCE_RELATIVE = "artifacts/jira_evidence/POST-TASK-CYCLE-10-SRC014-HISTORICAL-COVERAGE-INVENTORY-001.json"
UNION_CONTRACT_RELATIVE = "configs/tamu_official_gamebook_union_contract.json"
ARCHIVE_GATE_RELATIVE = "artifacts/data_lake/tamu_official_historical_archive_gate.json"
BOXSCORE_GATE_RELATIVE = "artifacts/data_lake/tamu_official_historical_boxscore_gate.json"
CONTRACT_ID = "BAT-585-TAMU-OFFICIAL-HISTORICAL-COVERAGE-INVENTORY-V1"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_HISTORICAL_COVERAGE_INVENTORY_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_INDEX_INVENTORY_TWO_PRE2010_SEASONS_SELECTED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
CAPTURE_INDEX_RELATIVE = "features/tamu_official_historical_coverage_inventory/season_index_capture_index.json"
HISTORY_INDEX_URL = "https://files.12thman.com/history/football/history/index.html"
HISTORY_INDEX_SHA256 = "1d3b44c95af913e94548a22e7eeef930fb485a472de362ca1f9c137fb759a17a"
UNION_GATE_IDENTITY = "dd0d0f32c499b4863551a9ab6649cbef7638c3916228661262fbd5a71909c106"
UNION_IDENTITY = "050fb22e733f3dc296a5bafed9f89a20281efb06860dc220264d074a7e9b7672"
REGISTRY_SHA256 = "6b90ef6fb09abd89d7a82a8b5835b00615671a7742839269c7401a2d0af5f764"
YEAR_RE = re.compile(r"^(18|19|20)\d{2}$")
HREF_YEAR_RE = re.compile(r"(?:18|19|20)\d{2}")
BOX_LABEL_RE = re.compile(r"^box\s*score$", re.IGNORECASE)
RESULTS_LABEL_RE = re.compile(r"^results$", re.IGNORECASE)
ROSTER_LABEL_RE = re.compile(r"^roster$", re.IGNORECASE)
TEAM_STAT_NAME_RE = re.compile(r"^(teamcume|teamgbg)\.html?$", re.IGNORECASE)
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
    "history_index_sha256",
    "selected_seasons",
    "rejected_seasons",
    "counts",
    "upstream_identities",
    "admissions",
    "authority",
    "scientific_nonclaims",
    "protected_lane",
)


class AuthorityViolation(ValueError):
    """Raised when official historical inventory evidence would invent a season, URL, or claim."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def fragment_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", value))).strip()


def official_host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def expected_authority() -> dict[str, bool]:
    return {
        "completeness_claim": False,
        "contest_id_fabrication": False,
        "guessed_season_url": False,
        "ncaa_contest_identity": False,
        "historical_known_at_from_capture_time": False,
        "historical_pit_admission": False,
        "availability_claim": False,
        "membership_as_availability": False,
        "participation_as_availability": False,
        "champion_or_production_promotion": False,
        "protected_outcome_authority": False,
        "tamu_specialization_lift_claims": False,
        "bas_or_aggie_excess_claims": False,
        "wmt_payload_mutated_in_place": False,
    }


def expected_scientific_nonclaims() -> dict[str, bool]:
    return {
        "completeness_claimed": False,
        "historical_known_at_established": False,
        "historical_population_ready": False,
        "pregame_availability_admitted": False,
        "ncaa_contest_ids_created": False,
        "protected_lane_opened": False,
        "champion_or_production_promotion": False,
        "guessed_year_urls": False,
        "numeric_ncaa_contest_id_sweep": False,
        "retrieval_time_used_as_historical_known_at": False,
    }


def expected_admissions() -> dict[str, str]:
    return {
        "inventory_admission": "CANDIDATE_ONLY",
        "source_authority": "SRC-014_OFFICIAL_SCHOOL_EVIDENCE",
        "ncaa_contest_identity": "NOT_CREATED",
        "historical_known_at": "UNKNOWN_CAPTURE_TIME_ONLY",
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "bat_523": "IN_PROGRESS",
        "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
        "bat_401": "DONE_VERIFIED_RETAIN_PROTECTED_LANE_BLOCKED",
        "gap_005": "OPEN",
        "wmt_payload": "PRESERVED_IMMUTABLE",
    }


def resolve_official_href(parent_url: str, href: str) -> str:
    candidate = urljoin(parent_url, href.split("#", 1)[0].strip())
    return validate_official_url(candidate)


def parse_history_index_seasons(body: bytes, discovery_source_url: str) -> list[dict[str, Any]]:
    text = body.decode("latin-1", errors="replace")
    seasons: list[dict[str, Any]] = []
    seen: set[int] = set()
    for table in TABLE_RE.findall(text):
        for raw_row in ROW_RE.findall(table):
            cells = [fragment_text(cell) for cell in CELL_RE.findall(raw_row)]
            if not cells:
                continue
            year_token = next((cell for cell in cells if YEAR_RE.match(cell)), None)
            if year_token is None:
                continue
            season = int(year_token)
            hrefs = [(href, fragment_text(label)) for href, label in ANCHOR_RE.findall(raw_row)]
            results = [item for item in hrefs if RESULTS_LABEL_RE.match(item[1])]
            rosters = [item for item in hrefs if ROSTER_LABEL_RE.match(item[1])]
            if not results:
                continue
            if len(results) != 1:
                raise AuthorityViolation(f"season {season} emitted {len(results)} Results links")
            official_index_url = resolve_official_href(discovery_source_url, results[0][0])
            href_years = {int(item) for item in HREF_YEAR_RE.findall(urlsplit(official_index_url).path)}
            if href_years and season not in href_years:
                raise AuthorityViolation(
                    f"row year {season} does not match official Results URL {official_index_url}"
                )
            roster_url = resolve_official_href(discovery_source_url, rosters[0][0]) if rosters else None
            if season in seen:
                raise AuthorityViolation(f"duplicate official season row: {season}")
            seen.add(season)
            seasons.append(
                {
                    "season": season,
                    "official_index_url": official_index_url,
                    "discovery_source_url": discovery_source_url,
                    "link_text": results[0][1],
                    "official_host": official_host(official_index_url),
                    "official_host_valid": official_host(official_index_url) in OFFICIAL_HOSTS,
                    "url_directly_emitted_by_official_page": True,
                    "roster_url": roster_url,
                    "roster_link_exists": roster_url is not None,
                }
            )
    if not seasons:
        raise AuthorityViolation("official history index emitted no season-index Results links")
    return sorted(seasons, key=lambda item: item["season"], reverse=True)


def is_box_score_url(url: str) -> bool:
    path = urlsplit(url).path.lower()
    name = path.rsplit("/", 1)[-1]
    if TEAM_STAT_NAME_RE.match(name):
        return False
    return "/history/football/stats/" in path and name.endswith((".html", ".htm"))


def parse_box_score_urls(body: bytes, parent_url: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for href, label in ANCHOR_RE.findall(body.decode("latin-1", errors="replace")):
        if not BOX_LABEL_RE.match(fragment_text(label)):
            continue
        candidate = resolve_official_href(parent_url, href)
        if not is_box_score_url(candidate):
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        urls.append(candidate)
    return urls


def parse_season_stat_urls(body: bytes, parent_url: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for href, label in ANCHOR_RE.findall(body.decode("latin-1", errors="replace")):
        text = fragment_text(label).casefold()
        candidate = resolve_official_href(parent_url, href)
        path = urlsplit(candidate).path.lower()
        name = path.rsplit("/", 1)[-1]
        if TEAM_STAT_NAME_RE.match(name) or "stats/season" in path or "cumulative stats" in text or "team game-by-game" in text:
            if candidate not in seen:
                seen.add(candidate)
                urls.append(candidate)
    return urls


def existing_raw_captures(data_root: Path) -> dict[str, dict[str, Any]]:
    captures: dict[str, dict[str, Any]] = {}
    raw_root = data_root / ARCHIVE_RAW_ROOT
    if not raw_root.is_dir():
        return captures
    for path in sorted(raw_root.rglob("sha256_*.html")):
        digest = path.stem.replace("sha256_", "")
        if sha256_file(path) != digest:
            raise AuthorityViolation(f"raw capture hash mismatch: {path}")
        captures[digest] = {
            "raw_sha256": digest,
            "raw_relative_path": path.relative_to(data_root).as_posix(),
            "raw_byte_count": path.stat().st_size,
            "path": path,
        }
    return captures


def load_capture_index(data_root: Path) -> list[dict[str, Any]]:
    path = data_root / CAPTURE_INDEX_RELATIVE
    if not path.is_file():
        return []
    payload = load_json(path)
    return list(payload.get("captures") or [])


def write_capture_index(data_root: Path, captures: list[Mapping[str, Any]]) -> None:
    merged: dict[str, dict[str, Any]] = {}
    for record in load_capture_index(data_root) + list(captures):
        url = record.get("url") or record.get("final_url")
        if url:
            merged[str(url)] = dict(record)
    write_json(
        data_root / CAPTURE_INDEX_RELATIVE,
        {
            "schema_version": SCHEMA_VERSION,
            "purpose": "URL-to-hash index for official season-index pages captured for the coverage inventory. Raw bytes remain content-addressed under SRC-014.",
            "captures": [merged[key] for key in sorted(merged)],
        },
    )


def capture_index_by_url(archive_gate: Mapping[str, Any], extra: list[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    by_url: dict[str, dict[str, Any]] = {}
    for record in list(archive_gate.get("captures") or []) + extra:
        url = record.get("url") or record.get("final_url")
        if not url:
            continue
        by_url[str(url)] = dict(record)
    return by_url


def coverage_maps(
    *,
    repo_root: Path,
    data_root: Path,
) -> dict[str, Any]:
    union_gate = load_json(repo_root / UNION_GATE_RELATIVE)
    if union_gate.get("gate_identity") != UNION_GATE_IDENTITY:
        raise AuthorityViolation("union gate identity drifted")
    official_by_season = {
        int(season): int(payload.get("official_school_games") or 0)
        for season, payload in (union_gate.get("coverage_by_season") or {}).items()
    }
    union_contract = load_json(repo_root / UNION_CONTRACT_RELATIVE)
    wmt_games, wmt_mount = load_wmt_compact_games(data_root, union_contract)
    wmt_by_season: dict[int, int] = {}
    if wmt_mount == "MOUNTED":
        for game in wmt_games:
            season = int(game["season"])
            wmt_by_season[season] = wmt_by_season.get(season, 0) + 1
    else:
        layer = union_gate.get("wmt_layer") or {}
        gaps = {int(item) for item in layer.get("source_evidence_gap_seasons") or []}
        minimum = int(layer.get("source_season_min") or 0)
        maximum = int(layer.get("source_season_max") or 0)
        for season in range(minimum, maximum + 1):
            if season not in gaps:
                wmt_by_season[season] = 0
    boxscore_gate = load_json(repo_root / BOXSCORE_GATE_RELATIVE)
    src014_by_season = {
        int(season): int(payload) if not isinstance(payload, Mapping) else int(payload.get("games") or payload.get("official_school_games") or 0)
        for season, payload in (boxscore_gate.get("coverage_by_season") or official_by_season).items()
    }
    if not src014_by_season:
        src014_by_season = dict(official_by_season)
    return {
        "union_gate": union_gate,
        "official_by_season": official_by_season,
        "wmt_by_season": wmt_by_season,
        "src014_by_season": src014_by_season,
        "wmt_mount": wmt_mount,
    }


def classify_row(
    *,
    season: int,
    official_index_url: str | None,
    season_index_captured: bool,
    box_score_count: int | None,
    union_games: int,
    selected: set[int],
    rejected: dict[int, str],
) -> str:
    if season in selected:
        return "SELECTED_NEXT_PRE2010_OFFICIAL_SEASON"
    if season in rejected:
        return rejected[season]
    if season >= 2010:
        return "SEASON_GE_2010_NOT_SELECTED_FOR_PRE2010_EXPANSION"
    if union_games:
        return "ALREADY_IN_IMMUTABLE_UNION"
    if not official_index_url:
        return "NO_OFFICIAL_SEASON_INDEX_LINK"
    if not season_index_captured:
        return "SEASON_INDEX_NOT_CAPTURED"
    if not box_score_count:
        return "NO_BOX_SCORE_LINKS_DISCOVERED"
    return "NOT_EVALUATED_AFTER_TWO_SEASONS_SELECTED"


def build_inventory_objects(
    *,
    repo_root: Path,
    data_root: Path,
    extra_captures: list[Mapping[str, Any]] | None = None,
    require_two_selected: bool = True,
) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    archive_gate = load_json(repo_root / ARCHIVE_GATE_RELATIVE)
    coverage = coverage_maps(repo_root=repo_root, data_root=data_root)
    raw_by_hash = existing_raw_captures(data_root)
    extra = list(extra_captures or []) + load_capture_index(data_root)
    history = raw_by_hash.get(HISTORY_INDEX_SHA256)
    if history is None:
        raise AuthorityViolation("captured official history index is missing")
    history_body = history["path"].read_bytes()
    if sha256_bytes(history_body) != HISTORY_INDEX_SHA256:
        raise AuthorityViolation("history index bytes drifted")
    parsed = parse_history_index_seasons(history_body, HISTORY_INDEX_URL)
    captures_by_url = capture_index_by_url(archive_gate, extra)
    rows: list[dict[str, Any]] = []
    for item in parsed:
        capture = captures_by_url.get(item["official_index_url"])
        captured = False
        box_urls: list[str] = []
        season_stat_urls: list[str] = []
        raw_sha256 = None
        raw_path = None
        if capture and capture.get("raw_sha256"):
            digest = capture["raw_sha256"]
            stored = raw_by_hash.get(digest)
            if stored is not None:
                captured = True
                raw_sha256 = digest
                raw_path = stored["raw_relative_path"]
                body = stored["path"].read_bytes()
                box_urls = parse_box_score_urls(body, item["official_index_url"])
                season_stat_urls = parse_season_stat_urls(body, item["official_index_url"])
        wmt_games = int(coverage["wmt_by_season"].get(item["season"], 0))
        src014_games = int(coverage["src014_by_season"].get(item["season"], 0))
        official_union = int(coverage["official_by_season"].get(item["season"], 0))
        union_games = official_union + (wmt_games if official_union == 0 else 0)
        if official_union and wmt_games:
            union_games = official_union + wmt_games
        if item["season"] >= 2012:
            union_games = max(union_games, wmt_games)
        if item["season"] in {2010, 2011}:
            union_games = max(union_games, official_union, src014_games)
        rows.append(
            {
                **item,
                "season_index_capture_exists": captured,
                "season_index_raw_sha256": raw_sha256,
                "season_index_raw_relative_path": raw_path,
                "season_stat_links_exist": bool(season_stat_urls),
                "season_stat_urls": season_stat_urls,
                "box_score_link_count": len(box_urls) if captured else None,
                "box_score_urls": box_urls,
                "wmt_game_count": wmt_games,
                "src014_game_count": src014_games,
                "union_game_count": union_games,
                "historical_publication_time": None,
                "historical_publication_time_status": "UNRESOLVED_RETRIEVAL_TIME_ONLY",
            }
        )

    selected: list[int] = []
    rejected: dict[int, str] = {}
    for row in rows:
        season = int(row["season"])
        if season >= 2010:
            continue
        if row["union_game_count"]:
            rejected[season] = "ALREADY_IN_IMMUTABLE_UNION"
            continue
        if not row["official_index_url"] or not row["url_directly_emitted_by_official_page"]:
            rejected[season] = "NO_OFFICIAL_SEASON_INDEX_LINK"
            continue
        if not row["season_index_capture_exists"]:
            if len(selected) >= 2:
                continue
            rejected[season] = "SEASON_INDEX_NOT_RETRIEVABLE_OR_NOT_CAPTURED"
            continue
        if not row["box_score_link_count"]:
            rejected[season] = "NO_BOX_SCORE_LINKS_DISCOVERED_FROM_OFFICIAL_SEASON_INDEX"
            continue
        if len(selected) < 2:
            selected.append(season)
        if len(selected) >= 2:
            break
    if require_two_selected and len(selected) != 2:
        raise AuthorityViolation(f"inventory did not independently select two pre-2010 seasons: {selected}")

    for row in rows:
        row["remaining_evidence_gaps"] = []
        if row["union_game_count"] == 0:
            row["remaining_evidence_gaps"].append("NOT_IN_IMMUTABLE_UNION")
        if not row["season_index_capture_exists"]:
            row["remaining_evidence_gaps"].append("SEASON_INDEX_NOT_CAPTURED")
        if row["box_score_link_count"] in {None, 0}:
            row["remaining_evidence_gaps"].append("BOX_SCORE_URLS_NOT_OBTAINED")
        if row["historical_publication_time"] is None:
            row["remaining_evidence_gaps"].append("HISTORICAL_PUBLICATION_TIME_UNRESOLVED")
        row["eligibility_classification"] = classify_row(
            season=int(row["season"]),
            official_index_url=row.get("official_index_url"),
            season_index_captured=bool(row["season_index_capture_exists"]),
            box_score_count=row.get("box_score_link_count"),
            union_games=int(row["union_game_count"]),
            selected=set(selected),
            rejected=rejected,
        )

    selected_rows = [row for row in rows if row["season"] in selected]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_HISTORICAL_COVERAGE_INVENTORY",
        "contract_id": CONTRACT_ID,
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "source_id": SOURCE_ID,
        "history_index_url": HISTORY_INDEX_URL,
        "history_index_sha256": HISTORY_INDEX_SHA256,
        "seasons": rows,
        "selected_seasons": [
            {
                "season": row["season"],
                "official_index_url": row["official_index_url"],
                "box_score_link_count": row["box_score_link_count"],
                "box_score_urls": row["box_score_urls"],
                "season_index_raw_sha256": row["season_index_raw_sha256"],
            }
            for row in selected_rows
        ],
        "rejected_seasons": [
            {"season": season, "reason": reason}
            for season, reason in sorted(rejected.items(), key=lambda item: item[0], reverse=True)
        ],
        "upstream_identities": {
            "union_gate_identity": UNION_GATE_IDENTITY,
            "union_identity": UNION_IDENTITY,
            "wmt_acquisition_identity": coverage["union_gate"]["upstream_identities"]["wmt_acquisition_identity"],
            "wmt_dataset_identity": coverage["union_gate"]["upstream_identities"]["wmt_dataset_identity"],
            "archive_gate_identity": archive_gate.get("gate_identity"),
            "protected_split_registry_sha256": REGISTRY_SHA256,
        },
        "admissions": expected_admissions(),
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "protected_lane": PROTECTED_LANE,
    }
    payload["inventory_identity"] = stable_hash(
        {
            "history_index_sha256": payload["history_index_sha256"],
            "seasons": payload["seasons"],
            "selected_seasons": payload["selected_seasons"],
            "rejected_seasons": payload["rejected_seasons"],
        }
    )
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_HISTORICAL_COVERAGE_INVENTORY_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "disposition": "INVENTORY_ONLY_NO_UNION_MUTATION",
        "source_id": SOURCE_ID,
        "inventory_identity": payload["inventory_identity"],
        "history_index_sha256": HISTORY_INDEX_SHA256,
        "selected_seasons": [row["season"] for row in selected_rows],
        "rejected_seasons": payload["rejected_seasons"],
        "counts": {
            "official_index_seasons": len(rows),
            "pre2010_official_index_seasons": sum(1 for row in rows if row["season"] < 2010),
            "selected_pre2010_seasons": 2,
            "selected_box_score_urls": sum(int(row["box_score_link_count"] or 0) for row in selected_rows),
            "ncaa_contest_ids_created": 0,
        },
        "upstream_identities": payload["upstream_identities"],
        "admissions": expected_admissions(),
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "protected_lane": PROTECTED_LANE,
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    return {"contract": contract, "payload": payload, "gate": gate, "coverage": coverage}


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    return stable_hash({field: gate.get(field) for field in GATE_IDENTITY_FIELDS})


def reconstruct_inventory(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    return build_inventory_objects(repo_root=repo_root, data_root=data_root)


def fetch_official_season_index(url: str, season: int) -> dict[str, Any]:
    validate_official_url(url)
    path_years = {int(item) for item in HREF_YEAR_RE.findall(urlsplit(url).path)}
    if path_years and season not in path_years:
        raise AuthorityViolation(f"refusing to fetch URL whose path years {path_years} omit {season}")
    record = direct_http_get(url)
    body = record.pop("body")
    if int(record["status"]) != 200:
        return {**record, "parser_disposition": "HTTP_NOT_OK", "source_season": season, "body": body}
    try:
        disposition = classify_capture(url, body, record.get("content_type"), int(record["status"]))
    except Exception as exc:  # noqa: BLE001 - preserve honest parser disposition
        disposition = f"REJECTED:{type(exc).__name__}"
    return {
        **record,
        "page_family": "season_index",
        "parent_url": HISTORY_INDEX_URL,
        "parser_disposition": disposition,
        "source_season": season,
        "rights_disposition": "PRIVATE_RESEARCH_METADATA_ONLY_NONBLOCKING",
        "body": body,
    }


def materialize_inventory(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    extra: list[dict[str, Any]] = []
    draft = build_inventory_objects(repo_root=repo_root, data_root=data_root, require_two_selected=False)
    needed = [
        row
        for row in draft["payload"]["seasons"]
        if row["season"] < 2010 and not row["union_game_count"] and not row["season_index_capture_exists"]
    ]
    selected = 0
    for row in needed:
        if selected >= 2:
            break
        fetched = fetch_official_season_index(row["official_index_url"], int(row["season"]))
        body = fetched.pop("body")
        stored = persist_capture(data_root, fetched, body)
        extra.append(compact_capture(stored) | {"raw_sha256": stored["raw_sha256"], "url": stored["url"]})
        if stored.get("parser_disposition") == "VERIFIED_OFFICIAL_SCHOOL_PAGE" and parse_box_score_urls(
            body, row["official_index_url"]
        ):
            selected += 1
    write_capture_index(data_root, extra)
    objects = build_inventory_objects(repo_root=repo_root, data_root=data_root, extra_captures=extra)
    payload = objects["payload"]
    gate = objects["gate"]
    payload_root = data_root / objects["contract"]["payloads"]["normalized_root"] / payload["inventory_identity"]
    write_json(payload_root / "inventory.json", payload)
    write_json(repo_root / GATE_RELATIVE, gate)
    return {
        "inventory_identity": payload["inventory_identity"],
        "gate_identity": gate["gate_identity"],
        "selected_seasons": gate["selected_seasons"],
        "payload_path": str(payload_root / "inventory.json"),
        "gate_path": GATE_RELATIVE,
    }


def validate_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    gate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    reconstructed = reconstruct_inventory(repo_root=repo_root, data_root=data_root)
    expected_gate = reconstructed["gate"]
    expected_payload = reconstructed["payload"]
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("authority", {}).get("historical_known_at_from_capture_time"):
        raise AuthorityViolation("retrieval time promoted to historical known-at")
    if committed.get("scientific_nonclaims", {}).get("historical_known_at_established"):
        raise AuthorityViolation("historical known-at forged")
    if committed.get("counts", {}).get("ncaa_contest_ids_created"):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if committed.get("result") != expected_gate["result"] or committed.get("classification") != expected_gate["classification"]:
        raise AuthorityViolation("completion or classification forged")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not recompute")
    if committed != expected_gate:
        raise AuthorityViolation("committed inventory gate does not match independent reconstruction")
    payload_path = (
        data_root
        / reconstructed["contract"]["payloads"]["normalized_root"]
        / expected_payload["inventory_identity"]
        / "inventory.json"
    )
    if not payload_path.is_file():
        raise AuthorityViolation("external inventory payload missing")
    payload = load_json(payload_path)
    if payload != expected_payload:
        raise AuthorityViolation("external inventory payload does not match reconstruction")
    seasons = [int(item["season"]) for item in expected_payload["seasons"]]
    if seasons != sorted(seasons, reverse=True):
        raise AuthorityViolation("season ordering is not official-index descending")
    union_seasons = set(reconstructed["coverage"]["official_by_season"]) | set(
        reconstructed["coverage"]["wmt_by_season"]
    )
    for row in expected_payload["seasons"]:
        if row["season"] in union_seasons and row["union_game_count"] == 0:
            raise AuthorityViolation(f"existing union season falsely marked missing: {row['season']}")
        if row["discovery_source_url"] != HISTORY_INDEX_URL:
            raise AuthorityViolation("missing official discovery provenance")
        if official_host(row["official_index_url"]) not in OFFICIAL_HOSTS:
            raise AuthorityViolation("third-party discovery URL presented as official")
        path_years = {int(item) for item in HREF_YEAR_RE.findall(urlsplit(row["official_index_url"]).path)}
        if path_years and row["season"] not in path_years:
            raise AuthorityViolation("guessed season URL")
    selected = [int(item) for item in expected_gate["selected_seasons"]]
    if selected != sorted(selected, reverse=True) or any(season >= 2010 for season in selected):
        raise AuthorityViolation("selected seasons are not the two most recent qualifying pre-2010 seasons")
    return {
        "result": "PASS",
        "gate_identity": expected_gate["gate_identity"],
        "inventory_identity": expected_payload["inventory_identity"],
        "selected_seasons": selected,
    }


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]

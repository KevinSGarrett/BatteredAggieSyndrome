"""Parse source-labeled 2005 official domains and classify Cycle #12 HTML tables."""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.tamu_official_historical_archive import sha256_file, validate_official_url
from aggie_analytics.data.tamu_official_historical_boxscores import (
    AuthorityViolation,
    expected_authority,
    expected_scientific_nonclaims,
)
from aggie_analytics.data.tamu_official_html_table_classifier import (
    PARSER_IDENTITY as TABLE_PARSER_IDENTITY,
    PLAY_BY_PLAY,
    classify_page,
    compact_classification,
)
from aggie_analytics.data.tamu_official_statcrew_preformatted import (
    DOMAINS,
    _assign_labeled_blocks,
    extract_pre_blocks,
    parse_preformatted_page,
)
from aggie_analytics.validation.artifact_binding import compute_identity


SCHEMA_VERSION = "aggie.data.tamu_official_2005_structured_domains.v1"
CONTRACT_RELATIVE = "configs/tamu_official_2005_structured_domains_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_2005_structured_domains_gate.json"
CONTRACT_ID = "BAT-601-TAMU-OFFICIAL-2005-STRUCTURED-DOMAINS-V1"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_SRC014_OFFICIAL_2005_STRUCTURED_DOMAIN_CANDIDATE_ONLY"
PASS_RESULT = "PASS_OFFICIAL_2005_STRUCTURED_DOMAINS_AND_HTML_TABLES_CLASSIFIED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
CAPTURE_INDEX_RELATIVE = "features/tamu_official_2005_boxscores/capture_index.json"
BOX_2006_CAPTURE_INDEX = "features/tamu_official_2006_boxscores/capture_index.json"
BOX_2007_CAPTURE_INDEX = "features/tamu_official_2007_boxscores/capture_index.json"
INVENTORY_IDENTITY = "d39d35ff7cfacf2e39a524d0f1fdb97072158c50f84225ed8413771140efaa37"
INVENTORY_GATE_IDENTITY = "f1a5821ad081dce7058848ccc453344f0a2827030959049133b69db15689c851"
INVENTORY_GATE_RELATIVE = "artifacts/data_lake/tamu_official_historical_coverage_inventory_gate.json"
PINNED_BAT600_GATE_IDENTITY = "c999af29522096e4ae3a9cdc558679321095c8cf11247ef1ccd23b3114ee18cc"
PINNED_BAT600_ACQUISITION_IDENTITY = "56aa050f4bf12c2e02a93915e03125f6cf782ea5b5cfd8b9bab63d724c3e5b59"
PINNED_BAT600_DATASET_IDENTITY = "e063378e564a3dcdbb09e42ea63cc0a843e9db8918130ecffd02f796c3805dbb"
PINNED_BAT600_GAMES_IDENTITY = "7bb39a7eaad39fa1b1c3ce640c78f309935c307c18d8498e6143cc35009153aa"
PINNED_BAT599_GATE_IDENTITY = "17868efadbc5cc6ec04869d194b8b8a205089c3050b069eec3e5ba9c1d25c301"
PINNED_BAT596_GATE_IDENTITY = "57eb2e0b9e449bef0b7935b89c573bfed79110e53d1de414984e0f781baa97a4"
PINNED_BAT596_PAYLOAD_IDENTITY = "039c773f902cbea6d7c6e361ac10315dfec364e30ebb83003bf3717cd9d1dfea"
PINNED_BAT591_GATE_IDENTITY = "9c3da52dceebd8da0908aa478326196bef2338095a8b5d4c42decaa27df53e16"
PINNED_BAT591_PAYLOAD_IDENTITY = "ba0820e45938714c144c4accee6637a67812e70dd89e4eb99b0373fc88a91d1d"
PINNED_BAT595_GATE_IDENTITY = "2a9c56a10b14cf5fec4dff1c3cd55d0b4440afdb9520fb308317a9ae59c47ed7"
PREFORMATTED_PARSER_IDENTITY = "tamu.official.statcrew.preformatted.v1"
TEXAS_2006_URL = "https://files.12thman.com/history/football/stats/2006-2007/texas.htm"
MSU_2007_URL = "https://files.12thman.com/history/football/stats/2007-2008/ta01-msu.htm"
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
    "html_table_classifications",
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


def load_2005_captures(repo_root: Path, data_root: Path) -> list[dict[str, Any]]:
    inventory = load_json(repo_root / INVENTORY_GATE_RELATIVE)
    if inventory.get("inventory_identity") != INVENTORY_IDENTITY or inventory.get("gate_identity") != INVENTORY_GATE_IDENTITY:
        raise AuthorityViolation("BAT-585 inventory identity rewritten")
    bat600 = load_json(repo_root / "artifacts/data_lake/tamu_official_2005_boxscore_gate.json")
    if bat600.get("gate_identity") != PINNED_BAT600_GATE_IDENTITY:
        raise AuthorityViolation("BAT-600 2005 acquisition identity rewritten")
    if bat600.get("acquisition_identity") != PINNED_BAT600_ACQUISITION_IDENTITY:
        raise AuthorityViolation("BAT-600 acquisition identity rewritten")
    if bat600.get("dataset_identity") != PINNED_BAT600_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-600 dataset identity rewritten")
    if bat600.get("games_identity") != PINNED_BAT600_GAMES_IDENTITY:
        raise AuthorityViolation("BAT-600 games identity rewritten")
    bat599 = load_json(repo_root / "artifacts/data_lake/tamu_official_2005_season_index_gate.json")
    if bat599.get("gate_identity") != PINNED_BAT599_GATE_IDENTITY:
        raise AuthorityViolation("BAT-599 2005 index identity rewritten")
    bat596 = load_json(repo_root / "artifacts/data_lake/tamu_official_2006_structured_domains_gate.json")
    if bat596.get("gate_identity") != PINNED_BAT596_GATE_IDENTITY:
        raise AuthorityViolation("BAT-596 2006 structured-domain identity rewritten")
    if bat596.get("payload_identity") != PINNED_BAT596_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-596 payload identity rewritten")
    bat591 = load_json(repo_root / "artifacts/data_lake/tamu_official_statcrew_preformatted_gate.json")
    if bat591.get("gate_identity") != PINNED_BAT591_GATE_IDENTITY:
        raise AuthorityViolation("BAT-591 StatCrew identity rewritten")
    if bat591.get("payload_identity") != PINNED_BAT591_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-591 payload identity rewritten")
    bat595 = load_json(repo_root / "artifacts/data_lake/tamu_official_2006_boxscore_gate.json")
    if bat595.get("gate_identity") != PINNED_BAT595_GATE_IDENTITY:
        raise AuthorityViolation("BAT-595 2006 acquisition identity rewritten")
    allowlist = [validate_official_url(str(url)) for url in (bat599.get("box_score_urls") or [])]
    if len(allowlist) != 11:
        raise AuthorityViolation("BAT-599 allowlist is not the 11 official 2005 box URLs")
    path = data_root / CAPTURE_INDEX_RELATIVE
    if not path.is_file():
        raise AuthorityViolation("BAT-600 capture index missing")
    by_url = {item["url"]: dict(item) for item in (load_json(path).get("captures") or [])}
    captures = []
    for url in allowlist:
        if url not in by_url:
            raise AuthorityViolation(f"BAT-600 capture missing official 2005 URL: {url}")
        captures.append(by_url[url])
    return captures


def bind_preformatted(parsed: dict[str, Any], body: bytes) -> dict[str, Any]:
    blocks = extract_pre_blocks(body.decode("latin-1", errors="replace"))
    assigned = _assign_labeled_blocks(blocks)
    block_index: dict[str, int] = {}
    for domain, domain_blocks in assigned.items():
        if not domain_blocks:
            continue
        try:
            block_index[domain] = blocks.index(domain_blocks[0])
        except ValueError:
            block_index[domain] = 0
    for domain in DOMAINS:
        for row in parsed[domain]:
            row["parser_identity"] = PREFORMATTED_PARSER_IDENTITY
            row["block_index"] = block_index.get(domain)
            row["source_domain"] = domain
            row["availability"] = "NOT_ESTABLISHED"
    parsed["parser_identity"] = PREFORMATTED_PARSER_IDENTITY
    parsed["availability_claim"] = False
    return parsed


def classify_bound_page(data_root: Path, index_relative: str, url: str, source_season: int) -> dict[str, Any]:
    index_path = data_root / index_relative
    if not index_path.is_file():
        raise AuthorityViolation(f"capture index missing for HTML classification: {index_relative}")
    match = next((item for item in (load_json(index_path).get("captures") or []) if item.get("url") == url), None)
    if match is None:
        raise AuthorityViolation(f"HTML classification URL was not in the bound capture index: {url}")
    raw_path = data_root / match["raw_relative_path"]
    if not raw_path.is_file():
        raise AuthorityViolation(f"HTML classification raw page missing: {url}")
    if sha256_file(raw_path) != match["raw_sha256"]:
        raise AuthorityViolation("HTML classification raw hash drifted")
    page = classify_page(
        raw_path.read_bytes(),
        url=validate_official_url(url),
        raw_sha256=str(match["raw_sha256"]),
        source_season=source_season,
    )
    page["raw_relative_path"] = match["raw_relative_path"]
    if page["domain_coverage"][PLAY_BY_PLAY] == "PRESENT":
        raise AuthorityViolation("empty or unlabeled HTML tables were promoted to play-by-play")
    if page["availability_claim"] or page["participation_as_availability"]:
        raise AuthorityViolation("participation or membership promoted to availability")
    return page


def _bind_rows(game: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for domain in DOMAINS:
        for item in game[domain]:
            rows.append({"domain": domain, **item})
    return rows


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    captures = load_2005_captures(repo_root, data_root)
    games: list[dict[str, Any]] = []
    for capture in captures:
        raw_path = data_root / capture["raw_relative_path"]
        if not raw_path.is_file():
            raise AuthorityViolation(f"captured raw page missing: {capture['raw_relative_path']}")
        raw_sha256 = str(capture["raw_sha256"])
        if sha256_file(raw_path) != raw_sha256:
            raise AuthorityViolation("raw capture bytes do not match recorded SHA-256")
        body = raw_path.read_bytes()
        parsed = parse_preformatted_page(
            body,
            url=validate_official_url(str(capture["url"])),
            source_season=2005,
            raw_sha256=raw_sha256,
        )
        games.append(bind_preformatted(parsed, body))
    texas = classify_bound_page(data_root, BOX_2006_CAPTURE_INDEX, TEXAS_2006_URL, 2006)
    msu = classify_bound_page(data_root, BOX_2007_CAPTURE_INDEX, MSU_2007_URL, 2007)
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
            "parser_identity": game["parser_identity"],
            "domain_coverage": {domain: game["domain_coverage"][domain] for domain in DOMAINS},
            "row_counts": {domain: len(game[domain]) for domain in DOMAINS},
            "rich_structured": game["rich_structured"],
            "warnings": game["warnings"],
        }
        for game in games
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "source_id": SOURCE_ID,
        "games": games,
        "rows": [_bind_rows(game) for game in games],
        "html_table_classifications": {"texas_2006": texas, "montana_state_2007": msu},
        "admissions": {
            "bat_401": "DONE_VERIFIED_RETAIN_PROTECTED_LANE_BLOCKED",
            "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
            "bat_523": "IN_PROGRESS",
            "bat_591_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_595_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_596_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_600_payload": "CONSUMED_CAPTURES_ONLY",
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
        "target_games_total": 11,
        "parsed_games": len(games),
        "games_2005": len(games),
        "rich_structured_games": sum(1 for game in games if game["rich_structured"]),
        "metadata_only_games": sum(1 for game in games if not game["rich_structured"]),
        "ambiguous_boundary_games": sum(1 for game in games if game["warnings"]),
        "ncaa_contest_ids_created": 0,
        "name_only_player_merges": 0,
        "availability_claims": 0,
        "html_tables_classified_pages": 2,
        "texas_2006_table_count": texas["table_count"],
        "texas_2006_unknown_tables": texas["unknown_table_count"],
        "montana_state_2007_table_count": msu["table_count"],
        "montana_state_2007_unknown_tables": msu["unknown_table_count"],
        "html_play_by_play_present_pages": 0,
        "games_admitted_to_union": 0,
        "pregame_availability_present": 0,
    }
    for domain in DOMAINS:
        counts[f"{domain}_present_games"] = int(coverage_counts[domain])
        counts[f"{domain}_absent_games"] = len(games) - int(coverage_counts[domain])
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_2005_STRUCTURED_DOMAINS_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": "POST-TASK-SRC014-2005-STRUCTURED-DOMAINS-001",
        "jira_key": "BAT-601",
        "disposition": "NEW_ENRICHED_PAYLOAD_PRIOR_IDENTITIES_PRESERVED",
        "source_id": SOURCE_ID,
        "inventory_identity": INVENTORY_IDENTITY,
        "payload_identity": payload["payload_identity"],
        "selected_seasons": [2005],
        "counts": counts,
        "games": compact_games,
        "html_table_classifications": {
            "texas_2006": compact_classification(texas),
            "montana_state_2007": compact_classification(msu),
            "parser_identity": TABLE_PARSER_IDENTITY,
        },
        "admissions": payload["admissions"],
        "authority": payload["authority"],
        "scientific_nonclaims": payload["scientific_nonclaims"],
        "protected_lane": PROTECTED_LANE,
        "upstream_identities": {
            "inventory_identity": INVENTORY_IDENTITY,
            "inventory_gate_identity": INVENTORY_GATE_IDENTITY,
            "bat600_gate_identity": PINNED_BAT600_GATE_IDENTITY,
            "bat600_acquisition_identity": PINNED_BAT600_ACQUISITION_IDENTITY,
            "bat600_dataset_identity": PINNED_BAT600_DATASET_IDENTITY,
            "bat600_games_identity": PINNED_BAT600_GAMES_IDENTITY,
            "bat599_gate_identity": PINNED_BAT599_GATE_IDENTITY,
            "bat596_gate_identity": PINNED_BAT596_GATE_IDENTITY,
            "bat596_payload_identity": PINNED_BAT596_PAYLOAD_IDENTITY,
            "bat591_gate_identity": PINNED_BAT591_GATE_IDENTITY,
            "bat591_payload_identity": PINNED_BAT591_PAYLOAD_IDENTITY,
            "bat595_gate_identity": PINNED_BAT595_GATE_IDENTITY,
        },
    }
    if counts["ncaa_contest_ids_created"] or gate["authority"]["ncaa_contest_identity"]:
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if any(game["availability_claim"] for game in games):
        raise AuthorityViolation("postgame participation treated as availability")
    if texas["domain_coverage"][PLAY_BY_PLAY] != "ABSENT" or msu["domain_coverage"][PLAY_BY_PLAY] != "ABSENT":
        raise AuthorityViolation("unclassified HTML rows were treated as play-by-play")
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
        "rich_structured_games": objects["gate"]["counts"]["rich_structured_games"],
        "texas_unknown_tables": objects["gate"]["counts"]["texas_2006_unknown_tables"],
        "msu_unknown_tables": objects["gate"]["counts"]["montana_state_2007_unknown_tables"],
    }


def lake_is_ready(data_root: Path) -> bool:
    return (
        (data_root / CAPTURE_INDEX_RELATIVE).is_file()
        and (data_root / BOX_2006_CAPTURE_INDEX).is_file()
        and (data_root / BOX_2007_CAPTURE_INDEX).is_file()
    )


def validate_compact_gate(committed: Mapping[str, Any]) -> None:
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("authority", {}).get("historical_known_at_from_capture_time"):
        raise AuthorityViolation("retrieval time promoted to historical known-at")
    if committed.get("counts", {}).get("ncaa_contest_ids_created"):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if committed.get("result") not in {PASS_RESULT, "PARTIAL_OFFICIAL_2005_STRUCTURED_DOMAINS"}:
        raise AuthorityViolation("completion or classification forged")
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("completion or classification forged")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not recompute")
    if committed.get("inventory_identity") != INVENTORY_IDENTITY:
        raise AuthorityViolation("inventory identity rebound incorrectly")
    if (committed.get("counts") or {}).get("pregame_availability_present"):
        raise AuthorityViolation("pregame availability claimed")
    if (committed.get("upstream_identities") or {}).get("bat600_gate_identity") != PINNED_BAT600_GATE_IDENTITY:
        raise AuthorityViolation("BAT-600 2005 acquisition identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat596_gate_identity") != PINNED_BAT596_GATE_IDENTITY:
        raise AuthorityViolation("BAT-596 2006 structured-domain identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat591_gate_identity") != PINNED_BAT591_GATE_IDENTITY:
        raise AuthorityViolation("BAT-591 StatCrew identity rewritten")
    if (committed.get("upstream_identities") or {}).get("bat595_gate_identity") != PINNED_BAT595_GATE_IDENTITY:
        raise AuthorityViolation("BAT-595 2006 acquisition identity rewritten")
    html = committed.get("html_table_classifications") or {}
    for key in ("texas_2006", "montana_state_2007"):
        page = html.get(key) or {}
        if (page.get("domain_coverage") or {}).get("play_by_play") == "PRESENT":
            raise AuthorityViolation("unclassified HTML rows were treated as play-by-play")
        if page.get("availability_claim"):
            raise AuthorityViolation("participation or membership promoted to availability")


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
        raise AuthorityViolation("external 2005 structured-domain reconstruction was required but the data root is not mounted")
    if not ready:
        return {
            "result": "PASS",
            "gate_identity": committed["gate_identity"],
            "external_reconstruction": "NOT_MOUNTED",
        }
    expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    if committed != expected["gate"]:
        raise AuthorityViolation("committed 2005 structured-domain gate does not match independent reconstruction")
    payload_path = (
        data_root
        / expected["contract"]["payloads"]["enriched_root"]
        / expected["payload"]["payload_identity"]
        / "payload.json"
    )
    if not payload_path.is_file():
        raise AuthorityViolation("external structured-domain payload missing")
    if load_json(payload_path) != expected["payload"]:
        raise AuthorityViolation("external structured-domain payload does not match reconstruction")
    return {
        "result": "PASS",
        "gate_identity": expected["gate"]["gate_identity"],
        "payload_identity": expected["payload"]["payload_identity"],
        "parsed_games": expected["gate"]["counts"]["parsed_games"],
        "external_reconstruction": "MOUNTED",
    }


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]

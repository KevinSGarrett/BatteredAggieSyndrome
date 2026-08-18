"""Immutable SRC-014 official-school gamebook union for 2010-2011 plus preserved WMT 2012-2025."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import normalize_team_name, stable_hash
from aggie_analytics.data.tamu_official_historical_boxscores import (
    ARCHIVE_ACQUISITION_IDENTITY,
    GATE_RELATIVE as BOXSCORE_GATE_RELATIVE,
    PINNED_COVERAGE_IDENTITY,
    PINNED_GAMES_IDENTITY,
    WMT_ACQUISITION_IDENTITY,
    WMT_DATASET_IDENTITY,
    load_json,
    write_json,
)


SCHEMA_VERSION = "aggie.data.tamu_official_gamebook_union.v1"
CONTRACT_RELATIVE = "configs/tamu_official_gamebook_union_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_gamebook_union_gate.json"
HISTORICAL_GATE_RELATIVE = "artifacts/pit/historical_tamu_official_gamebook_reconciliation_gate.json"
ARCHIVE_GATE_RELATIVE = "artifacts/data_lake/tamu_official_historical_archive_gate.json"
EVIDENCE_RELATIVE = "artifacts/jira_evidence/POST-TASK-CYCLE-9-OFFICIAL-GAMEBOOK-UNION-001.json"
CONTRACT_ID = "BAT-581-TAMU-OFFICIAL-GAMEBOOK-UNION-V1"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_OFFICIAL_GAMEBOOK_UNION_CANDIDATE_ONLY"
PASS_RESULT = "PASS_IMMUTABLE_WMT_PRESERVED_OFFICIAL_SCHOOL_2010_2011_ADDED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
TEXAS_DISPOSITION = "RESOLVED_OFFICIAL_STRONG_TUPLE_SIDEARM_DATE_CONFLICT_PRESERVED"
LSU_DISPOSITION = "SEASON_INDEX_DATE_VS_BOX_PLAYED_DATE"
BAT570_MATRIX_IDENTITY = "1e191204aea9c008e708f367fd36352298a3af8b129af6d0fb03b11247c3fffa"
BAT570_GATE_IDENTITY = "6a88922c727a34772224ef176aebd4930815dde533893204cbca42402376da93"
BOXSCORE_GATE_IDENTITY = "29e76b1e264387b2195e2fd4c1d04bbb375d448789b4ac64aec701a61eceb1e5"
BOXSCORE_DATASET_IDENTITY = "46841fcd9e3c3d18be55a7e098b52e089bc1a307a9779783cf4192f1324ba2aa"
WMT_TARGET_GAMES = 177
WMT_RICH_GAMES = 164
WMT_METADATA_ONLY = 13
REGISTRY_SHA256 = "6b90ef6fb09abd89d7a82a8b5835b00615671a7742839269c7401a2d0af5f764"
DOMAIN_MAP = {
    "linescore_game_info": ("scores", "game_identity_metadata", "played_date"),
    "venue": ("site_venue",),
    "attendance": ("attendance",),
    "officials": ("officials",),
    "team_statistics": ("team_statistics",),
    "team_statistics_by_period": ("quarter_scoring",),
    "player_statistics": ("individual_player_statistics",),
    "drives": ("drives",),
    "play_by_play": ("play_by_play",),
    "scoring_summary": ("scoring_summary",),
    "participation": ("participation",),
}
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
    "counts",
    "texas_2011",
    "lsu_2010",
    "coverage_by_season",
    "coverage_by_domain",
    "official_games",
    "wmt_layer",
    "admissions",
    "authority",
    "scientific_nonclaims",
    "protected_lane",
    "upstream_identities",
    "bat570_supersession",
)


class AuthorityViolation(ValueError):
    """Raised when the union is asked to invent identity, mutate WMT, or open a sealed lane."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    return stable_hash({key: gate[key] for key in GATE_IDENTITY_FIELDS if key in gate})


def expected_authority() -> dict[str, bool]:
    return {
        "completeness_claim": False,
        "contest_id_fabrication": False,
        "ncaa_contest_identity": False,
        "name_only_promotion": False,
        "name_only_player_merge": False,
        "availability_claim": False,
        "membership_as_availability": False,
        "participation_as_availability": False,
        "historical_known_at_from_capture_time": False,
        "historical_pit_admission": False,
        "preliminary_training_admission": False,
        "protected_training_admission": False,
        "protected_evaluation_admission": False,
        "protected_outcome_authority": False,
        "champion_or_production_promotion": False,
        "forecast_publication": False,
        "tamu_specialization_lift_claims": False,
        "bas_or_aggie_excess_claims": False,
        "wmt_payload_mutated_in_place": False,
        "canonical_gamebook_admission": False,
        "bat_523_closed": False,
        "bat_429_ready_or_done": False,
    }


def expected_scientific_nonclaims() -> dict[str, bool]:
    return {
        "completeness_claimed": False,
        "tamu_gamebook_history_complete": False,
        "historical_population_ready": False,
        "historical_known_at_established": False,
        "pregame_availability_admitted": False,
        "participation_used_as_availability": False,
        "membership_used_as_availability": False,
        "ncaa_contest_ids_invented": False,
        "name_only_promoted": False,
        "protected_lane_opened": False,
        "protected_evaluation_admitted": False,
        "protected_performance_claimed": False,
        "champion_or_production_promotion": False,
        "tamu_specialization_lift_claimed": False,
        "bas_or_aggie_excess_result_claimed": False,
        "trained_production_champion": False,
        "wmt_payload_mutated": False,
        "bat_523_closed": False,
        "bat_429_advanced": False,
    }


def expected_admissions() -> dict[str, str]:
    return {
        "union_admission": "CANDIDATE_ONLY",
        "source_authority": "SRC-014_OFFICIAL_SCHOOL_EVIDENCE",
        "ncaa_contest_identity": "NOT_CREATED",
        "wmt_payload": "PRESERVED_IMMUTABLE",
        "historical_known_at": "UNKNOWN_CAPTURE_TIME_ONLY",
        "pregame_availability": "BLOCKED",
        "player_identity": "SOURCE_PLAYER_CANDIDATE",
        "protected_lane": PROTECTED_LANE,
        "bat_523": "IN_PROGRESS",
        "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
        "texas_2011": TEXAS_DISPOSITION,
        "lsu_2010": LSU_DISPOSITION,
    }


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise AuthorityViolation("gamebook-union contract identity drift")
    if contract.get("wmt_payload_policy") != "DO_NOT_REWRITE_IN_PLACE":
        raise AuthorityViolation("WMT payload rewrite is forbidden")
    for key, expected in expected_authority().items():
        if (contract.get("authority") or {}).get(key) is not expected:
            raise AuthorityViolation(f"contract authority {key} is not fail-closed")
    return contract


def load_official_compact_games(repo_root: Path) -> list[dict[str, Any]]:
    gate = load_json(repo_root / BOXSCORE_GATE_RELATIVE)
    if gate.get("gate_identity") != BOXSCORE_GATE_IDENTITY:
        raise AuthorityViolation("BAT-580 boxscore gate identity drifted")
    if gate.get("dataset_identity") != BOXSCORE_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-580 dataset identity drifted")
    if stable_hash(gate.get("games") or []) != PINNED_GAMES_IDENTITY:
        raise AuthorityViolation("official compact games were rewritten")
    if gate.get("coverage_identity") != PINNED_COVERAGE_IDENTITY:
        raise AuthorityViolation("official domain coverage identity drifted")
    games = list(gate.get("games") or [])
    if len(games) != 26:
        raise AuthorityViolation(f"expected 26 official compact games, found {len(games)}")
    if any(item.get("ncaa_contest_id") for item in games):
        raise AuthorityViolation("official box scores invented NCAA contest IDs")
    return games


def load_historical_wmt_layer(repo_root: Path) -> dict[str, Any]:
    gate = load_json(repo_root / HISTORICAL_GATE_RELATIVE)
    layer = dict(gate.get("candidate_layer") or {})
    if layer.get("dataset_identity") != WMT_DATASET_IDENTITY:
        raise AuthorityViolation("WMT reconciliation dataset identity was rewritten")
    if layer.get("acquisition_identity") != WMT_ACQUISITION_IDENTITY:
        raise AuthorityViolation("WMT acquisition identity was rewritten")
    if int(layer.get("target_games") or 0) != WMT_TARGET_GAMES:
        raise AuthorityViolation("WMT target-game count drifted")
    if int(layer.get("captured_games") or 0) != WMT_TARGET_GAMES:
        raise AuthorityViolation("WMT captured-game count drifted")
    if list(layer.get("source_evidence_gap_seasons") or []) != [2010, 2011]:
        raise AuthorityViolation("WMT gap-season record drifted")
    return {
        "acquisition_identity": layer["acquisition_identity"],
        "dataset_identity": layer["dataset_identity"],
        "manifest_sha256": layer.get("manifest_sha256"),
        "target_games": int(layer["target_games"]),
        "captured_games": int(layer["captured_games"]),
        "rich_structured_games": int(layer.get("rich_structured_games") or 0),
        "metadata_only_games": int(layer.get("metadata_only_games") or 0),
        "source_season_min": layer.get("source_season_min"),
        "source_season_max": layer.get("source_season_max"),
        "source_evidence_gap_seasons": [2010, 2011],
        "payload_mutated_in_place": False,
    }


def load_wmt_compact_games(data_root: Path, contract: Mapping[str, Any]) -> tuple[list[dict[str, Any]], str]:
    root = data_root / contract["payloads"]["wmt_gamebook_root"]
    path = root / "domain=game" / "candidate_records.parquet"
    if not path.is_file():
        return [], "NOT_MOUNTED"
    try:
        import polars
    except ImportError:
        return [], "NOT_MOUNTED"
    rows = polars.read_parquet(path).to_dicts()
    games: list[dict[str, Any]] = []
    for row in rows:
        season = int(row.get("season") or 0)
        if season in {2010, 2011}:
            raise AuthorityViolation("WMT gamebook unexpectedly contains 2010-2011 rows")
        games.append(
            {
                "source_lane": "WMT_GAMEBOOK",
                "season": season,
                "game_date": str(row.get("game_date") or "")[:10],
                "boxscore_id": row.get("boxscore_id"),
                "record_id": row.get("record_id"),
                "source_record_sha256": row.get("source_record_sha256"),
                "ncaa_contest_id": None,
                "historical_publication_time": None,
            }
        )
    if len(games) != WMT_TARGET_GAMES:
        raise AuthorityViolation(f"WMT game population drifted: {len(games)}")
    return games, "MOUNTED"


def is_texas_2011(official: Mapping[str, Any]) -> bool:
    return (
        int(official.get("source_season") or 0) == 2011
        and official.get("opponent_normalized") == normalize_team_name("Texas")
        and official.get("calendar_date") == "2011-11-24"
        and official.get("tamu_points") == 25
        and official.get("opponent_points") == 27
        and official.get("venue_state") == "HOME"
    )


def is_lsu_2010(official: Mapping[str, Any]) -> bool:
    return (
        int(official.get("source_season") or 0) == 2010
        and official.get("opponent_normalized") == normalize_team_name("LSU")
        and official.get("football_season") == 2010
        and official.get("calendar_date") == "2011-01-07"
        and official.get("index_date_candidate") == "2010-12-31"
        and official.get("conflict_status") == LSU_DISPOSITION
    )


def match_official_box(
    game: Mapping[str, Any],
    official_games: list[Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, str]:
    """Match a Sidearm/gap-matrix row to an official box without name-only promotion."""
    season = int(game.get("season") or 0)
    date = str(game.get("game_date") or "")[:10]
    opponent = normalize_team_name(str(game.get("opponent_name") or ""))
    pool = [item for item in official_games if int(item.get("source_season") or 0) == season]
    if season == 2011 and opponent == normalize_team_name("Texas") and date == "2011-11-25":
        texas = [item for item in pool if is_texas_2011(item)]
        if len(texas) == 1:
            return dict(texas[0]), TEXAS_DISPOSITION
        raise AuthorityViolation("2011 Texas official strong tuple is missing or duplicated")
    dated = [item for item in pool if item.get("calendar_date") == date]
    if len(dated) == 1:
        return dict(dated[0]), "MATCHED_SEASON_DATE_NOT_NAME_ONLY"
    if len(dated) > 1:
        named = [item for item in dated if item.get("opponent_normalized") == opponent]
        if len(named) == 1:
            return dict(named[0]), "MATCHED_SEASON_DATE_OPPONENT"
        raise AuthorityViolation(f"ambiguous official-box date match for {season} {date}")
    return None, "UNMATCHED"


def attach_official_boxes(
    games: list[dict[str, Any]],
    official_games: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    attached: list[dict[str, Any]] = []
    used: set[str] = set()
    for game in games:
        matched, status = match_official_box(game, official_games)
        row = dict(game)
        row["official_box"] = matched
        row["official_match_status"] = status
        if matched is not None:
            url = str(matched.get("url") or "")
            if url in used:
                raise AuthorityViolation(f"duplicate official-box assignment: {url}")
            used.add(url)
            if matched.get("ncaa_contest_id") is not None:
                raise AuthorityViolation("official box invented an NCAA contest ID")
        attached.append(row)
    if len(used) != len(official_games):
        raise AuthorityViolation(
            f"official-box assignment incomplete: {len(used)} of {len(official_games)} bound"
        )
    return attached


def official_domain_present(official: Mapping[str, Any] | None, domain: str) -> bool:
    if official is None:
        return False
    coverage = official.get("domain_coverage") or {}
    keys = DOMAIN_MAP.get(domain) or ()
    return any(coverage.get(key) == "PRESENT" for key in keys)


def texas_2011_record(official_games: list[Mapping[str, Any]]) -> dict[str, Any]:
    texas = next((item for item in official_games if is_texas_2011(item)), None)
    if texas is None:
        raise AuthorityViolation("2011 Texas official box tuple is missing")
    return {
        "opponent": "Texas",
        "resolved": True,
        "name_only_promotion": False,
        "disposition": TEXAS_DISPOSITION,
        "official_school_date": "2011-11-24",
        "ncaa_official_date": "2011-11-24",
        "official_season_index_date": "2011-11-24",
        "sidearm_or_gap_matrix_date": "2011-11-25",
        "lost_authority": "SIDEARM_SCHEDULE_DATE",
        "winning_authority": "OFFICIAL_SCHOOL_BOX_PLUS_NCAA_LEGACY_PLUS_OFFICIAL_SEASON_INDEX",
        "final_score": {"texas": 27, "texas_am": 25},
        "venue": {"name": texas.get("stadium") or "Kyle Field", "state": "HOME"},
        "source_url": texas.get("url"),
        "source_sha256": texas.get("source_sha256"),
        "canonical_game_identity": None,
        "ncaa_contest_id": None,
        "discrepancy_erased": False,
    }


def lsu_2010_record(official_games: list[Mapping[str, Any]]) -> dict[str, Any]:
    lsu = next((item for item in official_games if is_lsu_2010(item)), None)
    if lsu is None:
        raise AuthorityViolation("2010 LSU official box conflict record is missing")
    return {
        "opponent": "LSU",
        "football_season": 2010,
        "calendar_date": "2011-01-07",
        "season_index_date": "2010-12-31",
        "sidearm_or_gap_matrix_date": "2011-01-07",
        "disposition": LSU_DISPOSITION,
        "silently_normalized": False,
        "played_date_authority": "OFFICIAL_GAME_SPECIFIC_BOX_PAGE",
        "source_url": lsu.get("url"),
        "source_sha256": lsu.get("source_sha256"),
        "canonical_game_identity": None,
        "ncaa_contest_id": None,
    }


def coverage_by_season(official_games: list[Mapping[str, Any]]) -> dict[str, Any]:
    by_season: dict[str, dict[str, int]] = {}
    for game in official_games:
        key = str(game["source_season"])
        bucket = by_season.setdefault(
            key,
            {
                "official_school_games": 0,
                "rich_structured_games": 0,
                "metadata_only_games": 0,
                "matched_strong_tuple": 0,
                "date_conflicts": 0,
            },
        )
        bucket["official_school_games"] += 1
        if any(
            official_domain_present(game, domain)
            for domain in ("team_statistics", "player_statistics", "play_by_play")
        ):
            bucket["rich_structured_games"] += 1
        else:
            bucket["metadata_only_games"] += 1
        if game.get("canonical_game_match_status") == "MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE":
            bucket["matched_strong_tuple"] += 1
        if game.get("conflict_status") not in {None, "NONE"}:
            bucket["date_conflicts"] += 1
    return {key: by_season[key] for key in sorted(by_season)}


def coverage_by_domain(official_games: list[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    totals: dict[str, dict[str, int]] = {}
    for domain in DOMAIN_MAP:
        present = sum(1 for game in official_games if official_domain_present(game, domain))
        totals[domain] = {
            "official_school_present": present,
            "official_school_absent": len(official_games) - present,
            "wmt_2010_2011_present": 0,
            "eligibility": "OFFICIAL_SCHOOL_POSTGAME_CANDIDATE_NOT_PREGAME_NOT_NCAA_CONTEST",
        }
    totals["roster_membership"] = {
        "official_school_present": 0,
        "official_school_absent": 26,
        "wmt_2010_2011_present": 0,
        "eligibility": "SEASON_MEMBERSHIP_CANDIDATE_NOT_GAME_AVAILABILITY",
    }
    totals["pregame_availability"] = {
        "official_school_present": 0,
        "official_school_absent": 26,
        "wmt_2010_2011_present": 0,
        "eligibility": "NOT_PROVIDED_BY_ROUTE",
    }
    return totals


def expected_counts(
    official_games: list[Mapping[str, Any]],
    wmt_layer: Mapping[str, Any],
    wmt_games: list[Mapping[str, Any]],
) -> dict[str, int]:
    official_2010 = [item for item in official_games if int(item["source_season"]) == 2010]
    official_2011 = [item for item in official_games if int(item["source_season"]) == 2011]
    duplicates = 0
    wmt_keys = {
        (int(item["season"]), str(item.get("game_date") or "")[:10])
        for item in wmt_games
    }
    for item in official_games:
        if (int(item["source_season"]), item.get("calendar_date")) in wmt_keys:
            duplicates += 1
    added = len(official_games) - duplicates
    union_captured = int(wmt_layer["captured_games"]) + added
    return {
        "wmt_preserved_games": int(wmt_layer["captured_games"]),
        "official_2010_added": len(official_2010),
        "official_2011_added": len(official_2011),
        "official_added_total": added,
        "duplicates_detected": duplicates,
        "union_target_games": union_captured,
        "union_captured_games": union_captured,
        "rich_structured_games": int(wmt_layer["rich_structured_games"]) + added,
        "metadata_only_games": int(wmt_layer["metadata_only_games"]),
        "matched_strong_tuple": sum(
            1
            for item in official_games
            if item.get("canonical_game_match_status") == "MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE"
        ),
        "date_conflicts": sum(1 for item in official_games if item.get("conflict_status") not in {None, "NONE"}),
        "ncaa_contest_ids_created": 0,
        "wmt_2010_2011_games": 0,
    }


def compact_official_games(official_games: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for item in official_games:
        compact.append(
            {
                "source_season": item["source_season"],
                "football_season": item.get("football_season"),
                "calendar_date": item.get("calendar_date"),
                "index_date_candidate": item.get("index_date_candidate"),
                "opponent_candidate": item.get("opponent_candidate"),
                "opponent_normalized": item.get("opponent_normalized"),
                "tamu_points": item.get("tamu_points"),
                "opponent_points": item.get("opponent_points"),
                "venue_state": item.get("venue_state"),
                "stadium": item.get("stadium"),
                "site": item.get("site"),
                "url": item.get("url"),
                "source_sha256": item.get("source_sha256"),
                "canonical_game_match_status": item.get("canonical_game_match_status"),
                "conflict_status": item.get("conflict_status"),
                "domain_coverage": item.get("domain_coverage"),
                "ncaa_contest_id": None,
                "canonical_game_id": None,
                "availability_claim": False,
                "historical_publication_time": None,
                "temporal_authority": item.get("temporal_authority"),
            }
        )
    return compact


def expected_upstream(repo_root: Path) -> dict[str, str]:
    archive = load_json(repo_root / ARCHIVE_GATE_RELATIVE)
    return {
        "archive_acquisition_identity": ARCHIVE_ACQUISITION_IDENTITY,
        "archive_gate_identity": str(archive.get("gate_identity") or ""),
        "boxscore_gate_identity": BOXSCORE_GATE_IDENTITY,
        "boxscore_dataset_identity": BOXSCORE_DATASET_IDENTITY,
        "boxscore_games_identity": PINNED_GAMES_IDENTITY,
        "wmt_acquisition_identity": WMT_ACQUISITION_IDENTITY,
        "wmt_dataset_identity": WMT_DATASET_IDENTITY,
        "bat570_matrix_identity": BAT570_MATRIX_IDENTITY,
        "bat570_gate_identity": BAT570_GATE_IDENTITY,
        "protected_split_registry_sha256": REGISTRY_SHA256,
    }


def expected_gate_document(
    *,
    contract: Mapping[str, Any],
    official_games: list[Mapping[str, Any]],
    wmt_layer: Mapping[str, Any],
    wmt_games: list[Mapping[str, Any]],
    wmt_mount: str,
    repo_root: Path,
) -> dict[str, Any]:
    if any(item.get("ncaa_contest_id") for item in official_games):
        raise AuthorityViolation("NCAA contest IDs were invented")
    if any(item.get("availability_claim") for item in official_games):
        raise AuthorityViolation("availability was claimed from official box evidence")
    texas = texas_2011_record(official_games)
    lsu = lsu_2010_record(official_games)
    if texas["name_only_promotion"] or texas["discrepancy_erased"]:
        raise AuthorityViolation("2011 Texas was name-only promoted or the Sidearm conflict was erased")
    if lsu["silently_normalized"] or lsu["football_season"] != 2010:
        raise AuthorityViolation("2010 LSU season/calendar split was silently normalized")
    counts = expected_counts(official_games, wmt_layer, wmt_games)
    if counts["duplicates_detected"] != 0:
        raise AuthorityViolation("official 2010-2011 boxes collided with preserved WMT games")
    if counts["ncaa_contest_ids_created"] != 0:
        raise AuthorityViolation("NCAA contest IDs were invented")
    if counts["official_added_total"] != 26:
        raise AuthorityViolation("official added-game count drifted")
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_GAMEBOOK_UNION_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": contract["contract_id"],
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "disposition": "IMMUTABLE_SUPERSESSION_WMT_PRESERVED_OFFICIAL_SCHOOL_2010_2011_ADDED",
        "source_id": SOURCE_ID,
        "counts": counts,
        "texas_2011": texas,
        "lsu_2010": lsu,
        "coverage_by_season": coverage_by_season(official_games),
        "coverage_by_domain": coverage_by_domain(official_games),
        "official_games": compact_official_games(official_games),
        "wmt_layer": dict(wmt_layer),
        "admissions": expected_admissions(),
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "protected_lane": PROTECTED_LANE,
        "upstream_identities": expected_upstream(repo_root),
        "bat570_supersession": {
            "matrix_identity": BAT570_MATRIX_IDENTITY,
            "gate_identity": BAT570_GATE_IDENTITY,
            "parquet_mutated_in_place": False,
            "note": (
                "BAT-570 remains the Sidearm/NCAA 2010-2011 special-path matrix. "
                "Official-school 2010/2011 box domains are bound here and by the BAT-572/BAT-575 "
                "rebound. The BAT-570 parquet is not rewritten because overlaying official fields "
                "under the same matrix identity would mutate an immutable payload."
            ),
        },
        "wmt_external_reconstruction": wmt_mount,
    }
    return gate


def rebuild_expected(*, data_root: Path, repo_root: Path) -> dict[str, Any]:
    contract = load_contract(repo_root)
    registry = repo_root / "governance/PROTECTED_SPLIT_REGISTRY.csv"
    if sha256_file(registry) != REGISTRY_SHA256:
        raise AuthorityViolation("protected-split registry identity drift")
    official_games = load_official_compact_games(repo_root)
    wmt_layer = load_historical_wmt_layer(repo_root)
    wmt_games, wmt_mount = load_wmt_compact_games(data_root, contract)
    historical = load_json(repo_root / HISTORICAL_GATE_RELATIVE)
    if historical["candidate_layer"]["dataset_identity"] != WMT_DATASET_IDENTITY:
        raise AuthorityViolation("historical gamebook gate was mutated in place")
    gate = expected_gate_document(
        contract=contract,
        official_games=official_games,
        wmt_layer=wmt_layer,
        wmt_games=wmt_games,
        wmt_mount=wmt_mount,
        repo_root=repo_root,
    )
    gate["union_identity"] = stable_hash(
        {
            "official_games": gate["official_games"],
            "wmt_layer": gate["wmt_layer"],
            "counts": gate["counts"],
            "texas_2011": gate["texas_2011"],
            "lsu_2010": gate["lsu_2010"],
        }
    )
    gate["gate_identity"] = compute_gate_identity(gate)
    return {
        "contract": contract,
        "official_games": official_games,
        "wmt_layer": wmt_layer,
        "wmt_games": wmt_games,
        "wmt_mount": wmt_mount,
        "gate": gate,
    }


def materialize(*, data_root: Path, repo_root: Path) -> dict[str, Any]:
    expected = rebuild_expected(data_root=data_root, repo_root=repo_root)
    gate = dict(expected["gate"])
    payload_root = (
        data_root
        / "features"
        / "tamu_official_gamebook_union"
        / "sha256"
        / gate["union_identity"]
    )
    payload_root.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "union_identity": gate["union_identity"],
        "gate_identity": gate["gate_identity"],
        "counts": gate["counts"],
        "texas_2011": gate["texas_2011"],
        "lsu_2010": gate["lsu_2010"],
        "official_games": gate["official_games"],
        "wmt_layer": gate["wmt_layer"],
        "scientific_nonclaims": gate["scientific_nonclaims"],
    }
    payload_path = payload_root / "union_manifest.json"
    write_json(payload_path, payload)
    gate["payload"] = {
        "manifest": str(payload_path),
        "sha256": sha256_file(payload_path),
        "union_identity": gate["union_identity"],
    }
    write_json(repo_root / GATE_RELATIVE, gate)
    return {"gate": gate, "payload": gate["payload"]}


def validate_compact_union_gate(committed: Mapping[str, Any], contract: Mapping[str, Any]) -> None:
    if committed.get("schema_version") != SCHEMA_VERSION:
        raise AuthorityViolation("schema version drift")
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("classification drift")
    if committed.get("result") != PASS_RESULT:
        raise AuthorityViolation("result drift")
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("source_id") != SOURCE_ID:
        raise AuthorityViolation("source id drift")
    if committed.get("contract_id") != contract["contract_id"]:
        raise AuthorityViolation("contract id drift")
    if committed.get("authority") != expected_authority():
        raise AuthorityViolation("authority nonclaim drift")
    if committed.get("scientific_nonclaims") != expected_scientific_nonclaims():
        raise AuthorityViolation("scientific nonclaim drift")
    if committed.get("admissions") != expected_admissions():
        raise AuthorityViolation("admission drift")
    identities = committed.get("upstream_identities") or {}
    if identities.get("wmt_dataset_identity") != WMT_DATASET_IDENTITY:
        raise AuthorityViolation("WMT dataset identity was rewritten")
    if identities.get("boxscore_gate_identity") != BOXSCORE_GATE_IDENTITY:
        raise AuthorityViolation("BAT-580 boxscore identity drifted")
    if identities.get("bat570_matrix_identity") != BAT570_MATRIX_IDENTITY:
        raise AuthorityViolation("BAT-570 matrix identity drifted")
    if identities.get("protected_split_registry_sha256") != REGISTRY_SHA256:
        raise AuthorityViolation("protected registry SHA drifted")
    counts = committed.get("counts") or {}
    if counts.get("ncaa_contest_ids_created") != 0:
        raise AuthorityViolation("NCAA contest IDs were invented")
    if counts.get("official_added_total") != 26:
        raise AuthorityViolation("official added-game count drifted")
    if counts.get("wmt_preserved_games") != WMT_TARGET_GAMES:
        raise AuthorityViolation("WMT preserved-game count drifted")
    if counts.get("duplicates_detected") != 0:
        raise AuthorityViolation("duplicate official/WMT games were accepted")
    if counts.get("union_captured_games") != counts.get("wmt_preserved_games") + counts.get("official_added_total"):
        raise AuthorityViolation("union captured-game arithmetic drifted")
    games = committed.get("official_games") or []
    if len(games) != 26:
        raise AuthorityViolation("official compact game count drifted")
    if any(item.get("ncaa_contest_id") for item in games):
        raise AuthorityViolation("NCAA contest IDs were invented")
    if any(item.get("availability_claim") for item in games):
        raise AuthorityViolation("availability was claimed")
    if any(item.get("historical_publication_time") is not None for item in games):
        raise AuthorityViolation("retrieval time was used as historical publication time")
    texas = committed.get("texas_2011") or {}
    if texas.get("disposition") != TEXAS_DISPOSITION or texas.get("resolved") is not True:
        raise AuthorityViolation("2011 Texas official strong tuple was not bound")
    if texas.get("name_only_promotion") or texas.get("discrepancy_erased"):
        raise AuthorityViolation("2011 Texas Sidearm conflict was erased or name-only promoted")
    if texas.get("sidearm_or_gap_matrix_date") != "2011-11-25":
        raise AuthorityViolation("incorrect Sidearm 2011-11-25 value was discarded")
    if texas.get("official_school_date") != "2011-11-24":
        raise AuthorityViolation("official 2011 Texas date drifted")
    lsu = committed.get("lsu_2010") or {}
    if lsu.get("disposition") != LSU_DISPOSITION or lsu.get("silently_normalized"):
        raise AuthorityViolation("2010 LSU date conflict was silently normalized")
    if lsu.get("football_season") != 2010 or lsu.get("calendar_date") != "2011-01-07":
        raise AuthorityViolation("2010 LSU season/calendar split drifted")
    if committed.get("wmt_layer", {}).get("dataset_identity") != WMT_DATASET_IDENTITY:
        raise AuthorityViolation("WMT layer identity was rewritten")
    if committed.get("bat570_supersession", {}).get("parquet_mutated_in_place"):
        raise AuthorityViolation("BAT-570 parquet was mutated in place")
    if compute_gate_identity(committed) != committed.get("gate_identity"):
        raise AuthorityViolation("gate identity does not reconstruct")


def validate_artifact(
    *,
    data_root: Path,
    repo_root: Path,
    require_rebuild: bool = True,
    gate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    committed = dict(gate or load_json(repo_root / GATE_RELATIVE))
    contract = load_contract(repo_root)
    validate_compact_union_gate(committed, contract)
    historical = load_json(repo_root / HISTORICAL_GATE_RELATIVE)
    if historical["candidate_layer"]["dataset_identity"] != WMT_DATASET_IDENTITY:
        raise AuthorityViolation("historical WMT gate was mutated in place")
    wmt_root = data_root / contract["payloads"]["wmt_gamebook_root"]
    lake_ready = (wmt_root / "domain=game" / "candidate_records.parquet").is_file()
    if require_rebuild and not lake_ready:
        raise AuthorityViolation("external WMT reconstruction was required but the data root is not mounted")
    if lake_ready:
        rebuilt = rebuild_expected(data_root=data_root, repo_root=repo_root)
        if rebuilt["gate"]["gate_identity"] != committed.get("gate_identity"):
            raise AuthorityViolation("rebuilt union gate identity drifted")
        if rebuilt["gate"]["union_identity"] != committed.get("union_identity"):
            raise AuthorityViolation("rebuilt union identity drifted")
        if rebuilt["gate"]["official_games"] != committed.get("official_games"):
            raise AuthorityViolation("official compact games were not independently reconstructed")
        if rebuilt["wmt_mount"] != "MOUNTED":
            raise AuthorityViolation("WMT payload was expected to be mounted")
    return {
        "result": "PASS",
        "gate_identity": committed["gate_identity"],
        "union_identity": committed.get("union_identity"),
        "counts": committed.get("counts"),
        "external_reconstruction": "MOUNTED" if lake_ready else "NOT_MOUNTED",
    }


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))

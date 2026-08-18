from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import (
    canonical_json_bytes,
    normalize_team_name,
    parse_tamu_sidearm_schedule_page,
    sha256_file,
    stable_hash,
)

SCHEMA_VERSION = "aggie.data.tamu_official_evidence_gap_matrix.v1"
CONTRACT_RELATIVE = "configs/tamu_official_evidence_gap_matrix_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_evidence_gap_matrix_gate.json"
CONTRACT_ID = "BAT-570-TAMU-OFFICIAL-EVIDENCE-GAP-MATRIX-V1"
PASS_RESULT = "PASS_IDENTITY_BOUND_GAP_MATRIX_ACQUISITION_GAPS_REMAIN"
PASS_CLASSIFICATION = "TAMU_OFFICIAL_EVIDENCE_GAP_MATRIX_NO_COMPLETENESS_CLAIM"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
AUBURN_SEEDS = frozenset({"136982", "16591"})
TAMU_2010_TEAM_SEASON = "137387"
TAMU_2011_TEAM_SEASON = "137872"
NON_AUTHORITATIVE_METADATA = ("issued_at_utc",)
DOMAIN_COLUMNS = (
    "linescore_game_info",
    "venue",
    "attendance",
    "officials",
    "team_statistics",
    "team_statistics_by_period",
    "player_statistics",
    "drives",
    "play_by_play",
    "scoring_summary",
    "participation",
    "roster_membership",
    "pregame_availability",
)
NCAA_ENDPOINTS = (
    "box_score",
    "play_by_play",
    "drives",
    "team_stats",
    "individual_stats",
    "officials",
)
GATE_IDENTITY_FIELDS = (
    "schema_version",
    "artifact_type",
    "result",
    "classification",
    "contract_id",
    "decision_unit",
    "jira_key",
    "input_identities",
    "matrix_identity",
    "counts",
    "special_path",
    "ncaa_lake_notes",
    "admissions",
    "authority",
    "scientific_nonclaims",
    "remaining_blockers",
    "issue_completion",
    "contest_ids_fabricated",
)


class AuthorityViolation(ValueError):
    """Raised when the matrix is asked to claim completeness or invent identity."""


def load_contract(repo_root: Path) -> dict[str, Any]:
    path = repo_root / CONTRACT_RELATIVE
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise AuthorityViolation("gap-matrix contract identity drift")
    authority = contract.get("authority") or {}
    for key, expected in (
        ("completeness_claim", False),
        ("contest_id_fabrication", False),
        ("name_only_promotion", False),
        ("historical_known_at_from_capture_time", False),
        ("participation_as_availability", False),
        ("protected_evaluation_admission", False),
        ("protected_outcome_authority", False),
        ("champion_or_production_promotion", False),
        ("tamu_specialization_lift_claims", False),
    ):
        if authority.get(key) is not expected:
            raise AuthorityViolation(f"contract authority {key} is not fail-closed")
    notes = contract.get("ncaa_lake_notes") or {}
    if notes.get("auburn_contract_seed_2010") in {TAMU_2010_TEAM_SEASON, TAMU_2011_TEAM_SEASON}:
        raise AuthorityViolation("Auburn seed mislabeled as TAMU")
    if notes.get("auburn_contract_seed_2011") in {TAMU_2010_TEAM_SEASON, TAMU_2011_TEAM_SEASON}:
        raise AuthorityViolation("Auburn seed mislabeled as TAMU")
    return contract


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_file(path: Path, expected_sha256: str, context: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"{context} is missing: {path}")
    digest = sha256_file(path)
    if digest.lower() != expected_sha256.lower():
        raise ValueError(f"{context} hash drift: {digest}")
    return {"path": str(path), "sha256": digest, "bytes": path.stat().st_size}


def missing_endpoint_document(*, contest_id: str | None = None) -> dict[str, Any]:
    return {
        endpoint_id: {
            "endpoint_id": endpoint_id,
            "contest_id": contest_id,
            "cache_present": False,
            "acquisition_state": "NOT_ACQUIRED_TAMU_TRANCHE_DEFERRED",
            "remaining_blocker": "NCAA_CONTEST_ID_ABSENT_OR_UNACQUIRED",
        }
        for endpoint_id in NCAA_ENDPOINTS
    }


def empty_domains(*, present: tuple[str, ...] = ()) -> dict[str, Any]:
    present_set = set(present)
    return {
        domain: {
            "present": domain in present_set,
            "state": "PRESENT_CANDIDATE" if domain in present_set else "MISSING",
            "pregame_available": False,
        }
        for domain in DOMAIN_COLUMNS
    }


def expected_authority() -> dict[str, bool]:
    return {
        "completeness_claim": False,
        "contest_id_fabrication": False,
        "name_only_promotion": False,
        "historical_known_at_from_capture_time": False,
        "participation_as_availability": False,
        "membership_as_availability": False,
        "historical_pit_admission": False,
        "preliminary_training_admission": False,
        "protected_training_admission": False,
        "protected_evaluation_admission": False,
        "protected_outcome_authority": False,
        "champion_or_production_promotion": False,
        "forecast_publication": False,
        "tamu_specialization_lift_claims": False,
        "bas_or_aggie_excess_claims": False,
    }


def expected_scientific_nonclaims() -> dict[str, bool]:
    return {
        "completeness_claimed": False,
        "historical_known_at_established": False,
        "historical_population_ready": False,
        "pregame_availability_admitted": False,
        "protected_lane_opened": False,
        "protected_evaluation_admitted": False,
        "protected_outcome_authority": False,
        "protected_performance_claimed": False,
        "champion_or_production_promotion": False,
        "tamu_specialization_lift_claimed": False,
        "bas_or_aggie_excess_result_claimed": False,
        "trained_production_champion": False,
        "contest_ids_fabricated": False,
    }


def expected_admissions() -> dict[str, str]:
    return {
        "matrix_admission": "CANDIDATE_GAP_MATRIX_ONLY",
        "ncaa_tamu_2010_2011_tranche": "NOT_ACQUIRED",
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "historical_known_at": "UNKNOWN_CAPTURE_TIME_ONLY",
    }


def expected_remaining_blockers() -> list[str]:
    return [
        "NCAA_CONTEST_IDS_EMPTY_FOR_TAMU_2010_2011",
        "NCAA_ENDPOINTS_UNACQUIRED_FOR_TAMU",
        "NO_PREGAME_AVAILABILITY_EVIDENCE",
        "MEMBERSHIP_IS_NOT_AVAILABILITY",
        "PARTICIPATION_IS_NOT_AVAILABILITY",
        "CAPTURE_TIME_IS_NOT_HISTORICAL_KNOWN_AT",
        "NAME_ONLY_PROMOTION_FORBIDDEN",
        "TEAM_BOX_PLAYER_BOX_NOT_JOINED_WITHOUT_CANONICAL_GAME_ID",
        "PHASE_4_TAMU_TRANCHE_NOT_STARTED",
    ]


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    return stable_hash({key: gate[key] for key in GATE_IDENTITY_FIELDS if key in gate})


def compute_matrix_identity(rows: list[Mapping[str, Any]]) -> str:
    return stable_hash(
        {
            "row_identities": [row["row_identity"] for row in rows],
            "contest_ids_fabricated": any(row.get("contest_id_fabricated") for row in rows),
        }
    )


def _write_bytes_immutable(payload: bytes, path: Path, *, artifact: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"immutable {artifact} collision: {path}")
        return
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("TAMU official-evidence gap matrix requires the optional data-engineering environment") from exc
    return polars


def _load_ncaa_tamu_legacy(data_root: Path, contract: Mapping[str, Any]) -> dict[int, dict[str, Any]]:
    identities = contract["identities"]
    notes = contract["ncaa_lake_notes"]
    wanted = {
        2010: (identities["ncaa_discovery_2010_identity"], notes["tamu_2010_team_season_id"]),
        2011: (identities["ncaa_discovery_2011_identity"], notes["tamu_2011_team_season_id"]),
    }
    result: dict[int, dict[str, Any]] = {}
    for season, (discovery_identity, team_season_id) in wanted.items():
        if team_season_id in AUBURN_SEEDS:
            raise AuthorityViolation(f"refusing Auburn seed {team_season_id} as TAMU")
        path = (
            data_root
            / "manifests/acquisition/BAT-554-NCAA-OFFICIAL-BOUNDED-V1/discovery"
            / str(season)
            / "sha256"
            / discovery_identity
            / "ncaa_team_graph_discovery_manifest.json"
        )
        doc = load_json(path)
        if str(doc.get("seed_team_season_id")) in {notes["tamu_2010_team_season_id"], notes["tamu_2011_team_season_id"]}:
            raise AuthorityViolation("discovery seed is TAMU; contract seeds must remain Auburn")
        if str(doc.get("seed_team_season_id")) not in AUBURN_SEEDS:
            raise AuthorityViolation("discovery seed is not the pinned Auburn contract seed")
        capture = next(
            (
                row
                for row in doc.get("captures") or []
                if str(row.get("team_season_id")) == str(team_season_id)
            ),
            None,
        )
        if capture is None:
            raise FileNotFoundError(f"dedicated TAMU NCAA capture missing for {season} {team_season_id}")
        records = list(capture.get("legacy_schedule_records") or [])
        if any(record.get("contest_id") for record in records):
            raise AuthorityViolation("unexpected fabricated or present NCAA contest ID on TAMU 2010-2011 capture")
        result[season] = {
            "team_season_id": str(team_season_id),
            "discovery_identity": discovery_identity,
            "legacy_schedule_record_count": int(capture.get("legacy_schedule_record_count") or len(records)),
            "contest_ids": list(capture.get("contest_ids") or []),
            "records": records,
            "dedicated_capture": True,
        }
    return result


def _reconcile_sidearm_to_ncaa(
    sidearm: Mapping[str, Any], ncaa_records: list[Mapping[str, Any]]
) -> dict[str, Any]:
    date_score: list[Mapping[str, Any]] = []
    name_only: list[Mapping[str, Any]] = []
    for record in ncaa_records:
        name_match = normalize_team_name(str(record.get("opponent_display_name") or "")) == sidearm[
            "opponent_team_name_normalized"
        ]
        date_match = str(record.get("game_date") or "") == sidearm["source_schedule_date"]
        score_match = (
            record.get("score_for") == sidearm["source_team_points"]
            and record.get("score_against") == sidearm["opponent_points"]
        )
        if date_match and score_match:
            date_score.append(record)
        elif name_match and not (date_match and score_match):
            name_only.append(record)
    if len(date_score) == 1:
        chosen = date_score[0]
        name_match = normalize_team_name(str(chosen.get("opponent_display_name") or "")) == sidearm[
            "opponent_team_name_normalized"
        ]
        conflicts: list[str] = []
        if not name_match:
            conflicts.append("DATE_SCORE_MATCH_OPPONENT_NAME_CONFLICT")
        if str(chosen.get("site_hint") or "") == "AWAY" and sidearm["venue_state"] != "AWAY":
            conflicts.append("NCAA_SITE_HINT_AWAY_CONFLICTS_WITH_SIDEARM_VENUE")
        if chosen.get("contest_id"):
            raise AuthorityViolation("NCAA legacy row unexpectedly carries a contest ID")
        return {
            "ncaa_contest_exposure": "LEGACY_SCHEDULE_ROW_NO_CONTEST_ID",
            "candidate_contest_ids": [],
            "reconciliation_state": (
                "EXACT_DATE_SCORE_OPPONENT_CANDIDATE"
                if name_match and not conflicts
                else "EXACT_DATE_SCORE_CANDIDATE_WITH_EXPLICIT_CONFLICT"
            ),
            "ncaa_source_row_sha256": chosen.get("source_row_sha256"),
            "ncaa_opponent_display_name": chosen.get("opponent_display_name"),
            "ncaa_opponent_team_season_id": chosen.get("opponent_team_season_id"),
            "name_only_promotion": False,
            "conflicts": conflicts,
        }
    if len(date_score) > 1:
        return {
            "ncaa_contest_exposure": "AMBIGUOUS_DATE_SCORE_CANDIDATES_NO_CONTEST_ID",
            "candidate_contest_ids": [],
            "reconciliation_state": "AMBIGUOUS",
            "ncaa_source_row_sha256": None,
            "ncaa_opponent_display_name": None,
            "ncaa_opponent_team_season_id": None,
            "name_only_promotion": False,
            "conflicts": ["DUPLICATE_DATE_SCORE_CANDIDATES"],
        }
    if name_only:
        return {
            "ncaa_contest_exposure": "NAME_ONLY_CANDIDATE_NOT_PROMOTED",
            "candidate_contest_ids": [],
            "reconciliation_state": "UNRESOLVED_NAME_ONLY_NOT_PROMOTED",
            "ncaa_source_row_sha256": None,
            "ncaa_opponent_display_name": None,
            "ncaa_opponent_team_season_id": None,
            "name_only_promotion": False,
            "conflicts": ["NAME_ONLY_MATCH_SUPPRESSED"],
        }
    return {
        "ncaa_contest_exposure": "UNRESOLVED_NO_CONTEST_ID",
        "candidate_contest_ids": [],
        "reconciliation_state": "UNRESOLVED",
        "ncaa_source_row_sha256": None,
        "ncaa_opponent_display_name": None,
        "ncaa_opponent_team_season_id": None,
        "name_only_promotion": False,
        "conflicts": [],
    }


def _domain_from_wmt_game(fields: Mapping[str, Any], coverage: Mapping[str, int]) -> dict[str, Any]:
    present = ["linescore_game_info"]
    if fields.get("venue"):
        present.append("venue")
    if fields.get("attendance") not in {None, ""}:
        present.append("attendance")
    if coverage.get("teams", 0) > 0:
        present.append("team_statistics")
    if coverage.get("players", 0) > 0:
        present.extend(["player_statistics", "participation"])
    if coverage.get("drives", 0) > 0:
        present.append("drives")
    if coverage.get("plays", 0) > 0:
        present.append("play_by_play")
    if coverage.get("actions", 0) > 0:
        present.append("scoring_summary")
    domains = empty_domains(present=tuple(present))
    domains["roster_membership"]["state"] = "SEASON_MEMBERSHIP_NOT_GAME_AVAILABILITY"
    domains["pregame_availability"]["state"] = "UNKNOWN_NO_TIMESTAMPED_PREGAME_EVIDENCE"
    return domains


def _sidearm_domains() -> dict[str, Any]:
    domains = empty_domains(present=("linescore_game_info", "venue"))
    domains["linescore_game_info"]["state"] = "SCHEDULE_METADATA_ONLY"
    domains["venue"]["state"] = "SIDEARM_VS_OR_AT_ONLY"
    domains["roster_membership"]["state"] = "SEASON_MEMBERSHIP_NOT_GAME_AVAILABILITY"
    domains["pregame_availability"]["state"] = "UNKNOWN_NO_TIMESTAMPED_PREGAME_EVIDENCE"
    return domains


def _load_wmt_coverage(data_root: Path, contract: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, int]]]:
    pl = _polars()
    root = data_root / contract["payloads"]["gamebook_root"]
    games = pl.read_parquet(root / "domain=game" / "candidate_records.parquet").to_dicts()
    coverage: dict[str, dict[str, int]] = {}
    for domain in ("teams", "players", "drives", "plays", "actions"):
        path = root / f"domain={domain}" / "candidate_records.parquet"
        if not path.is_file():
            continue
        frame = pl.read_parquet(path).select("boxscore_id")
        for boxscore_id, count in frame.group_by("boxscore_id").len().iter_rows():
            coverage.setdefault(str(boxscore_id), {})[domain] = int(count)
    competitors_path = root / "domain=competitors" / "candidate_records.parquet"
    opponents: dict[str, str] = {}
    if competitors_path.is_file():
        for row in pl.read_parquet(competitors_path).to_dicts():
            fields = json.loads(row["selected_fields_json"])
            name = str(fields.get("name_tabular") or "")
            if normalize_team_name(name) == normalize_team_name("Texas A&M"):
                continue
            if name:
                opponents[str(row["boxscore_id"])] = name
    for game in games:
        game["_opponent_name"] = opponents.get(str(game["boxscore_id"]))
        game["_coverage"] = coverage.get(str(game["boxscore_id"]), {})
    return games, coverage


def build_matrix_rows(
    *,
    data_root: Path,
    repo_root: Path,
    contract: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    contract = contract or load_contract(repo_root)
    identities = contract["identities"]
    ncaa = _load_ncaa_tamu_legacy(data_root, contract)
    rows: list[dict[str, Any]] = []
    for season in (2010, 2011):
        relative = contract["sidearm_schedule_html"][str(season)]
        path = data_root / relative
        expected = identities[f"sidearm_schedule_html_{season}_sha256"]
        verify_file(path, expected, f"Sidearm {season} schedule HTML")
        payload = path.read_text(encoding="utf-8", errors="replace")
        page, parsed = parse_tamu_sidearm_schedule_page(
            payload, season_title_year=season, raw_sha256=expected
        )
        if page["contest_ids_fabricated"] or any(item.get("contest_id") for item in parsed):
            raise AuthorityViolation("Sidearm parser fabricated a contest ID")
        if any(item.get("boxscore_id") for item in parsed):
            raise AuthorityViolation("Sidearm parser invented a boxscore ID")
        ncaa_bundle = ncaa[season]
        for item in parsed:
            recon = _reconcile_sidearm_to_ncaa(item, ncaa_bundle["records"])
            if item["contest_id"] is not None or recon["candidate_contest_ids"]:
                raise AuthorityViolation("2010-2011 contest IDs must remain empty")
            row = {
                "row_identity": item["legacy_source_row_identity"],
                "season": season,
                "source_lane": "WMT_SIDEARM_SCHEDULE",
                "game_date": item["source_schedule_date"],
                "opponent_name": item["opponent_team_name"],
                "opponent_name_normalized": item["opponent_team_name_normalized"],
                "venue_state": item["venue_state"],
                "source_result": item["source_result"],
                "source_team_points": item["source_team_points"],
                "opponent_points": item["opponent_points"],
                "wmt_exposure": "SCHEDULE_HTML_NO_BOXSCORE_LINK",
                "wmt_boxscore_id": None,
                "wmt_game_id": None,
                "contest_id": None,
                "boxscore_id": None,
                "contest_id_fabricated": False,
                "ncaa_team_season_id": ncaa_bundle["team_season_id"],
                "ncaa_contest_exposure": recon["ncaa_contest_exposure"],
                "candidate_contest_ids": [],
                "reconciliation_state": recon["reconciliation_state"],
                "name_only_promotion": False,
                "conflicts": recon["conflicts"],
                "domains": _sidearm_domains(),
                "ncaa_endpoints": missing_endpoint_document(),
                "team_box_join_state": "NOT_JOINED_NO_SHARED_CANONICAL_GAME_ID",
                "player_box_join_state": "NOT_JOINED_NO_SHARED_CANONICAL_GAME_ID",
                "historical_known_at_state": "UNKNOWN_CAPTURE_TIME_ONLY",
                "pregame_availability": False,
                "remaining_blockers": expected_remaining_blockers(),
                "source_row_sha256": item["source_row_sha256"],
                "source_page_raw_sha256": item["source_page_raw_sha256"],
            }
            rows.append(row)
    games, _coverage = _load_wmt_coverage(data_root, contract)
    unexpected_special_path = [game for game in games if int(game["season"]) in {2010, 2011}]
    if unexpected_special_path:
        raise AuthorityViolation(
            "WMT gamebook unexpectedly contains 2010-2011 rows; Sidearm special path is authoritative"
        )
    games = [game for game in games if 2012 <= int(game["season"]) <= 2025]
    if not games:
        raise AuthorityViolation("WMT gamebook 2012-2025 population is empty")
    for game in games:
        fields = json.loads(game["selected_fields_json"])
        season = int(game["season"])
        opponent = game.get("_opponent_name")
        domains = _domain_from_wmt_game(fields, game.get("_coverage") or {})
        row = {
            "row_identity": stable_hash(
                {
                    "source_lane": "WMT_GAMEBOOK",
                    "record_id": game["record_id"],
                    "source_record_sha256": game["source_record_sha256"],
                }
            ),
            "season": season,
            "source_lane": "WMT_GAMEBOOK",
            "game_date": str(game.get("game_date") or "")[:10],
            "opponent_name": opponent,
            "opponent_name_normalized": normalize_team_name(opponent) if opponent else None,
            "venue_state": "NEUTRAL" if fields.get("neutral_site") else "HOME_OR_AWAY_UNRESOLVED_IN_GAMEBOOK",
            "source_result": None,
            "source_team_points": None,
            "opponent_points": None,
            "wmt_exposure": "GAMEBOOK_OR_METADATA_CAPTURE",
            "wmt_boxscore_id": game.get("boxscore_id"),
            "wmt_game_id": game.get("wmt_game_id"),
            "contest_id": None,
            "boxscore_id": game.get("boxscore_id"),
            "contest_id_fabricated": False,
            "ncaa_team_season_id": None,
            "ncaa_contest_exposure": "NOT_SCANNED_OUTSIDE_2010_2011_SPECIAL_PATH",
            "candidate_contest_ids": [],
            "reconciliation_state": "UNRESOLVED_NO_NCAA_CONTEST_ID",
            "name_only_promotion": False,
            "conflicts": [],
            "domains": domains,
            "ncaa_endpoints": missing_endpoint_document(),
            "team_box_join_state": "NOT_JOINED_NO_SHARED_CANONICAL_GAME_ID",
            "player_box_join_state": "NOT_JOINED_NO_SHARED_CANONICAL_GAME_ID",
            "historical_known_at_state": str(game.get("historical_known_at_state") or "UNKNOWN_CAPTURE_TIME_ONLY"),
            "pregame_availability": False,
            "remaining_blockers": expected_remaining_blockers(),
            "source_row_sha256": game["source_record_sha256"],
            "source_page_raw_sha256": game.get("source_response_sha256"),
        }
        if row["historical_known_at_state"] in {"", "None"}:
            row["historical_known_at_state"] = "UNKNOWN_CAPTURE_TIME_ONLY"
        if "HISTORICAL_KNOWN_AT" in row["historical_known_at_state"] and "UNKNOWN" not in row["historical_known_at_state"]:
            raise AuthorityViolation("capture-time evidence must not be labeled historical known-at")
        rows.append(row)
    rows.sort(key=lambda item: (item["season"], item["game_date"], item["row_identity"]))
    if any(item.get("contest_id_fabricated") or item.get("contest_id") for item in rows):
        raise AuthorityViolation("matrix rows must not fabricate contest IDs")
    if any(item.get("name_only_promotion") for item in rows):
        raise AuthorityViolation("name-only promotion leaked into matrix rows")
    if any(item.get("pregame_availability") for item in rows):
        raise AuthorityViolation("pregame availability must remain false")
    if any(
        item["domains"]["pregame_availability"]["present"]
        or item["domains"]["participation"]["state"] == "PREGAME_AVAILABILITY"
        for item in rows
    ):
        raise AuthorityViolation("participation must not be relabeled availability")
    return rows


def special_path_fingerprint(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    subset = [row for row in rows if row["season"] in {2010, 2011}]
    contest_ids = [row.get("contest_id") for row in subset if row.get("contest_id")]
    return {
        "games_2010": sum(1 for row in subset if row["season"] == 2010),
        "games_2011": sum(1 for row in subset if row["season"] == 2011),
        "opponents": [row.get("opponent_name") for row in subset],
        "dates": [row.get("game_date") for row in subset],
        "contest_ids": contest_ids,
        "duplicate_contest_assignments": len(contest_ids) - len(set(contest_ids)),
        "name_only_promotions": sum(1 for row in subset if row.get("name_only_promotion")),
    }


def summarize_rows(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    by_season: dict[str, int] = {}
    for row in rows:
        key = str(row["season"])
        by_season[key] = by_season.get(key, 0) + 1
    return {
        "scheduled_games_2010_2025": len(rows),
        "games_2010": by_season.get("2010", 0),
        "games_2011": by_season.get("2011", 0),
        "games_2012_2025": sum(count for season, count in by_season.items() if int(season) >= 2012),
        "contest_ids_present": sum(1 for row in rows if row.get("contest_id")),
        "contest_ids_fabricated": sum(1 for row in rows if row.get("contest_id_fabricated")),
        "name_only_promotions": sum(1 for row in rows if row.get("name_only_promotion")),
        "pregame_availability_true": sum(1 for row in rows if row.get("pregame_availability")),
        "exact_2010_2011_candidates": sum(
            1
            for row in rows
            if row["season"] in {2010, 2011}
            and row["reconciliation_state"] == "EXACT_DATE_SCORE_OPPONENT_CANDIDATE"
        ),
        "unresolved_or_conflict_2010_2011": sum(
            1
            for row in rows
            if row["season"] in {2010, 2011}
            and row["reconciliation_state"] != "EXACT_DATE_SCORE_OPPONENT_CANDIDATE"
        ),
        "missing_ncaa_endpoints": len(rows) * len(NCAA_ENDPOINTS),
        "by_season": {key: by_season[key] for key in sorted(by_season, key=int)},
    }


def live_ncaa_lake_notes(contract: Mapping[str, Any], ncaa: Mapping[int, Mapping[str, Any]]) -> dict[str, Any]:
    notes = dict(contract["ncaa_lake_notes"])
    notes["tamu_2010_legacy_rows"] = ncaa[2010]["legacy_schedule_record_count"]
    notes["tamu_2011_legacy_rows"] = ncaa[2011]["legacy_schedule_record_count"]
    notes["tamu_2010_contest_ids"] = ncaa[2010]["contest_ids"]
    notes["tamu_2011_contest_ids"] = ncaa[2011]["contest_ids"]
    notes["tamu_2010_dedicated_capture"] = ncaa[2010]["dedicated_capture"]
    notes["tamu_2011_dedicated_capture"] = ncaa[2011]["dedicated_capture"]
    notes["auburn_seeds_treated_as_tamu"] = False
    return notes


def expected_input_identities(contract: Mapping[str, Any]) -> dict[str, str]:
    identities = contract["identities"]
    return {
        key: identities[key]
        for key in (
            "wmt_acquisition_identity",
            "wmt_reconciliation_dataset_identity",
            "team_box_snapshot_dataset_identity",
            "player_box_snapshot_dataset_identity",
            "ncaa_official_acquisition_identity",
            "roster_gate_identity",
            "protected_split_registry_sha256",
            "sidearm_schedule_html_2010_sha256",
            "sidearm_schedule_html_2011_sha256",
            "ncaa_discovery_2010_identity",
            "ncaa_discovery_2011_identity",
        )
    }


def verify_pinned_identities(data_root: Path, repo_root: Path, contract: Mapping[str, Any]) -> None:
    identities = contract["identities"]
    verify_file(
        repo_root / identities["protected_split_registry_relative_path"],
        identities["protected_split_registry_sha256"],
        "protected split registry",
    )
    roster = load_json(repo_root / identities["roster_gate_relative_path"])
    if roster.get("gate_identity") != identities["roster_gate_identity"]:
        raise ValueError("BAT-567 roster gate identity drift")
    team_box = load_json(repo_root / identities["team_box_snapshot_gate_relative_path"])
    if team_box.get("output_identities", {}).get("dataset") != identities["team_box_snapshot_dataset_identity"]:
        raise ValueError("BAT-548 team-box dataset identity drift")
    player_box = load_json(repo_root / identities["player_box_snapshot_gate_relative_path"])
    if player_box.get("output_identities", {}).get("dataset") != identities["player_box_snapshot_dataset_identity"]:
        raise ValueError("BAT-550 player-box dataset identity drift")
    ncaa_gate = load_json(repo_root / identities["ncaa_official_acquisition_gate_relative_path"])
    if ncaa_gate.get("manifest", {}).get("acquisition_identity") != identities["ncaa_official_acquisition_identity"]:
        raise ValueError("BAT-554 NCAA acquisition identity drift")
    if set(ncaa_gate.get("bounded_population", {}).get("contest_ids") or []) & {TAMU_2010_TEAM_SEASON, TAMU_2011_TEAM_SEASON}:
        raise AuthorityViolation("BAT-554 sample contest IDs collided with TAMU team-season IDs")
    acquire = load_json(data_root / identities["wmt_acquisition_manifest_relative_path"])
    if acquire.get("acquisition_identity") != identities["wmt_acquisition_identity"]:
        raise ValueError("BAT-523 WMT acquisition identity drift")
    recon_path = data_root / identities["wmt_reconciliation_manifest_relative_path"]
    if identities.get("wmt_reconciliation_manifest_sha256"):
        verify_file(
            recon_path,
            identities["wmt_reconciliation_manifest_sha256"],
            "BAT-523 WMT reconciliation manifest",
        )
    recon = load_json(recon_path)
    recon_identity = recon.get("dataset_identity") or (recon.get("candidate_layer") or {}).get(
        "dataset_identity"
    )
    if recon_identity != identities["wmt_reconciliation_dataset_identity"]:
        raise ValueError("BAT-523 WMT reconciliation dataset identity drift")


def expected_issue_completion(contract: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "jira_key": contract["jira_key"],
        "workflow_state": "DONE",
        "logical_state": "DONE",
        "maturity": "IMPLEMENTED",
        "evidence_state": "VERIFIED",
        "issue_complete": True,
        "acquisition_gaps_remain": True,
        "completeness_claimed": False,
    }


def expected_gate_document(expected: Mapping[str, Any]) -> dict[str, Any]:
    contract = expected["contract"]
    rows = expected["rows"]
    counts = summarize_rows(rows)
    if counts["contest_ids_fabricated"] or counts["contest_ids_present"]:
        raise AuthorityViolation("gate cannot admit fabricated or invented contest IDs")
    if counts["pregame_availability_true"]:
        raise AuthorityViolation("gate cannot admit pregame availability")
    if counts["games_2010"] < 1 or counts["games_2011"] < 1:
        raise AuthorityViolation("2010-2011 schedule rows missing")
    matrix_identity = compute_matrix_identity(rows)
    special_path = special_path_fingerprint(rows)
    if special_path["contest_ids"] or special_path["duplicate_contest_assignments"]:
        raise AuthorityViolation("2010-2011 special path must not assign contest IDs")
    if special_path["name_only_promotions"]:
        raise AuthorityViolation("2010-2011 special path silently promoted a name-only match")
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_EVIDENCE_GAP_MATRIX_GATE",
        "classification": PASS_CLASSIFICATION,
        "contract_id": contract["contract_id"],
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "result": PASS_RESULT,
        "input_identities": expected_input_identities(contract),
        "matrix_identity": matrix_identity,
        "counts": counts,
        "special_path": special_path,
        "ncaa_lake_notes": expected["ncaa_lake_notes"],
        "admissions": expected_admissions(),
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "remaining_blockers": expected_remaining_blockers(),
        "issue_completion": expected_issue_completion(contract),
        "contest_ids_fabricated": False,
        "protected_lane": PROTECTED_LANE,
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    return gate


def rebuild_expected(*, data_root: Path, repo_root: Path) -> dict[str, Any]:
    contract = load_contract(repo_root)
    verify_pinned_identities(data_root, repo_root, contract)
    ncaa = _load_ncaa_tamu_legacy(data_root, contract)
    rows = build_matrix_rows(data_root=data_root, repo_root=repo_root, contract=contract)
    expected = {
        "contract": contract,
        "rows": rows,
        "ncaa_lake_notes": live_ncaa_lake_notes(contract, ncaa),
    }
    expected["gate"] = expected_gate_document(expected)
    expected["matrix_identity"] = expected["gate"]["matrix_identity"]
    expected["gate_identity"] = expected["gate"]["gate_identity"]
    return expected


def write_matrix_payloads(
    *,
    data_root: Path,
    rows: list[Mapping[str, Any]],
    matrix_identity: str,
) -> dict[str, Any]:
    pl = _polars()
    root = data_root / "features" / "tamu_official_evidence_gap_matrix" / "sha256" / matrix_identity
    records = []
    for row in rows:
        records.append(
            {
                "row_identity": row["row_identity"],
                "season": int(row["season"]),
                "source_lane": row["source_lane"],
                "game_date": row["game_date"],
                "opponent_name": row.get("opponent_name"),
                "venue_state": row.get("venue_state"),
                "wmt_exposure": row.get("wmt_exposure"),
                "wmt_boxscore_id": row.get("wmt_boxscore_id"),
                "contest_id": row.get("contest_id"),
                "boxscore_id": row.get("boxscore_id"),
                "contest_id_fabricated": bool(row.get("contest_id_fabricated")),
                "ncaa_team_season_id": row.get("ncaa_team_season_id"),
                "ncaa_contest_exposure": row.get("ncaa_contest_exposure"),
                "reconciliation_state": row.get("reconciliation_state"),
                "name_only_promotion": bool(row.get("name_only_promotion")),
                "pregame_availability": bool(row.get("pregame_availability")),
                "historical_known_at_state": row.get("historical_known_at_state"),
                "domains_json": json.dumps(row["domains"], sort_keys=True, separators=(",", ":")),
                "ncaa_endpoints_json": json.dumps(row["ncaa_endpoints"], sort_keys=True, separators=(",", ":")),
                "conflicts_json": json.dumps(row.get("conflicts") or [], sort_keys=True, separators=(",", ":")),
                "remaining_blockers_json": json.dumps(row.get("remaining_blockers") or [], sort_keys=True, separators=(",", ":")),
                "source_row_sha256": row.get("source_row_sha256"),
                "source_page_raw_sha256": row.get("source_page_raw_sha256"),
            }
        )
    frame = pl.DataFrame(records)
    payload_path = root / "game_rows.parquet"
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(payload_path, compression="zstd", statistics=True)
    digest = sha256_file(payload_path)
    manifest = {
        "matrix_identity": matrix_identity,
        "row_count": len(records),
        "payload": "game_rows.parquet",
        "sha256": digest,
        "bytes": payload_path.stat().st_size,
    }
    _write_bytes_immutable(
        canonical_json_bytes(manifest) + b"\n",
        root / "matrix_manifest.json",
        artifact="gap-matrix manifest",
    )
    return {"root": str(root), "payload": str(payload_path), "sha256": digest, "rows": len(records)}


def materialize(
    *,
    data_root: Path,
    repo_root: Path,
    issued_at_utc: str,
) -> dict[str, Any]:
    expected = rebuild_expected(data_root=data_root, repo_root=repo_root)
    gate = dict(expected["gate"])
    gate["issued_at_utc"] = issued_at_utc
    payload = write_matrix_payloads(
        data_root=data_root,
        rows=expected["rows"],
        matrix_identity=expected["matrix_identity"],
    )
    gate["payload"] = payload
    gate_path = repo_root / GATE_RELATIVE
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {
        "gate_path": str(gate_path),
        "gate_identity": gate["gate_identity"],
        "matrix_identity": gate["matrix_identity"],
        "counts": gate["counts"],
        "payload": payload,
    }


def validate_artifact(
    *,
    data_root: Path,
    repo_root: Path,
    require_rebuild: bool = True,
    gate: Mapping[str, Any] | None = None,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    expected = dict(expected) if expected is not None else rebuild_expected(data_root=data_root, repo_root=repo_root)
    rebuilt = expected_gate_document(expected)
    live_artifact = gate is None
    if live_artifact:
        gate = load_json(repo_root / GATE_RELATIVE)
    observed = {key: gate[key] for key in GATE_IDENTITY_FIELDS if key in gate}
    desired = {key: rebuilt[key] for key in GATE_IDENTITY_FIELDS}
    if observed != desired:
        raise AuthorityViolation("gap-matrix gate drifted from rebuilt identity-bound document")
    if gate.get("gate_identity") != compute_gate_identity(gate):
        raise AuthorityViolation("forged terminal state after rehash")
    if gate.get("contest_ids_fabricated") is not False:
        raise AuthorityViolation("contest IDs were fabricated")
    if gate.get("counts", {}).get("contest_ids_present"):
        raise AuthorityViolation("matrix reports contest IDs that were not acquired")
    if gate.get("scientific_nonclaims", {}).get("contest_ids_fabricated"):
        raise AuthorityViolation("scientific nonclaim inverted")
    if gate.get("admissions", {}).get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane must remain blocked")
    if gate.get("authority", {}).get("protected_outcome_authority"):
        raise AuthorityViolation("protected outcome authority is not granted")
    if gate.get("authority", {}).get("historical_known_at_from_capture_time"):
        raise AuthorityViolation("capture time is not historical known-at")
    if gate.get("authority", {}).get("participation_as_availability"):
        raise AuthorityViolation("participation is not availability")
    if gate.get("counts", {}).get("missing_ncaa_endpoints", 0) < len(expected["rows"]) * len(NCAA_ENDPOINTS):
        raise AuthorityViolation("missing NCAA endpoints were omitted")
    if gate.get("counts", {}).get("scheduled_games_2010_2025", 0) > len(expected["rows"]):
        raise AuthorityViolation("inflated coverage")
    if require_rebuild and expected.get("matrix_identity") != rebuilt["matrix_identity"]:
        raise AuthorityViolation("matrix identity rebuild mismatch")
    if live_artifact:
        payload_root = (
            data_root
            / "features"
            / "tamu_official_evidence_gap_matrix"
            / "sha256"
            / rebuilt["matrix_identity"]
            / "game_rows.parquet"
        )
        if not payload_root.is_file():
            raise FileNotFoundError("gap-matrix payload is missing")
    return {"result": "PASS", "gate_identity": rebuilt["gate_identity"], "matrix_identity": rebuilt["matrix_identity"]}

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

from aggie_analytics.data.national_foundation_reconciliation import (
    binding_identity,
    canonical_json_bytes,
    manifest_authoritative_sha256,
    sha256_file,
    stable_hash,
)

# National domain coverage and point-in-time admission matrix.
#
# Every candidate national feature domain is scored against the BAT-652 tiered
# spine population. A domain is admitted only when its known-at basis survives
# without appealing to a capture timestamp. Admission is deliberately partial:
# the unadmitted domains stay visible in the matrix instead of disappearing.

SCHEMA_VERSION = "aggie.data.national_pit_domain_admission_matrix.v1"
CONTRACT_RELATIVE = "configs/national_pit_domain_admission_matrix_contract.json"
CONTRACT_ID = "BAT-653-NATIONAL-PIT-DOMAIN-ADMISSION-MATRIX-V1"
GATE_RELATIVE = "artifacts/data_lake/national_pit_domain_admission_matrix_gate.json"
PASS_RESULT = "PASS_NATIONAL_PIT_DOMAIN_ADMISSION_MATRIX_PARTIAL_ADMISSION"
CLASSIFICATION = "NATIONAL_DOMAIN_COVERAGE_AND_PIT_ADMISSION_MATRIX"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"

AP_POLL_TOKEN = "ap top"
COACHES_POLL_TOKEN = "coaches"

GATE_IDENTITY_FIELDS = (
    "admission_matrix",
    "admitted_feature_registry",
    "artifact_type",
    "authority",
    "classification",
    "contract_id",
    "contract_sha256",
    "dataset_identity",
    "decision_unit",
    "feature_missingness",
    "jira_key",
    "leakage_checks",
    "manifest",
    "parent_jira_key",
    "payloads",
    "population",
    "protected_lane",
    "quarantined_fields",
    "result",
    "schema_version",
    "scientific_nonclaims",
    "source_identities",
    "tamu_share",
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) + b"\n" for row in rows)


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _require_file(path: Path, expected_sha256: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"missing pinned input: {path}")
    if sha256_file(path) != expected_sha256:
        raise ValueError(f"pinned input SHA-256 drift: {path}")


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 12)


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    return stable_hash({field: gate[field] for field in GATE_IDENTITY_FIELDS})


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = _read_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("national PIT domain matrix contract identity drift")
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("national PIT domain matrix schema drift")
    if contract.get("protected_lane") != PROTECTED_LANE:
        raise ValueError("protected lane must remain blocked")
    authority = contract["authority"]
    if authority.get("national_domain_matrix_use") is not True:
        raise ValueError("national domain matrix authority is not enabled")
    for key in (
        "historical_pit_admission",
        "protected_training_admission",
        "protected_evaluation_admission",
        "champion_or_production_promotion",
        "protected_performance_claims",
        "forecast_publication",
        "immutable_raw_capture_mutation",
        "canonical_entity_mutation",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"national domain matrix authority is open: {key}")
    rules = contract["admission_rules"]
    for key in (
        "capture_timestamp_is_never_a_known_at_basis",
        "membership_is_never_availability",
        "postgame_grain_is_never_pregame_evidence",
        "unranked_is_never_imputed_as_a_rank",
        "missingness_is_always_indicated_never_filled",
        "same_game_evidence_is_always_excluded_from_that_game",
    ):
        if rules.get(key) is not True:
            raise ValueError(f"admission rule is disabled: {key}")
    declared = {item["domain_id"] for item in contract["domains"]}
    for feature in contract["admitted_feature_registry"]:
        if feature["domain_id"] not in declared:
            raise ValueError(f"feature references an undeclared domain: {feature['feature_id']}")
    admitted = {item["domain_id"] for item in contract["domains"] if item["decision"] == "ADMITTED"}
    for feature in contract["admitted_feature_registry"]:
        if feature["domain_id"] not in admitted:
            raise ValueError(
                f"admitted feature draws on an unadmitted domain: {feature['feature_id']}"
            )
    return contract


def season_type_ordinal(season_type: str | None) -> int:
    return 1 if str(season_type or "regular").lower() == "postseason" else 0


def week_ordinal(season: int, season_type: str | None, week: Any) -> tuple[int, int, int]:
    return (int(season), season_type_ordinal(season_type), int(week or 0))


def _load_spine_rows(data_root: Path, gate: Mapping[str, Any], name: str) -> list[dict[str, Any]]:
    entry = next(item for item in gate["payloads"] if item["name"] == name)
    manifest = _read_json(data_root / gate["manifest"]["relative_path"])
    located = next(item for item in manifest["payloads"] if item["name"] == name)
    payload = (data_root / located["relative_path"]).read_bytes()
    if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
        raise ValueError(f"spine payload hash drift: {name}")
    return [json.loads(line) for line in payload.splitlines() if line.strip()]


def _manifest_entries(manifest: Mapping[str, Any], domain_use: str) -> list[Mapping[str, Any]]:
    return [
        entry
        for entry in manifest["snapshot_index"]
        if domain_use in entry["coverage"].get("domain_uses", [])
    ]


def _schema_identity(entry: Mapping[str, Any]) -> str:
    """Source routes name their schema digest differently; both are authoritative."""
    schema = entry["parser_and_schema"]
    for key in ("schema_sha256", "top_level_schema_sha256"):
        value = schema.get(key)
        if value:
            return str(value)
    raise ValueError("capture declares no schema identity")


def _load_capture_rows(data_root: Path, entry: Mapping[str, Any]) -> list[Any]:
    path = data_root / entry["content_identity"]["external_relative_path"]
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != entry["content_identity"]["sha256"]:
        raise ValueError(f"raw capture rehash drift: {entry['content_identity']['sha256']}")
    return json.loads(payload.decode("utf-8"))


def build_rankings_index(
    data_root: Path, manifest: Mapping[str, Any]
) -> tuple[dict[int, list[tuple[tuple[int, int, int], dict[str, dict[int, int]]]]], dict[str, Any]]:
    """Map every season to its poll snapshots ordered by week ordinal."""
    index: dict[int, list[tuple[tuple[int, int, int], dict[str, dict[int, int]]]]] = defaultdict(
        list
    )
    stats = Counter()
    schema_ids: set[str] = set()
    for entry in sorted(
        _manifest_entries(manifest, "rankings"),
        key=lambda item: item["content_identity"]["sha256"],
    ):
        schema_ids.add(_schema_identity(entry))
        for snapshot in _load_capture_rows(data_root, entry):
            season = int(snapshot["season"])
            ordinal = week_ordinal(season, snapshot.get("seasonType"), snapshot.get("week"))
            polls: dict[str, dict[int, int]] = {}
            for poll in snapshot.get("polls") or []:
                name = str(poll.get("poll") or "").lower()
                if AP_POLL_TOKEN in name:
                    key = "ap"
                elif COACHES_POLL_TOKEN in name:
                    key = "coaches"
                else:
                    stats["unmapped_polls"] += 1
                    continue
                ranks = {}
                for rank in poll.get("ranks") or []:
                    team_id = rank.get("teamId")
                    if team_id is None:
                        stats["rank_rows_without_team_id"] += 1
                        continue
                    ranks[int(team_id)] = int(rank["rank"])
                    stats["rank_rows"] += 1
                polls[key] = ranks
            index[season].append((ordinal, polls))
            stats["poll_snapshots"] += 1
    for season in index:
        index[season].sort(key=lambda item: item[0])
    return dict(index), {
        "poll_snapshots": int(stats["poll_snapshots"]),
        "rank_rows": int(stats["rank_rows"]),
        "unmapped_polls": int(stats["unmapped_polls"]),
        "rank_rows_without_team_id": int(stats["rank_rows_without_team_id"]),
        "schema_identities": sorted(schema_ids),
    }


def lookup_prior_poll(
    snapshots: list[tuple[tuple[int, int, int], dict[str, dict[int, int]]]],
    ordinal: tuple[int, int, int],
) -> dict[str, dict[int, int]] | None:
    """Return the latest poll strictly before the game's own week ordinal."""
    chosen: dict[str, dict[int, int]] | None = None
    for poll_ordinal, polls in snapshots:
        if poll_ordinal < ordinal:
            chosen = polls
        else:
            break
    return chosen


def build_venue_index(
    data_root: Path, manifest: Mapping[str, Any]
) -> tuple[dict[int, Mapping[str, Any]], dict[str, Any]]:
    index: dict[int, Mapping[str, Any]] = {}
    schema_ids: set[str] = set()
    for entry in _manifest_entries(manifest, "venues"):
        schema_ids.add(_schema_identity(entry))
        for row in _load_capture_rows(data_root, entry):
            index[int(row["id"])] = row
    return index, {"venue_rows": len(index), "schema_identities": sorted(schema_ids)}


def build_team_season_index(
    data_root: Path, manifest: Mapping[str, Any]
) -> tuple[dict[tuple[int, int], Mapping[str, Any]], dict[str, Any]]:
    index: dict[tuple[int, int], Mapping[str, Any]] = {}
    schema_ids: set[str] = set()
    seasons: set[int] = set()
    for entry in _manifest_entries(manifest, "teams"):
        schema_ids.add(_schema_identity(entry))
        season = int(entry["coverage"]["season"])
        seasons.add(season)
        for row in _load_capture_rows(data_root, entry):
            index[(season, int(row["id"]))] = row
    return index, {
        "team_season_rows": len(index),
        "seasons": sorted(seasons),
        "schema_identities": sorted(schema_ids),
    }


def _source_team_id(canonical_team_id: str) -> int | None:
    tail = canonical_team_id.rsplit(":", 1)[-1]
    return int(tail) if tail.isdigit() else None


class _TeamState:
    __slots__ = ("games", "win_credit", "points_for", "points_against", "seasons")

    def __init__(self) -> None:
        self.games = 0
        self.win_credit = 0.0
        self.points_for = 0
        self.points_against = 0
        self.seasons: dict[int, list[float]] = {}

    def observe(self, season: int, points_for: int, points_against: int) -> None:
        credit = 1.0 if points_for > points_against else (0.5 if points_for == points_against else 0.0)
        self.games += 1
        self.win_credit += credit
        self.points_for += points_for
        self.points_against += points_against
        bucket = self.seasons.setdefault(season, [0.0, 0.0])
        bucket[0] += 1.0
        bucket[1] += credit

    def prior_season_win_rate(self, season: int) -> float | None:
        earlier = [key for key in self.seasons if key < season]
        if not earlier:
            return None
        played, credit = self.seasons[max(earlier)]
        return round(credit / played, 12) if played else None

    def season_to_date(self, season: int) -> tuple[int, float | None]:
        bucket = self.seasons.get(season)
        if not bucket or bucket[0] <= 0:
            return 0, None
        return int(bucket[0]), round(bucket[1] / bucket[0], 12)


def build_pregame_features(
    *,
    membership: list[Mapping[str, Any]],
    labels: list[Mapping[str, Any]],
    observations: list[Mapping[str, Any]],
    rankings: Mapping[int, list[tuple[tuple[int, int, int], dict[str, dict[int, int]]]]],
    venues: Mapping[int, Mapping[str, Any]],
    team_seasons: Mapping[tuple[int, int], Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Emit one pregame feature row per team observation using strictly earlier evidence."""
    by_game = {row["canonical_game_id"]: row for row in membership}
    labels_by_game: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in labels:
        labels_by_game[row["canonical_game_id"]].append(row)
    observations_by_game: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in observations:
        observations_by_game[row["canonical_game_id"]].append(row)

    labeled_ids = sorted(
        observations_by_game,
        key=lambda game_id: (
            str(by_game[game_id]["start_date_utc_text"] or ""),
            game_id,
        ),
    )

    team_season_seasons = {key[0] for key in team_seasons}
    state: defaultdict[str, _TeamState] = defaultdict(_TeamState)
    features: list[dict[str, Any]] = []
    unresolved = Counter()

    index = 0
    total = len(labeled_ids)
    while index < total:
        # Same-timestamp games are one cohort: none of them may inform another.
        cohort_key = str(by_game[labeled_ids[index]]["start_date_utc_text"] or "")
        cohort: list[str] = []
        while index < total and str(by_game[labeled_ids[index]]["start_date_utc_text"] or "") == cohort_key:
            cohort.append(labeled_ids[index])
            index += 1

        for game_id in cohort:
            game = by_game[game_id]
            season = int(game["season"])
            ordinal = week_ordinal(season, game["season_type"], game["week"])
            poll = lookup_prior_poll(rankings.get(season, []), ordinal)
            venue_id = game["venue_id"]
            venue = venues.get(int(venue_id)) if venue_id is not None else None
            if venue_id is not None and venue is None:
                unresolved["venue_ids"] += 1

            for observation in observations_by_game[game_id]:
                team = observation["canonical_team_id"]
                current = state[team]
                source_team_id = _source_team_id(team)
                if source_team_id is None:
                    unresolved["team_ids"] += 1

                ap_rank = coaches_rank = None
                if poll is not None and source_team_id is not None:
                    ap_rank = poll.get("ap", {}).get(source_team_id)
                    coaches_rank = poll.get("coaches", {}).get(source_team_id)

                team_season = (
                    team_seasons.get((season, source_team_id))
                    if source_team_id is not None
                    else None
                )
                if team_season is None and season in team_season_seasons:
                    unresolved["team_season_rows"] += 1

                prior_games = current.games
                prior_win_rate = (
                    round(current.win_credit / prior_games, 12) if prior_games else None
                )
                prior_points_for = (
                    round(current.points_for / prior_games, 12) if prior_games else None
                )
                prior_points_against = (
                    round(current.points_against / prior_games, 12) if prior_games else None
                )
                prior_margin = (
                    round((current.points_for - current.points_against) / prior_games, 12)
                    if prior_games
                    else None
                )
                season_games, season_rate = current.season_to_date(season)
                prior_season_rate = current.prior_season_win_rate(season)
                elevation = venue.get("elevation") if venue else None

                features.append(
                    {
                        "canonical_game_id": game_id,
                        "canonical_team_id": team,
                        "opponent_canonical_team_id": observation["opponent_canonical_team_id"],
                        "tier_id": observation["tier_id"],
                        "season": season,
                        "week": game["week"],
                        "season_type": game["season_type"],
                        "start_date_utc_text": game["start_date_utc_text"],
                        "is_home": bool(observation["is_home"]),
                        "is_neutral_site": bool(observation["is_neutral_site"]),
                        "prior_games_played": prior_games,
                        "prior_win_rate": prior_win_rate,
                        "prior_win_rate_missing": prior_win_rate is None,
                        "prior_points_for_mean": prior_points_for,
                        "prior_points_for_mean_missing": prior_points_for is None,
                        "prior_points_against_mean": prior_points_against,
                        "prior_points_against_mean_missing": prior_points_against is None,
                        "prior_margin_mean": prior_margin,
                        "prior_margin_mean_missing": prior_margin is None,
                        "prior_season_win_rate": prior_season_rate,
                        "prior_season_win_rate_missing": prior_season_rate is None,
                        "season_to_date_games": season_games,
                        "season_to_date_win_rate": season_rate,
                        "season_to_date_win_rate_missing": season_rate is None,
                        "ap_poll_rank": ap_rank,
                        "ap_poll_rank_missing": ap_rank is None,
                        "coaches_poll_rank": coaches_rank,
                        "coaches_poll_rank_missing": coaches_rank is None,
                        "rankings_source_available": poll is not None,
                        "venue_dome": bool(venue["dome"]) if venue and venue.get("dome") is not None else None,
                        "venue_dome_missing": not (venue and venue.get("dome") is not None),
                        "venue_grass": bool(venue["grass"]) if venue and venue.get("grass") is not None else None,
                        "venue_grass_missing": not (venue and venue.get("grass") is not None),
                        "venue_elevation_m": round(float(elevation), 6) if elevation is not None else None,
                        "venue_elevation_m_missing": elevation is None,
                        "venue_latitude": round(float(venue["latitude"]), 6)
                        if venue and venue.get("latitude") is not None
                        else None,
                        "venue_latitude_missing": not (venue and venue.get("latitude") is not None),
                        "venue_longitude": round(float(venue["longitude"]), 6)
                        if venue and venue.get("longitude") is not None
                        else None,
                        "venue_longitude_missing": not (venue and venue.get("longitude") is not None),
                        "team_conference": team_season.get("conference") if team_season else None,
                        "team_conference_missing": not (team_season and team_season.get("conference")),
                        "team_is_fbs": (
                            str(team_season.get("classification") or "").lower() == "fbs"
                        )
                        if team_season
                        else None,
                        "team_is_fbs_missing": team_season is None,
                    }
                )

        for game_id in cohort:
            season = int(by_game[game_id]["season"])
            for label in labels_by_game[game_id]:
                state[label["canonical_team_id"]].observe(
                    season, int(label["points_for"]), int(label["points_against"])
                )

    features.sort(key=lambda row: (row["canonical_game_id"], row["canonical_team_id"]))
    return features, {
        "unresolved_venue_ids": int(unresolved["venue_ids"]),
        "unresolved_team_ids": int(unresolved["team_ids"]),
        "unresolved_team_season_rows": int(unresolved["team_season_rows"]),
        "distinct_teams": len(state),
    }


def _domain_season_scope(
    manifest: Mapping[str, Any], domain_use: str, population_seasons: set[int]
) -> tuple[set[int], dict[str, Any]]:
    entries = _manifest_entries(manifest, domain_use)
    seasons = {
        int(entry["coverage"]["season"])
        for entry in entries
        if entry["coverage"].get("season") is not None
    }
    declared_rows = sum(int(entry["coverage"].get("row_count") or 0) for entry in entries)
    schema_ids = sorted({_schema_identity(entry) for entry in entries})
    capture_ids = sorted({entry["content_identity"]["sha256"] for entry in entries})
    scope = (seasons & population_seasons) if seasons else set(population_seasons)
    return scope, {
        "captures": len(entries),
        "declared_source_rows": declared_rows,
        "capture_seasons": sorted(seasons),
        "schema_identities": schema_ids,
        "capture_identity_count": len(capture_ids),
        "season_scope_is_capture_declared": bool(seasons),
    }


def _feature_missingness(
    features: list[Mapping[str, Any]], registry: Iterable[Mapping[str, Any]]
) -> dict[str, Any]:
    total = len(features)
    report: dict[str, Any] = {}
    for entry in registry:
        indicator = entry.get("missing_indicator")
        if indicator is None:
            report[entry["feature_id"]] = {
                "rows": total,
                "missing_rows": 0,
                "missing_rate": 0.0,
                "missing_indicator": None,
            }
            continue
        missing = sum(1 for row in features if row[indicator])
        report[entry["feature_id"]] = {
            "rows": total,
            "missing_rows": missing,
            "missing_rate": _ratio(missing, total),
            "missing_indicator": indicator,
        }
    return report


def _admission_matrix(
    *,
    contract: Mapping[str, Any],
    repo_root: Path,
    manifest: Mapping[str, Any],
    membership: list[Mapping[str, Any]],
    features: list[Mapping[str, Any]],
    source_stats: Mapping[str, Any],
    join_stats: Mapping[str, Any],
) -> list[dict[str, Any]]:
    population_seasons = {int(row["season"]) for row in membership}
    games_by_season = Counter(int(row["season"]) for row in membership)
    tamu = contract["tamu_reference"]["canonical_team_id"]
    tamu_games_by_season = Counter(
        int(row["season"])
        for row in membership
        if tamu in (row["home_canonical_team_id"], row["away_canonical_team_id"])
    )
    population_games = len(membership)
    population_rows = len(features)
    distinct_population_teams = len(
        {row["canonical_team_id"] for row in features}
    )

    joined_counts = {
        "rankings": sum(1 for row in features if row["rankings_source_available"]),
        "venues": sum(1 for row in features if not row["venue_latitude_missing"]),
        "team_season_context": sum(1 for row in features if not row["team_is_fbs_missing"]),
        "team_outcome_priors": sum(1 for row in features if not row["prior_win_rate_missing"]),
    }

    rows: list[dict[str, Any]] = []
    for domain in contract["domains"]:
        domain_id = domain["domain_id"]
        route = domain["evidence_route"]
        evidence: dict[str, Any] = {}
        if route == "RAW_CAPTURE":
            scope, evidence = _domain_season_scope(
                manifest, domain["manifest_domain_use"], population_seasons
            )
        elif route == "GATE_REFERENCE":
            gate_path = repo_root / contract["source_contract"][domain["gate_key"]]
            referenced = _read_json(gate_path)
            scope = set()
            evidence = {
                "referenced_gate_relative_path": contract["source_contract"][domain["gate_key"]],
                "referenced_gate_sha256": sha256_file(gate_path),
                "referenced_gate_result": referenced.get("result"),
                "referenced_gate_classification": referenced.get("classification"),
            }
            if domain_id == "weather_forecast_vintages":
                population = referenced["population"]
                scope = set(
                    range(int(population["season_min"]), int(population["season_max"]) + 1)
                ) & population_seasons
                evidence["candidate_games"] = int(population["candidate_games"])
                evidence["candidate_cells"] = int(population["candidate_cells"])
                evidence["historical_pit_admission_in_source_gate"] = bool(
                    referenced["authority"]["historical_pit_admission"]
                )
            if domain_id == "tamu_official_structured_archive":
                scope = set(referenced["selected_seasons"]) & population_seasons
                evidence["archive_games"] = int(referenced["counts"]["games"])
                evidence["archive_rows"] = int(referenced["counts"]["serialized_rows_total"])
                evidence["archive_known_at"] = referenced["historical_known_at"]
        elif route == "SPINE_DERIVED":
            scope = set(population_seasons)
            evidence = {
                "derived_from": "BAT-652 tiered spine outcome labels",
                "requires_no_external_capture": True,
            }
        else:
            scope = set()
            evidence = {"reason": "NO_ACQUIRED_EVIDENCE_IN_THE_PROJECT_FOR_THIS_DOMAIN"}

        scope_games = sum(games_by_season[season] for season in scope)
        scope_tamu_games = sum(tamu_games_by_season[season] for season in scope)

        if domain_id == "tamu_official_structured_archive":
            tamu_game_share_of_domain = 1.0
        else:
            tamu_game_share_of_domain = _ratio(scope_tamu_games, scope_games)

        joined = joined_counts.get(domain_id)
        rows.append(
            {
                "domain_id": domain_id,
                "label": domain["label"],
                "evidence_route": route,
                "decision": domain["decision"],
                "known_at_basis": domain["known_at_basis"],
                "population_games": population_games,
                "population_team_rows": population_rows,
                "domain_season_scope": sorted(scope),
                "domain_scope_seasons": len(scope),
                "domain_scope_games": scope_games,
                "domain_scope_game_share_of_population": _ratio(scope_games, population_games),
                "canonical_join_rate": _ratio(joined, population_rows) if joined is not None else None,
                "canonical_join_rate_basis": (
                    "ADMITTED_FEATURE_ROWS_WITH_A_RESOLVED_NON_MISSING_VALUE"
                    if joined is not None
                    else "NOT_JOINED_BECAUSE_THE_DOMAIN_IS_NOT_ADMITTED"
                ),
                "unresolved_identity_count": (
                    int(join_stats["unresolved_venue_ids"])
                    if domain_id == "venues"
                    else int(join_stats["unresolved_team_season_rows"])
                    if domain_id == "team_season_context"
                    else int(join_stats["unresolved_team_ids"])
                    if domain_id == "team_outcome_priors"
                    else None
                ),
                "missing_rows": (population_rows - joined) if joined is not None else None,
                "missing_rate": _ratio(population_rows - joined, population_rows)
                if joined is not None
                else None,
                "source_identity": evidence,
                "source_row_statistics": source_stats.get(domain_id),
                "target_game_leakage_check": {
                    "same_game_evidence_excluded": True,
                    "same_timestamp_cohort_excluded": domain_id == "team_outcome_priors",
                    "poll_ordinal_strictly_before_game": domain_id == "rankings",
                    "postgame_grain_rejected_from_admission": domain["known_at_basis"]
                    == "POSTGAME_ONLY",
                },
                "national_symmetry": {
                    "distinct_population_teams": distinct_population_teams,
                    "domain_scope_covers_all_population_seasons": scope == population_seasons,
                    "domain_scope_season_share": _ratio(len(scope), len(population_seasons)),
                    "asymmetric": scope != population_seasons,
                },
                "tamu_share": {
                    "domain_scope_tamu_games": scope_tamu_games,
                    "tamu_game_share_of_domain": tamu_game_share_of_domain,
                    "tamu_is_overrepresented": bool(
                        tamu_game_share_of_domain is not None
                        and tamu_game_share_of_domain > 0.05
                    ),
                    "overrepresentation_is_a_finding_not_a_deletion_trigger": True,
                },
                "protected_and_training_authority": {
                    "development_matrix_input": domain["decision"] == "ADMITTED",
                    "protected_training_admission": False,
                    "protected_evaluation_admission": False,
                },
            }
        )
    rows.sort(key=lambda row: row["domain_id"])
    return rows


def _tamu_share_summary(
    *, contract: Mapping[str, Any], membership: list[Mapping[str, Any]], features: list[Mapping[str, Any]]
) -> dict[str, Any]:
    tamu = contract["tamu_reference"]["canonical_team_id"]
    tamu_games = sum(
        1
        for row in membership
        if tamu in (row["home_canonical_team_id"], row["away_canonical_team_id"])
    )
    tamu_rows = sum(1 for row in features if row["canonical_team_id"] == tamu)
    return {
        "canonical_team_id": tamu,
        "population_games": len(membership),
        "tamu_population_games": tamu_games,
        "tamu_game_share_of_population": _ratio(tamu_games, len(membership)),
        "population_team_rows": len(features),
        "tamu_team_rows": tamu_rows,
        "tamu_team_row_share": _ratio(tamu_rows, len(features)),
        "tamu_resolves_in_population": tamu_rows > 0,
        "coverage_distortion_finding": (
            "The Texas A and M official structured archive is 100 percent Texas A and M by "
            "construction while Texas A and M is a small single-digit-per-mille share of the "
            "national population. Recent A and M-heavy execution therefore skewed effort, not "
            "the national admitted matrix, because that archive is quarantined for point-in-time "
            "use and contributes no admitted feature row."
        ),
        "valid_tamu_data_is_retained": True,
    }


def rebuild_expected(*, data_root: Path, repo_root: Path) -> dict[str, Any]:
    contract = load_contract(repo_root)
    contract_bytes = (repo_root / CONTRACT_RELATIVE).read_bytes()
    source = contract["source_contract"]

    spine_gate_path = repo_root / source["spine_gate_relative_path"]
    _require_file(spine_gate_path, source["spine_gate_sha256"])
    spine_gate = _read_json(spine_gate_path)
    if spine_gate["dataset_identity"] != source["spine_dataset_identity"]:
        raise ValueError("spine dataset identity drift")

    manifest_path = repo_root / source["master_manifest_relative_path"]
    _require_file(manifest_path, source["master_manifest_sha256"])
    manifest = _read_json(manifest_path)
    _require_file(
        repo_root / source["weather_candidate_gate_relative_path"],
        source["weather_candidate_gate_sha256"],
    )
    _require_file(
        repo_root / source["tamu_official_corpus_gate_relative_path"],
        source["tamu_official_corpus_gate_sha256"],
    )

    membership = [
        row
        for row in _load_spine_rows(data_root, spine_gate, "national_game_membership.jsonl")
        if row["label_eligible"]
    ]
    observations = _load_spine_rows(data_root, spine_gate, "national_team_observations.jsonl")
    labels = _load_spine_rows(data_root, spine_gate, "national_team_outcome_labels.jsonl")

    scope = contract["population_scope"]
    if len(membership) != int(scope["expected_population_games"]):
        raise ValueError(
            f"population games drift: {len(membership)} != {scope['expected_population_games']}"
        )
    if len(observations) != int(scope["expected_population_team_observations"]):
        raise ValueError("population team observation drift")
    allowed_tiers = set(scope["label_eligible_tiers"])
    if {row["tier_id"] for row in membership} - allowed_tiers:
        raise ValueError("population escaped the declared label-eligible tiers")
    if {row["tier_id"] for row in observations} & set(scope["excluded_tiers"]):
        raise ValueError("an excluded tier leaked a team observation into the population")

    rankings, ranking_stats = build_rankings_index(data_root, manifest)
    venues, venue_stats = build_venue_index(data_root, manifest)
    team_seasons, team_season_stats = build_team_season_index(data_root, manifest)

    features, join_stats = build_pregame_features(
        membership=membership,
        labels=labels,
        observations=observations,
        rankings=rankings,
        venues=venues,
        team_seasons=team_seasons,
    )
    if len(features) != len(observations):
        raise ValueError("pregame feature rows do not cover the population one-for-one")
    _assert_no_outcome_leakage(features)

    source_stats = {
        "rankings": ranking_stats,
        "venues": venue_stats,
        "team_season_context": team_season_stats,
    }
    matrix = _admission_matrix(
        contract=contract,
        repo_root=repo_root,
        manifest=manifest,
        membership=membership,
        features=features,
        source_stats=source_stats,
        join_stats=join_stats,
    )
    missingness = _feature_missingness(features, contract["admitted_feature_registry"])
    tamu_share = _tamu_share_summary(contract=contract, membership=membership, features=features)

    admitted = sorted(row["domain_id"] for row in matrix if row["decision"] == "ADMITTED")
    population = {
        "population_games": len(membership),
        "population_team_rows": len(features),
        "population_seasons": sorted({int(row["season"]) for row in membership}),
        "distinct_population_teams": len({row["canonical_team_id"] for row in features}),
        "declared_domains": len(matrix),
        "admitted_domains": admitted,
        "candidate_domains": sorted(
            row["domain_id"] for row in matrix if row["decision"] == "CANDIDATE"
        ),
        "quarantined_domains": sorted(
            row["domain_id"] for row in matrix if row["decision"] == "QUARANTINED"
        ),
        "source_absent_domains": sorted(
            row["domain_id"] for row in matrix if row["decision"] == "SOURCE_ABSENT"
        ),
        "admitted_feature_count": len(contract["admitted_feature_registry"]),
        "join_statistics": dict(join_stats),
    }

    record_hashes = {
        "pregame_features": stable_hash(features),
        "admission_matrix": stable_hash(matrix),
        "feature_registry": stable_hash(list(contract["admitted_feature_registry"])),
    }
    module_path = Path(__file__).resolve()
    dataset_identity = stable_hash(
        {
            "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "builder_sha256": sha256_file(module_path),
            "spine_dataset_identity": source["spine_dataset_identity"],
            "record_hashes": record_hashes,
            "classification": CLASSIFICATION,
        }
    )
    return {
        "contract": contract,
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "code_identity": sha256_file(module_path),
        "dataset_identity": dataset_identity,
        "record_hashes": record_hashes,
        "population": population,
        "admission_matrix": matrix,
        "feature_missingness": missingness,
        "tamu_share": tamu_share,
        "features": features,
    }


POSTGAME_FIELD_TOKENS = (
    "points_for",
    "points_against",
    "margin",
    "label_win",
    "label_tie",
    "completed",
    "postgame",
    "attendance",
    "excitement",
)


def _assert_no_outcome_leakage(features: list[Mapping[str, Any]]) -> None:
    """A pregame feature row may never carry the target game's own outcome."""
    if not features:
        raise ValueError("pregame feature payload is empty")
    fields = set(features[0])
    leaked = {
        field
        for field in fields
        if any(token in field for token in POSTGAME_FIELD_TOKENS)
        and not field.startswith(("prior_", "season_to_date_"))
    }
    if leaked:
        raise ValueError(f"pregame features carry target-game outcome fields: {sorted(leaked)}")
    for row in features:
        if set(row) != fields:
            raise ValueError("pregame feature rows have inconsistent schemas")
        if row["prior_games_played"] == 0 and not row["prior_win_rate_missing"]:
            raise ValueError("a team with no prior games reported a prior win rate")
        for rank_field in ("ap_poll_rank", "coaches_poll_rank"):
            value = row[rank_field]
            if value is not None and not 1 <= int(value) <= 100:
                raise ValueError(f"implausible poll rank in {rank_field}")
            if value is None and not row[f"{rank_field}_missing"]:
                raise ValueError(f"{rank_field} missing indicator disagrees with the value")


def build_gate(
    *,
    expected: Mapping[str, Any],
    manifest_entry: Mapping[str, Any],
    payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    contract = expected["contract"]
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "NATIONAL_PIT_DOMAIN_ADMISSION_MATRIX_GATE",
        "contract_id": CONTRACT_ID,
        "contract_sha256": expected["contract_sha256"],
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "parent_jira_key": contract["parent_jira_key"],
        "classification": CLASSIFICATION,
        "protected_lane": PROTECTED_LANE,
        "result": PASS_RESULT,
        "dataset_identity": expected["dataset_identity"],
        "manifest": dict(manifest_entry),
        "payloads": payloads,
        "population": expected["population"],
        "admission_matrix": expected["admission_matrix"],
        "admitted_feature_registry": list(contract["admitted_feature_registry"]),
        "quarantined_fields": list(contract["quarantined_fields"]),
        "feature_missingness": expected["feature_missingness"],
        "tamu_share": expected["tamu_share"],
        "leakage_checks": {
            "same_game_outcome_excluded": True,
            "same_timestamp_cohort_excluded": True,
            "poll_ordinal_strictly_before_game_week": True,
            "capture_timestamp_used_as_known_at": False,
            "membership_treated_as_availability": False,
            "unranked_imputed_as_a_rank": False,
            "missing_values_filled": False,
        },
        "source_identities": {
            "spine_gate_sha256": contract["source_contract"]["spine_gate_sha256"],
            "spine_dataset_identity": contract["source_contract"]["spine_dataset_identity"],
            "master_manifest_sha256": contract["source_contract"]["master_manifest_sha256"],
            "weather_candidate_gate_sha256": contract["source_contract"][
                "weather_candidate_gate_sha256"
            ],
            "tamu_official_corpus_gate_sha256": contract["source_contract"][
                "tamu_official_corpus_gate_sha256"
            ],
        },
        "authority": contract["authority"],
        "scientific_nonclaims": {
            "all_domains_admitted": False,
            "gap_004_resolved": False,
            "gap_008_resolved": False,
            "production_feature_set_declared": False,
            "trained_production_champion": False,
            "protected_performance_claimed": False,
            "tamu_specialization_lift_claimed": False,
            "bas_or_aggie_excess_result_claimed": False,
        },
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    gate["binding_identity"] = binding_identity(gate, "binding_identity")
    return gate


def materialize(*, data_root: Path, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    expected = rebuild_expected(data_root=data_root, repo_root=repo_root)
    identity = expected["dataset_identity"]
    canonical_root = (
        data_root / "canonical" / "national_pit_domain_admission_matrix" / "sha256" / identity
    )
    manifest_root = (
        data_root / "manifests" / "national_pit_domain_admission_matrix" / "sha256" / identity
    )

    written = [
        (
            "national_pregame_team_features.jsonl",
            "NATIONAL_ADMITTED_PREGAME_TEAM_FEATURES",
            expected["features"],
        ),
        (
            "national_domain_admission_matrix.jsonl",
            "NATIONAL_DOMAIN_COVERAGE_AND_ADMISSION_MATRIX",
            expected["admission_matrix"],
        ),
        (
            "national_admitted_feature_registry.jsonl",
            "NATIONAL_ADMITTED_FEATURE_REGISTRY",
            list(expected["contract"]["admitted_feature_registry"]),
        ),
        (
            "national_quarantined_field_registry.jsonl",
            "NATIONAL_QUARANTINED_FIELD_REGISTRY",
            list(expected["contract"]["quarantined_fields"]),
        ),
    ]
    payloads: list[dict[str, Any]] = []
    for name, role, rows in written:
        payload_bytes = _jsonl_bytes(rows)
        path = canonical_root / name
        _write_bytes(path, payload_bytes)
        payloads.append(
            {
                "name": name,
                "role": role,
                "relative_path": _relative(path, data_root),
                "rows": len(rows),
                "bytes": len(payload_bytes),
                "sha256": hashlib.sha256(payload_bytes).hexdigest(),
            }
        )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "NATIONAL_PIT_DOMAIN_ADMISSION_MATRIX_MANIFEST",
        "contract_id": CONTRACT_ID,
        "decision_unit": expected["contract"]["decision_unit"],
        "jira_key": expected["contract"]["jira_key"],
        "dataset_identity": identity,
        "issued_at_utc": issued_at_utc,
        "classification": CLASSIFICATION,
        "population": expected["population"],
        "record_hashes": expected["record_hashes"],
        "payloads": payloads,
        "producer": {
            "python": sys.version.split()[0],
            "platform": platform.system(),
            "code_identity": expected["code_identity"],
            "contract_sha256": expected["contract_sha256"],
        },
    }
    manifest_path = manifest_root / "national_pit_domain_admission_matrix_manifest.json"
    _write_bytes(manifest_path, canonical_json_bytes(manifest) + b"\n")

    manifest_entry = {
        "relative_path": _relative(manifest_path, data_root),
        "authoritative_sha256": manifest_authoritative_sha256(manifest),
    }
    gate_payloads = [
        {key: item[key] for key in ("name", "role", "rows", "bytes", "sha256")} for item in payloads
    ]
    gate = build_gate(expected=expected, manifest_entry=manifest_entry, payloads=gate_payloads)
    _write_bytes(repo_root / GATE_RELATIVE, canonical_json_bytes(gate) + b"\n")
    return {"gate": gate, "manifest": manifest, "expected": expected}


def _compare(path: str, actual: Any, expected: Any, errors: list[str]) -> None:
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping):
            errors.append(f"{path}: expected object")
            return
        for key in sorted(set(expected) | set(actual)):
            if key not in expected:
                errors.append(f"{path}.{key}: unexpected key")
            elif key not in actual:
                errors.append(f"{path}.{key}: missing key")
            else:
                _compare(f"{path}.{key}", actual[key], expected[key], errors)
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            errors.append(f"{path}: list shape mismatch")
            return
        for index, (left, right) in enumerate(zip(actual, expected)):
            _compare(f"{path}[{index}]", left, right, errors)
        return
    if actual != expected:
        errors.append(f"{path}: {actual!r} != {expected!r}")


def validate_artifact(
    *,
    data_root: Path,
    repo_root: Path,
    require_rebuild: bool = True,
    gate: Mapping[str, Any] | None = None,
    manifest: Mapping[str, Any] | None = None,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    gate = dict(gate if gate is not None else _read_json(repo_root / GATE_RELATIVE))
    if gate.get("result") != PASS_RESULT:
        raise ValueError(f"national domain matrix gate is not passing: {gate.get('result')}")
    if gate.get("protected_lane") != PROTECTED_LANE:
        raise ValueError("national domain matrix gate opened the protected lane")
    for key, value in gate.get("scientific_nonclaims", {}).items():
        if value is not False:
            raise ValueError(f"national domain matrix gate asserted a forbidden claim: {key}")
    checks = gate.get("leakage_checks", {})
    for key in (
        "same_game_outcome_excluded",
        "same_timestamp_cohort_excluded",
        "poll_ordinal_strictly_before_game_week",
    ):
        if checks.get(key) is not True:
            raise ValueError(f"leakage control is disabled: {key}")
    for key in (
        "capture_timestamp_used_as_known_at",
        "membership_treated_as_availability",
        "unranked_imputed_as_a_rank",
        "missing_values_filled",
    ):
        if checks.get(key) is not False:
            raise ValueError(f"forbidden inference is enabled: {key}")

    admitted = set(gate.get("population", {}).get("admitted_domains", []))
    for row in gate.get("admission_matrix", []):
        if row["decision"] == "ADMITTED" and row["known_at_basis"] in {
            "POSTGAME_ONLY",
            "UNKNOWN_RETRIEVAL_TIME_ONLY",
            "SOURCE_ABSENT",
            "CURRENT_STATE_NOT_VINTAGED",
        }:
            raise ValueError(f"domain admitted without a defensible known-at basis: {row['domain_id']}")
        if row["decision"] == "ADMITTED" and row["domain_id"] not in admitted:
            raise ValueError(f"admitted domain missing from the population summary: {row['domain_id']}")
        if row["decision"] != "ADMITTED" and row["protected_and_training_authority"][
            "development_matrix_input"
        ]:
            raise ValueError(f"unadmitted domain claims matrix input: {row['domain_id']}")
        for key in ("protected_training_admission", "protected_evaluation_admission"):
            if row["protected_and_training_authority"][key] is not False:
                raise ValueError(f"domain opened protected authority: {row['domain_id']}")
    for entry in gate.get("admitted_feature_registry", []):
        if entry["domain_id"] not in admitted:
            raise ValueError(f"registry feature draws on an unadmitted domain: {entry['feature_id']}")

    if not require_rebuild:
        return {"result": "PASS", "mode": "SCHEMA_ONLY", "gate_identity": gate.get("gate_identity")}

    if expected is None:
        expected = rebuild_expected(data_root=data_root, repo_root=repo_root)
    manifest_path = data_root / gate["manifest"]["relative_path"]
    manifest = dict(manifest if manifest is not None else _read_json(manifest_path))

    errors: list[str] = []
    if gate["dataset_identity"] != expected["dataset_identity"]:
        errors.append("dataset identity drift")
    _compare("population", gate["population"], expected["population"], errors)
    _compare("admission_matrix", gate["admission_matrix"], expected["admission_matrix"], errors)
    _compare(
        "feature_missingness", gate["feature_missingness"], expected["feature_missingness"], errors
    )
    _compare("tamu_share", gate["tamu_share"], expected["tamu_share"], errors)
    _compare(
        "manifest.record_hashes", manifest.get("record_hashes"), expected["record_hashes"], errors
    )
    if manifest_authoritative_sha256(manifest) != gate["manifest"].get("authoritative_sha256"):
        errors.append("manifest authoritative content drift")

    for payload in gate["payloads"]:
        entry = next(
            (item for item in manifest.get("payloads", []) if item["name"] == payload["name"]), None
        )
        if entry is None:
            errors.append(f"payload missing from manifest: {payload['name']}")
            continue
        for key in ("rows", "bytes", "sha256", "role"):
            if entry[key] != payload[key]:
                errors.append(f"payload {payload['name']} {key} drift")
        path = data_root / entry["relative_path"]
        if not path.is_file():
            errors.append(f"payload absent on disk: {entry['relative_path']}")
        elif sha256_file(path) != entry["sha256"]:
            errors.append(f"payload rehash drift: {entry['relative_path']}")

    if compute_gate_identity(gate) != gate.get("gate_identity"):
        errors.append("gate identity does not match its own identity-bearing fields")
    if binding_identity(gate, "binding_identity") != gate.get("binding_identity"):
        errors.append("cross-surface binding identity drift")

    if errors:
        raise ValueError("independent national domain matrix validation failed: " + "; ".join(errors[:16]))
    return {
        "result": "PASS",
        "mode": "INDEPENDENT_REBUILD",
        "dataset_identity": gate["dataset_identity"],
        "gate_identity": gate["gate_identity"],
    }

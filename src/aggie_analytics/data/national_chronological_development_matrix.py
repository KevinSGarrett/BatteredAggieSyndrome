from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import platform
import statistics
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
from aggie_analytics.data.national_pit_domain_admission_matrix import week_ordinal

# Nationally scoped chronological development matrix.
#
# Only the BAT-653 admitted domains reach this matrix. Folds expand forward
# through the 2023 development season, every transform is fitted inside its own
# fold's training partition, and appending a later fold can never disturb an
# earlier one.

SCHEMA_VERSION = "aggie.data.national_chronological_development_matrix.v1"
CONTRACT_RELATIVE = "configs/national_chronological_development_matrix_contract.json"
CONTRACT_ID = "BAT-654-NATIONAL-CHRONOLOGICAL-DEVELOPMENT-MATRIX-V1"
GATE_RELATIVE = "artifacts/pit/national_chronological_development_matrix_gate.json"
PASS_RESULT = "PASS_NATIONAL_DEVELOPMENT_MATRIX_UNPROTECTED_DEVELOPMENT_ONLY"
CLASSIFICATION = "NATIONAL_CHRONOLOGICAL_DEVELOPMENT_MATRIX_UNPROTECTED_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"

IDENTITY_FIELDS = (
    "canonical_game_id",
    "canonical_team_id",
    "opponent_canonical_team_id",
    "season",
    "week",
    "season_type",
    "chronological_ordinal",
    "partition",
    "fold_id",
)

NUMERIC_FEATURES = (
    "prior_games_played",
    "prior_win_rate",
    "prior_points_for_mean",
    "prior_points_against_mean",
    "prior_margin_mean",
    "prior_season_win_rate",
    "season_to_date_games",
    "season_to_date_win_rate",
    "ap_poll_rank",
    "coaches_poll_rank",
    "venue_elevation_m",
    "venue_latitude",
    "venue_longitude",
    "opponent_prior_games_played",
    "opponent_prior_win_rate",
    "opponent_prior_margin_mean",
    "opponent_prior_season_win_rate",
    "opponent_ap_poll_rank",
    "prior_win_rate_differential",
)

BOOLEAN_FEATURES = (
    "is_home",
    "is_neutral_site",
    "rankings_source_available",
    "venue_dome",
    "venue_grass",
    "team_is_fbs",
)

CATEGORICAL_FEATURES = ("team_conference",)

GATE_IDENTITY_FIELDS = (
    "artifact_type",
    "authority",
    "chronology",
    "classification",
    "contract_id",
    "contract_sha256",
    "dataset_identity",
    "decision_unit",
    "feature_registry",
    "folds",
    "invariance_proof",
    "jira_key",
    "leakage_checks",
    "manifest",
    "parent_jira_key",
    "payloads",
    "policy",
    "population",
    "protected_lane",
    "result",
    "schema_version",
    "scientific_nonclaims",
    "slices",
    "source_identities",
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
        raise ValueError("national development matrix contract identity drift")
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("national development matrix schema drift")
    if contract.get("protected_lane") != PROTECTED_LANE:
        raise ValueError("protected lane must remain blocked")
    policy = contract["policy"]
    for key in (
        "admitted_domains_only",
        "fold_local_transformations_only",
        "same_game_target_outcome_excluded",
        "future_append_invariance_required",
        "missingness_indicated_never_filled",
        "tamu_rows_are_ordinary_national_rows",
    ):
        if policy.get(key) is not True:
            raise ValueError(f"development matrix policy is disabled: {key}")
    for key in (
        "globally_fitted_scaling_or_imputation",
        "unranked_imputed_as_a_rank",
        "availability_inferred",
        "tamu_adapter_or_specialization_feature",
        "protected_seasons_present_in_any_fold",
    ):
        if policy.get(key) is not False:
            raise ValueError(f"development matrix policy is open: {key}")
    authority = contract["authority"]
    if authority.get("national_development_matrix_use") is not True:
        raise ValueError("development matrix authority is not enabled")
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
            raise ValueError(f"development matrix authority is open: {key}")
    if contract["favorite_rule"].get("uses_market_or_postgame_evidence") is not False:
        raise ValueError("the favorite rule must not consult market or postgame evidence")
    return contract


def _load_payload_rows(
    data_root: Path, gate: Mapping[str, Any], name: str
) -> list[dict[str, Any]]:
    entry = next(item for item in gate["payloads"] if item["name"] == name)
    manifest = _read_json(data_root / gate["manifest"]["relative_path"])
    located = next(item for item in manifest["payloads"] if item["name"] == name)
    payload = (data_root / located["relative_path"]).read_bytes()
    if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
        raise ValueError(f"source payload hash drift: {name}")
    return [json.loads(line) for line in payload.splitlines() if line.strip()]


def chronological_ordinal(row: Mapping[str, Any]) -> tuple[str, int, int, int]:
    season, season_ordinal, week = week_ordinal(
        int(row["season"]), row.get("season_type"), row.get("week")
    )
    return (str(row.get("start_date_utc_text") or ""), season, season_ordinal, week)


def build_matrix(
    *,
    features: list[Mapping[str, Any]],
    labels: list[Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Join admitted pregame features to their own label under one stable identity."""
    chronology = contract["chronology"]
    evaluation_season = int(chronology["development_evaluation_season"])
    excluded = set(chronology["excluded_protected_seasons"]) | set(
        chronology["excluded_prospective_seasons"]
    )

    label_index = {
        (row["canonical_game_id"], row["canonical_team_id"]): row for row in labels
    }
    feature_index = {
        (row["canonical_game_id"], row["canonical_team_id"]): row for row in features
    }

    ordered = sorted(features, key=lambda row: (chronological_ordinal(row), row["canonical_team_id"]))
    ordinals: dict[tuple[str, str], int] = {}
    distinct: dict[tuple[str, int, int, int], int] = {}
    for row in ordered:
        key = chronological_ordinal(row)
        if key not in distinct:
            distinct[key] = len(distinct)
        ordinals[(row["canonical_game_id"], row["canonical_team_id"])] = distinct[key]

    matrix: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    for row in ordered:
        season = int(row["season"])
        if season in excluded:
            raise ValueError(f"an excluded season reached the development matrix: {season}")
        key = (row["canonical_game_id"], row["canonical_team_id"])
        label = label_index.get(key)
        if label is None:
            raise ValueError(f"matrix row has no identity-bound label: {key}")
        opponent = feature_index.get(
            (row["canonical_game_id"], row["opponent_canonical_team_id"])
        )
        if opponent is None:
            raise ValueError(f"matrix row has no opponent observation: {key}")
        if opponent["canonical_team_id"] == row["canonical_team_id"]:
            raise ValueError(f"matrix row is its own opponent: {key}")

        differential = None
        if not row["prior_win_rate_missing"] and not opponent["prior_win_rate_missing"]:
            differential = round(
                float(row["prior_win_rate"]) - float(opponent["prior_win_rate"]), 12
            )
        if differential is None:
            favorite_state = "EVEN_OR_UNKNOWN"
        elif differential > 0:
            favorite_state = "FAVORITE"
        elif differential < 0:
            favorite_state = "UNDERDOG"
        else:
            favorite_state = "EVEN_OR_UNKNOWN"

        if row["ap_poll_rank"] is not None and opponent["ap_poll_rank"] is not None:
            ranking_state = "BOTH_RANKED"
        elif row["ap_poll_rank"] is not None:
            ranking_state = "SELF_RANKED"
        elif opponent["ap_poll_rank"] is not None:
            ranking_state = "OPPONENT_RANKED"
        elif row["rankings_source_available"]:
            ranking_state = "NEITHER_RANKED_POLL_PRESENT"
        else:
            ranking_state = "NO_POLL_SOURCE"

        site = (
            "NEUTRAL"
            if row["is_neutral_site"]
            else ("HOME" if row["is_home"] else "AWAY")
        )
        coverage_bits = (
            not row["prior_win_rate_missing"],
            not row["venue_latitude_missing"],
            not row["team_is_fbs_missing"],
            row["rankings_source_available"],
        )
        coverage = f"COVERAGE_{sum(1 for bit in coverage_bits if bit)}_OF_4"

        entry = {
            "canonical_game_id": row["canonical_game_id"],
            "canonical_team_id": row["canonical_team_id"],
            "opponent_canonical_team_id": row["opponent_canonical_team_id"],
            "season": season,
            "week": row["week"],
            "season_type": row["season_type"],
            "chronological_ordinal": ordinals[key],
            "partition": "EVALUATION" if season == evaluation_season else "TRAINING",
            "site": site,
            "favorite_state": favorite_state,
            "ranking_state": ranking_state,
            "data_coverage_class": coverage,
            "is_home": bool(row["is_home"]),
            "is_neutral_site": bool(row["is_neutral_site"]),
            "prior_games_played": row["prior_games_played"],
            "prior_win_rate": row["prior_win_rate"],
            "prior_win_rate_missing": row["prior_win_rate_missing"],
            "prior_points_for_mean": row["prior_points_for_mean"],
            "prior_points_for_mean_missing": row["prior_points_for_mean_missing"],
            "prior_points_against_mean": row["prior_points_against_mean"],
            "prior_points_against_mean_missing": row["prior_points_against_mean_missing"],
            "prior_margin_mean": row["prior_margin_mean"],
            "prior_margin_mean_missing": row["prior_margin_mean_missing"],
            "prior_season_win_rate": row["prior_season_win_rate"],
            "prior_season_win_rate_missing": row["prior_season_win_rate_missing"],
            "season_to_date_games": row["season_to_date_games"],
            "season_to_date_win_rate": row["season_to_date_win_rate"],
            "season_to_date_win_rate_missing": row["season_to_date_win_rate_missing"],
            "ap_poll_rank": row["ap_poll_rank"],
            "ap_poll_rank_missing": row["ap_poll_rank_missing"],
            "coaches_poll_rank": row["coaches_poll_rank"],
            "coaches_poll_rank_missing": row["coaches_poll_rank_missing"],
            "rankings_source_available": row["rankings_source_available"],
            "venue_dome": row["venue_dome"],
            "venue_dome_missing": row["venue_dome_missing"],
            "venue_grass": row["venue_grass"],
            "venue_grass_missing": row["venue_grass_missing"],
            "venue_elevation_m": row["venue_elevation_m"],
            "venue_elevation_m_missing": row["venue_elevation_m_missing"],
            "venue_latitude": row["venue_latitude"],
            "venue_latitude_missing": row["venue_latitude_missing"],
            "venue_longitude": row["venue_longitude"],
            "venue_longitude_missing": row["venue_longitude_missing"],
            "team_conference": row["team_conference"],
            "team_conference_missing": row["team_conference_missing"],
            "team_is_fbs": row["team_is_fbs"],
            "team_is_fbs_missing": row["team_is_fbs_missing"],
            "opponent_prior_games_played": opponent["prior_games_played"],
            "opponent_prior_win_rate": opponent["prior_win_rate"],
            "opponent_prior_win_rate_missing": opponent["prior_win_rate_missing"],
            "opponent_prior_margin_mean": opponent["prior_margin_mean"],
            "opponent_prior_margin_mean_missing": opponent["prior_margin_mean_missing"],
            "opponent_prior_season_win_rate": opponent["prior_season_win_rate"],
            "opponent_prior_season_win_rate_missing": opponent["prior_season_win_rate_missing"],
            "opponent_ap_poll_rank": opponent["ap_poll_rank"],
            "opponent_ap_poll_rank_missing": opponent["ap_poll_rank_missing"],
            "prior_win_rate_differential": differential,
            "prior_win_rate_differential_missing": differential is None,
        }
        matrix.append(entry)
        label_rows.append(
            {
                "canonical_game_id": row["canonical_game_id"],
                "canonical_team_id": row["canonical_team_id"],
                "season": season,
                "chronological_ordinal": ordinals[key],
                "partition": entry["partition"],
                "label_win": bool(label["label_win"]),
                "label_tie": bool(label["label_tie"]),
                "label_margin": int(label["margin"]),
            }
        )

    matrix.sort(key=lambda row: (row["chronological_ordinal"], row["canonical_game_id"], row["canonical_team_id"]))
    label_rows.sort(
        key=lambda row: (row["chronological_ordinal"], row["canonical_game_id"], row["canonical_team_id"])
    )
    _assert_matrix_invariants(matrix, label_rows, evaluation_season)
    stats = {
        "distinct_chronological_ordinals": len(distinct),
        "training_rows": sum(1 for row in matrix if row["partition"] == "TRAINING"),
        "evaluation_rows": sum(1 for row in matrix if row["partition"] == "EVALUATION"),
    }
    return matrix, label_rows, stats


TARGET_LEAKAGE_TOKENS = ("label_", "points_", "margin_actual", "postgame", "outcome_")


def _assert_matrix_invariants(
    matrix: list[Mapping[str, Any]],
    labels: list[Mapping[str, Any]],
    evaluation_season: int,
) -> None:
    if not matrix:
        raise ValueError("the development matrix is empty")
    fields = set(matrix[0])
    leaked = {
        field
        for field in fields
        if any(token in field for token in TARGET_LEAKAGE_TOKENS)
        and not field.startswith(("prior_", "season_to_date_", "opponent_prior_"))
    }
    if leaked:
        raise ValueError(f"the feature matrix carries target columns: {sorted(leaked)}")

    keys = [(row["canonical_game_id"], row["canonical_team_id"]) for row in matrix]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate matrix identities")
    if [(row["canonical_game_id"], row["canonical_team_id"]) for row in labels] != keys:
        raise ValueError("labels are not identity-aligned with the feature matrix")

    ordinals = [row["chronological_ordinal"] for row in matrix]
    if ordinals != sorted(ordinals):
        raise ValueError("the matrix is not chronologically ordered")

    by_game: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in matrix:
        if set(row) != fields:
            raise ValueError("matrix rows have inconsistent schemas")
        by_game[row["canonical_game_id"]].append(row)
    for game_id, rows in by_game.items():
        if len(rows) != 2:
            raise ValueError(f"game {game_id} does not carry exactly two matrix rows")
        first, second = rows
        if first["canonical_team_id"] != second["opponent_canonical_team_id"]:
            raise ValueError(f"game {game_id} has an inconsistent opponent reference")
        if first["chronological_ordinal"] != second["chronological_ordinal"]:
            raise ValueError(f"game {game_id} spans two chronological ordinals")
        states = {first["favorite_state"], second["favorite_state"]}
        if states not in ({"FAVORITE", "UNDERDOG"}, {"EVEN_OR_UNKNOWN"}):
            raise ValueError(f"game {game_id} has incoherent favorite orientation")

    evaluation_ordinals = {
        row["chronological_ordinal"] for row in matrix if row["partition"] == "EVALUATION"
    }
    training_ordinals = {
        row["chronological_ordinal"] for row in matrix if row["partition"] == "TRAINING"
    }
    if evaluation_ordinals and training_ordinals:
        if min(evaluation_ordinals) <= max(training_ordinals):
            raise ValueError("a training row is chronologically after an evaluation row")
    for row in matrix:
        if row["partition"] == "EVALUATION" and int(row["season"]) != evaluation_season:
            raise ValueError("the evaluation partition escaped its declared season")


def build_folds(
    *, matrix: list[Mapping[str, Any]], labels: list[Mapping[str, Any]], contract: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Expanding folds: fold k trains on everything strictly before its evaluation ordinal."""
    evaluation_season = int(contract["chronology"]["development_evaluation_season"])
    label_index = {
        (row["canonical_game_id"], row["canonical_team_id"]): row for row in labels
    }
    # Group the season into weekly buckets so folds line up with real match weeks.
    buckets: dict[tuple[str, int], list[int]] = {}
    for row in matrix:
        if row["season"] != evaluation_season:
            continue
        key = (str(row["season_type"]), int(row["week"] or 0))
        buckets.setdefault(key, []).append(row["chronological_ordinal"])
    ordered_buckets = sorted(buckets, key=lambda key: (key[0] != "regular", key[1]))

    folds: list[dict[str, Any]] = []
    for index, key in enumerate(ordered_buckets, start=1):
        fold_ordinals = sorted(set(buckets[key]))
        boundary = min(fold_ordinals)
        training = [row for row in matrix if row["chronological_ordinal"] < boundary]
        evaluation = [row for row in matrix if row["chronological_ordinal"] in set(fold_ordinals)]
        if not evaluation:
            continue
        transforms = _fold_transforms(training)
        positives = sum(
            1
            for row in evaluation
            if label_index[(row["canonical_game_id"], row["canonical_team_id"])]["label_win"]
        )
        folds.append(
            {
                "fold_id": f"FOLD-{index:02d}",
                "season_type": key[0],
                "week": key[1],
                "training_max_ordinal_exclusive": boundary,
                "evaluation_ordinals": fold_ordinals,
                "training_rows": len(training),
                "evaluation_rows": len(evaluation),
                "training_seasons": [
                    min(row["season"] for row in training),
                    max(row["season"] for row in training),
                ]
                if training
                else [],
                "evaluation_positive_rate": _ratio(positives, len(evaluation)),
                "fold_local_transforms": transforms,
                "transform_scope": "FITTED_ON_THIS_FOLD_TRAINING_PARTITION_ONLY",
            }
        )
    if not folds:
        raise ValueError("no chronological folds were produced")
    if any(fold["training_rows"] == 0 for fold in folds):
        raise ValueError("a fold has an empty training partition")
    return folds


def _fold_transforms(training: list[Mapping[str, Any]]) -> dict[str, Any]:
    transforms: dict[str, Any] = {}
    for feature in NUMERIC_FEATURES:
        values = [
            float(row[feature])
            for row in training
            if row.get(feature) is not None
        ]
        if len(values) < 2:
            transforms[feature] = {"observed": len(values), "mean": None, "stdev": None}
            continue
        mean = statistics.fmean(values)
        stdev = statistics.pstdev(values)
        transforms[feature] = {
            "observed": len(values),
            "mean": round(mean, 9),
            "stdev": round(stdev, 9) if stdev > 0 else None,
        }
    return transforms


def build_slices(
    *, matrix: list[Mapping[str, Any]], labels: list[Mapping[str, Any]], contract: Mapping[str, Any]
) -> list[dict[str, Any]]:
    evaluation_season = int(contract["chronology"]["development_evaluation_season"])
    label_index = {
        (row["canonical_game_id"], row["canonical_team_id"]): row for row in labels
    }
    rows = [row for row in matrix if row["season"] == evaluation_season]

    def emit(dimension: str, key_of) -> list[dict[str, Any]]:
        counts: Counter[str] = Counter()
        wins: Counter[str] = Counter()
        for row in rows:
            key = str(key_of(row))
            counts[key] += 1
            if label_index[(row["canonical_game_id"], row["canonical_team_id"])]["label_win"]:
                wins[key] += 1
        return [
            {
                "dimension": dimension,
                "slice": key,
                "rows": counts[key],
                "row_share": _ratio(counts[key], len(rows)),
                "positive_rate": _ratio(wins[key], counts[key]),
            }
            for key in sorted(counts)
        ]

    produced: list[dict[str, Any]] = []
    produced.extend(emit("national", lambda row: "ALL"))
    produced.extend(emit("season", lambda row: row["season"]))
    produced.extend(emit("conference", lambda row: row["team_conference"] or "UNRESOLVED"))
    produced.extend(emit("site", lambda row: row["site"]))
    produced.extend(emit("favorite_state", lambda row: row["favorite_state"]))
    produced.extend(emit("ranking_state", lambda row: row["ranking_state"]))
    produced.extend(emit("data_coverage", lambda row: row["data_coverage_class"]))
    return produced


def build_feature_registry(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    registry: list[dict[str, Any]] = []
    for feature in NUMERIC_FEATURES:
        registry.append(
            {
                "feature_id": feature,
                "dtype": "NUMERIC",
                "fold_local_scaled": True,
                "missing_indicator": f"{feature}_missing"
                if feature not in {"prior_games_played", "season_to_date_games", "opponent_prior_games_played"}
                else None,
            }
        )
    for feature in BOOLEAN_FEATURES:
        registry.append(
            {
                "feature_id": feature,
                "dtype": "BOOLEAN",
                "fold_local_scaled": False,
                "missing_indicator": f"{feature}_missing"
                if feature not in {"is_home", "is_neutral_site", "rankings_source_available"}
                else None,
            }
        )
    for feature in CATEGORICAL_FEATURES:
        registry.append(
            {
                "feature_id": feature,
                "dtype": "CATEGORICAL",
                "fold_local_scaled": False,
                "missing_indicator": f"{feature}_missing",
            }
        )
    registry.sort(key=lambda item: item["feature_id"])
    return registry


def _invariance_proof(
    *, matrix: list[Mapping[str, Any]], labels: list[Mapping[str, Any]], contract: Mapping[str, Any], folds: list[Mapping[str, Any]]
) -> dict[str, Any]:
    """Rebuild the folds without the final fold's rows; earlier folds must be untouched."""
    if len(folds) < 2:
        raise ValueError("append invariance requires at least two folds")
    final = folds[-1]
    retained = set(final["evaluation_ordinals"])
    truncated_matrix = [row for row in matrix if row["chronological_ordinal"] not in retained]
    truncated_labels = [row for row in labels if row["chronological_ordinal"] not in retained]
    truncated_folds = build_folds(
        matrix=truncated_matrix, labels=truncated_labels, contract=contract
    )
    earlier = [dict(fold) for fold in folds[:-1]]
    if len(truncated_folds) != len(earlier):
        raise ValueError("truncating the last fold changed the earlier fold count")
    for left, right in zip(earlier, truncated_folds):
        if stable_hash(left) != stable_hash(right):
            raise ValueError(f"appending later rows changed earlier fold {left['fold_id']}")
    return {
        "method": "REBUILD_WITHOUT_THE_FINAL_FOLD_AND_COMPARE_EARLIER_FOLD_IDENTITIES",
        "removed_fold_id": final["fold_id"],
        "removed_rows": len(matrix) - len(truncated_matrix),
        "earlier_folds_compared": len(earlier),
        "earlier_folds_identity": stable_hash(earlier),
        "earlier_folds_identity_after_truncation": stable_hash(truncated_folds),
        "invariant": True,
    }


def rebuild_expected(*, data_root: Path, repo_root: Path) -> dict[str, Any]:
    contract = load_contract(repo_root)
    contract_bytes = (repo_root / CONTRACT_RELATIVE).read_bytes()
    source = contract["source_contract"]

    domain_gate_path = repo_root / source["domain_matrix_gate_relative_path"]
    _require_file(domain_gate_path, source["domain_matrix_gate_sha256"])
    domain_gate = _read_json(domain_gate_path)
    if domain_gate["dataset_identity"] != source["domain_matrix_dataset_identity"]:
        raise ValueError("domain matrix dataset identity drift")

    spine_gate_path = repo_root / source["spine_gate_relative_path"]
    _require_file(spine_gate_path, source["spine_gate_sha256"])
    spine_gate = _read_json(spine_gate_path)
    if spine_gate["dataset_identity"] != source["spine_dataset_identity"]:
        raise ValueError("spine dataset identity drift")

    admitted_domains = set(domain_gate["population"]["admitted_domains"])
    for entry in domain_gate["admitted_feature_registry"]:
        if entry["domain_id"] not in admitted_domains:
            raise ValueError("an unadmitted domain reached the development matrix source")

    features = _load_payload_rows(
        data_root, domain_gate, "national_pregame_team_features.jsonl"
    )
    labels = _load_payload_rows(data_root, spine_gate, "national_team_outcome_labels.jsonl")

    matrix, label_rows, stats = build_matrix(features=features, labels=labels, contract=contract)
    chronology = contract["chronology"]
    if len(matrix) != int(chronology["expected_matrix_rows"]):
        raise ValueError(f"matrix row drift: {len(matrix)}")
    if stats["evaluation_rows"] != int(chronology["expected_evaluation_rows"]):
        raise ValueError(f"evaluation row drift: {stats['evaluation_rows']}")

    folds = build_folds(matrix=matrix, labels=label_rows, contract=contract)
    slices = build_slices(matrix=matrix, labels=label_rows, contract=contract)
    registry = build_feature_registry(contract)
    invariance = _invariance_proof(
        matrix=matrix, labels=label_rows, contract=contract, folds=folds
    )

    tamu = "SRC-002:TEAM:245"
    population = {
        "matrix_rows": len(matrix),
        "training_rows": stats["training_rows"],
        "evaluation_rows": stats["evaluation_rows"],
        "distinct_chronological_ordinals": stats["distinct_chronological_ordinals"],
        "distinct_games": len({row["canonical_game_id"] for row in matrix}),
        "distinct_teams": len({row["canonical_team_id"] for row in matrix}),
        "seasons": [
            min(row["season"] for row in matrix),
            max(row["season"] for row in matrix),
        ],
        "folds": len(folds),
        "feature_count": len(registry),
        "tamu_rows": sum(1 for row in matrix if row["canonical_team_id"] == tamu),
        "tamu_row_share": _ratio(
            sum(1 for row in matrix if row["canonical_team_id"] == tamu), len(matrix)
        ),
        "tamu_evaluation_rows": sum(
            1
            for row in matrix
            if row["canonical_team_id"] == tamu and row["partition"] == "EVALUATION"
        ),
        "evaluation_positive_rate": _ratio(
            sum(1 for row in label_rows if row["partition"] == "EVALUATION" and row["label_win"]),
            stats["evaluation_rows"],
        ),
    }

    record_hashes = {
        "matrix": stable_hash(matrix),
        "labels": stable_hash(label_rows),
        "folds": stable_hash(folds),
        "slices": stable_hash(slices),
        "feature_registry": stable_hash(registry),
    }
    module_path = Path(__file__).resolve()
    dataset_identity = stable_hash(
        {
            "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "builder_sha256": sha256_file(module_path),
            "domain_matrix_dataset_identity": source["domain_matrix_dataset_identity"],
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
        "folds": folds,
        "slices": slices,
        "feature_registry": registry,
        "invariance_proof": invariance,
        "matrix": matrix,
        "labels": label_rows,
    }


def build_gate(
    *,
    expected: Mapping[str, Any],
    manifest_entry: Mapping[str, Any],
    payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    contract = expected["contract"]
    folds = [
        {key: value for key, value in fold.items() if key != "fold_local_transforms"}
        | {"fold_local_transforms_identity": stable_hash(fold["fold_local_transforms"])}
        for fold in expected["folds"]
    ]
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "NATIONAL_CHRONOLOGICAL_DEVELOPMENT_MATRIX_GATE",
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
        "chronology": contract["chronology"],
        "policy": contract["policy"],
        "folds": folds,
        "slices": expected["slices"],
        "feature_registry": expected["feature_registry"],
        "invariance_proof": expected["invariance_proof"],
        "leakage_checks": {
            "same_game_target_outcome_excluded": True,
            "labels_stored_separately_from_features": True,
            "fold_transforms_fitted_on_training_only": True,
            "globally_fitted_scaling_or_imputation": False,
            "protected_season_row_present": False,
            "prospective_season_row_present": False,
            "unranked_imputed_as_a_rank": False,
            "availability_inferred": False,
            "tamu_adapter_present": False,
        },
        "source_identities": {
            "domain_matrix_gate_sha256": contract["source_contract"]["domain_matrix_gate_sha256"],
            "domain_matrix_dataset_identity": contract["source_contract"][
                "domain_matrix_dataset_identity"
            ],
            "spine_gate_sha256": contract["source_contract"]["spine_gate_sha256"],
            "spine_dataset_identity": contract["source_contract"]["spine_dataset_identity"],
        },
        "authority": contract["authority"],
        "scientific_nonclaims": {
            "production_matrix_declared": False,
            "gap_003_resolved": False,
            "gap_004_resolved": False,
            "gap_005_resolved": False,
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
        data_root / "canonical" / "national_chronological_development_matrix" / "sha256" / identity
    )
    manifest_root = (
        data_root / "manifests" / "national_chronological_development_matrix" / "sha256" / identity
    )

    written = [
        ("national_development_matrix_features.jsonl", "NATIONAL_DEVELOPMENT_MATRIX_FEATURES", expected["matrix"]),
        ("national_development_matrix_labels.jsonl", "NATIONAL_DEVELOPMENT_MATRIX_LABELS", expected["labels"]),
        ("national_development_matrix_folds.jsonl", "NATIONAL_DEVELOPMENT_MATRIX_FOLD_MANIFEST", expected["folds"]),
        ("national_development_matrix_slices.jsonl", "NATIONAL_DEVELOPMENT_MATRIX_SLICES", expected["slices"]),
        (
            "national_development_matrix_feature_registry.jsonl",
            "NATIONAL_DEVELOPMENT_MATRIX_FEATURE_REGISTRY",
            expected["feature_registry"],
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
        "artifact_type": "NATIONAL_CHRONOLOGICAL_DEVELOPMENT_MATRIX_MANIFEST",
        "contract_id": CONTRACT_ID,
        "decision_unit": expected["contract"]["decision_unit"],
        "jira_key": expected["contract"]["jira_key"],
        "dataset_identity": identity,
        "issued_at_utc": issued_at_utc,
        "classification": CLASSIFICATION,
        "population": expected["population"],
        "record_hashes": expected["record_hashes"],
        "invariance_proof": expected["invariance_proof"],
        "payloads": payloads,
        "producer": {
            "python": sys.version.split()[0],
            "platform": platform.system(),
            "code_identity": expected["code_identity"],
            "contract_sha256": expected["contract_sha256"],
        },
    }
    manifest_path = manifest_root / "national_chronological_development_matrix_manifest.json"
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
        raise ValueError(f"development matrix gate is not passing: {gate.get('result')}")
    if gate.get("protected_lane") != PROTECTED_LANE:
        raise ValueError("development matrix gate opened the protected lane")
    for key, value in gate.get("scientific_nonclaims", {}).items():
        if value is not False:
            raise ValueError(f"development matrix gate asserted a forbidden claim: {key}")
    checks = gate.get("leakage_checks", {})
    for key in (
        "same_game_target_outcome_excluded",
        "labels_stored_separately_from_features",
        "fold_transforms_fitted_on_training_only",
    ):
        if checks.get(key) is not True:
            raise ValueError(f"leakage control is disabled: {key}")
    for key in (
        "globally_fitted_scaling_or_imputation",
        "protected_season_row_present",
        "prospective_season_row_present",
        "unranked_imputed_as_a_rank",
        "availability_inferred",
        "tamu_adapter_present",
    ):
        if checks.get(key) is not False:
            raise ValueError(f"forbidden matrix behaviour is enabled: {key}")

    chronology = gate.get("chronology", {})
    forbidden_seasons = set(chronology.get("excluded_protected_seasons", [])) | set(
        chronology.get("excluded_prospective_seasons", [])
    )
    seasons = gate.get("population", {}).get("seasons", [])
    if seasons and forbidden_seasons and max(seasons) >= min(forbidden_seasons):
        raise ValueError("an excluded season reached the development matrix population")
    if gate.get("invariance_proof", {}).get("invariant") is not True:
        raise ValueError("the matrix does not prove future append invariance")
    for fold in gate.get("folds", []):
        if fold["transform_scope"] != "FITTED_ON_THIS_FOLD_TRAINING_PARTITION_ONLY":
            raise ValueError(f"fold {fold['fold_id']} used an out-of-fold transform")
        if int(fold["training_rows"]) <= 0:
            raise ValueError(f"fold {fold['fold_id']} has an empty training partition")
        if int(fold["training_max_ordinal_exclusive"]) > min(fold["evaluation_ordinals"]):
            raise ValueError(f"fold {fold['fold_id']} trains past its own evaluation ordinal")

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
    _compare("slices", gate["slices"], expected["slices"], errors)
    _compare("feature_registry", gate["feature_registry"], expected["feature_registry"], errors)
    _compare("invariance_proof", gate["invariance_proof"], expected["invariance_proof"], errors)
    expected_folds = [
        {key: value for key, value in fold.items() if key != "fold_local_transforms"}
        | {"fold_local_transforms_identity": stable_hash(fold["fold_local_transforms"])}
        for fold in expected["folds"]
    ]
    _compare("folds", gate["folds"], expected_folds, errors)
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
        raise ValueError(
            "independent development matrix validation failed: " + "; ".join(errors[:16])
        )
    return {
        "result": "PASS",
        "mode": "INDEPENDENT_REBUILD",
        "dataset_identity": gate["dataset_identity"],
        "gate_identity": gate["gate_identity"],
    }

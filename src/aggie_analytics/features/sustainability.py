from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from aggie_analytics.temporal.play_drive_pit import (
    canonical_json_bytes,
    cutoff_utc,
    parse_utc,
    sha256_file,
    stable_hash,
)


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError(
            "sustainability materialization requires the optional data-engineering environment"
        ) from exc
    return polars


def _source_paths(data_root: Path, contract: dict[str, Any]) -> dict[str, Path]:
    identity = contract["source_contract"]["dataset_identity"]
    return {
        "outcomes": data_root
        / "pit_state"
        / "historical_known_at"
        / "sha256"
        / identity
        / "accepted_game_outcomes.parquet",
        "targets": data_root
        / "features"
        / "historical_known_at"
        / "sha256"
        / identity
        / "target_game_cutoffs.parquet",
        "manifest": data_root
        / "manifests"
        / "historical_known_at"
        / "sha256"
        / identity
        / "known_at_replay_manifest.json",
    }


def _verify_sources(
    data_root: Path, contract: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    paths = _source_paths(data_root, contract)
    expected = {
        "outcomes": contract["source_contract"]["accepted_outcomes_sha256"],
        "targets": contract["source_contract"]["target_cutoffs_sha256"],
        "manifest": contract["source_contract"]["replay_manifest_sha256"],
    }
    verified: dict[str, dict[str, Any]] = {}
    for name, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256_file(path)
        if actual.lower() != expected[name].lower():
            raise ValueError(
                f"pinned {name} hash drift: expected {expected[name]}, found {actual}"
            )
        verified[name] = {
            "path": str(path.relative_to(data_root)).replace("\\", "/"),
            "bytes": path.stat().st_size,
            "sha256": actual,
        }
    replay = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    if (
        replay.get("dataset_identity")
        != contract["source_contract"]["dataset_identity"]
    ):
        raise ValueError("historical known-at replay identity drift")
    return verified


def _team_game_rows(outcomes: Any) -> Any:
    pl = _polars()
    shared = [
        "canonical_game_id",
        "season",
        "season_type",
        "game_start_utc",
        "completed_known_by_utc",
        "source_known_at_utc",
        "source_capture_id",
        "source_record_evidence_sha256",
    ]
    home = outcomes.select(
        *shared,
        pl.col("home_team_id").alias("team_id"),
        pl.col("away_team_id").alias("opponent_team_id"),
        pl.col("home_points").alias("points_for"),
        pl.col("away_points").alias("points_against"),
        pl.lit("HOME").alias("team_role"),
    )
    away = outcomes.select(
        *shared,
        pl.col("away_team_id").alias("team_id"),
        pl.col("home_team_id").alias("opponent_team_id"),
        pl.col("away_points").alias("points_for"),
        pl.col("home_points").alias("points_against"),
        pl.lit("AWAY").alias("team_role"),
    )
    return (
        pl.concat([home, away], how="vertical")
        .with_columns(
            (pl.col("points_for") - pl.col("points_against")).alias("team_margin"),
            pl.when(pl.col("points_for") > pl.col("points_against"))
            .then(pl.lit(1.0))
            .when(pl.col("points_for") < pl.col("points_against"))
            .then(pl.lit(0.0))
            .otherwise(pl.lit(0.5))
            .alias("win_share_value"),
        )
        .with_columns(
            (pl.col("team_margin").abs() <= 7).alias("close_game"),
            (pl.col("team_margin") <= -17).alias("downside_tail"),
            (pl.col("team_margin") >= 17).alias("upside_tail"),
        )
        .sort(["season", "game_start_utc", "canonical_game_id", "team_role"])
    )


def _aggregate_window(rows: Any, prefix: str) -> Any:
    pl = _polars()
    grouped = rows.group_by("team_id").agg(
        pl.len().alias(f"{prefix}_source_game_count"),
        pl.col("season").n_unique().alias(f"{prefix}_source_season_count"),
        pl.col("win_share_value").mean().alias(f"{prefix}_win_share"),
        pl.col("points_for").sum().alias(f"{prefix}_points_for"),
        pl.col("points_against").sum().alias(f"{prefix}_points_against"),
        pl.col("close_game")
        .cast(pl.Float64)
        .mean()
        .alias(f"{prefix}_close_game_share"),
        pl.col("win_share_value")
        .filter(pl.col("close_game"))
        .mean()
        .alias(f"{prefix}_close_win_share"),
        pl.col("team_margin").mean().alias(f"{prefix}_margin_mean"),
        pl.col("team_margin").std(ddof=0).alias(f"{prefix}_margin_stddev"),
        pl.col("team_margin").abs().mean().alias(f"{prefix}_mean_absolute_margin"),
        pl.col("downside_tail")
        .cast(pl.Float64)
        .mean()
        .alias(f"{prefix}_downside_tail_rate"),
        pl.col("upside_tail")
        .cast(pl.Float64)
        .mean()
        .alias(f"{prefix}_upside_tail_rate"),
        pl.col("source_known_at_utc").max().alias(f"{prefix}_source_known_at_utc_max"),
    )
    return grouped.with_columns(
        (
            pl.col(f"{prefix}_points_for")
            / (pl.col(f"{prefix}_points_for") + pl.col(f"{prefix}_points_against"))
        ).alias(f"{prefix}_score_share"),
        (pl.col(f"{prefix}_close_win_share") - pl.col(f"{prefix}_win_share")).alias(
            f"{prefix}_close_win_share_minus_overall"
        ),
        (
            pl.col(f"{prefix}_upside_tail_rate")
            - pl.col(f"{prefix}_downside_tail_rate")
        ).alias(f"{prefix}_tail_imbalance"),
    ).with_columns(
        (pl.col(f"{prefix}_win_share") - pl.col(f"{prefix}_score_share")).alias(
            f"{prefix}_win_share_minus_score_share"
        )
    )


def _build_profiles(
    outcomes: Any, contract: dict[str, Any]
) -> tuple[Any, dict[str, Any]]:
    pl = _polars()
    source = contract["source_contract"]
    seasons = source["source_seasons"]
    recent_seasons = source["recent_window_seasons"]
    admitted = outcomes.filter(pl.col("season").is_in(seasons))
    if admitted.height != outcomes.height:
        raise ValueError(
            "outcome source contains rows outside the pinned source seasons"
        )
    if admitted.select(pl.col("canonical_game_id").is_duplicated().sum()).item() != 0:
        raise ValueError("duplicate canonical source game identities")
    team_games = _team_game_rows(admitted)
    all_profiles = _aggregate_window(team_games, "all")
    recent_rows = team_games.filter(pl.col("season").is_in(recent_seasons))
    recent_profiles = _aggregate_window(recent_rows, "recent")
    pandemic = recent_rows.group_by("team_id").agg(
        (pl.col("season").eq(2020).cast(pl.Float64).mean()).alias(
            "pandemic_2020_game_share"
        )
    )
    profiles = (
        all_profiles.join(recent_profiles, on="team_id", how="left")
        .join(pandemic, on="team_id", how="left")
        .with_columns(
            pl.max_horizontal(
                "all_source_known_at_utc_max", "recent_source_known_at_utc_max"
            ).alias("source_known_at_utc_max"),
            pl.lit("DEVELOPMENT_ONLY_RETROSPECTIVE").alias("authority"),
            pl.lit(False).alias("historical_original_pit_eligible"),
        )
        .sort("team_id")
    )
    season_counts = {
        str(row["season"]): int(row["len"])
        for row in admitted.group_by("season").len().sort("season").to_dicts()
    }
    team_season = team_games.group_by(["season", "team_id"]).len()
    counts = {
        "source_games": admitted.height,
        "source_team_game_rows": team_games.height,
        "source_games_by_season": season_counts,
        "source_teams": profiles.height,
        "source_team_seasons": team_season.height,
        "source_ties": admitted.filter(
            pl.col("home_points") == pl.col("away_points")
        ).height,
        "source_close_games": admitted.filter(
            (pl.col("home_points") - pl.col("away_points")).abs() <= 7
        ).height,
        "source_tail_games": admitted.filter(
            (pl.col("home_points") - pl.col("away_points")).abs() >= 17
        ).height,
        "source_known_at_utc_max": admitted["source_known_at_utc"].max(),
        "minimum_team_season_games": int(team_season["len"].min()),
        "median_team_season_games": float(team_season["len"].median()),
        "maximum_team_season_games": int(team_season["len"].max()),
    }
    return profiles, counts


def _build_target_features(targets: Any, profiles: Any, classification: str) -> Any:
    pl = _polars()
    targets = targets.with_columns(
        pl.struct(["start_utc", "cutoff_lead_hours"])
        .map_elements(
            lambda row: cutoff_utc(row["start_utc"], row["cutoff_lead_hours"]),
            return_dtype=pl.String,
        )
        .alias("cutoff_utc")
    )
    home = targets.select(
        "game_id",
        "season",
        "season_type",
        "week",
        "start_utc",
        "cutoff_utc",
        pl.col("home_team_id").cast(pl.String).alias("team_id"),
        pl.col("away_team_id").cast(pl.String).alias("opponent_team_id"),
        pl.lit("HOME").alias("team_role"),
        "neutral_site",
    )
    away = targets.select(
        "game_id",
        "season",
        "season_type",
        "week",
        "start_utc",
        "cutoff_utc",
        pl.col("away_team_id").cast(pl.String).alias("team_id"),
        pl.col("home_team_id").cast(pl.String).alias("opponent_team_id"),
        pl.lit("AWAY").alias("team_role"),
        "neutral_site",
    )
    return (
        pl.concat([home, away], how="vertical")
        .sort(["season", "start_utc", "game_id", "team_role"])
        .join(profiles, on="team_id", how="left")
        .with_columns(
            pl.col("all_source_game_count").is_null().alias("cold_start"),
            pl.lit(classification).alias("classification"),
            pl.lit(False).alias("protected_eligible"),
            pl.lit(False).alias("historical_original_pit_eligible"),
            pl.lit(True).alias("event_chronology_eligible"),
        )
    )


def materialize(
    *,
    input_data_root: Path,
    output_data_root: Path,
    repo_root: Path,
    issued_at_utc: str,
) -> dict[str, Any]:
    pl = _polars()
    parse_utc(issued_at_utc)
    contract_path = repo_root / "configs" / "preliminary_sustainability_contract.json"
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    verified_sources = _verify_sources(input_data_root, contract)
    paths = _source_paths(input_data_root, contract)
    outcomes = pl.read_parquet(paths["outcomes"]).sort(
        ["season", "game_start_utc", "canonical_game_id"]
    )
    targets = pl.read_parquet(paths["targets"]).sort(["season", "start_utc", "game_id"])
    profiles, counts = _build_profiles(outcomes, contract)
    features = _build_target_features(targets, profiles, contract["classification"])
    expected_rows = (
        targets.height * contract["acceptance"]["required_target_game_team_multiplier"]
    )
    if features.height != expected_rows:
        raise ValueError(
            "target-game/team population is not exactly two rows per target game"
        )
    target_ids = set(targets["game_id"].to_list())
    source_ids = set(outcomes["canonical_game_id"].to_list())
    target_overlap = len(target_ids & source_ids)
    if target_overlap:
        raise ValueError("target game appears in sustainability source evidence")
    minimum_cutoff = features["cutoff_utc"].min()
    maximum_source_known = counts["source_known_at_utc_max"]
    if parse_utc(maximum_source_known) >= parse_utc(minimum_cutoff):
        raise ValueError("source known-at does not precede every target cutoff")
    forbidden = {
        "home_win",
        "home_points",
        "away_points",
        "margin",
        "winner",
        "outcome",
        "target_score",
    }
    if forbidden & set(features.columns):
        raise ValueError(
            "target or future-outcome column present in candidate features"
        )
    identity_payload = {
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "verified_sources": verified_sources,
        "classification": contract["classification"],
        "profile_records": profiles.to_dicts(),
        "feature_records": features.to_dicts(),
    }
    dataset_identity = stable_hash(identity_payload)
    state_root = (
        output_data_root
        / "pit_state"
        / "preliminary_sustainability"
        / "sha256"
        / dataset_identity
    )
    feature_root = (
        output_data_root
        / "features"
        / "preliminary_sustainability"
        / "sha256"
        / dataset_identity
    )
    manifest_root = (
        output_data_root
        / "manifests"
        / "preliminary_sustainability"
        / "sha256"
        / dataset_identity
    )
    for path in (state_root, feature_root, manifest_root):
        path.mkdir(parents=True, exist_ok=True)
    state_path = state_root / "team_sustainability_profiles.parquet"
    feature_path = feature_root / "target_game_team_sustainability_features.parquet"
    profiles.write_parquet(state_path, compression="zstd", statistics=True)
    features.write_parquet(feature_path, compression="zstd", statistics=True)
    payloads = [
        {
            "role": "DEVELOPMENT_ONLY_TEAM_SUSTAINABILITY_PROFILE",
            "path": f"pit_state/preliminary_sustainability/sha256/{dataset_identity}/team_sustainability_profiles.parquet",
            "rows": profiles.height,
            "bytes": state_path.stat().st_size,
            "sha256": sha256_file(state_path),
        },
        {
            "role": "PRELIMINARY_UNPROTECTED_TARGET_GAME_TEAM_FEATURES",
            "path": f"features/preliminary_sustainability/sha256/{dataset_identity}/target_game_team_sustainability_features.parquet",
            "rows": features.height,
            "bytes": feature_path.stat().st_size,
            "sha256": sha256_file(feature_path),
        },
    ]
    feature_names = list(contract["feature_contract"]["features"])
    manifest = {
        "schema_version": "1.0.0",
        "artifact_type": "PRELIMINARY_SUSTAINABILITY_VOLATILITY_CANDIDATE",
        "dataset_identity": dataset_identity,
        "issued_at_utc": issued_at_utc,
        "decision_unit": contract["decision_unit"],
        "related_design_units": contract["related_design_units"],
        "parent_unit": contract["parent_unit"],
        "classification": contract["classification"],
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "source_contract": contract["source_contract"],
        "verified_sources": verified_sources,
        "population": {
            **counts,
            "target_seasons": contract["source_contract"]["target_seasons"],
            "target_games": targets.height,
            "target_game_team_rows": features.height,
            "cold_start_rows": features.filter(pl.col("cold_start")).height,
            "target_game_overlap": target_overlap,
        },
        "features": contract["feature_contract"]["features"],
        "feature_missingness": {
            name: features[name].null_count() for name in feature_names
        },
        "temporal_validation": {
            "maximum_source_known_at_utc": maximum_source_known,
            "minimum_target_cutoff_utc": minimum_cutoff,
            "source_known_at_precedes_all_target_cutoffs": True,
            "source_seasons_max": int(outcomes["season"].max()),
            "target_seasons_min": int(targets["season"].min()),
            "source_season_precedes_target_season": int(outcomes["season"].max())
            < int(targets["season"].min()),
            "target_game_overlap": target_overlap,
            "historical_original_pit_eligible": False,
        },
        "unsupported_fields": contract["feature_contract"]["unsupported_fields"],
        "authority": contract["authority"],
        "payloads": payloads,
        "negative_findings": contract["negative_findings"],
        "scientific_nonclaims": {
            "historical_population_ready": False,
            "production_model_ready": False,
            "champion_promoted": False,
            "protected_performance_claimed": False,
            "tamu_specialization_lift_claimed": False,
            "bas_or_aggie_excess_result_claimed": False,
            "causal_luck_or_clutch_claimed": False,
        },
    }
    manifest_path = manifest_root / "run_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    return {
        "dataset_identity": dataset_identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "manifest": manifest,
        "state_path": str(state_path),
        "feature_path": str(feature_path),
    }

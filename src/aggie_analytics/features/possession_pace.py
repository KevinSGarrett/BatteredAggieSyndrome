from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from aggie_analytics.temporal.play_drive_pit import (
    _eligible_source_rows,
    _load_sources,
    _validate_source_contract,
    canonical_json_bytes,
    cutoff_utc,
    sha256_file,
    stable_hash,
)


def regulation_elapsed_seconds(period: int | None, minutes: int | None, seconds: int | None) -> int | None:
    """Convert a regulation game clock to elapsed seconds from kickoff."""
    if period is None or minutes is None or seconds is None:
        return None
    period = int(period)
    minutes = int(minutes)
    seconds = int(seconds)
    if (
        period < 1
        or period > 4
        or minutes < 0
        or minutes > 15
        or seconds < 0
        or seconds > 59
        or (minutes == 15 and seconds != 0)
    ):
        return None
    return (period - 1) * 900 + (900 - (minutes * 60 + seconds))


def observed_regulation_drive_span_seconds(
    first_period: int | None,
    first_minutes: int | None,
    first_seconds: int | None,
    last_period: int | None,
    last_minutes: int | None,
    last_seconds: int | None,
) -> tuple[int | None, bool | None]:
    """Return order-normalized recorded-play span and whether endpoints were reversed."""
    first = regulation_elapsed_seconds(first_period, first_minutes, first_seconds)
    last = regulation_elapsed_seconds(last_period, last_minutes, last_seconds)
    if first is None or last is None:
        return None, None
    return abs(last - first), last < first


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("possession/pace materialization requires the optional data-engineering environment") from exc
    return polars


def _verify_source_manifests(data_root: Path, contract: dict[str, Any]) -> list[dict[str, str]]:
    source = contract["source_contract"]
    expected: set[tuple[str, str]] = set()
    for layer in source["source_layers"]:
        expected.add((layer["play_dataset_identity"], layer["play_manifest_sha256"]))
        expected.add((layer["drive_dataset_identity"], layer["drive_manifest_sha256"]))
    expected.add((source["target_replay_identity"], source["target_replay_manifest_sha256"]))
    verified: list[dict[str, str]] = []
    for identity, expected_sha in sorted(expected):
        root = data_root / "manifests" / "historical_known_at" / "sha256" / identity
        matches = [path for path in root.glob("*.json") if sha256_file(path).lower() == expected_sha.lower()]
        if len(matches) != 1:
            raise ValueError(f"pinned source manifest hash did not resolve exactly once for {identity}: {expected_sha}")
        verified.append({"dataset_identity": identity, "manifest_name": matches[0].name, "manifest_sha256": expected_sha.lower()})
    return verified


def _build_profiles(plays: Any, drives: Any, team_map: Any, contract: dict[str, Any]) -> tuple[Any, dict[str, int]]:
    pl = _polars()
    source = contract["source_contract"]
    plays = _eligible_source_rows(plays, source, "play").with_columns(
        pl.col("offense_team_id").cast(pl.String).alias("source_team_id"),
        pl.col("canonical_game_id").cast(pl.String),
    ).join(team_map, on="source_team_id", how="left")
    drives = _eligible_source_rows(drives, source, "drive").with_columns(
        pl.col("offense_team_id").cast(pl.String).alias("source_team_id"),
        pl.col("canonical_game_id").cast(pl.String),
    ).join(team_map, on="source_team_id", how="left")
    source_play_rows = plays.height
    source_drive_rows = drives.height
    unmapped_play_rows = plays["team_id"].null_count()
    unmapped_drive_rows = drives["team_id"].null_count()
    plays = plays.filter(pl.col("team_id").is_not_null())
    drives = drives.filter(pl.col("team_id").is_not_null())

    span = pl.struct(
        "first_period", "first_clock_minutes", "first_clock_seconds",
        "last_period", "last_clock_minutes", "last_clock_seconds",
    ).map_elements(
        lambda row: observed_regulation_drive_span_seconds(
            row["first_period"], row["first_clock_minutes"], row["first_clock_seconds"],
            row["last_period"], row["last_clock_minutes"], row["last_clock_seconds"],
        )[0],
        return_dtype=pl.Int64,
    )
    reversed_endpoint = pl.struct(
        "first_period", "first_clock_minutes", "first_clock_seconds",
        "last_period", "last_clock_minutes", "last_clock_seconds",
    ).map_elements(
        lambda row: observed_regulation_drive_span_seconds(
            row["first_period"], row["first_clock_minutes"], row["first_clock_seconds"],
            row["last_period"], row["last_clock_minutes"], row["last_clock_seconds"],
        )[1],
        return_dtype=pl.Boolean,
    )
    drives = drives.with_columns(
        span.alias("regulation_drive_span_seconds"),
        reversed_endpoint.alias("source_endpoint_reversed"),
        ((pl.col("first_period") > 4) | (pl.col("last_period") > 4)).alias("overtime_drive"),
        pl.col("source_known_at_utc").alias("drive_source_known_at_utc"),
    )
    play_profiles = plays.group_by("team_id").agg(
        pl.len().alias("exact_play_rows"),
        pl.col("canonical_game_id").n_unique().alias("exact_play_games"),
        pl.col("season").n_unique().alias("source_season_count"),
        pl.col("source_known_at_utc").max().alias("play_source_known_at_utc_max"),
    )
    drive_profiles = drives.group_by("team_id").agg(
        pl.len().alias("exact_drive_rows"),
        pl.col("canonical_game_id").n_unique().alias("exact_drive_games"),
        pl.col("source_play_rows").mean().alias("observed_plays_per_drive_mean"),
        pl.col("regulation_drive_span_seconds").count().alias("regulation_drive_span_rows"),
        pl.col("regulation_drive_span_seconds").mean().alias("regulation_drive_span_seconds_mean"),
        pl.col("regulation_drive_span_seconds").median().alias("regulation_drive_span_seconds_median"),
        pl.col("source_endpoint_reversed").cast(pl.Float64).mean().alias("source_endpoint_reverse_rate"),
        pl.col("overtime_drive").cast(pl.Float64).mean().alias("overtime_drive_rate"),
        pl.col("drive_source_known_at_utc").max().alias("drive_source_known_at_utc_max"),
    )
    profiles = play_profiles.join(drive_profiles, on="team_id", how="full", coalesce=True).with_columns(
        (pl.col("exact_play_rows") / pl.col("exact_play_games")).alias("offensive_plays_per_game"),
        (pl.col("exact_drive_rows") / pl.col("exact_drive_games")).alias("offensive_drives_per_game"),
        (pl.col("regulation_drive_span_rows") / pl.col("exact_drive_rows")).alias("regulation_drive_span_eligible_rate"),
        pl.lit("PRE_2023_FIRST_DOWN_CLOCK").alias("source_rule_era"),
        pl.lit("DEVELOPMENT_ONLY").alias("authority"),
    ).sort("team_id")
    counts = {
        "source_exact_play_rows": source_play_rows,
        "mapped_exact_play_rows": plays.height,
        "source_exact_drive_rows": source_drive_rows,
        "mapped_exact_drive_rows": drives.height,
        "unmapped_exact_play_rows": unmapped_play_rows,
        "unmapped_exact_drive_rows": unmapped_drive_rows,
        "exact_play_games": plays["canonical_game_id"].n_unique(),
        "exact_drive_games": drives["canonical_game_id"].n_unique(),
        "profile_teams": profiles.height,
        "regulation_drive_span_rows": drives["regulation_drive_span_seconds"].drop_nulls().len(),
        "overtime_drive_rows": drives.filter(pl.col("overtime_drive")).height,
        "source_endpoint_reversed_rows": drives.filter(pl.col("source_endpoint_reversed") == True).height,  # noqa: E712
        "invalid_or_ineligible_clock_rows": drives["regulation_drive_span_seconds"].null_count(),
    }
    return profiles, counts


def _build_target_features(targets: Any, profiles: Any, classification: str) -> Any:
    pl = _polars()
    targets = targets.with_columns(
        pl.struct(["start_utc", "cutoff_lead_hours"]).map_elements(
            lambda row: cutoff_utc(row["start_utc"], row["cutoff_lead_hours"]),
            return_dtype=pl.String,
        ).alias("cutoff_utc")
    )
    home = targets.select(
        "game_id", "season", "season_type", "week", "start_utc", "cutoff_utc",
        pl.col("home_team_id").cast(pl.String).alias("team_id"),
        pl.col("away_team_id").cast(pl.String).alias("opponent_team_id"),
        pl.lit("HOME").alias("team_role"), "neutral_site",
    )
    away = targets.select(
        "game_id", "season", "season_type", "week", "start_utc", "cutoff_utc",
        pl.col("away_team_id").cast(pl.String).alias("team_id"),
        pl.col("home_team_id").cast(pl.String).alias("opponent_team_id"),
        pl.lit("AWAY").alias("team_role"), "neutral_site",
    )
    return pl.concat([home, away], how="vertical").sort(
        ["season", "start_utc", "game_id", "team_role"]
    ).join(profiles, on="team_id", how="left").with_columns(
        pl.col("exact_play_rows").is_null().alias("cold_start"),
        pl.when(pl.col("season") >= 2023)
        .then(pl.lit("2023_PLUS_FIRST_DOWN_CLOCK_RUNNING"))
        .otherwise(pl.lit("PRE_2023_FIRST_DOWN_CLOCK"))
        .alias("target_rule_era"),
        (pl.col("season") >= 2023).alias("rule_era_transfer_mismatch"),
        pl.lit(classification).alias("classification"),
        pl.lit(False).alias("protected_eligible"),
    )


def materialize(*, input_data_root: Path, output_data_root: Path, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    pl = _polars()
    contract_path = repo_root / "configs" / "preliminary_possession_pace_contract.json"
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    verified_source_manifests = _verify_source_manifests(input_data_root, contract)
    plays, drives, targets, team_map = _load_sources(input_data_root, contract)
    temporal = _validate_source_contract(plays, drives, targets, contract)
    profiles, counts = _build_profiles(plays, drives, team_map, contract)
    features = _build_target_features(targets, profiles, contract["classification"])
    expected_rows = targets.height * contract["acceptance"]["required_target_game_team_multiplier"]
    if features.height != expected_rows:
        raise ValueError("target-game/team feature population is not exactly two rows per target game")
    forbidden = {"home_win", "home_points", "away_points", "margin", "winner", "outcome"}
    if forbidden & set(features.columns):
        raise ValueError("target or outcome column present in candidate features")
    identity_payload = {
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "source_contract": contract["source_contract"],
        "verified_source_manifests": verified_source_manifests,
        "classification": contract["classification"],
        "profile_records": profiles.to_dicts(),
        "feature_records": features.to_dicts(),
    }
    dataset_identity = stable_hash(identity_payload)
    state_root = output_data_root / "pit_state" / "preliminary_possession_pace" / "sha256" / dataset_identity
    feature_root = output_data_root / "features" / "preliminary_possession_pace" / "sha256" / dataset_identity
    manifest_root = output_data_root / "manifests" / "preliminary_possession_pace" / "sha256" / dataset_identity
    for path in (state_root, feature_root, manifest_root):
        path.mkdir(parents=True, exist_ok=True)
    state_path = state_root / "team_possession_pace_profiles.parquet"
    feature_path = feature_root / "target_game_team_possession_pace_features.parquet"
    profiles.write_parquet(state_path, compression="zstd", statistics=True)
    features.write_parquet(feature_path, compression="zstd", statistics=True)
    payloads = [
        {
            "role": "DEVELOPMENT_ONLY_TEAM_PROFILE",
            "path": f"pit_state/preliminary_possession_pace/sha256/{dataset_identity}/team_possession_pace_profiles.parquet",
            "rows": profiles.height,
            "bytes": state_path.stat().st_size,
            "sha256": sha256_file(state_path),
        },
        {
            "role": "PRELIMINARY_UNPROTECTED_TARGET_FEATURES",
            "path": f"features/preliminary_possession_pace/sha256/{dataset_identity}/target_game_team_possession_pace_features.parquet",
            "rows": features.height,
            "bytes": feature_path.stat().st_size,
            "sha256": sha256_file(feature_path),
        },
    ]
    metric_names = list(contract["feature_contract"]["features"])
    manifest = {
        "schema_version": "1.0.0",
        "artifact_type": "PRELIMINARY_POSSESSION_PACE_WORKLOAD_CANDIDATE",
        "dataset_identity": dataset_identity,
        "issued_at_utc": issued_at_utc,
        "decision_unit": contract["decision_unit"],
        "parent_unit": contract["parent_unit"],
        "classification": contract["classification"],
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "source_contract": contract["source_contract"],
        "verified_source_manifests": verified_source_manifests,
        "population": {**counts, "source_seasons": contract["source_contract"]["source_seasons"], "target_seasons": contract["source_contract"]["target_seasons"], "target_games": targets.height, "target_game_team_rows": features.height, "cold_start_rows": features.filter(pl.col("cold_start")).height},
        "features": contract["feature_contract"]["features"],
        "feature_missingness": {name: features[name].null_count() for name in metric_names},
        "unsupported_fields": contract["feature_contract"]["unsupported_fields"],
        "temporal_validation": temporal,
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
        },
    }
    manifest_path = manifest_root / "run_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    return {"dataset_identity": dataset_identity, "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path), "manifest": manifest, "state_path": str(state_path), "feature_path": str(feature_path)}

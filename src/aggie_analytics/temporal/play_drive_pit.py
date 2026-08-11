from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


PLAY_IDENTITY = "714a856691a84bac8f822091a98bb8ef68f2473edd1924abd94b8c5045c3cfc5"
DRIVE_IDENTITY = "342be676be8a01ce00677a872e06fda73e607b26116ec971f09f5966d21891d0"
TARGET_REPLAY_IDENTITY = "cf732b78db6deff2e2cca51364a18e03219a5ceda88d2f5efa475dad1f7e3fe7"


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("historical play/drive materialization requires the optional data-engineering environment") from exc
    return polars


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp lacks timezone: {value}")
    return parsed.astimezone(timezone.utc)


def cutoff_utc(start_utc: str, lead_hours: int) -> str:
    value = parse_utc(start_utc) - timedelta(hours=int(lead_hours))
    return value.isoformat().replace("+00:00", "Z")


def classify_drive_result(value: str | None, contract: dict[str, Any]) -> tuple[bool, bool, bool]:
    normalized = (value or "").strip().upper()
    features = contract["feature_contract"]
    return (
        normalized in features["touchdown_drive_results"],
        normalized in features["field_goal_drive_results"],
        normalized in features["turnover_drive_results"],
    )


def _source_files(data_root: Path, identity: str, domain: str, seasons: list[int], name: str) -> list[Path]:
    base = data_root / "quarantine" / "historical_known_at" / "sha256" / identity / domain
    files = [base / f"season={season}" / name for season in seasons]
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing exact source payloads: {missing}")
    return files


def _load_sources(
    data_root: Path, contract: dict[str, Any]
) -> tuple[Any, Any, Any, Any]:
    pl = _polars()
    source = contract["source_contract"]
    seasons = [int(value) for value in source["source_seasons"]]
    play_files = _source_files(data_root, source["play_dataset_identity"], "plays", seasons, "candidate_play_rows.parquet")
    drive_files = _source_files(data_root, source["drive_dataset_identity"], "drives", seasons, "candidate_drive_rows.parquet")
    plays = pl.concat([pl.read_parquet(path) for path in play_files], how="vertical_relaxed")
    drives = pl.concat([pl.read_parquet(path) for path in drive_files], how="vertical_relaxed")
    target_path = (
        data_root / "features" / "historical_known_at" / "sha256"
        / source["target_replay_identity"] / "target_game_cutoffs.parquet"
    )
    if not target_path.is_file():
        raise FileNotFoundError(f"missing exact target cutoff payload: {target_path}")
    targets = pl.read_parquet(target_path)
    registry_path = (
        data_root / "canonical" / "BAT-387" / "sha256"
        / source["canonical_registry_sha256"] / "canonical_core_registry.csv"
    )
    if not registry_path.is_file() or sha256_file(registry_path) != source["canonical_registry_sha256"]:
        raise ValueError("canonical registry path or SHA-256 does not match the pinned contract")
    registry = pl.read_csv(registry_path, infer_schema_length=10000)
    team_map = registry.filter(
        (pl.col("record_type") == "ENTITY")
        & (pl.col("entity_type") == "team")
        & (pl.col("source_system_id") == "SRC-002")
        & (pl.col("resolution_state") == "AUTO_ACCEPTED_VERIFIED")
        & (pl.col("mapping_method") == source["canonical_team_mapping_method"])
    ).select(
        pl.col("source_entity_key").cast(pl.String).alias("source_team_id"),
        pl.col("canonical_id").alias("team_id"),
    )
    if team_map["source_team_id"].n_unique() != team_map.height:
        raise ValueError("pinned canonical team map is not one-to-one by source team ID")
    return plays, drives, targets, team_map


def _validate_source_contract(
    plays: Any, drives: Any, targets: Any, contract: dict[str, Any]
) -> dict[str, Any]:
    pl = _polars()
    source = contract["source_contract"]
    plays = plays.filter(pl.col("reconciliation_disposition") == source["play_disposition"])
    drives = drives.filter(pl.col("reconciliation_disposition") == source["drive_disposition"])
    if plays.is_empty() or drives.is_empty() or targets.is_empty():
        raise ValueError("exact play, drive, and target populations must all be nonempty")
    target_seasons = sorted(targets["season"].unique().to_list())
    if target_seasons != source["target_seasons"]:
        raise ValueError(f"target season drift: {target_seasons}")
    source_games = set(plays["canonical_game_id"].cast(pl.String).to_list())
    target_games = set(targets["game_id"].cast(pl.String).to_list())
    overlap = source_games & target_games
    if overlap:
        raise ValueError(f"target games present in source plays: {sorted(overlap)[:5]}")
    target_cutoffs = [cutoff_utc(row["start_utc"], row["cutoff_lead_hours"]) for row in targets.iter_rows(named=True)]
    minimum_cutoff = min(target_cutoffs, key=parse_utc)
    max_known_at = max(plays["source_known_at_utc"].drop_nulls().to_list(), key=parse_utc)
    max_effective = max(plays["effective_at_utc"].drop_nulls().to_list(), key=parse_utc)
    if parse_utc(max_known_at) > parse_utc(minimum_cutoff):
        raise ValueError("play source publication exceeds earliest target cutoff")
    if parse_utc(max_effective) >= parse_utc(minimum_cutoff):
        raise ValueError("play source effective time reaches earliest target cutoff")
    if drives["source_known_at_utc"].null_count() or plays["source_known_at_utc"].null_count():
        raise ValueError("exact source row has missing known-at timestamp")
    if plays["effective_at_utc"].null_count():
        raise ValueError("exact play row has missing effective timestamp")
    return {
        "minimum_target_cutoff_utc": minimum_cutoff,
        "maximum_source_known_at_utc": max_known_at,
        "maximum_source_effective_at_utc": max_effective,
        "target_game_overlap": 0,
    }


def _build_profiles(
    plays: Any, drives: Any, team_map: Any, contract: dict[str, Any]
) -> tuple[Any, dict[str, int]]:
    pl = _polars()
    source = contract["source_contract"]
    plays = plays.filter(pl.col("reconciliation_disposition") == source["play_disposition"])
    drives = drives.filter(pl.col("reconciliation_disposition") == source["drive_disposition"])
    plays = plays.with_columns(
        pl.col("offense_team_id").cast(pl.String).alias("source_team_id"),
        pl.col("canonical_game_id").cast(pl.String),
    ).join(team_map, on="source_team_id", how="left")
    source_exact_play_rows = plays.height
    unmapped_play_rows = plays["team_id"].null_count()
    plays = plays.filter(pl.col("team_id").is_not_null())
    play_profiles = (
        plays.group_by("team_id")
        .agg(
            pl.len().alias("play_count"),
            pl.col("canonical_game_id").n_unique().alias("play_game_count"),
            pl.col("season").n_unique().alias("play_season_count"),
            pl.col("epa").mean().alias("epa_mean"),
            pl.col("stat_yardage").mean().alias("stat_yardage_mean"),
            pl.col("rush").cast(pl.Float64).mean().alias("rush_rate"),
            pl.col("pass").cast(pl.Float64).mean().alias("pass_rate"),
            pl.col("scoring_play").cast(pl.Float64).mean().alias("scoring_play_rate"),
            pl.col("interception").cast(pl.Float64).mean().alias("interception_rate"),
            pl.col("sack").cast(pl.Float64).mean().alias("sack_rate"),
            pl.when(pl.col("pass_attempt") == True)  # noqa: E712
            .then(pl.col("completion").cast(pl.Float64))
            .otherwise(None)
            .mean()
            .alias("pass_completion_rate"),
            pl.col("source_known_at_utc").max().alias("source_known_at_utc"),
            pl.col("effective_at_utc").max().alias("source_effective_at_utc_max"),
        )
        .sort("team_id")
    )
    td_results = contract["feature_contract"]["touchdown_drive_results"]
    fg_results = contract["feature_contract"]["field_goal_drive_results"]
    to_results = contract["feature_contract"]["turnover_drive_results"]
    drives = drives.with_columns(
        pl.col("offense_team_id").cast(pl.String).alias("source_team_id"),
        pl.col("canonical_game_id").cast(pl.String),
        pl.col("drive_result").str.strip_chars().str.to_uppercase().alias("normalized_drive_result"),
    ).join(team_map, on="source_team_id", how="left")
    source_exact_drive_rows = drives.height
    unmapped_drive_rows = drives["team_id"].null_count()
    drives = drives.filter(pl.col("team_id").is_not_null())
    drive_profiles = (
        drives.group_by("team_id")
        .agg(
            pl.len().alias("drive_count"),
            pl.col("canonical_game_id").n_unique().alias("drive_game_count"),
            pl.col("source_play_rows").mean().alias("drive_plays_mean"),
            pl.col("normalized_drive_result").is_in(td_results).cast(pl.Float64).mean().alias("touchdown_drive_rate"),
            pl.col("normalized_drive_result").is_in(fg_results).cast(pl.Float64).mean().alias("field_goal_drive_rate"),
            pl.col("normalized_drive_result").is_in(to_results).cast(pl.Float64).mean().alias("turnover_drive_rate"),
        )
        .sort("team_id")
    )
    profiles = (
        play_profiles.join(drive_profiles, on="team_id", how="full", coalesce=True)
        .with_columns(
            pl.lit(True).alias("historical_known_at_eligible"),
            pl.lit("DEVELOPMENT_ONLY").alias("authority"),
        )
        .sort("team_id")
    )
    counts = {
        "exact_play_rows": source_exact_play_rows,
        "mapped_exact_play_rows": plays.height,
        "exact_play_games": plays["canonical_game_id"].n_unique(),
        "exact_drive_rows": source_exact_drive_rows,
        "mapped_exact_drive_rows": drives.height,
        "exact_drive_games": drives["canonical_game_id"].n_unique(),
        "profile_teams": profiles.height,
        "unmapped_exact_play_rows": unmapped_play_rows,
        "unmapped_exact_drive_rows": unmapped_drive_rows,
        "canonical_team_map_rows": team_map.height,
    }
    return profiles, counts


def _build_features(targets: Any, profiles: Any) -> Any:
    pl = _polars()
    targets = targets.with_columns(
        pl.struct(["start_utc", "cutoff_lead_hours"])
        .map_elements(lambda row: cutoff_utc(row["start_utc"], row["cutoff_lead_hours"]), return_dtype=pl.String)
        .alias("cutoff_utc")
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
    rows = pl.concat([home, away], how="vertical").sort(["season", "start_utc", "game_id", "team_role"])
    rows = rows.join(profiles, on="team_id", how="left")
    rows = rows.with_columns(
        pl.col("play_count").is_null().alias("cold_start"),
        pl.lit("DEVELOPMENT_ONLY_HISTORICAL_KNOWN_AT_PIT_AGGREGATE").alias("classification"),
        pl.lit(False).alias("protected_eligible"),
    )
    return rows


def materialize(
    *, input_data_root: Path, output_data_root: Path, repo_root: Path, issued_at_utc: str
) -> dict[str, Any]:
    pl = _polars()
    contract_path = repo_root / "configs" / "historical_play_drive_pit_aggregate_contract.json"
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    plays, drives, targets, team_map = _load_sources(input_data_root, contract)
    temporal = _validate_source_contract(plays, drives, targets, contract)
    profiles, counts = _build_profiles(plays, drives, team_map, contract)
    features = _build_features(targets, profiles)
    target_games = targets.height
    if features.height != target_games * contract["acceptance"]["required_target_game_team_multiplier"]:
        raise ValueError("target-game/team feature population is not exactly two rows per target game")
    source_games = set(plays.filter(pl.col("reconciliation_disposition") == contract["source_contract"]["play_disposition"])["canonical_game_id"].cast(pl.String).to_list())
    if any(game in source_games for game in features["game_id"].to_list()):
        raise ValueError("target-game leakage detected in feature source population")
    identity_payload = {
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "source_contract": contract["source_contract"],
        "classification": contract["classification"],
        "profile_records": profiles.to_dicts(),
        "feature_records": features.to_dicts(),
    }
    dataset_identity = stable_hash(identity_payload)
    state_root = output_data_root / "pit_state" / "historical_known_at" / "sha256" / dataset_identity
    feature_root = output_data_root / "features" / "historical_known_at" / "sha256" / dataset_identity
    manifest_root = output_data_root / "manifests" / "historical_known_at" / "sha256" / dataset_identity
    for path in (state_root, feature_root, manifest_root):
        path.mkdir(parents=True, exist_ok=True)
    state_path = state_root / "team_play_drive_profiles.parquet"
    feature_path = feature_root / "target_game_team_play_drive_features.parquet"
    profiles.write_parquet(state_path, compression="zstd", statistics=True)
    features.write_parquet(feature_path, compression="zstd", statistics=True)
    payloads = [
        {
            "role": "DEVELOPMENT_ONLY_PIT_TEAM_PROFILE",
            "path": "pit_state/historical_known_at/sha256/<dataset_identity>/team_play_drive_profiles.parquet",
            "rows": profiles.height,
            "bytes": state_path.stat().st_size,
            "sha256": sha256_file(state_path),
        },
        {
            "role": "DEVELOPMENT_ONLY_TARGET_GAME_TEAM_FEATURES",
            "path": "features/historical_known_at/sha256/<dataset_identity>/target_game_team_play_drive_features.parquet",
            "rows": features.height,
            "bytes": feature_path.stat().st_size,
            "sha256": sha256_file(feature_path),
        },
    ]
    manifest = {
        "schema_version": "1.0.0",
        "artifact_type": "HISTORICAL_PLAY_DRIVE_PIT_AGGREGATE",
        "decision_unit": contract["decision_unit"],
        "classification": contract["classification"],
        "dataset_identity": dataset_identity,
        "issued_at_utc": issued_at_utc,
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "source_contract": contract["source_contract"],
        "population": {
            **counts,
            "source_seasons": contract["source_contract"]["source_seasons"],
            "missing_source_seasons": contract["source_contract"]["missing_source_seasons"],
            "target_seasons": contract["source_contract"]["target_seasons"],
            "target_games": target_games,
            "target_game_team_rows": features.height,
            "cold_start_rows": features.filter(pl.col("cold_start")).height,
            "feature_columns": len(contract["feature_contract"]["play_features"] + contract["feature_contract"]["drive_features"]),
        },
        "temporal_validation": temporal,
        "missingness": {
            name: features[name].null_count()
            for name in contract["feature_contract"]["play_features"] + contract["feature_contract"]["drive_features"]
        },
        "payloads": payloads,
        "authority": contract["authority"],
        "negative_findings": [
            "The validated versioned repository has no source season for 2011 or 2020.",
            "Only exact cross-route canonical-game reconciliations from 2010-2022 are admitted; 2004-2009 source-level-only rows and current 2026 supplemental captures remain excluded.",
            "The profile is static for 2023-2025 targets because no later play/drive capture has an eligible historical publication time.",
            "Cold starts and null source statistics remain explicit; no missing value, target, outcome, or publication time is fabricated.",
            "This development-only PIT aggregate does not authorize protected training, protected evaluation, champion promotion, production forecasts, or scientific claims.",
        ],
        "scientific_nonclaims": {
            "historical_population_ready": False,
            "gap_002_resolved": False,
            "production_model_ready": False,
            "protected_performance_claimed": False,
            "tamu_specialization_lift_claimed": False,
            "bas_or_aggie_excess_result_claimed": False,
        },
    }
    manifest_path = manifest_root / "play_drive_pit_aggregate_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    return {
        "dataset_identity": dataset_identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "manifest": manifest,
        "state_path": str(state_path),
        "feature_path": str(feature_path),
    }


def remove_rebuild_root(path: Path) -> None:
    resolved = path.resolve()
    if "validation" not in {part.lower() for part in resolved.parts}:
        raise ValueError(f"refusing to clean non-validation path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)

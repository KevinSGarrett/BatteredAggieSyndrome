from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("player-event PIT materialization requires the optional data-engineering environment") from exc
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


def remove_rebuild_root(path: Path) -> None:
    resolved = path.resolve()
    if "validation" not in {part.lower() for part in resolved.parts}:
        raise ValueError(f"refusing to clean non-validation path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def _candidate_paths(data_root: Path, contract: dict[str, Any]) -> tuple[Path, list[Path], dict[str, Any]]:
    source = contract["source_contract"]
    identity = source["candidate_dataset_identity"]
    manifest_path = (
        data_root / "manifests" / "historical_known_at" / "sha256" / identity
        / "player_event_metric_reconciliation.json"
    )
    if not manifest_path.is_file() or sha256_file(manifest_path) != source["candidate_manifest_sha256"]:
        raise ValueError("candidate reconciliation manifest is absent or differs from the pinned SHA-256")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = data_root / "quarantine" / "historical_known_at" / "sha256" / identity / "player_event_metrics"
    payload_by_season = {int(item["season"]): item for item in manifest["payloads"]}
    files: list[Path] = []
    for season in source["source_seasons"]:
        payload = payload_by_season[int(season)]
        path = base / payload["name"]
        if not path.is_file() or sha256_file(path) != payload["sha256"] or path.stat().st_size != payload["bytes"]:
            raise ValueError(f"candidate payload identity drift for season {season}")
        files.append(path)
    return manifest_path, files, manifest


def _load_inputs(data_root: Path, contract: dict[str, Any]) -> tuple[Any, Any, dict[str, Any], Path]:
    pl = _polars()
    manifest_path, files, manifest = _candidate_paths(data_root, contract)
    candidates = pl.concat([pl.read_parquet(path) for path in files], how="diagonal_relaxed")
    target_path = (
        data_root / "features" / "historical_known_at" / "sha256"
        / contract["source_contract"]["target_replay_identity"] / "target_game_cutoffs.parquet"
    )
    if not target_path.is_file():
        raise FileNotFoundError(f"missing exact target cutoff payload: {target_path}")
    return candidates, pl.read_parquet(target_path), manifest, manifest_path


def disposition_counts(candidates: Any) -> dict[str, int]:
    return {
        str(row["reconciliation_disposition"]): int(row["len"])
        for row in candidates.group_by("reconciliation_disposition").len().iter_rows(named=True)
    }


def _validate_inputs(candidates: Any, targets: Any, contract: dict[str, Any]) -> dict[str, Any]:
    pl = _polars()
    source = contract["source_contract"]
    acceptance = contract["acceptance"]
    if candidates.height != acceptance["expected_candidate_rows"]:
        raise ValueError(f"candidate row drift: {candidates.height}")
    actual_dispositions = disposition_counts(candidates)
    if actual_dispositions != acceptance["expected_disposition_counts"]:
        raise ValueError("candidate reconciliation disposition population drift")
    if sorted(candidates["season"].unique().to_list()) != source["source_seasons"]:
        raise ValueError("candidate source season drift")
    if sorted(targets["season"].unique().to_list()) != source["target_seasons"]:
        raise ValueError("target season drift")
    eligible = candidates.filter(pl.col("reconciliation_disposition") == source["eligible_disposition"])
    if eligible.height != acceptance["expected_eligible_rows"]:
        raise ValueError("eligible population drift")
    required_nonnull = [
        "canonical_game_id", "canonical_player_id", "canonical_membership_player_id", "canonical_team_id",
        "source_known_at_utc", "source_commit_sha", "current_value", "row_lineage_sha256",
    ]
    if any(eligible[name].null_count() for name in required_nonnull):
        raise ValueError("eligible row lacks exact canonical identity, evidence, or value")
    if not eligible["current_value_exact"].all() or not eligible["current_player_name_match"].all():
        raise ValueError("eligible row lacks exact cross-route value or name reconciliation")
    if not (eligible["source_value"] == eligible["current_value"]).all():
        raise ValueError("eligible source/current value mismatch")
    if set(eligible["source_commit_sha"].unique().to_list()) != {source["source_commit_sha"]}:
        raise ValueError("source commit identity drift")
    if set(eligible["source_known_at_utc"].unique().to_list()) != {source["source_known_at_utc"]}:
        raise ValueError("source known-at identity drift")
    if set(eligible["canonical_membership_resolution_state"].unique().to_list()) != {
        source["canonical_membership_resolution_state"]
    }:
        raise ValueError("canonical membership resolution drift")
    if set(eligible["upstream_independence"].unique().to_list()) != {source["cross_route_independence"]}:
        raise ValueError("cross-route independence caveat drift")
    expected_metrics = {
        (item["category"], item["stat_type"], item["aggregation"]) for item in contract["metric_contract"]
    }
    actual_metrics = set(eligible.select("category", "stat_type", "aggregation").unique().iter_rows())
    if actual_metrics != expected_metrics:
        raise ValueError("eligible metric schema drift")
    cutoffs = [cutoff_utc(row["start_utc"], row["cutoff_lead_hours"]) for row in targets.iter_rows(named=True)]
    minimum_cutoff = min(cutoffs, key=parse_utc)
    if parse_utc(source["source_known_at_utc"]) > parse_utc(minimum_cutoff):
        raise ValueError("source publication exceeds earliest target cutoff")
    source_games = set(eligible["canonical_game_id"].to_list())
    target_games = set(targets["game_id"].to_list())
    overlap = source_games & target_games
    if overlap:
        raise ValueError(f"target-game overlap detected: {sorted(overlap)[:5]}")
    if max(source["source_seasons"]) >= min(source["target_seasons"]):
        raise ValueError("source seasons are not strictly before target seasons")
    return {
        "minimum_target_cutoff_utc": minimum_cutoff,
        "maximum_source_known_at_utc": source["source_known_at_utc"],
        "target_game_overlap": 0,
        "source_season_before_target_season": True,
        "disposition_counts": actual_dispositions,
    }


def _admitted_state(candidates: Any, contract: dict[str, Any]) -> Any:
    pl = _polars()
    source = contract["source_contract"]
    return (
        candidates.filter(pl.col("reconciliation_disposition") == source["eligible_disposition"])
        .select(
            "observation_id", "season", "game_id", "canonical_game_id", "player_id", "canonical_player_id",
            "canonical_membership_player_id", "canonical_team_id", "canonical_team_label", "category", "stat_type",
            "aggregation", "source_value", "source_event_rows", "source_capture_id", "source_payload_sha256",
            "source_commit_sha", "source_known_at_utc", "source_schema_sha256", "source_aggregate_evidence_sha256",
            "current_capture_id", "current_payload_sha256", "current_request_sha256", "upstream_independence",
            "reconciliation_disposition", "row_lineage_sha256",
        )
        .with_columns(
            pl.lit("DEVELOPMENT_ONLY_HISTORICAL_KNOWN_AT_PLAYER_EVENT_METRIC").alias("admission_state"),
            pl.lit(False).alias("official_player_box_complete"),
            pl.col("season").is_in(source["partial_source_seasons"]).alias("partial_source_season"),
            pl.lit(False).alias("protected_eligible"),
        )
        .sort(["season", "canonical_game_id", "canonical_team_id", "canonical_player_id", "category", "stat_type"])
    )


def _build_profiles(state: Any, contract: dict[str, Any]) -> Any:
    pl = _polars()
    expressions: list[Any] = [
        pl.col("canonical_game_id").n_unique().alias("source_game_count"),
        pl.col("season").n_unique().alias("source_season_count"),
        pl.col("canonical_player_id").n_unique().alias("contributing_player_count"),
        pl.len().alias("metric_observation_count"),
        pl.col("source_known_at_utc").max().alias("source_known_at_utc"),
        pl.col("partial_source_season").any().alias("includes_partial_source_season"),
    ]
    for item in contract["metric_contract"]:
        match = (pl.col("category") == item["category"]) & (pl.col("stat_type") == item["stat_type"])
        expressions.extend(
            [
                pl.when(match).then(pl.col("source_value")).otherwise(None).sum().alias(item["feature_name"]),
                match.cast(pl.Int64).sum().alias(f"{item['feature_name']}_metric_rows"),
            ]
        )
    profiles = state.group_by("canonical_team_id").agg(*expressions).rename({"canonical_team_id": "team_id"})
    derived: list[Any] = []
    for item in contract["metric_contract"]:
        name = item["feature_name"]
        derived.append(
            pl.when(pl.col(f"{name}_metric_rows") > 0)
            .then(pl.col(name).cast(pl.Float64) / pl.col("source_game_count"))
            .otherwise(None)
            .alias(f"{name}_per_source_game")
        )
    profiles = profiles.with_columns(*derived)
    profiles = profiles.with_columns(
        pl.when(pl.col("rushing_attempts") > 0)
        .then(pl.col("rushing_yds").cast(pl.Float64) / pl.col("rushing_attempts"))
        .otherwise(None)
        .alias("rushing_yds_per_attempt"),
        pl.when(pl.col("receiving_receptions") > 0)
        .then(pl.col("receiving_yds").cast(pl.Float64) / pl.col("receiving_receptions"))
        .otherwise(None)
        .alias("receiving_yds_per_reception"),
        pl.lit("DEVELOPMENT_ONLY").alias("authority"),
        pl.lit(False).alias("protected_eligible"),
    )
    return profiles.sort("team_id")


def _build_features(targets: Any, profiles: Any, contract: dict[str, Any]) -> Any:
    pl = _polars()
    targets = targets.with_columns(
        pl.struct(["start_utc", "cutoff_lead_hours"])
        .map_elements(lambda row: cutoff_utc(row["start_utc"], row["cutoff_lead_hours"]), return_dtype=pl.String)
        .alias("cutoff_utc")
    )
    common = ["game_id", "season", "season_type", "week", "start_utc", "cutoff_utc", "neutral_site"]
    home = targets.select(
        *common,
        pl.col("home_team_id").alias("team_id"), pl.col("away_team_id").alias("opponent_team_id"),
        pl.lit("HOME").alias("team_role"),
    )
    away = targets.select(
        *common,
        pl.col("away_team_id").alias("team_id"), pl.col("home_team_id").alias("opponent_team_id"),
        pl.lit("AWAY").alias("team_role"),
    )
    return (
        pl.concat([home, away], how="vertical")
        .join(profiles, on="team_id", how="left")
        .with_columns(
            pl.col("source_game_count").is_null().alias("cold_start"),
            pl.lit(contract["classification"]).alias("classification"),
            pl.lit(False).alias("official_player_box_complete"),
            pl.lit(False).alias("protected_eligible"),
        )
        .sort(["season", "start_utc", "game_id", "team_role"])
    )


def materialize(
    *, input_data_root: Path, output_data_root: Path, repo_root: Path, issued_at_utc: str,
    contract_name: str = "historical_player_event_metric_pit_contract.json",
) -> dict[str, Any]:
    pl = _polars()
    contract_path = repo_root / "configs" / contract_name
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    candidates, targets, source_manifest, source_manifest_path = _load_inputs(input_data_root, contract)
    temporal = _validate_inputs(candidates, targets, contract)
    state = _admitted_state(candidates, contract)
    profiles = _build_profiles(state, contract)
    features = _build_features(targets, profiles, contract)
    if features.height != targets.height * contract["acceptance"]["required_target_game_team_multiplier"]:
        raise ValueError("target-game/team feature population is not exactly two rows per target game")
    lineage_digest = hashlib.sha256("\n".join(state["row_lineage_sha256"].to_list()).encode("utf-8")).hexdigest()
    identity_payload = {
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "candidate_manifest_sha256": sha256_file(source_manifest_path),
        "admitted_lineage_sha256": lineage_digest,
        "profile_records": profiles.to_dicts(),
        "feature_records": features.to_dicts(),
        "classification": contract["classification"],
    }
    identity = stable_hash(identity_payload)
    state_root = output_data_root / "pit_state" / "historical_known_at" / "sha256" / identity
    feature_root = output_data_root / "features" / "historical_known_at" / "sha256" / identity
    manifest_root = output_data_root / "manifests" / "historical_known_at" / "sha256" / identity
    for path in (state_root, feature_root, manifest_root):
        path.mkdir(parents=True, exist_ok=True)
    state_path = state_root / "player_event_metrics.parquet"
    profile_path = state_root / "team_player_event_metric_profiles.parquet"
    feature_path = feature_root / "target_game_team_player_event_features.parquet"
    state.write_parquet(state_path, compression="zstd", statistics=True)
    profiles.write_parquet(profile_path, compression="zstd", statistics=True)
    features.write_parquet(feature_path, compression="zstd", statistics=True)
    feature_names = (
        contract["feature_contract"]["base_features"]
        + contract["feature_contract"]["per_game_features"]
        + contract["feature_contract"]["efficiency_features"]
    )
    payload_paths = [state_path, profile_path, feature_path]
    payload_roles = ["ADMITTED_PLAYER_EVENT_METRIC_STATE", "DEVELOPMENT_ONLY_TEAM_PROFILE", "TARGET_GAME_TEAM_FEATURE_CANDIDATE"]
    payloads = [
        {"role": role, "name": path.name, "rows": pl.read_parquet(path).height, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for role, path in zip(payload_roles, payload_paths, strict=True)
    ]
    disposition = temporal["disposition_counts"]
    per_season = [
        {
            "season": int(season),
            "eligible_rows": state.filter(pl.col("season") == season).height,
            "games": state.filter(pl.col("season") == season)["canonical_game_id"].n_unique(),
            "players": state.filter(pl.col("season") == season)["canonical_player_id"].n_unique(),
            "partial_source_season": int(season) in contract["source_contract"]["partial_source_seasons"],
        }
        for season in contract["source_contract"]["source_seasons"]
    ]
    manifest = {
        "schema_version": "1.0.0",
        "artifact_type": "HISTORICAL_PLAYER_EVENT_METRIC_PIT",
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "classification": contract["classification"],
        "dataset_identity": identity,
        "issued_at_utc": issued_at_utc,
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "source_manifest_sha256": sha256_file(source_manifest_path),
        "source_contract": contract["source_contract"],
        "admitted_lineage_sha256": lineage_digest,
        "population": {
            "candidate_rows": candidates.height,
            "eligible_rows": state.height,
            "excluded_or_quarantined_rows": candidates.height - state.height,
            "eligible_games": state["canonical_game_id"].n_unique(),
            "eligible_players": state["canonical_player_id"].n_unique(),
            "eligible_teams": state["canonical_team_id"].n_unique(),
            "profile_teams": profiles.height,
            "source_seasons": contract["source_contract"]["source_seasons"],
            "partial_source_seasons": contract["source_contract"]["partial_source_seasons"],
            "target_seasons": contract["source_contract"]["target_seasons"],
            "target_games": targets.height,
            "target_game_team_rows": features.height,
            "cold_start_rows": features.filter(pl.col("cold_start")).height,
            "feature_columns": len(feature_names),
            "per_season": per_season,
            "disposition_counts": disposition,
        },
        "temporal_validation": {key: value for key, value in temporal.items() if key != "disposition_counts"},
        "missingness": {name: features[name].null_count() for name in feature_names},
        "payloads": payloads,
        "source_dataset_version": source_manifest["dataset_version"],
        "authority": contract["authority"],
        "negative_findings": contract["negative_findings"],
        "scientific_nonclaims": {
            "historical_population_ready": False,
            "gap_002_resolved": False,
            "production_model_ready": False,
            "protected_performance_claimed": False,
            "tamu_specialization_lift_claimed": False,
            "bas_or_aggie_excess_result_claimed": False,
        },
    }
    manifest_path = manifest_root / "player_event_metric_pit_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    return {
        "dataset_identity": identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "state_path": str(state_path),
        "profile_path": str(profile_path),
        "feature_path": str(feature_path),
        "manifest": manifest,
    }

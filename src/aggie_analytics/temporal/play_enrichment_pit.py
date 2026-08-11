from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


POSITION_COLUMNS = [
    "position_reception", "position_target", "position_completion", "position_incompletion",
    "position_sack_taken", "position_sack", "position_interception_thrown", "position_interception",
    "position_fumble", "position_fumble_forced", "position_fumble_recovered", "position_pass_breakup",
    "position_rush", "position_touchdown",
]
PLAYER_ID_COLUMNS = [
    "rush_player_id", "reception_player_id", "completion_player_id", "interception_player_id",
    "interception_thrown_player_id", "touchdown_player_id", "incompletion_player_id", "target_player_id",
    "fumble_recovered_player_id", "fumble_forced_player_id", "fumble_player_id", "sack_player_id",
    "sack_taken_player_id", "pass_breakup_player_id",
]
SOURCE_MODEL_COLUMNS = ["EPA", "wpa", "success", "ppa"]
EVENT_COLUMNS = [
    "rush", "pass", "sack", "int", "completion", "pass_attempt", "target", "touchdown", "turnover",
    "penalty_flag", "rz_play", "scoring_opp", "middle_8", "stuffed_run",
]


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("play-enrichment PIT materialization requires the optional data-engineering environment") from exc
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


def _verified_payloads(
    *, data_root: Path, identity: str, manifest_name: str, manifest_sha256: str,
    payload_domain: str, seasons: list[int], payload_name: str,
) -> tuple[Path, list[Path], dict[str, Any]]:
    manifest_path = data_root / "manifests" / "historical_known_at" / "sha256" / identity / manifest_name
    if not manifest_path.is_file() or sha256_file(manifest_path) != manifest_sha256:
        raise ValueError(f"{manifest_name} is absent or differs from the pinned SHA-256")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload_by_season = {int(item["season"]): item for item in manifest["payloads"]}
    base = data_root / "quarantine" / "historical_known_at" / "sha256" / identity / payload_domain
    files: list[Path] = []
    for season in seasons:
        item = payload_by_season[int(season)]
        expected_name = f"season={season}/{payload_name}"
        if item["name"] != expected_name:
            raise ValueError(f"payload name drift for season {season}: {item['name']}")
        path = base / item["name"]
        if not path.is_file() or sha256_file(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
            raise ValueError(f"payload identity drift for season {season}")
        files.append(path)
    return manifest_path, files, manifest


def _candidate_columns() -> list[str]:
    return [
        "observation_id", "season", "game_id", "sequence_number", "canonical_game_id", "pos_team",
        "def_pos_team", "base_play_observation_id", "base_canonical_game_id", "base_source_epa",
        "base_source_wpa", "source_epa_delta_from_base", "source_wpa_delta_from_base",
        "base_play_text_match", "base_reconciliation_disposition", "base_source_record_evidence_sha256",
        "base_row_lineage_sha256", "source_capture_id", "source_payload_sha256", "source_commit_sha",
        "source_known_at_utc", "source_schema_sha256", "source_record_evidence_sha256", "metric_authority",
        "player_identity_contract", "reconciliation_disposition", "row_lineage_sha256",
        *SOURCE_MODEL_COLUMNS, *EVENT_COLUMNS, *POSITION_COLUMNS, *PLAYER_ID_COLUMNS,
    ]


def _load_inputs(data_root: Path, contract: dict[str, Any]) -> tuple[Any, Any, Any, Any, dict[str, Any], Path, Path]:
    pl = _polars()
    source = contract["source_contract"]
    candidate_manifest_path, candidate_files, candidate_manifest = _verified_payloads(
        data_root=data_root,
        identity=source["candidate_dataset_identity"],
        manifest_name="play_enrichment_reconciliation.json",
        manifest_sha256=source["candidate_manifest_sha256"],
        payload_domain="play_enrichment",
        seasons=source["candidate_source_seasons"],
        payload_name="candidate_play_enrichment_rows.parquet",
    )
    base_manifest_path, base_files, _ = _verified_payloads(
        data_root=data_root,
        identity=source["base_play_dataset_identity"],
        manifest_name="play_history_reconciliation.json",
        manifest_sha256=source["base_play_manifest_sha256"],
        payload_domain="plays",
        seasons=source["exact_link_source_seasons"],
        payload_name="candidate_play_rows.parquet",
    )
    candidates = pl.concat(
        [pl.read_parquet(path, columns=_candidate_columns()) for path in candidate_files],
        how="diagonal_relaxed",
    )
    base_columns = [
        "observation_id", "season", "canonical_game_id", "sequence_number", "offense_team_id",
        "defense_team_id", "effective_at_utc", "source_known_at_utc", "source_record_evidence_sha256",
        "reconciliation_disposition", "row_lineage_sha256",
    ]
    base_plays = pl.concat(
        [pl.read_parquet(path, columns=base_columns) for path in base_files],
        how="diagonal_relaxed",
    )
    target_path = (
        data_root / "features" / "historical_known_at" / "sha256"
        / source["target_replay_identity"] / "target_game_cutoffs.parquet"
    )
    if not target_path.is_file() or sha256_file(target_path) != source["target_cutoff_payload_sha256"]:
        raise ValueError("target cutoff payload is absent or differs from the pinned SHA-256")
    registry_path = (
        data_root / "canonical" / "BAT-387" / "sha256"
        / source["canonical_registry_sha256"] / "canonical_core_registry.csv"
    )
    if not registry_path.is_file() or sha256_file(registry_path) != source["canonical_registry_sha256"]:
        raise ValueError("canonical registry is absent or differs from the pinned SHA-256")
    registry = pl.read_csv(registry_path, infer_schema_length=10000)
    team_map = registry.filter(
        (pl.col("record_type") == "ENTITY")
        & (pl.col("entity_type") == "team")
        & (pl.col("source_system_id") == source["source_system_id"])
        & (pl.col("resolution_state") == "AUTO_ACCEPTED_VERIFIED")
        & (pl.col("mapping_method") == source["canonical_team_mapping_method"])
    ).select(
        pl.col("source_entity_key").cast(pl.String).alias("source_team_id"),
        pl.col("canonical_id").alias("team_id"),
    )
    if team_map["source_team_id"].n_unique() != team_map.height:
        raise ValueError("pinned canonical team map is not one-to-one by source team ID")
    return (
        candidates,
        base_plays,
        pl.read_parquet(target_path),
        team_map,
        candidate_manifest,
        candidate_manifest_path,
        base_manifest_path,
    )


def disposition_counts(candidates: Any) -> dict[str, int]:
    return {
        str(row["reconciliation_disposition"]): int(row["len"])
        for row in candidates.group_by("reconciliation_disposition").len().iter_rows(named=True)
    }


def _join_exact_rows(candidates: Any, base_plays: Any, team_map: Any, contract: dict[str, Any]) -> Any:
    pl = _polars()
    source = contract["source_contract"]
    exact = candidates.filter(
        pl.col("reconciliation_disposition") == source["eligible_enrichment_disposition"]
    )
    base = base_plays.rename(
        {
            "observation_id": "joined_base_observation_id",
            "season": "base_season",
            "canonical_game_id": "joined_base_canonical_game_id",
            "sequence_number": "base_sequence_number",
            "source_known_at_utc": "base_source_known_at_utc",
            "source_record_evidence_sha256": "joined_base_source_record_evidence_sha256",
            "reconciliation_disposition": "joined_base_reconciliation_disposition",
            "row_lineage_sha256": "joined_base_row_lineage_sha256",
        }
    )
    return (
        exact.join(
            base,
            left_on="base_play_observation_id",
            right_on="joined_base_observation_id",
            how="left",
        )
        .with_columns(pl.col("offense_team_id").cast(pl.String).alias("source_team_id"))
        .join(team_map, on="source_team_id", how="left")
    )


def _validate_inputs(candidates: Any, base_plays: Any, targets: Any, joined: Any, contract: dict[str, Any]) -> dict[str, Any]:
    pl = _polars()
    source = contract["source_contract"]
    acceptance = contract["acceptance"]
    if candidates.height != acceptance["expected_candidate_rows"]:
        raise ValueError(f"candidate row drift: {candidates.height}")
    actual_dispositions = disposition_counts(candidates)
    if actual_dispositions != acceptance["expected_disposition_counts"]:
        raise ValueError("candidate reconciliation disposition population drift")
    if sorted(candidates["season"].unique().to_list()) != source["candidate_source_seasons"]:
        raise ValueError("candidate source season drift")
    if sorted(targets["season"].unique().to_list()) != source["target_seasons"]:
        raise ValueError("target season drift")
    if joined.height != acceptance["expected_exact_link_rows"]:
        raise ValueError("exact-link population drift")
    if joined["base_play_observation_id"].n_unique() != joined.height:
        raise ValueError("enrichment exact-link observation identity is not unique")
    if base_plays["observation_id"].n_unique() != base_plays.height:
        raise ValueError("base-play observation identity is not unique")
    required_nonnull = [
        "base_play_observation_id", "joined_base_canonical_game_id", "offense_team_id", "defense_team_id",
        "effective_at_utc", "source_known_at_utc", "source_commit_sha", "row_lineage_sha256",
        "joined_base_row_lineage_sha256",
    ]
    if any(joined[name].null_count() for name in required_nonnull):
        raise ValueError("exact enrichment row lacks base-play identity, team, timing, or lineage")
    if not (joined["canonical_game_id"] == joined["joined_base_canonical_game_id"]).all():
        raise ValueError("enrichment/base-play canonical game mismatch")
    if not (joined["base_canonical_game_id"] == joined["joined_base_canonical_game_id"]).all():
        raise ValueError("recorded base canonical game differs from the pinned base play")
    if not (joined["season"] == joined["base_season"]).all():
        raise ValueError("enrichment/base-play season mismatch")
    if not (joined["sequence_number"].cast(pl.String) == joined["base_sequence_number"].cast(pl.String)).all():
        raise ValueError("enrichment/base-play sequence mismatch")
    if not joined["base_play_text_match"].all():
        raise ValueError("exact enrichment row lacks exact base-play text agreement")
    if set(joined["base_reconciliation_disposition"].unique().to_list()) != {
        source["eligible_base_play_disposition"]
    }:
        raise ValueError("recorded base-play reconciliation disposition drift")
    if set(joined["joined_base_reconciliation_disposition"].unique().to_list()) != {
        source["eligible_base_play_disposition"]
    }:
        raise ValueError("joined base-play reconciliation disposition drift")
    if not (joined["base_row_lineage_sha256"] == joined["joined_base_row_lineage_sha256"]).all():
        raise ValueError("recorded base-play lineage differs from the pinned base row")
    if not (
        joined["base_source_record_evidence_sha256"]
        == joined["joined_base_source_record_evidence_sha256"]
    ).all():
        raise ValueError("recorded base-play evidence differs from the pinned base row")
    if set(joined["source_commit_sha"].unique().to_list()) != {source["source_commit_sha"]}:
        raise ValueError("source commit identity drift")
    if set(joined["source_known_at_utc"].unique().to_list()) != {source["source_known_at_utc"]}:
        raise ValueError("source known-at identity drift")
    mapped = joined.filter(pl.col("team_id").is_not_null())
    unmapped = joined.filter(pl.col("team_id").is_null())
    if mapped.height != acceptance["expected_verified_team_mapped_rows"]:
        raise ValueError("verified-team-mapped population drift")
    if unmapped.height != acceptance["expected_unmapped_exact_link_rows"]:
        raise ValueError("unmapped exact-link population drift")
    if sorted(unmapped["source_team_id"].unique().to_list()) != acceptance["expected_unmapped_source_team_ids"]:
        raise ValueError("unmapped source-team identity drift")
    cutoffs = [cutoff_utc(row["start_utc"], row["cutoff_lead_hours"]) for row in targets.iter_rows(named=True)]
    minimum_cutoff = min(cutoffs, key=parse_utc)
    maximum_known_at = max(joined["source_known_at_utc"].to_list(), key=parse_utc)
    maximum_effective = max(joined["effective_at_utc"].to_list(), key=parse_utc)
    if parse_utc(maximum_known_at) > parse_utc(minimum_cutoff):
        raise ValueError("source publication exceeds earliest target cutoff")
    if parse_utc(maximum_effective) >= parse_utc(minimum_cutoff):
        raise ValueError("base-play effective time reaches earliest target cutoff")
    overlap = set(mapped["canonical_game_id"].cast(pl.String).to_list()) & set(
        targets["game_id"].cast(pl.String).to_list()
    )
    if overlap:
        raise ValueError(f"target-game overlap detected: {sorted(overlap)[:5]}")
    if max(source["exact_link_source_seasons"]) >= min(source["target_seasons"]):
        raise ValueError("source seasons are not strictly before target seasons")
    return {
        "minimum_target_cutoff_utc": minimum_cutoff,
        "maximum_source_known_at_utc": maximum_known_at,
        "maximum_source_effective_at_utc": maximum_effective,
        "target_game_overlap": 0,
        "source_season_before_target_season": True,
        "disposition_counts": actual_dispositions,
        "exact_link_rows": joined.height,
        "verified_team_mapped_rows": mapped.height,
        "unmapped_exact_link_rows": unmapped.height,
    }


def _row_flags(frame: Any) -> Any:
    pl = _polars()
    return frame.with_columns(
        pl.any_horizontal([pl.col(name).is_not_null() for name in POSITION_COLUMNS]).alias("has_position_candidate"),
        pl.any_horizontal([pl.col(name) == "?" for name in POSITION_COLUMNS]).alias("has_unknown_position_candidate"),
        pl.any_horizontal([pl.col(name).is_not_null() for name in PLAYER_ID_COLUMNS]).alias("has_source_player_id_candidate"),
    )


def _admitted_state(joined: Any, contract: dict[str, Any]) -> Any:
    pl = _polars()
    source = contract["source_contract"]
    selected = [
        "observation_id", "season", "game_id", "sequence_number", "canonical_game_id",
        "base_play_observation_id", "source_team_id", "team_id", "offense_team_id", "defense_team_id",
        "effective_at_utc", "source_capture_id", "source_payload_sha256", "source_commit_sha",
        "source_known_at_utc", "source_schema_sha256", "source_record_evidence_sha256",
        "base_source_record_evidence_sha256", "base_row_lineage_sha256", "row_lineage_sha256",
        "metric_authority", "player_identity_contract", "base_source_epa", "base_source_wpa",
        "source_epa_delta_from_base", "source_wpa_delta_from_base", *SOURCE_MODEL_COLUMNS,
        *EVENT_COLUMNS, *POSITION_COLUMNS, "has_position_candidate", "has_unknown_position_candidate",
        "has_source_player_id_candidate",
    ]
    return (
        _row_flags(joined.filter(pl.col("team_id").is_not_null()))
        .select(*selected)
        .with_columns(
            pl.lit("DEVELOPMENT_ONLY_HISTORICAL_KNOWN_AT_EXACT_PLAY_ENRICHMENT").alias("admission_state"),
            pl.lit(False).alias("canonical_player_identity_promoted"),
            pl.lit(False).alias("official_stat_authority"),
            pl.lit(False).alias("protected_eligible"),
            pl.col("season").is_in(source["partial_source_seasons"]).alias("partial_source_season"),
        )
        .sort(["season", "canonical_game_id", "sequence_number", "observation_id"])
    )


def _unmapped_quarantine(joined: Any) -> Any:
    pl = _polars()
    return (
        joined.filter(pl.col("team_id").is_null())
        .select(
            "observation_id", "season", "game_id", "sequence_number", "canonical_game_id",
            "base_play_observation_id", "source_team_id", "pos_team", "def_pos_team", "offense_team_id",
            "defense_team_id", "source_known_at_utc", "effective_at_utc", "source_record_evidence_sha256",
            "base_source_record_evidence_sha256", "row_lineage_sha256", "base_row_lineage_sha256",
        )
        .with_columns(
            pl.lit("QUARANTINE_EXACT_PLAY_ENRICHMENT_SOURCE_TEAM_UNMAPPED").alias("quarantine_reason"),
            pl.lit("NO_NAME_ONLY_TEAM_MAPPING").alias("identity_policy"),
        )
        .sort(["season", "canonical_game_id", "sequence_number", "observation_id"])
    )


def _mean_rate(name: str, alias: str) -> Any:
    pl = _polars()
    return pl.col(name).cast(pl.Float64).mean().alias(alias)


def _build_profiles(state: Any) -> Any:
    pl = _polars()
    return (
        state.group_by("team_id")
        .agg(
            pl.len().alias("source_play_count"),
            pl.col("canonical_game_id").n_unique().alias("source_game_count"),
            pl.col("season").n_unique().alias("source_season_count"),
            pl.col("has_position_candidate").cast(pl.Int64).sum().alias("position_candidate_row_count"),
            pl.col("has_unknown_position_candidate").cast(pl.Int64).sum().alias("unknown_position_row_count"),
            pl.col("has_source_player_id_candidate").cast(pl.Int64).sum().alias("source_player_id_candidate_row_count"),
            pl.col("EPA").mean().alias("source_epa_mean"),
            pl.col("wpa").mean().alias("source_wpa_mean"),
            _mean_rate("success", "source_success_rate"),
            pl.col("ppa").mean().alias("source_ppa_mean"),
            pl.col("source_epa_delta_from_base").cast(pl.Float64).abs().mean().alias("source_epa_revision_mean_abs"),
            pl.col("source_wpa_delta_from_base").cast(pl.Float64).abs().mean().alias("source_wpa_revision_mean_abs"),
            _mean_rate("rush", "rush_rate"),
            _mean_rate("pass", "pass_rate"),
            _mean_rate("sack", "sack_rate"),
            _mean_rate("int", "interception_rate"),
            pl.when(pl.col("pass_attempt") == 1)
            .then(pl.col("completion").cast(pl.Float64))
            .otherwise(None)
            .mean()
            .alias("completion_rate_on_pass_attempt"),
            _mean_rate("target", "target_rate"),
            _mean_rate("touchdown", "touchdown_rate"),
            _mean_rate("turnover", "turnover_rate"),
            _mean_rate("penalty_flag", "penalty_rate"),
            _mean_rate("rz_play", "red_zone_play_rate"),
            _mean_rate("scoring_opp", "scoring_opportunity_rate"),
            _mean_rate("middle_8", "middle_eight_rate"),
            _mean_rate("stuffed_run", "stuffed_run_rate"),
            pl.col("source_known_at_utc").max().alias("source_known_at_utc"),
            pl.col("effective_at_utc").max().alias("maximum_source_effective_at_utc"),
        )
        .with_columns(
            (pl.col("position_candidate_row_count") / pl.col("source_play_count")).alias("position_candidate_rate"),
            (pl.col("unknown_position_row_count") / pl.col("source_play_count")).alias("unknown_position_rate"),
            (pl.col("source_player_id_candidate_row_count") / pl.col("source_play_count"))
            .alias("source_player_id_candidate_rate"),
            pl.lit("SOURCE_MODEL_CANDIDATE_NOT_OFFICIAL").alias("metric_authority"),
            pl.lit("DEVELOPMENT_ONLY").alias("authority"),
            pl.lit(False).alias("protected_eligible"),
        )
        .sort("team_id")
    )


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
        pl.col("home_team_id").alias("team_id"),
        pl.col("away_team_id").alias("opponent_team_id"),
        pl.lit("HOME").alias("team_role"),
    )
    away = targets.select(
        *common,
        pl.col("away_team_id").alias("team_id"),
        pl.col("home_team_id").alias("opponent_team_id"),
        pl.lit("AWAY").alias("team_role"),
    )
    return (
        pl.concat([home, away], how="vertical")
        .join(profiles, on="team_id", how="left")
        .with_columns(
            pl.col("source_play_count").is_null().alias("cold_start"),
            pl.lit(contract["classification"]).alias("classification"),
            pl.lit(False).alias("canonical_player_identity_promoted"),
            pl.lit(False).alias("official_stat_authority"),
            pl.lit(False).alias("protected_eligible"),
        )
        .sort(["season", "start_utc", "game_id", "team_role"])
    )


def _feature_names(contract: dict[str, Any]) -> list[str]:
    feature = contract["feature_contract"]
    return (
        feature["base_features"]
        + feature["source_model_features"]
        + feature["event_rate_features"]
        + feature["candidate_coverage_features"]
    )


def materialize(
    *, input_data_root: Path, output_data_root: Path, repo_root: Path, issued_at_utc: str,
    contract_name: str = "historical_play_enrichment_pit_contract.json",
) -> dict[str, Any]:
    pl = _polars()
    contract_path = repo_root / "configs" / contract_name
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    candidates, base_plays, targets, team_map, source_manifest, source_manifest_path, base_manifest_path = (
        _load_inputs(input_data_root, contract)
    )
    joined = _join_exact_rows(candidates, base_plays, team_map, contract)
    temporal = _validate_inputs(candidates, base_plays, targets, joined, contract)
    state = _admitted_state(joined, contract)
    quarantine = _unmapped_quarantine(joined)
    profiles = _build_profiles(state)
    features = _build_features(targets, profiles, contract)
    if features.height != targets.height * contract["acceptance"]["required_target_game_team_multiplier"]:
        raise ValueError("target-game/team feature population is not exactly two rows per target game")
    lineage_digest = hashlib.sha256("\n".join(state["row_lineage_sha256"].to_list()).encode("utf-8")).hexdigest()
    quarantine_digest = hashlib.sha256(
        "\n".join(quarantine["row_lineage_sha256"].to_list()).encode("utf-8")
    ).hexdigest()
    identity_payload = {
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "candidate_manifest_sha256": sha256_file(source_manifest_path),
        "base_play_manifest_sha256": sha256_file(base_manifest_path),
        "admitted_lineage_sha256": lineage_digest,
        "unmapped_quarantine_lineage_sha256": quarantine_digest,
        "profile_records": profiles.to_dicts(),
        "feature_records": features.to_dicts(),
        "classification": contract["classification"],
    }
    identity = stable_hash(identity_payload)
    state_root = output_data_root / "pit_state" / "historical_known_at" / "sha256" / identity
    feature_root = output_data_root / "features" / "historical_known_at" / "sha256" / identity
    quarantine_root = output_data_root / "quarantine" / "historical_known_at" / "sha256" / identity
    manifest_root = output_data_root / "manifests" / "historical_known_at" / "sha256" / identity
    for path in (state_root, feature_root, quarantine_root, manifest_root):
        path.mkdir(parents=True, exist_ok=True)
    state_path = state_root / "play_enrichment.parquet"
    profile_path = state_root / "team_play_enrichment_profiles.parquet"
    feature_path = feature_root / "target_game_team_play_enrichment_features.parquet"
    quarantine_path = quarantine_root / "unmapped_source_team_rows.parquet"
    state.write_parquet(state_path, compression="zstd", statistics=True)
    profiles.write_parquet(profile_path, compression="zstd", statistics=True)
    features.write_parquet(feature_path, compression="zstd", statistics=True)
    quarantine.write_parquet(quarantine_path, compression="zstd", statistics=True)
    payload_paths = [state_path, profile_path, feature_path, quarantine_path]
    payload_roles = [
        "ADMITTED_EXACT_LINKED_PLAY_ENRICHMENT_STATE",
        "DEVELOPMENT_ONLY_TEAM_PROFILE",
        "TARGET_GAME_TEAM_FEATURE_CANDIDATE",
        "UNMAPPED_SOURCE_TEAM_QUARANTINE",
    ]
    payloads = [
        {
            "role": role,
            "name": path.name,
            "rows": pl.read_parquet(path).height,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for role, path in zip(payload_roles, payload_paths, strict=True)
    ]
    feature_names = _feature_names(contract)
    per_season: list[dict[str, Any]] = []
    for season in contract["source_contract"]["candidate_source_seasons"]:
        candidate_season = candidates.filter(pl.col("season") == season)
        state_season = state.filter(pl.col("season") == season)
        quarantine_season = quarantine.filter(pl.col("season") == season)
        exact_rows = candidate_season.filter(
            pl.col("reconciliation_disposition")
            == contract["source_contract"]["eligible_enrichment_disposition"]
        ).height
        per_season.append(
            {
                "season": int(season),
                "candidate_rows": candidate_season.height,
                "exact_link_rows": exact_rows,
                "admitted_rows": state_season.height,
                "unmapped_team_quarantine_rows": quarantine_season.height,
                "admitted_games": state_season["canonical_game_id"].n_unique() if state_season.height else 0,
                "admitted_teams": state_season["team_id"].n_unique() if state_season.height else 0,
                "rows_with_position_candidate": (
                    state_season.filter(pl.col("has_position_candidate")).height if state_season.height else 0
                ),
                "rows_with_unknown_position_candidate": (
                    state_season.filter(pl.col("has_unknown_position_candidate")).height if state_season.height else 0
                ),
                "source_metric_nulls": {
                    name: state_season[name].null_count() if state_season.height else 0
                    for name in SOURCE_MODEL_COLUMNS
                },
                "partial_source_season": int(season) in contract["source_contract"]["partial_source_seasons"],
            }
        )
    manifest = {
        "schema_version": "1.0.0",
        "artifact_type": "HISTORICAL_EXACT_LINKED_PLAY_ENRICHMENT_PIT",
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "classification": contract["classification"],
        "dataset_identity": identity,
        "issued_at_utc": issued_at_utc,
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "source_manifest_sha256": sha256_file(source_manifest_path),
        "base_play_manifest_sha256": sha256_file(base_manifest_path),
        "source_contract": contract["source_contract"],
        "admitted_lineage_sha256": lineage_digest,
        "unmapped_quarantine_lineage_sha256": quarantine_digest,
        "population": {
            "candidate_rows": candidates.height,
            "exact_link_rows": temporal["exact_link_rows"],
            "admitted_rows": state.height,
            "unmapped_exact_link_rows": quarantine.height,
            "excluded_or_quarantined_rows": candidates.height - state.height,
            "admitted_games": state["canonical_game_id"].n_unique(),
            "admitted_teams": state["team_id"].n_unique(),
            "profile_teams": profiles.height,
            "candidate_source_seasons": contract["source_contract"]["candidate_source_seasons"],
            "exact_link_source_seasons": contract["source_contract"]["exact_link_source_seasons"],
            "partial_source_seasons": contract["source_contract"]["partial_source_seasons"],
            "target_seasons": contract["source_contract"]["target_seasons"],
            "target_games": targets.height,
            "target_game_team_rows": features.height,
            "cold_start_rows": features.filter(pl.col("cold_start")).height,
            "feature_columns": len(feature_names),
            "rows_with_position_candidate": state.filter(pl.col("has_position_candidate")).height,
            "rows_with_unknown_position_candidate": state.filter(pl.col("has_unknown_position_candidate")).height,
            "rows_with_source_player_id_candidate": state.filter(pl.col("has_source_player_id_candidate")).height,
            "per_season": per_season,
            "disposition_counts": temporal["disposition_counts"],
        },
        "temporal_validation": {key: value for key, value in temporal.items() if key != "disposition_counts"},
        "feature_missingness": {name: features[name].null_count() for name in feature_names},
        "admitted_source_metric_missingness": {name: state[name].null_count() for name in SOURCE_MODEL_COLUMNS},
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
    manifest_path = manifest_root / "play_enrichment_pit_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    return {
        "dataset_identity": identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "state_path": str(state_path),
        "profile_path": str(profile_path),
        "feature_path": str(feature_path),
        "quarantine_path": str(quarantine_path),
        "manifest": manifest,
    }

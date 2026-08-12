from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from aggie_analytics.temporal.play_drive_pit import canonical_json_bytes, parse_utc, sha256_file, stable_hash


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("postgame collapse taxonomy requires the optional data-engineering environment") from exc
    return polars


def oriented_team_taxonomy(
    *, final_margin: float, expected_margin: float | None,
    observed_leads: Iterable[float], late_observed_leads: Iterable[float],
    lead_thresholds: Iterable[int] = (7, 14, 21),
    residual_thresholds: Iterable[int] = (3, 7, 14, 21),
) -> dict[str, Any]:
    leads = [float(value) for value in observed_leads]
    late_leads = [float(value) for value in late_observed_leads]
    maximum_lead = max([0.0, *leads])
    lost = final_margin < 0
    residual = None if expected_margin is None else final_margin - expected_margin
    row: dict[str, Any] = {
        "maximum_observed_lead": maximum_lead,
        "maximum_late_observed_lead": max([0.0, *late_leads]),
        "largest_lead_surrendered": maximum_lead if lost else None,
        "fourth_quarter_lead_surrendered": bool(lost and any(value > 0 for value in late_leads)),
        "actual_margin": float(final_margin),
        "national_expected_margin": expected_margin,
        "national_expected_margin_residual": residual,
    }
    for threshold in lead_thresholds:
        row[f"lead_surrendered_{threshold}"] = bool(lost and maximum_lead >= threshold)
    for threshold in residual_thresholds:
        row[f"downside_residual_{threshold}"] = None if residual is None else bool(residual <= -threshold)
    return row


def _verify(path: Path, expected_sha256: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = sha256_file(path)
    if actual.lower() != expected_sha256.lower():
        raise ValueError(f"pinned input drift for {path}: expected {expected_sha256}, found {actual}")
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": actual}


def _input_paths(data_root: Path, contract: dict[str, Any]) -> dict[str, Path]:
    source = contract["source_contract"]
    return {name: data_root / source[name] for name in (
        "acquisition_manifest", "canonical_registry", "outcome_targets", "national_reference_predictions"
    )}


def _load_plays(data_root: Path, acquisition: dict[str, Any], contract: dict[str, Any]) -> tuple[Any, list[dict[str, Any]]]:
    pl = _polars()
    seasons = set(contract["source_contract"]["seasons"])
    requests = [row for row in acquisition["requests"] if row.get("dataset") == "plays" and row.get("result") == "SUCCESS" and int(row.get("parameters", {}).get("year", -1)) in seasons]
    frames: list[Any] = []
    captures: list[dict[str, Any]] = []
    for request in sorted(requests, key=lambda row: row["request_id"]):
        raw_path = data_root / request["immutable_path"]
        verified = _verify(raw_path, request["response_sha256"])
        rows = json.loads(raw_path.read_text(encoding="utf-8"))
        if len(rows) != int(request["row_count"]):
            raise ValueError(f"row-count drift for {request['request_id']}")
        frame = pl.DataFrame(rows, infer_schema_length=None).select(
            pl.col("gameId").cast(pl.String).alias("source_game_id"),
            pl.col("id").cast(pl.String).alias("source_play_id"),
            pl.col("playNumber").cast(pl.Int64, strict=False).alias("play_number"),
            pl.col("period").cast(pl.Int64, strict=False),
            pl.col("clock").struct.field("minutes").cast(pl.Int64, strict=False).alias("clock_minutes"),
            pl.col("clock").struct.field("seconds").cast(pl.Int64, strict=False).alias("clock_seconds"),
            pl.col("offense").cast(pl.String), pl.col("defense").cast(pl.String),
            pl.col("home").cast(pl.String), pl.col("away").cast(pl.String),
            pl.col("offenseScore").cast(pl.Int64, strict=False).alias("offense_score"),
            pl.col("defenseScore").cast(pl.Int64, strict=False).alias("defense_score"),
            pl.lit(request["capture_id"]).alias("source_capture_id"),
            pl.lit(request["response_sha256"]).alias("source_payload_sha256"),
            pl.lit(request["capture_known_at_utc"]).alias("source_known_at_utc"),
        ).with_columns(
            pl.when(pl.col("offense") == pl.col("home")).then(pl.col("offense_score")).when(pl.col("defense") == pl.col("home")).then(pl.col("defense_score")).otherwise(None).alias("home_score"),
            pl.when(pl.col("offense") == pl.col("away")).then(pl.col("offense_score")).when(pl.col("defense") == pl.col("away")).then(pl.col("defense_score")).otherwise(None).alias("away_score"),
        )
        frames.append(frame)
        captures.append({
            "request_id": request["request_id"], "capture_id": request["capture_id"],
            "season": int(request["parameters"]["year"]), "season_type": request["parameters"]["seasonType"],
            "week": int(request["parameters"]["week"]), "rows": len(rows), **verified,
        })
    if not frames:
        raise ValueError("no eligible play captures")
    plays = pl.concat(frames, how="vertical_relaxed")
    if plays["source_play_id"].null_count() or plays["source_play_id"].n_unique() != plays.height:
        raise ValueError("source play identities are null or duplicated")
    return plays, captures


def _game_map(registry: Any, seasons: list[int]) -> Any:
    pl = _polars()
    return registry.filter(
        (pl.col("record_type") == "ENTITY") & (pl.col("entity_type") == "game")
        & (pl.col("source_system_id") == "SRC-002") & pl.col("season").is_in(seasons)
        & (pl.col("resolution_state") == "AUTO_ACCEPTED_VERIFIED")
    ).select(
        pl.col("source_entity_key").alias("source_game_id"), pl.col("canonical_id").alias("canonical_game_id"),
        "season", "season_type", "week", "start_time_utc", "home_team_id", "away_team_id", "neutral_site", "provenance_sha256",
    )


def _build_taxonomy(plays: Any, games: Any, outcomes: Any, references: Any, contract: dict[str, Any]) -> tuple[Any, Any, Any, dict[str, Any]]:
    pl = _polars()
    source = contract["source_contract"]
    valid = plays.filter(
        pl.col("home_score").is_not_null() & pl.col("away_score").is_not_null()
        & (pl.col("home_score") >= 0) & (pl.col("away_score") >= 0) & pl.col("period").is_not_null()
    ).with_columns((pl.col("home_score") - pl.col("away_score")).alias("home_lead"))
    game_states = valid.group_by("source_game_id").agg(
        pl.len().alias("valid_score_state_rows"),
        pl.col("home_lead").max().alias("home_maximum_observed_lead"),
        (-pl.col("home_lead").min()).alias("away_maximum_observed_lead"),
        pl.col("home_lead").filter(pl.col("period") >= 4).max().alias("home_maximum_late_observed_lead"),
        (-pl.col("home_lead").filter(pl.col("period") >= 4).min()).alias("away_maximum_late_observed_lead"),
        pl.col("home_score").max().alias("recorded_final_home_score"),
        pl.col("away_score").max().alias("recorded_final_away_score"),
        pl.col("source_capture_id").unique().sort().str.join(";").alias("source_capture_ids"),
        pl.col("source_payload_sha256").unique().sort().str.join(";").alias("source_payload_sha256s"),
        pl.col("source_known_at_utc").max().alias("source_known_at_utc_max"),
    )
    outcomes = outcomes.filter(pl.col("season").is_in(source["seasons"]))
    references = references.filter(
        (pl.col("model_id") == source["national_reference_model_id"])
        & (pl.col("model_identity") == source["national_reference_model_identity"])
    ).select("target_game_id", "model_id", "model_identity", "predicted_margin", "dataset_identity", "feature_identity", "target_identity", "split_identity")
    joined = (
        games.join(game_states, on="source_game_id", how="inner", validate="1:1")
        .join(outcomes, left_on="canonical_game_id", right_on="target_game_id", how="inner", validate="1:1", suffix="_outcome")
        .join(references, left_on="canonical_game_id", right_on="target_game_id", how="left", validate="1:1")
        .with_columns(
            (pl.col("recorded_final_home_score") == pl.col("home_points")).alias("recorded_final_home_match"),
            (pl.col("recorded_final_away_score") == pl.col("away_points")).alias("recorded_final_away_match"),
        )
    )
    mismatches = joined.filter(~(pl.col("recorded_final_home_match") & pl.col("recorded_final_away_match")))
    admitted = joined.filter(pl.col("recorded_final_home_match") & pl.col("recorded_final_away_match"))
    game_rows: list[dict[str, Any]] = []
    team_rows: list[dict[str, Any]] = []
    for row in admitted.sort(["season", "start_utc", "canonical_game_id"]).to_dicts():
        expected = row["predicted_margin"]
        home = oriented_team_taxonomy(final_margin=float(row["margin"]), expected_margin=expected, observed_leads=[row["home_maximum_observed_lead"]], late_observed_leads=[row["home_maximum_late_observed_lead"] or 0], lead_thresholds=contract["taxonomy"]["lead_thresholds"], residual_thresholds=contract["taxonomy"]["downside_residual_thresholds"])
        away = oriented_team_taxonomy(final_margin=float(-row["margin"]), expected_margin=None if expected is None else -float(expected), observed_leads=[row["away_maximum_observed_lead"]], late_observed_leads=[row["away_maximum_late_observed_lead"] or 0], lead_thresholds=contract["taxonomy"]["lead_thresholds"], residual_thresholds=contract["taxonomy"]["downside_residual_thresholds"])
        shared = {
            "classification": contract["classification"], "canonical_game_id": row["canonical_game_id"], "source_game_id": row["source_game_id"],
            "season": row["season"], "season_type": row["season_type"], "week": int(row["week"]), "start_utc": row["start_utc"],
            "neutral_site": str(row["neutral_site"]).lower() == "true", "home_team_id": row["home_team_id"], "away_team_id": row["away_team_id"],
            "home_points": row["home_points"], "away_points": row["away_points"], "valid_score_state_rows": row["valid_score_state_rows"],
            "source_capture_ids": row["source_capture_ids"], "source_payload_sha256s": row["source_payload_sha256s"], "source_known_at_utc_max": row["source_known_at_utc_max"],
            "canonical_game_provenance_sha256": row["provenance_sha256"], "reference_model_id": row["model_id"], "reference_model_identity": row["model_identity"],
            "reference_dataset_identity": row["dataset_identity"], "reference_feature_identity": row["feature_identity"], "reference_target_identity": row["target_identity"],
            "reference_split_identity": row["split_identity"], "historical_original_pit_eligible": False, "pregame_feature_eligible": False, "protected_eligible": False,
        }
        game_rows.append({**shared, "home_maximum_observed_lead": home["maximum_observed_lead"], "away_maximum_observed_lead": away["maximum_observed_lead"], "home_fourth_quarter_lead_surrendered": home["fourth_quarter_lead_surrendered"], "away_fourth_quarter_lead_surrendered": away["fourth_quarter_lead_surrendered"], "home_national_expected_margin_residual": home["national_expected_margin_residual"], "away_national_expected_margin_residual": away["national_expected_margin_residual"]})
        for role, team_id, opponent_id, values in (("HOME", row["home_team_id"], row["away_team_id"], home), ("AWAY", row["away_team_id"], row["home_team_id"], away)):
            team_rows.append({**{key: value for key, value in shared.items() if key not in {"home_team_id", "away_team_id"}}, "team_role": role, "team_id": team_id, "opponent_team_id": opponent_id, **values})
    games_frame = pl.DataFrame(game_rows, infer_schema_length=None).sort(["season", "start_utc", "canonical_game_id"])
    teams_frame = pl.DataFrame(team_rows, infer_schema_length=None).sort(["season", "start_utc", "canonical_game_id", "team_role"])
    coverage = (
        outcomes.group_by(["season", "season_type"]).agg(pl.len().alias("outcome_games"))
        .join(games.group_by(["season", "season_type"]).agg(pl.len().alias("registry_games")), on=["season", "season_type"], how="left")
        .join(game_states.join(games, on="source_game_id", how="inner").group_by(["season", "season_type"]).agg(pl.len().alias("play_games")), on=["season", "season_type"], how="left")
        .join(games_frame.group_by(["season", "season_type"]).agg(pl.len().alias("admitted_games")), on=["season", "season_type"], how="left")
        .fill_null(0).with_columns((pl.col("admitted_games") / pl.col("outcome_games")).alias("admitted_outcome_coverage")).sort(["season", "season_type"])
    )
    findings = {
        "source_play_rows": plays.height, "valid_score_state_rows": valid.height, "source_play_games": plays["source_game_id"].n_unique(),
        "valid_score_state_games": game_states.height, "canonical_registry_games": games.height, "outcome_games": outcomes.height, "reference_games": references.height,
        "joined_games_before_final_score_gate": joined.height, "final_score_mismatch_games": mismatches.height, "admitted_games": games_frame.height, "admitted_team_rows": teams_frame.height,
    }
    return games_frame, teams_frame, coverage, findings


def materialize(*, input_data_root: Path, output_data_root: Path, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    pl = _polars()
    parse_utc(issued_at_utc)
    contract_path = repo_root / "configs" / "preliminary_postgame_collapse_taxonomy_contract.json"
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    paths = _input_paths(input_data_root, contract)
    source = contract["source_contract"]
    verified_inputs = {name: _verify(paths[name], source[f"{name}_sha256"]) for name in paths}
    acquisition = json.loads(paths["acquisition_manifest"].read_text(encoding="utf-8"))
    plays, captures = _load_plays(input_data_root, acquisition, contract)
    registry = pl.read_csv(paths["canonical_registry"], infer_schema_length=10_000)
    game_taxonomy, team_taxonomy, coverage, findings = _build_taxonomy(
        plays, _game_map(registry, source["seasons"]), pl.read_parquet(paths["outcome_targets"]), pl.read_parquet(paths["national_reference_predictions"]), contract
    )
    dataset_identity = stable_hash({"contract_sha256": hashlib.sha256(contract_bytes).hexdigest(), "verified_inputs": verified_inputs, "capture_identities": captures, "game_records": game_taxonomy.to_dicts(), "team_records": team_taxonomy.to_dicts(), "coverage_records": coverage.to_dicts()})
    feature_root = output_data_root / "features" / "postgame_collapse_taxonomy" / "sha256" / dataset_identity
    manifest_root = output_data_root / "manifests" / "postgame_collapse_taxonomy" / "sha256" / dataset_identity
    feature_root.mkdir(parents=True, exist_ok=True)
    manifest_root.mkdir(parents=True, exist_ok=True)
    payloads = []
    for name, frame, role in (("game_postgame_taxonomy.parquet", game_taxonomy, "POSTGAME_GAME_TAXONOMY"), ("team_game_postgame_taxonomy.parquet", team_taxonomy, "POSTGAME_TEAM_GAME_TAXONOMY"), ("season_domain_coverage.parquet", coverage, "SEASON_DOMAIN_COVERAGE")):
        path = feature_root / name
        frame.write_parquet(path, compression="zstd", statistics=True)
        payloads.append({"name": name, "role": role, "rows": frame.height, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": "1.0.0", "artifact_type": "PRELIMINARY_POSTGAME_COLLAPSE_DOWNSIDE_TAXONOMY", "dataset_identity": dataset_identity,
        "issued_at_utc": issued_at_utc, "classification": contract["classification"], "decision_unit": contract["decision_unit"], "jira_key": contract["jira_key"],
        "feature_umbrella": contract["feature_umbrella"], "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(), "verified_inputs": verified_inputs,
        "capture_count": len(captures), "capture_identities": captures, "population": findings, "coverage": coverage.to_dicts(), "taxonomy": contract["taxonomy"],
        "eligibility": contract["eligibility"], "authority": contract["authority"], "payloads": payloads, "negative_findings": contract["negative_findings"],
        "scientific_nonclaims": {"historical_population_ready": False, "production_model_ready": False, "champion_promoted": False, "protected_performance_claimed": False, "tamu_specialization_lift_claimed": False, "bas_or_aggie_excess_result_claimed": False, "coaching_or_causal_effect_claimed": False},
    }
    manifest_path = manifest_root / "run_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    return {"dataset_identity": dataset_identity, "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path), "manifest": manifest}

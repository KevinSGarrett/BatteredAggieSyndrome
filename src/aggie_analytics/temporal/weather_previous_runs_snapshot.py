from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("weather previous-runs snapshot materialization requires the optional data-engineering environment") from exc
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


def _duplicate_groups(frame: Any, keys: Iterable[str]) -> int:
    return frame.group_by(list(keys)).len().filter(_polars().col("len") > 1).height


def _validate_contract_authority(contract: dict[str, Any]) -> None:
    authority = contract["authority"]
    required_true = ("candidate_snapshot_materialization", "nominal_lead_semantics_verified")
    if any(authority.get(key) is not True for key in required_true):
        raise ValueError("weather nominal-lead candidate authority is not explicitly enabled")
    required_false = (
        "immutable_raw_capture_mutation", "canonical_weather_mutation", "exact_run_initialization_inference",
        "api_availability_inference", "venue_effective_time_backcast", "observed_weather_substitution",
        "historical_pit_admission", "preliminary_chronological_replay_admission", "protected_training_admission",
        "protected_evaluation_admission", "champion_or_production_promotion", "forecast_publication",
    )
    if any(authority.get(key) is not False for key in required_false):
        raise ValueError("weather authority boundary is open beyond nominal-lead candidate use")


def _load_candidates(
    data_root: Path, contract: dict[str, Any]
) -> tuple[Any, dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    pl = _polars()
    source, expected = contract["source_contract"], contract["acceptance"]
    manifest_path = data_root / Path(source["candidate_manifest_relative_path"])
    if not manifest_path.is_file() or sha256_file(manifest_path) != source["candidate_manifest_sha256"]:
        raise ValueError("weather candidate manifest identity drift")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_identity") != source["candidate_dataset_identity"]:
        raise ValueError("weather candidate dataset identity drift")
    if manifest.get("domain") != "weather_previous_runs" or manifest.get("grain") != "GAME_FORECAST_VALID_HOUR_VARIABLE_NOMINAL_LEAD":
        raise ValueError("weather candidate domain or grain drift")
    payloads = sorted(manifest.get("payloads", []), key=lambda item: int(item["season"]))
    if len(payloads) != expected["expected_source_files"]:
        raise ValueError("weather candidate file count drift")
    required = set(contract["disposition"]["snapshot_fields"]) - {"capture_known_at_utc"}
    required |= {"admission_state"}
    payload_root = data_root / Path(source["candidate_payload_root"])
    frames, profiles = [], []
    for item in payloads:
        season, path = int(item["season"]), payload_root / Path(item["name"])
        if not path.is_file() or path.stat().st_size != int(item["bytes"]) or sha256_file(path) != item["sha256"]:
            raise ValueError(f"weather candidate payload identity drift for {season}")
        frame = pl.read_parquet(path)
        if frame.height != int(item["rows"]) or set(frame.columns) < required:
            raise ValueError(f"weather candidate population or schema drift for {season}")
        if frame["season"].n_unique() != 1 or int(frame["season"][0]) != season:
            raise ValueError(f"weather candidate season drift for {season}")
        profiles.append({
            "season": season,
            "rows": frame.height,
            "bytes": path.stat().st_size,
            "sha256": item["sha256"],
            "physical_schema_sha256": stable_hash(sorted((name, str(dtype)) for name, dtype in frame.schema.items())),
        })
        frames.append(frame)
    capture_refs = manifest.get("capture_refs", [])
    if len(capture_refs) != expected["expected_capture_manifests"]:
        raise ValueError("weather capture-manifest population drift")
    capture_rows = []
    capture_hashes = []
    capture_root = data_root / Path(source["capture_manifest_root"])
    for ref in sorted(capture_refs, key=lambda item: item["request_id"]):
        path = capture_root / f"{ref['request_id']}.json"
        if not path.is_file() or sha256_file(path) != ref["capture_manifest_sha256"]:
            raise ValueError(f"weather capture manifest identity drift: {ref['request_id']}")
        capture = json.loads(path.read_text(encoding="utf-8"))
        if capture.get("capture_id") != ref["capture_id"] or capture.get("request_id") != ref["request_id"]:
            raise ValueError("weather capture request/capture identity drift")
        if capture.get("response_sha256") != ref["raw_sha256"] or int(capture.get("response_bytes", -1)) != int(ref["raw_bytes"]):
            raise ValueError("weather capture response identity drift")
        capture_hashes.append(ref["capture_manifest_sha256"])
        capture_rows.append({
            "source_capture_id": ref["capture_id"],
            "source_request_id": ref["request_id"],
            "capture_known_at_utc": capture["captured_at_utc"],
            "capture_response_sha256": capture["response_sha256"],
        })
    candidates = pl.concat(frames, how="diagonal_relaxed")
    capture_frame = pl.DataFrame(capture_rows)
    candidates = candidates.join(capture_frame, on=["source_capture_id", "source_request_id"], how="left", validate="m:1")
    if candidates["capture_known_at_utc"].null_count() or candidates.filter(
        pl.col("source_response_sha256") != pl.col("capture_response_sha256")
    ).height:
        raise ValueError("weather candidate-to-capture linkage drift")
    candidates = candidates.drop("capture_response_sha256")
    capture_profile = {
        "capture_manifests": len(capture_rows),
        "capture_manifest_aggregate_sha256": stable_hash(capture_hashes),
        "minimum_capture_known_at_utc": min(row["capture_known_at_utc"] for row in capture_rows),
        "maximum_capture_known_at_utc": max(row["capture_known_at_utc"] for row in capture_rows),
    }
    return candidates, manifest, profiles, capture_profile


def _disposition(candidates: Any, contract: dict[str, Any]) -> tuple[Any, Any, dict[str, Any]]:
    pl = _polars()
    rules, expected, source = contract["disposition"], contract["acceptance"], contract["source_contract"]
    eligible = (
        (pl.col("reconciliation_disposition") == rules["eligible_reconciliation_disposition"])
        & pl.col("source_value").is_not_null()
    )
    nonadmitted_rule = (
        (pl.col("reconciliation_disposition") == rules["nonadmitted_reconciliation_disposition"])
        & pl.col("source_value").is_null()
    )
    unexpected = candidates.filter(~eligible & ~nonadmitted_rule)
    if unexpected.height:
        raise ValueError("unexpected weather disposition or missingness state")
    candidate_source, nonadmitted = candidates.filter(eligible), candidates.filter(nonadmitted_rule)
    if candidate_source.height != expected["expected_candidate_cells"] or nonadmitted.height != expected["expected_nonadmitted_cells"]:
        raise ValueError("weather disposition population drift")
    if _duplicate_groups(candidates, ["observation_id"]) != expected["expected_duplicate_observation_ids"]:
        raise ValueError("duplicate weather observation identity")
    if _duplicate_groups(candidate_source, rules["natural_key"]) != expected["expected_duplicate_natural_keys"]:
        raise ValueError("duplicate candidate weather natural key")
    if set(rules["forbidden_snapshot_fields"]) & set(rules["snapshot_fields"]):
        raise ValueError("forbidden weather fields configured for snapshot")
    if candidates.filter(pl.col("weather_model") != source["weather_model"]).height:
        raise ValueError("weather model identity drift")
    if candidates.filter(pl.col("historical_known_at_state") != source["historical_known_at_state"]).height:
        raise ValueError("weather historical known-at boundary drift")
    if candidates.filter(pl.col("venue_coordinate_effective_time_state") != source["venue_coordinate_effective_time_state"]).height:
        raise ValueError("weather venue-coordinate authority drift")
    if candidates.filter(pl.col("historical_model_run_initialization_at_utc").is_not_null()).height:
        raise ValueError("weather exact model-run initialization was fabricated")
    if candidates.filter(pl.col("historical_api_available_at_utc").is_not_null()).height:
        raise ValueError("weather historical API availability was fabricated")
    if candidates.filter(pl.col("observed_weather_substitution") != False).height:
        raise ValueError("observed/reanalysis weather substitution entered candidate")
    if candidates.filter(pl.col("nominal_lead_hours") != pl.col("lead_days") * 24).height:
        raise ValueError("weather nominal lead-hour semantics drift")
    expected_source_variable = pl.concat_str(
        [pl.col("weather_variable"), pl.lit("_previous_day"), pl.col("lead_days").cast(pl.String)]
    )
    if candidates.filter(pl.col("source_variable") != expected_source_variable).height:
        raise ValueError("weather source-variable lead suffix drift")
    valid_at = pl.col("forecast_valid_hour_utc").str.to_datetime(format="%Y-%m-%dT%H:%M:%SZ", time_zone="UTC")
    nominal_at = pl.col("nominal_prediction_at_utc").str.to_datetime(format="%Y-%m-%dT%H:%M:%SZ", time_zone="UTC")
    if candidates.filter(nominal_at != valid_at - pl.duration(days=pl.col("lead_days"))).height:
        raise ValueError("weather fixed-lead nominal timestamp drift")
    kickoff_at = pl.col("kickoff_at_utc").str.to_datetime(time_zone="UTC")
    calculated_offset = (kickoff_at - valid_at).dt.total_minutes()
    if candidates.filter(calculated_offset != pl.col("kickoff_minus_valid_hour_minutes")).height:
        raise ValueError("weather kickoff-to-valid-hour alignment drift")
    snapshot = candidate_source.select(rules["snapshot_fields"]).with_columns(
        pl.lit(True).alias("nominal_lead_reference_only"),
        pl.lit(False).alias("historical_pit_eligible"),
        pl.lit(False).alias("preliminary_replay_eligible"),
        pl.lit(False).alias("protected_eligible"),
    )
    nonadmitted = nonadmitted.with_columns(
        pl.lit("ARCHIVE_VARIABLE_NOT_AVAILABLE_NO_VALUE_FABRICATED").alias("nonadmission_reason"),
        pl.lit(False).alias("historical_pit_eligible"),
        pl.lit(False).alias("preliminary_replay_eligible"),
        pl.lit(False).alias("protected_eligible"),
    )

    def by_season(frame: Any) -> dict[str, int]:
        return {str(row["season"]): int(row["len"]) for row in frame.group_by("season").len().sort("season").iter_rows(named=True)}

    source_game_seasons = candidates.select("season", "source_game_id").unique()
    source_games_by_season = {
        str(row["season"]): int(row["len"])
        for row in source_game_seasons.group_by("season").len().sort("season").iter_rows(named=True)
    }
    profile = {
        "source_cells": candidates.height,
        "source_games": candidates["source_game_id"].n_unique(),
        "source_requests": candidates["source_request_id"].n_unique(),
        "source_captures": candidates["source_capture_id"].n_unique(),
        "variables": candidates["weather_variable"].n_unique(),
        "leads": candidates["lead_days"].n_unique(),
        "candidate_cells": snapshot.height,
        "candidate_games": snapshot["source_game_id"].n_unique(),
        "nonadmitted_cells": nonadmitted.height,
        "nonadmitted_games": nonadmitted["source_game_id"].n_unique(),
        "dome_context_cells": candidates.filter(pl.col("venue_dome_current_catalog")).height,
        "candidate_dome_context_cells": snapshot.filter(pl.col("venue_dome_current_catalog")).height,
        "missing_source_value_cells": candidates["source_value"].null_count(),
        "missing_game_id_cells": candidates["canonical_game_id_candidate"].null_count(),
        "missing_venue_id_cells": candidates["venue_id_candidate"].null_count(),
        "missing_coordinate_cells": candidates.filter(pl.col("requested_latitude").is_null() | pl.col("requested_longitude").is_null()).height,
        "candidate_by_season": by_season(snapshot),
        "nonadmitted_by_season": by_season(nonadmitted),
        "source_cells_by_season": by_season(candidates),
        "source_games_by_season": source_games_by_season,
        "lead_hours": sorted(int(value) for value in candidates["nominal_lead_hours"].unique().to_list()),
        "kickoff_offset_minutes": sorted(int(value) for value in candidates["kickoff_minus_valid_hour_minutes"].unique().to_list()),
    }
    comparisons = {
        "source_cells": "expected_source_cells", "source_games": "expected_source_games", "source_requests": "expected_source_requests",
        "source_captures": "expected_source_captures", "variables": "expected_variables", "leads": "expected_leads",
        "candidate_cells": "expected_candidate_cells", "candidate_games": "expected_candidate_games",
        "nonadmitted_cells": "expected_nonadmitted_cells", "nonadmitted_games": "expected_nonadmitted_games",
        "dome_context_cells": "expected_dome_context_cells", "candidate_dome_context_cells": "expected_candidate_dome_context_cells",
        "missing_source_value_cells": "expected_missing_source_value_cells", "missing_game_id_cells": "expected_missing_game_id_cells",
        "missing_venue_id_cells": "expected_missing_venue_id_cells", "missing_coordinate_cells": "expected_missing_coordinate_cells",
    }
    for actual, expected_key in comparisons.items():
        if profile[actual] != expected[expected_key]:
            raise ValueError(f"weather population drift: {actual}; actual={profile[actual]} expected={expected[expected_key]}")
    profile_expectations = (
        ("candidate_by_season", "expected_candidate_by_season"), ("nonadmitted_by_season", "expected_nonadmitted_by_season"),
        ("source_cells_by_season", "expected_source_cells_by_season"), ("source_games_by_season", "expected_source_games_by_season"),
        ("lead_hours", "expected_lead_hours"), ("kickoff_offset_minutes", "expected_kickoff_offset_minutes"),
    )
    for actual, expected_key in profile_expectations:
        if profile[actual] != expected[expected_key]:
            raise ValueError(f"weather population profile drift: {actual}")
    return snapshot, nonadmitted, profile


def materialize(*, input_data_root: Path, output_data_root: Path, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    pl = _polars()
    contract_path = repo_root / "configs" / "historical_weather_previous_runs_snapshot_contract.json"
    contract_bytes, core_path = contract_path.read_bytes(), Path(__file__).resolve()
    contract = json.loads(contract_bytes)
    _validate_contract_authority(contract)
    builder_path = repo_root / "tools" / "build_historical_weather_previous_runs_snapshot.py"
    candidates, candidate_manifest, source_profiles, capture_profile = _load_candidates(input_data_root, contract)
    expected, source = contract["acceptance"], contract["source_contract"]
    if candidates.height != expected["expected_source_cells"] or set(candidates["season"].unique().to_list()) != set(source["source_seasons"]):
        raise ValueError("weather source population or season coverage drift")
    physical_hashes = {item["physical_schema_sha256"] for item in source_profiles}
    if len(physical_hashes) != expected["expected_physical_schema_hashes"]:
        raise ValueError("weather physical schema drift")
    snapshot, nonadmitted, population = _disposition(candidates, contract)
    population["physical_schema_hashes"] = sorted(physical_hashes)
    population["source_evidence_gap_games"] = int(candidate_manifest["population"]["source_evidence_gap_games"])
    population["technical_route_gap_games"] = int(candidate_manifest["population"]["technical_route_gap_games"])
    if population["source_evidence_gap_games"] != expected["expected_source_evidence_gap_games"]:
        raise ValueError("weather source-evidence gap population drift")
    if population["technical_route_gap_games"] != expected["expected_technical_route_gap_games"]:
        raise ValueError("weather technical-route gap population drift")
    runtime_root = output_data_root / "runtime" / "BAT-551"
    runtime_root.mkdir(parents=True, exist_ok=True)
    staging_root = Path(tempfile.mkdtemp(prefix="weather-previous-runs-snapshot-", dir=runtime_root))
    try:
        staged_snapshot = staging_root / "candidate_weather_previous_run_cells.parquet"
        staged_nonadmitted = staging_root / "archive_unavailable_weather_cells.parquet"
        snapshot.write_parquet(staged_snapshot, compression="zstd", statistics=True)
        nonadmitted.write_parquet(staged_nonadmitted, compression="zstd", statistics=True)
        staged_hashes = {"candidate": sha256_file(staged_snapshot), "nonadmitted": sha256_file(staged_nonadmitted)}
        identity = stable_hash({
            "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "core_sha256": sha256_file(core_path),
            "builder_sha256": sha256_file(builder_path),
            "candidate_manifest_sha256": source["candidate_manifest_sha256"],
            "candidate_payload_sha256": [item["sha256"] for item in candidate_manifest["payloads"]],
            "capture_manifest_aggregate_sha256": capture_profile["capture_manifest_aggregate_sha256"],
            "payload_sha256": staged_hashes,
            "classification": contract["classification"],
        })
        payload_root = output_data_root / "quarantine" / "historical_nominal_lead" / "sha256" / identity
        manifest_root = output_data_root / "manifests" / "historical_nominal_lead" / "sha256" / identity
        payload_root.mkdir(parents=True, exist_ok=True)
        manifest_root.mkdir(parents=True, exist_ok=True)
        snapshot_path, nonadmitted_path = payload_root / staged_snapshot.name, payload_root / staged_nonadmitted.name
        for staged, target, expected_hash in (
            (staged_snapshot, snapshot_path, staged_hashes["candidate"]),
            (staged_nonadmitted, nonadmitted_path, staged_hashes["nonadmitted"]),
        ):
            if target.exists():
                if sha256_file(target) != expected_hash:
                    raise ValueError(f"existing weather payload identity conflict: {target}")
                staged.unlink()
            else:
                os.replace(staged, target)
        payloads = [
            {"role": "NOMINAL_LEAD_WEATHER_CANDIDATE_CELLS", "name": snapshot_path.name, "rows": snapshot.height, "bytes": snapshot_path.stat().st_size, "sha256": staged_hashes["candidate"]},
            {"role": "ARCHIVE_VARIABLE_UNAVAILABLE_WEATHER_CELLS", "name": nonadmitted_path.name, "rows": nonadmitted.height, "bytes": nonadmitted_path.stat().st_size, "sha256": staged_hashes["nonadmitted"]},
        ]
        manifest = {
            "schema_version": "1.0.0",
            "artifact_type": "HISTORICAL_WEATHER_PREVIOUS_RUNS_NOMINAL_LEAD_SNAPSHOT",
            "decision_unit": contract["decision_unit"],
            "jira_key": contract["jira_key"],
            "classification": contract["classification"],
            "dataset_identity": identity,
            "issued_at_utc": issued_at_utc,
            "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "producer": {"python": sys.version.split()[0], "platform": platform.platform(), "polars": pl.__version__, "core_sha256": sha256_file(core_path), "builder_sha256": sha256_file(builder_path)},
            "input_identities": {
                "candidate_dataset": source["candidate_dataset_identity"],
                "candidate_manifest_sha256": source["candidate_manifest_sha256"],
                "candidate_payload_sha256": [item["sha256"] for item in candidate_manifest["payloads"]],
                "acquisition_identity": candidate_manifest["inputs"][0]["acquisition_identity"],
                "acquisition_manifest_sha256": candidate_manifest["inputs"][0]["sha256"],
                "capture_manifest_aggregate_sha256": capture_profile["capture_manifest_aggregate_sha256"],
            },
            "source_profiles": source_profiles,
            "capture_profile": capture_profile,
            "population": population,
            "chronology": {
                "historical_known_at_state": source["historical_known_at_state"],
                "nominal_lead_semantics_verified": True,
                "exact_model_run_initialization_proved": False,
                "historical_api_availability_proved": False,
                "venue_coordinate_effective_time_proved": False,
                "pre_capture_backcast": False,
            },
            "payloads": payloads,
            "authority": contract["authority"],
            "negative_findings": contract["negative_findings"],
            "scientific_nonclaims": {
                "historical_weather_complete": False, "historical_population_ready": False, "gap_002_resolved": False,
                "gap_006_resolved": False, "canonical_weather_materialized": False, "preliminary_model_training_eligible": False,
                "production_model_ready": False, "trained_production_champion": False, "protected_performance_claimed": False,
                "tamu_specialization_lift_claimed": False, "bas_or_aggie_excess_result_claimed": False,
            },
        }
        manifest_path = manifest_root / "historical_weather_previous_runs_snapshot_manifest.json"
        manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
        return {
            "dataset_identity": identity,
            "manifest_path": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "manifest": manifest,
            "snapshot_path": str(snapshot_path),
            "nonadmitted_path": str(nonadmitted_path),
        }
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)

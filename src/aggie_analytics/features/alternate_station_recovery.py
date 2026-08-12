from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .observed_weather_shadow import (
    load_best_observations,
    parse_utc,
    select_temporal_candidates,
    sha256_file,
    stable_hash,
    station_file_id,
)


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("alternate station recovery requires the optional data-engineering environment") from exc
    return polars


def _verify(root: Path, specification: dict[str, Any]) -> Path:
    path = root / specification["relative_path"]
    if not path.is_file() or sha256_file(path) != specification["sha256"]:
        raise RuntimeError(f"alternate-station pinned input mismatch: {path}")
    return path


def build_candidate_population(data_root: Path, contract: dict[str, Any]) -> list[dict[str, Any]]:
    pl = _polars()
    shadow = pl.read_parquet(_verify(data_root, contract["inputs"]["rank_one_shadow"]))
    failed = shadow.filter(pl.col("nearest_absolute_delta_minutes") > 1440).select(
        "source_game_id", "canonical_game_id_candidate", "kickoff_at_utc", "calendar_year", "venue_id", "venue_name",
        pl.col("station_id").alias("rank_one_station_id"),
        pl.col("distance_km").alias("rank_one_distance_km"),
        pl.col("nearest_absolute_delta_minutes").alias("rank_one_delta_minutes"),
    )
    stations = (
        pl.read_csv(_verify(data_root, contract["inputs"]["station_candidates"]), schema_overrides={"venue_id": pl.String, "station_id": pl.String})
        .filter(
            (pl.col("season") == contract["population"]["football_season"])
            & pl.col("station_rank").is_in(contract["population"]["alternate_ranks"])
        )
        .select(
            "venue_id", "station_rank", "station_id", "station_name", "station_latitude", "station_longitude", "distance_km"
        )
    )
    rows = failed.join(stations, on="venue_id", how="left").sort("source_game_id", "station_rank")
    if failed.height != contract["population"]["expected_games"] or rows.height != contract["population"]["expected_game_candidate_rows"]:
        raise RuntimeError("alternate-station recovery population drift")
    if rows["station_id"].null_count():
        raise RuntimeError("alternate-station candidate missing")
    return rows.to_dicts()


def _write_immutable(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise RuntimeError(f"immutable alternate-station collision: {path}")
        return
    descriptor, temporary_name = tempfile.mkstemp(prefix=".incoming-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise RuntimeError(f"immutable alternate-station collision: {path}")
    finally:
        temporary.unlink(missing_ok=True)


def materialize(*, data_root: Path, output_root: Path, repo_root: Path, capture_manifest: dict[str, Any], issued_at_utc: str) -> dict[str, Any]:
    pl = _polars()
    contract_path = repo_root / "configs/noaa_isd_alternate_station_recovery_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    candidates = build_candidate_population(data_root, contract)
    captures = {(int(row["calendar_year"]), row["station_id"]): row for row in capture_manifest["captures"]}
    expected_pairs = {(int(row["calendar_year"]), row["station_id"]) for row in candidates}
    if set(captures) != expected_pairs:
        raise RuntimeError("alternate capture population mismatch")
    cache: dict[tuple[int, str], list[dict[str, Any]]] = {}
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        pair = (int(candidate["calendar_year"]), candidate["station_id"])
        capture = captures[pair]
        payload_path = data_root / capture["raw_relative_path"]
        if sha256_file(payload_path) != capture["raw_sha256"]:
            raise RuntimeError("alternate station payload identity mismatch")
        if pair not in cache:
            cache[pair] = load_best_observations(payload_path, station_file_id(pair[1]), pair[0])
        kickoff = parse_utc(candidate["kickoff_at_utc"])
        nearest = select_temporal_candidates(cache[pair], kickoff)["nearest"]
        row = {
            "schema_version": "1.0.0",
            "classification": contract["classification"],
            **candidate,
            "station_snapshot_id": capture["snapshot_id"],
            "station_raw_sha256": capture["raw_sha256"],
            "station_request_identity_sha256": capture["request_identity_sha256"],
            "nearest_observation_present": nearest is not None,
            "nearest_observed_at_utc": nearest["observed_at_utc"] if nearest else None,
            "nearest_absolute_delta_minutes": abs((parse_utc(nearest["observed_at_utc"]) - kickoff).total_seconds()) / 60.0 if nearest else None,
            "improves_rank_one_time_delta": bool(nearest and abs((parse_utc(nearest["observed_at_utc"]) - kickoff).total_seconds()) / 60.0 < float(candidate["rank_one_delta_minutes"])),
            "automatic_alternate_selection": False,
            "station_acceptance_state": "CANDIDATE_REVIEW_REQUIRED",
            "game_feature_eligible": False,
            "historical_pit_eligible": False,
            "protected_eligible": False,
        }
        for key in (
            "temperature_c", "temperature_quality", "dew_point_c", "dew_point_quality", "wind_direction_degrees",
            "wind_direction_quality", "wind_type_code", "wind_speed_mps", "wind_speed_quality", "visibility_m",
            "visibility_quality", "sea_level_pressure_hpa", "sea_level_pressure_quality", "precipitation_raw_json",
            "raw_tmp", "raw_dew", "raw_wnd", "raw_vis", "raw_slp", "report_type", "source_code", "source_row_number",
        ):
            row[key] = nearest.get(key) if nearest else None
        row["row_lineage_sha256"] = stable_hash({key: row[key] for key in ("source_game_id", "station_rank", "station_id", "station_raw_sha256", "nearest_observed_at_utc")})
        rows.append(row)
    frame = pl.DataFrame(rows).sort("source_game_id", "station_rank")
    per_game = (
        frame.sort("source_game_id", "nearest_absolute_delta_minutes", "station_rank")
        .group_by("source_game_id", maintain_order=True)
        .first()
    )
    core = {
        "schema_version": "1.0.0",
        "artifact_type": "NOAA_ISD_ALTERNATE_STATION_RECOVERY_REVIEW",
        "classification": contract["classification"],
        "decision_unit": contract["decision_unit"],
        "contract_sha256": sha256_file(contract_path),
        "input_sha256": {name: value["sha256"] for name, value in contract["inputs"].items()},
        "capture_manifest_identity": capture_manifest["capture_manifest_identity"],
        "capture_raw_sha256": sorted(row["raw_sha256"] for row in capture_manifest["captures"]),
        "authority": contract["authority"],
    }
    identity = stable_hash(core)
    runtime = output_root / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="alternate-station-recovery-", dir=runtime))
    payloads = []
    try:
        for role, filename, value in (
            ("ALTERNATE_COMPARISONS", "alternate_station_comparisons.parquet", frame),
            ("BEST_TIME_DELTA_PER_GAME_REVIEW_ONLY", "best_alternate_per_game_review.parquet", per_game),
        ):
            staged = staging / filename
            value.write_parquet(staged, compression="zstd", statistics=True)
            payload = staged.read_bytes()
            destination = output_root / contract["artifact_roots"]["features"] / identity / filename
            _write_immutable(destination, payload)
            payloads.append({"role": role, "path": destination.relative_to(output_root).as_posix(), "rows": value.height, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    finally:
        for child in staging.iterdir(): child.unlink()
        staging.rmdir()
    manifest = {
        **core,
        "dataset_identity": identity,
        "issued_at_utc": issued_at_utc,
        "population": {
            "failed_rank_one_games": frame["source_game_id"].n_unique(),
            "comparison_rows": frame.height,
            "alternate_station_years": len(expected_pairs),
            "comparisons_improving_time_delta": frame.filter(pl.col("improves_rank_one_time_delta")).height,
            "games_with_any_alternate_within_60_minutes": per_game.filter(pl.col("nearest_absolute_delta_minutes") <= 60).height,
            "games_with_any_alternate_within_1440_minutes": per_game.filter(pl.col("nearest_absolute_delta_minutes") <= 1440).height,
            "games_still_above_1440_minutes": per_game.filter(pl.col("nearest_absolute_delta_minutes") > 1440).height,
            "best_time_delta_is_selection_authority": False,
        },
        "payloads": payloads,
        "selection": contract["selection"],
        "scientific_nonclaims": contract["scientific_nonclaims"],
    }
    manifest_path = output_root / contract["artifact_roots"]["manifests"] / identity / "run_manifest.json"
    _write_immutable(manifest_path, json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    return {"dataset_identity": identity, "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path), "population": manifest["population"], "payloads": payloads, "manifest": manifest}

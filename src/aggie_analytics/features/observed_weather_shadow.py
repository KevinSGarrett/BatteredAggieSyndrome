from __future__ import annotations

import bisect
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("observed weather shadow requires the optional data-engineering environment") from exc
    return polars


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def stable_hash(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def station_file_id(station_id: str) -> str:
    parts = station_id.split("-")
    if len(parts) != 2 or len(parts[0]) != 6 or len(parts[1]) != 5 or not all(part.isdigit() for part in parts):
        raise ValueError(f"invalid NOAA ISD station identity: {station_id}")
    return "".join(parts)


def _decode_scaled(raw: str | None, *, sentinel: str, divisor: float) -> tuple[float | None, str]:
    parts = str(raw or "").split(",")
    value_text = parts[0] if parts else ""
    quality = parts[1] if len(parts) > 1 else ""
    if not value_text or value_text in {sentinel, f"+{sentinel}", f"-{sentinel}"}:
        return None, quality
    try:
        return int(value_text) / divisor, quality
    except ValueError:
        return None, quality


def decode_observation(row: dict[str, str], row_number: int) -> dict[str, Any]:
    temperature, temperature_quality = _decode_scaled(row.get("TMP"), sentinel="9999", divisor=10.0)
    dew_point, dew_point_quality = _decode_scaled(row.get("DEW"), sentinel="9999", divisor=10.0)
    visibility, visibility_quality = _decode_scaled(row.get("VIS"), sentinel="999999", divisor=1.0)
    pressure, pressure_quality = _decode_scaled(row.get("SLP"), sentinel="99999", divisor=10.0)
    wind_parts = str(row.get("WND") or "").split(",")
    wind_direction = None
    wind_speed = None
    if len(wind_parts) >= 4:
        if wind_parts[0] and wind_parts[0] != "999":
            try:
                wind_direction = int(wind_parts[0])
            except ValueError:
                wind_direction = None
        if wind_parts[3] and wind_parts[3] != "9999":
            try:
                wind_speed = int(wind_parts[3]) / 10.0
            except ValueError:
                wind_speed = None
    precipitation = {key: value for key, value in sorted(row.items()) if key.startswith("AA") and value}
    decoded_count = sum(value is not None for value in (temperature, dew_point, visibility, pressure, wind_direction, wind_speed))
    return {
        "observed_at_utc": parse_utc(str(row.get("DATE") or "")).isoformat().replace("+00:00", "Z"),
        "report_type": str(row.get("REPORT_TYPE") or ""),
        "source_code": str(row.get("SOURCE") or ""),
        "source_row_number": row_number,
        "decoded_common_field_count": decoded_count,
        "temperature_c": temperature,
        "temperature_quality": temperature_quality,
        "dew_point_c": dew_point,
        "dew_point_quality": dew_point_quality,
        "wind_direction_degrees": wind_direction,
        "wind_direction_quality": wind_parts[1] if len(wind_parts) > 1 else "",
        "wind_type_code": wind_parts[2] if len(wind_parts) > 2 else "",
        "wind_speed_mps": wind_speed,
        "wind_speed_quality": wind_parts[4] if len(wind_parts) > 4 else "",
        "visibility_m": visibility,
        "visibility_quality": visibility_quality,
        "sea_level_pressure_hpa": pressure,
        "sea_level_pressure_quality": pressure_quality,
        "precipitation_raw_json": json.dumps(precipitation, sort_keys=True, separators=(",", ":")),
        "raw_tmp": str(row.get("TMP") or ""),
        "raw_dew": str(row.get("DEW") or ""),
        "raw_wnd": str(row.get("WND") or ""),
        "raw_vis": str(row.get("VIS") or ""),
        "raw_slp": str(row.get("SLP") or ""),
    }


def _better_duplicate(candidate: dict[str, Any], existing: dict[str, Any]) -> bool:
    candidate_key = (
        -int(candidate["decoded_common_field_count"]),
        candidate["report_type"],
        candidate["source_code"],
        int(candidate["source_row_number"]),
    )
    existing_key = (
        -int(existing["decoded_common_field_count"]),
        existing["report_type"],
        existing["source_code"],
        int(existing["source_row_number"]),
    )
    return candidate_key < existing_key


def load_best_observations(path: Path, expected_station_file_id: str, calendar_year: int) -> list[dict[str, Any]]:
    by_timestamp: dict[str, dict[str, Any]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), start=2):
            if str(row.get("STATION") or "") != expected_station_file_id:
                raise RuntimeError(f"station identity mismatch in {path}")
            date_text = str(row.get("DATE") or "")
            if not date_text.startswith(f"{calendar_year:04d}-"):
                raise RuntimeError(f"calendar-year mismatch in {path}")
            decoded = decode_observation(row, row_number)
            timestamp = decoded["observed_at_utc"]
            existing = by_timestamp.get(timestamp)
            if existing is None or _better_duplicate(decoded, existing):
                by_timestamp[timestamp] = decoded
    return [by_timestamp[key] for key in sorted(by_timestamp)]


def select_temporal_candidates(observations: list[dict[str, Any]], kickoff: datetime) -> dict[str, Any]:
    if not observations:
        return {"before": None, "after": None, "nearest": None}
    timestamps = [parse_utc(row["observed_at_utc"]) for row in observations]
    position = bisect.bisect_left(timestamps, kickoff)
    if position < len(timestamps) and timestamps[position] == kickoff:
        before = after = observations[position]
    else:
        before = observations[position - 1] if position > 0 else None
        after = observations[position] if position < len(observations) else None
    if before is None:
        nearest = after
    elif after is None:
        nearest = before
    else:
        before_delta = abs((kickoff - parse_utc(before["observed_at_utc"])).total_seconds())
        after_delta = abs((parse_utc(after["observed_at_utc"]) - kickoff).total_seconds())
        nearest = before if before_delta <= after_delta else after
    return {"before": before, "after": after, "nearest": nearest}


def _write_immutable(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise RuntimeError(f"immutable output collision: {path}")
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
                raise RuntimeError(f"immutable output collision: {path}")
    finally:
        temporary.unlink(missing_ok=True)


def _verify(root: Path, specification: dict[str, Any]) -> Path:
    path = root / specification["relative_path"]
    if not path.is_file() or sha256_file(path) != specification["sha256"]:
        raise RuntimeError(f"pinned observed-weather shadow input mismatch: {path}")
    return path


def build_game_population(data_root: Path, contract: dict[str, Any]) -> list[dict[str, Any]]:
    pl = _polars()
    game_path = _verify(data_root, contract["inputs"]["game_coordinate_payload"])
    station_path = _verify(data_root, contract["inputs"]["station_candidate_payload"])
    games = (
        pl.read_parquet(game_path)
        .filter(pl.col("season") == contract["population"]["football_season"])
        .select(
            "source_game_id", "canonical_game_id_candidate", "kickoff_at_utc", "home_team", "away_team",
            pl.col("venue_id_candidate").alias("venue_id"),
            pl.col("venue_name_current_catalog").alias("venue_name"),
            pl.col("venue_dome_current_catalog").alias("venue_dome"),
        )
        .unique()
        .with_columns(pl.col("kickoff_at_utc").str.slice(0, 4).cast(pl.Int64).alias("calendar_year"))
    )
    stations = (
        pl.read_csv(station_path, schema_overrides={"venue_id": pl.String, "station_id": pl.String})
        .filter(
            (pl.col("season") == contract["population"]["football_season"])
            & (pl.col("station_rank") == contract["population"]["station_rank"])
        )
        .select("venue_id", "station_id", "station_name", "station_latitude", "station_longitude", "distance_km")
    )
    joined = games.join(stations, on="venue_id", how="left").sort("kickoff_at_utc", "source_game_id")
    if joined.height != contract["population"]["expected_games"] or joined["station_id"].null_count():
        raise RuntimeError("game-to-station shadow population drift")
    return joined.to_dicts()


def materialize(
    *,
    data_root: Path,
    output_root: Path,
    repo_root: Path,
    capture_manifest: dict[str, Any],
    issued_at_utc: str,
) -> dict[str, Any]:
    pl = _polars()
    contract_path = repo_root / "configs/noaa_isd_game_observation_shadow_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    games = build_game_population(data_root, contract)
    captures = {(int(row["calendar_year"]), row["station_id"]): row for row in capture_manifest["captures"]}
    expected_pairs = {(int(row["calendar_year"]), row["station_id"]) for row in games}
    if set(captures) != expected_pairs:
        raise RuntimeError("station-year capture population does not match target games")
    games_by_pair: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for game in games:
        games_by_pair.setdefault((int(game["calendar_year"]), game["station_id"]), []).append(game)
    output_rows: list[dict[str, Any]] = []
    for pair in sorted(games_by_pair):
        capture = captures[pair]
        payload_path = data_root / capture["raw_relative_path"]
        if sha256_file(payload_path) != capture["raw_sha256"]:
            raise RuntimeError("station-year raw identity mismatch")
        observations = load_best_observations(payload_path, station_file_id(pair[1]), pair[0])
        for game in games_by_pair[pair]:
            kickoff = parse_utc(game["kickoff_at_utc"])
            selected = select_temporal_candidates(observations, kickoff)
            before, after, nearest = selected["before"], selected["after"], selected["nearest"]
            row = {
                "schema_version": "1.0.0",
                "classification": contract["classification"],
                "football_season": contract["population"]["football_season"],
                **game,
                "station_file_id": station_file_id(game["station_id"]),
                "station_rank": contract["population"]["station_rank"],
                "station_acceptance_state": "CANDIDATE_REVIEW_REQUIRED",
                "station_snapshot_id": capture["snapshot_id"],
                "station_raw_sha256": capture["raw_sha256"],
                "station_request_identity_sha256": capture["request_identity_sha256"],
                "before_observed_at_utc": before["observed_at_utc"] if before else None,
                "before_delta_minutes": (kickoff - parse_utc(before["observed_at_utc"])).total_seconds() / 60.0 if before else None,
                "after_observed_at_utc": after["observed_at_utc"] if after else None,
                "after_delta_minutes": (parse_utc(after["observed_at_utc"]) - kickoff).total_seconds() / 60.0 if after else None,
                "nearest_observation_state": "PRESENT" if nearest else "MISSING",
                "nearest_absolute_delta_minutes": abs((parse_utc(nearest["observed_at_utc"]) - kickoff).total_seconds()) / 60.0 if nearest else None,
                "observed_weather_substitution": False,
                "historical_pit_eligible": False,
                "training_feature_eligible": False,
                "protected_eligible": False,
                "dome_observation_feature_eligible": False,
            }
            if nearest:
                row.update({f"nearest_{key}": value for key, value in nearest.items()})
            else:
                for key in (
                    "observed_at_utc", "report_type", "source_code", "source_row_number", "decoded_common_field_count",
                    "temperature_c", "temperature_quality", "dew_point_c", "dew_point_quality", "wind_direction_degrees",
                    "wind_direction_quality", "wind_type_code", "wind_speed_mps", "wind_speed_quality", "visibility_m",
                    "visibility_quality", "sea_level_pressure_hpa", "sea_level_pressure_quality", "precipitation_raw_json",
                    "raw_tmp", "raw_dew", "raw_wnd", "raw_vis", "raw_slp",
                ):
                    row[f"nearest_{key}"] = None
            lineage = {key: row[key] for key in ("source_game_id", "kickoff_at_utc", "station_id", "station_raw_sha256", "nearest_observed_at_utc")}
            row["row_lineage_sha256"] = stable_hash(lineage)
            output_rows.append(row)
    output_rows.sort(key=lambda row: (row["kickoff_at_utc"], row["source_game_id"]))
    frame = pl.DataFrame(output_rows)
    core = {
        "schema_version": "1.0.0",
        "artifact_type": "NOAA_ISD_GAME_TIME_OBSERVATION_SHADOW",
        "classification": contract["classification"],
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "contract_sha256": sha256_file(contract_path),
        "input_sha256": {name: value["sha256"] for name, value in contract["inputs"].items()},
        "capture_manifest_identity": capture_manifest["capture_manifest_identity"],
        "capture_raw_sha256": sorted(row["raw_sha256"] for row in capture_manifest["captures"]),
        "authority": contract["authority"],
    }
    identity = stable_hash(core)
    runtime_root = output_root / "runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="observed-weather-shadow-", dir=runtime_root))
    try:
        staged = staging / "game_time_observation_shadow.parquet"
        frame.write_parquet(staged, compression="zstd", statistics=True)
        payload = staged.read_bytes()
    finally:
        for child in staging.iterdir():
            child.unlink()
        staging.rmdir()
    feature_path = output_root / contract["artifact_roots"]["features"] / identity / "game_time_observation_shadow.parquet"
    _write_immutable(feature_path, payload)
    delta_values = sorted(float(value) for value in frame["nearest_absolute_delta_minutes"].drop_nulls())
    population = {
        "games": frame.height,
        "calendar_2024_games": frame.filter(pl.col("calendar_year") == 2024).height,
        "calendar_2025_games": frame.filter(pl.col("calendar_year") == 2025).height,
        "station_years": len(expected_pairs),
        "nearest_observation_present": frame.filter(pl.col("nearest_observation_state") == "PRESENT").height,
        "dome_games": frame.filter(pl.col("venue_dome") == True).height,  # noqa: E712
        "nearest_delta_minutes": {
            "minimum": delta_values[0] if delta_values else None,
            "median": delta_values[len(delta_values) // 2] if delta_values else None,
            "p95": delta_values[int(0.95 * (len(delta_values) - 1))] if delta_values else None,
            "maximum": delta_values[-1] if delta_values else None,
            "acceptance_threshold": None,
        },
        "non_null_decoded": {
            name: frame[name].drop_nulls().len()
            for name in (
                "nearest_temperature_c", "nearest_dew_point_c", "nearest_wind_direction_degrees",
                "nearest_wind_speed_mps", "nearest_visibility_m", "nearest_sea_level_pressure_hpa",
            )
        },
    }
    manifest = {
        **core,
        "dataset_identity": identity,
        "issued_at_utc": issued_at_utc,
        "population": population,
        "payload": {
            "path": feature_path.relative_to(output_root).as_posix(),
            "rows": frame.height,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        },
        "selection": contract["selection"],
        "missingness": contract["missingness"],
        "scientific_nonclaims": contract["scientific_nonclaims"],
    }
    manifest_path = output_root / contract["artifact_roots"]["manifests"] / identity / "run_manifest.json"
    _write_immutable(manifest_path, json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    return {"dataset_identity": identity, "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path), "population": population, "payload": manifest["payload"], "manifest": manifest}

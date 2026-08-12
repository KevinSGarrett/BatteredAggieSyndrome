from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any


def _pl() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("GFS pilot requires the isolated data runtime") from exc
    return polars


def _eccodes() -> Any:
    try:
        import eccodes
    except ImportError as exc:
        raise RuntimeError("GFS pilot requires the isolated ecCodes runtime") from exc
    return eccodes


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def load_population(data_root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    pl = _pl()
    spec = contract["input"]
    path = data_root / spec["relative_path"]
    if not path.is_file() or sha256_file(path) != spec["sha256"]:
        raise RuntimeError("GFS pilot pinned input mismatch")
    population = contract["population"]
    rows = (
        pl.read_parquet(path)
        .filter(
            (pl.col("source_game_id") == population["source_game_id"])
            & (pl.col("lead_days") == population["lead_days"])
        )
        .select(
            "source_game_id", "canonical_game_id_candidate", "kickoff_at_utc", "forecast_valid_hour_utc",
            "nominal_prediction_at_utc", "requested_latitude", "requested_longitude", "venue_dome_current_catalog",
        )
        .unique()
    )
    if rows.height != 1:
        raise RuntimeError("GFS pilot population is not exactly one game/cutoff")
    row = rows.row(0, named=True)
    expected = {
        "nominal_prediction_at_utc": population["expected_cutoff_utc"],
        "forecast_valid_hour_utc": population["expected_valid_utc"],
        "requested_latitude": population["expected_latitude"],
        "requested_longitude": population["expected_longitude"],
    }
    for key, value in expected.items():
        actual = row[key]
        if isinstance(value, float):
            if not math.isclose(float(actual), value, abs_tol=1e-8):
                raise RuntimeError(f"GFS pilot population drift: {key}")
        elif str(actual).replace(".000Z", "Z") != str(value):
            raise RuntimeError(f"GFS pilot population drift: {key}")
    return row


_INDEX = re.compile(r"^(?P<number>\d+):(?P<offset>\d+):d=(?P<init>\d{10}):(?P<descriptor>.*)$")


def parse_index(index_text: str, message_specs: list[dict[str, str]], object_bytes: int) -> list[dict[str, Any]]:
    entries = []
    for raw in index_text.splitlines():
        match = _INDEX.match(raw)
        if match:
            entries.append({"number": int(match.group("number")), "offset": int(match.group("offset")), "initialization": match.group("init"), "line": raw})
    if not entries:
        raise RuntimeError("GFS index contained no messages")
    selected = []
    for spec in message_specs:
        found = [index for index, row in enumerate(entries) if spec["match"] in row["line"]]
        if len(found) != 1:
            raise RuntimeError(f"GFS index message match cardinality: {spec['component']}")
        index = found[0]
        start = entries[index]["offset"]
        end = entries[index + 1]["offset"] - 1 if index + 1 < len(entries) else object_bytes - 1
        selected.append({**spec, **entries[index], "range_start": start, "range_end": end, "range_bytes": end - start + 1})
    return selected


def _decode(path: Path, latitude: float, longitude: float) -> dict[str, Any]:
    ec = _eccodes()
    with path.open("rb") as handle:
        grib = ec.codes_grib_new_from_file(handle)
        if grib is None:
            raise RuntimeError("ecCodes could not decode GFS message")
        try:
            nearest = ec.codes_grib_find_nearest(grib, latitude, longitude)[0]
            return {
                "value": float(nearest["value"]),
                "grid_latitude": float(nearest["lat"]),
                "grid_longitude": float(nearest["lon"]),
                "grid_distance_km": float(nearest["distance"]),
                "short_name": str(ec.codes_get(grib, "shortName")),
                "units": str(ec.codes_get(grib, "units")),
                "valid_date": int(ec.codes_get(grib, "validityDate")),
                "valid_time": int(ec.codes_get(grib, "validityTime")),
                "data_date": int(ec.codes_get(grib, "dataDate")),
                "data_time": int(ec.codes_get(grib, "dataTime")),
                "step": int(ec.codes_get(grib, "step")),
            }
        finally:
            ec.codes_release(grib)


def _convert(component: str, decoded: dict[str, Any]) -> tuple[str, float, str]:
    value, units = decoded["value"], decoded["units"]
    if component in {"temperature_2m", "dew_point_2m"} and units == "K":
        return component, value - 273.15, "degC"
    if component == "surface_pressure" and units == "Pa":
        return component, value / 100.0, "hPa"
    expected = {
        "relative_humidity_2m": "%",
        "wind_u_10m": "m s**-1",
        "wind_v_10m": "m s**-1",
        "wind_gust_surface": "m s**-1",
        "precipitation_1h": "kg m**-2",
        "visibility_surface": "m",
        "cloud_cover_total": "%",
    }
    if expected.get(component) != units:
        raise RuntimeError(f"unsupported GFS unit for {component}: {units}")
    return component, value, units


def _write_immutable(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise RuntimeError(f"immutable GFS artifact collision: {path}")
        return
    descriptor, name = tempfile.mkstemp(prefix=".incoming-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload); handle.flush(); os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise RuntimeError(f"immutable GFS artifact collision: {path}")
    finally:
        temporary.unlink(missing_ok=True)


def materialize(*, data_root: Path, output_root: Path, repo_root: Path, capture_manifest: dict[str, Any], issued_at_utc: str) -> dict[str, Any]:
    pl, ec = _pl(), _eccodes()
    contract_path = repo_root / "configs/noaa_gfs_issued_run_pilot_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    population = load_population(data_root, contract)
    cutoff = parse_utc(population["nominal_prediction_at_utc"])
    run = contract["issued_run"]
    if parse_utc(run["initialization_utc"]) > cutoff or parse_utc(capture_manifest["object_last_modified_utc"]) > cutoff:
        raise RuntimeError("GFS run was not proven available by cutoff")
    if capture_manifest["object_last_modified_utc"] != run["expected_object_last_modified_utc"]:
        raise RuntimeError("GFS object publication identity drift")
    captures = {row["component"]: row for row in capture_manifest["message_captures"]}
    if set(captures) != {row["component"] for row in contract["messages"]}:
        raise RuntimeError("GFS message capture population mismatch")
    decoded: dict[str, dict[str, Any]] = {}
    for component, capture in captures.items():
        path = data_root / capture["raw_relative_path"]
        if not path.is_file() or sha256_file(path) != capture["raw_sha256"]:
            raise RuntimeError("GFS message capture integrity failure")
        decoded[component] = _decode(path, float(population["requested_latitude"]), float(population["requested_longitude"]))
        if decoded[component]["step"] != run["forecast_hour"] or decoded[component]["valid_date"] != 20240831 or decoded[component]["valid_time"] != 1900:
            raise RuntimeError("GFS decoded temporal identity mismatch")
    rows = []
    for component in ("temperature_2m", "dew_point_2m", "relative_humidity_2m", "wind_gust_surface", "precipitation_1h", "surface_pressure", "visibility_surface", "cloud_cover_total"):
        variable, value, unit = _convert(component, decoded[component])
        rows.append((variable, value, unit, [component]))
    u, v = decoded["wind_u_10m"]["value"], decoded["wind_v_10m"]["value"]
    rows.extend([
        ("wind_speed_10m", math.hypot(u, v), "m s**-1", ["wind_u_10m", "wind_v_10m"]),
        ("wind_direction_10m", (270.0 - math.degrees(math.atan2(v, u))) % 360.0, "degree", ["wind_u_10m", "wind_v_10m"]),
    ])
    output_rows = []
    for variable, value, unit, components in rows:
        reference = decoded[components[0]]
        raw_hashes = [captures[item]["raw_sha256"] for item in components]
        output_rows.append({
            "schema_version": "1.0.0", "classification": contract["classification"],
            "source_game_id": population["source_game_id"], "canonical_game_id_candidate": population["canonical_game_id_candidate"],
            "cutoff_utc": contract["population"]["expected_cutoff_utc"], "run_initialization_utc": run["initialization_utc"],
            "object_last_modified_utc": capture_manifest["object_last_modified_utc"], "valid_utc": contract["population"]["expected_valid_utc"],
            "forecast_hour": run["forecast_hour"], "weather_variable": variable, "value": value, "unit": unit,
            "requested_latitude": population["requested_latitude"], "requested_longitude": population["requested_longitude"],
            "grid_latitude": reference["grid_latitude"], "grid_longitude": reference["grid_longitude"], "grid_distance_km": reference["grid_distance_km"],
            "source_components": json.dumps(components), "source_raw_sha256": json.dumps(raw_hashes),
            "historical_pit_candidate": True, "training_feature_admitted": False, "protected_eligible": False,
            "row_lineage_sha256": stable_hash({"game": population["source_game_id"], "variable": variable, "raw": raw_hashes, "value": value}),
        })
    frame = pl.DataFrame(output_rows).sort("weather_variable")
    if frame.height != contract["population"]["expected_output_rows"]:
        raise RuntimeError("GFS output row count drift")
    core = {
        "schema_version": "1.0.0", "artifact_type": "NOAA_GFS_ISSUED_RUN_PILOT", "classification": contract["classification"],
        "decision_unit": contract["decision_unit"], "contract_sha256": sha256_file(contract_path), "input_sha256": contract["input"]["sha256"],
        "capture_manifest_identity": capture_manifest["capture_manifest_identity"], "raw_sha256": sorted(row["raw_sha256"] for row in capture_manifest["message_captures"]),
        "decoder": {"package": "eccodes", "package_version": getattr(ec, "__version__", "UNKNOWN"), "api_version": ec.codes_get_api_version()},
        "authority": contract["authority"],
    }
    identity = stable_hash(core)
    target = output_root / contract["artifact_roots"]["features"] / identity / "issued_forecast_candidates.parquet"
    runtime = output_root / "runtime"; runtime.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="gfs-issued-run-", dir=runtime))
    try:
        staged = staging / target.name; frame.write_parquet(staged, compression="zstd", statistics=True); payload = staged.read_bytes()
        _write_immutable(target, payload)
    finally:
        for child in staging.iterdir(): child.unlink()
        staging.rmdir()
    manifest = {**core, "dataset_identity": identity, "issued_at_utc": issued_at_utc, "population": {"games": 1, "output_rows": frame.height, "raw_message_captures": len(captures)}, "payload": {"path": target.relative_to(output_root).as_posix(), "rows": frame.height, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}, "scientific_nonclaims": contract["scientific_nonclaims"]}
    manifest_path = output_root / contract["artifact_roots"]["manifests"] / identity / "run_manifest.json"
    _write_immutable(manifest_path, json.dumps(manifest, sort_keys=True, indent=2).encode() + b"\n")
    return {"dataset_identity": identity, "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path), "payload": manifest["payload"], "manifest": manifest}

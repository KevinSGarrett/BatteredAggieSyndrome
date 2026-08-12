from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import tempfile
from typing import Any

from aggie_analytics.features.gfs_issued_run import (
    _decode,
    _eccodes,
    _pl,
    _write_immutable,
    parse_utc,
    sha256_file,
    stable_hash,
)


_INDEX = re.compile(r"^(?P<number>\d+):(?P<offset>\d+):d=(?P<init>\d{10}):(?P<descriptor>.*)$")
_ACCUMULATION = re.compile(r"^APCP:surface:(?P<start>\d+)-(?P<end>\d+) hour acc fcst:$")


def load_population(data_root: Path, contract: dict[str, Any]) -> list[dict[str, Any]]:
    pl = _pl()
    source = data_root / contract["input"]["relative_path"]
    if not source.is_file() or sha256_file(source) != contract["input"]["sha256"]:
        raise RuntimeError("GFS multigame pinned input mismatch")
    frame = pl.read_parquet(source)
    rows: list[dict[str, Any]] = []
    for selector in contract["population"]["selectors"]:
        selected = (
            frame.filter(
                (pl.col("season") == selector["season"])
                & (pl.col("source_game_id") == selector["source_game_id"])
                & (pl.col("lead_days") == selector["lead_days"])
            )
            .select(
                "season",
                "season_type",
                "week",
                "source_game_id",
                "canonical_game_id_candidate",
                "kickoff_at_utc",
                "forecast_valid_hour_utc",
                "nominal_prediction_at_utc",
                "requested_latitude",
                "requested_longitude",
                "venue_dome_current_catalog",
            )
            .unique()
        )
        if selected.height != 1:
            raise RuntimeError("GFS multigame selector is not exactly one game/cutoff")
        row = selected.row(0, named=True)
        expected = {
            "nominal_prediction_at_utc": selector["expected_cutoff_utc"],
            "forecast_valid_hour_utc": selector["expected_valid_utc"],
            "requested_latitude": selector["expected_latitude"],
            "requested_longitude": selector["expected_longitude"],
        }
        for key, value in expected.items():
            actual = row[key]
            if isinstance(value, float):
                if not math.isclose(float(actual), value, abs_tol=1e-8):
                    raise RuntimeError(f"GFS multigame population drift: {key}")
            elif str(actual).replace(".000Z", "Z") != str(value):
                raise RuntimeError(f"GFS multigame population drift: {key}")
        row["selector_identity"] = stable_hash(
            {
                "season": selector["season"],
                "source_game_id": selector["source_game_id"],
                "lead_days": selector["lead_days"],
                "cutoff": selector["expected_cutoff_utc"],
                "valid": selector["expected_valid_utc"],
            }
        )
        rows.append(row)
    if len(rows) != contract["population"]["expected_selection_rows"]:
        raise RuntimeError("GFS multigame population count drift")
    if len({row["selector_identity"] for row in rows}) != len(rows):
        raise RuntimeError("GFS multigame selector identity collision")
    return rows


def candidate_runs(
    cutoff: datetime,
    valid: datetime,
    *,
    cycles_to_probe: int,
    maximum_forecast_hour: int,
) -> list[dict[str, Any]]:
    cutoff = cutoff.astimezone(timezone.utc)
    valid = valid.astimezone(timezone.utc)
    if cutoff.minute or cutoff.second or cutoff.microsecond or valid.minute or valid.second or valid.microsecond:
        raise ValueError("GFS selection requires exact hourly cutoff and valid time")
    latest = cutoff.replace(hour=cutoff.hour - cutoff.hour % 6)
    candidates = []
    for offset in range(cycles_to_probe):
        initialization = latest - timedelta(hours=6 * offset)
        forecast_hours = (valid - initialization).total_seconds() / 3600
        if forecast_hours != int(forecast_hours):
            continue
        forecast_hour = int(forecast_hours)
        if forecast_hour < 0 or forecast_hour > maximum_forecast_hour:
            continue
        key = (
            f"gfs.{initialization:%Y%m%d}/{initialization:%H}/atmos/"
            f"gfs.t{initialization:%H}z.pgrb2.0p25.f{forecast_hour:03d}"
        )
        candidates.append(
            {
                "initialization_utc": initialization.isoformat().replace("+00:00", "Z"),
                "forecast_hour": forecast_hour,
                "object_key": key,
                "index_object_key": f"{key}.idx",
            }
        )
    if not candidates:
        raise RuntimeError("GFS selection generated no eligible candidate cycles")
    return candidates


def choose_attempt(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    for attempt in attempts:
        if attempt["disposition"] == "AVAILABLE_BY_CUTOFF":
            return attempt
    raise RuntimeError("no GFS object was proven available by cutoff")


def parse_index_messages(
    index_text: str,
    message_specs: list[dict[str, str]],
    object_bytes: int,
    forecast_hour: int,
) -> list[dict[str, Any]]:
    entries = []
    for raw in index_text.splitlines():
        match = _INDEX.match(raw)
        if match:
            entries.append(
                {
                    "number": int(match.group("number")),
                    "offset": int(match.group("offset")),
                    "initialization": match.group("init"),
                    "descriptor": match.group("descriptor"),
                    "line": raw,
                }
            )
    if not entries:
        raise RuntimeError("GFS index contained no messages")
    selected = []
    for spec in message_specs:
        if spec["component"] == "precipitation_accumulation":
            candidates = []
            for index, row in enumerate(entries):
                match = _ACCUMULATION.match(row["descriptor"])
                if match and int(match.group("end")) == forecast_hour:
                    start, end = int(match.group("start")), int(match.group("end"))
                    if end > start:
                        candidates.append((end - start, start, index))
            if not candidates:
                raise RuntimeError("GFS precipitation accumulation window missing")
            duration, start_hour, index = min(candidates)
            accumulation_hours = duration
            accumulation_start_hour = start_hour
        else:
            expected = f"{spec['descriptor']}:{forecast_hour} hour fcst:"
            matches = [index for index, row in enumerate(entries) if row["descriptor"] == expected]
            if len(matches) != 1:
                raise RuntimeError(f"GFS index message match cardinality: {spec['component']}")
            index = matches[0]
            accumulation_hours = None
            accumulation_start_hour = None
        start = entries[index]["offset"]
        end = entries[index + 1]["offset"] - 1 if index + 1 < len(entries) else object_bytes - 1
        selected.append(
            {
                **spec,
                **entries[index],
                "range_start": start,
                "range_end": end,
                "range_bytes": end - start + 1,
                "accumulation_hours": accumulation_hours,
                "accumulation_start_hour": accumulation_start_hour,
            }
        )
    return selected


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
        "precipitation_accumulation": "kg m**-2",
        "visibility_surface": "m",
        "cloud_cover_total": "%",
    }
    if expected.get(component) != units:
        raise RuntimeError(f"unsupported GFS unit for {component}: {units}")
    return component, value, units


def _expected_valid_parts(value: str) -> tuple[int, int]:
    parsed = parse_utc(value)
    return int(parsed.strftime("%Y%m%d")), parsed.hour * 100


def materialize(
    *,
    data_root: Path,
    output_root: Path,
    repo_root: Path,
    capture_manifest: dict[str, Any],
    issued_at_utc: str,
) -> dict[str, Any]:
    pl, ec = _pl(), _eccodes()
    contract_path = repo_root / "configs/noaa_gfs_multigame_selection_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    population = {row["selector_identity"]: row for row in load_population(data_root, contract)}
    selection_rows = capture_manifest["selections"]
    if {row["selector_identity"] for row in selection_rows} != set(population):
        raise RuntimeError("GFS multigame capture population mismatch")
    output_rows: list[dict[str, Any]] = []
    all_raw_hashes = []
    for selection in selection_rows:
        source = population[selection["selector_identity"]]
        cutoff = parse_utc(source["nominal_prediction_at_utc"])
        initialization = parse_utc(selection["initialization_utc"])
        publication = parse_utc(selection["object_last_modified_utc"])
        valid = parse_utc(source["forecast_valid_hour_utc"])
        if initialization > cutoff or publication > cutoff:
            raise RuntimeError("GFS selected run was not available by cutoff")
        if int((valid - initialization).total_seconds() / 3600) != selection["forecast_hour"]:
            raise RuntimeError("GFS selected forecast-hour identity mismatch")
        captures = {row["component"]: row for row in selection["message_captures"]}
        if set(captures) != {row["component"] for row in contract["messages"]}:
            raise RuntimeError("GFS selected message capture population mismatch")
        decoded: dict[str, dict[str, Any]] = {}
        expected_date, expected_time = _expected_valid_parts(source["forecast_valid_hour_utc"])
        for component, capture in captures.items():
            path = data_root / capture["raw_relative_path"]
            if not path.is_file() or sha256_file(path) != capture["raw_sha256"]:
                raise RuntimeError("GFS selected message capture integrity failure")
            result = _decode(path, float(source["requested_latitude"]), float(source["requested_longitude"]))
            if (
                result["step"] != selection["forecast_hour"]
                or result["valid_date"] != expected_date
                or result["valid_time"] != expected_time
            ):
                raise RuntimeError("GFS decoded temporal identity mismatch")
            decoded[component] = result
            all_raw_hashes.append(capture["raw_sha256"])
        values = []
        for component in (
            "temperature_2m",
            "dew_point_2m",
            "relative_humidity_2m",
            "wind_gust_surface",
            "precipitation_accumulation",
            "surface_pressure",
            "visibility_surface",
            "cloud_cover_total",
        ):
            variable, value, unit = _convert(component, decoded[component])
            values.append((variable, value, unit, [component]))
        u, v = decoded["wind_u_10m"]["value"], decoded["wind_v_10m"]["value"]
        values.extend(
            [
                ("wind_speed_10m", math.hypot(u, v), "m s**-1", ["wind_u_10m", "wind_v_10m"]),
                ("wind_direction_10m", (270.0 - math.degrees(math.atan2(v, u))) % 360.0, "degree", ["wind_u_10m", "wind_v_10m"]),
            ]
        )
        precipitation_capture = captures["precipitation_accumulation"]
        for variable, value, unit, components in values:
            reference = decoded[components[0]]
            raw_hashes = [captures[item]["raw_sha256"] for item in components]
            accumulation_hours = (
                precipitation_capture["accumulation_hours"]
                if variable == "precipitation_accumulation"
                else None
            )
            lineage = {
                "selector": selection["selector_identity"],
                "variable": variable,
                "raw": raw_hashes,
                "value": value,
                "accumulation_hours": accumulation_hours,
            }
            output_rows.append(
                {
                    "schema_version": "1.0.0",
                    "classification": contract["classification"],
                    "season": source["season"],
                    "season_type": source["season_type"],
                    "week": source["week"],
                    "source_game_id": source["source_game_id"],
                    "canonical_game_id_candidate": source["canonical_game_id_candidate"],
                    "lead_days": contract_selector_lead(contract, selection["selector_identity"]),
                    "selector_identity": selection["selector_identity"],
                    "cutoff_utc": source["nominal_prediction_at_utc"].replace(".000Z", "Z"),
                    "valid_utc": source["forecast_valid_hour_utc"].replace(".000Z", "Z"),
                    "run_initialization_utc": selection["initialization_utc"],
                    "object_last_modified_utc": selection["object_last_modified_utc"],
                    "forecast_hour": selection["forecast_hour"],
                    "weather_variable": variable,
                    "value": value,
                    "unit": unit,
                    "accumulation_hours": accumulation_hours,
                    "requested_latitude": source["requested_latitude"],
                    "requested_longitude": source["requested_longitude"],
                    "venue_dome_current_catalog": source["venue_dome_current_catalog"],
                    "grid_latitude": reference["grid_latitude"],
                    "grid_longitude": reference["grid_longitude"],
                    "grid_distance_km": reference["grid_distance_km"],
                    "source_components": json.dumps(components),
                    "source_raw_sha256": json.dumps(raw_hashes),
                    "issued_run_available_by_cutoff": True,
                    "venue_coordinate_historical_eligibility": False,
                    "historical_pit_candidate": True,
                    "weather_feature_pit_eligible": False,
                    "training_feature_admitted": False,
                    "protected_eligible": False,
                    "row_lineage_sha256": stable_hash(lineage),
                }
            )
    frame = pl.DataFrame(output_rows).sort(["season", "source_game_id", "lead_days", "weather_variable"])
    if frame.height != contract["population"]["expected_output_rows"]:
        raise RuntimeError("GFS multigame output row count drift")
    natural_key = ["selector_identity", "weather_variable"]
    if frame.select(natural_key).unique().height != frame.height:
        raise RuntimeError("GFS multigame output natural-key collision")
    core = {
        "schema_version": "1.0.0",
        "artifact_type": "NOAA_GFS_MULTIGAME_SELECTION_PILOT",
        "classification": contract["classification"],
        "decision_unit": contract["decision_unit"],
        "contract_sha256": sha256_file(contract_path),
        "transformation_implementation_sha256": sha256_file(Path(__file__).resolve()),
        "input_sha256": contract["input"]["sha256"],
        "capture_manifest_identity": capture_manifest["capture_manifest_identity"],
        "raw_sha256": sorted(all_raw_hashes),
        "decoder": {
            "package": "eccodes",
            "package_version": getattr(ec, "__version__", "UNKNOWN"),
            "api_version": ec.codes_get_api_version(),
            "polars_package_version": getattr(pl, "__version__", "UNKNOWN"),
        },
        "authority": contract["authority"],
    }
    identity = stable_hash(core)
    target = output_root / contract["artifact_roots"]["features"] / identity / "issued_forecast_candidates.parquet"
    runtime = output_root / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="gfs-multigame-", dir=runtime))
    try:
        staged = staging / target.name
        frame.write_parquet(staged, compression="zstd", statistics=True)
        payload = staged.read_bytes()
        _write_immutable(target, payload)
    finally:
        for child in staging.iterdir():
            child.unlink()
        staging.rmdir()
    manifest = {
        **core,
        "dataset_identity": identity,
        "issued_at_utc": issued_at_utc,
        "population": {
            "selector_rows": len(selection_rows),
            "distinct_games": frame["source_game_id"].n_unique(),
            "seasons": sorted(frame["season"].unique().to_list()),
            "lead_days": sorted(frame["lead_days"].unique().to_list()),
            "output_rows": frame.height,
            "raw_message_captures": len(all_raw_hashes),
        },
        "payload": {
            "path": target.relative_to(output_root).as_posix(),
            "rows": frame.height,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        },
        "scientific_nonclaims": contract["scientific_nonclaims"],
    }
    manifest_path = output_root / contract["artifact_roots"]["manifests"] / identity / "run_manifest.json"
    _write_immutable(manifest_path, json.dumps(manifest, sort_keys=True, indent=2).encode() + b"\n")
    return {
        "dataset_identity": identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "payload": manifest["payload"],
        "manifest": manifest,
    }


def contract_selector_lead(contract: dict[str, Any], selector_identity: str) -> int:
    for selector in contract["population"]["selectors"]:
        identity = stable_hash(
            {
                "season": selector["season"],
                "source_game_id": selector["source_game_id"],
                "lead_days": selector["lead_days"],
                "cutoff": selector["expected_cutoff_utc"],
                "valid": selector["expected_valid_utc"],
            }
        )
        if identity == selector_identity:
            return int(selector["lead_days"])
    raise RuntimeError("GFS selector identity missing from contract")

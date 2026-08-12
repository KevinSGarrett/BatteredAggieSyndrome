from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import tempfile
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable


EARTH_RADIUS_KM = 6371.0088


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("station matching requires the optional data-engineering environment") from exc
    return polars


def _numpy() -> Any:
    try:
        import numpy
    except ImportError as exc:
        raise RuntimeError("national station matching requires the optional data-engineering environment") from exc
    return numpy


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


def haversine_km(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    """Return great-circle distance using the contract's fixed WGS84 mean radius."""

    phi_a, phi_b = math.radians(latitude_a), math.radians(latitude_b)
    delta_phi = math.radians(latitude_b - latitude_a)
    delta_lambda = math.radians(longitude_b - longitude_a)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi_a) * math.cos(phi_b) * math.sin(delta_lambda / 2.0) ** 2
    return EARTH_RADIUS_KM * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def station_period_covers_season(begin: date, end: date, season: int) -> bool:
    return begin <= date(season, 12, 31) and end >= date(season, 1, 1)


def _parse_station_date(value: str) -> date | None:
    text = value.strip()
    if len(text) != 8 or not text.isdigit():
        return None
    try:
        return date(int(text[:4]), int(text[4:6]), int(text[6:8]))
    except ValueError:
        return None


def parse_isd_station_catalog(payload: bytes) -> list[dict[str, Any]]:
    text = payload.decode("utf-8-sig")
    rows: list[dict[str, Any]] = []
    for raw in csv.DictReader(io.StringIO(text)):
        normalized = {str(key).strip(): (value or "").strip() for key, value in raw.items()}
        try:
            latitude = float(normalized.get("LAT", ""))
            longitude = float(normalized.get("LON", ""))
        except ValueError:
            continue
        begin = _parse_station_date(normalized.get("BEGIN", ""))
        end = _parse_station_date(normalized.get("END", ""))
        if begin is None or end is None or begin > end:
            continue
        usaf, wban = normalized.get("USAF", ""), normalized.get("WBAN", "")
        if not usaf and not wban:
            continue
        station_id = f"{usaf or 'UNKNOWN'}-{wban or 'UNKNOWN'}"
        rows.append(
            {
                "station_id": station_id,
                "usaf": usaf,
                "wban": wban,
                "station_name": normalized.get("STATION NAME", ""),
                "country": normalized.get("CTRY", ""),
                "state": normalized.get("STATE", ""),
                "icao": normalized.get("ICAO", ""),
                "latitude": latitude,
                "longitude": longitude,
                "elevation_m": normalized.get("ELEV(M)", ""),
                "begin": begin,
                "end": end,
            }
        )
    rows.sort(key=lambda row: row["station_id"])
    return rows


def rank_station_candidates(
    latitude: float,
    longitude: float,
    season: int,
    stations: Iterable[dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    candidates = []
    for station in stations:
        if not station_period_covers_season(station["begin"], station["end"], season):
            continue
        candidates.append(
            {
                **station,
                "distance_km": round(
                    haversine_km(latitude, longitude, station["latitude"], station["longitude"]), 6
                ),
            }
        )
    candidates.sort(key=lambda row: (row["distance_km"], row["station_id"]))
    return candidates[:top_k]


def _csv_bytes(rows: list[dict[str, Any]], fieldnames: list[str]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _write_immutable(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise RuntimeError(f"immutable artifact collision: {path}")
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
                raise RuntimeError(f"immutable artifact collision: {path}")
    finally:
        temporary.unlink(missing_ok=True)


def _verify_input(root: Path, specification: dict[str, Any]) -> Path:
    path = root / specification["relative_path"]
    if not path.is_file() or sha256_file(path) != specification["sha256"]:
        raise RuntimeError(f"pinned station-matching input mismatch: {path}")
    return path


def materialize(
    *,
    input_data_root: Path,
    output_data_root: Path,
    repo_root: Path,
    station_payload_path: Path,
    station_snapshot: dict[str, Any],
    issued_at_utc: str,
) -> dict[str, Any]:
    pl = _polars()
    contract_path = repo_root / "configs/noaa_isd_station_matching_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    inputs = {name: _verify_input(input_data_root, value) for name, value in contract["inputs"].items()}
    if sha256_file(station_payload_path) != station_snapshot["raw_sha256"]:
        raise RuntimeError("station snapshot payload identity mismatch")
    historical_manifest = json.loads(inputs["historical_venue_manifest"].read_text(encoding="utf-8"))
    coordinate_manifest = json.loads(inputs["current_coordinate_manifest"].read_text(encoding="utf-8"))
    if historical_manifest["dataset_identity"] != contract["inputs"]["historical_venue_manifest"]["dataset_identity"]:
        raise RuntimeError("historical venue dataset identity mismatch")
    if coordinate_manifest["dataset_identity"] != contract["inputs"]["current_coordinate_manifest"]["dataset_identity"]:
        raise RuntimeError("coordinate candidate dataset identity mismatch")

    venues = pl.read_parquet(inputs["historical_venue_payload"])
    weather = pl.read_parquet(inputs["current_coordinate_payload"])
    coordinate_rows = (
        weather.select(
            pl.col("venue_id_candidate").alias("venue_id"),
            pl.col("venue_name_current_catalog").alias("coordinate_catalog_venue_name"),
            pl.col("requested_latitude").alias("venue_latitude"),
            pl.col("requested_longitude").alias("venue_longitude"),
        )
        .unique()
        .sort("venue_id")
    )
    coordinate_counts = coordinate_rows.group_by("venue_id").len().rename({"len": "coordinate_variant_count"})
    unique_coordinates = coordinate_rows.join(coordinate_counts, on="venue_id").filter(
        pl.col("coordinate_variant_count") == 1
    )
    historical_backbone = venues.select(
        "season", "venue_id", pl.col("venue_full_name").alias("historical_venue_name")
    ).unique()
    recent_backbone = weather.select(
        "season",
        pl.col("venue_id_candidate").alias("venue_id"),
        pl.col("venue_name_current_catalog").alias("historical_venue_name"),
    ).unique()
    backbone = (
        pl.concat([historical_backbone, recent_backbone], how="vertical_relaxed")
        .group_by("season", "venue_id")
        .agg(pl.col("historical_venue_name").drop_nulls().sort().first())
        .filter(
            pl.col("season").is_between(
                contract["population"]["season_min"], contract["population"]["season_max"]
            )
        )
        .join(unique_coordinates, on="venue_id", how="left")
        .join(coordinate_counts, on="venue_id", how="left", suffix="_all")
        .sort("season", "venue_id")
    )
    stations = parse_isd_station_catalog(station_payload_path.read_bytes())
    if not stations:
        raise RuntimeError("NOAA ISD station catalog produced no valid stations")

    np = _numpy()
    station_latitudes = np.radians(np.array([row["latitude"] for row in stations], dtype=float))
    station_longitudes = np.radians(np.array([row["longitude"] for row in stations], dtype=float))
    station_ids = np.array([row["station_id"] for row in stations], dtype=str)
    station_indices_by_season = {
        season: np.array(
            [
                index
                for index, station in enumerate(stations)
                if station_period_covers_season(station["begin"], station["end"], season)
            ],
            dtype=int,
        )
        for season in range(
            contract["population"]["season_min"],
            contract["population"]["season_max"] + 1,
        )
    }

    def ranked_for_venue(latitude: float, longitude: float, season: int) -> list[dict[str, Any]]:
        eligible = station_indices_by_season[season]
        if eligible.size == 0:
            return []
        venue_latitude = math.radians(latitude)
        venue_longitude = math.radians(longitude)
        delta_latitude = station_latitudes[eligible] - venue_latitude
        delta_longitude = station_longitudes[eligible] - venue_longitude
        a = (
            np.sin(delta_latitude / 2.0) ** 2
            + math.cos(venue_latitude)
            * np.cos(station_latitudes[eligible])
            * np.sin(delta_longitude / 2.0) ** 2
        )
        distances = EARTH_RADIUS_KM * 2.0 * np.arctan2(np.sqrt(a), np.sqrt(np.maximum(0.0, 1.0 - a)))
        keep = min(top_k, int(eligible.size))
        if keep < int(eligible.size):
            threshold = float(np.partition(distances, keep - 1)[keep - 1])
            local_pool = np.flatnonzero(distances <= threshold)
        else:
            local_pool = np.arange(eligible.size)
        ordered_pool = local_pool[
            np.lexsort((station_ids[eligible[local_pool]], distances[local_pool]))
        ][:keep]
        output: list[dict[str, Any]] = []
        for local_index in ordered_pool:
            station = dict(stations[int(eligible[int(local_index)])])
            station["distance_km"] = round(float(distances[int(local_index)]), 6)
            output.append(station)
        return output

    coverage_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    top_k = int(contract["population"]["top_k_station_candidates"])
    for venue in backbone.to_dicts():
        latitude, longitude = venue.get("venue_latitude"), venue.get("venue_longitude")
        variants = int(venue.get("coordinate_variant_count") or 0)
        if variants == 0:
            coordinate_state = "MISSING_CURRENT_CATALOG_COORDINATE"
            ranked: list[dict[str, Any]] = []
        elif variants > 1:
            coordinate_state = "AMBIGUOUS_CURRENT_CATALOG_COORDINATE"
            ranked = []
        else:
            coordinate_state = "CURRENT_CATALOG_COORDINATE_EFFECTIVE_TIME_UNKNOWN"
            ranked = ranked_for_venue(float(latitude), float(longitude), int(venue["season"]))
        coverage_rows.append(
            {
                "season": int(venue["season"]),
                "venue_id": str(venue["venue_id"]),
                "venue_name": venue.get("historical_venue_name") or venue.get("coordinate_catalog_venue_name") or "",
                "coordinate_state": coordinate_state,
                "coordinate_variant_count": variants,
                "candidate_count": len(ranked),
                "automatic_station_promotion": "false",
                "historical_pit_eligible": "false",
                "training_feature_eligible": "false",
            }
        )
        for rank, station in enumerate(ranked, start=1):
            identity_fields = {
                "season": int(venue["season"]),
                "station_id": station["station_id"],
                "station_rank": rank,
                "venue_id": str(venue["venue_id"]),
            }
            candidate_rows.append(
                {
                    **identity_fields,
                    "candidate_identity": stable_hash(identity_fields),
                    "venue_name": venue.get("historical_venue_name") or venue.get("coordinate_catalog_venue_name") or "",
                    "venue_latitude": format(float(latitude), ".6f"),
                    "venue_longitude": format(float(longitude), ".6f"),
                    "coordinate_effective_time_state": "UNKNOWN_CURRENT_2026_CATALOG_COORDINATE",
                    "station_name": station["station_name"],
                    "station_country": station["country"],
                    "station_state": station["state"],
                    "station_icao": station["icao"],
                    "station_latitude": format(station["latitude"], ".6f"),
                    "station_longitude": format(station["longitude"], ".6f"),
                    "station_elevation_m": station["elevation_m"],
                    "station_begin": station["begin"].isoformat(),
                    "station_end": station["end"].isoformat(),
                    "distance_km": format(station["distance_km"], ".6f"),
                    "distance_acceptance_state": "UNSET_REQUIRES_EMPIRICAL_OR_MANUAL_REVIEW",
                    "automatic_station_promotion": "false",
                    "historical_pit_eligible": "false",
                    "training_feature_eligible": "false",
                }
            )

    candidate_fields = [
        "season", "venue_id", "station_id", "station_rank", "candidate_identity", "venue_name",
        "venue_latitude", "venue_longitude", "coordinate_effective_time_state", "station_name",
        "station_country", "station_state", "station_icao", "station_latitude", "station_longitude",
        "station_elevation_m", "station_begin", "station_end", "distance_km", "distance_acceptance_state",
        "automatic_station_promotion", "historical_pit_eligible", "training_feature_eligible",
    ]
    coverage_fields = [
        "season", "venue_id", "venue_name", "coordinate_state", "coordinate_variant_count",
        "candidate_count", "automatic_station_promotion", "historical_pit_eligible", "training_feature_eligible",
    ]
    candidate_bytes = _csv_bytes(candidate_rows, candidate_fields)
    coverage_bytes = _csv_bytes(coverage_rows, coverage_fields)
    core = {
        "schema_version": "1.0.0",
        "artifact_type": "NOAA_ISD_VENUE_SEASON_STATION_MATCHING_CANDIDATES",
        "classification": contract["classification"],
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "contract_sha256": sha256_file(contract_path),
        "input_sha256": {name: specification["sha256"] for name, specification in contract["inputs"].items()},
        "station_snapshot_id": station_snapshot["snapshot_id"],
        "station_raw_sha256": station_snapshot["raw_sha256"],
        "station_request_identity_sha256": station_snapshot["request_identity_sha256"],
        "authority": contract["authority"],
    }
    dataset_identity = stable_hash(core)
    feature_root = output_data_root / contract["artifact_roots"]["features"] / dataset_identity
    candidate_path = feature_root / "venue_season_station_candidates.csv"
    coverage_path = feature_root / "venue_season_station_coverage.csv"
    _write_immutable(candidate_path, candidate_bytes)
    _write_immutable(coverage_path, coverage_bytes)
    season_counts: dict[int, int] = defaultdict(int)
    for row in coverage_rows:
        season_counts[row["season"]] += 1
    payloads = [
        {"role": "STATION_CANDIDATES", "path": candidate_path.relative_to(output_data_root).as_posix(), "rows": len(candidate_rows), "bytes": len(candidate_bytes), "sha256": hashlib.sha256(candidate_bytes).hexdigest()},
        {"role": "VENUE_SEASON_COVERAGE", "path": coverage_path.relative_to(output_data_root).as_posix(), "rows": len(coverage_rows), "bytes": len(coverage_bytes), "sha256": hashlib.sha256(coverage_bytes).hexdigest()},
    ]
    manifest = {
        **core,
        "dataset_identity": dataset_identity,
        "issued_at_utc": issued_at_utc,
        "station_capture": station_snapshot,
        "population": {
            "station_catalog_valid_rows": len(stations),
            "venue_season_rows": len(coverage_rows),
            "venue_seasons_with_unique_coordinates": sum(row["coordinate_variant_count"] == 1 for row in coverage_rows),
            "venue_seasons_missing_coordinates": sum(row["coordinate_variant_count"] == 0 for row in coverage_rows),
            "venue_seasons_ambiguous_coordinates": sum(row["coordinate_variant_count"] > 1 for row in coverage_rows),
            "candidate_rows": len(candidate_rows),
            "top_k": top_k,
            "season_counts": {str(key): season_counts[key] for key in sorted(season_counts)},
        },
        "matching_contract": contract["matching_contract"],
        "payloads": payloads,
        "negative_findings": [
            "Venue coordinates come from a current catalog candidate layer with unknown historical effective time.",
            "No automatic distance threshold or canonical station promotion is authorized.",
            "Observed station selection and hourly weather acquisition remain a later independently validated unit.",
        ],
        "scientific_nonclaims": contract["scientific_nonclaims"],
    }
    manifest_path = output_data_root / contract["artifact_roots"]["manifests"] / dataset_identity / "run_manifest.json"
    _write_immutable(manifest_path, json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    return {
        "dataset_identity": dataset_identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "population": manifest["population"],
        "payloads": payloads,
        "manifest": manifest,
    }

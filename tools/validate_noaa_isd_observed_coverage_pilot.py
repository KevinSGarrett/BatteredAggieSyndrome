from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aggie_analytics.data.snapshots import RawSnapshotStore  # noqa: E402


BASE_FIELDS = {"STATION", "DATE", "LATITUDE", "LONGITUDE", "NAME", "REPORT_TYPE", "QUALITY_CONTROL"}


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


def _not_sentinel(value: str | None, sentinel: str) -> bool:
    return bool(value) and str(value).split(",", 1)[0] != sentinel


def _wind_usable(value: str | None) -> bool:
    parts = str(value or "").split(",")
    return len(parts) >= 4 and parts[0] != "999" and parts[3] != "9999"


def _precip_usable(row: dict[str, str | None], precipitation_fields: list[str]) -> bool:
    for field in precipitation_fields:
        parts = str(row.get(field) or "").split(",")
        if len(parts) >= 2 and parts[1] != "9999":
            return True
    return False


def profile_capture(path: Path, station_file_id: str, season: int) -> dict[str, Any]:
    rows = 0
    min_date: str | None = None
    max_date: str | None = None
    outside_season = 0
    station_mismatch = 0
    usable = {"temperature": 0, "dew_point": 0, "wind": 0, "visibility": 0, "sea_level_pressure": 0, "precipitation": 0}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        missing_base = sorted(BASE_FIELDS.difference(fields))
        precipitation_fields = sorted(field for field in fields if field.startswith("AA"))
        for row in reader:
            rows += 1
            observed_station = str(row.get("STATION") or "")
            if observed_station != station_file_id:
                station_mismatch += 1
            observed_date = str(row.get("DATE") or "")
            if min_date is None or observed_date < min_date:
                min_date = observed_date
            if max_date is None or observed_date > max_date:
                max_date = observed_date
            if not observed_date.startswith(f"{season:04d}-"):
                outside_season += 1
            usable["temperature"] += _not_sentinel(row.get("TMP"), "+9999") and _not_sentinel(row.get("TMP"), "-9999")
            usable["dew_point"] += _not_sentinel(row.get("DEW"), "+9999") and _not_sentinel(row.get("DEW"), "-9999")
            usable["wind"] += _wind_usable(row.get("WND"))
            usable["visibility"] += _not_sentinel(row.get("VIS"), "999999")
            usable["sea_level_pressure"] += _not_sentinel(row.get("SLP"), "99999")
            usable["precipitation"] += _precip_usable(row, precipitation_fields)
    return {
        "row_count": rows,
        "min_date": min_date or "",
        "max_date": max_date or "",
        "outside_season_rows": outside_season,
        "station_mismatch_rows": station_mismatch,
        "schema_field_count": len(fields),
        "schema_sha256": stable_hash(fields),
        "missing_base_fields": ";".join(missing_base),
        "precipitation_field_count": len(precipitation_fields),
        **{f"usable_{name}_rows": int(value) for name, value in usable.items()},
    }


def _csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    fields = list(rows[0])
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _write_immutable(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise RuntimeError(f"immutable validation collision: {path}")
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
                raise RuntimeError(f"immutable validation collision: {path}")
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--acquisition-identity", required=True)
    args = parser.parse_args()
    data_root = args.data_root.resolve()
    contract_path = ROOT / "configs/noaa_isd_observed_coverage_pilot_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    acquisition_path = data_root / contract["artifact_root"] / args.acquisition_identity / "acquisition_manifest.json"
    acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        checks.append({"check": name, "result": "PASS" if condition else "FAIL", "detail": detail})

    check("acquisition_identity", acquisition["dataset_identity"] == args.acquisition_identity)
    check("classification", acquisition["classification"] == contract["classification"])
    check("authority", acquisition["authority"] == contract["authority"])
    check("complete_population", acquisition["complete_population_run"] is True)
    check("capture_count", acquisition["capture_count"] == contract["pilot_population"]["expected_unique_station_years"])
    captures = acquisition["captures"]
    check("station_id_unique", len({row["station_id"] for row in captures}) == len(captures))
    check("request_identity_unique", len({row["request_identity_sha256"] for row in captures}) == len(captures))
    store = RawSnapshotStore(data_root)
    profiles = []
    for capture in captures:
        snapshot = store.manifest_record(capture["snapshot_id"])
        path = data_root / capture["raw_relative_path"]
        uri = urlsplit(capture["source_uri"])
        identity_ok = snapshot["raw_sha256"] == capture["raw_sha256"] and sha256_file(path) == capture["raw_sha256"]
        check(f"capture_identity:{capture['station_id']}", identity_ok)
        check(f"public_nodd_uri:{capture['station_id']}", uri.scheme == "https" and uri.netloc == "noaa-global-hourly-pds.s3.amazonaws.com" and not uri.query)
        profile = profile_capture(path, capture["station_file_id"], int(capture["season"]))
        profiles.append(
            {
                "season": capture["season"],
                "station_id": capture["station_id"],
                "station_file_id": capture["station_file_id"],
                "referenced_venue_count": len(capture["referenced_venue_ids"]),
                "raw_sha256": capture["raw_sha256"],
                "raw_bytes": capture["raw_bytes"],
                **profile,
            }
        )
    profiles.sort(key=lambda row: (row["season"], row["station_id"]))
    check("all_payloads_nonempty", all(row["row_count"] > 0 for row in profiles))
    check("all_rows_in_season", sum(row["outside_season_rows"] for row in profiles) == 0)
    check("all_station_rows_match", sum(row["station_mismatch_rows"] for row in profiles) == 0)
    check("base_schema_present", all(not row["missing_base_fields"] for row in profiles))
    check("no_station_promotion", acquisition["authority"]["canonical_station_acceptance"] is False)
    coverage_core = {
        "schema_version": "1.0.0",
        "artifact_type": "NOAA_ISD_OBSERVED_STATION_YEAR_SCHEMA_COVERAGE",
        "classification": contract["classification"],
        "acquisition_identity": args.acquisition_identity,
        "acquisition_manifest_sha256": sha256_file(acquisition_path),
        "contract_sha256": sha256_file(contract_path),
        "profile_semantics": "RAW_SCHEMA_AND_NON_SENTINEL_COUNTS_NO_GAME_FEATURE_OR_STATION_PROMOTION",
    }
    coverage_identity = stable_hash(coverage_core)
    coverage_bytes = _csv_bytes(profiles)
    coverage_path = data_root / "features/weather_observed_coverage_pilot/sha256" / coverage_identity / "station_year_schema_coverage.csv"
    _write_immutable(coverage_path, coverage_bytes)
    failures = [row for row in checks if row["result"] == "FAIL"]
    report = {
        **coverage_core,
        "coverage_identity": coverage_identity,
        "result": "PASS" if not failures else "FAIL",
        "checks_passed": len(checks) - len(failures),
        "checks_failed": len(failures),
        "checks": checks,
        "failures": failures,
        "coverage_payload": {
            "path": coverage_path.relative_to(data_root).as_posix(),
            "rows": len(profiles),
            "bytes": len(coverage_bytes),
            "sha256": hashlib.sha256(coverage_bytes).hexdigest(),
        },
        "population": {
            "raw_rows": sum(row["row_count"] for row in profiles),
            "raw_bytes": sum(row["raw_bytes"] for row in profiles),
            "stations": len(profiles),
            "schema_variants": len({row["schema_sha256"] for row in profiles}),
            "partial_calendar_stations": sum(not row["min_date"].startswith("2024-01-01") or not row["max_date"].startswith("2024-12-31") for row in profiles),
            "stations_with_temperature": sum(row["usable_temperature_rows"] > 0 for row in profiles),
            "stations_with_dew_point": sum(row["usable_dew_point_rows"] > 0 for row in profiles),
            "stations_with_wind": sum(row["usable_wind_rows"] > 0 for row in profiles),
            "stations_with_visibility": sum(row["usable_visibility_rows"] > 0 for row in profiles),
            "stations_with_pressure": sum(row["usable_sea_level_pressure_rows"] > 0 for row in profiles),
            "stations_with_precipitation": sum(row["usable_precipitation_rows"] > 0 for row in profiles),
        },
        "authority": contract["authority"],
        "scientific_nonclaims": contract["scientific_nonclaims"],
    }
    report_path = data_root / "validation/POST-SUBTASK-067/noaa_isd_observed_coverage_pilot/sha256" / coverage_identity / "validation.json"
    _write_immutable(report_path, json.dumps(report, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(json.dumps({"result": report["result"], "coverage_identity": coverage_identity, "coverage_sha256": report["coverage_payload"]["sha256"], "report_path": str(report_path), "report_sha256": sha256_file(report_path), "population": report["population"]}, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

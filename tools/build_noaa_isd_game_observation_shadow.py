from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aggie_analytics.data.adapters import AcquisitionRequest, AcquisitionRoute, ResilientAcquirer, RetryPolicy  # noqa: E402
from aggie_analytics.data.http import PublicHTTPTransport  # noqa: E402
from aggie_analytics.data.snapshots import RawSnapshotStore  # noqa: E402
from aggie_analytics.features.observed_weather_shadow import (  # noqa: E402
    build_game_population,
    materialize,
    sha256_file,
    stable_hash,
    station_file_id,
)


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--issued-at-utc", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    args = parser.parse_args()
    data_root, output_root = args.data_root.resolve(), args.output_root.resolve()
    issued_at = parse_utc(args.issued_at_utc)
    contract_path = ROOT / "configs/noaa_isd_game_observation_shadow_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    games = build_game_population(data_root, contract)
    expected_pairs = sorted({(int(row["calendar_year"]), row["station_id"]) for row in games})
    if len(expected_pairs) != contract["population"]["expected_unique_station_years"]:
        raise RuntimeError("game station-year population drift")
    prior_spec = contract["inputs"]["observed_2024_acquisition_manifest"]
    prior_path = data_root / prior_spec["relative_path"]
    if sha256_file(prior_path) != prior_spec["sha256"]:
        raise RuntimeError("2024 observation acquisition manifest mismatch")
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    if prior["dataset_identity"] != prior_spec["identity"]:
        raise RuntimeError("2024 observation acquisition identity mismatch")
    prior_map = {(int(row["season"]), row["station_id"]): row for row in prior["captures"]}
    store = RawSnapshotStore(data_root)
    acquirer = ResilientAcquirer(store, retry_policy=RetryPolicy(max_attempts=4, base_delay_seconds=2.0, maximum_delay_seconds=30.0))
    transport = PublicHTTPTransport(args.timeout_seconds)
    captures = []
    for calendar_year, station_id in expected_pairs:
        if (calendar_year, station_id) in prior_map:
            source = prior_map[(calendar_year, station_id)]
            captures.append(
                {
                    "calendar_year": calendar_year,
                    "station_id": station_id,
                    "station_file_id": source["station_file_id"],
                    "source_uri": source["source_uri"],
                    "snapshot_id": source["snapshot_id"],
                    "raw_relative_path": source["raw_relative_path"],
                    "raw_sha256": source["raw_sha256"],
                    "raw_bytes": source["raw_bytes"],
                    "request_identity_sha256": source["request_identity_sha256"],
                    "capture_reuse_state": "REUSED_PINNED_2024_COVERAGE_PILOT",
                }
            )
            continue
        file_id = station_file_id(station_id)
        source_uri = contract["source"]["url_template"].format(calendar_year=calendar_year, station_file_id=file_id)
        request = AcquisitionRequest(
            source_id=contract["source"]["source_id"],
            dataset=contract["source"]["dataset"],
            source_uri=source_uri,
            identity_components={
                "calendar_year": calendar_year,
                "decision_unit": contract["decision_unit"],
                "source_role": "FOOTBALL_SEASON_CALENDAR_BOUNDARY_OBSERVATION",
                "station_file_id": file_id,
            },
            extension=".csv",
        )
        acquired = acquirer.acquire((AcquisitionRoute("noaa-nodd-global-hourly-s3-https", request, transport),), retrieved_at=issued_at)
        snapshot = acquired.snapshot
        captures.append(
            {
                "calendar_year": calendar_year,
                "station_id": station_id,
                "station_file_id": file_id,
                "source_uri": source_uri,
                "snapshot_id": snapshot.snapshot_id,
                "raw_relative_path": snapshot.relative_path,
                "raw_sha256": snapshot.raw_sha256,
                "raw_bytes": (data_root / snapshot.relative_path).stat().st_size,
                "request_identity_sha256": acquired.request_identity_sha256,
                "capture_reuse_state": "CACHE_HIT" if acquired.from_cache else "NEW_IMMUTABLE_CAPTURE",
            }
        )
        print(json.dumps({"calendar_year": calendar_year, "station_id": station_id, "bytes": captures[-1]["raw_bytes"], "state": captures[-1]["capture_reuse_state"]}, sort_keys=True), flush=True)
    captures.sort(key=lambda row: (row["calendar_year"], row["station_id"]))
    capture_core = {
        "schema_version": "1.0.0",
        "artifact_type": "NOAA_ISD_GAME_OBSERVATION_STATION_YEAR_CAPTURES",
        "classification": contract["classification"],
        "contract_sha256": sha256_file(contract_path),
        "football_season": contract["population"]["football_season"],
        "station_year_pairs": [(row["calendar_year"], row["station_id"], row["raw_sha256"]) for row in captures],
    }
    capture_identity = stable_hash(capture_core)
    capture_manifest = {
        **capture_core,
        "capture_manifest_identity": capture_identity,
        "issued_at_utc": issued_at.isoformat().replace("+00:00", "Z"),
        "captures": captures,
        "capture_count": len(captures),
        "reused_2024_captures": sum(row["capture_reuse_state"] == "REUSED_PINNED_2024_COVERAGE_PILOT" for row in captures),
        "calendar_2025_captures": sum(row["calendar_year"] == 2025 for row in captures),
        "total_bytes_referenced": sum(row["raw_bytes"] for row in captures),
    }
    result = materialize(
        data_root=data_root,
        output_root=output_root,
        repo_root=ROOT,
        capture_manifest=capture_manifest,
        issued_at_utc=issued_at.isoformat().replace("+00:00", "Z"),
    )
    capture_path = output_root / "manifests/weather_game_observation_shadow/sha256" / result["dataset_identity"] / "capture_manifest.json"
    encoded = json.dumps(capture_manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    if capture_path.exists() and capture_path.read_bytes() != encoded:
        raise RuntimeError("game observation capture manifest collision")
    capture_path.parent.mkdir(parents=True, exist_ok=True)
    if not capture_path.exists():
        temporary = capture_path.with_name(capture_path.name + f".tmp-{os.getpid()}")
        temporary.write_bytes(encoded)
        os.replace(temporary, capture_path)
    print(json.dumps({key: value for key, value in result.items() if key != "manifest"} | {"capture_manifest_path": str(capture_path), "capture_manifest_sha256": sha256_file(capture_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

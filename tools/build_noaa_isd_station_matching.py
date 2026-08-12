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

from aggie_analytics.data.adapters import (  # noqa: E402
    AcquisitionRequest,
    AcquisitionRoute,
    ResilientAcquirer,
    RetryPolicy,
)
from aggie_analytics.data.http import PublicHTTPTransport  # noqa: E402
from aggie_analytics.data.snapshots import RawSnapshotStore  # noqa: E402
from aggie_analytics.features.weather_station_matching import materialize  # noqa: E402


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("issued-at timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Acquire NOAA ISD station history and materialize review-only venue candidates.")
    parser.add_argument("--input-data-root", type=Path, default=Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")))
    parser.add_argument("--output-data-root", type=Path, default=Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")))
    parser.add_argument("--issued-at-utc", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    args = parser.parse_args()
    input_root, output_root = args.input_data_root.resolve(), args.output_data_root.resolve()
    issued_at = parse_utc(args.issued_at_utc)
    contract = json.loads((ROOT / "configs/noaa_isd_station_matching_contract.json").read_text(encoding="utf-8"))
    source = contract["source"]
    request = AcquisitionRequest(
        source_id=source["source_id"],
        dataset=source["dataset"],
        source_uri=source["source_uri"],
        identity_components={
            "decision_unit": contract["decision_unit"],
            "schema_version": contract["schema_version"],
            "source_role": "STATION_PERIOD_OF_RECORD_CATALOG",
        },
        extension=source["extension"],
    )
    result = ResilientAcquirer(
        RawSnapshotStore(output_root),
        retry_policy=RetryPolicy(max_attempts=4, base_delay_seconds=2.0, maximum_delay_seconds=30.0),
    ).acquire(
        (AcquisitionRoute("noaa-ncei-public-https", request, PublicHTTPTransport(args.timeout_seconds)),),
        retrieved_at=issued_at,
    )
    snapshot = result.snapshot
    station_snapshot = {
        "snapshot_id": snapshot.snapshot_id,
        "raw_relative_path": snapshot.relative_path,
        "raw_sha256": snapshot.raw_sha256,
        "source_uri": snapshot.source_uri,
        "retrieved_at_utc": snapshot.retrieved_at.isoformat().replace("+00:00", "Z"),
        "request_identity_sha256": result.request_identity_sha256,
        "selected_route_id": result.selected_route_id,
        "from_cache": result.from_cache,
        "attempt_evidence": list(result.attempt_evidence),
    }
    built = materialize(
        input_data_root=input_root,
        output_data_root=output_root,
        repo_root=ROOT,
        station_payload_path=output_root / snapshot.relative_path,
        station_snapshot=station_snapshot,
        issued_at_utc=issued_at.isoformat().replace("+00:00", "Z"),
    )
    print(json.dumps({key: value for key, value in built.items() if key != "manifest"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

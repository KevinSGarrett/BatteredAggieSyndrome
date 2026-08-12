from __future__ import annotations

import argparse
from datetime import timezone
from email.utils import parsedate_to_datetime
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aggie_analytics.data.snapshots import RawSnapshotStore, request_identity_sha256  # noqa: E402
from aggie_analytics.features.gfs_multigame_selection import (  # noqa: E402
    candidate_runs,
    choose_attempt,
    load_population,
    materialize,
    parse_index_messages,
)
from aggie_analytics.features.gfs_issued_run import (  # noqa: E402
    _write_immutable,
    parse_utc,
    sha256_file,
    stable_hash,
)


USER_AGENT = "AggieAnalyticsEngine-private-research/1.0"


def get(
    url: str,
    *,
    byte_range: tuple[int, int] | None = None,
    timeout: float = 120.0,
) -> tuple[bytes, dict[str, str], int]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/octet-stream"}
    if byte_range:
        headers["Range"] = f"bytes={byte_range[0]}-{byte_range[1]}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as response:
        return response.read(), {key.lower(): value for key, value in response.headers.items()}, int(response.status)


def head(url: str, *, timeout: float = 120.0) -> tuple[int, dict[str, str]]:
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), {key.lower(): value for key, value in response.headers.items()}
    except urllib.error.HTTPError as exc:
        return int(exc.code), {key.lower(): value for key, value in exc.headers.items()}


def _selection_attempts(base_url: str, population: dict, contract: dict) -> list[dict]:
    cutoff = parse_utc(population["nominal_prediction_at_utc"])
    valid = parse_utc(population["forecast_valid_hour_utc"])
    policy = contract["selection"]
    attempts = []
    for candidate in candidate_runs(
        cutoff,
        valid,
        cycles_to_probe=policy["cycles_to_probe"],
        maximum_forecast_hour=policy["maximum_forecast_hour"],
    ):
        url = f"{base_url}/{candidate['object_key']}"
        status, headers = head(url)
        attempt = {**candidate, "http_status": status}
        if status != 200:
            attempt["disposition"] = "OBJECT_UNAVAILABLE"
        else:
            published = parsedate_to_datetime(headers["last-modified"]).astimezone(timezone.utc)
            attempt.update(
                {
                    "object_last_modified_utc": published.isoformat().replace("+00:00", "Z"),
                    "object_bytes": int(headers["content-length"]),
                    "etag": headers.get("etag", ""),
                    "disposition": "AVAILABLE_BY_CUTOFF" if published <= cutoff else "PUBLISHED_AFTER_CUTOFF",
                }
            )
        attempts.append(attempt)
        if attempt["disposition"] == "AVAILABLE_BY_CUTOFF":
            break
    return attempts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--issued-at-utc", required=True)
    args = parser.parse_args()
    issued = parse_utc(args.issued_at_utc)
    data_root, output_root = args.data_root.resolve(), args.output_root.resolve()
    contract_path = ROOT / "configs/noaa_gfs_multigame_selection_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    population = load_population(data_root, contract)
    base_url = contract["source"]["base_url"]
    store = RawSnapshotStore(data_root)
    selections = []
    for population_row in population:
        attempts = _selection_attempts(base_url, population_row, contract)
        selected = choose_attempt(attempts)
        object_url = f"{base_url}/{selected['object_key']}"
        index_url = f"{base_url}/{selected['index_object_key']}"
        index_bytes, index_headers, index_status = get(index_url)
        if index_status != 200:
            raise RuntimeError("GFS selected index request did not return 200")
        messages = parse_index_messages(
            index_bytes.decode("utf-8"),
            contract["messages"],
            selected["object_bytes"],
            selected["forecast_hour"],
        )
        publication = parse_utc(selected["object_last_modified_utc"])
        if issued < publication:
            raise RuntimeError("GFS retrieval timestamp predates the selected object's publication")
        index_snapshot = store.ingest_bytes(
            contract["source"]["source_id"],
            "noaa_gfs_grib_index",
            index_bytes,
            retrieved_at=issued,
            source_uri=index_url,
            extension=".idx",
            publication_time=publication,
            metadata={
                "object_key": selected["index_object_key"],
                "object_last_modified_utc": selected["object_last_modified_utc"],
                "etag": index_headers.get("etag", ""),
            },
        )
        captures = []
        for message in messages:
            byte_range = (message["range_start"], message["range_end"])
            identity = request_identity_sha256(
                contract["source"]["source_id"],
                "noaa_gfs_indexed_grib_message",
                "GET",
                object_url,
                {
                    "component": message["component"],
                    "range_start": byte_range[0],
                    "range_end": byte_range[1],
                },
            )
            cached = store.lookup_request(identity)
            if cached is None:
                payload, headers, status = get(object_url, byte_range=byte_range)
                if status != 206 or len(payload) != message["range_bytes"]:
                    raise RuntimeError("GFS byte-range response mismatch")
                snapshot = store.ingest_bytes(
                    contract["source"]["source_id"],
                    "noaa_gfs_indexed_grib_message",
                    payload,
                    retrieved_at=issued,
                    source_uri=object_url,
                    extension=".grib2",
                    publication_time=publication,
                    metadata={
                        "component": message["component"],
                        "range_start": byte_range[0],
                        "range_end": byte_range[1],
                        "index_line": message["line"],
                        "etag": headers.get("etag", ""),
                    },
                )
                store.bind_request(identity, snapshot)
                state = "NEW_IMMUTABLE_CAPTURE"
            else:
                snapshot, state = cached, "CACHE_HIT"
            captures.append(
                {
                    "component": message["component"],
                    "descriptor": message["descriptor"],
                    "index_line": message["line"],
                    "range_start": byte_range[0],
                    "range_end": byte_range[1],
                    "range_bytes": message["range_bytes"],
                    "accumulation_hours": message["accumulation_hours"],
                    "accumulation_start_hour": message["accumulation_start_hour"],
                    "raw_relative_path": snapshot.relative_path,
                    "raw_sha256": snapshot.raw_sha256,
                    "snapshot_id": snapshot.snapshot_id,
                    "request_identity_sha256": identity,
                    "capture_state": state,
                }
            )
        selection_core = {
            "selector_identity": population_row["selector_identity"],
            "source_game_id": population_row["source_game_id"],
            "cutoff_utc": population_row["nominal_prediction_at_utc"].replace(".000Z", "Z"),
            "valid_utc": population_row["forecast_valid_hour_utc"].replace(".000Z", "Z"),
            "initialization_utc": selected["initialization_utc"],
            "forecast_hour": selected["forecast_hour"],
            "object_key": selected["object_key"],
            "object_last_modified_utc": selected["object_last_modified_utc"],
            "object_bytes": selected["object_bytes"],
            "index_raw_sha256": index_snapshot.raw_sha256,
            "selection_attempts_sha256": stable_hash(attempts),
            "message_capture_sha256": sorted((row["component"], row["raw_sha256"]) for row in captures),
        }
        selections.append(
            {
                **selection_core,
                "selection_identity": stable_hash(selection_core),
                "selection_attempts": attempts,
                "index_snapshot_id": index_snapshot.snapshot_id,
                "index_raw_sha256": index_snapshot.raw_sha256,
                "object_bytes": selected["object_bytes"],
                "message_captures": captures,
            }
        )
        print(
            json.dumps(
                {
                    "event": "GFS_MULTIGAME_SELECTION_CAPTURED",
                    "source_game_id": population_row["source_game_id"],
                    "cutoff_utc": population_row["nominal_prediction_at_utc"],
                    "initialization_utc": selected["initialization_utc"],
                    "forecast_hour": selected["forecast_hour"],
                    "attempts": len(attempts),
                },
                sort_keys=True,
            ),
            flush=True,
        )
    capture_core = {
        "schema_version": "1.0.0",
        "artifact_type": "NOAA_GFS_MULTIGAME_SELECTION_CAPTURES",
        "classification": contract["classification"],
        "contract_sha256": sha256_file(contract_path),
        "acquisition_implementation_sha256": sha256_file(Path(__file__).resolve()),
        "input_sha256": contract["input"]["sha256"],
        "selection_identities": sorted(row["selection_identity"] for row in selections),
    }
    capture_manifest = {
        **capture_core,
        "capture_manifest_identity": stable_hash(capture_core),
        "issued_at_utc": args.issued_at_utc,
        "selections": selections,
    }
    result = materialize(
        data_root=data_root,
        output_root=output_root,
        repo_root=ROOT,
        capture_manifest=capture_manifest,
        issued_at_utc=args.issued_at_utc,
    )
    capture_path = (
        output_root
        / contract["artifact_roots"]["manifests"]
        / result["dataset_identity"]
        / "capture_manifest.json"
    )
    _write_immutable(capture_path, json.dumps(capture_manifest, sort_keys=True, indent=2).encode() + b"\n")
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "manifest"}
            | {"capture_manifest_path": str(capture_path), "capture_manifest_sha256": sha256_file(capture_path)},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

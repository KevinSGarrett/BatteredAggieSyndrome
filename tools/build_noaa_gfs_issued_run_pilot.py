from __future__ import annotations

import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path: sys.path.insert(0, str(SRC))

from aggie_analytics.data.snapshots import RawSnapshotStore, request_identity_sha256  # noqa: E402
from aggie_analytics.features.gfs_issued_run import load_population, materialize, parse_index, sha256_file, stable_hash  # noqa: E402


def get(url: str, *, byte_range: tuple[int, int] | None = None, timeout: float = 120.0) -> tuple[bytes, dict[str, str], int]:
    headers = {"User-Agent": "AggieAnalyticsEngine-private-research/1.0", "Accept": "application/octet-stream"}
    if byte_range: headers["Range"] = f"bytes={byte_range[0]}-{byte_range[1]}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as response:
        return response.read(), {key.lower(): value for key, value in response.headers.items()}, int(response.status)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--issued-at-utc", required=True)
    args = parser.parse_args()
    issued = datetime.fromisoformat(args.issued_at_utc.replace("Z", "+00:00")).astimezone(timezone.utc)
    data_root, output_root = args.data_root.resolve(), args.output_root.resolve()
    contract_path = ROOT / "configs/noaa_gfs_issued_run_pilot_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8")); load_population(data_root, contract)
    base, run = contract["source"]["base_url"], contract["issued_run"]
    index_url, object_url = f"{base}/{run['index_object_key']}", f"{base}/{run['object_key']}"
    index_bytes, index_headers, index_status = get(index_url)
    if index_status != 200: raise RuntimeError("GFS index request did not return 200")
    object_bytes = int(index_headers.get("x-amz-meta-grib-content-length", "0") or 0)
    if not object_bytes:
        request = urllib.request.Request(object_url, method="HEAD", headers={"User-Agent": "AggieAnalyticsEngine-private-research/1.0"})
        with urllib.request.urlopen(request, timeout=120) as response:
            object_bytes = int(response.headers["Content-Length"]); object_last_modified = parsedate_to_datetime(response.headers["Last-Modified"]).astimezone(timezone.utc)
    else:
        object_last_modified = parsedate_to_datetime(index_headers["last-modified"]).astimezone(timezone.utc)
    last_modified = object_last_modified.isoformat().replace("+00:00", "Z")
    if last_modified != run["expected_object_last_modified_utc"]: raise RuntimeError("GFS object Last-Modified drift")
    selections = parse_index(index_bytes.decode("utf-8"), contract["messages"], object_bytes)
    store = RawSnapshotStore(data_root)
    index_snapshot = store.ingest_bytes(contract["source"]["source_id"], "noaa_gfs_grib_index", index_bytes, retrieved_at=issued, source_uri=index_url, extension=".idx", publication_time=object_last_modified, metadata={"object_key": run["index_object_key"], "object_last_modified_utc": last_modified})
    captures = []
    for selection in selections:
        byte_range = (selection["range_start"], selection["range_end"])
        identity = request_identity_sha256(contract["source"]["source_id"], "noaa_gfs_indexed_grib_message", "GET", object_url, {"component": selection["component"], "range_start": byte_range[0], "range_end": byte_range[1]})
        cached = store.lookup_request(identity)
        if cached is None:
            payload, headers, status = get(object_url, byte_range=byte_range)
            if status != 206 or len(payload) != selection["range_bytes"]: raise RuntimeError("GFS byte-range response mismatch")
            snapshot = store.ingest_bytes(contract["source"]["source_id"], "noaa_gfs_indexed_grib_message", payload, retrieved_at=issued, source_uri=object_url, extension=".grib2", publication_time=object_last_modified, metadata={"component": selection["component"], "range_start": byte_range[0], "range_end": byte_range[1], "index_line": selection["line"], "etag": headers.get("etag", "")})
            store.bind_request(identity, snapshot); state = "NEW_IMMUTABLE_CAPTURE"
        else: snapshot, state = cached, "CACHE_HIT"
        captures.append({"component": selection["component"], "index_line": selection["line"], "range_start": byte_range[0], "range_end": byte_range[1], "raw_relative_path": snapshot.relative_path, "raw_sha256": snapshot.raw_sha256, "snapshot_id": snapshot.snapshot_id, "request_identity_sha256": identity, "capture_state": state})
    core = {"schema_version": "1.0.0", "artifact_type": "NOAA_GFS_ISSUED_RUN_PILOT_CAPTURES", "classification": contract["classification"], "contract_sha256": sha256_file(contract_path), "object_key": run["object_key"], "object_last_modified_utc": last_modified, "message_capture_sha256": sorted((row["component"], row["raw_sha256"]) for row in captures)}
    capture_manifest = {**core, "capture_manifest_identity": stable_hash(core), "issued_at_utc": args.issued_at_utc, "index_snapshot_id": index_snapshot.snapshot_id, "index_raw_sha256": index_snapshot.raw_sha256, "object_bytes": object_bytes, "message_captures": captures}
    result = materialize(data_root=data_root, output_root=output_root, repo_root=ROOT, capture_manifest=capture_manifest, issued_at_utc=args.issued_at_utc)
    capture_path = output_root / contract["artifact_roots"]["manifests"] / result["dataset_identity"] / "capture_manifest.json"
    payload = json.dumps(capture_manifest, sort_keys=True, indent=2).encode() + b"\n"
    if capture_path.exists() and capture_path.read_bytes() != payload: raise RuntimeError("GFS capture manifest collision")
    if not capture_path.exists(): capture_path.write_bytes(payload)
    print(json.dumps({key: value for key, value in result.items() if key != "manifest"} | {"capture_manifest_path": str(capture_path), "capture_manifest_sha256": sha256_file(capture_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__": raise SystemExit(main())

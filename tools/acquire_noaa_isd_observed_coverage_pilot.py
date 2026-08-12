from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aggie_analytics.data.adapters import AcquisitionRequest, AcquisitionRoute, ResilientAcquirer, RetryPolicy  # noqa: E402
from aggie_analytics.data.http import PublicHTTPTransport  # noqa: E402
from aggie_analytics.data.snapshots import RawSnapshotStore  # noqa: E402


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
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def station_file_id(station_id: str) -> str:
    parts = station_id.split("-")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise ValueError(f"invalid NOAA ISD station identity: {station_id}")
    usaf, wban = parts
    if len(usaf) != 6 or len(wban) != 5:
        raise ValueError(f"invalid NOAA ISD station identity width: {station_id}")
    return usaf + wban


def load_population(data_root: Path, contract: dict[str, object]) -> list[dict[str, object]]:
    input_contract = contract["input"]
    assert isinstance(input_contract, dict)
    manifest_path = data_root / str(input_contract["station_matching_manifest_relative_path"])
    candidate_path = data_root / str(input_contract["station_candidate_relative_path"])
    if sha256_file(manifest_path) != input_contract["station_matching_manifest_sha256"]:
        raise RuntimeError("station-matching manifest identity mismatch")
    if sha256_file(candidate_path) != input_contract["station_candidate_sha256"]:
        raise RuntimeError("station-candidate payload identity mismatch")
    source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if source_manifest["dataset_identity"] != input_contract["station_matching_identity"]:
        raise RuntimeError("station-matching dataset identity mismatch")
    pilot = contract["pilot_population"]
    assert isinstance(pilot, dict)
    selected: dict[str, dict[str, object]] = {}
    with candidate_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if int(row["season"]) != int(pilot["season"]) or int(row["station_rank"]) != int(pilot["station_rank"]):
                continue
            station_id = row["station_id"]
            selected.setdefault(
                station_id,
                {
                    "season": int(row["season"]),
                    "station_id": station_id,
                    "station_file_id": station_file_id(station_id),
                    "referenced_venue_ids": set(),
                },
            )["referenced_venue_ids"].add(row["venue_id"])
    output = []
    for station_id in sorted(selected):
        record = selected[station_id]
        record["referenced_venue_ids"] = sorted(record["referenced_venue_ids"])
        output.append(record)
    if len(output) != int(pilot["expected_unique_station_years"]):
        raise RuntimeError(f"station-year population drift: {len(output)}")
    return output


def write_immutable_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise RuntimeError(f"immutable manifest collision: {path}")
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
                raise RuntimeError(f"immutable manifest collision: {path}")
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Acquire a resumable NOAA ISD observed station-year coverage pilot.")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--issued-at-utc", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument("--maximum-stations", type=int, default=None)
    args = parser.parse_args()
    data_root = args.data_root.resolve()
    issued_at = parse_utc(args.issued_at_utc)
    contract_path = ROOT / "configs/noaa_isd_observed_coverage_pilot_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    population = load_population(data_root, contract)
    selected = population if args.maximum_stations is None else population[: args.maximum_stations]
    if not selected:
        raise RuntimeError("pilot selection is empty")
    source = contract["source"]
    store = RawSnapshotStore(data_root)
    acquirer = ResilientAcquirer(store, retry_policy=RetryPolicy(max_attempts=4, base_delay_seconds=2.0, maximum_delay_seconds=30.0))
    transport = PublicHTTPTransport(args.timeout_seconds)
    captures = []
    for index, station in enumerate(selected, start=1):
        source_uri = source["url_template"].format(**station)
        request = AcquisitionRequest(
            source_id=source["source_id"],
            dataset=source["dataset"],
            source_uri=source_uri,
            identity_components={
                "decision_unit": contract["decision_unit"],
                "pilot_season": station["season"],
                "station_file_id": station["station_file_id"],
                "station_matching_identity": contract["input"]["station_matching_identity"],
                "station_rank": contract["pilot_population"]["station_rank"],
            },
            extension=source["extension"],
        )
        result = acquirer.acquire((AcquisitionRoute("noaa-nodd-global-hourly-s3-https", request, transport),), retrieved_at=issued_at)
        snapshot = result.snapshot
        captures.append(
            {
                **station,
                "source_uri": source_uri,
                "snapshot_id": snapshot.snapshot_id,
                "raw_relative_path": snapshot.relative_path,
                "raw_sha256": snapshot.raw_sha256,
                "raw_bytes": (data_root / snapshot.relative_path).stat().st_size,
                "request_identity_sha256": result.request_identity_sha256,
                "from_cache": result.from_cache,
                "attempt_evidence": list(result.attempt_evidence),
            }
        )
        print(json.dumps({"index": index, "total": len(selected), "station_id": station["station_id"], "from_cache": result.from_cache, "raw_bytes": captures[-1]["raw_bytes"]}, sort_keys=True), flush=True)
    core = {
        "schema_version": "1.0.0",
        "artifact_type": "NOAA_ISD_OBSERVED_STATION_YEAR_COVERAGE_PILOT",
        "classification": contract["classification"],
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "contract_sha256": sha256_file(contract_path),
        "station_matching_identity": contract["input"]["station_matching_identity"],
        "pilot_population": contract["pilot_population"],
        "selected_station_years": len(selected),
        "complete_population_run": len(selected) == len(population),
        "authority": contract["authority"],
        "capture_identities": [row["raw_sha256"] for row in captures],
    }
    identity = stable_hash(core)
    manifest = {
        **core,
        "dataset_identity": identity,
        "issued_at_utc": issued_at.isoformat().replace("+00:00", "Z"),
        "captures": captures,
        "capture_count": len(captures),
        "total_bytes": sum(row["raw_bytes"] for row in captures),
        "cache_hits": sum(bool(row["from_cache"]) for row in captures),
        "missingness": contract["missingness"],
        "scientific_nonclaims": contract["scientific_nonclaims"],
    }
    manifest_path = data_root / contract["artifact_root"] / identity / "acquisition_manifest.json"
    write_immutable_json(manifest_path, manifest)
    print(json.dumps({"dataset_identity": identity, "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path), "capture_count": len(captures), "total_bytes": manifest["total_bytes"], "cache_hits": manifest["cache_hits"]}, indent=2, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

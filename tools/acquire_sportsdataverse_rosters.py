from __future__ import annotations

"""Acquire pinned SportsDataverse roster release assets after CFBD route failure."""

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aggie_analytics.data.adapters import (
    AcquisitionRequest,
    AcquisitionRoute,
    ResilientAcquirer,
    RetryPolicy,
)
from aggie_analytics.data.http import PublicHTTPTransport
from aggie_analytics.data.snapshots import RawSnapshotStore


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


def write_immutable_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    if path.is_file():
        if path.read_bytes() != payload:
            raise RuntimeError(f"immutable manifest collision: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--data-root", type=Path, required=True)
    result.add_argument("--config", type=Path, required=True)
    result.add_argument("--issued-at-utc", required=True)
    result.add_argument("--timeout-seconds", type=float, default=180.0)
    return result


def main() -> int:
    args = parser().parse_args()
    root = args.data_root.resolve()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    issued_at = parse_utc(args.issued_at_utc)
    store = RawSnapshotStore(root)
    acquirer = ResilientAcquirer(
        store,
        retry_policy=RetryPolicy(max_attempts=4, base_delay_seconds=2.0, maximum_delay_seconds=60.0),
    )
    transport = PublicHTTPTransport(timeout_seconds=args.timeout_seconds)
    captures: list[dict[str, Any]] = []
    for asset in config["assets"]:
        request = AcquisitionRequest(
            source_id=config["source_id"],
            dataset="sportsdataverse_rosters_post2022",
            source_uri=asset["url"],
            identity_components={
                "asset_name": asset["name"],
                "asset_sha256": asset["sha256"],
                "release_id": config["release_id"],
                "release_tag": config["release_tag"],
                "run_id": config["run_id"],
                "season": asset["season"],
            },
            extension=".parquet",
        )
        result = acquirer.acquire(
            (AcquisitionRoute("sportsdataverse-github-release", request, transport),),
            retrieved_at=issued_at,
        )
        snapshot = result.snapshot
        payload_path = root / snapshot.relative_path
        actual_size = payload_path.stat().st_size
        actual_sha = sha256_file(payload_path)
        if actual_size != int(asset["size"]) or actual_sha != asset["sha256"]:
            store.quarantine_snapshot(
                snapshot.snapshot_id,
                reason_code="CORRUPTED_RECORD",
                quarantined_at=issued_at,
                details={
                    "finding": "RELEASE_ASSET_DIGEST_OR_SIZE_MISMATCH",
                    "expected_bytes": int(asset["size"]),
                    "actual_bytes": actual_size,
                    "expected_sha256": asset["sha256"],
                    "actual_sha256": actual_sha,
                },
            )
            raise RuntimeError(f"release asset integrity failure: {asset['name']}")
        captures.append(
            {
                "season": int(asset["season"]),
                "asset_name": asset["name"],
                "asset_updated_at_utc": asset["updated_at_utc"],
                "source_uri": asset["url"],
                "request_identity_sha256": result.request_identity_sha256,
                "snapshot_id": snapshot.snapshot_id,
                "raw_relative_path": snapshot.relative_path,
                "raw_sha256": actual_sha,
                "raw_bytes": actual_size,
                "retrieved_at_utc": snapshot.retrieved_at.isoformat().replace("+00:00", "Z"),
                "from_cache": result.from_cache,
                "attempt_evidence": list(result.attempt_evidence),
            }
        )
    captures.sort(key=lambda row: row["season"])
    core = {
        "schema_version": "1.0.0",
        "artifact_type": "SPORTSDATAVERSE_ROSTER_RELEASE_ACQUISITION_MANIFEST",
        "decision_unit": config["decision_unit"],
        "run_id": config["run_id"],
        "classification": config["classification"],
        "source_id": config["source_id"],
        "provider": config["provider"],
        "repository": config["repository"],
        "release_id": config["release_id"],
        "release_tag": config["release_tag"],
        "release_published_at_utc": config["release_published_at_utc"],
        "release_inventory_checked_at_utc": config["release_inventory_checked_at_utc"],
        "config_sha256": sha256_file(config_path),
        "captures": captures,
        "capture_count": len(captures),
        "seasons": [row["season"] for row in captures],
        "total_bytes": sum(row["raw_bytes"] for row in captures),
        "authority": config["authority"],
        "superseded_primary_route_finding": "CFBD_REST_HTTP_429_AFTER_FOUR_BOUNDED_ATTEMPTS",
    }
    identity = stable_hash(core)
    manifest = {
        **core,
        "acquisition_identity": identity,
        "issued_at_utc": issued_at.isoformat().replace("+00:00", "Z"),
    }
    manifest_path = (
        root / "manifests" / "acquisition" / config["run_id"] / "sha256" / identity
        / "sportsdataverse_roster_acquisition_manifest.json"
    )
    write_immutable_json(manifest_path, manifest)
    print(json.dumps({
        "acquisition_identity": identity,
        "capture_count": len(captures),
        "seasons": core["seasons"],
        "total_bytes": core["total_bytes"],
        "cache_hits": sum(bool(row["from_cache"]) for row in captures),
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

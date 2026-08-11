from __future__ import annotations

"""Acquire a finite CFBD request plan into the immutable external raw store."""

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aggie_analytics.data.adapters import AcquisitionRoute, ResilientAcquirer, RetryPolicy
from aggie_analytics.data.cfbd import CFBDTransport, acquisition_request, load_dotenv_value
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
        raise ValueError("issued-at timestamp must be timezone-aware")
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


def manifest_core(config: dict[str, Any], config_sha256: str, captures: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "artifact_type": "CFBD_FINITE_ACQUISITION_MANIFEST",
        "decision_unit": config["decision_unit"],
        "run_id": config["run_id"],
        "classification": config["classification"],
        "source_id": config["source_id"],
        "endpoint_id": config["endpoint_id"],
        "config_sha256": config_sha256,
        "captures": captures,
        "capture_count": len(captures),
        "total_rows": sum(int(row["row_count"]) for row in captures),
        "total_bytes": sum(int(row["raw_bytes"]) for row in captures),
        "seasons": sorted({int(row["parameters"]["year"]) for row in captures}),
        "authority": config["authority"],
    }


def validate_source_registry(repo_root: Path, config: dict[str, Any]) -> None:
    registry_path = repo_root / "configs" / "source_acquisition_registry.json"
    if sha256_file(registry_path) != config["source_acquisition_registry_sha256"]:
        raise RuntimeError("source acquisition registry drift")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    source = next(
        (row for row in registry["sources"] if row["source_id"] == config["source_id"]),
        None,
    )
    if source is None:
        raise RuntimeError("configured source is absent from acquisition registry")
    endpoint = next(
        (row for row in source["endpoints"] if row["endpoint_id"] == config["endpoint_id"]),
        None,
    )
    if endpoint is None or endpoint["path"] != config["path"]:
        raise RuntimeError("configured endpoint does not match acquisition registry")
    allowed = set(endpoint["allowed_parameters"])
    required = set(endpoint["required_parameters"])
    current_year = datetime.now(timezone.utc).year
    for parameters in config["requests"]:
        keys = set(parameters)
        if not keys <= allowed or not required <= keys:
            raise RuntimeError("request parameters violate acquisition registry")
        year = int(parameters["year"])
        if year < int(endpoint["allowed_seasons"]["minimum"]) or year > current_year:
            raise RuntimeError("request season violates acquisition registry")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--data-root", type=Path, required=True)
    result.add_argument("--env-file", type=Path, required=True)
    result.add_argument("--config", type=Path, required=True)
    result.add_argument("--issued-at-utc", required=True)
    result.add_argument("--timeout-seconds", type=float, default=90.0)
    return result


def main() -> int:
    args = parser().parse_args()
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    config_path = args.config.resolve()
    if repo_root not in config_path.parents:
        raise ValueError("acquisition config must be versioned in the repository")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_source_registry(repo_root, config)
    issued_at = parse_utc(args.issued_at_utc)
    credential_value = load_dotenv_value(
        args.env_file.resolve(), config["credential_environment_variable"]
    )
    transport = CFBDTransport(credential_value, timeout_seconds=args.timeout_seconds)
    store = RawSnapshotStore(data_root)
    acquirer = ResilientAcquirer(
        store,
        retry_policy=RetryPolicy(max_attempts=4, base_delay_seconds=2.0, maximum_delay_seconds=60.0),
    )

    captures: list[dict[str, Any]] = []
    for parameters in config["requests"]:
        request = acquisition_request(
            endpoint_id=config["endpoint_id"],
            path=config["path"],
            parameters=parameters,
            run_id=config["run_id"],
        )
        result = acquirer.acquire(
            (AcquisitionRoute("cfbd-rest-primary", request, transport),),
            retrieved_at=issued_at,
        )
        snapshot = result.snapshot
        if snapshot.row_count < int(config["expected_minimum_rows_per_season"]):
            store.quarantine_snapshot(
                snapshot.snapshot_id,
                reason_code="SCHEMA_INCOMPATIBLE",
                quarantined_at=issued_at,
                details={"finding": "ROW_COUNT_BELOW_CONFIGURED_MINIMUM"},
            )
            raise RuntimeError(f"row-count gate failed for year={parameters['year']}")
        payload_path = data_root / snapshot.relative_path
        captures.append(
            {
                "parameters": dict(sorted(parameters.items())),
                "request_identity_sha256": result.request_identity_sha256,
                "snapshot_id": snapshot.snapshot_id,
                "raw_sha256": snapshot.raw_sha256,
                "raw_relative_path": snapshot.relative_path,
                "raw_bytes": payload_path.stat().st_size,
                "row_count": snapshot.row_count,
                "schema_fields": list(snapshot.schema_fields),
                "source_uri": snapshot.source_uri,
                "retrieved_at": snapshot.retrieved_at.isoformat().replace("+00:00", "Z"),
                "from_cache": result.from_cache,
                "attempt_evidence": list(result.attempt_evidence),
            }
        )
    captures.sort(key=lambda row: canonical_bytes(row["parameters"]))
    core = manifest_core(config, sha256_file(config_path), captures)
    identity = stable_hash(core)
    manifest = {
        **core,
        "acquisition_identity": identity,
        "issued_at_utc": issued_at.isoformat().replace("+00:00", "Z"),
        "credential_value_logged_or_persisted": False,
    }
    manifest_path = (
        data_root
        / "manifests"
        / "acquisition"
        / config["run_id"]
        / "sha256"
        / identity
        / "cfbd_acquisition_manifest.json"
    )
    write_immutable_json(manifest_path, manifest)
    print(
        json.dumps(
            {
                "acquisition_identity": identity,
                "capture_count": len(captures),
                "total_rows": core["total_rows"],
                "total_bytes": core["total_bytes"],
                "seasons": core["seasons"],
                "manifest_path": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "cache_hits": sum(bool(row["from_cache"]) for row in captures),
                "credential_value_logged_or_persisted": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

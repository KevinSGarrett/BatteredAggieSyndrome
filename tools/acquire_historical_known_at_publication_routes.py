"""Acquire the declared national publication-time-bearing routes for the known-at audit.

This is the only Phase 6 command that touches the network. It attempts every route the
contract declares and records the outcome truthfully, including a route that carries no
publication instant at all. Deterministic validators and tests consume the manifest offline.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.adapters import AcquisitionFailure, AcquisitionRequest  # noqa: E402
from aggie_analytics.data.historical_known_at_authority import (  # noqa: E402
    CONTRACT_ID,
    CONTRACT_RELATIVE,
    extract_publication_instants,
    load_contract,
)
from aggie_analytics.data.national_foundation_reconciliation import (  # noqa: E402
    sha256_file,
    stable_hash,
)
from aggie_analytics.data.prospective_shadow_cohort import iso_utc, parse_utc  # noqa: E402
from aggie_analytics.data.snapshots import RawSnapshotStore  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from acquire_2026_prospective_schedule import TRANSIENT_CONDITIONS, build_routes  # noqa: E402

PROBE_ID = "HISTORICAL_KNOWN_AT_PUBLICATION_ROUTE_PROBE"


def route_uri(route: Mapping[str, Any]) -> str:
    uri = f"https://{route['official_host']}{route['path']}"
    parsed = urlsplit(uri)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != route["official_host"]:
        raise ValueError("a route URI must use the declared official HTTPS host")
    return uri


def attempt_route(
    *,
    store: RawSnapshotStore,
    contract: Mapping[str, Any],
    route: Mapping[str, Any],
    transports,
    retrieved_at: datetime,
    maximum_attempts: int,
) -> dict[str, Any]:
    request = AcquisitionRequest(
        source_id="SRC-KNOWN-AT-ROUTE",
        dataset=route["dataset"],
        source_uri=route_uri(route),
        identity_components={
            "contract_id": CONTRACT_ID,
            "decision_unit": contract["local_issue_id"],
            "probe_id": PROBE_ID,
            "route_id": route["route_id"],
        },
        extension=".html",
    )
    attempts: list[dict[str, Any]] = []
    for route_id, transport in transports:
        for attempt in range(1, maximum_attempts + 1):
            try:
                response = transport(request)
                status = int(response.status_code)
                if not 200 <= status < 300:
                    condition = "RATE_LIMITED" if status == 429 else f"HTTP_{status}"
                    raise AcquisitionFailure(condition, f"HTTP {status}", status_code=status)
            except AcquisitionFailure as error:
                attempts.append(
                    {"attempt": attempt, "condition": error.condition, "transport_id": route_id}
                )
                if error.condition in TRANSIENT_CONDITIONS and attempt < maximum_attempts:
                    continue
                break
            attempts.append({"attempt": attempt, "condition": "SUCCESS", "transport_id": route_id})
            document = response.body.decode("utf-8", "replace")
            snapshot = store.ingest_bytes(
                request.source_id,
                request.dataset,
                response.body,
                retrieved_at=retrieved_at,
                source_uri=request.source_uri,
                extension=request.extension,
                row_count=0,
                schema_fields=("probe_id", "route_id", "source_uri"),
                metadata={
                    "contract_id": CONTRACT_ID,
                    "decision_unit": contract["local_issue_id"],
                    "jira_key": contract["jira_key"],
                    "lane": contract["lane"],
                    "probe_id": PROBE_ID,
                    "route_id": route["route_id"],
                    "selected_transport_id": route_id,
                },
            )
            store.bind_request(request.identity_sha256, snapshot)
            return {
                "attempts": attempts,
                "publication_instants": extract_publication_instants(
                    document, contract["publication_instant_patterns"]
                ),
                "raw_bytes": len(response.body),
                "raw_relative_path": snapshot.relative_path,
                "raw_sha256": snapshot.raw_sha256,
                "request_identity_sha256": request.identity_sha256,
                "retrieved_at_utc": iso_utc(snapshot.retrieved_at),
                "route_id": route["route_id"],
                "selected_transport_id": route_id,
                "source_uri": request.source_uri,
                "state": "CAPTURED",
            }
    return {
        "attempts": attempts,
        "failure_condition": attempts[-1]["condition"] if attempts else "NO_AVAILABLE_TRANSPORT",
        "publication_instants": [],
        "request_identity_sha256": request.identity_sha256,
        "route_id": route["route_id"],
        "source_uri": request.source_uri,
        "state": "TECHNICALLY_UNAVAILABLE",
    }


def write_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--issued-at-utc", required=True)
    parser.add_argument("--maximum-attempts", type=int, default=2)
    args = parser.parse_args()

    repo_root, data_root = args.repo_root.resolve(), args.data_root.resolve()
    contract = load_contract(repo_root)
    retrieved_at = parse_utc(args.issued_at_utc)
    if retrieved_at > datetime.now(timezone.utc):
        raise ValueError("a capture must not claim a retrieval time in the future")

    store = RawSnapshotStore(data_root)
    transports = build_routes(args.env_file.resolve())

    rows = []
    for route in contract["publication_time_routes"]:
        row = attempt_route(
            store=store,
            contract=contract,
            route=route,
            transports=transports,
            retrieved_at=retrieved_at,
            maximum_attempts=args.maximum_attempts,
        )
        rows.append(row)
        print(
            json.dumps(
                {
                    "event": "KNOWN_AT_ROUTE_PROBE",
                    "observed_instant_count": len(row.get("publication_instants", [])),
                    "route_id": row["route_id"],
                    "state": row["state"],
                },
                sort_keys=True,
            ),
            flush=True,
        )

    core = {
        "artifact_type": "HISTORICAL_KNOWN_AT_PUBLICATION_ROUTE_CAPTURE_MANIFEST",
        "captured_count": sum(1 for row in rows if row["state"] == "CAPTURED"),
        "contract_id": CONTRACT_ID,
        "contract_sha256": sha256_file(repo_root / CONTRACT_RELATIVE),
        "decision_unit": contract["local_issue_id"],
        "jira_key": contract["jira_key"],
        "lane": contract["lane"],
        "probe_id": PROBE_ID,
        "routes": sorted(rows, key=lambda row: row["route_id"]),
        "schema_version": "aggie.data.historical_known_at_route_capture.v1",
    }
    identity = stable_hash(core)
    manifest = {**core, "capture_identity": identity, "issued_at_utc": iso_utc(retrieved_at)}
    path = (
        data_root
        / "manifests"
        / "known_at"
        / "historical_known_at_publication_routes"
        / "sha256"
        / identity
        / "historical_known_at_publication_route_manifest.json"
    )
    write_json(path, manifest)
    print(
        json.dumps(
            {
                "capture_identity": identity,
                "captured_count": core["captured_count"],
                "manifest_path": str(path),
                "route_count": len(rows),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

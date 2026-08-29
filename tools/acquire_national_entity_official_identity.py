"""Acquire official NCAA organization identity and season-record evidence.

This is an explicit operator acquisition command. It is never invoked by a
validator or by the deterministic test suite.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.adapters import AcquisitionFailure, AcquisitionRequest  # noqa: E402
from aggie_analytics.data.national_entity_identity_benchmark import (  # noqa: E402
    CONTRACT_ID,
    parse_organization_directory,
    parse_season_record_series,
)
from aggie_analytics.data.prospective_shadow_cohort import iso_utc  # noqa: E402
from aggie_analytics.data.snapshots import RawSnapshotStore  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from acquire_2026_prospective_schedule import TRANSIENT_CONDITIONS, build_routes  # noqa: E402


def history_uri(contract: dict, organization_id: int) -> str:
    source = contract["official_source"]
    template = source["team_history_path_template"].format(organization_id=organization_id)
    return f"https://{source['official_host']}{template}"


def rejected(document: str, contract: dict) -> str | None:
    source = contract["official_source"]
    lowered = document.lower()
    for marker in source["reject_case_insensitive_markers"]:
        if marker.lower() in lowered:
            return f"INTERSTITIAL_MARKER:{marker}"
    if len(document.encode("utf-8")) < int(source["minimum_html_bytes"]):
        return "BELOW_MINIMUM_HTML_BYTES"
    return None


def acquire_one(
    *,
    store: RawSnapshotStore,
    contract: dict,
    organization_id: int,
    transports,
    retrieved_at: datetime,
    maximum_attempts: int,
) -> dict:
    uri = history_uri(contract, organization_id)
    request = AcquisitionRequest(
        source_id=contract["official_source"]["source_id"],
        dataset="ncaa_official_team_history",
        source_uri=uri,
        identity_components={
            "contract_id": CONTRACT_ID,
            "decision_unit": contract["decision_unit"],
            "organization_id": str(organization_id),
            "sport_code": contract["official_source"]["sport_code"],
        },
        extension=".html",
    )
    attempts = 0
    last_reason = "NO_ROUTE_ATTEMPTED"
    for route_name, transport in transports:
        for _ in range(maximum_attempts):
            attempts += 1
            try:
                response = transport(request)
            except AcquisitionFailure as failure:
                last_reason = f"{route_name}:{failure.condition}"
                if failure.condition in TRANSIENT_CONDITIONS:
                    continue
                break
            document = response.body.decode("utf-8", "replace")
            reason = rejected(document, contract)
            if reason is not None or response.status_code != 200:
                last_reason = f"{route_name}:{reason or response.status_code}"
                continue
            snapshot = store.ingest_bytes(
                request.source_id,
                request.dataset,
                response.body,
                retrieved_at=retrieved_at,
                source_uri=request.source_uri,
                extension=request.extension,
                row_count=0,
                schema_fields=("organization_id", "season", "wins", "losses", "ties"),
            )
            store.bind_request(request.identity_sha256, snapshot)
            return {
                "acquisition_state": "ACQUIRED",
                "attempts": attempts,
                "organization_id": organization_id,
                "raw_bytes": len(response.body),
                "raw_relative_path": snapshot.relative_path,
                "raw_sha256": snapshot.raw_sha256,
                "request_identity_sha256": request.identity_sha256,
                "retrieved_at_utc": iso_utc(retrieved_at),
                "route": route_name,
                "season_record_series": parse_season_record_series(document),
                "source_uri": uri,
            }
    return {
        "acquisition_state": "UNAVAILABLE",
        "attempts": attempts,
        "organization_id": organization_id,
        "reason": last_reason,
        "request_identity_sha256": request.identity_sha256,
        "retrieved_at_utc": iso_utc(retrieved_at),
        "source_uri": uri,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--organizations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--maximum-attempts", type=int, default=2)
    parser.add_argument("--directory-organization-id", type=int, default=657)
    args = parser.parse_args()

    data_root = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
    if not data_root:
        print("AGGIE_ANALYTICS_DATA_ROOT must be mounted for acquisition", file=sys.stderr)
        return 2

    contract = json.loads(args.contract.read_text(encoding="utf-8-sig"))
    organizations = json.loads(args.organizations.read_text(encoding="utf-8-sig"))
    store = RawSnapshotStore(Path(data_root))
    transports = build_routes(args.env_file.resolve())
    retrieved_at = datetime.now(timezone.utc)

    rows = []
    directory: dict[str, int] = {}
    for organization_id in organizations["organization_ids"]:
        row = acquire_one(
            store=store,
            contract=contract,
            organization_id=int(organization_id),
            transports=transports,
            retrieved_at=retrieved_at,
            maximum_attempts=args.maximum_attempts,
        )
        rows.append(row)
        print(
            f"{organization_id:>7} {row['acquisition_state']:12s}"
            f" seasons={len(row.get('season_record_series') or [])}"
            f" {row.get('reason', '')}",
            flush=True,
        )
        if int(organization_id) == args.directory_organization_id and row["acquisition_state"] == "ACQUIRED":
            raw = (Path(data_root) / row["raw_relative_path"]).read_text("utf-8", errors="replace")
            directory = parse_organization_directory(raw)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "acquisitions": rows,
                "contract_id": CONTRACT_ID,
                "official_organization_directory": directory,
                "retrieved_at_utc": iso_utc(retrieved_at),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    acquired = sum(1 for row in rows if row["acquisition_state"] == "ACQUIRED")
    print(f"acquired {acquired}/{len(rows)}; directory entries {len(directory)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

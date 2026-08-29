"""Refresh the official Week Zero 2026 schedule, kickoff and final-status surface.

This is the only Phase 5 command that touches the network. It re-reads the official NCAA
scoreboard for each corrected Week Zero date at execution time and records both the
refreshed contest cards and any published official final status. Deterministic validators
and tests consume the resulting manifest offline.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.adapters import AcquisitionFailure, AcquisitionRequest  # noqa: E402
from aggie_analytics.data.national_foundation_reconciliation import (  # noqa: E402
    sha256_file,
    stable_hash,
)
from aggie_analytics.data.prospective_shadow_cohort import (  # noqa: E402
    iso_utc,
    parse_scoreboard_document,
    parse_utc,
)
from aggie_analytics.data.snapshots import RawSnapshotStore  # noqa: E402
from aggie_analytics.modeling.week_zero_live_shadow_execution import (  # noqa: E402
    CONTRACT_ID,
    CONTRACT_RELATIVE,
    load_contract,
    parse_official_finals,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from acquire_2026_prospective_schedule import (  # noqa: E402
    TRANSIENT_CONDITIONS,
    build_routes,
)

CHECKPOINT_ID = "WEEK_ZERO_LIVE_EXECUTION"


def scoreboard_uri(contract: Mapping[str, Any], game_date: str) -> str:
    source = contract["official_ncaa_source"]
    query = urllib.parse.urlencode(
        {
            "utf8": "\u2713",
            "sport_code": source["sport_code"],
            "academic_year": source["academic_year"],
            "division": source["division"],
            "game_date": datetime.strptime(game_date, "%Y-%m-%d").strftime("%m/%d/%Y"),
        }
    )
    uri = f"https://{source['official_host']}{source['path']}?{query}"
    parsed = urlsplit(uri)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != source["official_host"]:
        raise ValueError("capture URI must use the declared official HTTPS host")
    return uri


def profile(body: bytes, *, contract: Mapping[str, Any], game_date: str) -> dict[str, Any]:
    source = contract["official_ncaa_source"]
    text = body.decode("utf-8", "replace")
    lowered = text.casefold()
    matched = sorted(
        marker
        for marker in source["reject_case_insensitive_markers"]
        if marker.casefold() in lowered
    )
    if matched:
        raise AcquisitionFailure("ANTI_BOT_INTERSTITIAL", f"access interstitial markers: {matched}")
    if len(body) < int(source["minimum_html_bytes"]):
        raise AcquisitionFailure("CONTENT_TOO_SMALL", "response was below the declared minimum")
    if "livestream_scoreboards" not in lowered:
        raise AcquisitionFailure("SCHEMA_INCOMPATIBLE", "response was not a scoreboard page")
    cards = parse_scoreboard_document(text, game_date=game_date)
    return {
        "cards": cards,
        "finals": parse_official_finals(text, contract, game_date=game_date),
        "parsed_card_count": len(cards),
    }


def capture_date(
    *,
    store: RawSnapshotStore,
    contract: Mapping[str, Any],
    game_date: str,
    routes,
    retrieved_at: datetime,
    maximum_attempts: int,
) -> dict[str, Any]:
    source = contract["official_ncaa_source"]
    request = AcquisitionRequest(
        source_id=source["source_id"],
        dataset=source["dataset"],
        source_uri=scoreboard_uri(contract, game_date),
        identity_components={
            "contract_id": CONTRACT_ID,
            "checkpoint_id": CHECKPOINT_ID,
            "decision_unit": contract["local_issue_id"],
            "game_date": game_date,
            "execution_instant": iso_utc(retrieved_at),
        },
        extension=".html",
    )
    attempts: list[dict[str, Any]] = []
    for route_id, transport in routes:
        for attempt in range(1, maximum_attempts + 1):
            try:
                response = transport(request)
                status = int(response.status_code)
                if not 200 <= status < 300:
                    condition = "RATE_LIMITED" if status == 429 else f"HTTP_{status}"
                    raise AcquisitionFailure(condition, f"HTTP {status}", status_code=status)
                observed = profile(response.body, contract=contract, game_date=game_date)
            except AcquisitionFailure as error:
                attempts.append(
                    {"attempt": attempt, "condition": error.condition, "route_id": route_id}
                )
                if error.condition in TRANSIENT_CONDITIONS and attempt < maximum_attempts:
                    continue
                break
            attempts.append({"attempt": attempt, "condition": "SUCCESS", "route_id": route_id})
            snapshot = store.ingest_bytes(
                request.source_id,
                request.dataset,
                response.body,
                retrieved_at=retrieved_at,
                source_uri=request.source_uri,
                extension=request.extension,
                row_count=observed["parsed_card_count"],
                schema_fields=("checkpoint_id", "official_surface", "source_uri"),
                metadata={
                    "checkpoint_id": CHECKPOINT_ID,
                    "contract_id": CONTRACT_ID,
                    "decision_unit": contract["local_issue_id"],
                    "jira_key": contract["jira_key"],
                    "lane": contract["lane"],
                    "request_identity_sha256": request.identity_sha256,
                    "selected_route_id": route_id,
                },
            )
            store.bind_request(request.identity_sha256, snapshot)
            return {
                "attempts": attempts,
                "cards": observed["cards"],
                "finals": observed["finals"],
                "game_date": game_date,
                "parsed_card_count": observed["parsed_card_count"],
                "raw_relative_path": snapshot.relative_path,
                "raw_sha256": snapshot.raw_sha256,
                "request_identity_sha256": request.identity_sha256,
                "retrieved_at_utc": iso_utc(snapshot.retrieved_at),
                "route_id": route_id,
                "source_uri": request.source_uri,
                "state": "CAPTURED",
            }
    return {
        "attempts": attempts,
        "cards": [],
        "failure_condition": attempts[-1]["condition"] if attempts else "NO_AVAILABLE_ROUTE",
        "finals": [],
        "game_date": game_date,
        "request_identity_sha256": request.identity_sha256,
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
    routes = build_routes(args.env_file.resolve())

    captures = []
    refreshed_contests: list[dict[str, Any]] = []
    official_finals: list[dict[str, Any]] = []
    for game_date in contract["week_zero_game_dates"]:
        row = capture_date(
            store=store,
            contract=contract,
            game_date=game_date,
            routes=routes,
            retrieved_at=retrieved_at,
            maximum_attempts=args.maximum_attempts,
        )
        for card in row.pop("cards"):
            refreshed_contests.append({**card, "game_date": game_date})
        for final in row.pop("finals"):
            official_finals.append(
                {
                    **final,
                    "capture_sha256": row.get("raw_sha256"),
                    "retrieved_at_utc": row.get("retrieved_at_utc"),
                }
            )
        captures.append(row)
        print(
            json.dumps(
                {
                    "event": "WEEK_ZERO_LIVE_REFRESH",
                    "game_date": game_date,
                    "parsed_card_count": row.get("parsed_card_count"),
                    "state": row["state"],
                },
                sort_keys=True,
            ),
            flush=True,
        )

    core = {
        "artifact_type": "WEEK_ZERO_2026_LIVE_EXECUTION_CAPTURE_MANIFEST",
        "captured_count": sum(1 for row in captures if row["state"] == "CAPTURED"),
        "captures": sorted(captures, key=lambda row: row["game_date"]),
        "checkpoint_id": CHECKPOINT_ID,
        "contract_id": CONTRACT_ID,
        "contract_sha256": sha256_file(repo_root / CONTRACT_RELATIVE),
        "decision_unit": contract["local_issue_id"],
        "jira_key": contract["jira_key"],
        "lane": contract["lane"],
        "official_finals": sorted(official_finals, key=lambda row: row["ncaa_contest_id"]),
        "refreshed_contests": sorted(refreshed_contests, key=lambda row: row["ncaa_contest_id"]),
        "requested_game_dates": list(contract["week_zero_game_dates"]),
        "schema_version": "aggie.shadow.week_zero_2026_live_execution_capture.v1",
    }
    identity = stable_hash(core)
    manifest = {**core, "capture_identity": identity, "issued_at_utc": iso_utc(retrieved_at)}
    path = (
        data_root
        / "manifests"
        / "shadow"
        / "week_zero_2026_live_execution"
        / "sha256"
        / identity
        / "week_zero_2026_live_execution_capture_manifest.json"
    )
    write_json(path, manifest)
    print(
        json.dumps(
            {
                "capture_identity": identity,
                "captured_count": core["captured_count"],
                "manifest_path": str(path),
                "official_final_count": len(official_finals),
                "refreshed_contest_count": len(refreshed_contests),
                "result": "CAPTURED"
                if core["captured_count"] == len(captures)
                else "PARTIAL",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if core["captured_count"] == len(captures) else 2


if __name__ == "__main__":
    raise SystemExit(main())

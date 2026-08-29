"""Capture the Texas A&M T-7D checkpoint evidence from official surfaces.

This is the only Phase 1 command that touches the network. It captures the official
NCAA scoreboard pages for the corrected Week Zero and Week One dates and the official
Texas A&M athletics schedule page, scoping each request identity to the checkpoint so a
checkpoint capture is a genuinely new read rather than a replay of an earlier cache
entry. Deterministic validators and tests consume the resulting manifest offline.
"""

from __future__ import annotations

import argparse
import json
import os
import re
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
from aggie_analytics.data.week_zero_2026_calendar import (  # noqa: E402
    CONTRACT_ID,
    CONTRACT_RELATIVE,
    load_contract,
    parse_tamu_official_events,
    taxonomy_label,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from acquire_2026_prospective_schedule import (  # noqa: E402
    TRANSIENT_CONDITIONS,
    DirectTransport,
    build_routes,
)

CHECKPOINT_ID = "T_MINUS_7D"


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
    assert_official_uri(uri, source["official_host"])
    return uri


def tamu_uri(contract: Mapping[str, Any]) -> str:
    source = contract["official_tamu_source"]
    uri = f"https://{source['official_host']}{source['path']}"
    assert_official_uri(uri, source["official_host"])
    return uri


def assert_official_uri(uri: str, host: str) -> None:
    parsed = urlsplit(uri)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != host:
        raise ValueError("capture URI must use the declared official HTTPS host")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("capture URI must not carry credentials or a fragment")


def reject_interstitial(body: bytes, *, markers: list[str], minimum_bytes: int) -> str:
    text = body.decode("utf-8", "replace")
    lowered = text.casefold()
    matched = sorted(marker for marker in markers if marker.casefold() in lowered)
    if matched:
        raise AcquisitionFailure("ANTI_BOT_INTERSTITIAL", f"access interstitial markers: {matched}")
    if len(body) < int(minimum_bytes):
        raise AcquisitionFailure("CONTENT_TOO_SMALL", "response was below the declared minimum")
    return text


def profile_scoreboard(body: bytes, *, contract: Mapping[str, Any], game_date: str) -> dict[str, Any]:
    source = contract["official_ncaa_source"]
    text = reject_interstitial(
        body,
        markers=list(source["reject_case_insensitive_markers"]),
        minimum_bytes=int(source["minimum_html_bytes"]),
    )
    if "livestream_scoreboards" not in text.casefold():
        raise AcquisitionFailure("SCHEMA_INCOMPATIBLE", "response was not a scoreboard page")
    echoed = re.search(r'id="change_sport_game_date"[^>]*value="(\d{2}/\d{2}/\d{4})"', text)
    if echoed is None:
        raise AcquisitionFailure("SCHEMA_INCOMPATIBLE", "scoreboard did not echo its game date")
    echoed_date = datetime.strptime(echoed.group(1), "%m/%d/%Y").date().isoformat()
    if echoed_date != game_date:
        return {
            "date_observation_state": "SOURCE_SUBSTITUTED_A_DIFFERENT_DATE",
            "source_echoed_game_date": echoed_date,
            "parsed_card_count": 0,
        }
    cards = parse_scoreboard_document(text, game_date=game_date)
    return {
        "date_observation_state": (
            "OFFICIAL_CONTESTS_PRESENT" if cards else "NO_OFFICIAL_CONTESTS_ON_THIS_DATE"
        ),
        "source_echoed_game_date": echoed_date,
        "parsed_card_count": len(cards),
    }


def profile_tamu(body: bytes, *, contract: Mapping[str, Any]) -> dict[str, Any]:
    source = contract["official_tamu_source"]
    text = reject_interstitial(
        body,
        markers=list(source["reject_case_insensitive_markers"]),
        minimum_bytes=int(source["minimum_html_bytes"]),
    )
    events = parse_tamu_official_events(text)
    required = source["required_event_description"]
    matches = [event for event in events if event["description"] == required]
    if not matches:
        raise AcquisitionFailure(
            "SCHEMA_INCOMPATIBLE", f"official page did not carry the event {required!r}"
        )
    lowered = text.casefold()
    return {
        "structured_event_count": len(events),
        "target_event_present": True,
        "required_token_presence": {
            token: token.casefold() in lowered for token in source["required_tokens"]
        },
    }


def capture(
    *,
    store: RawSnapshotStore,
    contract: Mapping[str, Any],
    source_key: str,
    source_uri: str,
    identity_components: Mapping[str, Any],
    dataset: str,
    source_id: str,
    profiler,
    routes,
    retrieved_at: datetime,
    maximum_attempts: int,
) -> dict[str, Any]:
    request = AcquisitionRequest(
        source_id=source_id,
        dataset=dataset,
        source_uri=source_uri,
        identity_components=dict(identity_components),
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
                profile = profiler(response.body)
            except AcquisitionFailure as error:
                attempts.append(
                    {
                        "route_id": route_id,
                        "attempt": attempt,
                        "condition": error.condition,
                        "status_code": error.status_code,
                    }
                )
                if error.condition in TRANSIENT_CONDITIONS and attempt < maximum_attempts:
                    continue
                break
            attempts.append({"route_id": route_id, "attempt": attempt, "condition": "SUCCESS"})
            snapshot = store.ingest_bytes(
                request.source_id,
                request.dataset,
                response.body,
                retrieved_at=retrieved_at,
                source_uri=request.source_uri,
                extension=request.extension,
                row_count=int(profile.get("parsed_card_count") or 0),
                schema_fields=("checkpoint_id", "official_surface", "source_uri"),
                metadata={
                    "contract_id": CONTRACT_ID,
                    "decision_unit": contract["decision_unit"],
                    "jira_key": contract["jira_key"],
                    "lane": contract["lane"],
                    "checkpoint_id": CHECKPOINT_ID,
                    "request_identity_sha256": request.identity_sha256,
                    "selected_route_id": route_id,
                    "attempts": attempts,
                    "outcome_fields_extracted": False,
                },
            )
            store.bind_request(request.identity_sha256, snapshot)
            path = store.root / snapshot.relative_path
            return {
                "source_key": source_key,
                "state": "CAPTURED",
                "route_id": route_id,
                "source_uri": request.source_uri,
                "request_identity_sha256": request.identity_sha256,
                "raw_relative_path": snapshot.relative_path,
                "raw_sha256": snapshot.raw_sha256,
                "raw_bytes": path.stat().st_size,
                "retrieved_at_utc": iso_utc(snapshot.retrieved_at),
                **profile,
                "attempts": attempts,
            }
    return {
        "source_key": source_key,
        "state": "TECHNICALLY_UNAVAILABLE",
        "source_uri": source_uri,
        "request_identity_sha256": request.identity_sha256,
        "attempts": attempts,
        "failure_condition": attempts[-1]["condition"] if attempts else "NO_AVAILABLE_ROUTE",
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


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--data-root", type=Path, required=True)
    result.add_argument("--env-file", type=Path, required=True)
    result.add_argument("--issued-at-utc", required=True)
    result.add_argument("--maximum-attempts", type=int, default=2)
    return result


def main() -> int:
    args = parser().parse_args()
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    contract = load_contract(repo_root)
    retrieved_at = parse_utc(args.issued_at_utc)
    now = datetime.now(timezone.utc)
    if retrieved_at > now:
        raise ValueError("a capture must not claim a retrieval time in the future")

    checkpoint = next(
        row for row in contract["checkpoints"] if row["checkpoint_id"] == CHECKPOINT_ID
    )
    deadline = parse_utc(str(checkpoint["deadline_utc"]))
    if now >= deadline:
        print(
            json.dumps(
                {
                    "result": "MISSED_CUTOFF_NO_BACKFILL",
                    "checkpoint_id": CHECKPOINT_ID,
                    "deadline_utc": iso_utc(deadline),
                    "observed_utc": iso_utc(now),
                    "backfill_performed": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 3

    taxonomy = contract["corrected_season_taxonomy"]
    game_dates = sorted(
        set(taxonomy["week_zero_dates"])
        | set(taxonomy["week_zero_to_week_one_transition_dates"])
        | set(taxonomy["week_one_dates"])
    )
    store = RawSnapshotStore(data_root)
    routes = build_routes(args.env_file.resolve())
    captures: list[dict[str, Any]] = []
    for game_date in game_dates:
        row = capture(
            store=store,
            contract=contract,
            source_key=f"NCAA_SCOREBOARD:{game_date}",
            source_uri=scoreboard_uri(contract, game_date),
            identity_components={
                "contract_id": CONTRACT_ID,
                "checkpoint_id": CHECKPOINT_ID,
                "decision_unit": contract["decision_unit"],
                "game_date": game_date,
            },
            dataset=contract["official_ncaa_source"]["dataset"],
            source_id=contract["official_ncaa_source"]["source_id"],
            profiler=lambda body, game_date=game_date: profile_scoreboard(
                body, contract=contract, game_date=game_date
            ),
            routes=routes,
            retrieved_at=retrieved_at,
            maximum_attempts=args.maximum_attempts,
        )
        row["game_date"] = game_date
        row["corrected_label"] = taxonomy_label(contract, game_date)
        captures.append(row)
        print(
            json.dumps(
                {
                    "event": "WEEK_ZERO_2026_T7D_CAPTURE",
                    "game_date": game_date,
                    "state": row["state"],
                    "date_observation_state": row.get("date_observation_state"),
                    "parsed_card_count": row.get("parsed_card_count"),
                },
                sort_keys=True,
            ),
            flush=True,
        )

    tamu = capture(
        store=store,
        contract=contract,
        source_key="TAMU_OFFICIAL_SCHEDULE",
        source_uri=tamu_uri(contract),
        identity_components={
            "contract_id": CONTRACT_ID,
            "checkpoint_id": CHECKPOINT_ID,
            "decision_unit": contract["decision_unit"],
            "official_surface": "TAMU_OFFICIAL_FOOTBALL_SCHEDULE_2026",
        },
        dataset=contract["official_tamu_source"]["dataset"],
        source_id=contract["official_tamu_source"]["source_id"],
        profiler=lambda body: profile_tamu(body, contract=contract),
        routes=[("direct_http", DirectTransport())],
        retrieved_at=retrieved_at,
        maximum_attempts=args.maximum_attempts,
    )
    captures.append(tamu)
    print(
        json.dumps(
            {
                "event": "WEEK_ZERO_2026_T7D_CAPTURE",
                "source_key": tamu["source_key"],
                "state": tamu["state"],
                "target_event_present": tamu.get("target_event_present"),
            },
            sort_keys=True,
        ),
        flush=True,
    )

    captured = [row for row in captures if row["state"] == "CAPTURED"]
    core = {
        "schema_version": "aggie.shadow.week_zero_2026_t7d_capture.v1",
        "artifact_type": "WEEK_ZERO_2026_T7D_CAPTURE_MANIFEST",
        "contract_id": CONTRACT_ID,
        "checkpoint_id": CHECKPOINT_ID,
        "checkpoint_deadline_utc": iso_utc(deadline),
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "lane": contract["lane"],
        "contract_sha256": sha256_file(repo_root / CONTRACT_RELATIVE),
        "requested_game_dates": game_dates,
        "captures": sorted(captures, key=lambda row: row["source_key"]),
        "captured_count": len(captured),
        "technical_failure_count": len(captures) - len(captured),
        "total_raw_bytes": sum(int(row["raw_bytes"]) for row in captured),
        "captured_before_deadline": all(
            parse_utc(str(row["retrieved_at_utc"])) < deadline for row in captured
        ),
        "backdated_capture_performed": False,
        "outcome_fields_extracted": False,
    }
    identity = stable_hash(core)
    manifest = {**core, "capture_identity": identity, "issued_at_utc": iso_utc(retrieved_at)}
    path = (
        data_root
        / "manifests"
        / "shadow"
        / "week_zero_2026_t7d_capture"
        / "sha256"
        / identity
        / "week_zero_2026_t7d_capture_manifest.json"
    )
    write_json(path, manifest)
    print(
        json.dumps(
            {
                "result": "CAPTURED" if len(captured) == len(captures) else "PARTIAL",
                "capture_identity": identity,
                "manifest_path": str(path),
                "manifest_sha256": sha256_file(path),
                "captured_count": len(captured),
                "technical_failure_count": core["technical_failure_count"],
                "checkpoint_id": CHECKPOINT_ID,
                "captured_before_deadline": core["captured_before_deadline"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if len(captured) == len(captures) else 2


if __name__ == "__main__":
    raise SystemExit(main())

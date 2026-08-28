"""Re-fetch official 2026 Division I schedule pages into the immutable lake.

This is the only Phase 7 command that touches the network. It captures one
official scoreboard page per declared game date, validates that the response is a
real scoreboard rather than an anti-bot interstitial, and writes a content
addressed capture manifest that the offline cohort builder consumes.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.adapters import (  # noqa: E402
    AcquisitionFailure,
    AcquisitionRequest,
    FetchResponse,
)
from aggie_analytics.data.national_foundation_reconciliation import (  # noqa: E402
    sha256_file,
    stable_hash,
)
from aggie_analytics.data.prospective_shadow_cohort import (  # noqa: E402
    CONTRACT_ID,
    iso_utc,
    load_contract,
    parse_scoreboard_document,
    parse_utc,
)
from aggie_analytics.data.snapshots import RawSnapshotStore  # noqa: E402

TRANSIENT_CONDITIONS = frozenset({"CONNECTION_ERROR", "RATE_LIMITED", "SERVER_ERROR", "TIMEOUT"})
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


def scoreboard_uri(contract: Mapping[str, Any], game_date: str) -> str:
    source = contract["official_source"]
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
        raise ValueError("scoreboard URI must use the official HTTPS host")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("scoreboard URI must not carry credentials or a fragment")
    return uri


def validate_scoreboard(body: bytes, *, contract: Mapping[str, Any], game_date: str) -> dict[str, Any]:
    """Classify one scoreboard response without conflating three different facts.

    A date can legitimately carry no Division I football contest, in which case the
    page renders its shell with no results table. Separately, the official host
    silently substitutes the season's first available date when a requested date
    precedes it. That substitution is recorded rather than accepted, because
    accepting it would attribute one date's games to another.
    """

    source = contract["official_source"]
    text = body.decode("utf-8", "replace")
    lowered = text.casefold()
    matched = sorted(marker for marker in source["reject_case_insensitive_markers"] if marker.casefold() in lowered)
    if matched:
        raise AcquisitionFailure("ANTI_BOT_INTERSTITIAL", f"response carried access interstitial markers: {matched}")
    if len(body) < int(source["minimum_html_bytes"]):
        raise AcquisitionFailure("CONTENT_TOO_SMALL", "response was below the minimum scoreboard size")
    if "livestream_scoreboards" not in lowered:
        raise AcquisitionFailure("SCHEMA_INCOMPATIBLE", "response was not a recognizable scoreboard page")
    echoed = re.search(r'id="change_sport_game_date"[^>]*value="(\d{2}/\d{2}/\d{4})"', text)
    if echoed is None:
        raise AcquisitionFailure("SCHEMA_INCOMPATIBLE", "scoreboard page did not echo its requested game date")
    echoed_date = datetime.strptime(echoed.group(1), "%m/%d/%Y").date().isoformat()
    if echoed_date != game_date:
        return {
            "date_observation_state": "SOURCE_SUBSTITUTED_A_DIFFERENT_DATE",
            "source_echoed_game_date": echoed_date,
            "parsed_card_count": 0,
            "cohort_rows_admitted": False,
        }
    card_count = len(parse_scoreboard_document(text, game_date=game_date))
    return {
        "date_observation_state": (
            "OFFICIAL_CONTESTS_PRESENT" if card_count else "NO_OFFICIAL_CONTESTS_ON_THIS_DATE"
        ),
        "source_echoed_game_date": echoed_date,
        "parsed_card_count": card_count,
        "cohort_rows_admitted": True,
    }


def read_dotenv_value(path: Path, name: str) -> str | None:
    if not Path(path).is_file():
        return None
    resolved: str | None = None
    with Path(path).open(encoding="utf-8-sig") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() != name:
                continue
            candidate = value.strip()
            if len(candidate) >= 2 and candidate[0] == candidate[-1] and candidate[0] in {"'", '"'}:
                candidate = candidate[1:-1]
            resolved = candidate or None
    return resolved


@dataclass(frozen=True)
class DirectTransport:
    timeout_seconds: float = 60.0

    def __call__(self, request: AcquisitionRequest) -> FetchResponse:
        wire = urllib.request.Request(
            request.source_uri,
            headers={"Accept": "text/html,application/xhtml+xml", "User-Agent": USER_AGENT},
            method="GET",
        )
        try:
            with urllib.request.urlopen(wire, timeout=self.timeout_seconds) as response:
                return FetchResponse(body=response.read(), status_code=int(response.status))
        except urllib.error.HTTPError as error:
            return FetchResponse(body=error.read(), status_code=int(error.code))
        except TimeoutError as error:
            raise AcquisitionFailure("TIMEOUT", "direct scoreboard request timed out") from error
        except urllib.error.URLError as error:
            raise AcquisitionFailure("CONNECTION_ERROR", "direct scoreboard connection failed") from error


@dataclass(frozen=True)
class ScrapflyTransport:
    """Route the official page through a rendering proxy.

    The official host serves an Akamai interstitial that only resolves after
    client-side script execution, so a rendering route is required rather than
    preferred. Credentials are read per run and never persisted.
    """

    access_token: str = field(repr=False)
    rendering_wait_milliseconds: int = 6000
    timeout_seconds: float = 240.0

    def __call__(self, request: AcquisitionRequest) -> FetchResponse:
        wire = "https://api.scrapfly.io/scrape?" + urllib.parse.urlencode(
            {
                "key": self.access_token,
                "url": request.source_uri,
                "asp": "true",
                "country": "us",
                "render_js": "true",
                "rendering_wait": str(self.rendering_wait_milliseconds),
            }
        )
        try:
            with urllib.request.urlopen(
                urllib.request.Request(wire, headers={"Accept": "application/json"}),
                timeout=self.timeout_seconds,
            ) as response:
                envelope = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            return FetchResponse(body=b"", status_code=int(error.code))
        except TimeoutError as error:
            raise AcquisitionFailure("TIMEOUT", "rendering route timed out") from error
        except (urllib.error.URLError, json.JSONDecodeError, UnicodeDecodeError) as error:
            raise AcquisitionFailure("CONNECTION_ERROR", "rendering route failed") from error
        result = envelope.get("result") or {}
        content = result.get("content")
        if not isinstance(content, str):
            raise AcquisitionFailure("SCHEMA_INCOMPATIBLE", "rendering route returned no text content")
        return FetchResponse(body=content.encode("utf-8"), status_code=int(result.get("status_code", 0)))


def build_routes(env_file: Path) -> list[tuple[str, Any]]:
    routes: list[tuple[str, Any]] = [("direct_http", DirectTransport())]
    credential = read_dotenv_value(env_file, "SCRAPFLY_API_TOKEN")
    if credential:
        routes.append(("scrapfly_rendering", ScrapflyTransport(credential)))
    return routes


def capture_one(
    *,
    store: RawSnapshotStore,
    contract: Mapping[str, Any],
    game_date: str,
    routes: list[tuple[str, Any]],
    retrieved_at: datetime,
    maximum_attempts: int,
) -> dict[str, Any]:
    source = contract["official_source"]
    request = AcquisitionRequest(
        source_id=source["source_id"],
        dataset=source["dataset"],
        source_uri=scoreboard_uri(contract, game_date),
        identity_components={
            "contract_id": CONTRACT_ID,
            "decision_unit": contract["decision_unit"],
            "game_date": game_date,
            "division": source["division"],
            "sport_code": source["sport_code"],
        },
        extension=".html",
    )
    cached = store.lookup_request(request.identity_sha256)
    if cached is not None:
        path = store.root / cached.relative_path
        profile = validate_scoreboard(path.read_bytes(), contract=contract, game_date=game_date)
        return {
            "game_date": game_date,
            "state": "CAPTURED",
            "route_id": "IMMUTABLE_REQUEST_CACHE",
            "source_uri": request.source_uri,
            "request_identity_sha256": request.identity_sha256,
            "raw_relative_path": cached.relative_path,
            "raw_sha256": cached.raw_sha256,
            "raw_bytes": path.stat().st_size,
            "retrieved_at_utc": iso_utc(cached.retrieved_at),
            **profile,
            "attempts": [{"route_id": "IMMUTABLE_REQUEST_CACHE", "attempt": 0, "condition": "CACHE_HIT"}],
        }
    attempts: list[dict[str, Any]] = []
    for route_id, transport in routes:
        for attempt in range(1, maximum_attempts + 1):
            try:
                response = transport(request)
                status = int(response.status_code)
                if not 200 <= status < 300:
                    condition = "RATE_LIMITED" if status == 429 else f"HTTP_{status}"
                    raise AcquisitionFailure(condition, f"route returned HTTP {status}", status_code=status)
                profile = validate_scoreboard(response.body, contract=contract, game_date=game_date)
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
                row_count=int(profile["parsed_card_count"]),
                schema_fields=("ncaa_contest_id", "game_date", "published_clock", "participants"),
                metadata={
                    "contract_id": CONTRACT_ID,
                    "decision_unit": contract["decision_unit"],
                    "jira_key": contract["jira_key"],
                    "lane": contract["lane"],
                    "request_identity_sha256": request.identity_sha256,
                    "selected_route_id": route_id,
                    "attempts": attempts,
                    "outcome_fields_extracted": False,
                },
            )
            store.bind_request(request.identity_sha256, snapshot)
            path = store.root / snapshot.relative_path
            return {
                "game_date": game_date,
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
        "game_date": game_date,
        "state": "TECHNICALLY_UNAVAILABLE",
        "source_uri": request.source_uri,
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
    result.add_argument("--game-date", action="append", default=[])
    result.add_argument("--maximum-attempts", type=int, default=2)
    return result


def main() -> int:
    args = parser().parse_args()
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    contract = load_contract(repo_root)
    declared = list(contract["schedule_window"]["game_dates"])
    unknown = sorted(set(args.game_date) - set(declared))
    if unknown:
        raise ValueError(f"game dates outside the declared window: {unknown}")
    selected = [date for date in declared if not args.game_date or date in args.game_date]
    retrieved_at = parse_utc(args.issued_at_utc)
    store = RawSnapshotStore(data_root)
    routes = build_routes(args.env_file.resolve())
    captures: list[dict[str, Any]] = []
    for game_date in selected:
        capture = capture_one(
            store=store,
            contract=contract,
            game_date=game_date,
            routes=routes,
            retrieved_at=retrieved_at,
            maximum_attempts=args.maximum_attempts,
        )
        captures.append(capture)
        print(
            json.dumps(
                {
                    "event": "PROSPECTIVE_2026_SCHEDULE_CAPTURE",
                    "game_date": game_date,
                    "state": capture["state"],
                    "route_id": capture.get("route_id"),
                    "date_observation_state": capture.get("date_observation_state"),
                    "parsed_card_count": capture.get("parsed_card_count"),
                },
                sort_keys=True,
            ),
            flush=True,
        )
    captured = [row for row in captures if row["state"] == "CAPTURED"]
    core = {
        "schema_version": "aggie.shadow.prospective_2026_schedule_capture.v1",
        "artifact_type": "PROSPECTIVE_2026_SCHEDULE_CAPTURE_MANIFEST",
        "contract_id": CONTRACT_ID,
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "lane": contract["lane"],
        "contract_sha256": sha256_file(repo_root / "configs/prospective_2026_shadow_cohort_contract.json"),
        "requested_game_dates": selected,
        "captures": sorted(captures, key=lambda row: row["game_date"]),
        "captured_count": len(captured),
        "technical_failure_count": len(captures) - len(captured),
        "total_raw_bytes": sum(int(row["raw_bytes"]) for row in captured),
        "date_observation_counts": {
            state: sum(1 for row in captured if row.get("date_observation_state") == state)
            for state in (
                "OFFICIAL_CONTESTS_PRESENT",
                "NO_OFFICIAL_CONTESTS_ON_THIS_DATE",
                "SOURCE_SUBSTITUTED_A_DIFFERENT_DATE",
            )
        },
        "outcome_fields_extracted": False,
    }
    identity = stable_hash(core)
    manifest = {**core, "capture_identity": identity, "issued_at_utc": iso_utc(retrieved_at)}
    path = (
        data_root
        / "manifests"
        / "shadow"
        / "prospective_2026_schedule_capture"
        / "sha256"
        / identity
        / "prospective_2026_schedule_capture_manifest.json"
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
                "credentials_logged_or_persisted": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if len(captured) == len(captures) else 2


if __name__ == "__main__":
    raise SystemExit(main())

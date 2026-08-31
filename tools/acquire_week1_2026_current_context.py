"""Acquire the timestamped Week 1 2026 current-context sources.

Two prospective domains are captured at execution time:

``rankings``
    the official NCAA ranking page for the declared poll, preserving the raw
    response, the page's own publication authority line, and the retrieval time;

``weather``
    the official public National Weather Service point, gridpoint and hourly
    forecast responses for each resolvable Week 1 home venue, preserving the
    office and gridpoint, the forecast issuance and generation times, the valid
    interval of every period, and the raw response digest.

Nothing here is a forecast of a contest outcome and no observed postgame value is
ever requested: the weather route asks only for forecast products issued before
the snapshot, and a later vintage is written as a new immutable capture rather
than as an overwrite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]

RANKING_SOURCE_ID = "SRC-NCAA-OFFICIAL-COM"
RANKING_DATASET = "ncaa_2026_football_rankings"
RANKING_MANIFEST_SLUG = "week1_2026_current_rankings"
RANKING_URI = "https://www.ncaa.com/rankings/football/fbs/associated-press"
RANKING_POLL_ID = "ASSOCIATED_PRESS_FBS_TOP_25"

WEATHER_SOURCE_ID = "SRC-NWS-OFFICIAL-API"
WEATHER_DATASET = "nws_week1_2026_venue_forecast"
WEATHER_MANIFEST_SLUG = "week1_2026_weather_vintage"
NWS_POINTS_URI = "https://api.weather.gov/points/{latitude:.4f},{longitude:.4f}"

USER_AGENT = "AggieAnalyticsEngine/1.0 (research use; repository KevinSGarrett/BatteredAggieSyndrome)"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(uri: str, *, accept: str) -> tuple[bytes | None, dict[str, Any]]:
    request = urllib.request.Request(
        uri, headers={"User-Agent": USER_AGENT, "Accept": accept}
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read(), {"condition": "SUCCESS", "status": response.status}
    except urllib.error.HTTPError as exc:
        return None, {"condition": f"HTTP_{exc.code}", "status": exc.code}
    except Exception as exc:  # noqa: BLE001 - any refusal is recorded verbatim
        return None, {"condition": f"ERROR_{type(exc).__name__}", "status": None}


def store(body: bytes, *, raw_dir: Path, data_root: Path, extension: str) -> dict[str, Any]:
    digest = hashlib.sha256(body).hexdigest()
    raw_dir.mkdir(parents=True, exist_ok=True)
    target = raw_dir / f"{digest}{extension}"
    if not target.exists():
        target.write_bytes(body)
    return {
        "raw_sha256": digest,
        "raw_bytes": len(body),
        "raw_relative_path": str(target.relative_to(data_root)).replace("\\", "/"),
    }


def write_manifest(data_root: Path, slug: str, name: str, manifest: dict[str, Any]) -> str:
    payload = json.dumps(manifest, indent=1, sort_keys=True).encode("utf-8")
    identity = hashlib.sha256(payload).hexdigest()
    manifest["capture_identity"] = identity
    target = data_root / "manifests" / "shadow" / slug / "sha256" / identity / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
    return identity


def acquire_rankings(data_root: Path) -> str:
    raw_dir = data_root / "raw" / RANKING_SOURCE_ID / RANKING_DATASET
    body, outcome = fetch(RANKING_URI, accept="text/html")
    record: dict[str, Any] = {
        "poll_id": RANKING_POLL_ID,
        "source_uri": RANKING_URI,
        "request_identity_sha256": hashlib.sha256(RANKING_URI.encode("utf-8")).hexdigest(),
        "retrieved_at_utc": utc_now(),
        "attempts": [{"attempt": 1, "route_id": "direct_http", **outcome}],
    }
    if body is None:
        record["state"] = "CAPTURE_FAILED"
    else:
        record.update(store(body, raw_dir=raw_dir, data_root=data_root, extension=".html"))
        record["state"] = "CAPTURED"
        record["route_id"] = "direct_http"
    manifest = {
        "artifact_type": "WEEK1_2026_CURRENT_RANKINGS_CAPTURE_MANIFEST",
        "issued_at_utc": utc_now(),
        "captures": [record],
        "captured_count": int(record["state"] == "CAPTURED"),
        "excluded_sources": [
            {
                "source_uri": "https://www.ncaa.com/rankings/football/fbs/college-football-playoff",
                "exclusion_reason": (
                    "PUBLICATION_AUTHORITY_PRECEDES_THE_2026_SEASON_AND_DERIVES_FROM_SEALED_RESULTS"
                ),
            }
        ],
    }
    return write_manifest(
        data_root,
        RANKING_MANIFEST_SLUG,
        "week1_2026_current_rankings_capture_manifest.json",
        manifest,
    )


def acquire_weather(data_root: Path, venues: Sequence[dict[str, Any]]) -> str:
    raw_dir = data_root / "raw" / WEATHER_SOURCE_ID / WEATHER_DATASET
    captures: list[dict[str, Any]] = []
    for venue in venues:
        point_uri = NWS_POINTS_URI.format(
            latitude=float(venue["latitude"]), longitude=float(venue["longitude"])
        )
        body, outcome = fetch(point_uri, accept="application/geo+json")
        record: dict[str, Any] = {
            "venue_key": venue["venue_key"],
            "canonical_team_id": venue["canonical_team_id"],
            "latitude": venue["latitude"],
            "longitude": venue["longitude"],
            "point_source_uri": point_uri,
            "retrieved_at_utc": utc_now(),
            "attempts": [{"stage": "points", "route_id": "direct_http", **outcome}],
        }
        if body is None:
            record["state"] = "POINT_UNRESOLVED"
            captures.append(record)
            continue
        record.update(
            {
                f"point_{key}": value
                for key, value in store(
                    body, raw_dir=raw_dir, data_root=data_root, extension=".json"
                ).items()
            }
        )
        point = json.loads(body.decode("utf-8"))["properties"]
        forecast_uri = point["forecastHourly"]
        record.update(
            {
                "grid_office": point["gridId"],
                "grid_x": point["gridX"],
                "grid_y": point["gridY"],
                "forecast_source_uri": forecast_uri,
            }
        )
        time.sleep(0.4)
        forecast_body, forecast_outcome = fetch(forecast_uri, accept="application/geo+json")
        record["attempts"].append(
            {"stage": "forecast_hourly", "route_id": "direct_http", **forecast_outcome}
        )
        if forecast_body is None:
            record["state"] = "FORECAST_UNAVAILABLE"
            captures.append(record)
            continue
        record.update(
            {
                f"forecast_{key}": value
                for key, value in store(
                    forecast_body, raw_dir=raw_dir, data_root=data_root, extension=".json"
                ).items()
            }
        )
        forecast = json.loads(forecast_body.decode("utf-8"))["properties"]
        record.update(
            {
                "forecast_update_time_utc": forecast.get("updateTime"),
                "forecast_generated_at_utc": forecast.get("generatedAt"),
                "forecast_valid_interval": forecast.get("validTimes"),
                "forecast_period_count": len(forecast.get("periods", [])),
                "state": "CAPTURED",
            }
        )
        captures.append(record)
        print(f"{venue['venue_key']}: {record['state']}")
        time.sleep(0.4)

    manifest = {
        "artifact_type": "WEEK1_2026_WEATHER_VINTAGE_CAPTURE_MANIFEST",
        "issued_at_utc": utc_now(),
        "provider": "NATIONAL_WEATHER_SERVICE_PUBLIC_API",
        "product": "HOURLY_FORECAST",
        "observed_weather_requested": False,
        "captures": captures,
        "captured_count": sum(1 for row in captures if row["state"] == "CAPTURED"),
        "failed_count": sum(1 for row in captures if row["state"] != "CAPTURED"),
    }
    return write_manifest(
        data_root,
        WEATHER_MANIFEST_SLUG,
        "week1_2026_weather_vintage_capture_manifest.json",
        manifest,
    )


def load_venues(repo_root: Path, data_root: Path, coordinate_source: Path) -> list[dict[str, Any]]:
    """Resolve one home venue coordinate per Week 1 contest that has a home site."""

    gate = json.loads(
        (repo_root / "artifacts/schedule/week1_2026_official_schedule_identity_gate.json").read_text(
            encoding="utf-8-sig"
        )
    )
    manifest = json.loads(
        (data_root / gate["manifest"]["relative_path"]).read_text(encoding="utf-8-sig")
    )
    contest_payload = next(
        payload for payload in manifest["payloads"] if payload["name"].startswith("week1_2026_contest")
    )
    contests = [
        json.loads(line)
        for line in (data_root / contest_payload["relative_path"])
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    coordinates = json.loads(coordinate_source.read_text(encoding="utf-8"))
    venues: dict[str, dict[str, Any]] = {}
    for contest in contests:
        if contest["site_state"] != "HOME_TEAM_SITE":
            continue
        home = contest["home_team"]
        team = home["canonical_team_id"]
        if not team or team not in coordinates:
            continue
        venues.setdefault(
            team,
            {
                "venue_key": team,
                "canonical_team_id": team,
                "latitude": coordinates[team]["latitude"],
                "longitude": coordinates[team]["longitude"],
            },
        )
    return [venues[key] for key in sorted(venues)]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("rankings", "weather"), required=True)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", ""))
    parser.add_argument("--venue-coordinates", default="")
    args = parser.parse_args(argv)
    if not args.data_root:
        print("AGGIE_ANALYTICS_DATA_ROOT is required", file=sys.stderr)
        return 2
    data_root = Path(args.data_root)
    if args.dataset == "rankings":
        identity = acquire_rankings(data_root)
    else:
        if not args.venue_coordinates:
            print("--venue-coordinates is required for the weather dataset", file=sys.stderr)
            return 2
        venues = load_venues(Path(args.repo_root), data_root, Path(args.venue_coordinates))
        print(f"resolvable home venues: {len(venues)}")
        identity = acquire_weather(data_root, venues)
    print("capture_identity:", identity)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

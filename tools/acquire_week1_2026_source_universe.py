"""Acquire the official 2026 Week 1 source universe and 2026-27 season authority.

Two datasets are captured from the official NCAA statistics site:

``schedule``
    one livestream scoreboard response per declared Week 1 date, which is the
    official Division I contest universe for that date;
``team-season-authority``
    the official institution lists for the Football Bowl Subdivision and the
    Football Championship Subdivision, then one list per conference, which is the
    2026-27 subdivision and conference authority.

The direct official route is attempted first. When the official host refuses the
direct request, the configured transport is used to reach the same official
uniform resource identifier; no unofficial schedule is ever substituted. Every
response is stored content addressed and every attempt is recorded, including its
refusal condition, so the capture ledger is reconstructable.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]

SOURCE_ID = "SRC-NCAA-OFFICIAL-STATS"
SCHEDULE_DATASET = "ncaa_week1_2026_schedule_scoreboard"
AUTHORITY_DATASET = "ncaa_2026_team_season_authority"
SCHEDULE_MANIFEST_SLUG = "week1_2026_source_universe"
AUTHORITY_MANIFEST_SLUG = "week1_2026_team_season_authority"

WEEK1_DATES = ("2026-09-03", "2026-09-04", "2026-09-05", "2026-09-06", "2026-09-07")
ACADEMIC_YEAR = "2027"
SEASON = 2026
DIVISIONS = (("11", "FBS"), ("12", "FCS"))

SCHEDULE_URI = (
    "https://stats.ncaa.org/contests/livestream_scoreboards"
    "?utf8=%E2%9C%93&sport_code=MFB&academic_year=2027&division=1&game_date={encoded_date}"
)
TEAM_LIST_URI = (
    "https://stats.ncaa.org/team/inst_team_list"
    "?academic_year={academic_year}&conf_id={conference_id}&division={division}&sport_code=MFB"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

CONFERENCE_MENU = re.compile(r'href="javascript:changeConference\((\d+)\);">\s*([^<]+?)\s*</a>')
TEAM_ANCHOR = re.compile(r'href="/teams/(\d+)"[^>]*>\s*([^<]+?)\s*</a>')


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_env(env_path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not env_path.is_file():
        return env
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def direct_fetch(uri: str) -> tuple[bytes | None, dict[str, Any]]:
    request = urllib.request.Request(uri, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return response.read(), {"route_id": "direct_http", "condition": "SUCCESS"}
    except urllib.error.HTTPError as exc:
        return None, {"route_id": "direct_http", "condition": f"HTTP_{exc.code}"}
    except Exception as exc:  # noqa: BLE001 - any refusal is recorded verbatim
        return None, {"route_id": "direct_http", "condition": f"ERROR_{type(exc).__name__}"}


def transport_fetch(uri: str, token: str) -> tuple[bytes | None, dict[str, Any]]:
    parameters = {
        "key": token,
        "url": uri,
        "render_js": "true",
        "asp": "true",
        "country": "us",
    }
    endpoint = "https://api.scrapfly.io/scrape?" + urllib.parse.urlencode(parameters)
    request = urllib.request.Request(endpoint, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            payload = json.loads(response.read().decode("utf-8", "replace"))
    except Exception as exc:  # noqa: BLE001 - any refusal is recorded verbatim
        return None, {
            "route_id": "scrapfly_rendering",
            "condition": f"ERROR_{type(exc).__name__}",
        }
    result = payload.get("result", {})
    if not result.get("content"):
        return None, {
            "route_id": "scrapfly_rendering",
            "condition": f"NO_CONTENT_UPSTREAM_{result.get('status_code')}",
        }
    return result["content"].encode("utf-8"), {
        "route_id": "scrapfly_rendering",
        "condition": "SUCCESS",
        "upstream_status": result.get("status_code"),
    }


def capture(uri: str, *, raw_dir: Path, data_root: Path, token: str) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    body, outcome = direct_fetch(uri)
    attempts.append({"attempt": 1, **outcome})
    if body is None and token:
        time.sleep(1)
        body, outcome = transport_fetch(uri, token)
        attempts.append({"attempt": 1, **outcome})
    record: dict[str, Any] = {
        "source_uri": uri,
        "request_identity_sha256": hashlib.sha256(uri.encode("utf-8")).hexdigest(),
        "retrieved_at_utc": utc_now(),
        "attempts": attempts,
    }
    if body is None:
        record["state"] = "CAPTURE_FAILED"
        record["raw_sha256"] = None
        return record
    digest = hashlib.sha256(body).hexdigest()
    raw_dir.mkdir(parents=True, exist_ok=True)
    target = raw_dir / f"{digest}.html"
    if not target.exists():
        target.write_bytes(body)
    record.update(
        {
            "state": "CAPTURED",
            "raw_sha256": digest,
            "raw_bytes": len(body),
            "route_id": attempts[-1]["route_id"],
            "raw_relative_path": str(target.relative_to(data_root)).replace("\\", "/"),
        }
    )
    record["_document"] = body.decode("utf-8", "replace")
    return record


def write_manifest(data_root: Path, slug: str, name: str, manifest: dict[str, Any]) -> str:
    payload = json.dumps(manifest, indent=1, sort_keys=True).encode("utf-8")
    identity = hashlib.sha256(payload).hexdigest()
    manifest["capture_identity"] = identity
    target = data_root / "manifests" / "shadow" / slug / "sha256" / identity / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
    return identity


def acquire_schedule(data_root: Path, token: str) -> str:
    raw_dir = data_root / "raw" / SOURCE_ID / SCHEDULE_DATASET
    captures: list[dict[str, Any]] = []
    for iso_date in WEEK1_DATES:
        year, month, day = iso_date.split("-")
        uri = SCHEDULE_URI.format(encoded_date=f"{month}%2F{day}%2F{year}")
        record = capture(uri, raw_dir=raw_dir, data_root=data_root, token=token)
        record.pop("_document", None)
        record["requested_game_date"] = iso_date
        captures.append(record)
        print(f"{iso_date}: {record['state']} {record.get('raw_sha256')}")
    manifest = {
        "artifact_type": "WEEK1_2026_SOURCE_UNIVERSE_CAPTURE_MANIFEST",
        "issued_at_utc": utc_now(),
        "requested_dates": list(WEEK1_DATES),
        "captured_count": sum(1 for row in captures if row["state"] == "CAPTURED"),
        "failed_count": sum(1 for row in captures if row["state"] != "CAPTURED"),
        "captures": captures,
    }
    return write_manifest(
        data_root,
        SCHEDULE_MANIFEST_SLUG,
        "week1_2026_source_universe_capture_manifest.json",
        manifest,
    )


def teams_in(document: str) -> dict[str, str]:
    teams: dict[str, str] = {}
    for team_id, name in TEAM_ANCHOR.findall(document):
        teams.setdefault(team_id, html.unescape(name).strip())
    return teams


def acquire_team_season_authority(data_root: Path, token: str) -> str:
    raw_dir = data_root / "raw" / SOURCE_ID / AUTHORITY_DATASET
    captures: list[dict[str, Any]] = []
    memberships: list[dict[str, Any]] = []

    for division, subdivision in DIVISIONS:
        uri = TEAM_LIST_URI.format(
            academic_year=ACADEMIC_YEAR, conference_id="-1", division=division
        )
        record = capture(uri, raw_dir=raw_dir, data_root=data_root, token=token)
        document = record.pop("_document", "")
        record.update(
            {"division_code": division, "subdivision": subdivision, "conference_id": None}
        )
        captures.append(record)
        if record["state"] != "CAPTURED":
            raise RuntimeError(f"official {subdivision} institution list could not be captured")
        division_teams = teams_in(document)
        seen: set[str] = set()
        for conference_id, conference_name in CONFERENCE_MENU.findall(document):
            if conference_id in seen:
                continue
            seen.add(conference_id)
            conference_uri = TEAM_LIST_URI.format(
                academic_year=ACADEMIC_YEAR, conference_id=conference_id, division=division
            )
            conference_record = capture(
                conference_uri, raw_dir=raw_dir, data_root=data_root, token=token
            )
            conference_document = conference_record.pop("_document", "")
            conference_record.update(
                {
                    "division_code": division,
                    "subdivision": subdivision,
                    "conference_id": conference_id,
                    "conference_name": html.unescape(conference_name).strip(),
                }
            )
            captures.append(conference_record)
            if conference_record["state"] != "CAPTURED":
                raise RuntimeError(f"official conference list {conference_id} was not captured")
            for team_id, team_name in teams_in(conference_document).items():
                if team_id not in division_teams:
                    continue
                memberships.append(
                    {
                        "season": SEASON,
                        "academic_year": ACADEMIC_YEAR,
                        "source_team_id": team_id,
                        "source_team_name": team_name,
                        "subdivision": subdivision,
                        "division_code": division,
                        "conference_id": conference_id,
                        "conference_name": conference_record["conference_name"],
                        "source_capture_sha256": conference_record["raw_sha256"],
                        "retrieved_at_utc": conference_record["retrieved_at_utc"],
                        "source_uri": conference_uri,
                    }
                )
            print(f"  {conference_record['conference_name']}: {len(memberships)} cumulative")

    memberships.sort(key=lambda row: (row["subdivision"], row["source_team_id"]))
    manifest = {
        "artifact_type": "WEEK1_2026_TEAM_SEASON_AUTHORITY_CAPTURE_MANIFEST",
        "season": SEASON,
        "academic_year": ACADEMIC_YEAR,
        "issued_at_utc": utc_now(),
        "captures": captures,
        "captured_count": sum(1 for row in captures if row["state"] == "CAPTURED"),
        "failed_count": sum(1 for row in captures if row["state"] != "CAPTURED"),
        "memberships": memberships,
        "membership_count": len(memberships),
    }
    return write_manifest(
        data_root,
        AUTHORITY_MANIFEST_SLUG,
        "week1_2026_team_season_authority_capture_manifest.json",
        manifest,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("schedule", "team-season-authority"), required=True)
    parser.add_argument("--data-root", default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", ""))
    parser.add_argument("--env-file", default=str(REPO_ROOT / ".env"))
    args = parser.parse_args(argv)
    if not args.data_root:
        print("AGGIE_ANALYTICS_DATA_ROOT is required", file=sys.stderr)
        return 2
    data_root = Path(args.data_root)
    token = load_env(Path(args.env_file)).get("SCRAPFLY_API_TOKEN", "")
    if args.dataset == "schedule":
        identity = acquire_schedule(data_root, token)
    else:
        identity = acquire_team_season_authority(data_root, token)
    print("capture_identity:", identity)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

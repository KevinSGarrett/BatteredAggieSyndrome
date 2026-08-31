"""Acquire the current authority evidence Cycle #23 left unresolved for Week 1 2026.

Three datasets are captured, each from an official publisher, because Cycle #23
left three distinct authority gaps:

``kickoff-authority``
    the official NCAA.com Week 1 scoreboard, whose embedded contest graph
    publishes an absolute kickoff instant per contest together with the current
    Associated Press rank bound to an official team slug.  The statistics site
    publishes only a bare local clock with no declared zone, which is why every
    Cycle #23 contest carries an unconfirmed conservative lower bound.

``entity-authority``
    one official organization history page per unresolved Week 1 participant.
    The organization identifiers come from the official organization directory
    already captured under the entity identity benchmark, so no name-only join
    and no similarity threshold is involved.

``venue-authority``
    the official Texas A&M athletics season schedule, which is the institutional
    authority for the focus contest's venue and published kickoff clock.

The direct official route is attempted first.  When the official host refuses the
direct request, the configured transport reaches the same official uniform
resource identifier; no unofficial source is ever substituted.  Every response is
stored content addressed and every attempt is recorded with its refusal
condition, so the capture ledger is reconstructable.

Collegiate Football Data is deliberately not called here.  Its monthly quota is
already exhausted and the refusal receipt is preserved at
``artifacts/shadow/week_zero_2026_cfbd_route_probe.json``; re-attempting it would
burn calls without producing evidence.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]

NCAA_COM_SOURCE_ID = "SRC-NCAA-OFFICIAL-COM"
NCAA_STATS_SOURCE_ID = "SRC-NCAA-OFFICIAL-STATS"
INSTITUTIONAL_SOURCE_ID = "SRC-TAMU-OFFICIAL-ATHLETICS"

KICKOFF_DATASET = "ncaa_com_week1_2026_scoreboard_contest_graph"
ENTITY_DATASET = "ncaa_official_team_history"
VENUE_DATASET = "tamu_official_2026_football_schedule"

KICKOFF_MANIFEST_SLUG = "week1_2026_kickoff_authority"
ENTITY_MANIFEST_SLUG = "week1_2026_entity_authority"
VENUE_MANIFEST_SLUG = "week1_2026_venue_authority"

SEASON = 2026
WEEK_INDEX = "01"
KICKOFF_URI = (
    f"https://www.ncaa.com/scoreboard/football/fbs/{SEASON}/{WEEK_INDEX}/all-conf"
)
TEAM_HISTORY_URI = "https://stats.ncaa.org/teams/history/MFB/{organization_id}"
VENUE_URI = f"https://12thman.com/sports/football/schedule/{SEASON}"

# Organization identifiers read from the official organization directory captured
# by the entity identity benchmark.  Each is an exact official label match, never
# a similarity match.
UNRESOLVED_ORGANIZATIONS = (
    {
        "source_team_id": "622349",
        "source_display_name": "Mercyhurst",
        "official_organization_id": 408,
    },
    {
        "source_team_id": "622350",
        "source_display_name": "West Ga.",
        "official_organization_id": 766,
    },
    {
        "source_team_id": "622352",
        "source_display_name": "LIU",
        "official_organization_id": 361,
    },
    {
        "source_team_id": "622358",
        "source_display_name": "Alcorn",
        "official_organization_id": 17,
    },
    {
        "source_team_id": "622407",
        "source_display_name": "Mississippi Val.",
        "official_organization_id": 432,
    },
    {
        "source_team_id": "622417",
        "source_display_name": "N.C. A&T",
        "official_organization_id": 488,
    },
    {
        "source_team_id": "622443",
        "source_display_name": "Southeastern La.",
        "official_organization_id": 655,
    },
    {
        "source_team_id": "622444",
        "source_display_name": "UTRGV",
        "official_organization_id": 536,
    },
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_env(env_path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not env_path.is_file():
        return env
    for line in env_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def _decode(raw: bytes, content_encoding: str) -> bytes:
    encoding = (content_encoding or "").lower()
    if encoding == "gzip":
        return gzip.decompress(raw)
    if encoding == "deflate":
        return zlib.decompress(raw, -zlib.MAX_WBITS)
    return raw


def direct_fetch(uri: str) -> tuple[bytes | None, dict[str, Any]]:
    request = urllib.request.Request(
        uri,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Accept-Encoding": "gzip, deflate",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = _decode(
                response.read(), response.headers.get("Content-Encoding", "")
            )
            return body, {"route_id": "direct_http", "condition": "SUCCESS"}
    except urllib.error.HTTPError as exc:
        return None, {"route_id": "direct_http", "condition": f"HTTP_{exc.code}"}
    except Exception as exc:  # noqa: BLE001 - any refusal is recorded verbatim
        return None, {
            "route_id": "direct_http",
            "condition": f"ERROR_{type(exc).__name__}",
        }


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


def capture(
    uri: str,
    *,
    raw_dir: Path,
    data_root: Path,
    token: str,
    force_transport: bool = False,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    body: bytes | None = None
    if force_transport:
        attempts.append(
            {
                "attempt": 1,
                "route_id": "direct_http",
                "condition": "SKIPPED_OFFICIAL_HOST_REFUSES_DIRECT",
            }
        )
    else:
        body, outcome = direct_fetch(uri)
        attempts.append({"attempt": 1, **outcome})
    if body is None and token:
        time.sleep(1)
        body, outcome = transport_fetch(uri, token)
        attempts.append({"attempt": len(attempts) + 1, **outcome})
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
    return record


def write_manifest(
    data_root: Path, slug: str, name: str, manifest: dict[str, Any]
) -> str:
    payload = json.dumps(manifest, indent=1, sort_keys=True).encode("utf-8")
    identity = hashlib.sha256(payload).hexdigest()
    manifest["capture_identity"] = identity
    target = data_root / "manifests" / "shadow" / slug / "sha256" / identity / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
    return identity


def acquire_kickoff_authority(data_root: Path, token: str) -> str:
    raw_dir = data_root / "raw" / NCAA_COM_SOURCE_ID / KICKOFF_DATASET
    record = capture(KICKOFF_URI, raw_dir=raw_dir, data_root=data_root, token=token)
    print(f"kickoff authority: {record['state']} {record.get('raw_sha256')}")
    manifest = {
        "artifact_type": "WEEK1_2026_KICKOFF_AUTHORITY_CAPTURE_MANIFEST",
        "season": SEASON,
        "week_index": WEEK_INDEX,
        "issued_at_utc": utc_now(),
        "authority_semantics": (
            "The official scoreboard contest graph publishes an absolute kickoff instant "
            "per contest and the current Associated Press rank bound to an official team "
            "slug, which the statistics site does not publish."
        ),
        "captures": [record],
        "captured_count": 1 if record["state"] == "CAPTURED" else 0,
        "failed_count": 0 if record["state"] == "CAPTURED" else 1,
    }
    return write_manifest(
        data_root,
        KICKOFF_MANIFEST_SLUG,
        "week1_2026_kickoff_authority_capture_manifest.json",
        manifest,
    )


def acquire_entity_authority(data_root: Path, token: str) -> str:
    raw_dir = data_root / "raw" / NCAA_STATS_SOURCE_ID / ENTITY_DATASET
    captures: list[dict[str, Any]] = []
    for organization in UNRESOLVED_ORGANIZATIONS:
        uri = TEAM_HISTORY_URI.format(
            organization_id=organization["official_organization_id"]
        )
        record = capture(
            uri, raw_dir=raw_dir, data_root=data_root, token=token, force_transport=True
        )
        record.update(organization)
        captures.append(record)
        print(
            f"  {organization['source_display_name']} "
            f"(org {organization['official_organization_id']}): {record['state']}"
        )
    manifest = {
        "artifact_type": "WEEK1_2026_ENTITY_AUTHORITY_CAPTURE_MANIFEST",
        "season": SEASON,
        "issued_at_utc": utc_now(),
        "organization_identifier_provenance": (
            "Exact official label match in the official organization directory captured by "
            "the national entity identity benchmark; no similarity threshold is involved."
        ),
        "captures": captures,
        "captured_count": sum(1 for row in captures if row["state"] == "CAPTURED"),
        "failed_count": sum(1 for row in captures if row["state"] != "CAPTURED"),
    }
    return write_manifest(
        data_root,
        ENTITY_MANIFEST_SLUG,
        "week1_2026_entity_authority_capture_manifest.json",
        manifest,
    )


def acquire_venue_authority(data_root: Path, token: str) -> str:
    raw_dir = data_root / "raw" / INSTITUTIONAL_SOURCE_ID / VENUE_DATASET
    record = capture(VENUE_URI, raw_dir=raw_dir, data_root=data_root, token=token)
    print(f"venue authority: {record['state']} {record.get('raw_sha256')}")
    manifest = {
        "artifact_type": "WEEK1_2026_VENUE_AUTHORITY_CAPTURE_MANIFEST",
        "season": SEASON,
        "issued_at_utc": utc_now(),
        "authority_semantics": (
            "Official institutional season schedule; the institution is the venue authority "
            "for its own home contests.  This capture covers the focus contest only and does "
            "not license a venue for any other contest."
        ),
        "captures": [record],
        "captured_count": 1 if record["state"] == "CAPTURED" else 0,
        "failed_count": 0 if record["state"] == "CAPTURED" else 1,
    }
    return write_manifest(
        data_root,
        VENUE_MANIFEST_SLUG,
        "week1_2026_venue_authority_capture_manifest.json",
        manifest,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        choices=("kickoff-authority", "entity-authority", "venue-authority", "all"),
        required=True,
    )
    parser.add_argument(
        "--data-root", default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", "")
    )
    parser.add_argument("--env-file", default=str(REPO_ROOT / ".env"))
    args = parser.parse_args(argv)
    if not args.data_root:
        print("AGGIE_ANALYTICS_DATA_ROOT is required", file=sys.stderr)
        return 2
    data_root = Path(args.data_root)
    token = load_env(Path(args.env_file)).get("SCRAPFLY_API_TOKEN", "")
    print(f"transport credential present: {bool(token)} length: {len(token)}")

    selected = (
        ("kickoff-authority", "entity-authority", "venue-authority")
        if args.dataset == "all"
        else (args.dataset,)
    )
    identities: dict[str, str] = {}
    for dataset in selected:
        if dataset == "kickoff-authority":
            identities[dataset] = acquire_kickoff_authority(data_root, token)
        elif dataset == "entity-authority":
            identities[dataset] = acquire_entity_authority(data_root, token)
        else:
            identities[dataset] = acquire_venue_authority(data_root, token)
    print(json.dumps({"capture_identities": identities}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Acquire official Week 1 schedule/final pages as atomic SOURCE_ACQUISITION_RECEIPTs.

Direct official HTTP is attempted first. Scrapfly is labeled transport only.
Failures are preserved; local files are never admitted as newly acquired.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle28.atomic_receipt import (
    SOURCE_ACQUISITION_RECEIPT,
    write_atomic_source_acquisition,
    write_acquisition_failure,
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

TARGETS = (
    {
        "target_id": "washington_athletics_schedule",
        "ncaa_contest_id": "6618941",
        "source_uri": "https://gohuskies.com/sports/football/schedule",
        "purpose": "official_institutional_kickoff",
    },
    {
        "target_id": "wisconsin_athletics_schedule",
        "ncaa_contest_id": "6602874",
        "source_uri": "https://uwbadgers.com/sports/football/schedule",
        "purpose": "official_institutional_kickoff",
    },
    {
        "target_id": "olemiss_athletics_schedule",
        "ncaa_contest_id": "6620581",
        "source_uri": "https://olemisssports.com/sports/football/schedule",
        "purpose": "official_institutional_kickoff",
    },
    {
        "target_id": "fsu_athletics_schedule",
        "ncaa_contest_id": "6594400",
        "source_uri": "https://seminoles.com/sports/football/schedule",
        "purpose": "official_institutional_kickoff",
    },
    {
        "target_id": "ncaa_scoreboard_2026_09_03",
        "ncaa_contest_id": None,
        "source_uri": (
            "https://stats.ncaa.org/contests/livestream_scoreboards"
            "?utf8=%E2%9C%93&sport_code=MFB&academic_year=2027&division=1"
            "&game_date=09%2F03%2F2026"
        ),
        "purpose": "official_ncaa_scoreboard",
    },
    {
        "target_id": "ncaa_scoreboard_2026_09_04",
        "ncaa_contest_id": None,
        "source_uri": (
            "https://stats.ncaa.org/contests/livestream_scoreboards"
            "?utf8=%E2%9C%93&sport_code=MFB&academic_year=2027&division=1"
            "&game_date=09%2F04%2F2026"
        ),
        "purpose": "official_ncaa_scoreboard",
    },
    {
        "target_id": "ncaa_scoreboard_2026_09_05",
        "ncaa_contest_id": None,
        "source_uri": (
            "https://stats.ncaa.org/contests/livestream_scoreboards"
            "?utf8=%E2%9C%93&sport_code=MFB&academic_year=2027&division=1"
            "&game_date=09%2F05%2F2026"
        ),
        "purpose": "official_ncaa_scoreboard",
    },
    {
        "target_id": "ncaa_scoreboard_2026_09_06",
        "ncaa_contest_id": None,
        "source_uri": (
            "https://stats.ncaa.org/contests/livestream_scoreboards"
            "?utf8=%E2%9C%93&sport_code=MFB&academic_year=2027&division=1"
            "&game_date=09%2F06%2F2026"
        ),
        "purpose": "official_ncaa_scoreboard",
    },
    {
        "target_id": "ncaa_scoreboard_2026_09_07",
        "ncaa_contest_id": None,
        "source_uri": (
            "https://stats.ncaa.org/contests/livestream_scoreboards"
            "?utf8=%E2%9C%93&sport_code=MFB&academic_year=2027&division=1"
            "&game_date=09%2F07%2F2026"
        ),
        "purpose": "official_ncaa_scoreboard",
    },
    {
        "target_id": "ncaa_contest_6607349",
        "ncaa_contest_id": "6607349",
        "source_uri": "https://stats.ncaa.org/contests/6607349/box_score",
        "purpose": "official_ncaa_box_or_status",
    },
    {
        "target_id": "ncaa_contest_6618941",
        "ncaa_contest_id": "6618941",
        "source_uri": "https://stats.ncaa.org/contests/6618941/box_score",
        "purpose": "official_ncaa_box_or_status",
    },
    {
        "target_id": "ncaa_contest_6602874",
        "ncaa_contest_id": "6602874",
        "source_uri": "https://stats.ncaa.org/contests/6602874/box_score",
        "purpose": "official_ncaa_box_or_status",
    },
    {
        "target_id": "ncaa_contest_6620581",
        "ncaa_contest_id": "6620581",
        "source_uri": "https://stats.ncaa.org/contests/6620581/box_score",
        "purpose": "official_ncaa_box_or_status",
    },
    {
        "target_id": "ncaa_contest_6594400",
        "ncaa_contest_id": "6594400",
        "source_uri": "https://stats.ncaa.org/contests/6594400/box_score",
        "purpose": "official_ncaa_box_or_status",
    },
    {
        "target_id": "tamu_athletics_schedule",
        "ncaa_contest_id": None,
        "source_uri": "https://12thman.com/sports/football/schedule",
        "purpose": "a_and_m_official_cross_check",
    },
    {
        "target_id": "missouri_state_athletics_schedule",
        "ncaa_contest_id": None,
        "source_uri": "https://missouristatebears.com/sports/football/schedule",
        "purpose": "a_and_m_official_cross_check",
    },
)


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
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def direct_fetch(uri: str) -> tuple[bytes | None, dict[str, Any]]:
    request = urllib.request.Request(uri, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return response.read(), {
                "route_id": "direct_http",
                "network_response_status": int(response.status),
                "condition": "SUCCESS",
            }
    except urllib.error.HTTPError as exc:
        body = exc.read() if exc.fp else b""
        return (body or None), {
            "route_id": "direct_http",
            "network_response_status": int(exc.code),
            "condition": f"HTTP_{exc.code}",
        }
    except Exception as exc:  # noqa: BLE001
        return None, {
            "route_id": "direct_http",
            "network_response_status": 0,
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
    except Exception as exc:  # noqa: BLE001
        return None, {
            "route_id": "scrapfly_rendering",
            "network_response_status": 0,
            "condition": f"ERROR_{type(exc).__name__}",
            "transport_only": True,
        }
    result = payload.get("result", {})
    status = int(result.get("status_code") or 0)
    content = result.get("content")
    if not content:
        return None, {
            "route_id": "scrapfly_rendering",
            "network_response_status": status,
            "condition": f"NO_CONTENT_UPSTREAM_{status}",
            "transport_only": True,
        }
    body = content.encode("utf-8") if isinstance(content, str) else content
    return body, {
        "route_id": "scrapfly_rendering",
        "network_response_status": status or 200,
        "condition": "SUCCESS",
        "transport_only": True,
        "transport_is_not_result_authority": True,
    }


def acquire_one(target: dict[str, Any], *, data_root: Path, token: str) -> dict[str, Any]:
    started = utc_now()
    uri = str(target["source_uri"])
    request_id = hashlib.sha256(
        f"{uri}|{started}|{os.getpid()}".encode("utf-8")
    ).hexdigest()
    body, outcome = direct_fetch(uri)
    attempts = [{"attempt": 1, **outcome}]
    if (body is None or outcome.get("condition") != "SUCCESS") and token:
        time.sleep(0.5)
        body, outcome = transport_fetch(uri, token)
        attempts.append({"attempt": 2, **outcome})
    ended = utc_now()
    fields = {
        "receipt_kind": SOURCE_ACQUISITION_RECEIPT,
        "request_identity_sha256": request_id,
        "source_uri": uri,
        "route_id": outcome.get("route_id") or "direct_http",
        "network_response_status": outcome.get("network_response_status") or 0,
        "acquisition_started_at_utc": started,
        "acquisition_ended_at_utc": ended,
        "trusted_clock_retrieval_utc": ended,
        "process_identity": f"acquire_cycle28_official_atomic.py:{os.getpid()}",
        "target_id": target["target_id"],
        "ncaa_contest_id": target.get("ncaa_contest_id"),
        "purpose": target["purpose"],
        "attempts": attempts,
        "transport_is_not_result_authority": bool(outcome.get("transport_only")),
    }
    rel_raw = f"raw/CYCLE28/{target['target_id']}"
    rel_receipt = f"receipts/CYCLE28/{target['target_id']}"
    if body is None or outcome.get("condition") != "SUCCESS":
        failed = write_acquisition_failure(
            data_root=data_root,
            receipt_relative_dir=rel_receipt,
            receipt_fields={**fields, "failure_condition": outcome.get("condition")},
        )
        return {"state": "SOURCE_ACQUISITION_FAILED", **failed, "attempts": attempts}
    written = write_atomic_source_acquisition(
        data_root=data_root,
        raw_relative_dir=rel_raw,
        receipt_relative_dir=rel_receipt,
        raw_bytes=body,
        receipt_fields=fields,
    )
    return {"state": "CAPTURED", **written, "attempts": attempts}


def already_captured(data_root: Path, target_id: str) -> bool:
    raw_dir = data_root / "raw" / "CYCLE28" / target_id
    return raw_dir.is_dir() and any(raw_dir.glob("*.html"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(r"C:\BatteredAggieSyndrome.data"),
    )
    parser.add_argument(
        "--env-path",
        type=Path,
        default=Path(r"C:\BatteredAggieSyndrome\.env"),
    )
    parser.add_argument(
        "--skip-captured",
        action="store_true",
        help="Do not re-fetch targets that already have raw HTML.",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Acquire only these target_id values (repeatable).",
    )
    args = parser.parse_args()
    env = load_env(args.env_path)
    token = (
        env.get("SCRAPFLY_API_TOKEN")
        or env.get("SCRAPFLY_API_KEY")
        or os.environ.get("SCRAPFLY_API_TOKEN")
        or os.environ.get("SCRAPFLY_API_KEY")
        or ""
    )
    records = []
    out = (
        args.data_root
        / "ops"
        / "cycle28"
        / "outputs"
        / "CYCLE28_OFFICIAL_ATOMIC_ACQUISITION_LEDGER.json"
    )
    selected = [target for target in TARGETS if not args.only or target["target_id"] in args.only]
    for target in selected:
        if args.skip_captured and already_captured(args.data_root, str(target["target_id"])):
            html = next((args.data_root / "raw" / "CYCLE28" / str(target["target_id"])).glob("*.html"))
            records.append(
                {
                    "target_id": target["target_id"],
                    "ncaa_contest_id": target.get("ncaa_contest_id"),
                    "source_uri": target["source_uri"],
                    "state": "CAPTURED",
                    "raw_sha256": html.stem,
                    "receipt_sha256": None,
                    "route_id": "already_captured_not_refetched",
                }
            )
            print(f"{target['target_id']}: SKIP_CAPTURED")
            continue
        record = acquire_one(target, data_root=args.data_root, token=token)
        records.append(
            {
                "target_id": target["target_id"],
                "ncaa_contest_id": target.get("ncaa_contest_id"),
                "source_uri": target["source_uri"],
                "state": record["state"],
                "raw_sha256": record.get("raw_sha256"),
                "receipt_sha256": record.get("receipt_sha256"),
                "route_id": record.get("route_id")
                or (record.get("attempts") or [{}])[-1].get("route_id"),
            }
        )
        print(f"{target['target_id']}: {record['state']}")
    by_id = {row["target_id"]: row for row in records}
    if out.is_file() and args.only:
        previous = json.loads(out.read_text(encoding="utf-8"))
        merged = {row["target_id"]: row for row in previous.get("records") or []}
        merged.update(by_id)
        records = list(merged.values())
    ledger = {
        "artifact_type": "CYCLE28_OFFICIAL_ATOMIC_ACQUISITION_LEDGER",
        "issued_at_utc": utc_now(),
        "records": records,
        "captured_count": sum(1 for row in records if row["state"] == "CAPTURED"),
        "failed_count": sum(1 for row in records if row["state"] != "CAPTURED"),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ledger, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"captured": ledger["captured_count"], "failed": ledger["failed_count"]}))
    return 0 if ledger["captured_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Cache-first NCAA.com FCS scoreboards for Week 2 closeout.

Does not re-arm TAMU-ASU, invent finals, or install a scheduler.
Declared ceiling: 8 live requests. Cache hits preserve original clocks.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aggie_analytics.cycle30.acquisition import parse_ncaa_com_scoreboard_contests
from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_json
from aggie_analytics.cycle33.acquisition_receipts import cache_hit_from_path
from aggie_analytics.cycle33.week2 import (
    cutoffs_from_kickoff_epoch,
    utc_now as week2_now,
)

OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science"
)
CACHE = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\ncaa")
WEEKS = ("00", "01", "02", "03")
BUDGET = {
    "max_requests": 8,
    "sleep_seconds": 0.4,
    "metered_scraper_credits": 0,
    "route": "ncaa_com_fcs_scoreboard",
}
UA = (
    "BAS-Cycle33-Reconstruction/1.0 "
    "(https://github.com/KevinSGarrett/BatteredAggieSyndrome; "
    "FCS scoreboard cache-first, not forecast backfill)"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    now = week2_now()
    ledger: list[dict[str, Any]] = []
    contests: list[dict[str, Any]] = []
    live = 0
    for week in WEEKS:
        uri = f"https://www.ncaa.com/scoreboard/football/fcs/2026/{week}/all-conf"
        cache = CACHE / f"scoreboard-fcs-2026-{week}.html"
        if cache.is_file():
            body = cache.read_bytes()
            receipt = cache_hit_from_path(
                cache,
                url=uri,
                original={
                    "request_id": sha256_json({"url": uri}),
                    "raw_sha256": sha256_bytes(body),
                    "http_status": 200,
                    "ok": True,
                },
            )
            receipt["week"] = week
            receipt["subdivision"] = "FCS"
            ledger.append(receipt)
            contests.extend(
                parse_ncaa_com_scoreboard_contests(body.decode("utf-8", "replace"))
            )
            continue
        if live >= int(BUDGET["max_requests"]):
            ledger.append(
                {
                    "route": uri,
                    "week": week,
                    "status": "BUDGET_CEILING",
                    "http_status": None,
                    "ok": False,
                    "cached": False,
                    "subdivision": "FCS",
                }
            )
            continue
        live += 1
        start = utc_now()
        request = urllib.request.Request(uri, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status = int(response.status)
                body = response.read()
            error = None
        except urllib.error.HTTPError as exc:
            status = int(exc.code)
            body = exc.read() or b""
            error = f"HTTPError:{exc.code}"
        except Exception as exc:  # noqa: BLE001
            status = 0
            body = b""
            error = type(exc).__name__
        time.sleep(float(BUDGET["sleep_seconds"]))
        end = utc_now()
        ok = 200 <= int(status) < 300 and body
        if ok:
            cache.write_bytes(body)
            contests.extend(
                parse_ncaa_com_scoreboard_contests(body.decode("utf-8", "replace"))
            )
        elif body and status:
            (CACHE / f"scoreboard-fcs-2026-{week}.error-{status}.html").write_bytes(
                body
            )
        ledger.append(
            {
                "route": uri,
                "week": week,
                "subdivision": "FCS",
                "status": "HTTP_OK" if ok else "HTTP_ERROR",
                "http_status": status,
                "ok": bool(ok),
                "cached": False,
                "error": error,
                "retrieved_at_utc": end,
                "cache_read_at_utc": None,
                "request_identity_sha256": sha256_json({"url": uri}),
                "raw_sha256": sha256_bytes(body) if body else None,
                "start_utc": start,
                "error_body_not_success": not ok,
            }
        )
    cutoff_counts: dict[str, int] = {}
    for row in contests:
        cut = cutoffs_from_kickoff_epoch(row.get("start_time_epoch"), now=now)
        key = str(cut.get("t24h_disposition") or "CUTOFF_UNKNOWN")
        cutoff_counts[key] = cutoff_counts.get(key, 0) + 1
        row["t24h_disposition"] = cut["t24h_disposition"]
        row["t90m_disposition"] = cut["t90m_disposition"]
        row["forecast_classification"] = "UNTRUSTED_SHADOW"
        row["retroactive_forecast_forbidden"] = True
    unique_ids = {
        str(row.get("ncaa_com_contest_id"))
        for row in contests
        if row.get("ncaa_com_contest_id")
    }
    payload = {
        "artifact_type": "CYCLE33_FCS_SCOREBOARD",
        "as_of_utc": utc_now(),
        "budget": BUDGET,
        "live_requests": live,
        "scoreboard_attempts": ledger,
        "observation_count": len(contests),
        "unique_contest_ids": len(unique_ids),
        "week2_label_source": "NCAA_COM_FCS_SCOREBOARD_WEEKS_00_03",
        "t24h_disposition_counts": cutoff_counts,
        "rearm_forbidden": True,
        "invented_forecast": False,
        "pit_admitted": False,
        "week2_row_count": len(contests),
    }
    (OUT / "CYCLE33_FCS_SCOREBOARD.json").write_text(
        json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "observation_count": payload["observation_count"],
                "unique_contest_ids": payload["unique_contest_ids"],
                "live_requests": live,
                "t24h_disposition_counts": cutoff_counts,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

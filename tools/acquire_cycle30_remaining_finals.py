"""Acquire remaining Week 1 official contest pages without scrapfly.

Does not recapture a past T-90 as on-time. Preserves predecessor captures.
Uses contest-scoped terminal classification from Cycle #30 acquisition.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.acquisition import (  # noqa: E402
    classify_semantic_page,
    classify_transport_and_upstream,
    contest_scoped_terminal,
    request_identity,
    receipt_identity,
)
from aggie_analytics.cycle30.hashing import sha256_bytes  # noqa: E402
from aggie_analytics.data.cfbd import (  # noqa: E402
    CFBDTransport,
    acquisition_request,
    load_dotenv_value,
)

REMAINING = (
    {"ncaa_contest_id": "6602874", "away": "Notre Dame", "home": "Wisconsin"},
    {"ncaa_contest_id": "6620581", "away": "Louisville", "home": "Ole Miss"},
    {"ncaa_contest_id": "6594400", "away": "SMU", "home": "Florida St."},
)
UA = (
    "BAS-Cycle30-Reconstruction/1.0 "
    "(https://github.com/KevinSGarrett/BatteredAggieSyndrome; "
    "official-final status, not T-90 recapture)"
)
EXT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work")
BUDGET = {
    "max_requests": 6,
    "max_retries": 0,
    "concurrency": 1,
    "metered_scraper_credits": 0,
    "route": "ncaa_stats_direct_http",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    EXT.mkdir(parents=True, exist_ok=True)
    (EXT / "CYCLE30_REMAINING_FINALS_BUDGET.json").write_text(
        json.dumps(BUDGET, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    cache_root = EXT / "raw" / "ncaa"
    cache_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for contest in REMAINING:
        contest_id = contest["ncaa_contest_id"]
        uri = f"https://stats.ncaa.org/contests/{contest_id}/box_score"
        cache = cache_root / f"{contest_id}.html"
        start = utc_now()
        http_status = None
        body = b""
        cached = False
        error = None
        request = urllib.request.Request(uri, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                http_status = int(response.status)
                body = response.read()
            cache.write_bytes(body)
        except urllib.error.HTTPError as exc:
            error = f"HTTPError:{exc.code}"
            http_status = int(exc.code)
            body = exc.read() or b""
            if body:
                (cache_root / f"{contest_id}.error-{exc.code}.html").write_bytes(body)
        except Exception as exc:  # noqa: BLE001
            error = str(type(exc).__name__)
            if cache.is_file():
                body = cache.read_bytes()
                http_status = 200
                cached = True
                error = f"{error}:FALLBACK_CACHE"
        end = utc_now()
        text = body.decode("utf-8", errors="replace")
        transport = classify_transport_and_upstream(
            http_status=http_status, upstream_status=http_status, body=body
        )
        semantic = classify_semantic_page(body)
        terminal = "NOT_ATTEMPTED"
        if http_status is not None and int(http_status) >= 400:
            terminal = "ACQUISITION_FAILED"
            acquisition_disposition = "ACQUISITION_FAILED"
        else:
            acquisition_disposition = "CAPTURED" if body else "NOT_ATTEMPTED"
        if body and acquisition_disposition != "ACQUISITION_FAILED":
            try:
                terminal = contest_scoped_terminal(
                    page_text=text,
                    contest_id=contest_id,
                    contest_hint=contest_id,
                    score_element_ids=[f"score-{contest_id}"],
                    ordered_participant_ids=["HOME", "AWAY"],
                    page_url=uri,
                    embedded_contest_id=contest_id,
                )
            except Exception as exc:  # noqa: BLE001
                terminal = f"CLASSIFY_FAILED:{type(exc).__name__}"
        req_id = request_identity(
            method="GET",
            uri=uri,
            source_contract="NCAA_STATS_BOX_SCORE",
        )
        rows.append(
            {
                **contest,
                "uri": uri,
                "http_status": http_status,
                "cached": cached,
                "error": error,
                "transport_state": transport.get("transport_state"),
                "upstream_state": transport.get("upstream_state"),
                "semantic_state": semantic,
                "terminal_state": terminal,
                "acquisition_disposition": acquisition_disposition,
                "t90_not_relabeled_on_time": True,
                "forecast_not_created": True,
                "raw_sha256": sha256_bytes(body) if body else None,
                "request_identity_sha256": req_id,
                "receipt_identity": receipt_identity(
                    request_identity_sha256=req_id,
                    start_utc=start,
                    end_utc=end,
                    time_authority="local_clock",
                    raw_sha256=sha256_bytes(body) if body else "empty",
                ),
                "retrieved_at_utc": end,
                "artifact_class": "REAL_EVIDENCE" if body else "BLOCKER_METADATA",
            }
        )
    predecessor = Path(
        r"C:\BatteredAggieSyndrome.data\ops\cycle29_work\outputs\CYCLE29_REMAINING_WEEK1_OFFICIAL_FINAL_SUCCESSOR.json"
    )
    predecessor_rows = []
    if predecessor.is_file():
        predecessor_rows = (
            json.loads(predecessor.read_text(encoding="utf-8")).get("contests") or []
        )
    smu_cfbd = None
    try:
        token = load_dotenv_value(
            Path(r"C:\BatteredAggieSyndrome\.env"), "CFBD_API_KEY"
        )
        transport = CFBDTransport(access_token=token)
        request = acquisition_request(
            endpoint_id="games",
            path="/games",
            parameters={"year": 2026, "team": "Florida State"},
            run_id="cycle30-smu-status",
        )
        response = transport(request)
        payload = json.loads(response.body.decode("utf-8"))
        for item in payload if isinstance(payload, list) else []:
            if (
                item.get("homeTeam") == "Florida State"
                and item.get("awayTeam") == "SMU"
            ):
                smu_cfbd = {
                    "completed": item.get("completed"),
                    "home_points": item.get("homePoints"),
                    "away_points": item.get("awayPoints"),
                    "start_date": item.get("startDate"),
                    "cfbd_id": item.get("id"),
                    "not_ncaa_official_final": True,
                    "http_status": response.status_code,
                }
                break
    except Exception as exc:  # noqa: BLE001
        smu_cfbd = {"error": type(exc).__name__, "not_ncaa_official_final": True}
    out = EXT / "outputs" / "WEEK1_REMAINING_FINALS_ATTEMPTS.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "ncaa_direct_attempts": rows,
                "predecessor_cycle29_contests": [
                    {
                        "ncaa_contest_id": row.get("ncaa_contest_id"),
                        "state": row.get("state"),
                        "admitted": row.get("admitted_score") is not None,
                        "forecast_rewritten": row.get("forecast_rewritten"),
                    }
                    for row in predecessor_rows
                ],
                "smu_fsu_cfbd_corroboration": smu_cfbd,
                "smu_t90_lease_expired_not_recaptured": True,
                "no_new_scheduler_job": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print("remaining_finals", len(rows), [row.get("terminal_state") for row in rows])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

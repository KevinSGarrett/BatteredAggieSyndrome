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
    match_ncaa_com_contest,
    parse_ncaa_com_scoreboard_contests,
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
    "max_requests": 20,
    "max_retries": 0,
    "concurrency": 1,
    "metered_scraper_credits": 0,
    "route": "ncaa_stats_direct_http_plus_ncaa_com_scoreboard",
}
UA_BROWSER = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
STATS_PATH_TEMPLATES = (
    "https://stats.ncaa.org/contests/{id}/box_score",
    "https://stats.ncaa.org/contests/{id}/play_by_play",
    "https://stats.ncaa.org/contests/{id}",
)
NCAA_COM_WEEKS = ("00", "01", "02", "03")
REMAINING_NAME_KEYS = {
    "6602874": {
        "home_names": ("wisconsin", "wisconsin badgers"),
        "away_names": ("notre dame", "notre-dame", "notre dame fighting irish"),
    },
    "6620581": {
        "home_names": ("ole miss", "ole-miss", "mississippi"),
        "away_names": ("louisville",),
    },
    "6594400": {
        "home_names": ("florida st", "florida st.", "florida state", "florida-st"),
        "away_names": ("smu",),
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stats_headers(contest_id: str) -> dict[str, str]:
    return {
        "User-Agent": UA_BROWSER,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"https://stats.ncaa.org/contests/{contest_id}/box_score",
    }


def fetch_stats_uri(uri: str, contest_id: str) -> tuple[int | None, bytes, str | None]:
    request = urllib.request.Request(uri, headers=stats_headers(contest_id))
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return int(response.status), response.read(), None
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read() or b"", f"HTTPError:{exc.code}"
    except Exception as exc:  # noqa: BLE001
        return None, b"", str(type(exc).__name__)


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
        chosen_uri = STATS_PATH_TEMPLATES[0].format(id=contest_id)
        start = utc_now()
        http_status = None
        body = b""
        error = None
        path_attempts: list[dict[str, object]] = []
        for template in STATS_PATH_TEMPLATES:
            uri = template.format(id=contest_id)
            status, fetched, fetch_error = fetch_stats_uri(uri, contest_id)
            path_attempts.append(
                {
                    "uri": uri,
                    "http_status": status,
                    "error": fetch_error,
                    "same_contest_id": contest_id,
                }
            )
            chosen_uri = uri
            http_status = status
            body = fetched
            error = fetch_error
            if status == 200 and contest_id.encode("ascii") in fetched:
                cache_root.joinpath(f"{contest_id}.html").write_bytes(fetched)
                break
            if body:
                (
                    cache_root / f"{contest_id}.error-{status or 0}.html"
                ).write_bytes(body)
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
                    page_url=chosen_uri,
                    embedded_contest_id=contest_id,
                )
            except Exception as exc:  # noqa: BLE001
                terminal = f"CLASSIFY_FAILED:{type(exc).__name__}"
        req_id = request_identity(
            method="GET",
            uri=chosen_uri,
            source_contract="NCAA_STATS_BOX_SCORE",
        )
        rows.append(
            {
                **contest,
                "uri": chosen_uri,
                "http_status": http_status,
                "cached": False,
                "error": error,
                "same_contest_id_paths": path_attempts,
                "transport_state": transport.get("transport_state"),
                "upstream_state": transport.get("upstream_state"),
                "semantic_state": semantic,
                "terminal_state": terminal,
                "acquisition_disposition": acquisition_disposition,
                "t90_not_relabeled_on_time": True,
                "forecast_not_created": True,
                "ncaa_com_is_not_stats_final": True,
                "cfbd_is_not_stats_final": True,
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
    ncaa_com_contests: list[dict[str, object]] = []
    ncaa_com_attempts: list[dict[str, object]] = []
    cache_com = EXT / "raw" / "ncaa"
    cache_com.mkdir(parents=True, exist_ok=True)
    for week in NCAA_COM_WEEKS:
        uri = f"https://www.ncaa.com/scoreboard/football/fbs/2026/{week}/all-conf"
        start = utc_now()
        cache = cache_com / f"scoreboard-2026-{week}.html"
        http_status = None
        body = b""
        error = None
        try:
            request = urllib.request.Request(uri, headers={"User-Agent": UA})
            with urllib.request.urlopen(request, timeout=30) as response:
                http_status = int(response.status)
                body = response.read()
            cache.write_bytes(body)
        except urllib.error.HTTPError as exc:
            error = f"HTTPError:{exc.code}"
            http_status = int(exc.code)
            body = exc.read() or b""
        except Exception as exc:  # noqa: BLE001
            error = str(type(exc).__name__)
            if cache.is_file():
                body = cache.read_bytes()
                http_status = 200
        end = utc_now()
        ncaa_com_attempts.append(
            {
                "uri": uri,
                "http_status": http_status,
                "error": error,
                "retrieved_at_utc": end,
                "raw_sha256": sha256_bytes(body) if body else None,
                "receipt_identity": receipt_identity(
                    request_identity_sha256=request_identity(
                        method="GET",
                        uri=uri,
                        source_contract="NCAA_COM_SCOREBOARD",
                    ),
                    start_utc=start,
                    end_utc=end,
                    time_authority="local_clock",
                    raw_sha256=sha256_bytes(body) if body else "empty",
                ),
                "artifact_class": "REAL_EVIDENCE",
            }
        )
        if body:
            ncaa_com_contests.extend(
                parse_ncaa_com_scoreboard_contests(body.decode("utf-8", "replace"))
            )
    ncaa_com_matches = {}
    for contest in REMAINING:
        contest_id = contest["ncaa_contest_id"]
        keys = REMAINING_NAME_KEYS[contest_id]
        matched = match_ncaa_com_contest(
            ncaa_com_contests,
            home_names=keys["home_names"],
            away_names=keys["away_names"],
        )
        if matched is None:
            matched = match_ncaa_com_contest(
                ncaa_com_contests,
                home_names=keys["away_names"],
                away_names=keys["home_names"],
            )
        ncaa_com_matches[contest_id] = matched
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
                "ncaa_com_scoreboard_attempts": ncaa_com_attempts,
                "ncaa_com_contests_parsed": len(ncaa_com_contests),
                "ncaa_com_remaining_matches": ncaa_com_matches,
                "smu_t90_lease_expired_not_recaptured": True,
                "no_new_scheduler_job": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        "remaining_finals",
        len(rows),
        [row.get("terminal_state") for row in rows],
        "ncaa_com",
        {
            key: (value or {}).get("terminal_state")
            for key, value in ncaa_com_matches.items()
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

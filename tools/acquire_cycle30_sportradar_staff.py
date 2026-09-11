"""Budgeted SportsRadar NCAAFB team-roster coach acquisition.

Uses the local SPORTSRADAR_API_KEY. Does not infer assistant roles. CFBD
assistant inference remains forbidden. Personal email/phone is not stored.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.coaching import (  # noqa: E402
    match_program_to_sportradar_team,
    parse_sportradar_coaches,
    redact_personal_contact,
)
from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_json  # noqa: E402
from aggie_analytics.data.cfbd import load_dotenv_value  # noqa: E402

BUDGET = {
    "max_requests": 280,
    "max_retries": 0,
    "concurrency": 1,
    "metered_scraper_credits": 0,
    "sleep_s": 1.1,
    "timeout_s": 20,
    "route": "sportradar_ncaafb_v7_full_roster",
    "access_levels": ["production", "trial"],
    "pit_admitted": False,
}
ENV_FILE = Path(r"C:\BatteredAggieSyndrome\.env")
WORK = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work")
RAW = WORK / "raw" / "sportradar"
OUT = WORK / "outputs"
BASE = "https://api.sportradar.com/ncaafb"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _public_url(url: str) -> str:
    query_key = "api" + "_key"
    return url.replace(f"{query_key}=", f"{query_key}=REDACTED")


def fetch_json(
    url: str,
    *,
    access_credential: str,
    ledger: list[dict[str, Any]],
    budget: dict[str, Any],
    use_query: bool = False,
) -> tuple[int, Any, dict[str, Any]]:
    if sum(1 for row in ledger if not row.get("cached")) >= int(budget["max_requests"]):
        raise RuntimeError("SportsRadar request ceiling reached")
    cache = RAW / f"{sha256_json({'url': url, 'query': use_query})}.json"
    if cache.is_file():
        body = cache.read_bytes()
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            payload = None
        usable = isinstance(payload, dict) and (
            "coaches" in payload or "teams" in payload or "divisions" in payload
        )
        if usable:
            receipt = {
                "route": _public_url(url),
                "status": "CACHE_HIT",
                "http_status": 200,
                "request_identity_sha256": sha256_json(
                    {"url": url, "query": use_query}
                ),
                "receipt_identity": sha256_bytes(body),
                "raw_sha256": sha256_bytes(body),
                "cached": True,
                "retrieved_at_utc": utc_now(),
            }
            ledger.append(receipt)
            return 200, payload, receipt
    request_url = url
    headers = {
        "Accept": "application/json",
        "User-Agent": "BAS-Cycle30-Reconstruction/1.0",
    }
    if use_query:
        sep = "&" if "?" in url else "?"
        query_key = "api" + "_key"
        request_url = f"{url}{sep}{query_key}={access_credential}"
    else:
        header_key = "x-api" + "-key"
        headers[header_key] = access_credential
    request = urllib.request.Request(request_url, headers=headers)
    start = utc_now()
    status = 0
    body = b""
    try:
        with urllib.request.urlopen(
            request, timeout=int(budget["timeout_s"])
        ) as response:
            status = int(response.status)
            body = response.read()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        body = exc.read() or b""
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
        status = 0
        body = str(exc).encode("utf-8")
    time.sleep(float(budget["sleep_s"]))
    end = utc_now()
    raw_hash = sha256_bytes(body) if body else "empty"
    receipt = {
        "route": _public_url(url),
        "status": "HTTP_OK" if 200 <= status < 300 else "HTTP_ERROR",
        "http_status": status,
        "request_identity_sha256": sha256_json({"url": url, "query": use_query}),
        "receipt_identity": sha256_json(
            {"start": start, "end": end, "raw_sha256": raw_hash, "status": status}
        ),
        "raw_sha256": raw_hash,
        "cached": False,
        "retrieved_at_utc": end,
    }
    ledger.append(receipt)
    RAW.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(body)
    try:
        payload = json.loads(body.decode("utf-8")) if body else None
    except json.JSONDecodeError:
        payload = None
    if not (200 <= status < 300):
        cache.unlink(missing_ok=True)
    return status, payload, receipt


def teams_from_payload(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    teams = payload.get("teams")
    if isinstance(teams, list):
        return [row for row in teams if isinstance(row, dict)]
    out: list[dict[str, Any]] = []
    for division in payload.get("divisions") or []:
        if not isinstance(division, dict):
            continue
        for conference in division.get("conferences") or []:
            if not isinstance(conference, dict):
                continue
            for team in conference.get("teams") or []:
                if isinstance(team, dict):
                    out.append(team)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (WORK / "CYCLE30_SPORTSRADAR_STAFF_BUDGET.json").write_text(
        json.dumps(BUDGET, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    programs = load_jsonl(OUT / "CURRENT_2026_PROGRAMS.jsonl")
    if args.limit:
        programs = programs[: args.limit]
    if args.dry_run:
        print("BUDGET_DECLARED", BUDGET["max_requests"], "programs", len(programs))
        return 0
    access_credential = load_dotenv_value(ENV_FILE, "SPORTSRADAR_API_KEY")
    ledger: list[dict[str, Any]] = []
    access_level = ""
    use_query = False
    teams: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    people_out: list[dict[str, Any]] = []
    try:
        for level in BUDGET["access_levels"]:
            for query_mode in (False, True):
                url = f"{BASE}/{level}/v7/en/league/teams.json"
                status, payload, _receipt = fetch_json(
                    url,
                    access_credential=access_credential,
                    ledger=ledger,
                    budget=BUDGET,
                    use_query=query_mode,
                )
                found = teams_from_payload(payload)
                if status == 200 and found:
                    access_level = str(level)
                    use_query = query_mode
                    teams = found
                    break
            if teams:
                break
        if not teams:
            raise RuntimeError("SportsRadar teams feed returned no teams")
        for program in programs:
            pid = str(program.get("program_id") or "")
            display = str(program.get("display_name") or "")
            matched = match_program_to_sportradar_team(display, teams)
            if not matched:
                attempts.append(
                    {
                        "program_id": pid,
                        "display_name": display,
                        "status": "NO_SPORTSRADAR_TEAM_MATCH",
                        "attempt_count": 1,
                        "receipt_identity": sha256_json(
                            {"program_id": pid, "access_level": access_level}
                        ),
                        "artifact_class": "REAL_EVIDENCE",
                        "pit_admitted": False,
                    }
                )
                continue
            team_id = str(matched.get("id") or "")
            roster_url = f"{BASE}/{access_level}/v7/en/teams/{team_id}/full_roster.json"
            status, payload, receipt = fetch_json(
                roster_url,
                access_credential=access_credential,
                ledger=ledger,
                budget=BUDGET,
                use_query=use_query,
            )
            coaches: list[dict[str, str]] = []
            if isinstance(payload, dict):
                text = redact_personal_contact(json.dumps(payload))
                payload = json.loads(text)
                coaches = parse_sportradar_coaches(
                    payload, team_id=team_id, page_url=_public_url(roster_url)
                )
            if status != 200:
                attempts.append(
                    {
                        "program_id": pid,
                        "display_name": display,
                        "status": "ACQUISITION_FAILED",
                        "http_status": status,
                        "sportradar_team_id": team_id,
                        "attempt_count": 1,
                        "receipt_identity": receipt.get("receipt_identity"),
                        "artifact_class": "REAL_EVIDENCE",
                        "pit_admitted": False,
                    }
                )
                continue
            for person in coaches:
                people_out.append(
                    {
                        "program_id": pid,
                        "display_name": display,
                        "sportradar_team_id": team_id,
                        "sportradar_market": matched.get("market"),
                        "artifact_class": "REAL_EVIDENCE",
                        "pit_admitted": False,
                        **person,
                    }
                )
            attempts.append(
                {
                    "program_id": pid,
                    "display_name": display,
                    "status": "CAPTURED" if coaches else "ATTEMPTED_EMPTY_COACHES",
                    "http_status": status,
                    "sportradar_team_id": team_id,
                    "sportradar_market": matched.get("market"),
                    "people_count": len(coaches),
                    "attempt_count": 1,
                    "receipt_identity": receipt.get("receipt_identity"),
                    "request_identity_sha256": receipt.get("request_identity_sha256"),
                    "route": _public_url(roster_url),
                    "artifact_class": "REAL_EVIDENCE",
                    "pit_admitted": False,
                }
            )
    except RuntimeError as exc:
        print("CEILING", exc)
        attempts = locals().get("attempts") or []
        people_out = locals().get("people_out") or []
    (OUT / "CYCLE30_SPORTSRADAR_STAFF_LEDGER.json").write_text(
        json.dumps(
            {
                "budget": BUDGET,
                "access_level": access_level,
                "attempt_count": len(ledger),
                "team_count": len(teams),
                "attempts": ledger,
                "artifact_class": "REAL_EVIDENCE",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (OUT / "SPORTSRADAR_STAFF_HTTP_ATTEMPTS.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in attempts),
        encoding="utf-8",
    )
    (OUT / "SPORTSRADAR_STAFF_PARSED.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in people_out),
        encoding="utf-8",
    )
    print(
        "sportradar_staff",
        "access",
        access_level or "NONE",
        "teams",
        len(teams),
        "programs",
        len(attempts),
        "captured",
        sum(1 for row in attempts if row.get("status") == "CAPTURED"),
        "people",
        len(people_out),
        "unmatched",
        sum(1 for row in attempts if row.get("status") == "NO_SPORTSRADAR_TEAM_MATCH"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

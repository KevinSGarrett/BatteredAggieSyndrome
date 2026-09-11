"""Exhaust remaining structured availability routes.

Follows extra report-like assets from cached conference pages, then
cache-first CFBD /injuries and Sportradar weekly injuries. Those providers
are not official conference reports. Name-only rows are not verified
roster joins. Empty official reports keep the required acquisition blocked.
"""

from __future__ import annotations

import json
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aggie_analytics.cycle30.availability import (  # noqa: E402
    PUBLIC_AVAILABILITY_ROUTES,
    availability_report_hrefs,
    classify_availability_source,
    extract_candidate_player_rows,
    pdf_plaintext,
)
from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_json  # noqa: E402
from aggie_analytics.data.cfbd import (  # noqa: E402
    load_dotenv_value,
    public_uri,
)

RAW_HTML = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\availability")
RAW_CFBD = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\injuries")
RAW_SR = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\sportradar")
ENV_FILE = Path(r"C:\BatteredAggieSyndrome\.env")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)
EXTRA = (
    {
        "source_id": "SRC-017-LIVE",
        "conference": "SEC",
        "uri": "https://www.secsports.com/fbreports",
    },
)
CFBD_BUDGET = {
    "max_requests": 6,
    "years": [2024, 2025, 2026],
    "weeks": [1],
    "path": "/injuries",
}
SR_BUDGET = {
    "max_requests": 2,
    "year": 2026,
    "season": "REG",
    "weeks": [1],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cache_html(uri: str) -> Path:
    return RAW_HTML / f"{sha256_json({'url': uri})}.html"


ASSET_BUDGET = {"max_requests": 48}


def fetch_asset(
    uri: str, ledger: list[dict[str, Any]]
) -> tuple[bytes, dict[str, Any]]:
    cache = cache_html(uri)
    if cache.is_file() and cache.stat().st_size > 0:
        body = cache.read_bytes()
        receipt = {
            "route": uri,
            "status": "CACHE_HIT",
            "http_status": 200,
            "cached": True,
            "raw_sha256": sha256_bytes(body),
            "retrieved_at_utc": utc_now(),
        }
        ledger.append(receipt)
        return body, receipt
    live = sum(1 for row in ledger if not row.get("cached"))
    if live >= int(ASSET_BUDGET["max_requests"]):
        receipt = {
            "route": uri,
            "status": "CEILING",
            "http_status": 0,
            "cached": False,
            "retrieved_at_utc": utc_now(),
        }
        ledger.append(receipt)
        return b"", receipt
    request = urllib.request.Request(
        uri,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "application/pdf,application/json,text/html,*/*;q=0.8",
        },
    )
    start = utc_now()
    status = 0
    body = b""
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = int(response.status)
            body = response.read()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        body = exc.read() or b""
    except urllib.error.URLError as exc:
        status = 0
        body = str(exc.reason).encode("utf-8")
    time.sleep(0.2)
    receipt = {
        "route": uri,
        "status": "HTTP_OK" if 200 <= status < 300 else "HTTP_ERROR",
        "http_status": status,
        "cached": False,
        "raw_sha256": sha256_bytes(body) if body else "empty",
        "retrieved_at_utc": utc_now(),
        "started_at_utc": start,
    }
    ledger.append(receipt)
    cache.parent.mkdir(parents=True, exist_ok=True)
    if body:
        cache.write_bytes(body)
    return body, receipt


def _cfbd_cache(parameters: dict[str, Any]) -> Path:
    ident = sha256_json({"endpoint": "/injuries", "parameters": parameters})
    return RAW_CFBD / f"{ident}.json"


def _public_sr(url: str) -> str:
    return url.replace("api_key=", "api_key=REDACTED")


def fetch_cfbd_injuries(
    *,
    access_credential: str,
    parameters: dict[str, Any],
    ledger: list[dict[str, Any]],
) -> tuple[Any, dict[str, Any]]:
    if sum(1 for row in ledger if not row.get("cached")) >= int(CFBD_BUDGET["max_requests"]):
        raise RuntimeError("CFBD injuries request ceiling reached")
    cached = _cfbd_cache(parameters)
    if cached.is_file():
        body = cached.read_bytes()
        payload = json.loads(body.decode("utf-8"))
        receipt = {
            "route": "/injuries",
            "parameters": parameters,
            "status": "CACHE_HIT",
            "http_status": 200,
            "cached": True,
            "raw_sha256": sha256_bytes(body),
            "retrieved_at_utc": utc_now(),
            "row_count": len(payload) if isinstance(payload, list) else None,
            "source_class": classify_availability_source(
                source_id="SRC-002", uri=public_uri("/injuries", parameters)
            ),
        }
        ledger.append(receipt)
        return payload, receipt
    uri = public_uri("/injuries", parameters)
    request = urllib.request.Request(
        uri,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_credential}",
            "User-Agent": "AggieAnalyticsEngine-private-research/1.0",
        },
    )
    start = utc_now()
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = response.read()
            status = int(response.status)
    except urllib.error.HTTPError as exc:
        body = exc.read() or b""
        status = int(exc.code)
    except urllib.error.URLError as exc:
        body = str(exc.reason).encode("utf-8")
        status = 0
    time.sleep(0.2)
    end = utc_now()
    receipt = {
        "route": "/injuries",
        "parameters": parameters,
        "status": "HTTP_OK" if 200 <= status < 300 else "HTTP_ERROR",
        "http_status": status,
        "cached": False,
        "raw_sha256": sha256_bytes(body) if body else "empty",
        "retrieved_at_utc": end,
        "started_at_utc": start,
        "source_class": classify_availability_source(source_id="SRC-002", uri=uri),
    }
    ledger.append(receipt)
    if status < 200 or status >= 300:
        receipt["row_count"] = 0
        return None, receipt
    RAW_CFBD.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(body)
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        receipt["row_count"] = 0
        receipt["status"] = "SCHEMA_INCOMPATIBLE"
        return None, receipt
    receipt["row_count"] = len(payload) if isinstance(payload, list) else None
    return payload, receipt


def fetch_sr_injuries(
    *,
    access_credential: str,
    year: int,
    week: int,
    ledger: list[dict[str, Any]],
) -> tuple[Any, dict[str, Any]]:
    if sum(1 for row in ledger if not row.get("cached")) >= int(SR_BUDGET["max_requests"]):
        raise RuntimeError("Sportradar injuries request ceiling reached")
    url = (
        "https://api.sportradar.com/ncaafb/production/v7/en/seasons/"
        f"{year}/REG/weeks/{week}/injuries.json"
    )
    cache = RAW_SR / f"{sha256_json({'url': url, 'kind': 'injuries'})}.json"
    if cache.is_file() and cache.stat().st_size > 0:
        body = cache.read_bytes()
        if body and body != b"{}":
            try:
                payload = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                payload = None
            usable = isinstance(payload, dict) and (
                "teams" in payload or "injuries" in payload or "week" in payload
            )
            if usable:
                receipt = {
                    "route": _public_sr(url),
                    "status": "CACHE_HIT",
                    "http_status": 200,
                    "cached": True,
                    "raw_sha256": sha256_bytes(body),
                    "retrieved_at_utc": utc_now(),
                    "source_class": classify_availability_source(
                        source_id="SRC-SPORTSRADAR", uri=url
                    ),
                }
                ledger.append(receipt)
                return payload, receipt
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "BAS-Cycle32-Reconstruction/1.0",
            "x-api-key": access_credential,
        },
    )
    start = utc_now()
    status = 0
    body = b""
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = int(response.status)
            body = response.read()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        body = exc.read() or b""
    except urllib.error.URLError as exc:
        status = 0
        body = str(exc.reason).encode("utf-8")
    time.sleep(1.1)
    receipt = {
        "route": _public_sr(url),
        "status": "HTTP_OK" if 200 <= status < 300 else "HTTP_ERROR",
        "http_status": status,
        "cached": False,
        "raw_sha256": sha256_bytes(body) if body else "empty",
        "retrieved_at_utc": utc_now(),
        "started_at_utc": start,
        "source_class": classify_availability_source(
            source_id="SRC-SPORTSRADAR", uri=url
        ),
    }
    ledger.append(receipt)
    RAW_SR.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(body)
    if status < 200 or status >= 300:
        return None, receipt
    try:
        return json.loads(body.decode("utf-8")), receipt
    except json.JSONDecodeError:
        receipt["status"] = "SCHEMA_INCOMPATIBLE"
        return None, receipt


def cfbd_candidates(payload: Any, *, parameters: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not isinstance(payload, list):
        return rows
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(
            item.get("player")
            or item.get("playerName")
            or " ".join(
                part
                for part in (item.get("firstName"), item.get("lastName"))
                if part
            )
            or ""
        ).strip()
        if not name:
            continue
        status = str(
            item.get("status") or item.get("injuryStatus") or item.get("availability") or ""
        )
        rows.append(
            {
                "source_id": "SRC-002",
                "uri": public_uri("/injuries", parameters),
                "candidate_name": name,
                "program_hint": item.get("team") or item.get("teamId"),
                "original_status_token": status or None,
                "season": item.get("season") or parameters.get("year"),
                "week": item.get("week") or parameters.get("week"),
                "disposition": "CANDIDATE_NOT_JOINED",
                "joined_to_verified_roster": False,
                "no_report_means": "UNKNOWN",
                "private_medical_detail_ingested": False,
                "health_status_inferred": False,
                "source_class": "STRUCTURED_PROVIDER_NOT_OFFICIAL_CONFERENCE_REPORT",
                "out_of_fitted_models": True,
                "owner": "BAT-324",
                "artifact_class": "REAL_EVIDENCE",
            }
        )
    return rows


def sportradar_candidates(payload: Any, *, uri: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not isinstance(payload, dict):
        return rows
    teams = payload.get("teams") or payload.get("injuries") or []
    if isinstance(payload.get("week"), dict):
        teams = payload.get("teams") or []
    if not isinstance(teams, list):
        return rows
    for team in teams:
        if not isinstance(team, dict):
            continue
        players = team.get("players") or team.get("injuries") or []
        if not isinstance(players, list):
            continue
        for player in players:
            if not isinstance(player, dict):
                continue
            name = str(
                player.get("full_name")
                or player.get("name")
                or " ".join(
                    part
                    for part in (player.get("first_name"), player.get("last_name"))
                    if part
                )
                or ""
            ).strip()
            if not name:
                continue
            status = player.get("status") or player.get("injury") or {}
            token = ""
            if isinstance(status, dict):
                token = str(status.get("status") or status.get("comment") or "")
            else:
                token = str(status)
            rows.append(
                {
                    "source_id": "SRC-SPORTSRADAR",
                    "uri": uri,
                    "candidate_name": name,
                    "program_hint": team.get("name") or team.get("market"),
                    "original_status_token": token or None,
                    "disposition": "CANDIDATE_NOT_JOINED",
                    "joined_to_verified_roster": False,
                    "no_report_means": "UNKNOWN",
                    "private_medical_detail_ingested": False,
                    "health_status_inferred": False,
                    "source_class": "STRUCTURED_PROVIDER_NOT_OFFICIAL_CONFERENCE_REPORT",
                    "out_of_fitted_models": True,
                    "owner": "BAT-324",
                    "artifact_class": "REAL_EVIDENCE",
                }
            )
    return rows


def main() -> int:
    html_ledger: list[dict[str, Any]] = []
    asset_rows: list[dict[str, Any]] = []
    official_candidates: list[dict[str, Any]] = []
    seen_assets: set[str] = set()
    for route in [*PUBLIC_AVAILABILITY_ROUTES, *EXTRA]:
        uri = route["uri"]
        cache = cache_html(uri)
        if not cache.is_file():
            asset_rows.append(
                {
                    "parent_uri": uri,
                    "source_id": route["source_id"],
                    "disposition": "PARENT_CACHE_MISS",
                    "artifact_class": "BLOCKER_METADATA",
                }
            )
            continue
        html = cache.read_bytes().decode("utf-8", "replace")
        for asset_uri in availability_report_hrefs(html, page_uri=uri, limit=16):
            if asset_uri.casefold() in seen_assets:
                continue
            seen_assets.add(asset_uri.casefold())
            body, receipt = fetch_asset(asset_uri, html_ledger)
            if body.startswith(b"%PDF") or asset_uri.casefold().endswith(".pdf"):
                text = pdf_plaintext(body) or body.decode("utf-8", "replace")
            else:
                text = body.decode("utf-8", "replace") if body else ""
            candidates = extract_candidate_player_rows(
                text, source_id=route["source_id"], uri=asset_uri
            )
            official_candidates.extend(candidates)
            asset_rows.append(
                {
                    "parent_uri": uri,
                    "asset_uri": asset_uri,
                    "source_id": route["source_id"],
                    "conference": route["conference"],
                    "disposition": receipt.get("status"),
                    "http_status": receipt.get("http_status"),
                    "cached": receipt.get("cached"),
                    "player_rows_extracted": len(candidates),
                    "joined_to_verified_roster": False,
                    "source_class": classify_availability_source(
                        source_id=route["source_id"], uri=asset_uri
                    ),
                    "page_kind": (
                        "PARSED_PUBLIC_REPORT_OR_ARCHIVE"
                        if candidates
                        else "LINKED_ASSET_NO_PLAYER_ROWS"
                    ),
                    "artifact_class": "REAL_EVIDENCE",
                    "owner": "BAT-324",
                }
            )

    cfbd_ledger: list[dict[str, Any]] = []
    cfbd_candidates_out: list[dict[str, Any]] = []
    try:
        access = load_dotenv_value(ENV_FILE, "CFBD_API_KEY")
        for year in CFBD_BUDGET["years"]:
            payload, receipt = fetch_cfbd_injuries(
                access_credential=access,
                parameters={"year": year},
                ledger=cfbd_ledger,
            )
            cfbd_candidates_out.extend(
                cfbd_candidates(payload, parameters={"year": year})
            )
            if receipt.get("status") == "HTTP_OK" and not cfbd_candidates_out:
                for week in CFBD_BUDGET["weeks"]:
                    payload, _ = fetch_cfbd_injuries(
                        access_credential=access,
                        parameters={"year": year, "week": week},
                        ledger=cfbd_ledger,
                    )
                    cfbd_candidates_out.extend(
                        cfbd_candidates(
                            payload, parameters={"year": year, "week": week}
                        )
                    )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        cfbd_ledger.append(
            {
                "route": "/injuries",
                "status": "CREDENTIAL_OR_CEILING",
                "detail": type(exc).__name__,
                "cached": False,
            }
        )

    sr_ledger: list[dict[str, Any]] = []
    sr_candidates_out: list[dict[str, Any]] = []
    try:
        sr_key = load_dotenv_value(ENV_FILE, "SPORTSRADAR_API_KEY")
        for week in SR_BUDGET["weeks"]:
            payload, receipt = fetch_sr_injuries(
                access_credential=sr_key,
                year=int(SR_BUDGET["year"]),
                week=week,
                ledger=sr_ledger,
            )
            sr_candidates_out.extend(
                sportradar_candidates(
                    payload,
                    uri=(
                        "https://api.sportradar.com/ncaafb/production/v7/en/seasons/"
                        f"{SR_BUDGET['year']}/REG/weeks/{week}/injuries.json"
                    ),
                )
            )
            del receipt
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        sr_ledger.append(
            {
                "route": "sportradar_weekly_injuries",
                "status": "CREDENTIAL_OR_CEILING",
                "detail": type(exc).__name__,
                "cached": False,
            }
        )

    science = OUT / "science"
    science.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_type": "CYCLE32_AVAILABILITY_STRUCTURED_EXHAUSTION",
        "as_of_utc": utc_now(),
        "official_conference_player_status_rows": len(official_candidates),
        "structured_provider_candidate_rows": len(cfbd_candidates_out)
        + len(sr_candidates_out),
        "cfbd_injury_candidate_rows": len(cfbd_candidates_out),
        "sportradar_injury_candidate_rows": len(sr_candidates_out),
        "joined_to_verified_roster": False,
        "cfbd_is_not_official_conference_report": True,
        "sportradar_is_not_official_conference_report": True,
        "record_book_or_media_guide_names_are_not_availability": True,
        "no_report_means": "UNKNOWN",
        "acquisition_complete": False,
        "if_empty_official": "required official-report acquisition remains BLOCKED, not locally complete",
        "asset_rows": asset_rows,
        "cfbd_attempts": cfbd_ledger,
        "sportradar_attempts": [
            {key: value for key, value in row.items() if "key" not in key.casefold()}
            for row in sr_ledger
        ],
        "predecessor_not_overwritten": True,
    }
    (science / "CYCLE32_AVAILABILITY_STRUCTURED_EXHAUSTION.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "official_rows": len(official_candidates),
                "cfbd_rows": len(cfbd_candidates_out),
                "sportradar_rows": len(sr_candidates_out),
                "assets": len(asset_rows),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

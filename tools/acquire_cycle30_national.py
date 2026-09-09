"""Budgeted Cycle #30 CFBD national acquisition.

Ceiling is declared before any request. Cached responses are reused.
No scrapfly/scraperapi. No new paid purchase.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_json  # noqa: E402
from aggie_analytics.data.cfbd import (  # noqa: E402
    CFBDTransport,
    acquisition_request,
    load_dotenv_value,
)

BUDGET = {
    "max_requests": 80,
    "max_retries": 1,
    "concurrency": 1,
    "metered_scraper_credits": 0,
    "years": list(range(2013, 2024)) + [2026],
    "endpoints": ["/teams", "/games", "/coaches", "/venues"],
    "classifications": ["fbs", "fcs"],
}
ENV_FILE = Path(r"C:\BatteredAggieSyndrome\.env")
EXT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cache_path(endpoint: str, parameters: dict[str, Any]) -> Path:
    ident = sha256_json({"endpoint": endpoint, "parameters": parameters})
    safe = endpoint.strip("/").replace("/", "_")
    return EXT / safe / f"{ident}.json"


def fetch(
    transport: CFBDTransport,
    *,
    endpoint_id: str,
    path: str,
    parameters: dict[str, Any],
    ledger: list[dict[str, Any]],
    budget: dict[str, Any],
) -> tuple[Any, dict[str, Any]]:
    if len(ledger) >= int(budget["max_requests"]):
        raise RuntimeError("CFBD request ceiling reached")
    cached = cache_path(path, parameters)
    if cached.is_file():
        body = cached.read_bytes()
        payload = json.loads(body.decode("utf-8"))
        receipt = {
            "route": path,
            "parameters": parameters,
            "status": "CACHE_HIT",
            "http_status": 200,
            "request_identity_sha256": sha256_json(
                {"path": path, "parameters": parameters}
            ),
            "receipt_identity": sha256_bytes(body),
            "raw_sha256": sha256_bytes(body),
            "cached": True,
            "retrieved_at_utc": utc_now(),
            "row_count": len(payload) if isinstance(payload, list) else None,
        }
        ledger.append(receipt)
        return payload, receipt
    request = acquisition_request(
        endpoint_id=endpoint_id, path=path, parameters=parameters, run_id="cycle30"
    )
    start = utc_now()
    response = transport(request)
    end = utc_now()
    raw_hash = sha256_bytes(response.body)
    receipt = {
        "route": path,
        "parameters": parameters,
        "status": "HTTP_OK" if 200 <= response.status_code < 300 else "HTTP_ERROR",
        "http_status": response.status_code,
        "request_identity_sha256": sha256_json(
            {"path": path, "parameters": parameters, "run_id": "cycle30"}
        ),
        "receipt_identity": sha256_json(
            {
                "start": start,
                "end": end,
                "raw_sha256": raw_hash,
                "status": response.status_code,
            }
        ),
        "raw_sha256": raw_hash,
        "cached": False,
        "retrieved_at_utc": end,
        "headers_safe": dict(response.headers),
        "row_count": response.row_count,
    }
    ledger.append(receipt)
    if response.status_code >= 300:
        return None, receipt
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(response.body)
    return json.loads(response.body.decode("utf-8")), receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    EXT.mkdir(parents=True, exist_ok=True)
    budget_path = EXT.parent / "CYCLE30_ACQUISITION_BUDGET.json"
    budget_path.write_text(
        json.dumps(BUDGET, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if args.dry_run:
        print("BUDGET_DECLARED", BUDGET["max_requests"])
        return 0
    token = load_dotenv_value(ENV_FILE, "CFBD_API_KEY")
    transport = CFBDTransport(access_token=token)
    ledger: list[dict[str, Any]] = []
    teams: list[dict[str, Any]] = []
    games: list[dict[str, Any]] = []
    coaches: list[dict[str, Any]] = []
    venues: list[dict[str, Any]] = []
    try:
        payload, _ = fetch(
            transport,
            endpoint_id="venues",
            path="/venues",
            parameters={},
            ledger=ledger,
            budget=BUDGET,
        )
        if isinstance(payload, list):
            venues = payload
        for year in BUDGET["years"]:
            for classification in BUDGET["classifications"]:
                payload, _ = fetch(
                    transport,
                    endpoint_id="teams",
                    path="/teams",
                    parameters={"year": year, "classification": classification},
                    ledger=ledger,
                    budget=BUDGET,
                )
                if isinstance(payload, list):
                    for row in payload:
                        teams.append(
                            {
                                **row,
                                "source_year": year,
                                "source_classification": classification,
                            }
                        )
            payload, _ = fetch(
                transport,
                endpoint_id="games",
                path="/games",
                parameters={"year": year, "classification": "fcs"},
                ledger=ledger,
                budget=BUDGET,
            )
            if isinstance(payload, list):
                games.extend(payload)
            if year == 2026:
                payload, _ = fetch(
                    transport,
                    endpoint_id="games",
                    path="/games",
                    parameters={"year": year, "classification": "fbs"},
                    ledger=ledger,
                    budget=BUDGET,
                )
                if isinstance(payload, list):
                    games.extend(payload)
            payload, _ = fetch(
                transport,
                endpoint_id="coaches",
                path="/coaches",
                parameters={"year": year},
                ledger=ledger,
                budget=BUDGET,
            )
            if isinstance(payload, list):
                for row in payload:
                    coaches.append({**row, "source_year": year})
    except RuntimeError as exc:
        print("CEILING", exc)
    out = EXT.parent / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    (out / "CYCLE30_ACQUISITION_LEDGER.json").write_text(
        json.dumps(
            {
                "budget": BUDGET,
                "attempt_count": len(ledger),
                "attempts": ledger,
                "artifact_class": "REAL_EVIDENCE",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    def write_jsonl(name: str, rows: list[dict[str, Any]]) -> None:
        path = out / name
        path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )

    write_jsonl("CFBD_TEAMS_TRANCHE.jsonl", teams)
    write_jsonl("CFBD_GAMES_TRANCHE.jsonl", games)
    write_jsonl("CFBD_COACHES_TRANCHE.jsonl", coaches)
    write_jsonl("CFBD_VENUES.jsonl", venues)
    print(
        "acquired",
        "teams",
        len(teams),
        "fcs_games",
        len(games),
        "coaches",
        len(coaches),
        "venues",
        len(venues),
        "attempts",
        len(ledger),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

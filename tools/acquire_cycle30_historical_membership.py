"""Budgeted Cycle #30 CFBD 1963–2012 program-season membership.

Separate ceiling from the 2013–2023/2026 national tranche.
Classification query parameter is not sent; it does not filter CFBD /teams.
Cached /teams responses are reused. No scrapfly.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
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
    "max_requests": 55,
    "max_retries": 1,
    "concurrency": 1,
    "metered_scraper_credits": 0,
    "years": list(range(1963, 2013)),
    "endpoints": ["/teams"],
    "classifications": [],
    "note": "one /teams?year=YYYY request per year; classification param omitted",
}
ENV_FILE = Path(r"C:\BatteredAggieSyndrome\.env")
RAW = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw")
OUT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cache_path(endpoint: str, parameters: dict[str, Any]) -> Path:
    ident = sha256_json({"endpoint": endpoint, "parameters": parameters})
    safe = endpoint.strip("/").replace("/", "_")
    return RAW / safe / f"{ident}.json"


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
        raise RuntimeError("CFBD 1963-2012 membership request ceiling reached")
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
        endpoint_id=endpoint_id,
        path=path,
        parameters=parameters,
        run_id="cycle30-membership-1963-2012",
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
            {
                "path": path,
                "parameters": parameters,
                "run_id": "cycle30-membership-1963-2012",
            }
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
        "row_count": response.row_count,
    }
    ledger.append(receipt)
    if response.status_code >= 300:
        return None, receipt
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(response.body)
    time.sleep(0.12)
    return json.loads(response.body.decode("utf-8")), receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    budget_path = RAW.parent / "CYCLE30_MEMBERSHIP_1963_2012_BUDGET.json"
    budget_path.write_text(
        json.dumps(BUDGET, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if args.dry_run:
        print("BUDGET_DECLARED", BUDGET["max_requests"], "years", len(BUDGET["years"]))
        return 0
    token = load_dotenv_value(ENV_FILE, "CFBD_API_KEY")
    transport = CFBDTransport(access_token=token)
    ledger: list[dict[str, Any]] = []
    teams: list[dict[str, Any]] = []
    try:
        for year in BUDGET["years"]:
            payload, _ = fetch(
                transport,
                endpoint_id="teams",
                path="/teams",
                parameters={"year": year},
                ledger=ledger,
                budget=BUDGET,
            )
            if isinstance(payload, list):
                for row in payload:
                    teams.append({**row, "source_year": year})
    except RuntimeError as exc:
        print("CEILING", exc)
    (OUT / "CYCLE30_MEMBERSHIP_1963_2012_LEDGER.json").write_text(
        json.dumps(
            {
                "budget": BUDGET,
                "attempt_count": len(ledger),
                "attempts": ledger,
                "years_attempted": sorted(
                    {
                        int(row["parameters"]["year"])
                        for row in ledger
                        if row.get("parameters") and "year" in row["parameters"]
                    }
                ),
                "artifact_class": "REAL_EVIDENCE",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (OUT / "CFBD_TEAMS_1963_2012.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in teams),
        encoding="utf-8",
    )
    print(
        "membership_1963_2012",
        "teams",
        len(teams),
        "attempts",
        len(ledger),
        "years",
        len(BUDGET["years"]),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

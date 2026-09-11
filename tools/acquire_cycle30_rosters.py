"""Budgeted CFBD 2026 roster slice for availability name joins.

Ceiling is declared before any request. Cached responses are reused.
Roster membership is not availability.
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
    "max_requests": 12,
    "max_retries": 0,
    "concurrency": 1,
    "metered_scraper_credits": 0,
    "year": 2026,
    "teams": (
        "Alabama",
        "Georgia",
        "Ohio State",
        "Michigan",
        "Texas A&M",
        "SMU",
        "Florida State",
        "Notre Dame",
        "Oregon",
        "Penn State",
        "Ole Miss",
        "Louisville",
    ),
    "endpoints": ["/roster"],
}
ENV_FILE = Path(r"C:\BatteredAggieSyndrome\.env")
WORK = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work")
EXT = WORK / "raw"


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
        raise RuntimeError("CFBD roster request ceiling reached")
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
        run_id="cycle30-roster-join-slice",
    )
    response = transport(request)
    body = response.body
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(body)
    payload = json.loads(body.decode("utf-8"))
    receipt = {
        "route": path,
        "parameters": parameters,
        "status": "HTTP_OK",
        "http_status": int(response.status_code),
        "request_identity_sha256": sha256_json(
            {"path": path, "parameters": parameters}
        ),
        "receipt_identity": sha256_bytes(body),
        "raw_sha256": sha256_bytes(body),
        "cached": False,
        "retrieved_at_utc": utc_now(),
        "row_count": len(payload) if isinstance(payload, list) else None,
    }
    ledger.append(receipt)
    return payload, receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    EXT.mkdir(parents=True, exist_ok=True)
    (WORK / "CYCLE30_ROSTER_JOIN_BUDGET.json").write_text(
        json.dumps(BUDGET, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if args.dry_run:
        print("BUDGET_DECLARED", BUDGET["max_requests"], "teams", len(BUDGET["teams"]))
        return 0
    access_credential = load_dotenv_value(ENV_FILE, "CFBD_API_KEY")
    transport = CFBDTransport(access_credential)
    ledger: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    try:
        for team in BUDGET["teams"]:
            payload, _ = fetch(
                transport,
                endpoint_id="roster",
                path="/roster",
                parameters={"year": BUDGET["year"], "team": team},
                ledger=ledger,
                budget=BUDGET,
            )
            if not isinstance(payload, list):
                continue
            for item in payload:
                if not isinstance(item, dict):
                    continue
                rows.append(
                    {
                        **item,
                        "source_team": team,
                        "source_year": BUDGET["year"],
                        "source_id": "SRC-002",
                        "artifact_class": "REAL_EVIDENCE",
                        "roster_or_participation_is_not_availability": True,
                    }
                )
    except RuntimeError as exc:
        print("CEILING", exc)
    out = WORK / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    (out / "CYCLE30_ROSTER_JOIN_LEDGER.json").write_text(
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
    (out / "CFBD_ROSTER_JOIN_SLICE.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    print("roster_slice", len(rows), "attempts", len(ledger))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

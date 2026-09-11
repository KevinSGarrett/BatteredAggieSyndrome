"""Cache-first CFBD /teams membership for 2024-2026.

Does not overwrite Cycle30 predecessor membership files. Classification
query parameter is omitted. Cached year files are reused.
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
    "max_requests": 3,
    "max_retries": 1,
    "concurrency": 1,
    "metered_scraper_credits": 0,
    "years": [2024, 2025, 2026],
    "endpoints": ["/teams"],
    "classifications": [],
    "note": "one /teams?year=YYYY request per year; classification param omitted",
}
ENV_FILE = Path(r"C:\BatteredAggieSyndrome\.env")
RAW = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cache_path(endpoint: str, parameters: dict[str, Any]) -> Path:
    ident = sha256_json({"endpoint": endpoint, "parameters": parameters})
    safe = endpoint.strip("/").replace("/", "_")
    return RAW / safe / f"{ident}.json"


def team_id(source_id: Any) -> str:
    return f"SRC-002:TEAM:{source_id}"


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
        raise RuntimeError("CFBD 2024-2026 membership request ceiling reached")
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
        run_id="cycle32-membership-2024-2026",
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
                "run_id": "cycle32-membership-2024-2026",
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


def membership_rows(payload: Any, year: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not isinstance(payload, list):
        return rows
    seen: set[tuple[str, int]] = set()
    for row in payload:
        cls = str(row.get("classification") or "").lower()
        if cls not in {"fbs", "fcs"}:
            continue
        pid = team_id(row.get("id"))
        key = (pid, year)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "program_id": pid,
                "season": year,
                "classification": cls,
                "conference": row.get("conference"),
                "display_name": row.get("school") or row.get("team"),
                "era": "FBS_PLUS_FCS",
                "artifact_class": "REAL_EVIDENCE",
                "source_id": "SRC-002",
                "source_year": year,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    science = OUT / "science"
    science.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        print("BUDGET_DECLARED", BUDGET["max_requests"], "years", BUDGET["years"])
        return 0
    access_credential = load_dotenv_value(ENV_FILE, "CFBD_API_KEY")
    transport = CFBDTransport(access_credential)
    ledger: list[dict[str, Any]] = []
    membership: list[dict[str, Any]] = []
    try:
        for year in BUDGET["years"]:
            payload, receipt = fetch(
                transport,
                endpoint_id="teams",
                path="/teams",
                parameters={"year": year},
                ledger=ledger,
                budget=BUDGET,
            )
            if receipt.get("status") == "HTTP_ERROR":
                continue
            membership.extend(membership_rows(payload, year))
    except RuntimeError as exc:
        print("CEILING", exc)
    (science / "CYCLE32_MEMBERSHIP_2024_2026.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in membership),
        encoding="utf-8",
    )
    summary = {
        "artifact_type": "CYCLE32_MEMBERSHIP_2024_2026",
        "artifact_class": "REAL_EVIDENCE",
        "budget": BUDGET,
        "attempt_count": len(ledger),
        "attempts": [
            {
                "year": row.get("parameters", {}).get("year"),
                "status": row.get("status"),
                "http_status": row.get("http_status"),
                "cached": row.get("cached"),
                "row_count": row.get("row_count"),
                "raw_sha256": row.get("raw_sha256"),
            }
            for row in ledger
        ],
        "membership_row_count": len(membership),
        "years_with_rows": sorted({int(row["season"]) for row in membership}),
        "cfbd_presence_is_not_ncaa_sponsorship_truth": True,
        "predecessor_2013_2023_not_overwritten": True,
    }
    (science / "CYCLE32_MEMBERSHIP_2024_2026_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "membership_row_count": len(membership),
                "years_with_rows": summary["years_with_rows"],
                "attempts": summary["attempts"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

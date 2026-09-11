"""Direct GET of known public availability-report policy/archive pages.

No scrapfly. No private medical detail ingested. Name-only player rows are
not joined to verified roster identities.
"""

from __future__ import annotations

import argparse
import csv
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

from aggie_analytics.cycle30.availability import (  # noqa: E402
    PUBLIC_AVAILABILITY_ROUTES,
    availability_pdf_hrefs,
    extract_candidate_player_rows,
    join_candidates_to_roster,
    pdf_plaintext,
)
from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_json  # noqa: E402

BUDGET = {
    "max_requests": 80,
    "max_retries": 1,
    "concurrency": 1,
    "metered_scraper_credits": 0,
    "route_count": len(PUBLIC_AVAILABILITY_ROUTES) + 1,
}
UA = (
    "BAS-Cycle30-Reconstruction/1.0 "
    "(https://github.com/KevinSGarrett/BatteredAggieSyndrome; "
    "public availability-report policy pages)"
)
UA_BROWSER = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
RAW = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\availability")
OUT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _looks_like_pdf(body: bytes) -> bool:
    return body.startswith(b"%PDF")


def fetch_url(
    uri: str,
    ledger: list[dict[str, Any]],
    budget: dict[str, Any],
    *,
    refresh: bool = False,
) -> bytes:
    if len(ledger) >= int(budget["max_requests"]):
        raise RuntimeError("availability request ceiling reached")
    cache = RAW / f"{sha256_json({'url': uri})}.html"
    wants_pdf = ".pdf" in uri.casefold()
    if cache.is_file() and not refresh:
        body = cache.read_bytes()
        stale_pdf = wants_pdf and not _looks_like_pdf(body)
        if not stale_pdf:
            ledger.append(
                {
                    "route": uri,
                    "status": "CACHE_HIT",
                    "http_status": 200,
                    "request_identity_sha256": sha256_json({"url": uri}),
                    "receipt_identity": sha256_bytes(body),
                    "raw_sha256": sha256_bytes(body),
                    "cached": True,
                    "retrieved_at_utc": utc_now(),
                }
            )
            return body
    accept = (
        "application/pdf,*/*;q=0.8"
        if wants_pdf
        else "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"
    )
    user_agents = [UA_BROWSER, UA] if wants_pdf else [UA, UA_BROWSER]
    body = b""
    status = 0
    start = utc_now()
    for user_agent in user_agents:
        request = urllib.request.Request(
            uri,
            headers={
                "User-Agent": user_agent,
                "Accept": accept,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
                status = int(response.status)
        except urllib.error.HTTPError as exc:
            body = exc.read() or b""
            status = int(exc.code)
        except urllib.error.URLError as exc:
            body = str(exc.reason).encode("utf-8")
            status = 0
        time.sleep(0.2)
        if wants_pdf:
            if _looks_like_pdf(body):
                break
            continue
        if body:
            break
    end = utc_now()
    raw_hash = sha256_bytes(body) if body else "empty"
    ledger.append(
        {
            "route": uri,
            "status": "HTTP_OK" if 200 <= status < 300 else "HTTP_ERROR",
            "http_status": status,
            "request_identity_sha256": sha256_json({"url": uri}),
            "receipt_identity": sha256_json(
                {"start": start, "end": end, "raw_sha256": raw_hash, "status": status}
            ),
            "raw_sha256": raw_hash,
            "cached": False,
            "pdf_magic": _looks_like_pdf(body),
            "retrieved_at_utc": end,
        }
    )
    RAW.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(body)
    return body


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Bypass HTML cache for a fresh public-route attempt",
    )
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (RAW.parent.parent / "CYCLE30_AVAILABILITY_BUDGET.json").write_text(
        json.dumps(BUDGET, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if args.dry_run:
        print("BUDGET_DECLARED", BUDGET["max_requests"])
        return 0
    ledger: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    extra_routes = (
        {
            "source_id": "SRC-017-LIVE",
            "conference": "SEC",
            "uri": "https://www.secsports.com/fbreports",
        },
    )
    for route in [*PUBLIC_AVAILABILITY_ROUTES, *extra_routes]:
        uri = route["uri"]
        body = fetch_url(uri, ledger, BUDGET, refresh=args.refresh)
        receipt = ledger[-1]
        text = body.decode("utf-8", "replace").casefold()
        looks_like_report = any(
            token in text
            for token in (
                "availability report",
                "player availability",
                "gameday availability",
                "fb reports",
                "fbreports",
            )
        )
        decoded = body.decode("utf-8", "replace")
        candidates = extract_candidate_player_rows(
            decoded, source_id=route["source_id"], uri=uri
        )
        for pdf_uri in availability_pdf_hrefs(decoded, page_uri=uri, limit=8):
            try:
                pdf_body = fetch_url(pdf_uri, ledger, BUDGET, refresh=args.refresh)
            except RuntimeError:
                break
            candidates.extend(
                extract_candidate_player_rows(
                    pdf_plaintext(pdf_body) or pdf_body.decode("utf-8", "replace"),
                    source_id=route["source_id"],
                    uri=pdf_uri,
                )
            )
        rows.append(
            {
                "source_id": route["source_id"],
                "conference": route["conference"],
                "uri": uri,
                "attempt_count": 1,
                "http_status": receipt["http_status"],
                "receipt_identity": receipt["receipt_identity"],
                "disposition": (
                    "ATTEMPTED_WITH_EVIDENCE"
                    if receipt["http_status"] and int(receipt["http_status"]) < 400
                    else "ACQUISITION_FAILED"
                ),
                "page_kind": "POLICY_OR_ARCHIVE_PAGE",
                "looks_like_availability_surface": looks_like_report,
                "player_rows_extracted": len(candidates),
                "candidate_player_rows": candidates,
                "joined_to_verified_roster": False,
                "private_medical_detail_ingested": False,
                "no_report_means": "UNKNOWN",
                "artifact_class": "REAL_EVIDENCE",
                "owner": "BAT-324",
                "co_owners": ["BAT-328", "BAT-703", "CFIP-23"],
            }
        )
    (OUT / "CYCLE30_AVAILABILITY_LEDGER.json").write_text(
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
    (OUT / "AVAILABILITY_ROUTE_ATTEMPTS.jsonl").write_text(
        "".join(
            json.dumps(
                {
                    key: value
                    for key, value in row.items()
                    if key != "candidate_player_rows"
                },
                sort_keys=True,
            )
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )
    candidates = [
        item for row in rows for item in (row.get("candidate_player_rows") or [])
    ]
    roster_rows: list[dict[str, Any]] = []
    people_csv = Path(
        r"C:\BatteredAggieSyndrome.data\canonical\BAT-388\sha256"
        r"\0ab6acafbe350a4958a5fca1c02a9c51463ab8a93ecc173a57b9fd925bf2198d"
        r"\canonical_people_registry.csv"
    )
    if people_csv.is_file():
        with people_csv.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                roster_rows.append(row)
    cfbd_roster = OUT / "CFBD_ROSTER_JOIN_SLICE.jsonl"
    if cfbd_roster.is_file():
        for line in cfbd_roster.read_text(encoding="utf-8").splitlines():
            if line.strip():
                roster_rows.append(json.loads(line))
    joined = join_candidates_to_roster(candidates, roster_rows)
    (OUT / "AVAILABILITY_CANDIDATE_PLAYER_ROWS.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in joined["rows"]),
        encoding="utf-8",
    )
    (OUT / "AVAILABILITY_CANDIDATE_PLAYER_SUMMARY.json").write_text(
        json.dumps(
            {key: value for key, value in joined.items() if key != "rows"},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        "availability",
        "routes",
        len(rows),
        "attempts",
        len(ledger),
        "http_ok",
        sum(1 for row in rows if int(row["http_status"] or 0) == 200),
        "candidates",
        len(candidates),
        "joined",
        joined["joined_to_verified_roster"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

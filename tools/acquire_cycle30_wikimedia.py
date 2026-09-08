"""Revision-bound Wikimedia discovery for current national coaching pages.

Declared ceiling before any request. Not PIT. No email/phone ingestion.
Official HTML staff directories remain separately NOT_ATTEMPTED under scraper=0.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.coaching import (  # noqa: E402
    parse_wikimedia_infobox,
    redact_personal_contact,
    reject_wikimedia_as_pit,
)
from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_json  # noqa: E402

BUDGET = {
    "max_requests": 600,
    "max_retries": 1,
    "concurrency": 1,
    "metered_scraper_credits": 0,
    "route": "mediawiki_api",
    "pit_admitted": False,
}
API = "https://en.wikipedia.org/w/api.php"
UA = (
    "BAS-Cycle30-Reconstruction/1.0 "
    "(https://github.com/KevinSGarrett/BatteredAggieSyndrome; "
    "revision-bound coaching discovery)"
)
ART_POP = (
    ROOT
    / "artifacts"
    / "scientific_integrity"
    / "cycle30"
    / "CURRENT_2026_DIVISION_I_PROGRAM_POPULATION.json"
)
EXT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_json(url: str, ledger: list[dict[str, Any]], budget: dict[str, Any]) -> Any:
    if len(ledger) >= int(budget["max_requests"]):
        raise RuntimeError("Wikimedia request ceiling reached")
    cache = EXT / "raw" / "wikimedia" / f"{sha256_json({'url': url})}.json"
    if cache.is_file():
        body = cache.read_bytes()
        ledger.append(
            {
                "route": url.split("?", 1)[0],
                "status": "CACHE_HIT",
                "http_status": 200,
                "request_identity_sha256": sha256_json({"url": url}),
                "receipt_identity": sha256_bytes(body),
                "raw_sha256": sha256_bytes(body),
                "cached": True,
                "retrieved_at_utc": utc_now(),
            }
        )
        return json.loads(body.decode("utf-8"))
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    start = utc_now()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            status = int(response.status)
    except urllib.error.HTTPError as exc:
        body = exc.read() or b""
        status = int(exc.code)
        ledger.append(
            {
                "route": url.split("?", 1)[0],
                "status": "HTTP_ERROR",
                "http_status": status,
                "request_identity_sha256": sha256_json({"url": url}),
                "receipt_identity": sha256_bytes(body) if body else "empty",
                "raw_sha256": sha256_bytes(body) if body else "empty",
                "cached": False,
                "retrieved_at_utc": utc_now(),
            }
        )
        raise
    time.sleep(0.15)
    end = utc_now()
    ledger.append(
        {
            "route": url.split("?", 1)[0],
            "status": "HTTP_OK" if 200 <= status < 300 else "HTTP_ERROR",
            "http_status": status,
            "request_identity_sha256": sha256_json({"url": url}),
            "receipt_identity": sha256_json(
                {"start": start, "end": end, "raw_sha256": sha256_bytes(body)}
            ),
            "raw_sha256": sha256_bytes(body),
            "cached": False,
            "retrieved_at_utc": end,
        }
    )
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(body)
    return json.loads(body.decode("utf-8"))


def search_and_parse(school: str, ledger: list[dict[str, Any]]) -> dict[str, Any]:
    query = f"{school} football"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": "1",
        "format": "json",
    }
    search_url = f"{API}?{urllib.parse.urlencode(params)}"
    payload = fetch_json(search_url, ledger, BUDGET)
    hits = (payload.get("query") or {}).get("search") or []
    if not hits:
        return {
            "school": school,
            "status": "NO_SEARCH_HIT",
            "pit_admitted": False,
            "episodes": [],
        }
    title = str(hits[0].get("title") or "")
    page_params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "ids|timestamp|content",
        "rvslots": "main",
        "titles": title,
        "format": "json",
    }
    page = fetch_json(f"{API}?{urllib.parse.urlencode(page_params)}", ledger, BUDGET)
    pages = (page.get("query") or {}).get("pages") or {}
    page_obj = next(iter(pages.values()), {})
    revisions = page_obj.get("revisions") or []
    if not revisions:
        return {
            "school": school,
            "status": "NO_REVISION",
            "title": title,
            "pit_admitted": False,
            "episodes": [],
        }
    revision = revisions[0]
    revision_id = str(revision.get("revid") or "")
    wikitext = redact_personal_contact(
        str((revision.get("slots") or {}).get("main", {}).get("*") or "")
    )
    reject_wikimedia_as_pit(True, False)
    episodes = parse_wikimedia_infobox(
        wikitext, revision_id=revision_id, page_title=title
    )
    return {
        "school": school,
        "status": "REVISION_BOUND",
        "title": title,
        "wikimedia_revision": revision_id,
        "revision_timestamp": revision.get("timestamp"),
        "pit_admitted": False,
        "episodes": episodes,
        "artifact_class": "REAL_EVIDENCE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    budget_path = EXT / "CYCLE30_WIKIMEDIA_BUDGET.json"
    EXT.mkdir(parents=True, exist_ok=True)
    budget_path.write_text(
        json.dumps(BUDGET, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    programs = json.loads(ART_POP.read_text(encoding="utf-8")).get("programs") or []
    if args.limit:
        programs = programs[: args.limit]
    ledger: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    out = EXT / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    jsonl_path = out / "WIKIMEDIA_CURRENT_STAFF_CANDIDATES.jsonl"
    jsonl_path.write_text("", encoding="utf-8")
    try:
        for program in programs:
            school = str(program.get("display_name") or "")
            try:
                row = search_and_parse(school, ledger)
            except RuntimeError:
                raise
            except Exception as exc:  # noqa: BLE001
                row = {
                    "school": school,
                    "status": f"ACQUISITION_FAILED:{type(exc).__name__}",
                    "pit_admitted": False,
                    "episodes": [],
                    "artifact_class": "BLOCKER_METADATA",
                }
            row["program_id"] = program.get("program_id")
            rows.append(row)
            with jsonl_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    except RuntimeError as exc:
        print("CEILING", exc)
    (out / "CYCLE30_WIKIMEDIA_LEDGER.json").write_text(
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
    print(
        "wikimedia",
        "programs",
        len(rows),
        "attempts",
        len(ledger),
        "episodes",
        sum(len(row.get("episodes") or []) for row in rows),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

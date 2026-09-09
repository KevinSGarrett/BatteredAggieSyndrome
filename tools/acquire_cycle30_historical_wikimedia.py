"""Revision-bound Wikimedia national team-season staff tranche.

Cache-first. Live ceiling declared before requests. Completes 1963–2026
season pages until the ceiling; remaining cells stay queued. Not PIT.
Wikipedia is a candidate source, not official confirmation.
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
    historical_season_page_title,
    parse_wikimedia_infobox,
    redact_personal_contact,
    reject_wikimedia_as_pit,
)
from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_json  # noqa: E402

BUDGET = {
    "max_requests": 10000,
    "max_retries": 1,
    "concurrency": 1,
    "metered_scraper_credits": 0,
    "route": "mediawiki_api",
    "years": list(range(1963, 2027)),
    "sleep_seconds": 0.35,
    "pit_admitted": False,
    "wikipedia_is_not_official_confirmation": True,
}
API = "https://en.wikipedia.org/w/api.php"
UA = (
    "BAS-Cycle30-Reconstruction/1.0 "
    "(https://github.com/KevinSGarrett/BatteredAggieSyndrome; "
    "revision-bound historical coaching discovery)"
)
EXT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work")
OUT = EXT / "outputs"
RAW = EXT / "raw" / "wikimedia"


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


def fetch_json(url: str, ledger: list[dict[str, Any]], budget: dict[str, Any]) -> Any:
    cache = RAW / f"{sha256_json({'url': url})}.json"
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
    live = sum(1 for item in ledger if not item.get("cached"))
    if live >= int(budget["max_requests"]):
        raise RuntimeError("historical Wikimedia request ceiling reached")
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
    time.sleep(0.35)
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


def fetch_title(title: str, ledger: list[dict[str, Any]]) -> dict[str, Any]:
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "ids|timestamp|content",
        "rvslots": "main",
        "titles": title,
        "redirects": "1",
        "format": "json",
    }
    page = fetch_json(f"{API}?{urllib.parse.urlencode(params)}", ledger, BUDGET)
    pages = (page.get("query") or {}).get("pages") or {}
    page_obj = next(iter(pages.values()), {})
    if page_obj.get("missing") is not None:
        return {
            "title": title,
            "status": "PAGE_MISSING",
            "pit_admitted": False,
            "episodes": [],
        }
    revisions = page_obj.get("revisions") or []
    if not revisions:
        return {
            "title": title,
            "status": "NO_REVISION",
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
        wikitext,
        revision_id=revision_id,
        page_title=str(page_obj.get("title") or title),
    )
    return {
        "title": str(page_obj.get("title") or title),
        "requested_title": title,
        "status": "REVISION_BOUND",
        "wikimedia_revision": revision_id,
        "revision_timestamp": revision.get("timestamp"),
        "pit_admitted": False,
        "episodes": episodes,
        "artifact_class": "REAL_EVIDENCE",
    }


def search_season_title(
    school: str, year: int, ledger: list[dict[str, Any]]
) -> str | None:
    """Resolve a season page when the guessed title is missing. Not a vacancy."""

    query = f"{year} {school} football team"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": "8",
        "format": "json",
    }
    payload = fetch_json(f"{API}?{urllib.parse.urlencode(params)}", ledger, BUDGET)
    for hit in (payload.get("query") or {}).get("search") or []:
        title = str(hit.get("title") or "").strip()
        lowered = title.casefold()
        if title.startswith(str(year)) and "football" in lowered:
            return title
    return None


def fetch_season(
    *,
    school: str,
    year: int,
    guessed_title: str,
    ledger: list[dict[str, Any]],
) -> dict[str, Any]:
    parsed = fetch_title(guessed_title, ledger)
    if parsed.get("status") != "PAGE_MISSING":
        return parsed
    alt = search_season_title(school, year, ledger)
    if not alt or alt == guessed_title:
        return parsed
    return fetch_title(alt, ledger)


def write_row(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def coverage_gaps(rows: list[dict[str, Any]], expected_n: int) -> list[int]:
    by_year: dict[int, int] = {}
    for row in rows:
        year = int(row.get("season") or 0)
        if year:
            by_year[year] = by_year.get(year, 0) + 1
    return [year for year in range(1963, 2027) if by_year.get(year, 0) < expected_n]


def reparse_existing(
    jsonl_path: Path, ledger: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    old_rows = load_jsonl(jsonl_path)
    rewritten: list[dict[str, Any]] = []
    for row in old_rows:
        title = str(row.get("title") or row.get("requested_title") or "")
        if row.get("status") in {"REVISION_BOUND", "NO_REVISION"} and title:
            parsed = fetch_title(title, ledger)
            row = {
                **row,
                **parsed,
                "program_id": row.get("program_id"),
                "school": row.get("school"),
                "season": row.get("season"),
                "current_title": row.get("current_title"),
                "pit_admitted": False,
            }
        rewritten.append(row)
    jsonl_path.write_text("", encoding="utf-8")
    for row in rewritten:
        write_row(jsonl_path, row)
    return rewritten


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--reparse", action="store_true")
    parser.add_argument("--retry-missing", action="store_true")
    parser.add_argument("--max-requests", type=int, default=0)
    parser.add_argument("--year-start", type=int, default=1963)
    parser.add_argument("--year-end", type=int, default=2026)
    args = parser.parse_args()
    if args.max_requests:
        BUDGET["max_requests"] = args.max_requests
    years = [
        year for year in BUDGET["years"] if args.year_start <= year <= args.year_end
    ]
    years = sorted(years, key=lambda year: (0 if year >= 2013 else 1, -year))
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (EXT / "CYCLE30_HISTORICAL_WIKIMEDIA_BUDGET.json").write_text(
        json.dumps({**BUDGET, "years": years}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    current = load_jsonl(OUT / "WIKIMEDIA_CURRENT_STAFF_CANDIDATES.jsonl")
    if args.limit:
        current = current[: args.limit]
    ledger: list[dict[str, Any]] = []
    jsonl_path = OUT / "WIKIMEDIA_HISTORICAL_STAFF_CANDIDATES.jsonl"
    if args.replace or not jsonl_path.is_file():
        jsonl_path.write_text("", encoding="utf-8")
    if args.reparse and jsonl_path.is_file():
        try:
            reparse_existing(jsonl_path, ledger)
        except RuntimeError as exc:
            print("CEILING", exc)
    if args.retry_missing and jsonl_path.is_file():
        try:
            rewritten = []
            for row in load_jsonl(jsonl_path):
                year = int(row.get("season") or 0)
                if (
                    row.get("status") == "PAGE_MISSING"
                    and args.year_start <= year <= args.year_end
                ):
                    parsed = fetch_season(
                        school=str(row.get("school") or ""),
                        year=int(row.get("season") or 0),
                        guessed_title=str(
                            row.get("title") or row.get("requested_title") or ""
                        ),
                        ledger=ledger,
                    )
                    row = {
                        **row,
                        **parsed,
                        "program_id": row.get("program_id"),
                        "school": row.get("school"),
                        "season": row.get("season"),
                        "current_title": row.get("current_title"),
                        "pit_admitted": False,
                    }
                rewritten.append(row)
            jsonl_path.write_text("", encoding="utf-8")
            for row in rewritten:
                write_row(jsonl_path, row)
        except RuntimeError as exc:
            print("CEILING", exc)
    existing = {
        (str(row.get("program_id")), int(row.get("season") or 0))
        for row in load_jsonl(jsonl_path)
    }
    new_rows = 0
    try:
        for year in years:
            for program in current:
                current_title = str(program.get("title") or "")
                if (str(program.get("program_id")), year) in existing:
                    continue
                season_title = historical_season_page_title(current_title, year)
                if not season_title:
                    row = {
                        "program_id": program.get("program_id"),
                        "school": program.get("school"),
                        "season": year,
                        "status": "NO_CURRENT_TITLE",
                        "pit_admitted": False,
                        "episodes": [],
                    }
                    write_row(jsonl_path, row)
                    existing.add((str(program.get("program_id")), year))
                    new_rows += 1
                    continue
                try:
                    parsed = fetch_season(
                        school=str(program.get("school") or ""),
                        year=year,
                        guessed_title=season_title,
                        ledger=ledger,
                    )
                except RuntimeError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    parsed = {
                        "title": season_title,
                        "status": f"ACQUISITION_FAILED:{type(exc).__name__}",
                        "pit_admitted": False,
                        "episodes": [],
                    }
                row = {
                    **parsed,
                    "program_id": program.get("program_id"),
                    "school": program.get("school"),
                    "season": year,
                    "current_title": current_title,
                    "pit_admitted": False,
                }
                write_row(jsonl_path, row)
                existing.add((str(program.get("program_id")), year))
                new_rows += 1
    except RuntimeError as exc:
        print("CEILING", exc)
    all_rows = load_jsonl(jsonl_path)
    remaining = coverage_gaps(all_rows, len(current) or 266)
    (OUT / "CYCLE30_HISTORICAL_WIKIMEDIA_LEDGER.json").write_text(
        json.dumps(
            {
                "budget": {**BUDGET, "years": years},
                "attempt_count": len(ledger),
                "page_count": len(all_rows),
                "new_rows_this_run": new_rows,
                "remaining_years_incomplete": remaining,
                "remaining_year_count": len(remaining),
                "artifact_class": "REAL_EVIDENCE",
                "pit_admitted": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        "historical_wikimedia",
        "pages",
        len(all_rows),
        "new",
        new_rows,
        "attempts",
        len(ledger),
        "episodes",
        sum(len(row.get("episodes") or []) for row in all_rows),
        "bound",
        sum(1 for row in all_rows if row.get("status") == "REVISION_BOUND"),
        "incomplete_years",
        len(remaining),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

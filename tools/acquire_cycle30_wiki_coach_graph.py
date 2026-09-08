"""Program-category × coach-career reconstruction. Candidate history, not PIT.

Cache-first MediaWiki categorymembers + coach infobox pages. Live ceiling
declared before requests. Does not infer HC from a missing parenthetical.
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
    career_episode_seasons,
    parse_infobox_college_coach,
    program_coach_category_title,
    redact_personal_contact,
    reject_wikimedia_as_pit,
)
from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_json  # noqa: E402

BUDGET = {
    "max_requests": 4000,
    "max_retries": 1,
    "concurrency": 1,
    "metered_scraper_credits": 0,
    "route": "mediawiki_api",
    "sleep_seconds": 0.35,
    "pit_admitted": False,
    "wikipedia_is_not_official_confirmation": True,
    "category_is_discovery_not_proof": True,
}
API = "https://en.wikipedia.org/w/api.php"
UA = (
    "BAS-Cycle30-Reconstruction/1.0 "
    "(https://github.com/KevinSGarrett/BatteredAggieSyndrome; "
    "revision-bound coaching career discovery)"
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


def write_row(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


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
        raise RuntimeError("coach-graph Wikimedia request ceiling reached")
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
    time.sleep(float(budget["sleep_seconds"]))
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


def category_members(title: str, ledger: list[dict[str, Any]]) -> list[str]:
    members: list[str] = []
    cont = ""
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": title,
            "cmnamespace": "0",
            "cmlimit": "500",
            "format": "json",
        }
        if cont:
            params["cmcontinue"] = cont
        payload = fetch_json(f"{API}?{urllib.parse.urlencode(params)}", ledger, BUDGET)
        batch = (payload.get("query") or {}).get("categorymembers") or []
        for item in batch:
            name = str(item.get("title") or "")
            if name and not name.startswith("Category:"):
                members.append(name)
        cont = str((payload.get("continue") or {}).get("cmcontinue") or "")
        if not cont:
            break
    return members


def fetch_coach_page(title: str, ledger: list[dict[str, Any]]) -> dict[str, Any]:
    params = {
        "action": "query",
        "prop": "revisions|pageprops",
        "rvprop": "ids|timestamp|content",
        "rvslots": "main",
        "ppprop": "wikibase_item",
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
    episodes = parse_infobox_college_coach(
        wikitext,
        revision_id=revision_id,
        page_title=str(page_obj.get("title") or title),
    )
    props = page_obj.get("pageprops") or {}
    return {
        "title": str(page_obj.get("title") or title),
        "requested_title": title,
        "pageid": page_obj.get("pageid"),
        "wikidata_qid": props.get("wikibase_item"),
        "status": "REVISION_BOUND",
        "wikimedia_revision": revision_id,
        "revision_timestamp": revision.get("timestamp"),
        "pit_admitted": False,
        "episodes": episodes,
        "artifact_class": "REAL_EVIDENCE",
    }


def expand_seasons(coach_row: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    person = str(coach_row.get("title") or "")
    for episode in coach_row.get("episodes") or []:
        if str(episode.get("role") or "") == "UNKNOWN":
            continue
        for year in career_episode_seasons(episode, through_year=2026):
            if year < 1963 or year > 2026:
                continue
            out.append(
                {
                    "person": episode.get("person") or person,
                    "program_raw": episode.get("program_raw"),
                    "season": year,
                    "role": episode.get("role"),
                    "raw_title": episode.get("raw_title"),
                    "source_year_text": episode.get("source_year_text"),
                    "ongoing": episode.get("ongoing"),
                    "wikimedia_revision": episode.get("wikimedia_revision"),
                    "wikidata_qid": coach_row.get("wikidata_qid"),
                    "pageid": coach_row.get("pageid"),
                    "source": "WIKIMEDIA_COACH_CAREER",
                    "pit_admitted": False,
                    "evidence_class": "RETROSPECTIVE_CANDIDATE_ONLY",
                }
            )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (EXT / "CYCLE30_WIKI_COACH_GRAPH_BUDGET.json").write_text(
        json.dumps(BUDGET, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    current = load_jsonl(OUT / "WIKIMEDIA_CURRENT_STAFF_CANDIDATES.jsonl")
    if args.limit:
        current = current[: args.limit]
    cat_path = OUT / "WIKIMEDIA_PROGRAM_COACH_CATEGORIES.jsonl"
    coach_path = OUT / "WIKIMEDIA_COACH_CAREER_PAGES.jsonl"
    season_path = OUT / "WIKIMEDIA_CAREER_SEASON_EPISODES.jsonl"
    cat_path.write_text("", encoding="utf-8")
    coach_path.write_text("", encoding="utf-8")
    season_path.write_text("", encoding="utf-8")
    ledger: list[dict[str, Any]] = []
    seen_coaches: set[str] = set()
    coach_count = 0
    season_count = 0
    try:
        for program in current:
            category = program_coach_category_title(str(program.get("title") or ""))
            members: list[str] = []
            status = "NO_CURRENT_TITLE"
            if category:
                try:
                    members = category_members(category, ledger)
                    status = "CATEGORY_ENUMERATED"
                except RuntimeError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    status = f"ACQUISITION_FAILED:{type(exc).__name__}"
            write_row(
                cat_path,
                {
                    "program_id": program.get("program_id"),
                    "school": program.get("school"),
                    "category": category,
                    "status": status,
                    "member_count": len(members),
                    "members": members,
                    "pit_admitted": False,
                    "evidence_class": "DISCOVERY_ONLY",
                },
            )
            for title in members:
                if title in seen_coaches:
                    continue
                seen_coaches.add(title)
                try:
                    parsed = fetch_coach_page(title, ledger)
                except RuntimeError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    parsed = {
                        "title": title,
                        "status": f"ACQUISITION_FAILED:{type(exc).__name__}",
                        "pit_admitted": False,
                        "episodes": [],
                    }
                parsed["source_program_id"] = program.get("program_id")
                write_row(coach_path, parsed)
                coach_count += 1
                for season_row in expand_seasons(parsed):
                    write_row(season_path, season_row)
                    season_count += 1
    except RuntimeError as exc:
        print("CEILING", exc)
    (OUT / "CYCLE30_WIKI_COACH_GRAPH_LEDGER.json").write_text(
        json.dumps(
            {
                "budget": BUDGET,
                "attempt_count": len(ledger),
                "coach_pages": coach_count,
                "season_episodes": season_count,
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
        "wiki_coach_graph",
        "coaches",
        coach_count,
        "seasons",
        season_count,
        "attempts",
        len(ledger),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

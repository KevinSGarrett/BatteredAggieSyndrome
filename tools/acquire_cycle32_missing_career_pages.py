"""Cache-first Wikipedia career pages for current official occupants.

Writes Cycle32 successors. Does not overwrite predecessor career files.
Search hits are not identity. Wikipedia is not factual verification or PIT.
"""

from __future__ import annotations

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
    parse_infobox_college_coach,
    redact_personal_contact,
    reject_wikimedia_as_pit,
    wiki_career_title_matches_person,
)
from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_json  # noqa: E402

PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)
RAW = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\wikimedia")
API = "https://en.wikipedia.org/w/api.php"
UA = (
    "BAS-Cycle32-Reconstruction/1.0 "
    "(https://github.com/KevinSGarrett/BatteredAggieSyndrome; "
    "revision-bound coaching career discovery)"
)
BUDGET = {
    "max_requests": 1000,
    "sleep_seconds": 0.2,
    "pit_admitted": False,
    "wikipedia_is_not_factual_verification": True,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def fetch_json(url: str, ledger: list[dict[str, Any]]) -> Any:
    cache = RAW / f"{sha256_json({'url': url})}.json"
    if cache.is_file():
        body = cache.read_bytes()
        ledger.append(
            {
                "route": url.split("?", 1)[0],
                "status": "CACHE_HIT",
                "http_status": 200,
                "cached": True,
                "raw_sha256": sha256_bytes(body),
                "retrieved_at_utc": utc_now(),
            }
        )
        return json.loads(body.decode("utf-8"))
    live = sum(1 for item in ledger if not item.get("cached"))
    if live >= int(BUDGET["max_requests"]):
        raise RuntimeError("Cycle32 career Wikimedia request ceiling reached")
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
                "cached": False,
                "raw_sha256": sha256_bytes(body) if body else "empty",
                "retrieved_at_utc": utc_now(),
            }
        )
        raise
    time.sleep(float(BUDGET["sleep_seconds"]))
    ledger.append(
        {
            "route": url.split("?", 1)[0],
            "status": "HTTP_OK" if 200 <= status < 300 else "HTTP_ERROR",
            "http_status": status,
            "cached": False,
            "raw_sha256": sha256_bytes(body),
            "retrieved_at_utc": utc_now(),
            "started_at_utc": start,
        }
    )
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(body)
    return json.loads(body.decode("utf-8"))


def search_titles(person: str, ledger: list[dict[str, Any]]) -> list[str]:
    params = {
        "action": "query",
        "list": "search",
        "srsearch": f"{person} college football coach",
        "srlimit": "5",
        "srnamespace": "0",
        "format": "json",
    }
    payload = fetch_json(f"{API}?{urllib.parse.urlencode(params)}", ledger)
    hits = (payload.get("query") or {}).get("search") or []
    titles = [str(item.get("title") or "") for item in hits if item.get("title")]
    if person not in titles:
        titles.insert(0, person)
    return titles


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
    page = fetch_json(f"{API}?{urllib.parse.urlencode(params)}", ledger)
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
    resolved = str(page_obj.get("title") or title)
    episodes = parse_infobox_college_coach(
        wikitext, revision_id=revision_id, page_title=resolved
    )
    props = page_obj.get("pageprops") or {}
    return {
        "title": resolved,
        "requested_title": title,
        "pageid": page_obj.get("pageid"),
        "wikidata_qid": props.get("wikibase_item"),
        "status": "REVISION_BOUND",
        "wikimedia_revision": revision_id,
        "revision_timestamp": revision.get("timestamp"),
        "pit_admitted": False,
        "episodes": episodes,
        "artifact_class": "REAL_EVIDENCE",
        "wikipedia_is_not_factual_verification": True,
    }


def main() -> int:
    occupants = load_jsonl(OUT / "science" / "CYCLE32_CURRENT_STAFF_CAREER_ROUNDTRIP.jsonl")
    missing = [
        row
        for row in occupants
        if str(row.get("status") or "") == "NO_CACHED_CAREER_PAGE"
    ]
    seen_people: set[str] = set()
    ledger: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    matched = 0
    unmatched = 0
    ceiling = False
    try:
        for occupant in missing:
            person = str(occupant.get("person") or "").strip()
            key = person.casefold()
            if not person or key in seen_people:
                continue
            seen_people.add(key)
            bound = None
            for title in search_titles(person, ledger):
                if not wiki_career_title_matches_person(title, person):
                    continue
                page = fetch_coach_page(title, ledger)
                if page.get("status") != "REVISION_BOUND":
                    continue
                resolved = str(page.get("title") or title)
                if not wiki_career_title_matches_person(resolved, person):
                    continue
                bound = {
                    **page,
                    "occupant_person": person,
                    "program_id": occupant.get("program_id"),
                }
                break
            if bound:
                pages.append(bound)
                matched += 1
            else:
                unmatched += 1
                pages.append(
                    {
                        "occupant_person": person,
                        "program_id": occupant.get("program_id"),
                        "status": "NO_MATCHING_WIKI_TITLE",
                        "pit_admitted": False,
                        "episodes": [],
                        "wikipedia_is_not_factual_verification": True,
                    }
                )
    except RuntimeError:
        ceiling = True
    science = OUT / "science"
    science.mkdir(parents=True, exist_ok=True)
    path = science / "CYCLE32_WIKI_CAREER_PAGES_SUCCESSOR.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in pages:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")
    summary = {
        "artifact_type": "CYCLE32_WIKI_CAREER_PAGES_SUCCESSOR",
        "as_of_utc": utc_now(),
        "missing_occupants_unique": len(seen_people),
        "revision_bound_matches": matched,
        "unmatched": unmatched,
        "request_ceiling_reached": ceiling,
        "live_requests": sum(1 for row in ledger if not row.get("cached")),
        "cache_hits": sum(1 for row in ledger if row.get("cached")),
        "pit_admitted": False,
        "wikipedia_is_not_factual_verification": True,
        "predecessor_not_overwritten": str(PRED / "WIKIMEDIA_COACH_CAREER_PAGES.jsonl"),
    }
    (science / "CYCLE32_WIKI_CAREER_PAGES_SUCCESSOR.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

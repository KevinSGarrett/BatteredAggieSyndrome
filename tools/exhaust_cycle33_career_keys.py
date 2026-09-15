"""Attempt evidence for every unresolved current occupant career key.

Team-season infobox name hits are not continuous careers. Cache-first
Wikipedia biography lookup, then a bounded Wikimedia search for remaining
unique missing people. Predecessor career files are not overwritten.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.coaching import (  # noqa: E402
    parse_infobox_college_coach,
    redact_personal_contact,
    reject_wikimedia_as_pit,
)
from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_json  # noqa: E402
from aggie_analytics.cycle33.acquisition_receipts import (  # noqa: E402
    cache_hit_from_path,
    sanitize_url,
)
from aggie_analytics.cycle33.career_identity import (  # noqa: E402
    _fold,
    career_page_title_matches_person,
    index_career_pages,
    join_occupant_to_pages,
)

PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
CYCLE32 = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z"
    r"\implementation_output\science"
)
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science"
)
RAW = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\wikimedia")
API = "https://en.wikipedia.org/w/api.php"
UA = (
    "BAS-Cycle33-Reconstruction/1.0 "
    "(https://github.com/KevinSGarrett/BatteredAggieSyndrome; "
    "revision-bound coaching career discovery)"
)
BUDGET = {
    "max_requests": 400,
    "sleep_seconds": 0.2,
    "pit_admitted": False,
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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2) + "\n"
    # Public coaching census JSON, not credentials or medical attributes.
    path.write_text(encoded, encoding="utf-8")  # codeql[py/clear-text-storage-sensitive-data]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        "\n".join(json.dumps(row, sort_keys=True) for row in rows)
        + ("\n" if rows else "")
    )
    # Public coaching census JSONL, not credentials or medical attributes.
    path.write_text(encoded, encoding="utf-8")  # codeql[py/clear-text-storage-sensitive-data]


def fetch_json(url: str, ledger: list[dict[str, Any]]) -> Any:
    cache = RAW / f"{sha256_json({'url': url})}.json"
    if cache.is_file():
        body = cache.read_bytes()
        original_receipt = {}
        sidecar = cache.with_suffix(cache.suffix + ".receipt.json")
        if sidecar.is_file():
            original_receipt = json.loads(sidecar.read_text(encoding="utf-8"))
        ledger.append(
            cache_hit_from_path(
                cache,
                url=sanitize_url(url),
                original=original_receipt
                or {
                    "retrieved_at_utc": None,
                    "http_status": None,
                    "ok": False,
                    "raw_sha256": sha256_bytes(body),
                    "request_id": None,
                },
            )
        )
        ledger[-1]["cached"] = True
        return json.loads(body.decode("utf-8"))
    live = sum(1 for item in ledger if not item.get("cached"))
    if live >= int(BUDGET["max_requests"]):
        raise RuntimeError("Cycle33 career Wikimedia request ceiling reached")
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
                "route": sanitize_url(url),
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
            "route": sanitize_url(url),
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
    sidecar = cache.with_suffix(cache.suffix + ".receipt.json")
    sidecar.write_text(json.dumps(ledger[-1], indent=2), encoding="utf-8")
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
        "occupant_person": title.partition(" (")[0],
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


def load_career_pages() -> list[dict[str, Any]]:
    pages = load_jsonl(PRED / "WIKIMEDIA_COACH_CAREER_PAGES.jsonl")
    successor = [
        page
        for page in load_jsonl(CYCLE32 / "CYCLE32_WIKI_CAREER_PAGES_SUCCESSOR.jsonl")
        if str(page.get("status") or "") == "REVISION_BOUND"
    ]
    cycle33_pages = load_jsonl(OUT / "CYCLE33_WIKI_CAREER_PAGES_SUCCESSOR.jsonl")
    return [*pages, *successor, *cycle33_pages]


def occupant_rows() -> list[dict[str, Any]]:
    matrix = load_jsonl(OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX.jsonl")
    if not matrix:
        matrix = load_jsonl(
            OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX_HTML_SUCCESSOR.jsonl"
        )
    programs = {
        str(row.get("program_id")): row
        for row in load_jsonl(PRED / "CURRENT_2026_PROGRAMS.jsonl")
    }
    occupants: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for cell in matrix:
        display = str(
            (programs.get(str(cell.get("program_id"))) or {}).get("display_name")
            or cell.get("display_name")
            or ""
        )
        for ep in cell.get("episode_refs") or []:
            person = str(ep.get("person") or "").strip()
            if not person:
                continue
            key = (
                str(cell.get("program_id") or ""),
                _fold(person),
                str(cell.get("role") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            occupants.append(
                {
                    "program_id": cell.get("program_id"),
                    "display_name": display,
                    "role": cell.get("role"),
                    "person": person,
                    "source_title": ep.get("source_title"),
                    "span_id": ep.get("span_id"),
                    "page_url": ep.get("page_url"),
                }
            )
    return occupants


def attempt_row(
    occupant: Mapping[str, Any],
    pages: list[Mapping[str, Any]],
    *,
    acquisition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    joined = join_occupant_to_pages(
        person=str(occupant.get("person") or ""),
        program_display=str(occupant.get("display_name") or ""),
        pages=pages,
    )
    page = pages[0] if len(pages) == 1 else None
    episodes = []
    if page is not None:
        episodes = [
            {
                "program_raw": ep.get("program_raw"),
                "role": ep.get("role"),
                "source_title": ep.get("source_title"),
                "start_year": ep.get("start_year"),
                "end_year": ep.get("end_year"),
                "wikimedia_revision": ep.get("wikimedia_revision"),
                "span_id": ep.get("span_id"),
                "continuous_career_not_inferred": True,
            }
            for ep in (page.get("episodes") or [])
        ]
    return {
        **occupant,
        **joined,
        "episode_count_on_bound_page": len(episodes),
        "locatable_episodes_sample": episodes[:12],
        "team_season_appearance_is_not_career": True,
        "name_agreement_is_not_join": True,
        "acquisition_attempt": acquisition or {"status": "CACHE_INDEX_ONLY"},
        "pit_admitted": False,
        "as_of_utc": utc_now(),
    }


def acquire_missing(
    people: list[str], ledger: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]], str]:
    acquired: list[dict[str, Any]] = []
    by_person: dict[str, list[dict[str, Any]]] = {}
    halt = "COMPLETED_OR_CACHE_EXHAUSTED"
    for person in people:
        bound = None
        try:
            titles = search_titles(person, ledger)
        except RuntimeError:
            halt = "LIVE_REQUEST_CEILING"
            break
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            by_person[_fold(person)] = []
            acquired.append(
                {
                    "occupant_person": person,
                    "status": "SEARCH_ERROR",
                    "error": str(exc),
                    "pit_admitted": False,
                }
            )
            continue
        for title in titles:
            if not career_page_title_matches_person(title, person) and _fold(
                title.partition(" (")[0]
            ) != _fold(person):
                continue
            try:
                page = fetch_coach_page(title, ledger)
            except RuntimeError:
                halt = "LIVE_REQUEST_CEILING"
                break
            except (OSError, urllib.error.URLError, json.JSONDecodeError):
                continue
            if str(page.get("status") or "") != "REVISION_BOUND":
                continue
            if not career_page_title_matches_person(
                str(page.get("title") or ""), person
            ) and _fold(str(page.get("title") or "").partition(" (")[0]) != _fold(
                person
            ):
                continue
            page["occupant_person"] = person
            bound = page
            break
        if halt == "LIVE_REQUEST_CEILING":
            break
        if bound is None:
            acquired.append(
                {
                    "occupant_person": person,
                    "status": "NO_MATCHING_WIKI_TITLE",
                    "pit_admitted": False,
                    "wikipedia_is_not_factual_verification": True,
                }
            )
            by_person[_fold(person)] = []
            continue
        acquired.append(bound)
        by_person[_fold(person)] = [bound]
    return acquired, by_person, halt


def historical_team_season_census(index: dict[str, list[Mapping[str, Any]]]) -> dict[str, Any]:
    wiki = load_jsonl(OUT / "CYCLE33_WIKI_STAFF_SUCCESSORS.jsonl")
    people: dict[str, dict[str, Any]] = {}
    for page in wiki:
        for ep in page.get("episodes") or []:
            person = str(ep.get("person") or "").strip()
            if not person:
                continue
            key = _fold(person)
            bucket = people.setdefault(
                key,
                {
                    "person": person,
                    "team_season_pages": 0,
                    "career_pages_indexed": 0,
                    "not_inferred_continuous": True,
                },
            )
            bucket["team_season_pages"] += 1
    for key, pages in index.items():
        if key in people:
            people[key]["career_pages_indexed"] = len(pages)
    return {
        "artifact_type": "CYCLE33_HISTORICAL_TEAM_SEASON_NOT_CAREER",
        "wiki_team_season_pages": len(wiki),
        "distinct_infobox_people": len(people),
        "infobox_people_with_indexed_career_page": sum(
            1 for row in people.values() if row["career_pages_indexed"]
        ),
        "team_season_appearance_is_not_career_join": True,
        "continuous_career_not_inferred_from_yearly_names": True,
        "pit_admitted": False,
    }


def main() -> int:
    occupants = occupant_rows()
    pages = load_career_pages()
    index = index_career_pages(pages)
    attempts: list[dict[str, Any]] = []
    for occupant in occupants:
        key = _fold(str(occupant.get("person") or ""))
        attempts.append(attempt_row(occupant, list(index.get(key) or [])))
    missing_people = []
    seen_missing: set[str] = set()
    for row in attempts:
        if row.get("career_join_state") != "CAREER_PAGE_MISSING":
            continue
        person = str(row.get("person") or "")
        folded = _fold(person)
        if not person or folded in seen_missing:
            continue
        seen_missing.add(folded)
        missing_people.append(person)
    ledger: list[dict[str, Any]] = []
    acquired, acquired_index, halt = acquire_missing(missing_people, ledger)
    if acquired:
        existing = {
            str(page.get("wikimedia_revision") or page.get("pageid") or i)
            for i, page in enumerate(pages)
        }
        new_pages = [
            page
            for page in acquired
            if str(page.get("status") or "") == "REVISION_BOUND"
            and str(page.get("wikimedia_revision") or page.get("pageid"))
            not in existing
        ]
        write_jsonl(OUT / "CYCLE33_WIKI_CAREER_PAGES_SUCCESSOR.jsonl", new_pages)
        for key, extra in acquired_index.items():
            if extra:
                index.setdefault(key, []).extend(extra)
        rebuilt: list[dict[str, Any]] = []
        for occupant in occupants:
            key = _fold(str(occupant.get("person") or ""))
            acq = None
            if key in acquired_index:
                acq = {
                    "status": (
                        "ACQUIRED_REVISION_BOUND"
                        if acquired_index[key]
                        else "ACQUIRED_NO_MATCHING_TITLE"
                    ),
                    "live_or_cache": "CACHE_THEN_BOUNDED_WIKIMEDIA",
                }
            rebuilt.append(
                attempt_row(
                    occupant, list(index.get(key) or []), acquisition=acq
                )
            )
        attempts = rebuilt
    counts = Counter(str(row.get("career_join_state")) for row in attempts)
    unique_people = len({_fold(str(row.get("person") or "")) for row in attempts})
    payload = {
        "artifact_type": "CYCLE33_CAREER_KEY_ATTEMPTS",
        "as_of_utc": utc_now(),
        "occupant_keys": len(attempts),
        "unique_people": unique_people,
        "state_counts": dict(counts),
        "evidence_bound": counts.get("EVIDENCE_BOUND_CAREER_JOIN", 0),
        "missing_pages": counts.get("CAREER_PAGE_MISSING", 0),
        "name_only_not_accepted": counts.get("NAME_ONLY_CANDIDATE_NOT_ACCEPTED", 0),
        "org_identity_unbound": counts.get("FOOTBALL_PAGE_ORG_IDENTITY_UNBOUND", 0),
        "ambiguous": counts.get("AMBIGUOUS_MULTIPLE_FOOTBALL_PAGES", 0),
        "every_occupant_key_has_attempt": len(attempts) == len(occupants),
        "missing_unique_people_searched": len(missing_people),
        "wikimedia_ledger_rows": len(ledger),
        "wikimedia_cache_hits": sum(1 for row in ledger if row.get("cached")),
        "wikimedia_live_requests": sum(
            1 for row in ledger if not row.get("cached")
        ),
        "acquisition_halt": halt,
        "denominators": {
            "occupant_keys": len(attempts),
            "unique_people": unique_people,
            "cached_career_pages_indexed": len(pages),
            "team_season_infobox_people": historical_team_season_census(index)[
                "distinct_infobox_people"
            ],
        },
        "historical": historical_team_season_census(index),
        "team_season_appearance_is_not_career": True,
        "continuous_career_not_inferred": True,
        "predecessor_career_files_not_overwritten": True,
        "pit_admitted": False,
        "wikipedia_is_not_factual_verification": True,
        "hold": "SCIENTIFIC_OPERATOR_HOLD_ACTIVE",
    }
    write_json(OUT / "CYCLE33_CAREER_KEY_ATTEMPTS.json", payload)
    write_jsonl(OUT / "CYCLE33_CAREER_KEY_ATTEMPTS.jsonl", attempts)
    write_json(OUT / "CYCLE33_CAREER_WIKIMEDIA_LEDGER.json", {"rows": ledger[:800]})
    print(json.dumps({k: payload[k] for k in payload if k != "historical"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

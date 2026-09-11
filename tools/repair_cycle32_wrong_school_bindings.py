"""Re-bind programs whose stored wiki titles or staff URLs fail identity.

Writes Cycle32 successors. Does not overwrite Cycle30 predecessor files.
Cache-first Wikimedia and official-staff routes; bounded live fetches only
when the identity-correct page is absent from cache.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aggie_analytics.cycle30.coaching import (  # noqa: E402
    CoachingError,
    PROGRAM_ATHLETICS_ORIGINS,
    extract_athletics_website_from_wikitext,
    official_staff_candidate_urls,
    parse_official_staff_html,
    parse_official_staff_json,
    primary_role_coverage,
    PRIMARY_ROLES,
    redact_personal_contact,
    season_title_matches_school,
)
from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_json  # noqa: E402
from tools.acquire_cycle30_official_staff import (  # noqa: E402
    BUDGET,
    fetch_html,
    useful_people,
)
from tools.acquire_cycle30_wikimedia import search_and_parse  # noqa: E402

PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")


def main() -> int:
    programs = load_jsonl(PRED / "CURRENT_2026_PROGRAMS.jsonl")
    wiki_rows = load_jsonl(PRED / "WIKIMEDIA_CURRENT_STAFF_CANDIDATES.jsonl")
    wiki_by_program = {str(row.get("program_id")): row for row in wiki_rows}
    ledger: list[dict[str, Any]] = []
    wiki_successors: list[dict[str, Any]] = []
    staff_attempts: list[dict[str, Any]] = []
    staff_people: list[dict[str, Any]] = []
    repaired = 0
    for program in programs:
        pid = str(program.get("program_id") or "")
        display = str(program.get("display_name") or "")
        stored = wiki_by_program.get(pid) or {}
        stored_title = str(stored.get("title") or "")
        quarantined_names = {
            "Arizona",
            "Illinois",
            "Kansas",
            "Louisiana",
            "New Mexico",
            "Ohio",
            "Southern",
            "Tennessee State",
            "Utah",
            "Georgia",
            "Utah Tech",
            "Wisconsin",
        }
        if (
            stored_title
            and season_title_matches_school(stored_title, display)
            and display not in quarantined_names
        ):
            continue
        parsed = search_and_parse(display, ledger)
        title = str(parsed.get("title") or "")
        bound = bool(title) and season_title_matches_school(title, display)
        wiki_successors.append(
            {
                **parsed,
                "program_id": pid,
                "display_name": display,
                "predecessor_title": stored_title or None,
                "identity_bound": bound,
                "artifact_class": "REAL_EVIDENCE",
                "pit_admitted": False,
            }
        )
        if not bound:
            staff_attempts.append(
                {
                    "program_id": pid,
                    "display_name": display,
                    "status": "ATTEMPTED_NO_IDENTITY_BOUND_WIKI_TITLE",
                    "predecessor_title": stored_title or None,
                    "page_url": None,
                    "attempt_count": 1,
                    "artifact_class": "BLOCKER_METADATA",
                }
            )
            continue
        wikitext = ""
        # search_and_parse already fetched the page into cache; website comes
        # from a fresh title-bound parse of stored revision content when present.
        from tools.acquire_cycle30_official_staff import load_current_wikitext

        wikitext = load_current_wikitext([title]).get(title, "")
        website = (
            extract_athletics_website_from_wikitext(wikitext) if wikitext else None
        )
        if not website:
            website = PROGRAM_ATHLETICS_ORIGINS.get(pid)
        if not website:
            staff_attempts.append(
                {
                    "program_id": pid,
                    "display_name": display,
                    "status": "ATTEMPTED_NO_URL",
                    "wiki_title": title,
                    "page_url": None,
                    "attempt_count": 1,
                    "reason": "identity-bound wiki page has no athletics website",
                    "artifact_class": "BLOCKER_METADATA",
                }
            )
            continue
        parsed_people: list[dict[str, str]] = []
        chosen_url = None
        last_receipt: dict[str, Any] | None = None
        for url in official_staff_candidate_urls(website):
            body, receipt = fetch_html(url, ledger, BUDGET, cache_only=False)
            last_receipt = receipt
            if int(receipt.get("http_status") or 0) >= 400 or not body:
                continue
            html = redact_personal_contact(body.decode("utf-8", "replace"))
            people: list[dict[str, str]] = []
            stripped = body.lstrip()
            if stripped.startswith(b"{") or stripped.startswith(b"["):
                try:
                    payload = json.loads(html)
                except json.JSONDecodeError:
                    payload = None
                if payload is not None:
                    people = parse_official_staff_json(payload, page_url=url)
            if not people:
                try:
                    people = parse_official_staff_html(
                        html, page_url=url, program_name=display
                    )
                except CoachingError:
                    continue
            if useful_people(people) or (
                people and len(primary_role_coverage(people)) > len(primary_role_coverage(parsed_people))
            ):
                parsed_people = people
                chosen_url = url
            if set(PRIMARY_ROLES) <= primary_role_coverage(people):
                break
        if not parsed_people:
            staff_attempts.append(
                {
                    "program_id": pid,
                    "display_name": display,
                    "status": "QUARANTINED_IDENTITY_OR_PARSE",
                    "wiki_title": title,
                    "website": website,
                    "page_url": chosen_url or (last_receipt or {}).get("route"),
                    "http_status": (last_receipt or {}).get("http_status"),
                    "attempt_count": 1,
                    "artifact_class": "REAL_EVIDENCE",
                }
            )
            continue
        repaired += 1
        staff_attempts.append(
            {
                "program_id": pid,
                "display_name": display,
                "status": "CAPTURED",
                "wiki_title": title,
                "website": website,
                "page_url": chosen_url,
                "parser": "parse_official_staff_html",
                "http_status": (last_receipt or {}).get("http_status"),
                "receipt_identity": sha256_bytes(
                    json.dumps(parsed_people, sort_keys=True).encode("utf-8")
                ),
                "attempt_count": 1,
                "artifact_class": "REAL_EVIDENCE",
                "as_of_utc": utc_now(),
            }
        )
        for person in parsed_people:
            staff_people.append(
                {
                    **person,
                    "program_id": pid,
                    "display_name": display,
                    "page_url": chosen_url,
                    "artifact_class": "REAL_EVIDENCE",
                    "pit_admitted": False,
                }
            )
    science = OUT / "science"
    write_jsonl(science / "CYCLE32_WIKI_TITLE_SUCCESSORS.jsonl", wiki_successors)
    write_jsonl(science / "CYCLE32_REPAIRED_STAFF_ATTEMPTS.jsonl", staff_attempts)
    write_jsonl(science / "CYCLE32_REPAIRED_STAFF_PEOPLE.jsonl", staff_people)
    summary = {
        "artifact_type": "CYCLE32_WRONG_SCHOOL_REPAIR",
        "programs_with_unbound_predecessor_wiki_title": len(wiki_successors),
        "identity_bound_wiki_titles": sum(
            1 for row in wiki_successors if row.get("identity_bound")
        ),
        "staff_captured": repaired,
        "staff_people": len(staff_people),
        "wiki_ledger_requests": len(ledger),
        "predecessor_not_overwritten": True,
        "as_of_utc": utc_now(),
    }
    (science / "CYCLE32_WRONG_SCHOOL_REPAIR_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

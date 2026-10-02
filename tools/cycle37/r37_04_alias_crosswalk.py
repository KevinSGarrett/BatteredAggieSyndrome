"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-04 AC04 / R36-04 / MR35R-07: every unresolved program display name,
examined individually against source-backed alias evidence, with effective
dates where a source states them.

Evidence routes, in order, all bound to bytes:

1. Primary-source rename statements the manager's leads name, read this
   attempt: each quoted sentence must occur in the stored bytes, and its date
   is recorded as the source states it (effective date, or publication date
   when no effective date is stated).
2. The declared game source's own alternate names (CFBD ``/teams`` cache,
   ``alternateNames``), exactly or under one declared orthography ("Saint" =
   "St.", parentheses dropped): source-backed identity, undated.
3. Official athletics pages (the R37-03 source identity crosswalk) whose own
   title or site name states the raw name as a whole phrase: a capture whose
   program the page identity confirms, or the page requested for exactly one
   program whose game-source mascot the page states (in its title or host) or
   whose school name the raw name is the initialism of. Current pages support
   retrospective identity, not what was known before an old game.
4. Revision-bound Wikimedia career rows (R37-05) whose employer display is
   the raw name and whose football link target resolved to one program:
   secondary evidence, dated by the years of use.

A name resolves only when its evidence points at exactly one canonical
program. Several programs is a conflict and stays unresolved; no evidence
stays unresolved with the routes searched. Names are never merged by
similarity. Each unresolved user-corpus cell carrying the name is counted so
the reprocessing is visible at cell grain.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import html
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path
from typing import Any
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
METADATA = ATTEMPT / "private" / "acquisition" / "metadata"
TEAMS = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle30_work/raw/teams")
CROSSWALK_ROWS = ATTEMPT / "evidence" / "repairs" / "R37_03_SOURCE_IDENTITY_ROWS.jsonl"
AUDIT = ATTEMPT / "evidence" / "repairs" / "R37_04_POPULATION_AUDIT.json"
#: Primary-source renames: the aliases they cover, the program's CFBD id, and the exact statement.
RENAMES = [
    {"aliases": ["Dixie State"], "cfbd_id": 3101, "source": "8c9b0400acb6", "format": "RENDER_JSON",
     "url": "https://umac.utahtech.edu/brandingguide/",
     "quote": "the University was officially renamed to Utah Tech University starting July 1, 2022",
     "effective": "2022-07-01", "date_basis": "EFFECTIVE_DATE_STATED"},
    {"aliases": ["Houston Baptist"], "cfbd_id": 2277, "source": "2853141d21f6", "format": "HTML",
     "url": "https://hc.edu/news-and-events/2022/09/21/hbu-changes-name-to-houston-christian-university/",
     "quote": "Houston Baptist University Changes Name to Houston Christian University",
     "effective": "2022-09-21", "date_basis": "PUBLICATION_DATE_IN_THE_URL_NO_EFFECTIVE_DATE_IN_THE_HELD_BYTES"},
    {"aliases": ["Texas A&M-Commerce", "Texas A&M-Commerce / East Texas A&M"], "cfbd_id": 2837, "source": "bc08ac77c0eb",
     "format": "HTML",
     "url": "https://news.tamus.edu/stories/texas-am-university-system-board-of-regents-approves-name-change-for-texas-am-university-commerce/",
     "quote": "voted to change the name of Texas A&M University-Commerce to East Texas A&M University , effective immediately",
     "effective": "2024-11-07", "date_basis": "EFFECTIVE_DATE_STATED"},
    {"aliases": ["Texas A&M-Commerce", "Texas A&M-Commerce / East Texas A&M"], "cfbd_id": 2837, "source": "6519018c5b4c",
     "format": "HTML", "url": "https://www.etamu.edu/name-change-faqs/",
     "quote": "approved the renaming of Texas A&M University-Commerce to East Texas A&M University. This decision, "
              "effective immediately",
     "effective": "2024-11-07", "date_basis": "EFFECTIVE_DATE_STATED"},
]


EPISODES = ATTEMPT / "evidence" / "repairs" / "R37_05_CAREER_EPISODES.jsonl"
WIKIMEDIA = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle30_work/raw/wikimedia")
SEASON_TITLE = re.compile(r"^(\d{4}) (.+) football team$")
#: The page's own lead defines a short name for the institution it represents, e.g.
#: "... football team represented the [[University of Texas Rio Grande Valley]] (UTRGV) ...".
LEAD_DEFINITION = re.compile(r"represented the \[\[([^\]|]+)(?:\|[^\]]*)?\]\]\s*\(([^)]{1,40})\)")


QUALIFIER = re.compile(r"\s*\([^()]*\)\s*$")


def unqualified(name: str) -> str:
    """The name without its trailing parenthesised qualifier: "Saint Mary's (CA)" -> "Saint Mary's"."""

    return QUALIFIER.sub("", name).strip()


def fold(value: str) -> str:
    """The contest-site fold: accents removed, case folded, every non-alphanumeric run one space."""

    text = unicodedata.normalize("NFKD", html.unescape(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def season_feed_names(seasons: list[int]) -> dict[tuple[int, str], tuple[str, str]]:
    """The game feed's own (school, mascot) for each program in each season, from the cached /teams payloads."""

    out: dict[tuple[int, str], tuple[str, str]] = {}
    for season in seasons:
        for shape in ({}, {"classification": "fbs"}, {"classification": "fcs"}):
            request = {"endpoint": "/teams", "parameters": {"year": season, **shape}}
            identity = hashlib.sha256(json.dumps(request, sort_keys=True, separators=(",", ":"),
                                                 ensure_ascii=False).encode("utf-8")).hexdigest()
            path = TEAMS / f"{identity}.json"
            if not path.is_file():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows = payload if isinstance(payload, list) else (payload.get("data") or payload.get("teams") or [])
            for row in rows:
                if isinstance(row, dict) and row.get("id") is not None and row.get("school") and row.get("mascot"):
                    out.setdefault((season, f"SRC-002:TEAM:{row['id']}"), (str(row["school"]), str(row["mascot"])))
    return out


def team_season_pages(seasons: set[int]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Revision-bound cached team-season pages for the given seasons, and the redirects that reached them."""

    pages: dict[str, dict[str, Any]] = {}
    redirects: dict[str, str] = {}
    for path in sorted(WIKIMEDIA.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        query = payload.get("query") or {}
        found = query.get("pages") or {}
        for page in (found.values() if isinstance(found, dict) else found):
            title = str(page.get("title") or "")
            match = SEASON_TITLE.match(title)
            if not match or int(match.group(1)) not in seasons or not page.get("revisions"):
                continue
            revision = page["revisions"][0]
            slot = (revision.get("slots") or {}).get("main") or {}
            text = slot.get("*") or slot.get("content") or ""
            defined = LEAD_DEFINITION.search(text)
            infobox = re.search(r"\|\s*team\s*=\s*([^\n|}]+)", text)
            pages[fold(title)] = {"title": title, "file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                  "revid": revision.get("revid"), "timestamp": revision.get("timestamp"),
                                  "infobox_team": infobox.group(1).strip() if infobox else None,
                                  "lead_defines": fold(defined.group(2)) if defined else None,
                                  "lead_definition": defined.group(0)[:200] if defined else None}
            for redirect in query.get("redirects") or []:
                redirects[fold(str(redirect.get("from") or ""))] = fold(title)
    return pages, redirects


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", html.unescape(str(text or "")).casefold()).strip()


def orthographic(text: str) -> str:
    """The declared orthography: "Saint" and "St." are one word, and parentheses are dropped."""

    return re.sub(r"\bsaint\b", "st", norm(text))


def initialism(school: str) -> str:
    """"UT Rio Grande Valley" -> "utrgv": an all-capital word is kept, other words give their initial."""

    return "".join(word if word.isupper() else word[0] for word in re.findall(r"[A-Za-z]+", school)).casefold()


def source_text(prefix: str, fmt: str) -> tuple[str, Path]:
    path = next(p for p in METADATA.iterdir() if p.name.startswith(prefix) and p.suffix == ".bin")
    data = path.read_bytes().decode("utf-8", "replace")
    if fmt == "RENDER_JSON":
        return re.sub(r"\s+", " ", json.loads(data)["text"]), path
    data = re.sub(r"<(script|style|noscript)\b.*?</\1\s*>", " ", data, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", data))), path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence" / "repairs" / "R37_04_ALIAS_CROSSWALK.json")
    args = parser.parse_args(argv)
    conn = sqlite3.connect(f"file:{args.release}?mode=ro", uri=True)
    programs = {pid: json.loads(names) for pid, names in conn.execute("select program_id, display_names from canonical_program")}
    names = [row[0] for row in conn.execute("select raw_name from unresolved_program_name order by unresolved_id")]
    cells = collections.Counter(row[0] for row in conn.execute(
        "select team_as_written from user_corpus_cell where canonical_program_id is null"))
    # 1. primary-source renames
    rename_evidence: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for spec in RENAMES:
        text, path = source_text(spec["source"], spec["format"])
        found = spec["quote"] in text
        for alias in spec["aliases"]:
            rename_evidence[alias].append({
                "route": "PRIMARY_SOURCE_RENAME_STATEMENT", "program_id": f"SRC-002:TEAM:{spec['cfbd_id']}",
                "url": spec["url"], "source_path": str(path), "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "quote": spec["quote"], "quote_found_in_bytes": found, "effective_date": spec["effective"],
                "date_basis": spec["date_basis"]})
    # 2. declared game source alternate names, exactly and under the declared orthography
    alternates: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    spelled: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    teams: dict[str, dict[str, Any]] = {}
    for path in sorted(TEAMS.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        for team in payload:
            pid = f"SRC-002:TEAM:{team.get('id')}"
            teams.setdefault(pid, team)
            for alt in [team.get("school")] + list(team.get("alternateNames") or []):
                if alt:
                    alternates[norm(alt)].add((pid, digest))
                    spelled[orthographic(alt)].add((pid, digest))
    # 3. official pages that state the name in their own title or site name: a page whose program
    #    the page identity confirms, or the page requested for a program whose game-source mascot
    #    the page title or host states, or whose school name the raw name is the initialism of
    official: dict[str, set[tuple[str, str, str, str]]] = collections.defaultdict(set)
    for line in CROSSWALK_ROWS.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        identity = row.get("page_identity") or {}
        stated = f" {norm(identity.get('title'))} {norm(identity.get('site_name'))} "
        host = norm(re.sub(r"^[a-z]+://", "", str(row.get("route") or "")).split("/")[0])
        claims = [c.get("program_id") for c in row.get("claimed_programs") or [] if c.get("program_id")]
        for name in names:
            if f" {norm(name)} " not in stated:
                continue
            if row.get("state") == "CONFIRMED_BY_SOURCE_IDENTITY" and row.get("admitted_program_id"):
                official[name].add((row["admitted_program_id"], row["capture_path"], str(identity.get("title"))[:120],
                                    "PAGE_IDENTITY_CONFIRMED"))
            elif len(claims) == 1 and claims[0] in teams:
                team = teams[claims[0]]
                mascot = norm(team.get("mascot"))
                basis = ("REQUESTED_PROGRAMS_MASCOT_STATED_BY_THE_PAGE" if mascot and (
                    f" {mascot} " in stated or mascot.replace(" ", "") in host.replace(" ", ""))
                    else "RAW_NAME_IS_THE_INITIALISM_OF_THE_REQUESTED_PROGRAM"
                    if norm(name).replace(" ", "") == initialism(team.get("school") or "") else None)
                if basis:
                    official[name].add((claims[0], row["capture_path"], str(identity.get("title"))[:120], basis))
    # 4. revision-bound Wikimedia career rows whose display is the name and whose link target
    #    resolved to one program (secondary, retrospective; the rows' years date the usage)
    wiki: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    unresolved_links: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    years: dict[tuple[str, str], list[int]] = collections.defaultdict(list)
    link_rows: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    wanted = set(names)
    with EPISODES.open(encoding="utf-8") as handle:
        for line in handle:
            episode = json.loads(line)
            display = episode.get("employer_display")
            pid = (episode.get("resolution") or {}).get("program_id")
            if display in wanted and not pid and str(episode.get("employer_link_target") or "").endswith(" football"):
                unresolved_links[display][episode["employer_link_target"]] += 1
                link_rows[(display, episode["employer_link_target"])].append({
                    "episode_id": episode.get("episode_id"), "revision": episode.get("revision"),
                    "raw_file_sha256": episode.get("raw_file_sha256"), "team_byte_span": episode.get("team_byte_span"),
                    "start": episode.get("start"), "end": episode.get("end")})
            if display in wanted and pid and str(episode.get("employer_link_target") or "").endswith(" football"):
                wiki[display][pid] += 1
                if episode.get("start"):
                    years[(display, pid)].append(int(episode["start"]))
    # 5. revision-bound Wikimedia team-season pages, for exactly the seasons each name occurs in.
    #    A page is bound to a program by one of three exact rules, never by a similar name:
    #    FEED_NAME_REDIRECT - the feed's own title for (season, program) redirects to a page whose title is
    #      "<season> <name> <mascot> football team";
    #    EVIDENCED_PROGRAMS_MASCOT - the one program the other routes evidence has a page titled exactly
    #      "<season> <name> <its mascot> football team";
    #    FEED_NAME_PAGE_DEFINES_THE_ALIAS - the page titled with the feed's own name for (season, program)
    #      names its own team "<name> <mascot>" in the infobox, or its lead defines the name for the institution it
    #      represents ("represented the [[...]] (<name>)"); an opponent named in the text never counts.
    name_seasons = {raw: [int(x) for x in json.loads(seasons or "[]")]
                    for raw, seasons in conn.execute("select raw_name, seasons from unresolved_program_name")}
    needed = sorted({season for values in name_seasons.values() for season in values})
    feed = season_feed_names(needed)
    season_pages, season_redirects = team_season_pages(set(needed))

    def team_season_evidence(name: str, evidenced: str | None) -> list[dict[str, Any]]:
        found = []
        for season in name_seasons.get(name, []):
            for (feed_season, pid), (school, mascot) in sorted(feed.items()):
                if feed_season != season:
                    continue
                feed_key = fold(f"{season} {school} {mascot} football team")
                alias_key = fold(f"{season} {name} {mascot} football team")
                basis, page = None, None
                if season_redirects.get(feed_key) == alias_key and alias_key in season_pages:
                    basis, page = "FEED_NAME_REDIRECT", season_pages[alias_key]
                elif pid == evidenced and alias_key in season_pages:
                    basis, page = "EVIDENCED_PROGRAMS_MASCOT", season_pages[alias_key]
                elif feed_key in season_pages and (
                        season_pages[feed_key]["lead_defines"] == fold(name)
                        or fold(season_pages[feed_key]["infobox_team"] or "") == fold(f"{name} {mascot}")):
                    # the page's own naming of its team, never an opponent mentioned in its text
                    basis, page = "FEED_NAME_PAGE_DEFINES_THE_ALIAS", season_pages[feed_key]
                if basis:
                    found.append({"route": "WIKIMEDIA_TEAM_SEASON_PAGE_NAMES_THE_ALIAS", "basis": basis,
                                  "program_id": pid, "season": season, "feed_name": f"{school} {mascot}",
                                  "page_title": page["title"], "infobox_team": page["infobox_team"],
                                  "lead_definition": page["lead_definition"],
                                  "revid": page["revid"], "revision_timestamp": page["timestamp"],
                                  "file": page["file"], "file_sha256": page["sha256"], "effective_date": None,
                                  "date_basis": "SEASON_OF_A_REVISION_BOUND_TEAM_SEASON_PAGE"})
        return found

    rows, states = [], collections.Counter()
    for name in names:
        evidence: list[dict[str, Any]] = [e for e in rename_evidence.get(name, []) if e["quote_found_in_bytes"]]
        for pid, digest in sorted(alternates.get(norm(name), set())):
            evidence.append({"route": "DECLARED_GAME_SOURCE_ALTERNATE_NAME", "program_id": pid,
                             "source_sha256": digest, "effective_date": None, "date_basis": "UNDATED"})
        for pid, digest in sorted(spelled.get(orthographic(name), set()) - alternates.get(norm(name), set())):
            evidence.append({"route": "DECLARED_GAME_SOURCE_ALTERNATE_NAME_UNDER_DECLARED_ORTHOGRAPHY",
                             "program_id": pid, "source_sha256": digest, "effective_date": None,
                             "date_basis": "UNDATED", "orthography": "Saint = St.; parentheses dropped"})
        for pid, capture, title, basis in sorted(official.get(name, set())):
            evidence.append({"route": "OFFICIAL_PAGE_STATES_THE_NAME", "basis": basis, "program_id": pid,
                             "capture_path": capture, "page_title": title, "effective_date": None,
                             "date_basis": "CURRENT_PAGE_RETROSPECTIVE_IDENTITY_ONLY"})
        for pid, count in sorted(wiki.get(name, collections.Counter()).items()):
            span = years.get((name, pid)) or []
            evidence.append({"route": "WIKIMEDIA_CAREER_ROWS_LINK_THIS_DISPLAY_TO_ONE_PROGRAM", "program_id": pid,
                             "rows": count, "first_year_used": min(span) if span else None,
                             "last_year_used": max(span) if span else None, "effective_date": None,
                             "date_basis": "YEARS_OF_USE_IN_REVISION_BOUND_SECONDARY_ROWS"})
        candidates = sorted({e["program_id"] for e in evidence})
        known = [pid for pid in candidates if pid in programs]
        evidence.extend(team_season_evidence(name, known[0] if len(known) == 1 else None))
        candidates = sorted({e["program_id"] for e in evidence})
        known = [pid for pid in candidates if pid in programs]
        if len(known) == 1 and not wiki.get(name):
            mascot = str((teams.get(known[0]) or {}).get("mascot") or "").strip()
            article = f"{name} {mascot} football" if mascot else None
            rows_linked = link_rows.get((name, article), []) if article else []
            bare = unqualified(name)
            if mascot and not rows_linked and bare != name:
                # "Saint Mary's (CA)" rows linking "Saint Mary's Gaels football": the article drops the display's
                # qualifier and the game source's own mascot for the one evidenced program pins it instead
                article = f"{bare} {mascot} football"
                rows_linked = link_rows.get((name, article), [])
            span = [int(r["start"]) for r in rows_linked if r.get("start")]
            if rows_linked:
                entry = {
                    "route": "WIKIMEDIA_CAREER_ROWS_LINK_THIS_DISPLAY_TO_THE_EVIDENCED_PROGRAMS_ARTICLE",
                    "program_id": known[0], "article": article, "mascot_from_game_source": mascot,
                    "rows": len(rows_linked), "first_year_used": min(span) if span else None,
                    "last_year_used": max(span) if span else None, "effective_date": None,
                    "date_basis": "YEARS_OF_USE_IN_REVISION_BOUND_SECONDARY_ROWS",
                    "rule": ("link target is exactly '<raw name> <mascot> football' for the one program the other "
                             "routes evidence; corroborates that identity and never creates one"),
                    "row_receipts": rows_linked[:25]}
                if article != f"{name} {mascot} football":
                    entry["article_spelling"] = "RAW_NAME_WITHOUT_ITS_TRAILING_PARENTHESISED_QUALIFIER"
                    entry["rule"] = ("link target is exactly '<raw name without its trailing parenthesised qualifier> "
                                     "<mascot> football' for the one program the other routes evidence, the game "
                                     "source's mascot pinning the program; corroborates that identity and never "
                                     "creates one")
                evidence.append(entry)
        if len(known) == 1:
            dated = any(e["effective_date"] for e in evidence)
            used = any(e["route"].startswith("WIKIMEDIA") for e in evidence)
            state = ("RESOLVED_WITH_DATED_PRIMARY_SOURCE" if dated else "RESOLVED_WITH_DATED_USAGE_IN_SECONDARY_ROWS"
                     if used else "RESOLVED_WITH_UNDATED_SOURCE_IDENTITY")
        elif (candidates and not known) or (not candidates and unresolved_links.get(name)):
            # The name is a program's (its football article is linked) that the canonical
            # 1963-2026 FBS/FCS population does not carry, e.g. a discontinued program.
            state = "UNRESOLVED_PROGRAM_NOT_IN_THE_CANONICAL_POPULATION"
        elif len(known) > 1:
            state = "UNRESOLVED_EVIDENCE_NAMES_SEVERAL_PROGRAMS"
        else:
            state = "UNRESOLVED_NO_SOURCE_BACKED_ALIAS"
        states[state] += 1
        rows.append({"raw_name": name, "state": state, "program_id": known[0] if len(known) == 1 else None,
                     "program_display_names": programs.get(known[0]) if len(known) == 1 else None,
                     "candidates": candidates, "evidence": evidence,
                     "unresolved_user_corpus_cells_with_this_name": cells.get(name, 0),
                     "football_articles_linked_for_this_name_without_a_canonical_program":
                         dict(unresolved_links.get(name, collections.Counter())),
                     "routes_searched": ["primary-source rename statements read this attempt",
                                         "CFBD /teams alternateNames cache", "confirmed official page titles",
                                         "revision-bound Wikimedia career rows (resolved links, and links to the "
                                         "evidenced program's '<name> <mascot> football' article)",
                                         "cached revision-bound team-season pages for the seasons the name occurs "
                                         "in (feed-name redirect, evidenced program's mascot, the feed-named page's own definition)"],
                     "pit_note": "identity only; a current page does not show what was known before an old game"})
    report = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-04",
        "rows_claimed": ["R37-04-AC04", "R37-04-CF-R36-04", "R37-04-CF-MR35R-07"],
        "names": len(rows), "states": dict(states),
        "cells_reprocessed": sum(r["unresolved_user_corpus_cells_with_this_name"] for r in rows),
        "cells_that_would_bind": sum(r["unresolved_user_corpus_cells_with_this_name"] for r in rows if r["program_id"]),
        "rows": rows, "release": str(args.release),
        "never_merged_by_similarity": True,
    }
    resolved = {r["raw_name"]: r for r in rows if r["program_id"]}
    bindings = []
    for cell_id, written, season in conn.execute(
            "select user_cell_id, team_as_written, season from user_corpus_cell where canonical_program_id is null "
            "order by user_cell_id"):
        if written in resolved:
            row = resolved[written]
            bindings.append({"user_cell_id": cell_id, "team_as_written": written, "season": season,
                             "program_id": row["program_id"], "alias_state": row["state"],
                             "routes": sorted({e["route"] for e in row["evidence"]}),
                             "binding": "ALIAS_CROSSWALK_SUCCESSOR_NOT_A_CONFIRMATION"})
    cells_path = args.out.with_name("R37_04_ALIAS_CELL_BINDINGS.jsonl")
    _bas_atomic.write_text(cells_path, "".join(json.dumps(b, sort_keys=True) + "\n" for b in bindings), encoding="utf-8")
    report["cell_bindings_written"] = len(bindings)
    report["cell_bindings_path"] = str(cells_path)
    _bas_atomic.write_text(args.out.with_name("R37_04_ALIAS_CROSSWALK_ROWS.jsonl"), 
        "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    _bas_atomic.write_text(args.out, json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for row in rows:
        print(f"{row['raw_name']:40} {row['state']:45} {row['program_display_names']} cells={row['unresolved_user_corpus_cells_with_this_name']}")
    print(dict(states))
    return 0


if __name__ == "__main__":
    sys.exit(main())

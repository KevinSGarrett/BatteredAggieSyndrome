r"""Cycle #37 — Attempt #5 — build the corrected explicit career successor (TP37-A05-02/03/04/06, R37A05-06).

    a05_career_successor.py --out <new directory> --census <A4 CAREER_RAW_CENSUS.json>
                            --template-census <A5 CAREER_TEMPLATE_CENSUS.json> [--pointer <new file>]
    a05_career_successor.py --compare-to <delivered CAREER_SUCCESSOR_A05.sqlite> --out <new directory> ...

Rereads every cached revision of the delivered career population with the v37.5 parser (season templates keep
both endpoints; nested list lines keep their own dates; an inherited date names its parent line) and the v37.5
role taxonomy (a side-dependent role takes its unit from the words of its own title segment), through the same
program crosswalk, staff join and official-site rule as the delivered rows (:mod:`r37_05_career_reparse`), and
writes:

* ``CAREER_SUCCESSOR_A05.sqlite`` -- the Attempt 5 format that :mod:`aggie_analytics.cycle37.career_successor`
  validates and the installed ``bas-staff-query --career-successor`` serves: ``career_episode_a05``,
  ``career_a05_disposition`` (one row per delivered predecessor episode) and ``career_a05_from_a04`` (one row per
  Attempt 4 successor episode), all under digest-bound identity;
* ``CAREER_A05_DISPOSITIONS.jsonl.gz`` and ``CAREER_A05_FROM_A04.jsonl.gz`` -- the same two mappings, for a reader
  without SQLite;
* ``CAREER_A05_SUCCESSOR_BUILD.json`` (+ ``_ROWS.json.gz``) -- inputs and digests; accounting; the manager's
  2,257-row template screen and 33-row defensive-title screen member by member, each checked against the raw text
  with code that does not use the parser or the taxonomy; the Attempt 3 screens; the Attempt 4 raw census and the
  Attempt 5 template census reconciled against the rows; every unit change; and the delivered release's staff
  rows whose unit the v37.5 taxonomy states differently (affected descendants, recorded, not rebuilt).

Only a changed *meaning* counts as a change: an assignment's taxonomy version and the unit basis it now records
are expected to differ on every row and are not compared (the unit itself is). The file is built in memory and
serialized, so ``--compare-to`` rebuilds and compares bytes without writing a second copy. Nothing is fetched;
the predecessor, the Attempt 4 successor and every raw file are only read.
"""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import a04_career_successor as a4b  # noqa: E402
import a05_career_template_census as template_tool  # noqa: E402
import r37_05_career_reparse as reparse  # noqa: E402

from aggie_analytics.cycle37 import career_infobox, staff_record  # noqa: E402
from aggie_analytics.cycle37 import career_successor as cs  # noqa: E402

CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 5
BUILDER_VERSION = "BAS-C37A05-CAREER-SUCCESSOR-BUILDER-v1"
PREDECESSOR_DB = a4b.PREDECESSOR_DB
PREDECESSOR_SHA256 = a4b.PREDECESSOR_SHA256
PREDECESSOR_RELEASE_VERSION = a4b.PREDECESSOR_RELEASE_VERSION
A4_SUCCESSOR = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle37\attempt04\release\successor\CAREER_SUCCESSOR_A04.sqlite")
A4_SUCCESSOR_SHA256 = "f7103f781259ecf13a06dfc59318ab7c735a9ff7c1080b9fd4608f04ae0373c7"
#: The manager's Attempt 4 review census: 2,257 rows whose years carry a two-argument season template and 33 rows
#: whose defensive passing-game title carried OFFENSE or UNKNOWN. Read only; its digest is recorded per build.
A4_SEMANTIC_CENSUS = Path(r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle37\attempt04"
                          r"\review-20260925T025537Z\CAREER_SEMANTIC_CENSUS.json")
SCREEN_TEMPLATE = "MANAGER_A04_TWO_ARGUMENT_SEASON_TEMPLATE_2257"
SCREEN_DEFENSIVE = "MANAGER_A04_DEFENSIVE_PASS_GAME_TITLE_33"
SCREEN_EXPECTED = {SCREEN_TEMPLATE: 2257, SCREEN_DEFENSIVE: 33}
#: Keys of an assignment that record the taxonomy's version and how it read the unit. They differ on every row
#: by construction and are recorded, not compared; ``unit`` itself is compared.
VERSION_ONLY_ASSIGNMENT_KEYS = frozenset({"taxonomy_version", "unit_basis", "unit_words", "base_unit"})
#: Columns an Attempt 4 row stores as JSON text.
A04_JSON_COLUMNS = cs.PREDECESSOR_JSON_COLUMNS | {"predecessor_episode_ids", "start_bounds", "end_bounds",
                                                 "uncertainty_classes", "unresolved_parentheticals",
                                                 "employer_qualifier_kinds", "role_parentheticals"}
A05_JSON_COLUMNS = A04_JSON_COLUMNS | {"a04_episode_ids", "date_parent", "unresolved_date_templates"}
#: Fields compared between an Attempt 4 row and the Attempt 5 row it maps to.
A04_COMPARED = a4b.COMPARED + ("start_state", "end_state", "start_bounds", "end_bounds", "start_qualifier",
                               "end_qualifier", "definite_first_season", "definite_last_season",
                               "possible_first_season", "possible_last_season", "bounds_consistent",
                               "uncertainty_classes", "unresolved_parentheticals", "role_parentheticals",
                               "employer_qualifier_kinds", "career_field")
_YEAR = re.compile(r"^(1[89]\d\d|20\d\d)$")
#: Footnote and citation templates (the reconciliation's own list, not the parser's).
_NOTE_TEMPLATE = re.compile(r"^(?:efn|efn-[a-z]+|refn|sfn|sfnp|note|notetag|ref|cite\b.*|citation)$", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def semantic(key: str, value: Any) -> Any:
    """The comparable meaning of a field: :func:`a4b.normal`, with an assignment's version-only keys removed."""

    value = a4b.normal(value)
    if key == "assignments" and isinstance(value, list):
        return [{k: v for k, v in item.items() if k not in VERSION_ONLY_ASSIGNMENT_KEYS}
                if isinstance(item, dict) else item for item in value]
    if key in ("pageid", "revision", "row_index") and value is not None:
        return str(value)
    return value


def comparable(row: dict[str, Any], keys: tuple[str, ...], json_columns: frozenset[str] | set[str] = frozenset()
               ) -> dict[str, Any]:
    out = {}
    for key in keys:
        value = row.get(key)
        if key in json_columns and isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                value = {"undecodable_stored_text": value}
        out[key] = semantic(key, value)
    return out


def uncertainty_classes(team: dict[str, Any], interval: dict[str, Any]) -> list[str]:
    classes = a4b.uncertainty_classes(team, interval)
    if career_infobox.UNRESOLVED_TEMPLATE in (interval.get("start_state"), interval.get("end_state")):
        classes.append("UNRESOLVED_DATE_TEMPLATE")
    return classes


def successor_episodes() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Every Attempt 5 episode, parsed from the cached raw revisions (the Attempt 4 loop, v37.5 parser/taxonomy)."""

    pages, duplicates, seen = [], [], set()
    for page in reparse.read_jsonl(reparse.CAREER_PAGES):
        key = (str(page["pageid"]), str(page["wikimedia_revision"]))
        if key in seen:
            duplicates.append(list(key))  # the same revision listed again reads to the same rows; read once
            continue
        seen.add(key)
        pages.append(page)
    index, index_stats = reparse.index_raw()
    resolver = reparse.Resolver()
    hosts = reparse.official_hosts()
    staff = [row for row in reparse.read_jsonl(reparse.STAFF_REPARSE) if row.get("admitted_for_coverage")]
    staff_by_key: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in staff:
        staff_by_key[(row["program_id"], staff_record.fold_name(row["person"]))].append(row)
    display_pages: dict[str, set[str]] = collections.defaultdict(set)
    for page in pages:
        display_pages[re.sub(r"\s*\(.*\)$", "", str(page.get("title") or ""))].add(str(page.get("pageid")))
    episodes: list[dict[str, Any]] = []
    missing_raw = []
    no_interval = {"start": None, "end": None, "ongoing": False, "as_written": None}
    for page in pages:
        key = (str(page["pageid"]), str(page["wikimedia_revision"]))
        path = index.get(key)
        if path is None:
            missing_raw.append(list(key))
            continue
        raw_bytes = path.read_bytes()
        record = next(iter(json.loads(raw_bytes)["query"]["pages"].values()))
        text = record["revisions"][0]["slots"]["main"]["*"]
        parsed = career_infobox.career_rows(text)
        cited = {urlparse(u).netloc.lower().removeprefix("www.") for u in reparse._URL.findall(text)}
        person_base = re.sub(r"\s*\(.*\)$", "", str(page.get("title") or ""))
        homonym = len(display_pages.get(person_base, ())) > 1
        for row in parsed["rows"]:
            team = row["team"] or {}
            resolution = resolver.resolve(team.get("employer_display") or "", team.get("employer_link_target"))
            assignments = reparse.assignments_for(row)
            parent = row.get("date_parent")
            unresolved = (career_infobox.unresolved_templates(career_infobox.plain(row["years_raw"], dates=True))
                          if row.get("years_raw") else [])
            for number, interval in enumerate(row["intervals"] or [no_interval]):
                first, last = a4b.definite_range(interval)
                classification = (resolver.classification(resolution.get("program_id"), first, last)
                                  if first is not None else {})
                state = a4b.population_state(row, interval, resolution, classification)
                join = {"state": "NOT_ATTEMPTED_OUTSIDE_POPULATION"}
                if state == "IN_POPULATION_CANDIDATE_EPISODE":
                    matches = [s for s in staff_by_key.get((resolution["program_id"], staff_record.fold_name(person_base)), [])
                               if s["season"] is not None and first <= s["season"] <= last
                               and {a["role"] for a in assignments} & {a["role"] for a in s["assignments"]}]
                    cites_official = bool(cited & hosts.get(resolution["program_id"], set()))
                    if matches and cites_official:
                        join = {"state": "JOINED_PAGE_CITES_THE_PROGRAMS_OFFICIAL_SITE",
                                "staff_rows": [[m["capture_path"], m["observation_index"]] for m in matches[:5]]}
                    elif matches:
                        join = {"state": "CANDIDATE_NAME_PROGRAM_ROLE_SEASON_ONLY_NOT_JOINED",
                                "staff_rows": [[m["capture_path"], m["observation_index"]] for m in matches[:5]]}
                    else:
                        join = {"state": "NO_ADMITTED_STAFF_ROW_FOR_THIS_PERSON_PROGRAM_ROLE_SEASON"}
                team_span = row["team_span"] or [None, None]
                possible_first, possible_last = a4b.possible_range(interval)
                locator = f"{page['pageid']}:{page['wikimedia_revision']}:{row['family']}:{row['index']}"
                episodes.append({
                    "locator": locator, "interval_index": number,
                    "episode_id": f"{cs.A05_IDENTITY_PREFIX}:{locator}:{number}",
                    "pageid": page["pageid"], "revision": page["wikimedia_revision"], "page_title": page.get("title"),
                    "wikidata_qid": page.get("wikidata_qid"), "person_display": person_base,
                    "homonym_display_name": homonym, "family": row["family"], "row_index": row["index"],
                    "start": interval["start"], "end": interval["end"], "ongoing": interval["ongoing"],
                    "years_as_written": interval["as_written"], "years_raw": row["years_raw"],
                    "employer_display": team.get("employer_display"),
                    "employer_link_target": team.get("employer_link_target"),
                    "employer_link_basis": team.get("employer_link_basis"),
                    "employer_qualifiers": team.get("employer_qualifiers"), "employer_kind": row["employer_kind"],
                    "resolution": resolution, "classification": classification, "role_text": team.get("role_text"),
                    "role_basis": team.get("role_basis"), "assignments": assignments, "population_state": state,
                    "join": join, "team_raw": row["team_raw"], "team_char_span": team_span,
                    "team_byte_span": [staff_record.byte_offset(text, team_span[0]),
                                       staff_record.byte_offset(text, team_span[1])]
                    if team_span[0] is not None else None,
                    # An inherited date is the parent line's text, so its span is the parent's (named in date_parent).
                    "years_char_span": row["years_span"] or (parent or {}).get("years_span"),
                    "wikitext_sha256": parsed["wikitext_sha256"],
                    "raw_file": str(path), "raw_file_sha256": sha256_bytes(raw_bytes),
                    "parser_version": parsed["parser_version"], "evidence_class": cs.EVIDENCE_CLASS,
                    "pit_admitted": False,
                    "start_state": interval.get("start_state"), "end_state": interval.get("end_state"),
                    "start_bounds": interval.get("start_bounds"), "end_bounds": interval.get("end_bounds"),
                    "start_qualifier": interval.get("start_qualifier"), "end_qualifier": interval.get("end_qualifier"),
                    "definite_first_season": interval.get("definite_first_season"),
                    "definite_last_season": interval.get("definite_last_season"),
                    "possible_first_season": possible_first, "possible_last_season": possible_last,
                    "bounds_consistent": interval.get("bounds_consistent"),
                    "uncertainty_classes": uncertainty_classes(team, interval),
                    "unresolved_parentheticals": team.get("unresolved_parentheticals") or [],
                    "employer_qualifier_kinds": team.get("employer_qualifier_kinds") or [],
                    "role_parentheticals": team.get("role_parentheticals") or [],
                    "career_field": row.get("list_field") or ("variant" if row["index"] >= career_infobox.VARIANT_FIELD_INDEX_OFFSET
                                                              else "numbered"),
                    "date_basis": row.get("date_basis"),
                    "date_parent": parent,
                    "unresolved_date_templates": unresolved,
                    # Builder-only (not a column): the employer line a dated role line was split from.
                    "_role_line_of": (f"{page['pageid']}:{page['wikimedia_revision']}:{row['family']}:"
                                      f"{row['role_line_of_index']}" if row.get("role_line_of_index") is not None
                                      else None),
                })
    stats = {"pages": len(pages), "duplicate_page_entries_read_once": duplicates, "pages_missing_raw": missing_raw,
             "raw_index": index_stats, "successor_episodes": len(episodes)}
    return episodes, stats


def _group(episodes: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_locator: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for episode in episodes:
        by_locator[episode["locator"]].append(episode)
    for rows in by_locator.values():
        rows.sort(key=lambda e: e["interval_index"])
    return by_locator


def _role_lines(episodes: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """The rows of dated role lines split from each employer line, by the employer line's locator."""

    by_parent: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for episode in episodes:
        if episode.get("_role_line_of"):
            by_parent[episode["_role_line_of"]].append(episode)
    for rows in by_parent.values():
        rows.sort(key=lambda e: e["episode_id"])
    return by_parent


def _role_line_change(split: list[dict[str, Any]], old_role_text: Any, old_key: str, new_key: str) -> dict[str, Any]:
    return {"role_lines": {old_key: old_role_text,
                           new_key: [[e["episode_id"], e["role_text"], e["start"], e["end"], e["date_basis"]]
                                     for e in split]}}


#: Text a revision does not display (the reconciliation's own rule, not the parser's): HTML comments -- an unclosed
#: one hides the rest of the page -- and <nowiki> spans, whose markup is literal.
_HIDDEN = re.compile(r"<!--.*?(?:-->|\Z)|<nowiki>.*?</nowiki>", re.I | re.S)
_HIDDEN_SPANS: dict[str, list[tuple[int, int, str]]] = {}
_PARAMS: dict[str, list[tuple[str, int, int]]] = {}
#: The career family each infobox parameter records (a naming table for the reconciliation).
_FIELD_FAMILY = re.compile(r"^(?:(?P<coach>coach(?:ing)?_?(?:years|team)\d+|pastcoaching)|"
                           r"(?P<player>play(?:er|ing)_?(?:years|team)\d+|pastteams)|"
                           r"(?P<admin>(?:admin(?:istrating)?|executive)_?(?:years|team)\d+|pastexecutives?|pastadmin))$")


def hidden_spans(raw_file: str) -> list[tuple[int, int, str]]:
    """(start, end, kind) of every span of the revision text that the revision does not display."""

    if raw_file not in _HIDDEN_SPANS:
        try:
            record = next(iter(json.loads(Path(raw_file).read_bytes())["query"]["pages"].values()))
            text = record["revisions"][0]["slots"]["main"]["*"]
        except (OSError, ValueError, KeyError, IndexError, StopIteration):
            text = ""
        _HIDDEN_SPANS[raw_file] = [(m.start(), m.end(), "NOWIKI" if m.group(0).lower().startswith("<nowiki")
                                    else "HTML_COMMENT") for m in _HIDDEN.finditer(text)]
        # The infobox parameters as the census tokenizer reads them once hidden text is literal.
        literal = _HIDDEN.sub(lambda m: re.sub(r"[{}\[\]|]", " ", m.group(0)), text)
        _PARAMS[raw_file] = [(name, start, end) for _box, a, b in template_tool.infoboxes(literal)
                             for name, start, end in template_tool.params(literal, a, b)]
    return _HIDDEN_SPANS[raw_file]


def parameter_at(raw_file: str, position: int) -> str | None:
    hidden_spans(raw_file)
    return next((name for name, a, b in _PARAMS[raw_file] if a <= position <= b), None)


def hidden_at(raw_file: Any, position: Any) -> str | None:
    """The kind of hidden text at ``position`` of the revision, if any."""

    if not raw_file or not isinstance(position, int):
        return None
    return next((kind for a, b, kind in hidden_spans(str(raw_file)) if a <= position < b), None)


def not_produced_reason(raw_file: Any, family: Any, spans: list[Any]) -> tuple[str, str]:
    """(code, reason) for a row the Attempt 5 parser does not produce, from the row's own raw locator."""

    positions = []
    for span in spans:
        if isinstance(span, str):
            try:
                span = json.loads(span)
            except ValueError:
                span = None
        if isinstance(span, list) and span and isinstance(span[0], int):
            positions.append(span[0])
    for position in positions:
        kind = hidden_at(raw_file, position)
        if kind:
            return ("READ_FROM_TEXT_THE_REVISION_DOES_NOT_DISPLAY",
                    f"the row was read from text inside {'an HTML comment' if kind == 'HTML_COMMENT' else 'a <nowiki> span'} "
                    f"at character {position}, which the revision does not display (a commented-out infobox or "
                    f"literal markup); the {career_infobox.PARSER_VERSION} parser reads displayed text only")
    for position in positions:
        name = parameter_at(str(raw_file), position) if raw_file else None
        match = _FIELD_FAMILY.match(name or "")
        stated = {"coach": "COACHING", "player": "PLAYING", "admin": "ADMINISTRATIVE"}.get(
            match.lastgroup if match else "", None)
        if stated != family:
            return ("READ_ACROSS_A_PARAMETER_BOUNDARY",
                    f"the row's raw text at character {position} is in parameter {name!r} "
                    f"({stated or 'not a career field'}), not a {family} field, once <nowiki> and comment text is "
                    "read as literal: an earlier parser let a literal '{{' swallow the parameters after it")
    return ("NO_ROW_AT_THIS_LOCATOR", f"the {career_infobox.PARSER_VERSION} parser produces no row at this locator")


def predecessor_dispositions(predecessor_rows: list[dict[str, Any]], episodes: list[dict[str, Any]],
                             manager: dict[str, set[str]]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """One disposition per delivered predecessor episode (the Attempt 4 rule, :func:`a4b.dispositions`, with an
    assignment's version-only keys not counted as a change), and the predecessor ids of each Attempt 5 row."""

    by_locator_new = _group(episodes)
    by_role_lines = _role_lines(episodes)
    by_locator_old: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in predecessor_rows:
        row["_decoded"] = a4b.decoded_predecessor(row)
        locator, number = a4b.predecessor_locator(row)
        row["_locator"], row["_number"] = locator, number
        by_locator_old[locator].append(row)
    derived: dict[str, list[str]] = collections.defaultdict(list)
    out = []
    for locator, old_rows in by_locator_old.items():
        old_rows.sort(key=lambda r: r["_number"])
        new_rows = by_locator_new.get(locator, [])
        for row in old_rows:
            screen = a4b.screens_for(row, manager)
            digest = cs.predecessor_row_digest(row)
            if not new_rows:
                code, reason = not_produced_reason(row["_decoded"].get("raw_file"), row["_decoded"].get("family"),
                                                   [row["_decoded"].get("team_char_span"),
                                                    row["_decoded"].get("years_char_span")])
                out.append({"predecessor_episode_id": row["episode_id"], "disposition": cs.NOT_PRODUCED,
                            "successor_episode_ids": [], "changed_fields": {}, "predecessor_row_sha256": digest,
                            "screens": screen, "reason": f"{code}: {reason}"})
                continue
            restructured = len(new_rows) != len(old_rows)
            mapped = new_rows if restructured else [new_rows[row["_number"]]]
            split = by_role_lines.get(locator, [])
            for episode in mapped + split:
                derived[episode["episode_id"]].append(row["episode_id"])
            if restructured:
                changed = {"intervals": {"predecessor": [[r["_decoded"].get("start"), r["_decoded"].get("end"),
                                                          r["_decoded"].get("years_as_written")] for r in old_rows],
                                         "successor": [[e["start"], e["end"], e["start_state"], e["end_state"],
                                                        e["years_as_written"]] for e in new_rows]}}
                state, reason = cs.RESTRUCTURED, (f"the row's years now read as {len(new_rows)} interval(s) where "
                                                  f"the predecessor had {len(old_rows)}")
            else:
                old = {key: semantic(key, row["_decoded"].get(key)) for key in a4b.COMPARED}
                new = comparable(mapped[0], a4b.COMPARED)
                changed = {key: {"predecessor": old[key], "successor": new[key]} for key in a4b.COMPARED
                           if old[key] != new[key]}
                if split:
                    changed.update(_role_line_change(split, row["_decoded"].get("role_text"), "predecessor", "successor"))
                if not changed:
                    state = cs.UNCHANGED
                    reason, _ = a4b.unchanged_basis(screen, mapped[0])
                elif mapped[0]["uncertainty_classes"]:
                    state, reason = cs.UNRESOLVED_EXPLICIT, ("the successor states an unresolved role, date or "
                                                             f"uncertain bound ({mapped[0]['uncertainty_classes']}) "
                                                             "where the predecessor stated a definite value")
                else:
                    state, reason = cs.CORRECTED, f"changed: {sorted(changed)}"
            if split:
                reason += ("; the employer line's role lines state their own dates and are read as their own rows "
                           f"({len(split)})")
            out.append({"predecessor_episode_id": row["episode_id"], "disposition": state,
                        "successor_episode_ids": [e["episode_id"] for e in mapped + split], "changed_fields": changed,
                        "predecessor_row_sha256": digest, "screens": screen, "reason": reason})
    return out, derived


def load_a04(path: Path) -> list[dict[str, Any]]:
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute(f"SELECT * FROM {cs.EPISODE_TABLE} ORDER BY episode_id")]
    finally:
        conn.close()


def a04_locator(identity: str) -> tuple[str, int]:
    match = re.match(r"^C37A04:(\d+):(\d+):([A-Z]+):(\d+):(\d+)$", identity)
    if not match:
        raise ValueError(f"unexpected Attempt 4 identity {identity!r}")
    return f"{match.group(1)}:{match.group(2)}:{match.group(3)}:{match.group(4)}", int(match.group(5))


def a04_mapping(a4_rows: list[dict[str, Any]], episodes: list[dict[str, Any]],
                screens: dict[str, set[str]]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """One row per Attempt 4 episode: unchanged, corrected, made explicitly unresolved, restructured or not
    produced, with each changed field's two values, the Attempt 4 row's stored-content digest and its screens."""

    by_locator_new = _group(episodes)
    by_role_lines = _role_lines(episodes)
    by_locator_old: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in a4_rows:
        by_locator_old[a04_locator(str(row["episode_id"]))[0]].append(row)
    derived: dict[str, list[str]] = collections.defaultdict(list)
    out = []
    for locator, old_rows in by_locator_old.items():
        old_rows.sort(key=lambda r: a04_locator(str(r["episode_id"]))[1])
        new_rows = by_locator_new.get(locator, [])
        for row in old_rows:
            identity = str(row["episode_id"])
            number = a04_locator(identity)[1]
            member_of = [name for name, ids in sorted(screens.items()) if identity in ids]
            digest = cs.episode_row_digest(row)
            if not new_rows:
                code, reason = not_produced_reason(row.get("raw_file"), row.get("family"),
                                                   [row.get("team_char_span"), row.get("years_char_span")])
                out.append({"a04_episode_id": identity, "disposition": cs.NOT_PRODUCED, "a05_episode_ids": [],
                            "changed_fields": {}, "a04_row_sha256": digest, "screens": member_of,
                            "reason": f"{code}: {reason}"})
                continue
            restructured = len(new_rows) != len(old_rows)
            mapped = new_rows if restructured else [new_rows[number]]
            split = by_role_lines.get(locator, [])
            for episode in mapped + split:
                derived[episode["episode_id"]].append(identity)
            if restructured:
                changed = {"intervals": {"a04": [[r.get("start"), r.get("end"), r.get("start_state"),
                                                  r.get("end_state"), r.get("years_as_written")] for r in old_rows],
                                         "a05": [[e["start"], e["end"], e["start_state"], e["end_state"],
                                                  e["years_as_written"]] for e in new_rows]}}
                state = cs.RESTRUCTURED
                reason = f"the row's years now read as {len(new_rows)} interval(s) where Attempt 4 had {len(old_rows)}"
            else:
                old = comparable(row, A04_COMPARED, A04_JSON_COLUMNS)
                new = comparable(mapped[0], A04_COMPARED)
                changed = {key: {"a04": old[key], "a05": new[key]} for key in A04_COMPARED if old[key] != new[key]}
                if split:
                    changed.update(_role_line_change(split, old.get("role_text"), "a04", "a05"))
                added = sorted(set(new["uncertainty_classes"] or []) - set(old["uncertainty_classes"] or []))
                if not changed:
                    state, reason = cs.UNCHANGED, "every compared field is equal"
                elif added:
                    state, reason = cs.UNRESOLVED_EXPLICIT, (f"the successor now states {added} where Attempt 4 "
                                                             f"stated a definite value; changed: {sorted(changed)}")
                else:
                    state, reason = cs.CORRECTED, f"changed: {sorted(changed)}"
            if split:
                reason += ("; the employer line's role lines state their own dates and are read as their own rows "
                           f"({len(split)})")
            out.append({"a04_episode_id": identity, "disposition": state,
                        "a05_episode_ids": [e["episode_id"] for e in mapped + split], "changed_fields": changed,
                        "a04_row_sha256": digest, "screens": member_of, "reason": reason})
    return out, derived


# ---- checks that do not use the parser or the taxonomy ----

def season_template_forms(text: str, names: set[str] | frozenset[str]) -> list[dict[str, Any]]:
    """Each season template in ``text`` (read by the census tokenizer) with the form its arguments state."""

    out = []
    for occurrence in template_tool.templates(text, 0, len(text)):
        name = re.sub(r"[\s_]+", " ", occurrence["name_key"]).strip()
        if name not in names:
            continue
        args = occurrence["positional"]
        if occurrence["named"] or not args or not _YEAR.match(args[0]) or len(args) > 2:
            form: tuple[Any, ...] = ("UNSUPPORTED",)
        elif len(args) == 1:
            form = ("SEASON", int(args[0]))
        elif _YEAR.match(args[1]):
            form = ("RANGE", int(args[0]), int(args[1]))
        elif args[1].casefold() in ("present", "current"):
            form = ("TO_PRESENT", int(args[0]))
        elif args[1] == "":
            form = ("OPEN_END", int(args[0]))
        else:
            form = ("UNSUPPORTED",)
        out.append({"raw": occurrence["raw"], "name": name, "positional": args, "named": occurrence["named"],
                    "span": occurrence["span"], "form": list(form)})
    return out


def form_is_read(form: list[Any], raw: str, rows: list[dict[str, Any]]) -> bool:
    """Whether some row reads a template of this form as the form states."""

    kind = form[0]
    if kind == "SEASON":
        return any(form[1] in (e["start"], e["end"]) for e in rows)
    if kind == "RANGE":
        return any(e["start"] == form[1] and e["end"] == form[2] for e in rows)
    if kind == "TO_PRESENT":
        return any(e["start"] == form[1] and e["ongoing"] for e in rows)
    if kind == "OPEN_END":
        return any(e["start"] == form[1] and e["end_state"] == career_infobox.UNKNOWN for e in rows)
    return any(career_infobox.UNRESOLVED_TEMPLATE in (e["start_state"], e["end_state"])
               and raw in (e.get("unresolved_date_templates") or []) for e in rows)


def independent_side(title: str) -> str | None:
    """The side a raw title states for its passing-game coordinator, by this screen's own rule: the words between
    the previous separator and "pass(ing) game coordinator"."""

    for match in re.finditer(r"pass(?:ing)?\s+game\s+coordinator", title, re.I):
        before = re.split(r"/|&|,|;|\band\b|\|", title[:match.start()], flags=re.I)[-1].lower()
        sides = {side for side, words in (("DEFENSE", ("defensive", "defense")), ("OFFENSE", ("offensive", "offense")))
                 if any(word in before for word in words)}
        if len(sides) == 1:
            return next(iter(sides))
    return None


def _assignments(value: Any) -> list[dict[str, Any]]:
    decoded = json.loads(value) if isinstance(value, str) else (value or [])
    return [item for item in decoded if isinstance(item, dict)]


def screen_accounting(a4_rows: list[dict[str, Any]], mapping: list[dict[str, Any]], episodes: list[dict[str, Any]],
                      semantic_census: dict[str, Any]) -> dict[str, Any]:
    """The manager's two Attempt 4 screens, member by member."""

    by_id = {str(r["a04_episode_id"]): r for r in mapping}
    episode_by_id = {e["episode_id"]: e for e in episodes}
    a4_by_id = {str(r["episode_id"]): r for r in a4_rows}
    by_locator_new = _group(episodes)
    by_role_lines = _role_lines(episodes)
    names = {re.sub(r"[\s_]+", " ", name).strip().casefold() for name in semantic_census["template_types"]}
    template_members = []
    for member in semantic_census["range_rows"]:
        identity = member["episode_id"]
        row = by_id.get(identity) or {}
        a4 = a4_by_id.get(identity) or {}
        locator = a04_locator(identity)[0]
        # The rows the line now reads to: its own, and any dated role line split from it.
        at_locator = by_locator_new.get(locator, []) + by_role_lines.get(locator, [])
        # The date the raw line states for itself: a list line's own text (its team_raw is the whole line), or a
        # numbered years field. A list line that states no season template of its own inherits its parent's.
        list_row = str(a4.get("career_field") or "") in career_infobox.LIST_FIELDS
        own = season_template_forms(str(member.get("team_raw") or ""), names) if list_row else []
        years_forms = season_template_forms(str(member.get("years_raw") or ""), names)
        forms = own if own else years_forms
        source = ("THE_LIST_LINE_ITSELF" if own else "THE_PARENT_LINE_INHERITED" if list_row
                  else "THE_NUMBERED_YEARS_FIELD")
        if str(row.get("reason") or "").startswith("READ_FROM_TEXT_THE_REVISION_DOES_NOT_DISPLAY"):
            source = "TEXT_THE_REVISION_DOES_NOT_DISPLAY"
        reads = [{"raw": f["raw"], "form": f["form"], "read": form_is_read(f["form"], f["raw"], at_locator)}
                 for f in forms]
        endpoint = str(member.get("template_endpoint") or "")
        manager_years_are_the_lines_own = (not list_row or not own
                                           or {f["raw"] for f in years_forms} <= {f["raw"] for f in own})
        endpoint_read = (None if not manager_years_are_the_lines_own or source == "TEXT_THE_REVISION_DOES_NOT_DISPLAY"
                         else
                         any(e["end"] == int(endpoint) for e in at_locator) if _YEAR.match(endpoint) else
                         any(e["ongoing"] for e in at_locator) if endpoint.casefold() in ("present", "current") else
                         None)
        mapped = [episode_by_id[i] for i in row.get("a05_episode_ids", [])]
        template_members.append({
            "a04_episode_id": identity, "person": member.get("person_display"), "years_raw": member.get("years_raw"),
            "a04_interval": [a4.get("start"), a4.get("end"), a4.get("ongoing")],
            "manager_template_endpoint": member.get("template_endpoint"),
            "manager_collapsed_to_first": member.get("collapsed_to_first"),
            "disposition": row.get("disposition"), "a05_episode_ids": row.get("a05_episode_ids"),
            "a05_intervals": [[e["start"], e["end"], e["ongoing"], e["start_state"], e["end_state"]] for e in mapped],
            "templates_in_the_row_read_by_the_census_tokenizer": reads, "template_source": source,
            "every_template_read_as_its_form_states": (source == "TEXT_THE_REVISION_DOES_NOT_DISPLAY"
                                                       or (bool(reads) and all(r["read"] for r in reads))),
            "manager_years_are_the_lines_own_date": manager_years_are_the_lines_own,
            "manager_endpoint_read_at_this_locator": endpoint_read,
        })
    defensive_members = []
    for member in semantic_census["defensive_pass_game_rows"]:
        identity = member["episode_id"]
        row = by_id.get(identity) or {}
        mapped = [episode_by_id[i] for i in row.get("a05_episode_ids", [])]
        title = member["assignment"].get("source_title") or ""
        expected = independent_side(title)
        units = [(a.get("unit"), a.get("unit_basis"), a.get("unit_words")) for e in mapped
                 for a in e["assignments"] if a.get("role") == "pass_game_coordinator"]
        defensive_members.append({
            "a04_episode_id": identity, "person": member.get("person_display"),
            "employer": member.get("employer_display"), "title": title,
            "a04_unit": member["assignment"].get("unit"), "independent_side_from_the_raw_title": expected,
            "a05_units": units, "disposition": row.get("disposition"), "a05_episode_ids": row.get("a05_episode_ids"),
            "population_division_and_employer": [
                {"population_state": e["population_state"],
                 "divisions": (e.get("classification") or {}).get("divisions"), "employer_kind": e["employer_kind"]}
                for e in mapped],
            "holds": bool(units) and expected is not None and all(unit == expected for unit, _, _ in units),
        })
    return {
        SCREEN_TEMPLATE: {
            "expected": SCREEN_EXPECTED[SCREEN_TEMPLATE], "members": len(template_members),
            "without_disposition": [m["a04_episode_id"] for m in template_members if not m["disposition"]],
            "by_disposition": dict(collections.Counter(m["disposition"] for m in template_members)),
            "template_not_read_as_its_form_states": [m["a04_episode_id"] for m in template_members
                                                     if not m["every_template_read_as_its_form_states"]],
            "manager_endpoint_not_read": [m["a04_episode_id"] for m in template_members
                                          if m["manager_endpoint_read_at_this_locator"] is False],
            "manager_years_not_the_lines_own_date": [m["a04_episode_id"] for m in template_members
                                                     if not m["manager_years_are_the_lines_own_date"]],
            "forms": dict(collections.Counter(r["form"][0] for m in template_members
                                              for r in m["templates_in_the_row_read_by_the_census_tokenizer"])),
            "template_sources": dict(collections.Counter(m["template_source"] for m in template_members)),
            "check": ("each season template the raw line states for itself (a list line's own text, else the parent "
                      "line it inherits, or the numbered years field) is read by the census tokenizer, not the "
                      "parser, and must be read as its form states by some Attempt 5 row at the row's locator; the "
                      "manager's recorded endpoint must be read there too unless the Attempt 4 years it came from "
                      "were a parent line's date written over the line's own (MF37A04-03)"),
            "rows": template_members,
        },
        SCREEN_DEFENSIVE: {
            "expected": SCREEN_EXPECTED[SCREEN_DEFENSIVE], "members": len(defensive_members),
            "without_disposition": [m["a04_episode_id"] for m in defensive_members if not m["disposition"]],
            "by_a04_unit": dict(collections.Counter(m["a04_unit"] for m in defensive_members)),
            "by_a05_unit": dict(collections.Counter(u for m in defensive_members for u, _, _ in m["a05_units"])),
            "independent_side_differs_or_absent": [m["a04_episode_id"] for m in defensive_members if not m["holds"]],
            "check": ("the side is read from the raw title by this screen's own rule (the words before 'pass(ing) "
                      "game coordinator' back to the previous separator), not by the taxonomy"),
            "rows": defensive_members,
        },
    }


def template_census_reconciliation(template_census: Path, episodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Every season template the independent census found in a career field, and every nested list line,
    reconciled against the successor rows: a template by the rows whose years span contains its own span (no
    locator mapping and no parser code), a nested line by its locator and the date form the census saw."""

    summary = json.loads(template_census.read_text(encoding="utf-8"))
    rows_file = Path(summary["template_rows_file"])
    items_file = Path(summary["list_items_file"])
    spans: dict[tuple[str, str], list[tuple[int, int, dict[str, Any]]]] = collections.defaultdict(list)
    for episode in episodes:
        span = episode.get("years_char_span")
        if span and span[0] is not None:
            spans[(str(episode["pageid"]), str(episode["revision"]))].append((span[0], span[1], episode))
    by_locator = _group(episodes)
    counts: collections.Counter = collections.Counter()
    examples: dict[str, list[Any]] = collections.defaultdict(list)

    def example(name: str, value: Any, limit: int = 40) -> None:
        if len(examples[name]) < limit:
            examples[name].append(value)

    # A season template inside a footnote or citation template is the note's, not a date of the row.
    notes: dict[tuple[str, str], list[tuple[int, int]]] = collections.defaultdict(list)
    with rows_file.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                if _NOTE_TEMPLATE.match(row["name_key"]):
                    notes[(row["pageid"], row["revision"])].append(tuple(row["span"]))
    with rows_file.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            name = re.sub(r"[\s_]+", " ", row["name_key"]).strip()
            if name not in career_infobox.SEASON_TEMPLATES or not row["year_bearing"]:
                continue
            forms = season_template_forms(row["raw"], {name})
            if not forms:
                continue
            form = forms[0]["form"]
            counts[f"season_templates::{row['field_kind']}"] += 1
            lo, hi = row["span"]
            if any(a < lo and hi <= b for a, b in notes.get((row["pageid"], row["revision"]), [])):
                counts[f"inside_a_note_template_not_a_date::{row['field_kind']}"] += 1
                example("inside_a_note_template_not_a_date", {"pageid": row["pageid"], "raw": row["raw"]})
                continue
            containing = [e for a, b, e in spans.get((row["pageid"], row["revision"]), []) if a <= lo and hi <= b]
            hidden = hidden_at(row.get("raw_file"), lo)
            if not containing and hidden:
                counts[f"inside_text_the_revision_does_not_display::{hidden}"] += 1
                example(f"inside_text_the_revision_does_not_display::{hidden}",
                        {"pageid": row["pageid"], "field": row["field"], "raw": row["raw"][:80]})
                continue
            if not containing:
                counts[f"not_inside_any_row_years_span::{row['field_kind']}"] += 1
                example(f"not_inside_any_row_years_span::{row['field_kind']}",
                        {"pageid": row["pageid"], "revision": row["revision"], "field": row["field"], "raw": row["raw"]})
                continue
            read = form_is_read(form, row["raw"], containing)
            counts[f"{form[0]}::{'read_as_stated' if read else 'not_read_as_stated'}"] += 1
            if not read:
                example(f"{form[0]}::not_read_as_stated", {
                    "pageid": row["pageid"], "revision": row["revision"], "field": row["field"], "raw": row["raw"],
                    "rows": [[e["episode_id"], e["start"], e["end"], e["ongoing"], e["start_state"], e["end_state"],
                              e["years_as_written"]] for e in containing[:4]]})
    with items_file.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            if item["depth"] < 2:
                continue
            counts["nested_items"] += 1
            family = career_infobox.LIST_FIELDS.get(item["field"])
            base = career_infobox.LIST_FIELD_INDEX_BASE.get(item["field"], 1000)
            locator = f"{item['pageid']}:{item['revision']}:{family}:{base + int(item['item'])}"
            found = by_locator.get(locator, [])
            form = ("BALANCED" if item["dated_parenthetical_balanced"] else
                    "UNBALANCED" if item["years_outside_links"] else "NONE")
            expected = {"BALANCED": "CHILD_DATE_IN_BALANCED_PARENTHESES",
                        "UNBALANCED": "CHILD_DATE_WITHOUT_BALANCED_PARENTHESES",
                        "NONE": "INHERITED_FROM_PARENT_ITEM"}[form]
            bases = sorted({str(e.get("date_basis")) for e in found})
            parent_named = all(e.get("date_parent") for e in found) if form == "NONE" else True
            if item["parent_item"] is None:
                state = "NO_PARENT_ITEM_ABOVE_IT"
            elif not found:
                state = "NO_ROW"
            elif bases == [expected] and parent_named:
                state = "CONSISTENT"
            else:
                state = "INCONSISTENT"
            counts[f"nested::{form}::{state}"] += 1
            if state != "CONSISTENT":
                example(f"nested::{form}::{state}", {"locator": locator, "bases": bases, "body": item["body"][:200]})
    return {"template_census": str(template_census), "template_census_sha256": sha256_bytes(template_census.read_bytes()),
            "census_version": summary.get("census_version"),
            "template_rows_sha256_matches": sha256_bytes(rows_file.read_bytes()) == summary.get("template_rows_sha256"),
            "list_items_sha256_matches": sha256_bytes(items_file.read_bytes()) == summary.get("list_items_sha256"),
            "counts": dict(sorted(counts.items())), "examples": dict(examples)}


def a4_census_uncovered(census: Path, episodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Each numbered row of the Attempt 4 raw census with no Attempt 5 row, by cause read from its raw offsets."""

    locators = {e["locator"] for e in episodes}
    counts: collections.Counter = collections.Counter()
    other = []
    with census.with_name("CAREER_RAW_CENSUS_ROWS.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            family, offset = a4b.CENSUS_FAMILIES[str(row["family"]).lower()]
            locator = f"{row['pageid']}:{row['revision']}:{family}:{int(row['index']) + offset}"
            if locator in locators:
                continue
            kind = hidden_at(row.get("raw_file"), row.get("team_offset")) or \
                hidden_at(row.get("raw_file"), row.get("years_offset"))
            if kind:
                counts[f"inside_text_the_revision_does_not_display::{kind}"] += 1
            else:
                counts["no_row_for_another_reason"] += 1
                other.append({"locator": locator, "team_raw": str(row.get("team_raw") or "")[:160],
                              "years_raw": str(row.get("years_raw") or "")[:80]})
    return {"uncovered": sum(counts.values()), "by_cause": dict(counts), "other_examples": other[:40]}


def unit_changes(a4_rows: list[dict[str, Any]], mapping: list[dict[str, Any]],
                 episodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Every assignment whose unit differs between an Attempt 4 row and the Attempt 5 row(s) it maps to."""

    episode_by_id = {e["episode_id"]: e for e in episodes}
    a4_by_id = {str(r["episode_id"]): r for r in a4_rows}
    counts: collections.Counter = collections.Counter()
    contexts: collections.Counter = collections.Counter()
    rows = []
    for row in mapping:
        if not row["a05_episode_ids"]:
            continue
        old = {a.get("role"): a.get("unit") for a in _assignments(a4_by_id[row["a04_episode_id"]]["assignments"])}
        new_episode = episode_by_id[row["a05_episode_ids"][0]]
        for assignment in new_episode["assignments"]:
            role = assignment.get("role")
            if role in old and old[role] != assignment.get("unit"):
                counts[f"{role}: {old[role]} -> {assignment.get('unit')} ({assignment.get('unit_basis')})"] += 1
                divisions = ",".join(sorted((new_episode.get("classification") or {}).get("divisions") or [])) or "-"
                contexts[f"{new_episode['population_state']}|{divisions}|{new_episode['employer_kind']}"] += 1
                rows.append({"a04_episode_id": row["a04_episode_id"], "a05_episode_ids": row["a05_episode_ids"],
                             "role": role, "a04_unit": old[role], "a05_unit": assignment.get("unit"),
                             "unit_basis": assignment.get("unit_basis"), "unit_words": assignment.get("unit_words"),
                             "title": assignment.get("source_title")})
    return {"total": len(rows), "changes": dict(counts.most_common()),
            "by_population_division_employer": dict(contexts.most_common()), "rows": rows}


def staff_descendants(database: Path) -> dict[str, Any]:
    """The delivered release's staff role rows whose unit the v37.5 taxonomy states differently for the same title.
    The release is only read: these are affected descendants, recorded for the owner, not rebuilt or activated."""

    conn = sqlite3.connect(f"file:{database.resolve().as_posix()}?mode=ro&immutable=1", uri=True)
    try:
        rows = conn.execute("SELECT a.assignment_id, a.observation_id, a.role_code, a.unit, o.source_title, "
                            "o.program_id, o.season FROM staff_role_assignment a JOIN staff_observation o "
                            "ON o.observation_id = a.observation_id ORDER BY a.assignment_id").fetchall()
    finally:
        conn.close()
    changed, counts, absent = [], collections.Counter(), collections.Counter()
    cache: dict[str, dict[str, dict[str, Any]]] = {}
    for assignment_id, observation_id, role, unit, title, program, season in rows:
        key = str(title or "")
        if key not in cache:
            cache[key] = {a["role"]: a for a in staff_record.assignments_v37(key)}
        new = cache[key].get(role)
        if new is None:
            absent[role] += 1
            continue
        if new["unit"] != unit:
            counts[f"{role}: {unit} -> {new['unit']} ({new['unit_basis']})"] += 1
            changed.append({"assignment_id": assignment_id, "observation_id": observation_id, "role": role,
                            "delivered_unit": unit, "v37_5_unit": new["unit"], "unit_basis": new["unit_basis"],
                            "unit_words": new["unit_words"], "source_title": title, "program_id": program,
                            "season": season})
    return {"database": str(database), "staff_role_assignments": len(rows), "affected": len(changed),
            "by_change": dict(counts.most_common()),
            "delivered_roles_not_emitted_for_the_stored_title": dict(absent.most_common()),
            "rows": changed,
            "disposition": ("AFFECTED_DESCENDANT_NOT_REBUILT: the delivered release keeps its bytes and its default "
                            "answers; a staff successor under the v37.5 taxonomy is a separate owner decision. The "
                            "stored source_title is re-read, so a role the release derived from other text is "
                            "counted, not compared.")}


def write_successor(episodes: list[dict[str, Any]], dispositions: list[dict[str, Any]], mapping: list[dict[str, Any]],
                    identity: dict[str, str]) -> bytes:
    """The successor, built in memory; returns its serialized bytes (the same for the same inputs)."""

    conn = sqlite3.connect(":memory:")
    try:
        conn.execute(f"CREATE TABLE {cs.IDENTITY_TABLE} (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute(f"CREATE TABLE {cs.A05_EPISODE_TABLE} "
                     f"({', '.join(chr(34) + c + chr(34) for c in cs.A05_EPISODE_COLUMNS)})")
        conn.execute(f"CREATE TABLE {cs.A05_DISPOSITION_TABLE} ({', '.join(cs.DISPOSITION_COLUMNS)})")
        conn.execute(f"CREATE TABLE {cs.A05_FROM_A04_TABLE} ({', '.join(cs.A04_MAP_COLUMNS)})")
        for episode in sorted(episodes, key=lambda e: e["episode_id"]):
            values = []
            for column in cs.A05_EPISODE_COLUMNS:
                value = episode.get(column)
                if column in A05_JSON_COLUMNS:
                    value = None if value is None else json.dumps(value, sort_keys=True)
                elif isinstance(value, bool):
                    value = int(value)
                values.append(value)
            conn.execute(f"INSERT INTO {cs.A05_EPISODE_TABLE} VALUES ({', '.join('?' for _ in cs.A05_EPISODE_COLUMNS)})",
                         values)
        for row in sorted(dispositions, key=lambda r: r["predecessor_episode_id"]):
            conn.execute(f"INSERT INTO {cs.A05_DISPOSITION_TABLE} VALUES ({', '.join('?' for _ in cs.DISPOSITION_COLUMNS)})",
                         [row["predecessor_episode_id"], row["disposition"], json.dumps(row["successor_episode_ids"]),
                          json.dumps(row["changed_fields"], sort_keys=True, default=str), row["predecessor_row_sha256"],
                          json.dumps(row["screens"]), row["reason"]])
        for row in sorted(mapping, key=lambda r: r["a04_episode_id"]):
            conn.execute(f"INSERT INTO {cs.A05_FROM_A04_TABLE} VALUES ({', '.join('?' for _ in cs.A04_MAP_COLUMNS)})",
                         [row["a04_episode_id"], row["disposition"], json.dumps(row["a05_episode_ids"]),
                          json.dumps(row["changed_fields"], sort_keys=True, default=str), row["a04_row_sha256"],
                          json.dumps(row["screens"]), row["reason"]])
        conn.execute(f"CREATE UNIQUE INDEX a05_episode_id ON {cs.A05_EPISODE_TABLE}(episode_id)")
        conn.execute(f"CREATE UNIQUE INDEX a05_disposition_id ON {cs.A05_DISPOSITION_TABLE}(predecessor_episode_id)")
        conn.execute(f"CREATE UNIQUE INDEX a05_from_a04_id ON {cs.A05_FROM_A04_TABLE}(a04_episode_id)")
        conn.commit()
        for table, columns, key in ((cs.A05_EPISODE_TABLE, cs.A05_EPISODE_COLUMNS, "episode_id"),
                                    (cs.A05_DISPOSITION_TABLE, cs.DISPOSITION_COLUMNS, "predecessor_episode_id"),
                                    (cs.A05_FROM_A04_TABLE, cs.A04_MAP_COLUMNS, "a04_episode_id")):
            digest, count = cs.table_ledger(conn, table, columns, key)
            identity[f"ledger::{table}::sha256"] = digest
            identity[f"ledger::{table}::rows"] = str(count)
        conn.executemany(f"INSERT INTO {cs.IDENTITY_TABLE} VALUES (?, ?)", sorted(identity.items()))
        conn.commit()
        return bytes(conn.serialize())
    finally:
        conn.close()


def _write_jsonl_gz(path: Path, rows: list[dict[str, Any]], key: str) -> str:
    # mtime=0 and no file name in the header: the same rows give the same bytes.
    with path.open("xb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
        for row in sorted(rows, key=lambda r: r[key]):
            handle.write((json.dumps(row, sort_keys=True, default=str, ensure_ascii=False) + "\n").encode("utf-8"))
    return cs.sha256_file(path)


def build(out: Path, *, census: Path, template_census: Path, compare_to: Path | None = None) -> dict[str, Any]:
    before = cs.sha256_file(PREDECESSOR_DB)
    a4_before = cs.sha256_file(A4_SUCCESSOR)
    if before != PREDECESSOR_SHA256 or a4_before != A4_SUCCESSOR_SHA256:
        raise SystemExit(f"the predecessor ({before}) or the Attempt 4 successor ({a4_before}) is not the issued subject")
    manager_data = json.loads(a4b.MANAGER_SCREENS.read_text(encoding="utf-8"))
    manager = {"broad": {r["episode_id"] for r in manager_data["candidates"]},
               "specific": {r["episode_id"] for r in manager_data["specific_role_code_screen"]}}
    semantic_census = json.loads(A4_SEMANTIC_CENSUS.read_text(encoding="utf-8"))
    a4_screens = {SCREEN_TEMPLATE: {r["episode_id"] for r in semantic_census["range_rows"]},
                  SCREEN_DEFENSIVE: {r["episode_id"] for r in semantic_census["defensive_pass_game_rows"]}}
    started = utc_now()
    episodes, stats = successor_episodes()
    predecessor_rows = a4b.load_predecessor(PREDECESSOR_DB)
    rows, derived = predecessor_dispositions(predecessor_rows, episodes, manager)
    a4_rows = load_a04(A4_SUCCESSOR)
    mapping, from_a04 = a04_mapping(a4_rows, episodes, a4_screens)
    produced_by: dict[str, set[str]] = collections.defaultdict(set)
    for row in rows:
        for identity in row["successor_episode_ids"]:
            produced_by[identity].add(row["disposition"])
    a04_produced_by: dict[str, set[str]] = collections.defaultdict(set)
    for row in mapping:
        for identity in row["a05_episode_ids"]:
            a04_produced_by[identity].add(row["disposition"])
    for episode in episodes:
        parents = derived.get(episode["episode_id"], [])
        episode["predecessor_episode_ids"] = parents
        episode["lineage_state"] = cs.DERIVED if parents else cs.ADDED_STATES[cs.A05_FORMAT_VERSION]
        episode["disposition"] = ",".join(sorted(produced_by.get(episode["episode_id"], ()))) or "ADDED"
        a4_parents = from_a04.get(episode["episode_id"], [])
        episode["a04_episode_ids"] = a4_parents
        episode["a04_lineage_state"] = cs.A04_DERIVED if a4_parents else cs.A04_ADDED
        episode["a04_disposition"] = ",".join(sorted(a04_produced_by.get(episode["episode_id"], ()))) or "ADDED_IN_A05"
    identity = {
        "format_version": cs.A05_FORMAT_VERSION, "successor_version": cs.A05_SUCCESSOR_VERSION,
        "predecessor_database_sha256": PREDECESSOR_SHA256, "predecessor_database_path": str(PREDECESSOR_DB),
        "predecessor_release_version": PREDECESSOR_RELEASE_VERSION, "predecessor_table": cs.PREDECESSOR_TABLE,
        "predecessor_row_count": str(len(predecessor_rows)), "parser_version": career_infobox.PARSER_VERSION,
        "predecessor_parser_version": career_infobox.PREDECESSOR_PARSER_VERSION,
        "a04_parser_version": career_infobox.A4_PARSER_VERSION, "taxonomy_version": staff_record.TAXONOMY_VERSION,
        "a04_taxonomy_version": staff_record.PREDECESSOR_TAXONOMY_VERSION,
        "a04_successor_path": str(A4_SUCCESSOR), "a04_successor_sha256": A4_SUCCESSOR_SHA256,
        "a04_successor_row_count": str(len(a4_rows)),
        "identity_rule": (f"{cs.A05_IDENTITY_PREFIX}:<pageid>:<revision>:<family>:<row index>:<interval index>; never "
                          "a predecessor or Attempt 4 identity; each row names the delivered predecessor rows and the "
                          "Attempt 4 rows it derives from; each predecessor row and each Attempt 4 row has exactly "
                          "one disposition"),
        "default_activation": cs.NOT_ACTIVATED, "acceptance_state": cs.NOT_ACCEPTED,
        "evidence_class": cs.EVIDENCE_CLASS, "pit_admitted": "0", "builder_version": BUILDER_VERSION,
        "cycle_number": str(CYCLE_NUMBER), "attempt_number": str(ATTEMPT_NUMBER),
        # No build time: the same committed builder over the same cached bytes gives the same file.
    }
    data = write_successor(episodes, rows, mapping, identity)
    successor_sha256 = sha256_bytes(data)
    successor_path = out / "CAREER_SUCCESSOR_A05.sqlite"
    comparison = None
    files: dict[str, Any] = {}
    if compare_to is not None:
        delivered = cs.sha256_file(compare_to)
        comparison = {"compared_to": str(compare_to), "delivered_sha256": delivered, "rebuilt_sha256": successor_sha256,
                      "byte_identical": delivered == successor_sha256, "rebuilt_bytes": len(data),
                      "method": "rebuilt in memory and serialized; no second successor file was written"}
    else:
        with successor_path.open("xb") as handle:
            handle.write(data)
        files["dispositions"] = {"path": str(out / "CAREER_A05_DISPOSITIONS.jsonl.gz"),
                                 "sha256": _write_jsonl_gz(out / "CAREER_A05_DISPOSITIONS.jsonl.gz", rows,
                                                           "predecessor_episode_id")}
        files["a04_mapping"] = {"path": str(out / "CAREER_A05_FROM_A04.jsonl.gz"),
                                "sha256": _write_jsonl_gz(out / "CAREER_A05_FROM_A04.jsonl.gz", mapping,
                                                          "a04_episode_id")}
    after = cs.sha256_file(PREDECESSOR_DB)
    a4_after = cs.sha256_file(A4_SUCCESSOR)
    screens = screen_accounting(a4_rows, mapping, episodes, semantic_census)
    units = unit_changes(a4_rows, mapping, episodes)
    descendants = staff_descendants(PREDECESSOR_DB)
    summary = {
        "label": f"Cycle #{CYCLE_NUMBER} — Attempt #{ATTEMPT_NUMBER} — IN_PROGRESS — career successor build"
                 + (" (rebuild comparison)" if compare_to else ""),
        "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "builder_version": BUILDER_VERSION,
        "started_at": started, "finished_at": utc_now(),
        "predecessor": {"path": str(PREDECESSOR_DB), "sha256_before": before, "sha256_after": after,
                        "unchanged": before == after == PREDECESSOR_SHA256, "rows": len(predecessor_rows)},
        "a04_successor": {"path": str(A4_SUCCESSOR), "sha256_before": a4_before, "sha256_after": a4_after,
                          "unchanged": a4_before == a4_after == A4_SUCCESSOR_SHA256, "rows": len(a4_rows)},
        "inputs": {name: {"path": str(path), "sha256": sha256_bytes(path.read_bytes())} for name, path in (
            ("career_pages", reparse.CAREER_PAGES), ("staff_reparse", reparse.STAFF_REPARSE),
            ("crosswalk_rows", reparse.CROSSWALK_ROWS), ("historical_membership", reparse.HISTORICAL),
            ("manager_a3_screens", a4b.MANAGER_SCREENS), ("manager_a3_date_screen", a4b.MANAGER_DATE_SCREEN),
            ("manager_a4_semantic_census", A4_SEMANTIC_CENSUS), ("a4_raw_census", census),
            ("a5_template_census", template_census))},
        "parse": stats,
        "successor": {"path": None if compare_to else str(successor_path), "sha256": successor_sha256,
                      "bytes": len(data), "identity": identity, "episodes": len(episodes),
                      "episodes_new_without_predecessor": sum(1 for e in episodes if not e["predecessor_episode_ids"]),
                      "episodes_new_without_a04_row": sum(1 for e in episodes if not e["a04_episode_ids"])},
        "files": files,
        "rebuild_comparison": comparison,
        "dispositions": {"total": len(rows), "by_disposition": dict(collections.Counter(r["disposition"] for r in rows)),
                         "changed_field_counts": dict(collections.Counter(
                             k for r in rows for k in r["changed_fields"]).most_common())},
        "a04_mapping": {"total": len(mapping),
                        "by_disposition": dict(collections.Counter(r["disposition"] for r in mapping)),
                        "changed_field_counts": dict(collections.Counter(
                            k for r in mapping for k in r["changed_fields"]).most_common()),
                        "every_a04_row_mapped_once": (sorted(str(r["episode_id"]) for r in a4_rows)
                                                      == sorted(r["a04_episode_id"] for r in mapping))},
        "comparison_rule": {"version_only_assignment_keys_not_compared": sorted(VERSION_ONLY_ASSIGNMENT_KEYS),
                            "parser_version": "expected to change; recorded, not compared"},
        "uncertainty_classes": dict(collections.Counter(c for e in episodes for c in e["uncertainty_classes"])),
        "date_basis": dict(collections.Counter(str(e.get("date_basis")) for e in episodes)),
        "accounting": a4b.accounting(predecessor_rows, rows, episodes),
        "a3_screens": a4b.screen_accounting(rows, episodes, manager),
        "a4_screens": {k: {kk: vv for kk, vv in v.items() if kk != "rows"} for k, v in screens.items()},
        "a4_raw_census_reconciliation": a4b.census_reconciliation(census, episodes),
        "a4_raw_census_uncovered_by_cause": a4_census_uncovered(census, episodes),
        "not_produced_by_cause": {
            "predecessor": dict(collections.Counter(r["reason"].split(":", 1)[0] for r in rows
                                                    if r["disposition"] == cs.NOT_PRODUCED)),
            "a04": dict(collections.Counter(r["reason"].split(":", 1)[0] for r in mapping
                                            if r["disposition"] == cs.NOT_PRODUCED))},
        "template_census_reconciliation": template_census_reconciliation(template_census, episodes),
        "unit_changes": {k: v for k, v in units.items() if k != "rows"},
        "staff_descendants": {k: v for k, v in descendants.items() if k != "rows"},
        "not_claimed": ("Wikimedia revisions are secondary retrospective evidence. No episode is PIT admitted or "
                        "official; an unresolved role, date template or uncertain year is retained as stated, not "
                        "interpreted; no play-calling authority is inferred from any title. The successor is not "
                        "activated and not accepted; the predecessor, the Attempt 4 successor and their defaults "
                        "are unchanged; the delivered staff rows are recorded as affected descendants, not rebuilt."),
    }
    name = "CAREER_A05_SUCCESSOR_REBUILD" if compare_to else "CAREER_A05_SUCCESSOR_BUILD"
    with (out / f"{name}_ROWS.json.gz").open("xb") as raw, \
            gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
        handle.write(json.dumps({"screen_rows": {k: v["rows"] for k, v in screens.items()},
                                 "unit_change_rows": units["rows"], "staff_descendant_rows": descendants["rows"]},
                                default=str, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    summary["files"]["detail_rows"] = {"path": str(out / f"{name}_ROWS.json.gz"),
                                       "sha256": cs.sha256_file(out / f"{name}_ROWS.json.gz")}
    with (out / f"{name}.json").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(summary, indent=2, default=str, ensure_ascii=False) + "\n")
    return summary


def deliver(out: Path, summary: dict[str, Any], pointer: Path) -> None:
    """Record the delivered successor: file and digests, and the committed subject that built it."""

    import subprocess  # noqa: PLC0415

    def git(*args: str) -> str:
        return subprocess.run(["git", "--no-optional-locks", "-C", str(ROOT), *args], capture_output=True, text=True,
                              check=False).stdout.strip()

    if git("status", "--porcelain=v1", "-uall"):
        raise SystemExit("the successor is delivered only from a clean, committed subject")
    successor = Path(summary["successor"]["path"])
    record = {
        "label": f"Cycle #{CYCLE_NUMBER} — Attempt #{ATTEMPT_NUMBER} — IN_PROGRESS_LOCAL_WORK_REMAINS "
                 "(delivered explicit career successor)",
        "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
        "successor_file": str(successor), "successor_sha256": cs.sha256_file(successor),
        "successor_version": cs.A05_SUCCESSOR_VERSION, "format_version": cs.A05_FORMAT_VERSION,
        "predecessor_database": str(PREDECESSOR_DB), "predecessor_database_sha256": PREDECESSOR_SHA256,
        "a04_successor": str(A4_SUCCESSOR), "a04_successor_sha256": A4_SUCCESSOR_SHA256,
        "build_summary": str(out / "CAREER_A05_SUCCESSOR_BUILD.json"),
        "build_summary_sha256": cs.sha256_file(out / "CAREER_A05_SUCCESSOR_BUILD.json"),
        "files": summary["files"],
        "built_from": {"head": git("rev-parse", "HEAD"), "tree": git("rev-parse", "HEAD^{tree}"), "clean": True},
        "default_activation": cs.NOT_ACTIVATED, "acceptance_state": cs.NOT_ACCEPTED,
        "selection": "bas-staff-query --career-successor <successor_file> --career-successor-sha256 <successor_sha256>",
    }
    pointer.parent.mkdir(parents=True, exist_ok=True)
    with pointer.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, indent=2, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--census", type=Path, required=True, help="The Attempt 4 raw census (CAREER_RAW_CENSUS.json).")
    parser.add_argument("--template-census", type=Path, required=True,
                        help="The Attempt 5 template census (CAREER_TEMPLATE_CENSUS.json).")
    parser.add_argument("--compare-to", type=Path, help="Rebuild in memory and compare with this delivered file.")
    parser.add_argument("--pointer", type=Path, help="Deliver: write this new pointer file (clean, committed subject).")
    args = parser.parse_args(argv)
    if args.pointer is not None and (args.compare_to or args.pointer.exists()):
        raise SystemExit("a pointer is written once, for a delivered build only")
    args.out.mkdir(parents=True, exist_ok=False)
    summary = build(args.out, census=args.census, template_census=args.template_census, compare_to=args.compare_to)
    if args.pointer is not None:
        deliver(args.out, summary, args.pointer)
    print(json.dumps({"episodes": summary["successor"]["episodes"],
                      "dispositions": summary["dispositions"]["by_disposition"],
                      "a04_mapping": summary["a04_mapping"]["by_disposition"],
                      "predecessor_unchanged": summary["predecessor"]["unchanged"],
                      "a04_unchanged": summary["a04_successor"]["unchanged"],
                      "successor_sha256": summary["successor"]["sha256"],
                      "rebuild_comparison": summary["rebuild_comparison"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

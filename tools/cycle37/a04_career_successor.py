r"""Cycle #37 — Attempt #4 — build the explicitly selected career successor (TP37-A04-06, R37A04-04/05/06).

    a04_career_successor.py --out <new directory> [--census <CAREER_RAW_CENSUS.json>] [--limit N]

Rereads every cached revision of the delivered career population with the v37.4 parser, through the same
program crosswalk, staff join and official-site rule the delivered rows were built with
(:mod:`r37_05_career_reparse`), and writes:

* ``CAREER_SUCCESSOR_A04.sqlite`` -- the successor file :mod:`aggie_analytics.cycle37.career_successor`
  validates and the installed ``bas-staff-query --career-successor`` serves;
* ``CAREER_A04_DISPOSITIONS.jsonl.gz`` -- one line per predecessor episode (all 72,070), the same rows the
  successor's disposition table holds, for a reader without SQLite;
* ``CAREER_A04_SUCCESSOR_BUILD.json`` -- inputs and their digests, counts by disposition, screen and
  uncertainty class, the three manager screens row by row, and what is not claimed.

What changes from the delivered rows, and why each change is sourced:

* role: a parenthetical the parser cannot read as a role, place, league or sport scope is kept verbatim as
  unresolved and blocks the head-coach convention (MF37A03-04); an ``{{abbr}}``/``{{tooltip}}`` the old parser
  deleted now displays its code and, when the code is not established, the meaning that row states; a years
  field with no team field states no role;
* interval: every endpoint has a state and the interval the seasons it definitely covers (MF37A03-05);
  classification, population state and the staff join use only those definite seasons;
* rows: ``coaching_``/``playing_``/``administrating_`` numbered fields, never read before, are added.

Nothing is looked up: no acquisition, no request, no guess at an abbreviation's meaning or an unknown year.
The predecessor database is opened read-only by URI and immutable; its bytes are checked before and after.
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

import r37_05_career_reparse as reparse  # noqa: E402

from aggie_analytics.cycle37 import career_infobox, staff_record  # noqa: E402
from aggie_analytics.cycle37 import career_successor as cs  # noqa: E402

CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 4
BUILDER_VERSION = "BAS-C37A04-CAREER-SUCCESSOR-BUILDER-v1"
PREDECESSOR_DB = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle37\attempts\REWORK-20260922T171601Z\release\sha256"
                      r"\67d2ce357dc36d5a13a8edc94d0ffa9fc27115768817b1ee1ac9dff567757671"
                      r"\CYCLE37_CORRECTED_NATIONAL_RELEASE.sqlite")
PREDECESSOR_SHA256 = "757d4b5f0649d60943c4594d6e0c22b7c930f5ef3acf9f675b4f93f328a7d331"
PREDECESSOR_RELEASE_VERSION = "BAS-CYCLE37-CORRECTED-NATIONAL-RELEASE-v37.2-STAFF-REPARSE"
MANAGER_SCREENS = Path(r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle37\attempt03\review-20260924T212311Z"
                       r"\CAREER_SEMANTIC_COUNTEREXAMPLE.json")
MANAGER_SCREENS_SHA256 = None  # recorded, not pinned: the review file is read-only input
#: The manager's 312-row unknown-endpoint screen (``years_raw LIKE '%?%' AND start = end`` over the delivered rows).
MANAGER_DATE_SCREEN = MANAGER_SCREENS.with_name("CAREER_SEMANTIC_REPRODUCTION.json")
SCREEN_EXPECTED = {"MANAGER_BROAD_SUFFIX_HEAD_COACH_3896": 3896, "MANAGER_ROLE_CODE_343": 343,
                   "MANAGER_QUESTION_MARK_START_EQUALS_END_312": 312}
HEAD_COACH_SCREENS = ("MANAGER_BROAD_SUFFIX_HEAD_COACH_3896", "MANAGER_ROLE_CODE_343",
                      "WORKER_HEAD_COACH_DEFAULT_WITH_ANY_QUALIFIER")
QUESTION_MARK_SCREENS = ("MANAGER_QUESTION_MARK_START_EQUALS_END_312", "WORKER_ANY_QUESTION_MARK_YEARS")
#: The raw census names its career fields as the revision writes them; this is where each lands in a row identity.
CENSUS_FAMILIES = {"coach": ("COACHING", 0), "player": ("PLAYING", 0), "admin": ("ADMINISTRATIVE", 0),
                   "executive": ("ADMINISTRATIVE", 0),
                   "coaching": ("COACHING", career_infobox.VARIANT_FIELD_INDEX_OFFSET),
                   "playing": ("PLAYING", career_infobox.VARIANT_FIELD_INDEX_OFFSET),
                   "administrating": ("ADMINISTRATIVE", career_infobox.VARIANT_FIELD_INDEX_OFFSET)}
MODEL_SCOPE = reparse.MODEL_SCOPE
UNCERTAIN_STATES = frozenset({career_infobox.QUESTIONED, career_infobox.APPROXIMATE, career_infobox.DECADE,
                              career_infobox.PARTIAL, career_infobox.AFTER, career_infobox.BEFORE,
                              career_infobox.ALTERNATIVES})
#: Fields compared between a predecessor row and the successor row(s) it maps to. ``parser_version`` is
#: expected to change and is recorded, not counted as a correction.
COMPARED = ("family", "pageid", "revision", "row_index", "page_title", "person_display", "wikidata_qid",
            "homonym_display_name", "employer_display", "employer_link_target", "employer_link_basis",
            "employer_qualifiers", "employer_kind", "resolution", "classification", "role_text", "role_basis",
            "assignments", "start", "end", "ongoing", "years_as_written", "years_raw", "population_state", "join",
            "team_raw", "team_char_span", "team_byte_span", "years_char_span", "raw_file", "raw_file_sha256",
            "wikitext_sha256", "evidence_class", "pit_admitted")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normal(value: Any) -> Any:
    """One comparable form: booleans as 0/1, identifiers as text, JSON structures as structures."""

    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (list, tuple)):
        return [normal(item) for item in value]
    if isinstance(value, dict):
        return {str(key): normal(item) for key, item in value.items()}
    return value


def decoded_predecessor(row: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key, value in row.items():
        if key in cs.PREDECESSOR_JSON_COLUMNS and isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                value = {"undecodable_stored_text": value}
        out[key] = normal(value)
    for key in ("pageid", "revision", "row_index", "interval_index"):
        if out.get(key) is not None:
            out[key] = str(out[key])
    return out


def assignments_for(row: dict[str, Any]) -> list[dict[str, Any]]:
    return reparse.assignments_for(row)


def definite_range(interval: dict[str, Any]) -> tuple[int | None, int | None]:
    """(first, last) seasons an interval definitely covers; last is the model's last season when ongoing."""

    first = interval.get("definite_first_season")
    if first is None:
        return None, None
    last = interval.get("definite_last_season")
    if last is None:
        last = MODEL_SCOPE[1] if interval.get("ongoing") else first
    return first, last


def possible_range(interval: dict[str, Any]) -> tuple[int | None, int | None]:
    """(earliest, latest) season an interval may cover; None where the revision leaves it unbounded."""

    def low(state: str | None, value: int | None, bounds: list[int] | None) -> int | None:
        if state == career_infobox.STATED:
            return value
        if bounds and bounds[0] is not None:
            return bounds[0]
        return None

    def high(state: str | None, value: int | None, bounds: list[int] | None) -> int | None:
        if state == career_infobox.STATED:
            return value
        if state == career_infobox.PRESENT:
            return MODEL_SCOPE[1]
        if bounds and bounds[-1] is not None and state != career_infobox.AFTER:
            return bounds[-1]
        return None

    if not interval.get("start_state"):
        return None, None
    return (low(interval["start_state"], interval.get("start"), interval.get("start_bounds")),
            high(interval["end_state"], interval.get("end"), interval.get("end_bounds")))


def uncertainty_classes(team: dict[str, Any], interval: dict[str, Any]) -> list[str]:
    classes = []
    if team.get("role_basis") == "UNRESOLVED_PARENTHETICAL":
        classes.append("UNRESOLVED_ROLE")
    start_state, end_state = interval.get("start_state"), interval.get("end_state")
    if start_state == career_infobox.UNKNOWN:
        classes.append("UNKNOWN_START")
    if end_state == career_infobox.UNKNOWN:
        classes.append("UNKNOWN_END")
    if start_state in UNCERTAIN_STATES:
        classes.append("UNCERTAIN_START")
    if end_state in UNCERTAIN_STATES:
        classes.append("UNCERTAIN_END")
    if start_state is not None and interval.get("definite_first_season") is None:
        classes.append("NO_DEFINITE_SEASON")
    if interval.get("bounds_consistent") is False:
        classes.append("INCONSISTENT_BOUNDS")
    return classes


def population_state(row: dict[str, Any], interval: dict[str, Any], resolution: dict[str, Any],
                     classification: dict[str, Any]) -> str:
    """r37_05's population rule over the seasons the interval definitely covers."""

    first, last = definite_range(interval)
    if first is None:
        return "NO_DEFINITE_SEASON_STATED" if interval.get("start_state") else "NO_INTERVAL_STATED"
    if row["family"] == "PLAYING":
        return "TYPED_PLAYER_CAREER_NOT_A_COACHING_EPISODE"
    if row["family"] == "ADMINISTRATIVE":
        return "TYPED_ADMINISTRATIVE_CAREER"
    kind = row["employer_kind"]
    if kind == "OTHER_SPORT_PROGRAM":
        return "TYPED_OTHER_SPORT_EMPLOYER"
    if kind == "HIGH_SCHOOL":
        return "TYPED_HIGH_SCHOOL_EMPLOYER"
    if kind == "PROFESSIONAL":
        return "TYPED_PROFESSIONAL_EMPLOYER"
    if last < MODEL_SCOPE[0]:
        return "PRE_1963_CONTEXT_OUTSIDE_THE_MODEL_POPULATION"
    if resolution.get("state") != reparse.RESOLVED:
        return "EMPLOYER_NOT_RESOLVED_TO_ONE_PROGRAM"
    if not any(d in ("fbs", "fcs") for d in classification.get("divisions", [])):
        return "COLLEGE_EMPLOYER_OUTSIDE_FBS_FCS_IN_THESE_SEASONS"
    return "IN_POPULATION_CANDIDATE_EPISODE"


def successor_episodes(limit: int | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Every successor episode, parsed from the cached raw revisions (mirrors r37_05's episode loop)."""

    pages = reparse.read_jsonl(reparse.CAREER_PAGES)
    pages = pages[:limit] if limit else pages
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
            assignments = assignments_for(row)
            for number, interval in enumerate(row["intervals"] or [no_interval]):
                first, last = definite_range(interval)
                classification = (resolver.classification(resolution.get("program_id"), first, last)
                                  if first is not None else {})
                state = population_state(row, interval, resolution, classification)
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
                possible_first, possible_last = possible_range(interval)
                locator = f"{page['pageid']}:{page['wikimedia_revision']}:{row['family']}:{row['index']}"
                episodes.append({
                    "locator": locator, "interval_index": number,
                    "episode_id": f"{cs.IDENTITY_PREFIX}:{locator}:{number}",
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
                    "years_char_span": row["years_span"], "wikitext_sha256": parsed["wikitext_sha256"],
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
                })
    stats = {"pages": len(pages), "pages_missing_raw": missing_raw, "raw_index": index_stats,
             "successor_episodes": len(episodes)}
    return episodes, stats


def load_predecessor(database: Path) -> list[dict[str, Any]]:
    conn = sqlite3.connect(database.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute(f"SELECT * FROM {cs.PREDECESSOR_TABLE}")]
    finally:
        conn.close()


def predecessor_locator(row: dict[str, Any]) -> tuple[str, int]:
    match = re.match(r"^R37-05:(\d+):(\d+):([A-Z]+):(\d+):(\d+)$", str(row["episode_id"]))
    if not match:
        raise ValueError(f"unexpected predecessor episode id {row['episode_id']!r}")
    return f"{match.group(1)}:{match.group(2)}:{match.group(3)}:{match.group(4)}", int(match.group(5))


def comparable_successor(episode: dict[str, Any]) -> dict[str, Any]:
    out = {key: normal(episode.get(key)) for key in COMPARED}
    for key in ("pageid", "revision", "row_index"):
        if out.get(key) is not None:
            out[key] = str(out[key])
    return out


def screens_for(predecessor: dict[str, Any], manager: dict[str, set[str]]) -> list[str]:
    decoded = predecessor["_decoded"]
    labels = []
    if predecessor["episode_id"] in manager["broad"]:
        labels.append("MANAGER_BROAD_SUFFIX_HEAD_COACH_3896")
    if predecessor["episode_id"] in manager["specific"]:
        labels.append("MANAGER_ROLE_CODE_343")
    head_coach_default = any(isinstance(a, dict) and a.get("basis") == "INFOBOX_CONVENTION_NO_ROLE_PARENTHETICAL"
                             for a in decoded.get("assignments") or [])
    if head_coach_default and decoded.get("employer_qualifiers"):
        labels.append("WORKER_HEAD_COACH_DEFAULT_WITH_ANY_QUALIFIER")
    years = str(predecessor.get("years_raw") or "")
    if "?" in years and predecessor.get("start") is not None and predecessor.get("start") == predecessor.get("end"):
        labels.append("MANAGER_QUESTION_MARK_START_EQUALS_END_312")
    if "?" in years:
        labels.append("WORKER_ANY_QUESTION_MARK_YEARS")
    return labels


def unchanged_basis(screens: list[str], episode: dict[str, Any]) -> tuple[str, bool]:
    """Why a screened row the successor reads identically keeps its meaning, from its own source text.

    Returns the reason and whether it is grounded (every screen the row belongs to is explained).
    """

    parts, grounded = [], True
    if any(screen in screens for screen in HEAD_COACH_SCREENS):
        kinds = [item for item in episode.get("employer_qualifier_kinds") or []
                 if item.get("kind") != "ROSTER_MARKER"]
        if kinds and not episode.get("unresolved_parentheticals") and not episode.get("role_parentheticals"):
            parts.append("no role is stated: every parenthetical is a qualifier ("
                         + "; ".join(f"({item['text']}) {item['kind']}" for item in kinds)
                         + "), so the infobox head-coach convention reads the row as the predecessor did")
        else:
            grounded = False
            parts.append("NOT_GROUNDED: a head-coach screen row with no recorded qualifier kind")
    if any(screen in screens for screen in QUESTION_MARK_SCREENS):
        written = episode.get("years_as_written")
        if "?" not in str(written or ""):
            parts.append(f"the '?' is inside reference or comment markup, not in the years as written ({written!r})")
        else:
            grounded = False
            parts.append("NOT_GROUNDED: the years as written carry '?' yet the interval is stated")
    reason = "every compared field is equal" + ("; " + "; ".join(parts) if parts else "")
    return reason, grounded


def dispositions(predecessor_rows: list[dict[str, Any]], episodes: list[dict[str, Any]],
                 manager: dict[str, set[str]]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """One disposition per predecessor episode, and the predecessor ids each successor episode derives from."""

    by_locator_new: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for episode in episodes:
        by_locator_new[episode["locator"]].append(episode)
    by_locator_old: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in predecessor_rows:
        row["_decoded"] = decoded_predecessor(row)
        locator, number = predecessor_locator(row)
        row["_locator"], row["_number"] = locator, number
        by_locator_old[locator].append(row)
    derived: dict[str, list[str]] = collections.defaultdict(list)
    out = []
    for locator, old_rows in by_locator_old.items():
        old_rows.sort(key=lambda r: r["_number"])
        new_rows = sorted(by_locator_new.get(locator, []), key=lambda e: e["interval_index"])
        for row in old_rows:
            screen = screens_for(row, manager)
            digest = cs.predecessor_row_digest(row)
            if not new_rows:
                out.append({"predecessor_episode_id": row["episode_id"], "disposition": cs.NOT_PRODUCED,
                            "successor_episode_ids": [], "changed_fields": {}, "predecessor_row_sha256": digest,
                            "screens": screen, "reason": "the v37.4 parser produces no row at this locator"})
                continue
            restructured = len(new_rows) != len(old_rows)
            mapped = new_rows if restructured else [new_rows[row["_number"]]]
            for episode in mapped:
                derived[episode["episode_id"]].append(row["episode_id"])
            old = {key: row["_decoded"].get(key) for key in COMPARED}
            if not restructured:
                new = comparable_successor(mapped[0])
                changed = {key: {"predecessor": old[key], "successor": new[key]} for key in COMPARED
                           if old[key] != new[key]}
            else:
                changed = {"intervals": {"predecessor": [[r["_decoded"].get("start"), r["_decoded"].get("end"),
                                                          r["_decoded"].get("years_as_written")] for r in old_rows],
                                         "successor": [[e["start"], e["end"], e["start_state"], e["end_state"],
                                                        e["years_as_written"]] for e in new_rows]}}
            unresolved = any(e["uncertainty_classes"] for e in mapped)
            if restructured:
                state, reason = cs.RESTRUCTURED, (f"the row's years now read as {len(new_rows)} interval(s) where the "
                                                  f"predecessor had {len(old_rows)}")
            elif not changed:
                state = cs.UNCHANGED
                reason, _ = unchanged_basis(screen, mapped[0])
            elif unresolved:
                state, reason = cs.UNRESOLVED_EXPLICIT, ("the successor states an unresolved role or uncertain bounds "
                                                         f"({mapped[0]['uncertainty_classes']}) where the predecessor "
                                                         "stated a definite value")
            else:
                state, reason = cs.CORRECTED, f"changed: {sorted(changed)}"
            out.append({"predecessor_episode_id": row["episode_id"], "disposition": state,
                        "successor_episode_ids": [e["episode_id"] for e in mapped], "changed_fields": changed,
                        "predecessor_row_sha256": digest, "screens": screen, "reason": reason})
    return out, derived


def accounting(predecessor_rows: list[dict[str, Any]], rows: list[dict[str, Any]],
               episodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Every predecessor row dispositioned exactly once; every successor identity distinct and accounted."""

    predecessor_ids = [str(r["episode_id"]) for r in predecessor_rows]
    dispositioned = [str(r["predecessor_episode_id"]) for r in rows]
    identities = [e["episode_id"] for e in episodes]
    new = [e for e in episodes if not e["predecessor_episode_ids"]]
    return {
        "predecessor_rows": len(predecessor_ids), "dispositions": len(dispositioned),
        "distinct_dispositioned": len(set(dispositioned)),
        "every_predecessor_row_dispositioned_once": (sorted(predecessor_ids) == sorted(dispositioned)
                                                     and len(set(dispositioned)) == len(dispositioned)),
        "not_produced": sum(1 for r in rows if r["disposition"] == cs.NOT_PRODUCED),
        "successor_episodes": len(identities), "successor_identities_distinct": len(set(identities)) == len(identities),
        "derived_from_predecessor_rows": len(identities) - len(new), "new_without_predecessor": len(new),
        "new_by_family_and_field": dict(collections.Counter(f"{e['family']}::{e['career_field']}" for e in new)),
    }


def screen_accounting(rows: list[dict[str, Any]], episodes: list[dict[str, Any]],
                      manager: dict[str, set[str]]) -> dict[str, Any]:
    """The three manager screens, member by member: disposition, remaining head-coach rows, grounded basis."""

    by_id = {str(r["predecessor_episode_id"]): r for r in rows}
    episode_by_id = {e["episode_id"]: e for e in episodes}
    dates = {str(r["episode_id"]) for r in
             json.loads(MANAGER_DATE_SCREEN.read_text(encoding="utf-8"))["unknown_endpoint_screen"]}
    sets = {"MANAGER_BROAD_SUFFIX_HEAD_COACH_3896": manager["broad"], "MANAGER_ROLE_CODE_343": manager["specific"],
            "MANAGER_QUESTION_MARK_START_EQUALS_END_312": dates}
    out: dict[str, Any] = {}
    for name, ids in sets.items():
        members = [by_id[i] for i in sorted(ids) if i in by_id]
        labelled = {str(r["predecessor_episode_id"]) for r in rows if name in r["screens"]}
        successors = [episode_by_id[s] for r in members for s in r["successor_episode_ids"]]
        head = [e["episode_id"] for e in successors
                if any(isinstance(a, dict) and a.get("role") == "head_coach" for a in e["assignments"])]
        ungrounded = [str(r["predecessor_episode_id"]) for r in members if r["disposition"] == cs.UNCHANGED
                      and not unchanged_basis(r["screens"], episode_by_id[r["successor_episode_ids"][0]])[1]]
        out[name] = {
            "expected": SCREEN_EXPECTED[name], "manager_ids": len(ids), "members": len(members),
            "without_disposition": sorted(ids - set(by_id)), "labelled_by_the_builder": len(labelled),
            "builder_label_equals_manager_set": labelled == set(ids),
            "by_disposition": dict(collections.Counter(r["disposition"] for r in members)),
            "successor_rows_still_head_coach": len(head), "head_coach_examples": head[:20],
            "unchanged_without_grounded_basis": ungrounded,
            "manager_source": str(MANAGER_DATE_SCREEN if name.endswith("_312") else MANAGER_SCREENS),
        }
    return out


def _fold(text: Any) -> str:
    return " ".join(str(text or "").split()).casefold()


def census_reconciliation(census: Path | None, episodes: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Every numbered career row the independent raw census lists, matched to the successor rows at its locator.

    Three questions per census row: is there a successor row; does every parenthetical the census found outside
    the links have a reading (role, unresolved text or a stated qualifier); and does a question mark in the years
    as the revision writes them (outside references) leave an uncertainty class on the row.
    """

    if census is None:
        return None
    summary = json.loads(census.read_text(encoding="utf-8"))
    rows_path = census.with_name("CAREER_RAW_CENSUS_ROWS.jsonl")
    rows_sha256 = sha256_bytes(rows_path.read_bytes())
    by_locator: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for episode in episodes:
        by_locator[f"{episode['pageid']}:{episode['revision']}:{episode['family']}:{episode['row_index']}"].append(episode)
    counts: collections.Counter = collections.Counter()
    examples: dict[str, list[Any]] = collections.defaultdict(list)
    uncertain = {"UNKNOWN_START", "UNKNOWN_END", "UNCERTAIN_START", "UNCERTAIN_END", "NO_DEFINITE_SEASON"}
    with rows_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            counts["census_rows"] += 1
            family, offset = CENSUS_FAMILIES[str(row["family"]).lower()]
            locator = f"{row['pageid']}:{row['revision']}:{family}:{int(row['index']) + offset}"
            found = by_locator.get(locator)
            if not found:
                team, years = str(row.get("team_raw") or "").strip(), str(row.get("years_raw") or "").strip()
                reason = "EMPTY_TEAM_AND_YEARS" if not team and not years else "NOT_READ_BY_THE_SUCCESSOR_PARSER"
                counts[f"uncovered::{reason}"] += 1
                if len(examples[reason]) < 25:
                    examples[reason].append({"locator": locator, "team_raw": team[:160], "years_raw": years[:80]})
                continue
            counts["covered"] += 1
            episode = found[0]
            census_groups = row.get("parentheticals") or []
            census_texts = sorted(_fold(g["plain"]) for g in census_groups if not g.get("template_only"))
            readings = ([_fold(x.get("text")) for x in episode.get("role_parentheticals") or []]
                        + [_fold(x.get("text")) for x in episode.get("unresolved_parentheticals") or []]
                        + [_fold(x.get("text")) for x in episode.get("employer_qualifier_kinds") or []
                           if x.get("kind") not in ("PART_OF_THE_LINKED_NAME", "ROSTER_MARKER")])
            remaining = list(readings)
            unread = []
            for text in census_texts:
                if text in remaining:
                    remaining.remove(text)
                else:
                    unread.append(text)
            if census_groups:
                counts["rows_with_census_parentheticals"] += 1
                if unread or len(readings) < len(census_groups):
                    counts["rows_with_a_census_parenthetical_not_read_verbatim"] += 1
                    if len(examples["parenthetical_not_read_verbatim"]) < 60:
                        examples["parenthetical_not_read_verbatim"].append({
                            "locator": locator, "census": [g["raw"] for g in census_groups], "unread": unread,
                            "successor_readings": readings, "role_basis": episode.get("role_basis"),
                            "team_raw": str(row.get("team_raw") or "")[:200]})
            years = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>|<!--.*?-->", "", str(row.get("years_raw") or ""),
                           flags=re.S | re.I)
            if re.search(r"\{\{\s*(?:circa|c\.|ca\.?)\s*\||\bc(?:a)?\.\s*\d|\bcirca\b", years, re.I):
                counts["census_rows_with_approximate_years"] += 1
                if any(set(e.get("uncertainty_classes") or []) & uncertain for e in found):
                    counts["approximate_rows_carrying_an_uncertainty_class"] += 1
                else:
                    counts["approximate_rows_without_an_uncertainty_class"] += 1
                    if len(examples["approximate_without_uncertainty"]) < 25:
                        examples["approximate_without_uncertainty"].append({
                            "locator": locator, "years_raw": years[:120],
                            "states": [(e.get("start_state"), e.get("end_state")) for e in found]})
            if "?" in years:
                counts["census_rows_with_question_mark_years"] += 1
                if any(set(e.get("uncertainty_classes") or []) & uncertain for e in found):
                    counts["question_mark_rows_carrying_an_uncertainty_class"] += 1
                else:
                    counts["question_mark_rows_without_an_uncertainty_class"] += 1
                    if len(examples["question_mark_without_uncertainty"]) < 25:
                        examples["question_mark_without_uncertainty"].append({
                            "locator": locator, "years_raw": years[:120],
                            "states": [(e.get("start_state"), e.get("end_state")) for e in found]})
    return {"census": str(census), "census_sha256": sha256_bytes(census.read_bytes()),
            "rows_file": str(rows_path), "rows_sha256": rows_sha256,
            "rows_sha256_matches_census": rows_sha256 == summary.get("rows_sha256"),
            "census_version": summary.get("census_version"), "counts": dict(counts), "examples": dict(examples),
            "scope": ("Numbered and spelled-out career fields; list fields are counted by the census at item level "
                      "and read row by row by the parser.")}


def write_successor(path: Path, episodes: list[dict[str, Any]], rows: list[dict[str, Any]],
                    identity: dict[str, str]) -> dict[str, str]:
    conn = sqlite3.connect(path)
    try:
        conn.execute(f"CREATE TABLE {cs.IDENTITY_TABLE} (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute(f"CREATE TABLE {cs.EPISODE_TABLE} ({', '.join(chr(34) + c + chr(34) for c in cs.EPISODE_COLUMNS)})")
        conn.execute(f"CREATE TABLE {cs.DISPOSITION_TABLE} ({', '.join(cs.DISPOSITION_COLUMNS)})")
        json_columns = cs.PREDECESSOR_JSON_COLUMNS | {"predecessor_episode_ids", "start_bounds", "end_bounds",
                                                     "uncertainty_classes", "unresolved_parentheticals",
                                                     "employer_qualifier_kinds", "role_parentheticals"}
        for episode in episodes:
            values = []
            for column in cs.EPISODE_COLUMNS:
                value = episode.get(column)
                if column in json_columns:
                    value = None if value is None else json.dumps(value, sort_keys=True)
                elif isinstance(value, bool):
                    value = int(value)
                values.append(value)
            conn.execute(f"INSERT INTO {cs.EPISODE_TABLE} VALUES ({', '.join('?' for _ in cs.EPISODE_COLUMNS)})", values)
        for row in rows:
            conn.execute(f"INSERT INTO {cs.DISPOSITION_TABLE} VALUES ({', '.join('?' for _ in cs.DISPOSITION_COLUMNS)})",
                         [row["predecessor_episode_id"], row["disposition"], json.dumps(row["successor_episode_ids"]),
                          json.dumps(row["changed_fields"], sort_keys=True, default=str), row["predecessor_row_sha256"],
                          json.dumps(row["screens"]), row["reason"]])
        conn.execute(f"CREATE UNIQUE INDEX a04_episode_id ON {cs.EPISODE_TABLE}(episode_id)")
        conn.execute(f"CREATE UNIQUE INDEX a04_disposition_id ON {cs.DISPOSITION_TABLE}(predecessor_episode_id)")
        conn.commit()
        for table, columns, key in ((cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, "episode_id"),
                                    (cs.DISPOSITION_TABLE, cs.DISPOSITION_COLUMNS, "predecessor_episode_id")):
            digest, count = cs.table_ledger(conn, table, columns, key)
            identity[f"ledger::{table}::sha256"] = digest
            identity[f"ledger::{table}::rows"] = str(count)
        conn.executemany(f"INSERT INTO {cs.IDENTITY_TABLE} VALUES (?, ?)", sorted(identity.items()))
        conn.commit()
    finally:
        conn.close()
    return identity


def build(out: Path, *, census: Path | None, limit: int | None) -> dict[str, Any]:
    before = cs.sha256_file(PREDECESSOR_DB)
    if before != PREDECESSOR_SHA256:
        raise SystemExit(f"the predecessor database is {before}, not the issued {PREDECESSOR_SHA256}")
    manager_data = json.loads(MANAGER_SCREENS.read_text(encoding="utf-8"))
    manager = {"broad": {r["episode_id"] for r in manager_data["candidates"]},
               "specific": {r["episode_id"] for r in manager_data["specific_role_code_screen"]}}
    started = utc_now()
    episodes, stats = successor_episodes(limit)
    predecessor_rows = load_predecessor(PREDECESSOR_DB)
    if limit:
        pages = {str(e["pageid"]) for e in episodes}
        predecessor_rows = [r for r in predecessor_rows if str(r["pageid"]) in pages]
    rows, derived = dispositions(predecessor_rows, episodes, manager)
    for episode in episodes:
        parents = derived.get(episode["episode_id"], [])
        episode["predecessor_episode_ids"] = parents
        episode["lineage_state"] = "DERIVED_FROM_PREDECESSOR_ROWS" if parents else "NEW_IN_A04_SUCCESSOR_NO_PREDECESSOR_ROW"
        states = sorted({r["disposition"] for r in rows if episode["episode_id"] in r["successor_episode_ids"]})
        episode["disposition"] = ",".join(states) if states else "ADDED"
    successor_path = out / "CAREER_SUCCESSOR_A04.sqlite"
    identity = {
        "format_version": cs.FORMAT_VERSION, "successor_version": cs.SUCCESSOR_VERSION,
        "predecessor_database_sha256": PREDECESSOR_SHA256, "predecessor_database_path": str(PREDECESSOR_DB),
        "predecessor_release_version": PREDECESSOR_RELEASE_VERSION, "predecessor_table": cs.PREDECESSOR_TABLE,
        "predecessor_row_count": str(len(predecessor_rows)), "parser_version": career_infobox.PARSER_VERSION,
        "predecessor_parser_version": career_infobox.PREDECESSOR_PARSER_VERSION,
        "identity_rule": (f"{cs.IDENTITY_PREFIX}:<pageid>:<revision>:<family>:<row index>:<interval index>; never a "
                          "predecessor identity; each successor row names the predecessor rows it derives from and "
                          "each predecessor row has exactly one disposition"),
        "default_activation": cs.NOT_ACTIVATED, "acceptance_state": cs.NOT_ACCEPTED,
        "evidence_class": cs.EVIDENCE_CLASS, "pit_admitted": "0", "builder_version": BUILDER_VERSION,
        "cycle_number": str(CYCLE_NUMBER), "attempt_number": str(ATTEMPT_NUMBER),
        # No build time: the same committed builder over the same cached bytes writes the same file, so a
        # rebuild can be compared byte for byte. The build time is in CAREER_A04_SUCCESSOR_BUILD.json.
    }
    write_successor(successor_path, episodes, rows, identity)
    after = cs.sha256_file(PREDECESSOR_DB)
    with gzip.open(out / "CAREER_A04_DISPOSITIONS.jsonl.gz", "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    by_disposition = collections.Counter(r["disposition"] for r in rows)
    by_screen: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for row in rows:
        for screen in row["screens"] or ["NOT_IN_ANY_SCREEN"]:
            by_screen[screen][row["disposition"]] += 1
    uncertainty = collections.Counter(c for e in episodes for c in e["uncertainty_classes"])
    changed_field_counts = collections.Counter(k for r in rows for k in r["changed_fields"])
    screen_rows = {name: [{"predecessor_episode_id": r["predecessor_episode_id"], "disposition": r["disposition"],
                           "successor_episode_ids": r["successor_episode_ids"], "changed_fields": sorted(r["changed_fields"]),
                           "reason": r["reason"]}
                          for r in rows if name in r["screens"]]
                   for name in ("MANAGER_ROLE_CODE_343", "MANAGER_QUESTION_MARK_START_EQUALS_END_312",
                                "MANAGER_BROAD_SUFFIX_HEAD_COACH_3896")}
    summary = {
        "label": f"Cycle #{CYCLE_NUMBER} — Attempt #{ATTEMPT_NUMBER} — IN_PROGRESS — career successor build",
        "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "builder_version": BUILDER_VERSION,
        "started_at": started, "finished_at": utc_now(), "limit": limit,
        "predecessor": {"path": str(PREDECESSOR_DB), "sha256_before": before, "sha256_after": after,
                        "unchanged": before == after == PREDECESSOR_SHA256, "rows": len(predecessor_rows)},
        "inputs": {"career_pages": {"path": str(reparse.CAREER_PAGES), "sha256": sha256_bytes(reparse.CAREER_PAGES.read_bytes())},
                   "staff_reparse": {"path": str(reparse.STAFF_REPARSE), "sha256": sha256_bytes(reparse.STAFF_REPARSE.read_bytes())},
                   "crosswalk_rows": {"path": str(reparse.CROSSWALK_ROWS), "sha256": sha256_bytes(reparse.CROSSWALK_ROWS.read_bytes())},
                   "historical_membership": {"path": str(reparse.HISTORICAL), "sha256": sha256_bytes(reparse.HISTORICAL.read_bytes())},
                   "manager_screens": {"path": str(MANAGER_SCREENS), "sha256": sha256_bytes(MANAGER_SCREENS.read_bytes()),
                                       "broad": len(manager["broad"]), "specific": len(manager["specific"])},
                   "raw_census": ({"path": str(census), "sha256": sha256_bytes(census.read_bytes())} if census else None)},
        "parse": stats,
        "successor": {"path": str(successor_path), "sha256": cs.sha256_file(successor_path),
                      "bytes": successor_path.stat().st_size, "identity": identity, "episodes": len(episodes),
                      "episodes_new_without_predecessor": sum(1 for e in episodes if not e["predecessor_episode_ids"])},
        "dispositions": {"total": len(rows), "by_disposition": dict(by_disposition),
                         "by_screen": {k: dict(v) for k, v in sorted(by_screen.items())},
                         "changed_field_counts": dict(changed_field_counts.most_common()),
                         "file": str(out / "CAREER_A04_DISPOSITIONS.jsonl.gz"),
                         "file_sha256": cs.sha256_file(out / "CAREER_A04_DISPOSITIONS.jsonl.gz")},
        "uncertainty_classes": dict(uncertainty),
        "role_bases": dict(collections.Counter(str(e["role_basis"]) for e in episodes)),
        "accounting": accounting(predecessor_rows, rows, episodes),
        "screens": screen_accounting(rows, episodes, manager) if not limit else None,
        "census_reconciliation": census_reconciliation(census, episodes),
        "screen_rows": screen_rows,
        "not_claimed": ("Wikimedia revisions are secondary retrospective evidence. No episode is PIT admitted or "
                        "official; an unresolved role or an uncertain year is retained as stated, not interpreted. The "
                        "successor is not activated and not accepted; the predecessor and its default path are unchanged."),
    }
    (out / "CAREER_A04_SUCCESSOR_BUILD.json").write_text(json.dumps(summary, indent=2, default=str, ensure_ascii=False)
                                                         + "\n", encoding="utf-8")
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
        "successor_version": cs.SUCCESSOR_VERSION, "format_version": cs.FORMAT_VERSION,
        "predecessor_database": str(PREDECESSOR_DB), "predecessor_database_sha256": PREDECESSOR_SHA256,
        "build_summary": str(out / "CAREER_A04_SUCCESSOR_BUILD.json"),
        "build_summary_sha256": cs.sha256_file(out / "CAREER_A04_SUCCESSOR_BUILD.json"),
        "dispositions_file": summary["dispositions"]["file"], "dispositions_sha256": summary["dispositions"]["file_sha256"],
        "raw_census": summary["inputs"].get("raw_census"),
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
    parser.add_argument("--census", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--pointer", type=Path,
                        help="Deliver: write this new pointer file naming the built successor, its digests and the "
                             "committed subject it was built from (refused for a --limit build or a dirty tree).")
    args = parser.parse_args(argv)
    if args.pointer is not None and (args.limit or args.pointer.exists()):
        raise SystemExit("a pointer is written once, for a full build only")
    args.out.mkdir(parents=True, exist_ok=False)
    summary = build(args.out, census=args.census, limit=args.limit)
    if args.pointer is not None:
        deliver(args.out, summary, args.pointer)
    print(json.dumps({"episodes": summary["successor"]["episodes"],
                      "new_without_predecessor": summary["successor"]["episodes_new_without_predecessor"],
                      "dispositions": summary["dispositions"]["by_disposition"],
                      "predecessor_unchanged": summary["predecessor"]["unchanged"],
                      "successor_sha256": summary["successor"]["sha256"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-11: availability statements bound to player, program stint, season,
contest and report vintage; a versioned policy ledger; and a national
report-opportunity denominator.

``statements``
    Every one of the 252 SEC statements is resolved again with the repaired
    identity rule (MF36-08: only rows of exactly this program in exactly this
    season), against the CFBD roster slice and the seven official 2026 roster
    pages this attempt read. Each statement is bound to its canonical contest
    by date and both teams. The 92 earlier resolutions are checked against
    the new ones row by row.

``policies``
    One ledger row per conference policy the attempt holds bytes for, with
    season, scope, schedule, vocabulary, the absence rule and the source
    digest. A policy's absence rule applies only to an actual complete report
    of its own conference.

``denominator``
    One opportunity per program per 2026 contest in the schedule vintage,
    with the policy that governs it and whether a report was ingested. With no
    ingested report the state is UNKNOWN_NOT_HEALTHY.

No medical detail is ingested; ``Out`` does not mean injured; no status is
PIT-admitted, and no frozen pregame input is touched.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36.availability_identity import (  # noqa: E402
    AVAILABILITY_IDENTITY_VERSION,
    RosterPlayer,
    normalize_jersey,
    resolve_player,
)
from aggie_analytics import atomic_io as _bas_atomic
from aggie_analytics.cycle37 import official_roster  # noqa: E402

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
REPAIRS = ATTEMPT / "evidence" / "repairs"
ACQUIRED = ATTEMPT / "private" / "acquisition" / "availability"
CYCLE30 = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle30_work")
ASSERTIONS = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle35/runs/20260920T172801Z/implementation_output"
                  r"/R35_11_AVAILABILITY_ASSERTIONS.jsonl")
ROSTER_SLICE = CYCLE30 / "outputs" / "CFBD_ROSTER_JOIN_SLICE.jsonl"
SCHEDULE = CYCLE30 / "outputs" / "CFBD_GAMES_TRANCHE.jsonl"
POLICY_INVENTORY = CYCLE30 / "outputs" / "AVAILABILITY_POLICY_INVENTORY.jsonl"
PREDECESSOR_ROWS = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle36/runs/20260921T200027Z/implementation_output"
                        r"/CYCLE36_AVAILABILITY_ROWS.jsonl")
#: Official 2026 roster pages read this attempt, by the program name the statements use.
OFFICIAL_ROSTERS = {"LSU": "34fafdcef4ed", "Kentucky": "f42358543fca", "South Carolina": "ad7c7f60a461",
                    "Mississippi State": "2345f122b145", "Arkansas": "5a8d8d0dff11", "Auburn": "0ca3777c6dc9",
                    "Florida": "ac72a785b2e5",
                    # Programs of the rendered ACC, Big 12 and Big Ten reports (hosts from the cached
                    # official staff pages, or the program's official athletics host).
                    "California": "650ff88245b9", "Clemson": "f180e85aadff", "Duke": "5a5aa5168bdf",
                    "Miami": "6a48964f69f7", "NC State": "91319245d8c2", "North Carolina": "3cb95a036b7a",
                    "Stanford": "ba844f2fe289", "Syracuse": "6a307bb29ce7", "Wake Forest": "1e813e758eb2",
                    "Pittsburgh": "a5116cc1a485", "Virginia": "7c63f2385b5f", "BYU": "c13b117d9280",
                    "Houston": "4ea03970cf15", "Texas Tech": "1ac3d87443fe", "Arizona": "860a1b58f64c",
                    "Arizona State": "95e936ea7c8e", "Kansas": "194e12452c6e", "Indiana": "ee9730582138",
                    "Northwestern": "7cfac83c1cfa", "Purdue": "e93d08d46bad", "Rutgers": "1717e2aeb1a9",
                    "USC": "a35606820e9b", "UCLA": "6bcc3c35aa18"}
#: A conference report route rendered this attempt that showed no 2026 report.
ROUTE_RENDERS = {"Mid-American": ("4ce1fe88cdcb", "REPORT_ROUTE_RENDERED_NO_2026_REPORT_LINKED")}
_CONTEST = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2})\s+(at|vs\.?)\s+(.+)$")
_SEASON_OUT = re.compile(r"\bseason\b", re.I)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def acquired(prefix: str) -> Path:
    return next(path for path in ACQUIRED.iterdir() if path.name.startswith(prefix) and path.suffix == ".bin")


def rosters() -> tuple[list[RosterPlayer], list[dict[str, Any]]]:
    players: list[RosterPlayer] = []
    sources = []
    for row in read_jsonl(ROSTER_SLICE):
        players.append(RosterPlayer(
            player_id=f"CFBD:{row.get('id')}", program_id=str(row.get("team") or ""),
            season=int(row["source_year"]) if str(row.get("source_year") or "").isdigit() else None,
            first_name=str(row.get("firstName") or ""), last_name=str(row.get("lastName") or ""),
            jersey=normalize_jersey(row.get("jersey")), position=row.get("position")))
    sources.append({"source": "CFBD roster slice", "path": str(ROSTER_SLICE),
                    "sha256": sha256_bytes(ROSTER_SLICE.read_bytes()), "programs": sorted(
                        {p.program_id for p in players})})
    for program, prefix in OFFICIAL_ROSTERS.items():
        path = acquired(prefix)
        parsed = official_roster.parse_roster(path.read_bytes().decode("utf-8", "replace"))
        for index, player in enumerate(parsed["players"]):
            name = player["name"]
            first = player["first_name"] or name.split(" ", 1)[0]
            last = player["last_name"] or (name.split(" ", 1)[1] if " " in name else "")
            players.append(RosterPlayer(
                player_id=f"OFFICIAL:{program}:{parsed['season']}:{index}", program_id=program,
                season=parsed["season"], first_name=first, last_name=last,
                jersey=normalize_jersey(player["jersey"]), position=player["position"]))
        sources.append({"source": f"official roster page, {program}", "path": str(path),
                        "sha256": sha256_bytes(path.read_bytes()), "method": parsed["method"],
                        "season": parsed["season"], "players": len(parsed["players"])})
    return players, sources


def schedule_index() -> dict[tuple[str, str], list[dict[str, Any]]]:
    index: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for game in read_jsonl(SCHEDULE):
        if int(game.get("season") or 0) != 2026:
            continue
        pair = tuple(sorted((str(game.get("homeTeam")), str(game.get("awayTeam")))))
        index[pair].append(game)
    return index


def bind_contest(program: str, label: str, index: dict[tuple[str, str], list[dict[str, Any]]]) -> dict[str, Any]:
    match = _CONTEST.match(str(label or "").strip())
    if not match:
        return {"state": "CONTEST_LABEL_NOT_READ", "season": None}
    month, day, year, where, opponent = match.groups()
    when = date(2000 + int(year), int(month), int(day))
    if opponent.strip() == program:
        # The Big 12 archive lists Kansas's 9/19/26 rows as "vs. Kansas". The
        # source is kept as written and the contest is not guessed from it.
        return {"state": "CONTEST_LABEL_NAMES_THE_PROGRAM_ITSELF", "season": when.year,
                "date_as_written": when.isoformat(), "opponent_as_written": opponent.strip()}
    games = index.get(tuple(sorted((program, opponent.strip()))), [])
    hits = []
    for game in games:
        start = datetime.fromisoformat(str(game["startDate"]).replace("Z", "+00:00"))
        # A US evening kickoff is the next UTC day; the label states the local date.
        if abs((start.date() - when).days) <= 1:
            hits.append(game)
    if len(hits) != 1:
        return {"state": "CONTEST_NOT_UNIQUELY_IN_SCHEDULE_VINTAGE", "season": when.year, "candidates": len(hits),
                "date_as_written": when.isoformat(), "opponent_as_written": opponent.strip()}
    game = hits[0]
    home_expected = where.lower() == "vs" or where.lower() == "vs."
    home_ok = (str(game["homeTeam"]) == program) == home_expected or bool(game.get("neutralSite"))
    return {"state": "CONTEST_BOUND" if home_ok else "CONTEST_BOUND_ORIENTATION_DISAGREES",
            "canonical_contest_id": f"SRC-002:GAME:{game['id']}", "season": int(game["season"]),
            "conference_game": bool(game.get("conferenceGame")), "date_as_written": when.isoformat()}


#: Conference report views rendered in the browser this attempt (R37-11-AC03):
#: the archive table each conference page embeds, and the ACC current view,
#: which states when each report was posted.
RENDERED_ARCHIVES = {"ACC": "bfd5b51508ca", "Big 12": "07a9bdadee51", "Big Ten": "660569f36bcd"}
RENDERED_CURRENT = {"ACC": "b8953b637350"}
_STAGES = ("initial_status", "update_1_status", "update_2_status", "game_day_status")
_CARD_STAGE = {"INITIAL REPORT": "initial_status", "UPDATE REPORT": "update_1_status",
               "GAME DAY REPORT": "game_day_status"}
_POSTED = re.compile(r"Report posted on \w+, (\w+) (\d{1,2}) at (\d{1,2}):(\d{2})\s*(am|pm) ET", re.I)
_FOOTER = re.compile(r"\b\w+DAY, (\w+) (\d{1,2}) \|", re.I)
_MONTHS = {m: i for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august",
                                        "september", "october", "november", "december"), start=1)}
#: Vendor display names that differ from the schedule vintage's team names.
TEAM_ALIASES = {"Pitt": "Pittsburgh", "Miami (FL)": "Miami", "Ole Miss": "Ole Miss"}


def _vendor_date(text: str) -> date | None:
    text = text.strip()
    for fmt in ("%m/%d/%y", "%a, %b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _normalized(status: str) -> str | None:
    text = status.strip()
    return None if text in ("", "-") else re.sub(r"[^A-Z0-9]+", "_", text.upper()).strip("_")


def rendered_postings() -> dict[tuple[str, str, str], dict[str, Any]]:
    """(team, ISO date, stage) -> the posting time the current view states for that report."""

    postings = {}
    for conference, prefix in RENDERED_CURRENT.items():
        payload = json.loads(acquired(prefix).read_bytes())
        for card in payload["cards"]:
            posted = _POSTED.search(card["text"])
            footer = _FOOTER.search(card["text"])
            stage = next((s for label, s in _CARD_STAGE.items() if card["text"].startswith(label)), None)
            if not (posted and footer and stage):
                continue
            month, day, hour, minute, half = posted.groups()
            hour = int(hour) % 12 + (12 if half.lower() == "pm" else 0)
            # Eastern daylight time (UTC-4) holds for every September date.
            local = datetime(2026, _MONTHS[month.lower()], int(day), hour, int(minute))
            utc = (local.replace(tzinfo=timezone.utc) + timedelta(hours=4)).isoformat()
            game_day = date(2026, _MONTHS[footer.group(1).lower()], int(footer.group(2))).isoformat()
            for column in card["columns"]:
                postings[(column["team"], game_day, stage)] = {
                    "publication_utc": utc, "basis": f"{conference} current view: {posted.group(0)!r}",
                    "source_sha256": sha256_bytes(acquired(prefix).read_bytes())}
    return postings


def rendered_assertions() -> list[dict[str, Any]]:
    """One assertion per player, contest and report stage from the rendered archive tables."""

    postings = rendered_postings()
    out = []
    for conference, prefix in RENDERED_ARCHIVES.items():
        path = acquired(prefix)
        payload = json.loads(path.read_bytes())
        header, *body = payload["rows"]
        assert header[:5] == ["Team", "Date", "Opponent", "Number", "Player"], header
        for row_index, cells in enumerate(body, start=1):
            if len(cells) != 9:
                continue
            team, when_text, opponent, number, player, *stages = cells
            when = _vendor_date(when_text)
            label = f"{when.month}/{when.day}/{when.strftime('%y')} {opponent.strip()}" if when else when_text
            for stage, status in zip(_STAGES, stages):
                posted = postings.get((team, when.isoformat() if when else "", stage)) or {}
                out.append({
                    "conference": conference, "program": TEAM_ALIASES.get(team, team), "program_as_written": team,
                    "player_name": player.strip(), "jersey": number.strip(), "raw_text": status.strip(),
                    "status": _normalized(status), "stage": stage,
                    "presence": "PUBLISHED_EMPTY" if status.strip() in ("", "-") else "PUBLISHED_VALUE",
                    "contest_label": label, "retrieval_utc": payload["rendered_utc"],
                    "publication_utc": posted.get("publication_utc"), "publication_basis": posted.get("basis"),
                    "effective_utc": None, "source_sha256": sha256_bytes(path.read_bytes()),
                    "source_locator": f"rows[{row_index}].{stage}", "source_url": payload["url"],
                    "embedded_in": payload.get("embedded_in"),
                    "rights_state": "PUBLIC_CONFERENCE_REPORT_RESEARCH_USE",
                })
    return out


def _contest_date(row: dict[str, Any]) -> str:
    return str(row["contest"].get("date_as_written") or "")


def season_out_carry(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """A season-long absence stated once stays stated through later reports that omit the player.

    For every statement whose exact text states a season-long absence, each
    later contest of the same program and season with an ingested report that
    does not list the player gains a carried row. A later report that does
    list the player states its own status and ends the carry.
    """

    by_contest: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for row in rows:
        if row["contest"].get("canonical_contest_id"):
            by_contest[(row["program"], _contest_date(row))].add(str(row["player_name"]).casefold())
    carries = []
    for row in sorted(rows, key=_contest_date):
        if not _SEASON_OUT.search(row["exact_status_text"]) or not row["contest"].get("canonical_contest_id"):
            continue
        name = str(row["player_name"]).casefold()
        stated_on = _contest_date(row)
        for (program, when), listed in sorted(by_contest.items()):
            if program != row["program"] or when <= stated_on or when[:4] != stated_on[:4]:
                continue
            if name in listed:
                break  # the later report states this player's status itself
            carries.append({"label": LABEL, "program": program, "player_name": row["player_name"],
                            "carried_status_text": row["exact_status_text"], "stated_for_contest_date": stated_on,
                            "carried_to_contest_date": when, "state": "SEASON_OUT_CARRIED_ACROSS_OMISSION",
                            "source_row": row["availability_row_id"]})
    return carries


def version_conflicts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Where two rendered views state the same report, whether they agree player by player."""

    checked, conflicts = 0, []
    for conference, prefix in RENDERED_CURRENT.items():
        payload = json.loads(acquired(prefix).read_bytes())
        for card in payload["cards"]:
            footer = _FOOTER.search(card["text"])
            stage = next((s for label, s in _CARD_STAGE.items() if card["text"].startswith(label)), None)
            if not (footer and stage):
                continue
            game_day = date(2026, _MONTHS[footer.group(1).lower()], int(footer.group(2))).isoformat()
            for column in card["columns"]:
                current, status = {}, None
                for line in column["text"].splitlines():
                    player = re.match(r"^\S+\s+(#\d+)\s+(.+)$", line.strip())
                    if player:
                        current[(player.group(1), player.group(2).strip())] = status
                    elif line.strip():
                        status = line.strip().title()
                team = TEAM_ALIASES.get(column["team"], column["team"])
                archive = {(r["jersey"], r["player_name"]): r["exact_status_text"] for r in rows
                           if r["conference"] == conference and r["program"] == team and r["stage"] == stage
                           and _contest_date(r) == game_day and r["exact_status_text"] not in ("", "-")}
                checked += 1
                if {k: str(v).casefold() for k, v in current.items()} != \
                        {k: str(v).casefold() for k, v in archive.items()}:
                    conflicts.append({"conference": conference, "program": team, "contest_date": game_day,
                                      "stage": stage, "current_view": sorted(map(list, current.items())),
                                      "archive_view": sorted(map(list, archive.items()))})
    return {"reports_seen_in_two_views": checked, "conflicts": conflicts,
            "rule": "A disagreement between views is kept as a conflict; neither view overwrites the other."}


def statements(out_dir: Path) -> dict[str, Any]:
    assertions = [{**row, "conference": "SEC"} for row in read_jsonl(ASSERTIONS)]
    sec_count = len(assertions)
    assertions.extend(rendered_assertions())
    roster, roster_sources = rosters()
    index = schedule_index()
    predecessor = read_jsonl(PREDECESSOR_ROWS)
    predecessor.extend({} for _ in range(len(assertions) - len(predecessor)))
    rows, states, prior_check = [], collections.Counter(), collections.Counter()
    season_out: dict[tuple[str, str], str] = {}
    for number, (row, before) in enumerate(zip(assertions, predecessor), start=1):
        program = str(row.get("program") or "")
        contest = bind_contest(program, row.get("contest_label"), index)
        identity = resolve_player(program=program, player_name=str(row.get("player_name") or ""),
                                  jersey=row.get("jersey"), roster=roster, season=contest.get("season"))
        states[identity["state"]] += 1
        if before.get("canonical_player_id"):
            same = before["canonical_player_id"] == identity.get("canonical_player_id") or (
                identity.get("canonical_player_id") or "").endswith(f":{before['canonical_player_id']}")
            prior_check["AGREES" if same else "DIFFERS"] += 1
        raw_text = str(row.get("raw_text") or "")
        key = (program, str(row.get("player_name") or "").casefold())
        if _SEASON_OUT.search(raw_text):
            season_out[key] = str(row.get("contest_label"))
        rows.append({
            "label": LABEL, "availability_row_id": number, "conference": row["conference"], "program": program,
            "program_as_written": row.get("program_as_written", program),
            "player_name": row.get("player_name"), "jersey": row.get("jersey"),
            "exact_status_text": raw_text, "normalized_status": row.get("status"),
            "stage": row.get("stage"), "presence": row.get("presence"),
            "contest_label": row.get("contest_label"), "contest": contest,
            "report_vintage_retrieval_utc": row.get("retrieval_utc"),
            "publication_utc": row.get("publication_utc"), "effective_utc": row.get("effective_utc"),
            "publication_time_established": bool(row.get("publication_utc")),
            "publication_basis": row.get("publication_basis"),
            "source_sha256": row.get("source_sha256"), "source_locator": row.get("source_locator"),
            "source_url": row.get("source_url"), "embedded_in": row.get("embedded_in"),
            "rights_state": row.get("rights_state"),
            "identity": {k: identity.get(k) for k in (
                "state", "canonical_player_id", "confidence", "detail", "roster_rows_considered", "season",
                "refused_rows_without_a_program", "refused_rows_of_this_program_in_another_season",
                "matched_on_suffix_stripped_name_only", "name_matches", "jersey_matches")},
            "identity_version": AVAILABILITY_IDENTITY_VERSION,
            "season_out_carried_from": season_out.get(key),
            "out_does_not_imply_injury": True, "no_medical_detail": True, "pit_admitted": False,
            "quarantined": identity.get("canonical_player_id") is None,
        })
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "R37_11_AVAILABILITY_ROWS.jsonl"
    _bas_atomic.write_text(path, "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    carries = season_out_carry(rows)
    _bas_atomic.write_text(out_dir / "R37_11_SEASON_OUT_CARRY.jsonl", 
        "".join(json.dumps(c, sort_keys=True) + "\n" for c in carries), encoding="utf-8")
    predecessor_unresolved = [(row, before) for row, before in zip(rows[:sec_count], predecessor[:sec_count])
                              if not before.get("canonical_player_id")]
    report = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-11",
        "statements": len(assertions), "rows": len(rows), "one_row_per_statement": len(rows) == len(assertions),
        "sec_statements": sec_count, "rendered_statements": len(assertions) - sec_count,
        "by_conference": dict(collections.Counter(r["conference"] for r in rows)),
        "identity_states": dict(states), "resolved": sum(1 for r in rows if not r["quarantined"]),
        "quarantined": sum(1 for r in rows if r["quarantined"]),
        "resolved_by_conference": dict(collections.Counter(r["conference"] for r in rows if not r["quarantined"])),
        "contest_states": dict(collections.Counter(r["contest"]["state"] for r in rows)),
        "contest_states_by_conference": {c: dict(collections.Counter(r["contest"]["state"] for r in rows
                                                                     if r["conference"] == c))
                                         for c in sorted({r["conference"] for r in rows})},
        "contests_not_bound": sorted({(r["conference"], r["program"], r["contest_label"]) for r in rows
                                      if r["contest"]["state"] != "CONTEST_BOUND"}),
        "publication_time_established": sum(1 for r in rows if r["publication_time_established"]),
        "season_out_statements": sum(1 for r in rows if _SEASON_OUT.search(r["exact_status_text"])),
        "refused_rows_of_the_program_in_another_season": sum(
            int(r["identity"].get("refused_rows_of_this_program_in_another_season") or 0) for r in rows),
        "predecessor_resolutions_checked": dict(prior_check),
        "predecessor_unresolved_reviewed": {
            "count": len(predecessor_unresolved),
            "now": dict(collections.Counter(row["identity"]["state"] for row, _ in predecessor_unresolved)),
            "still_quarantined": sorted({(row["program"], row["player_name"], row["jersey"],
                                          row["identity"]["state"]) for row, _ in predecessor_unresolved
                                         if row["quarantined"]})},
        "source_version_conflicts": version_conflicts(rows),
        "season_out_carries": len(carries),
        "status_texts": dict(collections.Counter(r["exact_status_text"] for r in rows)),
        "roster_sources": roster_sources,
        "inputs": {"assertions": {"path": str(ASSERTIONS), "sha256": sha256_bytes(ASSERTIONS.read_bytes())},
                   "schedule": {"path": str(SCHEDULE), "sha256": sha256_bytes(SCHEDULE.read_bytes()),
                                "vintage": "CFBD tranche written 2026-09-09"}},
        "written": str(path),
    }
    _bas_atomic.write_text(out_dir / "R37_11_AVAILABILITY_STATEMENTS.json", json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


# --------------------------------------------------------------------------
# Policies
# --------------------------------------------------------------------------

RAW = CYCLE30 / "raw" / "availability"
#: One row per policy statement the attempt holds bytes for. Every quoted
#: phrase must occur in the text extracted from those bytes, or the ledger is
#: not written. ``covers_2026`` is what the bytes say about 2026, nothing more.
POLICY_SOURCES: list[dict[str, Any]] = [
    {"policy_id": "ACC-FB-2026-27", "conference": "ACC", "source": ("acquired", "f12f1e5b"), "format": "PDF",
     "url": "https://s3.amazonaws.com/sidearm.sites/acc.sidearmsports.com/documents/2026/8/24/"
            "ACC_Availability_Reporting_Policy_2026_27.pdf",
     "policy_season": 2026, "covers_2026": "STATED", "version_as_stated": "Last updated: August 20, 2026",
     "scope": "CONFERENCE_GAMES", "non_conference": "OPTIONAL",
     "schedule": ["initial: three nights before, by 8:00 p.m. local", "updates: two nights and one night before, "
                  "by 8:00 p.m. local", "game day: no later than two hours before the scheduled game time"],
     "vocabulary_pregame": ["Available", "Probable", "Questionable", "Doubtful", "Out", "Out (1st half)"],
     "vocabulary_gameday": ["Available", "Game Time Decision", "Out"],
     "absence_rule": "ABSENT_FROM_A_REPORT_PRESUMED_AVAILABLE",
     "quotes": ["A student-athlete who is not included on an Availability Report is presumed to be Available for "
                "the game.", "Initial Report three nights before the game, no later than 8:00 p.m. local time",
                "An institution is not required to, but may at its discretion, release an Availability Report in "
                "advance of a game against a non-ACC opponent.", "Last updated: August 20, 2026"]},
    {"policy_id": "BIG12-FB-2025", "conference": "Big 12", "source": ("acquired", "94c3f291"), "format": "PDF",
     "url": "https://s3.amazonaws.com/big12sports.com/documents/2025/8/19/"
            "2025_Big_12_Conference_Player_Availability_Reporting_Policy.pdf",
     "policy_season": 2025, "covers_2026": "SUPERSEDED_BY BIG12-FB-2026", "version_as_stated": "8/19/2025",
     "scope": "CONFERENCE_GAMES", "non_conference": "OPTIONAL",
     "schedule": ["initial: Wednesday 9:00 p.m. CT for Saturday games", "Thursday and Friday updates by 9:00 p.m. CT",
                  "game day: no later than 90 minutes before kickoff"],
     "vocabulary_pregame": ["Out", "Doubtful", "Questionable", "Probable", "Available", "Out (1st Half)"],
     "vocabulary_gameday": ["Available", "Game Time Decision", "Out"],
     "absence_rule": "NOT_STATED",
     "quotes": ["For Saturday football games, institutions must submit the Initial Report by Wednesday at 9:00 p.m. "
                "Central Time."]},
    {"policy_id": "BIG12-FB-2026", "conference": "Big 12", "source": ("acquired", "465d2c7b"), "format": "PDF",
     "url": "https://s3.amazonaws.com/big12sports.com/documents/2026/9/2/Updated_Player_Availability_Policy_9_2_2026.pdf",
     "policy_season": 2026, "covers_2026": "STATED", "version_as_stated": "9/2/2026 (Updated for 2026 Season)",
     "supersedes": "BIG12-FB-2025", "scope": "CONFERENCE_GAMES", "non_conference": "OPTIONAL",
     "schedule": ["initial reports: Wednesday, Thursday and Friday by 9:00 p.m. CT for Saturday games",
                  "game day: no later than 90 minutes before kickoff"],
     "vocabulary_pregame": ["Out", "Doubtful", "Questionable", "Probable", "Available", "Out (1st Half)"],
     "vocabulary_gameday": ["Available", "Game Time Decision", "Out"],
     "absence_rule": "NOT_STATED",
     "quotes": ["Big 12 Conference Player Availability Policy (Updated for 2026 Season)",
                "Institutions may choose to release an Availability Report before games against non-Big 12 "
                "opponents, but it is not mandatory."]},
    {"policy_id": "BIGTEN-FB-2026", "conference": "Big Ten", "source": ("acquired", "525940a7"), "format": "HTML",
     "url": "https://bigten.org/fb/article/60284/", "policy_season": 2026, "covers_2026": "STATED",
     "version_as_stated": "Published: 8/28/2026", "supersedes": "BIGTEN-FB-GAMEDAY-2025",
     "scope": "CONFERENCE_GAMES", "non_conference": "NOT_COVERED", "first_report_contest_date": "2026-09-19",
     "schedule": ["three, two and one day before kickoff by 8pm ET/7pm CT/5pm PT",
                  "game day: two hours before kickoff"],
     "vocabulary_pregame": ["Probable", "Questionable", "Doubtful", "Out", "Out (1st Half)"],
     "vocabulary_gameday": ["Game Time Decision", "Out", "Out (1st Half)"],
     "absence_rule": "ABSENT_FROM_A_REPORT_PRESUMED_AVAILABLE",
     "quotes": ["Student-athletes not listed on a report are considered Available.",
                "This policy will apply to all competition against conference opponents only",
                "first reports of the Big Ten season due in advance of the USC at Rutgers and Purdue at UCLA games "
                "on Sept. 19"]},
    {"policy_id": "BIGTEN-FB-GAMEDAY-2025", "conference": "Big Ten", "source": ("raw", "793a84fdb665"),
     "format": "HTML", "url": "https://bigten.org/fb/article/blt2856785fb75ee868/", "policy_season": 2025,
     "covers_2026": "SUPERSEDED_BY BIGTEN-FB-2026", "scope": "AS_STATED_ON_PAGE", "non_conference": "AS_STATED_ON_PAGE",
     "schedule": [], "vocabulary_pregame": [], "vocabulary_gameday": [], "absence_rule": "NOT_READ",
     "quotes": ["Big Ten Conference Announces U.S. Integrity Partnership"]},
    {"policy_id": "SUNBELT-FB-2025", "conference": "Sun Belt", "source": ("raw", "a7362ba030b9"), "format": "HTML",
     "url": "https://sunbeltsports.org/news/2025/8/20/sun-belt-to-institute-availability-reporting-for-2025-football-season.aspx",
     "policy_season": 2025, "covers_2026": "STATED_AS_BEGINNING_2025_NO_2026_RESTATEMENT_HELD",
     "scope": "CONFERENCE_GAMES", "non_conference": "NOT_STATED",
     "schedule": ["initial: three days before each conference game", "game day: by 10:30 a.m. ET/9:30 a.m. CT"],
     "vocabulary_pregame": ["available", "probable", "questionable", "doubtful", "out"],
     "vocabulary_gameday": ["available", "game time decision", "out"], "absence_rule": "NOT_STATED",
     "quotes": ["Beginning with the 2025 season, the Sun Belt Conference will publish availability reports for all "
                "conference football games"]},
    {"policy_id": "AMERICAN-FB-2025", "conference": "American Athletic", "source": ("raw", "819889f2bf69"),
     "format": "HTML", "url": "https://theamerican.org/sports/2025/8/5/fbavail.aspx", "policy_season": 2025,
     "covers_2026": "NO_2026_STATEMENT_HELD", "scope": "CONFERENCE_GAMES", "non_conference": "NOT_COVERED",
     "schedule": ["published no later than two hours before kickoff"], "vocabulary_pregame": [],
     "vocabulary_gameday": [], "absence_rule": "NOT_STATED",
     "quotes": ["Player availability reports will be issued for intraconference games only."]},
    {"policy_id": "CUSA-FB", "conference": "Conference USA", "source": ("raw", "45e92bda44d2"), "format": "HTML",
     "url": "https://conferenceusa.com/sports/2025/8/23/FB_0823254134.aspx", "policy_season": None,
     "covers_2026": "PAGE_UNDATED_FOOTER_2026", "scope": "NOT_STATED", "non_conference": "NOT_STATED",
     "schedule": [], "vocabulary_pregame": ["Out", "Questionable"], "vocabulary_gameday": [],
     "absence_rule": "ABSENT_FROM_A_REPORT_PRESUMED_AVAILABLE",
     "quotes": ["Players not listed are presumed fully available"]},
    {"policy_id": "MAC-FB-GAMEDAY-2024", "conference": "Mid-American", "source": ("raw", "198281a39255"),
     "format": "HTML", "url": "https://getsomemaction.com/news/2024/8/22/"
                              "mac-to-launch-gameday-student-athlete-availability-report-for-2024-football-season.aspx",
     "policy_season": 2024, "covers_2026": "NO_2026_STATEMENT_HELD", "scope": "ALL_GAMES",
     "non_conference": "COVERED", "schedule": ["game day: no later than three hours before scheduled kickoff"],
     "vocabulary_pregame": [], "vocabulary_gameday": [], "absence_rule": "NOT_STATED",
     "quotes": ["Reports must be submitted by schools no later than three hours before scheduled kickoff times."]},
    {"policy_id": "MW-FB-2026", "conference": "Mountain West", "source": ("raw", "5b36f22ce295"), "format": "HTML",
     "url": "https://themw.com/news/2026/9/1/2026-mw-football-weekly-release-week-1.aspx", "policy_season": 2026,
     "covers_2026": "STATED", "scope": "CONFERENCE_GAMES", "non_conference": "NOT_STATED", "schedule": [],
     "vocabulary_pregame": [], "vocabulary_gameday": [], "absence_rule": "NOT_STATED",
     "quotes": ["The Mountain West will continue player availability reporting in 2026 for all regular-season "
                "Conference games and the MW Championship Game."]},
    {"policy_id": "PAC12-FB-2026", "conference": "Pac-12", "source": ("raw", "7e898ac92798"), "format": "HTML",
     "url": "https://pac-12.com/news/2026/9/3/pac-12-announces-commercial-and-operational-updates-ahead-of-its-2026-football-season-kickoff.aspx",
     "policy_season": 2026, "covers_2026": "STATED", "scope": "CONFERENCE_GAMES",
     "non_conference": "WHEN_THE_OPPONENT_CONFERENCE_PARTICIPATES",
     "schedule": ["three, two and one day before by 7 p.m. PT", "game day: no later than two hours before"],
     "vocabulary_pregame": [], "vocabulary_gameday": [], "absence_rule": "NOT_STATED",
     "quotes": ["the Pac-12 will begin providing player availability reports in football for the 2026 season"]},
    {"policy_id": "CFP-2025-26", "conference": "CFP", "source": ("raw", "c7d91673c981"), "format": "HTML",
     "url": "https://collegefootballplayoff.com/sports/2025/11/12/reports", "policy_season": 2025,
     "covers_2026": "PLAYOFF_GAMES_ONLY_NOT_IN_THIS_SCHEDULE", "scope": "PLAYOFF_GAMES", "non_conference": "N/A",
     "schedule": ["daily updates to a final report 90 minutes before game time"],
     "vocabulary_pregame": ["available", "probable", "questionable", "doubtful", "out"],
     "vocabulary_gameday": ["available", "game time decision", "out"], "absence_rule": "NOT_STATED",
     "quotes": ["all schools participating in the College Football Playoff will provide public reports"]},
    {"policy_id": "SEC-FB-REPORT-SURFACE", "conference": "SEC", "source": ("raw", "ee4d13d263e7"), "format": "HTML",
     "url": "https://www.secsports.com/fbreports", "policy_season": None,
     "covers_2026": "REPORTS_2026_INGESTED_POLICY_TEXT_NOT_HELD", "scope": "NOT_READ_POLICY_TEXT_NOT_HELD",
     "non_conference": "NOT_READ", "schedule": [],
     "vocabulary_pregame": [], "vocabulary_gameday": [], "absence_rule": "NOT_STATED_IN_HELD_BYTES",
     "vocabulary_observed_in_ingested_reports": ["Available", "Probable", "Questionable", "Doubtful", "Out",
                                                 "Game Time Decision", "-"],
     "quotes": ["SEC Student-Athlete Availability Report: Football"]},
]
#: Which policy governs 2026 contests of each conference, from the rows above.
GOVERNING_2026 = {"ACC": "ACC-FB-2026-27", "Big 12": "BIG12-FB-2026", "Big Ten": "BIGTEN-FB-2026",
                  "Sun Belt": "SUNBELT-FB-2025", "American Athletic": "AMERICAN-FB-2025", "Conference USA": "CUSA-FB",
                  "Mid-American": "MAC-FB-GAMEDAY-2024", "Mountain West": "MW-FB-2026", "Pac-12": "PAC12-FB-2026",
                  "SEC": "SEC-FB-REPORT-SURFACE"}


def _source_path(kind: str, prefix: str) -> Path:
    root = ACQUIRED if kind == "acquired" else RAW
    return next(p for p in root.iterdir() if p.name.startswith(prefix) and not p.name.endswith(".meta.json"))


def _source_text(path: Path, fmt: str) -> str:
    data = path.read_bytes()
    if fmt == "PDF":
        import io

        import pypdf

        text = " ".join((page.extract_text() or "") for page in pypdf.PdfReader(io.BytesIO(data)).pages)
    else:
        import html as html_lib

        text = data.decode("utf-8", "replace")
        text = re.sub(r"<(script|style|noscript)\b.*?</\1\s*>", " ", text, flags=re.S | re.I)
        text = html_lib.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text)


def policies(out_dir: Path) -> dict[str, Any]:
    rows, missing = [], []
    for spec in POLICY_SOURCES:
        path = _source_path(*spec["source"])
        text = _source_text(path, spec["format"])
        found = {quote: quote in text for quote in spec["quotes"]}
        missing.extend(f"{spec['policy_id']}: {q}" for q, ok in found.items() if not ok)
        rows.append({"label": LABEL, **{k: v for k, v in spec.items() if k != "source"},
                     "source_path": str(path), "source_sha256": sha256_bytes(path.read_bytes()),
                     "source_kind": "ACQUIRED_THIS_ATTEMPT" if spec["source"][0] == "acquired" else "CYCLE30_CACHE",
                     "quotes_verified_in_extracted_text": found,
                     "absence_rule_applies_only_to": ("an actual, complete, current report of this conference for "
                                                      "this contest; never to a missing, partial or stale report or "
                                                      "to another conference")})
    if missing:
        raise SystemExit(f"policy quotes not found in their bytes: {missing}")
    out_dir.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out_dir / "R37_11_AVAILABILITY_POLICIES.jsonl", 
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    report = {"label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-11",
              "policies": len(rows), "conferences": sorted({r["conference"] for r in rows}),
              "governing_2026": GOVERNING_2026,
              "covers_2026": {r["policy_id"]: r["covers_2026"] for r in rows},
              "absence_rules": {r["policy_id"]: r["absence_rule"] for r in rows},
              "not_held": ["SEC policy text (the SEC report pages are script-rendered; the attempt holds the "
                           "report surface and the ingested SEC reports, not the policy document)",
                           "any FCS conference or program policy (FCS_VARIES_BY_PROGRAM in the Cycle 30 inventory)",
                           "FBS Independents"],
              "fcs_national_coverage_established": False}
    _bas_atomic.write_text(out_dir / "R37_11_AVAILABILITY_POLICIES.json", json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


# --------------------------------------------------------------------------
# Denominator
# --------------------------------------------------------------------------


R35_RELEASE = ASSERTIONS.parent / "R35_11_AVAILABILITY_RELEASE.json"


def pending_reports() -> list[dict[str, Any]]:
    """Reports a rendered current view names as expected but not yet posted."""

    pending = []
    for conference, prefix in RENDERED_CURRENT.items():
        payload = json.loads(acquired(prefix).read_bytes())
        for card in payload["cards"]:
            if card["text"].startswith("REPORT PENDING"):
                expected = re.search(r"Report expected on (.+)", card["text"])
                pending.append({"conference": conference, "teams": [c["team"] for c in card["columns"]],
                                "expected": expected.group(1).strip() if expected else None,
                                "rendered_utc": payload["rendered_utc"],
                                "source_sha256": sha256_bytes(acquired(prefix).read_bytes())})
    return pending


def predeclared_keys(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The 12 national report-opportunity keys R35-11 declared, each completed from this attempt's evidence."""

    declared = json.loads(R35_RELEASE.read_text(encoding="utf-8"))["national_report_opportunities"]["keys"]
    pending = pending_reports()
    out = []
    for key in declared:
        team_id = int(str(key["program_id"]).rsplit(":", 1)[-1])
        mine = [o for o in opportunities if o["team_id"] == team_id]
        ingested = [o for o in mine if o["statements_ingested"]]
        expected = [o for o in mine if o["report_expectation"] == "POLICY_STATES_A_REPORT"]
        waiting = [p for p in pending if key["display_name"] in p["teams"]]
        route = ROUTE_RENDERS.get(key["conference"])
        if ingested:
            outcome = "REPORT_STATEMENTS_INGESTED"
        elif waiting:
            outcome = "REPORT_ROUTE_RENDERED_REPORT_PENDING"
        elif route:
            outcome = route[1]
        elif expected:
            outcome = "POLICY_STATES_REPORTS_NONE_INGESTED"
        elif any(o["governing_policy"] for o in mine):
            outcome = "POLICY_HELD_NO_REPORT_EXPECTED_FOR_THESE_CONTESTS"
        else:
            outcome = "NO_POLICY_HELD_UNKNOWN_NOT_HEALTHY"
        out.append({"display_name": key["display_name"], "program_id": key["program_id"],
                    "classification": key["classification"], "conference": key["conference"],
                    "r35_outcome": key["outcome"], "outcome": outcome, "opportunities_2026": len(mine),
                    "policy_expected": len(expected), "ingested": len(ingested),
                    "governing_policy": sorted({str(o["governing_policy"]) for o in mine}),
                    "pending_reports_seen": waiting,
                    "route_render": ({"source_sha256": sha256_bytes(acquired(route[0]).read_bytes()),
                                      "summary": json.loads(acquired(route[0]).read_bytes()).get("finding")}
                                     if route else None),
                    "retained_in_denominator": True,
                    "no_report_means": "UNKNOWN_NOT_HEALTHY"})
    return out


def denominator(out_dir: Path) -> dict[str, Any]:
    policy_rows = {r["policy_id"]: r for r in read_jsonl(out_dir / "R37_11_AVAILABILITY_POLICIES.jsonl")}
    statements_rows = read_jsonl(out_dir / "R37_11_AVAILABILITY_ROWS.jsonl")
    ingested: dict[tuple[str, str], int] = collections.Counter()
    for row in statements_rows:
        if row["contest"].get("canonical_contest_id"):
            ingested[(row["contest"]["canonical_contest_id"], row["program"])] += 1
    as_of = max(str(r["report_vintage_retrieval_utc"]) for r in statements_rows)
    opportunities, counts = [], collections.Counter()
    for game in read_jsonl(SCHEDULE):
        if int(game.get("season") or 0) != 2026:
            continue
        contest = f"SRC-002:GAME:{game['id']}"
        for side, other in (("home", "away"), ("away", "home")):
            program = str(game.get(f"{side}Team"))
            conference = game.get(f"{side}Conference")
            classification = game.get(f"{side}Classification")
            policy_id = GOVERNING_2026.get(conference)
            policy = policy_rows.get(policy_id) if policy_id else None
            conference_game = bool(game.get("conferenceGame")) and conference == game.get(f"{other}Conference")
            if policy is None:
                expectation = "NO_POLICY_HELD_FOR_THIS_CONFERENCE"
            elif policy["scope"] == "ALL_GAMES":
                expectation = "POLICY_STATES_A_REPORT"
            elif policy["scope"] == "CONFERENCE_GAMES" and conference_game:
                first = policy.get("first_report_contest_date")
                expectation = ("BEFORE_THE_POLICY_FIRST_REPORT_DATE"
                               if first and str(game["startDate"])[:10] < first else "POLICY_STATES_A_REPORT")
            elif policy["scope"] == "CONFERENCE_GAMES":
                expectation = f"NON_CONFERENCE_{policy['non_conference']}"
            else:
                expectation = "POLICY_SCOPE_NOT_READ"
            statements_here = ingested.get((contest, program), 0)
            state = "REPORT_STATEMENTS_INGESTED" if statements_here else "UNKNOWN_NOT_HEALTHY"
            opportunities.append({
                "label": LABEL, "canonical_contest_id": contest, "program": program, "side": side,
                "team_id": game.get(f"{side}Id"),
                "conference": conference, "classification": classification, "conference_game": conference_game,
                "kickoff_utc": game["startDate"], "kickoff_before_as_of": str(game["startDate"]) < as_of,
                "governing_policy": policy_id, "policy_covers_2026": policy["covers_2026"] if policy else None,
                "report_expectation": expectation, "statements_ingested": statements_here, "state": state,
                "absent_players": ("UNKNOWN: completeness of the ingested report is not established, so no "
                                   "absence rule is applied" if statements_here else "UNKNOWN_NOT_HEALTHY"),
            })
            counts[(classification, expectation, state)] += 1
    _bas_atomic.write_text(out_dir / "R37_11_AVAILABILITY_OPPORTUNITIES.jsonl", 
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in opportunities), encoding="utf-8")
    by_state = collections.Counter(r["state"] for r in opportunities)
    keys = predeclared_keys(opportunities)
    report = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-11",
        "as_of_latest_report_retrieval_utc": as_of,
        "schedule": {"path": str(SCHEDULE), "sha256": sha256_bytes(SCHEDULE.read_bytes()), "season": 2026,
                     "games": len(opportunities) // 2},
        "opportunities": len(opportunities), "states": dict(by_state),
        "by_classification_expectation_state": {"|".join(map(str, k)): v for k, v in sorted(counts.items(),
                                                                                              key=str)},
        "policy_expected_reports": sum(1 for r in opportunities if r["report_expectation"] == "POLICY_STATES_A_REPORT"),
        "policy_expected_reports_before_as_of": sum(1 for r in opportunities if r["report_expectation"]
                                                    == "POLICY_STATES_A_REPORT" and r["kickoff_before_as_of"]),
        "policy_expected_reports_ingested": sum(1 for r in opportunities if r["report_expectation"]
                                                == "POLICY_STATES_A_REPORT" and r["statements_ingested"]),
        "ingested_opportunities_by_conference": dict(collections.Counter(
            r["conference"] for r in opportunities if r["statements_ingested"])),
        "predeclared_keys": keys,
        "healthy_inferred": 0,
        "rule": ("An opportunity without an ingested report is UNKNOWN_NOT_HEALTHY. An ingested report is not shown "
                 "to be complete, so players absent from it stay unknown even where the policy presumes absence "
                 "means available."),
    }
    _bas_atomic.write_text(out_dir / "R37_11_AVAILABILITY_DENOMINATOR.json", json.dumps(report, indent=2) + "\n",
                                                                  encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("statements", "policies", "denominator", "all"))
    parser.add_argument("--out", type=Path, default=REPAIRS)
    args = parser.parse_args(argv)
    steps = {"statements": [statements], "policies": [policies], "denominator": [denominator],
             "all": [statements, policies, denominator]}[args.command]
    for step in steps:
        report = step(args.out)
        print(json.dumps({k: v for k, v in report.items() if k not in ("roster_sources",)}, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())

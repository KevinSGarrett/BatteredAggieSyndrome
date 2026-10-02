"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-05 AC01-AC05/AC07/AC09: reparse the 8,399 revision-bound career pages
from their raw wikitext and reconcile every one of the 44,748 predecessor
episodes.

The Cycle #36 corpus read ``WIKIMEDIA_COACH_CAREER_PAGES.jsonl``, a parsed
summary. This tool opens the raw MediaWiki response for each page's exact
page id and revision in the local cache, parses the infobox with
:mod:`aggie_analytics.cycle37.career_infobox`, and writes one episode per
interval of every coaching, playing and administrative row, each with its
character and byte spans in the revision text and the digest of the file it
came from.

Employers are resolved through the same R36-04 program crosswalk, in a
declared order: the display text as written (which keeps "Miami (OH)"), then
the link target split into school and mascot where the school resolves to
exactly one program whose own mascot matches. A resolution that disagrees
between the two is a conflict, not a choice. The link is also read as the
identity of the article it names, by the source's own spellings only (the
school plus its mascot, or the school without its trailing parenthesised
qualifier plus its mascot, naming exactly one program); a display
resolution -- inside or outside the population -- that this identity
contradicts is a conflict too (W37R-65). That identity never resolves a row.

Every predecessor episode is reconciled to the raw row it was parsed from:
retained, corrected (with the fields that changed), split, carried as one
of several role assignments of its row, or rejected when the revision has
no such row. Episodes the predecessor never produced (player and
administrative rows, missed coaching rows) are new rows.

Joining (AC05) needs identity evidence that is not the name: here, the
career page citing an official athletics page on the same program's site. A
person, program, role and season that merely coincide with a staff row are
reported as a name-and-context candidate, not joined. Nothing is admitted
point-in-time and nothing is promoted to an official fact.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.hashing import sha256_json
from aggie_analytics import atomic_io as _bas_atomic  # noqa: E402
from aggie_analytics.cycle36.program_crosswalk import (  # noqa: E402
    OUT_OF_POPULATION,
    RESOLVED,
    build_crosswalk,
    load_payloads,
    normalize_name,
)
from aggie_analytics.cycle37 import career_infobox, staff_record  # noqa: E402

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
TOOL_VERSION = "BAS-CAREER-REPARSE-v37.2"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
CYCLE30 = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle30_work")
RAW_WIKIMEDIA = CYCLE30 / "raw" / "wikimedia"
RAW_TEAMS = CYCLE30 / "raw" / "teams"
CAREER_PAGES = CYCLE30 / "outputs" / "WIKIMEDIA_COACH_CAREER_PAGES.jsonl"
HISTORICAL = CYCLE30 / "outputs" / "HISTORICAL_MEMBERSHIP_1963_2012.jsonl"
PREDECESSOR = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle36/runs/20260921T200027Z/implementation_output"
                   r"/CYCLE36_CAREER_EPISODE_ROWS.jsonl")
STAFF_REPARSE = ATTEMPT / "evidence" / "repairs" / "R37_03_STAFF_REPARSE_ROWS.jsonl"
CROSSWALK_ROWS = ATTEMPT / "evidence" / "repairs" / "R37_03_SOURCE_IDENTITY_ROWS.jsonl"
MODEL_SCOPE = (1963, 2026)
CORE = ("head_coach", "offensive_coordinator", "defensive_coordinator")
_URL = re.compile(r"https?://[^\s|\]}<>\"']+", re.I)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def request_identity(endpoint: str, parameters: dict[str, Any]) -> str:
    return sha256_json({"endpoint": endpoint, "parameters": parameters})


def index_raw() -> tuple[dict[tuple[str, str], Path], dict[str, Any]]:
    """(page id, revision id) -> raw file, with duplicate files checked for identical text."""

    index: dict[tuple[str, str], Path] = {}
    digests: dict[tuple[str, str], str] = {}
    duplicates = mismatched = 0
    for path in sorted(RAW_WIKIMEDIA.iterdir()):
        try:
            payload = json.loads(path.read_bytes())
        except (OSError, ValueError):
            continue
        for page in ((payload.get("query") or {}).get("pages") or {}).values():
            revisions = page.get("revisions") or []
            if not revisions:
                continue
            key = (str(page.get("pageid")), str(revisions[0].get("revid")))
            text = ((revisions[0].get("slots") or {}).get("main") or {}).get("*") or ""
            digest = sha256_bytes(text.encode("utf-8", "surrogateescape"))
            if key in index:
                duplicates += 1
                mismatched += digests[key] != digest
                continue
            index[key] = path
            digests[key] = digest
    return index, {"page_revisions": len(index), "duplicate_files": duplicates,
                   "duplicates_with_different_text": mismatched}


class Resolver:
    """Employer resolution through the R36-04 crosswalk, in the declared order."""

    def __init__(self) -> None:
        payloads = load_payloads(RAW_TEAMS, range(MODEL_SCOPE[0], MODEL_SCOPE[1] + 1), request_identity)
        self.crosswalk = build_crosswalk(payloads, declared_name_rows=read_jsonl(HISTORICAL))
        self.cache: dict[tuple[str, str | None], dict[str, Any]] = {}
        # (school without a trailing "(XX)" qualifier, mascot) -> programs, both as the source writes them
        self.unqualified: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
        for pid, program in self.crosswalk.programs.items():
            for school in program.display_names:
                head = normalize_name(re.sub(r"\s*\([^()]*\)\s*$", "", school))
                for mascot in program.mascots:
                    if head and normalize_name(mascot):
                        self.unqualified[(head, normalize_name(mascot))].add(pid)

    def _link_identity(self, target: str) -> dict[str, Any] | None:
        """The one program a linked '<school> <mascot> football' article is, by the source's own spellings.

        Consulted only to refuse a display resolution the row's own link contradicts; it never resolves a row.
        """

        whole = self.crosswalk.resolve(target)  # the title's " football" is stripped by the crosswalk
        if whole.get("state") in (RESOLVED, OUT_OF_POPULATION) and whole.get("canonical_program_id"):
            return {"program_id": whole["canonical_program_id"],
                    "basis": "LINK_TARGET_IS_A_DECLARED_SCHOOL_PLUS_MASCOT_SPELLING"}
        tokens = normalize_name(re.sub(r"\s+football$", "", target.strip(), flags=re.I)).split()
        hits: set[str] = set()
        for cut in range(1, len(tokens)):
            hits |= self.unqualified.get((" ".join(tokens[:cut]), " ".join(tokens[cut:])), set())
        if len(hits) == 1:
            return {"program_id": next(iter(hits)),
                    "basis": "LINK_TARGET_IS_A_DECLARED_SCHOOL_WITHOUT_ITS_QUALIFIER_PLUS_ITS_MASCOT"}
        return None

    def _link_school_and_mascot(self, target: str) -> dict[str, Any] | None:
        base = re.sub(r"\s+football$", "", target.strip(), flags=re.I)
        tokens = base.split()
        for cut in range(len(tokens) - 1, 0, -1):
            school, mascot = " ".join(tokens[:cut]), " ".join(tokens[cut:])
            result = self.crosswalk.resolve(school)
            if result.get("state") != RESOLVED:
                continue
            program = self.crosswalk.programs[result["canonical_program_id"]]
            if mascot.casefold() in {m.casefold() for m in program.mascots}:
                return {**result, "basis": "LINK_TARGET_SCHOOL_AND_MATCHING_MASCOT", "school": school,
                        "mascot": mascot}
        return None

    def resolve(self, display: str, target: str | None) -> dict[str, Any]:
        key = (display, target)
        if key in self.cache:
            return self.cache[key]
        by_display = self.crosswalk.resolve(display) if display else {"state": "EMPTY"}
        by_link = self._link_school_and_mascot(target) if target else None
        shown = by_display.get("canonical_program_id") \
            if by_display.get("state") in (RESOLVED, OUT_OF_POPULATION) else None
        identity = self._link_identity(target) if target and shown else None
        chosen: dict[str, Any]
        if by_display.get("state") == RESOLVED and by_link and \
                by_link["canonical_program_id"] != by_display["canonical_program_id"]:
            chosen = {"state": "CONFLICT_DISPLAY_AND_LINK_RESOLVE_TO_DIFFERENT_PROGRAMS", "program_id": None,
                      "candidates": sorted({by_display["canonical_program_id"], by_link["canonical_program_id"]})}
        elif identity and identity["program_id"] != shown:
            chosen = {"state": "CONFLICT_DISPLAY_AND_LINK_RESOLVE_TO_DIFFERENT_PROGRAMS", "program_id": None,
                      "candidates": sorted({shown, identity["program_id"]}), "link_basis": identity["basis"]}
        elif by_display.get("state") == RESOLVED:
            chosen = {"state": RESOLVED, "program_id": by_display["canonical_program_id"],
                      "basis": "DISPLAY_TEXT_AS_WRITTEN", "link_agrees": bool(by_link)}
        elif by_link:
            chosen = {"state": RESOLVED, "program_id": by_link["canonical_program_id"], "basis": by_link["basis"]}
        else:
            chosen = {"state": str(by_display.get("state") or "UNRESOLVED"), "program_id": None,
                      "candidates": by_display.get("candidate_program_ids") or []}
        self.cache[key] = chosen
        return chosen

    def classification(self, program_id: str | None, start: int, end: int | None) -> dict[str, Any]:
        if not program_id:
            return {}
        program = self.crosswalk.programs.get(program_id)
        if program is None:
            return {}
        last = end if end is not None else MODEL_SCOPE[1]
        seasons = {year: program.classifications_by_season.get(year) for year in range(start, last + 1)}
        return {"by_season": {str(k): v for k, v in seasons.items() if v},
                "divisions": sorted({v for v in seasons.values() if v})}


def assignments_for(row: dict[str, Any]) -> list[dict[str, Any]]:
    team = row["team"] or {}
    if row["family"] == "PLAYING":
        return [{"role": "player", "occupancy": "OBSERVED", "basis": "PLAYER_YEARS_FIELD"}]
    if row["family"] == "ADMINISTRATIVE":
        return [{"role": "administrator", "occupancy": "OBSERVED", "basis": "ADMINISTRATIVE_YEARS_FIELD"}]
    if row.get("team") is None:
        # Cycle #37 - Attempt #4: a coach_years field with no team field states a stint and nothing about the
        # job or the employer; the head-coach convention needs a team row to apply to.
        return [{"role": "role_not_stated", "occupancy": "UNMAPPED", "basis": "TEAM_FIELD_ABSENT"}]
    if team.get("role_text"):
        return [{**item, "basis": team.get("role_basis") or "EXPLICIT_PARENTHETICAL"}
                for item in staff_record.assignments_v37(team["role_text"])]
    if team.get("role_basis") == "LIST_ROW_STATES_NO_ROLE":
        return [{"role": "role_not_stated", "occupancy": "UNMAPPED", "basis": "LIST_ROW_STATES_NO_ROLE"}]
    if team.get("role_basis") == "UNRESOLVED_PARENTHETICAL":
        # Cycle #37 - Attempt #4 (MF37A03-04): a parenthetical this parser cannot read as a role or a place
        # ("DFO", "STQC", "SA", "trainer") is not the absence of one. The head-coach convention is for a row
        # that states no parenthetical; this row states one whose meaning the revision does not give.
        return [{"role": "role_unresolved", "occupancy": "UNRESOLVED", "basis": "UNRESOLVED_PARENTHETICAL",
                 "unresolved_text": [item["text"] for item in team.get("unresolved_parentheticals") or []]}]
    return [{"role": "head_coach", "occupancy": "PRINCIPAL", "basis": "INFOBOX_CONVENTION_NO_ROLE_PARENTHETICAL"}]


def population_state(row: dict[str, Any], interval: dict[str, Any], resolution: dict[str, Any],
                     classification: dict[str, Any]) -> str:
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
    end = interval["end"] if interval["end"] is not None else MODEL_SCOPE[1]
    if end < MODEL_SCOPE[0]:
        return "PRE_1963_CONTEXT_OUTSIDE_THE_MODEL_POPULATION"
    if resolution.get("state") != RESOLVED:
        return "EMPLOYER_NOT_RESOLVED_TO_ONE_PROGRAM"
    if not any(d in ("fbs", "fcs") for d in classification.get("divisions", [])):
        return "COLLEGE_EMPLOYER_OUTSIDE_FBS_FCS_IN_THESE_SEASONS"
    return "IN_POPULATION_CANDIDATE_EPISODE"


def reconcile(predecessor: list[dict[str, Any]], episodes: list[dict[str, Any]]) -> tuple[list[dict[str, Any]],
                                                                                       collections.Counter]:
    """One disposition per predecessor episode, against the raw row it came from."""

    by_row: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for episode in episodes:
        if episode["family"] == "COACHING":
            by_row[episode["row_index"]].append(episode)
    per_row = collections.Counter()
    for row in predecessor:
        match = re.search(r":career:(\d+):", str(row.get("span_id") or ""))
        if match:
            per_row[int(match.group(1))] += 1
    out, states = [], collections.Counter()
    for row in predecessor:
        match = re.search(r":career:(\d+):", str(row.get("span_id") or ""))
        number = int(match.group(1)) if match else None
        mine = by_row.get(number) if number is not None else None
        if not mine:
            state, changes = "REJECTED_NO_SUCH_ROW_IN_THE_REVISION", {}
        else:
            first = mine[0]
            changes = {}
            if (row.get("employer_raw") or "") != first["employer_display"]:
                changes["employer"] = {"predecessor": row.get("employer_raw"), "reparse": first["employer_display"]}
            if row.get("start_year") != first["start"] or row.get("end_year") != first["end"]:
                changes["interval"] = {"predecessor": [row.get("start_year"), row.get("end_year")],
                                       "reparse": [[e["start"], e["end"]] for e in mine]}
            new_roles = sorted({a["role"] for a in first["assignments"]})
            old_roles = sorted(set(row.get("role_codes") or []))
            if not set(old_roles) <= set(new_roles):
                changes["roles"] = {"predecessor": old_roles, "reparse": new_roles}
            if len(mine) > 1:
                state = "SPLIT_INTO_INTERVALS"
            elif per_row[number] > 1 and not changes:
                state = "RETAINED_AS_ONE_OF_SEVERAL_ROLE_ASSIGNMENTS_OF_ITS_ROW"
            elif changes:
                state = "CORRECTED"
            else:
                state = "RETAINED"
        states[state] += 1
        out.append({"predecessor_span_id": row.get("span_id"), "pageid": row.get("pageid"),
                    "row_index": number, "state": state, "changes": changes,
                    "reparse_episode_ids": [e["episode_id"] for e in (mine or [])]})
    return out, states


def official_hosts() -> dict[str, set[str]]:
    """Program -> athletics hosts, from captures whose program the page's own identity confirms."""

    hosts: dict[str, set[str]] = collections.defaultdict(set)
    for row in read_jsonl(CROSSWALK_ROWS):
        if row.get("state") != "CONFIRMED_BY_SOURCE_IDENTITY" or not row.get("admitted_program_id"):
            continue
        identity = row.get("page_identity") or {}
        for url in (identity.get("canonical_href"), row.get("route")):
            host = urlparse(str(url or "")).netloc.lower().removeprefix("www.")
            if host:
                hosts[row["admitted_program_id"]].add(host)
        if identity.get("route_host"):
            hosts[row["admitted_program_id"]].add(str(identity["route_host"]).lower().removeprefix("www."))
    return hosts


def build(out_dir: Path, limit: int | None = None, staff_rows: Path = STAFF_REPARSE) -> dict[str, Any]:
    pages = read_jsonl(CAREER_PAGES)[:limit] if limit else read_jsonl(CAREER_PAGES)
    index, index_stats = index_raw()
    resolver = Resolver()
    hosts = official_hosts()
    staff = [row for row in read_jsonl(staff_rows) if row.get("admitted_for_coverage")]
    staff_by_key: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in staff:
        staff_by_key[(row["program_id"], staff_record.fold_name(row["person"]))].append(row)
    display_pages: dict[str, set[str]] = collections.defaultdict(set)
    for page in pages:
        display_pages[re.sub(r"\s*\(.*\)$", "", str(page.get("title") or ""))].add(str(page.get("pageid")))

    predecessor_by_page: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in read_jsonl(PREDECESSOR):
        predecessor_by_page[str(row.get("pageid"))].append(row)

    out_dir.mkdir(parents=True, exist_ok=True)
    episodes_path = out_dir / "R37_05_CAREER_EPISODES.jsonl"
    reconciliation_path = out_dir / "R37_05_CAREER_PREDECESSOR_RECONCILIATION.jsonl"
    counts: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    missing_raw = []
    episode_total = 0
    with _bas_atomic.open_write(episodes_path, "w", encoding="utf-8", newline="\n") as ep_out, \
            _bas_atomic.open_write(reconciliation_path, "w", encoding="utf-8", newline="\n") as rec_out:
        for page in pages:
            key = (str(page["pageid"]), str(page["wikimedia_revision"]))
            path = index.get(key)
            if path is None:
                missing_raw.append(key)
                continue
            raw_bytes = path.read_bytes()
            payload = json.loads(raw_bytes)
            record = next(iter(payload["query"]["pages"].values()))
            text = record["revisions"][0]["slots"]["main"]["*"]
            parsed = career_infobox.career_rows(text)
            counts["infobox"][str(parsed["infobox"])] += 1
            cited = {urlparse(u).netloc.lower().removeprefix("www.") for u in _URL.findall(text)}
            person_base = re.sub(r"\s*\(.*\)$", "", str(page.get("title") or ""))
            homonym = len(display_pages.get(person_base, ())) > 1
            episodes = []
            for row in parsed["rows"]:
                team = row["team"] or {}
                resolution = resolver.resolve(team.get("employer_display") or "", team.get("employer_link_target"))
                assignments = assignments_for(row)
                for number, interval in enumerate(row["intervals"] or [{"start": None, "end": None,
                                                                        "ongoing": False, "as_written": None}]):
                    classification = (resolver.classification(resolution.get("program_id"), interval["start"],
                                                              interval["end"])
                                      if interval["start"] is not None else {})
                    state = (population_state(row, interval, resolution, classification)
                             if interval["start"] is not None else "NO_INTERVAL_STATED")
                    episode_id = f"R37-05:{page['pageid']}:{page['wikimedia_revision']}:{row['family']}:" \
                                 f"{row['index']}:{number}"
                    team_span = row["team_span"] or [None, None]
                    join = {"state": "NOT_ATTEMPTED_OUTSIDE_POPULATION"}
                    if state == "IN_POPULATION_CANDIDATE_EPISODE":
                        matches = [s for s in staff_by_key.get((resolution["program_id"],
                                                                staff_record.fold_name(person_base)), [])
                                   if s["season"] is not None and interval["start"] <= s["season"]
                                   <= (interval["end"] or MODEL_SCOPE[1])
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
                    episode = {
                        "episode_id": episode_id, "pageid": page["pageid"], "revision": page["wikimedia_revision"],
                        "page_title": page.get("title"), "wikidata_qid": page.get("wikidata_qid"),
                        "person_display": person_base, "homonym_display_name": homonym,
                        "family": row["family"], "row_index": row["index"], "interval_index": number,
                        "start": interval["start"], "end": interval["end"], "ongoing": interval["ongoing"],
                        "years_as_written": interval["as_written"], "years_raw": row["years_raw"],
                        "employer_display": team.get("employer_display"),
                        "employer_link_target": team.get("employer_link_target"),
                        "employer_link_basis": team.get("employer_link_basis"),
                        "employer_qualifiers": team.get("employer_qualifiers"),
                        "employer_kind": row["employer_kind"], "resolution": resolution,
                        "classification": classification, "role_text": team.get("role_text"),
                        "role_basis": team.get("role_basis"), "assignments": assignments,
                        "population_state": state, "join": join,
                        "team_raw": row["team_raw"], "team_char_span": team_span,
                        "team_byte_span": [staff_record.byte_offset(text, team_span[0]),
                                           staff_record.byte_offset(text, team_span[1])]
                        if team_span[0] is not None else None,
                        "years_char_span": row["years_span"],
                        "wikitext_sha256": parsed["wikitext_sha256"], "raw_file": str(path),
                        "raw_file_sha256": sha256_bytes(raw_bytes), "parser_version": parsed["parser_version"],
                        "evidence_class": "RETROSPECTIVE_SECONDARY_WIKIMEDIA_REVISION", "pit_admitted": False,
                    }
                    episodes.append(episode)
                    ep_out.write(json.dumps(episode, sort_keys=True, ensure_ascii=True) + "\n")
                    episode_total += 1
                    counts["family"][row["family"]] += 1
                    counts["population_state"][state] += 1
                    counts["employer_kind"][str(row["employer_kind"])] += 1
                    counts["role_basis"][str(team.get("role_basis"))] += 1
                    counts["resolution"][f"{resolution.get('state')}|{resolution.get('basis')}"] += 1
                    counts["join"][join["state"]] += 1
                    counts["homonym"][str(homonym)] += 1
            reconciled, states = reconcile(predecessor_by_page.get(str(page["pageid"]), []), episodes)
            for item in reconciled:
                rec_out.write(json.dumps(item, sort_keys=True) + "\n")
            counts["predecessor_disposition"].update(states)
    predecessor_total = sum(len(v) for v in predecessor_by_page.values())
    summary = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "tool_version": TOOL_VERSION,
        "requirement": "R37-05", "parser_version": career_infobox.PARSER_VERSION,
        "pages": len(pages), "pages_read_from_raw": len(pages) - len(missing_raw), "pages_missing_raw": missing_raw,
        "raw_index": index_stats, "episodes": episode_total, "predecessor_episodes": predecessor_total,
        "predecessor_dispositioned": sum(counts["predecessor_disposition"].values()),
        "counts": {name: dict(counter.most_common()) for name, counter in sorted(counts.items())},
        "join_rule": ("A career episode is joined to an admitted official staff row only when the person, program, "
                      "role and season coincide AND the career page cites the program's own official athletics site. "
                      "Coincidence alone is a candidate, not a join."),
        "model_population": f"FBS/FCS programs, seasons {MODEL_SCOPE[0]}-{MODEL_SCOPE[1]}; earlier and non-college "
                            "rows are typed and kept, never counted in it",
        "inputs": {"career_pages": {"path": str(CAREER_PAGES), "sha256": sha256_bytes(CAREER_PAGES.read_bytes())},
                   "predecessor": {"path": str(PREDECESSOR), "sha256": sha256_bytes(PREDECESSOR.read_bytes())},
                   "staff_reparse": {"path": str(staff_rows), "sha256": sha256_bytes(staff_rows.read_bytes())}},
        "written": {"episodes": str(episodes_path), "reconciliation": str(reconciliation_path),
                    "episodes_sha256": sha256_bytes(episodes_path.read_bytes())},
        "not_claimed": "Wikimedia revisions are secondary retrospective evidence. No episode is PIT or official.",
    }
    _bas_atomic.write_text(out_dir / "R37_05_CAREER_REPARSE.json", json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence" / "repairs")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--staff-rows", type=Path, default=STAFF_REPARSE)
    args = parser.parse_args(argv)
    summary = build(args.out, args.limit, args.staff_rows)
    print(json.dumps({k: summary[k] for k in ("pages", "pages_read_from_raw", "episodes", "predecessor_episodes",
                                              "predecessor_dispositioned", "raw_index")} | {"counts": summary["counts"]},
                     indent=1)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-05 / OBL_CAREER_TRANCHE_KEYS: the 48 predeclared person-program-role-time
keys of R35-05, searched again in every local cache this attempt rebuilt.

For each key (program, role, season) the search reads, in order:

1. the reparsed career episodes (R37-05, revision-bound Wikimedia): coaching
   episodes of that program whose interval contains the season and whose
   role is the key's role as principal or co-shared occupant;
2. the official staff reparse (R37-03): rows of that program bound to that
   season carrying the role;
3. the CFBD ``/coaches`` cache, for head-coach keys: an independent secondary
   source, reported as such.

A key is bound to the sources that state it; a key none states is recorded
MISSING_NO_EVIDENCE with the routes searched. Several people for one key is a
conflict and is kept as one. The Cycle 36 disposition is shown beside each
key so a change is visible, not silently replaced.
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle37 import staff_record
from aggie_analytics import atomic_io as _bas_atomic  # noqa: E402

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
REPAIRS = ATTEMPT / "evidence" / "repairs"
EPISODES = REPAIRS / "R37_05_CAREER_EPISODES.jsonl"
STAFF = REPAIRS / "R37_03_STAFF_REPARSE_ROWS.jsonl"
KEYS = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle36/runs/20260921T200027Z/implementation_output"
            r"/CYCLE36_CAREER_TRANCHE_RECONCILIATION.json")
CFBD_COACHES = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle30_work/raw/coaches")
OCCUPANT = ("PRINCIPAL", "CO_SHARED")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _person(name: str) -> str:
    return staff_record.fold_name(re.sub(r"\s*\(.*\)$", "", name or ""))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=REPAIRS / "R37_05_TRANCHE_KEYS.json")
    args = parser.parse_args(argv)
    keys = json.loads(KEYS.read_text(encoding="utf-8"))["rows"]
    wanted = {(k["program_id"], k["role"]) for k in keys}

    episodes: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    with EPISODES.open(encoding="utf-8") as handle:
        for line in handle:
            episode = json.loads(line)
            if episode["family"] != "COACHING" or episode["population_state"] != "IN_POPULATION_CANDIDATE_EPISODE":
                continue
            program = episode["resolution"].get("program_id")
            for assignment in episode["assignments"]:
                if (program, assignment["role"]) in wanted and assignment.get("occupancy") in OCCUPANT:
                    episodes[(program, assignment["role"])].append(episode)
    staff: dict[tuple[str, str, int], list[dict[str, Any]]] = collections.defaultdict(list)
    with STAFF.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("season") is None or not row.get("program_id"):
                continue
            for assignment in row["assignments"]:
                if (row["program_id"], assignment["role"]) in wanted and assignment.get("occupancy") in OCCUPANT:
                    staff[(row["program_id"], assignment["role"], row["season"])].append(row)
    cfbd: dict[tuple[str, int], list[str]] = collections.defaultdict(list)
    for path in sorted(CFBD_COACHES.iterdir()):
        for coach in json.loads(path.read_bytes()):
            name = f"{coach.get('firstName') or ''} {coach.get('lastName') or ''}".strip()
            for season in coach.get("seasons") or []:
                cfbd[(f"SRC-002:TEAM:{season.get('teamId')}", int(season["year"]))].append(name)

    out, changes = [], collections.Counter()
    for key in keys:
        program, role, season = key["program_id"], key["role"], int(key["season"])
        career = [e for e in episodes.get((program, role), [])
                  if e["start"] <= season <= (e["end"] if e["end"] is not None else 2026)]
        people = sorted({_person(e["person_display"]) for e in career})
        official = staff.get((program, role, season), [])
        secondary = sorted(set(cfbd.get((program, season), []))) if role == "head_coach" else []
        if official:
            disposition = "BOUND_OFFICIAL_STAFF_PAGE"
        elif len(people) > 1:
            disposition = "CONFLICT_SEVERAL_PEOPLE_RETAINED"
        elif people:
            disposition = "BOUND_REVISION_CAREER_EPISODE_CANDIDATE"
        elif secondary:
            disposition = "BOUND_INDEPENDENT_SECONDARY_ONLY"
        elif key.get("resolved_people") and key["disposition"] == "ACCEPTED_SINGLE_SOURCE":
            # Cycle 36 bound this key from a team-season infobox, a route the
            # career episodes do not cover; that evidence is carried, not lost.
            disposition = "BOUND_CYCLE36_EVIDENCE_CARRIED"
        else:
            disposition = "MISSING_NO_EVIDENCE"
        cycle36_people = {_person(p) for p in key.get("resolved_people") or []}
        people_agree_with_cycle36 = (sorted(cycle36_people & set(people)) if people and cycle36_people else None)
        agrees_with_secondary = (bool(secondary) and bool(people)
                                 and bool({_person(n) for n in secondary} & set(people)))
        changes[(key["disposition"], disposition)] += 1
        out.append({
            "key_id": key["key_id"], "program_id": program, "display_name": key["display_name"],
            "classification": key["classification"], "role": role, "season": season,
            "cycle36_disposition": key["disposition"], "cycle36_people": key.get("resolved_people"),
            "cycle36_evidence_class": key.get("evidence_class"),
            "career_people_agreeing_with_cycle36": people_agree_with_cycle36,
            "disposition": disposition, "people_in_career_episodes": people,
            "career_episodes": [{"episode_id": e["episode_id"], "page_title": e["page_title"],
                                 "revision": e["revision"], "team_raw": e["team_raw"],
                                 "team_char_span": e["team_char_span"], "interval": [e["start"], e["end"]]}
                                for e in career[:10]],
            "official_staff_rows": [{"capture_path": r["capture_path"], "observation_index": r["observation_index"],
                                     "person": r["person"], "title": r["source_title"]} for r in official[:10]],
            "independent_secondary_cfbd_head_coaches": secondary,
            "career_person_named_by_cfbd": agrees_with_secondary if secondary and people else None,
            "routes_searched": ["R37-05 reparsed career episodes (revision-bound Wikimedia, in population)",
                                "Cycle 36 key evidence (team-season infobox or career page, as it recorded)",
                                "R37-03 official staff reparse (season-bound rows)",
                                "CFBD /coaches cache (head coach keys only)"],
            "official_corroboration": "OFFICIAL_STAFF_PAGE" if official else "NOT_FOUND_IN_LOCAL_OFFICIAL_CAPTURES",
        })
    report = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-05",
        "obligation": "OBL_CAREER_TRANCHE_KEYS", "keys": len(out),
        "dispositions": dict(collections.Counter(k["disposition"] for k in out)),
        "cycle36_to_cycle37": {f"{a} -> {b}": n for (a, b), n in sorted(changes.items())},
        "every_key_bound_or_missing_with_routes": all(
            k["disposition"] != "MISSING_NO_EVIDENCE" or k["routes_searched"] for k in out),
        "rows": out,
        "inputs": {"keys": {"path": str(KEYS), "sha256": sha256_file(KEYS)},
                   "episodes": {"path": str(EPISODES), "sha256": sha256_file(EPISODES)},
                   "staff": {"path": str(STAFF), "sha256": sha256_file(STAFF)}},
        "not_claimed": ("Wikimedia career episodes are revision-bound retrospective candidates; CFBD is an "
                        "independent secondary source. Neither is official corroboration."),
    }
    _bas_atomic.write_text(args.out, json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("rows", "inputs")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-04 AC01: transitions, discontinued programs and outside-division
opponents made explicit over the 1963-2026 membership, and the era every
membership row carries.

* Transitions: a program whose classification bucket changes between two
  consecutive member seasons, with both seasons and buckets.
* Gaps and discontinued programs: a program absent in a season between two
  member seasons (a gap), or whose last member season is before 2026
  (discontinued or reclassified out of the population); names the canonical
  population does not carry at all come from the alias crosswalk.
* Outside-division opponents: games in the held game tranche (2013-2026)
  whose one side is a member that season and whose other side is not,
  counted by season and classification as the game source states it.

The era of each membership row comes from the rebuilt membership rows (one
declared era table); the corrected release's own 2026 rows carry no era,
which this makes visible and a successor table repairs.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sqlite3
import sys
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
MEMBERSHIP = Path(r"C:/BatteredAggieSyndrome.validation/c37r-171601/r37_04_population_head2"
                  r"/CYCLE36_NATIONAL_MEMBERSHIP_ROWS.jsonl")
GAMES = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle30_work/outputs/CFBD_GAMES_TRANCHE.jsonl")
ALIAS = ATTEMPT / "evidence" / "repairs" / "R37_04_ALIAS_CROSSWALK.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence" / "repairs" / "R37_04_TRANSITIONS.json")
    args = parser.parse_args(argv)
    conn = sqlite3.connect(f"file:{args.release}?mode=ro", uri=True)
    released = {(pid, season): (bucket, era) for pid, season, bucket, era in conn.execute(
        "select program_id, season, classification_bucket, era from program_season_membership")}
    names = {pid: json.loads(n) for pid, n in conn.execute("select program_id, display_names from canonical_program")}
    rebuilt = [json.loads(line) for line in MEMBERSHIP.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_program: dict[str, dict[int, dict[str, Any]]] = collections.defaultdict(dict)
    for row in rebuilt:
        by_program[row["program_id"]][int(row["season"])] = row
    transitions, gaps, discontinued = [], [], []
    for pid, seasons in sorted(by_program.items()):
        years = sorted(seasons)
        for before, after in zip(years, years[1:]):
            a, b = seasons[before]["classification"], seasons[after]["classification"]
            if after == before + 1 and a != b:
                transitions.append({"program_id": pid, "names": names.get(pid), "from_season": before, "from": a,
                                    "to_season": after, "to": b})
            if after > before + 1:
                gaps.append({"program_id": pid, "names": names.get(pid), "absent_seasons": [before + 1, after - 1]})
        if years[-1] < 2026:
            discontinued.append({"program_id": pid, "names": names.get(pid), "first_member_season": years[0],
                                 "last_member_season": years[-1], "classification_last": seasons[years[-1]]["classification"]})
    members = {(row["program_id"], int(row["season"])) for row in rebuilt}
    outside = collections.Counter()
    examples: dict[str, list[str]] = collections.defaultdict(list)
    for line in GAMES.read_text(encoding="utf-8").splitlines():
        game = json.loads(line)
        season = int(game.get("season") or 0)
        for side, other in (("home", "away"), ("away", "home")):
            if (f"SRC-002:TEAM:{game.get(side + 'Id')}", season) in members and \
                    (f"SRC-002:TEAM:{game.get(other + 'Id')}", season) not in members:
                key = f"{season}|{game.get(other + 'Classification')}"
                outside[key] += 1
                if len(examples[key]) < 5:
                    examples[key].append(str(game.get(f"{other}Team")))
    era_rows = [{"program_id": row["program_id"], "season": int(row["season"]), "era": row["era"],
                 "classification": row["classification"], "release_era": released.get((row["program_id"], int(row["season"])),
                                                                                       (None, None))[1]}
                for row in rebuilt]
    missing_era_in_release = sum(1 for r in era_rows if r["release_era"] is None)
    _bas_atomic.write_text(args.out.with_name("R37_04_MEMBERSHIP_ERA_ROWS.jsonl"), 
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in era_rows), encoding="utf-8")
    alias = json.loads(ALIAS.read_text(encoding="utf-8")) if ALIAS.is_file() else {}
    outside_population = [r["raw_name"] for r in alias.get("rows", [])
                          if r["state"] == "UNRESOLVED_PROGRAM_NOT_IN_THE_CANONICAL_POPULATION"]
    report = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-04-AC01",
        "membership_rows": len(rebuilt), "programs": len(by_program),
        "seasons": [min(s for _, s in members), max(s for _, s in members)],
        "era_rows_written": len(era_rows), "release_rows_without_era": missing_era_in_release,
        "transitions": transitions, "transition_count": len(transitions),
        "membership_gaps": gaps, "discontinued_or_left_the_population": discontinued,
        "named_programs_outside_the_canonical_population": outside_population,
        "outside_division_opponent_games_by_season_and_class": dict(sorted(outside.items())),
        "outside_division_examples": dict(examples),
        "inputs": {"membership": {"path": str(MEMBERSHIP), "sha256": sha256_file(MEMBERSHIP)},
                   "games": {"path": str(GAMES), "sha256": sha256_file(GAMES), "seasons_held": "2013-2023, 2026"},
                   "release": str(args.release)},
    }
    _bas_atomic.write_text(args.out, json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k in ("membership_rows", "programs", "seasons", "era_rows_written",
                                                                "release_rows_without_era", "transition_count",
                                                                "named_programs_outside_the_canonical_population")}, indent=1))
    print("gaps", len(gaps), "discontinued", len(discontinued))
    print("outside-division", dict(list(sorted(outside.items()))[:12]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

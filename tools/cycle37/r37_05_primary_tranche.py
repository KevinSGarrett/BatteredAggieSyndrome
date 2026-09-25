"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R35-05 (carried as R37-04-CF-R35-05 and R37-05-CF-R35-05): the balanced
primary program-season tranche, built from evidence the release already holds.

R35-05 asks for at least 24 distinct program-seasons in a balanced
12-FBS / 12-FCS primary tranche, with at least four distinct seasons in each
original band (2000-2005, 2006-2012, 2013-2018, 2019-2023), including
transition and discontinued programs, plus a separate 2026 current slice. The
Cycle 35 sample reconciliation recorded that tranche as still required and
unsatisfied. Existing valid evidence counts and is not fetched again.

Selection is deterministic: the candidates in each band and division are
ordered by sha256 of a declared seed and the program-season, and three are
taken per band and division, on distinct seasons and distinct programs. If no
transition program-season or no discontinued program lands in the tranche,
the last pick of a band and division is replaced by the first candidate of
that kind in the same band and division, and the replacement is recorded.
Division and transitions are read from the release's own membership rows.

For each program-season, every head coach, offensive coordinator and
defensive coordinator stated by any layer is listed with its evidence class:
- OFFICIAL_SOURCE_SCOPED: a confirmed core cell and an admitted principal
  official staff assignment;
- SECONDARY_REVISION_BOUND: a career episode with a principal or co-shared
  role whose interval contains the season;
- USER_COMPILED: a user-corpus cell.
Where layers name different people, that is listed as a conflict. Nothing is
promoted: an appointment keeps the highest class its own evidence reaches.
The file imports nothing from aggie_analytics.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path
from typing import Any
class _bas_atomic:  # U37-11: atomic writes, self-contained -- this tool stays independent of aggie_analytics
    @staticmethod
    def _begin(path):
        import os as _bas_os
        import pathlib as _bas_pathlib
        import tempfile as _bas_tempfile

        target = path.resolve() if path.is_symlink() else path
        handle, name = _bas_tempfile.mkstemp(dir=str(target.parent), prefix="~", suffix="")
        _bas_os.close(handle)
        return target, _bas_pathlib.Path(name)

    @staticmethod
    def _finish(temporary, target):
        import os as _bas_os
        import stat as _bas_stat
        import time as _bas_time

        with open(temporary, "rb+") as stream:
            _bas_os.fsync(stream.fileno())
        try:
            mode = _bas_stat.S_IMODE(_bas_os.stat(target).st_mode)
        except FileNotFoundError:
            umask = _bas_os.umask(0)
            _bas_os.umask(umask)
            mode = 0o666 & ~umask
        _bas_os.chmod(temporary, mode)
        for attempt in range(6):
            try:
                _bas_os.replace(temporary, target)
                return
            except PermissionError:
                if attempt == 5:
                    raise
                _bas_time.sleep(0.05 * (attempt + 1))

    @classmethod
    def _call(cls, method, path, *args, **kwargs):
        import pathlib as _bas_pathlib

        if not isinstance(path, _bas_pathlib.Path):
            return getattr(path, method)(*args, **kwargs)
        target, temporary = cls._begin(path)
        try:
            written = getattr(temporary, method)(*args, **kwargs)
            cls._finish(temporary, target)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        return written

    @classmethod
    def write_text(cls, path, *args, **kwargs):
        return cls._call("write_text", path, *args, **kwargs)

    @classmethod
    def write_bytes(cls, path, *args, **kwargs):
        return cls._call("write_bytes", path, *args, **kwargs)

    @classmethod
    def open_write(cls, path, *args, **kwargs):
        import contextlib as _bas_contextlib
        import pathlib as _bas_pathlib

        @_bas_contextlib.contextmanager
        def _stream():
            if not isinstance(path, _bas_pathlib.Path):
                with path.open(*args, **kwargs) as stream:
                    yield stream
                return
            target, temporary = cls._begin(path)
            try:
                with temporary.open(*args, **kwargs) as stream:
                    yield stream
                cls._finish(temporary, target)
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise

        return _stream()

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
SEED = "R37-05-R35-05-PRIMARY-TRANCHE-v1"
BANDS = {"2000-2005": (2000, 2005), "2006-2012": (2006, 2012), "2013-2018": (2013, 2018), "2019-2023": (2019, 2023)}
PER_BAND_DIVISION = 3
CURRENT_SLICE = {"FBS": 2, "FCS": 2}
ROLES = {"head_coach": "Head Coach", "offensive_coordinator": "Offensive Coordinator",
         "defensive_coordinator": "Defensive Coordinator"}
PRINCIPAL = {"PRINCIPAL", "CO_SHARED"}


def fold(text: Any) -> str:
    value = unicodedata.normalize("NFKD", str(text or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).casefold()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def order(pid: str, season: int) -> str:
    return hashlib.sha256(f"{SEED}|{pid}|{season}".encode()).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence/repairs/R37_05_PRIMARY_TRANCHE.json")
    args = parser.parse_args(argv)
    before = sha256_file(args.release)
    c = sqlite3.connect(f"file:{args.release.as_posix()}?mode=ro&immutable=1", uri=True)
    membership = {(pid, int(s)): b for pid, s, b in c.execute(
        "SELECT program_id, season, classification_bucket FROM program_season_membership")}
    names = {pid: json.loads(d or "[]") for pid, d in c.execute("SELECT program_id, display_names FROM canonical_program")}
    seasons_of: dict[str, list[int]] = collections.defaultdict(list)
    for pid, season in membership:
        seasons_of[pid].append(season)
    last_season = {pid: max(s) for pid, s in seasons_of.items()}

    def transition(pid: str, season: int) -> bool:
        here = membership.get((pid, season))
        return any(membership.get((pid, season + d)) not in (None, here) for d in (-1, 1))

    def discontinued(pid: str) -> bool:
        return last_season[pid] < 2026

    # ---- selection ------------------------------------------------------------
    picks, substitutions = [], []
    for band, (lo, hi) in BANDS.items():
        used_seasons: set[int] = set()
        for division in ("FBS", "FCS"):
            pool = sorted(((pid, s) for (pid, s), b in membership.items() if b == division and lo <= s <= hi),
                          key=lambda k: order(*k))
            chosen: list[tuple[str, int]] = []
            # Seasons are distinct within a division; a season the band has
            # not used yet is preferred, so each band reaches four or more.
            for allow_band_repeat in (False, True):
                for pid, s in pool:
                    if len(chosen) == PER_BAND_DIVISION:
                        break
                    if (not allow_band_repeat and s in used_seasons) or any(y == s for _, y in chosen) \
                            or any(p == pid for p, _ in picks + chosen):
                        continue
                    chosen.append((pid, s))
            used_seasons.update(s for _, s in chosen)
            picks.extend((pid, s) for pid, s in chosen)
    for kind, test in (("TRANSITION", lambda k: transition(*k)), ("DISCONTINUED", lambda k: discontinued(k[0]))):
        if any(test(k) for k in picks):
            continue
        for index in range(len(picks) - 1, -1, -1):
            pid, s = picks[index]
            division = membership[(pid, s)]
            lo, hi = next(v for v in BANDS.values() if v[0] <= s <= v[1])
            replacement = next(((p, y) for (p, y), b in sorted(membership.items(), key=lambda kv: order(*kv[0]))
                                if b == division and y == s and test((p, y))
                                and all(p != q for q, _ in picks)), None)
            if replacement:
                substitutions.append({"kind": kind, "replaced": [pid, s], "by": list(replacement)})
                picks[index] = replacement
                break
    current_pool = sorted(((pid, s) for (pid, s), b in membership.items() if s == 2026), key=lambda k: order(*k))
    current = []
    for division, n in CURRENT_SLICE.items():
        current += [k for k in current_pool if membership[k] == division][:n]

    # ---- evidence -------------------------------------------------------------
    wanted = set(picks) | set(current)
    official: dict[tuple, set[str]] = collections.defaultdict(set)
    for pid, season, role, person in c.execute(
            "SELECT o.program_id, o.season, a.role_code, o.person FROM staff_observation o "
            "JOIN staff_role_assignment a ON a.observation_id = o.observation_id "
            "WHERE o.admitted_for_coverage = 1 AND a.occupancy IN ('PRINCIPAL', 'CO_SHARED') AND o.season IS NOT NULL"):
        if (pid, int(season)) in wanted and role in ROLES:
            official[(pid, int(season), role)].add(person)
    confirmed = {(pid, int(s), role) for pid, s, role, state in c.execute(
        "SELECT program_id, season, role_code, coverage_state FROM core_role_cell")
        if state == "CONFIRMED_SOURCE_SCOPED"}
    user: dict[tuple, set[str]] = collections.defaultdict(set)
    column_role = {v: k for k, v in ROLES.items()}
    for pid, season, column, person in c.execute(
            "SELECT canonical_program_id, season, role_column, person_as_written FROM user_corpus_cell "
            "WHERE canonical_program_id IS NOT NULL"):
        if (pid, int(season)) in wanted and column in column_role:
            user[(pid, int(season), column_role[column])].add(person)
    career: dict[tuple, set[str]] = collections.defaultdict(set)
    for person, start, end, resolution, assignments, state in c.execute(
            "SELECT person_display, start, \"end\", resolution, assignments, population_state "
            "FROM career_episode_successor WHERE family = 'COACHING'"):
        pid = (json.loads(resolution or "{}") or {}).get("program_id")
        if not pid or state != "IN_POPULATION_CANDIDATE_EPISODE" or start is None:
            continue
        for a in json.loads(assignments or "[]"):
            if a.get("role") in ROLES and a.get("occupancy") in PRINCIPAL:
                for season in range(int(start), int(end if end is not None else 2026) + 1):
                    if (pid, season) in wanted:
                        career[(pid, season, a["role"])].add(person)
    c.close()

    def cell(pid: str, season: int, role: str) -> dict[str, Any]:
        people: dict[str, dict[str, Any]] = {}
        layers = (("OFFICIAL_SOURCE_SCOPED", official.get((pid, season, role), set())
                   if (pid, season, role) in confirmed else set()),
                  ("SECONDARY_REVISION_BOUND", career.get((pid, season, role), set())),
                  ("USER_COMPILED", user.get((pid, season, role), set())))
        for layer, persons in layers:
            for person in persons:
                entry = people.setdefault(fold(person), {"person": person, "layers": []})
                entry["layers"].append(layer)
        for entry in people.values():
            entry["evidence_class"] = entry["layers"][0]
        distinct = {k for k in people}
        return {"role": role, "appointments": sorted(people.values(), key=lambda e: e["person"]),
                "layers_disagree_on_person": len(distinct) > 1,
                "best_evidence_class": min((e["evidence_class"] for e in people.values()),
                                           key=["OFFICIAL_SOURCE_SCOPED", "SECONDARY_REVISION_BOUND",
                                                "USER_COMPILED"].index, default="NO_EVIDENCE_IN_ANY_LAYER")}

    def row(pid: str, season: int) -> dict[str, Any]:
        return {"program_id": pid, "display_names": names.get(pid, [])[:3], "season": season,
                "division": membership[(pid, season)],
                "band": next((b for b, (lo, hi) in BANDS.items() if lo <= season <= hi), "2026_CURRENT"),
                "transition_program_season": transition(pid, season), "discontinued_program": discontinued(pid),
                "cells": [cell(pid, season, role) for role in ROLES]}

    tranche = [row(pid, s) for pid, s in picks]
    current_rows = [row(pid, s) for pid, s in current]
    checks = {
        "distinct_program_seasons": len({(r["program_id"], r["season"]) for r in tranche}),
        "fbs": sum(1 for r in tranche if r["division"] == "FBS"),
        "fcs": sum(1 for r in tranche if r["division"] == "FCS"),
        "distinct_seasons_by_band": {b: len({r["season"] for r in tranche if r["band"] == b}) for b in BANDS},
        "includes_transition": any(r["transition_program_season"] for r in tranche),
        "includes_discontinued_program": any(r["discontinued_program"] for r in tranche),
        "current_slice_is_separate_and_2026": bool(current_rows) and all(r["season"] == 2026 for r in current_rows),
    }
    checks["balanced_and_complete"] = (checks["distinct_program_seasons"] >= 24 and checks["fbs"] == 12
                                       and checks["fcs"] == 12
                                       and all(n >= 4 for n in checks["distinct_seasons_by_band"].values())
                                       and checks["includes_transition"] and checks["includes_discontinued_program"]
                                       and checks["current_slice_is_separate_and_2026"])
    classes = collections.Counter(cell_["best_evidence_class"] for r in tranche + current_rows for cell_ in r["cells"])
    report = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2,
        "requirements": ["R37-04-CF-R35-05", "R37-05-CF-R35-05"], "seed": SEED,
        "release": {"path": str(args.release), "sha256": before, "unchanged": sha256_file(args.release) == before},
        "checks": checks, "substitutions": substitutions,
        "cells_by_best_evidence_class": dict(classes),
        "cells_where_layers_disagree_on_person": sum(1 for r in tranche + current_rows for cell_ in r["cells"]
                                                     if cell_["layers_disagree_on_person"]),
        "primary_tranche": tranche, "current_2026_slice": current_rows,
        "rule": ("Existing evidence only, no request made. Nothing is promoted: an appointment keeps the class its "
                 "own evidence reaches, a disagreement between layers is listed, not resolved, and the tranche is "
                 "a sample, not the national career universe."),
        "independence": "Imports nothing from aggie_analytics; the release is opened read-only and immutable.",
    }
    _bas_atomic.write_text(args.out, json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("checks", "substitutions", "cells_by_best_evidence_class",
                                             "cells_where_layers_disagree_on_person")}, indent=1))
    return 0 if checks["balanced_and_complete"] else 1


if __name__ == "__main__":
    sys.exit(main())

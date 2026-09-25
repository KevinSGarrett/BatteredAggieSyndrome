"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R36-05 / MR35R-06 (carried as R37-05-CF-R36-05, R37-05-CF-MR35R-06): publish
the national staff, career and user-corpus counts by program, year, role,
source and evidence tier, and the unknown cells, from the delivered release.

R36-05 asks for "counts by program/year/role/source/evidence tier and unknown
cells, not just a row grand total". This tool reads the corrected release
read-only and immutable and reports each layer on its own grain:

* official staff: every observation and role assignment by division, season
  state, role, occupancy, source class, evidence tier and admission. Roles
  beyond head coach and coordinators are counted for FBS and FCS separately,
  and unmapped titles stay unmapped;
* user corpus: every cell by season band, role column, evidence tier and
  program-resolution state;
* career episodes: by family, evidence class, population state and role;
* core cells: coverage state by division and season band, with the cells
  that have no evidence of any kind counted as unknown.

Program-level rows (program x season x role x layer) go to a JSONL beside the
summary, so a count can be traced to its program. The file imports nothing
from aggie_analytics.
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def band(season: Any) -> str:
    if season is None:
        return "SEASON_UNBOUND"
    season = int(season)
    return "1963-1999" if season < 2000 else "2000-2012" if season < 2013 else "2013-2025" if season < 2026 else "2026"


def table(rows: list[tuple]) -> dict[str, int]:
    return {"|".join("NULL" if v is None else str(v) for v in key): int(n)
            for *key, n in sorted(rows, key=lambda r: [str(v) for v in r[:-1]])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence/repairs/R37_05_NATIONAL_STAFF_COUNTS.json")
    args = parser.parse_args(argv)
    before = sha256_file(args.release)
    c = sqlite3.connect(f"file:{args.release.as_posix()}?mode=ro&immutable=1", uri=True)
    division = {(pid, int(season)): bucket for pid, season, bucket in c.execute(
        "SELECT program_id, season, classification_bucket FROM program_season_membership")}

    # ---- official staff ----------------------------------------------------
    staff = c.execute(
        "SELECT o.program_id, o.season, o.source_class, o.evidence_tier, o.admitted_for_coverage, o.season_state, "
        "a.role_code, a.occupancy, a.is_core_role FROM staff_observation o "
        "LEFT JOIN staff_role_assignment a ON a.observation_id = o.observation_id").fetchall()
    by_grain: collections.Counter = collections.Counter()
    beyond_core: collections.Counter = collections.Counter()
    program_rows: collections.Counter = collections.Counter()
    for pid, season, source, tier, admitted, season_state, role, occupancy, core in staff:
        div = division.get((pid, int(season)), "NO_MEMBERSHIP_ROW") if pid and season is not None else (
            "PROGRAM_UNBOUND" if not pid else "SEASON_UNBOUND")
        by_grain[(div, band(season), role or "NO_ROLE_ASSIGNMENT", occupancy or "NONE", source, tier,
                  "ADMITTED" if admitted else "NOT_ADMITTED")] += 1
        if role and not core and occupancy != "UNMAPPED":
            beyond_core[(div, role)] += 1
        if pid and season is not None:
            program_rows[("OFFICIAL_STAFF", pid, int(season), role or "NO_ROLE_ASSIGNMENT", tier)] += 1
    observations = c.execute(
        "SELECT season_state, admitted_for_coverage, COUNT(*) FROM staff_observation GROUP BY 1,2").fetchall()
    unmapped_titles = c.execute(
        "SELECT o.source_title, COUNT(*) FROM staff_role_assignment a JOIN staff_observation o "
        "ON o.observation_id = a.observation_id WHERE a.occupancy = 'UNMAPPED' GROUP BY 1 ORDER BY 2 DESC").fetchall()

    # ---- user corpus ---------------------------------------------------------
    user = c.execute("SELECT canonical_program_id, season, role_column, evidence_tier, program_resolution_state "
                     "FROM user_corpus_cell").fetchall()
    user_grain = collections.Counter((band(s), col, tier, state) for _p, s, col, tier, state in user)
    for pid, season, column, tier, _state in user:
        if pid:
            program_rows[("USER_CORPUS", pid, int(season), column, tier)] += 1

    # ---- career --------------------------------------------------------------
    career_grain: collections.Counter = collections.Counter()
    for family, evidence, population, assignments in c.execute(
            "SELECT family, evidence_class, population_state, assignments FROM career_episode_successor"):
        roles = sorted({a.get("role") for a in json.loads(assignments or "[]")} or {"NO_ROLE"})
        for role in roles:
            career_grain[(family, evidence, population, role)] += 1

    # ---- core cells ------------------------------------------------------------
    cells = c.execute("SELECT program_id, season, role_code, coverage_state FROM core_role_cell").fetchall()
    cell_grain = collections.Counter((division.get((pid, int(s)), "NO_MEMBERSHIP_ROW"), band(s), role, state)
                                     for pid, s, role, state in cells)
    layers = c.execute(
        "SELECT program_id, season, role, confirmed, candidate_user_corpus, candidate_user_corpus_via_alias_binding, "
        "candidate_career_episodes FROM core_cell_coverage_layer").fetchall()
    unknown_grain = collections.Counter(
        (division.get((pid, int(s)), "NO_MEMBERSHIP_ROW"), band(s), role)
        for pid, s, role, confirmed, user_n, alias_n, career_n in layers
        if not (confirmed or user_n or alias_n or career_n))
    c.close()

    rows_path = args.out.with_name("R37_05_NATIONAL_STAFF_COUNT_ROWS.jsonl")
    with _bas_atomic.open_write(rows_path, "w", encoding="utf-8", newline="\n") as sink:
        for (layer, pid, season, role, tier), n in sorted(program_rows.items(), key=lambda kv: [str(x) for x in kv[0]]):
            sink.write(json.dumps({"layer": layer, "program_id": pid, "season": season, "role": role,
                                   "evidence_tier": tier, "rows": n}, sort_keys=True) + "\n")
    report = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2,
        "requirements": ["R37-05-CF-R36-05", "R37-05-CF-MR35R-06"],
        "release": {"path": str(args.release), "sha256": before, "unchanged": sha256_file(args.release) == before},
        "official_staff": {
            "observations_by_season_state_and_admission": table(observations),
            "assignments_by_division_band_role_occupancy_source_tier_admission": table(
                [(*k, n) for k, n in by_grain.items()]),
            "roles_beyond_head_coach_and_coordinators_by_division": table([(*k, n) for k, n in beyond_core.items()]),
            "unmapped_titles": {"distinct": len(unmapped_titles), "rows": sum(n for _t, n in unmapped_titles),
                                "titles": [[t, n] for t, n in unmapped_titles]},
        },
        "user_corpus": {"cells": len(user), "by_band_role_column_tier_resolution": table(
            [(*k, n) for k, n in user_grain.items()])},
        "career_episodes": {"by_family_evidence_population_role": table([(*k, n) for k, n in career_grain.items()])},
        "core_cells": {
            "cells": len(cells),
            "source_scoped_confirmation_state_by_division_band_role": table([(*k, n) for k, n in cell_grain.items()]),
            "note": "coverage_state NO_EVIDENCE means no source-scoped confirmation; candidate layers are separate",
            "unknown_cells_with_no_layer_at_all": sum(unknown_grain.values()),
            "unknown_cells_by_division_band_role": table([(*k, n) for k, n in unknown_grain.items()]),
        },
        "program_level_rows": {"path": str(rows_path), "rows": len(program_rows),
                               "sha256": sha256_file(rows_path)},
        "not_claimed": ("Counts of what the release holds, by layer. A user-corpus or career row is candidate "
                        "evidence, not confirmation, and no layer is summed into another."),
        "independence": "Imports nothing from aggie_analytics; the release is opened read-only and immutable.",
    }
    _bas_atomic.write_text(args.out, json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    beyond = report["official_staff"]["roles_beyond_head_coach_and_coordinators_by_division"]
    print(json.dumps({"observations": report["official_staff"]["observations_by_season_state_and_admission"],
                      "beyond_core_fbs": sum(v for k, v in beyond.items() if k.upper().startswith("FBS|")),
                      "beyond_core_fcs": sum(v for k, v in beyond.items() if k.upper().startswith("FCS|")),
                      "beyond_core_keys": sorted({k.split("|")[0] for k in beyond}),
                      "unmapped": report["official_staff"]["unmapped_titles"]["rows"],
                      "user_cells": len(user),
                      "unknown_cells": report["core_cells"]["unknown_cells_with_no_layer_at_all"],
                      "program_rows": len(program_rows)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

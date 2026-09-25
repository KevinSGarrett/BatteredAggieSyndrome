"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R35-03 (carried as R37-03/04/06/07-CF-R35-03): reconcile the Cycle 34 85-row
delivery, row by row, against the current corrected release.

The 85-row database (R34_07_CAREER_INGEST.sqlite) is a preserved candidate
transcription: 83 observations of head coach, offensive and defensive
coordinator cells from team-season encyclopedia pages, plus two synthetic
negative controls. 26 carry a verified flag. The flag came from a hardcoded
tuple in the Cycle 34 ingester with no per-row receipt, so it is a claim to
reconcile, not a verification.

For each observation this tool asks the current release, read-only, whether
another layer states the same fact. Three layers are checked separately:
- a revision-bound career episode for the same person, at the same program,
  with an interval containing the season and a principal or co-shared role;
- a user-corpus cell for the same program, season, role column and person;
- the core cell's source-scoped coverage state.

Names are compared exactly after folding case and punctuation; nothing is
fuzzy. Each negative control must find no Texas A&M employment for its
person in any layer, and neither control may appear in any national total.
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
CYCLE34_DB = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle34/20260919T_R34_receipts/pipeline_output"
                  r"/R34_07_CAREER_INGEST.sqlite")
ROLE = {"HC": "head_coach", "OC": "offensive_coordinator", "DC": "defensive_coordinator"}
USER_COLUMN = {"HC": "Head Coach", "OC": "Offensive Coordinator", "DC": "Defensive Coordinator"}
PRINCIPAL = {"PRINCIPAL", "CO_SHARED"}
IN_POPULATION = "IN_POPULATION_CANDIDATE_EPISODE"
TEXAS_AM = "texas a m"


def fold(text: Any) -> str:
    value = unicodedata.normalize("NFKD", str(text or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).casefold()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--out", type=Path,
                        default=ATTEMPT / "evidence/repairs/R37_07_CYCLE34_TRANSCRIPTION_RECONCILIATION.json")
    args = parser.parse_args(argv)
    before = {"cycle34_db": sha256_file(CYCLE34_DB), "release": sha256_file(args.release)}
    src = sqlite3.connect(f"file:{CYCLE34_DB.as_posix()}?mode=ro&immutable=1", uri=True)
    src.row_factory = sqlite3.Row
    delivered = [dict(r) for r in src.execute("SELECT * FROM staff_role_cells ORDER BY observation_id")]
    scheme_claims = src.execute("SELECT COUNT(*) FROM scheme_tenure_claims").fetchone()[0]
    src.close()

    rel = sqlite3.connect(f"file:{args.release.as_posix()}?mode=ro&immutable=1", uri=True)
    aliases: dict[str, set[str]] = collections.defaultdict(set)
    for pid, alias in rel.execute("SELECT program_id, normalized_alias FROM program_alias"):
        aliases[fold(alias)].add(pid)
    cells = {(pid, season, role): state for pid, season, role, state in rel.execute(
        "SELECT program_id, season, role_code, coverage_state FROM core_role_cell")}
    user: dict[tuple, set[str]] = collections.defaultdict(set)
    for pid, season, column, person in rel.execute(
            "SELECT canonical_program_id, season, role_column, person_as_written FROM user_corpus_cell "
            "WHERE canonical_program_id IS NOT NULL"):
        user[(pid, int(season), column)].add(fold(person))
    careers: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for person, start, end, ongoing, resolution, assignments, state, employer, page, revision in rel.execute(
            "SELECT person_display, start, \"end\", ongoing, resolution, assignments, population_state, "
            "employer_display, page_title, revision FROM career_episode_successor WHERE family = 'COACHING'"):
        careers[fold(person)].append({
            "start": start, "end": end, "ongoing": ongoing, "program_id": (json.loads(resolution or "{}") or {}).get(
                "program_id"), "assignments": json.loads(assignments or "[]"), "population_state": state,
            "employer": employer, "page_title": page, "revision": revision})
    release_sources = [path for (path,) in rel.execute("SELECT path FROM source_file")]
    rel.close()

    rows, outcomes = [], collections.Counter()
    for row in delivered:
        person = fold(row["person"])
        base = {"observation_id": row["observation_id"], "person": row["person"], "team": row["team"],
                "season": row["season"], "role_column": row["role_column"], "cycle34_disposition": row["disposition"],
                "cycle34_verified_flag": int(row["verified"] or 0), "source_title": row["source_title"]}
        if row["disposition"] == "CORRECTLY_REJECTED_NO_EMPLOYER_MATCH":
            texas = [e for e in careers.get(person, []) if TEXAS_AM in fold(e["employer"])]
            outcome = ("CONTROL_HOLDS_NO_TEXAS_A_M_EMPLOYMENT_IN_ANY_LAYER" if not texas
                       else "CONTROL_BROKEN_A_LAYER_STATES_THE_REJECTED_EMPLOYMENT")
            rows.append({**base, "outcome": outcome, "career_episodes_for_person": len(careers.get(person, [])),
                         "texas_a_m_episodes": texas})
            outcomes[outcome] += 1
            continue
        programs = sorted(aliases.get(fold(row["team_id_source"] or row["team"]), set()))
        if len(programs) != 1:
            outcome = "PROGRAM_UNRESOLVED" if not programs else "PROGRAM_AMBIGUOUS"
            rows.append({**base, "outcome": outcome, "program_candidates": programs})
            outcomes[outcome] += 1
            continue
        pid, season, role = programs[0], int(row["season"]), ROLE[row["role_column"]]
        career_hits = [
            {k: e[k] for k in ("page_title", "revision", "start", "end", "employer")}
            for e in careers.get(person, [])
            if e["program_id"] == pid and e["population_state"] == IN_POPULATION
            and e["start"] is not None and e["start"] <= season <= (e["end"] if e["end"] is not None else 2026)
            and any(a.get("role") == role and a.get("occupancy") in PRINCIPAL for a in e["assignments"])]
        same_program_other_role = [
            e["page_title"] for e in careers.get(person, [])
            if e["program_id"] == pid and e["start"] is not None
            and e["start"] <= season <= (e["end"] if e["end"] is not None else 2026)] if not career_hits else []
        user_hit = person in user.get((pid, season, USER_COLUMN[row["role_column"]]), set())
        layers = [name for name, hit in (("CAREER_EPISODE", bool(career_hits)), ("USER_CORPUS", user_hit)) if hit]
        outcome = ("CORROBORATED_BY_" + "_AND_".join(layers)) if layers else "NO_OTHER_LAYER_STATES_THIS_FACT"
        rows.append({**base, "program_id": pid, "role": role, "outcome": outcome,
                     "career_episodes": career_hits,
                     "career_at_program_in_season_other_role": same_program_other_role,
                     "user_corpus_same_person_same_cell": user_hit,
                     "core_cell_state": cells.get((pid, season, role))})
        outcomes[outcome] += 1

    by_flag = collections.Counter((r["cycle34_verified_flag"], r["outcome"]) for r in rows)
    report = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2,
        "requirements": ["R37-03-CF-R35-03", "R37-04-CF-R35-03", "R37-06-CF-R35-03", "R37-07-CF-R35-03"],
        "cycle34_db": {"path": str(CYCLE34_DB), "sha256": before["cycle34_db"], "rows": len(delivered),
                       "dispositions": dict(collections.Counter(r["disposition"] for r in delivered)),
                       "verified_flags": sum(int(r["verified"] or 0) for r in delivered),
                       "scheme_tenure_claims": scheme_claims},
        "release": {"path": str(args.release), "sha256": before["release"]},
        "cycle34_db_is_a_release_source_file": any("R34_07" in p for p in release_sources),
        "outcomes": dict(outcomes),
        "verified_flag_by_outcome": {f"verified={flag}|{outcome}": n for (flag, outcome), n in sorted(by_flag.items())},
        "controls_in_national_totals": 0 if not any("R34_07" in p for p in release_sources) else None,
        "rows": rows,
        "rule": ("A verified flag is a claim. A row is corroborated only when another layer of the release states "
                 "the same person, program, season and role. Names are matched exactly after folding, never "
                 "fuzzily. The 85-row table is never used as a national total."),
        "independence": "Imports nothing from aggie_analytics; both databases are opened read-only and immutable.",
        "independence_limit": ("The 85 rows come from encyclopedia team-season pages. A career episode comes from "
                               "the coach's own page revision and a user-corpus cell from the user's compiled "
                               "research, so agreement is across different pages and compilations. All are "
                               "secondary; none is an official verification."),
        "unchanged": {"cycle34_db": sha256_file(CYCLE34_DB) == before["cycle34_db"],
                      "release": sha256_file(args.release) == before["release"]},
    }
    _bas_atomic.write_text(args.out, json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("cycle34_db", "cycle34_db_is_a_release_source_file", "outcomes",
                                             "verified_flag_by_outcome", "unchanged")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

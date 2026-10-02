"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-04 / OBL_MEMBERSHIP_OFFICIAL_CORROBORATION: the 2026 FBS and FCS
membership rows compared with the NCAA's own standings pages.

NCAA.com publishes one FBS and one FCS standings page for the current
season, each team with its conference and its NCAA school slug (in its logo
address). A team's slug is joined to the canonical program through the
participant bindings the Cycle 35 replay made from NCAA scoreboard bytes
(slug -> canonical team id), never by name similarity. Each 2026 membership
row ends CORROBORATED, DIVISION_DISAGREES, NOT_ON_THE_NCAA_PAGE or its team
has NO_SLUG_BINDING; each NCAA team without a membership row is listed too.

The pages state only the current season, so they corroborate 2026, not 2024
or 2025. The file imports nothing from aggie_analytics.
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
METADATA = ATTEMPT / "private" / "acquisition" / "metadata"
BINDINGS = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle35/runs/20260920T172801Z/implementation_output"
                r"/R35_07_BOUND_OBSERVATIONS.jsonl")
PAGES = {"fbs": "b057f7617d3a", "fcs": "c6a5ad4c9659"}


def standings(prefix: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = next(p for p in METADATA.iterdir() if p.name.startswith(prefix) and p.suffix == ".bin")
    page = path.read_bytes().decode("utf-8", "replace")
    season = re.search(r'seasonYear"?\s*:\s*(\d{4})', page)
    teams = []
    for block in re.finditer(r'standings-conference"><img[^>]*>([^<]+)</figure>(.*?)(?=standings-conference"|$)', page, re.S):
        conference = html.unescape(block.group(1)).strip()
        for cell in re.finditer(r'<td class="standings-team"><img[^>]*src="[^"]*/([a-z0-9-]+)\.svg"[^>]*>([^<]+)</td>',
                                block.group(2)):
            teams.append({"slug": cell.group(1), "school": html.unescape(cell.group(2)).strip(), "conference": conference})
    return teams, {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "season_stated": int(season.group(1)) if season else None}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence" / "repairs" / "R37_04_OFFICIAL_MEMBERSHIP.json")
    args = parser.parse_args(argv)
    slug_to_program: dict[str, set[str]] = collections.defaultdict(set)
    for line in BINDINGS.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        for side in ("home", "away"):
            if row.get(f"{side}_seoname") and row.get(f"{side}_canonical_team_id"):
                slug_to_program[row[f"{side}_seoname"]].add(row[f"{side}_canonical_team_id"])
    official: dict[str, dict[str, Any]] = {}
    sources, unbound = {}, []
    for division, prefix in PAGES.items():
        teams, source = standings(prefix)
        sources[division] = {**source, "teams": len(teams)}
        for team in teams:
            programs = slug_to_program.get(team["slug"], set())
            if len(programs) != 1:
                unbound.append({**team, "division": division, "candidates": sorted(programs)})
                continue
            official[next(iter(programs))] = {**team, "division": division}
    conn = sqlite3.connect(f"file:{args.release}?mode=ro", uri=True)
    rows, states = [], collections.Counter()
    members = set()
    for pid, classification, conference in conn.execute(
            "select program_id, classification, conference from program_season_membership where season = 2026"):
        members.add(pid)
        ncaa = official.get(pid)
        if ncaa is None:
            state = "NOT_ON_THE_NCAA_PAGE_OR_NO_SLUG_BINDING"
        elif ncaa["division"] == str(classification).lower():
            state = "CORROBORATED"
        else:
            state = "DIVISION_DISAGREES"
        states[state] += 1
        rows.append({"program_id": pid, "membership_classification": classification, "membership_conference": conference,
                     "ncaa": ncaa, "state": state})
    extra = [{"program_id": pid, **team} for pid, team in official.items() if pid not in members]
    report = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-04",
        "obligation": "OBL_MEMBERSHIP_OFFICIAL_CORROBORATION", "season": 2026, "sources": sources,
        "membership_rows_2026": len(rows), "states": dict(states),
        "ncaa_teams_without_a_slug_binding": unbound, "ncaa_teams_without_a_2026_membership_row": extra,
        "rows": rows, "join": "NCAA school slug -> canonical team id from the Cycle 35 NCAA scoreboard bindings",
        "not_covered": "2024 and 2025: the NCAA standings route serves the current season only",
        "independence": "Imports nothing from aggie_analytics.",
    }
    _bas_atomic.write_text(args.out.with_name("R37_04_OFFICIAL_MEMBERSHIP_ROWS.jsonl"), 
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    _bas_atomic.write_text(args.out, json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k in ("sources", "membership_rows_2026", "states")}, indent=1))
    print("unbound NCAA teams:", [(u["school"], u["candidates"]) for u in unbound][:20])
    print("NCAA teams without membership:", [(e["school"], e["division"]) for e in extra])
    for r in rows:
        if r["state"] != "CORROBORATED":
            print("  ", r["program_id"], r["membership_classification"], r["state"], (r["ncaa"] or {}).get("school"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-10 AC04/AC05/AC08: an independent reconstruction of the official-final
population, the declared tie and correction rules applied to it, and the
present calendar with its real upcoming cutoffs.

Independence. This file imports nothing from aggie_analytics. It reads the raw
NCAA.com scoreboard bytes itself -- the eight captures Cycle 35 bound and the
five read this attempt -- decoding each page's embedded contest array with the
standard JSON decoder, not the producer's parser.

Vintage. Every observation is kept. For a contest seen in several captures,
the latest capture states its current status; an earlier FINAL whose score a
later capture states differently is a CORRECTION, recorded with both values,
never silently overwritten. A contest that was pregame in an early capture
and final in a later one is simply later news.

Ties and corrections (the declared policy, POLICY below). College football has
resolved regulation ties by overtime since 1996, so a terminal tie is
possible only in an unusual or truncated game; one is scored with the
outcome 0.5 and flagged, not treated as a home loss. A scored row is
immutable: a later correction is scored as a new row superseding it, and the
original row is kept.

Calendar. The present calendar and each upcoming contest's T-24H and T-90M
cutoffs come from the newest captures. Nothing is armed or scheduled here;
the historical Week 1/2 jobs are not re-armed.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
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
RAW = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle30_work/raw/ncaa")
ACQUIRED = ATTEMPT / "private" / "acquisition" / "games"
PRODUCER_ROWS = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle35/runs/20260920T172801Z/implementation_output"
                     r"/R35_07_BOUND_OBSERVATIONS.jsonl")
POLICY = {
    "version": "BAS-SCORING-POLICY-v37.1",
    "tie": ("A terminal final with equal scores is a tie: outcome 0.5 for a probability of the designated home "
            "side, flagged tie=true. It is neither a home win nor a home loss."),
    "correction": ("A scored row is immutable. When a later official observation states a different final for a "
                   "contest already scored, the correction is admitted as a new scoring row that supersedes the "
                   "original by reference; the original row and its score remain."),
    "non_final": "Pregame, in-progress, postponed and cancelled contests are never scored.",
    "denominator": "One contest is one game-grain unit; oriented rows are derived from it, never counted twice.",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contests(page: str) -> list[dict[str, Any]]:
    """The page's embedded contest array, decoded structurally."""

    start = page.find('"initialGames":')
    if start < 0:
        return []
    bracket = page.find("[", start)
    value, _ = json.JSONDecoder().raw_decode(page, bracket)
    return value


def captures() -> list[dict[str, Any]]:
    found = []
    for path in sorted(RAW.glob("scoreboard-*.html")):
        division = "fcs" if "-fcs-" in path.name else "fbs"
        week = path.stem.rsplit("-", 1)[-1]
        found.append({"path": path, "division": division, "week": week, "vintage": "CYCLE30_CACHE",
                      "retrieved": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()})
    for meta_path in sorted(ACQUIRED.glob("*.meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if "ncaa.com/scoreboard" not in str(meta.get("url")) or not meta.get("stored"):
            continue
        parts = str(meta["url"]).rstrip("/").split("/")
        found.append({"path": Path(meta["stored"]), "division": parts[-4], "week": parts[-2],
                      "vintage": "ACQUIRED_THIS_ATTEMPT", "retrieved": meta["requested_at_utc"]})
    return found


def score(team: dict[str, Any]) -> int | None:
    value = team.get("score")
    if isinstance(value, bool):
        return None
    try:
        return int(str(value)) if str(value).strip() not in ("", "None") else None
    except ValueError:
        return None


def observation(game: dict[str, Any], capture: dict[str, Any]) -> dict[str, Any]:
    teams = game.get("teams") or []
    home = next((t for t in teams if t.get("isHome") is True), None)
    away = next((t for t in teams if t.get("isHome") is False), None)
    state = str(game.get("gameState") or "").upper()
    display = str(game.get("statusCodeDisplay") or "").lower()
    return {"contest_id": str(game.get("contestId")), "division_page": capture["division"], "week": capture["week"],
            "vintage": capture["vintage"], "retrieved": capture["retrieved"], "capture_sha256": capture["sha256"],
            "state": state, "status_display": display, "start_epoch": game.get("startTimeEpoch"),
            "start_date": game.get("startDate"), "home": (home or {}).get("seoname"), "away": (away or {}).get("seoname"),
            "home_points": score(home or {}), "away_points": score(away or {}),
            "home_winner_flag": (home or {}).get("isWinner"), "away_winner_flag": (away or {}).get("isWinner"),
            "teams_bound": home is not None and away is not None}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence" / "repairs" / "R37_10_FINALS_RECONSTRUCTION.json")
    parser.add_argument("--now", default=None, help="the present instant (UTC ISO); default: the newest capture's")
    args = parser.parse_args(argv)
    rows, inputs = [], []
    for capture in captures():
        data = capture["path"].read_bytes()
        capture["sha256"] = hashlib.sha256(data).hexdigest()
        games = contests(data.decode("utf-8", "replace"))
        inputs.append({"path": str(capture["path"]), "sha256": capture["sha256"], "division": capture["division"],
                       "week": capture["week"], "vintage": capture["vintage"], "retrieved": capture["retrieved"],
                       "contests": len(games)})
        rows.extend(observation(game, capture) for game in games)
    by_contest: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        by_contest[row["contest_id"]].append(row)
    finals, corrections, contradictions, ties, current_states = {}, [], [], [], collections.Counter()
    for contest, observed in by_contest.items():
        observed.sort(key=lambda r: r["retrieved"])
        latest = observed[-1]
        current_states[latest["state"] or "UNKNOWN"] += 1
        final_rows = [r for r in observed if r["state"] == "F" and r["home_points"] is not None
                      and r["away_points"] is not None]
        scores = []
        for row in final_rows:
            pair = (row["home_points"], row["away_points"])
            if not scores or scores[-1] != pair:
                scores.append(pair)
        if len(scores) > 1:
            corrections.append({"contest_id": contest, "finals_in_vintage_order": scores})
        if final_rows:
            last = final_rows[-1]
            home_won = last["home_points"] > last["away_points"]
            flagged = last["home_winner_flag"] is True and not home_won and last["home_points"] != last["away_points"]
            if flagged or (last["away_winner_flag"] is True and home_won):
                contradictions.append({"contest_id": contest, "score": [last["home_points"], last["away_points"]],
                                       "winner_flags": [last["home_winner_flag"], last["away_winner_flag"]]})
            if last["home_points"] == last["away_points"]:
                ties.append(contest)
            finals[contest] = {"home": last["home"], "away": last["away"], "home_points": last["home_points"],
                               "away_points": last["away_points"], "outcome_for_home":
                               0.5 if last["home_points"] == last["away_points"] else float(home_won),
                               "vintage": last["vintage"]}
    newest = max(i["retrieved"] for i in inputs)
    now = datetime.fromisoformat((args.now or newest).replace("Z", "+00:00"))
    upcoming = []
    for contest, observed in by_contest.items():
        latest = observed[-1]
        if latest["state"] != "P" or not latest["start_epoch"]:
            continue
        kickoff = datetime.fromtimestamp(int(latest["start_epoch"]), timezone.utc)
        if kickoff <= now:
            continue
        upcoming.append({"contest_id": contest, "home": latest["home"], "away": latest["away"],
                         "kickoff_utc": kickoff.isoformat(), "t_minus_24h": (kickoff - timedelta(hours=24)).isoformat(),
                         "t_minus_90m": (kickoff - timedelta(minutes=90)).isoformat(),
                         "t_minus_24h_already_passed": kickoff - timedelta(hours=24) <= now})
    upcoming.sort(key=lambda r: r["kickoff_utc"])
    producer = [json.loads(line) for line in PRODUCER_ROWS.read_text(encoding="utf-8").splitlines() if line.strip()]
    old_vintage = [r for r in rows if r["vintage"] == "CYCLE30_CACHE"]
    report = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-10",
        "rows": ["R37-10-AC04", "R37-10-AC05", "R37-10-AC08", "R37-10-AC09"],
        "independence": "Imports nothing from aggie_analytics; decodes the raw pages' embedded JSON itself.",
        "policy": POLICY, "inputs": inputs, "observations": len(rows), "distinct_contests": len(by_contest),
        "game_grain": {"contests": len(by_contest), "current_states": dict(current_states),
                       "contests_with_a_terminal_final": len(finals),
                       "never_scored_nonfinal": len(by_contest) - len(finals)},
        "corrections": corrections, "winner_flag_contradictions": contradictions, "ties": ties,
        "cycle35_vintage_check": {"independent_observations": len(old_vintage), "producer_observations": len(producer),
                                  "independent_contests": len({r["contest_id"] for r in old_vintage}),
                                  "producer_contests": len({str(r.get("ncaa_com_contest_id")) for r in producer}),
                                  "agree": len(old_vintage) == len(producer) and {r["contest_id"] for r in old_vintage}
                                  == {str(r.get("ncaa_com_contest_id")) for r in producer}},
        "scoring": {"eligible_forecasts": 0, "scored_rows": 0,
                    "reason": "no durable frozen forecast with a trusted receipt exists; zero stays zero and nothing "
                              "is created retroactively"},
        "calendar": {"now_utc": now.isoformat(), "now_basis": "argument" if args.now else "newest capture's retrieval",
                     "upcoming_contests": len(upcoming), "next": upcoming[:40],
                     "jobs_armed": [], "historical_week1_2_jobs_rearmed": False},
    }
    _bas_atomic.write_text(args.out, json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("inputs", "calendar", "policy")}, indent=1)[:2500])
    print("upcoming:", len(upcoming), upcoming[:2])
    return 0


if __name__ == "__main__":
    sys.exit(main())

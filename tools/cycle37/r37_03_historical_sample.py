"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-03 AC11, historical part: 20 raw records dated before 2026.

The official staff captures hold no record dated before 2026 (every bound
season in the reparse is 2026), so official staff history is not available
and this sample does not pretend otherwise. The historical raw records that
do exist are the career rows of cached encyclopedia revisions (retrospective
secondary evidence). ``draw`` takes 20 in-population coaching rows spread
across decades and role classes and writes, for each, only the revision's own
raw infobox lines around the row; ``compare`` reads blind labels written from
those lines and reports agreement on employer, role text, years and the
principal core roles.
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
EPISODES = ATTEMPT / "evidence" / "repairs" / "R37_05_CAREER_EPISODES.jsonl"
SEED = "R37-03-AC11-HISTORICAL"
CORE = ("head_coach", "offensive_coordinator", "defensive_coordinator")


def _rank(episode: dict[str, Any]) -> str:
    return hashlib.sha256(f"{SEED}|{episode['episode_id']}".encode()).hexdigest()


def _role_class(episode: dict[str, Any]) -> str:
    roles = {(a["role"], a.get("occupancy")) for a in episode["assignments"]}
    if any(role in CORE and occ in ("PRINCIPAL", "CO_SHARED") for role, occ in roles):
        return "CORE"
    return "OTHER"


def _wikitext(raw_file: str, revision: str) -> str:
    data = json.loads(Path(raw_file).read_text(encoding="utf-8"))
    pages = (data.get("query") or {}).get("pages") or {}
    for page in (pages.values() if isinstance(pages, dict) else pages):
        for rev in page.get("revisions") or []:
            if str(rev.get("revid")) == str(revision):
                return ((rev.get("slots") or {}).get("main") or {}).get("*") or ""
    raise KeyError(f"revision {revision} not in {raw_file}")


def draw(out_dir: Path) -> dict[str, Any]:
    pools: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    with EPISODES.open(encoding="utf-8") as handle:
        for line in handle:
            episode = json.loads(line)
            if (episode["population_state"] != "IN_POPULATION_CANDIDATE_EPISODE" or episode["family"] != "COACHING"
                    or episode.get("start") is None or episode["start"] >= 2026):
                continue
            decade = f"{episode['start'] // 10 * 10}s"
            pools[f"{decade}|{_role_class(episode)}"].append(episode)
    strata = sorted(pools)
    chosen: list[tuple[str, dict[str, Any]]] = []
    seen_pages: set[int] = set()
    ranked = {s: sorted(pools[s], key=_rank) for s in strata}
    while len(chosen) < 20 and any(ranked.values()):
        for stratum in strata:
            while ranked[stratum] and len(chosen) < 20:
                episode = ranked[stratum].pop(0)
                if episode["pageid"] in seen_pages:
                    continue
                seen_pages.add(episode["pageid"])
                chosen.append((stratum, episode))
                break
    blind = []
    for sample_id, (stratum, episode) in enumerate(chosen, start=1):
        text = _wikitext(episode["raw_file"], episode["revision"])
        start, end = episode["team_char_span"]
        assert text[start:end] == episode["team_raw"], episode["episode_id"]
        first = min(start, *(episode["years_char_span"] or [start]))
        line_start = text.rfind("\n", 0, first) + 1
        line_end = text.find("\n", end)
        before = text.rfind("\n", 0, max(0, line_start - 1))
        before = text.rfind("\n", 0, max(0, before - 1)) + 1
        after = text.find("\n", line_end + 1)
        after = text.find("\n", after + 1) if after >= 0 else -1
        blind.append({"sample_id": sample_id, "stratum": stratum, "page_title": episode["page_title"],
                      "raw_lines": text[before:after if after >= 0 else len(text)],
                      "row_lines": text[line_start:line_end if line_end >= 0 else len(text)],
                      "revision": episode["revision"], "raw_file_sha256": episode["raw_file_sha256"],
                      "key": {"episode_id": episode["episode_id"]}})
    out_dir.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out_dir / "R37_03_HISTORICAL_SAMPLE_BLIND.jsonl", 
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in blind), encoding="utf-8")
    manifest = {"label": LABEL, "cycle_number": 37, "attempt_number": 2, "seed": SEED, "sample_size": len(blind),
                "strata": dict(collections.Counter(s for s, _ in chosen)),
                "pool_sizes": {s: len(pools[s]) for s in strata},
                "official_staff_history": ("NOT_AVAILABLE: no official staff capture binds a season before 2026 "
                                           "(R37_03_STAFF_REPARSE_ROWS seasons: 2026 or unbound)"),
                "evidence_class": "RETROSPECTIVE_SECONDARY_WIKIMEDIA_REVISION",
                "episodes_file": str(EPISODES), "episodes_sha256": hashlib.sha256(EPISODES.read_bytes()).hexdigest(),
                "withheld_from_the_labeller": ["employer_display", "role_text", "start", "end", "assignments"]}
    _bas_atomic.write_text(out_dir / "R37_03_HISTORICAL_SAMPLE_MANIFEST.json", json.dumps(manifest, indent=2) + "\n",
                                                                    encoding="utf-8")
    return manifest


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def compare(blind_path: Path, labels_path: Path, out: Path, episodes_path: Path = EPISODES) -> dict[str, Any]:
    wanted = {json.loads(line)["key"]["episode_id"]: json.loads(line)["sample_id"]
              for line in blind_path.read_text(encoding="utf-8").splitlines()}
    episodes = {}
    with episodes_path.open(encoding="utf-8") as handle:
        for line in handle:
            episode = json.loads(line)
            if episode["episode_id"] in wanted:
                episodes[wanted[episode["episode_id"]]] = episode
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    fields, agree, disagreements = collections.Counter(), collections.Counter(), []
    for label in labels["labels"]:
        episode = episodes[label["sample_id"]]
        football = episode["population_state"] == "IN_POPULATION_CANDIDATE_EPISODE"
        # Core roles are football core roles: a head coach of another sport's
        # programme keeps that row's own assignment but holds no football role.
        core = sorted({a["role"] for a in episode["assignments"]
                       if football and a["role"] in CORE and a.get("occupancy") in ("PRINCIPAL", "CO_SHARED")})
        checks = {"employer": (_norm(label["employer"]), _norm(episode["employer_display"])),
                  "role_text": (_norm(label["role_text"]), _norm(episode["role_text"])),
                  "start": (label["start"], episode["start"]), "end": (label["end"], episode["end"]),
                  "football_coaching": (label["football_coaching"], football),
                  "principal_core_roles": (sorted(label["principal_core_roles"]), core)}
        for name, (expected, got) in checks.items():
            fields[name] += 1
            if expected == got:
                agree[name] += 1
            else:
                disagreements.append({"sample_id": label["sample_id"], "field": name, "label": expected,
                                      "reparse": got, "note": label.get("note")})
    report = {"label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-03-AC11",
              "sample": "HISTORICAL_RAW_CASES", "labelled": len(labels["labels"]),
              "agreement": {name: f"{agree[name]}/{fields[name]}" for name in fields},
              "disagreements": disagreements, "labeller": labels.get("labeller"),
              "independence_limit": labels.get("independence_limit"),
              "evidence_class": "RETROSPECTIVE_SECONDARY_WIKIMEDIA_REVISION",
              "episodes_file": str(episodes_path),
              "episodes_sha256": hashlib.sha256(episodes_path.read_bytes()).hexdigest(),
              "population_inference": "None; 20 records show where the parser is right or wrong on them."}
    _bas_atomic.write_text(out, json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("draw")
    d.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("compare")
    c.add_argument("--blind", type=Path, required=True)
    c.add_argument("--labels", type=Path, required=True)
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("--episodes", type=Path, default=EPISODES)
    args = parser.parse_args(argv)
    result = draw(args.out) if args.command == "draw" else compare(args.blind, args.labels, args.out, args.episodes)
    print(json.dumps({k: v for k, v in result.items() if k != "disagreements"}, indent=1)[:2500])
    return 0


if __name__ == "__main__":
    sys.exit(main())

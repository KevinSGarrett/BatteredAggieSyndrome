"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-03 AC11: a stratified raw-record sample of the staff reparse, labelled
blind, and the comparison of those labels with the reparse.

``draw`` selects at least 60 records across FBS/FCS (and unconfirmed
captures), principal/co/assistant/support roles and season-bound/unbound
cases, plus up to 20 records dated before 2026 where the cache has them. For
each it writes a blind file carrying only what a reader of the page would
see: an excerpt of the page's text around the record, the visible headings
above it, the page title and canonical address, and the record's byte
offset. The reparse's person, title, season, roles and sport are not in it.
The excerpt is made here with a plain tag strip that shares no code with the
parser under test.

``compare`` reads the labels written from that file and reports agreement
field by field. Every disagreement is listed. A sample this size does not
establish a population error rate, and the report says so.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import html
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
CYCLE36_CAPTURES = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle36/runs/20260921T200027Z/implementation_output"
                        r"/CYCLE36_STAFF_CAPTURE_INVENTORY.jsonl")
CROSSWALK_ROWS = ATTEMPT / "evidence" / "repairs" / "R37_03_SOURCE_IDENTITY_ROWS.jsonl"
SEED = "R37-03-AC11"
CORE = ("head_coach", "offensive_coordinator", "defensive_coordinator")
COACHING_ROLES = frozenset({
    "head_coach", "offensive_coordinator", "defensive_coordinator", "assistant_head_coach", "assistant_unspecified",
    "quarterbacks", "running_backs", "wide_receivers", "tight_ends", "offensive_line", "defensive_line",
    "defensive_ends", "defensive_tackles", "linebackers", "inside_linebackers", "outside_linebackers",
    "defensive_backs", "cornerbacks", "safeties", "special_teams_coordinator", "receivers", "edge", "nickels",
    "secondary", "run_game_coordinator", "pass_game_coordinator", "kickers_punters", "specialists", "halfbacks",
    "fullbacks", "slot_backs",
})
_TAG = re.compile(r"<[^>]*>")
_DROP = re.compile(r"<(script|style|noscript|template)\b.*?</\1\s*>", re.I | re.S)
_HEADING = re.compile(r"<h([1-6])\b[^>]*>(.*?)</h\1\s*>", re.I | re.S)


def plain(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", _DROP.sub(" ", fragment)))).strip()


def role_class(row: dict[str, Any]) -> str:
    assignments = row["assignments"]
    if any(a["role"] in CORE and a["occupancy"] == "PRINCIPAL" for a in assignments):
        return "PRINCIPAL_CORE"
    if any(a["role"] in CORE and a["occupancy"] == "CO_SHARED" for a in assignments):
        return "CO_SHARED_CORE"
    if any(a["role"] in COACHING_ROLES for a in assignments):
        return "ASSISTANT_OR_POSITION_COACH"
    return "SUPPORT_OR_NON_COACHING"


def rank(row: dict[str, Any], seed: str = SEED) -> str:
    return hashlib.sha256(f"{seed}|{row['capture_path']}|{row['observation_index']}".encode()).hexdigest()


def blind_record(row: dict[str, Any], sample_id: int, stratum: str) -> dict[str, Any]:
    path = Path(row["capture_path"])
    text = path.read_bytes().decode("utf-8", "surrogateescape")
    binding = row["binding"]
    offset = (binding.get("name_span") or {}).get("char_start") or binding.get("char_offset")
    if offset is None:
        excerpt, headings = None, []
    else:
        excerpt = plain(text[max(0, offset - 700):offset + 900])
        headings = [plain(m.group(2))[:120] for m in _HEADING.finditer(text, 0, offset)][-4:]
    title = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    return {"sample_id": sample_id, "stratum": stratum, "capture_path": str(path),
            "payload_sha256": row["payload_sha256"], "record_char_offset": offset,
            "record_byte_offset": (binding.get("name_span") or {}).get("byte_start") or binding.get("byte_offset"),
            "page_title": plain(title.group(1))[:200] if title else None,
            "page_canonical": (row.get("page_url") if str(row.get("page_url") or "").startswith("http") else None),
            "visible_headings_before_record": headings, "excerpt": excerpt,
            "key": {"capture_path": str(path), "observation_index": row["observation_index"]}}


def draw(rows_path: Path, out_dir: Path, *, seed: str = SEED, exclude: Path | None = None,
         stem: str = "R37_03_LABEL_SAMPLE") -> dict[str, Any]:
    """Draw the stratified sample.

    A held-out draw passes another ``seed`` and the blind file of an earlier
    sample as ``exclude``: none of its records can be drawn again, so rules
    tuned on the earlier sample are judged on records they were not tuned on.
    """

    excluded = set()
    if exclude is not None:
        for line in exclude.read_text(encoding="utf-8").splitlines():
            key = json.loads(line)["key"]
            excluded.add((key["capture_path"], key["observation_index"]))
    division = {}
    for line in CYCLE36_CAPTURES.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        division[record["capture_path"]] = ((record.get("declared_attempt") or {}).get("classification") or "").upper()
    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    pools: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    historical = []
    for row in rows:
        if (row["capture_path"], row["observation_index"]) in excluded:
            continue
        confirmed = row["identity_state"] == "CONFIRMED_BY_SOURCE_IDENTITY"
        group = (division.get(row["capture_path"]) or "UNKNOWN") if confirmed else "UNCONFIRMED_CAPTURE"
        season = "SEASON_BOUND" if row["season"] is not None else "SEASON_UNBOUND"
        pools[f"{group}|{role_class(row)}|{season}"].append(row)
        if row["season"] is not None and row["season"] < 2026:
            historical.append(row)
    quota = {"FBS": 3, "FCS": 3, "UNCONFIRMED_CAPTURE": 2}
    chosen: list[tuple[str, dict[str, Any]]] = []
    shortfall = {}
    for stratum in sorted(pools):
        group = stratum.split("|")[0]
        want = quota.get(group, 0)
        pool = sorted(pools[stratum], key=lambda row: rank(row, seed))
        chosen.extend((stratum, row) for row in pool[:want])
        if len(pool) < want:
            shortfall[stratum] = {"wanted": want, "available": len(pool)}
    wanted_strata = [f"{g}|{r}|{s}" for g in quota for r in ("PRINCIPAL_CORE", "CO_SHARED_CORE",
                                                                "ASSISTANT_OR_POSITION_COACH",
                                                                "SUPPORT_OR_NON_COACHING")
                     for s in ("SEASON_BOUND", "SEASON_UNBOUND")]
    for stratum in wanted_strata:
        if stratum not in pools:
            shortfall[stratum] = {"wanted": quota[stratum.split("|")[0]], "available": 0}
    picked = {(r["capture_path"], r["observation_index"]) for _, r in chosen}
    hist = [row for row in sorted(historical, key=lambda row: rank(row, seed)) if (row["capture_path"], row["observation_index"]) not in picked]
    by_season = collections.defaultdict(list)
    for row in hist:
        by_season[row["season"]].append(row)
    spread = []
    while len(spread) < 20 and any(by_season.values()):
        for season in sorted(by_season):
            if by_season[season] and len(spread) < 20:
                spread.append(by_season[season].pop(0))
    chosen.extend((f"HISTORICAL|{row['season']}", row) for row in spread)
    blind = [blind_record(row, index + 1, stratum) for index, (stratum, row) in enumerate(chosen)]
    out_dir.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out_dir / f"{stem}_BLIND.jsonl", 
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in blind), encoding="utf-8")
    manifest = {"label": LABEL, "cycle_number": 37, "attempt_number": 2, "seed": seed,
                "excluded_records": len(excluded), "excluded_from": str(exclude) if exclude else None,
                "sample_size": len(blind), "main_sample": len(blind) - len(spread), "historical_sample": len(spread),
                "historical_rows_available": len(historical),
                "historical_seasons_available": sorted({row["season"] for row in historical}),
                "strata": dict(collections.Counter(stratum for stratum, _ in chosen)),
                "stratum_shortfall": shortfall, "rows_file": str(rows_path),
                "rows_sha256": hashlib.sha256(rows_path.read_bytes()).hexdigest(),
                "blind_fields": ["page_title", "page_canonical", "visible_headings_before_record", "excerpt",
                                 "record_char_offset", "record_byte_offset"],
                "withheld_from_the_labeller": ["person", "source_title", "season", "roles", "sport", "program"]}
    _bas_atomic.write_text(out_dir / f"{stem}_MANIFEST.json", json.dumps(manifest, indent=2) + "\n",
                                                               encoding="utf-8")
    return manifest


def _school(value: str) -> str:
    """A school name without punctuation, so "Miami (OH)" and "Miami OH" compare equal."""

    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def compare(rows_path: Path, blind_path: Path, labels_path: Path, out: Path) -> dict[str, Any]:
    rows = {(r["capture_path"], r["observation_index"]): r
            for r in map(json.loads, rows_path.read_text(encoding="utf-8").splitlines())}
    blind = {item["sample_id"]: item for item in map(json.loads, blind_path.read_text(encoding="utf-8").splitlines())}
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    names: dict[str, str] = {}
    for line in CROSSWALK_ROWS.read_text(encoding="utf-8").splitlines():
        for claim in json.loads(line).get("claimed_programs") or []:
            names.setdefault(claim["program_id"], claim.get("display_name") or "")
    fields = collections.Counter()
    agree = collections.Counter()
    disagreements = []
    wrong_school_confirmed = []
    for label in labels["labels"]:
        item = blind[label["sample_id"]]
        row = rows[(item["key"]["capture_path"], item["key"]["observation_index"])]
        principal = sorted({a["role"] for a in row["assignments"]
                            if a["role"] in CORE and a["occupancy"] in ("PRINCIPAL", "CO_SHARED")})
        checks = {
            "person": (_norm(label["person"]), _norm(row["person"])),
            "title": (_norm(label["title"]), _norm(row["source_title"])),
            "season": (label["season"], row["season"]),
            "football": (label["football"], row["sport_scope"]["football_role_admissible"]),
            "principal_core_roles": (sorted(label["principal_core_roles"]), principal),
            "own_record": (label["own_record_located"], bool(row["binding"]["person_record_bound"])),
        }
        for name, (expected, got) in checks.items():
            if expected == "NOT_JUDGED":
                continue
            fields[name] += 1
            if expected == got:
                agree[name] += 1
            else:
                disagreements.append({"sample_id": label["sample_id"], "field": name, "label": expected,
                                      "reparse": got, "note": label.get("note")})
        admitted_name = names.get(row["program_id"]) if row["program_id"] else None
        if label.get("school_on_page") and admitted_name:
            fields["school"] += 1
            same = (label["school_program_id"] == row["program_id"] if label.get("school_program_id")
                    else _school(label["school_on_page"]) == _school(admitted_name))
            if same:
                agree["school"] += 1
            else:
                disagreements.append({"sample_id": label["sample_id"], "field": "school",
                                      "label": label["school_on_page"], "reparse": admitted_name,
                                      "note": label.get("note")})
                if row["admitted_for_coverage"]:
                    wrong_school_confirmed.append(label["sample_id"])
    report = {"label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-03-AC11",
              "labelled": len(labels["labels"]), "fields_judged": dict(fields),
              "agreement": {name: f"{agree[name]}/{fields[name]}" for name in fields},
              "disagreements": disagreements, "wrong_school_record_admitted": wrong_school_confirmed,
              "labeller": labels.get("labeller"), "independence_limit": labels.get("independence_limit"),
              "population_inference": ("None. A sample of this size shows where the reparse is right or wrong "
                                       "on these records; it does not estimate a population error rate.")}
    _bas_atomic.write_text(out, json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("draw")
    d.add_argument("--rows", type=Path, required=True)
    d.add_argument("--out", type=Path, required=True)
    d.add_argument("--seed", default=SEED)
    d.add_argument("--exclude", type=Path, help="blind file of an earlier sample; its records are not drawn")
    d.add_argument("--stem", default="R37_03_LABEL_SAMPLE")
    c = sub.add_parser("compare")
    c.add_argument("--rows", type=Path, required=True)
    c.add_argument("--blind", type=Path, required=True)
    c.add_argument("--labels", type=Path, required=True)
    c.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "draw":
        result = draw(args.rows, args.out, seed=args.seed, exclude=args.exclude, stem=args.stem)
    else:
        result = compare(args.rows, args.blind, args.labels, args.out)
    print(json.dumps({k: v for k, v in result.items() if k not in ("disagreements",)}, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())

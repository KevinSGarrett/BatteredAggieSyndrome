r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-09-AC06/AC08: an independent check of the contest-site successor on its
stratified sample. It imports nothing from ``aggie_analytics``: origins,
distances, time-zone shifts, relocation, label rules and the secondary
schedule entry are all re-derived here from the raw cached inputs, with a
different distance formula, so a shared bug cannot pass both.

Checks per sampled contest:

* **orientation** -- the home leg is the designated home side's own origin
  to the venue (not the away side's); swapping the sides swaps the legs;
* **distance** -- the spherical law of cosines on the same radius agrees
  with the producer's haversine within 0.05 km;
* **units** -- miles are kilometres divided by 1.609344;
* **time zones** -- each leg's shift is recomputed from the venue's and the
  origin's IANA zones at kickoff;
* **neutral** -- a missing feed flag is unknown, never false; a neutral
  contest has no ordinary home term and still has travel;
* **venue support** -- confirmed only when the secondary entry on that date
  names the venue's city; a provider index match alone is not confirmation;
* **aliases and relocation** -- same-program sides and teams whose home
  venue changed across payload years are detected from the raw payloads;
* **motivating case** -- any Lambeau Field contest is located by venue name,
  and its designated home side's own home venue is checked to differ.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
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

sys.dont_write_bytecode = True

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
CYCLE30 = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle30_work")
TEAMS = CYCLE30 / "raw" / "teams"
WIKIMEDIA = CYCLE30 / "raw" / "wikimedia"
VENUES = CYCLE30 / "outputs" / "CFBD_VENUES.jsonl"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
RADIUS = 6371.0088
MILE = 1.609344


def cosine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    c = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)
    return RADIUS * math.acos(max(-1.0, min(1.0, c)))


def team_payloads() -> list[tuple[int, list[dict[str, Any]]]]:
    """Every cached /teams payload with the year its request declared.

    The year is read from the payload's own request identity file name only
    through the declared parameter set, re-derived here: sha256 of the
    canonical JSON of {"endpoint": "/teams", "parameters": {...}}.
    """

    def identity(parameters: dict[str, Any]) -> str:
        text = json.dumps({"endpoint": "/teams", "parameters": parameters}, sort_keys=True,
                          separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    found = []
    for year in range(1963, 2027):
        for shape in ({}, {"classification": "fbs"}, {"classification": "fcs"}):
            path = TEAMS / f"{identity({'year': year, **shape})}.json"
            if path.is_file():
                data = json.loads(path.read_text(encoding="utf-8"))
                rows = data if isinstance(data, list) else (data.get("data") or data.get("teams") or [])
                found.append((year, [r for r in rows if isinstance(r, dict)]))
    return found


def latest_origins(payloads) -> tuple[dict[int, dict[str, Any] | None], dict[int, set], dict[int, str]]:
    by_team: dict[int, dict[int, set]] = collections.defaultdict(lambda: collections.defaultdict(set))
    venues_seen: dict[int, set] = collections.defaultdict(set)
    school: dict[int, str] = {}
    for year, rows in payloads:
        for row in rows:
            if row.get("id") is None:
                continue
            loc = row.get("location") or {}
            key = (loc.get("id"), loc.get("name"), loc.get("latitude"), loc.get("longitude"), loc.get("timezone"))
            by_team[int(row["id"])][year].add(key)
            if loc.get("id") is not None:
                venues_seen[int(row["id"])].add(loc["id"])
            school[int(row["id"])] = str(row.get("school") or "")
    origins: dict[int, dict[str, Any] | None] = {}
    for team, years in by_team.items():
        latest = max(years)
        readings = years[latest]
        if len(readings) != 1:
            origins[team] = None
            continue
        venue_id, name, lat, lon, tz = next(iter(readings))
        origins[team] = None if lat is None or lon is None else {
            "venue_id": venue_id, "name": name, "point": (float(lat), float(lon)), "tz": tz}
    return origins, venues_seen, school


def offset(tz: str | None, at: datetime | None) -> float | None:
    if not tz or at is None:
        return None
    try:
        return at.astimezone(ZoneInfo(tz)).utcoffset().total_seconds() / 3600.0
    except Exception:
        return None


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", re.sub(r"\([^)]*\)", " ", text.lower())).strip()


def unlink(text: str) -> str:
    return re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", text)


def secondary_sites(revision: dict[str, Any] | None, season: int) -> dict[date, list[tuple[str, str]]]:
    """Independent minimal read of a schedule table: date -> (site city, stadium)."""

    if not revision or not revision.get("file"):
        return {}
    payload = json.loads((WIKIMEDIA / revision["file"]).read_text(encoding="utf-8"))
    pages = payload["query"]["pages"]
    page = pages[0] if isinstance(pages, list) else next(iter(pages.values()))
    slot = page["revisions"][0]["slots"]["main"]
    text = slot.get("*") or slot.get("content") or ""
    months = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july",
                                          "august", "september", "october", "november", "december"], 1)}
    out: dict[date, list[tuple[str, str]]] = collections.defaultdict(list)
    # One block per entry, cut at the next entry's start or at the entry's own
    # closing line ("}}" or "|}}"), whichever comes first.
    cuts = [m.start() for m in re.finditer(r"\{\{\s*CFB schedule entry", text, flags=re.I)] + [len(text)]
    blocks = []
    for a, b in zip(cuts, cuts[1:]):
        closing = re.search(r"\n\s*\|?\s*\}\}", text[a:b])
        blocks.append(text[a:b][:closing.start()] if closing else text[a:b])
    for block in blocks:
        # The date field only: a citation inside the entry has its own date.
        field = re.search(r"^\s*\|\s*date\s*=(.*)$", block, flags=re.M)
        value = re.sub(r"<ref.*", "", field.group(1)) if field else ""
        d = re.search(r"([A-Za-z]+)\s+(\d{1,2})\b", value)
        c = re.search(r"\|\s*site_cityst\s*=\s*(.*)", block)
        st = re.search(r"\|\s*site_stadium\s*=\s*(.*)", block)
        if not d or not c or d.group(1).lower() not in months:
            continue
        month = months[d.group(1).lower()]
        try:
            when = date(season + 1 if month <= 6 else season, month, int(d.group(2)))
        except ValueError:
            continue
        city_text = unlink(c.group(1)).strip()
        city = city_text.split(",")[0] if "," in city_text else re.sub(r"\s+[A-Z]{2}$", "", city_text)
        out[when].append((norm(city), norm(unlink(st.group(1))) if st else ""))
    return out


def check_row(row: dict[str, Any], venues: dict[Any, Any], origins: dict[int, Any],
              venues_seen: dict[int, set], school: dict[int, str]) -> tuple[list[str], bool, Any]:
    """Every problem the independent re-derivation finds in one successor row."""

    problems = []
    venue = venues.get(row.get("venue_id"))
    point = (float(venue["latitude"]), float(venue["longitude"])) \
        if venue and venue.get("latitude") is not None else None
    kickoff = datetime.fromisoformat(row["start_utc"].replace("Z", "+00:00")) if row.get("start_utc") else None
    if kickoff and kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=timezone.utc)
    for side, other in (("home", "away"), ("away", "home")):
        team = row.get(f"designated_{side}_team_id")
        origin = origins.get(int(team)) if team is not None else None
        leg = row[f"{side}_leg"]
        if origin is None or point is None:
            if leg["km"] is not None:
                problems.append(f"{side}: a leg exists where an origin or venue coordinate is missing")
            continue
        expected = cosine_km(origin["point"], point)
        if leg["km"] is None or abs(leg["km"] - expected) > 0.05:
            problems.append(f"{side}: distance {leg['km']} vs independent {expected:.3f}")
        elif abs(leg["miles"] * MILE - leg["km"]) > 1e-6:
            problems.append(f"{side}: miles and kilometres disagree")
        other_team = row.get(f"designated_{other}_team_id")
        other_origin = origins.get(int(other_team)) if other_team is not None else None
        if other_origin and other_origin["point"] != origin["point"] and leg["km"] is not None \
                and abs(leg["km"] - cosine_km(other_origin["point"], point)) < 1e-9 \
                and abs(expected - leg["km"]) > 0.05:
            problems.append(f"{side}: leg matches the other side's origin (swapped orientation)")
        shift = None
        venue_offset, origin_offset = offset(venue.get("timezone"), kickoff), offset(origin["tz"], kickoff)
        if venue_offset is not None and origin_offset is not None:
            shift = venue_offset - origin_offset
        if shift != leg.get("tz_shift_hours"):
            problems.append(f"{side}: tz shift {leg.get('tz_shift_hours')} vs independent {shift}")
        relocated = len(venues_seen.get(int(team), set())) > 1
        if relocated != bool(row.get(f"{side}_origin_relocated_across_vintages")):
            problems.append(f"{side}: relocation flag {row.get(f'{side}_origin_relocated_across_vintages')} "
                            f"vs independent {relocated}")

    flag = row.get("source_neutral_flag")
    expected_status = {True: "SOURCE_DESIGNATED_NEUTRAL", False: "SOURCE_DESIGNATED_NOT_NEUTRAL"}.get(
        flag, "NEUTRAL_STATUS_UNKNOWN")
    if row["neutral_status"] != expected_status:
        problems.append(f"neutral status {row['neutral_status']} for feed flag {flag}")
    if row["neutral_status"] == "SOURCE_DESIGNATED_NEUTRAL":
        if row.get("ordinary_home_term_magnitude") != 0.0:
            problems.append("neutral contest keeps an ordinary home term")
    elif row.get("ordinary_home_term_magnitude") == 0.0:
        problems.append("non-neutral or unknown contest has a zero home term")
    if row["neutral_status"] == "NEUTRAL_STATUS_UNKNOWN" and row.get("ordinary_home_term_applies") is not None:
        problems.append("unknown neutral status resolved to a value")

    state = (row.get("secondary_confirmation") or {}).get("state")
    support = row["venue_support"]
    if row.get("venue_id") is None and support != "VENUE_ID_ABSENT_IN_FEED":
        problems.append(f"no venue id but support {support}")
    if support == "INDEPENDENTLY_CONFIRMED_BY_SECONDARY_SOURCE":
        revision = (row.get("secondary_confirmation") or {}).get("secondary_revision")
        sites = secondary_sites(revision, int(row["season"]))
        local = (row.get("secondary_confirmation") or {}).get("feed_local_date")
        want_city = norm(str((venue or {}).get("city") or ""))
        want_stadium = norm(str((venue or {}).get("name") or ""))
        near = [pair for d, pairs in sites.items()
                if local and abs((d - date.fromisoformat(local)).days) <= 1 for pair in pairs]
        if not any((city and city == want_city) or (stadium and stadium == want_stadium)
                   for city, stadium in near):
            problems.append("confirmed support, but the independent read of the secondary entry names "
                            "neither the venue city nor the venue on that date")
    if support == "PROVIDER_VENUE_INDEX_MATCH_NOT_INDEPENDENT" and state == "DATE_AND_SITE_CITY_CONFIRMED":
        problems.append("a confirmed contest is labelled provider-only")

    home, away = row.get("designated_home_team_id"), row.get("designated_away_team_id")
    alias = home is not None and away is not None and home != away and \
        school.get(int(home)) and school.get(int(home)) == school.get(int(away))
    if (home == away) != bool(row.get("same_team_both_sides")):
        problems.append("same-team flag disagrees with the ids")

    motivating = None
    if "lambeau" in str((venue or {}).get("name") or "").casefold():
        own = origins.get(int(home)) if home is not None else None
        motivating = {"venue": venue.get("name"),
                      "designated_home_own_venue": own and own["name"],
                      "designated_label_locates_the_contest": bool(own and own["venue_id"] == row.get("venue_id"))}
        if motivating["designated_label_locates_the_contest"]:
            problems.append("the motivating case's designated home venue is the contest venue")

    return problems, bool(alias), motivating


#: Declared negative controls: each corrupts one sampled row in memory the
#: way a real defect would, and the check must report it. A checker that
#: passes every control has not shown it can fail.
def _mutations(row: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    out = []
    home, away = row["home_leg"], row["away_leg"]
    if home.get("km") is not None and away.get("km") is not None and abs(home["km"] - away["km"]) > 1:
        out.append(("SWAPPED_ORIENTATION", {**row, "home_leg": away, "away_leg": home}))
    # A scaled or mis-unitised zero is still zero, so these two target a leg
    # long enough for the defect to change the value.
    long_side = next((side for side in ("away", "home") if (row[f"{side}_leg"].get("km") or 0) > 10), None)
    if long_side:
        leg = row[f"{long_side}_leg"]
        out.append(("DISTANCE_SCALED", {**row, f"{long_side}_leg": {**leg, "km": leg["km"] * 1.01,
                                                                     "miles": leg["km"] * 1.01 / MILE}}))
        out.append(("MILES_REPORTED_AS_KM", {**row, f"{long_side}_leg": {**leg, "miles": leg["km"]}}))
    if home.get("tz_shift_hours") is not None:
        out.append(("TZ_SHIFT_OFF_BY_ONE", {**row, "home_leg": {**home, "tz_shift_hours": home["tz_shift_hours"] + 1}}))
    out.append(("MISSING_NEUTRAL_FLAG_BECOMES_FALSE", {**row, "source_neutral_flag": None,
                                                       "neutral_status": "SOURCE_DESIGNATED_NOT_NEUTRAL"}))
    if row.get("venue_support") in ("PROVIDER_VENUE_INDEX_MATCH_NOT_INDEPENDENT", "SECONDARY_SOURCE_DISAGREES_ON_SITE"):
        out.append(("UNSUPPORTED_CONFIRMATION_LABEL",
                    {**row, "venue_support": "INDEPENDENTLY_CONFIRMED_BY_SECONDARY_SOURCE"}))
    return out


def check(sample_path: Path) -> dict[str, Any]:
    venues = {}
    for line in VENUES.read_text(encoding="utf-8").splitlines():
        if line.strip():
            v = json.loads(line)
            venues[v["id"]] = v
    origins, venues_seen, school = latest_origins(team_payloads())
    rows = [json.loads(line) for line in sample_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    results, failures = [], collections.Counter()
    controls: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    missed_controls: list[dict[str, Any]] = []
    for row in rows:
        problems, alias, motivating = check_row(row, venues, origins, venues_seen, school)
        for p in problems:
            failures[p.split(":")[0]] += 1
        results.append({"canonical_game_id": row["canonical_game_id"], "stratum": row.get("stratum"),
                        "neutral_status": row["neutral_status"], "venue_support": row["venue_support"],
                        "legs_checked": sum(1 for s in ("home", "away") if row[f"{s}_leg"]["km"] is not None),
                        "alias_sides_same_school": alias, "motivating_case": motivating,
                        "problems": problems, "passes": not problems})
        if not problems:
            for name, mutated in _mutations(row):
                caught = bool(check_row(mutated, venues, origins, venues_seen, school)[0])
                controls[name]["caught" if caught else "missed"] += 1
                if not caught:
                    missed_controls.append({"control": name, "canonical_game_id": row["canonical_game_id"],
                                            "venue_support": row["venue_support"],
                                            "confirmation": row.get("secondary_confirmation")})
    strata = collections.Counter("|".join(r["stratum"]) for r in results)
    return {"label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-09-AC06/AC08",
            "independence": "Imports no aggie_analytics module; every value re-derived from raw cached inputs "
                            "with a different distance formula.",
            "sample": {"path": str(sample_path), "sha256": hashlib.sha256(sample_path.read_bytes()).hexdigest(),
                       "rows": len(rows), "strata": dict(strata)},
            "passed": sum(1 for r in results if r["passes"]), "failed": sum(1 for r in results if not r["passes"]),
            "failure_kinds": dict(failures), "results": results,
            "negative_controls": {k: dict(v) for k, v in sorted(controls.items())},
            "negative_controls_missed": sum(v["missed"] for v in controls.values()),
            "missed_control_rows": missed_controls,
            "generated_at_utc": datetime.now(timezone.utc).isoformat()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sample", type=Path, default=ATTEMPT / "evidence/repairs/R37_09_INDEPENDENT_SAMPLE.jsonl")
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence/repairs/R37_09_INDEPENDENT_CHECK.json")
    args = parser.parse_args(argv)
    receipt = check(args.sample)
    _bas_atomic.write_text(args.out, json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print("sample:", receipt["sample"]["rows"], receipt["sample"]["strata"])
    print("passed:", receipt["passed"], "failed:", receipt["failed"], receipt["failure_kinds"])
    print("negative controls:", receipt["negative_controls"], "| missed:", receipt["negative_controls_missed"])
    for r in receipt["results"]:
        if r["problems"]:
            print("  ", r["canonical_game_id"], r["problems"][:3])
    return 1 if receipt["failed"] or receipt["negative_controls_missed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

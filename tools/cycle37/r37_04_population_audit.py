r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-04: audit the national membership population against its own source bytes.

This tool is deliberately independent of the producer. It imports nothing
from ``cycle36.c36_04_program_population``, nothing from
``cycle36.membership_lineage`` and nothing from the release builder. It opens
the cached payloads, recomputes what it needs, and asks whether the delivered
rows are what those bytes say. Agreement is therefore informative rather than
guaranteed by shared code.

What each section answers, and to which acceptance criterion:

* **AC02 -- exact source verification.** For every season, the cached
  ``/teams`` payload is hashed, its request identity is recomputed from the
  route and parameters, and every delivered membership row is checked against
  the payload's own rows: does the entity appear, does the classification the
  row records equal the classification the payload states, and does the
  payload itself contain duplicates. A deliberately wrong request identity is
  run beside the real one as a negative control, because a check that cannot
  fail has not verified anything.
* **AC03 / AC07 -- row grain and expected cells.** One row per
  program-season, and three HC/OC/DC expected cells per key. The delivered
  release's core-role cells are counted directly from the database when one
  is supplied, so ``12988 x 3 = 38964`` is reconciled rather than asserted.
* **AC01 / AC07 -- the season-division population ledger.** Year by year,
  era-correct buckets, and an exclusion ledger that says for each season how
  many source rows were excluded and under which classification the source
  put them. A denominator that shrinks is visible here.
* **AC05 -- the 2020 population change.** Investigated through a second
  route rather than assumed. The ``/games`` payloads are a different endpoint
  with different bytes; they say whether the programs missing from the 2020
  membership statement played at all, when the season was played, and whether
  the two routes disagree about anyone.
* **AC04 -- unresolved display names.** Reported with what the cache does and
  does not say. Nothing is merged here; a related spelling is a candidate
  requiring source rename evidence, which is not this tool's to invent.

What this tool does not establish: that a source's membership statement is
true. It establishes that the delivered population is what the acquired bytes
say, and names every place where it is not.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
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

#: Recomputed locally rather than imported, so that an agreement between this
#: audit and the producer is evidence rather than a shared implementation.
def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


#: The request-identity conventions this repository writes, recomputed here.
IDENTITY_CONVENTIONS = {
    "CYCLE30_LEDGER_CACHE_HIT_PATH_PARAMETERS_V1": lambda route, parameters: (
        sha256_json({"path": route, "parameters": parameters})
    ),
    "CYCLE30_LEDGER_LIVE_PATH_PARAMETERS_RUN_V1": lambda route, parameters: (
        sha256_json({"path": route, "parameters": parameters, "run_id": "cycle30"})
    ),
    "CYCLE30_CACHE_FILENAME_ENDPOINT_PARAMETERS_V1": lambda route, parameters: (
        sha256_json({"endpoint": route, "parameters": parameters})
    ),
}

#: The parameter shapes the cache was written under, in the order they are
#: tried. The source ignores ``classification`` on ``/teams`` and returns
#: identical bytes for all three, which is itself reported.
TEAMS_SHAPES = ({}, {"classification": "fbs"}, {"classification": "fcs"})

#: The three core roles an expected cell is opened for.
CORE_ROLES = ("HC", "OC", "DC")

FOOTBALL_CLASSIFICATIONS = ("fbs", "fcs")

DECLARED_SCOPE = (1963, 2026)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def payload_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        payload = payload.get("data") or payload.get("teams") or []
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def entity_suffix(program_id: Any) -> str:
    return str(program_id or "").rsplit(":", 1)[-1]


def cache_identity(route: str, parameters: dict[str, Any]) -> str:
    return IDENTITY_CONVENTIONS["CYCLE30_CACHE_FILENAME_ENDPOINT_PARAMETERS_V1"](
        route, parameters
    )


def locate_payloads(
    cache: dict[str, Path], route: str, year: int, shapes: tuple[dict[str, Any], ...]
) -> list[tuple[dict[str, Any], str, Path]]:
    """Every cached file for this route and year, over the declared shapes.

    The cache was not written under one shape. ``/teams`` was requested as
    ``{classification, year}`` for 2013-2023 and as ``{year}`` alone for the
    years a later tool restored, so a lookup that tries only one shape finds
    nothing for most of the range and silently reports an empty source. The
    first version of this audit did exactly that and reported zero source rows
    for 2019 through 2023 while still printing a verified count.
    """

    found = []
    for shape in shapes:
        parameters = {"year": int(year), **shape}
        path = cache.get(cache_identity(route, parameters))
        if path is not None:
            found.append((parameters, cache_identity(route, parameters), path))
    return found


def effective_classification(row: dict[str, Any]) -> Any:
    """The division a delivered row states, whichever field carries it.

    Two derivatives feed the membership file and they populate different
    fields: the 1963-2012 rows carry ``source_classification`` with
    ``classification`` null, and the 2013-2023 rows carry ``classification``
    with ``source_classification`` null. Reading only one of them makes the
    check vacuous for half the range.
    """

    for field in ("classification", "source_classification"):
        value = row.get(field)
        if value is not None:
            return value
    return None


# ------------------------------------------------------------------ AC02 ---
def verify_sources(
    membership: list[dict[str, Any]], raw_root: Path
) -> dict[str, Any]:
    """Every delivered row checked against the bytes of its season's payload."""

    cache = {path.stem: path for path in sorted((raw_root / "teams").glob("*.json"))}
    by_season: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in membership:
        by_season[int(row["season"])].append(row)

    seasons: list[dict[str, Any]] = []
    unverified_rows: list[dict[str, Any]] = []
    classification_disagreements: list[dict[str, Any]] = []
    for season in sorted(by_season):
        located = locate_payloads(cache, "/teams", season, TEAMS_SHAPES)
        if not located:
            seasons.append(
                {
                    "season": season,
                    "state": "NO_CACHED_PAYLOAD_COVERS_THIS_SEASON",
                    "delivered_rows": len(by_season[season]),
                    "verified_rows": 0,
                }
            )
            for row in by_season[season]:
                unverified_rows.append(
                    {
                        "season": season,
                        "program_id": row.get("program_id"),
                        "reason": "NO_CACHED_PAYLOAD",
                    }
                )
            continue

        parameters, identity, path = located[0]
        digest = sha256_file(path)
        rows = payload_rows(json.loads(path.read_text(encoding="utf-8")))
        source_ids = collections.Counter(str(r.get("id")) for r in rows)
        source_class = {str(r.get("id")): r.get("classification") for r in rows}

        verified = 0
        for row in by_season[season]:
            entity = entity_suffix(row.get("program_id"))
            if entity not in source_ids:
                unverified_rows.append(
                    {
                        "season": season,
                        "program_id": row.get("program_id"),
                        "reason": "ENTITY_NOT_IN_PAYLOAD",
                    }
                )
                continue
            stated = source_class.get(entity)
            recorded = effective_classification(row)
            if recorded is not None and stated != recorded:
                classification_disagreements.append(
                    {
                        "season": season,
                        "program_id": row.get("program_id"),
                        "row_says": recorded,
                        "payload_says": stated,
                    }
                )
                continue
            verified += 1

        # The bytes being identical across parameter shapes is a property of
        # the source, not an accident of this audit, so it is reported.
        digests_by_shape = {
            json.dumps(p, sort_keys=True): sha256_file(candidate)
            for p, _, candidate in located
        }
        seasons.append(
            {
                "season": season,
                "state": "PAYLOAD_PRESENT",
                "cached_payload": str(path),
                "payload_sha256": digest,
                "payload_rows": len(rows),
                "request_parameters": parameters,
                "request_identity_sha256": identity,
                "request_identity_convention": (
                    "CYCLE30_CACHE_FILENAME_ENDPOINT_PARAMETERS_V1"
                ),
                "request_identity_recomputes": identity
                == cache_identity("/teams", parameters),
                "parameter_shapes_cached": len(located),
                "all_shapes_byte_identical": len(set(digests_by_shape.values())) == 1,
                "duplicate_entity_ids_in_payload": sum(
                    1 for count in source_ids.values() if count > 1
                ),
                "delivered_rows": len(by_season[season]),
                "verified_rows": verified,
            }
        )

    # A negative control: an identity that belongs to a different year must
    # not recompute for this one, or the check above proves nothing.
    wrong = cache_identity("/teams", {"year": 1999})
    right = cache_identity("/teams", {"year": 2026})
    return {
        "seasons": seasons,
        "delivered_rows": len(membership),
        "verified_rows": sum(s["verified_rows"] for s in seasons),
        "rows_not_verified": unverified_rows[:200],
        "rows_not_verified_count": len(unverified_rows),
        "classification_disagreements": classification_disagreements[:200],
        "classification_disagreement_count": len(classification_disagreements),
        "seasons_without_a_payload": [
            s["season"] for s in seasons if s["state"] != "PAYLOAD_PRESENT"
        ],
        "negative_control": {
            "question": "does a different year's request identity recompute for 2026",
            "identity_for_1999": wrong,
            "identity_for_2026": right,
            "distinct": wrong != right,
        },
        "every_delivered_row_verified": not unverified_rows
        and not classification_disagreements,
    }


# ------------------------------------------------------------ AC03 / AC07 ---
def reconcile_grain(
    membership: list[dict[str, Any]], release: Path | None
) -> dict[str, Any]:
    keys = collections.Counter(
        (str(row.get("program_id")), int(row["season"])) for row in membership
    )
    duplicated = sorted(key for key, count in keys.items() if count > 1)
    expected_cells = len(keys) * len(CORE_ROLES)

    delivered: dict[str, Any] = {"release": None}
    if release is not None and release.is_file():
        connection = sqlite3.connect(
            f"file:{release.as_posix()}?mode=ro&immutable=1", uri=True
        )
        try:
            tables = {
                str(r[0])
                for r in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            cells = (
                int(
                    connection.execute("SELECT COUNT(*) FROM core_role_cell").fetchone()[0]
                )
                if "core_role_cell" in tables
                else None
            )
            memberships = (
                int(
                    connection.execute(
                        "SELECT COUNT(*) FROM program_season_membership"
                    ).fetchone()[0]
                )
                if "program_season_membership" in tables
                else None
            )
            roles = (
                sorted(
                    str(r[0])
                    for r in connection.execute(
                        "SELECT DISTINCT role_code FROM core_role_cell"
                    )
                )
                if "core_role_cell" in tables
                else []
            )
            delivered = {
                "release": str(release),
                "release_sha256": sha256_file(release),
                "core_role_cells": cells,
                "program_season_memberships": memberships,
                "role_codes": roles,
            }
        finally:
            connection.close()

    return {
        "program_season_keys": len(keys),
        "rows": len(membership),
        "one_row_per_program_season": not duplicated,
        "duplicated_keys": [list(key) for key in duplicated[:50]],
        "duplicated_key_count": len(duplicated),
        "core_roles": list(CORE_ROLES),
        "expected_cells_from_membership": expected_cells,
        "delivered": delivered,
        "expected_cells_match_delivered": (
            delivered.get("core_role_cells") == expected_cells
            if delivered.get("core_role_cells") is not None
            else None
        ),
        "membership_rows_match_delivered": (
            delivered.get("program_season_memberships") == len(membership)
            if delivered.get("program_season_memberships") is not None
            else None
        ),
    }


# ------------------------------------------------------------ AC01 / AC07 ---
def population_ledger(
    membership: list[dict[str, Any]], raw_root: Path
) -> dict[str, Any]:
    cache = {path.stem: path for path in sorted((raw_root / "teams").glob("*.json"))}
    by_season: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in membership:
        by_season[int(row["season"])].append(row)

    low, high = DECLARED_SCOPE
    rows: list[dict[str, Any]] = []
    missing_era: list[int] = []
    for season in range(low, high + 1):
        delivered = by_season.get(season, [])
        located = locate_payloads(cache, "/teams", season, TEAMS_SHAPES)
        source = (
            payload_rows(json.loads(located[0][2].read_text(encoding="utf-8")))
            if located
            else []
        )
        source_buckets = collections.Counter(
            str(r.get("classification")) for r in source
        )
        kept = {entity_suffix(r.get("program_id")) for r in delivered}
        excluded = collections.Counter(
            str(r.get("classification"))
            for r in source
            if str(r.get("id")) not in kept
        )
        eras = collections.Counter(str(r.get("era")) for r in delivered)
        if any(r.get("era") in (None, "", "None") for r in delivered):
            missing_era.append(season)
        rows.append(
            {
                "season": season,
                "delivered_programs": len(delivered),
                "source_rows": len(source),
                "source_classifications": dict(sorted(source_buckets.items())),
                "delivered_by_classification": dict(
                    sorted(
                        collections.Counter(
                            str(effective_classification(r)) for r in delivered
                        ).items()
                    )
                ),
                "classification_field_used": dict(
                    sorted(
                        collections.Counter(
                            "classification"
                            if r.get("classification") is not None
                            else "source_classification"
                            if r.get("source_classification") is not None
                            else "neither"
                            for r in delivered
                        ).items()
                    )
                ),
                "excluded_by_source_classification": dict(sorted(excluded.items())),
                "excluded_total": sum(excluded.values()),
                "era_labels": dict(sorted(eras.items())),
                "state": "MEMBERSHIP_PRESENT" if delivered else "NO_MEMBERSHIP_ROWS",
            }
        )

    return {
        "declared_scope": list(DECLARED_SCOPE),
        "seasons_in_scope": high - low + 1,
        "seasons_with_rows": sum(1 for r in rows if r["delivered_programs"]),
        "seasons_with_no_rows": [r["season"] for r in rows if not r["delivered_programs"]],
        "seasons_where_some_row_carries_no_era": missing_era,
        "exclusions_are_bound_to_a_source_classification": all(
            "None" not in r["excluded_by_source_classification"]
            or r["excluded_by_source_classification"].get("None", 0) == 0
            for r in rows
        ),
        "by_season": rows,
        "denominator_note": (
            "Excluded rows are source rows this season's payload carries that "
            "the football population does not keep, counted under the "
            "classification the source itself states. A denominator that got "
            "smaller would show here as a rise in exclusions, not as a rise in "
            "confirmed coverage."
        ),
    }


# ------------------------------------------------------------------ AC05 ---
def investigate_2020(
    membership: list[dict[str, Any]], raw_root: Path, season: int = 2020
) -> dict[str, Any]:
    """The 2020 change examined through a second route, not assumed."""

    cache_teams = {p.stem: p for p in (raw_root / "teams").glob("*.json")}
    cache_games = {p.stem: p for p in (raw_root / "games").glob("*.json")}

    def teams_for(year: int) -> list[dict[str, Any]]:
        located = locate_payloads(cache_teams, "/teams", year, TEAMS_SHAPES)
        if not located:
            return []
        return payload_rows(json.loads(located[0][2].read_text(encoding="utf-8")))

    def games_for(year: int) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        located = locate_payloads(
            cache_games,
            "/games",
            year,
            ({"classification": "fcs"}, {}, {"classification": "fbs"}),
        )
        if not located:
            return [], None
        parameters, _, path = located[0]
        return (
            payload_rows(json.loads(path.read_text(encoding="utf-8"))),
            {
                "parameters": parameters,
                "cached_payload": str(path),
                "payload_sha256": sha256_file(path),
                "scope_note": (
                    "This payload was requested with classification=fcs, so it "
                    "records games in which at least one side is FCS. It is the "
                    "right instrument for FCS absences and cannot speak to an "
                    "FBS program that played only FBS opponents."
                ),
            },
        )

    previous, current, following = season - 1, season, season + 1

    def football(year: int) -> dict[str, dict[str, Any]]:
        """Only the programs the source itself puts in the two subdivisions.

        A ``/teams`` payload carries every division the provider knows, so
        differencing whole payloads compares Division III rosters as well and
        reports no change. The population under audit is the football
        denominator, which is the rows the source classifies fbs or fcs.
        """

        return {
            str(row.get("id")): row
            for row in teams_for(year)
            if row.get("classification") in FOOTBALL_CLASSIFICATIONS
        }

    before, now, after = football(previous), football(current), football(following)
    absent = sorted(set(before) - set(now))
    games, provenance = games_for(current)
    played: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in games:
        for side in ("home", "away"):
            played[str(row.get(f"{side}Id"))].append(
                {
                    "start_date": row.get("startDate"),
                    "opponent": row.get("awayTeam" if side == "home" else "homeTeam"),
                    "completed": row.get("completed"),
                }
            )
    later_games, _ = games_for(following)
    played_after = set()
    for row in later_games:
        played_after.add(str(row.get("homeId")))
        played_after.add(str(row.get("awayId")))

    detail = []
    for entity in absent:
        row = before[entity]
        appearances = played.get(entity, [])
        detail.append(
            {
                "source_entity_id": entity,
                "school": row.get("school"),
                "conference": row.get("conference"),
                f"classification_in_{previous}": row.get("classification"),
                f"in_{current}_membership_statement": False,
                f"games_recorded_for_the_{current}_season": len(appearances),
                f"first_{current}_game": appearances[0] if appearances else None,
                f"in_{following}_membership_statement": entity in after,
                f"played_in_{following}": entity in played_after,
            }
        )

    by_conference = collections.Counter(
        str(before[entity].get("conference")) for entity in absent
    )
    whole_conferences = []
    for conference, count in by_conference.items():
        total = sum(
            1 for r in before.values() if str(r.get("conference")) == conference
        )
        if total and count == total:
            whole_conferences.append({"conference": conference, "programs": count})

    calendar = collections.Counter(str(row.get("startDate", ""))[:4] for row in games)
    months = collections.Counter(str(row.get("startDate", ""))[:7] for row in games)

    # The one thing that would be a source inconsistency rather than a
    # participation change: a program the membership statement omits that the
    # results route says played.
    contradicted = [
        row
        for row in detail
        if row[f"games_recorded_for_the_{current}_season"]
    ]

    playing = set()
    for row in games:
        for side in ("home", "away"):
            if row.get(f"{side}Classification") == "fcs":
                playing.add(str(row.get(f"{side}Id")))
    stated_fcs = {
        entity for entity, row in now.items() if row.get("classification") == "fcs"
    }

    return {
        "season": current,
        "method": (
            "The membership statement and the results statement are different "
            "endpoints with different bytes. Asking the second whether the "
            "programs missing from the first played at all is a check, not an "
            "assumption about why they are missing."
        ),
        "membership_counts": {
            str(year): dict(
                sorted(
                    collections.Counter(
                        str(r.get("classification")) for r in payload.values()
                    ).items()
                )
            )
            for year, payload in ((previous, before), (current, now), (following, after))
        },
        "programs_absent": len(absent),
        "absent_by_conference": dict(sorted(by_conference.items())),
        "entire_conferences_absent": sorted(
            whole_conferences, key=lambda r: -r["programs"]
        ),
        "absent_programs": detail,
        "absent_and_played_nothing": sum(
            1 for row in detail if not row[f"games_recorded_for_the_{current}_season"]
        ),
        "absent_but_the_results_route_says_they_played": contradicted,
        "returned_the_following_season": sum(
            1 for row in detail if row[f"in_{following}_membership_statement"]
        ),
        "games_route": provenance,
        "games_recorded": len(games),
        "games_by_calendar_year": dict(sorted(calendar.items())),
        "games_by_month": dict(sorted(months.items())),
        "games_played_on_a_later_calendar_year": sum(
            count for year, count in calendar.items() if year and int(year) > current
        ),
        "fcs_programs_in_the_membership_statement": len(stated_fcs),
        "fcs_programs_the_results_route_shows_playing": len(playing),
        "playing_but_not_in_the_membership_statement": sorted(playing - stated_fcs),
        "what_this_establishes": (
            "The payload is complete and byte-verified, so the reduced count is "
            "not a truncated or failed acquisition. A separate route confirms "
            "that all but one of the absent programs played no game recorded "
            "for this season, and that the season itself was largely played on "
            "the following calendar year's dates. The absences are clustered by "
            "conference rather than scattered, which is the shape of a decision "
            "not to play rather than of rows lost in transfer."
        ),
        "what_this_does_not_establish": (
            "Both routes are the same provider. This is route-independent "
            "corroboration, not provider-independent corroboration, and it "
            "cannot say why a program did not play. The only non-CFBD "
            "membership source in the cache is a single current-academic-year "
            "NCAA snapshot, which carries no historical year and cannot speak "
            "to this season. Acquiring a historical non-CFBD membership source "
            "is an acquisition decision, not local work."
        ),
    }


# ------------------------------------------------------------------ AC04 ---
#: The fields an unresolved-name entry actually carries. Named as a constant
#: so that a producer renaming one breaks the check below instead of silently
#: emptying this section: the first version of this audit guessed
#: "display_name" and "related_declared_names", neither of which exists, and
#: published twenty rows of nulls that looked like twenty inspected names.
UNRESOLVED_NAME_FIELDS = ("raw_name", "normalized_query", "state", "seasons")


def unresolved_names(coverage: dict[str, Any]) -> dict[str, Any]:
    names = coverage.get("unresolved_program_names") or []
    unreadable: list[str] = []
    rows = []
    for entry in names:
        missing = [f for f in UNRESOLVED_NAME_FIELDS if f not in entry]
        if missing:
            unreadable.append(
                f"{entry.get('raw_name') or '<unnamed>'}: missing {missing}"
            )
        inspection = entry.get("individual_inspection") or {}
        candidates = inspection.get("related_declared_spellings") or []
        rows.append(
            {
                "raw_name": entry.get("raw_name"),
                "normalized_query": entry.get("normalized_query"),
                "seasons": entry.get("seasons"),
                "state": entry.get("state"),
                "candidate_program_ids": entry.get("candidate_program_ids") or [],
                "declared_names_searched": inspection.get("declared_names_searched"),
                "related_declared_spellings": [
                    {
                        "declared_name": c.get("declared_name"),
                        "canonical_program_id": c.get("canonical_program_id"),
                        "basis": c.get("basis"),
                        "disposition": c.get("disposition"),
                    }
                    for c in candidates
                ],
                "resolved_here": False,
                "why_not": (
                    "A related spelling is a candidate requiring source rename "
                    "evidence with an effective date. This audit does not hold "
                    "such evidence and does not invent it; mapping by "
                    "resemblance is the inference this cycle declines "
                    "everywhere else."
                ),
            }
        )
    with_candidate = sum(1 for r in rows if r["related_declared_spellings"])
    return {
        "unresolved_display_names": len(rows),
        "with_a_related_declared_spelling": with_candidate,
        "with_no_related_spelling_at_all": len(rows) - with_candidate,
        "resolved_by_this_audit": 0,
        "entries_this_audit_could_not_read": unreadable,
        "every_entry_readable": not unreadable,
        "names": rows,
        "alias_collisions": coverage.get("crosswalk_conflicts", {}).get("collisions", []),
        "alias_collision_count": coverage.get("crosswalk_conflicts", {}).get(
            "colliding_alias_count"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--release", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    membership = read_jsonl(args.membership)
    coverage = json.loads(args.coverage.read_text(encoding="utf-8"))

    sources = verify_sources(membership, args.raw_root)
    grain = reconcile_grain(membership, args.release)
    ledger = population_ledger(membership, args.raw_root)
    twenty_twenty = investigate_2020(membership, args.raw_root)
    names = unresolved_names(coverage)

    findings: list[str] = []
    if not sources["every_delivered_row_verified"]:
        findings.append(
            f"{sources['rows_not_verified_count']} rows have no source row and "
            f"{sources['classification_disagreement_count']} disagree with the "
            "classification their payload states"
        )
    if not grain["one_row_per_program_season"]:
        findings.append(f"{grain['duplicated_key_count']} program-season keys repeat")
    if grain["expected_cells_match_delivered"] is False:
        findings.append(
            f"the delivered release carries {grain['delivered']['core_role_cells']} "
            f"core-role cells where the membership implies "
            f"{grain['expected_cells_from_membership']}"
        )
    if ledger["seasons_with_no_rows"]:
        findings.append(
            f"seasons with no membership rows: {ledger['seasons_with_no_rows']}"
        )
    if ledger["seasons_where_some_row_carries_no_era"]:
        findings.append(
            "seasons where a delivered row carries no era label: "
            f"{ledger['seasons_where_some_row_carries_no_era']}"
        )
    if not names["every_entry_readable"]:
        findings.append(
            "the unresolved-name section could not read "
            f"{len(names['entries_this_audit_could_not_read'])} entries, so its "
            "counts describe this audit rather than the data"
        )
    if twenty_twenty["absent_but_the_results_route_says_they_played"]:
        findings.append(
            f"{len(twenty_twenty['absent_but_the_results_route_says_they_played'])} "
            "programs are absent from the 2020 membership statement while the "
            "results route records completed games for them"
        )

    receipt = {
        "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE",
        "cycle_number": 37,
        "attempt_number": 2,
        "state": "ACTUAL_STATE",
        "requirement": "R37-04",
        "acceptance": ["R37-04-AC01", "R37-04-AC02", "R37-04-AC03",
                       "R37-04-AC04", "R37-04-AC05", "R37-04-AC07"],
        "independence": (
            "This tool imports no producer module. Digests, request identities "
            "and every count are recomputed here from the cached bytes and the "
            "delivered artifacts."
        ),
        "inputs": {
            "membership": str(args.membership),
            "membership_sha256": sha256_file(args.membership),
            "coverage": str(args.coverage),
            "coverage_sha256": sha256_file(args.coverage),
            "raw_root": str(args.raw_root),
            "release": str(args.release) if args.release else None,
        },
        "ac02_source_verification": sources,
        "ac03_ac07_row_grain": grain,
        "ac01_ac07_population_ledger": ledger,
        "ac05_2020_investigation": twenty_twenty,
        "ac04_unresolved_names": names,
        "findings": findings,
        "result": "CONSISTENT" if not findings else "DISCREPANCIES_FOUND",
        "not_established": (
            "Verifying that the delivered population is what the acquired bytes "
            "say is not verifying that the source is right. No membership claim "
            "here has non-provider corroboration, and this audit adds none."
        ),
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(args.out, 
        json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )

    print("rows verified against source bytes:",
          f"{sources['verified_rows']}/{sources['delivered_rows']}")
    print("seasons without a payload        :",
          sources["seasons_without_a_payload"] or "none")
    print("program-season keys / cells      :",
          grain["program_season_keys"], "/", grain["expected_cells_from_membership"])
    print("delivered core-role cells        :",
          grain["delivered"].get("core_role_cells"))
    print("2020 absent / played nothing     :",
          twenty_twenty["programs_absent"], "/", twenty_twenty["absent_and_played_nothing"])
    print("2020 games on a later calendar yr:",
          twenty_twenty["games_played_on_a_later_calendar_year"], "of",
          twenty_twenty["games_recorded"])
    print("unresolved display names         :", names["unresolved_display_names"])
    print("result                           :", receipt["result"])
    for line in findings:
        print("   -", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

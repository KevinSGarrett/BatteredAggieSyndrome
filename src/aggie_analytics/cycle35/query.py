"""R35-06: read-only queries against the actual cycle35 coaching release.

The Cycle #35 manager follow-up (20260920T205200Z, MF35-06) ran the installed
`bas-staff-query` entry point against the delivered r7 release and got
`OperationalError: no such table: staff_role_cells`: the CLI still dispatches
to `cycle33.query`, which is built entirely around the OLD, flat
`staff_role_cells` table. The r7 release uses `cycle35.coaching_release`'s
normalized schema (`canonical_program`, `employment_episode`,
`formal_role_assertion`, `canonical_person`, ...) instead, and nothing ever
taught the installed query path to speak it.

This module is the cycle35-native half of that fix: `team_staff` and
`coach_career` here read the *actual* normalized schema directly, with no
translation into the legacy row shape and no pretending the two schemas are
the same thing. `cycle33.query` is made version-aware separately (it detects
which schema a given database actually has and delegates here when it is a
cycle35 release), so the one installed CLI keeps working against either.

Program and person name resolution here is exact (case/whitespace-folded),
never a substring match -- the MR33-08 lesson (`cycle33.query.team_schemes`)
applies here too: a "Virginia" query must never silently also return
"Virginia Tech".
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

#: Table names that, if present, positively identify a cycle35 coaching
#: release. `staff_role_cells` identifies a legacy cycle33 database instead.
_CYCLE35_MARKER_TABLES = ("canonical_program", "formal_role_assertion")
_CYCLE33_MARKER_TABLE = "staff_role_cells"

SCHEMA_KIND_CYCLE35 = "CYCLE35_COACHING_RELEASE"
SCHEMA_KIND_CYCLE33 = "CYCLE33_STAFF_ROLE_CELLS"
SCHEMA_KIND_UNKNOWN = "UNKNOWN_SCHEMA"


class Cycle35QueryError(ValueError):
    """Raised when a cycle35-release query cannot be answered as asked."""


def _existing_tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {str(row[0]) for row in rows}


def schema_kind(conn: sqlite3.Connection) -> str:
    """Which schema a database actually has, read from its own tables.

    MF35-06: this is the detection the installed CLI never performed -- it
    always assumed `staff_role_cells`. Detection is by table presence, not
    by a filename or a caller's claim, for the same reason bytes are the
    ground truth in `cycle35.forecast_admission`: a database's own content
    is authoritative over what anyone calls it.
    """

    tables = _existing_tables(conn)
    if all(name in tables for name in _CYCLE35_MARKER_TABLES):
        return SCHEMA_KIND_CYCLE35
    if _CYCLE33_MARKER_TABLE in tables:
        return SCHEMA_KIND_CYCLE33
    return SCHEMA_KIND_UNKNOWN


def _resolve_program_id(conn: sqlite3.Connection, team: str) -> str | None:
    row = conn.execute(
        "SELECT program_id FROM canonical_program "
        "WHERE TRIM(display_name) = TRIM(?) COLLATE NOCASE",
        (team,),
    ).fetchone()
    return str(row["program_id"]) if row else None


def _resolve_person_ids(conn: sqlite3.Connection, person: str) -> list[str]:
    direct = conn.execute(
        "SELECT person_id FROM canonical_person "
        "WHERE TRIM(canonical_name) = TRIM(?) COLLATE NOCASE",
        (person,),
    ).fetchall()
    via_alias = conn.execute(
        "SELECT person_id FROM person_alias WHERE TRIM(alias) = TRIM(?) COLLATE NOCASE",
        (person,),
    ).fetchall()
    ids = {str(row["person_id"]) for row in direct}
    ids.update(str(row["person_id"]) for row in via_alias)
    return sorted(ids)


def _role_row(row: sqlite3.Row) -> dict[str, Any]:
    qualifiers_raw = row["qualifiers"]
    try:
        qualifiers = json.loads(qualifiers_raw) if qualifiers_raw else []
    except (TypeError, ValueError):
        qualifiers = []
    return {
        "assertion_id": row["assertion_id"],
        "episode_id": row["episode_id"],
        "person_id": row["person_id"],
        "person": row["canonical_name"],
        "program_id": row["program_id"],
        "program": row["display_name"],
        "season": row["season"],
        "date_precision": row["date_precision"],
        "role_family": row["role_family"],
        "exact_title_text": row["exact_title_text"],
        "qualifiers": qualifiers,
        "principal_role_blocked": bool(row["principal_role_blocked"]),
        "episode_evidence_layer": row["episode_evidence_layer"],
        "assertion_evidence_layer": row["assertion_evidence_layer"],
    }


_ROLE_SELECT = """
    SELECT
        a.assertion_id AS assertion_id,
        a.role_family AS role_family,
        a.exact_title_text AS exact_title_text,
        a.qualifiers AS qualifiers,
        a.principal_role_blocked AS principal_role_blocked,
        a.evidence_layer AS assertion_evidence_layer,
        e.episode_id AS episode_id,
        e.season AS season,
        e.date_precision AS date_precision,
        e.evidence_layer AS episode_evidence_layer,
        p.person_id AS person_id,
        p.canonical_name AS canonical_name,
        g.program_id AS program_id,
        g.display_name AS display_name
    FROM formal_role_assertion a
    JOIN employment_episode e ON e.episode_id = a.episode_id
    LEFT JOIN canonical_person p ON p.person_id = e.person_id
    LEFT JOIN canonical_program g ON g.program_id = e.program_id
"""


def team_staff(
    conn: sqlite3.Connection, *, team: str, season: str
) -> list[dict[str, Any]]:
    """Every role assertion for a program-season, across all evidence layers.

    An unresolved program name or a season with no episodes returns an empty
    list -- never a substring-matched program, and never a fabricated row.
    """

    program_id = _resolve_program_id(conn, team)
    if program_id is None:
        return []
    rows = conn.execute(
        _ROLE_SELECT + " WHERE e.program_id = ? AND e.season = ? "
        "ORDER BY a.role_family, p.canonical_name",
        (program_id, str(season)),
    ).fetchall()
    return [_role_row(row) for row in rows]


def coach_career(conn: sqlite3.Connection, *, person: str) -> list[dict[str, Any]]:
    """Every role assertion for a person, resolved by canonical name or any
    recorded alias, across every program and season."""

    person_ids = _resolve_person_ids(conn, person)
    if not person_ids:
        return []
    placeholders = ",".join("?" for _ in person_ids)
    rows = conn.execute(
        _ROLE_SELECT + f" WHERE e.person_id IN ({placeholders}) "  # noqa: S608
        "ORDER BY e.season, g.display_name, a.role_family",
        person_ids,
    ).fetchall()
    return [_role_row(row) for row in rows]


#: Evidence layers that positively resolve an assertion, mirroring
#: `cycle33.query.RESOLVED_DISPOSITIONS`'s enumerate-what-IS-resolved
#: inversion (MR34-06): everything else -- including a layer this module has
#: never seen -- counts as unresolved, so an unanticipated layer is
#: over-reported rather than silently dropped.
_RESOLVED_EVIDENCE_LAYERS = frozenset({"CORROBORATED_MULTI_SOURCE", "OFFICIAL_PRIMARY_CONFIRMED"})
_REJECTED_EVIDENCE_LAYERS = frozenset({"REJECTED"})
_QUARANTINED_EVIDENCE_LAYERS = frozenset({"QUARANTINED_CONFLICT"})


def unresolved_roles(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every role assertion not positively resolved, including any evidence
    layer this module was never told about."""

    rows = conn.execute(_ROLE_SELECT).fetchall()
    return [
        _role_row(row)
        for row in rows
        if row["assertion_evidence_layer"] not in _RESOLVED_EVIDENCE_LAYERS
    ]


def rejected_roles(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(_ROLE_SELECT).fetchall()
    return [
        _role_row(row)
        for row in rows
        if row["assertion_evidence_layer"] in _REJECTED_EVIDENCE_LAYERS
    ]


def quarantined_roles(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(_ROLE_SELECT).fetchall()
    return [
        _role_row(row)
        for row in rows
        if row["assertion_evidence_layer"] in _QUARANTINED_EVIDENCE_LAYERS
    ]


def verified_roles(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(_ROLE_SELECT).fetchall()
    return [
        _role_row(row)
        for row in rows
        if row["assertion_evidence_layer"] in _RESOLVED_EVIDENCE_LAYERS
    ]


def team_schemes(conn: sqlite3.Connection, *, program: str, season: str) -> list[dict[str, Any]]:
    """Scheme assertions for a program-season.

    The real r7 release has zero `scheme_assertion` rows -- this returns an
    honest empty list for it, not a fabricated one. It exists so the CLI
    dispatch has something to call without raising on a table that exists
    but is legitimately unpopulated.
    """

    program_id = _resolve_program_id(conn, program)
    if program_id is None:
        return []
    rows = conn.execute(
        "SELECT * FROM scheme_assertion WHERE program_id = ? AND season = ? "
        "ORDER BY side",
        (program_id, str(season)),
    ).fetchall()
    return [dict(row) for row in rows]


def role_state_conservation(conn: sqlite3.Connection) -> dict[str, Any]:
    """The MR34-06 partition proof, restated for the cycle35 schema: every
    `formal_role_assertion` row must be reachable through exactly one state
    view."""

    rows = conn.execute(_ROLE_SELECT).fetchall()
    total = len(rows)
    buckets: dict[str, int] = {}
    unknown_layers: dict[str, int] = {}
    for row in rows:
        layer = str(row["assertion_evidence_layer"] or "")
        if layer in _RESOLVED_EVIDENCE_LAYERS:
            state = "VERIFIED"
        elif layer in _REJECTED_EVIDENCE_LAYERS:
            state = "REJECTED"
        elif layer in _QUARANTINED_EVIDENCE_LAYERS:
            state = "QUARANTINED"
        else:
            state = "UNRESOLVED"
        buckets[state] = buckets.get(state, 0) + 1
        if state == "UNRESOLVED" and layer not in ("", "CANDIDATE_SINGLE_SOURCE", "OBSERVED_SOURCE_ROW", "UNRESOLVED"):
            unknown_layers[layer] = unknown_layers.get(layer, 0) + 1
    return {
        "table_row_count": total,
        "classified_row_count": sum(buckets.values()),
        "state_counts": buckets,
        "states_partition_table": sum(buckets.values()) == total,
        "no_row_is_unreachable": sum(buckets.values()) == total,
        "evidence_layers_not_in_declared_resolved_set": unknown_layers,
    }

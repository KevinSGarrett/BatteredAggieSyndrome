r"""Read-only research queries against the delivered national release.

V37-01 repair. The installed ``bas-staff-query`` entry point knew two
schemas: the flat Cycle 33 ``staff_role_cells`` table and the Cycle 35
coaching release. The Cycle 36 *national* release is neither -- it carries
``canonical_program`` but not ``formal_role_assertion`` -- so
``cycle35.query.schema_kind`` returned ``UNKNOWN_SCHEMA`` and the installed
consumer exited 1 against the very database the cycle delivered.

Two separate honesty problems are fixed here, not one:

1. **The national schema is spoken natively.** Nothing is translated into
   another release's row shape. A ``staff_observation`` carries a rejection
   reason, an evidence tier and a PIT flag that a flat cell cannot express,
   and flattening them would be a different kind of wrong answer than
   exiting 1.

2. **An unmatched key is not an empty answer.** Asking the published Cycle
   35 release for season ``2024`` returned ``[]`` with exit 0, but that
   release's only season value is ``CURRENT``: the query was unanswerable
   and said "none". Every lookup here reports whether the program and the
   season it was given actually exist in the database, so "no rows for a
   real key" and "that key is not in this release" are distinguishable at
   the consumer.

Program resolution is exact over the release's own alias table, never a
substring match: a query for ``Ohio`` must not return ``Ohio State``, and a
query for ``Texas A&M`` must not return ``East Texas A&M``.

MF37A02-04 repair (Cycle 37 Attempt 3). The corrected release carries
``career_episode_successor`` and ``responsibility_successor`` beside the
retained predecessor tables ``career_episode`` and
``responsibility_assertion``, but the career and responsibility queries
here named the predecessor tables. The installed CLI therefore returned
Bill Anderson's predecessor row whose title is the state qualifier ``TX``
although the delivered correction reads the employer as
``Stamford HS (TX)``. Direct SQL against the corrected tables was the only
way to see the correction, which is not a delivered consumer.

Table selection is now a version dispatch, not a table name:

* the release's own ``release_version`` must be registered in
  :data:`RELEASE_VERSION_REGISTRY`; an absent or unregistered version is
  refused instead of being answered from whichever tables happen to exist;
* a corrected release declares each successor table in its own
  ``release_lineage`` (``successor_table::<name>::ledger_sha256``). A
  declared successor is selected by default (``CORRECTED_SUCCESSOR``). The
  predecessor rows stay reachable only through the explicit
  ``LEGACY_PREDECESSOR_AUDIT`` mode, labelled superseded and joined to
  their old-to-new disposition;
* a release that declares no successor answers from its own tables
  (``PREDECESSOR_ONLY_RELEASE``), so older releases stay readable with the
  row shape they always had;
* a successor table that is declared but absent, present but undeclared,
  declared without its companion table, or missing a column the query
  reads is refused by name.

Career, responsibility and scheme answers are paged with an exact
``total_count`` for the filter and the selected table's full row count, so
a caller can prove it has read every row. Corrected rows carry a source
locator back to the raw bytes they were parsed from.
"""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any, Iterable, Sequence

__all__ = [
    "DEFAULT_PAGE_LIMIT",
    "MODE_CORRECTED_SUCCESSOR",
    "MODE_LEGACY_PREDECESSOR_AUDIT",
    "MODE_PREDECESSOR_ONLY_RELEASE",
    "RELEASE_DISPATCH_VERSION",
    "RELEASE_VERSION_REGISTRY",
    "SCHEMA_KIND_CYCLE36",
    "Cycle36QueryError",
    "ReleaseDispatchError",
    "career_listing",
    "coach_career",
    "coverage",
    "is_cycle36_release",
    "program_seasons",
    "provenance",
    "release_dispatch",
    "release_identity",
    "release_version_binding",
    "responsibilities",
    "resolve_program",
    "schemes",
    "season_division_population",
    "team_staff",
    "unresolved_records",
]

SCHEMA_KIND_CYCLE36 = "CYCLE36_NATIONAL_RELEASE"

#: Tables that together identify a national release. ``core_role_cell`` and
#: ``program_season_membership`` are the two no other delivered schema has.
_MARKER_TABLES = (
    "canonical_program",
    "program_season_membership",
    "core_role_cell",
    "staff_observation",
)


class Cycle36QueryError(ValueError):
    """Raised when a national-release query cannot be answered as asked."""


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def is_cycle36_release(conn: sqlite3.Connection) -> bool:
    return all(name in _tables(conn) for name in _MARKER_TABLES)


def _rows(conn: sqlite3.Connection, sql: str, parameters: Iterable[Any] = ()) -> list[dict[str, Any]]:
    previous = conn.row_factory
    conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute(sql, tuple(parameters))]
    finally:
        conn.row_factory = previous


def _normalize(value: str) -> str:
    return " ".join(str(value).split()).casefold()


#: Columns a corrected successor adds to ``staff_observation``. A query has
#: to return them or the correction is invisible to the consumer: R37-07-AC04
#: requires original values and conflict rows to survive into query results,
#: and a release that records the original program while the CLI never shows
#: it is only half a repair. They are selected conditionally so the same
#: consumer still reads the uncorrected predecessor.
_LINEAGE_COLUMNS = (
    "original_program_id",
    "binding_state",
    "binding_reason",
    "admitted_for_coverage",
)


def _lineage_columns(conn: sqlite3.Connection, prefix: str = "") -> str:
    """Selectable lineage columns, qualified for the caller's own alias.

    ``prefix`` is the table alias the caller used. ``team_staff`` joins and
    aliases the table ``o``; ``provenance`` does not alias it at all, and
    hard-coding ``o.`` made that query raise ``no such column``.
    """

    present = {
        str(row[1]) for row in conn.execute('PRAGMA table_info("staff_observation")')
    }
    available = [name for name in _LINEAGE_COLUMNS if name in present]
    qualifier = f"{prefix}." if prefix else ""
    return "".join(f"{qualifier}{name}, " for name in available) if available else ""


def release_identity(conn: sqlite3.Connection) -> dict[str, Any]:
    """The release's own identity rows, as the release states them."""

    return {
        str(row["key"]): row["value"]
        for row in _rows(conn, "SELECT key, value FROM release_identity")
    }


# --------------------------------------------------------------------------
# Version dispatch (MF37A02-04)
# --------------------------------------------------------------------------

RELEASE_DISPATCH_VERSION = "BAS-RELEASE-QUERY-DISPATCH-v37.3"

MODE_CORRECTED_SUCCESSOR = "CORRECTED_SUCCESSOR"
MODE_LEGACY_PREDECESSOR_AUDIT = "LEGACY_PREDECESSOR_AUDIT"
MODE_PREDECESSOR_ONLY_RELEASE = "PREDECESSOR_ONLY_RELEASE"
#: Cycle #37 - Attempt #4 (R37A04-06): a career successor file the caller names explicitly. Never a default.
MODE_EXPLICIT_CAREER_SUCCESSOR = "EXPLICIT_CAREER_SUCCESSOR"
REFUSED_SUCCESSOR_WITH_LEGACY_AUDIT = "REFUSED_EXPLICIT_SUCCESSOR_AND_LEGACY_AUDIT_ARE_EXCLUSIVE"
REFUSED_UNKNOWN_UNCERTAINTY_CLASS = "REFUSED_UNKNOWN_UNCERTAINTY_CLASS"

LINEAGE_ABSENT = "RELEASE_HAS_NO_LINEAGE_TABLE"
LINEAGE_REQUIRED = "RELEASE_LINEAGE_TABLE_REQUIRED"

#: Every national release version this consumer answers, by the exact
#: ``release_version`` the release states about itself. A version is never
#: inferred from which tables exist: an unregistered version is refused.
RELEASE_VERSION_REGISTRY: dict[str, dict[str, str]] = {
    "BAS-CYCLE36-NATIONAL-RELEASE-v36.1": {
        "family": "CYCLE36_NATIONAL_RELEASE",
        "lineage": LINEAGE_ABSENT,
    },
    "BAS-CYCLE37-CORRECTED-NATIONAL-RELEASE-v37.1": {
        "family": "CYCLE37_CORRECTED_NATIONAL_RELEASE",
        "lineage": LINEAGE_REQUIRED,
    },
    "BAS-CYCLE37-CORRECTED-NATIONAL-RELEASE-v37.2-STAFF-REPARSE": {
        "family": "CYCLE37_CORRECTED_NATIONAL_RELEASE",
        "lineage": LINEAGE_REQUIRED,
    },
}

REFUSED_RELEASE_IDENTITY_TABLE_ABSENT = "REFUSED_RELEASE_IDENTITY_TABLE_ABSENT"
REFUSED_RELEASE_VERSION_NOT_DECLARED = "REFUSED_RELEASE_VERSION_NOT_DECLARED"
REFUSED_RELEASE_VERSION_NOT_SUPPORTED = "REFUSED_RELEASE_VERSION_NOT_SUPPORTED"
REFUSED_LINEAGE_NOT_DECLARED_BY_VERSION = "REFUSED_LINEAGE_NOT_DECLARED_BY_VERSION"
REFUSED_LINEAGE_VERSION_DISAGREES = "REFUSED_LINEAGE_VERSION_DISAGREES"
REFUSED_REQUIRED_TABLES_ABSENT = "REFUSED_REQUIRED_TABLES_ABSENT"
REFUSED_REQUIRED_COLUMNS_ABSENT = "REFUSED_REQUIRED_COLUMNS_ABSENT"
REFUSED_UNDECLARED_SUCCESSOR_TABLE = "REFUSED_UNDECLARED_SUCCESSOR_TABLE"
REFUSED_SUCCESSOR_DECLARATION_INCOMPLETE = "REFUSED_SUCCESSOR_DECLARATION_INCOMPLETE"
REFUSED_FILTER_NOT_CARRIED_BY_SELECTED_TABLE = "REFUSED_FILTER_NOT_CARRIED_BY_SELECTED_TABLE"
REFUSED_INVALID_PAGINATION = "REFUSED_INVALID_PAGINATION"
REFUSED_SEASON_IS_NOT_AN_INTEGER = "REFUSED_SEASON_IS_NOT_AN_INTEGER"

#: Successor tables a corrected answer needs together, per dataset. A career
#: correction without its disposition table cannot show old-to-new lineage,
#: so a release declaring one without the other is refused.
CAREER_SUCCESSOR_TABLES = ("career_episode_successor", "career_predecessor_disposition")
RESPONSIBILITY_SUCCESSOR_TABLES = ("responsibility_successor",)

_DATASETS: dict[str, tuple[str, tuple[str, ...]]] = {
    "career": ("career_episode", CAREER_SUCCESSOR_TABLES),
    "responsibility": ("responsibility_assertion", RESPONSIBILITY_SUCCESSOR_TABLES),
}

#: Row identity per selected table: pagination is ordered on it and a caller
#: reconciles pages against the table by it.
_ROW_IDENTITY = {
    "career_episode": "career_episode_id",
    "career_episode_successor": "episode_id",
    "responsibility_assertion": "responsibility_id",
    "responsibility_successor": "successor_key",
}

#: Columns each query reads. Answers select every column of their row, so a
#: correction's extra fields are never dropped; these are the ones whose
#: absence would change the answer, and they are checked before querying.
_REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "career_episode": (
        "career_episode_id", "span_id", "pageid", "page_title", "wikidata_qid",
        "wikimedia_revision", "episode_index", "person_display_name", "employer_raw",
        "employer_resolution_state", "employer_program_id", "source_title", "role_codes",
        "start_year", "end_year", "ongoing", "source_year_text", "evidence_class",
        "state", "flags", "joined", "pit_admitted",
    ),
    "career_episode_successor": (
        "episode_id", "pageid", "page_title", "person_display", "wikidata_qid",
        "revision", "family", "row_index", "interval_index", "employer_display",
        "employer_kind", "assignments", "start", "end", "ongoing", "years_as_written",
        "classification", "resolution", "population_state", "evidence_class",
        "pit_admitted", "raw_file", "raw_file_sha256", "wikitext_sha256",
        "team_char_span", "team_byte_span", "team_raw", "years_char_span", "years_raw",
    ),
    "career_predecessor_disposition": (
        "predecessor_span_id", "pageid", "row_index", "state", "changes",
        "reparse_episode_ids",
    ),
    "responsibility_assertion": (
        "responsibility_id", "person", "program_id", "season", "source_title",
        "evidence_code", "disposition", "inferred_from_role_title", "pit_admitted",
    ),
    "responsibility_successor": (
        "successor_key", "release_responsibility_id", "predecessor_row_index",
        "predecessor_version", "predecessor_disposition", "predecessor_evidence_code",
        "responsibility_version", "source_kind", "person", "program_id", "season",
        "source_title", "evidence_code", "disposition", "capture_path",
        "payload_sha256", "observation_id", "wiki_file", "revision_id",
        "offset_in_plain_text", "offset_in_rendered_text",
    ),
}

_LINEAGE_SUCCESSOR_KEY = re.compile(r"^successor_table::([a-z][a-z0-9_]*)::ledger_sha256$")

#: The lineage facts every dispatched answer repeats, when the release has them.
_LINEAGE_FACTS = (
    "predecessor_sha256",
    "predecessor_path",
    "predecessor_modified",
    "correction_ledger_sha256",
    "activation_state",
)

DEFAULT_PAGE_LIMIT = 500


class ReleaseDispatchError(Cycle36QueryError):
    """A dispatch refusal. ``code`` is stable; the message names the cause."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f'PRAGMA table_info("{table}")')}


def _require_columns(conn: sqlite3.Connection, table: str) -> None:
    present = _columns(conn, table)
    missing = [name for name in _REQUIRED_COLUMNS[table] if name not in present]
    if missing:
        raise ReleaseDispatchError(
            REFUSED_REQUIRED_COLUMNS_ABSENT,
            f"table {table} lacks column(s) {missing} that this query reads; "
            "answering without them would silently drop part of each row",
        )


def _count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])


def release_version_binding(conn: sqlite3.Connection) -> dict[str, Any]:
    """The release's declared version, checked against the registry.

    Refuses a release with no identity table, no declared version, an
    unregistered version, a lineage table its version does not declare, or
    a lineage that names a different successor version.
    """

    tables = _tables(conn)
    if "release_identity" not in tables:
        raise ReleaseDispatchError(
            REFUSED_RELEASE_IDENTITY_TABLE_ABSENT,
            "the database has no release_identity table, so its release version "
            "cannot be read and no table can be selected for it",
        )
    identity = release_identity(conn)
    version = identity.get("release_version")
    if version is None or not str(version).strip():
        raise ReleaseDispatchError(
            REFUSED_RELEASE_VERSION_NOT_DECLARED,
            f"release_identity declares no release_version (keys present: "
            f"{sorted(identity)}); table selection is by declared version, not by guess",
        )
    version = str(version)
    entry = RELEASE_VERSION_REGISTRY.get(version)
    if entry is None:
        raise ReleaseDispatchError(
            REFUSED_RELEASE_VERSION_NOT_SUPPORTED,
            f"release_version {version!r} is not registered; registered versions: "
            f"{sorted(RELEASE_VERSION_REGISTRY)}",
        )
    lineage: dict[str, Any] = {}
    if entry["lineage"] == LINEAGE_REQUIRED:
        if "release_lineage" not in tables:
            raise ReleaseDispatchError(
                REFUSED_REQUIRED_TABLES_ABSENT,
                f"release_version {version} requires a release_lineage table and "
                "this database has none",
            )
        lineage = {
            str(row["key"]): row["value"]
            for row in _rows(conn, "SELECT key, value FROM release_lineage")
        }
        declared = lineage.get("successor_release_version")
        if declared != version:
            raise ReleaseDispatchError(
                REFUSED_LINEAGE_VERSION_DISAGREES,
                f"release_identity says {version!r} but release_lineage names "
                f"successor_release_version {declared!r}",
            )
    elif "release_lineage" in tables:
        raise ReleaseDispatchError(
            REFUSED_LINEAGE_NOT_DECLARED_BY_VERSION,
            f"release_version {version} declares no lineage, yet the database "
            "carries a release_lineage table; its successor claims are not "
            "part of the version this consumer knows",
        )
    successors: dict[str, Any] = {}
    for key, value in lineage.items():
        match = _LINEAGE_SUCCESSOR_KEY.match(key)
        if match:
            successors[match.group(1)] = value
    return {
        "dispatch_version": RELEASE_DISPATCH_VERSION,
        "release_version": version,
        "release_family": entry["family"],
        "lineage_rule": entry["lineage"],
        "release_identity": identity,
        "declared_successor_tables": dict(sorted(successors.items())),
        "lineage": {name: lineage[name] for name in _LINEAGE_FACTS if name in lineage},
    }


_MODE_NOTES = {
    MODE_CORRECTED_SUCCESSOR: (
        "Rows come from the delivered correction. The superseded predecessor "
        "rows are reachable only through the explicit legacy audit mode."
    ),
    MODE_LEGACY_PREDECESSOR_AUDIT: (
        "SUPERSEDED predecessor rows returned for audit, each joined to its "
        "old-to-new disposition. They are not the corrected answer."
    ),
    MODE_PREDECESSOR_ONLY_RELEASE: (
        "This release declares no successor for this dataset, so its own "
        "table is its only answer."
    ),
}


def _dataset_selection(
    conn: sqlite3.Connection,
    binding: dict[str, Any],
    *,
    dataset: str,
    legacy_audit: bool,
) -> dict[str, Any]:
    predecessor, successors = _DATASETS[dataset]
    tables = _tables(conn)
    declared = [name for name in successors if name in binding["declared_successor_tables"]]
    present = [name for name in successors if name in tables]
    if predecessor not in tables:
        raise ReleaseDispatchError(
            REFUSED_REQUIRED_TABLES_ABSENT,
            f"the {dataset} predecessor table {predecessor} is absent; every "
            "registered release retains it",
        )
    if not declared:
        if present:
            raise ReleaseDispatchError(
                REFUSED_UNDECLARED_SUCCESSOR_TABLE,
                f"table(s) {present} exist but release_lineage does not declare "
                f"them for {binding['release_version']}; an undeclared correction "
                "is neither selected nor silently ignored",
            )
        _require_columns(conn, predecessor)
        mode = MODE_PREDECESSOR_ONLY_RELEASE
        selected = predecessor
        successor_tables: list[str] = []
    else:
        if len(declared) != len(successors):
            raise ReleaseDispatchError(
                REFUSED_SUCCESSOR_DECLARATION_INCOMPLETE,
                f"release_lineage declares {declared} but a corrected {dataset} "
                f"answer needs {list(successors)} together",
            )
        missing = [name for name in successors if name not in tables]
        if missing:
            raise ReleaseDispatchError(
                REFUSED_REQUIRED_TABLES_ABSENT,
                f"release_lineage declares {missing} but the table(s) are absent",
            )
        for name in (predecessor, *successors):
            _require_columns(conn, name)
        mode = MODE_LEGACY_PREDECESSOR_AUDIT if legacy_audit else MODE_CORRECTED_SUCCESSOR
        selected = predecessor if legacy_audit else successors[0]
        successor_tables = list(successors)
    return {
        "dispatch_version": RELEASE_DISPATCH_VERSION,
        "dataset": dataset,
        "release_version": binding["release_version"],
        "release_family": binding["release_family"],
        "mode": mode,
        "mode_note": _MODE_NOTES[mode],
        "legacy_audit_requested": bool(legacy_audit),
        "selected_table": selected,
        "row_identity_field": _ROW_IDENTITY[selected],
        "selected_table_row_count": _count(conn, selected),
        "predecessor_table": predecessor,
        "predecessor_table_row_count": _count(conn, predecessor),
        "successor_tables": successor_tables,
        "successor_table_row_counts": {name: _count(conn, name) for name in successor_tables},
        "declared_ledger_sha256": {
            name: binding["declared_successor_tables"][name] for name in successor_tables
        },
        "lineage": binding["lineage"],
    }


def release_dispatch(conn: sqlite3.Connection, *, legacy_audit: bool = False) -> dict[str, Any]:
    """The whole dispatch decision for a release, as one inspectable record."""

    binding = release_version_binding(conn)
    return {
        **binding,
        "career": _dataset_selection(conn, binding, dataset="career", legacy_audit=legacy_audit),
        "responsibility": _dataset_selection(
            conn, binding, dataset="responsibility", legacy_audit=legacy_audit
        ),
    }


def _selection(conn: sqlite3.Connection, dataset: str, legacy_audit: bool) -> dict[str, Any]:
    return _dataset_selection(
        conn, release_version_binding(conn), dataset=dataset, legacy_audit=legacy_audit
    )


def _check_page(limit: int | None, offset: int) -> None:
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 1):
        raise ReleaseDispatchError(
            REFUSED_INVALID_PAGINATION, f"limit must be a positive integer or None (all), got {limit!r}"
        )
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise ReleaseDispatchError(
            REFUSED_INVALID_PAGINATION, f"offset must be a non-negative integer, got {offset!r}"
        )


def _pagination(total: int, offset: int, limit: int | None, returned: int) -> dict[str, Any]:
    end = offset + returned
    return {
        "total_count": total,
        "offset": offset,
        "limit": limit,
        "returned_count": returned,
        "next_offset": end if end < total else None,
        "is_last_page": end >= total,
    }


def _season_int(season: Any) -> int:
    try:
        return int(str(season).strip())
    except ValueError:
        raise ReleaseDispatchError(
            REFUSED_SEASON_IS_NOT_AN_INTEGER,
            f"season {season!r} is not an integer; career intervals are in years",
        ) from None


def _register_normalizer(conn: sqlite3.Connection) -> None:
    conn.create_function(
        "bas_release_query_normalize",
        1,
        lambda value: None if value is None else _normalize(value),
        deterministic=True,
    )


def _decode(value: Any) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return {"undecodable_stored_text": value}


def _chunks(values: Sequence[Any], size: int = 900) -> Iterable[Sequence[Any]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def _where(clauses: list[str]) -> str:
    return f"WHERE {' AND '.join(clauses)}" if clauses else ""


def _page_rows(
    conn: sqlite3.Connection,
    *,
    table: str,
    clauses: list[str],
    parameters: list[Any],
    order: str,
    limit: int | None,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    where = _where(clauses)
    total = int(
        conn.execute(f'SELECT COUNT(*) FROM "{table}" {where}', tuple(parameters)).fetchone()[0]
    )
    rows = _rows(
        conn,
        f'SELECT * FROM "{table}" {where} ORDER BY {order} LIMIT ? OFFSET ?',
        [*parameters, -1 if limit is None else limit, offset],
    )
    return total, rows


def resolve_program(conn: sqlite3.Connection, name: str) -> dict[str, Any]:
    """Resolve a program name exactly, reporting ambiguity rather than picking.

    ``display_names`` is a JSON array in this schema and ``program_alias``
    carries dated rename evidence, so both are consulted. A name matching
    more than one program is an explicit ambiguity, never a first-row choice.
    """

    wanted = _normalize(name)
    matches: dict[str, dict[str, Any]] = {}

    for row in _rows(
        conn, "SELECT program_id, display_names, in_football_population FROM canonical_program"
    ):
        try:
            names = json.loads(row["display_names"] or "[]")
        except ValueError:
            names = [row["display_names"]]
        if not isinstance(names, list):
            names = [names]
        if any(_normalize(candidate) == wanted for candidate in names if candidate):
            matches[str(row["program_id"])] = {
                "program_id": str(row["program_id"]),
                "display_names": names,
                "in_football_population": row["in_football_population"],
                "matched_on": "canonical_display_name",
            }

    for row in _rows(
        conn,
        "SELECT program_id, original_alias, normalized_alias, alias_basis, "
        "effective_state, effective_start, effective_end "
        "FROM program_alias",
    ):
        alias = row["normalized_alias"] or row["original_alias"] or ""
        if _normalize(alias) == wanted or _normalize(row["original_alias"] or "") == wanted:
            entry = matches.setdefault(
                str(row["program_id"]),
                {"program_id": str(row["program_id"]), "matched_on": "alias"},
            )
            entry.setdefault("aliases", []).append(
                {
                    "original_alias": row["original_alias"],
                    "alias_basis": row["alias_basis"],
                    "effective_state": row["effective_state"],
                    "effective_start": row["effective_start"],
                    "effective_end": row["effective_end"],
                }
            )

    collisions = _rows(
        conn,
        "SELECT normalized_alias, match_basis, program_ids, disposition "
        "FROM alias_collision WHERE LOWER(TRIM(normalized_alias)) = ?",
        (wanted,),
    )
    return {
        "requested": name,
        "normalized": wanted,
        "resolved": sorted(matches),
        "match_count": len(matches),
        "matches": [matches[key] for key in sorted(matches)],
        "ambiguous": len(matches) > 1,
        "known": bool(matches),
        "alias_collisions": collisions,
    }


def _season_known(conn: sqlite3.Connection, season: str) -> dict[str, Any]:
    present = _rows(
        conn,
        "SELECT season, programs, fbs, fcs, pre_classification, other_division, "
        "unknown, state FROM season_population WHERE CAST(season AS TEXT) = ?",
        (str(season),),
    )
    return {
        "requested": str(season),
        "known": bool(present),
        "population": present[0] if present else None,
    }


def team_staff(conn: sqlite3.Connection, *, team: str, season: str) -> dict[str, Any]:
    """Every observation and role assignment for one program-season.

    The return value is an envelope, not a bare list. An empty ``rows`` with
    ``program.known`` false means the name is not in this release; an empty
    ``rows`` with both keys known means the release genuinely holds nothing
    for them. The old shape could not tell those apart.
    """

    program = resolve_program(conn, team)
    season_state = _season_known(conn, season)
    rows: list[dict[str, Any]] = []
    if program["resolved"] and not program["ambiguous"]:
        program_id = program["resolved"][0]
        lineage = _lineage_columns(conn, "o")
        rows = _rows(
            conn,
            "SELECT o.observation_id, o.program_id, o.display_name, o.person, "
            "o.source_title, o.season, o.season_state, o.evidence_tier, "
            "o.source_class, o.pit_admitted, o.role_claim_supported, "
            "o.reject_reason, o.capture_path, o.payload_sha256, "
            + lineage +
            "a.assignment_id, a.role_code, a.unit, a.qualifiers, a.occupancy, "
            "a.taxonomy_version, a.is_core_role, a.play_caller_inferred "
            "FROM staff_observation o "
            "LEFT JOIN staff_role_assignment a ON a.observation_id = o.observation_id "
            "WHERE o.program_id = ? AND CAST(o.season AS TEXT) = ? "
            "ORDER BY o.observation_id, a.assignment_id",
            (program_id, str(season)),
        )
    return {
        "query": {"team": team, "season": str(season)},
        "program": program,
        "season": season_state,
        "answerable": bool(program["resolved"]) and not program["ambiguous"],
        "row_count": len(rows),
        "rows": rows,
        "unknowns_preserved": (
            "Observations with reject_reason or role_claim_supported = 0 are "
            "returned, not filtered: a rejected observation is evidence about "
            "the source, and omitting it would make the release look cleaner "
            "than it is."
        ),
    }


def program_seasons(conn: sqlite3.Connection, *, team: str) -> dict[str, Any]:
    program = resolve_program(conn, team)
    rows: list[dict[str, Any]] = []
    if program["resolved"] and not program["ambiguous"]:
        rows = _rows(
            conn,
            "SELECT season, classification, classification_bucket, conference, era, "
            "membership_authority FROM program_season_membership "
            "WHERE program_id = ? ORDER BY CAST(season AS INTEGER)",
            (program["resolved"][0],),
        )
    return {
        "query": {"team": team},
        "program": program,
        "answerable": bool(program["resolved"]) and not program["ambiguous"],
        "row_count": len(rows),
        "rows": rows,
    }


def season_division_population(
    conn: sqlite3.Connection, *, season: str, division: str | None = None
) -> dict[str, Any]:
    season_state = _season_known(conn, season)
    parameters: list[Any] = [str(season)]
    clause = "CAST(m.season AS TEXT) = ?"
    if division:
        clause += " AND UPPER(TRIM(m.classification_bucket)) = UPPER(TRIM(?))"
        parameters.append(division)
    rows = _rows(
        conn,
        "SELECT m.program_id, m.season, m.classification, m.classification_bucket, "
        "m.conference, m.era, m.membership_authority, p.display_names "
        "FROM program_season_membership m "
        "LEFT JOIN canonical_program p ON p.program_id = m.program_id "
        f"WHERE {clause} ORDER BY m.program_id",
        parameters,
    )
    buckets = _rows(
        conn,
        "SELECT classification_bucket, COUNT(*) AS n FROM program_season_membership "
        "WHERE CAST(season AS TEXT) = ? GROUP BY classification_bucket ORDER BY 1",
        (str(season),),
    )
    return {
        "query": {"season": str(season), "division": division},
        "season": season_state,
        "answerable": season_state["known"],
        "row_count": len(rows),
        "buckets_present_for_season": buckets,
        "rows": rows,
    }


# ------------------------------------------------------------ career rows

_CAREER_SUCCESSOR_ORDER = "pageid, family, row_index, interval_index, episode_id"
_CAREER_PREDECESSOR_ORDER = "CAST(COALESCE(start_year, 0) AS INTEGER), episode_index, career_episode_id"
_CAREER_PREDECESSOR_LISTING_ORDER = "career_episode_id, span_id"

#: The predecessor person query's exact historical column list, kept so an
#: older release answers in the row shape it always had.
_CAREER_PREDECESSOR_COLUMNS = (
    "career_episode_id, span_id, pageid, page_title, wikidata_qid, "
    "wikimedia_revision, episode_index, person_display_name, employer_raw, "
    "employer_resolution_state, employer_program_id, source_title, role_codes, "
    "start_year, end_year, ongoing, source_year_text, evidence_class, state, "
    "flags, joined, pit_admitted"
)


def _career_locator(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "WIKIMEDIA_REVISION_WIKITEXT",
        "raw_file": row.get("raw_file"),
        "raw_file_sha256": row.get("raw_file_sha256"),
        "pageid": row.get("pageid"),
        "revision": row.get("revision"),
        "wikitext_sha256": row.get("wikitext_sha256"),
        "row_index": row.get("row_index"),
        "interval_index": row.get("interval_index"),
        "team_char_span": _decode(row.get("team_char_span")),
        "team_byte_span": _decode(row.get("team_byte_span")),
        "team_raw": row.get("team_raw"),
        "years_char_span": _decode(row.get("years_char_span")),
        "years_raw": row.get("years_raw"),
        "parser_version": row.get("parser_version"),
        "note": (
            "team_char_span and years_char_span index the revision's wikitext "
            "(sha256 wikitext_sha256) inside raw_file; team_byte_span indexes "
            "its UTF-8 bytes."
        ),
    }


def _career_corrected_view(row: dict[str, Any]) -> dict[str, Any]:
    resolution = _decode(row.get("resolution")) or {}
    classification = _decode(row.get("classification")) or {}
    assignments = _decode(row.get("assignments")) or []
    if not isinstance(resolution, dict):
        resolution = {"undecodable_stored_value": resolution}
    if not isinstance(classification, dict):
        classification = {"undecodable_stored_value": classification}
    roles = (
        [item.get("role") for item in assignments if isinstance(item, dict)]
        if isinstance(assignments, list)
        else []
    )
    return {
        "family": row.get("family"),
        "employer": row.get("employer_display"),
        "employer_kind": row.get("employer_kind"),
        "employer_link_target": row.get("employer_link_target"),
        "program_id": resolution.get("program_id"),
        "program_resolution_state": resolution.get("state"),
        "roles": roles,
        "role_text": row.get("role_text"),
        "interval": {
            "start": row.get("start"),
            "end": row.get("end"),
            "ongoing": row.get("ongoing"),
            "as_written": row.get("years_as_written"),
        },
        "divisions": classification.get("divisions"),
        "division_by_season": classification.get("by_season"),
        "population_state": row.get("population_state"),
        "evidence_class": row.get("evidence_class"),
        "pit_admitted": row.get("pit_admitted"),
    }


def _dispositions_for_pages(
    conn: sqlite3.Connection, pageids: Sequence[Any]
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    wanted = sorted({str(pageid) for pageid in pageids if pageid is not None})
    for chunk in _chunks(wanted):
        marks = ",".join("?" for _ in chunk)
        found.extend(
            _rows(
                conn,
                "SELECT predecessor_span_id, pageid, row_index, state, changes, "
                "reparse_episode_ids FROM career_predecessor_disposition "
                f"WHERE CAST(pageid AS TEXT) IN ({marks}) "
                "ORDER BY pageid, row_index, predecessor_span_id",
                chunk,
            )
        )
    return found


def _disposition_view(row: dict[str, Any]) -> dict[str, Any]:
    episodes = _decode(row.get("reparse_episode_ids"))
    return {
        "predecessor_span_id": row.get("predecessor_span_id"),
        "predecessor_row_index": row.get("row_index"),
        "state": row.get("state"),
        "changes": _decode(row.get("changes")),
        "successor_episode_ids": episodes if isinstance(episodes, list) else episodes,
    }


def _enrich_career_successor(
    conn: sqlite3.Connection, rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Attach the corrected view, locator and old-to-new disposition.

    Returns the enriched rows and, for the same pages, the predecessor rows
    whose disposition maps to no successor episode, so a rejected
    predecessor row is reported rather than vanishing from the answer.
    """

    dispositions = _dispositions_for_pages(conn, [row.get("pageid") for row in rows])
    by_episode: dict[str, list[dict[str, Any]]] = {}
    orphans: list[dict[str, Any]] = []
    for disposition in dispositions:
        view = _disposition_view(disposition)
        episodes = view["successor_episode_ids"]
        if isinstance(episodes, list) and episodes:
            for episode in episodes:
                by_episode.setdefault(str(episode), []).append(view)
        else:
            orphans.append(view)
    enriched = []
    for row in rows:
        mapped = by_episode.get(str(row.get("episode_id")), [])
        enriched.append(
            {
                **row,
                "corrected": _career_corrected_view(row),
                "locator": _career_locator(row),
                "lineage_state": (
                    "DERIVED_FROM_PREDECESSOR_ROWS" if mapped else "NEW_IN_SUCCESSOR_NO_PREDECESSOR_ROW"
                ),
                "predecessor_dispositions": mapped,
            }
        )
    return enriched, orphans


def _enrich_career_legacy(
    conn: sqlite3.Connection, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    spans = [str(row.get("span_id")) for row in rows if row.get("span_id") is not None]
    by_span: dict[str, list[dict[str, Any]]] = {}
    for chunk in _chunks(sorted(set(spans))):
        marks = ",".join("?" for _ in chunk)
        for disposition in _rows(
            conn,
            "SELECT predecessor_span_id, pageid, row_index, state, changes, "
            "reparse_episode_ids FROM career_predecessor_disposition "
            f"WHERE predecessor_span_id IN ({marks})",
            chunk,
        ):
            by_span.setdefault(str(disposition["predecessor_span_id"]), []).append(
                _disposition_view(disposition)
            )
    return [
        {
            **row,
            "row_status": "SUPERSEDED_PREDECESSOR_ROW",
            "successor_disposition": by_span.get(str(row.get("span_id")), []),
        }
        for row in rows
    ]


def _career_filters_successor(
    *,
    program_id: str | None,
    season: int | None,
    division: str | None,
    role: str | None,
    family: str | None,
    person: str | None,
    pageid: Any,
) -> dict[str, tuple[str, list[Any]]]:
    filters: dict[str, tuple[str, list[Any]]] = {}
    if program_id is not None:
        filters["team"] = (
            "(CASE WHEN json_valid(resolution) THEN json_extract(resolution, '$.program_id') END) = ?",
            [program_id],
        )
    if season is not None:
        filters["season"] = (
            '(start IS NOT NULL AND start <= ? AND (("end" IS NOT NULL AND "end" >= ?) '
            'OR ("end" IS NULL AND ongoing = 1)))',
            [season, season],
        )
    if division is not None:
        if season is not None:
            filters["division"] = (
                "(CASE WHEN json_valid(classification) THEN "
                "lower(json_extract(classification, ?)) = lower(?) ELSE 0 END)",
                [f'$.by_season."{season}"', division],
            )
        else:
            filters["division"] = (
                "(CASE WHEN json_valid(classification) THEN EXISTS (SELECT 1 FROM "
                "json_each(classification, '$.divisions') WHERE lower(value) = lower(?)) "
                "ELSE 0 END)",
                [division],
            )
    if role is not None:
        filters["role"] = (
            "(CASE WHEN json_valid(assignments) THEN EXISTS (SELECT 1 FROM "
            "json_each(assignments) WHERE lower(json_extract(value, '$.role')) = lower(?)) "
            "ELSE 0 END)",
            [role],
        )
    if family is not None:
        filters["family"] = ("upper(family) = upper(?)", [family])
    if person is not None:
        wanted = _normalize(person)
        filters["person"] = (
            "(bas_release_query_normalize(page_title) = ? "
            "OR bas_release_query_normalize(person_display) = ?)",
            [wanted, wanted],
        )
    if pageid is not None:
        filters["pageid"] = ("CAST(pageid AS TEXT) = ?", [str(pageid)])
    return filters


#: For each filter that needs a value the row may lack, the rows that lack
#: it. They can match no value of that filter and are counted, not hidden.
def _missing_value_clauses(season: int | None) -> dict[str, str]:
    return {
        "season": "start IS NULL",
        "division": (
            "(CASE WHEN json_valid(classification) THEN "
            + (
                "json_extract(classification, ?) IS NULL"
                if season is not None
                else "NOT EXISTS (SELECT 1 FROM json_each(classification, '$.divisions'))"
            )
            + " ELSE 1 END)"
        ),
        "role": (
            "(CASE WHEN json_valid(assignments) THEN NOT EXISTS (SELECT 1 FROM "
            "json_each(assignments) WHERE json_extract(value, '$.role') IS NOT NULL) ELSE 1 END)"
        ),
    }


def _missingness(
    conn: sqlite3.Connection,
    table: str,
    filters: dict[str, tuple[str, list[Any]]],
    season: int | None,
) -> dict[str, int]:
    report: dict[str, int] = {}
    missing = _missing_value_clauses(season)
    for name, clause in missing.items():
        if name not in filters:
            continue
        others = [(sql, params) for key, (sql, params) in filters.items() if key != name]
        clauses = [sql for sql, _ in others] + [clause]
        parameters = [value for _, params in others for value in params]
        if name == "division" and season is not None:
            parameters.append(f'$.by_season."{season}"')
        report[f"rows_without_a_{name}_value_matching_the_other_filters"] = int(
            conn.execute(
                f'SELECT COUNT(*) FROM "{table}" {_where(clauses)}', tuple(parameters)
            ).fetchone()[0]
        )
    return report


def _explicit_successor_selection(
    conn: sqlite3.Connection, successor: dict[str, Any], *, legacy_audit: bool
) -> dict[str, Any]:
    """The dispatch record for an explicitly selected career successor (R37A04-06)."""

    if legacy_audit:
        raise ReleaseDispatchError(
            REFUSED_SUCCESSOR_WITH_LEGACY_AUDIT,
            "--legacy-audit reads the predecessor's own superseded table; a named career successor "
            "answers from its successor. Asking for both is refused rather than answered from one.",
        )
    base = _selection(conn, "career", False)
    from aggie_analytics.cycle37 import career_successor as cs  # noqa: PLC0415

    return {
        **base,
        "mode": MODE_EXPLICIT_CAREER_SUCCESSOR,
        "mode_note": (
            "Rows come from a career successor the caller named, bound to this release's exact digest. The "
            "release's own corrected table stays its default answer; this successor is not activated and "
            "not accepted."
        ),
        "selected_table": cs.VIEW_NAME,
        "row_identity_field": "episode_id",
        "selected_table_row_count": _count(conn, cs.VIEW_NAME),
        "delivered_default_table": base["selected_table"],
        "explicit_career_successor": successor,
    }


def _career_filters_explicit_successor(
    *,
    program_id: str | None,
    season: int | None,
    division: str | None,
    role: str | None,
    family: str | None,
    person: str | None,
    pageid: Any,
    uncertainty: str | None,
) -> dict[str, tuple[str, list[Any]]]:
    """The successor mode's filters: the corrected filters, with season membership on definite bounds.

    MF37A03-05: ``2009–?`` is certain only for 2009 and ``?–2009`` only for 2009; an ongoing interval
    covers every later season. A season filter answers from those certain seasons and never from an
    unknown end, which is neither closed nor ongoing.
    """

    filters = _career_filters_successor(
        program_id=program_id, season=None, division=division, role=role, family=family,
        person=person, pageid=pageid,
    )
    if season is not None:
        filters["season"] = (
            "(definite_first_season IS NOT NULL AND definite_first_season <= ? AND "
            "((definite_last_season IS NOT NULL AND definite_last_season >= ?) OR "
            "(definite_last_season IS NULL AND ongoing = 1)))",
            [season, season],
        )
        if division is not None:
            filters["division"] = (
                "(CASE WHEN json_valid(classification) THEN "
                "lower(json_extract(classification, ?)) = lower(?) ELSE 0 END)",
                [f'$.by_season."{season}"', division],
            )
    if uncertainty is not None:
        from aggie_analytics.cycle37 import career_successor as cs  # noqa: PLC0415

        if uncertainty not in cs.UNCERTAINTY_CLASSES:
            raise ReleaseDispatchError(
                REFUSED_UNKNOWN_UNCERTAINTY_CLASS,
                f"uncertainty class {uncertainty!r} is not one of {list(cs.UNCERTAINTY_CLASSES)}",
            )
        filters["uncertainty"] = (
            "(CASE WHEN json_valid(uncertainty_classes) THEN EXISTS (SELECT 1 FROM "
            "json_each(uncertainty_classes) WHERE value = ?) ELSE 0 END)",
            [uncertainty],
        )
    return filters


def _explicit_successor_missingness(
    conn: sqlite3.Connection, table: str, filters: dict[str, tuple[str, list[Any]]], season: int | None
) -> dict[str, int]:
    report: dict[str, int] = {}
    if season is None or "season" not in filters:
        return report
    others = [(sql, params) for key, (sql, params) in filters.items() if key not in ("season", "division")]
    clauses = [sql for sql, _ in others]
    parameters = [value for _, params in others for value in params]
    report["rows_without_a_definite_season_matching_the_other_filters"] = int(
        conn.execute(
            f'SELECT COUNT(*) FROM "{table}" {_where(clauses + ["definite_first_season IS NULL"])}',
            tuple(parameters),
        ).fetchone()[0]
    )
    maybe = (
        "(NOT (definite_first_season IS NOT NULL AND definite_first_season <= ? AND "
        "((definite_last_season IS NOT NULL AND definite_last_season >= ?) OR "
        "(definite_last_season IS NULL AND ongoing = 1))) "
        "AND json_array_length(uncertainty_classes) > 0 "
        "AND (possible_first_season IS NULL OR possible_first_season <= ?) "
        "AND (possible_last_season IS NULL OR possible_last_season >= ?))"
    )
    report["rows_whose_uncertain_bounds_may_cover_the_season_not_returned"] = int(
        conn.execute(
            f'SELECT COUNT(*) FROM "{table}" {_where(clauses + [maybe])}',
            tuple(parameters + [season, season, season, season]),
        ).fetchone()[0]
    )
    return report


_EXPLICIT_SUCCESSOR_JSON = (
    "predecessor_episode_ids", "start_bounds", "end_bounds", "uncertainty_classes",
    "unresolved_parentheticals", "employer_qualifier_kinds", "role_parentheticals",
    # Cycle #37 - Attempt #5: the Attempt 5 format's Attempt 4 lineage, date basis and unresolved date templates.
    "a04_episode_ids", "date_parent", "unresolved_date_templates",
)


def _enrich_explicit_successor(
    conn: sqlite3.Connection, rows: list[dict[str, Any]], selection: dict[str, Any]
) -> list[dict[str, Any]]:
    """Each successor row with its corrected view, raw locator, successor lineage and the predecessor rows
    it derives from -- both bindings, so the original and the corrected answer are read side by side.

    Cycle #37 - Attempt #5 (MF37A04-02): each served row's raw evidence is re-proved from the bytes (file, revision
    text and recorded spans); ``raw_file_sha256_verified`` reports that proof and is never a constant. An Attempt 5
    row also carries the Attempt 4 rows it supersedes and their mapping dispositions.
    """

    from aggie_analytics.cycle37 import career_successor as cs  # noqa: PLC0415

    verifier = cs.RawBytesVerifier()
    successor = selection["explicit_career_successor"]
    schema = successor.get("attached_schema", cs.ATTACHED_SCHEMA)
    disposition_table = successor.get("disposition_table", cs.DISPOSITION_TABLE)
    a04_table = successor.get("a04_table")
    predecessor_ids = sorted({
        str(identity)
        for row in rows
        for identity in (_decode(row.get("predecessor_episode_ids")) or [])
    })
    predecessors: dict[str, dict[str, Any]] = {}
    dispositions: dict[str, dict[str, Any]] = {}
    for chunk in _chunks(predecessor_ids):
        marks = ",".join("?" for _ in chunk)
        for row in _rows(conn, f"SELECT * FROM main.{cs.PREDECESSOR_TABLE} WHERE episode_id IN ({marks})", chunk):
            predecessors[str(row["episode_id"])] = row
        for row in _rows(
            conn,
            f"SELECT * FROM {schema}.{disposition_table} WHERE predecessor_episode_id IN ({marks})",
            chunk,
        ):
            dispositions[str(row["predecessor_episode_id"])] = row
    a04_rows: dict[str, dict[str, Any]] = {}
    if a04_table:
        a04_ids = sorted({str(i) for row in rows for i in (_decode(row.get("a04_episode_ids")) or [])})
        for chunk in _chunks(a04_ids):
            marks = ",".join("?" for _ in chunk)
            for row in _rows(conn, f"SELECT * FROM {schema}.{a04_table} WHERE a04_episode_id IN ({marks})", chunk):
                a04_rows[str(row["a04_episode_id"])] = row
    enriched = []
    for row in rows:
        verification = verifier.verify(row)
        parents = []
        for identity in _decode(row.get("predecessor_episode_ids")) or []:
            old = predecessors.get(str(identity))
            disposition = dispositions.get(str(identity)) or {}
            if old is None or cs.predecessor_row_digest(old) != disposition.get("predecessor_row_sha256"):
                raise cs.CareerSuccessorError(
                    cs.REFUSED_ROW_BINDING,
                    f"predecessor row {identity} no longer has the content digest the successor recorded",
                )
            parents.append({
                "predecessor_episode_id": identity,
                "disposition": disposition.get("disposition"),
                "changed_fields": _decode(disposition.get("changed_fields")),
                "screens": _decode(disposition.get("screens")),
                "reason": disposition.get("reason"),
                "predecessor_row_sha256": disposition.get("predecessor_row_sha256"),
                "predecessor_values": {
                    "employer_display": old.get("employer_display"),
                    "employer_qualifiers": _decode(old.get("employer_qualifiers")),
                    "role_text": old.get("role_text"),
                    "role_basis": old.get("role_basis"),
                    "assignments": _decode(old.get("assignments")),
                    "start": old.get("start"), "end": old.get("end"), "ongoing": old.get("ongoing"),
                    "years_as_written": old.get("years_as_written"),
                    "population_state": old.get("population_state"),
                    "parser_version": old.get("parser_version"),
                },
            })
        decoded = {key: _decode(row.get(key)) for key in _EXPLICIT_SUCCESSOR_JSON}
        corrected = _career_corrected_view(row)
        corrected["interval"].update({
            "start_state": row.get("start_state"), "end_state": row.get("end_state"),
            "start_bounds": decoded["start_bounds"], "end_bounds": decoded["end_bounds"],
            "definite_first_season": row.get("definite_first_season"),
            "definite_last_season": row.get("definite_last_season"),
            "possible_first_season": row.get("possible_first_season"),
            "possible_last_season": row.get("possible_last_season"),
        })
        corrected["role_basis"] = row.get("role_basis")
        corrected["unresolved_parentheticals"] = decoded["unresolved_parentheticals"]
        corrected["uncertainty_classes"] = decoded["uncertainty_classes"]
        if a04_table:
            corrected["date_basis"] = row.get("date_basis")
            corrected["date_parent"] = decoded["date_parent"]
            corrected["unresolved_date_templates"] = decoded["unresolved_date_templates"]
        served = {
            **row,
            "corrected": corrected,
            "locator": _career_locator(row),
            "successor_binding": {
                "successor_file_sha256": successor["successor_file_sha256"],
                "successor_version": successor["successor_version"],
                "successor_episode_id": row.get("episode_id"),
                "lineage_state": row.get("lineage_state"),
                "disposition": row.get("disposition"),
                "raw_file_sha256_verified": verification.get("raw_file_sha256") is True,
                "raw_verification": verification,
            },
            "predecessor_binding": {
                "database_sha256": successor["predecessor_database_sha256"],
                "table": cs.PREDECESSOR_TABLE,
                "rows": parents,
            },
        }
        if a04_table:
            served["a04_binding"] = {
                "a04_successor_sha256": successor.get("a04_successor_sha256"),
                "a04_lineage_state": row.get("a04_lineage_state"),
                "a04_disposition": row.get("a04_disposition"),
                "rows": [{"a04_episode_id": identity,
                          "disposition": (a04_rows.get(str(identity)) or {}).get("disposition"),
                          "changed_fields": _decode((a04_rows.get(str(identity)) or {}).get("changed_fields")),
                          "reason": (a04_rows.get(str(identity)) or {}).get("reason")}
                         for identity in decoded["a04_episode_ids"] or []],
            }
        enriched.append(served)
    return enriched


def _career_rows(
    conn: sqlite3.Connection,
    selection: dict[str, Any],
    *,
    program_id: str | None,
    season: int | None,
    division: str | None,
    role: str | None,
    family: str | None,
    person: str | None,
    pageid: Any,
    limit: int | None,
    offset: int,
    person_order: bool,
    uncertainty: str | None = None,
) -> dict[str, Any]:
    _check_page(limit, offset)
    table = selection["selected_table"]
    mode = selection["mode"]
    if mode == MODE_EXPLICIT_CAREER_SUCCESSOR:
        _register_normalizer(conn)
        filters = _career_filters_explicit_successor(
            program_id=program_id, season=season, division=division, role=role,
            family=family, person=person, pageid=pageid, uncertainty=uncertainty,
        )
        clauses = [sql for sql, _ in filters.values()]
        parameters = [value for _, params in filters.values() for value in params]
        total, rows = _page_rows(
            conn, table=table, clauses=clauses, parameters=parameters,
            order=_CAREER_SUCCESSOR_ORDER, limit=limit, offset=offset,
        )
        missingness = _missingness(
            conn, table, {k: v for k, v in filters.items() if k != "season"}, season
        )
        missingness.update(_explicit_successor_missingness(conn, table, filters, season))
        return {
            "total": total,
            "rows": _enrich_explicit_successor(conn, rows, selection),
            "predecessor_rows_without_successor_on_these_pages": [],
            "missingness": missingness,
            "filters_applied": sorted(filters),
        }
    if uncertainty is not None:
        raise ReleaseDispatchError(
            REFUSED_FILTER_NOT_CARRIED_BY_SELECTED_TABLE,
            f"an uncertainty class is carried only by an explicit career successor, not by {table} (mode {mode})",
        )
    if mode == MODE_CORRECTED_SUCCESSOR:
        _register_normalizer(conn)
        filters = _career_filters_successor(
            program_id=program_id, season=season, division=division, role=role,
            family=family, person=person, pageid=pageid,
        )
        clauses = [sql for sql, _ in filters.values()]
        parameters = [value for _, params in filters.values() for value in params]
        total, rows = _page_rows(
            conn, table=table, clauses=clauses, parameters=parameters,
            order=_CAREER_SUCCESSOR_ORDER, limit=limit, offset=offset,
        )
        enriched, orphans = _enrich_career_successor(conn, rows)
        return {
            "total": total,
            "rows": enriched,
            "predecessor_rows_without_successor_on_these_pages": orphans,
            "missingness": _missingness(conn, table, filters, season),
            "filters_applied": sorted(filters),
        }

    unsupported = [
        name for name, value in (("division", division), ("family", family)) if value is not None
    ]
    if unsupported:
        raise ReleaseDispatchError(
            REFUSED_FILTER_NOT_CARRIED_BY_SELECTED_TABLE,
            f"{unsupported} are not carried by {table} (mode {mode}); a predecessor "
            "career row has no division classification or episode family",
        )
    clauses: list[str] = []
    parameters: list[Any] = []
    if program_id is not None:
        clauses.append("employer_program_id = ?")
        parameters.append(program_id)
    if season is not None:
        clauses.append(
            "(start_year IS NOT NULL AND CAST(start_year AS INTEGER) <= ? AND "
            "((end_year IS NOT NULL AND CAST(end_year AS INTEGER) >= ?) OR "
            "(end_year IS NULL AND ongoing = 1)))"
        )
        parameters.extend([season, season])
    if role is not None:
        clauses.append(
            "(CASE WHEN json_valid(role_codes) THEN EXISTS (SELECT 1 FROM "
            "json_each(role_codes) WHERE lower(value) = lower(?)) ELSE 0 END)"
        )
        parameters.append(role)
    if person is not None:
        clauses.append("LOWER(TRIM(person_display_name)) = ?")
        parameters.append(_normalize(person))
    if pageid is not None:
        clauses.append("CAST(pageid AS TEXT) = ?")
        parameters.append(str(pageid))
    where = _where(clauses)
    total = int(
        conn.execute(f"SELECT COUNT(*) FROM career_episode {where}", tuple(parameters)).fetchone()[0]
    )
    order = _CAREER_PREDECESSOR_ORDER if person_order else _CAREER_PREDECESSOR_LISTING_ORDER
    rows = _rows(
        conn,
        f"SELECT {_CAREER_PREDECESSOR_COLUMNS} FROM career_episode {where} "
        f"ORDER BY {order} LIMIT ? OFFSET ?",
        [*parameters, -1 if limit is None else limit, offset],
    )
    if mode == MODE_LEGACY_PREDECESSOR_AUDIT:
        rows = _enrich_career_legacy(conn, rows)
    return {
        "total": total,
        "rows": rows,
        "predecessor_rows_without_successor_on_these_pages": None,
        "missingness": {},
        "filters_applied": sorted(
            name
            for name, value in (
                ("team", program_id), ("season", season), ("role", role),
                ("person", person), ("pageid", pageid),
            )
            if value is not None
        ),
    }


def coach_career(
    conn: sqlite3.Connection,
    *,
    person: str,
    legacy_audit: bool = False,
    pageid: Any = None,
    limit: int | None = None,
    offset: int = 0,
    career_successor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One person's career rows from the table the release version selects.

    A corrected release answers from ``career_episode_successor`` and
    matches the person on the page title or the display name; every
    matching identity is listed separately because a shared display name is
    not a shared person. ``legacy_audit`` returns the superseded predecessor
    rows with their disposition instead.
    """

    selection = (
        _explicit_successor_selection(conn, career_successor, legacy_audit=legacy_audit)
        if career_successor is not None
        else _selection(conn, "career", legacy_audit)
    )
    wanted = _normalize(person)
    result = _career_rows(
        conn, selection, program_id=None, season=None, division=None, role=None,
        family=None, person=person, pageid=pageid, limit=limit, offset=offset,
        person_order=True,
    )
    observations = _rows(
        conn,
        "SELECT observation_id, program_id, display_name, person, source_title, "
        "season, evidence_tier, source_class, pit_admitted "
        "FROM staff_observation WHERE LOWER(TRIM(person)) = ? ORDER BY observation_id",
        (wanted,),
    )
    identities: list[dict[str, Any]] = []
    if selection["mode"] in (MODE_CORRECTED_SUCCESSOR, MODE_EXPLICIT_CAREER_SUCCESSOR):
        clauses = [
            "(bas_release_query_normalize(page_title) = ? "
            "OR bas_release_query_normalize(person_display) = ?)"
        ]
        parameters: list[Any] = [wanted, wanted]
        if pageid is not None:
            clauses.append("CAST(pageid AS TEXT) = ?")
            parameters.append(str(pageid))
        identities = _rows(
            conn,
            "SELECT pageid, page_title, wikidata_qid, person_display, "
            "MAX(bas_release_query_normalize(page_title) = ?) AS matched_on_page_title, "
            "MAX(bas_release_query_normalize(person_display) = ?) AS matched_on_display_name, "
            f"COUNT(*) AS episode_rows FROM \"{selection['selected_table']}\" {_where(clauses)} "
            "GROUP BY pageid, page_title, wikidata_qid, person_display ORDER BY pageid",
            [wanted, wanted, *parameters],
        )
    rows = result["rows"]
    return {
        "query": {"person": person, "pageid": pageid, "legacy_audit": bool(legacy_audit)},
        "release_dispatch": selection,
        "person_known": bool(result["total"] or observations),
        "career_episode_count": len(rows),
        "career_episode_total_count": result["total"],
        "pagination": _pagination(result["total"], offset, limit, len(rows)),
        "career_episodes": rows,
        "career_identities": identities,
        "career_identity_count": len(identities),
        "career_identity_ambiguous": len(identities) > 1,
        "predecessor_rows_without_successor": result[
            "predecessor_rows_without_successor_on_these_pages"
        ],
        "staff_observation_count": len(observations),
        "staff_observations": observations,
        "identity_caveat": (
            "Rows are matched on exact display name. Name agreement is not "
            "person identity; two people sharing a name are not separated "
            "here and the release's own identity state is returned with each "
            "row so the caller can see it."
        ),
    }


def career_listing(
    conn: sqlite3.Connection,
    *,
    team: str | None = None,
    season: Any = None,
    division: str | None = None,
    role: str | None = None,
    family: str | None = None,
    person: str | None = None,
    pageid: Any = None,
    legacy_audit: bool = False,
    limit: int | None = DEFAULT_PAGE_LIMIT,
    offset: int = 0,
    career_successor: dict[str, Any] | None = None,
    uncertainty: str | None = None,
) -> dict[str, Any]:
    """National career episodes, filtered and paged, with exact totals.

    ``season`` selects episodes whose stated interval covers that year;
    with ``division`` it uses the division the release classified for that
    season. ``team`` is an exact program resolution, never a substring.
    """

    selection = (
        _explicit_successor_selection(conn, career_successor, legacy_audit=legacy_audit)
        if career_successor is not None
        else _selection(conn, "career", legacy_audit)
    )
    season_value = None if season is None else _season_int(season)
    program: dict[str, Any] | None = None
    program_id: str | None = None
    if team is not None:
        program = resolve_program(conn, team)
        if not program["resolved"] or program["ambiguous"]:
            _check_page(limit, offset)
            return {
                "query": {"team": team, "season": season, "division": division, "role": role,
                          "family": family, "person": person, "pageid": pageid,
                          "legacy_audit": bool(legacy_audit)},
                "release_dispatch": selection,
                "program": program,
                "answerable": False,
                "row_count": 0,
                "pagination": _pagination(0, offset, limit, 0),
                "rows": [],
            }
        program_id = program["resolved"][0]
    result = _career_rows(
        conn, selection, program_id=program_id, season=season_value, division=division,
        role=role, family=family, person=person, pageid=pageid, limit=limit,
        offset=offset, person_order=False, uncertainty=uncertainty,
    )
    rows = result["rows"]
    return {
        "query": {"team": team, "season": season, "division": division, "role": role,
                  "family": family, "person": person, "pageid": pageid,
                  "legacy_audit": bool(legacy_audit), "uncertainty": uncertainty,
                  "career_successor": (career_successor or {}).get("successor_file")},
        "release_dispatch": selection,
        "program": program,
        "answerable": True,
        "filters_applied": result["filters_applied"],
        "row_count": len(rows),
        "pagination": _pagination(result["total"], offset, limit, len(rows)),
        "missingness": result["missingness"],
        "rows": rows,
        "predecessor_rows_without_successor_on_these_pages": result[
            "predecessor_rows_without_successor_on_these_pages"
        ],
        "caveat": (
            "Career episodes are retrospective encyclopedia evidence. They are "
            "candidate history, not official confirmation, and none is PIT "
            "admitted by this query."
        ),
    }


def unresolved_records(conn: sqlite3.Connection) -> dict[str, Any]:
    """Every class of record the release could not resolve, kept separate."""

    unresolved_names = _rows(
        conn,
        "SELECT unresolved_id, raw_name, state, seasons, candidate_program_ids, detail "
        "FROM unresolved_program_name ORDER BY unresolved_id",
    )
    rejected = _rows(
        conn,
        "SELECT observation_id, program_id, display_name, person, source_title, "
        "season, season_state, reject_reason, role_claim_supported, evidence_tier "
        "FROM staff_observation "
        "WHERE (reject_reason IS NOT NULL AND TRIM(reject_reason) <> '') "
        "   OR role_claim_supported = 0 "
        "ORDER BY observation_id",
    )
    no_evidence_cells = _rows(
        conn,
        "SELECT coverage_state, COUNT(*) AS n FROM core_role_cell "
        "GROUP BY coverage_state ORDER BY n DESC",
    )
    collisions = _rows(
        conn,
        "SELECT collision_id, normalized_alias, match_basis, program_ids, disposition "
        "FROM alias_collision ORDER BY collision_id",
    )
    conflicts = _rows(
        conn,
        "SELECT conflict_id, page_title, season, side, conflict_texts, "
        "program_resolution_state FROM scheme_conflict ORDER BY conflict_id",
    )
    return {
        "unresolved_program_names": unresolved_names,
        "unresolved_program_name_count": len(unresolved_names),
        "rejected_or_unsupported_observations": rejected,
        "rejected_or_unsupported_observation_count": len(rejected),
        "core_role_cell_coverage_states": no_evidence_cells,
        "alias_collisions": collisions,
        "alias_collision_count": len(collisions),
        "scheme_conflicts": conflicts,
        "scheme_conflict_count": len(conflicts),
        "note": (
            "These are distinct kinds of unresolved. Summing them would "
            "invent a single 'unresolved' population that the release does "
            "not define."
        ),
    }


def schemes(
    conn: sqlite3.Connection,
    *,
    team: str | None = None,
    season: str | None = None,
    limit: int | None = DEFAULT_PAGE_LIMIT,
    offset: int = 0,
) -> dict[str, Any]:
    _check_page(limit, offset)
    clauses: list[str] = []
    parameters: list[Any] = []
    program = resolve_program(conn, team) if team else None
    if program is not None:
        if not program["resolved"] or program["ambiguous"]:
            return {
                "query": {"team": team, "season": season},
                "program": program,
                "answerable": False,
                "row_count": 0,
                "pagination": _pagination(0, offset, limit, 0),
                "rows": [],
            }
        clauses.append("program_id = ?")
        parameters.append(program["resolved"][0])
    if season:
        clauses.append("CAST(season AS TEXT) = ?")
        parameters.append(str(season))
    where = _where(clauses)
    total = int(
        conn.execute(f"SELECT COUNT(*) FROM scheme_assertion {where}", tuple(parameters)).fetchone()[0]
    )
    rows = _rows(
        conn,
        "SELECT scheme_assertion_id, program_id, season, side, source_text, "
        "normalized_families, source_disposition, state, evidence_tier, "
        "official_corroboration, page_title, wikimedia_revision, pit_admitted, "
        f"inferred_from_title FROM scheme_assertion {where} "
        "ORDER BY scheme_assertion_id LIMIT ? OFFSET ?",
        [*parameters, -1 if limit is None else limit, offset],
    )
    totals = _rows(
        conn,
        "SELECT side, state, COUNT(*) AS n FROM scheme_assertion GROUP BY side, state "
        "ORDER BY n DESC",
    )
    return {
        "query": {"team": team, "season": season},
        "program": program,
        "answerable": True,
        "row_count": len(rows),
        "pagination": _pagination(total, offset, limit, len(rows)),
        "selected_table": "scheme_assertion",
        "selected_table_row_count": _count(conn, "scheme_assertion"),
        "row_identity_field": "scheme_assertion_id",
        "rows": rows,
        "release_totals_by_side_and_state": totals,
        "caveat": (
            "A source-stated scheme is candidate historical evidence. It is "
            "not official confirmation, a realized-scheme conclusion or "
            "evidence of play-calling responsibility."
        ),
        "row_limit": limit,
    }


# ------------------------------------------------------ responsibility rows

_RESPONSIBILITY_COMPARED_FIELDS = (
    "person", "program_id", "season", "source_title", "evidence_code", "disposition",
)


def _by_ids(
    conn: sqlite3.Connection, sql_prefix: str, column: str, ids: Sequence[Any]
) -> dict[str, list[dict[str, Any]]]:
    found: dict[str, list[dict[str, Any]]] = {}
    wanted = sorted({str(value) for value in ids if value is not None})
    for chunk in _chunks(wanted):
        marks = ",".join("?" for _ in chunk)
        for row in _rows(conn, f"{sql_prefix} WHERE CAST({column} AS TEXT) IN ({marks})", chunk):
            found.setdefault(str(row[column]), []).append(row)
    return found


def _enrich_responsibility_successor(
    conn: sqlite3.Connection, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    predecessors = _by_ids(
        conn,
        "SELECT responsibility_id, person, program_id, season, source_title, "
        "evidence_code, disposition FROM responsibility_assertion",
        "responsibility_id",
        [row.get("release_responsibility_id") for row in rows],
    )
    observations = _by_ids(
        conn,
        "SELECT observation_id, capture_path, payload_sha256, record_selector "
        "FROM staff_observation",
        "observation_id",
        [row.get("observation_id") for row in rows],
    )
    enriched = []
    for row in rows:
        identity = row.get("release_responsibility_id")
        matches = predecessors.get(str(identity), []) if identity is not None else []
        predecessor = matches[0] if len(matches) == 1 else None
        observation_rows = (
            observations.get(str(row.get("observation_id")), [])
            if row.get("observation_id") is not None
            else []
        )
        observation = observation_rows[0] if len(observation_rows) == 1 else None
        if identity is None:
            lineage_state = "NEW_IN_SUCCESSOR_NO_PREDECESSOR_ROW"
        elif predecessor is None:
            lineage_state = (
                "PREDECESSOR_ROW_ABSENT" if not matches else "PREDECESSOR_ROW_AMBIGUOUS"
            )
        else:
            lineage_state = "DERIVED_FROM_PREDECESSOR_ROW"
        enriched.append(
            {
                **row,
                "lineage_state": lineage_state,
                "predecessor": (
                    {
                        **predecessor,
                        "changed_fields": [
                            name
                            for name in _RESPONSIBILITY_COMPARED_FIELDS
                            if predecessor.get(name) != row.get(name)
                        ],
                    }
                    if predecessor is not None
                    else None
                ),
                "locator": {
                    "source_kind": row.get("source_kind"),
                    "capture_path": row.get("capture_path"),
                    "payload_sha256": row.get("payload_sha256"),
                    "observation_id": row.get("observation_id"),
                    "observation_capture_path": observation and observation.get("capture_path"),
                    "observation_payload_sha256": observation and observation.get("payload_sha256"),
                    "observation_record_selector": observation and observation.get("record_selector"),
                    "offset_in_rendered_text": row.get("offset_in_rendered_text"),
                    "wiki_file": row.get("wiki_file"),
                    "revision_id": row.get("revision_id"),
                    "revision_timestamp": row.get("revision_timestamp"),
                    "offset_in_plain_text": row.get("offset_in_plain_text"),
                },
            }
        )
    return enriched


def _enrich_responsibility_legacy(
    conn: sqlite3.Connection, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    successors = _by_ids(
        conn,
        "SELECT successor_key, release_responsibility_id, person, program_id, season, "
        "evidence_code, disposition, responsibility_version FROM responsibility_successor",
        "release_responsibility_id",
        [row.get("responsibility_id") for row in rows],
    )
    return [
        {
            **row,
            "row_status": "SUPERSEDED_PREDECESSOR_ROW",
            "successor_rows": successors.get(str(row.get("responsibility_id")), []),
        }
        for row in rows
    ]


def responsibilities(
    conn: sqlite3.Connection,
    *,
    team: str | None = None,
    season: str | None = None,
    person: str | None = None,
    disposition: str | None = None,
    source_kind: str | None = None,
    legacy_audit: bool = False,
    limit: int | None = DEFAULT_PAGE_LIMIT,
    offset: int = 0,
) -> dict[str, Any]:
    selection = _selection(conn, "responsibility", legacy_audit)
    _check_page(limit, offset)
    table = selection["selected_table"]
    corrected = selection["mode"] == MODE_CORRECTED_SUCCESSOR
    if source_kind is not None and not corrected:
        raise ReleaseDispatchError(
            REFUSED_FILTER_NOT_CARRIED_BY_SELECTED_TABLE,
            f"source_kind is not carried by {table} (mode {selection['mode']})",
        )
    query = {"team": team, "season": season, "person": person, "disposition": disposition,
             "source_kind": source_kind, "legacy_audit": bool(legacy_audit)}
    clauses: list[str] = []
    parameters: list[Any] = []
    program = resolve_program(conn, team) if team else None
    if program is not None:
        if not program["resolved"] or program["ambiguous"]:
            return {
                "query": query,
                "release_dispatch": selection,
                "program": program,
                "answerable": False,
                "row_count": 0,
                "pagination": _pagination(0, offset, limit, 0),
                "rows": [],
            }
        clauses.append("program_id = ?")
        parameters.append(program["resolved"][0])
    if season:
        clauses.append("CAST(season AS TEXT) = ?")
        parameters.append(str(season))
    if person is not None:
        _register_normalizer(conn)
        clauses.append("bas_release_query_normalize(person) = ?")
        parameters.append(_normalize(person))
    if disposition is not None:
        clauses.append("disposition = ?")
        parameters.append(disposition)
    if source_kind is not None:
        clauses.append("source_kind = ?")
        parameters.append(source_kind)
    if corrected:
        order = "(release_responsibility_id IS NULL), release_responsibility_id, successor_key"
        total, rows = _page_rows(
            conn, table=table, clauses=clauses, parameters=parameters,
            order=order, limit=limit, offset=offset,
        )
        rows = _enrich_responsibility_successor(conn, rows)
    else:
        where = _where(clauses)
        total = int(
            conn.execute(
                f"SELECT COUNT(*) FROM responsibility_assertion {where}", tuple(parameters)
            ).fetchone()[0]
        )
        rows = _rows(
            conn,
            "SELECT responsibility_id, person, program_id, season, source_title, "
            "evidence_code, disposition, inferred_from_role_title, pit_admitted "
            f"FROM responsibility_assertion {where} ORDER BY responsibility_id LIMIT ? OFFSET ?",
            [*parameters, -1 if limit is None else limit, offset],
        )
        if selection["mode"] == MODE_LEGACY_PREDECESSOR_AUDIT:
            rows = _enrich_responsibility_legacy(conn, rows)
    dispositions = _rows(
        conn,
        f'SELECT disposition, COUNT(*) AS n FROM "{table}" '
        "GROUP BY disposition ORDER BY n DESC, disposition",
    )
    payload: dict[str, Any] = {
        "query": query,
        "release_dispatch": selection,
        "program": program,
        "answerable": True,
        "row_count": len(rows),
        "pagination": _pagination(total, offset, limit, len(rows)),
        "rows": rows,
        "release_totals_by_disposition": dispositions,
        "caveat": (
            "A coordinator title is not a play-calling statement. Rows whose "
            "disposition is a rejection are returned, not hidden."
        ),
        "row_limit": limit,
    }
    if corrected:
        payload["release_totals_by_source_kind"] = _rows(
            conn,
            "SELECT source_kind, COUNT(*) AS n FROM responsibility_successor "
            "GROUP BY source_kind ORDER BY n DESC, source_kind",
        )
    return payload


def _career_conservation(conn: sqlite3.Connection) -> dict[str, Any]:
    """Old-to-new accounting between the predecessor and corrected career rows."""

    predecessor_spans = [
        str(row[0]) for row in conn.execute("SELECT span_id FROM career_episode")
    ]
    states: dict[str, int] = {}
    mapped = 0
    unmapped = 0
    referenced: set[str] = set()
    disposition_spans: list[str] = []
    for span, state, episodes in conn.execute(
        "SELECT predecessor_span_id, state, reparse_episode_ids FROM career_predecessor_disposition"
    ):
        disposition_spans.append(str(span))
        states[str(state)] = states.get(str(state), 0) + 1
        decoded = _decode(episodes)
        if isinstance(decoded, list) and decoded:
            mapped += 1
            referenced.update(str(value) for value in decoded)
        else:
            unmapped += 1
    successor_ids: dict[str, str] = {
        str(row[0]): str(row[1])
        for row in conn.execute("SELECT episode_id, family FROM career_episode_successor")
    }
    new_by_family: dict[str, int] = {}
    for episode, family in successor_ids.items():
        if episode not in referenced:
            new_by_family[family] = new_by_family.get(family, 0) + 1
    predecessor_set = set(predecessor_spans)
    disposition_set = set(disposition_spans)
    return {
        "predecessor_rows": len(predecessor_spans),
        "disposition_rows": len(disposition_spans),
        "disposition_states": dict(sorted(states.items())),
        "predecessor_rows_mapped_to_a_successor": mapped,
        "predecessor_rows_mapped_to_no_successor": unmapped,
        "predecessor_rows_without_a_disposition": len(predecessor_set - disposition_set),
        "dispositions_for_no_predecessor_row": len(disposition_set - predecessor_set),
        "duplicate_dispositions": len(disposition_spans) - len(disposition_set),
        "successor_rows": len(successor_ids),
        "successor_rows_derived_from_predecessor_rows": len(referenced & set(successor_ids)),
        "successor_rows_new_in_successor_by_family": dict(sorted(new_by_family.items())),
        "referenced_successor_ids_absent": len(referenced - set(successor_ids)),
        "balanced": (
            predecessor_set == disposition_set
            and len(disposition_spans) == len(disposition_set)
            and not (referenced - set(successor_ids))
        ),
    }


def _responsibility_conservation(conn: sqlite3.Connection) -> dict[str, Any]:
    predecessor_ids = [
        str(row[0]) for row in conn.execute("SELECT responsibility_id FROM responsibility_assertion")
    ]
    successor_ids = [
        None if row[0] is None else str(row[0])
        for row in conn.execute("SELECT release_responsibility_id FROM responsibility_successor")
    ]
    linked = [value for value in successor_ids if value is not None]
    new_by_kind = {
        str(row[0]): int(row[1])
        for row in conn.execute(
            "SELECT source_kind, COUNT(*) FROM responsibility_successor "
            "WHERE release_responsibility_id IS NULL GROUP BY source_kind ORDER BY source_kind"
        )
    }
    predecessor_set = set(predecessor_ids)
    linked_set = set(linked)
    return {
        "predecessor_rows": len(predecessor_ids),
        "successor_rows": len(successor_ids),
        "successor_rows_linked_to_a_predecessor_row": len(linked),
        "successor_rows_new_in_successor_by_source_kind": new_by_kind,
        "predecessor_rows_without_a_successor_row": len(predecessor_set - linked_set),
        "successor_links_to_no_predecessor_row": len(linked_set - predecessor_set),
        "predecessor_rows_linked_more_than_once": len(linked) - len(linked_set),
        "balanced": predecessor_set == linked_set and len(linked) == len(linked_set),
    }


def coverage(conn: sqlite3.Connection) -> dict[str, Any]:
    """The release's own coverage statement, plus a live recount beside it."""

    dispatch = release_dispatch(conn)
    declared = _rows(
        conn, "SELECT grain, bucket, value FROM coverage_summary ORDER BY grain, bucket"
    )
    recount = {
        "canonical_program": _rows(conn, "SELECT COUNT(*) AS n FROM canonical_program")[0]["n"],
        "program_season_membership": _rows(
            conn, "SELECT COUNT(*) AS n FROM program_season_membership"
        )[0]["n"],
        "core_role_cell": _rows(conn, "SELECT COUNT(*) AS n FROM core_role_cell")[0]["n"],
        "staff_observation": _rows(conn, "SELECT COUNT(*) AS n FROM staff_observation")[0]["n"],
        "staff_role_assignment": _rows(
            conn, "SELECT COUNT(*) AS n FROM staff_role_assignment"
        )[0]["n"],
        "career_episode": _rows(conn, "SELECT COUNT(*) AS n FROM career_episode")[0]["n"],
        "scheme_assertion": _rows(conn, "SELECT COUNT(*) AS n FROM scheme_assertion")[0]["n"],
        "responsibility_assertion": _rows(
            conn, "SELECT COUNT(*) AS n FROM responsibility_assertion"
        )[0]["n"],
        "user_corpus_cell": _rows(conn, "SELECT COUNT(*) AS n FROM user_corpus_cell")[0]["n"],
        "unresolved_program_name": _rows(
            conn, "SELECT COUNT(*) AS n FROM unresolved_program_name"
        )[0]["n"],
    }
    for dataset in ("career", "responsibility"):
        for name, count in dispatch[dataset]["successor_table_row_counts"].items():
            recount[name] = count
    seasons = _rows(
        conn,
        "SELECT season, programs, fbs, fcs, pre_classification, other_division, "
        "unknown, state FROM season_population ORDER BY CAST(season AS INTEGER)",
    )
    conservation: dict[str, Any] = {}
    if dispatch["career"]["mode"] == MODE_CORRECTED_SUCCESSOR:
        conservation["career"] = _career_conservation(conn)
    if dispatch["responsibility"]["mode"] == MODE_CORRECTED_SUCCESSOR:
        conservation["responsibility"] = _responsibility_conservation(conn)
    return {
        "release_identity": release_identity(conn),
        "release_dispatch": dispatch,
        "declared_coverage_summary": declared,
        "live_table_recount": recount,
        "successor_conservation": conservation,
        "season_population": seasons,
        "season_count": len(seasons),
        "note": (
            "The declared summary and the live recount are reported side by "
            "side rather than reconciled into one number: a disagreement "
            "between them is a finding, and averaging it away would hide it."
        ),
    }


def provenance(conn: sqlite3.Connection, *, observation_id: str | None = None) -> dict[str, Any]:
    files = _rows(
        conn,
        "SELECT source_file_id, path, sha256, bytes, source_class, exists_at_build "
        "FROM source_file ORDER BY source_file_id",
    )
    drill: dict[str, Any] | None = None
    if observation_id:
        observation = _rows(
            conn,
            "SELECT observation_id, capture_path, payload_sha256, program_id, "
            "display_name, person, source_title, record_selector, "
            "person_body_offset, person_record_bound, role_claim_supported, "
            "reject_reason, evidence_tier, season, season_state, source_class, "
            + _lineage_columns(conn) +
            "pit_admitted FROM staff_observation WHERE observation_id = ?",
            (observation_id,),
        )
        assignments = _rows(
            conn,
            "SELECT assignment_id, role_code, unit, qualifiers, occupancy, "
            "taxonomy_version, is_core_role, play_caller_inferred "
            "FROM staff_role_assignment WHERE observation_id = ? ORDER BY assignment_id",
            (observation_id,),
        )
        drill = {
            "requested": observation_id,
            "known": bool(observation),
            "observation": observation[0] if observation else None,
            "role_assignments": assignments,
        }
    return {
        "source_file_count": len(files),
        "source_files": files,
        "observation_drill_down": drill,
        "lineage_note": (
            "capture_path plus payload_sha256 on an observation, and path plus "
            "sha256 on a source file, are what tie a row to bytes. A file "
            "listing alone is not row-level lineage."
        ),
    }

"""Read-only research queries for staff, careers, schemes and coverage.

Unknown and conflicting values are returned, never silently omitted.
Package-installed use must pass explicit data roots; there is no private
absolute-path default that loads production secrets.

MF35-06 repair: `team_staff`, `coach_career`, `unresolved_roles` and
`team_schemes` below now detect which schema the given database actually
has (`aggie_analytics.cycle35.query.schema_kind`) and delegate to that
module's equivalents when it is a cycle35 coaching release. The installed
`bas-staff-query` CLI (`main`, below) is this module's `main`, so this is
what makes the ONE installed entry point work against either a legacy
cycle33 delivery or a cycle35 release without raising
`OperationalError: no such table: staff_role_cells` -- exactly the failure
the Cycle #35 manager follow-up reproduced against the delivered r7
release. Every function's return-row SHAPE stays whatever its owning schema
actually produces; this is a dispatch fix, not a shape-unifying translation
layer, because pretending the two schemas are the same would hide the real
difference between a flat disposition-tagged cell and an evidence-layered
assertion.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics import readonly_sqlite
from aggie_analytics.cycle35 import query as cycle35_query

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS staff_role_cells (
    observation_id TEXT NOT NULL,
    canonical_claim_id TEXT,
    source_file TEXT,
    team TEXT,
    team_id_source TEXT,
    season TEXT,
    role_column TEXT,
    person TEXT,
    source_title TEXT,
    disposition TEXT NOT NULL,
    support_column INTEGER NOT NULL,
    principal_role_blocked INTEGER NOT NULL,
    source_class TEXT NOT NULL,
    pit_admitted INTEGER NOT NULL,
    cell_text TEXT,
    subdivision TEXT,
    verified INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS scheme_tenure_claims (
    program_raw TEXT,
    season TEXT,
    field TEXT NOT NULL,
    source_text TEXT,
    disposition TEXT NOT NULL,
    inferred INTEGER NOT NULL,
    source_class TEXT NOT NULL,
    family_tags TEXT,
    conflict INTEGER NOT NULL,
    official_corroboration TEXT,
    source_receipt_sha256 TEXT,
    source_span TEXT,
    source_revision TEXT
);
"""


class StaffQueryError(ValueError):
    """Raised when a research query cannot be answered from bound evidence."""


def connect_for_import(database: Path) -> sqlite3.Connection:
    path = Path(database)
    if not path.parent.exists():
        raise StaffQueryError("query database parent directory does not exist")
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    return conn


def connect_readonly(database: Path) -> sqlite3.Connection:
    """Read-only, never creating: exactly the literal local file named (``aggie_analytics.readonly_sqlite``); a
    network, device or non-literal location is refused before any file is touched."""
    path = Path(database)
    try:
        readonly_sqlite.literal_path(database)
    except readonly_sqlite.DatabaseLocationError as exc:
        raise StaffQueryError(str(exc)) from exc
    if not path.is_file():
        raise StaffQueryError("query database does not exist; import is separate")
    try:
        conn = readonly_sqlite.connect_readonly(database)
    except readonly_sqlite.DatabaseLocationError as exc:
        raise StaffQueryError(str(exc)) from exc
    conn.row_factory = sqlite3.Row
    return conn


def connect(database: Path, *, readonly: bool = True) -> sqlite3.Connection:
    """Read-only by default. Schema creation is explicit import-only."""

    if readonly:
        return connect_readonly(database)
    return connect_for_import(database)


def load_import(conn: sqlite3.Connection, imported: Mapping[str, Any]) -> int:
    conn.execute("DELETE FROM staff_role_cells")
    payload = [
        (
            cell.get("observation_id"),
            cell.get("canonical_claim_id"),
            cell.get("source_file"),
            cell.get("team"),
            cell.get("team_id_source"),
            str(cell.get("season") or ""),
            cell.get("role_column"),
            cell.get("person"),
            cell.get("source_title"),
            cell.get("disposition"),
            1 if cell.get("support_column") else 0,
            1 if cell.get("principal_role_blocked") else 0,
            cell.get("source_class") or "USER_COMPILED_RESEARCH_OBSERVATION",
            1 if cell.get("pit_admitted") is True else 0,
            cell.get("cell_text"),
            cell.get("source_subdivision")
            or cell.get("filename_subdivision")
            or "SUBDIVISION_UNRESOLVED",
            1 if cell.get("verified") is True else 0,
        )
        for cell in imported.get("role_cells") or []
    ]
    conn.executemany(
        """
        INSERT INTO staff_role_cells (
            observation_id, canonical_claim_id, source_file, team,
            team_id_source, season, role_column, person, source_title,
            disposition, support_column, principal_role_blocked,
            source_class, pit_admitted, cell_text, subdivision, verified
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        payload,
    )
    conn.commit()
    return len(payload)


def team_staff(
    conn: sqlite3.Connection, *, team: str, season: str
) -> list[dict[str, Any]]:
    if cycle35_query.schema_kind(conn) == cycle35_query.SCHEMA_KIND_CYCLE35:
        return cycle35_query.team_staff(conn, team=team, season=season)
    cur = conn.execute(
        """
        SELECT * FROM staff_role_cells
        WHERE season = ? AND (team = ? OR team_id_source = ?)
        ORDER BY role_column, person
        """,
        (str(season), team, team),
    )
    return [dict(row) for row in cur.fetchall()]


def coach_career(conn: sqlite3.Connection, *, person: str) -> list[dict[str, Any]]:
    if cycle35_query.schema_kind(conn) == cycle35_query.SCHEMA_KIND_CYCLE35:
        return cycle35_query.coach_career(conn, person=person)
    cur = conn.execute(
        """
        SELECT * FROM staff_role_cells
        WHERE person = ?
        ORDER BY season, team, role_column
        """,
        (person,),
    )
    return [dict(row) for row in cur.fetchall()]


def load_scheme_claims(
    conn: sqlite3.Connection, claims: Sequence[Mapping[str, Any]]
) -> int:
    conn.execute("DELETE FROM scheme_tenure_claims")
    payload = [
        (
            claim.get("program_raw") or claim.get("title"),
            str(claim.get("season") or ""),
            claim.get("field") or claim.get("normalized_field") or "",
            claim.get("source_text") or claim.get("raw_value"),
            claim.get("disposition") or "WIKI_REPORTED_NOT_OFFICIAL",
            1 if claim.get("inferred") else 0,
            claim.get("source_class") or "WIKIPEDIA_ATTRIBUTED_RETROSPECTIVE",
            json.dumps(claim.get("family_tags") or [], sort_keys=True),
            1 if claim.get("conflict_distinct_source_text") else 0,
            claim.get("official_corroboration") or "WIKIPEDIA_ONLY_NOT_OFFICIAL",
            claim.get("source_receipt_sha256") or claim.get("receipt_sha256"),
            claim.get("source_span"),
            claim.get("source_revision") or claim.get("wikimedia_revision"),
        )
        for claim in claims
    ]
    conn.executemany(
        """
        INSERT INTO scheme_tenure_claims (
            program_raw, season, field, source_text, disposition,
            inferred, source_class, family_tags, conflict,
            official_corroboration, source_receipt_sha256, source_span,
            source_revision
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        payload,
    )
    conn.commit()
    return len(payload)


def team_schemes(
    conn: sqlite3.Connection, *, program: str, season: str
) -> list[dict[str, Any]]:
    """Exact (case/whitespace-insensitive) canonical-program fact lookup.

    MR33-08 repair: this previously used a `LIKE '%program%'` substring match,
    so a "Virginia" fact query silently also returned "Virginia Tech" and
    "West Virginia" rows. A fact query must resolve to the named program only;
    callers who want candidates for an ambiguous/partial name must use
    `search_team_schemes_by_name` below and get back an explicitly labeled
    multi-program result, never a merged fact answer.
    """

    if cycle35_query.schema_kind(conn) == cycle35_query.SCHEMA_KIND_CYCLE35:
        return cycle35_query.team_schemes(conn, program=program, season=season)
    cur = conn.execute(
        """
        SELECT * FROM scheme_tenure_claims
        WHERE season = ? AND TRIM(program_raw) = TRIM(?) COLLATE NOCASE
        ORDER BY field
        """,
        (str(season), program),
    )
    return [dict(row) for row in cur.fetchall()]


def search_team_schemes_by_name(
    conn: sqlite3.Connection, *, name_fragment: str, season: str | None = None
) -> dict[str, Any]:
    """Explicit disambiguation search -- returns labeled search *candidates*,
    never a silently merged single-program fact answer. Distinct from
    `team_schemes`, which is name-exact and used for actual fact retrieval."""

    if season is not None:
        cur = conn.execute(
            """
            SELECT DISTINCT program_raw, season FROM scheme_tenure_claims
            WHERE season = ? AND program_raw LIKE ?
            ORDER BY program_raw
            """,
            (str(season), f"%{name_fragment}%"),
        )
    else:
        cur = conn.execute(
            """
            SELECT DISTINCT program_raw, season FROM scheme_tenure_claims
            WHERE program_raw LIKE ?
            ORDER BY program_raw, season
            """,
            (f"%{name_fragment}%",),
        )
    candidates = [dict(row) for row in cur.fetchall()]
    return {
        "result_kind": "SEARCH_RESULTS_NOT_A_FACT_QUERY",
        "name_fragment": name_fragment,
        "distinct_program_count": len({row["program_raw"] for row in candidates}),
        "candidates": candidates,
    }


#: Dispositions that positively assert a resolved, admitted observation.
#: Stating the closed set this way is what makes an unanticipated enum value
#: default to VISIBLE instead of disappearing.
RESOLVED_DISPOSITIONS = frozenset(
    {
        "RESOLVED_CAREER_JOIN_VERIFIED",
        "CONFIRMED_APPOINTMENT",
        "CONFIRMED_CO_SHARED_ROLE",
    }
)

#: Resolved *as a negative*: examined and deliberately not admitted. Not
#: unresolved, but not a verified fact either, so it gets its own view.
REJECTED_DISPOSITIONS = frozenset({"CORRECTLY_REJECTED_NO_EMPLOYER_MATCH"})
QUARANTINED_DISPOSITION_TOKENS = ("QUARANTINE",)
CONFLICTED_DISPOSITION_TOKENS = ("CONFLICT",)

ROLE_STATE_VERIFIED = "VERIFIED"
ROLE_STATE_REJECTED = "REJECTED"
ROLE_STATE_QUARANTINED = "QUARANTINED"
ROLE_STATE_CONFLICTED = "CONFLICTED"
ROLE_STATE_UNRESOLVED = "UNRESOLVED"


def classify_disposition(disposition: str | None) -> str:
    """Map any disposition -- including one this code has never seen -- to a
    state bucket.

    MR34-06 repair. `unresolved_roles` previously matched an allowlist of
    four substrings (`UNMAPPED`, `CONFLICT`, `NOT_VERIFIED`, `UNPARSED`).
    `ROSTER_OBSERVATION_UNRESOLVED` contains none of them, so 57 genuinely
    unresolved rows in the delivered database were invisible to the query
    whose entire job was to surface them, while direct SQL found them
    immediately. Enumeration-by-example cannot be repaired by adding a fifth
    substring: the next unanticipated state would vanish the same way.

    The inversion is the fix -- name the states that ARE resolved and treat
    everything else as unresolved. An unrecognised disposition is then
    over-reported rather than silently dropped, which is the correct
    direction to fail for a completeness query.
    """

    text = str(disposition or "").strip().upper()
    if not text:
        return ROLE_STATE_UNRESOLVED
    if any(token in text for token in CONFLICTED_DISPOSITION_TOKENS):
        return ROLE_STATE_CONFLICTED
    if any(token in text for token in QUARANTINED_DISPOSITION_TOKENS):
        return ROLE_STATE_QUARANTINED
    if text in REJECTED_DISPOSITIONS:
        return ROLE_STATE_REJECTED
    if text in RESOLVED_DISPOSITIONS:
        return ROLE_STATE_VERIFIED
    return ROLE_STATE_UNRESOLVED


def _all_role_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT * FROM staff_role_cells ORDER BY season, team, role_column, person"
    )
    return [dict(row) for row in cur.fetchall()]


def roles_in_state(conn: sqlite3.Connection, state: str) -> list[dict[str, Any]]:
    """Every row whose disposition classifies into `state`."""

    return [
        row
        for row in _all_role_rows(conn)
        if classify_disposition(row.get("disposition")) == state
    ]


def unresolved_roles(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every row that is not positively resolved, including unknown states.

    A row with no `person` is unresolved whatever its disposition label says.
    """

    if cycle35_query.schema_kind(conn) == cycle35_query.SCHEMA_KIND_CYCLE35:
        return cycle35_query.unresolved_roles(conn)
    return [
        row
        for row in _all_role_rows(conn)
        if row.get("person") in (None, "")
        or classify_disposition(row.get("disposition")) == ROLE_STATE_UNRESOLVED
    ]


def rejected_roles(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return roles_in_state(conn, ROLE_STATE_REJECTED)


def quarantined_roles(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return roles_in_state(conn, ROLE_STATE_QUARANTINED)


def conflicted_roles(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return roles_in_state(conn, ROLE_STATE_CONFLICTED)


def verified_roles(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return roles_in_state(conn, ROLE_STATE_VERIFIED)


def role_state_conservation(conn: sqlite3.Connection) -> dict[str, Any]:
    """Prove every stored row is reachable through exactly one state view.

    This is the query that would have caught MR34-06 the day it shipped: the
    buckets must partition the table, so "57 rows reachable by raw SQL and by
    no view" becomes a detectable, reportable contradiction instead of an
    omission a consumer has to stumble onto.
    """

    rows = _all_role_rows(conn)
    total = conn.execute("SELECT COUNT(*) FROM staff_role_cells").fetchone()[0]
    buckets: dict[str, int] = {}
    unknown_dispositions: dict[str, int] = {}
    for row in rows:
        state = classify_disposition(row.get("disposition"))
        buckets[state] = buckets.get(state, 0) + 1
        label = str(row.get("disposition") or "").strip().upper()
        if (
            label
            and label not in RESOLVED_DISPOSITIONS
            and label not in REJECTED_DISPOSITIONS
            and not any(t in label for t in QUARANTINED_DISPOSITION_TOKENS)
            and not any(t in label for t in CONFLICTED_DISPOSITION_TOKENS)
        ):
            unknown_dispositions[label] = unknown_dispositions.get(label, 0) + 1
    return {
        "table_row_count": total,
        "classified_row_count": sum(buckets.values()),
        "state_counts": buckets,
        "unresolved_view_count": len(unresolved_roles(conn)),
        "states_partition_table": sum(buckets.values()) == total,
        "no_row_is_unreachable": sum(buckets.values()) == total,
        "dispositions_not_in_declared_enums": unknown_dispositions,
        "unknown_states_are_reported_not_hidden": True,
    }


def run_query_demonstrations(
    *,
    database: Path,
    imported: Mapping[str, Any],
    scheme_claims: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Explicit import then read-only queries. Missing DB is not created."""

    path = Path(database)
    if path.exists():
        raise StaffQueryError("demonstration database must not already exist")
    writer = connect_for_import(path)
    try:
        load_import(writer, imported)
        if scheme_claims:
            load_scheme_claims(writer, scheme_claims)
        writer.commit()
    finally:
        writer.close()
    reader = connect_readonly(path)
    try:
        historical_fbs = team_staff(reader, team="Air Force", season="2018")
        historical_fcs = team_staff(reader, team="Lehigh", season="2000")
        if not historical_fcs:
            historical_fcs = team_staff(reader, team="Lehigh", season="2026")
        current_staff = team_staff(reader, team="Texas A&M", season="2026")
        career = coach_career(reader, person="Troy Calhoun")
        unresolved = unresolved_roles(reader)
        schemes = team_schemes(reader, program="Air Force", season="2018")
        evidence = [
            {
                "observation_id": row.get("observation_id"),
                "person": row.get("person"),
                "role_column": row.get("role_column"),
                "source_title": row.get("source_title"),
                "disposition": row.get("disposition"),
                "source_subdivision": row.get("subdivision"),
            }
            for row in historical_fbs
            if row.get("person")
        ][:5]
    finally:
        reader.close()
    return {
        "artifact_type": "CYCLE33_QUERY_DEMONSTRATIONS",
        "database": str(path),
        "explicit_import_separate_from_readonly": True,
        "requires_explicit_database": True,
        "no_private_path_default": True,
        "historical_fbs_rows": len(historical_fbs),
        "historical_fcs_or_current_fcs_rows": len(historical_fcs),
        "current_staff_rows": len(current_staff),
        "multi_school_career_rows": len(career),
        "unresolved_visible": len(unresolved),
        "scheme_rows": len(schemes),
        "per_row_evidence_sample": evidence,
        "unknown_not_silently_omitted": True,
        "role_column_list_is_not_qualified_assignment": True,
        "market_margin_is_not_bas_score": True,
        "pit_admitted": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """The installed ``bas-staff-query`` entry point.

    V37-01 repair, in three parts:

    * the Cycle 36 *national* release is dispatched to its own module
      instead of being classified unknown and exiting 1;
    * an unknown schema fails **explicitly**, naming the tables it saw, so
      a refusal is legible rather than an ``OperationalError`` traceback;
    * the national-release queries a research consumer actually needs --
      division and season population, team season history, scheme,
      responsibility, coverage and provenance drill-down -- are reachable
      from this one entry point instead of requiring an ad-hoc SQL script.

    MF37A02-04: career and responsibility answers come from the table the
    release's registered version and its own lineage select -- the delivered
    correction by default, the superseded predecessor only under
    ``--legacy-audit`` -- and are paged with exact totals.
    """

    parser = argparse.ArgumentParser(description="Read-only BAS staff research queries")
    parser.add_argument("--database", required=True)
    parser.add_argument("--team")
    parser.add_argument("--season")
    parser.add_argument("--person")
    parser.add_argument("--unresolved", action="store_true")
    parser.add_argument(
        "--division",
        help="Classification bucket (for example FBS or FCS) within --season.",
    )
    parser.add_argument(
        "--seasons-for-team",
        action="store_true",
        help="Every season membership row for --team.",
    )
    parser.add_argument("--scheme", action="store_true", help="Scheme assertions.")
    parser.add_argument(
        "--responsibility", action="store_true", help="Responsibility assertions."
    )
    parser.add_argument(
        "--coverage", action="store_true", help="The release's own coverage statement."
    )
    parser.add_argument(
        "--provenance",
        nargs="?",
        const="",
        metavar="OBSERVATION_ID",
        help="Source-file lineage; with an observation id, drill down to that row.",
    )
    parser.add_argument(
        "--schema", action="store_true", help="Report the detected schema and exit."
    )
    # MF37A02-04: career listing, the corrected/legacy table dispatch and
    # exact pagination for the national release.
    parser.add_argument(
        "--career",
        action="store_true",
        help="National career episodes; filter with --team/--season/--division/"
        "--role/--family/--person/--pageid.",
    )
    parser.add_argument("--role", help="Career role code, for example head_coach.")
    parser.add_argument(
        "--family", help="Career episode family: COACHING, PLAYING or ADMINISTRATIVE."
    )
    parser.add_argument("--pageid", help="One career identity (encyclopedia page id).")
    parser.add_argument("--disposition", help="Responsibility disposition filter.")
    parser.add_argument("--source-kind", help="Responsibility source kind filter.")
    parser.add_argument(
        "--legacy-audit",
        action="store_true",
        help="Return the superseded predecessor career/responsibility rows, "
        "each joined to its old-to-new disposition, instead of the correction.",
    )
    # Cycle #37 - Attempt #4 (R37A04-06): an explicitly named career successor, bound to this database's
    # exact digest. It is never discovered or defaulted; without the flag the release answers as delivered.
    parser.add_argument(
        "--career-successor",
        help="A career successor file to answer --career/--person from, instead of the release's "
        "own corrected table. Refused unless it is bound to this exact database.",
    )
    parser.add_argument(
        "--career-successor-sha256",
        help="Refuse the named career successor unless its file bytes have this SHA-256.",
    )
    parser.add_argument(
        "--uncertainty",
        help="With --career-successor: only episodes carrying this uncertainty class "
        "(UNRESOLVED_ROLE, UNKNOWN_START, UNKNOWN_END, UNCERTAIN_START, UNCERTAIN_END, "
        "NO_DEFINITE_SEASON, INCONSISTENT_BOUNDS).",
    )
    parser.add_argument("--limit", type=int, help="Page size for paged queries.")
    parser.add_argument("--offset", type=int, help="Rows to skip for paged queries.")
    parser.add_argument(
        "--all", action="store_true", help="Return every matching row in one page."
    )
    parser.add_argument(
        "--compact", action="store_true", help="Print JSON without indentation."
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    # The connection is closed on every exit path, including the refusals
    # below. A read-only handle left open keeps a file lock on Windows, which
    # is how a caller's own cleanup starts failing for reasons that have
    # nothing to do with the query it ran.
    conn = connect_readonly(Path(args.database))
    try:
        detected = cycle35_query.schema_kind(conn)

        if args.schema:
            report = cycle35_query.schema_report(conn)
            if detected == cycle35_query.SCHEMA_KIND_CYCLE36:
                report["release_dispatch"] = _dispatch_report(conn)
            print(json.dumps(report, indent=2, default=str))
            return 0

        if detected == cycle35_query.SCHEMA_KIND_UNKNOWN:
            report = cycle35_query.schema_report(conn)
            raise StaffQueryError(
                "this database matches no schema this consumer can answer. "
                f"Tables present: {report['tables_present']}. Marker sets: "
                f"{json.dumps(report['marker_sets'], sort_keys=True)}. Refusing "
                "to guess a shape: an empty result here would be a wrong answer "
                "rather than an absent one."
            )

        if detected == cycle35_query.SCHEMA_KIND_CYCLE36:
            payload = _cycle36_dispatch(conn, args)
        else:
            payload = _legacy_dispatch(conn, args)

        if getattr(args, "compact", False):
            print(json.dumps(payload, separators=(",", ":"), default=str))
        else:
            print(json.dumps(payload, indent=2, default=str))
        return 0
    finally:
        conn.close()


def _dispatch_report(conn: sqlite3.Connection) -> dict[str, Any]:
    """The national dispatch decision for ``--schema``; a refusal is reported."""

    from aggie_analytics.cycle36 import release_query

    try:
        return release_query.release_dispatch(conn)
    except release_query.Cycle36QueryError as exc:
        return {"refused": getattr(exc, "code", None), "detail": str(exc)}


#: Modifier flags added for MF37A02-04, by the queries each applies to. A
#: modifier given to a query it does not apply to is refused, never ignored:
#: an ignored ``--legacy-audit`` would return corrected rows the caller
#: believes are predecessor rows, and an ignored ``--limit`` would return a
#: different number of rows than was asked for.
_MODIFIERS = {
    "--legacy-audit": lambda a: bool(getattr(a, "legacy_audit", False)),
    "--limit": lambda a: getattr(a, "limit", None) is not None,
    "--offset": lambda a: getattr(a, "offset", None) is not None,
    "--all": lambda a: bool(getattr(a, "all", False)),
    "--role": lambda a: getattr(a, "role", None) is not None,
    "--family": lambda a: getattr(a, "family", None) is not None,
    "--pageid": lambda a: getattr(a, "pageid", None) is not None,
    "--disposition": lambda a: getattr(a, "disposition", None) is not None,
    "--source-kind": lambda a: getattr(a, "source_kind", None) is not None,
    "--career-successor": lambda a: getattr(a, "career_successor", None) is not None,
    "--career-successor-sha256": lambda a: getattr(a, "career_successor_sha256", None) is not None,
    "--uncertainty": lambda a: getattr(a, "uncertainty", None) is not None,
}
#: The explicit career successor applies to the two career queries only.
_SUCCESSOR = {"--career-successor", "--career-successor-sha256"}
_PAGED = {"--limit", "--offset", "--all"}


def _refuse_modifiers(args: argparse.Namespace, query: str, allowed: set[str]) -> None:
    given = sorted(name for name, test in _MODIFIERS.items() if test(args))
    extra = [name for name in given if name not in allowed]
    if extra:
        raise StaffQueryError(
            f"{extra} do not apply to {query}; refusing rather than ignoring them"
        )


def _page(args: argparse.Namespace, *, default: int | None) -> dict[str, Any]:
    if getattr(args, "all", False) and getattr(args, "limit", None) is not None:
        raise StaffQueryError("--all and --limit are mutually exclusive")
    if getattr(args, "all", False):
        limit = None
    elif getattr(args, "limit", None) is not None:
        limit = args.limit
    else:
        limit = default
    offset = getattr(args, "offset", None)
    return {"limit": limit, "offset": 0 if offset is None else offset}


def _cycle36_dispatch(conn: sqlite3.Connection, args: argparse.Namespace) -> Any:
    from aggie_analytics.cycle36 import release_query

    try:
        # Every national answer is bound to a registered release version
        # first; an unregistered or undeclared version is refused here
        # rather than answered from whichever tables exist.
        binding = release_query.release_version_binding(conn)
        payload = _cycle36_route(conn, args, release_query)
    except release_query.Cycle36QueryError as exc:
        raise StaffQueryError(str(exc)) from exc
    except ValueError as exc:
        # A career successor refusal raised while rows are served (changed raw bytes or predecessor binding).
        from aggie_analytics.cycle37 import career_successor  # noqa: PLC0415

        if isinstance(exc, career_successor.CareerSuccessorError):
            raise StaffQueryError(str(exc)) from exc
        raise
    if isinstance(payload, dict):
        payload.setdefault("release_version_binding", binding)
    return payload


def _cycle36_route(conn: sqlite3.Connection, args: argparse.Namespace, release_query: Any) -> Any:
    default = release_query.DEFAULT_PAGE_LIMIT
    if args.coverage:
        _refuse_modifiers(args, "--coverage", set())
        return release_query.coverage(conn)
    if args.provenance is not None:
        _refuse_modifiers(args, "--provenance", set())
        return release_query.provenance(conn, observation_id=args.provenance or None)
    if args.unresolved:
        _refuse_modifiers(args, "--unresolved", set())
        return release_query.unresolved_records(conn)
    if args.scheme:
        _refuse_modifiers(args, "--scheme", _PAGED)
        return release_query.schemes(
            conn, team=args.team, season=args.season, **_page(args, default=default)
        )
    if args.responsibility:
        _refuse_modifiers(
            args, "--responsibility", _PAGED | {"--legacy-audit", "--disposition", "--source-kind"}
        )
        return release_query.responsibilities(
            conn,
            team=args.team,
            season=args.season,
            person=args.person,
            disposition=args.disposition,
            source_kind=args.source_kind,
            legacy_audit=args.legacy_audit,
            **_page(args, default=default),
        )
    if getattr(args, "career", False):
        _refuse_modifiers(
            args, "--career",
            _PAGED | _SUCCESSOR | {"--legacy-audit", "--role", "--family", "--pageid", "--uncertainty"},
        )
        return release_query.career_listing(
            conn,
            team=args.team,
            season=args.season,
            division=args.division,
            role=args.role,
            family=args.family,
            person=args.person,
            pageid=args.pageid,
            legacy_audit=args.legacy_audit,
            career_successor=_career_successor(conn, args),
            uncertainty=args.uncertainty,
            **_page(args, default=default),
        )
    if args.seasons_for_team:
        _refuse_modifiers(args, "--seasons-for-team", set())
        if not args.team:
            raise StaffQueryError("--seasons-for-team requires --team")
        return release_query.program_seasons(conn, team=args.team)
    if args.division or (args.season and not args.team):
        _refuse_modifiers(args, "a season population query", set())
        if not args.season:
            raise StaffQueryError("--division requires --season")
        return release_query.season_division_population(
            conn, season=args.season, division=args.division
        )
    if args.person:
        _refuse_modifiers(args, "--person", _PAGED | _SUCCESSOR | {"--legacy-audit", "--pageid"})
        # A person's career is returned whole unless a page is asked for,
        # which is what this query always did.
        return release_query.coach_career(
            conn,
            person=args.person,
            legacy_audit=args.legacy_audit,
            pageid=args.pageid,
            career_successor=_career_successor(conn, args),
            **_page(args, default=None),
        )
    if args.team and args.season:
        _refuse_modifiers(args, "a team-season staff query", set())
        return release_query.team_staff(conn, team=args.team, season=args.season)
    raise StaffQueryError(
        "specify --team/--season, --team --seasons-for-team, --season "
        "[--division], --person, --career, --unresolved, --scheme, "
        "--responsibility, --coverage or --provenance"
    )


def _career_successor(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any] | None:
    """Validate and attach the named career successor, or None when none was named."""

    if getattr(args, "career_successor_sha256", None) and not getattr(args, "career_successor", None):
        raise StaffQueryError("--career-successor-sha256 pins a successor that was not named")
    if getattr(args, "uncertainty", None) and not getattr(args, "career_successor", None):
        raise StaffQueryError("--uncertainty is carried only by a named --career-successor")
    if not getattr(args, "career_successor", None):
        return None
    from aggie_analytics.cycle37 import career_successor  # noqa: PLC0415

    try:
        return career_successor.attach_successor(
            conn, args.career_successor, database=Path(args.database),
            expected_sha256=getattr(args, "career_successor_sha256", None),
        )
    except career_successor.CareerSuccessorError as exc:
        raise StaffQueryError(str(exc)) from exc


def _legacy_dispatch(conn: sqlite3.Connection, args: argparse.Namespace) -> Any:
    # A national-release flag answered from a schema that has no such table
    # would be an invented answer. It is refused by name instead.
    unsupported = [
        name
        for name, requested in (
            ("--division", bool(args.division)),
            ("--seasons-for-team", args.seasons_for_team),
            ("--scheme", args.scheme),
            ("--responsibility", args.responsibility),
            ("--coverage", args.coverage),
            ("--provenance", args.provenance is not None),
            ("--career", bool(getattr(args, "career", False))),
            *((name, test(args)) for name, test in _MODIFIERS.items()),
        )
        if requested
    ]
    if unsupported:
        raise StaffQueryError(
            f"{unsupported} are national-release queries and this database is "
            f"a {cycle35_query.schema_kind(conn)}. Refusing to answer them "
            f"from a schema that does not carry those tables."
        )
    # Every legacy answer is returned inside an envelope that says which of
    # the supplied keys this database actually knows. The rows keep their
    # original shape; what changes is that an empty list is no longer
    # ambiguous between "none" and "not in this release".
    kind = cycle35_query.schema_kind(conn)
    if args.unresolved:
        rows = unresolved_roles(conn)
        keys: dict[str, Any] = {}
    elif args.person:
        rows = coach_career(conn, person=args.person)
        keys = _key_resolution(conn, kind, person=args.person)
    elif args.team and args.season:
        rows = team_staff(conn, team=args.team, season=args.season)
        keys = _key_resolution(conn, kind, team=args.team, season=args.season)
    else:
        raise StaffQueryError("specify --team/--season, --person, or --unresolved")

    return {
        "schema_kind": kind,
        "query": {
            "team": args.team,
            "season": args.season,
            "person": args.person,
            "unresolved": args.unresolved,
        },
        "key_resolution": keys,
        "answerable": keys.get("all_requested_keys_known", True),
        "row_count": len(rows),
        "rows": rows,
    }


def _key_resolution(
    conn: sqlite3.Connection, kind: str, **keys: Any
) -> dict[str, Any]:
    if kind == cycle35_query.SCHEMA_KIND_CYCLE35:
        return cycle35_query.key_resolution(conn, **keys)
    # The flat cycle33 schema has no canonical key tables; reporting the
    # distinct values it does hold is the honest equivalent.
    report: dict[str, Any] = {}
    if keys.get("team") is not None:
        values = {
            str(row[0])
            for row in conn.execute("SELECT DISTINCT team FROM staff_role_cells")
        }
        report["team"] = {
            "requested": keys["team"],
            "known": str(keys["team"]) in values,
        }
    if keys.get("season") is not None:
        values = {
            str(row[0])
            for row in conn.execute("SELECT DISTINCT season FROM staff_role_cells")
        }
        report["season"] = {
            "requested": str(keys["season"]),
            "known": str(keys["season"]) in values,
            "season_value_count": len(values),
        }
    if keys.get("person") is not None:
        values = {
            str(row[0])
            for row in conn.execute("SELECT DISTINCT person FROM staff_role_cells")
        }
        report["person"] = {
            "requested": keys["person"],
            "known": str(keys["person"]) in values,
        }
    report["all_requested_keys_known"] = all(
        entry["known"] for entry in report.values() if isinstance(entry, dict)
    )
    return report


if __name__ == "__main__":
    raise SystemExit(main())

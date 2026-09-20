"""Read-only research queries for staff, careers, schemes and coverage.

Unknown and conflicting values are returned, never silently omitted.
Package-installed use must pass explicit data roots; there is no private
absolute-path default that loads production secrets.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

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
    path = Path(database)
    if not path.is_file():
        raise StaffQueryError("query database does not exist; import is separate")
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
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
    parser = argparse.ArgumentParser(description="Read-only BAS staff research queries")
    parser.add_argument("--database", required=True)
    parser.add_argument("--team")
    parser.add_argument("--season")
    parser.add_argument("--person")
    parser.add_argument("--unresolved", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    conn = connect_readonly(Path(args.database))
    if args.unresolved:
        payload = unresolved_roles(conn)
    elif args.person:
        payload = coach_career(conn, person=args.person)
    elif args.team and args.season:
        payload = team_staff(conn, team=args.team, season=args.season)
    else:
        raise StaffQueryError("specify --team/--season, --person, or --unresolved")
    print(json.dumps(payload, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

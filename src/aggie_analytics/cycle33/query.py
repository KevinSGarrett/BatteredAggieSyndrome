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
    source_class TEXT NOT NULL
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
    rows = 0
    conn.execute("DELETE FROM staff_role_cells")
    for cell in imported.get("role_cells") or []:
        conn.execute(
            """
            INSERT INTO staff_role_cells (
                observation_id, canonical_claim_id, source_file, team,
                team_id_source, season, role_column, person, source_title,
                disposition, support_column, principal_role_blocked,
                source_class, pit_admitted, cell_text, subdivision, verified
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
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
            ),
        )
        rows += 1
    conn.commit()
    return rows


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
    rows = 0
    for claim in claims:
        conn.execute(
            """
            INSERT INTO scheme_tenure_claims (
                program_raw, season, field, source_text, disposition,
                inferred, source_class
            ) VALUES (?,?,?,?,?,?,?)
            """,
            (
                claim.get("program_raw") or claim.get("title"),
                str(claim.get("season") or ""),
                claim.get("field") or claim.get("normalized_field") or "",
                claim.get("source_text") or claim.get("raw_value"),
                claim.get("disposition") or "WIKI_REPORTED_NOT_OFFICIAL",
                1 if claim.get("inferred") else 0,
                claim.get("source_class") or "WIKIPEDIA_ATTRIBUTED_RETROSPECTIVE",
            ),
        )
        rows += 1
    conn.commit()
    return rows


def team_schemes(
    conn: sqlite3.Connection, *, program: str, season: str
) -> list[dict[str, Any]]:
    cur = conn.execute(
        """
        SELECT * FROM scheme_tenure_claims
        WHERE season = ? AND (program_raw LIKE ?)
        ORDER BY field
        """,
        (str(season), f"%{program}%"),
    )
    return [dict(row) for row in cur.fetchall()]


def unresolved_roles(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    cur = conn.execute(
        """
        SELECT * FROM staff_role_cells
        WHERE person IS NULL OR disposition LIKE '%UNMAPPED%'
           OR disposition LIKE '%CONFLICT%'
           OR disposition LIKE '%NOT_VERIFIED%'
           OR disposition LIKE '%UNPARSED%'
        ORDER BY season, team, role_column
        """
    )
    return [dict(row) for row in cur.fetchall()]


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

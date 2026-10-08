r"""Read-only query over the national 2016-2023 FBS retrospective history prefix (BAT-711).

``bas-national-history-query --database <canonical\...\sha256\<id>\national_history.sqlite> --grain history
--season 2019 --team org:697 --limit 50 --offset 0``

Standard library only (argparse, hashlib, json, re, sqlite3). Before any row is read the database is verified:

* the file sits at ``<canonical root>/sha256/<id>/national_history.sqlite`` and its run manifest at
  ``<data root>/manifests/<population>/sha256/<id>/run_manifest.json``;
* ``<id>`` equals the SHA-256 of the manifest's canonical database identity document, which names the database
  file's own SHA-256, the content identity of the payloads it holds and every table count; the database bytes must
  hash to that value (row tampering is refused; a tamper that also rewrites the manifest changes the identity, which
  no longer matches the directory);
* the database meta table must carry the known schema version and the same content identity and contract hash;
* an ``--expect-identity`` that differs is refused as a stale identity;
* the connection is opened read-only through :mod:`aggie_analytics.readonly_sqlite`, so no statement can write and
  SQLite opens exactly the literal local file named (long and extended-length Windows locations included); a network,
  device or non-literal location is refused before any file is touched.

Grains: ``targets`` (target contests), ``history`` (two team/current-opponent views per target) and ``exclusions``
(every other 2016-2023 parent contest with exact reasons). Each returns exact totals with ``--limit``/``--offset``
or ``--all`` in the payload's own order. Target outcome labels are never served. A season outside 2016-2023 returns
``NOT_YET_AUDITED`` with no rows. Every record is RETROSPECTIVE_OBSERVATION_ONLY with calendar-order-only temporal
basis; ``--require-pit`` is always refused (PIT_ELIGIBILITY_NOT_ESTABLISHED). Unknown or abbreviated flags,
negative paging and malformed team/contest keys are refused.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Sequence

from aggie_analytics import readonly_sqlite

DB_FILE_NAME = "national_history.sqlite"
DB_SCHEMA_VERSION = "BAS-NATIONAL-HISTORY-PREFIX-DB-1"
DATABASE_DOCUMENT_SCHEMA = "BAS-NATIONAL-HISTORY-PREFIX-DATABASE-1"
TARGET_SEASONS = tuple(range(2016, 2024))
OUT_OF_SCOPE_STATE = "NOT_YET_AUDITED"
IN_SCOPE_STATE = "RETROSPECTIVE_2016_2023"
ROW_LABELS = {"observation_authority": "RETROSPECTIVE_OBSERVATION_ONLY",
              "pit_eligibility": "PIT_ELIGIBILITY_NOT_ESTABLISHED",
              "temporal_basis": "CALENDAR_DATE_ORDER_ONLY_NOT_PUBLICATION_TIME"}
IDENTITY_RE = re.compile(r"^[0-9a-f]{64}$")
TEAM_RE = re.compile(r"^(?:org:)?([0-9]{1,12})$")
CONTEST_RE = re.compile(r"^(?:ncaa|nolink|cfbd):[^\x00-\x1f]{1,200}$")
TABLES = ("meta", "targets", "history", "exclusions", "target_labels")

#: grain -> (table, filter -> SQL predicate; each "?" receives the same value)
GRAINS: dict[str, tuple[str, dict[str, str]]] = {
    "targets": ("targets", {"season": "season = ?", "team": "(a_key = ? OR b_key = ?)", "contest": "contest_key = ?"}),
    "history": ("history", {"season": "season = ?", "team": "team_key = ?", "contest": "target_contest_key = ?"}),
    "exclusions": ("exclusions", {"season": "season = ?", "team": "(a_key = ? OR b_key = ?)",
                                  "contest": "contest_key = ?"}),
}


class HistoryQueryError(ValueError):
    """A refused query; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def manifest_path_for(database: Path) -> Path:
    """``<data>/canonical/<population>/sha256/<id>/<db>`` -> ``<data>/manifests/<population>/sha256/<id>/run_manifest.json``."""
    db = Path(database).resolve()
    population_root = db.parent.parent.parent
    return population_root.parent.parent / "manifests" / population_root.name / "sha256" / db.parent.name / \
        "run_manifest.json"


def normalize_team(value: str) -> str:
    match = TEAM_RE.match(str(value).strip())
    if not match:
        raise HistoryQueryError("TEAM_KEY_INVALID", f"team must be an organization key org:<digits>, got {value!r}")
    return f"org:{int(match.group(1))}"


def normalize_contest(value: str) -> str:
    text = str(value)
    if text.isdigit() and len(text) <= 12:
        return f"ncaa:{text}"
    if not CONTEST_RE.match(text):
        raise HistoryQueryError("CONTEST_KEY_INVALID", f"contest must be a parent contest key, got {value!r}")
    return text


def verify_database(database: Path, *, expect_identity: str | None = None) -> dict[str, Any]:
    """Verify location, manifest identity, database bytes and expected identity; return the bound identity."""
    literal_location(database)
    db = Path(database)
    if not db.is_file():
        raise HistoryQueryError("DATABASE_MISSING", f"no database file at {db}")
    if db.name != DB_FILE_NAME or db.resolve().parent.parent.name != "sha256":
        raise HistoryQueryError("DATABASE_LOCATION_INVALID", "the database must sit at <root>/sha256/<id>/" + DB_FILE_NAME)
    identity = db.resolve().parent.name
    if not IDENTITY_RE.match(identity):
        raise HistoryQueryError("DATABASE_LOCATION_INVALID", f"directory name {identity!r} is not a SHA-256 identity")
    manifest_path = manifest_path_for(db)
    if not manifest_path.is_file():
        raise HistoryQueryError("MANIFEST_MISSING", f"no run manifest at {manifest_path}")
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        identity_document = document["identity_document"]
        computed = hashlib.sha256(canonical_json_bytes(identity_document)).hexdigest()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HistoryQueryError("MANIFEST_MALFORMED", str(exc)) from exc
    if computed != identity or document.get("identity") != identity:
        raise HistoryQueryError("DATABASE_IDENTITY_MISMATCH",
                                f"manifest identity document hashes to {computed}, directory is {identity}")
    if (identity_document.get("stage"), identity_document.get("schema"), identity_document.get("db_schema_version")) \
            != ("history-database", DATABASE_DOCUMENT_SCHEMA, DB_SCHEMA_VERSION):
        raise HistoryQueryError("DATABASE_SCHEMA_UNSUPPORTED", "the manifest is not a known history-database manifest")
    expected_db_sha = (identity_document.get("outputs") or {}).get(DB_FILE_NAME)
    actual_db_sha = _sha256_file(db)
    if expected_db_sha != actual_db_sha:
        raise HistoryQueryError("DATABASE_TAMPERED",
                                f"database bytes hash to {actual_db_sha}, manifest names {expected_db_sha}")
    if expect_identity is not None and expect_identity != identity:
        raise HistoryQueryError("STALE_DATABASE_IDENTITY", f"expected {expect_identity}, found {identity}")
    return {"database_identity": identity, "database_sha256": actual_db_sha, "manifest": str(manifest_path),
            "content_identity": identity_document.get("content_identity"),
            "contract_sha256": identity_document.get("contract_sha256"),
            "table_counts": identity_document.get("table_counts")}


def literal_location(database: Path) -> str:
    """The literal local file ``database`` names; a network, device or non-literal location is refused lexically."""
    try:
        return readonly_sqlite.literal_path(database)
    except readonly_sqlite.DatabaseLocationError as exc:
        raise HistoryQueryError(exc.code, exc.detail) from exc


def connect_readonly(database: Path) -> sqlite3.Connection:
    try:
        conn = readonly_sqlite.connect_readonly(database)
    except readonly_sqlite.DatabaseLocationError as exc:
        raise HistoryQueryError(exc.code, exc.detail) from exc
    conn.row_factory = sqlite3.Row
    return conn


class NationalHistoryDatabase:
    """A verified, read-only handle on one content-addressed national history-prefix database."""

    def __init__(self, database: Path, *, expect_identity: str | None = None) -> None:
        self.binding = verify_database(database, expect_identity=expect_identity)
        self.conn = connect_readonly(database)
        try:
            meta = {row["key"]: row["value"] for row in self.conn.execute("SELECT key, value FROM meta")}
            counts = {table: self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES}
        except sqlite3.DatabaseError as exc:
            self.conn.close()
            raise HistoryQueryError("DATABASE_SCHEMA_UNSUPPORTED", str(exc)) from exc
        problems = []
        if meta.get("schema_version") != DB_SCHEMA_VERSION:
            problems.append(("DATABASE_SCHEMA_UNSUPPORTED", f"schema {meta.get('schema_version')!r}"))
        elif meta.get("content_identity") != self.binding["content_identity"] or \
                meta.get("contract_sha256") != self.binding["contract_sha256"]:
            problems.append(("DATABASE_IDENTITY_MISMATCH", "database meta and manifest identities differ"))
        elif counts != self.binding["table_counts"]:
            problems.append(("DATABASE_COUNT_MISMATCH", f"table counts {counts} != {self.binding['table_counts']}"))
        elif json.loads(meta.get("row_labels") or "null") != ROW_LABELS:
            problems.append(("DATABASE_SCHEMA_UNSUPPORTED", "row labels differ from the retrospective-only labels"))
        if problems:
            self.conn.close()
            raise HistoryQueryError(*problems[0])
        self.meta = meta

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "NationalHistoryDatabase":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def query(self, grain: str, *, season: int | None = None, team: str | None = None, contest: str | None = None,
              limit: int | None = 50, offset: int = 0, all_rows: bool = False) -> dict[str, Any]:
        if grain not in GRAINS:
            raise HistoryQueryError("UNKNOWN_GRAIN", f"grain must be one of {sorted(GRAINS)}")
        if offset < 0:
            raise HistoryQueryError("NEGATIVE_OFFSET", "offset must be zero or positive")
        if limit is not None and limit < 0:
            raise HistoryQueryError("NEGATIVE_LIMIT", "limit must be zero or positive")
        filters: dict[str, Any] = {}
        if season is not None:
            if isinstance(season, bool) or not isinstance(season, int):
                raise HistoryQueryError("SEASON_INVALID", f"season must be an integer, got {season!r}")
            filters["season"] = season
        if team is not None:
            filters["team"] = normalize_team(team)
        if contest is not None:
            filters["contest"] = normalize_contest(contest)
        result: dict[str, Any] = {"database_identity": self.binding["database_identity"],
                                  "content_identity": self.binding["content_identity"],
                                  "contract_sha256": self.binding["contract_sha256"], "grain": grain,
                                  "filters": filters, "offset": offset, "limit": None if all_rows else limit,
                                  **ROW_LABELS, "target_labels_served": False}
        if season is not None and season not in TARGET_SEASONS:
            result.update(season_scope_state=OUT_OF_SCOPE_STATE, total=0, returned=0, rows=[],
                          note="season outside the retrospective 2016-2023 tranche; no rows are fabricated")
            return result
        table, predicates = GRAINS[grain]
        clauses, params = [], []
        for name, value in filters.items():
            clauses.append(predicates[name])
            params.extend([value] * predicates[name].count("?"))
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        total = self.conn.execute(f"SELECT COUNT(*) FROM {table}{where}", params).fetchone()[0]
        sql = f"SELECT record FROM {table}{where} ORDER BY ord"
        page_params = list(params)
        if not all_rows:
            sql += " LIMIT ? OFFSET ?"
            page_params += [limit, offset]
        elif offset:
            sql += " LIMIT -1 OFFSET ?"
            page_params += [offset]
        rows = [json.loads(row["record"]) for row in self.conn.execute(sql, page_params)]
        returned = len(rows)
        result.update(season_scope_state=IN_SCOPE_STATE if season is not None else "ALL_RETROSPECTIVE_SEASONS",
                      total=total, returned=returned, rows=rows,
                      next_offset=offset + returned if offset + returned < total else None)
        return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bas-national-history-query", allow_abbrev=False,
                                     description="Read-only national 2016-2023 FBS retrospective history-prefix "
                                                 "query (calendar order only; not PIT eligible).")
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--grain", required=True, choices=sorted(GRAINS))
    parser.add_argument("--season", type=int, default=None)
    parser.add_argument("--team", default=None, help="organization key org:<digits> or bare digits")
    parser.add_argument("--contest", default=None, help="parent contest key, e.g. ncaa:1519847, or bare digits")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--all", dest="all_rows", action="store_true")
    parser.add_argument("--expect-identity", default=None)
    parser.add_argument("--require-pit", action="store_true",
                        help="refused: no row is PIT eligible (RETROSPECTIVE_OBSERVATION_ONLY)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.require_pit:
            raise HistoryQueryError("PIT_ELIGIBILITY_NOT_ESTABLISHED",
                                    "every row is RETROSPECTIVE_OBSERVATION_ONLY; calendar order is not PIT authority")
        with NationalHistoryDatabase(args.database, expect_identity=args.expect_identity) as db:
            result = db.query(args.grain, season=args.season, team=args.team, contest=args.contest,
                              limit=args.limit, offset=args.offset, all_rows=args.all_rows)
    except HistoryQueryError as exc:
        print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

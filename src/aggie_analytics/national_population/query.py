r"""Read-only query over the national Division I program-season and contest population (BAT-710).

``bas-national-population-query --database <canonical\...\sha256\<id>\national_population.sqlite> --grain contest
--season 2018 --team "Missouri St." --limit 50 --offset 0``

Standard library only (argparse, hashlib, json, os, re, sqlite3, urllib.parse). Before any row is read the database
is verified:

* the file sits at ``<canonical root>/sha256/<id>/national_population.sqlite`` and its run manifest at
  ``<data root>/manifests/<population>/sha256/<id>/run_manifest.json`` (or ``--manifest``);
* ``<id>`` equals the SHA-256 of the manifest's canonical identity document, which names the database file's own
  SHA-256; the database bytes must hash to that value (row tampering is refused, and a tamper that also rewrites
  the manifest changes the identity, which no longer matches the directory);
* an ``--expect-identity`` that differs is refused as a stale identity;
* the connection is opened read-only through the BAT-717 literal-location core -- a byte-identical copy of the block in
  :mod:`aggie_analytics.readonly_sqlite`, carried here because this module is standard-library only -- so no statement
  can write and SQLite opens exactly the literal local file named (long and extended-length Windows locations
  included); a network, device or non-literal location is refused before any file is touched.

Every grain returns exact totals with ``--limit``/``--offset`` or ``--all``. A season outside 2016-2025 returns
``NOT_YET_AUDITED`` with no rows; nothing is fabricated for an out-of-tranche season. Unknown flags, flag
abbreviations, a negative offset or limit and a filter that does not apply to the chosen grain are refused.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Sequence

DB_FILE_NAME = "national_population.sqlite"
DB_SCHEMA_VERSION = "BAS-NATIONAL-DI-POPULATION-DB-1"
DELIVERY_SEASONS = tuple(range(2016, 2026))
OUT_OF_SCOPE_STATE = "NOT_YET_AUDITED"
IDENTITY_RE = re.compile(r"^[0-9a-f]{64}$")

#: grain -> (table, stable ordering)
GRAINS = {
    "program-season": ("program_season", "season, ncaa_org_id, cell_key"),
    "contest": ("contest", "season, contest_date, contest_key"),
    "orientation": ("orientation", "season, contest_date, contest_key, side"),
}
#: filter -> grain -> SQL predicate with one or two "?" placeholders filled with the same value
FILTERS: dict[str, dict[str, str]] = {
    "season": {"program-season": "season = ?", "contest": "season = ?", "orientation": "season = ?"},
    "division": {"program-season": "division_label = ?",
                 "contest": "(a_division_label = ? OR b_division_label = ?)",
                 "orientation": "team_division_label = ?"},
    "org": {"program-season": "ncaa_org_id = ?", "contest": "(a_org_id = ? OR b_org_id = ?)",
            "orientation": "team_org_id = ?"},
    "team": {"program-season": "team_name = ? COLLATE NOCASE",
             "contest": "(a_team_name = ? COLLATE NOCASE OR b_team_name = ? COLLATE NOCASE)",
             "orientation": "team_name = ? COLLATE NOCASE"},
    "classification_pair": {"contest": "classification_pair = ?", "orientation": "classification_pair = ?"},
    "disposition": {"program-season": "disposition = ?", "contest": "disposition = ?",
                    "orientation": "disposition = ?"},
    "reconciliation_state": {"contest": "reconciliation_state = ?", "orientation": "reconciliation_state = ?"},
}


class NationalQueryError(ValueError):
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
    identity_dir = db.parent
    population_root = identity_dir.parent.parent
    return population_root.parent.parent / "manifests" / population_root.name / "sha256" / identity_dir.name / \
        "run_manifest.json"


def verify_database(database: Path, *, manifest: Path | None = None,
                    expect_identity: str | None = None) -> dict[str, Any]:
    """Verify location, manifest identity, database bytes and expected identity; return the bound identity."""
    literal_location(database)
    db = Path(database)
    if not db.is_file():
        raise NationalQueryError("DATABASE_MISSING", f"no database file at {db}")
    if db.name != DB_FILE_NAME or db.resolve().parent.parent.name != "sha256":
        raise NationalQueryError("DATABASE_LOCATION_INVALID", "the database must sit at <root>/sha256/<id>/" + DB_FILE_NAME)
    identity = db.resolve().parent.name
    if not IDENTITY_RE.match(identity):
        raise NationalQueryError("DATABASE_LOCATION_INVALID", f"directory name {identity!r} is not a SHA-256 identity")
    manifest_path = Path(manifest) if manifest is not None else manifest_path_for(db)
    if not manifest_path.is_file():
        raise NationalQueryError("MANIFEST_MISSING", f"no run manifest at {manifest_path}")
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        identity_document = document["identity_document"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise NationalQueryError("MANIFEST_MALFORMED", str(exc)) from exc
    computed = hashlib.sha256(canonical_json_bytes(identity_document)).hexdigest()
    if computed != identity or document.get("identity") != identity:
        raise NationalQueryError("DATABASE_IDENTITY_MISMATCH",
                                 f"manifest identity document hashes to {computed}, directory is {identity}")
    if identity_document.get("stage") != "query-db":
        raise NationalQueryError("DATABASE_IDENTITY_MISMATCH", "the manifest is not a query-db stage manifest")
    expected_db_sha = (identity_document.get("outputs") or {}).get(DB_FILE_NAME)
    actual_db_sha = _sha256_file(db)
    if expected_db_sha != actual_db_sha:
        raise NationalQueryError("DATABASE_TAMPERED", f"database bytes hash to {actual_db_sha}, manifest names {expected_db_sha}")
    if expect_identity is not None and expect_identity != identity:
        raise NationalQueryError("STALE_DATABASE_IDENTITY", f"expected {expect_identity}, found {identity}")
    return {"database_identity": identity, "database_sha256": actual_db_sha, "manifest": str(manifest_path),
            "contract_sha256": identity_document.get("contract_sha256"),
            "upstream": identity_document.get("upstream")}


# ---- BEGIN BAT-717 LITERAL-LOCATION CORE (byte-identical in aggie_analytics.readonly_sqlite,
# ---- aggie_analytics.national_population.query and aggie_analytics.national_history.query) ----
_LOCATION_UNSUPPORTED = "DATABASE_LOCATION_UNSUPPORTED"
_LOCATION_NOT_LITERAL = "DATABASE_LOCATION_NOT_LITERAL"
_EXTENDED_PREFIX = "\\\\?\\"
_DEVICE_PREFIX = "\\\\.\\"
_VERBATIM_DRIVE = re.compile(r"\\\\\?\\[A-Za-z]:\\")
_DEVICE_DRIVE = re.compile(r"\\\\\.\\[A-Za-z]:\\")
_DRIVE_ABSOLUTE = re.compile(r"[A-Za-z]:\\")


class _LocationError(ValueError):
    """A database location that cannot be opened as exactly the literal local file it names."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _literal_path(database: str | os.PathLike[str]) -> str:
    """The absolute path naming exactly the local file ``database`` names, in the form SQLite will open.

    Purely lexical on Windows: an unsupported location is refused before any filesystem access."""

    try:
        text = os.fsdecode(os.fspath(database))
    except TypeError as exc:
        raise _LocationError(_LOCATION_UNSUPPORTED, f"not a filesystem path: {database!r}") from exc
    if not text or "\x00" in text:
        raise _LocationError(_LOCATION_UNSUPPORTED, f"an empty path or one holding a NUL character: {text!r}")
    if os.name != "nt":
        return os.path.realpath(text)
    if text[:1] in "\\/" and text[1:2] in ("\\", "/"):
        if _VERBATIM_DRIVE.match(text):
            normal = os.path.abspath(text)
            if normal != text:
                raise _LocationError(_LOCATION_NOT_LITERAL, (
                    f"SQLite would open {normal!r}, not the verbatim {text!r} (a trailing dot, a '.' or '..' "
                    "component or a forward slash in an extended-length path names a different file than SQLite "
                    "opens)"))
            return text
        normal = os.path.abspath(text)
        if _DEVICE_DRIVE.match(normal):
            # \\.\X:\... is the local drive device: Win32 normalizes it like an ordinary path and it names the same
            # file as X:\... -- the spelling SQLite is given.
            return normal[len(_DEVICE_PREFIX):]
        raise _LocationError(_LOCATION_UNSUPPORTED, (
            f"{text!r} is a network share or a device or namespace path; only a local drive path, its native "
            "extended-length form \\\\?\\X:\\... or its local device form \\\\.\\X:\\... is supported"))
    location = os.path.abspath(text)
    if not _DRIVE_ABSOLUTE.match(location):
        raise _LocationError(_LOCATION_UNSUPPORTED, f"{text!r} resolves to {location!r}, not a local drive path")
    return location


def _location_uri(location: str, immutable: bool) -> str:
    """The read-only ``file:`` URI of a literal path, every reserved character escaped."""

    if os.name == "nt" and location.startswith(_EXTENDED_PREFIX):
        body = "file:" + urllib.parse.quote(location, safe="")
    else:
        body = Path(location).as_uri()
    return body + ("?mode=ro&immutable=1" if immutable else "?mode=ro")


def _same_object(opened: str, location: str) -> bool:
    try:
        first, second = os.stat(opened), os.stat(location)
    except (OSError, ValueError):
        return os.path.normcase(opened) == os.path.normcase(location)
    if first.st_ino and second.st_ino:
        return (first.st_dev, first.st_ino) == (second.st_dev, second.st_ino)
    return os.path.normcase(opened) == os.path.normcase(location)


def _verify_opened(conn: sqlite3.Connection, schema: str, location: str) -> str:
    """Confirm that the database SQLite opened as ``schema`` is the file at ``location``; return SQLite's name."""

    opened = {str(row[1]): str(row[2] or "") for row in conn.execute("PRAGMA database_list")}.get(schema)
    if not opened or not _same_object(opened, location):
        raise _LocationError(_LOCATION_NOT_LITERAL, f"SQLite opened {opened!r} as {schema}, not {location!r}")
    return opened


def _connect_literal(database: str | os.PathLike[str], immutable: bool) -> sqlite3.Connection:
    """A read-only connection to exactly the literal file ``database`` names (never created, never writable)."""

    location = _literal_path(database)
    conn = sqlite3.connect(_location_uri(location, immutable), uri=True)
    try:
        _verify_opened(conn, "main", location)
    except BaseException:
        conn.close()
        raise
    return conn
# ---- END BAT-717 LITERAL-LOCATION CORE ----


def literal_location(database: Path) -> str:
    """The literal local file ``database`` names; a network, device or non-literal location is refused lexically."""
    try:
        return _literal_path(database)
    except _LocationError as exc:
        raise NationalQueryError(exc.code, exc.detail) from exc


def connect_readonly(database: Path) -> sqlite3.Connection:
    try:
        conn = _connect_literal(database, False)
    except _LocationError as exc:
        raise NationalQueryError(exc.code, exc.detail) from exc
    conn.row_factory = sqlite3.Row
    return conn


class NationalPopulationDatabase:
    """A verified, read-only handle on one content-addressed national population database."""

    def __init__(self, database: Path, *, manifest: Path | None = None, expect_identity: str | None = None) -> None:
        self.binding = verify_database(database, manifest=manifest, expect_identity=expect_identity)
        self.conn = connect_readonly(database)
        meta = {row["key"]: row["value"] for row in self.conn.execute("SELECT key, value FROM meta")}
        if meta.get("schema_version") != DB_SCHEMA_VERSION:
            raise NationalQueryError("DATABASE_SCHEMA_UNSUPPORTED", f"schema {meta.get('schema_version')!r}")
        if meta.get("contract_sha256") != self.binding["contract_sha256"]:
            raise NationalQueryError("DATABASE_IDENTITY_MISMATCH", "database and manifest contract hashes differ")
        self.meta = meta

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "NationalPopulationDatabase":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def query(self, grain: str, *, filters: dict[str, Any] | None = None, limit: int | None = 50, offset: int = 0,
              all_rows: bool = False) -> dict[str, Any]:
        if grain not in GRAINS:
            raise NationalQueryError("UNKNOWN_GRAIN", f"grain must be one of {sorted(GRAINS)}")
        filters = {k: v for k, v in (filters or {}).items() if v is not None}
        if offset < 0:
            raise NationalQueryError("NEGATIVE_OFFSET", "offset must be zero or positive")
        if limit is not None and limit < 0:
            raise NationalQueryError("NEGATIVE_LIMIT", "limit must be zero or positive")
        result: dict[str, Any] = {"database_identity": self.binding["database_identity"],
                                  "contract_sha256": self.binding["contract_sha256"], "grain": grain,
                                  "filters": filters, "offset": offset, "limit": None if all_rows else limit}
        # Filters are validated for the grain before the season scope is evaluated (contract filter_validation).
        clauses, params = [], []
        for name in filters:
            if FILTERS.get(name, {}).get(grain) is None:
                raise NationalQueryError("FILTER_NOT_APPLICABLE", f"filter {name!r} does not apply to grain {grain!r}")
        season = filters.get("season")
        if season is not None:
            season = int(season)
            filters["season"] = season
            if season not in DELIVERY_SEASONS:
                result.update(season_scope_state=OUT_OF_SCOPE_STATE, total=0, returned=0, rows=[],
                              note="season outside the delivered 2016-2025 tranche; no rows are fabricated")
                return result
        for name, value in filters.items():
            predicate = FILTERS[name][grain]
            clauses.append(predicate)
            params.extend([value] * predicate.count("?"))
        table, order = GRAINS[grain]
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        total = self.conn.execute(f"SELECT COUNT(*) FROM {table}{where}", params).fetchone()[0]
        sql = f"SELECT * FROM {table}{where} ORDER BY {order}"
        page_params = list(params)
        if not all_rows:
            sql += " LIMIT ? OFFSET ?"
            page_params += [limit, offset]
        elif offset:
            sql += " LIMIT -1 OFFSET ?"
            page_params += [offset]
        rows = [dict(row) for row in self.conn.execute(sql, page_params)]
        result.update(season_scope_state="DELIVERED_2016_2025" if season is not None else "ALL_DELIVERED_SEASONS",
                      total=total, returned=len(rows), rows=rows)
        return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bas-national-population-query", allow_abbrev=False,
                                     description="Read-only national Division I population query (2016-2025).")
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--expect-identity", default=None)
    parser.add_argument("--grain", required=True, choices=sorted(GRAINS))
    parser.add_argument("--season", type=int, default=None)
    parser.add_argument("--division", default=None)
    parser.add_argument("--org", default=None)
    parser.add_argument("--team", default=None)
    parser.add_argument("--classification-pair", dest="classification_pair", default=None)
    parser.add_argument("--disposition", default=None)
    parser.add_argument("--reconciliation-state", dest="reconciliation_state", default=None)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--all", dest="all_rows", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    filters = {"season": args.season, "division": args.division, "org": args.org, "team": args.team,
               "classification_pair": args.classification_pair, "disposition": args.disposition,
               "reconciliation_state": args.reconciliation_state}
    try:
        with NationalPopulationDatabase(args.database, manifest=args.manifest,
                                        expect_identity=args.expect_identity) as db:
            result = db.query(args.grain, filters=filters, limit=args.limit, offset=args.offset,
                              all_rows=args.all_rows)
    except NationalQueryError as exc:
        print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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

BAT-718 (Cycle #46 TP46-A01) adds an explicit, never-default cached-source reconciliation sidecar for the accepted
2024-2025 parent contests: ``--reconciliation <...\sha256\<id>\national_population_reconciliation.sqlite>`` with
``--grain parent-reconciliation`` or ``--grain provider-reconciliation`` and the ``--season``, ``--team``,
``--contest`` and ``--disposition`` filters. Before any sidecar row is served the reader verifies the sidecar's
location, manifest identity and bytes, the accepted parent and every bound cached input (provider captures, their
capture receipts, the accepted crosswalk and the canonical registry), then re-derives every parent and provider record,
the summary denominators and the content identity from those verified inputs and refuses any difference for its own
cause. Without ``--reconciliation`` every existing grain answers exactly as before. ``--require-pit`` is always
refused (PIT_ELIGIBILITY_NOT_ESTABLISHED).
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import html
import io
import json
import os
import re
import sqlite3
import sys
import unicodedata
import urllib.parse
from datetime import datetime, timedelta, timezone
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


# =============================================================================================== BAT-718 sidecar
# The reconciliation rules live here once, in this standard-library-only module: the producer
# (tools/build_national_population_reconciliation.py) materializes exactly what ReconciliationSidecar re-derives from
# the verified parent and cached inputs before it serves a row. The independent oracle never imports this code.

RECONCILIATION_POPULATION = "national_population_reconciliation_2024_2025"
RECONCILIATION_DB_FILE = "national_population_reconciliation.sqlite"
RECONCILIATION_SEASONS = (2024, 2025)
RECONCILIATION_CONTENT_SCHEMA = "BAS-NATIONAL-POPULATION-RECONCILIATION-CONTENT-1"
RECONCILIATION_DATABASE_SCHEMA = "BAS-NATIONAL-POPULATION-RECONCILIATION-DATABASE-1"
RECONCILIATION_DB_SCHEMA = "BAS-NATIONAL-POPULATION-RECONCILIATION-DB-1"
RECONCILIATION_PAYLOAD_SCHEMA = "BAS-NATIONAL-POPULATION-RECONCILIATION-PAYLOAD-1"
RECONCILIATION_PAYLOADS = ("parent_reconciliation.jsonl", "provider_reconciliation.jsonl", "summary.json")
RECONCILIATION_GRAINS = ("parent-reconciliation", "provider-reconciliation")
RECONCILIATION_SCOPE_OUTSIDE = "OUTSIDE_RECONCILIATION_SIDECAR_SCOPE"
RECONCILIATION_LABELS = {
    "observation_authority": "CACHED_SOURCE_RECONCILIATION_ONLY",
    "independent_truth": "NOT_ESTABLISHED_PROVIDER_MAY_SHARE_UPSTREAM_EVIDENCE",
    "pit_eligibility": "PIT_ELIGIBILITY_NOT_ESTABLISHED",
    "exposure": "EXPOSED_NOT_PROTECTED",
    "protected_lane": "RETAIN_PROTECTED_LANE_BLOCKED",
    "predictive_skill": "NOT_ESTABLISHED",
    "selection": "EXPLICIT_SIDECAR_SELECTION_ONLY_NEVER_A_DEFAULT",
}
#: The accepted BAT-554 token expansions of the parent contract (reconciliation.participant_resolution).
RECONCILIATION_TOKEN_EXPANSIONS = {
    "ala": "alabama", "ariz": "arizona", "ark": "arkansas", "caro": "carolina", "coll": "college", "colo": "colorado",
    "conn": "connecticut", "fla": "florida", "ga": "georgia", "ill": "illinois", "ind": "indiana", "ky": "kentucky",
    "la": "louisiana", "mass": "massachusetts", "mich": "michigan", "minn": "minnesota", "miss": "mississippi",
    "mo": "missouri", "neb": "nebraska", "okla": "oklahoma", "ore": "oregon", "so": "southern", "st": "state",
    "tenn": "tennessee", "tex": "texas", "va": "virginia", "wash": "washington", "wis": "wisconsin"}
#: The accepted parent cfbd_date_basis: candidate US-local calendar dates of a provider UTC instant (EDT through HST).
RECONCILIATION_LOCAL_OFFSET_HOURS = (-4, -10)
BOUND_CROSSWALK_RULES = ("NAME_CONFIRMED_BY_SCHEDULE", "NAME_COLLISION_DISAMBIGUATED_BY_SCHEDULE",
                         "SCHEDULE_FINGERPRINT_ONLY")
#: Parent contest status -> completion; every other status leaves parent completion unknown.
PARENT_COMPLETION = {"COMPLETED": True, "CANCELED": False, "NO_CONTEST": False}
COMPARABLE_CLASSIFICATIONS = {"FBS": "fbs", "FCS": "fcs"}
PROVIDER_FACT_FIELDS = ("id", "season", "seasonType", "week", "startDate", "startTimeTBD", "completed", "neutralSite",
                        "homeId", "homeTeam", "homeClassification", "homePoints", "awayId", "awayTeam",
                        "awayClassification", "awayPoints")
COMPARED_FIELDS = ("season", "date", "participants", "neutral_status", "home_orientation", "completion", "score",
                   "classification_a", "classification_b")
FIELD_RESULTS = ("AGREE", "DISAGREE", "NOT_COMPARABLE_PARENT_MISSING", "NOT_COMPARABLE_PROVIDER_MISSING",
                 "NOT_COMPARABLE_BOTH_MISSING", "NOT_COMPARABLE_PARENT_INVALID", "NOT_COMPARABLE_PROVIDER_INVALID",
                 "NOT_COMPARABLE_PARENT_NEUTRAL_NO_DESIGNATION", "NOT_COMPARABLE_PROVIDER_NEUTRAL_DESIGNATION",
                 "NOT_COMPARABLE_VOCABULARY")
PARENT_DISPOSITIONS = ("RECONCILED_FIELDS_AGREE", "RECONCILED_FIELD_CONFLICT", "CANDIDATE_PARTICIPANT_EVIDENCE_INCOMPLETE",
                       "AMBIGUOUS_PROVIDER_CANDIDATES", "UNMATCHED_DATE_OUTSIDE_LOCAL_CANDIDATES",
                       "UNMATCHED_IN_ROUTE_PROVIDER_ROW_ABSENT", "UNMATCHED_PARTICIPANT_UNBOUND",
                       "UNMATCHED_PARENT_DATE_MISSING", "OUT_OF_ROUTE_NOT_EXPECTED")
PROVIDER_DISPOSITIONS = ("RECONCILED_FIELDS_AGREE", "RECONCILED_FIELD_CONFLICT",
                         "CANDIDATE_PARTICIPANT_EVIDENCE_INCOMPLETE", "AMBIGUOUS_PARENT_CANDIDATES",
                         "DUPLICATE_PROVIDER_GAME_ID", "PROVIDER_SEASON_MISMATCH", "INVALID_PROVIDER_ROW",
                         "UNMATCHED_PARTICIPANT_UNBOUND", "UNMATCHED_DATE_OUTSIDE_LOCAL_CANDIDATES",
                         "UNMATCHED_PARENT_CONTEST_ABSENT")
RECONCILIATION_PARAMETERS = {
    "seasons": list(RECONCILIATION_SEASONS),
    "name_normalization": "BAT-554: html.unescape, NFKD then ASCII, lowercase, '&' -> ' and ', every run of "
                          "non-alphanumerics -> one space, then the token expansions",
    "token_expansions": RECONCILIATION_TOKEN_EXPANSIONS,
    "provider_local_offset_hours": list(RECONCILIATION_LOCAL_OFFSET_HOURS),
    "bound_crosswalk_rules": list(BOUND_CROSSWALK_RULES),
    "parent_completion": PARENT_COMPLETION,
    "comparable_classifications": COMPARABLE_CLASSIFICATIONS,
    "provider_fact_fields": list(PROVIDER_FACT_FIELDS),
    "compared_fields": list(COMPARED_FIELDS),
    "field_results": list(FIELD_RESULTS),
    "parent_dispositions": list(PARENT_DISPOSITIONS),
    "provider_dispositions": list(PROVIDER_DISPOSITIONS),
}
#: The production trust anchors: the committed contract (its SHA-256 and contract id) and every bound input it names
#: (INPUT_BINDINGS of TP46-A01). The command line always uses these; tests construct their own for tiny fixtures.
RECONCILIATION_ANCHORS: dict[str, Any] = {
    "contract_sha256": "2f6300bc0ee2364f0c8059a5622b6d3377869ab19a681c625fb57015cb857ee0",
    "contract_id": "BAT-718-NATIONAL-POPULATION-RECONCILIATION-2024-2025-V1",
    "parent": {"query_db_identity": "3baff07fac99831a2b0d06db408ea0ae513566757d763dfd58571d3c958b5f27",
               "sqlite_sha256": "9c517af94b9e0c7105627397b8a8cd9f9fc0ee806493c126c842c5018c5ba172",
               "contract_sha256": "3b27a454269127806b4930466dcb7c11de089a9479ccc41b7b2500dc606dc903",
               "schema_version": DB_SCHEMA_VERSION,
               "contest_identity": "ab4cdf1b0c1c06f20c9b143b9e0452fa71081670decc13c931830f50d140c4d8",
               "program_season_identity": "711e9dfcc35a181d51206099f41aa576424fc30ed61600811ab464074fb8f81e",
               "expected_contests": {"2024": 1672, "2025": 1688}},
    "inputs": {
        "identity_bindings": {
            "relative_path": "canonical/national_di_population_2016_2025/sha256/"
                             "711e9dfcc35a181d51206099f41aa576424fc30ed61600811ab464074fb8f81e/identity_bindings.jsonl.gz",
            "sha256": "5d15acf7c12b94d5e7ad5fa2d22c60192aad0b4d6a48cecd66cab6835596dee9"},
        "registry": {
            "relative_path": "canonical/BAT-387/sha256/10d0bd0adcef3fc1ba22fb9932f353cc59b0e5d4508c7891a1472d0221a454ac/"
                             "canonical_core_registry.csv",
            "sha256": "10d0bd0adcef3fc1ba22fb9932f353cc59b0e5d4508c7891a1472d0221a454ac"},
        "provider_captures": [
            {"season": 2024,
             "relative_path": "raw/SRC-002/games/sha256_6a49d6e19808cecf3743e0b3e85067ce7b717027c25ad571247a19c749d692f6.json",
             "sha256": "6a49d6e19808cecf3743e0b3e85067ce7b717027c25ad571247a19c749d692f6", "rows": 920,
             "receipt_relative_path": "manifests/captures/SRC-002/cap_6a97891fa5d6fdff8afab532.json",
             "receipt_sha256": "93cbc39c96cb8401576a7c3e301907116bc76f807fdbaddcdd708d896eb9ee23",
             "capture_id": "cap_6a97891fa5d6fdff8afab532", "source_id": "SRC-002", "route_path": "/games",
             "route_parameters": {"classification": "fbs", "year": "2024"}},
            {"season": 2025,
             "relative_path": "raw/SRC-002/games/sha256_4bcce67d1d788b3af33124d35837ec2836fb0f064850c5ec8554cfaed0024b79.json",
             "sha256": "4bcce67d1d788b3af33124d35837ec2836fb0f064850c5ec8554cfaed0024b79", "rows": 934,
             "receipt_relative_path": "manifests/captures/SRC-002/cap_f17f633d4e589a13300f2320.json",
             "receipt_sha256": "da9dd3f79f6ee50deb59c97cf1b8c199d49779a0daf79019da705e326f05b23a",
             "capture_id": "cap_f17f633d4e589a13300f2320", "source_id": "SRC-002", "route_path": "/games",
             "route_parameters": {"classification": "fbs", "year": "2025"}}]},
}
_INSTANT_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?(Z|\+00:00)$")
_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_ORG_KEY_RE = re.compile(r"^(?:org:)?([0-9]{1,12})$")
_PROVIDER_CONTEST_RE = re.compile(r"^cfbd:([0-9]{1,12})$")


def reconciliation_line(record: dict[str, Any]) -> str:
    """The canonical text of one record (sorted keys, compact separators, no float anywhere)."""
    _no_float(record)
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _no_float(value: Any) -> None:
    if isinstance(value, float):
        raise NationalQueryError("RECONCILIATION_FLOAT_VALUE", "records never carry a binary float")
    if isinstance(value, dict):
        for item in value.values():
            _no_float(item)
    elif isinstance(value, list):
        for item in value:
            _no_float(item)


def normalize_team_name(value: Any) -> str:
    """The accepted BAT-554 name normalization with the parent contract's token expansions."""
    folded = unicodedata.normalize("NFKD", html.unescape(str(value))).encode("ascii", "ignore").decode("ascii")
    folded = folded.lower().replace("&", " and ")
    return " ".join(RECONCILIATION_TOKEN_EXPANSIONS.get(token, token)
                    for token in re.sub(r"[^a-z0-9]+", " ", folded).split())


def provider_local_dates(start: Any) -> list[str] | None:
    """Candidate US-local calendar dates of a provider UTC start instant, or None when it is not a UTC instant."""
    if not isinstance(start, str) or not _INSTANT_RE.match(start):
        return None
    try:
        instant = datetime.fromisoformat(start.replace("Z", "+00:00"))
    except ValueError:
        return None
    if instant.utcoffset() != timedelta(0):
        return None
    instant = instant.astimezone(timezone.utc)
    return sorted({(instant + timedelta(hours=hours)).date().isoformat() for hours in RECONCILIATION_LOCAL_OFFSET_HOURS})


def _valid_score(value: Any) -> bool:
    return type(value) is int and value >= 0


def _plain(value: Any) -> Any:
    """A provider fact value as recorded: JSON scalars other than floats verbatim, anything else an explicit marker."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    return f"INVALID_TYPE:{type(value).__name__}"


def _io_path(path: Path) -> Path:
    """A path the operating system can open even beyond MAX_PATH (Windows extended-length form when needed)."""
    text = os.path.abspath(str(path))
    if os.name == "nt" and not text.startswith(_EXTENDED_PREFIX) and len(text) >= 240:
        return Path(_EXTENDED_PREFIX + text)
    return Path(text)


def reconciliation_data_root(parent_database: Path) -> Path:
    """``<data>/canonical/<population>/sha256/<id>/<db>`` -> ``<data>`` (the root every bound input is read under)."""
    return Path(parent_database).resolve().parent.parent.parent.parent.parent


def _read_bound(data_root: Path, relative_path: str, expected_sha256: str, code: str) -> bytes:
    if not isinstance(relative_path, str) or relative_path.startswith(("/", "\\")) or ".." in relative_path.split("/"):
        raise NationalQueryError("RECONCILIATION_INPUT_MISMATCH", f"bound input path {relative_path!r} is not relative")
    path = _io_path(Path(data_root).joinpath(*relative_path.split("/")))
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise NationalQueryError("RECONCILIATION_INPUT_MISSING", f"{relative_path}: {exc}") from exc
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha256:
        raise NationalQueryError(code, f"{relative_path} hashes to {actual}, the contract binds {expected_sha256}")
    return data


def load_reconciliation_inputs(data_root: Path, anchors: dict[str, Any]) -> dict[str, Any]:
    """Read and verify every bound cached input under ``data_root``; refuse any byte or receipt difference."""
    inputs = anchors["inputs"]
    binding_bytes = _read_bound(data_root, inputs["identity_bindings"]["relative_path"],
                                inputs["identity_bindings"]["sha256"], "RECONCILIATION_INPUT_MISMATCH")
    try:
        binding_rows = [json.loads(line) for line in gzip.decompress(binding_bytes).decode("utf-8").splitlines()
                        if line.strip()]
    except (OSError, ValueError) as exc:
        raise NationalQueryError("RECONCILIATION_INPUT_MISMATCH", f"identity bindings unreadable: {exc}") from exc
    header = (binding_rows[0] if binding_rows else {}).get("_header") or {}
    if header.get("contract_sha256") != anchors["parent"]["contract_sha256"] or header.get("stage") != "program-season":
        raise NationalQueryError("RECONCILIATION_INPUT_MISMATCH", "identity bindings are not the parent's program-season stage")
    registry_bytes = _read_bound(data_root, inputs["registry"]["relative_path"], inputs["registry"]["sha256"],
                                 "RECONCILIATION_INPUT_MISMATCH")
    providers = []
    for capture in inputs["provider_captures"]:
        raw = _read_bound(data_root, capture["relative_path"], capture["sha256"], "RECONCILIATION_SOURCE_BYTES_MISMATCH")
        receipt_bytes = _read_bound(data_root, capture["receipt_relative_path"], capture["receipt_sha256"],
                                    "RECONCILIATION_RECEIPT_MISMATCH")
        try:
            receipt = json.loads(receipt_bytes.decode("utf-8"))
            rows = json.loads(raw.decode("utf-8"))
        except ValueError as exc:
            raise NationalQueryError("RECONCILIATION_SOURCE_BYTES_MISMATCH", f"{capture['relative_path']}: {exc}") from exc
        expected_receipt = {"response_sha256": capture["sha256"], "row_count": capture["rows"],
                            "capture_id": capture["capture_id"], "source_id": capture["source_id"],
                            "path": capture["route_path"], "parameters": capture["route_parameters"],
                            "immutable_path": capture["relative_path"], "http_status": 200, "result": "SUCCESS"}
        differing = sorted(k for k, v in expected_receipt.items() if receipt.get(k) != v)
        if differing:
            raise NationalQueryError("RECONCILIATION_RECEIPT_MISMATCH",
                                     f"capture receipt {capture['capture_id']} differs on {differing}")
        if not isinstance(rows, list) or len(rows) != capture["rows"]:
            raise NationalQueryError("RECONCILIATION_SOURCE_BYTES_MISMATCH",
                                     f"{capture['relative_path']} is not a list of {capture['rows']} rows")
        providers.append({"season": capture["season"], "sha256": capture["sha256"], "capture_id": capture["capture_id"],
                          "rows": rows})
    return {"bindings": binding_rows[1:], "registry": _parse_registry(registry_bytes), "providers": providers}


def _parse_registry(data: bytes) -> dict[str, Any]:
    """Provider team id -> canonical team id (verified ENTITY TEAM|SRC-002|<id>) and verified team aliases."""
    entities: dict[str, set[str]] = {}
    aliases: dict[str, list[dict[str, Any]]] = {}
    for row in csv.DictReader(io.StringIO(data.decode("utf-8"), newline="")):
        if row.get("entity_type") != "team" or row.get("resolution_state") != "AUTO_ACCEPTED_VERIFIED":
            continue
        if row.get("record_type") == "ENTITY" and (row.get("identity_key") or "").startswith("TEAM|SRC-002|"):
            entities.setdefault(row["identity_key"].split("|", 2)[2], set()).add(row["canonical_id"])
        elif row.get("record_type") == "ALIAS" and row.get("alias"):
            start, end = (row.get("effective_from") or "")[:4], (row.get("effective_to_exclusive") or "")[:4]
            aliases.setdefault(row["canonical_id"], []).append({
                "record_id": row.get("record_id"), "alias": row["alias"], "normalized": normalize_team_name(row["alias"]),
                "from_season": int(start) if start.isdigit() else None,
                "to_season_exclusive": int(end) if end.isdigit() else None,
                "source_system_id": row.get("source_system_id")})
    for rows in aliases.values():
        rows.sort(key=lambda r: (str(r["record_id"]), r["alias"]))
    canonical = {team: next(iter(ids)) for team, ids in entities.items() if len(ids) == 1}
    return {"provider_to_canonical": canonical, "ambiguous_provider_ids": sorted(t for t, i in entities.items() if len(i) > 1),
            "aliases": aliases}


def _season_aliases(registry: dict[str, Any], canonical: str | None, season: int) -> tuple[list[dict], list[dict]]:
    rows = registry["aliases"].get(canonical, []) if canonical else []
    inside = [r for r in rows if (r["from_season"] is None or r["from_season"] <= season)
              and (r["to_season_exclusive"] is None or season < r["to_season_exclusive"])]
    return inside, [r for r in rows if r not in inside]


def verify_reconciliation_parent(parent: NationalPopulationDatabase, anchors: dict[str, Any]) -> None:
    """The verified parent must be exactly the accepted parent the contract binds."""
    expected = anchors["parent"]
    observed = {"query_db_identity": parent.binding["database_identity"],
                "sqlite_sha256": parent.binding["database_sha256"], "contract_sha256": parent.meta.get("contract_sha256"),
                "schema_version": parent.meta.get("schema_version"),
                "contest_identity": parent.meta.get("contest_identity"),
                "program_season_identity": parent.meta.get("program_season_identity")}
    differing = sorted(k for k, v in observed.items() if expected.get(k) != v)
    if differing:
        raise NationalQueryError("RECONCILIATION_PARENT_MISMATCH",
                                 f"the parent database differs from the bound accepted parent on {differing}")


def read_reconciliation_parent(conn: sqlite3.Connection) -> dict[str, Any]:
    """Every parent contest and program-season cell of the reconciliation seasons (read only, verified parent)."""
    marks = ",".join("?" * len(RECONCILIATION_SEASONS))
    contests = [dict(row) for row in conn.execute(
        f"SELECT * FROM contest WHERE season IN ({marks}) ORDER BY season, contest_date, contest_key",
        RECONCILIATION_SEASONS)]
    cells = {}
    for row in conn.execute(f"SELECT ncaa_org_id, season, team_name, ncaa_team_season_id, division_label "
                            f"FROM program_season WHERE season IN ({marks})", RECONCILIATION_SEASONS):
        cells.setdefault((row["ncaa_org_id"], row["season"]), []).append(dict(row))
    return {"contests": contests, "cells": cells}


def _permute(rows: list[Any], order: str) -> list[Any]:
    if order == "natural":
        return list(rows)
    if order == "reverse":
        return list(reversed(rows))
    match = re.match(r"^shuffle:([0-9]{1,9})$", order)
    if not match:
        raise NationalQueryError("RECONCILIATION_INPUT_ORDER_INVALID", f"input order {order!r}")
    import random  # noqa: PLC0415 - only the deterministic permutation variant needs it
    out = list(rows)
    random.Random(int(match.group(1))).shuffle(out)
    return out


def _crosswalk(bindings: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Accepted parent org -> provider team bindings, kept only when one-to-one in both directions."""
    by_org: dict[str, list[dict[str, Any]]] = {}
    by_team: dict[str, set[str]] = {}
    for row in bindings:
        org = row.get("org_id")
        if not isinstance(org, str):
            continue
        by_org.setdefault(org, []).append(row)
        team = row.get("cfbd_team_id")
        if isinstance(team, str) and row.get("rule") in BOUND_CROSSWALK_RULES:
            by_team.setdefault(team, set()).add(org)
    org_state: dict[str, dict[str, Any]] = {}
    team_to_org: dict[str, str] = {}
    for org, rows in by_org.items():
        if len(rows) != 1:
            org_state[org] = {"state": "BINDING_NOT_ONE_TO_ONE", "provider_team_id": None, "rule": None,
                              "reason": "ORGANIZATION_LISTED_MORE_THAN_ONCE"}
            continue
        row = rows[0]
        team = row.get("cfbd_team_id")
        if not isinstance(team, str) or row.get("rule") not in BOUND_CROSSWALK_RULES:
            org_state[org] = {"state": "UNBOUND", "provider_team_id": None, "rule": None, "reason": row.get("reason")}
        elif len(by_team.get(team, ())) != 1:
            org_state[org] = {"state": "BINDING_NOT_ONE_TO_ONE", "provider_team_id": None, "rule": row.get("rule"),
                              "reason": "PROVIDER_TEAM_BOUND_TO_MORE_THAN_ONE_ORGANIZATION"}
        else:
            org_state[org] = {"state": "BOUND", "provider_team_id": team, "rule": row["rule"], "reason": None}
            team_to_org[team] = org
    return org_state, team_to_org


def _parent_side(contest: dict[str, Any], side: str, cells: dict, org_state: dict[str, dict[str, Any]]) -> dict[str, Any]:
    org = contest.get(f"{side}_org_id")
    if org is None:
        crosswalk = {"state": "NO_ORGANIZATION", "provider_team_id": None, "rule": None, "reason": None}
        program = {"state": "NOT_APPLICABLE_NO_ORGANIZATION", "mismatched_fields": []}
    else:
        crosswalk = dict(org_state.get(org) or {"state": "UNBOUND", "provider_team_id": None, "rule": None,
                                                "reason": "ORGANIZATION_ABSENT_FROM_CROSSWALK"})
        found = cells.get((org, contest["season"])) or []
        if len(found) != 1:
            program = {"state": "CELL_ABSENT" if not found else "CELL_NOT_UNIQUE", "mismatched_fields": []}
        else:
            cell = found[0]
            label = cell["division_label"] if cell["division_label"] is not None else "UNRESOLVED"
            mismatched = [name for name, ours, theirs in (
                ("team_season_id", contest.get(f"{side}_team_season_id"), cell["ncaa_team_season_id"]),
                ("team_name", contest.get(f"{side}_team_name"), cell["team_name"]),
                ("division_label", contest.get(f"{side}_division_label"), label)) if ours != theirs]
            program = {"state": "MISMATCH" if mismatched else "VERIFIED", "mismatched_fields": mismatched}
    return {"key": contest.get(f"{side}_key"), "org_id": org, "team_name": contest.get(f"{side}_team_name"),
            "membership": contest.get(f"{side}_membership"), "crosswalk": crosswalk, "program_season": program,
            "provider_name": {"state": "NOT_EVALUATED_NO_ONE_TO_ONE_RELATION"},
            "name_link": {"state": "NOT_EVALUATED_NO_ONE_TO_ONE_RELATION"}, "verified": False}


def _name_evidence(evidence: dict[str, Any], provider_name: Any, provider_team: str, registry: dict[str, Any],
                   season: int) -> None:
    """Add the provider-name and name-link evidence of one parent participant in a one-to-one relation."""
    canonical = registry["provider_to_canonical"].get(provider_team)
    inside, outside = _season_aliases(registry, canonical, season)
    if not isinstance(provider_name, str) or not provider_name.strip():
        provider = {"state": "PROVIDER_NAME_MISSING", "provider_team_name": _plain(provider_name),
                    "canonical_team_id": canonical, "alias_record_ids": []}
    elif canonical is None:
        provider = {"state": "NO_CANONICAL_TEAM", "provider_team_name": provider_name, "canonical_team_id": None,
                    "alias_record_ids": []}
    else:
        hits = [r["record_id"] for r in inside if r["normalized"] == normalize_team_name(provider_name)]
        provider = {"state": "SEASON_ALIAS_DOCUMENTED" if hits else "UNDOCUMENTED_FOR_SEASON",
                    "provider_team_name": provider_name, "canonical_team_id": canonical,
                    "alias_record_ids": sorted({str(h) for h in hits})}
    parent_norm = normalize_team_name(evidence["team_name"] or "")
    provider_norm = normalize_team_name(provider_name) if isinstance(provider_name, str) else None
    season_hits = sorted({str(r["record_id"]) for r in inside if r["normalized"] == parent_norm})
    other_hits = sorted({str(r["record_id"]) for r in outside if r["normalized"] == parent_norm})
    if parent_norm and parent_norm == provider_norm:
        state = "NAME_EQUAL"
    elif parent_norm and season_hits:
        state = "SEASON_ALIAS_DOCUMENTED"
    else:
        state = "NO_DOCUMENTED_NAME_LINK"
    evidence["provider_name"] = provider
    evidence["name_link"] = {"state": state, "parent_name_normalized": parent_norm,
                             "provider_name_normalized": provider_norm, "alias_record_ids": season_hits,
                             "alias_outside_season_record_ids": other_hits}
    evidence["verified"] = (evidence["crosswalk"]["state"] == "BOUND" and evidence["program_season"]["state"] == "VERIFIED"
                            and provider["state"] == "SEASON_ALIAS_DOCUMENTED"
                            and state in ("NAME_EQUAL", "SEASON_ALIAS_DOCUMENTED"))


def _compare(contest: dict[str, Any], row: dict[str, Any], side_map: dict[str, str]) -> dict[str, Any]:
    """Every exposed decision-bearing field at its own authority (parent and provider values kept side by side)."""
    def score(values: list[Any], invalid: str, missing: str) -> str | None:
        if any(v is not None and not _valid_score(v) for v in values):
            return invalid
        if any(v is None for v in values):
            return missing
        return None
    parent_scores = [contest.get("a_points"), contest.get("b_points")]
    provider_scores = [row.get(f"{side_map['a']}Points"), row.get(f"{side_map['b']}Points")]
    p_state = score(parent_scores, "NOT_COMPARABLE_PARENT_INVALID", "NOT_COMPARABLE_PARENT_MISSING")
    q_state = score(provider_scores, "NOT_COMPARABLE_PROVIDER_INVALID", "NOT_COMPARABLE_PROVIDER_MISSING")
    if p_state == "NOT_COMPARABLE_PARENT_INVALID" or q_state == "NOT_COMPARABLE_PROVIDER_INVALID":
        score_result = p_state if p_state == "NOT_COMPARABLE_PARENT_INVALID" else q_state
    elif p_state and q_state:
        score_result = "NOT_COMPARABLE_BOTH_MISSING"
    elif p_state or q_state:
        score_result = p_state or q_state
    else:
        score_result = "AGREE" if parent_scores == provider_scores else "DISAGREE"
    site, neutral = contest.get("site"), row.get("neutralSite")
    parent_known_site = site in ("HOME_A", "HOME_B", "NEUTRAL")
    if not parent_known_site:
        neutral_result = "NOT_COMPARABLE_PARENT_MISSING"
    elif neutral is None:
        neutral_result = "NOT_COMPARABLE_PROVIDER_MISSING"
    elif not isinstance(neutral, bool):
        neutral_result = "NOT_COMPARABLE_PROVIDER_INVALID"
    else:
        neutral_result = "AGREE" if (site == "NEUTRAL") == neutral else "DISAGREE"
    provider_home_side = "a" if side_map["a"] == "home" else "b"
    if not parent_known_site:
        home_result = "NOT_COMPARABLE_PARENT_MISSING"
    elif site == "NEUTRAL":
        home_result = "NOT_COMPARABLE_PARENT_NEUTRAL_NO_DESIGNATION"
    elif neutral is None or not isinstance(neutral, bool):
        home_result = "NOT_COMPARABLE_PROVIDER_MISSING" if neutral is None else "NOT_COMPARABLE_PROVIDER_INVALID"
    elif neutral:
        home_result = "NOT_COMPARABLE_PROVIDER_NEUTRAL_DESIGNATION"
    else:
        home_result = "AGREE" if site == f"HOME_{provider_home_side.upper()}" else "DISAGREE"
    parent_completed = PARENT_COMPLETION.get(contest.get("contest_status"))
    provider_completed = row.get("completed")
    if parent_completed is None:
        completion_result = "NOT_COMPARABLE_PARENT_MISSING"
    elif provider_completed is None:
        completion_result = "NOT_COMPARABLE_PROVIDER_MISSING"
    elif not isinstance(provider_completed, bool):
        completion_result = "NOT_COMPARABLE_PROVIDER_INVALID"
    else:
        completion_result = "AGREE" if parent_completed == provider_completed else "DISAGREE"

    def classification(side: str) -> dict[str, Any]:
        parent_label, provider_value = contest.get(f"{side}_division_label"), row.get(f"{side_map[side]}Classification")
        if provider_value is None:
            result = "NOT_COMPARABLE_PROVIDER_MISSING"
        elif parent_label not in COMPARABLE_CLASSIFICATIONS or provider_value not in COMPARABLE_CLASSIFICATIONS.values():
            result = "NOT_COMPARABLE_VOCABULARY"
        else:
            result = "AGREE" if COMPARABLE_CLASSIFICATIONS[parent_label] == provider_value else "DISAGREE"
        return {"parent": parent_label, "provider": _plain(provider_value), "result": result}
    season_value = row.get("season")
    dates = provider_local_dates(row.get("startDate")) or []
    return {
        "season": {"parent": contest.get("season"), "provider": _plain(season_value),
                   "result": "AGREE" if season_value == contest.get("season") else "DISAGREE"},
        "date": {"parent": contest.get("contest_date"), "provider_start_utc": _plain(row.get("startDate")),
                 "provider_candidate_local_dates": dates, "provider_start_time_tbd": _plain(row.get("startTimeTBD")),
                 "provider_local_date_determined": len(dates) == 1,
                 "result": "AGREE" if contest.get("contest_date") in dates else "DISAGREE"},
        "participants": {"a": {"parent_key": contest.get("a_key"), "provider_role": side_map["a"],
                               "provider_team_id": str(row.get(f"{side_map['a']}Id"))},
                         "b": {"parent_key": contest.get("b_key"), "provider_role": side_map["b"],
                               "provider_team_id": str(row.get(f"{side_map['b']}Id"))},
                         "result": "AGREE"},
        "neutral_status": {"parent_site": site, "provider_neutral_site": _plain(neutral), "result": neutral_result},
        "home_orientation": {"parent_site": site, "provider_home_side": provider_home_side,
                             "provider_home_team_id": str(row.get("homeId")), "result": home_result},
        "completion": {"parent_contest_status": contest.get("contest_status"), "parent_completed": parent_completed,
                       "provider_completed": _plain(provider_completed), "result": completion_result},
        "score": {"parent": parent_scores, "provider_oriented": [_plain(v) for v in provider_scores],
                  "result": score_result},
        "classification_a": classification("a"), "classification_b": classification("b"),
    }


def _provider_row_key(season: int, ordinal: int) -> str:
    return f"src002:{season}:{ordinal:04d}"


def derive_reconciliation(parent: dict[str, Any], inputs: dict[str, Any], *, input_order: str = "natural"
                          ) -> dict[str, Any]:
    """The complete parent and provider reconciliation records and their summary, derived from verified inputs.

    The expected collections come from the inputs, never from outputs: one record per parent contest of the
    reconciliation seasons and one per provider input row (capture season + array ordinal)."""
    org_state, team_to_org = _crosswalk(inputs["bindings"])
    registry = inputs["registry"]
    cells = parent["cells"]
    contests = sorted((dict(c) for c in _permute(parent["contests"], input_order)),
                      key=lambda c: (c["season"], c.get("contest_date") or "", c["contest_key"]))
    keys = [c["contest_key"] for c in contests]
    if len(keys) != len(set(keys)):
        raise NationalQueryError("RECONCILIATION_PARENT_COLLECTION_INVALID", "duplicate parent contest keys")
    rows: list[dict[str, Any]] = []
    for capture in inputs["providers"]:
        for ordinal, raw in enumerate(capture["rows"]):
            rows.append({"season": capture["season"], "ordinal": ordinal, "raw": raw, "capture_sha256": capture["sha256"],
                         "capture_id": capture["capture_id"]})
    rows = sorted(_permute(rows, input_order), key=lambda r: (r["season"], r["ordinal"]))
    # ---- provider rows: validity, identity, participants
    id_counts: dict[str, int] = {}
    for r in rows:
        raw = r["raw"]
        gid = raw.get("id") if isinstance(raw, dict) else None
        r["game_id"] = str(gid) if type(gid) is int else None
        if r["game_id"] is not None:
            id_counts[r["game_id"]] = id_counts.get(r["game_id"], 0) + 1
    for r in rows:
        raw = r["raw"] if isinstance(r["raw"], dict) else {}
        problems = []
        if not isinstance(r["raw"], dict):
            problems.append("ROW_NOT_AN_OBJECT")
        if r["game_id"] is None:
            problems.append("GAME_ID_INVALID")
        for side in ("home", "away"):
            if type(raw.get(f"{side}Id")) is not int:
                problems.append(f"{side.upper()}_TEAM_ID_INVALID")
        if not problems and raw["homeId"] == raw["awayId"]:
            problems.append("SAME_TEAM_BOTH_SIDES")
        r["local_dates"] = provider_local_dates(raw.get("startDate"))
        if r["local_dates"] is None:
            problems.append("START_INSTANT_NOT_UTC")
        r["problems"] = problems
        r["season_ok"] = type(raw.get("season")) is int and raw.get("season") == r["season"]
        r["duplicate"] = r["game_id"] is not None and id_counts[r["game_id"]] > 1
        r["sides"] = {}
        for side in ("home", "away"):
            team = str(raw[f"{side}Id"]) if type(raw.get(f"{side}Id")) is int else None
            org = team_to_org.get(team) if team else None
            r["sides"][side] = {"provider_team_id": team, "provider_team_name": _plain(raw.get(f"{side}Team")),
                                "provider_classification": _plain(raw.get(f"{side}Classification")),
                                "crosswalk": {"state": "BOUND" if org else "UNBOUND", "org_id": org,
                                              "rule": (org_state.get(org) or {}).get("rule") if org else None},
                                "parent_key": f"org:{org}" if org else None}
        r["key"] = _provider_row_key(r["season"], r["ordinal"])
        r["matchable"] = not problems and r["season_ok"]
    # ---- parent participant evidence and the bound pair index
    parent_index: dict[tuple[int, frozenset], list[dict[str, Any]]] = {}
    for c in contests:
        c_sides = {s: _parent_side(c, s, cells, org_state) for s in ("a", "b")}
        c["_sides"] = c_sides
        teams = [c_sides[s]["crosswalk"]["provider_team_id"] if c_sides[s]["crosswalk"]["state"] == "BOUND" else None
                 for s in ("a", "b")]
        c["_bound_pair"] = frozenset(teams) if None not in teams and teams[0] != teams[1] else None
        c["_dated"] = isinstance(c.get("contest_date"), str) and bool(_DATE_RE.match(c["contest_date"]))
        if c["_bound_pair"] is not None:
            parent_index.setdefault((c["season"], c["_bound_pair"]), []).append(c)
    # ---- edges: same season, same bound pair, parent date among the provider candidate local dates
    same_pair: dict[str, list[str]] = {k: [] for k in keys}
    dated: dict[str, list[str]] = {k: [] for k in keys}
    row_same_pair: dict[str, list[str]] = {}
    row_dated: dict[str, list[str]] = {}
    for r in rows:
        row_same_pair[r["key"]], row_dated[r["key"]] = [], []
        if not r["matchable"]:
            continue
        pair = frozenset((r["sides"]["home"]["provider_team_id"], r["sides"]["away"]["provider_team_id"]))
        for c in parent_index.get((r["season"], pair), []):
            same_pair[c["contest_key"]].append(r["key"])
            row_same_pair[r["key"]].append(c["contest_key"])
            if c["_dated"] and c["contest_date"] in r["local_dates"]:
                dated[c["contest_key"]].append(r["key"])
                row_dated[r["key"]].append(c["contest_key"])
    row_by_key = {r["key"]: r for r in rows}
    contest_by_key = {c["contest_key"]: c for c in contests}
    one_to_one: dict[str, str] = {}
    for c in contests:
        cand = dated[c["contest_key"]]
        if len(cand) == 1 and row_dated[cand[0]] == [c["contest_key"]] and not row_by_key[cand[0]]["duplicate"]:
            one_to_one[c["contest_key"]] = cand[0]
    linked_rows = {v: k for k, v in one_to_one.items()}
    # ---- parent records
    parent_records = []
    for c in contests:
        key = c["contest_key"]
        sides = c["_sides"]
        relation, comparisons, conflicts = None, None, []
        if key in one_to_one:
            r = row_by_key[one_to_one[key]]
            raw = r["raw"]
            a_team = sides["a"]["crosswalk"]["provider_team_id"]
            side_map = {"a": "home" if str(raw["homeId"]) == a_team else "away"}
            side_map["b"] = "away" if side_map["a"] == "home" else "home"
            for s in ("a", "b"):
                _name_evidence(sides[s], raw.get(f"{side_map[s]}Team"), str(raw[f"{side_map[s]}Id"]), registry,
                               c["season"])
            comparisons = _compare(c, raw, side_map)
            conflicts = sorted(name for name, value in comparisons.items() if value["result"] == "DISAGREE")
            promoted = sides["a"]["verified"] and sides["b"]["verified"]
            relation = {"provider_row_key": r["key"], "provider_game_id": r["game_id"], "one_to_one": True,
                        "promoted": promoted, "side_map": side_map}
            if not promoted:
                disposition = "CANDIDATE_PARTICIPANT_EVIDENCE_INCOMPLETE"
                reason = ",".join(f"{s}:{_participant_gap(sides[s])}" for s in ("a", "b") if not sides[s]["verified"])
            elif conflicts:
                disposition, reason = "RECONCILED_FIELD_CONFLICT", "FIELD_DISAGREEMENT:" + ",".join(conflicts)
            else:
                disposition, reason = "RECONCILED_FIELDS_AGREE", None
        elif dated[key]:
            disposition = "AMBIGUOUS_PROVIDER_CANDIDATES"
            dup = any(row_by_key[k]["duplicate"] for k in dated[key])
            reason = ("DUPLICATE_PROVIDER_GAME_ID" if dup else "MULTIPLE_DATED_PROVIDER_ROWS" if len(dated[key]) > 1
                      else "PROVIDER_ROW_HAS_MULTIPLE_DATED_PARENTS")
        elif not c["_dated"]:
            disposition, reason = "UNMATCHED_PARENT_DATE_MISSING", "PARENT_CONTEST_DATE_MISSING_OR_INVALID"
        else:
            in_route = "FBS" in (c.get("a_division_label"), c.get("b_division_label"))
            unbound = [s for s in ("a", "b") if sides[s]["crosswalk"]["state"] != "BOUND"]
            open_same_pair = [k for k in same_pair[key] if k not in linked_rows]
            if c["_bound_pair"] is not None and open_same_pair:
                disposition, reason = "UNMATCHED_DATE_OUTSIDE_LOCAL_CANDIDATES", "SAME_PAIR_PROVIDER_ROW_OTHER_DATE"
            elif not in_route:
                disposition = "OUT_OF_ROUTE_NOT_EXPECTED"
                reason = ("NO_FBS_PARTICIPANT_" + ("PARTICIPANT_UNBOUND:" + ",".join(unbound) if unbound
                                                    else "NO_PROVIDER_ROW"))
            elif unbound:
                disposition = "UNMATCHED_PARTICIPANT_UNBOUND"
                reason = ",".join(f"{s}:{sides[s]['crosswalk']['state']}" for s in unbound)
            else:
                disposition = "UNMATCHED_IN_ROUTE_PROVIDER_ROW_ABSENT"
                reason = ("SAME_PAIR_PROVIDER_ROWS_LINKED_TO_OTHER_CONTESTS" if same_pair[key]
                          else "NO_SAME_PAIR_PROVIDER_ROW")
        parent_records.append({
            "record_type": "parent_reconciliation", "contest_key": key, "season": c["season"],
            "contest_date": c.get("contest_date"),
            "parent": {k: v for k, v in c.items() if not k.startswith("_")},
            "participants": {"a": sides["a"], "b": sides["b"]},
            "route_scope": "IN_FBS_ROUTE" if "FBS" in (c.get("a_division_label"), c.get("b_division_label"))
            else "OUTSIDE_FBS_ROUTE",
            "candidates": {"same_pair_provider_rows": same_pair[key], "dated_provider_rows": dated[key]},
            "relation": relation, "comparisons": comparisons, "field_conflicts": conflicts,
            "disposition": disposition, "disposition_reason": reason})
    parent_by_key = {rec["contest_key"]: rec for rec in parent_records}
    # ---- provider records
    provider_records = []
    for r in rows:
        raw = r["raw"] if isinstance(r["raw"], dict) else {}
        key = r["key"]
        relation, conflicts = None, []
        if key in linked_rows:
            prec = parent_by_key[linked_rows[key]]
            relation = {"contest_key": prec["contest_key"], "one_to_one": True,
                        "promoted": prec["relation"]["promoted"]}
            conflicts = prec["field_conflicts"]
            disposition, reason = prec["disposition"], prec["disposition_reason"]
        elif r["problems"]:
            disposition, reason = "INVALID_PROVIDER_ROW", ",".join(r["problems"])
        elif not r["season_ok"]:
            disposition, reason = "PROVIDER_SEASON_MISMATCH", f"ROW_SEASON_{_plain(raw.get('season'))}_CAPTURE_{r['season']}"
        elif r["duplicate"]:
            disposition, reason = "DUPLICATE_PROVIDER_GAME_ID", f"GAME_ID_ROWS:{id_counts[r['game_id']]}"
        elif row_dated[key]:
            disposition = "AMBIGUOUS_PARENT_CANDIDATES"
            reason = ("MULTIPLE_DATED_PARENT_CONTESTS" if len(row_dated[key]) > 1
                      else "PARENT_CONTEST_HAS_MULTIPLE_DATED_PROVIDER_ROWS")
        elif any(r["sides"][s]["crosswalk"]["state"] != "BOUND" for s in ("home", "away")):
            disposition = "UNMATCHED_PARTICIPANT_UNBOUND"
            reason = ",".join(f"{s}:UNBOUND" for s in ("home", "away") if r["sides"][s]["crosswalk"]["state"] != "BOUND")
        elif [k for k in row_same_pair[key] if k not in one_to_one]:
            disposition, reason = "UNMATCHED_DATE_OUTSIDE_LOCAL_CANDIDATES", "SAME_PAIR_PARENT_CONTEST_OTHER_DATE"
        else:
            disposition = "UNMATCHED_PARENT_CONTEST_ABSENT"
            reason = ("SAME_PAIR_PARENT_CONTESTS_LINKED_TO_OTHER_ROWS" if row_same_pair[key]
                      else "NO_SAME_PAIR_PARENT_CONTEST")
        provider_records.append({
            "record_type": "provider_reconciliation", "provider_row_key": key, "capture_season": r["season"],
            "row_ordinal": r["ordinal"], "capture": {"sha256": r["capture_sha256"], "capture_id": r["capture_id"]},
            "raw_row_sha256": hashlib.sha256(canonical_json_bytes(r["raw"])).hexdigest(),
            "provider": {field: _plain(raw.get(field)) for field in PROVIDER_FACT_FIELDS},
            "provider_game_id": r["game_id"], "candidate_local_dates": r["local_dates"],
            "participants": r["sides"],
            "candidates": {"same_pair_parent_contests": row_same_pair[key], "dated_parent_contests": row_dated[key]},
            "relation": relation, "field_conflicts": conflicts, "disposition": disposition,
            "disposition_reason": reason})
    return {"parent_records": parent_records, "provider_records": provider_records,
            "summary": reconciliation_summary(parent_records, provider_records)}


def _participant_gap(evidence: dict[str, Any]) -> str:
    for name, ok in (("CROSSWALK", evidence["crosswalk"]["state"] == "BOUND"),
                     ("PROGRAM_SEASON", evidence["program_season"]["state"] == "VERIFIED"),
                     ("PROVIDER_NAME", evidence["provider_name"].get("state") == "SEASON_ALIAS_DOCUMENTED"),
                     ("NAME_LINK", evidence["name_link"].get("state") in ("NAME_EQUAL", "SEASON_ALIAS_DOCUMENTED"))):
        if not ok:
            return name
    return "NONE"


def _count(values: Sequence[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        out[value] = out.get(value, 0) + 1
    return dict(sorted(out.items()))


def reconciliation_summary(parent_records: list[dict[str, Any]], provider_records: list[dict[str, Any]]) -> dict[str, Any]:
    """The summary denominators, computed only from the records themselves."""
    def block(records: list[dict[str, Any]], season_key: str) -> dict[str, Any]:
        seasons = sorted({str(r[season_key]) for r in records})
        return {"total": len(records), "by_season": _count([str(r[season_key]) for r in records]),
                "by_disposition": _count([r["disposition"] for r in records]),
                "by_season_and_disposition": {s: _count([r["disposition"] for r in records if str(r[season_key]) == s])
                                              for s in seasons}}
    relations = [r for r in parent_records if r["relation"]]
    fields: dict[str, dict[str, dict[str, int]]] = {"promoted": {}, "not_promoted": {}}
    for record in relations:
        bucket = fields["promoted" if record["relation"]["promoted"] else "not_promoted"]
        for name, value in record["comparisons"].items():
            slot = bucket.setdefault(name, {})
            slot[value["result"]] = slot.get(value["result"], 0) + 1
    links = [record["participants"][s]["name_link"]["state"] for record in relations for s in ("a", "b")]
    return {"parent": block(parent_records, "season"), "provider": block(provider_records, "capture_season"),
            "relations": {"one_to_one": len(relations), "promoted": sum(r["relation"]["promoted"] for r in relations),
                          "not_promoted": sum(not r["relation"]["promoted"] for r in relations)},
            "field_results": {k: {n: dict(sorted(v.items())) for n, v in sorted(b.items())} for k, b in fields.items()},
            "name_links": _count(links),
            "route_scope": _count([r["route_scope"] for r in parent_records])}


def reconciliation_payloads(derived: dict[str, Any]) -> dict[str, bytes]:
    return {"parent_reconciliation.jsonl": "".join(reconciliation_line(r) + "\n"
                                                   for r in derived["parent_records"]).encode("utf-8"),
            "provider_reconciliation.jsonl": "".join(reconciliation_line(r) + "\n"
                                                     for r in derived["provider_records"]).encode("utf-8"),
            "summary.json": (reconciliation_line(derived["summary"]) + "\n").encode("utf-8")}


def reconciliation_scope(anchors: dict[str, Any]) -> dict[str, Any]:
    return {"seasons": list(RECONCILIATION_SEASONS), "parent_population": "national_di_population_2016_2025",
            "parent_contests_expected": anchors["parent"]["expected_contests"],
            "provider_rows_expected": {str(c["season"]): c["rows"] for c in anchors["inputs"]["provider_captures"]},
            "provider_route": "SRC-002 GET /games classification=fbs year=<season> (FBS route only)",
            "excluded_seasons_note": "2016-2023 are reconciled in the parent itself; 2026 and earlier eras are not "
                                     "in this sidecar"}


def reconciliation_content_document(contract_id: str, contract_sha256: str, anchors: dict[str, Any],
                                    payloads: dict[str, bytes]) -> dict[str, Any]:
    return {"schema": RECONCILIATION_CONTENT_SCHEMA, "stage": "reconciliation-content",
            "population": RECONCILIATION_POPULATION, "contract_id": contract_id, "contract_sha256": contract_sha256,
            "parent": {k: v for k, v in anchors["parent"].items()}, "inputs": anchors["inputs"],
            "parameters_sha256": hashlib.sha256(canonical_json_bytes(RECONCILIATION_PARAMETERS)).hexdigest(),
            "labels": RECONCILIATION_LABELS, "scope": reconciliation_scope(anchors),
            "payload_schema": RECONCILIATION_PAYLOAD_SCHEMA,
            "outputs": {name: hashlib.sha256(payloads[name]).hexdigest() for name in RECONCILIATION_PAYLOADS},
            "row_counts": {"parent_reconciliation.jsonl": payloads["parent_reconciliation.jsonl"].count(b"\n"),
                           "provider_reconciliation.jsonl": payloads["provider_reconciliation.jsonl"].count(b"\n")}}


def reconciliation_meta(content_document: dict[str, Any], content_identity: str,
                        summary: dict[str, Any]) -> dict[str, str]:
    dumps = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)  # noqa: E731
    return {"schema_version": RECONCILIATION_DB_SCHEMA, "contract_id": content_document["contract_id"],
            "contract_sha256": content_document["contract_sha256"], "content_identity": content_identity,
            "payload_schema": RECONCILIATION_PAYLOAD_SCHEMA, "payload_sha256": dumps(content_document["outputs"]),
            "row_counts": dumps(content_document["row_counts"]), "parent": dumps(content_document["parent"]),
            "inputs": dumps(content_document["inputs"]), "labels": dumps(content_document["labels"]),
            "scope": dumps(content_document["scope"]), "parameters_sha256": content_document["parameters_sha256"],
            "summary": dumps(summary)}


def reconciliation_database_document(contract_sha256: str, content_identity: str, database_sha256: str,
                                     table_counts: dict[str, int]) -> dict[str, Any]:
    """The complete contract-defined database identity document (output_identity_scheme.database_identity): exactly
    these members, and outputs naming only the database file."""
    return {"schema": RECONCILIATION_DATABASE_SCHEMA, "stage": "reconciliation-database",
            "population": RECONCILIATION_POPULATION, "contract_sha256": contract_sha256,
            "content_identity": content_identity, "db_schema_version": RECONCILIATION_DB_SCHEMA,
            "outputs": {RECONCILIATION_DB_FILE: database_sha256}, "table_counts": dict(table_counts)}


#: The exact sidecar schema (every sqlite_master entry carries its statement; no automatic index exists).
RECONCILIATION_DDL = (
    ("table", "meta", "CREATE TABLE meta (key TEXT NOT NULL, value TEXT NOT NULL)"),
    ("table", "parent_reconciliation",
     "CREATE TABLE parent_reconciliation (ord INTEGER PRIMARY KEY, contest_key TEXT NOT NULL, season INTEGER NOT NULL, "
     "contest_date TEXT, a_key TEXT, b_key TEXT, disposition TEXT NOT NULL, provider_row_key TEXT, "
     "record TEXT NOT NULL)"),
    ("table", "provider_reconciliation",
     "CREATE TABLE provider_reconciliation (ord INTEGER PRIMARY KEY, provider_row_key TEXT NOT NULL, "
     "season INTEGER NOT NULL, row_ordinal INTEGER NOT NULL, provider_game_id TEXT, disposition TEXT NOT NULL, "
     "contest_key TEXT, record TEXT NOT NULL)"),
    ("index", "ix_meta_key", "CREATE INDEX ix_meta_key ON meta (key)"),
    ("index", "ix_parent_key", "CREATE INDEX ix_parent_key ON parent_reconciliation (contest_key)"),
    ("index", "ix_parent_season", "CREATE INDEX ix_parent_season ON parent_reconciliation (season, ord)"),
    ("index", "ix_parent_disposition", "CREATE INDEX ix_parent_disposition ON parent_reconciliation (disposition, ord)"),
    ("index", "ix_provider_key", "CREATE INDEX ix_provider_key ON provider_reconciliation (provider_row_key)"),
    ("index", "ix_provider_season", "CREATE INDEX ix_provider_season ON provider_reconciliation (season, ord)"),
    ("index", "ix_provider_disposition",
     "CREATE INDEX ix_provider_disposition ON provider_reconciliation (disposition, ord)"),
)
RECONCILIATION_TABLES = ("meta", "parent_reconciliation", "provider_reconciliation")


def reconciliation_table_rows(derived: dict[str, Any]) -> dict[str, list[tuple[Any, ...]]]:
    """The exact rows of both record tables (ord order); every index column is taken from its record."""
    parent = [(i, r["contest_key"], r["season"], r["contest_date"], r["participants"]["a"]["key"],
               r["participants"]["b"]["key"], r["disposition"],
               (r["relation"] or {}).get("provider_row_key"), reconciliation_line(r))
              for i, r in enumerate(derived["parent_records"])]
    provider = [(i, r["provider_row_key"], r["capture_season"], r["row_ordinal"], r["provider_game_id"],
                 r["disposition"], (r["relation"] or {}).get("contest_key"), reconciliation_line(r))
                for i, r in enumerate(derived["provider_records"])]
    return {"parent_reconciliation": parent, "provider_reconciliation": provider}


#: Which refusal a differing top-level record field gets (first match in this order).
_RECORD_FIELD_CODES = (("relation", "RECONCILIATION_RELATION_MISMATCH"),
                       ("candidates", "RECONCILIATION_RELATION_MISMATCH"),
                       ("participants", "RECONCILIATION_PARTICIPANT_MISMATCH"),
                       ("comparisons", "RECONCILIATION_FIELD_MISMATCH"),
                       ("field_conflicts", "RECONCILIATION_FIELD_MISMATCH"),
                       ("disposition", "RECONCILIATION_DISPOSITION_MISMATCH"),
                       ("disposition_reason", "RECONCILIATION_DISPOSITION_MISMATCH"),
                       ("parent", "RECONCILIATION_SOURCE_FIELD_MISMATCH"),
                       ("provider", "RECONCILIATION_SOURCE_FIELD_MISMATCH"),
                       ("raw_row_sha256", "RECONCILIATION_SOURCE_FIELD_MISMATCH"),
                       ("capture", "RECONCILIATION_SOURCE_FIELD_MISMATCH"),
                       ("provider_game_id", "RECONCILIATION_SOURCE_FIELD_MISMATCH"),
                       ("candidate_local_dates", "RECONCILIATION_SOURCE_FIELD_MISMATCH"))


class ReconciliationSidecar:
    """A verified, read-only handle on one content-addressed reconciliation sidecar of an accepted parent.

    Construction refuses (NationalQueryError with a stable code) unless the sidecar location, manifest identity,
    database bytes, schema, meta claims, the accepted parent and every bound cached input verify, and every record,
    the summary and the content identity equal what is re-derived from those inputs. Both contract-defined identity
    documents come from trusted authority, never from the sidecar's own claims: the content document is re-derived
    with the reader's pinned contract id and SHA-256, and the manifest's identity document must be exactly the
    contract-defined database document of the re-derived content identity, the database bytes and its table counts
    (a self-consistent, rehashed envelope is not authority). The documents are compared as canonical bytes, so a count
    declared as its equal integral float is another document, and the served identity is the digest of the rebuilt
    document (MF46A01-03)."""

    def __init__(self, database: Path, *, parent: NationalPopulationDatabase, parent_database: Path,
                 manifest: Path | None = None, expect_identity: str | None = None,
                 anchors: dict[str, Any] | None = None) -> None:
        self.anchors = anchors if anchors is not None else RECONCILIATION_ANCHORS
        a = self.anchors
        verify_reconciliation_parent(parent, a)
        self.binding = self._verify_location_and_manifest(database, manifest, expect_identity)
        document = self.binding["identity_document"]
        if document.get("contract_sha256") != a["contract_sha256"]:
            raise NationalQueryError("RECONCILIATION_CONTRACT_MISMATCH",
                                     f"the sidecar names contract {document.get('contract_sha256')}, the reader binds "
                                     f"{a['contract_sha256']}")
        self.conn = connect_readonly(database)
        try:
            self._verify_database(parent, Path(parent_database))
        except BaseException:
            self.conn.close()
            raise

    # ---- outer identity
    @staticmethod
    def _verify_location_and_manifest(database: Path, manifest: Path | None,
                                      expect_identity: str | None) -> dict[str, Any]:
        try:
            _literal_path(database)
        except _LocationError as exc:
            raise NationalQueryError(exc.code, exc.detail) from exc
        db = Path(database)
        if not db.is_file():
            raise NationalQueryError("RECONCILIATION_DATABASE_MISSING", f"no sidecar database file at {db}")
        resolved = db.resolve()
        if db.name != RECONCILIATION_DB_FILE or resolved.parent.parent.name != "sha256" or \
                resolved.parent.parent.parent.name != RECONCILIATION_POPULATION:
            raise NationalQueryError("RECONCILIATION_LOCATION_INVALID",
                                     f"the sidecar must sit at <root>/{RECONCILIATION_POPULATION}/sha256/<id>/"
                                     f"{RECONCILIATION_DB_FILE}")
        identity = resolved.parent.name
        if not IDENTITY_RE.match(identity):
            raise NationalQueryError("RECONCILIATION_LOCATION_INVALID", f"directory name {identity!r} is not an identity")
        manifest_path = Path(manifest) if manifest is not None else manifest_path_for(db)
        if not manifest_path.is_file():
            raise NationalQueryError("RECONCILIATION_MANIFEST_MISSING", f"no run manifest at {manifest_path}")
        try:
            document = json.loads(manifest_path.read_text(encoding="utf-8"))
            identity_document = document["identity_document"]
            computed = hashlib.sha256(canonical_json_bytes(identity_document)).hexdigest()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise NationalQueryError("RECONCILIATION_MANIFEST_MALFORMED", str(exc)) from exc
        if computed != identity or document.get("identity") != identity:
            raise NationalQueryError("RECONCILIATION_IDENTITY_MISMATCH",
                                     f"manifest identity document hashes to {computed}, directory is {identity}")
        if not isinstance(identity_document, dict) or \
                (identity_document.get("stage"), identity_document.get("schema"),
                 identity_document.get("db_schema_version"), identity_document.get("population")) != \
                ("reconciliation-database", RECONCILIATION_DATABASE_SCHEMA, RECONCILIATION_DB_SCHEMA,
                 RECONCILIATION_POPULATION):
            raise NationalQueryError("RECONCILIATION_SCHEMA_UNSUPPORTED", "not a reconciliation-database manifest")
        outputs = identity_document.get("outputs")
        if outputs is not None and not isinstance(outputs, dict):
            raise NationalQueryError("RECONCILIATION_IDENTITY_DOCUMENT_MISMATCH",
                                     "the manifest identity document's outputs member is not an object")
        expected_sha = (outputs or {}).get(RECONCILIATION_DB_FILE)
        actual_sha = _sha256_file(_io_path(db))
        if expected_sha != actual_sha:
            raise NationalQueryError("RECONCILIATION_DATABASE_TAMPERED",
                                     f"sidecar bytes hash to {actual_sha}, manifest names {expected_sha}")
        if expect_identity is not None and expect_identity != identity:
            raise NationalQueryError("STALE_RECONCILIATION_IDENTITY", f"expected {expect_identity}, found {identity}")
        return {"identity": identity, "sha256": actual_sha, "manifest": str(manifest_path),
                "identity_document": identity_document}

    # ---- schema, meta claims, inputs and the complete re-derivation
    def _verify_database(self, parent: NationalPopulationDatabase, parent_database: Path) -> None:
        a = self.anchors
        try:
            master = sorted((str(r[0]), str(r[1]), r[2]) for r in self.conn.execute(
                "SELECT type, name, sql FROM sqlite_master"))
        except sqlite3.DatabaseError as exc:
            raise NationalQueryError("RECONCILIATION_SCHEMA_UNSUPPORTED", str(exc)) from exc
        if master != sorted(RECONCILIATION_DDL):
            raise NationalQueryError("RECONCILIATION_SCHEMA_UNSUPPORTED", "the sidecar schema differs from the contract")
        meta_rows = [(str(r[0]), r[1]) for r in self.conn.execute("SELECT key, value FROM meta ORDER BY rowid")]
        meta = dict(meta_rows)
        if len(meta) != len(meta_rows):
            raise NationalQueryError("RECONCILIATION_META_MISMATCH", "duplicate meta keys")
        if meta.get("schema_version") != RECONCILIATION_DB_SCHEMA:
            raise NationalQueryError("RECONCILIATION_SCHEMA_UNSUPPORTED", f"schema {meta.get('schema_version')!r}")
        if meta.get("contract_sha256") != a["contract_sha256"]:
            raise NationalQueryError("RECONCILIATION_CONTRACT_MISMATCH", "the sidecar meta names another contract")
        # MF46A01-01: the contract id is the reader's pinned one, never the sidecar's own claim
        bound_id = a.get("contract_id")
        if not isinstance(bound_id, str) or not bound_id:
            raise NationalQueryError("RECONCILIATION_CONTRACT_MISMATCH", "the reader binds no contract id")
        if meta.get("contract_id") != bound_id:
            raise NationalQueryError("RECONCILIATION_CONTRACT_MISMATCH",
                                     f"the sidecar meta names contract id {meta.get('contract_id')!r}, the reader "
                                     f"binds {bound_id!r}")
        claims = {name: _json_or_none(meta.get(name)) for name in ("parent", "inputs", "labels", "scope")}
        if claims["parent"] != a["parent"]:
            raise NationalQueryError("RECONCILIATION_PARENT_MISMATCH", "the sidecar was built for another parent")
        if claims["inputs"] != a["inputs"]:
            raise NationalQueryError("RECONCILIATION_SOURCE_MISMATCH", "the sidecar names other cached inputs")
        if claims["labels"] != RECONCILIATION_LABELS:
            labels = claims["labels"] if isinstance(claims["labels"], dict) else {}
            code = ("RECONCILIATION_PIT_CLAIM_INVALID" if labels.get("pit_eligibility") !=
                    RECONCILIATION_LABELS["pit_eligibility"] else "RECONCILIATION_LABEL_CLAIM_INVALID")
            raise NationalQueryError(code, "the sidecar declares labels other than the contract's")
        if claims["scope"] != reconciliation_scope(a):
            raise NationalQueryError("RECONCILIATION_SCOPE_CLAIM_INVALID", "the sidecar declares another scope")
        if meta.get("parameters_sha256") != hashlib.sha256(canonical_json_bytes(RECONCILIATION_PARAMETERS)).hexdigest():
            raise NationalQueryError("RECONCILIATION_PARAMETERS_MISMATCH", "the sidecar was built with other rules")
        counts = {table: self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                  for table in RECONCILIATION_TABLES}
        if counts != self.binding["identity_document"].get("table_counts"):
            raise NationalQueryError("RECONCILIATION_COUNT_MISMATCH",
                                     f"table counts {counts} != {self.binding['identity_document'].get('table_counts')}")
        inputs = load_reconciliation_inputs(reconciliation_data_root(parent_database), a)
        parent_rows = read_reconciliation_parent(parent.conn)
        observed = _count([str(c["season"]) for c in parent_rows["contests"]])
        if observed != a["parent"]["expected_contests"]:
            raise NationalQueryError("RECONCILIATION_PARENT_MISMATCH",
                                     f"parent contests {observed} != bound {a['parent']['expected_contests']}")
        derived = derive_reconciliation(parent_rows, inputs)
        expected_rows = reconciliation_table_rows(derived)
        self._compare_table("parent_reconciliation", expected_rows["parent_reconciliation"], 1, "PARENT")
        self._compare_table("provider_reconciliation", expected_rows["provider_reconciliation"], 1, "PROVIDER")
        payloads = reconciliation_payloads(derived)
        content_document = reconciliation_content_document(bound_id, a["contract_sha256"], a, payloads)
        content_identity = hashlib.sha256(canonical_json_bytes(content_document)).hexdigest()
        if _json_or_none(meta.get("summary")) != derived["summary"]:
            raise NationalQueryError("RECONCILIATION_SUMMARY_MISMATCH", "the sidecar summary differs from its records")
        if meta.get("content_identity") != content_identity or \
                self.binding["identity_document"].get("content_identity") != content_identity:
            raise NationalQueryError("RECONCILIATION_CONTENT_IDENTITY_MISMATCH",
                                     f"the re-derived content identity is {content_identity}")
        expected_meta = reconciliation_meta(content_document, content_identity, derived["summary"])
        if meta != expected_meta:
            raise NationalQueryError("RECONCILIATION_META_MISMATCH",
                                     f"meta differs on {sorted(k for k in set(meta) | set(expected_meta) if meta.get(k) != expected_meta.get(k))}")
        # MF46A01-01/-03: the whole manifest identity document must be the contract-defined one, compared as canonical
        # bytes -- Python equality takes an integral float count for its integer although the canonical bytes, and so
        # the identity, differ -- and the served identity is the digest of that rebuilt document. Checked last, so
        # every earlier refusal keeps its own code.
        document = self.binding["identity_document"]
        expected_document = reconciliation_database_document(a["contract_sha256"], content_identity,
                                                             self.binding["sha256"], counts)
        expected_bytes = canonical_json_bytes(expected_document)
        if canonical_json_bytes(document) != expected_bytes:
            differing = sorted(k for k in set(document) | set(expected_document)
                               if k not in document or k not in expected_document
                               or canonical_json_bytes(document[k]) != canonical_json_bytes(expected_document[k]))
            raise NationalQueryError("RECONCILIATION_IDENTITY_DOCUMENT_MISMATCH",
                                     f"the manifest identity document is not the contract-defined database document "
                                     f"(differs on {differing})")
        database_identity = hashlib.sha256(expected_bytes).hexdigest()
        if database_identity != self.binding["identity"]:
            raise NationalQueryError("RECONCILIATION_IDENTITY_DOCUMENT_MISMATCH",
                                     f"the sidecar location names {self.binding['identity']}, the contract-defined "
                                     f"database document is {database_identity}")
        self.database_identity = database_identity
        self.meta = meta
        self.content_identity = content_identity
        self.summary = derived["summary"]
        self.records = {"parent-reconciliation": derived["parent_records"],
                        "provider-reconciliation": derived["provider_records"]}
        self.team_names = reconciliation_team_names(self.records)
        self.parent_identity = parent.binding["database_identity"]

    def _compare_table(self, table: str, expected: list[tuple[Any, ...]], key_index: int, label: str) -> None:
        present = [tuple(row) for row in self.conn.execute(f"SELECT * FROM {table} ORDER BY ord")]
        keys = [row[key_index] for row in present]
        if len(keys) != len(set(keys)):
            raise NationalQueryError("RECONCILIATION_DUPLICATE_ROW", f"{table} repeats a record key")
        wanted = [row[key_index] for row in expected]
        missing = sorted(set(wanted) - set(keys))
        if missing:
            raise NationalQueryError(f"RECONCILIATION_{label}_ROW_MISSING",
                                     f"{len(missing)} expected {table} records absent, e.g. {missing[:3]}")
        extra = sorted(set(keys) - set(wanted))
        if extra:
            raise NationalQueryError(f"RECONCILIATION_{label}_ROW_EXTRA",
                                     f"{len(extra)} {table} records outside the input collection, e.g. {extra[:3]}")
        if keys != wanted or [row[0] for row in present] != list(range(len(present))):
            raise NationalQueryError("RECONCILIATION_ORDER_MISMATCH", f"{table} is not in the contract order")
        for got, want in zip(present, expected):
            if got == want:
                continue
            if got[-1] == want[-1]:
                raise NationalQueryError("RECONCILIATION_INDEX_MISMATCH",
                                         f"{table} {want[key_index]} index columns differ from its record")
            got_record, want_record = _json_or_none(got[-1]), json.loads(want[-1])
            if not isinstance(got_record, dict):
                raise NationalQueryError("RECONCILIATION_RECORD_MISMATCH",
                                         f"{table} {want[key_index]} record is not a JSON object")
            differing = {f for f in set(want_record) | set(got_record) if got_record.get(f) != want_record.get(f)}
            code = next((c for f, c in _RECORD_FIELD_CODES if f in differing), "RECONCILIATION_RECORD_MISMATCH")
            raise NationalQueryError(code, f"{table} {want[key_index]} differs on {sorted(differing)[:6]}")

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "ReconciliationSidecar":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def query(self, grain: str, *, season: int | None = None, team: str | None = None, contest: str | None = None,
              disposition: str | None = None, limit: int | None = 50, offset: int = 0,
              all_rows: bool = False) -> dict[str, Any]:
        if grain not in RECONCILIATION_GRAINS:
            raise NationalQueryError("RECONCILIATION_GRAIN_REQUIRED", f"grain must be one of {list(RECONCILIATION_GRAINS)}")
        if offset < 0:
            raise NationalQueryError("NEGATIVE_OFFSET", "offset must be zero or positive")
        if limit is not None and limit < 0:
            raise NationalQueryError("NEGATIVE_LIMIT", "limit must be zero or positive")
        filters: dict[str, Any] = {}
        if season is not None:
            if isinstance(season, bool) or not isinstance(season, int):
                raise NationalQueryError("SEASON_INVALID", f"season must be an integer, got {season!r}")
            filters["season"] = season
        if team is not None:
            match = _ORG_KEY_RE.match(str(team).strip())
            filters["team"] = f"org:{int(match.group(1))}" if match else str(team).strip()
        if contest is not None:
            text = str(contest).strip()
            filters["contest"] = f"ncaa:{text}" if text.isdigit() and len(text) <= 12 else text
            if not (CONTEST_KEY_RE.match(filters["contest"]) or _PROVIDER_CONTEST_RE.match(filters["contest"])):
                raise NationalQueryError("CONTEST_KEY_INVALID", f"contest must be a parent key or cfbd:<id>, got {contest!r}")
        vocabulary = PARENT_DISPOSITIONS if grain == "parent-reconciliation" else PROVIDER_DISPOSITIONS
        if disposition is not None:
            if disposition not in vocabulary:
                raise NationalQueryError("DISPOSITION_UNKNOWN", f"disposition must be one of {list(vocabulary)}")
            filters["disposition"] = disposition
        side = "parent" if grain == "parent-reconciliation" else "provider"
        result: dict[str, Any] = {"reconciliation_identity": self.database_identity,
                                  "content_identity": self.content_identity,
                                  "contract_sha256": self.anchors["contract_sha256"],
                                  "parent_database_identity": self.parent_identity, "grain": grain,
                                  "filters": filters, "offset": offset, "limit": None if all_rows else limit,
                                  **RECONCILIATION_LABELS,
                                  "collection_denominators": self.summary[side],
                                  "verification": {"parent_records_verified": len(self.records["parent-reconciliation"]),
                                                   "provider_records_verified": len(self.records["provider-reconciliation"]),
                                                   "inputs_verified": True, "content_identity_rederived": True}}
        if season is not None and season not in RECONCILIATION_SEASONS:
            result.update(season_scope_state=RECONCILIATION_SCOPE_OUTSIDE, total=0, returned=0, rows=[],
                          next_offset=None, filtered_by_disposition={},
                          note="season outside the 2024-2025 reconciliation sidecar; no rows are fabricated")
            return result
        rows = [r for r in self.records[grain] if _reconciliation_match(grain, r, filters, self.team_names)]
        total = len(rows)
        page = rows[offset:] if all_rows else rows[offset:offset + (limit or 0)]
        result.update(season_scope_state="RECONCILIATION_2024_2025", total=total, returned=len(page), rows=page,
                      next_offset=offset + len(page) if offset + len(page) < total else None,
                      filtered_by_disposition=_count([r["disposition"] for r in rows]))
        return result


CONTEST_KEY_RE = re.compile(r"^(?:ncaa|nolink):[^\x00-\x1f]{1,200}$")


def _json_or_none(text: Any) -> Any:
    try:
        return json.loads(text) if isinstance(text, str) else None
    except ValueError:
        return None


def reconciliation_team_names(records: dict[str, list[dict[str, Any]]]
                              ) -> dict[str, dict[tuple[int, str], frozenset[str]]]:
    """Each source's own team names (casefolded) by season and source-native team id, from the verified records: the
    parent names of each organization in each parent season and the provider names of each provider team in each
    capture season (contract consumer.filters: a parent or provider team name)."""
    parent: dict[tuple[int, str], set[str]] = {}
    for record in records["parent-reconciliation"]:
        for side in (record["participants"]["a"], record["participants"]["b"]):
            if side["org_id"] is not None and side["team_name"]:
                parent.setdefault((record["season"], side["org_id"]), set()).add(str(side["team_name"]).casefold())
    provider: dict[tuple[int, str], set[str]] = {}
    for record in records["provider-reconciliation"]:
        for side in record["participants"].values():
            if side["provider_team_id"] and isinstance(side["provider_team_name"], str):
                provider.setdefault((record["capture_season"], side["provider_team_id"]), set()).add(
                    side["provider_team_name"].casefold())
    return {"parent": {k: frozenset(v) for k, v in parent.items()},
            "provider": {k: frozenset(v) for k, v in provider.items()}}


def _reconciliation_match(grain: str, record: dict[str, Any], filters: dict[str, Any],
                          names: dict[str, dict[tuple[int, str], frozenset[str]]] | None = None) -> bool:
    """A record's own source names always match. MF46A01-02: a name of the other source matches only through a
    participant's own BOUND crosswalk binding and only that source's names of the record's season, so a parent name,
    the provider name of its bound team, org:<id> and cfbdteam:<id> select the same records; an unbound or
    not one-to-one participant never borrows a name and no alias, normalization or fuzzy rule applies."""
    names = names or {"parent": {}, "provider": {}}
    if grain == "parent-reconciliation":
        season = record["season"]
        participants = [record["participants"]["a"], record["participants"]["b"]]
        bound = [p["crosswalk"]["provider_team_id"] for p in participants if p["crosswalk"]["state"] == "BOUND"]
        team_keys = {p["key"] for p in participants if p["key"]} | \
            {str(p["team_name"]).casefold() for p in participants if p["team_name"]} | \
            {f"cfbdteam:{team}" for team in bound}
        for team in bound:
            team_keys |= names["provider"].get((season, team), frozenset())
        contest_keys = {record["contest_key"]}
        if record["relation"] and record["relation"]["provider_game_id"]:
            contest_keys.add(f"cfbd:{record['relation']['provider_game_id']}")
    else:
        season = record["capture_season"]
        sides = record["participants"].values()
        team_keys = {s["parent_key"] for s in sides if s["parent_key"]} | \
            {f"cfbdteam:{s['provider_team_id']}" for s in sides if s["provider_team_id"]} | \
            {str(s["provider_team_name"]).casefold() for s in sides if isinstance(s["provider_team_name"], str)}
        for side in sides:
            if side["crosswalk"]["state"] == "BOUND":
                team_keys |= names["parent"].get((season, side["crosswalk"]["org_id"]), frozenset())
        contest_keys = set(record["candidates"]["dated_parent_contests"])
        if record["provider_game_id"]:
            contest_keys.add(f"cfbd:{record['provider_game_id']}")
    if "season" in filters and season != filters["season"]:
        return False
    if "team" in filters:
        value = filters["team"]
        if value not in team_keys and value.casefold() not in team_keys:
            return False
    if "contest" in filters and filters["contest"] not in contest_keys:
        return False
    if "disposition" in filters and record["disposition"] != filters["disposition"]:
        return False
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bas-national-population-query", allow_abbrev=False,
                                     description="Read-only national Division I population query (2016-2025).")
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--expect-identity", default=None)
    parser.add_argument("--grain", required=True, choices=sorted(GRAINS) + sorted(RECONCILIATION_GRAINS))
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
    parser.add_argument("--reconciliation", type=Path, default=None,
                        help="explicitly select a reconciliation sidecar database (never a default)")
    parser.add_argument("--reconciliation-manifest", dest="reconciliation_manifest", type=Path, default=None)
    parser.add_argument("--expect-reconciliation-identity", dest="expect_reconciliation_identity", default=None)
    parser.add_argument("--contest", default=None,
                        help="reconciliation grains: a parent contest key (ncaa:/nolink:, bare digits = ncaa:) or "
                             "cfbd:<provider game id>")
    parser.add_argument("--require-pit", dest="require_pit", action="store_true",
                        help="refused: no row of this query is PIT eligible")
    return parser


def _reconciliation_main(args: argparse.Namespace) -> dict[str, Any]:
    if args.reconciliation is None:
        raise NationalQueryError("RECONCILIATION_NOT_SELECTED",
                                 f"grain {args.grain!r} needs an explicitly selected --reconciliation sidecar")
    if args.grain not in RECONCILIATION_GRAINS:
        raise NationalQueryError("RECONCILIATION_GRAIN_REQUIRED",
                                 f"with --reconciliation the grain must be one of {list(RECONCILIATION_GRAINS)}")
    for name in ("division", "org", "classification_pair", "reconciliation_state"):
        if getattr(args, name) is not None:
            raise NationalQueryError("FILTER_NOT_APPLICABLE", f"filter {name!r} does not apply to grain {args.grain!r}")
    with NationalPopulationDatabase(args.database, manifest=args.manifest, expect_identity=args.expect_identity) as parent:
        with ReconciliationSidecar(args.reconciliation, parent=parent, parent_database=args.database,
                                   manifest=args.reconciliation_manifest,
                                   expect_identity=args.expect_reconciliation_identity) as sidecar:
            return sidecar.query(args.grain, season=args.season, team=args.team, contest=args.contest,
                                 disposition=args.disposition, limit=args.limit, offset=args.offset,
                                 all_rows=args.all_rows)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    filters = {"season": args.season, "division": args.division, "org": args.org, "team": args.team,
               "classification_pair": args.classification_pair, "disposition": args.disposition,
               "reconciliation_state": args.reconciliation_state}
    try:
        if args.require_pit:
            raise NationalQueryError("PIT_ELIGIBILITY_NOT_ESTABLISHED",
                                     "no population or reconciliation row is PIT eligible; calendar order and cached "
                                     "provider agreement are not known-at authority")
        if args.reconciliation is not None or args.grain in RECONCILIATION_GRAINS:
            result = _reconciliation_main(args)
        else:
            for name in ("contest", "reconciliation_manifest", "expect_reconciliation_identity"):
                if getattr(args, name) is not None:
                    raise NationalQueryError("RECONCILIATION_NOT_SELECTED",
                                             f"--{name.replace('_', '-')} applies only with --reconciliation")
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

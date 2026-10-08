r"""Read-only query over the national 2016-2023 source-time evidence (BAT-712).

``bas-source-time-query --database <canonical\...\sha256\<id>\national_source_time.sqlite> --grain contribution
--cutoff 2026-10-01T00:00:00Z --season 2019 --team org:697 --limit 50 --offset 0``

Standard library only (argparse, datetime, hashlib, json, re, sqlite3, zlib). Before any row is read the database is
verified: the file sits at ``<canonical root>/sha256/<id>/national_source_time.sqlite`` with its run manifest at
``<data root>/manifests/<population>/sha256/<id>/run_manifest.json``; ``<id>`` equals the SHA-256 of the manifest's
canonical database identity document, which names the database file's own SHA-256, the content identity, contract,
parents, table counts and record counts; the database bytes must hash to that value; the meta table must carry the
known schema, the same identities and the evidence-only row labels; ``--expect-identity`` / ``--expect-contract``
that differ are refused as stale; the connection is opened read-only through :mod:`aggie_analytics.readonly_sqlite`
(exactly the literal local file named, long and extended-length Windows locations included; a network, device or
non-literal location is refused before any file is touched).

Grains: ``assertion`` (field-grain source assertions), ``contest`` (per-field summary of a universe contest),
``contribution`` (target-contest and contributor relations of every history view), ``repository-row`` (every
repository-version row with its join disposition), ``lineage-row`` (parent NCAA page / CFBD route rows), ``capture``
(receipts and clocks) and ``partition`` (every parent key). The first three require ``--cutoff``, a timezone-aware
instant; their decisions keep content corroboration, the time-evidence class, ``observed_by_cutoff``,
``historically_published_by_cutoff`` (TRUE/FALSE/UNKNOWN as justified), the source-asserted commit comparison and
``pit_admission`` separate. Nothing is ever admitted: ``--require-pit`` is refused (PIT_ADMISSION_AUTHORITY_ABSENT).
A season outside 2016-2023 is NOT_YET_AUDITED with no evidence rows. Unknown or abbreviated flags, negative paging,
malformed filters and naive cutoffs are refused.

``--archive-evidence <archived-publication sidecar>`` (BAT-713) explicitly composes one verified sidecar through
``aggie_analytics.national_source_time.archive``, which is imported only then; it adds archive evidence next to the
unchanged decisions and serves the ``archive-*`` grains. Without it every output is exactly the behaviour above and
the archive grains are refused (ARCHIVE_EVIDENCE_REQUIRED).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sqlite3
import sys
import zlib
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

from aggie_analytics import readonly_sqlite

DB_FILE_NAME = "national_source_time.sqlite"
DB_SCHEMA_VERSION = "BAS-NATIONAL-SOURCE-TIME-DB-1"
DATABASE_DOCUMENT_SCHEMA = "BAS-NATIONAL-SOURCE-TIME-DATABASE-1"
TARGET_SEASONS = tuple(range(2016, 2024))
OUT_OF_SCOPE_STATE = "NOT_YET_AUDITED"
ROW_LABELS = {"evidence_authority": "SOURCE_TIME_EVIDENCE_ONLY",
              "pit_admission": "NOT_ADMITTED_NO_SEPARATE_PIT_ADMISSION_AUTHORITY",
              "publication_inference": "NONE_FROM_EVENT_DATE_GIT_DATE_RETRIEVAL_BACKDATING_PROVIDER_AGREEMENT_OR_GATE_LABEL"}
FIELDS = ("season", "contest_date", "a_participant", "b_participant", "completion", "a_points", "b_points")
ROLES = {"season": "IDENTITY", "contest_date": "IDENTITY", "a_participant": "IDENTITY", "b_participant": "IDENTITY",
         "completion": "OUTCOME", "a_points": "OUTCOME", "b_points": "OUTCOME"}
EVIDENCE_CLASSES = ("RECORDED_RETRIEVAL_STAMP_ONLY", "EXACT_REQUEST_RECEIPT_ONLY", "CACHE_HIT_RECEIPT_ONLY",
                    "RECORDED_RETRIEVAL_STAMP_WITH_ASSERTED_COMMIT_TIME", "NO_RECEIPT")
SOURCE_KINDS = ("NCAA_TEAM_SEASON_PAGE", "CFBD_ROUTE_RESPONSE", "REPOSITORY_VERSION")
RELATION_TYPES = ("TARGET_CONTEST", "CONTRIBUTOR")
JOIN_STATES = ("JOINED", "JOINED_OUTSIDE_UNIVERSE", "AMBIGUOUS_MULTIPLE_PARENT_CANDIDATES", "CONFLICTING", "UNJOINED")
GRAINS = ("assertion", "contest", "contribution", "repository-row", "lineage-row", "capture", "partition")
#: Grains served only with an explicitly named archive sidecar (``--archive-evidence``; BAT-713).
ARCHIVE_GRAINS = ("archive-disposition", "archive-request", "archive-capture", "archive-assertion")
DECISION_GRAINS = ("assertion", "contest", "contribution")
APPLICABLE = {"assertion": {"season", "team", "contest", "field", "evidence_class", "source_kind"},
              "contest": {"season", "team", "contest"},
              "contribution": {"season", "team", "contest", "relation_type"},
              "repository-row": {"season", "contest", "join_state"},
              "lineage-row": {"season", "team", "contest", "source_kind"},
              "capture": {"season", "source_kind", "evidence_class"},
              "partition": {"season", "contest"}}
TABLES = ("meta", "partition", "contests", "captures", "repository_rows", "relation_groups")
IDENTITY_RE = re.compile(r"^[0-9a-f]{64}$")
TEAM_RE = re.compile(r"^(?:org:)?([0-9]{1,12})$")
CONTEST_RE = re.compile(r"^(?:ncaa|nolink|cfbd):[^\x00-\x1f]{1,200}$")
CUTOFF_RE = re.compile(r"^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]{1,6})?"
                       r"(Z|[+-][0-9]{2}:[0-9]{2})$")
NAIVE_OR_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}([T ][0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]+)?)?)?$")
UTC = _dt.timezone.utc
EARLIEST_ZONE = _dt.timezone(_dt.timedelta(hours=14))
TRUE, FALSE, UNKNOWN = "TRUE", "FALSE", "UNKNOWN"
SYNTHETIC_PUBLICATION_ROLE = "SYNTHETIC_FIXTURE_QUALIFIED_PUBLICATION_NOT_REAL_EVIDENCE"


class SourceTimeQueryError(ValueError):
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
    db = Path(database).resolve()
    population_root = db.parent.parent.parent
    return population_root.parent.parent / "manifests" / population_root.name / "sha256" / db.parent.name / \
        "run_manifest.json"


# --------------------------------------------------------------------------------------------- inputs

def parse_cutoff(value: str | None) -> _dt.datetime:
    if value is None:
        raise SourceTimeQueryError("CUTOFF_REQUIRED", "this grain needs --cutoff <ISO-8601 instant with a zone>")
    text = str(value)
    match = CUTOFF_RE.match(text)
    if not match:
        if NAIVE_OR_DATE_RE.match(text):
            raise SourceTimeQueryError("CUTOFF_TIMEZONE_REQUIRED", f"cutoff {text!r} has no explicit zone or seconds")
        raise SourceTimeQueryError("CUTOFF_INVALID", f"cutoff {text!r} is not an ISO-8601 instant")
    year, month, day, hour, minute, second, fraction, zone = match.groups()
    try:
        if zone == "Z":
            tz = UTC
        else:
            hours, minutes = int(zone[1:3]), int(zone[4:6])
            if hours > 14 or minutes > 59:
                raise ValueError(zone)
            sign = 1 if zone[0] == "+" else -1
            tz = _dt.timezone(sign * _dt.timedelta(hours=hours, minutes=minutes))
        micro = int(fraction[1:].ljust(6, "0")) if fraction else 0
        return _dt.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), micro,
                            tzinfo=tz).astimezone(UTC)
    except ValueError as exc:
        raise SourceTimeQueryError("CUTOFF_INVALID", f"cutoff {text!r}: {exc}") from exc


def normalize_team(value: str) -> str:
    match = TEAM_RE.match(str(value).strip())
    if not match:
        raise SourceTimeQueryError("TEAM_KEY_INVALID", f"team must be an organization key org:<digits>, got {value!r}")
    return f"org:{int(match.group(1))}"


def normalize_contest(value: str) -> str:
    text = str(value)
    if text.isdigit() and len(text) <= 12:
        return f"ncaa:{text}"
    if not CONTEST_RE.match(text):
        raise SourceTimeQueryError("CONTEST_KEY_INVALID", f"contest must be a parent contest key, got {value!r}")
    return text


def _choice(value: str, allowed: Sequence[str], code: str) -> str:
    if value not in allowed:
        raise SourceTimeQueryError(code, f"{value!r} is not one of {list(allowed)}")
    return value


def _utc(text: str) -> _dt.datetime:
    return _dt.datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)


def _fmt(value: _dt.datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# --------------------------------------------------------------------------------------------- decisions

def observed_by_cutoff(capture: dict[str, Any], cutoff: _dt.datetime) -> tuple[str, str]:
    clock = capture["clocks"]["retrieval"]
    if clock["state"] == "ABSENT":
        return UNKNOWN, "RECEIPT_ABSENT"
    if clock["state"] == "CONTRADICTORY":
        return UNKNOWN, "RECEIPT_TIMES_CONTRADICTORY"
    if clock["state"] != "PRESENT":
        return UNKNOWN, "RECEIPT_TIME_INVALID"
    earliest, latest = _utc(clock["earliest_utc"]), _utc(clock["latest_utc"])
    role = clock["role"]
    if role == "EXACT_REQUEST_INTERVAL":
        if latest <= cutoff:
            return TRUE, "RECEIPT_COMPLETED_AT_OR_BEFORE_CUTOFF"
        if earliest > cutoff:
            return FALSE, "REQUEST_STARTED_AFTER_CUTOFF"
        return UNKNOWN, "CUTOFF_WITHIN_REQUEST_INTERVAL"
    if role == "CACHE_HIT_POSSESSION_UPPER_BOUND":
        if latest <= cutoff:
            return TRUE, "CACHE_HIT_RECORDED_AT_OR_BEFORE_CUTOFF"
        return UNKNOWN, "CACHE_HIT_AFTER_CUTOFF_ORIGINAL_RETRIEVAL_UNRECORDED"
    if role == "RECORDED_POSSESSION_UPPER_BOUND":
        if latest <= cutoff:
            return TRUE, "POSSESSION_RECORDED_AT_OR_BEFORE_CUTOFF"
        return UNKNOWN, "RECORDED_AFTER_CUTOFF_EARLIER_POSSESSION_NOT_EXCLUDED"
    return UNKNOWN, "RECEIPT_ROLE_UNKNOWN"


def earliest_event_instant(contest_date: str | None) -> _dt.datetime | None:
    try:
        day = _dt.date.fromisoformat(contest_date or "")
    except ValueError:
        return None
    return _dt.datetime(day.year, day.month, day.day, tzinfo=EARLIEST_ZONE).astimezone(UTC)


def published_by_cutoff(capture: dict[str, Any], observed: str, field: str, contest_date: str | None,
                        cutoff: _dt.datetime) -> tuple[str, str]:
    publication = capture["clocks"]["supported_publication"]
    if publication["state"] == "PRESENT":
        # No publication class is qualified by this contract and a database carrying any PRESENT publication clock is
        # refused at open. Only an unmistakably synthetic fixture role exercises the interval mechanism (tests).
        if publication.get("role") != SYNTHETIC_PUBLICATION_ROLE:
            return UNKNOWN, "PUBLICATION_CLAIM_UNQUALIFIED"
        if _utc(publication["latest_utc"]) <= cutoff:
            return TRUE, "SYNTHETIC_FIXTURE_PUBLICATION_AT_OR_BEFORE_CUTOFF"
        if _utc(publication["earliest_utc"]) > cutoff:
            return FALSE, "SYNTHETIC_FIXTURE_PUBLICATION_AFTER_CUTOFF"
        return UNKNOWN, "SYNTHETIC_FIXTURE_PUBLICATION_INTERVAL_CROSSES_CUTOFF"
    if observed == TRUE:
        return TRUE, "OBSERVED_PUBLIC_SOURCE_BYTES_AT_OR_BEFORE_CUTOFF"
    earliest = earliest_event_instant(contest_date)
    if ROLES[field] == "OUTCOME" and earliest is not None and cutoff < earliest:
        return FALSE, "OUTCOME_CANNOT_EXIST_BEFORE_EVENT_DATE"
    return UNKNOWN, "NO_INDEPENDENT_PUBLICATION_EVIDENCE_BEFORE_OWN_OBSERVATION"


def asserted_commit_by_cutoff(capture: dict[str, Any], cutoff: _dt.datetime) -> str:
    clock = capture["clocks"]["asserted_commit_committer"]
    if clock["state"] == "NOT_APPLICABLE":
        return "NOT_APPLICABLE"
    if clock["state"] != "PRESENT":
        return UNKNOWN
    if _utc(clock["latest_utc"]) <= cutoff:
        return TRUE
    if _utc(clock["earliest_utc"]) > cutoff:
        return FALSE
    return UNKNOWN


def decide(assertion: dict[str, Any], capture: dict[str, Any], contest_date: str | None,
           cutoff: _dt.datetime) -> dict[str, Any]:
    observed, observed_reason = observed_by_cutoff(capture, cutoff)
    published, published_reason = published_by_cutoff(capture, observed, assertion["field"], contest_date, cutoff)
    commit = asserted_commit_by_cutoff(capture, cutoff)
    reasons = ["NO_SEPARATE_PIT_ADMISSION_AUTHORITY"]
    if published != TRUE:
        reasons.append("PUBLICATION_NOT_ESTABLISHED_AT_CUTOFF")
    if assertion["corroboration"] != "AGREES_WITH_PARENT":
        reasons.append("CONTENT_NOT_CORROBORATED")
    return {"content_corroboration": assertion["corroboration"], "time_evidence_class": capture["time_evidence_class"],
            "observed_by_cutoff": observed, "observed_reason": observed_reason,
            "historically_published_by_cutoff": published, "publication_reason": published_reason,
            "asserted_commit_time_by_cutoff": commit,
            "asserted_commit_label": None if commit == "NOT_APPLICABLE"
            else "SOURCE_ASSERTED_ONLY_NOT_PUBLICATION_EVIDENCE",
            "pit_admission": {"state": "NOT_ADMITTED", "reasons": reasons}}


def aggregate_any(states: list[str]) -> str:
    if not states:
        return "NO_CORROBORATING_ASSERTION"
    if TRUE in states:
        return TRUE
    if all(s == FALSE for s in states):
        return FALSE
    return UNKNOWN


def aggregate_all(states: list[str]) -> str:
    if states and all(s == TRUE for s in states):
        return TRUE
    if FALSE in states:
        return FALSE
    return UNKNOWN


# --------------------------------------------------------------------------------------------- database

def verify_database(database: Path, *, expect_identity: str | None = None,
                    expect_contract: str | None = None) -> dict[str, Any]:
    literal_location(database)
    db = Path(database)
    if not db.is_file():
        raise SourceTimeQueryError("DATABASE_MISSING", f"no database file at {db}")
    if db.name != DB_FILE_NAME or db.resolve().parent.parent.name != "sha256":
        raise SourceTimeQueryError("DATABASE_LOCATION_INVALID", "the database must sit at <root>/sha256/<id>/" + DB_FILE_NAME)
    identity = db.resolve().parent.name
    if not IDENTITY_RE.match(identity):
        raise SourceTimeQueryError("DATABASE_LOCATION_INVALID", f"directory name {identity!r} is not a SHA-256 identity")
    manifest_path = manifest_path_for(db)
    if not manifest_path.is_file():
        raise SourceTimeQueryError("MANIFEST_MISSING", f"no run manifest at {manifest_path}")
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        identity_document = document["identity_document"]
        computed = hashlib.sha256(canonical_json_bytes(identity_document)).hexdigest()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SourceTimeQueryError("MANIFEST_MALFORMED", str(exc)) from exc
    if computed != identity or document.get("identity") != identity:
        raise SourceTimeQueryError("DATABASE_IDENTITY_MISMATCH",
                                   f"manifest identity document hashes to {computed}, directory is {identity}")
    if (identity_document.get("stage"), identity_document.get("schema"), identity_document.get("db_schema_version")) \
            != ("source-time-database", DATABASE_DOCUMENT_SCHEMA, DB_SCHEMA_VERSION):
        raise SourceTimeQueryError("DATABASE_SCHEMA_UNSUPPORTED", "the manifest is not a known source-time database")
    expected_db_sha = (identity_document.get("outputs") or {}).get(DB_FILE_NAME)
    actual_db_sha = _sha256_file(db)
    if expected_db_sha != actual_db_sha:
        raise SourceTimeQueryError("DATABASE_TAMPERED",
                                   f"database bytes hash to {actual_db_sha}, manifest names {expected_db_sha}")
    if expect_identity is not None and expect_identity != identity:
        raise SourceTimeQueryError("STALE_DATABASE_IDENTITY", f"expected {expect_identity}, found {identity}")
    if expect_contract is not None and expect_contract != identity_document.get("contract_sha256"):
        raise SourceTimeQueryError("STALE_CONTRACT", f"expected contract {expect_contract}, found "
                                   f"{identity_document.get('contract_sha256')}")
    return {"database_identity": identity, "database_sha256": actual_db_sha, "manifest": str(manifest_path),
            "content_identity": identity_document.get("content_identity"),
            "contract_sha256": identity_document.get("contract_sha256"), "parent": identity_document.get("parent"),
            "table_counts": identity_document.get("table_counts"),
            "record_counts": identity_document.get("record_counts")}


def literal_location(database: Path) -> str:
    """The literal local file ``database`` names; a network, device or non-literal location is refused lexically."""
    try:
        return readonly_sqlite.literal_path(database)
    except readonly_sqlite.DatabaseLocationError as exc:
        raise SourceTimeQueryError(exc.code, exc.detail) from exc


def connect_readonly(database: Path) -> sqlite3.Connection:
    try:
        conn = readonly_sqlite.connect_readonly(database)
    except readonly_sqlite.DatabaseLocationError as exc:
        raise SourceTimeQueryError(exc.code, exc.detail) from exc
    conn.row_factory = sqlite3.Row
    return conn


def _unpack(blob: bytes) -> list[dict[str, Any]]:
    text = zlib.decompress(blob).decode("utf-8")
    return [json.loads(line) for line in text.splitlines()]


class SourceTimeDatabase:
    """A verified, read-only handle on one content-addressed national source-time database."""

    def __init__(self, database: Path, *, expect_identity: str | None = None,
                 expect_contract: str | None = None) -> None:
        self.binding = verify_database(database, expect_identity=expect_identity, expect_contract=expect_contract)
        self.conn = connect_readonly(database)
        try:
            meta = {row["key"]: row["value"] for row in self.conn.execute("SELECT key, value FROM meta")}
            counts = {table: self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES}
            records = {"assertions.jsonl": self.conn.execute("SELECT SUM(assertion_count) FROM contests").fetchone()[0],
                       "lineage_rows.jsonl": self.conn.execute("SELECT SUM(lineage_count) FROM contests").fetchone()[0],
                       "relations.jsonl": self.conn.execute(
                           "SELECT SUM(relation_count) FROM relation_groups").fetchone()[0],
                       "contests.jsonl": counts["contests"], "partition.jsonl": counts["partition"],
                       "captures.jsonl": counts["captures"], "repository_rows.jsonl": counts["repository_rows"]}
            self.captures = {row["capture_id"]: json.loads(row["record"])
                             for row in self.conn.execute("SELECT capture_id, record FROM captures")}
        except sqlite3.DatabaseError as exc:
            self.conn.close()
            raise SourceTimeQueryError("DATABASE_SCHEMA_UNSUPPORTED", str(exc)) from exc
        problems = []
        if meta.get("schema_version") != DB_SCHEMA_VERSION:
            problems.append(("DATABASE_SCHEMA_UNSUPPORTED", f"schema {meta.get('schema_version')!r}"))
        elif meta.get("content_identity") != self.binding["content_identity"] or \
                meta.get("contract_sha256") != self.binding["contract_sha256"] or \
                json.loads(meta.get("parent") or "null") != self.binding["parent"]:
            problems.append(("DATABASE_IDENTITY_MISMATCH", "database meta and manifest identities differ"))
        elif counts != self.binding["table_counts"] or records != self.binding["record_counts"]:
            problems.append(("DATABASE_COUNT_MISMATCH", f"counts {counts} {records} differ from the manifest"))
        elif json.loads(meta.get("row_labels") or "null") != ROW_LABELS:
            problems.append(("DATABASE_SCHEMA_UNSUPPORTED", "row labels differ from the evidence-only labels"))
        elif any(c["clocks"]["supported_publication"]["state"] == "PRESENT" for c in self.captures.values()):
            problems.append(("PUBLICATION_CLAIM_UNQUALIFIED", "a capture claims a supported publication clock"))
        if problems:
            self.conn.close()
            raise SourceTimeQueryError(*problems[0])
        self.meta = meta
        self._contest_cache: dict[str, dict[str, Any]] = {}

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "SourceTimeDatabase":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------ helpers
    def _contest_rows(self, filters: dict[str, Any]) -> list[sqlite3.Row]:
        clauses, params = [], []
        if "season" in filters:
            clauses.append("season = ?")
            params.append(filters["season"])
        if "team" in filters:
            clauses.append("(a_key = ? OR b_key = ?)")
            params += [filters["team"], filters["team"]]
        if "contest" in filters:
            clauses.append("contest_key = ?")
            params.append(filters["contest"])
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        return list(self.conn.execute("SELECT ord, contest_key, contest_date, record, assertion_count, assertions, "
                                      f"lineage_count, lineage FROM contests{where} ORDER BY ord", params))

    def contest(self, key: str) -> dict[str, Any] | None:
        if key not in self._contest_cache:
            row = self.conn.execute("SELECT record, assertions FROM contests WHERE contest_key = ?", (key,)).fetchone()
            self._contest_cache[key] = None if row is None else {"record": json.loads(row["record"]),
                                                                  "assertions": _unpack(row["assertions"])}
        return self._contest_cache[key]

    def field_decisions(self, key: str, cutoff: _dt.datetime) -> dict[str, dict[str, Any]]:
        item = self.contest(key)
        if item is None:
            return {f: {"assertions": 0, "agreeing": 0, "conflicting": 0, "observed_by_cutoff":
                        "NO_CORROBORATING_ASSERTION", "historically_published_by_cutoff":
                        "NO_CORROBORATING_ASSERTION"} for f in FIELDS}
        cache = item.setdefault("decisions", {})
        stamp = _fmt(cutoff)
        if stamp in cache:
            return cache[stamp]
        date = item["record"]["contest_date"]
        out: dict[str, dict[str, Any]] = {}
        for field in FIELDS:
            rows = [a for a in item["assertions"] if a["field"] == field]
            agreeing = [a for a in rows if a["corroboration"] == "AGREES_WITH_PARENT"]
            decisions = [decide(a, self.captures[a["capture_id"]], date, cutoff) for a in agreeing]
            out[field] = {"assertions": len(rows), "agreeing": len(agreeing),
                          "conflicting": len(rows) - len(agreeing),
                          "observed_by_cutoff": aggregate_any([d["observed_by_cutoff"] for d in decisions]),
                          "historically_published_by_cutoff": aggregate_any(
                              [d["historically_published_by_cutoff"] for d in decisions])}
        cache[stamp] = out
        return out

    # ------------------------------------------------------------------ query
    def query(self, grain: str, *, cutoff: str | None = None, season: int | None = None, team: str | None = None,
              contest: str | None = None, field: str | None = None, evidence_class: str | None = None,
              source_kind: str | None = None, relation_type: str | None = None, join_state: str | None = None,
              limit: int | None = 50, offset: int = 0, all_rows: bool = False) -> dict[str, Any]:
        if grain not in GRAINS:
            raise SourceTimeQueryError("UNKNOWN_GRAIN", f"grain must be one of {list(GRAINS)}")
        if offset < 0:
            raise SourceTimeQueryError("NEGATIVE_OFFSET", "offset must be zero or positive")
        if limit is not None and limit < 0:
            raise SourceTimeQueryError("NEGATIVE_LIMIT", "limit must be zero or positive")
        filters: dict[str, Any] = {}
        if season is not None:
            if isinstance(season, bool) or not isinstance(season, int):
                raise SourceTimeQueryError("SEASON_INVALID", f"season must be an integer, got {season!r}")
            filters["season"] = season
        if team is not None:
            filters["team"] = normalize_team(team)
        if contest is not None:
            filters["contest"] = normalize_contest(contest)
        if field is not None:
            filters["field"] = _choice(field, FIELDS, "FIELD_INVALID")
        if evidence_class is not None:
            filters["evidence_class"] = _choice(evidence_class, EVIDENCE_CLASSES, "EVIDENCE_CLASS_INVALID")
        if source_kind is not None:
            filters["source_kind"] = _choice(source_kind, SOURCE_KINDS, "SOURCE_KIND_INVALID")
        if relation_type is not None:
            filters["relation_type"] = _choice(relation_type, RELATION_TYPES, "RELATION_TYPE_INVALID")
        if join_state is not None:
            filters["join_state"] = _choice(join_state, JOIN_STATES, "JOIN_STATE_INVALID")
        stray = sorted(set(filters) - APPLICABLE[grain])
        if stray:
            raise SourceTimeQueryError("FILTER_NOT_APPLICABLE", f"{stray} do not apply to the {grain} grain")
        when = parse_cutoff(cutoff) if grain in DECISION_GRAINS else (parse_cutoff(cutoff) if cutoff else None)
        result: dict[str, Any] = {"database_identity": self.binding["database_identity"],
                                  "content_identity": self.binding["content_identity"],
                                  "contract_sha256": self.binding["contract_sha256"], "grain": grain,
                                  "filters": filters, "cutoff": None if when is None else
                                  {"literal": cutoff, "utc": _fmt(when)}, "offset": offset,
                                  "limit": None if all_rows else limit, **ROW_LABELS}
        if season is not None and season not in TARGET_SEASONS and grain != "partition":
            result.update(season_scope_state=OUT_OF_SCOPE_STATE, total=0, returned=0, rows=[], next_offset=None,
                          note="season outside the audited 2016-2023 source-time tranche; no evidence is fabricated")
            return result
        iterator, total = getattr(self, "_" + grain.replace("-", "_"))(filters, when)
        stop = None if all_rows else offset + (limit or 0)
        rows = []
        for index, row in enumerate(iterator(offset, stop)):
            rows.append(row)
        returned = len(rows)
        state = (OUT_OF_SCOPE_STATE if season is not None and season not in TARGET_SEASONS else
                 ("AUDITED_2016_2023" if season is not None else "ALL_AUDITED_SEASONS"))
        result.update(season_scope_state=state, total=total, returned=returned, rows=rows,
                      next_offset=offset + returned if offset + returned < total else None)
        return result

    # Each grain returns (iterator(start, stop) -> rows in payload order, exact total).
    @staticmethod
    def _slice(items: Iterable[Any], start: int, stop: int | None) -> Iterator[Any]:
        for index, item in enumerate(items):
            if stop is not None and index >= stop:
                return
            if index >= start:
                yield item

    def _assertion(self, filters: dict[str, Any], cutoff: _dt.datetime):
        contests = self._contest_rows(filters)
        filtered = any(k in filters for k in ("field", "evidence_class", "source_kind"))

        def keep(a: dict[str, Any]) -> bool:
            return (filters.get("field") in (None, a["field"]) and
                    filters.get("source_kind") in (None, a["source_kind"]) and
                    filters.get("evidence_class") in (None, self.captures[a["capture_id"]]["time_evidence_class"]))

        def rows_of(row: sqlite3.Row) -> list[dict[str, Any]]:
            date = row["contest_date"]
            return [{"assertion": a, "decision": decide(a, self.captures[a["capture_id"]], date, cutoff)}
                    for a in _unpack(row["assertions"]) if keep(a)]
        if filtered:
            total = sum(sum(1 for a in _unpack(r["assertions"]) if keep(a)) for r in contests)
        else:
            total = sum(r["assertion_count"] for r in contests)

        def iterate(start: int, stop: int | None) -> Iterator[dict[str, Any]]:
            seen = 0
            for row in contests:
                size = row["assertion_count"]
                if not filtered and seen + size <= start:
                    seen += size
                    continue
                for item in (rows_of(row) if filtered else rows_of(row)):
                    if stop is not None and seen >= stop:
                        return
                    if seen >= start:
                        yield item
                    seen += 1
        return iterate, total

    def _contest(self, filters: dict[str, Any], cutoff: _dt.datetime):
        contests = self._contest_rows(filters)

        def iterate(start: int, stop: int | None) -> Iterator[dict[str, Any]]:
            for row in self._slice(contests, start, stop):
                record = json.loads(row["record"])
                fields = self.field_decisions(record["contest_key"], cutoff)
                yield {"contest": record, "fields": fields,
                       "pit_admission": {"state": "NOT_ADMITTED", "reasons": ["NO_SEPARATE_PIT_ADMISSION_AUTHORITY"]}}
        return iterate, len(contests)

    def _contribution(self, filters: dict[str, Any], cutoff: _dt.datetime):
        clauses, params = [], []
        if "season" in filters:
            clauses.append("season = ?")
            params.append(filters["season"])
        if "contest" in filters:
            clauses.append("target_contest_key = ?")
            params.append(filters["contest"])
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        groups = list(self.conn.execute(f"SELECT target_contest_key, team_keys, relation_count, relations FROM "
                                        f"relation_groups{where} ORDER BY ord", params))
        team, kind = filters.get("team"), filters.get("relation_type")
        if team is not None:
            groups = [g for g in groups if team in json.loads(g["team_keys"])]
        filtered = team is not None or kind is not None

        def keep(rel: dict[str, Any]) -> bool:
            return team in (None, rel["history_team_key"]) and kind in (None, rel["relation_type"])
        total = sum(sum(1 for r in _unpack(g["relations"]) if keep(r)) for g in groups) if filtered \
            else sum(g["relation_count"] for g in groups)

        def decide_relation(rel: dict[str, Any]) -> dict[str, Any]:
            fields = self.field_decisions(rel["contributor_contest_key"], cutoff)
            required = {f: {"observed_by_cutoff": fields[f]["observed_by_cutoff"],
                            "historically_published_by_cutoff": fields[f]["historically_published_by_cutoff"]}
                        for f in rel["required_fields"]}
            return {"relation": rel, "required_field_decisions": required,
                    "inputs_observed_by_cutoff": aggregate_all([v["observed_by_cutoff"] for v in required.values()]),
                    "inputs_published_by_cutoff": aggregate_all(
                        [v["historically_published_by_cutoff"] for v in required.values()]),
                    "target_outcome_fields_excluded": rel["relation_type"] == "TARGET_CONTEST",
                    "pit_admission": {"state": "NOT_ADMITTED", "reasons": ["NO_SEPARATE_PIT_ADMISSION_AUTHORITY"]}}

        def iterate(start: int, stop: int | None) -> Iterator[dict[str, Any]]:
            seen = 0
            for group in groups:
                size = group["relation_count"]
                if not filtered and seen + size <= start:
                    seen += size
                    continue
                for rel in _unpack(group["relations"]):
                    if not keep(rel):
                        continue
                    if stop is not None and seen >= stop:
                        return
                    if seen >= start:
                        yield decide_relation(rel)
                    seen += 1
        return iterate, total

    def _simple(self, table: str, clauses: list[str], params: list[Any]):
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        total = self.conn.execute(f"SELECT COUNT(*) FROM {table}{where}", params).fetchone()[0]

        def iterate(start: int, stop: int | None) -> Iterator[dict[str, Any]]:
            sql = f"SELECT record FROM {table}{where} ORDER BY ord"
            page = list(params)
            if stop is not None:
                sql += " LIMIT ? OFFSET ?"
                page += [stop - start, start]
            elif start:
                sql += " LIMIT -1 OFFSET ?"
                page += [start]
            for row in self.conn.execute(sql, page):
                yield json.loads(row["record"])
        return iterate, total

    def _repository_row(self, filters: dict[str, Any], _cutoff: Any):
        clauses, params = [], []
        for name, column in (("season", "season"), ("contest", "national_contest_key"), ("join_state", "join_state")):
            if name in filters:
                clauses.append(f"{column} = ?")
                params.append(filters[name])
        return self._simple("repository_rows", clauses, params)

    def _capture(self, filters: dict[str, Any], _cutoff: Any):
        clauses, params = [], []
        if "source_kind" in filters:
            clauses.append("source_kind = ?")
            params.append(filters["source_kind"])
        if "evidence_class" in filters:
            clauses.append("time_evidence_class = ?")
            params.append(filters["evidence_class"])
        if "season" in filters:
            clauses.append("json_extract(record, '$.season') = ?")
            params.append(filters["season"])
        return self._simple("captures", clauses, params)

    def _partition(self, filters: dict[str, Any], _cutoff: Any):
        clauses, params = [], []
        if "season" in filters:
            clauses.append("season = ?")
            params.append(filters["season"])
        if "contest" in filters:
            clauses.append("contest_key = ?")
            params.append(filters["contest"])
        return self._simple("partition", clauses, params)

    def _lineage_row(self, filters: dict[str, Any], _cutoff: Any):
        contests = self._contest_rows(filters)
        kind = filters.get("source_kind")
        items = [r for row in contests for r in _unpack(row["lineage"]) if kind in (None, r["source_kind"])]

        def iterate(start: int, stop: int | None) -> Iterator[dict[str, Any]]:
            return self._slice(items, start, stop)
        return iterate, len(items)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bas-source-time-query", allow_abbrev=False,
                                     description="Read-only national 2016-2023 source-time evidence and explicit-cutoff "
                                                 "query (evidence only; nothing is PIT admitted).")
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--grain", required=True, choices=list(GRAINS) + list(ARCHIVE_GRAINS))
    parser.add_argument("--cutoff", default=None, help="ISO-8601 instant with seconds and an explicit zone")
    parser.add_argument("--season", type=int, default=None)
    parser.add_argument("--team", default=None, help="organization key org:<digits> or bare digits")
    parser.add_argument("--contest", default=None, help="parent contest key, e.g. ncaa:1735135, or bare digits")
    parser.add_argument("--field", default=None)
    parser.add_argument("--evidence-class", default=None)
    parser.add_argument("--source-kind", default=None)
    parser.add_argument("--relation-type", default=None)
    parser.add_argument("--join-state", default=None)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--all", dest="all_rows", action="store_true")
    parser.add_argument("--expect-identity", default=None)
    parser.add_argument("--expect-contract", default=None)
    parser.add_argument("--require-pit", action="store_true",
                        help="refused: no separate PIT admission authority exists for any row")
    parser.add_argument("--archive-evidence", type=Path, default=None,
                        help="explicitly compose one verified archived-publication sidecar (never a default)")
    parser.add_argument("--expect-archive-identity", default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.require_pit:
            raise SourceTimeQueryError("PIT_ADMISSION_AUTHORITY_ABSENT",
                                       "no row has separate PIT admission authority; evidence is not admission")
        if args.archive_evidence is None and (args.grain in ARCHIVE_GRAINS or args.expect_archive_identity):
            raise SourceTimeQueryError("ARCHIVE_EVIDENCE_REQUIRED",
                                       "archive grains and identities need an explicit --archive-evidence sidecar")
        with SourceTimeDatabase(args.database, expect_identity=args.expect_identity,
                                expect_contract=args.expect_contract) as db:
            options = dict(cutoff=args.cutoff, season=args.season, team=args.team, contest=args.contest,
                           field=args.field, evidence_class=args.evidence_class, source_kind=args.source_kind,
                           relation_type=args.relation_type, join_state=args.join_state, limit=args.limit,
                           offset=args.offset, all_rows=args.all_rows)
            if args.archive_evidence is None:
                result = db.query(args.grain, **options)
            else:
                from aggie_analytics.national_source_time import archive  # noqa: PLC0415 - explicit option only

                with archive.ArchiveEvidence(args.archive_evidence, db,
                                             expect_identity=args.expect_archive_identity) as evidence:
                    result = evidence.query(args.grain, **options)
    except SourceTimeQueryError as exc:
        print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    # ``python -m`` runs this file as __main__ while the explicitly imported archive module imports the package
    # module; delegating keeps one identity for the shared refusal classes at the console and the module front.
    from aggie_analytics.national_source_time import query as _package_query  # noqa: PLC0415

    raise SystemExit(_package_query.main())

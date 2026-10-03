r"""Build the national 2016-2023 source-time evidence dataset (BAT-712, Cycle #40 TP40-A01).

``python -B tools/build_national_source_time.py --contract configs/national_source_time_2016_2023_contract.json
--history-database <data>/canonical/national_history_prefix_2016_2023/sha256/<id>/national_history.sqlite
--population-database <data>/canonical/national_di_population_2016_2025/sha256/<id>/national_population.sqlite
--source-bindings <INPUT_BINDINGS.json>
--output-root <data>/canonical/national_source_time_2016_2023
--manifest-root <data>/manifests/national_source_time_2016_2023``

Standard library plus ``polars`` (Parquet reads only). Before any row is read the producer verifies the committed
contract, both accepted parents (file hashes, run-manifest identity documents, stage files, parent chain), the
manager's source-binding document and every declared source file and receipt (including the repository payloads' git
blob binding to their commit responses). It then writes, create-only and content addressed:

* ``partition.jsonl`` -- every one of the parent's contest keys with its history partition and source-time scope;
* ``contests.jsonl`` -- the source-time universe (every BAT-711 target plus every unique contributing prior contest);
* ``assertions.jsonl`` -- field-grain source assertions ``(contest, capture, native row, field, revision)`` with
  source literals, normalized values and corroboration against the parent's accepted value;
* ``lineage_rows.jsonl`` -- the parent's own NCAA page and CFBD route observations of every universe contest;
* ``repository_rows.jsonl`` -- every repository-version source row with its namespaced join disposition;
* ``captures.jsonl`` -- every capture with separately preserved clocks (event, retrieval, asserted commit author and
  committer, supported publication, correction) and their receipt evidence;
* ``relations.jsonl`` -- every target-contest and contributor relation of all history views;
* ``national_source_time.sqlite`` -- the deterministic read-only query database over those payloads.

Nothing here establishes historical publication or PIT admission: retrieval receipts are this system's 2026
observations, asserted commit times are assertions, and cutoff decisions are made by the query from these clocks.
``--chunk-size`` with ``--checkpoint-dir`` builds through a hash-chained checkpoint that ``--resume`` verifies;
``--stop-after-chunks`` simulates an interruption; ``--input-order`` permutes every input list.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import gzip
import hashlib
import json
import os
import platform
import random
import re
import sqlite3
import sys
import tempfile
import time
import zlib
from pathlib import Path
from typing import Any, Iterable, Sequence

PRODUCER = "national_source_time/1.0.0"
POPULATION = "national_source_time_2016_2023"
CONTRACT_SCHEMA = "1.0.0"
CONTRACT_ID_PREFIX = "BAT-712-NATIONAL-SOURCE-TIME-2016-2023-"
PAYLOAD_SCHEMA = "BAS-NATIONAL-SOURCE-TIME-PAYLOAD-1"
CONTENT_SCHEMA = "BAS-NATIONAL-SOURCE-TIME-CONTENT-1"
DATABASE_SCHEMA = "BAS-NATIONAL-SOURCE-TIME-DATABASE-1"
DB_SCHEMA = "BAS-NATIONAL-SOURCE-TIME-DB-1"
CHECKPOINT_SCHEMA = "BAS-NATIONAL-SOURCE-TIME-CHECKPOINT-1"
DB_FILE = "national_source_time.sqlite"
HISTORY_DB_FILE = "national_history.sqlite"
POPULATION_DB_FILE = "national_population.sqlite"
TARGET_SEASONS = tuple(range(2016, 2024))
PROTECTED_SEASONS = (2024, 2025)
PROSPECTIVE_SEASONS = (2026,)
AUTHORITY = {"evidence_authority": "SOURCE_TIME_EVIDENCE_ONLY",
             "pit_admission": "NOT_ADMITTED_NO_SEPARATE_PIT_ADMISSION_AUTHORITY",
             "publication_inference": "NONE_FROM_EVENT_DATE_GIT_DATE_RETRIEVAL_BACKDATING_PROVIDER_AGREEMENT_OR_GATE_LABEL"}
FIELDS = ("season", "contest_date", "a_participant", "b_participant", "completion", "a_points", "b_points")
ROLES = {"season": "IDENTITY", "contest_date": "IDENTITY", "a_participant": "IDENTITY", "b_participant": "IDENTITY",
         "completion": "OUTCOME", "a_points": "OUTCOME", "b_points": "OUTCOME"}
TARGET_FIELDS = ("season", "contest_date", "a_participant", "b_participant")
KIND_ORDER = ("NCAA_TEAM_SEASON_PAGE", "CFBD_ROUTE_RESPONSE", "REPOSITORY_VERSION")
CLOCK_KINDS = ("retrieval", "asserted_commit_author", "asserted_commit_committer", "supported_publication", "correction")
CLOCK_FIELDS = ("state", "role", "literal", "start_literal", "zone", "precision", "earliest_utc", "latest_utc",
                "evidence_document", "evidence_pointer", "reason")
PAYLOAD_FILES = ("partition.jsonl", "contests.jsonl", "assertions.jsonl", "lineage_rows.jsonl",
                 "repository_rows.jsonl", "captures.jsonl", "relations.jsonl")
BUNDLE_FILES = {"contest": "contests.jsonl", "assertion": "assertions.jsonl", "lineage_row": "lineage_rows.jsonl"}
RECORD_FIELDS: dict[str, tuple[str, ...]] = {
    "partition": ("record_type", "contest_key", "season", "history_partition", "source_time_scope", "roles"),
    "contest": ("record_type", "contest_key", "ncaa_contest_id", "season", "term", "contest_date", "a_key", "b_key",
                "a_org_id", "b_org_id", "a_team_name", "b_team_name", "parent_site", "roles", "cfbd_game_id",
                "a_cfbd_team_id", "b_cfbd_team_id", "source_coverage", "missing_evidence", "assertion_count",
                "season_scope_state"),
    "assertion": ("record_type", "contest_key", "capture_id", "native_row_key", "field", "source_revision",
                  "source_kind", "field_role", "source_column", "literal", "value", "parent_value", "corroboration"),
    "lineage_row": ("record_type", "contest_key", "capture_id", "native_row_key", "source_kind", "route",
                    "source_revision", "identifiers", "literals", "event_clock", "join_state", "orientation"),
    "repository_row": ("record_type", "capture_id", "native_row_key", "season", "source_revision", "identifiers",
                       "literals", "event_clock", "join_state", "join_reasons", "national_contest_key",
                       "candidate_contest_keys", "orientation", "site_note"),
    "capture": ("record_type", "capture_id", "source_kind", "route", "season", "source_uri", "payload_path",
                "payload_sha256", "source_revision", "byte_binding", "receipt_document", "receipt_document_sha256",
                "receipt_pointer", "receipt_stamp_shared_by", "time_evidence_class", "clocks"),
    "relation": ("record_type", "relation_type", "target_contest_key", "view", "side", "history_team_key",
                 "contributor_contest_key", "season", "target_date", "contributor_date", "required_fields"),
    "clock": CLOCK_FIELDS,
    "identifier": ("namespace", "value"),
}
REPOSITORY_COLUMNS = ("id", "game_id", "season", "start_date", "home_id", "away_id", "home_score", "away_score",
                      "status_type_completed", "status_type_name", "neutral_site", "home_location", "away_location")
CFBD_COLUMNS = ("id", "season", "startDate", "startTimeTBD", "completed", "neutralSite", "homeId", "homeTeam",
                "homePoints", "awayId", "awayTeam", "awayPoints")
PAGE_COLUMNS = ("season", "date_text", "result_text", "status", "page_org_id", "page_team_name", "page_team_season_id",
                "opponent_logo_org_id", "opponent_name", "team_points", "opponent_points", "page_team_marked_away",
                "neutral_site", "row_index")
INPUT_ORDER = re.compile(r"^(natural|reverse|shuffle:[0-9]{1,9})$")
INSTANT_RE = re.compile(r"^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]{1,6})?"
                        r"(Z|[+-][0-9]{2}:[0-9]{2})$")
MINUTE_RE = re.compile(r"^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2})(Z|[+-][0-9]{2}:[0-9]{2})$")
NAIVE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]+)?)?$")
US_DATE_RE = re.compile(r"^([0-9]{2})/([0-9]{2})/([0-9]{4})$")
ISO_DATE_RE = re.compile(r"^([0-9]{4})-([0-9]{2})-([0-9]{2})$")
DIGITS_RE = re.compile(r"^[0-9]{1,12}$")
INTEGRAL_DECIMAL_RE = re.compile(r"^([0-9]{1,12})\.0+$")
US_LOCAL_OFFSETS_HOURS = (-4, -10)
EARLIEST_ZONE_HOURS = 14
INTERRUPTED_EXIT = 3
GZIP_LEVEL = 9
UTC = _dt.timezone.utc


class BuildRefused(Exception):
    """A refused build; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# --------------------------------------------------------------------------------------------- serialization

def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _check_fields(kind: str, value: dict[str, Any]) -> None:
    expected = RECORD_FIELDS[kind]
    if not isinstance(value, dict) or set(value) != set(expected):
        raise BuildRefused("UNKNOWN_FIELD", f"{kind} fields {sorted(set(value or {}) ^ set(expected))}")


def _assert_no_float(value: Any) -> None:
    if isinstance(value, float):
        raise BuildRefused("FLOAT_IN_PAYLOAD", repr(value))
    if isinstance(value, dict):
        for item in value.values():
            _assert_no_float(item)
    elif isinstance(value, list):
        for item in value:
            _assert_no_float(item)


def record_line(record: dict[str, Any]) -> bytes:
    kind = record["record_type"]
    _check_fields(kind, record)
    if kind == "capture":
        if set(record["clocks"]) != set(CLOCK_KINDS):
            raise BuildRefused("UNKNOWN_FIELD", f"capture clocks {sorted(record['clocks'])}")
        for clock in record["clocks"].values():
            _check_fields("clock", clock)
    if kind in ("lineage_row", "repository_row"):
        _check_fields("clock", record["event_clock"])
        for ident in record["identifiers"].values():
            _check_fields("identifier", ident)
    if kind == "contest":
        for name in ("cfbd_game_id", "a_cfbd_team_id", "b_cfbd_team_id"):
            _check_fields("identifier", record[name])
    _assert_no_float(record)
    return canonical_json_bytes(record) + b"\n"


# --------------------------------------------------------------------------------------------- clocks

def fmt_utc(value: _dt.datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _zone(text: str) -> _dt.timezone:
    if text == "Z":
        return UTC
    sign = 1 if text[0] == "+" else -1
    hours, minutes = int(text[1:3]), int(text[4:6])
    if hours > 14 or minutes > 59:
        raise ValueError(f"offset {text}")
    return _dt.timezone(sign * _dt.timedelta(hours=hours, minutes=minutes))


def clock(state: str, *, role: str | None = None, literal: str | None = None, start_literal: str | None = None,
          zone: str | None = None, precision: str | None = None, earliest: str | None = None,
          latest: str | None = None, document: str | None = None, pointer: str | None = None,
          reason: str | None = None) -> dict[str, Any]:
    return {"state": state, "role": role, "literal": literal, "start_literal": start_literal, "zone": zone,
            "precision": precision, "earliest_utc": earliest, "latest_utc": latest, "evidence_document": document,
            "evidence_pointer": pointer, "reason": reason}


def parse_literal(literal: Any, *, allow_local_date: bool = False) -> tuple[str, str | None, str, str]:
    """Return (precision, zone, earliest_utc, latest_utc) for a timestamp literal; ValueError when unusable."""
    if not isinstance(literal, str):
        raise ValueError("NOT_A_STRING")
    match = INSTANT_RE.match(literal)
    if match:
        year, month, day, hour, minute, second, fraction, zone = match.groups()
        micro = int((fraction or ".")[1:].ljust(6, "0")) if fraction else 0
        value = _dt.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), micro,
                             tzinfo=_zone(zone))
        digits = len(fraction) - 1 if fraction else 0
        precision = "second" if digits == 0 else ("millisecond" if digits <= 3 else "microsecond")
        return precision, zone, fmt_utc(value), fmt_utc(value)
    match = MINUTE_RE.match(literal)
    if match:
        year, month, day, hour, minute, zone = match.groups()
        value = _dt.datetime(int(year), int(month), int(day), int(hour), int(minute), tzinfo=_zone(zone))
        return "minute", zone, fmt_utc(value), fmt_utc(value + _dt.timedelta(seconds=59, microseconds=999999))
    if allow_local_date:
        day = parse_local_date(literal)
        if day is not None:
            start = _dt.datetime(day.year, day.month, day.day, tzinfo=_dt.timezone(_dt.timedelta(hours=-4)))
            end = _dt.datetime(day.year, day.month, day.day, 23, 59, 59, 999999,
                               tzinfo=_dt.timezone(_dt.timedelta(hours=-10)))
            return "date", None, fmt_utc(start), fmt_utc(end)
    if NAIVE_RE.match(literal):
        raise ValueError("NAIVE_TIMESTAMP_REFUSED")
    raise ValueError("TIMESTAMP_MALFORMED")


def parse_local_date(literal: Any) -> _dt.date | None:
    if not isinstance(literal, str):
        return None
    match = US_DATE_RE.match(literal)
    try:
        if match:
            return _dt.date(int(match.group(3)), int(match.group(1)), int(match.group(2)))
        match = ISO_DATE_RE.match(literal)
        if match:
            day = _dt.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            return day if day.isoformat() == literal else None
    except ValueError:
        return None
    return None


def present_clock(literal: Any, *, role: str, document: str | None, pointer: str | None,
                  start_literal: Any = None, allow_local_date: bool = False) -> dict[str, Any]:
    try:
        precision, zone, earliest, latest = parse_literal(literal, allow_local_date=allow_local_date)
        if start_literal is not None:
            _p, _z, earliest, _l = parse_literal(start_literal)
            if earliest > latest:
                return clock("INVALID", role=role, literal=_text(literal), start_literal=_text(start_literal),
                             document=document, pointer=pointer, reason="START_AFTER_COMPLETION")
    except ValueError as exc:
        return clock("INVALID" if literal is not None else "ABSENT", role=role, literal=_text(literal),
                     start_literal=_text(start_literal), document=document, pointer=pointer,
                     reason=str(exc) if literal is not None else "LITERAL_ABSENT")
    return clock("PRESENT", role=role, literal=literal, start_literal=start_literal, zone=zone, precision=precision,
                 earliest=earliest, latest=latest, document=document, pointer=pointer)


def contradictory_clock(literals: list[str], *, role: str, document: str, pointers: list[str]) -> dict[str, Any]:
    return clock("CONTRADICTORY", role=role, literal="|".join(sorted(set(literals))), document=document,
                 pointer="|".join(pointers), reason="RECEIPT_TIMES_CONTRADICTORY")


def local_candidate_dates(event_clock: dict[str, Any]) -> list[str]:
    """The parent BAT-710 cfbd_date_basis: a UTC instant's US-local candidate dates (shift -4 h and -10 h)."""
    if event_clock["state"] != "PRESENT" or event_clock["precision"] == "date":
        return []
    out = set()
    for bound in (event_clock["earliest_utc"], event_clock["latest_utc"]):
        instant = _dt.datetime.strptime(bound, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)
        for hours in US_LOCAL_OFFSETS_HOURS:
            out.add((instant + _dt.timedelta(hours=hours)).date().isoformat())
    return sorted(out)


def _text(value: Any) -> str | None:
    """A source literal as text: None stays None, booleans are true/false, numbers keep their own spelling."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def normalize_int(value: Any) -> tuple[int | None, str]:
    """(value, state) for a score/id literal: OK, NULL or MALFORMED; integral floats/decimal strings normalize."""
    if value is None:
        return None, "NULL"
    if isinstance(value, bool):
        return None, "MALFORMED"
    if isinstance(value, int):
        return (value, "OK") if value >= 0 else (None, "MALFORMED")
    if isinstance(value, float):
        return (int(value), "OK") if value.is_integer() and value >= 0 else (None, "MALFORMED")
    if isinstance(value, str):
        text = value.strip()
        if text != value:
            return None, "MALFORMED"
        if DIGITS_RE.match(text):
            return int(text), "OK"
        match = INTEGRAL_DECIMAL_RE.match(text)
        if match:
            return int(match.group(1)), "OK"
    return None, "MALFORMED"


# --------------------------------------------------------------------------------------------- contract

def load_contract(path: Path) -> tuple[dict[str, Any], str]:
    raw = Path(path).read_bytes()
    try:
        contract = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BuildRefused("CONTRACT_INVALID", str(exc)) from exc
    if contract.get("schema_version") != CONTRACT_SCHEMA or not str(contract.get("contract_id", "")).startswith(
            CONTRACT_ID_PREFIX):
        raise BuildRefused("CONTRACT_SCHEMA_UNKNOWN",
                           f"schema {contract.get('schema_version')!r} id {contract.get('contract_id')!r}")
    authority = contract.get("authority") or {}
    for key, value in AUTHORITY.items():
        if authority.get(key) != value:
            raise BuildRefused("FORGED_PIT_AUTHORITY", f"authority.{key} is {authority.get(key)!r}")
    if contract.get("row_labels") != AUTHORITY:
        raise BuildRefused("FORGED_PIT_AUTHORITY", "row_labels differ from the evidence-only labels")
    if authority.get("require_pit") != "REFUSED_PIT_ADMISSION_AUTHORITY_ABSENT":
        raise BuildRefused("FORGED_PIT_AUTHORITY", "require_pit must be refused")
    if authority.get("qualified_publication_evidence_classes") != []:
        raise BuildRefused("PUBLICATION_CLAIM_UNQUALIFIED", "no publication evidence class is qualified")
    scope = contract.get("scope") or {}
    seasons = scope.get("target_seasons")
    if seasons != list(TARGET_SEASONS):
        bad = sorted(set(seasons or []) & set(PROTECTED_SEASONS + PROSPECTIVE_SEASONS))
        raise BuildRefused("PROTECTED_SEASON_IN_SCOPE" if bad else "CONTRACT_INVALID",
                           f"target seasons {seasons!r}; protected/prospective present: {bad}")
    if scope.get("protected_seasons") != list(PROTECTED_SEASONS):
        raise BuildRefused("CONTRACT_INVALID", "protected seasons differ")
    versions = (contract.get("source_universe") or {}).get("repository_versions") or []
    bad_versions = sorted({v.get("season") for v in versions} & set(PROTECTED_SEASONS + PROSPECTIVE_SEASONS))
    if bad_versions:
        raise BuildRefused("PROTECTED_SEASON_IN_SCOPE", f"repository versions for {bad_versions}")
    payloads = contract.get("payloads") or {}
    if payloads.get("schema_version") != PAYLOAD_SCHEMA:
        raise BuildRefused("CONTRACT_SCHEMA_UNKNOWN", "payload schema differs")
    if payloads.get("record_fields") != {k: list(v) for k, v in RECORD_FIELDS.items()}:
        raise BuildRefused("CONTRACT_INVALID", "payloads.record_fields differ from the producer's closed schemas")
    fields = contract.get("fields") or {}
    if fields.get("order") != list(FIELDS) or fields.get("roles") != ROLES or \
            fields.get("target_relation_fields") != list(TARGET_FIELDS):
        raise BuildRefused("CONTRACT_INVALID", "fields differ from the producer's field set")
    binding = contract.get("parent_binding") or {}
    for side, keys in (("history", ("contract_sha256", "content_identity", "database_identity", "sqlite_sha256",
                                    "db_schema_version")),
                       ("population", ("contract_sha256", "query_db_identity", "sqlite_sha256", "schema_version",
                                       "contest_identity", "program_season_identity"))):
        for key in keys:
            if not isinstance((binding.get(side) or {}).get(key), str):
                raise BuildRefused("CONTRACT_INVALID", f"parent_binding.{side}.{key} missing")
    return contract, sha256_bytes(raw)


# --------------------------------------------------------------------------------------------- parents

def _manifest_for(file_path: Path) -> Path:
    path = Path(file_path).resolve()
    population_root = path.parent.parent.parent
    return population_root.parent.parent / "manifests" / population_root.name / "sha256" / path.parent.name / \
        "run_manifest.json"


def _identity_document(manifest: Path, expected: str) -> dict[str, Any]:
    try:
        document = json.loads(Path(manifest).read_text(encoding="utf-8"))
        identity_document = document["identity_document"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise BuildRefused("PARENT_BINDING_MISMATCH", f"manifest {manifest} unreadable: {exc}") from exc
    computed = sha256_bytes(canonical_json_bytes(identity_document))
    if computed != expected or document.get("identity") != expected:
        raise BuildRefused("PARENT_BINDING_MISMATCH", f"manifest {manifest} identity {computed} != {expected}")
    return identity_document


def data_root_for(population_database: Path) -> Path:
    return Path(population_database).resolve().parents[4]


def verify_population(contract: dict[str, Any], database: Path) -> dict[str, Any]:
    binding = contract["parent_binding"]["population"]
    db = Path(database)
    if not db.is_file() or db.name != POPULATION_DB_FILE or db.resolve().parent.name != binding["query_db_identity"]:
        raise BuildRefused("PARENT_BINDING_MISMATCH", f"{db} is not <root>/sha256/{binding['query_db_identity']}/"
                           + POPULATION_DB_FILE)
    actual = sha256_file(db)
    if actual != binding["sqlite_sha256"]:
        raise BuildRefused("PARENT_BINDING_MISMATCH", f"population database hashes to {actual}")
    document = _identity_document(_manifest_for(db), binding["query_db_identity"])
    upstream = document.get("upstream") or {}
    checks = {"stage": document.get("stage") == "query-db",
              "outputs": (document.get("outputs") or {}).get(POPULATION_DB_FILE) == actual,
              "contract": document.get("contract_sha256") == binding["contract_sha256"],
              "contest": upstream.get("contest") == binding["contest_identity"],
              "program_season": upstream.get("program-season") == binding["program_season_identity"]}
    if not all(checks.values()):
        raise BuildRefused("PARENT_BINDING_MISMATCH", f"population manifest checks {checks}")
    canonical_root = db.resolve().parent.parent
    stages = {}
    for stage, identity, files in (("contest", binding["contest_identity"], binding.get("contest_stage_files") or {}),
                                   ("program-season", binding["program_season_identity"],
                                    binding.get("program_season_stage_files") or {})):
        stage_dir = canonical_root / identity
        stage_document = _identity_document(_manifest_for(stage_dir / "x"), identity)
        if stage_document.get("stage") != stage or stage_document.get("contract_sha256") != binding["contract_sha256"]:
            raise BuildRefused("PARENT_BINDING_MISMATCH", f"{stage} stage manifest names another stage or contract")
        for name, sha in files.items():
            if (stage_document.get("outputs") or {}).get(name) != sha or not (stage_dir / name).is_file() \
                    or sha256_file(stage_dir / name) != sha:
                raise BuildRefused("PARENT_BINDING_MISMATCH", f"{stage} stage file {name} differs from the binding")
        stages[stage] = {"identity": identity, "dir": stage_dir, "document": stage_document}
    return {"query_db_identity": binding["query_db_identity"], "sqlite_sha256": actual,
            "contract_sha256": binding["contract_sha256"], "contest_identity": binding["contest_identity"],
            "program_season_identity": binding["program_season_identity"], "stages": stages}


def verify_history(contract: dict[str, Any], database: Path, population: dict[str, Any]) -> dict[str, Any]:
    binding = contract["parent_binding"]["history"]
    db = Path(database)
    if not db.is_file() or db.name != HISTORY_DB_FILE or db.resolve().parent.name != binding["database_identity"]:
        raise BuildRefused("PARENT_BINDING_MISMATCH", f"{db} is not <root>/sha256/{binding['database_identity']}/"
                           + HISTORY_DB_FILE)
    actual = sha256_file(db)
    if actual != binding["sqlite_sha256"]:
        raise BuildRefused("PARENT_BINDING_MISMATCH", f"history database hashes to {actual}")
    document = _identity_document(_manifest_for(db), binding["database_identity"])
    checks = {"stage": document.get("stage") == "history-database",
              "schema": document.get("db_schema_version") == binding["db_schema_version"],
              "outputs": (document.get("outputs") or {}).get(HISTORY_DB_FILE) == actual,
              "content": document.get("content_identity") == binding["content_identity"],
              "contract": document.get("contract_sha256") == binding["contract_sha256"]}
    if not all(checks.values()):
        raise BuildRefused("PARENT_BINDING_MISMATCH", f"history manifest checks {checks}")
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        meta = {row[0]: row[1] for row in conn.execute("SELECT key, value FROM meta")}
    finally:
        conn.close()
    try:
        parent = json.loads(meta.get("parent") or "null")
    except ValueError:
        parent = None
    expected_parent = {k: population[k] for k in ("query_db_identity", "sqlite_sha256", "contract_sha256",
                                                  "contest_identity", "program_season_identity")}
    if meta.get("schema_version") != binding["db_schema_version"] or \
            meta.get("content_identity") != binding["content_identity"] or \
            meta.get("contract_sha256") != binding["contract_sha256"]:
        raise BuildRefused("PARENT_SCHEMA_UNKNOWN", "history database meta differs from the binding")
    if not isinstance(parent, dict) or {k: parent.get(k) for k in expected_parent} != expected_parent:
        raise BuildRefused("PARENT_BINDING_MISMATCH", "history database parent is not the bound population")
    return {"database_identity": binding["database_identity"], "sqlite_sha256": actual,
            "content_identity": binding["content_identity"], "contract_sha256": binding["contract_sha256"]}


def verify_source_bindings(contract: dict[str, Any], path: Path, history: dict[str, Any],
                           population: dict[str, Any], data_root: Path) -> dict[str, Any]:
    try:
        raw = Path(path).read_bytes()
        bindings = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise BuildRefused("SOURCE_BINDING_MISMATCH", f"source bindings unreadable: {exc}") from exc
    declared = contract["parent_binding"]["source_bindings"]
    delivery = contract["parent_binding"]["delivery_manifest"]
    try:
        checks = {"history": bindings["history_database"]["sha256"] == history["sqlite_sha256"]
                  and bindings["history_database"]["identity"] == history["database_identity"],
                  "population": bindings["population_database"]["sha256"] == population["sqlite_sha256"]
                  and bindings["population_database"]["identity"] == population["query_db_identity"],
                  "delivery": bindings["parent_delivery_manifest"]["sha256"] == delivery["sha256"],
                  "preflight_sha": bindings["source_preflight"]["sha256"] == declared["cache_preflight_sha256"],
                  "preflight_counts": (bindings["source_preflight"]["captures"], bindings["source_preflight"][
                      "source_rows"]) == (declared["captures"], declared["source_rows"])}
    except (KeyError, TypeError) as exc:
        raise BuildRefused("SOURCE_BINDING_MISMATCH", f"source bindings lack {exc}") from exc
    if not all(checks.values()):
        raise BuildRefused("SOURCE_BINDING_MISMATCH", f"source binding checks {checks}")
    delivery_path = data_root / Path(*delivery["path"].split("/"))
    if not delivery_path.is_file() or sha256_file(delivery_path) != delivery["sha256"]:
        raise BuildRefused("SOURCE_BINDING_MISMATCH", "parent delivery manifest differs from the binding")
    preflight_path = Path(bindings["source_preflight"]["path"])
    if not preflight_path.is_file() or sha256_file(preflight_path) != declared["cache_preflight_sha256"]:
        raise BuildRefused("SOURCE_BINDING_MISMATCH", "cache preflight file differs from the binding")
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    flown = sorted((c["season"], c["payload_sha256"], c["api_sha256"], c["rows"]) for c in preflight["captures"])
    mine = sorted((v["season"], v["payload_sha256"], v["commit_api_sha256"], v["rows"])
                  for v in contract["source_universe"]["repository_versions"])
    if flown != mine or sum(c["rows"] for c in preflight["captures"]) != declared["source_rows"]:
        raise BuildRefused("SOURCE_BINDING_MISMATCH", "repository versions differ from the cache preflight")
    return {"sha256": sha256_bytes(raw), "path": str(path)}


def _file(data_root: Path, rel: str, sha: str, code: str = "SOURCE_BINDING_MISMATCH") -> Path:
    path = data_root / Path(*rel.split("/"))
    if not path.is_file() or sha256_file(path) != sha:
        raise BuildRefused(code, f"{rel} is missing or differs from {sha}")
    return path


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


def verify_sources(contract: dict[str, Any], data_root: Path) -> dict[str, Any]:
    universe = contract["source_universe"]
    out: dict[str, Any] = {"repository": [], "fbs": {}, "fcs": {}, "ncaa": {}}
    for version in universe["repository_versions"]:
        manifest_path = _file(data_root, version["manifest"], version["manifest_sha256"])
        payload_path = _file(data_root, version["payload"], version["payload_sha256"])
        api_path = _file(data_root, version["commit_api"], version["commit_api_sha256"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        api = json.loads(api_path.read_text(encoding="utf-8"))
        payload = payload_path.read_bytes()
        files = {f.get("filename"): f.get("sha") for f in api.get("files") or []}
        checks = {"capture": manifest.get("capture_id") == version["capture_id"],
                  "commit": manifest.get("commit_sha") == version["commit_sha"] == api.get("sha"),
                  "payload": (manifest.get("payload") or {}).get("sha256") == version["payload_sha256"],
                  "api": (manifest.get("commit_api_capture") or {}).get("api_sha256") == version["commit_api_sha256"],
                  "season": manifest.get("season") == version["season"],
                  "path": manifest.get("source_path") == version["source_path"],
                  "blob": files.get(version["source_path"]) == git_blob_sha1(payload)}
        if not all(checks.values()):
            raise BuildRefused("REPOSITORY_BYTE_BINDING_MISMATCH", f"{version['capture_id']} checks {checks}")
        out["repository"].append({"version": version, "manifest": manifest, "api": api, "payload_path": payload_path})
    for season, spec in sorted(universe["cfbd_fbs_route"].items()):
        raw = _file(data_root, spec["raw"], spec["sha256"])
        receipt_path = _file(data_root, spec["receipt"], spec["receipt_sha256"])
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("response_sha256") != spec["sha256"] or receipt.get("immutable_path") != spec["raw"]:
            raise BuildRefused("SOURCE_BINDING_MISMATCH", f"FBS route {season} receipt names other bytes")
        out["fbs"][season] = {"spec": spec, "rows": json.loads(raw.read_text(encoding="utf-8")), "receipt": receipt}
    ledger_path = _file(data_root, universe["cycle30_ledger"]["path"], universe["cycle30_ledger"]["sha256"])
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    for season, spec in sorted(universe["cfbd_fcs_route"].items()):
        raw = _file(data_root, spec["raw"], spec["sha256"])
        entries = [(i, a) for i, a in enumerate(ledger.get("attempts") or []) if a.get("raw_sha256") == spec["sha256"]]
        out["fcs"][season] = {"spec": spec, "rows": json.loads(raw.read_text(encoding="utf-8")), "entries": entries}
    for season, spec in sorted(universe["ncaa_bound_manifests"].items()):
        path = _file(data_root, spec["manifest"], spec["sha256"])
        document = json.loads(path.read_text(encoding="utf-8"))
        if document.get("discovery_identity") != spec["identity"] or len(document.get("captures") or []) != \
                spec["captures"]:
            raise BuildRefused("SOURCE_BINDING_MISMATCH", f"NCAA manifest {season} identity or capture count differs")
        out["ncaa"][season] = {"spec": spec, "document": document}
    out["ledger"] = {"path": universe["cycle30_ledger"]["path"], "sha256": universe["cycle30_ledger"]["sha256"]}
    out["universe_sha256"] = sha256_bytes(canonical_json_bytes(universe))
    return out


# --------------------------------------------------------------------------------------------- parent rows

def permute(rows: list[Any], order: str) -> list[Any]:
    if not INPUT_ORDER.match(order):
        raise BuildRefused("INPUT_ORDER_INVALID", order)
    rows = list(rows)
    if order == "reverse":
        rows.reverse()
    elif order.startswith("shuffle:"):
        random.Random(int(order.split(":", 1)[1])).shuffle(rows)
    return rows


def read_history(database: Path, order: str) -> dict[str, Any]:
    conn = sqlite3.connect(Path(database).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        targets = [(ord_, key, season, date, a_key, b_key) for ord_, key, season, date, a_key, b_key in conn.execute(
            "SELECT ord, contest_key, season, contest_date, a_key, b_key FROM targets ORDER BY ord")]
        views = [(ord_, key, view, season, date, team, opponent, json.loads(record)) for
                 ord_, key, view, season, date, team, opponent, record in conn.execute(
                     "SELECT ord, target_contest_key, view, season, target_date, team_key, opponent_key, record "
                     "FROM history ORDER BY ord")]
        exclusions = [row[0] for row in conn.execute("SELECT contest_key FROM exclusions ORDER BY ord")]
        meta = {row[0]: row[1] for row in conn.execute("SELECT key, value FROM meta")}
    finally:
        conn.close()
    return {"targets": permute(targets, order), "views": permute(views, order),
            "exclusions": permute(exclusions, order), "row_counts": json.loads(meta.get("row_counts") or "{}")}


POPULATION_COLUMNS = ("contest_key", "ncaa_contest_id", "season", "term", "contest_date", "site", "contest_status",
                      "a_org_id", "a_team_name", "a_points", "b_org_id", "b_team_name", "b_points", "a_key", "b_key",
                      "cfbd_game_ids")


def read_population(database: Path, population: dict[str, Any], contract: dict[str, Any],
                    order: str) -> dict[str, Any]:
    conn = sqlite3.connect(Path(database).resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        meta = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM meta")}
        binding = contract["parent_binding"]["population"]
        if meta.get("schema_version") != binding["schema_version"] or (
                meta.get("contract_sha256"), meta.get("contest_identity"), meta.get("program_season_identity")) != (
                binding["contract_sha256"], binding["contest_identity"], binding["program_season_identity"]):
            raise BuildRefused("PARENT_SCHEMA_UNKNOWN", "population meta differs from the binding")
        census = [(row["contest_key"], row["season"]) for row in
                  conn.execute("SELECT contest_key, season FROM contest ORDER BY rowid")]
        columns = ", ".join(POPULATION_COLUMNS)
        rows = [dict(row) for row in conn.execute(
            f"SELECT {columns} FROM contest WHERE season >= ? AND season <= ? ORDER BY rowid",
            (TARGET_SEASONS[0], TARGET_SEASONS[-1]))]
    finally:
        conn.close()
    keys = [key for key, _season in census]
    if len(set(keys)) != len(keys) or len(keys) != binding.get("parent_contest_rows", len(keys)):
        raise BuildRefused("PARENT_DUPLICATE_KEY", "population census keys are duplicated or miscounted")
    stage_rows: dict[str, dict[str, Any]] = {}
    with gzip.open(population["stages"]["contest"]["dir"] / "contests.jsonl.gz", "rt", encoding="utf-8") as handle:
        lines = [line for line in handle]
    for line in permute(lines, order):
        record = json.loads(line)
        if "_header" in record or record.get("season") not in TARGET_SEASONS:
            continue  # 2024/2025 stage lines are discarded by season; no field of them is retained
        stage_rows[record["contest_key"]] = {k: record.get(k) for k in ("a_cfbd_team_id", "b_cfbd_team_id",
                                                                          "cfbd_routes", "cfbd_game_ids")}
    pages: list[dict[str, Any]] = []
    with gzip.open(population["stages"]["program-season"]["dir"] / "page_observations.jsonl.gz", "rt",
                   encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if "_header" in record or record.get("season") not in TARGET_SEASONS or not record.get("ncaa_contest_id"):
                continue
            pages.append({k: record.get(k) for k in PAGE_COLUMNS + ("ncaa_contest_id", "page_raw_sha256")})
    return {"census": permute(census, order), "rows": permute(rows, order), "stage": stage_rows,
            "pages": permute(pages, order)}


def _json_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
    except ValueError:
        return [value]
    return parsed if isinstance(parsed, list) else [parsed]


# --------------------------------------------------------------------------------------------- model

def ident(namespace: str, value: Any) -> dict[str, Any]:
    return {"namespace": namespace, "value": _text(value)}


def corroborate(value: Any, parent: Any, state: str = "OK") -> str:
    if state == "MALFORMED":
        return "SOURCE_VALUE_MALFORMED"
    if value is None:
        return "SOURCE_VALUE_NULL"
    return "AGREES_WITH_PARENT" if value == parent else "CONFLICTS_WITH_PARENT"


class Model:
    """Every output record, derived from the verified parents and sources only."""

    def __init__(self, contract: dict[str, Any], history: dict[str, Any], population: dict[str, Any],
                 sources: dict[str, Any], order: str) -> None:
        self.contract = contract
        self.order = order
        self.parent_rows = {row["contest_key"]: row for row in population["rows"]}
        self.stage = population["stage"]
        self.census = sorted(population["census"], key=lambda item: (item[1], item[0]))
        targets = sorted(history["targets"])
        self.target_keys = [row[1] for row in targets]
        views = sorted(history["views"], key=lambda item: item[0])
        self.views = views
        roles: dict[str, set[str]] = {key: {"TARGET"} for key in self.target_keys}
        for _ord, _key, _view, _season, _date, _team, _opponent, record in views:
            for block in ("team_history", "opponent_history"):
                for item in record[block]["contributing"]:
                    roles.setdefault(item["contest_key"], set()).add("CONTRIBUTOR")
        self.roles = roles
        missing = sorted(k for k in roles if k not in self.parent_rows)
        if missing:
            raise BuildRefused("CENSUS_INCOMPLETE", f"history keys absent from the 2016-2023 parent rows: {missing[:5]}")
        self.universe = sorted(roles, key=lambda k: (self.parent_rows[k]["season"], self.parent_rows[k]["contest_date"],
                                                     k))
        self.history_partition = {key: "TARGET" for key in self.target_keys}
        for key in history["exclusions"]:
            self.history_partition[key] = "EXCLUSION"
        counts = history["row_counts"]
        if len(self.target_keys) != counts.get("targets.jsonl") or len(history["exclusions"]) != counts.get(
                "exclusions.jsonl") or len(views) != counts.get("history.jsonl"):
            raise BuildRefused("CENSUS_INCOMPLETE", "history tables disagree with the history row counts")
        self.sources = sources
        self._index_pages(population["pages"])
        self._index_ncaa()
        self._index_routes()
        self.captures: dict[str, dict[str, Any]] = {}
        self.repository_rows = self._repository_rows()

    # ------------------------------------------------------------------ indexes
    def _index_pages(self, pages: list[dict[str, Any]]) -> None:
        wanted = {(self.parent_rows[k]["ncaa_contest_id"], self.parent_rows[k]["season"]): k for k in self.universe}
        self.pages: dict[str, list[dict[str, Any]]] = {}
        for page in pages:
            key = wanted.get((page["ncaa_contest_id"], page["season"]))
            if key:
                self.pages.setdefault(key, []).append(page)
        for rows in self.pages.values():
            rows.sort(key=lambda p: (p["page_raw_sha256"], p["row_index"]))

    def _index_ncaa(self) -> None:
        self.ncaa_captures: dict[str, list[tuple[str, int, dict[str, Any], int]]] = {}
        for season, item in self.sources["ncaa"].items():
            captures = item["document"].get("captures") or []
            shared: dict[str, int] = {}
            for capture in captures:
                shared[capture.get("retrieved_at_utc")] = shared.get(capture.get("retrieved_at_utc"), 0) + 1
            for index, capture in enumerate(captures):
                self.ncaa_captures.setdefault(capture.get("raw_sha256"), []).append(
                    (season, index, capture, shared[capture.get("retrieved_at_utc")]))

    def _index_routes(self) -> None:
        self.routes: dict[tuple[str, str], dict[str, list[dict[str, Any]]]] = {}
        for route, key in (("SRC-002", "fbs"), ("CYCLE30_FCS", "fcs")):
            for season, item in self.sources[key].items():
                index: dict[str, list[dict[str, Any]]] = {}
                for row in permute(item["rows"], self.order):
                    index.setdefault(_text(row.get("id")), []).append(row)
                self.routes[(route, season)] = index

    # ------------------------------------------------------------------ captures
    def ncaa_capture(self, raw_sha: str) -> dict[str, Any]:
        capture_id = f"ncaa_page:{raw_sha}"
        if capture_id in self.captures:
            return self.captures[capture_id]
        entries = sorted(self.ncaa_captures.get(raw_sha, []), key=lambda e: (e[0], e[1]))
        absent = clock("ABSENT", reason="SINGLE_RETAINED_REVISION_NO_CORRECTION_OBSERVED")
        publication = clock("ABSENT", reason="NO_QUALIFIED_INDEPENDENT_PUBLICATION_EVIDENCE")
        na = clock("NOT_APPLICABLE", reason="NOT_A_REPOSITORY_VERSION")
        if not entries:
            record = {"record_type": "capture", "capture_id": capture_id, "source_kind": "NCAA_TEAM_SEASON_PAGE",
                      "route": None, "season": None, "source_uri": None, "payload_path": None,
                      "payload_sha256": raw_sha, "source_revision": raw_sha, "byte_binding": "NOT_VERIFIED_NO_CAPTURE",
                      "receipt_document": None, "receipt_document_sha256": None, "receipt_pointer": None,
                      "receipt_stamp_shared_by": 0, "time_evidence_class": "NO_RECEIPT",
                      "clocks": {"retrieval": clock("ABSENT", role="RECORDED_POSSESSION_UPPER_BOUND",
                                                    reason="NCAA_CAPTURE_NOT_IN_BOUND_MANIFEST"),
                                 "asserted_commit_author": na, "asserted_commit_committer": na,
                                 "supported_publication": publication, "correction": absent}}
        else:
            season, index, capture, shared = entries[0]
            spec = self.sources["ncaa"][season]["spec"]
            rel = capture.get("raw_relative_path")
            path = self.data_root / Path(*str(rel).split("/")) if rel else None
            bound = bool(path) and path.is_file() and path.name == f"{raw_sha}.html" and sha256_file(path) == raw_sha
            literals = sorted({e[2].get("retrieved_at_utc") for e in entries}, key=str)
            if len(literals) > 1:
                retrieval = contradictory_clock([str(x) for x in literals], role="RECORDED_POSSESSION_UPPER_BOUND",
                                                document=spec["manifest"],
                                                pointers=[f"/captures/{e[1]}/retrieved_at_utc" for e in entries])
            else:
                retrieval = present_clock(capture.get("retrieved_at_utc"), role="RECORDED_POSSESSION_UPPER_BOUND",
                                          document=spec["manifest"], pointer=f"/captures/{index}/retrieved_at_utc")
            record = {"record_type": "capture", "capture_id": capture_id, "source_kind": "NCAA_TEAM_SEASON_PAGE",
                      "route": None, "season": int(season), "source_uri": capture.get("source_uri"),
                      "payload_path": rel, "payload_sha256": raw_sha, "source_revision": raw_sha,
                      "byte_binding": "RAW_SHA256_VERIFIED" if bound else "RAW_BYTES_MISSING_OR_DIFFERENT",
                      "receipt_document": spec["manifest"], "receipt_document_sha256": spec["sha256"],
                      "receipt_pointer": f"/captures/{index}", "receipt_stamp_shared_by": shared,
                      "time_evidence_class": "RECORDED_RETRIEVAL_STAMP_ONLY" if retrieval["state"] == "PRESENT"
                      else "NO_RECEIPT",
                      "clocks": {"retrieval": retrieval, "asserted_commit_author": na, "asserted_commit_committer": na,
                                 "supported_publication": publication, "correction": absent}}
        self.captures[capture_id] = record
        return record

    def route_capture(self, route: str, season: str) -> dict[str, Any]:
        key = "fbs" if route == "SRC-002" else "fcs"
        item = self.sources[key][season]
        spec = item["spec"]
        capture_id = f"cfbd_route:{route}:{season}:{spec['sha256']}"
        if capture_id in self.captures:
            return self.captures[capture_id]
        absent = clock("ABSENT", reason="SINGLE_RETAINED_REVISION_NO_CORRECTION_OBSERVED")
        publication = clock("ABSENT", reason="NO_QUALIFIED_INDEPENDENT_PUBLICATION_EVIDENCE")
        na = clock("NOT_APPLICABLE", reason="NOT_A_REPOSITORY_VERSION")
        if route == "SRC-002":
            receipt = item["receipt"]
            retrieval = present_clock(receipt.get("retrieved_at_utc"), role="EXACT_REQUEST_INTERVAL",
                                      start_literal=receipt.get("retrieval_started_at_utc"),
                                      document=spec["receipt"], pointer="/retrieved_at_utc")
            record = {"record_type": "capture", "capture_id": capture_id, "source_kind": "CFBD_ROUTE_RESPONSE",
                      "route": route, "season": int(season), "source_uri": receipt.get("source_uri"),
                      "payload_path": spec["raw"], "payload_sha256": spec["sha256"], "source_revision": spec["sha256"],
                      "byte_binding": "RESPONSE_SHA256_MATCHES_RECEIPT", "receipt_document": spec["receipt"],
                      "receipt_document_sha256": spec["receipt_sha256"], "receipt_pointer": "",
                      "receipt_stamp_shared_by": 1,
                      "time_evidence_class": "EXACT_REQUEST_RECEIPT_ONLY" if retrieval["state"] == "PRESENT"
                      else "NO_RECEIPT"}
        else:
            entries = item["entries"]
            ledger = self.sources["ledger"]
            shared = 0
            if not entries:
                retrieval = clock("ABSENT", role="CACHE_HIT_POSSESSION_UPPER_BOUND", reason="LEDGER_ENTRY_ABSENT")
                pointer = None
            else:
                literals = sorted({str(a.get("retrieved_at_utc")) for _i, a in entries})
                role = "CACHE_HIT_POSSESSION_UPPER_BOUND" if all(a.get("status") == "CACHE_HIT" for _i, a in entries) \
                    else "RECORDED_POSSESSION_UPPER_BOUND"
                pointer = f"/attempts/{entries[0][0]}"
                if len(literals) > 1:
                    retrieval = contradictory_clock(literals, role=role, document=ledger["path"],
                                                    pointers=[f"/attempts/{i}/retrieved_at_utc" for i, _a in entries])
                else:
                    retrieval = present_clock(entries[0][1].get("retrieved_at_utc"), role=role,
                                              document=ledger["path"], pointer=pointer + "/retrieved_at_utc")
                shared = sum(1 for a in self.sources["ledger_attempts"]
                             if a.get("retrieved_at_utc") == entries[0][1].get("retrieved_at_utc"))
            record = {"record_type": "capture", "capture_id": capture_id, "source_kind": "CFBD_ROUTE_RESPONSE",
                      "route": route, "season": int(season),
                      "source_uri": f"cfbd:/games?classification=fcs&year={season}",
                      "payload_path": spec["raw"], "payload_sha256": spec["sha256"], "source_revision": spec["sha256"],
                      "byte_binding": "CONTENT_SHA256_MATCHES_LEDGER_RAW_SHA256" if entries else "CONTENT_SHA256_ONLY",
                      "receipt_document": ledger["path"] if entries else None,
                      "receipt_document_sha256": ledger["sha256"] if entries else None, "receipt_pointer": pointer,
                      "receipt_stamp_shared_by": shared,
                      "time_evidence_class": "CACHE_HIT_RECEIPT_ONLY" if retrieval["state"] == "PRESENT" and
                      retrieval["role"] == "CACHE_HIT_POSSESSION_UPPER_BOUND" else (
                          "RECORDED_RETRIEVAL_STAMP_ONLY" if retrieval["state"] == "PRESENT" else "NO_RECEIPT")}
        record["clocks"] = {"retrieval": retrieval, "asserted_commit_author": na, "asserted_commit_committer": na,
                            "supported_publication": publication, "correction": absent}
        self.captures[capture_id] = record
        return record

    def repository_capture(self, item: dict[str, Any], shared: int) -> dict[str, Any]:
        version, manifest, api = item["version"], item["manifest"], item["api"]
        capture_id = f"repo_version:{version['capture_id']}"
        commit = api.get("commit") or {}
        retrieval = present_clock(manifest.get("acquired_at_utc"), role="RECORDED_POSSESSION_UPPER_BOUND",
                                  document=version["manifest"], pointer="/acquired_at_utc")
        record = {"record_type": "capture", "capture_id": capture_id, "source_kind": "REPOSITORY_VERSION",
                  "route": version["repository"], "season": version["season"], "source_uri": manifest.get("source_url"),
                  "payload_path": version["payload"], "payload_sha256": version["payload_sha256"],
                  "source_revision": version["commit_sha"], "byte_binding": "GIT_BLOB_SHA1_MATCHES_COMMIT_FILE_ENTRY",
                  "receipt_document": version["manifest"], "receipt_document_sha256": version["manifest_sha256"],
                  "receipt_pointer": "", "receipt_stamp_shared_by": shared,
                  "time_evidence_class": "RECORDED_RETRIEVAL_STAMP_WITH_ASSERTED_COMMIT_TIME"
                  if retrieval["state"] == "PRESENT" else "NO_RECEIPT",
                  "clocks": {"retrieval": retrieval,
                             "asserted_commit_author": present_clock(
                                 (commit.get("author") or {}).get("date"), role="SOURCE_ASSERTED",
                                 document=version["commit_api"], pointer="/commit/author/date"),
                             "asserted_commit_committer": present_clock(
                                 (commit.get("committer") or {}).get("date"), role="SOURCE_ASSERTED",
                                 document=version["commit_api"], pointer="/commit/committer/date"),
                             "supported_publication": clock("ABSENT",
                                                            reason="NO_QUALIFIED_INDEPENDENT_PUBLICATION_EVIDENCE"),
                             "correction": clock("ABSENT", reason="SINGLE_RETAINED_REVISION_NO_CORRECTION_OBSERVED")}}
        self.captures[capture_id] = record
        return record

    # ------------------------------------------------------------------ repository rows
    def _repository_rows(self) -> list[dict[str, Any]]:
        import polars as pl  # noqa: PLC0415 - Parquet reads only

        cfbd_index: dict[str, list[str]] = {}
        for key, row in self.parent_rows.items():
            for value in _json_list(row["cfbd_game_ids"]):
                cfbd_index.setdefault(str(value), []).append(key)
        stamps: dict[str, int] = {}
        for item in self.sources["repository"]:
            stamp = item["manifest"].get("acquired_at_utc")
            stamps[stamp] = stamps.get(stamp, 0) + 1
        out = []
        for item in sorted(self.sources["repository"], key=lambda i: i["version"]["season"]):
            capture = self.repository_capture(item, stamps[item["manifest"].get("acquired_at_utc")])
            frame = pl.read_parquet(item["payload_path"])
            if frame.height != item["version"]["rows"]:
                raise BuildRefused("SOURCE_BINDING_MISMATCH", f"{capture['capture_id']} has {frame.height} rows")
            missing = [c for c in REPOSITORY_COLUMNS if c not in frame.columns]
            if missing:
                raise BuildRefused("SOURCE_SCHEMA_UNKNOWN", f"{capture['capture_id']} lacks {missing}")
            rows = list(enumerate(frame.select(list(REPOSITORY_COLUMNS)).iter_rows(named=True)))
            for index, row in sorted(permute(rows, self.order), key=lambda pair: pair[0]):
                out.append(self._repository_row(capture, item["version"], index, row, cfbd_index))
        return out

    def _repository_row(self, capture: dict[str, Any], version: dict[str, Any], index: int, row: dict[str, Any],
                        cfbd_index: dict[str, list[str]]) -> dict[str, Any]:
        event_raw = row["game_id"] if row["game_id"] is not None else row["id"]
        event_id, event_state = normalize_int(event_raw)
        event_clock = present_clock(row["start_date"], role="SOURCE_ASSERTED", document=version["payload"],
                                    pointer=f"/rows/{index}/start_date")
        record = {"record_type": "repository_row", "capture_id": capture["capture_id"],
                  "native_row_key": f"parquet_row:{index}", "season": version["season"],
                  "source_revision": version["commit_sha"],
                  "identifiers": {"event": ident("ESPN_EVENT_ID", event_raw),
                                  "home_team": ident("ESPN_TEAM_ID", row["home_id"]),
                                  "away_team": ident("ESPN_TEAM_ID", row["away_id"])},
                  "literals": {name: _text(row[name]) for name in REPOSITORY_COLUMNS},
                  "event_clock": event_clock, "join_state": None, "join_reasons": [], "national_contest_key": None,
                  "candidate_contest_keys": [], "orientation": None, "site_note": None}
        if event_state != "OK":
            record.update(join_state="UNJOINED", join_reasons=["UNJOINED_EVENT_ID_MALFORMED"])
            return record
        candidates = sorted(cfbd_index.get(str(event_id), []))
        record["candidate_contest_keys"] = candidates
        if not candidates:
            record.update(join_state="UNJOINED", join_reasons=["UNJOINED_NO_PARENT_CANDIDATE"])
            return record
        if len(candidates) > 1:
            record.update(join_state="AMBIGUOUS_MULTIPLE_PARENT_CANDIDATES",
                          join_reasons=["AMBIGUOUS_MULTIPLE_PARENT_CANDIDATES"])
            return record
        key = candidates[0]
        parent = self.parent_rows[key]
        stage = self.stage.get(key) or {}
        reasons = []
        season, season_state = normalize_int(row["season"])
        if season_state != "OK" or season != parent["season"]:
            reasons.append("CONFLICTING_SEASON")
        home, home_state = normalize_int(row["home_id"])
        away, away_state = normalize_int(row["away_id"])
        a_id, b_id = stage.get("a_cfbd_team_id"), stage.get("b_cfbd_team_id")
        orientation = None
        if a_id is None or b_id is None:
            reasons.append("PARENT_TEAM_ID_UNBOUND")
        elif home_state != "OK" or away_state != "OK" or {str(home), str(away)} != {str(a_id), str(b_id)} \
                or str(home) == str(away):
            reasons.append("CONFLICTING_PARTICIPANT_IDENTITY")
        else:
            orientation = "A" if str(home) == str(a_id) else "B"
            neutral = row["neutral_site"]
            if parent["site"] in ("HOME_A", "HOME_B") and neutral is False and parent["site"] != f"HOME_{orientation}":
                reasons.append("CONFLICTING_SITE_ORIENTATION")
            elif parent["site"] in ("HOME_A", "HOME_B") and neutral is True:
                record["site_note"] = "SITE_DESIGNATION_DIFFERS_SOURCE_NEUTRAL"
        if row["status_type_completed"] is not True or parent["contest_status"] != "COMPLETED":
            reasons.append("CONFLICTING_COMPLETION")
        home_score, hs_state = normalize_int(row["home_score"])
        away_score, as_state = normalize_int(row["away_score"])
        if hs_state == "MALFORMED" or as_state == "MALFORMED":
            reasons.append("SOURCE_VALUE_MALFORMED")
        elif orientation is not None:
            expected = (parent["a_points"], parent["b_points"]) if orientation == "A" else (parent["b_points"],
                                                                                            parent["a_points"])
            if (home_score, away_score) != expected or home_score is None:
                reasons.append("CONFLICTING_SCORES")
        if parent["contest_date"] not in local_candidate_dates(event_clock):
            reasons.append("DATE_NOT_IN_DECLARED_US_LOCAL_CANDIDATES")
        record["orientation"] = {"home_side": orientation} if orientation else None
        if reasons:
            record.update(join_state="CONFLICTING", join_reasons=reasons)
            return record
        record.update(national_contest_key=key,
                      join_state="JOINED" if key in self.roles else "JOINED_OUTSIDE_UNIVERSE",
                      join_reasons=[])
        return record

    # ------------------------------------------------------------------ bundles
    def assertion(self, key: str, capture: dict[str, Any], native: str, field: str, column: str, literal: Any,
                  value: Any, parent_value: Any, corroboration: str) -> dict[str, Any]:
        return {"record_type": "assertion", "contest_key": key, "capture_id": capture["capture_id"],
                "native_row_key": native, "field": field, "source_revision": capture["source_revision"],
                "source_kind": capture["source_kind"], "field_role": ROLES[field], "source_column": column,
                "literal": _text(literal), "value": value, "parent_value": parent_value,
                "corroboration": corroboration}

    def parent_values(self, key: str) -> dict[str, Any]:
        row = self.parent_rows[key]
        return {"season": row["season"], "contest_date": row["contest_date"], "a_participant": row["a_key"],
                "b_participant": row["b_key"],
                "completion": "COMPLETED" if row["contest_status"] == "COMPLETED" else "NOT_COMPLETED",
                "a_points": row["a_points"], "b_points": row["b_points"]}

    def page_bundle(self, key: str, page: dict[str, Any], parent: dict[str, Any]) -> tuple[dict, list[dict], dict]:
        row = self.parent_rows[key]
        capture = self.ncaa_capture(page["page_raw_sha256"])
        native = f"page_row:{page['row_index']}"
        page_org, opp_org = _text(page["page_org_id"]), _text(page["opponent_logo_org_id"])
        side = "A" if page_org == _text(row["a_org_id"]) else ("B" if page_org == _text(row["b_org_id"]) else None)
        day = parse_local_date(page["date_text"])
        event_clock = present_clock(page["date_text"], role="SOURCE_ASSERTED", document=capture["payload_path"],
                                    pointer=f"schedule_row/{page['row_index']}/date", allow_local_date=True)
        lineage = {"record_type": "lineage_row", "contest_key": key, "capture_id": capture["capture_id"],
                   "native_row_key": native, "source_kind": "NCAA_TEAM_SEASON_PAGE", "route": None,
                   "source_revision": capture["source_revision"],
                   "identifiers": {"event": ident("NCAA_CONTEST_ID", page["ncaa_contest_id"]),
                                   "page_team": ident("NCAA_ORG_ID", page_org),
                                   "opponent": ident("NCAA_ORG_ID", opp_org)},
                   "literals": {name: _text(page[name]) for name in PAGE_COLUMNS},
                   "event_clock": event_clock, "join_state": "PARENT_LINEAGE",
                   "orientation": {"page_team_side": side}}
        out = []
        season, s_state = normalize_int(page["season"])
        out.append(self.assertion(key, capture, native, "season", "page.season", page["season"], season,
                                  parent["season"], corroborate(season, parent["season"], s_state)))
        dates = [day.isoformat()] if day else None
        out.append(self.assertion(key, capture, native, "contest_date", "page.date_text", page["date_text"], dates,
                                  parent["contest_date"],
                                  "SOURCE_VALUE_MALFORMED" if page["date_text"] is not None and day is None else (
                                      "SOURCE_VALUE_NULL" if day is None else
                                      ("AGREES_WITH_PARENT" if dates == [parent["contest_date"]]
                                       else "CONFLICTS_WITH_PARENT"))))
        team_points, tp_state = normalize_int(page["team_points"])
        opp_points, op_state = normalize_int(page["opponent_points"])
        for field_side in ("a", "b"):
            if side is None:
                out.append(self.assertion(key, capture, native, f"{field_side}_participant", "page.page_org_id",
                                          page_org, f"org:{page_org}" if page_org else None,
                                          parent[f"{field_side}_participant"], "CONFLICTS_WITH_PARENT"))
                continue
            own = field_side.upper() == side
            org = page_org if own else opp_org
            column = "page.page_org_id" if own else "page.opponent_logo_org_id"
            value = f"org:{org}" if org else None
            out.append(self.assertion(key, capture, native, f"{field_side}_participant", column, org, value,
                                      parent[f"{field_side}_participant"],
                                      corroborate(value, parent[f"{field_side}_participant"])
                                      if value is not None else "NOT_ASSERTED_BY_SOURCE_ROW"))
        completion = "COMPLETED" if page["status"] == "COMPLETED" else "NOT_COMPLETED"
        out.append(self.assertion(key, capture, native, "completion", "page.result_text", page["result_text"],
                                  completion, parent["completion"], corroborate(completion, parent["completion"])))
        for field_side in ("a", "b"):
            if side is None:
                value, state, column, literal = None, "NULL", "page.team_points", page["team_points"]
            elif field_side.upper() == side:
                value, state, column, literal = team_points, tp_state, "page.team_points", page["team_points"]
            else:
                value, state, column, literal = opp_points, op_state, "page.opponent_points", page["opponent_points"]
            out.append(self.assertion(key, capture, native, f"{field_side}_points", column, literal, value,
                                      parent[f"{field_side}_points"],
                                      corroborate(value, parent[f"{field_side}_points"], state)
                                      if side is not None else "CONFLICTS_WITH_PARENT"))
        return lineage, out, capture

    def route_bundle(self, key: str, route: str, game: dict[str, Any], parent: dict[str, Any]) -> tuple[dict, list]:
        row = self.parent_rows[key]
        stage = self.stage.get(key) or {}
        capture = self.route_capture(route, str(row["season"]))
        native = f"cfbd_game_id:{_text(game.get('id'))}"
        a_id, b_id = _text(stage.get("a_cfbd_team_id")), _text(stage.get("b_cfbd_team_id"))
        home, away = _text(game.get("homeId")), _text(game.get("awayId"))
        side = "A" if a_id and home == a_id else ("B" if b_id and home == b_id else None)
        event_clock = present_clock(game.get("startDate"), role="SOURCE_ASSERTED", document=capture["payload_path"],
                                    pointer=f"/[id={_text(game.get('id'))}]/startDate")
        lineage = {"record_type": "lineage_row", "contest_key": key, "capture_id": capture["capture_id"],
                   "native_row_key": native, "source_kind": "CFBD_ROUTE_RESPONSE", "route": route,
                   "source_revision": capture["source_revision"],
                   "identifiers": {"event": ident("CFBD_GAME_ID", game.get("id")),
                                   "home_team": ident("CFBD_TEAM_ID", game.get("homeId")),
                                   "away_team": ident("CFBD_TEAM_ID", game.get("awayId"))},
                   "literals": {name: _text(game.get(name)) for name in CFBD_COLUMNS},
                   "event_clock": event_clock, "join_state": "PARENT_LINEAGE", "orientation": {"home_side": side}}
        out = []
        season, s_state = normalize_int(game.get("season"))
        out.append(self.assertion(key, capture, native, "season", "cfbd.season", game.get("season"), season,
                                  parent["season"], corroborate(season, parent["season"], s_state)))
        out.append(self._instant_date(key, capture, native, "cfbd.startDate", game.get("startDate"), event_clock,
                                      parent["contest_date"]))
        pair = {home, away}
        for field_side, bound in (("a", a_id), ("b", b_id)):
            ok = bound is not None and bound in pair and home != away
            out.append(self.assertion(key, capture, native, f"{field_side}_participant", "cfbd.homeId|awayId",
                                      f"{home}|{away}", parent[f"{field_side}_participant"] if ok else None,
                                      parent[f"{field_side}_participant"],
                                      "AGREES_WITH_PARENT" if ok else "CONFLICTS_WITH_PARENT"))
        completed = game.get("completed")
        completion = "COMPLETED" if completed is True else "NOT_COMPLETED"
        out.append(self.assertion(key, capture, native, "completion", "cfbd.completed", completed, completion,
                                  parent["completion"], corroborate(completion, parent["completion"])))
        for field_side in ("a", "b"):
            column = None
            if side is not None:
                column = "homePoints" if field_side.upper() == side else "awayPoints"
            literal = game.get(column) if column else None
            value, state = normalize_int(literal) if column else (None, "NULL")
            out.append(self.assertion(key, capture, native, f"{field_side}_points",
                                      f"cfbd.{column}" if column else "cfbd.homePoints|awayPoints", literal, value,
                                      parent[f"{field_side}_points"],
                                      corroborate(value, parent[f"{field_side}_points"], state)
                                      if column else "CONFLICTS_WITH_PARENT"))
        return lineage, out

    def _instant_date(self, key: str, capture: dict[str, Any], native: str, column: str, literal: Any,
                      event_clock: dict[str, Any], parent_date: str) -> dict[str, Any]:
        if event_clock["state"] != "PRESENT":
            corr = "SOURCE_VALUE_NULL" if literal is None else "SOURCE_VALUE_MALFORMED"
            return self.assertion(key, capture, native, "contest_date", column, literal, None, parent_date, corr)
        dates = local_candidate_dates(event_clock)
        return self.assertion(key, capture, native, "contest_date", column, literal, dates, parent_date,
                              "AGREES_WITH_PARENT" if parent_date in dates else
                              "NOT_CORROBORATED_BY_DECLARED_DATE_BASIS")

    def repository_assertions(self, key: str, record: dict[str, Any], parent: dict[str, Any]) -> list[dict[str, Any]]:
        capture = self.captures[record["capture_id"]]
        lit = record["literals"]
        side = record["orientation"]["home_side"]
        native = record["native_row_key"]
        out = []
        season, s_state = normalize_int(lit["season"])
        out.append(self.assertion(key, capture, native, "season", "repo.season", lit["season"], season,
                                  parent["season"], corroborate(season, parent["season"], s_state)))
        out.append(self._instant_date(key, capture, native, "repo.start_date", lit["start_date"],
                                      record["event_clock"], parent["contest_date"]))
        for field_side in ("a", "b"):
            column = "home_id" if field_side.upper() == side else "away_id"
            out.append(self.assertion(key, capture, native, f"{field_side}_participant", f"repo.{column}", lit[column],
                                      parent[f"{field_side}_participant"], parent[f"{field_side}_participant"],
                                      "AGREES_WITH_PARENT"))
        completion = "COMPLETED" if lit["status_type_completed"] == "true" else "NOT_COMPLETED"
        out.append(self.assertion(key, capture, native, "completion", "repo.status_type_completed",
                                  lit["status_type_completed"], completion, parent["completion"],
                                  corroborate(completion, parent["completion"])))
        for field_side in ("a", "b"):
            column = "home_score" if field_side.upper() == side else "away_score"
            value, state = normalize_int(lit[column])
            out.append(self.assertion(key, capture, native, f"{field_side}_points", f"repo.{column}", lit[column],
                                      value, parent[f"{field_side}_points"],
                                      corroborate(value, parent[f"{field_side}_points"], state)))
        return out

    def bundle(self, key: str) -> bytes:
        row = self.parent_rows[key]
        stage = self.stage.get(key) or {}
        parent = self.parent_values(key)
        lineage_rows, assertions, missing = [], [], []
        coverage = {kind: 0 for kind in KIND_ORDER}
        pages = self.pages.get(key, [])
        for page in pages:
            lineage, items, capture = self.page_bundle(key, page, parent)
            lineage_rows.append(lineage)
            assertions.extend(items)
            coverage["NCAA_TEAM_SEASON_PAGE"] += 1
            if capture["clocks"]["retrieval"]["state"] != "PRESENT" and "NCAA_CAPTURE_RECEIPT_ABSENT" not in missing:
                missing.append("NCAA_CAPTURE_RECEIPT_ABSENT")
        if not pages:
            missing.append("NCAA_PAGE_ROW_ABSENT")
        elif len(pages) == 1:
            missing.append("NCAA_SECOND_MIRROR_ABSENT")
        game_ids = [_text(g) for g in _json_list(row["cfbd_game_ids"])]
        for route in sorted(stage.get("cfbd_routes") or []):
            index = self.routes.get((route, str(row["season"])), {})
            games = [g for gid in game_ids for g in index.get(gid, [])]
            if not games:
                if "CFBD_ROUTE_ROW_ABSENT" not in missing:
                    missing.append("CFBD_ROUTE_ROW_ABSENT")
                continue
            for game in sorted(games, key=lambda g: _text(g.get("id"))):
                lineage, items = self.route_bundle(key, route, game, parent)
                lineage_rows.append(lineage)
                assertions.extend(items)
                coverage["CFBD_ROUTE_RESPONSE"] += 1
        joined = [r for r in self.repository_by_key.get(key, [])]
        for record in joined:
            assertions.extend(self.repository_assertions(key, record, parent))
            coverage["REPOSITORY_VERSION"] += 1
        repo_seasons = {v["season"] for v in self.contract["source_universe"]["repository_versions"]}
        if row["season"] not in repo_seasons:
            missing.append("REPOSITORY_VERSION_ABSENT_FOR_SEASON")
        elif not joined:
            missing.append("REPOSITORY_VERSION_ROW_NOT_JOINED")
        kind_rank = {k: i for i, k in enumerate(KIND_ORDER)}
        field_rank = {f: i for i, f in enumerate(FIELDS)}
        assertions.sort(key=lambda a: (kind_rank[a["source_kind"]], a["capture_id"], a["native_row_key"],
                                       field_rank[a["field"]]))
        lineage_rows.sort(key=lambda r: (kind_rank[r["source_kind"]], r["capture_id"], r["native_row_key"]))
        seen = set()
        for item in assertions:
            natural = (item["contest_key"], item["capture_id"], item["native_row_key"], item["field"],
                       item["source_revision"])
            if natural in seen:
                raise BuildRefused("DUPLICATE_NATURAL_KEY", f"assertion {natural}")
            seen.add(natural)
        contest = {"record_type": "contest", "contest_key": key, "ncaa_contest_id": row["ncaa_contest_id"],
                   "season": row["season"], "term": row["term"], "contest_date": row["contest_date"],
                   "a_key": row["a_key"], "b_key": row["b_key"], "a_org_id": row["a_org_id"],
                   "b_org_id": row["b_org_id"], "a_team_name": row["a_team_name"], "b_team_name": row["b_team_name"],
                   "parent_site": row["site"], "roles": sorted(self.roles[key]),
                   "cfbd_game_id": ident("CFBD_GAME_ID", game_ids[0] if len(game_ids) == 1 else
                                         ("|".join(game_ids) if game_ids else None)),
                   "a_cfbd_team_id": ident("CFBD_TEAM_ID", stage.get("a_cfbd_team_id")),
                   "b_cfbd_team_id": ident("CFBD_TEAM_ID", stage.get("b_cfbd_team_id")),
                   "source_coverage": coverage, "missing_evidence": missing, "assertion_count": len(assertions),
                   "season_scope_state": "AUDITED_2016_2023"}
        return b"".join([record_line(contest)] + [record_line(a) for a in assertions] +
                        [record_line(r) for r in lineage_rows])

    def prepare(self) -> None:
        """Index joined repository rows and pre-register every capture so census bytes do not depend on chunks."""
        self.repository_by_key: dict[str, list[dict[str, Any]]] = {}
        for record in self.repository_rows:
            if record["join_state"] == "JOINED":
                self.repository_by_key.setdefault(record["national_contest_key"], []).append(record)
        for records in self.repository_by_key.values():
            records.sort(key=lambda r: (r["capture_id"], r["native_row_key"]))
        for key in self.universe:
            for page in self.pages.get(key, []):
                self.ncaa_capture(page["page_raw_sha256"])
            row = self.parent_rows[key]
            for route in (self.stage.get(key) or {}).get("cfbd_routes") or []:
                if (route, str(row["season"])) in self.routes:
                    self.route_capture(route, str(row["season"]))

    # ------------------------------------------------------------------ census payloads
    def partition_records(self) -> list[dict[str, Any]]:
        out = []
        for key, season in self.census:
            history = self.history_partition.get(key, "OUT_OF_SCOPE")
            if history == "OUT_OF_SCOPE" and season in TARGET_SEASONS:
                raise BuildRefused("CENSUS_INCOMPLETE", f"{key} is a 2016-2023 key outside the history partition")
            if key in self.roles:
                scope = "IN_SCOPE"
            elif season in PROTECTED_SEASONS or season not in TARGET_SEASONS:
                scope = "KEY_ONLY_PROTECTED_EXPOSED"
            else:
                scope = "NOT_REFERENCED_BY_HISTORY_RELATIONS"
            out.append({"record_type": "partition", "contest_key": key, "season": season, "history_partition": history,
                        "source_time_scope": scope, "roles": sorted(self.roles.get(key, ()))})
        return out

    def relation_records(self) -> list[dict[str, Any]]:
        out = []
        for _ord, key, view, season, date, team, opponent, record in self.views:
            out.append({"record_type": "relation", "relation_type": "TARGET_CONTEST", "target_contest_key": key,
                        "view": view, "side": None, "history_team_key": team, "contributor_contest_key": key,
                        "season": season, "target_date": date, "contributor_date": date,
                        "required_fields": list(TARGET_FIELDS)})
            for side, block in (("TEAM", "team_history"), ("OPPONENT", "opponent_history")):
                if record[block]["team_key"] != (team if side == "TEAM" else opponent):
                    raise BuildRefused("PARENT_SCHEMA_INVALID", f"{key} {view} {block} names another team")
                for item in record[block]["contributing"]:
                    out.append({"record_type": "relation", "relation_type": "CONTRIBUTOR", "target_contest_key": key,
                                "view": view, "side": side, "history_team_key": record[block]["team_key"],
                                "contributor_contest_key": item["contest_key"], "season": season,
                                "target_date": date, "contributor_date": item["contest_date"],
                                "required_fields": list(FIELDS)})
        seen = set()
        for rel in out:
            natural = (rel["relation_type"], rel["target_contest_key"], rel["view"], rel["side"],
                       rel["contributor_contest_key"])
            if natural in seen:
                raise BuildRefused("DUPLICATE_NATURAL_KEY", f"relation {natural}")
            seen.add(natural)
        return out

    def capture_records(self) -> list[dict[str, Any]]:
        rank = {k: i for i, k in enumerate(KIND_ORDER)}
        return sorted(self.captures.values(), key=lambda c: (rank[c["source_kind"]], c["capture_id"]))

    def census_bytes(self) -> dict[str, bytes]:
        return {"partition.jsonl": b"".join(record_line(r) for r in self.partition_records()),
                "repository_rows.jsonl": b"".join(record_line(r) for r in self.repository_rows),
                "captures.jsonl": b"".join(record_line(r) for r in self.capture_records()),
                "relations.jsonl": b"".join(record_line(r) for r in self.relation_records())}


def split_bundles(blob: bytes) -> dict[str, bytes]:
    out: dict[str, list[bytes]] = {name: [] for name in BUNDLE_FILES.values()}
    for line in blob.splitlines(keepends=True):
        kind = json.loads(line)["record_type"]
        if kind not in BUNDLE_FILES:
            raise BuildRefused("REFUSED_ALTERED_PREFIX", f"unexpected record type {kind} in the bundle stream")
        out[BUNDLE_FILES[kind]].append(line)
    return {name: b"".join(lines) for name, lines in out.items()}


# --------------------------------------------------------------------------------------------- checkpoint

def _keys_sha(keys: Sequence[str]) -> str:
    return sha256_bytes("\n".join(keys).encode("utf-8"))


class Checkpoint:
    def __init__(self, directory: Path, header: dict[str, Any], chunk_size: int, resume: bool) -> None:
        self.dir = Path(directory)
        self.chunk_size = chunk_size
        self.ledger = self.dir / "checkpoint.ledger.jsonl"
        header_path = self.dir / "checkpoint.json"
        if resume:
            if not header_path.is_file():
                raise BuildRefused("REFUSED_STALE_CHECKPOINT", f"no checkpoint header in {self.dir}")
            stored = json.loads(header_path.read_text(encoding="utf-8"))
            differing = sorted(k for k in set(stored) | set(header) if stored.get(k) != header.get(k))
            if differing:
                raise BuildRefused("REFUSED_STALE_CHECKPOINT", f"checkpoint binds different {differing}")
        else:
            if self.dir.exists() and any(self.dir.iterdir()):
                raise BuildRefused("CHECKPOINT_EXISTS", f"{self.dir} is not empty; use --resume")
            (self.dir / "chunks").mkdir(parents=True, exist_ok=True)
            with header_path.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(header, sort_keys=True, indent=1) + "\n")

    def chunk_path(self, index: int) -> Path:
        return self.dir / "chunks" / f"chunk_{index:06d}.jsonl.gz"

    @staticmethod
    def read_chunk(path: Path) -> bytes:
        return gzip.decompress(path.read_bytes())

    def completed(self, keys_all: list[str]) -> list[dict[str, Any]]:
        if not self.ledger.is_file():
            return []
        lines = self.ledger.read_text(encoding="utf-8").split("\n")
        rows = [json.loads(line) for line in lines[:-1] if line]
        prefix = ""
        for expected_index, row in enumerate(rows, start=1):
            start = (expected_index - 1) * self.chunk_size
            keys = keys_all[start:start + self.chunk_size]
            path = self.chunk_path(expected_index)
            if row.get("index") != expected_index or row.get("count") != len(keys) or \
                    row.get("keys_sha256") != _keys_sha(keys) or not keys or \
                    row.get("first_key") != keys[0] or row.get("last_key") != keys[-1]:
                raise BuildRefused("REFUSED_ALTERED_PREFIX", f"ledger row {expected_index} does not match the key prefix")
            if not path.is_file() or sha256_bytes(self.read_chunk(path)) != row.get("chunk_sha256"):
                raise BuildRefused("REFUSED_ALTERED_PREFIX", f"chunk {expected_index} bytes differ from the ledger")
            prefix = sha256_bytes((prefix + row["chunk_sha256"]).encode("ascii"))
            if row.get("prefix_sha256") != prefix:
                raise BuildRefused("REFUSED_ALTERED_PREFIX", f"chained prefix breaks at chunk {expected_index}")
        return rows

    def write_chunk(self, index: int, keys: list[str], blob: bytes, previous_prefix: str) -> dict[str, Any]:
        path = self.chunk_path(index)
        packed = gzip.compress(blob, compresslevel=6, mtime=0)
        if path.exists():
            if self.read_chunk(path) != blob:
                raise BuildRefused("REFUSED_FORKED_CHECKPOINT", f"unrecorded chunk {index} differs from the rebuild")
        else:
            temporary = path.with_suffix(".partial")
            if temporary.exists():
                raise BuildRefused("REFUSED_FORKED_CHECKPOINT", f"partial chunk {index} present")
            with temporary.open("xb") as handle:
                handle.write(packed)
            os.replace(temporary, path)
        chunk_sha = sha256_bytes(blob)
        row = {"index": index, "count": len(keys), "first_key": keys[0], "last_key": keys[-1],
               "keys_sha256": _keys_sha(keys), "chunk_sha256": chunk_sha,
               "prefix_sha256": sha256_bytes((previous_prefix + chunk_sha).encode("ascii"))}
        with self.ledger.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return row


def build_bundles(model: Model, *, chunk_size: int, checkpoint: Checkpoint | None,
                  stop_after: int | None) -> bytes | None:
    keys = model.universe
    if checkpoint is None:
        return b"".join(model.bundle(key) for key in keys)
    done = checkpoint.completed(keys)
    prefix = done[-1]["prefix_sha256"] if done else ""
    written = 0
    index = len(done)
    while index * chunk_size < len(keys):
        index += 1
        part = keys[(index - 1) * chunk_size:index * chunk_size]
        blob = b"".join(model.bundle(key) for key in part)
        prefix = checkpoint.write_chunk(index, part, blob, prefix)["prefix_sha256"]
        written += 1
        if stop_after is not None and written >= stop_after and index * chunk_size < len(keys):
            return None
    rows = checkpoint.completed(keys)
    if sum(row["count"] for row in rows) != len(keys):
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "checkpoint does not cover every universe contest")
    return b"".join(checkpoint.read_chunk(checkpoint.chunk_path(row["index"])) for row in rows)


# --------------------------------------------------------------------------------------------- database

TABLE_SQL = (
    "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
    "CREATE TABLE partition (ord INTEGER PRIMARY KEY, contest_key TEXT NOT NULL UNIQUE, season INTEGER NOT NULL,"
    " history_partition TEXT NOT NULL, source_time_scope TEXT NOT NULL, record TEXT NOT NULL);"
    "CREATE TABLE contests (ord INTEGER PRIMARY KEY, contest_key TEXT NOT NULL UNIQUE, season INTEGER NOT NULL,"
    " contest_date TEXT, a_key TEXT, b_key TEXT, record TEXT NOT NULL, assertion_count INTEGER NOT NULL,"
    " assertion_first_ord INTEGER NOT NULL, assertions BLOB NOT NULL, lineage_count INTEGER NOT NULL,"
    " lineage_first_ord INTEGER NOT NULL, lineage BLOB NOT NULL);"
    "CREATE TABLE captures (ord INTEGER PRIMARY KEY, capture_id TEXT NOT NULL UNIQUE, source_kind TEXT NOT NULL,"
    " time_evidence_class TEXT NOT NULL, record TEXT NOT NULL);"
    "CREATE TABLE repository_rows (ord INTEGER PRIMARY KEY, capture_id TEXT NOT NULL, native_row_key TEXT NOT NULL,"
    " season INTEGER NOT NULL, join_state TEXT NOT NULL, national_contest_key TEXT, record TEXT NOT NULL,"
    " UNIQUE (capture_id, native_row_key));"
    "CREATE TABLE relation_groups (ord INTEGER PRIMARY KEY, target_contest_key TEXT NOT NULL UNIQUE,"
    " season INTEGER NOT NULL, target_date TEXT NOT NULL, team_keys TEXT NOT NULL, relation_count INTEGER NOT NULL,"
    " relation_first_ord INTEGER NOT NULL, relations BLOB NOT NULL);")
INDEX_SQL = (
    "CREATE INDEX ix_partition_season ON partition (season, ord);"
    "CREATE INDEX ix_contests_season ON contests (season, ord);"
    "CREATE INDEX ix_contests_a ON contests (a_key, ord);"
    "CREATE INDEX ix_contests_b ON contests (b_key, ord);"
    "CREATE INDEX ix_repository_season ON repository_rows (season, ord);"
    "CREATE INDEX ix_repository_contest ON repository_rows (national_contest_key, ord);"
    "CREATE INDEX ix_repository_state ON repository_rows (join_state, ord);"
    "CREATE INDEX ix_relation_groups_season ON relation_groups (season, ord);")
TABLES = ("meta", "partition", "contests", "captures", "repository_rows", "relation_groups")
#: payload file -> how its records are held in the database (exact canonical lines, grouped and zlib-compressed)
RECORD_HOMES = {"partition.jsonl": "partition", "contests.jsonl": "contests", "assertions.jsonl": "contests.assertions",
                "lineage_rows.jsonl": "contests.lineage", "repository_rows.jsonl": "repository_rows",
                "captures.jsonl": "captures", "relations.jsonl": "relation_groups.relations"}
ZLIB_LEVEL = 9


def _lines(payload: bytes) -> list[str]:
    return payload.decode("utf-8").splitlines(keepends=True)


def _grouped(lines: list[str], key: str) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    last = None
    for line in lines:
        value = json.loads(line)[key]
        if value != last and value in groups:
            raise BuildRefused("PAYLOAD_ORDER_INVALID", f"{key} {value} is not contiguous")
        groups.setdefault(value, []).append(line)
        last = value
    return groups


def build_database(path: Path, payloads: dict[str, bytes], meta: dict[str, str]) -> dict[str, Any]:
    """Write the query database: small tables hold exact payload lines; assertions/lineage rows (per contest) and
    relations (per target) are held as zlib-compressed concatenations of their exact canonical lines."""
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA page_size = 4096")
        conn.execute("PRAGMA journal_mode = OFF")
        conn.executescript(TABLE_SQL)
        conn.executemany("INSERT INTO meta VALUES (?, ?)", sorted(meta.items()))
        partition = _lines(payloads["partition.jsonl"])
        conn.executemany("INSERT INTO partition VALUES (?, ?, ?, ?, ?, ?)",
                         [(i, r["contest_key"], r["season"], r["history_partition"], r["source_time_scope"],
                           line.rstrip("\n")) for i, (r, line) in enumerate((json.loads(x), x) for x in partition)])
        assertions = _grouped(_lines(payloads["assertions.jsonl"]), "contest_key")
        lineage = _grouped(_lines(payloads["lineage_rows.jsonl"]), "contest_key")
        rows, a_ord, l_ord = [], 0, 0
        for i, line in enumerate(_lines(payloads["contests.jsonl"])):
            record = json.loads(line)
            key = record["contest_key"]
            a_lines, l_lines = assertions.pop(key, []), lineage.pop(key, [])
            if len(a_lines) != record["assertion_count"]:
                raise BuildRefused("CENSUS_INCOMPLETE", f"{key} assertion count differs")
            rows.append((i, key, record["season"], record["contest_date"], record["a_key"], record["b_key"],
                         line.rstrip("\n"), len(a_lines), a_ord, zlib.compress("".join(a_lines).encode("utf-8"),
                                                                               ZLIB_LEVEL),
                         len(l_lines), l_ord, zlib.compress("".join(l_lines).encode("utf-8"), ZLIB_LEVEL)))
            a_ord += len(a_lines)
            l_ord += len(l_lines)
        if assertions or lineage:
            raise BuildRefused("CENSUS_INCOMPLETE", "assertions or lineage rows name a contest outside contests.jsonl")
        conn.executemany("INSERT INTO contests VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
        conn.executemany("INSERT INTO captures VALUES (?, ?, ?, ?, ?)",
                         [(i, r["capture_id"], r["source_kind"], r["time_evidence_class"], line.rstrip("\n"))
                          for i, (r, line) in enumerate((json.loads(x), x)
                                                        for x in _lines(payloads["captures.jsonl"]))])
        conn.executemany("INSERT INTO repository_rows VALUES (?, ?, ?, ?, ?, ?, ?)",
                         [(i, r["capture_id"], r["native_row_key"], r["season"], r["join_state"],
                           r["national_contest_key"], line.rstrip("\n"))
                          for i, (r, line) in enumerate((json.loads(x), x)
                                                        for x in _lines(payloads["repository_rows.jsonl"]))])
        groups, r_ord = [], 0
        for i, (target, lines) in enumerate(_grouped(_lines(payloads["relations.jsonl"]),
                                                     "target_contest_key").items()):
            first = json.loads(lines[0])
            teams = sorted({json.loads(x)["history_team_key"] for x in lines})
            groups.append((i, target, first["season"], first["target_date"], json.dumps(teams), len(lines), r_ord,
                           zlib.compress("".join(lines).encode("utf-8"), ZLIB_LEVEL)))
            r_ord += len(lines)
        conn.executemany("INSERT INTO relation_groups VALUES (?, ?, ?, ?, ?, ?, ?, ?)", groups)
        conn.executescript(INDEX_SQL)
        conn.commit()
        counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES}
        records = {"assertions.jsonl": conn.execute("SELECT COALESCE(SUM(assertion_count), 0) FROM contests").fetchone()[0],
                   "lineage_rows.jsonl": conn.execute("SELECT COALESCE(SUM(lineage_count), 0) FROM contests").fetchone()[0],
                   "relations.jsonl": conn.execute(
                       "SELECT COALESCE(SUM(relation_count), 0) FROM relation_groups").fetchone()[0],
                   "contests.jsonl": counts["contests"], "partition.jsonl": counts["partition"],
                   "captures.jsonl": counts["captures"], "repository_rows.jsonl": counts["repository_rows"]}
    finally:
        conn.close()
    return {"table_counts": counts, "record_counts": records}


# --------------------------------------------------------------------------------------------- materialization

def runtime() -> dict[str, str]:
    import polars as pl  # noqa: PLC0415

    return {"implementation": platform.python_implementation(), "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version, "zlib": zlib.ZLIB_VERSION, "polars": pl.__version__}


def materialize(output_root: Path, manifest_root: Path, identity_document: dict[str, Any],
                files: dict[str, Path | bytes], provenance: dict[str, Any]) -> dict[str, Any]:
    """Create-only content-addressed write: verify an existing identity, never overwrite it."""
    identity = sha256_bytes(canonical_json_bytes(identity_document))
    target = Path(output_root) / "sha256" / identity
    manifest = Path(manifest_root) / "sha256" / identity / "run_manifest.json"
    declared = identity_document["outputs"]
    state = "MATERIALIZED"
    if target.exists():
        present = sorted(p.name for p in target.iterdir())
        if present != sorted(declared) or any(sha256_file(target / name) != sha for name, sha in declared.items()):
            raise BuildRefused("REFUSED_IMMUTABLE_COLLISION", f"{target} exists with different content")
        state = "ALREADY_PRESENT_IDENTICAL"
    else:
        temporary = Path(output_root) / "sha256" / f".tmp-{identity[:16]}-{os.getpid()}-{time.time_ns()}"
        temporary.mkdir(parents=True)
        for name, source in files.items():
            data = source if isinstance(source, bytes) else Path(source).read_bytes()
            with (temporary / name).open("xb") as handle:
                handle.write(data)
            if sha256_file(temporary / name) != declared[name]:
                raise BuildRefused("WRITE_VERIFY_FAILED", name)
        os.rename(temporary, target)
    if manifest.exists():
        existing = json.loads(manifest.read_text(encoding="utf-8"))
        if existing.get("identity") != identity or existing.get("identity_document") != identity_document:
            raise BuildRefused("REFUSED_IMMUTABLE_COLLISION", f"{manifest} names a different identity")
        manifest_state = "ALREADY_PRESENT"
    else:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        with manifest.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"identity": identity, "identity_document": identity_document,
                                     "provenance": provenance}, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
        manifest_state = "WRITTEN"
    return {"identity": identity, "state": state, "data_dir": str(target), "manifest": str(manifest),
            "manifest_state": manifest_state}


def build(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    contract, contract_sha = load_contract(args.contract)
    if args.chunk_size < 0 or (args.stop_after_chunks is not None and args.stop_after_chunks < 1):
        raise BuildRefused("ARGUMENT_INVALID", "chunk size and stop-after must be positive")
    if (args.resume or args.stop_after_chunks is not None) and not args.checkpoint_dir:
        raise BuildRefused("ARGUMENT_INVALID", "--resume and --stop-after-chunks need --checkpoint-dir")
    if args.checkpoint_dir and args.chunk_size < 1:
        raise BuildRefused("ARGUMENT_INVALID", "--checkpoint-dir needs --chunk-size >= 1")
    if not INPUT_ORDER.match(args.input_order):
        raise BuildRefused("INPUT_ORDER_INVALID", args.input_order)
    population = verify_population(contract, args.population_database)
    history_binding = verify_history(contract, args.history_database, population)
    data_root = data_root_for(args.population_database)
    bindings = verify_source_bindings(contract, args.source_bindings, history_binding, population, data_root)
    sources = verify_sources(contract, data_root)
    sources["ledger_attempts"] = json.loads((data_root / Path(*contract["source_universe"]["cycle30_ledger"][
        "path"].split("/"))).read_text(encoding="utf-8")).get("attempts") or []
    history = read_history(args.history_database, args.input_order)
    parent_rows = read_population(args.population_database, population, contract, args.input_order)
    model = Model(contract, history, parent_rows, sources, args.input_order)
    model.data_root = data_root
    model.prepare()
    census = model.census_bytes()
    checkpoint = None
    parent_doc = {"history": {k: history_binding[k] for k in ("database_identity", "sqlite_sha256",
                                                              "content_identity", "contract_sha256")},
                  "population": {k: population[k] for k in ("query_db_identity", "sqlite_sha256", "contract_sha256",
                                                            "contest_identity", "program_season_identity")}}
    if args.checkpoint_dir:
        header = {"schema": CHECKPOINT_SCHEMA, "contract_sha256": contract_sha, "parent": parent_doc,
                  "source_universe_sha256": sources["universe_sha256"], "payload_schema": PAYLOAD_SCHEMA,
                  "chunk_size": args.chunk_size, "unit_key_list_sha256": _keys_sha(model.universe),
                  "unit_count": len(model.universe),
                  "census_sha256": sha256_bytes(b"".join(census[name] for name in sorted(census))),
                  "producer_sha256": sha256_file(Path(__file__))}
        checkpoint = Checkpoint(Path(args.checkpoint_dir), header, args.chunk_size, args.resume)
    blob = build_bundles(model, chunk_size=args.chunk_size, checkpoint=checkpoint, stop_after=args.stop_after_chunks)
    if blob is None:
        return {"state": "INTERRUPTED_AT_CHECKPOINT", "checkpoint_dir": str(args.checkpoint_dir),
                "completed_chunks": len(checkpoint.completed(model.universe)) if checkpoint else 0,
                "unit_count": len(model.universe)}
    payloads = split_bundles(blob)
    payloads.update(census)
    counts = {name: payloads[name].count(b"\n") for name in PAYLOAD_FILES}
    if counts["partition.jsonl"] != len(model.census) or counts["contests.jsonl"] != len(model.universe):
        raise BuildRefused("CENSUS_INCOMPLETE", "partition or contest records do not match the census/universe")
    semantic = {name: sha256_bytes(payloads[name]) for name in PAYLOAD_FILES}
    packed = {f"{name}.gz": gzip.compress(payloads[name], compresslevel=GZIP_LEVEL, mtime=0) for name in PAYLOAD_FILES}
    content_document = {"schema": CONTENT_SCHEMA, "stage": "source-time-content", "population": POPULATION,
                        "contract_id": contract["contract_id"], "contract_sha256": contract_sha, "parent": parent_doc,
                        "source_universe_sha256": sources["universe_sha256"], "payload_schema": PAYLOAD_SCHEMA,
                        "payload_encoding": "gzip(level 9, mtime 0) of the canonical JSONL; semantic sha256 over the "
                                            "uncompressed bytes",
                        "semantic_outputs": semantic, "outputs": {name: sha256_bytes(data) for name, data in packed.items()},
                        "row_counts": counts}
    content_identity = sha256_bytes(canonical_json_bytes(content_document))
    with tempfile.TemporaryDirectory(prefix="nst-") as work:
        db_path = Path(work) / DB_FILE
        meta = {"schema_version": DB_SCHEMA, "contract_id": contract["contract_id"], "contract_sha256": contract_sha,
                "content_identity": content_identity, "payload_schema": PAYLOAD_SCHEMA,
                "semantic_sha256": json.dumps(semantic, sort_keys=True),
                "row_counts": json.dumps(counts, sort_keys=True), "parent": json.dumps(parent_doc, sort_keys=True),
                "source_universe_sha256": sources["universe_sha256"],
                "row_labels": json.dumps(AUTHORITY, sort_keys=True),
                "fields": json.dumps({"order": list(FIELDS), "roles": ROLES,
                                      "target_relation_fields": list(TARGET_FIELDS)}, sort_keys=True),
                "record_homes": json.dumps(RECORD_HOMES, sort_keys=True),
                "target_seasons": json.dumps(list(TARGET_SEASONS))}
        db_counts = build_database(db_path, payloads, meta)
        if db_counts["record_counts"] != counts:
            raise BuildRefused("CENSUS_INCOMPLETE", f"database records {db_counts['record_counts']} != {counts}")
        database_document = {"schema": DATABASE_SCHEMA, "stage": "source-time-database", "population": POPULATION,
                             "contract_sha256": contract_sha, "content_identity": content_identity,
                             "parent": parent_doc, "db_schema_version": DB_SCHEMA,
                             "outputs": {DB_FILE: sha256_file(db_path)}, "table_counts": db_counts["table_counts"],
                             "record_counts": db_counts["record_counts"]}
        database_identity = sha256_bytes(canonical_json_bytes(database_document))
        provenance = {"producer": PRODUCER, "producer_path": str(Path(__file__).resolve()),
                      "producer_sha256": sha256_file(Path(__file__)), "argv": list(args.argv),
                      "issued_at_utc": _dt.datetime.now(UTC).replace(microsecond=0).isoformat(),
                      "processing_clock": "nonsemantic run provenance only", "runtime": runtime(),
                      "variant": args.variant, "input_order": args.input_order, "chunk_size": args.chunk_size,
                      "resumed": bool(args.resume), "jira_key": contract.get("jira_key"),
                      "cycle_number": contract.get("cycle_number"), "attempt_number": contract.get("attempt_number"),
                      "source_bindings": bindings, "database_identity": database_identity,
                      "database_manifest": f"sha256/{database_identity}/run_manifest.json"}
        content = materialize(args.output_root, args.manifest_root, content_document, packed, provenance)
        database = materialize(args.output_root, args.manifest_root, database_document, {DB_FILE: db_path},
                               {**provenance, "content_identity": content_identity})
    return {"state": content["state"], "content_identity": content_identity, "database_identity": database_identity,
            "content": content, "database": database, "row_counts": counts,
            "table_counts": db_counts["table_counts"], "semantic_sha256": semantic,
            "payload_sha256": content_document["outputs"], "database_sha256": database_document["outputs"][DB_FILE],
            "database_state": database["state"], "contract_sha256": contract_sha, "parent": parent_doc,
            "source_universe_sha256": sources["universe_sha256"], "input_order": args.input_order,
            "chunk_size": args.chunk_size, "variant": args.variant, "runtime": runtime(),
            "seconds": round(time.time() - started, 3)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_national_source_time", allow_abbrev=False,
                                     description="Build the national 2016-2023 source-time evidence dataset.")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--history-database", required=True, type=Path)
    parser.add_argument("--population-database", required=True, type=Path)
    parser.add_argument("--source-bindings", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--manifest-root", required=True, type=Path)
    parser.add_argument("--input-order", default="natural")
    parser.add_argument("--chunk-size", type=int, default=0)
    parser.add_argument("--checkpoint-dir", type=Path, default=None)
    parser.add_argument("--stop-after-chunks", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--variant", default="CANONICAL")
    parser.add_argument("--receipt", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(raw)
    args.argv = ["tools/build_national_source_time.py", *raw]
    try:
        result = build(args)
    except BuildRefused as exc:
        print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
        return 2
    text = json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if args.receipt is not None:
        with Path(args.receipt).open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    sys.stdout.write(text)
    return INTERRUPTED_EXIT if result["state"] == "INTERRUPTED_AT_CHECKPOINT" else 0


if __name__ == "__main__":
    raise SystemExit(main())

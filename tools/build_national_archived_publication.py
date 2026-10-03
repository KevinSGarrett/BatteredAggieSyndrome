r"""Build the archived-publication evidence sidecar for the fixed 2019 tranche (BAT-713, Cycle #41 TP41-A01).

``python -B tools/build_national_archived_publication.py --contract configs/national_archived_publication_2019_contract.json
--source-database <data>/canonical/national_source_time_2016_2023/sha256/<id>/national_source_time.sqlite
--source-bindings <INPUT_BINDINGS.json> --tranche <ARCHIVE_TRANCHE.json>
--output-root <data>/canonical/national_archived_publication_2019
--manifest-root <data>/manifests/national_archived_publication_2019 [--stage capture|materialize|all]``

Standard library only. Two stages:

* ``capture`` (the only networked stage): for each tranche key, at most two Internet Archive availability requests and
  two replay requests under the contract's acquisition section (128 requests in total, one at a time, at least one
  second between request starts, Retry-After honoured within its cap, no proxies, no credentials, no live ESPN
  request, no redirect to another host). An append-only journal records an INTENT line before and a RESULT line after
  every request; every response body goes create-only into the content-addressed raw store. The retained manager
  control is registered with zero requests. The finalized acquisition document is content addressed by the sha256 of
  its canonical bytes; a rerun with a finalized acquisition makes no request.
* ``materialize`` (offline): verifies the contract, the parent source-time database (location, run manifest, identity
  document, bytes), the manager's source bindings and tranche, the acquisition document and journal, every raw body
  and the control's retained receipts; checks each replayed version's receipts; reads only the main game element of
  each archived page with an HTML tokenizer; qualifies every field witness against the parent's accepted values; and
  writes, create-only and content addressed, ``dispositions.jsonl``, ``requests.jsonl``, ``captures.jsonl``,
  ``assertions.jsonl`` (gzip) and ``national_archived_publication.sqlite`` with their run manifests.

Nothing here admits anything: an archive capture is an upper bound for the exact witnessed version, the parent's
assertions and clocks are untouched, and the query decides cutoffs from the retained receipt literals.
``--chunk-size`` with ``--checkpoint-dir`` builds through a hash-chained checkpoint that ``--resume`` verifies;
``--stop-after-chunks`` simulates an interruption; ``--input-order`` permutes the tranche processing order.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import email.utils
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
import urllib.error
import urllib.parse
import urllib.request
import zlib
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Sequence

PRODUCER = "national_archived_publication/1.0.0"
POPULATION = "national_archived_publication_2019"
CONTRACT_SCHEMA = "1.0.0"
CONTRACT_ID_PREFIX = "BAT-713-NATIONAL-ARCHIVED-PUBLICATION-2019-"
PAYLOAD_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-PAYLOAD-1"
CONTENT_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-CONTENT-1"
DATABASE_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-DATABASE-1"
DB_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-DB-1"
ACQUISITION_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-ACQUISITION-1"
JOURNAL_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-JOURNAL-1"
CHECKPOINT_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-CHECKPOINT-1"
DB_FILE = "national_archived_publication.sqlite"
SOURCE_DB_FILE = "national_source_time.sqlite"
SOURCE_DATABASE_DOCUMENT_SCHEMA = "BAS-NATIONAL-SOURCE-TIME-DATABASE-1"
SOURCE_DB_SCHEMA = "BAS-NATIONAL-SOURCE-TIME-DB-1"
AUTHORITY = {"evidence_authority": "ARCHIVED_PUBLICATION_EVIDENCE_ONLY",
             "pit_admission": "NOT_ADMITTED_NO_SEPARATE_PIT_ADMISSION_AUTHORITY",
             "publication_inference": "ARCHIVE_CAPTURE_UPPER_BOUND_FOR_EXACT_WITNESSED_VERSION_ONLY_NOT_FIRST_PUBLICATION",
             "scope": "BOUNDED_2019_TRANCHE_28_CONTESTS_NOT_NATIONAL_COVERAGE"}
FIELDS = ("season", "contest_date", "a_participant", "b_participant", "completion", "a_points", "b_points")
ROLES = {"season": "IDENTITY", "contest_date": "IDENTITY", "a_participant": "IDENTITY", "b_participant": "IDENTITY",
         "completion": "OUTCOME", "a_points": "OUTCOME", "b_points": "OUTCOME"}
WITNESSABLE = ("contest_date", "a_participant", "b_participant", "completion", "a_points", "b_points")
PAYLOAD_FILES = ("dispositions.jsonl", "requests.jsonl", "captures.jsonl", "assertions.jsonl")
BUNDLE_FILES = {"archive_disposition": "dispositions.jsonl", "archive_request": "requests.jsonl",
                "archive_capture": "captures.jsonl", "archive_assertion": "assertions.jsonl"}
RECORD_FIELDS: dict[str, tuple[str, ...]] = {
    "archive_disposition": ("record_type", "ord", "contest_key", "season", "contest_date", "a_key", "b_key",
                            "classification_pair", "stratum", "selection_role", "candidate_url", "game_id_literal",
                            "acquisition_outcome", "disposition", "reasons", "request_count", "metadata_requests",
                            "replay_requests", "capture_ids", "qualified_capture_ids", "field_support",
                            "parent_values"),
    "archive_request": ("record_type", "seq", "contest_key", "kind", "purpose", "url", "started_utc", "ended_utc",
                        "outcome", "http_status", "reason", "headers", "location", "body_sha256", "body_bytes",
                        "body_path", "retry_after_seconds", "slept_seconds", "error", "metadata_answer"),
    "archive_capture": ("record_type", "capture_id", "contest_key", "origin", "request_seq", "original_url",
                        "final_url", "wayback_timestamp", "http_status", "content_type", "memento_datetime_literal",
                        "origin_date_literal", "link_original", "archive_src", "payload_sha256", "payload_bytes",
                        "payload_path", "receipt_document", "receipt_document_sha256", "receipt_pointer",
                        "receipt_checks", "state", "quarantine_reasons", "time_evidence_class", "clocks",
                        "main_element_spans", "page_status", "page_participants", "orientation", "field_states"),
    "archive_assertion": ("record_type", "contest_key", "original_url", "capture_id", "payload_sha256",
                          "source_revision", "field", "field_role", "witness", "witness_span", "literal", "value",
                          "parent_value", "parent_comparator", "corroboration", "field_state"),
    "clock": ("state", "role", "literal", "start_literal", "zone", "precision", "earliest_utc", "latest_utc",
              "evidence_document", "evidence_pointer", "reason"),
}
CLOCK_KINDS = ("archive_capture", "retrieval", "event")
INPUT_ORDER = re.compile(r"^(natural|reverse|shuffle:[0-9]{1,9})$")
TS14_RE = re.compile(r"^[0-9]{14}$")
DIGITS_RE = re.compile(r"^[0-9]{1,12}$")
SCORE_RE = re.compile(r"^[0-9]{1,3}$")
FINAL_RE = re.compile(r"^Final(/[0-9]*OT)?$")
INSTANT_RE = re.compile(r"^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2})(?::([0-9]{2}))?(Z|[+-][0-9]{2}:[0-9]{2})$")
TEAM_HREF_RE = re.compile(r"^(?:https?://www\.espn\.com)?/college-football/team/_/id/([0-9]{1,12})(?:/[^\s\"'<>]*)?$")
NAV_ID_RE = re.compile(r"^gamepackage-([0-9]{1,12})$")
JS_ASSIGN_RE = re.compile(r'espn\.gamepackage\.(gameId|status|homeTeamId|awayTeamId|timestamp)\s*=\s*"([^"\\\r\n]*)"\s*;')
GAME_PATH_RE = re.compile(r"^/college-football/game/_/gameId/([0-9]{1,12})$")
REPLAY_PATH_RE = re.compile(r"^/web/([0-9]{14})id_/(.+)$")
CLOSEST_URL_RE = re.compile(r"^https?://web\.archive\.org/web/([0-9]{14})(?:[a-z]{2}_)?/(.+)$")
US_LOCAL_OFFSETS_HOURS = (-4, -10)
EARLIEST_ZONE_HOURS = 14
ORIGIN_DATE_TOLERANCE_SECONDS = 300
USABLE_CLOSEST_STATUS = ("200", "301", "302", "307", "308")
REDIRECT_STATUS = (301, 302, 303, 307, 308)
RETRYABLE_STATUS = (429, 500, 502, 503, 504)
INTERRUPTED_EXIT = 3
GZIP_LEVEL = 9
ZLIB_LEVEL = 9
UTC = _dt.timezone.utc
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
ALLOWED_HOSTS = ("archive.org", "web.archive.org")


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
    if kind == "archive_capture":
        if set(record["clocks"]) != set(CLOCK_KINDS):
            raise BuildRefused("UNKNOWN_FIELD", f"capture clocks {sorted(record['clocks'])}")
        for clock_value in record["clocks"].values():
            _check_fields("clock", clock_value)
        if set(record["field_states"]) != set(FIELDS):
            raise BuildRefused("UNKNOWN_FIELD", "capture field states")
    _assert_no_float(record)
    return canonical_json_bytes(record) + b"\n"


# --------------------------------------------------------------------------------------------- clocks and URLs

def fmt_utc(value: _dt.datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def utc_now() -> str:
    return fmt_utc(_dt.datetime.now(UTC))


def parse_utc(text: str) -> _dt.datetime:
    return _dt.datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)


def ts14_instant(ts: str) -> _dt.datetime:
    if not TS14_RE.match(ts or ""):
        raise ValueError("TIMESTAMP_NOT_14_DIGITS")
    return _dt.datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=UTC)


def rfc1123(text: Any) -> _dt.datetime:
    """An RFC 1123 HTTP date in GMT; anything else (naive, other zone, malformed) raises ValueError."""
    if not isinstance(text, str) or not text.strip().endswith("GMT"):
        raise ValueError("HTTP_DATE_NOT_GMT")
    parsed = email.utils.parsedate_to_datetime(text)
    if parsed is None or parsed.tzinfo is None or parsed.utcoffset() != _dt.timedelta(0):
        raise ValueError("HTTP_DATE_MALFORMED")
    return parsed.astimezone(UTC)


def end_of_second(value: _dt.datetime) -> _dt.datetime:
    return value.replace(microsecond=999999)


def earliest_event_instant(contest_date: str) -> _dt.datetime:
    day = _dt.date.fromisoformat(contest_date)
    zone = _dt.timezone(_dt.timedelta(hours=EARLIEST_ZONE_HOURS))
    return _dt.datetime(day.year, day.month, day.day, tzinfo=zone).astimezone(UTC)


def clock(state: str, *, role: str | None = None, literal: str | None = None, start_literal: str | None = None,
          zone: str | None = None, precision: str | None = None, earliest: str | None = None,
          latest: str | None = None, document: str | None = None, pointer: str | None = None,
          reason: str | None = None) -> dict[str, Any]:
    return {"state": state, "role": role, "literal": literal, "start_literal": start_literal, "zone": zone,
            "precision": precision, "earliest_utc": earliest, "latest_utc": latest, "evidence_document": document,
            "evidence_pointer": pointer, "reason": reason}


def event_interval(literal: str) -> tuple[str, str, str, str]:
    """(precision, zone, earliest_utc, latest_utc) of an ISO event instant literal with minute or second precision."""
    match = INSTANT_RE.match(literal or "")
    if not match:
        raise ValueError("EVENT_INSTANT_MALFORMED")
    year, month, day, hour, minute, second, zone = match.groups()
    if zone == "Z":
        tz = UTC
    else:
        sign = 1 if zone[0] == "+" else -1
        tz = _dt.timezone(sign * _dt.timedelta(hours=int(zone[1:3]), minutes=int(zone[4:6])))
    value = _dt.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second or 0), tzinfo=tz)
    if second is None:
        return "minute", zone, fmt_utc(value), fmt_utc(value + _dt.timedelta(seconds=59, microseconds=999999))
    return "second", zone, fmt_utc(value), fmt_utc(value.replace(microsecond=999999))


def local_candidate_dates(earliest_utc: str, latest_utc: str) -> list[str]:
    out = set()
    for bound in (earliest_utc, latest_utc):
        instant = parse_utc(bound)
        for hours in US_LOCAL_OFFSETS_HOURS:
            out.add((instant + _dt.timedelta(hours=hours)).date().isoformat())
    return sorted(out)


def equivalent_original(url: str, game_id: str) -> bool:
    """The contract's original-URL equivalence for one requested ESPN game page."""
    try:
        parts = urllib.parse.urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    if parts.scheme not in ("http", "https") or (parts.hostname or "").lower() != "www.espn.com":
        return False
    if port not in (None, 80, 443) or parts.query or parts.fragment or parts.username or parts.password:
        return False
    match = GAME_PATH_RE.match(parts.path)
    return bool(match) and match.group(1) == game_id


def replay_parts(url: str) -> tuple[str, str] | None:
    """(timestamp, original) of a https://web.archive.org/web/<ts>id_/<original> replay URL, else None."""
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return None
    if parts.scheme != "https" or (parts.hostname or "").lower() != "web.archive.org" or parts.port not in (None, 443):
        return None
    if parts.query or parts.fragment or parts.username or parts.password:
        return None
    match = REPLAY_PATH_RE.match(parts.path)
    return (match.group(1), match.group(2)) if match else None


def replay_url(ts: str, original: str) -> str:
    return f"https://web.archive.org/web/{ts}id_/{original}"


def metadata_url(candidate: str, ts: str) -> str:
    return "https://archive.org/wayback/available?" + urllib.parse.urlencode({"url": candidate, "timestamp": ts})


def link_original(link: str | None) -> str | None:
    """The rel="original" URL of a Memento Link header."""
    if not link:
        return None
    for match in re.finditer(r'<([^>]*)>\s*;\s*([^,<]*)', link):
        if re.search(r'\brel\s*=\s*"?original"?', match.group(2)):
            return match.group(1)
    return None


def header(headers: list[list[Any]], name: str) -> str | None:
    values = [v for k, v in headers if str(k).lower() == name.lower()]
    if not values:
        return None
    value = values[0]
    return value if isinstance(value, str) else None


# --------------------------------------------------------------------------------------------- contract and parents

def load_contract(path: Path) -> tuple[dict[str, Any], str]:
    raw = Path(path).read_bytes()
    try:
        contract = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BuildRefused("CONTRACT_INVALID", str(exc)) from exc
    if contract.get("schema_version") != CONTRACT_SCHEMA or not str(contract.get("contract_id", "")).startswith(
            CONTRACT_ID_PREFIX):
        raise BuildRefused("CONTRACT_SCHEMA_UNKNOWN", f"{contract.get('schema_version')} {contract.get('contract_id')}")
    if contract.get("population_id") != POPULATION:
        raise BuildRefused("CONTRACT_SCHEMA_UNKNOWN", "population")
    if contract.get("row_labels") != AUTHORITY:
        raise BuildRefused("AUTHORITY_LABELS_INVALID", "row labels differ from the evidence-only labels")
    if contract.get("authority", {}).get("pit_admission") != AUTHORITY["pit_admission"]:
        raise BuildRefused("FORGED_PIT_AUTHORITY", "the contract claims a PIT admission authority")
    if tuple(contract.get("extraction", {}).get("fields", {}).get("order") or ()) != FIELDS:
        raise BuildRefused("CONTRACT_SCHEMA_UNKNOWN", "field order")
    limits = contract["acquisition"]["limits"]
    if (limits["metadata_requests_per_key"], limits["replay_requests_per_key"], limits["max_concurrency"]) != (2, 2, 1) \
            or limits["total_requests"] > 128 or limits["min_seconds_between_request_starts"] < 1.0:
        raise BuildRefused("ACQUISITION_POLICY_INVALID", "limits exceed the TP41-A01 section 2 grant")
    hosts = contract["acquisition"]["hosts"]
    if (hosts["metadata"]["host"], hosts["replay"]["host"]) != ALLOWED_HOSTS:
        raise BuildRefused("ACQUISITION_POLICY_INVALID", "hosts differ from the granted archive hosts")
    return contract, sha256_bytes(raw)


def policy_id(contract: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes({"acquisition": contract["acquisition"],
                                              "tranche_sha256": contract["scope"]["tranche_sha256"]}))


def _manifest_for(database: Path) -> Path:
    db = Path(database).resolve()
    population_root = db.parent.parent.parent
    return population_root.parent.parent / "manifests" / population_root.name / "sha256" / db.parent.name / \
        "run_manifest.json"


def verify_source_database(contract: dict[str, Any], database: Path) -> dict[str, Any]:
    """The accepted parent source-time database: location, run manifest identity document, bytes and contract."""
    db = Path(database)
    binding = contract["parent_binding"]["source_time"]
    if not db.is_file() or db.name != SOURCE_DB_FILE or db.resolve().parent.parent.name != "sha256":
        raise BuildRefused("PARENT_LOCATION_INVALID", f"{db}")
    identity = db.resolve().parent.name
    manifest = _manifest_for(db)
    if not manifest.is_file():
        raise BuildRefused("PARENT_MANIFEST_MISSING", str(manifest))
    document = json.loads(manifest.read_text(encoding="utf-8"))
    identity_document = document.get("identity_document") or {}
    if sha256_bytes(canonical_json_bytes(identity_document)) != identity or document.get("identity") != identity:
        raise BuildRefused("PARENT_IDENTITY_MISMATCH", "parent manifest identity document")
    if (identity_document.get("schema"), identity_document.get("db_schema_version")) != (
            SOURCE_DATABASE_DOCUMENT_SCHEMA, SOURCE_DB_SCHEMA):
        raise BuildRefused("PARENT_SCHEMA_UNSUPPORTED", "parent is not a source-time database")
    actual = sha256_file(db)
    if actual != (identity_document.get("outputs") or {}).get(SOURCE_DB_FILE):
        raise BuildRefused("PARENT_TAMPERED", "parent database bytes differ from its manifest")
    if (identity, actual, identity_document.get("content_identity"), identity_document.get("contract_sha256")) != (
            binding["database_identity"], binding["sqlite_sha256"], binding["content_identity"],
            binding["contract_sha256"]):
        raise BuildRefused("WRONG_PARENT", "the source-time database is not the bound accepted parent")
    return {"database_identity": identity, "sqlite_sha256": actual,
            "content_identity": identity_document["content_identity"],
            "contract_sha256": identity_document["contract_sha256"]}


def verify_tranche(contract: dict[str, Any], tranche_path: Path) -> list[dict[str, Any]]:
    raw = Path(tranche_path).read_bytes()
    scope = contract["scope"]
    if sha256_bytes(raw) != scope["tranche_sha256"]:
        raise BuildRefused("TRANCHE_MISMATCH", "tranche bytes differ from the contract binding")
    tranche = json.loads(raw.decode("utf-8"))
    rows = tranche.get("selected") or []
    keys = [r.get("contest_key") for r in rows]
    if len(rows) != scope["tranche_count"] or tranche.get("count") != scope["tranche_count"] or \
            len(set(keys)) != len(keys):
        raise BuildRefused("TRANCHE_KEYS_INVALID", "duplicate, missing or extra tranche keys")
    declared = scope["keys"]
    for row, spec in zip(rows, declared):
        if (row["contest_key"], row["selection_role"], row["stratum"], row["candidate_espn_url"],
                row["metadata_probe_timestamp"]) != (spec["contest_key"], spec["selection_role"], spec["stratum"],
                                                     spec["candidate_url"], spec["probe_1_timestamp"]):
            raise BuildRefused("TRANCHE_KEYS_INVALID", f"{row['contest_key']} differs from the contract scope")
        if row["season"] != scope["season"]:
            raise BuildRefused("OUT_OF_TRANCHE_SEASON", row["contest_key"])
        game = urllib.parse.urlsplit(row["candidate_espn_url"]).path.rsplit("/", 1)[-1]
        if game != spec["game_id_literal"] or not equivalent_original(row["candidate_espn_url"], game):
            raise BuildRefused("TRANCHE_KEYS_INVALID", f"{row['contest_key']} candidate URL")
    controls = [r["contest_key"] for r in rows if r["selection_role"] == "SEPARATE_PREQUALIFIED_ROUTE_CONTROL"]
    if controls != [scope["control_contest_key"]]:
        raise BuildRefused("TRANCHE_KEYS_INVALID", "control key")
    return rows


def verify_source_bindings(contract: dict[str, Any], path: Path, parent: dict[str, Any], tranche_path: Path,
                           database: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    if sha256_bytes(raw) != contract["parent_binding"]["source_bindings"]["sha256"]:
        raise BuildRefused("SOURCE_BINDINGS_MISMATCH", "binding document bytes differ from the contract")
    doc = json.loads(raw.decode("utf-8"))
    st = doc.get("source_time_database") or {}
    if (st.get("sha256"), st.get("identity")) != (parent["sqlite_sha256"], parent["database_identity"]) or \
            Path(st.get("path", "")).resolve() != Path(database).resolve():
        raise BuildRefused("SOURCE_BINDINGS_MISMATCH", "bindings name another source-time database")
    if (doc.get("tranche") or {}).get("sha256") != contract["scope"]["tranche_sha256"] or \
            (doc.get("tranche") or {}).get("count") != contract["scope"]["tranche_count"] or \
            Path((doc.get("tranche") or {}).get("path", "")).resolve() != Path(tranche_path).resolve():
        raise BuildRefused("SOURCE_BINDINGS_MISMATCH", "bindings name another tranche")
    if (doc.get("control") or {}).get("sha256") != contract["parent_binding"]["route_control"]["sha256"]:
        raise BuildRefused("SOURCE_BINDINGS_MISMATCH", "bindings name another route control")
    return {"path": str(path), "sha256": sha256_bytes(raw), "control_path": doc["control"]["path"]}


def read_parent(database: Path, rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Accepted parent values for every tranche key (contest record plus the single parent value of each field)."""
    conn = sqlite3.connect(Path(database).resolve().as_uri() + "?mode=ro", uri=True)
    out: dict[str, dict[str, Any]] = {}
    try:
        for row in rows:
            found = conn.execute("SELECT record, assertions FROM contests WHERE contest_key = ?",
                                 (row["contest_key"],)).fetchone()
            if found is None:
                raise BuildRefused("TRANCHE_PARENT_MISMATCH", f"{row['contest_key']} is not a source-time contest")
            record = json.loads(found[0])
            values: dict[str, set] = {}
            for line in zlib.decompress(found[1]).decode("utf-8").splitlines():
                item = json.loads(line)
                values.setdefault(item["field"], set()).add(json.dumps(item["parent_value"], sort_keys=True))
            if any(len(v) != 1 for v in values.values()) or set(values) != set(FIELDS):
                raise BuildRefused("TRANCHE_PARENT_MISMATCH", f"{row['contest_key']} parent values are not single")
            parent_values = {f: json.loads(next(iter(values[f]))) for f in FIELDS}
            if (record["season"], record["contest_date"], record["a_key"], record["b_key"],
                    record["cfbd_game_id"]["value"], parent_values["a_points"], parent_values["b_points"]) != (
                    row["season"], row["contest_date"], row["a_key"], row["b_key"], row["cfbd_game_id"]["value"],
                    row["a_points"], row["b_points"]):
                raise BuildRefused("TRANCHE_PARENT_MISMATCH", f"{row['contest_key']} differs from the parent")
            if record["a_cfbd_team_id"].get("namespace") != "CFBD_TEAM_ID" or \
                    record["b_cfbd_team_id"].get("namespace") != "CFBD_TEAM_ID":
                raise BuildRefused("TRANCHE_PARENT_MISMATCH", f"{row['contest_key']} team id namespace")
            out[row["contest_key"]] = {"record": record, "values": parent_values}
    finally:
        conn.close()
    return out


def verify_control(contract: dict[str, Any], control_path: Path) -> dict[str, Any]:
    """The manager's retained route control: qualification document, raw receipt and raw payload bytes."""
    spec = contract["parent_binding"]["route_control"]
    route_raw = Path(control_path).read_bytes()
    if sha256_bytes(route_raw) != spec["sha256"]:
        raise BuildRefused("CONTROL_MISMATCH", "route qualification bytes")
    route = json.loads(route_raw.decode("utf-8"))
    base = Path(control_path).parent
    receipt_path = base / Path(*spec["raw_receipt_document"].split("/"))
    payload_path = base / Path(*spec["raw_payload"].split("/"))
    receipt_raw, payload = receipt_path.read_bytes(), payload_path.read_bytes()
    if sha256_bytes(receipt_raw) != spec["raw_receipt_sha256"] or sha256_bytes(payload) != spec["raw_payload_sha256"]:
        raise BuildRefused("CONTROL_MISMATCH", "control receipt or payload bytes")
    if (route["contest_key"], route["archive_capture_utc"], route["conservative_upper_bound"]) != (
            spec["contest_key"], spec["archive_capture_utc"], spec["conservative_upper_bound"]):
        raise BuildRefused("CONTROL_MISMATCH", "control capture identity")
    return {"route_raw": route_raw, "receipt_raw": receipt_raw, "payload": payload, "route": route,
            "receipt": json.loads(receipt_raw.decode("utf-8"))}


# --------------------------------------------------------------------------------------------- raw store

def raw_rel(sha: str) -> str:
    return f"raw/sha256/{sha}"


def store_raw(output_root: Path, data: bytes) -> str:
    sha = sha256_bytes(data)
    path = Path(output_root) / "raw" / "sha256" / sha
    if path.exists():
        if sha256_file(path) != sha:
            raise BuildRefused("REFUSED_IMMUTABLE_COLLISION", f"raw store {sha} holds different bytes")
        return sha
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".tmp-{sha[:16]}-{os.getpid()}-{time.time_ns()}")
    with temporary.open("xb") as handle:
        handle.write(data)
    if sha256_file(temporary) != sha:
        raise BuildRefused("WRITE_VERIFY_FAILED", sha)
    os.rename(temporary, path)
    return sha


def read_raw(output_root: Path, sha: str) -> bytes:
    path = Path(output_root) / "raw" / "sha256" / sha
    if not path.is_file():
        raise BuildRefused("RAW_MISSING", sha)
    data = path.read_bytes()
    if sha256_bytes(data) != sha:
        raise BuildRefused("RAW_ALTERED", sha)
    return data


# --------------------------------------------------------------------------------------------- capture stage

class Response:
    def __init__(self, status: int | None, reason: str | None, headers: list[list[str]], body: bytes,
                 error: str | None = None) -> None:
        self.status, self.reason, self.headers, self.body, self.error = status, reason, headers, body, error


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401 - urllib hook
        return None


def urllib_transport(url: str, headers: dict[str, str], timeout: float) -> Response:
    """One HTTP GET without proxies, redirects, cookies or credentials. A 3xx/4xx/5xx is a response, not an error."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with opener.open(request, timeout=timeout) as response:
            return Response(response.status, response.reason, [[k, v] for k, v in response.headers.items()],
                            response.read())
    except urllib.error.HTTPError as error:
        body = error.read() if error.fp is not None else b""
        return Response(error.code, str(error.reason), [[k, v] for k, v in (error.headers or {}).items()], body)
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as error:
        return Response(None, None, [], b"", f"{type(error).__name__}: {error}")


def install_network_audit(log_path: Path) -> None:
    """Refuse name resolution for any host but the two archive hosts; log every resolution/connection event."""
    import socket  # noqa: F401,PLC0415 - make sure the module is imported before the hook

    def hook(event: str, args: tuple) -> None:
        if event not in ("socket.getaddrinfo", "socket.connect", "socket.gethostbyname"):
            return
        target = args[0] if event != "socket.connect" else (args[1] if len(args) > 1 else None)
        allowed = event == "socket.connect" or str(target).lower() in ALLOWED_HOSTS
        with open(log_path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"event": event, "target": repr(target), "allowed": allowed, "at": utc_now()})
                         + "\n")
        if not allowed:
            raise PermissionError(f"archive capture network audit: {event} to {target!r} refused")
    sys.addaudithook(hook)


def redact(headers: list[list[str]], names: Sequence[str]) -> list[list[Any]]:
    lowered = {n.lower() for n in names}
    return [[k, {"redacted": True, "sha256": sha256_bytes(str(v).encode("utf-8"))} if k.lower() in lowered else v]
            for k, v in headers]


def retry_after(headers: list[list[Any]]) -> int | None:
    value = header(headers, "Retry-After")
    if value is None:
        return None
    if value.strip().isdigit():
        return int(value.strip())
    try:
        return max(0, int((rfc1123(value) - _dt.datetime.now(UTC)).total_seconds()) + 1)
    except (ValueError, TypeError):
        return None


def metadata_answer(body: bytes, game_id: str) -> dict[str, Any]:
    """The availability answer: closest {timestamp, status, original} when usable, else a reason."""
    try:
        doc = json.loads(body.decode("utf-8"))
        closest = ((doc.get("archived_snapshots") or {}).get("closest")) or None
    except (UnicodeDecodeError, ValueError, AttributeError):
        return {"usable": False, "reason": "METADATA_ANSWER_NOT_JSON"}
    if not closest:
        return {"usable": False, "reason": "NO_CAPTURE_REPORTED"}
    ts, status = str(closest.get("timestamp") or ""), str(closest.get("status") or "")
    match = CLOSEST_URL_RE.match(str(closest.get("url") or ""))
    if closest.get("available") is not True or not TS14_RE.match(ts) or not match or match.group(1) != ts:
        return {"usable": False, "reason": "CLOSEST_MALFORMED", "timestamp": ts or None, "status": status or None}
    original = match.group(2)
    if not equivalent_original(original, game_id):
        return {"usable": False, "reason": "CLOSEST_FOR_ANOTHER_URL", "timestamp": ts, "status": status}
    if status not in USABLE_CLOSEST_STATUS:
        return {"usable": False, "reason": f"CLOSEST_STATUS_{status or 'ABSENT'}", "timestamp": ts, "status": status}
    return {"usable": True, "timestamp": ts, "status": status, "original": original}


def transient(record: dict[str, Any]) -> bool:
    return record["outcome"] in ("NETWORK_ERROR", "INTERRUPTED_UNKNOWN") or record["http_status"] in RETRYABLE_STATUS


def retry_allowed(record: dict[str, Any], cap: int) -> bool:
    return transient(record) and (record.get("retry_after_seconds") is None or record["retry_after_seconds"] <= cap)


def plan_next(key: dict[str, Any], history: list[dict[str, Any]], contract: dict[str, Any],
              read_body: Callable[[dict[str, Any]], bytes]) -> tuple[str, str, str] | None:
    """The next request for one key from its recorded history (pure and deterministic): (kind, purpose, url)."""
    cap = contract["acquisition"]["limits"]["retry_after_cap_seconds"]
    game, candidate = key["game_id_literal"], key["candidate_url"]
    probe1 = key["probe_1_timestamp"]
    day = _dt.date(int(probe1[:4]), int(probe1[4:6]), int(probe1[6:8])) + _dt.timedelta(days=3)
    probe2 = day.strftime("%Y%m%d") + "235959"
    metas = [r for r in history if r["kind"] == "METADATA"]
    replays = [r for r in history if r["kind"] == "REPLAY"]
    if not metas:
        return "METADATA", "PROBE_1", metadata_url(candidate, probe1)
    first = metas[0]
    answer = None
    if transient(first):
        if len(metas) < 2:
            return ("METADATA", "RETRY", metadata_url(candidate, probe1)) if retry_allowed(first, cap) else None
        if metas[1]["http_status"] == 200:
            answer = metadata_answer(read_body(metas[1]), game)
        meta_used = 2
    else:
        if first["http_status"] != 200:
            return None
        answer = metadata_answer(read_body(first), game)
        meta_used = 1
        if not answer["usable"]:
            if len(metas) < 2:
                return "METADATA", "PROBE_2", metadata_url(candidate, probe2)
            answer = metadata_answer(read_body(metas[1]), game) if metas[1]["http_status"] == 200 else None
            meta_used = 2
    if not answer or not answer["usable"]:
        return None
    if not replays:
        return "REPLAY", "CAPTURE_1", replay_url(answer["timestamp"], answer["original"])
    first_replay = replays[0]
    if transient(first_replay):
        if len(replays) < 2 and retry_allowed(first_replay, cap):
            return "REPLAY", "RETRY", first_replay["url"]
        return None
    if first_replay["http_status"] in REDIRECT_STATUS:
        location = first_replay["location"] or ""
        target = replay_parts(urllib.parse.urljoin(first_replay["url"], location)) if location else None
        if len(replays) < 2 and target and equivalent_original(target[1], game):
            return "REPLAY", "REDIRECT_HOP", replay_url(target[0], target[1])
        return None
    if first_replay["http_status"] == 200 and meta_used == 1:
        captured = replay_parts(first_replay["url"])
        if captured and ts14_instant(captured[0]) < ts14_instant(probe1):
            if len(metas) < 2:
                return "METADATA", "PROBE_2", metadata_url(candidate, probe2)
            second = metadata_answer(read_body(metas[1]), game) if metas[1]["http_status"] == 200 else None
            if second and second["usable"] and second["timestamp"] != captured[0] and len(replays) < 2:
                return "REPLAY", "CAPTURE_2", replay_url(second["timestamp"], second["original"])
    return None


def acquisition_outcome(key: dict[str, Any], history: list[dict[str, Any]], exhausted: bool) -> str:
    if key["selection_role"] == "SEPARATE_PREQUALIFIED_ROUTE_CONTROL":
        return "CONTROL_REUSED"
    replays = [r for r in history if r["kind"] == "REPLAY"]
    metas = [r for r in history if r["kind"] == "METADATA"]
    if any(r["http_status"] == 200 for r in replays):
        return "CAPTURED"
    if not metas:
        return "NOT_ATTEMPTED_TOTAL_BUDGET_EXHAUSTED" if exhausted else "NOT_ATTEMPTED"
    if replays:
        last = replays[-1]
        if last["http_status"] in REDIRECT_STATUS:
            return "REDIRECT_REFUSED"
        return "REPLAY_REQUEST_FAILED"
    if all(m["http_status"] != 200 for m in metas):
        return "METADATA_REQUEST_FAILED"
    if exhausted:
        return "NOT_ATTEMPTED_TOTAL_BUDGET_EXHAUSTED"
    return "NO_ARCHIVE_CAPTURE_REPORTED"


class Journal:
    def __init__(self, directory: Path, header_doc: dict[str, Any]) -> None:
        self.dir = Path(directory)
        self.path = self.dir / "journal.jsonl"
        self.dir.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            lines = self.lines()
            if not lines or lines[0].get("type") != "HEADER" or lines[0].get("header") != header_doc:
                raise BuildRefused("REFUSED_STALE_JOURNAL", "the journal binds a different acquisition policy")
        else:
            self.append({"type": "HEADER", "header": header_doc})

    def lines(self) -> list[dict[str, Any]]:
        text = self.path.read_text(encoding="utf-8")
        if text and not text.endswith("\n"):
            raise BuildRefused("JOURNAL_TORN", "the journal's last line is incomplete")
        return [json.loads(line) for line in text.splitlines() if line]

    def append(self, row: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def journal_history(lines: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str], str | None]:
    """Request records (INTENT without RESULT become INTERRUPTED_UNKNOWN), key outcomes and the finalized id."""
    intents: dict[int, dict[str, Any]] = {}
    results: dict[int, dict[str, Any]] = {}
    outcomes: dict[str, str] = {}
    final = None
    for row in lines[1:]:
        kind = row.get("type")
        if kind == "INTENT":
            if row["seq"] in intents:
                raise BuildRefused("JOURNAL_INVALID", f"duplicate intent {row['seq']}")
            intents[row["seq"]] = row
        elif kind == "RESULT":
            if row["seq"] not in intents or row["seq"] in results:
                raise BuildRefused("JOURNAL_INVALID", f"result without a single intent {row['seq']}")
            results[row["seq"]] = row["request"]
        elif kind == "KEY_DONE":
            outcomes[row["contest_key"]] = row["acquisition_outcome"]
        elif kind == "FINALIZED":
            final = row["acquisition_identity"]
        else:
            raise BuildRefused("JOURNAL_INVALID", f"unknown line type {kind}")
    if sorted(intents) != list(range(1, len(intents) + 1)):
        raise BuildRefused("JOURNAL_INVALID", "intent sequence is not contiguous")
    records = []
    for seq in sorted(intents):
        if seq in results:
            records.append(results[seq])
        else:
            intent = intents[seq]
            records.append({"seq": seq, "contest_key": intent["contest_key"], "kind": intent["kind"],
                            "purpose": intent["purpose"], "url": intent["url"], "started_utc": intent["started_utc"],
                            "ended_utc": None, "outcome": "INTERRUPTED_UNKNOWN", "http_status": None, "reason": None,
                            "headers": [], "location": None, "body_sha256": None, "body_bytes": None,
                            "retry_after_seconds": None, "slept_seconds": "0.000", "error": "INTENT_WITHOUT_RESULT"})
    return records, outcomes, final


def capture(contract: dict[str, Any], rows: list[dict[str, Any]], output_root: Path, control: dict[str, Any],
            *, transport: Callable[[str, dict[str, str], float], Response] | None = None,
            sleep: Callable[[float], None] = time.sleep, monotonic: Callable[[], float] = time.monotonic,
            now: Callable[[], str] = utc_now,
            audit: bool = True) -> dict[str, Any]:
    """Run (or resume) the bounded acquisition and finalize the acquisition document."""
    output_root = Path(output_root)

    def read_body(record: dict[str, Any]) -> bytes:
        return read_raw(output_root, record["body_sha256"])
    acquisition = contract["acquisition"]
    limits = acquisition["limits"]
    pid = policy_id(contract)
    header_doc = {"schema": JOURNAL_SCHEMA, "policy_id": pid, "tranche_sha256": contract["scope"]["tranche_sha256"],
                  "contract_id": contract["contract_id"]}
    existing = sorted((output_root / "acquisition" / "sha256").glob("*/acquisition.json")) \
        if (output_root / "acquisition" / "sha256").is_dir() else []
    for path in existing:
        doc = load_acquisition(path, output_root)
        if doc["policy_id"] == pid:
            return {"state": "ALREADY_FINALIZED", "acquisition_identity": path.parent.name, "path": str(path),
                    "new_requests": 0}
    journal = Journal(output_root / "acquisition" / "journal" / pid, header_doc)
    records, outcomes, final = journal_history(journal.lines())
    if final:
        raise BuildRefused("JOURNAL_INVALID", "the journal is finalized but its document is missing")
    if transport is None:
        transport = urllib_transport
        if audit:
            install_network_audit(journal.dir / "network_audit.jsonl")
    for sha in [r["body_sha256"] for r in records if r.get("body_sha256")]:
        read_raw(output_root, sha)
    for data in (control["payload"], control["receipt_raw"], control["route_raw"]):
        store_raw(output_root, data)
    keys = {spec["contest_key"]: spec for spec in contract["scope"]["keys"]}
    headers = dict(acquisition["request_headers"])
    new_requests = 0
    last_start = None
    exhausted = False
    for row in rows:
        key = keys[row["contest_key"]]
        if key["contest_key"] in outcomes:
            continue
        if key["selection_role"] == "SEPARATE_PREQUALIFIED_ROUTE_CONTROL":
            journal.append({"type": "KEY_DONE", "contest_key": key["contest_key"],
                            "acquisition_outcome": "CONTROL_REUSED"})
            outcomes[key["contest_key"]] = "CONTROL_REUSED"
            continue
        while True:
            history = [r for r in records if r["contest_key"] == key["contest_key"]]
            step = plan_next(key, history, contract, read_body)
            if step is None:
                break
            kind, purpose, url = step
            if sum(1 for r in history if r["kind"] == kind) >= limits[
                    "metadata_requests_per_key" if kind == "METADATA" else "replay_requests_per_key"]:
                break
            if len(records) >= limits["total_requests"]:
                exhausted = True
                break
            host = urllib.parse.urlsplit(url).hostname
            if host not in ALLOWED_HOSTS or (kind == "METADATA") != (host == "archive.org"):
                raise BuildRefused("ACQUISITION_HOST_REFUSED", url)
            slept = 0.0
            previous = history[-1] if history else None
            if previous and purpose == "RETRY" and previous.get("retry_after_seconds"):
                slept += previous["retry_after_seconds"]
                sleep(previous["retry_after_seconds"])
            if last_start is not None:
                wait = limits["min_seconds_between_request_starts"] - (monotonic() - last_start)
                if wait > 0:
                    sleep(wait)
                    slept += wait
            seq = len(records) + 1
            last_start = monotonic()
            started = now()
            journal.append({"type": "INTENT", "seq": seq, "contest_key": key["contest_key"], "kind": kind,
                            "purpose": purpose, "url": url, "started_utc": started})
            response = transport(url, headers, float(limits["timeout_seconds"]))
            ended = now()
            new_requests += 1
            body_sha = store_raw(output_root, response.body) if response.status is not None else None
            response_headers = redact(response.headers, acquisition["redacted_response_headers"])
            record = {"seq": seq, "contest_key": key["contest_key"], "kind": kind, "purpose": purpose, "url": url,
                      "started_utc": started, "ended_utc": ended,
                      "outcome": "RESPONSE" if response.status is not None else "NETWORK_ERROR",
                      "http_status": response.status, "reason": response.reason, "headers": response_headers,
                      "location": header(response_headers, "Location"), "body_sha256": body_sha,
                      "body_bytes": len(response.body) if response.status is not None else None,
                      "retry_after_seconds": retry_after(response_headers), "slept_seconds": f"{slept:.3f}",
                      "error": response.error}
            journal.append({"type": "RESULT", "seq": seq, "request": record})
            records.append(record)
        history = [r for r in records if r["contest_key"] == key["contest_key"]]
        if exhausted and plan_next(key, history, contract, read_body) is not None:
            outcome = "NOT_ATTEMPTED_TOTAL_BUDGET_EXHAUSTED" if not history else acquisition_outcome(key, history, True)
        else:
            outcome = acquisition_outcome(key, history, False)
        journal.append({"type": "KEY_DONE", "contest_key": key["contest_key"], "acquisition_outcome": outcome})
        outcomes[key["contest_key"]] = outcome
    document = {"schema": ACQUISITION_SCHEMA, "policy_id": pid, "contract_id": contract["contract_id"],
                "tranche_sha256": contract["scope"]["tranche_sha256"],
                "keys": [k["contest_key"] for k in contract["scope"]["keys"]],
                "control": {"contest_key": contract["scope"]["control_contest_key"], "requests": 0,
                            "route_qualification_sha256": sha256_bytes(control["route_raw"]),
                            "raw_receipt_sha256": sha256_bytes(control["receipt_raw"]),
                            "payload_sha256": sha256_bytes(control["payload"])},
                "requests": records, "outcomes": {k["contest_key"]: outcomes[k["contest_key"]]
                                                  for k in contract["scope"]["keys"]},
                "totals": {"requests": len(records),
                           "metadata": sum(1 for r in records if r["kind"] == "METADATA"),
                           "replay": sum(1 for r in records if r["kind"] == "REPLAY"),
                           "retries": sum(1 for r in records if r["purpose"] == "RETRY"),
                           "redirect_hops": sum(1 for r in records if r["purpose"] == "REDIRECT_HOP"),
                           "network_errors": sum(1 for r in records if r["outcome"] != "RESPONSE"),
                           "limit": limits["total_requests"]},
                "journal": f"acquisition/journal/{pid}/journal.jsonl"}
    data = canonical_json_bytes(document)
    identity = sha256_bytes(data)
    target = output_root / "acquisition" / "sha256" / identity / "acquisition.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != data:
            raise BuildRefused("REFUSED_IMMUTABLE_COLLISION", str(target))
    else:
        with target.open("xb") as handle:
            handle.write(data)
    journal.append({"type": "FINALIZED", "acquisition_identity": identity})
    return {"state": "FINALIZED", "acquisition_identity": identity, "path": str(target), "new_requests": new_requests,
            "totals": document["totals"], "outcomes": document["outcomes"]}


def load_acquisition(path: Path, output_root: Path) -> dict[str, Any]:
    data = Path(path).read_bytes()
    if sha256_bytes(data) != Path(path).parent.name:
        raise BuildRefused("ACQUISITION_ALTERED", f"{path} does not hash to its identity")
    doc = json.loads(data.decode("utf-8"))
    if doc.get("schema") != ACQUISITION_SCHEMA:
        raise BuildRefused("ACQUISITION_SCHEMA_UNKNOWN", str(path))
    return doc


# --------------------------------------------------------------------------------------------- extraction

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr", "param"}


class GamePageParser(HTMLParser):
    """HTML tokenizer pass over one archived page that records only the main game element's witnesses and spans."""

    def __init__(self, text: str) -> None:
        super().__init__(convert_charrefs=False)
        self.text = text
        self.line_starts = [0]
        for index, char in enumerate(text):
            if char == "\n":
                self.line_starts.append(index + 1)
        self.stack: list[dict[str, Any]] = []
        self.nav: list[dict[str, Any]] = []
        self.info: list[dict[str, Any]] = []
        self.js: list[dict[str, Any]] = []
        self.witnesses: list[dict[str, Any]] = []
        self.in_script = False
        self.pending_text: dict[str, Any] | None = None

    def char_offset(self) -> int:
        line, col = self.getpos()
        return self.line_starts[line - 1] + col

    def _context(self, predicate) -> dict[str, Any] | None:
        for item in reversed(self.stack):
            if predicate(item):
                return item
        return None

    def _attr_span(self, start: int, name: str) -> tuple[int, int] | None:
        raw = self.get_starttag_text() or ""
        match = re.search(r"\s" + re.escape(name) + r"\s*=\s*(\"([^\"]*)\"|'([^']*)')", raw)
        if not match:
            return None
        group = 2 if match.group(2) is not None else 3
        return start + match.start(group), start + match.end(group)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        start = self.char_offset()
        values = dict(attrs)
        item = {"tag": tag, "attrs": values, "classes": set((values.get("class") or "").split()), "start": start}
        in_nav = bool(self.nav) and self.nav[-1].get("end") is None
        in_info = bool(self.info) and self.info[-1].get("end") is None
        if tag == "div" and values.get("id") == "custom-nav":
            span = self._attr_span(start, "data-id")
            item["role"] = "NAV"
            self.nav.append({"start": start, "end": None, "data_id": values.get("data-id"), "data_id_span": span})
            if span:
                self.witnesses.append({"witness": "NAV_GAME_ID", "span": span, "scope": "NAV"})
        elif tag == "div" and values.get("id") == "gamepackage-game-information":
            item["role"] = "INFO"
            self.info.append({"start": start, "end": None})
        elif in_nav and tag == "div" and {"team", "home"} <= item["classes"]:
            item["side"] = "HOME"
        elif in_nav and tag == "div" and {"team", "away"} <= item["classes"]:
            item["side"] = "AWAY"
        elif in_nav and tag == "a" and "team-name" in item["classes"]:
            team = self._context(lambda i: "side" in i)
            if team is not None and not team.get("href_seen"):
                team["href_seen"] = True
                span = self._attr_span(start, "href")
                if span:
                    self.witnesses.append({"witness": f"{team['side']}_TEAM_HREF", "span": span, "scope": "NAV"})
        elif in_nav and tag == "div" and "score" in item["classes"]:
            team = self._context(lambda i: "side" in i)
            if team is not None and not team.get("score_seen"):
                team["score_seen"] = True
                self.pending_text = {"witness": f"{team['side']}_SCORE", "scope": "NAV", "tag": "div"}
        elif in_nav and tag == "span" and "status-detail" in item["classes"]:
            self.pending_text = {"witness": "STATUS_DETAIL", "scope": "NAV", "tag": "span"}
        elif in_info and tag == "span" and values.get("data-behavior") == "date_time" and \
                self._context(lambda i: "game-date-time" in i["classes"]) is not None:
            span = self._attr_span(start, "data-date")
            if span:
                self.witnesses.append({"witness": "INFO_EVENT_DATE", "span": span, "scope": "INFO"})
        if tag == "script":
            self.in_script = True
        if tag not in VOID:
            self.stack.append(item)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1]["tag"] == tag:
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        position = self.char_offset()
        end = self.text.find(">", position) + 1
        if tag == "script":
            self.in_script = False
        if self.pending_text and self.pending_text["tag"] == tag:
            self.pending_text = None
        if not any(item["tag"] == tag for item in self.stack):
            return
        while self.stack:
            item = self.stack.pop()
            if item.get("role") == "NAV" and self.nav and self.nav[-1]["end"] is None:
                self.nav[-1]["end"] = end
            if item.get("role") == "INFO" and self.info and self.info[-1]["end"] is None:
                self.info[-1]["end"] = end
            if item["tag"] == tag:
                break

    def handle_data(self, data: str) -> None:
        start = self.char_offset()
        if self.in_script:
            for match in JS_ASSIGN_RE.finditer(data):
                names = {"gameId": "JS_GAME_ID", "status": "JS_STATUS", "homeTeamId": "JS_HOME_TEAM_ID",
                         "awayTeamId": "JS_AWAY_TEAM_ID", "timestamp": "JS_EVENT_TIMESTAMP"}
                self.js.append({"start": start + match.start(), "end": start + match.end()})
                self.witnesses.append({"witness": names[match.group(1)],
                                       "span": (start + match.start(2), start + match.end(2)), "scope": "JS"})
            return
        if self.pending_text is not None:
            stripped = data.strip()
            if stripped:
                lead = len(data) - len(data.lstrip())
                self.witnesses.append({"witness": self.pending_text["witness"],
                                       "span": (start + lead, start + lead + len(stripped)),
                                       "scope": self.pending_text["scope"]})
                self.pending_text = None


def byte_offsets(text: str) -> Callable[[int], int]:
    starts = [0]
    acc = 0
    for line in text.splitlines(keepends=True):
        acc += len(line.encode("utf-8"))
        starts.append(acc)
    char_starts = [0]
    for line in text.splitlines(keepends=True):
        char_starts.append(char_starts[-1] + len(line))

    def convert(index: int) -> int:
        lo, hi = 0, len(char_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if char_starts[mid] <= index:
                lo = mid
            else:
                hi = mid - 1
        return starts[lo] + len(text[char_starts[lo]:index].encode("utf-8"))
    return convert


def extract(payload: bytes) -> dict[str, Any]:
    """Witnesses of the main game element with byte spans; the scope spans; problems found while reading."""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return {"problems": ["BODY_NOT_UTF8"], "witnesses": [], "scopes": []}
    parser = GamePageParser(text)
    parser.feed(text)
    parser.close()
    to_byte = byte_offsets(text)
    scopes = []
    for nav in parser.nav:
        if nav["end"]:
            scopes.append({"kind": "NAV", "span": [to_byte(nav["start"]), to_byte(nav["end"])]})
    for info in parser.info:
        if info["end"]:
            scopes.append({"kind": "INFO", "span": [to_byte(info["start"]), to_byte(info["end"])]})
    for js in parser.js:
        scopes.append({"kind": "JS", "span": [to_byte(js["start"]), to_byte(js["end"])]})
    witnesses = []
    for w in parser.witnesses:
        start, end = to_byte(w["span"][0]), to_byte(w["span"][1])
        witnesses.append({"witness": w["witness"], "span": [start, end], "literal": payload[start:end].decode("utf-8"),
                          "scope": w["scope"]})
    problems = []
    if len([n for n in parser.nav if n["end"]]) == 0:
        problems.append("MAIN_GAME_ELEMENT_ABSENT")
    elif len(parser.nav) > 1:
        problems.append("MAIN_GAME_ELEMENT_DUPLICATED")
    return {"problems": problems, "witnesses": witnesses,
            "scopes": sorted(scopes, key=lambda s: (s["span"][0], s["kind"]))}


def witness_value(witness: str, literal: str) -> tuple[Any, str | None]:
    """(normalized value, problem) for one witness literal."""
    if witness in ("JS_GAME_ID",):
        return (literal, None) if DIGITS_RE.match(literal) else (None, "UNPARSEABLE")
    if witness == "NAV_GAME_ID":
        match = NAV_ID_RE.match(literal)
        return (match.group(1), None) if match else (None, "UNPARSEABLE")
    if witness in ("JS_HOME_TEAM_ID", "JS_AWAY_TEAM_ID"):
        return (literal, None) if DIGITS_RE.match(literal) else (None, "UNPARSEABLE")
    if witness in ("HOME_TEAM_HREF", "AWAY_TEAM_HREF"):
        match = TEAM_HREF_RE.match(literal)
        return (match.group(1), None) if match else (None, "UNPARSEABLE")
    if witness in ("HOME_SCORE", "AWAY_SCORE"):
        return (int(literal), None) if SCORE_RE.match(literal) else (None, "UNPARSEABLE")
    if witness in ("JS_EVENT_TIMESTAMP", "INFO_EVENT_DATE"):
        try:
            event_interval(literal)
        except ValueError:
            return None, "UNPARSEABLE"
        return literal, None
    if witness in ("JS_STATUS", "STATUS_DETAIL"):
        return literal, None
    return None, "UNKNOWN_WITNESS"


# --------------------------------------------------------------------------------------------- qualification

def receipt_checks(final_url: str, status: int | None, headers: list[list[Any]], payload: bytes,
                   game_id: str) -> tuple[dict[str, Any], list[str], dict[str, Any]]:
    """Receipt rules R1-R6; returns (checks, quarantine reasons, derived clock fields)."""
    reasons, derived = [], {}
    parts = replay_parts(final_url)
    checks = {"replay_url_valid": bool(parts) and equivalent_original(parts[1], game_id)}
    if not checks["replay_url_valid"]:
        reasons.append("REPLAY_URL_INVALID")
    memento = header(headers, "Memento-Datetime")
    origin = header(headers, "x-archive-orig-date")
    original = link_original(header(headers, "Link"))
    content_type = header(headers, "Content-Type") or ""
    derived.update(memento=memento, origin=origin, original=original, content_type=content_type,
                   wayback_timestamp=parts[0] if parts else None, archive_src=header(headers, "x-archive-src"))
    try:
        memento_at = rfc1123(memento)
        checks["memento_datetime_valid"] = True
    except (ValueError, TypeError):
        memento_at = None
        checks["memento_datetime_valid"] = False
        reasons.append("MEMENTO_DATETIME_ABSENT" if memento is None else "MEMENTO_DATETIME_MALFORMED")
    checks["memento_equals_url_timestamp"] = bool(memento_at and parts and
                                                  memento_at == ts14_instant(parts[0]))
    if memento_at and parts and not checks["memento_equals_url_timestamp"]:
        reasons.append("ARCHIVE_TIMESTAMPS_CONTRADICTORY")
    checks["link_original_equivalent"] = bool(original) and equivalent_original(original, game_id)
    if not checks["link_original_equivalent"]:
        reasons.append("MEMENTO_FOR_ANOTHER_URL")
    checks["html_200"] = status == 200 and content_type.lower().startswith("text/html")
    if not checks["html_200"]:
        reasons.append("NOT_AN_ARCHIVED_HTML_200")
    bound = end_of_second(memento_at) if memento_at else None
    checks["origin_date_consistent"] = True
    if origin is not None:
        try:
            origin_at = rfc1123(origin)
            if memento_at and origin_at > memento_at + _dt.timedelta(seconds=ORIGIN_DATE_TOLERANCE_SECONDS):
                checks["origin_date_consistent"] = False
                reasons.append("ORIGIN_DATE_CONTRADICTORY")
            elif memento_at and origin_at > memento_at:
                bound = end_of_second(origin_at)
        except (ValueError, TypeError):
            checks["origin_date_consistent"] = False
            reasons.append("ORIGIN_DATE_CONTRADICTORY")
    try:
        payload.decode("utf-8")
        checks["body_utf8"] = True
    except UnicodeDecodeError:
        checks["body_utf8"] = False
        reasons.append("BODY_NOT_UTF8")
    derived["bound"] = fmt_utc(bound) if bound else None
    return checks, reasons, derived


def qualify(contest_key: str, parent: dict[str, Any], game_id: str, payload: bytes, bound: str | None,
            receipt_reasons: list[str]) -> dict[str, Any]:
    """Field states, assertions and page facts of one archived version."""
    record, values = parent["record"], parent["values"]
    extraction = extract(payload) if "BODY_NOT_UTF8" not in receipt_reasons else \
        {"problems": ["BODY_NOT_UTF8"], "witnesses": [], "scopes": []}
    reasons = list(receipt_reasons) + [p for p in extraction["problems"] if p not in receipt_reasons]
    by: dict[str, list[dict[str, Any]]] = {}
    for w in extraction["witnesses"]:
        value, problem = witness_value(w["witness"], w["literal"])
        by.setdefault(w["witness"], []).append(dict(w, value=value, problem=problem))

    def single(name: str) -> tuple[Any, str]:
        items = by.get(name) or []
        if not items:
            return None, "ABSENT"
        if any(i["problem"] for i in items):
            return None, "UNPARSEABLE"
        distinct = {json.dumps(i["value"]) for i in items}
        return (items[0]["value"], "OK") if len(distinct) == 1 else (None, "CONTRADICTORY")
    nav_game, nav_state = single("NAV_GAME_ID")
    js_game, js_state = single("JS_GAME_ID")
    if "MAIN_GAME_ELEMENT_ABSENT" not in reasons and "MAIN_GAME_ELEMENT_DUPLICATED" not in reasons:
        if nav_state != "OK" or nav_game != game_id:
            reasons.append("WRONG_GAME_NODE")
        if js_state == "CONTRADICTORY":
            reasons.append("GAME_IDENTITY_CONTRADICTORY")
        elif js_state != "OK" or js_game != game_id:
            reasons.append("GAME_IDENTITY_MISMATCH")
    js_status, _s1 = single("JS_STATUS")
    detail, _s2 = single("STATUS_DETAIL")
    final = js_status == "post" and isinstance(detail, str) and bool(FINAL_RE.match(detail))
    if final and bound and parse_utc(bound) < earliest_event_instant(record["contest_date"]):
        reasons.append("IMPOSSIBLE_CHRONOLOGY")
    sides = {}
    for side in ("HOME", "AWAY"):
        js_id, js_st = single(f"JS_{side}_TEAM_ID")
        href_id, href_st = single(f"{side}_TEAM_HREF")
        sides[side] = {"js": js_id, "js_state": js_st, "href": href_id, "href_state": href_st,
                       "agree": js_st == "OK" and href_st == "OK" and js_id == href_id}
    page_participants = {s.lower(): {"espn_team_id": sides[s]["js"] if sides[s]["agree"] else None,
                                     "js_state": sides[s]["js_state"], "href_state": sides[s]["href_state"],
                                     "witnesses_agree": sides[s]["agree"],
                                     "witness_spans": sorted([w["witness"], list(w["span"])]
                                                             for n in (f"JS_{s}_TEAM_ID", f"{s}_TEAM_HREF")
                                                             for w in by.get(n) or [])}
                         for s in ("HOME", "AWAY")}
    a_id, b_id = record["a_cfbd_team_id"]["value"], record["b_cfbd_team_id"]["value"]
    orientation = {"a_side": None, "b_side": None, "rule": "page team block whose ESPN id equals the parent's a/b "
                                                           "CFBD id literal; pair must match exactly"}
    pair_ok = sides["HOME"]["agree"] and sides["AWAY"]["agree"] and \
        {sides["HOME"]["js"], sides["AWAY"]["js"]} == {a_id, b_id} and a_id != b_id
    if pair_ok:
        orientation["a_side"] = "HOME" if sides["HOME"]["js"] == a_id else "AWAY"
        orientation["b_side"] = "AWAY" if orientation["a_side"] == "HOME" else "HOME"
    qualified_capture = not reasons
    assertions: list[dict[str, Any]] = []
    states: dict[str, str] = {}

    def emit(field: str, witness_names: list[str], state: str, corroboration: str, parent_value: Any,
             comparator: Any) -> None:
        """One assertion per witness; ``value`` is that witness's own normalized value (participants namespaced)."""
        states[field] = state
        for name in sorted(witness_names):
            for item in by.get(name) or []:
                value = item["value"]
                if field in ("a_participant", "b_participant") and value is not None:
                    value = {"namespace": "ESPN_TEAM_ID", "value": value}
                assertions.append({"field": field, "witness": name, "witness_span": list(item["span"]),
                                   "literal": item["literal"], "value": value, "parent_value": parent_value,
                                   "parent_comparator": comparator,
                                   "corroboration": "UNPARSEABLE" if item["problem"] else corroboration,
                                   "field_state": state})
    states["season"] = "NOT_WITNESSED_IN_VERSION"
    # contest_date: both witnesses must be present, parse and agree
    date_names = ["JS_EVENT_TIMESTAMP", "INFO_EVENT_DATE"]
    present = [n for n in date_names if by.get(n)]
    if not present:
        states["contest_date"] = "NOT_WITNESSED_IN_VERSION"
    else:
        vals = [single(n) for n in present]
        if any(s == "UNPARSEABLE" for _v, s in vals):
            date_state, corr = "WITNESS_LITERAL_UNPARSEABLE", "UNPARSEABLE"
        elif any(s == "CONTRADICTORY" for _v, s in vals) or len({v for v, _s in vals}) != 1:
            date_state, corr = "CONTRADICTORY_WITHIN_VERSION", "CONTRADICTORY_WITHIN_VERSION"
        else:
            _p, _z, earliest, latest = event_interval(vals[0][0])
            agrees = record["contest_date"] in local_candidate_dates(earliest, latest)
            corr = "AGREES_WITH_PARENT" if agrees else "CONFLICTS_WITH_PARENT"
            date_state = ("QUALIFIED_AGREES_WITH_PARENT" if agrees else "CONFLICTS_WITH_PARENT") \
                if len(present) == len(date_names) else "INCOMPLETE_WITNESS_SET"
        if not qualified_capture:
            date_state = "CAPTURE_NOT_QUALIFIED"
        emit("contest_date", present, date_state, corr, values["contest_date"],
             {"basis": "US_LOCAL_CANDIDATE_DATES_-4H_-10H", "value": record["contest_date"]})
    # participants
    for field, parent_side in (("a_participant", "a"), ("b_participant", "b")):
        names_present = [n for n in ("JS_HOME_TEAM_ID", "HOME_TEAM_HREF", "JS_AWAY_TEAM_ID", "AWAY_TEAM_HREF")
                         if by.get(n)]
        if not names_present:
            states[field] = "NOT_WITNESSED_IN_VERSION"
            continue
        comparator = record[f"{parent_side}_cfbd_team_id"]
        if not pair_ok:
            states[field] = "CAPTURE_NOT_QUALIFIED" if not qualified_capture else (
                "CONTRADICTORY_WITHIN_VERSION" if not (sides["HOME"]["agree"] and sides["AWAY"]["agree"])
                else "ORIENTATION_UNRESOLVED")
            continue
        side = orientation[f"{parent_side}_side"]
        state = "QUALIFIED_AGREES_WITH_PARENT" if qualified_capture else "CAPTURE_NOT_QUALIFIED"
        emit(field, [f"JS_{side}_TEAM_ID", f"{side}_TEAM_HREF"], state, "AGREES_WITH_PARENT", values[field],
             comparator)
    # completion: both status witnesses must be present; COMPLETED only for post + Final
    status_names = [n for n in ("JS_STATUS", "STATUS_DETAIL") if by.get(n)]
    completed_ok = False
    if not status_names:
        states["completion"] = "NOT_WITNESSED_IN_VERSION"
    else:
        if len(status_names) < 2 or _s1 != "OK" or _s2 != "OK":
            state, corr = ("INCOMPLETE_WITNESS_SET", "VERSION_PREDATES_OUTCOME") if len(status_names) < 2 else \
                ("CONTRADICTORY_WITHIN_VERSION", "CONTRADICTORY_WITHIN_VERSION")
        elif final:
            completed_ok = values["completion"] == "COMPLETED"
            state = "QUALIFIED_AGREES_WITH_PARENT" if completed_ok else "CONFLICTS_WITH_PARENT"
            corr = "AGREES_WITH_PARENT" if completed_ok else "CONFLICTS_WITH_PARENT"
        else:
            state, corr = "NOT_SUPPORTED_BY_VERSION_STATUS", "VERSION_PREDATES_OUTCOME"
        if not qualified_capture:
            state = "CAPTURE_NOT_QUALIFIED"
        emit("completion", status_names, state, corr, values["completion"], None)
    final = final and len(status_names) == 2 and _s1 == "OK" and _s2 == "OK"
    # points: only in a final version, oriented by team identity
    for field, parent_side in (("a_points", "a"), ("b_points", "b")):
        if not final:
            states[field] = "NOT_SUPPORTED_BY_VERSION_STATUS" if status_names else "NOT_WITNESSED_IN_VERSION"
            if not qualified_capture:
                states[field] = "CAPTURE_NOT_QUALIFIED"
            continue
        if not pair_ok:
            states[field] = "CAPTURE_NOT_QUALIFIED" if not qualified_capture else "ORIENTATION_UNRESOLVED"
            continue
        side = orientation[f"{parent_side}_side"]
        score, score_state = single(f"{side}_SCORE")
        if score_state == "ABSENT":
            states[field] = "NOT_WITNESSED_IN_VERSION" if qualified_capture else "CAPTURE_NOT_QUALIFIED"
            continue
        if score_state == "UNPARSEABLE":
            state, corr = "WITNESS_LITERAL_UNPARSEABLE", "UNPARSEABLE"
        elif score_state == "CONTRADICTORY":
            state, corr = "CONTRADICTORY_WITHIN_VERSION", "CONTRADICTORY_WITHIN_VERSION"
        else:
            agrees = score == values[field]
            corr = "AGREES_WITH_PARENT" if agrees else "CONFLICTS_WITH_PARENT"
            state = "QUALIFIED_AGREES_WITH_PARENT" if agrees and completed_ok else (
                "CONFLICTS_WITH_PARENT" if not agrees else "NOT_SUPPORTED_BY_VERSION_STATUS")
        if not qualified_capture:
            state = "CAPTURE_NOT_QUALIFIED"
        emit(field, [f"{side}_SCORE"], state, corr, values[field], None)
    for field in FIELDS:
        states.setdefault(field, "NOT_WITNESSED_IN_VERSION")
    return {"reasons": reasons, "qualified": qualified_capture, "states": states, "assertions": assertions,
            "scopes": extraction["scopes"],
            "page_status": {"js_status": js_status, "status_detail": detail, "final": final},
            "page_participants": page_participants, "orientation": orientation}


# --------------------------------------------------------------------------------------------- materialization model

class Model:
    def __init__(self, contract: dict[str, Any], rows: list[dict[str, Any]], parent: dict[str, dict[str, Any]],
                 acquisition: dict[str, Any], acquisition_id: str, output_root: Path, control: dict[str, Any]) -> None:
        self.contract = contract
        self.rows = {r["contest_key"]: r for r in rows}
        self.order = [k["contest_key"] for k in contract["scope"]["keys"]]
        self.parent = parent
        self.acquisition = acquisition
        self.acquisition_id = acquisition_id
        self.root = Path(output_root)
        self.control = control
        self.keys = {k["contest_key"]: k for k in contract["scope"]["keys"]}

    def receipt_document(self) -> str:
        return f"acquisition/sha256/{self.acquisition_id}/acquisition.json"

    def requests(self, key: str) -> list[dict[str, Any]]:
        return [r for r in self.acquisition["requests"] if r["contest_key"] == key]

    def capture_records(self, key: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        spec = self.keys[key]
        game = spec["game_id_literal"]
        parent = self.parent[key]
        versions = []
        if spec["selection_role"] == "SEPARATE_PREQUALIFIED_ROUTE_CONTROL":
            receipt = self.control["receipt"]
            headers = [[k, v] for k, v in receipt["headers"].items()]
            observed = _dt.datetime.fromisoformat(receipt["observed_at"]).astimezone(UTC)
            retrieval = clock("PRESENT", role="RECORDED_POSSESSION_UPPER_BOUND", literal=receipt["observed_at"],
                              zone="+00:00", precision="microsecond", earliest=fmt_utc(observed),
                              latest=fmt_utc(observed), document=raw_rel(sha256_bytes(self.control["receipt_raw"])),
                              pointer="/observed_at")
            versions.append({"origin": "MANAGER_RETAINED_CONTROL_REPLAY", "request_seq": None,
                             "final_url": receipt["final_url"], "status": receipt["status"], "headers": headers,
                             "payload": self.control["payload"], "retrieval": retrieval,
                             "receipt_document": raw_rel(sha256_bytes(self.control["receipt_raw"])),
                             "receipt_document_sha256": sha256_bytes(self.control["receipt_raw"]),
                             "receipt_pointer": "/headers"})
        for index, request in enumerate(self.acquisition["requests"]):
            if request["contest_key"] != key or request["kind"] != "REPLAY" or request["http_status"] != 200:
                continue
            payload = read_raw(self.root, request["body_sha256"])
            retrieval = clock("PRESENT", role="EXACT_REQUEST_INTERVAL", literal=request["ended_utc"],
                              start_literal=request["started_utc"], zone="Z", precision="microsecond",
                              earliest=request["started_utc"], latest=request["ended_utc"],
                              document=self.receipt_document(), pointer=f"/requests/{index}/ended_utc")
            versions.append({"origin": "WORKER_ARCHIVE_REPLAY", "request_seq": request["seq"],
                             "final_url": request["url"], "status": request["http_status"],
                             "headers": request["headers"], "payload": payload, "retrieval": retrieval,
                             "receipt_document": self.receipt_document(),
                             "receipt_document_sha256": self.acquisition_id, "receipt_pointer": f"/requests/{index}"})
        captures, assertions = [], []
        for version in versions:
            payload_sha = sha256_bytes(version["payload"])
            checks, receipt_reasons, derived = receipt_checks(version["final_url"], version["status"],
                                                              version["headers"], version["payload"], game)
            result = qualify(key, parent, game, version["payload"], derived["bound"], receipt_reasons)
            ts = derived["wayback_timestamp"] or "00000000000000"
            capture_id = f"wayback:{ts}:{payload_sha}"
            bound = derived["bound"]
            archive_clock = clock("PRESENT", role="ARCHIVE_CAPTURE_UPPER_BOUND", literal=derived["memento"],
                                  zone="GMT", precision="second", latest=bound, document=version["receipt_document"],
                                  pointer=version["receipt_pointer"]) if bound else \
                clock("INVALID", role="ARCHIVE_CAPTURE_UPPER_BOUND", literal=derived["memento"],
                      document=version["receipt_document"], pointer=version["receipt_pointer"],
                      reason=",".join(receipt_reasons) or "MEMENTO_DATETIME_ABSENT")
            if result["reasons"] and bound:
                archive_clock["reason"] = "CAPTURE_QUARANTINED:" + ",".join(result["reasons"])
            event_literal = next((a["literal"] for a in result["assertions"] if a["field"] == "contest_date"
                                  and a["witness"] == "JS_EVENT_TIMESTAMP"), None)
            if event_literal:
                precision, zone, earliest, latest = event_interval(event_literal)
                event = clock("PRESENT", role="SOURCE_ASSERTED_EVENT_INSTANT", literal=event_literal, zone=zone,
                              precision=precision, earliest=earliest, latest=latest, document=raw_rel(payload_sha),
                              pointer="JS_EVENT_TIMESTAMP")
            else:
                event = clock("ABSENT", role="SOURCE_ASSERTED_EVENT_INSTANT", reason="NOT_WITNESSED_IN_VERSION")
            original = replay_parts(version["final_url"])[1] if replay_parts(version["final_url"]) else None
            captures.append({
                "record_type": "archive_capture", "capture_id": capture_id, "contest_key": key,
                "origin": version["origin"], "request_seq": version["request_seq"], "original_url": original,
                "final_url": version["final_url"], "wayback_timestamp": derived["wayback_timestamp"],
                "http_status": version["status"], "content_type": derived["content_type"],
                "memento_datetime_literal": derived["memento"], "origin_date_literal": derived["origin"],
                "link_original": derived["original"], "archive_src": derived["archive_src"],
                "payload_sha256": payload_sha, "payload_bytes": len(version["payload"]),
                "payload_path": raw_rel(payload_sha), "receipt_document": version["receipt_document"],
                "receipt_document_sha256": version["receipt_document_sha256"],
                "receipt_pointer": version["receipt_pointer"], "receipt_checks": checks,
                "state": "QUALIFIED" if result["qualified"] else "QUARANTINED",
                "quarantine_reasons": result["reasons"], "time_evidence_class": "ARCHIVE_CAPTURE_UPPER_BOUND",
                "clocks": {"archive_capture": archive_clock, "retrieval": version["retrieval"], "event": event},
                "main_element_spans": result["scopes"], "page_status": result["page_status"],
                "page_participants": result["page_participants"], "orientation": result["orientation"],
                "field_states": result["states"]})
            for a in result["assertions"]:
                assertions.append({"record_type": "archive_assertion", "contest_key": key, "original_url": original,
                                   "capture_id": capture_id, "payload_sha256": payload_sha,
                                   "source_revision": capture_id, "field": a["field"], "field_role": ROLES[a["field"]],
                                   "witness": a["witness"], "witness_span": a["witness_span"], "literal": a["literal"],
                                   "value": a["value"], "parent_value": a["parent_value"],
                                   "parent_comparator": a["parent_comparator"], "corroboration": a["corroboration"],
                                   "field_state": a["field_state"]})
        captures.sort(key=lambda c: (c["wayback_timestamp"] or "", c["payload_sha256"]))
        rank = {c["capture_id"]: i for i, c in enumerate(captures)}
        assertions.sort(key=lambda a: (rank[a["capture_id"]], FIELDS.index(a["field"]), a["witness"],
                                       a["witness_span"][0]))
        return captures, assertions

    def bundle(self, key: str) -> bytes:
        row, spec, parent = self.rows[key], self.keys[key], self.parent[key]
        requests = self.requests(key)
        captures, assertions = self.capture_records(key)
        outcome = self.acquisition["outcomes"][key]
        support: dict[str, Any] = {}
        for field in WITNESSABLE:
            bounds = sorted(c["clocks"]["archive_capture"]["latest_utc"] for c in captures
                            if c["field_states"][field] == "QUALIFIED_AGREES_WITH_PARENT")
            support[field] = bounds[0] if bounds else None
        qualified = [c["capture_id"] for c in captures if c["state"] == "QUALIFIED"]
        supported = [f for f in WITNESSABLE if support[f]]
        reasons = sorted({r for c in captures for r in c["quarantine_reasons"]})
        if outcome == "CONTROL_REUSED":
            disposition = "CONTROL_REUSED_QUALIFIED" if len(supported) == len(WITNESSABLE) else \
                "ARCHIVED_VERSION_NOT_QUALIFIED"
        elif captures:
            disposition = ("ARCHIVED_VERSION_QUALIFIED_ALL_WITNESSABLE_FIELDS" if len(supported) == len(WITNESSABLE)
                           else "ARCHIVED_VERSION_QUALIFIED_PARTIAL_FIELDS" if supported
                           else "ARCHIVED_VERSION_NOT_QUALIFIED")
        else:
            disposition = outcome
        if outcome in ("REDIRECT_REFUSED", "REPLAY_REQUEST_FAILED") and captures:
            reasons.append(f"ACQUISITION_{outcome}")
        lines = [record_line({
            "record_type": "archive_disposition", "ord": self.order.index(key), "contest_key": key,
            "season": row["season"], "contest_date": row["contest_date"], "a_key": row["a_key"], "b_key": row["b_key"],
            "classification_pair": row["classification_pair"], "stratum": row["stratum"],
            "selection_role": row["selection_role"], "candidate_url": spec["candidate_url"],
            "game_id_literal": spec["game_id_literal"], "acquisition_outcome": outcome, "disposition": disposition,
            "reasons": sorted(set(reasons)), "request_count": len(requests),
            "metadata_requests": sum(1 for r in requests if r["kind"] == "METADATA"),
            "replay_requests": sum(1 for r in requests if r["kind"] == "REPLAY"),
            "capture_ids": [c["capture_id"] for c in captures], "qualified_capture_ids": qualified,
            "field_support": support, "parent_values": parent["values"]})]
        for request in requests:
            answer = None
            if request["kind"] == "METADATA" and request["http_status"] == 200:
                answer = metadata_answer(read_raw(self.root, request["body_sha256"]), spec["game_id_literal"])
            lines.append(record_line({"record_type": "archive_request", **{k: request[k] for k in (
                "seq", "contest_key", "kind", "purpose", "url", "started_utc", "ended_utc", "outcome", "http_status",
                "reason", "headers", "location", "body_sha256", "body_bytes", "retry_after_seconds", "slept_seconds",
                "error")}, "body_path": raw_rel(request["body_sha256"]) if request["body_sha256"] else None,
                "metadata_answer": answer}))
        lines += [record_line(c) for c in captures]
        lines += [record_line(a) for a in assertions]
        return b"".join(lines)


def split_bundles(blob: bytes) -> dict[str, bytes]:
    out: dict[str, list[bytes]] = {name: [] for name in PAYLOAD_FILES}
    for line in blob.splitlines(keepends=True):
        kind = json.loads(line)["record_type"]
        if kind not in BUNDLE_FILES:
            raise BuildRefused("REFUSED_ALTERED_PREFIX", f"unexpected record type {kind} in the bundle stream")
        out[BUNDLE_FILES[kind]].append(line)
    return {name: b"".join(lines) for name, lines in out.items()}


def permute(items: list[Any], order: str) -> list[Any]:
    items = list(items)
    if order == "natural":
        return items
    if order == "reverse":
        return items[::-1]
    random.Random(int(order.split(":")[1])).shuffle(items)
    return items


# --------------------------------------------------------------------------------------------- checkpoint

def _keys_sha(keys: Sequence[str]) -> str:
    return sha256_bytes("\n".join(keys).encode("utf-8"))


class Checkpoint:
    def __init__(self, directory: Path, header_doc: dict[str, Any], chunk_size: int, resume: bool) -> None:
        self.dir = Path(directory)
        self.chunk_size = chunk_size
        self.ledger = self.dir / "checkpoint.ledger.jsonl"
        header_path = self.dir / "checkpoint.json"
        if resume:
            if not header_path.is_file():
                raise BuildRefused("REFUSED_STALE_CHECKPOINT", f"no checkpoint header in {self.dir}")
            stored = json.loads(header_path.read_text(encoding="utf-8"))
            differing = sorted(k for k in set(stored) | set(header_doc) if stored.get(k) != header_doc.get(k))
            if differing:
                raise BuildRefused("REFUSED_STALE_CHECKPOINT", f"checkpoint binds different {differing}")
        else:
            if self.dir.exists() and any(self.dir.iterdir()):
                raise BuildRefused("CHECKPOINT_EXISTS", f"{self.dir} is not empty; use --resume")
            (self.dir / "chunks").mkdir(parents=True, exist_ok=True)
            with header_path.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(header_doc, sort_keys=True, indent=1) + "\n")

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


def build_bundles(model: Model, keys: list[str], *, chunk_size: int, checkpoint: Checkpoint | None,
                  stop_after: int | None) -> dict[str, bytes] | None:
    if checkpoint is None:
        blobs = {key: model.bundle(key) for key in keys}
    else:
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
            raise BuildRefused("REFUSED_ALTERED_PREFIX", "checkpoint does not cover every tranche key")
        blobs = {}
        for row in rows:
            data = checkpoint.read_chunk(checkpoint.chunk_path(row["index"]))
            for line in data.splitlines(keepends=True):
                blobs.setdefault(json.loads(line)["contest_key"], []).append(line)
        blobs = {k: b"".join(v) for k, v in blobs.items()}
    if sorted(blobs) != sorted(keys):
        raise BuildRefused("CENSUS_INCOMPLETE", "a tranche key is missing or duplicated")
    return blobs


# --------------------------------------------------------------------------------------------- database

TABLE_SQL = (
    "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
    "CREATE TABLE dispositions (ord INTEGER PRIMARY KEY, contest_key TEXT NOT NULL UNIQUE, season INTEGER NOT NULL,"
    " a_key TEXT NOT NULL, b_key TEXT NOT NULL, disposition TEXT NOT NULL, record TEXT NOT NULL);"
    "CREATE TABLE requests (ord INTEGER PRIMARY KEY, seq INTEGER NOT NULL UNIQUE, contest_key TEXT NOT NULL,"
    " kind TEXT NOT NULL, record TEXT NOT NULL);"
    "CREATE TABLE captures (ord INTEGER PRIMARY KEY, capture_id TEXT NOT NULL UNIQUE, contest_key TEXT NOT NULL,"
    " state TEXT NOT NULL, record TEXT NOT NULL);"
    "CREATE TABLE assertions (ord INTEGER PRIMARY KEY, contest_key TEXT NOT NULL, capture_id TEXT NOT NULL,"
    " field TEXT NOT NULL, witness TEXT NOT NULL, span_start INTEGER NOT NULL, record TEXT NOT NULL,"
    " UNIQUE (contest_key, capture_id, field, witness, span_start));")
INDEX_SQL = ("CREATE INDEX ix_requests_contest ON requests (contest_key, ord);"
             "CREATE INDEX ix_captures_contest ON captures (contest_key, ord);"
             "CREATE INDEX ix_assertions_contest ON assertions (contest_key, ord);")
TABLES = ("meta", "dispositions", "requests", "captures", "assertions")
RECORD_HOMES = {"dispositions.jsonl": "dispositions", "requests.jsonl": "requests", "captures.jsonl": "captures",
                "assertions.jsonl": "assertions"}


def _lines(payload: bytes) -> list[str]:
    return payload.decode("utf-8").splitlines(keepends=True)


def build_database(path: Path, payloads: dict[str, bytes], meta: dict[str, str]) -> dict[str, Any]:
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA page_size = 4096")
        conn.execute("PRAGMA journal_mode = OFF")
        conn.executescript(TABLE_SQL)
        conn.executemany("INSERT INTO meta VALUES (?, ?)", sorted(meta.items()))
        rows = [(i, r["contest_key"], r["season"], r["a_key"], r["b_key"], r["disposition"], line.rstrip("\n"))
                for i, (r, line) in enumerate((json.loads(x), x) for x in _lines(payloads["dispositions.jsonl"]))]
        conn.executemany("INSERT INTO dispositions VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
        rows = [(i, r["seq"], r["contest_key"], r["kind"], line.rstrip("\n"))
                for i, (r, line) in enumerate((json.loads(x), x) for x in _lines(payloads["requests.jsonl"]))]
        conn.executemany("INSERT INTO requests VALUES (?, ?, ?, ?, ?)", rows)
        rows = [(i, r["capture_id"], r["contest_key"], r["state"], line.rstrip("\n"))
                for i, (r, line) in enumerate((json.loads(x), x) for x in _lines(payloads["captures.jsonl"]))]
        conn.executemany("INSERT INTO captures VALUES (?, ?, ?, ?, ?)", rows)
        try:
            rows = [(i, r["contest_key"], r["capture_id"], r["field"], r["witness"], r["witness_span"][0],
                     line.rstrip("\n"))
                    for i, (r, line) in enumerate((json.loads(x), x) for x in _lines(payloads["assertions.jsonl"]))]
            conn.executemany("INSERT INTO assertions VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
        except sqlite3.IntegrityError as exc:
            raise BuildRefused("DUPLICATE_ASSERTION", str(exc)) from exc
        conn.executescript(INDEX_SQL)
        conn.commit()
        counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES}
    finally:
        conn.close()
    records = {name: counts[RECORD_HOMES[name]] for name in PAYLOAD_FILES}
    return {"table_counts": counts, "record_counts": records}


# --------------------------------------------------------------------------------------------- materialization

def runtime() -> dict[str, str]:
    return {"implementation": platform.python_implementation(), "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version, "zlib": zlib.ZLIB_VERSION}


def materialize_identity(output_root: Path, manifest_root: Path, identity_document: dict[str, Any],
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


def find_acquisition(output_root: Path, pid: str, explicit: Path | None) -> tuple[Path, dict[str, Any]]:
    if explicit is not None:
        doc = load_acquisition(explicit, output_root)
        if doc["policy_id"] != pid:
            raise BuildRefused("ACQUISITION_POLICY_MISMATCH", "the acquisition binds another policy")
        return Path(explicit), doc
    root = Path(output_root) / "acquisition" / "sha256"
    found = []
    for path in sorted(root.glob("*/acquisition.json")) if root.is_dir() else []:
        doc = load_acquisition(path, output_root)
        if doc["policy_id"] == pid:
            found.append((path, doc))
    if len(found) != 1:
        raise BuildRefused("ACQUISITION_MISSING", f"{len(found)} finalized acquisitions for policy {pid}")
    return found[0]


def verify_acquisition(contract: dict[str, Any], doc: dict[str, Any], output_root: Path,
                       control: dict[str, Any]) -> None:
    keys = [k["contest_key"] for k in contract["scope"]["keys"]]
    if doc["keys"] != keys or set(doc["outcomes"]) != set(keys) or doc["tranche_sha256"] != contract["scope"][
            "tranche_sha256"]:
        raise BuildRefused("ACQUISITION_KEYS_INVALID", "acquisition keys differ from the tranche")
    limits = contract["acquisition"]["limits"]
    if [r["seq"] for r in doc["requests"]] != list(range(1, len(doc["requests"]) + 1)) or \
            len(doc["requests"]) > limits["total_requests"]:
        raise BuildRefused("ACQUISITION_REQUESTS_INVALID", "request sequence or total")
    for key in keys:
        mine = [r for r in doc["requests"] if r["contest_key"] == key]
        if sum(1 for r in mine if r["kind"] == "METADATA") > limits["metadata_requests_per_key"] or \
                sum(1 for r in mine if r["kind"] == "REPLAY") > limits["replay_requests_per_key"]:
            raise BuildRefused("ACQUISITION_REQUESTS_INVALID", f"{key} exceeds the per-key limits")
        spec = next(k for k in contract["scope"]["keys"] if k["contest_key"] == key)
        if spec["selection_role"] == "SEPARATE_PREQUALIFIED_ROUTE_CONTROL" and mine:
            raise BuildRefused("ACQUISITION_REQUESTS_INVALID", "the control must cost zero requests")
    for request in doc["requests"]:
        host = urllib.parse.urlsplit(request["url"]).hostname
        if host not in ALLOWED_HOSTS or (request["kind"] == "METADATA") != (host == "archive.org"):
            raise BuildRefused("ACQUISITION_HOST_REFUSED", request["url"])
        if request["kind"] == "REPLAY":
            parts = replay_parts(request["url"])
            spec = next(k for k in contract["scope"]["keys"] if k["contest_key"] == request["contest_key"])
            if not parts or not equivalent_original(parts[1], spec["game_id_literal"]):
                raise BuildRefused("ACQUISITION_HOST_REFUSED", request["url"])
        if request["body_sha256"]:
            read_raw(output_root, request["body_sha256"])
    ctrl = doc["control"]
    if (ctrl["payload_sha256"], ctrl["raw_receipt_sha256"], ctrl["route_qualification_sha256"]) != (
            sha256_bytes(control["payload"]), sha256_bytes(control["receipt_raw"]), sha256_bytes(control["route_raw"])):
        raise BuildRefused("CONTROL_MISMATCH", "acquisition control binding")
    for sha in (ctrl["payload_sha256"], ctrl["raw_receipt_sha256"], ctrl["route_qualification_sha256"]):
        read_raw(output_root, sha)


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
    parent = verify_source_database(contract, args.source_database)
    rows = verify_tranche(contract, args.tranche)
    bindings = verify_source_bindings(contract, args.source_bindings, parent, args.tranche, args.source_database)
    control = verify_control(contract, Path(bindings["control_path"]))
    parent_values = read_parent(args.source_database, rows)
    output_root = Path(args.output_root)
    evidence_root = Path(args.evidence_root) if args.evidence_root else output_root
    pid = policy_id(contract)
    capture_result = None
    if args.stage in ("capture", "all"):
        if evidence_root.resolve() != output_root.resolve():
            raise BuildRefused("ARGUMENT_INVALID", "capture writes its evidence into the output root only")
        capture_result = capture(contract, rows, output_root, control, audit=not args.no_network_audit)
        if args.stage == "capture":
            return {"state": "CAPTURE_" + capture_result["state"], "capture": capture_result,
                    "policy_id": pid, "contract_sha256": contract_sha, "seconds": round(time.time() - started, 3)}
    acquisition_path, acquisition = find_acquisition(evidence_root, pid, args.acquisition)
    acquisition_id = acquisition_path.parent.name
    verify_acquisition(contract, acquisition, evidence_root, control)
    model = Model(contract, rows, parent_values, acquisition, acquisition_id, evidence_root, control)
    keys = permute([k["contest_key"] for k in contract["scope"]["keys"]], args.input_order)
    parent_doc = {"source_time": parent}
    control_doc = {"contest_key": contract["scope"]["control_contest_key"],
                   "route_qualification_sha256": sha256_bytes(control["route_raw"]),
                   "raw_receipt_sha256": sha256_bytes(control["receipt_raw"]),
                   "payload_sha256": sha256_bytes(control["payload"])}
    checkpoint = None
    if args.checkpoint_dir:
        header_doc = {"schema": CHECKPOINT_SCHEMA, "contract_sha256": contract_sha, "parent": parent_doc,
                      "tranche_sha256": contract["scope"]["tranche_sha256"], "acquisition_identity": acquisition_id,
                      "payload_schema": PAYLOAD_SCHEMA, "chunk_size": args.chunk_size,
                      "unit_key_list_sha256": _keys_sha(keys), "unit_count": len(keys),
                      "producer_sha256": sha256_file(Path(__file__))}
        checkpoint = Checkpoint(Path(args.checkpoint_dir), header_doc, args.chunk_size, args.resume)
    blobs = build_bundles(model, keys, chunk_size=args.chunk_size, checkpoint=checkpoint,
                          stop_after=args.stop_after_chunks)
    if blobs is None:
        return {"state": "INTERRUPTED_AT_CHECKPOINT", "checkpoint_dir": str(args.checkpoint_dir),
                "completed_chunks": len(checkpoint.completed(keys)) if checkpoint else 0, "unit_count": len(keys)}
    ordered = b"".join(blobs[k] for k in model.order)
    payloads = split_bundles(ordered)
    counts = {name: payloads[name].count(b"\n") for name in PAYLOAD_FILES}
    if counts["dispositions.jsonl"] != contract["scope"]["tranche_count"] or \
            counts["requests.jsonl"] != len(acquisition["requests"]):
        raise BuildRefused("CENSUS_INCOMPLETE", "dispositions or requests do not cover the tranche/acquisition")
    semantic = {name: sha256_bytes(payloads[name]) for name in PAYLOAD_FILES}
    packed = {f"{name}.gz": gzip.compress(payloads[name], compresslevel=GZIP_LEVEL, mtime=0) for name in PAYLOAD_FILES}
    content_document = {"schema": CONTENT_SCHEMA, "stage": "archived-publication-content", "population": POPULATION,
                        "contract_id": contract["contract_id"], "contract_sha256": contract_sha, "parent": parent_doc,
                        "tranche_sha256": contract["scope"]["tranche_sha256"], "acquisition_identity": acquisition_id,
                        "acquisition_policy_id": pid, "control": control_doc, "payload_schema": PAYLOAD_SCHEMA,
                        "payload_encoding": "gzip(level 9, mtime 0) of the canonical JSONL; semantic sha256 over the "
                                            "uncompressed bytes",
                        "semantic_outputs": semantic, "outputs": {n: sha256_bytes(d) for n, d in packed.items()},
                        "row_counts": counts}
    content_identity = sha256_bytes(canonical_json_bytes(content_document))
    with tempfile.TemporaryDirectory(prefix="nap-") as work:
        db_path = Path(work) / DB_FILE
        meta = {"schema_version": DB_SCHEMA, "contract_id": contract["contract_id"], "contract_sha256": contract_sha,
                "content_identity": content_identity, "payload_schema": PAYLOAD_SCHEMA,
                "semantic_sha256": json.dumps(semantic, sort_keys=True),
                "row_counts": json.dumps(counts, sort_keys=True), "parent": json.dumps(parent_doc, sort_keys=True),
                "tranche_sha256": contract["scope"]["tranche_sha256"], "acquisition_identity": acquisition_id,
                "acquisition_policy_id": pid, "control": json.dumps(control_doc, sort_keys=True),
                "row_labels": json.dumps(AUTHORITY, sort_keys=True),
                "fields": json.dumps({"order": list(FIELDS), "roles": ROLES, "witnessable": list(WITNESSABLE)},
                                     sort_keys=True),
                "record_homes": json.dumps(RECORD_HOMES, sort_keys=True),
                "origin_date_tolerance_seconds": str(ORIGIN_DATE_TOLERANCE_SECONDS)}
        db_counts = build_database(db_path, payloads, meta)
        if db_counts["record_counts"] != counts:
            raise BuildRefused("CENSUS_INCOMPLETE", f"database records {db_counts['record_counts']} != {counts}")
        database_document = {"schema": DATABASE_SCHEMA, "stage": "archived-publication-database",
                             "population": POPULATION, "contract_sha256": contract_sha,
                             "content_identity": content_identity, "parent": parent_doc, "db_schema_version": DB_SCHEMA,
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
                      "source_bindings": bindings, "acquisition": str(acquisition_path),
                      "database_identity": database_identity,
                      "database_manifest": f"sha256/{database_identity}/run_manifest.json"}
        content = materialize_identity(args.output_root, args.manifest_root, content_document, packed, provenance)
        database = materialize_identity(args.output_root, args.manifest_root, database_document, {DB_FILE: db_path},
                                        {**provenance, "content_identity": content_identity})
    dispositions = [json.loads(line) for line in payloads["dispositions.jsonl"].decode("utf-8").splitlines()]
    tally: dict[str, int] = {}
    for item in dispositions:
        tally[item["disposition"]] = tally.get(item["disposition"], 0) + 1
    return {"state": content["state"], "content_identity": content_identity, "database_identity": database_identity,
            "content": content, "database": database, "row_counts": counts, "table_counts": db_counts["table_counts"],
            "semantic_sha256": semantic, "payload_sha256": content_document["outputs"],
            "database_sha256": database_document["outputs"][DB_FILE], "database_state": database["state"],
            "contract_sha256": contract_sha, "parent": parent_doc, "acquisition_identity": acquisition_id,
            "acquisition_policy_id": pid, "acquisition_totals": acquisition["totals"], "capture": capture_result,
            "dispositions": tally, "input_order": args.input_order, "chunk_size": args.chunk_size,
            "variant": args.variant, "runtime": runtime(), "seconds": round(time.time() - started, 3)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_national_archived_publication", allow_abbrev=False,
                                     description="Build the bounded 2019 archived-publication evidence sidecar.")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--source-database", required=True, type=Path)
    parser.add_argument("--source-bindings", required=True, type=Path)
    parser.add_argument("--tranche", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--manifest-root", required=True, type=Path)
    parser.add_argument("--stage", choices=["capture", "materialize", "all"], default="materialize")
    parser.add_argument("--acquisition", type=Path, default=None)
    parser.add_argument("--evidence-root", type=Path, default=None,
                        help="raw store and acquisition root (default: the output root); variants write elsewhere")
    parser.add_argument("--input-order", default="natural")
    parser.add_argument("--chunk-size", type=int, default=0)
    parser.add_argument("--checkpoint-dir", type=Path, default=None)
    parser.add_argument("--stop-after-chunks", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--variant", default="CANONICAL")
    parser.add_argument("--receipt", type=Path, default=None)
    parser.add_argument("--no-network-audit", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(raw)
    args.argv = ["tools/build_national_archived_publication.py", *raw]
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

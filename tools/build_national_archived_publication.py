r"""Build the archived-publication evidence sidecar for the fixed 2019 tranche (BAT-713, Cycle #41 TP41-A01).

``python -B tools/build_national_archived_publication.py --contract configs/national_archived_publication_2019_contract_v1_2.json
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
  each archived page at its exact field grain (``aggie_analytics.national_source_time.archive_fields``: tokenized
  attributes, closed text-only elements, line-start JS assignments, every occurrence counted); maps the page teams to
  the parent's a/b teams only through documented parent names, the CFBD route role and a qualified date (contract
  V1.2; numeric ESPN/CFBD identifiers are never equated; a version whose participants do not map is quarantined
  whole); qualifies every field witness against the parent's accepted values; refuses contradictory participant
  mappings across the tranche; and writes, create-only and content
  addressed, ``dispositions.jsonl``, ``requests.jsonl``, ``captures.jsonl``, ``assertions.jsonl`` (gzip) and
  ``national_archived_publication.sqlite`` with their run manifests. The consumer re-derives every capture and
  assertion record with the same field-grain module and refuses any difference.

Nothing here admits anything: an archive capture is an upper bound for the exact witnessed version, the parent's
assertions and clocks are untouched, and the query decides cutoffs from the retained receipt literals.
``--chunk-size`` with ``--checkpoint-dir`` builds through a hash-chained checkpoint that ``--resume`` verifies;
``--stop-after-chunks`` simulates an interruption; ``--input-order`` permutes the tranche processing order.

``--capture-policy <policy.json>`` (BAT-716, stage capture or all; ``configs/national_archived_publication_capture_policy.json``,
``docs/architecture/ARCHIVE_CAPTURE_SERVICE_PAUSE.md``) selects the prospective service-aware capture mode: the first
HTTP 429 stops the whole acquisition after its response is retained, a later explicit invocation resumes only at or
after the derived eligible instant, under one bound, hash-chained journal, request-authority anchor and owner lock,
and ``--acknowledge-unknown-intent <seq>`` reconciles an interrupted request. Without the option the capture stage
keeps its frozen per-key retry behaviour.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import gzip
import hashlib
import http.client
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
from pathlib import Path
from typing import Any, Callable, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.national_source_time import archive_fields as af  # noqa: E402

PRODUCER = "national_archived_publication/1.2.0"
POPULATION = "national_archived_publication_2019"
CONTRACT_SCHEMA = "1.2.0"
CONTRACT_ID_PREFIX = "BAT-713-NATIONAL-ARCHIVED-PUBLICATION-2019-"
CONTRACT_ID = CONTRACT_ID_PREFIX + "V1.2"
SUPERSEDED_CONTRACTS = {("1.0.0", CONTRACT_ID_PREFIX + "V1.0"): "contract V1.0 equated ESPN and CFBD team identifiers "
                        "and read witnesses by first match",
                        ("1.1.0", CONTRACT_ID_PREFIX + "V1.1"): "contract V1.1 left a version with an unresolved "
                        "participant mapping qualified for its date and completion"}
PAYLOAD_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-PAYLOAD-2"
CONTENT_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-CONTENT-2"
DATABASE_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-DATABASE-2"
DB_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-DB-2"
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
FIELDS = af.FIELDS
ROLES = af.ROLES
WITNESSABLE = af.WITNESSABLE
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
                        "main_element_spans", "page_status", "page_participants", "orientation", "participant_mapping",
                        "field_states"),
    "archive_assertion": ("record_type", "contest_key", "original_url", "capture_id", "payload_sha256",
                          "source_revision", "field", "field_role", "witness", "witness_span", "literal", "value",
                          "parent_value", "parent_comparator", "corroboration", "field_state"),
    "clock": ("state", "role", "literal", "start_literal", "zone", "precision", "earliest_utc", "latest_utc",
              "evidence_document", "evidence_pointer", "reason"),
}
CLOCK_KINDS = ("archive_capture", "retrieval", "event")
INPUT_ORDER = re.compile(r"^(natural|reverse|shuffle:[0-9]{1,9})$")
TS14_RE = af.TS14_RE
CLOSEST_URL_RE = af.CLOSEST_URL_RE
ORIGIN_DATE_TOLERANCE_SECONDS = af.ORIGIN_DATE_TOLERANCE_SECONDS
USABLE_CLOSEST_STATUS = af.USABLE_CLOSEST_STATUS
REDIRECT_STATUS = (301, 302, 303, 307, 308)
RETRYABLE_STATUS = (429, 500, 502, 503, 504)
INTERRUPTED_EXIT = 3
GZIP_LEVEL = 9
ZLIB_LEVEL = 9
UTC = _dt.timezone.utc
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
ALLOWED_HOSTS = ("archive.org", "web.archive.org")
#: Request starts are spaced with the high-resolution performance counter plus this margin. Cycle #41 Attempt #1's
#: capture at 30b1bdb0 spaced them with time.monotonic(), which on CPython 3.12/Windows is GetTickCount64 with a
#: 15.625 ms tick; 9 of its 68 recorded start gaps were 0.4-8.5 ms short of one second (disclosed finding).
SPACING_MARGIN_SECONDS = 0.05


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


def _check_fields(kind: str, value: dict[str, Any], fields: dict[str, tuple[str, ...]] | None = None) -> None:
    expected = (fields or RECORD_FIELDS)[kind]
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


def record_line(record: dict[str, Any], fields: dict[str, tuple[str, ...]] | None = None) -> bytes:
    kind = record["record_type"]
    _check_fields(kind, record, fields)
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
# The clock, URL and header rules are the shared field-grain module's (the consumer re-derives with the same rules).

fmt_utc = af.fmt_utc
parse_utc = af.parse_utc
ts14_instant = af.ts14_instant
rfc1123 = af.rfc1123
end_of_second = af.end_of_second
earliest_event_instant = af.earliest_event_instant
clock = af.clock
event_interval = af.event_interval
local_candidate_dates = af.local_candidate_dates
equivalent_original = af.equivalent_original
replay_parts = af.replay_parts
link_original = af.link_original
header = af.header


def utc_now() -> str:
    return fmt_utc(_dt.datetime.now(UTC))


def replay_url(ts: str, original: str) -> str:
    return f"https://web.archive.org/web/{ts}id_/{original}"


def metadata_url(candidate: str, ts: str) -> str:
    return "https://archive.org/wayback/available?" + urllib.parse.urlencode({"url": candidate, "timestamp": ts})


# --------------------------------------------------------------------------------------------- contract and parents

def load_contract(path: Path) -> tuple[dict[str, Any], str]:
    raw = Path(path).read_bytes()
    try:
        contract = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BuildRefused("CONTRACT_INVALID", str(exc)) from exc
    superseded = SUPERSEDED_CONTRACTS.get((contract.get("schema_version"), contract.get("contract_id")))
    if superseded:
        raise BuildRefused("CONTRACT_SUPERSEDED", f"{superseded}; build with the successor {CONTRACT_ID}")
    if contract.get("schema_version") != CONTRACT_SCHEMA or contract.get("contract_id") != CONTRACT_ID:
        raise BuildRefused("CONTRACT_SCHEMA_UNKNOWN", f"{contract.get('schema_version')} {contract.get('contract_id')}")
    mapping = contract.get("participant_mapping") or {}
    if mapping.get("numeric_identifier_equality") != "NEVER_AUTHORITY" or mapping.get("rule") != af.MAPPING_RULE             or mapping.get("capture_quarantine") != af.QUARANTINE_RULE:
        raise BuildRefused("CONTRACT_SCHEMA_UNKNOWN", "participant mapping rule")
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
    """Accepted parent values for every tranche key (contest record plus the single parent value of each field) and
    the participant sources documented by the parent's own joined lineage rows (CFBD route school names and roles,
    NCAA names); the participant mapping uses nothing else."""
    conn = sqlite3.connect(Path(database).resolve().as_uri() + "?mode=ro", uri=True)
    out: dict[str, dict[str, Any]] = {}
    try:
        for row in rows:
            found = conn.execute("SELECT record, assertions, lineage FROM contests WHERE contest_key = ?",
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
            lineage = [json.loads(line) for line in zlib.decompress(found[2]).decode("utf-8").splitlines()]
            out[row["contest_key"]] = {"record": record, "values": parent_values,
                                       "participants": af.participant_sources(record, lineage)}
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
                 error: str | None = None, incomplete: str | None = None) -> None:
        self.status, self.reason, self.headers, self.body, self.error = status, reason, headers, body, error
        #: Only ``urllib_transport_observed`` (BAT-716 service mode) sets this: BODY_LIMIT_EXCEEDED or BODY_READ_FAILED
        #: when the status line and headers were received but ``body`` is not the complete body.
        self.incomplete = incomplete


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401 - urllib hook
        return None


def urllib_transport(url: str, headers: dict[str, str], timeout: float, max_bytes: int | None = None) -> Response:
    """One HTTP GET without proxies, redirects, cookies or credentials. A 3xx/4xx/5xx is a response, not an error.
    With ``max_bytes`` (BAT-715 expansion) a body longer than the limit is not kept: the request fails closed as a
    network error naming BODY_LIMIT_EXCEEDED (it still counts against every request limit)."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    request = urllib.request.Request(url, headers=headers, method="GET")

    def read(stream: Any) -> bytes | None:
        if max_bytes is None:
            return stream.read()
        data = stream.read(max_bytes + 1)
        return None if len(data) > max_bytes else data
    try:
        with opener.open(request, timeout=timeout) as response:
            body = read(response)
            if body is None:
                return Response(None, None, [], b"", f"BODY_LIMIT_EXCEEDED: more than {max_bytes} bytes")
            return Response(response.status, response.reason, [[k, v] for k, v in response.headers.items()], body)
    except urllib.error.HTTPError as error:
        body = read(error) if error.fp is not None else b""
        if body is None:
            return Response(None, None, [], b"", f"BODY_LIMIT_EXCEEDED: more than {max_bytes} bytes")
        return Response(error.code, str(error.reason), [[k, v] for k, v in (error.headers or {}).items()], body)
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as error:
        return Response(None, None, [], b"", f"{type(error).__name__}: {error}")


def urllib_transport_observed(url: str, headers: dict[str, str], timeout: float,
                              max_bytes: int | None = None) -> Response:
    """BAT-716 service-aware capture only: the same single GET as ``urllib_transport`` (no proxies, redirects, cookies
    or credentials), except that a received status line and headers are never discarded. When the body exceeds
    ``max_bytes`` (BODY_LIMIT_EXCEEDED) or reading it fails after the status (BODY_READ_FAILED), ``body`` is the bounded
    prefix actually read (at most ``max_bytes``; nothing beyond ``max_bytes + 1`` bytes is read) and ``incomplete``
    names the case. The caller decides what such a response may evidence; ``urllib_transport`` is unchanged."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    request = urllib.request.Request(url, headers=headers, method="GET")

    def bounded(stream: Any) -> tuple[bytes, str | None, str | None]:
        chunks: list[bytes] = []
        total = 0
        limit = None if max_bytes is None else max_bytes + 1
        try:
            while limit is None or total < limit:
                chunk = stream.read(65536 if limit is None else min(65536, limit - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
        except (OSError, http.client.HTTPException, ValueError) as exc:
            partial = getattr(exc, "partial", b"")
            data = b"".join(chunks) + (partial if isinstance(partial, bytes) else b"")
            data = data if max_bytes is None else data[:max_bytes]
            return data, "BODY_READ_FAILED", f"BODY_READ_FAILED: {type(exc).__name__}: {exc}"
        data = b"".join(chunks)
        if max_bytes is not None and len(data) > max_bytes:
            return data[:max_bytes], "BODY_LIMIT_EXCEEDED", f"BODY_LIMIT_EXCEEDED: more than {max_bytes} bytes"
        return data, None, None
    try:
        with opener.open(request, timeout=timeout) as response:
            received = [[k, v] for k, v in response.headers.items()]
            body, incomplete, error = bounded(response)
            return Response(response.status, response.reason, received, body, error, incomplete)
    except urllib.error.HTTPError as error:
        received = [[k, v] for k, v in (error.headers or {}).items()]
        body, incomplete, note = bounded(error) if error.fp is not None else (b"", None, None)
        return Response(error.code, str(error.reason), received, body, note, incomplete)
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, http.client.HTTPException) as error:
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


# The availability answer read from a retained metadata body is the shared module's (the consumer re-derives it).
metadata_answer = af.metadata_answer


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
            sleep: Callable[[float], None] = time.sleep, monotonic: Callable[[], float] = time.perf_counter,
            now: Callable[[], str] = utc_now,
            audit: bool = True, planner: Callable[..., tuple[str, str, str] | None] | None = None,
            outcome_of: Callable[[dict[str, Any], list[dict[str, Any]], bool], str] | None = None) -> dict[str, Any]:
    """Run (or resume) the bounded acquisition and finalize the acquisition document. ``planner`` and ``outcome_of``
    default to the V1.2 per-key plan and outcome; the BAT-715 expansion passes its own (same journal and limits)."""
    plan_next_key = planner or plan_next
    key_outcome = outcome_of or acquisition_outcome
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
            step = plan_next_key(key, history, contract, read_body)
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
                wait = limits["min_seconds_between_request_starts"] + SPACING_MARGIN_SECONDS -                     (monotonic() - last_start)
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
        if exhausted and plan_next_key(key, history, contract, read_body) is not None:
            outcome = "NOT_ATTEMPTED_TOTAL_BUDGET_EXHAUSTED" if not history else key_outcome(key, history, True)
        else:
            outcome = key_outcome(key, history, False)
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
# Field-grain extraction, receipt rules, participant mapping and qualification live in the shared module so that the
# consumer re-derives exactly the same records from the retained bytes (the independent validator does not use it).

extract = af.extract
witness_value = af.witness_value
receipt_checks = af.receipt_checks
qualify = af.qualify
participant_sources = af.participant_sources


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
        """Every archived version of one key: the retained control (zero requests) and each 200 replay, each derived
        by the shared field-grain module exactly as the consumer re-derives it."""
        spec = self.keys[key]
        game = spec["game_id_literal"]
        parent = self.parent[key]
        versions = []
        if spec["selection_role"] == af.CONTROL_ROLE:
            versions.append(af.control_version(sha256_bytes(self.control["receipt_raw"]), self.control["receipt"],
                                               self.control["payload"]))
        for index, request in enumerate(self.acquisition["requests"]):
            if request["contest_key"] != key or not af.capture_request(request):
                continue
            versions.append(af.worker_version(self.acquisition_id, index, request,
                                              read_raw(self.root, request["body_sha256"])))
        captures, assertions = [], []
        for version in versions:
            capture, rows = af.derive_capture(key, parent, game, version, sha256_bytes(version["payload"]))
            captures.append(capture)
            assertions += rows
        captures = af.order_captures(captures)
        return captures, af.order_assertions(captures, assertions)

    def bundle(self, key: str) -> bytes:
        row, spec, parent = self.rows[key], self.keys[key], self.parent[key]
        requests = self.requests(key)
        captures, assertions = self.capture_records(key)
        outcome = self.acquisition["outcomes"][key]
        lines = [record_line(af.disposition_record(self.order.index(key), key, row, spec["candidate_url"],
                                                   spec["game_id_literal"], outcome, requests, captures,
                                                   parent["values"]))]
        lines += [record_line(af.request_record(request, spec["game_id_literal"], lambda sha: read_raw(self.root, sha)))
                  for request in requests]
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


def build_database(path: Path, payloads: dict[str, bytes], meta: dict[str, str], *, table_sql: str = TABLE_SQL,
                   per_acquisition_requests: bool = False) -> dict[str, Any]:
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA page_size = 4096")
        conn.execute("PRAGMA journal_mode = OFF")
        conn.executescript(table_sql)
        conn.executemany("INSERT INTO meta VALUES (?, ?)", sorted(meta.items()))
        rows = [(i, r["contest_key"], r["season"], r["a_key"], r["b_key"], r["disposition"], line.rstrip("\n"))
                for i, (r, line) in enumerate((json.loads(x), x) for x in _lines(payloads["dispositions.jsonl"]))]
        conn.executemany("INSERT INTO dispositions VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
        if per_acquisition_requests:
            rows = [(i, r["acquisition_identity"], r["seq"], r["contest_key"], r["kind"], line.rstrip("\n"))
                    for i, (r, line) in enumerate((json.loads(x), x) for x in _lines(payloads["requests.jsonl"]))]
            conn.executemany("INSERT INTO requests VALUES (?, ?, ?, ?, ?, ?)", rows)
        else:
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


# --------------------------------------------------------------------------------------------- expansion (BAT-715)
# Contract BAT-715 EXPANSION V1.0 (Cycle #43 TP43-A01): the 97-key union of the retained 28-key tranche and the 70-key
# missing-prior cohort. The retained V1.2 acquisition (zero new requests), its journal and every raw body it names are
# copied byte-identically into the expansion root; the expansion acquisition covers the 70 cohort keys only, under its
# own policy, journal and 320-request ceiling. Materialization reads both acquisitions in that order. Every V1.2
# function above keeps its exact behaviour; a V1.2 contract never reaches this section.

EXPANSION_PRODUCER = "national_archived_publication_expansion/1.0.0"
EXPANSION_POPULATION = "national_archived_publication_2019_expansion"
EXPANSION_CONTRACT_SCHEMA = "1.0.0"
EXPANSION_CONTRACT_ID_PREFIX = "BAT-715-NATIONAL-ARCHIVED-PUBLICATION-2019-EXPANSION-"
EXPANSION_CONTRACT_ID = EXPANSION_CONTRACT_ID_PREFIX + "V1.0"
EXPANSION_PAYLOAD_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-PAYLOAD-3"
EXPANSION_CONTENT_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-CONTENT-3"
EXPANSION_DATABASE_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-DATABASE-3"
EXPANSION_DB_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-DB-3"
EXPANSION_CHECKPOINT_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-CHECKPOINT-2"
EXPANSION_AUTHORITY = {**AUTHORITY, "scope": "BOUNDED_2019_UNION_97_CONTESTS_RETAINED_TRANCHE_28_PLUS_MISSING_PRIOR_"
                                             "COHORT_70_NOT_NATIONAL_COVERAGE"}
EXPANSION_MAX_TOTAL_REQUESTS = 320
EXPANSION_MIN_SPACING_SECONDS = 1.05
EXPANSION_RECORD_FIELDS: dict[str, tuple[str, ...]] = {
    **RECORD_FIELDS,
    "archive_request": RECORD_FIELDS["archive_request"] + ("acquisition_identity",),
    "archive_disposition": RECORD_FIELDS["archive_disposition"] + ("selection_sources", "acquisition_outcomes",
                                                                   "duplicate_versions")}
EXPANSION_TABLE_SQL = TABLE_SQL.replace(
    "CREATE TABLE requests (ord INTEGER PRIMARY KEY, seq INTEGER NOT NULL UNIQUE, contest_key TEXT NOT NULL,"
    " kind TEXT NOT NULL, record TEXT NOT NULL);",
    "CREATE TABLE requests (ord INTEGER PRIMARY KEY, acquisition_identity TEXT NOT NULL, seq INTEGER NOT NULL,"
    " contest_key TEXT NOT NULL, kind TEXT NOT NULL, record TEXT NOT NULL, UNIQUE (acquisition_identity, seq));")
assert EXPANSION_TABLE_SQL != TABLE_SQL
RETAINED_ORIGIN = "RETAINED_V1_2_ACQUISITION_ZERO_NEW_REQUESTS"
EXPANSION_ORIGIN = "EXPANSION_ACQUISITION_COHORT_70"


def contract_id_of(path: Path) -> str | None:
    try:
        return json.loads(Path(path).read_bytes().decode("utf-8")).get("contract_id")
    except (OSError, UnicodeDecodeError, ValueError, AttributeError):
        return None


def load_expansion_contract(path: Path) -> tuple[dict[str, Any], str]:
    raw = Path(path).read_bytes()
    try:
        contract = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BuildRefused("CONTRACT_INVALID", str(exc)) from exc
    if contract.get("schema_version") != EXPANSION_CONTRACT_SCHEMA or contract.get("contract_id") != EXPANSION_CONTRACT_ID:
        raise BuildRefused("CONTRACT_SCHEMA_UNKNOWN", f"{contract.get('schema_version')} {contract.get('contract_id')}")
    mapping = contract.get("participant_mapping") or {}
    if mapping.get("numeric_identifier_equality") != "NEVER_AUTHORITY" or mapping.get("rule") != af.MAPPING_RULE \
            or mapping.get("capture_quarantine") != af.QUARANTINE_RULE:
        raise BuildRefused("CONTRACT_SCHEMA_UNKNOWN", "participant mapping rule")
    if contract.get("population_id") != EXPANSION_POPULATION:
        raise BuildRefused("CONTRACT_SCHEMA_UNKNOWN", "population")
    if contract.get("row_labels") != EXPANSION_AUTHORITY:
        raise BuildRefused("AUTHORITY_LABELS_INVALID", "row labels differ from the evidence-only expansion labels")
    if contract.get("authority", {}).get("pit_admission") != AUTHORITY["pit_admission"]:
        raise BuildRefused("FORGED_PIT_AUTHORITY", "the contract claims a PIT admission authority")
    if tuple(contract.get("extraction", {}).get("fields", {}).get("order") or ()) != FIELDS:
        raise BuildRefused("CONTRACT_SCHEMA_UNKNOWN", "field order")
    if contract.get("duplicate_versions", {}).get("rule") != af.DUPLICATE_RULE:
        raise BuildRefused("CONTRACT_SCHEMA_UNKNOWN", "duplicate version rule")
    limits = contract["acquisition"]["limits"]
    if (limits["metadata_requests_per_key"], limits["replay_requests_per_key"], limits["max_concurrency"]) != (2, 2, 1) \
            or limits["total_requests"] > EXPANSION_MAX_TOTAL_REQUESTS \
            or limits["min_seconds_between_request_starts"] < EXPANSION_MIN_SPACING_SECONDS \
            or not isinstance(limits.get("max_body_bytes"), int) or limits["max_body_bytes"] < 1:
        raise BuildRefused("ACQUISITION_POLICY_INVALID", "limits exceed the TP43-A01 grant")
    hosts = contract["acquisition"]["hosts"]
    if (hosts["metadata"]["host"], hosts["replay"]["host"]) != ALLOWED_HOSTS:
        raise BuildRefused("ACQUISITION_POLICY_INVALID", "hosts differ from the granted archive hosts")
    retained = contract.get("parent_binding", {}).get("retained_acquisition") or {}
    if not all(isinstance(retained.get(k), str) for k in ("identity", "policy_id", "contract_id", "contract_sha256")):
        raise BuildRefused("CONTRACT_INVALID", "parent_binding.retained_acquisition")
    return contract, sha256_bytes(raw)


def _game_literal(url: str) -> str:
    return urllib.parse.urlsplit(url).path.rsplit("/", 1)[-1]


def verify_expansion_scope(contract: dict[str, Any], tranche_path: Path, cohort_path: Path) -> list[dict[str, Any]]:
    """The 97-key union from the exact issued tranche and cohort bytes: every declared key spec must equal the row it
    comes from; the union order is the tranche order, then the cohort's new keys in cohort order. Returns one row per
    union key (tranche-derived fields for tranche keys; parent fields are filled from the parent database later)."""
    scope = contract["scope"]
    traw, craw = Path(tranche_path).read_bytes(), Path(cohort_path).read_bytes()
    if sha256_bytes(traw) != scope["tranche_sha256"]:
        raise BuildRefused("TRANCHE_MISMATCH", "tranche bytes differ from the contract binding")
    if sha256_bytes(craw) != scope["cohort_sha256"]:
        raise BuildRefused("COHORT_MISMATCH", "cohort bytes differ from the contract binding")
    tranche, cohort = json.loads(traw.decode("utf-8")), json.loads(craw.decode("utf-8"))
    trows, crows = tranche.get("selected") or [], cohort.get("selected") or []
    tkeys, ckeys = [r.get("contest_key") for r in trows], [r.get("contest_key") for r in crows]
    if len(trows) != scope["tranche_count"] or tranche.get("count") != scope["tranche_count"] or \
            len(set(tkeys)) != len(tkeys):
        raise BuildRefused("TRANCHE_KEYS_INVALID", "duplicate, missing or extra tranche keys")
    if len(crows) != scope["cohort_count"] or (cohort.get("counts") or {}).get("new_query_keys") != len(crows) or \
            len(set(ckeys)) != len(ckeys) or ckeys != scope["cohort_keys"]:
        raise BuildRefused("COHORT_KEYS_INVALID", "duplicate, missing, extra or reordered cohort keys")
    tset = set(tkeys)
    union = tkeys + [k for k in ckeys if k not in tset]
    overlap = [k for k in ckeys if k in tset]
    if len(union) != scope["union_count"] or overlap != scope["overlap_keys"] or \
            [k.get("contest_key") for k in scope["keys"]] != union:
        raise BuildRefused("SCOPE_KEYS_INVALID", "the declared union keys differ from tranche + cohort")
    tby, cby = dict(zip(tkeys, trows)), dict(zip(ckeys, crows))
    rows = []
    for spec in scope["keys"]:
        key = spec["contest_key"]
        t, c = tby.get(key), cby.get(key)
        sources = [name for name, row in zip(af.SELECTION_SOURCES, (t, c)) if row is not None]
        url = spec["candidate_url"]
        game = _game_literal(url)
        problems = []
        if spec.get("selection_sources") != sources:
            problems.append("selection_sources")
        if game != spec["game_id_literal"] or not equivalent_original(url, game):
            problems.append("candidate locator")
        if t is not None:
            if (spec["selection_role"], spec["stratum"], spec["retained_probe_1_timestamp"], url) != (
                    t["selection_role"], t["stratum"], t["metadata_probe_timestamp"], t["candidate_espn_url"]):
                problems.append("tranche row")
            if t["season"] != scope["season"]:
                raise BuildRefused("OUT_OF_TRANCHE_SEASON", key)
        elif (spec["selection_role"], spec["stratum"], spec["retained_probe_1_timestamp"]) != (
                af.COHORT_ROLE, af.COHORT_STRATUM, None):
            problems.append("cohort-only role/stratum")
        if c is not None:
            probes = c.get("metadata_probe_timestamps")
            if spec["expansion_probe_timestamps"] != probes or c["candidate_espn_url"] != url or \
                    bool(c.get("already_in_original_tranche")) != (t is not None) or \
                    not (isinstance(probes, list) and len(probes) == 2 and all(TS14_RE.match(str(p)) for p in probes)
                         and probes[1] <= probes[0]):
                problems.append("cohort row")
            if str(c["contest_date"])[:4] != str(scope["season"]):
                raise BuildRefused("OUT_OF_COHORT_SEASON", key)
        elif spec["expansion_probe_timestamps"] is not None:
            problems.append("tranche-only key with expansion probes")
        if t is not None and c is not None and (t["contest_date"], t["a_key"], t["b_key"], t["cfbd_game_id"]) != (
                c["contest_date"], c["a_key"], c["b_key"], c["cfbd_game_id"]):
            problems.append("tranche and cohort rows disagree")
        if problems:
            raise BuildRefused("SCOPE_KEYS_INVALID", f"{key}: {problems}")
        base = t if t is not None else c
        rows.append({"contest_key": key, "selection_sources": sources, "selection_role": spec["selection_role"],
                     "stratum": spec["stratum"], "classification_pair": t["classification_pair"] if t else None,
                     "season": t["season"] if t else None, "contest_date": base["contest_date"],
                     "a_key": base["a_key"], "b_key": base["b_key"], "cfbd_game_id": base["cfbd_game_id"],
                     "a_points": t["a_points"] if t else None, "b_points": t["b_points"] if t else None})
    controls = [r["contest_key"] for r in rows if r["selection_role"] == af.CONTROL_ROLE]
    if controls != [scope["control_contest_key"]]:
        raise BuildRefused("SCOPE_KEYS_INVALID", "control key")
    return rows


def verify_expansion_bindings(contract: dict[str, Any], path: Path, parent: dict[str, Any], tranche_path: Path,
                              cohort_path: Path, database: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    if sha256_bytes(raw) != contract["parent_binding"]["source_bindings"]["sha256"]:
        raise BuildRefused("SOURCE_BINDINGS_MISMATCH", "binding document bytes differ from the contract")
    doc = json.loads(raw.decode("utf-8"))
    st = doc.get("source_time_database") or {}
    if (st.get("sha256"), st.get("identity")) != (parent["sqlite_sha256"], parent["database_identity"]) or \
            Path(st.get("path", "")).resolve() != Path(database).resolve():
        raise BuildRefused("SOURCE_BINDINGS_MISMATCH", "bindings name another source-time database")
    tr, co = doc.get("tranche") or {}, doc.get("expansion_cohort") or {}
    scope = contract["scope"]
    if (tr.get("sha256"), tr.get("count")) != (scope["tranche_sha256"], scope["tranche_count"]) or \
            Path(tr.get("path", "")).resolve() != Path(tranche_path).resolve():
        raise BuildRefused("SOURCE_BINDINGS_MISMATCH", "bindings name another tranche")
    if (co.get("sha256"), co.get("missing_prior_contests")) != (scope["cohort_sha256"], scope["cohort_count"]) or \
            co.get("union_archive_contests") != scope["union_count"] or \
            Path(co.get("path", "")).resolve() != Path(cohort_path).resolve():
        raise BuildRefused("SOURCE_BINDINGS_MISMATCH", "bindings name another expansion cohort")
    if (doc.get("control") or {}).get("sha256") != contract["parent_binding"]["route_control"]["sha256"]:
        raise BuildRefused("SOURCE_BINDINGS_MISMATCH", "bindings name another route control")
    if doc.get("prior_archive_acquisition_identity") != contract["parent_binding"]["retained_acquisition"]["identity"]:
        raise BuildRefused("SOURCE_BINDINGS_MISMATCH", "bindings name another retained acquisition")
    return {"path": str(path), "sha256": sha256_bytes(raw), "control_path": doc["control"]["path"]}


def read_parent_union(database: Path, rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Accepted parent values and participant sources for every union key (as ``read_parent``). A tranche row must
    also equal the parent's points; a cohort-only row carries no outcome (its selection never looked at results), so
    its season comes from the parent record."""
    conn = sqlite3.connect(Path(database).resolve().as_uri() + "?mode=ro", uri=True)
    out: dict[str, dict[str, Any]] = {}
    try:
        for row in rows:
            found = conn.execute("SELECT record, assertions, lineage FROM contests WHERE contest_key = ?",
                                 (row["contest_key"],)).fetchone()
            if found is None:
                raise BuildRefused("SCOPE_PARENT_MISMATCH", f"{row['contest_key']} is not a source-time contest")
            record = json.loads(found[0])
            values: dict[str, set] = {}
            for line in zlib.decompress(found[1]).decode("utf-8").splitlines():
                item = json.loads(line)
                values.setdefault(item["field"], set()).add(json.dumps(item["parent_value"], sort_keys=True))
            if any(len(v) != 1 for v in values.values()) or set(values) != set(FIELDS):
                raise BuildRefused("SCOPE_PARENT_MISMATCH", f"{row['contest_key']} parent values are not single")
            parent_values = {f: json.loads(next(iter(values[f]))) for f in FIELDS}
            if row["season"] is None:
                row["season"] = record["season"]
            expected = (row["season"], row["contest_date"], row["a_key"], row["b_key"], row["cfbd_game_id"]["value"])
            observed = (record["season"], record["contest_date"], record["a_key"], record["b_key"],
                        record["cfbd_game_id"]["value"])
            if expected != observed or ("TRANCHE_28" in row["selection_sources"] and (
                    parent_values["a_points"], parent_values["b_points"]) != (row["a_points"], row["b_points"])):
                raise BuildRefused("SCOPE_PARENT_MISMATCH", f"{row['contest_key']} differs from the parent")
            if record["a_cfbd_team_id"].get("namespace") != "CFBD_TEAM_ID" or \
                    record["b_cfbd_team_id"].get("namespace") != "CFBD_TEAM_ID":
                raise BuildRefused("SCOPE_PARENT_MISMATCH", f"{row['contest_key']} team id namespace")
            lineage = [json.loads(line) for line in zlib.decompress(found[2]).decode("utf-8").splitlines()]
            out[row["contest_key"]] = {"record": record, "values": parent_values,
                                       "participants": af.participant_sources(record, lineage)}
    finally:
        conn.close()
    return out


def _copy_create_only(target: Path, data: bytes) -> str:
    """Create ``target`` with exactly ``data``; an existing file must already hold identical bytes."""
    target = Path(target)
    if target.exists():
        if target.read_bytes() != data:
            raise BuildRefused("REFUSED_IMMUTABLE_COLLISION", str(target))
        return "PRESENT_IDENTICAL"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".tmp-{sha256_bytes(data)[:16]}-{os.getpid()}-{time.time_ns()}")
    with temporary.open("xb") as handle:
        handle.write(data)
    os.replace(temporary, target)
    return "COPIED"


def _retained_requirements(contract: dict[str, Any], doc: dict[str, Any], scope_keys: list[str]) -> None:
    spec = contract["parent_binding"]["retained_acquisition"]
    if doc.get("schema") != ACQUISITION_SCHEMA or doc.get("policy_id") != spec["policy_id"] or \
            doc.get("contract_id") != spec["contract_id"] or \
            doc.get("tranche_sha256") != contract["scope"]["tranche_sha256"] or doc.get("keys") != scope_keys or \
            len(doc.get("requests") or []) != spec["requests"]:
        raise BuildRefused("RETAINED_ACQUISITION_INVALID", "the retained acquisition is not the bound V1.2 acquisition")


def import_retained(contract: dict[str, Any], retained_root: Path, output_root: Path) -> dict[str, Any]:
    """Copy the bound retained V1.2 acquisition document, its journal files and every raw body it names (plus the
    route-control raw bytes) create-only and byte-identically into the expansion root. Zero requests."""
    spec = contract["parent_binding"]["retained_acquisition"]
    ident = spec["identity"]
    source = Path(retained_root)
    data = (source / "acquisition" / "sha256" / ident / "acquisition.json").read_bytes()
    if sha256_bytes(data) != ident:
        raise BuildRefused("RETAINED_ACQUISITION_ALTERED", "the retained acquisition does not hash to its identity")
    doc = json.loads(data.decode("utf-8"))
    tranche_keys = [k["contest_key"] for k in contract["scope"]["keys"] if "TRANCHE_28" in k["selection_sources"]]
    _retained_requirements(contract, doc, tranche_keys)
    states: dict[str, int] = {}
    total = 0
    files: list[tuple[str, bytes]] = [(f"acquisition/sha256/{ident}/acquisition.json", data)]
    for name, sha in sorted(spec["journal_files"].items()):
        rel = f"acquisition/journal/{spec['policy_id']}/{name}"
        blob = (source / Path(*rel.split("/"))).read_bytes()
        if sha256_bytes(blob) != sha:
            raise BuildRefused("RETAINED_ACQUISITION_ALTERED", rel)
        files.append((rel, blob))
    bodies = sorted({r["body_sha256"] for r in doc["requests"] if r.get("body_sha256")} |
                    {doc["control"][k] for k in ("payload_sha256", "raw_receipt_sha256", "route_qualification_sha256")})
    for sha in bodies:
        files.append((raw_rel(sha), read_raw(source, sha)))
    for rel, blob in files:
        state = _copy_create_only(Path(output_root) / Path(*rel.split("/")), blob)
        states[state] = states.get(state, 0) + 1
        total += len(blob)
    return {"identity": ident, "document": doc, "files": len(files), "states": states, "bytes": total,
            "new_requests": 0}


def load_retained(contract: dict[str, Any], root: Path) -> tuple[str, dict[str, Any]]:
    ident = contract["parent_binding"]["retained_acquisition"]["identity"]
    path = Path(root) / "acquisition" / "sha256" / ident / "acquisition.json"
    if not path.is_file():
        raise BuildRefused("RETAINED_ACQUISITION_MISSING", str(path))
    doc = load_acquisition(path, root)
    tranche_keys = [k["contest_key"] for k in contract["scope"]["keys"] if "TRANCHE_28" in k["selection_sources"]]
    _retained_requirements(contract, doc, tranche_keys)
    for request in doc["requests"]:
        if request.get("body_sha256"):
            read_raw(root, request["body_sha256"])
    return ident, doc


def acquisition_view(contract: dict[str, Any]) -> dict[str, Any]:
    """The expansion acquisition's own contract view: its acquisition section and the 70 cohort keys in cohort order.
    Its policy id is sha256 of {acquisition section, cohort sha256}; the journal and the document bind it."""
    scope = contract["scope"]
    specs = {k["contest_key"]: k for k in scope["keys"]}
    keys = [{"contest_key": key, "selection_role": af.COHORT_ROLE, "candidate_url": specs[key]["candidate_url"],
             "game_id_literal": specs[key]["game_id_literal"],
             "expansion_probe_timestamps": specs[key]["expansion_probe_timestamps"]} for key in scope["cohort_keys"]]
    return {"contract_id": contract["contract_id"], "acquisition": contract["acquisition"],
            "scope": {"tranche_sha256": scope["cohort_sha256"], "keys": keys,
                      "control_contest_key": scope["control_contest_key"]}}


def retained_versions(doc: dict[str, Any]) -> dict[str, frozenset[str]]:
    """Per key, the wayback timestamps of the versions the retained acquisition already replayed (HTTP 200)."""
    out: dict[str, set[str]] = {}
    for request in doc["requests"]:
        if af.capture_request(request):
            parts = replay_parts(request["url"])
            if parts:
                out.setdefault(request["contest_key"], set()).add(parts[0])
    return {k: frozenset(v) for k, v in out.items()}


def _replay_chain(chain: list[dict[str, Any]], target: tuple[str, str], purpose: str, budget: int, cap: int,
                  game: str, retained: frozenset[str]) -> tuple[tuple[str, str, str] | None, int]:
    """One replay chain: the target replay and at most one follow-up (RETRY of a transient failure or one
    REDIRECT_HOP to an equivalent original). Returns (next step or None when the chain is done, replays consumed)."""
    if budget <= 0:
        return None, 0
    if not chain:
        return ("REPLAY", purpose, replay_url(target[0], target[1])), 0
    first = chain[0]
    if transient(first):
        if len(chain) == 1:
            if budget >= 2 and retry_allowed(first, cap):
                return ("REPLAY", "RETRY", first["url"]), 1
            return None, 1
        return None, 2
    if first["http_status"] in REDIRECT_STATUS:
        if len(chain) == 1:
            location = first["location"] or ""
            hop = replay_parts(urllib.parse.urljoin(first["url"], location)) if location else None
            if budget >= 2 and hop and equivalent_original(hop[1], game) and hop[0] not in retained:
                return ("REPLAY", "REDIRECT_HOP", replay_url(hop[0], hop[1])), 1
            return None, 1
        return None, 2
    return None, 1


def _answer(record: dict[str, Any] | None, read_body: Callable[[dict[str, Any]], bytes],
            game: str) -> dict[str, Any] | None:
    if record is None or record["http_status"] != 200:
        return None
    answer = metadata_answer(read_body(record), game)
    return answer if answer["usable"] else None


def plan_next_expansion(key: dict[str, Any], history: list[dict[str, Any]], contract: dict[str, Any],
                        read_body: Callable[[dict[str, Any]], bytes],
                        retained: frozenset[str] = frozenset()) -> tuple[str, str, str] | None:
    """The next expansion request for one cohort key (pure and deterministic): (kind, purpose, url).

    PROBE_1 asks for the version nearest one second before the earliest dependent target's conservative boundary
    (a transient failure is retried once at the same timestamp, which closes PROBE_2). The answered version is replayed
    (CAPTURE_1) unless the retained acquisition already replayed that exact timestamp. PROBE_2, at the cohort's second
    timestamp, is asked only when it differs from the first and the first answer gave no usable version, a version
    later than the first timestamp or earlier than the second, or a replay that did not answer HTTP 200. Its version is
    replayed (CAPTURE_2) only when it is a different timestamp, not retained, and replay capacity remains."""
    cap = contract["acquisition"]["limits"]["retry_after_cap_seconds"]
    budget = contract["acquisition"]["limits"]["replay_requests_per_key"]
    game, candidate = key["game_id_literal"], key["candidate_url"]
    probe1, probe2 = key["expansion_probe_timestamps"]
    metas = [r for r in history if r["kind"] == "METADATA"]
    replays = [r for r in history if r["kind"] == "REPLAY"]
    if not metas:
        return "METADATA", "PROBE_1", metadata_url(candidate, probe1)
    if transient(metas[0]):
        if len(metas) < 2:
            return ("METADATA", "RETRY", metadata_url(candidate, probe1)) if retry_allowed(metas[0], cap) else None
        first, probe2_open = metas[1], False
    else:
        first, probe2_open = metas[0], probe2 != probe1
    answer1 = _answer(first, read_body, game)
    t1 = (answer1["timestamp"], answer1["original"]) if answer1 else None
    used = 0
    replayed_ok = False
    if t1 is not None and t1[0] not in retained:
        step, used = _replay_chain(replays, t1, "CAPTURE_1", budget, cap, game, retained)
        if step is not None:
            return step
        replayed_ok = any(r["http_status"] == 200 for r in replays[:used])
    in_window = t1 is not None and probe2 <= t1[0] <= probe1
    first_version_ok = t1 is not None and (t1[0] in retained or replayed_ok)
    if not probe2_open or (in_window and first_version_ok):
        return None
    if len(metas) < 2:
        return "METADATA", "PROBE_2", metadata_url(candidate, probe2)
    answer2 = _answer(metas[1], read_body, game)
    if answer2 is None:
        return None
    t2 = (answer2["timestamp"], answer2["original"])
    if (t1 is not None and t2[0] == t1[0]) or t2[0] in retained:
        return None
    step, _ = _replay_chain(replays[used:], t2, "CAPTURE_2", budget - used, cap, game, retained)
    return step


def expansion_outcome(key: dict[str, Any], history: list[dict[str, Any]], exhausted: bool,
                      read_body: Callable[[dict[str, Any]], bytes], retained: frozenset[str]) -> str:
    """The V1.2 outcome, except that a key whose usable answers named only versions the retained acquisition had
    already replayed (and which got no new HTTP 200 replay) is RETAINED_VERSION_REUSED."""
    outcome = acquisition_outcome(key, history, exhausted)
    if outcome == "CAPTURED" or not retained:
        return outcome
    named = {a["timestamp"] for a in (_answer(r, read_body, key["game_id_literal"]) for r in history
                                      if r["kind"] == "METADATA") if a}
    return "RETAINED_VERSION_REUSED" if named and named <= retained else outcome


def capture_expansion(contract: dict[str, Any], output_root: Path, control: dict[str, Any],
                      retained_doc: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """The expansion acquisition (the only networked step): the 70 cohort keys in cohort order through ``capture``
    with the expansion planner, outcome and body limit, under the expansion policy and journal."""
    view = acquisition_view(contract)
    retained = retained_versions(retained_doc)
    root = Path(output_root)
    limit = contract["acquisition"]["limits"]["max_body_bytes"]

    def read_body(record: dict[str, Any]) -> bytes:
        return read_raw(root, record["body_sha256"])

    def planner(key: dict[str, Any], history: list[dict[str, Any]], _contract: dict[str, Any],
                reader: Callable[[dict[str, Any]], bytes]) -> tuple[str, str, str] | None:
        return plan_next_expansion(key, history, view, reader, retained.get(key["contest_key"], frozenset()))

    def outcome_of(key: dict[str, Any], history: list[dict[str, Any]], exhausted: bool) -> str:
        return expansion_outcome(key, history, exhausted, read_body, retained.get(key["contest_key"], frozenset()))
    if kwargs.get("transport") is None:
        # capture() installs the network audit only for its own default transport; the body-limited real transport
        # is passed explicitly, so the audit hook is installed here (finding F43A01-03: the first real capture ran
        # without it; its journal shows archive.org requests only).
        if kwargs.get("audit", True):
            journal_dir = root / "acquisition" / "journal" / policy_id(view)
            journal_dir.mkdir(parents=True, exist_ok=True)
            install_network_audit(journal_dir / "network_audit.jsonl")
        kwargs["transport"] = lambda url, headers, timeout: urllib_transport(url, headers, timeout, max_bytes=limit)
    rows = [{"contest_key": k["contest_key"]} for k in view["scope"]["keys"]]
    return capture(view, rows, root, control, planner=planner, outcome_of=outcome_of, **kwargs)


def verify_expansion_acquisition(view: dict[str, Any], doc: dict[str, Any], output_root: Path,
                                 control: dict[str, Any]) -> None:
    """``verify_acquisition`` over the expansion view (cohort keys, cohort sha256, 320-request ceiling)."""
    verify_acquisition(view, doc, output_root, control)
    if doc.get("contract_id") != view["contract_id"]:
        raise BuildRefused("ACQUISITION_KEYS_INVALID", "acquisition contract id")


class ExpansionModel:
    """Bundles of the 97 union keys from the ordered acquisitions (retained V1.2 first, then the expansion)."""

    def __init__(self, contract: dict[str, Any], rows: list[dict[str, Any]], parent: dict[str, dict[str, Any]],
                 acquisitions: list[tuple[str, dict[str, Any]]], output_root: Path, control: dict[str, Any]) -> None:
        self.contract = contract
        self.rows = {r["contest_key"]: r for r in rows}
        self.order = [k["contest_key"] for k in contract["scope"]["keys"]]
        self.keys = {k["contest_key"]: k for k in contract["scope"]["keys"]}
        self.parent = parent
        self.acquisitions = acquisitions
        self.root = Path(output_root)
        self.control = control

    def read(self, sha: str) -> bytes:
        return read_raw(self.root, sha)

    def outcomes(self, key: str) -> list[dict[str, str]]:
        return [{"acquisition_identity": ident, "acquisition_outcome": doc["outcomes"][key]}
                for ident, doc in self.acquisitions if key in doc["outcomes"]]

    def requests(self, key: str) -> list[tuple[str, dict[str, Any]]]:
        return [(ident, r) for ident, doc in self.acquisitions for r in doc["requests"] if r["contest_key"] == key]

    def capture_records(self, key: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        spec = self.keys[key]
        game = spec["game_id_literal"]
        parent = self.parent[key]
        control = None
        if spec["selection_role"] == af.CONTROL_ROLE:
            control = af.control_version(sha256_bytes(self.control["receipt_raw"]), self.control["receipt"],
                                         self.control["payload"])
        entries, duplicates = af.expansion_versions(key, control, self.acquisitions, self.read)
        captures, assertions = [], []
        for entry in entries:
            capture_record, rows = af.derive_capture(key, parent, game, entry["version"], entry["payload_sha256"])
            captures.append(capture_record)
            assertions += rows
        captures = af.order_captures(captures)
        return captures, af.order_assertions(captures, assertions), duplicates

    def bundle(self, key: str) -> bytes:
        row, spec, parent = self.rows[key], self.keys[key], self.parent[key]
        requests = self.requests(key)
        captures, assertions, duplicates = self.capture_records(key)
        record = af.expansion_disposition_record(self.order.index(key), key, row, spec["candidate_url"],
                                                 spec["game_id_literal"], self.outcomes(key),
                                                 [r for _, r in requests], captures, duplicates, parent["values"])
        lines = [record_line(record, EXPANSION_RECORD_FIELDS)]
        lines += [record_line(af.expansion_request_record(ident, r, spec["game_id_literal"], self.read),
                              EXPANSION_RECORD_FIELDS) for ident, r in requests]
        lines += [record_line(c, EXPANSION_RECORD_FIELDS) for c in captures]
        lines += [record_line(a, EXPANSION_RECORD_FIELDS) for a in assertions]
        return b"".join(lines)


def build_expansion(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    contract, contract_sha = load_expansion_contract(args.contract)
    if args.chunk_size < 0 or (args.stop_after_chunks is not None and args.stop_after_chunks < 1):
        raise BuildRefused("ARGUMENT_INVALID", "chunk size and stop-after must be positive")
    if (args.resume or args.stop_after_chunks is not None) and not args.checkpoint_dir:
        raise BuildRefused("ARGUMENT_INVALID", "--resume and --stop-after-chunks need --checkpoint-dir")
    if args.checkpoint_dir and args.chunk_size < 1:
        raise BuildRefused("ARGUMENT_INVALID", "--checkpoint-dir needs --chunk-size >= 1")
    if not INPUT_ORDER.match(args.input_order):
        raise BuildRefused("INPUT_ORDER_INVALID", args.input_order)
    if args.cohort is None:
        raise BuildRefused("ARGUMENT_INVALID", "the expansion contract needs --cohort")
    parent = verify_source_database(contract, args.source_database)
    rows = verify_expansion_scope(contract, args.tranche, args.cohort)
    bindings = verify_expansion_bindings(contract, args.source_bindings, parent, args.tranche, args.cohort,
                                         args.source_database)
    control = verify_control(contract, Path(bindings["control_path"]))
    parent_values = read_parent_union(args.source_database, rows)
    output_root = Path(args.output_root)
    evidence_root = Path(args.evidence_root) if args.evidence_root else output_root
    view = acquisition_view(contract)
    pid = policy_id(view)
    capture_result = retained_result = None
    if args.stage in ("capture", "all"):
        if evidence_root.resolve() != output_root.resolve():
            raise BuildRefused("ARGUMENT_INVALID", "capture writes its evidence into the output root only")
        if args.retained_root is None:
            raise BuildRefused("ARGUMENT_INVALID", "the expansion capture needs --retained-root")
        service = None
        if args.capture_policy is not None:
            service = prepare_capture_service(args.capture_policy, contract_id=contract["contract_id"],
                                              contract_sha=contract_sha, pid=pid,
                                              keys=[k["contest_key"] for k in view["scope"]["keys"]],
                                              total=view["acquisition"]["limits"]["total_requests"],
                                              output_root=output_root)
        retained_result = import_retained(contract, args.retained_root, output_root)
        if service is None:
            capture_result = capture_expansion(contract, output_root, control, retained_result["document"],
                                               audit=not args.no_network_audit)
        else:
            capture_result = capture_expansion_service(contract, output_root, control, retained_result["document"],
                                                       service, audit=not args.no_network_audit,
                                                       acknowledge=args.acknowledge_unknown_intent)
        retained_summary = {k: v for k, v in retained_result.items() if k != "document"}
        if args.stage == "capture" or capture_result["state"] not in FINAL_CAPTURE_STATES:
            return {"state": "CAPTURE_" + capture_result["state"], "capture": capture_result,
                    "retained": retained_summary, "policy_id": pid, "contract_sha256": contract_sha,
                    "seconds": round(time.time() - started, 3)}
    retained_id, retained_doc = load_retained(contract, evidence_root)
    acquisition_path, acquisition = find_acquisition(evidence_root, pid, args.acquisition)
    acquisition_id = acquisition_path.parent.name
    verify_expansion_acquisition(view, acquisition, evidence_root, control)
    retained_pid = contract["parent_binding"]["retained_acquisition"]["policy_id"]
    model = ExpansionModel(contract, rows, parent_values, [(retained_id, retained_doc), (acquisition_id, acquisition)],
                           evidence_root, control)
    keys = permute([k["contest_key"] for k in contract["scope"]["keys"]], args.input_order)
    parent_doc = {"source_time": parent}
    control_doc = {"contest_key": contract["scope"]["control_contest_key"],
                   "route_qualification_sha256": sha256_bytes(control["route_raw"]),
                   "raw_receipt_sha256": sha256_bytes(control["receipt_raw"]),
                   "payload_sha256": sha256_bytes(control["payload"])}
    acquisitions_doc = [{"acquisition_identity": retained_id, "policy_id": retained_pid, "origin": RETAINED_ORIGIN},
                        {"acquisition_identity": acquisition_id, "policy_id": pid, "origin": EXPANSION_ORIGIN}]
    checkpoint = None
    if args.checkpoint_dir:
        header_doc = {"schema": EXPANSION_CHECKPOINT_SCHEMA, "contract_sha256": contract_sha, "parent": parent_doc,
                      "tranche_sha256": contract["scope"]["tranche_sha256"],
                      "cohort_sha256": contract["scope"]["cohort_sha256"], "acquisitions": acquisitions_doc,
                      "payload_schema": EXPANSION_PAYLOAD_SCHEMA, "chunk_size": args.chunk_size,
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
    conflicts = af.mapping_conflicts([json.loads(line) for line in payloads["captures.jsonl"].splitlines()])
    if conflicts:
        raise BuildRefused("PARTICIPANT_MAPPING_CONTRADICTORY", f"qualified participant mappings disagree across the "
                                                                f"union: {conflicts[:5]}")
    counts = {name: payloads[name].count(b"\n") for name in PAYLOAD_FILES}
    if counts["dispositions.jsonl"] != contract["scope"]["union_count"] or \
            counts["requests.jsonl"] != len(retained_doc["requests"]) + len(acquisition["requests"]):
        raise BuildRefused("CENSUS_INCOMPLETE", "dispositions or requests do not cover the union/acquisitions")
    semantic = {name: sha256_bytes(payloads[name]) for name in PAYLOAD_FILES}
    packed = {f"{name}.gz": gzip.compress(payloads[name], compresslevel=GZIP_LEVEL, mtime=0) for name in PAYLOAD_FILES}
    content_document = {"schema": EXPANSION_CONTENT_SCHEMA, "stage": "archived-publication-content",
                        "population": EXPANSION_POPULATION, "contract_id": contract["contract_id"],
                        "contract_sha256": contract_sha, "parent": parent_doc,
                        "tranche_sha256": contract["scope"]["tranche_sha256"],
                        "cohort_sha256": contract["scope"]["cohort_sha256"], "acquisition_identity": acquisition_id,
                        "acquisition_policy_id": pid, "acquisitions": acquisitions_doc, "control": control_doc,
                        "payload_schema": EXPANSION_PAYLOAD_SCHEMA,
                        "payload_encoding": "gzip(level 9, mtime 0) of the canonical JSONL; semantic sha256 over the "
                                            "uncompressed bytes",
                        "semantic_outputs": semantic, "outputs": {n: sha256_bytes(d) for n, d in packed.items()},
                        "row_counts": counts}
    content_identity = sha256_bytes(canonical_json_bytes(content_document))
    with tempfile.TemporaryDirectory(prefix="nape-") as work:
        db_path = Path(work) / DB_FILE
        meta = {"schema_version": EXPANSION_DB_SCHEMA, "contract_id": contract["contract_id"],
                "contract_sha256": contract_sha, "content_identity": content_identity,
                "payload_schema": EXPANSION_PAYLOAD_SCHEMA, "semantic_sha256": json.dumps(semantic, sort_keys=True),
                "row_counts": json.dumps(counts, sort_keys=True), "parent": json.dumps(parent_doc, sort_keys=True),
                "tranche_sha256": contract["scope"]["tranche_sha256"],
                "cohort_sha256": contract["scope"]["cohort_sha256"], "acquisition_identity": acquisition_id,
                "acquisition_policy_id": pid, "acquisitions": json.dumps(acquisitions_doc, sort_keys=True),
                "control": json.dumps(control_doc, sort_keys=True),
                "row_labels": json.dumps(EXPANSION_AUTHORITY, sort_keys=True),
                "fields": json.dumps({"order": list(FIELDS), "roles": ROLES, "witnessable": list(WITNESSABLE)},
                                     sort_keys=True),
                "record_homes": json.dumps(RECORD_HOMES, sort_keys=True),
                "origin_date_tolerance_seconds": str(ORIGIN_DATE_TOLERANCE_SECONDS),
                "participant_mapping_rule": af.MAPPING_RULE, "capture_quarantine_rule": af.QUARANTINE_RULE,
                "duplicate_version_rule": af.DUPLICATE_RULE,
                "field_witnesses": json.dumps({f: sorted(w) for f, w in af.FIELD_WITNESSES.items()}, sort_keys=True)}
        db_counts = build_database(db_path, payloads, meta, table_sql=EXPANSION_TABLE_SQL,
                                   per_acquisition_requests=True)
        if db_counts["record_counts"] != counts:
            raise BuildRefused("CENSUS_INCOMPLETE", f"database records {db_counts['record_counts']} != {counts}")
        database_document = {"schema": EXPANSION_DATABASE_SCHEMA, "stage": "archived-publication-database",
                             "population": EXPANSION_POPULATION, "contract_sha256": contract_sha,
                             "content_identity": content_identity, "parent": parent_doc,
                             "db_schema_version": EXPANSION_DB_SCHEMA, "outputs": {DB_FILE: sha256_file(db_path)},
                             "table_counts": db_counts["table_counts"], "record_counts": db_counts["record_counts"]}
        database_identity = sha256_bytes(canonical_json_bytes(database_document))
        provenance = {"producer": EXPANSION_PRODUCER, "producer_path": str(Path(__file__).resolve()),
                      "producer_sha256": sha256_file(Path(__file__)), "argv": list(args.argv),
                      "issued_at_utc": _dt.datetime.now(UTC).replace(microsecond=0).isoformat(),
                      "processing_clock": "nonsemantic run provenance only", "runtime": runtime(),
                      "variant": args.variant, "input_order": args.input_order, "chunk_size": args.chunk_size,
                      "resumed": bool(args.resume), "jira_key": contract.get("jira_key"),
                      "cycle_number": contract.get("cycle_number"), "attempt_number": contract.get("attempt_number"),
                      "source_bindings": bindings, "acquisition": str(acquisition_path),
                      "retained_acquisition": retained_id, "database_identity": database_identity,
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
            "acquisition_policy_id": pid, "acquisitions": acquisitions_doc,
            "acquisition_totals": acquisition["totals"], "retained_totals": retained_doc["totals"],
            "capture": capture_result, "dispositions": tally, "input_order": args.input_order,
            "chunk_size": args.chunk_size, "variant": args.variant, "runtime": runtime(),
            "seconds": round(time.time() - started, 3)}


def build(args: argparse.Namespace) -> dict[str, Any]:
    _service_arguments(args)
    if (contract_id_of(args.contract) or "").startswith(EXPANSION_CONTRACT_ID_PREFIX):
        return build_expansion(args)
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
        if args.capture_policy is None:
            capture_result = capture(contract, rows, output_root, control, audit=not args.no_network_audit)
        else:
            service = prepare_capture_service(args.capture_policy, contract_id=contract["contract_id"],
                                              contract_sha=contract_sha, pid=pid,
                                              keys=[r["contest_key"] for r in rows],
                                              total=contract["acquisition"]["limits"]["total_requests"],
                                              output_root=output_root)
            capture_result = capture_service(contract, rows, output_root, control, service,
                                             audit=not args.no_network_audit,
                                             acknowledge=args.acknowledge_unknown_intent)
        if args.stage == "capture" or capture_result["state"] not in FINAL_CAPTURE_STATES:
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
    conflicts = af.mapping_conflicts([json.loads(line) for line in payloads["captures.jsonl"].splitlines()])
    if conflicts:
        raise BuildRefused("PARTICIPANT_MAPPING_CONTRADICTORY", f"qualified participant mappings disagree across the "
                                                                f"tranche: {conflicts[:5]}")
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
                "origin_date_tolerance_seconds": str(ORIGIN_DATE_TOLERANCE_SECONDS),
                "participant_mapping_rule": af.MAPPING_RULE, "capture_quarantine_rule": af.QUARANTINE_RULE,
                "field_witnesses": json.dumps({f: sorted(w) for f, w in af.FIELD_WITNESSES.items()}, sort_keys=True)}
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


# --------------------------------------------------------------------------------------------- service-aware capture
# BAT-716 (Cycle #44 TP44-A01): the explicitly selected prospective capture policy (--capture-policy). One HTTP 429
# stops the whole acquisition after its response is retained; only a later explicit invocation at or after the
# derived eligible instant resumes it, under the same bound journal, request ceiling and source grant. Specification:
# docs/architecture/ARCHIVE_CAPTURE_SERVICE_PAUSE.md. Without the option every function above keeps its behaviour.

CAPTURE_POLICY_SCHEMA = "BAS-ARCHIVE-CAPTURE-POLICY-1"
SERVICE_JOURNAL_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-JOURNAL-2"
#: Version 2 announces the exact next line before it is appended (C44-CONT-01, MF44A01-01): a journal line after the
#: anchored head is authority only when it is that announced line.
AUTHORITY_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-REQUEST-AUTHORITY-2"
#: A line after the anchored head that the anchor did not announce (an unauthenticated tail).
TAIL_REFUSAL = "CAPTURE_JOURNAL_TAIL_NOT_ANNOUNCED"
#: A decision-bearing line that is not its own derivation from the recorded observations, raw bodies and policy.
DERIVATION_REFUSAL = "CAPTURE_JOURNAL_LINE_NOT_DERIVED"
#: Every rule this implementation performs; a policy naming any other value refuses (the fallback is configurable).
SERVICE_RULES: dict[str, Any] = {
    "mode": "SERVICE_AWARE_PAUSE_RESUME",
    "service_pause_statuses": [429],
    "service_pause_scope": "ACQUISITION_WIDE_STOP_BEFORE_ANY_FURTHER_DISPATCH",
    "retry_after_clock": "RESPONSE_RECEIPT_UTC",
    "retry_after_forms": ["DELTA_SECONDS", "IMF_FIXDATE_GMT", "RFC850_GMT", "ASCTIME_GMT"],
    "retry_after_fallback_cases": ["MISSING", "MALFORMED", "NEGATIVE", "PAST_DATE", "CONFLICTING"],
    "retry_after_cap": "NONE_A_VALID_NONNEGATIVE_DELAY_IS_AUTHORITATIVE",
    "eligibility": "LATEST_RECORDED_PAUSE_AND_NO_CLOCK_BEFORE_THE_LATEST_JOURNAL_INSTANT",
    "resume": "EXPLICIT_INVOCATION_ONLY_NO_COOLDOWN_SLEEP_NO_MONITOR_NO_SELF_DISPATCH",
    "paused_request_planning": "THE_SERVICE_PAUSE_HONOURS_RETRY_AFTER_THE_CONTRACT_PER_KEY_PLAN_AND_LIMITS_ARE_UNCHANGED",
    "unknown_intent": "RECONCILIATION_REQUIRED_EXPLICIT_ACKNOWLEDGEMENT_STAYS_COUNTED",
    "owner": "EXCLUSIVE_OS_FILE_LOCK_PER_ACQUISITION_JOURNAL",
    "journal": "BAS-NATIONAL-ARCHIVED-PUBLICATION-JOURNAL-2_HASH_CHAINED_WITH_ANNOUNCED_TAIL_REQUEST_AUTHORITY_ANCHOR",
    "derived_lines": "INTENT_RESULT_PAUSE_RESUME_KEY_DONE_AND_FINALIZED_RECOMPUTED_FROM_RECORDED_OBSERVATIONS_BEFORE_USE",
    "incomplete_body": "A_SERVICE_PAUSE_STATUS_KEEPS_STATUS_HEADERS_AND_BOUNDED_BODY_OTHER_STATUSES_FAIL_CLOSED",
    "binding": "OUTPUT_ROOT_CONTRACT_ACQUISITION_POLICY_ORDERED_KEYS_TOTAL_REQUESTS"}
BINDING_FIELDS = ("contract_id", "contract_sha256", "acquisition_policy_id", "ordered_keys", "total_requests",
                  "output_root")
SERVICE_PAUSED_EXIT = 4
RECONCILIATION_EXIT = 5
FINAL_CAPTURE_STATES = ("FINALIZED", "ALREADY_FINALIZED")
MAX_INSTANT = _dt.datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=UTC)
SERVICE_LINE_TYPES = ("INTENT", "RESULT", "PAUSE", "RESUME", "ACKNOWLEDGED", "KEY_DONE", "OWNER_START", "OWNER_END",
                      "FINALIZED")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_MONTHS = {name: number for number, name in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}
_MONTH_ALT = "|".join(_MONTHS)
_IMF_FIXDATE = re.compile(r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), ([0-9]{2}) (" + _MONTH_ALT +
                          r") ([0-9]{4}) ([0-9]{2}):([0-9]{2}):([0-9]{2}) GMT")
_RFC850_DATE = re.compile(r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), ([0-9]{2})-(" + _MONTH_ALT +
                          r")-([0-9]{2}) ([0-9]{2}):([0-9]{2}):([0-9]{2}) GMT")
_ASCTIME_DATE = re.compile(r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) (" + _MONTH_ALT +
                           r") ([ 0-9][0-9]) ([0-9]{2}):([0-9]{2}):([0-9]{2}) ([0-9]{4})")


def _root_key(path: Any) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def load_capture_policy(path: Path) -> dict[str, Any]:
    """The explicit capture policy: schema, no claimed request authority, exactly the implemented rules and a positive
    integer fallback, and structurally valid bindings with unique output roots."""
    raw = Path(path).read_bytes()
    try:
        policy = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BuildRefused("CAPTURE_POLICY_INVALID", str(exc)) from exc
    if not isinstance(policy, dict) or policy.get("schema") != CAPTURE_POLICY_SCHEMA:
        raise BuildRefused("CAPTURE_POLICY_INVALID", "schema")
    if policy.get("authorizes_requests") is not False:
        raise BuildRefused("CAPTURE_POLICY_INVALID", "a capture policy cannot claim request authority")
    rules = policy.get("rules")
    if not isinstance(rules, dict) or set(rules) != set(SERVICE_RULES) | {"retry_after_fallback_seconds"}:
        raise BuildRefused("CAPTURE_POLICY_INVALID", "rules fields")
    unsupported = sorted(k for k, v in SERVICE_RULES.items() if rules[k] != v)
    if unsupported:
        raise BuildRefused("CAPTURE_POLICY_INVALID", f"unsupported rules {unsupported}")
    fallback = rules["retry_after_fallback_seconds"]
    if type(fallback) is not int or fallback < 1:
        raise BuildRefused("CAPTURE_POLICY_INVALID", "retry_after_fallback_seconds must be a positive integer")
    bindings = policy.get("acquisitions")
    if not isinstance(bindings, list) or not bindings:
        raise BuildRefused("CAPTURE_POLICY_INVALID", "acquisitions")
    roots: set[str] = set()
    for binding in bindings:
        if not isinstance(binding, dict) or any(f not in binding for f in BINDING_FIELDS):
            raise BuildRefused("CAPTURE_POLICY_INVALID", "binding fields")
        if not (isinstance(binding["contract_id"], str) and isinstance(binding["output_root"], str)
                and binding["output_root"]
                and all(isinstance(binding[f], str) and _HEX64.fullmatch(binding[f])
                        for f in ("contract_sha256", "acquisition_policy_id"))
                and isinstance(binding["ordered_keys"], list) and binding["ordered_keys"]
                and all(isinstance(k, str) for k in binding["ordered_keys"])
                and type(binding["total_requests"]) is int and binding["total_requests"] > 0):
            raise BuildRefused("CAPTURE_POLICY_INVALID", "binding field types")
        root = _root_key(binding["output_root"])
        if root in roots:
            raise BuildRefused("CAPTURE_POLICY_INVALID", "two bindings name one output root")
        roots.add(root)
    return {"policy": policy, "rules": rules, "fallback": fallback, "path": str(path), "sha256": sha256_bytes(raw),
            "rules_identity": sha256_bytes(canonical_json_bytes(rules))}


def prepare_capture_service(path: Path, *, contract_id: str, contract_sha: str, pid: str, keys: list[str],
                            total: int, output_root: Path) -> dict[str, Any]:
    """Select and verify the one binding of ``output_root`` against the actual contract, acquisition policy id,
    ordered keys and ceiling before anything is written."""
    loaded = load_capture_policy(path)
    hits = [b for b in loaded["policy"]["acquisitions"] if _root_key(b["output_root"]) == _root_key(output_root)]
    if not hits:
        raise BuildRefused("CAPTURE_ROOT_NOT_BOUND", f"no capture policy binding names {output_root}")
    binding = hits[0]
    if (binding["contract_id"], binding["contract_sha256"]) != (contract_id, contract_sha):
        raise BuildRefused("CAPTURE_CONTRACT_MISMATCH", "the binding names another contract")
    if binding["acquisition_policy_id"] != pid:
        raise BuildRefused("CAPTURE_ACQUISITION_POLICY_MISMATCH", "the binding names another acquisition policy")
    bound = binding["ordered_keys"]
    duplicates = sorted({k for k in bound if bound.count(k) > 1})
    if duplicates:
        raise BuildRefused("CAPTURE_KEYSET_DUPLICATE", f"duplicate bound keys {duplicates[:5]}")
    if bound != keys:
        missing, extra = [k for k in keys if k not in set(bound)], [k for k in bound if k not in set(keys)]
        raise BuildRefused("CAPTURE_KEYSET_MISMATCH", f"missing {missing[:5]} extra {extra[:5]} "
                                                      f"reordered {not missing and not extra}")
    if binding["total_requests"] != total:
        raise BuildRefused("CAPTURE_LIMIT_MISMATCH", f"bound {binding['total_requests']} != contract {total}")
    normative = {f: binding[f] for f in BINDING_FIELDS}
    return {**loaded, "binding": normative, "binding_identity": sha256_bytes(canonical_json_bytes(normative)),
            "binding_label": binding.get("label"), "contract_sha256": contract_sha}


def http_date_instant(value: str, receipt: _dt.datetime) -> _dt.datetime | None:
    """An IMF-fixdate, RFC 850 (two-digit year interpreted per RFC 9110 against the receipt year) or asctime HTTP
    date as a UTC instant; None for anything else. The weekday name is not used."""
    match = _IMF_FIXDATE.fullmatch(value)
    if match:
        day, month, year = int(match.group(1)), _MONTHS[match.group(2)], int(match.group(3))
        clock_parts = match.group(4, 5, 6)
    else:
        match = _RFC850_DATE.fullmatch(value)
        if match:
            day, month = int(match.group(1)), _MONTHS[match.group(2)]
            year = receipt.year // 100 * 100 + int(match.group(3))
            if year > receipt.year + 50:
                year -= 100
            clock_parts = match.group(4, 5, 6)
        else:
            match = _ASCTIME_DATE.fullmatch(value)
            if not match:
                return None
            month, day, year = _MONTHS[match.group(1)], int(match.group(2).strip()), int(match.group(6))
            clock_parts = match.group(3, 4, 5)
    try:
        return _dt.datetime(year, month, day, *(int(p) for p in clock_parts), tzinfo=UTC)
    except ValueError:
        return None


def _decimal_seconds(delta: _dt.timedelta) -> str:
    micro = (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds
    return f"{micro // 1_000_000}.{micro % 1_000_000:06d}"


def service_pause(record: dict[str, Any], fallback_seconds: int) -> dict[str, Any]:
    """The pause one service-pause response imposes, derived only from its recorded result: the raw Retry-After values,
    the rule applied and the eligible instant against the response receipt clock (``ended_utc``)."""
    receipt = parse_utc(record["ended_utc"])
    raw = [v for k, v in record["headers"] if str(k).lower() == "retry-after"]
    values = [v.strip(" \t") if isinstance(v, str) else None for v in raw]
    eligible = None
    if not values:
        rule = "FALLBACK_MISSING"
    elif any(v is None for v in values):
        rule = "FALLBACK_MALFORMED"
    elif len(set(values)) > 1:
        rule = "FALLBACK_CONFLICTING"
    elif re.fullmatch(r"[0-9]+", values[0]):
        rule = "DELTA_SECONDS"
        try:
            eligible = receipt + _dt.timedelta(seconds=int(values[0]))
        except (OverflowError, ValueError):
            eligible = MAX_INSTANT
    elif re.fullmatch(r"-[0-9]+", values[0]):
        rule = "FALLBACK_NEGATIVE"
    else:
        when = http_date_instant(values[0], receipt)
        if when is None:
            rule = "FALLBACK_MALFORMED"
        elif when < receipt:
            rule = "FALLBACK_PAST_DATE"
        else:
            rule, eligible = "HTTP_DATE", when
    if eligible is None:
        eligible = receipt + _dt.timedelta(seconds=fallback_seconds)
    return {"retry_after_raw": raw, "retry_after_rule": rule, "response_clock_utc": record["ended_utc"],
            "delay_seconds": _decimal_seconds(eligible - receipt), "eligible_utc": fmt_utc(eligible),
            "fallback_seconds": fallback_seconds}


def _receipt_retry_after(headers: list[list[Any]], receipt: str) -> int | None:
    """The request record's retry_after_seconds (same meaning as the default mode) against the receipt clock."""
    value = header(headers, "Retry-After")
    if value is None:
        return None
    try:
        if value.strip().isdigit():
            return int(value.strip())
        return max(0, int((rfc1123(value) - parse_utc(receipt)).total_seconds()) + 1)
    except (ValueError, TypeError, OverflowError):
        return None


class OwnerLock:
    """An exclusive operating-system lock on the acquisition's OWNER.lock for one whole invocation (released by the
    operating system when the owner process ends)."""

    def __init__(self, directory: Path) -> None:
        self.path = Path(directory) / "OWNER.lock"
        self.fd: int | None = None

    def __enter__(self) -> "OwnerLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            if os.name == "nt":
                import msvcrt  # noqa: PLC0415 - platform lock
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl  # noqa: PLC0415 - platform lock
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            os.close(fd)
            raise BuildRefused("CAPTURE_OWNER_ACTIVE", "another capture owner holds this acquisition") from exc
        self.fd = fd
        return self

    def __exit__(self, *exc_info: Any) -> None:
        if self.fd is None:
            return
        try:
            if os.name == "nt":
                import msvcrt  # noqa: PLC0415
                os.lseek(self.fd, 0, 0)
                msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        os.close(self.fd)
        self.fd = None


class ServiceJournal:
    """The service-aware journal: a HEADER line, then lines each carrying ``prev`` (sha256 of the previous line's exact
    bytes), plus the request-authority anchor (line count, intent count, the last anchored line's sha256 and the sha256
    of the one line being appended, announced before it is written)."""

    def __init__(self, directory: Path, header_doc: dict[str, Any]) -> None:
        self.dir = Path(directory)
        self.path = self.dir / "journal.jsonl"
        self.anchor_path = self.dir / "AUTHORITY.json"
        self.header = header_doc
        self.rows: list[dict[str, Any]] = []
        self.shas: list[str] = []

    @staticmethod
    def _line(row: dict[str, Any]) -> bytes:
        return json.dumps(row, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"

    def create(self) -> None:
        line = self._line({"type": "HEADER", "header": self.header})
        with self.path.open("xb") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        self.rows, self.shas = [{"type": "HEADER", "header": self.header}], [sha256_bytes(line)]

    def load(self) -> None:
        data = self.path.read_bytes()
        if data and not data.endswith(b"\n"):
            raise BuildRefused("JOURNAL_TORN", "the journal's last line is incomplete")
        lines = [line + b"\n" for line in data.split(b"\n")[:-1]] if data else []
        try:
            rows = [json.loads(line.decode("utf-8")) for line in lines]
        except (UnicodeDecodeError, ValueError) as exc:
            raise BuildRefused("JOURNAL_INVALID", f"unreadable journal line: {exc}") from exc
        if not rows or not isinstance(rows[0], dict) or rows[0].get("type") != "HEADER":
            raise BuildRefused("JOURNAL_INVALID", "the journal does not start with its header")
        header_doc = rows[0].get("header") or {}
        if header_doc.get("schema") != SERVICE_JOURNAL_SCHEMA:
            raise BuildRefused("CAPTURE_MODE_CONFLICT", "a default-mode journal exists for this acquisition policy; "
                                                        "the service-aware mode neither adopts nor resets it")
        if header_doc != self.header:
            changed = sorted(k for k in set(header_doc) | set(self.header) if header_doc.get(k) != self.header.get(k))
            raise BuildRefused("CAPTURE_POLICY_CHANGED", f"the journal binds other {changed}")
        shas = [sha256_bytes(line) for line in lines]
        for index in range(1, len(rows)):
            if not isinstance(rows[index], dict) or rows[index].get("prev") != shas[index - 1]:
                raise BuildRefused("CAPTURE_JOURNAL_PREFIX_CHANGED", f"journal line {index + 1} breaks the hash chain")
        self.rows, self.shas = rows, shas

    def append(self, row: dict[str, Any]) -> None:
        row = dict(row, prev=self.shas[-1])
        line = self._line(row)
        with self.path.open("ab") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        self.rows.append(row)
        self.shas.append(sha256_bytes(line))

    def anchor_document(self, binding_identity: str, pending: str | None = None) -> dict[str, Any]:
        return {"schema": AUTHORITY_SCHEMA, "policy_id": self.header["policy_id"],
                "binding_identity": binding_identity, "lines": len(self.rows),
                "intents": sum(1 for r in self.rows if r.get("type") == "INTENT"), "head_sha256": self.shas[-1],
                "pending_sha256": pending}

    def verify_anchor(self, binding_identity: str) -> dict[str, Any]:
        """Line count L and head of the anchor: the journal holds L or L + 1 lines, line L hashes to the head and the
        anchor's intent count equals the intents among the first L lines. A line L + 1 (a crash after its append and
        before the anchor advanced) is authority only when it is exactly the line the anchor announced; any other
        line after the anchored head refuses CAPTURE_JOURNAL_TAIL_NOT_ANNOUNCED. An announced line that is absent (a
        crash before its append) was never written; for an INTENT that means it was never dispatched."""
        if not self.anchor_path.exists():
            if len(self.rows) > 1:
                raise BuildRefused("CAPTURE_COUNTER_RESET", "the request-authority anchor is missing beside recorded "
                                                            "journal lines")
            return {"lines": 1, "lagging_lines": len(self.rows) - 1, "announced_tail": False}
        try:
            doc = json.loads(self.anchor_path.read_bytes().decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise BuildRefused("CAPTURE_COUNTER_RESET", f"unreadable request-authority anchor: {exc}") from exc
        if doc.get("schema") != AUTHORITY_SCHEMA:
            raise BuildRefused("CAPTURE_POLICY_CHANGED", f"the request-authority anchor schema {doc.get('schema')!r} "
                                                         f"is not {AUTHORITY_SCHEMA}")
        if doc.get("policy_id") != self.header["policy_id"] or doc.get("binding_identity") != binding_identity:
            raise BuildRefused("CAPTURE_POLICY_CHANGED", "the request-authority anchor binds another acquisition")
        pending = doc.get("pending_sha256")
        if pending is not None and not (isinstance(pending, str) and _HEX64.fullmatch(pending)):
            raise BuildRefused("CAPTURE_COUNTER_RESET", "the request-authority anchor announces an invalid line")
        lines = doc.get("lines")
        if type(lines) is not int or lines < 1 or not (lines <= len(self.rows) <= lines + 1):
            raise BuildRefused("CAPTURE_COUNTER_RESET", f"the anchor records {lines} lines; the journal holds "
                                                        f"{len(self.rows)}")
        if doc.get("head_sha256") != self.shas[lines - 1]:
            raise BuildRefused("CAPTURE_JOURNAL_PREFIX_CHANGED", "the journal no longer hashes to its anchored head")
        if doc.get("intents") != sum(1 for r in self.rows[:lines] if r.get("type") == "INTENT"):
            raise BuildRefused("CAPTURE_COUNTER_RESET", "the anchored intent count differs from the journal")
        if len(self.rows) == lines + 1 and self.shas[lines] != pending:
            raise BuildRefused(TAIL_REFUSAL, f"journal line {lines + 1} follows the anchored head but is not the line "
                                             f"the request-authority anchor announced")
        return {"lines": lines, "lagging_lines": len(self.rows) - lines, "announced_tail": len(self.rows) == lines + 1}


def _write_authority(journal: ServiceJournal, binding_identity: str, clock: str, pending: str | None = None) -> None:
    """Replace the request-authority anchor atomically (create-only temporary file, fsync, replace); ``pending`` is the
    sha256 of the exact line about to be appended."""
    doc = dict(journal.anchor_document(binding_identity, pending), updated_utc=clock)
    temporary = journal.dir / f".AUTHORITY.tmp-{os.getpid()}-{time.time_ns()}"
    with temporary.open("xb") as handle:
        handle.write(canonical_json_bytes(doc) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, journal.anchor_path)


def _service_append(journal: ServiceJournal, row: dict[str, Any], binding_identity: str, clock: str) -> None:
    """Every service journal write: announce the exact next line in the request-authority anchor, append it, then
    advance the anchor to it. A crash leaves at most that one announced line after the anchored head."""
    line = journal._line(dict(row, prev=journal.shas[-1]))
    _write_authority(journal, binding_identity, clock, sha256_bytes(line))
    journal.append(row)
    _write_authority(journal, binding_identity, clock)


def _unbound_raw(output_root: Path, control: dict[str, Any]) -> list[str]:
    """Raw bodies in a root whose journal is new that no finalized acquisition, other journal or control explains."""
    raw_dir = Path(output_root) / "raw" / "sha256"
    if not raw_dir.is_dir():
        return []
    present = {p.name for p in raw_dir.iterdir() if _HEX64.fullmatch(p.name)}
    known = {sha256_bytes(control[k]) for k in ("payload", "receipt_raw", "route_raw")}
    acq_root = Path(output_root) / "acquisition"
    for path in sorted((acq_root / "sha256").glob("*/acquisition.json")) if (acq_root / "sha256").is_dir() else []:
        doc = load_acquisition(path, output_root)
        known |= {r["body_sha256"] for r in doc.get("requests") or [] if r.get("body_sha256")}
        known |= {v for k, v in (doc.get("control") or {}).items() if k.endswith("sha256") and isinstance(v, str)}
    for path in sorted((acq_root / "journal").glob("*/journal.jsonl")) if (acq_root / "journal").is_dir() else []:
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line) if line.strip() else {}
            if row.get("type") == "RESULT" and (row.get("request") or {}).get("body_sha256"):
                known.add(row["request"]["body_sha256"])
    return sorted(present - known)


def service_state(journal: ServiceJournal, pause_statuses: tuple[int, ...]) -> dict[str, Any]:
    """Request records, key outcomes, pauses, resumes, acknowledgements, owners and the latest recorded instant of a
    loaded service journal, with its ordering rules (no dispatch after an unpaused 429 or before a resume)."""
    intents: dict[int, dict[str, Any]] = {}
    intent_line: dict[int, int] = {}
    results: dict[int, dict[str, Any]] = {}
    pauses: list[dict[str, Any]] = []
    resumes: list[dict[str, Any]] = []
    acks: dict[int, dict[str, Any]] = {}
    outcomes: dict[str, str] = {}
    owners: dict[str, dict[str, Any]] = {}
    final = None
    instants: list[str] = []
    paused_unresumed = False
    unknown_open: list[int] = []
    for index, row in enumerate(journal.rows[1:], start=1):
        kind = row.get("type")
        if kind not in SERVICE_LINE_TYPES:
            raise BuildRefused("JOURNAL_INVALID", f"unknown line type {kind}")
        if kind == "INTENT":
            seq = row["seq"]
            if seq in intents or seq != len(intents) + 1:
                raise BuildRefused("JOURNAL_INVALID", f"intent {seq} is not the next sequence")
            if paused_unresumed:
                raise BuildRefused("JOURNAL_INVALID", f"intent {seq} was dispatched during a service pause")
            if [s for s in unknown_open if s not in acks]:
                raise BuildRefused("JOURNAL_INVALID", f"intent {seq} follows an unreconciled intent")
            last = max(results) if results else None
            if last is not None and results[last]["http_status"] in pause_statuses and \
                    not any(p["seq"] == last for p in pauses):
                raise BuildRefused("JOURNAL_INVALID", f"intent {seq} follows an unpaused service response")
            intents[seq], intent_line[seq] = row, index
            unknown_open.append(seq)
            instants.append(row["started_utc"])
        elif kind == "RESULT":
            seq = row["seq"]
            if seq not in intents or seq in results or row["request"].get("seq") != seq:
                raise BuildRefused("JOURNAL_INVALID", f"result without a single intent {seq}")
            results[seq] = row["request"]
            if seq in unknown_open:
                unknown_open.remove(seq)
            instants.append(row["request"]["ended_utc"])
        elif kind == "PAUSE":
            seq = row["seq"]
            if seq not in results or results[seq]["http_status"] not in pause_statuses or \
                    any(p["seq"] == seq for p in pauses):
                raise BuildRefused("JOURNAL_INVALID", f"pause {seq} does not follow a single service response")
            pauses.append(row)
            paused_unresumed = True
            instants.append(row["recorded_utc"])
        elif kind == "RESUME":
            if not paused_unresumed:
                raise BuildRefused("JOURNAL_INVALID", "resume without a pause")
            resumes.append(row)
            paused_unresumed = False
            instants.append(row["at"])
        elif kind == "ACKNOWLEDGED":
            seq = row["seq"]
            if seq not in intents or seq in results or seq in acks:
                raise BuildRefused("JOURNAL_INVALID", f"acknowledgement {seq} names no unknown intent")
            acks[seq] = row
            instants.append(row["at"])
        elif kind == "KEY_DONE":
            outcomes[row["contest_key"]] = row["acquisition_outcome"]
        elif kind == "OWNER_START":
            owners[row["owner"]] = {"start": row, "end": None}
            instants.append(row["at"])
        elif kind == "OWNER_END":
            if row["owner"] not in owners:
                raise BuildRefused("JOURNAL_INVALID", "owner end without a start")
            owners[row["owner"]]["end"] = row
            instants.append(row["at"])
        else:
            final = row["acquisition_identity"]
    records: list[dict[str, Any]] = []
    unknown = []
    for seq in sorted(intents):
        if seq in results:
            records.append(results[seq])
        else:
            unknown.append(seq)
            records.append(_unknown_record(intents[seq]))
    last = max(results) if results else None
    unpaused = last if last is not None and results[last]["http_status"] in pause_statuses and \
        not any(p["seq"] == last for p in pauses) else None
    stopped = [o for o, v in owners.items() if v["end"] is None]
    return {"records": records, "outcomes": outcomes, "pauses": pauses, "resumes": resumes, "acks": acks,
            "unknown": unknown, "intent_line": intent_line, "unpaused_429": unpaused, "final": final,
            "latest_utc": max(instants) if instants else None, "paused_unresumed": paused_unresumed,
            "stopped_owners": stopped,
            "last_intent_started": intents[max(intents)]["started_utc"] if intents else None}


def _service_planning(history: list[dict[str, Any]], pause_statuses: tuple[int, ...]) -> list[dict[str, Any]]:
    """The history the per-key plan sees in the service mode: the service pause, not an in-run sleep, honoured a
    paused response's Retry-After, so its retry is not refused by the contract's in-run cap."""
    return [dict(r, retry_after_seconds=None) if r["http_status"] in pause_statuses else r for r in history]


def _unknown_record(intent: dict[str, Any]) -> dict[str, Any]:
    return {"seq": intent["seq"], "contest_key": intent["contest_key"], "kind": intent["kind"],
            "purpose": intent["purpose"], "url": intent["url"], "started_utc": intent["started_utc"],
            "ended_utc": None, "outcome": "INTERRUPTED_UNKNOWN", "http_status": None, "reason": None, "headers": [],
            "location": None, "body_sha256": None, "body_bytes": None, "retry_after_seconds": None,
            "slept_seconds": "0.000", "error": "INTENT_WITHOUT_RESULT"}


def verify_service_lines(journal: ServiceJournal, contract: dict[str, Any], keys_order: list[str],
                         service: dict[str, Any], control: dict[str, Any], pid: str,
                         plan_next_key: Callable[..., Any], key_outcome: Callable[..., str],
                         read_body: Callable[[dict[str, Any]], bytes], pause_statuses: tuple[int, ...]) -> dict[str, Any]:
    """Replay the whole journal and recompute every decision-bearing line before any of it is used: each INTENT is the
    contract plan's next request for the next pending key within the limits, inside an eligible owner invocation; each
    RESULT answers its INTENT and its derived fields (outcome, location, Retry-After seconds, body size) match its own
    observation and verified raw body; each PAUSE directly follows its RESULT and equals ``service_pause`` of that
    record under the bound fallback, with the request count and key partition of that moment; each OWNER_START and
    RESUME is at or after the latest journal instant and the effective eligible instant; each KEY_DONE is the next
    pending key in the bound order, the plan has no request left within the limits and its outcome is the contract's
    outcome of its recorded history; FINALIZED names the identity of the document of the recorded observations. The
    first line that is not its own derivation refuses CAPTURE_JOURNAL_LINE_NOT_DERIVED (C44-CONT-01, MF44A01-01):
    an edited, appended or promoted line can neither shorten a pause, invent a completion nor renew a budget."""
    limits = contract["acquisition"]["limits"]
    total = limits["total_requests"]
    specs = {spec["contest_key"]: spec for spec in contract["scope"]["keys"]}
    fallback = service["fallback"]
    records: list[dict[str, Any]] = []
    position: dict[int, int] = {}
    intents: dict[int, dict[str, Any]] = {}
    result_line: dict[int, int] = {}
    outcomes: dict[str, str] = {}
    pauses: list[dict[str, Any]] = []
    owners: dict[str, bool] = {}
    instants: list[str] = []
    in_owner = exhausted = paused = False

    def per_key_limit(kind: str) -> int:
        return limits["metadata_requests_per_key" if kind == "METADATA" else "replay_requests_per_key"]
    for index in range(1, len(journal.rows)):
        row = journal.rows[index]
        kind = row.get("type")

        def refuse(reason: str) -> None:
            raise BuildRefused(DERIVATION_REFUSAL, f"journal line {index + 1} ({kind}): {reason}")
        if kind == "OWNER_START":
            if instants and parse_utc(row["at"]) < parse_utc(max(instants)):
                refuse("the owner started before the latest recorded journal instant")
            if paused and parse_utc(row["at"]) < parse_utc(max(p["eligible_utc"] for p in pauses)):
                refuse("the owner started before the paused acquisition's eligible instant")
            if row.get("previous_owner_unreleased") != [o for o, open_ in owners.items() if open_]:
                refuse("previous_owner_unreleased is not the set of owners that never ended")
            owners[row["owner"]] = True
            in_owner, exhausted = True, False
            instants.append(row["at"])
        elif kind == "OWNER_END":
            owners[row["owner"]] = False
            in_owner = False
            instants.append(row["at"])
        elif kind == "ACKNOWLEDGED":
            in_owner = False
            instants.append(row["at"])
        elif kind == "RESUME":
            before = journal.rows[index - 1]
            if before.get("type") != "OWNER_START" or before.get("at") != row.get("at"):
                refuse("a resume directly follows its owner's start, at the same instant")
            if not pauses or row.get("after_pause_seq") != pauses[-1]["seq"] or \
                    row.get("eligible_utc") != max(p["eligible_utc"] for p in pauses):
                refuse("the resume does not name the latest pause and the effective eligible instant")
            paused = False
            instants.append(row["at"])
        elif kind == "INTENT":
            if not in_owner or paused:
                refuse("a request outside an eligible owner invocation")
            pending = [k for k in keys_order if k not in outcomes]
            key = row.get("contest_key")
            if not pending or key != pending[0]:
                refuse(f"the request is for {key}, not the next pending key in the bound order")
            spec = specs[key]
            history = [r for r in records if r["contest_key"] == key]
            step = None if spec["selection_role"] == af.CONTROL_ROLE else \
                plan_next_key(spec, _service_planning(history, pause_statuses), contract, read_body)
            if step is None or (row.get("kind"), row.get("purpose"), row.get("url")) != tuple(step):
                refuse(f"the request {(row.get('kind'), row.get('purpose'))} is not the contract plan's next "
                       f"request {tuple(step[:2]) if step else None}")
            if sum(1 for r in history if r["kind"] == row["kind"]) >= per_key_limit(row["kind"]) or \
                    len(records) >= total:
                refuse("the request exceeds the per-key or total limit")
            intents[row["seq"]] = row
            position[row["seq"]] = len(records)
            records.append(_unknown_record(row))
            instants.append(row["started_utc"])
        elif kind == "RESULT":
            seq, record = row["seq"], row["request"]
            intent = intents[seq]
            observed = record.get("http_status") is not None
            if any(record.get(f) != intent.get(f) for f in ("seq", "contest_key", "kind", "purpose", "url",
                                                             "started_utc")):
                refuse("the result does not answer its intent")
            if record.get("outcome") != ("RESPONSE" if observed else "NETWORK_ERROR") or \
                    (record.get("body_sha256") is not None) != observed or \
                    record.get("location") != header(record.get("headers") or [], "Location") or \
                    record.get("retry_after_seconds") != _receipt_retry_after(record.get("headers") or [],
                                                                              record["ended_utc"]) or \
                    (observed and record.get("body_bytes") != len(read_body(record))):
                refuse("the result's derived fields do not match its own observation")
            records[position[seq]] = record
            result_line[seq] = index
            instants.append(record["ended_utc"])
        elif kind == "PAUSE":
            seq = row["seq"]
            record = records[position[seq]]
            if result_line.get(seq) != index - 1:
                refuse("a pause directly follows the result it derives from")
            if type(row.get("recovered")) is not bool or (row["recovered"] is False and not in_owner):
                refuse("an in-run pause outside its owner invocation")
            expected = {"seq": seq, "contest_key": record["contest_key"], "kind": record["kind"],
                        "purpose": record["purpose"], "url": record["url"], "http_status": record["http_status"],
                        **service_pause(record, fallback), "requests_used": len(records), "requests_limit": total,
                        "keys": key_partition(keys_order, records, outcomes)}
            for field, value in expected.items():
                if row.get(field) != value:
                    refuse(f"{field} {row.get(field)!r} is not its derivation {value!r} from the recorded result "
                           f"and the bound policy")
            extra = sorted(set(row) - set(expected) - {"type", "prev", "recovered", "recorded_utc"})
            if extra:
                refuse(f"unexpected fields {extra}")
            pauses.append(row)
            paused = True
            in_owner = in_owner and not row["recovered"]
            instants.append(row["recorded_utc"])
        elif kind == "KEY_DONE":
            if not in_owner or paused:
                refuse("a key completion outside an eligible owner invocation")
            pending = [k for k in keys_order if k not in outcomes]
            key = row.get("contest_key")
            if not pending or key != pending[0]:
                refuse(f"{key} is not the next pending key in the bound order")
            spec = specs[key]
            history = [r for r in records if r["contest_key"] == key]
            if spec["selection_role"] == af.CONTROL_ROLE:
                expected_outcome = "CONTROL_REUSED" if not history else None
            else:
                step = plan_next_key(spec, _service_planning(history, pause_statuses), contract, read_body)
                if step is not None:
                    if sum(1 for r in history if r["kind"] == step[0]) >= per_key_limit(step[0]):
                        pass
                    elif len(records) >= total:
                        exhausted = True
                    else:
                        refuse(f"the contract plan still has its next request {tuple(step[:2])} for {key} within "
                               f"its limits")
                if step is not None and exhausted:
                    expected_outcome = key_outcome(spec, history, True) if history else \
                        "NOT_ATTEMPTED_TOTAL_BUDGET_EXHAUSTED"
                else:
                    expected_outcome = key_outcome(spec, history, False)
            if row.get("acquisition_outcome") != expected_outcome:
                refuse(f"outcome {row.get('acquisition_outcome')!r} is not {expected_outcome!r}, the outcome of "
                       f"{key}'s recorded observations")
            outcomes[key] = expected_outcome
        elif kind == "FINALIZED":
            if not in_owner or paused or [k for k in keys_order if k not in outcomes]:
                refuse("finalization before every key is done inside an eligible owner invocation")
            identity = sha256_bytes(canonical_json_bytes(_acquisition_document(contract, control, pid, records,
                                                                               outcomes)))
            if row.get("acquisition_identity") != identity:
                refuse("the finalized identity is not the document of the recorded observations")
    return {"lines": len(journal.rows), "records": len(records), "outcomes": len(outcomes), "pauses": len(pauses)}


def key_partition(keys: list[str], records: list[dict[str, Any]], outcomes: dict[str, str]) -> dict[str, Any]:
    attempted = {r["contest_key"] for r in records}
    return {"completed": {k: outcomes[k] for k in keys if k in outcomes},
            "attempted_failed_pending": [k for k in keys if k not in outcomes and k in attempted],
            "pending_unattempted": [k for k in keys if k not in outcomes and k not in attempted]}


def _service_summary(state: dict[str, Any], keys: list[str], limit: int, service: dict[str, Any],
                     new_requests: int, journal: ServiceJournal, stopped: list[str] | None = None) -> dict[str, Any]:
    """``stopped`` names the owners that had stopped without release before this invocation's own owner started."""
    used = len(state["records"])
    eligible = max((p["eligible_utc"] for p in state["pauses"]), default=None)
    return {"capture_mode": SERVICE_RULES["mode"], "rules_identity": service["rules_identity"],
            "binding_identity": service["binding_identity"], "new_requests": new_requests, "requests_used": used,
            "requests_limit": limit, "requests_remaining": max(0, limit - used), "eligible_utc": eligible,
            "pauses": [{k: p[k] for k in ("seq", "contest_key", "kind", "purpose", "http_status", "retry_after_raw",
                                          "retry_after_rule", "response_clock_utc", "delay_seconds", "eligible_utc",
                                          "recovered")} for p in state["pauses"]],
            "keys": key_partition(keys, state["records"], state["outcomes"]),
            "stopped_owner": state["stopped_owners"] if stopped is None else stopped, "journal": str(journal.path)}


def _acquisition_document(contract: dict[str, Any], control: dict[str, Any], pid: str, records: list[dict[str, Any]],
                          outcomes: dict[str, str]) -> dict[str, Any]:
    """The default mode's acquisition document, field for field (materialization and validators are unchanged)."""
    limits = contract["acquisition"]["limits"]
    return {"schema": ACQUISITION_SCHEMA, "policy_id": pid, "contract_id": contract["contract_id"],
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


def capture_service(contract: dict[str, Any], rows: list[dict[str, Any]], output_root: Path, control: dict[str, Any],
                    service: dict[str, Any], *, transport: Callable[[str, dict[str, str], float], Response] | None = None,
                    sleep: Callable[[float], None] | None = None, monotonic: Callable[[], float] | None = None,
                    now: Callable[[], str] | None = None, audit: bool = True,
                    planner: Callable[..., tuple[str, str, str] | None] | None = None,
                    outcome_of: Callable[[dict[str, Any], list[dict[str, Any]], bool], str] | None = None,
                    max_body_bytes: int | None = None, acknowledge: int | None = None) -> dict[str, Any]:
    """The service-aware acquisition: the default mode's per-key plan, limits, hosts, transport and document, but the
    first service-pause response stops every further dispatch and only a later explicit eligible invocation
    resumes it (docs/architecture/ARCHIVE_CAPTURE_SERVICE_PAUSE.md)."""
    plan_next_key = planner or plan_next
    key_outcome = outcome_of or acquisition_outcome
    sleep = sleep or (lambda seconds: time.sleep(seconds))
    monotonic = monotonic or (lambda: time.perf_counter())
    now = now or (lambda: utc_now())
    output_root = Path(output_root)

    def read_body(record: dict[str, Any]) -> bytes:
        return read_raw(output_root, record["body_sha256"])
    acquisition = contract["acquisition"]
    limits = acquisition["limits"]
    pid = policy_id(contract)
    keys_order = [row["contest_key"] for row in rows]
    pause_statuses = tuple(service["rules"]["service_pause_statuses"])
    bid = service["binding_identity"]
    header_doc = {"schema": SERVICE_JOURNAL_SCHEMA, "policy_id": pid,
                  "tranche_sha256": contract["scope"]["tranche_sha256"], "contract_id": contract["contract_id"],
                  "contract_sha256": service["contract_sha256"], "rules_identity": service["rules_identity"],
                  "binding_identity": bid, "ordered_keys_sha256": sha256_bytes(canonical_json_bytes(keys_order)),
                  "total_requests": limits["total_requests"]}
    existing = sorted((output_root / "acquisition" / "sha256").glob("*/acquisition.json")) \
        if (output_root / "acquisition" / "sha256").is_dir() else []
    for path in existing:
        doc = load_acquisition(path, output_root)
        if doc["policy_id"] == pid:
            return {"state": "ALREADY_FINALIZED", "acquisition_identity": path.parent.name, "path": str(path),
                    "new_requests": 0, "totals": doc["totals"], "outcomes": doc["outcomes"],
                    "capture_mode": SERVICE_RULES["mode"], "binding_identity": bid}
    journal_dir = output_root / "acquisition" / "journal" / pid
    with OwnerLock(journal_dir):
        journal = ServiceJournal(journal_dir, header_doc)
        if journal.path.exists():
            journal.load()
        else:
            if acknowledge is not None:
                raise BuildRefused("CAPTURE_ACKNOWLEDGEMENT_INVALID", "no journal records an intent to acknowledge")
            if journal.anchor_path.exists():
                raise BuildRefused("CAPTURE_COUNTER_RESET", "the journal is missing beside its request-authority "
                                                            "anchor")
            unbound = _unbound_raw(output_root, control)
            if unbound:
                raise BuildRefused("CAPTURE_COUNTER_RESET", f"raw bodies without any journal or acquisition "
                                                            f"{unbound[:5]}")
            journal.create()
        anchor = journal.verify_anchor(bid)
        state = service_state(journal, pause_statuses)
        for sha in [r["body_sha256"] for r in state["records"] if r.get("body_sha256")]:
            read_raw(output_root, sha)
        verify_service_lines(journal, contract, keys_order, service, control, pid, plan_next_key, key_outcome,
                             read_body, pause_statuses)
        if state["final"]:
            # another owner finalized between the unlocked check above and this lock
            final_path = output_root / "acquisition" / "sha256" / state["final"] / "acquisition.json"
            if not final_path.is_file() or load_acquisition(final_path, output_root)["policy_id"] != pid:
                raise BuildRefused("JOURNAL_INVALID", "the journal is finalized but its document is missing")
            doc = load_acquisition(final_path, output_root)
            return {"state": "ALREADY_FINALIZED", "acquisition_identity": state["final"], "path": str(final_path),
                    "new_requests": 0, "totals": doc["totals"], "outcomes": doc["outcomes"],
                    "capture_mode": SERVICE_RULES["mode"], "binding_identity": bid}
        if acknowledge is not None:
            open_unknown = [s for s in state["unknown"] if s not in state["acks"]]
            if acknowledge not in open_unknown:
                raise BuildRefused("CAPTURE_ACKNOWLEDGEMENT_INVALID", f"{acknowledge} is not an unreconciled intent "
                                                                      f"(open: {open_unknown})")
            clock = now()
            _service_append(journal, {"type": "ACKNOWLEDGED", "seq": acknowledge, "at": clock,
                                      "decision": "COUNTED_RESULT_UNKNOWN",
                                      "anchor_had_advanced": state["intent_line"][acknowledge] < anchor["lines"]},
                            bid, clock)
            anchor = journal.verify_anchor(bid)
            state = service_state(journal, pause_statuses)
        unresolved = [s for s in state["unknown"] if s not in state["acks"]]
        if unresolved:
            return {"state": "RECONCILIATION_REQUIRED", **_service_summary(state, keys_order, limits["total_requests"],
                                                                          service, 0, journal),
                    "unknown_intents": [{**{k: r[k] for k in ("seq", "contest_key", "kind", "purpose", "url",
                                                              "started_utc")},
                                         "anchor_had_advanced": state["intent_line"][r["seq"]] < anchor["lines"]}
                                        for r in state["records"] if r["seq"] in unresolved],
                    "statement": "The request may have been sent; its result is unknown and it stays counted. Record "
                                 "--acknowledge-unknown-intent <seq> to continue under the per-key plan."}
        if state["unpaused_429"] is not None:
            record = next(r for r in state["records"] if r["seq"] == state["unpaused_429"])
            clock = now()
            _service_append(journal, {"type": "PAUSE", "seq": record["seq"], "contest_key": record["contest_key"],
                                      "kind": record["kind"], "purpose": record["purpose"], "url": record["url"],
                                      "http_status": record["http_status"], **service_pause(record, service["fallback"]),
                                      "recovered": True, "recorded_utc": clock,
                                      "requests_used": len(state["records"]),
                                      "requests_limit": limits["total_requests"],
                                      "keys": key_partition(keys_order, state["records"], state["outcomes"])},
                            bid, clock)
            state = service_state(journal, pause_statuses)
        clock = now()
        moment = parse_utc(clock)
        summary = _service_summary(state, keys_order, limits["total_requests"], service, 0, journal)
        eligible = summary["eligible_utc"]
        reason = "SERVICE_PAUSE_NOT_ELIGIBLE" if eligible and moment < parse_utc(eligible) else \
            "CLOCK_BEHIND_JOURNAL" if state["latest_utc"] and moment < parse_utc(state["latest_utc"]) else None
        if reason:
            return {"state": "DEFERRED", "reason": reason, "now_utc": clock, "latest_journal_utc": state["latest_utc"],
                    "clock_behind_journal": bool(state["latest_utc"]) and moment < parse_utc(state["latest_utc"]),
                    "seconds_until_eligible": _decimal_seconds(parse_utc(eligible) - moment)
                    if eligible and moment < parse_utc(eligible) else "0.000000", **summary}
        owner = sha256_bytes(f"{os.getpid()}:{time.time_ns()}:{clock}".encode("utf-8"))[:32]
        _service_append(journal, {"type": "OWNER_START", "owner": owner, "pid": os.getpid(), "at": clock,
                                  "previous_owner_unreleased": state["stopped_owners"]}, bid, clock)
        try:
            if state["paused_unresumed"]:
                _service_append(journal, {"type": "RESUME", "after_pause_seq": state["pauses"][-1]["seq"],
                                          "eligible_utc": eligible, "at": clock}, bid, clock)
            result = _service_dispatch(contract, rows, output_root, control, service, journal, state, keys_order,
                                       transport=transport, sleep=sleep, monotonic=monotonic, now=now, audit=audit,
                                       plan_next_key=plan_next_key, key_outcome=key_outcome, read_body=read_body,
                                       max_body_bytes=max_body_bytes, pause_statuses=pause_statuses, pid=pid)
        except Exception as exc:
            ended = now()
            _service_append(journal, {"type": "OWNER_END", "owner": owner, "at": ended, "state": "ABORTED",
                                      "error": f"{type(exc).__name__}: {exc}"[:500]}, bid, ended)
            raise
        ended = now()
        _service_append(journal, {"type": "OWNER_END", "owner": owner, "at": ended, "state": result["state"]},
                        bid, ended)
        return result


def _service_dispatch(contract: dict[str, Any], rows: list[dict[str, Any]], output_root: Path, control: dict[str, Any],
                      service: dict[str, Any], journal: ServiceJournal, state: dict[str, Any], keys_order: list[str],
                      *, transport: Any, sleep: Callable[[float], None], monotonic: Callable[[], float],
                      now: Callable[[], str], audit: bool, plan_next_key: Callable[..., Any], key_outcome: Callable[..., str],
                      read_body: Callable[[dict[str, Any]], bytes], max_body_bytes: int | None,
                      pause_statuses: tuple[int, ...], pid: str) -> dict[str, Any]:
    """The dispatch loop of one eligible invocation (the default mode's loop with the pause stop)."""
    acquisition = contract["acquisition"]
    limits = acquisition["limits"]
    bid = service["binding_identity"]
    records, outcomes = list(state["records"]), dict(state["outcomes"])
    for data in (control["payload"], control["receipt_raw"], control["route_raw"]):
        store_raw(output_root, data)
    if transport is None:
        if audit:
            install_network_audit(journal.dir / "network_audit.jsonl")
        transport = lambda url, headers, timeout: urllib_transport_observed(  # noqa: E731
            url, headers, timeout, max_bytes=max_body_bytes)
    keys = {spec["contest_key"]: spec for spec in contract["scope"]["keys"]}
    headers = dict(acquisition["request_headers"])
    spacing = limits["min_seconds_between_request_starts"] + SPACING_MARGIN_SECONDS
    prior_start = parse_utc(state["last_intent_started"]) if state["last_intent_started"] else None
    new_requests = 0
    last_start = None
    exhausted = False

    def planning(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return _service_planning(history, pause_statuses)
    for row in rows:
        key = keys[row["contest_key"]]
        if key["contest_key"] in outcomes:
            continue
        if key["selection_role"] == "SEPARATE_PREQUALIFIED_ROUTE_CONTROL":
            clock = now()
            _service_append(journal, {"type": "KEY_DONE", "contest_key": key["contest_key"],
                                      "acquisition_outcome": "CONTROL_REUSED"}, bid, clock)
            outcomes[key["contest_key"]] = "CONTROL_REUSED"
            continue
        while True:
            history = [r for r in records if r["contest_key"] == key["contest_key"]]
            step = plan_next_key(key, planning(history), contract, read_body)
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
            if previous and purpose == "RETRY" and previous.get("retry_after_seconds") and \
                    previous["http_status"] not in pause_statuses:
                slept += previous["retry_after_seconds"]
                sleep(previous["retry_after_seconds"])
            if last_start is not None:
                wait = spacing - (monotonic() - last_start)
                if wait > 0:
                    sleep(wait)
                    slept += wait
            elif prior_start is not None:
                wait = spacing - (parse_utc(now()) - prior_start).total_seconds()
                if wait > 0:
                    sleep(wait)
                    slept += wait
            seq = len(records) + 1
            last_start = monotonic()
            started = now()
            _service_append(journal, {"type": "INTENT", "seq": seq, "contest_key": key["contest_key"], "kind": kind,
                                      "purpose": purpose, "url": url, "started_utc": started}, bid, started)
            response = transport(url, headers, float(limits["timeout_seconds"]))
            ended = now()
            new_requests += 1
            incomplete = getattr(response, "incomplete", None)
            if incomplete and response.status in pause_statuses:
                # MF44A01-02: an observed service-pause status stays observed (status, headers, Retry-After and the
                # bounded body actually read) although its body is incomplete; the record says so
                response = Response(response.status, response.reason, response.headers, response.body,
                                    f"{response.error}; HTTP {response.status} status and headers kept; the first "
                                    f"{len(response.body)} body bytes retained")
            elif incomplete:
                # any other status with an incomplete body stays the default mode's fail-closed network error: a
                # truncated body is never evidence of an answer or a capture
                response = Response(None, None, [], b"", f"{response.error}; HTTP {response.status} received; body not "
                                                         f"retained (not a service-pause status)")
            body_sha = store_raw(output_root, response.body) if response.status is not None else None
            response_headers = redact(response.headers, acquisition["redacted_response_headers"])
            record = {"seq": seq, "contest_key": key["contest_key"], "kind": kind, "purpose": purpose, "url": url,
                      "started_utc": started, "ended_utc": ended,
                      "outcome": "RESPONSE" if response.status is not None else "NETWORK_ERROR",
                      "http_status": response.status, "reason": response.reason, "headers": response_headers,
                      "location": header(response_headers, "Location"), "body_sha256": body_sha,
                      "body_bytes": len(response.body) if response.status is not None else None,
                      "retry_after_seconds": _receipt_retry_after(response_headers, ended),
                      "slept_seconds": f"{slept:.3f}", "error": response.error}
            _service_append(journal, {"type": "RESULT", "seq": seq, "request": record}, bid, ended)
            records.append(record)
            if response.status in pause_statuses:
                clock = now()
                state_now = {"records": records, "outcomes": outcomes}
                _service_append(journal, {"type": "PAUSE", "seq": seq, "contest_key": key["contest_key"],
                                          "kind": kind, "purpose": purpose, "url": url,
                                          "http_status": response.status,
                                          **service_pause(record, service["fallback"]), "recovered": False,
                                          "recorded_utc": clock, "requests_used": len(records),
                                          "requests_limit": limits["total_requests"],
                                          "keys": key_partition(keys_order, state_now["records"],
                                                                state_now["outcomes"])}, bid, clock)
                paused = service_state(journal, pause_statuses)
                summary = _service_summary(paused, keys_order, limits["total_requests"], service, new_requests,
                                           journal, stopped=state["stopped_owners"])
                return {"state": "PAUSED_SERVICE_429", "pause": summary["pauses"][-1], **summary}
        history = [r for r in records if r["contest_key"] == key["contest_key"]]
        if exhausted and plan_next_key(key, planning(history), contract, read_body) is not None:
            outcome = "NOT_ATTEMPTED_TOTAL_BUDGET_EXHAUSTED" if not history else key_outcome(key, history, True)
        else:
            outcome = key_outcome(key, history, False)
        clock = now()
        _service_append(journal, {"type": "KEY_DONE", "contest_key": key["contest_key"],
                                  "acquisition_outcome": outcome}, bid, clock)
        outcomes[key["contest_key"]] = outcome
    document = _acquisition_document(contract, control, pid, records, outcomes)
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
    clock = now()
    _service_append(journal, {"type": "FINALIZED", "acquisition_identity": identity}, bid, clock)
    final = service_state(journal, pause_statuses)
    return {"state": "FINALIZED", "acquisition_identity": identity, "path": str(target), "totals": document["totals"],
            "outcomes": document["outcomes"], **_service_summary(final, keys_order, limits["total_requests"], service,
                                                                 new_requests, journal,
                                                                 stopped=state["stopped_owners"])}


def capture_expansion_service(contract: dict[str, Any], output_root: Path, control: dict[str, Any],
                              retained_doc: dict[str, Any], service: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """The expansion acquisition's 70 cohort keys through the service-aware mode, with the expansion planner, outcome
    and body limit of ``capture_expansion``."""
    view = acquisition_view(contract)
    retained = retained_versions(retained_doc)
    root = Path(output_root)

    def read_body(record: dict[str, Any]) -> bytes:
        return read_raw(root, record["body_sha256"])

    def planner(key: dict[str, Any], history: list[dict[str, Any]], _contract: dict[str, Any],
                reader: Callable[[dict[str, Any]], bytes]) -> tuple[str, str, str] | None:
        return plan_next_expansion(key, history, view, reader, retained.get(key["contest_key"], frozenset()))

    def outcome_of(key: dict[str, Any], history: list[dict[str, Any]], exhausted: bool) -> str:
        return expansion_outcome(key, history, exhausted, read_body, retained.get(key["contest_key"], frozenset()))
    rows = [{"contest_key": k["contest_key"]} for k in view["scope"]["keys"]]
    return capture_service(view, rows, root, control, service, planner=planner, outcome_of=outcome_of,
                           max_body_bytes=contract["acquisition"]["limits"]["max_body_bytes"], **kwargs)


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
    parser.add_argument("--cohort", type=Path, default=None,
                        help="BAT-715 expansion contract only: the issued missing-prior cohort (ARCHIVE_COHORT.json)")
    parser.add_argument("--retained-root", type=Path, default=None,
                        help="BAT-715 expansion capture only: the read-only V1.2 canonical root whose retained "
                             "acquisition and raw bodies are copied create-only into the output root")
    parser.add_argument("--no-network-audit", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--capture-policy", type=Path, default=None,
                        help="BAT-716 explicit service-aware capture mode (stage capture or all): stop the whole "
                             "acquisition at HTTP 429 and resume only on a later explicit eligible invocation")
    parser.add_argument("--acknowledge-unknown-intent", type=int, default=None,
                        help="with --capture-policy: record that the result of this interrupted request is unknown "
                             "(it stays counted) so the acquisition may continue")
    return parser


def _service_arguments(args: argparse.Namespace) -> None:
    if args.capture_policy is not None and args.stage == "materialize":
        raise BuildRefused("ARGUMENT_INVALID", "--capture-policy applies to the capture stage (capture or all)")
    if args.acknowledge_unknown_intent is not None and args.capture_policy is None:
        raise BuildRefused("ARGUMENT_INVALID", "--acknowledge-unknown-intent needs --capture-policy")


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
    if result["state"] in ("CAPTURE_PAUSED_SERVICE_429", "CAPTURE_DEFERRED"):
        return SERVICE_PAUSED_EXIT
    if result["state"] == "CAPTURE_RECONCILIATION_REQUIRED":
        return RECONCILIATION_EXIT
    return INTERRUPTED_EXIT if result["state"] == "INTERRUPTED_AT_CHECKPOINT" else 0


if __name__ == "__main__":
    raise SystemExit(main())

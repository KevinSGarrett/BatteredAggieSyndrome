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

r"""Explicit archived-publication evidence for the source-time query (BAT-713, Cycle #41 TP41-A01; contract V1.1).

``bas-source-time-query --database <source-time sqlite> --archive-evidence
<canonical\national_archived_publication_2019\sha256\<id>\national_archived_publication.sqlite> --grain contest
--contest ncaa:1735109 --cutoff 2019-09-02T01:00:50.999999Z``

Standard library only (plus the shared field-grain module), imported only when ``--archive-evidence`` is given;
without it the source-time consumer is unchanged. Opening a sidecar verifies its location, run manifest identity
document, SQLite bytes, schema, labels, counts and natural keys, and that its parent is exactly the opened source-time
database. It then trusts no stored label: every raw payload is rehashed; every request and capture receipt is bound to
the content-addressed acquisition document or the retained control receipt; every stored witness (witness, byte span,
literal) must be exactly one of the occurrences this module's own field-grain extraction finds in the raw page
(attributes tokenized from the start tag, complete text of closed text-only elements, line-start JS assignments);
and every capture and assertion record -- scopes, page facts, the evidenced participant mapping (documented parent
names, CFBD route role and date; numeric ESPN/CFBD ids are never equated), field states, clocks and the complete
witness rows -- is re-derived from the raw bytes, receipts and the parent's lineage and must equal the stored record.
Qualified participant mappings must agree across the tranche. A predecessor V1.0 sidecar is checked for exact witness
occurrences and then refused as superseded (it carries no evidenced participant mapping).

An archived version is only an upper bound for its exact witnessed field values: before the bound publication stays
UNKNOWN (outcome fields FALSE before the contest date's earliest instant), nothing is ever PIT admitted, and the
original source-time assertions, clocks and decisions are returned unchanged next to the archive evidence.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import sqlite3
import urllib.parse
from pathlib import Path
from typing import Any

from aggie_analytics.national_source_time import archive_fields as af
from aggie_analytics.national_source_time import query as base

ARCHIVE_DB_FILE = "national_archived_publication.sqlite"
ARCHIVE_DB_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-DB-2"
ARCHIVE_DOCUMENT_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-DATABASE-2"
LEGACY_DB_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-DB-1"
LEGACY_DOCUMENT_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-DATABASE-1"
ACQUISITION_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-ACQUISITION-1"
KNOWN_CONTRACT_IDS = ("BAT-713-NATIONAL-ARCHIVED-PUBLICATION-2019-V1.1",)
LEGACY_CONTRACT_IDS = ("BAT-713-NATIONAL-ARCHIVED-PUBLICATION-2019-V1.0",)
ARCHIVE_GRAINS = base.ARCHIVE_GRAINS
ARCHIVE_ROW_LABELS = {"evidence_authority": "ARCHIVED_PUBLICATION_EVIDENCE_ONLY",
                      "pit_admission": "NOT_ADMITTED_NO_SEPARATE_PIT_ADMISSION_AUTHORITY",
                      "publication_inference": "ARCHIVE_CAPTURE_UPPER_BOUND_FOR_EXACT_WITNESSED_VERSION_ONLY_NOT_"
                                               "FIRST_PUBLICATION",
                      "scope": "BOUNDED_2019_TRANCHE_28_CONTESTS_NOT_NATIONAL_COVERAGE"}
TABLES = ("meta", "dispositions", "requests", "captures", "assertions")
PAYLOADS = {"dispositions.jsonl": "dispositions", "requests.jsonl": "requests", "captures.jsonl": "captures",
            "assertions.jsonl": "assertions"}
FIELDS = base.FIELDS
WITNESSABLE = af.WITNESSABLE
QUALIFIED = af.QUAL
FIELD_WITNESSES = af.FIELD_WITNESSES
#: The predecessor V1.0 witness sets (participants without the team-name witness), used only to check a legacy
#: sidecar's spans before refusing it as superseded.
LEGACY_FIELD_WITNESSES = {**af.FIELD_WITNESSES,
                          "a_participant": frozenset({"JS_HOME_TEAM_ID", "HOME_TEAM_HREF", "JS_AWAY_TEAM_ID",
                                                      "AWAY_TEAM_HREF"}),
                          "b_participant": frozenset({"JS_HOME_TEAM_ID", "HOME_TEAM_HREF", "JS_AWAY_TEAM_ID",
                                                      "AWAY_TEAM_HREF"})}
VERIFICATION = "SIDECAR_RAW_RECEIPT_FIELD_GRAIN_AND_PARTICIPANT_MAPPING_REDERIVATION_PASSED"
UTC = _dt.timezone.utc
TRUE, FALSE, UNKNOWN = base.TRUE, base.FALSE, base.UNKNOWN
NO_ARCHIVE = "NO_QUALIFIED_ARCHIVE_ASSERTION"
#: Capture record fields by the refusal they map to when the re-derived value differs.
CLOCK_FIELDS = ("clocks", "capture_id", "wayback_timestamp", "original_url")
RECEIPT_FIELDS = ("origin", "request_seq", "final_url", "http_status", "content_type", "memento_datetime_literal",
                  "origin_date_literal", "link_original", "archive_src", "payload_sha256", "payload_bytes",
                  "payload_path", "receipt_document", "receipt_document_sha256", "receipt_pointer")
PARTICIPANT_FIELDS = ("participant_mapping", "orientation", "page_participants")


class ArchiveEvidenceError(base.SourceTimeQueryError):
    """A refused archive sidecar or archive query."""


def _refuse(code: str, message: str) -> ArchiveEvidenceError:
    return ArchiveEvidenceError(code, message)


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _cjson(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# --------------------------------------------------------------------------------------------- sidecar verification

def verify_archive_database(database: Path, *, expect_identity: str | None = None) -> dict[str, Any]:
    db = Path(database)
    if not db.is_file():
        raise _refuse("ARCHIVE_DATABASE_MISSING", f"no archive sidecar at {db}")
    if db.name != ARCHIVE_DB_FILE or db.resolve().parent.parent.name != "sha256":
        raise _refuse("ARCHIVE_LOCATION_INVALID", "the sidecar must sit at <root>/sha256/<id>/" + ARCHIVE_DB_FILE)
    identity = db.resolve().parent.name
    if not base.IDENTITY_RE.match(identity):
        raise _refuse("ARCHIVE_LOCATION_INVALID", f"directory name {identity!r} is not a SHA-256 identity")
    manifest_path = base.manifest_path_for(db)
    if not manifest_path.is_file():
        raise _refuse("ARCHIVE_MANIFEST_MISSING", f"no run manifest at {manifest_path}")
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        identity_document = document["identity_document"]
        computed = hashlib.sha256(base.canonical_json_bytes(identity_document)).hexdigest()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise _refuse("ARCHIVE_MANIFEST_MALFORMED", str(exc)) from exc
    if computed != identity or document.get("identity") != identity:
        raise _refuse("ARCHIVE_IDENTITY_MISMATCH", f"manifest identity document hashes to {computed}, directory is "
                                                   f"{identity}")
    schemas = (identity_document.get("stage"), identity_document.get("schema"), identity_document.get("db_schema_version"))
    if schemas not in (("archived-publication-database", ARCHIVE_DOCUMENT_SCHEMA, ARCHIVE_DB_SCHEMA),
                       ("archived-publication-database", LEGACY_DOCUMENT_SCHEMA, LEGACY_DB_SCHEMA)):
        raise _refuse("ARCHIVE_SCHEMA_UNSUPPORTED", "the manifest is not a known archived-publication sidecar")
    expected = (identity_document.get("outputs") or {}).get(ARCHIVE_DB_FILE)
    actual = base._sha256_file(db)
    if expected != actual:
        raise _refuse("ARCHIVE_DATABASE_TAMPERED", f"sidecar bytes hash to {actual}, manifest names {expected}")
    if expect_identity is not None and expect_identity != identity:
        raise _refuse("STALE_ARCHIVE_IDENTITY", f"expected {expect_identity}, found {identity}")
    return {"archive_identity": identity, "archive_sha256": actual, "manifest": str(manifest_path),
            "content_identity": identity_document.get("content_identity"),
            "contract_sha256": identity_document.get("contract_sha256"), "parent": identity_document.get("parent"),
            "table_counts": identity_document.get("table_counts"),
            "record_counts": identity_document.get("record_counts"),
            "db_schema_version": identity_document.get("db_schema_version")}


class ArchiveEvidence:
    """A verified, read-only archive sidecar composed with one verified source-time database."""

    def __init__(self, database: Path, source: base.SourceTimeDatabase, *, expect_identity: str | None = None) -> None:
        self.binding = verify_archive_database(database, expect_identity=expect_identity)
        self.source = source
        self.root = Path(database).resolve().parent.parent.parent
        conn = base.connect_readonly(database)
        try:
            meta = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM meta")}
            counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}
            tables = {t: [json.loads(row["record"]) for row in conn.execute(f"SELECT record FROM {t} ORDER BY ord")]
                      for t in TABLES if t != "meta"}
        except sqlite3.DatabaseError as exc:
            raise _refuse("ARCHIVE_SCHEMA_UNSUPPORTED", str(exc)) from exc
        finally:
            conn.close()
        legacy = (meta.get("schema_version"), meta.get("contract_id")) in \
            ((LEGACY_DB_SCHEMA, c) for c in LEGACY_CONTRACT_IDS)
        if not legacy and (meta.get("schema_version") != ARCHIVE_DB_SCHEMA or
                           meta.get("contract_id") not in KNOWN_CONTRACT_IDS):
            raise _refuse("ARCHIVE_SCHEMA_UNSUPPORTED", f"schema {meta.get('schema_version')!r} contract "
                                                        f"{meta.get('contract_id')!r}")
        if legacy != (self.binding["db_schema_version"] == LEGACY_DB_SCHEMA):
            raise _refuse("ARCHIVE_SCHEMA_UNSUPPORTED", "sidecar meta and manifest schemas differ")
        if meta.get("content_identity") != self.binding["content_identity"] or \
                meta.get("contract_sha256") != self.binding["contract_sha256"] or \
                json.loads(meta.get("parent") or "null") != self.binding["parent"]:
            raise _refuse("ARCHIVE_IDENTITY_MISMATCH", "sidecar meta and manifest identities differ")
        records = {name: counts[table] for name, table in PAYLOADS.items()}
        if counts != self.binding["table_counts"] or records != self.binding["record_counts"]:
            raise _refuse("ARCHIVE_COUNT_MISMATCH", f"counts {counts} differ from the manifest")
        if json.loads(meta.get("row_labels") or "null") != ARCHIVE_ROW_LABELS:
            raise _refuse("ARCHIVE_SCHEMA_UNSUPPORTED", "row labels differ from the archive evidence-only labels")
        parent = (self.binding["parent"] or {}).get("source_time") or {}
        if (parent.get("database_identity"), parent.get("sqlite_sha256"), parent.get("content_identity"),
                parent.get("contract_sha256")) != (source.binding["database_identity"], source.binding["database_sha256"],
                                                   source.binding["content_identity"], source.binding["contract_sha256"]):
            raise _refuse("ARCHIVE_PARENT_MISMATCH", "the sidecar was built over another source-time database")
        self.meta = meta
        self.dispositions = tables["dispositions"]
        self.requests = tables["requests"]
        self.captures = tables["captures"]
        self.assertions = tables["assertions"]
        self._extractions: dict[str, dict[str, Any]] = {}
        if legacy:
            self._refuse_legacy()
        self._verify()
        self.by_key = {d["contest_key"]: d for d in self.dispositions}
        self.captures_by_id = {c["capture_id"]: c for c in self.captures}

    def close(self) -> None:
        return None

    def __enter__(self) -> "ArchiveEvidence":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------ verification
    def _raw(self, sha: Any) -> bytes:
        if not isinstance(sha, str) or not base.IDENTITY_RE.match(sha):
            raise _refuse("ARCHIVE_PATH_INVALID", f"raw reference {sha!r}")
        path = self.root / "raw" / "sha256" / sha
        if not path.is_file():
            raise _refuse("ARCHIVE_RAW_MISSING", f"raw payload {sha} is missing")
        data = path.read_bytes()
        if _sha_bytes(data) != sha:
            raise _refuse("ARCHIVE_RAW_ALTERED", f"raw payload {sha} bytes changed")
        return data

    def _occurrences(self, payload_sha: str, payload: bytes) -> set[tuple[str, int, int, str]]:
        if payload_sha not in self._extractions:
            self._extractions[payload_sha] = af.extract(payload)
        return {(w["witness"], w["span"][0], w["span"][1], w["literal"])
                for w in self._extractions[payload_sha]["witnesses"]}

    def _check_assertion_structure(self, payloads: dict[str, bytes], field_witnesses: dict[str, Any]) -> None:
        """Natural keys, ownership, field/witness role and the exact-occurrence rule for every stored witness."""
        seen = set()
        captures = {c["capture_id"]: c for c in self.captures}
        for item in self.assertions:
            natural = (item["contest_key"], item["original_url"], item["capture_id"], item["payload_sha256"],
                       item["field"], item["witness"], item["source_revision"], tuple(item["witness_span"]))
            if natural in seen:
                raise _refuse("ARCHIVE_DUPLICATE_ASSERTION", f"duplicate assertion {natural[:7]}")
            seen.add(natural)
            cap = captures.get(item["capture_id"])
            if cap is None or cap["contest_key"] != item["contest_key"] or cap["payload_sha256"] != item[
                    "payload_sha256"] or item["source_revision"] != cap["capture_id"] or \
                    item["original_url"] != cap["original_url"]:
                raise _refuse("ARCHIVE_SOURCE_INVALID", "assertion does not belong to its capture")
            if item["field"] not in FIELDS or item["witness"] not in field_witnesses[item["field"]] or \
                    item.get("field_role") != base.ROLES[item["field"]]:
                raise _refuse("ARCHIVE_SOURCE_INVALID", f"{item['field']} cannot be witnessed by {item['witness']}")
            span = item["witness_span"]
            if not (isinstance(span, list) and len(span) == 2 and all(isinstance(x, int) for x in span)) or \
                    (item["witness"], span[0], span[1], str(item["literal"])) not in self._occurrences(
                        cap["payload_sha256"], payloads[cap["capture_id"]]):
                raise _refuse("ARCHIVE_WITNESS_MISMATCH", f"{item['capture_id']} {item['field']} {item['witness']} "
                                                          f"{span} is not an occurrence of that witness in the raw page")

    def _refuse_legacy(self) -> None:
        """A V1.0 sidecar: check that every stored witness span is an exact occurrence, then refuse it as superseded
        (it orients participants by equal numeric ids in two namespaces and cannot be served under V1.1)."""
        payloads = {}
        for cap in self.captures:
            payloads[cap["capture_id"]] = self._raw(cap["payload_sha256"])
        self._check_assertion_structure(payloads, LEGACY_FIELD_WITNESSES)
        raise _refuse("ARCHIVE_SCHEMA_SUPERSEDED", "contract V1.0 sidecar: its witness spans are exact occurrences but "
                                                   "it carries no evidenced participant mapping (numeric ESPN/CFBD "
                                                   "equality); use the V1.1 successor")

    def _verify(self) -> None:
        acq_id = self.meta.get("acquisition_identity") or ""
        if not base.IDENTITY_RE.match(acq_id):
            raise _refuse("ARCHIVE_PATH_INVALID", "acquisition identity")
        acq_path = self.root / "acquisition" / "sha256" / acq_id / "acquisition.json"
        if not acq_path.is_file():
            raise _refuse("ARCHIVE_RAW_MISSING", "acquisition document is missing")
        acq_bytes = acq_path.read_bytes()
        if _sha_bytes(acq_bytes) != acq_id:
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", "acquisition document bytes changed")
        acquisition = json.loads(acq_bytes.decode("utf-8"))
        if acquisition.get("schema") != ACQUISITION_SCHEMA or \
                acquisition.get("policy_id") != self.meta.get("acquisition_policy_id") or \
                acquisition.get("tranche_sha256") != self.meta.get("tranche_sha256"):
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", "acquisition document binding")
        control = json.loads(self.meta.get("control") or "null") or {}
        receipt_raw = self._raw(control.get("raw_receipt_sha256"))
        receipt = json.loads(receipt_raw.decode("utf-8"))
        self._raw(control.get("route_qualification_sha256"))
        if acquisition.get("control") != {**control, "requests": 0}:
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", "control binding differs from the acquisition document")
        keys = [d["contest_key"] for d in self.dispositions]
        if keys != acquisition.get("keys") or len(set(keys)) != len(keys):
            raise _refuse("ARCHIVE_DUPLICATE_ASSERTION", "dispositions are not exactly one per tranche key")
        acq_requests = acquisition.get("requests") or []
        if len(acq_requests) != len(self.requests):
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", "request accounting differs from the acquisition document")
        by_seq = {}
        for index, (mine, theirs) in enumerate(zip(self.requests, acq_requests)):
            stripped = {k: v for k, v in mine.items() if k not in ("record_type", "body_path", "metadata_answer")}
            if stripped != theirs:
                raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"request {mine.get('seq')} differs from its receipt")
            host = (urllib.parse.urlsplit(str(mine["url"])).hostname or "").lower()
            if host not in ("archive.org", "web.archive.org") or (mine["kind"] == "METADATA") != (host == "archive.org"):
                raise _refuse("ARCHIVE_SOURCE_INVALID", f"request {mine['seq']} host {host}")
            by_seq[mine["seq"]] = (mine, index)
        for item in self.requests:
            if item.get("body_sha256"):
                self._raw(item["body_sha256"])
        payloads: dict[str, bytes] = {}
        versions: dict[str, dict[str, Any]] = {}
        games = {d["contest_key"]: d["game_id_literal"] for d in self.dispositions}
        for cap in self.captures:
            if cap["contest_key"] not in games:
                raise _refuse("ARCHIVE_SOURCE_INVALID", f"capture for out-of-tranche key {cap['contest_key']}")
            payload = payloads[cap["capture_id"]] = self._raw(cap["payload_sha256"])
            if cap["payload_path"] != af.raw_rel(cap["payload_sha256"]) or len(payload) != cap["payload_bytes"]:
                raise _refuse("ARCHIVE_PATH_INVALID", f"capture {cap['capture_id']} payload path")
            versions[cap["capture_id"]] = self._version(cap, payload, by_seq, acq_id, control, receipt,
                                                        _sha_bytes(receipt_raw))
        self._check_assertion_structure(payloads, FIELD_WITNESSES)
        parents: dict[str, dict[str, Any]] = {}
        stored_rows: dict[str, list[dict[str, Any]]] = {}
        for item in self.assertions:
            stored_rows.setdefault(item["capture_id"], []).append(item)
        for cap in self.captures:
            key = cap["contest_key"]
            if key not in parents:
                parents[key] = self._parent(key)
            expected, rows = af.derive_capture(key, parents[key], games[key], versions[cap["capture_id"]],
                                               cap["payload_sha256"])
            self._compare_capture(cap, expected)
            self._compare_rows(cap["capture_id"], stored_rows.get(cap["capture_id"], []), rows)
        conflicts = af.mapping_conflicts(self.captures)
        if conflicts:
            raise _refuse("ARCHIVE_PARTICIPANT_MAPPING_CONTRADICTORY", f"qualified participant mappings disagree: "
                                                                        f"{conflicts[:3]}")
        for disposition in self.dispositions:
            self._verify_disposition(disposition, acquisition)

    def _version(self, cap: dict[str, Any], payload: bytes, by_seq: dict[int, Any], acq_id: str,
                 control: dict[str, Any], receipt: dict[str, Any], receipt_sha: str) -> dict[str, Any]:
        """The archived version exactly as its verified receipt describes it (never from the capture's own labels)."""
        if cap["origin"] == "WORKER_ARCHIVE_REPLAY":
            if cap["request_seq"] not in by_seq:
                raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"{cap['capture_id']} names no request")
            request, index = by_seq[cap["request_seq"]]
            if request["kind"] != "REPLAY" or request["contest_key"] != cap["contest_key"] or \
                    request["http_status"] != 200 or request["body_sha256"] != cap["payload_sha256"]:
                raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"{cap['capture_id']} receipt binding")
            return af.worker_version(acq_id, index, request, payload)
        if cap["origin"] == "MANAGER_RETAINED_CONTROL_REPLAY":
            if cap["payload_sha256"] != control.get("payload_sha256") or cap["contest_key"] != control.get(
                    "contest_key") or cap["request_seq"] is not None:
                raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"{cap['capture_id']} control binding")
            return af.control_version(receipt_sha, receipt, payload)
        raise _refuse("ARCHIVE_SOURCE_INVALID", f"capture origin {cap['origin']!r}")

    def _parent(self, key: str) -> dict[str, Any]:
        contest = self.source.contest(key)
        if contest is None:
            raise _refuse("ARCHIVE_PARENT_MISMATCH", f"{key} is not a source-time contest")
        values: dict[str, set[str]] = {}
        for item in contest["assertions"]:
            values.setdefault(item["field"], set()).add(_cjson(item["parent_value"]))
        if set(values) != set(FIELDS) or any(len(v) != 1 for v in values.values()):
            raise _refuse("ARCHIVE_PARENT_MISMATCH", f"{key} parent values are not single")
        row = self.source.conn.execute("SELECT lineage FROM contests WHERE contest_key = ?", (key,)).fetchone()
        lineage = base._unpack(row["lineage"]) if row is not None and row["lineage"] is not None else []
        record = contest["record"]
        return {"record": record, "values": {f: json.loads(next(iter(values[f]))) for f in FIELDS},
                "participants": af.participant_sources(record, lineage)}

    @staticmethod
    def _compare_capture(stored: dict[str, Any], expected: dict[str, Any]) -> None:
        cid = stored.get("capture_id")
        if set(stored) != set(expected):
            raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{cid} record fields {sorted(set(stored) ^ set(expected))}")
        differs = [k for k in expected if _cjson(stored[k]) != _cjson(expected[k])]
        if not differs:
            return
        if any(k in RECEIPT_FIELDS for k in differs):
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"{cid} receipt literals {[k for k in differs if k in RECEIPT_FIELDS]}")
        if any(k in CLOCK_FIELDS for k in differs):
            raise _refuse("ARCHIVE_CLOCK_FORGED", f"{cid} {[k for k in differs if k in CLOCK_FIELDS]}")
        if "main_element_spans" in differs:
            raise _refuse("ARCHIVE_WITNESS_OUT_OF_SCOPE", f"{cid} main element scopes differ from the raw page")
        participant_states = any(stored["field_states"].get(f) != expected["field_states"].get(f)
                                 for f in ("a_participant", "b_participant"))
        if any(k in PARTICIPANT_FIELDS for k in differs) or participant_states:
            raise _refuse("ARCHIVE_PARTICIPANT_MAPPING_INVALID", f"{cid} participant mapping, orientation or "
                                                                 f"participant states differ from the evidence")
        raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{cid} {differs} differ from the re-derived version")

    @staticmethod
    def _compare_rows(capture_id: str, stored: list[dict[str, Any]], expected: list[dict[str, Any]]) -> None:
        if [_cjson(r) for r in stored] == [_cjson(r) for r in expected]:
            return
        have = sorted((r["witness"], tuple(r["witness_span"])) for r in stored)
        want = sorted((r["witness"], tuple(r["witness_span"])) for r in expected)
        if have != want:
            missing = sorted(set(want) - set(have))
            extra = sorted(set(have) - set(want))
            raise _refuse("ARCHIVE_WITNESS_SET_MISMATCH", f"{capture_id} witness rows omitted {missing[:4]} or "
                                                          f"unexpected {extra[:4]}")
        raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{capture_id} witness rows carry another field, value, comparator "
                                                  f"or state than the re-derived version")

    def _verify_disposition(self, disposition: dict[str, Any], acquisition: dict[str, Any]) -> None:
        key = disposition["contest_key"]
        contest = self.source.contest(key)
        if contest is None:
            raise _refuse("ARCHIVE_PARENT_MISMATCH", f"{key} is not a source-time contest")
        parent = {a["field"]: a["parent_value"] for a in contest["assertions"]}
        record = contest["record"]
        if disposition["parent_values"] != {f: parent.get(f) for f in FIELDS} or \
                (disposition["a_key"], disposition["b_key"], disposition["season"]) != (
                record["a_key"], record["b_key"], record["season"]):
            raise _refuse("ARCHIVE_PARENT_MISMATCH", f"{key} parent values differ from the source-time parent")
        requests = [r for r in self.requests if r["contest_key"] == key]
        if (disposition["request_count"], disposition["metadata_requests"], disposition["replay_requests"]) != (
                len(requests), sum(1 for r in requests if r["kind"] == "METADATA"),
                sum(1 for r in requests if r["kind"] == "REPLAY")):
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"{key} request accounting")
        outcome = (acquisition.get("outcomes") or {}).get(key)
        if disposition["acquisition_outcome"] != outcome:
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"{key} acquisition outcome")
        mine = [c for c in self.captures if c["contest_key"] == key]
        summary = af.disposition_summary(outcome, mine)
        if any(_cjson(disposition[k]) != _cjson(v) for k, v in summary.items()):
            raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{key} disposition, support or capture accounting")

    # ------------------------------------------------------------------ decisions
    def decide(self, assertion: dict[str, Any], cutoff: _dt.datetime) -> dict[str, Any]:
        cap = self.captures_by_id[assertion["capture_id"]]
        contest_date = self.by_key[assertion["contest_key"]]["contest_date"]
        observed, observed_reason = base.observed_by_cutoff({"clocks": {"retrieval": cap["clocks"]["retrieval"]}},
                                                            cutoff)
        bound = cap["clocks"]["archive_capture"]["latest_utc"]
        qualified = assertion["field_state"] == QUALIFIED and cap["state"] == "QUALIFIED"
        if qualified:
            if _dt.datetime.strptime(bound, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC) <= cutoff:
                published, reason = TRUE, "ARCHIVED_VERSION_CAPTURED_AT_OR_BEFORE_CUTOFF"
            elif base.ROLES[assertion["field"]] == "OUTCOME" and cutoff < base.earliest_event_instant(contest_date):
                published, reason = FALSE, "OUTCOME_CANNOT_EXIST_BEFORE_EVENT_DATE"
            else:
                published, reason = UNKNOWN, "BEFORE_ARCHIVE_UPPER_BOUND_EARLIER_PUBLICATION_NOT_EXCLUDED"
        else:
            published, reason = UNKNOWN, "ARCHIVED_ASSERTION_NOT_QUALIFIED:" + assertion["field_state"]
        reasons = ["NO_SEPARATE_PIT_ADMISSION_AUTHORITY"]
        if published != TRUE:
            reasons.append("PUBLICATION_NOT_ESTABLISHED_AT_CUTOFF")
        return {"content_corroboration": assertion["corroboration"], "time_evidence_class": cap["time_evidence_class"],
                "archive_upper_bound_utc": bound if qualified else None, "observed_by_cutoff": observed,
                "observed_reason": observed_reason, "historically_published_by_cutoff": published,
                "publication_reason": reason, "pit_admission": {"state": "NOT_ADMITTED", "reasons": reasons}}

    def field_archive(self, key: str, field: str, cutoff: _dt.datetime) -> dict[str, Any]:
        disposition = self.by_key.get(key)
        if disposition is None:
            return {"in_archive_tranche": False, "disposition": None, "historically_published_by_cutoff": NO_ARCHIVE,
                    "publication_reason": "CONTEST_OUTSIDE_THE_ARCHIVE_TRANCHE", "qualified_capture_ids": [],
                    "other_capture_ids": [], "earliest_qualified_upper_bound_utc": None}
        mine = [c for c in self.captures if c["contest_key"] == key]
        qualified = [c for c in mine if c["state"] == "QUALIFIED" and c["field_states"][field] == QUALIFIED]
        decisions = []
        for cap in qualified:
            item = next(a for a in self.assertions if a["capture_id"] == cap["capture_id"] and a["field"] == field)
            decisions.append(self.decide(item, cutoff)["historically_published_by_cutoff"])
        if not decisions:
            state, reason = NO_ARCHIVE, "NO_ARCHIVED_VERSION_QUALIFIES_THIS_FIELD"
        elif TRUE in decisions:
            state, reason = TRUE, "ARCHIVED_VERSION_CAPTURED_AT_OR_BEFORE_CUTOFF"
        elif all(d == FALSE for d in decisions):
            state, reason = FALSE, "OUTCOME_CANNOT_EXIST_BEFORE_EVENT_DATE"
        else:
            state, reason = UNKNOWN, "BEFORE_ARCHIVE_UPPER_BOUND_EARLIER_PUBLICATION_NOT_EXCLUDED"
        bounds = sorted(c["clocks"]["archive_capture"]["latest_utc"] for c in qualified)
        return {"in_archive_tranche": True, "disposition": disposition["disposition"],
                "historically_published_by_cutoff": state, "publication_reason": reason,
                "qualified_capture_ids": [c["capture_id"] for c in qualified],
                "other_capture_ids": [c["capture_id"] for c in mine if c not in qualified],
                "earliest_qualified_upper_bound_utc": bounds[0] if bounds else None}

    @staticmethod
    def compose(original: str, archive: str) -> str:
        if TRUE in (original, archive):
            return TRUE
        if original == FALSE and archive in (FALSE, NO_ARCHIVE):
            return FALSE
        if original == "NO_CORROBORATING_ASSERTION" and archive == FALSE:
            return FALSE
        if original == "NO_CORROBORATING_ASSERTION" and archive == NO_ARCHIVE:
            return "NO_CORROBORATING_ASSERTION"
        return UNKNOWN

    # ------------------------------------------------------------------ query
    def binding_block(self) -> dict[str, Any]:
        return {"archive_identity": self.binding["archive_identity"],
                "archive_content_identity": self.binding["content_identity"],
                "archive_contract_id": self.meta["contract_id"], "archive_contract_sha256": self.binding["contract_sha256"],
                "acquisition_identity": self.meta["acquisition_identity"],
                "tranche_sha256": self.meta["tranche_sha256"], "tranche_keys": len(self.dispositions),
                "parent_source_time_identity": self.source.binding["database_identity"],
                "verification": VERIFICATION, **ARCHIVE_ROW_LABELS}

    def query(self, grain: str, **kwargs: Any) -> dict[str, Any]:
        if grain in ARCHIVE_GRAINS:
            return self._archive_grain(grain, **kwargs)
        result = self.source.query(grain, **kwargs)
        if grain in ("contest", "contribution"):
            when = base.parse_cutoff(kwargs.get("cutoff"))
            for row in result["rows"]:
                if grain == "contest":
                    key = row["contest"]["contest_key"]
                    row["archive_disposition"] = (self.by_key.get(key) or {}).get("disposition") or \
                        "NOT_IN_ARCHIVE_TRANCHE"
                    for field, value in row["fields"].items():
                        value["archive"] = self.field_archive(key, field, when)
                        value["historically_published_by_cutoff_with_archive"] = self.compose(
                            value["historically_published_by_cutoff"], value["archive"]["historically_published_by_cutoff"])
                else:
                    key = row["relation"]["contributor_contest_key"]
                    for field, value in row["required_field_decisions"].items():
                        archive = self.field_archive(key, field, when)
                        value["archive_published_by_cutoff"] = archive["historically_published_by_cutoff"]
                        value["published_by_cutoff_with_archive"] = self.compose(
                            value["historically_published_by_cutoff"], archive["historically_published_by_cutoff"])
                    row["inputs_published_by_cutoff_with_archive"] = base.aggregate_all(
                        [v["published_by_cutoff_with_archive"] for v in row["required_field_decisions"].values()])
        result["archive_evidence"] = self.binding_block()
        return result

    def _archive_grain(self, grain: str, *, cutoff: str | None = None, season: int | None = None,
                       team: str | None = None, contest: str | None = None, field: str | None = None,
                       evidence_class: str | None = None, source_kind: str | None = None,
                       relation_type: str | None = None, join_state: str | None = None, limit: int | None = 50,
                       offset: int = 0, all_rows: bool = False) -> dict[str, Any]:
        if offset < 0:
            raise base.SourceTimeQueryError("NEGATIVE_OFFSET", "offset must be zero or positive")
        if limit is not None and limit < 0:
            raise base.SourceTimeQueryError("NEGATIVE_LIMIT", "limit must be zero or positive")
        if evidence_class is not None or source_kind is not None or relation_type is not None or join_state is not None \
                or (field is not None and grain != "archive-assertion"):
            raise base.SourceTimeQueryError("FILTER_NOT_APPLICABLE", f"filter does not apply to the {grain} grain")
        filters: dict[str, Any] = {}
        if season is not None:
            if isinstance(season, bool) or not isinstance(season, int):
                raise base.SourceTimeQueryError("SEASON_INVALID", f"season must be an integer, got {season!r}")
            filters["season"] = season
        if team is not None:
            filters["team"] = base.normalize_team(team)
        if contest is not None:
            filters["contest"] = base.normalize_contest(contest)
        if field is not None:
            filters["field"] = base._choice(field, FIELDS, "FIELD_INVALID")
        when = base.parse_cutoff(cutoff) if grain == "archive-assertion" else (
            base.parse_cutoff(cutoff) if cutoff else None)
        keys = [d["contest_key"] for d in self.dispositions
                if filters.get("season") in (None, d["season"]) and filters.get("contest") in (None, d["contest_key"])
                and filters.get("team") in (None, d["a_key"], d["b_key"])]
        if grain == "archive-disposition":
            items: list[Any] = [self.by_key[k] for k in keys]
        elif grain == "archive-request":
            items = [r for r in self.requests if r["contest_key"] in keys]
        elif grain == "archive-capture":
            items = [c for k in keys for c in self.captures if c["contest_key"] == k]
        else:
            items = [{"assertion": a, "decision": None} for k in keys for a in self.assertions
                     if a["contest_key"] == k and filters.get("field") in (None, a["field"])]
        total = len(items)
        stop = None if all_rows else offset + (limit or 0)
        rows = items[offset:stop]
        if grain == "archive-assertion":
            rows = [{"assertion": r["assertion"], "decision": self.decide(r["assertion"], when)} for r in rows]
        return {"grain": grain, "filters": filters,
                "cutoff": None if when is None else {"literal": cutoff, "utc": base._fmt(when)},
                "offset": offset, "limit": None if all_rows else limit, "total": total, "returned": len(rows),
                "rows": rows, "next_offset": offset + len(rows) if offset + len(rows) < total else None,
                "archive_evidence": self.binding_block(), **ARCHIVE_ROW_LABELS}

r"""Explicit archived-publication evidence for the source-time query (BAT-713, Cycle #41 TP41-A01).

``bas-source-time-query --database <source-time sqlite> --archive-evidence
<canonical\national_archived_publication_2019\sha256\<id>\national_archived_publication.sqlite> --grain contest
--contest ncaa:1735109 --cutoff 2019-09-02T01:00:50.999999Z``

Standard library only, imported only when ``--archive-evidence`` is given; without it the source-time consumer is
unchanged. Opening a sidecar verifies its location, run manifest identity document, SQLite bytes, schema, labels,
counts and natural keys, and that its parent is exactly the opened source-time database. It then trusts no stored
label: every raw payload is rehashed, every witness literal is re-read at its byte span inside the recorded main game
element, every witness value, team orientation, field state and disposition is re-derived from those bytes and the
parent's accepted values, every request and capture receipt is compared with the content-addressed acquisition
document or the retained control receipt, and every archive upper bound is recomputed from the receipt literals
(end of second of Memento-Datetime, or of a later x-archive-orig-date within 300 seconds).

An archived version is only an upper bound for its exact witnessed field values: before the bound publication stays
UNKNOWN (outcome fields FALSE before the contest date's earliest instant), nothing is ever PIT admitted, and the
original source-time assertions, clocks and decisions are returned unchanged next to the archive evidence.
"""
from __future__ import annotations

import datetime as _dt
import email.utils
import hashlib
import json
import re
import sqlite3
import urllib.parse
from pathlib import Path
from typing import Any, Iterator

from aggie_analytics.national_source_time import query as base

ARCHIVE_DB_FILE = "national_archived_publication.sqlite"
ARCHIVE_DB_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-DB-1"
ARCHIVE_DOCUMENT_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-DATABASE-1"
ACQUISITION_SCHEMA = "BAS-NATIONAL-ARCHIVED-PUBLICATION-ACQUISITION-1"
KNOWN_CONTRACT_IDS = ("BAT-713-NATIONAL-ARCHIVED-PUBLICATION-2019-V1.0",)
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
WITNESSABLE = ("contest_date", "a_participant", "b_participant", "completion", "a_points", "b_points")
QUALIFIED = "QUALIFIED_AGREES_WITH_PARENT"
FIELD_WITNESSES = {"contest_date": {"JS_EVENT_TIMESTAMP", "INFO_EVENT_DATE"},
                   "a_participant": {"JS_HOME_TEAM_ID", "HOME_TEAM_HREF", "JS_AWAY_TEAM_ID", "AWAY_TEAM_HREF"},
                   "b_participant": {"JS_HOME_TEAM_ID", "HOME_TEAM_HREF", "JS_AWAY_TEAM_ID", "AWAY_TEAM_HREF"},
                   "completion": {"JS_STATUS", "STATUS_DETAIL"},
                   "a_points": {"HOME_SCORE", "AWAY_SCORE"}, "b_points": {"HOME_SCORE", "AWAY_SCORE"},
                   "season": set()}
WITNESS_SCOPE = {"JS_GAME_ID": "JS", "JS_STATUS": "JS", "JS_HOME_TEAM_ID": "JS", "JS_AWAY_TEAM_ID": "JS",
                 "JS_EVENT_TIMESTAMP": "JS", "NAV_GAME_ID": "NAV", "STATUS_DETAIL": "NAV", "HOME_TEAM_HREF": "NAV",
                 "AWAY_TEAM_HREF": "NAV", "HOME_SCORE": "NAV", "AWAY_SCORE": "NAV", "INFO_EVENT_DATE": "INFO"}
SCOPE_MARKERS = {"NAV": (b"<div", b'id="custom-nav"'), "INFO": (b"<div", b'id="gamepackage-game-information"'),
                 "JS": (b"espn.gamepackage.", None)}
TS14_RE = re.compile(r"^[0-9]{14}$")
DIGITS_RE = re.compile(r"^[0-9]{1,12}$")
SCORE_RE = re.compile(r"^[0-9]{1,3}$")
FINAL_RE = re.compile(r"^Final(/[0-9]*OT)?$")
INSTANT_RE = re.compile(r"^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2})(?::([0-9]{2}))?(Z|[+-][0-9]{2}:[0-9]{2})$")
TEAM_HREF_RE = re.compile(r"^(?:https?://www\.espn\.com)?/college-football/team/_/id/([0-9]{1,12})(?:/[^\s\"'<>]*)?$")
NAV_ID_RE = re.compile(r"^gamepackage-([0-9]{1,12})$")
GAME_PATH_RE = re.compile(r"^/college-football/game/_/gameId/([0-9]{1,12})$")
REPLAY_PATH_RE = re.compile(r"^/web/([0-9]{14})id_/(.+)$")
ORIGIN_TOLERANCE = _dt.timedelta(seconds=300)
UTC = _dt.timezone.utc
TRUE, FALSE, UNKNOWN = base.TRUE, base.FALSE, base.UNKNOWN
NO_ARCHIVE = "NO_QUALIFIED_ARCHIVE_ASSERTION"


class ArchiveEvidenceError(base.SourceTimeQueryError):
    """A refused archive sidecar or archive query."""


def _refuse(code: str, message: str) -> ArchiveEvidenceError:
    return ArchiveEvidenceError(code, message)


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------------------------- receipt helpers

def _fmt(value: _dt.datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _http_date(text: Any) -> _dt.datetime:
    if not isinstance(text, str) or not text.strip().endswith("GMT"):
        raise ValueError("HTTP_DATE_NOT_GMT")
    parsed = email.utils.parsedate_to_datetime(text)
    if parsed is None or parsed.utcoffset() != _dt.timedelta(0):
        raise ValueError("HTTP_DATE_MALFORMED")
    return parsed.astimezone(UTC)


def _ts14(text: str) -> _dt.datetime:
    if not TS14_RE.match(text or ""):
        raise ValueError("TIMESTAMP_NOT_14_DIGITS")
    return _dt.datetime.strptime(text, "%Y%m%d%H%M%S").replace(tzinfo=UTC)


def equivalent_original(url: Any, game_id: str) -> bool:
    try:
        parts = urllib.parse.urlsplit(str(url))
        port = parts.port
    except ValueError:
        return False
    if parts.scheme not in ("http", "https") or (parts.hostname or "").lower() != "www.espn.com":
        return False
    if port not in (None, 80, 443) or parts.query or parts.fragment or parts.username or parts.password:
        return False
    match = GAME_PATH_RE.match(parts.path)
    return bool(match) and match.group(1) == game_id


def replay_parts(url: Any) -> tuple[str, str] | None:
    try:
        parts = urllib.parse.urlsplit(str(url))
    except ValueError:
        return None
    if parts.scheme != "https" or (parts.hostname or "").lower() != "web.archive.org" or parts.port not in (None, 443):
        return None
    if parts.query or parts.fragment or parts.username or parts.password:
        return None
    match = REPLAY_PATH_RE.match(parts.path)
    return (match.group(1), match.group(2)) if match else None


def _header(headers: Any, name: str) -> Any:
    if isinstance(headers, dict):
        items = list(headers.items())
    else:
        items = [tuple(pair) for pair in headers or []]
    for key, value in items:
        if str(key).lower() == name.lower():
            return value
    return None


def _link_original(link: Any) -> str | None:
    if not isinstance(link, str):
        return None
    for match in re.finditer(r'<([^>]*)>\s*;\s*([^,<]*)', link):
        if re.search(r'\brel\s*=\s*"?original"?', match.group(2)):
            return match.group(1)
    return None


def upper_bound(memento: Any, origin: Any) -> tuple[str | None, list[str]]:
    """The conservative archive upper bound from the receipt literals and the receipt problems found."""
    problems = []
    try:
        memento_at = _http_date(memento)
    except (ValueError, TypeError):
        return None, ["MEMENTO_DATETIME_ABSENT" if memento is None else "MEMENTO_DATETIME_MALFORMED"]
    bound = memento_at.replace(microsecond=999999)
    if origin is not None:
        try:
            origin_at = _http_date(origin)
            if origin_at > memento_at + ORIGIN_TOLERANCE:
                problems.append("ORIGIN_DATE_CONTRADICTORY")
            elif origin_at > memento_at:
                bound = origin_at.replace(microsecond=999999)
        except (ValueError, TypeError):
            problems.append("ORIGIN_DATE_CONTRADICTORY")
    return _fmt(bound), problems


def event_interval(literal: str) -> tuple[str, str]:
    match = INSTANT_RE.match(literal or "")
    if not match:
        raise ValueError("EVENT_INSTANT_MALFORMED")
    year, month, day, hour, minute, second, zone = match.groups()
    tz = UTC if zone == "Z" else _dt.timezone((1 if zone[0] == "+" else -1) * _dt.timedelta(
        hours=int(zone[1:3]), minutes=int(zone[4:6])))
    value = _dt.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second or 0), tzinfo=tz)
    if second is None:
        return _fmt(value), _fmt(value + _dt.timedelta(seconds=59, microseconds=999999))
    return _fmt(value), _fmt(value.replace(microsecond=999999))


def local_dates(literal: str) -> list[str]:
    out = set()
    for bound in event_interval(literal):
        instant = _dt.datetime.strptime(bound, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)
        for hours in (-4, -10):
            out.add((instant + _dt.timedelta(hours=hours)).date().isoformat())
    return sorted(out)


def witness_value(witness: str, literal: str) -> Any:
    """The normalized value of one witness literal (None when the literal does not parse)."""
    if witness in ("JS_GAME_ID", "JS_HOME_TEAM_ID", "JS_AWAY_TEAM_ID"):
        return literal if DIGITS_RE.match(literal) else None
    if witness == "NAV_GAME_ID":
        match = NAV_ID_RE.match(literal)
        return match.group(1) if match else None
    if witness in ("HOME_TEAM_HREF", "AWAY_TEAM_HREF"):
        match = TEAM_HREF_RE.match(literal)
        return match.group(1) if match else None
    if witness in ("HOME_SCORE", "AWAY_SCORE"):
        return int(literal) if SCORE_RE.match(literal) else None
    if witness in ("JS_EVENT_TIMESTAMP", "INFO_EVENT_DATE"):
        try:
            event_interval(literal)
        except ValueError:
            return None
        return literal
    if witness in ("JS_STATUS", "STATUS_DETAIL"):
        return literal
    raise _refuse("ARCHIVE_SOURCE_INVALID", f"unknown witness {witness!r}")


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
    if (identity_document.get("stage"), identity_document.get("schema"), identity_document.get("db_schema_version")) \
            != ("archived-publication-database", ARCHIVE_DOCUMENT_SCHEMA, ARCHIVE_DB_SCHEMA):
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
            "record_counts": identity_document.get("record_counts")}


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
        if meta.get("schema_version") != ARCHIVE_DB_SCHEMA or meta.get("contract_id") not in KNOWN_CONTRACT_IDS:
            raise _refuse("ARCHIVE_SCHEMA_UNSUPPORTED", f"schema {meta.get('schema_version')!r} contract "
                                                        f"{meta.get('contract_id')!r}")
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
        receipt = json.loads(self._raw(control.get("raw_receipt_sha256")).decode("utf-8"))
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
        for mine, theirs in zip(self.requests, acq_requests):
            stripped = {k: v for k, v in mine.items() if k not in ("record_type", "body_path", "metadata_answer")}
            if stripped != theirs:
                raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"request {mine.get('seq')} differs from its receipt")
            host = (urllib.parse.urlsplit(str(mine["url"])).hostname or "").lower()
            if host not in ("archive.org", "web.archive.org") or (mine["kind"] == "METADATA") != (host == "archive.org"):
                raise _refuse("ARCHIVE_SOURCE_INVALID", f"request {mine['seq']} host {host}")
            by_seq[mine["seq"]] = (mine, acq_requests.index(theirs))
        for item in self.requests:
            if item.get("body_sha256"):
                self._raw(item["body_sha256"])
        payloads: dict[str, bytes] = {}
        games = {d["contest_key"]: d["game_id_literal"] for d in self.dispositions}
        for cap in self.captures:
            key = cap["contest_key"]
            if key not in games:
                raise _refuse("ARCHIVE_SOURCE_INVALID", f"capture for out-of-tranche key {key}")
            payload = payloads[cap["capture_id"]] = self._raw(cap["payload_sha256"])
            if cap["payload_path"] != f"raw/sha256/{cap['payload_sha256']}" or len(payload) != cap["payload_bytes"]:
                raise _refuse("ARCHIVE_PATH_INVALID", f"capture {cap['capture_id']} payload path")
            self._verify_capture_receipt(cap, by_seq, receipt, control, acq_id)
            self._verify_scopes(cap, payload)
        seen = set()
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for item in self.assertions:
            natural = (item["contest_key"], item["original_url"], item["capture_id"], item["payload_sha256"],
                       item["field"], item["witness"], item["source_revision"], tuple(item["witness_span"]))
            if natural in seen:
                raise _refuse("ARCHIVE_DUPLICATE_ASSERTION", f"duplicate assertion {natural[:7]}")
            seen.add(natural)
            cap = next((c for c in self.captures if c["capture_id"] == item["capture_id"]), None)
            if cap is None or cap["contest_key"] != item["contest_key"] or cap["payload_sha256"] != item[
                    "payload_sha256"] or item["source_revision"] != cap["capture_id"] or \
                    item["original_url"] != cap["original_url"]:
                raise _refuse("ARCHIVE_SOURCE_INVALID", "assertion does not belong to its capture")
            if item["field"] not in FIELDS or item["witness"] not in FIELD_WITNESSES[item["field"]] or \
                    item["field_role"] != base.ROLES[item["field"]]:
                raise _refuse("ARCHIVE_SOURCE_INVALID", f"{item['field']} cannot be witnessed by {item['witness']}")
            start, end = item["witness_span"]
            payload = payloads[item["capture_id"]]
            if not (0 <= start < end <= len(payload)) or payload[start:end] != str(item["literal"]).encode("utf-8"):
                raise _refuse("ARCHIVE_WITNESS_MISMATCH", f"{item['capture_id']} {item['witness']} literal")
            if not any(s["kind"] == WITNESS_SCOPE[item["witness"]] and s["span"][0] <= start and end <= s["span"][1]
                       for s in cap["main_element_spans"]):
                raise _refuse("ARCHIVE_WITNESS_OUT_OF_SCOPE", f"{item['capture_id']} {item['witness']} span")
            value = witness_value(item["witness"], item["literal"])
            expected = {"namespace": "ESPN_TEAM_ID", "value": value} if item["field"] in (
                "a_participant", "b_participant") and value is not None else value
            if item["value"] != expected or (value is None) != (item["corroboration"] == "UNPARSEABLE"):
                raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{item['capture_id']} {item['witness']} value")
            if item["field_state"] != cap["field_states"][item["field"]]:
                raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{item['capture_id']} {item['field']} state")
            grouped.setdefault((item["capture_id"], item["field"]), []).append(item)
        for cap in self.captures:
            self._verify_field_states(cap, grouped, payloads[cap["capture_id"]])
        for disposition in self.dispositions:
            self._verify_disposition(disposition)

    def _verify_capture_receipt(self, cap: dict[str, Any], by_seq: dict[int, Any], control_receipt: dict[str, Any],
                                control: dict[str, Any], acq_id: str) -> None:
        game = next(d["game_id_literal"] for d in self.dispositions if d["contest_key"] == cap["contest_key"])
        if cap["origin"] == "WORKER_ARCHIVE_REPLAY":
            if cap["request_seq"] not in by_seq:
                raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"{cap['capture_id']} names no request")
            request, index = by_seq[cap["request_seq"]]
            final_url, status, headers = request["url"], request["http_status"], request["headers"]
            if request["kind"] != "REPLAY" or request["contest_key"] != cap["contest_key"] or \
                    request["body_sha256"] != cap["payload_sha256"] or \
                    (cap["receipt_document"], cap["receipt_document_sha256"], cap["receipt_pointer"]) != (
                    f"acquisition/sha256/{acq_id}/acquisition.json", acq_id, f"/requests/{index}"):
                raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"{cap['capture_id']} receipt binding")
            retrieval = cap["clocks"]["retrieval"]
            if (retrieval["role"], retrieval["earliest_utc"], retrieval["latest_utc"]) != (
                    "EXACT_REQUEST_INTERVAL", request["started_utc"], request["ended_utc"]):
                raise _refuse("ARCHIVE_CLOCK_FORGED", f"{cap['capture_id']} retrieval clock")
        elif cap["origin"] == "MANAGER_RETAINED_CONTROL_REPLAY":
            if cap["payload_sha256"] != control.get("payload_sha256") or \
                    cap["receipt_document_sha256"] != control.get("raw_receipt_sha256") or \
                    cap["contest_key"] != control.get("contest_key") or cap["request_seq"] is not None:
                raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"{cap['capture_id']} control binding")
            final_url, status, headers = control_receipt["final_url"], control_receipt["status"], \
                control_receipt["headers"]
            observed = _dt.datetime.fromisoformat(control_receipt["observed_at"]).astimezone(UTC)
            retrieval = cap["clocks"]["retrieval"]
            if (retrieval["role"], retrieval["latest_utc"]) != ("RECORDED_POSSESSION_UPPER_BOUND", _fmt(observed)):
                raise _refuse("ARCHIVE_CLOCK_FORGED", f"{cap['capture_id']} control retrieval clock")
        else:
            raise _refuse("ARCHIVE_SOURCE_INVALID", f"capture origin {cap['origin']!r}")
        memento, origin = _header(headers, "Memento-Datetime"), _header(headers, "x-archive-orig-date")
        literals = (final_url, status, memento, origin, _link_original(_header(headers, "Link")),
                    _header(headers, "Content-Type") or "")
        if literals != (cap["final_url"], cap["http_status"], cap["memento_datetime_literal"],
                        cap["origin_date_literal"], cap["link_original"], cap["content_type"]):
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"{cap['capture_id']} receipt literals")
        parts = replay_parts(final_url)
        if not parts or cap["capture_id"] != f"wayback:{parts[0]}:{cap['payload_sha256']}" or \
                cap["wayback_timestamp"] != parts[0] or cap["original_url"] != parts[1]:
            raise _refuse("ARCHIVE_CLOCK_FORGED", f"{cap['capture_id']} capture identity")
        bound, problems = upper_bound(memento, origin)
        clock = cap["clocks"]["archive_capture"]
        if clock["role"] != "ARCHIVE_CAPTURE_UPPER_BOUND" or clock["latest_utc"] != bound or \
                clock["earliest_utc"] is not None or clock["literal"] != memento:
            raise _refuse("ARCHIVE_CLOCK_FORGED", f"{cap['capture_id']} upper bound {clock['latest_utc']} != {bound}")
        try:
            timestamps_agree = _http_date(memento) == _ts14(parts[0])
        except (ValueError, TypeError):
            timestamps_agree = False
        receipt_ok = (equivalent_original(parts[1], game) and timestamps_agree and not problems and
                      equivalent_original(cap["link_original"], game) and status == 200 and
                      str(cap["content_type"]).lower().startswith("text/html"))
        if cap["state"] == "QUALIFIED" and not receipt_ok:
            raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{cap['capture_id']} is qualified with failing receipts")
        if cap["state"] not in ("QUALIFIED", "QUARANTINED") or (cap["state"] == "QUALIFIED") == bool(
                cap["quarantine_reasons"]):
            raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{cap['capture_id']} state")

    def _verify_scopes(self, cap: dict[str, Any], payload: bytes) -> None:
        for scope in cap["main_element_spans"]:
            start, end = scope["span"]
            marker, inner = SCOPE_MARKERS.get(scope["kind"], (None, None))
            if marker is None or not (0 <= start < end <= len(payload)) or payload[start:start + len(marker)] != marker:
                raise _refuse("ARCHIVE_WITNESS_OUT_OF_SCOPE", f"{cap['capture_id']} scope {scope}")
            if inner is not None:
                tag_end = payload.find(b">", start)
                if tag_end < 0 or inner not in payload[start:tag_end]:
                    raise _refuse("ARCHIVE_WITNESS_OUT_OF_SCOPE", f"{cap['capture_id']} scope {scope['kind']}")

    def _verify_field_states(self, cap: dict[str, Any], grouped: dict[tuple[str, str], list[dict[str, Any]]],
                             payload: bytes) -> None:
        contest = self.source.contest(cap["contest_key"])
        if contest is None:
            raise _refuse("ARCHIVE_PARENT_MISMATCH", f"{cap['contest_key']} is not a source-time contest")
        record = contest["record"]
        parent = {a["field"]: a["parent_value"] for a in contest["assertions"]}
        ids = {"a": record["a_cfbd_team_id"]["value"], "b": record["b_cfbd_team_id"]["value"]}
        states = cap["field_states"]
        if set(states) != set(FIELDS):
            raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{cap['capture_id']} field states")
        qualified = [f for f in FIELDS if states[f] == QUALIFIED]
        if qualified and cap["state"] != "QUALIFIED":
            raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{cap['capture_id']} qualifies fields while quarantined")
        game = next(d["game_id_literal"] for d in self.dispositions if d["contest_key"] == cap["contest_key"])
        if cap["state"] == "QUALIFIED":
            nav = [s for s in cap["main_element_spans"] if s["kind"] == "NAV"]
            if len(nav) != 1 or (b'data-id="gamepackage-' + game.encode("ascii") + b'"') not in \
                    payload[nav[0]["span"][0]:payload.find(b">", nav[0]["span"][0])]:
                raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{cap['capture_id']} main element is another game")
        orientation = cap["orientation"]
        sides: dict[str, str] = {}
        for field in qualified:
            items = grouped.get((cap["capture_id"], field)) or []
            if not items or any(i["corroboration"] != "AGREES_WITH_PARENT" for i in items):
                raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{cap['capture_id']} {field} qualified without agreement")
            values = {json.dumps(i["value"], sort_keys=True) for i in items}
            if (len(values) != 1 and field != "completion") or any(i["parent_value"] != parent.get(field)
                                                                   for i in items):
                raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{cap['capture_id']} {field} values")
            value = items[0]["value"]
            if field == "contest_date":
                if {i["witness"] for i in items} != FIELD_WITNESSES["contest_date"] or \
                        record["contest_date"] not in local_dates(value):
                    raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{cap['capture_id']} contest date")
            elif field in ("a_participant", "b_participant"):
                letter = field[0]
                names = {i["witness"] for i in items}
                side = "HOME" if names == {"JS_HOME_TEAM_ID", "HOME_TEAM_HREF"} else (
                    "AWAY" if names == {"JS_AWAY_TEAM_ID", "AWAY_TEAM_HREF"} else None)
                if side is None or value != {"namespace": "ESPN_TEAM_ID", "value": ids[letter]} or \
                        orientation.get(f"{letter}_side") != side:
                    raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{cap['capture_id']} {field} orientation")
                sides[letter] = side
            elif field == "completion":
                literal = {i["witness"]: i["literal"] for i in items}
                if set(literal) != FIELD_WITNESSES["completion"] or len(items) != 2 or literal["JS_STATUS"] != "post" \
                        or not FINAL_RE.match(literal["STATUS_DETAIL"]) or parent.get("completion") != "COMPLETED":
                    raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{cap['capture_id']} completion")
            else:
                letter = field[0]
                if len(items) != 1 or items[0]["witness"] != f"{orientation.get(f'{letter}_side')}_SCORE" or \
                        value != parent.get(field) or states["completion"] != QUALIFIED:
                    raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{cap['capture_id']} {field} score orientation")
        if ("a_points" in qualified or "b_points" in qualified) and not (
                "a_participant" in qualified and "b_participant" in qualified):
            raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{cap['capture_id']} scores without oriented participants")
        if len(sides) == 2 and sides["a"] == sides["b"]:
            raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{cap['capture_id']} both participants on one side")
        if states.get("season") == QUALIFIED:
            raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{cap['capture_id']} season is never witnessed")
        bound = cap["clocks"]["archive_capture"]["latest_utc"]
        if qualified and "completion" in qualified and bound and _dt.datetime.strptime(
                bound, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC) < base.earliest_event_instant(record["contest_date"]):
            raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{cap['capture_id']} outcome before the event date")

    def _verify_disposition(self, disposition: dict[str, Any]) -> None:
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
        mine = [c for c in self.captures if c["contest_key"] == key]
        if disposition["capture_ids"] != [c["capture_id"] for c in mine] or \
                disposition["qualified_capture_ids"] != [c["capture_id"] for c in mine if c["state"] == "QUALIFIED"]:
            raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{key} capture accounting")
        requests = [r for r in self.requests if r["contest_key"] == key]
        if (disposition["request_count"], disposition["metadata_requests"], disposition["replay_requests"]) != (
                len(requests), sum(1 for r in requests if r["kind"] == "METADATA"),
                sum(1 for r in requests if r["kind"] == "REPLAY")):
            raise _refuse("ARCHIVE_RECEIPT_ALTERED", f"{key} request accounting")
        for field in WITNESSABLE:
            bounds = sorted(c["clocks"]["archive_capture"]["latest_utc"] for c in mine
                            if c["field_states"][field] == QUALIFIED)
            if disposition["field_support"].get(field) != (bounds[0] if bounds else None):
                raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{key} {field} support")
        supported = [f for f in WITNESSABLE if disposition["field_support"].get(f)]
        if disposition["disposition"] in ("CONTROL_REUSED_QUALIFIED", "ARCHIVED_VERSION_QUALIFIED_ALL_WITNESSABLE_FIELDS") \
                and len(supported) != len(WITNESSABLE):
            raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{key} disposition overstates support")
        if disposition["disposition"] == "ARCHIVED_VERSION_QUALIFIED_PARTIAL_FIELDS" and not supported:
            raise _refuse("ARCHIVE_SEMANTIC_FORGERY", f"{key} disposition overstates support")

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
                "verification": "SIDECAR_RAW_RECEIPT_AND_SEMANTIC_REDERIVATION_PASSED", **ARCHIVE_ROW_LABELS}

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

r"""Read-only verified reader of the fixed C37 2026 availability source/parser assertions (BAT-733, TP62-A01).

:class:`AvailabilityEvidence` opens exactly the literal local database file and data root a caller names and serves
the existing ``availability_statement_successor`` (1,592 source-cell assertions), ``availability_opportunity`` (3,474
retained schedule-record x program-side occurrences, 3,220 business keys) and ``availability_policy`` (13 policy
observations) records under the builtin profile :data:`~aggie_analytics.availability_evidence.profile.PROFILE` only.

Before any record is interpreted the reader (fixed order, each refusal for its own cause):

1. refuses network, device and namespace spellings of the database and the data root before any filesystem access
   (the BAT-717 literal-location core), never creates a missing input;
2. hashes the whole database file and refuses any byte difference from the builtin anchor
   (``DATABASE_IDENTITY_MISMATCH``) before a caller pin is compared (``EXPECTED_SHA256_MISMATCH``): a caller pin only
   adds a constraint and cannot bless other bytes;
3. reads each of the five report/posting witnesses once from ``<data-root>/<frozen relative path>`` and verifies its
   SHA-256 and size on those same bytes, which are the bytes it then parses;
4. verifies the three closed table schemas, every column's SQLite storage class, every key, the row counts and
   contiguous rowids, strictly decodes every JSON-text and Boolean column and re-derives the frozen population;
5. re-hashes the database file after reading and refuses any change during the session
   (``INPUT_CHANGED_DURING_SESSION``);
6. recomputes the frozen rules identity (``QUALIFICATION_RULES_MISMATCH``) and, once pinned, the qualified audit
   identity of the complete per-row qualification collection (``QUALIFICATION_AUDIT_MISMATCH``).

Each served row keeps the original record in its original schema beside a separate ``qualification`` object (and, for
opportunities, a ``source_occurrence`` wrapper naming the pinned database SHA-256, table and original SQLite rowid).
No row is dropped for being unresolved, disputed or quarantined. Nothing here establishes a current or historical
availability or health state, report completeness, first-known time or PIT eligibility.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Callable, Iterable

from aggie_analytics import readonly_sqlite
from aggie_analytics.availability_evidence import audit as _audit
from aggie_analytics.availability_evidence import profile as P

REQUEST_EXIT = 2
INTEGRITY_EXIT = 3
_INTEGRITY = frozenset(P.RULES["refusals"]["integrity"])
_REQUEST = frozenset(P.RULES["refusals"]["request"])


class AvailabilityError(Exception):
    """A controlled refusal with a stable code; integrity failures carry exit 3, request refusals exit 2."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        if code not in _INTEGRITY and code not in _REQUEST:
            raise ValueError(f"undeclared refusal code {code}")
        self.code = code
        self.detail = detail
        self.refusal_class = "INPUT_INTEGRITY_FAILURE" if code in _INTEGRITY else "REQUEST_REFUSED"
        self.exit_code = INTEGRITY_EXIT if code in _INTEGRITY else REQUEST_EXIT


# --------------------------------------------------------------------------------------------- strict decoding

class _StrictJSONError(ValueError):
    pass


def _no_constant(name: str) -> Any:
    raise _StrictJSONError(f"non-finite JSON number {name}")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise _StrictJSONError(f"duplicate JSON member {key!r}")
        out[key] = value
    return out


def _depth(value: Any, limit: int, level: int = 1) -> None:
    if level > limit:
        raise _StrictJSONError(f"JSON nesting deeper than {limit}")
    if isinstance(value, dict):
        for item in value.values():
            _depth(item, limit, level + 1)
    elif isinstance(value, list):
        for item in value:
            _depth(item, limit, level + 1)


def strict_json(text: str | bytes, limit: int = P.RULES["original_record"]["json_max_depth"]) -> Any:
    """Strict JSON: valid UTF-8, no NaN/Infinity, no duplicate member names, bounded depth."""
    try:
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="strict")
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_no_constant)
    except RecursionError as exc:
        raise _StrictJSONError("JSON nesting too deep") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise _StrictJSONError(str(exc)[:200]) from exc
    _depth(value, limit)
    return value


_STORAGE = {int: "integer", str: "text", type(None): "null", float: "real", bytes: "blob"}


def decode_record(grain: str, raw: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """The original record in its original column order with documented JSON/Boolean decoding (RECORD_INVALID
    otherwise)."""
    out: dict[str, Any] = {}
    for column, allowed in spec["columns"].items():
        value = raw[column]
        storage = _STORAGE.get(type(value), "other")
        if storage not in allowed:
            raise AvailabilityError("RECORD_INVALID", f"{grain} column {column} holds a {storage} value; allowed "
                                                      f"{allowed}")
        if column in spec["json_columns"] and value is not None:
            try:
                decoded = strict_json(value)
            except _StrictJSONError as exc:
                raise AvailabilityError("RECORD_INVALID", f"{grain} column {column} is not strict JSON: {exc}") from None
            want = spec["json_columns"][column]
            if (want == "object" and not isinstance(decoded, dict)) or (want == "list" and not isinstance(decoded, list)):
                raise AvailabilityError("RECORD_INVALID", f"{grain} column {column} is not a JSON {want}")
            value = decoded
        elif column in spec["boolean_columns"]:
            if type(value) is not int or value not in (0, 1):
                raise AvailabilityError("RECORD_INVALID", f"{grain} Boolean column {column} holds {value!r}")
            value = bool(value)
        out[column] = value
    return out


# --------------------------------------------------------------------------------------------- locations

def _io_path(path: Path) -> Path:
    """A path every file API can open: the extended form beyond the classic Windows limit (never re-normalized)."""
    text = os.fspath(path)
    if os.name == "nt" and not text.startswith("\\\\?\\") and len(os.path.abspath(text)) >= 250:
        return Path("\\\\?\\" + os.path.abspath(text))
    return Path(text)


def literal_database(database: Any) -> str:
    """The validated absolute literal location of the database (lexical; no filesystem access)."""
    try:
        return readonly_sqlite.literal_path(database)
    except readonly_sqlite.DatabaseLocationError as exc:
        raise AvailabilityError(exc.code, exc.detail) from None


def literal_data_root(data_root: Any) -> str:
    """The validated absolute literal location of the data root (the same lexical rules; no filesystem access)."""
    try:
        return readonly_sqlite.literal_path(data_root)
    except readonly_sqlite.DatabaseLocationError as exc:
        raise AvailabilityError("DATA_ROOT_LOCATION_UNSUPPORTED", exc.detail) from None


def _file_identity(path: Path) -> tuple[str, int, int]:
    digest = hashlib.sha256()
    io = _io_path(path)
    with io.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    st = os.stat(io)
    return digest.hexdigest(), st.st_size, st.st_mtime_ns


# --------------------------------------------------------------------------------------------- witnesses

_LOCATOR = re.compile(P.RULES["statement_qualification"]["source_cell"]["locator"])
_MONTHS = {m: i for i, m in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
                                        "Dec"), 1)}
_FULL_MONTHS = {m: i for i, m in enumerate(("January", "February", "March", "April", "May", "June", "July", "August",
                                             "September", "October", "November", "December"), 1)}
_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def parse_report_date(text: str) -> dt.date | None:
    """A raw report Date cell: 'M/D/YY' or 'Ddd, Mon D, YYYY' (weekday consistent), else None."""
    m = re.fullmatch(r"([0-9]{1,2})/([0-9]{1,2})/([0-9]{2})", text)
    try:
        if m:
            return dt.date(2000 + int(m[3]), int(m[1]), int(m[2]))
        m = re.fullmatch(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun), ([A-Z][a-z]{2}) ([0-9]{1,2}), ([0-9]{4})", text)
        if m and m[2] in _MONTHS:
            day = dt.date(int(m[4]), _MONTHS[m[2]], int(m[3]))
            return day if _WEEKDAYS[day.weekday()][:3] == m[1] else None
    except ValueError:
        return None
    return None


def _table_rows(witness_id: str, spec: dict[str, Any], data: bytes) -> list[list[str]]:
    try:
        if spec["format"] == "TAB_SEPARATED_TEXT_TABLE":
            text = data.decode("utf-8", errors="strict")
            lines = text.split("\n")
            if lines and lines[-1] == "":
                lines = lines[:-1]
            rows = [line.split("\t") for line in lines]
        else:
            doc = strict_json(data)
            if not isinstance(doc, dict) or not isinstance(doc.get("rows"), list):
                raise _StrictJSONError("no rows list")
            rows = doc["rows"]
    except (UnicodeDecodeError, _StrictJSONError) as exc:
        raise AvailabilityError("WITNESS_FORMAT_INVALID", f"{witness_id}: {exc}") from None
    if not rows or list(rows[0]) != list(P.SOURCE_HEADER) or \
            any(not isinstance(r, list) or len(r) != len(P.SOURCE_HEADER) or not all(isinstance(c, str) for c in r)
                for r in rows) or len(rows) - 1 != spec["player_rows"]:
        raise AvailabilityError("WITNESS_FORMAT_INVALID", f"{witness_id}: not the declared {spec['player_rows']}-row "
                                                          f"report table with the frozen header")
    return rows


def _witness_meta(spec: dict[str, Any], data: bytes) -> dict[str, Any]:
    if spec["format"] == "TAB_SEPARATED_TEXT_TABLE":
        return {"rendered_utc": None, "url": None, "embedded_in": None}
    doc = strict_json(data)
    return {"rendered_utc": doc.get("rendered_utc"), "url": doc.get("url"), "embedded_in": doc.get("embedded_in")}


_POSTED = re.compile(r"Report posted on (Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
                     r"(January|February|March|April|May|June|July|August|September|October|November|December) "
                     r"([0-9]{1,2}) at ([0-9]{1,2}):([0-9]{2})(am|pm) ET")
_FOOTER = re.compile(r"(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY), "
                     r"(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER) "
                     r"([0-9]{1,2}) \|")
_HEADING_YEAR = re.compile(r"Games of .* ([0-9]{4})$")
_ENTRY = re.compile(r"^(\S+) #([0-9]{1,3}) (.+)$")


def _us_eastern_offset(day: dt.date, hour: int) -> int:
    """US Eastern offset in hours for a local wall time: -4 in daylight time (second Sunday of March 2:00 to the first
    Sunday of November 2:00), else -5 (pure arithmetic; no time-zone database)."""
    def nth_sunday(year: int, month: int, n: int) -> dt.date:
        first = dt.date(year, month, 1)
        return first + dt.timedelta(days=(6 - first.weekday()) % 7 + 7 * (n - 1))
    start, end = nth_sunday(day.year, 3, 2), nth_sunday(day.year, 11, 1)
    local = (day, hour)
    return -4 if (start, 2) <= local < (end, 2) else -5


def parse_posting(data: bytes) -> dict[str, Any]:
    """The later posting capture: its cards with kind, posted-claim text and UTC instant, the game date and the team
    columns with their status headings and entries."""
    try:
        doc = strict_json(data)
        heading = str(doc.get("h1") or "")
        year_m = _HEADING_YEAR.search(heading)
        cards = []
        for index, card in enumerate(doc["cards"]):
            text = str(card["text"])
            lines = text.split("\n")
            kind = lines[0]
            posted_m = _POSTED.search(text)
            footer_m = _FOOTER.search(text)
            game_date = None
            if footer_m and year_m:
                game_date = dt.date(int(year_m[1]), _FULL_MONTHS[footer_m[2].title()], int(footer_m[3]))
                if _WEEKDAYS[game_date.weekday()].upper() != footer_m[1]:
                    game_date = None
            posted = None
            if posted_m and year_m:
                day = dt.date(int(year_m[1]), _FULL_MONTHS[posted_m[2]], int(posted_m[3]))
                hour = int(posted_m[4]) % 12 + (12 if posted_m[6] == "pm" else 0)
                local = dt.datetime(day.year, day.month, day.day, hour, int(posted_m[5]))
                offset = _us_eastern_offset(day, hour)
                posted = {"text": posted_m[0], "weekday_consistent": _WEEKDAYS[day.weekday()] == posted_m[1],
                          "local_wall_time": local.isoformat(), "utc_offset_hours": offset,
                          "utc": (local - dt.timedelta(hours=offset)).replace(tzinfo=dt.timezone.utc).isoformat()}
            columns = []
            for cindex, column in enumerate(card.get("columns") or []):
                entries, current = [], None
                for line in str(column.get("text") or "").split("\n"):
                    if not line:
                        continue
                    if _ENTRY.match(line):
                        m = _ENTRY.match(line)
                        entries.append({"heading": current, "entry": line, "position": m[1], "jersey": f"#{m[2]}",
                                        "player": m[3]})
                    else:
                        current = line
                columns.append({"column": cindex, "team": column.get("team"), "entries": entries})
            cards.append({"card": index, "kind": kind, "posted": posted, "game_date": game_date.isoformat()
                          if game_date else None, "columns": columns})
        return {"rendered_utc": doc.get("rendered_utc"), "heading": heading, "cards": cards,
                "card_kinds": dict(collections.Counter(c["kind"] for c in cards))}
    except (_StrictJSONError, KeyError, TypeError, ValueError) as exc:
        raise AvailabilityError("WITNESS_FORMAT_INVALID", f"{P.POSTING_WITNESS}: {exc}") from None


# --------------------------------------------------------------------------------------------- times

def parse_instant(text: Any) -> dt.datetime | None:
    if not isinstance(text, str):
        return None
    try:
        value = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return value.astimezone(dt.timezone.utc) if value.tzinfo else None


_CUTOFF = re.compile(P.RULES["cutoff"]["grammar"])


def parse_cutoff(text: str) -> dt.datetime:
    """A cutoff instant with an explicit offset, normalized to UTC (date-only, naive and malformed values refused)."""
    if not isinstance(text, str) or not _CUTOFF.match(text):
        raise AvailabilityError("INVALID_SELECTOR", f"--cutoff must be an ISO-8601 instant with an explicit offset, "
                                                    f"got {text!r}")
    value = parse_instant(text)
    if value is None:
        raise AvailabilityError("INVALID_SELECTOR", f"--cutoff is not a valid instant: {text!r}")
    return value


def relation(clock: dt.datetime | None, cutoff: dt.datetime) -> str:
    if clock is None:
        return "UNKNOWN"
    return "BEFORE" if clock < cutoff else "AT" if clock == cutoff else "AFTER"


# --------------------------------------------------------------------------------------------- selectors

_LITERAL_MAX = 200


def literal_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > _LITERAL_MAX or \
            any(ord(c) < 32 or ord(c) == 127 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise AvailabilityError("INVALID_SELECTOR", f"{name} must be exact non-empty literal text without leading or "
                                                    f"trailing white space, control characters or lone surrogates")
    return value


def validate_selectors(grain: str, selectors: dict[str, Any]) -> dict[str, Any]:
    """Applicability and grammar of every supplied selector (no data access): SELECTOR_NOT_APPLICABLE /
    INVALID_SELECTOR / SEASON_NOT_IN_PROFILE for a foreign season."""
    if grain not in P.GRAINS:
        raise AvailabilityError("ARGUMENT_INVALID", f"unknown grain {grain!r}")
    out: dict[str, Any] = {}
    for option, raw in selectors.items():
        if raw is None:
            continue
        spec = P.RULES["selectors"].get(option)
        if spec is None:
            raise AvailabilityError("ARGUMENT_INVALID", f"unknown selector {option}")
        if grain not in spec["grains"]:
            raise AvailabilityError("SELECTOR_NOT_APPLICABLE", f"{option} does not apply to the {grain} grain")
        grammar = spec["grammar"]
        if grammar == "LITERAL_TEXT":
            out[option] = literal_text(option, raw)
        elif grammar == "ENUM":
            if raw not in spec["values"]:
                raise AvailabilityError("INVALID_SELECTOR", f"{option} must be one of {spec['values']}, got {raw!r}")
            out[option] = raw
        elif grammar == "CUTOFF":
            out[option] = parse_cutoff(raw)
        else:
            if not isinstance(raw, str) or not re.fullmatch(grammar, raw):
                raise AvailabilityError("INVALID_SELECTOR", f"{option} is malformed: {raw!r}")
            if option == "--statement-id":
                value = int(raw)
                if value > 9223372036854775807:
                    raise AvailabilityError("INVALID_SELECTOR", f"{option} exceeds the signed 64-bit range")
                out[option] = value
            elif option in ("--season", "--policy-season"):
                out[option] = int(raw)
            elif option == "--person-id" and raw.startswith("OFFICIAL:") and int(raw.split(":")[-2]) != \
                    P.PROFILE["report_season"]:
                raise AvailabilityError("SEASON_NOT_IN_PROFILE", f"{option} names roster season {raw.split(':')[-2]}; "
                                                                 f"the fixed profile holds {P.PROFILE['report_season']}")
            else:
                out[option] = raw
    for option in ("--season",):
        if option in out and out[option] != P.PROFILE["report_season"]:
            raise AvailabilityError("SEASON_NOT_IN_PROFILE", f"{option} {out[option]} is not the fixed profile season "
                                                             f"{P.PROFILE['report_season']}")
    return out


def validate_paging(limit: Any, offset: Any, all_rows: bool) -> tuple[int | None, int]:
    paging = P.RULES["paging"]
    if all_rows and (limit is not None or offset is not None):
        raise AvailabilityError("PAGING_INVALID", "--all is mutually exclusive with --limit and --offset")
    if all_rows:
        return None, 0
    lim = paging["default_limit"] if limit is None else limit
    off = 0 if offset is None else offset
    for name, value in (("--limit", lim), ("--offset", off)):
        if isinstance(value, bool) or not isinstance(value, (int, str)) or \
                not re.fullmatch(paging["grammar"], str(value)):
            raise AvailabilityError("PAGING_INVALID", f"{name} must be a non-negative decimal integer, got {value!r}")
    lim, off = int(lim), int(off)
    if not paging["min_limit"] <= lim <= paging["max_limit"]:
        raise AvailabilityError("PAGING_INVALID", f"--limit must be between {paging['min_limit']} and "
                                                  f"{paging['max_limit']}")
    if off > paging["max_offset"]:
        raise AvailabilityError("PAGING_INVALID", "--offset exceeds the signed 64-bit range")
    return lim, off


# --------------------------------------------------------------------------------------------- the reader

def _sort_key(values: Iterable[Any]) -> tuple:
    return tuple((0, "") if v is None else (1, v) for v in values)


class AvailabilityEvidence:
    """A verified read-only session over the fixed C37 availability tables (see the module docstring). ``profile`` and
    ``hooks`` are internal: tests inject a trusted synthetic profile and a mid-session hook; the public CLI never
    does."""

    def __init__(self, database: Any, data_root: Any, *, expect_sha256: str | None = None,
                 profile: dict[str, Any] | None = None, rules: dict[str, Any] | None = None,
                 audit: dict[str, Any] | None = None, hooks: dict[str, Callable[[], None]] | None = None) -> None:
        self.profile = P.PROFILE if profile is None else profile
        self.rules = P.RULES if rules is None else rules
        self.audit_pin = _audit.QUALIFIED_AUDIT if audit is None else audit
        hooks = hooks or {}
        if P.rules_sha256(self.rules) != P.RULES_SHA256:
            raise AvailabilityError("QUALIFICATION_RULES_MISMATCH", "the packaged qualification rules differ from the "
                                                                    "frozen rules identity")
        if profile is None and P.profile_sha256(self.profile) != P.PROFILE_SHA256:
            raise AvailabilityError("PROFILE_INTEGRITY_MISMATCH", "the packaged builtin profile differs from its frozen "
                                                                  "identity")
        if expect_sha256 is not None and (not isinstance(expect_sha256, str) or
                                          not re.fullmatch(r"[0-9a-f]{64}", expect_sha256)):
            raise AvailabilityError("INVALID_SELECTOR", "--expect-sha256 must be 64 lower-case hex digits")
        db_location = literal_database(database)
        root_location = literal_data_root(data_root)
        db_path, root = Path(db_location), Path(root_location)
        if not _io_path(db_path).is_file():
            raise AvailabilityError("DATABASE_MISSING", f"no database file at {db_location}")
        if not _io_path(root).is_dir():
            raise AvailabilityError("DATA_ROOT_MISSING", f"no data root directory at {root_location}")
        anchor = self.profile["database"]
        before = _file_identity(db_path)
        if before[0] != anchor["sha256"] or before[1] != anchor["bytes"]:
            raise AvailabilityError("DATABASE_IDENTITY_MISMATCH", f"the database bytes (sha256 {before[0]}, {before[1]} "
                                                                  f"bytes) are not the builtin {self.profile['profile_id']} "
                                                                  f"database {anchor['sha256']}")
        if expect_sha256 is not None and expect_sha256 != before[0]:
            raise AvailabilityError("EXPECTED_SHA256_MISMATCH", f"--expect-sha256 {expect_sha256} differs from the "
                                                                f"verified database {before[0]}")
        self.database_location, self.data_root_location = db_location, root_location
        self.witness_bytes: dict[str, bytes] = {}
        for wid, spec in self.profile["witnesses"].items():
            path = root.joinpath(*spec["relative_path"].split("/"))
            io = _io_path(path)
            if not io.is_file():
                raise AvailabilityError("WITNESS_MISSING", f"{wid} is not present at {spec['relative_path']} under the "
                                                           f"data root")
            data = io.read_bytes()
            if hashlib.sha256(data).hexdigest() != spec["sha256"] or len(data) != spec["bytes"]:
                raise AvailabilityError("WITNESS_IDENTITY_MISMATCH", f"{wid} bytes differ from the builtin witness "
                                                                     f"{spec['sha256']}")
            self.witness_bytes[wid] = data
        raw = self._read_tables(db_path)
        if "after_read" in hooks:
            hooks["after_read"]()
        after = _file_identity(db_path)
        if after != before:
            raise AvailabilityError("INPUT_CHANGED_DURING_SESSION", "the database changed while it was being read")
        self._decode(raw)
        self._parse_witnesses()
        self._qualify()
        self._population()
        self._check_audit()

    # ---- verification
    def _read_tables(self, db_path: Path) -> dict[str, list[tuple[int, dict[str, Any]]]]:
        try:
            conn = readonly_sqlite.connect_readonly(_io_path(db_path), immutable=True)
        except readonly_sqlite.DatabaseLocationError as exc:
            raise AvailabilityError(exc.code, exc.detail) from None
        except sqlite3.Error as exc:
            raise AvailabilityError("SCHEMA_MISMATCH", f"the database cannot be opened read-only: {exc}") from None
        try:
            out = {}
            for grain, spec in self.profile["tables"].items():
                columns = [r[1] for r in conn.execute(f'PRAGMA table_info("{spec["table"]}")')]
                if columns != list(spec["columns"]):
                    raise AvailabilityError("SCHEMA_MISMATCH", f"{spec['table']} columns {columns} differ from the "
                                                               f"closed schema {list(spec['columns'])}")
                cursor = conn.execute("SELECT rowid, " + ", ".join(f'"{c}"' for c in columns) +
                                      f' FROM "{spec["table"]}" ORDER BY rowid')
                rows = [(r[0], dict(zip(columns, r[1:]))) for r in cursor]
                if len(rows) != spec["rows"] or [r[0] for r in rows] != list(range(1, spec["rows"] + 1)):
                    raise AvailabilityError("SCHEMA_MISMATCH", f"{spec['table']} holds {len(rows)} rows (rowids "
                                                               f"1..{spec['rows']} expected)")
                out[grain] = rows
            return out
        except sqlite3.Error as exc:
            raise AvailabilityError("SCHEMA_MISMATCH", f"the database cannot be read: {exc}") from None
        finally:
            conn.close()

    def _decode(self, raw: dict[str, list[tuple[int, dict[str, Any]]]]) -> None:
        tables = self.profile["tables"]
        self.records: dict[str, list[tuple[int, dict[str, Any]]]] = {
            grain: [(rowid, decode_record(grain, rec, tables[grain])) for rowid, rec in rows]
            for grain, rows in raw.items()}
        ids = [r["availability_row_id"] for _rid, r in self.records["statement"]]
        if ids != [rid for rid, _r in self.records["statement"]]:
            raise AvailabilityError("RECORD_INVALID", "statement keys are not the unique contiguous 1-based sequence")
        pids = [r["policy_id"] for _rid, r in self.records["policy"]]
        if len(set(pids)) != len(pids):
            raise AvailabilityError("RECORD_INVALID", "policy_id is not unique")
        population = self.profile["population"]
        for _rid, r in self.records["statement"]:
            ident, contest = r["identity"], r["contest"]
            if not isinstance(ident.get("state"), str) or ident["state"] not in population["identity_states"] or \
                    not isinstance(contest.get("state"), str) or contest["state"] not in population["contest_states"] \
                    or r["stage"] not in P.STAGES or r["presence"] not in ("PUBLISHED_EMPTY", "PUBLISHED_VALUE") or \
                    r["source_sha256"] not in {self.profile["witnesses"][w]["sha256"] for w in P.PRIMARY_WITNESSES}:
                raise AvailabilityError("RECORD_INVALID", f"statement {r['availability_row_id']} names an undeclared "
                                                          f"state, stage, presence or source")
        for _rid, r in self.records["opportunity"]:
            if r["side"] not in ("home", "away") or r["state"] not in population["opportunity_states"]:
                raise AvailabilityError("RECORD_INVALID", "an opportunity names an undeclared side or state")

    def _parse_witnesses(self) -> None:
        by_sha = {}
        for wid in P.PRIMARY_WITNESSES:
            data = self.witness_bytes[wid]
            spec = self.profile["witnesses"][wid]
            rows = _table_rows(wid, spec, data)
            by_sha[spec["sha256"]] = {"id": wid, "spec": spec, "rows": rows, "meta": _witness_meta(spec, data)}
        self.tables_by_sha = by_sha
        self.posting = parse_posting(self.witness_bytes[P.POSTING_WITNESS])

    # ---- qualification
    def _cell(self, r: dict[str, Any]) -> dict[str, Any]:
        rules = self.rules["statement_qualification"]["source_cell"]
        witness = self.tables_by_sha[r["source_sha256"]]
        spec, meta = witness["spec"], witness["meta"]
        m = _LOCATOR.match(r["source_locator"])
        conflicts: list[dict[str, Any]] = []
        base = {"witness": witness["id"], "source_sha256": spec["sha256"], "row": None, "column": None}
        if not m or int(m[2]) >= len(witness["rows"]):
            return {**base, "state": rules["disputed"], "conflicts": [{"field": "source_locator",
                                                                      "original": r["source_locator"],
                                                                      "witness": "SOURCE_LOCATOR_NOT_RESOLVABLE"}],
                    "consequence": rules["consequence_of_dispute"], "source_empty": None, "fields_compared": 0}
        row_index, stage_token = int(m[2]), m[3]
        raw = witness["rows"][row_index]
        team, date_text, opponent, number, player = raw[0], raw[1], raw[2], raw[3], raw[4]
        cell = raw[P.SOURCE_HEADER.index(P.STAGE_COLUMNS[r["stage"]])]
        day = parse_report_date(date_text)
        contest = r["contest"]
        expected = {
            "source_sha256": (r["source_sha256"], spec["sha256"]),
            "locator_prefix": (m[1], spec["locator_prefix"]),
            "locator_stage": (stage_token, r["stage"]),
            "stage": (r["stage"], stage_token),
            "conference": (r["conference"], spec["conference"]),
            "report_vintage_retrieval_utc": (r["report_vintage_retrieval_utc"], spec["retrieval_observation_utc"]),
            "source_url": (r["source_url"], spec["source_url"]),
            "embedded_in": (r["embedded_in"], spec["embedded_in"]),
            "program_as_written": (r["program_as_written"], team),
            "date_as_written": (contest.get("date_as_written"), day.isoformat() if day else f"UNPARSED:{date_text}"),
            "contest_label": (r["contest_label"],
                              f"{day.month}/{day.day}/{day.year % 100:02d} {opponent}" if day else
                              f"UNPARSED:{date_text} {opponent}"),
            "jersey": (r["jersey"], number),
            "player_name": (r["player_name"], player),
            "exact_status_text": (r["exact_status_text"], cell),
            "presence": (r["presence"], "PUBLISHED_EMPTY" if cell == "-" else "PUBLISHED_VALUE"),
        }
        if "opponent_as_written" in contest:
            expected["opponent_as_written"] = (contest["opponent_as_written"], re.sub(r"^(vs\. |at )", "", opponent))
        if spec["format"] != "TAB_SEPARATED_TEXT_TABLE":
            expected["capture_rendered_utc"] = (spec["retrieval_observation_utc"], meta["rendered_utc"])
            expected["capture_url"] = (spec["source_url"], meta["url"])
            expected["capture_embedded_in"] = (spec["embedded_in"], meta["embedded_in"])
        for field, (original, witnessed) in expected.items():
            if original != witnessed:
                conflicts.append({"field": field, "original": original, "witness": witnessed})
        state = rules["verified"] if not conflicts else rules["disputed"]
        return {**base, "row": row_index, "column": P.STAGE_COLUMNS[r["stage"]], "state": state,
                "fields_compared": len(expected), "conflicts": conflicts,
                **({"consequence": rules["consequence_of_dispute"]} if conflicts else {}),
                "raw": {"team": team, "date": date_text, "opponent": opponent, "number": number, "player": player,
                        "cell": cell},
                "source_empty": cell == "-",
                **({"source_empty_meaning": self.rules["statement_qualification"]["status"]["source_empty"],
                    "original_empty_representation": {"exact_status_text": r["exact_status_text"],
                                                      "normalized_status": r["normalized_status"]}}
                   if cell == "-" else {})}

    def _publication(self, r: dict[str, Any]) -> dict[str, Any]:
        rules = self.rules["statement_qualification"]["publication"]
        posting_spec = self.profile["witnesses"][P.POSTING_WITNESS]
        if not r["publication_time_established"]:
            return {"state": rules["unknown"], "original_publication_utc": r["publication_utc"],
                    "original_publication_basis": r["publication_basis"], "authority": rules["authority"]}
        matches = []
        contest_date = r["contest"].get("date_as_written")
        for card in self.posting["cards"]:
            if card["kind"] != "INITIAL REPORT" or r["stage"] != "initial_status" or card["game_date"] != contest_date:
                continue
            for column in card["columns"]:
                if column["team"] != r["program_as_written"]:
                    continue
                for entry in column["entries"]:
                    if entry["jersey"] == r["jersey"] and entry["player"] == r["player_name"] and \
                            entry["heading"] == r["exact_status_text"].upper():
                        matches.append((card, column, entry))
        conflicts = []
        if len(matches) != 1:
            conflicts.append({"field": "posting_entry", "original": "publication_time_established=true",
                              "witness": f"{len(matches)} matching INITIAL REPORT entries"})
        else:
            card, column, entry = matches[0]
            posted = card["posted"] or {}
            capture = parse_instant(self.posting["rendered_utc"])
            claim = parse_instant(r["publication_utc"])
            if not posted.get("weekday_consistent"):
                conflicts.append({"field": "posted_weekday", "original": posted.get("text"), "witness": "INCONSISTENT"})
            if parse_instant(posted.get("utc")) != claim:
                conflicts.append({"field": "publication_utc", "original": r["publication_utc"],
                                  "witness": posted.get("utc")})
            if capture is None or claim is None or not capture > claim:
                conflicts.append({"field": "capture_later_than_claim", "original": r["publication_utc"],
                                  "witness": self.posting["rendered_utc"]})
        if conflicts:
            return {"state": rules["disputed"], "conflicts": conflicts,
                    "consequence": self.rules["statement_qualification"]["source_cell"]["consequence_of_dispute"],
                    "original_publication_utc": r["publication_utc"], "authority": rules["authority"]}
        card, column, entry = matches[0]
        return {"state": rules["witnessed"], "claim_utc": r["publication_utc"],
                "original_publication_basis": r["publication_basis"], "authority": rules["authority"],
                "witness": {"id": P.POSTING_WITNESS, "sha256": posting_spec["sha256"], "card": card["card"],
                            "card_kind": card["kind"], "posted_text": card["posted"]["text"],
                            "posted_local_wall_time_et": card["posted"]["local_wall_time"],
                            "posted_utc_offset_hours": card["posted"]["utc_offset_hours"],
                            "column": column["column"], "team": column["team"], "heading": entry["heading"],
                            "entry": entry["entry"], "game_date": card["game_date"]},
                "capture_observation_utc": self.posting["rendered_utc"],
                "not_established": ["FIRST_KNOWN_TIME", "IMMUTABLE_HISTORICAL_VERSION_SEAL", "PIT_PERMISSION",
                                    "EFFECTIVE_INTERVAL"]}

    def _identity(self, r: dict[str, Any]) -> dict[str, Any]:
        rules = self.rules["statement_qualification"]["identity"]
        ident = r["identity"]
        state = ident["state"]
        pid = ident.get("canonical_player_id")
        prefix = pid.split(":", 1)[0] if isinstance(pid, str) else None
        return {"state": rules["resolved"] if state.startswith("RESOLVED_") else state, "original_state": state,
                "source_scoped_person_id": pid, "id_scope": rules["scope"].get(prefix) if prefix else None,
                "global_person_identity": rules["global_person_identity"],
                "jersey_not_stated": state == "RESOLVED_UNIQUE_NAME_JERSEY_NOT_STATED",
                "roster_witness_proof": rules["roster_witness_proof"]}

    def _contest(self, r: dict[str, Any]) -> dict[str, Any]:
        rules = self.rules["statement_qualification"]["contest"]
        contest = r["contest"]
        state = contest["state"]
        return {"state": rules["bound"] if state == "CONTEST_BOUND" else
                rules["self_opponent"] if state == "CONTEST_LABEL_NAMES_THE_PROGRAM_ITSELF" else state,
                "original_state": state, "canonical_contest_id": contest.get("canonical_contest_id"),
                "schedule_witness_proof": rules["schedule_witness_proof"]}

    def _qualify(self) -> None:
        sq = self.rules["statement_qualification"]
        self.qualifications: dict[str, list[dict[str, Any]]] = {"statement": [], "opportunity": [], "policy": []}
        for _rid, r in self.records["statement"]:
            identity, contest = self._identity(r), self._contest(r)
            person_ok = identity["state"] == sq["identity"]["resolved"]
            contest_ok = contest["state"] == sq["contest"]["bound"]
            joint = sq["joint"][0 if person_ok and contest_ok else 1 if contest_ok else 2 if person_ok else 3]
            text = r["exact_status_text"]
            self.qualifications["statement"].append({
                "schema": self.rules["schema"],
                "key": {"table": self.profile["tables"]["statement"]["table"],
                        "availability_row_id": r["availability_row_id"]},
                "source_cell": self._cell(r),
                "stage_time": {"state": sq["stage_time"], "stage": r["stage"]},
                "publication": self._publication(r),
                "effective_time": {"state": sq["effective_time"], "original_effective_utc": r["effective_utc"]},
                "first_known": sq["first_known"],
                "identity": identity, "contest": contest, "joint": joint,
                "quarantine_flag": {"state": sq["quarantine_flag"], "original_quarantined": r["quarantined"],
                                    "agrees_with_identity_claim": r["quarantined"] == (not person_ok)},
                "status": {"literal_text": text, "meaning": sq["status"]["meaning"],
                           **({"note": sq["status"]["available"]} if text == "Available" else
                              {"note": sq["status"]["exempt"]} if text == "Exempt" else
                              {"note": sq["status"]["source_empty"]} if text == "-" else {})},
                "pit": {"original_pit_admitted": r["pit_admitted"], "pit_admission": "NOT_ADMITTED"},
                "health_inference": "NOT_ASSERTED"})
        oq = self.rules["opportunity_qualification"]
        groups: dict[tuple, list[int]] = collections.defaultdict(list)
        for rowid, r in self.records["opportunity"]:
            groups[(r["canonical_contest_id"], r["team_id"], r["side"])].append(rowid)
        by_rowid = dict(self.records["opportunity"])
        ingested = collections.Counter()
        for _rid, r in self.records["statement"]:
            cid = r["contest"].get("canonical_contest_id")
            if cid:
                ingested[(cid, r["program"])] += 1
        policy_ids = {r["policy_id"] for _rid, r in self.records["policy"]}
        db_sha = self.profile["database"]["sha256"]
        table = self.profile["tables"]["opportunity"]["table"]
        for rowid, r in self.records["opportunity"]:
            key = (r["canonical_contest_id"], r["team_id"], r["side"])
            siblings = groups[key]
            identical = all(by_rowid[s] == r for s in siblings)
            occurrence = oq["occurrence"]["singleton"] if len(siblings) == 1 else \
                oq["occurrence"]["exact_duplicate"] if identical else oq["occurrence"]["nonidentical_repeat"]
            policy = r["governing_policy"]
            counted = ingested.get((r["canonical_contest_id"], r["program"]), 0)
            self.qualifications["opportunity"].append({
                "schema": self.rules["schema"],
                "key": {"database_sha256": db_sha, "table": table, "original_sqlite_rowid": rowid},
                "occurrence": {"state": occurrence, "business_key": {"canonical_contest_id": key[0], "team_id": key[1],
                                                                     "side": key[2]},
                               "business_key_multiplicity": len(siblings),
                               "occurrence_ordinal_within_key": siblings.index(rowid) + 1,
                               "sibling_original_sqlite_rowids": [s for s in siblings if s != rowid],
                               "meaning": oq["occurrence"]["meaning"]},
                "denominator": {"state": oq["denominator"], "retained_as_of_utc":
                                self.profile["retained_opportunity_as_of_utc"], "note": oq["not_current"],
                                "kickoff_before_as_of_claim": r["kickoff_before_as_of"],
                                "schedule_witness_proof": oq["schedule_witness_proof"]},
                "state_meaning": {"original_state": r["state"], "state": oq["state"][r["state"]]},
                "statements_ingested": {"original": r["statements_ingested"], "meaning": oq["statements_ingested"],
                                        "retained_statement_rows_for_contest_and_program": counted,
                                        "reconciles": counted == r["statements_ingested"]},
                "policy": ({"state": oq["policy"]["present"], "policy_id": policy,
                            "foreign_key_present_in_policy_table": policy in policy_ids}
                           if policy else {"state": oq["policy"]["absent"]}),
                "health_inference": "NOT_ASSERTED"})
        pq = self.rules["policy_qualification"]
        references = collections.Counter(r["governing_policy"] for _rid, r in self.records["opportunity"])
        for _rid, r in self.records["policy"]:
            self.qualifications["policy"].append({
                "schema": self.rules["schema"],
                "key": {"table": self.profile["tables"]["policy"]["table"], "policy_id": r["policy_id"]},
                "state": pq["state"],
                "witness": {"source_sha256": r["source_sha256"], "proof": pq["witness_proof"]},
                "quotes": {"count": len(r["quotes"]), "verification_claim": pq["quotes"]},
                "absence_rule": {"original": r["absence_rule"], "meaning": pq["absence_rule"]},
                "coverage": {"original_covers_2026": r["covers_2026"], "meaning": pq["coverage"]},
                "policy_season": {"original": r["policy_season"], "state": pq["policy_season"]["stated"]
                                  if r["policy_season"] is not None else pq["policy_season"]["unstated"]},
                "opportunity_references": references.get(r["policy_id"], 0),
                "health_inference": "NOT_ASSERTED"})

    def _population(self) -> None:
        st = [r for _rid, r in self.records["statement"]]
        sq = self.qualifications["statement"]
        op = [r for _rid, r in self.records["opportunity"]]
        oq = self.qualifications["opportunity"]
        C = collections.Counter
        keys = C((r["canonical_contest_id"], r["team_id"], r["side"]) for r in op)
        first_by_key = {}
        for r in op:
            first_by_key.setdefault((r["canonical_contest_id"], r["team_id"], r["side"]), r)
        record_pairs = list(zip(op[0::2], op[1::2]))
        cid_records = C(a["canonical_contest_id"] for a, _b in record_pairs)
        expected_rows = [r for r in op if r["report_expectation"] == "POLICY_STATES_A_REPORT"]
        distinct = list(first_by_key.values())
        distinct_expected = [r for r in distinct if r["report_expectation"] == "POLICY_STATES_A_REPORT"]
        derived = {
            "statements": len(st), "source_player_rows": len({(r["source_sha256"], r["source_locator"].split(".")[0])
                                                              for r in st}),
            "source_cells": len({(r["source_sha256"], r["source_locator"]) for r in st}),
            "statements_by_conference": dict(sorted(C(r["conference"] for r in st).items())),
            "statements_by_stage": dict(sorted(C(r["stage"] for r in st).items())),
            "presence": dict(sorted(C(r["presence"] for r in st).items())),
            "source_empty_representations": {
                "normalized_null": sum(1 for r in st if r["exact_status_text"] == "-" and r["normalized_status"] is None),
                "normalized_unknown_sec": sum(1 for r in st if r["exact_status_text"] == "-" and
                                              r["normalized_status"] == "UNKNOWN" and r["conference"] == "SEC")},
            "status_texts": dict(sorted(C(r["exact_status_text"] for r in st).items())),
            "effective_time_known": sum(1 for r in st if r["effective_utc"] is not None),
            "pit_admitted": sum(1 for r in st if r["pit_admitted"]),
            "publication_claims": sum(1 for r in st if r["publication_time_established"]),
            "source_person_id_prefixes": dict(sorted(C((r["identity"].get("canonical_player_id") or "null:").split(
                ":", 1)[0] for r in st).items())),
            "joint_person_contest": {j: sum(1 for q in sq if q["joint"] == j) for j in
                                     self.rules["statement_qualification"]["joint"]},
            "identity_states": dict(sorted(C(r["identity"]["state"] for r in st).items())),
            "contest_states": dict(sorted(C(r["contest"]["state"] for r in st).items())),
            "quarantined": sum(1 for r in st if r["quarantined"]),
            "opportunity_occurrences": len(op), "opportunity_distinct_business_keys": len(keys),
            "opportunity_singleton_business_keys": sum(1 for v in keys.values() if v == 1),
            "opportunity_duplicate_business_key_groups": sum(1 for v in keys.values() if v > 1),
            "schedule_record_occurrences": len(record_pairs) if len(op) % 2 == 0 and all(
                a["canonical_contest_id"] == b["canonical_contest_id"] and a["side"] == "home" and b["side"] == "away"
                for a, b in record_pairs) else None,
            "schedule_distinct_game_ids": len(cid_records),
            "schedule_duplicate_game_ids": sum(1 for v in cid_records.values() if v > 1),
            "opportunity_states": dict(sorted(C(r["state"] for r in op).items())),
            "policy_expected_occurrences": len(expected_rows),
            "policy_expected_before_as_of_occurrences": sum(1 for r in expected_rows if r["kickoff_before_as_of"]),
            "policy_expected_ingested_occurrences": sum(1 for r in expected_rows
                                                        if r["state"] == "REPORT_STATEMENTS_INGESTED"),
            "distinct_key_inventory": {
                "opportunity_states": dict(sorted(C(r["state"] for r in distinct).items())),
                "policy_expected": len(distinct_expected),
                "policy_expected_before_as_of": sum(1 for r in distinct_expected if r["kickoff_before_as_of"]),
                "policy_expected_ingested": sum(1 for r in distinct_expected
                                                if r["state"] == "REPORT_STATEMENTS_INGESTED")},
            "policies": len(self.records["policy"]),
        }
        frozen = self.profile["population"]
        differing = sorted(k for k in set(frozen) | set(derived) if frozen.get(k) != derived.get(k))
        if differing:
            raise AvailabilityError("POPULATION_MISMATCH", f"re-derived population differs from the builtin profile at "
                                                           f"{differing}")
        self.derived_population = derived
        self.qualification_summary = {
            "source_cells": dict(sorted(C(q["source_cell"]["state"] for q in sq).items())),
            "source_cell_fields_compared": sum(q["source_cell"]["fields_compared"] for q in sq),
            "publication": dict(sorted(C(q["publication"]["state"] for q in sq).items())),
            "opportunity_occurrence": dict(sorted(C(q["occurrence"]["state"] for q in oq).items())),
            "statements_ingested_reconciled": sum(1 for q in oq if q["statements_ingested"]["reconciles"]),
            "opportunity_policy_foreign_keys_present": sum(1 for q in oq if q["policy"].get(
                "foreign_key_present_in_policy_table")),
            "quarantine_flag_agrees_with_identity_claim": sum(1 for q in sq
                                                              if q["quarantine_flag"]["agrees_with_identity_claim"]),
        }

    def audit_lines(self) -> list[str]:
        """The complete per-row qualification collection as canonical lines in the frozen order."""
        out = []
        for grain in ("statement", "opportunity", "policy"):
            for q in self.qualifications[grain]:
                out.append(P.canonical_bytes({"grain": grain, "qualification": q}).decode("utf-8"))
        return out

    def audit_identity(self) -> dict[str, Any]:
        lines = self.audit_lines()
        return {"rules_sha256": P.RULES_SHA256, "database_sha256": self.profile["database"]["sha256"],
                "rows": len(lines), "lines_sha256": hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest(),
                "summary": self.qualification_summary}

    def _check_audit(self) -> None:
        if self.audit_pin is None:
            return
        ident = self.audit_identity()
        if ident != self.audit_pin:
            raise AvailabilityError("QUALIFICATION_AUDIT_MISMATCH", "the per-row qualification collection differs "
                                                                    "from the pinned qualified audit identity")

    # ---- query
    def domains(self) -> dict[str, set]:
        st = [r for _rid, r in self.records["statement"]]
        op = [r for _rid, r in self.records["opportunity"]]
        po = [r for _rid, r in self.records["policy"]]
        return {
            "--statement-id": {r["availability_row_id"] for r in st},
            "--policy-id": {r["policy_id"] for r in po} | {r["governing_policy"] for r in op if r["governing_policy"]},
            "--team": {r["program"] for r in st} | {r["program"] for r in op},
            "--conference": {r["conference"] for r in st} | {r["conference"] for r in op if r["conference"]} |
                            {r["conference"] for r in po},
            "--contest": {r["contest"].get("canonical_contest_id") for r in st if r["contest"].get(
                "canonical_contest_id")} | {r["canonical_contest_id"] for r in op},
            "--person-id": {r["identity"].get("canonical_player_id") for r in st if r["identity"].get(
                "canonical_player_id")},
            "--published-name": {r["player_name"] for r in st},
            "--source-sha256": {r["source_sha256"] for r in st} | {r["source_sha256"] for r in po} |
                               {self.profile["witnesses"][P.POSTING_WITNESS]["sha256"]},
            "--reported-status": {r["exact_status_text"] for r in st},
            "--policy-season": {r["policy_season"] for r in po if r["policy_season"] is not None},
        }

    def _match(self, grain: str, r: dict[str, Any], q: dict[str, Any], rowid: int, sel: dict[str, Any]) -> bool:
        for option, value in sel.items():
            if option == "--cutoff":
                continue
            if grain == "statement":
                got = {"--statement-id": r["availability_row_id"], "--team": r["program"],
                       "--conference": r["conference"], "--season": r["contest"].get("season"),
                       "--contest": r["contest"].get("canonical_contest_id"),
                       "--person-id": r["identity"].get("canonical_player_id"), "--published-name": r["player_name"],
                       "--source-sha256": r["source_sha256"], "--stage": r["stage"],
                       "--reported-status": r["exact_status_text"], "--presence": r["presence"],
                       "--identity-state": r["identity"]["state"], "--contest-state": r["contest"]["state"]}[option]
            elif grain == "opportunity":
                got = {"--policy-id": r["governing_policy"], "--team": r["program"], "--conference": r["conference"],
                       "--season": self.profile["schedule_season"], "--contest": r["canonical_contest_id"]}[option]
            else:
                got = {"--policy-id": r["policy_id"], "--conference": r["conference"],
                       "--policy-season": r["policy_season"], "--source-sha256": r["source_sha256"]}[option]
            if type(got) is not type(value) or got != value:
                return False
        return True

    def _cutoff(self, r: dict[str, Any], q: dict[str, Any], cutoff: dt.datetime) -> dict[str, Any]:
        pub = q["publication"]
        witnessed = pub["state"] == self.rules["statement_qualification"]["publication"]["witnessed"]
        clocks = [
            {"clock": "PRIMARY_CAPTURE_RETRIEVAL_OBSERVATION", "value": r["report_vintage_retrieval_utc"],
             "relation": relation(parse_instant(r["report_vintage_retrieval_utc"]), cutoff),
             "authority": "OBSERVED_CAPTURE_TIME_NOT_PUBLICATION_EFFECTIVE_OR_FIRST_KNOWN_TIME"},
            {"clock": "LATER_POSTING_CAPTURE_OBSERVATION",
             "value": pub.get("capture_observation_utc") if witnessed else None,
             "relation": relation(parse_instant(pub.get("capture_observation_utc")), cutoff) if witnessed else "UNKNOWN",
             "authority": "OBSERVED_CAPTURE_TIME_OF_THE_SEPARATE_POSTING_VIEW" if witnessed else
             "NO_POSTING_WITNESS_FOR_THIS_ROW"},
            {"clock": "SOURCE_REPORTED_POSTING_CLAIM", "value": r["publication_utc"],
             "relation": relation(parse_instant(r["publication_utc"]), cutoff) if witnessed else "UNKNOWN",
             "authority": pub["authority"] if witnessed else "PUBLICATION_TIME_UNKNOWN"},
            {"clock": "EFFECTIVE_TIME", "value": None, "relation": "UNKNOWN", "authority": "EFFECTIVE_TIME_UNKNOWN"},
            {"clock": "FIRST_KNOWN_TIME", "value": None, "relation": "UNKNOWN", "authority": "FIRST_KNOWN_NOT_ESTABLISHED"},
        ]
        return {"cutoff_utc": cutoff.isoformat(), "clocks": clocks, "rows_filtered": False,
                "rule": self.rules["cutoff"]["rule"]}

    def profile_record(self) -> dict[str, Any]:
        return {"profile_id": self.profile["profile_id"], "database": self.profile["database"],
                "tables": {grain: {"table": spec["table"], "data_grain": spec["data_grain"], "rows": spec["rows"],
                                   "columns": list(spec["columns"])} for grain, spec in self.profile["tables"].items()},
                "witnesses": {wid: {k: spec[k] for k in ("relative_path", "sha256", "bytes", "role", "conference",
                                                         "retrieval_observation_utc", "retrieval_observation_basis")}
                              for wid, spec in self.profile["witnesses"].items()},
                "offline_witnesses": self.profile["offline_witnesses"],
                "population": self.derived_population,
                "qualification_summary": self.qualification_summary,
                "posting_card_kinds": self.posting["card_kinds"],
                "report_season": self.profile["report_season"],
                "retained_opportunity_as_of_utc": self.profile["retained_opportunity_as_of_utc"],
                "selectors_supported": "NONE (the profile grain is a singleton coverage record)",
                "meaning": "EXACT_FIXED_POPULATION_AND_SCOPE_NOT_PLAYER_SUMMARIES_NOT_CURRENT_COVERAGE"}

    def query(self, grain: str, selectors: dict[str, Any] | None = None, *, limit: Any = None, offset: Any = None,
              all_rows: bool = False) -> dict[str, Any]:
        sel = validate_selectors(grain, dict(selectors or {}))
        lim, off = validate_paging(limit, offset, all_rows)
        domains = self.domains()
        for option, value in sel.items():
            if option in ("--season", "--cutoff", "--stage", "--presence", "--identity-state", "--contest-state"):
                continue
            if option == "--policy-season":
                if value not in domains[option]:
                    raise AvailabilityError("SEASON_NOT_IN_PROFILE", f"--policy-season {value} is not a retained "
                                                                     f"policy season")
                continue
            if value not in domains[option]:
                raise AvailabilityError("KEY_NOT_IN_PROFILE", f"{option} {value!r} is not represented in the fixed "
                                                              f"profile")
        spec = self.profile["tables"].get(grain)
        if grain == "profile":
            ordered: list[dict[str, Any]] = [{"profile": self.profile_record()}]
            order = ["SINGLETON"]
        else:
            rows = []
            for (rowid, r), q in zip(self.records[grain], self.qualifications[grain]):
                if not self._match(grain, r, q, rowid, sel):
                    continue
                item: dict[str, Any] = {"original_record": r, "qualification": q}
                if grain == "opportunity":
                    item["source_occurrence"] = {"database_sha256": self.profile["database"]["sha256"],
                                                 "table": spec["table"], "original_sqlite_rowid": rowid}
                    sort = _sort_key((r["canonical_contest_id"], r["team_id"], r["side"], rowid))
                elif grain == "statement":
                    if "--cutoff" in sel:
                        item["cutoff_comparison"] = self._cutoff(r, q, sel["--cutoff"])
                    sort = _sort_key((r["availability_row_id"],))
                else:
                    sort = _sort_key((r["policy_id"],))
                rows.append((sort, item))
            rows.sort(key=lambda pair: pair[0])
            ordered = [item for _sort, item in rows]
            order = list(spec["order"])
        total = len(ordered)
        page = ordered[off:] if lim is None else ordered[off:off + lim]
        applied = {k: (v.isoformat() if isinstance(v, dt.datetime) else v) for k, v in sorted(sel.items())}
        out = {
            "schema": P.RESPONSE_SCHEMA, "profile": self.profile["profile_id"], "grain": grain,
            "database_sha256": self.profile["database"]["sha256"],
            "table": spec["table"] if spec else None, "selectors": applied, "order": order,
            "total_count": total, "limit": lim, "offset": off, "all": all_rows, "returned": len(page),
            "next_offset": off + len(page) if lim is not None and off + len(page) < total else None,
            "source_clock_scope": {
                "primary_capture_retrieval_observations": {w: self.profile["witnesses"][w]["retrieval_observation_utc"]
                                                           for w in P.PRIMARY_WITNESSES},
                "later_posting_capture_observation": self.profile["witnesses"][P.POSTING_WITNESS][
                    "retrieval_observation_utc"],
                "retained_opportunity_as_of_utc": self.profile["retained_opportunity_as_of_utc"],
                "effective_times": "UNKNOWN", "first_known_times": "NOT_ESTABLISHED",
                "meaning": "CAPTURE_AND_CLAIM_CLOCKS_ONLY_NOT_A_CURRENT_OR_HISTORICAL_STATE"},
            "qualification_rules": {"schema": self.rules["schema"], "sha256": P.RULES_SHA256},
            "qualified_audit": None if self.audit_pin is None else {"lines_sha256": self.audit_pin["lines_sha256"],
                                                                    "rows": self.audit_pin["rows"]},
            "witnesses_verified": {wid: spec_w["sha256"] for wid, spec_w in sorted(self.profile["witnesses"].items())},
            "decoding": {g: {"json_text_columns": sorted(s["json_columns"]), "boolean_columns": s["boolean_columns"]}
                         for g, s in self.profile["tables"].items()},
            "authority": dict(self.rules["authority"]),
            "rows": page,
        }
        if grain != "profile" and total == 0:
            out["empty_match"] = {"state": "REPRESENTED_SELECTORS_WITH_EMPTY_INTERSECTION",
                                  "meaning": "NO_RETAINED_ROW_MATCHES_THIS_EXACT_INTERSECTION_NOT_HEALTH_NOT_"
                                             "AVAILABILITY_NOT_REPORT_COMPLETENESS"}
        elif total and not page:
            out["page_state"] = "OFFSET_BEYOND_FILTERED_POPULATION"
        return out

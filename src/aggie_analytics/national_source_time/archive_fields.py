r"""Field-grain evidence of one archived ESPN game page (BAT-713, contract V1.2; Cycle #41 Attempt #1 continuation).

Standard library only. The archived-publication producer (``tools/build_national_archived_publication.py``) builds every
capture and assertion record with :func:`derive_capture`; the read-only consumer (``archive.py``) re-runs the same
derivation on the retained raw bytes, receipts and parent values and refuses a sidecar whose stored records differ, so
no stored witness span, scope, field state or orientation is ever trusted. The independent validator does not import
this module.

Witnesses are read only at their exact structural grain (see the contract's ``extraction`` section):

* attributes are tokenized from the raw start tag (value span exact; a repeated attribute name is unparseable);
* element text witnesses are the complete content of an explicitly closed element with no child markup, trimmed;
* JS witnesses are ``espn.gamepackage.<name> = "<value>";`` statements that begin a line inside a script element;
* every occurrence is recorded, so an absent, duplicated or contradictory witness is visible, never a first match.

Participants are mapped to the parent's a/b teams only through documented names (the parent's joined CFBD route row
school names and NCAA names), the CFBD home/away role and a qualified contest date; equal numbers in two provider
namespaces are never evidence, and differing ESPN/CFBD ids are allowed when the names, roles and date prove the map.
A version whose participant mapping does not qualify is quarantined as a whole (contract V1.2 QUARANTINE_RULE): a
page whose participant identity is not evidenced supports no field.
"""
from __future__ import annotations

import datetime as _dt
import email.utils
import html
import json
import re
import urllib.parse
from html.parser import HTMLParser
from typing import Any, Callable

FIELDS = ("season", "contest_date", "a_participant", "b_participant", "completion", "a_points", "b_points")
ROLES = {"season": "IDENTITY", "contest_date": "IDENTITY", "a_participant": "IDENTITY", "b_participant": "IDENTITY",
         "completion": "OUTCOME", "a_points": "OUTCOME", "b_points": "OUTCOME"}
WITNESSABLE = ("contest_date", "a_participant", "b_participant", "completion", "a_points", "b_points")
QUAL = "QUALIFIED_AGREES_WITH_PARENT"
SIDES = ("HOME", "AWAY")
PARTICIPANT_WITNESSES = ("JS_HOME_TEAM_ID", "HOME_TEAM_HREF", "HOME_TEAM_NAME", "JS_AWAY_TEAM_ID", "AWAY_TEAM_HREF",
                         "AWAY_TEAM_NAME")
FIELD_WITNESSES = {"season": frozenset(), "contest_date": frozenset({"JS_EVENT_TIMESTAMP", "INFO_EVENT_DATE"}),
                   "a_participant": frozenset(PARTICIPANT_WITNESSES),
                   "b_participant": frozenset(PARTICIPANT_WITNESSES),
                   "completion": frozenset({"JS_STATUS", "STATUS_DETAIL"}),
                   "a_points": frozenset({"HOME_SCORE", "AWAY_SCORE"}),
                   "b_points": frozenset({"HOME_SCORE", "AWAY_SCORE"})}
WITNESS_NAMES = ("NAV_GAME_ID", "JS_GAME_ID", "JS_STATUS", "STATUS_DETAIL", "JS_HOME_TEAM_ID", "JS_AWAY_TEAM_ID",
                 "HOME_TEAM_HREF", "AWAY_TEAM_HREF", "HOME_TEAM_NAME", "AWAY_TEAM_NAME", "HOME_SCORE", "AWAY_SCORE",
                 "JS_EVENT_TIMESTAMP", "INFO_EVENT_DATE")
MAPPING_RULE = ("each page team block maps to the parent side whose documented name (the parent's joined CFBD route "
                "school name or an NCAA name of that team) equals the block's ESPN long-name, whose CFBD home/away role "
                "equals the block's side, in a version whose contest date qualifies; ESPN and CFBD numeric identifiers "
                "are recorded in their own namespaces and never equated")
#: Contract V1.2: a version whose participant identity is not evidenced serves no field at all.
QUARANTINE_REASON = "PARTICIPANT_MAPPING_UNRESOLVED"
QUARANTINE_RULE = ("a version qualifies only when its participant mapping qualifies: a missing, unresolved, ambiguous, "
                   "swapped, cross-assigned or contradictory mapping quarantines the whole capture (reason "
                   "PARTICIPANT_MAPPING_UNRESOLVED; every field CAPTURE_NOT_QUALIFIED), so no field of a page whose "
                   "participant identity is not evidenced is served")
TS14_RE = re.compile(r"^[0-9]{14}$")
DIGITS_RE = re.compile(r"^[0-9]{1,12}$")
SCORE_RE = re.compile(r"^[0-9]{1,3}$")
FINAL_RE = re.compile(r"^Final(/[0-9]*OT)?$")
INSTANT_RE = re.compile(r"^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2})(?::([0-9]{2}))?(Z|[+-][0-9]{2}:[0-9]{2})$")
TEAM_HREF_RE = re.compile(r"^(?:https?://www\.espn\.com)?/college-football/team/_/id/([0-9]{1,12})(?:/[^\s\"'<>]*)?$")
NAV_ID_RE = re.compile(r"^gamepackage-([0-9]{1,12})$")
JS_LINE_RE = re.compile(r'^[ \t]*(espn\.gamepackage\.(gameId|status|homeTeamId|awayTeamId|timestamp)[ \t]*=[ \t]*'
                        r'"([^"\\\r\n]*)"[ \t]*;)', re.M)
JS_NAMES = {"gameId": "JS_GAME_ID", "status": "JS_STATUS", "homeTeamId": "JS_HOME_TEAM_ID",
            "awayTeamId": "JS_AWAY_TEAM_ID", "timestamp": "JS_EVENT_TIMESTAMP"}
ATTR_RE = re.compile(r'([^\s/>"\'=]+)(?:[ \t\r\n\f]*=[ \t\r\n\f]*("([^"]*)"|\'([^\']*)\'|([^\s"\'=<>`]+)))?')
GAME_PATH_RE = re.compile(r"^/college-football/game/_/gameId/([0-9]{1,12})$")
REPLAY_PATH_RE = re.compile(r"^/web/([0-9]{14})id_/(.+)$")
US_LOCAL_OFFSETS_HOURS = (-4, -10)
EARLIEST_ZONE_HOURS = 14
ORIGIN_DATE_TOLERANCE_SECONDS = 300
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr", "param"}
UTC = _dt.timezone.utc


# --------------------------------------------------------------------------------------------- clocks and URLs

def fmt_utc(value: _dt.datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


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


def equivalent_original(url: Any, game_id: str) -> bool:
    """The contract's original-URL equivalence for one requested ESPN game page."""
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
    """(timestamp, original) of a https://web.archive.org/web/<ts>id_/<original> replay URL, else None."""
    try:
        parts = urllib.parse.urlsplit(str(url))
        port = parts.port
    except ValueError:
        return None
    if parts.scheme != "https" or (parts.hostname or "").lower() != "web.archive.org" or port not in (None, 443):
        return None
    if parts.query or parts.fragment or parts.username or parts.password:
        return None
    match = REPLAY_PATH_RE.match(parts.path)
    return (match.group(1), match.group(2)) if match else None


def link_original(link: Any) -> str | None:
    """The rel="original" URL of a Memento Link header."""
    if not isinstance(link, str) or not link:
        return None
    for match in re.finditer(r'<([^>]*)>\s*;\s*([^,<]*)', link):
        if re.search(r'\brel\s*=\s*"?original"?', match.group(2)):
            return match.group(1)
    return None


def header(headers: Any, name: str) -> str | None:
    pairs = list(headers.items()) if isinstance(headers, dict) else [tuple(pair) for pair in headers or []]
    values = [v for k, v in pairs if str(k).lower() == name.lower()]
    if not values:
        return None
    return values[0] if isinstance(values[0], str) else None


def receipt_checks(final_url: str, status: int | None, headers: Any, payload: bytes,
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
    checks["memento_equals_url_timestamp"] = bool(memento_at and parts and memento_at == ts14_instant(parts[0]))
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


# --------------------------------------------------------------------------------------------- extraction

def start_tag_attributes(raw_tag: str) -> tuple[str, list[tuple[str, str | None, int, int]]]:
    """(tag name, [(lower attribute name, value, value start, value end)]) with exact offsets in ``raw_tag``."""
    match = re.match(r"<([a-zA-Z][^\s/>]*)", raw_tag)
    if not match:
        return "", []
    out = []
    pos = match.end()
    limit = len(raw_tag) - (2 if raw_tag.endswith("/>") else 1)
    while pos < limit:
        space = re.match(r"[\s/]*", raw_tag[pos:limit])
        pos += space.end()
        if pos >= limit:
            break
        found = ATTR_RE.match(raw_tag, pos, limit)
        if not found or found.end() == pos:
            break
        name = found.group(1).lower()
        if found.group(2) is None:
            out.append((name, None, found.end(), found.end()))
        else:
            group = 3 if found.group(3) is not None else (4 if found.group(4) is not None else 5)
            out.append((name, found.group(group), found.start(group), found.end(group)))
        pos = found.end()
    return match.group(1).lower(), out


class _Page(HTMLParser):
    """One tokenizer pass recording every main-element witness occurrence with exact character spans."""

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
        self.js: list[tuple[int, int]] = []
        self.occurrences: list[dict[str, Any]] = []
        self.problems: list[str] = []

    def char_offset(self) -> int:
        line, col = self.getpos()
        return self.line_starts[line - 1] + col

    def _ancestor(self, predicate: Callable[[dict[str, Any]], bool]) -> dict[str, Any] | None:
        for item in reversed(self.stack):
            if predicate(item):
                return item
        return None

    def _add(self, witness: str, span: tuple[int, int], scope: str, problem: str | None = None) -> None:
        self.occurrences.append({"witness": witness, "span": span, "scope": scope, "problem": problem})

    def _attr(self, item: dict[str, Any], name: str, witness: str, scope: str) -> None:
        found = [a for a in item["attrs"] if a[0] == name]
        if not found:
            return
        if len(found) > 1:
            self._add(witness, (item["start"] + found[0][2], item["start"] + found[0][3]), scope,
                      "ATTRIBUTE_REPEATED")
            return
        _name, _value, start, end = found[0]
        self._add(witness, (item["start"] + start, item["start"] + end), scope)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        start = self.char_offset()
        raw = self.get_starttag_text() or ""
        _name, parsed = start_tag_attributes(raw)
        values: dict[str, list[str | None]] = {}
        for name, value, _s, _e in parsed:
            values.setdefault(name, []).append(value)

        def one(name: str) -> str | None:
            got = values.get(name) or []
            return got[0] if len(got) == 1 else None
        classes = set((one("class") or "").split())
        item = {"tag": tag, "start": start, "open_end": start + len(raw), "attrs": parsed, "classes": classes}
        nav = self._ancestor(lambda i: i.get("role") == "NAV")
        info = self._ancestor(lambda i: i.get("role") == "INFO")
        if tag == "div" and one("id") == "custom-nav":
            item["role"] = "NAV"
            self.nav.append({"start": start, "end": None})
            self._attr(item, "data-id", "NAV_GAME_ID", "NAV")
        elif tag == "div" and one("id") == "gamepackage-game-information":
            item["role"] = "INFO"
            self.info.append({"start": start, "end": None})
        elif nav is not None and tag == "div" and "team" in classes and ({"home", "away"} & classes):
            if {"home", "away"} <= classes:
                self.problems.append("TEAM_BLOCK_SIDE_AMBIGUOUS")
            else:
                item["side"] = "HOME" if "home" in classes else "AWAY"
        elif nav is not None and tag == "a" and "team-name" in classes:
            team = self._ancestor(lambda i: "side" in i)
            if team is not None:
                item["team_name_side"] = team["side"]
                self._attr(item, "href", f"{team['side']}_TEAM_HREF", "NAV")
        elif nav is not None and tag == "span" and "long-name" in classes:
            anchor = self._ancestor(lambda i: "team_name_side" in i)
            if anchor is not None:
                item["text_witness"] = f"{anchor['team_name_side']}_TEAM_NAME"
        elif nav is not None and tag == "div" and "score" in classes:
            team = self._ancestor(lambda i: "side" in i)
            if team is not None:
                item["text_witness"] = f"{team['side']}_SCORE"
        elif nav is not None and tag == "span" and "status-detail" in classes:
            item["text_witness"] = "STATUS_DETAIL"
        elif info is not None and tag == "span" and one("data-behavior") == "date_time" and \
                self._ancestor(lambda i: i["tag"] == "div" and "game-date-time" in i["classes"]) is not None:
            self._attr(item, "data-date", "INFO_EVENT_DATE", "INFO")
        if tag not in VOID:
            self.stack.append(item)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1]["tag"] == tag:
            self.stack.pop()

    def _close(self, item: dict[str, Any], position: int, end: int, explicit: bool) -> None:
        if item.get("role") == "NAV" and self.nav and self.nav[-1]["end"] is None:
            self.nav[-1]["end"] = end
        if item.get("role") == "INFO" and self.info and self.info[-1]["end"] is None:
            self.info[-1]["end"] = end
        if item["tag"] == "script":
            body = self.text[item["open_end"]:position]
            for match in JS_LINE_RE.finditer(body):
                self.js.append((item["open_end"] + match.start(1), item["open_end"] + match.end(1)))
                self._add(JS_NAMES[match.group(2)], (item["open_end"] + match.start(3),
                                                     item["open_end"] + match.end(3)), "JS")
        if "text_witness" in item:
            content = self.text[item["open_end"]:position]
            stripped = content.strip()
            if not explicit:
                self._add(item["text_witness"], (item["open_end"], item["open_end"]), "NAV", "ELEMENT_NOT_CLOSED")
            elif "<" in content or ">" in content:
                self._add(item["text_witness"], (item["open_end"], position), "NAV", "CHILD_MARKUP_IN_TEXT_WITNESS")
            elif stripped:
                lead = len(content) - len(content.lstrip())
                self._add(item["text_witness"], (item["open_end"] + lead, item["open_end"] + lead + len(stripped)),
                          "NAV")

    def handle_endtag(self, tag: str) -> None:
        position = self.char_offset()
        end = self.text.find(">", position) + 1
        if not any(item["tag"] == tag for item in self.stack):
            return
        while self.stack:
            item = self.stack.pop()
            self._close(item, position, end, item["tag"] == tag)
            if item["tag"] == tag:
                break

    def close(self) -> None:
        super().close()
        while self.stack:
            item = self.stack.pop()
            self._close(item, len(self.text), len(self.text), False)


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
    """Every witness occurrence of the main game element with byte spans, the scope spans and the page problems."""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return {"problems": ["BODY_NOT_UTF8"], "witnesses": [], "scopes": []}
    page = _Page(text)
    page.feed(text)
    page.close()
    to_byte = byte_offsets(text)
    scopes = [{"kind": "NAV", "span": [to_byte(n["start"]), to_byte(n["end"])]} for n in page.nav if n["end"]]
    scopes += [{"kind": "INFO", "span": [to_byte(n["start"]), to_byte(n["end"])]} for n in page.info if n["end"]]
    scopes += [{"kind": "JS", "span": [to_byte(a), to_byte(b)]} for a, b in page.js]
    witnesses = []
    for occ in page.occurrences:
        start, end = to_byte(occ["span"][0]), to_byte(occ["span"][1])
        witnesses.append({"witness": occ["witness"], "span": [start, end],
                          "literal": payload[start:end].decode("utf-8"), "scope": occ["scope"],
                          "problem": occ["problem"]})
    witnesses.sort(key=lambda w: (w["span"][0], w["span"][1], w["witness"]))
    problems = list(dict.fromkeys(page.problems))
    if not [n for n in page.nav if n["end"]]:
        problems.append("MAIN_GAME_ELEMENT_ABSENT")
    elif len(page.nav) > 1:
        problems.append("MAIN_GAME_ELEMENT_DUPLICATED")
    return {"problems": problems, "witnesses": witnesses,
            "scopes": sorted(scopes, key=lambda s: (s["span"][0], s["kind"]))}


def witness_value(witness: str, literal: str) -> tuple[Any, str | None]:
    """(normalized value, problem) for one witness literal."""
    if witness in ("JS_GAME_ID", "JS_HOME_TEAM_ID", "JS_AWAY_TEAM_ID"):
        return (literal, None) if DIGITS_RE.match(literal) else (None, "UNPARSEABLE")
    if witness == "NAV_GAME_ID":
        match = NAV_ID_RE.match(literal)
        return (match.group(1), None) if match else (None, "UNPARSEABLE")
    if witness in ("HOME_TEAM_HREF", "AWAY_TEAM_HREF"):
        match = TEAM_HREF_RE.match(literal)
        return (match.group(1), None) if match else (None, "UNPARSEABLE")
    if witness in ("HOME_TEAM_NAME", "AWAY_TEAM_NAME"):
        name = " ".join(html.unescape(literal).split())
        return (name, None) if name else (None, "UNPARSEABLE")
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


# --------------------------------------------------------------------------------------------- participants

def participant_sources(record: dict[str, Any], lineage: list[dict[str, Any]]) -> dict[str, Any]:
    """Documented names and the CFBD role of the parent's a/b teams, read from the parent's own joined lineage rows
    (CFBD route responses and NCAA team-season pages). The CFBD rows must bind exactly the parent's a/b CFBD ids
    (same namespace) and agree with each other; otherwise the sources are ABSENT or CONTRADICTORY."""
    ids = {"A": (record.get("a_cfbd_team_id") or {}).get("value"), "B": (record.get("b_cfbd_team_id") or {}).get("value")}
    names: dict[str, dict[str, set[str]]] = {"A": {}, "B": {}}
    for side, field in (("A", "a_team_name"), ("B", "b_team_name")):
        if record.get(field):
            names[side].setdefault(str(record[field]), set()).add("NCAA_TEAM_NAME")
    cfbd_rows, views, problems = [], set(), []
    for row in lineage:
        if row.get("join_state") != "PARENT_LINEAGE":
            continue
        literals = row.get("literals") or {}
        if row.get("source_kind") == "NCAA_TEAM_SEASON_PAGE":
            page_side = (row.get("orientation") or {}).get("page_team_side")
            if page_side in ("A", "B"):
                other = "B" if page_side == "A" else "A"
                for side, key in ((page_side, "page_team_name"), (other, "opponent_name")):
                    if literals.get(key):
                        names[side].setdefault(str(literals[key]), set()).add("NCAA_TEAM_NAME")
        elif row.get("source_kind") == "CFBD_ROUTE_RESPONSE":
            home_side = (row.get("orientation") or {}).get("home_side")
            if home_side not in ("A", "B"):
                problems.append("CFBD_HOME_SIDE_UNKNOWN")
                continue
            away_side = "B" if home_side == "A" else "A"
            view = (home_side, literals.get("homeTeam"), literals.get("homeId"), literals.get("awayTeam"),
                    literals.get("awayId"))
            if (literals.get("homeId"), literals.get("awayId")) != (ids[home_side], ids[away_side]) or \
                    not literals.get("homeTeam") or not literals.get("awayTeam"):
                problems.append("CFBD_ROW_DOES_NOT_BIND_THE_PARENT_TEAMS")
            views.add(view)
            cfbd_rows.append({"capture_id": row.get("capture_id"), "native_row_key": row.get("native_row_key"),
                              "source_revision": row.get("source_revision"),
                              "evidence_document": (row.get("event_clock") or {}).get("evidence_document"),
                              "home_side": home_side, "home_team": literals.get("homeTeam"),
                              "away_team": literals.get("awayTeam"), "neutral_site": literals.get("neutralSite")})
    cfbd_rows.sort(key=lambda r: (str(r["capture_id"]), str(r["native_row_key"])))
    if not cfbd_rows:
        state = "CFBD_SOURCE_ABSENT"
    elif problems or len(views) != 1:
        state = "CFBD_SOURCE_CONTRADICTORY"
    else:
        state = "PRESENT"
    sides: dict[str, Any] = {}
    view = next(iter(views)) if state == "PRESENT" else None
    for side in ("A", "B"):
        role = cfbd_name = None
        if view is not None:
            home_side, home_team, _hid, away_team, _aid = view
            role = "HOME" if home_side == side else "AWAY"
            cfbd_name = home_team if role == "HOME" else away_team
            names[side].setdefault(str(cfbd_name), set()).add("CFBD_SCHOOL_NAME")
        letter = side.lower()
        sides[letter] = {"parent_key": record.get(f"{letter}_key"),
                         "cfbd_team_id": record.get(f"{letter}_cfbd_team_id"), "cfbd_school_name": cfbd_name,
                         "cfbd_role": role,
                         "documented_names": [{"name": n, "sources": sorted(s)} for n, s in sorted(names[side].items())]}
    return {"state": state, "problems": sorted(set(problems)), "cfbd_rows": cfbd_rows, "sides": sides,
            "rule": MAPPING_RULE}


def mapping_conflicts(captures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Contradictions between qualified participant mappings of different captures: one ESPN team id mapped to two
    parent teams, or one parent team mapped to two ESPN team ids."""
    by_espn: dict[str, set[str]] = {}
    by_parent: dict[str, set[str]] = {}
    for cap in captures:
        mapping = cap.get("participant_mapping") or {}
        if mapping.get("state") != "QUALIFIED":
            continue
        for side in mapping["sides"].values():
            espn, parent = side["espn_team_id"]["value"], side["parent_key"]
            by_espn.setdefault(espn, set()).add(parent)
            by_parent.setdefault(parent, set()).add(espn)
    out = [{"espn_team_id": k, "parent_keys": sorted(v)} for k, v in sorted(by_espn.items()) if len(v) > 1]
    out += [{"parent_key": k, "espn_team_ids": sorted(v)} for k, v in sorted(by_parent.items()) if len(v) > 1]
    return out


# --------------------------------------------------------------------------------------------- qualification

def qualify(contest_key: str, parent: dict[str, Any], game_id: str, payload: bytes, bound: str | None,
            receipt_reasons: list[str]) -> dict[str, Any]:
    """Field states, assertions and page facts of one archived version. ``parent`` is {record, values, participants}
    (participants from :func:`participant_sources`; without them no participant mapping can qualify)."""
    record, values = parent["record"], parent["values"]
    sources = parent.get("participants") or {"state": "PARTICIPANT_SOURCES_ABSENT", "sides": {}}
    extraction = extract(payload) if "BODY_NOT_UTF8" not in receipt_reasons else \
        {"problems": ["BODY_NOT_UTF8"], "witnesses": [], "scopes": []}
    reasons = list(receipt_reasons) + [p for p in extraction["problems"] if p not in receipt_reasons]
    by: dict[str, list[dict[str, Any]]] = {}
    for w in extraction["witnesses"]:
        value, problem = witness_value(w["witness"], w["literal"])
        by.setdefault(w["witness"], []).append(dict(w, value=value, problem=w["problem"] or problem))

    def single(name: str) -> tuple[Any, str]:
        items = by.get(name) or []
        if not items:
            return None, "ABSENT"
        if any(i["problem"] for i in items):
            return None, "UNPARSEABLE"
        distinct = {json.dumps(i["value"], sort_keys=True) for i in items}
        if len(distinct) > 1:
            return None, "CONTRADICTORY"
        return (items[0]["value"], "OK") if len(items) == 1 else (None, "DUPLICATED")
    nav_game, nav_state = single("NAV_GAME_ID")
    js_game, js_state = single("JS_GAME_ID")
    if "MAIN_GAME_ELEMENT_ABSENT" not in reasons and "MAIN_GAME_ELEMENT_DUPLICATED" not in reasons \
            and "BODY_NOT_UTF8" not in reasons:
        if nav_state != "OK" or nav_game != game_id:
            reasons.append("WRONG_GAME_NODE")
        if js_state == "CONTRADICTORY":
            reasons.append("GAME_IDENTITY_CONTRADICTORY")
        elif js_state == "DUPLICATED":
            reasons.append("GAME_IDENTITY_DUPLICATED")
        elif js_state != "OK" or js_game != game_id:
            reasons.append("GAME_IDENTITY_MISMATCH")
    js_status, s1 = single("JS_STATUS")
    detail, s2 = single("STATUS_DETAIL")
    final = s1 == "OK" and s2 == "OK" and js_status == "post" and isinstance(detail, str) and bool(FINAL_RE.match(detail))
    if final and bound and parse_utc(bound) < earliest_event_instant(record["contest_date"]):
        reasons.append("IMPOSSIBLE_CHRONOLOGY")
    qualified_capture = not reasons
    assertions: list[dict[str, Any]] = []
    states: dict[str, str] = {"season": "NOT_WITNESSED_IN_VERSION"}

    def state_for(witness_state: str) -> str:
        return {"UNPARSEABLE": "WITNESS_LITERAL_UNPARSEABLE", "CONTRADICTORY": "CONTRADICTORY_WITHIN_VERSION",
                "DUPLICATED": "DUPLICATED_WITNESS"}[witness_state]

    def emit(field: str, witness_names: list[str], state: str, corroboration: str, comparator: Any) -> None:
        """One assertion per witness occurrence; ``value`` is that occurrence's own normalized value."""
        states[field] = state
        for name in sorted(witness_names):
            for item in by.get(name) or []:
                value = item["value"]
                if value is not None and name in ("JS_HOME_TEAM_ID", "JS_AWAY_TEAM_ID", "HOME_TEAM_HREF",
                                                  "AWAY_TEAM_HREF"):
                    value = {"namespace": "ESPN_TEAM_ID", "value": value}
                elif value is not None and name in ("HOME_TEAM_NAME", "AWAY_TEAM_NAME"):
                    value = {"namespace": "ESPN_TEAM_LOCATION_NAME", "value": value}
                assertions.append({"field": field, "witness": name, "witness_span": list(item["span"]),
                                   "literal": item["literal"], "value": value, "parent_value": values[field],
                                   "parent_comparator": comparator,
                                   "corroboration": "UNPARSEABLE" if item["problem"] else corroboration,
                                   "field_state": state})
    # contest_date: both witnesses, exactly once each, parse and agree
    date_names = ["JS_EVENT_TIMESTAMP", "INFO_EVENT_DATE"]
    present = [n for n in date_names if by.get(n)]
    date_agrees = False
    if not present:
        states["contest_date"] = "NOT_WITNESSED_IN_VERSION"
    else:
        got = [single(n) for n in present]
        bad = [s for _v, s in got if s != "OK"]
        if bad:
            worst = "UNPARSEABLE" if "UNPARSEABLE" in bad else ("CONTRADICTORY" if "CONTRADICTORY" in bad
                                                                 else "DUPLICATED")
            date_state = state_for(worst)
            corr = "UNPARSEABLE" if worst == "UNPARSEABLE" else date_state
        elif len({v for v, _s in got}) != 1:
            date_state, corr = "CONTRADICTORY_WITHIN_VERSION", "CONTRADICTORY_WITHIN_VERSION"
        else:
            _p, _z, earliest, latest = event_interval(got[0][0])
            agrees = record["contest_date"] in local_candidate_dates(earliest, latest)
            corr = "AGREES_WITH_PARENT" if agrees else "CONFLICTS_WITH_PARENT"
            date_state = (QUAL if agrees else "CONFLICTS_WITH_PARENT") if len(present) == len(date_names) \
                else "INCOMPLETE_WITNESS_SET"
            date_agrees = date_state == QUAL
        if not qualified_capture:
            date_state = "CAPTURE_NOT_QUALIFIED"
        emit("contest_date", present, date_state, corr,
             {"basis": "US_LOCAL_CANDIDATE_DATES_-4H_-10H", "value": record["contest_date"]})
    # participants: page facts, then the evidenced mapping
    page: dict[str, dict[str, Any]] = {}
    for side in SIDES:
        js_id, js_st = single(f"JS_{side}_TEAM_ID")
        href_id, href_st = single(f"{side}_TEAM_HREF")
        name, name_st = single(f"{side}_TEAM_NAME")
        page[side] = {"id": js_id if (js_st == "OK" and href_st == "OK" and js_id == href_id) else None,
                      "js": js_st, "href": href_st, "name": name if name_st == "OK" else None, "name_state": name_st,
                      "ids_agree": js_st == "OK" and href_st == "OK" and js_id == href_id,
                      "ids_disagree": js_st == "OK" and href_st == "OK" and js_id != href_id}
    page_participants = {s.lower(): {"espn_team_id": page[s]["id"], "espn_location_name": page[s]["name"],
                                     "js_state": page[s]["js"], "href_state": page[s]["href"],
                                     "name_state": page[s]["name_state"], "witnesses_agree": page[s]["ids_agree"],
                                     "witness_spans": sorted([w["witness"], list(w["span"])]
                                                             for n in (f"JS_{s}_TEAM_ID", f"{s}_TEAM_HREF",
                                                                       f"{s}_TEAM_NAME")
                                                             for w in by.get(n) or [])}
                         for s in SIDES}
    mapping = _map_participants(sources, page, date_agrees)
    if qualified_capture and mapping["state"] != "QUALIFIED":
        # QUARANTINE_RULE: requalify with the mapping reason; the mapping itself does not depend on the capture state.
        return qualify(contest_key, parent, game_id, payload, bound, list(receipt_reasons) + [QUARANTINE_REASON])
    orientation = {"a_side": mapping.get("a_side"), "b_side": mapping.get("b_side"), "rule": MAPPING_RULE}
    witnessed = any(by.get(n) for n in PARTICIPANT_WITNESSES)
    for field, letter in (("a_participant", "a"), ("b_participant", "b")):
        if not witnessed:
            states[field] = "NOT_WITNESSED_IN_VERSION"
            continue
        if mapping["state"] != "QUALIFIED":  # only in a capture already quarantined (QUARANTINE_RULE)
            states[field] = "CAPTURE_NOT_QUALIFIED"
            continue
        side = mapping[f"{letter}_side"]
        info = mapping["sides"][side.lower()]
        emit(field, [f"JS_{side}_TEAM_ID", f"{side}_TEAM_HREF", f"{side}_TEAM_NAME"],
             QUAL if qualified_capture else "CAPTURE_NOT_QUALIFIED", "AGREES_WITH_PARENT",
             {"rule": "DOCUMENTED_PARENT_NAME_CFBD_ROLE_AND_DATE", "parent_key": info["parent_key"],
              "documented_name": info["documented_name"], "name_sources": info["name_sources"],
              "cfbd_team_id": info["cfbd_team_id"], "cfbd_role": info["cfbd_role"]})
    # completion: both status witnesses exactly once; COMPLETED only for post + Final
    status_names = [n for n in ("JS_STATUS", "STATUS_DETAIL") if by.get(n)]
    completed_ok = False
    if not status_names:
        states["completion"] = "NOT_WITNESSED_IN_VERSION"
    else:
        if len(status_names) < 2:
            state, corr = "INCOMPLETE_WITNESS_SET", "VERSION_PREDATES_OUTCOME"
        elif s1 != "OK" or s2 != "OK":
            worst = "UNPARSEABLE" if "UNPARSEABLE" in (s1, s2) else ("CONTRADICTORY" if "CONTRADICTORY" in (s1, s2)
                                                                    else "DUPLICATED")
            state = state_for(worst)
            corr = "UNPARSEABLE" if worst == "UNPARSEABLE" else state
        elif final:
            completed_ok = values["completion"] == "COMPLETED"
            state = QUAL if completed_ok else "CONFLICTS_WITH_PARENT"
            corr = "AGREES_WITH_PARENT" if completed_ok else "CONFLICTS_WITH_PARENT"
        else:
            state, corr = "NOT_SUPPORTED_BY_VERSION_STATUS", "VERSION_PREDATES_OUTCOME"
        if not qualified_capture:
            state = "CAPTURE_NOT_QUALIFIED"
        emit("completion", status_names, state, corr, None)
    # points: only in a final version, oriented by the evidenced participant mapping
    for field, letter in (("a_points", "a"), ("b_points", "b")):
        if not final:
            states[field] = ("NOT_SUPPORTED_BY_VERSION_STATUS" if status_names else "NOT_WITNESSED_IN_VERSION") \
                if qualified_capture else "CAPTURE_NOT_QUALIFIED"
            continue
        if mapping["state"] != "QUALIFIED":  # only in a capture already quarantined (QUARANTINE_RULE)
            states[field] = "CAPTURE_NOT_QUALIFIED"
            continue
        side = mapping[f"{letter}_side"]
        score, score_state = single(f"{side}_SCORE")
        if score_state == "ABSENT":
            states[field] = "NOT_WITNESSED_IN_VERSION" if qualified_capture else "CAPTURE_NOT_QUALIFIED"
            continue
        if score_state != "OK":
            state = state_for(score_state)
            corr = "UNPARSEABLE" if score_state == "UNPARSEABLE" else state
        else:
            agrees = score == values[field]
            corr = "AGREES_WITH_PARENT" if agrees else "CONFLICTS_WITH_PARENT"
            state = QUAL if agrees and completed_ok else ("CONFLICTS_WITH_PARENT" if not agrees
                                                          else "NOT_SUPPORTED_BY_VERSION_STATUS")
        if not qualified_capture:
            state = "CAPTURE_NOT_QUALIFIED"
        emit(field, [f"{side}_SCORE"], state, corr, None)
    for field in FIELDS:
        states.setdefault(field, "NOT_WITNESSED_IN_VERSION")
    return {"reasons": reasons, "qualified": qualified_capture, "states": states, "assertions": assertions,
            "scopes": extraction["scopes"],
            "page_status": {"js_status": js_status, "status_detail": detail, "final": final},
            "page_participants": page_participants, "orientation": orientation, "participant_mapping": mapping}


def _map_participants(sources: dict[str, Any], page: dict[str, dict[str, Any]], date_agrees: bool
                      ) -> dict[str, Any]:
    """The evidenced map of the two page team blocks to the parent's a/b teams, or the first unmet predicate."""
    out: dict[str, Any] = {"state": None, "reason": None, "rule": MAPPING_RULE, "a_side": None, "b_side": None,
                           "sources": {"state": sources.get("state"), "problems": sources.get("problems", []),
                                       "cfbd_rows": sources.get("cfbd_rows", []), "sides": sources.get("sides", {})},
                           "sides": {}}

    def fail(reason: str) -> dict[str, Any]:
        out.update(state="UNRESOLVED", reason=reason)
        return out
    if sources.get("state") != "PRESENT":
        return fail(str(sources.get("state")))
    for side in SIDES:
        if page[side]["ids_disagree"] or page[side]["js"] in ("CONTRADICTORY", "DUPLICATED", "UNPARSEABLE") or \
                page[side]["href"] in ("CONTRADICTORY", "DUPLICATED", "UNPARSEABLE"):
            return fail(f"{side}_TEAM_ID_WITNESSES_NOT_SINGLE_AND_EQUAL")
        if not page[side]["ids_agree"]:
            return fail(f"{side}_TEAM_ID_NOT_WITNESSED")
        if page[side]["name_state"] != "OK":
            return fail(f"{side}_TEAM_NAME_{page[side]['name_state']}")
    chosen: dict[str, str] = {}
    for side in SIDES:
        candidates = [letter for letter in ("a", "b")
                      if any(d["name"] == page[side]["name"] for d in sources["sides"][letter]["documented_names"])]
        if not candidates:
            return fail(f"{side}_TEAM_NAME_NOT_DOCUMENTED_FOR_EITHER_PARENT_TEAM")
        if len(candidates) > 1:
            return fail(f"{side}_TEAM_NAME_AMBIGUOUS_BETWEEN_PARENT_TEAMS")
        chosen[side] = candidates[0]
    if chosen["HOME"] == chosen["AWAY"]:
        return fail("BOTH_PAGE_TEAMS_MAP_TO_ONE_PARENT_TEAM")
    for side in SIDES:
        if sources["sides"][chosen[side]]["cfbd_role"] != side:
            return fail(f"{side}_TEAM_ROLE_CONTRADICTS_THE_CFBD_ROUTE_ROLE")
    if not date_agrees:
        return fail("CONTEST_DATE_NOT_CORROBORATED_IN_THIS_VERSION")
    for side in SIDES:
        mine = sources["sides"][chosen[side]]
        other = sources["sides"]["b" if chosen[side] == "a" else "a"]
        espn = page[side]["id"]
        if espn == (other["cfbd_team_id"] or {}).get("value") and espn != (mine["cfbd_team_id"] or {}).get("value"):
            return fail(f"{side}_ESPN_TEAM_ID_EQUALS_THE_OPPONENT_CFBD_ID")
    for side in SIDES:
        letter = chosen[side]
        info = sources["sides"][letter]
        doc = next(d for d in info["documented_names"] if d["name"] == page[side]["name"])
        out["sides"][side.lower()] = {
            "page_side": side, "parent_side": letter, "parent_key": info["parent_key"],
            "espn_team_id": {"namespace": "ESPN_TEAM_ID", "value": page[side]["id"]},
            "espn_location_name": page[side]["name"], "documented_name": doc["name"], "name_sources": doc["sources"],
            "cfbd_team_id": info["cfbd_team_id"], "cfbd_role": info["cfbd_role"],
            "id_relation": "ESPN_ID_LITERAL_EQUALS_CFBD_ID_LITERAL_NOT_AUTHORITY"
            if page[side]["id"] == (info["cfbd_team_id"] or {}).get("value") else "ESPN_ID_DIFFERS_FROM_CFBD_ID"}
        out[f"{letter}_side"] = side
    out.update(state="QUALIFIED", reason=None)
    return out


# --------------------------------------------------------------------------------------------- records

def raw_rel(sha: str) -> str:
    return f"raw/sha256/{sha}"


def worker_version(acquisition_id: str, index: int, request: dict[str, Any], payload: bytes) -> dict[str, Any]:
    """One replayed archived version from the content-addressed acquisition document."""
    document = f"acquisition/sha256/{acquisition_id}/acquisition.json"
    retrieval = clock("PRESENT", role="EXACT_REQUEST_INTERVAL", literal=request["ended_utc"],
                      start_literal=request["started_utc"], zone="Z", precision="microsecond",
                      earliest=request["started_utc"], latest=request["ended_utc"], document=document,
                      pointer=f"/requests/{index}/ended_utc")
    return {"origin": "WORKER_ARCHIVE_REPLAY", "request_seq": request["seq"], "final_url": request["url"],
            "status": request["http_status"], "headers": request["headers"], "payload": payload,
            "retrieval": retrieval, "receipt_document": document, "receipt_document_sha256": acquisition_id,
            "receipt_pointer": f"/requests/{index}"}


def control_version(receipt_sha256: str, receipt: dict[str, Any], payload: bytes) -> dict[str, Any]:
    """The manager-retained route control version from its raw receipt (zero requests)."""
    observed = _dt.datetime.fromisoformat(receipt["observed_at"]).astimezone(UTC)
    retrieval = clock("PRESENT", role="RECORDED_POSSESSION_UPPER_BOUND", literal=receipt["observed_at"],
                      zone="+00:00", precision="microsecond", earliest=fmt_utc(observed), latest=fmt_utc(observed),
                      document=raw_rel(receipt_sha256), pointer="/observed_at")
    return {"origin": "MANAGER_RETAINED_CONTROL_REPLAY", "request_seq": None, "final_url": receipt["final_url"],
            "status": receipt["status"], "headers": [[k, v] for k, v in receipt["headers"].items()],
            "payload": payload, "retrieval": retrieval, "receipt_document": raw_rel(receipt_sha256),
            "receipt_document_sha256": receipt_sha256, "receipt_pointer": "/headers"}


def derive_capture(contest_key: str, parent: dict[str, Any], game_id: str, version: dict[str, Any],
                   payload_sha256: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The exact capture record and its assertion rows for one archived version (producer and consumer)."""
    payload = version["payload"]
    checks, receipt_reasons, derived = receipt_checks(version["final_url"], version["status"], version["headers"],
                                                      payload, game_id)
    result = qualify(contest_key, parent, game_id, payload, derived["bound"], receipt_reasons)
    capture_id = f"wayback:{derived['wayback_timestamp'] or '00000000000000'}:{payload_sha256}"
    bound = derived["bound"]
    if bound:
        archive_clock = clock("PRESENT", role="ARCHIVE_CAPTURE_UPPER_BOUND", literal=derived["memento"], zone="GMT",
                              precision="second", latest=bound, document=version["receipt_document"],
                              pointer=version["receipt_pointer"])
        if result["reasons"]:
            archive_clock["reason"] = "CAPTURE_QUARANTINED:" + ",".join(result["reasons"])
    else:
        archive_clock = clock("INVALID", role="ARCHIVE_CAPTURE_UPPER_BOUND", literal=derived["memento"],
                              document=version["receipt_document"], pointer=version["receipt_pointer"],
                              reason=",".join(receipt_reasons) or "MEMENTO_DATETIME_ABSENT")
    event_literal = next((a["literal"] for a in result["assertions"] if a["field"] == "contest_date"
                          and a["witness"] == "JS_EVENT_TIMESTAMP"), None)
    if event_literal:
        precision, zone, earliest, latest = event_interval(event_literal)
        event = clock("PRESENT", role="SOURCE_ASSERTED_EVENT_INSTANT", literal=event_literal, zone=zone,
                      precision=precision, earliest=earliest, latest=latest, document=raw_rel(payload_sha256),
                      pointer="JS_EVENT_TIMESTAMP")
    else:
        event = clock("ABSENT", role="SOURCE_ASSERTED_EVENT_INSTANT", reason="NOT_WITNESSED_IN_VERSION")
    parts = replay_parts(version["final_url"])
    original = parts[1] if parts else None
    capture = {
        "record_type": "archive_capture", "capture_id": capture_id, "contest_key": contest_key,
        "origin": version["origin"], "request_seq": version["request_seq"], "original_url": original,
        "final_url": version["final_url"], "wayback_timestamp": derived["wayback_timestamp"],
        "http_status": version["status"], "content_type": derived["content_type"],
        "memento_datetime_literal": derived["memento"], "origin_date_literal": derived["origin"],
        "link_original": derived["original"], "archive_src": derived["archive_src"],
        "payload_sha256": payload_sha256, "payload_bytes": len(payload), "payload_path": raw_rel(payload_sha256),
        "receipt_document": version["receipt_document"], "receipt_document_sha256": version["receipt_document_sha256"],
        "receipt_pointer": version["receipt_pointer"], "receipt_checks": checks,
        "state": "QUALIFIED" if result["qualified"] else "QUARANTINED", "quarantine_reasons": result["reasons"],
        "time_evidence_class": "ARCHIVE_CAPTURE_UPPER_BOUND",
        "clocks": {"archive_capture": archive_clock, "retrieval": version["retrieval"], "event": event},
        "main_element_spans": result["scopes"], "page_status": result["page_status"],
        "page_participants": result["page_participants"], "orientation": result["orientation"],
        "participant_mapping": result["participant_mapping"], "field_states": result["states"]}
    assertions = [{"record_type": "archive_assertion", "contest_key": contest_key, "original_url": original,
                   "capture_id": capture_id, "payload_sha256": payload_sha256, "source_revision": capture_id,
                   "field": a["field"], "field_role": ROLES[a["field"]], "witness": a["witness"],
                   "witness_span": a["witness_span"], "literal": a["literal"], "value": a["value"],
                   "parent_value": a["parent_value"], "parent_comparator": a["parent_comparator"],
                   "corroboration": a["corroboration"], "field_state": a["field_state"]}
                  for a in result["assertions"]]
    assertions.sort(key=lambda a: (FIELDS.index(a["field"]), a["witness"], a["witness_span"][0]))
    return capture, assertions


def disposition_summary(outcome: str, captures: list[dict[str, Any]]) -> dict[str, Any]:
    """Disposition, reasons, field support and capture accounting of one tranche key from its captures."""
    support: dict[str, Any] = {}
    for field in WITNESSABLE:
        bounds = sorted(c["clocks"]["archive_capture"]["latest_utc"] for c in captures if c["field_states"][field] == QUAL)
        support[field] = bounds[0] if bounds else None
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
    return {"disposition": disposition, "reasons": sorted(set(reasons)), "field_support": support,
            "capture_ids": [c["capture_id"] for c in captures],
            "qualified_capture_ids": [c["capture_id"] for c in captures if c["state"] == "QUALIFIED"]}

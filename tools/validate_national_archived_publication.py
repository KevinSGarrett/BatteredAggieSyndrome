r"""Independent validator for the 2019 archived-publication evidence sidecar (BAT-713, Cycle #41 TP41-A01).

``python -B tools/validate_national_archived_publication.py --contract
configs/national_archived_publication_2019_contract_v1_1.json --source-database <bound source-time sqlite>
--source-bindings <INPUT_BINDINGS.json> --tranche <ARCHIVE_TRANCHE.json>
--manifest <manifests/national_archived_publication_2019/sha256/<content id>/run_manifest.json> --report <new path>``

Standard library only. It imports no producer, query or project code (in particular not the shared field-grain module
the producer and consumer use). From the files themselves it re-verifies the contract (the V1.1 successor), the parent
source-time database (location, run manifest identity document, bytes), the manager's bindings, tranche and retained
control; it re-reads the acquisition journal and document, every raw body and receipt; it scans every archived page
with its own byte scanner (start-tag attribute tokenizing, div/span/a balance, complete text of child-free elements,
line-start script assignments, every occurrence counted) and reads the parent's CFBD/NCAA lineage itself to rebuild
every main-element span, witness, value, participant map (documented parent name, CFBD role and date; numeric ESPN
and CFBD identifiers are never equated), orientation, field state, capture state, upper bound and disposition; it
compares every delivered record field by field by natural key, recomputes both identity documents and every database
row, and recomputes cutoff decisions that it compares with the delivered query consumer run as a subprocess.
Coordinated semantic tampers of the delivered records (as if every outer hash were consistently recomputed) and oracle
self-challenges on in-memory page copies (borrowed status/score substrings, same-element digits, unrelated or swapped
team names with equal numbers, duplicated witnesses) are reported with their limits. The report is a new file written
once. Exit 0 only when every check passes.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import gzip
import hashlib
import html
import json
import os
import re
import sqlite3
import subprocess
import sys
import zlib
from pathlib import Path
from typing import Any

UTCZ = dt.timezone.utc
FIELD_LIST = ["season", "contest_date", "a_participant", "b_participant", "completion", "a_points", "b_points"]
OUTCOME = {"completion", "a_points", "b_points"}
SUPPORTABLE = ["contest_date", "a_participant", "b_participant", "completion", "a_points", "b_points"]
PAYLOAD_NAMES = ["dispositions.jsonl", "requests.jsonl", "captures.jsonl", "assertions.jsonl"]
QUAL = "QUALIFIED_AGREES_WITH_PARENT"
MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
                                      "Dec"], start=1)}
PROBE_CUTOFFS = ["2019-01-01T00:00:00Z", "2019-08-24T23:00:00Z", "2019-09-02T01:00:50Z",
                 "2019-09-02T01:00:50.999999Z", "2019-09-01T21:00:50.999999-04:00", "2019-12-31T23:59:59Z",
                 "2026-10-02T00:00:00Z"]


def h_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def h_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            block = stream.read(1 << 20)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def cjson(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class Report:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def check(self, name: str, ok: bool, detail: Any = None) -> bool:
        self.checks.append({"check": name, "ok": bool(ok), "detail": detail})
        return bool(ok)

    def failed(self) -> list[str]:
        return [c["check"] for c in self.checks if not c["ok"]]


# --------------------------------------------------------------------------------------------- time and URL rules

def z(value: dt.datetime) -> str:
    return value.astimezone(UTCZ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def gmt(text: Any) -> dt.datetime | None:
    """RFC 1123 'Mon, 02 Sep 2019 01:00:50 GMT' only."""
    if not isinstance(text, str):
        return None
    m = re.fullmatch(r"\s*[A-Z][a-z]{2}, (\d{2}) ([A-Z][a-z]{2}) (\d{4}) (\d{2}):(\d{2}):(\d{2}) GMT\s*", text)
    if not m or m.group(2) not in MONTHS:
        return None
    try:
        return dt.datetime(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)), int(m.group(4)), int(m.group(5)),
                           int(m.group(6)), tzinfo=UTCZ)
    except ValueError:
        return None


def ts14(text: Any) -> dt.datetime | None:
    if not isinstance(text, str) or not re.fullmatch(r"\d{14}", text):
        return None
    try:
        return dt.datetime(int(text[:4]), int(text[4:6]), int(text[6:8]), int(text[8:10]), int(text[10:12]),
                           int(text[12:14]), tzinfo=UTCZ)
    except ValueError:
        return None


def iso_interval(text: Any) -> tuple[str, str] | None:
    if not isinstance(text, str):
        return None
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?(Z|[+-]\d{2}:\d{2})", text)
    if not m:
        return None
    zone = m.group(7)
    off = dt.timedelta(0) if zone == "Z" else (1 if zone[0] == "+" else -1) * dt.timedelta(
        hours=int(zone[1:3]), minutes=int(zone[4:6]))
    try:
        start = dt.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)),
                            int(m.group(6) or 0), tzinfo=dt.timezone(off))
    except ValueError:
        return None
    end = start + (dt.timedelta(seconds=59, microseconds=999999) if m.group(6) is None else
                   dt.timedelta(microseconds=999999))
    return z(start), z(end)


def us_dates(text: str) -> list[str]:
    span = iso_interval(text)
    out = set()
    for bound in span or ():
        instant = dt.datetime.strptime(bound, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTCZ)
        for hours in (4, 10):
            out.add((instant - dt.timedelta(hours=hours)).date().isoformat())
    return sorted(out)


def earliest_instant(day: str) -> dt.datetime:
    y, mth, d = (int(x) for x in day.split("-"))
    return dt.datetime(y, mth, d, tzinfo=dt.timezone(dt.timedelta(hours=14))).astimezone(UTCZ)


def is_game_url(url: Any, game: str) -> bool:
    m = re.fullmatch(r"(?i:https?)://(?i:www\.espn\.com)(?::(80|443))?(/college-football/game/_/gameId/(\d{1,12}))",
                     str(url))
    return bool(m) and m.group(3) == game


def replay_split(url: Any) -> tuple[str, str] | None:
    m = re.fullmatch(r"https://(?i:web\.archive\.org)(?::443)?/web/(\d{14})id_/(\S+)", str(url))
    return (m.group(1), m.group(2)) if m else None


def header_of(headers: Any, name: str) -> Any:
    pairs = list(headers.items()) if isinstance(headers, dict) else [tuple(x) for x in headers or []]
    for key, value in pairs:
        if str(key).lower() == name.lower():
            return value
    return None


def link_rel_original(link: Any) -> str | None:
    if not isinstance(link, str):
        return None
    for part in link.split(","):
        m = re.match(r"\s*<([^>]*)>(.*)$", part)
        if m and re.search(r'rel\s*=\s*"original"', m.group(2)):
            return m.group(1)
    return None


# --------------------------------------------------------------------------------------------- byte scanner
#: a start tag whose quoted attribute values may contain '>' (the value is skipped whole)
START_TAG = rb"<%s\b(?:[^>\"']|\"[^\"]*\"|'[^']*')*>"
JS_LINE = re.compile(rb'^[ \t]*(espn\.gamepackage\.(gameId|status|homeTeamId|awayTeamId|timestamp)[ \t]*=[ \t]*'
                     rb'"([^"\\\r\n]*)"[ \t]*;)', re.M)
JS_WITNESS = {b"gameId": "JS_GAME_ID", b"status": "JS_STATUS", b"homeTeamId": "JS_HOME_TEAM_ID",
              b"awayTeamId": "JS_AWAY_TEAM_ID", b"timestamp": "JS_EVENT_TIMESTAMP"}


def tag_attrs(tag: bytes) -> list[tuple[bytes, bytes | None, int, int]]:
    """Every attribute of one raw start tag, in order: (lower name, value, value start, value end) offsets inside
    ``tag``. A quoted value is consumed whole, so text inside one attribute's value never becomes an attribute."""
    out: list[tuple[bytes, bytes | None, int, int]] = []
    head = re.match(rb"<[A-Za-z][^\s/>]*", tag)
    i = head.end() if head else len(tag)
    n = len(tag) - (2 if tag.endswith(b"/>") else 1)
    space = b" \t\r\n\f"
    while i < n:
        while i < n and tag[i:i + 1] in space + b"/":
            i += 1
        if i >= n:
            break
        j = i
        while j < n and tag[j:j + 1] not in space + b"/>=\"'":
            j += 1
        if j == i:
            i += 1
            continue
        name = tag[i:j].lower()
        k = j
        while k < n and tag[k:k + 1] in space:
            k += 1
        if k < n and tag[k:k + 1] == b"=":
            k += 1
            while k < n and tag[k:k + 1] in space:
                k += 1
            quote = tag[k:k + 1]
            if quote in (b'"', b"'"):
                close = tag.find(quote, k + 1)
                close = n if close < 0 or close > n else close
                out.append((name, tag[k + 1:close], k + 1, close))
                i = close + 1
            else:
                e = k
                while e < n and tag[e:e + 1] not in space + b">":
                    e += 1
                out.append((name, tag[k:e], k, e))
                i = e
        else:
            out.append((name, None, j, j))
            i = j
    return out


def one_attr(tag: bytes, name: bytes) -> Any:
    """(value, start, end) of the single attribute ``name``; None if absent; "REPEATED" if it occurs twice."""
    found = [a for a in tag_attrs(tag) if a[0] == name]
    if not found:
        return None
    if len(found) > 1:
        return "REPEATED"
    return found[0][1], found[0][2], found[0][3]


def class_set(tag: bytes) -> set[bytes]:
    value = one_attr(tag, b"class")
    return set(value[0].split()) if isinstance(value, tuple) and value[0] is not None else set()


def div_end(data: bytes, open_end: int) -> int | None:
    """End offset (after '</div>') of the div whose start tag ends at ``open_end`` (div balance)."""
    depth = 1
    for m in re.finditer(rb"<(/?)div\b[^>]*>", data[open_end:]):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return open_end + m.end()
    return None


def close_start(data: bytes, open_end: int, tag: bytes) -> int | None:
    """Start offset of the closing tag that balances the ``tag`` element whose start tag ends at ``open_end``."""
    depth = 1
    for m in re.finditer(rb"<(/?)" + tag + rb"\b[^>]*>", data[open_end:]):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return open_end + m.start()
    return None


def text_witness(data: bytes, open_end: int, close: int | None) -> tuple[int, int, str | None] | None:
    """The complete text of a closed, child-free element, trimmed; None when it is empty."""
    if close is None:
        return open_end, open_end, "ELEMENT_NOT_CLOSED"
    content = data[open_end:close]
    if b"<" in content or b">" in content:
        return open_end, close, "CHILD_MARKUP_IN_TEXT_WITNESS"
    text = content.decode("utf-8")
    stripped = text.strip()
    if not stripped:
        return None
    start = open_end + len(text[:len(text) - len(text.lstrip())].encode("utf-8"))
    return start, start + len(stripped.encode("utf-8")), None


def tags(data: bytes, name: bytes, lo: int, hi: int) -> list[re.Match]:
    return [m for m in re.finditer(START_TAG % name, data[lo:hi])]


def scan_page(data: bytes) -> dict[str, Any]:
    """Every main-element witness occurrence from raw bytes (independent of any HTML parser library)."""
    out: dict[str, Any] = {"navs": [], "infos": [], "js": [], "witnesses": [], "problems": []}

    def attr_witness(name: str, tag_start: int, tag: bytes, attribute: bytes) -> None:
        value = one_attr(tag, attribute)
        if value == "REPEATED":
            first = next(a for a in tag_attrs(tag) if a[0] == attribute)
            out["witnesses"].append((name, tag_start + first[2], tag_start + first[3], "ATTRIBUTE_REPEATED"))
        elif value is not None:
            out["witnesses"].append((name, tag_start + value[1], tag_start + value[2], None))

    def text_of(name: str, open_end: int, close: int | None) -> None:
        found = text_witness(data, open_end, close)
        if found is not None:
            out["witnesses"].append((name, found[0], found[1], found[2]))
    for m in tags(data, b"div", 0, len(data)):
        ident = one_attr(m.group(0), b"id")
        ident = ident[0] if isinstance(ident, tuple) else None
        if ident == b"custom-nav":
            end = div_end(data, m.end())
            out["navs"].append((m.start(), end))
            attr_witness("NAV_GAME_ID", m.start(), m.group(0), b"data-id")
            if end is None:
                continue
            nav = (m.start(), end)
            for team in tags(data, b"div", nav[0], nav[1]):
                cls = class_set(team.group(0))
                if b"team" not in cls or not ({b"home", b"away"} & cls):
                    continue
                if {b"home", b"away"} <= cls:
                    out["problems"].append("TEAM_BLOCK_SIDE_AMBIGUOUS")
                    continue
                side = "HOME" if b"home" in cls else "AWAY"
                t_start = nav[0] + team.start()
                t_end = div_end(data, nav[0] + team.end()) or nav[1]
                for anchor in tags(data, b"a", t_start, t_end):
                    if b"team-name" not in class_set(anchor.group(0)):
                        continue
                    a_start = t_start + anchor.start()
                    attr_witness(f"{side}_TEAM_HREF", a_start, anchor.group(0), b"href")
                    a_open = t_start + anchor.end()
                    a_close = close_start(data, a_open, b"a") or t_end
                    for span in tags(data, b"span", a_open, a_close):
                        if b"long-name" in class_set(span.group(0)):
                            s_open = a_open + span.end()
                            text_of(f"{side}_TEAM_NAME", s_open, close_start(data, s_open, b"span"))
                for div in tags(data, b"div", t_start + len(team.group(0)), t_end):
                    if b"score" in class_set(div.group(0)):
                        d_open = t_start + len(team.group(0)) + div.end()
                        text_of(f"{side}_SCORE", d_open, close_start(data, d_open, b"div"))
            for span in tags(data, b"span", nav[0], nav[1]):
                if b"status-detail" in class_set(span.group(0)):
                    s_open = nav[0] + span.end()
                    text_of("STATUS_DETAIL", s_open, close_start(data, s_open, b"span"))
        elif ident == b"gamepackage-game-information":
            end = div_end(data, m.end())
            out["infos"].append((m.start(), end))
            if end is None:
                continue
            for box in tags(data, b"div", m.start(), end):
                if b"game-date-time" not in class_set(box.group(0)):
                    continue
                b_start = m.start() + box.start()
                b_end = div_end(data, m.start() + box.end()) or end
                for span in tags(data, b"span", b_start, b_end):
                    behaviour = one_attr(span.group(0), b"data-behavior")
                    if isinstance(behaviour, tuple) and behaviour[0] == b"date_time":
                        attr_witness("INFO_EVENT_DATE", b_start + span.start(), span.group(0), b"data-date")
    for script in re.finditer(rb"<script\b(?:[^>\"']|\"[^\"]*\"|'[^']*')*>(.*?)</script\s*>", data, re.S | re.I):
        body = script.start(1)
        for js in JS_LINE.finditer(script.group(1)):
            out["js"].append((body + js.start(1), body + js.end(1)))
            out["witnesses"].append((JS_WITNESS[js.group(2)], body + js.start(3), body + js.end(3), None))
    out["witnesses"].sort(key=lambda w: (w[1], w[2], w[0]))
    out["problems"] = list(dict.fromkeys(out["problems"]))
    return out


def normalize(name: str, literal: str) -> Any:
    if name in ("JS_GAME_ID", "JS_HOME_TEAM_ID", "JS_AWAY_TEAM_ID"):
        return literal if re.fullmatch(r"\d{1,12}", literal) else None
    if name == "NAV_GAME_ID":
        m = re.fullmatch(r"gamepackage-(\d{1,12})", literal)
        return m.group(1) if m else None
    if name in ("HOME_TEAM_HREF", "AWAY_TEAM_HREF"):
        m = re.fullmatch(r"(?:https?://www\.espn\.com)?/college-football/team/_/id/(\d{1,12})(?:/[^\s\"'<>]*)?",
                         literal)
        return m.group(1) if m else None
    if name in ("HOME_TEAM_NAME", "AWAY_TEAM_NAME"):
        text = " ".join(html.unescape(literal).split())
        return text or None
    if name in ("HOME_SCORE", "AWAY_SCORE"):
        return int(literal) if re.fullmatch(r"\d{1,3}", literal) else None
    if name in ("JS_EVENT_TIMESTAMP", "INFO_EVENT_DATE"):
        return literal if iso_interval(literal) else None
    return literal


# --------------------------------------------------------------------------------------------- participant evidence

def team_sources(rec: dict[str, Any], lineage: list[dict[str, Any]], rule: str) -> dict[str, Any]:
    """The parent's own documented team names and CFBD roles, read here from the parent lineage rows."""
    cfbd_ids = {"A": (rec.get("a_cfbd_team_id") or {}).get("value"),
                "B": (rec.get("b_cfbd_team_id") or {}).get("value")}
    named: dict[str, dict[str, set[str]]] = {"A": {}, "B": {}}

    def note(side: str, name: Any, source: str) -> None:
        if name:
            named[side].setdefault(str(name), set()).add(source)
    note("A", rec.get("a_team_name"), "NCAA_TEAM_NAME")
    note("B", rec.get("b_team_name"), "NCAA_TEAM_NAME")
    rows, views, problems = [], set(), []
    for row in lineage:
        if row.get("join_state") != "PARENT_LINEAGE":
            continue
        lit = row.get("literals") or {}
        if row.get("source_kind") == "NCAA_TEAM_SEASON_PAGE":
            mine = (row.get("orientation") or {}).get("page_team_side")
            if mine in ("A", "B"):
                note(mine, lit.get("page_team_name"), "NCAA_TEAM_NAME")
                note("B" if mine == "A" else "A", lit.get("opponent_name"), "NCAA_TEAM_NAME")
        elif row.get("source_kind") == "CFBD_ROUTE_RESPONSE":
            home = (row.get("orientation") or {}).get("home_side")
            if home not in ("A", "B"):
                problems.append("CFBD_HOME_SIDE_UNKNOWN")
                continue
            away = "B" if home == "A" else "A"
            if (lit.get("homeId"), lit.get("awayId")) != (cfbd_ids[home], cfbd_ids[away]) or \
                    not lit.get("homeTeam") or not lit.get("awayTeam"):
                problems.append("CFBD_ROW_DOES_NOT_BIND_THE_PARENT_TEAMS")
            views.add((home, lit.get("homeTeam"), lit.get("homeId"), lit.get("awayTeam"), lit.get("awayId")))
            rows.append({"capture_id": row.get("capture_id"), "native_row_key": row.get("native_row_key"),
                         "source_revision": row.get("source_revision"),
                         "evidence_document": (row.get("event_clock") or {}).get("evidence_document"),
                         "home_side": home, "home_team": lit.get("homeTeam"), "away_team": lit.get("awayTeam"),
                         "neutral_site": lit.get("neutralSite")})
    rows.sort(key=lambda r: (str(r["capture_id"]), str(r["native_row_key"])))
    state = "CFBD_SOURCE_ABSENT" if not rows else (
        "CFBD_SOURCE_CONTRADICTORY" if problems or len(views) != 1 else "PRESENT")
    view = next(iter(views)) if state == "PRESENT" else None
    sides = {}
    for side in ("A", "B"):
        role = school = None
        if view:
            role = "HOME" if view[0] == side else "AWAY"
            school = view[1] if role == "HOME" else view[3]
            note(side, school, "CFBD_SCHOOL_NAME")
        letter = side.lower()
        sides[letter] = {"parent_key": rec.get(f"{letter}_key"), "cfbd_team_id": rec.get(f"{letter}_cfbd_team_id"),
                         "cfbd_school_name": school, "cfbd_role": role,
                         "documented_names": [{"name": k, "sources": sorted(v)} for k, v in sorted(named[side].items())]}
    return {"state": state, "problems": sorted(set(problems)), "cfbd_rows": rows, "sides": sides, "rule": rule}


def map_teams(src: dict[str, Any], page: dict[str, dict[str, Any]], date_agrees: bool, rule: str) -> dict[str, Any]:
    out: dict[str, Any] = {"state": None, "reason": None, "rule": rule, "a_side": None, "b_side": None,
                           "sources": {"state": src["state"], "problems": src["problems"], "cfbd_rows": src["cfbd_rows"],
                                       "sides": src["sides"]}, "sides": {}}

    def no(reason: str) -> dict[str, Any]:
        out["state"], out["reason"] = "UNRESOLVED", reason
        return out
    if src["state"] != "PRESENT":
        return no(src["state"])
    for side in ("HOME", "AWAY"):
        p = page[side]
        if p["ids_disagree"] or p["js"] in ("CONTRADICTORY", "DUPLICATED", "UNPARSEABLE") or \
                p["href"] in ("CONTRADICTORY", "DUPLICATED", "UNPARSEABLE"):
            return no(f"{side}_TEAM_ID_WITNESSES_NOT_SINGLE_AND_EQUAL")
        if not p["ids_agree"]:
            return no(f"{side}_TEAM_ID_NOT_WITNESSED")
        if p["name_state"] != "OK":
            return no(f"{side}_TEAM_NAME_{p['name_state']}")
    pick = {}
    for side in ("HOME", "AWAY"):
        hits = [x for x in ("a", "b") if page[side]["name"] in {d["name"] for d in src["sides"][x]["documented_names"]}]
        if not hits:
            return no(f"{side}_TEAM_NAME_NOT_DOCUMENTED_FOR_EITHER_PARENT_TEAM")
        if len(hits) == 2:
            return no(f"{side}_TEAM_NAME_AMBIGUOUS_BETWEEN_PARENT_TEAMS")
        pick[side] = hits[0]
    if pick["HOME"] == pick["AWAY"]:
        return no("BOTH_PAGE_TEAMS_MAP_TO_ONE_PARENT_TEAM")
    for side in ("HOME", "AWAY"):
        if src["sides"][pick[side]]["cfbd_role"] != side:
            return no(f"{side}_TEAM_ROLE_CONTRADICTS_THE_CFBD_ROUTE_ROLE")
    if not date_agrees:
        return no("CONTEST_DATE_NOT_CORROBORATED_IN_THIS_VERSION")
    for side in ("HOME", "AWAY"):
        own = (src["sides"][pick[side]]["cfbd_team_id"] or {}).get("value")
        opp = (src["sides"]["b" if pick[side] == "a" else "a"]["cfbd_team_id"] or {}).get("value")
        if page[side]["id"] == opp and page[side]["id"] != own:
            return no(f"{side}_ESPN_TEAM_ID_EQUALS_THE_OPPONENT_CFBD_ID")
    for side in ("HOME", "AWAY"):
        letter = pick[side]
        info = src["sides"][letter]
        doc = next(d for d in info["documented_names"] if d["name"] == page[side]["name"])
        own = (info["cfbd_team_id"] or {}).get("value")
        out["sides"][side.lower()] = {
            "page_side": side, "parent_side": letter, "parent_key": info["parent_key"],
            "espn_team_id": {"namespace": "ESPN_TEAM_ID", "value": page[side]["id"]},
            "espn_location_name": page[side]["name"], "documented_name": doc["name"], "name_sources": doc["sources"],
            "cfbd_team_id": info["cfbd_team_id"], "cfbd_role": info["cfbd_role"],
            "id_relation": "ESPN_ID_LITERAL_EQUALS_CFBD_ID_LITERAL_NOT_AUTHORITY" if page[side]["id"] == own
            else "ESPN_ID_DIFFERS_FROM_CFBD_ID"}
        out[f"{letter}_side"] = side
    out["state"] = "QUALIFIED"
    return out


# --------------------------------------------------------------------------------------------- reconstruction

class Expected:
    """Every record the delivery should contain, rebuilt from contract, parent, acquisition and raw bytes."""

    def __init__(self, contract: dict[str, Any], ctx: dict[str, Any]) -> None:
        self.contract = contract
        self.ctx = ctx
        self.records: dict[str, list[dict[str, Any]]] = {name: [] for name in PAYLOAD_NAMES}

    def raw(self, sha: str) -> bytes:
        data = (self.ctx["out"] / "raw" / "sha256" / sha).read_bytes()
        if h_bytes(data) != sha:
            raise ValueError(f"raw {sha} altered")
        return data

    def versions(self, key: str, spec: dict[str, Any]) -> list[dict[str, Any]]:
        out = []
        acq = self.ctx["acquisition"]
        if spec["selection_role"] == "SEPARATE_PREQUALIFIED_ROUTE_CONTROL":
            receipt = self.ctx["control_receipt"]
            seen = dt.datetime.fromisoformat(receipt["observed_at"]).astimezone(UTCZ)
            doc = f"raw/sha256/{self.ctx['control_receipt_sha']}"
            out.append({"origin": "MANAGER_RETAINED_CONTROL_REPLAY", "seq": None, "url": receipt["final_url"],
                        "status": receipt["status"], "headers": list(receipt["headers"].items()),
                        "payload": self.ctx["control_payload"], "receipt_document": doc,
                        "receipt_document_sha256": self.ctx["control_receipt_sha"], "receipt_pointer": "/headers",
                        "retrieval": {"state": "PRESENT", "role": "RECORDED_POSSESSION_UPPER_BOUND",
                                      "literal": receipt["observed_at"], "start_literal": None, "zone": "+00:00",
                                      "precision": "microsecond", "earliest_utc": z(seen), "latest_utc": z(seen),
                                      "evidence_document": doc, "evidence_pointer": "/observed_at", "reason": None}})
        for i, req in enumerate(acq["requests"]):
            if req["contest_key"] != key or req["kind"] != "REPLAY" or req["http_status"] != 200:
                continue
            doc = f"acquisition/sha256/{self.ctx['acquisition_id']}/acquisition.json"
            out.append({"origin": "WORKER_ARCHIVE_REPLAY", "seq": req["seq"], "url": req["url"],
                        "status": req["http_status"], "headers": req["headers"], "payload": self.raw(req["body_sha256"]),
                        "receipt_document": doc, "receipt_document_sha256": self.ctx["acquisition_id"],
                        "receipt_pointer": f"/requests/{i}",
                        "retrieval": {"state": "PRESENT", "role": "EXACT_REQUEST_INTERVAL",
                                      "literal": req["ended_utc"], "start_literal": req["started_utc"], "zone": "Z",
                                      "precision": "microsecond", "earliest_utc": req["started_utc"],
                                      "latest_utc": req["ended_utc"], "evidence_document": doc,
                                      "evidence_pointer": f"/requests/{i}/ended_utc", "reason": None}})
        return out

    def capture(self, key: str, spec: dict[str, Any], version: dict[str, Any],
                payload: bytes | None = None) -> tuple[dict, list[dict]]:
        game = spec["game_id_literal"]
        parent = self.ctx["parent"][key]
        rec, val = parent["record"], parent["values"]
        payload = version["payload"] if payload is None else payload
        headers = version["headers"]
        problems: list[str] = []
        split = replay_split(version["url"])
        checks = {"replay_url_valid": bool(split) and is_game_url(split[1], game)}
        if not checks["replay_url_valid"]:
            problems.append("REPLAY_URL_INVALID")
        memento, origin = header_of(headers, "Memento-Datetime"), header_of(headers, "x-archive-orig-date")
        original = link_rel_original(header_of(headers, "Link"))
        ctype = header_of(headers, "Content-Type") or ""
        m_at = gmt(memento)
        checks["memento_datetime_valid"] = m_at is not None
        if m_at is None:
            problems.append("MEMENTO_DATETIME_ABSENT" if memento is None else "MEMENTO_DATETIME_MALFORMED")
        checks["memento_equals_url_timestamp"] = bool(m_at and split and m_at == ts14(split[0]))
        if m_at and split and not checks["memento_equals_url_timestamp"]:
            problems.append("ARCHIVE_TIMESTAMPS_CONTRADICTORY")
        checks["link_original_equivalent"] = bool(original) and is_game_url(original, game)
        if not checks["link_original_equivalent"]:
            problems.append("MEMENTO_FOR_ANOTHER_URL")
        checks["html_200"] = version["status"] == 200 and ctype.lower().startswith("text/html")
        if not checks["html_200"]:
            problems.append("NOT_AN_ARCHIVED_HTML_200")
        bound = m_at.replace(microsecond=999999) if m_at else None
        checks["origin_date_consistent"] = True
        if origin is not None:
            o_at = gmt(origin)
            if o_at is None or (m_at and o_at - m_at > dt.timedelta(seconds=300)):
                checks["origin_date_consistent"] = False
                problems.append("ORIGIN_DATE_CONTRADICTORY")
            elif m_at and o_at > m_at:
                bound = o_at.replace(microsecond=999999)
        try:
            payload.decode("utf-8")
            checks["body_utf8"] = True
        except UnicodeDecodeError:
            checks["body_utf8"] = False
            problems.append("BODY_NOT_UTF8")
        scan = scan_page(payload) if checks["body_utf8"] else {"navs": [], "infos": [], "js": [], "witnesses": [],
                                                                "problems": []}
        problems += [p for p in scan["problems"] if p not in problems]
        found: dict[str, list[tuple[int, int, str, Any]]] = {}
        for name, start, end, issue in scan["witnesses"]:
            literal = payload[start:end].decode("utf-8")
            found.setdefault(name, []).append((start, end, literal, None if issue else normalize(name, literal)))
        closed_navs = [n for n in scan["navs"] if n[1] is not None]
        if checks["body_utf8"]:
            if not closed_navs:
                problems.append("MAIN_GAME_ELEMENT_ABSENT")
            elif len(scan["navs"]) > 1:
                problems.append("MAIN_GAME_ELEMENT_DUPLICATED")

        def one(name: str) -> tuple[Any, str]:
            items = found.get(name) or []
            if not items:
                return None, "ABSENT"
            if any(i[3] is None for i in items):
                return None, "UNPARSEABLE"
            if len({json.dumps(i[3], sort_keys=True) for i in items}) > 1:
                return None, "CONTRADICTORY"
            return (items[0][3], "OK") if len(items) == 1 else (None, "DUPLICATED")
        if "MAIN_GAME_ELEMENT_ABSENT" not in problems and "MAIN_GAME_ELEMENT_DUPLICATED" not in problems \
                and checks["body_utf8"]:
            nav_value, nav_state = one("NAV_GAME_ID")
            js_value, js_state = one("JS_GAME_ID")
            if nav_state != "OK" or nav_value != game:
                problems.append("WRONG_GAME_NODE")
            if js_state == "CONTRADICTORY":
                problems.append("GAME_IDENTITY_CONTRADICTORY")
            elif js_state == "DUPLICATED":
                problems.append("GAME_IDENTITY_DUPLICATED")
            elif js_state != "OK" or js_value != game:
                problems.append("GAME_IDENTITY_MISMATCH")
        status_js, s1 = one("JS_STATUS")
        detail, s2 = one("STATUS_DETAIL")
        final_page = s1 == "OK" and s2 == "OK" and status_js == "post" and isinstance(detail, str) and \
            bool(re.fullmatch(r"Final(/\d*OT)?", detail))
        if final_page and bound and bound < earliest_instant(rec["contest_date"]):
            problems.append("IMPOSSIBLE_CHRONOLOGY")
        ok_capture = not problems
        bad_state = {"UNPARSEABLE": "WITNESS_LITERAL_UNPARSEABLE", "CONTRADICTORY": "CONTRADICTORY_WITHIN_VERSION",
                     "DUPLICATED": "DUPLICATED_WITNESS"}
        states: dict[str, str] = {"season": "NOT_WITNESSED_IN_VERSION"}
        rows: list[dict[str, Any]] = []

        def put(field: str, names: list[str], state: str, corr: str, comparator: Any) -> None:
            states[field] = state
            for name in sorted(names):
                for start, end, literal, value in found.get(name) or []:
                    shown = value
                    if value is not None and name in ("JS_HOME_TEAM_ID", "JS_AWAY_TEAM_ID", "HOME_TEAM_HREF",
                                                      "AWAY_TEAM_HREF"):
                        shown = {"namespace": "ESPN_TEAM_ID", "value": value}
                    elif value is not None and name in ("HOME_TEAM_NAME", "AWAY_TEAM_NAME"):
                        shown = {"namespace": "ESPN_TEAM_LOCATION_NAME", "value": value}
                    rows.append({"field": field, "witness": name, "witness_span": [start, end], "literal": literal,
                                 "value": shown, "parent_value": val[field], "parent_comparator": comparator,
                                 "corroboration": "UNPARSEABLE" if value is None else corr, "field_state": state})
        dates = [n for n in ("JS_EVENT_TIMESTAMP", "INFO_EVENT_DATE") if found.get(n)]
        date_agrees = False
        if not dates:
            states["contest_date"] = "NOT_WITNESSED_IN_VERSION"
        else:
            got = [one(n) for n in dates]
            worst = [s for _v, s in got if s != "OK"]
            if worst:
                kind = "UNPARSEABLE" if "UNPARSEABLE" in worst else ("CONTRADICTORY" if "CONTRADICTORY" in worst
                                                                     else "DUPLICATED")
                st = bad_state[kind]
                corr = "UNPARSEABLE" if kind == "UNPARSEABLE" else st
            elif len({v for v, _s in got}) != 1:
                st, corr = "CONTRADICTORY_WITHIN_VERSION", "CONTRADICTORY_WITHIN_VERSION"
            else:
                agrees = rec["contest_date"] in us_dates(got[0][0])
                corr = "AGREES_WITH_PARENT" if agrees else "CONFLICTS_WITH_PARENT"
                st = (QUAL if agrees else "CONFLICTS_WITH_PARENT") if len(dates) == 2 else "INCOMPLETE_WITNESS_SET"
                date_agrees = st == QUAL
            put("contest_date", dates, st if ok_capture else "CAPTURE_NOT_QUALIFIED", corr,
                {"basis": "US_LOCAL_CANDIDATE_DATES_-4H_-10H", "value": rec["contest_date"]})
        page = {}
        for side in ("HOME", "AWAY"):
            jv, jst = one(f"JS_{side}_TEAM_ID")
            hv, hst = one(f"{side}_TEAM_HREF")
            nv, nst = one(f"{side}_TEAM_NAME")
            page[side] = {"id": jv if (jst == "OK" and hst == "OK" and jv == hv) else None, "js": jst, "href": hst,
                          "name": nv if nst == "OK" else None, "name_state": nst,
                          "ids_agree": jst == "OK" and hst == "OK" and jv == hv,
                          "ids_disagree": jst == "OK" and hst == "OK" and jv != hv}
        rule = self.contract["participant_mapping"]["rule"]
        mapping = map_teams(parent["teams"], page, date_agrees, rule)
        orient = {"a_side": mapping["a_side"], "b_side": mapping["b_side"], "rule": rule}
        team_names = ("JS_HOME_TEAM_ID", "HOME_TEAM_HREF", "HOME_TEAM_NAME", "JS_AWAY_TEAM_ID", "AWAY_TEAM_HREF",
                      "AWAY_TEAM_NAME")
        for field, letter in (("a_participant", "a"), ("b_participant", "b")):
            if not any(found.get(n) for n in team_names):
                states[field] = "NOT_WITNESSED_IN_VERSION"
                continue
            if mapping["state"] != "QUALIFIED":
                split_ids = any(page[s][k] in ("CONTRADICTORY", "DUPLICATED") for s in ("HOME", "AWAY")
                                for k in ("js", "href")) or any(page[s]["ids_disagree"] for s in ("HOME", "AWAY"))
                states[field] = "CAPTURE_NOT_QUALIFIED" if not ok_capture else (
                    "CONTRADICTORY_WITHIN_VERSION" if split_ids else "PARTICIPANT_MAPPING_UNRESOLVED")
                continue
            side = mapping[f"{letter}_side"]
            info = mapping["sides"][side.lower()]
            put(field, [f"JS_{side}_TEAM_ID", f"{side}_TEAM_HREF", f"{side}_TEAM_NAME"],
                QUAL if ok_capture else "CAPTURE_NOT_QUALIFIED", "AGREES_WITH_PARENT",
                {"rule": "DOCUMENTED_PARENT_NAME_CFBD_ROLE_AND_DATE", "parent_key": info["parent_key"],
                 "documented_name": info["documented_name"], "name_sources": info["name_sources"],
                 "cfbd_team_id": info["cfbd_team_id"], "cfbd_role": info["cfbd_role"]})
        status_names = [n for n in ("JS_STATUS", "STATUS_DETAIL") if found.get(n)]
        completed = False
        if not status_names:
            states["completion"] = "NOT_WITNESSED_IN_VERSION"
        else:
            if len(status_names) < 2:
                st, corr = "INCOMPLETE_WITNESS_SET", "VERSION_PREDATES_OUTCOME"
            elif s1 != "OK" or s2 != "OK":
                kind = "UNPARSEABLE" if "UNPARSEABLE" in (s1, s2) else ("CONTRADICTORY" if "CONTRADICTORY" in (s1, s2)
                                                                       else "DUPLICATED")
                st = bad_state[kind]
                corr = "UNPARSEABLE" if kind == "UNPARSEABLE" else st
            elif final_page:
                completed = val["completion"] == "COMPLETED"
                st = QUAL if completed else "CONFLICTS_WITH_PARENT"
                corr = "AGREES_WITH_PARENT" if completed else "CONFLICTS_WITH_PARENT"
            else:
                st, corr = "NOT_SUPPORTED_BY_VERSION_STATUS", "VERSION_PREDATES_OUTCOME"
            put("completion", status_names, st if ok_capture else "CAPTURE_NOT_QUALIFIED", corr, None)
        for field, letter in (("a_points", "a"), ("b_points", "b")):
            if not final_page:
                states[field] = ("NOT_SUPPORTED_BY_VERSION_STATUS" if status_names else "NOT_WITNESSED_IN_VERSION") \
                    if ok_capture else "CAPTURE_NOT_QUALIFIED"
                continue
            if mapping["state"] != "QUALIFIED":
                states[field] = "ORIENTATION_UNRESOLVED" if ok_capture else "CAPTURE_NOT_QUALIFIED"
                continue
            side = mapping[f"{letter}_side"]
            score, sst = one(f"{side}_SCORE")
            if sst == "ABSENT":
                states[field] = "NOT_WITNESSED_IN_VERSION" if ok_capture else "CAPTURE_NOT_QUALIFIED"
                continue
            if sst != "OK":
                st = bad_state[sst]
                corr = "UNPARSEABLE" if sst == "UNPARSEABLE" else st
            else:
                agrees = score == val[field]
                corr = "AGREES_WITH_PARENT" if agrees else "CONFLICTS_WITH_PARENT"
                st = QUAL if agrees and completed else ("CONFLICTS_WITH_PARENT" if not agrees
                                                         else "NOT_SUPPORTED_BY_VERSION_STATUS")
            put(field, [f"{side}_SCORE"], st if ok_capture else "CAPTURE_NOT_QUALIFIED", corr, None)
        for field in FIELD_LIST:
            states.setdefault(field, "NOT_WITNESSED_IN_VERSION")
        ts = split[0] if split else None
        payload_sha = h_bytes(payload)
        capture_id = f"wayback:{ts or '00000000000000'}:{payload_sha}"
        doc, ptr = version["receipt_document"], version["receipt_pointer"]
        if bound:
            archive = {"state": "PRESENT", "role": "ARCHIVE_CAPTURE_UPPER_BOUND", "literal": memento,
                       "start_literal": None, "zone": "GMT", "precision": "second", "earliest_utc": None,
                       "latest_utc": z(bound), "evidence_document": doc, "evidence_pointer": ptr,
                       "reason": "CAPTURE_QUARANTINED:" + ",".join(problems) if problems else None}
        else:
            archive = {"state": "INVALID", "role": "ARCHIVE_CAPTURE_UPPER_BOUND", "literal": memento,
                       "start_literal": None, "zone": None, "precision": None, "earliest_utc": None,
                       "latest_utc": None, "evidence_document": doc, "evidence_pointer": ptr,
                       "reason": ",".join(p for p in problems if p in (
                           "REPLAY_URL_INVALID", "MEMENTO_DATETIME_ABSENT", "MEMENTO_DATETIME_MALFORMED",
                           "ARCHIVE_TIMESTAMPS_CONTRADICTORY", "MEMENTO_FOR_ANOTHER_URL", "NOT_AN_ARCHIVED_HTML_200",
                           "ORIGIN_DATE_CONTRADICTORY", "BODY_NOT_UTF8")) or "MEMENTO_DATETIME_ABSENT"}
        js_ts = [w for w in rows if w["field"] == "contest_date" and w["witness"] == "JS_EVENT_TIMESTAMP"]
        if js_ts:
            span = iso_interval(js_ts[0]["literal"])
            lit = js_ts[0]["literal"]
            zone = "Z" if lit.endswith("Z") else lit[-6:]
            precision = "minute" if re.fullmatch(r".*T\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})", lit) else "second"
            event = {"state": "PRESENT", "role": "SOURCE_ASSERTED_EVENT_INSTANT", "literal": lit,
                     "start_literal": None, "zone": zone, "precision": precision, "earliest_utc": span[0],
                     "latest_utc": span[1], "evidence_document": f"raw/sha256/{payload_sha}",
                     "evidence_pointer": "JS_EVENT_TIMESTAMP", "reason": None}
        else:
            event = {"state": "ABSENT", "role": "SOURCE_ASSERTED_EVENT_INSTANT", "literal": None,
                     "start_literal": None, "zone": None, "precision": None, "earliest_utc": None,
                     "latest_utc": None, "evidence_document": None, "evidence_pointer": None,
                     "reason": "NOT_WITNESSED_IN_VERSION"}
        scopes = [{"kind": "NAV", "span": [a, b]} for a, b in scan["navs"] if b is not None] + \
            [{"kind": "INFO", "span": [a, b]} for a, b in scan["infos"] if b is not None] + \
            [{"kind": "JS", "span": [a, b]} for a, b in scan["js"]]
        scopes.sort(key=lambda s: (s["span"][0], s["kind"]))
        participants = {}
        for side in ("HOME", "AWAY"):
            spans = sorted([n, [s, e]] for n in (f"JS_{side}_TEAM_ID", f"{side}_TEAM_HREF", f"{side}_TEAM_NAME")
                           for s, e, _l, _v in found.get(n) or [])
            participants[side.lower()] = {"espn_team_id": page[side]["id"], "espn_location_name": page[side]["name"],
                                          "js_state": page[side]["js"], "href_state": page[side]["href"],
                                          "name_state": page[side]["name_state"],
                                          "witnesses_agree": page[side]["ids_agree"], "witness_spans": spans}
        capture = {
            "record_type": "archive_capture", "capture_id": capture_id, "contest_key": key,
            "origin": version["origin"], "request_seq": version["seq"], "original_url": split[1] if split else None,
            "final_url": version["url"], "wayback_timestamp": ts, "http_status": version["status"],
            "content_type": ctype, "memento_datetime_literal": memento, "origin_date_literal": origin,
            "link_original": original, "archive_src": header_of(headers, "x-archive-src"),
            "payload_sha256": payload_sha, "payload_bytes": len(payload), "payload_path": f"raw/sha256/{payload_sha}",
            "receipt_document": doc, "receipt_document_sha256": version["receipt_document_sha256"],
            "receipt_pointer": ptr, "receipt_checks": checks, "state": "QUALIFIED" if ok_capture else "QUARANTINED",
            "quarantine_reasons": problems, "time_evidence_class": "ARCHIVE_CAPTURE_UPPER_BOUND",
            "clocks": {"archive_capture": archive, "retrieval": version["retrieval"], "event": event},
            "main_element_spans": scopes,
            "page_status": {"js_status": status_js, "status_detail": detail, "final": final_page},
            "page_participants": participants, "orientation": orient, "participant_mapping": mapping,
            "field_states": states}
        assertions = [{"record_type": "archive_assertion", "contest_key": key,
                       "original_url": split[1] if split else None, "capture_id": capture_id,
                       "payload_sha256": payload_sha, "source_revision": capture_id, "field_role":
                       "OUTCOME" if r["field"] in OUTCOME else "IDENTITY", **r} for r in rows]
        return capture, assertions

    def key_records(self, key: str, index: int) -> None:
        spec = next(s for s in self.contract["scope"]["keys"] if s["contest_key"] == key)
        row = self.ctx["tranche"][key]
        acq = self.ctx["acquisition"]
        captures, assertions = [], []
        for version in self.versions(key, spec):
            cap, rows = self.capture(key, spec, version)
            captures.append(cap)
            assertions += rows
        captures.sort(key=lambda c: (c["wayback_timestamp"] or "", c["payload_sha256"]))
        rank = {c["capture_id"]: i for i, c in enumerate(captures)}
        assertions.sort(key=lambda a: (rank[a["capture_id"]], FIELD_LIST.index(a["field"]), a["witness"],
                                       a["witness_span"][0]))
        mine = [r for r in acq["requests"] if r["contest_key"] == key]
        outcome = acq["outcomes"][key]
        support = {}
        for field in SUPPORTABLE:
            bounds = sorted(c["clocks"]["archive_capture"]["latest_utc"] for c in captures if c["field_states"][field] == QUAL)
            support[field] = bounds[0] if bounds else None
        supported = [f for f in SUPPORTABLE if support[f]]
        reasons = sorted({r for c in captures for r in c["quarantine_reasons"]})
        if outcome == "CONTROL_REUSED":
            disposition = "CONTROL_REUSED_QUALIFIED" if len(supported) == 6 else "ARCHIVED_VERSION_NOT_QUALIFIED"
        elif captures:
            disposition = "ARCHIVED_VERSION_QUALIFIED_ALL_WITNESSABLE_FIELDS" if len(supported) == 6 else (
                "ARCHIVED_VERSION_QUALIFIED_PARTIAL_FIELDS" if supported else "ARCHIVED_VERSION_NOT_QUALIFIED")
        else:
            disposition = outcome
        if outcome in ("REDIRECT_REFUSED", "REPLAY_REQUEST_FAILED") and captures:
            reasons.append(f"ACQUISITION_{outcome}")
        self.records["dispositions.jsonl"].append({
            "record_type": "archive_disposition", "ord": index, "contest_key": key, "season": row["season"],
            "contest_date": row["contest_date"], "a_key": row["a_key"], "b_key": row["b_key"],
            "classification_pair": row["classification_pair"], "stratum": row["stratum"],
            "selection_role": row["selection_role"], "candidate_url": spec["candidate_url"],
            "game_id_literal": spec["game_id_literal"], "acquisition_outcome": outcome, "disposition": disposition,
            "reasons": sorted(set(reasons)), "request_count": len(mine),
            "metadata_requests": sum(1 for r in mine if r["kind"] == "METADATA"),
            "replay_requests": sum(1 for r in mine if r["kind"] == "REPLAY"),
            "capture_ids": [c["capture_id"] for c in captures],
            "qualified_capture_ids": [c["capture_id"] for c in captures if c["state"] == "QUALIFIED"],
            "field_support": support, "parent_values": self.ctx["parent"][key]["values"]})
        for req in mine:
            answer = None
            if req["kind"] == "METADATA" and req["http_status"] == 200:
                answer = self.answer(self.raw(req["body_sha256"]), spec["game_id_literal"])
            self.records["requests.jsonl"].append({"record_type": "archive_request", **req,
                                                   "body_path": f"raw/sha256/{req['body_sha256']}"
                                                   if req["body_sha256"] else None, "metadata_answer": answer})
        self.records["captures.jsonl"] += captures
        self.records["assertions.jsonl"] += assertions

    @staticmethod
    def answer(body: bytes, game: str) -> dict[str, Any]:
        try:
            doc = json.loads(body.decode("utf-8"))
            closest = (doc.get("archived_snapshots") or {}).get("closest") or None
        except (UnicodeDecodeError, ValueError, AttributeError):
            return {"usable": False, "reason": "METADATA_ANSWER_NOT_JSON"}
        if not closest:
            return {"usable": False, "reason": "NO_CAPTURE_REPORTED"}
        stamp, status = str(closest.get("timestamp") or ""), str(closest.get("status") or "")
        m = re.fullmatch(r"https?://web\.archive\.org/web/(\d{14})(?:[a-z]{2}_)?/(.+)", str(closest.get("url") or ""))
        if closest.get("available") is not True or not re.fullmatch(r"\d{14}", stamp) or not m or m.group(1) != stamp:
            return {"usable": False, "reason": "CLOSEST_MALFORMED", "timestamp": stamp or None, "status": status or None}
        if not is_game_url(m.group(2), game):
            return {"usable": False, "reason": "CLOSEST_FOR_ANOTHER_URL", "timestamp": stamp, "status": status}
        if status not in ("200", "301", "302", "307", "308"):
            return {"usable": False, "reason": f"CLOSEST_STATUS_{status or 'ABSENT'}", "timestamp": stamp,
                    "status": status}
        return {"usable": True, "timestamp": stamp, "status": status, "original": m.group(2)}

    def build(self) -> None:
        for index, spec in enumerate(self.contract["scope"]["keys"]):
            self.key_records(spec["contest_key"], index)


def lines_of(records: list[dict[str, Any]]) -> bytes:
    return b"".join(cjson(r) + b"\n" for r in records)


# --------------------------------------------------------------------------------------------- bindings

def verify_inputs(contract: dict[str, Any], args: argparse.Namespace, report: Report) -> dict[str, Any]:
    ctx: dict[str, Any] = {}
    db = Path(args.source_database)
    pop_root = db.resolve().parent.parent.parent
    manifest = pop_root.parent.parent / "manifests" / pop_root.name / "sha256" / db.resolve().parent.name / \
        "run_manifest.json"
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    ident = doc["identity_document"]
    binding = contract["parent_binding"]["source_time"]
    db_sha = h_file(db)
    report.check("parent_source_time_identity_bound", h_bytes(cjson(ident)) == db.resolve().parent.name ==
                 doc["identity"] == binding["database_identity"] and ident["outputs"]["national_source_time.sqlite"]
                 == db_sha == binding["sqlite_sha256"] and ident["content_identity"] == binding["content_identity"]
                 and ident["contract_sha256"] == binding["contract_sha256"], {"identity": doc["identity"]})
    ctx["parent_binding"] = {"source_time": {"database_identity": doc["identity"], "sqlite_sha256": db_sha,
                                             "content_identity": ident["content_identity"],
                                             "contract_sha256": ident["contract_sha256"]}}
    tranche_raw = Path(args.tranche).read_bytes()
    tranche = json.loads(tranche_raw.decode("utf-8"))
    rows = tranche["selected"]
    keys = [r["contest_key"] for r in rows]
    report.check("tranche_bound_and_complete", h_bytes(tranche_raw) == contract["scope"]["tranche_sha256"] and
                 len(keys) == len(set(keys)) == contract["scope"]["tranche_count"] == tranche["count"] and
                 keys == [k["contest_key"] for k in contract["scope"]["keys"]], {"keys": len(keys)})
    ctx["tranche"] = {r["contest_key"]: r for r in rows}
    bindings_raw = Path(args.source_bindings).read_bytes()
    bindings = json.loads(bindings_raw.decode("utf-8"))
    report.check("bindings_bound", h_bytes(bindings_raw) == contract["parent_binding"]["source_bindings"]["sha256"]
                 and bindings["source_time_database"]["sha256"] == db_sha and
                 bindings["tranche"]["sha256"] == h_bytes(tranche_raw) and
                 bindings["control"]["sha256"] == contract["parent_binding"]["route_control"]["sha256"])
    route_path = Path(bindings["control"]["path"])
    route_raw = route_path.read_bytes()
    spec = contract["parent_binding"]["route_control"]
    receipt_raw = (route_path.parent / spec["raw_receipt_document"]).read_bytes()
    payload = (route_path.parent / spec["raw_payload"]).read_bytes()
    route = json.loads(route_raw.decode("utf-8"))
    report.check("control_bytes_bound", h_bytes(route_raw) == spec["sha256"] and
                 h_bytes(receipt_raw) == spec["raw_receipt_sha256"] and h_bytes(payload) == spec["raw_payload_sha256"]
                 and route["conservative_upper_bound"] == spec["conservative_upper_bound"])
    ctx.update(control_route_raw=route_raw, control_receipt_raw=receipt_raw, control_payload=payload,
               control_receipt=json.loads(receipt_raw.decode("utf-8")), control_route=route,
               control_receipt_sha=h_bytes(receipt_raw))
    conn = sqlite3.connect("file:" + str(db.resolve()).replace("\\", "/") + "?mode=ro", uri=True)
    parent = {}
    single = True
    rule = (contract.get("participant_mapping") or {}).get("rule", "")
    for key in keys:
        rec_text, blob, lineage_blob = conn.execute(
            "SELECT record, assertions, lineage FROM contests WHERE contest_key = ?", (key,)).fetchone()
        rec = json.loads(rec_text)
        seen: dict[str, set[str]] = {}
        values: dict[str, Any] = {}
        for line in zlib.decompress(blob).decode("utf-8").splitlines():
            item = json.loads(line)
            values.setdefault(item["field"], item["parent_value"])
            seen.setdefault(item["field"], set()).add(json.dumps(item["parent_value"], sort_keys=True))
        single &= set(seen) == set(FIELD_LIST) and all(len(v) == 1 for v in seen.values())
        lineage = [json.loads(x) for x in zlib.decompress(lineage_blob).decode("utf-8").splitlines()]
        parent[key] = {"record": rec, "values": {f: values.get(f) for f in FIELD_LIST},
                       "teams": team_sources(rec, lineage, rule)}
    conn.close()
    ctx["parent"] = parent
    report.check("parent_values_single_per_field", single)
    report.check("contract_is_the_v1_1_successor_without_numeric_identity",
                 (contract.get("schema_version"), contract.get("contract_id")) == (
                     "1.1.0", "BAT-713-NATIONAL-ARCHIVED-PUBLICATION-2019-V1.1") and
                 (contract.get("participant_mapping") or {}).get("numeric_identifier_equality") == "NEVER_AUTHORITY"
                 and bool(rule))
    ctx["participant_source_states"] = {k: p["teams"]["state"] for k, p in parent.items()}
    report.check("tranche_rows_equal_parent", all(
        (ctx["tranche"][k]["a_key"], ctx["tranche"][k]["b_key"], ctx["tranche"][k]["contest_date"],
         ctx["tranche"][k]["a_points"], ctx["tranche"][k]["b_points"]) ==
        (parent[k]["record"]["a_key"], parent[k]["record"]["b_key"], parent[k]["record"]["contest_date"],
         parent[k]["values"]["a_points"], parent[k]["values"]["b_points"]) for k in keys))
    return ctx


def verify_acquisition(contract: dict[str, Any], ctx: dict[str, Any], content: dict[str, Any],
                       report: Report) -> None:
    out = ctx["out"]
    acq_id = content["acquisition_identity"]
    path = out / "acquisition" / "sha256" / acq_id / "acquisition.json"
    data = path.read_bytes()
    acq = json.loads(data.decode("utf-8"))
    ctx.update(acquisition=acq, acquisition_id=acq_id)
    policy = h_bytes(cjson({"acquisition": contract["acquisition"],
                            "tranche_sha256": contract["scope"]["tranche_sha256"]}))
    report.check("acquisition_document_bound", h_bytes(data) == acq_id and acq["policy_id"] == policy ==
                 content["acquisition_policy_id"] and acq["tranche_sha256"] == contract["scope"]["tranche_sha256"]
                 and acq["keys"] == [k["contest_key"] for k in contract["scope"]["keys"]])
    journal = out / "acquisition" / "journal" / policy / "journal.jsonl"
    lines = [json.loads(x) for x in journal.read_text(encoding="utf-8").splitlines() if x]
    intents = [x for x in lines if x["type"] == "INTENT"]
    results = {x["seq"]: x["request"] for x in lines if x["type"] == "RESULT"}
    rebuilt = []
    for intent in intents:
        rebuilt.append(results.get(intent["seq"]) or {"seq": intent["seq"], "outcome": "INTERRUPTED_UNKNOWN"})
    finals = [x for x in lines if x["type"] == "FINALIZED"]
    report.check("journal_reproduces_requests", lines[0]["type"] == "HEADER" and
                 [r["seq"] for r in rebuilt] == list(range(1, len(rebuilt) + 1)) and
                 [cjson(r) for r in rebuilt] == [cjson(r) for r in acq["requests"]] and
                 finals and finals[-1]["acquisition_identity"] == acq_id,
                 {"intents": len(intents), "results": len(results)})
    limits = contract["acquisition"]["limits"]
    keys = {k["contest_key"]: k for k in contract["scope"]["keys"]}
    per_key_ok, host_ok, purpose_ok = True, True, True
    for key, spec in keys.items():
        mine = [r for r in acq["requests"] if r["contest_key"] == key]
        metas = [r for r in mine if r["kind"] == "METADATA"]
        reps = [r for r in mine if r["kind"] == "REPLAY"]
        if len(metas) > limits["metadata_requests_per_key"] or len(reps) > limits["replay_requests_per_key"]:
            per_key_ok = False
        if spec["selection_role"] == "SEPARATE_PREQUALIFIED_ROUTE_CONTROL" and mine:
            per_key_ok = False
        for r in metas:
            m = re.fullmatch(r"https://archive\.org/wayback/available\?url=([^&]+)&timestamp=(\d{14})", r["url"])
            from urllib.parse import unquote  # noqa: PLC0415 - standard library
            if not m or unquote(m.group(1)) != spec["candidate_url"]:
                host_ok = False
            if r["purpose"] not in ("PROBE_1", "PROBE_2", "RETRY"):
                purpose_ok = False
        for r in reps:
            split = replay_split(r["url"])
            if not split or not is_game_url(split[1], spec["game_id_literal"]):
                host_ok = False
            if r["purpose"] not in ("CAPTURE_1", "CAPTURE_2", "RETRY", "REDIRECT_HOP"):
                purpose_ok = False
    report.check("per_key_and_total_limits_held", per_key_ok and len(acq["requests"]) <= limits["total_requests"],
                 {"requests": len(acq["requests"])})
    report.check("only_granted_archive_urls_requested", host_ok)
    report.check("request_purposes_declared", purpose_ok)
    starts = [dt.datetime.strptime(r["started_utc"], "%Y-%m-%dT%H:%M:%S.%fZ") for r in acq["requests"]]
    ordered = all(b > a for a, b in zip(starts, starts[1:])) and all(
        r["ended_utc"] is None or r["ended_utc"] >= r["started_utc"] for r in acq["requests"])
    report.check("request_times_recorded_and_ordered", ordered)
    gaps = [{"from_seq": a["seq"], "to_seq": b["seq"], "gap_seconds": round((y - x).total_seconds(), 6)}
            for a, b, x, y in zip(acq["requests"], acq["requests"][1:], starts, starts[1:])]
    short = [g for g in gaps if g["gap_seconds"] < limits["min_seconds_between_request_starts"]]
    ctx["grant_conditions"] = {
        "request_start_spacing": {
            "declared_min_seconds": limits["min_seconds_between_request_starts"], "intervals": len(gaps),
            "recorded_min_gap_seconds": min((g["gap_seconds"] for g in gaps), default=None),
            "intervals_below_declared": short, "state": "DEVIATION_RECORDED" if short else "HELD",
            "basis": "gaps between the producer's recorded wall-clock started_utc values; a grant-condition "
                     "measurement reported for adjudication, not an evidence-integrity check"},
        "total_requests": {"declared_max": limits["total_requests"], "actual": len(acq["requests"]),
                           "state": "HELD" if len(acq["requests"]) <= limits["total_requests"] else "EXCEEDED"},
        "per_key_requests": {"state": "HELD" if per_key_ok else "EXCEEDED"},
        "hosts": {"state": "HELD" if host_ok else "VIOLATED"}}
    bodies_ok = True
    for r in acq["requests"]:
        if r.get("body_sha256"):
            raw = out / "raw" / "sha256" / r["body_sha256"]
            bodies_ok &= raw.is_file() and h_file(raw) == r["body_sha256"] and raw.stat().st_size == r["body_bytes"]
    report.check("every_raw_body_retained_unchanged", bodies_ok)
    ctl = acq["control"]
    report.check("control_reused_with_zero_requests", ctl["requests"] == 0 and
                 ctl["payload_sha256"] == h_bytes(ctx["control_payload"]) and
                 ctl["raw_receipt_sha256"] == h_bytes(ctx["control_receipt_raw"]) and
                 ctl["route_qualification_sha256"] == h_bytes(ctx["control_route_raw"]) and
                 all((out / "raw" / "sha256" / s).is_file() for s in (ctl["payload_sha256"], ctl["raw_receipt_sha256"],
                                                                     ctl["route_qualification_sha256"])))


def read_delivered(manifest: Path, ctx: dict[str, Any], report: Report) -> dict[str, Any]:
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    content = doc["identity_document"]
    identity = h_bytes(cjson(content))
    report.check("content_identity_recomputes", identity == doc["identity"] == manifest.parent.name)
    data_dir = ctx["out"] / "sha256" / identity
    payloads = {}
    for name in PAYLOAD_NAMES:
        packed = (data_dir / f"{name}.gz").read_bytes()
        raw = gzip.decompress(packed)
        report.check(f"payload_{name}_hashes", h_bytes(packed) == content["outputs"][f"{name}.gz"] and
                     h_bytes(raw) == content["semantic_outputs"][name] and
                     raw.count(b"\n") == content["row_counts"][name])
        payloads[name] = raw
    db_manifest_path = Path(str(manifest.parent.parent)) / doc["provenance"]["database_identity"] / "run_manifest.json"
    db_doc = json.loads(db_manifest_path.read_text(encoding="utf-8"))
    db_ident = db_doc["identity_document"]
    db_path = ctx["out"] / "sha256" / db_doc["identity"] / "national_archived_publication.sqlite"
    report.check("database_identity_recomputes", h_bytes(cjson(db_ident)) == db_doc["identity"] and
                 db_ident["content_identity"] == identity and h_file(db_path) == db_ident["outputs"][
                     "national_archived_publication.sqlite"] and db_ident["parent"] == content["parent"])
    conn = sqlite3.connect("file:" + str(db_path.resolve()).replace("\\", "/") + "?mode=ro", uri=True)
    db_rows = {}
    for table, name in (("dispositions", "dispositions.jsonl"), ("requests", "requests.jsonl"),
                        ("captures", "captures.jsonl"), ("assertions", "assertions.jsonl")):
        db_rows[name] = b"".join(r[0].encode("utf-8") + b"\n" for r in conn.execute(
            f"SELECT record FROM {table} ORDER BY ord"))
    meta = dict(conn.execute("SELECT key, value FROM meta"))
    conn.close()
    report.check("database_rows_equal_payload_lines", all(db_rows[n] == payloads[n] for n in PAYLOAD_NAMES))
    report.check("database_meta_binds_content", meta.get("content_identity") == identity and
                 meta.get("acquisition_identity") == content["acquisition_identity"] and
                 json.loads(meta.get("parent")) == content["parent"])
    return {"content": content, "content_identity": identity, "payloads": payloads, "database": db_path,
            "database_identity": db_doc["identity"], "records": {n: [json.loads(x) for x in payloads[n].splitlines()]
                                                                  for n in PAYLOAD_NAMES}}


def compare(expected: Expected, delivered: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    out = {}
    for name in PAYLOAD_NAMES:
        exp, got = expected.records[name], delivered[name]
        mismatches = []
        for i in range(max(len(exp), len(got))):
            a = exp[i] if i < len(exp) else None
            b = got[i] if i < len(got) else None
            if cjson(a) != cjson(b):
                keys = sorted(set(a or {}) | set(b or {}))
                mismatches.append({"index": i, "fields": [k for k in keys if cjson((a or {}).get(k)) !=
                                                          cjson((b or {}).get(k))][:12]})
        out[name] = {"expected": len(exp), "delivered": len(got), "mismatches": len(mismatches),
                     "first": mismatches[:5]}
    return out


def clean(result: dict[str, Any]) -> bool:
    return all(v["mismatches"] == 0 and v["expected"] == v["delivered"] for v in result.values())


# --------------------------------------------------------------------------------------------- decisions

def my_cutoff(text: str) -> dt.datetime:
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})", text)
    zone = m.group(8)
    off = dt.timedelta(0) if zone == "Z" else (1 if zone[0] == "+" else -1) * dt.timedelta(
        hours=int(zone[1:3]), minutes=int(zone[4:6]))
    micro = int((m.group(7) or ".0")[1:].ljust(6, "0"))
    return dt.datetime(*(int(m.group(i)) for i in range(1, 7)), micro, tzinfo=dt.timezone(off)).astimezone(UTCZ)


def my_archive_state(captures: list[dict[str, Any]], key: str, field: str, date: str, cut: dt.datetime) -> str:
    states = []
    for cap in captures:
        if cap["contest_key"] != key or cap["state"] != "QUALIFIED" or cap["field_states"][field] != QUAL:
            continue
        bound = dt.datetime.strptime(cap["clocks"]["archive_capture"]["latest_utc"],
                                     "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTCZ)
        if bound <= cut:
            states.append("TRUE")
        elif field in OUTCOME and cut < earliest_instant(date):
            states.append("FALSE")
        else:
            states.append("UNKNOWN")
    if not states:
        return "NO_QUALIFIED_ARCHIVE_ASSERTION"
    if "TRUE" in states:
        return "TRUE"
    return "FALSE" if all(s == "FALSE" for s in states) else "UNKNOWN"


def my_compose(original: str, archive: str) -> str:
    if "TRUE" in (original, archive):
        return "TRUE"
    if original == "FALSE" and archive in ("FALSE", "NO_QUALIFIED_ARCHIVE_ASSERTION"):
        return "FALSE"
    if original == "NO_CORROBORATING_ASSERTION" and archive == "FALSE":
        return "FALSE"
    if original == "NO_CORROBORATING_ASSERTION" and archive == "NO_QUALIFIED_ARCHIVE_ASSERTION":
        return original
    return "UNKNOWN"


def run_query(argv: list[str]) -> tuple[int, Any, str]:
    proc = subprocess.run([sys.executable, "-B", "-m", "aggie_analytics.national_source_time.query", *argv],
                          capture_output=True, text=True, encoding="utf-8", check=False)
    return proc.returncode, (json.loads(proc.stdout) if proc.stdout.strip() else None), proc.stderr


def decision_checks(args: argparse.Namespace, delivered: dict[str, Any], expected: Expected,
                    report: Report) -> dict[str, Any]:
    sidecar = str(delivered["database"])
    caps = expected.records["captures.jsonl"]
    disagreements, compared = [], 0
    season = expected.contract["scope"]["season"]
    for cutoff in PROBE_CUTOFFS:
        cut = my_cutoff(cutoff)
        code, doc, err = run_query(["--database", str(args.source_database), "--archive-evidence", sidecar,
                                    "--grain", "contest", "--season", str(season), "--cutoff", cutoff, "--all"])
        if code != 0:
            disagreements.append({"cutoff": cutoff, "error": err[-300:]})
            continue
        rows = {r["contest"]["contest_key"]: r for r in doc["rows"]}
        outside = [r for k, r in rows.items() if k not in expected.ctx["parent"]]
        if any(r["archive_disposition"] != "NOT_IN_ARCHIVE_TRANCHE" or any(
                v["archive"]["in_archive_tranche"] or v["historically_published_by_cutoff_with_archive"] !=
                v["historically_published_by_cutoff"] for v in r["fields"].values()) for r in outside):
            disagreements.append({"cutoff": cutoff, "error": "a contest outside the tranche changed"})
        for spec in expected.contract["scope"]["keys"]:
            key = spec["contest_key"]
            row = rows.get(key)
            if row is None:
                disagreements.append({"cutoff": cutoff, "key": key, "error": "missing from the consumer page"})
                continue
            date = expected.ctx["parent"][key]["record"]["contest_date"]
            for field in FIELD_LIST:
                compared += 1
                mine = my_archive_state(caps, key, field, date, cut)
                theirs = row["fields"][field]
                composed = my_compose(theirs["historically_published_by_cutoff"], mine)
                if theirs["archive"]["historically_published_by_cutoff"] != mine or \
                        theirs["historically_published_by_cutoff_with_archive"] != composed or \
                        row["pit_admission"]["state"] != "NOT_ADMITTED":
                    disagreements.append({"cutoff": cutoff, "key": key, "field": field, "mine": mine,
                                          "consumer": theirs["archive"]["historically_published_by_cutoff"]})
    code, doc, err = run_query(["--database", str(args.source_database), "--archive-evidence", sidecar, "--grain",
                                "archive-assertion", "--cutoff", "2019-09-02T01:00:50.999999Z", "--all"])
    assertion_ok = code == 0 and doc["total"] == len(expected.records["assertions.jsonl"]) and all(
        r["decision"]["pit_admission"]["state"] == "NOT_ADMITTED" for r in doc["rows"])
    code2, _doc2, err2 = run_query(["--database", str(args.source_database), "--archive-evidence", sidecar, "--grain",
                                    "contest", "--contest", expected.contract["scope"]["control_contest_key"],
                                    "--cutoff", "2026-10-02T00:00:00Z", "--require-pit"])
    report.check("consumer_decisions_agree_with_independent_rules", not disagreements and compared > 0,
                 {"compared_field_decisions": compared, "disagreements": disagreements[:10]})
    report.check("consumer_archive_assertion_grain_complete", assertion_ok, err[-300:] if not assertion_ok else None)
    report.check("consumer_refuses_require_pit_with_archive", code2 == 2 and "PIT_ADMISSION_AUTHORITY_ABSENT" in err2)
    return {"probe_cutoffs": PROBE_CUTOFFS, "compared_field_decisions": compared,
            "disagreements": len(disagreements)}


# --------------------------------------------------------------------------------------------- tamper and challenges

def tamper_cases(expected: Expected, delivered: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Coordinated semantic tampers of the delivered records (as if every outer hash were consistently recomputed);
    each must be rejected by the field-by-field comparison with the independent reconstruction."""
    out = []

    def run(name: str, mutate) -> None:
        copy_ = copy.deepcopy(delivered)
        applied = bool(mutate(copy_))
        out.append({"case": name, "applied": applied,
                    "rejected": (not clean(compare(expected, copy_))) if applied else None})

    def first(name: str, pred):
        def pick(d):
            for item in d[name]:
                if pred(item):
                    return item
            return None
        return pick

    def edit(name: str, pred, change):
        def mutate(d):
            item = first(name, pred)(d)
            if item is None:
                return False
            change(item)
            return True
        return mutate
    qualified = lambda c: c["state"] == "QUALIFIED"  # noqa: E731
    run("bound_backdated_to_probe_instant", edit("captures.jsonl", qualified, lambda c: c["clocks"]["archive_capture"]
                                                 .update(latest_utc="2019-01-01T00:00:00.999999Z")))
    run("first_publication_claimed", edit("captures.jsonl", qualified, lambda c: c["clocks"]["archive_capture"]
                                          .update(earliest_utc=c["clocks"]["archive_capture"]["latest_utc"])))
    run("points_swapped_between_participants", edit("assertions.jsonl", lambda a: a["field"] == "a_points",
                                                    lambda a: a.update(field="b_points")))
    run("score_value_changed", edit("assertions.jsonl", lambda a: a["field"] == "b_points",
                                    lambda a: a.update(value=a["value"] + 1, literal=str(a["value"] + 1))))
    run("witness_span_moved_to_scoreboard", edit("assertions.jsonl", lambda a: a["witness"] == "HOME_SCORE",
                                                 lambda a: a.update(witness_span=[0, 2])))
    run("quarantined_capture_promoted", edit("captures.jsonl", lambda c: c["state"] == "QUARANTINED",
                                             lambda c: c.update(state="QUALIFIED", quarantine_reasons=[])))
    run("season_fabricated", edit("captures.jsonl", qualified, lambda c: c["field_states"].update(season=QUAL)))
    run("unsupported_field_promoted", edit("captures.jsonl", lambda c: any(
        s != QUAL for f, s in c["field_states"].items() if f != "season"), lambda c: c["field_states"].update(
        {f: QUAL for f, s in c["field_states"].items() if s != QUAL and f != "season"})))
    run("orientation_flipped", edit("captures.jsonl", lambda c: c["orientation"]["a_side"],
                                    lambda c: c["orientation"].update(a_side=c["orientation"]["b_side"],
                                                                      b_side=c["orientation"]["a_side"])))
    run("missing_key_disposition_dropped", lambda d: bool(d["dispositions.jsonl"]) and
        d["dispositions.jsonl"].pop() is not None)
    run("disposition_overstated", edit("dispositions.jsonl", lambda x: x["disposition"] in (
        "NO_ARCHIVE_CAPTURE_REPORTED", "ARCHIVED_VERSION_QUALIFIED_PARTIAL_FIELDS", "REDIRECT_REFUSED",
        "METADATA_REQUEST_FAILED", "REPLAY_REQUEST_FAILED"),
        lambda x: x.update(disposition="ARCHIVED_VERSION_QUALIFIED_ALL_WITNESSABLE_FIELDS")))
    run("hidden_retry_removed", edit("requests.jsonl", lambda r: True, lambda r: r.update(purpose="PROBE_2")))
    run("out_of_tranche_capture_injected", lambda d: bool(d["captures.jsonl"]) and d["captures.jsonl"].append(
        dict(copy.deepcopy(d["captures.jsonl"][0]), contest_key="ncaa:0", capture_id="wayback:x")) is None)
    run("duplicate_assertion_added", lambda d: bool(d["assertions.jsonl"]) and d["assertions.jsonl"].append(
        copy.deepcopy(d["assertions.jsonl"][0])) is None)
    run("retrieval_clock_relabelled_historical", edit("captures.jsonl", qualified, lambda c: c["clocks"]["retrieval"]
                                                      .update(latest_utc="2019-09-02T01:00:50.000000Z")))
    run("parent_value_copied_into_unwitnessed_field", lambda d: bool(d["assertions.jsonl"]) and
        d["assertions.jsonl"].append(dict(copy.deepcopy(d["assertions.jsonl"][0]), field="season",
                                          value=2019, field_state=QUAL)) is None)

    def borrowed(d: dict[str, list[dict[str, Any]]]) -> bool:
        """MF41A01-01 class: a pregame version promoted with 'post', 'Final' and score digits borrowed from
        unrelated substrings of the same raw page."""
        literals = (("completion", "JS_STATUS", "post"), ("completion", "STATUS_DETAIL", "Final"),
                    ("a_points", "AWAY_SCORE", "2"), ("b_points", "HOME_SCORE", "3"))
        for cap in d["captures.jsonl"]:
            if cap["state"] != "QUALIFIED" or cap["page_status"]["js_status"] != "pre":
                continue
            raw = expected.raw(cap["payload_sha256"])
            starts = [raw.find(literal.encode("utf-8")) for _f, _w, literal in literals]
            if min(starts) < 0:
                continue
            template = next(a for a in d["assertions.jsonl"] if a["capture_id"] == cap["capture_id"])
            for (field, witness, literal), start in zip(literals, starts):
                d["assertions.jsonl"].append(dict(copy.deepcopy(template), field=field, witness=witness,
                                                  literal=literal, witness_span=[start, start + len(literal)],
                                                  field_state=QUAL, corroboration="AGREES_WITH_PARENT",
                                                  field_role="OUTCOME"))
                cap["field_states"][field] = QUAL
            return True
        return False
    run("pregame_promoted_with_borrowed_substrings", borrowed)

    def adjacent(d: dict[str, list[dict[str, Any]]]) -> bool:
        """MF41A01-01 class: a score span moved to the same digits elsewhere inside the genuine main element."""
        for a in d["assertions.jsonl"]:
            if a["field"] not in ("a_points", "b_points") or a["field_state"] != QUAL:
                continue
            cap = next(c for c in d["captures.jsonl"] if c["capture_id"] == a["capture_id"])
            raw = expected.raw(cap["payload_sha256"])
            nav = next(s["span"] for s in cap["main_element_spans"] if s["kind"] == "NAV")
            pos = raw.find(a["literal"].encode("utf-8"), nav[0])
            while 0 <= pos < nav[1]:
                if pos != a["witness_span"][0]:
                    a["witness_span"] = [pos, pos + len(a["literal"])]
                    return True
                pos = raw.find(a["literal"].encode("utf-8"), pos + 1)
        return False
    run("score_span_moved_to_same_digits_in_the_main_element", adjacent)
    run("participant_mapping_name_replaced", edit("captures.jsonl", lambda c: (c.get("participant_mapping") or {})
                                                  .get("state") == "QUALIFIED", lambda c: c["participant_mapping"]
                                                  ["sides"]["home"].update(espn_location_name="Unrelated College")))
    run("participant_mapping_claimed_without_evidence", edit(
        "captures.jsonl", lambda c: c["field_states"]["a_participant"] == QUAL,
        lambda c: c.update(participant_mapping=dict(c["participant_mapping"], state="UNRESOLVED",
                                                    reason="HOME_TEAM_NAME_NOT_DOCUMENTED_FOR_EITHER_PARENT_TEAM"))))
    run("required_status_detail_row_omitted", lambda d: any(
        d["assertions.jsonl"].remove(a) is None for a in [next((x for x in d["assertions.jsonl"]
                                                               if x["witness"] == "STATUS_DETAIL"
                                                               and x["field_state"] == QUAL), None)] if a))
    run("team_name_witness_row_omitted", lambda d: any(
        d["assertions.jsonl"].remove(a) is None for a in [next((x for x in d["assertions.jsonl"]
                                                               if x["witness"].endswith("_TEAM_NAME")), None)] if a))
    return out


def challenges(expected: Expected, delivered: dict[str, list[dict[str, Any]]], ctx: dict[str, Any]) -> list[dict]:
    caps = delivered["captures.jsonl"]
    asr = delivered["assertions.jsonl"]
    out = []
    route = ctx["control_route"]
    control = [c for c in caps if c["origin"] == "MANAGER_RETAINED_CONTROL_REPLAY"]
    out.append({"challenge": "control_bound_equals_manager_route_qualification", "as_expected": bool(control) and
                control[0]["clocks"]["archive_capture"]["latest_utc"] == route["conservative_upper_bound"] and
                control[0]["state"] == "QUALIFIED"})
    out.append({"challenge": "no_bound_precedes_its_own_memento", "as_expected": all(
        gmt(c["memento_datetime_literal"]) is None or c["clocks"]["archive_capture"]["latest_utc"] is None or
        dt.datetime.strptime(c["clocks"]["archive_capture"]["latest_utc"], "%Y-%m-%dT%H:%M:%S.%fZ")
        .replace(tzinfo=UTCZ) >= gmt(c["memento_datetime_literal"]) for c in caps)})
    out.append({"challenge": "no_first_publication_instant_claimed", "as_expected": all(
        c["clocks"]["archive_capture"]["earliest_utc"] is None for c in caps)})
    out.append({"challenge": "quarantined_captures_qualify_no_field", "as_expected": all(
        QUAL not in c["field_states"].values() for c in caps if c["state"] != "QUALIFIED")})
    out.append({"challenge": "season_never_qualified", "as_expected": all(
        c["field_states"]["season"] != QUAL for c in caps) and not any(a["field"] == "season" for a in asr)})
    payload_cache: dict[str, bytes] = {}

    def payload(c: dict[str, Any]) -> bytes:
        if c["capture_id"] not in payload_cache:
            payload_cache[c["capture_id"]] = (ctx["out"] / "raw" / "sha256" / c["payload_sha256"]).read_bytes()
        return payload_cache[c["capture_id"]]
    by_id = {c["capture_id"]: c for c in caps}
    out.append({"challenge": "every_witness_inside_the_main_game_element", "as_expected": all(
        any(s["span"][0] <= a["witness_span"][0] and a["witness_span"][1] <= s["span"][1]
            for s in by_id[a["capture_id"]]["main_element_spans"]) for a in asr)})
    out.append({"challenge": "witness_literals_reread_from_raw", "as_expected": all(
        payload(by_id[a["capture_id"]])[a["witness_span"][0]:a["witness_span"][1]] == a["literal"].encode("utf-8")
        for a in asr)})
    def rests_on_names(c: dict[str, Any]) -> bool:
        mapping = c["participant_mapping"]
        teams = ctx["parent"][c["contest_key"]]["teams"]["sides"]
        return all(side["espn_location_name"] in {d["name"] for d in teams[side["parent_side"]]["documented_names"]}
                   and teams[side["parent_side"]]["cfbd_role"] == side["page_side"]
                   for side in mapping["sides"].values()) and c["field_states"]["contest_date"] == QUAL
    mapped = [c for c in caps if c["participant_mapping"]["state"] == "QUALIFIED"]
    out.append({"challenge": "participant_maps_rest_on_documented_names_roles_and_dates_not_numbers",
                "as_expected": all(rests_on_names(c) for c in mapped),
                "detail": {"qualified_maps": len(mapped), "differing_id_sides": sum(
                    1 for c in mapped for s in c["participant_mapping"]["sides"].values()
                    if s["id_relation"] == "ESPN_ID_DIFFERS_FROM_CFBD_ID")}})
    out.extend(page_challenges(expected, caps, payload))
    probes = {s["contest_key"]: s["probe_1_timestamp"] for s in expected.contract["scope"]["keys"]}
    out.append({"challenge": "probe_timestamps_never_used_as_bounds", "as_expected": all(
        c["wayback_timestamp"] != probes[c["contest_key"]] or c["memento_datetime_literal"] is not None for c in caps)})
    out.append({"challenge": "every_key_has_exactly_one_disposition", "as_expected": sorted(
        d["contest_key"] for d in delivered["dispositions.jsonl"]) == sorted(probes)})
    return out


def page_challenges(expected: Expected, caps: list[dict[str, Any]], payload) -> list[dict[str, Any]]:
    """Self-challenges on in-memory copies of the retained pages: this tool's own reconstruction must refuse the
    manager's failure classes (MF41A01-01 borrowed or same-element field literals, MF41A01-02 numeric identity)."""
    out: list[dict[str, Any]] = []
    specs = {s["contest_key"]: s for s in expected.contract["scope"]["keys"]}

    def version_of(cap: dict[str, Any]) -> dict[str, Any]:
        return next(v for v in expected.versions(cap["contest_key"], specs[cap["contest_key"]])
                    if h_bytes(v["payload"]) == cap["payload_sha256"])
    pre = [c for c in caps if c["state"] == "QUALIFIED" and c["page_status"]["js_status"] == "pre"]
    bites = 0
    ok = True
    for c in pre:
        scan = scan_page(payload(c))
        status = [payload(c)[w[1]:w[2]] for w in scan["witnesses"] if w[0] == "JS_STATUS"]
        details = [payload(c)[w[1]:w[2]] for w in scan["witnesses"] if w[0] == "STATUS_DETAIL"]
        names = [w[0] for w in scan["witnesses"]]
        ok &= status == [b"pre"] and not any(re.fullmatch(rb"Final(/\d*OT)?", d) for d in details) \
            and "HOME_SCORE" not in names and "AWAY_SCORE" not in names
        bites += int(b"post" in payload(c) and b"Final" in payload(c))
    out.append({"challenge": "pregame_versions_yield_no_borrowed_status_or_scores", "as_expected": ok,
                "detail": {"pregame_captures": len(pre), "pages_containing_post_and_Final_elsewhere": bites}})
    final = [c for c in caps if c["state"] == "QUALIFIED" and c["page_status"]["final"]]
    ok, extra = True, 0
    for c in final:
        scan = scan_page(payload(c))
        nav = next(s["span"] for s in c["main_element_spans"] if s["kind"] == "NAV")
        for side in ("HOME", "AWAY"):
            hits = [w for w in scan["witnesses"] if w[0] == f"{side}_SCORE"]
            ok &= len(hits) == 1
            if hits:
                literal = payload(c)[hits[0][1]:hits[0][2]]
                extra += max(payload(c)[nav[0]:nav[1]].count(literal) - 1, 0)
    out.append({"challenge": "each_score_is_exactly_one_score_element_not_any_equal_digits", "as_expected": ok,
                "detail": {"final_captures": len(final), "other_equal_digit_runs_inside_the_main_element": extra}})
    mapped = [c for c in caps if c["participant_mapping"]["state"] == "QUALIFIED" and c["state"] == "QUALIFIED"]
    ok_unrelated, ok_swapped = True, True
    for c in mapped:
        data = payload(c)
        unrelated = re.sub(rb'(<span class="long-name">)[^<]+', rb"\1Unrelated College", data)
        capture, _rows = expected.capture(c["contest_key"], specs[c["contest_key"]], version_of(c), unrelated)
        ok_unrelated &= capture["participant_mapping"]["state"] == "UNRESOLVED" and \
            capture["field_states"]["a_participant"] == "PARTICIPANT_MAPPING_UNRESOLVED" and \
            capture["field_states"]["a_points"] in ("ORIENTATION_UNRESOLVED", "NOT_SUPPORTED_BY_VERSION_STATUS",
                                                    "NOT_WITNESSED_IN_VERSION")
        home = c["page_participants"]["home"]["espn_location_name"]
        away = c["page_participants"]["away"]["espn_location_name"]
        marker = b"\x00SWAP\x00"
        swapped = data.replace(b'class="long-name">' + home.encode("utf-8") + b"<", marker) \
            .replace(b'class="long-name">' + away.encode("utf-8") + b"<",
                     b'class="long-name">' + home.encode("utf-8") + b"<") \
            .replace(marker, b'class="long-name">' + away.encode("utf-8") + b"<")
        capture, _rows = expected.capture(c["contest_key"], specs[c["contest_key"]], version_of(c), swapped)
        ok_swapped &= swapped != data and capture["participant_mapping"]["state"] == "UNRESOLVED" and \
            capture["field_states"]["b_participant"] == "PARTICIPANT_MAPPING_UNRESOLVED"
    out.append({"challenge": "unrelated_team_names_with_equal_numeric_ids_never_join", "as_expected": ok_unrelated,
                "detail": {"captures": len(mapped)}})
    out.append({"challenge": "swapped_team_names_never_join", "as_expected": ok_swapped,
                "detail": {"captures": len(mapped)}})
    ok_dup, tried = True, 0
    for c in final:
        data = payload(c)
        line = re.search(rb'\n([ \t]*espn\.gamepackage\.status[ \t]*=[ \t]*"post"[ \t]*;)', data)
        if not line:
            continue
        tried += 1
        doubled = data[:line.end()] + b"\n" + line.group(1) + data[line.end():]
        capture, _rows = expected.capture(c["contest_key"], specs[c["contest_key"]], version_of(c), doubled)
        ok_dup &= capture["field_states"]["completion"] == "DUPLICATED_WITNESS" and \
            capture["field_states"]["a_points"] != QUAL
    out.append({"challenge": "duplicated_status_assignment_never_qualifies", "as_expected": ok_dup and tried > 0,
                "detail": {"captures": tried}})
    ok_attr, tried = True, 0
    for c in mapped:
        data = payload(c)
        nav = next(s["span"] for s in c["main_element_spans"] if s["kind"] == "NAV")
        pos = data.find(b'class="team-name"', nav[0], nav[1])
        if pos < 0:
            continue
        tried += 1
        hidden = data[:pos] + b"title=' href=\"/college-football/team/_/id/1\"' " + data[pos:]
        scan = scan_page(hidden)
        before = sorted(normalize(w[0], payload(c)[w[1]:w[2]].decode("utf-8"))
                        for w in scan_page(payload(c))["witnesses"] if w[0].endswith("_TEAM_HREF"))
        after = sorted(normalize(w[0], hidden[w[1]:w[2]].decode("utf-8"))
                       for w in scan["witnesses"] if w[0].endswith("_TEAM_HREF"))
        ok_attr &= before == after and "1" not in after
    out.append({"challenge": "href_text_inside_another_attribute_is_not_a_witness", "as_expected": ok_attr and tried > 0,
                "detail": {"captures": tried}})
    return out


def strata(delivered: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    out: dict[str, dict[str, int]] = {}
    for d in delivered["dispositions.jsonl"]:
        out.setdefault(d["stratum"], {})
        out[d["stratum"]][d["disposition"]] = out[d["stratum"]].get(d["disposition"], 0) + 1
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("contract", "source-database", "source-bindings", "tranche", "manifest", "report"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--skip-consumer", action="store_true", help="test hook: no consumer subprocess")
    args = parser.parse_args(argv)
    if args.report.exists():
        raise SystemExit("the report path already exists (written once)")
    report = Report()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    ctx = verify_inputs(contract, args, report)
    manifest = Path(args.manifest)
    ctx["out"] = manifest.parent.parent.parent.parent.parent / "canonical" / manifest.parent.parent.parent.name
    content_doc = json.loads(manifest.read_text(encoding="utf-8"))["identity_document"]
    verify_acquisition(contract, ctx, content_doc, report)
    delivered = read_delivered(manifest, ctx, report)
    report.check("content_binds_contract_parent_tranche", delivered["content"]["contract_sha256"] == h_bytes(
        args.contract.read_bytes()) and delivered["content"]["parent"] == ctx["parent_binding"] and
        delivered["content"]["tranche_sha256"] == contract["scope"]["tranche_sha256"])
    expected = Expected(contract, ctx)
    expected.build()
    result = compare(expected, delivered["records"])
    report.check("every_record_reconstructed_independently", clean(result), result)
    report.check("reconstructed_payloads_hash_to_delivered_semantics", all(
        h_bytes(lines_of(expected.records[n])) == delivered["content"]["semantic_outputs"][n] for n in PAYLOAD_NAMES))
    decisions = {"skipped": True} if args.skip_consumer else decision_checks(args, delivered, expected, report)
    tampers = tamper_cases(expected, delivered["records"])
    applied = [t for t in tampers if t["applied"]]
    report.check("every_tamper_case_rejected", len(applied) >= 10 and all(t["rejected"] for t in applied),
                 {"applied": len(applied), "not_applicable": [t["case"] for t in tampers if not t["applied"]],
                  "not_rejected": [t["case"] for t in applied if not t["rejected"]]})
    oracle = challenges(expected, delivered["records"], ctx)
    report.check("oracle_self_challenges_as_expected", all(c["as_expected"] for c in oracle),
                 [c["challenge"] for c in oracle if not c["as_expected"]])
    tally: dict[str, int] = {}
    for d in delivered["records"]["dispositions.jsonl"]:
        tally[d["disposition"]] = tally.get(d["disposition"], 0) + 1
    fields = {f: sum(1 for d in delivered["records"]["dispositions.jsonl"] if d["field_support"][f])
              for f in SUPPORTABLE}
    failed = report.failed()
    doc = {"tool": "tools/validate_national_archived_publication.py", "tool_sha256": h_file(Path(__file__)),
           "result": "PASS" if not failed else "FAIL", "failed_checks": failed, "checks": report.checks,
           "content_identity": delivered["content_identity"], "database_identity": delivered["database_identity"],
           "acquisition_identity": ctx["acquisition_id"],
           "counts": {"tranche_keys": len(contract["scope"]["keys"]), "dispositions": tally,
                      "requests": len(ctx["acquisition"]["requests"]),
                      "captures": len(delivered["records"]["captures.jsonl"]),
                      "qualified_captures": sum(1 for c in delivered["records"]["captures.jsonl"]
                                                if c["state"] == "QUALIFIED"),
                      "assertions": len(delivered["records"]["assertions.jsonl"]),
                      "keys_with_field_support": fields, "strata": strata(delivered["records"]),
                      "participant_maps": {
                          "qualified": sum(1 for c in delivered["records"]["captures.jsonl"]
                                           if c["participant_mapping"]["state"] == "QUALIFIED"),
                          "unresolved": sorted({c["participant_mapping"]["reason"]
                                                for c in delivered["records"]["captures.jsonl"]
                                                if c["participant_mapping"]["state"] != "QUALIFIED"}),
                          "name_sources": sorted({tuple(s["name_sources"])
                                                  for c in delivered["records"]["captures.jsonl"]
                                                  for s in c["participant_mapping"]["sides"].values()}),
                          "differing_id_sides": sum(1 for c in delivered["records"]["captures.jsonl"]
                                                    for s in c["participant_mapping"]["sides"].values()
                                                    if s["id_relation"] == "ESPN_ID_DIFFERS_FROM_CFBD_ID"),
                          "source_states": ctx.get("participant_source_states")}},
           "grant_conditions": ctx.get("grant_conditions"), "decisions": decisions, "tamper_cases": tampers,
           "oracle_challenges": oracle,
           "independence": "standard library only; no producer, query or project import; the consumer is exercised "
                           "only as a subprocess and compared with this tool's own decisions",
           "limits": ["a bounded 28-key 2019 tranche, not a national or seasonal audit",
                      "archive captures are upper bounds for the exact witnessed versions, never first publication",
                      "capture times are the archive's receipts; this offline tool cannot re-query the archive",
                      "a coordinated forgery that rewrites raw bytes, receipts and every hash is detectable only "
                      "against the committed gate identities and the manager's independent control receipt"],
           "observed_at": dt.datetime.now(UTCZ).isoformat()}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"result": doc["result"], "failed_checks": failed, "counts": doc["counts"]}, indent=1))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

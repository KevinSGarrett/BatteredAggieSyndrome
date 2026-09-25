"""Players on an official football roster page, as the page states them (R37-11).

Roster presence is identity evidence, never availability: a roster says who
is on a team in a season, not whether anyone plays on a given day. This
module reads three page shapes the cached SEC rosters use, in a declared
order, and reports which one it used:

* ``NUXT_PAYLOAD`` -- the page embeds its state as a flattened, index-linked
  JSON array (``__NUXT_DATA__``). It is decoded exactly and every record
  carrying a first name, last name and jersey field is a player.
* ``ROSTER_ITEM_CARDS`` -- player cards with their own number and name
  elements, taken only from the players section (before the staff heading).
* ``ROSTER_TABLE`` -- a table whose header names a number column and a name
  column.

The season is the one the page's own roster heading, selected season or
roster container class states; a page that states none has no season, and
the caller decides what that means.
"""

from __future__ import annotations

import html as html_lib
import json
import re
import sys
from typing import Any

ROSTER_VERSION = "BAS-OFFICIAL-ROSTER-v37.2"

_NUXT = re.compile(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', re.S | re.I)
_TAG = re.compile(r"<[^>]+>")
_SEASON_TEXT = re.compile(r"\b(20\d{2})(?:\s*[-–]\s*\d{2})?\s+(?:[A-Z][\w'’.-]*\s+){0,2}?football\s+roster\b"
                          r"|football\s+(20\d{2})\s+roster\b|football\s+roster\s+(20\d{2})\b", re.I)
_SELECTED_SEASON = re.compile(r'season=(20\d{2})(?:-\d{2})?"\s+selected', re.I)
#: The roster container's own season class ("roster-sport-football roster-season-2026").
_SEASON_CLASS = re.compile(r'class="[^"]*\broster-sport-football\b[^"]*\broster-season-(20\d{2})\b', re.I)
_SPECIAL = {"Reactive", "ShallowReactive", "Ref", "ShallowRef", "EmptyRef", "EmptyShallowRef", "NuxtError"}


def plain(fragment: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(_TAG.sub(" ", fragment))).strip()


def decode_devalue(data: list[Any]) -> Any:
    """Resolve a devalue-style flattened array (``__NUXT_DATA__``) into values."""

    memo: dict[int, Any] = {}
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 20000))

    def get(index: Any) -> Any:
        if not isinstance(index, int) or isinstance(index, bool):
            return index
        if index < 0:
            return None  # undefined, hole, NaN, infinities and -0 carry no roster fact
        if index in memo:
            return memo[index]
        value = data[index]
        if isinstance(value, list):
            if value and isinstance(value[0], str) and value[0] in _SPECIAL:
                memo[index] = None
                memo[index] = get(value[1]) if len(value) > 1 else None
                return memo[index]
            if value and isinstance(value[0], str) and value[0] in ("Set", "Map", "Date", "RegExp", "BigInt", "null"):
                memo[index] = [get(item) for item in value[1:]] if value[0] in ("Set", "Map") else value[1:]
                return memo[index]
            out: list[Any] = []
            memo[index] = out
            out.extend(get(item) for item in value)
            return out
        if isinstance(value, dict):
            out_dict: dict[str, Any] = {}
            memo[index] = out_dict
            for key, item in value.items():
                out_dict[key] = get(item)
            return out_dict
        memo[index] = value
        return value

    return get(0)


def _walk(value: Any, seen: set[int]) -> Any:
    if id(value) in seen:
        return
    if isinstance(value, dict):
        seen.add(id(value))
        yield value
        for item in value.values():
            yield from _walk(item, seen)
    elif isinstance(value, list):
        seen.add(id(value))
        for item in value:
            yield from _walk(item, seen)


def _text(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("abbreviation", "short", "name", "title"):
            if value.get(key):
                return str(value[key])
        return None
    return None if value is None else str(value)


def _nuxt_players(page: str) -> list[dict[str, Any]]:
    match = _NUXT.search(page)
    if not match:
        return []
    try:
        decoded = decode_devalue(json.loads(match.group(1)))
    except (ValueError, IndexError, RecursionError):
        return []
    entries, flat = [], []
    for record in _walk(decoded, set()):
        # A season's roster entry holds this roster's number and wraps the
        # person ({"roster_id": 21, "jersey_number": 2, "player": {...}}). The
        # person record's own number is not this roster's: it can be empty or
        # another season's. When roster entries exist, only they are read.
        wrapped = isinstance(record.get("player"), dict)
        person = record["player"] if wrapped else record
        first = person.get("firstName", person.get("first_name"))
        last = person.get("lastName", person.get("last_name"))
        if not (isinstance(first, str) and isinstance(last, str)):
            continue
        if not any(key in record for key in ("jerseyNumber", "jersey_number")):
            continue
        jersey = record.get("jerseyNumber", record.get("jersey_number"))
        position = (record.get("positionShort") or record.get("player_position") or record.get("position")
                    or person.get("positionShort") or person.get("player_position") or person.get("position"))
        (entries if wrapped else flat).append({
            "first_name": first.strip(), "last_name": last.strip(), "name": f"{first.strip()} {last.strip()}".strip(),
            "jersey": None if jersey in (None, "") else str(jersey).strip(), "position": _text(position),
            "roster_id": record.get("roster_id") if wrapped else None})
    if entries:
        rosters = {entry["roster_id"] for entry in entries}
        if len(rosters) > 1:
            return []  # entries of several rosters and no way here to tell which is the page's own season
        return entries
    return flat


def _card_players(page: str) -> list[dict[str, Any]]:
    stop = len(page)
    staff = re.search(r"<h2[^>]*>\s*[^<]*\bStaff\b[^<]*</h2>", page, re.I)
    if staff:
        stop = staff.start()
    players = []
    for match in re.finditer(r'<span class="roster-item__number">\s*([^<]*?)\s*</span>\s*'
                             r'<h3 class="roster-item__name">(.*?)</h3>', page[:stop], re.S):
        name = plain(match.group(2))
        players.append({"name": name, "first_name": None, "last_name": None,
                        "jersey": plain(match.group(1)) or None, "position": None})
    return players


def _table_players(page: str) -> list[dict[str, Any]]:
    players = []
    for table in re.finditer(r"<table\b.*?</table>", page, re.S | re.I):
        body = table.group(0)
        head = re.search(r"<thead\b.*?</thead>", body, re.S | re.I)
        if not head:
            continue
        headers = [plain(cell).lower() for cell in re.findall(r"<th\b[^>]*>(.*?)</th>", head.group(0), re.S | re.I)]
        number = next((i for i, h in enumerate(headers) if h in ("num", "no.", "no", "#", "number")), None)
        name = next((i for i, h in enumerate(headers) if h == "name"), None)
        position = next((i for i, h in enumerate(headers) if h in ("pos", "pos.", "position")), None)
        if number is None or name is None:
            continue
        rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", body[head.end():], re.S | re.I)
        for row in rows:
            cells = [plain(cell) for cell in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", row, re.S | re.I)]
            if len(cells) <= max(number, name):
                continue
            players.append({"name": cells[name], "first_name": None, "last_name": None,
                            "jersey": cells[number] or None,
                            "position": cells[position] if position is not None and position < len(cells) else None})
    return players


def page_season(page: str) -> int | None:
    title = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
    headings = [plain(h) for h in re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", page, re.S | re.I)]
    for text in ([plain(title.group(1))] if title else []) + headings:
        match = _SEASON_TEXT.search(text)
        if match:
            return int(next(group for group in match.groups() if group))
    selected = _SELECTED_SEASON.search(page) or _SEASON_CLASS.search(page)
    return int(selected.group(1)) if selected else None


def parse_roster(page: str) -> dict[str, Any]:
    for method, reader in (("NUXT_PAYLOAD", _nuxt_players), ("ROSTER_ITEM_CARDS", _card_players),
                           ("ROSTER_TABLE", _table_players)):
        players = reader(page)
        if players:
            unique: dict[tuple[str, str | None], dict[str, Any]] = {}
            for player in players:
                unique.setdefault((player["name"].casefold(), player["jersey"]), player)
            return {"roster_version": ROSTER_VERSION, "method": method, "season": page_season(page),
                    "players": list(unique.values()), "raw_records": len(players)}
    return {"roster_version": ROSTER_VERSION, "method": None, "season": page_season(page), "players": [],
            "raw_records": 0}

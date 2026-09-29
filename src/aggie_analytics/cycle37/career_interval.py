r"""Cycle #37 — Attempt #10 — the interval a career row's identity names, read again from its verified revision
(MF37A09-01).

A career row's identity ends in an interval ordinal: ``C37A05:<page>:<revision>:<family>:<row>:<interval>``. Inside a
field that states several intervals (Walter Camp's ``coachyears2 = 1892, 1894–1895``) every row of the field shares its
page, revision, capture, source unit and spans, so none of those says *which* interval a row is. The Attempt 9 manager
swapped the reciprocal default and Attempt 4 edges of those two rows, blanked (or copied) their ``years_as_written``
and resealed; the v5 verifier compared that text by containment, treated blank text as agreement, and served. Text a
row carries about its own interval proves nothing.

The interval is what the row's parser read from the source: the parser version that produced the row splits the
unit's years text into intervals, sorts them, and the row is the one its identity numbers. This module reads them
again from the verified revision text:

* **v37.5** (Attempt 5 rows): the current parser itself (``career_infobox.career_rows``), whose rows are keyed by the
  same ``(family, row index)`` the identities carry -- every one of the 292 Attempt 5 rows in a multi-interval field
  (and the 12 interval fields of each) is reproduced exactly;
* **v37.4** (Attempt 4 rows, and an Attempt 4 file used as the successor): that parser's interval reader, frozen here
  verbatim from ``career_infobox.py`` at 4d6321e1 (blob a7dd2d976bf7fb285f98e471d7c827706f6e3470), over the source
  units that version's splitting names (``career_witness.source_units(..., literal_blanking=False)``) and its own
  choice of a list line's years text -- every one of the 281 Attempt 4 rows in a multi-interval field is reproduced
  exactly. v37.4 read no role lines, so a role-line identity names no v37.4 interval.

:func:`interval_problems` says why what a row states about its interval is not the interval its identity names: an
identity naming no source row (or two), an ordinal the source does not state, an entry holding a different number of
rows than the source states intervals, or stated interval text or fields that differ. What a row does not state -- a
blank ``years_as_written`` (SQL NULL, empty or whitespace, the one absent state) or a NULL interval field -- is absent:
it proves nothing and asserts nothing, so it neither grants nor blocks lineage. Lineage between two rows of one field is
decided by their identities' ordinals (``career_successor.check_anchors``), never by text or normalized dates.

Cycle #37 -- Attempt #11 (MF37A10-01): the verifier now reads *every* successor row again (and every Attempt 4 row an
edge names), not only rows an unrestructured edge inside a multi-interval field reaches, and it separates the reasons:
an identity naming no source row, an ordinal the source does not state or a field held by another number of rows than
the source states intervals is the field's cardinality (:data:`CARDINALITY`); text or fields that are not the interval
are the row's period assertion.

Nothing here rewrites a parser, fills a missing date or decides whether a revision's statement is true.
"""

from __future__ import annotations

import html
import json
import re
from typing import Any, Mapping

from aggie_analytics.cycle37 import career_infobox as ci
from aggie_analytics.cycle37 import career_witness as cw

V375 = "BAS-CAREER-INFOBOX-v37.5"
V374 = "BAS-CAREER-INFOBOX-v37.4"
#: The parser versions whose intervals can be read again here (the delivered v37.2 rows are always parents: their
#: interval is their identity's ordinal, compared by ``check_anchors``, and their bytes are the pinned release's).
READERS = frozenset({V375, V374})
#: The interval fields a parser writes for every interval (``career_infobox._interval``), in both versions.
INTERVAL_FIELDS = ("start", "end", "ongoing", "start_state", "end_state", "start_bounds", "end_bounds",
                   "start_qualifier", "end_qualifier", "definite_first_season", "definite_last_season",
                   "bounds_consistent")
_JSON_FIELDS = frozenset({"start_bounds", "end_bounds"})
#: A row whose source row states no interval is written as one row with this interval (both builders).
NO_INTERVAL = {"start": None, "end": None, "ongoing": False, "as_written": None}

#: Why what a row states is not the interval its identity names.
NO_SOURCE_ROW = "IDENTITY_NAMES_NO_SOURCE_ROW"
AMBIGUOUS_SOURCE_ROW = "IDENTITY_NAMES_SEVERAL_SOURCE_ROWS"
NO_READER = "NO_INTERVAL_READER_FOR_ITS_PARSER_VERSION"
ORDINAL_NOT_STATED = "IDENTITY_ORDINAL_NOT_AN_INTERVAL_OF_ITS_SOURCE_ROW"
COUNT_NOT_STATED = "ENTRY_ROWS_ARE_NOT_ITS_SOURCE_INTERVALS"
TEXT_NOT_ITS_INTERVAL = "INTERVAL_TEXT_IS_NOT_ITS_SOURCE_INTERVAL"
FIELD_NOT_ITS_INTERVAL = "INTERVAL_FIELD_IS_NOT_ITS_SOURCE_INTERVAL"
#: v37.11 (MF37A10-01): the reasons that say a row is not one of the intervals its source field states -- no source row
#: (or several), an ordinal the source does not state, or an entry holding another number of rows than the source states
#: intervals. They are the field's cardinality; the other two reasons are what a row asserts about its own period.
CARDINALITY = frozenset({NO_SOURCE_ROW, AMBIGUOUS_SOURCE_ROW, NO_READER, ORDINAL_NOT_STATED, COUNT_NOT_STATED})


def is_cardinality(problem: str) -> bool:
    """Whether ``problem`` (an :func:`interval_problems` reason) concerns the field's membership, ordinal or
    multiplicity rather than a row's stated period."""

    return problem in CARDINALITY


# ---------------------------------------------------------------------------------------------------------------------
# The v37.4 interval reader, frozen verbatim from career_infobox.py at 4d6321e1 (blob a7dd2d97...): ``plain`` and
# ``parse_years`` with the patterns, endpoint states and helpers they use, and ``list_rows``' choice of a line's years.
# Names keep their v37.4 spelling with a ``_v374`` suffix where the current module has a different function.

_LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]*))?\]\]")
_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
_REF = re.compile(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", re.I | re.S)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_DISPLAY_TEMPLATE = re.compile(
    r"\{\{\s*(abbr|abbrlink|tooltip|hover title|nowrap|nobr|small|smaller|big|nobold|noitalic)\s*\|"
    r"\s*([^{}|]*?)\s*(?:\|\s*([^{}]*?)\s*)?\}\}", re.I)
_YEAR_TEMPLATE = re.compile(r"\{\{\s*[A-Za-z][^|{}]*\|\s*(1[89]\d{2}|20\d{2})\s*(?:\|[^{}]*)?\}\}")
_CIRCA_TEMPLATE = re.compile(r"\{\{\s*(?:circa|c\.|ca\.?|approx\.?|approximately)\s*(?:\|([^{}]*))?\}\}", re.I)


def _circa(match: re.Match[str]) -> str:
    """``{{circa|1973}}`` -> "c. 1973"; ``{{circa|1959–1962}}`` -> "c. 1959–c. 1962"; ``{{circa}}`` -> "c."."""

    positional = [part for part in (match.group(1) or "").split("|") if "=" not in part]
    argument = positional[0].strip() if positional else ""
    return re.sub(r"(1[89]\d{2}|20\d{2})", r"c. \1", argument) if argument else "c."


def plain_v374(text: str) -> str:
    text = _COMMENT.sub("", _REF.sub("", text))
    text = _CIRCA_TEMPLATE.sub(_circa, text)
    text = _YEAR_TEMPLATE.sub(lambda m: m.group(1), text)
    text = _LINK.sub(lambda m: m.group(2) if m.group(2) is not None else m.group(1), text)
    # v37.4: a display template shows its first argument; deleting it (as every template was) turned
    # "({{abbr|OC|Offensive coordinator}})" into an empty parenthetical.
    text = _DISPLAY_TEMPLATE.sub(lambda m: m.group(2), text)
    text = _TEMPLATE.sub("", text)
    text = re.sub(r"'{2,}", "", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


STATED = "STATED"
QUESTIONED = "QUESTIONED"            # "1990?" -- the revision doubts its own year
APPROXIMATE = "APPROXIMATE"          # "c. 1950"
DECADE = "DECADE"                    # "1950s", "late 1950s"
PARTIAL = "PARTIAL"                  # "191?", "201x", "19??"
UNKNOWN = "UNKNOWN"                  # "?", "unknown", or an endpoint the revision leaves empty ("1999–")
PRESENT = "PRESENT"                  # "present", "current"
AFTER = "AFTER"                      # "after 2005" as an end: still there through 2005, end unknown
BEFORE = "BEFORE"                    # "before 1990" as a start: there by 1989, start unknown
ALTERNATIVES = "ALTERNATIVES"        # "1994 or 1995" as an end: one of these years
_DASHES = "‐‑‒–—−-"
_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
_ENDPOINT = re.compile(
    r"(?P<qual>\bc\.|\bca\.|\bcirca\b|\bearly\b|\bmid\b|\blate\b|\bafter\b|\bbefore\b)?\s*"
    rf"(?:\b{_MONTH}\s+(?:\d{{1,2}},?\s+)?)?"
    r"(?P<core>(?P<decade>\b(?:1[89]\d0|20\d0)s\b)"
    r"|(?P<partial>\b(?:1[89]\d[?x]|20\d[?x]|1[89][?x][?x]|20[?x][?x])(?![\dx?]))"
    r"|(?P<year>\b(?:1[89]\d\d|20\d\d))(?P<questioned>\?)?(?![\d])"
    r"|(?P<unknown>\?+|\bunknown\b)"
    r"|(?P<present>\bpresent\b|\bcurrent\b|\btoday\b)"
    r"|(?P<short>(?<![\d])\d\d(?![\d?x])))", re.I)


def _endpoint(match: re.Match) -> dict[str, Any]:
    qual = (match.group("qual") or "").lower() or None
    written = match.group(0).strip()
    if match.group("decade"):
        low = int(match.group("decade")[:4])
        return {"state": DECADE, "value": None, "bounds": [low, low + 9], "qualifier": qual, "as_written": written}
    if match.group("partial"):
        token = match.group("partial").lower().replace("x", "?")
        low, high = int(token.replace("?", "0")), int(token.replace("?", "9"))
        return {"state": PARTIAL, "value": None, "bounds": [low, high], "qualifier": qual, "as_written": written}
    if match.group("year"):
        year = int(match.group("year"))
        if match.group("questioned"):
            state = QUESTIONED
        elif qual in ("c.", "ca.", "circa"):
            state = APPROXIMATE
        elif qual == "after":
            state = AFTER
        elif qual == "before":
            state = BEFORE
        else:
            state = STATED
        return {"state": state, "value": year if state == STATED else None,
                "bounds": [year, year] if state in (STATED, QUESTIONED) else None, "stated_year": year,
                "qualifier": qual, "as_written": written}
    if match.group("unknown"):
        return {"state": UNKNOWN, "value": None, "bounds": None, "qualifier": qual, "as_written": written}
    if match.group("present"):
        return {"state": PRESENT, "value": None, "bounds": None, "qualifier": qual, "as_written": written}
    return {"state": "SHORT", "value": int(match.group("short")), "bounds": None, "qualifier": qual,
            "as_written": written}


def _unknown_endpoint(as_written: str) -> dict[str, Any]:
    return {"state": UNKNOWN, "value": None, "bounds": None, "qualifier": None, "as_written": as_written}


def _latest_start(point: dict[str, Any]) -> int | None:
    """The latest year a stated start can be: the first season the person was certainly there."""

    if point["state"] == STATED:
        return point["value"]
    if point["state"] in (PARTIAL, DECADE):
        return point["bounds"][1]
    if point["state"] == BEFORE:
        return point["stated_year"] - 1
    return None


def _earliest_end(point: dict[str, Any]) -> int | None:
    """The earliest year a stated end can be: the last season the person was certainly there."""

    if point["state"] == STATED:
        return point["value"]
    if point["state"] in (PARTIAL, DECADE, ALTERNATIVES):
        return point["bounds"][0]
    if point["state"] == AFTER:
        return point["stated_year"]
    return None


def _interval(start: dict[str, Any], end: dict[str, Any], as_written: str) -> dict[str, Any]:
    if end["state"] == "SHORT":
        base = start.get("value") or start.get("stated_year") or ((start.get("bounds") or [None])[0])
        if base is None:
            end = _unknown_endpoint(end["as_written"])
        else:
            year = int(str(base)[:2] + f"{end['value']:02d}")
            if year < base:
                year += 100
            end = {"state": STATED, "value": year, "bounds": [year, year], "stated_year": year,
                   "qualifier": None, "as_written": end["as_written"]}
    ongoing = end["state"] == PRESENT
    if start is end:
        # One point: certain only when the revision states that exact year.
        first = last = start["value"] if start["state"] == STATED else None
    else:
        first = _latest_start(start)
        last = _earliest_end(end)
        if first is None and not ongoing:
            first = last  # only the end year is certain ("?–2009")
        if last is None and not ongoing:
            last = first  # only the start year is certain ("2009–?")
    consistent = not (first is not None and last is not None and first > last)
    return {
        "start": start["value"] if start["state"] == STATED else None,
        "end": end["value"] if end["state"] == STATED else None,
        "ongoing": ongoing,
        "start_state": start["state"], "end_state": end["state"],
        "start_bounds": start.get("bounds"), "end_bounds": end.get("bounds"),
        "start_qualifier": start.get("qualifier"), "end_qualifier": end.get("qualifier"),
        "definite_first_season": first if consistent else None,
        "definite_last_season": (last if consistent else None) if not ongoing else None,
        "bounds_consistent": consistent,
        "as_written": as_written,
    }


def parse_years_v374(raw: str) -> list[dict[str, Any]]:
    """Intervals a years field states: ranges, single years, lists, "present" -- and what is uncertain.

    v37.4 (MF37A03-05). Every interval keeps the v37.2 fields ``start``, ``end``, ``ongoing`` and
    ``as_written``; ``start``/``end`` hold a year only where the revision states that exact year. Each
    endpoint also has a state (:data:`STATED`, :data:`QUESTIONED`, :data:`APPROXIMATE`, :data:`DECADE`,
    :data:`PARTIAL`, :data:`UNKNOWN`, :data:`PRESENT`, :data:`AFTER`, :data:`BEFORE`, :data:`ALTERNATIVES`)
    and bounds where the text gives them, and the interval states the seasons it *definitely* covers
    (``definite_first_season``/``definite_last_season``; open when ongoing). ``2009–?`` is certain only for
    2009, is not ongoing, and has no end year; a field that states no year at all ("?", "unknown") is one
    interval with nothing certain rather than no interval.
    """

    # ``original`` is what the revision renders; ``text`` is the same string with every dash spelling, and the
    # word "to", replaced by an en dash of the same length, so positions -- and ``as_written`` -- are the
    # revision's own characters.
    original = html.unescape(plain_v374(html.unescape(raw)))
    text = original
    for dash in _DASHES:
        text = text.replace(dash, "–")
    text = re.sub(r"\s+to\s+", lambda m: "–".center(len(m.group(0))), text, flags=re.I)
    points = [(match.start(), match.end(), _endpoint(match)) for match in _ENDPOINT.finditer(text)]
    intervals: list[dict[str, Any]] = []
    index = 0
    consumed_until = 0
    while index < len(points):
        begin, finish, point = points[index]
        before_gap = text[consumed_until:begin]
        following = points[index + 1] if index + 1 < len(points) else None
        after_gap = text[finish:following[0]] if following else text[finish:]
        if point["state"] == "SHORT":
            index += 1
            continue
        # "–1999" (the start left empty) and "1999–" (the end left empty) are unknown endpoints.
        if before_gap.strip().endswith("–") and not intervals and not before_gap.strip()[:-1].strip():
            intervals.append(_interval(_unknown_endpoint(""), point, original[max(0, begin - 1):finish].strip()))
            consumed_until, index = finish, index + 1
            continue
        if following and after_gap.strip() == "–":
            end_point = following[2]
            end_finish = following[1]
            # "1990–1994 or 1995": the end is one of the stated years.
            rest = text[end_finish:]
            alternative = re.match(r"\s+or\s+(1[89]\d\d|20\d\d)\b", rest)
            if alternative and end_point["state"] == STATED:
                years = sorted({end_point["value"], int(alternative.group(1))})
                end_point = {"state": ALTERNATIVES, "value": None, "bounds": [years[0], years[-1]],
                             "qualifier": "or", "as_written": end_point["as_written"] + alternative.group(0)}
                end_finish += alternative.end()
            intervals.append(_interval(point, end_point, original[begin:end_finish].strip()))
            consumed_until = end_finish
            index += 2
            while index < len(points) and points[index][0] < consumed_until:
                index += 1
            continue
        if after_gap.strip().startswith("–") and (following is None or after_gap.strip() != "–"):
            intervals.append(_interval(point, _unknown_endpoint(""), original[begin:finish].strip() + "–"))
            consumed_until, index = finish, index + 1
            continue
        intervals.append(_interval(point, point, original[begin:finish].strip()))
        consumed_until, index = finish, index + 1
    if not intervals and text.strip() and text.strip() not in ("–", "()", "*"):
        # The field states a stint but no year ("?", "unknown", "N/A"): one interval, nothing certain.
        unknown = _unknown_endpoint(original.strip())
        intervals.append(_interval(unknown, unknown, original.strip()))
    intervals.sort(key=lambda item: (item["start"] is None, item["start"] or item["definite_first_season"] or 0))
    return intervals


_BREAK = re.compile(r"<br\s*/?>", re.I)
_LIST_TEMPLATE = re.compile(r"^\{\{\s*(?:ubl|unbulleted\s+list|plainlist|flatlist|nowrap)\s*\|(.*)\}\}$",
                            re.I | re.S)


def _unwrap_v374(body: str) -> str:
    """``{{ubl|[[Michigan ...|Michigan]] (2015–2023)}}`` -> its single item."""

    match = _LIST_TEMPLATE.match(body.strip())
    return match.group(1).strip() if match else body


def _line_years_v374(body: str) -> str | None:
    """The years text v37.4 read from a line: its last parenthetical whose plain text holds a year (``list_rows``)."""

    years_match = None
    for paren in re.finditer(r"\(([^()]*)\)", body):
        if re.search(r"1[89]\d{2}|20\d{2}", plain_v374(paren.group(1))):
            years_match = paren
    return years_match.group(1) if years_match else None


# ------------------------------------------------------------------------------------------ end of the frozen v37.4 code


def _v374_intervals(text: str) -> dict[tuple[str, int], list[dict[str, Any]] | None]:
    units = cw.source_units(text, literal_blanking=False)
    out: dict[tuple[str, int], list[dict[str, Any]] | None] = {}
    for key, found in units.items():
        if len(found) != 1:
            out[key] = None
            continue
        unit = found[0]
        if unit.form == cw.PARAMETER:
            out[key] = parse_years_v374(text[unit.years[0]:unit.years[1]]) if unit.years is not None else []
        elif unit.form == cw.LIST_LINE:
            head = _BREAK.split(_unwrap_v374(text[unit.team[0]:unit.team[1]]), maxsplit=1)[0]
            years = _line_years_v374(head)
            out[key] = parse_years_v374(years) if years else []
        elif unit.form == cw.NESTED_LINE:
            years = _line_years_v374(_unwrap_v374(text[unit.team[0]:unit.team[1]]))
            if years is None and unit.employer is not None:
                # A nested line without its own years carries its employer line's (v37.4 ``list_rows``).
                head = _BREAK.split(_unwrap_v374(text[unit.employer[0]:unit.employer[1]]), maxsplit=1)[0]
                years = _line_years_v374(head)
            out[key] = parse_years_v374(years) if years else []
        # A role line is a v37.5 unit; v37.4 read none, so its identity names no v37.4 interval (absent here).
    return out


def _v375_intervals(text: str) -> dict[tuple[str, int], list[dict[str, Any]] | None]:
    out: dict[tuple[str, int], list[dict[str, Any]] | None] = {}
    for row in ci.career_rows(text)["rows"]:
        key = (str(row["family"]), int(row["index"]))
        out[key] = None if key in out else list(row["intervals"])   # two rows under one identity: ambiguous
    return out


def source_intervals(text: str, parser_version: str) -> dict[tuple[str, int], list[dict[str, Any]] | None]:
    """Every ``(family, row index)`` of a revision with the intervals ``parser_version`` read there (None where the
    identity names several rows). Raises KeyError for a version with no reader."""

    if parser_version == V375:
        return _v375_intervals(text)
    if parser_version == V374:
        return _v374_intervals(text)
    raise KeyError(parser_version)


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _stated(field: str, value: Any) -> Any:
    """A stored interval field as the parser wrote it: JSON bounds decoded, a boolean as a boolean."""

    if field in _JSON_FIELDS and isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    if field in ("ongoing", "bounds_consistent") and isinstance(value, (int, bool)):
        return bool(value)
    return value


def interval_problems(row: Mapping[str, Any], intervals: list[dict[str, Any]] | None | str,
                      entry_rows: int) -> list[str]:
    """Why what ``row`` states about its interval is not the interval its identity names; empty when it is.

    ``intervals`` is what the row's parser read for its ``(family, row index)`` (:func:`source_intervals`): a list,
    None for an identity naming several rows, or the string :data:`NO_SOURCE_ROW` / :data:`NO_READER`. ``entry_rows``
    is how many rows of the same file carry this identity's entry. A blank text or a NULL field is absent: never
    compared, never agreement."""

    if isinstance(intervals, str):
        return [intervals]
    if intervals is None:
        return [AMBIGUOUS_SOURCE_ROW]
    stated = intervals or [NO_INTERVAL]
    try:
        ordinal = int(row.get("interval_index"))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return [ORDINAL_NOT_STATED]
    problems = []
    if not 0 <= ordinal < len(stated):
        return [ORDINAL_NOT_STATED]
    if entry_rows != len(stated):
        problems.append(COUNT_NOT_STATED)
    interval = stated[ordinal]
    if not _blank(row.get("years_as_written")) and row.get("years_as_written") != interval.get("as_written"):
        problems.append(TEXT_NOT_ITS_INTERVAL)
    wrong = [field for field in INTERVAL_FIELDS
             if row.get(field) is not None and _stated(field, row.get(field)) != interval.get(field)]
    if wrong:
        problems.append(f"{FIELD_NOT_ITS_INTERVAL}{wrong}")
    return problems

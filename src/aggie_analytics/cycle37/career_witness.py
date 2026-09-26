r"""Cycle #37 — Attempt #8 — the source field a career row's recorded witness must be (MF37A07-01).

A career row records where in its revision's wikitext it was read: ``team_char_span`` and ``years_char_span``. The
Attempt 7 manager enlarged two of Fred Mariani's genuine witnesses -- the 1974 graduate-assistant row's and the 2009
Rutgers row's -- to one span running from the first job's parameter to the sixth's, swapped their reciprocal default
and Attempt 4 edges and re-sealed: the enlarged spans were still exact substrings of the genuine revision, so they
overlapped both jobs' fields and every anchor agreed. Overlap and containment of text do not show which field a span
*is*.

A genuine witness is a source unit of its revision, and the row's own identity names which one. The parser that read
the row (``career_infobox``) defines the units, and every one of the 218,110 genuine rows of the delivered release,
the Attempt 4 file and the Attempt 5 successor records exactly the unit its identity names:

* a numbered field ``coach_team6`` / ``coach_years6`` (``coaching_``-style fields under index 2000 + N): the team span
  is exactly the ``*_team`` parameter's value and the years span exactly the ``*_years`` parameter's value, as the
  infobox's top-level parameters split (an empty value is a zero-length span at its position);
* a line of a career list (``pastcoaching`` and the other list fields, index base + line number): the team span is
  exactly the line -- a bullet line, a nested line under an employer, or an item of a list template -- and a years
  span lies inside it, or, for a date inherited from the employer, inside the employer's line;
* a role line after a break inside an employer line (index employer index * 100 + line number): the team span is
  exactly that role line, and a years span lies inside it or inside its employer's line.

:func:`source_units` enumerates every unit of a revision with the identity that names it, reusing the parser's own
splitting (so the units are exactly the parser's), and :func:`witness_problems` says why a row's recorded witness is
not the unit its identity names. The parser versions split parameters differently in one respect only: v37.5 reads
braces, brackets and bars inside ``<nowiki>`` and HTML comments as literal text; v37.4 and v37.2 (the Attempt 4 file
and the delivered release) do not. A row is checked under its own version's splitting.

An unrecorded span is an absent field, not a witness: it is never checked here and never used as an anchor. Nothing
here decides whether a revision's statement is true, or rewrites a parser.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from aggie_analytics.cycle37 import career_infobox as ci

#: The parser versions whose rows a consumer checks, and whether each reads comments and nowiki as literal text
#: when it splits an infobox's parameters.
LITERAL_BLANKING = {"BAS-CAREER-INFOBOX-v37.5": True, "BAS-CAREER-INFOBOX-v37.4": False,
                    "BAS-CAREER-INFOBOX-v37.2": False}

PARAMETER = "PARAMETER"
LIST_LINE = "LIST_LINE"
NESTED_LINE = "NESTED_LINE"
ROLE_LINE = "ROLE_LINE"

#: Why a recorded witness is not its row's source unit.
NO_SOURCE_UNIT = "NO_SOURCE_UNIT"
TEAM_NOT_SOURCE_UNIT = "TEAM_NOT_SOURCE_UNIT"
YEARS_NOT_SOURCE_UNIT = "YEARS_NOT_SOURCE_UNIT"


@dataclass(frozen=True)
class Unit:
    """One source unit: the field (or line) an identity names, with the spans a row read from it must record."""

    form: str
    field: str
    team: tuple[int, int] | None
    years: tuple[int, int] | None
    employer: tuple[int, int] | None = None


def literals_change_structure(text: str) -> bool:
    """Whether reading comments and nowiki as literal text can split this revision's parameters differently."""

    return ci._literal_blanked(text) != text


def _boxes(text: str, literal_blanking: bool) -> list[ci.Infobox]:
    if literal_blanking:
        return ci.find_infoboxes(text)
    # v37.4 / v37.2: the same brace matching and parameter split over the revision as written.
    boxes = []
    for match in ci._INFOBOX.finditer(text):
        end = ci._match_braces(text, match.start())
        box = ci.Infobox(template=match.group(1).strip(), start=match.start(), end=end)
        box.params = ci.split_params(text, match.end(), end - 2)
        boxes.append(box)
    return boxes


def source_units(text: str, *, literal_blanking: bool = True) -> dict[tuple[str, int], list[Unit]]:
    """Every source unit of a revision, keyed by the ``(family, row index)`` that names it.

    Numbered fields follow the parser's pairing (the first infobox stating a field owns it); list lines follow its
    numbering (bullet lines, then the items of a list template written as a block, from the field's base); a role
    line after a break is numbered under its employer line. A key can name more than one unit only where the parser
    would give two rows one identity; a witness then has to be one of them."""

    boxes = _boxes(text, literal_blanking)
    units: dict[tuple[str, int], list[Unit]] = {}
    pairs: dict[tuple[str, int], dict[str, ci.Param]] = {}
    for box in boxes:
        for param in box.params:
            match = ci._PAIR.match(param.name)
            if not match:
                continue
            family, kind, number = match.group(1).lower(), match.group(2).lower(), int(match.group(3))
            if family in ci._VARIANT_FIELDS:
                number += ci.VARIANT_FIELD_INDEX_OFFSET
            pairs.setdefault((family, number), {}).setdefault(kind, param)
    for (family, number), both in pairs.items():
        team, years = both.get("team"), both.get("years")
        units.setdefault((ci.FAMILIES[family], number), []).append(Unit(
            PARAMETER, (team or years).name, (team.value_start, team.value_end) if team else None,
            (years.value_start, years.value_end) if years else None))
    for box in boxes:
        for param in box.params:
            family = ci.LIST_FIELDS.get(param.name)
            if not family:
                continue
            base = ci.LIST_FIELD_INDEX_BASE.get(param.name, 1000)
            employer: tuple[int, tuple[int, int]] | None = None
            for number, (depth, raw_item, raw_start) in enumerate(ci._list_entries(param.value), start=1):
                start = param.value_start + raw_start
                index, span = base + number, (start, start + len(raw_item))
                if depth > 1 and employer is not None:
                    units.setdefault((family, index), []).append(Unit(NESTED_LINE, param.name, span, None,
                                                                      employer[1]))
                    continue
                units.setdefault((family, index), []).append(Unit(LIST_LINE, param.name, span, None))
                employer = (index, span)
                body, body_offset = ci._unwrap(raw_item)
                body_start = start + body_offset
                breaks = list(ci._BREAK.finditer(body))
                for line, found in enumerate(breaks, start=1):
                    stop = breaks[line].start() if line < len(breaks) else len(body)
                    part = body[found.end():stop]
                    lead = ci._LINE_LEAD.match(part)
                    begin = lead.end() if lead else 0
                    line_start = body_start + found.end() + begin
                    units.setdefault((family, index * ci.ROLE_LINE_INDEX_FACTOR + line), []).append(Unit(
                        ROLE_LINE, param.name, (line_start, line_start + len(part[begin:].rstrip())), None, span))
    return units


_SPAN_TEXT = re.compile(r"\[(0|[1-9][0-9]*), ?(0|[1-9][0-9]*)\]")


def recorded_span(value: Any) -> tuple[int, int] | None:
    """A recorded ``[start, end]`` span, or None when the row records none (``null`` or ``[null, null]``). A value
    that is recorded but is not a well-formed span is returned as ``(-1, -1)``, which no unit equals."""

    if value is None:
        return None
    if isinstance(value, str):
        match = _SPAN_TEXT.fullmatch(value)   # the common case, read without a JSON decode
        if match:
            start, end = int(match.group(1)), int(match.group(2))
            return (start, end) if start <= end else (-1, -1)
    try:
        decoded = json.loads(value) if isinstance(value, str) else value
    except ValueError:
        return (-1, -1)
    if decoded is None or decoded == [None, None]:
        return None
    if (isinstance(decoded, list) and len(decoded) == 2
            and all(isinstance(v, int) and not isinstance(v, bool) for v in decoded) and 0 <= decoded[0] <= decoded[1]):
        return decoded[0], decoded[1]
    return (-1, -1)


def _inside(inner: tuple[int, int], outer: tuple[int, int] | None) -> bool:
    return outer is not None and outer[0] <= inner[0] <= inner[1] <= outer[1]


def witness_problems(row: Mapping[str, Any], units: Mapping[tuple[str, int], list[Unit]]) -> tuple[list[str], str]:
    """``(problems, form)`` for one row: empty problems when every span the row records is exactly the source unit
    its identity ``(family, row_index)`` names; the unit's form (``NO_WITNESS`` when the row records none)."""

    team, years = recorded_span(row.get("team_char_span")), recorded_span(row.get("years_char_span"))
    if team is None and years is None:
        return [], "NO_WITNESS"
    try:
        key = (str(row.get("family")), int(row.get("row_index")))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return [NO_SOURCE_UNIT], "NONE"
    candidates = units.get(key) or []
    if not candidates:
        return [NO_SOURCE_UNIT], "NONE"
    best: list[str] | None = None
    for unit in candidates:
        problems = []
        if team is not None and team != unit.team:
            problems.append(TEAM_NOT_SOURCE_UNIT)
        if years is not None:
            if unit.form == PARAMETER:
                ok = years == unit.years
            else:
                ok = _inside(years, unit.team) or _inside(years, unit.employer)
            if not ok:
                problems.append(YEARS_NOT_SOURCE_UNIT)
        if not problems:
            return [], unit.form
        if best is None or len(problems) < len(best):
            best = problems
    return best or [NO_SOURCE_UNIT], candidates[0].form

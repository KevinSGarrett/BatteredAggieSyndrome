"""Coaching and playing careers read from a revision-bound infobox (R37-05).

The Cycle #30 career parser flattened each infobox row into an employer
string and a title, and got the shape wrong in general ways the raw wikitext
shows directly:

* A team with no parenthetical ("Stamford HS (TX)") had its location
  qualifier taken as the title ("TX"), and the row was refused as having no
  role. In a coach infobox a row without a role parenthetical is the
  person's own programme; that is recorded here as the infobox convention it
  is, not as an explicit title.
* The link target (``[[Howard Payne Yellow Jackets football|Howard Payne]]``)
  that identifies the employer far better than its display text was thrown
  away.
* Player years, administrative years and coaching years were not typed
  apart, and years such as ``1990, 1992`` or ``2019–present`` were not split
  into intervals.

This module parses the wikitext itself: it finds the infobox by brace
matching, splits its top-level parameters with their character spans, and
parses each numbered ``*_years``/``*_team`` pair. Nothing here resolves an
employer to a canonical program or decides whether a person is who a staff
page names; it reports what the revision says and where.

v37.4 (Cycle #37 - Attempt #4, MF37A03-04/05). Two general failures made a
fact out of text the revision does not state:

* a parenthetical that was neither a recognized role nor a recognized place
  (``Rutgers (DFO)``, ``(STQC)``, ``(SA)``, ``(trainer)``, an ``{{abbr}}``
  whose display this module deleted) was filed as an employer qualifier, and
  the row then took the head-coach convention. Parentheticals are now a role,
  a place, a league or level, a sport scope, or explicitly **unresolved**; an
  unresolved one blocks the convention and is carried verbatim. A code is a
  role only through the established vocabulary or the row's own
  ``{{abbr|code|expansion}}``; ``SA`` means "student assistant" on one page
  and "special assistant to the president" on another, so no code is given a
  meaning the row does not state;
* years a revision states as uncertain (``2009–?``, ``?–2009``, ``191?``,
  ``c. 1950``, ``1950s``, ``1999–``, ``–after 2005``) were read as definite
  single years, and ``1990&ndash;1995`` as two separate years. Every endpoint
  now carries its own state (stated, questioned, approximate, decade, partial,
  unknown, present, after, before) and every interval the seasons it
  *definitely* covers; nothing unknown is filled in.

Numbered career fields written ``coaching_``/``playing_``/``administrating_``
(CFL and gridiron-person infoboxes) were never read; they are now, under row
indexes 2000 + N so no earlier row identity moves.
"""

from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass, field
from typing import Any

from aggie_analytics.cycle33.role_taxonomy import assignments_from_title

PARSER_VERSION = "BAS-CAREER-INFOBOX-v37.5"
#: The parser of the delivered release's career rows (the successor's predecessor table).
PREDECESSOR_PARSER_VERSION = "BAS-CAREER-INFOBOX-v37.2"
#: The parser of the Attempt 4 explicit successor, which the Attempt 5 successor supersedes row by row.
A4_PARSER_VERSION = "BAS-CAREER-INFOBOX-v37.4"

#: Parameter families and what they record.
FAMILIES = {"coach": "COACHING", "player": "PLAYING", "admin": "ADMINISTRATIVE", "executive": "ADMINISTRATIVE",
            "coaching": "COACHING", "playing": "PLAYING", "administrating": "ADMINISTRATIVE"}
_PAIR = re.compile(r"^(coaching|coach|playing|player|administrating|admin|executive)_?(years|team)(\d+)$", re.I)
#: v37.4: the spelled-out field names are read under their own index range so they can never take an
#: earlier row's identity.
VARIANT_FIELD_INDEX_OFFSET = 2000
_VARIANT_FIELDS = frozenset({"coaching", "playing", "administrating"})

#: What a team parenthetical is (v37.4). Only a role states a job; only an unresolved one blocks the
#: head-coach convention without stating one.
ROLE = "ROLE"
PLACE = "PLACE"
LEAGUE_OR_LEVEL = "LEAGUE_OR_LEVEL"
SPORT_SCOPE = "SPORT_SCOPE"
UNRESOLVED = "UNRESOLVED"
QUALIFIER_KINDS = frozenset({PLACE, LEAGUE_OR_LEVEL, SPORT_SCOPE})
_LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]*))?\]\]")
_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
_REF = re.compile(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", re.I | re.S)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_YEAR = r"(1[89]\d{2}|20\d{2})"
_RANGE = re.compile(_YEAR + r"\s*(?:[-–—]|to)\s*(" + r"1[89]\d{2}|20\d{2}|\d{2}|present|current" + r")", re.I)
_SINGLE = re.compile(_YEAR)
#: A parenthetical is a role when its plain text names a coaching job.
_ROLE_WORDS = re.compile(
    r"\b(?:assistant|asst|associate|assoc|coordinator|coord|oc|dc|stc|ga|graduate|interim|acting|head\s+coach|hc|"
    r"co-|coach|coaches|line|lines|backs?|receivers|ends|tackles|guards|st|special\s+teams|qb|qbs|quarterbacks|lb|"
    r"lbs|linebackers|db|dbs|secondary|safeties|corners|cornerbacks|recruiting|analyst|volunteer|consultant|"
    r"director|strength|conditioning|defense|offense|defensive|offensive|tight|running|wide|kickers|punters|scout|"
    r"intern|advisor|manager|freshman|frosh|jv|junior\s+varsity|passing|run\s+game|pass\s+game|quality\s+control|"
    r"qc|te|ol|dl|wr|rb|coordinator|admin|athletic|ad|player\s+personnel|operations|"
    # Position abbreviations and phrases the cached infoboxes use; each was
    # found as a role the first parse left inside the employer (R37-05).
    r"s|fs|ss|olb|ilb|mlb|nt|de|dt|cb|nb|ot|og|hb|fb|tb|ob|k|p|ahc|rc|oline|dline|backfield|chief\s+of\s+staff|"
    r"chief|scout\s+team|freshmen|spring|offensive\s+assistant|defensive\s+assistant|nickels?|nickelbacks?|"
    r"stars?|edge|edges|rush|jack|dqc|oqc|dga|oga|ds|ops|gm)\b", re.I)
#: US state and province codes, which are location qualifiers ("Stamford HS
#: (TX)").
_PLACE_CODES = frozenset(
    "AL AK AZ AR CA CO CT DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH "
    "OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY PR ON QC BC AB MB SK NS NB".split())
_NOT_A_ROLE = frozenset({"unmapped_title_review_required", "pronoun_not_coaching_title"})
_SCHOOL_LIKE = re.compile(r"\b(?:HS|high\s+school|academy|prep|secondary\s+school|school)\b", re.I)
_HAS_PLACE = re.compile(r"\((?:[A-Z]{2}|[A-Z][a-z]+,\s*[A-Z]{2})\)")

#: Codes that are both a place and a coaching role: Delaware / defensive
#: ends, Georgia / graduate assistant, District of Columbia / defensive
#: coordinator, Quebec / quality control.
_PLACE_OR_ROLE = frozenset({"DE", "GA", "DC", "QC"})


#: v37.4 place vocabulary: US states, territories and DC by name and by the older abbreviations newspapers
#: and infoboxes still use, Canadian provinces, and countries. A place qualifies an employer; it never states
#: a job.
_STATE_NAMES = frozenset(name.casefold() for name in (
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "Florida",
    "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine",
    "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska",
    "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio",
    "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas",
    "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming", "District of Columbia",
    "Washington, D.C.", "Puerto Rico", "Guam", "American Samoa", "U.S. Virgin Islands", "Ontario", "Quebec",
    "British Columbia", "Alberta", "Manitoba", "Saskatchewan", "Nova Scotia", "New Brunswick", "Newfoundland",
    "Newfoundland and Labrador", "Prince Edward Island", "Canada", "Mexico", "United States", "USA", "U.S.",
    "Germany", "West Germany", "Austria", "Italy", "Japan", "England", "Scotland", "Wales", "United Kingdom", "UK",
    "Ireland", "France", "Spain", "Finland", "Sweden", "Norway", "Denmark", "Netherlands", "Belgium",
    "Switzerland", "Poland", "Czech Republic", "Hungary", "Russia", "Turkey", "Australia", "New Zealand",
    "Brazil", "China", "South Korea", "Korea", "Philippines", "Israel", "Samoa", "South Africa", "Tonga", "Fiji"))
_STATE_ABBREVIATIONS = frozenset(re.sub(r"\s+", "", name).casefold() for name in (
    "Ala.", "Ariz.", "Ark.", "Calif.", "Cal.", "Colo.", "Conn.", "Del.", "Fla.", "Ga.", "Ill.", "Ind.", "Kan.",
    "Kans.", "Ky.", "La.", "Md.", "Mass.", "Mich.", "Minn.", "Miss.", "Mo.", "Mont.", "Neb.", "Nebr.", "Nev.",
    "N.H.", "N.J.", "N.M.", "N. Mex.", "N.Y.", "N.C.", "N.D.", "N. Dak.", "Okla.", "Ore.", "Oreg.", "Pa.", "Penn.",
    "R.I.", "S.C.", "S.D.", "S. Dak.", "Tenn.", "Tex.", "Vt.", "Va.", "Wash.", "W.Va.", "Wis.", "Wisc.", "Wyo.",
    "D.C.", "Ont.", "Que.", "B.C.", "Alta.", "Man.", "Sask.", "N.S."))
#: Leagues and competitive levels that disambiguate an employer ("Montreal (CFL)", "Tyler (JC)").
_LEAGUES = frozenset(name.casefold() for name in (
    "NFL", "CFL", "AFL", "AAFC", "WFL", "USFL", "XFL", "UFL", "NFL Europe", "NFLE", "WLAF", "NAFL", "Arena",
    "Arena Football", "Arena Football League", "AF2", "IFL", "NAIA", "NCAA", "JUCO", "JC", "junior college",
    "community college", "semi-pro", "semipro", "Division I", "Division II", "Division III", "D-I", "D-II",
    "D-III", "DI", "DII", "DIII", "FBS", "FCS", "I-A", "I-AA", "D-IAA"))
#: A parenthetical made only of sport names ("football, basketball") scopes the employer to those sports.
_SPORT_SCOPE = re.compile(
    r"^(?:(?:football|basketball|baseball|softball|track(?:\s+and\s+field)?|cross[\s-]+country|golf|tennis|"
    r"wrestling|swimming|soccer|lacrosse|hockey|volleyball|boxing|rugby)(?:\s*(?:,|and|&|/)\s*|\s*$))+$", re.I)
#: Display templates: ``{{abbr|code|expansion}}`` and ``{{tooltip|code|expansion}}`` display the code and
#: state its meaning on this row; the layout templates display their content.
_DISPLAY_TEMPLATE = re.compile(
    r"\{\{\s*(abbr|abbrlink|tooltip|hover title|nowrap|nobr|small|smaller|big|nobold|noitalic)\s*\|"
    r"\s*([^{}|]*?)\s*(?:\|\s*([^{}]*?)\s*)?\}\}", re.I)


def _is_place(text: str) -> bool:
    folded = text.strip().casefold()
    if text.strip().upper().rstrip(".") in _PLACE_CODES or folded in _STATE_NAMES:
        return True
    if re.sub(r"\s+", "", folded) in _STATE_ABBREVIATIONS:
        return True
    if "," in text:
        city, _, region = text.rpartition(",")
        region = region.strip()
        return bool(re.fullmatch(r"[A-Z][A-Za-z.' -]*", city.strip())) and (
            region.upper().rstrip(".") in _PLACE_CODES or region.casefold() in _STATE_NAMES
            or re.sub(r"\s+", "", region.casefold()) in _STATE_ABBREVIATIONS)
    return False


def _maps_to_role(text: str) -> bool:
    if _ROLE_WORDS.search(text):
        return True
    # Anything the versioned staff role taxonomy maps to a role is a role
    # ("adviser", "player development", "compliance"); a place maps to none.
    mapped = {item["role"] for item in assignments_from_title(text)}
    return bool(mapped - _NOT_A_ROLE)


def classify_parenthetical(inner: str, head: str, later_role: bool, *,
                           expansion: str | None = None) -> dict[str, Any]:
    """What one team parenthetical is: ``kind`` (a role, a place, a league or level, a sport scope, or
    unresolved), whether a place/role reading is ambiguous, and the basis for the decision.

    A both-ways code is a place only when a role parenthetical follows it
    ("Miami (OH) (DE)" reads the other way round, so "Smyrna HS (DE) (DC)"
    makes DE the place). Otherwise it is read as the role the infobox's
    parentheticals normally carry, and flagged as ambiguous when the employer
    is a school that states no other place.

    v37.4: text that is none of these is ``UNRESOLVED`` -- not a qualifier. ``expansion`` is the meaning
    this row's own ``{{abbr}}``/``{{tooltip}}`` states for the displayed code, and is the only way a code
    outside the established vocabulary becomes a role.
    """

    text = inner.strip()
    code = text.upper().rstrip(".")
    if code in _PLACE_OR_ROLE:
        if later_role:
            return {"kind": PLACE, "ambiguous": False, "basis": "BOTH_WAYS_CODE_BEFORE_A_ROLE_IS_A_PLACE"}
        return {"kind": ROLE, "ambiguous": bool(_SCHOOL_LIKE.search(head) and not _HAS_PLACE.search(head)),
                "basis": "BOTH_WAYS_CODE_READ_AS_THE_ROLE"}
    if _is_place(text):
        return {"kind": PLACE, "ambiguous": False, "basis": "STATE_PROVINCE_COUNTRY_OR_CITY_REGION"}
    if text.casefold() in _LEAGUES:
        return {"kind": LEAGUE_OR_LEVEL, "ambiguous": False, "basis": "LEAGUE_OR_COMPETITIVE_LEVEL"}
    if text and _SPORT_SCOPE.fullmatch(text):
        return {"kind": SPORT_SCOPE, "ambiguous": False, "basis": "SPORT_NAMES_ONLY"}
    if text and _maps_to_role(text):
        return {"kind": ROLE, "ambiguous": False, "basis": "ESTABLISHED_ROLE_VOCABULARY"}
    if expansion and _maps_to_role(expansion):
        return {"kind": ROLE, "ambiguous": False, "basis": "EXPANSION_STATED_BY_THIS_ROWS_TEMPLATE"}
    return {"kind": UNRESOLVED, "ambiguous": False,
            "basis": "EMPTY_PARENTHETICAL" if not text else "NOT_A_KNOWN_ROLE_PLACE_LEAGUE_OR_SPORT"}


def _classify_parenthetical(inner: str, head: str, later_role: bool) -> tuple[bool, bool]:
    """(is a role, the reading is ambiguous): the v37.2 interface, kept for its callers."""

    decided = classify_parenthetical(inner, head, later_role)
    return decided["kind"] == ROLE, decided["ambiguous"]


def _is_role(inner: str, head: str, later_role: bool) -> bool:
    return _classify_parenthetical(inner, head, later_role)[0]


def _template_display(inner_raw: str) -> tuple[str, str | None]:
    """(what a parenthetical displays, the expansion its own abbreviation template states, if any)."""

    expansion = None
    match = _DISPLAY_TEMPLATE.search(inner_raw)
    if match and match.group(1).casefold() in ("abbr", "abbrlink", "tooltip", "hover title"):
        expansion = plain(match.group(3) or "") or None
    return plain(inner_raw), expansion


@dataclass
class Param:
    name: str
    value: str
    value_start: int
    value_end: int


@dataclass
class Infobox:
    template: str
    start: int
    end: int
    params: list[Param] = field(default_factory=list)


def _match_braces(text: str, start: int) -> int:
    """Index just past the ``}}`` closing the template opened at ``start``."""

    depth = 0
    index = start
    while index < len(text) - 1:
        pair = text[index:index + 2]
        if pair == "{{":
            depth += 1
            index += 2
            continue
        if pair == "}}":
            depth -= 1
            index += 2
            if depth == 0:
                return index
            continue
        index += 1
    return len(text)


_INFOBOX = re.compile(r"\{\{\s*Infobox\s+([^|\n}]+)", re.I)


def find_infoboxes(text: str) -> list[Infobox]:
    """Every infobox on the page, including one embedded as another's module.

    An officeholder's page carries its coaching career as ``| module =
    {{Infobox college coach | embed = yes ...}}``; its parameters are not
    top-level parameters of the outer box, so each box is parsed on its own.
    """

    # v37.5: braces, brackets and bars inside <nowiki> and comments are literal text in the revision; they are
    # blanked (same length) while the structure is found, and every value is taken from the revision itself.
    structure = _literal_blanked(text)
    boxes = []
    for match in _INFOBOX.finditer(structure):
        end = _match_braces(structure, match.start())
        box = Infobox(template=match.group(1).strip(), start=match.start(), end=end)
        box.params = [Param(param.name, text[param.value_start:param.value_end], param.value_start, param.value_end)
                      for param in split_params(structure, match.end(), end - 2)]
        boxes.append(box)
    return boxes


_LITERAL = re.compile(r"<nowiki>.*?</nowiki>|<!--.*?-->", re.I | re.S)


def _literal_blanked(text: str) -> str:
    return _LITERAL.sub(lambda m: re.sub(r"[{}\[\]|]", " ", m.group(0)), text)


def find_infobox(text: str) -> Infobox | None:
    boxes = find_infoboxes(text)
    return boxes[0] if boxes else None


def split_params(text: str, start: int, end: int) -> list[Param]:
    """Top-level ``| name = value`` parameters with the value's character span."""

    params: list[Param] = []
    depth_links = depth_templates = 0
    index = start
    cut = None
    while index < end:
        pair = text[index:index + 2]
        if pair == "[[":
            depth_links += 1
            index += 2
            continue
        if pair == "]]" and depth_links:
            depth_links -= 1
            index += 2
            continue
        if pair == "{{":
            depth_templates += 1
            index += 2
            continue
        if pair == "}}" and depth_templates:
            depth_templates -= 1
            index += 2
            continue
        if text[index] == "|" and not depth_links and not depth_templates:
            if cut is not None:
                params.append(_param(text, cut, index))
            cut = index + 1
        index += 1
    if cut is not None:
        params.append(_param(text, cut, end))
    return [param for param in params if param.name]


def _param(text: str, start: int, end: int) -> Param:
    chunk = text[start:end]
    if "=" not in chunk:
        return Param("", "", start, end)
    name, _, value = chunk.partition("=")
    lead = len(value) - len(value.lstrip())
    value_start = start + len(name) + 1 + lead
    stripped = value.strip()
    return Param(name.strip().lower(), stripped, value_start, value_start + len(stripped))


#: v37.5 (Cycle #37 - Attempt #5, MF37A04-03). v37.4 rendered *any* template whose first argument is a year as
#: that year alone ("a season template such as {{nfly|2001}} renders as its year"), so the two-endpoint form
#: {{NFL Year|1987|1989}} became 1987 and {{nfly|2023|present}} became 2023. The supported grammar is now explicit,
#: from the independent census of every template in the cached career fields (a05_career_template_census.py):
#: a season template renders one season, and a template of the "Year" family with a second argument renders the
#: range it displays -- to a year, to "present", or (second argument written empty) to an open end. Any other
#: argument shape, and any other template that carries a year inside a date, is kept as an explicitly unresolved
#: date rather than cut to its first year. Citation and footnote templates are not dates and are removed as before.
SEASON_TEMPLATES = frozenset((
    "nfl year", "nfly", "cfl year", "cfly", "afl year", "afly", "ufl year", "usfl year", "xfl year", "af2 year",
    "nfle year", "aaf year", "ifl year", "cafl year", "elf year", "pifl year", "nal year", "cifl year", "cif year",
    "rhe season", "ams season", "fra season", "ber season", "hsd season"))
#: The templates of the "Year" family take an optional end season as their second argument.
SEASON_RANGE_TEMPLATES = frozenset(name for name in SEASON_TEMPLATES if name.endswith(" year") or name.endswith("y"))
_DATE_TEMPLATE = re.compile(r"\{\{\s*([^|{}]*?)\s*\|([^{}]*)\}\}")
_NOT_A_DATE_TEMPLATE = re.compile(
    r"^(?:cite\b.*|citation.*|efn.*|sfn.*|refn|ref|notetag|note label|cn|citation needed|dead link|clarify|when|"
    r"by whom|dubious|disputed inline|failed verification|better source.*|verification needed|"
    r"additional citation needed|abbr|abbrlink|tooltip|tip|hover title|nowrap|nobr|small|smaller|big|nobold|"
    r"noitalic|ubl|unbulleted list|plainlist|flatlist|bulleted list|hlist|ublist)$", re.I)
_NAMED_ARGUMENT = re.compile(r"^\s*[A-Za-z_][\w -]*=")
UNRESOLVED_TEMPLATE = "UNRESOLVED_TEMPLATE"
#: What an unresolved date template becomes inside a date: a marker carrying the template's raw text (base32, so
#: no later rule can read a year or a template out of it); parse_years reads it as an unresolved endpoint.
_UNRESOLVED_MARK = re.compile("⟦UDT:([A-Z2-7=]+)⟧")


def _season_template(match: re.Match[str], dates: bool) -> str:
    import base64  # noqa: PLC0415

    name = re.sub(r"[\s_]+", " ", match.group(1)).strip().casefold()
    arguments = [part.strip() for part in match.group(2).split("|")]
    positional = [part for part in arguments if not _NAMED_ARGUMENT.match(part)]
    named = [part for part in arguments if _NAMED_ARGUMENT.match(part)]
    year = re.compile(_YEAR)
    if name in SEASON_TEMPLATES:
        if not named and positional and year.fullmatch(positional[0]):
            if len(positional) == 1:
                return positional[0]
            if len(positional) == 2 and name in SEASON_RANGE_TEMPLATES:
                end = positional[1]
                if year.fullmatch(end) or end.casefold() in ("present", "current"):
                    return f"{positional[0]}–{end}"
                if end == "":
                    return f"{positional[0]}–"  # an end season written empty is an open end, never the start alone
        # A season template in a shape the grammar does not read (named arguments, a third argument, a short year).
    elif _NOT_A_DATE_TEMPLATE.match(name) or not re.search(_YEAR, match.group(2)):
        return match.group(0)
    if not dates:
        return ""
    return "⟦UDT:" + base64.b32encode(match.group(0).encode("utf-8")).decode("ascii") + "⟧"


def unresolved_templates(text: str) -> list[str]:
    """The raw text of every unresolved date template marked in ``text``."""

    import base64  # noqa: PLC0415

    return [base64.b32decode(m.group(1)).decode("utf-8") for m in _UNRESOLVED_MARK.finditer(text)]
#: v37.4 (Attempt 4 census): ``{{circa|1973}}`` states an approximate year. The season-template rule above
#: collapsed it to "1973", an exact year; it is rendered as the "c. 1973" it displays instead.
_CIRCA_TEMPLATE = re.compile(r"\{\{\s*(?:circa|c\.|ca\.?|approx\.?|approximately)\s*(?:\|([^{}]*))?\}\}", re.I)


def _circa(match: re.Match[str]) -> str:
    """``{{circa|1973}}`` -> "c. 1973"; ``{{circa|1959–1962}}`` -> "c. 1959–c. 1962"; ``{{circa}}`` -> "c."."""

    positional = [part for part in (match.group(1) or "").split("|") if "=" not in part]
    argument = positional[0].strip() if positional else ""
    return re.sub(r"(1[89]\d{2}|20\d{2})", r"c. \1", argument) if argument else "c."


def plain(text: str, dates: bool = False) -> str:
    """What the wikitext displays. With ``dates`` the text is a date: a season template the grammar cannot read, or
    any other template carrying a year, becomes an unresolved-date marker instead of disappearing (v37.5)."""

    text = _COMMENT.sub("", _REF.sub("", text)).replace(ITEM_BREAK, " ")
    text = _CIRCA_TEMPLATE.sub(_circa, text)
    text = _DATE_TEMPLATE.sub(lambda m: _season_template(m, dates), text)
    text = _LINK.sub(lambda m: m.group(2) if m.group(2) is not None else m.group(1), text)
    # v37.4: a display template shows its first argument; deleting it (as every template was) turned
    # "({{abbr|OC|Offensive coordinator}})" into an empty parenthetical.
    text = _DISPLAY_TEMPLATE.sub(lambda m: m.group(2), text)
    text = _TEMPLATE.sub("", text)
    text = re.sub(r"'{2,}", "", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


#: v37.4 endpoint states. Only ``STATED`` carries an exact year in ``start``/``end``; the others carry what
#: the revision says about the year, never an invented one.
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
    # v37.5: an unresolved date template, as parse_years writes it in its scanning text.
    "|(?P<udt>⟦U(?P<udt_index>\\d+)_*⟧)"
    r"|(?P<short>(?<![\d])\d\d(?![\d?x])))", re.I)


def _endpoint(match: re.Match) -> dict[str, Any]:
    qual = (match.group("qual") or "").lower() or None
    written = match.group(0).strip()
    if match.group("udt"):
        # The template's raw text replaces this placeholder as ``as_written`` in parse_years.
        return {"state": UNRESOLVED_TEMPLATE, "value": None, "bounds": None, "qualifier": None,
                "as_written": written, "template_index": int(match.group("udt_index"))}
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


def parse_years(raw: str) -> list[dict[str, Any]]:
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
    #
    # v37.5 (MF37A04-03): season templates render the range they display ({{NFL Year|1987|1989}} -> 1987–1989);
    # a date template the grammar cannot read is shown in ``original`` as its own raw text and scanned in ``text``
    # as a same-length placeholder that reads as an UNRESOLVED_TEMPLATE endpoint -- never as its first year.
    rendered = html.unescape(plain(html.unescape(raw), dates=True))
    templates = unresolved_templates(rendered)
    shown, scanned, last = [], [], 0
    for number, mark in enumerate(_UNRESOLVED_MARK.finditer(rendered)):
        shown.append(rendered[last:mark.start()])
        scanned.append(rendered[last:mark.start()])
        token = f"⟦U{number}"
        shown.append(templates[number])
        scanned.append(token + "_" * max(0, len(templates[number]) - len(token) - 1) + "⟧")
        last = mark.end()
    shown.append(rendered[last:])
    scanned.append(rendered[last:])
    original = "".join(shown)
    text = "".join(scanned)
    for dash in _DASHES:
        text = text.replace(dash, "–")
    text = re.sub(r"\s+to\s+", lambda m: "–".center(len(m.group(0))), text, flags=re.I)
    points = [(match.start(), match.end(), _endpoint(match)) for match in _ENDPOINT.finditer(text)]
    for _, _, point in points:
        if point["state"] == UNRESOLVED_TEMPLATE:
            point["as_written"] = templates[point.pop("template_index")]
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


def _parenthetical_spans(text: str, begin: int = 0, end: int | None = None,
                         opaque: list[tuple[int, int]] | None = None) -> tuple[list[tuple[int, int]], bool]:
    """Top-level ``(...)`` spans of ``text[begin:end]`` and whether every parenthesis there is paired.

    ``opaque`` spans (wiki links) are stepped over whole: their parentheses belong to the link.
    """

    spans: list[tuple[int, int]] = []
    depth, start, paired = 0, None, True
    index = begin
    stop = len(text) if end is None else end
    skips = sorted(opaque or [])
    while index < stop:
        skip = next(((a, b) for a, b in skips if a <= index < b), None)
        if skip is not None:
            index = skip[1]
            continue
        char = text[index]
        if char == "(":
            if depth == 0:
                start = index
            depth += 1
        elif char == ")":
            if depth:
                depth -= 1
                if depth == 0 and start is not None:
                    spans.append((start, index + 1))
                    start = None
            else:
                paired = False
        index += 1
    return spans, paired and depth == 0


def parse_team(raw: str) -> dict[str, Any]:
    """Employer link and display, its qualifiers, and the role parenthetical."""

    cleaned = _COMMENT.sub("", _REF.sub("", raw)).strip()
    link = _LINK.search(cleaned)
    parentheticals, paired = _parenthetical_spans(cleaned)
    unpaired: list[dict[str, Any]] = []
    if not paired:
        # v37.4 (Attempt 4 census): an unpaired parenthesis -- "[[Claremore High School|Claremore (HS (OK)]]
        # ([[Defensive coordinator|DC]])" -- made one scan over the whole text swallow the role that follows it.
        # Links are read as closed units instead: the employer link's own text (its target and display each
        # alone when the whole is unpaired) and the text outside every link. A parenthesis still unpaired
        # outside the links is kept as unresolved text, and it blocks the head-coach convention.
        links = [(match.start(), match.end()) for match in _LINK.finditer(cleaned)]
        parentheticals, outside_paired = _parenthetical_spans(cleaned, opaque=links)
        if link is not None:
            inside, inside_paired = _parenthetical_spans(cleaned, link.start(), link.end())
            if not inside_paired:
                inside = []
                for group in (1, 2):
                    if link.group(group) is not None:
                        part, part_paired = _parenthetical_spans(cleaned, link.start(group), link.end(group))
                        inside += part if part_paired else []
            parentheticals = sorted(parentheticals + inside)
        if not outside_paired:
            outside_text = "".join(char for index, char in enumerate(cleaned)
                                   if not any(a <= index < b for a, b in links))
            unpaired.append({"text": plain(outside_text).strip(), "raw": outside_text.strip(),
                             "basis": "UNPAIRED_PARENTHESIS_OUTSIDE_THE_LINKS", "expansion": None})
    roles, qualifiers, unresolved = [], [], list(unpaired)
    qualifier_kinds: list[dict[str, str]] = []
    role_spans = set()
    outside = [(b, f) for b, f in parentheticals if not (link is not None and link.start() < b < link.end())]
    # Decide from the last parenthetical backwards, so "(DE)" knows whether a
    # role follows it.
    later_role = False
    decided: dict[tuple[int, int], dict[str, Any]] = {}
    for begin, finish in reversed(outside):
        inner, expansion = _template_display(cleaned[begin + 1:finish - 1])
        decision = classify_parenthetical(inner, cleaned[:begin], later_role, expansion=expansion)
        decided[(begin, finish)] = {**decision, "text": inner, "expansion": expansion}
        later_role = later_role or decision["kind"] == ROLE
    for begin, finish in parentheticals:
        inner = cleaned[begin + 1:finish - 1]
        if (begin, finish) not in decided:
            qualifiers.append(plain(inner))  # a parenthetical inside the link text belongs to the name
            qualifier_kinds.append({"text": plain(inner), "kind": "PART_OF_THE_LINKED_NAME"})
            continue
        decision = decided[(begin, finish)]
        if decision["kind"] == ROLE:
            role_link = _LINK.search(inner)
            roles.append({"text": decision["text"], "link_target": role_link.group(1).strip() if role_link else None,
                          "place_or_role_ambiguous": decision["ambiguous"], "basis": decision["basis"],
                          "expansion": decision["expansion"]})
            role_spans.add((begin, finish))
        elif decision["kind"] == UNRESOLVED:
            # v37.4 (MF37A03-04): neither a qualifier nor a role. Kept verbatim, in the display as the revision
            # writes it, and it blocks the head-coach convention; nothing is inferred from it.
            unresolved.append({"text": decision["text"], "raw": inner, "basis": decision["basis"],
                               "expansion": decision["expansion"]})
        else:
            qualifiers.append(decision["text"])
            qualifier_kinds.append({"text": decision["text"], "kind": decision["kind"]})
    head = cleaned
    for begin, finish in sorted(role_spans, reverse=True):
        head = head[:begin] + head[finish:]
    display = plain(head)
    marker = re.search(r"\s*[*†‡#]+$", display)
    if marker:
        qualifiers.append(f"roster marker {marker.group(0).strip()}")
        qualifier_kinds.append({"text": marker.group(0).strip(), "kind": "ROSTER_MARKER"})
        display = display[:marker.start()].strip()
    # A role stated by the row's own template is mapped from the meaning that template states.
    role_texts = [item["expansion"] if item["basis"] == "EXPANSION_STATED_BY_THIS_ROWS_TEMPLATE" else item["text"]
                  for item in roles]
    if roles:
        basis = "EXPLICIT_PARENTHETICAL"
    elif unresolved:
        basis = "UNRESOLVED_PARENTHETICAL"
    else:
        basis = "INFOBOX_CONVENTION_NO_ROLE_PARENTHETICAL"
    return {
        "raw": raw, "employer_display": display, "employer_link_target": link.group(1).strip() if link else None,
        "employer_qualifiers": qualifiers, "employer_qualifier_kinds": qualifier_kinds,
        "role_parentheticals": roles, "unresolved_parentheticals": unresolved,
        "role_text": "; ".join(role_texts) or None,
        "role_basis": basis, "parser_version": PARSER_VERSION,
    }


#: Nicknames of professional clubs (NFL, CFL, USFL, XFL, historical AFL/WFL).
#: Used only for a link target that is not a "... football" college article.
_PRO_NICKNAME = re.compile(
    r"\b(?:Chiefs|Dolphins|Eagles|Buccaneers|Chargers|Patriots|Browns|Raiders|Rams|Cowboys|Giants|Jets|Bills|"
    r"Bengals|Steelers|Ravens|Texans|Colts|Titans|Oilers|Jaguars|Broncos|Seahawks|49ers|Cardinals|Falcons|Panthers|"
    r"Saints|Packers|Bears|Vikings|Lions|Commanders|Redskins|Argonauts|Tiger-Cats|Roughriders|Rough Riders|"
    r"Stampeders|Eskimos|Elks|Blue Bombers|Alouettes|Redblacks|Renegades|Rough Riders|Stallions|Gamblers|Maulers|"
    r"Generals|Express|Outlaws|Invaders|Bandits|Wranglers|Breakers|Showboats|Federals|Blitz|Renegades|Roughnecks|"
    r"Defenders|Guardians|Battlehawks|Brahmas|Sea Dragons|Vipers|Dragons|Hitmen|Enforcers|Thunderbolts|Demons|"
    r"Machine|Ghosts|Admirals|Monarchs|Surge|Galaxy|Centurions|Thunder|Rhein Fire|Claymores|Sea Devils)\b")


#: Another sport's programme, as a link target or a qualifier names it
#: ("[[Holy Cross Crusaders track and field|Holy Cross]]"). The R37-03
#: historical sample found such rows read as football coaching (v37.1).
_OTHER_SPORT_PROGRAM = re.compile(
    r"\b(?:baseball|softball|basketball|track(?:\s+and\s+field)?|cross[\s-]+country|lacrosse|soccer|hockey|"
    r"wrestling|swimming|diving|golf|tennis|volleyball|rowing|crew|gymnastics|rugby|boxing|fencing)\b", re.I)
#: Infobox templates of another sport ("football biography" is association football).
NON_GRIDIRON_TEMPLATES = frozenset({"baseball biography", "basketball biography", "ice hockey player",
                                    "tennis biography", "football biography", "professional wrestler"})


def names_other_sport(text: str) -> bool:
    return bool(_OTHER_SPORT_PROGRAM.search(text)) and not re.search(r"\bfootball\b", text, re.I)


def employer_kind(team: dict[str, Any]) -> str:
    """College, high school, professional, another sport or unknown, from the link and the display."""

    target = str(team.get("employer_link_target") or "")
    display = str(team.get("employer_display") or "")
    both = f"{target} {display}"
    qualifiers = [str(q) for q in team.get("employer_qualifiers") or []]
    if names_other_sport(target) or (any(names_other_sport(q) for q in qualifiers)
                                     and not any(re.search(r"football", q, re.I) for q in qualifiers)):
        return "OTHER_SPORT_PROGRAM"
    if re.search(r"\bhigh\s+school\b|\bacademy\b|\bprep\b|\bsecondary\s+school\b", both, re.I) or \
            re.search(r"\bHS\b", both):
        return "HIGH_SCHOOL"
    if re.search(r"\b(?:NFL|CFL|AFL|USFL|XFL|WLAF|NFL\s+Europe|Arena\s+Football|UFL|AAFC|IFL)\b", both):
        return "PROFESSIONAL"
    # A professional club's article is titled "City Nickname", never "... football".
    if not target.lower().endswith(" football") and _PRO_NICKNAME.search(target or display):
        return "PROFESSIONAL"
    if target.lower().endswith(" football") or re.search(r"\b(?:college|university|state|institute)\b", both, re.I):
        return "COLLEGE_OR_OTHER_FOOTBALL_PROGRAM"
    if target and not target.lower().endswith(" football"):
        return "LINKED_NON_COLLEGE_OR_UNKNOWN"
    return "UNKNOWN"


#: Bulleted career lists (NFL/gridiron biographies) and the family each records.
LIST_FIELDS = {"pastcoaching": "COACHING", "pastteams": "PLAYING", "pastexecutive": "ADMINISTRATIVE",
               "pastexecutives": "ADMINISTRATIVE", "pastadmin": "ADMINISTRATIVE"}
#: v37.4 (Attempt 4 census): ``pastadmin`` lists, never read before, are numbered from their own base so an
#: item can never take a ``pastexecutive`` item's identity on the same page.
LIST_FIELD_INDEX_BASE = {"pastadmin": 3000}
#: v37.5 (census): the items of a list template ({{ubl|[[Purdue]] (1943)|Assistant coach}}) display one per line.
#: Inside a list line, each top-level "|" between two items is read as this one-character line break, so every
#: position -- and so every recorded span -- stays the revision's own.
ITEM_BREAK = "\ue000"
_BREAK = re.compile(r"<br\s*/?>|" + ITEM_BREAK, re.I)
_LIST_TEMPLATE = re.compile(r"^\{\{\s*(?:ubl|unbulleted\s+list|plainlist|flatlist|nowrap|bulleted\s+list|blist)\s*\|(.*)\}\}$",
                            re.I | re.S)
_ITEM_LIST_TEMPLATE = re.compile(r"^\{\{\s*(?:ubl|unbulleted\s+list|bulleted\s+list|blist)\s*\|", re.I)


def _top_level_bars(text: str) -> list[int]:
    """Positions of each "|" in ``text`` outside every link and template."""

    bars, links, templates, index = [], 0, 0, 0
    while index < len(text):
        pair = text[index:index + 2]
        if pair in ("[[", "{{", "]]", "}}"):
            if pair == "[[":
                links += 1
            elif pair == "{{":
                templates += 1
            elif pair == "]]" and links:
                links -= 1
            elif pair == "}}" and templates:
                templates -= 1
            index += 2
            continue
        if text[index] == "|" and not links and not templates:
            bars.append(index)
        index += 1
    return bars


def _unwrap(body: str) -> tuple[str, int]:
    """``{{ubl|[[Michigan ...|Michigan]] (2015–2023)}}`` -> its item, and where that text starts in ``body``.

    v37.5: only a template that closes at the end of the line is unwrapped, and the items of a multi-item list
    template are kept as lines (:data:`ITEM_BREAK`) instead of being read as one employer text.
    """

    stripped = body.strip()
    match = _LIST_TEMPLATE.match(stripped)
    if not match or _match_braces(stripped, 0) != len(stripped):
        return body, 0
    inner = match.group(1)
    if _ITEM_LIST_TEMPLATE.match(stripped):
        chars = list(inner)
        for position in _top_level_bars(inner):
            chars[position] = ITEM_BREAK
        inner = "".join(chars)
    begin = len(body) - len(body.lstrip()) + match.start(1) + len(inner) - len(inner.lstrip())
    return inner.strip(), begin


def _list_entries(value: str) -> list[tuple[int, str, int]]:
    """(depth, text, start) of every item of a list field: its bullet lines, then the items of any list template
    written as a block of its own ({{bulleted list | ... }}), which v37.4 did not read. Bullet lines keep the
    numbers they always had; template items are numbered after them."""

    blocks, entries = [], []
    for match in re.finditer(r"^[ \t]*\{\{", value, re.M):
        start = match.end() - 2
        end = _match_braces(value, start)
        if not _ITEM_LIST_TEMPLATE.match(value[start:end]) or value[end:].split("\n", 1)[0].strip():
            continue
        blocks.append((start, end))
    for match in re.finditer(r"^(\*+)\s*(.+?)\s*$", value, re.M):
        if not any(a <= match.start() < b for a, b in blocks):
            entries.append((len(match.group(1)), match.group(2), match.start(2)))
    for start, end in blocks:
        entries.extend((1, text, start + offset) for offset, text in _list_template_items(value[start:end]))
    return entries


def _list_template_items(value: str) -> list[tuple[int, str]]:
    """(start, text) of each item when a whole list field is one list template without bullets
    ({{bulleted list | [[Toledo ...|Toledo]] (1966)<br/>Graduate assistant | ...}}); otherwise none."""

    stripped = value.strip()
    if not _ITEM_LIST_TEMPLATE.match(stripped) or _match_braces(stripped, 0) != len(stripped):
        return []
    lead = len(value) - len(value.lstrip())
    inner_start = stripped.index("|") + 1
    inner = stripped[inner_start:-2]
    bounds = [-1] + _top_level_bars(inner) + [len(inner)]
    items = []
    for left, right in zip(bounds, bounds[1:]):
        chunk = inner[left + 1:right]
        text = chunk.strip()
        if text and not _NAMED_ARGUMENT.match(text):
            items.append((lead + inner_start + left + 1 + len(chunk) - len(chunk.lstrip()), text))
    return items


def _is_date_text(value: str) -> bool:
    rendered = plain(value, dates=True)
    return bool(re.search(_YEAR, rendered) or _UNRESOLVED_MARK.search(rendered))


#: v37.5 (MF37A04-03): a date written at the end of a list line without a balanced parenthesis around it
#: ("Defensive quality control coach {{nfly|2005|2006}})"). Each token is a template, a year (optionally
#: questioned) or "present"; tokens are joined by dashes, "to", commas or semicolons.
_DATE_TOKEN = r"(?:\{\{[^{}]*\}\}|(?:1[89]|20)\d\d\??|present|current)"
_TRAILING_DATE = re.compile(
    rf"\(?\s*(?P<date>{_DATE_TOKEN}(?:\s*(?:[-–—−‐‑‒]|to\b|,|;)\s*{_DATE_TOKEN}?)*)\s*\)?\s*$", re.I)


#: v37.5 (census): a date written at the very start of a line ("{{NFL Year|1978}} [[New York Jets]] (LB/ST)").
_LEADING_DATE = re.compile(
    rf"^\s*(?P<date>{_DATE_TOKEN}(?:\s*(?:[-–—−‐‑‒]|to\b|,|;)\s*{_DATE_TOKEN})*)\s+(?=\S)", re.I)
#: What may separate two date parentheticals that together state one date: "({{NFL Year|2002}}); ({{NFL Year|2004}})".
_JOINED_DATES = re.compile(r"[\s;,&/]*(?:and\b)?[\s;,&/]*", re.I)


def _template_spans(text: str) -> list[tuple[int, int]]:
    """Top-level ``{{...}}`` spans: a parenthesis inside a template (a footnote, an embedded list) is the template's."""

    spans, index = [], 0
    while True:
        start = text.find("{{", index)
        if start < 0:
            return spans
        index = _match_braces(text, start)
        spans.append((start, index))


def _own_dates(text: str) -> tuple[int, int, str, int, int] | None:
    """(start, end, date text, date start, date end) of the date a list line states for itself, or None.

    The last top-level parenthetical outside every link that carries a date -- with any date parentheticals
    directly before it, separated only by punctuation -- else a date written at the very end of the line, else one
    written at its very start, outside every link. v37.5 (census of the cached list items): a parenthesis inside a
    link ("[[American Football Association (1977–1983)#1983|1983]]") belongs to the link, a date parenthetical may
    itself contain one, and a date inside a reference or comment is never the line's date.
    """

    scan = _masked(text)
    links = [(m.start(), m.end()) for m in _LINK.finditer(scan)]
    spans, _paired = _parenthetical_spans(scan, opaque=links + _template_spans(scan))
    dated = [(a, b) for a, b in spans if _is_date_text(scan[a + 1:b - 1])]
    if dated:
        first = len(dated) - 1
        while first and _JOINED_DATES.fullmatch(scan[dated[first - 1][1]:dated[first][0]]):
            first -= 1
        start, end = dated[first][0], dated[-1][1]
        return (start, end, text[start + 1:end - 1], start + 1, end - 1)
    for pattern in (_TRAILING_DATE, _LEADING_DATE):
        match = pattern.search(scan)
        if match is None or not _is_date_text(match.group("date")):
            continue
        if any(a <= match.start("date") < b for a, b in links):
            continue
        return (match.start(), match.end(), text[match.start("date"):match.end("date")], match.start("date"),
                match.end("date"))
    return None


def list_rows(text: str, param: Param, family: str, template: str) -> list[dict[str, Any]]:
    """``* [[Team]] (years)<br>Role`` items, one row each, with the item's span.

    v37.5 (MF37A04-03): every row reads its *own* dates wherever the line writes them -- in a balanced
    parenthetical, or unparenthesized at the end of the line -- and records the span of that text. A nested line
    that states no date of its own inherits its employer line's dates, and says so: ``date_basis`` is
    ``INHERITED_FROM_PARENT_ITEM`` with the parent row's index and raw years span. A child's explicit date is never
    replaced by the parent's wider one.
    """

    rows = []
    offset = param.value_start
    base = LIST_FIELD_INDEX_BASE.get(param.name, 1000)
    parent: dict[str, Any] | None = None
    entries = _list_entries(param.value)
    for number, (depth, raw_item, raw_start) in enumerate(entries, start=1):
        body, body_offset = _unwrap(raw_item)
        # Where ``body`` starts in the wikitext, so a date inside it has an exact character span.
        body_start = offset + raw_start + body_offset
        if depth > 1 and parent is not None:
            # A nested line under an employer states a role and its own years
            # there ("** Running backs coach (2017–2018)"); the employer is the
            # parent item's.
            dates = _own_dates(body)
            if dates is not None:
                role_text = plain(body[:dates[0]] + body[dates[1]:])
                basis = ("CHILD_DATE_IN_BALANCED_PARENTHESES" if _balanced(body[dates[0]:dates[1]])
                         else "CHILD_DATE_WITHOUT_BALANCED_PARENTHESES")
            else:
                role_text = plain(body)
                basis = "INHERITED_FROM_PARENT_ITEM"
            team = {**parent["team"], "role_text": role_text or None, "role_basis": "NESTED_LIST_LINE_UNDER_EMPLOYER",
                    "role_parentheticals": [{"text": role_text, "link_target": None}] if role_text else []}
            start = offset + raw_start
            rows.append({
                "family": family, "index": base + number, "infobox": template, "list_field": param.name,
                "years_raw": dates[2] if dates else parent["years_raw"],
                "years_span": [body_start + dates[3], body_start + dates[4]] if dates else None,
                "intervals": parse_years(dates[2]) if dates else parent["intervals"],
                "team_raw": raw_item, "team_span": [start, start + len(raw_item)], "team": team,
                "employer_kind": parent["employer_kind"], "nested_under_index": parent["index"],
                "date_basis": basis,
                "date_parent": ({"row_index": parent["index"], "years_raw": parent["years_raw"],
                                 "years_span": parent["years_span"]} if dates is None else None),
            })
            continue
        parts = _BREAK.split(body, maxsplit=1)
        head = parts[0]
        lines = _role_lines(body)
        split = any(line["dates"] is not None for line in lines)
        # v37.5: when a role line after a break states its own date, each role line is its own row (below) and
        # this employer line states only the employer and its own dates.
        role_part = plain(parts[1]) if len(parts) > 1 and not split else None
        dates = _own_dates(head)
        years_raw = dates[2] if dates else None
        team_raw = (head[:dates[0]] + head[dates[1]:]).strip() if dates else head.strip()
        team = parse_team(team_raw)
        if role_part and not team["role_text"]:
            team["role_text"] = role_part
            team["role_basis"] = "EXPLICIT_LINE_AFTER_BREAK"
            team["role_parentheticals"] = [{"text": role_part, "link_target": None}]
        elif not team["role_text"] and team["role_basis"] == "UNRESOLVED_PARENTHETICAL":
            pass  # v37.4: an unresolved parenthetical stays unresolved; it is not "no role stated"
        elif not team["role_text"]:
            # The head-coach convention belongs to a coach infobox's numbered
            # rows; a list item that names no role states none.
            team["role_basis"] = "LIST_ROW_STATES_NO_ROLE"
        if dates is not None:
            _keep_words_beside_the_date(team, dates[2])
        start = offset + raw_start
        parent = {
            "family": family, "index": base + number, "infobox": template, "list_field": param.name,
            "years_raw": years_raw,
            "years_span": [body_start + dates[3], body_start + dates[4]] if dates else None,
            "intervals": parse_years(years_raw) if years_raw else [],
            "team_raw": raw_item, "team_span": [start, start + len(raw_item)], "team": team,
            "employer_kind": employer_kind(team),
            "date_basis": ("NO_DATE_STATED" if dates is None else
                           "ITEM_DATE_IN_BALANCED_PARENTHESES" if _balanced(head[dates[0]:dates[1]])
                           else "ITEM_DATE_WITHOUT_BALANCED_PARENTHESES"),
            "date_parent": None,
        }
        rows.append(parent)
        if not split:
            continue
        for line in lines:
            line_start = body_start + line["start"]
            own = line["dates"]
            if line["employer"] is not None:
                # Another employer written as the next item of the same list template: its own row, employer,
                # date and role, never this employer's.
                line_team = line["employer"]
                if not line_team["role_text"] and line_team["role_basis"] != "UNRESOLVED_PARENTHETICAL":
                    line_team["role_basis"] = "LIST_ROW_STATES_NO_ROLE"
                _keep_words_beside_the_date(line_team, own[2])
                rows.append({
                    "family": family, "index": parent["index"] * ROLE_LINE_INDEX_FACTOR + line["number"],
                    "infobox": template, "list_field": param.name, "years_raw": own[2],
                    "years_span": [line_start + own[3], line_start + own[4]], "intervals": parse_years(own[2]),
                    "team_raw": line["text"], "team_span": [line_start, line_start + len(line["text"])],
                    "team": line_team, "employer_kind": employer_kind(line_team), "nested_under_index": None,
                    "role_line_of_index": parent["index"],
                    "date_basis": ("EMPLOYER_LINE_DATE_IN_BALANCED_PARENTHESES"
                                   if _balanced(line["text"][own[0]:own[1]])
                                   else "EMPLOYER_LINE_DATE_WITHOUT_BALANCED_PARENTHESES"),
                    "date_parent": None,
                })
                continue
            if own is not None:
                role_text = plain(line["text"][:own[0]] + line["text"][own[1]:])
                basis = ("ROLE_LINE_DATE_IN_BALANCED_PARENTHESES" if _balanced(line["text"][own[0]:own[1]])
                         else "ROLE_LINE_DATE_WITHOUT_BALANCED_PARENTHESES")
            else:
                role_text = plain(line["text"])
                basis = "INHERITED_FROM_PARENT_ITEM"
            rows.append({
                "family": family, "index": parent["index"] * ROLE_LINE_INDEX_FACTOR + line["number"],
                "infobox": template, "list_field": param.name,
                "years_raw": own[2] if own else parent["years_raw"],
                "years_span": [line_start + own[3], line_start + own[4]] if own else None,
                "intervals": parse_years(own[2]) if own else parent["intervals"],
                "team_raw": line["text"], "team_span": [line_start, line_start + len(line["text"])],
                "team": {**team, "role_text": role_text or None, "role_basis": "ROLE_LINE_AFTER_BREAK_UNDER_EMPLOYER",
                         "role_parentheticals": [{"text": role_text, "link_target": None}] if role_text else []},
                "employer_kind": parent["employer_kind"], "nested_under_index": parent["index"],
                "role_line_of_index": parent["index"], "date_basis": basis,
                "date_parent": ({"row_index": parent["index"], "years_raw": parent["years_raw"],
                                 "years_span": parent["years_span"]} if own is None else None),
            })
    return rows


#: v37.5 (census of the cached list items): an employer line's role lines after a break can each state their own
#: dates -- "[[St. Louis Rams]] (1999–2005)<br />- Offensive coordinator (1999)<br />- Head coach (2000–2005)".
#: Read as one row, every role took the employer's whole span (a head coach in 1999). Such a line becomes its own
#: row, numbered ``employer row index * ROLE_LINE_INDEX_FACTOR + line number``; a role line with no date of its
#: own then inherits the employer line's and names it. A line splits only on a date that states nothing else
#: ("(2012 CFB Champion as Asst. Coach)" is an annotation, not a tenure); references and comments are masked.
ROLE_LINE_INDEX_FACTOR = 100
_LINE_LEAD = re.compile(r"^[\s\-–—•·:]+")
_DATE_ONLY_WORDS = re.compile(
    rf"⟦UDT:[A-Z2-7=]+⟧|\b(?:1[89]\d\d|20\d\d)s?\??|\b\d{{1,2}}\b|\b(?:present|current|today|unknown|c|ca|circa|"
    rf"early|mid|late|after|before|to|and|or)\b\.?|{_MONTH}|[‐‑‒–—−\-,;/&?.'’\s]", re.I)


def _masked(text: str) -> str:
    """``text`` with references and comments blanked to the same length, so positions stay the revision's own."""

    def blank(match: re.Match[str]) -> str:
        return " " * len(match.group(0))

    return _COMMENT.sub(blank, _REF.sub(blank, text))


_SEASON_OF_THE_YEAR = re.compile(r"\b(?:spring|fall|autumn|summer|winter)\b", re.I)


def _words_beside_the_date(value: str) -> str:
    """The date text as displayed, when it also carries words that are not part of a date ("2013–2014; QC -
    Running backs"); empty when it states only a date (a season of the year, "spring", is part of a date)."""

    rendered = html.unescape(plain(value, dates=True))
    left = _SEASON_OF_THE_YEAR.sub(" ", _DATE_ONLY_WORDS.sub(" ", rendered))
    return rendered if re.search(r"[^\W\d_]{2,}", left) else ""


def _is_date_only(value: str) -> bool:
    return _is_date_text(value) and not _words_beside_the_date(value)


def _keep_words_beside_the_date(team: dict[str, Any], date_text: str) -> None:
    """A list line that states no role elsewhere but writes words beside its date ("(1995–1999; GA / DB / LB)")
    does not state "no role": the words are kept verbatim as an unresolved role, and nothing is inferred."""

    words = _words_beside_the_date(date_text)
    if words and team["role_basis"] == "LIST_ROW_STATES_NO_ROLE":
        team["role_basis"] = "UNRESOLVED_PARENTHETICAL"
        team["unresolved_parentheticals"] = list(team["unresolved_parentheticals"]) + [
            {"text": words, "raw": date_text, "basis": "WORDS_BESIDE_THE_DATE_IN_ITS_PARENTHETICAL",
             "expansion": None}]


def _role_lines(body: str) -> list[dict[str, Any]]:
    """Each line after a break in a list item (numbered from 1), with its start in ``body`` and its own date."""

    breaks = list(_BREAK.finditer(body))
    out = []
    for number, found in enumerate(breaks, start=1):
        stop = breaks[number].start() if number < len(breaks) else len(body)
        part = body[found.end():stop]
        lead = _LINE_LEAD.match(part)
        begin = lead.end() if lead else 0
        text = part[begin:].rstrip()
        if not plain(text):
            continue
        own = _own_dates(text)
        employer = None
        if own is not None and text.startswith("[["):
            # A dated line that opens with a link to a football employer is another employer line.
            candidate = parse_team((text[:own[0]] + text[own[1]:]).strip())
            if employer_kind(candidate) in _EMPLOYER_KINDS:
                employer = candidate
        if own is not None and employer is None and not _is_date_only(own[2]):
            own = None
        out.append({"number": number, "start": found.end() + begin, "text": text, "dates": own,
                    "employer": employer})
    return out


_EMPLOYER_KINDS = frozenset({"COLLEGE_OR_OTHER_FOOTBALL_PROGRAM", "PROFESSIONAL", "HIGH_SCHOOL"})


def _balanced(text: str) -> bool:
    depth = 0
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and text.startswith("(") and text.endswith(")")


def career_rows(text: str) -> dict[str, Any]:
    """Every numbered years/team pair in the page's infobox, with spans."""

    boxes = find_infoboxes(text)
    digest = hashlib.sha256(text.encode("utf-8", "surrogateescape")).hexdigest()
    if not boxes:
        return {"parser_version": PARSER_VERSION, "wikitext_sha256": digest, "infobox": None, "infoboxes": [],
                "rows": []}
    pairs: dict[tuple[str, int], dict[str, Param]] = {}
    source_box: dict[tuple[str, int], str] = {}
    for box in boxes:
        for param in box.params:
            match = _PAIR.match(param.name)
            if match:
                family, kind, number = match.group(1).lower(), match.group(2).lower(), int(match.group(3))
                if family in _VARIANT_FIELDS:
                    number += VARIANT_FIELD_INDEX_OFFSET
                slot = pairs.setdefault((family, number), {})
                if kind not in slot:  # the first box that states a pair owns it
                    slot[kind] = param
                    source_box.setdefault((family, number), box.template)
    box = boxes[0]
    rows = []
    for list_box in boxes:
        for param in list_box.params:
            family = LIST_FIELDS.get(param.name)
            if family:
                rows.extend(list_rows(text, param, family, list_box.template))
    for (family, number), both in sorted(pairs.items(), key=lambda item: (item[0][0], item[0][1])):
        years = both.get("years")
        team = both.get("team")
        parsed_team = parse_team(team.value) if team else None
        rows.append({
            "family": FAMILIES[family], "index": number, "infobox": source_box.get((family, number)),
            "years_raw": years.value if years else None,
            "years_span": [years.value_start, years.value_end] if years else None,
            "intervals": parse_years(years.value) if years else [],
            "team_raw": team.value if team else None,
            "team_span": [team.value_start, team.value_end] if team else None,
            "team": parsed_team,
            "employer_kind": employer_kind(parsed_team) if parsed_team else None,
            "date_basis": "YEARS_FIELD" if years else "NO_YEARS_FIELD", "date_parent": None,
        })
    # Wikipedia links an employer at its first occurrence only. A later,
    # unlinked row with the same display text on the same page names the same
    # employer; the link is carried to it and the carry is recorded.
    linked: dict[str, str] = {}
    for row in rows:
        team = row["team"]
        if not team:
            continue
        display = team["employer_display"]
        if team["employer_link_target"]:
            linked.setdefault(display, team["employer_link_target"])
            team["employer_link_basis"] = "LINKED_ON_THIS_ROW"
        elif display in linked:
            team["employer_link_target"] = linked[display]
            team["employer_link_basis"] = "SAME_DISPLAY_LINKED_EARLIER_ON_THIS_PAGE"
            row["employer_kind"] = employer_kind(team)
        else:
            team["employer_link_basis"] = "UNLINKED"
    for row in rows:
        team = row["team"] or {}
        if row["infobox"] in NON_GRIDIRON_TEMPLATES and not str(team.get("employer_link_target") or "").lower() \
                .endswith(" football"):
            row["employer_kind"] = "OTHER_SPORT_PROGRAM"
            row["employer_kind_basis"] = f"row of an Infobox {row['infobox']}"
    return {"parser_version": PARSER_VERSION, "wikitext_sha256": digest, "infobox": box.template,
            "infobox_span": [box.start, box.end], "infoboxes": [b.template for b in boxes], "rows": rows}

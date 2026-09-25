"""One official staff record, reparsed: person, title, roles, sport and span (R37-03).

Four general defects from the Cycle #36 raw review (MF36-16) and AC07-AC10:

* **Name pollution.** A card's link text ("Full Bio", "Opens in a new
  window") was read into the person's name. :func:`clean_person` strips a
  declared list of interface phrases from the ends of a name and records
  what it removed; the raw value is kept beside the clean one.
* **Selector drift.** ``span_locate.bind_person_role`` binds a record when
  the person's name appears anywhere in the record's markup, so an unclosed
  ``<tr>`` whose own person cell names the next coach bound the previous
  one. :func:`bind_record` binds only a record whose *own* person cell names
  the person; a record that names someone else is refused and reported.
  Offsets are given in characters and in bytes of the capture, and the bytes
  at the byte offset are checked against the name.
* **Roles.** The v1.1 taxonomy is kept and corrected where it is wrong in a
  general way: an assistant *to* a coordinator or head coach is not that
  coordinator or an assistant head coach; a coordinator's assistant is not
  the coordinator; a graduate assistant listed with a coordinator title is
  not taken as the principal; an academic advisor is not a consultant. The
  exact title, each normalized role and its principal/co/assistant
  qualifiers are kept separate, qualifiers scoped to the title segment the
  role came from (AC07/AC08).
* **Sport.** A record whose title, section or page belongs to another sport
  is excluded from football role admission before any role is admitted, and
  kept as an observation (AC09).
"""

from __future__ import annotations

import html
import re
from typing import Any, Sequence

from aggie_analytics.cycle33 import role_taxonomy as tax
from aggie_analytics.cycle33 import span_locate
from aggie_analytics.cycle36.source_scoped_season import OTHER_SPORTS
from aggie_analytics.cycle37.staff_season_scope import NON_VARSITY_FOOTBALL

RECORD_VERSION = "BAS-STAFF-RECORD-v37.3"
#: v37.5 (Cycle #37 - Attempt #5, MF37A04-04): units of side-dependent roles come from the side the role's own
#: title segment states, and every role finds its segment through all of its patterns.
TAXONOMY_VERSION = "BAS-COACH-ROLE-TAXONOMY-v37.5-OVER-" + tax.TAXONOMY_VERSION
PREDECESSOR_TAXONOMY_VERSION = "BAS-COACH-ROLE-TAXONOMY-v37.2-OVER-" + tax.TAXONOMY_VERSION

# --------------------------------------------------------------------------
# Person names
# --------------------------------------------------------------------------

#: Interface phrases that are link or button text, never part of a name.
#: A bare "Bio" or "Profile" is not listed: "Bio" is a real surname.
UI_PHRASES = (
    "view full bio", "full bio", "view bio", "read bio", "opens in a new window", "read more", "view profile",
    "e-mail", "email", "twitter", "instagram", "facebook", "linkedin",
)
_UI_END = re.compile(r"(?:\s*[|\-–—:]?\s*(?:" + "|".join(re.escape(p) for p in UI_PHRASES) + r"))+\s*$",
                     re.I)
_UI_START = re.compile(r"^\s*(?:" + "|".join(re.escape(p) for p in UI_PHRASES) + r")\s*[|\-–—:]?\s*",
                       re.I)


#: Link text that never occurs inside a name, so everything from it onward is
#: interface text ("Kai Ross Full Bio Football Support Staff").
_UI_CUT = re.compile(r"\s*[|\-–—:]?\s*\b(?:view\s+full\s+bio|full\s+bio|view\s+bio|read\s+bio|opens\s+in\s+a\s+new"
                     r"\s+window|read\s+more|view\s+profile)\b.*$", re.I)
#: A student staffer's class year after the name ("JP Gourley '25"), also as
#: the upstream parser leaves it with the apostrophe dropped ("Ty Morgan 24").
_CLASS_YEAR = re.compile(r"\s+['’]?\d{2}$")


def clean_person(raw: str) -> tuple[str, list[str]]:
    """The name without interface text, and what was removed."""

    text = re.sub(r"\s+", " ", str(raw or "")).strip()
    removed: list[str] = []
    cut = _UI_CUT.search(text)
    if cut and re.search(r"[A-Za-z]{2}", text[:cut.start()]):
        removed.append(cut.group(0).strip())
        text = text[:cut.start()].strip()
    for pattern in (_UI_END, _UI_START, _CLASS_YEAR):
        match = pattern.search(text)
        if match and match.group(0).strip():
            candidate = (text[:match.start()] + text[match.end():]).strip()
            if re.search(r"[A-Za-z]{2}", candidate):
                removed.append(match.group(0).strip())
                text = candidate
    return text, removed


def fold_name(name: str) -> str:
    """A name without case, punctuation or spacing differences ("O'Daffer" = "ODaffer")."""

    return re.sub(r"[^a-z0-9]+", "", str(name or "").casefold())


def same_person_text(person: str, record_person: str) -> bool:
    """The record's own person text names ``person``: exactly, or up to punctuation."""

    record_clean = clean_person(record_person)[0]
    return span_locate._name_match(person, record_clean) or (
        bool(fold_name(person)) and fold_name(person) == fold_name(record_clean))


# --------------------------------------------------------------------------
# Record binding
# --------------------------------------------------------------------------


def byte_offset(text: str, offset: int | None) -> int | None:
    if offset is None:
        return None
    return len(text[:offset].encode("utf-8", "surrogateescape"))


_TR_START = re.compile(r"<tr\b", re.I)
_TR_END = re.compile(r"</tr\s*>|<tr\b", re.I)


def dom_row_selector(text: str, offset: int | None, person: str) -> dict[str, Any] | None:
    """The row as a DOM reader counts it: the n-th ``<tr`` start tag in the document.

    ``span_locate`` numbers rows by its own regular-expression matches, which
    skip and merge malformed rows, so its ``tr[369]`` is not the 369th row a
    DOM reader sees and resolved to the next person in an independent check.
    This counts start tags, the way a browser does, and says whether the row
    it names contains the person.
    """

    if offset is None:
        return None
    starts = [match.start() for match in _TR_START.finditer(text, 0, offset + 1)]
    if not starts:
        return None
    row_start = starts[-1]
    end_match = _TR_END.search(text, row_start + 3)
    row_end = end_match.start() if end_match else len(text)
    row_text = span_locate._plain(text[row_start:row_end])
    return {"selector": f"tr:nth-start-tag({len(starts) - 1})", "row_char_offset": row_start,
            "row_byte_offset": byte_offset(text, row_start),
            "row_contains_person": span_locate._name_match(person, row_text) or person.lower() in row_text.lower()}


def locate_name(text: str, data: bytes, person: str, start: int, end: int) -> dict[str, Any] | None:
    """The person's own characters inside the record cell, in characters and bytes.

    A cell's recorded start is where its markup begins (whitespace, an anchor
    tag), not where the name is. The name is found inside the cell -- as
    written, or through the entity decoding ``span_locate`` already maps --
    and the file's bytes at that offset are compared with it.
    """

    if not person or end <= start:
        return None
    cell = text[start:end]
    literal = cell.find(person)
    spaced = re.compile(r"(?:\s|&nbsp;|&#160;)+".join(re.escape(token) for token in person.split()), re.I)
    flexible = spaced.search(cell) if literal < 0 else None
    if literal >= 0:
        char_start = start + literal
        char_end = char_start + len(person)
        encoding = "LITERAL"
    elif flexible is not None:
        char_start, char_end = start + flexible.start(), start + flexible.end()
        encoding = "WHITESPACE_OR_NBSP_BETWEEN_NAME_PARTS"
    else:
        located = span_locate.locate_string(cell, person)
        if located is None:
            return {"verified": False, "reason": "name not found in its own cell as written or entity-decoded"}
        char_start = start + int(located["body_offset"])
        char_end = start + int(located.get("body_end_offset") or located["body_offset"] + len(person))
        encoding = "ENTITY_OR_MARKUP_DECODED"
    byte_start, byte_end = byte_offset(text, char_start), byte_offset(text, char_end)
    raw = data[byte_start:byte_end].decode("utf-8", "surrogateescape")
    decoded = re.sub(r"\s+", " ", span_locate._plain(raw) if encoding == "ENTITY_OR_MARKUP_DECODED"
                     else html.unescape(raw).replace("\xa0", " ")).strip()
    return {"char_start": char_start, "char_end": char_end, "byte_start": byte_start, "byte_end": byte_end,
            "encoding": encoding, "verified": decoded.casefold() == person.casefold()
            or span_locate._name_match(person, decoded)}


def bind_record(text: str, data: bytes, person: str, title: str,
                records: Sequence[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Bind the record whose own person cell names ``person``; never a neighbour's."""

    records = list(span_locate.iter_staff_records(text) if records is None else records)
    own = [record for record in records if same_person_text(person, record.get("person") or "")]
    drift = [record for record in records
             if record not in own and span_locate._name_match(person, span_locate._plain(record.get("record_html") or ""))
             and span_locate._name_like(record.get("person") or "")]
    with_title = [record for record in own
                  if title and span_locate.role_claim_supported_on_title(record.get("title") or "", title)]
    chosen = (with_title or own or [None])[0]
    result: dict[str, Any] = {
        "record_version": RECORD_VERSION,
        "records_on_page": len(records),
        "own_person_records": len(own),
        "drift_refused": [{"selector": record.get("selector"), "record_person": record.get("person")}
                          for record in drift[:5]],
    }
    if chosen is None:
        located = span_locate.locate_string(text, person) if person else None
        offset = (located or {}).get("body_offset")
        result.update(state="PERSON_NOT_ON_ITS_OWN_RECORD" if not drift else "REFUSED_RECORD_NAMES_ANOTHER_PERSON",
                      person_record_bound=False, role_claim_supported=False, record_selector=None,
                      record_person=None, record_title=None, char_offset=offset,
                      byte_offset=byte_offset(text, offset), string_located=located is not None)
        return result
    start, end = chosen["person_start"], chosen.get("person_end") or chosen["person_start"]
    evidence = text[start:end]
    start_byte = byte_offset(text, start)
    # The page's own spelling is the name. The upstream parser drops
    # apostrophes ("D'Eriq" -> "DEriq"); when the record's text differs from
    # the parsed name only by punctuation, the record's text is used.
    on_page = clean_person(chosen.get("person") or "")[0]
    if not on_page or fold_name(on_page) != fold_name(person):
        on_page = person
    name = locate_name(text, data, on_page, start, end)
    result.update(person_as_on_page=on_page, person_differs_from_parsed_only_by_punctuation=on_page != person)
    result.update(
        state="BOUND_TO_OWN_RECORD",
        person_record_bound=True,
        role_claim_supported=bool(title) and span_locate.role_claim_supported_on_title(chosen.get("title") or "", title),
        ambiguous_same_person_records=len(own) > 1,
        record_selector=chosen.get("selector"), record_kind=chosen.get("kind"),
        record_person=chosen.get("person"), record_title=chosen.get("title"),
        char_offset=start, char_end=end, byte_offset=start_byte, byte_end=byte_offset(text, end),
        title_char_offset=chosen.get("title_start"), title_byte_offset=byte_offset(text, chosen.get("title_start")),
        evidence_text=evidence[:200],
        dom_row=dom_row_selector(text, start, on_page) if chosen.get("kind") == "table_row" else None,
        name_span=name,
        bytes_at_offset_are_the_name=bool(name and name["verified"]),
        string_located=True,
    )
    return result


_NOT_A_TITLE = re.compile(r"@|https?://|^[\d\s().+/-]*$")


def title_for_row(binding: dict[str, Any], parsed_title: str) -> dict[str, Any]:
    """The title a bound row's roles come from: its own record's, never a neighbour's.

    Cycle 36 read names and titles from parallel lists and on some pages
    zipped them one row out of step, so the parsed title of a correctly bound
    person is the next person's ("Jason Woodman" / "Defensive Coordinator"
    where his own row says "Head Coach"). When the person is bound to their own
    record and that record states a title that disagrees, the record's title is
    used and the parsed title is kept as the predecessor value. A record title
    that is an address, link or number is not a title, and the parsed title
    stays unsupported.
    """

    own = re.sub(r"\s+", " ", str(binding.get("record_title") or "")).strip()
    if binding.get("person_record_bound") and not binding.get("role_claim_supported") and own \
            and re.search(r"[A-Za-z]", own) and not _NOT_A_TITLE.search(own) and len(own) <= 200:
        return {"title": own, "title_source": "OWN_RECORD_TITLE_REPLACES_OUT_OF_STEP_PARSED_TITLE",
                "role_claim_supported": True, "cycle36_title": parsed_title}
    return {"title": parsed_title, "title_source": "PARSED_TITLE_AGREES_WITH_OWN_RECORD"
            if binding.get("role_claim_supported") else "PARSED_TITLE_NOT_SUPPORTED_BY_OWN_RECORD",
            "role_claim_supported": bool(binding.get("role_claim_supported")), "cycle36_title": parsed_title}


# --------------------------------------------------------------------------
# Roles
# --------------------------------------------------------------------------

_SEGMENT_SPLIT = re.compile(r"\s*(?:/|\||;|,|\s[-–—]\s|\s&\s)\s*")
_ASSISTANT_TO_HC = re.compile(
    r"\b(?:special|executive|administrative)?\s*assistant\s+to\s+(?:the\s+)?head(?:\s+football)?\s+coach\b", re.I)
_REAL_AHC = re.compile(r"\b(?:assistant|associate)\s+head(?:\s+football)?\s+coach\b", re.I)
_COORDINATOR_ASSISTANT = re.compile(
    r"\b(offensive|defensive)\s+coord\w*(?:'s)?\s+assistant\b|\bassistant\s+to\s+(?:the\s+)?(offensive|defensive)"
    r"\s+coord", re.I)
_GRADUATE = re.compile(r"\bgraduate\s+assistant\b|\bgrad(?:uate)?\.?\s+asst\b|(?:^|[\s/(-])ga(?:$|[\s/),-])", re.I)
_ACADEMIC_ADVISOR = re.compile(r"\bacademic\s+advis[eo]r\b", re.I)
_OTHER_CONSULTANT = re.compile(r"\bconsultant\b|\b(?<!academic\s)advis[eo]r\b", re.I)

_ROLE_PATTERNS: dict[str, re.Pattern[str]] = {
    tax.ROLE_HC: tax._HC,
    tax.ROLE_OC: re.compile("|".join(p.pattern for p in (tax._OC, tax._CO_OC, tax._DIRECTOR_OFFENSE)), re.I),
    tax.ROLE_DC: re.compile("|".join(p.pattern for p in (tax._DC, tax._CO_DC, tax._DIRECTOR_DEFENSE)), re.I),
}
# v37.5 (MF37A04-04): every pattern that emits a role code finds that role's segment. v37.2 kept only the first
# pattern of each code, so "defensive passing game coordinator" (matched by a later pattern than "pass game
# coordinator") had no segment, its qualifiers were read from the whole title, and nothing tied it to its side.
_ALL_PATTERNS: dict[str, list[str]] = {}
for _pattern, _code, _unit in tax.POSITION_PATTERNS:
    _ALL_PATTERNS.setdefault(_code, []).append(f"(?:{_pattern})")
for _code, _patterns in _ALL_PATTERNS.items():
    _ROLE_PATTERNS.setdefault(_code, re.compile("|".join(_patterns), re.I))
_ROLE_PATTERNS.setdefault("assistant_head_coach", re.compile(r"\b(?:assistant|associate|deputy)\s+head\b", re.I))


def _segment_qualifiers(title: str, role: str) -> tuple[str, str | None, list[str]]:
    segments = [segment for segment in _SEGMENT_SPLIT.split(title) if segment.strip()]
    pattern = _ROLE_PATTERNS.get(role)
    if pattern is None or len(segments) < 2:
        return "TITLE", None, list(tax.extract_qualifiers(title))
    hits = [segment for segment in segments if pattern.search(segment)
            or (role == tax.ROLE_OC and tax._SLASH_OC.search(f" {segment} "))
            or (role == tax.ROLE_DC and tax._SLASH_DC.search(f" {segment} "))]
    if len(hits) != 1:
        return "TITLE", None, list(tax.extract_qualifiers(title))
    return "SEGMENT", hits[0].strip(), list(tax.extract_qualifiers(hits[0]))


# --------------------------------------------------------------------------
# Units (v37.5, MF37A04-04)
# --------------------------------------------------------------------------

#: Roles whose side of the ball is not part of the role itself: a pass-game coordinator, a quality-control coach,
#: an analyst or a graduate assistant can work for the offense, the defense or the special teams. The v1.1
#: taxonomy gave "passing game coordinator" a fixed OFFENSE and the others a fixed UNKNOWN; the title's own words
#: decide instead. Every other role keeps its intrinsic unit (quarterbacks are offense, safeties defense).
SIDE_DEPENDENT_ROLES = frozenset({
    "pass_game_coordinator", "run_game_coordinator", "quality_control", "analyst", "graduate_assistant",
    "assistant_unspecified", "intern_or_student_assistant", "student_assistant", "consultant", "volunteer_coach",
})
_SIDES = (
    ("DEFENSE", re.compile(r"\bdefen[cs]ive\b|\bdefen[cs]e\b|\bdef\.|\bdef\b", re.I)),
    ("OFFENSE", re.compile(r"\boffensive\b|\boffense\b|\boff\.|\boff\b", re.I)),
    ("SPECIAL_TEAMS", re.compile(r"\bspecial[\s-]+teams?\b|\bkicking\s+game\b", re.I)),
)
#: Words that end the phrase a side word can modify ("offensive line coach and run game coordinator": the run
#: game coordinator is not thereby offensive).
_PHRASE_BREAK = re.compile(r"\band\b|&|,|/|;|\||\bwith\b|\bplus\b", re.I)
_SIDE_WORD = r"(?:defen[cs]ive|defen[cs]e|offensive|offense|special[\s-]+teams?)"
#: What may follow a role within its segment and still be only its side: "(Defense)", "coach - offense".
_TRAILING_SIDE = re.compile(rf"\s*(?:coach(?:es)?|assistant)?\s*[(\-–—:]?\s*{_SIDE_WORD}\s*\)?\s*", re.I)
#: A whole segment that is only a side ("Graduate Assistant - Offense" splits into two segments).
_SIDE_ONLY = re.compile(rf"\(?\s*{_SIDE_WORD}\s*\)?", re.I)
UNIT_BASES = ("INTRINSIC_ROLE_UNIT", "SIDE_STATED_FOR_THE_ROLE", "SIDE_NOT_STATED_FOR_THE_ROLE",
              "BOTH_SIDES_STATED_FOR_THE_ROLE")


def unit_for(title: str, role: str, base_unit: str) -> dict[str, Any]:
    """The unit an assignment states, with its basis and the words it rests on.

    A side-dependent role takes the side only from words that directly modify it: the text between the previous
    phrase break in its own title segment and the role's own words ("Special teams / defensive passing game
    coordinator" -> DEFENSE; "Cornerbacks coach & defensive passing game coordinator" -> DEFENSE; "Pass game
    coordinator & quarterbacks coach" -> UNKNOWN, because nothing modifies the coordinator). A side is never
    borrowed from another role in the title, and no play-calling authority is inferred.
    """

    if role not in SIDE_DEPENDENT_ROLES:
        return {"unit": base_unit, "unit_basis": "INTRINSIC_ROLE_UNIT", "unit_words": None}
    pattern = _ROLE_PATTERNS.get(role)
    raw = re.sub(r"\s+", " ", str(title or "")).strip()
    sides: set[str] = set()
    words: list[str] = []
    segments = [s for s in _SEGMENT_SPLIT.split(raw) if s.strip()]
    for position, segment in enumerate(segments):
        match = pattern.search(segment) if pattern is not None else None
        if match is None:
            continue
        before = segment[:match.start()]
        breaks = list(_PHRASE_BREAK.finditer(before))
        modifier = before[breaks[-1].end():] if breaks else before
        # Coordinated sides modify the role together ("Offensive and defensive quality control"): walk back over
        # earlier phrases that are nothing but a side word.
        while breaks:
            last = breaks.pop()
            previous_start = breaks[-1].end() if breaks else 0
            chunk = before[previous_start:last.start()]
            if not _SIDE_ONLY.fullmatch(chunk.strip()):
                break
            modifier = before[previous_start:last.end()] + modifier
        # A side written directly after the role ("Analyst (Defense)"), or as the whole next segment
        # ("Graduate Assistant - Offense"), states it as plainly as one written before it.
        after = segment[match.end():]
        cut = _PHRASE_BREAK.search(after)
        after = after[:cut.start()] if cut else after
        trailing = after if _TRAILING_SIDE.fullmatch(after) else ""
        following = segments[position + 1] if position + 1 < len(segments) else ""
        next_side = following if _SIDE_ONLY.fullmatch(following.strip()) else ""
        phrase = modifier + match.group(0) + trailing + (f" | {next_side}" if next_side else "")
        stated = {side for side, side_pattern in _SIDES if side_pattern.search(phrase)}
        sides |= stated
        words.append(phrase.strip())
    if len(sides) == 1:
        return {"unit": next(iter(sides)), "unit_basis": "SIDE_STATED_FOR_THE_ROLE", "unit_words": words}
    if len(sides) > 1:
        return {"unit": "UNKNOWN", "unit_basis": "BOTH_SIDES_STATED_FOR_THE_ROLE", "unit_words": words}
    return {"unit": "UNKNOWN", "unit_basis": "SIDE_NOT_STATED_FOR_THE_ROLE", "unit_words": words or None}


_EXECUTIVE_DIRECTOR_OF_FOOTBALL = re.compile(r"\bexecutive\s+director\s+of\s+football\b(?!\s+operations)", re.I)
_HEAD_COACH_AT_END = re.compile(r"\bhead(?:\s+football)?\s+coach\s*$", re.I)
#: A head coach of a sub-team is not the program's head coach ("freshman head coach").
_SUB_TEAM = re.compile(r"\b(?:freshman|freshmen|frosh|jv|junior\s+varsity|b-team|scout\s+team|youth|middle\s+school|"
                       r"high\s+school|club|intramural|practice\s+squad)\b", re.I)


def _head_coach_corrections(raw: str, base: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Two general head-coach defects of the v1.1 title-level reading (R37-03, found reconciling R35-02).

    * A qualifier in *another* segment disqualified the head coach: "Head
      Football Coach / Sr. Associate Athletic Director" read as an assistant
      head coach because "Associate" appears anywhere in the title. When one
      segment alone is a principal head-coach title and no segment alone is an
      assistant/associate head coach, the head coach is principal.
    * "Executive Director of Football" read as head coach: v1.1 lists it among
      the non-head-coach titles, but in a verbose pattern whose spaces are
      dropped, so the exclusion never matches. It is an administrative
      football role, not the head coach.
    """

    segments = [segment.strip() for segment in _SEGMENT_SPLIT.split(raw) if segment.strip()]
    roles = {item["role"]: item for item in base}
    out = list(base)
    if _EXECUTIVE_DIRECTOR_OF_FOOTBALL.search(raw) and not re.search(r"\bhead\b", raw, re.I):
        # No "head" anywhere: every head-coach reading came from "director of
        # football" inside "Executive Director of Football".
        artefacts = [item for item in out if item["role"] in (tax.ROLE_HC, "assistant_head_coach")
                     or (item["role"] == "unmapped_title_review_required"
                         and item["occupancy"] == "QUALIFIED_NOT_PRINCIPAL")]
        if artefacts:
            out = [item for item in out if item not in artefacts]
            out.append({**artefacts[0], "role": "football_operations", "unit": "TEAM", "occupancy": "OBSERVED",
                        "v37_correction": "EXECUTIVE_DIRECTOR_OF_FOOTBALL_IS_NOT_HEAD_COACH"})
            return out
    if len(segments) < 2 or (tax.ROLE_HC in roles and roles[tax.ROLE_HC]["occupancy"] == "PRINCIPAL"):
        return out
    # The segment must end in its head-coach noun ("Head Football Coach"); a
    # segment such as "Head Coach Logistics" names something else.
    principal_segments = [s for s in segments if tax._principal_hc(s) and _HEAD_COACH_AT_END.search(s)
                          and not _EXECUTIVE_DIRECTOR_OF_FOOTBALL.search(s) and not _SUB_TEAM.search(s)]
    assistant_segments = [s for s in segments
                          if any(a["role"] == "assistant_head_coach" for a in tax.assignments_from_title(s))]
    if len(principal_segments) == 1 and not assistant_segments:
        segment = principal_segments[0]
        out = [item for item in out if not (item["role"] in ("assistant_head_coach", "unmapped_title_review_required")
                                             and item["occupancy"] == "QUALIFIED_NOT_PRINCIPAL")]
        out.insert(0, {"role": tax.ROLE_HC, "unit": "TEAM", "occupancy": "PRINCIPAL",
                       "qualifiers": list(tax.extract_qualifiers(segment)),
                       "v37_correction": "HEAD_COACH_WAS_QUALIFIED_ONLY_BY_ANOTHER_SEGMENT"})
    return out


def assignments_v37(title: str) -> list[dict[str, Any]]:
    """v1.1 assignments with the declared general corrections and scoped qualifiers."""

    raw = re.sub(r"\s+", " ", str(title or "")).strip()
    base = _head_coach_corrections(raw, tax.assignments_from_title(raw))
    out: list[dict[str, Any]] = []
    for item in base:
        role, occupancy, correction = item["role"], item["occupancy"], item.get("v37_correction")
        if role == "assistant_head_coach" and _ASSISTANT_TO_HC.search(raw) and not _REAL_AHC.search(raw):
            role, occupancy = "administrative_staff", "OBSERVED"
            correction = "ASSISTANT_TO_THE_HEAD_COACH_IS_SUPPORT_NOT_ASSISTANT_HEAD_COACH"
        elif role in (tax.ROLE_OC, tax.ROLE_DC) and occupancy in ("PRINCIPAL", "CO_SHARED"):
            side = "offensive" if role == tax.ROLE_OC else "defensive"
            match = _COORDINATOR_ASSISTANT.search(raw)
            if match and side in {(match.group(1) or "").lower(), (match.group(2) or "").lower()}:
                occupancy = "QUALIFIED_NOT_PRINCIPAL"
                correction = "ASSISTANT_TO_A_COORDINATOR_IS_NOT_THE_COORDINATOR"
            elif _GRADUATE.search(raw):
                occupancy = "QUALIFIED_NOT_PRINCIPAL"
                correction = "GRADUATE_ASSISTANT_WITH_A_COORDINATOR_TITLE_IS_NOT_TAKEN_AS_PRINCIPAL"
        elif role == "consultant" and _ACADEMIC_ADVISOR.search(raw) and not _OTHER_CONSULTANT.search(raw):
            continue  # "Academic Advisor" is academic staff, which v1.1 also emits
        if any(existing["role"] == role for existing in out):
            continue
        scope, segment, segment_qualifiers = _segment_qualifiers(raw, role)
        unit = unit_for(raw, role, item["unit"])
        out.append({
            "role": role, "unit": unit["unit"], "occupancy": occupancy,
            "title_qualifiers": list(item["qualifiers"]), "qualifier_scope": scope, "segment": segment,
            "segment_qualifiers": segment_qualifiers, "taxonomy_correction": correction,
            "source_title": raw, "taxonomy_version": TAXONOMY_VERSION, "play_caller_inferred": False,
            "unit_basis": unit["unit_basis"], "unit_words": unit["unit_words"], "base_unit": item["unit"],
        })
    if not any(item["role"] == "academic_staff" for item in out) and _ACADEMIC_ADVISOR.search(raw):
        out.append({"role": "academic_staff", "unit": "TEAM", "occupancy": "OBSERVED",
                    "title_qualifiers": list(tax.extract_qualifiers(raw)), "qualifier_scope": "TITLE", "segment": None,
                    "segment_qualifiers": list(tax.extract_qualifiers(raw)),
                    "taxonomy_correction": "ACADEMIC_ADVISOR_IS_ACADEMIC_STAFF", "source_title": raw,
                    "taxonomy_version": TAXONOMY_VERSION, "play_caller_inferred": False,
                    "unit_basis": "INTRINSIC_ROLE_UNIT", "unit_words": None, "base_unit": "TEAM"})
    return out


# --------------------------------------------------------------------------
# Sport
# --------------------------------------------------------------------------

_OTHER = re.compile(r"\b(?:" + OTHER_SPORTS + r")\b", re.I)
_FOOTBALL = re.compile(r"\bfootball\b", re.I)
#: Football as multi-sport titles abbreviate it: "(FB, WBB, BSB)".
_FOOTBALL_IN_TITLE = re.compile(r"\bfootball\b|\bfb\b|\bfball\b", re.I)
#: URL path slugs athletics platforms use for sports.
FOOTBALL_SLUGS = frozenset({"football", "fball", "fb", "m-footbl", "mfootball"})
OTHER_SPORT_SLUGS = frozenset({
    "mbkb", "wbkb", "mbball", "wbball", "mens-basketball", "womens-basketball", "basketball", "baseball", "bsb",
    "softball", "sball", "volleyball", "wvball", "vball", "msoc", "wsoc", "mens-soccer", "womens-soccer", "soccer",
    "mten", "wten", "mens-tennis", "womens-tennis", "mgolf", "wgolf", "mens-golf", "womens-golf", "wrestling",
    "wrest", "mswim", "wswim", "swimming-and-diving", "track-and-field", "mtrack", "wtrack", "xc", "cross-country",
    "mlax", "wlax", "mens-lacrosse", "womens-lacrosse", "field-hockey", "fhockey", "mhockey", "whockey",
    "ice-hockey", "gymnastics", "wgym", "rowing", "bowling", "rifle", "equestrian", "beach-volleyball",
    "sprint-football", "sprintfb", "flag-football",
})


def _url_sports(url: str | None) -> tuple[bool, bool]:
    path = re.sub(r"^[a-z]+://[^/]+", "", str(url or "").lower())
    slugs = set(re.findall(r"[a-z0-9-]+", path))
    return bool(slugs & FOOTBALL_SLUGS), bool(slugs & OTHER_SPORT_SLUGS)


def sport_scope(title: str, section_state: str | None, page_url: str | None, page_title: str | None) -> dict[str, Any]:
    """FOOTBALL, OTHER_SPORT or UNSPECIFIED, decided before any role is admitted."""

    title = str(title or "")
    varsity_title = NON_VARSITY_FOOTBALL.sub(" ", title)
    if _FOOTBALL_IN_TITLE.search(varsity_title):
        return {"scope": "FOOTBALL", "basis": "TITLE_NAMES_FOOTBALL", "football_role_admissible": True}
    if _OTHER.search(title) or NON_VARSITY_FOOTBALL.search(title):
        return {"scope": "OTHER_SPORT", "basis": "TITLE_NAMES_ANOTHER_SPORT", "football_role_admissible": False}
    if section_state == "OTHER_SPORT_SECTION":
        return {"scope": "OTHER_SPORT", "basis": "RECORD_IN_ANOTHER_SPORT_SECTION", "football_role_admissible": False}
    football_url, other_url = _url_sports(page_url)
    if other_url and not football_url:
        return {"scope": "OTHER_SPORT", "basis": "PAGE_URL_IS_ANOTHER_SPORT", "football_role_admissible": False}
    page = str(page_title or "")
    varsity_page = NON_VARSITY_FOOTBALL.sub(" ", page)
    if (_OTHER.search(page) or NON_VARSITY_FOOTBALL.search(page)) and not _FOOTBALL.search(varsity_page) \
            and not football_url:
        return {"scope": "OTHER_SPORT", "basis": "PAGE_TITLE_IS_ANOTHER_SPORT", "football_role_admissible": False}
    if football_url or _FOOTBALL.search(varsity_page) or section_state == "FOOTBALL_SECTION" \
            or _FOOTBALL.search(varsity_title):
        return {"scope": "FOOTBALL", "basis": "FOOTBALL_STATED_BY_PAGE_SECTION_OR_TITLE",
                "football_role_admissible": True}
    return {"scope": "UNSPECIFIED", "basis": "NO_SPORT_STATED", "football_role_admissible": True}

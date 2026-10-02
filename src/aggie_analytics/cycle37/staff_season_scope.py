"""Record-scoped staff season authority, Cycle #37 successor (R37-03 AC06).

MF36-02 reproduced seven cases against the Cycle #36 binder
(:mod:`aggie_analytics.cycle36.source_scoped_season`). It bound 2026 from an
announcement about another person, from a fundraiser "announced" on a date,
through a basketball subsection nested under a football heading, and from a
heading inside a ``hidden`` element; it bound a December 2025 appointment
"to lead the team beginning in 2026" to 2025; and it refused a 1999 staff
heading because its year range started in 2000. This module keeps the
Cycle #36 structure -- a season must come from rendered text that governs the
record -- and repairs each of those general failures:

* **Visible.** An element carrying ``hidden``, ``aria-hidden="true"``,
  ``display:none``/``visibility:hidden`` or a screen-reader-only class is not
  rendered to a reader, so nothing inside it labels anything.
* **Football.** A record is dated by a heading only if no heading between
  that heading and the record names another sport. A record inside another
  sport's section is reported as such, and never gets a football season.
* **Bounded to the person and the role.** A dated announcement dates a record
  only when its own sentence states an appointment (a role verb and a role
  noun) and names the record's person, whose surname no other record on the
  page shares.
* **Effective season, not announcement date.** A season is bound from an
  announcement only when the sentence *states* the season the role serves
  ("beginning in 2026", "for the 2026 season"). An announcement date alone is
  kept as ``announcement_date`` and binds nothing: a December hire may serve
  the next season, and choosing is a guess.
* **Supported range 1963-2026.** A staff heading from 1999 is a real label.
  A year outside the range is not a staff season.
* **No borrowing.** Schedule and generic "season" headings, footers, sidebars
  and navigation never date a staff record; only a staff or football-roster
  heading does.

``known_at`` is never derived here. A season the source states is the
source-effective season; when the bytes demonstrably existed is a separate
fact this module does not have.
"""

from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass
from typing import Any, Sequence

from aggie_analytics.cycle36 import source_scoped_season as base

PARSER_VERSION = "BAS-STAFF-SEASON-SCOPE-v37.2"
SEASON_RANGE = (1963, 2026)
_YEAR = r"(19[6-9]\d|20[0-2]\d)"

#: A staff heading: the year (or an academic year such as "2026-27", whose
#: football season is the first year), up to two words such as a nickname
#: ("2026 Cowboy Football Staff"), and a football staff phrase including the
#: support staff. The R37-03 blind sample found these real headings unread.
STAFF_LABEL = re.compile(
    r"\b" + _YEAR + r"(?:\s*[-–/]\s*\d{2,4})?\s+(?:[A-Z][\w'’.&-]*\s+){0,2}?"
    r"(?:football\s+(?:coaching\s+|support\s+|operations\s+|recruiting\s+)?staff(?:\s+directory)?"
    r"|coaching\s+staff|staff\s+directory|football\s+coaches)\b",
    re.I,
)
ROSTER_LABEL = re.compile(r"\b" + _YEAR + r"\s+football\s+roster\b", re.I)

_MONTHS = r"january|february|march|april|may|june|july|august|september|october|november|december"
DATE = re.compile(r"\b(" + _MONTHS + r")\s+(\d{1,2}),\s*" + _YEAR + r"\b", re.I)
#: Verbs that state an employment by themselves.
APPOINTMENT_VERB = re.compile(r"\b(?:hired|appointed|promoted|elevated)\b", re.I)
#: Verbs that also name honours ("named to the All-America team"), so they
#: count only beside a role noun or "lead the team/program".
WEAK_VERB = re.compile(r"\b(?:named|tabbed|selected|announced\s+as)\b", re.I)
ROLE_NOUN = re.compile(r"\b(?:coach|coordinator|director|analyst|assistant|staff|manager|coaching)\b"
                       r"|\blead\s+the\s+(?:team|program|football\s+program)\b", re.I)


def _states_appointment(sentence: str) -> bool:
    return bool(APPOINTMENT_VERB.search(sentence) or (WEAK_VERB.search(sentence) and ROLE_NOUN.search(sentence)))
EFFECTIVE = re.compile(
    r"\b(?:for|beginning(?:\s+(?:in|with))?|starting(?:\s+(?:in|with))?|effective(?:\s+(?:for|with))?"
    r"|ahead\s+of|entering)\s+(?:the\s+)?" + _YEAR + r"(?:\s+(?:season|campaign))?\b",
    re.I,
)

HIDDEN_CLASS_TOKENS = frozenset({
    "sr-only", "visually-hidden", "screen-reader-text", "screen-reader-only", "hidden", "d-none", "is-hidden",
    "hide", "invisible", "u-hidden", "offscreen", "element-invisible",
})
_HIDDEN_STYLE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.I)
_FOOTBALL = re.compile(r"\bfootball\b", re.I)
_OTHER_SPORT = re.compile(r"\b(?:" + base.OTHER_SPORTS + r")\b", re.I)
#: Football that is not the varsity program. "Sprint Football" contains the
#: word football but is another sport (R37-03 held-out record 55: an Army
#: West Point "Sprint Football" table read as football).
NON_VARSITY_FOOTBALL = re.compile(r"\b(?:sprint|flag|lightweight|arena|indoor)\s+football\b", re.I)
_TAG = re.compile(r"<[^>]*>")


def names_varsity_football(text: str) -> bool:
    """Whether ``text`` names football other than sprint, flag or arena football."""

    return bool(_FOOTBALL.search(NON_VARSITY_FOOTBALL.sub(" ", str(text or ""))))


def names_other_sport(text: str) -> bool:
    """Whether ``text`` names another sport (sprint football included) and not varsity football."""

    text = str(text or "")
    return bool(_OTHER_SPORT.search(text) or NON_VARSITY_FOOTBALL.search(text)) and not names_varsity_football(text)

BOUND_HEADING = base.BOUND_HEADING
BOUND_STATED = "SEASON_BOUND_BY_SOURCE_STATED_EFFECTIVE_SEASON"
UNBOUND_NO_ADMISSIBLE = base.UNBOUND_NO_ADMISSIBLE
UNBOUND_OUT_OF_SCOPE = base.UNBOUND_OUT_OF_SCOPE
UNBOUND_CONFLICT = base.UNBOUND_CONFLICT
UNBOUND_OTHER_SPORT = "UNBOUND_RECORD_IN_ANOTHER_SPORT_SECTION"
UNBOUND_DATE_ONLY = "UNBOUND_ANNOUNCEMENT_DATE_WITHOUT_STATED_SEASON"
UNBOUND_NOT_LOCATED = "UNBOUND_RECORD_NOT_LOCATED"
STATES = (BOUND_HEADING, BOUND_STATED, UNBOUND_NO_ADMISSIBLE, UNBOUND_OUT_OF_SCOPE, UNBOUND_CONFLICT,
          UNBOUND_OTHER_SPORT, UNBOUND_DATE_ONLY, UNBOUND_NOT_LOCATED)
BOUND_STATES = frozenset({BOUND_HEADING, BOUND_STATED})

CTX_HIDDEN = "HIDDEN_NOT_RENDERED"


def _is_hidden(attrs: Sequence[tuple[str, str | None]]) -> bool:
    for name, value in attrs:
        name = (name or "").lower()
        text = str(value or "")
        if name == "hidden":
            return True
        if name == "aria-hidden" and text.strip().lower() == "true":
            return True
        if name == "style" and _HIDDEN_STYLE.search(text):
            return True
        if name == "class" and HIDDEN_CLASS_TOKENS.intersection(text.lower().split()):
            return True
    return False


class _Scanner(base._DocumentScanner):
    """The Cycle #36 scanner with hidden subtrees treated as not rendered."""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:  # noqa: D102
        tag = tag.lower()
        start = self._offset()
        self.spans.append(base.Span(start, start, "TAG", tag, len(self._stack), self._ancestors()))
        non_rendered = tag in base.NON_RENDERED_ELEMENTS or _is_hidden(attrs)
        chrome = self._is_chrome(tag, attrs)
        prose = tag in base.PROSE_ELEMENTS
        if tag in {"br", "hr", "img", "input", "meta", "link", "source", "wbr", "area", "col", "embed", "param",
                   "track"}:
            return
        inherited_hidden = self._in_non_rendered()
        self._stack.append((tag, non_rendered, chrome, prose))
        rank = self._heading_rank(tag, attrs)
        if rank is not None and not non_rendered and not inherited_hidden and self._open_heading is None:
            self._open_heading = base.HeadingSection(start=start, text_start=start, end=start, rank=rank,
                                                     tag=tag, text="")
            self._heading_text = []


@dataclass
class Label:
    season: int
    matched_text: str
    offset: int
    end: int
    kind: str
    heading_index: int
    scope_start: int
    scope_end: int

    def as_dict(self) -> dict[str, Any]:
        return {"season": self.season, "matched_text": self.matched_text[:160], "offset": self.offset,
                "end": self.end, "kind": self.kind, "governs_from": self.scope_start, "governs_to": self.scope_end}


@dataclass
class Rejected:
    season: int
    matched_text: str
    offset: int
    kind: str
    context: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {"season": self.season, "matched_text": self.matched_text[:160], "offset": self.offset,
                "kind": self.kind, "context": self.context, "reason": self.reason}


@dataclass
class Scanned:
    text: str
    base_scan: base.ScannedCapture
    headings: list[base.HeadingSection]
    labels: list[Label]
    rejected: list[Rejected]
    parse_error: str | None

    def context_at(self, offset: int) -> str:
        context, _ = self.base_scan.context_at(offset)
        return context


def _heading_names_other_sport(heading: base.HeadingSection) -> bool:
    return names_other_sport(heading.text)


def table_header(text: str, offset: int) -> str | None:
    """The caption and header row of the table the record sits in, as plain text.

    A staff directory often lists several sports in one page with no heading
    between them; the only statement of the sport is the table's own header
    ("Sprint Football | @ArmyWP_SprintFB | Name | Title"). ``None`` when the
    record is not inside a table.
    """

    lower = text.lower()
    start = lower.rfind("<table", 0, offset)
    if start < 0:
        return None
    close = lower.find("</table", start)
    if 0 <= close < offset:
        return None
    body = text[start:offset]
    parts = [m.group(1) for m in re.finditer(r"<caption\b[^>]*>(.*?)</caption\s*>", body, re.I | re.S)]
    head = re.search(r"<thead\b[^>]*>(.*?)</thead\s*>", body, re.I | re.S)
    if head:
        parts.append(head.group(1))
    else:
        first = re.search(r"<tr\b[^>]*>(.*?)</tr\s*>", body, re.I | re.S)
        if first and re.search(r"<th\b", first.group(1), re.I) and not re.search(r"<td\b", first.group(1), re.I):
            parts.append(first.group(1))
    plain = re.sub(r"\s+", " ", html_lib.unescape(_TAG.sub(" ", " ".join(parts)))).strip()
    return plain or None


def scan(text: str) -> Scanned:
    """Parse once; classify every season-label match by where it sits."""

    scanner = _Scanner()
    parse_error = None
    try:
        scanner.feed_document(text)
    except Exception as error:  # pragma: no cover - malformed real markup
        parse_error = f"{type(error).__name__}: {error}"
    base_scan = base.ScannedCapture(text=text, spans=scanner.spans, headings=scanner.headings, candidates=[],
                                    parse_error=parse_error)
    labels: list[Label] = []
    rejected: list[Rejected] = []
    low, high = SEASON_RANGE
    for pattern, kind in ((STAFF_LABEL, "STAFF_SEASON_LABEL"), (ROSTER_LABEL, "FOOTBALL_ROSTER_SEASON_LABEL")):
        for match in pattern.finditer(text):
            year = int(match.group(1))
            if not low <= year <= high:
                continue
            context, _ = base_scan.context_at(match.start())
            reason = {
                base.CTX_SCRIPT: "inside a script, style, template or hidden element, not rendered",
                base.CTX_COMMENT: "inside an HTML comment, not published",
                base.CTX_ATTRIBUTE: "inside a tag attribute value, not rendered text",
                base.CTX_CHROME: "inside navigation, menu, breadcrumb, sidebar or footer",
                base.CTX_PROSE: "in running prose, which describes rather than labels",
            }.get(context)
            heading_index = base._heading_for(scanner.headings, match.start()) if reason is None else -1
            if reason is None and heading_index < 0:
                context, reason = base.CTX_OTHER_RENDERED, "rendered but not inside a heading, caption or title"
            # The heading's own text decides its sport. A character window
            # around the year reaches into the next heading and borrowed a
            # "Basketball" subsection title for the football label above it.
            if reason is None and _heading_names_other_sport(scanner.headings[heading_index]):
                context, reason = base.CTX_OTHER_SPORT, "the heading labels another sport's section"
            if reason is not None:
                rejected.append(Rejected(year, match.group(0).strip(), match.start(), kind, context, reason))
                continue
            heading = scanner.headings[heading_index]
            labels.append(Label(year, match.group(0).strip(), match.start(), match.end(), kind, heading_index,
                                heading.start, heading.scope_end))
    labels.sort(key=lambda label: label.offset)
    return Scanned(text, base_scan, scanner.headings, labels, rejected, parse_error)


def heading_chain(scanned: Scanned, offset: int) -> list[int]:
    """Indexes of the headings whose scope contains ``offset``, outermost first."""

    chain = [index for index, heading in enumerate(scanned.headings)
             if heading.start <= offset < heading.scope_end]
    chain.sort(key=lambda index: (scanned.headings[index].rank, scanned.headings[index].start))
    return chain


def record_sport_section(scanned: Scanned, offset: int | None) -> dict[str, Any]:
    """Whether the innermost section containing the record names another sport."""

    if offset is None:
        return {"state": "RECORD_NOT_LOCATED", "heading": None}
    # The record's own table is the innermost section it can be in.
    header = table_header(scanned.text, offset)
    if header and names_other_sport(header):
        return {"state": "OTHER_SPORT_SECTION", "heading": f"table header: {header[:150]}"}
    if header and names_varsity_football(header):
        return {"state": "FOOTBALL_SECTION", "heading": f"table header: {header[:150]}"}
    chain = heading_chain(scanned, offset)
    for index in reversed(chain):
        heading = scanned.headings[index]
        if names_varsity_football(heading.text):
            return {"state": "FOOTBALL_SECTION", "heading": heading.text[:160]}
        if _heading_names_other_sport(heading):
            return {"state": "OTHER_SPORT_SECTION", "heading": heading.text[:160]}
    return {"state": "NO_SPORT_NAMED_BY_ANY_GOVERNING_HEADING", "heading": None}


def _sentence(text: str, offset: int, end: int) -> tuple[str, int]:
    left = max(text.rfind(".", 0, offset), text.rfind("<", 0, offset), text.rfind(">", 0, offset))
    right_candidates = [pos for pos in (text.find(".", end), text.find("<", end)) if pos >= 0]
    right = min(right_candidates) if right_candidates else len(text)
    return text[left + 1:right], left + 1


def _surname(person: str) -> str:
    tokens = [token for token in re.split(r"[^A-Za-z'\-]+", person or "") if token]
    tokens = [token for token in tokens if token.lower().rstrip(".") not in {"jr", "sr", "ii", "iii", "iv", "v"}]
    return tokens[-1] if tokens else ""


def announcements(scanned: Scanned, person: str | None) -> list[dict[str, Any]]:
    """Rendered appointment sentences that name ``person``, each with its date and stated season."""

    if not person:
        return []
    surname = _surname(person)
    if len(surname) < 2:
        return []
    found: list[dict[str, Any]] = []
    for match in DATE.finditer(scanned.text):
        context = scanned.context_at(match.start())
        if context not in (base.CTX_PROSE, base.CTX_OTHER_RENDERED):
            continue
        sentence, origin = _sentence(scanned.text, match.start(), match.end())
        if not _states_appointment(sentence):
            continue
        if not re.search(r"\b" + re.escape(surname) + r"\b", sentence):
            continue
        stated = [int(m.group(1)) for m in EFFECTIVE.finditer(sentence)
                  if SEASON_RANGE[0] <= int(m.group(1)) <= SEASON_RANGE[1]]
        found.append({"sentence": re.sub(r"\s+", " ", sentence).strip()[:300], "offset": origin,
                      "announcement_date": f"{match.group(3)}-{match.group(1).title()}-{int(match.group(2)):02d}",
                      "stated_effective_seasons": sorted(set(stated))})
    return found


def season_for_record(scanned: Scanned, record_offset: int | None, *, person: str | None = None,
                      surname_shared_on_page: bool = False) -> dict[str, Any]:
    """Bind a season for one located staff record, or say exactly why not."""

    evidence: dict[str, Any] = {
        "parser_version": PARSER_VERSION, "record_offset": record_offset,
        "admissible_label_count": len(scanned.labels), "rejected_label_count": len(scanned.rejected),
        "labels": [label.as_dict() for label in scanned.labels[:20]],
        "rejected": [item.as_dict() for item in scanned.rejected[:20]],
        "source_effective_season": None, "announcement_date": None, "known_at": None,
    }
    if scanned.parse_error:
        evidence["parse_error"] = scanned.parse_error
    if record_offset is None:
        evidence.update(state=UNBOUND_NOT_LOCATED, bound_season=None,
                        detail="The record was not located in the capture, so nothing can be shown to govern it.")
        return evidence
    sport = record_sport_section(scanned, record_offset)
    evidence["sport_section"] = sport
    if sport["state"] == "OTHER_SPORT_SECTION":
        evidence.update(state=UNBOUND_OTHER_SPORT, bound_season=None,
                        detail=f"The record sits under the heading {sport['heading']!r}, another sport's section.")
        return evidence

    stated = [] if surname_shared_on_page else announcements(scanned, person)
    evidence["announcements"] = stated[:5]
    stated_seasons = sorted({season for item in stated for season in item["stated_effective_seasons"]})

    chain = set(heading_chain(scanned, record_offset))
    governing = [label for label in scanned.labels
                 if label.heading_index in chain and label.offset <= record_offset]
    if governing:
        innermost_rank = max(scanned.headings[label.heading_index].rank for label in governing)
        tightest = [label for label in governing if scanned.headings[label.heading_index].rank == innermost_rank]
        nearest = max(label.heading_index for label in tightest)
        tightest = [label for label in tightest if label.heading_index == nearest]
        seasons = sorted({label.season for label in tightest})
        if len(seasons) > 1:
            evidence.update(state=UNBOUND_CONFLICT, bound_season=None, conflicting_seasons=seasons,
                            detail=f"The governing heading states {seasons}; choosing one would be a guess.")
            return evidence
        label = tightest[0]
        evidence.update(state=BOUND_HEADING, bound_season=label.season, source_effective_season=label.season,
                        bound_by=label.as_dict(),
                        detail=(f"The record at offset {record_offset} is inside the section headed "
                                f"{label.matched_text!r}, with no other sport's heading between them."))
        if stated_seasons and stated_seasons != [label.season]:
            evidence["announcement_disagrees_with_heading"] = stated_seasons
        return evidence

    if len(stated_seasons) == 1:
        evidence.update(state=BOUND_STATED, bound_season=stated_seasons[0], source_effective_season=stated_seasons[0],
                        announcement_date=stated[0]["announcement_date"],
                        detail=("An appointment sentence naming this person states the season the role serves; "
                                "the announcement date is kept separately."))
        return evidence
    if len(stated_seasons) > 1:
        evidence.update(state=UNBOUND_CONFLICT, bound_season=None, conflicting_seasons=stated_seasons,
                        detail="Appointment sentences naming this person state different seasons.")
        return evidence
    if stated:
        evidence.update(state=UNBOUND_DATE_ONLY, bound_season=None, announcement_date=stated[0]["announcement_date"],
                        detail=("An appointment sentence names this person and a date but states no season; a "
                                "date is not a season."))
        return evidence
    if scanned.labels:
        evidence.update(state=UNBOUND_OUT_OF_SCOPE, bound_season=None,
                        detail="Every admissible label governs a different section than this record.")
    else:
        evidence.update(state=UNBOUND_NO_ADMISSIBLE, bound_season=None,
                        detail="The capture has no visible staff or roster season heading.")
    return evidence

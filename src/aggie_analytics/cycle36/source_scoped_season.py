"""Record-scoped season authority for official football staff captures.

MR35R-04 reproduced four false admissions against the Cycle #35 binder
(``tools/cycle35/r35_28_staff_season_evidence.py``): a year written in an
HTML comment, a year inside a ``<script>`` string, a year in an archive
navigation link and a year in a biography sentence each bound the capture to
2026. The cause is structural rather than a bad regular expression. That
module matches ``STAFF_LABEL`` against the *raw markup of the whole file* and
then binds when the distinct matched years are unanimous, so anything
lexically shaped like a staff-season label counts as evidence no matter where
it sits, and one match is automatically unanimous.

This module replaces "somewhere on the page" with two separate questions that
TP36-02 requires to be answered together:

1. **Is this text a season label at all?**  A label must be *rendered* text
   (not a comment, script, style, template or attribute value), must not sit
   in a navigation/menu/breadcrumb/footer subtree, must be a *heading-like*
   element or an explicitly dated role announcement, and must not belong to
   another sport.
2. **Does it govern this particular staff record?**  A heading governs the
   span from its own start to the next heading of the same or higher rank.
   A record outside that span is not dated by it, so a biography paragraph
   further down the page cannot date the staff table above it, and a second
   program's section cannot date the first program's rows.

The module never reads a retrieval timestamp. ``source_effective`` (which
season the source says the staff serves) and ``known_at`` (when the bytes
demonstrably existed) stay distinct fields: a current page can support a
retrospective descriptive claim about 2026 while proving nothing about what
was publishable before a 2026 game.

Nothing here binds a season it cannot locate. ``UNBOUND`` is a result, not a
failure to be repaired by a default.
"""

from __future__ import annotations

import bisect
import html as html_lib
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any, Iterable, Sequence

PARSER_VERSION = "BAS-SOURCE-SCOPED-SEASON-v36.1"

#: Seasons a college football staff directory could plausibly label itself
#: with. A four-digit number outside this band is a phone number, a street
#: address, an asset hash or a copyright year, never a staff season.
SEASON_RANGE = (2000, 2030)

# --------------------------------------------------------------------------
# Context classification
# --------------------------------------------------------------------------

#: Element subtrees whose text is never rendered to a reader. A year inside
#: one of these is markup, not a published claim.
NON_RENDERED_ELEMENTS = frozenset(
    {"script", "style", "noscript", "template", "head", "title", "svg", "math"}
)

#: Element subtrees that carry site chrome. An archive menu listing every
#: season is the clearest false positive in MR35R-04: the page links to
#: "2026 Football Coaching Staff" precisely because the page being read is
#: *not* that one.
CHROME_ELEMENTS = frozenset({"nav", "header", "footer", "aside", "menu"})

#: Class/id/role tokens that mark chrome even on a generic ``div``. These
#: sites wrap navigation in divs far more often than in ``<nav>``.
CHROME_TOKENS = (
    "nav",
    "navigation",
    "menu",
    "breadcrumb",
    "crumb",
    "sidebar",
    "site-header",
    "site-footer",
    "footer",
    "masthead",
    "dropdown",
    "submenu",
    "pagination",
    "skip-link",
    "archive-list",
    "season-select",
    "year-select",
)

#: Heading-like elements. A staff directory states its season in a heading,
#: a table caption or a section title, not in running prose.
HEADING_ELEMENTS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6", "caption", "legend"})

#: Class tokens that make a generic element heading-like. Modern athletics
#: templates render section titles as ``<div class="...__title">``.
HEADING_TOKENS = ("title", "heading", "headline", "section-header", "page-title")

#: Heading rank used for scope nesting. Non-``hN`` heading-like elements are
#: treated as rank 3 so they bound a section without out-ranking a page
#: title.
_HEADING_RANK = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
_SYNTHETIC_HEADING_RANK = 3

#: Prose containers. A sentence mentioning a year is biography, not a label.
PROSE_ELEMENTS = frozenset({"p", "blockquote", "figcaption", "li", "dd"})

OTHER_SPORTS = (
    r"basketball|baseball|softball|volleyball|soccer|hockey|lacrosse|"
    r"tennis|golf|swimming|diving|track|cross\s*country|wrestling|rowing|"
    r"gymnastics|water\s*polo|field\s*hockey|bowling|rifle|equestrian|"
    r"beach\s*volleyball|acrobatics|triathlon|fencing|squash|sailing"
)

# --------------------------------------------------------------------------
# Label patterns
# --------------------------------------------------------------------------

#: An explicit staff-season label. Unchanged in shape from Cycle #35 so the
#: comparison between the two binders is about *context*, not about which
#: phrases each one recognises.
STAFF_LABEL = re.compile(
    r"\b(20[0-3]\d)\s+(?:football\s+coaching\s+staff"
    r"|football\s+staff\s+directory"
    r"|football\s+staff"
    r"|coaching\s+staff"
    r"|staff\s+directory"
    r"|football\s+coaches)\b",
    re.I,
)

#: A football roster/season section heading. TP36-02 admits "the actual
#: football roster section or record" as season authority alongside a staff
#: label.
ROSTER_LABEL = re.compile(
    r"\b(20[0-3]\d)\s+(?:football\s+roster|football\s+season|football\s+schedule)\b",
    re.I,
)

MEDIA_GUIDE = re.compile(r"\b(20[0-3]\d)\s+(?:football\s+)?media\s+guide\b", re.I)

#: A dated role announcement: "named offensive coordinator on January 9,
#: 2026". The year is the *announcement* year and dates the appointment, so
#: it is captured as its own evidence kind rather than as a season label.
DATED_ANNOUNCEMENT = re.compile(
    r"\b(?:named|hired|announced|promoted|appointed)\b[^.]{0,120}?"
    r"\b(?:january|february|march|april|may|june|july|august|september|"
    r"october|november|december)\s+\d{1,2},\s*(20[0-3]\d)\b",
    re.I,
)

_OTHER_SPORT_NEAR = re.compile(
    r"\b(?:" + OTHER_SPORTS + r")\b",
    re.I,
)

# Context states -----------------------------------------------------------

CTX_HEADING = "RENDERED_HEADING"
CTX_ANNOUNCEMENT = "DATED_ROLE_ANNOUNCEMENT"
CTX_PROSE = "RENDERED_PROSE"
CTX_OTHER_RENDERED = "RENDERED_NON_HEADING"
CTX_CHROME = "SITE_CHROME_OR_NAVIGATION"
CTX_SCRIPT = "NON_RENDERED_SCRIPT_OR_STYLE"
CTX_COMMENT = "HTML_COMMENT"
CTX_ATTRIBUTE = "TAG_ATTRIBUTE_VALUE"
CTX_OTHER_SPORT = "ANOTHER_SPORT_SECTION"

#: The only contexts a season may be bound from.
ADMISSIBLE_CONTEXTS = frozenset({CTX_HEADING, CTX_ANNOUNCEMENT})

# Binding states -----------------------------------------------------------

BOUND_HEADING = "SEASON_BOUND_BY_GOVERNING_SECTION_HEADING"
BOUND_ANNOUNCEMENT = "SEASON_BOUND_BY_DATED_ROLE_ANNOUNCEMENT"
UNBOUND_NO_ADMISSIBLE = "UNBOUND_NO_ADMISSIBLE_SEASON_LABEL"
UNBOUND_OUT_OF_SCOPE = "UNBOUND_NO_LABEL_GOVERNS_THIS_RECORD"
UNBOUND_CONFLICT = "UNBOUND_GOVERNING_LABELS_DISAGREE"
UNREADABLE = "CAPTURE_UNREADABLE"


@dataclass(frozen=True)
class Span:
    """One rendered or non-rendered region of a capture."""

    start: int
    end: int
    kind: str
    tag: str
    depth: int
    #: Ancestor tags outermost-first, for explaining a rejection.
    ancestors: tuple[str, ...] = ()


@dataclass
class HeadingSection:
    """A heading and the span of document it governs."""

    start: int
    text_start: int
    end: int
    rank: int
    tag: str
    text: str
    #: Exclusive end of the governed region, filled in once the next
    #: same-or-higher-rank heading is known.
    scope_end: int = -1


@dataclass
class LabelCandidate:
    """One lexical season-label match plus why it was or was not admitted."""

    season: int
    matched_text: str
    offset: int
    end: int
    kind: str
    context: str
    admissible: bool
    reason: str
    heading_index: int = -1
    scope_start: int = -1
    scope_end: int = -1
    ancestors: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "season": self.season,
            "matched_text": self.matched_text[:160],
            "offset": self.offset,
            "end": self.end,
            "kind": self.kind,
            "context": self.context,
            "admissible": self.admissible,
            "reason": self.reason,
            "governs_from": self.scope_start,
            "governs_to": self.scope_end,
            "ancestors": list(self.ancestors[-6:]),
        }


class _DocumentScanner(HTMLParser):
    """Record where rendered text, chrome, scripts and comments live.

    ``HTMLParser`` is stdlib, so this adds no dependency to a repository that
    parses HTML with the standard library everywhere else. It is lenient
    about unclosed tags, which real athletics templates require.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.spans: list[Span] = []
        self.headings: list[HeadingSection] = []
        self._stack: list[tuple[str, bool, bool, bool]] = []
        self._open_heading: HeadingSection | None = None
        self._heading_text: list[str] = []
        self._doc_end = 0

    # -- helpers ----------------------------------------------------------
    def _offset(self) -> int:
        line, col = self.getpos()
        return self._line_starts[line - 1] + col

    def feed_document(self, text: str) -> None:
        self._line_starts = [0]
        for index, char in enumerate(text):
            if char == "\n":
                self._line_starts.append(index + 1)
        self._doc_end = len(text)
        self.feed(text)
        self.close()
        self._finish_headings()

    def _ancestors(self) -> tuple[str, ...]:
        return tuple(entry[0] for entry in self._stack)

    def _in_non_rendered(self) -> bool:
        return any(entry[1] for entry in self._stack)

    def _in_chrome(self) -> bool:
        return any(entry[2] for entry in self._stack)

    def _in_prose(self) -> bool:
        return any(entry[3] for entry in self._stack)

    @staticmethod
    def _tokens(attrs: Sequence[tuple[str, str | None]]) -> str:
        parts = []
        for name, value in attrs:
            if name in {"class", "id", "role", "data-test-id", "aria-label"}:
                parts.append(str(value or ""))
        return " ".join(parts).lower()

    @classmethod
    def _is_chrome(cls, tag: str, attrs: Sequence[tuple[str, str | None]]) -> bool:
        if tag in CHROME_ELEMENTS:
            return True
        blob = cls._tokens(attrs)
        if not blob:
            return False
        return any(token in blob for token in CHROME_TOKENS)

    @classmethod
    def _heading_rank(
        cls, tag: str, attrs: Sequence[tuple[str, str | None]]
    ) -> int | None:
        if tag in _HEADING_RANK:
            return _HEADING_RANK[tag]
        if tag in HEADING_ELEMENTS:
            return _SYNTHETIC_HEADING_RANK
        blob = cls._tokens(attrs)
        if blob and any(token in blob for token in HEADING_TOKENS):
            return _SYNTHETIC_HEADING_RANK
        return None

    # -- HTMLParser hooks -------------------------------------------------
    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:  # noqa: D102
        tag = tag.lower()
        start = self._offset()
        self.spans.append(
            Span(start, start, "TAG", tag, len(self._stack), self._ancestors())
        )
        non_rendered = tag in NON_RENDERED_ELEMENTS
        chrome = self._is_chrome(tag, attrs)
        prose = tag in PROSE_ELEMENTS
        if tag in {"br", "hr", "img", "input", "meta", "link", "source"}:
            return
        self._stack.append((tag, non_rendered, chrome, prose))
        rank = self._heading_rank(tag, attrs)
        if rank is not None and not non_rendered and self._open_heading is None:
            self._open_heading = HeadingSection(
                start=start,
                text_start=start,
                end=start,
                rank=rank,
                tag=tag,
                text="",
            )
            self._heading_text = []

    def handle_endtag(self, tag: str) -> None:  # noqa: D102
        tag = tag.lower()
        end = self._offset()
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tag:
                del self._stack[index:]
                break
        if self._open_heading is not None and self._open_heading.tag == tag:
            self._open_heading.end = end
            self._open_heading.text = re.sub(
                r"\s+", " ", html_lib.unescape("".join(self._heading_text))
            ).strip()
            self.headings.append(self._open_heading)
            self._open_heading = None
            self._heading_text = []

    def handle_data(self, data: str) -> None:  # noqa: D102
        start = self._offset()
        if self._in_non_rendered():
            kind = "SCRIPT"
        elif self._in_chrome():
            kind = "CHROME"
        elif self._in_prose():
            kind = "PROSE"
        else:
            kind = "TEXT"
        self.spans.append(
            Span(start, start + len(data), kind, self._stack[-1][0] if self._stack else "", len(self._stack), self._ancestors())
        )
        if self._open_heading is not None and kind != "SCRIPT":
            self._heading_text.append(data)

    def handle_comment(self, data: str) -> None:  # noqa: D102
        start = self._offset()
        self.spans.append(
            Span(start, start + len(data) + 7, "COMMENT", "", len(self._stack), self._ancestors())
        )

    def unknown_decl(self, data: str) -> None:  # noqa: D102
        start = self._offset()
        self.spans.append(
            Span(start, start + len(data), "COMMENT", "", len(self._stack), self._ancestors())
        )

    # -- finishing --------------------------------------------------------
    def _finish_headings(self) -> None:
        if self._open_heading is not None:
            self._open_heading.end = self._doc_end
            self._open_heading.text = re.sub(
                r"\s+", " ", html_lib.unescape("".join(self._heading_text))
            ).strip()
            self.headings.append(self._open_heading)
            self._open_heading = None
        self.headings.sort(key=lambda h: h.start)
        for index, heading in enumerate(self.headings):
            scope_end = self._doc_end
            for later in self.headings[index + 1 :]:
                if later.rank <= heading.rank:
                    scope_end = later.start
                    break
            heading.scope_end = scope_end


@dataclass
class ScannedCapture:
    """A parsed capture: its spans, headings and admissible season labels."""

    text: str
    spans: list[Span]
    headings: list[HeadingSection]
    candidates: list[LabelCandidate]
    parse_error: str | None = None
    _index: list[int] = field(default_factory=list, repr=False)
    _regions: list[Span] = field(default_factory=list, repr=False)

    def _build_index(self) -> None:
        """Sorted, non-overlapping text regions for O(log n) lookup.

        Zero-length ``TAG`` markers are dropped; what remains are the data
        and comment regions the parser emitted in document order, which do
        not overlap each other. Offsets that fall in no region are inside a
        tag -- an attribute value -- which is exactly the ``CTX_ATTRIBUTE``
        answer.
        """

        self._regions = [s for s in self.spans if s.end > s.start]
        self._regions.sort(key=lambda s: s.start)
        self._index = [s.start for s in self._regions]

    def context_at(self, offset: int) -> tuple[str, tuple[str, ...]]:
        """Which document region an absolute offset falls in."""

        if not self._index:
            self._build_index()
        position = bisect.bisect_right(self._index, offset) - 1
        best: Span | None = None
        if 0 <= position < len(self._regions):
            candidate = self._regions[position]
            if candidate.start <= offset < candidate.end:
                best = candidate
        if best is None:
            return CTX_ATTRIBUTE, ()
        return {
            "SCRIPT": CTX_SCRIPT,
            "COMMENT": CTX_COMMENT,
            "CHROME": CTX_CHROME,
            "PROSE": CTX_PROSE,
            "TEXT": CTX_OTHER_RENDERED,
            "TAG": CTX_ATTRIBUTE,
        }.get(best.kind, CTX_ATTRIBUTE), best.ancestors

    def admissible(self) -> list[LabelCandidate]:
        return [c for c in self.candidates if c.admissible]


def _heading_for(headings: Sequence[HeadingSection], offset: int) -> int:
    """Index of the innermost heading whose own element contains ``offset``."""

    best = -1
    for index, heading in enumerate(headings):
        if heading.start <= offset < max(heading.end, heading.start + 1):
            if best < 0 or heading.rank >= headings[best].rank:
                best = index
    return best


def _names_another_sport(text: str, start: int, end: int) -> bool:
    """Whether the label sits inside another sport's section.

    These sites host every varsity program, so a football staff capture also
    carries "2025 Women's Basketball Coaching Staff". The window looks
    *before* the year (where the sport qualifier lives) and a short way after.
    """

    window = text[max(0, start - 80) : end + 30]
    if re.search(r"\bfootball\b", window, re.I):
        return False
    return bool(_OTHER_SPORT_NEAR.search(window))


def scan_capture(text: str) -> ScannedCapture:
    """Parse one capture and classify every lexical season-label match."""

    scanner = _DocumentScanner()
    parse_error: str | None = None
    try:
        scanner.feed_document(text)
    except Exception as error:  # pragma: no cover - malformed real markup
        parse_error = f"{type(error).__name__}: {error}"
    scanned = ScannedCapture(
        text=text,
        spans=scanner.spans,
        headings=scanner.headings,
        candidates=[],
        parse_error=parse_error,
    )

    patterns = (
        (STAFF_LABEL, "STAFF_SEASON_LABEL"),
        (ROSTER_LABEL, "FOOTBALL_ROSTER_SEASON_LABEL"),
        (MEDIA_GUIDE, "MEDIA_GUIDE_YEAR"),
        (DATED_ANNOUNCEMENT, "DATED_ROLE_ANNOUNCEMENT"),
    )
    low, high = SEASON_RANGE
    for pattern, kind in patterns:
        for match in pattern.finditer(text):
            year = int(match.group(1))
            if not low <= year <= high:
                continue
            context, ancestors = scanned.context_at(match.start())
            if context == CTX_SCRIPT:
                reason = (
                    "The text is inside a script, style or template element, "
                    "so it is markup the reader never sees."
                )
                admissible = False
            elif context == CTX_COMMENT:
                reason = "The text is inside an HTML comment and is not published."
                admissible = False
            elif context == CTX_ATTRIBUTE:
                reason = (
                    "The text is inside a tag's attribute value, not in the "
                    "document's rendered text."
                )
                admissible = False
            elif context == CTX_CHROME:
                reason = (
                    "The text is inside site chrome (navigation, menu, "
                    "breadcrumb, sidebar or footer). An archive menu lists "
                    "seasons the page is not showing."
                )
                admissible = False
            elif _names_another_sport(text, match.start(), match.end()):
                context = CTX_OTHER_SPORT
                reason = (
                    "The label belongs to another sport's section on the same "
                    "multi-sport page."
                )
                admissible = False
            elif kind == "DATED_ROLE_ANNOUNCEMENT":
                context = CTX_ANNOUNCEMENT
                reason = (
                    "An explicitly dated appointment announcement in rendered "
                    "text supplies the year of the role change."
                )
                admissible = True
            elif context == CTX_PROSE:
                reason = (
                    "The year appears in running prose (a biography sentence), "
                    "which describes a person rather than dating this staff "
                    "directory."
                )
                admissible = False
            else:
                heading_index = _heading_for(scanned.headings, match.start())
                if heading_index < 0:
                    context = CTX_OTHER_RENDERED
                    reason = (
                        "The year is rendered but not inside a heading, caption "
                        "or section title, so it labels nothing in particular."
                    )
                    admissible = False
                else:
                    context = CTX_HEADING
                    reason = (
                        "The year is inside a rendered section heading, which "
                        "labels the records that follow it."
                    )
                    admissible = kind != "MEDIA_GUIDE_YEAR"
                    if not admissible:
                        reason = (
                            "A media-guide year is corroboration only; it never "
                            "substitutes for a staff or roster season label."
                        )
                    heading = scanned.headings[heading_index]
                    scanned.candidates.append(
                        LabelCandidate(
                            season=year,
                            matched_text=match.group(0).strip(),
                            offset=match.start(),
                            end=match.end(),
                            kind=kind,
                            context=context,
                            admissible=admissible,
                            reason=reason,
                            heading_index=heading_index,
                            scope_start=heading.start,
                            scope_end=heading.scope_end,
                            ancestors=ancestors,
                        )
                    )
                    continue
            scope_start, scope_end = (-1, -1)
            if admissible and kind == "DATED_ROLE_ANNOUNCEMENT":
                # An announcement governs only the record it sits inside; the
                # caller supplies the record span, so the announcement's own
                # sentence is the widest scope it can claim.
                scope_start = max(0, match.start() - 400)
                scope_end = min(len(text), match.end() + 400)
            scanned.candidates.append(
                LabelCandidate(
                    season=year,
                    matched_text=match.group(0).strip(),
                    offset=match.start(),
                    end=match.end(),
                    kind=kind,
                    context=context,
                    admissible=admissible,
                    reason=reason,
                    scope_start=scope_start,
                    scope_end=scope_end,
                    ancestors=ancestors,
                )
            )
    scanned.candidates.sort(key=lambda c: (c.offset, c.kind))
    return scanned


def season_for_record(
    scanned: ScannedCapture, record_offset: int | None
) -> dict[str, Any]:
    """Bind a season for one staff record, or explain why nothing binds.

    ``record_offset`` is the raw-HTML offset of the record the caller already
    bound a person and title to (Cycle #33's ``span_locate`` contract). When
    it is ``None`` the record is not located, so no label can be shown to
    govern it and nothing is bound.
    """

    admissible = scanned.admissible()
    evidence = {
        "parser_version": PARSER_VERSION,
        "record_offset": record_offset,
        "admissible_label_count": len(admissible),
        "rejected_label_count": len(scanned.candidates) - len(admissible),
        "labels": [c.as_dict() for c in scanned.candidates[:40]],
    }
    if scanned.parse_error:
        evidence["parse_error"] = scanned.parse_error

    if not admissible:
        evidence.update(
            state=UNBOUND_NO_ADMISSIBLE,
            bound_season=None,
            detail=(
                "The capture carries no season label in rendered heading text. "
                "Years found in comments, scripts, attributes, navigation, "
                "other sports' sections or biography prose are recorded with "
                "their rejection reason and bind nothing."
            ),
        )
        return evidence

    if record_offset is None:
        evidence.update(
            state=UNBOUND_OUT_OF_SCOPE,
            bound_season=None,
            detail=(
                "The capture carries admissible season labels, but this record "
                "was never bound to a raw-HTML offset, so no label can be shown "
                "to govern it."
            ),
        )
        return evidence

    # A heading dates the records that FOLLOW it, so a heading whose text
    # starts after the record cannot govern it. A dated announcement is
    # different: "A Person ... was named coordinator on January 9, 2026"
    # puts the date after the name inside the same biography block, so an
    # announcement governs its surrounding span in both directions.
    governing = [
        c
        for c in admissible
        if c.scope_start <= record_offset < c.scope_end
        and (c.kind == "DATED_ROLE_ANNOUNCEMENT" or c.offset <= record_offset)
    ]
    if not governing:
        evidence.update(
            state=UNBOUND_OUT_OF_SCOPE,
            bound_season=None,
            detail=(
                "Every admissible season label governs a different section of "
                "the page than the one this record sits in. A heading dates the "
                "records it introduces, not records under a later heading."
            ),
        )
        return evidence

    # The innermost governing heading wins: a "2025 Football Staff" subsection
    # inside a "Football Staff Archive" page dates its own rows.
    governing.sort(key=lambda c: (c.scope_end - c.scope_start, -c.offset))
    tightest = governing[0]
    tied = [
        c
        for c in governing
        if (c.scope_end - c.scope_start) == (tightest.scope_end - tightest.scope_start)
    ]
    seasons = sorted({c.season for c in tied})
    if len(seasons) > 1:
        evidence.update(
            state=UNBOUND_CONFLICT,
            bound_season=None,
            conflicting_seasons=seasons,
            detail=(
                "Two equally-scoped labels govern this record with different "
                f"seasons ({seasons}). Choosing between them would be a guess "
                "about the page rather than evidence from it."
            ),
        )
        return evidence

    evidence.update(
        state=(
            BOUND_ANNOUNCEMENT
            if tightest.kind == "DATED_ROLE_ANNOUNCEMENT"
            else BOUND_HEADING
        ),
        bound_season=tightest.season,
        bound_by=tightest.as_dict(),
        detail=(
            f"The record at offset {record_offset} sits inside the span "
            f"[{tightest.scope_start}, {tightest.scope_end}) governed by the "
            f"rendered label {tightest.matched_text!r}. The season comes from "
            "that label's own text, never from when the page was retrieved."
        ),
    )
    return evidence


def season_evidence_for_capture(
    text: str, record_offsets: Iterable[int | None] = ()
) -> dict[str, Any]:
    """Scan a capture once and bind each supplied record independently."""

    scanned = scan_capture(text)
    offsets = list(record_offsets)
    records = [
        {"record_offset": offset, **season_for_record(scanned, offset)}
        for offset in offsets
    ]
    return {
        "parser_version": PARSER_VERSION,
        "headings": [
            {
                "tag": h.tag,
                "rank": h.rank,
                "start": h.start,
                "end": h.end,
                "scope_end": h.scope_end,
                "text": h.text[:160],
            }
            for h in scanned.headings[:80]
        ],
        "labels": [c.as_dict() for c in scanned.candidates],
        "admissible_label_count": len(scanned.admissible()),
        "records": records,
        "capture_level_state": (
            UNBOUND_NO_ADMISSIBLE
            if not scanned.admissible()
            else "ADMISSIBLE_LABELS_PRESENT_RECORD_SCOPE_DECIDES"
        ),
    }

"""R35-11: availability as report-version evidence, not a roster row.

Availability is a statement someone published about a player, for a contest,
at a stage of a reporting cycle. It is not a property of the player. Three
distinctions carry most of the weight here, and Cycle #34 lost all three:

* **Absence is unknown, never healthy.** A team with no report, a player not
  listed, or a dash in a stage column tells us nothing about that player. The
  only honest value is UNKNOWN, and `AVAILABILITY_UNKNOWN` is a real state
  that downstream code must handle rather than a null to be defaulted away.

* **`Out` does not mean injured.** A player can be out for suspension,
  academic, personal, transfer or undisclosed reasons. The status and the
  REASON are separate fields, and the reason is unknown unless the source
  said it.

* **Three clocks, never merged.** `publication_utc` is when the report was
  published, `effective_utc` is the stage it describes, and `retrieval_utc`
  is when we fetched it. A page byline is at best evidence about the page,
  never about each report embedded in it -- so a byline may populate
  `page_byline_utc` and may not populate `publication_utc`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

CONTRACT_VERSION = "BAS-AVAILABILITY-EVIDENCE-v35.1"

STATUS_AVAILABLE = "AVAILABLE"
STATUS_PROBABLE = "PROBABLE"
STATUS_QUESTIONABLE = "QUESTIONABLE"
STATUS_DOUBTFUL = "DOUBTFUL"
STATUS_OUT = "OUT"
STATUS_GAME_TIME_DECISION = "GAME_TIME_DECISION"
STATUS_UNKNOWN = "UNKNOWN"

#: Exact published spellings -> controlled status. Anything not listed stays
#: UNKNOWN and keeps its raw text, because silently mapping an unrecognised
#: string is how a source's meaning gets replaced by ours.
STATUS_VOCABULARY: dict[str, str] = {
    "available": STATUS_AVAILABLE,
    "probable": STATUS_PROBABLE,
    "questionable": STATUS_QUESTIONABLE,
    "doubtful": STATUS_DOUBTFUL,
    "out": STATUS_OUT,
    "game time decision": STATUS_GAME_TIME_DECISION,
    "game-time decision": STATUS_GAME_TIME_DECISION,
}

#: Tokens a source uses to mean "this stage has no value". They are NOT
#: available, and they are NOT missing data to be dropped: they are an
#: explicit published absence, which is itself an observation.
EMPTY_STAGE_TOKENS = frozenset({"", "-", "--", "–", "—", "n/a", "na"})

REPORT_STAGES = (
    "initial_status",
    "update_1_status",
    "update_2_status",
    "game_day_status",
)

#: Why a player is unavailable is a separate assertion from whether they are.
REASON_UNKNOWN = "REASON_NOT_STATED_BY_SOURCE"


class AvailabilityError(ValueError):
    """Raised when an availability assertion cannot be formed honestly."""


def normalize_status(raw: Any) -> dict[str, Any]:
    """Map a published cell to a controlled status, preserving the original.

    A dash is `PUBLISHED_EMPTY`: the report exists and this stage carries no
    value. That is different from `NOT_IN_REPORT` (the player is absent
    entirely) and different again from `NO_REPORT` (nothing was published).
    Cycle #34 could not tell these apart; downstream, all three became
    indistinguishable from "fine".
    """

    text = str(raw or "").strip()
    folded = re.sub(r"\s+", " ", text).casefold()
    if folded in EMPTY_STAGE_TOKENS:
        return {
            "status": STATUS_UNKNOWN,
            "raw_text": text,
            "presence": "PUBLISHED_EMPTY",
            "vocabulary_recognized": True,
        }
    mapped = STATUS_VOCABULARY.get(folded)
    return {
        "status": mapped or STATUS_UNKNOWN,
        "raw_text": text,
        "presence": "PUBLISHED_VALUE",
        "vocabulary_recognized": mapped is not None,
    }


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


@dataclass(frozen=True)
class AvailabilityAssertion:
    """One published status for one player, contest and stage."""

    program: str
    contest_label: str
    player_name: str
    jersey: str
    stage: str
    status: str
    raw_text: str
    presence: str
    vocabulary_recognized: bool
    reason: str = REASON_UNKNOWN
    canonical_player_id: str | None = None
    canonical_program_id: str | None = None
    canonical_contest_id: str | None = None
    publication_utc: str | None = None
    effective_utc: str | None = None
    retrieval_utc: str | None = None
    page_byline_utc: str | None = None
    source_sha256: str | None = None
    source_locator: str | None = None
    rights_state: str = "UNDECLARED"
    identity_state: str = "UNRESOLVED_NAME_AND_JERSEY_ONLY"

    def as_dict(self) -> dict[str, Any]:
        return {
            "program": self.program,
            "contest_label": self.contest_label,
            "player_name": self.player_name,
            "jersey": self.jersey,
            "stage": self.stage,
            "status": self.status,
            "raw_text": self.raw_text,
            "presence": self.presence,
            "vocabulary_recognized": self.vocabulary_recognized,
            "reason": self.reason,
            "out_does_not_imply_injury": True,
            "canonical_player_id": self.canonical_player_id,
            "canonical_program_id": self.canonical_program_id,
            "canonical_contest_id": self.canonical_contest_id,
            "publication_utc": self.publication_utc,
            "effective_utc": self.effective_utc,
            "retrieval_utc": self.retrieval_utc,
            "page_byline_utc": self.page_byline_utc,
            "byline_is_not_per_report_publication_time": True,
            "source_sha256": self.source_sha256,
            "source_locator": self.source_locator,
            "rights_state": self.rights_state,
            "identity_state": self.identity_state,
            "contract_version": CONTRACT_VERSION,
            "pit_admitted": False,
        }


def parse_tabular_report(
    text: str,
    *,
    source_sha256: str | None = None,
    retrieval_utc: str | None = None,
    page_byline_utc: str | None = None,
    rights_state: str = "PUBLIC_CONFERENCE_REPORT_RESEARCH_USE",
) -> dict[str, Any]:
    """Parse a tab-separated conference availability report.

    Every stage column of every row becomes its own assertion, including the
    empty ones -- 63 player rows with four stages are 252 assertions, and
    collapsing them to 63 "statuses" is what loses the progression a report
    exists to communicate.
    """

    lines = [line for line in (text or "").splitlines() if line.strip()]
    if not lines:
        raise AvailabilityError("empty availability report")
    header = [cell.strip() for cell in lines[0].split("\t")]
    expected = [
        "Team",
        "Date",
        "Opponent",
        "Number",
        "Player",
        "Initial Status",
        "Update 1 Status",
        "Update 2 Status",
        "Game Day Status",
    ]
    if header != expected:
        raise AvailabilityError(
            "unexpected availability report header: " + repr(header)
        )

    assertions: list[AvailabilityAssertion] = []
    player_rows = 0
    malformed: list[dict[str, Any]] = []
    for index, line in enumerate(lines[1:], start=1):
        cells = [cell.strip() for cell in line.split("\t")]
        if len(cells) != len(expected):
            malformed.append({"line": index, "cells": len(cells), "raw": line[:120]})
            continue
        player_rows += 1
        team, date, opponent, number, player = cells[:5]
        for stage_index, stage in enumerate(REPORT_STAGES):
            normalized = normalize_status(cells[5 + stage_index])
            assertions.append(
                AvailabilityAssertion(
                    program=team,
                    contest_label=date + " " + opponent,
                    player_name=player,
                    jersey=number,
                    stage=stage,
                    status=normalized["status"],
                    raw_text=normalized["raw_text"],
                    presence=normalized["presence"],
                    vocabulary_recognized=normalized["vocabulary_recognized"],
                    source_sha256=source_sha256,
                    source_locator="row[" + str(index) + "]." + stage,
                    retrieval_utc=retrieval_utc,
                    page_byline_utc=page_byline_utc,
                    rights_state=rights_state,
                )
            )
    return {
        "contract_version": CONTRACT_VERSION,
        "player_rows": player_rows,
        "stage_columns": len(REPORT_STAGES),
        "assertions": [item.as_dict() for item in assertions],
        "assertion_count": len(assertions),
        "expected_assertion_count": player_rows * len(REPORT_STAGES),
        "conservation_holds": len(assertions) == player_rows * len(REPORT_STAGES),
        "malformed_rows": malformed,
        "publication_time_established": False,
        "publication_time_reason": (
            "This capture is a rendered table with no per-report publication "
            "timestamp. The retrieval time is recorded; publication time is "
            "not, and the contest date is not a publication time."
        ),
    }


def summarize(assertions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Counts that keep absence separate from availability."""

    by_status: dict[str, int] = {}
    by_presence: dict[str, int] = {}
    unrecognized: list[str] = []
    for row in assertions:
        status = str(row.get("status"))
        by_status[status] = by_status.get(status, 0) + 1
        presence = str(row.get("presence"))
        by_presence[presence] = by_presence.get(presence, 0) + 1
        if not row.get("vocabulary_recognized"):
            unrecognized.append(str(row.get("raw_text")))
    return {
        "by_status": by_status,
        "by_presence": by_presence,
        "unrecognized_vocabulary": sorted(set(unrecognized)),
        "unknown_is_not_available": True,
        "absence_of_a_report_is_not_health": True,
    }


@dataclass
class ReportOpportunity:
    """One predeclared national report-opportunity key.

    A key stays in the denominator whatever its outcome. A program whose
    conference publishes no report, and a program whose route was blocked,
    are both part of the population -- removing them would make coverage
    look complete by shrinking what completeness means.
    """

    program_id: str
    display_name: str
    classification: str
    conference: str
    policy_status: str
    outcome: str
    detail: str = ""
    evidence_paths: tuple[str, ...] = field(default_factory=tuple)
    #: The grain this key is actually defined at. A program-season policy
    #: record is NOT a per-game report opportunity, and conflating the two
    #: is how a program policy became a claimed report.
    declared_period: str = "UNDECLARED"
    grain: str = "PROGRAM_DECLARED_PERIOD_POLICY"
    #: POLICY_RECORD, GAME_REPORT or NONE -- policy evidence and
    #: game-specific report evidence are different things.
    evidence_kind: str = "NONE"
    #: Every declared path was resolved on disk when this key was built.
    evidence_verified: bool = False
    vintage: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "display_name": self.display_name,
            "classification": self.classification,
            "conference": self.conference,
            "policy_status": self.policy_status,
            "outcome": self.outcome,
            "detail": self.detail,
            "evidence_paths": list(self.evidence_paths),
            "declared_period": self.declared_period,
            "grain": self.grain,
            "evidence_kind": self.evidence_kind,
            "evidence_verified": self.evidence_verified,
            "vintage": self.vintage,
            "retained_in_denominator": True,
            "no_report_means": "UNKNOWN",
        }


OUTCOME_EVIDENCE = "REPORT_EVIDENCE_PRESENT"
OUTCOME_POLICY_NO_REPORT = "POLICY_PUBLISHES_NO_REPORT"
OUTCOME_BLOCKED = "ROUTE_BLOCKED_OR_UNATTEMPTED"
OUTCOME_UNKNOWN_POLICY = "POLICY_UNKNOWN"
#: A documented policy exists and was attempted, but no locatable
#: game-specific report evidence backs it. Previously these were labelled
#: REPORT_EVIDENCE_PRESENT on the strength of an inventory label alone.
OUTCOME_POLICY_EVIDENCE_ONLY = "POLICY_EVIDENCE_ONLY_NO_LOCATABLE_REPORT"
#: The route was never attempted. Distinct from an attempted-and-blocked
#: route: "not attempted" is not evidence about what the source publishes.
OUTCOME_NOT_ATTEMPTED = "ROUTE_NOT_ATTEMPTED"
#: Per-program policy variation. It does NOT establish that no report is
#: published -- only that a conference-wide one is not established.
OUTCOME_POLICY_VARIES_UNKNOWN = "POLICY_VARIES_PER_PROGRAM_REPORT_UNKNOWN"
#: A declared evidence path that does not resolve on disk.
OUTCOME_EVIDENCE_DECLARED_BUT_UNLOCATABLE = "EVIDENCE_DECLARED_BUT_UNLOCATABLE"


def stage_vintage_ordinal(stage: str) -> int | None:
    """Relative recency only, never a timestamp.

    The source's own four stage columns are a real, ordered sequence
    (initial -> update 1 -> update 2 -> game day), even though no per-stage
    publication timestamp is established (see `publication_time_established`
    above). Exposing that order as an ordinal preserves the genuinely
    available "which of two reports for this player/contest is more
    recent" signal without fabricating an absolute time the source never
    published.
    """

    try:
        return REPORT_STAGES.index(stage)
    except ValueError:
        return None


def normalize_join_name(value: Any) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()
    return re.sub(r"\s+", " ", text)


def _normalize_jersey(value: Any) -> int | None:
    """`value or ""` would discard a real jersey number 0 as falsy --
    jersey #0 is real and increasingly common, so None is checked
    explicitly instead of relying on truthiness."""

    if value is None:
        return None
    text = str(value).strip().lstrip("#")
    return int(text) if text.isdigit() else None


ROSTER_NOT_LOCALLY_AVAILABLE = "ROSTER_NOT_LOCALLY_AVAILABLE"
RESOLVED_JERSEY_AND_NAME_MATCH = "RESOLVED_JERSEY_AND_NAME_MATCH"
#: A jersey number shared by several roster rows, broken by name evidence.
RESOLVED_JERSEY_COLLISION_BROKEN_BY_NAME = "RESOLVED_JERSEY_COLLISION_BROKEN_BY_NAME"
#: A surname-only agreement with no corroborating jersey. This is NOT a
#: resolution: it never yields a canonical_player_id, because a surname
#: alone does not identify a person on a football roster.
UNRESOLVED_NAME_ONLY_NOT_CORROBORATED = "UNRESOLVED_NAME_ONLY_NOT_CORROBORATED"
UNRESOLVED_NO_ROSTER_MATCH = "UNRESOLVED_NO_ROSTER_MATCH"
QUARANTINE_JERSEY_NAME_CONFLICT = "QUARANTINE_JERSEY_NAME_CONFLICT"
QUARANTINE_GIVEN_NAME_CONTRADICTS = "QUARANTINE_GIVEN_NAME_CONTRADICTS"
QUARANTINE_AMBIGUOUS_ROSTER_MATCH = "QUARANTINE_AMBIGUOUS_ROSTER_MATCH"
QUARANTINE_ROSTER_ROW_HAS_NO_IDENTIFIER = "QUARANTINE_ROSTER_ROW_HAS_NO_IDENTIFIER"

#: Given-name evidence is three-valued plus an explicit "absent" state.
#: Collapsing it to a boolean is what let a report for "Bob Smith" resolve
#: to roster person "Alice Smith" purely because the surnames matched.
GIVEN_NAME_AGREES = "AGREES"
GIVEN_NAME_COMPATIBLE_INITIAL = "COMPATIBLE_INITIAL"
GIVEN_NAME_UNCORROBORATED = "UNCORROBORATED"
GIVEN_NAME_CONTRADICTS = "CONTRADICTS"

#: Tokens a source emits for "no value" that must never become an id.
_NON_IDENTIFIER_TOKENS = frozenset({"", "none", "null", "nan", "n/a", "na", "-", "0000"})

#: Generational suffixes are name decoration, not given-name evidence.
_NAME_SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv", "v"})


def valid_source_identifier(value: Any) -> str | None:
    """A usable source identifier, or None.

    `str(row.get("id"))` turns a missing id into the literal string
    "None", which then travels downstream as if it were a real canonical
    player id. Every candidate id passes through here instead.
    """

    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if text.casefold() in _NON_IDENTIFIER_TOKENS:
        return None
    return text or None


def qualify_player_id(source_id: Any, raw_id: Any) -> str | None:
    """Source-qualify a roster identifier, matching this codebase's
    existing `SRC-002:TEAM:` / `SRC-002:GAME:` convention. A bare integer
    from one provider is not a canonical identity on its own."""

    identifier = valid_source_identifier(raw_id)
    if identifier is None:
        return None
    source = valid_source_identifier(source_id) or "SRC-UNDECLARED"
    return f"{source}:PLAYER:{identifier}"


def _name_tokens(value: Any) -> list[str]:
    return [
        token
        for token in normalize_join_name(value).split()
        if token and token not in _NAME_SUFFIXES
    ]


def given_name_evidence(published_name: Any, roster_row: Mapping[str, Any]) -> str:
    """Compare the published given name against the roster's own.

    Returns one of AGREES / COMPATIBLE_INITIAL / UNCORROBORATED /
    CONTRADICTS. An initial ("A. Smith") is compatible with a matching
    full given name; two different full given names contradict.
    """

    roster_given = _name_tokens(roster_row.get("first_name"))
    if not roster_given:
        return GIVEN_NAME_UNCORROBORATED

    published_tokens = _name_tokens(published_name)
    roster_surname = set(_name_tokens(roster_row.get("last_name")))
    published_given = [t for t in published_tokens if t not in roster_surname]
    if not published_given:
        return GIVEN_NAME_UNCORROBORATED

    roster_first, published_first = roster_given[0], published_given[0]
    if roster_first == published_first:
        return GIVEN_NAME_AGREES
    if len(published_first) == 1 and roster_first.startswith(published_first):
        return GIVEN_NAME_COMPATIBLE_INITIAL
    if len(roster_first) == 1 and published_first.startswith(roster_first):
        return GIVEN_NAME_COMPATIBLE_INITIAL
    return GIVEN_NAME_CONTRADICTS


def resolve_canonical_player(
    *,
    program: str,
    player_name: str,
    jersey: str,
    roster_index: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    """Join one availability assertion's name+jersey to a real roster row.

    This is deliberately conservative: a jersey-number match with a
    conflicting name is a QUARANTINE, not a resolution -- rosters drift
    (walk-ons, mid-season number changes) and a wrong player identity is
    worse than an honestly unresolved one. Resolving an identity here never
    changes the assertion's own status/presence -- roster membership is not
    an injury/health fact, and this function does not return one.
    """

    candidates = roster_index.get(program)
    if candidates is None:
        return {
            "canonical_player_id": None,
            "identity_state": ROSTER_NOT_LOCALLY_AVAILABLE,
            "identity_detail": "No local roster snapshot covers this program.",
            "identity_evidence": {"considered": []},
        }

    jersey_number = _normalize_jersey(jersey)
    name_tokens = set(_name_tokens(player_name))

    def surname_agrees(row: Mapping[str, Any]) -> bool:
        """`last in name_tokens` would fail whenever the roster's own
        last_name field is itself multi-word (CFBD returns generational
        suffixes folded into last_name, e.g. "Kinsler IV", "Lincoln Jr.")
        -- that literal multi-word string is never an element of a set of
        single-word tokens. Every word of the roster's last name must
        appear among the assertion's name tokens instead."""

        last_tokens = set(_name_tokens(row.get("last_name")))
        return bool(last_tokens) and last_tokens.issubset(name_tokens)

    def evidence_of(row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "roster_full_name": " ".join(
                part
                for part in (str(row.get("first_name") or ""), str(row.get("last_name") or ""))
                if part
            ).strip(),
            "roster_jersey": _normalize_jersey(row.get("jersey")),
            "roster_season": row.get("roster_season"),
            "roster_source_id": row.get("source_id"),
            "roster_source_path": row.get("source_path"),
            "surname_evidence": "AGREES" if surname_agrees(row) else "DISAGREES",
            "given_name_evidence": given_name_evidence(player_name, row),
            "jersey_evidence": (
                "AGREES"
                if jersey_number is not None
                and _normalize_jersey(row.get("jersey")) == jersey_number
                else "UNCORROBORATED"
            ),
        }

    def resolved(row: Mapping[str, Any], state: str, detail: str) -> dict[str, Any]:
        """A matched roster row still only yields an id if it HAS one."""

        player_id = qualify_player_id(row.get("source_id"), row.get("id"))
        evidence = evidence_of(row)
        if player_id is None:
            return {
                "canonical_player_id": None,
                "identity_state": QUARANTINE_ROSTER_ROW_HAS_NO_IDENTIFIER,
                "identity_detail": "The matching roster row carries no usable "
                "source identifier, so no canonical player id exists to assign.",
                "identity_evidence": evidence,
            }
        return {
            "canonical_player_id": player_id,
            "identity_state": state,
            "identity_detail": detail,
            "identity_evidence": evidence,
        }

    def unresolved(state: str, detail: str, rows: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
        return {
            "canonical_player_id": None,
            "identity_state": state,
            "identity_detail": detail,
            "identity_evidence": {"considered": [evidence_of(row) for row in rows]},
        }

    jersey_candidates = (
        [row for row in candidates if _normalize_jersey(row.get("jersey")) == jersey_number]
        if jersey_number is not None
        else []
    )

    if jersey_candidates:
        # Name evidence disambiguates a shared jersey number BEFORE any
        # quarantine decision. Two real players wearing one number is
        # ordinary in college football; it is not by itself irresolvable
        # when the published name agrees with exactly one of them.
        surname_ok = [row for row in jersey_candidates if surname_agrees(row)]
        supported = [
            row
            for row in surname_ok
            if given_name_evidence(player_name, row) != GIVEN_NAME_CONTRADICTS
        ]
        contradicted = [
            row
            for row in surname_ok
            if given_name_evidence(player_name, row) == GIVEN_NAME_CONTRADICTS
        ]
        if len(supported) == 1:
            row = supported[0]
            state = (
                RESOLVED_JERSEY_AND_NAME_MATCH
                if len(jersey_candidates) == 1
                else RESOLVED_JERSEY_COLLISION_BROKEN_BY_NAME
            )
            detail = (
                "Jersey number and name evidence agree with exactly one local "
                "roster row."
                if len(jersey_candidates) == 1
                else f"{len(jersey_candidates)} roster rows share this jersey "
                "number; name evidence supports exactly one of them."
            )
            return resolved(row, state, detail)
        if len(supported) > 1:
            return unresolved(
                QUARANTINE_AMBIGUOUS_ROSTER_MATCH,
                f"{len(supported)} roster rows share this jersey number and are "
                "each consistent with the published name; the available identity "
                "evidence does not separate them.",
                supported,
            )
        if contradicted:
            return unresolved(
                QUARANTINE_GIVEN_NAME_CONTRADICTS,
                "The jersey number and surname agree, but the published given "
                "name contradicts the roster's given name for every candidate.",
                contradicted,
            )
        return unresolved(
            QUARANTINE_JERSEY_NAME_CONFLICT,
            "The jersey number matches a roster row, but the published surname "
            "does not agree with any candidate; not resolved.",
            jersey_candidates,
        )

    name_candidates = [row for row in candidates if surname_agrees(row)]
    if name_candidates:
        # A surname-only agreement is NOT promoted to a canonical id: the
        # manager's rule is that a name-only match must not silently become
        # a canonical identity. The candidate is retained for audit.
        return {
            "canonical_player_id": None,
            "identity_state": UNRESOLVED_NAME_ONLY_NOT_CORROBORATED,
            "identity_detail": (
                f"{len(name_candidates)} roster row(s) share this surname, but no "
                "jersey number corroborates the match; a surname alone does not "
                "identify a person."
            ),
            "identity_evidence": {
                "considered": [evidence_of(row) for row in name_candidates],
                "name_only_candidate_ids": [
                    qualify_player_id(row.get("source_id"), row.get("id"))
                    for row in name_candidates
                ],
            },
        }
    return unresolved(
        UNRESOLVED_NO_ROSTER_MATCH,
        "A local roster snapshot covers this program, but no row matches this "
        "jersey number or name.",
    )


_CONTEST_LABEL_RE = re.compile(
    r"^(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<year>\d{2,4})\s+"
    r"(?P<qualifier>at|vs\.?)\s+(?P<opponent>.+)$",
    re.IGNORECASE,
)

CONTEST_NOT_LOCALLY_AVAILABLE = "CONTEST_NOT_LOCALLY_AVAILABLE"
RESOLVED_CONTEST_MATCH = "RESOLVED_CONTEST_MATCH"
UNRESOLVED_CONTEST_LABEL_UNPARSEABLE = "UNRESOLVED_CONTEST_LABEL_UNPARSEABLE"
UNRESOLVED_CONTEST_LABEL_DATE_INVALID = "UNRESOLVED_CONTEST_LABEL_DATE_INVALID"
#: The published date's own season disagrees with the season the caller
#: declared. A caller-supplied season must not silently override an
#: explicit, contradictory source date.
QUARANTINE_CONTEST_SEASON_CONTRADICTS_LABEL = "QUARANTINE_CONTEST_SEASON_CONTRADICTS_LABEL"
UNRESOLVED_NO_CONTEST_MATCH = "UNRESOLVED_NO_CONTEST_MATCH"
QUARANTINE_AMBIGUOUS_CONTEST_MATCH = "QUARANTINE_AMBIGUOUS_CONTEST_MATCH"


def season_of_calendar_date(year: int, month: int) -> int:
    """The football season a calendar date belongs to.

    A season runs within its own calendar year from March onward and
    continues into January/February of the NEXT calendar year for
    postseason play, so 1/10/2027 belongs to season 2026.
    """

    return year if month >= 3 else year - 1


def _expand_two_digit_year(raw: str) -> int:
    """'26' -> 2026. Four-digit years are taken verbatim."""

    value = int(raw)
    return value if len(raw) == 4 else 2000 + value


def parse_contest_label(contest_label: str) -> dict[str, Any] | None:
    match = _CONTEST_LABEL_RE.match(str(contest_label or "").strip())
    if not match:
        return None
    year = _expand_two_digit_year(match.group("year"))
    month, day = int(match.group("month")), int(match.group("day"))
    try:
        # Rejects 2/30, 13/1 and similar malformed published dates instead
        # of matching them against an index keyed only on month/day.
        date(year, month, day)
    except ValueError:
        return {
            "year": year,
            "month": month,
            "day": day,
            "date_valid": False,
            "qualifier": match.group("qualifier").rstrip(".").lower(),
            "opponent_raw": match.group("opponent").strip(),
        }
    return {
        "year": year,
        "month": month,
        "day": day,
        "date_valid": True,
        "label_season": season_of_calendar_date(year, month),
        "qualifier": match.group("qualifier").rstrip(".").lower(),
        "opponent_raw": match.group("opponent").strip(),
    }


def resolve_canonical_contest(
    *,
    program: str,
    contest_label: str,
    season: int,
    games_index: Mapping[tuple[str, str, int, int], Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    """Join a published "M/D/YY at|vs Opponent" label to a real game row.

    Matched on the program/opponent pair (order-independent, since the
    report's home/away qualifier and the source's home/away designation are
    not guaranteed to agree in spelling) plus the declared month/day within
    the assertion's own season. A designated home or away side is not
    home-field advantage and is not asserted here -- only game identity.
    """

    parsed = parse_contest_label(contest_label)
    if parsed is None:
        return {
            "canonical_contest_id": None,
            "contest_resolution_state": UNRESOLVED_CONTEST_LABEL_UNPARSEABLE,
            "contest_detail": "contest_label did not match the expected "
            "'M/D/YY at|vs Opponent' shape.",
            "contest_evidence": {"contest_label": contest_label},
        }
    evidence = {
        "contest_label": contest_label,
        "label_year": parsed["year"],
        "label_month": parsed["month"],
        "label_day": parsed["day"],
        "label_season": parsed.get("label_season"),
        "caller_declared_season": season,
    }
    if not parsed["date_valid"]:
        return {
            "canonical_contest_id": None,
            "contest_resolution_state": UNRESOLVED_CONTEST_LABEL_DATE_INVALID,
            "contest_detail": "The published date is not a real calendar date, "
            "so it cannot identify a contest.",
            "contest_evidence": evidence,
        }
    if parsed["label_season"] != season:
        # The published year was previously parsed and then discarded: the
        # lookup keyed only on program/opponent/month/day, so 9/20/25
        # resolved to a 2026 contest whenever the caller declared 2026.
        return {
            "canonical_contest_id": None,
            "contest_resolution_state": QUARANTINE_CONTEST_SEASON_CONTRADICTS_LABEL,
            "contest_detail": (
                f"The published date {parsed['month']}/{parsed['day']}/"
                f"{parsed['year']} belongs to season {parsed['label_season']}, "
                f"but the caller declared season {season}. A declared season "
                "does not override an explicit contradictory source date."
            ),
            "contest_evidence": evidence,
        }
    key = (
        normalize_join_name(program),
        normalize_join_name(parsed["opponent_raw"]),
        parsed["year"],
        parsed["month"],
        parsed["day"],
    )
    matches = list(games_index.get(key, ()))
    if not matches:
        return {
            "canonical_contest_id": None,
            "contest_resolution_state": UNRESOLVED_NO_CONTEST_MATCH,
            "contest_detail": "No local game for this program/opponent/date "
            f"in season {season}.",
            "contest_evidence": evidence,
        }
    distinct = {str(row.get("canonical_game_id")) for row in matches}
    if len(distinct) > 1:
        return {
            "canonical_contest_id": None,
            "contest_resolution_state": QUARANTINE_AMBIGUOUS_CONTEST_MATCH,
            "contest_detail": "More than one distinct local game matches this "
            "program/opponent/date.",
            "contest_evidence": dict(evidence, candidate_ids=sorted(distinct)),
        }
    return {
        "canonical_contest_id": matches[0]["canonical_game_id"],
        "contest_resolution_state": RESOLVED_CONTEST_MATCH,
        "contest_detail": "Exactly one local game matches program, opponent "
        "and the full published date.",
        "contest_evidence": evidence,
    }


def enrich_assertion_identities(
    assertion: Mapping[str, Any],
    *,
    program_id_by_name: Mapping[str, str],
    roster_index: Mapping[str, Sequence[Mapping[str, Any]]],
    games_index: Mapping[tuple[str, str, int, int], Sequence[Mapping[str, Any]]],
    season: int,
) -> dict[str, Any]:
    """Return a NEW assertion dict with real canonical identities attached.

    Never mutates `status`/`presence`/`reason` -- identity resolution and
    the availability statement itself are kept fully separate, per this
    module's own rule that roster membership is not an injury/health fact.
    """

    out = dict(assertion)
    program = str(assertion.get("program") or "")
    out["canonical_program_id"] = program_id_by_name.get(program)

    player = resolve_canonical_player(
        program=program,
        player_name=str(assertion.get("player_name") or ""),
        jersey=str(assertion.get("jersey") or ""),
        roster_index=roster_index,
    )
    out["canonical_player_id"] = player["canonical_player_id"]
    out["identity_state"] = player["identity_state"]
    out["identity_detail"] = player["identity_detail"]
    out["identity_evidence"] = player.get("identity_evidence")
    # The published name is the source's own text and is never overwritten
    # by whatever roster row was (or was not) matched to it.
    out["published_player_name"] = str(assertion.get("player_name") or "")

    contest = resolve_canonical_contest(
        program=program,
        contest_label=str(assertion.get("contest_label") or ""),
        season=season,
        games_index=games_index,
    )
    out["canonical_contest_id"] = contest["canonical_contest_id"]
    out["contest_resolution_state"] = contest["contest_resolution_state"]
    out["contest_detail"] = contest["contest_detail"]
    out["contest_evidence"] = contest.get("contest_evidence")

    out["stage_vintage_ordinal"] = stage_vintage_ordinal(str(assertion.get("stage") or ""))
    out["stage_vintage_is_ordinal_not_temporal"] = True
    #: The player-program-contest grain the manager requires reported
    #: separately from the assertion (stage) grain.
    out["player_program_contest_key"] = "|".join(
        [
            str(out.get("canonical_program_id") or f"UNRESOLVED_PROGRAM:{program}"),
            str(
                out.get("canonical_player_id")
                or f"UNRESOLVED_PLAYER:{out['published_player_name']}"
                f"#{assertion.get('jersey')}"
            ),
            str(
                out.get("canonical_contest_id")
                or f"UNRESOLVED_CONTEST:{assertion.get('contest_label')}"
            ),
        ]
    )
    return out


def opportunity_coverage(keys: Iterable[ReportOpportunity]) -> dict[str, Any]:
    rows = [key.as_dict() for key in keys]
    by_outcome: dict[str, int] = {}
    by_classification: dict[str, int] = {}
    conferences: set[str] = set()
    policies: set[str] = set()
    for row in rows:
        by_outcome[row["outcome"]] = by_outcome.get(row["outcome"], 0) + 1
        by_classification[row["classification"]] = (
            by_classification.get(row["classification"], 0) + 1
        )
        conferences.add(row["conference"])
        policies.add(row["policy_status"])
    return {
        "keys": rows,
        "key_count": len(rows),
        "by_outcome": by_outcome,
        "by_classification": by_classification,
        "distinct_conferences": sorted(conferences),
        "distinct_policies": sorted(policies),
        "denominator_includes_no_report_and_blocked_keys": True,
        "evidence_bearing_keys": by_outcome.get(OUTCOME_EVIDENCE, 0),
    }

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
from datetime import datetime, timezone
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
            "retained_in_denominator": True,
            "no_report_means": "UNKNOWN",
        }


OUTCOME_EVIDENCE = "REPORT_EVIDENCE_PRESENT"
OUTCOME_POLICY_NO_REPORT = "POLICY_PUBLISHES_NO_REPORT"
OUTCOME_BLOCKED = "ROUTE_BLOCKED_OR_UNATTEMPTED"
OUTCOME_UNKNOWN_POLICY = "POLICY_UNKNOWN"


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
RESOLVED_NAME_ONLY_MATCH = "RESOLVED_NAME_ONLY_MATCH"
UNRESOLVED_NO_ROSTER_MATCH = "UNRESOLVED_NO_ROSTER_MATCH"
QUARANTINE_JERSEY_NAME_CONFLICT = "QUARANTINE_JERSEY_NAME_CONFLICT"
QUARANTINE_AMBIGUOUS_ROSTER_MATCH = "QUARANTINE_AMBIGUOUS_ROSTER_MATCH"


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
        }

    jersey_number = _normalize_jersey(jersey)
    normalized_name = normalize_join_name(player_name)
    name_tokens = set(normalized_name.split())

    def name_agrees(row: Mapping[str, Any]) -> bool:
        """`last in name_tokens` would fail whenever the roster's own
        last_name field is itself multi-word (CFBD returns generational
        suffixes folded into last_name, e.g. "Kinsler IV", "Lincoln Jr.")
        -- that literal multi-word string is never an element of a set of
        single-word tokens. Every word of the roster's last name must
        appear among the assertion's name tokens instead."""

        last = normalize_join_name(row.get("last_name"))
        last_tokens = set(last.split())
        return bool(last_tokens) and last_tokens.issubset(name_tokens)

    jersey_candidates = (
        [row for row in candidates if _normalize_jersey(row.get("jersey")) == jersey_number]
        if jersey_number is not None
        else []
    )
    if len(jersey_candidates) == 1:
        row = jersey_candidates[0]
        if name_agrees(row):
            return {
                "canonical_player_id": str(row.get("id")),
                "identity_state": RESOLVED_JERSEY_AND_NAME_MATCH,
                "identity_detail": "Jersey number and last name both agree with "
                "exactly one local roster row.",
            }
        return {
            "canonical_player_id": None,
            "identity_state": QUARANTINE_JERSEY_NAME_CONFLICT,
            "identity_detail": "Jersey number matches exactly one roster row, but "
            "the published name does not agree with it; not resolved.",
        }
    if len(jersey_candidates) > 1:
        return {
            "canonical_player_id": None,
            "identity_state": QUARANTINE_AMBIGUOUS_ROSTER_MATCH,
            "identity_detail": "More than one local roster row shares this jersey "
            "number for this program.",
        }

    name_candidates = [row for row in candidates if name_agrees(row)]
    if len(name_candidates) == 1:
        return {
            "canonical_player_id": str(name_candidates[0].get("id")),
            "identity_state": RESOLVED_NAME_ONLY_MATCH,
            "identity_detail": "Exactly one local roster row's last name agrees; "
            "jersey number did not corroborate it.",
        }
    if len(name_candidates) > 1:
        return {
            "canonical_player_id": None,
            "identity_state": QUARANTINE_AMBIGUOUS_ROSTER_MATCH,
            "identity_detail": "More than one local roster row shares this last "
            "name for this program.",
        }
    return {
        "canonical_player_id": None,
        "identity_state": UNRESOLVED_NO_ROSTER_MATCH,
        "identity_detail": "A local roster snapshot covers this program, but no "
        "row matches this jersey number or name.",
    }


_CONTEST_LABEL_RE = re.compile(
    r"^(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<year>\d{2,4})\s+"
    r"(?P<qualifier>at|vs\.?)\s+(?P<opponent>.+)$",
    re.IGNORECASE,
)

CONTEST_NOT_LOCALLY_AVAILABLE = "CONTEST_NOT_LOCALLY_AVAILABLE"
RESOLVED_CONTEST_MATCH = "RESOLVED_CONTEST_MATCH"
UNRESOLVED_CONTEST_LABEL_UNPARSEABLE = "UNRESOLVED_CONTEST_LABEL_UNPARSEABLE"
UNRESOLVED_NO_CONTEST_MATCH = "UNRESOLVED_NO_CONTEST_MATCH"
QUARANTINE_AMBIGUOUS_CONTEST_MATCH = "QUARANTINE_AMBIGUOUS_CONTEST_MATCH"


def parse_contest_label(contest_label: str) -> dict[str, Any] | None:
    match = _CONTEST_LABEL_RE.match(str(contest_label or "").strip())
    if not match:
        return None
    return {
        "month": int(match.group("month")),
        "day": int(match.group("day")),
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
        }
    key = (
        normalize_join_name(program),
        normalize_join_name(parsed["opponent_raw"]),
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
        }
    if len(matches) > 1:
        return {
            "canonical_contest_id": None,
            "contest_resolution_state": QUARANTINE_AMBIGUOUS_CONTEST_MATCH,
            "contest_detail": "More than one local game matches this "
            "program/opponent/date.",
        }
    return {
        "canonical_contest_id": matches[0]["canonical_game_id"],
        "contest_resolution_state": RESOLVED_CONTEST_MATCH,
        "contest_detail": "Exactly one local game matches program, opponent "
        "and declared date.",
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

    contest = resolve_canonical_contest(
        program=program,
        contest_label=str(assertion.get("contest_label") or ""),
        season=season,
        games_index=games_index,
    )
    out["canonical_contest_id"] = contest["canonical_contest_id"]
    out["contest_resolution_state"] = contest["contest_resolution_state"]
    out["contest_detail"] = contest["contest_detail"]

    out["stage_vintage_ordinal"] = stage_vintage_ordinal(str(assertion.get("stage") or ""))
    out["stage_vintage_is_ordinal_not_temporal"] = True
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

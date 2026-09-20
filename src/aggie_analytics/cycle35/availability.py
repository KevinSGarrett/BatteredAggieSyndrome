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

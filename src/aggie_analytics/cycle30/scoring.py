"""Cycle #30 official-final scoring successor.

Probability 0.5 is not a directional pick. Upstream success must be bound
evidence, not a literal True.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from aggie_analytics.cycle30.acquisition import (
    SCORE_ADMITTED,
    TERMINAL_STATUS_ESTABLISHED,
    AcquisitionError,
    bind_actual_upstream,
    bind_participants,
    contest_scoped_terminal,
)
from aggie_analytics.cycle30.temporal import parse_aware_utc

SHADOW = "UNTRUSTED_SHADOW"
HOLD = "SCIENTIFIC_OPERATOR_HOLD_ACTIVE"


class ScoringError(ValueError):
    """Raised when a scored row cannot be admitted."""


def reject_oriented_rows_as_games(rows: Sequence[Mapping[str, Any]]) -> int:
    contests = {
        str(row.get("ncaa_contest_id") or row.get("canonical_game_id"))
        for row in rows
        if row.get("ncaa_contest_id") or row.get("canonical_game_id")
    }
    oriented = [row for row in rows if row.get("orientation") in {"HOME", "AWAY"}]
    if oriented and len(oriented) == 2 * len(contests) and len(contests) != len(rows):
        return len(contests)
    if len(oriented) > len(contests) and len(rows) == len(oriented):
        raise ScoringError("oriented rows cannot be counted as independent games")
    return len(contests) if contests else len(rows)


def directional_from_probability(probability_home: float) -> str:
    if probability_home == 0.5:
        return "NO_DIRECTION"
    return "HOME" if probability_home > 0.5 else "AWAY"


def reject_half_counted_as_home(probability_home: float, counted_home: bool) -> None:
    if probability_home == 0.5 and counted_home:
        raise ScoringError("base-rate 0.5 cannot be counted as a home prediction")


def admit_official_final(
    *,
    page_text: str,
    contest_id: str,
    contest_hint: str,
    score_element_ids: Sequence[str],
    ordered_participant_ids: Sequence[str],
    page_url: str,
    embedded_contest_id: str,
    canonical_home_id: str,
    canonical_away_id: str,
    displayed_home_name: str,
    displayed_away_name: str,
    name_only: bool,
    home_points: int,
    away_points: int,
    kickoff_utc: str,
    retrieval_utc: str,
    http_status: int | None,
    upstream_status: int | None,
    body: bytes,
) -> dict[str, Any]:
    try:
        bind_actual_upstream(
            http_status=http_status, upstream_status=upstream_status, body=body
        )
    except AcquisitionError as exc:
        raise ScoringError(str(exc)) from exc
    parse_aware_utc(kickoff_utc)
    retrieved = parse_aware_utc(retrieval_utc)
    kickoff = parse_aware_utc(kickoff_utc)
    if retrieved < kickoff:
        raise ScoringError("pre-kickoff retrieval cannot be an official final")
    terminal = contest_scoped_terminal(
        page_text=page_text,
        contest_id=contest_id,
        contest_hint=contest_hint,
        score_element_ids=score_element_ids,
        ordered_participant_ids=ordered_participant_ids,
        page_url=page_url,
        embedded_contest_id=embedded_contest_id,
    )
    if terminal != TERMINAL_STATUS_ESTABLISHED:
        raise ScoringError("contest is not terminal")
    identities = bind_participants(
        canonical_home_id=canonical_home_id,
        canonical_away_id=canonical_away_id,
        ordered_participant_ids=ordered_participant_ids,
        displayed_home_name=displayed_home_name,
        displayed_away_name=displayed_away_name,
        name_only=name_only,
    )
    winner = (
        "HOME"
        if home_points > away_points
        else "AWAY"
        if away_points > home_points
        else "TIE"
    )
    return {
        **identities,
        "ncaa_contest_id": contest_id,
        "home_points": int(home_points),
        "away_points": int(away_points),
        "winner": winner,
        "state": SCORE_ADMITTED,
        "trust_classification": SHADOW,
        "operator_hold": HOLD,
        "display_names_are_not_canonical": True,
        "http_status": http_status,
        "upstream_status": upstream_status,
    }


def reject_forecast_mutation(
    predecessor_rows: Sequence[Mapping[str, Any]],
    successor_rows: Sequence[Mapping[str, Any]],
) -> None:
    pred = [dict(row) for row in predecessor_rows]
    succ = [dict(row) for row in successor_rows]
    if pred != succ:
        raise ScoringError("frozen forecast opportunities must not mutate")

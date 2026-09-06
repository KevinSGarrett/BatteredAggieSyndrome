"""Independent Cycle #28 scoring reconstruction.

Must not import producer scoring, receipt, identity, or metric helpers from
``aggie_analytics.data`` or ``aggie_analytics.cycle28.scoring``.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from aggie_analytics.scientific_reference.metrics import accuracy, brier_score, log_loss
from aggie_analytics.scientific_reference.ncaa_scoreboard_cards import (
    reconstruct_box_score_header,
    reconstruct_scoreboard_cards,
)


class IndependentScoringError(ValueError):
    """Raised when independent reconstruction cannot admit a scored row."""


def game_grain_denominators(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    contests = {
        str(row.get("ncaa_contest_id")) for row in rows if row.get("ncaa_contest_id")
    }
    oriented = [row for row in rows if row.get("orientation") in {"HOME", "AWAY"}]
    if oriented and len(oriented) == 2 * len(contests):
        # Oriented pairs are not independent games.
        pass
    return {
        "unique_games": len(contests),
        "oriented_rows": len(oriented),
        "row_count": len(rows),
    }


def reject_oriented_rows_as_games(rows: Sequence[Mapping[str, Any]]) -> int:
    stats = game_grain_denominators(rows)
    if stats["oriented_rows"] and stats["unique_games"] * 2 == stats["oriented_rows"]:
        return stats["unique_games"]
    if stats["oriented_rows"] > stats["unique_games"]:
        raise IndependentScoringError(
            "oriented rows cannot be counted as independent games"
        )
    return stats["unique_games"]


def reconstruct_metrics(
    *,
    predicted: Sequence[float],
    observed: Sequence[float],
    unique_game_count: int,
) -> dict[str, float | None | int]:
    if unique_game_count != len(predicted):
        raise IndependentScoringError("metrics must be computed at unique-game grain")
    return {
        "unique_games": unique_game_count,
        "brier": brier_score(predicted, observed),
        "log_loss": log_loss(predicted, observed),
        "accuracy": accuracy(predicted, observed),
    }


def residual_margin(actual_margin: float, predicted_margin: float) -> float:
    return float(actual_margin) - float(predicted_margin)


def result_residual(observed_win: float, predicted_probability: float) -> float:
    return float(observed_win) - float(predicted_probability)


def select_earliest_valid_terminal(
    receipts: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | str:
    """Select the earliest valid atomic terminal receipt; quarantine conflicts."""

    admitted: list[Mapping[str, Any]] = []
    for row in receipts:
        if row.get("receipt_kind") != "SOURCE_ACQUISITION_RECEIPT":
            continue
        if row.get("final_status") not in {"FINAL", "OFFICIAL_FINAL"}:
            continue
        admitted.append(row)
    if not admitted:
        return "NO_VALID_ATOMIC_TERMINAL"
    scores = {
        (
            int(row["home_points"]),
            int(row["away_points"]),
            str(row["winner"]),
            str(row["ncaa_contest_id"]),
        )
        for row in admitted
    }
    if len(scores) > 1:
        return "CONFLICT_QUARANTINED"
    contest_ids = {str(row["ncaa_contest_id"]) for row in admitted}
    if len(contest_ids) != 1:
        return "CONFLICT_QUARANTINED"
    ordered = sorted(
        admitted,
        key=lambda row: str(
            row.get("trusted_clock_retrieval_utc")
            or row.get("acquisition_ended_at_utc")
        ),
    )
    return ordered[0]


def parse_independent_cards(document: str) -> list[dict[str, Any]]:
    return reconstruct_scoreboard_cards(document)


def parse_independent_box(
    document: str, contest_id_hint: str | None = None
) -> dict[str, Any]:
    return reconstruct_box_score_header(document, contest_id_hint)


def reject_prekickoff_final(retrieved_utc: str, kickoff_utc: str) -> None:
    if retrieved_utc < kickoff_utc:
        raise IndependentScoringError("pre-kickoff final cannot be admitted")


def reject_non_final_score(status: str) -> None:
    if status not in {"FINAL", "OFFICIAL_FINAL"}:
        raise IndependentScoringError("non-final score cannot be admitted")

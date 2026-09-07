"""Independent reconstruction of official-final and identity contracts."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from aggie_analytics.scientific_reference.cycle29.metrics import directional_accuracy
from aggie_analytics.scientific_reference.cycle29.temporal import parse_aware_utc


class IndependentIdentityError(ValueError):
    """Raised when independent identity reconstruction fails."""


def require_canonical_ids(home_id: str, away_id: str, name_only: bool) -> None:
    if name_only or not home_id or not away_id:
        raise IndependentIdentityError("name-only matching is not identity authority")
    if home_id == away_id:
        raise IndependentIdentityError("home and away IDs must differ")


def unique_games(rows: Sequence[Mapping[str, Any]]) -> int:
    contests = {
        str(row.get("ncaa_contest_id") or row.get("canonical_game_id"))
        for row in rows
        if row.get("ncaa_contest_id") or row.get("canonical_game_id")
    }
    oriented = [row for row in rows if row.get("orientation") in {"HOME", "AWAY"}]
    if oriented and len(oriented) == 2 * len(contests):
        return len(contests)
    return len(contests) or len(rows)


def half_has_no_direction(
    predicted: Sequence[float], observed: Sequence[float]
) -> dict[str, Any]:
    return directional_accuracy(predicted, observed)


def issued_before(issued_utc: str, cutoff_utc: str) -> bool:
    return parse_aware_utc(issued_utc) <= parse_aware_utc(cutoff_utc)

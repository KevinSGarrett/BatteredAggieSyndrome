"""Neutral-site context. Ordinary home advantage is not applicable."""

from __future__ import annotations

import math
from typing import Any, Mapping


class NeutralVenueError(ValueError):
    """Raised when a neutral contest is labeled as ordinary home advantage,
    or when a neutral/travel value cannot be strictly and safely resolved."""


def ordinary_home_advantage(*, neutral_site: bool | None) -> float | None:
    """Zero at a confirmed neutral site; not-applicable/unknown otherwise.

    `neutral_site=None` (unknown) must never silently manufacture a nonzero
    or a zero exposure value -- it stays None (not-applicable/unknown), never
    coerced to the `neutral_site=False` case.
    """

    if neutral_site is True:
        return 0.0
    return None


def _resolve_neutral_site(value: Any) -> bool | None:
    """Strict true/false/unknown. `None` becomes unknown, never false. A
    string must spell exactly "true"/"false"/"unknown" (case-insensitive) --
    any other string, or any other type, is rejected outright rather than
    coerced by Python truthiness (which would turn "false" into True)."""

    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, str):
        folded = value.strip().casefold()
        if folded == "true":
            return True
        if folded == "false":
            return False
        if folded in {"unknown", ""}:
            return None
        raise NeutralVenueError(f"neutral_site string is not a strict boolean: {value!r}")
    raise NeutralVenueError(f"neutral_site must be bool/None/strict string, got {value!r}")


def _finite_nonneg_distance(value: Any, *, label: str) -> float | None:
    """`None` (unknown) is preserved as-is; anything else must be a finite,
    nonnegative real number -- NaN, infinities and negative distances raise
    rather than being silently accepted."""

    if value is None:
        return None
    if isinstance(value, bool):
        raise NeutralVenueError(f"{label} distance must be numeric, not boolean")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise NeutralVenueError(f"{label} distance is not numeric: {value!r}") from exc
    if not math.isfinite(number) or number < 0:
        raise NeutralVenueError(
            f"{label} distance must be finite and nonnegative, got {value!r}"
        )
    return number


def travel_context(
    contest: Mapping[str, Any],
    *,
    home_distance: float | None,
    away_distance: float | None,
    venue_confirmed: bool,
) -> dict[str, Any]:
    """Retain administrative home/away plus actual venue and both travel legs."""

    if not venue_confirmed:
        raise NeutralVenueError(
            "distance from an inferred stadium is not confirmed historical travel"
        )
    if "neutral_site" not in contest:
        raise NeutralVenueError("neutral_site must come from venue/contest authority")
    neutral = _resolve_neutral_site(contest.get("neutral_site"))
    neutral_state = "UNKNOWN" if neutral is None else ("TRUE" if neutral else "FALSE")
    home_valid = _finite_nonneg_distance(home_distance, label="home")
    away_valid = _finite_nonneg_distance(away_distance, label="away")
    return {
        "canonical_contest_id": contest.get("canonical_contest_id"),
        "administrative_home_id": contest.get("administrative_home_id")
        or contest.get("home_canonical_team_id"),
        "administrative_away_id": contest.get("administrative_away_id")
        or contest.get("away_canonical_team_id"),
        "neutral_site": neutral,
        "neutral_state": neutral_state,
        "venue_id": contest.get("venue_id"),
        "venue_timezone": contest.get("venue_timezone"),
        "home_travel_distance": home_valid,
        "away_travel_distance": away_valid,
        "ordinary_home_advantage": ordinary_home_advantage(neutral_site=neutral),
        "asymmetric_travel_is_separate_feature": True,
        "inferred_stadium_distance_forbidden": True,
        "unknown_neutral_is_not_false": True,
        "pit_admitted": False,
    }

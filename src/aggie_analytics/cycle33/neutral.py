"""Neutral-site context. Ordinary home advantage is not applicable."""

from __future__ import annotations

from typing import Any, Mapping


class NeutralVenueError(ValueError):
    """Raised when a neutral contest is labeled as ordinary home advantage."""


def ordinary_home_advantage(*, neutral_site: bool) -> float | None:
    """Zero/not-applicable at neutral sites. Do not infer from stadium names."""

    if neutral_site:
        return 0.0
    return None


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
    neutral = bool(contest.get("neutral_site"))
    return {
        "canonical_contest_id": contest.get("canonical_contest_id"),
        "administrative_home_id": contest.get("administrative_home_id")
        or contest.get("home_canonical_team_id"),
        "administrative_away_id": contest.get("administrative_away_id")
        or contest.get("away_canonical_team_id"),
        "neutral_site": neutral,
        "venue_id": contest.get("venue_id"),
        "venue_timezone": contest.get("venue_timezone"),
        "home_travel_distance": home_distance,
        "away_travel_distance": away_distance,
        "ordinary_home_advantage": ordinary_home_advantage(neutral_site=neutral),
        "asymmetric_travel_is_separate_feature": True,
        "inferred_stadium_distance_forbidden": True,
        "pit_admitted": False,
    }

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


#: Identity fields a travel value is meaningless without. A distance is a
#: measurement between two places for one contest; without the contest, both
#: participants, the venue version and the venue's timezone there is nothing
#: the number is a measurement *of*.
REQUIRED_TRAVEL_IDENTITY_FIELDS = (
    "canonical_contest_id",
    "administrative_home_id",
    "administrative_away_id",
    "venue_id",
    "venue_version",
    "venue_timezone",
)

DISTANCE_UNIT = "KILOMETRES"


def _strict_bool(value: Any, *, label: str) -> bool:
    """Exactly True or False.

    MR34-08 repair: `if not venue_confirmed` reads the string `"false"` as
    confirmation -- the precise inversion of what the source said. A
    confirmation flag that its own type can silently invert is not a flag.
    """

    if isinstance(value, bool):
        return value
    raise NeutralVenueError(
        f"{label} must be a real boolean, got {type(value).__name__} {value!r}"
    )


def travel_context(
    contest: Mapping[str, Any],
    *,
    home_distance: float | None,
    away_distance: float | None,
    venue_confirmed: bool,
    distance_unit: str = DISTANCE_UNIT,
    distance_method: str | None = None,
    require_identities: bool = True,
) -> dict[str, Any]:
    """Retain administrative home/away plus actual venue and both travel legs.

    MR34-08 repair, two parts. `venue_confirmed` is type-checked rather than
    tested for truthiness, so the string `"false"` raises instead of
    confirming. And the identity fields are required rather than emitted as
    `None`: the previous version returned a complete-looking travel context
    whose contest, both participants, venue and timezone were all null --
    two numbers with nothing attached to them. Missing authority is reported
    as a refusal, not as a populated row with empty identities.

    `require_identities=False` remains available for the genuinely partial
    case where a caller wants only the neutral/unknown classification; it is
    explicit at the call site and recorded in the result, so a consumer can
    never mistake a partial answer for a bound one.
    """

    if not _strict_bool(venue_confirmed, label="venue_confirmed"):
        raise NeutralVenueError(
            "distance from an inferred stadium is not confirmed historical travel"
        )
    if "neutral_site" not in contest:
        raise NeutralVenueError("neutral_site must come from venue/contest authority")
    neutral = _resolve_neutral_site(contest.get("neutral_site"))
    neutral_state = "UNKNOWN" if neutral is None else ("TRUE" if neutral else "FALSE")

    identities = {
        "canonical_contest_id": contest.get("canonical_contest_id"),
        "administrative_home_id": contest.get("administrative_home_id")
        or contest.get("home_canonical_team_id"),
        "administrative_away_id": contest.get("administrative_away_id")
        or contest.get("away_canonical_team_id"),
        "venue_id": contest.get("venue_id"),
        "venue_version": contest.get("venue_version"),
        "venue_timezone": contest.get("venue_timezone"),
    }
    missing = [
        field
        for field in REQUIRED_TRAVEL_IDENTITY_FIELDS
        if not str(identities.get(field) or "").strip()
    ]
    if require_identities and missing:
        raise NeutralVenueError(
            "travel context requires bound identities; missing: " + ", ".join(missing)
        )

    home_valid = _finite_nonneg_distance(home_distance, label="home")
    away_valid = _finite_nonneg_distance(away_distance, label="away")
    has_distance = home_valid is not None or away_valid is not None
    if require_identities and has_distance and not str(distance_method or "").strip():
        raise NeutralVenueError("a travel distance requires a declared distance_method")
    return {
        **identities,
        "neutral_site": neutral,
        "neutral_state": neutral_state,
        "home_travel_distance": home_valid,
        "away_travel_distance": away_valid,
        "distance_unit": distance_unit if has_distance else None,
        "distance_method": distance_method,
        "missing_identity_fields": missing,
        "identities_required": require_identities,
        "ordinary_home_advantage": ordinary_home_advantage(neutral_site=neutral),
        "asymmetric_travel_is_separate_feature": True,
        "inferred_stadium_distance_forbidden": True,
        "unknown_neutral_is_not_false": True,
        "pit_admitted": False,
    }

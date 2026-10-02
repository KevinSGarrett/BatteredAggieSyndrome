"""Explicit input vintage for team home geography, and two travel legs.

MR35R-09 reproduced the defect with a two-file probe: Cycle #35's
``load_team_home_venues`` does

    files = sorted(directory.glob("*.json"))
    ...
    by_team.setdefault(int(team["id"]), {...})

so the winning coordinates are whichever payload sorts first by *filename*.
The filenames are request-identity hashes, which have no relationship to
when the payload describes. The manager swapped two filenames holding the
same two observations and got different coordinates, both labelled
``CURRENT_VINTAGE_HOME_VENUE_NOT_PIT``.

This module selects by a declared policy over declared vintages instead:

* every payload contributes only if its **declared acquisition year** is
  known, because a file of unknown vintage cannot be ranked against one of
  known vintage;
* a policy (``LATEST_DECLARED_YEAR`` or ``EARLIEST_DECLARED_YEAR``) picks
  among years, never among filenames;
* two payloads of the **same** declared year that disagree about a team
  leave that team ``CONFLICT_SAME_VINTAGE_DISAGREES`` with both readings
  retained -- unknown, not first-wins.

Selection is also stable under input permutation by construction: the
result depends on (declared year, observed value) only, and the tests
permute the inputs to prove it.

Travel is two legs. TP36-06: "A neutral contest suppresses ordinary home
advantage but still has two travel legs." Both teams travel from their own
reference origin to the actual venue, and a leg whose identities or
coordinates are missing is ``None`` -- never zero, because zero is a
distance and missing is not.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

VINTAGE_VERSION = "BAS-VENUE-VINTAGE-v36.1"

POLICY_LATEST = "LATEST_DECLARED_YEAR"
POLICY_EARLIEST = "EARLIEST_DECLARED_YEAR"
POLICIES = (POLICY_LATEST, POLICY_EARLIEST)

SELECTED = "SELECTED_BY_DECLARED_VINTAGE"
CONFLICT_SAME_VINTAGE = "CONFLICT_SAME_VINTAGE_DISAGREES"
NO_KNOWN_VINTAGE = "NO_PAYLOAD_WITH_A_KNOWN_DECLARED_VINTAGE"

#: Earth radius used for the great-circle reference distance. Declared so
#: an independent checker can reproduce the number exactly.
EARTH_RADIUS_KM = 6371.0088
KM_PER_MILE = 1.609344


@dataclass(frozen=True)
class HomeObservation:
    """One team-home reading from one payload of one declared vintage."""

    team_id: int
    declared_year: int | None
    payload_sha256: str
    payload_path: str
    venue_id: Any
    venue_name: str | None
    latitude: float | None
    longitude: float | None

    @property
    def point(self) -> tuple[float, float] | None:
        if self.latitude is None or self.longitude is None:
            return None
        return (self.latitude, self.longitude)

    def as_dict(self) -> dict[str, Any]:
        return {
            "team_id": self.team_id,
            "declared_year": self.declared_year,
            "payload_sha256": self.payload_sha256,
            "payload_path": self.payload_path,
            "home_venue_id": self.venue_id,
            "home_venue_name": self.venue_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


def observations_from_payloads(
    payloads: Iterable[tuple[int | None, str, str, Sequence[Mapping[str, Any]]]]
) -> list[HomeObservation]:
    """Flatten ``(declared_year, digest, path, rows)`` into observations."""

    found: list[HomeObservation] = []
    for declared_year, digest, path, rows in payloads:
        for team in rows:
            if not isinstance(team, Mapping) or team.get("id") is None:
                continue
            location = team.get("location") or {}
            found.append(
                HomeObservation(
                    team_id=int(team["id"]),
                    declared_year=(
                        int(declared_year) if declared_year is not None else None
                    ),
                    payload_sha256=digest,
                    payload_path=path,
                    venue_id=location.get("id"),
                    venue_name=location.get("name"),
                    latitude=(
                        float(location["latitude"])
                        if location.get("latitude") is not None
                        else None
                    ),
                    longitude=(
                        float(location["longitude"])
                        if location.get("longitude") is not None
                        else None
                    ),
                )
            )
    return found


def _comparable(observation: HomeObservation) -> tuple:
    return (
        observation.venue_id,
        observation.venue_name,
        observation.latitude,
        observation.longitude,
    )


def select_home_geography(
    observations: Iterable[HomeObservation], policy: str = POLICY_LATEST
) -> dict[int, dict[str, Any]]:
    """One home-geography record per team, chosen by declared vintage.

    Nothing about filename order, iteration order or first occurrence takes
    part. A team whose only readings have no declared vintage is reported
    as such rather than being filled from an unrankable file.
    """

    if policy not in POLICIES:
        raise ValueError(f"unknown vintage policy: {policy}")
    grouped: dict[int, list[HomeObservation]] = {}
    for observation in observations:
        grouped.setdefault(observation.team_id, []).append(observation)

    selected: dict[int, dict[str, Any]] = {}
    for team_id, rows in grouped.items():
        dated = [row for row in rows if row.declared_year is not None]
        record: dict[str, Any] = {
            "team_id": team_id,
            "vintage_policy": policy,
            "vintage_version": VINTAGE_VERSION,
            "observations_total": len(rows),
            "observations_with_a_declared_vintage": len(dated),
            "declared_years": sorted({row.declared_year for row in dated}),
            "vintage_authority": "CURRENT_VINTAGE_HOME_VENUE_NOT_PIT",
        }
        if not dated:
            record.update(
                state=NO_KNOWN_VINTAGE,
                home_venue_id=None,
                home_venue_name=None,
                latitude=None,
                longitude=None,
                detail=(
                    "No payload naming this team has a declared acquisition "
                    "year, so no reading can be ranked against another. A file "
                    "that sorts first is not a vintage."
                ),
                candidates=[row.as_dict() for row in rows[:6]],
            )
            selected[team_id] = record
            continue

        chosen_year = (
            max(row.declared_year for row in dated)
            if policy == POLICY_LATEST
            else min(row.declared_year for row in dated)
        )
        at_year = [row for row in dated if row.declared_year == chosen_year]
        distinct = {_comparable(row) for row in at_year}
        record["selected_declared_year"] = chosen_year
        if len(distinct) > 1:
            record.update(
                state=CONFLICT_SAME_VINTAGE,
                home_venue_id=None,
                home_venue_name=None,
                latitude=None,
                longitude=None,
                detail=(
                    "Two payloads of the same declared year disagree about this "
                    "team's home venue. Both readings are retained and nothing "
                    "is selected; picking one would be the first-wins behaviour "
                    "this replaces."
                ),
                candidates=[row.as_dict() for row in at_year],
            )
            selected[team_id] = record
            continue

        winner = at_year[0]
        record.update(
            state=SELECTED,
            home_venue_id=winner.venue_id,
            home_venue_name=winner.venue_name,
            latitude=winner.latitude,
            longitude=winner.longitude,
            payload_sha256=winner.payload_sha256,
            payload_path=winner.payload_path,
            detail=(
                f"Selected the reading from the payload whose declared year is "
                f"{chosen_year} under the {policy} policy. Filename order takes "
                "no part."
            ),
        )
        selected[team_id] = record
    return selected


def great_circle_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres on a sphere of ``EARTH_RADIUS_KM``."""

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


NEUTRAL_SOURCE_DESIGNATED = "SOURCE_DESIGNATED_NEUTRAL"
NEUTRAL_SOURCE_NOT_NEUTRAL = "SOURCE_DESIGNATED_NOT_NEUTRAL"
NEUTRAL_UNKNOWN = "NEUTRAL_STATUS_UNKNOWN"


def ordinary_home_advantage_state(neutral_status: str) -> dict[str, Any]:
    """Whether ordinary home advantage applies, with unknown failing closed.

    A suppressed home advantage is ``0.0`` *only* when the source designates
    the contest neutral. An unknown neutral status does not mean the game was
    ordinary, so the magnitude is ``None`` and the row is not admissible to a
    consumer that needs it. Zero and unknown are different values.
    """

    if neutral_status == NEUTRAL_SOURCE_DESIGNATED:
        return {
            "ordinary_home_advantage_applies": False,
            "ordinary_home_advantage_magnitude": 0.0,
            "basis": "SOURCE_DESIGNATED_NEUTRAL_SUPPRESSES_ORDINARY_HFA",
        }
    if neutral_status == NEUTRAL_SOURCE_NOT_NEUTRAL:
        return {
            "ordinary_home_advantage_applies": True,
            "ordinary_home_advantage_magnitude": None,
            "basis": "ORDINARY_HOME_GAME_MAGNITUDE_IS_SEPARATELY_MODELLED",
        }
    return {
        "ordinary_home_advantage_applies": None,
        "ordinary_home_advantage_magnitude": None,
        "basis": "UNKNOWN_NEUTRAL_STATUS_FAILS_CLOSED",
    }


@dataclass
class TravelLegs:
    """Two reference legs to the actual venue, either of which may be unknown."""

    home_team_id: int | None
    away_team_id: int | None
    venue_point: tuple[float, float] | None
    home_origin: tuple[float, float] | None
    away_origin: tuple[float, float] | None
    notes: list[str] = field(default_factory=list)

    def compute(self) -> dict[str, Any]:
        def leg(origin: tuple[float, float] | None) -> dict[str, Any]:
            if origin is None or self.venue_point is None:
                return {
                    "km": None,
                    "miles": None,
                    "state": "UNKNOWN_MISSING_IDENTITY_OR_COORDINATES",
                }
            km = great_circle_km(*origin, *self.venue_point)
            return {
                "km": km,
                "miles": km / KM_PER_MILE,
                "state": "COMPUTED_FROM_CURRENT_VINTAGE_REFERENCE_ORIGIN",
            }

        home = leg(self.home_origin)
        away = leg(self.away_origin)
        return {
            "vintage_version": VINTAGE_VERSION,
            "designated_home_team_id": self.home_team_id,
            "designated_away_team_id": self.away_team_id,
            "venue_point": list(self.venue_point) if self.venue_point else None,
            "home_leg": home,
            "away_leg": away,
            "legs_computed": sum(
                1 for item in (home, away) if item["km"] is not None
            ),
            "authority": (
                "Each leg is a great-circle distance from a CURRENT-vintage "
                "reference origin to the venue. It is not a point-in-time "
                "historical origin and not an actual itinerary."
            ),
            "notes": list(self.notes),
        }


def travel_for_contest(
    *,
    home_team_id: int | None,
    away_team_id: int | None,
    venue_point: tuple[float, float] | None,
    home_geography: Mapping[int, Mapping[str, Any]],
    neutral_status: str,
) -> dict[str, Any]:
    """Both travel legs plus the ordinary-home-advantage state for one contest.

    Swapping the designated sides swaps the two legs and leaves the venue and
    the neutral state untouched, which is the invariant the regression test
    asserts.
    """

    def origin(team_id: int | None) -> tuple[float, float] | None:
        if team_id is None:
            return None
        record = home_geography.get(int(team_id))
        if not record or record.get("state") != SELECTED:
            return None
        if record.get("latitude") is None or record.get("longitude") is None:
            return None
        return (float(record["latitude"]), float(record["longitude"]))

    legs = TravelLegs(
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        venue_point=venue_point,
        home_origin=origin(home_team_id),
        away_origin=origin(away_team_id),
    ).compute()
    legs.update(ordinary_home_advantage_state(neutral_status))
    legs["neutral_status"] = neutral_status
    return legs

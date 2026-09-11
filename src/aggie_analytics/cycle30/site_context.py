"""National site, venue, travel and ordinary-home semantics.

Designation, physical venue, per-team travel and ordinary HFA are separate facts.
Missing annotation is UNKNOWN, never ordinary home.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from aggie_analytics.cycle30.hashing import sha256_json

SITE_NEUTRAL = "NEUTRAL"
SITE_NON_NEUTRAL = "NON_NEUTRAL"
SITE_UNKNOWN = "UNKNOWN"
SITE_CONFLICT = "CONFLICT"
IUGG_MEAN_RADIUS_KM = 6371.0088
WGS84_A_KM = 6378.137
WGS84_F = 1 / 298.257223563
GEODESIC_DEFINITION = "IUGG_MEAN_RADIUS_HAVERSINE_AND_WGS84_VINCENTY"


class SiteContextError(ValueError):
    """Raised when site/venue/travel contracts fail."""


def classify_site(
    *,
    official_neutral: bool | None,
    provider_neutral: bool | None,
    missing_annotation: bool,
    conflicting: bool = False,
) -> str:
    if conflicting:
        return SITE_CONFLICT
    if missing_annotation and official_neutral is None and provider_neutral is None:
        return SITE_UNKNOWN
    votes = [
        value for value in (official_neutral, provider_neutral) if value is not None
    ]
    if not votes:
        return SITE_UNKNOWN
    if all(votes) and official_neutral is not False:
        return SITE_NEUTRAL
    if any(votes) and not all(
        value is True or value is None for value in (official_neutral, provider_neutral)
    ):
        if official_neutral is True:
            return SITE_NEUTRAL
        if official_neutral is False and provider_neutral is True:
            return SITE_CONFLICT
        if official_neutral is False:
            return SITE_NON_NEUTRAL
    if votes and all(value is False for value in votes):
        return SITE_NON_NEUTRAL
    if official_neutral is True:
        return SITE_NEUTRAL
    if official_neutral is False:
        return SITE_NON_NEUTRAL
    if provider_neutral is True:
        return SITE_UNKNOWN
    return SITE_NON_NEUTRAL


def ordinary_home_exposure(
    *,
    site_class: str,
    orientation_is_designated_home: bool,
) -> float | None:
    if site_class in {SITE_UNKNOWN, SITE_CONFLICT}:
        return None
    if site_class == SITE_NEUTRAL:
        return 0.0
    if site_class == SITE_NON_NEUTRAL:
        return 1.0 if orientation_is_designated_home else 0.0
    raise SiteContextError(f"unknown site class {site_class}")


def contest_context(
    *,
    canonical_game_id: str,
    source_order: Sequence[str],
    canonical_home_id: str,
    canonical_away_id: str,
    designated_home_id: str | None,
    designated_source: str | None,
    site_class: str,
    venue_id: str | None,
    venue_name: str | None,
    venue_lat: float | None,
    venue_lon: float | None,
    missing_reason: str | None = None,
) -> dict[str, Any]:
    if len(source_order) != 2:
        raise SiteContextError("source order must contain two participant IDs")
    permutation = {
        "source_to_canonical_home": list(source_order).index(canonical_home_id)
        if canonical_home_id in source_order
        else None,
        "source_to_canonical_away": list(source_order).index(canonical_away_id)
        if canonical_away_id in source_order
        else None,
    }
    designated = designated_home_id or "UNKNOWN"
    return {
        "canonical_game_id": canonical_game_id,
        "source_order": list(source_order),
        "canonical_home_id": canonical_home_id,
        "canonical_away_id": canonical_away_id,
        "designated_home_id": designated,
        "designated_source": designated_source,
        "site_class": site_class,
        "venue_id": venue_id,
        "venue_name": venue_name,
        "venue_latitude": venue_lat,
        "venue_longitude": venue_lon,
        "ordinary_home_exposure_designated_home": ordinary_home_exposure(
            site_class=site_class, orientation_is_designated_home=True
        ),
        "ordinary_home_exposure_designated_away": ordinary_home_exposure(
            site_class=site_class, orientation_is_designated_home=False
        ),
        "permutation": permutation,
        "missing_reason": missing_reason,
        "display_order_is_not_designated_home": True,
    }


def _radians(degrees: float) -> float:
    return degrees * math.pi / 180.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Spherical great-circle kilometres using the IUGG mean radius."""

    phi1, phi2 = _radians(lat1), _radians(lat2)
    dphi = _radians(lat2 - lat1)
    dlmb = _radians(lon2 - lon1)
    chord = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    )
    return 2 * IUGG_MEAN_RADIUS_KM * math.asin(min(1.0, math.sqrt(chord)))


def vincenty_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Independent WGS84 inverse geodesic (Vincenty), kilometres."""

    if (lat1, lon1) == (lat2, lon2):
        return 0.0
    phi1, phi2 = _radians(lat1), _radians(lat2)
    lmb = _radians(lon2 - lon1)
    u1 = math.atan((1 - WGS84_F) * math.tan(phi1))
    u2 = math.atan((1 - WGS84_F) * math.tan(phi2))
    sin_u1, cos_u1 = math.sin(u1), math.cos(u1)
    sin_u2, cos_u2 = math.sin(u2), math.cos(u2)
    lam = lmb
    for _ in range(100):
        sin_lam, cos_lam = math.sin(lam), math.cos(lam)
        sin_sigma = math.sqrt(
            (cos_u2 * sin_lam) ** 2 + (cos_u1 * sin_u2 - sin_u1 * cos_u2 * cos_lam) ** 2
        )
        if sin_sigma == 0:
            return 0.0
        cos_sigma = sin_u1 * sin_u2 + cos_u1 * cos_u2 * cos_lam
        sigma = math.atan2(sin_sigma, cos_sigma)
        sin_alpha = cos_u1 * cos_u2 * sin_lam / sin_sigma
        cos2_alpha = 1 - sin_alpha**2
        cos_2sigma_m = (
            cos_sigma - 2 * sin_u1 * sin_u2 / cos2_alpha if cos2_alpha else 0.0
        )
        c = WGS84_F / 16 * cos2_alpha * (2 + WGS84_F * (4 - 3 * cos2_alpha))
        lam_prev = lam
        lam = lmb + (1 - c) * WGS84_F * sin_alpha * (
            sigma
            + c
            * sin_sigma
            * (cos_2sigma_m + c * cos_sigma * (-1 + 2 * cos_2sigma_m**2))
        )
        if abs(lam - lam_prev) < 1e-12:
            break
    b = WGS84_A_KM * (1 - WGS84_F)
    u2 = cos2_alpha * (WGS84_A_KM**2 - b**2) / b**2
    a = 1 + u2 / 16384 * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)))
    b_coeff = u2 / 1024 * (256 + u2 * (-128 + u2 * (74 - 47 * u2)))
    delta_sigma = (
        b_coeff
        * sin_sigma
        * (
            cos_2sigma_m
            + b_coeff
            / 4
            * (
                cos_sigma * (-1 + 2 * cos_2sigma_m**2)
                - b_coeff
                / 6
                * cos_2sigma_m
                * (-3 + 4 * sin_sigma**2)
                * (-3 + 4 * cos_2sigma_m**2)
            )
        )
    )
    return b * a * (sigma - delta_sigma)


def missing_coordinate_reason(
    *,
    origin_lat: float | None,
    origin_lon: float | None,
    venue_lat: float | None,
    venue_lon: float | None,
) -> str | None:
    origin_missing = origin_lat is None or origin_lon is None
    venue_missing = venue_lat is None or venue_lon is None
    if not origin_missing and not venue_missing:
        return None
    if origin_missing and venue_missing:
        return "MISSING_COORDINATES"
    if origin_missing:
        return "MISSING_ORIGIN"
    return "MISSING_VENUE"


def venue_index_by_name(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    """Exact casefold name index. Not a default and not fuzzy matching."""

    out: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        name = str(row.get("name") or "").casefold().strip()
        if not name:
            continue
        out.setdefault(name, row)
    return out


def venue_from_bowl_note(
    notes: str, venues_by_name: Mapping[str, Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    """Join CFBD bowl/site notes onto an exact venue-name index.

    Short tokens are not used. This is not a home-stadium default.
    """

    text = str(notes or "").casefold().strip()
    if len(text) < 8:
        return None
    exact = venues_by_name.get(text)
    if exact:
        return exact
    best: Mapping[str, Any] | None = None
    best_len = 0
    for name, venue in venues_by_name.items():
        if len(name) < 10:
            continue
        if name in text or text in name:
            if len(name) > best_len:
                best = venue
                best_len = len(name)
    return best


def travel_gap_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "travel_with_coordinates": sum(
            1 for row in rows if row.get("distance_km_haversine") is not None
        ),
        "missing_origin": sum(
            1 for row in rows if row.get("missing_reason") == "MISSING_ORIGIN"
        ),
        "missing_venue": sum(
            1 for row in rows if row.get("missing_reason") == "MISSING_VENUE"
        ),
        "missing_coordinates": sum(
            1 for row in rows if row.get("missing_reason") == "MISSING_COORDINATES"
        ),
    }


def travel_row(
    *,
    canonical_game_id: str,
    team_id: str,
    origin_lat: float | None,
    origin_lon: float | None,
    venue_lat: float | None,
    venue_lon: float | None,
    origin_class: str,
    origin_id: str | None,
    origin_coordinate_precision: str | None = None,
    venue_coordinate_precision: str | None = None,
    origin_known_at_utc: str | None = None,
    venue_known_at_utc: str | None = None,
) -> dict[str, Any]:
    reason = missing_coordinate_reason(
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        venue_lat=venue_lat,
        venue_lon=venue_lon,
    )
    geodesic_metadata = {
        "geodesic_definition": GEODESIC_DEFINITION,
        "origin_coordinate_precision": origin_coordinate_precision,
        "venue_coordinate_precision": venue_coordinate_precision,
        "origin_known_at_utc": origin_known_at_utc,
        "venue_known_at_utc": venue_known_at_utc,
    }
    if reason is not None:
        return {
            "canonical_game_id": canonical_game_id,
            "team_id": team_id,
            "origin_class": origin_class,
            "origin_id": origin_id,
            "origin_latitude": origin_lat,
            "origin_longitude": origin_lon,
            "venue_latitude": venue_lat,
            "venue_longitude": venue_lon,
            "distance_km_haversine": None,
            "distance_km_vincenty": None,
            "units": "km",
            **geodesic_metadata,
            "missing_reason": reason,
            "proximity_is_not_home_bonus": True,
            "model_consumed": False,
        }
    haver = haversine_km(origin_lat, origin_lon, venue_lat, venue_lon)
    vincenty = vincenty_km(origin_lat, origin_lon, venue_lat, venue_lon)
    if abs(haver - vincenty) > 25.0 and min(haver, vincenty) > 0:
        raise SiteContextError(
            f"haversine/vincenty disagreement {haver} vs {vincenty} exceeds 25 km"
        )
    return {
        "canonical_game_id": canonical_game_id,
        "team_id": team_id,
        "origin_class": origin_class,
        "origin_id": origin_id,
        "origin_latitude": origin_lat,
        "origin_longitude": origin_lon,
        "venue_latitude": venue_lat,
        "venue_longitude": venue_lon,
        "distance_km_haversine": round(haver, 6),
        "distance_km_vincenty": round(vincenty, 6),
        "radius_km": IUGG_MEAN_RADIUS_KM,
        "units": "km",
        **geodesic_metadata,
        "methods_not_identical": True,
        "proximity_is_not_home_bonus": True,
        "model_consumed": False,
        "missing_reason": None,
    }


def designation_swap_invariant(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> None:
    if (
        left.get("site_class") != SITE_NEUTRAL
        or right.get("site_class") != SITE_NEUTRAL
    ):
        raise SiteContextError(
            "designation-swap invariant applies to verified neutrals"
        )
    team_keys = {"travel", "ordinary_home_exposure", "strength"}
    for key in team_keys:
        if key in left and key in right and left[key] != right[key]:
            raise SiteContextError(f"neutral designation swap changed team-keyed {key}")


def persist_design_row(
    *,
    canonical_game_id: str,
    ordinary_home_exposure_value: float | None,
    site_class: str,
    travel_home_km: float | None,
    travel_away_km: float | None,
    consumed_columns: Sequence[str],
) -> dict[str, Any]:
    travel_consumed = (
        "travel_home_km" in consumed_columns or "travel_away_km" in consumed_columns
    )
    return {
        "canonical_game_id": canonical_game_id,
        "ordinary_home_exposure": ordinary_home_exposure_value,
        "site_class": site_class,
        "travel_home_km": travel_home_km,
        "travel_away_km": travel_away_km,
        "consumed_columns": list(consumed_columns),
        "travel_available": travel_home_km is not None and travel_away_km is not None,
        "travel_consumed": travel_consumed,
        "context_available_is_not_model_consumed": True,
        "feature_version": "cycle30-ordinary-home-exposure-v1",
        "row_identity": sha256_json(
            {
                "canonical_game_id": canonical_game_id,
                "ordinary_home_exposure": ordinary_home_exposure_value,
                "site_class": site_class,
            }
        ),
    }

"""Independent site/travel reconstruction using an ellipsoidal check."""

from __future__ import annotations

import math
from typing import Any, Mapping

IUGG_MEAN_RADIUS_KM = 6371.0088


class IndependentSiteError(ValueError):
    """Raised when independent site reconstruction fails."""


def ordinary_home_exposure(site_class: str, designated_home: bool) -> float | None:
    if site_class in {"UNKNOWN", "CONFLICT"}:
        return None
    if site_class == "NEUTRAL":
        return 0.0
    if site_class == "NON_NEUTRAL":
        return 1.0 if designated_home else 0.0
    raise IndependentSiteError(f"unknown site class {site_class}")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    chord = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    )
    return 2 * IUGG_MEAN_RADIUS_KM * math.asin(min(1.0, math.sqrt(chord)))


def compare_travel(
    producer: Mapping[str, Any], *, lat1: float, lon1: float, lat2: float, lon2: float
) -> None:
    independent = haversine_km(lat1, lon1, lat2, lon2)
    reported = producer.get("distance_km_haversine")
    if reported is None:
        raise IndependentSiteError("producer travel distance missing")
    if abs(float(reported) - independent) > 0.05:
        raise IndependentSiteError("independent haversine disagrees with producer")

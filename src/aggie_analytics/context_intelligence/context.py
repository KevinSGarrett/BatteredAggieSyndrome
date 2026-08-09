from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import radians, sin, cos, sqrt, atan2

@dataclass(frozen=True)
class WeatherForecastEvidence:
    evidence_id: str
    model_init_at: datetime
    model_available_at: datetime
    valid_at: datetime
    retrieved_at: datetime

def forecast_eligible(evidence: WeatherForecastEvidence, cutoff: datetime) -> bool:
    return evidence.model_available_at <= cutoff and evidence.retrieved_at <= cutoff

@dataclass(frozen=True)
class TravelContext:
    distance_km: float
    timezone_shift_hours: float
    rest_days: float
    recent_travel_km: float = 0.0
    road_streak: int = 0

class ResourceLane(str, Enum):
    R0_NO_RESOURCES = "R0_NO_RESOURCES"
    R1_UNIVERSAL = "R1_UNIVERSAL"
    R2_PUBLIC_ENRICHED = "R2_PUBLIC_ENRICHED"
    R3_LATENT_CAPACITY_RESEARCH = "R3_LATENT_CAPACITY_RESEARCH"

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius=6371.0088
    p1,p2=radians(lat1),radians(lat2)
    dp=radians(lat2-lat1); dl=radians(lon2-lon1)
    a=sin(dp/2)**2 + cos(p1)*cos(p2)*sin(dl/2)**2
    return 2*radius*atan2(sqrt(a),sqrt(1-a))

def home_residual(actual_margin: float, expected_neutral_margin: float) -> float:
    """Research residual only; not a production home-field bonus."""
    return actual_margin - expected_neutral_margin

def fabricate_private_school_spend(*args, **kwargs) -> float:
    raise RuntimeError("Missing private-school detailed spending may not be fabricated.")

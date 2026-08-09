from .coaching import CoachRoleEpisode, eligible_role, coach_residual, manual_coach_bonus
from .context import WeatherForecastEvidence, forecast_eligible, TravelContext, haversine_km, home_residual, ResourceLane
from .mechanics import hidden_yards, expected_possessions_baseline, crew_feature_eligible, strict_prior_opponent_value

__all__ = [
    "CoachRoleEpisode","eligible_role","coach_residual","manual_coach_bonus",
    "WeatherForecastEvidence","forecast_eligible","TravelContext","haversine_km","home_residual","ResourceLane",
    "hidden_yards","expected_possessions_baseline","crew_feature_eligible","strict_prior_opponent_value",
]

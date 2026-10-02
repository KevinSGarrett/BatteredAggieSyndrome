"""Independent scientific-reference implementations.

These modules must not import producer scoring, metrics, interval, readiness,
crosswalk, median, identity, or feature-binding helpers. Only this package may
authorize SEMANTICALLY_AUDITED or higher claim classifications.
"""

from aggie_analytics.scientific_reference.metrics import (
    accuracy,
    brier_score,
    calibration_bins,
    expected_observed_wins,
    log_loss,
)
from aggie_analytics.scientific_reference.coherence import (
    interval_coverage,
    interval_quantile,
    inverse_normal_cdf,
    joint_distribution_coherent,
    pair_normalize,
    probability_from_normal_residual,
    residual_metrics,
    standard_normal_cdf,
)
from aggie_analytics.scientific_reference.market import even_odd_median, overround
from aggie_analytics.scientific_reference.binding import (
    current_opponent_bound,
    temporal_order_ok,
)

__all__ = [
    "accuracy",
    "brier_score",
    "calibration_bins",
    "current_opponent_bound",
    "even_odd_median",
    "expected_observed_wins",
    "interval_coverage",
    "interval_quantile",
    "inverse_normal_cdf",
    "joint_distribution_coherent",
    "log_loss",
    "overround",
    "pair_normalize",
    "probability_from_normal_residual",
    "residual_metrics",
    "standard_normal_cdf",
    "temporal_order_ok",
]

from __future__ import annotations
from math import exp
from typing import Mapping, Sequence

def exponential_recency_weight(age: float, decay_rate: float) -> float:
    """Parameterized candidate. W11 freezes no default decay rate."""
    if age < 0:
        raise ValueError("age must be non-negative")
    if decay_rate < 0:
        raise ValueError("decay_rate must be non-negative")
    return exp(-decay_rate * age)

def weighted_similarity(factors: Mapping[str, float], weights: Mapping[str, float]) -> float:
    """Explicit, caller-weighted 0..1 regime similarity candidate."""
    if not factors:
        raise ValueError("at least one factor is required")
    if set(factors) != set(weights):
        raise ValueError("factors and weights must have identical keys")
    if any(not 0 <= v <= 1 for v in factors.values()):
        raise ValueError("factor values must be in [0,1]")
    if any(v < 0 for v in weights.values()):
        raise ValueError("weights must be non-negative")
    total=sum(weights.values())
    if total <= 0:
        raise ValueError("weight sum must be positive")
    return sum(factors[k]*weights[k] for k in factors)/total

def combined_history_weight(recency_weight: float, regime_similarity: float, evidence_quality: float=1.0) -> float:
    """Candidate multiplicative relevance, not a production-selected formula."""
    vals=(recency_weight,regime_similarity,evidence_quality)
    if any(not 0 <= v <= 1 for v in vals):
        raise ValueError("all relevance inputs must be in [0,1]")
    return recency_weight*regime_similarity*evidence_quality

def blend_prior_observed(prior: float, observed: float, observed_weight: float) -> float:
    """Generic explicit blend. observed_weight is an experiment parameter."""
    if not 0 <= observed_weight <= 1:
        raise ValueError("observed_weight must be in [0,1]")
    return prior*(1-observed_weight)+observed*observed_weight

def pseudo_count_blend(prior: float, observed_mean: float, observations: int, prior_equivalent: float) -> float:
    """Candidate early-season update with explicit prior pseudo-count."""
    if observations < 0 or prior_equivalent < 0:
        raise ValueError("counts must be non-negative")
    denom=observations+prior_equivalent
    if denom == 0:
        raise ValueError("at least one unit of evidence is required")
    return (prior*prior_equivalent + observed_mean*observations)/denom

def precision_weighted_blend(prior: float, prior_uncertainty: float, observed: float, observed_uncertainty: float) -> float:
    """Reference precision blend; zero uncertainty is rejected rather than treated as certainty."""
    if prior_uncertainty <= 0 or observed_uncertainty <= 0:
        raise ValueError("uncertainties must be positive")
    p1=1/(prior_uncertainty**2); p2=1/(observed_uncertainty**2)
    return (prior*p1+observed*p2)/(p1+p2)

def standardized_shift(before_mean: float, after_mean: float, scale: float) -> float:
    """Change-point candidate score. No W11 threshold is supplied."""
    if scale <= 0:
        raise ValueError("scale must be positive")
    return abs(after_mean-before_mean)/scale

def normalized_history_weights(raw_weights: Sequence[float]) -> tuple[float,...]:
    if not raw_weights or any(w < 0 for w in raw_weights):
        raise ValueError("non-empty non-negative weights required")
    total=sum(raw_weights)
    if total <= 0:
        raise ValueError("weight sum must be positive")
    return tuple(w/total for w in raw_weights)

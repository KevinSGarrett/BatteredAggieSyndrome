from __future__ import annotations

from .contracts import PublishedForecastSnapshot


def explanation_view(snapshot: PublishedForecastSnapshot) -> dict[str, object]:
    """Render only precomputed publication evidence; never run SHAP/models in serving."""
    return {
        "claim_scope": "PRECOMPUTED_ASSOCIATIONAL_NOT_CAUSAL",
        "matchup_drivers": [dict(x) for x in snapshot.matchup_explanation],
        "availability": [dict(x) for x in snapshot.availability],
        "historical_analogs": [dict(x) for x in snapshot.historical_analogs],
        "comparison_context": dict(snapshot.comparison_context),
    }

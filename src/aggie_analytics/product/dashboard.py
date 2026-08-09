from __future__ import annotations

from datetime import datetime

from .service import ForecastProductService


def dashboard_view_model(service: ForecastProductService, game_id: str, *, market_lane: str = "PURE_FOOTBALL", now: datetime | None = None) -> dict[str, object]:
    """Framework-neutral dashboard view model used by UI adapters/tests."""
    payload = service.forecast(game_id, market_lane=market_lane, now=now)
    return {
        "title": f"{payload['game']['team_name']} vs {payload['game']['opponent_name']}",
        "headline": payload["forecast"],
        "bas": payload["bas"],
        "uncertainty": payload["uncertainty"],
        "freshness": payload["freshness"],
        "warnings": payload["warnings"],
        "availability": payload["explainability"]["availability"],
        "matchup_drivers": payload["explainability"]["matchup_drivers"],
        "historical_analogs": payload["explainability"]["historical_analogs"],
        "comparison_context": payload["explainability"]["comparison_context"],
        "lineage": payload["lineage"],
        "snapshot": payload["snapshot"],
    }

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .contracts import PublishedForecastSnapshot


@dataclass(frozen=True)
class FreshnessPolicy:
    """Product freshness classifier.

    THR-010 remains operationally TBD. If max_forecast_age is None, serving exposes
    exact timestamps/age but refuses to label the snapshot CURRENT.
    """
    max_forecast_age: timedelta | None = None

    def assess(self, snapshot: PublishedForecastSnapshot, *, now: datetime | None = None) -> dict[str, object]:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        if now < snapshot.published_at:
            return {
                "state": "NOT_YET_PUBLISHED_AT_AS_OF",
                "stale": None,
                "served_at": now.isoformat(),
                "forecast_cutoff": snapshot.forecast_cutoff.isoformat(),
                "published_at": snapshot.published_at.isoformat(),
                "forecast_age_seconds": None,
                "threshold_seconds": None if self.max_forecast_age is None else self.max_forecast_age.total_seconds(),
            }
        age = now - snapshot.forecast_cutoff
        if self.max_forecast_age is None:
            state, stale = "UNASSESSED_THRESHOLD_TBD", None
            threshold = None
        else:
            threshold = self.max_forecast_age.total_seconds()
            stale = age > self.max_forecast_age
            state = "STALE" if stale else "CURRENT_WITHIN_CONFIGURED_THRESHOLD"
        return {
            "state": state,
            "stale": stale,
            "served_at": now.isoformat(),
            "forecast_cutoff": snapshot.forecast_cutoff.isoformat(),
            "published_at": snapshot.published_at.isoformat(),
            "forecast_age_seconds": max(0.0, age.total_seconds()),
            "threshold_seconds": threshold,
        }

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .contracts import PublishedForecastSnapshot
from .explainability import explanation_view
from .freshness import FreshnessPolicy
from .repository import PublishedSnapshotRepository


class ForecastProductService:
    """Read-only serving facade over immutable published snapshots."""

    def __init__(self, repository: PublishedSnapshotRepository, freshness_policy: FreshnessPolicy | None = None):
        self.repository = repository
        self.freshness_policy = freshness_policy or FreshnessPolicy()

    def health(self) -> dict[str, object]:
        return {"status": "ok", "serving_mode": "IMMUTABLE_PUBLISHED_SNAPSHOT_ONLY", "api_version": "v1"}

    def games(self, *, now: datetime | None = None) -> dict[str, object]:
        now = now or datetime.now(timezone.utc)
        rows: list[dict[str, object]] = []
        for game_id in self.repository.list_games():
            snapshots = self.repository.list_snapshots(game_id)
            eligible = [s for s in snapshots if s.forecast_cutoff <= now and s.published_at <= now]
            latest = max(eligible, key=lambda s: (s.forecast_cutoff, s.published_at, s.snapshot_id)) if eligible else None
            rows.append({
                "game_id": game_id,
                "snapshot_count": len(snapshots),
                "latest_snapshot_id": latest.snapshot_id if latest else None,
                "latest_forecast_cutoff": latest.forecast_cutoff.isoformat() if latest else None,
                "available_market_lanes": sorted({s.market_lane for s in eligible}),
            })
        return {"api_version": "v1", "games": rows}

    def snapshots(self, game_id: str) -> dict[str, object]:
        rows = [{
            "snapshot_id": s.snapshot_id,
            "forecast_cutoff": s.forecast_cutoff.isoformat(),
            "published_at": s.published_at.isoformat(),
            "market_lane": s.market_lane,
            "schema_version": s.schema_version,
        } for s in self.repository.list_snapshots(game_id)]
        return {"api_version": "v1", "game_id": game_id, "snapshots": rows}

    def _select(
        self,
        game_id: str,
        *,
        snapshot_id: str | None,
        market_lane: str | None,
        now: datetime,
    ) -> PublishedForecastSnapshot:
        if snapshot_id:
            snapshot = self.repository.get(game_id, snapshot_id, market_lane=market_lane)
            if snapshot.forecast_cutoff > now or snapshot.published_at > now:
                raise KeyError("requested snapshot is not eligible at supplied as_of")
            return snapshot
        return self.repository.latest(game_id, market_lane=market_lane or "PURE_FOOTBALL", as_of=now)

    def forecast(
        self,
        game_id: str,
        *,
        snapshot_id: str | None = None,
        market_lane: str | None = "PURE_FOOTBALL",
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        snapshot = self._select(game_id, snapshot_id=snapshot_id, market_lane=market_lane, now=now)
        freshness = self.freshness_policy.assess(snapshot, now=now)
        summary = dict(snapshot.public_summary)
        bas = {key.removeprefix("bas_"): value for key, value in summary.items() if key.startswith("bas_")}
        core = {key: value for key, value in summary.items() if not key.startswith("bas_")}
        warnings = list(snapshot.warnings)
        if freshness["state"] == "STALE":
            warnings.append("FORECAST_STALE_AT_SERVE_TIME")
        elif freshness["state"] == "UNASSESSED_THRESHOLD_TBD":
            warnings.append("FRESHNESS_THRESHOLD_NOT_OPERATIONALLY_FROZEN")
        return {
            "api_version": "v1",
            "serving_mode": "IMMUTABLE_PUBLISHED_SNAPSHOT_ONLY",
            "game": {"game_id": snapshot.game_id, "team_name": snapshot.team_name, "opponent_name": snapshot.opponent_name},
            "snapshot": {
                "snapshot_id": snapshot.snapshot_id,
                "schema_version": snapshot.schema_version,
                "forecast_cutoff": snapshot.forecast_cutoff.isoformat(),
                "published_at": snapshot.published_at.isoformat(),
                "market_lane": snapshot.market_lane,
            },
            "forecast": core,
            "bas": bas,
            "uncertainty": [dict(x) for x in snapshot.uncertainty],
            "freshness": freshness,
            "warnings": warnings,
            "explainability": explanation_view(snapshot),
            "lineage": self._lineage_payload(snapshot),
            "public_metadata": dict(snapshot.public_metadata),
        }

    def lineage(self, game_id: str, snapshot_id: str, *, market_lane: str | None = None) -> dict[str, object]:
        snapshot = self.repository.get(game_id, snapshot_id, market_lane=market_lane)
        return {
            "api_version": "v1",
            "game_id": game_id,
            "snapshot_id": snapshot_id,
            "lineage": self._lineage_payload(snapshot),
        }

    @staticmethod
    def _lineage_payload(snapshot: PublishedForecastSnapshot) -> dict[str, object]:
        return {
            "model_artifact_sha256": snapshot.model_artifact_sha256,
            "feature_snapshot_id": snapshot.feature_snapshot_id,
            "data_snapshot_refs": list(snapshot.data_snapshot_refs),
            "lineage_refs": list(snapshot.lineage_refs),
            "source_metadata": [dict(x) for x in snapshot.source_metadata],
            "model_metadata": dict(snapshot.model_metadata),
            "artifact_ref": snapshot.artifact_ref,
        }

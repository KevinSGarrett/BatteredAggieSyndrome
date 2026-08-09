from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
import json, os, tempfile

from .contracts import stable_hash


class ImmutableForecastPublisher:
    """Publishes immutable forecast snapshots; never overwrites a prior snapshot.

    W22 extends the W21 envelope with optional product metadata. The old W21
    call signature remains valid, and serving still reads only published files.
    """
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def publish(
        self,
        *,
        snapshot_id: str,
        game_id: str,
        forecast_cutoff: datetime,
        model_artifact_sha256: str,
        feature_snapshot_id: str,
        public_summary: dict[str, float],
        lineage_refs: tuple[str, ...],
        schema_version: str = "aggie.forecast.snapshot.v2",
        market_lane: str = "PURE_FOOTBALL",
        teams: Mapping[str, str] | None = None,
        uncertainty: Sequence[Mapping[str, Any]] | None = None,
        warnings: Sequence[str] | None = None,
        availability: Sequence[Mapping[str, Any]] | None = None,
        matchup_explanation: Sequence[Mapping[str, Any]] | None = None,
        historical_analogs: Sequence[Mapping[str, Any]] | None = None,
        source_metadata: Sequence[Mapping[str, Any]] | None = None,
        model_metadata: Mapping[str, Any] | None = None,
        data_snapshot_refs: Sequence[str] | None = None,
        comparison_context: Mapping[str, Any] | None = None,
        public_metadata: Mapping[str, Any] | None = None,
    ) -> str:
        if forecast_cutoff.tzinfo is None or not all((snapshot_id, game_id, model_artifact_sha256, feature_snapshot_id)) or not lineage_refs:
            raise ValueError("forecast publication requires PIT-safe identity and lineage")
        if market_lane not in {"PURE_FOOTBALL", "MARKET_AUGMENTED"}:
            raise ValueError("market_lane must preserve the pure-football/market-augmented split")
        payload = {
            "schema_version": schema_version,
            "snapshot_id": snapshot_id,
            "game_id": game_id,
            "forecast_cutoff": forecast_cutoff.isoformat(),
            "model_artifact_sha256": model_artifact_sha256,
            "feature_snapshot_id": feature_snapshot_id,
            "public_summary": dict(public_summary),
            "lineage_refs": list(lineage_refs),
            "market_lane": market_lane,
            "teams": dict(teams or {}),
            "uncertainty": [dict(x) for x in (uncertainty or ())],
            "warnings": [str(x) for x in (warnings or ())],
            "availability": [dict(x) for x in (availability or ())],
            "matchup_explanation": [dict(x) for x in (matchup_explanation or ())],
            "historical_analogs": [dict(x) for x in (historical_analogs or ())],
            "source_metadata": [dict(x) for x in (source_metadata or ())],
            "model_metadata": dict(model_metadata or {}),
            "data_snapshot_refs": [str(x) for x in (data_snapshot_refs or ())],
            "comparison_context": dict(comparison_context or {}),
            "public_metadata": dict(public_metadata or {}),
            "published_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }
        content_hash = stable_hash({k: v for k, v in payload.items() if k != "published_at"})
        p = self.root / game_id / f"{snapshot_id}-{content_hash}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        siblings = list(p.parent.glob(f"{snapshot_id}-*.json"))
        if siblings and p not in siblings:
            raise RuntimeError("immutable snapshot_id collision with different content")
        if not p.exists():
            fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".forecast.", suffix=".tmp")
            os.close(fd)
            Path(tmp).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            os.replace(tmp, p)
        return str(p)

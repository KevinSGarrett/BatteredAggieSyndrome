from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .contracts import PublishedForecastSnapshot


class SnapshotNotFound(KeyError):
    pass


class PublishedSnapshotRepository:
    """Read-only repository over W21+ immutable published forecast JSON artifacts."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def _game_dir(self, game_id: str) -> Path:
        if not game_id or game_id in {".", ".."} or "/" in game_id or "\\" in game_id:
            raise ValueError("unsafe game_id")
        return self.root / game_id

    def _load(self, path: Path) -> PublishedForecastSnapshot:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return PublishedForecastSnapshot.from_payload(payload, artifact_ref=str(path))

    def list_games(self) -> tuple[str, ...]:
        if not self.root.exists():
            return ()
        return tuple(sorted(p.name for p in self.root.iterdir() if p.is_dir() and any(p.glob("*.json"))))

    def list_snapshots(self, game_id: str) -> tuple[PublishedForecastSnapshot, ...]:
        game_dir = self._game_dir(game_id)
        if not game_dir.exists():
            return ()
        snapshots = [self._load(p) for p in sorted(game_dir.glob("*.json"))]
        return tuple(sorted(snapshots, key=lambda s: (s.forecast_cutoff, s.published_at, s.snapshot_id)))

    def get(self, game_id: str, snapshot_id: str, *, market_lane: str | None = None) -> PublishedForecastSnapshot:
        matches = [s for s in self.list_snapshots(game_id) if s.snapshot_id == snapshot_id]
        if market_lane is not None:
            matches = [s for s in matches if s.market_lane == market_lane]
        if not matches:
            raise SnapshotNotFound((game_id, snapshot_id, market_lane))
        if len(matches) > 1:
            raise RuntimeError("snapshot identity is ambiguous across immutable artifacts")
        return matches[0]

    def latest(
        self,
        game_id: str,
        *,
        market_lane: str | None = "PURE_FOOTBALL",
        as_of: datetime | None = None,
    ) -> PublishedForecastSnapshot:
        as_of = as_of or datetime.now(timezone.utc)
        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        candidates = [
            s for s in self.list_snapshots(game_id)
            if s.forecast_cutoff <= as_of and s.published_at <= as_of
            and (market_lane is None or s.market_lane == market_lane)
        ]
        if not candidates:
            raise SnapshotNotFound((game_id, market_lane, as_of.isoformat()))
        return max(candidates, key=lambda s: (s.forecast_cutoff, s.published_at, s.snapshot_id))

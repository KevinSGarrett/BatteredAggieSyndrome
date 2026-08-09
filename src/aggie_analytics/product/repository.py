from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .contracts import PublishedForecastSnapshot


class SnapshotNotFound(KeyError):
    pass


_GAME_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


class PublishedSnapshotRepository:
    """Read-only repository over W21+ immutable published forecast JSON artifacts."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def _game_dir(self, game_id: str) -> Path | None:
        if not isinstance(game_id, str) or _GAME_ID.fullmatch(game_id) is None:
            raise ValueError("unsafe game_id")
        if not self.root.is_dir():
            return None
        for child in self.root.iterdir():
            if child.name != game_id:
                continue
            if child.is_symlink():
                raise ValueError("unsafe game repository entry")
            if not child.is_dir():
                return None
            resolved = child.resolve(strict=True)
            if resolved.parent != self.root:
                raise ValueError("game directory escapes repository root")
            return resolved
        return None

    @staticmethod
    def _snapshot_paths(game_dir: Path) -> tuple[Path, ...]:
        snapshots: list[Path] = []
        for child in game_dir.iterdir():
            if child.suffix.lower() != ".json":
                continue
            if child.is_symlink():
                raise ValueError("unsafe snapshot repository entry")
            if not child.is_file():
                continue
            resolved = child.resolve(strict=True)
            if resolved.parent != game_dir:
                raise ValueError("snapshot path escapes game directory")
            snapshots.append(resolved)
        return tuple(sorted(snapshots))

    def _load(self, path: Path) -> PublishedForecastSnapshot:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return PublishedForecastSnapshot.from_payload(payload, artifact_ref=str(path))

    def list_games(self) -> tuple[str, ...]:
        if not self.root.is_dir():
            return ()
        games: list[str] = []
        for child in self.root.iterdir():
            if child.is_symlink() or not child.is_dir():
                continue
            resolved = child.resolve(strict=True)
            if resolved.parent == self.root and self._snapshot_paths(resolved):
                games.append(child.name)
        return tuple(sorted(games))

    def list_snapshots(self, game_id: str) -> tuple[PublishedForecastSnapshot, ...]:
        game_dir = self._game_dir(game_id)
        if game_dir is None:
            return ()
        snapshots = [self._load(path) for path in self._snapshot_paths(game_dir)]
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

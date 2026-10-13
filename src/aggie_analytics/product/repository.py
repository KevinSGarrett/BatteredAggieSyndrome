from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Mapping
from datetime import datetime, timezone
from pathlib import Path

from .contracts import PublishedForecastSnapshot
from ..orchestration.contracts import stable_hash


class SnapshotNotFound(KeyError):
    pass


_GAME_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


class PublishedSnapshotRepository:
    """Read-only repository over W21+ immutable published forecast JSON artifacts."""

    def __init__(self, root: Path, *, legacy_artifact_sha256: Mapping[str, str] | None = None):
        self.root = Path(root).resolve()
        # Legacy non-content-addressed filenames require separately supplied byte
        # pins, keyed by root-relative POSIX path. A filename change is not a waiver.
        self.legacy_artifact_sha256 = dict(legacy_artifact_sha256 or {})

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

    def _load(self, path: Path, game_id: str) -> PublishedForecastSnapshot:
        raw = path.read_bytes()
        payload = json.loads(raw)
        snapshot = PublishedForecastSnapshot.from_payload(payload, artifact_ref=str(path))
        if snapshot.game_id != game_id or path.parent.name != game_id:
            raise ValueError("published snapshot game identity mismatch")
        if snapshot.schema_version not in {"aggie.forecast.snapshot.v1", "aggie.forecast.snapshot.v2"}:
            raise ValueError("unsupported published snapshot schema")
        publication_format = payload.get("publication_format")
        if publication_format not in {None, "aggie.forecast.publication.v1"}:
            raise ValueError("unsupported publication identity format")
        digest = stable_hash(payload)
        expected = f"{snapshot.snapshot_id}-{digest}.json"
        if publication_format is not None:
            if path.name != expected:
                raise ValueError("published snapshot content identity mismatch")
        else:
            # Original W21/W22 hashes omit the serving timestamp. Require a
            # separately retained byte pin for either legacy naming convention.
            legacy_name = f"{snapshot.snapshot_id}-{snapshot.market_lane}.json"
            legacy_hash = stable_hash({k: v for k, v in payload.items() if k != "published_at"})
            legacy_hashed_name = f"{snapshot.snapshot_id}-{legacy_hash}.json"
            pin = self.legacy_artifact_sha256.get(path.relative_to(self.root).as_posix())
            if path.name not in {legacy_name, legacy_hashed_name} or pin != sha256(raw).hexdigest():
                raise ValueError("legacy published snapshot requires an exact artifact pin")
        return snapshot

    def list_games(self) -> tuple[str, ...]:
        if not self.root.is_dir():
            return ()
        games: list[str] = []
        for child in self.root.iterdir():
            if child.is_symlink() or not child.is_dir():
                continue
            resolved = child.resolve(strict=True)
            if resolved.parent == self.root and self.list_snapshots(child.name):
                games.append(child.name)
        return tuple(sorted(games))

    def list_snapshots(self, game_id: str) -> tuple[PublishedForecastSnapshot, ...]:
        game_dir = self._game_dir(game_id)
        if game_dir is None:
            return ()
        snapshots = [self._load(path, game_id) for path in self._snapshot_paths(game_dir)]
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

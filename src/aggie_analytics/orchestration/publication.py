from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any, Mapping, Sequence
import json, os, re, tempfile

from .contracts import stable_hash


def _publication_component(value: str) -> str:
    if (not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value) is None
            or value.endswith(".") or PureWindowsPath(value).is_reserved()):
        raise ValueError("unsafe publication identifier")
    return value


class ImmutableForecastPublisher:
    """Publishes immutable forecast snapshots; never overwrites a prior snapshot.

    W22 extends the W21 envelope with optional product metadata. The old W21
    call signature remains valid, and serving still reads only published files.
    """
    def __init__(self, root: Path, *, legacy_artifact_sha256: Mapping[str, str] | None = None):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.legacy_artifact_sha256 = dict(legacy_artifact_sha256 or {})

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
        _publication_component(game_id)
        _publication_component(snapshot_id)
        if forecast_cutoff.tzinfo is None or not all((snapshot_id, game_id, model_artifact_sha256, feature_snapshot_id)) or not lineage_refs:
            raise ValueError("forecast publication requires PIT-safe identity and lineage")
        if market_lane not in {"PURE_FOOTBALL", "MARKET_AUGMENTED"}:
            raise ValueError("market_lane must preserve the pure-football/market-augmented split")
        if schema_version not in {"aggie.forecast.snapshot.v1", "aggie.forecast.snapshot.v2"}:
            raise ValueError("unsupported forecast snapshot schema")
        payload = {
            "publication_format": "aggie.forecast.publication.v1",
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
        content_hash = stable_hash(payload)
        p = self.root / game_id / f"{snapshot_id}-{content_hash}.json"
        if p.parent.is_symlink() or p.parent.resolve().parent != self.root:
            raise ValueError("publication game directory escapes root")
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.is_symlink() or p.resolve().parent != p.parent.resolve():
            raise ValueError("publication snapshot escapes game directory")
        siblings = list(p.parent.glob(f"{snapshot_id}-*.json"))
        def verify_existing(path: Path) -> None:
            from ..product.repository import PublishedSnapshotRepository
            try:
                repository = PublishedSnapshotRepository(self.root, legacy_artifact_sha256=self.legacy_artifact_sha256)
                # Use the same path/identity boundary as serving, including time.
                if path not in repository._snapshot_paths(p.parent):
                    raise ValueError("unsafe publication snapshot path")
                repository._load(path, game_id)
            except ValueError as exc:
                raise RuntimeError("immutable snapshot content identity mismatch") from exc
            existing = json.loads(path.read_bytes())
            volatile = {"published_at", "publication_format"}
            if stable_hash({k: v for k, v in existing.items() if k not in volatile}) != stable_hash({k: v for k, v in payload.items() if k not in volatile}):
                raise RuntimeError("immutable snapshot_id collision with different content")

        if siblings:
            if len(siblings) != 1:
                raise RuntimeError("immutable snapshot_id collision with different content")
            verify_existing(siblings[0])
            return str(siblings[0])

        # The content filename includes the call's publication time, so its
        # exclusive hardlink alone cannot serialize two owners of one snapshot.
        # Claim the stable identity and recheck under that claim. A crash leaves
        # the claim in place; no caller guesses that another owner is stale.
        claim = p.parent / f".{snapshot_id}.publish-claim"
        try:
            claim_fd = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise RuntimeError("snapshot publication already in progress; retained claim requires explicit recovery") from exc
        try:
            siblings = list(p.parent.glob(f"{snapshot_id}-*.json"))
            if siblings:
                if len(siblings) != 1:
                    raise RuntimeError("immutable snapshot_id collision with different content")
                verify_existing(siblings[0])
                return str(siblings[0])
            fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".forecast.", suffix=".tmp")
            os.close(fd)
            Path(tmp).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            try:
                # Atomic create-only publication: a concurrent writer is never overwritten.
                try:
                    os.link(tmp, p)
                except FileExistsError:
                    verify_existing(p)
            finally:
                Path(tmp).unlink()
        finally:
            os.close(claim_fd)
            claim.unlink()
        return str(p)

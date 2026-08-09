from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from aggie_analytics.product import ForecastProductService, FreshnessPolicy, PublishedSnapshotRepository, SnapshotNotFound


def create_app(*, snapshot_root: Path, freshness_seconds: float | None = None, static_root: Path | None = None):
    """Create the optional FastAPI adapter without making FastAPI a base dependency."""
    try:
        from fastapi import FastAPI, HTTPException, Query
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError as exc:  # pragma: no cover - exercised only in product-extra environments
        raise RuntimeError('FastAPI product extra is not installed; use `pip install -e ".[product]"`') from exc

    policy = FreshnessPolicy(None if freshness_seconds is None else timedelta(seconds=float(freshness_seconds)))
    service = ForecastProductService(PublishedSnapshotRepository(Path(snapshot_root)), policy)
    static_root = static_root or (Path(__file__).resolve().parents[1] / "product" / "static")
    app = FastAPI(
        title="Aggie Analytics Engine Forecast API",
        version="1.0",
        description="Read-only API over immutable published forecast snapshots.",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.state.forecast_service = service
    app.mount("/static", StaticFiles(directory=str(static_root)), name="static")

    @app.get("/health")
    def health():
        return service.health()

    @app.get("/api/v1/games")
    def games():
        return service.games()

    @app.get("/api/v1/games/{game_id}/snapshots")
    def snapshots(game_id: str):
        return service.snapshots(game_id)

    @app.get("/api/v1/games/{game_id}/forecast")
    def forecast(
        game_id: str,
        snapshot_id: str | None = Query(default=None),
        market_lane: str = Query(default="PURE_FOOTBALL"),
        as_of: str | None = Query(default=None),
    ):
        try:
            now = datetime.fromisoformat(as_of.replace("Z", "+00:00")) if as_of else datetime.now(timezone.utc)
            if now.tzinfo is None:
                raise ValueError("as_of must include timezone")
            return service.forecast(game_id, snapshot_id=snapshot_id, market_lane=market_lane, now=now)
        except (SnapshotNotFound, KeyError) as exc:
            raise HTTPException(status_code=404, detail="forecast snapshot not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/v1/games/{game_id}/snapshots/{snapshot_id}/lineage")
    def lineage(game_id: str, snapshot_id: str, market_lane: str | None = Query(default=None)):
        try:
            return service.lineage(game_id, snapshot_id, market_lane=market_lane)
        except SnapshotNotFound as exc:
            raise HTTPException(status_code=404, detail="forecast snapshot not found") from exc

    @app.get("/")
    def dashboard():
        return FileResponse(static_root / "index.html")

    return app

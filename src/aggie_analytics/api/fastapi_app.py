from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.product import ForecastProductService, FreshnessPolicy, PublishedSnapshotRepository, SnapshotNotFound


def create_app(*, snapshot_root: Path, freshness_seconds: float | None = None, static_root: Path | None = None,
               legacy_artifact_sha256: Mapping[str, str] | None = None, research_config: Any = None):
    """Create the optional FastAPI adapter without making FastAPI a base dependency.

    ``research_config`` (BAT-728) optionally registers private retrospective research profiles: an operator JSON
    configuration location or mapping (bound to the packaged accepted pins) or a prebuilt
    :class:`aggie_analytics.product.research.ResearchRegistry`. Without it no research route, page or module exists."""
    try:
        from fastapi import FastAPI, HTTPException, Query
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError as exc:  # pragma: no cover - exercised only in product-extra environments
        raise RuntimeError('FastAPI product extra is not installed; use `pip install -e ".[product]"`') from exc

    policy = FreshnessPolicy(None if freshness_seconds is None else timedelta(seconds=float(freshness_seconds)))
    service = ForecastProductService(PublishedSnapshotRepository(Path(snapshot_root), legacy_artifact_sha256=legacy_artifact_sha256), policy)
    static_root = static_root or (Path(__file__).resolve().parents[1] / "product" / "static")
    registry = None
    if research_config is not None:
        # Validated completely (and bound to the accepted pins) before any route exists; a refused configuration
        # raises ResearchConfigError and the application is not created.
        from aggie_analytics.product.research import ResearchRegistry

        registry = research_config if isinstance(research_config, ResearchRegistry) else \
            ResearchRegistry.from_source(research_config)
    app = FastAPI(
        title="Aggie Analytics Engine Forecast API",
        version="1.0",
        description="Read-only API over immutable published forecast snapshots.",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
        # Serving published snapshots must not activate exporters from the host
        # environment or send request data to an unrelated global provider.
        telemetry={"auto_configure": False, "tracing": False, "metrics": False,
                   "logs": False, "operation_spans": False},
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

    if registry is not None:
        _add_research_routes(app, registry, static_root)
        registry.start()
    return app


def _add_research_routes(app: Any, registry: Any, static_root: Path) -> None:
    """The private research surface (BAT-728): a page and versioned read-only routes over registered profile IDs only.
    Every answer is JSON from :mod:`aggie_analytics.product.research`; a refusal keeps its own code and never carries a
    path, traceback or credential."""
    from fastapi import Request
    from fastapi.responses import FileResponse, JSONResponse

    from aggie_analytics.product import research

    app.state.research_registry = registry
    headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
    page_headers = {**headers, "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; "
                                                          "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
                                                          "base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
                    "Referrer-Policy": "no-referrer"}

    def answer(call: Any) -> Any:
        try:
            return JSONResponse(call(), headers=headers)
        except research.ResearchError as exc:
            extra = {"Retry-After": str(exc.retry_after)} if exc.retry_after else {}
            return JSONResponse(exc.payload(), status_code=exc.status, headers={**headers, **extra})
        except Exception:  # noqa: BLE001 - never a traceback, path or credential in a research answer
            error = research.ResearchError("RESEARCH_INTERNAL_ERROR", "the research request could not be answered", 500)
            return JSONResponse(error.payload(), status_code=500, headers=headers)

    def no_query(request: Any) -> None:
        if request.query_params:
            raise research.ResearchError("UNKNOWN_PARAMETER", "this endpoint accepts no parameters")

    def selectors_doc(grain: str) -> dict[str, Any]:
        names = list(research.GRAIN_FILTERS[grain]) + list(research.PAGING)
        return {"parameters": [{"name": n, "in": "query", "required": False, "schema": {"type": "string"},
                                "description": f"research selector {n} (strict; unknown or repeated parameters refuse)"}
                               for n in names]}

    def typed(func: Any, **annotations: Any) -> Any:
        # this module defers annotations, and FastAPI resolves deferred names in module globals where the lazily
        # imported Request is absent: give each handler its real annotation objects before registration
        func.__annotations__ = annotations
        return func

    def research_page():
        return FileResponse(static_root / "research.html", headers=page_headers)

    def research_profiles(request):
        return answer(lambda: (no_query(request), registry.listing())[1])

    def research_profile(profile_id, request):
        return answer(lambda: (no_query(request), registry.get(profile_id).detail())[1])

    def research_game(profile_id, game_key, request):
        return answer(lambda: (no_query(request), registry.get(profile_id).game(game_key))[1])

    def grain_route(grain: str) -> Any:
        def handler(profile_id, request):
            return answer(lambda: registry.get(profile_id).query(grain, list(request.query_params.multi_items())))
        handler.__name__ = f"research_{grain}"
        return typed(handler, profile_id=str, request=Request)

    app.get("/research", include_in_schema=False)(typed(research_page))
    app.get("/api/v1/research/profiles", summary="Registered private research profiles (retrospective research "
            "only)")(typed(research_profiles, request=Request))
    app.get("/api/v1/research/profiles/{profile_id}", summary="One research profile: identities, coverage and "
            "limits")(typed(research_profile, profile_id=str, request=Request))
    app.get("/api/v1/research/profiles/{profile_id}/games/{game_key}", summary="One accepted target: catalog row, "
            "label, both-team lineage, estimates and scores")(typed(research_game, profile_id=str, game_key=str,
                                                                    request=Request))
    for grain in ("games", "features", "estimates", "scores", "parameters", "summary", "comparisons"):
        app.get(f"/api/v1/research/profiles/{{profile_id}}/{grain}",
                summary=f"Research {grain} (exact selectors and paging; retrospective research only)",
                openapi_extra=selectors_doc(grain))(grain_route(grain))

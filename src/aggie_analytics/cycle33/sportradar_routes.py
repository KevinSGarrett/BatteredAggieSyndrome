"""Evidence-backed Sportradar NCAAFB route capability from real attempts.

Does not guess `/injuries` 404 responses. Endpoint unsupported, wrong
version/path/access level, unauthorized, exhausted quota, not published,
and cached error remain distinct. No national injury absence is inferred.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

ROUTE_LEAGUE_TEAMS = "LEAGUE_TEAMS"
ROUTE_TEAM_FULL_ROSTER = "TEAM_FULL_ROSTER"
ROUTE_INJURIES = "INJURIES"
ROUTE_UNKNOWN = "UNCLASSIFIED_PATH"


def classify_ncaafb_path(route: str) -> str:
    path = urlsplit(str(route or "")).path.casefold()
    if "/injuries" in path:
        return ROUTE_INJURIES
    if path.endswith("/league/teams.json") or path.endswith("/league/teams"):
        return ROUTE_LEAGUE_TEAMS
    if "/teams/" in path and "full_roster" in path:
        return ROUTE_TEAM_FULL_ROSTER
    return ROUTE_UNKNOWN


def capability_status(*, http_status: Any, status: str, cached: bool) -> str:
    folded = str(status or "").casefold()
    if http_status is None and folded in {"cache_hit_status_unknown", ""}:
        return "CACHED_STATUS_UNKNOWN"
    try:
        code = int(http_status) if http_status is not None else None
    except (TypeError, ValueError):
        code = None
    if code == 401 or code == 403:
        return "UNAUTHORIZED"
    if code == 404:
        return "ENDPOINT_UNSUPPORTED_OR_NOT_PUBLISHED"
    if code == 429:
        return "EXHAUSTED_QUOTA"
    if code is not None and code >= 500:
        return "UPSTREAM_ERROR"
    if code is not None and code >= 400:
        return "HTTP_ERROR"
    if code == 200 or folded in {"http_ok", "cache_hit"}:
        return "EVIDENCE_SUPPORTED" if cached or folded == "http_ok" else "HTTP_OK"
    return "ATTEMPTED_INCONCLUSIVE"


def matrix_from_attempts(attempts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize actual attempted NCAAFB routes. Injuries stay NOT_ATTEMPTED."""

    by_kind: dict[str, Counter[str]] = {
        ROUTE_LEAGUE_TEAMS: Counter(),
        ROUTE_TEAM_FULL_ROSTER: Counter(),
        ROUTE_INJURIES: Counter(),
        ROUTE_UNKNOWN: Counter(),
    }
    access_levels: Counter[str] = Counter()
    versions: Counter[str] = Counter()
    injuries_attempted = 0
    for row in attempts:
        route = str(row.get("route") or "")
        kind = classify_ncaafb_path(route)
        cap = capability_status(
            http_status=row.get("http_status"),
            status=str(row.get("status") or ""),
            cached=bool(row.get("cached")),
        )
        by_kind[kind][cap] += 1
        path = urlsplit(route).path
        parts = [p for p in path.split("/") if p]
        if "ncaafb" in parts:
            idx = parts.index("ncaafb")
            if idx + 1 < len(parts):
                access_levels[parts[idx + 1]] += 1
            if idx + 2 < len(parts):
                versions[parts[idx + 2]] += 1
        if kind == ROUTE_INJURIES:
            injuries_attempted += 1
    routes = [
        {
            "route_kind": ROUTE_LEAGUE_TEAMS,
            "declared_path": "/ncaafb/{access}/v7/en/league/teams.json",
            "capability_counts": dict(by_kind[ROUTE_LEAGUE_TEAMS]),
            "attempted": sum(by_kind[ROUTE_LEAGUE_TEAMS].values()),
        },
        {
            "route_kind": ROUTE_TEAM_FULL_ROSTER,
            "declared_path": "/ncaafb/{access}/v7/en/teams/{id}/full_roster.json",
            "capability_counts": dict(by_kind[ROUTE_TEAM_FULL_ROSTER]),
            "attempted": sum(by_kind[ROUTE_TEAM_FULL_ROSTER].values()),
        },
        {
            "route_kind": ROUTE_INJURIES,
            "declared_path": "/ncaafb/{access}/v7/en/.../injuries",
            "capability_counts": dict(by_kind[ROUTE_INJURIES]),
            "attempted": injuries_attempted,
            "status": "NOT_ATTEMPTED" if injuries_attempted == 0 else "ATTEMPTED",
            "national_injury_absence_not_inferred": True,
            "guessed_404_forbidden": True,
        },
    ]
    return {
        "artifact_type": "CYCLE33_SPORTRADAR_ROUTE_MATRIX",
        "attempt_count": len(attempts),
        "access_levels_observed": dict(access_levels),
        "versions_observed": dict(versions),
        "routes": routes,
        "unclassified_path_counts": dict(by_kind[ROUTE_UNKNOWN]),
        "injuries_not_inferred_from_guessed_404": True,
        "unsupported_vs_unauthorized_vs_quota_not_collapsed": True,
        "no_paid_review_provider": True,
        "pit_admitted": False,
    }

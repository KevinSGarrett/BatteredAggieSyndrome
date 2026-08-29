"""Pure offline reconstruction of the 1996-1998 official season-index gates.

The three season-index modules already know how to rebuild their objects from the
immutable lake, but that knowledge is reachable only through ``materialize``, which also
writes the tracked gate and, when lake-only mode is off, acquires over the network. That
is why the three suites erred whenever the official host rotated a certificate, and why
they dirtied tracked artifacts on every run.

This module exposes the rebuild half on its own. It lives outside every season-index
code bundle on purpose: those bundles hash their own module bytes into
``validator_code_identity``, and a pinned identity chain reaches from them through the
boxscore, structured-domain and gamebook-union gates. Reconstructing here keeps the
deterministic read path available without restating any pinned identity.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data import tamu_official_1996_season_index as index_1996
from aggie_analytics.data import tamu_official_1997_season_index as index_1997
from aggie_analytics.data import tamu_official_1998_season_index as index_1998
from aggie_analytics.data.offline_reconstruction import require_fixture
from aggie_analytics.data.tamu_official_historical_archive import AuthorityViolation

SEASON_MODULES = {
    1996: index_1996,
    1997: index_1997,
    1998: index_1998,
}


def committed_gate(season: int, *, repo_root: Path) -> dict[str, Any]:
    module = _module_for(season)
    return dict(module.load_json(repo_root / module.GATE_RELATIVE))


def reconstruct_season_index(
    season: int,
    *,
    repo_root: Path,
    data_root: Path,
    gate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Rebuild one season-index gate from the lake, writing nothing.

    Raises ``AuthorityViolation`` when the capture is absent or its bytes no longer hash
    to the value the committed gate recorded, so a drifted lake fails closed instead of
    silently reaching for the live host.
    """

    module = _module_for(season)
    committed = dict(gate or committed_gate(season, repo_root=repo_root))
    capture = dict(committed.get("capture") or {})
    raw_relative = capture.get("raw_relative_path")
    if not raw_relative:
        raise AuthorityViolation(f"committed {season} gate is missing raw_relative_path")
    body = require_fixture(
        data_root / str(raw_relative),
        expected_sha256=str(capture.get("raw_sha256") or ""),
        description=f"{season} official season index capture",
    )
    return module.build_objects(
        body=body,
        capture=_capture_for(season, committed=committed, capture=capture, body=body),
        repo_root=repo_root,
        data_root=data_root,
        **_discovered_for(season, committed=committed),
    )


def _module_for(season: int) -> Any:
    try:
        return SEASON_MODULES[season]
    except KeyError:
        raise AuthorityViolation(f"no offline season-index route for {season}") from None


def _capture_for(
    season: int,
    *,
    committed: Mapping[str, Any],
    capture: Mapping[str, Any],
    body: bytes,
) -> dict[str, Any]:
    if season == 1998:
        return {
            "content_type": "text/html",
            "historical_publication_time": None,
            "method": "GET",
            "page_family": "season_index",
            "parent_url": committed.get("discovery_parent_url"),
            "parser_disposition": capture.get("parser_disposition"),
            "raw_byte_count": len(body),
            "raw_relative_path": capture.get("raw_relative_path"),
            "raw_sha256": capture.get("raw_sha256"),
            "redirect_chain": [],
            "response_status": capture.get("response_status"),
            "rights_disposition": "PRIVATE_RESEARCH_METADATA_ONLY_NONBLOCKING",
            "source_id": index_1998.SOURCE_ID,
            "source_season": index_1998.SEASON,
            "status": capture.get("response_status"),
            "temporal_authority": "UNKNOWN_RETRIEVAL_TIME_ONLY",
            "timestamp": None,
            "url": committed.get("official_index_url"),
        }
    resolved = dict(capture)
    resolved["response_status"] = int(resolved.get("response_status") or 0)
    resolved["status"] = resolved["response_status"]
    resolved["content_type"] = str(resolved.get("content_type") or "text/html")
    return resolved


def _discovered_for(season: int, *, committed: Mapping[str, Any]) -> dict[str, Any]:
    if season == 1998:
        return {}
    module = _module_for(season)
    return {
        "discovered": {
            "official_index_url": module.OFFICIAL_SEASON_INDEX_URL,
            "history_index_sha256": committed.get("history_index_sha256")
            or module.PINNED_HISTORY_INDEX_SHA256,
            "history_href_proof": committed.get("history_href_proof")
            or module.HISTORY_HREF_PROOF,
        }
    }

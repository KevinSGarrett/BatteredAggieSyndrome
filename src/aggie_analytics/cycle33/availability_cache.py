"""Cache-first official availability extraction. File presence is not HTTP 200.

Roster membership and participation are not availability. No report is
UNKNOWN, not healthy. Injuries stay NOT_ATTEMPTED only when no injury
route was actually attempted. Cached official PDF/HTML is attempted.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.cycle30.availability import (
    PUBLIC_AVAILABILITY_ROUTES,
    availability_pdf_hrefs,
    classify_captured_document,
    extract_candidate_player_rows,
    pdf_plaintext,
)
from aggie_analytics.cycle30.hashing import sha256_bytes, sha256_json
from aggie_analytics.cycle33.acquisition_receipts import cache_hit_from_path, utc_now

DEFAULT_CACHE = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\availability"
)
EXTRA_ROUTES: tuple[dict[str, str], ...] = (
    {
        "source_id": "SRC-017-LIVE",
        "conference": "SEC",
        "uri": "https://www.secsports.com/fbreports",
    },
)


def cache_path_for_uri(uri: str, cache_root: Path) -> Path:
    return Path(cache_root) / f"{sha256_json({'url': uri})}.html"


def _page_bytes(path: Path) -> bytes:
    return Path(path).read_bytes()


def _decoded_text(body: bytes) -> str:
    if body.startswith(b"%PDF"):
        return pdf_plaintext(body) or body.decode("latin-1", "replace")
    return body.decode("utf-8", "replace")


def parse_cached_document(
    path: Path,
    *,
    uri: str,
    source_id: str,
    original_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    target = Path(path)
    if not target.is_file():
        return {
            "uri": uri,
            "source_id": source_id,
            "disposition": "CACHE_MISS_NOT_FETCHED",
            "http_status": None,
            "player_rows_extracted": 0,
            "page_kind": "ROUTE_INVENTORIED_CACHE_ABSENT",
            "file_existence_is_not_http_200": True,
            "roster_is_not_availability": True,
            "no_report_means": "UNKNOWN",
            "joined_to_verified_roster": False,
            "private_medical_detail_ingested": False,
            "out_of_fitted_models": True,
            "pit_admitted": False,
        }
    body = _page_bytes(target)
    receipt = cache_hit_from_path(target, url=uri, original=original_receipt)
    text = _decoded_text(body)
    page_kind = classify_captured_document(body, uri=uri)
    candidates: list[dict[str, Any]] = []
    if page_kind != "JS_LANDING_SHELL_NOT_REPORT":
        candidates = extract_candidate_player_rows(
            text, source_id=source_id, uri=uri
        )
    return {
        "uri": uri,
        "source_id": source_id,
        "cache_path": str(target),
        "bytes": len(body),
        "raw_sha256": sha256_bytes(body),
        "disposition": "CACHE_HIT_PARSED",
        "http_status": receipt.get("http_status"),
        "receipt_status": receipt.get("status"),
        "retrieved_at_utc": receipt.get("retrieved_at_utc"),
        "cache_read_at_utc": receipt.get("cache_read_at_utc") or utc_now(),
        "file_existence_is_not_http_200": receipt.get("http_status") is None,
        "page_kind": page_kind,
        "player_rows_extracted": len(candidates),
        "candidate_player_rows": candidates,
        "joined_to_verified_roster": False,
        "health_status_inferred": False,
        "private_medical_detail_ingested": False,
        "roster_is_not_availability": True,
        "no_report_means": "UNKNOWN",
        "out_of_fitted_models": True,
        "pit_admitted": False,
        "owner": "BAT-324",
    }


def parse_cached_routes(
    *,
    cache_root: Path | None = None,
    routes: Sequence[Mapping[str, str]] | None = None,
    original_receipts: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    root = Path(cache_root or DEFAULT_CACHE)
    selected = list(routes or [*PUBLIC_AVAILABILITY_ROUTES, *EXTRA_ROUTES])
    rows: list[dict[str, Any]] = []
    pdf_rows: list[dict[str, Any]] = []
    seen_pdf: set[str] = set()
    for route in selected:
        uri = str(route.get("uri") or "")
        source_id = str(route.get("source_id") or "")
        cache = cache_path_for_uri(uri, root)
        parsed = parse_cached_document(
            cache,
            uri=uri,
            source_id=source_id,
            original_receipt=(original_receipts or {}).get(uri),
        )
        parsed["conference"] = route.get("conference")
        rows.append(parsed)
        if not cache.is_file():
            continue
        html = cache.read_text(encoding="utf-8", errors="replace")
        for pdf_uri in availability_pdf_hrefs(html, page_uri=uri, limit=8):
            if pdf_uri.casefold() in seen_pdf:
                continue
            seen_pdf.add(pdf_uri.casefold())
            pdf_cache = cache_path_for_uri(pdf_uri, root)
            pdf_rows.append(
                parse_cached_document(
                    pdf_cache,
                    uri=pdf_uri,
                    source_id=source_id,
                    original_receipt=(original_receipts or {}).get(pdf_uri),
                )
            )
    cache_files = [path for path in root.iterdir()] if root.is_dir() else []
    bound_paths = {str(cache_path_for_uri(str(row.get("uri")), root)) for row in rows}
    unbound = []
    for path in cache_files:
        if not path.is_file():
            continue
        if str(path) in bound_paths:
            continue
        body = path.read_bytes()
        text = _decoded_text(body)
        candidates = extract_candidate_player_rows(
            text,
            source_id="UNBOUND_CACHE_FILE",
            uri=str(path),
        )
        unbound.append(
            {
                "cache_path": str(path),
                "bytes": len(body),
                "raw_sha256": sha256_bytes(body),
                "disposition": "CACHE_FILE_UNBOUND_TO_ROUTE",
                "page_kind": classify_captured_document(body),
                "pdf": body.startswith(b"%PDF"),
                "player_rows_extracted": len(candidates),
                "candidate_player_rows": candidates,
                "http_status": None,
                "file_existence_is_not_http_200": True,
                "joined_to_verified_roster": False,
                "no_report_means": "UNKNOWN",
                "pit_admitted": False,
            }
        )
    kinds = Counter(str(row.get("page_kind")) for row in rows)
    return {
        "artifact_type": "CYCLE33_AVAILABILITY_CACHE_PARSE",
        "as_of_utc": utc_now(),
        "cache_root": str(root),
        "route_count": len(selected),
        "cache_files_present": len(cache_files),
        "bound_route_rows": rows,
        "linked_pdf_rows": pdf_rows,
        "unbound_cache_files": unbound,
        "page_kind_counts": dict(kinds),
        "player_candidate_count": sum(
            int(row.get("player_rows_extracted") or 0) for row in rows
        )
        + sum(int(row.get("player_rows_extracted") or 0) for row in pdf_rows)
        + sum(int(row.get("player_rows_extracted") or 0) for row in unbound),
        "joined_to_verified_roster": False,
        "no_report_means_unknown_not_healthy": True,
        "roster_or_participation_is_not_availability": True,
        "http_200_not_inferred_from_file_presence": True,
        "injuries_api_not_attempted_unless_route_present": True,
        "no_new_source_in_frozen_pregame": True,
        "out_of_fitted_models": True,
        "pit_admitted": False,
        "owner": "BAT-324",
    }

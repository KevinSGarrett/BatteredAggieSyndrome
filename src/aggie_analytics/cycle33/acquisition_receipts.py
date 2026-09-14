"""Acquisition receipt identity, cache-read clocks, and URL sanitization.

Cache hits must preserve the original retrieval timestamp and HTTP status.
Reused error bodies cannot become successful captures. Query secrets are
removed by parsing, not by prefix rewriting that leaves the value.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SENSITIVE_QUERY_KEYS = {
    "api_key",
    "apikey",
    "access_token",
    "access-token",
    "token",
    "secret",
    "password",
    "authorization",
    "key",
}


class AcquisitionReceiptError(ValueError):
    """Raised when a receipt cannot be replayed honestly."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sanitize_url(url: str) -> str:
    """Drop sensitive query values. Prefix rewrite is not sufficient."""

    parts = urlsplit(url or "")
    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        folded = key.casefold().replace("-", "_")
        if folded in SENSITIVE_QUERY_KEYS or any(
            token in folded for token in ("api_key", "token", "secret", "password")
        ):
            continue
        query.append((key, value))
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


def cache_hit_receipt(
    *,
    original: Mapping[str, Any],
    cache_read_at_utc: str | None = None,
    route: str | None = None,
) -> dict[str, Any]:
    """Replay a cache hit without promoting status or retrieval time."""

    if not original:
        raise AcquisitionReceiptError(
            "cache hit requires the original acquisition receipt"
        )
    original_status = original.get("http_status")
    original_ok = original.get("ok")
    if original_ok is False or (
        original_status is not None and int(original_status) >= 400
    ):
        status = "CACHE_HIT_ERROR_PRESERVED"
        http_status = int(original_status or 0) or 0
        ok = False
    else:
        status = "CACHE_HIT"
        http_status = int(original_status or 200)
        ok = bool(original.get("ok", True))
    return {
        "route": sanitize_url(
            str(route or original.get("route") or original.get("url") or "")
        ),
        "status": status,
        "http_status": http_status,
        "ok": ok,
        "cached": True,
        "retrieved_at_utc": original.get("retrieved_at_utc"),
        "cache_read_at_utc": cache_read_at_utc or utc_now(),
        "original_request_id": original.get("request_id")
        or original.get("original_request_id"),
        "raw_sha256": original.get("raw_sha256"),
        "publication_or_revision": original.get("publication_or_revision"),
        "retrieval_clock_is_not_publication_clock": True,
        "error_body_not_success": not ok,
    }


def cache_hit_from_path(
    path: Path,
    *,
    url: str,
    original: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Cache hit from a local file. File mtime is original retrieval, not now."""

    target = Path(path)
    if not target.is_file():
        raise AcquisitionReceiptError("cache hit requires an existing cache file")
    mtime = datetime.fromtimestamp(target.stat().st_mtime, timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    orig = dict(original or {})
    orig.setdefault("retrieved_at_utc", mtime)
    orig.setdefault("route", url)
    orig.setdefault(
        "request_id", orig.get("request_identity") or orig.get("request_id")
    )
    if orig.get("http_status") is None:
        return {
            "route": sanitize_url(str(url)),
            "status": "CACHE_HIT_STATUS_UNKNOWN",
            "http_status": None,
            "ok": False,
            "cached": True,
            "retrieved_at_utc": orig.get("retrieved_at_utc"),
            "cache_read_at_utc": utc_now(),
            "original_request_id": orig.get("request_id")
            or orig.get("original_request_id"),
            "raw_sha256": orig.get("raw_sha256"),
            "publication_or_revision": orig.get("publication_or_revision"),
            "retrieval_clock_is_not_publication_clock": True,
            "error_body_not_success": True,
            "file_existence_is_not_http_200": True,
        }
    orig.setdefault("ok", orig.get("ok", int(orig.get("http_status") or 0) < 400))
    return cache_hit_receipt(original=orig, route=url)

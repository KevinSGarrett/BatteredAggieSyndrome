"""Read revision-bound wikitext from existing Wikimedia JSON caches."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class WikimediaRawError(ValueError):
    """Raised when a cache file cannot yield revision-bound wikitext."""


def wikitext_from_payload(payload: dict[str, Any]) -> tuple[str, str, str]:
    pages = (payload.get("query") or {}).get("pages") or {}
    for page in pages.values():
        title = str(page.get("title") or "")
        for rev in page.get("revisions") or []:
            revid = str(rev.get("revid") or "")
            slot = (rev.get("slots") or {}).get("main") or {}
            text = (
                slot.get("*")
                or slot.get("content")
                or rev.get("*")
                or rev.get("content")
            )
            if text and revid:
                return str(text), revid, title
    raise WikimediaRawError("no revision-bound wikitext")


def wikitext_from_path(path: Path) -> tuple[str, str, str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return wikitext_from_payload(payload)

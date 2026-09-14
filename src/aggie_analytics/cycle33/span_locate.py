"""Locate person/title spans in official HTML. String-built IDs are not enough."""

from __future__ import annotations

from typing import Any


def locate_person_title(html: str, *, person: str, title: str = "") -> dict[str, Any]:
    """Return body/title offsets when both strings are present in the raw body."""

    body = html or ""
    person_n = str(person or "").strip()
    title_n = str(title or "").strip()
    body_offset = body.find(person_n) if person_n else -1
    if body_offset < 0 and person_n:
        body_offset = body.casefold().find(person_n.casefold())
    title_offset = body.find(title_n) if title_n else -1
    if title_offset < 0 and title_n:
        title_offset = body.casefold().find(title_n.casefold())
    locatable = body_offset >= 0 and (not title_n or title_offset >= 0)
    return {
        "body_offset": body_offset if body_offset >= 0 else None,
        "title_offset": title_offset if title_offset >= 0 else None,
        "locatable": locatable,
        "span_id_string_built_insufficient": True,
    }

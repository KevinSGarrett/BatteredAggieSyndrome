"""Locate person/title spans in official HTML. String-built IDs are not enough."""

from __future__ import annotations

import html as html_lib
import re
from typing import Any

_APOSTROPHE = dict.fromkeys("’‘‛`", "'")
_JR = re.compile(r",?\s*jr\.?\s*$", re.I)


def _variants(text: str) -> tuple[str, ...]:
    raw = str(text or "").strip()
    if not raw:
        return ()
    unesc = html_lib.unescape(raw).replace("\xa0", " ")
    folded = unesc.translate(str.maketrans(_APOSTROPHE))
    collapsed = re.sub(r"\s+", " ", folded)
    values = [raw, unesc, folded, collapsed, _JR.sub("", collapsed).strip()]
    return tuple(dict.fromkeys(item for item in values if item))


def _find(body: str, needle: str) -> int:
    if not needle:
        return -1
    idx = body.find(needle)
    if idx >= 0:
        return idx
    return body.casefold().find(needle.casefold())


def locate_person_title(html: str, *, person: str, title: str = "") -> dict[str, Any]:
    """Return body/title offsets when both strings are present in the raw body."""

    body = html or ""
    unescaped_body = html_lib.unescape(body).replace("\xa0", " ")
    haystacks = (body, unescaped_body)
    body_offset = None
    for variant in _variants(person):
        for haystack in haystacks:
            idx = _find(haystack, variant)
            if idx >= 0:
                body_offset = idx
                break
        if body_offset is not None:
            break
    title_offset = None
    if str(title or "").strip():
        for variant in _variants(title):
            for haystack in haystacks:
                idx = _find(haystack, variant)
                if idx >= 0:
                    title_offset = idx
                    break
            if title_offset is not None:
                break
    locatable = body_offset is not None and (
        not str(title or "").strip() or title_offset is not None
    )
    return {
        "body_offset": body_offset,
        "title_offset": title_offset,
        "locatable": locatable,
        "span_id_string_built_insufficient": True,
    }

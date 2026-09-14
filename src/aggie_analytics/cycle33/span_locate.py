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
    recruits = re.split(r"\brecruits\s*:", collapsed, maxsplit=1, flags=re.I)
    if len(recruits) == 2:
        values.append(recruits[0].strip().rstrip("/,-"))
    if "coordinator" in collapsed.casefold() and "/" not in collapsed:
        values.append(
            re.sub(r"(coordinator)\s+", r"\1 / ", collapsed, flags=re.I).strip()
        )
    if "," in collapsed:
        last, _, first = collapsed.partition(",")
        swapped = f"{first.strip()} {last.strip()}".strip()
        if first.strip() and last.strip():
            values.append(swapped)
    return tuple(dict.fromkeys(item for item in values if item))


def _find(body: str, needle: str) -> int:
    if not needle:
        return -1
    idx = body.find(needle)
    if idx >= 0:
        return idx
    idx = body.casefold().find(needle.casefold())
    if idx >= 0:
        return idx
    parts = [part for part in re.split(r"\s+", needle.strip()) if part]
    if len(parts) < 2:
        return -1
    pattern = re.compile(r"\s+".join(re.escape(part) for part in parts), re.I)
    found = pattern.search(body)
    return found.start() if found else -1


def _recover_original_offset(original: str, variant: str, search_idx: int) -> int:
    recovered = _find(original, variant)
    if recovered >= 0:
        return recovered
    tokens = [part for part in re.split(r"\s+", variant) if part]
    if len(tokens) >= 2:
        recovered = _find(original, " ".join(tokens[:2]))
        if recovered >= 0:
            return recovered
    return search_idx


def _first_offset(html: str, needle: str) -> int | None:
    body = html or ""
    unescaped_body = html_lib.unescape(body).replace("\xa0", " ")
    br_normalized = re.sub(r"<br\s*/?>", " ", body, flags=re.I)
    haystacks = (body, unescaped_body, br_normalized)
    for variant in _variants(needle):
        for haystack in haystacks:
            idx = _find(haystack, variant)
            if idx >= 0:
                if haystack is br_normalized:
                    return _recover_original_offset(body, variant, idx)
                return idx
    return None


def locate_person_title(html: str, *, person: str, title: str = "") -> dict[str, Any]:
    """Return body/title offsets when both strings are present in the raw body."""

    body_offset = _first_offset(html, person)
    title_offset = None
    if str(title or "").strip():
        title_offset = _first_offset(html, title)
    locatable = body_offset is not None and (
        not str(title or "").strip() or title_offset is not None
    )
    return {
        "body_offset": body_offset,
        "title_offset": title_offset,
        "locatable": locatable,
        "span_id_string_built_insufficient": True,
    }

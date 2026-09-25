"""Top-level Wikipedia infobox parameters. Nested templates are not football fields."""

from __future__ import annotations

import re
from typing import Any

FOOTBALL_TEMPLATE_TOKENS = (
    "infobox college football season",
    "infobox college football team",
    "infobox ncaa team season",
    "infobox football college season",
    "nfleteamseason",
    "cfb year",
    "college football team",
)
SPORTS_TEAM_SEASON_TOKENS = (
    "infobox college sports team season",
    "infobox college sports season",
)
FOOTBALL_SPORT_VALUES = {
    "football",
    "cfb",
    "american football",
    "college football",
    "gridiron football",
}
NON_FOOTBALL_SPORT_TOKENS = (
    "soccer",
    "basketball",
    "baseball",
    "hockey",
    "softball",
    "lacrosse",
    "volleyball",
    "officeholder",
    "politician",
    "person",
)
SCHEME_KEYS = {
    "off_scheme": "offensive_scheme",
    "offscheme": "offensive_scheme",
    "offensive_scheme": "offensive_scheme",
    "def_scheme": "defensive_scheme",
    "defscheme": "defensive_scheme",
    "defensive_scheme": "defensive_scheme",
    "base_defense": "base_defense",
    "basedefense": "base_defense",
}
TENURE_KEYS = {
    "hc_year": "hc_tenure_stated",
    "hc_years": "hc_tenure_stated",
    "hcyear": "hc_tenure_stated",
    "hcyears": "hc_tenure_stated",
    "head_coach_years": "hc_tenure_stated",
    "oc_year": "oc_tenure_stated",
    "oc_years": "oc_tenure_stated",
    "ocyear": "oc_tenure_stated",
    "ocyears": "oc_tenure_stated",
    "dc_year": "dc_tenure_stated",
    "dc_years": "dc_tenure_stated",
    "dcyear": "dc_tenure_stated",
    "dcyears": "dc_tenure_stated",
}
SEQUENTIAL_OCCUPANCY = re.compile(
    r"\bgames?\s*\d|\(\s*\d+\s*[–\-]\s*\d+\s*\)|;\s*\[\[",
    re.I,
)


class WikiParameterError(ValueError):
    """Raised when wikitext cannot be structurally scoped."""


def _template_kind(body: str) -> str:
    return body.split("|", 1)[0].strip().casefold().replace("_", " ")


def _display_sport(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", str(value or ""))
    text = re.sub(r"\{\{[^}]+\}\}", "", text)
    link = re.search(r"\[\[(?:[^\|\]]+\|)?([^\]]+)\]\]", text)
    if link:
        text = link.group(1)
    return re.sub(r"\s+", " ", text).strip().casefold()


def sport_from_template_body(body: str) -> str:
    for param in parse_top_level_parameters(body):
        if str(param.get("compact_key") or "") in {"sport", "sports"}:
            return _display_sport(str(param.get("value") or ""))
    return ""


def is_football_season_template(kind: str, body: str = "") -> bool:
    folded = str(kind or "").casefold()
    if any(token in folded for token in NON_FOOTBALL_SPORT_TOKENS):
        return False
    if any(token in folded for token in FOOTBALL_TEMPLATE_TOKENS):
        return True
    if "football" in folded and "season" in folded:
        return True
    if any(token in folded for token in SPORTS_TEAM_SEASON_TOKENS):
        sport = sport_from_template_body(body)
        if sport in FOOTBALL_SPORT_VALUES:
            return True
        if sport and any(token in sport for token in NON_FOOTBALL_SPORT_TOKENS):
            return False
        return False
    return False


def is_college_coach_template(kind: str) -> bool:
    folded = str(kind or "").casefold()
    if any(token in folded for token in NON_FOOTBALL_SPORT_TOKENS):
        return False
    return "college coach" in folded or folded.strip() in {
        "infobox college coach",
        "infobox college football coach",
        "infobox nfl biography",
        "infobox american football coach",
    }


def iter_wikitext_templates(wikitext: str) -> list[tuple[str, str, int, int]]:
    """Return (kind, inner_body, start, end) for every closed template."""

    text = wikitext or ""
    found: list[tuple[str, str, int, int]] = []
    index = 0
    while True:
        start = text.find("{{", index)
        if start < 0:
            break
        depth = 0
        cursor = start
        closed = False
        while cursor < len(text) - 1:
            if text[cursor : cursor + 2] == "{{":
                depth += 1
                cursor += 2
                continue
            if text[cursor : cursor + 2] == "}}":
                depth -= 1
                cursor += 2
                if depth == 0:
                    body = text[start + 2 : cursor - 2]
                    found.append((_template_kind(body), body, start, cursor))
                    index = cursor
                    closed = True
                    break
                continue
            cursor += 1
        if not closed:
            break
    return found


def _top_level_ranges(body: str) -> list[tuple[int, int]]:
    """Character ranges of the template body that are not inside nested {{ }}."""

    ranges: list[tuple[int, int]] = []
    depth = 0
    start = 0
    i = 0
    text = body or ""
    while i < len(text):
        if text[i : i + 2] == "{{":
            if depth == 0 and i > start:
                ranges.append((start, i))
            depth += 1
            i += 2
            continue
        if text[i : i + 2] == "}}":
            depth = max(0, depth - 1)
            i += 2
            if depth == 0:
                start = i
            continue
        i += 1
    if depth == 0 and start < len(text):
        ranges.append((start, len(text)))
    return ranges


def parse_top_level_parameters(body: str) -> list[dict[str, Any]]:
    """Parse only `|key=value` parameters of this template, not nested ones."""

    text = body or ""
    name, sep, remainder = text.partition("|")
    if not sep:
        return []
    del name
    params: list[dict[str, Any]] = []
    depth = 0
    link_depth = 0
    buf: list[str] = []
    i = 0
    while i < len(remainder):
        pair = remainder[i : i + 2]
        if pair == "{{":
            depth += 1
            buf.append(pair)
            i += 2
            continue
        if pair == "}}":
            depth = max(0, depth - 1)
            buf.append(pair)
            i += 2
            continue
        if pair == "[[":
            link_depth += 1
            buf.append(pair)
            i += 2
            continue
        if pair == "]]":
            link_depth = max(0, link_depth - 1)
            buf.append(pair)
            i += 2
            continue
        if remainder[i] == "|" and depth == 0 and link_depth == 0:
            chunk = "".join(buf).strip()
            if chunk:
                params.append(_split_param(chunk))
            buf = []
            i += 1
            continue
        buf.append(remainder[i])
        i += 1
    tail = "".join(buf).strip()
    if tail:
        params.append(_split_param(tail))
    return [row for row in params if row["key"]]


def _split_param(chunk: str) -> dict[str, Any]:
    key, sep, value = chunk.partition("=")
    if not sep:
        return {
            "key": "",
            "raw_key": chunk.strip(),
            "value": "",
            "compact_key": "",
        }
    raw_key = key.strip()
    compact = re.sub(r"[\s_]+", "", raw_key).casefold()
    return {
        "key": raw_key.strip().replace(" ", "_").casefold(),
        "raw_key": raw_key,
        "value": value.strip(),
        "compact_key": compact,
    }


def football_season_template_bodies(wikitext: str) -> list[str]:
    """Only top-level football season infoboxes; soccer/basketball stay excluded."""

    templates = iter_wikitext_templates(wikitext)
    selected: list[str] = []
    for kind, body, start, _end in templates:
        if not is_football_season_template(kind, body):
            continue
        nested = any(
            other_start < start < other_end
            and is_football_season_template(other_kind, other_body)
            for other_kind, other_body, other_start, other_end in templates
        )
        if nested:
            continue
        selected.append(body)
    return selected


def occupancy_is_sequential(value: str) -> bool:
    return bool(SEQUENTIAL_OCCUPANCY.search(value or ""))


def scheme_or_tenure_claim(param: dict[str, Any]) -> dict[str, Any] | None:
    compact = str(param.get("compact_key") or "")
    key = str(param.get("key") or "")
    value = str(param.get("value") or "").strip()
    field = SCHEME_KEYS.get(compact) or SCHEME_KEYS.get(key)
    claim_kind = "SCHEME"
    if not field:
        field = TENURE_KEYS.get(compact) or TENURE_KEYS.get(key)
        claim_kind = "TENURE"
    if not field:
        return None
    if not value or value in {"", "?"}:
        return {
            "claim_kind": claim_kind,
            "field": field,
            "source_text": value,
            "normalized": None,
            "disposition": "BLANK_NOT_CAPTURED",
            "inferred": False,
        }
    return {
        "claim_kind": claim_kind,
        "field": field,
        "source_text": value,
        "normalized": None,
        "disposition": "SOURCE_REPORTED_UNNORMALIZED",
        "inferred": False,
        "normalization_version": "BAS-SCHEME-TENURE-v33.1-identity",
    }

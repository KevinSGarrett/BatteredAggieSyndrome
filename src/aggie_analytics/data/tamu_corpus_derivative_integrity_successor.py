"""A&M corpus derivative-integrity successor helpers.

Predecessor parsers remain immutable. This module implements the corrected
contracts against caller-supplied rows and temporary data roots only.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

PLACEHOLDER_RE = re.compile(r"BAT-XXX\b")
TEAM_STAT_SECTION_MARKERS = ("team statistics", "team stats")
SCORING_SUMMARY_MARKERS = ("scoring summary", "scoring")
METADATA_ROW_MARKERS = ("stadium", "attendance", "weather", "surface")
MULTI_PLAYER_MARKERS = ("totals", "team totals", "/", " and ")


def reject_placeholder(text: str) -> str | None:
    if PLACEHOLDER_RE.search(text or ""):
        return "UNRESOLVED_BAT_XXX_PLACEHOLDER"
    return None


def is_metadata_row(line: str) -> bool:
    lowered = line.strip().lower()
    return any(marker in lowered for marker in METADATA_ROW_MARKERS)


def scoring_summary_constrained(section_name: str, line: str) -> bool:
    section = section_name.strip().lower()
    if not any(marker in section for marker in SCORING_SUMMARY_MARKERS):
        return False
    if is_metadata_row(line):
        return False
    return True


def original_text_is_source(original_text: str, parsed_object: object) -> bool:
    return original_text != str(parsed_object)


def classify_player_line(line: str) -> dict[str, Any]:
    stripped = line.strip()
    lowered = stripped.lower()
    aggregate = any(marker in lowered for marker in MULTI_PLAYER_MARKERS)
    return {
        "line": stripped,
        "aggregate": aggregate,
        "disposition": "QUARANTINE_MULTI_PLAYER_AGGREGATE" if aggregate else "PARSE_PLAYER",
        "do_not_attribute_to_first_token": aggregate,
    }


def season_specific_rejection_count(
    rejections: Sequence[Mapping[str, Any]], season: int
) -> int:
    return sum(1 for row in rejections if int(row.get("season") or 0) == season)


def rejected_url_must_not_enter_union(url: str, union_urls: Sequence[str]) -> bool:
    return url not in set(union_urls)

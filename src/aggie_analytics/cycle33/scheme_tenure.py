"""Source-reported scheme and tenure extraction. Not film or causal effects."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Mapping, Sequence

from aggie_analytics.cycle33.wiki_parameters import (
    football_season_template_bodies,
    parse_top_level_parameters,
    scheme_or_tenure_claim,
)

PARSER_VERSION = "BAS-SCHEME-TENURE-v33.2"
NORMALIZATION_VERSION = "BAS-SCHEME-FAMILY-TAGS-v33.2"
WIKI_LINK = re.compile(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]")
REF_OR_HTML = re.compile(r"<ref\b[^>]*>.*?</ref>|<[^>]+>", re.I | re.S)
DASHES = str.maketrans({"–": "-", "—": "-", "−": "-"})


def _compile_family_patterns(
    pairs: tuple[tuple[str, str], ...],
) -> tuple[tuple[re.Pattern[str], str], ...]:
    return tuple((re.compile(pattern), code) for pattern, code in pairs)


# CS-06 examples, not an exhaustive mutually exclusive truth set.
OFFENSE_FAMILY_PATTERNS = _compile_family_patterns(
    (
        (r"\bair[\s\-]?raid\b", "AIR_RAID"),
        (r"\brun[\s\-]?and[\s\-]?shoot\b", "RUN_AND_SHOOT"),
        (r"\btriple[\s\-]?option\b", "TRIPLE_OPTION"),
        (r"\bwest[\s\-]?coast\b", "WEST_COAST"),
        (r"\bpro[\s\-]?style\b", "PRO_STYLE"),
        (r"\bflexbone\b", "FLEXBONE"),
        (r"\bwishbone\b", "WISHBONE"),
        (r"\bpistol\b", "PISTOL"),
        (r"\bspread\b", "SPREAD"),
        (r"\boption\b", "OPTION"),
        (r"\bveer\b", "VEER"),
        (r"\bmultiple\b", "MULTIPLE"),
    )
)
DEFENSE_FRONT_PATTERNS = _compile_family_patterns(
    (
        (r"\b4-2-5\b", "FRONT_4_2_5"),
        (r"\b3-3-5\b", "FRONT_3_3_5"),
        (r"\b3-4\b", "FRONT_3_4"),
        (r"\b4-3\b", "FRONT_4_3"),
        (r"\b4-4\b", "FRONT_4_4"),
        (r"\b5-2\b", "FRONT_5_2"),
        (r"\b4-6\b", "FRONT_46"),
        (r"\bnickel\b", "NICKEL_PACKAGE"),
        (r"\bmultiple\b", "MULTIPLE"),
    )
)
_FAMILY_SPEC = {
    "offensive_scheme": (OFFENSE_FAMILY_PATTERNS, "OFFENSE_FAMILY"),
    "defensive_scheme": (DEFENSE_FRONT_PATTERNS, "DEFENSE_FRONT_OR_PACKAGE"),
    "base_defense": (DEFENSE_FRONT_PATTERNS, "DEFENSE_FRONT_OR_PACKAGE"),
}


def display_scheme_text(source_text: str) -> str:
    text = WIKI_LINK.sub(r"\1", str(source_text or ""))
    text = REF_OR_HTML.sub(" ", text)
    return " ".join(text.translate(DASHES).split())


def family_tags_from_source(source_text: str, field: str) -> list[dict[str, str]]:
    spec = _FAMILY_SPEC.get(field)
    if spec is None:
        return []
    display = display_scheme_text(source_text)
    if not display:
        return []
    patterns, dimension = spec
    folded = display.casefold()
    tags: list[dict[str, str]] = []
    seen: set[str] = set()
    for pattern, code in patterns:
        if code in seen or not pattern.search(folded):
            continue
        seen.add(code)
        tags.append(
            {
                "code": code,
                "dimension": dimension,
                "source_warranted": True,
            }
        )
    return tags


def apply_scheme_normalization(claim: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(claim)
    if row.get("claim_kind") != "SCHEME":
        row.setdefault("official_corroboration", "NOT_APPLICABLE_TENURE")
        row.setdefault("conflict_distinct_source_text", False)
        return row
    row["official_corroboration"] = "WIKIPEDIA_ONLY_NOT_OFFICIAL"
    row["conflict_distinct_source_text"] = False
    row["normalization_version"] = NORMALIZATION_VERSION
    if row.get("disposition") == "BLANK_NOT_CAPTURED" or not row.get("source_text"):
        row["normalized"] = None
        row["family_tags"] = []
        return row
    tags = family_tags_from_source(
        str(row.get("source_text") or ""), str(row.get("field") or "")
    )
    row["family_tags"] = tags
    row["normalized"] = [item["code"] for item in tags] or None
    row["inferred"] = False
    if tags:
        row["disposition"] = "SOURCE_REPORTED_FAMILY_TAGGED"
    else:
        row["disposition"] = "SOURCE_REPORTED_UNNORMALIZED"
        row["unsupported_normalization_visible"] = True
    return row


def mark_scheme_conflicts(claims: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, Any, Any], list[int]] = defaultdict(list)
    rows = [dict(row) for row in claims]
    for idx, row in enumerate(rows):
        if row.get("claim_kind") != "SCHEME" or not row.get("source_text"):
            continue
        key = (row.get("page_title"), row.get("season"), row.get("field"))
        grouped[key].append(idx)
    for indexes in grouped.values():
        texts = {str(rows[idx].get("source_text") or "") for idx in indexes}
        if len(texts) <= 1:
            continue
        conflict_texts = sorted(texts)
        for idx in indexes:
            rows[idx]["conflict_distinct_source_text"] = True
            rows[idx]["disposition"] = "SCHEME_SOURCE_TEXT_CONFLICT"
            rows[idx]["conflict_texts"] = conflict_texts
    return rows


def extract_scheme_tenure_claims(
    wikitext: str,
    *,
    page_title: str,
    revision_id: str,
    season: str | int | None = None,
    program_raw: str | None = None,
) -> list[dict[str, Any]]:
    if not revision_id:
        raise ValueError("scheme/tenure claims must be revision-bound")
    claims: list[dict[str, Any]] = []
    for body in football_season_template_bodies(wikitext):
        for param in parse_top_level_parameters(body):
            claim = scheme_or_tenure_claim(param)
            if claim is None:
                continue
            claims.append(
                {
                    **claim,
                    "page_title": page_title,
                    "wikimedia_revision": revision_id,
                    "season": season,
                    "program_raw": program_raw,
                    "source_parameter": param.get("raw_key"),
                    "parser_version": PARSER_VERSION,
                    "reported_not_observed_film": True,
                    "not_play_calling": True,
                    "not_causal_coach_effect": True,
                    "role_tenure_is_not_school_tenure": True,
                    "pit_admitted": False,
                    "inferred": False,
                }
            )
    normalized = [apply_scheme_normalization(row) for row in claims]
    return mark_scheme_conflicts(normalized)


def summarize_claims(claims: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    nonempty = [row for row in claims if row.get("source_text")]
    schemes = [row for row in nonempty if row.get("claim_kind") == "SCHEME"]
    tenure = [row for row in nonempty if row.get("claim_kind") == "TENURE"]
    tagged = [row for row in schemes if row.get("family_tags")]
    unnormalized = [
        row
        for row in schemes
        if row.get("disposition") == "SOURCE_REPORTED_UNNORMALIZED"
    ]
    conflicts = [row for row in schemes if row.get("conflict_distinct_source_text")]
    return {
        "claim_count": len(claims),
        "nonempty_scheme_count": len(schemes),
        "nonempty_tenure_count": len(tenure),
        "blank_or_unknown": sum(
            1 for row in claims if row.get("disposition") == "BLANK_NOT_CAPTURED"
        ),
        "inferred_count": sum(1 for row in claims if row.get("inferred") is True),
        "family_tagged_scheme_count": len(tagged),
        "unnormalized_visible_scheme_count": len(unnormalized),
        "conflict_scheme_claim_count": len(conflicts),
        "parser_version": PARSER_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "not_full_national_verification": True,
        "wikipedia_is_not_official_corroboration": True,
    }

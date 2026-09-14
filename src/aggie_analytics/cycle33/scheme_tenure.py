"""Source-reported scheme and tenure extraction. Not film or causal effects."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from aggie_analytics.cycle33.wiki_parameters import (
    football_season_template_bodies,
    parse_top_level_parameters,
    scheme_or_tenure_claim,
)

PARSER_VERSION = "BAS-SCHEME-TENURE-v33.1"


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
    accounted: list[str] = []
    for body in football_season_template_bodies(wikitext):
        for param in parse_top_level_parameters(body):
            compact = str(param.get("compact_key") or "")
            claim = scheme_or_tenure_claim(param)
            if claim is None:
                continue
            accounted.append(compact)
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
    return claims


def summarize_claims(claims: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    nonempty = [row for row in claims if row.get("source_text")]
    schemes = [row for row in nonempty if row.get("claim_kind") == "SCHEME"]
    tenure = [row for row in nonempty if row.get("claim_kind") == "TENURE"]
    return {
        "claim_count": len(claims),
        "nonempty_scheme_count": len(schemes),
        "nonempty_tenure_count": len(tenure),
        "blank_or_unknown": sum(
            1 for row in claims if row.get("disposition") == "BLANK_NOT_CAPTURED"
        ),
        "inferred_count": sum(1 for row in claims if row.get("inferred") is True),
        "parser_version": PARSER_VERSION,
        "not_full_national_verification": True,
    }

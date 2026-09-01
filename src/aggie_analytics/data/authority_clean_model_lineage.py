"""Authority-clean historical model lineage without unproven ranking/venue domains."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

ADMITTED_HISTORICAL_DOMAINS = frozenset(
    {
        "schedule_participants",
        "final_score_when_completed",
        "conference_affiliation_when_published",
        "subdivision_when_published",
        "home_away_designation",
        "neutral_site_flag",
        "week_and_season",
    }
)
UNPROVEN_DOMAINS = frozenset(
    {
        "historical_rankings_without_publication_vintage",
        "mutable_venue_attributes_without_publication_vintage",
        "provider_recomputed_pregame_elo",
        "missingness_indicators_as_feature_authority",
    }
)


def classify_domain(domain_name: str) -> str:
    if domain_name in ADMITTED_HISTORICAL_DOMAINS:
        return "ADMITTED"
    if domain_name in UNPROVEN_DOMAINS:
        return "EXCLUDED_INSUFFICIENT_PUBLICATION_VINTAGE"
    return "UNDECLARED_BLOCK"


def authority_clean_fields(row: Mapping[str, Any]) -> dict[str, Any]:
    excluded = []
    admitted = {}
    for key, value in row.items():
        domain = str(row.get("_domain_by_field", {}).get(key, key))
        classification = classify_domain(domain)
        if classification != "ADMITTED":
            excluded.append(
                {
                    "field": key,
                    "domain": domain,
                    "classification": classification,
                    "missingness_does_not_admit": True,
                }
            )
        else:
            admitted[key] = value
    return {
        "admitted": admitted,
        "excluded": excluded,
        "elo_quarantined": True,
        "rankings_excluded_until_vintage_evidence": True,
        "venue_excluded_until_vintage_evidence": True,
    }


def bind_population_change(
    predecessor_n: int, successor_n: int, reason: str
) -> dict[str, Any]:
    return {
        "predecessor_n": predecessor_n,
        "successor_n": successor_n,
        "delta": successor_n - predecessor_n,
        "reason": reason,
    }


def field_lineage_graph(domains: Sequence[str]) -> dict[str, Any]:
    nodes = []
    for domain in domains:
        nodes.append(
            {
                "domain": domain,
                "classification": classify_domain(domain),
            }
        )
    return {
        "schema_version": 1,
        "cycles_covered": [20, 21, 22, 23, 24, 25],
        "nodes": nodes,
        "edges": [
            {"from": "raw_domains", "to": domain, "kind": "field_lineage"}
            for domain in domains
        ],
    }

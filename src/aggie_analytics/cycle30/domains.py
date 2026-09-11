"""Canonical domain ontology with one-to-many requirement mappings.

Distinct score-model, calibration/OOD, BAS inference, rest/timezone and travel
requirements stay distinct. Unmapped=0 cannot be produced by collapsing them.
"""

from __future__ import annotations

from typing import Any, Sequence

from aggie_analytics.cycle30.coverage_terms import (
    C28_DOMAINS,
    CURRENT_REQUIREMENTS,
    PIT_DOMAINS,
    SOURCE_POLICY_DOMAINS,
    W06_DOMAINS,
)

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED_INSUFFICIENT_EVIDENCE"
NOT_AUDITED = "NOT_YET_AUDITED"
CURRENT_VENUE_NEUTRAL_AND_HFA = ("CURRENT-NEUTRAL", "CURRENT-HFA")
CURRENT_VENUE_HFA_ONLY = ("CURRENT-HFA",)


class DomainError(ValueError):
    """Raised when domain catalog or coverage contracts fail."""


def canonical_catalog() -> dict[str, Any]:
    domains = []
    for domain_id, label in W06_DOMAINS:
        domains.append(
            {
                "canonical_domain_id": domain_id,
                "label": label,
                "kind": "DATA_DOMAIN",
            }
        )
    for domain_id, label in CURRENT_REQUIREMENTS:
        domains.append(
            {
                "canonical_domain_id": domain_id,
                "label": label,
                "kind": "CURRENT_REQUIREMENT",
            }
        )
    for domain_id, label in (
        ("CTRL-RIGHTS", "data rights"),
        ("CTRL-SECURITY", "security"),
        ("CTRL-COSTS", "costs"),
        ("CTRL-GOVERNANCE", "governance"),
    ):
        domains.append(
            {
                "canonical_domain_id": domain_id,
                "label": label,
                "kind": "NON_DATA_CONTROL",
            }
        )
    return {
        "artifact_type": "BAS_CANONICAL_DOMAIN_CATALOG",
        "version": "cycle30-v1",
        "canonical_domain_count": len(domains),
        "w06_domain_count": len(W06_DOMAINS),
        "current_requirement_count": len(CURRENT_REQUIREMENTS),
        "domains": domains,
    }


def _map(
    catalog: str, term: str, canonical: str, *, extra: Sequence[str] = ()
) -> list[dict[str, str]]:
    rows = [
        {
            "predecessor_catalog": catalog,
            "predecessor_term": term,
            "predecessor_label": term,
            "canonical_domain_id": canonical,
            "state": "NON_DATA_CONTROL" if canonical.startswith("CTRL") else "MAPPED",
            "mapping_arity": "one_to_many" if extra else "one_to_one",
        }
    ]
    for other in extra:
        rows.append(
            {
                "predecessor_catalog": catalog,
                "predecessor_term": term,
                "predecessor_label": term,
                "canonical_domain_id": other,
                "state": "MAPPED_ADDITIONAL",
                "mapping_arity": "one_to_many",
            }
        )
    return rows


def crosswalk() -> dict[str, Any]:
    mappings: list[dict[str, str]] = []
    catalog_ids = {row["canonical_domain_id"] for row in canonical_catalog()["domains"]}
    for domain_id, label in W06_DOMAINS:
        mappings.append(
            {
                "predecessor_catalog": "W06_52",
                "predecessor_term": domain_id,
                "predecessor_label": label,
                "canonical_domain_id": domain_id,
                "state": "MAPPED",
                "mapping_arity": "one_to_one",
            }
        )
    c28_maps: dict[str, tuple[str, tuple[str, ...]]] = {
        "schedules_results": ("DOM-001", ()),
        "identities": ("DOM-001", ()),
        "conferences": ("DOM-001", ()),
        "rankings": ("DOM-037", ()),
        "priors": ("DOM-035", ()),
        "venues": ("DOM-025", CURRENT_VENUE_NEUTRAL_AND_HFA),
        "weather": ("DOM-023", ()),
        "market": ("DOM-039", ()),
        "rosters": ("DOM-009", ()),
        "availability_injuries": ("DOM-011", ("CURRENT-AVAILABILITY", "DOM-012")),
        "recruiting": ("DOM-013", ()),
        "transfers": ("DOM-014", ()),
        "head_coaches": ("DOM-018", ()),
        "offensive_coordinator": ("DOM-018", ()),
        "defensive_coordinator": ("DOM-018", ()),
        "special_teams": ("DOM-031", ()),
        "play_callers": ("DOM-018", ()),
        "staff_regimes": ("DOM-019", ()),
        "box_scores": ("DOM-004", ()),
        "plays": ("DOM-002", ()),
        "drives": ("DOM-003", ()),
        "travel_rest_time_zone": (
            "DOM-027",
            ("DOM-026", "CURRENT-REST", "CURRENT-TIMEZONE", "CURRENT-TRAVEL"),
        ),
        "officials_penalties": ("DOM-040", ()),
        "film": ("DOM-051", ()),
        "calibration_ood_uncertainty": ("CURRENT-CALIBRATION-OOD", ()),
        "total_team_score": ("CURRENT-TOTAL-TEAM-SCORE", ()),
        "peer_cohorts": ("CURRENT-PEER-COHORTS", ()),
        "am_archive": ("DOM-009", ()),
        "bas_residual": ("CURRENT-BAS-INFERENCE", ()),
        "data_rights": ("CTRL-RIGHTS", ()),
        "security": ("CTRL-SECURITY", ()),
        "costs": ("CTRL-COSTS", ()),
        "governance": ("CTRL-GOVERNANCE", ()),
    }
    for term in C28_DOMAINS:
        canonical, extra = c28_maps[term]
        mappings.extend(_map("C28_33", term, canonical, extra=extra))
    pit_map = {
        "team_outcome_priors": ("DOM-035", ()),
        "rankings": ("DOM-037", ()),
        "venues": ("DOM-025", CURRENT_VENUE_NEUTRAL_AND_HFA),
        "team_season_context": ("DOM-001", ()),
        "plays": ("DOM-002", ()),
        "drives": ("DOM-003", ()),
        "team_box_scores": ("DOM-004", ()),
        "player_box_scores": ("DOM-006", ()),
        "advanced_game_statistics": ("DOM-005", ()),
        "roster_membership": ("DOM-009", ()),
        "structured_gamebook_equivalent": ("DOM-008", ()),
        "provider_pregame_elo": ("DOM-038", ()),
        "tamu_official_structured_archive": ("DOM-009", ()),
        "weather_forecast_vintages": ("DOM-023", ()),
        "pregame_availability": ("DOM-011", ("CURRENT-AVAILABILITY",)),
        "recruiting_talent": ("DOM-013", ()),
        "coaching_staff": ("DOM-018", ()),
        "market_context": ("DOM-039", ()),
    }
    for term in PIT_DOMAINS:
        canonical, extra = pit_map[term]
        mappings.extend(_map("PIT_18", term, canonical, extra=extra))
    source_map = {
        "schedules_results": ("DOM-001", ()),
        "identities": ("DOM-001", ()),
        "conferences": ("DOM-001", ()),
        "rankings": ("DOM-037", ()),
        "priors": ("DOM-035", ()),
        "venues": ("DOM-025", CURRENT_VENUE_HFA_ONLY),
        "weather": ("DOM-023", ()),
        "market": ("DOM-039", ()),
        "rosters": ("DOM-009", ()),
        "availability_injuries": ("DOM-011", ("CURRENT-AVAILABILITY",)),
        "recruiting": ("DOM-013", ()),
        "transfers": ("DOM-014", ()),
        "head_coaches": ("DOM-018", ()),
        "box_scores": ("DOM-004", ()),
        "plays": ("DOM-002", ()),
        "drives": ("DOM-003", ()),
    }
    for term in SOURCE_POLICY_DOMAINS:
        canonical, extra = source_map[term]
        mappings.extend(_map("SOURCE_POLICY_16", term, canonical, extra=extra))
    unmapped = [
        row
        for row in mappings
        if row["canonical_domain_id"] not in catalog_ids
        and row["state"] != "DEPRECATED_ALIAS"
    ]
    if unmapped:
        raise DomainError(f"unmapped predecessor terms: {unmapped}")
    required_current = {domain_id for domain_id, _label in CURRENT_REQUIREMENTS}
    mapped_current = {
        row["canonical_domain_id"]
        for row in mappings
        if row["canonical_domain_id"] in required_current
    }
    missing_current = sorted(required_current - mapped_current)
    if missing_current:
        raise DomainError(
            f"current requirements missing from governing crosswalk: {missing_current}"
        )
    one_to_many = [row for row in mappings if row.get("mapping_arity") == "one_to_many"]
    return {
        "artifact_type": "BAS_DOMAIN_CATALOG_CROSSWALK",
        "mapping_count": len(mappings),
        "unmapped_term_count": 0,
        "ambiguous_unresolved_mapping_count": None,
        "ambiguous_unresolved_mapping_count_is_not_literal_zero": True,
        "one_to_many_mapping_count": len(one_to_many),
        "w06_term_count": len(W06_DOMAINS),
        "c28_term_count": len(C28_DOMAINS),
        "source_policy_term_count": len(SOURCE_POLICY_DOMAINS),
        "pit_term_count": len(PIT_DOMAINS),
        "current_requirement_count": len(CURRENT_REQUIREMENTS),
        "mapped_current_requirement_count": len(mapped_current),
        "missing_current_requirement_ids": missing_current,
        "mappings": mappings,
    }


def reject_empty_inventory_pass(inventory: Sequence[Any], result: str) -> None:
    if not inventory and result == PASS:
        raise DomainError("empty field inventories cannot return PASS")


def reject_zero_filled_registry(admitted_count: int, labeled_complete: bool) -> None:
    if admitted_count == 0 and labeled_complete:
        raise DomainError(
            "zero-filled registry cannot be represented as completeness work"
        )


def reject_not_audited_pass(state: str, result: str) -> None:
    if state in {NOT_AUDITED, "NOT_YET_AUDITED"} and result == PASS:
        raise DomainError("not-audited cannot return PASS")


def reject_display_name_as_canonical(field_name: str, is_canonical: bool) -> None:
    if "display" in field_name.lower() and is_canonical:
        raise DomainError("display name cannot be represented as canonical ID")


def reject_not_applicable_inflation(
    *, covered_cells: int, not_applicable: int, claimed_covered: int
) -> None:
    if claimed_covered == covered_cells + not_applicable and not_applicable:
        raise DomainError("NOT_APPLICABLE cannot inflate coverage")


def reject_incompatible_parity_grains(national_grain: str, tamu_grain: str) -> None:
    if national_grain != tamu_grain:
        raise DomainError(
            "national-versus-A&M coverage compared across incompatible grains"
        )


def grain_contract() -> dict[str, Any]:
    grains = {
        "availability_injuries_depth": "player × program × target game × checkpoint × declared source lane",
        "availability_reporting_surface": "program × target game × checkpoint × source lane",
        "transfers": "player × adjacent program-season boundary × declared source lane",
        "markets": "eligible scheduled game × checkpoint × provider × normalized book/source lane × quote family",
        "plays_drives_box_film": "eligible game × asset family × source lane",
        "officials_penalties": "eligible game × assignment/penalty family × source lane",
        "coaching_position_roles": "program-season × predeclared role family × as-of/cutoff",
        "games_results": "canonical contest",
        "program_seasons": "canonical program × season × contemporaneous classification",
        "travel": "canonical contest × participant × origin → actual venue",
        "neutral_site": "canonical contest × schedule/venue version × cutoff",
    }
    return {
        "artifact_type": "BAS_DOMAIN_POPULATION_AND_GRAIN_CONTRACT",
        "grains": grains,
        "program_counts_cannot_reuse_for_game_grain": True,
        "blocked_parent_emits_blocked_children": True,
        "unknown_denominator_is_null_blocked_not_one": True,
    }

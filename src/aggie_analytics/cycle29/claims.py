"""Cycle #29/kernel dependency-closure claim inventory.

An unmapped numeric/status claim fails the gate. The producer cannot write
its own unmapped count.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from aggie_analytics.cycle29.hashing import sha256_json

CLAIM_FIELDS = (
    "claim_id",
    "artifact_path",
    "field",
    "formula",
    "numerator",
    "denominator",
    "population",
    "source_identities",
    "temporal_authority",
    "producer",
    "validator",
    "independent_reference",
    "dependencies",
    "trust_class",
)

ALL_CYCLE_PRIOR = "PRIOR_ALL_CYCLE_CLASSIFICATION_RETAINED"
KERNEL_INVENTORIED = "CYCLE29_KERNEL_CLOSURE_INVENTORIED"
UNMAPPED_FAIL = "UNMAPPED_CLAIM_FAIL_CLOSED"


class ClaimError(ValueError):
    """Raised when a claim cannot be inventoried."""


def require_mapped(claim: Mapping[str, Any]) -> None:
    missing = [field for field in CLAIM_FIELDS if field not in claim]
    if missing:
        raise ClaimError(f"unmapped authority-bearing claim fields: {missing}")


def inventory_claims(
    declared: Sequence[Mapping[str, Any]],
    discovered: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    declared_ids = [str(row["claim_id"]) for row in declared]
    for claim in declared:
        require_mapped(claim)
    unmapped = []
    for claim in discovered:
        cid = str(claim.get("claim_id") or claim.get("field") or "")
        if cid not in declared_ids:
            unmapped.append(claim)
    if unmapped:
        raise ClaimError(
            f"unmapped numeric/status claims: {len(unmapped)}; gate fails closed"
        )
    return {
        "declared_count": len(declared),
        "discovered_count": len(discovered),
        "unmapped_count": 0,
        "inventory_identity": sha256_json([dict(row) for row in declared]),
        "all_cycle_project_wide_trust": False,
        "all_cycle_claims_outside_closure_retain_prior_class": True,
        "producer_cannot_write_unmapped_count": True,
    }


def reject_producer_unmapped_count(
    producer_payload: Mapping[str, Any], independent_unmapped: int
) -> None:
    claimed = producer_payload.get("unmapped_count")
    if claimed != independent_unmapped:
        raise ClaimError("producer unmapped count disagrees with independent inventory")
    if independent_unmapped != 0:
        raise ClaimError("unmapped claims remain")


def kernel_closure_claims() -> list[dict[str, Any]]:
    """Minimal closed inventory for Cycle #29 kernel/census artifacts."""

    def _c(
        claim_id: str,
        field: str,
        population: str,
        numerator: Any,
        denominator: Any,
        trust: str,
        artifact: str,
    ) -> dict[str, Any]:
        return {
            "claim_id": claim_id,
            "artifact_path": artifact,
            "field": field,
            "formula": f"{field} = numerator/denominator over {population}",
            "numerator": numerator,
            "denominator": denominator,
            "population": population,
            "source_identities": ["cycle29_kernel"],
            "temporal_authority": "declared_cutoff_or_as_of",
            "producer": "aggie_analytics.cycle29",
            "validator": "tools.validate_cycle29_gates",
            "independent_reference": "aggie_analytics.scientific_reference.cycle29",
            "dependencies": [],
            "trust_class": trust,
        }

    return [
        _c(
            "C29-CLAIM-PIT-PROVEN-ROWS",
            "proven_pit_training_rows",
            "pit_kernel",
            "proven",
            "admitted",
            KERNEL_INVENTORIED,
            "PIT_KERNEL_TRUST_GATE.json",
        ),
        _c(
            "C29-CLAIM-WEEK1-CONTESTS",
            "contest_count",
            "week1_2026_slice",
            91,
            91,
            KERNEL_INVENTORIED,
            "WEEK1_2026_PROGRAM_SLICE.json",
        ),
        _c(
            "C29-CLAIM-FORECAST-455",
            "forecast_opportunity_count",
            "week1_frozen_forecasts",
            455,
            455,
            KERNEL_INVENTORIED,
            "CYCLE29_FORECAST_IMMUTABILITY.json",
        ),
        _c(
            "C29-CLAIM-GAMES-46953",
            "normalized_game_count",
            "fbs_centric_predecessor_spine",
            46953,
            46953,
            KERNEL_INVENTORIED,
            "HISTORICAL_GAME_PAIR_SUBDIVISION_COVERAGE.json",
        ),
        _c(
            "C29-CLAIM-COACH-2251",
            "accepted_coach_role_episodes",
            "predecessor_people_registry",
            2251,
            2251,
            KERNEL_INVENTORIED,
            "PREDECESSOR_COACHING_OBSERVATION_RECONCILIATION.jsonl",
        ),
        _c(
            "C29-CLAIM-STAFF-2382",
            "provisional_staff_role_observations",
            "predecessor_people_registry",
            2382,
            2382,
            KERNEL_INVENTORIED,
            "PREDECESSOR_COACHING_OBSERVATION_RECONCILIATION.jsonl",
        ),
        _c(
            "C29-CLAIM-TRUST-USABLE",
            "cycle29_kernel_trust_usable",
            "cycle29_kernel",
            "boolean",
            1,
            KERNEL_INVENTORIED,
            "PIT_KERNEL_TRUST_GATE.json",
        ),
        _c(
            "C29-CLAIM-FITTED-TRUST",
            "current_fitted_forecast_trust_recovered",
            "frozen_fitted_forecasts",
            False,
            1,
            KERNEL_INVENTORIED,
            "PIT_KERNEL_TRUST_GATE.json",
        ),
        _c(
            "C29-CLAIM-PROJECT-TRUST",
            "project_wide_scientific_trust_recovered",
            "all_cycles",
            False,
            1,
            ALL_CYCLE_PRIOR,
            "ALL_CYCLE_TRUST_RECOVERY_GATE.json",
        ),
        _c(
            "C29-CLAIM-SCIENTIFIC-COMPAT",
            "scientific_trust_recovered",
            "compatibility",
            False,
            1,
            ALL_CYCLE_PRIOR,
            "PIT_KERNEL_TRUST_GATE.json",
        ),
        _c(
            "C29-CLAIM-PRED-UNRESOLVED-8",
            "predecessor_unresolved_participant_row_count",
            "week1_entity_authority_predecessor",
            8,
            8,
            KERNEL_INVENTORIED,
            "WEEK1_2026_ENTITY_AUTHORITY_METADATA_SUCCESSOR.json",
        ),
        _c(
            "C29-CLAIM-SUCC-UNRESOLVED-0",
            "successor_unresolved_participant_row_count",
            "week1_entity_authority_successor",
            0,
            0,
            KERNEL_INVENTORIED,
            "WEEK1_2026_ENTITY_AUTHORITY_METADATA_SUCCESSOR.json",
        ),
        _c(
            "C29-CLAIM-FCS-TO-FCS-ZERO",
            "fcs_to_fcs_count",
            "predecessor_normalized_games",
            0,
            46953,
            KERNEL_INVENTORIED,
            "HISTORICAL_GAME_PAIR_SUBDIVISION_COVERAGE.json",
        ),
        _c(
            "C29-CLAIM-ENTITY-GAMES-46960",
            "canonical_game_entity_count",
            "canonical_core_registry",
            46960,
            46960,
            KERNEL_INVENTORIED,
            "HISTORICAL_GAME_PAIR_SUBDIVISION_COVERAGE.json",
        ),
        _c(
            "C29-CLAIM-PIT-ELIGIBLE-89855",
            "predecessor_pit_feature_eligible_rows",
            "national_pit_eligible_slice",
            89855,
            90198,
            KERNEL_INVENTORIED,
            "PIT_PREDECESSOR_POPULATION_RECONCILIATION.json",
        ),
        _c(
            "C29-CLAIM-ORIENTED-90198",
            "predecessor_oriented_development_rows",
            "chronological_development_matrix",
            90198,
            90198,
            KERNEL_INVENTORIED,
            "PIT_PREDECESSOR_POPULATION_RECONCILIATION.json",
        ),
        _c(
            "C29-CLAIM-ACTIVE-PROVEN-PRED-0",
            "predecessor_active_path_proven_pit_rows",
            "cycle28_trust_gate",
            0,
            0,
            KERNEL_INVENTORIED,
            "PIT_PREDECESSOR_POPULATION_RECONCILIATION.json",
        ),
        _c(
            "C29-CLAIM-UNMAPPED",
            "unmapped_count",
            "cycle29_claim_inventory",
            0,
            0,
            KERNEL_INVENTORIED,
            "CYCLE29_CLAIM_INVENTORY.json",
        ),
    ]

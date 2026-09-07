"""Cycle #29/kernel dependency-closure claim inventory.

An unmapped numeric/status claim fails the gate. The producer cannot write
its own unmapped count.
"""

from __future__ import annotations

import json
from pathlib import Path
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
AUTHORITY_KEY_MARKERS = (
    "_count",
    "_rows",
    "_row_count",
    "proven_pit_training_rows",
    "cycle29_kernel_trust_usable",
    "current_fitted_forecast_trust_recovered",
    "project_wide_scientific_trust_recovered",
    "scientific_trust_recovered",
    "unmapped_count",
    "all_cycle_trust_recovered",
)


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
    declared_fields = {str(row["field"]) for row in declared}
    for claim in declared:
        require_mapped(claim)
    if discovered is declared:
        raise ClaimError("discovered claims cannot be the producer's declared list")
    unmapped = []
    for claim in discovered:
        cid = str(claim.get("claim_id") or "")
        field = str(claim.get("field") or "")
        if cid not in declared_ids and field not in declared_fields:
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


def _is_authority_key(key: str, value: Any) -> bool:
    if key in AUTHORITY_KEY_MARKERS:
        return isinstance(value, (int, float, bool))
    if any(key.endswith(suffix) for suffix in ("_count", "_rows", "_row_count")):
        return isinstance(value, (int, float))
    return False


def _walk_authority_keys(payload: Any, found: set[str]) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if _is_authority_key(str(key), value):
                found.add(str(key))
            _walk_authority_keys(value, found)
    elif isinstance(payload, list):
        for item in payload:
            _walk_authority_keys(item, found)


def discover_authority_claims(
    art_dir: Path, declared: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Scan Cycle #29 artifacts; do not reuse the declared list as discovery."""

    skip = {
        "CYCLE29_CLAIM_INVENTORY.json",
        "CYCLE29_MATERIALIZATION_MANIFEST.json",
        "CYCLE29_PREFLIGHT_AND_PRESERVATION.json",
    }
    declared_artifacts = {Path(str(row["artifact_path"])).name for row in declared}
    declared_fields = {str(row["field"]) for row in declared}
    discovered: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for path in sorted(art_dir.glob("*.json")):
        if path.name in skip or path.name not in declared_artifacts:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        keys: set[str] = set()
        _walk_authority_keys(payload, keys)
        for key in sorted(keys):
            ident = (path.name, key)
            if ident in seen:
                continue
            seen.add(ident)
            if key in declared_fields:
                discovered.append(
                    {
                        "claim_id": key,
                        "field": key,
                        "artifact_path": path.name,
                    }
                )
            else:
                discovered.append(
                    {
                        "claim_id": f"UNMAPPED-{path.name}-{key}",
                        "field": key,
                        "artifact_path": path.name,
                    }
                )
    if not discovered:
        raise ClaimError("claim discovery produced no authority-bearing fields")
    return discovered


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
            "C29-CLAIM-WEEK1-APPEARANCES",
            "participant_appearance_count",
            "week1_2026_slice",
            182,
            182,
            KERNEL_INVENTORIED,
            "WEEK1_2026_PROGRAM_SLICE.json",
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
            "C29-CLAIM-FORECAST-ISSUED-BEFORE",
            "issued_before_cutoff_count",
            "week1_frozen_forecasts",
            "proven",
            455,
            KERNEL_INVENTORIED,
            "CYCLE29_FORECAST_IMMUTABILITY.json",
        ),
        _c(
            "C29-CLAIM-FORECAST-NOT-PROVEN",
            "not_proven_count",
            "week1_frozen_forecasts",
            "not_proven",
            455,
            KERNEL_INVENTORIED,
            "CYCLE29_FORECAST_IMMUTABILITY.json",
        ),
        _c(
            "C29-CLAIM-FORECAST-ROW-COUNT",
            "row_count",
            "week1_frozen_forecasts",
            455,
            455,
            KERNEL_INVENTORIED,
            "CYCLE29_FORECAST_IMMUTABILITY.json",
        ),
        _c(
            "C29-CLAIM-ENTITY-RESOLVED-COUNT",
            "resolved_authoritative_identity_count",
            "week1_entity_authority_successor",
            "resolved",
            "population",
            KERNEL_INVENTORIED,
            "WEEK1_2026_ENTITY_AUTHORITY_METADATA_SUCCESSOR.json",
        ),
        _c(
            "C29-CLAIM-KERNEL-PROVEN-RECONCILED",
            "cycle29_kernel_proven_pit_training_rows",
            "pit_kernel",
            0,
            0,
            KERNEL_INVENTORIED,
            "PIT_PREDECESSOR_POPULATION_RECONCILIATION.json",
        ),
        _c(
            "C29-CLAIM-PRODUCTION-PROVEN-ROWS",
            "production_proven_rows",
            "pit_kernel",
            0,
            0,
            KERNEL_INVENTORIED,
            "PIT_KERNEL_INDEPENDENT_RECONSTRUCTION.json",
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
        _c(
            "C29-CLAIM-COMPAT-FIXTURE-ROWS",
            "compatibility_fixture_row_count",
            "pit_kernel_bounded_compatibility",
            "fixture",
            "not_proven",
            KERNEL_INVENTORIED,
            "PIT_KERNEL_POPULATION_MANIFEST.json",
        ),
        _c(
            "C29-CLAIM-INDEPENDENT-MATCHED-ROWS",
            "matched_team_rows",
            "pit_kernel_bounded_compatibility",
            "reconstructed",
            "producer",
            KERNEL_INVENTORIED,
            "PIT_KERNEL_INDEPENDENT_RECONSTRUCTION.json",
        ),
        _c(
            "C29-CLAIM-INDEPENDENT-RECONSTRUCTED-COUNT",
            "reconstructed_count",
            "pit_kernel_bounded_compatibility",
            "reconstructed",
            "producer",
            KERNEL_INVENTORIED,
            "PIT_KERNEL_INDEPENDENT_RECONSTRUCTION.json",
        ),
        _c(
            "C29-CLAIM-PIT-GAME-GRAIN-COUNT",
            "game_grain_count",
            "pit_kernel",
            0,
            0,
            KERNEL_INVENTORIED,
            "PIT_KERNEL_POPULATION_MANIFEST.json",
        ),
        _c(
            "C29-CLAIM-PIT-ORIENTED-COUNT",
            "oriented_row_count",
            "pit_kernel",
            0,
            0,
            KERNEL_INVENTORIED,
            "PIT_KERNEL_POPULATION_MANIFEST.json",
        ),
        _c(
            "C29-CLAIM-MISSOURI-PRIOR-52",
            "admitted_prior_games",
            "missouri_state_transition_prior",
            52,
            52,
            KERNEL_INVENTORIED,
            "MISSOURI_STATE_RAW_TO_PRIOR_LINEAGE_TRACE.json",
        ),
    ]

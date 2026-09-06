"""Active-path scientific claim/evidence graph, assurance layers, and gates."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

ASSURANCE_LAYERS = (
    "scope_and_population",
    "source_authenticity",
    "raw_integrity",
    "parsing_semantics",
    "identity_and_joins",
    "temporal_pit_authority",
    "coverage_and_missingness",
    "feature_admission_binding",
    "split_and_leakage",
    "model_mathematics",
    "metrics_and_denominators",
    "cross_output_coherence",
    "prospective_empirical_validation",
    "operational_reproducibility",
    "rights_privacy_security_cost",
)

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED_INSUFFICIENT_EVIDENCE"
NOT_APPLICABLE = "NOT_APPLICABLE"

STRUCTURAL_VERIFIED = "STRUCTURAL_CORRECTNESS_VERIFIED_WITHIN_SCOPE"
EMPIRICAL_NOT_ESTABLISHED = "EMPIRICAL_PREDICTIVE_SKILL_NOT_ESTABLISHED"
ALL_CYCLE_INCOMPLETE = "ALL_CYCLE_SCIENTIFIC_TRUST_INCOMPLETE"
BLOCKED_ZERO_PIT = "BLOCKED_ZERO_PROVEN_PIT_TRAINING_ROWS"

PROHIBITED_PRODUCER_HELPERS = (
    "aggie_analytics.data",
    "aggie_analytics.modeling",
    "aggie_analytics.cycle28.scoring",
    "aggie_analytics.features",
)


class AssuranceError(ValueError):
    """Raised when a scientific claim cannot be mapped or promoted."""


def require_claim_mapped(claim: Mapping[str, Any], required_fields: Sequence[str]) -> None:
    missing = [field for field in required_fields if field not in claim]
    if missing:
        raise AssuranceError(f"unmapped authority-bearing claim fields: {missing}")


CLAIM_REQUIRED_FIELDS = (
    "claim_id",
    "field",
    "population",
    "numerator",
    "denominator",
    "sources",
    "transformations",
    "producer",
    "validators",
    "independent_reference",
    "assurance_layer_results",
    "dependencies",
    "trust_state",
)


def layer_results_complete(results: Mapping[str, str]) -> bool:
    return all(layer in results for layer in ASSURANCE_LAYERS)


def reject_lower_layer_promotion(results: Mapping[str, str], claimed_state: str) -> None:
    if claimed_state == STRUCTURAL_VERIFIED:
        structural = (
            "source_authenticity",
            "raw_integrity",
            "parsing_semantics",
            "identity_and_joins",
            "temporal_pit_authority",
            "coverage_and_missingness",
            "feature_admission_binding",
            "split_and_leakage",
            "model_mathematics",
            "metrics_and_denominators",
            "cross_output_coherence",
        )
        for layer in structural:
            if results.get(layer) != PASS:
                raise AssuranceError(
                    f"lower-layer {layer}={results.get(layer)} cannot promote {claimed_state}"
                )
    if results.get("prospective_empirical_validation") != PASS and claimed_state not in {
        EMPIRICAL_NOT_ESTABLISHED,
        ALL_CYCLE_INCOMPLETE,
        STRUCTURAL_VERIFIED,
        BLOCKED_ZERO_PIT,
    }:
        raise AssuranceError("empirical skill cannot be claimed without prospective PASS")


def invalidate_descendants(changed_node: str, graph: Mapping[str, Sequence[str]]) -> set[str]:
    invalidated = {changed_node}
    stack = [changed_node]
    while stack:
        node = stack.pop()
        for child in graph.get(node, ()):
            if child not in invalidated:
                invalidated.add(child)
                stack.append(child)
    return invalidated


def validator_imports_producer(import_names: Sequence[str]) -> bool:
    return any(
        name.startswith(prefix)
        for name in import_names
        for prefix in PROHIBITED_PRODUCER_HELPERS
    )


def cross_output_coherent(
    *,
    probability: float,
    margin: float,
    interval: tuple[float, float],
    from_same_distribution: bool,
) -> bool:
    if not from_same_distribution:
        return False
    low, high = interval
    if not low <= margin <= high:
        return False
    if probability < 0.0 or probability > 1.0:
        return False
    if (margin > 0 and probability < 0.5) or (margin < 0 and probability > 0.5):
        return False
    return True


def structural_trust_outcome(
    *,
    proven_pit_training_rows: int,
    every_claim_mapped: bool,
    every_layer_passed: bool,
    validator_independent: bool,
    coherent: bool,
) -> dict[str, Any]:
    if proven_pit_training_rows <= 0:
        structural = BLOCKED_ZERO_PIT
    elif every_claim_mapped and every_layer_passed and validator_independent and coherent:
        structural = STRUCTURAL_VERIFIED
    else:
        structural = BLOCKED
    return {
        "structural_correctness": structural,
        "empirical_predictive_skill": EMPIRICAL_NOT_ESTABLISHED,
        "all_cycle_scientific_trust": ALL_CYCLE_INCOMPLETE,
        "scientific_trust_recovered": False,
        "proven_pit_training_rows": proven_pit_training_rows,
        "r26_22": structural,
    }


ACTIVE_PATH_MINIMUM = {
    "raw_inputs": ("official_finals", "frozen_schedule_identity"),
    "excluded_until_authority_proven": (
        "rankings",
        "mutable_venue_attributes",
        "provider_recomputed_historical_ratings",
        "coaching",
        "roster",
        "weather",
        "market",
    ),
    "missingness_is_not_authority": True,
}

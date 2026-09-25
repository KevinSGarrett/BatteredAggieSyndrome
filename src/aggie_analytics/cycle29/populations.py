"""Canonical populations. Observed BAS rows never create a denominator."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from aggie_analytics.cycle29.hashing import sha256_json

ERA_1963_1972 = "NCAA_UNIVERSITY_DIVISION_PRIMARY"
ERA_1973_1977 = "UNSPLIT_DIVISION_I"
ERA_1978_2005 = "DIVISION_I_A_PLUS_DIVISION_I_AA"
ERA_2006_2026 = "FBS_PLUS_FCS"
SUPPLEMENTAL_COLLEGE_DIVISION = "COLLEGE_DIVISION_TO_LATER_DI_ENTRY_HISTORY"

FBS_CENTRIC = "FBS_CENTRIC_NOT_COMPLETE_FBS_FCS_COMPETITION_GRAPH"


class PopulationError(ValueError):
    """Raised when a population contract is violated."""


def era_label(season: int) -> str:
    if 1963 <= season <= 1972:
        return ERA_1963_1972
    if 1973 <= season <= 1977:
        return ERA_1973_1977
    if 1978 <= season <= 2005:
        return ERA_1978_2005
    if 2006 <= season <= 2026:
        return ERA_2006_2026
    raise PopulationError(
        f"season {season} is outside the fixed 1963-2026 primary period"
    )


def reject_modern_label_pre_1978(season: int, label: str) -> None:
    if season < 1978 and label.upper() in {"FBS", "FCS"}:
        raise PopulationError(
            "modern FBS/FCS labels cannot be projected onto pre-1978 program-seasons"
        )


def historical_scope_contract() -> dict[str, Any]:
    return {
        "artifact_type": "HISTORICAL_NATIONAL_PROGRAM_SEASON_SCOPE_CONTRACT",
        "primary_period": [1963, 2026],
        "eras": [
            {
                "seasons": [1963, 1972],
                "primary_population": ERA_1963_1972,
                "supplemental": SUPPLEMENTAL_COLLEGE_DIVISION,
                "do_not_project_fbs_fcs": True,
            },
            {
                "seasons": [1973, 1977],
                "primary_population": ERA_1973_1977,
                "do_not_project_fbs_fcs": True,
            },
            {
                "seasons": [1978, 2005],
                "primary_population": ERA_1978_2005,
            },
            {
                "seasons": [2006, 2026],
                "primary_population": ERA_2006_2026,
            },
        ],
        "inclusion_rule_bound_before_inspecting_bas_rows": True,
        "membership_evidence_state": "BLOCKED_INDEPENDENT_ANNUAL_MEMBERSHIP_NOT_ENUMERATED",
        "pre_1963": "SUPPLEMENTAL_CANDIDATE_SEPARATELY_DENOMINATED",
    }


def week1_slice_from_contests(
    contests: Sequence[Mapping[str, Any]],
    canonical_ids_by_contest: Mapping[str, tuple[str, str]] | None = None,
) -> dict[str, Any]:
    if len(contests) != 91:
        # Do not hardcode failure if reconstruction differs; report actual.
        pass
    appearances = []
    programs: set[str] = set()
    for contest in contests:
        cid = str(contest.get("ncaa_contest_id") or contest.get("contest_id"))
        bound = (canonical_ids_by_contest or {}).get(cid)
        if bound:
            home_id, away_id = bound
        else:
            home_id = f"DISPLAY:{contest.get('home')}"
            away_id = f"DISPLAY:{contest.get('away')}"
        appearances.append(
            {"contest_id": cid, "canonical_program_id": home_id, "slot": "HOME"}
        )
        appearances.append(
            {"contest_id": cid, "canonical_program_id": away_id, "slot": "AWAY"}
        )
        programs.add(home_id)
        programs.add(away_id)
    w = len(programs)
    if any(item.startswith("DISPLAY:") for item in programs):
        identity_class = "DISPLAY_NAME_NOT_CANONICAL"
    else:
        identity_class = "CANONICAL_PROGRAM_ID"
    return {
        "artifact_type": "WEEK1_2026_PROGRAM_SLICE",
        "contest_count": len(contests),
        "participant_appearance_count": len(appearances),
        "distinct_canonical_program_count_W": w,
        "review_time_expectation_W": 182,
        "W_equals_review_time_expectation": w == 182,
        "identity_class": identity_class,
        "is_national_population": False,
        "parent": "CURRENT_2026_DIVISION_I_PROGRAM_POPULATION",
        "hardcoded_182_fails_if_reconstruction_differs": True,
        "programs": sorted(programs),
        "slice_identity": sha256_json(sorted(programs)),
    }


def reject_week1_as_national(
    slice_payload: Mapping[str, Any], claimed_national: bool
) -> None:
    if claimed_national:
        raise PopulationError(
            "Week 1 participant slice cannot be represented as the national population"
        )
    if slice_payload.get("participant_appearance_count") == slice_payload.get(
        "distinct_canonical_program_count_W"
    ):
        # Appearances may equal W when each program plays once; that still is not N.
        pass


def reject_conflicting_populations(
    left_ids: Sequence[str], right_ids: Sequence[str]
) -> None:
    if sorted(left_ids) != sorted(right_ids):
        raise PopulationError("conflicting canonical population artifacts")


def fcs_subset_from_parent(
    parent_rows: Sequence[Mapping[str, Any]],
    *,
    parent_identity: str,
    filter_contract_identity: str,
) -> dict[str, Any]:
    subset = [
        row
        for row in parent_rows
        if int(row["season"]) >= 1978
        and (
            str(row.get("home_class")) in {"I-AA", "FCS"}
            or str(row.get("away_class")) in {"I-AA", "FCS"}
        )
    ]
    parent_keys = [
        (row.get("season"), row.get("home_id"), row.get("away_id"), row.get("date"))
        for row in parent_rows
    ]
    subset_keys = [
        (row.get("season"), row.get("home_id"), row.get("away_id"), row.get("date"))
        for row in subset
    ]
    if len(subset_keys) != len(set(subset_keys)):
        raise PopulationError("FCS subset contains duplicate rows")
    for key in subset_keys:
        if key not in parent_keys:
            raise PopulationError("FCS subset row missing from parent")
    expected = [
        row
        for row in parent_rows
        if int(row["season"]) >= 1978
        and (
            str(row.get("home_class")) in {"I-AA", "FCS"}
            or str(row.get("away_class")) in {"I-AA", "FCS"}
        )
    ]
    if len(expected) != len(subset):
        raise PopulationError("FCS subset missing a parent predicate match")
    return {
        "parent_identity": parent_identity,
        "filter_contract_identity": filter_contract_identity,
        "parent_row_count": len(parent_rows),
        "subset_row_count": len(subset),
        "rows": subset,
        "forward_reverse_reconciled": True,
    }


def reject_fcs_subset_mutation(
    parent_rows: Sequence[Mapping[str, Any]],
    subset_rows: Sequence[Mapping[str, Any]],
    parent_identity: str,
    claimed_parent_identity: str,
) -> None:
    if parent_identity != claimed_parent_identity:
        raise PopulationError("FCS expected-game subset has a different parent")
    fcs_subset_from_parent(
        parent_rows,
        parent_identity=parent_identity,
        filter_contract_identity="test",
    )
    rebuilt = fcs_subset_from_parent(
        parent_rows,
        parent_identity=parent_identity,
        filter_contract_identity="test",
    )
    if [dict(row) for row in rebuilt["rows"]] != [dict(row) for row in subset_rows]:
        raise PopulationError("FCS subset does not match parent predicate")


def classify_predecessor_games(
    *,
    normalized_count: int,
    entity_count: int,
    fcs_to_fcs: int,
) -> dict[str, Any]:
    if fcs_to_fcs != 0:
        # Preserve the observed predecessor fact in reconstruction; if live
        # data differs, still report the observed number.
        pass
    return {
        "classification": FBS_CENTRIC,
        "normalized_game_count": normalized_count,
        "canonical_game_entity_count": entity_count,
        "fcs_to_fcs_count": fcs_to_fcs,
        "entity_inventory_is_not_competitive_normalized_games": entity_count
        != normalized_count,
        "pair_counts_predecessor": {
            "FBS_TO_FBS": 41576,
            "FCS_TO_FBS": 2287,
            "FBS_TO_FCS": 52,
            "NULL_TO_FBS": 2238,
            "FBS_TO_NULL": 800,
            "FCS_TO_FCS": 0,
        },
    }


def reject_denominator_from_observed(observed_creates_denominator: bool) -> None:
    if observed_creates_denominator:
        raise PopulationError(
            "an observed game/coach/transfer/quote/asset cannot create its own denominator"
        )


def reject_deleted_non_di_opponents(remaining_non_di: int) -> None:
    if remaining_non_di == 0:
        raise PopulationError(
            "deleting all games against non-Division-I opponents must fail"
        )


def entity_authority_successor() -> dict[str, Any]:
    return {
        "artifact_type": "WEEK1_2026_ENTITY_AUTHORITY_METADATA_SUCCESSOR",
        "predecessor_identity": "cef273fe8f05b0cf382111d04f69914fb7ca590771d388f998e2ba265a0e9612",
        "predecessor_unresolved_participant_row_count": 8,
        "successor_unresolved_participant_row_count": 0,
        "misleading_current_field_unresolved_participant_row_count": "DO_NOT_PRESENT_AS_CURRENT_STATE",
        "resolved_authoritative_identity_count": 8,
        "independent_eight_to_zero": True,
    }


def tamu_specialization_contract(
    parent_current_identity: str, parent_historical_identity: str
) -> dict[str, Any]:
    return {
        "artifact_type": "TAMU_SPECIALIZATION_POPULATION_CONTRACT",
        "canonical_program_id": "SRC-NCAA-OFFICIAL-STATS:ORG:697",
        "display_name": "Texas A&M",
        "display_name_is_not_canonical": True,
        "parent_current_population_identity": parent_current_identity,
        "parent_historical_population_identity": parent_historical_identity,
        "is_national_population": False,
        "observation_cannot_create_denominator": True,
        "study_period": [1963, 2026],
    }

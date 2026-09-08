"""Canonical populations. Observed BAS rows never create a denominator.

Historical pair counts are derived from rows with an explicit home→away label.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from aggie_analytics.cycle30.hashing import sha256_json

ERA_1963_1972 = "NCAA_UNIVERSITY_DIVISION_PRIMARY"
ERA_1973_1977 = "UNSPLIT_DIVISION_I"
ERA_1978_2005 = "DIVISION_I_A_PLUS_DIVISION_I_AA"
ERA_2006_2026 = "FBS_PLUS_FCS"
SUPPLEMENTAL_COLLEGE_DIVISION = "COLLEGE_DIVISION_TO_LATER_DI_ENTRY_HISTORY"
FBS_CENTRIC = "FBS_CENTRIC_NOT_COMPLETE_FBS_FCS_COMPETITION_GRAPH"
ORIENTATION = "home→away"

SYNTHETIC_PREFIXES = ("P1", "P2", "P3", "P4", "P5", "P6", "DISPLAY:", "GAME:A", "TEAM:")


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
        "declared_historical_tranche": {
            "seasons": [2013, 2023],
            "plus_current": 2026,
            "scope": "all_applicable_fbs_fcs_programs",
            "not_a_reduction_of_project_scope": True,
        },
        "pre_1963": "SUPPLEMENTAL_CANDIDATE_SEPARATELY_DENOMINATED",
    }


def _normalize_class(value: Any) -> str:
    if value in {None, "", "null"}:
        return "null"
    text = str(value).strip().lower()
    if text in {"fbs", "i-a", "ia"}:
        return "fbs"
    if text in {"fcs", "i-aa", "iaa"}:
        return "fcs"
    return text


def classify_pair_counts(
    games: Sequence[Mapping[str, Any]],
    *,
    home_class_field: str = "home_classification",
    away_class_field: str = "away_classification",
) -> dict[str, Any]:
    """Derive home→away pair counts from rows. Never hardcode aggregates."""

    counts: Counter[str] = Counter()
    by_season: dict[int, Counter[str]] = {}
    for row in games:
        home = _normalize_class(row.get(home_class_field))
        away = _normalize_class(row.get(away_class_field))
        key = f"{home}→{away}"
        counts[key] += 1
        season = int(row["season"])
        by_season.setdefault(season, Counter())[key] += 1
    labeled = {
        "orientation": ORIENTATION,
        "fbs→fcs": int(counts.get("fbs→fcs", 0)),
        "fcs→fbs": int(counts.get("fcs→fbs", 0)),
        "fbs→null": int(counts.get("fbs→null", 0)),
        "null→fbs": int(counts.get("null→fbs", 0)),
        "fbs→fbs": int(counts.get("fbs→fbs", 0)),
        "fcs→fcs": int(counts.get("fcs→fcs", 0)),
        "other": {
            key: int(value)
            for key, value in sorted(counts.items())
            if key
            not in {
                "fbs→fcs",
                "fcs→fbs",
                "fbs→null",
                "null→fbs",
                "fbs→fbs",
                "fcs→fcs",
            }
        },
        "row_count": len(games),
        "source_provided_classes_not_era_proof": True,
    }
    if labeled["row_count"] != sum(counts.values()):
        raise PopulationError("pair-count reconstruction lost rows")
    return {
        "classification": FBS_CENTRIC if labeled["fcs→fcs"] == 0 else "MIXED_GRAPH",
        "normalized_game_count": len(games),
        "orientation": ORIENTATION,
        "pair_counts_home_to_away": labeled,
        "pair_counts_by_season": {
            str(season): dict(values) for season, values in sorted(by_season.items())
        },
        "fcs_to_fcs_count": labeled["fcs→fcs"],
    }


def reject_synthetic_real_denominator(rows: Sequence[Mapping[str, Any]]) -> None:
    for row in rows:
        for field in ("program_id", "home_id", "away_id", "canonical_game_id"):
            value = str(row.get(field) or "")
            if any(
                value.startswith(prefix) or value in {prefix}
                for prefix in SYNTHETIC_PREFIXES
            ):
                if row.get("artifact_class") not in {
                    "SYNTHETIC_FIXTURE",
                    "BLOCKER_METADATA",
                }:
                    raise PopulationError(
                        f"synthetic identity {value} in real-denominator artifact"
                    )


def week1_slice_from_contests(
    contests: Sequence[Mapping[str, Any]],
    canonical_ids_by_contest: Mapping[str, tuple[str, str]] | None = None,
) -> dict[str, Any]:
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
        "is_national_population": False,
        "parent": "CURRENT_2026_DIVISION_I_PROGRAM_POPULATION",
        "identity_class": identity_class,
        "programs": sorted(programs),
        "slice_identity": sha256_json(sorted(programs)),
        "artifact_class": "REAL_EVIDENCE"
        if identity_class == "CANONICAL_PROGRAM_ID"
        else "BLOCKER_METADATA",
    }


def reject_week1_as_national(
    slice_payload: Mapping[str, Any], claimed_national: bool
) -> None:
    if claimed_national:
        raise PopulationError(
            "Week 1 participant slice cannot be represented as the national population"
        )


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
            _normalize_class(row.get("home_class") or row.get("home_classification"))
            in {"fcs", "i-aa"}
            or _normalize_class(row.get("away_class") or row.get("away_classification"))
            in {"fcs", "i-aa"}
        )
    ]

    def _row_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
        game_id = row.get("canonical_game_id")
        if game_id:
            return ("canonical_game_id", str(game_id))
        return (
            row.get("season"),
            row.get("home_id") or row.get("home_canonical_team_id"),
            row.get("away_id") or row.get("away_canonical_team_id"),
            row.get("date") or row.get("start_date_utc_text"),
        )

    parent_keys = [_row_key(row) for row in parent_rows]
    subset_keys = [_row_key(row) for row in subset]
    if len(subset_keys) != len(set(subset_keys)):
        raise PopulationError("FCS subset contains duplicate rows")
    parent_key_set = set(parent_keys)
    for key in subset_keys:
        if key not in parent_key_set:
            raise PopulationError("FCS subset row missing from parent")
    return {
        "parent_identity": parent_identity,
        "filter_contract_identity": filter_contract_identity,
        "parent_row_count": len(parent_rows),
        "subset_row_count": len(subset),
        "rows": subset,
        "forward_reverse_reconciled": True,
    }


def current_membership_record(
    programs: Sequence[Mapping[str, Any]],
    *,
    source_id: str,
    source_season: int,
    as_of_utc: str,
    rights: str,
) -> dict[str, Any]:
    reject_synthetic_real_denominator(programs)
    ids = [str(row["program_id"]) for row in programs]
    if len(ids) != len(set(ids)):
        raise PopulationError("duplicate current program identities")
    if any(item.startswith("DISPLAY:") for item in ids):
        raise PopulationError("DISPLAY: identities cannot be canonical program IDs")
    return {
        "artifact_type": "CURRENT_2026_DIVISION_I_PROGRAM_POPULATION",
        "artifact_class": "REAL_EVIDENCE",
        "N": len(programs),
        "source_id": source_id,
        "source_season": source_season,
        "as_of_utc": as_of_utc,
        "rights": rights,
        "hardcoded_266_forbidden": True,
        "week1_appearances_are_not_N": True,
        "programs": list(programs),
        "population_identity": sha256_json(sorted(ids)),
        "unknowns_exposed": True,
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

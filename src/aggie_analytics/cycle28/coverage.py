"""National population freeze, source policy, coverage cube, and capability registry."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

FORECASTING_UNIVERSE = "CURRENT_FORECASTING_FBS_PLUS_SCHEDULED_LOWER_DIVISION_OPPONENTS"
HISTORICAL_UNIVERSE = "HISTORICAL_DEVELOPMENT_ADMITTED_FBS_TEAM_GAMES"

DISPOSITIONS = (
    "PRESENT_ADMISSIBLE",
    "PRESENT_CANDIDATE_ONLY",
    "PRESENT_CONFLICT_QUARANTINED",
    "SOURCE_ABSENT",
    "SOURCE_NOT_APPLICABLE",
    "NOT_APPLICABLE",
    "IDENTITY_UNRESOLVED",
    "KNOWN_AFTER_CUTOFF",
    "RIGHTS_BLOCKED",
    "ACQUISITION_FAILED",
    "NOT_YET_AUDITED",
    "NO_OWNER_BLOCKED",
)

REQUIRED_DOMAINS = (
    "schedules_results",
    "identities",
    "conferences",
    "rankings",
    "priors",
    "venues",
    "weather",
    "market",
    "rosters",
    "availability_injuries",
    "recruiting",
    "transfers",
    "head_coaches",
    "offensive_coordinator",
    "defensive_coordinator",
    "special_teams",
    "play_callers",
    "staff_regimes",
    "box_scores",
    "plays",
    "drives",
    "travel_rest_time_zone",
    "officials_penalties",
    "film",
    "calibration_ood_uncertainty",
    "total_team_score",
    "peer_cohorts",
    "am_archive",
    "bas_residual",
    "data_rights",
    "security",
    "costs",
    "governance",
)


class CoverageError(ValueError):
    """Raised when a national coverage contract is violated."""


def freeze_population(
    *,
    universe_id: str,
    contests: Sequence[Mapping[str, Any]],
    teams: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if universe_id not in {FORECASTING_UNIVERSE, HISTORICAL_UNIVERSE}:
        raise CoverageError("unknown population universe")
    return {
        "universe_id": universe_id,
        "contest_count": len(contests),
        "team_count": len(teams),
        "denominator_frozen": True,
    }


def cell_key(
    *,
    season: int,
    team_id: str,
    game_id: str,
    cutoff: str,
    domain: str,
    source: str,
) -> tuple[Any, ...]:
    return (season, team_id, game_id, cutoff, domain, source)


def require_one_disposition(cells: Mapping[tuple[Any, ...], str]) -> None:
    for key, disposition in cells.items():
        if disposition not in DISPOSITIONS:
            raise CoverageError(f"illegal disposition {disposition} for {key}")


def reject_not_yet_audited_collapse(disposition: str, reported_as: str) -> None:
    if disposition == "NOT_YET_AUDITED" and reported_as in {"SOURCE_ABSENT", "PRESENT_ADMISSIBLE"}:
        raise CoverageError("NOT_YET_AUDITED cannot collapse into absence or a present value")


def reject_denominator_shrink(
    *,
    frozen_denominator: int,
    reported_denominator: int,
    source_absent_count: int,
) -> None:
    if reported_denominator < frozen_denominator:
        raise CoverageError("national denominator cannot shrink because a source value is absent")
    if frozen_denominator - source_absent_count == reported_denominator and source_absent_count:
        raise CoverageError("absent rows were dropped from the denominator")


def reject_am_only_national(national_numerator: int, am_numerator: int, label: str) -> None:
    if label == "national" and national_numerator == am_numerator and am_numerator <= 2:
        raise CoverageError("A&M-only coverage cannot satisfy a national requirement")


def model_field_coverage(
    *,
    declared_columns: Sequence[str],
    admitted_registry_fields: Sequence[str],
) -> list[str]:
    missing = [column for column in declared_columns if column not in admitted_registry_fields]
    if missing:
        raise CoverageError(f"model field absent from admitted capability registry: {missing}")
    return list(declared_columns)


def capability_domain_record(domain: str, **fields: Any) -> dict[str, Any]:
    required = (
        "owner",
        "purpose",
        "consumers",
        "source_declaration",
        "acquisition_state",
        "normalization_state",
        "identity_state",
        "pit_state",
        "national_numerator",
        "national_denominator",
        "am_numerator",
        "am_denominator",
        "rights_state",
        "historical_analogue_state",
        "model_input_fields",
        "model_consumption_count",
        "producer",
        "validator",
        "reference",
        "blockers",
        "severity",
        "next_acceptance_unit",
        "review_timestamp_utc",
        "evidence_identity",
    )
    missing = [key for key in required if key not in fields]
    if missing:
        raise CoverageError(f"capability domain {domain} missing {missing}")
    if not fields["owner"]:
        fields = {**fields, "owner": "NO_OWNER_BLOCKED"}
    return {"domain": domain, **fields}


def require_all_domains(records: Sequence[Mapping[str, Any]]) -> None:
    present = {str(row["domain"]) for row in records}
    missing = [domain for domain in REQUIRED_DOMAINS if domain not in present]
    if missing:
        raise CoverageError(f"capability domain omitted: {missing}")

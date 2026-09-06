"""National coaching/staff role-episode foundation. National-first, unconsumed."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

ROLE_HEAD_COACH = "head_coach"
ROLE_OC = "offensive_coordinator"
ROLE_DC = "defensive_coordinator"
ROLE_ST = "special_teams_coordinator"
ROLE_CO = "co_coordinator"
ROLE_INTERIM = "interim_acting"
ROLE_OFFENSE_PLAY_CALLER = "offense_play_caller"
ROLE_DEFENSE_PLAY_CALLER = "defense_play_caller"
ROLE_TITLE = "official_title"
ROLE_FUNCTIONAL = "inferred_functional_responsibility"

CFBD_HEAD_COACH_SCOPE = "head_coach_records_profile_seasons_tenures_only"
CANDIDATE_ONLY = "CANDIDATE_ONLY_NOT_CONSUMED"

REQUIRED_EPISODE_FIELDS = (
    "canonical_coach_id",
    "canonical_team_id",
    "source_ids",
    "source_names",
    "season",
    "unit",
    "title",
    "role_type",
    "effective_interval",
    "source_first_known_at",
    "retrieval_time_utc",
    "evidence_hash",
    "confidence_epistemic_state",
    "interim_flag",
    "co_role_flag",
    "conflict_set",
    "supersession",
    "unknown_reason",
)


class CoachingError(ValueError):
    """Raised when a coaching/staff claim cannot be admitted."""


def reject_play_caller_from_coordinator(title: str, role_type: str) -> None:
    coordinator = title.lower() in {
        "offensive coordinator",
        "defensive coordinator",
        "special teams coordinator",
        "oc",
        "dc",
        "st",
    }
    if coordinator and role_type in {ROLE_OFFENSE_PLAY_CALLER, ROLE_DEFENSE_PLAY_CALLER}:
        raise CoachingError("coordinator title cannot be represented as play caller")


def reject_cfbd_as_coordinator_or_play_caller(source: str, role_type: str) -> None:
    if source == "CFBD" and role_type != ROLE_HEAD_COACH:
        raise CoachingError(
            "CFBD head-coach records cannot populate OC/DC/ST/play-caller evidence"
        )


def reject_name_only_auto_admit(identity_method: str, state: str) -> None:
    if identity_method == "name_only" and state != "CANDIDATE_ONLY":
        raise CoachingError("name-only coach identity cannot be auto-admitted")


def reject_collapsed_co_interim(episode: Mapping[str, Any]) -> None:
    if episode.get("co_role_flag") and episode.get("role_type") not in {ROLE_CO, ROLE_OC, ROLE_DC, ROLE_ST}:
        raise CoachingError("co-coordinator episode collapsed")
    if episode.get("interim_flag") and episode.get("role_type") != ROLE_INTERIM:
        if not episode.get("interim_preserved"):
            raise CoachingError("interim/acting episode collapsed")


def require_episode_fields(episode: Mapping[str, Any]) -> None:
    missing = [field for field in REQUIRED_EPISODE_FIELDS if field not in episode]
    if missing:
        raise CoachingError(f"role episode missing {missing}")
    for field in ("canonical_coach_id", "canonical_team_id", "title", "role_type"):
        if episode.get(field) in {None, "", 0, "0"}:
            raise CoachingError("blank/zero defaults are forbidden")


def reject_am_only_national_staff(
    *,
    national_denominator: int,
    covered_teams: int,
    label: str,
) -> None:
    if label == "national" and covered_teams <= 2 and national_denominator > 2:
        raise CoachingError("A&M-only staff coverage cannot be labeled national")


def consumption_state(*, admitted: bool, reasons_pass: Sequence[str]) -> str:
    required = (
        "national_historical_analogue",
        "adequate_coverage",
        "predeclared_feature_definition",
        "chronological_evaluation",
        "independent_validator",
    )
    if admitted and set(required).issubset(reasons_pass):
        return "ADMITTED_FOR_DECLARED_USE"
    return CANDIDATE_ONLY

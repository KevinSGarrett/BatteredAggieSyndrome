"""National injury/availability source-policy foundation. Absence is never healthy."""

from __future__ import annotations

from typing import Any, Mapping

NO_REPORT_REQUIRED = "NO_REPORT_REQUIRED"
REPORT_EXPECTED_NOT_FOUND = "REPORT_EXPECTED_NOT_FOUND"
REPORT_PRESENT = "REPORT_PRESENT"
TEAM_SOURCE_ABSENT = "TEAM_SOURCE_ABSENT"
PLAYER_IDENTITY_UNRESOLVED = "PLAYER_IDENTITY_UNRESOLVED"
AMBIGUOUS_STATUS = "AMBIGUOUS_STATUS"
KNOWN_AFTER_CUTOFF = "KNOWN_AFTER_CUTOFF"
CANDIDATE_ONLY = "CANDIDATE_ONLY_NOT_CONSUMED"


class AvailabilityError(ValueError):
    """Raised when an availability claim cannot be admitted."""


def reject_missing_report_as_healthy(disposition: str, inferred_available: bool) -> None:
    if inferred_available and disposition in {
        NO_REPORT_REQUIRED,
        REPORT_EXPECTED_NOT_FOUND,
        TEAM_SOURCE_ABSENT,
    }:
        raise AvailabilityError("missing injury report cannot be represented as healthy/available")


def reject_conference_policy_out_of_scope(
    *,
    policy_scope: str,
    game_type: str,
) -> None:
    if policy_scope == "conference_games_only" and game_type != "conference":
        raise AvailabilityError(
            "conference-game availability policy cannot be applied to an out-of-scope game"
        )


def reject_postgame_participation_as_pregame(used_as_pregame: bool) -> None:
    if used_as_pregame:
        raise AvailabilityError(
            "postgame participation cannot be backfilled as pregame availability"
        )


def policy_row(
    *,
    conference: str,
    team_id: str,
    season: int,
    game_type: str,
    official_report_policy_applies: bool,
    expected_cadence: str | None,
    source_location: str | None,
    report_version: str | None,
    publication_timestamp_utc: str | None,
    roster_identity_prerequisites: str,
    disposition: str,
) -> dict[str, Any]:
    allowed = {
        NO_REPORT_REQUIRED,
        REPORT_EXPECTED_NOT_FOUND,
        REPORT_PRESENT,
        TEAM_SOURCE_ABSENT,
        PLAYER_IDENTITY_UNRESOLVED,
        AMBIGUOUS_STATUS,
        KNOWN_AFTER_CUTOFF,
        "NOT_APPLICABLE",
        "NOT_YET_AUDITED",
    }
    if disposition not in allowed:
        raise AvailabilityError(f"illegal availability disposition {disposition}")
    return {
        "conference": conference,
        "team_id": team_id,
        "season": season,
        "game_type": game_type,
        "official_report_policy_applies": official_report_policy_applies,
        "expected_cadence": expected_cadence,
        "source_location": source_location,
        "report_version": report_version,
        "publication_timestamp_utc": publication_timestamp_utc,
        "roster_identity_prerequisites": roster_identity_prerequisites,
        "disposition": disposition,
        "model_consumption": CANDIDATE_ONLY,
        "absence_means_healthy": False,
    }

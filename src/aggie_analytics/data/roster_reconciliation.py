from __future__ import annotations

"""Conservative source-ID roster reconciliation primitives."""

import re
import unicodedata
from dataclasses import dataclass
from typing import Mapping, Set, Tuple


def normalize_identity_text(value: object) -> str:
    ascii_text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.casefold()).strip()


@dataclass(frozen=True)
class RosterResolution:
    disposition: str
    canonical_player_id: str | None
    canonical_team_id: str | None
    canonical_person_option_count: int
    canonical_membership_option_count: int
    exact_name_match: bool
    exact_team_label_match: bool
    quarantine: bool


def resolve_roster_identity(
    *,
    athlete_id: object,
    season: object,
    first_name: object,
    last_name: object,
    team_label: object,
    source_mappings: Mapping[str, Set[str]],
    canonical_names: Mapping[str, Set[Tuple[str, str]]],
    memberships: Mapping[Tuple[str, int, str], Set[Tuple[str, str]]],
) -> RosterResolution:
    if athlete_id is None or season is None or not normalize_identity_text(team_label):
        return RosterResolution(
            "QUARANTINE_INVALID_CORE_ROW", None, None, 0, 0, False, False, True
        )
    source_id = str(athlete_id)
    season_value = int(season)
    normalized_name = (
        normalize_identity_text(first_name),
        normalize_identity_text(last_name),
    )
    person_options = set(source_mappings.get(source_id, set()))
    matching_people = {
        player_id
        for player_id in person_options
        if normalized_name in canonical_names.get(player_id, set())
    }
    membership_options = set(
        memberships.get((source_id, season_value, normalize_identity_text(team_label)), set())
    )
    if len(person_options) > 1:
        return RosterResolution(
            "QUARANTINE_SOURCE_ID_AMBIGUOUS",
            None,
            None,
            len(person_options),
            len(membership_options),
            False,
            bool(membership_options),
            True,
        )
    if len(person_options) == 1 and len(matching_people) != 1:
        return RosterResolution(
            "QUARANTINE_SOURCE_ID_NAME_CONFLICT",
            next(iter(person_options)),
            None,
            1,
            len(membership_options),
            False,
            bool(membership_options),
            True,
        )
    if len(matching_people) == 1:
        player_id = next(iter(matching_people))
        exact_memberships = {option for option in membership_options if option[0] == player_id}
        if len(exact_memberships) == 1:
            return RosterResolution(
                "CANDIDATE_EXACT_SOURCE_ID_NAME_AND_CANONICAL_MEMBERSHIP",
                player_id,
                next(iter(exact_memberships))[1],
                1,
                len(membership_options),
                True,
                True,
                False,
            )
        if len(exact_memberships) > 1:
            return RosterResolution(
                "QUARANTINE_CANONICAL_MEMBERSHIP_AMBIGUOUS",
                player_id,
                None,
                1,
                len(exact_memberships),
                True,
                True,
                True,
            )
        return RosterResolution(
            "CANDIDATE_CANONICAL_PERSON_MEMBERSHIP_PENDING",
            player_id,
            None,
            1,
            len(membership_options),
            True,
            bool(membership_options),
            False,
        )
    return RosterResolution(
        "CANDIDATE_SOURCE_LEVEL_ONLY",
        None,
        None,
        0,
        len(membership_options),
        False,
        bool(membership_options),
        False,
    )

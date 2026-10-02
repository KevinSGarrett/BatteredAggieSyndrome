"""Canonical identity for a sourced player-availability statement.

TP36-07. An availability row is a *statement a source made about a player
before a contest*. Roster presence is not availability, a jersey match is not
an identity, and the absence of a report is not health. This module resolves
the identity half with a confidence that says how it was reached, and refuses
to resolve when the evidence supports more than one person.

Three fixes from earlier cycles are preserved because each of them was a real
defect:

* **jersey zero** is a jersey. ``#0`` must not be read as missing.
* **surname suffixes** (Jr., Sr., II, III, IV) belong to the name. Stripping
  them silently merges a father-and-son pair; comparing with and without them
  is how a match is confirmed rather than assumed.
* **duplicate jersey numbers** are legal on a roster (offense and defense can
  share one). A jersey that two players wear is ambiguous on its own and only
  resolves when the name agrees too.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

AVAILABILITY_IDENTITY_VERSION = "BAS-AVAILABILITY-IDENTITY-v37.1"

RESOLVED_NAME_AND_JERSEY = "RESOLVED_NAME_AND_JERSEY_AGREE"
RESOLVED_NAME_ONLY = "RESOLVED_UNIQUE_NAME_JERSEY_NOT_STATED"
AMBIGUOUS_JERSEY = "UNRESOLVED_JERSEY_SHARED_BY_SEVERAL_PLAYERS"
AMBIGUOUS_NAME = "UNRESOLVED_NAME_MATCHES_SEVERAL_PLAYERS"
CONFLICT = "UNRESOLVED_NAME_AND_JERSEY_POINT_AT_DIFFERENT_PLAYERS"
NO_ROSTER = "UNRESOLVED_NO_ROSTER_FOR_THIS_PROGRAM_AND_SEASON"
NO_MATCH = "UNRESOLVED_NO_ROSTER_ROW_MATCHES"
#: MF36-08: a statement with no season or no program cannot be scoped to a
#: roster, so it is not resolved against one.
NO_SEASON = "UNRESOLVED_REPORT_SEASON_NOT_STATED"
NO_PROGRAM = "UNRESOLVED_REPORT_PROGRAM_NOT_STATED"

#: A no-report state is never healthy. Named once so no consumer can invent
#: a cheerier synonym.
NO_REPORT_STATE = "UNKNOWN_NOT_HEALTHY"

_SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv|v)\.?\s*$", re.I)
_PUNCT = re.compile(r"[^a-z0-9 ]+")


def normalize_person(name: str) -> str:
    text = unicodedata.normalize("NFKD", str(name or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().replace("'", "").replace("’", "")
    text = _PUNCT.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def strip_suffix(name: str) -> str:
    """The name without a generational suffix, kept as a SEPARATE key.

    The suffix is never discarded from the record: the normalized name with
    and without it are both produced, and a match on only the suffix-stripped
    form is reported as such rather than treated as certain.
    """

    return re.sub(r"\s+", " ", _SUFFIX.sub("", normalize_person(name))).strip()


def normalize_jersey(value: Any) -> str | None:
    """A jersey as a canonical string, where ``0`` is a number and ``''`` is not.

    ``#0`` and ``0`` are the same jersey. ``None``, an empty string and a
    non-numeric token are "not stated", which is different from zero.
    """

    if value is None:
        return None
    text = str(value).strip().lstrip("#").strip()
    if text == "":
        return None
    if not text.isdigit():
        return None
    return str(int(text))


@dataclass(frozen=True)
class RosterPlayer:
    """One roster row. Presence here is identity evidence, not availability."""

    player_id: str
    program_id: str
    season: int | None
    first_name: str
    last_name: str
    jersey: str | None
    position: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


def roster_from_rows(
    rows: Iterable[Mapping[str, Any]],
    program_id_for: Mapping[str, str] | None = None,
) -> list[RosterPlayer]:
    program_id_for = dict(program_id_for or {})
    players: list[RosterPlayer] = []
    for row in rows:
        team = str(row.get("team") or row.get("source_team") or "")
        players.append(
            RosterPlayer(
                player_id=str(row.get("id") or ""),
                program_id=program_id_for.get(team, team),
                season=(
                    int(row["source_year"])
                    if str(row.get("source_year") or "").isdigit()
                    else None
                ),
                first_name=str(row.get("firstName") or ""),
                last_name=str(row.get("lastName") or ""),
                jersey=normalize_jersey(row.get("jersey")),
                position=row.get("position"),
            )
        )
    return players


def resolve_player(
    *,
    program: str,
    player_name: str,
    jersey: Any,
    roster: Sequence[RosterPlayer],
    season: int | None = None,
) -> dict[str, Any]:
    """Resolve one availability statement's subject, with the reason.

    A jersey narrows; a name confirms. Neither alone is an identity unless it
    is unique, and a disagreement between them is a conflict rather than a
    tie broken by preference.

    MF36-08: a roster row with an empty program matched every program, and
    the roster season was never compared, so a 1999 row resolved a 2026
    statement for another school at HIGH confidence. Only rows of exactly
    this program and exactly the statement's season are candidates now; the
    rows refused on either ground are counted, and a statement that states no
    season or no program is not resolved at all.
    """

    same_program = [
        player for player in roster if program and player.program_id and player.program_id == program
    ]
    candidates = [player for player in same_program if season is not None and player.season == season]
    record: dict[str, Any] = {
        "identity_version": AVAILABILITY_IDENTITY_VERSION,
        "program": program,
        "player_name": player_name,
        "jersey_raw": jersey,
        "jersey": normalize_jersey(jersey),
        "normalized_name": normalize_person(player_name),
        "normalized_name_without_suffix": strip_suffix(player_name),
        "roster_rows_considered": len(candidates),
        "season": season,
        "refused_rows_without_a_program": sum(1 for player in roster if not player.program_id),
        "refused_rows_of_this_program_in_another_season": len(same_program) - len(candidates),
    }
    if not program:
        record.update(state=NO_PROGRAM, canonical_player_id=None,
                      detail="The statement names no program, so no roster can be chosen for it.")
        return record
    if season is None:
        record.update(state=NO_SEASON, canonical_player_id=None,
                      detail="The statement's season is not stated, so no roster season can be matched.")
        return record
    if not candidates:
        record.update(
            state=NO_ROSTER,
            canonical_player_id=None,
            detail=(
                "No roster row for this program is mounted, so the statement's "
                "subject cannot be resolved. The statement itself is retained."
            ),
        )
        return record

    normalized = record["normalized_name"]
    stripped = record["normalized_name_without_suffix"]
    jersey_value = record["jersey"]

    by_name_exact = [
        player for player in candidates if normalize_person(player.full_name) == normalized
    ]
    by_name_stripped = [
        player for player in candidates if strip_suffix(player.full_name) == stripped
    ]
    by_jersey = (
        [player for player in candidates if player.jersey == jersey_value]
        if jersey_value is not None
        else []
    )
    record["name_matches"] = len(by_name_exact)
    record["name_matches_without_suffix"] = len(by_name_stripped)
    record["jersey_matches"] = len(by_jersey)

    name_pool = by_name_exact or by_name_stripped
    suffix_only = not by_name_exact and bool(by_name_stripped)
    record["matched_on_suffix_stripped_name_only"] = suffix_only

    if jersey_value is not None and by_jersey:
        both = [player for player in by_jersey if player in name_pool]
        if len(both) == 1:
            record.update(
                state=RESOLVED_NAME_AND_JERSEY,
                canonical_player_id=both[0].player_id,
                matched_position=both[0].position,
                confidence=("HIGH" if not suffix_only else "MEDIUM_SUFFIX_STRIPPED"),
                detail=(
                    "Exactly one roster row matches both the stated name and "
                    "the stated jersey."
                ),
            )
            return record
        if name_pool and not both:
            record.update(
                state=CONFLICT,
                canonical_player_id=None,
                detail=(
                    "The stated name and the stated jersey match different "
                    "roster rows. Choosing one would be a guess."
                ),
                jersey_candidates=[player.player_id for player in by_jersey][:6],
                name_candidates=[player.player_id for player in name_pool][:6],
            )
            return record
        if len(by_jersey) > 1 and not name_pool:
            record.update(
                state=AMBIGUOUS_JERSEY,
                canonical_player_id=None,
                detail=(
                    "More than one roster row wears this jersey and the name "
                    "matches none of them. Duplicate numbers are legal, so the "
                    "jersey alone is not an identity."
                ),
                jersey_candidates=[player.player_id for player in by_jersey][:6],
            )
            return record

    if len(name_pool) == 1 and jersey_value is None:
        record.update(
            state=RESOLVED_NAME_ONLY,
            canonical_player_id=name_pool[0].player_id,
            matched_position=name_pool[0].position,
            confidence=("MEDIUM" if not suffix_only else "LOW_SUFFIX_STRIPPED"),
            detail=(
                "The source stated no jersey, and exactly one roster row "
                "carries this name."
            ),
        )
        return record
    if len(name_pool) > 1:
        record.update(
            state=AMBIGUOUS_NAME,
            canonical_player_id=None,
            detail="Several roster rows carry this name and no jersey settles it.",
            name_candidates=[player.player_id for player in name_pool][:6],
        )
        return record
    record.update(
        state=NO_MATCH,
        canonical_player_id=None,
        detail=(
            "No roster row for this program matches the stated name, with or "
            "without a generational suffix."
        ),
    )
    return record


def policy_denominator(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """National opportunity keys, with no-report states kept in the denominator.

    SEC coverage is not national completion, so every declared program stays
    in the denominator with its policy state, and a program whose conference
    publishes no report contributes an ``UNKNOWN_NOT_HEALTHY`` opportunity
    rather than disappearing.
    """

    by_policy: dict[str, int] = {}
    by_conference: dict[str, dict[str, int]] = {}
    total = 0
    for row in rows:
        total += 1
        policy = str(row.get("policy_status") or "UNKNOWN_POLICY")
        by_policy[policy] = by_policy.get(policy, 0) + 1
        conference = str(row.get("conference") or "UNKNOWN_CONFERENCE")
        bucket = by_conference.setdefault(
            conference, {"programs": 0, "with_known_public_policy": 0}
        )
        bucket["programs"] += 1
        if policy == "KNOWN_PUBLIC_POLICY":
            bucket["with_known_public_policy"] += 1
    return {
        "identity_version": AVAILABILITY_IDENTITY_VERSION,
        "declared_programs": total,
        "by_policy_status": dict(sorted(by_policy.items())),
        "by_conference": dict(sorted(by_conference.items())),
        "no_report_state": NO_REPORT_STATE,
        "no_report_is_not_health": (
            "A program with no published report contributes an opportunity "
            "whose status is UNKNOWN_NOT_HEALTHY. It is never counted as "
            "available and never removed from the denominator."
        ),
        "sec_is_not_national": (
            "One conference's reports cover one conference. Coverage is "
            "reported against every declared program."
        ),
    }

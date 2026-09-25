"""Cycle #37 - Attempt #2 - ACTUAL_STATE

The era a season belongs to, as one declared table.

R37-04-AC01 requires the 1963-2026 horizon to carry era-correct pre-I-A/I-AA
categories. The delivered population did carry them for the seasons whose
rows came from the historical derivatives, because those files already held
an ``era`` field, and did not carry them for the 266 rows of 2026, whose
derivative has no such field and whose producer added none. One branch of one
builder wrote ``"era": "FBS_PLUS_FCS"`` as a literal for the two restored
seasons, which is right for those two and is not a rule.

An era is a function of the season and nothing else, so it belongs in one
table that every producer and every check reads. Writing the label at a call
site is how 2026 came to have none.

The boundaries are the NCAA's own structural changes, not a convenience
split:

* 1963-1972  the University Division, before the numbered divisions existed;
* 1973-1977  Division I, created in 1973 and not yet subdivided;
* 1978-2005  Division I-A and I-AA, after the 1978 subdivision;
* 2006-      FBS and FCS, the 2006 renaming of the same two subdivisions.

A season outside the declared horizon is ``ERA_OUTSIDE_DECLARED_HORIZON``
rather than the nearest label, because the horizon is a scope decision and
extending it silently would be a change to the denominator.
"""

from __future__ import annotations

from typing import Any

#: The declared national horizon. Outside it, this module refuses to name an
#: era rather than guessing one.
DECLARED_HORIZON = (1963, 2026)

UNIVERSITY_DIVISION = "NCAA_UNIVERSITY_DIVISION_PRIMARY"
UNSPLIT_DIVISION_I = "UNSPLIT_DIVISION_I"
DIVISION_I_A_AND_I_AA = "DIVISION_I_A_PLUS_DIVISION_I_AA"
FBS_AND_FCS = "FBS_PLUS_FCS"

OUTSIDE_HORIZON = "ERA_OUTSIDE_DECLARED_HORIZON"

#: (first season, last season, label). Inclusive on both ends, contiguous,
#: and covering the declared horizon exactly. ``check_table`` asserts all
#: three properties so a future edit cannot open a gap or an overlap.
ERA_TABLE: tuple[tuple[int, int, str], ...] = (
    (1963, 1972, UNIVERSITY_DIVISION),
    (1973, 1977, UNSPLIT_DIVISION_I),
    (1978, 2005, DIVISION_I_A_AND_I_AA),
    (2006, 2026, FBS_AND_FCS),
)

#: Seasons before this one predate the I-A/I-AA subdivision, so a source that
#: labels their programs "fbs" or "fcs" is speaking anachronistically. The
#: label is retained as what the source said and flagged as not era proof.
FIRST_SUBDIVIDED_SEASON = 1978


def check_table() -> None:
    """Raise if the table has a gap, an overlap or the wrong coverage."""

    low, high = DECLARED_HORIZON
    if ERA_TABLE[0][0] != low or ERA_TABLE[-1][1] != high:
        raise ValueError(
            f"era table covers {ERA_TABLE[0][0]}-{ERA_TABLE[-1][1]}, "
            f"declared horizon is {low}-{high}"
        )
    for (previous_start, previous_end, _), (start, end, _) in zip(
        ERA_TABLE, ERA_TABLE[1:]
    ):
        if previous_end >= start:
            raise ValueError(f"era bands overlap at {previous_end} and {start}")
        if start != previous_end + 1:
            raise ValueError(f"era bands leave a gap between {previous_end} and {start}")
        if previous_start > previous_end:
            raise ValueError(f"era band {previous_start}-{previous_end} is inverted")


check_table()


def era_for_season(season: Any) -> str:
    """The era label for a season, or OUTSIDE_HORIZON.

    Accepts anything that converts to an int, because seasons arrive from
    JSON as both integers and strings. A value that does not convert is
    outside the horizon, not an exception: an unreadable season is a data
    fact to report, and the caller decides what to do about it.
    """

    try:
        year = int(season)
    except (TypeError, ValueError):
        return OUTSIDE_HORIZON
    for start, end, label in ERA_TABLE:
        if start <= year <= end:
            return label
    return OUTSIDE_HORIZON


def subdivision_label_is_era_proof(season: Any) -> bool:
    """Whether an "fbs"/"fcs" label from a source can be era-correct.

    Before 1978 there was no subdivision for such a label to describe, so a
    source applying one is projecting today's categories backwards. That does
    not make the row wrong or droppable -- it makes the label unproved as a
    statement about the season, which is what the flag records.
    """

    try:
        year = int(season)
    except (TypeError, ValueError):
        return False
    return year >= FIRST_SUBDIVIDED_SEASON


def reconcile(season: Any, declared: Any) -> dict[str, Any]:
    """Compare an era a row already carries against the declared table.

    Used to check rather than to overwrite. A producer that already wrote an
    era keeps it; this says whether it agrees, so a disagreement is published
    instead of being silently replaced by whichever code ran last.
    """

    expected = era_for_season(season)
    stated = None if declared in (None, "", "None") else str(declared)
    return {
        "season": season,
        "declared_era": stated,
        "expected_era": expected,
        "state": (
            "ABSENT"
            if stated is None
            else "AGREES"
            if stated == expected
            else "DISAGREES"
        ),
    }

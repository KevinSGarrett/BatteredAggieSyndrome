"""Independent identity helpers for Cycle #30 reference reconstruction."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


class IndependentIdentityError(ValueError):
    """Raised when identity reconstruction fails."""


def pair_key(home_id: str, away_id: str, start: str) -> tuple[str, str, str]:
    return (str(home_id), str(away_id), str(start))


def reject_duplicate_games(games: Sequence[Mapping[str, Any]]) -> None:
    seen: set[str] = set()
    for row in games:
        gid = str(row["canonical_game_id"])
        if gid in seen:
            raise IndependentIdentityError(f"duplicate canonical game {gid}")
        seen.add(gid)

"""Independent Cycle #33 reference. Must not import producer scientific helpers."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

EXPOSED_SEASONS = {2024, 2025}


class IndependentCycle33Error(ValueError):
    """Raised when independent reconstruction fails."""


def reject_duplicate_games(rows: Sequence[Mapping[str, Any]]) -> None:
    seen: set[str] = set()
    for row in rows:
        gid = str(row.get("canonical_game_id") or "")
        if not gid:
            raise IndependentCycle33Error("canonical game identity is required")
        if gid in seen:
            raise IndependentCycle33Error(f"duplicate canonical game {gid}")
        seen.add(gid)


def reject_fold(train_seasons: Sequence[int], eval_seasons: Sequence[int]) -> None:
    train = {int(s) for s in train_seasons}
    evaluate = {int(s) for s in eval_seasons}
    if train & evaluate:
        raise IndependentCycle33Error(
            f"train/evaluation season overlap: {sorted(train & evaluate)}"
        )
    if not train or not evaluate:
        raise IndependentCycle33Error("train and evaluation seasons are required")
    if max(train) >= min(evaluate):
        raise IndependentCycle33Error("evaluation must be strictly after training")
    exposed = sorted((train | evaluate) & EXPOSED_SEASONS)
    if exposed:
        raise IndependentCycle33Error(
            f"exposed seasons cannot be used for selection: {exposed}"
        )


def competing_finals(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    scores: dict[str, set[tuple[Any, Any]]] = {}
    for row in rows:
        cid = str(row.get("ncaa_contest_id") or "")
        if not cid:
            continue
        scores.setdefault(cid, set()).add(
            (row.get("home_points"), row.get("away_points"))
        )
    return [cid for cid, values in scores.items() if len(values) > 1]

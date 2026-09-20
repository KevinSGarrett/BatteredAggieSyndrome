"""Guards for unique-game fold integrity. Numerical agreement is not PIT proof."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

EXPOSED_SEASONS = {2024, 2025}


class FitIntegrityError(ValueError):
    """Raised when a caller partition cannot be admitted."""


def game_id(row: Mapping[str, Any]) -> str:
    return str(
        row.get("canonical_game_id")
        or row.get("ncaa_contest_id")
        or row.get("game_id")
        or ""
    )


def reject_unidentified_games(rows: Sequence[Mapping[str, Any]]) -> None:
    """MR33-09 repair: an empty/missing canonical game id must not be
    silently admitted -- previously only *duplicate* ids were rejected, so a
    population of entirely unidentified rows passed with no error at all."""

    missing = sum(1 for row in rows if not game_id(row))
    if missing:
        raise FitIntegrityError(
            f"{missing} row(s) have no canonical game id (checked "
            "canonical_game_id/ncaa_contest_id/game_id)"
        )


def reject_duplicate_games(rows: Sequence[Mapping[str, Any]]) -> None:
    seen: set[str] = set()
    for row in rows:
        gid = game_id(row)
        if not gid:
            continue
        if gid in seen:
            raise FitIntegrityError(f"duplicate canonical game {gid}")
        seen.add(gid)


def reject_season_overlap(
    train_seasons: Sequence[int], eval_seasons: Sequence[int]
) -> None:
    overlap = set(int(s) for s in train_seasons) & set(int(s) for s in eval_seasons)
    if overlap:
        raise FitIntegrityError(f"train/evaluation season overlap: {sorted(overlap)}")


def reject_invalid_chronological_bounds(
    train_seasons: Sequence[int], eval_seasons: Sequence[int]
) -> None:
    if not train_seasons or not eval_seasons:
        raise FitIntegrityError("train and evaluation seasons are required")
    if max(int(s) for s in train_seasons) >= min(int(s) for s in eval_seasons):
        raise FitIntegrityError(
            "evaluation seasons must be strictly after training seasons"
        )


def reject_exposed_selection_inputs(
    train_seasons: Sequence[int], eval_seasons: Sequence[int]
) -> None:
    used = set(int(s) for s in train_seasons) | set(int(s) for s in eval_seasons)
    exposed = sorted(used & EXPOSED_SEASONS)
    if exposed:
        raise FitIntegrityError(
            f"exposed 2024/2025 seasons cannot be used for selection: {exposed}"
        )


def validate_fit_population(
    rows: Sequence[Mapping[str, Any]],
    *,
    train_seasons: Sequence[int],
    eval_seasons: Sequence[int],
) -> dict[str, Any]:
    reject_unidentified_games(rows)
    reject_duplicate_games(rows)
    reject_season_overlap(train_seasons, eval_seasons)
    reject_invalid_chronological_bounds(train_seasons, eval_seasons)
    reject_exposed_selection_inputs(train_seasons, eval_seasons)
    return {
        "grain": "UNIQUE_GAME",
        "row_count": len(rows),
        "unique_games": len({game_id(row) for row in rows}),
        "train_seasons": list(train_seasons),
        "eval_seasons": list(eval_seasons),
        "proven_pit": 0,
        "classification": "UNTRUSTED_SHADOW",
    }

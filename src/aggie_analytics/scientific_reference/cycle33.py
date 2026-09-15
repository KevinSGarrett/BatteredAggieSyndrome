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


def reject_outer_hash_only_admission(
    original: Mapping[str, Any],
    mutated: Mapping[str, Any],
    *,
    original_outer_hash: str,
    mutated_outer_hash: str,
) -> None:
    """A recomputed outer hash cannot admit a mutated semantic payload."""

    if dict(original) != dict(mutated):
        raise IndependentCycle33Error(
            "semantic mutation cannot be admitted from a recomputed outer hash"
        )
    if original_outer_hash != mutated_outer_hash:
        raise IndependentCycle33Error("outer hash mismatch on unchanged payload")


def consumed_fields(
    row: Mapping[str, Any], *, design_matrix_fields: Sequence[str]
) -> list[str]:
    """A feature absent from the design matrix cannot count as consumed."""

    present = []
    for field in design_matrix_fields:
        if field in row and row.get(field) is not None:
            present.append(str(field))
    return present


def reject_report_count_mismatch(*, declared: int, actual: int) -> None:
    if int(declared) != int(actual):
        raise IndependentCycle33Error(
            f"report count mismatch: declared {declared} actual {actual}"
        )


def unique_game_population(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Independent unique-game census. Does not import producer fit helpers."""

    ids: list[str] = []
    seasons: set[int] = set()
    missing_id = 0
    for row in rows:
        gid = str(row.get("canonical_game_id") or "")
        if not gid:
            missing_id += 1
            continue
        ids.append(gid)
        if row.get("season") is not None:
            seasons.add(int(row["season"]))
    unique = set(ids)
    return {
        "row_count": len(rows),
        "unique_games": len(unique),
        "duplicate_rows": len(ids) - len(unique),
        "missing_identity_rows": missing_id,
        "seasons": sorted(seasons),
        "proven_pit": 0,
        "classification": "UNTRUSTED_SHADOW",
        "producer_helpers_imported": False,
    }

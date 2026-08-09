from __future__ import annotations

def classify_season(season: int) -> str:
    season=int(season)
    if season <= 2022:
        return "DEVELOPMENT"
    if season == 2023:
        return "DEVELOPMENT_SELECTION"
    if season in {2024,2025}:
        return "PROTECTED_TEST"
    if season >= 2026:
        return "FORWARD_SHADOW"
    raise ValueError("unsupported season")

def assert_same_canonical_game_split(seasons: list[int]) -> str:
    if not seasons:
        raise ValueError("at least one representation is required")
    splits={classify_season(s) for s in seasons}
    if len(splits)!=1:
        raise ValueError("representations of one canonical game crossed split boundaries")
    return next(iter(splits))

"""Independent market median, alias, and overround reconstruction."""

from __future__ import annotations

from typing import Sequence

SPORTSBOOK_ALIASES = {
    "draft kings": "draftkings",
    "draftkings": "draftkings",
    "draftking": "draftkings",
    "fan duel": "fanduel",
    "fanduel": "fanduel",
}
PARTICIPANT_ALIASES = {
    "missouri st.": "missouri state",
    "missouri st": "missouri state",
    "missouri state": "missouri state",
}
OVERROUND_LOW = 1.01
OVERROUND_HIGH = 1.12


def normalize_sportsbook(name: str) -> str:
    return SPORTSBOOK_ALIASES.get(name.strip().lower(), name.strip().lower())


def normalize_participant(name: str) -> str:
    key = " ".join(name.strip().lower().replace(".", " ").split())
    return PARTICIPANT_ALIASES.get(key, key)


def even_odd_median(values: Sequence[float]) -> float:
    ordered = sorted(float(item) for item in values)
    count = len(ordered)
    if count == 0:
        raise ValueError("empty median sample")
    midpoint = count // 2
    if count % 2 == 1:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2.0


def implied_probability(american_odds: int) -> float:
    if american_odds == 0:
        raise ValueError("american odds cannot be zero")
    if american_odds > 0:
        return 100.0 / (american_odds + 100.0)
    return (-american_odds) / ((-american_odds) + 100.0)


def overround(home_odds: int, away_odds: int) -> dict[str, float | bool | str]:
    home_implied = implied_probability(home_odds)
    away_implied = implied_probability(away_odds)
    total = home_implied + away_implied
    pathological = total < OVERROUND_LOW or total > OVERROUND_HIGH
    return {
        "home_implied": home_implied,
        "away_implied": away_implied,
        "overround": total,
        "pathological": pathological,
        "quarantine_reason": "PATHOLOGICAL_OVERROUND" if pathological else "",
    }


def reject_duplicate_quotes(
    quotes: Sequence[tuple[str, str, str, float]],
) -> list[tuple[str, str, str, float]]:
    """Keep unique (event, book, snapshot, quote_identity) tuples; reject duplicates."""
    seen: set[tuple[str, str, str]] = set()
    unique: list[tuple[str, str, str, float]] = []
    for event_id, book, snapshot_id, value in quotes:
        key = (event_id, normalize_sportsbook(book), snapshot_id)
        if key in seen:
            continue
        seen.add(key)
        unique.append((event_id, book, snapshot_id, value))
    return unique

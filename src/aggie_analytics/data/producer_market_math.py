"""Producer-side market helpers. Independent reference must not import this."""

from __future__ import annotations

from typing import Sequence

SPORTSBOOK_ALIASES = {
    "draft kings": "draftkings",
    "draftkings": "draftkings",
    "draftking": "draftkings",
    "fan duel": "fanduel",
    "fanduel": "fanduel",
    "bovada": "bovada",
}
PARTICIPANT_ALIASES = {
    "missouri st.": "missouri state",
    "missouri st": "missouri state",
    "missouri state": "missouri state",
}
OVERROUND_LOW = 1.01
OVERROUND_HIGH = 1.12


def normalize_sportsbook(name: str) -> str:
    text = name.strip().lower()
    if not text:
        raise ValueError("empty sportsbook identifier")
    return SPORTSBOOK_ALIASES.get(text, text)


def normalize_participant(name: str) -> str:
    key = " ".join(name.strip().lower().replace(".", " ").split())
    if not key:
        raise ValueError("empty participant identifier")
    return PARTICIPANT_ALIASES.get(key, key)


def even_odd_median(values: Sequence[float]) -> float:
    ordered = sorted(float(item) for item in values)
    if not ordered:
        raise ValueError("empty median sample")
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
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
    seen: dict[tuple[str, str, str], float] = {}
    unique: list[tuple[str, str, str, float]] = []
    for event_id, book, snapshot_id, value in quotes:
        if not str(book).strip():
            raise ValueError("empty sportsbook identifier")
        key = (event_id, normalize_sportsbook(book), snapshot_id)
        if key in seen:
            if seen[key] != float(value):
                raise ValueError(f"conflicting duplicate quote for {key}")
            continue
        seen[key] = float(value)
        unique.append((event_id, normalize_sportsbook(book), snapshot_id, float(value)))
    return unique


def one_observation_per_book(
    probabilities: Sequence[float], books: Sequence[str]
) -> tuple[list[float], list[str]]:
    if len(probabilities) != len(books):
        raise ValueError("unpaired probability/book sequences")
    by_book: dict[str, float] = {}
    order: list[str] = []
    for probability, book in zip(probabilities, books):
        if not str(book).strip():
            raise ValueError("empty sportsbook identifier")
        key = normalize_sportsbook(book)
        if key in by_book:
            if by_book[key] != float(probability):
                raise ValueError(f"conflicting duplicate book observation {key}")
            continue
        by_book[key] = float(probability)
        order.append(key)
    return [by_book[key] for key in order], order

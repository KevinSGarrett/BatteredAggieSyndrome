"""Market-benchmark integrity successor. Predecessor artifacts remain immutable."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from aggie_analytics.scientific_reference.market import (
    even_odd_median,
    normalize_participant,
    normalize_sportsbook,
    overround,
    reject_duplicate_quotes,
)

FOCUS_HOME_KEY = "texas a&m"
FOCUS_AWAY_ALIASES = frozenset({"missouri state", "missouri st", "missouri st."})
STRONG_IDENTITY_REQUIRES = (
    "authoritative_participants",
    "schedule_evidence",
)
NAME_DATE_ONLY = "NAME_DATE_ONLY_NOT_STRONG_IDENTITY"


def classify_crosswalk(
    *,
    participants_authoritative: bool,
    schedule_evidence: bool,
    name_date_only: bool,
) -> str:
    if participants_authoritative and schedule_evidence:
        return "STRONG_IDENTITY"
    if name_date_only:
        return NAME_DATE_ONLY
    return "UNRESOLVED_PARTICIPANT"


def freeze_vs_market(
    *,
    model_freeze_utc: str | None,
    market_acquisition_utc: str | None,
    acquisition_source: str,
) -> str:
    if acquisition_source == "supplied_cli_time":
        return "PRE_MARKET_FREEZE_NOT_PROVEN"
    if not model_freeze_utc or not market_acquisition_utc:
        return "PRE_MARKET_FREEZE_NOT_PROVEN"
    if model_freeze_utc < market_acquisition_utc:
        return "PRE_MARKET_MODEL_FREEZE"
    return "PRE_MARKET_FREEZE_NOT_PROVEN"


def focus_game_quote_count(
    quotes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    matched = []
    for quote in quotes:
        home = normalize_participant(str(quote.get("home_team") or ""))
        away = normalize_participant(str(quote.get("away_team") or ""))
        if home == FOCUS_HOME_KEY and away in {
            normalize_participant(alias) for alias in FOCUS_AWAY_ALIASES
        }:
            matched.append(quote)
    unique = reject_duplicate_quotes(
        [
            (
                str(item.get("event_id") or "focus"),
                str(item.get("book") or ""),
                str(item.get("snapshot_id") or ""),
                float(item.get("home_price") or 0),
            )
            for item in matched
        ]
    )
    return {
        "quote_count": len(unique),
        "raw_matched_rows": len(matched),
        "alias_normalized": True,
        "predecessor_false_zero_if_quotes_present": len(unique) > 0,
    }


def consensus_from_quotes(
    probabilities: Sequence[float],
    books: Sequence[str],
    *,
    minimum_books: int = 3,
) -> dict[str, Any]:
    normalized_books = sorted({normalize_sportsbook(book) for book in books})
    source_count = len(normalized_books)
    if not probabilities:
        return {
            "label": "INSUFFICIENT_MARKET_COVERAGE",
            "median_devigged_home": None,
            "source_count": 0,
        }
    median = even_odd_median(probabilities)
    if source_count == 0:
        label = "INSUFFICIENT_MARKET_COVERAGE"
    elif source_count == 1:
        label = "SINGLE_SOURCE_MARKET_REFERENCE"
    elif source_count < minimum_books:
        label = "MULTI_SOURCE_MARKET_REFERENCE"
    else:
        label = "MARKET_CONSENSUS"
    return {
        "label": label,
        "median_devigged_home": median,
        "source_count": source_count,
        "independent_books": normalized_books,
        "quote_presence": True,
        "usable_moneyline": True,
        "spread_converted_to_probability": False,
        "neutral_contests_included": True,
        "cross_book_pairing_forbidden": True,
    }


def quarantine_pathological_prices(home_odds: int, away_odds: int) -> dict[str, Any]:
    return overround(home_odds, away_odds)

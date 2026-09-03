"""Market-benchmark integrity successor. Predecessor artifacts remain immutable."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from aggie_analytics.data.producer_market_math import (
    even_odd_median,
    normalize_participant,
    normalize_sportsbook,
    one_observation_per_book,
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
    if name_date_only:
        return NAME_DATE_ONLY
    if participants_authoritative and schedule_evidence:
        return "STRONG_IDENTITY"
    return "UNRESOLVED_PARTICIPANT"


def _parse_aware_utc(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


ALLOWED_ACQUISITION_SOURCES = {
    "provider_retrieval_receipt",
    "official_source_receipt",
    "declared_api_route",
}


def freeze_vs_market(
    *,
    model_freeze_utc: str | None,
    market_acquisition_utc: str | None,
    acquisition_source: str,
) -> str:
    if acquisition_source not in ALLOWED_ACQUISITION_SOURCES:
        return "PRE_MARKET_FREEZE_NOT_PROVEN"
    if acquisition_source == "supplied_cli_time":
        return "PRE_MARKET_FREEZE_NOT_PROVEN"
    if not model_freeze_utc or not market_acquisition_utc:
        return "PRE_MARKET_FREEZE_NOT_PROVEN"
    freeze_at = _parse_aware_utc(model_freeze_utc)
    acquired_at = _parse_aware_utc(market_acquisition_utc)
    if freeze_at is None or acquired_at is None:
        return "PRE_MARKET_FREEZE_NOT_PROVEN"
    if freeze_at < acquired_at:
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
    insufficient = {
        "label": "INSUFFICIENT_MARKET_COVERAGE",
        "median_devigged_home": None,
        "source_count": 0,
        "independent_books": [],
        "quote_presence": False,
        "usable_moneyline": False,
        "spread_converted_to_probability": False,
        "neutral_contests_included": True,
        "cross_book_pairing_forbidden": True,
    }
    if len(probabilities) != len(books):
        insufficient["reject_reason"] = "UNPAIRED_PROBABILITY_BOOK_SEQUENCES"
        return insufficient
    if not probabilities:
        insufficient["reject_reason"] = "NO_QUOTES"
        return insufficient
    try:
        unique_probabilities, normalized_books = one_observation_per_book(
            probabilities, books
        )
    except ValueError as exc:
        insufficient["reject_reason"] = str(exc)
        return insufficient
    source_count = len(normalized_books)
    median = even_odd_median(unique_probabilities)
    if source_count == 0:
        insufficient["quote_presence"] = True
        insufficient["reject_reason"] = "NO_USABLE_BOOKS"
        return insufficient
    if source_count == 1:
        label = "SINGLE_SOURCE_MARKET_REFERENCE"
        usable = True
    elif source_count < minimum_books:
        label = "MULTI_SOURCE_MARKET_REFERENCE"
        usable = True
    else:
        label = "MARKET_CONSENSUS"
        usable = True
    return {
        "label": label,
        "median_devigged_home": median,
        "source_count": source_count,
        "independent_books": normalized_books,
        "quote_presence": True,
        "usable_moneyline": usable,
        "spread_converted_to_probability": False,
        "neutral_contests_included": True,
        "cross_book_pairing_forbidden": True,
    }


def quarantine_pathological_prices(home_odds: int, away_odds: int) -> dict[str, Any]:
    return overround(home_odds, away_odds)

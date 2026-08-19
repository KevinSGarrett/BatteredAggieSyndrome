"""Classify official SRC-014 HTML tables from observed header schema only."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash
from aggie_analytics.data.tamu_official_historical_boxscores import (
    CELL_RE,
    ROW_RE,
    TABLE_RE,
    AuthorityViolation,
    clean_text,
    decode_page,
)


PARSER_IDENTITY = "tamu.official.html.table.classifier.v1"
TEAM_STATISTICS = "team_statistics"
PLAYER_STATISTICS = "individual_player_statistics"
SCORING_SUMMARY = "scoring_summary"
DRIVES = "drives"
PLAY_BY_PLAY = "play_by_play"
PARTICIPATION = "participation"
HEADING = "heading"
UNKNOWN = "unknown"
DOMAIN_LABELS = (
    TEAM_STATISTICS,
    PLAYER_STATISTICS,
    SCORING_SUMMARY,
    DRIVES,
    PLAY_BY_PLAY,
    PARTICIPATION,
)
PLAYER_STAT_LEADERS = {
    "rushing",
    "passing",
    "receiving",
    "punting",
    "kickoffs",
    "all purpose",
    "field goal attempts",
}
HEADING_TITLES = {
    "scoring summary",
    "team statistics",
    "individual statistics",
    "drive chart",
    "defensive statistics",
    "game participation",
    "participation report",
    "box score",
    "play-by-play summary",
    "play-by-play",
}
NAV_MARKERS = (
    "scoring summary",
    "team statistics",
    "individual statistics",
    "drive chart",
    "play-by-play",
)


def header_fingerprint(headers: list[str]) -> str:
    return hashlib.sha256(
        json.dumps(headers, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _norm(headers: list[str]) -> list[str]:
    return [re.sub(r"\s+", " ", item.casefold().strip(" .:-")) for item in headers]


def classify_headers(headers: list[str]) -> str:
    labels = [item for item in _norm(headers) if item]
    matches: list[str] = []
    if not labels:
        return UNKNOWN
    joined = " ".join(labels)
    if len(labels) == 1 and labels[0] in HEADING_TITLES:
        return HEADING
    if sum(1 for marker in NAV_MARKERS if marker in labels[0]) >= 3:
        return HEADING
    if labels[0] == "team totals" and len(labels) >= 3:
        matches.append(TEAM_STATISTICS)
    if labels[0] in PLAYER_STAT_LEADERS:
        matches.append(PLAYER_STATISTICS)
    if {"punts", "kickoffs", "intercept"} <= set(labels):
        matches.append(PLAYER_STATISTICS)
    if labels[0] == "##" and {"solo", "ast", "total"} <= set(labels):
        matches.append(PLAYER_STATISTICS)
    if labels[0] == "score by quarters" and {"1", "2", "3", "4"} <= set(labels):
        matches.append(SCORING_SUMMARY)
    if labels[0] == "scoring summary":
        matches.append(SCORING_SUMMARY)
    if "drive started" in labels and "drive ended" in labels:
        matches.append(DRIVES)
    play_tokens = {"quarter", "down", "play", "yds to go", "spot"}
    if play_tokens <= set(labels) or (labels[0] == "play-by-play summary" and len(labels) > 1):
        matches.append(PLAY_BY_PLAY)
    if labels[0] in {"participation report", "game participation", "player participation"}:
        matches.append(PARTICIPATION)
    if (
        len(labels) == 1
        and labels[0] not in HEADING_TITLES
        and ("texas" in labels[0] or "montana" in labels[0] or "a&m" in labels[0] or "tamu" in labels[0])
        and "fumbles:" not in labels[0]
        and "kickoff time" not in labels[0]
        and "score by quarters" not in labels[0]
    ):
        matches.append(PARTICIPATION)
    unique = list(dict.fromkeys(matches))
    if len(unique) > 1:
        return UNKNOWN
    if unique:
        return unique[0]
    if "kickoff time" in joined or joined.startswith("fumbles:"):
        return UNKNOWN
    return UNKNOWN


def extract_tables(body: bytes) -> list[dict[str, Any]]:
    text = decode_page(body)
    tables: list[dict[str, Any]] = []
    for table_index, raw_table in enumerate(TABLE_RE.findall(text)):
        raw_rows = ROW_RE.findall(raw_table)
        rows = [[clean_text(cell) for cell in CELL_RE.findall(raw_row)] for raw_row in raw_rows]
        headers = [cell for cell in (rows[0] if rows else [])]
        classification = classify_headers(headers)
        tables.append(
            {
                "table_index": table_index,
                "header_fingerprint": header_fingerprint(headers),
                "headers": headers,
                "classification": classification,
                "row_count": len(rows),
                "rows": [
                    {"row_order": row_index, "cells": cells}
                    for row_index, cells in enumerate(rows)
                ],
            }
        )
    return tables


def classify_page(
    body: bytes,
    *,
    url: str,
    raw_sha256: str,
    source_season: int,
) -> dict[str, Any]:
    tables = extract_tables(body)
    classified_rows: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    seen_fingerprints: dict[str, str] = {}
    for table in tables:
        fingerprint = table["header_fingerprint"]
        prior = seen_fingerprints.get(fingerprint)
        if prior and prior != table["classification"] and table["classification"] not in {HEADING, UNKNOWN}:
            conflicts.append(
                {
                    "header_fingerprint": fingerprint,
                    "first_classification": prior,
                    "second_classification": table["classification"],
                }
            )
            table["classification"] = UNKNOWN
        seen_fingerprints[fingerprint] = table["classification"]
        for row in table["rows"]:
            classified_rows.append(
                {
                    "source_url": url,
                    "source_sha256": raw_sha256,
                    "source_season": source_season,
                    "table_index": table["table_index"],
                    "header_fingerprint": fingerprint,
                    "row_order": row["row_order"],
                    "cells": row["cells"],
                    "classification": table["classification"],
                    "parser_identity": PARSER_IDENTITY,
                    "availability": "NOT_ESTABLISHED",
                }
            )
    if conflicts:
        raise AuthorityViolation("conflicting HTML-table header fingerprints")
    coverage = {}
    for domain in DOMAIN_LABELS:
        reconstructible = [
            row
            for row in classified_rows
            if row["classification"] == domain and any(cell for cell in row["cells"])
        ]
        coverage[domain] = "PRESENT" if reconstructible else "ABSENT"
    if coverage[PLAY_BY_PLAY] == "PRESENT" and all(
        table["classification"] != PLAY_BY_PLAY or not table["headers"] or not any(table["headers"])
        for table in tables
    ):
        coverage[PLAY_BY_PLAY] = "ABSENT"
    return {
        "url": url,
        "source_sha256": raw_sha256,
        "source_season": source_season,
        "parser_identity": PARSER_IDENTITY,
        "table_count": len(tables),
        "classified_row_count": len(classified_rows),
        "unknown_table_count": sum(1 for table in tables if table["classification"] == UNKNOWN),
        "heading_table_count": sum(1 for table in tables if table["classification"] == HEADING),
        "tables": tables,
        "classified_rows": classified_rows,
        "domain_coverage": coverage,
        "rows_identity": stable_hash(classified_rows),
        "availability_claim": False,
        "participation_as_availability": False,
    }


def compact_classification(page: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "url": page["url"],
        "source_sha256": page["source_sha256"],
        "source_season": page["source_season"],
        "parser_identity": page["parser_identity"],
        "table_count": page["table_count"],
        "classified_row_count": page["classified_row_count"],
        "unknown_table_count": page["unknown_table_count"],
        "heading_table_count": page["heading_table_count"],
        "domain_coverage": page["domain_coverage"],
        "rows_identity": page["rows_identity"],
        "availability_claim": False,
    }

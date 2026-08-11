from __future__ import annotations

"""Deterministic extraction helpers for timestamped SEC availability evidence."""

import hashlib
import html
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any


ALLOWED_STATUSES = {
    "OUT",
    "DOUBTFUL",
    "QUESTIONABLE",
    "PROBABLE",
    "AVAILABLE",
    "GAME_TIME_DECISION",
}


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def stable_hash(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def normalize_player_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", normalize_space(value))
    return normalized.replace("’", "'").replace("`", "'")


def normalize_status(value: str) -> str:
    normalized = re.sub(r"[^A-Z0-9]+", "_", normalize_space(value).upper()).strip("_")
    aliases = {
        "GAMETIME_DECISION": "GAME_TIME_DECISION",
        "GAME_TIME": "GAME_TIME_DECISION",
    }
    return aliases.get(normalized, normalized)


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include an offset")
    return parsed.astimezone(timezone.utc)


@dataclass
class ParsedTable:
    label: str
    headers: list[str]
    rows: list[list[str]]
    ordinal: int


@dataclass
class ParsedArticle:
    headline: str | None
    date_published: str | None
    tables: list[ParsedTable] = field(default_factory=list)


class _ArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.labels: list[str] = []
        self.tables: list[ParsedTable] = []
        self._label_tag: str | None = None
        self._label_parts: list[str] = []
        self._table_depth = 0
        self._in_row = False
        self._cell_tag: str | None = None
        self._cell_parts: list[str] = []
        self._row_tags: list[str] = []
        self._row_cells: list[str] = []
        self._table_rows: list[tuple[list[str], list[str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        tag = tag.lower()
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6", "b", "strong"} and self._table_depth == 0:
            self._label_tag = tag
            self._label_parts = []
        elif tag == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._table_rows = []
        elif self._table_depth and tag == "tr":
            self._in_row = True
            self._row_tags = []
            self._row_cells = []
        elif self._table_depth and self._in_row and tag in {"th", "td"}:
            self._cell_tag = tag
            self._cell_parts = []

    def handle_data(self, data: str) -> None:
        if self._cell_tag:
            self._cell_parts.append(data)
        elif self._label_tag:
            self._label_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._cell_tag == tag:
            value = normalize_space("".join(self._cell_parts))
            self._row_tags.append(self._cell_tag)
            self._row_cells.append(value)
            self._cell_tag = None
            self._cell_parts = []
        elif tag == "tr" and self._table_depth and self._in_row:
            if self._row_cells:
                self._table_rows.append((list(self._row_tags), list(self._row_cells)))
            self._in_row = False
            self._row_tags = []
            self._row_cells = []
        elif tag == "table" and self._table_depth:
            self._table_depth -= 1
            if self._table_depth == 0:
                headers: list[str] = []
                rows: list[list[str]] = []
                for tags, values in self._table_rows:
                    if all(cell_tag == "th" for cell_tag in tags) and not headers:
                        headers = values
                    else:
                        rows.append(values)
                self.tables.append(
                    ParsedTable(
                        label=self.labels[-1] if self.labels else "",
                        headers=headers,
                        rows=rows,
                        ordinal=len(self.tables) + 1,
                    )
                )
                self._table_rows = []
        elif self._label_tag == tag:
            label = normalize_space("".join(self._label_parts))
            if label:
                self.labels.append(label)
            self._label_tag = None
            self._label_parts = []


def _walk_json(value: Any):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk_json(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json(item)


def _extract_json_ld(document: str) -> tuple[str | None, str | None]:
    script_re = re.compile(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        re.IGNORECASE | re.DOTALL,
    )
    for match in script_re.finditer(document):
        try:
            payload = json.loads(html.unescape(match.group(1)).strip())
        except (json.JSONDecodeError, TypeError):
            continue
        for node in _walk_json(payload):
            published = node.get("datePublished")
            headline = node.get("headline") or node.get("name")
            if isinstance(published, str):
                return (headline if isinstance(headline, str) else None, published)
    return None, None


def parse_article(document: str) -> ParsedArticle:
    headline, date_published = _extract_json_ld(document)
    parser = _ArticleParser()
    parser.feed(document)
    parser.close()
    return ParsedArticle(headline=headline, date_published=date_published, tables=parser.tables)


def _split_embedded_position(value: str) -> tuple[str, str | None]:
    match = re.match(r"^([A-Za-z][A-Za-z0-9/-]{0,6})\s+(.+)$", normalize_space(value))
    if not match:
        return value, None
    return match.group(2), match.group(1).upper()


def extract_candidate_rows(
    *,
    document: str,
    source: dict[str, Any],
    capture_sha256: str,
    captured_at_utc: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    article = parse_article(document)
    quarantine: list[dict[str, Any]] = []
    if not article.date_published:
        quarantine.append({"reason": "PUBLICATION_TIME_MISSING", "source_record_id": source["source_record_id"]})
        return [], quarantine, {"headline": article.headline, "date_published": None, "tables_seen": len(article.tables)}
    try:
        published = parse_utc(article.date_published)
    except ValueError:
        quarantine.append(
            {
                "reason": "PUBLICATION_TIME_INVALID",
                "source_record_id": source["source_record_id"],
                "raw_value": article.date_published,
            }
        )
        return [], quarantine, {"headline": article.headline, "date_published": article.date_published, "tables_seen": len(article.tables)}

    expected_label = normalize_space(source["table_heading_contains"]).casefold()
    matches = [table for table in article.tables if expected_label in table.label.casefold()]
    if len(matches) != 1:
        quarantine.append(
            {
                "reason": "EXPECTED_TABLE_MATCH_COUNT_NOT_ONE",
                "source_record_id": source["source_record_id"],
                "expected_label": source["table_heading_contains"],
                "match_count": len(matches),
                "observed_labels": [table.label for table in article.tables],
            }
        )
        return [], quarantine, {"headline": article.headline, "date_published": article.date_published, "tables_seen": len(article.tables)}

    table = matches[0]
    normalized_headers = [normalize_space(value).casefold() for value in table.headers]
    normalized_headers = ["player" if value == "name" else value for value in normalized_headers]
    if normalized_headers not in (["player", "position", "status"], ["player", "status"]):
        quarantine.append(
            {
                "reason": "TABLE_SCHEMA_UNSUPPORTED",
                "source_record_id": source["source_record_id"],
                "headers": table.headers,
            }
        )
        return [], quarantine, {"headline": article.headline, "date_published": article.date_published, "tables_seen": len(article.tables)}

    target_boundary = datetime.fromisoformat(source["target_game_date"]).replace(tzinfo=timezone.utc)
    chronology_pass = published < target_boundary
    rows: list[dict[str, Any]] = []
    for row_number, cells in enumerate(table.rows, start=1):
        if len(cells) != len(normalized_headers):
            quarantine.append(
                {
                    "reason": "ROW_WIDTH_MISMATCH",
                    "source_record_id": source["source_record_id"],
                    "table_ordinal": table.ordinal,
                    "row_number": row_number,
                    "cells": cells,
                }
            )
            continue
        values = dict(zip(normalized_headers, cells, strict=True))
        player_raw = values["player"]
        position = values.get("position")
        if source.get("position_embedded_in_player"):
            player_raw, embedded_position = _split_embedded_position(player_raw)
            position = position or embedded_position
        player_normalized = normalize_player_name(player_raw)
        status = normalize_status(values["status"])
        if not player_normalized or status not in ALLOWED_STATUSES:
            quarantine.append(
                {
                    "reason": "ROW_VALUE_INVALID",
                    "source_record_id": source["source_record_id"],
                    "table_ordinal": table.ordinal,
                    "row_number": row_number,
                    "player_raw": player_raw,
                    "status_raw": values["status"],
                }
            )
            continue
        evidence_identity = {
            "source_record_id": source["source_record_id"],
            "source_capture_sha256": capture_sha256,
            "report_version": source["report_version"],
            "table_ordinal": table.ordinal,
            "row_number": row_number,
            "player_normalized": player_normalized,
            "status": status,
        }
        rows.append(
            {
                "availability_candidate_id": "avc_" + stable_hash(evidence_identity)[:24],
                "source_record_id": source["source_record_id"],
                "source_class": source["source_class"],
                "source_url": source["url"],
                "source_capture_sha256": capture_sha256,
                "source_capture_at_utc": captured_at_utc,
                "source_publication_time_utc": published.isoformat().replace("+00:00", "Z"),
                "season": int(source["season"]),
                "game_label": source["game_label"],
                "target_game_date": source["target_game_date"],
                "report_version": source["report_version"],
                "player_name_raw": normalize_space(player_raw),
                "player_name_normalized": player_normalized,
                "position_raw": normalize_space(position or "") or None,
                "status": status,
                "evidence_locator": {
                    "table_label": table.label,
                    "table_ordinal": table.ordinal,
                    "row_number": row_number,
                },
                "historical_known_at_candidate": chronology_pass,
                "historical_known_at_basis": "SOURCE_PUBLICATION_TIME",
                "chronology_rule": "PUBLICATION_BEFORE_UTC_START_OF_TARGET_GAME_DATE",
                "chronology_pass": chronology_pass,
                "canonical_player_id": None,
                "player_identity_state": "SOURCE_SCOPED_NAME_ONLY_UNRESOLVED",
                "authority": "LOWER_AUTHORITY_CANDIDATE_EVIDENCE",
                "canonical_admission": False,
                "pit_state_admission": False,
                "training_feature_admission": False,
                "protected_evaluation_admission": False,
                "absence_means_available": False,
            }
        )
    return rows, quarantine, {
        "headline": article.headline,
        "date_published": published.isoformat().replace("+00:00", "Z"),
        "tables_seen": len(article.tables),
        "matched_table_label": table.label,
        "matched_table_ordinal": table.ordinal,
    }

"""Shared immutable parser for legacy 1996/1997 official box-score game identity."""

from __future__ import annotations

import re
from datetime import date
from html import unescape
from urllib.parse import urlsplit
from typing import Any

from aggie_analytics.data.ncaa_contest_reconciliation import normalize_team_name
from aggie_analytics.data.tamu_official_historical_archive import fragment_text, validate_official_url
from aggie_analytics.data.tamu_official_historical_boxscores import (
    AuthorityViolation,
    DATE_RE,
    SEASON_RE,
    clean_text,
    decode_page,
    is_tamu_name,
    opponent_candidate,
    parse_quarter_scores,
    sha256_bytes,
    site_token,
    strip_rank_prefix,
)

LEGACY_H2_PARSER_VERSION = "tamu.official.legacy_h2.v1"
_H2_TAG_RE = re.compile(r"(?is)<h2\b[^>]*>(.*?)</h2>")
_PRE_HEADER_RE = re.compile(
    r"(?i)(?:#\d+\s+)?([A-Za-z0-9 .&';/-]+?)\s+vs\.?\s+(?:#\d+\s+)?([A-Za-z0-9 .&';/-]+?)"
    r"\s+\(([A-Za-z]{3,9}\.?\s+\d{1,2},?\s*\d{4})(?:\s+at\s+([^)]+))?\)"
)
_H2_HEADER_RE = re.compile(
    r"^(?P<weekday>[A-Za-z]+),\s*(?P<month>[A-Za-z]+)\s+(?P<day>\d{1,2}),\s*(?P<year>\d{4})\s*:\s*"
    r"(?P<team1>.+?)\s+(?P<score1>\d+)\s*,\s*(?P<team2>.+?)\s+(?P<score2>\d+)\s*$"
)
_SITE_RE = re.compile(r"Site:\s*([^<\n]+?)(?:Stadium:|Attendance:|$)", re.IGNORECASE)
_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def _normalize_team(value: str) -> str:
    return strip_rank_prefix(value).strip(" .,:;")


def _month_number(raw: str) -> int:
    token = re.sub(r"[^A-Za-z]", "", raw).lower()
    month = _MONTHS.get(token)
    if month is None:
        raise AuthorityViolation(f"legacy header month is unparseable: {raw}")
    return month


def _season_for_date(raw_date: date, source_season: int) -> int:
    if raw_date.year == source_season:
        return source_season
    if raw_date.month == 1 and raw_date.year == source_season + 1:
        return source_season
    raise AuthorityViolation(
        f"calendar-year/season mismatch for legacy page: parsed={raw_date.isoformat()} source_season={source_season}"
    )


def _parse_h2_identity(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in _H2_TAG_RE.findall(text):
        normalized = fragment_text(re.sub(r"(?is)<br\s*/?>", " ", raw)).replace("\xa0", " ")
        normalized = re.sub(r"\s+", " ", normalized).strip()
        match = _H2_HEADER_RE.match(normalized)
        if match is None:
            continue
        parsed_date = date(
            int(match.group("year")),
            _month_number(match.group("month")),
            int(match.group("day")),
        )
        rows.append(
            {
                "raw_date": parsed_date.strftime("%b %d, %Y"),
                "calendar_date": parsed_date.isoformat(),
                "visitor_name": _normalize_team(match.group("team1")),
                "home_name": _normalize_team(match.group("team2")),
                "visitor_points": int(match.group("score1")),
                "home_points": int(match.group("score2")),
                "team_scores": {
                    _normalize_team(match.group("team1")): int(match.group("score1")),
                    _normalize_team(match.group("team2")): int(match.group("score2")),
                },
                "source": "h2",
            }
        )
    return rows


def _parse_pre_identity(text: str) -> dict[str, Any]:
    head = _PRE_HEADER_RE.search(text)
    date_match = DATE_RE.search(text)
    if head is None:
        raise AuthorityViolation("legacy page missing HEAD identity block")
    visitor_name = _normalize_team(head.group(1))
    home_name = _normalize_team(head.group(2))
    raw_date = re.sub(r",(?=\d)", ", ", clean_text(head.group(3)))
    if date_match is not None:
        raw_date = clean_text(date_match.group(1))
    scores = parse_quarter_scores(text)
    visitor_score = next(
        (item for item in scores if normalize_team_name(strip_rank_prefix(item["team_raw"])) == normalize_team_name(visitor_name)),
        None,
    )
    home_score = next(
        (item for item in scores if normalize_team_name(strip_rank_prefix(item["team_raw"])) == normalize_team_name(home_name)),
        None,
    )
    if visitor_score is None or home_score is None:
        raise AuthorityViolation("legacy page score rows do not bind visitor/home labels")
    month_day_year = re.match(r"([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})$", raw_date)
    if month_day_year is None:
        raise AuthorityViolation(f"legacy page date is unparseable: {raw_date}")
    parsed_date = date(int(month_day_year.group(3)), _month_number(month_day_year.group(1)), int(month_day_year.group(2)))
    return {
        "raw_date": raw_date,
        "calendar_date": parsed_date.isoformat(),
        "visitor_name": visitor_name,
        "home_name": home_name,
        "visitor_points": int(visitor_score["points"]),
        "home_points": int(home_score["points"]),
        "team_scores": {
            visitor_name: int(visitor_score["points"]),
            home_name: int(home_score["points"]),
        },
        "site": clean_text(head.group(4) or ""),
        "source": "pre",
    }


def _resolve_single_identity(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not candidates:
        raise AuthorityViolation("legacy box page missing game identity metadata")
    by_fingerprint: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in candidates:
        team_scores = dict(item.get("team_scores") or {})
        tamu_scores = [int(points) for name, points in team_scores.items() if is_tamu_name(str(name))]
        opponent_scores = [int(points) for name, points in team_scores.items() if not is_tamu_name(str(name))]
        if len(tamu_scores) != 1 or len(opponent_scores) != 1:
            raise AuthorityViolation("legacy identity candidates are missing Texas A&M or opponent scores")
        fingerprint = (
            item["calendar_date"],
            tamu_scores[0],
            opponent_scores[0],
        )
        if fingerprint in by_fingerprint:
            if item.get("source") == "pre":
                by_fingerprint[fingerprint] = item
            elif not by_fingerprint[fingerprint].get("site") and item.get("site"):
                by_fingerprint[fingerprint] = item
            continue
        by_fingerprint[fingerprint] = item
    if len(by_fingerprint) > 1:
        raise AuthorityViolation("legacy box page has multiple incompatible game identity headers")
    return next(iter(by_fingerprint.values()))


def parse_legacy_game_identity(
    *,
    body: bytes,
    url: str,
    source_season: int,
    source_order: int,
    raw_sha256: str,
    raw_file_sha256: str,
    allowed_urls: frozenset[str],
    official_index_url: str,
    parent_url: str,
) -> dict[str, Any]:
    official_url = validate_official_url(url)
    official_index = validate_official_url(official_index_url)
    parent = validate_official_url(parent_url)
    if official_url not in allowed_urls:
        raise AuthorityViolation(f"box URL was not emitted by the official season index: {official_url}")
    if parent != official_index:
        raise AuthorityViolation("substituted parent URL in legacy capture")
    body_sha = sha256_bytes(body)
    if body_sha != raw_sha256 or raw_file_sha256 != raw_sha256:
        raise AuthorityViolation("legacy raw SHA mismatch")
    text = decode_page(body)
    if "texas a&m" not in text.lower() and "texas a&amp;m" not in text.lower():
        raise AuthorityViolation("missing Texas A&M team identity")

    candidates = _parse_h2_identity(text)
    pre_candidate: dict[str, Any] | None = None
    try:
        pre_candidate = _parse_pre_identity(text)
    except AuthorityViolation:
        pre_candidate = None
    if not candidates:
        if pre_candidate is None:
            raise AuthorityViolation("legacy box page missing game identity metadata")
        candidates.append(pre_candidate)
    elif pre_candidate is not None:
        candidates.append(pre_candidate)
    identity = _resolve_single_identity(candidates)
    parsed_date = date.fromisoformat(identity["calendar_date"])
    football_season = _season_for_date(parsed_date, source_season)
    season_header = SEASON_RE.search(text)
    if season_header is not None and int(season_header.group(1)) not in {source_season, source_season + 1}:
        raise AuthorityViolation("legacy season header conflicts with expected season")
    visitor_name = str(identity["visitor_name"])
    home_name = str(identity["home_name"])
    if is_tamu_name(visitor_name):
        tamu_side = "visitor"
        opponent = opponent_candidate(home_name)
    elif is_tamu_name(home_name):
        tamu_side = "home"
        opponent = opponent_candidate(visitor_name)
    else:
        raise AuthorityViolation("missing Texas A&M identity in legacy game header")

    site = clean_text(identity.get("site") or "")
    if not site:
        site_match = _SITE_RE.search(text)
        if site_match is not None:
            site = clean_text(unescape(site_match.group(1)))
    tamu_points = int(identity["visitor_points"]) if tamu_side == "visitor" else int(identity["home_points"])
    opponent_points = int(identity["home_points"]) if tamu_side == "visitor" else int(identity["visitor_points"])
    if tamu_points < 0 or opponent_points < 0:
        raise AuthorityViolation("ambiguous scores in legacy game header")
    return {
        "parser_identity": LEGACY_H2_PARSER_VERSION,
        "source": str(identity.get("source") or "unknown"),
        "official_season_index_url": official_index,
        "emitted_box_href": urlsplit(official_url).path,
        "resolved_official_url": official_url,
        "source_order": int(source_order),
        "raw_sha256": raw_sha256,
        "raw_file_sha256": raw_file_sha256,
        "football_season": football_season,
        "calendar_date": identity["calendar_date"],
        "raw_date": identity["raw_date"],
        "visitor_name": visitor_name,
        "home_name": home_name,
        "tamu_side": tamu_side,
        "opponent_candidate": opponent,
        "opponent_normalized": normalize_team_name(opponent),
        "tamu_points": tamu_points,
        "opponent_points": opponent_points,
        "visitor_points": int(identity["visitor_points"]),
        "home_points": int(identity["home_points"]),
        "site": site,
        "site_token": site_token(site),
        "raw_game_label": f"{visitor_name} vs {home_name} ({identity['raw_date']} at {site or 'UNKNOWN'})",
    }

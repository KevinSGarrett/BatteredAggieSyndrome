"""Normalize official Texas A&M 2010-2011 box scores as SRC-014 school evidence."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urljoin, urlsplit

from aggie_analytics.data.ncaa_contest_reconciliation import normalize_team_name, stable_hash
from aggie_analytics.data.tamu_official_historical_archive import (
    BOX_PATH_RE,
    PINNED_BOX_URLS_IDENTITY,
    fragment_text,
    load_json,
    season_from_archive_folder,
    sha256_file,
    validate_official_url,
    write_json,
)


SCHEMA_VERSION = "aggie.data.tamu_official_historical_boxscores.v1"
PARSER_VERSION = "tamu.official.historical.boxscore.v1"
CONTRACT_RELATIVE = "configs/tamu_official_historical_boxscore_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_historical_boxscore_gate.json"
ARCHIVE_GATE_RELATIVE = "artifacts/data_lake/tamu_official_historical_archive_gate.json"
EVIDENCE_RELATIVE = "artifacts/jira_evidence/POST-TASK-CYCLE-9-OFFICIAL-BOXSCORE-NORMALIZATION-001.json"
CONTRACT_ID = "BAT-580-TAMU-OFFICIAL-HISTORICAL-BOXSCORES-V1"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_2010_2011_OFFICIAL_SCHOOL_BOXSCORE_CANDIDATE_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
WMT_ACQUISITION_IDENTITY = "d227b6cfca71ad0e6d514fa707f7d23a4a6a59374142352a016202c3bd2f25b3"
WMT_DATASET_IDENTITY = "76c3b366431d5085588d07df7d8db77348ac737dc57538befe26c7080150f010"
ARCHIVE_ACQUISITION_IDENTITY = "535e278e4c0a9a9abbd2fac8e6e44f74eb8cbe0ba4cd26ff9692ae9b622280be"
RAW_ROOT = "raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive"
PINNED_GAMES_IDENTITY = "4b07b23cd0e4bef16d4a8eb7bf67d0f0d20f7d9f7ab94116fdee57239910d0e5"
PINNED_COVERAGE_IDENTITY = "b2b8f61a2f768d90268c42180a909fb9101787feb4cacfefa5205c1533588c09"
PINNED_COUNTS: dict[str, int] = {
    "captured_pages_2010": 13,
    "captured_pages_2011": 13,
    "captured_pages_total": 26,
    "date_conflicts": 1,
    "matched_strong_tuple": 25,
    "missing_pages_2010": 0,
    "missing_pages_2011": 0,
    "ncaa_contest_ids_created": 0,
    "normalized_rows": 3403,
    "participation_candidates": 1302,
    "player_stat_candidates": 617,
    "target_games_2010": 13,
    "target_games_2011": 13,
    "target_games_total": 26,
}
MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
DOMAINS = (
    "game_identity_metadata",
    "season",
    "played_date",
    "teams",
    "scores",
    "quarter_scoring",
    "site_venue",
    "attendance",
    "kickoff_time",
    "end_time",
    "duration",
    "weather",
    "officials",
    "team_statistics",
    "individual_player_statistics",
    "scoring_summary",
    "drives",
    "play_by_play",
    "participation",
    "starters",
    "penalties",
    "turnovers",
)
TABLE_RE = re.compile(r"(?is)<table\b[^>]*>(.*?)</table>")
ROW_RE = re.compile(r"(?is)<tr\b[^>]*>(.*?)</tr>")
CELL_RE = re.compile(r"(?is)<t[hd]\b[^>]*>(.*?)</t[hd]>")
SEASON_RE = re.compile(r"(\d{4})\s+Texas A&(?:amp;)?M Football", re.IGNORECASE)
DATE_RE = re.compile(r"Date:\s*([A-Za-z]{3}\s+\d{1,2},\s+\d{4})", re.IGNORECASE)
HEAD_RE = re.compile(
    r"(?:#\d+\s+)?([A-Za-z0-9 .&';-]+?)\s+vs\.?\s+(?:#\d+\s+)?([A-Za-z0-9 .&';-]+?)\s+\(([A-Za-z]{3}\s+\d{1,2},\s+\d{4})(?:\s+at\s+([^)]+))?\)",
    re.IGNORECASE,
)
SITE_RE = re.compile(r"Site:\s*([^<\n]+?)(?:Stadium:|Attendance:|$)", re.IGNORECASE)
STAD_RE = re.compile(r"Stadium:\s*([^<\n]+?)(?:Attendance:|$)", re.IGNORECASE)
ATT_RE = re.compile(r"Attendance:\s*([0-9,]+)", re.IGNORECASE)
KICK_RE = re.compile(r"Kickoff time:\s*([^<\n]+?)(?:End of Game:|$)", re.IGNORECASE)
END_RE = re.compile(r"End of Game:\s*([^<\n]+?)(?:Total elapsed|$)", re.IGNORECASE)
DUR_RE = re.compile(r"Total elapsed time:\s*([0-9:]+)", re.IGNORECASE)
TEMP_RE = re.compile(r"Temperature:\s*([^<\n]+?)(?:Wind:|Weather:|$)", re.IGNORECASE)
WIND_RE = re.compile(r"Wind:\s*([^<\n]+?)(?:Weather:|$)", re.IGNORECASE)
WEATH_RE = re.compile(r"Weather:\s*([^\n<]+)", re.IGNORECASE)
INDEX_RESULT_RE = re.compile(r"([WLT]),\s*(\d+)-(\d+)", re.IGNORECASE)
INDEX_DATE_RE = re.compile(r"\b([A-Za-z]{3})\s+(\d{1,2})\b")
SCORE_PLAY_RE = re.compile(
    r"(?:(1st|2nd|3rd|4th|OT)\s+)?(\d{1,2}:\d{2})\s+([A-Z]+)\s+-\s+(.+)",
    re.IGNORECASE,
)
STARTER_RE = re.compile(r"^([A-Z0-9]{1,4})\s+(\d+[A-Z]?)\s+(.+)$")
PART_RE = re.compile(r"(\d+[A-Z]?)-([A-Za-z][A-Za-z .'-]+)")
PLAYER_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'-]+$")
GATE_IDENTITY_FIELDS = (
    "schema_version",
    "artifact_type",
    "result",
    "classification",
    "contract_id",
    "decision_unit",
    "jira_key",
    "disposition",
    "source_id",
    "parser_version",
    "counts",
    "domain_coverage",
    "games",
    "admissions",
    "authority",
    "scientific_nonclaims",
    "protected_lane",
    "upstream_identities",
)


class AuthorityViolation(ValueError):
    """Raised when official-school box-score evidence is asked to invent identity or authority."""


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def decode_page(body: bytes) -> str:
    return body.decode("latin-1", errors="replace")


def clean_text(value: str) -> str:
    text = fragment_text(value).replace("\xa0", " ").replace("•", " ")
    text = re.sub(r"[^\w\s,.:#'&/-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip(" \t:-")


def is_tamu_name(value: str) -> bool:
    normalized = normalize_team_name(value)
    return normalized in {"texas a and m", "texas am", "tamu"} or normalized.startswith("texas a and m")


def strip_rank_prefix(value: str) -> str:
    return re.sub(r"^#?\d+\s+", "", clean_text(value)).strip()


def opponent_candidate(value: str) -> str:
    cleaned = re.sub(r"^[*!%]+", "", clean_text(value))
    cleaned = re.sub(r"^(vs\.?|at)\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\(?#?\d+\)\s*", "", cleaned)
    cleaned = re.sub(r"^#?\d+\s+", "", cleaned)
    return cleaned.strip(" .")


def site_token(value: str) -> str:
    token = clean_text(value).split(",")[0].lower()
    return re.sub(r"[^a-z0-9]+", " ", token).strip()


def parse_statcrew_date(raw: str) -> str:
    match = re.match(r"([A-Za-z]{3})\s+(\d{1,2}),\s+(\d{4})$", clean_text(raw))
    if match is None:
        raise AuthorityViolation(f"unparseable official box date: {raw}")
    month = MONTHS.get(match.group(1).lower())
    if month is None:
        raise AuthorityViolation(f"unparseable official box month: {raw}")
    return f"{int(match.group(3)):04d}-{month:02d}-{int(match.group(2)):02d}"


def reconstruct_index_date(raw: str, season: int) -> str | None:
    match = INDEX_DATE_RE.search(clean_text(raw))
    if match is None:
        return None
    month = MONTHS.get(match.group(1).lower())
    if month is None:
        return None
    year = season + 1 if month == 1 else season
    return f"{year:04d}-{month:02d}-{int(match.group(2)):02d}"


def _anchor_index(text: str, name: str, start_at: int = 0) -> int:
    quoted = text.find(f'name="{name}"', start_at)
    bare = text.find(f"name={name}", start_at)
    hits = [item for item in (quoted, bare) if item >= start_at]
    return min(hits) if hits else -1


def page_section(text: str, name: str, *following: str) -> str:
    start = _anchor_index(text, name)
    if start < 0:
        heading = re.search(rf"(?i)<h3>[^<]*{re.escape(name.replace('GAME.', '').replace('.', ' '))}[^<]*</h3>", text)
        start = heading.start() if heading else -1
    if start < 0:
        return ""
    ends = [_anchor_index(text, item, start + 8) for item in following]
    ends = [item for item in ends if item > start]
    return text[start : (min(ends) if ends else len(text))]


def table_rows(block: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for table in TABLE_RE.findall(block):
        for raw_row in ROW_RE.findall(table):
            cells = [clean_text(cell) for cell in CELL_RE.findall(raw_row)]
            cells = [cell for cell in cells if cell]
            if cells:
                rows.append(cells)
    return rows


def present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, dict, str)) and not value:
        return False
    return True


def coverage_flag(value: object) -> str:
    return "PRESENT" if present(value) else "ABSENT"


def expected_authority() -> dict[str, bool]:
    return {
        "completeness_claim": False,
        "contest_id_fabrication": False,
        "name_only_promotion": False,
        "name_only_player_merge": False,
        "ncaa_contest_identity": False,
        "historical_known_at_from_capture_time": False,
        "historical_pit_admission": False,
        "preliminary_training_admission": False,
        "protected_training_admission": False,
        "protected_evaluation_admission": False,
        "protected_outcome_authority": False,
        "champion_or_production_promotion": False,
        "forecast_publication": False,
        "availability_claim": False,
        "membership_as_availability": False,
        "participation_as_availability": False,
        "same_game_pregame_feature_admission": False,
        "wmt_payload_mutated_in_place": False,
    }


def expected_scientific_nonclaims() -> dict[str, bool]:
    return {
        "completeness_claimed": False,
        "historical_known_at_established": False,
        "historical_population_ready": False,
        "pregame_availability_admitted": False,
        "roster_membership_used_as_availability": False,
        "participation_used_as_availability": False,
        "ncaa_contest_ids_created": False,
        "protected_lane_opened": False,
        "protected_evaluation_admitted": False,
        "protected_performance_claimed": False,
        "champion_or_production_promotion": False,
        "tamu_specialization_lift_claimed": False,
        "bas_or_aggie_excess_result_claimed": False,
        "trained_production_champion": False,
        "same_game_pregame_features_admitted": False,
        "wmt_candidate_payload_rewritten": False,
    }


def expected_admissions() -> dict[str, str]:
    return {
        "normalization_admission": "CANDIDATE_ONLY",
        "source_authority": "SRC-014_OFFICIAL_SCHOOL_EVIDENCE",
        "ncaa_contest_identity": "NOT_CREATED",
        "historical_known_at": "UNKNOWN_CAPTURE_TIME_ONLY",
        "pregame_availability": "BLOCKED",
        "player_identity": "SOURCE_PLAYER_CANDIDATE",
        "protected_lane": PROTECTED_LANE,
        "bat_523": "IN_PROGRESS",
        "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
        "wmt_payload": "PRESERVED_IMMUTABLE",
        "rights_disposition": "DERIVED_ONLY_OR_REVIEW_PRIVATE_RESEARCH",
        "same_game_pregame_features": "BLOCKED",
    }


def refuse_name_only_player_merge(candidates: list[Mapping[str, Any]]) -> None:
    raise AuthorityViolation("name-only player merge is forbidden")


def availability_from_participation(_row: Mapping[str, Any]) -> None:
    raise AuthorityViolation("participation does not establish availability")


def availability_from_roster_membership(_row: Mapping[str, Any]) -> None:
    raise AuthorityViolation("roster membership does not establish availability")


def parse_season_index_rows(body: bytes, season: int, parent_url: str) -> list[dict[str, Any]]:
    text = decode_page(body)
    rows: list[dict[str, Any]] = []
    for table in TABLE_RE.findall(text):
        parsed_rows = ROW_RE.findall(table)
        if not parsed_rows:
            continue
        headers = [re.sub(r"[^a-z0-9]+", "_", clean_text(cell).lower()).strip("_") for cell in CELL_RE.findall(parsed_rows[0])]
        if "opponent" not in headers or "box_score" not in headers:
            continue
        for raw_row in parsed_rows[1:]:
            cells = [clean_text(cell) for cell in CELL_RE.findall(raw_row)]
            if len(cells) < 4:
                continue
            record = {headers[index] if index < len(headers) else f"col_{index}": cells[index] for index in range(len(cells))}
            hrefs = re.findall(r'(?is)<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', raw_row)
            box_url = None
            for href, label in hrefs:
                if clean_text(label).casefold() != "box score":
                    continue
                candidate = validate_official_url(urljoin(parent_url, href.split("#", 1)[0]))
                if BOX_PATH_RE.match(urlsplit(candidate).path):
                    box_url = candidate
                    break
            if box_url is None:
                continue
            result = INDEX_RESULT_RE.search(record.get("result") or "")
            if result is None:
                raise AuthorityViolation(f"season index row missing W/L/score: {record}")
            tamu_points = int(result.group(2))
            opponent_points = int(result.group(3))
            opponent = opponent_candidate(record.get("opponent") or "")
            location = record.get("location") or ""
            raw_date = record.get("date") or ""
            rows.append(
                {
                    "source_season": season,
                    "raw_date": raw_date,
                    "index_date_candidate": reconstruct_index_date(raw_date, season),
                    "opponent_raw": record.get("opponent") or "",
                    "opponent_candidate": opponent,
                    "opponent_normalized": normalize_team_name(opponent),
                    "location_raw": location,
                    "site_token": site_token(location),
                    "result_raw": record.get("result") or "",
                    "tamu_points": tamu_points,
                    "opponent_points": opponent_points,
                    "box_url": box_url,
                    "venue_state": (
                        "NEUTRAL"
                        if "vs." in (record.get("opponent") or "").lower()
                        else "HOME"
                        if "college station" in location.lower()
                        else "AWAY"
                    ),
                    "schedule_sequence": len(rows) + 1,
                }
            )
    if len(rows) != 13:
        raise AuthorityViolation(f"{season} official season index did not expose 13 box-linked schedule rows")
    return rows


def parse_quarter_scores(sum_block: str) -> list[dict[str, Any]]:
    scores: list[dict[str, Any]] = []
    in_table = False
    for cells in table_rows(sum_block):
        header = " ".join(cells).lower()
        if "score by quarters" in header:
            in_table = True
            continue
        if in_table and len(cells) >= 2 and not cells[0].lower().startswith("score"):
            try:
                total = int(cells[-1])
            except ValueError:
                continue
            periods = []
            for item in cells[1:-1]:
                try:
                    periods.append(int(item))
                except ValueError:
                    periods.append(None)
            scores.append({"team_raw": cells[0], "periods": periods, "points": total})
        if in_table and len(scores) >= 2:
            break
    if len(scores) < 2:
        raise AuthorityViolation("box score is missing labeled quarter/score rows")
    return scores


def parse_team_statistics(tem_block: str, visitor_name: str, home_name: str) -> list[dict[str, Any]]:
    stats: list[dict[str, Any]] = []
    started = False
    for cells in table_rows(tem_block):
        label = cells[0].lower()
        if "team totals" in label:
            started = True
            continue
        if not started or len(cells) < 3:
            continue
        if label in {"team totals"}:
            continue
        stats.append(
            {
                "stat_raw": cells[0],
                "visitor_raw": cells[1],
                "home_raw": cells[2],
                "visitor_team": visitor_name,
                "home_team": home_name,
            }
        )
    return stats


def parse_player_stat_tables(ind_block: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    current_team = None
    for table in TABLE_RE.findall(ind_block):
        rows = ROW_RE.findall(table)
        if not rows:
            continue
        heading = clean_text(rows[0]) if rows else ""
        if heading in {"Texas A&M", "Texas"} or (heading and "vs" not in heading.lower() and len(heading) < 40 and PLAYER_NAME_RE.match(heading.replace("&", "and"))):
            if heading.lower() not in {"rushing", "passing", "receiving"}:
                current_team = heading
        headers = [clean_text(cell) for cell in CELL_RE.findall(rows[0])]
        group = headers[0].lower() if headers else ""
        if group not in {"rushing", "passing", "receiving"}:
            continue
        for raw_row in rows[1:]:
            cells = [clean_text(cell) for cell in CELL_RE.findall(raw_row)]
            if len(cells) < 2:
                continue
            name = cells[0]
            if not name or name.lower().startswith("totals") or name.lower() in {group, "no.", "name"}:
                continue
            if not PLAYER_NAME_RE.match(name.replace(",", "")):
                continue
            candidates.append(
                {
                    "team_raw": current_team,
                    "name_raw": name,
                    "stat_group": group,
                    "raw_values": cells[1:],
                    "identity_status": "SOURCE_PLAYER_CANDIDATE",
                    "availability": "NOT_ESTABLISHED",
                }
            )
    return candidates


def parse_scoring_plays(new_block: str) -> list[dict[str, Any]]:
    plays: list[dict[str, Any]] = []
    start = new_block.lower().find("scoring summary")
    block = new_block[start:] if start >= 0 else new_block
    text = clean_text(re.sub(r"(?s)<[^>]+>", " ", block))
    current_quarter = None
    pattern = re.compile(
        r"(?:(?P<quarter>1st|2nd|3rd|4th|OT)\s+)?(?P<clock>\d{1,2}:\d{2})\s+(?P<team>[A-Z]{2,5})\s+-\s+(?P<play>.+?)(?=(?:1st|2nd|3rd|4th|OT)\s+\d{1,2}:\d{2}|\s+\d{1,2}:\d{2}\s+[A-Z]{2,5}\s+-|$)",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        if match.group("quarter"):
            current_quarter = match.group("quarter")
        play = clean_text(match.group("play"))
        if "yd" not in play.lower() and "field goal" not in play.lower() and "safety" not in play.lower() and "return" not in play.lower():
            continue
        plays.append(
            {
                "quarter_raw": current_quarter,
                "clock_raw": match.group("clock"),
                "team_raw": match.group("team").upper(),
                "play_raw": play,
            }
        )
    return plays


def parse_drives(drv_block: str) -> list[dict[str, Any]]:
    drives: list[dict[str, Any]] = []
    for cells in table_rows(drv_block):
        if len(cells) < 5:
            continue
        quarter = cells[1] if len(cells) > 1 else ""
        if quarter not in {"1st", "2nd", "3rd", "4th", "OT"}:
            continue
        if not re.match(r"^[A-Z]{2,4}$", cells[0]):
            continue
        drives.append(
            {
                "team_raw": cells[0],
                "quarter_raw": quarter,
                "start_spot_raw": cells[2] if len(cells) > 2 else "",
                "obtained_raw": cells[4] if len(cells) > 4 else "",
                "how_lost_raw": cells[8] if len(cells) > 8 else "",
                "plays_yards_raw": cells[9] if len(cells) > 9 else "",
            }
        )
    return drives


def parse_play_by_play(ply_block: str) -> list[dict[str, Any]]:
    plays: list[dict[str, Any]] = []
    tokens = ("rush", "pass", "kick", "punt", "penalty", "sack", "field goal", "kneel", "drive start")
    for raw_row in ROW_RE.findall(ply_block):
        line = clean_text(raw_row)
        if not line or not any(token in line.lower() for token in tokens):
            continue
        if line.lower().startswith("play-by-play"):
            continue
        plays.append({"play_raw": line})
    return plays


def parse_starters(pre_block: str) -> list[dict[str, Any]]:
    starters: list[dict[str, Any]] = []
    team = None
    unit = None
    text = re.sub(r"(?s)<[^>]+>", "\n", pre_block)
    if "Game Starters" not in text:
        return starters
    for raw_line in text.splitlines():
        line = clean_text(raw_line)
        if not line:
            continue
        compact_team = line.replace("&", "and")
        if line in {"Texas A&M", "Texas", "LSU", "SMU", "FIU"} or (
            2 < len(line) < 40 and PLAYER_NAME_RE.match(compact_team) and not STARTER_RE.match(line)
        ):
            team = line
            continue
        if line.startswith("POS"):
            unit = "OFFENSE" if "OFFENSE" in line.upper() else "DEFENSE" if "DEFENSE" in line.upper() else unit
            continue
        match = STARTER_RE.match(line)
        if match is None:
            continue
        starters.append(
            {
                "team_raw": team,
                "unit": unit,
                "position_raw": match.group(1),
                "jersey_raw": match.group(2),
                "name_raw": match.group(3),
                "identity_status": "SOURCE_PLAYER_CANDIDATE",
                "availability": "NOT_ESTABLISHED",
            }
        )
    return starters


def parse_participation(pre_block: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = pre_block.lower().find("player participation")
    if start < 0:
        return rows
    text = clean_text(re.sub(r"(?s)<[^>]+>", " ", pre_block[start:]))
    current_team = None
    for chunk in re.split(r"(Texas A&M|Texas):", text):
        if chunk in {"Texas A&M", "Texas"}:
            current_team = chunk
            continue
        if current_team is None:
            continue
        for jersey, name in PART_RE.findall(chunk):
            rows.append(
                {
                    "team_raw": current_team,
                    "jersey_raw": jersey,
                    "name_raw": name.strip(" ,."),
                    "identity_status": "SOURCE_PLAYER_CANDIDATE",
                    "availability": "NOT_ESTABLISHED",
                }
            )
    return rows


def parse_officials(block: str) -> list[dict[str, str]]:
    officials: list[dict[str, str]] = []
    text = clean_text(re.sub(r"(?s)<[^>]+>", " ", block))
    start = text.lower().find("officials:")
    if start < 0:
        named = {
            "Referee": re.search(r"Referee:\s*([^<]+?)(?:Umpire:|$)", block, re.IGNORECASE),
            "Umpire": re.search(r"Umpire:\s*([^<]+?)(?:Linesman:|$)", block, re.IGNORECASE),
            "Linesman": re.search(r"Linesman:\s*([^<]+?)(?:Line judge:|$)", block, re.IGNORECASE),
        }
        for role, match in named.items():
            if match:
                officials.append({"role_raw": role, "name_raw": clean_text(match.group(1))})
        return officials
    payload = text[start + len("Officials:") :]
    payload = payload.split("Temperature:")[0].split("Kickoff time:")[0]
    for part in re.split(r"[;•]+", payload):
        item = clean_text(part)
        if ":" not in item:
            continue
        role, name = item.split(":", 1)
        if name.strip():
            officials.append({"role_raw": role.strip(), "name_raw": name.strip()})
    return officials


def parse_official_box_page(
    body: bytes,
    *,
    url: str,
    source_season: int,
    raw_sha256: str,
) -> dict[str, Any]:
    validate_official_url(url)
    match = BOX_PATH_RE.match(urlsplit(url).path)
    if match is None:
        raise AuthorityViolation(f"non-box official URL submitted as box score: {url}")
    path_season = season_from_archive_folder(match.group(1))
    if path_season != source_season:
        raise AuthorityViolation(f"wrong-season box-score URL for {source_season}: {url}")
    if sha256_bytes(body) != raw_sha256:
        raise AuthorityViolation("changed raw source hash")
    text = decode_page(body)
    if "texas a&m" not in text.lower() and "texas a&amp;m" not in text.lower():
        raise AuthorityViolation("missing Texas A&M team identity")
    season_match = SEASON_RE.search(text)
    if season_match is None:
        raise AuthorityViolation("box page missing official football-season header")
    football_season = int(season_match.group(1))
    if football_season != source_season:
        raise AuthorityViolation(
            f"calendar-year/season-year confusion or wrong-season page: header {football_season} vs source {source_season}"
        )
    head = HEAD_RE.search(text)
    date_match = DATE_RE.search(text)
    if head is None or date_match is None:
        raise AuthorityViolation("box page missing game identity metadata")
    visitor_name = strip_rank_prefix(head.group(1))
    home_name = strip_rank_prefix(head.group(2))
    raw_date = clean_text(date_match.group(1))
    calendar_date = parse_statcrew_date(raw_date)
    if calendar_date[:4] != str(football_season) and not (
        football_season + 1 == int(calendar_date[:4]) and calendar_date[5:7] == "01"
    ):
        raise AuthorityViolation("played date is not a valid same-season or January postseason date")
    tamu_side = None
    if is_tamu_name(visitor_name):
        tamu_side = "visitor"
        opponent = opponent_candidate(home_name)
    elif is_tamu_name(home_name):
        tamu_side = "home"
        opponent = opponent_candidate(visitor_name)
    else:
        raise AuthorityViolation("Texas A&M is not a labeled participant")
    following = ("GAME.SUM", "GAME.TEM", "GAME.IND", "GAME.DRV", "GAME.DEF", "GAME.PRE", "GAME.NEW", "GAME.PLY")
    sum_block = page_section(text, "GAME.SUM", *following)
    tem_block = page_section(text, "GAME.TEM", *following)
    ind_block = page_section(text, "GAME.IND", *following)
    drv_block = page_section(text, "GAME.DRV", *following)
    pre_block = page_section(text, "GAME.PRE", *following)
    new_block = page_section(text, "GAME.NEW", *following)
    ply_block = page_section(text, "GAME.PLY", *following)
    if not sum_block:
        sum_block = text
    scores = parse_quarter_scores(sum_block)
    visitor_score = next(
        (item for item in scores if normalize_team_name(strip_rank_prefix(item["team_raw"])) == normalize_team_name(visitor_name)),
        None,
    )
    home_score = next(
        (item for item in scores if normalize_team_name(strip_rank_prefix(item["team_raw"])) == normalize_team_name(home_name)),
        None,
    )
    if visitor_score is None or home_score is None:
        raise AuthorityViolation("score rows do not bind visitor/home team labels")
    tamu_points = visitor_score["points"] if tamu_side == "visitor" else home_score["points"]
    opponent_points = home_score["points"] if tamu_side == "visitor" else visitor_score["points"]
    site = clean_text(SITE_RE.search(text).group(1)) if SITE_RE.search(text) else clean_text(head.group(4))
    stadium = clean_text(STAD_RE.search(text).group(1)) if STAD_RE.search(text) else ""
    attendance = ATT_RE.search(text)
    kickoff = clean_text(KICK_RE.search(text).group(1)) if KICK_RE.search(text) else ""
    end_time = clean_text(END_RE.search(text).group(1)) if END_RE.search(text) else ""
    duration = clean_text(DUR_RE.search(text).group(1)) if DUR_RE.search(text) else ""
    temperature = clean_text(TEMP_RE.search(text).group(1)) if TEMP_RE.search(text) else ""
    wind = clean_text(WIND_RE.search(text).group(1)) if WIND_RE.search(text) else ""
    weather = clean_text(WEATH_RE.search(text).group(1)) if WEATH_RE.search(text) else ""
    officials = parse_officials(new_block) or parse_officials(sum_block) or parse_officials(text)
    team_stats = parse_team_statistics(tem_block or text, visitor_name, home_name)
    player_stats = parse_player_stat_tables(ind_block or text)
    scoring = parse_scoring_plays(new_block or sum_block or text)
    drives = parse_drives(drv_block)
    pbp = parse_play_by_play(ply_block)
    starters = parse_starters(new_block) or parse_starters(pre_block)
    participation = parse_participation(new_block) or parse_participation(pre_block)
    penalties_present = any("penalt" in item["stat_raw"].lower() for item in team_stats) or "penalties-yards" in text.lower()
    turnovers_present = any(
        any(token in item["stat_raw"].lower() for token in ("fumble", "intercept")) for item in team_stats
    ) or "fumbles-lost" in text.lower()
    raw_label = f"{visitor_name} vs {home_name} ({raw_date} at {site})"
    coverage = {
        "game_identity_metadata": coverage_flag(raw_label),
        "season": coverage_flag(football_season),
        "played_date": coverage_flag(calendar_date),
        "teams": coverage_flag(visitor_name and home_name),
        "scores": coverage_flag(tamu_points is not None and opponent_points is not None),
        "quarter_scoring": coverage_flag(visitor_score["periods"] and home_score["periods"]),
        "site_venue": coverage_flag(site or stadium),
        "attendance": coverage_flag(attendance.group(1) if attendance else ""),
        "kickoff_time": coverage_flag(kickoff),
        "end_time": coverage_flag(end_time),
        "duration": coverage_flag(duration),
        "weather": coverage_flag(temperature or wind or weather),
        "officials": coverage_flag(officials),
        "team_statistics": coverage_flag(team_stats),
        "individual_player_statistics": coverage_flag(player_stats),
        "scoring_summary": coverage_flag(scoring),
        "drives": coverage_flag(drives),
        "play_by_play": coverage_flag(pbp),
        "participation": coverage_flag(participation),
        "starters": coverage_flag(starters),
        "penalties": "PRESENT" if penalties_present else "ABSENT",
        "turnovers": "PRESENT" if turnovers_present else "ABSENT",
    }
    return {
        "url": url,
        "source_sha256": raw_sha256,
        "source_season": source_season,
        "football_season": football_season,
        "calendar_date": calendar_date,
        "raw_date": raw_date,
        "raw_game_label": raw_label,
        "visitor_name": visitor_name,
        "home_name": home_name,
        "tamu_side": tamu_side,
        "opponent_candidate": opponent,
        "opponent_normalized": normalize_team_name(opponent),
        "tamu_points": tamu_points,
        "opponent_points": opponent_points,
        "visitor_points": visitor_score["points"],
        "home_points": home_score["points"],
        "visitor_periods": visitor_score["periods"],
        "home_periods": home_score["periods"],
        "site": site,
        "site_token": site_token(site),
        "stadium": stadium,
        "attendance": attendance.group(1).replace(",", "") if attendance else None,
        "kickoff_time": kickoff or None,
        "end_time": end_time or None,
        "duration": duration or None,
        "temperature": temperature or None,
        "wind": wind or None,
        "weather": weather or None,
        "officials": officials,
        "team_statistics": team_stats,
        "player_stat_candidates": player_stats,
        "scoring_plays": scoring,
        "drives": drives,
        "play_by_play": pbp,
        "starters": starters,
        "participation": participation,
        "domain_coverage": coverage,
        "parser_version": PARSER_VERSION,
        "temporal_authority": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "historical_publication_time": None,
        "ncaa_contest_id": None,
        "canonical_game_id": None,
        "availability_claim": False,
    }


def match_to_official_index(parsed: Mapping[str, Any], index_rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    url_matches = [row for row in index_rows if row["box_url"] == parsed["url"]]
    if not url_matches:
        raise AuthorityViolation(f"box URL was not discovered from the official season index: {parsed['url']}")
    if len(url_matches) > 1:
        raise AuthorityViolation(f"duplicate official season-index box URL: {parsed['url']}")
    row = url_matches[0]
    name_only = normalize_team_name(parsed["opponent_candidate"]) == row["opponent_normalized"]
    score_match = parsed["tamu_points"] == row["tamu_points"] and parsed["opponent_points"] == row["opponent_points"]
    season_match = int(parsed["football_season"]) == int(row["source_season"])
    site_match = bool(parsed["site_token"]) and (
        parsed["site_token"] == row["site_token"] or parsed["site_token"] in row["location_raw"].lower() or row["site_token"] in parsed["site"].lower()
    )
    date_match = parsed["calendar_date"] == row["index_date_candidate"]
    if name_only and not (score_match and season_match):
        return {
            "canonical_game_match_status": "NAME_ONLY_INSUFFICIENT",
            "conflict_status": "NAME_ONLY_NOT_PROMOTED",
            "index_date_candidate": row["index_date_candidate"],
            "index_date_raw": row["raw_date"],
            "schedule_sequence": row["schedule_sequence"],
            "venue_state": row["venue_state"],
        }
    if not (name_only and score_match and season_match and site_match):
        return {
            "canonical_game_match_status": "UNMATCHED_STRONG_TUPLE",
            "conflict_status": "INSUFFICIENT_TUPLE",
            "index_date_candidate": row["index_date_candidate"],
            "index_date_raw": row["raw_date"],
            "schedule_sequence": row["schedule_sequence"],
            "venue_state": row["venue_state"],
        }
    if not date_match:
        return {
            "canonical_game_match_status": "OFFICIAL_INDEX_DATE_CONFLICT",
            "conflict_status": "SEASON_INDEX_DATE_VS_BOX_PLAYED_DATE",
            "index_date_candidate": row["index_date_candidate"],
            "index_date_raw": row["raw_date"],
            "schedule_sequence": row["schedule_sequence"],
            "venue_state": row["venue_state"],
        }
    return {
        "canonical_game_match_status": "MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE",
        "conflict_status": "NONE",
        "index_date_candidate": row["index_date_candidate"],
        "index_date_raw": row["raw_date"],
        "schedule_sequence": row["schedule_sequence"],
        "venue_state": row["venue_state"],
    }


def compact_game(parsed: Mapping[str, Any], match: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "url": parsed["url"],
        "source_sha256": parsed["source_sha256"],
        "source_season": parsed["source_season"],
        "football_season": parsed["football_season"],
        "calendar_date": parsed["calendar_date"],
        "raw_date": parsed["raw_date"],
        "raw_game_label": parsed["raw_game_label"],
        "visitor_name": parsed["visitor_name"],
        "home_name": parsed["home_name"],
        "opponent_candidate": parsed["opponent_candidate"],
        "opponent_normalized": parsed["opponent_normalized"],
        "tamu_points": parsed["tamu_points"],
        "opponent_points": parsed["opponent_points"],
        "site": parsed["site"],
        "stadium": parsed["stadium"],
        "attendance": parsed["attendance"],
        "kickoff_time": parsed["kickoff_time"],
        "end_time": parsed["end_time"],
        "duration": parsed["duration"],
        "weather": parsed["weather"],
        "domain_coverage": parsed["domain_coverage"],
        "counts": {
            "team_stat_rows": len(parsed["team_statistics"]),
            "player_stat_candidates": len(parsed["player_stat_candidates"]),
            "scoring_plays": len(parsed["scoring_plays"]),
            "drives": len(parsed["drives"]),
            "play_by_play": len(parsed["play_by_play"]),
            "participation": len(parsed["participation"]),
            "starters": len(parsed["starters"]),
            "officials": len(parsed["officials"]),
        },
        "canonical_game_id": None,
        "canonical_game_match_status": match["canonical_game_match_status"],
        "conflict_status": match["conflict_status"],
        "index_date_raw": match["index_date_raw"],
        "index_date_candidate": match["index_date_candidate"],
        "schedule_sequence": match["schedule_sequence"],
        "venue_state": match["venue_state"],
        "ncaa_contest_id": None,
        "temporal_authority": parsed["temporal_authority"],
        "historical_publication_time": None,
        "availability_claim": False,
    }


def normalized_rows(parsed: Mapping[str, Any], match: Mapping[str, Any]) -> list[dict[str, Any]]:
    lineage = f"SRC-014/official-school-box/{parsed['source_sha256']}"
    base = {
        "source_url": parsed["url"],
        "source_sha": parsed["source_sha256"],
        "source_page_identity": parsed["source_sha256"],
        "season": parsed["football_season"],
        "raw_game_label": parsed["raw_game_label"],
        "normalized_opponent_candidate": parsed["opponent_normalized"],
        "raw_date": parsed["raw_date"],
        "normalized_date": parsed["calendar_date"],
        "raw_score": f"{parsed['tamu_points']}-{parsed['opponent_points']}",
        "normalized_score": {
            "tamu_points": parsed["tamu_points"],
            "opponent_points": parsed["opponent_points"],
        },
        "parser_version": PARSER_VERSION,
        "evidence_lineage": lineage,
        "canonical_game_match_status": match["canonical_game_match_status"],
        "conflict_status": match["conflict_status"],
        "temporal_authority": parsed["temporal_authority"],
        "canonical_game_id": None,
        "ncaa_contest_id": None,
    }
    rows = [
        {**base, "domain": "game_identity_metadata", "grain": "game", "raw_value": parsed["raw_game_label"], "normalized_value": parsed["raw_game_label"]},
        {**base, "domain": "season", "grain": "game", "raw_value": parsed["football_season"], "normalized_value": parsed["football_season"]},
        {**base, "domain": "played_date", "grain": "game", "raw_value": parsed["raw_date"], "normalized_value": parsed["calendar_date"]},
        {**base, "domain": "scores", "grain": "game", "raw_value": f"{parsed['visitor_name']} {parsed['visitor_points']} {parsed['home_name']} {parsed['home_points']}", "normalized_value": base["normalized_score"]},
        {**base, "domain": "site_venue", "grain": "game", "raw_value": f"{parsed['site']} / {parsed['stadium']}", "normalized_value": {"site": parsed["site"], "stadium": parsed["stadium"], "venue_state": match["venue_state"]}},
    ]
    if parsed["attendance"]:
        rows.append({**base, "domain": "attendance", "grain": "game", "raw_value": parsed["attendance"], "normalized_value": int(parsed["attendance"])})
    for item in parsed["team_statistics"]:
        rows.append({**base, "domain": "team_statistics", "grain": "team-stat", "raw_value": item, "normalized_value": item})
    for item in parsed["player_stat_candidates"]:
        rows.append(
            {
                **base,
                "domain": "individual_player_statistics",
                "grain": "source-player-candidate",
                "raw_value": item,
                "normalized_value": item,
                "identity_status": "SOURCE_PLAYER_CANDIDATE",
                "availability": "NOT_ESTABLISHED",
            }
        )
    for item in parsed["participation"]:
        rows.append(
            {
                **base,
                "domain": "participation",
                "grain": "source-player-candidate",
                "raw_value": item,
                "normalized_value": item,
                "identity_status": "SOURCE_PLAYER_CANDIDATE",
                "availability": "NOT_ESTABLISHED",
            }
        )
    return rows


def domain_coverage_totals(games: list[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    totals = {domain: {"PRESENT": 0, "ABSENT": 0} for domain in DOMAINS}
    for game in games:
        coverage = game.get("domain_coverage") or {}
        for domain in DOMAINS:
            flag = coverage.get(domain)
            if flag not in totals[domain]:
                raise AuthorityViolation(f"fabricated domain coverage flag: {domain}={flag}")
            totals[domain][flag] += 1
    return totals


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    return stable_hash({field: gate.get(field) for field in GATE_IDENTITY_FIELDS})


def load_contract(repo_root: Path) -> dict[str, Any]:
    return load_json(repo_root / CONTRACT_RELATIVE)


def _archive_capture(archive_gate: Mapping[str, Any], url: str) -> dict[str, Any]:
    for item in archive_gate.get("captures") or []:
        if item.get("url") == url:
            return item
    raise AuthorityViolation(f"BAT-579 archive gate is missing capture for {url}")


def normalize_boxscores(*, data_root: Path, repo_root: Path) -> dict[str, Any]:
    contract = load_contract(repo_root)
    archive_gate = load_json(repo_root / ARCHIVE_GATE_RELATIVE)
    if archive_gate.get("acquisition_identity") != ARCHIVE_ACQUISITION_IDENTITY:
        raise AuthorityViolation("BAT-579 archive identity drifted")
    boxes = archive_gate["discovered_box_score_urls"]
    if stable_hash(boxes) != PINNED_BOX_URLS_IDENTITY:
        raise AuthorityViolation("Phase 3 may consume only the BAT-579 discovered official box URLs")
    index_rows: list[dict[str, Any]] = []
    for season in (2010, 2011):
        parent = f"https://files.12thman.com/history/football/years/{season}.html"
        capture = _archive_capture(archive_gate, parent)
        raw_path = data_root / capture["raw_relative_path"]
        if sha256_file(raw_path) != capture["raw_sha256"]:
            raise AuthorityViolation(f"season index hash drift: {parent}")
        index_rows.extend(parse_season_index_rows(raw_path.read_bytes(), season, parent))
    parsed_games: list[dict[str, Any]] = []
    compact_games: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for season in (2010, 2011):
        for url in boxes[str(season)]:
            if url in seen_urls:
                raise AuthorityViolation(f"duplicate box-score page: {url}")
            seen_urls.add(url)
            capture = _archive_capture(archive_gate, url)
            if capture.get("page_family") != "box_scores":
                raise AuthorityViolation("recap or non-box page used as box-score authority")
            raw_path = data_root / capture["raw_relative_path"]
            if not raw_path.is_file():
                raise AuthorityViolation(f"missing raw box-score payload: {url}")
            if sha256_file(raw_path) != capture["raw_sha256"]:
                raise AuthorityViolation(f"raw hash pointing to a missing or different file: {url}")
            parsed = parse_official_box_page(
                raw_path.read_bytes(),
                url=url,
                source_season=season,
                raw_sha256=capture["raw_sha256"],
            )
            match = match_to_official_index(parsed, index_rows)
            parsed_games.append(parsed)
            compact = compact_game(parsed, match)
            compact_games.append(compact)
            rows.extend(normalized_rows(parsed, match))
    if any(game.get("ncaa_contest_id") for game in compact_games):
        raise AuthorityViolation("NCAA contest IDs were invented")
    coverage = domain_coverage_totals(compact_games)
    counts = {
        "target_games_2010": 13,
        "target_games_2011": 13,
        "target_games_total": 26,
        "captured_pages_2010": sum(1 for game in compact_games if game["source_season"] == 2010),
        "captured_pages_2011": sum(1 for game in compact_games if game["source_season"] == 2011),
        "captured_pages_total": len(compact_games),
        "missing_pages_2010": 0,
        "missing_pages_2011": 0,
        "normalized_rows": len(rows),
        "player_stat_candidates": sum(game["counts"]["player_stat_candidates"] for game in compact_games),
        "participation_candidates": sum(game["counts"]["participation"] for game in compact_games),
        "matched_strong_tuple": sum(1 for game in compact_games if game["canonical_game_match_status"] == "MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE"),
        "date_conflicts": sum(1 for game in compact_games if game["conflict_status"] == "SEASON_INDEX_DATE_VS_BOX_PLAYED_DATE"),
        "ncaa_contest_ids_created": 0,
    }
    if counts["captured_pages_2010"] != 13 or counts["captured_pages_2011"] != 13:
        raise AuthorityViolation("official 2010/2011 box-score normalization coverage is incomplete")
    disposition = "OFFICIAL_SCHOOL_BOXSCORES_NORMALIZED_CANDIDATE_ONLY"
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_HISTORICAL_BOXSCORE_GATE",
        "result": f"PASS_{disposition}",
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": contract["decision_unit"],
        "jira_key": "BAT-580",
        "disposition": disposition,
        "source_id": SOURCE_ID,
        "parser_version": PARSER_VERSION,
        "counts": counts,
        "domain_coverage": coverage,
        "games": compact_games,
        "admissions": expected_admissions(),
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "protected_lane": PROTECTED_LANE,
        "upstream_identities": {
            "archive_acquisition_identity": ARCHIVE_ACQUISITION_IDENTITY,
            "discovered_box_urls_identity": PINNED_BOX_URLS_IDENTITY,
            "wmt_acquisition_identity": WMT_ACQUISITION_IDENTITY,
            "wmt_dataset_identity": WMT_DATASET_IDENTITY,
        },
    }
    gate["games_identity"] = stable_hash(compact_games)
    gate["coverage_identity"] = stable_hash(coverage)
    gate["dataset_identity"] = stable_hash({"games": compact_games, "counts": counts, "domain_coverage": coverage, "rows": rows})
    gate["gate_identity"] = compute_gate_identity(gate)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset_identity": gate["dataset_identity"],
        "games_identity": gate["games_identity"],
        "coverage_identity": gate["coverage_identity"],
        "source_id": SOURCE_ID,
        "parser_version": PARSER_VERSION,
        "counts": counts,
        "games": compact_games,
        "upstream_identities": gate["upstream_identities"],
    }
    manifest["manifest_identity"] = stable_hash(manifest)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "dataset_identity": gate["dataset_identity"],
        "parser_version": PARSER_VERSION,
        "source_id": SOURCE_ID,
        "counts": counts,
        "games": compact_games,
        "rows": rows,
        "scientific_nonclaims": expected_scientific_nonclaims(),
    }
    write_json(data_root / contract["payloads"]["acquisition_manifest"], manifest)
    write_json(data_root / contract["payloads"]["normalized_root"] / "normalized.json", payload)
    write_json(repo_root / GATE_RELATIVE, gate)
    return gate


def validate_compact_boxscore_gate(committed: Mapping[str, Any], contract: Mapping[str, Any]) -> None:
    if committed.get("schema_version") != SCHEMA_VERSION:
        raise AuthorityViolation("schema version drift")
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("classification drift")
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("source_id") != SOURCE_ID:
        raise AuthorityViolation("source id drift")
    if committed.get("parser_version") != PARSER_VERSION:
        raise AuthorityViolation("parser version drift")
    if committed.get("contract_id") != contract["contract_id"]:
        raise AuthorityViolation("contract id drift")
    if committed.get("authority") != expected_authority():
        raise AuthorityViolation("authority nonclaim drift")
    if committed.get("scientific_nonclaims") != expected_scientific_nonclaims():
        raise AuthorityViolation("scientific nonclaim drift")
    if committed.get("admissions") != expected_admissions():
        raise AuthorityViolation("admission drift")
    if committed.get("upstream_identities", {}).get("archive_acquisition_identity") != ARCHIVE_ACQUISITION_IDENTITY:
        raise AuthorityViolation("BAT-579 archive identity was rewritten")
    if committed.get("upstream_identities", {}).get("wmt_dataset_identity") != WMT_DATASET_IDENTITY:
        raise AuthorityViolation("WMT dataset identity was rewritten")
    counts = committed.get("counts") or {}
    if counts.get("ncaa_contest_ids_created") != 0:
        raise AuthorityViolation("NCAA contest IDs were invented")
    if counts.get("target_games_total") != 26 or counts.get("captured_pages_total") != 26:
        raise AuthorityViolation("official box-score capture count drifted")
    if counts.get("captured_pages_2010") != 13 or counts.get("captured_pages_2011") != 13:
        raise AuthorityViolation("per-season official box-score count drifted")
    games = committed.get("games") or []
    if len(games) != 26:
        raise AuthorityViolation("compact game count drifted")
    urls = [item.get("url") for item in games]
    if len(urls) != len(set(urls)):
        raise AuthorityViolation("duplicate box-score page")
    if any(item.get("ncaa_contest_id") for item in games):
        raise AuthorityViolation("NCAA contest IDs were invented")
    if any(item.get("canonical_game_id") for item in games):
        raise AuthorityViolation("canonical game IDs were invented without a strong official tuple binding")
    if any(item.get("availability_claim") for item in games):
        raise AuthorityViolation("availability was claimed from box-score participation or roster membership")
    if any(item.get("historical_publication_time") is not None for item in games):
        raise AuthorityViolation("current retrieval timestamp used as historical publication time")
    if any(item.get("temporal_authority") != "UNKNOWN_RETRIEVAL_TIME_ONLY" for item in games):
        raise AuthorityViolation("temporal authority overclaimed")
    coverage = domain_coverage_totals(games)
    if coverage != committed.get("domain_coverage"):
        raise AuthorityViolation("domain coverage was not independently reconstructed")
    if stable_hash(games) != committed.get("games_identity"):
        raise AuthorityViolation("games identity does not reconstruct")
    if stable_hash(coverage) != committed.get("coverage_identity"):
        raise AuthorityViolation("coverage identity does not reconstruct")
    if PINNED_GAMES_IDENTITY and stable_hash(games) != PINNED_GAMES_IDENTITY:
        raise AuthorityViolation("compact games were not independently reconstructed")
    if PINNED_COVERAGE_IDENTITY and stable_hash(coverage) != PINNED_COVERAGE_IDENTITY:
        raise AuthorityViolation("domain coverage totals were not independently reconstructed")
    if PINNED_COUNTS and counts != PINNED_COUNTS:
        raise AuthorityViolation("box-score counts were not independently reconstructed")
    if compute_gate_identity(committed) != committed.get("gate_identity"):
        raise AuthorityViolation("gate identity does not reconstruct")
    texas_2011 = next((item for item in games if item["source_season"] == 2011 and item["opponent_normalized"] == normalize_team_name("Texas")), None)
    if texas_2011 is None or texas_2011["calendar_date"] != "2011-11-24" or texas_2011["tamu_points"] != 25 or texas_2011["opponent_points"] != 27:
        raise AuthorityViolation("2011 Texas official box tuple drifted")
    lsu_2010 = next((item for item in games if item["source_season"] == 2010 and item["opponent_normalized"] == normalize_team_name("LSU")), None)
    if lsu_2010 is None or lsu_2010["calendar_date"] != "2011-01-07" or lsu_2010["football_season"] != 2010:
        raise AuthorityViolation("2010 LSU postseason season/calendar split drifted")
    if lsu_2010["conflict_status"] != "SEASON_INDEX_DATE_VS_BOX_PLAYED_DATE":
        raise AuthorityViolation("2010 LSU season-index/box date conflict was silently normalized")


def reconstruct_from_pages(*, data_root: Path, repo_root: Path, committed: Mapping[str, Any]) -> dict[str, Any]:
    rebuilt = normalize_boxscores(data_root=data_root, repo_root=repo_root)
    if rebuilt["games"] != committed["games"]:
        raise AuthorityViolation("compact games were not independently reconstructed from official pages")
    if rebuilt["counts"] != committed["counts"]:
        raise AuthorityViolation("normalized counts drifted from independent reconstruction")
    if rebuilt["domain_coverage"] != committed["domain_coverage"]:
        raise AuthorityViolation("domain coverage drifted from independent reconstruction")
    if rebuilt["gate_identity"] != committed["gate_identity"]:
        raise AuthorityViolation("gate identity drifted from independent reconstruction")
    wmt_gate = load_json(repo_root / "artifacts/pit/historical_tamu_official_gamebook_reconciliation_gate.json")
    if wmt_gate["candidate_layer"]["dataset_identity"] != WMT_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-523 WMT candidate payload was rewritten")
    return rebuilt


def validate_artifact(
    *,
    data_root: Path,
    repo_root: Path,
    require_rebuild: bool = True,
    gate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    committed = dict(gate or load_json(repo_root / GATE_RELATIVE))
    contract = load_contract(repo_root)
    validate_compact_boxscore_gate(committed, contract)
    lake_ready = (data_root / RAW_ROOT / "box_scores").is_dir() and (data_root / contract["payloads"]["acquisition_manifest"]).is_file()
    if require_rebuild and not lake_ready:
        raise AuthorityViolation("external box-score reconstruction was required but the data root is not mounted")
    reconstructed = None
    if lake_ready:
        reconstructed = reconstruct_from_pages(data_root=data_root, repo_root=repo_root, committed=committed)
        manifest = load_json(data_root / contract["payloads"]["acquisition_manifest"])
        if manifest.get("dataset_identity") != committed.get("dataset_identity"):
            raise AuthorityViolation("external manifest dataset identity drifted")
        if manifest.get("games") != committed.get("games"):
            raise AuthorityViolation("external manifest games are not semantically equal")
    return {
        "result": "PASS",
        "gate_identity": committed["gate_identity"],
        "dataset_identity": committed["dataset_identity"],
        "games_identity": committed["games_identity"],
        "external_reconstruction": "MOUNTED" if reconstructed is not None else "NOT_MOUNTED",
    }


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))

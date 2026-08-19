"""Parse StatCrew preformatted domains from already-captured official 2007-2009 pages."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.tamu_official_historical_archive import (
    sha256_file,
    validate_official_url,
)
from aggie_analytics.data.tamu_official_historical_boxscores import (
    AuthorityViolation,
    expected_authority,
    expected_scientific_nonclaims,
)
from aggie_analytics.data.tamu_official_rich_structure import is_rich_structured
from aggie_analytics.validation.artifact_binding import compute_identity


SCHEMA_VERSION = "aggie.data.tamu_official_statcrew_preformatted.v1"
CONTRACT_RELATIVE = "configs/tamu_official_statcrew_preformatted_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_statcrew_preformatted_gate.json"
CONTRACT_ID = "BAT-591-TAMU-OFFICIAL-STATCREW-PREFORMATTED-V1"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_SRC014_STATCREW_PREFORMATTED_CANDIDATE_ONLY"
PASS_RESULT = "PASS_STATCREW_PREFORMATTED_DOMAINS_PARSED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
INVENTORY_IDENTITY = "d39d35ff7cfacf2e39a524d0f1fdb97072158c50f84225ed8413771140efaa37"
INVENTORY_GATE_IDENTITY = "f1a5821ad081dce7058848ccc453344f0a2827030959049133b69db15689c851"
PRE2010_GATE_RELATIVE = "artifacts/data_lake/tamu_official_pre2010_boxscore_gate.json"
PRE2010_GATE_IDENTITY = "c62a09d2b3bcf7e69c6b6ea90993084d124a779d7ab779e8ebeab300b2a9c006"
PRE2010_DATASET_IDENTITY = "1858893908f59afc8f6e88fea46764666869d7c809ddf2b3fedbdfcea02b6b59"
PRE2010_ACQUISITION_IDENTITY = "58c44cc252a6139a7618a779e9fc9b353949cf942ac93eeb08c38b6c697a62af"
BOX_2007_GATE_RELATIVE = "artifacts/data_lake/tamu_official_2007_boxscore_gate.json"
BOX_2007_GATE_IDENTITY = "f2080b0ebb7815892732b2e600917e00da972edca0379888fa0010ff6bf17e51"
BOX_2007_DATASET_IDENTITY = "8681c15f48e1335e3e56bca7f146af4dc9c7ce731d077b2923d977e429a8b0c0"
BOX_2007_ACQUISITION_IDENTITY = "d49d84a0d61e9046cfcc3b39f69d92ceb6d9efa46e36d49d26b9c832c20c2fa5"
PRE2010_CAPTURE_INDEX = "features/tamu_official_pre2010_boxscores/capture_index.json"
BOX_2007_CAPTURE_INDEX = "features/tamu_official_2007_boxscores/capture_index.json"
INVENTORY_GATE_RELATIVE = "artifacts/data_lake/tamu_official_historical_coverage_inventory_gate.json"
DOMAINS = (
    "team_statistics",
    "individual_player_statistics",
    "drives",
    "play_by_play",
)
PRE_RE = re.compile(r"(?is)<pre\b[^>]*>(.*?)</pre>")
TEAM_FINAL_RE = re.compile(r"team statistics\s*\(final\)", re.IGNORECASE)
IND_FINAL_RE = re.compile(r"individual statistics\s*\(final\)", re.IGNORECASE)
DRIVE_FINAL_RE = re.compile(r"drive chart\s*\(final\)", re.IGNORECASE)
DRIVE_QUARTER_RE = re.compile(r"drive chart\s*\(by quarter\)", re.IGNORECASE)
PBP_RE = re.compile(r"play-by-play summary", re.IGNORECASE)
COMPACT_TEAM_RE = re.compile(r"FIRST DOWNS\.{2,}")
NARRATIVE_GROUP_RE = re.compile(r"^\s*(RUSHING|PASSING|RECEIVING):\s*(.+)$", re.IGNORECASE)
NARRATIVE_PRESENT_RE = re.compile(r"(?im)^\s*(RUSHING|PASSING|RECEIVING):")
NARRATIVE_STOP_RE = re.compile(
    r"^(INTERCEPTIONS|FUMBLES|Stadium|Kickoff time|Officials|SACKS|TACKLES|Game Starters|Player participation)\b",
    re.IGNORECASE,
)
STAT_GROUP_HEADER_RE = re.compile(r"^(Rushing|Passing|Receiving)\s+No\.?\b", re.IGNORECASE | re.MULTILINE)
OTHER_IND_HEADER_RE = re.compile(
    r"^(Punting|All Returns|Interceptions|Fumbles|Field Goals|Kickoffs|Sacks|Tackles|Punt returns|Kick returns)\b",
    re.IGNORECASE,
)
TEAM_STAT_LINE_RE = re.compile(
    r"^(?P<label>.+?)(?:\.{2,}|\s{2,})\s*(?P<visitor>\S+)\s+(?P<home>\S+)\s*$"
)
DRIVE_LINE_RE = re.compile(r"^(?P<team>[A-Z]{2,5})\s+(?P<qtr>1st|2nd|3rd|4th|OT)\s+\S+")
PLAYER_TABLE_RE = re.compile(
    r"^(?P<name>(?:TEAM|[A-Za-z][A-Za-z.'\- ,]+?))\s{2,}(?P<values>.+\d.*)$"
)
REQUIRED_GATE_FIELDS = (
    "schema_version",
    "artifact_type",
    "result",
    "classification",
    "contract_id",
    "decision_unit",
    "jira_key",
    "disposition",
    "source_id",
    "inventory_identity",
    "payload_identity",
    "selected_seasons",
    "counts",
    "season_domain_coverage",
    "admissions",
    "authority",
    "scientific_nonclaims",
    "protected_lane",
    "upstream_identities",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    missing = [key for key in REQUIRED_GATE_FIELDS if key not in gate]
    if missing:
        raise AuthorityViolation("gate is missing required identity fields: " + ", ".join(missing))
    return compute_identity(gate, "gate_identity")


def strip_markup(text: str) -> str:
    text = re.sub(r"(?is)<script\b[^>]*>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style\b[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</(?:p|div|tr|h\d)>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html.unescape(text).replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines)


def extract_pre_blocks(page_text: str) -> list[str]:
    blocks: list[str] = []
    for raw in PRE_RE.findall(page_text):
        cleaned = strip_markup(raw)
        compact = re.sub(r"\s+", "", cleaned)
        if len(compact) < 20:
            continue
        blocks.append(cleaned)
    return blocks


def _section_after(text: str, start_re: re.Pattern[str], stop_res: tuple[re.Pattern[str], ...]) -> str:
    match = start_re.search(text)
    if match is None:
        return ""
    start = match.end()
    stops = [item.start() for item in (stop.search(text, start) for stop in stop_res) if item]
    end = min(stops) if stops else len(text)
    return text[start:end]


def _fingerprint_team_stats(rows: list[Mapping[str, Any]]) -> tuple[tuple[str, str, str], ...]:
    return tuple((str(row.get("stat_raw", "")), str(row.get("visitor_raw", "")), str(row.get("home_raw", ""))) for row in rows)


def parse_team_statistics(block: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    started = False
    for line in block.splitlines():
        text = line.strip()
        if not text:
            continue
        if re.fullmatch(r"[A-Z]{2,5}\s+[A-Z]{2,5}", text):
            started = True
            continue
        if re.fullmatch(r"[A-Z]{2,5}\s+[A-Z]{2,5}", re.sub(r"\s+", " ", text)):
            started = True
            continue
        if TEAM_FINAL_RE.search(text) or text.lower().startswith("first downs") or COMPACT_TEAM_RE.search(text):
            started = True
        if not started:
            continue
        match = TEAM_STAT_LINE_RE.match(text)
        if match is None:
            continue
        label = match.group("label").strip(" .")
        if label.lower() in {"team", "score"}:
            continue
        if not any(char.isalpha() for char in label):
            continue
        if label.lower().startswith("score by"):
            continue
        rows.append(
            {
                "stat_raw": label,
                "visitor_raw": match.group("visitor"),
                "home_raw": match.group("home"),
                "original_text": text,
            }
        )
    return rows


def _emit_narrative(group: str, body: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    segments = re.split(r"(?<=\.)\s+(?=[A-Z][A-Za-z&. ]{2,40}-[A-Za-z])", body)
    for segment in segments:
        item = segment.strip().rstrip(".")
        if "-" not in item:
            continue
        team, _, rest = item.partition("-")
        team = team.strip()
        if not team or any(char.isdigit() for char in team):
            continue
        for token in rest.split(";"):
            original = token.strip().rstrip(".")
            if not original:
                continue
            name = re.split(r"\s+\d", original, maxsplit=1)[0].strip()
            if len(name) < 2:
                continue
            rows.append(
                {
                    "team_raw": team,
                    "name_raw": name,
                    "stat_group": group,
                    "original_text": original,
                    "identity_status": "SOURCE_PLAYER_CANDIDATE",
                    "availability": "NOT_ESTABLISHED",
                }
            )
    return rows


def parse_narrative_players(block: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    current = ""
    buffer: list[str] = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        match = NARRATIVE_GROUP_RE.match(line)
        if match:
            if current:
                rows.extend(_emit_narrative(current, " ".join(buffer)))
            current = match.group(1).lower()
            buffer = [match.group(2).strip()]
            continue
        if current and NARRATIVE_STOP_RE.match(line):
            rows.extend(_emit_narrative(current, " ".join(buffer)))
            current = ""
            buffer = []
            continue
        if current and line:
            buffer.append(line)
    if current:
        rows.extend(_emit_narrative(current, " ".join(buffer)))
    return rows


def parse_table_players(block: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    current_team = ""
    current_group = ""
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith("totals"):
            continue
        header = STAT_GROUP_HEADER_RE.match(line)
        if header:
            current_group = header.group(1).lower()
            continue
        if OTHER_IND_HEADER_RE.match(line):
            current_group = ""
            continue
        if not any(char.isdigit() for char in line) and len(line) < 40 and " vs " not in line.lower() and set(line) != {"-"}:
            current_team = line
            continue
        if not current_group:
            continue
        match = PLAYER_TABLE_RE.match(line)
        if match is None:
            continue
        name = match.group("name").strip()
        if name.lower().startswith("totals"):
            continue
        rows.append(
            {
                "team_raw": current_team,
                "name_raw": name,
                "stat_group": current_group,
                "original_text": line,
                "identity_status": "SOURCE_PLAYER_CANDIDATE",
                "availability": "NOT_ESTABLISHED",
            }
        )
    return rows


def parse_player_statistics(block: str) -> list[dict[str, Any]]:
    if any(STAT_GROUP_HEADER_RE.match(line.strip()) for line in block.splitlines()):
        return parse_table_players(block)
    return parse_narrative_players(block)


def parse_drives(block: str) -> list[dict[str, Any]]:
    section = _section_after(block, DRIVE_FINAL_RE, (DRIVE_QUARTER_RE, re.compile(r"time of possession", re.I)))
    if not section:
        return []
    rows: list[dict[str, Any]] = []
    for line in section.splitlines():
        text = line.strip()
        match = DRIVE_LINE_RE.match(text)
        if match is None:
            continue
        rows.append(
            {
                "team_raw": match.group("team"),
                "quarter_raw": match.group("qtr"),
                "original_text": text,
            }
        )
    return rows


def parse_play_by_play(block: str) -> list[dict[str, Any]]:
    if PBP_RE.search(block) is None:
        return []
    rows: list[dict[str, Any]] = []
    for line in block.splitlines():
        text = line.strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered.startswith("play-by-play summary"):
            continue
        if re.match(r"^\d{4}\s+texas a", lowered):
            continue
        if re.match(r"^-{5,}$", text):
            continue
        if " vs " in lowered and " at " in lowered and not any(token in lowered for token in ("rush", "pass", "kick", "punt")):
            continue
        if not any(char.isalpha() for char in text):
            continue
        rows.append({"original_text": text})
    return rows


def _assign_labeled_blocks(blocks: list[str]) -> dict[str, list[str]]:
    assigned: dict[str, list[str]] = {domain: [] for domain in DOMAINS}
    unlabeled: list[str] = []
    for block in blocks:
        labeled = False
        if TEAM_FINAL_RE.search(block):
            assigned["team_statistics"].append(block)
            labeled = True
        if IND_FINAL_RE.search(block):
            assigned["individual_player_statistics"].append(block)
            labeled = True
        if DRIVE_FINAL_RE.search(block):
            assigned["drives"].append(block)
            labeled = True
        if PBP_RE.search(block):
            assigned["play_by_play"].append(block)
            labeled = True
        if not labeled:
            unlabeled.append(block)
    for block in unlabeled:
        if COMPACT_TEAM_RE.search(block) and not assigned["team_statistics"]:
            assigned["team_statistics"].append(block)
        if NARRATIVE_PRESENT_RE.search(block) and not assigned["individual_player_statistics"]:
            assigned["individual_player_statistics"].append(block)
    return assigned


def _unique_or_ambiguous(domain: str, blocks: list[str], parser) -> tuple[list[dict[str, Any]], str | None]:
    if not blocks:
        return [], None
    parsed = [parser(block) for block in blocks]
    nonempty = [rows for rows in parsed if rows]
    if not nonempty:
        return [], None
    if domain == "play_by_play":
        merged: list[dict[str, Any]] = []
        for rows in nonempty:
            merged.extend(rows)
        return merged, None
    first = nonempty[0]
    if domain == "team_statistics":
        fingerprint = _fingerprint_team_stats(first)
        for rows in nonempty[1:]:
            if _fingerprint_team_stats(rows) != fingerprint:
                return [], f"ambiguous {domain} table boundary"
        return first, None
    if len(nonempty) > 1:
        return [], f"ambiguous {domain} table boundary"
    return first, None


def parse_preformatted_page(
    body: bytes,
    *,
    url: str,
    source_season: int,
    raw_sha256: str,
) -> dict[str, Any]:
    validate_official_url(url)
    if sha256_bytes(body) != raw_sha256:
        raise AuthorityViolation("changed raw source hash")
    text = body.decode("latin-1", errors="replace")
    blocks = extract_pre_blocks(text)
    assigned = _assign_labeled_blocks(blocks)
    domain_rows: dict[str, list[dict[str, Any]]] = {}
    flags: dict[str, str] = {}
    warnings: list[str] = []
    parsers = {
        "team_statistics": parse_team_statistics,
        "individual_player_statistics": parse_player_statistics,
        "drives": parse_drives,
        "play_by_play": parse_play_by_play,
    }
    for domain in DOMAINS:
        rows, warning = _unique_or_ambiguous(domain, assigned[domain], parsers[domain])
        if warning:
            warnings.append(warning)
            domain_rows[domain] = []
            flags[domain] = "ABSENT"
            continue
        bound_rows = []
        for index, row in enumerate(rows):
            bound = dict(row)
            bound["row_order"] = index
            bound["source_url"] = url
            bound["source_sha256"] = raw_sha256
            bound["source_season"] = source_season
            bound["availability"] = "NOT_ESTABLISHED"
            bound_rows.append(bound)
        domain_rows[domain] = bound_rows
        flags[domain] = "PRESENT" if bound_rows else "ABSENT"
    coverage = dict(flags)
    if "player participation" in strip_markup(text).lower():
        coverage["participation"] = "PRESENT"
    else:
        coverage["participation"] = "ABSENT"
    return {
        "url": url,
        "source_sha256": raw_sha256,
        "source_season": source_season,
        "team_statistics": domain_rows["team_statistics"],
        "individual_player_statistics": domain_rows["individual_player_statistics"],
        "drives": domain_rows["drives"],
        "play_by_play": domain_rows["play_by_play"],
        "domain_coverage": coverage,
        "warnings": warnings,
        "preformatted_block_count": len(blocks),
        "rich_structured": is_rich_structured(coverage),
        "availability_claim": False,
        "ncaa_contest_id": None,
        "canonical_game_id": None,
        "historical_publication_time": None,
    }


def _load_captures(data_root: Path, relative: str, seasons: set[int]) -> list[dict[str, Any]]:
    path = data_root / relative
    if not path.is_file():
        raise AuthorityViolation(f"capture index missing: {relative}")
    rows = []
    for item in load_json(path).get("captures") or []:
        if int(item["source_season"]) not in seasons:
            continue
        rows.append(dict(item))
    return rows


def load_bound_captures(repo_root: Path, data_root: Path) -> list[dict[str, Any]]:
    inventory = load_json(repo_root / INVENTORY_GATE_RELATIVE)
    if inventory.get("inventory_identity") != INVENTORY_IDENTITY or inventory.get("gate_identity") != INVENTORY_GATE_IDENTITY:
        raise AuthorityViolation("BAT-585 inventory identity rewritten")
    pre2010 = load_json(repo_root / PRE2010_GATE_RELATIVE)
    if pre2010.get("gate_identity") != PRE2010_GATE_IDENTITY:
        raise AuthorityViolation("BAT-586 gate identity rewritten")
    if pre2010.get("dataset_identity") != PRE2010_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-586 dataset identity rewritten")
    if pre2010.get("acquisition_identity") != PRE2010_ACQUISITION_IDENTITY:
        raise AuthorityViolation("BAT-586 acquisition identity rewritten")
    box_2007 = load_json(repo_root / BOX_2007_GATE_RELATIVE)
    if box_2007.get("gate_identity") != BOX_2007_GATE_IDENTITY:
        raise AuthorityViolation("BAT-589 gate identity rewritten")
    if box_2007.get("dataset_identity") != BOX_2007_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-589 dataset identity rewritten")
    if box_2007.get("acquisition_identity") != BOX_2007_ACQUISITION_IDENTITY:
        raise AuthorityViolation("BAT-589 acquisition identity rewritten")
    captures = _load_captures(data_root, PRE2010_CAPTURE_INDEX, {2008, 2009})
    captures.extend(_load_captures(data_root, BOX_2007_CAPTURE_INDEX, {2007}))
    captures.sort(key=lambda item: (int(item["source_season"]), item["url"]))
    if len(captures) != 38:
        raise AuthorityViolation(f"expected 38 already-captured official 2007-2009 pages, found {len(captures)}")
    return captures


def _bind_rows(game: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for domain in DOMAINS:
        for item in game[domain]:
            rows.append({"domain": domain, **item})
    return rows


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    captures = load_bound_captures(repo_root, data_root)
    games: list[dict[str, Any]] = []
    for capture in captures:
        raw_path = data_root / capture["raw_relative_path"]
        if not raw_path.is_file():
            raise AuthorityViolation(f"captured raw page missing: {capture['raw_relative_path']}")
        body = raw_path.read_bytes()
        raw_sha256 = str(capture["raw_sha256"])
        if sha256_file(raw_path) != raw_sha256:
            raise AuthorityViolation("raw capture bytes do not match recorded SHA-256")
        parsed = parse_preformatted_page(
            body,
            url=validate_official_url(str(capture["url"])),
            source_season=int(capture["source_season"]),
            raw_sha256=raw_sha256,
        )
        games.append(parsed)
    for game in games:
        foreign = [
            row
            for other in games
            if other["url"] != game["url"]
            for row in other["individual_player_statistics"]
            if row.get("source_url") == game["url"]
        ]
        if foreign:
            raise AuthorityViolation("cross-game player identity leakage")
    season_coverage: dict[str, dict[str, dict[str, int]]] = {}
    for season in (2007, 2008, 2009):
        subset = [game for game in games if game["source_season"] == season]
        season_coverage[str(season)] = {}
        for domain in DOMAINS:
            present = sum(1 for game in subset if game["domain_coverage"][domain] == "PRESENT")
            season_coverage[str(season)][domain] = {
                "present_games": present,
                "absent_games": len(subset) - present,
            }
    coverage_counts = Counter()
    for game in games:
        for domain in DOMAINS:
            if game["domain_coverage"][domain] == "PRESENT":
                coverage_counts[domain] += 1
    compact_games = []
    for game in games:
        compact_games.append(
            {
                "url": game["url"],
                "source_sha256": game["source_sha256"],
                "source_season": game["source_season"],
                "domain_coverage": {domain: game["domain_coverage"][domain] for domain in DOMAINS},
                "row_counts": {domain: len(game[domain]) for domain in DOMAINS},
                "rich_structured": game["rich_structured"],
                "warnings": game["warnings"],
            }
        )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "source_id": SOURCE_ID,
        "games": games,
        "rows": [_bind_rows(game) for game in games],
        "admissions": {
            "bat_401": "DONE_VERIFIED_RETAIN_PROTECTED_LANE_BLOCKED",
            "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
            "bat_523": "IN_PROGRESS",
            "bat_586_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "bat_589_payload": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
            "gap_005": "OPEN",
            "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
            "ncaa_contest_identity": "NOT_CREATED",
            "participation_as_availability": "REJECTED",
            "name_only_player_merge": "REJECTED",
            "protected_lane": PROTECTED_LANE,
        },
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "protected_lane": PROTECTED_LANE,
    }
    payload["payload_identity"] = compute_identity(payload, "payload_identity")
    counts = {
        "target_games_total": 38,
        "parsed_games": len(games),
        "games_2007": sum(1 for game in games if game["source_season"] == 2007),
        "games_2008": sum(1 for game in games if game["source_season"] == 2008),
        "games_2009": sum(1 for game in games if game["source_season"] == 2009),
        "rich_structured_games": sum(1 for game in games if game["rich_structured"]),
        "metadata_only_games": sum(1 for game in games if not game["rich_structured"]),
        "ambiguous_boundary_games": sum(1 for game in games if game["warnings"]),
        "ncaa_contest_ids_created": 0,
        "name_only_player_merges": 0,
        "availability_claims": 0,
    }
    for domain in DOMAINS:
        counts[f"{domain}_present_games"] = int(coverage_counts[domain])
        counts[f"{domain}_absent_games"] = len(games) - int(coverage_counts[domain])
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "tamu_official_statcrew_preformatted_gate",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": "POST-TASK-SRC014-STATCREW-PREFORMATTED-001",
        "jira_key": "BAT-591",
        "disposition": "NEW_ENRICHED_PAYLOAD_PRIOR_IDENTITIES_PRESERVED",
        "source_id": SOURCE_ID,
        "inventory_identity": INVENTORY_IDENTITY,
        "payload_identity": payload["payload_identity"],
        "selected_seasons": [2007, 2008, 2009],
        "counts": counts,
        "season_domain_coverage": season_coverage,
        "games": compact_games,
        "admissions": payload["admissions"],
        "authority": payload["authority"],
        "scientific_nonclaims": payload["scientific_nonclaims"],
        "protected_lane": PROTECTED_LANE,
        "upstream_identities": {
            "inventory_identity": INVENTORY_IDENTITY,
            "inventory_gate_identity": INVENTORY_GATE_IDENTITY,
            "bat586_gate_identity": PRE2010_GATE_IDENTITY,
            "bat586_dataset_identity": PRE2010_DATASET_IDENTITY,
            "bat586_acquisition_identity": PRE2010_ACQUISITION_IDENTITY,
            "bat589_gate_identity": BOX_2007_GATE_IDENTITY,
            "bat589_dataset_identity": BOX_2007_DATASET_IDENTITY,
            "bat589_acquisition_identity": BOX_2007_ACQUISITION_IDENTITY,
        },
    }
    if counts["ncaa_contest_ids_created"] or gate["authority"]["ncaa_contest_identity"]:
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if any(game["availability_claim"] for game in games):
        raise AuthorityViolation("postgame participation treated as availability")
    gate["gate_identity"] = compute_gate_identity(gate)
    return {"contract": contract, "gate": gate, "payload": payload, "captures": captures}


def materialize(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    payload = objects["payload"]
    root = data_root / objects["contract"]["payloads"]["enriched_root"] / payload["payload_identity"]
    write_json(root / "payload.json", payload)
    write_json(repo_root / GATE_RELATIVE, objects["gate"])
    return {
        "gate_identity": objects["gate"]["gate_identity"],
        "payload_identity": payload["payload_identity"],
        "parsed_games": objects["gate"]["counts"]["parsed_games"],
    }


def lake_is_ready(data_root: Path) -> bool:
    return (data_root / PRE2010_CAPTURE_INDEX).is_file() and (data_root / BOX_2007_CAPTURE_INDEX).is_file()


def validate_compact_gate(committed: Mapping[str, Any]) -> None:
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("authority", {}).get("historical_known_at_from_capture_time"):
        raise AuthorityViolation("retrieval time promoted to historical known-at")
    if committed.get("counts", {}).get("ncaa_contest_ids_created"):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if committed.get("result") != PASS_RESULT or committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("completion or classification forged")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not recompute")
    if committed.get("inventory_identity") != INVENTORY_IDENTITY:
        raise AuthorityViolation("inventory identity rebound incorrectly")
    upstream = committed.get("upstream_identities") or {}
    if upstream.get("bat586_dataset_identity") != PRE2010_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-586 dataset identity rewritten")
    if upstream.get("bat589_dataset_identity") != BOX_2007_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-589 dataset identity rewritten")


def validate_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    gate: Mapping[str, Any] | None = None,
    require_rebuild: bool = True,
) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    validate_compact_gate(committed)
    ready = lake_is_ready(data_root)
    if require_rebuild and not ready:
        raise AuthorityViolation("external StatCrew reconstruction was required but the data root is not mounted")
    if not ready:
        return {
            "result": "PASS",
            "gate_identity": committed["gate_identity"],
            "external_reconstruction": "NOT_MOUNTED",
        }
    expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    if committed != expected["gate"]:
        raise AuthorityViolation("committed StatCrew preformatted gate does not match independent reconstruction")
    payload_path = (
        data_root
        / expected["contract"]["payloads"]["enriched_root"]
        / expected["payload"]["payload_identity"]
        / "payload.json"
    )
    if not payload_path.is_file():
        raise AuthorityViolation("external enriched payload missing")
    if load_json(payload_path) != expected["payload"]:
        raise AuthorityViolation("external enriched payload does not match reconstruction")
    return {
        "result": "PASS",
        "gate_identity": expected["gate"]["gate_identity"],
        "payload_identity": expected["payload"]["payload_identity"],
        "parsed_games": expected["gate"]["counts"]["parsed_games"],
        "external_reconstruction": "MOUNTED",
    }


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))

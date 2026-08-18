"""Bounded NCAA TAMU 2010-2011 team-season summary and roster evidence."""

from __future__ import annotations

import hashlib
import html
import importlib.util
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash


SCHEMA_VERSION = "aggie.data.tamu_2010_2011_ncaa_team_season_evidence.v1"
CONTRACT_RELATIVE = "configs/tamu_2010_2011_ncaa_team_season_evidence_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_2010_2011_ncaa_team_season_evidence_gate.json"
EVIDENCE_RELATIVE = "artifacts/jira_evidence/POST-TASK-TAMU-2010-2011-NCAA-TEAM-SEASON-EVIDENCE-001.json"
CONTRACT_ID = "BAT-574-TAMU-2010-2011-NCAA-TEAM-SEASON-EVIDENCE-V1"
PASS_CLASSIFICATION = "TAMU_2010_2011_NCAA_TEAM_SEASON_EVIDENCE_CANDIDATE_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
TAMU_SEEDS = {"2010": "137387", "2011": "137872"}
OFFICIAL_HOST = "stats.ncaa.org"
ALLOWED_PAGE_FAMILIES = ("team", "roster", "season_to_date_stats")
TABLE_RE = re.compile(r"(?is)<table\b[^>]*>(.*?)</table>")
ROW_RE = re.compile(r"(?is)(<tr\b[^>]*>.*?</tr>)")
CELL_RE = re.compile(r"(?is)<t[hd]\b[^>]*>(.*?)</t[hd]>")
NAV_RE = re.compile(
    r'(?is)<a\b[^>]*href=["\'](/teams/([0-9]+)(?:/(roster|season_to_date_stats))?)["\'][^>]*>(.*?)</a>'
)
TEAM_HREF_RE = re.compile(r'(?is)href=["\'](/teams/([0-9]+))["\']')
AGGIE_RECORD_RE = re.compile(
    r"Texas A&(?:amp;)?M Aggies</a>\s*\((\d+)\s*-\s*(\d+)(?:\s*-\s*(\d+))?\)",
    re.IGNORECASE,
)
RESULT_RE = re.compile(r"\b(?:(W|L|T)\s+)?(\d+)\s*-\s*(\d+)\b", re.IGNORECASE)
HARD_INTERSTITIAL_MARKERS = (
    "bm-verify",
    "_abck",
    "access denied",
    "reference #",
    "captcha",
    "enable javascript and cookies to continue",
)
SOFT_LOGIN_MARKERS = ("sign in", "log in")
GATE_IDENTITY_FIELDS = (
    "schema_version",
    "artifact_type",
    "result",
    "classification",
    "contract_id",
    "decision_unit",
    "jira_key",
    "disposition",
    "tamu_seeds",
    "page_identities",
    "counts",
    "domains",
    "attempts",
    "admissions",
    "authority",
    "scientific_nonclaims",
    "protected_lane",
)


class AuthorityViolation(ValueError):
    """Raised when team-season evidence is asked to invent identity or availability."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fragment_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", value))).strip()


def normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", fragment_text(value).lower()).strip("_")


def expected_authority() -> dict[str, bool]:
    return {
        "completeness_claim": False,
        "contest_id_fabrication": False,
        "name_only_promotion": False,
        "national_crawl": False,
        "id_range_sweep": False,
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
        "season_total_as_per_game_official": False,
        "tamu_specialization_lift_claims": False,
        "bas_or_aggie_excess_claims": False,
        "bat_554_reopen": False,
    }


def expected_scientific_nonclaims() -> dict[str, bool]:
    return {
        "completeness_claimed": False,
        "historical_known_at_established": False,
        "historical_population_ready": False,
        "pregame_availability_admitted": False,
        "roster_membership_used_as_availability": False,
        "participation_used_as_availability": False,
        "season_total_promoted_to_per_game_official": False,
        "protected_lane_opened": False,
        "protected_evaluation_admitted": False,
        "protected_outcome_authority": False,
        "protected_performance_claimed": False,
        "champion_or_production_promotion": False,
        "tamu_specialization_lift_claimed": False,
        "bas_or_aggie_excess_result_claimed": False,
        "trained_production_champion": False,
        "contest_ids_fabricated": False,
        "bat_554_reopened": False,
    }


def expected_admissions(disposition: str) -> dict[str, str]:
    return {
        "acquisition_admission": "CANDIDATE_ONLY",
        "disposition": disposition,
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "historical_known_at": "UNKNOWN_CAPTURE_TIME_ONLY",
        "roster_authority": "OFFICIAL_TEAM_SEASON_MEMBERSHIP_ONLY",
        "season_statistics_authority": "RETROSPECTIVE_UNLESS_HISTORICAL_KNOWN_AT_PROVEN",
        "bat_554": "RELATES_ONLY_DO_NOT_REOPEN",
        "bat_523": "IN_PROGRESS",
        "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
    }


def official_page_uri(team_season_id: str, page_family: str) -> str:
    if team_season_id not in TAMU_SEEDS.values():
        raise AuthorityViolation(f"unseeded team-season id {team_season_id}")
    if page_family == "team":
        path = f"/teams/{team_season_id}"
    elif page_family in {"roster", "season_to_date_stats"}:
        path = f"/teams/{team_season_id}/{page_family}"
    else:
        raise AuthorityViolation(f"unsupported page family {page_family}")
    return f"https://{OFFICIAL_HOST}{path}"


def validate_seeded_official_uri(value: str, team_season_id: str, page_family: str) -> None:
    expected = official_page_uri(team_season_id, page_family)
    if value != expected:
        raise AuthorityViolation(f"URI {value} is not the seeded official {page_family} route")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != OFFICIAL_HOST:
        raise AuthorityViolation("source URI must use the official HTTPS stats.ncaa.org host")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise AuthorityViolation("source URI must not contain credentials, a query, or a fragment")


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise AuthorityViolation("team-season evidence contract identity drift")
    if contract.get("tamu_seeds") != TAMU_SEEDS:
        raise AuthorityViolation("TAMU seeds drifted from the pinned 137387/137872 pair")
    if contract.get("bat_554_policy") != "RELATES_ONLY_DO_NOT_REOPEN":
        raise AuthorityViolation("BAT-554 reopen is forbidden")
    if contract.get("protected_split_registry_sha256") != (
        "6b90ef6fb09abd89d7a82a8b5835b00615671a7742839269c7401a2d0af5f764"
    ):
        raise AuthorityViolation("protected-split registry identity drift")
    for key, expected in expected_authority().items():
        if (contract.get("authority") or {}).get(key) is not expected:
            raise AuthorityViolation(f"contract authority {key} is not fail-closed")
    forbidden = set((contract.get("transport_reuse") or {}).get("forbidden_routes") or [])
    if forbidden != {"scrapfly", "scraperapi", "scraperapi_async"}:
        raise AuthorityViolation("credentialed scraper routes must remain forbidden")
    return contract


def reject_interstitial(body: bytes) -> None:
    lowered = body.decode("utf-8", "replace").lower()
    hard = [marker for marker in HARD_INTERSTITIAL_MARKERS if marker in lowered]
    if hard:
        raise AuthorityViolation(f"official response looked like a login or error page: {hard}")
    loginish = [marker for marker in SOFT_LOGIN_MARKERS if marker in lowered]
    bound = "ncaa" in lowered and ("texas a&m" in lowered or "texas a&amp;m" in lowered)
    if loginish and (not bound or len(body) < 4096):
        raise AuthorityViolation(f"official response looked like a login or error page: {loginish}")
    if len(body) < 1024:
        raise AuthorityViolation("official response was below the minimum HTML size")
    if "<html" not in lowered:
        raise AuthorityViolation("official response was not recognizable HTML")


def bind_team_season(body: bytes, team_season_id: str, season: int) -> dict[str, str]:
    text = body.decode("utf-8", "replace")
    lowered = text.lower()
    if "ncaa" not in lowered:
        raise AuthorityViolation("page lacked NCAA markers")
    if "texas a&m" not in lowered and "texas a&amp;m" not in lowered:
        raise AuthorityViolation("page lacked Texas A&M identity")
    if team_season_id not in text:
        raise AuthorityViolation("page lacked the seeded team-season binding")
    if str(season) not in text:
        raise AuthorityViolation("page lacked the expected season identity")
    return {"organization": "Texas A&M", "team_season_id": team_season_id, "season": str(season)}


def extract_official_nav_routes(body: bytes, team_season_id: str) -> dict[str, str]:
    routes: dict[str, str] = {}
    for path, found_id, family, _label in NAV_RE.findall(body.decode("utf-8", "replace")):
        if found_id != team_season_id:
            continue
        page_family = family or "team"
        if page_family not in ALLOWED_PAGE_FAMILIES:
            continue
        uri = f"https://{OFFICIAL_HOST}{path}"
        validate_seeded_official_uri(uri, team_season_id, page_family)
        routes[page_family] = uri
    required = {"team", "roster", "season_to_date_stats"}
    missing = sorted(required - set(routes))
    if missing:
        raise AuthorityViolation(f"official team page missing deterministic routes: {missing}")
    return routes


def parse_tables(body: bytes) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    for table_html in TABLE_RE.findall(body.decode("utf-8", "replace")):
        rows = ROW_RE.findall(table_html)
        if not rows:
            continue
        title = ""
        headers: list[str] = []
        data_rows: list[dict[str, Any]] = []
        for row in rows:
            cell_htmls = CELL_RE.findall(row)
            cells = [fragment_text(cell) for cell in cell_htmls]
            if not cells:
                continue
            row_lower = row.lower()
            if (len(cells) == 1 and ("heading" in row_lower or "colspan" in row_lower)) or (
                not headers and "heading" in row_lower and len(cells) == 1
            ):
                if not headers:
                    title = cells[0]
                continue
            if not headers and (
                "<th" in row_lower or "grey_heading" in row_lower or "heading" in row_lower
            ):
                headers = [normalize_header(cell) or f"column_{index}" for index, cell in enumerate(cells)]
                continue
            if not headers:
                headers = [normalize_header(cell) or f"column_{index}" for index, cell in enumerate(cells)]
                continue
            if len(cells) != len(headers):
                nonempty = [cell for cell in cells if cell]
                if len(cells) == 1 or not nonempty:
                    continue
                raise AuthorityViolation(f"table {title or headers} had a jagged row")
            mapped = {}
            for index, header in enumerate(headers):
                team_ids = [match[1] for match in TEAM_HREF_RE.findall(cell_htmls[index])]
                mapped[header] = {
                    "raw": cells[index],
                    "normalized": cells[index].strip(),
                    "official_team_season_ids": team_ids,
                }
            data_rows.append(mapped)
        if headers:
            tables.append({"title_raw": title, "headers": headers, "rows": data_rows})
    return tables


def _parse_result_cell(raw: str) -> dict[str, Any]:
    match = RESULT_RE.search(raw)
    if match is None:
        raise AuthorityViolation(f"unsupported result cell {raw!r}")
    score_for = int(match.group(2))
    score_against = int(match.group(3))
    if score_for > 200 or score_against > 200 or score_for < 0 or score_against < 0:
        raise AuthorityViolation(f"impossible score values in {raw!r}")
    letter = (match.group(1) or "").upper() or None
    if letter is None:
        if score_for > score_against:
            letter = "W"
            source = "DERIVED_FROM_OFFICIAL_SCORE"
        elif score_for < score_against:
            letter = "L"
            source = "DERIVED_FROM_OFFICIAL_SCORE"
        else:
            letter = "T"
            source = "DERIVED_FROM_OFFICIAL_SCORE"
    else:
        source = "EXPLICIT_RESULT_CODE"
    return {
        "raw": raw,
        "result_code": letter,
        "result_code_source": source,
        "points_for": score_for,
        "points_against": score_against,
    }


def parse_schedule_table(tables: list[Mapping[str, Any]], season: int) -> dict[str, Any]:
    schedule = next((table for table in tables if table.get("headers")[:3] == ["date", "opponent", "result"]), None)
    if schedule is None:
        raise AuthorityViolation("schedule table with Date/Opponent/Result headers was absent")
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    wins = losses = ties = points_for = points_against = 0
    for item in schedule["rows"]:
        date_raw = str(item["date"]["raw"])
        opponent_raw = str(item["opponent"]["raw"])
        result = _parse_result_cell(str(item["result"]["raw"]))
        try:
            game_date = datetime.strptime(date_raw, "%m/%d/%Y").date().isoformat()
        except ValueError as error:
            raise AuthorityViolation(f"unsupported schedule date {date_raw!r}") from error
        if int(game_date[:4]) not in {season, season + 1}:
            raise AuthorityViolation(f"schedule date {game_date} is outside season {season}")
        key = (game_date, opponent_raw, result["raw"])
        if key in seen:
            raise AuthorityViolation(f"duplicated schedule row {key}")
        seen.add(key)
        if result["result_code"] == "W":
            wins += 1
        elif result["result_code"] == "L":
            losses += 1
        elif result["result_code"] == "T":
            ties += 1
        points_for += int(result["points_for"])
        points_against += int(result["points_against"])
        opponent_ids = list(item["opponent"].get("official_team_season_ids") or [])
        rows.append(
            {
                "game_date_raw": date_raw,
                "game_date": game_date,
                "opponent_raw": opponent_raw,
                "opponent_normalized": re.sub(r"^@+\s*", "", opponent_raw).strip(),
                "opponent_team_season_id": opponent_ids[0] if len(opponent_ids) == 1 else None,
                "result_raw": result["raw"],
                "result_code": result["result_code"],
                "result_code_source": result["result_code_source"],
                "points_for": result["points_for"],
                "points_against": result["points_against"],
                "contest_id": None,
            }
        )
    derived = any(row["result_code_source"] == "DERIVED_FROM_OFFICIAL_SCORE" for row in rows)
    return {
        "table_title": schedule.get("title_raw") or "Schedule/Results",
        "row_count": len(rows),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "points_for": points_for,
        "points_against": points_against,
        "result_code_source": "MIXED_OR_DERIVED" if derived else "EXPLICIT_RESULT_CODE",
        "rows": rows,
    }


def parse_header_record(body: bytes) -> dict[str, int] | None:
    match = AGGIE_RECORD_RE.search(body.decode("utf-8", "replace"))
    if match is None:
        return None
    return {
        "wins": int(match.group(1)),
        "losses": int(match.group(2)),
        "ties": int(match.group(3) or 0),
        "raw": match.group(0),
    }


def parse_roster_tables(tables: list[Mapping[str, Any]]) -> dict[str, Any]:
    roster_tables = [
        table
        for table in tables
        if any(header in {"name", "player", "roster"} or "name" in header for header in table["headers"])
        and any(header in {"pos", "position", "yr", "class", "ht", "height", "no", "number", "jersey"} for header in table["headers"])
    ]
    if not roster_tables:
        raise AuthorityViolation("roster page lacked a header-mapped player table")
    members: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for table in roster_tables:
        for item in table["rows"]:
            raw_values = tuple(str(cell["raw"]) for cell in item.values())
            if raw_values in seen:
                raise AuthorityViolation(f"duplicated roster row {raw_values}")
            seen.add(raw_values)
            members.append(
                {
                    "table_title": table.get("title_raw") or "",
                    "fields": item,
                    "availability": "NOT_ESTABLISHED",
                    "authority": "OFFICIAL_TEAM_SEASON_MEMBERSHIP_ONLY",
                }
            )
    return {
        "table_count": len(roster_tables),
        "row_count": len(members),
        "members": members,
        "pregame_availability": "NOT_ESTABLISHED",
    }


def parse_stat_tables(tables: list[Mapping[str, Any]]) -> dict[str, Any]:
    if not tables:
        raise AuthorityViolation("season-to-date page contained no tables")
    recovered: list[dict[str, Any]] = []
    for table in tables:
        if not table["headers"]:
            raise AuthorityViolation("season-to-date table lacked headers")
        recovered.append(
            {
                "table_title": table.get("title_raw") or "",
                "headers": table["headers"],
                "row_count": len(table["rows"]),
                "rows": table["rows"],
                "temporal_class": "RETROSPECTIVE_UNLESS_HISTORICAL_KNOWN_AT_PROVEN",
                "per_game_official": False,
            }
        )
    return {
        "table_count": len(recovered),
        "row_count": sum(item["row_count"] for item in recovered),
        "tables": recovered,
        "pregame_availability": "NOT_ESTABLISHED",
        "per_game_box_authority": False,
    }


def classify_page(page_family: str, captured: bool, blocked: bool) -> str:
    if captured and page_family == "team":
        return "VERIFIED_OFFICIAL_SEASON_LEVEL"
    if captured and page_family == "roster":
        return "VERIFIED_OFFICIAL_SEASON_LEVEL"
    if captured and page_family == "season_to_date_stats":
        return "VERIFIED_OFFICIAL_SEASON_LEVEL"
    if blocked:
        return "OFFICIAL_ROUTE_ACCESS_BLOCKED"
    return "SOURCE_EVIDENCE_ABSENT"


def _acquire_mod() -> Any:
    path = Path(__file__).resolve().parents[3] / "tools" / "acquire_ncaa_official_gamebooks.py"
    spec = importlib.util.spec_from_file_location("acquire_ncaa_official_gamebooks_bat574", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load acquire_ncaa_official_gamebooks.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def direct_http_get(url: str, timeout_seconds: float = 30.0) -> dict[str, Any]:
    validate_seeded_official_uri(url, urlsplit(url).path.split("/")[2], _family_from_url(url))
    request = urllib.request.Request(
        url,
        headers={"Accept": "text/html,application/xhtml+xml", "User-Agent": "Mozilla/5.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
            retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            return {
                "url": url,
                "method": "GET",
                "timestamp": retrieved_at,
                "status": int(response.status),
                "content_type": response.headers.get("Content-Type"),
                "final_url": response.geturl(),
                "redirect_chain": [url] if response.geturl() == url else [url, response.geturl()],
                "response_sha256": sha256_bytes(body),
                "retrieval_route": "direct_http",
                "body": body,
            }
    except urllib.error.HTTPError as error:
        body = error.read()
        retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return {
            "url": url,
            "method": "GET",
            "timestamp": retrieved_at,
            "status": int(error.code),
            "content_type": error.headers.get("Content-Type") if error.headers else None,
            "final_url": url,
            "redirect_chain": [url],
            "response_sha256": sha256_bytes(body),
            "retrieval_route": "direct_http",
            "body": body,
        }


def _family_from_url(url: str) -> str:
    path = urlsplit(url).path
    if path.endswith("/roster"):
        return "roster"
    if path.endswith("/season_to_date_stats"):
        return "season_to_date_stats"
    return "team"


def browser_get(url: str, data_root: Path, repo_root: Path) -> dict[str, Any]:
    acquire = _acquire_mod()
    from aggie_analytics.data.adapters import AcquisitionRequest

    validate_seeded_official_uri(url, urlsplit(url).path.split("/")[2], _family_from_url(url))
    transport = acquire.LocalChromeTransport(
        executable_path=Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        profile_root=data_root / "runtime" / "BAT-574" / "chrome",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
        ),
        wait_after_load_milliseconds=8000,
        timeout_seconds=90.0,
        solve_attempts=2,
    )
    request = AcquisitionRequest(
        source_id="SRC-015",
        dataset="ncaa_team_season_evidence",
        source_uri=url,
        identity_components={"decision_unit": "POST-TASK-TAMU-2010-2011-NCAA-TEAM-SEASON-EVIDENCE-001"},
        extension=".html",
    )
    try:
        response = transport(request)
    except Exception as error:
        retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return {
            "url": url,
            "method": "GET",
            "timestamp": retrieved_at,
            "status": 0,
            "content_type": None,
            "final_url": url,
            "redirect_chain": [url],
            "response_sha256": None,
            "retrieval_route": "local_patchright_chrome",
            "error": f"{type(error).__name__}: {error}",
            "body": b"",
        }
    body = response.body
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "url": url,
        "method": "GET",
        "timestamp": retrieved_at,
        "status": int(response.status_code),
        "content_type": (response.headers or {}).get("content-type"),
        "final_url": url,
        "redirect_chain": [url],
        "response_sha256": sha256_bytes(body),
        "retrieval_route": "local_patchright_chrome",
        "body": body,
    }


def load_cached_page(data_root: Path, spec: Mapping[str, Any]) -> dict[str, Any]:
    path = data_root / spec["raw_relative_path"]
    if not path.is_file():
        raise FileNotFoundError(f"cached official page missing: {path}")
    digest = sha256_file(path)
    if digest != spec["raw_sha256"]:
        raise AuthorityViolation(f"cached official page hash drift: {digest}")
    body = path.read_bytes()
    reject_interstitial(body)
    return {
        "url": spec["source_uri"],
        "method": "GET",
        "timestamp": None,
        "status": 200,
        "content_type": "text/html",
        "final_url": spec["source_uri"],
        "redirect_chain": [spec["source_uri"]],
        "response_sha256": digest,
        "retrieval_route": "existing_lake_html",
        "cache_disposition": "REUSED_VERIFIED_LAKE_HTML",
        "raw_relative_path": spec["raw_relative_path"],
        "body": body,
    }


def _compact_attempt(capture: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in capture.items() if key != "body"}


def open_stateful_browser(data_root: Path) -> Any:
    acquire = _acquire_mod()
    session = acquire.StatefulPatchrightSession(
        executable_path=Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        browser_installation_root=None,
        runtime_root=data_root / "runtime" / "BAT-574" / "chrome_session",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
        ),
        challenge_wait_milliseconds=8000,
        timeout_seconds=90.0,
        solve_attempts=3,
    )
    return session.__enter__()


def stateful_browser_get(session: Any, url: str) -> dict[str, Any]:
    validate_seeded_official_uri(url, urlsplit(url).path.split("/")[2], _family_from_url(url))
    try:
        response = session.fetch(url)
    except Exception as error:
        retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return {
            "url": url,
            "method": "GET",
            "timestamp": retrieved_at,
            "status": 0,
            "content_type": None,
            "final_url": url,
            "redirect_chain": [url],
            "response_sha256": None,
            "retrieval_route": "stateful_patchright_chrome",
            "error": f"{type(error).__name__}: {error}",
            "body": b"",
        }
    body = response.body
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "url": url,
        "method": "GET",
        "timestamp": retrieved_at,
        "status": int(response.status_code),
        "content_type": (response.headers or {}).get("content-type") or "text/html",
        "final_url": url,
        "redirect_chain": [url],
        "response_sha256": sha256_bytes(body),
        "retrieval_route": "stateful_patchright_chrome",
        "body": body,
    }


def store_raw(data_root: Path, contract: Mapping[str, Any], body: bytes) -> dict[str, str]:
    digest = sha256_bytes(body)
    relative = f"{contract['payloads']['raw_root']}/{digest}.html"
    path = data_root / relative
    if path.exists() and sha256_file(path) != digest:
        raise AuthorityViolation(f"raw path collision for {digest}")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    return {"raw_relative_path": relative, "raw_sha256": digest}


def compute_gate_identity(payload: Mapping[str, Any]) -> str:
    return stable_hash({field: payload.get(field) for field in GATE_IDENTITY_FIELDS})


def _page_payload(
    *,
    season: int,
    team_season_id: str,
    page_family: str,
    capture: Mapping[str, Any],
    parsed: Mapping[str, Any] | None,
    classification: str,
) -> dict[str, Any]:
    return {
        "season": season,
        "team_season_id": team_season_id,
        "page_family": page_family,
        "source_uri": capture.get("url"),
        "method": capture.get("method"),
        "timestamp": capture.get("timestamp"),
        "status": capture.get("status"),
        "content_type": capture.get("content_type"),
        "redirect_chain": capture.get("redirect_chain"),
        "response_sha256": capture.get("response_sha256"),
        "retrieval_route": capture.get("retrieval_route"),
        "cache_disposition": capture.get("cache_disposition") or "LIVE_OR_BLOCKED",
        "raw_relative_path": capture.get("raw_relative_path"),
        "classification": classification,
        "parsed": parsed,
        "pregame_availability_eligible": False,
        "development_pit_eligible": page_family == "team" and classification == "VERIFIED_OFFICIAL_SEASON_LEVEL",
        "bat523_consumable": True,
    }


def rebuild_expected(
    *,
    data_root: Path,
    repo_root: Path,
    allow_live: bool = False,
    issued_at_utc: str = "2026-08-18T18:10:00Z",
) -> dict[str, Any]:
    contract = load_contract(repo_root)
    attempts: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    domains = {
        "schedule_game_count": {},
        "wins_losses_ties": {},
        "points_for_against": {},
        "roster_membership": {},
        "team_season_statistics": {},
        "player_season_statistics": {},
        "pregame_availability": {
            "2010": "TEMPORALLY_INELIGIBLE_FOR_PREGAME_USE",
            "2011": "TEMPORALLY_INELIGIBLE_FOR_PREGAME_USE",
        },
    }
    browser_session = None
    try:
        for season in (2010, 2011):
            seed = TAMU_SEEDS[str(season)]
            team_capture = load_cached_page(data_root, contract["lake_html"][str(season)])
            bind_team_season(team_capture["body"], seed, season)
            routes = extract_official_nav_routes(team_capture["body"], seed)
            tables = parse_tables(team_capture["body"])
            schedule = parse_schedule_table(tables, season)
            header_record = parse_header_record(team_capture["body"])
            header_conflict = bool(
                header_record
                and (
                    header_record["wins"] != schedule["wins"]
                    or header_record["losses"] != schedule["losses"]
                    or header_record["ties"] != schedule["ties"]
                )
            )
            wl_class = (
                "CONFLICT_REVIEW_REQUIRED" if header_conflict else "VERIFIED_OFFICIAL_SEASON_LEVEL"
            )
            team_parsed = {
                "binding": {"organization": "Texas A&M", "team_season_id": seed, "season": season},
                "official_routes": routes,
                "header_record": header_record,
                "header_schedule_record_agreement": (
                    "CONFLICT_REVIEW_REQUIRED" if header_conflict else "AGREES"
                ),
                "schedule": {key: value for key, value in schedule.items() if key != "rows"},
                "schedule_rows": schedule["rows"],
                "table_count": len(tables),
            }
            pages.append(
                _page_payload(
                    season=season,
                    team_season_id=seed,
                    page_family="team",
                    capture=team_capture,
                    parsed=team_parsed,
                    classification="VERIFIED_OFFICIAL_SEASON_LEVEL",
                )
            )
            domains["schedule_game_count"][str(season)] = {
                "value": schedule["row_count"],
                "classification": "VERIFIED_OFFICIAL_SEASON_LEVEL",
            }
            domains["wins_losses_ties"][str(season)] = {
                "value": {"wins": schedule["wins"], "losses": schedule["losses"], "ties": schedule["ties"]},
                "source": schedule["result_code_source"],
                "header_record": header_record,
                "classification": wl_class,
            }
            domains["points_for_against"][str(season)] = {
                "value": {"points_for": schedule["points_for"], "points_against": schedule["points_against"]},
                "classification": "VERIFIED_OFFICIAL_SEASON_LEVEL",
            }
            for page_family in ("roster", "season_to_date_stats"):
                url = routes[page_family]
                raw_root = data_root / contract["payloads"]["raw_root"]
                cached_hits = sorted(raw_root.glob("*.html")) if raw_root.is_dir() else []
                reused = None
                for cached_path in cached_hits:
                    body = cached_path.read_bytes()
                    try:
                        reject_interstitial(body)
                        bind_team_season(body, seed, season)
                        decoded = body.decode("utf-8", "replace")
                        if page_family == "roster" and "/roster" not in decoded:
                            continue
                        if page_family == "season_to_date_stats" and "season_to_date_stats" not in decoded:
                            continue
                        reused = {
                            "url": url,
                            "method": "GET",
                            "timestamp": None,
                            "status": 200,
                            "content_type": "text/html",
                            "final_url": url,
                            "redirect_chain": [url],
                            "response_sha256": sha256_file(cached_path),
                            "retrieval_route": "existing_lake_html",
                            "cache_disposition": "REUSED_VERIFIED_LAKE_HTML",
                            "raw_relative_path": cached_path.relative_to(data_root).as_posix(),
                            "body": body,
                        }
                        break
                    except AuthorityViolation:
                        continue
                capture = reused
                blocked_store: dict[str, str] | None = None
                if capture is None and allow_live:
                    http = direct_http_get(url)
                    if http.get("body"):
                        blocked_store = store_raw(data_root, contract, http["body"])
                        http.update(blocked_store)
                    attempts.append(_compact_attempt(http))
                    usable = 200 <= int(http["status"]) < 300
                    if usable:
                        try:
                            reject_interstitial(http["body"])
                            bind_team_season(http["body"], seed, season)
                            capture = http
                            capture["cache_disposition"] = "LIVE_HTTP_STORED"
                        except AuthorityViolation:
                            usable = False
                    if capture is None:
                        if browser_session is None:
                            browser_session = open_stateful_browser(data_root)
                        browser = stateful_browser_get(browser_session, url)
                        if browser.get("body"):
                            blocked_store = store_raw(data_root, contract, browser["body"])
                            browser.update(blocked_store)
                        attempts.append(_compact_attempt(browser))
                        if 200 <= int(browser.get("status") or 0) < 300 and browser.get("body"):
                            try:
                                reject_interstitial(browser["body"])
                                bind_team_season(browser["body"], seed, season)
                                capture = browser
                                capture["cache_disposition"] = "LIVE_BROWSER_STORED"
                            except AuthorityViolation:
                                capture = None
                if capture is None:
                    pages.append(
                        _page_payload(
                            season=season,
                            team_season_id=seed,
                            page_family=page_family,
                            capture={
                                "url": url,
                                "method": "GET",
                                "timestamp": (attempts[-1]["timestamp"] if attempts else None),
                                "status": (attempts[-1]["status"] if attempts else None),
                                "content_type": "text/html",
                                "redirect_chain": [url],
                                "response_sha256": (blocked_store or {}).get("raw_sha256"),
                                "retrieval_route": "direct_http_then_stateful_patchright_chrome"
                                if allow_live
                                else "none",
                                "cache_disposition": "BLOCKED_RESPONSE_STORED"
                                if blocked_store
                                else "NO_VERIFIED_CACHE_LIVE_BLOCKED_OR_NOT_ATTEMPTED",
                                "raw_relative_path": (blocked_store or {}).get("raw_relative_path"),
                            },
                            parsed=None,
                            classification="OFFICIAL_ROUTE_ACCESS_BLOCKED"
                            if allow_live
                            else "SOURCE_EVIDENCE_ABSENT",
                        )
                    )
                    domain_key = "roster_membership" if page_family == "roster" else "team_season_statistics"
                    pages_class = "OFFICIAL_ROUTE_ACCESS_BLOCKED" if allow_live else "SOURCE_EVIDENCE_ABSENT"
                    domains[domain_key][str(season)] = {"classification": pages_class, "row_count": 0}
                    if page_family == "season_to_date_stats":
                        domains["player_season_statistics"][str(season)] = {
                            "classification": pages_class,
                            "row_count": 0,
                        }
                    continue
                parsed: dict[str, Any]
                if page_family == "roster":
                    parsed = parse_roster_tables(parse_tables(capture["body"]))
                    domains["roster_membership"][str(season)] = {
                        "classification": "VERIFIED_OFFICIAL_SEASON_LEVEL",
                        "row_count": parsed["row_count"],
                        "pregame_availability": "TEMPORALLY_INELIGIBLE_FOR_PREGAME_USE",
                    }
                else:
                    parsed = parse_stat_tables(parse_tables(capture["body"]))
                    domains["team_season_statistics"][str(season)] = {
                        "classification": "VERIFIED_OFFICIAL_SEASON_LEVEL",
                        "row_count": parsed["row_count"],
                        "temporal_class": "RETROSPECTIVE_UNLESS_HISTORICAL_KNOWN_AT_PROVEN",
                        "per_game_official": False,
                    }
                    domains["player_season_statistics"][str(season)] = {
                        "classification": "VERIFIED_OFFICIAL_SEASON_LEVEL"
                        if parsed["row_count"]
                        else "SOURCE_EVIDENCE_ABSENT",
                        "row_count": parsed["row_count"],
                        "temporal_class": "RETROSPECTIVE_UNLESS_HISTORICAL_KNOWN_AT_PROVEN",
                    }
                pages.append(
                    _page_payload(
                        season=season,
                        team_season_id=seed,
                        page_family=page_family,
                        capture=capture,
                        parsed=parsed,
                        classification="VERIFIED_OFFICIAL_SEASON_LEVEL",
                    )
                )
    finally:
        if browser_session is not None:
            browser_session.__exit__(None, None, None)
    captured_optional = sum(
        1
        for page in pages
        if page["page_family"] in {"roster", "season_to_date_stats"}
        and page["classification"] == "VERIFIED_OFFICIAL_SEASON_LEVEL"
    )
    if captured_optional == 4:
        disposition = "TEAM_SEASON_PAGE_FAMILIES_CAPTURED"
    elif captured_optional:
        disposition = "PARTIAL_TEAM_SEASON_PAGE_FAMILIES_CAPTURED"
    else:
        disposition = "TEAM_PAGE_REUSED_OPTIONAL_ROUTES_BLOCKED"
    page_identities = {
        f"{page['season']}_{page['page_family']}": (
            page.get("response_sha256")
            if page["classification"] == "VERIFIED_OFFICIAL_SEASON_LEVEL"
            else None
        )
        for page in pages
    }
    blocked_response_identities = {
        f"{page['season']}_{page['page_family']}": page.get("response_sha256")
        for page in pages
        if page["classification"] != "VERIFIED_OFFICIAL_SEASON_LEVEL" and page.get("response_sha256")
    }
    counts = {
        "seasons": 2,
        "official_routes_attempted": len(attempts),
        "team_pages_reused": 2,
        "roster_pages_captured": sum(
            1
            for page in pages
            if page["page_family"] == "roster" and page["classification"] == "VERIFIED_OFFICIAL_SEASON_LEVEL"
        ),
        "season_stat_pages_captured": sum(
            1
            for page in pages
            if page["page_family"] == "season_to_date_stats"
            and page["classification"] == "VERIFIED_OFFICIAL_SEASON_LEVEL"
        ),
        "schedule_rows_2010": domains["schedule_game_count"]["2010"]["value"],
        "schedule_rows_2011": domains["schedule_game_count"]["2011"]["value"],
        "contest_ids_fabricated": 0,
        "availability_features": 0,
    }
    core = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_2010_2011_NCAA_TEAM_SEASON_EVIDENCE_MANIFEST",
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "run_id": contract["run_id"],
        "tamu_seeds": dict(TAMU_SEEDS),
        "disposition": disposition,
        "page_identities": page_identities,
        "blocked_response_identities": blocked_response_identities,
        "counts": counts,
        "domains": domains,
        "pages": [
            {key: value for key, value in page.items() if key != "parsed"}
            | {"parsed": page.get("parsed")}
            for page in pages
        ],
        "attempts": attempts,
        "admissions": expected_admissions(disposition),
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "protected_lane": PROTECTED_LANE,
        "issued_at_utc": issued_at_utc,
    }
    identity = stable_hash({key: core[key] for key in ("schema_version", "pages", "domains", "tamu_seeds")})
    core["manifest_identity"] = identity
    return core


def expected_gate_document(core: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_2010_2011_NCAA_TEAM_SEASON_EVIDENCE_GATE",
        "result": {
            "TEAM_SEASON_PAGE_FAMILIES_CAPTURED": "PASS_TEAM_SEASON_PAGE_FAMILIES_CAPTURED",
            "PARTIAL_TEAM_SEASON_PAGE_FAMILIES_CAPTURED": "PASS_PARTIAL_TEAM_SEASON_PAGE_FAMILIES_CAPTURED",
            "TEAM_PAGE_REUSED_OPTIONAL_ROUTES_BLOCKED": "PASS_TEAM_PAGE_REUSED_OPTIONAL_ROUTES_BLOCKED",
        }[str(core["disposition"])],
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": core["decision_unit"],
        "jira_key": core["jira_key"],
        "disposition": core["disposition"],
        "tamu_seeds": core["tamu_seeds"],
        "page_identities": core["page_identities"],
        "blocked_response_identities": core.get("blocked_response_identities") or {},
        "counts": core["counts"],
        "domains": core["domains"],
        "attempts": core.get("attempts") or [],
        "admissions": core["admissions"],
        "authority": core["authority"],
        "scientific_nonclaims": core["scientific_nonclaims"],
        "protected_lane": PROTECTED_LANE,
        "manifest_identity": core["manifest_identity"],
        "payload": payload,
        "issued_at_utc": core["issued_at_utc"],
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    return gate


def materialize(
    *,
    data_root: Path,
    repo_root: Path,
    issued_at_utc: str,
    allow_live: bool = True,
) -> dict[str, Any]:
    core = rebuild_expected(
        data_root=data_root,
        repo_root=repo_root,
        allow_live=allow_live,
        issued_at_utc=issued_at_utc,
    )
    identity = core["manifest_identity"]
    payload_dir = data_root / "features" / "tamu_2010_2011_ncaa_team_season_evidence" / "sha256" / identity
    payload_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = payload_dir / "tamu_2010_2011_ncaa_team_season_evidence_manifest.json"
    write_json(manifest_path, core)
    payload = {
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "manifest_relative_path": manifest_path.relative_to(data_root).as_posix(),
    }
    gate = expected_gate_document(core, payload)
    write_json(repo_root / GATE_RELATIVE, gate)
    return {"gate": gate, "core": core, "payload": payload}


ALLOWED_RESULTS = {
    "PASS_TEAM_SEASON_PAGE_FAMILIES_CAPTURED",
    "PASS_PARTIAL_TEAM_SEASON_PAGE_FAMILIES_CAPTURED",
    "PASS_TEAM_PAGE_REUSED_OPTIONAL_ROUTES_BLOCKED",
}


def validate_artifact(
    *,
    data_root: Path,
    repo_root: Path,
    require_rebuild: bool = True,
    gate: Mapping[str, Any] | None = None,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    del expected
    committed = dict(gate or load_json(repo_root / GATE_RELATIVE))
    contract = load_contract(repo_root)
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("classification drifted")
    if committed.get("result") not in ALLOWED_RESULTS:
        raise AuthorityViolation("result is not an allowed team-season evidence result")
    if committed["tamu_seeds"] != TAMU_SEEDS:
        raise AuthorityViolation("committed seeds drifted")
    if committed["authority"] != expected_authority():
        raise AuthorityViolation("committed authority drifted")
    if committed["scientific_nonclaims"] != expected_scientific_nonclaims():
        raise AuthorityViolation("committed nonclaims drifted")
    if committed["protected_lane"] != PROTECTED_LANE:
        raise AuthorityViolation("protected lane drifted")
    if any(committed["authority"].values()):
        raise AuthorityViolation("authority claim was opened")
    if committed["scientific_nonclaims"]["roster_membership_used_as_availability"]:
        raise AuthorityViolation("roster membership was promoted to availability")
    if committed["scientific_nonclaims"]["participation_used_as_availability"]:
        raise AuthorityViolation("participation was promoted to availability")
    if committed["counts"]["contest_ids_fabricated"] != 0:
        raise AuthorityViolation("contest IDs were fabricated")
    if committed["counts"]["availability_features"] != 0:
        raise AuthorityViolation("availability features were admitted")
    if committed["page_identities"].get("2010_team") != (
        "3cdb205a98242b335cc742a81ddbc66f4352bf0ce68387130d17534e5f3712d7"
    ):
        raise AuthorityViolation("2010 team page identity drifted")
    if committed["page_identities"].get("2011_team") != (
        "aa332e8213295ca49a09899d72e5549484d81c1dc566599064c9ac0d0096dac3"
    ):
        raise AuthorityViolation("2011 team page identity drifted")
    rebuilt_identity = compute_gate_identity(committed)
    if committed.get("gate_identity") != rebuilt_identity:
        raise AuthorityViolation("gate identity does not reconstruct from authority-bearing fields")
    if require_rebuild:
        for season in ("2010", "2011"):
            spec = contract["lake_html"][season]
            capture = load_cached_page(data_root, spec)
            bind_team_season(capture["body"], TAMU_SEEDS[season], int(season))
            schedule = parse_schedule_table(parse_tables(capture["body"]), int(season))
            committed_count = committed["domains"]["schedule_game_count"][season]["value"]
            if committed_count != schedule["row_count"]:
                raise AuthorityViolation(f"{season} schedule count drifted")
            if schedule["row_count"] != 13:
                raise AuthorityViolation(f"{season} schedule is not the 13-game official table")
            for optional in ("roster", "season_to_date_stats"):
                digest = committed["page_identities"].get(f"{season}_{optional}")
                domain_key = "roster_membership" if optional == "roster" else "team_season_statistics"
                classification = committed["domains"][domain_key][season]["classification"]
                if digest:
                    raw_path = data_root / contract["payloads"]["raw_root"] / f"{digest}.html"
                    if not raw_path.is_file():
                        raise AuthorityViolation(f"missing content-addressed {season} {optional} payload")
                    if sha256_file(raw_path) != digest:
                        raise AuthorityViolation(f"{season} {optional} payload hash drift")
                    body = raw_path.read_bytes()
                    reject_interstitial(body)
                    bind_team_season(body, TAMU_SEEDS[season], int(season))
                    if classification != "VERIFIED_OFFICIAL_SEASON_LEVEL":
                        raise AuthorityViolation(f"{season} {optional} identity present but not verified")
                elif classification == "VERIFIED_OFFICIAL_SEASON_LEVEL":
                    raise AuthorityViolation(f"{season} {optional} verified without an identity")
        payload = committed.get("payload") or {}
        manifest_path = Path(str(payload.get("manifest") or ""))
        if not manifest_path.is_file():
            raise AuthorityViolation("bulk payload manifest is missing")
        if sha256_file(manifest_path) != payload.get("manifest_sha256"):
            raise AuthorityViolation("bulk payload hash drift")
        manifest = load_json(manifest_path)
        if manifest.get("manifest_identity") != committed.get("manifest_identity"):
            raise AuthorityViolation("bulk manifest identity drifted")
        if manifest.get("tamu_seeds") != TAMU_SEEDS:
            raise AuthorityViolation("bulk manifest seeds drifted")
    return {"result": "PASS", "gate_identity": committed["gate_identity"]}

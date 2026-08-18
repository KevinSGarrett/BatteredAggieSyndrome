"""Official Texas A&M 2010-2011 historical-archive acquisition (SRC-014 school evidence)."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urljoin, urlsplit

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash


SCHEMA_VERSION = "aggie.data.tamu_official_historical_archive.v1"
CONTRACT_RELATIVE = "configs/tamu_official_historical_archive_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_historical_archive_gate.json"
EVIDENCE_RELATIVE = "artifacts/jira_evidence/POST-TASK-CYCLE-9-OFFICIAL-HISTORICAL-ARCHIVE-001.json"
CONTRACT_ID = "BAT-579-TAMU-OFFICIAL-HISTORICAL-ARCHIVE-V1"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_2010_2011_OFFICIAL_SCHOOL_HISTORICAL_ARCHIVE_CANDIDATE_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
OFFICIAL_HOSTS = frozenset({"files.12thman.com", "12thman.com", "www.12thman.com"})
WMT_ACQUISITION_IDENTITY = "d227b6cfca71ad0e6d514fa707f7d23a4a6a59374142352a016202c3bd2f25b3"
WMT_DATASET_IDENTITY = "76c3b366431d5085588d07df7d8db77348ac737dc57538befe26c7080150f010"
WMT_GATE_RELATIVE = "artifacts/pit/historical_tamu_official_gamebook_reconciliation_gate.json"
RAW_ROOT = "raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive"
PINNED_CAPTURES_IDENTITY = "32ddc9948b8d968110687b49b15c047a348d70f500050be6cd406c225708425b"
PINNED_BOX_URLS_IDENTITY = "b84868121549673b3c0dbe763e74d33832b6a2dd34b87c2a5ed6e42e7841fb00"
PINNED_ROSTER_ROWS = {"2010": 116, "2011": 119}
ANCHOR_RE = re.compile(r'(?is)<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>')
TABLE_RE = re.compile(r"(?is)<table\b[^>]*>(.*?)</table>")
ROW_RE = re.compile(r"(?is)<tr\b[^>]*>(.*?)</tr>")
CELL_RE = re.compile(r"(?is)<t[hd]\b[^>]*>(.*?)</t[hd]>")
BOX_PATH_RE = re.compile(
    r"^/history/football/stats/(2010-2011|2011-2012)/ta(\d{2})-[a-z0-9]+\.html?$",
    re.IGNORECASE,
)
RECAP_PATH_RE = re.compile(
    r"^/history/football/recaps/(2010-2011|2011-2012)/ta(\d{2})-[a-z0-9]+\.html?$",
    re.IGNORECASE,
)
SEASON_STAT_PATH_RE = re.compile(
    r"^/history/football/stats/(2010-2011|2011-2012)/(teamcume|teamgbg)\.html?$",
    re.IGNORECASE,
)
DOCUMENT_PATH_RE = re.compile(r"^/documents/[0-9a-f-]{36}\.pdf$", re.IGNORECASE)
SIDEARM_SEASON_PATH_RE = re.compile(r"^/sports/football/stats/season/(2010|2011)/?$", re.IGNORECASE)
UNRELATED_SPORT_MARKERS = (
    "sports/baseball",
    "sports/mens-basketball",
    "sports/womens-basketball",
    "sports/softball",
    "sports/soccer",
    "sports/volleyball",
)
HARD_INTERSTITIAL_MARKERS = (
    "bm-verify",
    "_abck",
    "access denied",
    "reference #",
    "captcha",
    "enable javascript and cookies to continue",
)
SOFT_LOGIN_MARKERS = ("sign in", "log in")
SEED_URLS = (
    ("history_index", None, "https://files.12thman.com/history/football/history/index.html"),
    ("season_index", 2010, "https://files.12thman.com/history/football/years/2010.html"),
    ("season_index", 2011, "https://files.12thman.com/history/football/years/2011.html"),
    ("rosters", 2010, "https://files.12thman.com/history/football/rosters/2010.html"),
    ("rosters", 2011, "https://files.12thman.com/history/football/rosters/2011.html"),
    ("season_stats", None, "https://12thman.com/old-texas-am-football-statistics"),
    ("season_stats", 2010, "https://12thman.com/sports/football/stats/season/2010"),
    ("season_stats", 2011, "https://12thman.com/sports/football/stats/season/2011"),
)
KNOWN_PDF_URLS = (
    "https://12thman.com/documents/1f488230-3dd2-41a8-89e2-acc2f040c7f8.pdf",
    "https://12thman.com/documents/9a519136-8c22-475c-b2ba-f2d5bf9dc3b1.pdf",
)
KNOWN_BOX_EXAMPLES = (
    "https://files.12thman.com/history/football/stats/2010-2011/ta13-lsu.html",
    "https://files.12thman.com/history/football/stats/2011-2012/ta01-smu.htm",
    "https://files.12thman.com/history/football/stats/2011-2012/ta12-ut.htm",
)
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
    "counts",
    "discovered_box_score_urls",
    "discovered_recap_urls",
    "page_identities",
    "captures",
    "admissions",
    "authority",
    "scientific_nonclaims",
    "protected_lane",
    "preserved_wmt_identities",
)


class AuthorityViolation(ValueError):
    """Raised when official-school archive evidence is asked to invent identity or authority."""


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
        "tamu_specialization_lift_claims": False,
        "bas_or_aggie_excess_claims": False,
        "bat_554_reopen": False,
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
        "bat_554_reopened": False,
        "wmt_candidate_payload_rewritten": False,
    }


def expected_admissions() -> dict[str, str]:
    return {
        "acquisition_admission": "CANDIDATE_ONLY",
        "source_authority": "SRC-014_OFFICIAL_SCHOOL_EVIDENCE",
        "ncaa_contest_identity": "NOT_CREATED",
        "historical_known_at": "UNKNOWN_CAPTURE_TIME_ONLY",
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "bat_523": "IN_PROGRESS",
        "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
        "bat_554": "RELATES_ONLY_DO_NOT_REOPEN",
        "wmt_payload": "PRESERVED_IMMUTABLE",
        "rights_disposition": "DERIVED_ONLY_OR_REVIEW_PRIVATE_RESEARCH",
    }


def official_host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def validate_official_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        raise AuthorityViolation(f"nonofficial scheme: {url}")
    host = official_host(url)
    if host not in OFFICIAL_HOSTS:
        raise AuthorityViolation(f"nonofficial host: {url}")
    path = parts.path.lower()
    if any(marker in path for marker in UNRELATED_SPORT_MARKERS):
        raise AuthorityViolation(f"unrelated sport: {url}")
    return url


def reject_interstitial(body: bytes) -> None:
    text = body.decode("latin-1", errors="replace").lower()
    official_content = (
        "box score" in text
        or "season stats" in text
        or "football roster" in text
        or "old texas" in text
        or "score by quarters" in text
        or "football:" in text
        or body.startswith(b"%PDF")
    )
    if official_content and len(body) >= 2048:
        return
    if any(marker in text for marker in HARD_INTERSTITIAL_MARKERS):
        raise AuthorityViolation("error/interstitial page rejected")
    login_hits = sum(text.count(marker) for marker in SOFT_LOGIN_MARKERS)
    if login_hits >= 8 and b"<table" not in body.lower() and len(body) < 8000:
        raise AuthorityViolation("login page rejected")


def pdf_capture_disposition(url: str, body: bytes, content_type: str | None, status: int) -> str:
    if not url.lower().endswith(".pdf"):
        raise AuthorityViolation("pdf_capture_disposition called for a non-PDF URL")
    if status != 200:
        return "OFFICIAL_ROUTE_ACCESS_BLOCKED"
    ctype = (content_type or "").lower()
    wrapper = (
        "html" in ctype
        or body.lstrip().lower().startswith(b"<html")
        or body.lstrip().lower().startswith(b"<!doctype html")
        or not body.startswith(b"%PDF")
    )
    if wrapper:
        return "PDF_WRAPPER_NOT_PDF_CONTENT"
    if "pdf" not in ctype and "octet-stream" not in ctype:
        raise AuthorityViolation("content-type mismatch for PDF")
    return "VERIFIED_OFFICIAL_DOCUMENT"


def season_from_archive_folder(folder: str) -> int:
    if folder.lower() == "2010-2011":
        return 2010
    if folder.lower() == "2011-2012":
        return 2011
    raise AuthorityViolation(f"unsupported archive season folder: {folder}")


def parse_anchors(body: bytes) -> list[tuple[str, str]]:
    text = body.decode("utf-8", errors="replace")
    return [(href, fragment_text(inner)) for href, inner in ANCHOR_RE.findall(text)]


def absolute_official_url(parent_url: str, href: str) -> str:
    joined = urljoin(parent_url, href.strip())
    return validate_official_url(joined.split("#", 1)[0])


def discover_labeled_urls(body: bytes, parent_url: str, label: str, path_re: re.Pattern[str]) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for href, text in parse_anchors(body):
        if text.casefold() != label.casefold():
            continue
        url = absolute_official_url(parent_url, href)
        path = urlsplit(url).path
        match = path_re.match(path)
        if match is None:
            raise AuthorityViolation(f"{label} href is not an official archive target: {url}")
        if url in seen:
            continue
        seen.add(url)
        found.append(url)
    return found


def discover_box_score_urls(body: bytes, parent_url: str, season: int) -> list[str]:
    urls = discover_labeled_urls(body, parent_url, "Box Score", BOX_PATH_RE)
    for url in urls:
        folder = BOX_PATH_RE.match(urlsplit(url).path).group(1)
        if season_from_archive_folder(folder) != season:
            raise AuthorityViolation(f"wrong-season box-score href on {season} index: {url}")
    if len(urls) != 13:
        raise AuthorityViolation(f"{season} season index did not expose 13 official box-score hrefs")
    return urls


def discover_recap_urls(body: bytes, parent_url: str, season: int) -> list[str]:
    urls = discover_labeled_urls(body, parent_url, "Recap", RECAP_PATH_RE)
    for url in urls:
        folder = RECAP_PATH_RE.match(urlsplit(url).path).group(1)
        if season_from_archive_folder(folder) != season:
            raise AuthorityViolation(f"wrong-season recap href on {season} index: {url}")
    return urls


def discover_season_stat_urls(body: bytes, parent_url: str, season: int) -> list[str]:
    found: list[str] = []
    for href, text in parse_anchors(body):
        if text.casefold() not in {"cumulative stats", "team game-by-game"}:
            continue
        url = absolute_official_url(parent_url, href)
        match = SEASON_STAT_PATH_RE.match(urlsplit(url).path)
        if match is None:
            raise AuthorityViolation(f"season-stat href is not official archive HTML: {url}")
        if season_from_archive_folder(match.group(1)) != season:
            raise AuthorityViolation(f"wrong-season season-stat href: {url}")
        if url not in found:
            found.append(url)
    return found


def discover_document_urls(body: bytes) -> dict[str, list[str]]:
    text = body.decode("utf-8", errors="replace")
    discovered = {"2010": [], "2011": []}
    for href, _label in parse_anchors(body):
        path = urlsplit(urljoin("https://12thman.com/old-texas-am-football-statistics", href)).path
        if DOCUMENT_PATH_RE.match(path) is None and SIDEARM_SEASON_PATH_RE.match(path) is None:
            continue
        url = absolute_official_url("https://12thman.com/old-texas-am-football-statistics", href)
        index = text.lower().find(href.lower())
        window = text[max(0, index - 400) : index + 80].lower() if index >= 0 else ""
        if "/stats/season/2010" in url or ("2010" in window and "2011" not in window[-40:]):
            season = "2010"
        elif "/stats/season/2011" in url or "2011" in window:
            season = "2011"
        else:
            continue
        if url not in discovered[season]:
            discovered[season].append(url)
    for known in KNOWN_PDF_URLS:
        if known not in discovered["2010"] and known not in discovered["2011"]:
            raise AuthorityViolation(f"known official PDF was not linked from the archive index: {known}")
    return discovered


def parse_roster_rows(body: bytes, season: int) -> list[dict[str, str]]:
    text = body.decode("utf-8", errors="replace")
    if f"{season} roster" not in text.lower():
        raise AuthorityViolation(f"roster page missing {season} team identity")
    rows: list[dict[str, str]] = []
    for table in TABLE_RE.findall(text):
        parsed_rows = ROW_RE.findall(table)
        if not parsed_rows:
            continue
        headers = [normalize_header(cell) for cell in CELL_RE.findall(parsed_rows[0])]
        if "name" not in headers:
            continue
        for raw_row in parsed_rows[1:]:
            cells = [fragment_text(cell) for cell in CELL_RE.findall(raw_row)]
            if len(cells) < 2:
                continue
            record = {headers[index] if index < len(headers) else f"col_{index}": cells[index] for index in range(len(cells))}
            name = record.get("name") or ""
            if not name or name.lower() in {"name", "no"}:
                continue
            rows.append(
                {
                    "jersey_raw": record.get("no") or record.get("no_") or "",
                    "name_raw": name,
                    "position_raw": record.get("position") or "",
                    "class_exp_raw": record.get("cl_exp") or "",
                    "hometown_raw": record.get("hometown_high_school_college") or record.get("hometown") or "",
                    "source_season": str(season),
                    "identity_status": "SOURCE_PLAYER_CANDIDATE",
                    "availability": "NOT_ESTABLISHED",
                }
            )
    if not rows:
        raise AuthorityViolation(f"{season} official roster rows were not independently reconstructed")
    return rows


def classify_capture(url: str, body: bytes, content_type: str | None, status: int) -> str:
    if status != 200:
        return "OFFICIAL_ROUTE_ACCESS_BLOCKED"
    if url.lower().endswith(".pdf"):
        return pdf_capture_disposition(url, body, content_type, status)
    reject_interstitial(body)
    path = urlsplit(url).path.lower()
    text = body.decode("latin-1", errors="replace").lower()
    official_football_path = (
        "/history/football/" in path
        or "/sports/football/" in path
        or "old-texas-am-football" in path
    )
    team_markers = (
        "texas a&m" in text
        or "texas a&amp;m" in text
        or "texas am" in text
        or "football roster" in text
        or "aggie" in text
        or "12thman" in text
        or "12th man" in text
        or "football:" in text
    )
    if not official_football_path and not team_markers:
        raise AuthorityViolation(f"missing team identity: {url}")
    if any(marker in path for marker in UNRELATED_SPORT_MARKERS):
        raise AuthorityViolation(f"unrelated sport: {url}")
    return "VERIFIED_OFFICIAL_SCHOOL_PAGE"


def page_family_for_url(url: str, seeded_family: str | None = None) -> str:
    path = urlsplit(url).path.lower()
    if BOX_PATH_RE.match(path):
        return "box_scores"
    if RECAP_PATH_RE.match(path):
        return "recaps"
    if "/rosters/" in path:
        return "rosters"
    if "/years/" in path:
        return "season_index"
    if path.endswith("/history/index.html") or path.endswith("/history/football/history/index.html"):
        return "history_index"
    if DOCUMENT_PATH_RE.match(path) or path.endswith(".pdf"):
        return "documents"
    if SEASON_STAT_PATH_RE.match(path) or SIDEARM_SEASON_PATH_RE.match(path) or "old-texas-am-football-statistics" in path:
        return "season_stats"
    if seeded_family:
        return seeded_family
    raise AuthorityViolation(f"unclassified official URL: {url}")


def extension_for(url: str, content_type: str | None, body: bytes) -> str:
    if body.startswith(b"%PDF"):
        return ".pdf"
    if url.lower().endswith(".pdf"):
        return ".html"
    if "xml" in (content_type or "").lower() or body.lstrip().startswith(b"<?xml"):
        return ".xml"
    return ".html"


def content_addressed_path(family: str, digest: str, extension: str) -> str:
    return f"{RAW_ROOT}/{family}/sha256_{digest}{extension}"


def direct_http_get(url: str, timeout_seconds: float = 45.0) -> dict[str, Any]:
    validate_official_url(url)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml,application/pdf,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0",
        },
        method="GET",
    )
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
            final_url = response.geturl()
            return {
                "url": url,
                "method": "GET",
                "timestamp": retrieved_at,
                "status": int(response.status),
                "content_type": response.headers.get("Content-Type"),
                "final_url": final_url,
                "redirect_chain": [url] if final_url == url else [url, final_url],
                "response_sha256": sha256_bytes(body),
                "raw_byte_count": len(body),
                "retrieval_route": "direct_http",
                "historical_publication_time": None,
                "body": body,
            }
    except urllib.error.HTTPError as error:
        body = error.read() or b""
        return {
            "url": url,
            "method": "GET",
            "timestamp": retrieved_at,
            "status": int(error.code),
            "content_type": error.headers.get("Content-Type") if error.headers else None,
            "final_url": url,
            "redirect_chain": [url],
            "response_sha256": sha256_bytes(body),
            "raw_byte_count": len(body),
            "retrieval_route": "direct_http",
            "historical_publication_time": None,
            "body": body,
        }


def compact_capture(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "content_type": record.get("content_type"),
        "final_url": record.get("final_url"),
        "historical_publication_time": None,
        "method": record.get("method"),
        "page_family": record.get("page_family"),
        "parent_url": record.get("parent_url"),
        "parser_disposition": record.get("parser_disposition"),
        "raw_byte_count": record.get("raw_byte_count"),
        "raw_relative_path": record.get("raw_relative_path"),
        "raw_sha256": record.get("raw_sha256"),
        "redirect_chain": record.get("redirect_chain"),
        "response_status": record.get("status"),
        "rights_disposition": record.get("rights_disposition"),
        "source_id": SOURCE_ID,
        "source_season": record.get("source_season"),
        "temporal_authority": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "timestamp": record.get("timestamp"),
        "url": record.get("url"),
    }


def persist_capture(data_root: Path, record: Mapping[str, Any], body: bytes) -> dict[str, Any]:
    stored = dict(record)
    stored["raw_sha256"] = sha256_bytes(body)
    stored["raw_byte_count"] = len(body)
    extension = extension_for(stored["url"], stored.get("content_type"), body)
    relative = content_addressed_path(stored["page_family"], stored["raw_sha256"], extension)
    target = data_root / relative
    if target.exists() and sha256_file(target) != stored["raw_sha256"]:
        raise AuthorityViolation(f"duplicate URL/path with conflicting bytes: {relative}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(body)
    stored["raw_relative_path"] = relative
    return stored


def capture_url(
    *,
    url: str,
    parent_url: str | None,
    family: str,
    season: int | None,
    data_root: Path,
) -> dict[str, Any]:
    validate_official_url(url)
    fetched = direct_http_get(url)
    body = fetched.pop("body")
    fetched["parent_url"] = parent_url
    fetched["page_family"] = family
    fetched["source_season"] = season
    fetched["rights_disposition"] = "PRIVATE_RESEARCH_METADATA_ONLY_NONBLOCKING"
    try:
        fetched["parser_disposition"] = classify_capture(url, body, fetched.get("content_type"), int(fetched["status"]))
    except AuthorityViolation as exc:
        raise AuthorityViolation(f"{exc}: {url}") from exc
    if fetched["historical_publication_time"] is not None:
        raise AuthorityViolation("current retrieval timestamp used as historical publication time")
    if family == "box_scores" and RECAP_PATH_RE.match(urlsplit(url).path):
        raise AuthorityViolation("recap link kept separate from box-score authority")
    return persist_capture(data_root, fetched, body)


def load_contract(repo_root: Path) -> dict[str, Any]:
    return load_json(repo_root / CONTRACT_RELATIVE)


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    return stable_hash({field: gate.get(field) for field in GATE_IDENTITY_FIELDS})


def acquire_archive(*, data_root: Path, repo_root: Path) -> dict[str, Any]:
    contract = load_contract(repo_root)
    seen_bytes: dict[str, str] = {}
    captures: list[dict[str, Any]] = []
    page_identities: dict[str, str] = {}
    bodies: dict[str, bytes] = {}

    def _capture(url: str, parent: str | None, family: str, season: int | None, identity_key: str | None = None) -> dict[str, Any]:
        record = capture_url(url=url, parent_url=parent, family=family, season=season, data_root=data_root)
        prior = seen_bytes.get(url)
        if prior and prior != record["raw_sha256"]:
            raise AuthorityViolation(f"duplicate URL with conflicting bytes: {url}")
        seen_bytes[url] = record["raw_sha256"]
        captures.append(record)
        if identity_key:
            page_identities[identity_key] = record["raw_sha256"]
        bodies[url] = (data_root / record["raw_relative_path"]).read_bytes()
        return record

    for family, season, url in SEED_URLS:
        key = family if season is None else f"{family}_{season}"
        _capture(url, None, family, season, key)

    season_boxes: dict[int, list[str]] = {}
    season_recaps: dict[int, list[str]] = {}
    for season in (2010, 2011):
        parent = f"https://files.12thman.com/history/football/years/{season}.html"
        body = bodies[parent]
        boxes = discover_box_score_urls(body, parent, season)
        recaps = discover_recap_urls(body, parent, season)
        stats = discover_season_stat_urls(body, parent, season)
        season_boxes[season] = boxes
        season_recaps[season] = recaps
        for url in stats:
            _capture(url, parent, "season_stats", season)
        for url in boxes:
            _capture(url, parent, "box_scores", season)
        for url in recaps:
            _capture(url, parent, "recaps", season)

    for example in KNOWN_BOX_EXAMPLES:
        if example not in season_boxes[2010] and example not in season_boxes[2011]:
            raise AuthorityViolation(f"known official box-score example was not discovered from season pages: {example}")

    documents = discover_document_urls(bodies["https://12thman.com/old-texas-am-football-statistics"])
    for season_key, urls in documents.items():
        season = int(season_key)
        for url in urls:
            family = "documents" if url.lower().endswith(".pdf") else "season_stats"
            if url not in seen_bytes:
                _capture(url, "https://12thman.com/old-texas-am-football-statistics", family, season)

    roster_counts = {}
    for season in (2010, 2011):
        roster_url = f"https://files.12thman.com/history/football/rosters/{season}.html"
        roster_counts[str(season)] = len(parse_roster_rows(bodies[roster_url], season))

    compact = [compact_capture(item) for item in captures]
    counts = {
        "history_index_pages": 1,
        "season_index_pages": 2,
        "roster_pages": 2,
        "roster_rows_2010": roster_counts["2010"],
        "roster_rows_2011": roster_counts["2011"],
        "box_scores_discovered_2010": len(season_boxes[2010]),
        "box_scores_discovered_2011": len(season_boxes[2011]),
        "box_scores_captured_2010": sum(1 for item in compact if item["page_family"] == "box_scores" and item["source_season"] == 2010 and item["response_status"] == 200),
        "box_scores_captured_2011": sum(1 for item in compact if item["page_family"] == "box_scores" and item["source_season"] == 2011 and item["response_status"] == 200),
        "box_scores_failed_2010": sum(1 for item in compact if item["page_family"] == "box_scores" and item["source_season"] == 2010 and item["response_status"] != 200),
        "box_scores_failed_2011": sum(1 for item in compact if item["page_family"] == "box_scores" and item["source_season"] == 2011 and item["response_status"] != 200),
        "recaps_discovered_2010": len(season_recaps[2010]),
        "recaps_discovered_2011": len(season_recaps[2011]),
        "documents_captured": sum(1 for item in compact if item["page_family"] == "documents" and item["parser_disposition"] == "VERIFIED_OFFICIAL_DOCUMENT"),
        "pdf_wrappers_rejected": sum(1 for item in compact if item["parser_disposition"] == "PDF_WRAPPER_NOT_PDF_CONTENT"),
        "captures_total": len(compact),
        "captures_http_200": sum(1 for item in compact if item["response_status"] == 200),
        "ncaa_contest_ids_created": 0,
    }
    if counts["box_scores_captured_2010"] != 13 or counts["box_scores_captured_2011"] != 13:
        raise AuthorityViolation("official 2010/2011 box-score capture coverage is incomplete")
    disposition = "OFFICIAL_SCHOOL_HISTORICAL_ARCHIVE_CAPTURED"
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_HISTORICAL_ARCHIVE_GATE",
        "result": f"PASS_{disposition}",
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": contract["decision_unit"],
        "jira_key": "BAT-579",
        "disposition": disposition,
        "source_id": SOURCE_ID,
        "counts": counts,
        "discovered_box_score_urls": {"2010": season_boxes[2010], "2011": season_boxes[2011]},
        "discovered_recap_urls": {"2010": season_recaps[2010], "2011": season_recaps[2011]},
        "page_identities": page_identities,
        "captures": compact,
        "admissions": expected_admissions(),
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "protected_lane": PROTECTED_LANE,
        "preserved_wmt_identities": {
            "acquisition_identity": WMT_ACQUISITION_IDENTITY,
            "dataset_identity": WMT_DATASET_IDENTITY,
            "mutation_policy": "DO_NOT_REWRITE_IN_PLACE",
        },
    }
    gate["acquisition_identity"] = stable_hash(
        {
            "captures": compact,
            "counts": counts,
            "discovered_box_score_urls": gate["discovered_box_score_urls"],
            "page_identities": page_identities,
        }
    )
    gate["gate_identity"] = compute_gate_identity(gate)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "acquisition_identity": gate["acquisition_identity"],
        "source_id": SOURCE_ID,
        "counts": counts,
        "discovered_box_score_urls": gate["discovered_box_score_urls"],
        "discovered_recap_urls": gate["discovered_recap_urls"],
        "captures": compact,
        "page_identities": page_identities,
        "preserved_wmt_identities": gate["preserved_wmt_identities"],
    }
    manifest["manifest_identity"] = stable_hash(manifest)
    write_json(data_root / contract["payloads"]["acquisition_manifest"], manifest)
    write_json(data_root / contract["payloads"]["normalized_root"] / "capture_index.json", {"acquisition_identity": gate["acquisition_identity"], "counts": counts})
    write_json(repo_root / GATE_RELATIVE, gate)
    return gate


def validate_compact_archive_gate(committed: Mapping[str, Any], contract: Mapping[str, Any]) -> None:
    if committed.get("schema_version") != SCHEMA_VERSION:
        raise AuthorityViolation("schema version drift")
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("classification drift")
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("source_id") != SOURCE_ID:
        raise AuthorityViolation("source id drift")
    if committed.get("contract_id") != contract["contract_id"]:
        raise AuthorityViolation("contract id drift")
    if committed.get("authority") != expected_authority():
        raise AuthorityViolation("authority nonclaim drift")
    if committed.get("scientific_nonclaims") != expected_scientific_nonclaims():
        raise AuthorityViolation("scientific nonclaim drift")
    if committed.get("admissions") != expected_admissions():
        raise AuthorityViolation("admission drift")
    if committed.get("preserved_wmt_identities", {}).get("acquisition_identity") != WMT_ACQUISITION_IDENTITY:
        raise AuthorityViolation("WMT acquisition identity was rewritten")
    if committed.get("preserved_wmt_identities", {}).get("dataset_identity") != WMT_DATASET_IDENTITY:
        raise AuthorityViolation("WMT dataset identity was rewritten")
    counts = committed.get("counts") or {}
    if counts.get("ncaa_contest_ids_created") != 0:
        raise AuthorityViolation("NCAA contest IDs were invented")
    if counts.get("box_scores_discovered_2010") != 13 or counts.get("box_scores_discovered_2011") != 13:
        raise AuthorityViolation("official box-score discovery count drifted")
    if counts.get("box_scores_captured_2010") != 13 or counts.get("box_scores_captured_2011") != 13:
        raise AuthorityViolation("official box-score capture count drifted")
    if counts.get("documents_captured") != 0:
        raise AuthorityViolation("PDF wrapper was reclassified as successful PDF evidence")
    if counts.get("pdf_wrappers_rejected") != 2:
        raise AuthorityViolation("PDF wrapper count drifted")
    if counts.get("roster_rows_2010") != PINNED_ROSTER_ROWS["2010"] or counts.get("roster_rows_2011") != PINNED_ROSTER_ROWS["2011"]:
        raise AuthorityViolation("official roster row count drifted")
    if stable_hash(committed.get("captures") or []) != PINNED_CAPTURES_IDENTITY:
        raise AuthorityViolation("capture records were not independently reconstructed")
    if stable_hash(committed.get("discovered_box_score_urls") or {}) != PINNED_BOX_URLS_IDENTITY:
        raise AuthorityViolation("discovered box-score URLs were not independently reconstructed")
    boxes = committed.get("discovered_box_score_urls") or {}
    recaps = committed.get("discovered_recap_urls") or {}
    if len(boxes.get("2010") or []) != 13 or len(boxes.get("2011") or []) != 13:
        raise AuthorityViolation("discovered box-score URL coverage drifted")
    for season, urls in boxes.items():
        for url in urls:
            validate_official_url(url)
            match = BOX_PATH_RE.match(urlsplit(url).path)
            if match is None:
                raise AuthorityViolation(f"non-box official URL accepted as box score: {url}")
            if season_from_archive_folder(match.group(1)) != int(season):
                raise AuthorityViolation(f"wrong-season box-score URL: {url}")
            if RECAP_PATH_RE.match(urlsplit(url).path):
                raise AuthorityViolation("recap classified as box-score authority")
    for season, urls in recaps.items():
        for url in urls:
            if BOX_PATH_RE.match(urlsplit(url).path):
                raise AuthorityViolation("box-score URL leaked into recap set")
    for example in KNOWN_BOX_EXAMPLES:
        if example not in (boxes.get("2010") or []) and example not in (boxes.get("2011") or []):
            raise AuthorityViolation("known official box-score example missing from compact gate")
    captures = committed.get("captures") or []
    if counts.get("captures_total") != len(captures):
        raise AuthorityViolation("capture count was not independently bound")
    urls = [item.get("url") for item in captures]
    if len(urls) != len(set(urls)):
        raise AuthorityViolation("duplicate capture URL")
    for item in captures:
        validate_official_url(item["url"])
        if item.get("historical_publication_time") is not None:
            raise AuthorityViolation("current retrieval timestamp used as historical publication time")
        if item.get("temporal_authority") != "UNKNOWN_RETRIEVAL_TIME_ONLY":
            raise AuthorityViolation("temporal authority overclaimed")
        if item.get("source_id") != SOURCE_ID:
            raise AuthorityViolation("capture source id drift")
        if int(item.get("response_status") or 0) == 200 and not item.get("raw_sha256"):
            raise AuthorityViolation("successful capture missing raw hash")
        if item.get("page_family") == "box_scores" and int(item.get("response_status") or 0) == 200:
            if not BOX_PATH_RE.match(urlsplit(item["url"]).path):
                raise AuthorityViolation("fabricated box-score capture")
    if compute_gate_identity(committed) != committed.get("gate_identity"):
        raise AuthorityViolation("gate identity does not reconstruct")
    rebuilt_acquisition = stable_hash(
        {
            "captures": committed.get("captures"),
            "counts": committed.get("counts"),
            "discovered_box_score_urls": committed.get("discovered_box_score_urls"),
            "page_identities": committed.get("page_identities"),
        }
    )
    if rebuilt_acquisition != committed.get("acquisition_identity"):
        raise AuthorityViolation("acquisition identity does not reconstruct")


def reconstruct_from_pages(*, data_root: Path, repo_root: Path, committed: Mapping[str, Any]) -> dict[str, Any]:
    boxes: dict[str, list[str]] = {}
    for season in (2010, 2011):
        parent = f"https://files.12thman.com/history/football/years/{season}.html"
        capture = next(item for item in committed["captures"] if item["url"] == parent)
        raw_path = data_root / capture["raw_relative_path"]
        if not raw_path.is_file():
            raise AuthorityViolation(f"missing raw season index: {parent}")
        if sha256_file(raw_path) != capture["raw_sha256"]:
            raise AuthorityViolation(f"season index hash drift: {parent}")
        body = raw_path.read_bytes()
        reject_interstitial(body)
        boxes[str(season)] = discover_box_score_urls(body, parent, season)
        if boxes[str(season)] != committed["discovered_box_score_urls"][str(season)]:
            raise AuthorityViolation(f"{season} box-score hrefs were not independently reconstructed")
    for item in committed["captures"]:
        path = data_root / item["raw_relative_path"]
        if int(item["response_status"]) == 200:
            if not path.is_file():
                raise AuthorityViolation(f"missing raw payload: {item['url']}")
            if sha256_file(path) != item["raw_sha256"]:
                raise AuthorityViolation(f"raw hash pointing to a missing or different file: {item['url']}")
            body = path.read_bytes()
            classify_capture(item["url"], body, item.get("content_type"), int(item["response_status"]))
            if item["page_family"] == "rosters" and item["source_season"] in {2010, 2011}:
                rows = parse_roster_rows(body, int(item["source_season"]))
                expected = committed["counts"][f"roster_rows_{item['source_season']}"]
                if len(rows) != expected:
                    raise AuthorityViolation(f"{item['source_season']} roster row count drifted")
        elif path.is_file() and item.get("parser_disposition") == "VERIFIED_OFFICIAL_SCHOOL_PAGE":
            raise AuthorityViolation("403/interstitial body reclassified as successful evidence")
    wmt_gate = load_json(repo_root / WMT_GATE_RELATIVE)
    if wmt_gate["candidate_layer"]["acquisition_identity"] != WMT_ACQUISITION_IDENTITY:
        raise AuthorityViolation("BAT-523 WMT candidate payload was rewritten")
    if wmt_gate["candidate_layer"]["dataset_identity"] != WMT_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-523 WMT dataset identity was rewritten")
    return {"discovered_box_score_urls": boxes}


def validate_artifact(
    *,
    data_root: Path,
    repo_root: Path,
    require_rebuild: bool = True,
    gate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    committed = dict(gate or load_json(repo_root / GATE_RELATIVE))
    contract = load_contract(repo_root)
    validate_compact_archive_gate(committed, contract)
    lake_ready = (data_root / RAW_ROOT / "season_index").is_dir() and (data_root / contract["payloads"]["acquisition_manifest"]).is_file()
    if require_rebuild and not lake_ready:
        raise AuthorityViolation("external historical-archive reconstruction was required but the data root is not mounted")
    reconstructed = None
    if lake_ready:
        reconstructed = reconstruct_from_pages(data_root=data_root, repo_root=repo_root, committed=committed)
        manifest = load_json(data_root / contract["payloads"]["acquisition_manifest"])
        if manifest.get("acquisition_identity") != committed.get("acquisition_identity"):
            raise AuthorityViolation("external manifest acquisition identity drifted")
        if manifest.get("discovered_box_score_urls") != committed.get("discovered_box_score_urls"):
            raise AuthorityViolation("external manifest box-score URLs are not semantically equal")
    return {
        "result": "PASS",
        "gate_identity": committed["gate_identity"],
        "acquisition_identity": committed["acquisition_identity"],
        "external_reconstruction": "MOUNTED" if reconstructed is not None else "NOT_MOUNTED",
    }


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))

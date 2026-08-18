"""Bounded official NCAA contest-ID route discovery for Texas A&M 2010-2011."""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urljoin, urlsplit, urlunsplit

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash
from aggie_analytics.data.tamu_ncaa_team_season_evidence import (
    bind_team_season,
    extract_official_nav_routes,
    load_cached_page,
    parse_schedule_table,
    parse_tables,
    reject_interstitial,
)


SCHEMA_VERSION = "aggie.data.tamu_2010_2011_ncaa_contest_route_discovery.v1"
CONTRACT_RELATIVE = "configs/tamu_2010_2011_ncaa_contest_route_discovery_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_2010_2011_ncaa_contest_route_discovery_gate.json"
CONTRACT_ID = "BAT-576-TAMU-2010-2011-NCAA-CONTEST-ROUTE-DISCOVERY-V1"
PASS_CLASSIFICATION = "TAMU_2010_2011_NCAA_CONTEST_ROUTE_DISCOVERY_CANDIDATE_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
TAMU_SEEDS = {"2010": "137387", "2011": "137872"}
OFFICIAL_HOST = "stats.ncaa.org"
CONTEST_HREF_RE = re.compile(r"""/contests/(\d+)/box_score""", re.I)
HREF_RE = re.compile(r"""href=["']([^"']+)["']""", re.I)
THIRD_PARTY_HOSTS = ("espn.com", "sports-reference.com", "wikipedia.org", "12thman.com")
ALLOWED_DISPOSITIONS = (
    "CONTEST_ROUTE_VERIFIED",
    "PARTIAL_CONTEST_ROUTE_VERIFIED",
    "LEGACY_SCHEDULE_ONLY_NO_CONTEST_ROUTE",
    "OFFICIAL_ROUTE_ACCESS_BLOCKED",
    "ROUTE_PRESENT_BUT_IDENTITY_UNRESOLVED",
)
PINNED_CONTEST_COUNTS = {
    "blocked_routes": 34,
    "candidate_routes": 36,
    "contest_endpoint_attempts": 0,
    "contest_ids_discovered": 0,
    "games_target": 26,
    "id_range_sweeps": 0,
    "inspected_http_200": 2,
    "inspections": 36,
    "live_attempts": 40,
}
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
    "input_identities",
    "counts",
    "modern_comparison",
    "discovered_contest_ids",
    "admissions",
    "authority",
    "scientific_nonclaims",
    "protected_lane",
)


class AuthorityViolation(ValueError):
    """Raised when contest-route discovery is asked to invent identity."""


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


def expected_authority() -> dict[str, bool]:
    return {
        "completeness_claim": False,
        "contest_id_fabrication": False,
        "id_range_sweep": False,
        "name_only_promotion": False,
        "third_party_as_ncaa_id": False,
        "opponent_date_only_identity": False,
        "historical_known_at_from_capture_time": False,
        "historical_pit_admission": False,
        "preliminary_training_admission": False,
        "protected_training_admission": False,
        "protected_evaluation_admission": False,
        "protected_outcome_authority": False,
        "champion_or_production_promotion": False,
        "forecast_publication": False,
        "membership_as_availability": False,
        "participation_as_availability": False,
        "tamu_specialization_lift_claims": False,
        "bas_or_aggie_excess_claims": False,
        "bat_554_reopen": False,
        "bat_523_closed": False,
        "bat_429_ready_or_done": False,
    }


def expected_nonclaims() -> dict[str, bool]:
    return {
        "completeness_claimed": False,
        "contest_ids_fabricated": False,
        "id_range_swept": False,
        "name_only_promoted": False,
        "third_party_promoted_as_ncaa_id": False,
        "opponent_date_only_promoted": False,
        "per_game_official_completion_claimed": False,
        "historical_known_at_established": False,
        "pregame_availability_admitted": False,
        "protected_lane_opened": False,
        "protected_evaluation_admitted": False,
        "champion_or_production_promotion": False,
        "tamu_specialization_lift_claimed": False,
        "bas_or_aggie_excess_result_claimed": False,
        "trained_production_champion": False,
        "bat_554_reopened": False,
        "bat_523_closed": False,
        "bat_429_advanced": False,
    }


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise AuthorityViolation("contest-route contract identity drift")
    if contract.get("tamu_seeds") != TAMU_SEEDS:
        raise AuthorityViolation("TAMU seeds drifted")
    if contract.get("authority") != expected_authority():
        raise AuthorityViolation("contract authority is not fail-closed")
    if contract.get("bat_554_policy") != "RELATES_ONLY_DO_NOT_REOPEN":
        raise AuthorityViolation("BAT-554 reopen is forbidden")
    return contract


def extract_contest_hrefs(body: bytes) -> list[str]:
    return sorted(set(CONTEST_HREF_RE.findall(body.decode("utf-8", "replace"))))


def reject_guessed_numeric_id(value: str, discovered: set[str]) -> None:
    if not str(value).isdigit():
        raise AuthorityViolation(f"non-numeric contest identifier {value!r}")
    if value not in discovered:
        raise AuthorityViolation("guessed numeric contest IDs are forbidden")


def reject_opponent_date_only_identity(binding: Mapping[str, Any]) -> None:
    if binding.get("ncaa_contest_id"):
        return
    if binding.get("promoted_from") == "opponent_date_only":
        raise AuthorityViolation("opponent/date-only identity cannot become an NCAA contest ID")


def reject_third_party_as_ncaa_id(url: str) -> None:
    host = (urlsplit(url).hostname or "").lower()
    if any(marker in host for marker in THIRD_PARTY_HOSTS):
        raise AuthorityViolation("third-party URLs cannot supply NCAA contest IDs")


def reject_wrong_season_contest(contest_page: bytes, expected_season: int) -> None:
    text = contest_page.decode("utf-8", "replace")
    if str(expected_season) not in text and str(expected_season + 1) not in text:
        raise AuthorityViolation(f"contest page lacked season {expected_season} identity")


def reject_error_or_redirect_page(body: bytes, status: int) -> None:
    if status in {301, 302, 303, 307, 308}:
        raise AuthorityViolation("redirect page cannot establish a contest ID")
    if status >= 400:
        raise AuthorityViolation(f"HTTP {status} cannot establish a contest ID")
    try:
        reject_interstitial(body)
    except Exception as exc:
        raise AuthorityViolation(str(exc)) from exc


def detect_conflicting_official_routes(game_key: str, contest_ids: list[str]) -> None:
    unique = sorted(set(str(item) for item in contest_ids if item))
    if len(unique) > 1:
        raise AuthorityViolation(f"conflicting official contest routes for {game_key}: {unique}")


def official_url(path_or_url: str) -> str:
    raw = html.unescape(path_or_url).strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlsplit(raw)
    else:
        parsed = urlsplit(urljoin("https://stats.ncaa.org/", raw))
    if (parsed.hostname or "").lower() != OFFICIAL_HOST:
        raise AuthorityViolation(f"non-official host {parsed.hostname}")
    if parsed.username or parsed.password:
        raise AuthorityViolation("credentials are forbidden")
    return urlunsplit(("https", OFFICIAL_HOST, parsed.path, parsed.query, ""))


def is_deterministic_candidate(path: str, query: str, opponent_ids: set[str]) -> str | None:
    if re.fullmatch(r"/teams/\d+", path) and path.split("/")[-1] in opponent_ids:
        return "opponent_team_page"
    if re.fullmatch(r"/teams/\d+/(roster|season_to_date_stats)", path):
        return "tamu_optional_page_family"
    if re.fullmatch(r"/players/\d+", path):
        return "official_player_game_by_game"
    if re.fullmatch(r"/team/\d+/stats/\d+", path):
        return "official_team_stats_ctl"
    if path == "/team/team_game_highs" and query:
        return "official_team_game_highs"
    if path == "/team/conf_game_highs" and query:
        return "official_conf_game_highs"
    if re.fullmatch(r"/contests/\d+/box_score", path):
        return "official_contest_box_score"
    return None


def extract_schedule_opponents(body: bytes, season: int) -> list[dict[str, Any]]:
    schedule = parse_schedule_table(parse_tables(body), season)
    rows = []
    for row in schedule["rows"]:
        opponent_id = row.get("opponent_team_season_id")
        if not opponent_id:
            raise AuthorityViolation(f"schedule row lacked official opponent team-season id: {row}")
        rows.append(
            {
                "season": season,
                "game_date": row["game_date"],
                "opponent_raw": row["opponent_raw"],
                "opponent_team_season_id": opponent_id,
                "source_uri": f"https://{OFFICIAL_HOST}/teams/{opponent_id}",
                "contest_id": None,
            }
        )
    return rows


def extract_official_candidates(body: bytes, *, seed: str, season: int) -> list[dict[str, Any]]:
    opponents = extract_schedule_opponents(body, season)
    opponent_ids = {row["opponent_team_season_id"] for row in opponents}
    routes = extract_official_nav_routes(body, seed)
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for page_family, uri in routes.items():
        if uri not in seen:
            seen.add(uri)
            candidates.append(
                {
                    "url": uri,
                    "family": f"tamu_{page_family}",
                    "season": season,
                    "derived_from": f"official_tamu_team_page_{seed}",
                }
            )
    for row in opponents:
        if row["source_uri"] not in seen:
            seen.add(row["source_uri"])
            candidates.append(
                {
                    "url": row["source_uri"],
                    "family": "opponent_team_page",
                    "season": season,
                    "derived_from": f"official_tamu_schedule_{seed}",
                    "opponent_team_season_id": row["opponent_team_season_id"],
                    "game_date": row["game_date"],
                }
            )
    text = body.decode("utf-8", "replace")
    for href in HREF_RE.findall(text):
        try:
            url = official_url(href)
        except AuthorityViolation:
            continue
        parsed = urlsplit(url)
        family = is_deterministic_candidate(parsed.path, parsed.query, opponent_ids)
        if family is None or url in seen:
            continue
        if family == "tamu_optional_page_family" and seed not in parsed.path:
            continue
        seen.add(url)
        candidates.append(
            {
                "url": url,
                "family": family,
                "season": season,
                "derived_from": f"official_tamu_team_page_{seed}",
            }
        )
    return candidates


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


def direct_http_get(url: str, timeout_seconds: float = 30.0) -> dict[str, Any]:
    reject_third_party_as_ncaa_id(url)
    request = urllib.request.Request(
        url,
        headers={"Accept": "text/html,application/xhtml+xml", "User-Agent": "Mozilla/5.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
            status = int(response.status)
            final_url = response.geturl()
    except urllib.error.HTTPError as error:
        body = error.read()
        status = int(error.code)
        final_url = url
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "url": url,
        "method": "GET",
        "timestamp": retrieved_at,
        "status": status,
        "content_type": "text/html",
        "final_url": final_url,
        "redirect_chain": [url] if final_url == url else [url, final_url],
        "response_sha256": sha256_bytes(body),
        "retrieval_route": "direct_http",
        "body": body,
    }


def open_stateful_browser(data_root: Path) -> Any:
    from aggie_analytics.data.tamu_ncaa_team_season_evidence import _acquire_mod

    acquire = _acquire_mod()
    session = acquire.StatefulPatchrightSession(
        executable_path=Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        browser_installation_root=None,
        runtime_root=data_root / "runtime" / "BAT-576" / "chrome_session",
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
    reject_third_party_as_ncaa_id(url)
    try:
        response = session.fetch(url)
        body = response.body
        status = int(response.status_code)
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
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "url": url,
        "method": "GET",
        "timestamp": retrieved_at,
        "status": status,
        "content_type": "text/html",
        "final_url": url,
        "redirect_chain": [url],
        "response_sha256": sha256_bytes(body),
        "retrieval_route": "stateful_patchright_chrome",
        "body": body,
    }


def _compact(capture: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in capture.items() if key != "body"}


def inspect_body(body: bytes) -> dict[str, Any]:
    contests = extract_contest_hrefs(body)
    return {
        "contest_ids": contests,
        "contest_link_count": len(contests),
        "html_bytes": len(body),
        "legacy_without_contest_href": len(contests) == 0,
    }


def choose_disposition(*, discovered: list[str], blocked_routes: int, inspected_ok: int) -> str:
    if discovered:
        return "CONTEST_ROUTE_VERIFIED" if inspected_ok >= 26 else "PARTIAL_CONTEST_ROUTE_VERIFIED"
    if blocked_routes and inspected_ok < 26:
        return "OFFICIAL_ROUTE_ACCESS_BLOCKED"
    return "LEGACY_SCHEDULE_ONLY_NO_CONTEST_ROUTE"


def rebuild_expected(
    *,
    data_root: Path,
    repo_root: Path,
    allow_live: bool = False,
    issued_at_utc: str = "2026-08-18T20:00:00Z",
) -> dict[str, Any]:
    contract = load_contract(repo_root)
    attempts: list[dict[str, Any]] = []
    inspections: list[dict[str, Any]] = []
    discovered: list[str] = []
    candidates: list[dict[str, Any]] = []
    chrome_targets: set[str] = set()
    browser = None
    try:
        for season in (2010, 2011):
            seed = TAMU_SEEDS[str(season)]
            team = load_cached_page(data_root, contract["lake_html"][str(season)])
            bind_team_season(team["body"], seed, season)
            parsed = inspect_body(team["body"])
            if parsed["contest_ids"]:
                raise AuthorityViolation("TAMU team page unexpectedly exposed contest IDs")
            inspections.append(
                {
                    "url": team["url"],
                    "family": "tamu_team",
                    "season": season,
                    "status": 200,
                    "cache_disposition": "REUSED_VERIFIED_LAKE_HTML",
                    "response_sha256": team["response_sha256"],
                    "contest_ids": [],
                    "classification": "LEGACY_SCHEDULE_ONLY_NO_CONTEST_ROUTE",
                }
            )
            season_candidates = extract_official_candidates(team["body"], seed=seed, season=season)
            candidates.extend(season_candidates)
            for item in season_candidates:
                if item["family"] in {
                    "official_player_game_by_game",
                    "official_team_stats_ctl",
                    "official_team_game_highs",
                    "official_conf_game_highs",
                }:
                    chrome_targets.add(item["url"])
                if item["family"] == "opponent_team_page" and item.get("opponent_team_season_id") in {
                    "137391",
                    "137876",
                }:
                    chrome_targets.add(item["url"])

        allowed_urls = {item["url"] for item in candidates}
        for item in candidates:
            if item["family"] == "tamu_team":
                continue
            url = item["url"]
            if url not in allowed_urls:
                raise AuthorityViolation("candidate URL escaped the official allowlist")
            capture = None
            if allow_live:
                http = direct_http_get(url)
                stored = store_raw(data_root, contract, http["body"]) if http.get("body") else {}
                http.update(stored)
                attempts.append(_compact(http))
                if 200 <= int(http["status"]) < 300 and http.get("body"):
                    try:
                        reject_error_or_redirect_page(http["body"], int(http["status"]))
                        capture = http
                        capture["cache_disposition"] = "LIVE_HTTP_STORED"
                    except AuthorityViolation:
                        capture = None
                if capture is None and url in chrome_targets:
                    if browser is None:
                        browser = open_stateful_browser(data_root)
                    chrome = stateful_browser_get(browser, url)
                    if chrome.get("body"):
                        chrome.update(store_raw(data_root, contract, chrome["body"]))
                    attempts.append(_compact(chrome))
                    if 200 <= int(chrome.get("status") or 0) < 300 and chrome.get("body"):
                        try:
                            reject_error_or_redirect_page(chrome["body"], int(chrome["status"]))
                            capture = chrome
                            capture["cache_disposition"] = "LIVE_BROWSER_STORED"
                        except AuthorityViolation:
                            capture = None
            if capture is None:
                inspections.append(
                    {
                        "url": url,
                        "family": item["family"],
                        "season": item["season"],
                        "status": attempts[-1]["status"] if attempts else None,
                        "cache_disposition": "BLOCKED_OR_NOT_ATTEMPTED",
                        "response_sha256": (attempts[-1].get("response_sha256") if attempts else None),
                        "contest_ids": [],
                        "classification": "OFFICIAL_ROUTE_ACCESS_BLOCKED"
                        if allow_live
                        else "SOURCE_EVIDENCE_ABSENT",
                    }
                )
                continue
            parsed = inspect_body(capture["body"])
            if parsed["contest_ids"]:
                reject_guessed_numeric_id(parsed["contest_ids"][0], set(parsed["contest_ids"]))
                discovered.extend(parsed["contest_ids"])
            inspections.append(
                {
                    "url": url,
                    "family": item["family"],
                    "season": item["season"],
                    "status": capture.get("status"),
                    "cache_disposition": capture.get("cache_disposition"),
                    "response_sha256": capture.get("response_sha256"),
                    "contest_ids": parsed["contest_ids"],
                    "classification": (
                        "CONTEST_ROUTE_VERIFIED" if parsed["contest_ids"] else "LEGACY_SCHEDULE_ONLY_NO_CONTEST_ROUTE"
                    ),
                }
            )
    finally:
        if browser is not None:
            try:
                browser.__exit__(None, None, None)
            except Exception:
                pass

    discovered = sorted(set(discovered))
    blocked = sum(1 for row in inspections if row["classification"] == "OFFICIAL_ROUTE_ACCESS_BLOCKED")
    inspected_ok = sum(1 for row in inspections if row["status"] == 200)
    disposition = choose_disposition(discovered=discovered, blocked_routes=blocked, inspected_ok=inspected_ok)
    if discovered and disposition not in {"CONTEST_ROUTE_VERIFIED", "PARTIAL_CONTEST_ROUTE_VERIFIED"}:
        raise AuthorityViolation("discovered contest IDs were not classified as a verified route")
    if not discovered and disposition not in {
        "LEGACY_SCHEDULE_ONLY_NO_CONTEST_ROUTE",
        "OFFICIAL_ROUTE_ACCESS_BLOCKED",
        "ROUTE_PRESENT_BUT_IDENTITY_UNRESOLVED",
    }:
        raise AuthorityViolation("negative finding used a success disposition")
    endpoint_attempts = len(discovered)
    counts = {
        "candidate_routes": len(candidates),
        "inspections": len(inspections),
        "live_attempts": len(attempts),
        "blocked_routes": blocked,
        "inspected_http_200": inspected_ok,
        "contest_ids_discovered": len(discovered),
        "contest_endpoint_attempts": endpoint_attempts,
        "games_target": 26,
        "id_range_sweeps": 0,
    }
    core = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_2010_2011_NCAA_CONTEST_ROUTE_DISCOVERY_GATE",
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "disposition": disposition,
        "tamu_seeds": TAMU_SEEDS,
        "input_identities": {
            "phase2_gate_identity": contract["input_identities"]["phase2_gate_identity"],
            "bat571_gate_identity": contract["input_identities"]["bat571_gate_identity"],
            "bat575_gate_identity": contract["input_identities"]["bat575_gate_identity"],
            "protected_split_registry_sha256": contract["input_identities"]["protected_split_registry_sha256"],
        },
        "modern_comparison": contract["modern_comparison"],
        "counts": counts,
        "candidates": candidates,
        "inspections": inspections,
        "attempts": attempts,
        "discovered_contest_ids": discovered,
        "next_authority_requirement": (
            "An official page or official mapping table that emits /contests/{id}/box_score "
            "for the 2010-2011 TAMU games, or successful retrieval of the blocked official "
            "player/team-stat/game-highs routes already derived from the 2011 team page."
            if not discovered
            else "Acquire official contest endpoints for the discovered IDs using existing endpoint safety rules."
        ),
        "admissions": {
            "discovery_admission": "CANDIDATE_ONLY",
            "disposition": disposition,
            "pregame_availability": "BLOCKED",
            "protected_lane": PROTECTED_LANE,
            "per_game_official_completion": False,
            "bat_523": "IN_PROGRESS",
            "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
            "bat_554": "RELATES_ONLY_DO_NOT_REOPEN",
        },
        "authority": expected_authority(),
        "scientific_nonclaims": expected_nonclaims(),
        "protected_lane": PROTECTED_LANE,
        "issued_at_utc": issued_at_utc,
    }
    core["manifest_identity"] = stable_hash(
        {key: core[key] for key in ("schema_version", "candidates", "inspections", "tamu_seeds", "discovered_contest_ids")}
    )
    return core


def compute_gate_identity(payload: Mapping[str, Any]) -> str:
    return stable_hash({field: payload.get(field) for field in GATE_IDENTITY_FIELDS})


def expected_gate_document(core: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_2010_2011_NCAA_CONTEST_ROUTE_DISCOVERY_GATE",
        "result": f"PASS_{core['disposition']}",
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": core["decision_unit"],
        "jira_key": core["jira_key"],
        "disposition": core["disposition"],
        "tamu_seeds": core["tamu_seeds"],
        "input_identities": core["input_identities"],
        "counts": core["counts"],
        "modern_comparison": core["modern_comparison"],
        "discovered_contest_ids": core["discovered_contest_ids"],
        "next_authority_requirement": core["next_authority_requirement"],
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


def materialize(*, data_root: Path, repo_root: Path, issued_at_utc: str, allow_live: bool = False) -> dict[str, Any]:
    core = rebuild_expected(
        data_root=data_root,
        repo_root=repo_root,
        allow_live=allow_live,
        issued_at_utc=issued_at_utc,
    )
    payload_dir = data_root / "features" / "tamu_2010_2011_ncaa_contest_route_discovery" / "sha256" / core["manifest_identity"]
    payload_dir.mkdir(parents=True, exist_ok=True)
    rows_path = payload_dir / "contest_route_discovery_rows.json"
    write_json(
        rows_path,
        {
            "candidates": core["candidates"],
            "inspections": core["inspections"],
            "attempts": core["attempts"],
        },
    )
    manifest_path = payload_dir / "tamu_2010_2011_ncaa_contest_route_discovery_manifest.json"
    write_json(manifest_path, {key: value for key, value in core.items() if key not in {"candidates", "inspections", "attempts"}})
    payload = {
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "rows": str(rows_path),
        "rows_sha256": sha256_file(rows_path),
        "inspection_count": len(core["inspections"]),
        "attempt_count": len(core["attempts"]),
    }
    gate = expected_gate_document(core, payload)
    write_json(repo_root / GATE_RELATIVE, gate)
    return {"gate": gate, "payload": payload}


CONTEST_ATTEMPT_REQUIRED_FIELDS = (
    "url",
    "timestamp",
    "status",
    "content_type",
    "redirect_chain",
    "raw_relative_path",
)
CONTEST_MANIFEST_SEMANTIC_FIELDS = (
    "tamu_seeds",
    "disposition",
    "counts",
    "input_identities",
    "discovered_contest_ids",
    "authority",
    "scientific_nonclaims",
    "protected_lane",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def reconstruct_contest_candidates(*, data_root: Path, repo_root: Path) -> dict[str, Any]:
    contract = load_contract(repo_root)
    candidates: list[dict[str, Any]] = []
    captured_bodies: list[tuple[str, bytes]] = []
    for season in (2010, 2011):
        seed = TAMU_SEEDS[str(season)]
        capture = load_cached_page(data_root, contract["lake_html"][str(season)])
        bind_team_season(capture["body"], seed, season)
        if extract_contest_hrefs(capture["body"]):
            raise AuthorityViolation("cached TAMU team page now exposes contest IDs")
        extracted = extract_official_candidates(capture["body"], seed=seed, season=season)
        if not extracted:
            raise AuthorityViolation("official candidate extraction collapsed")
        candidates.extend(extracted)
        captured_bodies.append((capture["url"], capture["body"]))
    discovered = sorted(
        {
            contest_id
            for _url, body in captured_bodies
            for contest_id in extract_contest_hrefs(body)
        }
    )
    return {
        "candidates": candidates,
        "candidate_urls": {item["url"] for item in candidates},
        "discovered_from_pages": discovered,
        "captured_bodies": captured_bodies,
    }


def load_independent_contest_payloads(
    *,
    committed: Mapping[str, Any],
    data_root: Path,
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    payload = committed.get("payload") or {}
    rows_path = Path(str(payload.get("rows") or ""))
    manifest_path = Path(str(payload.get("manifest") or ""))
    if not rows_path.is_file():
        raise AuthorityViolation("bulk discovery rows payload is missing")
    if sha256_file(rows_path) != payload.get("rows_sha256"):
        raise AuthorityViolation("bulk discovery payload hash drift")
    if not manifest_path.is_file():
        raise AuthorityViolation("bulk discovery manifest is missing")
    if sha256_file(manifest_path) != payload.get("manifest_sha256"):
        raise AuthorityViolation("bulk discovery manifest hash drift")
    rows = load_json(rows_path)
    manifest = load_json(manifest_path)
    rebuilt_manifest_identity = stable_hash(
        {
            "schema_version": manifest.get("schema_version"),
            "candidates": rows.get("candidates"),
            "inspections": rows.get("inspections"),
            "tamu_seeds": manifest.get("tamu_seeds"),
            "discovered_contest_ids": manifest.get("discovered_contest_ids"),
        }
    )
    if manifest.get("manifest_identity") != committed.get("manifest_identity"):
        raise AuthorityViolation("bulk discovery manifest identity drifted")
    if manifest.get("manifest_identity") != rebuilt_manifest_identity:
        raise AuthorityViolation("bulk discovery manifest identity does not reconstruct")
    for field in CONTEST_MANIFEST_SEMANTIC_FIELDS:
        if field not in manifest:
            continue
        if _canonical(manifest.get(field)) != _canonical(committed.get(field)):
            raise AuthorityViolation(f"bulk discovery manifest {field} is not semantically equal to the gate")
    raw_root = contract["payloads"]["raw_root"]
    if not str(rows_path).replace("\\", "/").endswith(
        f"{committed['manifest_identity']}/contest_route_discovery_rows.json"
    ) and raw_root not in str(rows_path).replace("\\", "/"):
        if committed["manifest_identity"] not in str(rows_path):
            raise AuthorityViolation("bulk rows path is not bound to the manifest identity")
    return {"rows": rows, "manifest": manifest, "payload": payload}


def validate_contest_attempts(
    *,
    attempts: list[Mapping[str, Any]],
    candidate_urls: set[str],
    data_root: Path | None,
    require_raw: bool,
    contract: Mapping[str, Any],
) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    validated: list[dict[str, Any]] = []
    for attempt in attempts:
        missing_core = [field for field in ("url", "timestamp", "status") if field not in attempt]
        if missing_core:
            raise AuthorityViolation(f"contest attempt is missing required fields: {missing_core}")
        url = str(attempt["url"])
        reject_third_party_as_ncaa_id(url)
        official_url(url)
        if candidate_urls and url not in candidate_urls:
            raise AuthorityViolation("contest attempt escaped the reconstructed official candidate set")
        status = int(attempt["status"])
        error = attempt.get("error")
        digest = str(attempt.get("raw_sha256") or attempt.get("response_sha256") or "")
        raw_relative = str(attempt.get("raw_relative_path") or "")
        if error:
            if 200 <= status < 300:
                raise AuthorityViolation("failed contest attempt claimed HTTP success")
            if digest or raw_relative:
                raise AuthorityViolation("failed contest attempt claimed a raw body")
            key = (url, str(attempt["timestamp"]), f"error:{error}")
            if key in seen:
                raise AuthorityViolation("duplicate contest attempts are forbidden")
            seen.add(key)
            validated.append(
                {
                    "url": url,
                    "timestamp": attempt["timestamp"],
                    "status": status,
                    "error": error,
                }
            )
            continue
        missing = [field for field in CONTEST_ATTEMPT_REQUIRED_FIELDS if field not in attempt or attempt.get(field) in (None, "")]
        if missing:
            raise AuthorityViolation(f"contest attempt is missing required fields: {missing}")
        if not digest:
            raise AuthorityViolation("contest attempt is missing a raw-body SHA")
        key = (url, str(attempt["timestamp"]), digest)
        if key in seen:
            raise AuthorityViolation("duplicate contest attempts are forbidden")
        seen.add(key)
        if not raw_relative.startswith(contract["payloads"]["raw_root"]):
            raise AuthorityViolation("contest attempt raw path escaped the discovery raw root")
        if require_raw:
            if data_root is None:
                raise AuthorityViolation("raw contest-attempt validation requires the data root")
            raw_path = data_root / raw_relative
            if not raw_path.is_file():
                raise AuthorityViolation("contest attempt raw payload is missing")
            if sha256_file(raw_path) != digest:
                raise AuthorityViolation("contest attempt raw hash points to a different file")
            body = raw_path.read_bytes()
            if 200 <= status < 300:
                reject_error_or_redirect_page(body, status)
            else:
                try:
                    reject_error_or_redirect_page(body, 200)
                except AuthorityViolation:
                    pass
                else:
                    if status >= 400:
                        raise AuthorityViolation("blocked contest attempt was not an error or interstitial page")
        validated.append(
            {
                "url": url,
                "timestamp": attempt["timestamp"],
                "status": status,
                "raw_sha256": digest,
                "raw_relative_path": raw_relative,
            }
        )
    return validated


def contest_ids_from_official_hrefs(bodies: list[bytes]) -> list[str]:
    discovered: list[str] = []
    for body in bodies:
        discovered.extend(extract_contest_hrefs(body))
    return sorted(set(discovered))


def validate_discovered_contest_ids(
    *,
    committed_ids: list[str],
    reconstructed_ids: list[str],
    source_bodies: list[tuple[str, bytes]],
) -> None:
    if list(committed_ids) != list(reconstructed_ids):
        raise AuthorityViolation("discovered contest IDs were not independently reconstructed from official hrefs")
    for contest_id in committed_ids:
        if not str(contest_id).isdigit():
            raise AuthorityViolation("non-numeric contest identifier is forbidden")
        reject_guessed_numeric_id(str(contest_id), set(reconstructed_ids))
        evidence = [
            url
            for url, body in source_bodies
            if contest_id in extract_contest_hrefs(body)
        ]
        if not evidence:
            raise AuthorityViolation(
                f"contest ID {contest_id} lacks an official /contests/{{digits}}/box_score source body"
            )


def validate_compact_contest_gate(committed: Mapping[str, Any], contract: Mapping[str, Any]) -> None:
    if committed.get("tamu_seeds") != TAMU_SEEDS:
        raise AuthorityViolation("seeds drifted")
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("classification drifted")
    if committed.get("authority") != expected_authority():
        raise AuthorityViolation("authority drifted")
    if committed.get("scientific_nonclaims") != expected_nonclaims():
        raise AuthorityViolation("nonclaims drifted")
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane drifted")
    if committed.get("disposition") not in ALLOWED_DISPOSITIONS:
        raise AuthorityViolation("unknown disposition")
    if committed.get("result") != f"PASS_{committed.get('disposition')}":
        raise AuthorityViolation("result/disposition pairing drifted")
    committed_inputs = committed.get("input_identities") or {}
    for key, value in committed_inputs.items():
        if key.endswith("_relative_path"):
            continue
        if contract["input_identities"].get(key) != value:
            raise AuthorityViolation("input identities drifted")
    counts = committed.get("counts") or {}
    discovered = list(committed.get("discovered_contest_ids") or [])
    if counts != PINNED_CONTEST_COUNTS:
        raise AuthorityViolation("contest-route counts were not independently reconstructed")
    if counts.get("id_range_sweeps") != 0:
        raise AuthorityViolation("ID-range sweep was recorded")
    if counts.get("contest_ids_discovered") != len(discovered):
        raise AuthorityViolation("discovered contest count drifted")
    if discovered and counts.get("contest_endpoint_attempts") == 0:
        raise AuthorityViolation("discovered IDs were not followed by endpoint attempts")
    if not discovered and counts.get("contest_endpoint_attempts") != 0:
        raise AuthorityViolation("endpoint attempts exist without discovered contest IDs")
    if not discovered and committed.get("disposition") in {
        "CONTEST_ROUTE_VERIFIED",
        "PARTIAL_CONTEST_ROUTE_VERIFIED",
    }:
        raise AuthorityViolation("success disposition was fabricated without discovered contest IDs")
    if committed.get("admissions", {}).get("per_game_official_completion") is not False:
        raise AuthorityViolation("per-game official completion was forged")
    if any(committed["authority"].values()):
        raise AuthorityViolation("authority claim was opened")
    if committed["scientific_nonclaims"].get("protected_lane_opened"):
        raise AuthorityViolation("protected lane opened")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not reconstruct")
    payload = committed.get("payload") or {}
    if not payload.get("manifest") or not payload.get("rows") or not payload.get("manifest_sha256") or not payload.get("rows_sha256"):
        raise AuthorityViolation("compact contest-route payload identity is incomplete")


def validate_artifact(
    *,
    data_root: Path,
    repo_root: Path,
    require_rebuild: bool = True,
    gate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    committed = dict(gate or load_json(repo_root / GATE_RELATIVE))
    contract = load_contract(repo_root)
    validate_compact_contest_gate(committed, contract)
    lake_ready = (data_root / contract["lake_html"]["2010"]["raw_relative_path"]).is_file() and (
        data_root / "features/tamu_2010_2011_ncaa_contest_route_discovery"
    ).is_dir()
    if require_rebuild and not lake_ready:
        raise AuthorityViolation("external contest-route reconstruction was required but the data root is not mounted")
    reconstructed_ids: list[str] = []
    candidate_urls: set[str] = set()
    source_bodies: list[tuple[str, bytes]] = []
    if lake_ready:
        reconstructed = reconstruct_contest_candidates(data_root=data_root, repo_root=repo_root)
        candidate_urls = reconstructed["candidate_urls"]
        source_bodies = reconstructed["captured_bodies"]
        payloads = load_independent_contest_payloads(
            committed=committed,
            data_root=data_root,
            contract=contract,
        )
        rows = payloads["rows"]
        row_candidates = list(rows.get("candidates") or [])
        row_inspections = list(rows.get("inspections") or [])
        row_attempts = list(rows.get("attempts") or [])
        if {item["url"] for item in row_candidates} != candidate_urls:
            raise AuthorityViolation("bulk candidate URLs were not independently reconstructed from official pages")
        if committed["counts"]["candidate_routes"] != len(reconstructed["candidates"]):
            raise AuthorityViolation("candidate count was not independently reconstructed")
        if committed["counts"]["candidate_routes"] != len(row_candidates):
            raise AuthorityViolation("candidate count does not match independently loaded bulk rows")
        if committed["counts"]["inspections"] != len(row_inspections):
            raise AuthorityViolation("inspection count does not match independently loaded bulk rows")
        if committed["counts"]["live_attempts"] != len(row_attempts):
            raise AuthorityViolation("live attempt count does not match independently loaded bulk rows")
        blocked = sum(1 for row in row_inspections if row.get("classification") == "OFFICIAL_ROUTE_ACCESS_BLOCKED")
        inspected_ok = sum(1 for row in row_inspections if row.get("status") == 200)
        if committed["counts"]["blocked_routes"] != blocked:
            raise AuthorityViolation("blocked route count was not independently reconstructed")
        if committed["counts"]["inspected_http_200"] != inspected_ok:
            raise AuthorityViolation("HTTP-200 inspection count was not independently reconstructed")
        row_bodies: list[bytes] = []
        for inspection in row_inspections:
            digest = inspection.get("response_sha256")
            if not digest:
                continue
            raw_path = data_root / contract["payloads"]["raw_root"] / f"{digest}.html"
            lake_path = None
            for season in ("2010", "2011"):
                spec = contract["lake_html"][season]
                if spec["raw_sha256"] == digest:
                    lake_path = data_root / spec["raw_relative_path"]
                    break
            path = lake_path if lake_path and lake_path.is_file() else raw_path
            if path.is_file():
                if sha256_file(path) != digest:
                    raise AuthorityViolation("inspection raw hash points to a different file")
                body = path.read_bytes()
                row_bodies.append(body)
                source_bodies.append((str(inspection.get("url")), body))
                if 200 <= int(inspection.get("status") or 0) < 300:
                    reject_error_or_redirect_page(body, int(inspection["status"]))
        reconstructed_ids = contest_ids_from_official_hrefs([body for _url, body in source_bodies])
        validate_discovered_contest_ids(
            committed_ids=list(committed.get("discovered_contest_ids") or []),
            reconstructed_ids=reconstructed_ids,
            source_bodies=source_bodies,
        )
        validate_contest_attempts(
            attempts=row_attempts,
            candidate_urls=candidate_urls,
            data_root=data_root,
            require_raw=True,
            contract=contract,
        )
        independently_chosen = choose_disposition(
            discovered=reconstructed_ids,
            blocked_routes=blocked,
            inspected_ok=inspected_ok,
        )
        if committed["disposition"] != independently_chosen:
            raise AuthorityViolation("contest-route disposition was not independently reconstructed")
        if committed["counts"]["contest_endpoint_attempts"] != len(reconstructed_ids):
            raise AuthorityViolation("contest endpoint attempt count was not independently reconstructed")
        if reconstructed_ids:
            contest_attempts = [
                attempt
                for attempt in row_attempts
                if "/contests/" in str(attempt.get("url"))
            ]
            if len(contest_attempts) != committed["counts"]["contest_endpoint_attempts"]:
                raise AuthorityViolation("invented or missing contest endpoint attempts")
        payload = committed.get("payload") or {}
        if payload.get("inspection_count") != len(row_inspections):
            raise AuthorityViolation("payload inspection count drifted")
        if payload.get("attempt_count") != len(row_attempts):
            raise AuthorityViolation("payload attempt count drifted")
    else:
        discovered = list(committed.get("discovered_contest_ids") or [])
        if discovered:
            raise AuthorityViolation("a discovered contest ID cannot be accepted without mounted source-body evidence")
    return {
        "result": "PASS",
        "gate_identity": committed["gate_identity"],
        "external_reconstruction": "MOUNTED" if lake_ready else "NOT_MOUNTED",
    }

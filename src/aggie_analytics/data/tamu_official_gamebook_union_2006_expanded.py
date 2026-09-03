"""New immutable SRC-014 union identity admitting official 2006 games beside BAT-592."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash
from aggie_analytics.data.tamu_official_gamebook_union import REGISTRY_SHA256
from aggie_analytics.data.tamu_official_gamebook_union_enriched import (
    GATE_RELATIVE as PRIOR_ENRICHED_GATE_RELATIVE,
)
from aggie_analytics.data.tamu_official_rich_structure import is_rich_structured
from aggie_analytics.validation.artifact_binding import compute_identity


SCHEMA_VERSION = "aggie.data.tamu_official_gamebook_union_2006_expanded.v1"
CONTRACT_RELATIVE = "configs/tamu_official_gamebook_union_2006_expanded_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_gamebook_union_2006_expanded_gate.json"
CONTRACT_ID = "BAT-597-TAMU-OFFICIAL-GAMEBOOK-UNION-2006-EXPANDED-V1"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_OFFICIAL_GAMEBOOK_UNION_2006_EXPANDED_CANDIDATE_ONLY"
PASS_RESULT = "PASS_IMMUTABLE_BAT592_PRESERVED_OFFICIAL_2006_ADDED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PINNED_BAT592_UNION_IDENTITY = "00fdb5eac85c3a89464ed6466359380d1089cec1f3ce34d4f9eb56258929cf31"
PINNED_BAT592_GATE_IDENTITY = "3b546b12b3d50098bec457a010b47168f472449e8475c397ee44cd26ff1edc6a"
PINNED_BAT591_PAYLOAD_IDENTITY = "c7e061fcafa480f260b8f614ae6481747502ba5d933a786f584da442039fc338"
PINNED_BAT591_GATE_IDENTITY = "ed2ce7b95bd046a282116cf50aff84fec1e585f8dee848cc4451bec63bdf668c"
PINNED_BAT596_PAYLOAD_IDENTITY = "f4fc2472e90e37adc3d0d4569d8b1225a45acd6ad4d41aa48a9b3dbb39473a9d"
PINNED_BAT596_GATE_IDENTITY = "973769e93b22c6e5f30fd8abbaef16bf0abc904e7bc9a5582fc25d4ef06514ba"
PINNED_BAT595_GATE_IDENTITY = "2a9c56a10b14cf5fec4dff1c3cd55d0b4440afdb9520fb308317a9ae59c47ed7"
PINNED_BAT595_DATASET_IDENTITY = "05ac9ce54a107007b433e52d7a52f85d7e20726d9aaf7ca204332a75f88cd697"
PINNED_BAT595_ACQUISITION_IDENTITY = "1ed988f759f383b62625d582ac70ee306a36c84d92ccded9f70c9fd11bfed269"
PINNED_BAT595_GAMES_IDENTITY = "40e37b3ac4a015def27682bc994a6b222567a84ed4745594cd9d56f7ebf0621b"
PINNED_BAT594_GATE_IDENTITY = "d1f765a73abf0107fcf200562590bfd0212a521df47f9c6b27bb336ad737635c"
PINNED_BAT594_BOX_URL_IDENTITY = "57ee217fa34eeb041681ad9552933c4da505ab448ab43cac95bbf73ad6b4bf07"
PINNED_BAT589_GATE_IDENTITY = "f2080b0ebb7815892732b2e600917e00da972edca0379888fa0010ff6bf17e51"
PINNED_BAT586_GATE_IDENTITY = "c62a09d2b3bcf7e69c6b6ea90993084d124a779d7ab779e8ebeab300b2a9c006"
INVENTORY_IDENTITY = "d39d35ff7cfacf2e39a524d0f1fdb97072158c50f84225ed8413771140efaa37"
PRIOR_ENRICHED_CAPTURED_GAMES = 237
PRIOR_ENRICHED_RICH = 224
PRIOR_ENRICHED_METADATA = 13
OFFICIAL_2006_EXPECTED = 13
ADMITTED_STATUSES = frozenset(
    {
        "MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE",
        "OFFICIAL_INDEX_DATE_CONFLICT",
    }
)
PRESERVED_REJECTION_URLS = frozenset(
    {
        "https://files.12thman.com/history/football/stats/2008-2009/ta03-mia.html",
        "https://files.12thman.com/history/football/stats/2009-2010/ta13-uga.html",
        "https://files.12thman.com/history/football/stats/2007-2008/mfb_148_ta04-mia.html",
        "https://files.12thman.com/history/football/stats/2007-2008/mfb_2158_ta10-ou.html",
    }
)
OVERLAY_DOMAINS = (
    "team_statistics",
    "individual_player_statistics",
    "drives",
    "play_by_play",
)
COMPACT_FIELDS = (
    "source_season",
    "football_season",
    "calendar_date",
    "index_date_candidate",
    "opponent_candidate",
    "opponent_normalized",
    "tamu_points",
    "opponent_points",
    "venue_state",
    "stadium",
    "site",
    "url",
    "source_sha256",
    "canonical_game_match_status",
    "conflict_status",
    "domain_coverage",
    "ncaa_contest_id",
    "canonical_game_id",
    "availability_claim",
    "historical_publication_time",
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
    "prior_union_identity",
    "prior_union_gate_identity",
    "union_identity",
    "selected_seasons",
    "counts",
    "coverage_by_season",
    "coverage_by_domain",
    "enriched_official_games",
    "preserved_rejections",
    "conflicts",
    "admissions",
    "authority",
    "scientific_nonclaims",
    "protected_lane",
    "upstream_identities",
)


class AuthorityViolation(ValueError):
    """Raised when the 2006-expanded union invents identity or mutates a sealed layer."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    missing = [key for key in REQUIRED_GATE_FIELDS if key not in gate]
    if missing:
        raise AuthorityViolation("gate is missing required identity fields: " + ", ".join(missing))
    return compute_identity(gate, "gate_identity")


def expected_authority() -> dict[str, bool]:
    return {
        "availability_claim": False,
        "bat_429_ready_or_done": False,
        "bat_523_closed": False,
        "champion_or_production_promotion": False,
        "completeness_claim": False,
        "contest_id_fabrication": False,
        "historical_known_at_from_capture_time": False,
        "name_only_promotion": False,
        "ncaa_contest_identity": False,
        "prior_enriched_union_mutated_in_place": False,
        "rejected_game_admitted": False,
        "statcrew_payload_mutated_in_place": False,
        "wmt_payload_mutated_in_place": False,
    }


def expected_scientific_nonclaims() -> dict[str, bool]:
    return {
        "bat_429_advanced": False,
        "bat_523_closed": False,
        "bat591_payload_rewritten": False,
        "bat592_union_rewritten": False,
        "bat595_payload_rewritten": False,
        "bat596_payload_rewritten": False,
        "champion_or_production_promotion": False,
        "completeness_claimed": False,
        "historical_known_at_established": False,
        "historical_population_ready": False,
        "ncaa_contest_ids_invented": False,
        "name_only_promoted": False,
        "pregame_availability_admitted": False,
        "protected_lane_opened": False,
        "rejected_games_admitted": False,
        "wmt_payload_mutated": False,
    }


def expected_admissions() -> dict[str, str]:
    return {
        "bat_401": "DONE_VERIFIED_RETAIN_PROTECTED_LANE_BLOCKED",
        "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
        "bat_523": "IN_PROGRESS",
        "bat_591_statcrew": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_592_enriched_union": "PRESERVED_IMMUTABLE_SUPERSEDED_AS_PRIOR_LAYER",
        "bat_594_index": "CONSUMED_OFFICIAL_INDEX_URLS_ONLY",
        "bat_595_boxscores": "CONSUMED_NORMALIZED_2006_BOXES_ONLY",
        "bat_596_domains": "CONSUMED_2006_STRUCTURED_DOMAINS_ONLY",
        "gap_005": "OPEN",
        "historical_known_at": "UNKNOWN_CAPTURE_TIME_ONLY",
        "ncaa_contest_identity": "NOT_CREATED",
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "source_authority": "SRC-014_OFFICIAL_SCHOOL_EVIDENCE",
        "union_admission": "CANDIDATE_ONLY",
        "wmt_payload": "PRESERVED_IMMUTABLE",
    }


def _index_by_url(games: list[Mapping[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for game in games:
        url = str(game.get("url") or "")
        if not url:
            raise AuthorityViolation(f"{label} compact game is missing a URL")
        if url in index:
            raise AuthorityViolation(f"duplicate {label} URL {url}")
        index[url] = dict(game)
    return index


def compact_official_2006(game: Mapping[str, Any]) -> dict[str, Any]:
    row = {key: game.get(key) for key in COMPACT_FIELDS}
    row["source_season"] = int(game.get("source_season") or game.get("football_season") or 0)
    row["official_index_url"] = game.get("parent_url") or "https://files.12thman.com/history/football/years/2006.html"
    row["ncaa_contest_id"] = None
    row["canonical_game_id"] = None
    row["availability_claim"] = False
    row["historical_publication_time"] = None
    return row


def overlay_2006(game: Mapping[str, Any], domains: Mapping[str, Any]) -> dict[str, Any]:
    row = json.loads(json.dumps(game))
    coverage = dict(row.get("domain_coverage") or {})
    prior_rich = is_rich_structured(row)
    row["prior_rich_structured"] = prior_rich
    if str(domains.get("source_sha256") or "") != str(row.get("source_sha256") or ""):
        raise AuthorityViolation(f"BAT-596 raw hash does not match admitted 2006 game {row.get('url')}")
    for domain in OVERLAY_DOMAINS:
        if (domains.get("domain_coverage") or {}).get(domain) == "PRESENT":
            coverage[domain] = "PRESENT"
    row["domain_coverage"] = coverage
    row["overlay_applied"] = True
    row["overlay_source"] = "BAT-596-2006-STRUCTURED-DOMAINS"
    row["rich_structured"] = is_rich_structured(row)
    row["ncaa_contest_id"] = None
    row["canonical_game_id"] = None
    row["availability_claim"] = False
    row["historical_publication_time"] = None
    return row


def coverage_by_season(games: list[Mapping[str, Any]]) -> dict[str, Any]:
    by_season: dict[str, dict[str, int]] = {}
    for game in games:
        key = str(game["source_season"])
        bucket = by_season.setdefault(
            key,
            {
                "official_school_games": 0,
                "rich_structured_games": 0,
                "metadata_only_games": 0,
                "overlays_applied": 0,
                "became_rich": 0,
            },
        )
        bucket["official_school_games"] += 1
        if is_rich_structured(game):
            bucket["rich_structured_games"] += 1
        else:
            bucket["metadata_only_games"] += 1
        if game.get("overlay_applied"):
            bucket["overlays_applied"] += 1
        if game.get("rich_structured") and not game.get("prior_rich_structured"):
            bucket["became_rich"] += 1
    return {key: by_season[key] for key in sorted(by_season, reverse=True)}


def coverage_by_domain(games: list[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    totals: dict[str, dict[str, int]] = {}
    for domain in OVERLAY_DOMAINS:
        present = sum(1 for game in games if (game.get("domain_coverage") or {}).get(domain) == "PRESENT")
        totals[domain] = {
            "official_pre2010_present": present,
            "official_pre2010_absent": len(games) - present,
            "eligibility": "OFFICIAL_SCHOOL_POSTGAME_CANDIDATE_NOT_PREGAME_NOT_NCAA_CONTEST",
        }
    totals["pregame_availability"] = {
        "official_pre2010_present": 0,
        "official_pre2010_absent": len(games),
        "eligibility": "NOT_PROVIDED_BY_ROUTE",
    }
    return totals


def load_official_2006_games(repo_root: Path, data_root: Path) -> list[dict[str, Any]]:
    index = load_json(repo_root / "artifacts/data_lake/tamu_official_2006_season_index_gate.json")
    if index.get("gate_identity") != PINNED_BAT594_GATE_IDENTITY:
        raise AuthorityViolation("BAT-594 2006 index identity rewritten")
    if index.get("box_url_identity") != PINNED_BAT594_BOX_URL_IDENTITY:
        raise AuthorityViolation("BAT-594 box-URL identity rewritten")
    allowed = [str(url) for url in (index.get("box_score_urls") or [])]
    if len(allowed) != OFFICIAL_2006_EXPECTED:
        raise AuthorityViolation("BAT-594 did not emit 13 official 2006 box URLs")
    allowed_set = frozenset(allowed)
    box = load_json(repo_root / "artifacts/data_lake/tamu_official_2006_boxscore_gate.json")
    if box.get("gate_identity") != PINNED_BAT595_GATE_IDENTITY:
        raise AuthorityViolation("BAT-595 2006 acquisition identity rewritten")
    if box.get("dataset_identity") != PINNED_BAT595_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-595 dataset identity rewritten")
    if box.get("acquisition_identity") != PINNED_BAT595_ACQUISITION_IDENTITY:
        raise AuthorityViolation("BAT-595 acquisition identity rewritten")
    if box.get("games_identity") != PINNED_BAT595_GAMES_IDENTITY:
        raise AuthorityViolation("BAT-595 games identity rewritten")
    contract = load_json(repo_root / "configs/tamu_official_2006_boxscore_contract.json")
    payload_path = data_root / contract["payloads"]["normalized_root"] / PINNED_BAT595_DATASET_IDENTITY / "payload.json"
    if not payload_path.is_file():
        raise AuthorityViolation("external BAT-595 payload is not mounted")
    payload = load_json(payload_path)
    if payload.get("games_identity") != PINNED_BAT595_GAMES_IDENTITY:
        raise AuthorityViolation("BAT-595 games identity drifted")
    if payload.get("dataset_identity") != PINNED_BAT595_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-595 dataset identity drifted")
    games = [compact_official_2006(item) for item in (payload.get("games") or [])]
    if len(games) != OFFICIAL_2006_EXPECTED:
        raise AuthorityViolation(f"expected 13 official 2006 games, found {len(games)}")
    if any(int(item["source_season"]) != 2006 for item in games):
        raise AuthorityViolation("BAT-595 payload contained a non-2006 game")
    if {item["url"] for item in games} != allowed_set:
        raise AuthorityViolation("BAT-595 games are not exactly the BAT-594 official index URLs")
    return games


def load_2006_domains(repo_root: Path) -> dict[str, dict[str, Any]]:
    domains = load_json(repo_root / "artifacts/data_lake/tamu_official_2006_structured_domains_gate.json")
    if domains.get("gate_identity") != PINNED_BAT596_GATE_IDENTITY:
        raise AuthorityViolation("BAT-596 structured-domain identity rewritten")
    if domains.get("payload_identity") != PINNED_BAT596_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-596 payload identity rewritten")
    return _index_by_url(list(domains.get("games") or []), "BAT-596")


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    registry = repo_root / "governance/PROTECTED_SPLIT_REGISTRY.csv"
    digest = hashlib.sha256(registry.read_bytes()).hexdigest()
    if digest != REGISTRY_SHA256:
        raise AuthorityViolation("protected-split registry identity drift")
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise AuthorityViolation("2006-expanded union contract identity drift")
    prior = load_json(repo_root / PRIOR_ENRICHED_GATE_RELATIVE)
    if prior.get("union_identity") != PINNED_BAT592_UNION_IDENTITY:
        raise AuthorityViolation("BAT-592 enriched-union identity was rewritten")
    if prior.get("gate_identity") != PINNED_BAT592_GATE_IDENTITY:
        raise AuthorityViolation("BAT-592 enriched-union gate identity was rewritten")
    if int(prior.get("counts", {}).get("union_captured_games") or 0) != PRIOR_ENRICHED_CAPTURED_GAMES:
        raise AuthorityViolation("BAT-592 captured-game count drifted")
    bat591 = load_json(repo_root / "artifacts/data_lake/tamu_official_statcrew_preformatted_gate.json")
    if bat591.get("gate_identity") != PINNED_BAT591_GATE_IDENTITY:
        raise AuthorityViolation("BAT-591 StatCrew identity rewritten")
    if bat591.get("payload_identity") != PINNED_BAT591_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-591 payload identity rewritten")
    bat589 = load_json(repo_root / "artifacts/data_lake/tamu_official_2007_boxscore_gate.json")
    if bat589.get("gate_identity") != PINNED_BAT589_GATE_IDENTITY:
        raise AuthorityViolation("BAT-589 2007 acquisition identity rewritten")
    bat586 = load_json(repo_root / "artifacts/data_lake/tamu_official_pre2010_boxscore_gate.json")
    if bat586.get("gate_identity") != PINNED_BAT586_GATE_IDENTITY:
        raise AuthorityViolation("BAT-586 2008/2009 acquisition identity rewritten")
    prior_games = [json.loads(json.dumps(item)) for item in (prior.get("enriched_official_games") or [])]
    rejected = [json.loads(json.dumps(item)) for item in (prior.get("preserved_rejections") or [])]
    rejected_urls = {str(item.get("url") or "") for item in rejected}
    if rejected_urls != PRESERVED_REJECTION_URLS:
        raise AuthorityViolation("the four preserved rejected games drifted")
    domains_by_url = load_2006_domains(repo_root)
    raw_2006 = load_official_2006_games(repo_root, data_root)
    admitted_2006: list[dict[str, Any]] = []
    for game in raw_2006:
        url = str(game["url"])
        if url in rejected_urls:
            raise AuthorityViolation(f"rejected game was presented for 2006 admission: {url}")
        status = str(game.get("canonical_game_match_status") or "")
        if status not in ADMITTED_STATUSES:
            raise AuthorityViolation(f"2006 game lacks official index+URL+SHA admission: {url}")
        if url not in domains_by_url:
            raise AuthorityViolation(f"BAT-596 domains missing for official 2006 URL {url}")
        admitted_2006.append(overlay_2006(game, domains_by_url[url]))
    admitted_2006.sort(key=lambda item: (item["football_season"], item["calendar_date"], item["url"]))
    if len(admitted_2006) != OFFICIAL_2006_EXPECTED:
        raise AuthorityViolation("official 2006 admission count drifted")
    official_games = prior_games + admitted_2006
    seen_urls: set[str] = set()
    for game in official_games:
        url = str(game.get("url") or "")
        if url in seen_urls:
            raise AuthorityViolation(f"duplicate official game presented for overlay: {url}")
        if url in rejected_urls:
            raise AuthorityViolation(f"rejected game leaked into overlay membership: {url}")
        seen_urls.add(url)
    became_rich = sum(1 for item in admitted_2006 if item["rich_structured"] and not item["prior_rich_structured"])
    overlays_applied = sum(1 for item in admitted_2006 if item["overlay_applied"])
    new_rich = sum(1 for item in admitted_2006 if item["rich_structured"])
    counts = {
        "wmt_games_preserved": int(prior["counts"]["wmt_games_preserved"]),
        "cycle9_official_games_preserved": int(prior["counts"]["cycle9_official_games_preserved"]),
        "cycle9_union_games_preserved": int(prior["counts"]["cycle9_union_games_preserved"]),
        "prior_226_union_games_preserved": int(prior["counts"]["prior_226_union_games_preserved"]),
        "prior_237_union_games_preserved": int(prior["counts"]["prior_237_union_games_preserved"]),
        "prior_enriched_union_games_preserved": PRIOR_ENRICHED_CAPTURED_GAMES,
        "official_2006_added": len(admitted_2006),
        "new_games_added": len(admitted_2006),
        "overlays_applied": int(prior["counts"]["overlays_applied"]) + overlays_applied,
        "overlays_became_rich": int(prior["counts"]["overlays_became_rich"]) + became_rich,
        "duplicates_rejected": 0,
        "unmatched_rejected": len(rejected),
        "union_target_games": PRIOR_ENRICHED_CAPTURED_GAMES + len(admitted_2006),
        "union_captured_games": PRIOR_ENRICHED_CAPTURED_GAMES + len(admitted_2006),
        "rich_structured_games": PRIOR_ENRICHED_RICH + new_rich,
        "metadata_only_games": PRIOR_ENRICHED_METADATA + len(admitted_2006) - new_rich,
        "matched_strong_tuple": int(prior["counts"]["matched_strong_tuple"])
        + sum(1 for item in admitted_2006 if item.get("canonical_game_match_status") == "MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE"),
        "date_conflicts": int(prior["counts"]["date_conflicts"])
        + sum(1 for item in admitted_2006 if item.get("conflict_status") not in {None, "NONE"}),
        "ncaa_contest_ids_created": 0,
        "wmt_rich_structured_games": int(prior["counts"]["wmt_rich_structured_games"]),
        "wmt_metadata_only_games": int(prior["counts"]["wmt_metadata_only_games"]),
    }
    if counts["union_captured_games"] != counts["rich_structured_games"] + counts["metadata_only_games"]:
        raise AuthorityViolation("2006-expanded rich/metadata arithmetic drifted")
    conflicts = [
        {
            "url": item["url"],
            "opponent_candidate": item.get("opponent_candidate"),
            "calendar_date": item.get("calendar_date"),
            "index_date_candidate": item.get("index_date_candidate"),
            "conflict_status": item.get("conflict_status"),
            "match_status": item.get("canonical_game_match_status"),
        }
        for item in admitted_2006
        if item.get("conflict_status") not in {None, "NONE"}
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "prior_union_identity": PINNED_BAT592_UNION_IDENTITY,
        "prior_union_gate_identity": PINNED_BAT592_GATE_IDENTITY,
        "bat596_payload_identity": PINNED_BAT596_PAYLOAD_IDENTITY,
        "enriched_official_games": official_games,
        "admitted_official_2006_games": admitted_2006,
        "preserved_rejections": rejected,
        "counts": counts,
        "conflicts": conflicts,
        "scientific_nonclaims": expected_scientific_nonclaims(),
    }
    payload["union_identity"] = stable_hash(
        {
            "prior_union_identity": PINNED_BAT592_UNION_IDENTITY,
            "bat596_payload_identity": PINNED_BAT596_PAYLOAD_IDENTITY,
            "admitted_official_2006_games": admitted_2006,
            "preserved_rejections": rejected,
            "counts": counts,
        }
    )
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_GAMEBOOK_UNION_2006_EXPANDED_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": "POST-TASK-SRC014-2006-EXPANDED-ENRICHED-UNION-001",
        "jira_key": "BAT-597",
        "disposition": "NEW_IMMUTABLE_IDENTITY_BAT592_PRESERVED_OFFICIAL_2006_ADDED",
        "source_id": SOURCE_ID,
        "prior_union_identity": PINNED_BAT592_UNION_IDENTITY,
        "prior_union_gate_identity": PINNED_BAT592_GATE_IDENTITY,
        "union_identity": payload["union_identity"],
        "selected_seasons": [2009, 2008, 2007, 2006],
        "counts": counts,
        "coverage_by_season": coverage_by_season(official_games),
        "coverage_by_domain": coverage_by_domain(official_games),
        "enriched_official_games": official_games,
        "admitted_official_2006_games": admitted_2006,
        "preserved_rejections": rejected,
        "conflicts": conflicts,
        "admissions": expected_admissions(),
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "protected_lane": PROTECTED_LANE,
        "upstream_identities": {
            "bat586_gate_identity": PINNED_BAT586_GATE_IDENTITY,
            "bat589_gate_identity": PINNED_BAT589_GATE_IDENTITY,
            "bat591_gate_identity": PINNED_BAT591_GATE_IDENTITY,
            "bat591_payload_identity": PINNED_BAT591_PAYLOAD_IDENTITY,
            "bat592_gate_identity": PINNED_BAT592_GATE_IDENTITY,
            "bat592_union_identity": PINNED_BAT592_UNION_IDENTITY,
            "bat594_box_url_identity": PINNED_BAT594_BOX_URL_IDENTITY,
            "bat594_gate_identity": PINNED_BAT594_GATE_IDENTITY,
            "bat595_acquisition_identity": PINNED_BAT595_ACQUISITION_IDENTITY,
            "bat595_dataset_identity": PINNED_BAT595_DATASET_IDENTITY,
            "bat595_games_identity": PINNED_BAT595_GAMES_IDENTITY,
            "bat595_gate_identity": PINNED_BAT595_GATE_IDENTITY,
            "bat596_gate_identity": PINNED_BAT596_GATE_IDENTITY,
            "bat596_payload_identity": PINNED_BAT596_PAYLOAD_IDENTITY,
            "inventory_identity": INVENTORY_IDENTITY,
            "protected_split_registry_sha256": REGISTRY_SHA256,
        },
    }
    if counts["ncaa_contest_ids_created"]:
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if any(item.get("ncaa_contest_id") for item in official_games):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if any(item.get("availability_claim") for item in official_games):
        raise AuthorityViolation("pregame availability claimed")
    if any(item.get("historical_publication_time") is not None for item in official_games):
        raise AuthorityViolation("retrieval time promoted to historical known-at")
    gate["gate_identity"] = compute_gate_identity(gate)
    payload["gate_identity"] = gate["gate_identity"]
    return {
        "contract": contract,
        "gate": gate,
        "payload": payload,
        "prior": prior,
    }


def materialize_union(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    payload = objects["payload"]
    root = data_root / objects["contract"]["payloads"]["union_root"] / payload["union_identity"]
    write_json(root / "union_manifest.json", payload)
    write_json(repo_root / GATE_RELATIVE, objects["gate"])
    return {
        "gate_identity": objects["gate"]["gate_identity"],
        "union_identity": payload["union_identity"],
        "counts": objects["gate"]["counts"],
    }


def lake_is_ready(data_root: Path) -> bool:
    return (
        data_root
        / "features/tamu_official_2006_boxscores/sha256"
        / PINNED_BAT595_DATASET_IDENTITY
        / "payload.json"
    ).is_file()


def validate_compact_gate(committed: Mapping[str, Any]) -> None:
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("prior_union_identity") != PINNED_BAT592_UNION_IDENTITY:
        raise AuthorityViolation("BAT-592 enriched-union identity was rewritten")
    if committed.get("prior_union_gate_identity") != PINNED_BAT592_GATE_IDENTITY:
        raise AuthorityViolation("BAT-592 enriched-union gate identity was rewritten")
    if committed.get("result") != PASS_RESULT:
        raise AuthorityViolation("completion forged")
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("classification forged")
    if committed.get("authority", {}).get("historical_known_at_from_capture_time"):
        raise AuthorityViolation("retrieval time promoted to historical known-at")
    if committed.get("counts", {}).get("ncaa_contest_ids_created"):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if int(committed.get("counts", {}).get("new_games_added") or 0) != OFFICIAL_2006_EXPECTED:
        raise AuthorityViolation("2006-expanded union invented or dropped a 2006 admission")
    if committed.get("admissions", {}).get("pregame_availability") != "BLOCKED":
        raise AuthorityViolation("pregame availability admitted")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not recompute")
    if not committed.get("union_identity"):
        raise AuthorityViolation("union identity missing")
    if int(committed.get("counts", {}).get("union_captured_games") or 0) != PRIOR_ENRICHED_CAPTURED_GAMES + OFFICIAL_2006_EXPECTED:
        raise AuthorityViolation("union captured-game arithmetic drifted")
    upstream = committed.get("upstream_identities") or {}
    if upstream.get("bat592_union_identity") != PINNED_BAT592_UNION_IDENTITY:
        raise AuthorityViolation("BAT-592 enriched-union identity was rewritten")
    if upstream.get("bat591_payload_identity") != PINNED_BAT591_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-591 payload identity rewritten")
    if upstream.get("bat596_payload_identity") != PINNED_BAT596_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-596 payload identity rewritten")
    rejected_urls = {str(item.get("url") or "") for item in committed.get("preserved_rejections") or []}
    admitted_urls = {str(item.get("url") or "") for item in committed.get("enriched_official_games") or []}
    if rejected_urls != PRESERVED_REJECTION_URLS:
        raise AuthorityViolation("the four preserved rejected games drifted")
    if rejected_urls & admitted_urls:
        raise AuthorityViolation("rejected games were admitted")


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
        raise AuthorityViolation("external 2006-expanded union reconstruction was required but the data root is not mounted")
    if not ready:
        return {
            "result": "PASS",
            "gate_identity": committed["gate_identity"],
            "union_identity": committed["union_identity"],
            "external_reconstruction": "NOT_MOUNTED",
        }
    expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    if committed != expected["gate"]:
        raise AuthorityViolation("committed 2006-expanded union gate does not match independent reconstruction")
    return {
        "result": "PASS",
        "gate_identity": expected["gate"]["gate_identity"],
        "union_identity": expected["gate"]["union_identity"],
        "counts": expected["gate"]["counts"],
        "external_reconstruction": "MOUNTED",
    }


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))

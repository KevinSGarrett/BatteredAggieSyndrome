"""New immutable SRC-014 enriched-union identity overlaying StatCrew domains."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import stable_hash
from aggie_analytics.data.tamu_official_gamebook_union import (
    BOXSCORE_DATASET_IDENTITY,
    BOXSCORE_GATE_IDENTITY,
    PINNED_GAMES_IDENTITY,
    REGISTRY_SHA256,
    WMT_ACQUISITION_IDENTITY,
    WMT_DATASET_IDENTITY,
    WMT_METADATA_ONLY,
    WMT_RICH_GAMES,
    WMT_TARGET_GAMES,
)
from aggie_analytics.data.tamu_official_gamebook_union_2007 import (
    GATE_RELATIVE as PRIOR_237_GATE_RELATIVE,
)
from aggie_analytics.data.tamu_official_gamebook_union_expanded import (
    GATE_RELATIVE as PRIOR_226_GATE_RELATIVE,
)
from aggie_analytics.data.tamu_official_rich_structure import is_rich_structured
from aggie_analytics.data.tamu_official_statcrew_preformatted import (
    GATE_RELATIVE as STATCREW_GATE_RELATIVE,
)
from aggie_analytics.validation.artifact_binding import compute_identity


SCHEMA_VERSION = "aggie.data.tamu_official_gamebook_union_enriched.v1"
CONTRACT_RELATIVE = "configs/tamu_official_gamebook_union_enriched_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_gamebook_union_enriched_gate.json"
CONTRACT_ID = "BAT-592-TAMU-OFFICIAL-GAMEBOOK-UNION-ENRICHED-V1"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_OFFICIAL_GAMEBOOK_UNION_ENRICHED_CANDIDATE_ONLY"
PASS_RESULT = "PASS_IMMUTABLE_PRIOR_UNIONS_PRESERVED_STATCREW_OVERLAY_APPLIED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PRIOR_237_UNION_IDENTITY = "d7f9ece5a5a79e190dd845bcd04e0d648469486b9f702c943feeb101898c2e31"
PRIOR_237_GATE_IDENTITY = "537de885b49e6e4574dfe5622b0d3f0db07a081f213e96b5ae14d5e1ee011297"
PRIOR_226_UNION_IDENTITY = "a5444d7c80baeb25751c8cac2338e86c5ac8746398bd94e61e1c43cb83916f4e"
PRIOR_226_GATE_IDENTITY = "77043db845ea4089e7530509b29489c3b76455e6db7eaea299854f316b6febe9"
CYCLE9_UNION_IDENTITY = "050fb22e733f3dc296a5bafed9f89a20281efb06860dc220264d074a7e9b7672"
CYCLE9_GATE_IDENTITY = "dd0d0f32c499b4863551a9ab6649cbef7638c3916228661262fbd5a71909c106"
STATCREW_PAYLOAD_IDENTITY = "ba0820e45938714c144c4accee6637a67812e70dd89e4eb99b0373fc88a91d1d"
STATCREW_GATE_IDENTITY = "9c3da52dceebd8da0908aa478326196bef2338095a8b5d4c42decaa27df53e16"
INVENTORY_IDENTITY = "d39d35ff7cfacf2e39a524d0f1fdb97072158c50f84225ed8413771140efaa37"
PRIOR_237_CAPTURED_GAMES = 237
PRIOR_237_RICH = 191
PRIOR_237_METADATA = 46
OVERLAY_DOMAINS = (
    "team_statistics",
    "individual_player_statistics",
    "drives",
    "play_by_play",
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
    "missing_domains",
    "admissions",
    "authority",
    "scientific_nonclaims",
    "protected_lane",
    "upstream_identities",
)


class AuthorityViolation(ValueError):
    """Raised when the enriched union invents identity, admits a rejected game, or opens a sealed lane."""


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
        "completeness_claim": False,
        "contest_id_fabrication": False,
        "ncaa_contest_identity": False,
        "name_only_promotion": False,
        "availability_claim": False,
        "historical_known_at_from_capture_time": False,
        "champion_or_production_promotion": False,
        "wmt_payload_mutated_in_place": False,
        "prior_union_mutated_in_place": False,
        "statcrew_payload_mutated_in_place": False,
        "rejected_game_admitted": False,
        "bat_523_closed": False,
        "bat_429_ready_or_done": False,
    }


def expected_scientific_nonclaims() -> dict[str, bool]:
    return {
        "completeness_claimed": False,
        "historical_known_at_established": False,
        "historical_population_ready": False,
        "pregame_availability_admitted": False,
        "ncaa_contest_ids_invented": False,
        "name_only_promoted": False,
        "protected_lane_opened": False,
        "champion_or_production_promotion": False,
        "wmt_payload_mutated": False,
        "prior_203_union_rewritten": False,
        "prior_226_union_rewritten": False,
        "prior_237_union_rewritten": False,
        "statcrew_payload_rewritten": False,
        "rejected_games_admitted": False,
        "bat_523_closed": False,
        "bat_429_advanced": False,
    }


def expected_admissions() -> dict[str, str]:
    return {
        "union_admission": "CANDIDATE_ONLY",
        "source_authority": "SRC-014_OFFICIAL_SCHOOL_EVIDENCE",
        "ncaa_contest_identity": "NOT_CREATED",
        "wmt_payload": "PRESERVED_IMMUTABLE",
        "cycle9_203_union": "PRESERVED_IMMUTABLE",
        "bat_587_226_union": "PRESERVED_IMMUTABLE",
        "bat_590_237_union": "PRESERVED_IMMUTABLE_SUPERSEDED_AS_PRIOR_LAYER",
        "bat_591_statcrew": "CONSUMED_PREFORMATTED_DOMAINS_ONLY",
        "historical_known_at": "UNKNOWN_CAPTURE_TIME_ONLY",
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "bat_523": "IN_PROGRESS",
        "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
        "gap_005": "OPEN",
    }


def _statcrew_index(statcrew_gate: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for game in statcrew_gate.get("games") or []:
        url = str(game.get("url") or "")
        if not url:
            raise AuthorityViolation("StatCrew compact game is missing a URL")
        if url in index:
            raise AuthorityViolation(f"duplicate StatCrew URL {url}")
        index[url] = game
    return index


def overlay_game(game: Mapping[str, Any], statcrew: Mapping[str, Any] | None) -> dict[str, Any]:
    row = json.loads(json.dumps(game))
    coverage = dict(row.get("domain_coverage") or {})
    prior_rich = is_rich_structured(row)
    row["prior_rich_structured"] = prior_rich
    row["overlay_applied"] = False
    row["overlay_source"] = None
    if statcrew is None:
        row["rich_structured"] = prior_rich
        row["domain_coverage"] = coverage
        return row
    if str(statcrew.get("source_sha256") or "") != str(row.get("source_sha256") or ""):
        raise AuthorityViolation(
            f"StatCrew raw hash does not match admitted game {row.get('url')}"
        )
    for domain in OVERLAY_DOMAINS:
        if (statcrew.get("domain_coverage") or {}).get(domain) == "PRESENT":
            coverage[domain] = "PRESENT"
    row["domain_coverage"] = coverage
    row["overlay_applied"] = True
    row["overlay_source"] = "BAT-591-STATCREW-PREFORMATTED"
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


def missing_domains(games: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for game in games:
        absent = [
            domain
            for domain in OVERLAY_DOMAINS
            if (game.get("domain_coverage") or {}).get(domain) != "PRESENT"
        ]
        if absent:
            rows.append({"url": game.get("url"), "absent_domains": absent})
    return rows


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    registry = repo_root / "governance/PROTECTED_SPLIT_REGISTRY.csv"
    digest = hashlib.sha256(registry.read_bytes()).hexdigest()
    if digest != REGISTRY_SHA256:
        raise AuthorityViolation("protected-split registry identity drift")
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise AuthorityViolation("enriched-union contract identity drift")
    prior_237 = load_json(repo_root / PRIOR_237_GATE_RELATIVE)
    if prior_237.get("union_identity") != PRIOR_237_UNION_IDENTITY:
        raise AuthorityViolation("BAT-590 237-game union identity was rewritten")
    if prior_237.get("gate_identity") != PRIOR_237_GATE_IDENTITY:
        raise AuthorityViolation("BAT-590 237-game union gate identity was rewritten")
    if int(prior_237.get("counts", {}).get("union_captured_games") or 0) != PRIOR_237_CAPTURED_GAMES:
        raise AuthorityViolation("BAT-590 captured-game count drifted")
    if prior_237.get("upstream_identities", {}).get("wmt_dataset_identity") != WMT_DATASET_IDENTITY:
        raise AuthorityViolation("WMT dataset identity was rewritten")
    prior_226 = load_json(repo_root / PRIOR_226_GATE_RELATIVE)
    if prior_226.get("union_identity") != PRIOR_226_UNION_IDENTITY:
        raise AuthorityViolation("BAT-587 226-game union identity was rewritten")
    if prior_226.get("gate_identity") != PRIOR_226_GATE_IDENTITY:
        raise AuthorityViolation("BAT-587 226-game union gate identity was rewritten")
    if prior_226.get("prior_union_identity") != CYCLE9_UNION_IDENTITY:
        raise AuthorityViolation("Cycle #9 203-game union identity was rewritten")
    if prior_226.get("prior_union_gate_identity") != CYCLE9_GATE_IDENTITY:
        raise AuthorityViolation("Cycle #9 203-game union gate identity was rewritten")
    statcrew = load_json(repo_root / STATCREW_GATE_RELATIVE)
    if statcrew.get("payload_identity") != STATCREW_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-591 payload identity was rewritten")
    if statcrew.get("gate_identity") != STATCREW_GATE_IDENTITY:
        raise AuthorityViolation("BAT-591 gate identity was rewritten")
    statcrew_by_url = _statcrew_index(statcrew)
    admitted = list(prior_226.get("admitted_pre2010_games") or []) + list(
        prior_237.get("admitted_official_2007_games") or []
    )
    rejected = list(prior_226.get("rejected_pre2010_games") or []) + list(
        prior_237.get("rejected_official_2007_games") or []
    )
    rejected_urls = {str(item.get("url") or "") for item in rejected}
    overlays: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for game in admitted:
        url = str(game.get("url") or "")
        if url in rejected_urls:
            raise AuthorityViolation(f"rejected game was presented for overlay admission: {url}")
        if url in seen_urls:
            raise AuthorityViolation(f"duplicate official game presented for overlay: {url}")
        seen_urls.add(url)
        overlays.append(overlay_game(game, statcrew_by_url.get(url)))
    for game in rejected:
        url = str(game.get("url") or "")
        if url in seen_urls:
            raise AuthorityViolation(f"rejected game leaked into overlay membership: {url}")
        if url in statcrew_by_url:
            conflicts.append(
                {
                    "url": url,
                    "conflict_status": "STATCREW_PRESENT_BUT_PRIOR_REJECTION_PRESERVED",
                    "match_status": game.get("canonical_game_match_status") or game.get("rejection_reason"),
                    "opponent_candidate": game.get("opponent_candidate"),
                }
            )
    became_rich = sum(1 for item in overlays if item["rich_structured"] and not item["prior_rich_structured"])
    overlays_applied = sum(1 for item in overlays if item["overlay_applied"])
    counts = {
        "wmt_games_preserved": WMT_TARGET_GAMES,
        "cycle9_official_games_preserved": 26,
        "cycle9_union_games_preserved": 203,
        "prior_226_union_games_preserved": 226,
        "prior_237_union_games_preserved": PRIOR_237_CAPTURED_GAMES,
        "union_target_games": PRIOR_237_CAPTURED_GAMES,
        "union_captured_games": PRIOR_237_CAPTURED_GAMES,
        "new_games_added": 0,
        "overlays_applied": overlays_applied,
        "overlays_became_rich": became_rich,
        "duplicates_rejected": 0,
        "unmatched_rejected": len(rejected),
        "rich_structured_games": PRIOR_237_RICH + became_rich,
        "metadata_only_games": PRIOR_237_METADATA - became_rich,
        "matched_strong_tuple": sum(
            1
            for item in overlays
            if item.get("canonical_game_match_status") == "MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE"
        ),
        "date_conflicts": sum(1 for item in overlays if item.get("conflict_status") not in {None, "NONE"}),
        "ncaa_contest_ids_created": 0,
        "wmt_rich_structured_games": WMT_RICH_GAMES,
        "wmt_metadata_only_games": WMT_METADATA_ONLY,
    }
    if counts["union_captured_games"] != counts["rich_structured_games"] + counts["metadata_only_games"]:
        raise AuthorityViolation("enriched rich/metadata arithmetic drifted")
    if any(item.get("url") in seen_urls for item in rejected):
        raise AuthorityViolation("rejected games were admitted")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "prior_union_identity": PRIOR_237_UNION_IDENTITY,
        "prior_union_gate_identity": PRIOR_237_GATE_IDENTITY,
        "statcrew_payload_identity": STATCREW_PAYLOAD_IDENTITY,
        "enriched_official_games": overlays,
        "preserved_rejections": rejected,
        "counts": counts,
        "conflicts": conflicts,
        "scientific_nonclaims": expected_scientific_nonclaims(),
    }
    payload["union_identity"] = stable_hash(
        {
            "prior_union_identity": PRIOR_237_UNION_IDENTITY,
            "statcrew_payload_identity": STATCREW_PAYLOAD_IDENTITY,
            "enriched_official_games": overlays,
            "preserved_rejections": rejected,
            "counts": counts,
        }
    )
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_GAMEBOOK_UNION_ENRICHED_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": "POST-TASK-SRC014-ENRICHED-UNION-001",
        "jira_key": "BAT-592",
        "disposition": "NEW_IMMUTABLE_IDENTITY_PRIOR_237_PRESERVED_STATCREW_OVERLAY",
        "source_id": SOURCE_ID,
        "prior_union_identity": PRIOR_237_UNION_IDENTITY,
        "prior_union_gate_identity": PRIOR_237_GATE_IDENTITY,
        "union_identity": payload["union_identity"],
        "selected_seasons": [2009, 2008, 2007],
        "counts": counts,
        "coverage_by_season": coverage_by_season(overlays),
        "coverage_by_domain": coverage_by_domain(overlays),
        "enriched_official_games": overlays,
        "preserved_rejections": rejected,
        "conflicts": conflicts,
        "missing_domains": missing_domains(overlays),
        "admissions": expected_admissions(),
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "protected_lane": PROTECTED_LANE,
        "upstream_identities": {
            "wmt_acquisition_identity": WMT_ACQUISITION_IDENTITY,
            "wmt_dataset_identity": WMT_DATASET_IDENTITY,
            "cycle9_boxscore_gate_identity": BOXSCORE_GATE_IDENTITY,
            "cycle9_boxscore_dataset_identity": BOXSCORE_DATASET_IDENTITY,
            "cycle9_boxscore_games_identity": PINNED_GAMES_IDENTITY,
            "cycle9_union_identity": CYCLE9_UNION_IDENTITY,
            "cycle9_union_gate_identity": CYCLE9_GATE_IDENTITY,
            "bat587_union_identity": PRIOR_226_UNION_IDENTITY,
            "bat587_gate_identity": PRIOR_226_GATE_IDENTITY,
            "bat590_union_identity": PRIOR_237_UNION_IDENTITY,
            "bat590_gate_identity": PRIOR_237_GATE_IDENTITY,
            "bat591_payload_identity": STATCREW_PAYLOAD_IDENTITY,
            "bat591_gate_identity": STATCREW_GATE_IDENTITY,
            "inventory_identity": INVENTORY_IDENTITY,
            "protected_split_registry_sha256": REGISTRY_SHA256,
        },
    }
    if counts["ncaa_contest_ids_created"]:
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if any(item.get("ncaa_contest_id") for item in overlays):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if any(item.get("availability_claim") for item in overlays):
        raise AuthorityViolation("pregame availability claimed")
    if any(item.get("historical_publication_time") is not None for item in overlays):
        raise AuthorityViolation("retrieval time promoted to historical known-at")
    if counts["new_games_added"] != 0:
        raise AuthorityViolation("enriched union invented a new admission")
    gate["gate_identity"] = compute_gate_identity(gate)
    payload["gate_identity"] = gate["gate_identity"]
    return {
        "contract": contract,
        "gate": gate,
        "payload": payload,
        "prior_237": prior_237,
        "statcrew": statcrew,
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
        / "features/tamu_official_statcrew_preformatted/sha256"
        / STATCREW_PAYLOAD_IDENTITY
        / "payload.json"
    ).is_file()


def validate_compact_gate(committed: Mapping[str, Any]) -> None:
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("prior_union_identity") != PRIOR_237_UNION_IDENTITY:
        raise AuthorityViolation("prior 237-game union identity was rewritten")
    if committed.get("prior_union_gate_identity") != PRIOR_237_GATE_IDENTITY:
        raise AuthorityViolation("prior 237-game union gate identity was rewritten")
    if committed.get("result") != PASS_RESULT:
        raise AuthorityViolation("completion forged")
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("classification forged")
    if committed.get("authority", {}).get("historical_known_at_from_capture_time"):
        raise AuthorityViolation("retrieval time promoted to historical known-at")
    if committed.get("counts", {}).get("ncaa_contest_ids_created"):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if committed.get("counts", {}).get("new_games_added"):
        raise AuthorityViolation("enriched union invented a new admission")
    if committed.get("admissions", {}).get("pregame_availability") != "BLOCKED":
        raise AuthorityViolation("pregame availability admitted")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not recompute")
    if not committed.get("union_identity"):
        raise AuthorityViolation("union identity missing")
    if int(committed.get("counts", {}).get("union_captured_games") or 0) != PRIOR_237_CAPTURED_GAMES:
        raise AuthorityViolation("union captured-game arithmetic drifted")
    rejected_urls = {str(item.get("url") or "") for item in committed.get("preserved_rejections") or []}
    admitted_urls = {str(item.get("url") or "") for item in committed.get("enriched_official_games") or []}
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
        raise AuthorityViolation("external enriched-union reconstruction was required but the data root is not mounted")
    if not ready:
        return {
            "result": "PASS",
            "gate_identity": committed["gate_identity"],
            "union_identity": committed["union_identity"],
            "external_reconstruction": "NOT_MOUNTED",
        }
    expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    if committed != expected["gate"]:
        raise AuthorityViolation("committed enriched-union gate does not match independent reconstruction")
    return {
        "result": "PASS",
        "gate_identity": expected["gate"]["gate_identity"],
        "union_identity": expected["gate"]["union_identity"],
        "counts": expected["gate"]["counts"],
        "external_reconstruction": "MOUNTED",
    }


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]

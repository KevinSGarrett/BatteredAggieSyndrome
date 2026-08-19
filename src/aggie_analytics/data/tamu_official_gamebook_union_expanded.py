"""New immutable SRC-014 union identity admitting independently matched 2008-2009 official games."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import normalize_team_name, stable_hash
from aggie_analytics.validation.artifact_binding import compute_identity
from aggie_analytics.data.tamu_official_gamebook_union import (
    BOXSCORE_DATASET_IDENTITY,
    BOXSCORE_GATE_IDENTITY,
    GATE_RELATIVE as PRIOR_UNION_GATE_RELATIVE,
    PINNED_GAMES_IDENTITY,
    REGISTRY_SHA256,
    WMT_ACQUISITION_IDENTITY,
    WMT_DATASET_IDENTITY,
    WMT_METADATA_ONLY,
    WMT_RICH_GAMES,
    WMT_TARGET_GAMES,
)
from aggie_analytics.data.tamu_official_pre2010_boxscores import (
    CONTRACT_RELATIVE as PRE2010_CONTRACT_RELATIVE,
    GATE_RELATIVE as PRE2010_GATE_RELATIVE,
)
from aggie_analytics.data.tamu_official_rich_structure import (
    is_rich_structured,
)


SCHEMA_VERSION = "aggie.data.tamu_official_gamebook_union_expanded.v1"
CONTRACT_RELATIVE = "configs/tamu_official_gamebook_union_expanded_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_gamebook_union_expanded_gate.json"
CONTRACT_ID = "BAT-587-TAMU-OFFICIAL-GAMEBOOK-UNION-EXPANDED-V1"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_OFFICIAL_GAMEBOOK_UNION_EXPANDED_CANDIDATE_ONLY"
PASS_RESULT = "PASS_IMMUTABLE_PRIOR_UNION_PRESERVED_OFFICIAL_2008_2009_ADDED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PRIOR_UNION_IDENTITY = "050fb22e733f3dc296a5bafed9f89a20281efb06860dc220264d074a7e9b7672"
PRIOR_UNION_GATE_IDENTITY = "dd0d0f32c499b4863551a9ab6649cbef7638c3916228661262fbd5a71909c106"
INVENTORY_IDENTITY = "d39d35ff7cfacf2e39a524d0f1fdb97072158c50f84225ed8413771140efaa37"
PRE2010_GATE_IDENTITY = "c62a09d2b3bcf7e69c6b6ea90993084d124a779d7ab779e8ebeab300b2a9c006"
PRE2010_DATASET_IDENTITY = "1858893908f59afc8f6e88fea46764666869d7c809ddf2b3fedbdfcea02b6b59"
PRE2010_GAMES_IDENTITY = "176ae7a0f6f93de591c850cd49da280682ac328c4ebf7a0b0d0beb78b24d4b7a"
PRE2010_ACQUISITION_IDENTITY = "58c44cc252a6139a7618a779e9fc9b353949cf942ac93eeb08c38b6c697a62af"
ADMITTED_STATUSES = frozenset(
    {
        "MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE",
        "OFFICIAL_INDEX_DATE_CONFLICT",
    }
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
    "prior_union_identity",
    "prior_union_gate_identity",
    "union_identity",
    "selected_seasons",
    "counts",
    "coverage_by_season",
    "coverage_by_domain",
    "admitted_pre2010_games",
    "rejected_pre2010_games",
    "conflicts",
    "admissions",
    "authority",
    "scientific_nonclaims",
    "protected_lane",
    "upstream_identities",
)


class AuthorityViolation(ValueError):
    """Raised when the expanded union invents identity, mutates a prior payload, or opens a sealed lane."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
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
        "cycle9_boxscore_mutated_in_place": False,
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
        "bat_523_closed": False,
        "bat_429_advanced": False,
    }


def expected_admissions() -> dict[str, str]:
    return {
        "union_admission": "CANDIDATE_ONLY",
        "source_authority": "SRC-014_OFFICIAL_SCHOOL_EVIDENCE",
        "ncaa_contest_identity": "NOT_CREATED",
        "wmt_payload": "PRESERVED_IMMUTABLE",
        "cycle9_official_2010_2011": "PRESERVED_IMMUTABLE",
        "cycle9_203_union": "PRESERVED_IMMUTABLE_SUPERSEDED_AS_PRIOR_LAYER",
        "historical_known_at": "UNKNOWN_CAPTURE_TIME_ONLY",
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "bat_523": "IN_PROGRESS",
        "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
        "gap_005": "OPEN",
    }


def compact_game(game: Mapping[str, Any]) -> dict[str, Any]:
    row = {key: game.get(key) for key in COMPACT_FIELDS}
    row["source_season"] = int(game.get("source_season") or game.get("football_season") or 0)
    row["ncaa_contest_id"] = None
    row["canonical_game_id"] = None
    row["availability_claim"] = False
    row["historical_publication_time"] = None
    return row


def game_key(game: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        int(game.get("source_season") or game.get("football_season") or game.get("season") or 0),
        str(game.get("calendar_date") or game.get("game_date") or "")[:10],
        normalize_team_name(str(game.get("opponent_normalized") or game.get("opponent_candidate") or game.get("opponent_name") or "")),
        game.get("tamu_points"),
        game.get("opponent_points"),
    )


def load_prior_union(repo_root: Path) -> dict[str, Any]:
    gate = load_json(repo_root / PRIOR_UNION_GATE_RELATIVE)
    if gate.get("union_identity") != PRIOR_UNION_IDENTITY or gate.get("gate_identity") != PRIOR_UNION_GATE_IDENTITY:
        raise AuthorityViolation("Cycle #9 203-game union identity drifted")
    if gate.get("counts", {}).get("union_captured_games") != 203:
        raise AuthorityViolation("Cycle #9 union captured-game count drifted")
    if gate.get("counts", {}).get("wmt_preserved_games") != WMT_TARGET_GAMES:
        raise AuthorityViolation("WMT preserved-game count drifted")
    if gate.get("upstream_identities", {}).get("boxscore_games_identity") != PINNED_GAMES_IDENTITY:
        raise AuthorityViolation("Cycle #9 official 26-game identity drifted")
    if gate.get("upstream_identities", {}).get("wmt_dataset_identity") != WMT_DATASET_IDENTITY:
        raise AuthorityViolation("WMT dataset identity was rewritten")
    return gate


def load_pre2010_games(repo_root: Path, data_root: Path) -> list[dict[str, Any]]:
    gate = load_json(repo_root / PRE2010_GATE_RELATIVE)
    if gate.get("gate_identity") != PRE2010_GATE_IDENTITY:
        raise AuthorityViolation("BAT-586 gate identity drifted")
    if gate.get("dataset_identity") != PRE2010_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-586 dataset identity drifted")
    if gate.get("inventory_identity") != INVENTORY_IDENTITY:
        raise AuthorityViolation("BAT-586 is not bound to the BAT-585 inventory identity")
    contract = load_json(repo_root / PRE2010_CONTRACT_RELATIVE)
    payload_path = data_root / contract["payloads"]["normalized_root"] / PRE2010_DATASET_IDENTITY / "payload.json"
    if not payload_path.is_file():
        raise AuthorityViolation("external BAT-586 payload is not mounted")
    payload = load_json(payload_path)
    if payload.get("games_identity") != PRE2010_GAMES_IDENTITY:
        raise AuthorityViolation("BAT-586 games identity drifted")
    return [compact_game(item) for item in payload.get("games") or []]


def classify_pre2010(games: list[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    admitted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for game in games:
        status = str(game.get("canonical_game_match_status") or "")
        row = dict(game)
        if status in ADMITTED_STATUSES:
            admitted.append(row)
            continue
        row["rejection_reason"] = status or "UNMATCHED_STRONG_TUPLE"
        if status == "NAME_ONLY_INSUFFICIENT" or game.get("name_only_promotion"):
            raise AuthorityViolation("name-only promotion cannot be admitted")
        rejected.append(row)
    admitted = sorted(admitted, key=lambda item: (item["football_season"], item["calendar_date"], item["url"]))
    rejected = sorted(rejected, key=lambda item: (item["football_season"], item["calendar_date"], item["url"]))
    return admitted, rejected


def detect_duplicates(
    admitted: list[Mapping[str, Any]],
    prior_official: list[Mapping[str, Any]],
    wmt_games: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    prior_keys = {game_key(item) for item in prior_official}
    wmt_keys = {
        (
            int(item.get("season") or 0),
            str(item.get("game_date") or item.get("calendar_date") or "")[:10],
            normalize_team_name(str(item.get("opponent_name") or item.get("opponent_normalized") or "")),
            item.get("tamu_points"),
            item.get("opponent_points"),
        )
        for item in wmt_games
    }
    duplicates: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    urls: set[str] = set()
    for game in admitted:
        key = game_key(game)
        url = str(game.get("url") or "")
        if key in seen or url in urls or key in prior_keys or key in wmt_keys:
            duplicates.append({"url": url, "key": [str(part) for part in key], "reason": "DUPLICATE_ACROSS_LAYERS"})
            continue
        seen.add(key)
        if url:
            urls.add(url)
    return duplicates


def coverage_by_season(admitted: list[Mapping[str, Any]]) -> dict[str, Any]:
    by_season: dict[str, dict[str, int]] = {}
    for game in admitted:
        key = str(game["source_season"])
        bucket = by_season.setdefault(
            key,
            {
                "official_school_games": 0,
                "rich_structured_games": 0,
                "metadata_only_games": 0,
                "matched_strong_tuple": 0,
                "date_conflicts": 0,
            },
        )
        bucket["official_school_games"] += 1
        if is_rich_structured(game):
            bucket["rich_structured_games"] += 1
        else:
            bucket["metadata_only_games"] += 1
        if game.get("canonical_game_match_status") == "MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE":
            bucket["matched_strong_tuple"] += 1
        if game.get("conflict_status") not in {None, "NONE"}:
            bucket["date_conflicts"] += 1
    return {key: by_season[key] for key in sorted(by_season, reverse=True)}


def coverage_by_domain(admitted: list[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    domains = (
        "game_identity_metadata",
        "season",
        "played_date",
        "teams",
        "scores",
        "quarter_scoring",
        "site_venue",
        "attendance",
        "officials",
        "scoring_summary",
        "participation",
        "starters",
        "team_statistics",
        "individual_player_statistics",
        "drives",
        "play_by_play",
    )
    totals: dict[str, dict[str, int]] = {}
    for domain in domains:
        present = sum(1 for game in admitted if (game.get("domain_coverage") or {}).get(domain) == "PRESENT")
        totals[domain] = {
            "official_pre2010_present": present,
            "official_pre2010_absent": len(admitted) - present,
            "eligibility": "OFFICIAL_SCHOOL_POSTGAME_CANDIDATE_NOT_PREGAME_NOT_NCAA_CONTEST",
        }
    totals["pregame_availability"] = {
        "official_pre2010_present": 0,
        "official_pre2010_absent": len(admitted),
        "eligibility": "NOT_PROVIDED_BY_ROUTE",
    }
    return totals


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    registry = repo_root / "governance/PROTECTED_SPLIT_REGISTRY.csv"
    digest = hashlib.sha256(registry.read_bytes()).hexdigest()
    if digest != REGISTRY_SHA256:
        raise AuthorityViolation("protected-split registry identity drift")
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise AuthorityViolation("expanded-union contract identity drift")
    prior = load_prior_union(repo_root)
    games = load_pre2010_games(repo_root, data_root)
    admitted, rejected = classify_pre2010(games)
    duplicates = detect_duplicates(admitted, prior.get("official_games") or [], [])
    if duplicates:
        raise AuthorityViolation(f"duplicate official games were presented for admission: {duplicates}")
    admitted_2009 = [item for item in admitted if int(item["source_season"]) == 2009]
    admitted_2008 = [item for item in admitted if int(item["source_season"]) == 2008]
    prior_rich = int(prior["counts"]["rich_structured_games"])
    prior_meta = int(prior["counts"]["metadata_only_games"])
    new_rich = sum(1 for item in admitted if is_rich_structured(item))
    new_meta = len(admitted) - new_rich
    counts = {
        "wmt_games_preserved": WMT_TARGET_GAMES,
        "cycle9_official_games_preserved": 26,
        "prior_union_games_preserved": 203,
        "official_2009_added": len(admitted_2009),
        "official_2008_added": len(admitted_2008),
        "new_games_added": len(admitted),
        "duplicates_rejected": 0,
        "unmatched_rejected": len(rejected),
        "union_target_games": 203 + len(admitted),
        "union_captured_games": 203 + len(admitted),
        "rich_structured_games": prior_rich + new_rich,
        "metadata_only_games": prior_meta + new_meta,
        "matched_strong_tuple": sum(
            1 for item in admitted if item.get("canonical_game_match_status") == "MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE"
        ),
        "date_conflicts": sum(1 for item in admitted if item.get("conflict_status") not in {None, "NONE"}),
        "ncaa_contest_ids_created": 0,
        "wmt_rich_structured_games": WMT_RICH_GAMES,
        "wmt_metadata_only_games": WMT_METADATA_ONLY,
    }
    conflicts = [
        {
            "url": item["url"],
            "opponent_candidate": item.get("opponent_candidate"),
            "calendar_date": item.get("calendar_date"),
            "index_date_candidate": item.get("index_date_candidate"),
            "conflict_status": item.get("conflict_status"),
            "match_status": item.get("canonical_game_match_status"),
        }
        for item in admitted
        if item.get("conflict_status") not in {None, "NONE"}
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "prior_union_identity": PRIOR_UNION_IDENTITY,
        "prior_union_gate_identity": PRIOR_UNION_GATE_IDENTITY,
        "admitted_pre2010_games": admitted,
        "rejected_pre2010_games": rejected,
        "counts": counts,
        "conflicts": conflicts,
        "scientific_nonclaims": expected_scientific_nonclaims(),
    }
    payload["union_identity"] = stable_hash(
        {
            "prior_union_identity": PRIOR_UNION_IDENTITY,
            "admitted_pre2010_games": admitted,
            "rejected_pre2010_games": rejected,
            "counts": counts,
        }
    )
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_GAMEBOOK_UNION_EXPANDED_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": "POST-TASK-CYCLE-10-SRC014-EXPANDED-GAMEBOOK-UNION-001",
        "jira_key": "BAT-587",
        "disposition": "NEW_IMMUTABLE_IDENTITY_PRIOR_203_PRESERVED_OFFICIAL_2008_2009_ADDED",
        "source_id": SOURCE_ID,
        "prior_union_identity": PRIOR_UNION_IDENTITY,
        "prior_union_gate_identity": PRIOR_UNION_GATE_IDENTITY,
        "union_identity": payload["union_identity"],
        "selected_seasons": [2009, 2008],
        "counts": counts,
        "coverage_by_season": coverage_by_season(admitted),
        "coverage_by_domain": coverage_by_domain(admitted),
        "admitted_pre2010_games": admitted,
        "rejected_pre2010_games": rejected,
        "conflicts": conflicts,
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
            "prior_union_identity": PRIOR_UNION_IDENTITY,
            "prior_union_gate_identity": PRIOR_UNION_GATE_IDENTITY,
            "inventory_identity": INVENTORY_IDENTITY,
            "pre2010_gate_identity": PRE2010_GATE_IDENTITY,
            "pre2010_dataset_identity": PRE2010_DATASET_IDENTITY,
            "pre2010_games_identity": PRE2010_GAMES_IDENTITY,
            "pre2010_acquisition_identity": PRE2010_ACQUISITION_IDENTITY,
            "protected_split_registry_sha256": REGISTRY_SHA256,
        },
    }
    if counts["ncaa_contest_ids_created"]:
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if any(item.get("ncaa_contest_id") for item in admitted):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if any(item.get("availability_claim") for item in admitted):
        raise AuthorityViolation("pregame availability claimed")
    if any(item.get("historical_publication_time") is not None for item in admitted):
        raise AuthorityViolation("retrieval time promoted to historical known-at")
    gate["gate_identity"] = compute_gate_identity(gate)
    payload["gate_identity"] = gate["gate_identity"]
    return {"contract": contract, "gate": gate, "payload": payload, "prior": prior}


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
        / "features/tamu_official_pre2010_boxscores/sha256"
        / PRE2010_DATASET_IDENTITY
        / "payload.json"
    ).is_file()


def validate_compact_gate(committed: Mapping[str, Any]) -> None:
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("prior_union_identity") != PRIOR_UNION_IDENTITY:
        raise AuthorityViolation("prior 203-game union identity was rewritten")
    if committed.get("prior_union_gate_identity") != PRIOR_UNION_GATE_IDENTITY:
        raise AuthorityViolation("prior 203-game union gate identity was rewritten")
    if committed.get("result") != PASS_RESULT:
        raise AuthorityViolation("completion forged")
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("classification forged")
    if committed.get("authority", {}).get("historical_known_at_from_capture_time"):
        raise AuthorityViolation("retrieval time promoted to historical known-at")
    if committed.get("counts", {}).get("ncaa_contest_ids_created"):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if committed.get("admissions", {}).get("pregame_availability") != "BLOCKED":
        raise AuthorityViolation("pregame availability admitted")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not recompute")
    if not committed.get("union_identity"):
        raise AuthorityViolation("union identity missing")
    if int(committed.get("counts", {}).get("union_captured_games") or 0) != 203 + int(
        committed.get("counts", {}).get("new_games_added") or 0
    ):
        raise AuthorityViolation("union captured-game arithmetic drifted")


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
        raise AuthorityViolation("external expanded-union reconstruction was required but the data root is not mounted")
    if not ready:
        return {
            "result": "PASS",
            "gate_identity": committed["gate_identity"],
            "union_identity": committed["union_identity"],
            "external_reconstruction": "NOT_MOUNTED",
        }
    expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    if committed != expected["gate"]:
        raise AuthorityViolation("committed expanded-union gate does not match independent reconstruction")
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

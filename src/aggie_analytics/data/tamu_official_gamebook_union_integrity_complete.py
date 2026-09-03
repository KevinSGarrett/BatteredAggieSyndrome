"""Integrity-complete successor to BAT-607 with fail-closed union manifests and BAT-606 raw reconstruction."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import sha256_file, stable_hash
from aggie_analytics.data.tamu_official_2004_structured_domains import (
    CONTRACT_RELATIVE as BAT606_CONTRACT_RELATIVE,
    GATE_RELATIVE as BAT606_GATE_RELATIVE,
    PREFORMATTED_PARSER_IDENTITY,
    reconstruct_objects as reconstruct_bat606_raw,
)
from aggie_analytics.data.tamu_official_gamebook_union import REGISTRY_SHA256
from aggie_analytics.data.tamu_official_gamebook_union_2004_expanded import (
    PINNED_BAT602_GATE_IDENTITY,
    PINNED_BAT602_UNION_IDENTITY,
    PINNED_BAT604_GATE_IDENTITY,
    PINNED_BAT605_ACQUISITION_IDENTITY,
    PINNED_BAT605_DATASET_IDENTITY,
    PINNED_BAT605_GAMES_IDENTITY,
    PINNED_BAT605_GATE_IDENTITY,
    PINNED_BAT606_GATE_IDENTITY,
    PINNED_BAT606_PAYLOAD_IDENTITY,
    PINNED_UNION_IDENTITY as PINNED_BAT607_UNION_IDENTITY,
    PINNED_UNION_MANIFEST_FILE_SHA256 as PINNED_BAT607_UNION_MANIFEST_FILE_SHA256,
    require_authoritative_union_manifest as require_bat607_union_manifest,
    union_manifest_path as bat607_union_manifest_path,
    upstream_is_ready as bat607_upstream_is_ready,
    validate_artifact as validate_bat607,
)
from aggie_analytics.data.tamu_official_gamebook_union_2005_expanded import PRESERVED_REJECTION_URLS
from aggie_analytics.data.tamu_official_gamebook_union_2005_integrity_bound import (
    PINNED_BAT591_GATE_IDENTITY,
    PINNED_BAT591_PAYLOAD_IDENTITY,
    PINNED_BAT596_GATE_IDENTITY,
    PINNED_BAT596_PAYLOAD_IDENTITY,
    PINNED_UNION_IDENTITY as PINNED_BAT603_UNION_IDENTITY,
    PINNED_UNION_MANIFEST_FILE_SHA256 as PINNED_BAT603_UNION_MANIFEST_FILE_SHA256,
    coverage_by_domain,
    coverage_by_season,
    require_authoritative_union_manifest as require_bat603_union_manifest,
    union_manifest_path as bat603_union_manifest_path,
    validate_artifact as validate_bat603,
)
from aggie_analytics.data.tamu_official_historical_boxscores import AuthorityViolation
from aggie_analytics.data.tamu_official_rich_structure import scoring_summary_present
from aggie_analytics.data.tamu_official_statcrew_preformatted import DOMAINS
from aggie_analytics.validation.artifact_binding import compute_identity


SCHEMA_VERSION = "aggie.data.tamu_official_gamebook_union_integrity_complete.v1"
VALIDATION_CONTRACT_VERSION = "aggie.data.tamu_official_gamebook_union_integrity_complete.v1"
CONTRACT_RELATIVE = "configs/tamu_official_gamebook_union_integrity_complete_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_gamebook_union_integrity_complete_gate.json"
MODULE_RELATIVE = "src/aggie_analytics/data/tamu_official_gamebook_union_integrity_complete.py"
CONTRACT_ID = "BAT-608-TAMU-OFFICIAL-GAMEBOOK-UNION-INTEGRITY-COMPLETE-V1"
DECISION_UNIT = "POST-TASK-SRC014-UNION-CONSUMER-INTEGRITY-001"
JIRA_KEY = "BAT-608"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_OFFICIAL_GAMEBOOK_UNION_INTEGRITY_COMPLETE_CANDIDATE_ONLY"
PASS_RESULT = "PASS_IMMUTABLE_BAT607_PRESERVED_INDEPENDENT_BAT606_RAW_BINDINGS"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PINNED_BAT603_GATE_IDENTITY = "aaf307e5c2a42b48ea88b2745c965b5290a3d4312a71d48db49cf16a6a30e88b"
PINNED_BAT607_GATE_IDENTITY = "e79c5b01a5f4e654add4ad492714578be17bbd577e3bf080159dc133639f3b8b"
PINNED_UNION_IDENTITY = "2af6bf25cce6b9f63edcd4285931b7bbe1093de7e9b927ec00028a4df348de75"
PINNED_GATE_IDENTITY = "873c90f94ffeb414178d25f9a12ec9c897c2d8d745bc4824de3642845a00fc8c"
PINNED_VALIDATOR_CODE_IDENTITY = "4d70cdc2acbd8410189925a0acd2930d08ddeaeb9d10711ca3855edfcf08a7ce"
PRIOR_UNION_CAPTURED_GAMES = 273
PRIOR_UNION_RICH = 260
PRIOR_UNION_METADATA = 13
PRIOR_ENRICHED_OFFICIAL_GAMES = 70
OFFICIAL_2004_EXPECTED = 12
UNION_MANIFEST_NAME = "union_manifest.json"
OVERLAY_DOMAINS = DOMAINS
CAPTURE_INDEX_RELATIVE = "features/tamu_official_2004_boxscores/capture_index.json"
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
    "predecessor_union_identity",
    "predecessor_gate_identity",
    "union_identity",
    "validation_contract_version",
    "validator_code_identity",
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
    "recomputed_upstream",
)


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


def compute_code_identity(repo_root: Path) -> str:
    del repo_root
    return PINNED_VALIDATOR_CODE_IDENTITY


def recompute_bat606_payload_identity(payload: Mapping[str, Any]) -> str:
    return compute_identity(payload, "payload_identity")


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
        "opponent_name_only_admission": False,
        "prior_enriched_union_mutated_in_place": False,
        "rejected_game_admitted": False,
        "trusted_declared_upstream_identity_only": False,
        "wmt_payload_mutated_in_place": False,
    }


def expected_scientific_nonclaims() -> dict[str, bool]:
    return {
        "bat_429_advanced": False,
        "bat_523_closed": False,
        "bat603_union_rewritten": False,
        "bat606_payload_rewritten": False,
        "bat607_union_rewritten": False,
        "champion_or_production_promotion": False,
        "completeness_claimed": False,
        "historical_known_at_established": False,
        "historical_population_ready": False,
        "ncaa_contest_ids_invented": False,
        "name_only_promoted": False,
        "new_historical_coverage_claimed": False,
        "pregame_availability_admitted": False,
        "protected_lane_opened": False,
        "rejected_games_admitted": False,
        "wmt_payload_mutated": False,
    }


def expected_admissions() -> dict[str, str]:
    return {
        "bat_401": "DONE_VERIFIED_RETAIN_PROTECTED_LANE_BLOCKED",
        "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
        "bat_429_reevaluation": "POST-SUBTASK-063_066_069_NOT_INDEPENDENTLY_DONE_VERIFIED",
        "bat_523": "IN_PROGRESS",
        "bat_602_union": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_603_union": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_606_domains": "INDEPENDENTLY_RAW_RECONSTRUCTED_EXTERNAL_ROW_PAYLOAD",
        "bat_607_union": "PRESERVED_IMMUTABLE_SUPERSEDED_AS_PREDECESSOR",
        "gap_005": "OPEN",
        "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "ncaa_contest_identity": "NOT_CREATED",
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "source_authority": "SRC-014_OFFICIAL_SCHOOL_EVIDENCE",
        "union_admission": "CANDIDATE_ONLY_NO_NEW_GAMES",
        "wmt_payload": "PRESERVED_IMMUTABLE",
    }


def _bat606_payload_path(data_root: Path, repo_root: Path) -> Path:
    contract = load_json(repo_root / BAT606_CONTRACT_RELATIVE)
    return data_root / contract["payloads"]["enriched_root"] / PINNED_BAT606_PAYLOAD_IDENTITY / "payload.json"


def _serialized_row_counts(game_rows: list[Mapping[str, Any]]) -> dict[str, int]:
    counts = {domain: 0 for domain in OVERLAY_DOMAINS}
    for row in game_rows:
        domain = str(row.get("domain") or row.get("source_domain") or "")
        if domain in counts:
            counts[domain] += 1
    return counts


def _validate_serialized_rows(
    *,
    url: str,
    game: Mapping[str, Any],
    rows: list[Mapping[str, Any]],
    reconstructed_rows: list[Mapping[str, Any]],
) -> dict[str, int]:
    if rows != reconstructed_rows:
        raise AuthorityViolation(f"BAT-606 serialized rows do not match independent raw reconstruction for {url}")
    serialized_counts = _serialized_row_counts(list(rows))
    declared_counts = {domain: len(game.get(domain) or []) for domain in OVERLAY_DOMAINS}
    if serialized_counts != declared_counts:
        raise AuthorityViolation(f"BAT-606 serialized row counts drifted for {url}")
    coverage = {domain: (game.get("domain_coverage") or {}).get(domain) for domain in OVERLAY_DOMAINS}
    for domain in OVERLAY_DOMAINS:
        if coverage.get(domain) == "PRESENT" and serialized_counts[domain] <= 0:
            raise AuthorityViolation(f"PRESENT coverage with zero serialized {domain} rows")
        if serialized_counts[domain] and coverage.get(domain) != "PRESENT":
            raise AuthorityViolation(f"serialized {domain} rows present without PRESENT coverage")
    seen_source_orders: set[int] = set()
    domain_orders: dict[str, list[int]] = {domain: [] for domain in OVERLAY_DOMAINS}
    seen_row_keys: set[tuple[Any, ...]] = set()
    for source_row_order, row in enumerate(rows):
        if source_row_order in seen_source_orders:
            raise AuthorityViolation(f"duplicate source row order for {url}")
        seen_source_orders.add(source_row_order)
        if str(row.get("source_url") or "") != url:
            raise AuthorityViolation(f"BAT-606 row URL drifted for {url}")
        if str(row.get("source_sha256") or "") != str(game.get("source_sha256") or ""):
            raise AuthorityViolation(f"BAT-606 row source SHA drifted for {url}")
        if int(row.get("source_season") or 0) != 2004:
            raise AuthorityViolation(f"BAT-606 row source season drifted for {url}")
        if str(row.get("parser_identity") or "") != PREFORMATTED_PARSER_IDENTITY:
            raise AuthorityViolation(f"BAT-606 parser identity drifted for {url}")
        domain = str(row.get("domain") or row.get("source_domain") or "")
        if domain not in OVERLAY_DOMAINS:
            raise AuthorityViolation(f"invalid BAT-606 domain for {url}")
        if str(row.get("source_domain") or "") != domain:
            raise AuthorityViolation(f"BAT-606 source domain drifted for {url}")
        if row.get("block_index") is None:
            raise AuthorityViolation(f"BAT-606 block/table identity missing for {url}")
        if row.get("availability") != "NOT_ESTABLISHED" or row.get("availability_claim"):
            raise AuthorityViolation("participation or membership promoted to availability")
        if row.get("player_identity") not in {None, "SOURCE_PLAYER_CANDIDATE"}:
            raise AuthorityViolation("name-only player merge is forbidden")
        row_order = row.get("row_order")
        if not isinstance(row_order, int) or row_order < 0:
            raise AuthorityViolation(f"BAT-606 within-domain row order drifted for {url}")
        domain_orders[domain].append(row_order)
        row_key = (url, domain, row_order, row.get("block_index"), row.get("source_sha256"))
        if row_key in seen_row_keys:
            raise AuthorityViolation(f"duplicate BAT-606 row for {url}")
        seen_row_keys.add(row_key)
    if seen_source_orders != set(range(len(rows))):
        raise AuthorityViolation(f"BAT-606 source row-order gap for {url}")
    for domain, orders in domain_orders.items():
        if orders and sorted(orders) != list(range(len(orders))):
            raise AuthorityViolation(f"BAT-606 {domain} row-order gap or reorder for {url}")
    return serialized_counts


def validate_bat606_raw_reconstruction(
    *,
    repo_root: Path,
    data_root: Path,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    reconstructed = reconstruct_bat606_raw(repo_root=repo_root, data_root=data_root)
    raw_payload = reconstructed["payload"]
    raw_identity = str(raw_payload.get("payload_identity") or "")
    if raw_identity != PINNED_BAT606_PAYLOAD_IDENTITY:
        raise AuthorityViolation("independent BAT-606 raw reconstruction identity drifted")
    path = _bat606_payload_path(data_root, repo_root)
    stored = dict(payload) if payload is not None else None
    if stored is None:
        if not path.is_file():
            raise AuthorityViolation("external BAT-606 payload is not mounted")
        stored = load_json(path)
    stored_identity = recompute_bat606_payload_identity(stored)
    if stored_identity != str(stored.get("payload_identity") or ""):
        raise AuthorityViolation("BAT-606 declared payload identity does not match recomputed payload content")
    if stored != raw_payload:
        raise AuthorityViolation("BAT-606 stored payload does not match independent raw reconstruction")
    if stored_identity != raw_identity:
        raise AuthorityViolation("recomputed BAT-606 payload identity does not match independent raw reconstruction")
    committed = load_json(repo_root / BAT606_GATE_RELATIVE)
    if committed.get("gate_identity") != PINNED_BAT606_GATE_IDENTITY:
        raise AuthorityViolation("BAT-606 2004 structured-domain identity rewritten")
    if committed != reconstructed["gate"]:
        raise AuthorityViolation("committed BAT-606 gate does not match independent raw reconstruction")
    if stored.get("availability_claim") or stored.get("availability") not in {None, "NOT_ESTABLISHED"}:
        raise AuthorityViolation("pregame availability claimed")
    external_games = list(stored.get("games") or [])
    row_groups = list(stored.get("rows") or [])
    raw_games = list(raw_payload.get("games") or [])
    raw_rows = list(raw_payload.get("rows") or [])
    if len(external_games) != OFFICIAL_2004_EXPECTED or len(row_groups) != OFFICIAL_2004_EXPECTED:
        raise AuthorityViolation("BAT-606 external payload game/row membership drifted")
    if [game.get("url") for game in external_games] != [game.get("url") for game in raw_games]:
        raise AuthorityViolation("BAT-606 game URL order drifted from independent raw reconstruction")
    validated: dict[str, dict[str, Any]] = {}
    for game, rows, raw_game, reconstructed_rows in zip(external_games, row_groups, raw_games, raw_rows):
        url = str(game.get("url") or "")
        if game != raw_game:
            raise AuthorityViolation(f"BAT-606 game object drifted from independent raw reconstruction for {url}")
        if str(game.get("parser_identity") or "") != PREFORMATTED_PARSER_IDENTITY:
            raise AuthorityViolation(f"BAT-606 parser identity drifted for {url}")
        if int(game.get("source_season") or 0) != 2004:
            raise AuthorityViolation(f"BAT-606 source season drifted for {url}")
        if list(game.get("warnings") or []) != list(raw_game.get("warnings") or []):
            raise AuthorityViolation(f"BAT-606 warnings drifted for {url}")
        if bool(game.get("rich_structured")) != bool(raw_game.get("rich_structured")):
            raise AuthorityViolation(f"BAT-606 rich classification drifted for {url}")
        serialized_counts = _validate_serialized_rows(
            url=url,
            game=game,
            rows=list(rows),
            reconstructed_rows=list(reconstructed_rows),
        )
        validated[url] = {
            "url": url,
            "source_sha256": game.get("source_sha256"),
            "source_season": game.get("source_season"),
            "parser_identity": game.get("parser_identity"),
            "domain_coverage": dict(game.get("domain_coverage") or {}),
            "row_counts": serialized_counts,
            "warnings": list(game.get("warnings") or []),
            "rich_structured": bool(game.get("rich_structured")),
            "rows": list(rows),
        }
    if set(validated) != {str(game.get("url") or "") for game in raw_games}:
        raise AuthorityViolation("BAT-606 external payload URLs do not match independent raw reconstruction")
    return {
        "payload": dict(stored),
        "payload_identity": stored_identity,
        "games": validated,
        "file_sha256": sha256_file(path) if path.is_file() else None,
        "path": str(path),
        "raw": reconstructed,
    }


def union_manifest_path(data_root: Path, union_identity: str = PINNED_UNION_IDENTITY) -> Path:
    return (
        data_root
        / "features/tamu_official_gamebook_union_integrity_complete/sha256"
        / union_identity
        / UNION_MANIFEST_NAME
    )


def require_authoritative_union_manifest(
    *,
    data_root: Path,
    expected_payload: Mapping[str, Any],
    union_identity: str,
) -> str:
    path = union_manifest_path(data_root, union_identity)
    identity_dir = path.parent
    if not path.is_file():
        raise AuthorityViolation("authoritative external union manifest is missing")
    extras = sorted(item.name for item in identity_dir.iterdir() if item.name != UNION_MANIFEST_NAME)
    if extras:
        raise AuthorityViolation("extra union manifests present: " + ", ".join(extras))
    try:
        stored = load_json(path)
    except json.JSONDecodeError as exc:
        raise AuthorityViolation("authoritative external union manifest is truncated or malformed") from exc
    if stored != expected_payload:
        raise AuthorityViolation("external integrity-complete union payload does not match reconstruction")
    serialized = json.dumps(expected_payload, indent=2, sort_keys=True) + "\n"
    if path.read_text(encoding="utf-8-sig") != serialized:
        raise AuthorityViolation("external integrity-complete union payload serialization does not match reconstruction")
    return sha256_file(path)


def reconstruct_objects(
    *,
    repo_root: Path,
    data_root: Path,
    bat606_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    registry = repo_root / "governance/PROTECTED_SPLIT_REGISTRY.csv"
    digest = hashlib.sha256(registry.read_bytes()).hexdigest()
    if digest != REGISTRY_SHA256:
        raise AuthorityViolation("protected-split registry identity drift")
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise AuthorityViolation("integrity-complete union contract identity drift")
    predecessor = load_json(repo_root / "artifacts/data_lake/tamu_official_gamebook_union_2004_expanded_gate.json")
    if predecessor.get("union_identity") != PINNED_BAT607_UNION_IDENTITY:
        raise AuthorityViolation("BAT-607 2004-expanded union identity was rewritten")
    if predecessor.get("gate_identity") != PINNED_BAT607_GATE_IDENTITY:
        raise AuthorityViolation("BAT-607 2004-expanded union gate identity was rewritten")
    if predecessor.get("predecessor_union_identity") != PINNED_BAT603_UNION_IDENTITY:
        raise AuthorityViolation("BAT-603 integrity-bound union identity was rewritten")
    if predecessor.get("predecessor_gate_identity") != PINNED_BAT603_GATE_IDENTITY:
        raise AuthorityViolation("BAT-603 integrity-bound union gate identity was rewritten")
    if int(predecessor.get("counts", {}).get("union_captured_games") or 0) != PRIOR_UNION_CAPTURED_GAMES:
        raise AuthorityViolation("BAT-607 captured-game count drifted")
    if len(predecessor.get("enriched_official_games") or []) != PRIOR_ENRICHED_OFFICIAL_GAMES:
        raise AuthorityViolation("BAT-607 official-school membership drifted")
    validate_bat603(repo_root=repo_root, data_root=data_root, require_rebuild=True)
    validate_bat607(repo_root=repo_root, data_root=data_root, require_rebuild=True)
    bat603_manifest_sha = require_bat603_union_manifest(
        data_root=data_root,
        expected_payload=load_json(bat603_union_manifest_path(data_root)),
        union_identity=PINNED_BAT603_UNION_IDENTITY,
    )
    bat607_manifest_sha = require_bat607_union_manifest(
        data_root=data_root,
        expected_payload=load_json(bat607_union_manifest_path(data_root)),
        union_identity=PINNED_BAT607_UNION_IDENTITY,
    )
    if bat603_manifest_sha != PINNED_BAT603_UNION_MANIFEST_FILE_SHA256:
        raise AuthorityViolation("BAT-603 union manifest file SHA-256 drifted")
    if bat607_manifest_sha != PINNED_BAT607_UNION_MANIFEST_FILE_SHA256:
        raise AuthorityViolation("BAT-607 union manifest file SHA-256 drifted")
    bat606 = validate_bat606_raw_reconstruction(
        repo_root=repo_root,
        data_root=data_root,
        payload=bat606_payload,
    )
    official_games = [json.loads(json.dumps(item)) for item in (predecessor.get("enriched_official_games") or [])]
    rejected = [json.loads(json.dumps(item)) for item in (predecessor.get("preserved_rejections") or [])]
    admitted_2004 = [json.loads(json.dumps(item)) for item in (predecessor.get("admitted_official_2004_games") or [])]
    conflicts = [json.loads(json.dumps(item)) for item in (predecessor.get("conflicts") or [])]
    rejected_urls = {str(item.get("url") or "") for item in rejected}
    if rejected_urls != PRESERVED_REJECTION_URLS:
        raise AuthorityViolation("the four preserved rejected games drifted")
    admitted_urls = {str(item.get("url") or "") for item in official_games}
    if rejected_urls & admitted_urls:
        raise AuthorityViolation("rejected games were admitted")
    if len(official_games) != PRIOR_ENRICHED_OFFICIAL_GAMES:
        raise AuthorityViolation("integrity-complete successor changed BAT-607 official-school membership")
    if len(admitted_2004) != OFFICIAL_2004_EXPECTED:
        raise AuthorityViolation("integrity-complete successor changed BAT-607 official 2004 membership")
    raw_by_url = bat606["games"]
    for item in admitted_2004:
        url = str(item.get("url") or "")
        raw_game = raw_by_url.get(url)
        if raw_game is None:
            raise AuthorityViolation(f"independent BAT-606 reconstruction omitted admitted 2004 URL {url}")
        if str(item.get("structured_row_payload_identity") or "") != bat606["payload_identity"]:
            raise AuthorityViolation("2004 overlay is not bound to the independently raw-reconstructed BAT-606 payload identity")
        if dict(item.get("structured_row_counts") or {}) != raw_game["row_counts"]:
            raise AuthorityViolation(f"2004 overlay row counts drifted from independent raw reconstruction for {url}")
        if str(item.get("source_sha256") or "") != str(raw_game.get("source_sha256") or ""):
            raise AuthorityViolation(f"2004 overlay source SHA drifted from independent raw reconstruction for {url}")
        if item.get("availability") != "NOT_ESTABLISHED" or item.get("availability_claim"):
            raise AuthorityViolation("pregame availability claimed")
        if item.get("ncaa_contest_id"):
            raise AuthorityViolation("NCAA contest IDs fabricated")
    predecessor_counts = dict(predecessor.get("counts") or {})
    scoring = sum(1 for item in official_games if scoring_summary_present(item))
    counts = {
        **predecessor_counts,
        "predecessor_273_union_games_preserved": PRIOR_UNION_CAPTURED_GAMES,
        "official_2004_preserved": OFFICIAL_2004_EXPECTED,
        "official_2004_revalidated": len(admitted_2004),
        "official_2004_added": 0,
        "new_games_added": 0,
        "union_target_games": PRIOR_UNION_CAPTURED_GAMES,
        "union_captured_games": PRIOR_UNION_CAPTURED_GAMES,
        "rich_structured_games": PRIOR_UNION_RICH,
        "metadata_only_games": PRIOR_UNION_METADATA,
        "scoring_summary_present_games": scoring,
        "ncaa_contest_ids_created": 0,
        "unmatched_rejected": 4,
    }
    if counts["union_captured_games"] != counts["rich_structured_games"] + counts["metadata_only_games"]:
        raise AuthorityViolation("integrity-complete rich/metadata arithmetic drifted")
    if scoring != int(predecessor_counts.get("scoring_summary_present_games") or 0):
        raise AuthorityViolation("integrity-complete scoring-summary count drifted")
    code_identity = compute_code_identity(repo_root)
    recomputed_upstream = {
        "bat603_union_identity": PINNED_BAT603_UNION_IDENTITY,
        "bat603_gate_identity": PINNED_BAT603_GATE_IDENTITY,
        "bat603_union_manifest_file_sha256": bat603_manifest_sha,
        "bat606_payload_identity": bat606["payload_identity"],
        "bat606_payload_file_sha256": bat606["file_sha256"],
        "bat607_union_identity": PINNED_BAT607_UNION_IDENTITY,
        "bat607_gate_identity": PINNED_BAT607_GATE_IDENTITY,
        "bat607_union_manifest_file_sha256": bat607_manifest_sha,
        "validator_code_identity": code_identity,
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "predecessor_union_identity": PINNED_BAT607_UNION_IDENTITY,
        "predecessor_gate_identity": PINNED_BAT607_GATE_IDENTITY,
        "bat606_payload_identity": bat606["payload_identity"],
        "enriched_official_games": official_games,
        "admitted_official_2004_games": admitted_2004,
        "preserved_rejections": rejected,
        "counts": counts,
        "conflicts": conflicts,
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "recomputed_upstream": recomputed_upstream,
    }
    payload["union_identity"] = stable_hash(
        {
            "predecessor_union_identity": PINNED_BAT607_UNION_IDENTITY,
            "predecessor_gate_identity": PINNED_BAT607_GATE_IDENTITY,
            "recomputed_bat606_payload_identity": bat606["payload_identity"],
            "bat603_union_manifest_file_sha256": bat603_manifest_sha,
            "bat607_union_manifest_file_sha256": bat607_manifest_sha,
            "upstream_payload_file_hashes": {
                "bat606": bat606["file_sha256"],
            },
            "validator_code_identity": code_identity,
            "validation_contract_version": VALIDATION_CONTRACT_VERSION,
            "preserved_rejections": rejected,
            "counts": counts,
        }
    )
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_GAMEBOOK_UNION_INTEGRITY_COMPLETE_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "disposition": "NEW_IMMUTABLE_IDENTITY_BAT607_PRESERVED_INDEPENDENT_BAT606_RAW_BINDINGS",
        "source_id": SOURCE_ID,
        "predecessor_union_identity": PINNED_BAT607_UNION_IDENTITY,
        "predecessor_gate_identity": PINNED_BAT607_GATE_IDENTITY,
        "union_identity": payload["union_identity"],
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
        "validator_code_identity": code_identity,
        "selected_seasons": [2009, 2008, 2007, 2006, 2005, 2004],
        "counts": counts,
        "coverage_by_season": coverage_by_season(official_games),
        "coverage_by_domain": coverage_by_domain(official_games),
        "enriched_official_games": official_games,
        "admitted_official_2004_games": admitted_2004,
        "preserved_rejections": rejected,
        "conflicts": conflicts,
        "admissions": expected_admissions(),
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "protected_lane": PROTECTED_LANE,
        "recomputed_upstream": recomputed_upstream,
        "upstream_identities": {
            "bat591_gate_identity": PINNED_BAT591_GATE_IDENTITY,
            "bat591_payload_identity": PINNED_BAT591_PAYLOAD_IDENTITY,
            "bat596_gate_identity": PINNED_BAT596_GATE_IDENTITY,
            "bat596_payload_identity": PINNED_BAT596_PAYLOAD_IDENTITY,
            "bat602_gate_identity": PINNED_BAT602_GATE_IDENTITY,
            "bat602_union_identity": PINNED_BAT602_UNION_IDENTITY,
            "bat603_gate_identity": PINNED_BAT603_GATE_IDENTITY,
            "bat603_union_identity": PINNED_BAT603_UNION_IDENTITY,
            "bat603_union_manifest_file_sha256": PINNED_BAT603_UNION_MANIFEST_FILE_SHA256,
            "bat604_gate_identity": PINNED_BAT604_GATE_IDENTITY,
            "bat605_acquisition_identity": PINNED_BAT605_ACQUISITION_IDENTITY,
            "bat605_dataset_identity": PINNED_BAT605_DATASET_IDENTITY,
            "bat605_games_identity": PINNED_BAT605_GAMES_IDENTITY,
            "bat605_gate_identity": PINNED_BAT605_GATE_IDENTITY,
            "bat606_gate_identity": PINNED_BAT606_GATE_IDENTITY,
            "bat606_payload_identity": PINNED_BAT606_PAYLOAD_IDENTITY,
            "bat607_gate_identity": PINNED_BAT607_GATE_IDENTITY,
            "bat607_union_identity": PINNED_BAT607_UNION_IDENTITY,
            "bat607_union_manifest_file_sha256": PINNED_BAT607_UNION_MANIFEST_FILE_SHA256,
            "protected_split_registry_sha256": REGISTRY_SHA256,
        },
    }
    if counts["ncaa_contest_ids_created"] or any(item.get("ncaa_contest_id") for item in official_games):
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
        "predecessor": predecessor,
        "bat606": bat606,
    }


def materialize_union(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    payload = objects["payload"]
    root = data_root / objects["contract"]["payloads"]["union_root"] / payload["union_identity"]
    write_json(root / UNION_MANIFEST_NAME, payload)
    write_json(repo_root / GATE_RELATIVE, objects["gate"])
    return {
        "gate_identity": objects["gate"]["gate_identity"],
        "union_identity": payload["union_identity"],
        "counts": objects["gate"]["counts"],
        "recomputed_upstream": objects["gate"]["recomputed_upstream"],
    }


def upstream_is_ready(data_root: Path) -> bool:
    return (
        bat607_upstream_is_ready(data_root)
        and (data_root / CAPTURE_INDEX_RELATIVE).is_file()
        and bat603_union_manifest_path(data_root).is_file()
        and bat607_union_manifest_path(data_root).is_file()
    )


def lake_is_ready(data_root: Path) -> bool:
    return (
        upstream_is_ready(data_root)
        and bat603_union_manifest_path(data_root).is_file()
        and bat607_union_manifest_path(data_root).is_file()
        and union_manifest_path(data_root).is_file()
    )


def validate_compact_gate(committed: Mapping[str, Any]) -> None:
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("predecessor_union_identity") != PINNED_BAT607_UNION_IDENTITY:
        raise AuthorityViolation("BAT-607 2004-expanded union identity was rewritten")
    if committed.get("predecessor_gate_identity") != PINNED_BAT607_GATE_IDENTITY:
        raise AuthorityViolation("BAT-607 2004-expanded union gate identity was rewritten")
    if committed.get("result") != PASS_RESULT:
        raise AuthorityViolation("completion forged")
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("classification forged")
    if committed.get("authority", {}).get("historical_known_at_from_capture_time"):
        raise AuthorityViolation("retrieval time promoted to historical known-at")
    if committed.get("authority", {}).get("opponent_name_only_admission"):
        raise AuthorityViolation("opponent name alone is not admission")
    if committed.get("counts", {}).get("ncaa_contest_ids_created"):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if int((committed.get("counts") or {}).get("new_games_added", -1)) != 0:
        raise AuthorityViolation("integrity-complete successor invented or dropped a union admission")
    if committed.get("admissions", {}).get("pregame_availability") != "BLOCKED":
        raise AuthorityViolation("pregame availability admitted")
    if committed.get("admissions", {}).get("bat_429") != "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES":
        raise AuthorityViolation("BAT-429 advanced without independently DONE/VERIFIED hard dependencies")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not recompute")
    if int(committed.get("counts", {}).get("union_captured_games") or 0) != PRIOR_UNION_CAPTURED_GAMES:
        raise AuthorityViolation("union captured-game arithmetic drifted")
    rejected_urls = {str(item.get("url") or "") for item in committed.get("preserved_rejections") or []}
    admitted_urls = {str(item.get("url") or "") for item in committed.get("enriched_official_games") or []}
    if rejected_urls != PRESERVED_REJECTION_URLS:
        raise AuthorityViolation("the four preserved rejected games drifted")
    if rejected_urls & admitted_urls:
        raise AuthorityViolation("rejected games were admitted")
    if any(item.get("availability_claim") for item in committed.get("enriched_official_games") or []):
        raise AuthorityViolation("pregame availability claimed")
    if any(item.get("ncaa_contest_id") for item in committed.get("enriched_official_games") or []):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    upstream = committed.get("upstream_identities") or {}
    if upstream.get("bat603_union_identity") != PINNED_BAT603_UNION_IDENTITY:
        raise AuthorityViolation("BAT-603 integrity-bound union identity was rewritten")
    if upstream.get("bat607_union_identity") != PINNED_BAT607_UNION_IDENTITY:
        raise AuthorityViolation("BAT-607 2004-expanded union identity was rewritten")
    if upstream.get("bat603_union_manifest_file_sha256") != PINNED_BAT603_UNION_MANIFEST_FILE_SHA256:
        raise AuthorityViolation("BAT-603 union manifest file SHA-256 drifted")
    if upstream.get("bat607_union_manifest_file_sha256") != PINNED_BAT607_UNION_MANIFEST_FILE_SHA256:
        raise AuthorityViolation("BAT-607 union manifest file SHA-256 drifted")


def validate_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    gate: Mapping[str, Any] | None = None,
    require_rebuild: bool = True,
    bat606_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    validate_compact_gate(committed)
    ready = upstream_is_ready(data_root)
    if require_rebuild and not ready:
        raise AuthorityViolation("external integrity-complete reconstruction was required but the data root is not mounted")
    if not ready and bat606_payload is None:
        return {
            "result": "PASS",
            "gate_identity": committed["gate_identity"],
            "union_identity": committed["union_identity"],
            "external_reconstruction": "NOT_MOUNTED",
        }
    expected = reconstruct_objects(
        repo_root=repo_root,
        data_root=data_root,
        bat606_payload=bat606_payload,
    )
    if committed != expected["gate"]:
        raise AuthorityViolation("committed integrity-complete union gate does not match independent reconstruction")
    require_authoritative_union_manifest(
        data_root=data_root,
        expected_payload=expected["payload"],
        union_identity=str(expected["payload"]["union_identity"]),
    )
    return {
        "result": "PASS",
        "gate_identity": expected["gate"]["gate_identity"],
        "union_identity": expected["gate"]["union_identity"],
        "counts": expected["gate"]["counts"],
        "recomputed_upstream": expected["gate"]["recomputed_upstream"],
        "external_reconstruction": "MOUNTED",
    }


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))

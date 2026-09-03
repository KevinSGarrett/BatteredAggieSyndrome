"""Immutable 1998-expanded official union from BAT-633 predecessor."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import sha256_file, stable_hash
from aggie_analytics.data.tamu_official_1998_boxscores import (
    reconstruct_objects as reconstruct_bat635,
    validate_artifact as validate_bat635,
)
from aggie_analytics.data.tamu_official_1998_season_index import (
    reconstruct as reconstruct_bat634,
    validate_artifact as validate_bat634,
)
from aggie_analytics.data.tamu_official_1998_structured_domains import (
    STRUCTURED_DOMAINS as OVERLAY_DOMAINS,
    validate_artifact as validate_bat636,
)
from aggie_analytics.data.tamu_official_gamebook_union import REGISTRY_SHA256
from aggie_analytics.data.tamu_official_gamebook_union_1999_expanded import (
    GATE_RELATIVE as BAT633_GATE_RELATIVE,
)
from aggie_analytics.data.tamu_official_gamebook_union_2005_expanded import (
    ADMITTED_STATUSES,
    COMPACT_FIELDS,
)
from aggie_analytics.data.tamu_official_gamebook_union_2005_integrity_bound import (
    coverage_by_domain,
    coverage_by_season,
)
from aggie_analytics.data.tamu_official_historical_boxscores import AuthorityViolation
from aggie_analytics.data.tamu_official_rich_structure import (
    is_rich_structured,
    scoring_summary_present,
)
from aggie_analytics.validation.artifact_binding import compute_identity

SCHEMA_VERSION = "aggie.data.tamu_official_gamebook_union_1998_expanded.v1"
VALIDATION_CONTRACT_VERSION = "aggie.data.tamu_official_gamebook_union_1998_expanded.v1"
CONTRACT_RELATIVE = "configs/tamu_official_gamebook_union_1998_expanded_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_gamebook_union_1998_expanded_gate.json"
MODULE_RELATIVE = "src/aggie_analytics/data/tamu_official_gamebook_union_1998_expanded.py"
CODE_BUNDLE_RELATIVE = (MODULE_RELATIVE,)
CONTRACT_ID = "BAT-637-TAMU-OFFICIAL-GAMEBOOK-UNION-1998-EXPANDED-V1"
DECISION_UNIT = "POST-TASK-SRC014-1998-EXPANDED-ENRICHED-UNION-001"
JIRA_KEY = "BAT-637"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_OFFICIAL_GAMEBOOK_UNION_1998_EXPANDED_CANDIDATE_ONLY"
PASS_RESULT = "PASS_IMMUTABLE_BAT633_PRESERVED_OFFICIAL_1998_ADDED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
OFFICIAL_1998_INDEX_URL = "https://files.12thman.com/history/football/years/1998.html"
OFFICIAL_1998_EXPECTED = 14
OFFICIAL_1998_ADMITTED_EXPECTED = 6
OFFICIAL_1998_REJECTED_EXPECTED = 8
PRIOR_UNION_CAPTURED_GAMES = 324
PRIOR_UNION_RICH = 311
PRIOR_UNION_METADATA = 13
PRIOR_ENRICHED_OFFICIAL_GAMES = 121
UNION_MANIFEST_NAME = "union_manifest.json"
PINNED_BAT633_UNION_IDENTITY = "c213761531a3b8f8605e2cd3a00afdb7993c9cbedeb1c383cf1429167f0fc53c"
PINNED_BAT633_GATE_IDENTITY = "a8d0a6594cfdf4557e2ef743983d64531474410fde6795fe4400441d11555403"
PINNED_BAT634_GATE_IDENTITY = "f621b849f5692dd6697bd6396086d858966b8d807a6f4ef63d7b0b72d7232306"
PINNED_BAT635_GATE_IDENTITY = "ecc112db8ee339ec80651b7afc021ee5df80751cafdf43ce92d493312cacd260"
PINNED_BAT635_DATASET_IDENTITY = "94d5fe1182a65c35b59f9b2a10d8de1ee561f92a4d6e6e06a53b0a2eded49c15"
PINNED_BAT635_ACQUISITION_IDENTITY = "6dc742a6d359d3800f1474e436734ab523ea17d389e81bca9e9f8c01200f18f7"
PINNED_BAT636_GATE_IDENTITY = "7f9e19fe686a440fba8a2fa44f0448064c7e18c7fe30767a86492416384a706f"
PINNED_BAT636_PAYLOAD_IDENTITY = "a588cd9d5ea94eaec80cd7f6605b3c0a2672fbf45b01216509c5bf5cb0dcb7b5"
NAME_ONLY_STATUSES = frozenset({"MATCHED_OPPONENT_NAME_ONLY", "NAME_ONLY", "OPPONENT_NAME_ONLY"})
REQUIRED_GATE_FIELDS = (
    "schema_version", "artifact_type", "result", "classification", "contract_id",
    "decision_unit", "jira_key", "disposition", "source_id", "predecessor_union_identity",
    "predecessor_gate_identity", "union_identity", "validation_contract_version",
    "validator_code_identity", "selected_seasons", "counts", "coverage_by_season",
    "coverage_by_domain", "enriched_official_games", "preserved_rejections", "conflicts",
    "admissions", "authority", "scientific_nonclaims", "protected_lane",
    "upstream_identities", "recomputed_upstream",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    missing = [key for key in REQUIRED_GATE_FIELDS if key not in gate]
    if missing:
        raise AuthorityViolation("gate is missing required identity fields: " + ", ".join(missing))
    return compute_identity(gate, "gate_identity")


def compute_code_identity(repo_root: Path) -> str:
    hasher = hashlib.sha256()
    hasher.update(b"aggie.union.code_bundle.v1\n")
    for relative in CODE_BUNDLE_RELATIVE:
        path = repo_root / relative
        if not path.is_file():
            raise AuthorityViolation(f"code bundle member missing: {relative}")
        hasher.update(b"PATH:")
        hasher.update(relative.replace("\\", "/").encode("utf-8"))
        hasher.update(b"\n")
        hasher.update(path.read_bytes())
        hasher.update(b"\n")
    return hasher.hexdigest()


def _index_by_url(games: list[Mapping[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for game in games:
        url = str(game.get("url") or "")
        if not url:
            raise AuthorityViolation(f"{label} game missing URL")
        if url in indexed:
            raise AuthorityViolation(f"duplicate {label} URL {url}")
        indexed[url] = dict(game)
    return indexed


def _serialized_row_counts(rows: list[Mapping[str, Any]]) -> dict[str, int]:
    counts = {domain: 0 for domain in OVERLAY_DOMAINS}
    for row in rows:
        domain = str(row.get("domain") or row.get("source_domain") or "")
        if domain in counts:
            counts[domain] += 1
    return counts


def expected_authority() -> dict[str, bool]:
    return {
        "availability_claim": False,
        "champion_or_production_promotion": False,
        "completeness_claim": False,
        "contest_id_fabrication": False,
        "historical_known_at_from_capture_time": False,
        "name_only_promotion": False,
        "ncaa_contest_identity": False,
        "opponent_name_only_admission": False,
        "rejected_game_admitted": False,
    }


def expected_scientific_nonclaims() -> dict[str, bool]:
    return {
        "bat_429_advanced": False,
        "bat_523_closed": False,
        "champion_or_production_promotion": False,
        "completeness_claimed": False,
        "historical_known_at_established": False,
        "historical_population_ready": False,
        "name_only_promoted": False,
        "ncaa_contest_ids_invented": False,
        "pregame_availability_admitted": False,
        "protected_lane_opened": False,
        "rejected_games_admitted": False,
    }


def expected_admissions() -> dict[str, str]:
    return {
        "bat_401": "DONE_VERIFIED_RETAIN_PROTECTED_LANE_BLOCKED",
        "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
        "bat_523": "IN_PROGRESS",
        "bat_633_union": "CONSUMED_IMMUTABLE_PREDECESSOR_ONLY",
        "bat_634_index": "CONSUMED_OFFICIAL_INDEX_URLS_ONLY",
        "bat_635_boxscores": "INDEPENDENTLY_RECONSTRUCTED_EXTERNAL_PAYLOAD",
        "bat_636_structured_domains": "INDEPENDENTLY_RECONSTRUCTED_EXTERNAL_ROWS",
        "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "ncaa_contest_identity": "NOT_CREATED",
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "source_authority": "SRC-014_OFFICIAL_SCHOOL_EVIDENCE",
        "union_admission": "CANDIDATE_ONLY",
    }


def compact_1998_game(game: Mapping[str, Any], official_index_url: str) -> dict[str, Any]:
    row = {key: game.get(key) for key in COMPACT_FIELDS}
    row["source_season"] = int(game.get("source_season") or game.get("football_season") or 0)
    row["football_season"] = int(game.get("football_season") or game.get("source_season") or 0)
    row["official_index_url"] = str(game.get("parent_url") or "")
    row["parent_url"] = str(game.get("parent_url") or "")
    row["availability_claim"] = False
    row["availability"] = "NOT_ESTABLISHED"
    row["historical_publication_time"] = None
    row["canonical_game_id"] = None
    row["ncaa_contest_id"] = None
    if row["official_index_url"] != official_index_url:
        raise AuthorityViolation("parent_url does not match official 1998 index URL")
    if row["source_season"] != 1998 or row["football_season"] != 1998:
        raise AuthorityViolation("1998 candidate season drifted")
    return row


def overlay_1998(game: Mapping[str, Any], domains: Mapping[str, Any], payload_identity: str, *, serialized_row_counts: Mapping[str, int]) -> dict[str, Any]:
    row = json.loads(json.dumps(game))
    coverage = dict(row.get("domain_coverage") or {})
    for domain in OVERLAY_DOMAINS:
        present = (domains.get("domain_coverage") or {}).get(domain) == "PRESENT"
        if present and int(serialized_row_counts.get(domain) or 0) <= 0:
            raise AuthorityViolation(f"PRESENT coverage without serialized {domain} rows")
        if present:
            coverage[domain] = "PRESENT"
        elif domain not in coverage:
            coverage[domain] = "ABSENT"
    row["domain_coverage"] = coverage
    row["overlay_applied"] = True
    row["overlay_source"] = "BAT-636-1998-STRUCTURED-DOMAINS-INDEPENDENTLY-VALIDATED"
    row["structured_row_payload_identity"] = payload_identity
    row["structured_row_counts"] = dict(serialized_row_counts)
    row["rich_structured"] = is_rich_structured(row)
    return row


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    if hashlib.sha256((repo_root / "governance/PROTECTED_SPLIT_REGISTRY.csv").read_bytes()).hexdigest() != REGISTRY_SHA256:
        raise AuthorityViolation("protected-split registry identity drift")
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    predecessor = load_json(repo_root / BAT633_GATE_RELATIVE)
    if predecessor.get("union_identity") != PINNED_BAT633_UNION_IDENTITY:
        raise AuthorityViolation("BAT-633 predecessor union identity rewritten")
    if predecessor.get("gate_identity") != PINNED_BAT633_GATE_IDENTITY:
        raise AuthorityViolation("BAT-633 predecessor gate identity rewritten")
    validate_bat634(repo_root=repo_root, data_root=data_root, require_rebuild=True)
    validate_bat635(repo_root=repo_root, data_root=data_root, require_rebuild=True)
    validate_bat636(repo_root=repo_root, data_root=data_root, require_rebuild=True)
    bat634 = reconstruct_bat634(repo_root=repo_root, data_root=data_root)
    if bat634["gate"]["gate_identity"] != PINNED_BAT634_GATE_IDENTITY:
        raise AuthorityViolation("BAT-634 identity rewritten")
    allowlist = [str(url) for url in (bat634["gate"].get("box_score_urls") or [])]
    bat635 = reconstruct_bat635(repo_root=repo_root, data_root=data_root)
    if bat635["gate"]["gate_identity"] != PINNED_BAT635_GATE_IDENTITY:
        raise AuthorityViolation("BAT-635 identity rewritten")
    if bat635["payload"]["dataset_identity"] != PINNED_BAT635_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-635 dataset identity rewritten")
    if bat635["payload"]["acquisition_identity"] != PINNED_BAT635_ACQUISITION_IDENTITY:
        raise AuthorityViolation("BAT-635 acquisition identity rewritten")
    bat636_payload_path = (
        data_root
        / "features/tamu_official_1998_structured_domains/sha256"
        / PINNED_BAT636_PAYLOAD_IDENTITY
        / "payload.json"
    )
    if not bat636_payload_path.is_file():
        raise AuthorityViolation("external BAT-636 payload missing")
    bat636_payload = load_json(bat636_payload_path)
    if bat636_payload.get("payload_identity") != PINNED_BAT636_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-636 payload identity rewritten")
    game_rows = list(bat635["payload"].get("games") or [])
    compact_candidates = [compact_1998_game(item, OFFICIAL_1998_INDEX_URL) for item in game_rows]
    domains_by_url: dict[str, dict[str, Any]] = {}
    for game, rows in zip(bat636_payload.get("games") or [], bat636_payload.get("rows") or []):
        url = str(game.get("url") or "")
        domains_by_url[url] = {
            "domain_coverage": dict(game.get("domain_coverage") or {}),
            "row_counts": _serialized_row_counts(list(rows)),
            "source_sha256": str(game.get("source_sha256") or ""),
        }
    compact_by_url = _index_by_url(compact_candidates, "BAT-635")
    admitted_1998: list[dict[str, Any]] = []
    rejected_1998: list[dict[str, Any]] = []
    for compact in compact_candidates:
        url = str(compact.get("url") or "")
        status = str(compact.get("canonical_game_match_status") or "")
        if status in NAME_ONLY_STATUSES:
            raise AuthorityViolation("opponent name alone is forbidden")
        if status not in ADMITTED_STATUSES:
            rejected_1998.append(dict(compact))
            continue
        domains = domains_by_url.get(url)
        if domains is None:
            raise AuthorityViolation(f"BAT-636 domains missing for {url}")
        admitted_1998.append(
            overlay_1998(
                compact,
                domains,
                PINNED_BAT636_PAYLOAD_IDENTITY,
                serialized_row_counts=domains["row_counts"],
            )
        )
    missing_from_635 = sorted(set(allowlist) - set(compact_by_url))
    for url in missing_from_635:
        rejected_1998.append(
            {
                "url": url,
                "canonical_game_match_status": "UNMATCHED_STRONG_TUPLE",
                "conflict_status": "PARSE_REJECTED_OR_PARTIAL",
                "official_index_url": OFFICIAL_1998_INDEX_URL,
                "source_season": 1998,
                "football_season": 1998,
                "availability": "NOT_ESTABLISHED",
                "availability_claim": False,
                "ncaa_contest_id": None,
            }
        )
    if len(allowlist) != OFFICIAL_1998_EXPECTED:
        raise AuthorityViolation("official 1998 allowlist count drifted")
    if len(admitted_1998) != OFFICIAL_1998_ADMITTED_EXPECTED:
        raise AuthorityViolation("official 1998 admission count drifted")
    if len(rejected_1998) != OFFICIAL_1998_REJECTED_EXPECTED:
        raise AuthorityViolation("official 1998 rejected count drifted")
    prior_games = [json.loads(json.dumps(item)) for item in (predecessor.get("enriched_official_games") or [])]
    official_games = prior_games + admitted_1998
    if len(official_games) != PRIOR_ENRICHED_OFFICIAL_GAMES + OFFICIAL_1998_ADMITTED_EXPECTED:
        raise AuthorityViolation("expanded official-school membership count drifted")
    rich_added = sum(1 for item in admitted_1998 if item.get("rich_structured"))
    counts = {
        **dict(predecessor.get("counts") or {}),
        "predecessor_union_games_preserved": PRIOR_UNION_CAPTURED_GAMES,
        "official_1998_target_games": OFFICIAL_1998_EXPECTED,
        "official_1998_admitted": len(admitted_1998),
        "official_1998_rejected": len(rejected_1998),
        "new_games_added": len(admitted_1998),
        "union_captured_games": PRIOR_UNION_CAPTURED_GAMES + len(admitted_1998),
        "union_target_games": PRIOR_UNION_CAPTURED_GAMES + len(admitted_1998),
        "rich_structured_games": PRIOR_UNION_RICH + rich_added,
        "metadata_only_games": PRIOR_UNION_METADATA + len(admitted_1998) - rich_added,
        "scoring_summary_present_games": sum(1 for item in official_games if scoring_summary_present(item)),
        "matched_strong_tuple": int((predecessor.get("counts") or {}).get("matched_strong_tuple") or 0)
        + sum(1 for item in admitted_1998 if item.get("canonical_game_match_status") == "MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE"),
        "date_conflicts": int((predecessor.get("counts") or {}).get("date_conflicts") or 0)
        + sum(1 for item in admitted_1998 if item.get("canonical_game_match_status") == "OFFICIAL_INDEX_DATE_CONFLICT"),
        "unmatched_rejected": int((predecessor.get("counts") or {}).get("unmatched_rejected") or 0) + len(rejected_1998),
        "ncaa_contest_ids_created": 0,
        "name_only_player_merges": 0,
        "games_admitted_to_union": 0,
    }
    conflicts = [json.loads(json.dumps(item)) for item in (predecessor.get("conflicts") or [])]
    conflicts.extend(
        {
            "url": item.get("url"),
            "match_status": item.get("canonical_game_match_status"),
            "conflict_status": item.get("conflict_status"),
        }
        for item in rejected_1998
    )
    code_identity = compute_code_identity(repo_root)
    recomputed_upstream = {
        "bat633_gate_identity": PINNED_BAT633_GATE_IDENTITY,
        "bat633_union_identity": PINNED_BAT633_UNION_IDENTITY,
        "bat634_gate_identity": PINNED_BAT634_GATE_IDENTITY,
        "bat635_gate_identity": PINNED_BAT635_GATE_IDENTITY,
        "bat635_dataset_identity": PINNED_BAT635_DATASET_IDENTITY,
        "bat635_acquisition_identity": PINNED_BAT635_ACQUISITION_IDENTITY,
        "bat635_payload_file_sha256": sha256_file(
            data_root / "features/tamu_official_1998_boxscores/sha256" / PINNED_BAT635_DATASET_IDENTITY / "payload.json"
        ),
        "bat636_gate_identity": PINNED_BAT636_GATE_IDENTITY,
        "bat636_payload_identity": PINNED_BAT636_PAYLOAD_IDENTITY,
        "bat636_payload_file_sha256": sha256_file(bat636_payload_path),
        "validator_code_identity": code_identity,
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "predecessor_union_identity": PINNED_BAT633_UNION_IDENTITY,
        "predecessor_gate_identity": PINNED_BAT633_GATE_IDENTITY,
        "enriched_official_games": official_games,
        "admitted_official_1998_games": admitted_1998,
        "rejected_official_1998_games": rejected_1998,
        "preserved_rejections": [json.loads(json.dumps(item)) for item in (predecessor.get("preserved_rejections") or [])],
        "counts": counts,
        "conflicts": conflicts,
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "recomputed_upstream": recomputed_upstream,
    }
    payload["union_identity"] = stable_hash(
        {
            "predecessor_union_identity": PINNED_BAT633_UNION_IDENTITY,
            "predecessor_gate_identity": PINNED_BAT633_GATE_IDENTITY,
            "admitted_official_1998_games": admitted_1998,
            "rejected_official_1998_games": rejected_1998,
            "counts": counts,
            "recomputed_upstream": recomputed_upstream,
        }
    )
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_GAMEBOOK_UNION_1998_EXPANDED_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "disposition": "NEW_IMMUTABLE_IDENTITY_BAT633_PRESERVED_OFFICIAL_1998_ADDED",
        "source_id": SOURCE_ID,
        "predecessor_union_identity": PINNED_BAT633_UNION_IDENTITY,
        "predecessor_gate_identity": PINNED_BAT633_GATE_IDENTITY,
        "union_identity": payload["union_identity"],
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
        "validator_code_identity": code_identity,
        "selected_seasons": [2009, 2008, 2007, 2006, 2005, 2004, 2003, 2002, 2001, 2000, 1999, 1998],
        "counts": counts,
        "coverage_by_season": coverage_by_season(official_games),
        "coverage_by_domain": coverage_by_domain(official_games),
        "enriched_official_games": official_games,
        "admitted_official_1998_games": admitted_1998,
        "rejected_official_1998_games": rejected_1998,
        "preserved_rejections": payload["preserved_rejections"],
        "conflicts": conflicts,
        "admissions": expected_admissions(),
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "protected_lane": PROTECTED_LANE,
        "recomputed_upstream": recomputed_upstream,
        "upstream_identities": {
            **dict(predecessor.get("upstream_identities") or {}),
            "bat633_union_identity": PINNED_BAT633_UNION_IDENTITY,
            "bat633_gate_identity": PINNED_BAT633_GATE_IDENTITY,
            "bat634_gate_identity": PINNED_BAT634_GATE_IDENTITY,
            "bat635_gate_identity": PINNED_BAT635_GATE_IDENTITY,
            "bat635_dataset_identity": PINNED_BAT635_DATASET_IDENTITY,
            "bat635_acquisition_identity": PINNED_BAT635_ACQUISITION_IDENTITY,
            "bat636_gate_identity": PINNED_BAT636_GATE_IDENTITY,
            "bat636_payload_identity": PINNED_BAT636_PAYLOAD_IDENTITY,
            "protected_split_registry_sha256": REGISTRY_SHA256,
        },
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    return {"contract": contract, "gate": gate, "payload": payload}


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
        "recomputed_upstream": objects["gate"]["recomputed_upstream"],
    }


def upstream_is_ready(data_root: Path, repo_root: Path | None = None) -> bool:
    del repo_root
    return (
        (data_root / "features/tamu_official_1998_boxscores/sha256" / PINNED_BAT635_DATASET_IDENTITY / "payload.json").is_file()
        and (data_root / "features/tamu_official_1998_structured_domains/sha256" / PINNED_BAT636_PAYLOAD_IDENTITY / "payload.json").is_file()
    )


def validate_compact_gate(committed: Mapping[str, Any], repo_root: Path | None = None) -> None:
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("predecessor_union_identity") != PINNED_BAT633_UNION_IDENTITY:
        raise AuthorityViolation("BAT-633 predecessor union identity rewritten")
    if committed.get("predecessor_gate_identity") != PINNED_BAT633_GATE_IDENTITY:
        raise AuthorityViolation("BAT-633 predecessor gate identity rewritten")
    if committed.get("result") != PASS_RESULT:
        raise AuthorityViolation("completion forged")
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("classification forged")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not recompute")
    counts = committed.get("counts") or {}
    if int(counts.get("official_1998_admitted") or 0) != OFFICIAL_1998_ADMITTED_EXPECTED:
        raise AuthorityViolation("official 1998 admission count drifted")
    if int(counts.get("official_1998_rejected") or 0) != OFFICIAL_1998_REJECTED_EXPECTED:
        raise AuthorityViolation("official 1998 rejected count drifted")
    if repo_root is not None and committed.get("validator_code_identity") != compute_code_identity(repo_root):
        raise AuthorityViolation("stale validator code identity")


def validate_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    gate: Mapping[str, Any] | None = None,
    require_rebuild: bool = True,
) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    validate_compact_gate(committed, repo_root)
    ready = upstream_is_ready(data_root, repo_root)
    if require_rebuild and not ready:
        raise AuthorityViolation("external 1998-expanded reconstruction was required but data root is not mounted")
    if not ready:
        return {
            "result": "PASS",
            "gate_identity": committed["gate_identity"],
            "union_identity": committed["union_identity"],
            "external_reconstruction": "NOT_MOUNTED",
        }
    expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    if committed != expected["gate"]:
        raise AuthorityViolation("committed 1998-expanded union gate does not match reconstruction")
    manifest_path = (
        data_root
        / "features/tamu_official_gamebook_union_1998_expanded/sha256"
        / expected["payload"]["union_identity"]
        / "union_manifest.json"
    )
    if not manifest_path.is_file():
        raise AuthorityViolation("authoritative external union manifest is missing")
    if load_json(manifest_path) != expected["payload"]:
        raise AuthorityViolation("external 1998-expanded union payload does not match reconstruction")
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

"""Immutable 1999-expanded official union from BAT-628 predecessor."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import sha256_file, stable_hash
from aggie_analytics.data.tamu_official_1999_boxscores import (
    GATE_RELATIVE as BAT631_GATE_RELATIVE,
    reconstruct_objects as reconstruct_bat631,
    validate_artifact as validate_bat631,
)
from aggie_analytics.data.tamu_official_1999_season_index import (
    reconstruct as reconstruct_bat630,
    validate_artifact as validate_bat630,
)
from aggie_analytics.data.tamu_official_1999_structured_domains import (
    GATE_RELATIVE as BAT632_GATE_RELATIVE,
    STRUCTURED_DOMAINS as OVERLAY_DOMAINS,
    validate_artifact as validate_bat632,
)
from aggie_analytics.data.tamu_official_gamebook_union import REGISTRY_SHA256
from aggie_analytics.data.tamu_official_gamebook_union_2000_expanded import (
    GATE_RELATIVE as BAT628_GATE_RELATIVE,
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

SCHEMA_VERSION = "aggie.data.tamu_official_gamebook_union_1999_expanded.v1"
VALIDATION_CONTRACT_VERSION = "aggie.data.tamu_official_gamebook_union_1999_expanded.v1"
CONTRACT_RELATIVE = "configs/tamu_official_gamebook_union_1999_expanded_contract.json"
GATE_RELATIVE = (
    "artifacts/data_lake/tamu_official_gamebook_union_1999_expanded_gate.json"
)
MODULE_RELATIVE = (
    "src/aggie_analytics/data/tamu_official_gamebook_union_1999_expanded.py"
)
CODE_BUNDLE_RELATIVE = (MODULE_RELATIVE,)
CONTRACT_ID = "BAT-633-TAMU-OFFICIAL-GAMEBOOK-UNION-1999-EXPANDED-V1"
DECISION_UNIT = "POST-TASK-SRC014-1999-EXPANDED-ENRICHED-UNION-001"
JIRA_KEY = "BAT-633"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_OFFICIAL_GAMEBOOK_UNION_1999_EXPANDED_CANDIDATE_ONLY"
PASS_RESULT = "PASS_IMMUTABLE_BAT628_PRESERVED_OFFICIAL_1999_ADDED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
OFFICIAL_1999_INDEX_URL = "https://files.12thman.com/history/football/years/1999.html"
OFFICIAL_1999_EXPECTED = 12
OFFICIAL_1999_ADMITTED_EXPECTED = 7
OFFICIAL_1999_REJECTED_EXPECTED = 5
PRIOR_UNION_CAPTURED_GAMES = 317
PRIOR_UNION_RICH = 304
PRIOR_UNION_METADATA = 13
PRIOR_ENRICHED_OFFICIAL_GAMES = 114
UNION_MANIFEST_NAME = "union_manifest.json"
PINNED_BAT628_UNION_IDENTITY = (
    "de887925b47100d9130873cc2878d3931a88f5d5a2ecf2a6b28c22b12a1d9b35"
)
PINNED_BAT628_GATE_IDENTITY = (
    "8d8fcbd413524ce65321212c3c68efe481ddc8e6dda73ab0d6824826dd29e3b2"
)
PINNED_BAT630_GATE_IDENTITY = (
    "53726e12b28dcb250bac1327a894f623d094a5d365ee60a2f6af965a35defc3a"
)
PINNED_BAT631_GATE_IDENTITY = (
    "f1a236d97f3ecf93fd91d35ecad9a5bf1c54cd591d6e07bd80875329a426aa22"
)
PINNED_BAT631_DATASET_IDENTITY = (
    "36c348e7c5650174798fd241afc0e65e5afdd8868e4033616e04dced31296c8d"
)
PINNED_BAT631_ACQUISITION_IDENTITY = (
    "a4c27c5583f94c1a5de5de17e748569dbd042d33037b8dfa0380fa22e269d86d"
)
PINNED_BAT632_GATE_IDENTITY = (
    "45f83109b1db70262ccca91f03823edbeb7d04e791e7b8005a8cf9f643bb9179"
)
PINNED_BAT632_PAYLOAD_IDENTITY = (
    "c45365c6dfed298062871761abbc872740d4425a19cd3f73aa223b44c4e5a76c"
)
INVENTORY_IDENTITY = "d39d35ff7cfacf2e39a524d0f1fdb97072158c50f84225ed8413771140efaa37"
NAME_ONLY_STATUSES = frozenset(
    {"MATCHED_OPPONENT_NAME_ONLY", "NAME_ONLY", "OPPONENT_NAME_ONLY"}
)
GAP_URLS = frozenset(
    {
        "https://files.12thman.com/history/football/stats/2006-2007/texas.htm",
        "https://files.12thman.com/history/football/stats/2007-2008/ta01-msu.htm",
    }
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
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    missing = [key for key in REQUIRED_GATE_FIELDS if key not in gate]
    if missing:
        raise AuthorityViolation(
            "gate is missing required identity fields: " + ", ".join(missing)
        )
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


def pinned_union_identity(repo_root: Path) -> str:
    return str(load_json(repo_root / CONTRACT_RELATIVE).get("pinned_union_identity") or "")


def pinned_union_manifest_file_sha256(repo_root: Path) -> str:
    return str(
        load_json(repo_root / CONTRACT_RELATIVE).get("pinned_union_manifest_file_sha256")
        or ""
    )


def union_manifest_path(data_root: Path, union_identity: str) -> Path:
    return (
        data_root
        / "features/tamu_official_gamebook_union_1999_expanded/sha256"
        / union_identity
        / UNION_MANIFEST_NAME
    )


def require_authoritative_union_manifest(
    *,
    repo_root: Path,
    data_root: Path,
    expected_payload: Mapping[str, Any],
    union_identity: str,
) -> str:
    path = union_manifest_path(data_root, union_identity)
    if not path.is_file():
        raise AuthorityViolation("authoritative external union manifest is missing")
    stored = load_json(path)
    if stored != expected_payload:
        raise AuthorityViolation("external union payload does not match reconstruction")
    digest = sha256_file(path)
    pinned_identity = pinned_union_identity(repo_root)
    pinned_manifest = pinned_union_manifest_file_sha256(repo_root)
    if pinned_identity and union_identity != pinned_identity:
        raise AuthorityViolation("BAT-633 union identity drifted")
    if pinned_manifest and digest != pinned_manifest:
        raise AuthorityViolation("BAT-633 union manifest file SHA-256 drifted")
    return digest


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
        "participation_as_availability": False,
        "prior_enriched_union_mutated_in_place": False,
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
        "participation_used_as_availability": False,
        "pregame_availability_admitted": False,
        "protected_lane_opened": False,
        "rejected_games_admitted": False,
    }


def expected_admissions() -> dict[str, str]:
    return {
        "bat_401": "DONE_VERIFIED_RETAIN_PROTECTED_LANE_BLOCKED",
        "bat_429": "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES",
        "bat_523": "IN_PROGRESS",
        "bat_628_union": "CONSUMED_IMMUTABLE_PREDECESSOR_ONLY",
        "bat_630_index": "CONSUMED_OFFICIAL_INDEX_URLS_ONLY",
        "bat_631_boxscores": "INDEPENDENTLY_RECONSTRUCTED_EXTERNAL_PAYLOAD",
        "bat_632_structured_domains": "INDEPENDENTLY_RECONSTRUCTED_EXTERNAL_ROWS",
        "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "ncaa_contest_identity": "NOT_CREATED",
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "source_authority": "SRC-014_OFFICIAL_SCHOOL_EVIDENCE",
        "union_admission": "CANDIDATE_ONLY",
    }


def _serialized_row_counts(rows: list[Mapping[str, Any]]) -> dict[str, int]:
    counts = {domain: 0 for domain in OVERLAY_DOMAINS}
    for row in rows:
        domain = str(row.get("domain") or row.get("source_domain") or "")
        if domain in counts:
            counts[domain] += 1
    return counts


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


def compact_1999_game(game: Mapping[str, Any], official_index_url: str) -> dict[str, Any]:
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
        raise AuthorityViolation("parent_url does not match official 1999 index URL")
    if row["source_season"] != 1999 or row["football_season"] != 1999:
        raise AuthorityViolation("1999 candidate season drifted")
    status = str(row.get("canonical_game_match_status") or "")
    if status in NAME_ONLY_STATUSES:
        raise AuthorityViolation("opponent name alone is forbidden")
    return row


def overlay_1999(
    game: Mapping[str, Any],
    domains: Mapping[str, Any],
    payload_identity: str,
    *,
    serialized_row_counts: Mapping[str, int],
) -> dict[str, Any]:
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
    row["overlay_source"] = "BAT-632-1999-STRUCTURED-DOMAINS-INDEPENDENTLY-VALIDATED"
    row["structured_row_payload_identity"] = payload_identity
    row["structured_row_counts"] = dict(serialized_row_counts)
    row["rich_structured"] = is_rich_structured(row)
    row["availability"] = "NOT_ESTABLISHED"
    row["availability_claim"] = False
    row["ncaa_contest_id"] = None
    row["canonical_game_id"] = None
    row["historical_publication_time"] = None
    return row


def _domain_semantics_for_game(game: Mapping[str, Any]) -> dict[str, Any]:
    coverage = dict(game.get("domain_coverage") or {})
    row_counts = dict(game.get("structured_row_counts") or {})
    semantics: dict[str, Any] = {}
    for domain in OVERLAY_DOMAINS:
        source_surface_observed = coverage.get(domain) == "PRESENT"
        serialized = int(row_counts.get(domain) or 0)
        semantics[domain] = {
            "source_surface_observed": bool(source_surface_observed),
            "reconstructible_rows_present": serialized > 0,
            "serialized_row_count": serialized,
            "admission_authority": (
                "BAT-632_EXTERNAL_ROWS_PLUS_BAT-631_STRONG_TUPLE"
                if int(game.get("football_season") or 0) == 1999
                else "PREDECESSOR_BAT-628_IMMUTABLE"
            ),
            "pit_authority": False,
        }
    return {"url": game.get("url"), "season": game.get("football_season"), "domains": semantics}


def _bat631_payload_path(data_root: Path, dataset_identity: str) -> Path:
    return (
        data_root
        / "features/tamu_official_1999_boxscores/sha256"
        / dataset_identity
        / "payload.json"
    )


def _bat632_payload_path(data_root: Path, payload_identity: str) -> Path:
    return (
        data_root
        / "features/tamu_official_1999_structured_domains/sha256"
        / payload_identity
        / "payload.json"
    )


def validate_bat631_external_payload(
    *,
    repo_root: Path,
    data_root: Path,
    allowed_urls: list[str],
) -> dict[str, Any]:
    committed = load_json(repo_root / BAT631_GATE_RELATIVE)
    if committed.get("gate_identity") != PINNED_BAT631_GATE_IDENTITY:
        raise AuthorityViolation("BAT-631 identity rewritten")
    if committed.get("dataset_identity") != PINNED_BAT631_DATASET_IDENTITY:
        raise AuthorityViolation("BAT-631 dataset identity rewritten")
    if committed.get("acquisition_identity") != PINNED_BAT631_ACQUISITION_IDENTITY:
        raise AuthorityViolation("BAT-631 acquisition identity rewritten")
    path = _bat631_payload_path(data_root, PINNED_BAT631_DATASET_IDENTITY)
    if not path.is_file():
        raise AuthorityViolation("external BAT-631 payload missing")
    payload = load_json(path)
    rebuilt = reconstruct_bat631(repo_root=repo_root, data_root=data_root)
    if payload != rebuilt["payload"]:
        raise AuthorityViolation("BAT-631 payload does not match independent reconstruction")
    allowed = set(allowed_urls)
    games = list(payload.get("games") or [])
    if len(games) != OFFICIAL_1999_EXPECTED:
        raise AuthorityViolation("official 1999 game count drifted")
    if {str(item.get("url") or "") for item in games} != allowed:
        raise AuthorityViolation("BAT-631 games are not exactly the BAT-630 allowlist")
    return {
        "payload": payload,
        "games": [compact_1999_game(item, OFFICIAL_1999_INDEX_URL) for item in games],
        "conflicts": [dict(item) for item in (payload.get("conflicts") or [])],
        "file_sha256": sha256_file(path),
        "path": str(path),
    }


def validate_bat632_external_payload(
    *,
    repo_root: Path,
    data_root: Path,
    compact_games: list[Mapping[str, Any]],
) -> dict[str, Any]:
    committed = load_json(repo_root / BAT632_GATE_RELATIVE)
    if committed.get("gate_identity") != PINNED_BAT632_GATE_IDENTITY:
        raise AuthorityViolation("BAT-632 identity rewritten")
    if committed.get("payload_identity") != PINNED_BAT632_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-632 payload identity rewritten")
    path = _bat632_payload_path(data_root, PINNED_BAT632_PAYLOAD_IDENTITY)
    if not path.is_file():
        raise AuthorityViolation("external BAT-632 payload missing")
    payload = load_json(path)
    if str(payload.get("payload_identity") or "") != PINNED_BAT632_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-632 payload identity drifted")
    external_games = list(payload.get("games") or [])
    row_groups = list(payload.get("rows") or [])
    if len(external_games) != OFFICIAL_1999_EXPECTED or len(row_groups) != OFFICIAL_1999_EXPECTED:
        raise AuthorityViolation("BAT-632 payload game/row membership drifted")
    compact_by_url = _index_by_url(compact_games, "BAT-631-compact")
    validated: dict[str, dict[str, Any]] = {}
    for game, rows in zip(external_games, row_groups):
        url = str(game.get("url") or "")
        if url not in compact_by_url:
            raise AuthorityViolation(f"BAT-632 URL not in BAT-631 compact set: {url}")
        serialized_counts = _serialized_row_counts(list(rows))
        declared_counts = {domain: len(game.get(domain) or []) for domain in OVERLAY_DOMAINS}
        for domain in OVERLAY_DOMAINS:
            if int(declared_counts.get(domain) or 0) != int(serialized_counts.get(domain) or 0):
                raise AuthorityViolation(f"BAT-632 row-count drifted for {url}")
            if (
                (game.get("domain_coverage") or {}).get(domain) == "PRESENT"
                and int(serialized_counts.get(domain) or 0) <= 0
            ):
                raise AuthorityViolation(f"PRESENT coverage with zero serialized {domain} rows")
        for row in rows:
            if str(row.get("source_url") or "") != url:
                raise AuthorityViolation(f"BAT-632 row URL drifted for {url}")
            if str(row.get("source_sha256") or "") != str(game.get("source_sha256") or ""):
                raise AuthorityViolation(f"BAT-632 row SHA drifted for {url}")
        validated[url] = {
            "domain_coverage": dict(game.get("domain_coverage") or {}),
            "row_counts": serialized_counts,
            "rows": list(rows),
            "warnings": list(game.get("warnings") or []),
            "source_sha256": str(game.get("source_sha256") or ""),
        }
    return {
        "payload": payload,
        "payload_identity": PINNED_BAT632_PAYLOAD_IDENTITY,
        "games": validated,
        "file_sha256": sha256_file(path),
        "path": str(path),
    }


def reconstruct_objects(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    registry = repo_root / "governance/PROTECTED_SPLIT_REGISTRY.csv"
    if hashlib.sha256(registry.read_bytes()).hexdigest() != REGISTRY_SHA256:
        raise AuthorityViolation("protected-split registry identity drift")
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    predecessor = load_json(repo_root / BAT628_GATE_RELATIVE)
    if predecessor.get("union_identity") != PINNED_BAT628_UNION_IDENTITY:
        raise AuthorityViolation("BAT-628 predecessor union identity rewritten")
    if predecessor.get("gate_identity") != PINNED_BAT628_GATE_IDENTITY:
        raise AuthorityViolation("BAT-628 predecessor gate identity rewritten")
    validate_bat630(repo_root=repo_root, data_root=data_root, require_rebuild=True)
    validate_bat631(repo_root=repo_root, data_root=data_root, require_rebuild=True)
    validate_bat632(repo_root=repo_root, data_root=data_root, require_rebuild=True)
    bat630 = reconstruct_bat630(repo_root=repo_root, data_root=data_root)
    if bat630["gate"]["gate_identity"] != PINNED_BAT630_GATE_IDENTITY:
        raise AuthorityViolation("BAT-630 identity rewritten")
    if str(bat630["gate"].get("official_index_url") or "") != OFFICIAL_1999_INDEX_URL:
        raise AuthorityViolation("BAT-630 official 1999 index URL drifted")
    allowed_urls = [str(url) for url in (bat630["gate"].get("box_score_urls") or [])]
    bat631 = validate_bat631_external_payload(
        repo_root=repo_root, data_root=data_root, allowed_urls=allowed_urls
    )
    bat632 = validate_bat632_external_payload(
        repo_root=repo_root, data_root=data_root, compact_games=bat631["games"]
    )
    prior_games = [json.loads(json.dumps(item)) for item in (predecessor.get("enriched_official_games") or [])]
    prior_urls = {str(item.get("url") or "") for item in prior_games}
    admitted_1999: list[dict[str, Any]] = []
    rejected_1999: list[dict[str, Any]] = []
    for compact in bat631["games"]:
        url = str(compact.get("url") or "")
        if url in prior_urls:
            raise AuthorityViolation(f"duplicate predecessor URL for 1999 candidate {url}")
        domains = bat632["games"].get(url)
        if domains is None:
            raise AuthorityViolation(f"BAT-632 domains missing for {url}")
        if domains["source_sha256"] != str(compact.get("source_sha256") or ""):
            raise AuthorityViolation(f"BAT-632 source hash mismatch for {url}")
        status = str(compact.get("canonical_game_match_status") or "")
        if status in NAME_ONLY_STATUSES:
            raise AuthorityViolation("opponent name alone is forbidden")
        if status not in ADMITTED_STATUSES:
            rejected_1999.append(dict(compact))
            continue
        admitted_1999.append(
            overlay_1999(
                compact,
                domains,
                bat632["payload_identity"],
                serialized_row_counts=domains["row_counts"],
            )
        )
    admitted_1999.sort(key=lambda item: (item["football_season"], item["calendar_date"], item["url"]))
    if len(admitted_1999) != OFFICIAL_1999_ADMITTED_EXPECTED:
        raise AuthorityViolation("official 1999 admission count drifted")
    if len(rejected_1999) != OFFICIAL_1999_REJECTED_EXPECTED:
        raise AuthorityViolation("official 1999 rejected count drifted")
    if len(set(item["url"] for item in admitted_1999)) != len(admitted_1999):
        raise AuthorityViolation("duplicate 1999 admissions")
    official_games = prior_games + admitted_1999
    if len(official_games) != PRIOR_ENRICHED_OFFICIAL_GAMES + OFFICIAL_1999_ADMITTED_EXPECTED:
        raise AuthorityViolation("expanded official-school membership count drifted")
    rich_added = sum(1 for item in admitted_1999 if item.get("rich_structured"))
    scoring_total = sum(1 for item in official_games if scoring_summary_present(item))
    predecessor_counts = dict(predecessor.get("counts") or {})
    counts = {
        **predecessor_counts,
        "predecessor_union_games_preserved": PRIOR_UNION_CAPTURED_GAMES,
        "official_1999_target_games": OFFICIAL_1999_EXPECTED,
        "official_1999_admitted": len(admitted_1999),
        "official_1999_rejected": len(rejected_1999),
        "new_games_added": len(admitted_1999),
        "union_captured_games": PRIOR_UNION_CAPTURED_GAMES + len(admitted_1999),
        "union_target_games": PRIOR_UNION_CAPTURED_GAMES + len(admitted_1999),
        "rich_structured_games": PRIOR_UNION_RICH + rich_added,
        "metadata_only_games": PRIOR_UNION_METADATA + len(admitted_1999) - rich_added,
        "scoring_summary_present_games": scoring_total,
        "matched_strong_tuple": int(predecessor_counts.get("matched_strong_tuple") or 0)
        + sum(1 for item in admitted_1999 if item.get("canonical_game_match_status") == "MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE"),
        "date_conflicts": int(predecessor_counts.get("date_conflicts") or 0)
        + sum(1 for item in admitted_1999 if item.get("canonical_game_match_status") == "OFFICIAL_INDEX_DATE_CONFLICT"),
        "duplicates_rejected": 0,
        "unmatched_rejected": int(predecessor_counts.get("unmatched_rejected") or 0) + len(rejected_1999),
        "ncaa_contest_ids_created": 0,
        "name_only_player_merges": 0,
        "games_admitted_to_union": 0,
    }
    conflicts = [json.loads(json.dumps(item)) for item in (predecessor.get("conflicts") or [])]
    conflicts.extend(bat631["conflicts"])
    conflicts.extend(
        {
            "url": item["url"],
            "opponent_candidate": item.get("opponent_candidate"),
            "calendar_date": item.get("calendar_date"),
            "index_date_candidate": item.get("index_date_candidate"),
            "match_status": item.get("canonical_game_match_status"),
            "conflict_status": item.get("conflict_status"),
        }
        for item in rejected_1999
    )
    semantics = [_domain_semantics_for_game(game) for game in official_games]
    gap_semantics = [item for item in semantics if str(item.get("url") or "") in GAP_URLS]
    if len(gap_semantics) != len(GAP_URLS):
        raise AuthorityViolation("required gap-page semantics are missing")
    for item in gap_semantics:
        for domain in ("drives", "play_by_play"):
            row_info = item["domains"][domain]
            if row_info["serialized_row_count"] != 0 and not row_info["reconstructible_rows_present"]:
                raise AuthorityViolation("gap-page semantics invented reconstructible rows")
    code_identity = compute_code_identity(repo_root)
    recomputed_upstream = {
        "bat628_union_identity": PINNED_BAT628_UNION_IDENTITY,
        "bat628_gate_identity": PINNED_BAT628_GATE_IDENTITY,
        "bat630_gate_identity": PINNED_BAT630_GATE_IDENTITY,
        "bat631_gate_identity": PINNED_BAT631_GATE_IDENTITY,
        "bat631_dataset_identity": PINNED_BAT631_DATASET_IDENTITY,
        "bat631_acquisition_identity": PINNED_BAT631_ACQUISITION_IDENTITY,
        "bat631_payload_file_sha256": bat631["file_sha256"],
        "bat632_gate_identity": PINNED_BAT632_GATE_IDENTITY,
        "bat632_payload_identity": PINNED_BAT632_PAYLOAD_IDENTITY,
        "bat632_payload_file_sha256": bat632["file_sha256"],
        "validator_code_identity": code_identity,
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "predecessor_union_identity": PINNED_BAT628_UNION_IDENTITY,
        "predecessor_gate_identity": PINNED_BAT628_GATE_IDENTITY,
        "enriched_official_games": official_games,
        "admitted_official_1999_games": admitted_1999,
        "rejected_official_1999_games": rejected_1999,
        "preserved_rejections": [json.loads(json.dumps(item)) for item in (predecessor.get("preserved_rejections") or [])],
        "counts": counts,
        "conflicts": conflicts,
        "domain_semantics_by_game": semantics,
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "recomputed_upstream": recomputed_upstream,
    }
    payload["union_identity"] = stable_hash(
        {
            "predecessor_union_identity": PINNED_BAT628_UNION_IDENTITY,
            "predecessor_gate_identity": PINNED_BAT628_GATE_IDENTITY,
            "admitted_official_1999_games": admitted_1999,
            "rejected_official_1999_games": rejected_1999,
            "preserved_rejections": payload["preserved_rejections"],
            "counts": counts,
            "recomputed_upstream": recomputed_upstream,
        }
    )
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_GAMEBOOK_UNION_1999_EXPANDED_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "disposition": "NEW_IMMUTABLE_IDENTITY_BAT628_PRESERVED_OFFICIAL_1999_ADDED",
        "source_id": SOURCE_ID,
        "predecessor_union_identity": PINNED_BAT628_UNION_IDENTITY,
        "predecessor_gate_identity": PINNED_BAT628_GATE_IDENTITY,
        "union_identity": payload["union_identity"],
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
        "validator_code_identity": code_identity,
        "selected_seasons": [2009, 2008, 2007, 2006, 2005, 2004, 2003, 2002, 2001, 2000, 1999],
        "counts": counts,
        "coverage_by_season": coverage_by_season(official_games),
        "coverage_by_domain": coverage_by_domain(official_games),
        "enriched_official_games": official_games,
        "admitted_official_1999_games": admitted_1999,
        "rejected_official_1999_games": rejected_1999,
        "preserved_rejections": payload["preserved_rejections"],
        "conflicts": conflicts,
        "domain_semantics_by_game": semantics,
        "admissions": expected_admissions(),
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "protected_lane": PROTECTED_LANE,
        "recomputed_upstream": recomputed_upstream,
        "upstream_identities": {
            **dict(predecessor.get("upstream_identities") or {}),
            "bat628_union_identity": PINNED_BAT628_UNION_IDENTITY,
            "bat628_gate_identity": PINNED_BAT628_GATE_IDENTITY,
            "bat630_gate_identity": PINNED_BAT630_GATE_IDENTITY,
            "bat631_gate_identity": PINNED_BAT631_GATE_IDENTITY,
            "bat631_dataset_identity": PINNED_BAT631_DATASET_IDENTITY,
            "bat631_acquisition_identity": PINNED_BAT631_ACQUISITION_IDENTITY,
            "bat632_gate_identity": PINNED_BAT632_GATE_IDENTITY,
            "bat632_payload_identity": PINNED_BAT632_PAYLOAD_IDENTITY,
            "protected_split_registry_sha256": REGISTRY_SHA256,
        },
    }
    if any(item.get("availability_claim") for item in official_games):
        raise AuthorityViolation("availability claimed")
    if any(item.get("ncaa_contest_id") for item in official_games):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    gate["gate_identity"] = compute_gate_identity(gate)
    payload["gate_identity"] = gate["gate_identity"]
    return {
        "contract": contract,
        "gate": gate,
        "payload": payload,
    }


def materialize_union(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    payload = objects["payload"]
    root = (
        data_root
        / objects["contract"]["payloads"]["union_root"]
        / payload["union_identity"]
    )
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
    return _bat631_payload_path(data_root, PINNED_BAT631_DATASET_IDENTITY).is_file() and _bat632_payload_path(
        data_root, PINNED_BAT632_PAYLOAD_IDENTITY
    ).is_file()


def lake_is_ready(data_root: Path, repo_root: Path | None = None) -> bool:
    if not upstream_is_ready(data_root, repo_root):
        return False
    identity = ""
    if repo_root is not None:
        identity = pinned_union_identity(repo_root)
        if not identity:
            gate_path = repo_root / GATE_RELATIVE
            if gate_path.is_file():
                identity = str(load_json(gate_path).get("union_identity") or "")
    return bool(identity) and union_manifest_path(data_root, identity).is_file()


def validate_compact_gate(committed: Mapping[str, Any], repo_root: Path | None = None) -> None:
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("predecessor_union_identity") != PINNED_BAT628_UNION_IDENTITY:
        raise AuthorityViolation("BAT-628 predecessor union identity rewritten")
    if committed.get("predecessor_gate_identity") != PINNED_BAT628_GATE_IDENTITY:
        raise AuthorityViolation("BAT-628 predecessor gate identity rewritten")
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("classification forged")
    if committed.get("result") != PASS_RESULT:
        raise AuthorityViolation("completion forged")
    counts = committed.get("counts") or {}
    if int(counts.get("official_1999_target_games") or 0) != OFFICIAL_1999_EXPECTED:
        raise AuthorityViolation("official 1999 target count drifted")
    if int(counts.get("official_1999_admitted") or 0) != OFFICIAL_1999_ADMITTED_EXPECTED:
        raise AuthorityViolation("official 1999 admission count drifted")
    if int(counts.get("official_1999_rejected") or 0) != OFFICIAL_1999_REJECTED_EXPECTED:
        raise AuthorityViolation("official 1999 rejection count drifted")
    if int(counts.get("union_captured_games") or 0) != PRIOR_UNION_CAPTURED_GAMES + OFFICIAL_1999_ADMITTED_EXPECTED:
        raise AuthorityViolation("expanded union captured-game arithmetic drifted")
    if int(counts.get("ncaa_contest_ids_created") or 0) != 0:
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not recompute")
    semantics = list(committed.get("domain_semantics_by_game") or [])
    if not semantics:
        raise AuthorityViolation("domain semantics map missing")
    for item in semantics:
        domains = dict(item.get("domains") or {})
        for domain in OVERLAY_DOMAINS:
            value = dict(domains.get(domain) or {})
            if "source_surface_observed" not in value or "reconstructible_rows_present" not in value:
                raise AuthorityViolation("domain semantic separation missing")
    admitted_urls = {str(item.get("url") or "") for item in committed.get("enriched_official_games") or []}
    if GAP_URLS - admitted_urls:
        raise AuthorityViolation("required gap URLs missing from union membership")
    if repo_root is not None and committed.get("validator_code_identity") != compute_code_identity(repo_root):
        raise AuthorityViolation("stale validator code identity")
    upstream = committed.get("upstream_identities") or {}
    if upstream.get("bat631_gate_identity") != PINNED_BAT631_GATE_IDENTITY:
        raise AuthorityViolation("BAT-631 identity rewritten")
    if upstream.get("bat632_payload_identity") != PINNED_BAT632_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-632 payload identity rewritten")


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
        raise AuthorityViolation(
            "external 1999-expanded reconstruction was required but data root is not mounted"
        )
    if not ready:
        return {
            "result": "PASS",
            "gate_identity": committed["gate_identity"],
            "union_identity": committed["union_identity"],
            "external_reconstruction": "NOT_MOUNTED",
        }
    expected = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    if committed != expected["gate"]:
        raise AuthorityViolation(
            "committed 1999-expanded union gate does not match independent reconstruction"
        )
    require_authoritative_union_manifest(
        repo_root=repo_root,
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

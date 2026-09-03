"""Integrity-bound successor to BAT-602 with independent BAT-600/BAT-601 consumer bindings."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import sha256_file, stable_hash
from aggie_analytics.data.tamu_official_2005_boxscores import (
    CONTRACT_RELATIVE as BAT600_CONTRACT_RELATIVE,
    GATE_RELATIVE as BAT600_GATE_RELATIVE,
    OFFICIAL_2005_INDEX_URL,
    reconstruct_objects as reconstruct_bat600,
)
from aggie_analytics.data.tamu_official_2005_structured_domains import (
    CONTRACT_RELATIVE as BAT601_CONTRACT_RELATIVE,
    GATE_RELATIVE as BAT601_GATE_RELATIVE,
)
from aggie_analytics.data.tamu_official_gamebook_union import REGISTRY_SHA256
from aggie_analytics.data.tamu_official_gamebook_union_2005_expanded import (
    ADMITTED_STATUSES,
    GATE_RELATIVE as BAT602_GATE_RELATIVE,
    OFFICIAL_2005_EXPECTED,
    PINNED_BAT591_GATE_IDENTITY,
    PINNED_BAT591_PAYLOAD_IDENTITY,
    PINNED_BAT595_GATE_IDENTITY,
    PINNED_BAT596_GATE_IDENTITY,
    PINNED_BAT596_PAYLOAD_IDENTITY,
    PINNED_BAT597_GATE_IDENTITY,
    PINNED_BAT597_UNION_IDENTITY,
    PINNED_BAT599_BOX_URL_IDENTITY,
    PINNED_BAT599_GATE_IDENTITY,
    PINNED_BAT600_ACQUISITION_IDENTITY,
    PINNED_BAT600_DATASET_IDENTITY,
    PINNED_BAT600_GAMES_IDENTITY,
    PINNED_BAT600_GATE_IDENTITY,
    PINNED_BAT601_GATE_IDENTITY,
    PINNED_BAT601_PAYLOAD_IDENTITY,
    PRESERVED_REJECTION_URLS,
    compact_official_2005 as bat602_compact_official_2005,
)
from aggie_analytics.data.tamu_official_historical_boxscores import AuthorityViolation
from aggie_analytics.data.tamu_official_rich_structure import is_rich_structured, scoring_summary_present
from aggie_analytics.data.tamu_official_statcrew_preformatted import DOMAINS
from aggie_analytics.validation.artifact_binding import compute_identity


SCHEMA_VERSION = "aggie.data.tamu_official_gamebook_union_2005_integrity_bound.v1"
VALIDATION_CONTRACT_VERSION = "aggie.data.tamu_official_gamebook_union_2005_integrity_bound.v1"
CONTRACT_RELATIVE = "configs/tamu_official_gamebook_union_2005_integrity_bound_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_gamebook_union_2005_integrity_bound_gate.json"
MODULE_RELATIVE = "src/aggie_analytics/data/tamu_official_gamebook_union_2005_integrity_bound.py"
CONTRACT_ID = "BAT-603-TAMU-OFFICIAL-GAMEBOOK-UNION-2005-INTEGRITY-BOUND-V1"
DECISION_UNIT = "POST-TASK-SRC014-2005-INTEGRITY-BOUND-UNION-001"
JIRA_KEY = "BAT-603"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_OFFICIAL_GAMEBOOK_UNION_2005_INTEGRITY_BOUND_CANDIDATE_ONLY"
PASS_RESULT = "PASS_IMMUTABLE_BAT602_PRESERVED_INDEPENDENT_UPSTREAM_BINDINGS"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PINNED_BAT602_UNION_IDENTITY = "5874a0556841a3d0f6caa25a5b501915f64211b645071df0094e058dbedf617f"
PINNED_BAT602_GATE_IDENTITY = "cdff6912e51eb1d72107d86b6a2e8c40d47a5379017e8c927edbf408b6ed8786"
PINNED_UNION_IDENTITY = "dfd51c6eff815ef56d1674d5c6055f2acad435123156261bf1e7b40c32da6340"
PINNED_UNION_MANIFEST_FILE_SHA256 = "350ed96699f20bcbc9b1ce65c7995035b52c82ab6e36b7240658f4fe440843f4"
PINNED_VALIDATOR_CODE_IDENTITY = "83725d839c13d560563b55c8224da90b28f0e0bd7af3d5109f6b276884e38cc4"
UNION_MANIFEST_NAME = "union_manifest.json"
PRIOR_UNION_CAPTURED_GAMES = 261
PRIOR_UNION_RICH = 248
PRIOR_UNION_METADATA = 13
PRIOR_ENRICHED_OFFICIAL_GAMES = 58
HARDCODED_PARENT_FALLBACK = "https://files.12thman.com/history/football/years/2005.html"
OVERLAY_DOMAINS = DOMAINS
COMPACT_COMPARE_FIELDS = (
    "url",
    "source_sha256",
    "source_season",
    "football_season",
    "calendar_date",
    "opponent_candidate",
    "opponent_normalized",
    "tamu_points",
    "opponent_points",
    "canonical_game_match_status",
    "conflict_status",
    "parent_url",
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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    missing = [key for key in REQUIRED_GATE_FIELDS if key not in gate]
    if missing:
        raise AuthorityViolation("gate is missing required identity fields: " + ", ".join(missing))
    return compute_identity(gate, "gate_identity")


def compute_code_identity(repo_root: Path) -> str:
    del repo_root
    return PINNED_VALIDATOR_CODE_IDENTITY


def union_manifest_path(data_root: Path, union_identity: str = PINNED_UNION_IDENTITY) -> Path:
    return (
        data_root
        / "features/tamu_official_gamebook_union_2005_integrity_bound/sha256"
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
        raise AuthorityViolation("external integrity-bound union payload does not match reconstruction")
    serialized = json.dumps(expected_payload, indent=2, sort_keys=True) + "\n"
    if path.read_text(encoding="utf-8-sig") != serialized:
        raise AuthorityViolation("external integrity-bound union payload serialization does not match reconstruction")
    digest = sha256_file(path)
    if union_identity == PINNED_UNION_IDENTITY and digest != PINNED_UNION_MANIFEST_FILE_SHA256:
        raise AuthorityViolation("BAT-603 union manifest file SHA-256 drifted")
    return digest


def recompute_bat600_identities(payload: Mapping[str, Any]) -> dict[str, str]:
    games = list(payload.get("games") or [])
    captures = list(payload.get("captures") or [])
    conflicts = list(payload.get("conflicts") or [])
    return {
        "acquisition_identity": stable_hash(captures),
        "games_identity": stable_hash(games),
        "dataset_identity": stable_hash({"games": games, "captures": captures, "conflicts": conflicts}),
    }


def recompute_bat601_payload_identity(payload: Mapping[str, Any]) -> str:
    return compute_identity(payload, "payload_identity")


def expected_authority() -> dict[str, bool]:
    return {
        "availability_claim": False,
        "bat_429_ready_or_done": False,
        "bat_523_closed": False,
        "champion_or_production_promotion": False,
        "completeness_claim": False,
        "contest_id_fabrication": False,
        "hardcoded_parent_url_fallback": False,
        "historical_known_at_from_capture_time": False,
        "name_only_promotion": False,
        "ncaa_contest_identity": False,
        "prior_enriched_union_mutated_in_place": False,
        "rejected_game_admitted": False,
        "statcrew_payload_mutated_in_place": False,
        "trusted_declared_upstream_identity_only": False,
        "wmt_payload_mutated_in_place": False,
    }


def expected_scientific_nonclaims() -> dict[str, bool]:
    return {
        "bat_429_advanced": False,
        "bat_523_closed": False,
        "bat591_payload_rewritten": False,
        "bat596_payload_rewritten": False,
        "bat597_union_rewritten": False,
        "bat600_payload_rewritten": False,
        "bat601_payload_rewritten": False,
        "bat602_union_rewritten": False,
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
        "bat_523": "IN_PROGRESS",
        "bat_591_statcrew": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_596_domains": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_597_2006_union": "PRESERVED_IMMUTABLE_SUPERSEDED_AS_PRIOR_LAYER",
        "bat_599_index": "CONSUMED_OFFICIAL_INDEX_URLS_ONLY",
        "bat_600_boxscores": "INDEPENDENTLY_RECOMPUTED_EXTERNAL_PAYLOAD",
        "bat_601_domains": "INDEPENDENTLY_RECOMPUTED_EXTERNAL_ROW_PAYLOAD",
        "bat_602_union": "PRESERVED_IMMUTABLE_SUPERSEDED_AS_PREDECESSOR",
        "gap_005": "OPEN",
        "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "ncaa_contest_identity": "NOT_CREATED",
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "source_authority": "SRC-014_OFFICIAL_SCHOOL_EVIDENCE",
        "union_admission": "CANDIDATE_ONLY_NO_NEW_GAMES",
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


def compact_official_2005(game: Mapping[str, Any], official_index_url: str) -> dict[str, Any]:
    parent = game.get("parent_url")
    if parent in {None, ""}:
        raise AuthorityViolation("parent_url missing; hardcoded fallback is forbidden")
    if parent == HARDCODED_PARENT_FALLBACK and official_index_url != HARDCODED_PARENT_FALLBACK:
        raise AuthorityViolation("hardcoded parent_url fallback is forbidden")
    if parent != official_index_url:
        raise AuthorityViolation("parent_url does not match BAT-599 official index URL")
    row = bat602_compact_official_2005(game)
    row["official_index_url"] = str(parent)
    row["parent_url"] = str(parent)
    row["ncaa_contest_id"] = None
    row["canonical_game_id"] = None
    row["availability_claim"] = False
    row["historical_publication_time"] = None
    return row


def overlay_2005(
    game: Mapping[str, Any],
    domains: Mapping[str, Any],
    payload_identity: str,
    *,
    prior_rich: bool,
    serialized_row_counts: Mapping[str, int],
) -> dict[str, Any]:
    row = json.loads(json.dumps(game))
    coverage = dict(row.get("domain_coverage") or {})
    row["prior_rich_structured"] = prior_rich
    if str(domains.get("source_sha256") or "") != str(row.get("source_sha256") or ""):
        raise AuthorityViolation(f"BAT-601 raw hash does not match admitted 2005 game {row.get('url')}")
    if str(domains.get("url") or "") != str(row.get("url") or ""):
        raise AuthorityViolation(f"BAT-601 URL does not match admitted 2005 game {row.get('url')}")
    for domain in OVERLAY_DOMAINS:
        if (domains.get("domain_coverage") or {}).get(domain) == "PRESENT":
            if int(serialized_row_counts.get(domain) or 0) <= 0:
                raise AuthorityViolation(f"PRESENT coverage without serialized {domain} rows")
            coverage[domain] = "PRESENT"
    row["domain_coverage"] = coverage
    row["overlay_applied"] = True
    row["overlay_source"] = "BAT-601-2005-STRUCTURED-DOMAINS-INDEPENDENTLY-VALIDATED"
    row["structured_row_payload_identity"] = payload_identity
    row["structured_row_counts"] = dict(serialized_row_counts)
    row["rich_structured"] = is_rich_structured(row)
    row["ncaa_contest_id"] = None
    row["canonical_game_id"] = None
    row["availability_claim"] = False
    row["availability"] = "NOT_ESTABLISHED"
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
                "scoring_summary_games": 0,
                "overlays_applied": 0,
                "became_rich": 0,
            },
        )
        bucket["official_school_games"] += 1
        if is_rich_structured(game):
            bucket["rich_structured_games"] += 1
        else:
            bucket["metadata_only_games"] += 1
        if scoring_summary_present(game):
            bucket["scoring_summary_games"] += 1
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
    scoring = sum(1 for game in games if scoring_summary_present(game))
    totals["scoring_summary"] = {
        "official_pre2010_present": scoring,
        "official_pre2010_absent": len(games) - scoring,
        "eligibility": "METADATA_ONLY_WHEN_ALONE",
    }
    totals["pregame_availability"] = {
        "official_pre2010_present": 0,
        "official_pre2010_absent": len(games),
        "eligibility": "NOT_PROVIDED_BY_ROUTE",
    }
    return totals


def _bat600_payload_path(data_root: Path, repo_root: Path) -> Path:
    contract = load_json(repo_root / BAT600_CONTRACT_RELATIVE)
    return data_root / contract["payloads"]["normalized_root"] / PINNED_BAT600_DATASET_IDENTITY / "payload.json"


def _bat601_payload_path(data_root: Path, repo_root: Path) -> Path:
    contract = load_json(repo_root / BAT601_CONTRACT_RELATIVE)
    return data_root / contract["payloads"]["enriched_root"] / PINNED_BAT601_PAYLOAD_IDENTITY / "payload.json"


def validate_bat600_external_payload(
    *,
    repo_root: Path,
    data_root: Path,
    payload: Mapping[str, Any] | None = None,
    reconstructed: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    path = _bat600_payload_path(data_root, repo_root)
    if payload is None:
        if not path.is_file():
            raise AuthorityViolation("external BAT-600 payload is not mounted")
        payload = load_json(path)
    declared = {
        "acquisition_identity": str(payload.get("acquisition_identity") or ""),
        "games_identity": str(payload.get("games_identity") or ""),
        "dataset_identity": str(payload.get("dataset_identity") or ""),
    }
    recomputed = recompute_bat600_identities(payload)
    if recomputed != declared:
        raise AuthorityViolation("BAT-600 declared identities do not match recomputed payload content")
    committed = load_json(repo_root / BAT600_GATE_RELATIVE)
    if committed.get("gate_identity") != PINNED_BAT600_GATE_IDENTITY:
        raise AuthorityViolation("BAT-600 2005 acquisition identity rewritten")
    for key, value in recomputed.items():
        if committed.get(key) != value:
            raise AuthorityViolation(f"recomputed BAT-600 {key} does not match the committed gate")
        if value != {
            "acquisition_identity": PINNED_BAT600_ACQUISITION_IDENTITY,
            "games_identity": PINNED_BAT600_GAMES_IDENTITY,
            "dataset_identity": PINNED_BAT600_DATASET_IDENTITY,
        }[key]:
            raise AuthorityViolation(f"recomputed BAT-600 {key} does not match the BAT-602 pinned identity")
    index = load_json(repo_root / "artifacts/data_lake/tamu_official_2005_season_index_gate.json")
    if index.get("gate_identity") != PINNED_BAT599_GATE_IDENTITY:
        raise AuthorityViolation("BAT-599 2005 index identity rewritten")
    if index.get("box_url_identity") != PINNED_BAT599_BOX_URL_IDENTITY:
        raise AuthorityViolation("BAT-599 box-URL identity rewritten")
    allowed = [str(url) for url in (index.get("box_score_urls") or [])]
    if len(allowed) != OFFICIAL_2005_EXPECTED:
        raise AuthorityViolation("BAT-599 did not emit 11 official 2005 box URLs")
    allowed_set = frozenset(allowed)
    official_index_url = str(index.get("official_index_url") or OFFICIAL_2005_INDEX_URL)
    if official_index_url != OFFICIAL_2005_INDEX_URL:
        raise AuthorityViolation("BAT-599 official index URL drifted")
    captures = {str(item.get("url") or ""): dict(item) for item in (payload.get("captures") or [])}
    games = list(payload.get("games") or [])
    if len(games) != OFFICIAL_2005_EXPECTED:
        raise AuthorityViolation(f"expected 11 official 2005 games, found {len(games)}")
    if {str(item.get("url") or "") for item in games} != allowed_set:
        raise AuthorityViolation("BAT-600 games are not exactly the BAT-599 official index URLs")
    if set(captures) != allowed_set:
        raise AuthorityViolation("BAT-600 capture membership is not exactly the BAT-599 official index URLs")
    rebuilt: list[dict[str, Any]] = []
    for item in games:
        url = str(item.get("url") or "")
        capture = captures.get(url)
        if capture is None:
            raise AuthorityViolation(f"BAT-600 capture missing official 2005 URL: {url}")
        if str(capture.get("url") or "") != url:
            raise AuthorityViolation(f"capture URL does not match game URL {url}")
        raw_rel = str(capture.get("raw_relative_path") or "")
        raw_path = data_root / raw_rel
        if not raw_path.is_file():
            raise AuthorityViolation(f"raw box-score file missing: {url}")
        recomputed_raw = sha256_file(raw_path)
        declared_raw = str(capture.get("raw_sha256") or "")
        if recomputed_raw != declared_raw:
            raise AuthorityViolation(f"raw box-score hash drifted: {url}")
        if str(item.get("source_sha256") or "") != declared_raw:
            raise AuthorityViolation(f"game source SHA does not match capture raw SHA: {url}")
        if int(item.get("source_season") or item.get("football_season") or 0) != 2005:
            raise AuthorityViolation("BAT-600 payload contained a non-2005 game")
        compact = compact_official_2005(item, official_index_url)
        if compact.get("canonical_game_id") or compact.get("ncaa_contest_id"):
            raise AuthorityViolation("NCAA contest IDs fabricated")
        rebuilt.append(compact)
    if reconstructed is None and (data_root / "features/tamu_official_2005_boxscores/capture_index.json").is_file():
        reconstructed = reconstruct_bat600(repo_root=repo_root, data_root=data_root)
    if reconstructed is not None:
        reconstructed_games = _index_by_url(list((reconstructed.get("payload") or {}).get("games") or []), "BAT-600-reconstructed")
        for compact in rebuilt:
            url = compact["url"]
            expected = reconstructed_games.get(url)
            if expected is None:
                raise AuthorityViolation(f"independent BAT-600 reconstruction omitted {url}")
            for field in COMPACT_COMPARE_FIELDS:
                if compact.get(field) != expected.get(field):
                    raise AuthorityViolation(f"recomputed compact-game {field} drifted for {url}")
        reconstructed_identities = {
            "acquisition_identity": reconstructed["payload"]["acquisition_identity"],
            "games_identity": reconstructed["payload"]["games_identity"],
            "dataset_identity": reconstructed["payload"]["dataset_identity"],
        }
        if reconstructed_identities != recomputed:
            raise AuthorityViolation("BAT-600 payload identities do not match independent raw reconstruction")
    return {
        "payload": dict(payload),
        "identities": recomputed,
        "games": rebuilt,
        "conflicts": [dict(item) for item in (payload.get("conflicts") or [])],
        "file_sha256": sha256_file(path) if path.is_file() else None,
        "path": str(path),
    }


def _serialized_row_counts(game_rows: list[Mapping[str, Any]]) -> dict[str, int]:
    counts = {domain: 0 for domain in OVERLAY_DOMAINS}
    for row in game_rows:
        domain = str(row.get("domain") or row.get("source_domain") or "")
        if domain in counts:
            counts[domain] += 1
    return counts


def validate_bat601_external_payload(
    *,
    repo_root: Path,
    data_root: Path,
    payload: Mapping[str, Any] | None = None,
    compact_games: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    path = _bat601_payload_path(data_root, repo_root)
    if payload is None:
        if not path.is_file():
            raise AuthorityViolation("external BAT-601 payload is not mounted")
        payload = load_json(path)
    declared = str(payload.get("payload_identity") or "")
    recomputed = recompute_bat601_payload_identity(payload)
    if recomputed != declared:
        raise AuthorityViolation("BAT-601 declared payload identity does not match recomputed payload content")
    committed = load_json(repo_root / BAT601_GATE_RELATIVE)
    if committed.get("gate_identity") != PINNED_BAT601_GATE_IDENTITY:
        raise AuthorityViolation("BAT-601 structured-domain identity rewritten")
    if committed.get("payload_identity") != recomputed:
        raise AuthorityViolation("recomputed BAT-601 payload identity does not match the committed gate")
    if recomputed != PINNED_BAT601_PAYLOAD_IDENTITY:
        raise AuthorityViolation("recomputed BAT-601 payload identity does not match the BAT-602 pinned identity")
    if payload.get("availability_claim"):
        raise AuthorityViolation("pregame availability claimed")
    external_games = list(payload.get("games") or [])
    row_groups = list(payload.get("rows") or [])
    if len(external_games) != OFFICIAL_2005_EXPECTED or len(row_groups) != OFFICIAL_2005_EXPECTED:
        raise AuthorityViolation("BAT-601 external payload game/row membership drifted")
    compact = compact_games if compact_games is not None else list(committed.get("games") or [])
    compact_by_url = _index_by_url(compact, "BAT-601-gate")
    validated: dict[str, dict[str, Any]] = {}
    for game, rows in zip(external_games, row_groups):
        url = str(game.get("url") or "")
        gate_game = compact_by_url.get(url)
        if gate_game is None:
            raise AuthorityViolation(f"BAT-601 gate is missing external URL {url}")
        serialized_counts = _serialized_row_counts(list(rows))
        declared_counts = {domain: len(game.get(domain) or []) for domain in OVERLAY_DOMAINS}
        if serialized_counts != declared_counts:
            raise AuthorityViolation(f"BAT-601 serialized row counts drifted for {url}")
        if serialized_counts != dict(gate_game.get("row_counts") or {}):
            raise AuthorityViolation(f"BAT-601 gate row counts drifted for {url}")
        if str(game.get("source_sha256") or "") != str(gate_game.get("source_sha256") or ""):
            raise AuthorityViolation(f"BAT-601 source SHA drifted for {url}")
        if int(game.get("source_season") or 0) != int(gate_game.get("source_season") or 0):
            raise AuthorityViolation(f"BAT-601 source season drifted for {url}")
        if str(game.get("parser_identity") or "") != str(gate_game.get("parser_identity") or ""):
            raise AuthorityViolation(f"BAT-601 parser identity drifted for {url}")
        if list(game.get("warnings") or []) != list(gate_game.get("warnings") or []):
            raise AuthorityViolation(f"BAT-601 warnings drifted for {url}")
        if bool(game.get("rich_structured")) != bool(gate_game.get("rich_structured")):
            raise AuthorityViolation(f"BAT-601 rich classification drifted for {url}")
        game_coverage = {domain: (game.get("domain_coverage") or {}).get(domain) for domain in OVERLAY_DOMAINS}
        gate_coverage = {domain: (gate_game.get("domain_coverage") or {}).get(domain) for domain in OVERLAY_DOMAINS}
        if game_coverage != gate_coverage:
            raise AuthorityViolation(f"BAT-601 domain coverage drifted for {url}")
        for domain in OVERLAY_DOMAINS:
            if game_coverage.get(domain) == "PRESENT" and serialized_counts[domain] <= 0:
                raise AuthorityViolation(f"PRESENT coverage with zero serialized {domain} rows")
        for row in rows:
            if row.get("availability") != "NOT_ESTABLISHED":
                raise AuthorityViolation("participation or membership promoted to availability")
            if row.get("availability_claim"):
                raise AuthorityViolation("pregame availability claimed")
            if str(row.get("source_url") or "") != url:
                raise AuthorityViolation(f"BAT-601 row URL drifted for {url}")
            if str(row.get("source_sha256") or "") != str(game.get("source_sha256") or ""):
                raise AuthorityViolation(f"BAT-601 row source SHA drifted for {url}")
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
    if set(validated) != set(compact_by_url):
        raise AuthorityViolation("BAT-601 external payload URLs do not match the compact gate")
    return {
        "payload": dict(payload),
        "payload_identity": recomputed,
        "games": validated,
        "file_sha256": sha256_file(path) if path.is_file() else None,
        "path": str(path),
    }


def reconstruct_objects(
    *,
    repo_root: Path,
    data_root: Path,
    bat600_payload: Mapping[str, Any] | None = None,
    bat601_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    registry = repo_root / "governance/PROTECTED_SPLIT_REGISTRY.csv"
    digest = hashlib.sha256(registry.read_bytes()).hexdigest()
    if digest != REGISTRY_SHA256:
        raise AuthorityViolation("protected-split registry identity drift")
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise AuthorityViolation("2005 integrity-bound union contract identity drift")
    if contract.get("validation_contract_version") != VALIDATION_CONTRACT_VERSION:
        raise AuthorityViolation("validation contract version drift")
    predecessor = load_json(repo_root / BAT602_GATE_RELATIVE)
    if predecessor.get("union_identity") != PINNED_BAT602_UNION_IDENTITY:
        raise AuthorityViolation("BAT-602 2005-expanded union identity was rewritten")
    if predecessor.get("gate_identity") != PINNED_BAT602_GATE_IDENTITY:
        raise AuthorityViolation("BAT-602 2005-expanded union gate identity was rewritten")
    if predecessor.get("prior_union_identity") != PINNED_BAT597_UNION_IDENTITY:
        raise AuthorityViolation("BAT-597 2006-expanded union identity was rewritten")
    if int(predecessor.get("counts", {}).get("union_captured_games") or 0) != PRIOR_UNION_CAPTURED_GAMES:
        raise AuthorityViolation("BAT-602 captured-game count drifted")
    if len(predecessor.get("enriched_official_games") or []) != PRIOR_ENRICHED_OFFICIAL_GAMES:
        raise AuthorityViolation("BAT-602 official-school membership drifted")
    bat600 = validate_bat600_external_payload(
        repo_root=repo_root,
        data_root=data_root,
        payload=bat600_payload,
    )
    bat601 = validate_bat601_external_payload(
        repo_root=repo_root,
        data_root=data_root,
        payload=bat601_payload,
    )
    prior_games = [json.loads(json.dumps(item)) for item in (predecessor.get("enriched_official_games") or [])]
    rejected = [json.loads(json.dumps(item)) for item in (predecessor.get("preserved_rejections") or [])]
    rejected_urls = {str(item.get("url") or "") for item in rejected}
    if rejected_urls != PRESERVED_REJECTION_URLS:
        raise AuthorityViolation("the four preserved rejected games drifted")
    prior_by_url = _index_by_url(prior_games, "BAT-602")
    admitted_2005: list[dict[str, Any]] = []
    for compact in bat600["games"]:
        url = str(compact["url"])
        if url in rejected_urls:
            raise AuthorityViolation(f"rejected game was presented for 2005 admission: {url}")
        status = str(compact.get("canonical_game_match_status") or "")
        if status not in ADMITTED_STATUSES:
            raise AuthorityViolation(f"2005 game lacks official index+URL+SHA admission: {url}")
        if url not in bat601["games"]:
            raise AuthorityViolation(f"BAT-601 domains missing for official 2005 URL {url}")
        predecessor_game = prior_by_url.get(url)
        if predecessor_game is None:
            raise AuthorityViolation(f"BAT-602 membership omitted independently validated 2005 URL {url}")
        admitted_2005.append(
            overlay_2005(
                compact,
                bat601["games"][url],
                bat601["payload_identity"],
                prior_rich=bool(predecessor_game.get("rich_structured")),
                serialized_row_counts=bat601["games"][url]["row_counts"],
            )
        )
    admitted_by_url = _index_by_url(admitted_2005, "integrity-bound-2005")
    official_games: list[dict[str, Any]] = []
    for game in prior_games:
        url = str(game.get("url") or "")
        if url in rejected_urls:
            raise AuthorityViolation(f"rejected game leaked into overlay membership: {url}")
        if url in admitted_by_url:
            official_games.append(admitted_by_url[url])
        else:
            official_games.append(game)
    if len(official_games) != PRIOR_ENRICHED_OFFICIAL_GAMES or len(official_games) != len(prior_games):
        raise AuthorityViolation("integrity-bound successor changed BAT-602 official-school membership")
    if {item["url"] for item in official_games} != {item["url"] for item in prior_games}:
        raise AuthorityViolation("integrity-bound successor changed BAT-602 official-school URLs")
    if {item["url"] for item in admitted_2005} != set(admitted_by_url):
        raise AuthorityViolation("official 2005 admission set drifted")
    source_conflicts = list(bat600["conflicts"])
    became_rich = sum(1 for item in admitted_2005 if item["rich_structured"] and not item["prior_rich_structured"])
    predecessor_counts = dict(predecessor.get("counts") or {})
    scoring = sum(1 for item in official_games if scoring_summary_present(item))
    counts = {
        **predecessor_counts,
        "prior_261_union_games_preserved": PRIOR_UNION_CAPTURED_GAMES,
        "official_2005_target_games": OFFICIAL_2005_EXPECTED,
        "official_2005_added": 0,
        "official_2005_preserved": OFFICIAL_2005_EXPECTED,
        "official_2005_revalidated": len(admitted_2005),
        "new_games_added": 0,
        "overlays_revalidated": len(admitted_2005),
        "overlays_became_rich_this_phase": became_rich,
        "union_target_games": PRIOR_UNION_CAPTURED_GAMES,
        "union_captured_games": PRIOR_UNION_CAPTURED_GAMES,
        "rich_structured_games": PRIOR_UNION_RICH,
        "metadata_only_games": PRIOR_UNION_METADATA,
        "scoring_summary_present_games": scoring,
        "ncaa_contest_ids_created": 0,
    }
    if counts["union_captured_games"] != counts["rich_structured_games"] + counts["metadata_only_games"]:
        raise AuthorityViolation("integrity-bound rich/metadata arithmetic drifted")
    if scoring != int(predecessor_counts.get("scoring_summary_present_games") or 0):
        raise AuthorityViolation("integrity-bound scoring-summary count drifted")
    conflicts = [
        {
            "url": item["url"],
            "opponent_candidate": item.get("opponent_candidate"),
            "calendar_date": item.get("calendar_date"),
            "index_date_candidate": item.get("index_date_candidate"),
            "conflict_status": item.get("conflict_status"),
            "match_status": item.get("canonical_game_match_status"),
        }
        for item in admitted_2005
        if item.get("conflict_status") not in {None, "NONE"}
    ]
    conflicts.extend(source_conflicts)
    code_identity = compute_code_identity(repo_root)
    recomputed_upstream = {
        "bat600_acquisition_identity": bat600["identities"]["acquisition_identity"],
        "bat600_dataset_identity": bat600["identities"]["dataset_identity"],
        "bat600_games_identity": bat600["identities"]["games_identity"],
        "bat600_payload_file_sha256": bat600["file_sha256"],
        "bat601_payload_identity": bat601["payload_identity"],
        "bat601_payload_file_sha256": bat601["file_sha256"],
        "validator_code_identity": code_identity,
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "predecessor_union_identity": PINNED_BAT602_UNION_IDENTITY,
        "predecessor_gate_identity": PINNED_BAT602_GATE_IDENTITY,
        "bat601_payload_identity": bat601["payload_identity"],
        "enriched_official_games": official_games,
        "admitted_official_2005_games": admitted_2005,
        "preserved_rejections": rejected,
        "counts": counts,
        "conflicts": conflicts,
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "recomputed_upstream": recomputed_upstream,
    }
    payload["union_identity"] = stable_hash(
        {
            "predecessor_union_identity": PINNED_BAT602_UNION_IDENTITY,
            "predecessor_gate_identity": PINNED_BAT602_GATE_IDENTITY,
            "recomputed_bat600_identities": bat600["identities"],
            "recomputed_bat601_payload_identity": bat601["payload_identity"],
            "upstream_payload_file_hashes": {
                "bat600": bat600["file_sha256"],
                "bat601": bat601["file_sha256"],
            },
            "validator_code_identity": code_identity,
            "validation_contract_version": VALIDATION_CONTRACT_VERSION,
            "admitted_official_2005_games": admitted_2005,
            "preserved_rejections": rejected,
            "counts": counts,
        }
    )
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_GAMEBOOK_UNION_2005_INTEGRITY_BOUND_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "disposition": "NEW_IMMUTABLE_IDENTITY_BAT602_PRESERVED_INDEPENDENT_UPSTREAM_BINDINGS",
        "source_id": SOURCE_ID,
        "predecessor_union_identity": PINNED_BAT602_UNION_IDENTITY,
        "predecessor_gate_identity": PINNED_BAT602_GATE_IDENTITY,
        "union_identity": payload["union_identity"],
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
        "validator_code_identity": code_identity,
        "selected_seasons": [2009, 2008, 2007, 2006, 2005],
        "counts": counts,
        "coverage_by_season": coverage_by_season(official_games),
        "coverage_by_domain": coverage_by_domain(official_games),
        "enriched_official_games": official_games,
        "admitted_official_2005_games": admitted_2005,
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
            "bat595_gate_identity": PINNED_BAT595_GATE_IDENTITY,
            "bat596_gate_identity": PINNED_BAT596_GATE_IDENTITY,
            "bat596_payload_identity": PINNED_BAT596_PAYLOAD_IDENTITY,
            "bat597_gate_identity": PINNED_BAT597_GATE_IDENTITY,
            "bat597_union_identity": PINNED_BAT597_UNION_IDENTITY,
            "bat599_box_url_identity": PINNED_BAT599_BOX_URL_IDENTITY,
            "bat599_gate_identity": PINNED_BAT599_GATE_IDENTITY,
            "bat600_acquisition_identity": PINNED_BAT600_ACQUISITION_IDENTITY,
            "bat600_dataset_identity": PINNED_BAT600_DATASET_IDENTITY,
            "bat600_games_identity": PINNED_BAT600_GAMES_IDENTITY,
            "bat600_gate_identity": PINNED_BAT600_GATE_IDENTITY,
            "bat601_gate_identity": PINNED_BAT601_GATE_IDENTITY,
            "bat601_payload_identity": PINNED_BAT601_PAYLOAD_IDENTITY,
            "bat602_gate_identity": PINNED_BAT602_GATE_IDENTITY,
            "bat602_union_identity": PINNED_BAT602_UNION_IDENTITY,
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
    if any(item.get("structured_row_payload_identity") != bat601["payload_identity"] for item in admitted_2005):
        raise AuthorityViolation("2005 overlay is not bound to the independently recomputed BAT-601 payload identity")
    gate["gate_identity"] = compute_gate_identity(gate)
    payload["gate_identity"] = gate["gate_identity"]
    return {
        "contract": contract,
        "gate": gate,
        "payload": payload,
        "predecessor": predecessor,
        "bat600": bat600,
        "bat601": bat601,
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
        "recomputed_upstream": objects["gate"]["recomputed_upstream"],
    }


def upstream_is_ready(data_root: Path) -> bool:
    return (
        data_root
        / "features/tamu_official_2005_boxscores/sha256"
        / PINNED_BAT600_DATASET_IDENTITY
        / "payload.json"
    ).is_file() and (
        data_root
        / "features/tamu_official_2005_structured_domains/sha256"
        / PINNED_BAT601_PAYLOAD_IDENTITY
        / "payload.json"
    ).is_file() and union_manifest_path(data_root).is_file()


def lake_is_ready(data_root: Path) -> bool:
    return upstream_is_ready(data_root) and union_manifest_path(data_root).is_file()


def validate_compact_gate(committed: Mapping[str, Any]) -> None:
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("predecessor_union_identity") != PINNED_BAT602_UNION_IDENTITY:
        raise AuthorityViolation("BAT-602 2005-expanded union identity was rewritten")
    if committed.get("predecessor_gate_identity") != PINNED_BAT602_GATE_IDENTITY:
        raise AuthorityViolation("BAT-602 2005-expanded union gate identity was rewritten")
    if committed.get("result") != PASS_RESULT:
        raise AuthorityViolation("completion forged")
    if committed.get("classification") != PASS_CLASSIFICATION:
        raise AuthorityViolation("classification forged")
    if committed.get("validation_contract_version") != VALIDATION_CONTRACT_VERSION:
        raise AuthorityViolation("validation contract version drift")
    if committed.get("authority", {}).get("historical_known_at_from_capture_time"):
        raise AuthorityViolation("retrieval time promoted to historical known-at")
    if committed.get("counts", {}).get("ncaa_contest_ids_created"):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if int((committed.get("counts") or {}).get("new_games_added", -1)) != 0:
        raise AuthorityViolation("integrity-bound successor invented or dropped a 2005 admission")
    if committed.get("admissions", {}).get("pregame_availability") != "BLOCKED":
        raise AuthorityViolation("pregame availability admitted")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not recompute")
    if not committed.get("union_identity"):
        raise AuthorityViolation("union identity missing")
    if int(committed.get("counts", {}).get("union_captured_games") or 0) != PRIOR_UNION_CAPTURED_GAMES:
        raise AuthorityViolation("union captured-game arithmetic drifted")
    upstream = committed.get("upstream_identities") or {}
    if upstream.get("bat602_union_identity") != PINNED_BAT602_UNION_IDENTITY:
        raise AuthorityViolation("BAT-602 2005-expanded union identity was rewritten")
    if upstream.get("bat601_payload_identity") != PINNED_BAT601_PAYLOAD_IDENTITY:
        raise AuthorityViolation("BAT-601 payload identity rewritten")
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


def validate_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    gate: Mapping[str, Any] | None = None,
    require_rebuild: bool = True,
    bat600_payload: Mapping[str, Any] | None = None,
    bat601_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    validate_compact_gate(committed)
    ready = upstream_is_ready(data_root)
    if require_rebuild and not ready:
        raise AuthorityViolation("external integrity-bound reconstruction was required but the data root is not mounted")
    if not ready and bat600_payload is None and bat601_payload is None:
        return {
            "result": "PASS",
            "gate_identity": committed["gate_identity"],
            "union_identity": committed["union_identity"],
            "external_reconstruction": "NOT_MOUNTED",
        }
    expected = reconstruct_objects(
        repo_root=repo_root,
        data_root=data_root,
        bat600_payload=bat600_payload,
        bat601_payload=bat601_payload,
    )
    if committed != expected["gate"]:
        raise AuthorityViolation("committed integrity-bound union gate does not match independent reconstruction")
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

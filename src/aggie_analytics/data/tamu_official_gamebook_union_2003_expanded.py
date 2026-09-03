"""Immutable 2003-expanded official union from the BAT-608 integrity-complete successor."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import sha256_file, stable_hash
from aggie_analytics.data.tamu_official_2003_boxscores import (
    CONTRACT_RELATIVE as BAT610_CONTRACT_RELATIVE,
    GATE_RELATIVE as BAT610_GATE_RELATIVE,
    reconstruct_objects as reconstruct_bat610,
)
from aggie_analytics.data.tamu_official_2003_season_index import (
    reconstruct as reconstruct_bat609,
    validate_artifact as validate_bat609,
)
from aggie_analytics.data.tamu_official_2003_structured_domains import (
    CONTRACT_RELATIVE as BAT611_CONTRACT_RELATIVE,
    GATE_RELATIVE as BAT611_GATE_RELATIVE,
)
from aggie_analytics.data.tamu_official_gamebook_union import REGISTRY_SHA256
from aggie_analytics.data.tamu_official_gamebook_union_2005_expanded import (
    ADMITTED_STATUSES,
    COMPACT_FIELDS,
    PRESERVED_REJECTION_URLS,
)
from aggie_analytics.data.tamu_official_gamebook_union_2005_integrity_bound import (
    PINNED_BAT591_GATE_IDENTITY,
    PINNED_BAT591_PAYLOAD_IDENTITY,
    PINNED_BAT596_GATE_IDENTITY,
    PINNED_BAT596_PAYLOAD_IDENTITY,
    PINNED_BAT602_GATE_IDENTITY,
    PINNED_BAT602_UNION_IDENTITY,
    coverage_by_domain,
    coverage_by_season,
)
from aggie_analytics.data.tamu_official_gamebook_union_integrity_complete import (
    PINNED_BAT603_GATE_IDENTITY,
    PINNED_BAT603_UNION_IDENTITY,
    PINNED_BAT607_GATE_IDENTITY,
    PINNED_BAT607_UNION_IDENTITY,
    PINNED_GATE_IDENTITY as PINNED_BAT608_GATE_IDENTITY,
    PINNED_UNION_IDENTITY as PINNED_BAT608_UNION_IDENTITY,
    union_manifest_path as bat608_union_manifest_path,
    upstream_is_ready as bat608_upstream_is_ready,
    validate_artifact as validate_bat608,
)
from aggie_analytics.data.tamu_official_historical_boxscores import AuthorityViolation
from aggie_analytics.data.tamu_official_rich_structure import is_rich_structured, scoring_summary_present
from aggie_analytics.data.tamu_official_statcrew_preformatted import DOMAINS
from aggie_analytics.validation.artifact_binding import compute_identity


SCHEMA_VERSION = "aggie.data.tamu_official_gamebook_union_2003_expanded.v1"
VALIDATION_CONTRACT_VERSION = "aggie.data.tamu_official_gamebook_union_2003_expanded.v1"
CONTRACT_RELATIVE = "configs/tamu_official_gamebook_union_2003_expanded_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_gamebook_union_2003_expanded_gate.json"
MODULE_RELATIVE = "src/aggie_analytics/data/tamu_official_gamebook_union_2003_expanded.py"
CONTRACT_ID = "BAT-612-TAMU-OFFICIAL-GAMEBOOK-UNION-2003-EXPANDED-V1"
DECISION_UNIT = "POST-TASK-SRC014-2003-EXPANDED-ENRICHED-UNION-001"
JIRA_KEY = "BAT-612"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_OFFICIAL_GAMEBOOK_UNION_2003_EXPANDED_CANDIDATE_ONLY"
PASS_RESULT = "PASS_IMMUTABLE_BAT608_PRESERVED_OFFICIAL_2003_ADDED"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
OFFICIAL_2003_INDEX_URL = "https://files.12thman.com/history/football/years/2003.html"
OFFICIAL_2003_EXPECTED = 12
PRIOR_UNION_CAPTURED_GAMES = 273
PRIOR_UNION_RICH = 260
PRIOR_UNION_METADATA = 13
PRIOR_ENRICHED_OFFICIAL_GAMES = 70
PRIOR_SCORING = 70
PINNED_UNION_IDENTITY = "f6f330d4574cfcb819bd304496e9163e4997d12b0839670b65194bae2a680252"
PINNED_UNION_MANIFEST_FILE_SHA256 = "d10487971148b5c05445cee9a2dd582be779315c5085653f1fce8df5fcb85853"
PINNED_VALIDATOR_CODE_IDENTITY = "cc32667930047871cdf020c6a0fd4994a70909b5b3cc00b6d571952e99b77dd3"
UNION_MANIFEST_NAME = "union_manifest.json"
PINNED_BAT608_UNION_MANIFEST_FILE_SHA256 = "c1b6de383aecc24380679b531d2a8e7e5606b596e76f03117f528b870fee0f21"
PINNED_BAT609_GATE_IDENTITY = "1a2b16c74bcfc27ba0afc83611fd817d34aa6a2a71a326fd385721b779d9411e"
PINNED_BAT609_CAPTURE_IDENTITY = "253a1065192f2e4aa1fa366d967b5c37c0c9586d9b664a3bf0f16079c5105921"
PINNED_BAT609_BOX_URL_IDENTITY = "169ecef65490a5a07889ccd06816fda94db5215e6f1eacf6cb22204286800a99"
PINNED_BAT609_PAYLOAD_IDENTITY = "9f58c220fe44e8c75835d0dced6dc6571ee7592249eaa6fa209fa181f25fdfa6"
PINNED_BAT610_GATE_IDENTITY = "45329843f7b4683e18c231bbc5c835c7d0e488734d849ea18286d9b098291a13"
PINNED_BAT610_ACQUISITION_IDENTITY = "f5c0a2824381669501b7bccaeac18ced85f7c14b570d03e56ea4ebb1e4e08ee0"
PINNED_BAT610_DATASET_IDENTITY = "741f92a8b0d3c19fe7fd51033e9ddfb797052a9da4e63a2115839a4617e2c0c5"
PINNED_BAT610_GAMES_IDENTITY = "17a9daed972a0fa91e554b33adeaf5027aefa206188fec949a4450e2f8971772"
PINNED_BAT611_GATE_IDENTITY = "4d22bbb416115c10a490d703b90cf70d8cdb67c9163c23b0f8cfb69212250284"
PINNED_BAT611_PAYLOAD_IDENTITY = "ad3065275042edc8c8f8770e73b237d243811d29e528481d1f88d918d529a040"
PINNED_BAT606_GATE_IDENTITY = "1b3fb5536ff535b23a910a462857b0c7c1e29f66b3d937e0b1de90e85ac179b6"
PINNED_BAT606_PAYLOAD_IDENTITY = "80ba101dc4699c32eae44e963be627ac1edff00a09e2dd459780f11f6930122c"
PINNED_BAT605_GATE_IDENTITY = "c570a33661bf194475693f56b2d21baf9a38e67c5ae568f5a531e374356b5c70"
PINNED_BAT605_ACQUISITION_IDENTITY = "7fa30d842696f0e73cc23f53daff1638326d58ce5636b354741eca9cf4c21ad9"
PINNED_BAT605_DATASET_IDENTITY = "6670084e2578fa0e0339668a8b4f47eeaba5c1368d91043203ecfeda38f6c96b"
PINNED_BAT605_GAMES_IDENTITY = "6f7f6505f8e863daeb8d8b7f662fb0ce455a7cb388379815d7d33734cd97ac9b"
PINNED_BAT604_GATE_IDENTITY = "3169f6b14e9f2e78e5af2c3dfa33419d80b37c791968fa39e0ddcf91f3643836"
OVERLAY_DOMAINS = DOMAINS
NAME_ONLY_STATUSES = frozenset(
    {
        "MATCHED_OPPONENT_NAME_ONLY",
        "NAME_ONLY",
        "OPPONENT_NAME_ONLY",
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
        / "features/tamu_official_gamebook_union_2003_expanded/sha256"
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
        raise AuthorityViolation("external 2003-expanded union payload does not match reconstruction")
    serialized = json.dumps(expected_payload, indent=2, sort_keys=True) + "\n"
    if path.read_text(encoding="utf-8-sig") != serialized:
        raise AuthorityViolation("external 2003-expanded union payload serialization does not match reconstruction")
    digest = sha256_file(path)
    if PINNED_UNION_IDENTITY and union_identity == PINNED_UNION_IDENTITY and digest != PINNED_UNION_MANIFEST_FILE_SHA256:
        raise AuthorityViolation("BAT-612 union manifest file SHA-256 drifted")
    return digest


def recompute_bat610_identities(payload: Mapping[str, Any]) -> dict[str, str]:
    games = list(payload.get("games") or [])
    captures = list(payload.get("captures") or [])
    conflicts = list(payload.get("conflicts") or [])
    return {
        "acquisition_identity": stable_hash(captures),
        "games_identity": stable_hash(games),
        "dataset_identity": stable_hash({"games": games, "captures": captures, "conflicts": conflicts}),
    }


def recompute_bat611_payload_identity(payload: Mapping[str, Any]) -> str:
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
        "bat602_union_rewritten": False,
        "bat603_union_rewritten": False,
        "bat607_union_rewritten": False,
        "bat608_union_rewritten": False,
        "bat610_payload_rewritten": False,
        "bat611_payload_rewritten": False,
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
        "bat_429_reevaluation": "POST-SUBTASK-063_066_069_NOT_INDEPENDENTLY_DONE_VERIFIED",
        "bat_523": "IN_PROGRESS",
        "bat_602_union": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_603_union": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_607_union": "PRESERVED_IMMUTABLE_NOT_REWRITTEN",
        "bat_608_union": "CONSUMED_AS_INTEGRITY_COMPLETE_PREDECESSOR_ONLY",
        "bat_609_index": "CONSUMED_OFFICIAL_INDEX_URLS_ONLY",
        "bat_610_boxscores": "INDEPENDENTLY_RECOMPUTED_EXTERNAL_PAYLOAD",
        "bat_611_domains": "INDEPENDENTLY_RECOMPUTED_EXTERNAL_ROW_PAYLOAD",
        "gap_005": "OPEN",
        "historical_known_at": "UNKNOWN_RETRIEVAL_TIME_ONLY",
        "ncaa_contest_identity": "NOT_CREATED",
        "pregame_availability": "BLOCKED",
        "protected_lane": PROTECTED_LANE,
        "source_authority": "SRC-014_OFFICIAL_SCHOOL_EVIDENCE",
        "union_admission": "CANDIDATE_ONLY",
        "wmt_payload": "PRESERVED_IMMUTABLE",
    }


def compact_official_2003(game: Mapping[str, Any], official_index_url: str) -> dict[str, Any]:
    parent = game.get("parent_url")
    if parent in {None, ""}:
        raise AuthorityViolation("parent_url missing; hardcoded fallback is forbidden")
    if parent != official_index_url:
        raise AuthorityViolation("parent_url does not match BAT-609 official index URL")
    row = {key: game.get(key) for key in COMPACT_FIELDS}
    row["source_season"] = int(game.get("source_season") or game.get("football_season") or 0)
    row["football_season"] = int(game.get("football_season") or game.get("source_season") or 0)
    row["official_index_url"] = str(parent)
    row["parent_url"] = str(parent)
    row["ncaa_contest_id"] = None
    row["canonical_game_id"] = None
    row["availability_claim"] = False
    row["availability"] = "NOT_ESTABLISHED"
    row["historical_publication_time"] = None
    if row["source_season"] != 2003 or row["football_season"] != 2003:
        raise AuthorityViolation("BAT-610 payload contained a non-2003 game")
    return row


def overlay_2003(
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
        raise AuthorityViolation(f"BAT-611 raw hash does not match admitted 2003 game {row.get('url')}")
    if str(domains.get("url") or "") != str(row.get("url") or ""):
        raise AuthorityViolation(f"BAT-611 URL does not match admitted 2003 game {row.get('url')}")
    for domain in OVERLAY_DOMAINS:
        if (domains.get("domain_coverage") or {}).get(domain) == "PRESENT":
            if int(serialized_row_counts.get(domain) or 0) <= 0:
                raise AuthorityViolation(f"PRESENT coverage without serialized {domain} rows")
            coverage[domain] = "PRESENT"
    row["domain_coverage"] = coverage
    row["overlay_applied"] = True
    row["overlay_source"] = "BAT-611-2003-STRUCTURED-DOMAINS-INDEPENDENTLY-VALIDATED"
    row["structured_row_payload_identity"] = payload_identity
    row["structured_row_counts"] = dict(serialized_row_counts)
    row["rich_structured"] = is_rich_structured(row)
    row["ncaa_contest_id"] = None
    row["canonical_game_id"] = None
    row["availability_claim"] = False
    row["availability"] = "NOT_ESTABLISHED"
    row["historical_publication_time"] = None
    return row


def _bat610_payload_path(data_root: Path, repo_root: Path) -> Path:
    contract = load_json(repo_root / BAT610_CONTRACT_RELATIVE)
    return data_root / contract["payloads"]["normalized_root"] / PINNED_BAT610_DATASET_IDENTITY / "payload.json"


def _bat611_payload_path(data_root: Path, repo_root: Path) -> Path:
    contract = load_json(repo_root / BAT611_CONTRACT_RELATIVE)
    return data_root / contract["payloads"]["enriched_root"] / PINNED_BAT611_PAYLOAD_IDENTITY / "payload.json"


def validate_bat610_external_payload(
    *,
    repo_root: Path,
    data_root: Path,
    payload: Mapping[str, Any] | None = None,
    allowed_urls: list[str] | None = None,
    official_index_url: str = OFFICIAL_2003_INDEX_URL,
) -> dict[str, Any]:
    path = _bat610_payload_path(data_root, repo_root)
    if payload is None:
        if not path.is_file():
            raise AuthorityViolation("external BAT-610 payload is not mounted")
        payload = load_json(path)
    declared = {
        "acquisition_identity": str(payload.get("acquisition_identity") or ""),
        "games_identity": str(payload.get("games_identity") or ""),
        "dataset_identity": str(payload.get("dataset_identity") or ""),
    }
    recomputed = recompute_bat610_identities(payload)
    if recomputed != declared:
        raise AuthorityViolation("BAT-610 declared identities do not match recomputed payload content")
    committed = load_json(repo_root / BAT610_GATE_RELATIVE)
    if committed.get("gate_identity") != PINNED_BAT610_GATE_IDENTITY:
        raise AuthorityViolation("BAT-610 2003 acquisition identity rewritten")
    for key, value in recomputed.items():
        if committed.get(key) != value:
            raise AuthorityViolation(f"recomputed BAT-610 {key} does not match the committed gate")
        if value != {
            "acquisition_identity": PINNED_BAT610_ACQUISITION_IDENTITY,
            "games_identity": PINNED_BAT610_GAMES_IDENTITY,
            "dataset_identity": PINNED_BAT610_DATASET_IDENTITY,
        }[key]:
            raise AuthorityViolation(f"recomputed BAT-610 {key} does not match the pinned identity")
    if allowed_urls is None:
        raise AuthorityViolation("BAT-609 official 2003 box URLs were not independently reconstructed")
    if len(allowed_urls) != OFFICIAL_2003_EXPECTED:
        raise AuthorityViolation("BAT-609 did not emit 12 official 2003 box URLs")
    if official_index_url != OFFICIAL_2003_INDEX_URL:
        raise AuthorityViolation("BAT-609 official index URL drifted")
    captures = {str(item.get("url") or ""): dict(item) for item in (payload.get("captures") or [])}
    games = list(payload.get("games") or [])
    if len(games) != OFFICIAL_2003_EXPECTED:
        raise AuthorityViolation(f"expected 12 official 2003 games, found {len(games)}")
    allowed_set = frozenset(allowed_urls)
    if {str(item.get("url") or "") for item in games} != allowed_set:
        raise AuthorityViolation("BAT-610 games are not exactly the BAT-609 official index URLs")
    if set(captures) != allowed_set:
        raise AuthorityViolation("BAT-610 capture membership is not exactly the BAT-609 official index URLs")
    rebuilt: list[dict[str, Any]] = []
    for item in games:
        url = str(item.get("url") or "")
        capture = captures.get(url)
        if capture is None:
            raise AuthorityViolation(f"BAT-610 capture missing official 2003 URL: {url}")
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
        if str(capture.get("url") or "") != url:
            raise AuthorityViolation(f"capture URL does not match game URL {url}")
        compact = compact_official_2003(item, official_index_url)
        status = str(compact.get("canonical_game_match_status") or "")
        if status in NAME_ONLY_STATUSES:
            raise AuthorityViolation("opponent name alone is not admission")
        if status not in ADMITTED_STATUSES:
            raise AuthorityViolation(f"2003 game lacks official index+URL+SHA admission: {url}")
        rebuilt.append(compact)
    reconstructed = reconstruct_bat610(repo_root=repo_root, data_root=data_root)
    reconstructed_identities = {
        "acquisition_identity": reconstructed["payload"]["acquisition_identity"],
        "games_identity": reconstructed["payload"]["games_identity"],
        "dataset_identity": reconstructed["payload"]["dataset_identity"],
    }
    if reconstructed_identities != recomputed:
        raise AuthorityViolation("BAT-610 payload identities do not match independent raw reconstruction")
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


def validate_bat611_external_payload(
    *,
    repo_root: Path,
    data_root: Path,
    payload: Mapping[str, Any] | None = None,
    compact_games: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    path = _bat611_payload_path(data_root, repo_root)
    if payload is None:
        if not path.is_file():
            raise AuthorityViolation("external BAT-611 payload is not mounted")
        payload = load_json(path)
    declared = str(payload.get("payload_identity") or "")
    recomputed = recompute_bat611_payload_identity(payload)
    if recomputed != declared:
        raise AuthorityViolation("BAT-611 declared payload identity does not match recomputed payload content")
    committed = load_json(repo_root / BAT611_GATE_RELATIVE)
    if committed.get("gate_identity") != PINNED_BAT611_GATE_IDENTITY:
        raise AuthorityViolation("BAT-611 2003 structured-domain identity rewritten")
    if committed.get("payload_identity") != recomputed or recomputed != PINNED_BAT611_PAYLOAD_IDENTITY:
        raise AuthorityViolation("recomputed BAT-611 payload identity does not match the pinned identity")
    if payload.get("availability_claim") or payload.get("availability") not in {None, "NOT_ESTABLISHED"}:
        raise AuthorityViolation("pregame availability claimed")
    external_games = list(payload.get("games") or [])
    row_groups = list(payload.get("rows") or [])
    if len(external_games) != OFFICIAL_2003_EXPECTED or len(row_groups) != OFFICIAL_2003_EXPECTED:
        raise AuthorityViolation("BAT-611 external payload game/row membership drifted")
    compact = compact_games if compact_games is not None else list(committed.get("games") or [])
    compact_by_url = _index_by_url(compact, "BAT-611-gate")
    validated: dict[str, dict[str, Any]] = {}
    for game, rows in zip(external_games, row_groups):
        url = str(game.get("url") or "")
        gate_game = compact_by_url.get(url)
        if gate_game is None:
            raise AuthorityViolation(f"BAT-611 gate is missing external URL {url}")
        serialized_counts = _serialized_row_counts(list(rows))
        declared_counts = {domain: len(game.get(domain) or []) for domain in OVERLAY_DOMAINS}
        if serialized_counts != declared_counts or serialized_counts != dict(gate_game.get("row_counts") or {}):
            raise AuthorityViolation(f"BAT-611 serialized row counts drifted for {url}")
        if str(game.get("source_sha256") or "") != str(gate_game.get("source_sha256") or ""):
            raise AuthorityViolation(f"BAT-611 source SHA drifted for {url}")
        if int(game.get("source_season") or 0) != 2003:
            raise AuthorityViolation(f"BAT-611 source season drifted for {url}")
        game_coverage = {domain: (game.get("domain_coverage") or {}).get(domain) for domain in OVERLAY_DOMAINS}
        for domain in OVERLAY_DOMAINS:
            if game_coverage.get(domain) == "PRESENT" and serialized_counts[domain] <= 0:
                raise AuthorityViolation(f"PRESENT coverage with zero serialized {domain} rows")
        for row in rows:
            if row.get("availability") != "NOT_ESTABLISHED" or row.get("availability_claim"):
                raise AuthorityViolation("participation or membership promoted to availability")
            if str(row.get("source_url") or "") != url:
                raise AuthorityViolation(f"BAT-611 row URL drifted for {url}")
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
        raise AuthorityViolation("BAT-611 external payload URLs do not match the compact gate")
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
    bat610_payload: Mapping[str, Any] | None = None,
    bat611_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    registry = repo_root / "governance/PROTECTED_SPLIT_REGISTRY.csv"
    digest = hashlib.sha256(registry.read_bytes()).hexdigest()
    if digest != REGISTRY_SHA256:
        raise AuthorityViolation("protected-split registry identity drift")
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise AuthorityViolation("2003-expanded union contract identity drift")
    predecessor = load_json(repo_root / "artifacts/data_lake/tamu_official_gamebook_union_integrity_complete_gate.json")
    if predecessor.get("union_identity") != PINNED_BAT608_UNION_IDENTITY:
        raise AuthorityViolation("BAT-608 integrity-complete union identity was rewritten")
    if predecessor.get("gate_identity") != PINNED_BAT608_GATE_IDENTITY:
        raise AuthorityViolation("BAT-608 integrity-complete union gate identity was rewritten")
    if predecessor.get("predecessor_union_identity") != PINNED_BAT607_UNION_IDENTITY:
        raise AuthorityViolation("BAT-607 2004-expanded union identity was rewritten")
    if predecessor.get("predecessor_gate_identity") != PINNED_BAT607_GATE_IDENTITY:
        raise AuthorityViolation("BAT-607 2004-expanded union gate identity was rewritten")
    if int(predecessor.get("counts", {}).get("union_captured_games") or 0) != PRIOR_UNION_CAPTURED_GAMES:
        raise AuthorityViolation("BAT-608 captured-game count drifted")
    if len(predecessor.get("enriched_official_games") or []) != PRIOR_ENRICHED_OFFICIAL_GAMES:
        raise AuthorityViolation("BAT-608 official-school membership drifted")
    validate_bat608(repo_root=repo_root, data_root=data_root, require_rebuild=True)
    bat608_manifest = bat608_union_manifest_path(data_root)
    if not bat608_manifest.is_file():
        raise AuthorityViolation("authoritative external union manifest is missing")
    bat608_manifest_sha = sha256_file(bat608_manifest)
    if bat608_manifest_sha != PINNED_BAT608_UNION_MANIFEST_FILE_SHA256:
        raise AuthorityViolation("BAT-608 union manifest file SHA-256 drifted")
    validate_bat609(repo_root=repo_root, data_root=data_root, require_rebuild=True)
    bat609 = reconstruct_bat609(repo_root=repo_root, data_root=data_root)
    if bat609["gate"]["gate_identity"] != PINNED_BAT609_GATE_IDENTITY:
        raise AuthorityViolation("BAT-609 2003 index identity rewritten")
    if bat609["gate"]["box_url_identity"] != PINNED_BAT609_BOX_URL_IDENTITY:
        raise AuthorityViolation("BAT-609 box-URL identity rewritten")
    if bat609["gate"]["official_index_url"] != OFFICIAL_2003_INDEX_URL:
        raise AuthorityViolation("BAT-609 official index URL drifted")
    allowed = [str(url) for url in (bat609["gate"].get("box_score_urls") or [])]
    bat610 = validate_bat610_external_payload(
        repo_root=repo_root,
        data_root=data_root,
        payload=bat610_payload,
        allowed_urls=allowed,
        official_index_url=str(bat609["gate"]["official_index_url"]),
    )
    bat611 = validate_bat611_external_payload(repo_root=repo_root, data_root=data_root, payload=bat611_payload)
    prior_games = [json.loads(json.dumps(item)) for item in (predecessor.get("enriched_official_games") or [])]
    rejected = [json.loads(json.dumps(item)) for item in (predecessor.get("preserved_rejections") or [])]
    rejected_urls = {str(item.get("url") or "") for item in rejected}
    if rejected_urls != PRESERVED_REJECTION_URLS:
        raise AuthorityViolation("the four preserved rejected games drifted")
    prior_by_url = _index_by_url(prior_games, "BAT-608")
    admitted_2003: list[dict[str, Any]] = []
    for compact in bat610["games"]:
        url = str(compact["url"])
        if url in rejected_urls:
            raise AuthorityViolation(f"rejected game was presented for 2003 admission: {url}")
        if url in prior_by_url:
            raise AuthorityViolation(f"duplicate union membership for {url}")
        if url not in bat611["games"]:
            raise AuthorityViolation(f"BAT-611 domains missing for official 2003 URL {url}")
        admitted_2003.append(
            overlay_2003(
                compact,
                bat611["games"][url],
                bat611["payload_identity"],
                prior_rich=bool(is_rich_structured(compact)),
                serialized_row_counts=bat611["games"][url]["row_counts"],
            )
        )
    admitted_2003.sort(key=lambda item: (item["football_season"], item["calendar_date"], item["url"]))
    if len(admitted_2003) != OFFICIAL_2003_EXPECTED:
        raise AuthorityViolation("official 2003 admission count drifted")
    official_games = prior_games + admitted_2003
    if len(official_games) != PRIOR_ENRICHED_OFFICIAL_GAMES + OFFICIAL_2003_EXPECTED:
        raise AuthorityViolation("2003-expanded official-school membership drifted")
    if len({item["url"] for item in official_games}) != len(official_games):
        raise AuthorityViolation("duplicate URLs in the expanded union")
    became_rich = sum(1 for item in admitted_2003 if item["rich_structured"] and not item["prior_rich_structured"])
    new_rich = sum(1 for item in admitted_2003 if item["rich_structured"])
    scoring = sum(1 for item in official_games if scoring_summary_present(item))
    predecessor_counts = dict(predecessor.get("counts") or {})
    date_conflicts = int(predecessor_counts.get("date_conflicts") or 0) + sum(
        1 for item in admitted_2003 if item.get("conflict_status") not in {None, "NONE"} and "DATE" in str(item.get("conflict_status") or "")
    )
    counts = {
        **predecessor_counts,
        "predecessor_273_union_games_preserved": PRIOR_UNION_CAPTURED_GAMES,
        "official_2003_target_games": OFFICIAL_2003_EXPECTED,
        "official_2003_added": len(admitted_2003),
        "official_2003_admitted": len(admitted_2003),
        "official_2003_rejected": 0,
        "new_games_added": len(admitted_2003),
        "overlays_applied_this_phase": len(admitted_2003),
        "overlays_became_rich_this_phase": became_rich,
        "union_target_games": PRIOR_UNION_CAPTURED_GAMES + len(admitted_2003),
        "union_captured_games": PRIOR_UNION_CAPTURED_GAMES + len(admitted_2003),
        "rich_structured_games": PRIOR_UNION_RICH + new_rich,
        "metadata_only_games": PRIOR_UNION_METADATA + len(admitted_2003) - new_rich,
        "scoring_summary_present_games": scoring,
        "matched_strong_tuple": int(predecessor_counts.get("matched_strong_tuple") or 0)
        + sum(
            1
            for item in admitted_2003
            if item.get("canonical_game_match_status") == "MATCHED_OFFICIAL_SEASON_INDEX_STRONG_TUPLE"
        ),
        "date_conflicts": date_conflicts,
        "ncaa_contest_ids_created": 0,
        "duplicates_rejected": 0,
        "unmatched_rejected": 4,
    }
    if counts["union_captured_games"] != counts["rich_structured_games"] + counts["metadata_only_games"]:
        raise AuthorityViolation("2003-expanded rich/metadata arithmetic drifted")
    if scoring != PRIOR_SCORING + sum(1 for item in admitted_2003 if scoring_summary_present(item)):
        raise AuthorityViolation("2003-expanded scoring-summary count drifted")
    conflicts = [json.loads(json.dumps(item)) for item in (predecessor.get("conflicts") or [])]
    conflicts.extend(bat610["conflicts"])
    conflicts.extend(
        {
            "url": item["url"],
            "opponent_candidate": item.get("opponent_candidate"),
            "calendar_date": item.get("calendar_date"),
            "index_date_candidate": item.get("index_date_candidate"),
            "conflict_status": item.get("conflict_status"),
            "match_status": item.get("canonical_game_match_status"),
        }
        for item in admitted_2003
        if item.get("conflict_status") not in {None, "NONE"}
    )
    code_identity = compute_code_identity(repo_root)
    recomputed_upstream = {
        "bat608_union_identity": PINNED_BAT608_UNION_IDENTITY,
        "bat608_gate_identity": PINNED_BAT608_GATE_IDENTITY,
        "bat608_union_manifest_file_sha256": bat608_manifest_sha,
        "bat610_acquisition_identity": bat610["identities"]["acquisition_identity"],
        "bat610_dataset_identity": bat610["identities"]["dataset_identity"],
        "bat610_games_identity": bat610["identities"]["games_identity"],
        "bat610_payload_file_sha256": bat610["file_sha256"],
        "bat611_payload_identity": bat611["payload_identity"],
        "bat611_payload_file_sha256": bat611["file_sha256"],
        "validator_code_identity": code_identity,
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "predecessor_union_identity": PINNED_BAT608_UNION_IDENTITY,
        "predecessor_gate_identity": PINNED_BAT608_GATE_IDENTITY,
        "bat611_payload_identity": bat611["payload_identity"],
        "enriched_official_games": official_games,
        "admitted_official_2003_games": admitted_2003,
        "preserved_rejections": rejected,
        "counts": counts,
        "conflicts": conflicts,
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "recomputed_upstream": recomputed_upstream,
    }
    payload["union_identity"] = stable_hash(
        {
            "predecessor_union_identity": PINNED_BAT608_UNION_IDENTITY,
            "predecessor_gate_identity": PINNED_BAT608_GATE_IDENTITY,
            "recomputed_bat610_identities": bat610["identities"],
            "recomputed_bat611_payload_identity": bat611["payload_identity"],
            "upstream_payload_file_hashes": {
                "bat608_union_manifest": bat608_manifest_sha,
                "bat610": bat610["file_sha256"],
                "bat611": bat611["file_sha256"],
            },
            "validator_code_identity": code_identity,
            "validation_contract_version": VALIDATION_CONTRACT_VERSION,
            "admitted_official_2003_games": admitted_2003,
            "preserved_rejections": rejected,
            "counts": counts,
        }
    )
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_GAMEBOOK_UNION_2003_EXPANDED_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "disposition": "NEW_IMMUTABLE_IDENTITY_BAT608_PRESERVED_OFFICIAL_2003_ADDED",
        "source_id": SOURCE_ID,
        "predecessor_union_identity": PINNED_BAT608_UNION_IDENTITY,
        "predecessor_gate_identity": PINNED_BAT608_GATE_IDENTITY,
        "union_identity": payload["union_identity"],
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
        "validator_code_identity": code_identity,
        "selected_seasons": [2009, 2008, 2007, 2006, 2005, 2004, 2003],
        "counts": counts,
        "coverage_by_season": coverage_by_season(official_games),
        "coverage_by_domain": coverage_by_domain(official_games),
        "enriched_official_games": official_games,
        "admitted_official_2003_games": admitted_2003,
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
            "bat605_acquisition_identity": PINNED_BAT605_ACQUISITION_IDENTITY,
            "bat605_dataset_identity": PINNED_BAT605_DATASET_IDENTITY,
            "bat605_games_identity": PINNED_BAT605_GAMES_IDENTITY,
            "bat605_gate_identity": PINNED_BAT605_GATE_IDENTITY,
            "bat606_gate_identity": PINNED_BAT606_GATE_IDENTITY,
            "bat606_payload_identity": PINNED_BAT606_PAYLOAD_IDENTITY,
            "bat604_gate_identity": PINNED_BAT604_GATE_IDENTITY,
            "bat607_gate_identity": PINNED_BAT607_GATE_IDENTITY,
            "bat607_union_identity": PINNED_BAT607_UNION_IDENTITY,
            "bat608_gate_identity": PINNED_BAT608_GATE_IDENTITY,
            "bat608_union_identity": PINNED_BAT608_UNION_IDENTITY,
            "bat608_union_manifest_file_sha256": PINNED_BAT608_UNION_MANIFEST_FILE_SHA256,
            "bat609_box_url_identity": PINNED_BAT609_BOX_URL_IDENTITY,
            "bat609_capture_identity": PINNED_BAT609_CAPTURE_IDENTITY,
            "bat609_gate_identity": PINNED_BAT609_GATE_IDENTITY,
            "bat609_payload_identity": PINNED_BAT609_PAYLOAD_IDENTITY,
            "bat610_acquisition_identity": PINNED_BAT610_ACQUISITION_IDENTITY,
            "bat610_dataset_identity": PINNED_BAT610_DATASET_IDENTITY,
            "bat610_games_identity": PINNED_BAT610_GAMES_IDENTITY,
            "bat610_gate_identity": PINNED_BAT610_GATE_IDENTITY,
            "bat611_gate_identity": PINNED_BAT611_GATE_IDENTITY,
            "bat611_payload_identity": PINNED_BAT611_PAYLOAD_IDENTITY,
            "protected_split_registry_sha256": REGISTRY_SHA256,
        },
    }
    if counts["ncaa_contest_ids_created"] or any(item.get("ncaa_contest_id") for item in official_games):
        raise AuthorityViolation("NCAA contest IDs fabricated")
    if any(item.get("availability_claim") for item in official_games):
        raise AuthorityViolation("pregame availability claimed")
    if any(item.get("historical_publication_time") is not None for item in official_games):
        raise AuthorityViolation("retrieval time promoted to historical known-at")
    if any(item.get("structured_row_payload_identity") != bat611["payload_identity"] for item in admitted_2003):
        raise AuthorityViolation("2003 overlay is not bound to the independently recomputed BAT-611 payload identity")
    gate["gate_identity"] = compute_gate_identity(gate)
    payload["gate_identity"] = gate["gate_identity"]
    return {
        "contract": contract,
        "gate": gate,
        "payload": payload,
        "predecessor": predecessor,
        "bat609": bat609,
        "bat610": bat610,
        "bat611": bat611,
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
        bat608_upstream_is_ready(data_root)
        and bat608_union_manifest_path(data_root).is_file()
        and (
            data_root
            / "features/tamu_official_2003_boxscores/sha256"
            / PINNED_BAT610_DATASET_IDENTITY
            / "payload.json"
        ).is_file()
        and (
            data_root
            / "features/tamu_official_2003_structured_domains/sha256"
            / PINNED_BAT611_PAYLOAD_IDENTITY
            / "payload.json"
        ).is_file()
    )


def lake_is_ready(data_root: Path) -> bool:
    return upstream_is_ready(data_root) and bool(PINNED_UNION_IDENTITY) and union_manifest_path(data_root).is_file()


def validate_compact_gate(committed: Mapping[str, Any]) -> None:
    if committed.get("protected_lane") != PROTECTED_LANE:
        raise AuthorityViolation("protected lane opened")
    if committed.get("predecessor_union_identity") != PINNED_BAT608_UNION_IDENTITY:
        raise AuthorityViolation("BAT-608 integrity-complete union identity was rewritten")
    if committed.get("predecessor_gate_identity") != PINNED_BAT608_GATE_IDENTITY:
        raise AuthorityViolation("BAT-608 integrity-complete union gate identity was rewritten")
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
    if int((committed.get("counts") or {}).get("new_games_added", -1)) != OFFICIAL_2003_EXPECTED:
        raise AuthorityViolation("2003 admission count drifted")
    if committed.get("admissions", {}).get("pregame_availability") != "BLOCKED":
        raise AuthorityViolation("pregame availability admitted")
    if committed.get("admissions", {}).get("bat_429") != "BLOCKED_UNSATISFIED_HARD_DEPENDENCIES":
        raise AuthorityViolation("BAT-429 advanced without independently DONE/VERIFIED hard dependencies")
    if committed.get("gate_identity") != compute_gate_identity(committed):
        raise AuthorityViolation("gate identity does not recompute")
    if int(committed.get("counts", {}).get("union_captured_games") or 0) != PRIOR_UNION_CAPTURED_GAMES + OFFICIAL_2003_EXPECTED:
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
    if upstream.get("bat608_union_identity") != PINNED_BAT608_UNION_IDENTITY:
        raise AuthorityViolation("BAT-608 integrity-complete union identity was rewritten")
    if upstream.get("bat607_union_identity") != PINNED_BAT607_UNION_IDENTITY:
        raise AuthorityViolation("BAT-607 2004-expanded union identity was rewritten")
    if upstream.get("bat603_union_identity") != PINNED_BAT603_UNION_IDENTITY:
        raise AuthorityViolation("BAT-603 integrity-bound union identity was rewritten")
    if upstream.get("bat602_union_identity") != PINNED_BAT602_UNION_IDENTITY:
        raise AuthorityViolation("BAT-602 2005-expanded union identity was rewritten")


def validate_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    gate: Mapping[str, Any] | None = None,
    require_rebuild: bool = True,
    bat610_payload: Mapping[str, Any] | None = None,
    bat611_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    validate_compact_gate(committed)
    ready = upstream_is_ready(data_root)
    if require_rebuild and not ready:
        raise AuthorityViolation("external 2003-expanded reconstruction was required but the data root is not mounted")
    if not ready and bat610_payload is None and bat611_payload is None:
        return {
            "result": "PASS",
            "gate_identity": committed["gate_identity"],
            "union_identity": committed["union_identity"],
            "external_reconstruction": "NOT_MOUNTED",
        }
    expected = reconstruct_objects(
        repo_root=repo_root,
        data_root=data_root,
        bat610_payload=bat610_payload,
        bat611_payload=bat611_payload,
    )
    if committed != expected["gate"]:
        raise AuthorityViolation("committed 2003-expanded union gate does not match independent reconstruction")
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

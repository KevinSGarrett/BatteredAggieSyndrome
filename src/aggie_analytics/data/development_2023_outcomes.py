from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# 2023-only development outcome labels from the existing SRC-002 capture.
# Labels are post-completion observations. They are never pregame features and
# grant no protected, champion, or promotion authority.

SCHEMA_VERSION = "aggie.data.development_2023_outcomes.v3"
CONTRACT_RELATIVE = "configs/development_2023_outcome_identity_contract.json"
CONTRACT_ID = "BAT-565-2023-DEVELOPMENT-OUTCOME-IDENTITY-V3"
GATE_RELATIVE = "artifacts/pit/development_2023_outcome_gate.json"
EVIDENCE_RELATIVE = "artifacts/jira_evidence/POST-TASK-2023-DEVELOPMENT-OUTCOMES-001.json"
HISTORICAL_KNOWN_AT_STATE = (
    "CAPTURE_TIME_KNOWN; FINAL_WHISTLE_AND_SOURCE_PUBLICATION_TIMES_UNKNOWN"
)
LABEL_AVAILABILITY_POLICY = (
    "CONSERVATIVE_POST_START_ELIGIBILITY_BOUND_NOT_OBSERVED_FINAL_WHISTLE"
)
OUTCOME_EFFECTIVE_UNAVAILABLE_REASON = (
    "UNAVAILABLE_NO_VERIFIED_COMPLETION_OR_PUBLICATION_TIMESTAMP"
)
SUPERSEDED_KICKOFF_IDENTITY = (
    "902f3558a466a3cc26def6f24285032c2d012c0adeaf5bf5a2cfb47101a99cb2"
)
SUPERSEDED_CYCLE6_IDENTITY = (
    "bdcacebeaccd3ba69e2445420664749b961f5a3a233a3d66b355e291fa9c6bb8"
)
NON_FINAL_TOKENS = (
    "canceled",
    "cancelled",
    "incomplete",
    "suspended",
    "postponed",
    "non-final",
    "non_final",
)
REQUIRED_LABEL_SEMANTICS = {
    "source_completed_final_required": True,
    "verified_completion_timestamp_available": False,
    "verified_historical_publication_timestamp_available": False,
    "historical_label_availability_proven": False,
    "label_eligibility_basis": "PRECOMMITTED_RETROSPECTIVE_POLICY_BOUND",
    "policy_boundary_not_observed_timestamp": True,
    "outcome_effective_at_utc": None,
    "outcome_observed_at_utc": "2026-08-09T16:57:56Z",
}
PROTECTED_SEASONS = frozenset({2024, 2025})
PASS_RESULT = "PASS_DEVELOPMENT_ONLY_2023_LABELS"
REQUIRED_SOURCE_FIELDS = (
    "id",
    "season",
    "seasonType",
    "week",
    "startDate",
    "completed",
    "neutralSite",
    "homeId",
    "awayId",
    "homePoints",
    "awayPoints",
)
ACCEPTED_GAME_FIELDS = (
    "observation_id",
    "source_game_id",
    "canonical_game_id",
    "season",
    "season_type",
    "week",
    "start_time_utc",
    "home_team_id",
    "away_team_id",
    "neutral_site",
    "home_points",
    "away_points",
    "margin",
    "outcome_result",
    "completed",
    "outcome_observed_at_utc",
    "outcome_effective_at_utc",
    "outcome_effective_unavailable_reason",
    "label_available_after_utc",
    "conservative_eligibility_bound_utc",
    "label_availability_policy",
    "source_capture_id",
    "source_payload_sha256",
    "source_record_evidence_sha256",
    "canonical_mapping_record_sha256",
    "canonical_registry_sha256",
    "ncaa_status",
    "ncaa_contest_id",
    "spine_score_match",
    "historical_known_at_state",
    "not_a_pregame_feature",
    "development_label_only",
    "protected_eligible",
    "protected_performance_authority",
    "row_lineage_sha256",
)
TEAM_OBSERVATION_FIELDS = (
    "observation_id",
    "parent_observation_id",
    "canonical_game_id",
    "source_game_id",
    "season",
    "season_type",
    "week",
    "start_time_utc",
    "team_id",
    "opponent_id",
    "site",
    "points_for",
    "points_against",
    "margin",
    "result",
    "outcome_observed_at_utc",
    "outcome_effective_at_utc",
    "outcome_effective_unavailable_reason",
    "label_available_after_utc",
    "conservative_eligibility_bound_utc",
    "label_availability_policy",
    "source_capture_id",
    "source_payload_sha256",
    "source_record_evidence_sha256",
    "not_a_pregame_feature",
    "development_label_only",
    "row_lineage_sha256",
)
QUARANTINE_FIELDS = (
    "source_game_id",
    "season",
    "reason_code",
    "detail",
    "source_record_evidence_sha256",
)
NCAA_FIELDS = (
    "canonical_game_id",
    "source_game_id",
    "ncaa_status",
    "ncaa_contest_id",
    "official_home_points",
    "official_away_points",
    "source_home_points",
    "source_away_points",
    "exact_canonical_match",
)
AUTHORITY_BEARING_MANIFEST_FIELDS = (
    "schema_version",
    "artifact_type",
    "classification",
    "contract_id",
    "decision_unit",
    "jira_key",
    "dataset_identity",
    "input_identities",
    "population",
    "authority",
    "label_semantics",
    "label_availability_policy",
    "payloads",
    "scientific_nonclaims",
    "downstream_eligibility",
    "issue_completion",
    "supersession",
    "protected_period_exclusions",
)
NON_AUTHORITATIVE_METADATA = (
    "issued_at_utc",
    "producer.python",
    "producer.platform",
    "producer.polars",
)


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError(
            "2023 development-outcome materialization requires the optional data-engineering environment"
        ) from exc
    return polars


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dataframe_record_sha256(frame: Any) -> str:
    digest = hashlib.sha256()
    for row in frame.iter_rows(named=True):
        digest.update(canonical_json_bytes(row) + b"\n")
    return digest.hexdigest()


def field_schema_sha256(rows: Iterable[Mapping[str, Any]]) -> str:
    fields: set[str] = set()
    for row in rows:
        fields.update(row)
    return stable_hash(sorted(fields))


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp lacks timezone: {value}")
    return parsed.astimezone(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def conservative_eligibility_bound(start_time_utc: str, offset_hours: int = 24) -> str:
    start = parse_utc(start_time_utc)
    bound = start + timedelta(hours=int(offset_hours))
    if bound <= start:
        raise ValueError("conservative eligibility bound is not strictly after kickoff")
    return iso_z(bound)


def expected_parent_identities(contract: Mapping[str, Any]) -> dict[str, str]:
    declared = dict(contract["parent_identities"])
    source = contract["source_contract"]
    derived = {
        "BAT-523_replay": declared["BAT-523_replay"],
        "BAT-554_outcome_spine": source["outcome_spine_identity"],
        "BAT-554_ncaa_crosscheck": source["ncaa_crosscheck_identity"],
    }
    if derived != declared:
        raise ValueError("contract parent identities are not independently derivable from admitted sources")
    return derived


def expected_scientific_nonclaims() -> dict[str, bool]:
    return {
        "bas_or_aggie_excess_result_claimed": False,
        "protected_performance_claimed": False,
        "production_model_ready": False,
        "trained_production_champion": False,
        "tamu_specialization_lift_claimed": False,
        "historical_population_ready": False,
    }


def expected_downstream_eligibility() -> dict[str, Any]:
    return {
        "fold_eligible_only_after": "label_available_after_utc",
        "comparison": "label_available_after_utc < fold_evaluation_cutoff_utc",
        "kickoff_eligibility_forbidden": True,
        "protected_years_forbidden": [2024, 2025],
    }


def expected_issue_completion(contract: Mapping[str, Any]) -> dict[str, Any]:
    completion = dict(contract["issue_completion"])
    return {
        "jira_key": completion["jira_key"],
        "local_issue_id": completion["local_issue_id"],
        "completion_requires_corrected_chronology": True,
        "kickoff_availability_forbidden": True,
        "issue_complete": True,
        "workflow_state": "DONE",
        "evidence_state": "VERIFIED",
        "correction": "LABEL_CHRONOLOGY_HARDENED",
    }


def expected_supersession(contract: Mapping[str, Any]) -> dict[str, Any]:
    supersedes = dict(contract["supersedes"])
    if supersedes.get("dataset_identity") != SUPERSEDED_CYCLE6_IDENTITY:
        raise ValueError("contract lost the superseded Cycle #6 identity")
    if supersedes.get("kickoff_dataset_identity") != SUPERSEDED_KICKOFF_IDENTITY:
        raise ValueError("contract lost the superseded kickoff-time identity")
    return {
        "dataset_identity": SUPERSEDED_CYCLE6_IDENTITY,
        "contract_id": supersedes["contract_id"],
        "reason": "LABEL_AVAILABILITY_CLAIMED_OBSERVED_COMPLETION",
        "active_downstream_use_forbidden": True,
        "kickoff_dataset_identity": SUPERSEDED_KICKOFF_IDENTITY,
        "kickoff_contract_id": supersedes["kickoff_contract_id"],
        "kickoff_reason": "KICKOFF_TIME_LABEL_AVAILABILITY_INVALID",
        "kickoff_active_downstream_use_forbidden": True,
    }


def outcome_result(home_points: int, away_points: int) -> str:
    if home_points > away_points:
        return "HOME_WIN"
    if away_points > home_points:
        return "AWAY_WIN"
    return "TIE"


def team_result(points_for: int, points_against: int) -> str:
    if points_for > points_against:
        return "WIN"
    if points_against > points_for:
        return "LOSS"
    return "TIE"


def load_contract(repo_root: Path) -> dict[str, Any]:
    path = repo_root / CONTRACT_RELATIVE
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected 2023 development-outcome contract identity")
    semantics = contract.get("label_semantics") or {}
    if "available_only_after_completion" in semantics:
        raise ValueError("available_only_after_completion claims observed completion and is forbidden")
    for key, expected in REQUIRED_LABEL_SEMANTICS.items():
        if semantics.get(key) != expected:
            raise ValueError(f"label availability truth drifted: {key}")
    policy = contract.get("label_availability_policy", {})
    if policy.get("policy_id") != LABEL_AVAILABILITY_POLICY:
        raise ValueError("label availability policy is not the precommitted conservative bound")
    if int(policy.get("offset_hours", 0)) != 24:
        raise ValueError("conservative eligibility offset drifted")
    if policy.get("invented_observed_timestamp") is not False:
        raise ValueError("contract must not invent an observed final-whistle timestamp")
    if contract.get("source_contract", {}).get("verified_completion_or_publication_timestamp_fields") != []:
        raise ValueError("contract invented a verified completion timestamp field")
    expected_parent_identities(contract)
    expected_supersession(contract)
    authority = contract["authority"]
    if authority.get("development_2023_label_use") is not True:
        raise ValueError("2023 development label authority is not explicitly enabled")
    for key in (
        "pregame_feature_use",
        "same_game_feature_join",
        "protected_training_admission",
        "protected_evaluation_admission",
        "champion_or_production_promotion",
        "protected_performance_claims",
        "forecast_publication",
        "immutable_raw_capture_mutation",
        "canonical_entity_mutation",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"2023 development-outcome authority is open: {key}")
    return contract


def verify_protected_registry(repo_root: Path, contract: Mapping[str, Any]) -> str:
    from aggie_analytics.validation.protected import classify_season
    from aggie_analytics.validation.protected_split_authority import (
        assert_labels_cannot_override_protected_membership,
        sha256_file as registry_sha,
    )

    source = contract["source_contract"]
    path = repo_root / source["protected_split_registry_relative_path"]
    digest = registry_sha(path)
    if digest != source["protected_split_registry_sha256"]:
        raise ValueError("protected split registry identity drift")
    for season in (2024, 2025):
        if classify_season(season) != "PROTECTED_TEST":
            raise ValueError("protected-season classifier drift")
        assert_labels_cannot_override_protected_membership(
            repo_root, season, "DEVELOPMENT_ONLY"
        )
    if classify_season(2023) != "DEVELOPMENT_SELECTION":
        raise ValueError("2023 development-selection classifier drift")
    return digest


def verify_schema_reconciliation_fingerprint(repo_root: Path, expected: str) -> None:
    path = repo_root / "artifacts" / "entities" / "schema_reconciliation.csv"
    text = path.read_text(encoding="utf-8")
    needle = f"SRC-002:2023:schedules_games_official_outcomes,{expected},"
    if "SRC-002:2023:schedules_games_official_outcomes" not in text or expected not in text:
        raise ValueError("observed schema-reconciliation fingerprint is no longer present")
    if needle not in text and f",{expected},cap_2c82aa5161f3ad63b5abb3c3," not in text:
        raise ValueError("schema-reconciliation fingerprint is not bound to the 2023 SRC-002 table")


def _require_file(path: Path, expected_sha256: str, expected_bytes: int | None = None) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"missing pinned payload: {path}")
    if expected_bytes is not None and path.stat().st_size != int(expected_bytes):
        raise ValueError(f"payload byte drift: {path}")
    if sha256_file(path) != expected_sha256:
        raise ValueError(f"payload SHA-256 drift: {path}")


def load_source_capture(
    data_root: Path, contract: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source = contract["source_contract"]
    raw_path = data_root / source["immutable_raw_relative_path"]
    manifest_path = data_root / source["capture_manifest_relative_path"]
    _require_file(raw_path, source["source_payload_sha256"], source["source_payload_bytes"])
    _require_file(manifest_path, source["capture_manifest_sha256"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("capture_id") != source["capture_id"]:
        raise ValueError("capture identity drift")
    if manifest.get("response_sha256") != source["source_payload_sha256"]:
        raise ValueError("capture manifest response hash drift")
    if int(manifest.get("row_count", -1)) != int(source["source_row_count"]):
        raise ValueError("capture manifest row-count drift")
    if str(manifest.get("parameters", {}).get("year")) != "2023":
        raise ValueError("capture is not the 2023 games request")
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("2023 source payload must be a JSON array")
    if len(payload) != int(source["source_row_count"]):
        raise ValueError("2023 source row-count drift")
    computed_schema = field_schema_sha256(payload)
    if computed_schema != source["source_field_schema_sha256"]:
        raise ValueError("independently computed source field schema drift")
    seasons = {int(row.get("season", -1)) for row in payload}
    if seasons & PROTECTED_SEASONS:
        raise ValueError("protected 2024/2025 outcome entered the 2023 development source")
    if seasons != {2023}:
        raise ValueError(f"2023 development source season drift: {sorted(seasons)}")
    return payload, manifest


def load_registry_maps(
    data_root: Path, contract: Mapping[str, Any]
) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    source = contract["source_contract"]
    path = data_root / source["canonical_registry_relative_path"]
    _require_file(path, source["canonical_registry_sha256"])
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    games = {
        row["source_entity_key"]: row
        for row in rows
        if row["record_type"] == "ENTITY"
        and row["entity_type"] == "game"
        and row["source_system_id"] == "SRC-002"
        and row["season"] == "2023"
    }
    teams: dict[str, str] = {}
    for row in rows:
        if (
            row["record_type"] == "ENTITY"
            and row["entity_type"] == "team"
            and row["source_system_id"] == "SRC-002"
            and row.get("resolution_state") == "AUTO_ACCEPTED_VERIFIED"
            and row.get("mapping_method") == source["canonical_team_mapping_method"]
        ):
            key = str(row["source_entity_key"])
            if key in teams and teams[key] != row["canonical_id"]:
                raise ValueError(f"canonical team map collision: {key}")
            teams[key] = row["canonical_id"]
    if len(games) != int(contract["acceptance"]["expected_source_rows"]):
        raise ValueError("canonical 2023 game map population drift")
    return games, teams


def load_spine_2023(
    data_root: Path, contract: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    source = contract["source_contract"]
    manifest_path = data_root / source["outcome_spine_manifest_relative_path"]
    payload_path = data_root / source["outcome_spine_completed_relative_path"]
    _require_file(manifest_path, source["outcome_spine_manifest_sha256"])
    _require_file(payload_path, source["outcome_spine_completed_sha256"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_identity") != source["outcome_spine_identity"]:
        raise ValueError("outcome-spine identity drift")
    frame = _polars().read_parquet(payload_path).filter(_polars().col("season") == 2023)
    if frame["season"].min() != 2023 or frame["season"].max() != 2023:
        raise ValueError("outcome-spine 2023 filter leaked another season")
    by_source: dict[str, dict[str, Any]] = {}
    for row in frame.iter_rows(named=True):
        key = str(row["primary_source_game_id"])
        if key in by_source:
            raise ValueError(f"duplicate spine source game: {key}")
        by_source[key] = row
    return by_source


def load_ncaa_2023(
    data_root: Path, contract: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    source = contract["source_contract"]
    manifest_path = data_root / source["ncaa_crosscheck_manifest_relative_path"]
    payload_path = data_root / source["ncaa_comparisons_relative_path"]
    _require_file(manifest_path, source["ncaa_crosscheck_manifest_sha256"])
    _require_file(payload_path, source["ncaa_comparisons_sha256"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_identity") != source["ncaa_crosscheck_identity"]:
        raise ValueError("NCAA cross-check identity drift")
    rows: dict[str, dict[str, Any]] = {}
    count = 0
    for line in payload_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        count += 1
        item = json.loads(line)
        if int(item["season"]) in PROTECTED_SEASONS:
            raise ValueError("NCAA cross-check payload contains protected-year outcomes")
        if int(item["season"]) != 2023:
            continue
        key = str(item["canonical_game_id"])
        if key in rows:
            raise ValueError(f"duplicate NCAA 2023 comparison: {key}")
        rows[key] = item
    if count != int(source["ncaa_comparisons_rows"]):
        raise ValueError("NCAA comparison row-count drift")
    return rows


def _quarantine(
    source_game_id: str,
    season: int,
    reason_code: str,
    detail: str,
    source_record_evidence_sha256: str,
) -> dict[str, Any]:
    return {
        "source_game_id": source_game_id,
        "season": int(season) if season is not None else None,
        "reason_code": reason_code,
        "detail": detail,
        "source_record_evidence_sha256": source_record_evidence_sha256,
    }


def source_row_non_final_reason(raw: Mapping[str, Any]) -> tuple[str, str] | None:
    if raw.get("completed") is not True:
        return "INCOMPLETE_GAME", str(raw.get("completed"))
    blobs: list[str] = []
    for key in ("notes", "status", "gameStatus", "contestStatus", "statusText"):
        value = raw.get(key)
        if value not in (None, ""):
            blobs.append(str(value).lower())
    text = " ".join(blobs)
    for token in NON_FINAL_TOKENS:
        if token in text:
            return "NON_FINAL_GAME", token
    return None


def classify_source_row(
    raw: Mapping[str, Any],
    *,
    games: Mapping[str, Mapping[str, str]],
    teams: Mapping[str, str],
    spine: Mapping[str, Mapping[str, Any]],
    ncaa: Mapping[str, Mapping[str, Any]],
    source: Mapping[str, Any],
    seen_source: set[str],
    seen_canonical: set[str],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any]]:
    record_sha = stable_hash(dict(raw))
    source_game_id = str(raw.get("id") or "").strip()
    try:
        season = int(raw.get("season"))
    except (TypeError, ValueError):
        season = -1
    ncaa_row: dict[str, Any] = {
        "canonical_game_id": None,
        "source_game_id": source_game_id,
        "ncaa_status": "NO_NCAA_COMPARISON_ROW",
        "ncaa_contest_id": None,
        "official_home_points": None,
        "official_away_points": None,
        "source_home_points": raw.get("homePoints"),
        "source_away_points": raw.get("awayPoints"),
        "exact_canonical_match": False,
    }
    missing = [name for name in REQUIRED_SOURCE_FIELDS if name not in raw]
    if missing:
        return None, _quarantine(
            source_game_id, season, "MISSING_REQUIRED_FIELD", ",".join(missing), record_sha
        ), ncaa_row
    if season in PROTECTED_SEASONS:
        raise ValueError("protected 2024/2025 outcome entered development materialization")
    if season != 2023:
        return None, _quarantine(
            source_game_id, season, "NON_2023_SEASON", f"season={season}", record_sha
        ), ncaa_row
    if source_game_id in seen_source:
        return None, _quarantine(
            source_game_id, season, "DUPLICATE_SOURCE_GAME", source_game_id, record_sha
        ), ncaa_row
    seen_source.add(source_game_id)
    non_final = source_row_non_final_reason(raw)
    if non_final is not None:
        reason_code, detail = non_final
        return None, _quarantine(source_game_id, season, reason_code, detail, record_sha), ncaa_row
    if raw.get("homePoints") is None or raw.get("awayPoints") is None:
        return None, _quarantine(
            source_game_id, season, "MISSING_SCORES", "homePoints/awayPoints", record_sha
        ), ncaa_row
    if raw.get("homeId") is None or raw.get("awayId") is None or raw.get("homeId") == raw.get("awayId"):
        return None, _quarantine(
            source_game_id, season, "SAME_TEAM_BOTH_SIDES", "homeId/awayId", record_sha
        ), ncaa_row
    mapping = games.get(source_game_id)
    if mapping is None:
        return None, _quarantine(
            source_game_id, season, "UNMAPPED_CANONICAL_GAME", source_game_id, record_sha
        ), ncaa_row
    canonical_game_id = mapping["canonical_id"]
    if canonical_game_id in seen_canonical:
        return None, _quarantine(
            source_game_id, season, "DUPLICATE_CANONICAL_GAME", canonical_game_id, record_sha
        ), ncaa_row
    seen_canonical.add(canonical_game_id)
    home_team_id = teams.get(str(raw["homeId"]))
    away_team_id = teams.get(str(raw["awayId"]))
    if home_team_id is None or away_team_id is None:
        return None, _quarantine(
            source_game_id, season, "UNMAPPED_TEAM", f"{raw['homeId']}/{raw['awayId']}", record_sha
        ), ncaa_row
    if home_team_id != mapping["home_team_id"] or away_team_id != mapping["away_team_id"]:
        return None, _quarantine(
            source_game_id,
            season,
            "HOME_AWAY_ORIENTATION_MISMATCH",
            f"source {home_team_id}/{away_team_id} vs canonical {mapping['home_team_id']}/{mapping['away_team_id']}",
            record_sha,
        ), ncaa_row
    if mapping["canonical_id"] != canonical_game_id:
        return None, _quarantine(
            source_game_id, season, "CANONICAL_ID_MISMATCH", canonical_game_id, record_sha
        ), ncaa_row
    home_points = int(raw["homePoints"])
    away_points = int(raw["awayPoints"])
    spine_row = spine.get(source_game_id)
    if spine_row is None:
        return None, _quarantine(
            source_game_id, season, "SPINE_SCORE_CONFLICT", "missing spine row", record_sha
        ), ncaa_row
    if int(spine_row["home_points"]) != home_points or int(spine_row["away_points"]) != away_points:
        return None, _quarantine(
            source_game_id,
            season,
            "SPINE_SCORE_CONFLICT",
            f"spine {spine_row['home_points']}-{spine_row['away_points']} vs source {home_points}-{away_points}",
            record_sha,
        ), ncaa_row
    if str(spine_row["canonical_game_id"]) != canonical_game_id:
        return None, _quarantine(
            source_game_id, season, "CANONICAL_ID_MISMATCH", str(spine_row["canonical_game_id"]), record_sha
        ), ncaa_row
    ncaa_item = ncaa.get(canonical_game_id)
    if ncaa_item is not None:
        ncaa_row.update(
            {
                "canonical_game_id": canonical_game_id,
                "ncaa_status": ncaa_item["status"],
                "ncaa_contest_id": ncaa_item.get("ncaa_contest_id"),
                "official_home_points": ncaa_item.get("official_home_points"),
                "official_away_points": ncaa_item.get("official_away_points"),
                "exact_canonical_match": ncaa_item.get("status") == "AGREEMENT",
            }
        )
        if ncaa_item.get("status") == "AGREEMENT":
            official_home = ncaa_item.get("official_home_points")
            official_away = ncaa_item.get("official_away_points")
            if official_home is None or official_away is None:
                return None, _quarantine(
                    source_game_id, season, "NCAA_SCORE_CONFLICT", "agreement lacks official points", record_sha
                ), ncaa_row
            if int(official_home) != home_points or int(official_away) != away_points:
                return None, _quarantine(
                    source_game_id,
                    season,
                    "NCAA_SCORE_CONFLICT",
                    f"ncaa {official_home}-{official_away} vs source {home_points}-{away_points}",
                    record_sha,
                ), ncaa_row
    start_time_utc = mapping["start_time_utc"]
    parse_utc(start_time_utc)
    offset_hours = int(source.get("conservative_offset_hours", 24))
    bound = conservative_eligibility_bound(start_time_utc, offset_hours)
    if parse_utc(bound) <= parse_utc(start_time_utc):
        raise ValueError("label availability boundary is not strictly after kickoff")
    accepted = {
        "observation_id": "dev2023_outcome_" + stable_hash(
            {
                "canonical_game_id": canonical_game_id,
                "source_record_evidence_sha256": record_sha,
                "source_payload_sha256": source["source_payload_sha256"],
            }
        )[:24],
        "source_game_id": source_game_id,
        "canonical_game_id": canonical_game_id,
        "season": 2023,
        "season_type": str(raw["seasonType"]),
        "week": int(raw["week"]),
        "start_time_utc": start_time_utc,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "neutral_site": bool(raw["neutralSite"]),
        "home_points": home_points,
        "away_points": away_points,
        "margin": home_points - away_points,
        "outcome_result": outcome_result(home_points, away_points),
        "completed": True,
        "outcome_observed_at_utc": source["capture_known_at_utc"],
        "outcome_effective_at_utc": None,
        "outcome_effective_unavailable_reason": OUTCOME_EFFECTIVE_UNAVAILABLE_REASON,
        "label_available_after_utc": bound,
        "conservative_eligibility_bound_utc": bound,
        "label_availability_policy": LABEL_AVAILABILITY_POLICY,
        "source_capture_id": source["capture_id"],
        "source_payload_sha256": source["source_payload_sha256"],
        "source_record_evidence_sha256": record_sha,
        "canonical_mapping_record_sha256": stable_hash(dict(mapping)),
        "canonical_registry_sha256": source["canonical_registry_sha256"],
        "ncaa_status": ncaa_row["ncaa_status"],
        "ncaa_contest_id": ncaa_row["ncaa_contest_id"],
        "spine_score_match": True,
        "historical_known_at_state": HISTORICAL_KNOWN_AT_STATE,
        "not_a_pregame_feature": True,
        "development_label_only": True,
        "protected_eligible": False,
        "protected_performance_authority": False,
    }
    accepted["row_lineage_sha256"] = stable_hash(accepted)
    ncaa_row["canonical_game_id"] = canonical_game_id
    ncaa_row["source_home_points"] = home_points
    ncaa_row["source_away_points"] = away_points
    return accepted, None, ncaa_row


def materialize_team_observations(accepted: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for game in accepted:
        for site, team_id, opponent_id, points_for, points_against in (
            ("HOME", game["home_team_id"], game["away_team_id"], game["home_points"], game["away_points"]),
            ("AWAY", game["away_team_id"], game["home_team_id"], game["away_points"], game["home_points"]),
        ):
            row = {
                "observation_id": "dev2023_team_" + stable_hash(
                    {"parent": game["observation_id"], "team_id": team_id, "site": site}
                )[:24],
                "parent_observation_id": game["observation_id"],
                "canonical_game_id": game["canonical_game_id"],
                "source_game_id": game["source_game_id"],
                "season": game["season"],
                "season_type": game["season_type"],
                "week": game["week"],
                "start_time_utc": game["start_time_utc"],
                "team_id": team_id,
                "opponent_id": opponent_id,
                "site": site,
                "points_for": points_for,
                "points_against": points_against,
                "margin": points_for - points_against,
                "result": team_result(points_for, points_against),
                "outcome_observed_at_utc": game["outcome_observed_at_utc"],
                "outcome_effective_at_utc": game["outcome_effective_at_utc"],
                "outcome_effective_unavailable_reason": game["outcome_effective_unavailable_reason"],
                "label_available_after_utc": game["label_available_after_utc"],
                "conservative_eligibility_bound_utc": game["conservative_eligibility_bound_utc"],
                "label_availability_policy": game["label_availability_policy"],
                "source_capture_id": game["source_capture_id"],
                "source_payload_sha256": game["source_payload_sha256"],
                "source_record_evidence_sha256": game["source_record_evidence_sha256"],
                "not_a_pregame_feature": True,
                "development_label_only": True,
            }
            row["row_lineage_sha256"] = stable_hash(row)
            observations.append(row)
    return observations


def build_rows(
    payload: Sequence[Mapping[str, Any]],
    *,
    games: Mapping[str, Mapping[str, str]],
    teams: Mapping[str, str],
    spine: Mapping[str, Mapping[str, Any]],
    ncaa: Mapping[str, Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    source = dict(contract["source_contract"])
    source["conservative_offset_hours"] = int(contract["label_availability_policy"]["offset_hours"])
    accepted: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    ncaa_rows: list[dict[str, Any]] = []
    seen_source: set[str] = set()
    seen_canonical: set[str] = set()
    for raw in payload:
        game, quarantine, ncaa_row = classify_source_row(
            raw,
            games=games,
            teams=teams,
            spine=spine,
            ncaa=ncaa,
            source=source,
            seen_source=seen_source,
            seen_canonical=seen_canonical,
        )
        ncaa_rows.append(ncaa_row)
        if quarantine is not None:
            quarantined.append(quarantine)
            continue
        if game is None:
            raise ValueError("classifier returned neither acceptance nor quarantine")
        accepted.append(game)
    accepted.sort(key=lambda row: (row["start_time_utc"], row["canonical_game_id"]))
    observations = materialize_team_observations(accepted)
    observations.sort(key=lambda row: (row["start_time_utc"], row["canonical_game_id"], row["site"]))
    assert_label_chronology(accepted, observations, contract)
    assert_complementary_team_labels(accepted, observations)
    return accepted, observations, quarantined, ncaa_rows


def _empty_frame(fields: tuple[str, ...]) -> Any:
    pl = _polars()
    return pl.DataFrame({name: [] for name in fields})


def _frame(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> Any:
    pl = _polars()
    if not rows:
        return _empty_frame(fields)
    return pl.DataFrame(rows).select(list(fields))


def population_from_rows(
    accepted: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    quarantined: list[dict[str, Any]],
    ncaa_rows: list[dict[str, Any]],
    source_row_count: int,
) -> dict[str, Any]:
    ncaa_status = Counter(str(row["ncaa_status"]) for row in ncaa_rows)
    return {
        "source_rows": source_row_count,
        "accepted_games": len(accepted),
        "team_observations": len(observations),
        "quarantine_rows": len(quarantined),
        "ties": sum(1 for row in accepted if row["outcome_result"] == "TIE"),
        "season_types": dict(Counter(row["season_type"] for row in accepted)),
        "ncaa_agreements": int(ncaa_status.get("AGREEMENT", 0)),
        "ncaa_missing_official_linescore": int(ncaa_status.get("MISSING_OFFICIAL_LINESCORE", 0)),
        "ncaa_no_comparison_row": int(ncaa_status.get("NO_NCAA_COMPARISON_ROW", 0)),
        "quarantine_reasons": dict(Counter(row["reason_code"] for row in quarantined)),
        "seasons": sorted({int(row["season"]) for row in accepted}),
    }


def assert_population(population: Mapping[str, Any], contract: Mapping[str, Any]) -> None:
    acceptance = contract["acceptance"]
    checks = {
        "source_rows": "expected_source_rows",
        "accepted_games": "expected_accepted_games",
        "team_observations": "expected_team_observations",
        "quarantine_rows": "expected_quarantine_rows",
        "ties": "expected_ties",
        "ncaa_agreements": "expected_ncaa_agreements",
        "ncaa_missing_official_linescore": "expected_ncaa_missing_official_linescore",
        "ncaa_no_comparison_row": "expected_ncaa_no_comparison_row",
    }
    for actual, expected in checks.items():
        if int(population[actual]) != int(acceptance[expected]):
            raise ValueError(f"population drift: {actual}={population[actual]} expected={acceptance[expected]}")
    if population["seasons"] != acceptance["allowed_seasons"]:
        raise ValueError(f"accepted season drift: {population['seasons']}")
    if set(population["seasons"]) & set(acceptance["forbidden_seasons"]):
        raise ValueError("forbidden season entered accepted population")
    if dict(population["season_types"]) != acceptance["expected_season_types"]:
        raise ValueError("season-type profile drift")
    if population["team_observations"] != population["accepted_games"] * 2:
        raise ValueError("team observations are not two-per-accepted-game")


def assert_label_chronology(
    accepted: Sequence[Mapping[str, Any]],
    observations: Sequence[Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> None:
    capture_known = contract["source_contract"]["capture_known_at_utc"]
    offset_hours = int(contract["label_availability_policy"]["offset_hours"])
    seen_game_team: set[tuple[str, str]] = set()
    for row in (*accepted, *observations):
        if int(row["season"]) in PROTECTED_SEASONS:
            raise ValueError("protected 2024/2025 outcome entered accepted labels")
        if int(row["season"]) != 2023:
            raise ValueError("non-2023 season entered accepted labels")
        start = parse_utc(str(row["start_time_utc"]))
        available = parse_utc(str(row["label_available_after_utc"]))
        bound = parse_utc(str(row["conservative_eligibility_bound_utc"]))
        if available <= start or bound <= start:
            raise ValueError("label availability boundary is not strictly after kickoff")
        expected_bound = conservative_eligibility_bound(str(row["start_time_utc"]), offset_hours)
        if str(row["label_available_after_utc"]) != expected_bound:
            raise ValueError("label_available_after_utc is not the precommitted conservative bound")
        if str(row["conservative_eligibility_bound_utc"]) != expected_bound:
            raise ValueError("conservative eligibility bound drifted")
        if row.get("outcome_effective_at_utc") is not None:
            raise ValueError("outcome_effective_at_utc must remain unavailable without a verified completion timestamp")
        if row.get("outcome_effective_unavailable_reason") != OUTCOME_EFFECTIVE_UNAVAILABLE_REASON:
            raise ValueError("outcome_effective unavailable reason drifted")
        if row.get("outcome_observed_at_utc") != capture_known:
            raise ValueError("outcome_observed_at_utc is not the source capture known-at")
        if row.get("label_availability_policy") != LABEL_AVAILABILITY_POLICY:
            raise ValueError("label availability policy drifted")
        if row.get("completed") is False:
            raise ValueError("non-final game received a development label")
    for row in accepted:
        if row.get("completed") is not True:
            raise ValueError("accepted game is not completed/final")
    for row in observations:
        key = (str(row["canonical_game_id"]), str(row["team_id"]))
        if key in seen_game_team:
            raise ValueError(f"duplicate game-team label row: {key}")
        seen_game_team.add(key)


def assert_complementary_team_labels(
    accepted: Sequence[Mapping[str, Any]],
    observations: Sequence[Mapping[str, Any]],
) -> None:
    by_game: dict[str, list[Mapping[str, Any]]] = {}
    for row in observations:
        by_game.setdefault(str(row["canonical_game_id"]), []).append(row)
    if len(by_game) != len(accepted):
        raise ValueError("team observations do not cover exactly the accepted games")
    for game in accepted:
        rows = by_game.get(str(game["canonical_game_id"]), [])
        if len(rows) != 2:
            raise ValueError(f"game {game['canonical_game_id']} does not have exactly two team rows")
        home = next((row for row in rows if row["site"] == "HOME"), None)
        away = next((row for row in rows if row["site"] == "AWAY"), None)
        if home is None or away is None:
            raise ValueError("team rows are not a HOME/AWAY pair")
        if home["team_id"] != game["home_team_id"] or away["team_id"] != game["away_team_id"]:
            raise ValueError("team-row orientation drifted from the accepted game")
        if home["opponent_id"] != away["team_id"] or away["opponent_id"] != home["team_id"]:
            raise ValueError("team/opponent identifiers are not complementary")
        if home["points_for"] != away["points_against"] or away["points_for"] != home["points_against"]:
            raise ValueError("team/opponent scores are not complementary")
        complementary = {
            ("WIN", "LOSS"),
            ("LOSS", "WIN"),
            ("TIE", "TIE"),
        }
        if (home["result"], away["result"]) not in complementary:
            raise ValueError("team/opponent results are not complementary")


def identity_core(
    *,
    contract_sha256: str,
    source: Mapping[str, Any],
    record_hashes: Mapping[str, str],
    population: Mapping[str, Any],
    classification: str,
    parent_identities: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "classification": classification,
        "contract_sha256": contract_sha256,
        "source_payload_sha256": source["source_payload_sha256"],
        "capture_id": source["capture_id"],
        "canonical_registry_sha256": source["canonical_registry_sha256"],
        "ncaa_comparisons_sha256": source["ncaa_comparisons_sha256"],
        "outcome_spine_completed_sha256": source["outcome_spine_completed_sha256"],
        "record_hashes": dict(record_hashes),
        "label_availability_policy": LABEL_AVAILABILITY_POLICY,
        "parent_identities": dict(parent_identities or {}),
        "population": {
            key: population[key]
            for key in (
                "source_rows",
                "accepted_games",
                "team_observations",
                "quarantine_rows",
                "ties",
                "ncaa_agreements",
                "ncaa_missing_official_linescore",
                "ncaa_no_comparison_row",
            )
        },
    }


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".tmp-{os.getpid()}-{hashlib.sha256(payload).hexdigest()[:8]}")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(dict(row)) + b"\n" for row in rows)


def rebuild_expected(
    *, data_root: Path, repo_root: Path
) -> dict[str, Any]:
    contract = load_contract(repo_root)
    verify_protected_registry(repo_root, contract)
    verify_schema_reconciliation_fingerprint(
        repo_root, contract["source_contract"]["observed_schema_reconciliation_fingerprint"]
    )
    payload, capture = load_source_capture(data_root, contract)
    games, teams = load_registry_maps(data_root, contract)
    spine = load_spine_2023(data_root, contract)
    ncaa = load_ncaa_2023(data_root, contract)
    accepted, observations, quarantined, ncaa_rows = build_rows(
        payload, games=games, teams=teams, spine=spine, ncaa=ncaa, contract=contract
    )
    population = population_from_rows(
        accepted, observations, quarantined, ncaa_rows, len(payload)
    )
    assert_population(population, contract)
    accepted_frame = _frame(accepted, ACCEPTED_GAME_FIELDS)
    observation_frame = _frame(observations, TEAM_OBSERVATION_FIELDS)
    quarantine_frame = _frame(quarantined, QUARANTINE_FIELDS)
    ncaa_frame = _frame(ncaa_rows, NCAA_FIELDS)
    record_hashes = {
        "accepted_game_outcomes": dataframe_record_sha256(accepted_frame),
        "team_outcome_observations": dataframe_record_sha256(observation_frame),
        "quarantine": dataframe_record_sha256(quarantine_frame),
        "ncaa_crosscheck": dataframe_record_sha256(ncaa_frame),
    }
    contract_sha256 = sha256_file(repo_root / CONTRACT_RELATIVE)
    parents = expected_parent_identities(contract)
    identity = stable_hash(
        identity_core(
            contract_sha256=contract_sha256,
            source=contract["source_contract"],
            record_hashes=record_hashes,
            population=population,
            classification=contract["classification"],
            parent_identities=parents,
        )
    )
    return {
        "contract": contract,
        "capture": capture,
        "accepted": accepted,
        "observations": observations,
        "quarantined": quarantined,
        "ncaa_rows": ncaa_rows,
        "accepted_frame": accepted_frame,
        "observation_frame": observation_frame,
        "quarantine_frame": quarantine_frame,
        "ncaa_frame": ncaa_frame,
        "population": population,
        "record_hashes": record_hashes,
        "contract_sha256": contract_sha256,
        "dataset_identity": identity,
        "parent_identities": parents,
        "code_identity": sha256_file(Path(__file__).resolve()),
    }


def materialize(
    *,
    data_root: Path,
    repo_root: Path,
    issued_at_utc: str,
    output_data_root: Path | None = None,
) -> dict[str, Any]:
    output_root = (output_data_root or data_root).resolve()
    expected = rebuild_expected(data_root=data_root, repo_root=repo_root)
    identity = expected["dataset_identity"]
    payload_root = output_root / "pit_state" / "development_outcomes" / "sha256" / identity
    manifest_root = output_root / "manifests" / "development_outcomes" / "sha256" / identity
    payload_root.mkdir(parents=True, exist_ok=True)
    manifest_root.mkdir(parents=True, exist_ok=True)
    accepted_path = payload_root / "accepted_game_outcomes.parquet"
    observations_path = payload_root / "team_outcome_observations.parquet"
    quarantine_path = payload_root / "quarantine.jsonl"
    ncaa_path = payload_root / "ncaa_crosscheck.jsonl"
    expected["accepted_frame"].write_parquet(accepted_path, compression="zstd", statistics=True)
    expected["observation_frame"].write_parquet(observations_path, compression="zstd", statistics=True)
    _write_bytes(quarantine_path, _jsonl_bytes(expected["quarantined"]))
    _write_bytes(ncaa_path, _jsonl_bytes(expected["ncaa_rows"]))
    payloads = [
        {
            "name": "accepted_game_outcomes.parquet",
            "role": "ACCEPTED_2023_DEVELOPMENT_GAME_LABELS",
            "relative_path": str(accepted_path.relative_to(output_root)).replace("\\", "/"),
            "rows": expected["accepted_frame"].height,
            "bytes": accepted_path.stat().st_size,
            "sha256": sha256_file(accepted_path),
            "record_sha256": expected["record_hashes"]["accepted_game_outcomes"],
            "columns": list(ACCEPTED_GAME_FIELDS),
        },
        {
            "name": "team_outcome_observations.parquet",
            "role": "ACCEPTED_2023_DEVELOPMENT_TEAM_LABELS",
            "relative_path": str(observations_path.relative_to(output_root)).replace("\\", "/"),
            "rows": expected["observation_frame"].height,
            "bytes": observations_path.stat().st_size,
            "sha256": sha256_file(observations_path),
            "record_sha256": expected["record_hashes"]["team_outcome_observations"],
            "columns": list(TEAM_OBSERVATION_FIELDS),
        },
        {
            "name": "quarantine.jsonl",
            "role": "QUARANTINED_2023_DEVELOPMENT_OUTCOMES",
            "relative_path": str(quarantine_path.relative_to(output_root)).replace("\\", "/"),
            "rows": len(expected["quarantined"]),
            "bytes": quarantine_path.stat().st_size,
            "sha256": sha256_file(quarantine_path),
            "record_sha256": expected["record_hashes"]["quarantine"],
            "columns": list(QUARANTINE_FIELDS),
        },
        {
            "name": "ncaa_crosscheck.jsonl",
            "role": "NCAA_OFFICIAL_CROSSCHECK_STATUS",
            "relative_path": str(ncaa_path.relative_to(output_root)).replace("\\", "/"),
            "rows": len(expected["ncaa_rows"]),
            "bytes": ncaa_path.stat().st_size,
            "sha256": sha256_file(ncaa_path),
            "record_sha256": expected["record_hashes"]["ncaa_crosscheck"],
            "columns": list(NCAA_FIELDS),
        },
    ]
    builder_path = repo_root / "tools" / "build_development_2023_outcomes.py"
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "DEVELOPMENT_2023_OUTCOME_IDENTITY",
        "classification": expected["contract"]["classification"],
        "contract_id": expected["contract"]["contract_id"],
        "decision_unit": expected["contract"]["decision_unit"],
        "jira_key": expected["contract"]["jira_key"],
        "parent_jira_key": expected["contract"]["parent_jira_key"],
        "dataset_identity": identity,
        "issued_at_utc": issued_at_utc,
        "input_identities": {
            "source_table_identity": expected["contract"]["source_contract"]["source_table_identity"],
            "capture_id": expected["contract"]["source_contract"]["capture_id"],
            "source_payload_sha256": expected["contract"]["source_contract"]["source_payload_sha256"],
            "capture_manifest_sha256": expected["contract"]["source_contract"]["capture_manifest_sha256"],
            "source_field_schema_sha256": expected["contract"]["source_contract"]["source_field_schema_sha256"],
            "canonical_registry_sha256": expected["contract"]["source_contract"]["canonical_registry_sha256"],
            "ncaa_crosscheck_identity": expected["contract"]["source_contract"]["ncaa_crosscheck_identity"],
            "ncaa_comparisons_sha256": expected["contract"]["source_contract"]["ncaa_comparisons_sha256"],
            "outcome_spine_identity": expected["contract"]["source_contract"]["outcome_spine_identity"],
            "outcome_spine_completed_sha256": expected["contract"]["source_contract"]["outcome_spine_completed_sha256"],
            "protected_split_registry_sha256": expected["contract"]["source_contract"]["protected_split_registry_sha256"],
            "contract_sha256": expected["contract_sha256"],
            "parent_identities": expected["parent_identities"],
        },
        "producer": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "polars": _polars().__version__,
            "code_identity": expected["code_identity"],
            "builder_sha256": sha256_file(builder_path) if builder_path.is_file() else None,
        },
        "population": expected["population"],
        "authority": expected["contract"]["authority"],
        "label_semantics": expected["contract"]["label_semantics"],
        "label_availability_policy": expected["contract"]["label_availability_policy"],
        "payloads": payloads,
        "negative_findings": expected["contract"]["negative_findings"],
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "downstream_eligibility": expected_downstream_eligibility(),
        "issue_completion": expected_issue_completion(expected["contract"]),
        "supersession": expected_supersession(expected["contract"]),
        "protected_period_exclusions": sorted(PROTECTED_SEASONS),
    }
    manifest_path = manifest_root / "development_2023_outcome_manifest.json"
    _write_bytes(manifest_path, canonical_json_bytes(manifest) + b"\n")
    gate_payloads = [
        {key: item[key] for key in ("name", "role", "rows", "bytes", "sha256", "record_sha256")}
        for item in payloads
    ]
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "DEVELOPMENT_2023_OUTCOME_IDENTITY",
        "decision_unit": expected["contract"]["decision_unit"],
        "jira_key": expected["contract"]["jira_key"],
        "parent_jira_key": expected["contract"]["parent_jira_key"],
        "result": PASS_RESULT,
        "classification": expected["contract"]["classification"],
        "contract_id": expected["contract"]["contract_id"],
        "dataset_identity": identity,
        "manifest": {
            "relative_path": str(manifest_path.relative_to(output_root)).replace("\\", "/"),
            "sha256": sha256_file(manifest_path),
        },
        "input_identities": manifest["input_identities"],
        "population": expected["population"],
        "payloads": gate_payloads,
        "authority": expected["contract"]["authority"],
        "label_semantics": expected["contract"]["label_semantics"],
        "label_availability_policy": expected["contract"]["label_availability_policy"],
        "scientific_nonclaims": manifest["scientific_nonclaims"],
        "downstream_eligibility": manifest["downstream_eligibility"],
        "issue_completion": manifest["issue_completion"],
        "supersession": manifest["supersession"],
        "protected_period_exclusions": sorted(PROTECTED_SEASONS),
        "issued_at_utc": issued_at_utc,
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    gate_path = repo_root / GATE_RELATIVE
    _write_bytes(gate_path, canonical_json_bytes(gate) + b"\n")
    return {
        "dataset_identity": identity,
        "gate_identity": gate["gate_identity"],
        "manifest_path": str(manifest_path),
        "gate_path": str(gate_path),
        "population": expected["population"],
        "manifest_sha256": sha256_file(manifest_path),
        "gate_sha256": sha256_file(gate_path),
        "supersedes": SUPERSEDED_CYCLE6_IDENTITY,
        "also_forbids": SUPERSEDED_KICKOFF_IDENTITY,
    }


GATE_IDENTITY_FIELDS = (
    "schema_version",
    "artifact_type",
    "result",
    "classification",
    "contract_id",
    "decision_unit",
    "jira_key",
    "dataset_identity",
    "manifest",
    "input_identities",
    "population",
    "payloads",
    "authority",
    "label_semantics",
    "label_availability_policy",
    "scientific_nonclaims",
    "downstream_eligibility",
    "issue_completion",
    "supersession",
    "protected_period_exclusions",
)


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    return stable_hash({key: gate[key] for key in GATE_IDENTITY_FIELDS if key in gate})


def expected_payload_inventory(
    expected: Mapping[str, Any],
    data_root: Path,
    manifest_payloads: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    identity = expected["dataset_identity"]
    inventory = [
        {
            "name": "accepted_game_outcomes.parquet",
            "role": "ACCEPTED_2023_DEVELOPMENT_GAME_LABELS",
            "relative_path": f"pit_state/development_outcomes/sha256/{identity}/accepted_game_outcomes.parquet",
            "rows": expected["population"]["accepted_games"],
            "record_sha256": expected["record_hashes"]["accepted_game_outcomes"],
            "columns": list(ACCEPTED_GAME_FIELDS),
        },
        {
            "name": "team_outcome_observations.parquet",
            "role": "ACCEPTED_2023_DEVELOPMENT_TEAM_LABELS",
            "relative_path": f"pit_state/development_outcomes/sha256/{identity}/team_outcome_observations.parquet",
            "rows": expected["population"]["team_observations"],
            "record_sha256": expected["record_hashes"]["team_outcome_observations"],
            "columns": list(TEAM_OBSERVATION_FIELDS),
        },
        {
            "name": "quarantine.jsonl",
            "role": "QUARANTINED_2023_DEVELOPMENT_OUTCOMES",
            "relative_path": f"pit_state/development_outcomes/sha256/{identity}/quarantine.jsonl",
            "rows": expected["population"]["quarantine_rows"],
            "record_sha256": expected["record_hashes"]["quarantine"],
            "columns": list(QUARANTINE_FIELDS),
        },
        {
            "name": "ncaa_crosscheck.jsonl",
            "role": "NCAA_OFFICIAL_CROSSCHECK_STATUS",
            "relative_path": f"pit_state/development_outcomes/sha256/{identity}/ncaa_crosscheck.jsonl",
            "rows": expected["population"]["source_rows"],
            "record_sha256": expected["record_hashes"]["ncaa_crosscheck"],
            "columns": list(NCAA_FIELDS),
        },
    ]
    by_name = {item["name"]: item for item in (manifest_payloads or inventory)}
    rebuilt: list[dict[str, Any]] = []
    for item in inventory:
        relative = by_name.get(item["name"], item).get("relative_path", item["relative_path"])
        path = data_root / relative
        rebuilt.append(
            {
                **item,
                "relative_path": relative,
                "bytes": path.stat().st_size if path.is_file() else None,
                "sha256": sha256_file(path) if path.is_file() else None,
            }
        )
    return rebuilt


def expected_input_identities(expected: Mapping[str, Any]) -> dict[str, Any]:
    source = expected["contract"]["source_contract"]
    return {
        "source_table_identity": source["source_table_identity"],
        "capture_id": source["capture_id"],
        "source_payload_sha256": source["source_payload_sha256"],
        "capture_manifest_sha256": source["capture_manifest_sha256"],
        "source_field_schema_sha256": source["source_field_schema_sha256"],
        "canonical_registry_sha256": source["canonical_registry_sha256"],
        "ncaa_crosscheck_identity": source["ncaa_crosscheck_identity"],
        "ncaa_comparisons_sha256": source["ncaa_comparisons_sha256"],
        "outcome_spine_identity": source["outcome_spine_identity"],
        "outcome_spine_completed_sha256": source["outcome_spine_completed_sha256"],
        "protected_split_registry_sha256": source["protected_split_registry_sha256"],
        "contract_sha256": expected["contract_sha256"],
        "parent_identities": expected_parent_identities(expected["contract"]),
    }


def expected_manifest_authority(
    expected: Mapping[str, Any],
    payloads: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "DEVELOPMENT_2023_OUTCOME_IDENTITY",
        "classification": expected["contract"]["classification"],
        "contract_id": expected["contract"]["contract_id"],
        "decision_unit": expected["contract"]["decision_unit"],
        "jira_key": expected["contract"]["jira_key"],
        "dataset_identity": expected["dataset_identity"],
        "input_identities": expected_input_identities(expected),
        "population": expected["population"],
        "authority": expected["contract"]["authority"],
        "label_semantics": expected["contract"]["label_semantics"],
        "label_availability_policy": expected["contract"]["label_availability_policy"],
        "payloads": list(payloads),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "downstream_eligibility": expected_downstream_eligibility(),
        "issue_completion": expected_issue_completion(expected["contract"]),
        "supersession": expected_supersession(expected["contract"]),
        "protected_period_exclusions": sorted(PROTECTED_SEASONS),
    }


def expected_gate_document(
    expected: Mapping[str, Any],
    *,
    manifest_relative_path: str,
    manifest_sha256: str,
    payloads: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "DEVELOPMENT_2023_OUTCOME_IDENTITY",
        "decision_unit": expected["contract"]["decision_unit"],
        "jira_key": expected["contract"]["jira_key"],
        "parent_jira_key": expected["contract"]["parent_jira_key"],
        "result": PASS_RESULT,
        "classification": expected["contract"]["classification"],
        "contract_id": expected["contract"]["contract_id"],
        "dataset_identity": expected["dataset_identity"],
        "manifest": {
            "relative_path": manifest_relative_path,
            "sha256": manifest_sha256,
        },
        "input_identities": expected_input_identities(expected),
        "population": expected["population"],
        "payloads": [
            {key: item[key] for key in ("name", "role", "rows", "bytes", "sha256", "record_sha256")}
            for item in payloads
        ],
        "authority": expected["contract"]["authority"],
        "label_semantics": expected["contract"]["label_semantics"],
        "label_availability_policy": expected["contract"]["label_availability_policy"],
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "downstream_eligibility": expected_downstream_eligibility(),
        "issue_completion": expected_issue_completion(expected["contract"]),
        "supersession": expected_supersession(expected["contract"]),
        "protected_period_exclusions": sorted(PROTECTED_SEASONS),
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    return gate


def _compare(expected: Any, actual: Any, path: str, errors: list[str]) -> None:
    if type(expected) is not type(actual) and not (
        isinstance(expected, (int, float)) and isinstance(actual, (int, float))
    ):
        errors.append(f"{path}: type {type(actual).__name__} != {type(expected).__name__}")
        return
    if isinstance(expected, Mapping):
        extra = set(actual) - set(expected)
        missing = set(expected) - set(actual)
        if extra:
            errors.append(f"{path}: unexpected keys {sorted(extra)}")
        if missing:
            errors.append(f"{path}: missing keys {sorted(missing)}")
        for key in expected:
            if key in actual:
                _compare(expected[key], actual[key], f"{path}.{key}", errors)
        return
    if isinstance(expected, list):
        if len(expected) != len(actual):
            errors.append(f"{path}: length {len(actual)} != {len(expected)}")
            return
        for index, (left, right) in enumerate(zip(expected, actual)):
            _compare(left, right, f"{path}[{index}]", errors)
        return
    if expected != actual:
        errors.append(f"{path}: {actual!r} != {expected!r}")


def validate_artifact(
    *,
    data_root: Path,
    repo_root: Path,
    require_rebuild: bool = True,
    gate: Mapping[str, Any] | None = None,
    manifest: Mapping[str, Any] | None = None,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    gate_path = repo_root / GATE_RELATIVE
    loaded_gate = dict(gate) if gate is not None else json.loads(gate_path.read_text(encoding="utf-8"))
    if not require_rebuild:
        if loaded_gate.get("result") != PASS_RESULT:
            raise ValueError("gate result is not a 2023 development-label pass")
        return {"result": "PASS", "mode": "gate_schema_only", "dataset_identity": loaded_gate["dataset_identity"]}
    rebuilt = expected or rebuild_expected(data_root=data_root, repo_root=repo_root)
    identity = rebuilt["dataset_identity"]
    manifest_path = (
        data_root / "manifests" / "development_outcomes" / "sha256" / identity
        / "development_2023_outcome_manifest.json"
    )
    loaded_manifest = (
        dict(manifest)
        if manifest is not None
        else json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.is_file()
        else {}
    )
    errors: list[str] = []
    if loaded_gate.get("dataset_identity") != identity:
        errors.append("gate dataset identity does not match independently rebuilt identity")
    if loaded_manifest.get("dataset_identity") != identity:
        errors.append("manifest dataset identity does not match independently rebuilt identity")
    if not loaded_manifest:
        errors.append("missing rebuilt manifest")
    rebuilt_payloads = expected_payload_inventory(rebuilt, data_root, loaded_manifest.get("payloads"))
    for item in rebuilt_payloads:
        if item["sha256"] is None:
            errors.append(f"missing payload: {item['name']}")
        if item["name"] not in {row.get("name") for row in loaded_manifest.get("payloads", [])}:
            errors.append(f"payload inventory omitted {item['name']}")
    expected_authority = expected_manifest_authority(rebuilt, rebuilt_payloads)
    actual_authority = {key: loaded_manifest.get(key) for key in AUTHORITY_BEARING_MANIFEST_FIELDS}
    _compare(expected_authority, actual_authority, "manifest", errors)
    expected_gate = expected_gate_document(
        rebuilt,
        manifest_relative_path=str(manifest_path.relative_to(data_root)).replace("\\", "/")
        if manifest_path.is_file()
        else loaded_gate.get("manifest", {}).get("relative_path", ""),
        manifest_sha256=sha256_file(manifest_path) if manifest_path.is_file() else "",
        payloads=rebuilt_payloads,
    )
    for key in GATE_IDENTITY_FIELDS:
        if key == "manifest":
            continue
        if loaded_gate.get(key) != expected_gate.get(key):
            errors.append(f"gate.{key} is not independently reconstructed")
    if loaded_gate.get("input_identities", {}).get("parent_identities") != expected_parent_identities(
        rebuilt["contract"]
    ):
        errors.append("gate parent identities were not derived from the authoritative contract")
    if loaded_gate.get("result") != PASS_RESULT:
        errors.append("altered result/classification")
    if loaded_gate.get("classification") != rebuilt["contract"]["classification"]:
        errors.append("altered result/classification")
    if loaded_gate.get("label_semantics") != rebuilt["contract"]["label_semantics"]:
        errors.append("altered completion semantics")
    if loaded_gate.get("scientific_nonclaims") != expected_scientific_nonclaims():
        errors.append("altered protected nonclaims")
    if loaded_gate.get("issue_completion") != expected_issue_completion(rebuilt["contract"]):
        errors.append("altered issue completion state")
    if loaded_gate.get("supersession") != expected_supersession(rebuilt["contract"]):
        errors.append("supersession metadata drift")
    if loaded_gate.get("protected_period_exclusions") != sorted(PROTECTED_SEASONS):
        errors.append("protected-period exclusions drifted")
    if loaded_gate.get("dataset_identity") == SUPERSEDED_KICKOFF_IDENTITY:
        errors.append("superseded kickoff-time identity is still active")
    if loaded_gate.get("dataset_identity") == SUPERSEDED_CYCLE6_IDENTITY:
        errors.append("superseded Cycle #6 identity is still active")
    if "available_only_after_completion" in (loaded_gate.get("label_semantics") or {}):
        errors.append("available_only_after_completion claims observed completion")
    for key, expected in REQUIRED_LABEL_SEMANTICS.items():
        if (loaded_gate.get("label_semantics") or {}).get(key) != expected:
            errors.append(f"altered label availability truth: {key}")
    independently_recomputed = compute_gate_identity(
        {key: loaded_gate[key] for key in GATE_IDENTITY_FIELDS if key in loaded_gate}
    )
    if loaded_gate.get("gate_identity") != expected_gate["gate_identity"]:
        errors.append("gate identity does not match independently reconstructed authority")
    if independently_recomputed == expected_gate["gate_identity"] and loaded_gate.get("result") != PASS_RESULT:
        errors.append("forged terminal state survived outer identity recomputation")
    if errors:
        raise ValueError("independent 2023 outcome validation failed: " + "; ".join(errors[:16]))
    return {
        "result": "PASS",
        "mode": "independent_rebuild",
        "dataset_identity": identity,
        "gate_identity": expected_gate["gate_identity"],
        "population": rebuilt["population"],
        "supersedes": SUPERSEDED_CYCLE6_IDENTITY,
        "also_forbids": SUPERSEDED_KICKOFF_IDENTITY,
    }

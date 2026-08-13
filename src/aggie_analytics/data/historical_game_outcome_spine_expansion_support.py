"""Expansion-only source and schedule-nonoutcome handling."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from .historical_game_outcome_spine import (
    _bool,
    _build_outputs,
    _missingness,
    _polars,
    _read_json,
    _required_text,
    sha256_file,
    stable_hash,
)


def load_cfbd_expansion(
    data_root: Path, contract: Mapping[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    source = contract["source_contract"]
    acceptance = contract["acceptance"]
    manifest_path = data_root / source["cfbd_manifest_relative_path"]
    if not manifest_path.is_file() or sha256_file(manifest_path) != source["cfbd_manifest_sha256"]:
        raise ValueError("CFBD acquisition manifest identity drift")
    manifest = _read_json(manifest_path)
    seasons = set(source["source_seasons"])
    requests = sorted(
        (
            item
            for item in manifest["request_index"]
            if item.get("endpoint_id") == source["cfbd_endpoint_id"]
            and int(item.get("season", 0)) in seasons
            and item.get("result") == "SUCCESS"
        ),
        key=lambda item: int(item["season"]),
    )
    if len(requests) != acceptance["expected_cfbd_files"]:
        raise ValueError("CFBD game capture file count drift")
    if [int(item["season"]) for item in requests] != sorted(seasons):
        raise ValueError("CFBD game capture season coverage drift")
    if stable_hash([item["response_sha256"] for item in requests]) != source["cfbd_raw_sha256_list_identity"]:
        raise ValueError("CFBD raw hash-list identity drift")
    completed: dict[str, dict[str, Any]] = {}
    incomplete: dict[str, dict[str, Any]] = {}
    profiles: list[dict[str, Any]] = []
    required = {
        "id", "season", "seasonType", "week", "startDate", "completed",
        "neutralSite", "homeId", "awayId", "homePoints", "awayPoints",
    }
    for request in requests:
        season = int(request["season"])
        raw_path = data_root / request["immutable_path"]
        capture_path = data_root / request["capture_manifest_path"]
        if (
            not raw_path.is_file()
            or raw_path.stat().st_size != int(request["response_bytes"])
            or sha256_file(raw_path) != request["response_sha256"]
        ):
            raise ValueError(f"CFBD raw game payload identity drift for {season}")
        if not capture_path.is_file():
            raise ValueError(f"CFBD capture manifest missing for {season}")
        capture = _read_json(capture_path)
        for key in (
            "capture_id", "request_id", "response_sha256", "response_bytes",
            "row_count", "capture_known_at_utc", "immutable_path",
        ):
            if capture.get(key) != request[key]:
                raise ValueError(f"CFBD capture manifest mismatch for {season}: {key}")
        payload = _read_json(raw_path)
        if len(payload) != int(request["row_count"]):
            raise ValueError(f"CFBD raw game row count drift for {season}")
        if request["schema"]["top_level_schema_sha256"] != source["cfbd_schema_sha256"]:
            raise ValueError(f"CFBD game schema drift for {season}")
        for source_row_number, raw in enumerate(payload, start=1):
            if not required <= set(raw):
                raise ValueError(f"CFBD required game field missing for {season}")
            source_game_id = str(raw["id"])
            if source_game_id in completed or source_game_id in incomplete:
                raise ValueError("duplicate CFBD source game identity")
            if int(raw["season"]) != season:
                raise ValueError(f"CFBD row season drift for {source_game_id}")
            if raw["homeId"] is None or raw["awayId"] is None or raw["homeId"] == raw["awayId"]:
                raise ValueError(f"CFBD game participant identity failure: {source_game_id}")
            _required_text(raw["startDate"], "CFBD startDate")
            row = {
                "raw": raw,
                "source_game_id": source_game_id,
                "source_row_number": source_row_number,
                "source_record_sha256": stable_hash(raw),
                "capture_id": request["capture_id"],
                "request_id": request["request_id"],
                "response_sha256": request["response_sha256"],
                "capture_known_at_utc": request["capture_known_at_utc"],
                "capture_manifest_sha256": sha256_file(capture_path),
            }
            if raw["completed"] is True:
                if raw["homePoints"] is None or raw["awayPoints"] is None:
                    raise ValueError(f"CFBD completed game lacks score: {source_game_id}")
                completed[source_game_id] = row
            else:
                if raw["homePoints"] is not None or raw["awayPoints"] is not None:
                    raise ValueError(f"CFBD incomplete game has outcome score: {source_game_id}")
                incomplete[source_game_id] = row
        profiles.append(
            {
                "season": season,
                "rows": len(payload),
                "completed_rows": sum(row["completed"] is True for row in payload),
                "incomplete_rows": sum(row["completed"] is not True for row in payload),
                "bytes": raw_path.stat().st_size,
                "sha256": request["response_sha256"],
                "capture_id": request["capture_id"],
                "capture_manifest_sha256": sha256_file(capture_path),
                "capture_known_at_utc": request["capture_known_at_utc"],
            }
        )
    if len(completed) + len(incomplete) != acceptance["expected_cfbd_rows"]:
        raise ValueError("CFBD game population drift")
    if len(completed) != acceptance["expected_cfbd_completed_rows"]:
        raise ValueError("CFBD completed game population drift")
    if len(incomplete) != acceptance["expected_cfbd_incomplete_rows"]:
        raise ValueError("CFBD incomplete game population drift")
    if min(item["capture_known_at_utc"] for item in profiles) != source["cfbd_minimum_capture_known_at_utc"]:
        raise ValueError("CFBD minimum capture time drift")
    if max(item["capture_known_at_utc"] for item in profiles) != source["cfbd_maximum_capture_known_at_utc"]:
        raise ValueError("CFBD maximum capture time drift")
    return completed, incomplete, manifest, profiles


def build_outputs_expansion(
    completed_cfbd_rows: Mapping[str, Mapping[str, Any]],
    incomplete_cfbd_rows: Mapping[str, Mapping[str, Any]],
    sportsdataverse_rows: Mapping[str, Mapping[str, Any]],
    entities: Mapping[str, Mapping[str, str]],
    cfbd_mappings: Mapping[str, Mapping[str, str]],
    sportsdataverse_mappings: Mapping[str, Mapping[str, str]],
    contract: Mapping[str, Any],
) -> tuple[Any, Any, Any, dict[str, Any]]:
    pl = _polars()
    incomplete_canonical_ids = {
        cfbd_mappings[source_id]["canonical_id"] for source_id in incomplete_cfbd_rows
    }
    if len(incomplete_canonical_ids) != len(incomplete_cfbd_rows):
        raise ValueError("incomplete CFBD canonical mapping is not one-to-one")
    completed_contract = deepcopy(dict(contract))
    acceptance = completed_contract["acceptance"]
    acceptance["expected_cfbd_rows"] = len(completed_cfbd_rows)
    acceptance["expected_cfbd_unique_games"] = len(completed_cfbd_rows)
    acceptance["expected_canonical_schedule_games"] -= len(incomplete_cfbd_rows)
    acceptance["expected_schedule_only_nonoutcomes"] -= len(incomplete_cfbd_rows)
    acceptance["expected_cfbd_only_canonical_games"] -= len(incomplete_cfbd_rows)
    for source_row in incomplete_cfbd_rows.values():
        season = str(source_row["raw"]["season"])
        acceptance["expected_cfbd_by_season"][season] -= 1
        acceptance["expected_schedule_by_season"][season] -= 1
    filtered_entities = {
        key: value for key, value in entities.items() if key not in incomplete_canonical_ids
    }
    filtered_mappings = {
        key: value for key, value in cfbd_mappings.items() if key not in incomplete_cfbd_rows
    }
    completed, schedule_only, reconciliation, profile = _build_outputs(
        completed_cfbd_rows,
        sportsdataverse_rows,
        filtered_entities,
        filtered_mappings,
        sportsdataverse_mappings,
        completed_contract,
    )
    source = contract["source_contract"]
    additional: list[dict[str, Any]] = []
    for source_game_id in sorted(incomplete_cfbd_rows, key=int):
        source_row = incomplete_cfbd_rows[source_game_id]
        mapping = cfbd_mappings[source_game_id]
        entity = entities[mapping["canonical_id"]]
        if _bool(entity["completed"]):
            raise ValueError("incomplete source conflicts with completed canonical entity")
        row = {
            "schema_version": "1.0.0",
            "classification": contract["classification"],
            "canonical_game_id": mapping["canonical_id"],
            "season": int(entity["season"]),
            "season_type": _required_text(entity["season_type"], "canonical season_type"),
            "week": int(entity["week"]),
            "start_time_utc": _required_text(entity["start_time_utc"], "canonical start time"),
            "home_team_id": _required_text(entity["home_team_id"], "canonical home team"),
            "away_team_id": _required_text(entity["away_team_id"], "canonical away team"),
            "neutral_site": _bool(entity["neutral_site"]),
            "game_status": _required_text(entity["game_status"], "canonical game status"),
            "completed": False,
            "home_points": None,
            "away_points": None,
            "outcome_result": None,
            "primary_source_id": source["cfbd_source_id"],
            "primary_source_game_id": source_game_id,
            "primary_source_capture_id": source_row["capture_id"],
            "primary_source_request_id": source_row["request_id"],
            "primary_source_response_sha256": source_row["response_sha256"],
            "primary_source_capture_known_at_utc": source_row["capture_known_at_utc"],
            "source_record_evidence_sha256": source_row["source_record_sha256"],
            "canonical_mapping_record_sha256": stable_hash(dict(mapping)),
            "canonical_registry_sha256": source["canonical_registry_sha256"],
            "source_route_count": 1,
            "source_evidence_sha256": stable_hash([source_row["source_record_sha256"]]),
            "historical_known_at_state": source["historical_known_at_state"],
            "schedule_reference_eligible": True,
            "outcome_reference_eligible": False,
            "preliminary_outcome_label_candidate": False,
            "historical_pit_eligible": False,
            "same_day_chronology_eligible": False,
            "preliminary_feature_direct_admission": False,
            "protected_eligible": False,
            "nonadmission_reason": "SOURCE_SCHEDULE_INCOMPLETE_NO_OUTCOME",
        }
        row["row_lineage_sha256"] = stable_hash(row)
        additional.append(row)
    schedule_only = pl.concat(
        [
            schedule_only,
            pl.DataFrame(additional).select(contract["fields"]["schedule_only_fields"]),
        ],
        how="vertical",
    ).sort(["season", "start_time_utc", "canonical_game_id"])
    profile["cfbd_rows"] += len(incomplete_cfbd_rows)
    profile["cfbd_unique_games"] += len(incomplete_cfbd_rows)
    profile["canonical_schedule_games"] += len(incomplete_cfbd_rows)
    profile["schedule_only_nonoutcomes"] += len(incomplete_cfbd_rows)
    profile["cfbd_only_canonical_games"] += len(incomplete_cfbd_rows)
    all_cfbd = [*completed_cfbd_rows.values(), *incomplete_cfbd_rows.values()]
    profile["cfbd_by_season"] = {
        str(key): value
        for key, value in sorted(Counter(int(row["raw"]["season"]) for row in all_cfbd).items())
    }
    schedule_counts = Counter({int(key): value for key, value in profile["schedule_by_season"].items()})
    for source_row in incomplete_cfbd_rows.values():
        schedule_counts[int(source_row["raw"]["season"])] += 1
    profile["schedule_by_season"] = {str(key): value for key, value in sorted(schedule_counts.items())}
    profile["missingness"]["schedule_only_nonoutcomes"] = _missingness(schedule_only)
    profile["physical_schema_sha256"]["schedule_only_nonoutcomes"] = stable_hash(
        sorted((name, str(dtype)) for name, dtype in schedule_only.schema.items())
    )
    final_acceptance = contract["acceptance"]
    for actual, expected in {
        "cfbd_rows": "expected_cfbd_rows",
        "cfbd_unique_games": "expected_cfbd_unique_games",
        "canonical_schedule_games": "expected_canonical_schedule_games",
        "completed_outcomes": "expected_completed_outcomes",
        "schedule_only_nonoutcomes": "expected_schedule_only_nonoutcomes",
        "ties": "expected_ties",
        "cfbd_only_canonical_games": "expected_cfbd_only_canonical_games",
    }.items():
        if profile[actual] != final_acceptance[expected]:
            raise ValueError(f"historical outcome expansion population drift: {actual}")
    for actual, expected in {
        "cfbd_by_season": "expected_cfbd_by_season",
        "schedule_by_season": "expected_schedule_by_season",
        "completed_by_season": "expected_completed_by_season",
    }.items():
        if profile[actual] != final_acceptance[expected]:
            raise ValueError(f"historical outcome expansion profile drift: {actual}")
    return completed, schedule_only, reconciliation, profile

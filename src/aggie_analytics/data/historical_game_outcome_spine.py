from __future__ import annotations

"""Deterministic historical game/outcome reference materialization.

The output is deliberately narrower than historical PIT truth.  It preserves
completed outcomes, schedule-only nonoutcomes, and source aliases separately;
it never invents publication or final-whistle times.
"""

from collections import Counter, defaultdict
import csv
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError(
            "historical game/outcome materialization requires the optional data-engineering environment"
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


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no", ""}:
        return False
    raise ValueError(f"invalid boolean value: {value!r}")


def _required_text(value: Any, name: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{name} must be nonempty")
    return result


def _by_season(frame: Any) -> dict[str, int]:
    return {
        str(row["season"]): int(row["len"])
        for row in frame.group_by("season").len().sort("season").iter_rows(named=True)
    }


def _duplicate_groups(frame: Any, keys: Iterable[str]) -> int:
    return frame.group_by(list(keys)).len().filter(_polars().col("len") > 1).height


def _missingness(frame: Any) -> dict[str, int]:
    return {name: int(frame[name].null_count()) for name in frame.columns}


def _validate_contract_authority(contract: Mapping[str, Any]) -> None:
    authority = contract["authority"]
    required_open = (
        "candidate_snapshot_materialization",
        "schedule_reference_use",
        "outcome_reference_use",
        "preliminary_outcome_label_candidate",
    )
    if any(authority.get(key) is not True for key in required_open):
        raise ValueError("historical outcome reference authority is not explicitly enabled")
    required_closed = (
        "immutable_raw_capture_mutation",
        "canonical_entity_mutation",
        "historical_pit_admission",
        "same_day_chronology_admission",
        "preliminary_feature_direct_admission",
        "protected_training_admission",
        "protected_evaluation_admission",
        "champion_or_production_promotion",
        "forecast_publication",
    )
    if any(authority.get(key) is not False for key in required_closed):
        raise ValueError("historical outcome authority is open beyond candidate reference use")
    fields = contract["fields"]
    forbidden = set(fields["forbidden_output_fields"])
    configured = set(fields["completed_outcome_fields"]) | set(fields["schedule_only_fields"])
    if forbidden & configured:
        raise ValueError("forbidden provider-derived fields are configured for output")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_registry(
    data_root: Path, contract: Mapping[str, Any]
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]], dict[str, dict[str, str]], dict[str, Any]]:
    source = contract["source_contract"]
    acceptance = contract["acceptance"]
    path = data_root / source["canonical_registry_relative_path"]
    if not path.is_file() or sha256_file(path) != source["canonical_registry_sha256"]:
        raise ValueError("canonical registry identity drift")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    seasons = {str(item) for item in source["source_seasons"]}
    entities = {
        row["canonical_id"]: row
        for row in rows
        if row["record_type"] == "ENTITY"
        and row["entity_type"] == "game"
        and row["season"] in seasons
    }
    cfbd_mappings = {
        row["source_entity_key"]: row
        for row in entities.values()
        if row["source_system_id"] == source["cfbd_source_id"]
    }
    sd_rows = [
        row
        for row in rows
        if row["record_type"] == "SOURCE_MAPPING"
        and row["entity_type"] == "game"
        and row["source_system_id"] == source["sportsdataverse_source_id"]
        and row["season"] in {str(item) for item in range(2004, 2010)}
    ]
    sd_mappings = {row["source_entity_key"]: row for row in sd_rows}
    if len(sd_mappings) != len(sd_rows):
        raise ValueError("duplicate SportsDataverse source mapping identity")
    if len(entities) != acceptance["expected_canonical_schedule_games"]:
        raise ValueError("canonical game entity population drift")
    if len(cfbd_mappings) != acceptance["expected_cfbd_rows"]:
        raise ValueError("canonical CFBD game mapping population drift")
    if len(sd_mappings) != acceptance["expected_sportsdataverse_rows"]:
        raise ValueError("canonical SportsDataverse mapping population drift")
    if any(row["canonical_id"] not in entities for row in sd_rows):
        raise ValueError("SportsDataverse mapping references a missing canonical game")
    if any(row["resolution_state"] != "AUTO_ACCEPTED_VERIFIED" for row in sd_rows):
        raise ValueError("SportsDataverse mapping is not verified")
    profile = {
        "relative_path": source["canonical_registry_relative_path"],
        "sha256": sha256_file(path),
        "canonical_game_entities": len(entities),
        "cfbd_game_mappings": len(cfbd_mappings),
        "sportsdataverse_source_mappings": len(sd_mappings),
        "sportsdataverse_unique_canonical_games": len(
            {row["canonical_id"] for row in sd_rows}
        ),
    }
    return entities, cfbd_mappings, sd_mappings, profile


def _load_cfbd(
    data_root: Path, contract: Mapping[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
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
    rows: dict[str, dict[str, Any]] = {}
    profiles: list[dict[str, Any]] = []
    required = {
        "id", "season", "seasonType", "week", "startDate", "completed",
        "neutralSite", "homeId", "awayId", "homePoints", "awayPoints",
    }
    for request in requests:
        season = int(request["season"])
        path = data_root / request["immutable_path"]
        capture_path = data_root / request["capture_manifest_path"]
        if (
            not path.is_file()
            or path.stat().st_size != int(request["response_bytes"])
            or sha256_file(path) != request["response_sha256"]
        ):
            raise ValueError(f"CFBD raw game payload identity drift for {season}")
        if not capture_path.is_file():
            raise ValueError(f"CFBD capture manifest missing for {season}")
        capture = _read_json(capture_path)
        for key in (
            "capture_id", "request_id", "response_sha256", "response_bytes",
            "row_count", "capture_known_at_utc", "immutable_path",
        ):
            expected = request[key]
            if capture.get(key) != expected:
                raise ValueError(f"CFBD capture manifest mismatch for {season}: {key}")
        payload = _read_json(path)
        if len(payload) != int(request["row_count"]):
            raise ValueError(f"CFBD raw game row count drift for {season}")
        if request["schema"]["top_level_schema_sha256"] != source["cfbd_schema_sha256"]:
            raise ValueError(f"CFBD game schema drift for {season}")
        for source_row_number, raw in enumerate(payload, start=1):
            if not required <= set(raw):
                raise ValueError(f"CFBD required game field missing for {season}")
            source_game_id = str(raw["id"])
            if source_game_id in rows:
                raise ValueError("duplicate CFBD source game identity")
            if int(raw["season"]) != season:
                raise ValueError(f"CFBD row season drift for {source_game_id}")
            if raw["completed"] is not True:
                raise ValueError(f"CFBD incomplete game in outcome source: {source_game_id}")
            if raw["homePoints"] is None or raw["awayPoints"] is None:
                raise ValueError(f"CFBD completed game lacks score: {source_game_id}")
            if raw["homeId"] is None or raw["awayId"] is None or raw["homeId"] == raw["awayId"]:
                raise ValueError(f"CFBD game participant identity failure: {source_game_id}")
            _required_text(raw["startDate"], "CFBD startDate")
            rows[source_game_id] = {
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
        profiles.append(
            {
                "season": season,
                "rows": len(payload),
                "bytes": path.stat().st_size,
                "sha256": request["response_sha256"],
                "capture_id": request["capture_id"],
                "capture_manifest_sha256": sha256_file(capture_path),
                "capture_known_at_utc": request["capture_known_at_utc"],
            }
        )
    if len(rows) != acceptance["expected_cfbd_rows"]:
        raise ValueError("CFBD game population drift")
    minimum = min(item["capture_known_at_utc"] for item in profiles)
    maximum = max(item["capture_known_at_utc"] for item in profiles)
    if minimum != source["cfbd_minimum_capture_known_at_utc"] or maximum != source["cfbd_maximum_capture_known_at_utc"]:
        raise ValueError("CFBD capture-time envelope drift")
    return rows, manifest, profiles


def _load_sportsdataverse(
    data_root: Path, contract: Mapping[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    pl = _polars()
    source = contract["source_contract"]
    acceptance = contract["acceptance"]
    manifest_path = data_root / source["sportsdataverse_manifest_relative_path"]
    if not manifest_path.is_file() or sha256_file(manifest_path) != source["sportsdataverse_manifest_sha256"]:
        raise ValueError("SportsDataverse acquisition manifest identity drift")
    manifest = _read_json(manifest_path)
    captures = sorted(
        (
            item
            for item in manifest["captures"]
            if item.get("dataset") == source["sportsdataverse_dataset"]
        ),
        key=lambda item: int(item["year"]),
    )
    if len(captures) != acceptance["expected_sportsdataverse_files"]:
        raise ValueError("SportsDataverse schedule file count drift")
    if stable_hash([item["sha256"] for item in captures]) != source["sportsdataverse_raw_sha256_list_identity"]:
        raise ValueError("SportsDataverse schedule hash-list identity drift")
    rows: dict[str, dict[str, Any]] = {}
    profiles: list[dict[str, Any]] = []
    required = {
        "game_id", "season", "week", "season_type", "game_date", "neutral_site",
        "home_id", "away_id", "home_score", "away_score", "status",
    }
    for capture in captures:
        season = int(capture["year"])
        path = data_root / capture["relative_path"]
        if (
            not path.is_file()
            or path.stat().st_size != int(capture["bytes"])
            or sha256_file(path) != capture["sha256"]
        ):
            raise ValueError(f"SportsDataverse schedule payload identity drift for {season}")
        frame = pl.read_parquet(path)
        if not required <= set(frame.columns):
            raise ValueError(f"SportsDataverse required schedule field missing for {season}")
        schema_sha256 = stable_hash(sorted((name, str(dtype)) for name, dtype in frame.schema.items()))
        if schema_sha256 != source["sportsdataverse_schema_sha256"]:
            raise ValueError(f"SportsDataverse schedule schema drift for {season}")
        for source_row_number, raw in enumerate(frame.to_dicts(), start=1):
            source_game_id = str(int(raw["game_id"]))
            if source_game_id in rows:
                raise ValueError("duplicate SportsDataverse source game identity")
            if int(raw["season"]) != season:
                raise ValueError(f"SportsDataverse row season drift for {source_game_id}")
            status = _required_text(raw["status"], "SportsDataverse status")
            if status not in {"STATUS_FINAL", "STATUS_POSTPONED", "STATUS_CANCELED"}:
                raise ValueError(f"unexpected SportsDataverse game status: {status}")
            if raw["home_id"] is None or raw["away_id"] is None or raw["home_id"] == raw["away_id"]:
                raise ValueError(f"SportsDataverse participant identity failure: {source_game_id}")
            _required_text(raw["game_date"], "SportsDataverse game_date")
            rows[source_game_id] = {
                "raw": raw,
                "source_game_id": source_game_id,
                "source_row_number": source_row_number,
                "source_record_sha256": stable_hash(raw),
                "capture_id": f"sportsdataverse_asset_{capture['asset_id']}",
                "request_id": capture["request_identity_sha256"],
                "response_sha256": capture["sha256"],
                "capture_known_at_utc": capture["acquired_at_utc"],
            }
        profiles.append(
            {
                "season": season,
                "rows": frame.height,
                "bytes": path.stat().st_size,
                "sha256": capture["sha256"],
                "asset_id": capture["asset_id"],
                "capture_known_at_utc": capture["acquired_at_utc"],
                "physical_schema_sha256": schema_sha256,
            }
        )
    if len(rows) != acceptance["expected_sportsdataverse_rows"]:
        raise ValueError("SportsDataverse schedule population drift")
    minimum = min(item["capture_known_at_utc"] for item in profiles)
    maximum = max(item["capture_known_at_utc"] for item in profiles)
    if minimum != source["sportsdataverse_minimum_capture_known_at_utc"] or maximum != source["sportsdataverse_maximum_capture_known_at_utc"]:
        raise ValueError("SportsDataverse capture-time envelope drift")
    return rows, manifest, profiles


def _outcome_result(home_points: int, away_points: int) -> str:
    if home_points > away_points:
        return "HOME_WIN"
    if home_points < away_points:
        return "AWAY_WIN"
    return "TIE"


def _classify_sportsdataverse_row(
    sportsdataverse_row: Mapping[str, Any], cfbd_row: Mapping[str, Any] | None
) -> tuple[str, bool]:
    raw = sportsdataverse_row["raw"]
    status = raw["status"]
    if cfbd_row is None:
        if status == "STATUS_FINAL":
            return "SUPPLEMENT_ONLY_FINAL", True
        if status == "STATUS_CANCELED":
            return "SUPPLEMENT_ONLY_CANCELED", False
        raise ValueError("supplement-only schedule has unsupported status")
    cfbd_raw = cfbd_row["raw"]
    if status == "STATUS_FINAL":
        if int(raw["home_score"]) != int(cfbd_raw["homePoints"]) or int(raw["away_score"]) != int(cfbd_raw["awayPoints"]):
            raise ValueError("cross-source final score conflict")
        return "CROSS_SOURCE_FINAL_SCORE_EXACT", True
    if status == "STATUS_POSTPONED":
        if int(raw["home_score"]) != 0 or int(raw["away_score"]) != 0:
            raise ValueError("postponed alias contains a nonzero outcome placeholder")
        return "CROSS_SOURCE_POSTPONED_RESCHEDULE_ALIAS", False
    raise ValueError("cross-source schedule has unsupported status")


def _build_outputs(
    cfbd_rows: Mapping[str, Mapping[str, Any]],
    sportsdataverse_rows: Mapping[str, Mapping[str, Any]],
    entities: Mapping[str, Mapping[str, str]],
    cfbd_mappings: Mapping[str, Mapping[str, str]],
    sportsdataverse_mappings: Mapping[str, Mapping[str, str]],
    contract: Mapping[str, Any],
) -> tuple[Any, Any, Any, dict[str, Any]]:
    pl = _polars()
    acceptance = contract["acceptance"]
    fields = contract["fields"]
    cfbd_keys = set(cfbd_rows)
    sportsdataverse_keys = set(sportsdataverse_rows)
    unmapped_cfbd = cfbd_keys - set(cfbd_mappings)
    unmapped_sportsdataverse = sportsdataverse_keys - set(sportsdataverse_mappings)
    if len(unmapped_cfbd) != acceptance["expected_unmapped_cfbd_rows"]:
        raise ValueError("unmapped CFBD game rows")
    if len(unmapped_sportsdataverse) != acceptance["expected_unmapped_sportsdataverse_rows"]:
        raise ValueError("unmapped SportsDataverse game rows")

    cfbd_by_canonical: dict[str, Mapping[str, Any]] = {}
    cfbd_mapping_by_canonical: dict[str, Mapping[str, str]] = {}
    for source_game_id, source_row in cfbd_rows.items():
        mapping = cfbd_mappings[source_game_id]
        canonical_id = mapping["canonical_id"]
        if canonical_id in cfbd_by_canonical:
            raise ValueError("duplicate canonical CFBD game mapping")
        cfbd_by_canonical[canonical_id] = source_row
        cfbd_mapping_by_canonical[canonical_id] = mapping

    sportsdataverse_by_canonical: dict[str, list[tuple[Mapping[str, str], Mapping[str, Any]]]] = defaultdict(list)
    for source_game_id, source_row in sportsdataverse_rows.items():
        mapping = sportsdataverse_mappings[source_game_id]
        sportsdataverse_by_canonical[mapping["canonical_id"]].append((mapping, source_row))
    for values in sportsdataverse_by_canonical.values():
        values.sort(key=lambda item: item[1]["source_game_id"])

    cfbd_canonical = set(cfbd_by_canonical)
    sportsdataverse_canonical = set(sportsdataverse_by_canonical)
    canonical_union = cfbd_canonical | sportsdataverse_canonical
    if canonical_union != set(entities):
        raise ValueError("canonical schedule union differs from the canonical registry")

    completed_rows: list[dict[str, Any]] = []
    schedule_only_rows: list[dict[str, Any]] = []
    reconciliation_rows: list[dict[str, Any]] = []
    for canonical_id in sorted(canonical_union):
        entity = entities[canonical_id]
        canonical_completed = _bool(entity["completed"])
        cfbd = cfbd_by_canonical.get(canonical_id)
        sd_values = sportsdataverse_by_canonical.get(canonical_id, [])
        if cfbd is not None:
            primary = cfbd
            primary_source_id = contract["source_contract"]["cfbd_source_id"]
            primary_mapping = cfbd_mapping_by_canonical[canonical_id]
            completed = True
            home_points = int(cfbd["raw"]["homePoints"])
            away_points = int(cfbd["raw"]["awayPoints"])
        else:
            finals = [value for _, value in sd_values if value["raw"]["status"] == "STATUS_FINAL"]
            canceled = [value for _, value in sd_values if value["raw"]["status"] == "STATUS_CANCELED"]
            if len(finals) == 1 and not canceled:
                primary = finals[0]
                completed = True
                home_points = int(primary["raw"]["home_score"])
                away_points = int(primary["raw"]["away_score"])
            elif len(canceled) == 1 and not finals:
                primary = canceled[0]
                completed = False
                home_points = None
                away_points = None
            else:
                raise ValueError("supplement-only canonical schedule disposition is ambiguous")
            primary_source_id = contract["source_contract"]["sportsdataverse_source_id"]
            primary_mapping = next(mapping for mapping, value in sd_values if value is primary)
        if completed != canonical_completed:
            raise ValueError("canonical completion state conflicts with source disposition")
        source_hashes = [primary["source_record_sha256"]]
        if cfbd is not None:
            source_hashes = [cfbd["source_record_sha256"]] + [
                value["source_record_sha256"] for _, value in sd_values
            ]
        base = {
            "schema_version": "1.0.0",
            "classification": contract["classification"],
            "canonical_game_id": canonical_id,
            "season": int(entity["season"]),
            "season_type": _required_text(entity["season_type"], "canonical season_type"),
            "week": int(entity["week"]),
            "start_time_utc": _required_text(entity["start_time_utc"], "canonical start_time_utc"),
            "home_team_id": _required_text(entity["home_team_id"], "canonical home_team_id"),
            "away_team_id": _required_text(entity["away_team_id"], "canonical away_team_id"),
            "neutral_site": _bool(entity["neutral_site"]),
            "game_status": _required_text(entity["game_status"], "canonical game_status"),
            "completed": completed,
            "home_points": home_points,
            "away_points": away_points,
            "outcome_result": _outcome_result(home_points, away_points) if completed else None,
            "primary_source_id": primary_source_id,
            "primary_source_game_id": primary["source_game_id"],
            "primary_source_capture_id": primary["capture_id"],
            "primary_source_request_id": primary["request_id"],
            "primary_source_response_sha256": primary["response_sha256"],
            "primary_source_capture_known_at_utc": primary["capture_known_at_utc"],
            "source_record_evidence_sha256": primary["source_record_sha256"],
            "canonical_mapping_record_sha256": stable_hash(dict(primary_mapping)),
            "canonical_registry_sha256": contract["source_contract"]["canonical_registry_sha256"],
            "source_route_count": int(cfbd is not None) + int(bool(sd_values)),
            "source_evidence_sha256": stable_hash(sorted(source_hashes)),
            "historical_known_at_state": contract["source_contract"]["historical_known_at_state"],
            "schedule_reference_eligible": True,
            "outcome_reference_eligible": completed,
            "preliminary_outcome_label_candidate": completed,
            "historical_pit_eligible": False,
            "same_day_chronology_eligible": False,
            "preliminary_feature_direct_admission": False,
            "protected_eligible": False,
        }
        if completed:
            base["row_lineage_sha256"] = stable_hash(base)
            completed_rows.append(base)
        else:
            base["nonadmission_reason"] = "CANCELED_SCHEDULE_NO_OUTCOME"
            base["row_lineage_sha256"] = stable_hash(base)
            schedule_only_rows.append(base)

        alias_group_size = len(sd_values)
        for mapping, sportsdataverse in sd_values:
            disposition, contributes = _classify_sportsdataverse_row(sportsdataverse, cfbd)
            reconciliation = {
                "schema_version": "1.0.0",
                "canonical_game_id": canonical_id,
                "season": int(entity["season"]),
                "sportsdataverse_source_game_id": sportsdataverse["source_game_id"],
                "sportsdataverse_status": sportsdataverse["raw"]["status"],
                "sportsdataverse_mapping_method": mapping["mapping_method"],
                "sportsdataverse_resolution_state": mapping["resolution_state"],
                "sportsdataverse_source_row_sha256": sportsdataverse["source_record_sha256"],
                "sportsdataverse_capture_sha256": sportsdataverse["response_sha256"],
                "cfbd_source_game_id": cfbd["source_game_id"] if cfbd else None,
                "cfbd_source_row_sha256": cfbd["source_record_sha256"] if cfbd else None,
                "alias_group_size": alias_group_size,
                "reconciliation_disposition": disposition,
                "same_upstream_independence": False,
                "outcome_reference_contribution": contributes,
            }
            reconciliation["row_lineage_sha256"] = stable_hash(reconciliation)
            reconciliation_rows.append(reconciliation)

    completed = pl.DataFrame(completed_rows).select(fields["completed_outcome_fields"]).sort(
        ["season", "start_time_utc", "canonical_game_id"]
    )
    schedule_only = pl.DataFrame(schedule_only_rows).select(fields["schedule_only_fields"]).sort(
        ["season", "start_time_utc", "canonical_game_id"]
    )
    reconciliation = pl.DataFrame(reconciliation_rows).select(fields["reconciliation_fields"]).sort(
        ["season", "canonical_game_id", "sportsdataverse_source_game_id"]
    )
    forbidden = set(fields["forbidden_output_fields"])
    if forbidden & (set(completed.columns) | set(schedule_only.columns) | set(reconciliation.columns)):
        raise ValueError("forbidden provider-derived field entered output")
    duplicate_completed = _duplicate_groups(completed, ["canonical_game_id"])
    duplicate_schedule_only = _duplicate_groups(schedule_only, ["canonical_game_id"])
    alias_groups = {
        canonical_id: values
        for canonical_id, values in sportsdataverse_by_canonical.items()
        if len(values) > 1
    }
    alias_groups_by_season = Counter(
        int(entities[canonical_id]["season"]) for canonical_id in alias_groups
    )
    disposition_counts = {
        str(row["reconciliation_disposition"]): int(row["len"])
        for row in reconciliation.group_by("reconciliation_disposition").len().iter_rows(named=True)
    }
    profile = {
        "cfbd_rows": len(cfbd_rows),
        "cfbd_unique_games": len(cfbd_rows),
        "sportsdataverse_rows": len(sportsdataverse_rows),
        "sportsdataverse_unique_source_games": len(sportsdataverse_rows),
        "sportsdataverse_unique_canonical_games": len(sportsdataverse_canonical),
        "canonical_schedule_games": len(canonical_union),
        "completed_outcomes": completed.height,
        "schedule_only_nonoutcomes": schedule_only.height,
        "ties": completed.filter(pl.col("outcome_result") == "TIE").height,
        "canonical_cross_source_overlap": len(cfbd_canonical & sportsdataverse_canonical),
        "cfbd_only_canonical_games": len(cfbd_canonical - sportsdataverse_canonical),
        "sportsdataverse_only_canonical_games": len(sportsdataverse_canonical - cfbd_canonical),
        "alias_groups": len(alias_groups),
        "alias_rows": sum(len(values) for values in alias_groups.values()),
        "duplicate_completed_game_ids": duplicate_completed,
        "duplicate_schedule_only_game_ids": duplicate_schedule_only,
        "unmapped_cfbd_rows": len(unmapped_cfbd),
        "unmapped_sportsdataverse_rows": len(unmapped_sportsdataverse),
        "reconciliation_dispositions": disposition_counts,
        "cfbd_by_season": dict(
            sorted(Counter(int(row["raw"]["season"]) for row in cfbd_rows.values()).items())
        ),
        "schedule_by_season": dict(
            sorted(Counter(int(entities[item]["season"]) for item in canonical_union).items())
        ),
        "completed_by_season": _by_season(completed),
        "alias_groups_by_season": {str(key): value for key, value in sorted(alias_groups_by_season.items())},
        "missingness": {
            "completed_outcomes": _missingness(completed),
            "schedule_only_nonoutcomes": _missingness(schedule_only),
            "source_reconciliation": _missingness(reconciliation),
        },
        "physical_schema_sha256": {
            "completed_outcomes": stable_hash(
                sorted((name, str(dtype)) for name, dtype in completed.schema.items())
            ),
            "schedule_only_nonoutcomes": stable_hash(
                sorted((name, str(dtype)) for name, dtype in schedule_only.schema.items())
            ),
            "source_reconciliation": stable_hash(
                sorted((name, str(dtype)) for name, dtype in reconciliation.schema.items())
            ),
        },
    }
    scalar_checks = {
        "cfbd_rows": "expected_cfbd_rows",
        "cfbd_unique_games": "expected_cfbd_unique_games",
        "sportsdataverse_rows": "expected_sportsdataverse_rows",
        "sportsdataverse_unique_source_games": "expected_sportsdataverse_unique_source_games",
        "sportsdataverse_unique_canonical_games": "expected_sportsdataverse_unique_canonical_games",
        "canonical_schedule_games": "expected_canonical_schedule_games",
        "completed_outcomes": "expected_completed_outcomes",
        "schedule_only_nonoutcomes": "expected_schedule_only_nonoutcomes",
        "ties": "expected_ties",
        "canonical_cross_source_overlap": "expected_canonical_cross_source_overlap",
        "cfbd_only_canonical_games": "expected_cfbd_only_canonical_games",
        "sportsdataverse_only_canonical_games": "expected_sportsdataverse_only_canonical_games",
        "alias_groups": "expected_alias_groups",
        "alias_rows": "expected_alias_rows",
        "duplicate_completed_game_ids": "expected_duplicate_completed_game_ids",
        "duplicate_schedule_only_game_ids": "expected_duplicate_schedule_only_game_ids",
        "unmapped_cfbd_rows": "expected_unmapped_cfbd_rows",
        "unmapped_sportsdataverse_rows": "expected_unmapped_sportsdataverse_rows",
    }
    for actual, expected in scalar_checks.items():
        if profile[actual] != acceptance[expected]:
            raise ValueError(f"historical game/outcome population drift: {actual}")
    expected_profiles = {
        "reconciliation_dispositions": "expected_reconciliation_dispositions",
        "cfbd_by_season": "expected_cfbd_by_season",
        "schedule_by_season": "expected_schedule_by_season",
        "completed_by_season": "expected_completed_by_season",
        "alias_groups_by_season": "expected_alias_groups_by_season",
    }
    for actual, expected in expected_profiles.items():
        normalized = {str(key): int(value) for key, value in profile[actual].items()}
        if normalized != acceptance[expected]:
            raise ValueError(f"historical game/outcome population profile drift: {actual}")
        profile[actual] = normalized
    return completed, schedule_only, reconciliation, profile


def materialize(
    *, input_data_root: Path, output_data_root: Path, repo_root: Path, issued_at_utc: str
) -> dict[str, Any]:
    pl = _polars()
    contract_path = repo_root / "configs" / "historical_game_outcome_spine_contract.json"
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    _validate_contract_authority(contract)
    core_path = Path(__file__).resolve()
    builder_path = repo_root / "tools" / "build_historical_game_outcome_spine.py"
    entities, cfbd_mappings, sd_mappings, registry_profile = _load_registry(
        input_data_root, contract
    )
    cfbd_rows, cfbd_manifest, cfbd_profiles = _load_cfbd(input_data_root, contract)
    sd_rows, sd_manifest, sd_profiles = _load_sportsdataverse(input_data_root, contract)
    completed, schedule_only, reconciliation, population = _build_outputs(
        cfbd_rows,
        sd_rows,
        entities,
        cfbd_mappings,
        sd_mappings,
        contract,
    )
    record_hashes = {
        "completed_outcomes": dataframe_record_sha256(completed),
        "schedule_only_nonoutcomes": dataframe_record_sha256(schedule_only),
        "source_reconciliation": dataframe_record_sha256(reconciliation),
    }
    source = contract["source_contract"]
    identity = stable_hash(
        {
            "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "core_sha256": sha256_file(core_path),
            "builder_sha256": sha256_file(builder_path),
            "cfbd_manifest_sha256": source["cfbd_manifest_sha256"],
            "cfbd_payload_sha256": [item["sha256"] for item in cfbd_profiles],
            "sportsdataverse_manifest_sha256": source["sportsdataverse_manifest_sha256"],
            "sportsdataverse_payload_sha256": [item["sha256"] for item in sd_profiles],
            "canonical_registry_sha256": source["canonical_registry_sha256"],
            "record_hashes": record_hashes,
            "classification": contract["classification"],
        }
    )
    canonical_root = output_data_root / "canonical" / "historical_game_outcome_spine" / "sha256" / identity
    quarantine_root = output_data_root / "quarantine" / "historical_game_outcome_spine" / "sha256" / identity
    manifest_root = output_data_root / "manifests" / "historical_game_outcome_spine" / "sha256" / identity
    canonical_root.mkdir(parents=True, exist_ok=True)
    quarantine_root.mkdir(parents=True, exist_ok=True)
    manifest_root.mkdir(parents=True, exist_ok=True)
    completed_path = canonical_root / "completed_game_outcomes.parquet"
    schedule_only_path = quarantine_root / "schedule_only_nonoutcomes.parquet"
    reconciliation_path = quarantine_root / "source_alias_reconciliation.parquet"
    completed.write_parquet(completed_path, compression="zstd", statistics=True)
    schedule_only.write_parquet(schedule_only_path, compression="zstd", statistics=True)
    reconciliation.write_parquet(reconciliation_path, compression="zstd", statistics=True)
    payloads = [
        {
            "role": "COMPLETED_OUTCOME_REFERENCE_CANDIDATES",
            "relative_path": str(completed_path.relative_to(output_data_root)).replace("\\", "/"),
            "rows": completed.height,
            "bytes": completed_path.stat().st_size,
            "sha256": sha256_file(completed_path),
            "record_sha256": record_hashes["completed_outcomes"],
        },
        {
            "role": "SCHEDULE_ONLY_NONOUTCOMES",
            "relative_path": str(schedule_only_path.relative_to(output_data_root)).replace("\\", "/"),
            "rows": schedule_only.height,
            "bytes": schedule_only_path.stat().st_size,
            "sha256": sha256_file(schedule_only_path),
            "record_sha256": record_hashes["schedule_only_nonoutcomes"],
        },
        {
            "role": "SOURCE_ALIAS_AND_OUTCOME_RECONCILIATION",
            "relative_path": str(reconciliation_path.relative_to(output_data_root)).replace("\\", "/"),
            "rows": reconciliation.height,
            "bytes": reconciliation_path.stat().st_size,
            "sha256": sha256_file(reconciliation_path),
            "record_sha256": record_hashes["source_reconciliation"],
        },
    ]
    manifest = {
        "schema_version": "1.0.0",
        "artifact_type": "HISTORICAL_GAME_OUTCOME_REFERENCE_SPINE",
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "classification": contract["classification"],
        "dataset_identity": identity,
        "issued_at_utc": issued_at_utc,
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "producer": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "polars": pl.__version__,
            "core_sha256": sha256_file(core_path),
            "builder_sha256": sha256_file(builder_path),
        },
        "input_identities": {
            "cfbd_manifest_sha256": sha256_file(
                input_data_root / source["cfbd_manifest_relative_path"]
            ),
            "cfbd_raw_sha256_list_identity": source["cfbd_raw_sha256_list_identity"],
            "sportsdataverse_manifest_sha256": sha256_file(
                input_data_root / source["sportsdataverse_manifest_relative_path"]
            ),
            "sportsdataverse_raw_sha256_list_identity": source[
                "sportsdataverse_raw_sha256_list_identity"
            ],
            "canonical_registry_sha256": registry_profile["sha256"],
        },
        "source_profiles": {
            "cfbd": cfbd_profiles,
            "sportsdataverse": sd_profiles,
            "canonical_registry": registry_profile,
            "cfbd_manifest_content_hash": cfbd_manifest.get("content_hash"),
            "sportsdataverse_manifest_content_hash": sd_manifest.get("content_hash"),
        },
        "population": population,
        "chronology": {
            "historical_known_at_state": source["historical_known_at_state"],
            "cfbd_capture_time_envelope": [
                source["cfbd_minimum_capture_known_at_utc"],
                source["cfbd_maximum_capture_known_at_utc"],
            ],
            "sportsdataverse_capture_time_envelope": [
                source["sportsdataverse_minimum_capture_known_at_utc"],
                source["sportsdataverse_maximum_capture_known_at_utc"],
            ],
            "historical_source_publication_time_proved": False,
            "historical_final_whistle_time_proved": False,
            "same_day_chronology_admitted": False,
            "target_game_feature_use_admitted": False,
        },
        "payloads": payloads,
        "authority": contract["authority"],
        "domain_eligibility": contract["domain_eligibility"],
        "negative_findings": contract["negative_findings"],
        "scientific_nonclaims": {
            "historical_population_ready": False,
            "gap_002_resolved": False,
            "production_model_ready": False,
            "trained_production_champion": False,
            "protected_performance_claimed": False,
            "tamu_specialization_lift_claimed": False,
            "bas_or_aggie_excess_result_claimed": False,
        },
    }
    manifest_path = manifest_root / "historical_game_outcome_spine_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    return {
        "dataset_identity": identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "completed_path": str(completed_path),
        "schedule_only_path": str(schedule_only_path),
        "reconciliation_path": str(reconciliation_path),
        "manifest": manifest,
    }

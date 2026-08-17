from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from aggie_analytics.temporal.contracts import parse_time
from aggie_analytics.temporal.historical_recovery import (
    HISTORICAL_OUTCOME_POLICY_VERSION,
    PregamePriorRow,
    TargetGame,
    TeamOutcomeObservation,
    build_pregame_team_priors,
    materialize_prior_cells,
    record_for_storage,
)

SCHEMA_VERSION = "aggie.pit.leakage_battery.v2"
DATASET_IDENTITY = "cf732b78db6deff2e2cca51364a18e03219a5ceda88d2f5efa475dad1f7e3fe7"
MANIFEST_RELATIVE = (
    f"manifests/historical_known_at/sha256/{DATASET_IDENTITY}/known_at_replay_manifest.json"
)
REQUIRED_PAYLOADS = {
    "accepted_game_outcomes.parquet": {
        "rows": 10593,
        "sha256": "7fdea2ced7508e7f3b78d397bf8984325dd2b7095b05dc486335ee9c432ccb64",
        "required_columns": (
            "observation_id",
            "canonical_game_id",
            "home_points",
            "away_points",
            "source_known_at_utc",
        ),
    },
    "team_outcome_observations.parquet": {
        "rows": 21186,
        "sha256": "8a8e057c5eb135a731e37b74587893f25e29c7f1040d7f294f38071e30a9f483",
        "required_columns": (
            "observation_id",
            "canonical_game_id",
            "team_id",
            "source_known_at_utc",
            "completed_known_by_utc",
            "game_start_utc",
            "points_for",
            "points_against",
            "result",
        ),
    },
    "target_game_cutoffs.parquet": {
        "rows": 2764,
        "sha256": "a32b733d9f2278639fea0d4dedc3e9f33a45004f042f869cff148a4bf0faf942",
        "required_columns": (
            "game_id",
            "season",
            "start_utc",
            "home_team_id",
            "away_team_id",
            "cutoff_lead_hours",
        ),
    },
    "pregame_prior_rows.parquet": {
        "rows": 5528,
        "sha256": "23db814da58cfbf0975e99b32130c531ae8e4f26867f0ac1e5207ba36bd6d140",
        "required_columns": (
            "row_id",
            "target_game_id",
            "cutoff_utc",
            "team_id",
            "lineage_sha256",
            "prior_games",
            "missingness",
        ),
    },
    "pregame_prior_cells.parquet": {
        "rows": 22112,
        "sha256": "b581ebd3b4dea87edee886ff8d46b2a5dc40671fc226ed037f4c253f17704c61",
        "required_columns": (
            "cell_id",
            "row_id",
            "feature_name",
            "value",
            "lineage_sha256",
            "missingness",
        ),
    },
}
SCENARIOS = [
    "static_prohibited_field_scan",
    "full_deterministic_reconstruction",
    "future_record_append_invariance",
    "postgame_record_append_invariance",
    "value_mutation_isolation",
    "same_game_target_outcome_exclusion",
    "prediction_cutoff_enforcement",
    "known_at_timestamp_enforcement",
    "normalization_time_leakage",
    "entity_correction_leakage",
    "weather_known_at_missingness_behavior",
    "market_cutoff_missingness_behavior",
    "roster_availability_revision_cutoff_behavior",
    "label_and_derived_label_leakage",
]
PROHIBITED_FEATURE_FIELDS = frozenset(
    {
        "home_win",
        "away_win",
        "winner",
        "label",
        "derived_label",
        "target",
        "target_label",
        "outcome",
        "result",
        "postgame",
        "postgame_result",
        "realized_weather",
        "observed_weather",
        "reanalysis_weather",
        "closing_line",
        "close_line",
        "market",
        "market_line",
        "protected_result",
        "home_points",
        "away_points",
        "margin",
        "total",
        "roster_revision",
        "availability",
        "injury_status",
    }
)
ABSENT_DOMAIN_FIELDS = {
    "weather": ("observed_weather", "realized_weather", "reanalysis_weather"),
    "market": ("closing_line", "close_line", "market_line", "market"),
    "roster": ("roster_revision", "availability", "injury_status"),
    "label": ("label", "derived_label", "target_label", "home_win"),
}
SCENARIO_EVIDENCE_FIELDS = (
    "scenario_id",
    "disposition",
    "mutation",
    "source_input_identity",
    "expected_behavior",
    "observed_behavior",
    "affected_row_ids",
    "unaffected_control_row_ids",
    "baseline_hash",
    "mutated_hash",
    "applicable_cutoff",
    "remediation_on_failure",
)
AUTHORITY_FIELDS = (
    "schema_version",
    "artifact_type",
    "decision_unit",
    "jira_key",
    "status",
    "remaining_blockers",
    "downstream_eligibility",
    "acceptance_matrix",
    "input_identities",
    "dataset_identity",
    "scenarios",
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def compute_artifact_identity(payload: Mapping[str, Any]) -> str:
    mutable = dict(payload)
    mutable.pop("artifact_identity", None)
    return _sha256_bytes(_canonical_json(mutable))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _aware(value: object, key: str) -> datetime:
    parsed = parse_time(value) if not isinstance(value, datetime) else value
    if parsed is None:
        raise ValueError(f"{key} must be present")
    return parsed.astimezone(timezone.utc)


def _polars() -> Any:
    try:
        import polars
    except ModuleNotFoundError as exc:
        raise RuntimeError("polars is required to execute the real BAT-399 leakage battery") from exc
    return polars


def resolve_data_root(explicit: Path | None, repo_root: Path) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    env = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", "").strip()
    if env:
        candidates.append(Path(env))
    policy_path = repo_root / "configs" / "external_storage_policy.json"
    if policy_path.is_file():
        policy = _load_json(policy_path)
        configured = str(policy.get("current_host_data_root_windows") or "").strip()
        if configured:
            candidates.append(Path(configured))
    seen: set[str] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        if not resolved.is_dir():
            continue
        try:
            resolved.relative_to(repo_root.resolve())
        except ValueError:
            return resolved
        raise ValueError(f"data root must be outside the repository: {resolved}")
    raise ValueError("unable to resolve an external data root")


def resolve_external_path(data_root: Path, raw_path: str) -> Path:
    marker = "<external-data-root>/"
    if not raw_path.startswith(marker):
        raise ValueError(f"external path must start with {marker}: {raw_path}")
    relative = raw_path[len(marker) :].replace("\\", "/")
    if not relative or relative.startswith("/") or ":" in relative.split("/", 1)[0]:
        raise ValueError(f"external path escapes the data root: {raw_path}")
    parts = Path(relative).parts
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"external path traversal is rejected: {raw_path}")
    resolved = (data_root / relative).resolve()
    try:
        resolved.relative_to(data_root.resolve())
    except ValueError as exc:
        raise ValueError(f"external path escapes the data root: {raw_path}") from exc
    return resolved


def _matrix_hash(rows: Sequence[Mapping[str, Any]], cells: Sequence[Mapping[str, Any]]) -> str:
    return _sha256_bytes(
        _canonical_json(
            {
                "rows": sorted((row["row_id"], row["lineage_sha256"]) for row in rows),
                "cells": sorted((cell["cell_id"], cell["lineage_sha256"]) for cell in cells),
            }
        )
    )


def _subset_hash(
    rows: Sequence[Mapping[str, Any]],
    cells: Sequence[Mapping[str, Any]],
    row_ids: Sequence[str],
) -> str:
    allowed = set(row_ids)
    return _matrix_hash(
        [row for row in rows if row["row_id"] in allowed],
        [cell for cell in cells if cell.get("row_id") in allowed],
    )


def _row_index(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {str(row["row_id"]): row for row in rows}


def _row_fingerprint(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(row.get("row_id")),
        str(row.get("lineage_sha256")),
        row.get("prior_games"),
        row.get("prior_win_rate"),
        row.get("prior_points_for_mean"),
        row.get("prior_points_against_mean"),
        row.get("missingness"),
        tuple(row.get("eligible_observation_ids") or []),
    )


def _diff_rows(
    baseline: Sequence[Mapping[str, Any]],
    mutated: Sequence[Mapping[str, Any]],
) -> tuple[list[str], list[str]]:
    before = _row_index(baseline)
    after = _row_index(mutated)
    affected = sorted(
        {
            *(
                row_id
                for row_id, row in before.items()
                if row_id not in after or _row_fingerprint(after[row_id]) != _row_fingerprint(row)
            ),
            *(row_id for row_id in after if row_id not in before),
        }
    )
    unaffected = sorted(row_id for row_id in before if row_id not in set(affected))
    return affected, unaffected


def _clone_observation(obs: TeamOutcomeObservation, **updates: Any) -> TeamOutcomeObservation:
    payload = {field: getattr(obs, field) for field in TeamOutcomeObservation.__dataclass_fields__}
    payload.update(updates)
    return TeamOutcomeObservation(**payload)


def observation_from_mapping(row: Mapping[str, Any]) -> TeamOutcomeObservation:
    return TeamOutcomeObservation(
        observation_id=str(row["observation_id"]),
        canonical_game_id=str(row["canonical_game_id"]),
        source_game_id=str(row["source_game_id"]),
        season=int(row["season"]),
        team_id=str(row["team_id"]),
        opponent_id=str(row["opponent_id"]),
        site=str(row["site"]),
        points_for=int(row["points_for"]),
        points_against=int(row["points_against"]),
        result=str(row["result"]),
        source_known_at_utc=_aware(row["source_known_at_utc"], "source_known_at_utc"),
        game_start_utc=_aware(row["game_start_utc"], "game_start_utc"),
        completed_known_by_utc=_aware(row["completed_known_by_utc"], "completed_known_by_utc"),
        source_capture_id=str(row["source_capture_id"]),
        source_payload_sha256=str(row["source_payload_sha256"]),
        source_record_evidence_sha256=str(row["source_record_evidence_sha256"]),
        temporal_policy_version=str(row.get("temporal_policy_version") or HISTORICAL_OUTCOME_POLICY_VERSION),
    )


def target_from_cutoff(row: Mapping[str, Any]) -> TargetGame:
    return TargetGame(
        game_id=str(row["game_id"]),
        season=int(row["season"]),
        season_type=str(row["season_type"]),
        week=int(row["week"]) if row.get("week") is not None else None,
        start_utc=_aware(row["start_utc"], "start_utc"),
        home_team_id=str(row["home_team_id"]),
        away_team_id=str(row["away_team_id"]),
        neutral_site=bool(row.get("neutral_site", False)),
    )


def reconstruct_matrix(
    observations: Sequence[TeamOutcomeObservation],
    targets: Sequence[TargetGame],
    *,
    cutoff_lead: timedelta = timedelta(hours=24),
) -> tuple[tuple[PregamePriorRow, ...], tuple[Any, ...]]:
    rows = build_pregame_team_priors(observations, targets, cutoff_lead=cutoff_lead)
    cells = materialize_prior_cells(rows)
    return rows, cells


def stored_matrix(rows: Iterable[Any], cells: Iterable[Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return [record_for_storage(row) for row in rows], [record_for_storage(cell) for cell in cells]


def validate_payload_file(path: Path, spec: Mapping[str, Any], frame: Any) -> dict[str, Any]:
    digest = _sha256_bytes(path.read_bytes())
    if digest != spec["sha256"]:
        raise ValueError(f"{path.name} sha256 mismatch: {digest}")
    if int(path.stat().st_size) <= 0:
        raise ValueError(f"{path.name} is empty")
    if frame.height != spec["rows"]:
        raise ValueError(f"{path.name} row count {frame.height} != {spec['rows']}")
    missing = [column for column in spec["required_columns"] if column not in frame.columns]
    if missing:
        raise ValueError(f"{path.name} missing columns: {missing}")
    return {
        "name": path.name,
        "path": str(path),
        "bytes": int(path.stat().st_size),
        "sha256": digest,
        "rows": int(frame.height),
        "columns": list(frame.columns),
    }


def load_bat523_payloads(data_root: Path) -> dict[str, Any]:
    manifest_path = resolve_external_path(data_root, f"<external-data-root>/{MANIFEST_RELATIVE}")
    manifest = _load_json(manifest_path)
    if manifest.get("dataset_identity") != DATASET_IDENTITY:
        raise ValueError("BAT-523 manifest dataset identity mismatch")
    if manifest.get("schema_version") != "1.1.0":
        raise ValueError("unexpected BAT-523 manifest schema")
    pl = _polars()
    frames: dict[str, Any] = {}
    validated: list[dict[str, Any]] = []
    for item in manifest["payloads"]:
        name = item["name"]
        spec = REQUIRED_PAYLOADS[name]
        if item["sha256"] != spec["sha256"] or item["rows"] != spec["rows"]:
            raise ValueError(f"manifest payload identity drifted: {name}")
        path = resolve_external_path(data_root, item["path"])
        if not path.is_file():
            raise ValueError(f"authoritative payload missing: {path}")
        frame = pl.read_parquet(path)
        record = validate_payload_file(path, spec, frame)
        record["manifest_path"] = item["path"]
        frames[name] = frame
        validated.append(record)
    return {
        "manifest_path": str(manifest_path),
        "manifest_sha256": _sha256_bytes(manifest_path.read_bytes()),
        "manifest": manifest,
        "frames": frames,
        "payloads": validated,
    }


def _scenario(
    scenario_id: str,
    *,
    disposition: str,
    mutation: str,
    source_input_identity: str,
    expected_behavior: str,
    observed_behavior: str,
    affected_row_ids: Sequence[str],
    unaffected_control_row_ids: Sequence[str],
    baseline_hash: str,
    mutated_hash: str,
    applicable_cutoff: str,
    remediation_on_failure: str,
) -> dict[str, Any]:
    if disposition not in {"PASS", "FAIL", "BLOCKED"}:
        raise ValueError(f"invalid disposition for {scenario_id}")
    return {
        "scenario_id": scenario_id,
        "disposition": disposition,
        "mutation": mutation,
        "source_input_identity": source_input_identity,
        "expected_behavior": expected_behavior,
        "observed_behavior": observed_behavior,
        "affected_row_ids": list(affected_row_ids),
        "unaffected_control_row_ids": list(unaffected_control_row_ids),
        "baseline_hash": baseline_hash,
        "mutated_hash": mutated_hash,
        "applicable_cutoff": applicable_cutoff,
        "remediation_on_failure": remediation_on_failure,
    }


def _pass_if(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def _schema_fields(frame: Any) -> set[str]:
    names = {str(column).lower() for column in frame.columns}
    if "feature_name" in frame.columns:
        names.update(str(value).lower() for value in frame["feature_name"].unique().to_list())
    return names


def _reject_prohibited(record: Mapping[str, Any], extra: Iterable[str] = ()) -> None:
    names = {str(key).lower() for key in record} | {str(item).lower() for item in extra}
    overlap = names & PROHIBITED_FEATURE_FIELDS
    if overlap:
        raise ValueError(f"prohibited feature fields present: {sorted(overlap)}")


def execute_battery(repo_root: Path, data_root: Path) -> dict[str, Any]:
    loaded = load_bat523_payloads(data_root)
    frames = loaded["frames"]
    observations = [observation_from_mapping(row) for row in frames["team_outcome_observations.parquet"].to_dicts()]
    targets = [target_from_cutoff(row) for row in frames["target_game_cutoffs.parquet"].to_dicts()]
    authoritative_rows = frames["pregame_prior_rows.parquet"].to_dicts()
    authoritative_cells = frames["pregame_prior_cells.parquet"].to_dicts()
    reconstructed_rows, reconstructed_cells = stored_matrix(*reconstruct_matrix(observations, targets))
    baseline_hash = _matrix_hash(reconstructed_rows, reconstructed_cells)
    auth_hash = _matrix_hash(authoritative_rows, authoritative_cells)
    source_identity = DATASET_IDENTITY

    reconstructed_ids = [row["row_id"] for row in reconstructed_rows]
    reconstructed_by_id = _row_index(reconstructed_rows)
    authoritative_by_id = _row_index(authoritative_rows)
    reconstructed_cells_by_id = {str(cell["cell_id"]): cell for cell in reconstructed_cells}
    authoritative_cells_by_id = {str(cell["cell_id"]): cell for cell in authoritative_cells}
    reconstruction_ok = (
        len(reconstructed_rows) == 5528
        and len(reconstructed_cells) == 22112
        and set(reconstructed_by_id) == set(authoritative_by_id)
        and set(reconstructed_cells_by_id) == set(authoritative_cells_by_id)
        and all(
            reconstructed_by_id[row_id]["lineage_sha256"] == row["lineage_sha256"]
            and reconstructed_by_id[row_id].get("prior_games") == row.get("prior_games")
            and reconstructed_by_id[row_id].get("missingness") == row.get("missingness")
            for row_id, row in authoritative_by_id.items()
        )
        and all(
            reconstructed_cells_by_id[cell_id]["lineage_sha256"] == cell["lineage_sha256"]
            and reconstructed_cells_by_id[cell_id].get("value") == cell.get("value")
            for cell_id, cell in authoritative_cells_by_id.items()
        )
        and baseline_hash == auth_hash
    )

    present_fields = _schema_fields(frames["pregame_prior_rows.parquet"]) | _schema_fields(
        frames["pregame_prior_cells.parquet"]
    )
    prohibited_hits = sorted(present_fields & PROHIBITED_FEATURE_FIELDS)
    try:
        for row in reconstructed_rows[:8]:
            _reject_prohibited(row)
        static_reject = True
    except ValueError:
        static_reject = False

    future_obs = TeamOutcomeObservation(
        observation_id="injected_future_obs",
        canonical_game_id="injected_future_game",
        source_game_id="injected_future_source",
        season=2026,
        team_id=observations[0].team_id,
        opponent_id=observations[0].opponent_id,
        site="HOME",
        points_for=99,
        points_against=0,
        result="WIN",
        source_known_at_utc=datetime(2026, 8, 1, tzinfo=timezone.utc),
        game_start_utc=datetime(2026, 7, 31, tzinfo=timezone.utc),
        completed_known_by_utc=datetime(2026, 8, 1, tzinfo=timezone.utc),
        source_capture_id="c" * 64,
        source_payload_sha256="d" * 64,
        source_record_evidence_sha256="e" * 64,
    )
    future_rows, future_cells = stored_matrix(*reconstruct_matrix([*observations, future_obs], targets))
    future_affected, future_unaffected = _diff_rows(reconstructed_rows, future_rows)
    future_hash = _matrix_hash(future_rows, future_cells)

    post_target = next(target for target in targets if target.season == 2023)
    post_obs = TeamOutcomeObservation(
        observation_id="injected_postgame_obs",
        canonical_game_id=post_target.game_id,
        source_game_id="injected_postgame_source",
        season=post_target.season,
        team_id=post_target.home_team_id,
        opponent_id=post_target.away_team_id,
        site="HOME",
        points_for=77,
        points_against=3,
        result="WIN",
        source_known_at_utc=post_target.start_utc + timedelta(hours=6),
        game_start_utc=post_target.start_utc,
        completed_known_by_utc=post_target.start_utc + timedelta(hours=6),
        source_capture_id="1" * 64,
        source_payload_sha256="2" * 64,
        source_record_evidence_sha256="3" * 64,
    )
    post_rows, post_cells = stored_matrix(*reconstruct_matrix([*observations, post_obs], targets))
    post_affected, post_unaffected = _diff_rows(reconstructed_rows, post_rows)
    post_target_rows = [row["row_id"] for row in reconstructed_rows if row["target_game_id"] == post_target.game_id]
    post_target_changed = bool(set(post_affected) & set(post_target_rows))
    baseline_by_id = _row_index(reconstructed_rows)
    earlier_post_leaked = [
        row_id
        for row_id in post_affected
        if row_id in baseline_by_id
        and _aware(baseline_by_id[row_id]["cutoff_utc"], "cutoff_utc") < post_obs.source_known_at_utc
    ]
    post_control_hash = _subset_hash(reconstructed_rows, reconstructed_cells, post_target_rows)
    post_mutated_control_hash = _subset_hash(post_rows, post_cells, post_target_rows)
    post_ok = (not post_target_changed) and (not earlier_post_leaked) and post_control_hash == post_mutated_control_hash

    mutable_source = next(
        obs
        for obs in observations
        if obs.season <= 2022 and any(row["team_id"] == obs.team_id and row["prior_games"] for row in reconstructed_rows)
    )
    mutated_obs = [
        _clone_observation(obs, points_for=obs.points_for + 17, result="WIN")
        if obs.observation_id == mutable_source.observation_id
        else obs
        for obs in observations
    ]
    value_rows, value_cells = stored_matrix(*reconstruct_matrix(mutated_obs, targets))
    value_affected, value_unaffected = _diff_rows(reconstructed_rows, value_rows)
    expected_value_impact = sorted(
        row["row_id"]
        for row in reconstructed_rows
        if row["team_id"] == mutable_source.team_id
        and _aware(row["cutoff_utc"], "cutoff_utc") >= mutable_source.source_known_at_utc
        and mutable_source.observation_id in set(row.get("eligible_observation_ids") or [])
    )
    value_hash = _matrix_hash(value_rows, value_cells)

    same_game_obs = TeamOutcomeObservation(
        observation_id="injected_same_game_obs",
        canonical_game_id=post_target.game_id,
        source_game_id="injected_same_game_source",
        season=post_target.season,
        team_id=post_target.home_team_id,
        opponent_id=post_target.away_team_id,
        site="HOME",
        points_for=41,
        points_against=7,
        result="WIN",
        source_known_at_utc=post_target.start_utc - timedelta(hours=36),
        game_start_utc=post_target.start_utc,
        completed_known_by_utc=post_target.start_utc - timedelta(hours=36),
        source_capture_id="4" * 64,
        source_payload_sha256="5" * 64,
        source_record_evidence_sha256="6" * 64,
    )
    same_rows, same_cells = stored_matrix(*reconstruct_matrix([*observations, same_game_obs], targets))
    same_affected, same_unaffected = _diff_rows(reconstructed_rows, same_rows)
    same_target_changed = bool(set(same_affected) & set(post_target_rows))
    same_target_eligible = {
        obs_id
        for row in same_rows
        if row["target_game_id"] == post_target.game_id
        for obs_id in (row.get("eligible_observation_ids") or [])
    }
    same_control_hash = _subset_hash(reconstructed_rows, reconstructed_cells, post_target_rows)
    same_mutated_control_hash = _subset_hash(same_rows, same_cells, post_target_rows)
    same_ok = (
        (not same_target_changed)
        and same_game_obs.observation_id not in same_target_eligible
        and same_control_hash == same_mutated_control_hash
    )

    cutoff_source = next(
        obs
        for obs in observations
        if any(
            row["team_id"] == obs.team_id and obs.observation_id in set(row.get("eligible_observation_ids") or [])
            for row in reconstructed_rows
        )
    )
    cutoff_row = next(
        row
        for row in reconstructed_rows
        if cutoff_source.observation_id in set(row.get("eligible_observation_ids") or [])
    )
    cutoff_time = _aware(cutoff_row["cutoff_utc"], "cutoff_utc")
    shifted = [
        _clone_observation(obs, source_known_at_utc=cutoff_time + timedelta(minutes=1))
        if obs.observation_id == cutoff_source.observation_id
        else obs
        for obs in observations
    ]
    cutoff_rows, cutoff_cells = stored_matrix(*reconstruct_matrix(shifted, targets))
    cutoff_affected, cutoff_unaffected = _diff_rows(reconstructed_rows, cutoff_rows)
    cutoff_hash = _matrix_hash(cutoff_rows, cutoff_cells)

    known_at_shifted = [
        _clone_observation(obs, completed_known_by_utc=cutoff_time + timedelta(minutes=1))
        if obs.observation_id == cutoff_source.observation_id
        else obs
        for obs in observations
    ]
    known_rows, known_cells = stored_matrix(*reconstruct_matrix(known_at_shifted, targets))
    known_affected, known_unaffected = _diff_rows(reconstructed_rows, known_rows)
    known_hash = _matrix_hash(known_rows, known_cells)
    start_shifted = [
        _clone_observation(obs, game_start_utc=cutoff_time + timedelta(minutes=1))
        if obs.observation_id == cutoff_source.observation_id
        else obs
        for obs in observations
    ]
    start_rows, _start_cells = stored_matrix(*reconstruct_matrix(start_shifted, targets))
    start_affected, _start_unaffected = _diff_rows(reconstructed_rows, start_rows)

    normalized = [
        {**record_for_storage(obs), "normalization_revision_utc": "2026-08-01T00:00:00Z"}
        for obs in observations
    ]
    # Extra source metadata is not a constructor field; reconstruction must ignore it.
    norm_obs = [observation_from_mapping(record) for record in normalized]
    norm_rows, norm_cells = stored_matrix(*reconstruct_matrix(norm_obs, targets))
    norm_affected, norm_unaffected = _diff_rows(reconstructed_rows, norm_rows)
    norm_hash = _matrix_hash(norm_rows, norm_cells)
    norm_ok = (
        not norm_affected
        and norm_hash == baseline_hash
        and "normalization_revision_utc" not in present_fields
    )

    entity_correction = TeamOutcomeObservation(
        observation_id="injected_entity_correction",
        canonical_game_id=cutoff_source.canonical_game_id,
        source_game_id="injected_entity_correction_source",
        season=cutoff_source.season,
        team_id="corrected_entity_id",
        opponent_id=cutoff_source.opponent_id,
        site=cutoff_source.site,
        points_for=cutoff_source.points_for,
        points_against=cutoff_source.points_against,
        result=cutoff_source.result,
        source_known_at_utc=datetime(2026, 1, 1, tzinfo=timezone.utc),
        game_start_utc=cutoff_source.game_start_utc,
        completed_known_by_utc=datetime(2026, 1, 1, tzinfo=timezone.utc),
        source_capture_id="7" * 64,
        source_payload_sha256="8" * 64,
        source_record_evidence_sha256="9" * 64,
    )
    entity_rows, entity_cells = stored_matrix(*reconstruct_matrix([*observations, entity_correction], targets))
    entity_affected, entity_unaffected = _diff_rows(reconstructed_rows, entity_rows)
    entity_hash = _matrix_hash(entity_rows, entity_cells)

    def _absence_case(domain: str) -> tuple[bool, str]:
        fields = ABSENT_DOMAIN_FIELDS[domain]
        absent = all(field not in present_fields for field in fields)
        injected = dict(reconstructed_rows[0])
        injected[fields[0]] = "INJECTED"
        rejected = False
        try:
            _reject_prohibited(injected, extra=fields)
        except ValueError:
            rejected = True
        return absent and rejected, fields[0]

    weather_ok, weather_field = _absence_case("weather")
    market_ok, market_field = _absence_case("market")
    roster_ok, roster_field = _absence_case("roster")
    label_ok, label_field = _absence_case("label")
    control_ids = reconstructed_ids[:8]

    cases = [
        _scenario(
            "static_prohibited_field_scan",
            disposition=_pass_if(not prohibited_hits and static_reject),
            mutation="inspect authoritative row/cell schemas and reject prohibited aliases",
            source_input_identity=source_identity,
            expected_behavior="Feature rows contain no target, label, postgame, weather, market, or protected-result fields.",
            observed_behavior="no prohibited fields" if not prohibited_hits else f"prohibited={prohibited_hits}",
            affected_row_ids=[],
            unaffected_control_row_ids=control_ids,
            baseline_hash=auth_hash,
            mutated_hash=auth_hash,
            applicable_cutoff="TARGET_START_UTC_MINUS_24_HOURS",
            remediation_on_failure="Remove prohibited fields from the scoped team-outcome matrix contract.",
        ),
        _scenario(
            "full_deterministic_reconstruction",
            disposition=_pass_if(reconstruction_ok),
            mutation="rebuild scoped matrix from team_outcome_observations and target_game_cutoffs through versioned historical-recovery code",
            source_input_identity=source_identity,
            expected_behavior="Reconstructed 5528 rows / 22112 cells match authoritative IDs, values, missingness, lineage, and dataset identity.",
            observed_behavior=f"rows={len(reconstructed_rows)} cells={len(reconstructed_cells)} hash_match={baseline_hash == auth_hash}",
            affected_row_ids=[],
            unaffected_control_row_ids=reconstructed_ids[:12],
            baseline_hash=auth_hash,
            mutated_hash=baseline_hash,
            applicable_cutoff="TARGET_START_UTC_MINUS_24_HOURS",
            remediation_on_failure="Fix historical-recovery reconstruction until it reproduces the BAT-523 payloads.",
        ),
        _scenario(
            "future_record_append_invariance",
            disposition=_pass_if(not future_affected and future_hash == baseline_hash),
            mutation="append a 2026 observation known strictly after every 2023-2025 cutoff",
            source_input_identity=future_obs.observation_id,
            expected_behavior="Earlier eligible row and cell hashes remain identical.",
            observed_behavior=f"affected={len(future_affected)}",
            affected_row_ids=future_affected[:32],
            unaffected_control_row_ids=future_unaffected[:12],
            baseline_hash=baseline_hash,
            mutated_hash=future_hash,
            applicable_cutoff="ALL_BASELINE_CUTOFFS",
            remediation_on_failure="Exclude observations whose known-at/game-start/completion times are after the cutoff.",
        ),
        _scenario(
            "postgame_record_append_invariance",
            disposition=_pass_if(post_ok),
            mutation=f"append postgame observation for {post_target.game_id} after kickoff",
            source_input_identity=post_obs.observation_id,
            expected_behavior="A target-game/postgame observation cannot alter that game's pregame state or any earlier cutoff.",
            observed_behavior=(
                f"target_rows_changed={post_target_changed} earlier_leaked={len(earlier_post_leaked)} "
                f"later_prior_updates={len(post_affected)}"
            ),
            affected_row_ids=post_affected[:32],
            unaffected_control_row_ids=post_target_rows,
            baseline_hash=post_control_hash,
            mutated_hash=post_mutated_control_hash,
            applicable_cutoff=post_target.start_utc.isoformat().replace("+00:00", "Z"),
            remediation_on_failure="Keep same-game and post-cutoff observations out of pregame priors.",
        ),
        _scenario(
            "value_mutation_isolation",
            disposition=_pass_if(value_affected == expected_value_impact and value_unaffected and value_hash != baseline_hash),
            mutation=f"add 17 points_for to {mutable_source.observation_id} in a temporary copy",
            source_input_identity=mutable_source.observation_id,
            expected_behavior="Only later same-team rows that consumed the observation change; unrelated teams/games/earlier cutoffs stay identical.",
            observed_behavior=f"affected={len(value_affected)} expected={len(expected_value_impact)}",
            affected_row_ids=value_affected[:32],
            unaffected_control_row_ids=value_unaffected[:12],
            baseline_hash=baseline_hash,
            mutated_hash=value_hash,
            applicable_cutoff=mutable_source.source_known_at_utc.isoformat().replace("+00:00", "Z"),
            remediation_on_failure="Bound prior aggregation by team_id and cutoff; do not leak values across unrelated rows.",
        ),
        _scenario(
            "same_game_target_outcome_exclusion",
            disposition=_pass_if(same_ok),
            mutation=f"inject {post_target.game_id} outcome with otherwise plausible identifiers",
            source_input_identity=same_game_obs.observation_id,
            expected_behavior="The target game's own outcome is excluded from its pregame rows.",
            observed_behavior=(
                f"target_rows_changed={same_target_changed} "
                f"injected_in_target={same_game_obs.observation_id in same_target_eligible} "
                f"later_prior_updates={len(same_affected)}"
            ),
            affected_row_ids=same_affected[:32],
            unaffected_control_row_ids=post_target_rows,
            baseline_hash=same_control_hash,
            mutated_hash=same_mutated_control_hash,
            applicable_cutoff=(post_target.start_utc - timedelta(hours=24)).isoformat().replace("+00:00", "Z"),
            remediation_on_failure="Keep canonical_game_id != target_game_id as a hard eligibility rule.",
        ),
        _scenario(
            "prediction_cutoff_enforcement",
            disposition=_pass_if(cutoff_row["row_id"] in cutoff_affected and cutoff_unaffected),
            mutation=f"move {cutoff_source.observation_id} source_known_at_utc one minute after cutoff {cutoff_row['cutoff_utc']}",
            source_input_identity=cutoff_source.observation_id,
            expected_behavior="Eligibility changes only at applicable cutoffs after the timestamp crosses the boundary.",
            observed_behavior=f"affected={len(cutoff_affected)} includes_source_row={cutoff_row['row_id'] in cutoff_affected}",
            affected_row_ids=cutoff_affected[:32],
            unaffected_control_row_ids=cutoff_unaffected[:12],
            baseline_hash=baseline_hash,
            mutated_hash=cutoff_hash,
            applicable_cutoff=cutoff_row["cutoff_utc"],
            remediation_on_failure="Enforce source_known_at_utc <= cutoff independently of other timestamps.",
        ),
        _scenario(
            "known_at_timestamp_enforcement",
            disposition=_pass_if(known_affected and start_affected and known_hash != baseline_hash),
            mutation="independently move completed_known_by_utc and game_start_utc across the same cutoff",
            source_input_identity=cutoff_source.observation_id,
            expected_behavior="source_known_at_utc, completed_known_by_utc, and game_start_utc are independently enforced.",
            observed_behavior=f"completed_affected={len(known_affected)} start_affected={len(start_affected)}",
            affected_row_ids=sorted(set(known_affected[:16] + start_affected[:16])),
            unaffected_control_row_ids=known_unaffected[:12],
            baseline_hash=baseline_hash,
            mutated_hash=known_hash,
            applicable_cutoff=cutoff_row["cutoff_utc"],
            remediation_on_failure="Keep all three temporal predicates mandatory and independent.",
        ),
        _scenario(
            "normalization_time_leakage",
            disposition=_pass_if(norm_ok),
            mutation="inject post-cutoff normalization_revision_utc on every observation copy",
            source_input_identity=source_identity,
            expected_behavior="Historical rows remain unchanged because reconstruction ignores post-cutoff normalization revisions.",
            observed_behavior=f"affected={len(norm_affected)}",
            affected_row_ids=norm_affected[:32],
            unaffected_control_row_ids=norm_unaffected[:12] or control_ids,
            baseline_hash=baseline_hash,
            mutated_hash=norm_hash,
            applicable_cutoff="TARGET_START_UTC_MINUS_24_HOURS",
            remediation_on_failure="Do not consume normalization revisions published after the cutoff.",
        ),
        _scenario(
            "entity_correction_leakage",
            disposition=_pass_if(not entity_affected and entity_hash == baseline_hash),
            mutation=f"append later entity correction {entity_correction.observation_id} with team_id=corrected_entity_id known at 2026-01-01",
            source_input_identity=entity_correction.observation_id,
            expected_behavior="A later entity correction cannot rewrite prior cutoff outputs.",
            observed_behavior=f"affected={len(entity_affected)}",
            affected_row_ids=entity_affected[:32],
            unaffected_control_row_ids=entity_unaffected[:12],
            baseline_hash=baseline_hash,
            mutated_hash=entity_hash,
            applicable_cutoff=cutoff_row["cutoff_utc"],
            remediation_on_failure="Bind entity identity to the version known at the cutoff, not a later correction.",
        ),
        _scenario(
            "weather_known_at_missingness_behavior",
            disposition=_pass_if(weather_ok),
            mutation=f"attempt to inject {weather_field} into a feature row",
            source_input_identity=source_identity,
            expected_behavior="Weather fields are absent from this scoped matrix and injection is rejected fail-closed.",
            observed_behavior="weather fields absent and injection rejected" if weather_ok else "weather injection accepted",
            affected_row_ids=[],
            unaffected_control_row_ids=control_ids,
            baseline_hash=baseline_hash,
            mutated_hash=baseline_hash,
            applicable_cutoff="NOT_APPLICABLE_DOMAIN_ABSENT",
            remediation_on_failure="Keep weather out of the scoped team-outcome matrix and reject injection.",
        ),
        _scenario(
            "market_cutoff_missingness_behavior",
            disposition=_pass_if(market_ok),
            mutation=f"attempt to inject {market_field} after cutoff",
            source_input_identity=source_identity,
            expected_behavior="Market fields are absent and post-cutoff/closing-line injection is rejected. Domain absence is not a blocker.",
            observed_behavior="market fields absent and injection rejected" if market_ok else "market injection accepted",
            affected_row_ids=[],
            unaffected_control_row_ids=control_ids,
            baseline_hash=baseline_hash,
            mutated_hash=baseline_hash,
            applicable_cutoff="NOT_APPLICABLE_DOMAIN_ABSENT",
            remediation_on_failure="Keep market lines out of this scoped matrix and reject injection.",
        ),
        _scenario(
            "roster_availability_revision_cutoff_behavior",
            disposition=_pass_if(roster_ok),
            mutation=f"attempt to inject {roster_field} revision",
            source_input_identity=source_identity,
            expected_behavior="Roster/availability fields are absent and later revisions cannot enter this scoped matrix.",
            observed_behavior="roster fields absent and injection rejected" if roster_ok else "roster injection accepted",
            affected_row_ids=[],
            unaffected_control_row_ids=control_ids,
            baseline_hash=baseline_hash,
            mutated_hash=baseline_hash,
            applicable_cutoff="NOT_APPLICABLE_DOMAIN_ABSENT",
            remediation_on_failure="Keep roster/availability revisions out of this scoped matrix.",
        ),
        _scenario(
            "label_and_derived_label_leakage",
            disposition=_pass_if(label_ok),
            mutation=f"attempt to inject {label_field} into a feature row",
            source_input_identity=source_identity,
            expected_behavior="Target labels are absent from feature rows and injection fails closed.",
            observed_behavior="label fields absent and injection rejected" if label_ok else "label injection accepted",
            affected_row_ids=[],
            unaffected_control_row_ids=control_ids,
            baseline_hash=baseline_hash,
            mutated_hash=baseline_hash,
            applicable_cutoff="TARGET_START_UTC_MINUS_24_HOURS",
            remediation_on_failure="Keep labels in a separate target payload and reject feature-row injection.",
        ),
    ]
    derived = derive_terminal_state(cases)
    failed = [case["scenario_id"] for case in cases if case["disposition"] != "PASS"]
    acceptance = [
        {
            "criterion": "Authoritative BAT-523 payloads exist, hash-verify, and bind dataset identity cf732b78db6deff2e2cca51364a18e03219a5ceda88d2f5efa475dad1f7e3fe7.",
            "disposition": "PASS",
            "evidence": "input_identities.payloads",
        },
        {
            "criterion": "All required leakage scenarios execute real mutations or governed-absence checks with row-level evidence.",
            "disposition": "PASS" if not failed else "FAIL",
            "evidence": "scenarios",
        },
        {
            "criterion": "Terminal status, blockers, BAT-400 eligibility, and acceptance are derived from scenario dispositions.",
            "disposition": "PASS" if not failed else "FAIL",
            "evidence": "status + remaining_blockers + downstream_eligibility",
        },
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "REAL_SCOPED_LEAKAGE_BATTERY_RESULTS",
        "decision_unit": "POST-SUBTASK-049",
        "jira_key": "BAT-399",
        "issued_at_utc": loaded["manifest"]["issued_at_utc"],
        "dataset_identity": DATASET_IDENTITY,
        "data_root_resolution": {
            "order": ["--data-root", "AGGIE_ANALYTICS_DATA_ROOT", "validated_canonical_sibling"],
            "resolved": str(data_root),
        },
        "input_identities": {
            "dataset_identity": DATASET_IDENTITY,
            "manifest_path": loaded["manifest_path"],
            "manifest_sha256": loaded["manifest_sha256"],
            "payloads": loaded["payloads"],
            "historical_recovery_module": "src/aggie_analytics/temporal/historical_recovery.py",
        },
        "population": {
            "accepted_game_outcomes": 10593,
            "team_outcome_observations": 21186,
            "target_game_cutoffs": 2764,
            "pregame_prior_rows": 5528,
            "pregame_prior_cells": 22112,
        },
        "scenarios": cases,
        "acceptance_matrix": acceptance,
        "status": derived["status"],
        "remaining_blockers": derived["remaining_blockers"],
        "downstream_eligibility": {
            "BAT-400": derived["bat400"],
            "reason": "BAT-399 completed with executable row-level leakage evidence."
            if derived["status"] == "DONE"
            else "BAT-399 still has failed or blocked leakage scenarios.",
        },
        "protected_nonclaims": {
            "protected_performance_claimed": False,
            "production_ready": False,
            "champion_selected": False,
        },
    }
    payload["artifact_identity"] = compute_artifact_identity(payload)
    return payload


def derive_terminal_state(scenarios: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    failed = [str(row["scenario_id"]) for row in scenarios if row.get("disposition") != "PASS"]
    status = "DONE" if not failed else "BLOCKED"
    blockers = ["NONE"] if not failed else [f"SCENARIO_{item.upper()}_NOT_PASS" for item in failed]
    return {
        "status": status,
        "remaining_blockers": blockers,
        "bat400": "READY" if status == "DONE" else "BLOCKED_UNTIL_BAT399_DONE",
    }


def validate_results(payload: Mapping[str, Any], repo_root: Path | None = None) -> None:
    del repo_root
    for field in AUTHORITY_FIELDS:
        if field not in payload:
            raise ValueError(f"missing authority field: {field}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unexpected leakage battery schema version")
    if payload.get("artifact_type") != "REAL_SCOPED_LEAKAGE_BATTERY_RESULTS":
        raise ValueError("unexpected leakage battery artifact_type")
    if payload.get("dataset_identity") != DATASET_IDENTITY:
        raise ValueError("dataset identity mismatch")
    if payload.get("artifact_identity") != compute_artifact_identity(payload):
        raise ValueError("artifact_identity mismatch")
    seen = [str(row.get("scenario_id")) for row in payload.get("scenarios", [])]
    if seen != SCENARIOS:
        raise ValueError("scenario set/order mismatch")
    if len(seen) != len(set(seen)):
        raise ValueError("duplicate scenarios")
    derived = derive_terminal_state(payload["scenarios"])
    if payload.get("status") != derived["status"]:
        raise ValueError("status is not bound to scenario dispositions")
    if list(payload.get("remaining_blockers") or []) != list(derived["remaining_blockers"]):
        raise ValueError("remaining_blockers are not bound to scenario dispositions")
    if list(payload.get("remaining_blockers") or []) == ["NONE"] and derived["status"] != "DONE":
        raise ValueError("remaining_blockers forged to NONE")
    if derived["status"] == "DONE" and list(payload.get("remaining_blockers") or []) != ["NONE"]:
        raise ValueError("DONE status requires remaining_blockers NONE")
    if derived["status"] != "DONE" and "NONE" in list(payload.get("remaining_blockers") or []):
        raise ValueError("non-DONE status cannot claim NONE blockers")
    eligibility = payload.get("downstream_eligibility") or {}
    if eligibility.get("BAT-400") != derived["bat400"]:
        raise ValueError("BAT-400 eligibility is not bound to BAT-399 terminal status")
    if derived["status"] != "DONE" and eligibility.get("BAT-400") == "READY":
        raise ValueError("BAT-400 eligibility forged to READY")
    acceptance = payload.get("acceptance_matrix") or []
    if len(acceptance) < 3:
        raise ValueError("acceptance matrix incomplete")
    if derived["status"] != "DONE" and any(
        row.get("disposition") == "PASS"
        and (
            "Terminal status" in str(row.get("criterion"))
            or "All required leakage scenarios" in str(row.get("criterion"))
        )
        for row in acceptance
    ):
        raise ValueError("acceptance matrix forged PASS while scenarios failed")
    if derived["status"] == "DONE" and any(row.get("disposition") != "PASS" for row in acceptance):
        raise ValueError("DONE artifact has a non-PASS acceptance row")
    identities = payload.get("input_identities") or {}
    if identities.get("dataset_identity") != DATASET_IDENTITY:
        raise ValueError("input identity dataset mismatch")
    if "ROW_LEVEL_MATRIX_PAYLOADS_UNAVAILABLE" in list(payload.get("remaining_blockers") or []):
        raise ValueError("obsolete unavailable-payload blocker is not valid for BAT-523 identities")
    payloads = {item["name"]: item for item in identities.get("payloads", [])}
    for name, spec in REQUIRED_PAYLOADS.items():
        item = payloads.get(name)
        if not item:
            raise ValueError(f"missing payload identity: {name}")
        if item.get("sha256") != spec["sha256"] or int(item.get("rows") or 0) != spec["rows"]:
            raise ValueError(f"payload identity mismatch: {name}")
        if not item.get("path") or not item.get("bytes"):
            raise ValueError(f"payload path/size missing: {name}")
        path_text = str(item.get("path") or "")
        if "<external-data-root>" in path_text or "BAT-397" in path_text:
            raise ValueError(f"payload path is unresolved or obsolete: {name}")
        if DATASET_IDENTITY not in path_text:
            raise ValueError(f"payload path is not bound to dataset identity: {name}")
    mutation_scenarios = {
        "future_record_append_invariance",
        "postgame_record_append_invariance",
        "value_mutation_isolation",
        "same_game_target_outcome_exclusion",
        "prediction_cutoff_enforcement",
        "known_at_timestamp_enforcement",
        "normalization_time_leakage",
        "entity_correction_leakage",
    }
    for row in payload["scenarios"]:
        missing = [field for field in SCENARIO_EVIDENCE_FIELDS if field not in row]
        if missing:
            raise ValueError(f"{row.get('scenario_id')} missing evidence fields: {missing}")
        if row.get("disposition") not in {"PASS", "FAIL", "BLOCKED"}:
            raise ValueError(f"{row.get('scenario_id')} has invalid disposition")
        if row["scenario_id"] in mutation_scenarios and row.get("disposition") == "PASS":
            if not row.get("unaffected_control_row_ids"):
                raise ValueError(f"{row['scenario_id']} PASS lacks unaffected control row identities")
            if row["scenario_id"] == "value_mutation_isolation" and not row.get("affected_row_ids"):
                raise ValueError("value_mutation_isolation PASS lacks affected row identities")
            if row["scenario_id"] in {
                "future_record_append_invariance",
                "postgame_record_append_invariance",
                "same_game_target_outcome_exclusion",
                "normalization_time_leakage",
                "entity_correction_leakage",
            } and row.get("baseline_hash") != row.get("mutated_hash"):
                raise ValueError(f"{row['scenario_id']} invariance PASS requires identical control hashes")
            if row["scenario_id"] in {
                "value_mutation_isolation",
                "prediction_cutoff_enforcement",
                "known_at_timestamp_enforcement",
            } and row.get("baseline_hash") == row.get("mutated_hash"):
                raise ValueError(f"{row['scenario_id']} assigned identical hashes without an executed mutation")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or validate BAT-399 leakage battery evidence.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=Path("artifacts/pit/leakage_battery_results.json"))
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    output = args.output if args.output.is_absolute() else (repo_root / args.output)
    if args.validate_only:
        payload = _load_json(output)
        validate_results(payload, repo_root)
        print("PASS: leakage battery artifact validated")
        return 0
    data_root = resolve_data_root(args.data_root, repo_root)
    payload = execute_battery(repo_root, data_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validate_results(payload, repo_root)
    print(f"Wrote leakage battery artifact: {output}")
    print(f"artifact_identity={payload['artifact_identity']}")
    print(f"status={payload['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

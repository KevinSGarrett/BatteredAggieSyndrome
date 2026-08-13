from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
from typing import Any

from .historical_game_outcome_spine import canonical_json_bytes, dataframe_record_sha256, sha256_file, stable_hash


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("outcome-reference adapter requires the data-engineering environment") from exc
    return polars


def _write_parquet_immutable(frame: Any, path: Path) -> None:
    buffer = io.BytesIO()
    frame.write_parquet(buffer, compression="zstd", statistics=True)
    payload = buffer.getvalue()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"immutable adapter payload collision: {path}")
        return
    temporary = path.with_name(f".tmp-{os.getpid()}-{hashlib.sha256(payload).hexdigest()[:8]}")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_json_immutable(value: dict[str, Any], path: Path) -> None:
    payload = canonical_json_bytes(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"immutable adapter manifest collision: {path}")
        return
    temporary = path.with_name(
        f".tmp-{os.getpid()}-{hashlib.sha256(payload).hexdigest()[:8]}"
    )
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def materialize_adapter(
    *, data_root: Path, output_data_root: Path, repo_root: Path, contract_path: Path, issued_at_utc: str
) -> dict[str, Any]:
    pl = _polars()
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    authority = contract["authority"]
    if authority["schema_adapter_materialization"] is not True or any(
        authority[key] is not False
        for key in (
            "canonical_entity_mutation", "outcome_value_mutation", "historical_pit_admission",
            "training_admission", "protected_evaluation_admission", "production_admission",
        )
    ):
        raise ValueError("outcome-reference adapter authority is open beyond schema adaptation")
    source = contract["source"]
    manifest_path = data_root / source["spine_manifest"]
    if not manifest_path.is_file() or sha256_file(manifest_path) != source["spine_manifest_sha256"]:
        raise ValueError("historical outcome spine manifest identity drift")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["dataset_identity"] != source["spine_dataset_identity"]:
        raise ValueError("historical outcome spine dataset identity drift")
    payload = next(
        (row for row in manifest["payloads"] if row["role"] == source["completed_payload_role"]),
        None,
    )
    if payload is None or payload["sha256"] != source["completed_payload_sha256"]:
        raise ValueError("historical outcome completed payload identity drift")
    payload_path = data_root / payload["relative_path"]
    if not payload_path.is_file() or sha256_file(payload_path) != payload["sha256"]:
        raise ValueError("historical outcome completed payload bytes drift")
    field_map = contract["field_map"]
    frame = pl.read_parquet(payload_path).select(
        [pl.col(source_name).alias(target_name) for source_name, target_name in field_map.items()]
    ).sort(["season", "start_utc", "target_game_id"])
    acceptance = contract["acceptance"]
    if frame.height != acceptance["expected_rows"]:
        raise ValueError("adapter row population drift")
    if frame["target_game_id"].n_unique() != acceptance["expected_unique_game_ids"]:
        raise ValueError("adapter game identity is not unique")
    seasons = sorted(frame["season"].unique().to_list())
    if (min(seasons), max(seasons), len(seasons)) != (
        acceptance["expected_season_min"], acceptance["expected_season_max"], acceptance["expected_season_count"]
    ):
        raise ValueError("adapter season coverage drift")
    null_cells = sum(frame[name].null_count() for name in frame.columns)
    if null_cells != acceptance["expected_null_cells"]:
        raise ValueError("adapter unexpectedly contains null cells")
    module_path = Path(__file__).resolve()
    builder_path = repo_root / "tools/build_ncaa_contest_outcome_reference_adapter.py"
    record_sha256 = dataframe_record_sha256(frame)
    identity = stable_hash(
        {
            "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "module_sha256": sha256_file(module_path),
            "builder_sha256": sha256_file(builder_path),
            "source_manifest_sha256": source["spine_manifest_sha256"],
            "source_payload_sha256": source["completed_payload_sha256"],
            "record_sha256": record_sha256,
            "classification": contract["classification"],
        }
    )
    payload_path_out = output_data_root / "canonical/ncaa_contest_outcome_reference_adapter/sha256" / identity / "outcome_targets.parquet"
    _write_parquet_immutable(frame, payload_path_out)
    output = {
        "relative_path": str(payload_path_out.relative_to(output_data_root)).replace("\\", "/"),
        "rows": frame.height,
        "bytes": payload_path_out.stat().st_size,
        "sha256": sha256_file(payload_path_out),
        "record_sha256": record_sha256,
    }
    run_manifest = {
        "schema_version": contract["schema_version"],
        "artifact_type": "NCAA_CONTEST_OUTCOME_REFERENCE_SCHEMA_ADAPTER",
        "classification": contract["classification"],
        "dataset_identity": identity,
        "issued_at_utc": issued_at_utc,
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "source": source,
        "producer": {"module_sha256": sha256_file(module_path), "builder_sha256": sha256_file(builder_path)},
        "population": {
            "rows": frame.height,
            "unique_games": frame["target_game_id"].n_unique(),
            "season_min": min(seasons),
            "season_max": max(seasons),
            "season_count": len(seasons),
            "null_cells": null_cells,
            "by_season": {str(row["season"]): int(row["len"]) for row in frame.group_by("season").len().sort("season").iter_rows(named=True)},
        },
        "payload": output,
        "authority": authority,
        "nonclaims": {
            "historical_pit_admission": False,
            "protected_performance": False,
            "production_readiness": False,
            "final_historical_completeness": False,
        },
    }
    manifest_out = output_data_root / "manifests/ncaa_contest_outcome_reference_adapter/sha256" / identity / "run_manifest.json"
    _write_json_immutable(run_manifest, manifest_out)
    return {
        "dataset_identity": identity,
        "manifest_path": str(manifest_out),
        "manifest_sha256": sha256_file(manifest_out),
        "payload_path": str(payload_path_out),
        "payload_sha256": output["sha256"],
        "population": run_manifest["population"],
        "manifest": run_manifest,
    }

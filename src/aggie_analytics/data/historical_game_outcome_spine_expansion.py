"""Versioned expansion of the immutable historical game/outcome reference spine.

This module intentionally leaves the original 1963-2009 implementation unchanged.
It resolves a pinned overlay contract, reuses the already validated source loaders and
normalizer, and writes a separate content-addressed 1963-2025 candidate artifact.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from .historical_game_outcome_spine import (
    _load_registry,
    _load_sportsdataverse,
    _polars,
    _validate_contract_authority,
    canonical_json_bytes,
    dataframe_record_sha256,
    sha256_file,
    stable_hash,
)
from .historical_game_outcome_spine_expansion_support import (
    build_outputs_expansion,
    load_cfbd_expansion,
)


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(base))
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def resolve_expansion_contract(
    *, repo_root: Path, contract_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    repo_root = repo_root.resolve()
    contract_path = contract_path.resolve()
    overlay_bytes = contract_path.read_bytes()
    overlay = json.loads(overlay_bytes)
    base_relative = Path(overlay["base_contract_relative_path"])
    if base_relative.is_absolute() or ".." in base_relative.parts:
        raise ValueError("base contract path must remain repository-relative")
    base_path = (repo_root / base_relative).resolve()
    try:
        base_path.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError("base contract resolves outside the repository") from exc
    expected_base_sha256 = str(overlay["base_contract_sha256"]).lower()
    actual_base_sha256 = sha256_file(base_path)
    if actual_base_sha256 != expected_base_sha256:
        raise ValueError(
            f"base historical outcome contract drift: expected {expected_base_sha256}, "
            f"found {actual_base_sha256}"
        )
    base = json.loads(base_path.read_text(encoding="utf-8"))
    contract = _deep_merge(base, overlay["overrides"])
    resolved_bytes = canonical_json_bytes(contract)
    sources = {
        "overlay_relative_path": str(contract_path.relative_to(repo_root)).replace("\\", "/"),
        "overlay_sha256": hashlib.sha256(overlay_bytes).hexdigest(),
        "base_relative_path": str(base_path.relative_to(repo_root)).replace("\\", "/"),
        "base_sha256": actual_base_sha256,
        "resolved_contract_sha256": hashlib.sha256(resolved_bytes).hexdigest(),
    }
    return contract, sources


def _write_parquet_immutable(frame: Any, path: Path) -> None:
    buffer = io.BytesIO()
    frame.write_parquet(buffer, compression="zstd", statistics=True)
    payload = buffer.getvalue()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"immutable payload collision: {path}")
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


def _write_json_immutable(value: Mapping[str, Any], path: Path) -> None:
    payload = canonical_json_bytes(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"immutable manifest collision: {path}")
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


def materialize_expansion(
    *,
    input_data_root: Path,
    output_data_root: Path,
    repo_root: Path,
    contract_path: Path,
    issued_at_utc: str,
) -> dict[str, Any]:
    pl = _polars()
    contract, contract_sources = resolve_expansion_contract(
        repo_root=repo_root, contract_path=contract_path
    )
    _validate_contract_authority(contract)
    core_path = Path(__file__).resolve()
    helper_path = repo_root / "src/aggie_analytics/data/historical_game_outcome_spine.py"
    builder_path = repo_root / "tools/build_historical_game_outcome_spine_expansion.py"
    entities, cfbd_mappings, sd_mappings, registry_profile = _load_registry(
        input_data_root, contract
    )
    completed_cfbd_rows, incomplete_cfbd_rows, cfbd_manifest, cfbd_profiles = (
        load_cfbd_expansion(input_data_root, contract)
    )
    sd_rows, sd_manifest, sd_profiles = _load_sportsdataverse(input_data_root, contract)
    completed, schedule_only, reconciliation, population = build_outputs_expansion(
        completed_cfbd_rows,
        incomplete_cfbd_rows,
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
    producer_hashes = {
        "core_sha256": sha256_file(core_path),
        "validated_helper_sha256": sha256_file(helper_path),
        "builder_sha256": sha256_file(builder_path),
    }
    identity = stable_hash(
        {
            "contract_sources": contract_sources,
            "producer_hashes": producer_hashes,
            "cfbd_manifest_sha256": source["cfbd_manifest_sha256"],
            "cfbd_payload_sha256": [item["sha256"] for item in cfbd_profiles],
            "sportsdataverse_manifest_sha256": source["sportsdataverse_manifest_sha256"],
            "sportsdataverse_payload_sha256": [item["sha256"] for item in sd_profiles],
            "canonical_registry_sha256": source["canonical_registry_sha256"],
            "record_hashes": record_hashes,
            "classification": contract["classification"],
        }
    )
    canonical_root = (
        output_data_root / "canonical/historical_game_outcome_spine/sha256" / identity
    )
    quarantine_root = (
        output_data_root / "quarantine/historical_game_outcome_spine/sha256" / identity
    )
    manifest_root = (
        output_data_root / "manifests/historical_game_outcome_spine/sha256" / identity
    )
    completed_path = canonical_root / "completed_game_outcomes.parquet"
    schedule_only_path = quarantine_root / "schedule_only_nonoutcomes.parquet"
    reconciliation_path = quarantine_root / "source_alias_reconciliation.parquet"
    _write_parquet_immutable(completed, completed_path)
    _write_parquet_immutable(schedule_only, schedule_only_path)
    _write_parquet_immutable(reconciliation, reconciliation_path)
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
        "schema_version": "2.0.0",
        "artifact_type": "HISTORICAL_GAME_OUTCOME_REFERENCE_SPINE_EXPANSION",
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "classification": contract["classification"],
        "dataset_identity": identity,
        "issued_at_utc": issued_at_utc,
        "contract_sources": contract_sources,
        "producer": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "polars": pl.__version__,
            **producer_hashes,
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
            "inspected_2024_2025_untouched_protected": False,
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
    _write_json_immutable(manifest, manifest_path)
    return {
        "dataset_identity": identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "completed_path": str(completed_path),
        "schedule_only_path": str(schedule_only_path),
        "reconciliation_path": str(reconciliation_path),
        "manifest": manifest,
    }

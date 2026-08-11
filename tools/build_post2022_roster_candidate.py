from __future__ import annotations

"""Normalize and conservatively reconcile 2023-2025 roster release captures."""

import argparse
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

from aggie_analytics.data.roster_reconciliation import (
    normalize_identity_text,
    resolve_roster_identity,
)


ACQUISITION_ID = "6e3fba9bff67318e6dc3d94b09700b16c92619fe7a14131ccf0a14757bacc2a8"
ACQUISITION_MANIFEST_SHA = "5e1efc3e56c803d4c2b3020e6e441544409a3ad6f27595aec7996b679920bec0"
CANONICAL_REGISTRY_SHA = "0ab6acafbe350a4958a5fca1c02a9c51463ab8a93ecc173a57b9fd925bf2198d"
SCHEMA_VERSION = "1.0.0"
POLICY_VERSION = "post2022-roster-source-id-name-membership-v1"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def stable_hash(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clean_value(value: object) -> object:
    if isinstance(value, float) and value != value:
        return None
    return value


def write_immutable_table(path: Path, rows: list[dict[str, Any]]) -> pa.Table:
    table = pa.Table.from_pylist(rows)
    if path.is_file():
        if pq.ParquetFile(path).read().to_pylist() != table.to_pylist():
            raise RuntimeError(f"immutable table collision: {path}")
        return table
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        pq.write_table(table, temporary, compression="zstd", compression_level=9, use_dictionary=False, write_statistics=True)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return table


def write_immutable_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    if path.is_file():
        if path.read_bytes() != payload:
            raise RuntimeError(f"immutable manifest collision: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def registry_indexes(path: Path) -> tuple[dict[str, set[str]], dict[str, set[tuple[str, str]]], dict[tuple[str, int, str], set[tuple[str, str]]]]:
    table = pacsv.read_csv(
        path,
        convert_options=pacsv.ConvertOptions(include_columns=[
            "record_type", "person_type", "source_system_id", "source_entity_key",
            "canonical_id", "first_name", "last_name", "team_label", "team_canonical_id", "season",
        ]),
    )
    table = table.filter(pc.equal(table["person_type"], "player"))
    source_mappings: dict[str, set[str]] = defaultdict(set)
    canonical_names: dict[str, set[tuple[str, str]]] = defaultdict(set)
    memberships: dict[tuple[str, int, str], set[tuple[str, str]]] = defaultdict(set)
    for row in table.to_pylist():
        if row["record_type"] == "PERSON":
            canonical_names[str(row["canonical_id"])].add((
                normalize_identity_text(row["first_name"]), normalize_identity_text(row["last_name"])
            ))
        elif row["source_system_id"] == "SRC-002" and row["record_type"] == "SOURCE_MAPPING":
            source_mappings[str(row["source_entity_key"])].add(str(row["canonical_id"]))
        elif row["source_system_id"] == "SRC-002" and row["record_type"] == "ROSTER_MEMBERSHIP":
            memberships[(
                str(row["source_entity_key"]), int(row["season"]), normalize_identity_text(row["team_label"])
            )].add((str(row["canonical_id"]), str(row["team_canonical_id"])))
    return dict(source_mappings), dict(canonical_names), dict(memberships)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-data-root", type=Path)
    parser.add_argument("--acquisition-manifest", type=Path, required=True)
    parser.add_argument("--canonical-registry", type=Path, required=True)
    parser.add_argument("--issued-at-utc", required=True)
    args = parser.parse_args()
    root = args.data_root.resolve()
    output_data_root = (args.output_data_root or root).resolve()
    acquisition_path = args.acquisition_manifest.resolve()
    registry_path = args.canonical_registry.resolve()
    if sha256_file(acquisition_path) != ACQUISITION_MANIFEST_SHA:
        raise RuntimeError("acquisition manifest hash drift")
    if sha256_file(registry_path) != CANONICAL_REGISTRY_SHA:
        raise RuntimeError("canonical people registry hash drift")
    acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
    if acquisition["acquisition_identity"] != ACQUISITION_ID:
        raise RuntimeError("acquisition identity drift")
    source_mappings, canonical_names, memberships = registry_indexes(registry_path)

    by_season: dict[int, list[dict[str, Any]]] = {}
    quarantined: list[dict[str, Any]] = []
    dispositions: Counter[str] = Counter()
    schema_by_season: dict[str, list[str]] = {}
    row_hashes: list[str] = []
    for capture in acquisition["captures"]:
        season = int(capture["season"])
        raw_path = root / capture["raw_relative_path"]
        if sha256_file(raw_path) != capture["raw_sha256"]:
            raise RuntimeError(f"raw roster hash drift: {season}")
        raw_table = pq.ParquetFile(raw_path).read()
        schema_by_season[str(season)] = raw_table.schema.names
        rows: list[dict[str, Any]] = []
        seen_keys: set[tuple[int, str, str]] = set()
        for source_row_number, raw in enumerate(raw_table.to_pylist()):
            raw = {key: clean_value(value) for key, value in raw.items()}
            if int(raw.get("season") or -1) != season:
                raise RuntimeError(f"asset season mismatch: {season}")
            source_key = (season, str(raw.get("athlete_id")), str(raw.get("team_id")))
            duplicate = source_key in seen_keys
            seen_keys.add(source_key)
            resolution = resolve_roster_identity(
                athlete_id=raw.get("athlete_id"), season=raw.get("season"),
                first_name=raw.get("first_name"), last_name=raw.get("last_name"),
                team_label=raw.get("team_location"), source_mappings=source_mappings,
                canonical_names=canonical_names, memberships=memberships,
            )
            disposition = "QUARANTINE_DUPLICATE_PLAYER_TEAM_SEASON" if duplicate else resolution.disposition
            source_record_sha = stable_hash(raw)
            identity_core = {
                "source_payload_sha256": capture["raw_sha256"],
                "source_row_number": source_row_number,
                "source_record_sha256": source_record_sha,
            }
            row = {
                "schema_version": SCHEMA_VERSION,
                "observation_id": "post22_roster_" + stable_hash(identity_core)[:24],
                "season": season,
                "source_row_number": source_row_number,
                "source_system_id": "SRC-001",
                "source_athlete_id": str(raw["athlete_id"]) if raw.get("athlete_id") is not None else None,
                "source_team_id": str(raw["team_id"]) if raw.get("team_id") is not None else None,
                "first_name": raw.get("first_name"),
                "last_name": raw.get("last_name"),
                "display_name": raw.get("athlete_display_name") or raw.get("full_name"),
                "team_label": raw.get("team_location"),
                "team_display_name": raw.get("team_display_name"),
                "position_source_href": raw.get("position_href"),
                "height": raw.get("height"),
                "weight": raw.get("weight"),
                "jersey": raw.get("jersey"),
                "experience_years": raw.get("experience_years"),
                "source_active": raw.get("active"),
                "canonical_player_id": resolution.canonical_player_id,
                "canonical_team_id": resolution.canonical_team_id,
                "canonical_person_option_count": resolution.canonical_person_option_count,
                "canonical_membership_option_count": resolution.canonical_membership_option_count,
                "exact_source_id_and_name_match": resolution.exact_name_match,
                "exact_normalized_team_label_match": resolution.exact_team_label_match,
                "reconciliation_disposition": disposition,
                "quarantined": duplicate or resolution.quarantine,
                "source_uri": capture["source_uri"],
                "source_snapshot_id": capture["snapshot_id"],
                "source_payload_sha256": capture["raw_sha256"],
                "source_asset_updated_at_utc": capture["asset_updated_at_utc"],
                "source_retrieved_at_utc": capture["retrieved_at_utc"],
                "source_record_evidence_sha256": source_record_sha,
                "historical_publication_time_state": "UNKNOWN",
                "historical_known_at_eligible": False,
                "availability_inference": False,
                "canonical_or_pit_admission": False,
                "feature_or_training_admission": False,
                "policy_version": POLICY_VERSION,
            }
            row["row_lineage_sha256"] = stable_hash(row)
            rows.append(row)
            row_hashes.append(stable_hash(row))
            dispositions[disposition] += 1
            if row["quarantined"]:
                quarantined.append(row)
        by_season[season] = rows

    manifest_core = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "POST2022_ROSTER_RECONCILIATION_MANIFEST",
        "decision_unit": "POST-SUBTASK-173",
        "dataset_version": "post2022-roster-reconciliation-2023-2025-v1",
        "domain": "ROSTERS",
        "grain": "PLAYER_TEAM_SEASON_ROSTER_MEMBERSHIP",
        "acquisition_identity": ACQUISITION_ID,
        "acquisition_manifest_sha256": ACQUISITION_MANIFEST_SHA,
        "canonical_people_registry_sha256": CANONICAL_REGISTRY_SHA,
        "policy_version": POLICY_VERSION,
        "seasons": sorted(by_season),
        "rows_by_season": {str(season): len(rows) for season, rows in sorted(by_season.items())},
        "total_rows": sum(map(len, by_season.values())),
        "disposition_counts": dict(sorted(dispositions.items())),
        "quarantined_rows": len(quarantined),
        "schema_by_season": schema_by_season,
        "schema_drift": {
            "2024_adds_age_and_date_of_birth_relative_to_2023_order": True,
            "2025_adds_draft_fields": True,
            "draft_fields_excluded_from_roster_candidate_to_prevent_future_information_use": True,
        },
        "row_hashes": row_hashes,
        "authority": {
            "candidate_only": True,
            "upstream_independence_from_cfbd": False,
            "name_only_merge_permitted": False,
            "roster_membership_implies_availability": False,
            "asset_updated_at_is_historical_game_known_at": False,
            "historical_known_at_eligible": False,
            "canonical_or_pit_admission": False,
            "feature_or_training_admission": False,
            "protected_use_admission": False,
        },
    }
    dataset_identity = stable_hash(manifest_core)
    output_root = output_data_root / "quarantine" / "historical_known_at" / "sha256" / dataset_identity / "rosters_post2022"
    payloads: list[dict[str, Any]] = []
    for season, rows in sorted(by_season.items()):
        path = output_root / f"season={season}" / "candidate_roster_rows.parquet"
        table = write_immutable_table(path, rows)
        payloads.append({"role": "CANDIDATE_ROSTER_ROWS", "season": season, "rows": table.num_rows, "bytes": path.stat().st_size, "sha256": sha256_file(path), "path": path.relative_to(output_data_root).as_posix()})
    quarantine_path = output_root / "quarantined_roster_rows.parquet"
    quarantine_table = write_immutable_table(quarantine_path, quarantined)
    payloads.append({"role": "QUARANTINED_ROSTER_ROWS", "rows": quarantine_table.num_rows, "bytes": quarantine_path.stat().st_size, "sha256": sha256_file(quarantine_path), "path": quarantine_path.relative_to(output_data_root).as_posix()})
    manifest = {**manifest_core, "dataset_identity": dataset_identity, "issued_at_utc": args.issued_at_utc, "payloads": payloads}
    manifest_path = output_data_root / "manifests" / "historical_known_at" / "sha256" / dataset_identity / "post2022_roster_reconciliation.json"
    write_immutable_json(manifest_path, manifest)
    print(json.dumps({"dataset_identity": dataset_identity, "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path), "total_rows": manifest_core["total_rows"], "quarantined_rows": len(quarantined), "disposition_counts": manifest_core["disposition_counts"], "payloads": payloads}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

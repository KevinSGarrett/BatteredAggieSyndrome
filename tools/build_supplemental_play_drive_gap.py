from __future__ import annotations

"""Build immutable candidate-only play/drive payloads for exact historical gaps."""

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import pyarrow as pa
import pyarrow.parquet as pq

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.play_drive import (  # noqa: E402
    DRIVE_POLICY_VERSION,
    PLAY_POLICY_VERSION,
    canonical_bytes,
    normalize_drive_candidate,
    normalize_play_candidate,
    stable_hash,
)


EXPECTED_ACQUISITION_MANIFEST_SHA = "bb5ace34c41cfc886f928119b53d495b9870ec1d7c7caff559d3a9e9d178fba7"
EXPECTED_ACQUISITION_PAYLOAD_SHA = "9c1c3555d4bd45fa9336582b696b4d62c28b63ab319ff97f320922f135afcc9a"
EXPECTED_CANONICAL_REGISTRY_SHA = "10d0bd0adcef3fc1ba22fb9932f353cc59b0e5d4508c7891a1472d0221a454ac"
VERSIONED_CANDIDATE_SEASONS = [
    2004, 2005, 2006, 2007, 2008, 2009, 2010, 2012, 2013, 2014,
    2015, 2016, 2017, 2018, 2019, 2021, 2022,
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ordered_hash(values: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(value.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def sort_identifier(value: object) -> tuple[int, int | str]:
    text = "" if value is None else str(value)
    return (0, int(text)) if text.isdigit() else (1, text)


def immutable_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise RuntimeError(f"immutable JSON collision: {path}")
        return
    path.write_bytes(payload)


def immutable_parquet(path: Path, rows: list[dict[str, Any]]) -> pa.Table:
    if not rows:
        raise RuntimeError(f"refusing to write an empty candidate payload: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".candidate.tmp")
    if temporary.exists():
        temporary.unlink()
    table = pa.Table.from_pylist(rows)
    pq.write_table(
        table,
        temporary,
        compression="zstd",
        compression_level=9,
        use_dictionary=True,
        write_statistics=True,
        data_page_version="1.0",
    )
    if path.exists():
        if path.read_bytes() != temporary.read_bytes():
            temporary.unlink()
            raise RuntimeError(f"immutable Parquet collision: {path}")
        temporary.unlink()
    else:
        temporary.replace(path)
    return table


def load_canonical_games(path: Path, seasons: set[int]) -> dict[tuple[int, str], str]:
    mappings: dict[tuple[int, str], str] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["entity_type"] != "game" or row["source_system_id"] != "SRC-002":
                continue
            if not row["season"] or int(row["season"]) not in seasons:
                continue
            if row["resolution_state"] != "AUTO_ACCEPTED_VERIFIED":
                continue
            key = (int(row["season"]), str(row["source_entity_key"]))
            prior = mappings.setdefault(key, row["canonical_id"])
            if prior != row["canonical_id"]:
                raise RuntimeError(f"conflicting canonical game mapping: {key}")
    return mappings


def load_capture(
    *, data_root: Path, entry: dict[str, Any]
) -> list[dict[str, Any]]:
    path = data_root / Path(*entry["immutable_path"].split("/"))
    if not path.is_file():
        raise FileNotFoundError(f"immutable capture is absent: {path}")
    if path.stat().st_size != int(entry["response_bytes"]):
        raise RuntimeError(f"capture byte-size drift: {entry['request_id']}")
    if sha256_file(path) != entry["response_sha256"]:
        raise RuntimeError(f"capture SHA-256 drift: {entry['request_id']}")
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise RuntimeError(f"capture is not a JSON object array: {entry['request_id']}")
    if len(rows) != int(entry["row_count"]):
        raise RuntimeError(f"capture row-count drift: {entry['request_id']}")
    return rows


def source_rows(
    *, data_root: Path, entries: list[dict[str, Any]]
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    result: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for entry in sorted(entries, key=lambda item: item["request_id"]):
        for source_row_number, row in enumerate(load_capture(data_root=data_root, entry=entry)):
            context = {
                "source_request_id": entry["request_id"],
                "source_capture_id": entry["capture_id"],
                "source_response_sha256": entry["response_sha256"],
                "source_immutable_path": entry["immutable_path"],
                "source_row_number": source_row_number,
                "source_retrieved_at_utc": entry["retrieved_at_utc"],
                "source_capture_known_at_utc": entry["capture_known_at_utc"],
                "source_season_type": entry["season_type"],
            }
            result.append((row, context))
    return result


def payload_contract(path: Path, root: Path, table: pa.Table, *, role: str, season: int) -> dict[str, Any]:
    return {
        "role": role,
        "season": season,
        "rows": table.num_rows,
        "columns": table.num_columns,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "path": path.relative_to(root).as_posix(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-data-root", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--issued-at-utc", required=True)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    output_data_root = (args.output_data_root or data_root).resolve()
    config_path = args.config.resolve()
    if repo_root not in config_path.parents:
        raise RuntimeError("contract must be versioned inside the repository")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    seasons = [int(value) for value in config["selected_seasons"]]
    season_set = set(seasons)
    if seasons != [2011, 2020, 2023, 2024, 2025]:
        raise RuntimeError("selected season scope drift")

    acquisition_path = data_root / Path(*config["acquisition_manifest"]["external_relative_path"].split("/"))
    registry_path = data_root / Path(*config["canonical_game_registry"]["external_relative_path"].split("/"))
    if sha256_file(acquisition_path) != EXPECTED_ACQUISITION_MANIFEST_SHA:
        raise RuntimeError("acquisition manifest SHA-256 drift")
    if sha256_file(registry_path) != EXPECTED_CANONICAL_REGISTRY_SHA:
        raise RuntimeError("canonical game registry SHA-256 drift")
    acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
    if acquisition["content_hash"]["canonical_payload_sha256"] != EXPECTED_ACQUISITION_PAYLOAD_SHA:
        raise RuntimeError("acquisition canonical payload identity drift")

    selected = [
        entry for entry in acquisition["request_index"]
        if entry["domain"] in {"plays", "drives"}
        and int(entry["season"]) in season_set
        and entry["result"] == "SUCCESS"
    ]
    capture_index = [
        {
            "domain": entry["domain"],
            "season": int(entry["season"]),
            "season_type": entry["season_type"],
            "request_id": entry["request_id"],
            "canonical_request_sha256": entry["canonical_request_sha256"],
            "capture_id": entry["capture_id"],
            "capture_known_at_utc": entry["capture_known_at_utc"],
            "retrieved_at_utc": entry["retrieved_at_utc"],
            "immutable_path": entry["immutable_path"],
            "response_sha256": entry["response_sha256"],
            "response_bytes": int(entry["response_bytes"]),
            "row_count": int(entry["row_count"]),
            "schema_sha256": entry["schema"]["top_level_schema_sha256"],
        }
        for entry in sorted(selected, key=lambda item: (int(item["season"]), item["domain"], item["request_id"]))
    ]
    expected = config["expected_population"]
    for season in seasons:
        for domain in ("plays", "drives"):
            entries = [entry for entry in selected if int(entry["season"]) == season and entry["domain"] == domain]
            contract = expected[str(season)][domain]
            if len(entries) != int(contract["captures"]):
                raise RuntimeError(f"capture-count drift: {season} {domain}")
            if sum(int(entry["row_count"]) for entry in entries) != int(contract["rows"]):
                raise RuntimeError(f"source row-count drift: {season} {domain}")

    builder_path = Path(__file__).resolve()
    normalizer_path = repo_root / "src" / "aggie_analytics" / "data" / "play_drive.py"
    identity_contract = {
        "schema_version": "1.0.0",
        "dataset_version": config["dataset_version"],
        "decision_unit": config["decision_unit"],
        "selected_seasons": seasons,
        "acquisition_manifest_sha256": EXPECTED_ACQUISITION_MANIFEST_SHA,
        "acquisition_canonical_payload_sha256": EXPECTED_ACQUISITION_PAYLOAD_SHA,
        "canonical_game_registry_sha256": EXPECTED_CANONICAL_REGISTRY_SHA,
        "contract_sha256": sha256_file(config_path),
        "builder_sha256": sha256_file(builder_path),
        "normalizer_sha256": sha256_file(normalizer_path),
        "play_policy_version": PLAY_POLICY_VERSION,
        "drive_policy_version": DRIVE_POLICY_VERSION,
        "capture_index": capture_index,
    }
    dataset_identity = stable_hash(identity_contract)
    output_root = (
        output_data_root / "quarantine" / "historical_known_at" / "sha256"
        / dataset_identity / "supplemental_play_drive"
    )
    canonical_games = load_canonical_games(registry_path, season_set)

    payloads: list[dict[str, Any]] = []
    population: dict[str, Any] = {}
    dispositions: Counter[str] = Counter()
    missingness: Counter[str] = Counter()
    quarantine_rows = 0
    total_play_rows = 0
    total_drive_rows = 0
    all_play_lineages: list[str] = []
    all_drive_lineages: list[str] = []

    for season in seasons:
        play_entries = [entry for entry in selected if int(entry["season"]) == season and entry["domain"] == "plays"]
        drive_entries = [entry for entry in selected if int(entry["season"]) == season and entry["domain"] == "drives"]
        raw_drives = source_rows(data_root=data_root, entries=drive_entries)
        raw_plays = source_rows(data_root=data_root, entries=play_entries)

        drive_ids = {str(row["id"]) for row, _context in raw_drives if row.get("id") is not None}
        play_linked_drive_ids = {str(row["driveId"]) for row, _context in raw_plays if row.get("driveId") is not None}
        if len(drive_ids) != len(raw_drives):
            raise RuntimeError(f"duplicate or missing drive source identity: {season}")
        play_ids = {str(row["id"]) for row, _context in raw_plays if row.get("id") is not None}
        if len(play_ids) != len(raw_plays):
            raise RuntimeError(f"duplicate or missing play source identity: {season}")

        play_rows = [
            normalize_play_candidate(
                season=season,
                raw=row,
                canonical_game_id=canonical_games.get((season, str(row.get("gameId")))),
                known_drive_ids=drive_ids,
                source_context=context,
            )
            for row, context in raw_plays
        ]
        drive_rows = [
            normalize_drive_candidate(
                season=season,
                raw=row,
                canonical_game_id=canonical_games.get((season, str(row.get("gameId")))),
                play_linked_drive_ids=play_linked_drive_ids,
                source_context=context,
            )
            for row, context in raw_drives
        ]
        play_rows.sort(key=lambda row: (sort_identifier(row["source_game_id"]), sort_identifier(row["source_play_id"])))
        drive_rows.sort(key=lambda row: (sort_identifier(row["source_game_id"]), sort_identifier(row["source_drive_id"])))

        for row in play_rows + drive_rows:
            dispositions[row["reconciliation_disposition"]] += 1
            quarantine_rows += int(row["quarantined"])
        for row in play_rows:
            missingness["play_text"] += int(row["play_text"] is None)
            missingness["play_type"] += int(row["play_type"] is None)
            missingness["ppa_source"] += int(row["ppa_source"] is None)
            missingness["wallclock_source"] += int(row["wallclock_source"] is None)
        for row in drive_rows:
            missingness["drive_result"] += int(row["drive_result"] is None)
            missingness["drive_without_play_rows"] += int(not row["play_rows_present"])

        play_path = output_root / f"season={season}" / "candidate_play_rows.parquet"
        drive_path = output_root / f"season={season}" / "candidate_drive_rows.parquet"
        play_table = immutable_parquet(play_path, play_rows)
        drive_table = immutable_parquet(drive_path, drive_rows)
        payloads.append(payload_contract(play_path, output_data_root, play_table, role="CANDIDATE_PLAY_ROWS", season=season))
        payloads.append(payload_contract(drive_path, output_data_root, drive_table, role="CANDIDATE_DRIVE_ROWS", season=season))

        play_games = {row["source_game_id"] for row in play_rows}
        drive_games = {row["source_game_id"] for row in drive_rows}
        population[str(season)] = {
            "play_rows": len(play_rows),
            "drive_rows": len(drive_rows),
            "play_games": len(play_games),
            "drive_games": len(drive_games),
            "play_capture_count": len(play_entries),
            "drive_capture_count": len(drive_entries),
            "play_linked_drive_ids": len(play_linked_drive_ids),
            "drive_ids": len(drive_ids),
            "drives_without_play_rows": len(drive_ids - play_linked_drive_ids),
            "play_drive_ids_without_drive_record": len(play_linked_drive_ids - drive_ids),
            "canonical_game_mapping_misses": sum(
                row["canonical_game_id"] is None for row in play_rows + drive_rows
            ),
        }
        total_play_rows += len(play_rows)
        total_drive_rows += len(drive_rows)
        all_play_lineages.extend(row["row_lineage_sha256"] for row in play_rows)
        all_drive_lineages.extend(row["row_lineage_sha256"] for row in drive_rows)

    manifest = {
        "schema_version": "1.0.0",
        "artifact_type": "SUPPLEMENTAL_CFBD_PLAY_DRIVE_RECONCILIATION_MANIFEST",
        "decision_unit": "POST-SUBTASK-174",
        "dataset_identity": dataset_identity,
        "issued_at_utc": args.issued_at_utc,
        "identity_contract": identity_contract,
        "population": {
            "by_season": population,
            "play_rows": total_play_rows,
            "drive_rows": total_drive_rows,
            "total_rows": total_play_rows + total_drive_rows,
            "capture_count": len(capture_index),
            "disposition_counts": dict(sorted(dispositions.items())),
            "quarantined_rows": quarantine_rows,
            "missingness": dict(sorted(missingness.items())),
            "ordered_play_lineage_sha256": ordered_hash(all_play_lineages),
            "ordered_drive_lineage_sha256": ordered_hash(all_drive_lineages),
        },
        "coverage_union": {
            "versioned_candidate_seasons": VERSIONED_CANDIDATE_SEASONS,
            "supplemental_candidate_seasons": seasons,
            "play_and_drive_candidate_seasons": sorted(set(VERSIONED_CANDIDATE_SEASONS) | season_set),
            "dense_2010_2025_candidate_seasons": list(range(2010, 2026)),
            "dense_2010_2025_missing_candidate_seasons": [],
            "authority_by_supplemental_season": {
                str(season): "CURRENT_CAPTURE_CANDIDATE_NO_HISTORICAL_KNOWN_AT"
                for season in seasons
            },
        },
        "authority": config["source_authority"],
        "negative_findings": config["required_negative_findings"],
        "payloads": payloads,
    }
    manifest_path = (
        output_data_root / "manifests" / "historical_known_at" / "sha256"
        / dataset_identity / "supplemental_play_drive_reconciliation.json"
    )
    immutable_json(manifest_path, manifest)
    print(json.dumps({
        "dataset_identity": dataset_identity,
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "play_rows": total_play_rows,
        "drive_rows": total_drive_rows,
        "quarantined_rows": quarantine_rows,
        "disposition_counts": dict(sorted(dispositions.items())),
        "missingness": dict(sorted(missingness.items())),
        "payloads": payloads,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

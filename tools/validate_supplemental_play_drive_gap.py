from __future__ import annotations

"""Independently validate and replay the supplemental play/drive candidate layer."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


EXPECTED_DATASET_ID = "813276328568574a1d19173018ba328fd1c4a63a8aa34b34255ef1a2d880020f"
EXPECTED_MANIFEST_SHA = "c41fbedaa89e2ff9188f74789554fd34d5b173f636ee0b3a0853403eee5c4671"
EXPECTED_SEASONS = [2011, 2020, 2023, 2024, 2025]
EXPECTED_PLAY_ROWS = 737580
EXPECTED_DRIVE_ROWS = 100341
EXPECTED_DISPOSITIONS = {
    "CANDIDATE_EXACT_CANONICAL_GAME_AND_DRIVE": 737580,
    "CANDIDATE_EXACT_CANONICAL_GAME_AND_PLAY_LINKS": 100315,
    "CANDIDATE_EXACT_CANONICAL_GAME_DRIVE_WITHOUT_PLAY_ROWS": 26,
}
EXPECTED_MISSINGNESS = {
    "drive_result": 0,
    "drive_without_play_rows": 26,
    "play_text": 235,
    "play_type": 0,
    "ppa_source": 186183,
    "wallclock_source": 154099,
}


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def stable_hash(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ordered_hash(values: list[str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(value.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--builder", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: list[str] = []

    def check(name: str, condition: bool, detail: object = None) -> None:
        if not condition:
            raise AssertionError(f"{name}: {detail}")
        checks.append(name)

    check("manifest_sha256", sha256_file(manifest_path) == EXPECTED_MANIFEST_SHA)
    check("dataset_identity", manifest["dataset_identity"] == EXPECTED_DATASET_ID)
    check("identity_contract_hash", stable_hash(manifest["identity_contract"]) == EXPECTED_DATASET_ID)
    check("decision_unit", manifest["decision_unit"] == "POST-SUBTASK-174")
    check("season_scope", manifest["identity_contract"]["selected_seasons"] == EXPECTED_SEASONS)
    check("capture_count", manifest["population"]["capture_count"] == 88)
    check("play_population", manifest["population"]["play_rows"] == EXPECTED_PLAY_ROWS)
    check("drive_population", manifest["population"]["drive_rows"] == EXPECTED_DRIVE_ROWS)
    check("dispositions", manifest["population"]["disposition_counts"] == EXPECTED_DISPOSITIONS)
    check("missingness", manifest["population"]["missingness"] == EXPECTED_MISSINGNESS)
    check("no_quarantine", manifest["population"]["quarantined_rows"] == 0)
    check(
        "dense_candidate_coverage",
        manifest["coverage_union"]["dense_2010_2025_candidate_seasons"] == list(range(2010, 2026))
        and manifest["coverage_union"]["dense_2010_2025_missing_candidate_seasons"] == [],
    )
    authority = manifest["authority"]
    check(
        "authority_closed",
        authority["candidate_only"]
        and not authority["historical_known_at_eligible"]
        and not authority["canonical_or_pit_admission"]
        and not authority["feature_or_training_admission"]
        and not authority["protected_use_admission"],
    )
    check("no_name_only_mapping", not authority["name_only_mapping_permitted"])

    payloads = manifest["payloads"]
    check("payload_count", len(payloads) == 10)
    dispositions: Counter[str] = Counter()
    missingness: Counter[str] = Counter()
    observation_ids: set[str] = set()
    play_lineages: list[str] = []
    drive_lineages: list[str] = []
    play_drive_ids: dict[int, set[str]] = defaultdict(set)
    drive_ids: dict[int, set[str]] = defaultdict(set)
    drive_without_plays: dict[int, int] = defaultdict(int)
    canonical_mapping_misses = 0

    for payload in sorted(payloads, key=lambda item: (int(item["season"]), item["role"])):
        path = data_root / Path(*payload["path"].split("/"))
        check(f"payload_exists_{payload['season']}_{payload['role']}", path.is_file())
        check(f"payload_bytes_{payload['season']}_{payload['role']}", path.stat().st_size == int(payload["bytes"]))
        check(f"payload_sha_{payload['season']}_{payload['role']}", sha256_file(path) == payload["sha256"])
        table = pq.ParquetFile(path).read()
        check(f"payload_rows_{payload['season']}_{payload['role']}", table.num_rows == int(payload["rows"]))
        check(f"payload_columns_{payload['season']}_{payload['role']}", table.num_columns == int(payload["columns"]))
        rows = table.to_pylist()
        for row in rows:
            observation_id = row["observation_id"]
            if observation_id in observation_ids:
                raise AssertionError(f"duplicate observation identity: {observation_id}")
            observation_ids.add(observation_id)
            lineage = dict(row)
            declared = lineage.pop("row_lineage_sha256")
            if stable_hash(lineage) != declared:
                raise AssertionError(f"row lineage mismatch: {observation_id}")
            if row["canonical_game_id"] is None:
                canonical_mapping_misses += 1
            if row["quarantined"]:
                raise AssertionError(f"unexpected quarantined row: {observation_id}")
            if any(row[field] for field in (
                "historical_known_at_eligible", "canonical_or_pit_admission",
                "feature_or_training_admission", "protected_use_admission",
                "target_game_feature_admission",
            )):
                raise AssertionError(f"authority boundary violation: {observation_id}")
            dispositions[row["reconciliation_disposition"]] += 1
            season = int(row["season"])
            if row["domain"] == "plays":
                play_lineages.append(declared)
                play_drive_ids[season].add(row["source_drive_id"])
                missingness["play_text"] += int(row["play_text"] is None)
                missingness["play_type"] += int(row["play_type"] is None)
                missingness["ppa_source"] += int(row["ppa_source"] is None)
                missingness["wallclock_source"] += int(row["wallclock_source"] is None)
            else:
                drive_lineages.append(declared)
                drive_ids[season].add(row["source_drive_id"])
                missingness["drive_result"] += int(row["drive_result"] is None)
                missingness["drive_without_play_rows"] += int(not row["play_rows_present"])
                drive_without_plays[season] += int(not row["play_rows_present"])

    check("unique_observation_identity", len(observation_ids) == EXPECTED_PLAY_ROWS + EXPECTED_DRIVE_ROWS)
    check("canonical_mapping_complete", canonical_mapping_misses == 0)
    check("payload_dispositions", dict(sorted(dispositions.items())) == EXPECTED_DISPOSITIONS)
    check("payload_missingness", dict(sorted(missingness.items())) == EXPECTED_MISSINGNESS)
    check(
        "ordered_play_lineage",
        ordered_hash(play_lineages) == manifest["population"]["ordered_play_lineage_sha256"],
    )
    check(
        "ordered_drive_lineage",
        ordered_hash(drive_lineages) == manifest["population"]["ordered_drive_lineage_sha256"],
    )
    check(
        "play_drive_links_complete",
        all(play_drive_ids[season] <= drive_ids[season] for season in EXPECTED_SEASONS),
    )
    check(
        "partial_drive_finding_exact",
        dict(sorted(drive_without_plays.items()))
        == {2011: 0, 2020: 26, 2023: 0, 2024: 0, 2025: 0},
    )

    # Keep the rebuild root deliberately short so the content-addressed payload
    # suffix remains below legacy Windows MAX_PATH limits.
    rebuild_root = data_root / "validation" / "P174R"
    expected_parent = (data_root / "validation").resolve()
    if rebuild_root.resolve().parent != expected_parent:
        raise RuntimeError("unsafe deterministic rebuild root")
    if rebuild_root.exists():
        shutil.rmtree(rebuild_root)
    command = [
        sys.executable,
        str(args.builder.resolve()),
        "--repo-root", str(repo_root),
        "--data-root", str(data_root),
        "--output-data-root", str(rebuild_root),
        "--config", str(args.config.resolve()),
        "--issued-at-utc", manifest["issued_at_utc"],
    ]
    environment = dict(__import__("os").environ)
    environment["PYTHONPATH"] = str(repo_root / "src")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        command, cwd=repo_root, env=environment,
        capture_output=True, text=True, timeout=300,
    )
    if completed.returncode != 0:
        raise AssertionError(f"deterministic rebuild failed: {completed.stderr[-2000:]}")
    compared: list[dict[str, Any]] = []
    try:
        for payload in payloads:
            source = data_root / Path(*payload["path"].split("/"))
            rebuilt = rebuild_root / Path(*payload["path"].split("/"))
            source_sha = sha256_file(source)
            rebuilt_sha = sha256_file(rebuilt)
            if source.stat().st_size != rebuilt.stat().st_size or source_sha != rebuilt_sha:
                raise AssertionError(f"byte-identical rebuild mismatch: {payload['path']}")
            compared.append({
                "path": payload["path"],
                "bytes": source.stat().st_size,
                "sha256": source_sha,
            })
        rebuilt_manifest = (
            rebuild_root / "manifests" / "historical_known_at" / "sha256"
            / EXPECTED_DATASET_ID / "supplemental_play_drive_reconciliation.json"
        )
        if manifest_path.read_bytes() != rebuilt_manifest.read_bytes():
            raise AssertionError("byte-identical manifest rebuild mismatch")
        compared.append({
            "path": "supplemental_play_drive_reconciliation.json",
            "bytes": manifest_path.stat().st_size,
            "sha256": sha256_file(manifest_path),
        })
    finally:
        if rebuild_root.exists():
            shutil.rmtree(rebuild_root)
    check("deterministic_rebuild", len(compared) == 11)

    report = {
        "schema_version": "1.0.0",
        "artifact_type": "SUPPLEMENTAL_PLAY_DRIVE_INDEPENDENT_VALIDATION",
        "decision_unit": "POST-SUBTASK-174",
        "status": "PASS",
        "dataset_identity": EXPECTED_DATASET_ID,
        "manifest_sha256": EXPECTED_MANIFEST_SHA,
        "checks_passed": len(checks),
        "checks_failed": 0,
        "checks": checks,
        "deterministic_payloads_compared": len(compared),
        "deterministic_rebuild": compared,
        "rebuild_root_removed": not rebuild_root.exists(),
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    if output.exists() and output.read_bytes() != payload:
        raise RuntimeError("immutable validation report collision")
    if not output.exists():
        output.write_bytes(payload)
    print(json.dumps({
        **report,
        "validation_report": str(output),
        "validation_report_sha256": sha256_file(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

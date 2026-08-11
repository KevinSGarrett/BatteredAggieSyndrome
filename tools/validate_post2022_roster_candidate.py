from __future__ import annotations

"""Independently validate and replay the post-2022 roster candidate population."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


EXPECTED_DATASET_ID = "151c594e243d6db7efcb811634da99415b46384a263114edd7121ddd3500b242"
EXPECTED_ACQUISITION_ID = "6e3fba9bff67318e6dc3d94b09700b16c92619fe7a14131ccf0a14757bacc2a8"


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


def read_payload(root: Path, contract: dict[str, Any]) -> list[dict[str, Any]]:
    path = root / Path(*contract["path"].split("/"))
    if path.stat().st_size != int(contract["bytes"]):
        raise AssertionError(f"payload byte-size mismatch: {path}")
    if sha256_file(path) != contract["sha256"]:
        raise AssertionError(f"payload hash mismatch: {path}")
    rows = pq.ParquetFile(path).read().to_pylist()
    if len(rows) != int(contract["rows"]):
        raise AssertionError(f"payload row-count mismatch: {path}")
    return rows


def validate(root: Path, manifest: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    checks: list[str] = []
    core = {key: value for key, value in manifest.items() if key not in {"dataset_identity", "issued_at_utc", "payloads"}}
    if stable_hash(core) != manifest["dataset_identity"] or manifest["dataset_identity"] != EXPECTED_DATASET_ID:
        raise AssertionError("dataset identity mismatch")
    checks.append("dataset_identity")
    if manifest["acquisition_identity"] != EXPECTED_ACQUISITION_ID:
        raise AssertionError("acquisition identity mismatch")
    checks.append("acquisition_identity")
    if manifest["seasons"] != [2023, 2024, 2025] or manifest["total_rows"] != 79832:
        raise AssertionError("population mismatch")
    checks.append("population")

    candidate_rows: list[dict[str, Any]] = []
    quarantine_rows: list[dict[str, Any]] = []
    for payload in manifest["payloads"]:
        rows = read_payload(root, payload)
        if payload["role"] == "CANDIDATE_ROSTER_ROWS":
            candidate_rows.extend(rows)
        else:
            quarantine_rows.extend(rows)
    checks.append("payload_integrity")
    if len(candidate_rows) != 79832 or len(quarantine_rows) != 749:
        raise AssertionError("payload population mismatch")
    checks.append("payload_population")
    ids = [row["observation_id"] for row in candidate_rows]
    if len(ids) != len(set(ids)):
        raise AssertionError("duplicate observation identity")
    checks.append("unique_observation_identity")
    for row in candidate_rows:
        lineage = dict(row)
        declared = lineage.pop("row_lineage_sha256")
        if stable_hash(lineage) != declared:
            raise AssertionError("row lineage mismatch")
    checks.append("row_lineage")
    if manifest["row_hashes"] != [stable_hash(row) for row in candidate_rows]:
        raise AssertionError("manifest row hash sequence mismatch")
    checks.append("manifest_row_hash_sequence")
    dispositions = Counter(row["reconciliation_disposition"] for row in candidate_rows)
    if dict(sorted(dispositions.items())) != manifest["disposition_counts"]:
        raise AssertionError("disposition count mismatch")
    checks.append("dispositions")
    quarantined_from_candidates = [row for row in candidate_rows if row["quarantined"]]
    if quarantined_from_candidates != quarantine_rows:
        raise AssertionError("quarantine payload is not the exact candidate subset")
    checks.append("quarantine_exact_subset")
    required_false = (
        "historical_known_at_eligible", "availability_inference", "canonical_or_pit_admission",
        "feature_or_training_admission",
    )
    if any(row[field] for row in candidate_rows for field in required_false):
        raise AssertionError("authority boundary violation")
    checks.append("authority_boundaries")
    exact = [row for row in candidate_rows if row["reconciliation_disposition"] == "CANDIDATE_EXACT_SOURCE_ID_NAME_AND_CANONICAL_MEMBERSHIP"]
    if len(exact) != 46586 or any(not row["canonical_player_id"] or not row["canonical_team_id"] for row in exact):
        raise AssertionError("exact reconciliation evidence mismatch")
    if any(not row["exact_source_id_and_name_match"] or not row["exact_normalized_team_label_match"] for row in exact):
        raise AssertionError("exact reconciliation flags mismatch")
    checks.append("exact_source_id_name_membership")
    source_only = [row for row in candidate_rows if row["reconciliation_disposition"] == "CANDIDATE_SOURCE_LEVEL_ONLY"]
    if len(source_only) != 27283 or any(row["canonical_player_id"] or row["canonical_team_id"] for row in source_only):
        raise AssertionError("source-only candidate was promoted")
    checks.append("source_only_not_promoted")
    if any("draft" in key.casefold() for row in candidate_rows for key in row):
        raise AssertionError("future draft field entered candidate payload")
    checks.append("future_draft_fields_excluded")
    if not manifest["schema_drift"]["2025_adds_draft_fields"]:
        raise AssertionError("schema drift finding missing")
    checks.append("schema_drift_preserved")
    authority = manifest["authority"]
    if not authority["candidate_only"] or any(authority[key] for key in (
        "name_only_merge_permitted", "roster_membership_implies_availability",
        "asset_updated_at_is_historical_game_known_at", "historical_known_at_eligible",
        "canonical_or_pit_admission", "feature_or_training_admission", "protected_use_admission",
    )):
        raise AssertionError("manifest authority mismatch")
    checks.append("manifest_authority")
    return checks, candidate_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--acquisition-manifest", type=Path, required=True)
    parser.add_argument("--canonical-registry", type=Path, required=True)
    parser.add_argument("--builder", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.data_root.resolve()
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks, _rows = validate(root, manifest)
    rebuild_root = root / "validation" / "POST-SUBTASK-173" / "deterministic-rebuild"
    expected_parent = (root / "validation" / "POST-SUBTASK-173").resolve()
    if rebuild_root.resolve().parent != expected_parent:
        raise RuntimeError("unsafe rebuild root")
    if rebuild_root.exists():
        shutil.rmtree(rebuild_root)
    command = [
        sys.executable, str(args.builder.resolve()), "--data-root", str(root),
        "--output-data-root", str(rebuild_root), "--acquisition-manifest", str(args.acquisition_manifest.resolve()),
        "--canonical-registry", str(args.canonical_registry.resolve()), "--issued-at-utc", manifest["issued_at_utc"],
    ]
    environment = dict(__import__("os").environ)
    environment["PYTHONPATH"] = str((args.repo_root.resolve() / "src"))
    completed = subprocess.run(command, cwd=args.repo_root.resolve(), env=environment, capture_output=True, text=True, timeout=300)
    if completed.returncode != 0:
        raise AssertionError(f"deterministic rebuild failed: {completed.stderr[-1000:]}")
    compared: list[dict[str, Any]] = []
    try:
        for contract in manifest["payloads"]:
            source = root / Path(*contract["path"].split("/"))
            rebuilt = rebuild_root / Path(*contract["path"].split("/"))
            source_sha, rebuilt_sha = sha256_file(source), sha256_file(rebuilt)
            if source.stat().st_size != rebuilt.stat().st_size or source_sha != rebuilt_sha:
                raise AssertionError(f"byte-identical rebuild mismatch: {contract['path']}")
            compared.append({"path": contract["path"], "sha256": source_sha, "bytes": source.stat().st_size})
        rebuilt_manifest = rebuild_root / "manifests" / "historical_known_at" / "sha256" / EXPECTED_DATASET_ID / "post2022_roster_reconciliation.json"
        if manifest_path.read_bytes() != rebuilt_manifest.read_bytes():
            raise AssertionError("byte-identical manifest rebuild mismatch")
        compared.append({"path": "post2022_roster_reconciliation.json", "sha256": sha256_file(manifest_path), "bytes": manifest_path.stat().st_size})
    finally:
        if rebuild_root.exists():
            shutil.rmtree(rebuild_root)
    checks.append("deterministic_rebuild")
    report = {
        "schema_version": "1.0.0", "artifact_type": "POST2022_ROSTER_INDEPENDENT_VALIDATION",
        "decision_unit": "POST-SUBTASK-173", "status": "PASS", "dataset_identity": EXPECTED_DATASET_ID,
        "manifest_sha256": sha256_file(manifest_path), "checks_passed": len(checks), "checks_failed": 0,
        "checks": checks, "deterministic_payloads_compared": len(compared), "deterministic_rebuild": compared,
        "rebuild_root_removed": not rebuild_root.exists(),
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    if output.is_file() and output.read_bytes() != payload:
        raise RuntimeError("immutable validation report collision")
    if not output.exists():
        output.write_bytes(payload)
    print(json.dumps({**report, "validation_report": str(output), "validation_report_sha256": sha256_file(output)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

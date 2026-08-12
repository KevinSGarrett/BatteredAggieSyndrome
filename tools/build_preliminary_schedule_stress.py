from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import tempfile

import polars as pl


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--issued-at-utc", required=True)
    args = parser.parse_args()
    repo, data = args.repo_root.resolve(), args.data_root.resolve()
    output = args.output_root.resolve() if args.output_root else data
    sys.path.insert(0, str(repo / "src"))
    from aggie_analytics.features.schedule_stress import canonical_json, materialize, stable_hash

    contract_path = repo / "configs/preliminary_schedule_stress_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    source = contract["source"]
    manifest_path = data / "manifests/preliminary_event_chronology/sha256" / source["run_identity"] / "run_manifest.json"
    if sha256_file(manifest_path) != source["manifest_sha256"]:
        raise ValueError("source manifest hash drift")
    source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if source_manifest["dataset_identity"] != source["dataset_identity"]:
        raise ValueError("source dataset identity drift")
    matrix_path = data / source_manifest["external_locations"]["training"] / "training_matrix.parquet"
    if sha256_file(matrix_path) != source["training_matrix_sha256"]:
        raise ValueError("source training matrix hash drift")
    source_rows = pl.read_parquet(matrix_path).to_dicts()
    features, diagnostics = materialize(source_rows, set(source["target_seasons"]))
    if diagnostics["target_games"] != contract["acceptance"]["target_games"]:
        raise ValueError("target-game population drift")
    if diagnostics["target_team_rows"] != contract["acceptance"]["target_team_rows"]:
        raise ValueError("target-team population drift")
    tmp_root = output / "tmp/preliminary_schedule_stress"
    tmp_root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="bat182-", dir=tmp_root))
    try:
        payload = stage / "target_game_team_schedule_stress.parquet"
        pl.DataFrame(features).write_parquet(payload, compression="zstd", statistics=True)
        payload_info = {"bytes": payload.stat().st_size, "rows": len(features), "sha256": sha256_file(payload)}
        code = {
            "contract_sha256": sha256_file(contract_path),
            "module_sha256": sha256_file(repo / "src/aggie_analytics/features/schedule_stress.py"),
            "builder_sha256": sha256_file(Path(__file__).resolve()),
        }
        identity = stable_hash({"source": source, "payload": payload_info, "code": code})
        feature_destination = output / "features/preliminary_schedule_stress/sha256" / identity
        feature_destination.parent.mkdir(parents=True, exist_ok=True)
        if feature_destination.exists():
            existing = feature_destination / payload.name
            if not existing.is_file() or sha256_file(existing) != payload_info["sha256"]:
                raise ValueError("immutable feature destination collision")
            payload.unlink()
        else:
            feature_destination.mkdir()
            shutil.move(str(payload), str(feature_destination / payload.name))
        manifest = {
            "schema_version": "1.0.0",
            "artifact_type": "PRELIMINARY_SCHEDULE_STRESS_FEATURE_CANDIDATE",
            "classification": contract["classification"],
            "decision_units": contract["decision_units"],
            "identity": identity,
            "issued_at_utc": datetime.fromisoformat(args.issued_at_utc.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source_identities": {"run": source["run_identity"], "dataset": source["dataset_identity"], "manifest_sha256": source["manifest_sha256"], "training_matrix_sha256": source["training_matrix_sha256"]},
            "code_identities": code,
            "payload": payload_info,
            "diagnostics": diagnostics,
            "leakage_validation": {"target_game_evidence_rows": 0, "source_start_at_or_after_cutoff_rows": 0, "historical_original_pit_eligible": False, "protected_eligible": False},
            "external_locations": {"features": f"features/preliminary_schedule_stress/sha256/{identity}/target_game_team_schedule_stress.parquet", "manifest": f"manifests/preliminary_schedule_stress/sha256/{identity}/run_manifest.json"},
            "limitations": contract["limitations"],
        }
        manifest_dir = output / "manifests/preliminary_schedule_stress/sha256" / identity
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_out = manifest_dir / "run_manifest.json"
        serialized = canonical_json(manifest) + b"\n"
        if manifest_out.exists() and manifest_out.read_bytes() != serialized:
            raise ValueError("immutable manifest collision")
        manifest_out.write_bytes(serialized)
        print(json.dumps({"result": "PASS", "identity": identity, "manifest_sha256": sha256_file(manifest_out), "payload": payload_info, "diagnostics": diagnostics}, sort_keys=True))
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

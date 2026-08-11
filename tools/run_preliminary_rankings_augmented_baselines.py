from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

import polars as pl


BASELINE_RUN = "3977b720c69dc75559b1f18ed5ab665ab2262e64fe97dc74dd9668ac09604d08"
BASELINE_MANIFEST_SHA = "27cb3b0ec782a0a97d474ff4a7d3c5710f57556ef412440f91fd2e246d091508"
RANKINGS_RUN = "a7743bb76680c5034b3b15bcccff76961af400f949fd7de0f3feb0db33acaa7e"
RANKINGS_FEATURE_ID = "b165e076222104d71f345cf294d5b177d2c049bf1168b11c29e9cc5690375274"
RANKINGS_FEATURE_SHA = "f7bade2b2653df3c4f82927beaf3ba7dc254c6bb8487849f980a2eac6f0c3a4e"


def load_base_runner(repo_root: Path) -> Any:
    path = repo_root / "tools/run_preliminary_unprotected_baselines.py"
    spec = importlib.util.spec_from_file_location("preliminary_base_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load baseline runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def all_metrics(manifest: dict[str, Any], family: str, slice_id: str) -> dict[str, Any]:
    return next(row for row in manifest["metrics"][family] if row["slice"] == slice_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-data-root", type=Path)
    parser.add_argument("--issued-at-utc", required=True)
    parser.add_argument("--summary-path", type=Path)
    args = parser.parse_args()
    repo_root, data_root = args.repo_root.resolve(), args.data_root.resolve()
    output_root = args.output_data_root.resolve() if args.output_data_root else data_root
    sys.path.insert(0, str(repo_root / "src"))
    from aggie_analytics.modeling import preliminary_rankings as helpers

    issued = datetime.fromisoformat(args.issued_at_utc.replace("Z", "+00:00"))
    if issued.tzinfo is None:
        raise ValueError("issued-at-utc must be timezone aware")
    base = load_base_runner(repo_root)
    base.RUN_VERSION = helpers.RUN_VERSION
    contract_path = repo_root / "configs/preliminary_rankings_augmented_contract.json"
    baseline_path = data_root / "manifests/preliminary_unprotected/sha256" / BASELINE_RUN / "run_manifest.json"
    rankings_manifest_path = data_root / "manifests/historical_rankings_pit/sha256" / RANKINGS_RUN / "rankings_pit_manifest.json"
    rankings_path = data_root / "features/historical_rankings/sha256" / RANKINGS_FEATURE_ID / "rankings_pit_features.parquet"
    for path, expected in (
        (baseline_path, BASELINE_MANIFEST_SHA),
        (rankings_path, RANKINGS_FEATURE_SHA),
    ):
        if not path.is_file() or helpers.sha256_file(path) != expected:
            raise ValueError(f"pinned input missing or drifted: {path}")
    baseline_manifest = json.loads(baseline_path.read_text(encoding="utf-8"))
    rankings_manifest = json.loads(rankings_manifest_path.read_text(encoding="utf-8"))
    if rankings_manifest["feature_identity"] != RANKINGS_FEATURE_ID:
        raise ValueError("rankings feature identity drift")

    inputs = base.load_inputs(repo_root, data_root, helpers)
    features, targets, assignments, tamu_team_id, population = base.materialize_dataset(inputs, helpers)
    features, rank_coverage = helpers.augment_with_rankings(
        features, pl.read_parquet(rankings_path).to_dicts()
    )
    rows = base.joined_rows(features, targets)
    if [row["target_game_id"] for row in rows] != [
        row["target_game_id"] for row in pl.read_parquet(
            data_root / baseline_manifest["external_locations"]["training"] / "training_matrix.parquet"
        ).sort(["start_utc", "target_game_id"]).to_dicts()
    ]:
        raise ValueError("augmented replay target rows differ from baseline")

    code = {
        "base_module_sha256": helpers.sha256_file(repo_root / "src/aggie_analytics/modeling/preliminary.py"),
        "rankings_module_sha256": helpers.sha256_file(repo_root / "src/aggie_analytics/modeling/preliminary_rankings.py"),
        "runner_sha256": helpers.sha256_file(Path(__file__).resolve()),
        "base_runner_sha256": helpers.sha256_file(repo_root / "tools/run_preliminary_unprotected_baselines.py"),
        "validator_sha256": helpers.sha256_file(repo_root / "tools/validate_preliminary_rankings_augmented_baselines.py"),
    }
    tmp_root = output_root / "tmp/preliminary_unprotected"
    tmp_root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="rankings-augmented-v1-", dir=tmp_root))
    try:
        dataset_stage = stage / "dataset"
        payloads = []
        for records, name in (
            (features, "feature_matrix.parquet"),
            (targets, "outcome_targets.parquet"),
            (assignments, "split_assignments.parquet"),
            (rows, "training_matrix.parquet"),
        ):
            info = base.write_parquet(records, dataset_stage / name, ["start_utc", "target_game_id"])
            info["sha256"] = helpers.sha256_file(dataset_stage / name)
            payloads.append(info)
        basis = {
            "run_version": helpers.RUN_VERSION,
            "classification": helpers.CLASSIFICATION,
            "contract_sha256": helpers.sha256_file(contract_path),
            "input_identities": {
                "baseline_run": BASELINE_RUN,
                "team_outcome_replay": base.REPLAY_IDENTITY,
                "rankings_run": RANKINGS_RUN,
                "rankings_features": RANKINGS_FEATURE_ID,
            },
            "code_identities": code,
            "feature_columns": list(helpers.FEATURE_COLUMNS),
            "payloads": sorted(payloads, key=lambda row: row["name"]),
        }
        dataset_id = helpers.stable_hash(basis)
        base.move_or_verify(dataset_stage, output_root / "training/preliminary_unprotected/sha256" / dataset_id, helpers.sha256_file)
        predictions, model_specs, diagnostics = base.train_models(rows, inputs["paths"]["accepted_game_outcomes"], helpers)
        models = base.serialize_models(model_specs, dataset_id, output_root, stage, helpers)
        model_ids = {row["family"]: row["model_identity"] for row in models}
        feature_id = helpers.stable_hash({"dataset_identity": dataset_id, "feature_columns": list(helpers.FEATURE_COLUMNS)})
        target_id = helpers.stable_hash({"dataset_identity": dataset_id, "target_policy": "completed-official-outcome-target-v1"})
        split_id = helpers.stable_hash({"dataset_identity": dataset_id, "split_policy": {"2023":"FIT","2024":"TUNE","2025":"EVALUATION_UNPROTECTED"}})
        for row in predictions:
            row.update({"model_identity": model_ids[row["model_id"]], "dataset_identity": dataset_id, "feature_identity": feature_id, "target_identity": target_id, "split_identity": split_id})
        forecast_stage = stage / "forecast"
        forecast = base.write_parquet(predictions, forecast_stage / "predictions.parquet", ["model_id", "start_utc", "target_game_id"])
        forecast["sha256"] = helpers.sha256_file(forecast_stage / "predictions.parquet")
        forecast_id = helpers.stable_hash({"dataset_identity": dataset_id, "models": sorted(model_ids.values()), "payload": forecast})
        base.move_or_verify(forecast_stage, output_root / "forecast_snapshots/preliminary_unprotected/sha256" / forecast_id, helpers.sha256_file)
        metrics = {family: helpers.metrics_by_season_and_slice([r for r in predictions if r["model_id"] == family], tamu_team_id) for family in sorted(model_ids)}
        comparison = {}
        for family in sorted(model_ids):
            old = all_metrics(baseline_manifest, family, "SEASON_2025_ALL")
            new = next(row for row in metrics[family] if row["slice"] == "SEASON_2025_ALL")
            comparison[family] = {
                "rows_equal": old["probability"]["rows"] == new["probability"]["rows"],
                "brier_delta_augmented_minus_baseline": new["probability"]["brier"] - old["probability"]["brier"],
                "log_loss_delta_augmented_minus_baseline": new["probability"]["log_loss"] - old["probability"]["log_loss"],
            }
        run_id = helpers.stable_hash({"run_version": helpers.RUN_VERSION, "dataset_identity": dataset_id, "feature_identity": feature_id, "target_identity": target_id, "split_identity": split_id, "model_identities": model_ids, "forecast_identity": forecast_id, "code": code})
        manifest = {
            "schema_version": "1.0.0", "artifact_type": "PRELIMINARY_UNPROTECTED_RANKINGS_AUGMENTED_RUN",
            "classification": helpers.CLASSIFICATION, "decision_unit": "POST-SUBTASK-171", "run_version": helpers.RUN_VERSION,
            "run_identity": run_id, "issued_at_utc": issued.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "input_identities": basis["input_identities"], "code_identities": code, "dataset_identity": dataset_id,
            "feature_identity": feature_id, "target_identity": target_id, "split_identity": split_id, "forecast_identity": forecast_id,
            "model_identities": model_ids, "dataset_payloads": payloads, "forecast_payload": forecast, "models": models,
            "population": {**population, "rankings_coverage": rank_coverage, "feature_count": len(helpers.FEATURE_COLUMNS)},
            "metrics": helpers.sanitize_for_json(metrics), "baseline_comparison": helpers.sanitize_for_json(comparison),
            "diagnostics": helpers.sanitize_for_json(diagnostics),
            "leakage_validation": {**population["split_validation"], "rankings_future_rows": 0, "rankings_target_outcome_fields": 0, "same_target_rows_as_baseline": "PASS", "protected_split_opened": False},
            "external_locations": {"training": f"training/preliminary_unprotected/sha256/{dataset_id}", "models": "model_artifacts/preliminary_unprotected/sha256/<model_identity>", "forecast": f"forecast_snapshots/preliminary_unprotected/sha256/{forecast_id}", "manifest": f"manifests/preliminary_unprotected/sha256/{run_id}/run_manifest.json"},
            "limitations": ["All artifacts and metrics are PRELIMINARY_UNPROTECTED.", "Numeric AP rank difference is missing unless both teams have a numeric rank; no unranked value is fabricated.", "Sparse rankings coverage is represented by explicit poll/listing/rank-observed indicators.", "No protected promotion or scientific result is established."],
            "protected_nonclaims": json.loads(contract_path.read_text(encoding="utf-8"))["protected_nonclaims"],
        }
        manifest_stage = stage / "manifest"; manifest_stage.mkdir(parents=True)
        manifest_file = manifest_stage / "run_manifest.json"; manifest_file.write_bytes(helpers.canonical_json(manifest) + b"\n")
        manifest_sha = helpers.sha256_file(manifest_file)
        base.move_or_verify(manifest_stage, output_root / "manifests/preliminary_unprotected/sha256" / run_id, helpers.sha256_file)
        result = {"result":"PASS", "run_identity":run_id, "manifest_sha256":manifest_sha, "dataset_identity":dataset_id, "feature_identity":feature_id, "target_identity":target_id, "split_identity":split_id, "forecast_identity":forecast_id, "model_identities":model_ids, "rankings_coverage":rank_coverage, "baseline_comparison":comparison}
        payload = json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
        if args.summary_path:
            args.summary_path.parent.mkdir(parents=True, exist_ok=True); args.summary_path.write_text(payload, encoding="utf-8")
        print(payload, end="")
    finally:
        if stage.exists(): shutil.rmtree(stage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

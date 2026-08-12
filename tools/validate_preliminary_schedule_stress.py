from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
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
    parser.add_argument("--identity", required=True)
    parser.add_argument("--report-path", type=Path, required=True)
    args = parser.parse_args()
    repo, data = args.repo_root.resolve(), args.data_root.resolve()
    sys.path.insert(0, str(repo / "src"))
    from aggie_analytics.features.schedule_stress import materialize, stable_hash

    contract_path = repo / "configs/preliminary_schedule_stress_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    manifest_path = data / "manifests/preliminary_schedule_stress/sha256" / args.identity / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: list[dict[str, object]] = []

    def check(name: str, condition: bool, detail: object = None) -> None:
        checks.append({"check": name, "result": "PASS" if condition else "FAIL", "detail": detail})

    check("identity", manifest["identity"] == args.identity)
    check("classification", manifest["classification"] == contract["classification"])
    check("decision_units", manifest["decision_units"] == contract["decision_units"])
    check("historical_pit_closed", manifest["leakage_validation"]["historical_original_pit_eligible"] is False)
    check("protected_closed", manifest["leakage_validation"]["protected_eligible"] is False)
    source = contract["source"]
    source_manifest_path = data / "manifests/preliminary_event_chronology/sha256" / source["run_identity"] / "run_manifest.json"
    check("source_manifest_hash", sha256_file(source_manifest_path) == source["manifest_sha256"])
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    matrix_path = data / source_manifest["external_locations"]["training"] / "training_matrix.parquet"
    check("source_matrix_hash", sha256_file(matrix_path) == source["training_matrix_sha256"])
    check("source_dataset", source_manifest["dataset_identity"] == source["dataset_identity"])
    payload_path = data / manifest["external_locations"]["features"]
    check("payload_exists", payload_path.is_file())
    check("payload_hash", sha256_file(payload_path) == manifest["payload"]["sha256"])
    frame = pl.read_parquet(payload_path)
    check("payload_rows", frame.height == contract["acceptance"]["target_team_rows"])
    check("target_games", frame["game_id"].n_unique() == contract["acceptance"]["target_games"])
    check("target_game_team_unique", frame.select(pl.struct(["game_id", "team_id"]).n_unique()).item() == frame.height)
    check("two_rows_per_game", frame.group_by("game_id").len().filter(pl.col("len") != 2).height == 0)
    check("home_away_roles", frame.group_by("game_id").agg(pl.col("team_role").n_unique().alias("roles")).filter(pl.col("roles") != 2).height == 0)
    check("classification_rows", set(frame["classification"].unique()) == {contract["classification"]})
    check("protected_rows_false", frame.filter(pl.col("protected_eligible") != False).height == 0)  # noqa: E712
    check("historical_pit_rows_false", frame.filter(pl.col("historical_original_pit_eligible") != False).height == 0)  # noqa: E712
    check("event_chronology_rows_true", frame.filter(pl.col("event_chronology_eligible") != True).height == 0)  # noqa: E712
    check("source_before_cutoff", frame.filter(pl.col("evidence_source_start_utc_max").is_not_null() & (pl.col("evidence_source_start_utc_max") >= pl.col("cutoff_utc"))).height == 0)
    check("nonnegative_counts", frame.filter((pl.col("prior_game_count") < 0) | (pl.col("games_last_7d") < 0) | (pl.col("games_last_14d") < 0) | (pl.col("games_last_28d") < 0)).height == 0)
    check("nested_windows", frame.filter((pl.col("games_last_7d") > pl.col("games_last_14d")) | (pl.col("games_last_14d") > pl.col("games_last_28d"))).height == 0)
    check("away_window_bounded", frame.filter(pl.col("away_or_neutral_games_last_28d") > pl.col("games_last_28d")).height == 0)
    check("cold_start_count", frame.filter(pl.col("cold_start")).height == manifest["diagnostics"]["cold_start_rows"])
    check("cold_start_missing_days", frame.filter(pl.col("cold_start") & pl.col("days_since_last_game_start").is_not_null()).height == 0)
    check("noncold_positive_days", frame.filter((~pl.col("cold_start")) & (pl.col("days_since_last_game_start") <= 0)).height == 0)
    check("lineage_unique", frame["feature_row_identity"].n_unique() == frame.height)
    code = manifest["code_identities"]
    check("contract_hash", sha256_file(contract_path) == code["contract_sha256"])
    check("module_hash", sha256_file(repo / "src/aggie_analytics/features/schedule_stress.py") == code["module_sha256"])
    check("builder_hash", sha256_file(repo / "tools/build_preliminary_schedule_stress.py") == code["builder_sha256"])
    expected_identity = stable_hash({"source": source, "payload": manifest["payload"], "code": code})
    check("identity_rebuild", expected_identity == args.identity)

    rebuilt, diagnostics = materialize(pl.read_parquet(matrix_path).to_dicts(), set(source["target_seasons"]))
    check("diagnostics_rebuild", diagnostics == manifest["diagnostics"])
    check("row_rebuild", rebuilt == frame.to_dicts())
    validation_root = data / "validation/TASK-079"
    validation_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bat182-validate-", dir=validation_root) as directory:
        rebuilt_path = Path(directory) / payload_path.name
        pl.DataFrame(rebuilt).write_parquet(rebuilt_path, compression="zstd", statistics=True)
        check("byte_identical_rebuild", sha256_file(rebuilt_path) == manifest["payload"]["sha256"])

    failures = [row for row in checks if row["result"] == "FAIL"]
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "PRELIMINARY_SCHEDULE_STRESS_VALIDATION",
        "identity": args.identity,
        "manifest_sha256": sha256_file(manifest_path),
        "result": "PASS" if not failures else "FAIL",
        "checks_passed": len(checks) - len(failures),
        "checks_failed": len(failures),
        "checks": checks,
        "failures": failures,
    }
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["result"], "checks_passed": report["checks_passed"], "checks_failed": report["checks_failed"], "report_sha256": sha256_file(args.report_path)}, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

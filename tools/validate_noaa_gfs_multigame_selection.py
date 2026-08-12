from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aggie_analytics.features.gfs_multigame_selection import (  # noqa: E402
    candidate_runs,
    load_population,
    materialize,
)
from aggie_analytics.features.gfs_issued_run import (  # noqa: E402
    _write_immutable,
    parse_utc,
    sha256_file,
    stable_hash,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--dataset-identity", required=True)
    parser.add_argument("--rebuild-root", type=Path, required=True)
    args = parser.parse_args()
    data_root, rebuild_parent = args.data_root.resolve(), args.rebuild_root.resolve()
    contract_path = ROOT / "configs/noaa_gfs_multigame_selection_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    population = {row["selector_identity"]: row for row in load_population(data_root, contract)}
    base = data_root / contract["artifact_roots"]["manifests"] / args.dataset_identity
    manifest_path, capture_path = base / "run_manifest.json", base / "capture_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    checks = []

    def check(name: str, condition: bool, detail=None) -> None:
        checks.append({"check": name, "result": "PASS" if condition else "FAIL", "detail": detail})

    check("dataset_identity", manifest["dataset_identity"] == args.dataset_identity)
    check("classification", manifest["classification"] == contract["classification"])
    check("authority", manifest["authority"] == contract["authority"])
    check(
        "transformation_implementation",
        manifest["transformation_implementation_sha256"]
        == sha256_file(ROOT / "src/aggie_analytics/features/gfs_multigame_selection.py"),
    )
    check("decoder_version", manifest["decoder"]["package_version"] == contract["decoder"]["package_version"])
    check("decoder_api_version", manifest["decoder"]["api_version"] == contract["decoder"]["api_version"])
    check("polars_version", manifest["decoder"]["polars_package_version"] == contract["decoder"]["polars_package_version"])
    capture_core = {
        key: capture[key]
        for key in (
            "schema_version",
            "artifact_type",
            "classification",
            "contract_sha256",
            "acquisition_implementation_sha256",
            "input_sha256",
            "selection_identities",
        )
    }
    check("capture_identity", stable_hash(capture_core) == capture["capture_manifest_identity"])
    check(
        "acquisition_implementation",
        capture["acquisition_implementation_sha256"]
        == sha256_file(ROOT / "tools/build_noaa_gfs_multigame_selection.py"),
    )
    check("capture_binding", manifest["capture_manifest_identity"] == capture["capture_manifest_identity"])
    check("selection_count", len(capture["selections"]) == contract["population"]["expected_selection_rows"])
    check("selector_population", {row["selector_identity"] for row in capture["selections"]} == set(population))
    for selection in capture["selections"]:
        source = population[selection["selector_identity"]]
        cutoff = parse_utc(source["nominal_prediction_at_utc"])
        valid = parse_utc(source["forecast_valid_hour_utc"])
        candidates = candidate_runs(
            cutoff,
            valid,
            cycles_to_probe=contract["selection"]["cycles_to_probe"],
            maximum_forecast_hour=contract["selection"]["maximum_forecast_hour"],
        )
        attempts = selection["selection_attempts"]
        check(
            f"attempt_population:{selection['selector_identity']}",
            len(attempts) <= len(candidates)
            and [row["object_key"] for row in attempts] == [row["object_key"] for row in candidates[: len(attempts)]],
        )
        check(f"selected_is_final_attempt:{selection['selector_identity']}", attempts[-1]["disposition"] == "AVAILABLE_BY_CUTOFF")
        check(f"prior_attempts_ineligible:{selection['selector_identity']}", all(a["disposition"] != "AVAILABLE_BY_CUTOFF" for a in attempts[:-1]))
        check(f"selected_key:{selection['selector_identity']}", attempts[-1]["object_key"] == selection["object_key"])
        check(f"initialization_before_cutoff:{selection['selector_identity']}", parse_utc(selection["initialization_utc"]) <= cutoff)
        check(f"publication_before_cutoff:{selection['selector_identity']}", parse_utc(selection["object_last_modified_utc"]) <= cutoff)
        check(
            f"forecast_hour:{selection['selector_identity']}",
            int((valid - parse_utc(selection["initialization_utc"])).total_seconds() / 3600) == selection["forecast_hour"],
        )
        selection_core = {
            "selector_identity": selection["selector_identity"],
            "source_game_id": selection["source_game_id"],
            "cutoff_utc": selection["cutoff_utc"],
            "valid_utc": selection["valid_utc"],
            "initialization_utc": selection["initialization_utc"],
            "forecast_hour": selection["forecast_hour"],
            "object_key": selection["object_key"],
            "object_last_modified_utc": selection["object_last_modified_utc"],
            "object_bytes": selection["object_bytes"],
            "index_raw_sha256": selection["index_raw_sha256"],
            "selection_attempts_sha256": selection["selection_attempts_sha256"],
            "message_capture_sha256": selection["message_capture_sha256"],
        }
        check(f"selection_identity:{selection['selector_identity']}", stable_hash(selection_core) == selection["selection_identity"])
        check(
            f"attempt_identity:{selection['selector_identity']}",
            stable_hash(attempts) == selection["selection_attempts_sha256"],
        )
        check(f"message_count:{selection['selector_identity']}", len(selection["message_captures"]) == len(contract["messages"]))
        precipitation = [row for row in selection["message_captures"] if row["component"] == "precipitation_accumulation"]
        check(f"precipitation_window:{selection['selector_identity']}", len(precipitation) == 1 and precipitation[0]["accumulation_hours"] > 0)
        for row in selection["message_captures"]:
            path = data_root / row["raw_relative_path"]
            check(
                f"raw:{selection['selector_identity']}:{row['component']}",
                path.is_file() and sha256_file(path) == row["raw_sha256"],
            )
    payload = data_root / manifest["payload"]["path"]
    check("payload", payload.is_file() and sha256_file(payload) == manifest["payload"]["sha256"])
    pl = __import__("polars")
    frame = pl.read_parquet(payload)
    check("row_count", frame.height == contract["population"]["expected_output_rows"])
    check("selector_rows", frame["selector_identity"].n_unique() == contract["population"]["expected_selection_rows"])
    check("variables_per_selector", frame.group_by("selector_identity").len().filter(pl.col("len") != 10).height == 0)
    check("natural_key", frame.select("selector_identity", "weather_variable").unique().height == frame.height)
    check("all_pit_candidate", frame.filter(pl.col("historical_pit_candidate") != True).height == 0)  # noqa: E712
    check("issued_run_available", frame.filter(pl.col("issued_run_available_by_cutoff") != True).height == 0)  # noqa: E712
    check("venue_coordinate_not_historical", frame.filter(pl.col("venue_coordinate_historical_eligibility") != False).height == 0)  # noqa: E712
    check("weather_feature_not_pit_eligible", frame.filter(pl.col("weather_feature_pit_eligible") != False).height == 0)  # noqa: E712
    check("no_training_admission", frame.filter(pl.col("training_feature_admitted") != False).height == 0)  # noqa: E712
    check("no_protected_admission", frame.filter(pl.col("protected_eligible") != False).height == 0)  # noqa: E712
    check("finite_values", frame.filter(~pl.col("value").is_finite()).height == 0)
    precip = frame.filter(pl.col("weather_variable") == "precipitation_accumulation")
    check("precipitation_duration_preserved", precip.filter(pl.col("accumulation_hours").is_null() | (pl.col("accumulation_hours") <= 0)).height == 0)
    check("nonprecipitation_duration_null", frame.filter((pl.col("weather_variable") != "precipitation_accumulation") & pl.col("accumulation_hours").is_not_null()).height == 0)
    rebuild_parent.mkdir(parents=True, exist_ok=True)
    rebuild = Path(tempfile.mkdtemp(prefix="bat417-gfs-multi-", dir=rebuild_parent))
    try:
        rebuilt = materialize(
            data_root=data_root,
            output_root=rebuild,
            repo_root=ROOT,
            capture_manifest=capture,
            issued_at_utc=manifest["issued_at_utc"],
        )
        check("rebuild_identity", rebuilt["dataset_identity"] == args.dataset_identity)
        check("payload_byte_identical", sha256_file(rebuild / manifest["payload"]["path"]) == manifest["payload"]["sha256"])
        check("manifest_byte_identical", sha256_file(Path(rebuilt["manifest_path"])) == sha256_file(manifest_path))
    finally:
        shutil.rmtree(rebuild, ignore_errors=False)
    failures = [row for row in checks if row["result"] == "FAIL"]
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "NOAA_GFS_MULTIGAME_SELECTION_VALIDATION",
        "classification": contract["classification"],
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "dataset_identity": args.dataset_identity,
        "manifest_sha256": sha256_file(manifest_path),
        "capture_manifest_sha256": sha256_file(capture_path),
        "result": "PASS" if not failures else "FAIL",
        "checks_passed": len(checks) - len(failures),
        "checks_failed": len(failures),
        "checks": checks,
        "failures": failures,
        "authority": contract["authority"],
        "scientific_nonclaims": contract["scientific_nonclaims"],
    }
    report_path = (
        data_root
        / contract["artifact_roots"]["validation"]
        / "sha256"
        / args.dataset_identity
        / "validation.json"
    )
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    _write_immutable(report_path, encoded)
    print(
        json.dumps(
            {
                "result": report["result"],
                "checks_passed": report["checks_passed"],
                "checks_failed": report["checks_failed"],
                "report_path": str(report_path),
                "report_sha256": sha256_file(report_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

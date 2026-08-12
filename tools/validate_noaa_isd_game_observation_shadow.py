from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aggie_analytics.features.observed_weather_shadow import materialize, sha256_file, stable_hash  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--dataset-identity", required=True)
    args = parser.parse_args()
    data_root = args.data_root.resolve()
    contract = json.loads((ROOT / "configs/noaa_isd_game_observation_shadow_contract.json").read_text(encoding="utf-8"))
    artifact_root = data_root / contract["artifact_roots"]["manifests"] / args.dataset_identity
    manifest_path = artifact_root / "run_manifest.json"
    capture_path = artifact_root / "capture_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        checks.append({"check": name, "result": "PASS" if condition else "FAIL", "detail": detail})

    check("dataset_identity", manifest["dataset_identity"] == args.dataset_identity)
    check("classification", manifest["classification"] == contract["classification"])
    check("authority", manifest["authority"] == contract["authority"])
    check("capture_identity_binding", capture["capture_manifest_identity"] == manifest["capture_manifest_identity"])
    capture_core = {key: capture[key] for key in ("schema_version", "artifact_type", "classification", "contract_sha256", "football_season", "station_year_pairs")}
    check("capture_identity_recomputed", stable_hash(capture_core) == capture["capture_manifest_identity"])
    check("capture_count", capture["capture_count"] == contract["population"]["expected_unique_station_years"])
    check("calendar_2025_captures", capture["calendar_2025_captures"] == contract["population"]["expected_2025_station_years"])
    check("reused_2024_captures", capture["reused_2024_captures"] == contract["population"]["expected_2024_station_years"])
    check("capture_pair_unique", len({(row["calendar_year"], row["station_id"]) for row in capture["captures"]}) == capture["capture_count"])
    for row in capture["captures"]:
        path = data_root / row["raw_relative_path"]
        check(f"capture_payload:{row['calendar_year']}:{row['station_id']}", path.is_file() and sha256_file(path) == row["raw_sha256"])
    payload_path = data_root / manifest["payload"]["path"]
    check("payload_identity", payload_path.is_file() and sha256_file(payload_path) == manifest["payload"]["sha256"])
    pl = __import__("polars")
    frame = pl.read_parquet(payload_path)
    check("game_rows", frame.height == contract["population"]["expected_games"] == manifest["population"]["games"])
    check("game_identity_unique", frame["source_game_id"].n_unique() == frame.height)
    check("calendar_2024_games", frame.filter(pl.col("calendar_year") == 2024).height == contract["population"]["expected_calendar_year_2024_games"])
    check("calendar_2025_games", frame.filter(pl.col("calendar_year") == 2025).height == contract["population"]["expected_calendar_year_2025_games"])
    check("nearest_present", frame.filter(pl.col("nearest_observation_state") == "PRESENT").height == frame.height)
    check("delta_nonnegative", frame.filter(pl.col("nearest_absolute_delta_minutes") < 0).height == 0)
    check("no_time_threshold", manifest["selection"]["maximum_time_delta_minutes"] is None)
    check("no_station_acceptance", set(frame["station_acceptance_state"]) == {"CANDIDATE_REVIEW_REQUIRED"})
    check("no_pit_admission", frame.filter(pl.col("historical_pit_eligible") != False).height == 0)  # noqa: E712
    check("no_training_admission", frame.filter(pl.col("training_feature_eligible") != False).height == 0)  # noqa: E712
    check("no_protected_admission", frame.filter(pl.col("protected_eligible") != False).height == 0)  # noqa: E712
    check("no_observed_substitution", frame.filter(pl.col("observed_weather_substitution") != False).height == 0)  # noqa: E712
    check("dome_feature_closed", frame.filter(pl.col("dome_observation_feature_eligible") != False).height == 0)  # noqa: E712
    check("lineage_unique", frame["row_lineage_sha256"].n_unique() == frame.height)
    check("long_delta_preserved", frame.filter(pl.col("nearest_absolute_delta_minutes") > 1440).height > 0)
    check("raw_fields_preserved", all(name in frame.columns for name in ("nearest_raw_tmp", "nearest_raw_dew", "nearest_raw_wnd", "nearest_raw_vis", "nearest_raw_slp")))
    runtime_root = data_root / "validation/runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    rebuild_root = Path(tempfile.mkdtemp(prefix="bat417-game-observation-shadow-", dir=runtime_root))
    try:
        rebuilt = materialize(data_root=data_root, output_root=rebuild_root, repo_root=ROOT, capture_manifest=capture, issued_at_utc=manifest["issued_at_utc"])
        check("rebuild_identity", rebuilt["dataset_identity"] == args.dataset_identity)
        check("payload_byte_identical", sha256_file(rebuild_root / manifest["payload"]["path"]) == manifest["payload"]["sha256"])
        rebuilt_manifest = rebuild_root / contract["artifact_roots"]["manifests"] / args.dataset_identity / "run_manifest.json"
        check("manifest_byte_identical", sha256_file(rebuilt_manifest) == sha256_file(manifest_path))
    finally:
        shutil.rmtree(rebuild_root, ignore_errors=False)
    failures = [row for row in checks if row["result"] == "FAIL"]
    delta = frame["nearest_absolute_delta_minutes"]
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "NOAA_ISD_GAME_OBSERVATION_SHADOW_VALIDATION",
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
        "coverage_diagnostics_not_acceptance_thresholds": {
            "games_at_or_below_15_minutes": frame.filter(delta <= 15).height,
            "games_at_or_below_30_minutes": frame.filter(delta <= 30).height,
            "games_at_or_below_60_minutes": frame.filter(delta <= 60).height,
            "games_at_or_below_1440_minutes": frame.filter(delta <= 1440).height,
            "games_above_1440_minutes": frame.filter(delta > 1440).height,
            "maximum_minutes": delta.max(),
        },
        "cleanup": {"rebuild_removed": not rebuild_root.exists()},
        "authority": contract["authority"],
        "scientific_nonclaims": contract["scientific_nonclaims"],
    }
    report_path = data_root / contract["artifact_roots"]["validation"] / "sha256" / args.dataset_identity / "validation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    if report_path.exists() and report_path.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("game observation validation collision")
    report_path.write_text(encoded, encoding="utf-8")
    print(json.dumps({"result": report["result"], "checks_passed": report["checks_passed"], "checks_failed": report["checks_failed"], "report_path": str(report_path), "report_sha256": sha256_file(report_path), "coverage_diagnostics": report["coverage_diagnostics_not_acceptance_thresholds"]}, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

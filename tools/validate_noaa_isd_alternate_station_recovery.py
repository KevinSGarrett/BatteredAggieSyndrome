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

from aggie_analytics.features.alternate_station_recovery import materialize  # noqa: E402
from aggie_analytics.features.observed_weather_shadow import sha256_file, stable_hash  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--dataset-identity", required=True)
    args = parser.parse_args()
    data_root = args.data_root.resolve()
    contract = json.loads((ROOT / "configs/noaa_isd_alternate_station_recovery_contract.json").read_text(encoding="utf-8"))
    root = data_root / contract["artifact_roots"]["manifests"] / args.dataset_identity
    manifest_path, capture_path = root / "run_manifest.json", root / "capture_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        checks.append({"check": name, "result": "PASS" if condition else "FAIL", "detail": detail})

    check("dataset_identity", manifest["dataset_identity"] == args.dataset_identity)
    check("classification", manifest["classification"] == contract["classification"])
    check("authority", manifest["authority"] == contract["authority"])
    check("capture_binding", manifest["capture_manifest_identity"] == capture["capture_manifest_identity"])
    capture_core = {key: capture[key] for key in ("schema_version", "artifact_type", "classification", "contract_sha256", "station_year_pairs")}
    check("capture_identity", stable_hash(capture_core) == capture["capture_manifest_identity"])
    check("capture_count", capture["capture_count"] == contract["population"]["expected_unique_alternate_station_years"])
    check("capture_reuse", capture["prior_capture_reuse"] == contract["population"]["expected_prior_capture_reuse"])
    check("capture_new_or_cache", capture["new_or_request_cache"] == contract["population"]["expected_new_or_request_cache_station_years"])
    for row in capture["captures"]:
        path = data_root / row["raw_relative_path"]
        check(f"capture_payload:{row['station_id']}", path.is_file() and sha256_file(path) == row["raw_sha256"])
    pl = __import__("polars")
    frames = {}
    for payload in manifest["payloads"]:
        path = data_root / payload["path"]
        check(f"payload:{payload['role']}", path.is_file() and sha256_file(path) == payload["sha256"])
        frames[payload["role"]] = pl.read_parquet(path)
    comparisons = frames["ALTERNATE_COMPARISONS"]
    best = frames["BEST_TIME_DELTA_PER_GAME_REVIEW_ONLY"]
    check("comparison_rows", comparisons.height == contract["population"]["expected_game_candidate_rows"])
    check("failed_games", comparisons["source_game_id"].n_unique() == contract["population"]["expected_games"])
    check("four_ranks_each", comparisons.group_by("source_game_id").len().filter(pl.col("len") != 4).height == 0)
    check("comparison_key_unique", comparisons.select("source_game_id", "station_rank").unique().height == comparisons.height)
    check("best_review_rows", best.height == contract["population"]["expected_games"])
    check("all_games_recovered_within_60_diagnostic", best.filter(pl.col("nearest_absolute_delta_minutes") <= 60).height == best.height)
    check("no_automatic_selection", comparisons.filter(pl.col("automatic_alternate_selection") != False).height == 0)  # noqa: E712
    check("no_station_acceptance", set(comparisons["station_acceptance_state"]) == {"CANDIDATE_REVIEW_REQUIRED"})
    check("no_feature_admission", comparisons.filter(pl.col("game_feature_eligible") != False).height == 0)  # noqa: E712
    check("no_pit_admission", comparisons.filter(pl.col("historical_pit_eligible") != False).height == 0)  # noqa: E712
    check("no_protected_admission", comparisons.filter(pl.col("protected_eligible") != False).height == 0)  # noqa: E712
    check("best_not_selection_authority", manifest["population"]["best_time_delta_is_selection_authority"] is False)
    check("lineage_unique", comparisons["row_lineage_sha256"].n_unique() == comparisons.height)
    runtime = data_root / "validation/runtime"; runtime.mkdir(parents=True, exist_ok=True)
    rebuild = Path(tempfile.mkdtemp(prefix="bat417-alternate-station-", dir=runtime))
    try:
        rebuilt = materialize(data_root=data_root, output_root=rebuild, repo_root=ROOT, capture_manifest=capture, issued_at_utc=manifest["issued_at_utc"])
        check("rebuild_identity", rebuilt["dataset_identity"] == args.dataset_identity)
        for payload in manifest["payloads"]:
            check(f"byte_identical:{payload['role']}", sha256_file(rebuild / payload["path"]) == payload["sha256"])
        rebuilt_manifest = rebuild / contract["artifact_roots"]["manifests"] / args.dataset_identity / "run_manifest.json"
        check("manifest_byte_identical", sha256_file(rebuilt_manifest) == sha256_file(manifest_path))
    finally:
        shutil.rmtree(rebuild, ignore_errors=False)
    failures = [row for row in checks if row["result"] == "FAIL"]
    report = {
        "schema_version": "1.0.0", "artifact_type": "NOAA_ISD_ALTERNATE_STATION_RECOVERY_VALIDATION",
        "classification": contract["classification"], "decision_unit": contract["decision_unit"], "jira_key": contract["jira_key"],
        "dataset_identity": args.dataset_identity, "manifest_sha256": sha256_file(manifest_path), "capture_manifest_sha256": sha256_file(capture_path),
        "result": "PASS" if not failures else "FAIL", "checks_passed": len(checks) - len(failures), "checks_failed": len(failures),
        "checks": checks, "failures": failures, "population": manifest["population"], "cleanup": {"rebuild_removed": not rebuild.exists()},
        "authority": contract["authority"], "scientific_nonclaims": contract["scientific_nonclaims"],
    }
    report_path = data_root / contract["artifact_roots"]["validation"] / "sha256" / args.dataset_identity / "validation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    if report_path.exists() and report_path.read_text(encoding="utf-8") != encoded: raise RuntimeError("alternate validation collision")
    report_path.write_text(encoded, encoding="utf-8")
    print(json.dumps({"result": report["result"], "checks_passed": report["checks_passed"], "checks_failed": report["checks_failed"], "report_path": str(report_path), "report_sha256": sha256_file(report_path), "population": report["population"]}, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
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

from aggie_analytics.features.weather_station_matching import materialize, sha256_file  # noqa: E402


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--dataset-identity", required=True)
    parser.add_argument("--report-path", type=Path, required=True)
    args = parser.parse_args()
    repo_root, data_root = args.repo_root.resolve(), args.data_root.resolve()
    contract = json.loads((repo_root / "configs/noaa_isd_station_matching_contract.json").read_text(encoding="utf-8"))
    manifest_path = data_root / contract["artifact_roots"]["manifests"] / args.dataset_identity / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        checks.append({"check": name, "result": "PASS" if condition else "FAIL", "detail": detail})

    check("dataset_identity", manifest["dataset_identity"] == args.dataset_identity)
    check("classification", manifest["classification"] == contract["classification"])
    check("authority", manifest["authority"] == contract["authority"])
    check("no_automatic_threshold", manifest["matching_contract"]["automatic_distance_acceptance_threshold"] is None)
    check("no_automatic_promotion", manifest["matching_contract"]["automatic_canonical_station_promotion"] is False)
    for name, specification in contract["inputs"].items():
        path = data_root / specification["relative_path"]
        check(f"pinned_input:{name}", path.is_file() and sha256_file(path) == specification["sha256"])
    payload_paths = {payload["role"]: data_root / payload["path"] for payload in manifest["payloads"]}
    for payload in manifest["payloads"]:
        path = data_root / payload["path"]
        check(f"payload:{payload['role']}", path.is_file() and sha256_file(path) == payload["sha256"] and path.stat().st_size == payload["bytes"])
    candidates = _rows(payload_paths["STATION_CANDIDATES"])
    coverage = _rows(payload_paths["VENUE_SEASON_COVERAGE"])
    candidate_keys = {(row["season"], row["venue_id"], row["station_id"], row["station_rank"]) for row in candidates}
    coverage_keys = {(row["season"], row["venue_id"]) for row in coverage}
    check("candidate_natural_key_unique", len(candidate_keys) == len(candidates))
    check("coverage_natural_key_unique", len(coverage_keys) == len(coverage))
    check("distance_nonnegative", all(float(row["distance_km"]) >= 0.0 for row in candidates))
    check("station_period_covers_season", all(int(row["station_begin"][:4]) <= int(row["season"]) <= int(row["station_end"][:4]) for row in candidates))
    check("rank_bounds", all(1 <= int(row["station_rank"]) <= manifest["population"]["top_k"] for row in candidates))
    check("candidate_only_authority", all(row["automatic_station_promotion"] == row["historical_pit_eligible"] == row["training_feature_eligible"] == "false" for row in candidates))
    check("missing_coordinate_preserved", any(row["coordinate_state"] == "MISSING_CURRENT_CATALOG_COORDINATE" for row in coverage))
    check("population_candidate_rows", len(candidates) == manifest["population"]["candidate_rows"])
    check("population_coverage_rows", len(coverage) == manifest["population"]["venue_season_rows"])

    runtime_root = data_root / "validation" / "runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    rebuild_root = Path(tempfile.mkdtemp(prefix="bat417-noaa-station-rebuild-", dir=runtime_root))
    deterministic_files = 0
    try:
        station_capture = manifest["station_capture"]
        rebuilt = materialize(
            input_data_root=data_root,
            output_data_root=rebuild_root,
            repo_root=repo_root,
            station_payload_path=data_root / station_capture["raw_relative_path"],
            station_snapshot=station_capture,
            issued_at_utc=manifest["issued_at_utc"],
        )
        check("rebuild_identity", rebuilt["dataset_identity"] == args.dataset_identity)
        relative_paths = [payload["path"] for payload in manifest["payloads"]]
        relative_paths.append(f"{contract['artifact_roots']['manifests']}/{args.dataset_identity}/run_manifest.json")
        for relative in relative_paths:
            deterministic_files += 1
            check(f"byte_identical:{relative}", sha256_file(data_root / relative) == sha256_file(rebuild_root / relative))
    finally:
        shutil.rmtree(rebuild_root, ignore_errors=False)
    failures = [row for row in checks if row["result"] == "FAIL"]
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "NOAA_ISD_STATION_MATCHING_VALIDATION",
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "dataset_identity": args.dataset_identity,
        "manifest_sha256": sha256_file(manifest_path),
        "result": "PASS" if not failures else "FAIL",
        "checks_passed": len(checks) - len(failures),
        "checks_failed": len(failures),
        "deterministic_files_compared": deterministic_files,
        "checks": checks,
        "failures": failures,
        "cleanup": {"rebuild_removed": not rebuild_root.exists()},
    }
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["result"], "checks_passed": report["checks_passed"], "checks_failed": report["checks_failed"], "report_sha256": sha256_file(args.report_path)}, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

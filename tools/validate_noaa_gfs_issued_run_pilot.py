from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path: sys.path.insert(0, str(SRC))

from aggie_analytics.features.gfs_issued_run import materialize, parse_utc, sha256_file, stable_hash  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--data-root", type=Path, required=True); parser.add_argument("--dataset-identity", required=True); args = parser.parse_args()
    data_root = args.data_root.resolve(); contract = json.loads((ROOT / "configs/noaa_gfs_issued_run_pilot_contract.json").read_text(encoding="utf-8"))
    base = data_root / contract["artifact_roots"]["manifests"] / args.dataset_identity
    manifest_path, capture_path = base / "run_manifest.json", base / "capture_manifest.json"
    manifest, capture = json.loads(manifest_path.read_text()), json.loads(capture_path.read_text())
    checks = []
    def check(name, condition, detail=None): checks.append({"check": name, "result": "PASS" if condition else "FAIL", "detail": detail})
    check("dataset_identity", manifest["dataset_identity"] == args.dataset_identity)
    check("classification", manifest["classification"] == contract["classification"])
    check("authority", manifest["authority"] == contract["authority"])
    capture_core = {key: capture[key] for key in ("schema_version", "artifact_type", "classification", "contract_sha256", "object_key", "object_last_modified_utc", "message_capture_sha256")}
    check("capture_identity", stable_hash(capture_core) == capture["capture_manifest_identity"])
    check("capture_binding", manifest["capture_manifest_identity"] == capture["capture_manifest_identity"])
    check("availability_before_cutoff", parse_utc(capture["object_last_modified_utc"]) <= parse_utc(contract["population"]["expected_cutoff_utc"]))
    check("message_count", len(capture["message_captures"]) == len(contract["messages"]))
    for row in capture["message_captures"]:
        path = data_root / row["raw_relative_path"]; check(f"raw:{row['component']}", path.is_file() and sha256_file(path) == row["raw_sha256"])
    payload = data_root / manifest["payload"]["path"]; check("payload", payload.is_file() and sha256_file(payload) == manifest["payload"]["sha256"])
    pl = __import__("polars"); frame = pl.read_parquet(payload)
    check("row_count", frame.height == contract["population"]["expected_output_rows"])
    check("variable_unique", frame["weather_variable"].n_unique() == frame.height)
    check("all_pit_candidate", frame.filter(pl.col("historical_pit_candidate") != True).height == 0)  # noqa: E712
    check("no_training_admission", frame.filter(pl.col("training_feature_admitted") != False).height == 0)  # noqa: E712
    check("no_protected_admission", frame.filter(pl.col("protected_eligible") != False).height == 0)  # noqa: E712
    check("finite_values", frame.filter(~pl.col("value").is_finite()).height == 0)
    runtime = data_root / "validation/runtime"; runtime.mkdir(parents=True, exist_ok=True); rebuild = Path(tempfile.mkdtemp(prefix="bat417-gfs-issued-", dir=runtime))
    try:
        rebuilt = materialize(data_root=data_root, output_root=rebuild, repo_root=ROOT, capture_manifest=capture, issued_at_utc=manifest["issued_at_utc"])
        check("rebuild_identity", rebuilt["dataset_identity"] == args.dataset_identity)
        check("payload_byte_identical", sha256_file(rebuild / manifest["payload"]["path"]) == manifest["payload"]["sha256"])
        check("manifest_byte_identical", sha256_file(Path(rebuilt["manifest_path"])) == sha256_file(manifest_path))
    finally: shutil.rmtree(rebuild, ignore_errors=False)
    failures = [row for row in checks if row["result"] == "FAIL"]
    report = {"schema_version": "1.0.0", "artifact_type": "NOAA_GFS_ISSUED_RUN_PILOT_VALIDATION", "classification": contract["classification"], "decision_unit": contract["decision_unit"], "jira_key": contract["jira_key"], "dataset_identity": args.dataset_identity, "manifest_sha256": sha256_file(manifest_path), "capture_manifest_sha256": sha256_file(capture_path), "result": "PASS" if not failures else "FAIL", "checks_passed": len(checks)-len(failures), "checks_failed": len(failures), "checks": checks, "failures": failures, "authority": contract["authority"], "scientific_nonclaims": contract["scientific_nonclaims"]}
    report_path = data_root / contract["artifact_roots"]["validation"] / "sha256" / args.dataset_identity / "validation.json"; report_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    if report_path.exists() and report_path.read_text() != encoded: raise RuntimeError("GFS validation report collision")
    report_path.write_text(encoded)
    print(json.dumps({"result": report["result"], "checks_passed": report["checks_passed"], "checks_failed": report["checks_failed"], "report_path": str(report_path), "report_sha256": sha256_file(report_path)}, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__": raise SystemExit(main())

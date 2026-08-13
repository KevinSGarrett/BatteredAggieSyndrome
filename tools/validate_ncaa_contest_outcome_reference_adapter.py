from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data.historical_game_outcome_spine import canonical_json_bytes, dataframe_record_sha256, sha256_file  # noqa: E402
from aggie_analytics.data.ncaa_contest_outcome_reference_adapter import materialize_adapter  # noqa: E402


def main() -> int:
    import polars as pl

    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--dataset-identity", required=True)
    parser.add_argument("--rebuild-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, default=ROOT / "configs/ncaa_contest_outcome_reference_adapter_contract.json")
    args = parser.parse_args()
    data_root = args.data_root.resolve()
    rebuild_root = args.rebuild_root.resolve()
    repo_root = args.repo_root.resolve()
    contract_path = args.contract.resolve()
    identity = args.dataset_identity
    manifest_path = data_root / "manifests/ncaa_contest_outcome_reference_adapter/sha256" / identity / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: list[dict[str, object]] = []

    def check(name: str, condition: bool, detail: object = None) -> None:
        if not condition:
            raise AssertionError(f"validation failed: {name}; detail={detail}")
        checks.append({"name": name, "result": "PASS", "detail": detail})

    check("dataset_identity", manifest["dataset_identity"] == identity)
    check("classification", manifest["classification"] == "CANDIDATE_ONLY_OUTCOME_REFERENCE_ADAPTER_NO_AUTHORITY_EXPANSION")
    payload = manifest["payload"]
    payload_path = data_root / payload["relative_path"]
    check("payload_exists", payload_path.is_file())
    check("payload_hash", sha256_file(payload_path) == payload["sha256"])
    check("payload_bytes", payload_path.stat().st_size == payload["bytes"])
    frame = pl.read_parquet(payload_path)
    check("payload_rows", frame.height == payload["rows"] == 46957)
    check("record_hash", dataframe_record_sha256(frame) == payload["record_sha256"])
    check("unique_games", frame["target_game_id"].n_unique() == frame.height)
    check("zero_null_cells", sum(frame[name].null_count() for name in frame.columns) == 0)
    check("season_range", (frame["season"].min(), frame["season"].max()) == (1963, 2025))
    for key, value in manifest["authority"].items():
        check(f"authority_{key}", value is (key == "schema_adapter_materialization"))
    for key, value in manifest["nonclaims"].items():
        check(f"nonclaim_{key}", value is False)

    if rebuild_root.exists():
        raise ValueError(f"rebuild root already exists: {rebuild_root}")
    rebuilt = materialize_adapter(
        data_root=data_root,
        output_data_root=rebuild_root,
        repo_root=repo_root,
        contract_path=contract_path,
        issued_at_utc=manifest["issued_at_utc"],
    )
    check("byte_identical_identity", rebuilt["dataset_identity"] == identity)
    check("byte_identical_manifest", Path(rebuilt["manifest_path"]).read_bytes() == manifest_path.read_bytes())
    check("byte_identical_payload", Path(rebuilt["payload_path"]).read_bytes() == payload_path.read_bytes())

    mutated = json.loads(contract_path.read_text(encoding="utf-8"))
    mutated["source"]["completed_payload_sha256"] = "0" * 64
    mutation_path = rebuild_root / "mutations/hash-drift.json"
    mutation_path.parent.mkdir(parents=True, exist_ok=True)
    mutation_path.write_text(json.dumps(mutated, sort_keys=True) + "\n", encoding="utf-8")
    try:
        materialize_adapter(
            data_root=data_root,
            output_data_root=rebuild_root / "mutation-output",
            repo_root=repo_root,
            contract_path=mutation_path,
            issued_at_utc=manifest["issued_at_utc"],
        )
    except ValueError as exc:
        checks.append({"name": "source_payload_hash_drift", "result": "PASS_FAIL_CLOSED", "exception": type(exc).__name__})
    else:
        raise AssertionError("source payload hash mutation did not fail closed")

    report = {
        "schema_version": "1.0.0",
        "artifact_type": "NCAA_CONTEST_OUTCOME_REFERENCE_ADAPTER_VALIDATION",
        "validated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset_identity": identity,
        "manifest_sha256": sha256_file(manifest_path),
        "rebuild_root": str(rebuild_root),
        "result": "PASS",
        "check_count": len(checks),
        "mutation_control_count": 1,
        "checks": checks,
    }
    report_bytes = canonical_json_bytes(report) + b"\n"
    report_sha256 = hashlib.sha256(report_bytes).hexdigest()
    report_path = data_root / "validation/BAT-554/outcome-adapter" / identity / "runs" / report_sha256 / "report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.exists() and report_path.read_bytes() != report_bytes:
        raise ValueError("immutable adapter validation report collision")
    report_path.write_bytes(report_bytes)
    print(json.dumps({"result": "PASS", "checks": len(checks), "mutation_controls": 1, "report_path": str(report_path), "report_sha256": report_sha256}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

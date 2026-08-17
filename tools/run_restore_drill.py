from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import time
import zipfile
from typing import Any, Mapping, Sequence

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.operations.backup import restore_backup, verify_backup  # noqa: E402

SCHEMA_VERSION = "aggie.operations.restore_drill.v2"
REQUIRED_CONSUMER_RELPATHS = {
    "jira_key_map_csv": Path("jira_metadata/POST_IMPORT_KEY_MAP.csv"),
    "jira_change_log_jsonl": Path("jira_metadata/ISSUE_CHANGE_LOG.jsonl"),
    "jira_issue_manifest_json": Path("jira_metadata/POST-SUBTASK-131.json"),
    "lineage_forecast_json": Path("representative/forecast.json"),
}
ACCEPTANCE_CRITERIA = (
    "Immutability and rights boundaries preserved while restoring representative lineage and Jira metadata.",
    "Backup integrity and fail-closed negative-path behavior are verified before restore use.",
    "Clean-location restore measured with explicit RPO/RTO and host telemetry.",
    "Prerequisite BAT-481 evidence consumed without hidden reconstruction.",
)
AUTHORITY_FIELDS = (
    "schema_version",
    "issue",
    "authority_classification",
    "input_identities",
    "destination_validation",
    "restore_repetitions",
    "measurement",
    "negative_paths",
    "consumer_validation",
    "backup_manifest_entries",
    "acceptance_matrix",
    "issue_completion_manifest",
)


def _iso_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _count_tree(root: Path) -> dict:
    files = [p for p in root.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    return {"file_count": len(files), "bytes": total}


def _compute_artifact_identity(payload: dict) -> str:
    envelope = dict(payload)
    envelope.pop("artifact_identity", None)
    return hashlib.sha256(
        json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _require_sha256(value: object, *, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"invalid {field}")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"invalid {field}") from exc
    return value


def _validate_backup_catalog(catalog: dict, *, catalog_path: Path) -> dict:
    if not isinstance(catalog, dict):
        raise ValueError("backup catalog payload must be an object")
    if catalog.get("schema_version") != "aggie.operations.backup_catalog_integrity.v1":
        raise ValueError("backup catalog schema mismatch")
    recorded_identity = _require_sha256(catalog.get("artifact_identity"), field="catalog artifact_identity")
    computed_identity = _compute_artifact_identity(catalog)
    if recorded_identity != computed_identity:
        raise ValueError("catalog artifact_identity mismatch")
    paths = catalog.get("paths")
    if not isinstance(paths, dict):
        raise ValueError("backup catalog paths missing")
    final_backup = paths.get("final_backup")
    if not isinstance(final_backup, str) or not final_backup.strip():
        raise ValueError("backup catalog final_backup path missing")
    backup_identity = catalog.get("backup_identity")
    if not isinstance(backup_identity, dict):
        raise ValueError("backup catalog backup_identity missing")
    archive_sha256 = _require_sha256(
        backup_identity.get("archive_sha256"), field="backup catalog archive_sha256"
    )
    content_identity = _require_sha256(
        backup_identity.get("content_identity"), field="backup catalog content_identity"
    )
    entry_count = backup_identity.get("entry_count")
    if not isinstance(entry_count, int) or entry_count < 0:
        raise ValueError("backup catalog entry_count invalid")
    return {
        "catalog_path": str(catalog_path),
        "catalog_artifact_identity": recorded_identity,
        "backup_path": str(Path(final_backup).resolve()),
        "expected_archive_sha256": archive_sha256,
        "expected_content_identity": content_identity,
        "expected_entry_count": entry_count,
    }


def _validate_catalog_to_backup_binding(*, catalog_identity: dict, backup_verified: dict) -> dict:
    actual_entry_count = len(backup_verified.get("entries", []))
    if backup_verified.get("archive_sha256") != catalog_identity["expected_archive_sha256"]:
        raise ValueError("catalog backup archive sha mismatch")
    if backup_verified.get("content_identity") != catalog_identity["expected_content_identity"]:
        raise ValueError("catalog backup content identity mismatch")
    if actual_entry_count != catalog_identity["expected_entry_count"]:
        raise ValueError("catalog backup entry count mismatch")
    return {
        "archive_sha256": backup_verified["archive_sha256"],
        "content_identity": backup_verified["content_identity"],
        "entry_count": actual_entry_count,
    }


def _load_jsonl_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"non-object JSONL row at line {index}")
        rows.append(payload)
    return rows


def validate_restored_consumers(destination: Path) -> dict:
    required_csv_columns = {"local_id", "import_id", "jira_key", "jira_issue_id", "verified", "last_synced_at"}
    parse_results: dict[str, dict] = {}
    all_ok = True
    for key, relpath in REQUIRED_CONSUMER_RELPATHS.items():
        absolute = destination / relpath
        entry = {"relative_path": relpath.as_posix(), "exists": absolute.exists()}
        if not absolute.exists():
            entry["parse_success"] = False
            entry["error"] = "missing required file"
            parse_results[key] = entry
            all_ok = False
            continue
        entry["sha256"] = _sha_file(absolute)
        entry["bytes"] = absolute.stat().st_size
        try:
            if key == "jira_key_map_csv":
                with absolute.open("r", encoding="utf-8", newline="") as handle:
                    reader = csv.DictReader(handle)
                    if reader.fieldnames is None:
                        raise ValueError("missing CSV header")
                    missing = sorted(required_csv_columns - set(reader.fieldnames))
                    if missing:
                        raise ValueError(f"missing CSV columns: {missing}")
                    row_count = sum(1 for _ in reader)
                    if row_count <= 0:
                        raise ValueError("CSV has no data rows")
                    entry["row_count"] = row_count
            elif key == "jira_change_log_jsonl":
                rows = _load_jsonl_rows(absolute)
                if not rows:
                    raise ValueError("JSONL has no records")
                entry["record_count"] = len(rows)
            else:
                payload = json.loads(absolute.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("JSON payload must be an object")
                if key == "jira_issue_manifest_json":
                    for required in ("local_id", "jira_key"):
                        if required not in payload:
                            raise ValueError(f"missing JSON field: {required}")
                if key == "lineage_forecast_json":
                    for required in ("forecast_id", "source"):
                        if required not in payload:
                            raise ValueError(f"missing JSON field: {required}")
                entry["field_count"] = len(payload)
            entry["parse_success"] = True
        except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
            entry["parse_success"] = False
            entry["error"] = str(exc)
            all_ok = False
        parse_results[key] = entry
    return {
        "required_files": parse_results,
        "readable_without_manual_repair": all_ok,
    }


def bind_consumers_to_backup_manifest(
    consumer_validation: Mapping[str, Any],
    backup_entries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    by_path = {
        str(entry.get("path")): entry
        for entry in backup_entries
        if isinstance(entry, Mapping)
    }
    bindings: list[dict[str, Any]] = []
    all_bound = True
    required_files = consumer_validation.get("required_files")
    if not isinstance(required_files, dict):
        raise ValueError("consumer_validation.required_files missing")
    for key, relpath in REQUIRED_CONSUMER_RELPATHS.items():
        relative = relpath.as_posix()
        file_info = required_files.get(key)
        if not isinstance(file_info, dict):
            raise ValueError(f"consumer file missing: {key}")
        manifest_entry = by_path.get(relative)
        consumer_sha = file_info.get("sha256")
        consumer_bytes = file_info.get("bytes")
        bound = (
            isinstance(manifest_entry, Mapping)
            and file_info.get("parse_success") is True
            and file_info.get("exists") is True
            and consumer_sha == manifest_entry.get("sha256")
            and consumer_bytes == manifest_entry.get("bytes")
        )
        if not bound:
            all_bound = False
        bindings.append(
            {
                "consumer_key": key,
                "relative_path": relative,
                "consumer_sha256": consumer_sha,
                "consumer_bytes": consumer_bytes,
                "manifest_sha256": None if not isinstance(manifest_entry, Mapping) else manifest_entry.get("sha256"),
                "manifest_bytes": None if not isinstance(manifest_entry, Mapping) else manifest_entry.get("bytes"),
                "bound": bound,
            }
        )
    return {"entries": bindings, "all_bound": all_bound}


def derive_acceptance_matrix(
    *,
    consumer_validation: Mapping[str, Any],
    negative_paths: Mapping[str, Any],
    restore_repetitions: Sequence[Mapping[str, Any]],
    measurement: Mapping[str, Any],
    input_identities: Mapping[str, Any],
    destination_validation: Mapping[str, Any],
) -> list[dict[str, str]]:
    binding = consumer_validation.get("backup_manifest_binding")
    consumer_ok = (
        consumer_validation.get("readable_without_manual_repair") is True
        and isinstance(binding, Mapping)
        and binding.get("all_bound") is True
    )
    dest_ok = all(
        destination_validation.get(field) is True
        for field in (
            "destination_disjoint_from_repo",
            "destination_disjoint_from_authoritative_root",
            "destination_precleaned",
        )
    )
    negatives_ok = (
        negative_paths.get("corrupt_backup_rejected") is True
        and negative_paths.get("schema_mismatch_rejected") is True
    )
    measured_ok = (
        isinstance(restore_repetitions, Sequence)
        and len(restore_repetitions) == 2
        and isinstance(measurement.get("rto_seconds"), (int, float))
        and float(measurement["rto_seconds"]) > 0
        and measurement.get("non_authoritative_for_target_host") is True
    )
    catalog_ok = False
    try:
        _require_sha256(input_identities.get("catalog_artifact_identity"), field="catalog_artifact_identity")
        _require_sha256(input_identities.get("backup_archive_sha256"), field="backup_archive_sha256")
        catalog_ok = True
    except ValueError:
        catalog_ok = False
    dispositions = (
        "PASS" if consumer_ok and dest_ok else "FAIL",
        "PASS" if negatives_ok else "FAIL",
        "PASS" if measured_ok else "FAIL",
        "PASS" if catalog_ok else "FAIL",
    )
    evidence = (
        "destination_validation + consumer_validation",
        "negative_paths + input_identities",
        "restore_repetitions + measurement",
        "input_identities.catalog_artifact_identity",
    )
    return [
        {"criterion": criterion, "disposition": disposition, "evidence": ev}
        for criterion, disposition, ev in zip(ACCEPTANCE_CRITERIA, dispositions, evidence, strict=True)
    ]


def derive_issue_completion(acceptance_matrix: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if len(acceptance_matrix) != len(ACCEPTANCE_CRITERIA):
        raise ValueError("acceptance matrix length mismatch")
    for expected, row in zip(ACCEPTANCE_CRITERIA, acceptance_matrix, strict=True):
        if row.get("criterion") != expected:
            raise ValueError("acceptance matrix criterion mismatch")
    failed = [row["criterion"] for row in acceptance_matrix if row.get("disposition") != "PASS"]
    all_pass = not failed
    blockers = ["TARGET_HARDWARE_AUTHORITY_PENDING"]
    if failed:
        blockers = ["CONSUMER_OR_ACCEPTANCE_FAILURE", *blockers]
    return {
        "status": "DONE" if all_pass else "BLOCKED",
        "achieved_maturity": (
            "DETERMINISTIC_LOCAL_RESTORE_DRILL_VERIFIED" if all_pass else "RESTORE_DRILL_FAIL_CLOSED"
        ),
        "evidence_state": "VERIFIED" if all_pass else "UNVERIFIED",
        "remaining_blockers": blockers,
        "downstream_reevaluated": [
            "POST-EPIC-015",
            "POST-STORY-045",
            "POST-SUBTASK-133",
            "POST-SUBTASK-134",
            "POST-SUBTASK-135",
        ],
    }


def validate_restore_drill_artifact(
    payload: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
    catalog_path: Path | None = None,
) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("restore drill schema mismatch")
    missing = [field for field in AUTHORITY_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"restore drill missing authority fields: {missing}")
    recorded_identity = _require_sha256(payload.get("artifact_identity"), field="artifact_identity")
    computed_identity = _compute_artifact_identity(dict(payload))
    if recorded_identity != computed_identity:
        raise ValueError("restore drill artifact_identity mismatch")

    issue = payload.get("issue")
    if not isinstance(issue, Mapping) or issue.get("jira_key") != "BAT-482" or issue.get("local_id") != "POST-SUBTASK-132":
        raise ValueError("restore drill issue identity mismatch")

    consumer_validation = payload.get("consumer_validation")
    if not isinstance(consumer_validation, Mapping):
        raise ValueError("consumer_validation missing")
    required_files = consumer_validation.get("required_files")
    if not isinstance(required_files, dict) or set(required_files) != set(REQUIRED_CONSUMER_RELPATHS):
        raise ValueError("consumer_validation required files mismatch")
    parse_ok = True
    for key, relpath in REQUIRED_CONSUMER_RELPATHS.items():
        entry = required_files[key]
        if not isinstance(entry, dict):
            raise ValueError(f"consumer file entry missing: {key}")
        if entry.get("relative_path") != relpath.as_posix():
            raise ValueError(f"consumer relative path mismatch: {key}")
        if entry.get("parse_success") is not True or entry.get("exists") is not True:
            parse_ok = False

    backup_entries = payload.get("backup_manifest_entries")
    if not isinstance(backup_entries, list) or not backup_entries:
        raise ValueError("backup_manifest_entries missing")
    expected_binding = bind_consumers_to_backup_manifest(consumer_validation, backup_entries)
    recorded_binding = consumer_validation.get("backup_manifest_binding")
    if recorded_binding != expected_binding:
        raise ValueError("consumer hashes are not bound to restored backup manifest entries")
    readable = parse_ok and expected_binding["all_bound"] is True
    if consumer_validation.get("readable_without_manual_repair") is not readable:
        raise ValueError("readable_without_manual_repair is not bound to consumer parse and manifest binding")

    derived_acceptance = derive_acceptance_matrix(
        consumer_validation=consumer_validation,
        negative_paths=payload["negative_paths"],
        restore_repetitions=payload["restore_repetitions"],
        measurement=payload["measurement"],
        input_identities=payload["input_identities"],
        destination_validation=payload["destination_validation"],
    )
    if list(payload.get("acceptance_matrix") or []) != derived_acceptance:
        raise ValueError("acceptance matrix is not derived from consumer and control evidence")

    derived_completion = derive_issue_completion(derived_acceptance)
    recorded_completion = payload.get("issue_completion_manifest")
    if not isinstance(recorded_completion, Mapping):
        raise ValueError("issue_completion_manifest missing")
    for field in ("status", "evidence_state", "achieved_maturity", "remaining_blockers"):
        if recorded_completion.get(field) != derived_completion[field]:
            raise ValueError(f"issue completion {field} is not derived from acceptance rows")
    if derived_completion["status"] != "DONE" and recorded_completion.get("status") == "DONE":
        raise ValueError("completion status forged to DONE")
    if derived_completion["evidence_state"] != "VERIFIED" and recorded_completion.get("evidence_state") == "VERIFIED":
        raise ValueError("completion evidence_state forged to VERIFIED")
    if derived_completion["status"] != "DONE" and "NONE" in list(recorded_completion.get("remaining_blockers") or []):
        raise ValueError("non-DONE completion cannot claim NONE blockers")

    negative_paths = payload.get("negative_paths")
    if not isinstance(negative_paths, Mapping):
        raise ValueError("negative_paths missing")
    for field in ("corrupt_backup_rejected", "schema_mismatch_rejected"):
        if not isinstance(negative_paths.get(field), bool):
            raise ValueError(f"negative path {field} missing")

    input_identities = payload.get("input_identities")
    if not isinstance(input_identities, Mapping):
        raise ValueError("input_identities missing")
    if input_identities.get("backup_entry_count") != len(backup_entries):
        raise ValueError("backup_entry_count is not bound to backup_manifest_entries")

    if catalog_path is not None:
        catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
        catalog_identity = _validate_backup_catalog(catalog, catalog_path=Path(catalog_path))
        if input_identities.get("catalog_artifact_identity") != catalog_identity["catalog_artifact_identity"]:
            raise ValueError("catalog artifact identity does not match supplied catalog")
        if input_identities.get("backup_archive_sha256") != catalog_identity["expected_archive_sha256"]:
            raise ValueError("backup archive sha is not bound to catalog")
        if input_identities.get("backup_content_identity") != catalog_identity["expected_content_identity"]:
            raise ValueError("backup content identity is not bound to catalog")
        if input_identities.get("backup_entry_count") != catalog_identity["expected_entry_count"]:
            raise ValueError("backup entry count is not bound to catalog")

    if repo_root is not None:
        output_path = Path(repo_root) / "artifacts/operations/restore_drill.json"
        if output_path.exists():
            on_disk = json.loads(output_path.read_text(encoding="utf-8"))
            if on_disk.get("artifact_identity") == recorded_identity and on_disk != dict(payload):
                raise ValueError("on-disk restore drill artifact does not match validated payload")


def _cleanup_paths(paths: Sequence[Path]) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            continue


def run_restore_drill(*, repo_root: Path, output_path: Path, catalog_path: Path) -> dict:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog_identity = _validate_backup_catalog(catalog, catalog_path=catalog_path)
    backup_path = Path(catalog_identity["backup_path"]).resolve()
    backup_verified = verify_backup(backup_path)
    backup_binding = _validate_catalog_to_backup_binding(
        catalog_identity=catalog_identity,
        backup_verified=backup_verified,
    )
    backup_manifest_entries = [
        {"path": entry["path"], "sha256": entry["sha256"], "bytes": int(entry["bytes"])}
        for entry in backup_verified.get("entries", [])
    ]

    external_root = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", "").strip()
    if not external_root and repo_root.parent.name.lower() == "worktrees":
        external_root = str(repo_root.parent.parent)
    if not external_root:
        raise ValueError("AGGIE_ANALYTICS_DATA_ROOT is required")

    external = Path(external_root).resolve()
    restore_root = external / "validation" / "BAT-482-clean-restore-drill"
    destination = (restore_root / "restore_target").resolve()
    authoritative_root = Path(catalog["paths"]["external_work_root"]).resolve()
    repo = repo_root.resolve()
    if destination == repo or repo in destination.parents:
        raise ValueError("restore destination must be disjoint from repository")
    if destination == authoritative_root or authoritative_root in destination.parents:
        raise ValueError("restore destination must be disjoint from authoritative backup root")

    temp_files = [
        restore_root / "corrupt_backup.zip",
        restore_root / "schema_mismatch.zip",
    ]
    try:
        if destination.exists():
            shutil.rmtree(destination)
        destination.mkdir(parents=True, exist_ok=True)

        repetitions = []
        for index in range(2):
            if destination.exists():
                shutil.rmtree(destination)
            destination.mkdir(parents=True, exist_ok=True)
            start = time.perf_counter()
            started_at = _iso_utc()
            restore_backup(backup_path, destination, require_empty=True)
            ended_at = _iso_utc()
            elapsed = time.perf_counter() - start
            repetitions.append(
                {
                    "iteration": index + 1,
                    "classification": "cold" if index == 0 else "warm",
                    "started_at_utc": started_at,
                    "ended_at_utc": ended_at,
                    "elapsed_seconds": round(elapsed, 6),
                    "restored": _count_tree(destination),
                }
            )

        corrupt = temp_files[0]
        corrupt.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_path, corrupt)
        with zipfile.ZipFile(corrupt, "a") as zf:
            zf.writestr("payload/forged.txt", "tampered")
        corrupt_rejected = False
        corrupt_error = None
        try:
            restore_backup(corrupt, destination, require_empty=False)
        except ValueError as exc:
            corrupt_rejected = True
            corrupt_error = str(exc)

        with zipfile.ZipFile(backup_path, "r") as zf:
            bad_manifest = json.loads(zf.read("BACKUP_MANIFEST.json"))
            payload_items = {
                item.filename: zf.read(item.filename)
                for item in zf.infolist()
                if not item.is_dir()
            }
        bad_manifest["schema_version"] = "aggie.backup.invalid"
        stale = temp_files[1]
        with zipfile.ZipFile(stale, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, data in payload_items.items():
                if name == "BACKUP_MANIFEST.json":
                    zf.writestr(name, json.dumps(bad_manifest))
                else:
                    zf.writestr(name, data)
        schema_rejected = False
        schema_error = None
        try:
            verify_backup(stale)
        except ValueError as exc:
            schema_rejected = True
            schema_error = str(exc)

        manifest_created = datetime.fromisoformat(backup_verified["created_at_utc"])
        rpo_seconds = max(0.0, (datetime.now(timezone.utc) - manifest_created).total_seconds())
        best_rto = min(row["elapsed_seconds"] for row in repetitions)

        disk = shutil.disk_usage(destination)
        consumer_validation = validate_restored_consumers(destination)
        consumer_validation["backup_manifest_binding"] = bind_consumers_to_backup_manifest(
            consumer_validation,
            backup_manifest_entries,
        )
        if consumer_validation["backup_manifest_binding"]["all_bound"] is not True:
            consumer_validation["readable_without_manual_repair"] = False

        destination_validation = {
            "destination_absolute_path": str(destination),
            "destination_disjoint_from_repo": True,
            "destination_disjoint_from_authoritative_root": True,
            "destination_precleaned": True,
        }
        negative_paths = {
            "corrupt_backup_rejected": corrupt_rejected,
            "corrupt_backup_error": corrupt_error,
            "schema_mismatch_rejected": schema_rejected,
            "schema_mismatch_error": schema_error,
        }
        input_identities = {
            "catalog_path": catalog_identity["catalog_path"],
            "catalog_artifact_identity": catalog_identity["catalog_artifact_identity"],
            "backup_path": str(backup_path),
            "backup_archive_sha256": backup_binding["archive_sha256"],
            "backup_content_identity": backup_binding["content_identity"],
            "backup_entry_count": backup_binding["entry_count"],
        }
        measurement = {
            "rpo_seconds": round(rpo_seconds, 3),
            "rto_seconds": best_rto,
            "manual_steps": [
                "Reconfigure credentials outside repository runtime for downstream systems.",
                "Reconfirm rights/authorization tokens before external publication or delivery.",
            ],
            "telemetry": {
                "os": platform.platform(),
                "python": platform.python_version(),
                "cpu_count": os.cpu_count(),
                "disk_total_bytes": disk.total,
                "disk_free_bytes": disk.free,
            },
            "non_authoritative_for_target_host": True,
        }
        acceptance_matrix = derive_acceptance_matrix(
            consumer_validation=consumer_validation,
            negative_paths=negative_paths,
            restore_repetitions=repetitions,
            measurement=measurement,
            input_identities=input_identities,
            destination_validation=destination_validation,
        )
        payload = {
            "schema_version": SCHEMA_VERSION,
            "created_at_utc": _iso_utc(),
            "issue": {"jira_key": "BAT-482", "local_id": "POST-SUBTASK-132"},
            "authority_classification": [
                "DETERMINISTIC_LOCAL_RESTORE_DRILL",
                "REPRESENTATIVE_OPERATING_PATH",
                "TARGET_HARDWARE_AUTHORITY_PENDING",
            ],
            "commands_executed": [
                "python -B tools/run_restore_drill.py --output artifacts/operations/restore_drill.json"
            ],
            "input_identities": input_identities,
            "destination_validation": destination_validation,
            "restore_repetitions": repetitions,
            "measurement": measurement,
            "negative_paths": negative_paths,
            "consumer_validation": consumer_validation,
            "backup_manifest_entries": backup_manifest_entries,
            "acceptance_matrix": acceptance_matrix,
            "issue_completion_manifest": derive_issue_completion(acceptance_matrix),
        }
        payload["artifact_identity"] = _compute_artifact_identity(payload)
        validate_restore_drill_artifact(payload, repo_root=None, catalog_path=catalog_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return payload
    finally:
        _cleanup_paths(temp_files)


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute BAT-482 restore drill.")
    parser.add_argument("--output", type=Path, default=Path("artifacts/operations/restore_drill.json"))
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("artifacts/operations/backup_catalog_and_integrity.json"),
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    if args.validate_only:
        payload = json.loads(args.output.read_text(encoding="utf-8"))
        validate_restore_drill_artifact(payload, repo_root=repo_root, catalog_path=args.catalog)
        print(json.dumps({"result": "PASS", "artifact_identity": payload["artifact_identity"]}, indent=2))
        return 0
    payload = run_restore_drill(repo_root=repo_root, output_path=args.output, catalog_path=args.catalog)
    print(json.dumps({"result": "PASS", "artifact_identity": payload["artifact_identity"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

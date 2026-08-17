from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "src")))
from aggie_analytics.operations.backup import create_backup  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RUN_RESTORE_DRILL_PATH = ROOT / "tools/run_restore_drill.py"
SPEC = importlib.util.spec_from_file_location("run_restore_drill_module", RUN_RESTORE_DRILL_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load tools/run_restore_drill.py")
run_restore_drill_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run_restore_drill_module)


class RestoreDrillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.external = Path(self.tmpdir.name) / "external"
        self.external.mkdir(parents=True, exist_ok=True)
        self.env = dict(os.environ, AGGIE_ANALYTICS_DATA_ROOT=str(self.external))
        self.catalog_path = Path(self.tmpdir.name) / "backup_catalog_and_integrity.json"
        self.output_path = Path(self.tmpdir.name) / "restore_drill.json"
        subprocess.run(
            [
                sys.executable,
                "-B",
                "tools/build_backup_catalog_and_integrity.py",
                "--output",
                str(self.catalog_path),
            ],
            cwd=ROOT,
            env=self.env,
            check=True,
        )
        self.catalog_payload = json.loads(self.catalog_path.read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def _run_drill(self, catalog_payload: dict) -> dict:
        self.catalog_path.write_text(json.dumps(catalog_payload, indent=2) + "\n", encoding="utf-8")
        with mock.patch.dict(os.environ, {"AGGIE_ANALYTICS_DATA_ROOT": str(self.external)}, clear=False):
            return run_restore_drill_module.run_restore_drill(
                repo_root=ROOT,
                output_path=self.output_path,
                catalog_path=self.catalog_path,
            )

    def test_restore_drill_executes_and_records_negative_paths(self) -> None:
        payload = self._run_drill(dict(self.catalog_payload))
        self.assertEqual(payload["schema_version"], "aggie.operations.restore_drill.v2")
        self.assertEqual(len(payload["artifact_identity"]), 64)
        self.assertTrue(payload["negative_paths"]["corrupt_backup_rejected"])
        self.assertTrue(payload["negative_paths"]["schema_mismatch_rejected"])
        self.assertTrue(payload["consumer_validation"]["readable_without_manual_repair"])
        self.assertTrue(payload["consumer_validation"]["backup_manifest_binding"]["all_bound"])
        self.assertEqual(payload["issue_completion_manifest"]["status"], "DONE")
        self.assertEqual(payload["acceptance_matrix"][0]["disposition"], "PASS")
        run_restore_drill_module.validate_restore_drill_artifact(
            payload,
            catalog_path=self.catalog_path,
        )
        self.assertGreater(
            payload["consumer_validation"]["required_files"]["jira_key_map_csv"]["row_count"],
            0,
        )
        self.assertGreater(
            payload["consumer_validation"]["required_files"]["jira_change_log_jsonl"]["record_count"],
            0,
        )
        self.assertGreater(payload["measurement"]["rto_seconds"], 0.0)
        self.assertGreaterEqual(payload["measurement"]["rpo_seconds"], 0.0)
        self.assertEqual(len(payload["restore_repetitions"]), 2)

    def test_rejects_invalid_catalog_artifact_identity(self) -> None:
        payload = dict(self.catalog_payload)
        payload["artifact_identity"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "catalog artifact_identity mismatch"):
            self._run_drill(payload)

    def test_rejects_catalog_identity_recomputed_with_changed_backup_path(self) -> None:
        payload = json.loads(json.dumps(self.catalog_payload))
        backup_dir = Path(payload["paths"]["backup_directory"])
        replacement_source = Path(self.tmpdir.name) / "replacement_source"
        replacement_source.mkdir(parents=True, exist_ok=True)
        (replacement_source / "jira_metadata").mkdir(parents=True, exist_ok=True)
        (replacement_source / "representative").mkdir(parents=True, exist_ok=True)
        (replacement_source / "jira_metadata" / "POST_IMPORT_KEY_MAP.csv").write_text(
            "local_id,import_id,jira_key,jira_issue_id,verified,last_synced_at\nX,1,BAT-X,1,true,2026-01-01T00:00:00+00:00\n",
            encoding="utf-8",
        )
        (replacement_source / "jira_metadata" / "ISSUE_CHANGE_LOG.jsonl").write_text(
            '{"event":"ALT","timestamp":"2026-01-01T00:00:00Z"}\n',
            encoding="utf-8",
        )
        (replacement_source / "jira_metadata" / "POST-SUBTASK-131.json").write_text(
            json.dumps({"local_id": "POST-SUBTASK-131", "jira_key": "BAT-481", "issue_completion_manifest": {}}),
            encoding="utf-8",
        )
        (replacement_source / "representative" / "forecast.json").write_text(
            json.dumps({"forecast_id": "alt-001", "source": "replacement"}),
            encoding="utf-8",
        )
        replacement_backup = backup_dir / "replacement-valid.zip"
        create_backup(replacement_source, replacement_backup)
        payload["paths"]["final_backup"] = str(replacement_backup)
        payload["artifact_identity"] = run_restore_drill_module._compute_artifact_identity(payload)
        with self.assertRaisesRegex(ValueError, "catalog backup archive sha mismatch"):
            self._run_drill(payload)

    def test_rejects_substituted_valid_backup_at_original_path(self) -> None:
        payload = json.loads(json.dumps(self.catalog_payload))
        original_backup = Path(payload["paths"]["final_backup"])
        backup_dir = Path(payload["paths"]["backup_directory"])
        replacement_source = Path(self.tmpdir.name) / "replacement_source_2"
        replacement_source.mkdir(parents=True, exist_ok=True)
        (replacement_source / "jira_metadata").mkdir(parents=True, exist_ok=True)
        (replacement_source / "representative").mkdir(parents=True, exist_ok=True)
        (replacement_source / "jira_metadata" / "POST_IMPORT_KEY_MAP.csv").write_text(
            "local_id,import_id,jira_key,jira_issue_id,verified,last_synced_at\nY,2,BAT-Y,2,true,2026-01-01T00:00:00+00:00\n",
            encoding="utf-8",
        )
        (replacement_source / "jira_metadata" / "ISSUE_CHANGE_LOG.jsonl").write_text(
            '{"event":"ALT2","timestamp":"2026-01-01T00:00:00Z"}\n',
            encoding="utf-8",
        )
        (replacement_source / "jira_metadata" / "POST-SUBTASK-131.json").write_text(
            json.dumps({"local_id": "POST-SUBTASK-131", "jira_key": "BAT-481", "issue_completion_manifest": {}}),
            encoding="utf-8",
        )
        (replacement_source / "representative" / "forecast.json").write_text(
            json.dumps({"forecast_id": "alt-002", "source": "replacement"}),
            encoding="utf-8",
        )
        replacement_backup = backup_dir / "replacement-overwrite.zip"
        create_backup(replacement_source, replacement_backup)
        shutil.copy2(replacement_backup, original_backup)
        with self.assertRaisesRegex(ValueError, "catalog backup archive sha mismatch"):
            self._run_drill(payload)

    def test_rejects_archive_sha_mismatch(self) -> None:
        payload = json.loads(json.dumps(self.catalog_payload))
        payload["backup_identity"]["archive_sha256"] = "f" * 64
        payload["artifact_identity"] = run_restore_drill_module._compute_artifact_identity(payload)
        with self.assertRaisesRegex(ValueError, "catalog backup archive sha mismatch"):
            self._run_drill(payload)

    def test_rejects_content_identity_mismatch(self) -> None:
        payload = json.loads(json.dumps(self.catalog_payload))
        payload["backup_identity"]["content_identity"] = "f" * 64
        payload["artifact_identity"] = run_restore_drill_module._compute_artifact_identity(payload)
        with self.assertRaisesRegex(ValueError, "catalog backup content identity mismatch"):
            self._run_drill(payload)

    def test_rejects_entry_count_mismatch(self) -> None:
        payload = json.loads(json.dumps(self.catalog_payload))
        payload["backup_identity"]["entry_count"] = int(payload["backup_identity"]["entry_count"]) + 1
        payload["artifact_identity"] = run_restore_drill_module._compute_artifact_identity(payload)
        with self.assertRaisesRegex(ValueError, "catalog backup entry count mismatch"):
            self._run_drill(payload)

    def _write_consumer_fixture(self, root: Path) -> None:
        (root / "jira_metadata").mkdir(parents=True, exist_ok=True)
        (root / "representative").mkdir(parents=True, exist_ok=True)
        (root / "jira_metadata" / "POST_IMPORT_KEY_MAP.csv").write_text(
            "local_id,import_id,jira_key,jira_issue_id,verified,last_synced_at\nPOST-SUBTASK-131,100435,BAT-481,24621,true,2026-08-17T00:00:00+00:00\n",
            encoding="utf-8",
        )
        (root / "jira_metadata" / "ISSUE_CHANGE_LOG.jsonl").write_text(
            '{"event":"SYNC","timestamp":"2026-08-17T00:00:00Z"}\n',
            encoding="utf-8",
        )
        (root / "jira_metadata" / "POST-SUBTASK-131.json").write_text(
            json.dumps({"local_id": "POST-SUBTASK-131", "jira_key": "BAT-481", "issue_completion_manifest": {}}),
            encoding="utf-8",
        )
        (root / "representative" / "forecast.json").write_text(
            json.dumps({"forecast_id": "sample-001", "source": "representative"}),
            encoding="utf-8",
        )

    def test_consumer_validation_rejects_missing_required_file(self) -> None:
        destination = Path(self.tmpdir.name) / "consumer_missing"
        self._write_consumer_fixture(destination)
        (destination / "representative" / "forecast.json").unlink()
        result = run_restore_drill_module.validate_restored_consumers(destination)
        self.assertFalse(result["readable_without_manual_repair"])
        self.assertFalse(result["required_files"]["lineage_forecast_json"]["parse_success"])

    def test_consumer_validation_rejects_malformed_csv(self) -> None:
        destination = Path(self.tmpdir.name) / "consumer_bad_csv"
        self._write_consumer_fixture(destination)
        (destination / "jira_metadata" / "POST_IMPORT_KEY_MAP.csv").write_text(
            "local_id,jira_key\nPOST-SUBTASK-131,BAT-481\n",
            encoding="utf-8",
        )
        result = run_restore_drill_module.validate_restored_consumers(destination)
        self.assertFalse(result["readable_without_manual_repair"])
        self.assertFalse(result["required_files"]["jira_key_map_csv"]["parse_success"])

    def test_consumer_validation_rejects_malformed_json(self) -> None:
        destination = Path(self.tmpdir.name) / "consumer_bad_json"
        self._write_consumer_fixture(destination)
        (destination / "representative" / "forecast.json").write_text("{not-json}", encoding="utf-8")
        result = run_restore_drill_module.validate_restored_consumers(destination)
        self.assertFalse(result["readable_without_manual_repair"])
        self.assertFalse(result["required_files"]["lineage_forecast_json"]["parse_success"])

    def test_consumer_validation_rejects_malformed_jsonl(self) -> None:
        destination = Path(self.tmpdir.name) / "consumer_bad_jsonl"
        self._write_consumer_fixture(destination)
        (destination / "jira_metadata" / "ISSUE_CHANGE_LOG.jsonl").write_text("not-jsonl\n", encoding="utf-8")
        result = run_restore_drill_module.validate_restored_consumers(destination)
        self.assertFalse(result["readable_without_manual_repair"])
        self.assertFalse(result["required_files"]["jira_change_log_jsonl"]["parse_success"])

    def test_acceptance_and_completion_fail_closed_when_consumer_unreadable(self) -> None:
        unreadable = {
            "required_files": {
                key: {
                    "relative_path": relpath.as_posix(),
                    "exists": False,
                    "parse_success": False,
                    "error": "missing required file",
                }
                for key, relpath in run_restore_drill_module.REQUIRED_CONSUMER_RELPATHS.items()
            },
            "readable_without_manual_repair": False,
        }
        with mock.patch.object(
            run_restore_drill_module,
            "validate_restored_consumers",
            return_value=unreadable,
        ):
            payload = self._run_drill(dict(self.catalog_payload))
        self.assertFalse(payload["consumer_validation"]["readable_without_manual_repair"])
        self.assertEqual(payload["acceptance_matrix"][0]["disposition"], "FAIL")
        self.assertEqual(payload["issue_completion_manifest"]["status"], "BLOCKED")
        self.assertEqual(payload["issue_completion_manifest"]["evidence_state"], "UNVERIFIED")
        self.assertIn("CONSUMER_OR_ACCEPTANCE_FAILURE", payload["issue_completion_manifest"]["remaining_blockers"])
        run_restore_drill_module.validate_restore_drill_artifact(payload, catalog_path=self.catalog_path)

    def test_validator_rejects_forged_done_after_rehash(self) -> None:
        unreadable = {
            "required_files": {
                key: {
                    "relative_path": relpath.as_posix(),
                    "exists": False,
                    "parse_success": False,
                    "error": "missing required file",
                }
                for key, relpath in run_restore_drill_module.REQUIRED_CONSUMER_RELPATHS.items()
            },
            "readable_without_manual_repair": False,
        }
        with mock.patch.object(
            run_restore_drill_module,
            "validate_restored_consumers",
            return_value=unreadable,
        ):
            payload = self._run_drill(dict(self.catalog_payload))
        forged = json.loads(json.dumps(payload))
        forged["acceptance_matrix"][0]["disposition"] = "PASS"
        forged["issue_completion_manifest"]["status"] = "DONE"
        forged["issue_completion_manifest"]["evidence_state"] = "VERIFIED"
        forged["issue_completion_manifest"]["remaining_blockers"] = ["TARGET_HARDWARE_AUTHORITY_PENDING"]
        forged["artifact_identity"] = run_restore_drill_module._compute_artifact_identity(forged)
        with self.assertRaisesRegex(ValueError, "acceptance matrix is not derived"):
            run_restore_drill_module.validate_restore_drill_artifact(forged, catalog_path=self.catalog_path)

    def test_validator_rejects_forged_consumer_status_after_rehash(self) -> None:
        payload = self._run_drill(dict(self.catalog_payload))
        forged = json.loads(json.dumps(payload))
        forged["consumer_validation"]["readable_without_manual_repair"] = False
        forged["artifact_identity"] = run_restore_drill_module._compute_artifact_identity(forged)
        with self.assertRaisesRegex(ValueError, "readable_without_manual_repair"):
            run_restore_drill_module.validate_restore_drill_artifact(forged, catalog_path=self.catalog_path)

    def test_validator_rejects_forged_catalog_binding_after_rehash(self) -> None:
        payload = self._run_drill(dict(self.catalog_payload))
        forged = json.loads(json.dumps(payload))
        forged["input_identities"]["backup_archive_sha256"] = "f" * 64
        forged["artifact_identity"] = run_restore_drill_module._compute_artifact_identity(forged)
        with self.assertRaisesRegex(ValueError, "backup archive sha is not bound to catalog"):
            run_restore_drill_module.validate_restore_drill_artifact(forged, catalog_path=self.catalog_path)

    def test_validator_rejects_forged_negative_path_after_rehash(self) -> None:
        payload = self._run_drill(dict(self.catalog_payload))
        forged = json.loads(json.dumps(payload))
        forged["negative_paths"]["corrupt_backup_rejected"] = False
        forged["artifact_identity"] = run_restore_drill_module._compute_artifact_identity(forged)
        with self.assertRaisesRegex(ValueError, "acceptance matrix is not derived"):
            run_restore_drill_module.validate_restore_drill_artifact(forged, catalog_path=self.catalog_path)

    def test_validator_rejects_forged_manifest_binding_after_rehash(self) -> None:
        payload = self._run_drill(dict(self.catalog_payload))
        forged = json.loads(json.dumps(payload))
        forged["consumer_validation"]["backup_manifest_binding"]["all_bound"] = False
        forged["consumer_validation"]["backup_manifest_binding"]["entries"][0]["bound"] = False
        forged["artifact_identity"] = run_restore_drill_module._compute_artifact_identity(forged)
        with self.assertRaisesRegex(ValueError, "consumer hashes are not bound"):
            run_restore_drill_module.validate_restore_drill_artifact(forged, catalog_path=self.catalog_path)

    def test_temporary_restore_files_removed_on_exception(self) -> None:
        original = run_restore_drill_module.restore_backup

        def flaky(backup_path, destination, require_empty=True):
            if Path(backup_path).name == "corrupt_backup.zip":
                raise RuntimeError("injected after corrupt archive created")
            return original(backup_path, destination, require_empty=require_empty)

        with mock.patch.object(run_restore_drill_module, "restore_backup", side_effect=flaky):
            with self.assertRaisesRegex(RuntimeError, "injected after corrupt archive created"):
                self._run_drill(dict(self.catalog_payload))
        restore_root = self.external / "validation" / "BAT-482-clean-restore-drill"
        self.assertFalse((restore_root / "corrupt_backup.zip").exists())
        self.assertFalse((restore_root / "schema_mismatch.zip").exists())


if __name__ == "__main__":
    unittest.main()


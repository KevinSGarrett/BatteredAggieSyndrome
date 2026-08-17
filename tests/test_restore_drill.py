from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RestoreDrillTests(unittest.TestCase):
    def test_restore_drill_executes_and_records_negative_paths(self) -> None:
        output = ROOT / "artifacts/operations/restore_drill.json"
        catalog = ROOT / "artifacts/operations/backup_catalog_and_integrity.json"
        previous = output.read_text(encoding="utf-8") if output.exists() else None
        previous_catalog = catalog.read_text(encoding="utf-8") if catalog.exists() else None
        with tempfile.TemporaryDirectory() as td:
            external = Path(td) / "external"
            external.mkdir(parents=True, exist_ok=True)
            env = dict(os.environ, AGGIE_ANALYTICS_DATA_ROOT=str(external))
            subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "tools/build_backup_catalog_and_integrity.py",
                    "--output",
                    "artifacts/operations/backup_catalog_and_integrity.json",
                ],
                cwd=ROOT,
                env=env,
                check=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "tools/run_restore_drill.py",
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                env=env,
                check=True,
            )
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], "aggie.operations.restore_drill.v1")
            self.assertEqual(len(payload["artifact_identity"]), 64)
            self.assertTrue(payload["negative_paths"]["corrupt_backup_rejected"])
            self.assertTrue(payload["negative_paths"]["schema_mismatch_rejected"])
            self.assertTrue(payload["consumer_validation"]["jira_metadata_restored"])
            self.assertTrue(payload["consumer_validation"]["lineage_file_restored"])
            self.assertGreater(payload["measurement"]["rto_seconds"], 0.0)
            self.assertGreaterEqual(payload["measurement"]["rpo_seconds"], 0.0)
            self.assertEqual(len(payload["restore_repetitions"]), 2)
        if previous is None:
            output.unlink(missing_ok=True)
        else:
            output.write_text(previous, encoding="utf-8")
        if previous_catalog is None:
            catalog.unlink(missing_ok=True)
        else:
            catalog.write_text(previous_catalog, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()

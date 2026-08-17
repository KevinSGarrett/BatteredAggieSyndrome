from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aggie_analytics.operations.backup import (  # noqa: E402
    create_backup,
    enforce_backup_destination_policy,
    restore_backup,
    verify_backup,
)


class BackupCatalogIntegrityTests(unittest.TestCase):
    def test_duplicate_zip_member_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            source.mkdir()
            (source / "a.txt").write_text("alpha", encoding="utf-8")
            archive = root / "backup.zip"
            create_backup(source, archive)
            with zipfile.ZipFile(archive, "a") as zf:
                zf.writestr("payload/a.txt", "duplicate")
            with self.assertRaisesRegex(ValueError, "duplicate ZIP member"):
                verify_backup(archive)

    def test_duplicate_manifest_path_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            source.mkdir()
            (source / "a.txt").write_text("alpha", encoding="utf-8")
            archive = root / "backup.zip"
            create_backup(source, archive)
            with zipfile.ZipFile(archive, "r") as zf:
                manifest = json.loads(zf.read("BACKUP_MANIFEST.json"))
            manifest["entries"].append(dict(manifest["entries"][0]))
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("payload/a.txt", "alpha")
                zf.writestr("BACKUP_MANIFEST.json", json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "duplicate manifest entry path"):
                verify_backup(archive)

    def test_missing_or_unexpected_member_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            source.mkdir()
            (source / "a.txt").write_text("alpha", encoding="utf-8")
            archive = root / "backup.zip"
            create_backup(source, archive)
            with zipfile.ZipFile(archive, "a") as zf:
                zf.writestr("payload/unexpected.bin", "x")
            with self.assertRaisesRegex(ValueError, "coverage mismatch|unexpected backup members"):
                verify_backup(archive)

    def test_traversal_or_drive_path_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "bad.zip"
            manifest = {
                "schema_version": "aggie.backup.v2",
                "created_at_utc": "2026-01-01T00:00:00+00:00",
                "source_name": "bad",
                "entries": [{"path": "../escape.txt", "bytes": 1, "sha256": "0" * 64}],
            }
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("payload/../escape.txt", "x")
                zf.writestr("BACKUP_MANIFEST.json", json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "unsafe backup member|unsafe manifest entry path"):
                verify_backup(archive)

    def test_last_known_good_not_replaced_on_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            source.mkdir()
            (source / "baseline.txt").write_text("baseline", encoding="utf-8")
            lkg = root / "last_known_good.zip"
            create_backup(source, lkg)
            before = lkg.read_bytes()
            corrupt = root / "corrupt.zip"
            shutil.copy2(lkg, corrupt)
            with zipfile.ZipFile(corrupt, "a") as zf:
                zf.writestr("payload/tampered.txt", "tampered")
            with self.assertRaises(ValueError):
                verify_backup(corrupt)
            self.assertEqual(before, lkg.read_bytes())

    def test_restricted_destination_rejected(self) -> None:
        repo_root = ROOT
        with self.assertRaisesRegex(ValueError, "restricted destination rejected"):
            enforce_backup_destination_policy(
                repo_root / "artifacts",
                source_class="raw_third_party_capture",
                repo_root=repo_root,
            )

    def test_restore_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            source.mkdir()
            (source / "a.txt").write_text("alpha", encoding="utf-8")
            archive = root / "backup.zip"
            create_backup(source, archive)
            destination = root / "restore"
            restore_backup(archive, destination)
            self.assertEqual((destination / "a.txt").read_text(encoding="utf-8"), "alpha")

    def test_catalog_builder_outputs_consumable_identity(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            external = Path(td) / "external"
            external.mkdir(parents=True, exist_ok=True)
            output = ROOT / "artifacts/operations/backup_catalog_and_integrity.json"
            old = output.read_text(encoding="utf-8") if output.exists() else None
            try:
                env = dict(**os.environ, AGGIE_ANALYTICS_DATA_ROOT=str(external))
                subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        "tools/build_backup_catalog_and_integrity.py",
                        "--output",
                        str(output),
                    ],
                    cwd=ROOT,
                    env=env,
                    check=True,
                )
                loaded = json.loads(output.read_text(encoding="utf-8"))
                self.assertEqual(len(loaded["artifact_identity"]), 64)
                self.assertTrue(loaded["verification"]["corruption_rejected"])
                self.assertTrue(loaded["verification"]["restricted_destination_rejected"])
                self.assertGreater(loaded["backup_identity"]["entry_count"], 0)
            finally:
                if old is None:
                    output.unlink(missing_ok=True)
                else:
                    output.write_text(old, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()

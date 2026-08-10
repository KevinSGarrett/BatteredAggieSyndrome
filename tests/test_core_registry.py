from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from aggie_analytics.entities.registry_artifacts import (
    CoreRegistryArtifactManifest,
    RegistryArtifactError,
)
from aggie_analytics.entities.resolution import (
    RegistryAssignment,
    assign_registry_slots,
    collapse_season_intervals,
)


ROOT = Path(__file__).resolve().parents[1]


class CoreRegistryTests(unittest.TestCase):
    def test_assignment_is_order_independent_and_append_only(self) -> None:
        first = assign_registry_slots("team", ("TEAM|SRC-002|2", "TEAM|SRC-002|1"))
        reversed_input = assign_registry_slots("team", ("TEAM|SRC-002|1", "TEAM|SRC-002|2"))
        self.assertEqual(first, reversed_input)
        expanded = assign_registry_slots(
            "team",
            ("TEAM|SRC-002|0", *first),
            first,
        )
        self.assertEqual(first["TEAM|SRC-002|1"], expanded["TEAM|SRC-002|1"])
        self.assertEqual("core-v1:team:00000003", expanded["TEAM|SRC-002|0"].assignment_slot)
        self.assertNotIn("SRC-002", expanded["TEAM|SRC-002|0"].canonical_id)

    def test_invalid_existing_assignment_is_rejected(self) -> None:
        corrupt = RegistryAssignment(
            identity_key="TEAM|SRC-002|1",
            assignment_slot="core-v1:team:00000001",
            canonical_id="team_00000000000000000000000000000000",
        )
        with self.assertRaisesRegex(ValueError, "does not match"):
            assign_registry_slots("team", (corrupt.identity_key,), {corrupt.identity_key: corrupt})

    def test_observed_seasons_form_non_overlapping_effective_intervals(self) -> None:
        self.assertEqual(((2010, 2013), (2015, 2017)), collapse_season_intervals((2016, 2010, 2012, 2011, 2015)))
        self.assertEqual((), collapse_season_intervals(()))

    def test_repository_pointer_matches_external_manifest(self) -> None:
        manifest = CoreRegistryArtifactManifest.load(
            ROOT / "artifacts" / "entities" / "canonical_core_registry_manifest.json"
        )
        manifest.verify_pointer(ROOT / "artifacts" / "entities" / "canonical_core_registry.csv")
        self.assertEqual(56676, manifest.rows)
        self.assertEqual(36, manifest.columns)

    def test_manifest_consumer_verifies_hash_size_schema_and_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_root = Path(directory)
            payload = data_root / "canonical" / "BAT-TEST" / "payload.csv"
            payload.parent.mkdir(parents=True)
            payload.write_text("id,name\n1,Aggie\n2,Reveille\n", encoding="utf-8")
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            addressed = data_root / "canonical" / "BAT-TEST" / "sha256" / digest / "payload.csv"
            addressed.parent.mkdir(parents=True)
            payload.replace(addressed)
            manifest_path = data_root / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "dataset_version": "test-v1",
                        "storage_boundary": "EXTERNAL_CANONICAL_PAYLOAD",
                        "payload": {
                            "external_relative_path": addressed.relative_to(data_root).as_posix(),
                            "sha256": digest,
                            "bytes": addressed.stat().st_size,
                            "rows": 2,
                            "columns": 2,
                        },
                    }
                ),
                encoding="utf-8",
            )
            manifest = CoreRegistryArtifactManifest.load(manifest_path)
            self.assertTrue(addressed.samefile(manifest.verify_payload(data_root)))
            addressed.write_text("id,name\n1,Tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(RegistryArtifactError, "SIZE_MISMATCH|HASH_MISMATCH"):
                manifest.verify_payload(data_root)

    def test_manifest_rejects_traversal_before_access(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "storage_boundary": "EXTERNAL_CANONICAL_PAYLOAD",
                        "payload": {
                            "external_relative_path": "../escape/deadbeef/payload.csv",
                            "sha256": "a" * 64,
                            "bytes": 1,
                            "rows": 1,
                            "columns": 1,
                        },
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RegistryArtifactError, "RELATIVE_PATH_UNSAFE"):
                CoreRegistryArtifactManifest.load(path)

    def test_manifest_rejects_windows_style_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "storage_boundary": "EXTERNAL_CANONICAL_PAYLOAD",
                        "payload": {
                            "external_relative_path": "canonical\\..\\escape\\payload.csv",
                            "sha256": "a" * 64,
                            "bytes": 1,
                            "rows": 1,
                            "columns": 1,
                        },
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RegistryArtifactError, "RELATIVE_PATH_UNSAFE"):
                CoreRegistryArtifactManifest.load(path)


if __name__ == "__main__":
    unittest.main()

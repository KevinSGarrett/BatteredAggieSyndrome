from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from aggie_analytics.entities.people_registry import (
    PeopleRegistryAssignment,
    assign_people_registry_slots,
)
from aggie_analytics.entities.registry_artifacts import (
    PeopleRegistryArtifactManifest,
    RegistryArtifactError,
)


ROOT = Path(__file__).resolve().parents[1]


class PeopleRegistryTests(unittest.TestCase):
    def test_assignment_is_order_independent_and_append_only(self) -> None:
        first = assign_people_registry_slots("player", ("PLAYER|SRC-002|2", "PLAYER|SRC-002|1"))
        self.assertEqual(first, assign_people_registry_slots("player", tuple(reversed(tuple(first)))))
        expanded = assign_people_registry_slots("player", ("PLAYER|SRC-002|0", *first), first)
        self.assertEqual(first["PLAYER|SRC-002|1"], expanded["PLAYER|SRC-002|1"])
        self.assertEqual("people-v1:player:00000003", expanded["PLAYER|SRC-002|0"].assignment_slot)
        self.assertNotIn("SRC-002", expanded["PLAYER|SRC-002|0"].canonical_id)

    def test_mutable_attributes_are_not_assignment_inputs(self) -> None:
        assignment = assign_people_registry_slots("coach", ("COACH|SRC-002|99",))["COACH|SRC-002|99"]
        self.assertEqual(assignment, assign_people_registry_slots("coach", ("COACH|SRC-002|99",))["COACH|SRC-002|99"])
        self.assertNotIn("team", assignment.assignment_slot)
        self.assertNotIn("2025", assignment.assignment_slot)

    def test_corrupt_prior_assignment_fails_closed(self) -> None:
        bad = PeopleRegistryAssignment("PLAYER|SRC-002|1", "people-v1:player:00000001", "player_" + "0" * 32)
        with self.assertRaisesRegex(ValueError, "does not match"):
            assign_people_registry_slots("player", (bad.identity_key,), {bad.identity_key: bad})

    def test_repository_pointer_matches_manifest(self) -> None:
        manifest = PeopleRegistryArtifactManifest.load(ROOT / "artifacts/entities/canonical_people_registry_manifest.json")
        manifest.verify_pointer(ROOT / "artifacts/entities/canonical_people_registry.csv")
        self.assertGreater(manifest.rows, 1)
        self.assertEqual(47, manifest.columns)

    def test_manifest_consumer_verifies_external_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            body = b"id,name\n1,Aggie\n"
            digest = hashlib.sha256(body).hexdigest()
            payload = root / "canonical" / "BAT-388" / "sha256" / digest / "people.csv"
            payload.parent.mkdir(parents=True)
            payload.write_bytes(body)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps({"schema_version": "1.0.0", "dataset_version": "test", "storage_boundary": "EXTERNAL_CANONICAL_PAYLOAD", "payload": {"external_relative_path": payload.relative_to(root).as_posix(), "sha256": digest, "bytes": len(body), "rows": 1, "columns": 2}}), encoding="utf-8")
            manifest = PeopleRegistryArtifactManifest.load(manifest_path)
            self.assertTrue(payload.samefile(manifest.verify_payload(root)))
            payload.write_text("id,name\n1,Tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(RegistryArtifactError, "SIZE_MISMATCH|HASH_MISMATCH"):
                manifest.verify_payload(root)

    def test_manifest_rejects_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps({"schema_version": "1.0.0", "storage_boundary": "EXTERNAL_CANONICAL_PAYLOAD", "payload": {"external_relative_path": "../escape/payload.csv", "sha256": "a" * 64, "bytes": 1, "rows": 1, "columns": 1}}), encoding="utf-8")
            with self.assertRaisesRegex(RegistryArtifactError, "RELATIVE_PATH_UNSAFE"):
                PeopleRegistryArtifactManifest.load(path)


if __name__ == "__main__":
    unittest.main()

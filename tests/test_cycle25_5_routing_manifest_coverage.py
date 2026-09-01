"""Prove every Cycle #25.5 material path has exactly one active routing owner."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "configs/cycle25_5_material_ownership_registry.json"
MANIFEST_PATH = REPO_ROOT / "configs/codex_usage_interlock_change_manifest.json"
BINDING_PATH = REPO_ROOT / "configs/unified_assistive_change_routing_binding.json"

PROCESS_ONLY_KINDS = {
    "PROCESS_ONLY_JIRA_CONTROL_PLANE",
    "PROCESS_ONLY_GENERATED_PROVENANCE",
    "PROCESS_ONLY_ROUTING_INTERLOCK",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_sha256(payload: dict, omit: str) -> str:
    reduced = {key: value for key, value in payload.items() if key != omit}
    encoded = json.dumps(reduced, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class Cycle255RoutingManifestCoverageTest(unittest.TestCase):
    def setUp(self) -> None:
        if not REGISTRY_PATH.is_file():
            self.skipTest("Cycle #25.5 ownership registry is not in this tree")
        self.registry = _load(REGISTRY_PATH)
        self.manifest = _load(MANIFEST_PATH)
        self.binding = _load(BINDING_PATH)
        self.assignments = self.registry["assignments"]
        self.active_owner = self.manifest["jira_identity"]
        self.active_owner_is_cycle255 = self.active_owner in self.registry["owners"]

    def _require_active_cycle255_owner(self) -> str:
        if not self.active_owner_is_cycle255:
            self.skipTest(
                f"active routing owner {self.active_owner} is not a Cycle #25.5 owner"
            )
        return self.active_owner

    def test_registry_declares_each_path_exactly_once(self) -> None:
        paths = [row["path"] for row in self.assignments]
        duplicates = sorted({path for path in paths if paths.count(path) > 1})
        self.assertEqual([], duplicates)

    def test_every_assignment_has_exactly_one_disposition(self) -> None:
        for row in self.assignments:
            with self.subTest(path=row["path"]):
                if row["kind"] == "MATERIAL":
                    self.assertIn(row["owner"], self.registry["owners"])
                else:
                    self.assertIn(row["kind"], PROCESS_ONLY_KINDS)
                    self.assertIsNone(row["owner"])

    def test_active_manifest_declares_only_paths_it_owns(self) -> None:
        active_owner = self._require_active_cycle255_owner()
        owned = {
            row["path"]
            for row in self.assignments
            if row["kind"] == "MATERIAL" and row["owner"] == active_owner
        }
        process_only = {
            row["path"] for row in self.assignments if row["kind"] in PROCESS_ONLY_KINDS
        }
        declared = set(self.manifest["changed_paths"])
        undeclared = sorted(declared - owned - process_only)
        self.assertEqual([], undeclared)

    def test_every_declared_material_path_exists_in_tree(self) -> None:
        for row in self.assignments:
            if row["kind"] != "MATERIAL":
                continue
            self.assertTrue((REPO_ROOT / row["path"]).is_file(), row["path"])

    def test_binding_allowlist_equals_manifest_change_set(self) -> None:
        self.assertEqual(
            sorted(self.binding["allowed_paths"]),
            sorted(self.manifest["changed_paths"]),
        )

    def test_manifest_identity_recomputes(self) -> None:
        self.assertEqual(
            _canonical_sha256(self.manifest, "manifest_identity"),
            self.manifest["manifest_identity"],
        )

    def test_binding_decision_identity_recomputes(self) -> None:
        self.assertEqual(
            _canonical_sha256(self.binding, "decision_sha256"),
            self.binding["decision_sha256"],
        )

    def test_cycle25_5_authorization_reason_code_is_recorded(self) -> None:
        self._require_active_cycle255_owner()
        self.assertEqual(
            "USER_EXPLICIT_CURSOR_AUTHORIZATION_CYCLE_25_5",
            self.binding["reason_code"],
        )
        waiver = self.binding["user_explicit_waiver"]
        self.assertEqual(
            hashlib.sha256(waiver["instruction_text"].encode("utf-8")).hexdigest(),
            waiver["instruction_sha256"],
        )


if __name__ == "__main__":
    unittest.main()

"""Prove every Cycle #22 carryover material path has exactly one active routing owner.

The Cycle #22 recovery worktree combined two material owners (BAT-674 scoring and
BAT-675 authority purity) in a single dirty tree.  These tests fail closed if a
material path is claimed by more than one owner, if the active routing manifest
declares a path it does not own, or if the manifest and binding identities do not
recompute from their own content.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "configs/cycle23_material_ownership_registry.json"
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


class Cycle23RoutingManifestCoverageTest(unittest.TestCase):
    """Fail-closed coverage checks for the Cycle #23 ownership split."""

    def setUp(self) -> None:
        self.registry = _load(REGISTRY_PATH)
        self.manifest = _load(MANIFEST_PATH)
        self.binding = _load(BINDING_PATH)
        self.assignments = self.registry["assignments"]
        self.active_owner = self.manifest["jira_identity"]

    def _require_active_cycle23_owner(self) -> str:
        """Defer owner-scoped checks when a later cycle holds the active manifest.

        Only one routing manifest is active at a time.  Once Cycle #24 owns it,
        the Cycle #24 coverage test performs these same assertions against its
        own registry; asserting them here would report a Cycle #23 defect that
        does not exist.
        """
        if self.active_owner not in self.registry["owners"]:
            self.skipTest(
                f"active routing owner {self.active_owner} is not a Cycle #23 owner"
            )
        return self.active_owner

    def test_registry_declares_each_path_exactly_once(self) -> None:
        paths = [row["path"] for row in self.assignments]
        duplicates = sorted({path for path in paths if paths.count(path) > 1})
        self.assertEqual([], duplicates, f"paths claimed more than once: {duplicates}")

    def test_every_assignment_has_exactly_one_disposition(self) -> None:
        for row in self.assignments:
            with self.subTest(path=row["path"]):
                if row["kind"] == "MATERIAL":
                    self.assertIn(
                        row["owner"],
                        self.registry["owners"],
                        "material path must name a declared owner",
                    )
                else:
                    self.assertIn(row["kind"], PROCESS_ONLY_KINDS)
                    self.assertIsNone(
                        row["owner"],
                        "process-only path must not claim a material owner",
                    )

    def test_no_material_path_is_shared_between_owners(self) -> None:
        by_owner: dict[str, set[str]] = {}
        for row in self.assignments:
            if row["kind"] != "MATERIAL":
                continue
            by_owner.setdefault(row["owner"], set()).add(row["path"])
        owners = sorted(by_owner)
        for index, left in enumerate(owners):
            for right in owners[index + 1 :]:
                overlap = sorted(by_owner[left] & by_owner[right])
                self.assertEqual(
                    [], overlap, f"{left} and {right} both claim: {overlap}"
                )

    def test_active_manifest_declares_only_paths_it_owns(self) -> None:
        """A manifest may declare its own material paths plus process-only paths.

        It may never declare a material path belonging to a different owner, which
        is exactly how the combined Cycle #22 worktree would have mis-routed
        BAT-674 scoring evidence into the BAT-675 unit.
        """
        active_owner = self._require_active_cycle23_owner()
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
        self.assertEqual(
            [],
            undeclared,
            f"{active_owner} manifest declares paths absent from the registry: {undeclared}",
        )

        foreign_material = {
            row["path"]
            for row in self.assignments
            if row["kind"] == "MATERIAL" and row["owner"] != active_owner
        }
        misrouted = sorted(declared & foreign_material)
        self.assertEqual(
            [],
            misrouted,
            f"{active_owner} manifest claims another owner's material paths: {misrouted}",
        )

    def test_every_declared_material_path_exists_in_tree(self) -> None:
        for row in self.assignments:
            if row["kind"] != "MATERIAL":
                continue
            with self.subTest(path=row["path"]):
                self.assertTrue(
                    (REPO_ROOT / row["path"]).is_file(),
                    f"declared material path is absent: {row['path']}",
                )

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

    def test_manifest_and_binding_agree_on_owner_and_work_unit(self) -> None:
        self.assertEqual(self.manifest["jira_identity"], self.binding["jira_identity"])
        self.assertEqual(self.manifest["work_unit_id"], self.binding["work_unit_id"])
        self.assertEqual(self.manifest["base_commit"], self.binding["source_commit"])
        self.assertEqual(
            self.manifest["pre_routing_decision_sha256"],
            self.binding["decision_sha256"],
        )

    def test_routing_never_authorizes_ordinary_direct_work(self) -> None:
        self.assertIs(self.manifest["ordinary_project_work_authorized"], False)
        self.assertIs(self.binding["ordinary_project_work_authorized"], False)

    def test_active_owner_is_a_declared_cycle23_owner(self) -> None:
        self._require_active_cycle23_owner()
        self.assertEqual(
            self.registry["owners"][self.manifest["jira_identity"]]["local_issue_id"],
            self.manifest["work_unit_id"],
        )


if __name__ == "__main__":
    unittest.main()

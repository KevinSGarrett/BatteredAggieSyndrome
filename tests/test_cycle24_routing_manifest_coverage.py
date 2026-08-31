"""Prove every Cycle #24 material path has exactly one active routing owner.

Cycle #24 carries five substantial decision units that all touch the same
control-plane files.  These tests fail closed if a material path is claimed by
more than one owner, if the active routing manifest declares a material path it
does not own, or if the manifest and binding identities do not recompute from
their own content.

Exactly one Cycle #24 routing manifest is active at a time.  When the active
manifest belongs to an earlier cycle, the owner-scoped assertions here defer to
that cycle's coverage test rather than manufacturing a failure.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "configs/cycle24_material_ownership_registry.json"
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


class Cycle24RoutingManifestCoverageTest(unittest.TestCase):
    """Fail-closed coverage checks for the Cycle #24 ownership split."""

    def setUp(self) -> None:
        self.registry = _load(REGISTRY_PATH)
        self.manifest = _load(MANIFEST_PATH)
        self.binding = _load(BINDING_PATH)
        self.assignments = self.registry["assignments"]
        self.active_owner = self.manifest["jira_identity"]
        self.active_owner_is_cycle24 = self.active_owner in self.registry["owners"]

    def _require_active_cycle24_owner(self) -> str:
        if not self.active_owner_is_cycle24:
            self.skipTest(
                f"active routing owner {self.active_owner} is not a Cycle #24 owner"
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
        active_owner = self._require_active_cycle24_owner()
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

    def test_active_owner_local_issue_id_matches_the_registry(self) -> None:
        active_owner = self._require_active_cycle24_owner()
        self.assertEqual(
            self.registry["owners"][active_owner]["local_issue_id"],
            self.manifest["work_unit_id"],
        )

    def test_cycle24_authorization_reason_code_is_recorded(self) -> None:
        self._require_active_cycle24_owner()
        self.assertEqual(
            "USER_EXPLICIT_CURSOR_AUTHORIZATION_CYCLE_24",
            self.binding["reason_code"],
        )
        waiver = self.binding["user_explicit_waiver"]
        self.assertEqual(
            hashlib.sha256(waiver["instruction_text"].encode("utf-8")).hexdigest(),
            waiver["instruction_sha256"],
        )
        self.assertIn(
            "USER_EXPLICIT_CURSOR_AUTHORIZATION_CYCLE_24", waiver["instruction_text"]
        )

    def test_no_cycle24_owner_is_also_a_cycle23_owner(self) -> None:
        cycle23 = _load(REPO_ROOT / "configs/cycle23_material_ownership_registry.json")
        overlap = sorted(set(self.registry["owners"]) & set(cycle23["owners"]))
        self.assertEqual([], overlap, f"owner declared in two cycles: {overlap}")


if __name__ == "__main__":
    unittest.main()

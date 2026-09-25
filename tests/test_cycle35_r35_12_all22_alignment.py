"""R35-12/MF35-12 (Cycle #35 manager follow-up, 20260920T224700Z): "complete
the authorized BAS-local C01 contract/released-package tests." No test
imported tools/cycle35/r35_12_all22_alignment.py before this file -- its
field-by-field compatibility decision, producer/consumer DAG and read-only
clone discovery had zero automated coverage locking in their behavior.

These exercise only the BAS-local, non-network parts: the released-vs-
proposed contract comparison, the producer/consumer DAG, and clone
discovery against a real (fixture) git checkout. Re-resolving the five
private owner remote heads and qualifying the C01 wheel both require a
network call this cache-first cycle does not spend without specific
confirmation, so neither is exercised here -- that stays a disclosed,
genuine blocker, not something a test papers over with a mock.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from r35_12_all22_alignment import (  # noqa: E402
    STAFF_SNAPSHOT_V1_ACTUAL_FIELDS,
    discover_clones,
    producer_consumer_dag,
    staff_snapshot_boundary,
)


def _git(args, cwd):
    subprocess.run(["git"] + args, cwd=str(cwd), check=True, capture_output=True)


def _init_repo(path: Path, *, dirty: bool = False) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q"], path)
    _git(["config", "user.email", "test@example.com"], path)
    _git(["config", "user.name", "Test"], path)
    (path / "README.md").write_text("x", encoding="utf-8")
    _git(["add", "README.md"], path)
    _git(["commit", "-q", "-m", "init"], path)
    if dirty:
        (path / "README.md").write_text("y", encoding="utf-8")


class StaffSnapshotBoundaryTests(unittest.TestCase):
    """The released StaffSnapshotV1 carries only team_id/coach_ids -- this
    is the actual owner contract, hardcoded from the manager's evidence,
    never re-derived from the BAS-local proposal itself (that would let a
    richer local proposal silently redefine what the owner actually
    released)."""

    def test_released_contract_is_the_hardcoded_actual_fields_not_a_guess(self) -> None:
        boundary = staff_snapshot_boundary()
        self.assertEqual(
            boundary["released_staff_snapshot_v1_fields"],
            list(STAFF_SNAPSHOT_V1_ACTUAL_FIELDS),
        )

    def test_owner_adoption_is_explicitly_pending_never_claimed(self) -> None:
        boundary = staff_snapshot_boundary()
        self.assertEqual(boundary["owner_adoption_state"], "C01_OWNER_ADOPTION_PENDING")

    def test_every_transported_field_gets_exactly_one_decision(self) -> None:
        boundary = staff_snapshot_boundary()
        allowed = {"TRANSPORTS_IN_PROPOSAL_ONLY", "TRANSPORTS_IN_BOTH", "NOT_TRANSPORTED"}
        for entry in boundary["field_by_field_decisions"]:
            self.assertIn(entry["decision"], allowed)
            # A field carried by the released v1 must never be marked
            # NOT_TRANSPORTED -- that would contradict its own carried flag.
            if entry["carried_by_released_staff_snapshot_v1"]:
                self.assertEqual(entry["decision"], "TRANSPORTS_IN_BOTH")

    def test_fields_outside_the_released_contract_are_proposal_only_or_absent(self) -> None:
        boundary = staff_snapshot_boundary()
        for entry in boundary["field_by_field_decisions"]:
            if entry["field"] not in STAFF_SNAPSHOT_V1_ACTUAL_FIELDS:
                self.assertFalse(entry["carried_by_released_staff_snapshot_v1"])
                self.assertNotEqual(entry["decision"], "TRANSPORTS_IN_BOTH")

    def test_compatibility_finding_names_both_shapes_as_unadopted(self) -> None:
        boundary = staff_snapshot_boundary()
        finding = boundary["compatibility_finding"]
        self.assertIn("PROPOSAL", finding)
        self.assertIn("lossy", finding)


class ProducerConsumerDagTests(unittest.TestCase):
    def test_every_node_declares_what_invalidates_it(self) -> None:
        dag = producer_consumer_dag()
        for node in dag["nodes"]:
            self.assertTrue(node["invalidated_by"], node["id"])

    def test_c01_node_is_marked_owned_by_the_owner_not_bas(self) -> None:
        dag = producer_consumer_dag()
        c01 = next(n for n in dag["nodes"] if n["id"] == "C01:StaffSnapshotV1")
        self.assertEqual(c01["owned_by"], "CFIP owner, not BAS")
        self.assertEqual(c01["kind"], "OWNER_CONTRACT")

    def test_no_runtime_path_dependency_on_all22_is_declared(self) -> None:
        dag = producer_consumer_dag()
        self.assertTrue(dag["no_runtime_path_dependency_on_all22"])

    def test_consumer_chain_is_connected_producer_to_owner_contract(self) -> None:
        dag = producer_consumer_dag()
        by_id = {n["id"]: n for n in dag["nodes"]}
        adapter = by_id["BAS:all22_adapter"]
        self.assertIn("BAS:coaching_release", adapter["consumes"])
        c01 = by_id["C01:StaffSnapshotV1"]
        self.assertIn("BAS:all22_adapter (lossy projection)", c01["consumes"])


class DiscoverClonesTests(unittest.TestCase):
    """Exercised against real git checkouts (git init + commit), not
    mocked subprocess calls -- the same discipline used elsewhere this
    session for anything that reads real on-disk state."""

    def test_missing_root_returns_empty_not_an_error(self) -> None:
        self.assertEqual(discover_clones(Path("Z:/does/not/exist")), [])

    def test_a_real_clean_checkout_is_observed_read_only(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "owner_workspace"
            repo = root / "repo_a"
            _init_repo(repo)
            clones = discover_clones(root)
        self.assertEqual(len(clones), 1)
        self.assertFalse(clones[0]["dirty"])
        self.assertTrue(clones[0]["observed_read_only"])
        self.assertTrue(clones[0]["preserved_without_mutation"])
        self.assertIsNotNone(clones[0]["head"])

    def test_a_dirty_checkout_is_reported_dirty_with_a_count(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "owner_workspace"
            repo = root / "repo_b"
            _init_repo(repo, dirty=True)
            clones = discover_clones(root)
        self.assertEqual(len(clones), 1)
        self.assertTrue(clones[0]["dirty"])
        self.assertGreaterEqual(clones[0]["dirty_entry_count"], 1)

    def test_multiple_sibling_checkouts_are_all_discovered(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "owner_workspace"
            _init_repo(root / "repo_a")
            _init_repo(root / "repo_b", dirty=True)
            clones = discover_clones(root)
        self.assertEqual(len(clones), 2)
        dirty_paths = {c["path"] for c in clones if c["dirty"]}
        self.assertEqual(len(dirty_paths), 1)

    def test_nested_checkout_inside_a_recorded_one_is_not_double_counted(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "owner_workspace"
            outer = root / "repo_outer"
            _init_repo(outer)
            _init_repo(outer / "vendor" / "nested")
            clones = discover_clones(root)
        self.assertEqual(len(clones), 1)
        self.assertEqual(clones[0]["path"], str(outer))

    def test_discovery_is_deterministic_across_repeated_calls(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "owner_workspace"
            _init_repo(root / "repo_a")
            _init_repo(root / "repo_b")
            first = discover_clones(root)
            second = discover_clones(root)
        self.assertEqual(
            sorted(c["path"] for c in first), sorted(c["path"] for c in second)
        )


if __name__ == "__main__":
    unittest.main()

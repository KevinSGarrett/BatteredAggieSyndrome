"""The mirror discrepancy report must not dress a stale row as an anomaly.

The mirror is a Cycle #30 point-in-time record, not a replica of the board.
Three distinctions decide whether this report is useful or misleading:

  * a status that still matches is agreement, and a status that moved to a
    state this project explicitly records is not a finding;
  * a status that moved on a board BAS does not govern -- the CFIP worker
    workflow -- is a stale mirrored row, not an unexplained divergence. A
    first version had one "diverges" bucket and reported three such rows as
    anomalies;
  * a status that moved away from a state this project DOES record is the
    finding the report exists to produce, and must never be softened into
    the stale bucket.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_SPEC = importlib.util.spec_from_file_location(
    "c36_mirror_discrepancy",
    ROOT / "tools" / "cycle36" / "c36_14b_mirror_discrepancy.py",
)
mirror = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(mirror)


class ClassificationTests(unittest.TestCase):
    def test_an_unchanged_status_agrees(self) -> None:
        state, _ = mirror.classify("BAT-706", "In Review", "In Review")
        self.assertEqual(state, mirror.AGREES)

    def test_a_missing_key_is_not_silently_agreement(self) -> None:
        state, _ = mirror.classify("BAT-999", "To Do", None)
        self.assertEqual(state, mirror.ABSENT)

    def test_a_recorded_destination_is_not_a_finding(self) -> None:
        state, _ = mirror.classify("BAT-700", "In Review", "Done")
        self.assertEqual(state, mirror.MOVED)

    def test_a_foreign_workflow_move_is_stale_not_divergent(self) -> None:
        """CFIP worker states are not BAS's to expect."""

        state, reason = mirror.classify("CFIP-18", "WORKER_RUNNING", "PM_REVIEW")
        self.assertEqual(state, mirror.MOVED_OUTSIDE)
        self.assertIn("does not govern", reason)

    def test_a_protected_identity_that_moved_is_a_finding(self) -> None:
        """BAT-523 must stay In Progress; anything else is reported."""

        state, reason = mirror.classify("BAT-523", "In Progress", "Done")
        self.assertEqual(state, mirror.DIVERGES)
        self.assertIn("expected state", reason)

    def test_the_protected_identities_are_the_governed_set(self) -> None:
        self.assertEqual(
            sorted(mirror.BAS_GOVERNED_KEYS), ["BAT-401", "BAT-429", "BAT-523"]
        )


class LiveMirrorTests(unittest.TestCase):
    """Skipped where the mirror or the manager readback is not mounted."""

    @classmethod
    def setUpClass(cls) -> None:
        if not mirror.MIRROR_ROOT.is_dir() or not mirror.LIVE_INVENTORY.is_file():
            raise unittest.SkipTest("mirror or live readback is not mounted")
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            cls.artifact = mirror.build(Path(tmp))

    def test_no_row_diverges_from_a_state_this_project_records(self) -> None:
        self.assertEqual(self.artifact["divergences_from_a_recorded_state"], [])

    def test_every_mirrored_row_is_classified(self) -> None:
        self.assertEqual(
            sum(self.artifact["states"].values()), self.artifact["row_count"]
        )

    def test_parity_is_not_claimed_from_the_comparison(self) -> None:
        self.assertIn(
            "UNSUPPORTED_NOT_CLAIMED_FROM_COUNTS",
            self.artifact["parity_is_still_not_claimed"],
        )

    def test_comment_ids_are_not_assumed_to_exist(self) -> None:
        self.assertTrue(
            all(
                row["comment_existence_verified"] is False
                for row in self.artifact["rows"]
            )
        )

    def test_no_jira_write_was_performed(self) -> None:
        self.assertTrue(self.artifact["no_jira_write_performed"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.validation.pit_replay_readiness import (  # noqa: E402
    LANE_DECISION,
    REQUIRED_ACCEPTANCE,
    STALE_ZERO_ROW_IDENTITY,
    compute_artifact_identity,
    validate_readiness_artifact,
)

ARTIFACT = ROOT / "artifacts" / "pit" / "PIT_REPLAY_READINESS.json"


class PitReplayReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    def test_gate_retains_protected_lane_blocked_and_completes_the_issue(self) -> None:
        validate_readiness_artifact(self.payload, ROOT)
        self.assertEqual(self.payload["lane_decision"], LANE_DECISION)
        self.assertEqual(self.payload["issue_status"], "DONE")
        self.assertTrue(self.payload["stale_zero_row_language_superseded"])
        self.assertFalse(self.payload["protected_metrics_republished"])
        self.assertEqual(self.payload["gap_005"], "OPEN")

    def test_stale_zero_row_language_is_not_the_live_blocker(self) -> None:
        blocker_ids = [row["id"] for row in self.payload["remaining_lane_blockers"]]
        self.assertNotIn("QUALITY_GATE_BLOCKED_MATRIX_IDENTITY", blocker_ids)
        self.assertIn(STALE_ZERO_ROW_IDENTITY, self.payload["superseded_blocker_text"])
        self.assertIn("PRIOR_PROTECTED_RESULT_EXPOSURE", blocker_ids)
        self.assertIn("NO_NEW_PROTECTED_PERIOD_AUTHORIZED", blocker_ids)

    def test_no_protected_metrics_are_republished(self) -> None:
        encoded = json.dumps(self.payload)
        self.assertNotIn("DEVELOPMENT_TUNE", encoded)
        self.assertNotIn("DEVELOPMENT_EVALUATION_UNPROTECTED", encoded)
        self.assertFalse(self.payload["claims"]["protected_performance"])

    def test_forged_open_lane_is_rejected_after_rehash(self) -> None:
        forged = copy.deepcopy(self.payload)
        forged["lane_decision"] = "OPEN_PROTECTED_LANE"
        forged["issue_status"] = "DONE"
        forged["protected_metrics_republished"] = False
        forged["artifact_identity"] = compute_artifact_identity(forged)
        with self.assertRaises(ValueError):
            validate_readiness_artifact(forged, ROOT)

    def test_forged_metric_republication_is_rejected_after_rehash(self) -> None:
        forged = copy.deepcopy(self.payload)
        forged["protected_metrics_republished"] = True
        forged["artifact_identity"] = compute_artifact_identity(forged)
        with self.assertRaises(ValueError):
            validate_readiness_artifact(forged, ROOT)

    def test_acceptance_order_is_required(self) -> None:
        self.assertEqual(
            [row["criterion"] for row in self.payload["acceptance_matrix"]],
            list(REQUIRED_ACCEPTANCE),
        )
        forged = copy.deepcopy(self.payload)
        forged["acceptance_matrix"] = list(reversed(forged["acceptance_matrix"]))
        forged["artifact_identity"] = compute_artifact_identity(forged)
        with self.assertRaises(ValueError):
            validate_readiness_artifact(forged, ROOT)


if __name__ == "__main__":
    unittest.main()

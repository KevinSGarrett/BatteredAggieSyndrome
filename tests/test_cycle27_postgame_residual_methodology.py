"""Postgame residual methodology is predeclared and does not flip error signs."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from aggie_analytics.data.cycle27_postgame_residual_methodology import (  # noqa: E402
    build_methodology,
)


class Cycle27PostgameResidualMethodologyTests(unittest.TestCase):
    def test_error_signs_are_not_flipped(self) -> None:
        payload = build_methodology(
            issued_at_utc="2026-09-04T18:00:00Z",
            cycle27_scoring_gate="test-gate-not-a-production-identity",
        )
        self.assertEqual(payload["prediction_error"], "predicted - actual")
        self.assertEqual(payload["result_residual"], "actual - predicted")
        self.assertIsNone(payload["independent_predicted_score"])
        self.assertTrue(payload["repeated_checkpoints_are_not_independent_games"])
        self.assertTrue(payload["one_game_residual_is_observation_not_bas"])
        self.assertTrue(payload["do_not_populate_actual_score_before_official_final"])
        self.assertFalse(payload["upset_severity"]["supported"])
        self.assertTrue(payload["p_equals_half_is_no_direction"])


if __name__ == "__main__":
    unittest.main()

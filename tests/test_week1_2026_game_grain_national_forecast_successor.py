"""Cycle #26 adversarial coverage for the game-grain national forecast successor."""

from __future__ import annotations

import math
import unittest

from aggie_analytics.data.week1_2026_game_grain_distribution_successor import (
    game_grain_forecast,
)
from aggie_analytics.data.week1_2026_game_grain_national_forecast_successor import (
    MARGIN_CAPABLE,
    build_successor_rows,
)
from aggie_analytics.scientific_reference.coherence import (
    interval_quantile,
    probability_from_normal_residual,
)


class GameGrainNationalSuccessorTests(unittest.TestCase):
    def test_ridge_joint_matches_independent_normal(self) -> None:
        residual_stdev = 17.7396030753
        expected_margin = 12.5
        game = game_grain_forecast(
            contest_id="contest-1",
            home_team_key="HOME",
            away_team_key="AWAY",
            expected_margin_home=expected_margin,
            residual_stdev=residual_stdev,
            interval_probability=0.8,
            trust_gate_open=False,
        )
        expected_p = probability_from_normal_residual(expected_margin, residual_stdev)
        z = interval_quantile(0.8)
        lower = expected_margin - z * residual_stdev
        upper = expected_margin + z * residual_stdev
        self.assertAlmostEqual(game["home_win_probability"], expected_p, places=8)
        self.assertAlmostEqual(game["interval_lower"], lower, places=8)
        self.assertAlmostEqual(game["interval_upper"], upper, places=8)
        self.assertTrue(game["joint"]["coherent"])
        self.assertTrue(game["pair"]["coherent"])

    def test_successor_rewrites_ridge_without_touching_abstentions(self) -> None:
        residual_stdev = 10.0
        rows = [
            {
                "candidate_id": MARGIN_CAPABLE,
                "row_state": "FORECAST_FROZEN",
                "contest_identity": "c1",
                "ncaa_contest_id": "1",
                "home_canonical_team_id": "H",
                "away_canonical_team_id": "A",
                "home_source_team_id": "1",
                "away_source_team_id": "2",
                "expected_margin_home": 5.0,
                "probability_home": 0.9,
                "probability_away": 0.1,
                "checkpoint_id": "EARLY_WEEK1",
                "forecast_row_identity": "f1",
                "abstention_reasons": [],
            },
            {
                "candidate_id": MARGIN_CAPABLE,
                "row_state": "ABSTAIN_UNSUPPORTED_ENTITY",
                "contest_identity": "c2",
                "ncaa_contest_id": "2",
                "home_canonical_team_id": "H2",
                "away_canonical_team_id": "A2",
                "home_source_team_id": "3",
                "away_source_team_id": "4",
                "expected_margin_home": None,
                "probability_home": None,
                "probability_away": None,
                "checkpoint_id": "EARLY_WEEK1",
                "forecast_row_identity": "f2",
                "abstention_reasons": ["ABSTAIN_UNSUPPORTED_ENTITY"],
            },
            {
                "candidate_id": "national_logistic_l2",
                "row_state": "FORECAST_FROZEN",
                "contest_identity": "c1",
                "ncaa_contest_id": "1",
                "home_canonical_team_id": "H",
                "away_canonical_team_id": "A",
                "home_source_team_id": "1",
                "away_source_team_id": "2",
                "raw_probability_home": 0.7,
                "raw_probability_away": 0.4,
                "probability_home": 0.7,
                "probability_away": 0.4,
                "checkpoint_id": "EARLY_WEEK1",
                "forecast_row_identity": "f3",
                "abstention_reasons": [],
            },
        ]
        built = build_successor_rows(
            predecessor_rows=rows, residual_stdev=residual_stdev
        )
        self.assertEqual(built["failing_pairs"], 0)
        self.assertEqual(built["ridge_emitted"], 1)
        ridge = next(
            r for r in built["forecast_rows"] if r["forecast_row_identity"] == "f1"
        )
        self.assertEqual(ridge["probability_link"], "NORMAL_CDF_FROM_SAME_DISTRIBUTION")
        self.assertTrue(math.isfinite(ridge["probability_home"]))
        self.assertAlmostEqual(
            ridge["probability_home"] + ridge["probability_away"], 1.0, places=12
        )
        self.assertAlmostEqual(
            ridge["expected_margin_home"] + ridge["expected_margin_away"],
            0.0,
            places=12,
        )
        abstained = next(
            r for r in built["forecast_rows"] if r["forecast_row_identity"] == "f2"
        )
        self.assertIsNone(abstained["probability_home"])
        logistic = next(
            r for r in built["forecast_rows"] if r["forecast_row_identity"] == "f3"
        )
        self.assertAlmostEqual(
            logistic["probability_home"] + logistic["probability_away"], 1.0, places=12
        )
        self.assertIsNone(logistic["expected_margin_home"])


if __name__ == "__main__":
    unittest.main()

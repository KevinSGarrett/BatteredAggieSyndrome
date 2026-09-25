"""Week 1 official-final scoring successor regressions."""

from __future__ import annotations

import unittest

from aggie_analytics.data.week1_2026_official_final_scoring_successor import (
    PREDECLARED_MIN_UNIQUE_GAMES_FOR_SKILL_CLAIM,
    Week1OfficialFinalScoringError,
    freeze_before_kickoff,
    merge_terminal_cards,
    score_row,
    unique_game_empirical_assessment,
)


class Week1OfficialFinalScoringTests(unittest.TestCase):
    def test_tie_is_not_silently_a_home_win(self) -> None:
        scored = score_row(
            probability_home=0.7,
            expected_margin_home=3.0,
            home_points=21,
            away_points=21,
            candidate_id="national_margin_ridge",
        )
        self.assertFalse(scored["scored"])
        self.assertEqual(
            scored["unscored_reason"], "TIE_OR_NO_CONTEST_NOT_SILENTLY_COUNTED"
        )
        self.assertIsNone(scored["brier"])

    def test_out_of_range_probability_is_rejected_before_metrics(self) -> None:
        with self.assertRaises(Week1OfficialFinalScoringError):
            score_row(
                probability_home=1.2,
                expected_margin_home=3.0,
                home_points=21,
                away_points=14,
                candidate_id="national_margin_ridge",
            )

    def test_abstained_row_has_no_residual(self) -> None:
        scored = score_row(
            probability_home=None,
            expected_margin_home=None,
            home_points=21,
            away_points=14,
            candidate_id="national_logistic_l2",
        )
        self.assertFalse(scored["scored"])
        self.assertIsNone(scored["brier"])
        self.assertIsNone(scored["margin_residual"])

    def test_freeze_after_kickoff_is_not_eligible(self) -> None:
        self.assertFalse(
            freeze_before_kickoff("2026-09-03T23:00:00Z", "2026-09-03T22:00:00Z")
        )
        self.assertTrue(
            freeze_before_kickoff("2026-09-03T06:47:23Z", "2026-09-03T22:00:00Z")
        )
        self.assertFalse(
            freeze_before_kickoff("2026-09-03T06:47:23", "2026-09-03T22:00:00Z")
        )

    def test_ridge_residual_uses_actual_margin(self) -> None:
        scored = score_row(
            probability_home=0.8,
            expected_margin_home=10.0,
            home_points=38,
            away_points=16,
            candidate_id="national_margin_ridge",
        )
        self.assertTrue(scored["scored"])
        self.assertEqual(scored["actual_margin_home"], 22.0)
        self.assertEqual(scored["margin_residual"], -12.0)
        self.assertAlmostEqual(scored["brier"], (0.8 - 1.0) ** 2)

    def test_later_capture_adds_terminal_without_dropping_prior(self) -> None:
        merged = merge_terminal_cards(
            [
                (
                    "first",
                    [
                        {
                            "final_status_is_terminal": True,
                            "ncaa_contest_id": "1",
                            "home_points": 21,
                            "away_points": 14,
                        }
                    ],
                ),
                (
                    "second",
                    [
                        {
                            "final_status_is_terminal": True,
                            "ncaa_contest_id": "1",
                            "home_points": 21,
                            "away_points": 14,
                        },
                        {
                            "final_status_is_terminal": True,
                            "ncaa_contest_id": "2",
                            "home_points": 17,
                            "away_points": 10,
                        },
                    ],
                ),
            ]
        )
        self.assertEqual(sorted(merged["terminals"]), ["1", "2"])
        self.assertEqual(merged["contributing_capture_sha256"], ["first", "second"])
        self.assertEqual(merged["quarantined_conflicts"], {})

    def test_conflicting_terminal_scores_are_quarantined(self) -> None:
        merged = merge_terminal_cards(
            [
                (
                    "first",
                    [
                        {
                            "final_status_is_terminal": True,
                            "ncaa_contest_id": "1",
                            "home_points": 21,
                            "away_points": 14,
                        }
                    ],
                ),
                (
                    "second",
                    [
                        {
                            "final_status_is_terminal": True,
                            "ncaa_contest_id": "1",
                            "home_points": 24,
                            "away_points": 14,
                        }
                    ],
                ),
                (
                    "third",
                    [
                        {
                            "final_status_is_terminal": True,
                            "ncaa_contest_id": "1",
                            "home_points": 21,
                            "away_points": 14,
                        }
                    ],
                ),
            ]
        )
        self.assertEqual(merged["terminals"], {})
        self.assertIn("1", merged["quarantined_conflicts"])

    def test_unique_game_census_does_not_double_count_candidates(self) -> None:
        rows = [
            {
                "scored": True,
                "ncaa_contest_id": "1",
                "candidate_id": "national_margin_ridge",
                "brier": 0.04,
                "binary_log_loss": 0.2,
                "forecast_probability_home": 0.8,
                "label_home_win": 1,
                "margin_residual": -3.0,
            },
            {
                "scored": True,
                "ncaa_contest_id": "1",
                "candidate_id": "national_logistic_l2",
                "brier": 0.09,
                "binary_log_loss": 0.3,
                "forecast_probability_home": 0.7,
                "label_home_win": 1,
                "margin_residual": None,
            },
        ]
        empirical = unique_game_empirical_assessment(rows)
        self.assertEqual(empirical["unique_scored_games"], 1)
        self.assertEqual(
            empirical["PREDICTIVE_SKILL_EVIDENCE_STATE"], "NOT_ESTABLISHED"
        )
        self.assertEqual(
            empirical["predeclared_min_unique_games_for_skill_claim"],
            PREDECLARED_MIN_UNIQUE_GAMES_FOR_SKILL_CLAIM,
        )
        self.assertFalse(empirical["used_for_training_or_tuning"])


if __name__ == "__main__":
    unittest.main()

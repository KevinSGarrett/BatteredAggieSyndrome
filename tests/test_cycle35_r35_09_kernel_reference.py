"""R35-09: unit tests for the independent kernel reference's own logic.

The reference is the thing that judges the producer, so its arithmetic and
its comparison semantics need their own tests -- an independent reference
with a bug is worse than none, because it manufactures findings.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from r35_09_independent_kernel_reference import (  # noqa: E402
    _delta_summary,
    _ratio,
    parse_start,
    reference_features,
    values_agree,
)

BASE = datetime(2020, 9, 1, tzinfo=timezone.utc)


def _game(day: int, season: int, points_for: int, points_against: int):
    tie = points_for == points_against
    return {
        "game_id": f"g{day}",
        "start": BASE + timedelta(days=day),
        "season": season,
        "points_for": points_for,
        "points_against": points_against,
        "margin": points_for - points_against,
        "tie": tie,
        "won": (not tie) and points_for > points_against,
    }


class RatioTests(unittest.TestCase):
    def test_empty_denominator_is_undefined_not_zero(self) -> None:
        """Zero would be a fabricated value: a team with no prior games has
        no win rate, it does not have a win rate of 0.0."""
        self.assertIsNone(_ratio(0, 0))
        self.assertIsNone(_ratio(5, 0))

    def test_ordinary_ratio(self) -> None:
        self.assertEqual(_ratio(3, 4), 0.75)


class FeatureArithmeticTests(unittest.TestCase):
    def test_features_over_an_empty_prior_set_are_undefined(self) -> None:
        out = reference_features([], 2020)
        self.assertEqual(out["pit_prior_games_played"], 0)
        self.assertIsNone(out["pit_prior_win_rate"])
        self.assertIsNone(out["pit_prior_margin_mean"])
        self.assertEqual(out["pit_season_to_date_games"], 0)

    def test_means_and_rates(self) -> None:
        priors = [
            _game(1, 2020, 30, 10),
            _game(2, 2020, 10, 20),
            _game(3, 2020, 21, 21),
        ]
        out = reference_features(priors, 2020)
        self.assertEqual(out["pit_prior_games_played"], 3)
        self.assertAlmostEqual(out["pit_prior_points_for_mean"], (30 + 10 + 21) / 3)
        self.assertAlmostEqual(out["pit_prior_points_against_mean"], (10 + 20 + 21) / 3)
        self.assertAlmostEqual(out["pit_prior_margin_mean"], (20 - 10 + 0) / 3)
        self.assertAlmostEqual(out["pit_prior_win_rate"], 1 / 3)
        self.assertEqual(out["pit_season_to_date_games"], 3)

    def test_a_tie_is_not_a_win(self) -> None:
        out = reference_features([_game(1, 2020, 14, 14)], 2020)
        self.assertEqual(out["pit_prior_win_rate"], 0.0)

    def test_previous_season_rate_uses_only_that_season(self) -> None:
        priors = [
            _game(1, 2019, 30, 10),
            _game(2, 2019, 3, 40),
            _game(3, 2020, 28, 7),
        ]
        out = reference_features(priors, 2020)
        self.assertAlmostEqual(out["pit_prior_season_win_rate"], 0.5)
        self.assertEqual(out["pit_season_to_date_games"], 1)
        self.assertEqual(out["pit_season_to_date_win_rate"], 1.0)

    def test_no_previous_season_rows_leaves_that_rate_undefined(self) -> None:
        out = reference_features([_game(3, 2020, 28, 7)], 2020)
        self.assertIsNone(out["pit_prior_season_win_rate"])


class ComparisonSemanticsTests(unittest.TestCase):
    def test_none_only_agrees_with_none(self) -> None:
        self.assertTrue(values_agree(None, None))
        self.assertFalse(values_agree(None, 0.0))
        self.assertFalse(values_agree(0.0, None))

    def test_floats_compare_within_tolerance(self) -> None:
        self.assertTrue(values_agree(0.1 + 0.2, 0.3))
        self.assertFalse(values_agree(0.3, 0.31))

    def test_parse_start_requires_timezone_aware_iso(self) -> None:
        self.assertIsNotNone(parse_start("2020-09-01T00:00:00Z"))
        self.assertIsNone(parse_start("2020-09-01T00:00:00"))
        self.assertIsNone(parse_start("not-a-date"))
        self.assertIsNone(parse_start(""))


class DeltaSummaryTests(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(_delta_summary([]), {"count": 0})

    def test_buckets_and_direction(self) -> None:
        out = _delta_summary([0, 0, 3, -4, 15, 60, 500])
        self.assertEqual(out["buckets"]["exact"], 2)
        self.assertEqual(out["buckets"]["within_5"], 2)
        self.assertEqual(out["buckets"]["within_20"], 1)
        self.assertEqual(out["buckets"]["within_100"], 1)
        self.assertEqual(out["buckets"]["over_100"], 1)
        self.assertEqual(out["min"], -4)
        self.assertEqual(out["max"], 500)
        # The two directions mean opposite things and must stay separable.
        self.assertIn("negative delta", out["interpretation"])


if __name__ == "__main__":
    unittest.main()

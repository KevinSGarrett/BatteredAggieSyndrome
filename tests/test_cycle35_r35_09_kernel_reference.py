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
    compare,
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


def _kernel_row(game_id, season, home_team, away_team, home_features=None, away_features=None):
    return {
        "canonical_game_id": game_id,
        "season": season,
        "home_canonical_team_id": home_team,
        "away_canonical_team_id": away_team,
        "home_features": home_features if home_features is not None else {},
        "away_features": away_features if away_features is not None else {},
        "home_win_label": None,
    }


def _by_game_entry(game_id, start, season, home_team, away_team):
    return {
        "game_id": game_id, "start": start, "season": season,
        "home_team": home_team, "away_team": away_team,
    }


class CompareRowAccountingTests(unittest.TestCase):
    """MF35-09 (Cycle #35 manager follow-up, 20260920T224700Z): rows_compared
    previously included rows whose game was absent from the declared raw
    sources -- an absent comparison counted as a successful one. These
    exercise compare() directly to prove the fix without needing the real
    13,280-row kernel artifact."""

    def test_missing_source_row_is_excluded_from_rows_compared(self) -> None:
        kernel = [
            _kernel_row("g1", 2020, "T:A", "T:B",
                        {"pit_prior_games_played": 0}, {"pit_prior_games_played": 0}),
            _kernel_row("g_missing", 2020, "T:A", "T:B"),
        ]
        history = {"T:A": [], "T:B": []}
        by_game = {"g1": _by_game_entry("g1", BASE, 2020, "T:A", "T:B")}
        result = compare(kernel, history, by_game)
        self.assertEqual(result["rows_compared"], 1)
        self.assertEqual(result["rows_not_comparable"], 1)
        self.assertEqual(result["row_states"]["GAME_NOT_IN_DECLARED_RAW_SOURCES"], 1)

    def test_row_with_both_sides_missing_features_is_not_counted_as_compared(self) -> None:
        """A row whose game IS found but BOTH sides carry no stored
        features previously fell through to the unchanged "COMPARED"
        default despite zero actual comparisons happening."""
        kernel = [_kernel_row("g1", 2020, "T:A", "T:B", home_features={}, away_features={})]
        history = {"T:A": [], "T:B": []}
        by_game = {"g1": _by_game_entry("g1", BASE, 2020, "T:A", "T:B")}
        result = compare(kernel, history, by_game)
        self.assertEqual(result["rows_compared"], 0)
        self.assertEqual(result["row_states"].get("NO_SIDE_HAD_STORED_FEATURES"), 1)
        self.assertNotIn("COMPARED", result["row_states"])

    def test_one_side_present_one_missing_still_counts_the_row_as_compared(self) -> None:
        """A row where only ONE side lacks stored features is still a real
        comparison for the other side -- it must not be silently dropped
        from rows_compared, only the missing side's own tally changes."""
        kernel = [
            _kernel_row("g1", 2020, "T:A", "T:B",
                        home_features={"pit_prior_games_played": 0}, away_features={})
        ]
        history = {"T:A": [], "T:B": []}
        by_game = {"g1": _by_game_entry("g1", BASE, 2020, "T:A", "T:B")}
        result = compare(kernel, history, by_game)
        self.assertEqual(result["rows_compared"], 1)
        self.assertEqual(result["row_states"]["MISSING_SIDE_FEATURES"], 1)

    def test_real_comparisons_still_populate_disagreement_examples(self) -> None:
        kernel = [
            _kernel_row("g1", 2020, "T:A", "T:B",
                        home_features={"pit_prior_games_played": 99}, away_features={})
        ]
        history = {"T:A": [], "T:B": []}
        by_game = {"g1": _by_game_entry("g1", BASE, 2020, "T:A", "T:B")}
        result = compare(kernel, history, by_game)
        self.assertEqual(result["row_states"]["DISAGREES"], 1)
        self.assertEqual(result["rows_compared"], 1)


class TargetExclusionCheckTests(unittest.TestCase):
    """MF35-09: target exclusion was previously tested against `priors`, a
    list that had already had the target filtered out of its own
    construction -- checking a self-filtered list for the thing just
    filtered from it can never fail. It is now a duplicate-game_id
    integrity check on the team's raw history instead."""

    def test_no_violation_for_a_normal_single_entry_history(self) -> None:
        target_start = BASE + timedelta(days=5)
        kernel = [
            _kernel_row("g_target", 2020, "T:A", "T:B",
                        home_features={"pit_prior_games_played": 0}, away_features={})
        ]
        history = {
            "T:A": [
                {"game_id": "g_target", "start": target_start, "season": 2020,
                 "points_for": 10, "points_against": 3, "margin": 7,
                 "tie": False, "won": True},
            ],
            "T:B": [],
        }
        by_game = {"g_target": _by_game_entry("g_target", target_start, 2020, "T:A", "T:B")}
        result = compare(kernel, history, by_game)
        self.assertEqual(result["target_exclusion_violation_count"], 0)

    def test_duplicate_game_id_in_team_history_is_flagged(self) -> None:
        """The one genuinely testable failure mode: the same game_id
        appearing twice in a team's raw history (an upstream dedup
        regression), which this check must catch."""
        target_start = BASE + timedelta(days=5)
        kernel = [
            _kernel_row("g_target", 2020, "T:A", "T:B",
                        home_features={"pit_prior_games_played": 0}, away_features={})
        ]
        history = {
            "T:A": [
                {"game_id": "g_target", "start": target_start, "season": 2020,
                 "points_for": 10, "points_against": 3, "margin": 7,
                 "tie": False, "won": True},
                # A duplicate record for the identical game_id.
                {"game_id": "g_target", "start": target_start - timedelta(days=1),
                 "season": 2020, "points_for": 10, "points_against": 3,
                 "margin": 7, "tie": False, "won": True},
            ],
            "T:B": [],
        }
        by_game = {"g_target": _by_game_entry("g_target", target_start, 2020, "T:A", "T:B")}
        result = compare(kernel, history, by_game)
        self.assertEqual(result["target_exclusion_violation_count"], 1)
        self.assertEqual(
            result["target_exclusion_violations"][0]["reason"],
            "DUPLICATE_GAME_ID_IN_TEAM_HISTORY",
        )

    def test_scope_disclosure_is_present_and_honest(self) -> None:
        result = compare([], {}, {})
        self.assertIn(
            "not an independent audit of", result["target_exclusion_check_scope"]
        )


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

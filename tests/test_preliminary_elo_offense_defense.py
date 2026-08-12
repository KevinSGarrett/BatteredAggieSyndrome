import importlib.util
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_preliminary_elo_offense_defense",
    ROOT / "tools" / "run_preliminary_elo_offense_defense.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def game(game_id, season, week, home, away, home_points, away_points):
    return {
        "target_game_id": game_id,
        "season": season,
        "season_type": "regular",
        "week": week,
        "start_utc": f"{season}-09-{week:02d}T00:00:00Z",
        "cutoff_utc": f"{season}-09-{max(1, week - 1):02d}T00:00:00Z",
        "home_team_id": home,
        "away_team_id": away,
        "neutral_site": False,
        "cold_start": week == 1,
        "home_points": home_points,
        "away_points": away_points,
        "margin": home_points - away_points,
        "home_win": float(home_points > away_points),
    }


class PreliminaryEloOffenseDefenseTests(unittest.TestCase):
    def test_week_batch_excludes_same_batch_outcomes(self):
        rows = [
            game("g1", 2020, 1, "a", "b", 50, 10),
            game("g2", 2020, 1, "a", "c", 10, 50),
        ]
        predictions = MODULE.replay_components(rows, update_rate=0.1, offseason_retention=1.0)
        self.assertEqual(predictions[0]["home_offense_component"], 0.0)
        self.assertEqual(predictions[1]["home_offense_component"], 0.0)
        self.assertEqual(predictions[0]["home_component_games"], 0)
        self.assertEqual(predictions[1]["home_component_games"], 0)

    def test_scoring_and_prevention_components_move_in_opposite_directions(self):
        rows = [
            game("g1", 2020, 1, "a", "b", 50, 10),
            game("g2", 2020, 2, "a", "c", 30, 20),
        ]
        predictions = MODULE.replay_components(rows, update_rate=0.1, offseason_retention=1.0)
        second = predictions[1]
        self.assertGreater(second["home_offense_component"], 0.0)
        self.assertGreater(second["home_defense_component"], 0.0)
        self.assertGreater(second["home_component_games"], 0)
        self.assertLess(second["home_information_scarcity"], 1.0)

    def test_offseason_retention_shrinks_both_components(self):
        rows = [
            game("g1", 2020, 1, "a", "b", 50, 10),
            game("g2", 2021, 1, "a", "c", 30, 20),
        ]
        unchanged = MODULE.replay_components(rows, update_rate=0.1, offseason_retention=1.0)
        shrunk = MODULE.replay_components(rows, update_rate=0.1, offseason_retention=0.5)
        self.assertAlmostEqual(shrunk[1]["home_offense_component"], unchanged[1]["home_offense_component"] / 2)
        self.assertAlmostEqual(shrunk[1]["home_defense_component"], unchanged[1]["home_defense_component"] / 2)

    def test_calibrations_are_finite_and_deterministic(self):
        rows = [
            {"raw_predicted_margin": -10.0, "home_win": 0.0, "margin": -14.0},
            {"raw_predicted_margin": -3.0, "home_win": 0.0, "margin": -7.0},
            {"raw_predicted_margin": -1.0, "home_win": 1.0, "margin": 1.0},
            {"raw_predicted_margin": 1.0, "home_win": 0.0, "margin": -1.0},
            {"raw_predicted_margin": 2.0, "home_win": 1.0, "margin": 3.0},
            {"raw_predicted_margin": 8.0, "home_win": 1.0, "margin": 17.0},
        ]
        first = MODULE.fit_logistic(rows)
        self.assertEqual(first, MODULE.fit_logistic(rows))
        self.assertTrue(math.isfinite(first["intercept"]))
        self.assertGreater(first["slope_per_margin_point"], 0.0)
        margin = MODULE.fit_margin(rows)
        self.assertTrue(math.isfinite(margin["intercept"]))
        self.assertTrue(math.isfinite(margin["slope"]))

    def test_reference_slice_uses_scalar_rating_difference(self):
        row = {
            **game("g1", 2023, 1, "a", "b", 21, 14),
            "rating_diff": 55.0,
        }
        result = MODULE.component_slices([row], 2023)
        self.assertEqual(result["HOME_FAVORITE"], [row])
        self.assertEqual(result["HOME_UNDERDOG"], [])

    def test_paired_bootstrap_is_deterministic_on_common_support(self):
        candidate = [
            {**game("g1", 2023, 1, "a", "b", 21, 14), "home_win_probability": 0.7, "predicted_margin": 5.0},
            {**game("g2", 2023, 2, "b", "c", 10, 20), "home_win_probability": 0.2, "predicted_margin": -7.0},
        ]
        comparator = [
            {**game("g1", 2023, 1, "a", "b", 21, 14), "home_win_probability": 0.6, "predicted_margin": 2.0},
            {**game("g2", 2023, 2, "b", "c", 10, 20), "home_win_probability": 0.4, "predicted_margin": -3.0},
        ]
        first = MODULE.paired_bootstrap_diagnostic(candidate, comparator, metric="brier", replicates=100, seed=423)
        self.assertEqual(first, MODULE.paired_bootstrap_diagnostic(candidate, comparator, metric="brier", replicates=100, seed=423))
        self.assertLess(first["mean_delta"], 0.0)


if __name__ == "__main__":
    unittest.main()

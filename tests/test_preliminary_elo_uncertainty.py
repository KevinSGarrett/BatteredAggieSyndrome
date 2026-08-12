import importlib.util
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_preliminary_elo_uncertainty",
    ROOT / "tools" / "run_preliminary_elo_uncertainty.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def game(
    game_id,
    season,
    week,
    home,
    away,
    home_points,
    away_points,
    home_prior=0,
    away_prior=0,
):
    return {
        "target_game_id": game_id,
        "season": season,
        "season_type": "regular",
        "week": week,
        "start_utc": f"{season}-09-{week:02d}T00:00:00Z",
        "cutoff_utc": f"{season}-08-{week:02d}T00:00:00Z",
        "home_team_id": home,
        "away_team_id": away,
        "neutral_site": False,
        "cold_start": home_prior == 0 or away_prior == 0,
        "home_prior_games": home_prior,
        "away_prior_games": away_prior,
        "home_points": home_points,
        "away_points": away_points,
        "margin": home_points - away_points,
        "home_win": float(home_points > away_points),
    }


class PreliminaryEloUncertaintyTests(unittest.TestCase):
    def test_poisson_weight_is_deterministic_and_nonnegative(self):
        first = [MODULE.poisson_one(423000, member, "g1") for member in range(64)]
        self.assertEqual(
            first, [MODULE.poisson_one(423000, member, "g1") for member in range(64)]
        )
        self.assertTrue(all(value >= 0 for value in first))
        self.assertGreater(len(set(first)), 1)

    def test_same_batch_outcomes_do_not_change_same_batch_predictions(self):
        rows = [
            game("g1", 2020, 1, "a", "b", 50, 10),
            game("g2", 2020, 1, "a", "c", 10, 50),
        ]
        predictions = MODULE.replay_weighted(rows, member=1, seed=423000)
        self.assertEqual(predictions[0]["rating_diff"], 55.0)
        self.assertEqual(predictions[1]["rating_diff"], 55.0)

    def test_support_decreases_with_more_history(self):
        sparse = game("g1", 2020, 1, "a", "b", 21, 14, 0, 0)
        dense = game("g2", 2020, 2, "a", "b", 21, 14, 20, 20)
        self.assertGreater(MODULE.support_value(sparse), MODULE.support_value(dense))

    def test_support_variance_fit_is_positive(self):
        rows = []
        for index in range(1, 10):
            row = game(f"g{index}", 2020, index, "a", "b", 21 + index, 14, index, index)
            row["margin_residual"] = float(index - 4)
            rows.append(row)
        result = MODULE.fit_support_variance(rows)
        self.assertGreater(result["smearing_scale"], 0.0)
        self.assertGreater(result["minimum_fit_variance"], 0.0)
        self.assertTrue(math.isfinite(result["slope_per_support_unit"]))

    def test_normal_metrics_reward_better_variance(self):
        base = game("g1", 2023, 1, "a", "b", 21, 14)
        well_scaled = [
            {
                **base,
                "home_win_probability": 0.7,
                "predicted_margin": 7.0,
                "margin_variance": 100.0,
            }
        ]
        too_wide = [
            {
                **base,
                "home_win_probability": 0.7,
                "predicted_margin": 7.0,
                "margin_variance": 10000.0,
            }
        ]
        self.assertLess(
            MODULE.normal_metrics(well_scaled)["normal_margin_nll"],
            MODULE.normal_metrics(too_wide)["normal_margin_nll"],
        )


if __name__ == "__main__":
    unittest.main()

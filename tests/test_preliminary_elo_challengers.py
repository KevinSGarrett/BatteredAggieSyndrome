import importlib.util
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_preliminary_elo_challengers",
    ROOT / "tools" / "run_preliminary_elo_challengers.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def game(
    game_id: str,
    *,
    season: int,
    week: int,
    start_utc: str,
    home: str,
    away: str,
    home_win: float,
    margin: float,
    neutral: bool = False,
) -> dict:
    return {
        "target_game_id": game_id,
        "season": season,
        "season_type": "regular",
        "week": week,
        "start_utc": start_utc,
        "home_team_id": home,
        "away_team_id": away,
        "neutral_site": neutral,
        "cold_start": False,
        "home_win": home_win,
        "margin": margin,
    }


class PreliminaryEloChallengerTests(unittest.TestCase):
    def test_inactivity_decay_moves_rating_toward_mean(self):
        rows = [
            game("g1", season=2020, week=1, start_utc="2020-09-01T00:00:00Z", home="a", away="b", home_win=1.0, margin=14.0),
            game("g2", season=2022, week=1, start_utc="2022-09-01T00:00:00Z", home="a", away="c", home_win=1.0, margin=7.0),
        ]
        reference = MODULE.replay(rows, offseason_retention=1.0, margin_cap=None)
        decayed = MODULE.replay(rows, offseason_retention=1.0, margin_cap=None, rating_half_life_days=365.0)
        reference_excess = reference[1]["rating_diff"] - MODULE.HOME_ADVANTAGE
        decayed_excess = decayed[1]["rating_diff"] - MODULE.HOME_ADVANTAGE
        self.assertGreater(reference_excess, 0.0)
        self.assertGreater(decayed_excess, 0.0)
        self.assertLess(decayed_excess, reference_excess)

    def test_site_adjustment_never_changes_neutral_probability(self):
        rows = [
            {"rating_diff": 55.0, "neutral_site": False, "home_win": 1.0},
            {"rating_diff": 55.0, "neutral_site": False, "home_win": 1.0},
            {"rating_diff": 55.0, "neutral_site": False, "home_win": 0.0},
            {"rating_diff": 0.0, "neutral_site": True, "home_win": 0.0},
        ]
        fit = MODULE.fit_site_adjustment(rows)
        transformed = MODULE.apply_site_adjustment(rows, float(fit["rating_point_adjustment"]))
        self.assertTrue(math.isfinite(float(fit["rating_point_adjustment"])))
        self.assertEqual(transformed[3]["home_win_probability"], MODULE.sigmoid(0.0))
        self.assertEqual(transformed[3]["rating_diff"], 0.0)

    def test_logistic_calibration_is_deterministic_and_finite(self):
        rows = [
            {"rating_diff": -200.0, "home_win": 0.0},
            {"rating_diff": -100.0, "home_win": 0.0},
            {"rating_diff": -25.0, "home_win": 1.0},
            {"rating_diff": 25.0, "home_win": 0.0},
            {"rating_diff": 100.0, "home_win": 1.0},
            {"rating_diff": 200.0, "home_win": 1.0},
        ]
        first = MODULE.fit_logistic_calibration(rows)
        second = MODULE.fit_logistic_calibration(rows)
        self.assertEqual(first, second)
        self.assertTrue(math.isfinite(float(first["intercept"])))
        self.assertGreater(float(first["slope_per_400_rating_points"]), 0.0)
        transformed = MODULE.apply_logistic_calibration(rows, float(first["intercept"]), float(first["slope_per_400_rating_points"]))
        self.assertTrue(all(0.0 < row["home_win_probability"] < 1.0 for row in transformed))

    def test_time_decay_selection_uses_only_supplied_fit_rows(self):
        rows = [
            game("g1", season=2010, week=1, start_utc="2010-09-01T00:00:00Z", home="a", away="b", home_win=1.0, margin=10.0),
            game("g2", season=2011, week=1, start_utc="2011-09-01T00:00:00Z", home="b", away="a", home_win=0.0, margin=-7.0),
        ]
        selected, trials = MODULE.select_time_decay(rows)
        self.assertIn(selected, MODULE.TIME_DECAY_HALF_LIFE_GRID_DAYS)
        self.assertEqual([row["half_life_days"] for row in trials], list(MODULE.TIME_DECAY_HALF_LIFE_GRID_DAYS))
        self.assertTrue(all(row["fit_rows"] == 2.0 for row in trials))


if __name__ == "__main__":
    unittest.main()

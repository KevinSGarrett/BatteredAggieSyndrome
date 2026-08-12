from __future__ import annotations

import json
from pathlib import Path
import unittest

from aggie_analytics.features.schedule_stress import materialize


ROOT = Path(__file__).resolve().parents[1]


def game(game_id: str, start: str, cutoff: str, home: str, away: str, margin: int, season: int = 2023) -> dict[str, object]:
    return {"target_game_id": game_id, "season": season, "season_type": "regular", "week": 1, "start_utc": start, "cutoff_utc": cutoff, "home_team_id": home, "away_team_id": away, "neutral_site": False, "margin": margin, "home_win": 1.0 if margin > 0 else 0.0}


class ScheduleStressTests(unittest.TestCase):
    def test_contract_keeps_pit_and_protected_authority_closed(self) -> None:
        contract = json.loads((ROOT / "configs/preliminary_schedule_stress_contract.json").read_text(encoding="utf-8"))
        self.assertFalse(contract["eligibility"]["historical_original_pit"])
        self.assertFalse(contract["eligibility"]["protected_training"])
        self.assertIn("NOT_MATERIALIZED", contract["feature_contract"]["travel_distance"])

    def test_target_game_never_enters_its_own_evidence(self) -> None:
        rows = [
            game("g1", "2023-09-01T00:00:00Z", "2023-08-31T18:00:00Z", "a", "b", 7),
            game("g2", "2023-09-08T00:00:00Z", "2023-09-07T18:00:00Z", "a", "c", -3),
        ]
        features, diagnostics = materialize(rows, {2023})
        by_key = {(row["game_id"], row["team_id"]): row for row in features}
        self.assertEqual(0, by_key[("g1", "a")]["prior_game_count"])
        self.assertEqual(1, by_key[("g2", "a")]["prior_game_count"])
        self.assertEqual(7.0, by_key[("g2", "a")]["days_since_last_game_start"])
        self.assertEqual(1, by_key[("g2", "a")]["games_last_7d"])
        self.assertEqual(3, diagnostics["cold_start_rows"])

    def test_opponent_adjusted_residual_requires_both_histories(self) -> None:
        rows = [
            game("g1", "2023-09-01T00:00:00Z", "2023-08-31T18:00:00Z", "a", "b", 10),
            game("g2", "2023-09-02T00:00:00Z", "2023-09-01T18:00:00Z", "c", "d", 4),
            game("g3", "2023-09-10T00:00:00Z", "2023-09-09T18:00:00Z", "a", "c", 3),
            game("g4", "2023-09-20T00:00:00Z", "2023-09-19T18:00:00Z", "a", "d", 1),
        ]
        features, _ = materialize(rows, {2023})
        row = next(item for item in features if item["game_id"] == "g4" and item["team_id"] == "a")
        self.assertIsNotNone(row["recent_5_opponent_adjusted_margin_mean"])
        self.assertFalse(row["historical_original_pit_eligible"])

    def test_same_day_post_cutoff_game_is_not_admitted(self) -> None:
        rows = [
            game("g1", "2023-09-01T20:00:00Z", "2023-09-01T14:00:00Z", "a", "b", 7),
            game("g2", "2023-09-01T22:00:00Z", "2023-09-01T16:00:00Z", "a", "c", 3),
        ]
        features, _ = materialize(rows, {2023})
        row = next(item for item in features if item["game_id"] == "g2" and item["team_id"] == "a")
        self.assertEqual(0, row["prior_game_count"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
from pathlib import Path
import unittest

from aggie_analytics.temporal.expanded_event_chronology import (
    CLASSIFICATION,
    build_event_chronology_features,
)


ROOT = Path(__file__).resolve().parents[1]


def game(
    game_id: str,
    *,
    season: int,
    week: int,
    start: str,
    home: str,
    away: str,
    home_points: int,
    away_points: int,
) -> dict:
    return {
        "target_game_id": game_id,
        "season": season,
        "season_type": "regular",
        "week": week,
        "start_utc": start,
        "home_team_id": home,
        "away_team_id": away,
        "home_points": home_points,
        "away_points": away_points,
        "neutral_site": False,
        "target_source_record_sha256": game_id * 32,
    }


class ExpandedEventChronologyTests(unittest.TestCase):
    def test_contract_preserves_preliminary_nonpit_authority(self) -> None:
        contract = json.loads(
            (ROOT / "configs/expanded_event_chronology_preliminary_contract.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(contract["classification"], CLASSIFICATION)
        self.assertFalse(contract["event_chronology_policy"]["historical_known_at_eligible"])
        self.assertFalse(contract["split_policy"]["protected_split_opened"])
        self.assertFalse(any(contract["protected_nonclaims"].values()))
        self.assertEqual(
            contract["game_start_reconciliation"][
                "pinned_population_maximum_observed_absolute_delta_minutes"
            ],
            270,
        )
        self.assertEqual(
            contract["game_start_reconciliation"]["larger_delta"], "FAIL_CLOSED"
        )

    def test_same_week_outcome_is_never_a_prior(self) -> None:
        rows = [
            game(
                "a" * 2,
                season=2020,
                week=1,
                start="2020-09-05T16:00:00Z",
                home="team-a",
                away="team-b",
                home_points=20,
                away_points=10,
            ),
            game(
                "b" * 2,
                season=2020,
                week=1,
                start="2020-09-06T16:00:00Z",
                home="team-a",
                away="team-c",
                home_points=30,
                away_points=20,
            ),
        ]
        features, report = build_event_chronology_features(rows)
        self.assertEqual(features[1]["home_prior_games"], 0)
        self.assertGreater(report["same_batch_candidates_excluded"], 0)

    def test_prior_week_is_available_but_never_pit_promoted(self) -> None:
        rows = [
            game(
                "c" * 2,
                season=2020,
                week=1,
                start="2020-09-05T16:00:00Z",
                home="team-a",
                away="team-b",
                home_points=20,
                away_points=10,
            ),
            game(
                "d" * 2,
                season=2020,
                week=2,
                start="2020-09-12T16:00:00Z",
                home="team-a",
                away="team-c",
                home_points=30,
                away_points=20,
            ),
        ]
        features, report = build_event_chronology_features(rows)
        self.assertEqual(features[1]["home_prior_games"], 1)
        self.assertEqual(features[1]["prior_win_rate_diff"], None)
        self.assertFalse(features[1]["historical_known_at_eligible"])
        self.assertEqual(report["target_game_evidence_rows"], 0)

    def test_duplicate_target_identity_fails_closed(self) -> None:
        row = game(
            "e" * 2,
            season=2020,
            week=1,
            start="2020-09-05T16:00:00Z",
            home="team-a",
            away="team-b",
            home_points=20,
            away_points=10,
        )
        with self.assertRaisesRegex(ValueError, "duplicate target game identity"):
            build_event_chronology_features([row, row])


if __name__ == "__main__":
    unittest.main()

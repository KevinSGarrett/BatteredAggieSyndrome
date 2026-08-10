from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from aggie_analytics.temporal.historical_recovery import (
    STRICT_OUTCOME_DISPOSITION,
    TargetGame,
    admit_strict_cross_source_outcomes,
    build_pregame_team_priors,
    materialize_prior_cells,
    materialize_team_outcome_observations,
    record_for_storage,
)


UTC = timezone.utc
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


def _outcome_row(**overrides):
    row = {
        "source_game_id": "401000001",
        "canonical_game_id": "game-source",
        "season": 2022,
        "season_type": 2,
        "start_at_utc": "2022-09-01T00:00:00Z",
        "canonical_home_team_id": "team-a",
        "canonical_away_team_id": "team-b",
        "home_points": 31,
        "away_points": 17,
        "completed": True,
        "source_known_at_utc": "2023-05-04T23:19:09Z",
        "source_capture_id": SHA_A,
        "source_payload_sha256": SHA_B,
        "source_record_evidence_sha256": SHA_C,
        "canonical_team_pair_match": True,
        "normalized_outcome_exact_match": True,
        "reconciliation_disposition": STRICT_OUTCOME_DISPOSITION,
    }
    row.update(overrides)
    return row


def _target(game_id="target-game", start=None):
    return TargetGame(
        game_id=game_id,
        season=2023,
        season_type="regular",
        week=1,
        start_utc=start or datetime(2023, 9, 1, tzinfo=UTC),
        home_team_id="team-a",
        away_team_id="team-b",
        neutral_site=False,
    )


class HistoricalKnownAtReplayTests(unittest.TestCase):
    def test_strict_lane_does_not_promote_single_source_candidate(self) -> None:
        row = _outcome_row(
            reconciliation_disposition="ELIGIBLE_REPOSITORY_VERSIONED_OUTCOME_SINGLE_SOURCE"
        )
        self.assertEqual(admit_strict_cross_source_outcomes([row]), ())

    def test_strict_lane_fails_closed_on_invalid_evidence(self) -> None:
        mutations = [
            ("completed", False),
            ("canonical_team_pair_match", False),
            ("normalized_outcome_exact_match", False),
            ("source_record_evidence_sha256", "not-a-hash"),
        ]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    admit_strict_cross_source_outcomes(
                        [_outcome_row(**{field: value})]
                    )

    def test_team_observations_preserve_orientation_and_outcome(self) -> None:
        outcomes = admit_strict_cross_source_outcomes([_outcome_row()])
        observations = materialize_team_outcome_observations(outcomes)
        self.assertEqual(len(observations), 2)
        home = next(row for row in observations if row.team_id == "team-a")
        away = next(row for row in observations if row.team_id == "team-b")
        self.assertEqual(
            (home.site, home.result, home.points_for, home.points_against),
            ("HOME", "WIN", 31, 17),
        )
        self.assertEqual(
            (away.site, away.result, away.points_for, away.points_against),
            ("AWAY", "LOSS", 17, 31),
        )

    def test_pregame_priors_are_cutoff_safe_and_target_excluding(self) -> None:
        outcomes = admit_strict_cross_source_outcomes([_outcome_row()])
        observations = materialize_team_outcome_observations(outcomes)
        rows = build_pregame_team_priors(observations, [_target()])
        self.assertEqual(len(rows), 2)
        home = next(row for row in rows if row.team_id == "team-a")
        self.assertEqual(home.cutoff_utc, datetime(2023, 8, 31, tzinfo=UTC))
        self.assertEqual(home.prior_games, 1)
        self.assertEqual(home.prior_win_rate, 1.0)
        self.assertEqual(home.prior_points_for_mean, 31.0)
        self.assertEqual(home.prior_points_against_mean, 17.0)
        self.assertIsNone(home.missingness)
        self.assertTrue(
            all(
                obs_id.startswith("team_outcome_")
                for obs_id in home.eligible_observation_ids
            )
        )

        same_game_target = _target(game_id="game-source")
        excluded = build_pregame_team_priors(observations, [same_game_target])
        self.assertTrue(all(row.prior_games is None for row in excluded))
        self.assertTrue(
            all(row.missingness == "SOURCE_MISSING" for row in excluded)
        )

    def test_known_after_cutoff_is_not_admitted_and_ids_are_deterministic(self) -> None:
        outcomes = admit_strict_cross_source_outcomes([_outcome_row()])
        observations = materialize_team_outcome_observations(outcomes)
        early_target = _target(start=datetime(2023, 5, 5, 12, tzinfo=UTC))
        first = build_pregame_team_priors(observations, [early_target])
        second = build_pregame_team_priors(observations, [early_target])
        self.assertEqual(first, second)
        self.assertTrue(all(row.prior_games is None for row in first))

    def test_storage_records_use_utc_strings_and_lists(self) -> None:
        outcomes = admit_strict_cross_source_outcomes([_outcome_row()])
        rows = build_pregame_team_priors(
            materialize_team_outcome_observations(outcomes), [_target()]
        )
        record = record_for_storage(rows[0])
        self.assertTrue(record["cutoff_utc"].endswith("Z"))
        self.assertIsInstance(record["eligible_observation_ids"], list)

    def test_feature_cells_have_independent_lineage_and_missingness(self) -> None:
        outcomes = admit_strict_cross_source_outcomes([_outcome_row()])
        rows = build_pregame_team_priors(
            materialize_team_outcome_observations(outcomes), [_target()]
        )
        cells = materialize_prior_cells(rows)
        self.assertEqual(len(cells), 8)
        self.assertEqual(len({cell.cell_id for cell in cells}), 8)
        self.assertEqual(len({cell.lineage_sha256 for cell in cells}), 8)
        self.assertTrue(all(cell.observation_ids for cell in cells))
        self.assertTrue(all(cell.missingness is None for cell in cells))

    def test_cutoff_lead_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            build_pregame_team_priors(
                (), [_target()], cutoff_lead=timedelta(0)
            )


if __name__ == "__main__":
    unittest.main()

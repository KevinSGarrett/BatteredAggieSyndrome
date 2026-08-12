from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    import polars as pl
except (
    ImportError
):  # pragma: no cover - exercised by the minimal hosted core environment
    pl = None

from aggie_analytics.features.sustainability import (
    _aggregate_window,
    _build_profiles,
    _verify_sources,
)


ROOT = Path(__file__).resolve().parents[1]


class PreliminarySustainabilityTests(unittest.TestCase):
    @unittest.skipIf(
        pl is None, "optional data-engineering dependency polars is not installed"
    )
    def test_aggregate_window_preserves_close_and_tail_semantics(self) -> None:
        rows = pl.DataFrame(
            {
                "team_id": ["a", "a", "a", "a"],
                "season": [2020, 2021, 2021, 2022],
                "win_share_value": [1.0, 0.0, 1.0, 0.0],
                "points_for": [21, 10, 42, 7],
                "points_against": [17, 31, 10, 10],
                "close_game": [True, False, False, True],
                "team_margin": [4, -21, 32, -3],
                "downside_tail": [False, True, False, False],
                "upside_tail": [False, False, True, False],
                "source_known_at_utc": ["2023-05-01T00:00:00Z"] * 4,
            }
        )
        row = _aggregate_window(rows, "all").to_dicts()[0]
        self.assertEqual(4, row["all_source_game_count"])
        self.assertAlmostEqual(0.5, row["all_win_share"])
        self.assertAlmostEqual(0.5, row["all_close_game_share"])
        self.assertAlmostEqual(0.5, row["all_close_win_share"])
        self.assertAlmostEqual(0.0, row["all_close_win_share_minus_overall"])
        self.assertAlmostEqual(0.25, row["all_downside_tail_rate"])
        self.assertAlmostEqual(0.25, row["all_upside_tail_rate"])
        self.assertAlmostEqual(0.0, row["all_tail_imbalance"])
        self.assertAlmostEqual(80 / 148, row["all_score_share"])

    @unittest.skipIf(
        pl is None, "optional data-engineering dependency polars is not installed"
    )
    def test_close_residual_is_null_without_close_games(self) -> None:
        rows = pl.DataFrame(
            {
                "team_id": ["a"],
                "season": [2022],
                "win_share_value": [1.0],
                "points_for": [40],
                "points_against": [10],
                "close_game": [False],
                "team_margin": [30],
                "downside_tail": [False],
                "upside_tail": [True],
                "source_known_at_utc": ["2023-05-01T00:00:00Z"],
            }
        )
        row = _aggregate_window(rows, "all").to_dicts()[0]
        self.assertIsNone(row["all_close_win_share"])
        self.assertIsNone(row["all_close_win_share_minus_overall"])

    def test_profile_contract_preserves_pandemic_and_sparse_evidence(self) -> None:
        contract = json.loads(
            (ROOT / "configs" / "preliminary_sustainability_contract.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            [2020, 2021, 2022], contract["source_contract"]["recent_window_seasons"]
        )
        self.assertIn(
            "pandemic_2020_game_share", contract["feature_contract"]["features"]
        )
        self.assertIn(
            "turnover_luck", contract["feature_contract"]["unsupported_fields"]
        )
        self.assertFalse(contract["eligibility"]["historical_original_pit_eligibility"])
        self.assertFalse(contract["authority"]["protected_evaluation_admission"])

    @unittest.skipIf(
        pl is None, "optional data-engineering dependency polars is not installed"
    )
    def test_duplicate_source_games_fail_closed(self) -> None:
        contract = {
            "source_contract": {
                "source_seasons": [2022],
                "recent_window_seasons": [2022],
            }
        }
        row = {
            "canonical_game_id": "g1",
            "season": 2022,
            "season_type": 2,
            "game_start_utc": "2022-09-01T00:00:00Z",
            "completed_known_by_utc": "2023-01-01T00:00:00Z",
            "source_known_at_utc": "2023-05-01T00:00:00Z",
            "source_capture_id": "c1",
            "source_record_evidence_sha256": "a" * 64,
            "home_team_id": "h",
            "away_team_id": "a",
            "home_points": 20,
            "away_points": 10,
        }
        with self.assertRaisesRegex(ValueError, "duplicate canonical"):
            _build_profiles(pl.from_dicts([row, row]), contract)

    def test_pinned_hash_drift_fails_closed(self) -> None:
        contract = json.loads(
            (ROOT / "configs" / "preliminary_sustainability_contract.json").read_text(
                encoding="utf-8"
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [
                root
                / "pit_state"
                / "historical_known_at"
                / "sha256"
                / contract["source_contract"]["dataset_identity"]
                / "accepted_game_outcomes.parquet",
                root
                / "features"
                / "historical_known_at"
                / "sha256"
                / contract["source_contract"]["dataset_identity"]
                / "target_game_cutoffs.parquet",
                root
                / "manifests"
                / "historical_known_at"
                / "sha256"
                / contract["source_contract"]["dataset_identity"]
                / "known_at_replay_manifest.json",
            ]
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"drift")
            with self.assertRaisesRegex(ValueError, "hash drift"):
                _verify_sources(root, contract)


if __name__ == "__main__":
    unittest.main()

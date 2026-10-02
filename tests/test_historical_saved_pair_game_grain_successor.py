"""Historical C20/C21 saved-pair game-grain successor regressions."""

from __future__ import annotations

import hashlib
import math
import unittest
from pathlib import Path

from aggie_analytics.data.historical_saved_pair_game_grain_successor import (
    HistoricalPairSuccessorError,
    PREDECESSORS,
    load_predecessor,
    succeed_pair,
)
from aggie_analytics.data.week1_2026_game_grain_national_forecast_successor import (
    normalize_pair_probabilities,
)
from aggie_analytics.scientific_reference.metrics import brier_score, log_loss


def _pair(
    *,
    candidate: str,
    p_a: float,
    p_b: float,
    m_a: float | None = None,
    m_b: float | None = None,
    win_a: bool = True,
) -> tuple[dict, dict]:
    left = {
        "candidate_id": candidate,
        "canonical_game_id": "SRC-002:GAME:1",
        "canonical_team_id": "SRC-002:TEAM:A",
        "predicted_win_probability": p_a,
        "predicted_margin": m_a,
        "observed_win": win_a,
        "observed_margin": 7 if win_a else -7,
        "fold_id": "FOLD-01",
    }
    right = {
        "candidate_id": candidate,
        "canonical_game_id": "SRC-002:GAME:1",
        "canonical_team_id": "SRC-002:TEAM:B",
        "predicted_win_probability": p_b,
        "predicted_margin": m_b,
        "observed_win": not win_a,
        "observed_margin": -7 if win_a else 7,
        "fold_id": "FOLD-01",
    }
    return left, right


class HistoricalSavedPairSuccessorTests(unittest.TestCase):
    def test_logistic_pair_normalize_is_complementary(self) -> None:
        spec = PREDECESSORS["20"]
        left, right = _pair(candidate="national_logistic_l2", p_a=0.7, p_b=0.4)
        built = succeed_pair(left, right, spec=spec, source_cycle="20")
        expected = normalize_pair_probabilities(0.7, 0.4)
        self.assertTrue(built["game"]["pair_coherence"])
        self.assertAlmostEqual(
            built["game"]["probability_a"], expected["p_a_game"], places=10
        )
        self.assertAlmostEqual(
            built["game"]["probability_b"] + built["game"]["probability_a"],
            1.0,
            places=12,
        )
        self.assertFalse(built["game"]["joint_probability_margin_interval"])

    def test_ridge_margins_are_antisymmetric_projection(self) -> None:
        spec = PREDECESSORS["20"]
        left, right = _pair(
            candidate="national_margin_ridge",
            p_a=0.8,
            p_b=0.3,
            m_a=10.0,
            m_b=-6.0,
        )
        built = succeed_pair(left, right, spec=spec, source_cycle="20")
        self.assertAlmostEqual(built["game"]["expected_margin_a"], 8.0, places=10)
        self.assertAlmostEqual(built["game"]["expected_margin_b"], -8.0, places=10)
        self.assertEqual(
            built["game"]["margin_support"],
            "ANTISYMMETRIC_PROJECTION_OF_SAVED_TEAM_MARGINS",
        )

    def test_base_rate_stays_control_only(self) -> None:
        spec = PREDECESSORS["20"]
        left, right = _pair(candidate="national_base_rate", p_a=0.5, p_b=0.5)
        built = succeed_pair(left, right, spec=spec, source_cycle="20")
        self.assertEqual(built["game"]["probability_a"], 0.5)
        self.assertTrue(built["game"]["control_only"])

    def test_empty_team_ids_rejected(self) -> None:
        spec = PREDECESSORS["20"]
        left, right = _pair(candidate="national_elo", p_a=0.6, p_b=0.4)
        left["canonical_team_id"] = ""
        with self.assertRaises(HistoricalPairSuccessorError):
            succeed_pair(left, right, spec=spec, source_cycle="20")

    def test_zero_probability_does_not_pair_normalize(self) -> None:
        spec = PREDECESSORS["20"]
        left, right = _pair(candidate="prior_only", p_a=0.0, p_b=0.8)
        built = succeed_pair(left, right, spec=spec, source_cycle="20")
        self.assertIsNone(built["game"]["probability_a"])
        self.assertEqual(
            built["game"]["abstention_reason"],
            "ABSTAIN_PROBABILITY_DISTRIBUTION_INCOHERENCE",
        )

    def test_unique_game_metrics_do_not_double_count(self) -> None:
        predicted = [0.7]
        observed = [1.0]
        self.assertAlmostEqual(brier_score(predicted, observed), 0.09, places=12)
        self.assertGreater(log_loss(predicted, observed), 0.0)

    def test_predecessor_bytes_are_immutable_when_mounted(self) -> None:
        data_root = Path(r"C:\BatteredAggieSyndrome.data")
        path = data_root / PREDECESSORS["20"]["relative_path"]
        if not path.is_file():
            self.skipTest("C20 predecessor payload is not mounted")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(digest, PREDECESSORS["20"]["sha256"])
        rows, spec = load_predecessor(data_root, "20")
        sample = next(
            row for row in rows if row["candidate_id"] == "national_logistic_l2"
        )
        partner = next(
            row
            for row in rows
            if row["candidate_id"] == sample["candidate_id"]
            and row["canonical_game_id"] == sample["canonical_game_id"]
            and row["canonical_team_id"] != sample["canonical_team_id"]
        )
        left, right = sorted(
            (sample, partner), key=lambda item: str(item["canonical_team_id"])
        )
        raw_sum = float(left["predicted_win_probability"]) + float(
            right["predicted_win_probability"]
        )
        self.assertGreater(abs(raw_sum - 1.0), 1e-8)
        built = succeed_pair(left, right, spec=spec, source_cycle="20")
        self.assertTrue(built["game"]["pair_coherence"])
        self.assertLessEqual(
            abs(built["game"]["probability_a"] + built["game"]["probability_b"] - 1.0),
            1e-12,
        )
        self.assertEqual(
            left["predicted_win_probability"] + right["predicted_win_probability"],
            raw_sum,
        )
        self.assertTrue(math.isfinite(float(built["game"]["probability_a"])))


if __name__ == "__main__":
    unittest.main()

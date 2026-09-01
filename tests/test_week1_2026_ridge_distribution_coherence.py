from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data.week1_2026_ridge_distribution_coherence import (  # noqa: E402
    audit_cycle24_ridge_forecast_row,
    classify_ridge_distribution_coherence,
    reconstruct_ridge_surfaces,
)

DIVISOR = 1.7013016167040798
STDEV = 17.7396030753
QUANTILE = 1.959964
A_AND_M_MARGIN = 22.2506043541
A_AND_M_INTERVAL = [-12.5183790478, 57.019587756]
A_AND_M_EMITTED = 0.9999979105
INCOHERENCE = "REVIEW_REQUIRED_PROBABILITY_DISTRIBUTION_INCOHERENCE"


class RidgeDistributionCoherenceTests(unittest.TestCase):
    def test_cycle24_emits_logistic_of_margin_over_divisor(self) -> None:
        reconstructed = reconstruct_ridge_surfaces(
            expected_margin=A_AND_M_MARGIN,
            residual_stdev=STDEV,
            logistic_link_scale_divisor=DIVISOR,
            normal_quantile=QUANTILE,
        )
        self.assertAlmostEqual(
            reconstructed["probability_if_divisor_used_as_link_scale"],
            A_AND_M_EMITTED,
            places=9,
        )
        self.assertAlmostEqual(
            reconstructed["interval"][0], A_AND_M_INTERVAL[0], places=6
        )
        self.assertAlmostEqual(
            reconstructed["interval"][1], A_AND_M_INTERVAL[1], places=6
        )

    def test_interval_implied_win_probability_is_far_from_emitted(self) -> None:
        reconstructed = reconstruct_ridge_surfaces(
            expected_margin=A_AND_M_MARGIN,
            residual_stdev=STDEV,
            logistic_link_scale_divisor=DIVISOR,
            normal_quantile=QUANTILE,
        )
        implied = reconstructed["probability_if_normal_residual_distribution"]
        self.assertGreater(implied, 0.89)
        self.assertLess(implied, 0.91)
        self.assertGreater(abs(A_AND_M_EMITTED - implied), 0.1)

    def test_saturated_probability_with_interval_crossing_zero_is_incoherent(
        self,
    ) -> None:
        classified = classify_ridge_distribution_coherence(
            expected_margin=A_AND_M_MARGIN,
            emitted_probability=A_AND_M_EMITTED,
            interval=A_AND_M_INTERVAL,
            residual_stdev=STDEV,
            logistic_link_scale_divisor=DIVISOR,
            normal_quantile=QUANTILE,
        )
        self.assertEqual(classified["state"], INCOHERENCE)
        self.assertIn(
            "SATURATED_PROBABILITY_WITH_INTERVAL_CROSSING_ZERO", classified["reasons"]
        )
        self.assertFalse(classified["cycle24_row_rewritten"])
        self.assertFalse(classified["mapping_changed"])
        self.assertFalse(classified["chosen_using_a_and_m_or_market_or_week1_outcome"])
        self.assertFalse(classified["presented_as_one_distribution"])

    def test_normal_cdf_probability_with_same_interval_is_coherent(self) -> None:
        reconstructed = reconstruct_ridge_surfaces(
            expected_margin=A_AND_M_MARGIN,
            residual_stdev=STDEV,
            logistic_link_scale_divisor=DIVISOR,
            normal_quantile=QUANTILE,
        )
        classified = classify_ridge_distribution_coherence(
            expected_margin=A_AND_M_MARGIN,
            emitted_probability=reconstructed[
                "probability_if_normal_residual_distribution"
            ],
            interval=reconstructed["interval"],
            residual_stdev=STDEV,
            logistic_link_scale_divisor=STDEV,
            normal_quantile=QUANTILE,
        )
        self.assertEqual(classified["state"], "PROBABILITY_AND_INTERVAL_COHERENT")
        self.assertTrue(classified["presented_as_one_distribution"])

    def test_audit_does_not_rewrite_cycle24_row_identity(self) -> None:
        row = {
            "forecast_row_identity": "f514d6c6eaa5b9261074224717f8813e3d4e9235c358c4bd12bc0e6b0627a119",
            "contest_identity": "0d28c02c699e878bd8a0526517d332c1a7218e878b2173a72973d19639f5fa02",
            "candidate_id": "national_margin_ridge",
            "expected_margin_home": A_AND_M_MARGIN,
            "margin_interval_home": A_AND_M_INTERVAL,
            "probability_home": A_AND_M_EMITTED,
            "row_state": "FORECAST_FROZEN",
        }
        audit = audit_cycle24_ridge_forecast_row(
            row,
            residual_stdev=STDEV,
            logistic_link_scale_divisor=DIVISOR,
            normal_quantile=QUANTILE,
            saturation_low=0.01,
            saturation_high=0.99,
        )
        self.assertEqual(audit["forecast_row_identity"], row["forecast_row_identity"])
        self.assertFalse(audit["cycle24_row_rewritten"])
        self.assertEqual(audit["adequacy_state"], INCOHERENCE)

    def test_thresholds_are_not_fit_to_the_a_and_m_margin(self) -> None:
        other_margin = 18.0
        reconstructed = reconstruct_ridge_surfaces(
            expected_margin=other_margin,
            residual_stdev=STDEV,
            logistic_link_scale_divisor=DIVISOR,
            normal_quantile=QUANTILE,
        )
        emitted = reconstructed["probability_if_divisor_used_as_link_scale"]
        classified = classify_ridge_distribution_coherence(
            expected_margin=other_margin,
            emitted_probability=emitted,
            interval=reconstructed["interval"],
            residual_stdev=STDEV,
            logistic_link_scale_divisor=DIVISOR,
            normal_quantile=QUANTILE,
        )
        self.assertEqual(classified["state"], INCOHERENCE)
        self.assertTrue(reconstructed["interval_crosses_zero"])
        self.assertGreaterEqual(emitted, 0.99)


if __name__ == "__main__":
    unittest.main()

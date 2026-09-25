"""Isolated Cycle #27 ridge 80%/95% interval-label successor regressions."""

from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from aggie_analytics.data.cycle27_ridge_interval_label_successor import (  # noqa: E402
    C26_DATASET_IDENTITY,
    C26_GATE_IDENTITY,
    CANDIDATE_ID,
    CANDIDATE_VERSION,
    PREDECESSOR_CANDIDATE_ID,
    RETROSPECTIVE,
    RidgeIntervalLabelSuccessorError,
    build_successor,
    choose_interval_level,
    correct_ridge_interval_row,
    reconstructed_interval_mass,
)
from aggie_analytics.scientific_reference.coherence import interval_quantile  # noqa: E402

STDEV = 17.7396030753
DECLARED_LEVEL = 0.8
AS_OF = "2026-09-04T16:45:00Z"


def _interval(mean: float, level: float = DECLARED_LEVEL) -> list[float]:
    half = interval_quantile(level) * STDEV
    return [mean - half, mean + half]


def _ridge_row(
    *,
    mean: float,
    labeled: float = 0.95,
    kickoff: str,
    row_id: str,
    contest: str = "contest-a",
    ncaa: str = "1",
) -> dict:
    interval = _interval(mean)
    z = mean / STDEV
    probability = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return {
        "candidate_id": PREDECESSOR_CANDIDATE_ID,
        "forecast_row_identity": row_id,
        "contest_identity": contest,
        "ncaa_contest_id": ncaa,
        "expected_margin_home": mean,
        "probability_home": probability,
        "probability_away": 1.0 - probability,
        "margin_interval_home": interval,
        "nominal_interval_level": labeled,
        "kickoff_bound_utc": kickoff,
        "row_state": "UNTRUSTED_SHADOW",
    }


class IntervalMassAndLevelTests(unittest.TestCase):
    def test_reconstructed_mass_is_eighty_not_ninety_five(self) -> None:
        mean = 22.2506043541
        mass = reconstructed_interval_mass(
            expected_margin=mean,
            interval=_interval(mean),
            residual_stdev=STDEV,
        )
        self.assertAlmostEqual(mass, 0.8, places=6)
        mass_95 = reconstructed_interval_mass(
            expected_margin=mean,
            interval=_interval(mean, 0.95),
            residual_stdev=STDEV,
        )
        self.assertAlmostEqual(mass_95, 0.95, places=6)
        self.assertGreater(abs(mass - 0.95), 0.1)

    def test_level_cannot_be_chosen_from_focus_or_market(self) -> None:
        with self.assertRaises(RidgeIntervalLabelSuccessorError):
            choose_interval_level(
                reconstructed_masses=(0.8,),
                declared_gate_level=0.8,
                focus_game_level=0.8,
            )
        with self.assertRaises(RidgeIntervalLabelSuccessorError):
            choose_interval_level(
                reconstructed_masses=(0.8,),
                declared_gate_level=0.8,
                market_level=0.95,
            )
        with self.assertRaises(RidgeIntervalLabelSuccessorError):
            choose_interval_level(
                reconstructed_masses=(0.8,),
                declared_gate_level=0.8,
                week1_outcome_level=0.8,
            )

    def test_gate_declared_level_is_used_when_masses_agree(self) -> None:
        level = choose_interval_level(
            reconstructed_masses=(0.8000001, 0.7999994),
            declared_gate_level=0.8,
        )
        self.assertEqual(level, 0.8)


class SuccessorIdentityTests(unittest.TestCase):
    def test_new_identities_preserve_lineage_and_original_scoring(self) -> None:
        kicked = _ridge_row(
            mean=10.0,
            kickoff="2026-09-03T22:00:00Z",
            row_id="old-row-kicked",
            ncaa="100",
        )
        future = _ridge_row(
            mean=-4.0,
            kickoff="2026-09-05T23:00:00Z",
            row_id="old-row-future",
            contest="contest-b",
            ncaa="200",
        )
        built = build_successor(
            predecessor_rows=[kicked, future],
            residual_stdev=STDEV,
            declared_gate_level=DECLARED_LEVEL,
            as_of_utc=AS_OF,
        )
        self.assertEqual(built["ridge_row_count"], 2)
        self.assertEqual(built["candidate_id"], CANDIDATE_ID)
        self.assertEqual(built["candidate_version"], CANDIDATE_VERSION)
        self.assertEqual(built["predecessor_gate_identity"], C26_GATE_IDENTITY)
        self.assertEqual(built["predecessor_dataset_identity"], C26_DATASET_IDENTITY)
        self.assertFalse(built["predecessor_gate_or_dataset_overwritten"])
        self.assertFalse(built["level_chosen_from_a_and_m_or_market_or_week1_outcome"])
        self.assertTrue(built["original_as_issued_scoring_preserved"])
        self.assertFalse(built["probability_values_changed"])
        self.assertFalse(built["interval_endpoints_changed"])
        self.assertEqual(built["new_prospective_freeze_count"], 0)
        self.assertEqual(built["retrospective_diagnostic_count"], 1)
        rows = {row["predecessor_forecast_row_identity"]: row for row in built["rows"]}
        kicked_out = rows["old-row-kicked"]
        future_out = rows["old-row-future"]
        self.assertNotEqual(kicked_out["forecast_row_identity"], "old-row-kicked")
        self.assertNotEqual(future_out["forecast_row_identity"], "old-row-future")
        self.assertEqual(kicked_out["issuance_class"], RETROSPECTIVE)
        self.assertEqual(future_out["issuance_class"], "PROSPECTIVE_SHADOW_LABEL_CORRECTION")
        self.assertFalse(kicked_out["new_prospective_freeze"])
        self.assertFalse(kicked_out["frozen_before_kickoff_claim"])
        self.assertEqual(kicked_out["successor_nominal_interval_level"], 0.8)
        self.assertEqual(kicked_out["predecessor_nominal_interval_level"], 0.95)
        self.assertEqual(kicked_out["probability_home"], kicked["probability_home"])
        self.assertEqual(kicked_out["margin_interval_home"], kicked["margin_interval_home"])

    def test_reusing_old_row_identity_is_rejected_by_construction(self) -> None:
        row = _ridge_row(
            mean=5.0, kickoff="2026-09-05T23:00:00Z", row_id="keep-me"
        )
        corrected = correct_ridge_interval_row(
            row,
            residual_stdev=STDEV,
            declared_gate_level=DECLARED_LEVEL,
            as_of_utc=AS_OF,
            predecessor_gate_identity=C26_GATE_IDENTITY,
            predecessor_dataset_identity=C26_DATASET_IDENTITY,
        )
        self.assertNotEqual(corrected["forecast_row_identity"], "keep-me")
        self.assertEqual(corrected["predecessor_forecast_row_identity"], "keep-me")

    def test_focus_game_cannot_drive_a_single_row_correction(self) -> None:
        row = _ridge_row(
            mean=22.2506043541,
            kickoff="2026-09-05T23:00:00Z",
            row_id="am-row",
        )
        with self.assertRaises(RidgeIntervalLabelSuccessorError):
            correct_ridge_interval_row(
                row,
                residual_stdev=STDEV,
                declared_gate_level=DECLARED_LEVEL,
                as_of_utc=AS_OF,
                predecessor_gate_identity=C26_GATE_IDENTITY,
                predecessor_dataset_identity=C26_DATASET_IDENTITY,
                focus_game_level=0.8,
            )

    def test_drifted_c26_lineage_is_rejected(self) -> None:
        row = _ridge_row(
            mean=5.0, kickoff="2026-09-05T23:00:00Z", row_id="x"
        )
        with self.assertRaises(RidgeIntervalLabelSuccessorError):
            correct_ridge_interval_row(
                row,
                residual_stdev=STDEV,
                declared_gate_level=DECLARED_LEVEL,
                as_of_utc=AS_OF,
                predecessor_gate_identity="0" * 64,
                predecessor_dataset_identity=C26_DATASET_IDENTITY,
            )


class FrozenC26PreservationTests(unittest.TestCase):
    def test_committed_c26_gate_and_dataset_remain_untouched(self) -> None:
        gate = json.loads(
            (
                REPO
                / "artifacts/forecast/week1_2026_game_grain_national_forecast_successor_gate.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(gate["gate_identity"], C26_GATE_IDENTITY)
        self.assertEqual(gate["dataset_identity"], C26_DATASET_IDENTITY)
        self.assertEqual(gate["joint_distribution"]["interval_probability"], 0.8)


if __name__ == "__main__":
    unittest.main()

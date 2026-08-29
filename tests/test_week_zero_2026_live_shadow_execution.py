"""Fail-closed and tamper coverage for the Week Zero 2026 live shadow execution lane."""

from __future__ import annotations

import copy
import math
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.modeling.week_zero_live_shadow_execution import (  # noqa: E402
    AWAITING,
    CANCELED,
    FINAL_OBSERVED,
    MISSED_CUTOFF,
    PROOF_COMPLETE,
    SCORED,
    LiveExecutionViolation,
    assert_no_scored_row_without_a_complete_proof,
    brier_score,
    calibration_bins,
    classify_official_status,
    execute_week_zero,
    gate_identity_of,
    load_contract,
    log_loss,
    parse_official_finals,
    score_eligible_rows,
    validate_artifact,
)

KICKOFF = "2026-08-29T19:00:00Z"
BEFORE = datetime(2026, 8, 29, 6, 0, tzinfo=timezone.utc)
AFTER = datetime(2026, 8, 30, 6, 0, tzinfo=timezone.utc)


def synthetic_contract() -> dict[str, object]:
    return {
        "calibration_bin_edges": [0.0, 0.5, 1.0],
        "final_status_tokens": {
            "CANCELED_OR_SUSPENDED": ["canceled", "postponed", "suspended", "no contest"],
            "FINAL": ["final"],
        },
        "log_loss_clip": [1e-15, 1 - 1e-15],
        "outcome_exclusion": "AN_OUTCOME_IS_READ_ONLY_FROM_A_CAPTURE_RETRIEVED_AT_OR_AFTER_THE_KICKOFF_BOUND",
        "scientific_nonclaims": {},
        "week_zero_game_dates": ["2026-08-29"],
    }


def synthetic_population() -> dict[str, object]:
    return {
        "audit_gate": {
            "gate_identity": "audit-identity",
            "row_verdicts": [
                {
                    "candidate_id": "national_base_rate",
                    "ncaa_contest_id": "6594361",
                    "verdict": PROOF_COMPLETE,
                }
            ],
        },
        "forecast_gate": {"gate_identity": "forecast-identity"},
        "forecast_rows": [
            {
                "candidate_id": "national_base_rate",
                "created_at_utc": "2026-08-28T23:34:57Z",
                "forecast_state": "FORECAST_FROZEN",
                "ncaa_contest_id": "6594361",
                "probability_home_win": 0.75,
                "source_published_game_date": "2026-08-29",
            }
        ],
        "snapshot_records": [
            {
                "kickoff_utc_conservative_lower_bound": KICKOFF,
                "ncaa_contest_id": "6594361",
                "snapshot": {"snapshot_frozen_at_utc": "2026-08-28T23:34:57Z"},
                "source_published_clock_text": "03:00 PM",
                "source_published_game_date": "2026-08-29",
            }
        ],
    }


def synthetic_capture(finals: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "capture_identity": "capture-identity",
        "official_finals": finals or [],
        "refreshed_contests": [
            {
                "game_date": "2026-08-29",
                "ncaa_contest_id": "6594361",
                "source_published_clock_text": "03:00 PM",
                "source_published_game_date": "2026-08-29",
            }
        ],
    }


class ScoringMathTests(unittest.TestCase):
    def test_brier_and_log_loss_reward_a_confident_correct_call(self) -> None:
        self.assertAlmostEqual(brier_score(1.0, 1), 0.0)
        self.assertAlmostEqual(brier_score(0.0, 1), 1.0)
        self.assertLess(log_loss(0.9, 1, [1e-15, 1 - 1e-15]), log_loss(0.6, 1, [1e-15, 1 - 1e-15]))

    def test_log_loss_clips_rather_than_diverging(self) -> None:
        self.assertTrue(math.isfinite(log_loss(0.0, 1, [1e-15, 1 - 1e-15])))
        self.assertTrue(math.isfinite(log_loss(1.0, 0, [1e-15, 1 - 1e-15])))

    def test_an_empty_population_yields_null_metrics_not_zero(self) -> None:
        metrics = score_eligible_rows([], synthetic_contract())
        self.assertIsNone(metrics["brier_score"])
        self.assertIsNone(metrics["accuracy"])
        self.assertEqual(metrics["scored_row_count"], 0)

    def test_calibration_bins_partition_every_row_exactly_once(self) -> None:
        rows = [
            {"home_win": 1, "probability_home_win": 0.2},
            {"home_win": 0, "probability_home_win": 0.5},
            {"home_win": 1, "probability_home_win": 1.0},
        ]
        bins = calibration_bins(rows, [0.0, 0.5, 1.0])
        self.assertEqual(sum(entry["row_count"] for entry in bins), len(rows))

    def test_accuracy_uses_a_one_half_decision_threshold(self) -> None:
        rows = [
            {"home_win": 1, "probability_home_win": 0.75},
            {"home_win": 0, "probability_home_win": 0.25},
        ]
        self.assertEqual(score_eligible_rows(rows, synthetic_contract())["accuracy"], 1.0)


class OfficialStatusTests(unittest.TestCase):
    def test_a_final_token_is_recognized(self) -> None:
        self.assertEqual(classify_official_status("FINAL", synthetic_contract()), FINAL_OBSERVED)

    def test_a_cancellation_outranks_a_final_token(self) -> None:
        self.assertEqual(
            classify_official_status("Final - Canceled", synthetic_contract()), CANCELED
        )

    def test_an_empty_status_is_not_a_final(self) -> None:
        self.assertNotEqual(classify_official_status("", synthetic_contract()), FINAL_OBSERVED)

    def test_a_scoreboard_without_a_status_yields_no_final(self) -> None:
        document = '<a href="/contests/6594361/">San Jose St.</a>'
        parsed = parse_official_finals(document, synthetic_contract(), game_date="2026-08-29")
        self.assertEqual(len(parsed), 1)
        self.assertNotEqual(parsed[0]["official_status_state"], FINAL_OBSERVED)


class LiveExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = synthetic_contract()
        self.population = synthetic_population()

    def run_lane(self, capture, execution_time=BEFORE, population=None):
        return execute_week_zero(
            population or self.population,
            capture,
            self.contract,
            execution_time=execution_time,
        )

    def test_before_kickoff_the_lane_truthfully_awaits_an_official_final(self) -> None:
        gate = self.run_lane(synthetic_capture())
        self.assertEqual(gate["contest_state_counts"], {AWAITING: 1})
        self.assertEqual(gate["forecast_state_counts"], {AWAITING: 1})
        self.assertEqual(gate["metrics"]["scored_row_count"], 0)
        self.assertFalse(gate["backfill_performed"])

    def test_the_lane_is_deterministic(self) -> None:
        first = self.run_lane(synthetic_capture())
        second = self.run_lane(synthetic_capture())
        self.assertEqual(first["gate_identity"], second["gate_identity"])
        self.assertEqual(gate_identity_of(first), first["gate_identity"])

    def test_an_official_final_with_a_complete_proof_is_scored(self) -> None:
        capture = synthetic_capture(
            [
                {
                    "away_points": 17,
                    "home_points": 31,
                    "ncaa_contest_id": "6594361",
                    "official_status_state": FINAL_OBSERVED,
                    "official_status_text": "FINAL",
                }
            ]
        )
        gate = self.run_lane(capture, execution_time=AFTER)
        self.assertEqual(gate["forecast_state_counts"], {SCORED: 1})
        self.assertEqual(gate["metrics"]["scored_row_count"], 1)
        self.assertAlmostEqual(gate["metrics"]["brier_score"], (0.75 - 1) ** 2)
        self.assertEqual(gate["metrics"]["accuracy"], 1.0)

    def test_a_final_without_a_complete_proof_is_never_scored(self) -> None:
        population = copy.deepcopy(self.population)
        population["audit_gate"]["row_verdicts"][0]["verdict"] = (
            "FAIL_CLOSED_INSUFFICIENT_TEMPORAL_PROOF"
        )
        capture = synthetic_capture(
            [
                {
                    "away_points": 17,
                    "home_points": 31,
                    "ncaa_contest_id": "6594361",
                    "official_status_state": FINAL_OBSERVED,
                    "official_status_text": "FINAL",
                }
            ]
        )
        gate = self.run_lane(capture, execution_time=AFTER, population=population)
        self.assertEqual(gate["forecast_state_counts"], {AWAITING: 1})
        self.assertEqual(gate["metrics"]["scored_row_count"], 0)

    def test_a_canceled_contest_is_never_scored(self) -> None:
        capture = synthetic_capture(
            [
                {
                    "away_points": None,
                    "home_points": None,
                    "ncaa_contest_id": "6594361",
                    "official_status_state": CANCELED,
                    "official_status_text": "Canceled",
                }
            ]
        )
        gate = self.run_lane(capture, execution_time=AFTER)
        self.assertEqual(gate["contest_state_counts"], {CANCELED: 1})
        self.assertEqual(gate["metrics"]["scored_row_count"], 0)

    def test_a_tie_cannot_resolve_a_home_win_label(self) -> None:
        capture = synthetic_capture(
            [
                {
                    "away_points": 24,
                    "home_points": 24,
                    "ncaa_contest_id": "6594361",
                    "official_status_state": FINAL_OBSERVED,
                    "official_status_text": "FINAL",
                }
            ]
        )
        gate = self.run_lane(capture, execution_time=AFTER)
        self.assertEqual(gate["metrics"]["scored_row_count"], 0)

    def test_an_elapsed_kickoff_without_a_frozen_forecast_is_a_missed_cutoff(self) -> None:
        population = copy.deepcopy(self.population)
        population["forecast_rows"] = []
        gate = self.run_lane(synthetic_capture(), execution_time=AFTER, population=population)
        self.assertEqual(gate["contest_state_counts"], {MISSED_CUTOFF: 1})
        self.assertEqual(gate["forecast_state_counts"], {})

    def test_the_lane_never_emits_a_probability_for_a_missed_cutoff_contest(self) -> None:
        population = copy.deepcopy(self.population)
        population["forecast_rows"] = []
        gate = self.run_lane(synthetic_capture(), execution_time=AFTER, population=population)
        self.assertEqual(gate["forecast_rows"], [])
        self.assertFalse(gate["backfill_performed"])

    def test_a_refreshed_clock_change_is_reported_rather_than_silently_absorbed(self) -> None:
        capture = synthetic_capture()
        capture["refreshed_contests"][0]["source_published_clock_text"] = "07:00 PM"
        gate = self.run_lane(capture)
        self.assertFalse(gate["contest_rows"][0]["refreshed_clock_matches_frozen_snapshot"])

    def test_transitions_are_recorded_for_every_entity(self) -> None:
        gate = self.run_lane(synthetic_capture())
        kinds = {row["entity_kind"] for row in gate["append_only_transitions"]}
        self.assertEqual(kinds, {"CONTEST", "FORECAST"})
        self.assertEqual(len(gate["append_only_transitions"]), 2)

    def test_a_forged_scored_state_is_rejected_by_the_guard(self) -> None:
        gate = self.run_lane(synthetic_capture())
        forged = copy.deepcopy(gate)
        forged["forecast_rows"][0]["forecast_state"] = SCORED
        forged["forecast_rows"][0]["temporal_audit_verdict"] = "FAIL_CLOSED_INSUFFICIENT_TEMPORAL_PROOF"
        with self.assertRaises(LiveExecutionViolation):
            assert_no_scored_row_without_a_complete_proof(forged)

    def test_a_kickoff_moved_earlier_than_issuance_makes_the_contest_a_missed_cutoff(self) -> None:
        population = copy.deepcopy(self.population)
        population["snapshot_records"][0]["kickoff_utc_conservative_lower_bound"] = (
            "2026-08-28T12:00:00Z"
        )
        gate = self.run_lane(synthetic_capture(), execution_time=BEFORE, population=population)
        self.assertEqual(gate["contest_rows"][0]["timing_state"], "KICKOFF_BOUND_HAS_ELAPSED")


class CommittedLiveExecutionGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data_root = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
        if not self.data_root:
            self.skipTest("AGGIE_ANALYTICS_DATA_ROOT is not mounted")

    def test_the_committed_gate_reproduces_from_the_captured_refresh(self) -> None:
        summary = validate_artifact(REPO_ROOT, Path(self.data_root))
        self.assertEqual(summary["result"], "PASS_WEEK_ZERO_2026_LIVE_SHADOW_EXECUTION")

    def test_the_committed_lane_scored_nothing_without_an_official_final(self) -> None:
        summary = validate_artifact(REPO_ROOT, Path(self.data_root))
        self.assertEqual(summary["metrics"]["scored_row_count"], 0)
        self.assertEqual(summary["forecast_state_counts"].get(SCORED, 0), 0)

    def test_the_contract_is_bound_to_this_issue(self) -> None:
        self.assertEqual(load_contract(REPO_ROOT)["jira_key"], "BAT-665")

    def test_the_validator_refuses_a_repository_without_the_gate(self) -> None:
        with self.assertRaises(LiveExecutionViolation):
            validate_artifact(Path(self.data_root), Path(self.data_root))

    def test_the_execution_time_precedes_every_week_zero_kickoff_bound(self) -> None:
        summary = validate_artifact(REPO_ROOT, Path(self.data_root))
        self.assertNotIn(MISSED_CUTOFF, summary["contest_state_counts"])


if __name__ == "__main__":
    unittest.main()

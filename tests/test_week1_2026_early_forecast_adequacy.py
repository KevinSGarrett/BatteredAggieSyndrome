"""Fail-closed tests for the EARLY_WEEK1 forecast adequacy snapshot."""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

try:
    from aggie_analytics.data import week1_2026_early_forecast_adequacy as E
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by core-only CI
    raise unittest.SkipTest(
        "the early forecast suite requires the optional modeling dependencies"
    ) from exc

REPO_ROOT = Path(__file__).resolve().parents[1]


def data_root() -> Path | None:
    value = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
    return Path(value) if value else None


class ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = E.load_contract(REPO_ROOT)

    def test_exactly_five_candidates(self) -> None:
        self.assertEqual(
            self.contract["candidates"],
            [
                "national_base_rate",
                "prior_only",
                "national_elo",
                "national_logistic_l2",
                "national_margin_ridge",
            ],
        )

    def test_tamu_checkpoints_cannot_execute_here(self) -> None:
        checkpoint = self.contract["checkpoint"]
        self.assertFalse(checkpoint["tamu_t_minus_24h_may_execute_in_this_unit"])
        self.assertFalse(checkpoint["tamu_t_minus_90m_may_execute_in_this_unit"])
        self.assertFalse(checkpoint["backfill_allowed"])

    def test_a_sixth_candidate_is_refused(self) -> None:
        relaxed = json.loads(json.dumps(self.contract))
        relaxed["candidates"].append("market_model")
        with self.assertRaises(E.EarlyForecastViolation):
            E.load_contract_mapping(relaxed)

    def test_partial_input_cannot_emit(self) -> None:
        relaxed = json.loads(json.dumps(self.contract))
        relaxed["adequacy_rule"]["partial_model_input_may_emit_a_forecast"] = True
        with self.assertRaises(E.EarlyForecastViolation):
            E.load_contract_mapping(relaxed)

    def test_custom_correction_is_forbidden(self) -> None:
        relaxed = json.loads(json.dumps(self.contract))
        relaxed["focus_contest"]["custom_correction_applied"] = True
        with self.assertRaises(E.EarlyForecastViolation):
            E.load_contract_mapping(relaxed)


class MaterializedArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        gate_path = REPO_ROOT / E.GATE_RELATIVE
        if not gate_path.is_file():
            raise unittest.SkipTest("early forecast gate is not materialized")
        self.gate = E.read_json(gate_path)
        self.root = data_root()

    def test_gate_identity_recomputes(self) -> None:
        self.assertEqual(E.compute_gate_identity(self.gate), self.gate["gate_identity"])

    def test_invariants_hold(self) -> None:
        E.enforce_invariants(self.gate)

    def test_pair_coherence_holds(self) -> None:
        self.assertTrue(self.gate["pair_coherence"]["pair_coherence_holds"])
        self.assertEqual(self.gate["pair_coherence"]["direction_disagreement_count"], 0)

    def test_checkpoints_remain_open(self) -> None:
        self.assertEqual(self.gate["checkpoints"]["t_minus_24h_state"], "OPEN")
        self.assertEqual(self.gate["checkpoints"]["t_minus_90m_state"], "OPEN")
        self.assertFalse(self.gate["checkpoints"]["executed_early"])
        self.assertFalse(self.gate["checkpoints"]["week1_outcome_access"])

    def test_no_recommendation_or_promotion(self) -> None:
        self.assertIsNone(self.gate["summary"]["recommended_candidate"])
        self.assertIsNone(self.gate["summary"]["promoted_candidate"])
        self.assertFalse(self.gate["summary"]["base_rate_presented_as_recommended"])

    def test_focus_contest_has_no_hardcoding(self) -> None:
        report = self.gate["focus_contest_report"]
        self.assertEqual(report["hardcoded_participant_identities"], [])
        self.assertFalse(report["custom_correction_applied"])
        self.assertFalse(report["tamu_specific_adjustment_applied"])
        self.assertFalse(report["outcome_read"])

    def test_historical_predecessors_remain_immutable(self) -> None:
        comparison = self.gate["historical_predecessor_comparison"]
        self.assertEqual(comparison["immutable_base_rate_probability"], 0.5)
        self.assertAlmostEqual(comparison["immutable_elo_probability"], 0.68188773)
        self.assertFalse(comparison["may_be_relabelled_as_current"])
        self.assertFalse(comparison["may_be_presented_as_recommended"])

    def test_independent_validation_passes(self) -> None:
        if self.root is None:
            raise unittest.SkipTest("AGGIE_ANALYTICS_DATA_ROOT is not mounted")
        report = E.validate_artifact(repo_root=REPO_ROOT, data_root=self.root)
        self.assertEqual(report["result"], "PASS")

    def test_every_contest_candidate_row_exists_exactly_once(self) -> None:
        if self.root is None:
            raise unittest.SkipTest("AGGIE_ANALYTICS_DATA_ROOT is not mounted")
        manifest = E.read_json(self.root / self.gate["manifest"]["relative_path"])
        entry = next(
            item
            for item in manifest["payloads"]
            if item["name"] == E.FORECAST_PAYLOAD_NAME
        )
        rows = [
            json.loads(line)
            for line in (self.root / entry["relative_path"])
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        self.assertEqual(len(rows), 455)
        seen: set[tuple[str, str]] = set()
        for row in rows:
            key = (row["contest_identity"], row["candidate_id"])
            self.assertNotIn(key, seen)
            seen.add(key)
            self.assertIn(row["row_state"], E.load_contract(REPO_ROOT)["row_states"])
            if row["row_state"] == E.FORECAST_FROZEN:
                self.assertIsNotNone(row["probability_home"])
                self.assertAlmostEqual(
                    float(row["probability_home"]) + float(row["probability_away"]),
                    1.0,
                    places=9,
                )
            else:
                self.assertIsNone(row["probability_home"])


if __name__ == "__main__":
    unittest.main()

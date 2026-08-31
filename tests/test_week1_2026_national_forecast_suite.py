"""Fail-closed tests for the Cycle #24 national forecast-suite binding."""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

try:
    from aggie_analytics.data import week1_2026_national_forecast_suite as S
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by core-only CI
    raise unittest.SkipTest(
        "the national forecast suite requires the optional modeling dependencies"
    ) from exc

REPO_ROOT = Path(__file__).resolve().parents[1]


def data_root() -> Path | None:
    value = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
    return Path(value) if value else None


class ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = S.load_contract(REPO_ROOT)

    def test_contract_identity_and_lane(self) -> None:
        self.assertEqual(self.contract["contract_id"], S.CONTRACT_ID)
        self.assertEqual(self.contract["lane"], S.LANE)
        self.assertEqual(self.contract["protected_lane"], S.PROTECTED_LANE)
        self.assertEqual(self.contract["jira_key"], S.JIRA_KEY)

    def test_exactly_five_candidates_are_declared(self) -> None:
        self.assertEqual(
            [item["candidate_id"] for item in self.contract["candidates"]],
            [
                "national_base_rate",
                "prior_only",
                "national_elo",
                "national_logistic_l2",
                "national_margin_ridge",
            ],
        )

    def test_a_sixth_candidate_is_refused(self) -> None:
        relaxed = json.loads(json.dumps(self.contract))
        relaxed["candidates"].append(
            dict(relaxed["candidates"][0], candidate_id="market_model")
        )
        with self.assertRaises(S.ForecastSuiteViolation):
            S.load_contract_mapping(relaxed)

    def test_only_the_ridge_family_may_carry_a_margin_interval(self) -> None:
        self.assertEqual(
            self.contract["uncertainty"]["margin_interval_allowed_candidates"],
            ["national_margin_ridge"],
        )
        relaxed = json.loads(json.dumps(self.contract))
        relaxed["uncertainty"]["margin_interval_allowed_candidates"].append(
            "national_elo"
        )
        with self.assertRaises(S.ForecastSuiteViolation):
            S.load_contract_mapping(relaxed)

    def test_a_declared_probability_interval_is_refused(self) -> None:
        relaxed = json.loads(json.dumps(self.contract))
        relaxed["uncertainty"]["probability_interval_established"] = True
        with self.assertRaises(S.ForecastSuiteViolation):
            S.load_contract_mapping(relaxed)

    def test_fabricated_feature_substitution_stays_forbidden(self) -> None:
        relaxed = json.loads(json.dumps(self.contract))
        relaxed["week1_feature_construction"][
            "forbid_training_mean_substitution_without_a_learned_indicator"
        ] = False
        with self.assertRaises(S.ForecastSuiteViolation):
            S.load_contract_mapping(relaxed)

    def test_week_zero_and_week1_fitting_stay_forbidden(self) -> None:
        for key in ("fitted_or_selected_on_week_zero", "fitted_or_selected_on_week1"):
            relaxed = json.loads(json.dumps(self.contract))
            relaxed["development_evidence"][key] = True
            with self.assertRaises(S.ForecastSuiteViolation):
                S.load_contract_mapping(relaxed)

    def test_weather_and_coordinates_stay_out_of_model_input(self) -> None:
        construction = self.contract["week1_feature_construction"]
        self.assertFalse(construction["weather_admitted_as_model_input"])
        self.assertFalse(construction["venue_coordinates_admitted_as_model_input"])


class MaterializedArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = data_root()
        gate_path = REPO_ROOT / S.GATE_RELATIVE
        if not gate_path.is_file():
            raise unittest.SkipTest("forecast suite gate is not materialized")
        self.gate = S.read_json(gate_path)

    def test_gate_identity_recomputes(self) -> None:
        self.assertEqual(S.compute_gate_identity(self.gate), self.gate["gate_identity"])

    def test_gate_invariants_hold(self) -> None:
        S.enforce_invariants(self.gate)

    def test_the_binding_emits_no_forecast_and_recommends_nothing(self) -> None:
        self.assertFalse(self.gate["summary"]["forecast_emitted"])
        self.assertIsNone(self.gate["summary"]["recommended_candidate"])
        for row in self.gate["candidate_bindings"]:
            self.assertFalse(row["recommended"])
            self.assertFalse(row["promoted"])

    def test_hyperparameters_match_the_frozen_candidate_gate(self) -> None:
        frozen = {
            item["candidate_id"]: item
            for item in S.read_json(
                REPO_ROOT
                / "artifacts/experimentation/national_expectation_baselines_and_peers_gate.json"
            )["candidates"]
        }
        for row in self.gate["candidate_bindings"]:
            self.assertEqual(
                row["hyperparameters"], frozen[row["candidate_id"]]["hyperparameters"]
            )
            self.assertEqual(row["family"], frozen[row["candidate_id"]]["family"])
            self.assertEqual(
                row["feature_scope"], frozen[row["candidate_id"]]["feature_scope"]
            )

    def test_only_the_ridge_family_claims_margin_support(self) -> None:
        supported = [
            row["candidate_id"]
            for row in self.gate["candidate_bindings"]
            if row["margin_support"] == "SUPPORTED_BY_MODEL_FAMILY"
        ]
        self.assertEqual(supported, ["national_margin_ridge"])
        for row in self.gate["candidate_bindings"]:
            if row["candidate_id"] != "national_margin_ridge":
                self.assertIsNone(row["development_margin_rmse"])

    def test_the_control_is_never_recommended(self) -> None:
        control = next(
            row
            for row in self.gate["candidate_bindings"]
            if row["candidate_id"] == "national_base_rate"
        )
        self.assertTrue(control["never_recommended"])
        self.assertEqual(control["development_brier"], 0.25)

    def test_training_evidence_never_reaches_a_protected_season(self) -> None:
        self.assertLessEqual(self.gate["deployment_fit"]["training_season_max"], 2023)

    def test_partial_input_cannot_emit_a_forecast(self) -> None:
        self.assertFalse(
            self.gate["adequacy"]["partial_model_input_may_emit_a_forecast"]
        )

    def test_no_feature_is_neither_admitted_nor_indicator_covered(self) -> None:
        self.assertEqual(
            self.gate["summary"]["features_neither_admitted_nor_indicator_covered"], []
        )
        self.assertEqual(self.gate["summary"]["fabricated_numeric_value_count"], 0)

    def test_independent_validation_passes(self) -> None:
        if self.root is None:
            raise unittest.SkipTest("AGGIE_ANALYTICS_DATA_ROOT is not mounted")
        report = S.validate_artifact(repo_root=REPO_ROOT, data_root=self.root)
        self.assertEqual(report["result"], "PASS")

    def test_every_adequacy_row_carries_exactly_one_state(self) -> None:
        if self.root is None:
            raise unittest.SkipTest("AGGIE_ANALYTICS_DATA_ROOT is not mounted")
        rows = S.payload_rows(self.root, self.gate, S.ADEQUACY_PAYLOAD_NAME)
        self.assertEqual(len(rows), 910)
        allowed = {S.READY, S.ABSTAIN_FEATURES, S.ABSTAIN_ENTITY, S.QUARANTINED}
        seen: set[tuple[str, str, str]] = set()
        for row in rows:
            self.assertIn(row["readiness_state"], allowed)
            key = (row["candidate_id"], row["contest_identity"], row["source_team_id"])
            self.assertNotIn(key, seen)
            seen.add(key)
            if row["readiness_state"] == S.READY:
                self.assertEqual(row["abstention_reasons"], [])
            else:
                self.assertTrue(row["abstention_reasons"])

    def test_unsupported_entities_never_reach_a_ready_state(self) -> None:
        if self.root is None:
            raise unittest.SkipTest("AGGIE_ANALYTICS_DATA_ROOT is not mounted")
        features = S.payload_rows(self.root, self.gate, S.FEATURE_PAYLOAD_NAME)
        unsupported = {
            row["source_team_id"]
            for row in features
            if row["prior_disposition"] == "ABSTAIN_UNSUPPORTED_ENTITY"
        }
        self.assertEqual(len(unsupported), 8)
        rows = S.payload_rows(self.root, self.gate, S.ADEQUACY_PAYLOAD_NAME)
        for row in rows:
            if row["source_team_id"] in unsupported:
                self.assertEqual(row["readiness_state"], S.ABSTAIN_ENTITY)

    def test_fitted_parameters_are_persisted_for_every_fitted_family(self) -> None:
        if self.root is None:
            raise unittest.SkipTest("AGGIE_ANALYTICS_DATA_ROOT is not mounted")
        rows = S.payload_rows(self.root, self.gate, S.PARAMETER_PAYLOAD_NAME)
        ids = {row["parameter_set_id"] for row in rows}
        self.assertEqual(
            ids,
            {
                "WEEK1_2026_DEPLOYMENT_DESIGN",
                "NATIONAL_LOGISTIC_L2_BETA",
                "PRIOR_ONLY_BETA",
                "NATIONAL_MARGIN_RIDGE_BETA",
            },
        )


if __name__ == "__main__":
    unittest.main()

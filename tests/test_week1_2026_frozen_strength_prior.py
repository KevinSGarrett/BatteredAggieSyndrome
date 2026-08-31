"""Fail-closed tests for the Cycle #24 frozen 2026 opening strength priors."""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from aggie_analytics.data import week1_2026_frozen_strength_prior as P

REPO_ROOT = Path(__file__).resolve().parents[1]


def data_root() -> Path | None:
    value = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
    return Path(value) if value else None


class ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = P.load_contract(REPO_ROOT)

    def test_contract_identity_and_lane(self) -> None:
        self.assertEqual(self.contract["contract_id"], P.CONTRACT_ID)
        self.assertEqual(self.contract["lane"], P.LANE)
        self.assertEqual(self.contract["protected_lane"], P.PROTECTED_LANE)
        self.assertEqual(self.contract["jira_key"], P.JIRA_KEY)

    def test_protected_seasons_are_excluded_from_the_evidence_window(self) -> None:
        window = self.contract["evidence_window"]
        self.assertEqual(int(window["allowed_season_max"]), 2023)
        self.assertEqual(sorted(window["excluded_protected_seasons"]), [2024, 2025])

    def test_forbidden_inputs_cover_the_declared_leakage_surface(self) -> None:
        forbidden = self.contract["forbidden"]
        for key in (
            "protected_season_evidence",
            "target_game_outcome",
            "future_week1_outcome",
            "market_lines",
            "manual_tamu_boost",
            "post_hoc_parameter_selection_on_week_zero",
            "name_only_joins",
            "defaults_presented_as_team_evidence",
        ):
            self.assertTrue(forbidden[key], key)

    def test_week_zero_update_rule_is_predeclared_and_batch_gated(self) -> None:
        rule = self.contract["week_zero_update_rule"]
        self.assertTrue(rule["predeclared"])
        self.assertTrue(rule["requires_official_final_capture_timestamp"])
        self.assertEqual(
            rule["batch_definition"], "THE_EIGHT_OFFICIAL_2026_WEEK_ZERO_CONTESTS"
        )
        self.assertFalse(rule["may_change_hyperparameters"])
        self.assertFalse(rule["may_change_candidate_selection"])

    def test_relaxing_the_evidence_window_is_refused(self) -> None:
        relaxed = json.loads(json.dumps(self.contract))
        relaxed["evidence_window"]["allowed_season_max"] = 2025
        with self.assertRaises(P.FrozenPriorViolation):
            P.load_contract_mapping(relaxed)

    def test_relaxing_the_week_zero_capture_gate_is_refused(self) -> None:
        relaxed = json.loads(json.dumps(self.contract))
        relaxed["week_zero_update_rule"][
            "requires_official_final_capture_timestamp"
        ] = False
        with self.assertRaises(P.FrozenPriorViolation):
            P.load_contract_mapping(relaxed)

    def test_enabling_a_hierarchical_fallback_is_refused(self) -> None:
        relaxed = json.loads(json.dumps(self.contract))
        relaxed["support"]["hierarchical_fallback_enabled"] = True
        with self.assertRaises(P.FrozenPriorViolation):
            P.load_contract_mapping(relaxed)


class ReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hyperparameters = P.load_contract(REPO_ROOT)["elo"]

    def _contest(self, ordinal: int, home: str, away: str, home_win: int) -> dict:
        return {
            "canonical_game_id": f"G{ordinal}",
            "chronological_ordinal": ordinal,
            "season": 2020,
            "home_team": home,
            "away_team": away,
            "home_win": home_win,
            "neutral_site": False,
            "tie": False,
            "kickoff_utc": f"2020-09-0{ordinal}T00:00:00Z",
        }

    def test_replay_is_invariant_to_input_row_order(self) -> None:
        contests = [
            self._contest(1, "A", "B", 1),
            self._contest(2, "B", "C", 0),
            self._contest(3, "C", "A", 1),
        ]
        forward = P.replay_elo(contests, hyperparameters=self.hyperparameters)
        backward = P.replay_elo(
            list(reversed(contests)), hyperparameters=self.hyperparameters
        )
        for team, state in forward.items():
            self.assertAlmostEqual(state["rating"], backward[team]["rating"], places=9)

    def test_a_contest_never_updates_the_state_it_predicted_from(self) -> None:
        contests = [self._contest(1, "A", "B", 1)]
        state = P.replay_elo(contests, hyperparameters=self.hyperparameters)
        initial = float(self.hyperparameters["initial_rating"])
        self.assertGreater(state["A"]["rating"], initial)
        self.assertLess(state["B"]["rating"], initial)
        self.assertAlmostEqual(
            state["A"]["rating"] + state["B"]["rating"], 2 * initial, places=6
        )

    def test_between_season_regression_pulls_toward_the_initial_rating(self) -> None:
        first = self._contest(1, "A", "B", 1)
        later = dict(self._contest(2, "A", "C", 1), season=2021)
        one_season = P.replay_elo([first], hyperparameters=self.hyperparameters)
        two_seasons = P.replay_elo([first, later], hyperparameters=self.hyperparameters)
        regression = float(self.hyperparameters["between_season_regression"])
        if regression > 0:
            self.assertNotAlmostEqual(
                one_season["A"]["rating"], two_seasons["A"]["rating"], places=6
            )


class MaterializedArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = data_root()
        gate_path = REPO_ROOT / P.GATE_RELATIVE
        if not gate_path.is_file():
            raise unittest.SkipTest("prior gate is not materialized")
        self.gate = P.read_json(gate_path)

    def test_gate_identity_recomputes(self) -> None:
        self.assertEqual(P.compute_gate_identity(self.gate), self.gate["gate_identity"])

    def test_gate_invariants_hold(self) -> None:
        P.enforce_invariants(self.gate)

    def test_no_forecast_is_emitted_by_the_prior_surface(self) -> None:
        self.assertFalse(self.gate["summary"]["forecast_emitted"])

    def test_the_prior_excludes_protected_seasons(self) -> None:
        self.assertEqual(self.gate["summary"]["protected_season_rows"], 0)
        self.assertEqual(self.gate["summary"]["latest_allowed_season"], 2023)

    def test_no_default_rating_is_presented_as_team_evidence(self) -> None:
        self.assertEqual(
            self.gate["summary"]["default_rating_presented_as_evidence_count"], 0
        )

    def test_the_focus_contest_carries_no_team_specific_adjustment(self) -> None:
        report = self.gate["focus_contest_report"]
        self.assertFalse(report["tamu_specific_adjustment_applied"])
        self.assertFalse(report["custom_correction_applied"])
        self.assertEqual(len(report["focus_contest_participants"]), 2)

    def test_every_invariance_proof_holds(self) -> None:
        proofs = {
            item["proof"]: item["holds"] for item in self.gate["invariance_proofs"]
        }
        for name in (
            "ROW_ORDER_INVARIANCE",
            "FUTURE_APPEND_INVARIANCE",
            "SAME_GAME_EXCLUSION",
            "BATCH_UPDATE_CORRECTNESS",
            "BYTE_STABLE_RECONSTRUCTION",
        ):
            self.assertTrue(proofs[name], name)

    def test_independent_validation_passes(self) -> None:
        if self.root is None:
            raise unittest.SkipTest("AGGIE_ANALYTICS_DATA_ROOT is not mounted")
        report = P.validate_artifact(repo_root=REPO_ROOT, data_root=self.root)
        self.assertEqual(report["result"], "PASS")

    def test_admitted_and_abstaining_rows_stay_mutually_exclusive(self) -> None:
        if self.root is None:
            raise unittest.SkipTest("AGGIE_ANALYTICS_DATA_ROOT is not mounted")
        rows = P._payload_rows(self.root, self.gate, P.PRIOR_PAYLOAD_NAME)
        for row in rows:
            if row["prior_admitted"]:
                self.assertIsNotNone(row["opening_rating"])
                self.assertNotEqual(row["prior_disposition"][:7], "ABSTAIN")
            else:
                self.assertIsNone(row["opening_rating"])
                self.assertEqual(row["prior_disposition"][:7], "ABSTAIN")

    def test_unresolved_entities_abstain(self) -> None:
        if self.root is None:
            raise unittest.SkipTest("AGGIE_ANALYTICS_DATA_ROOT is not mounted")
        rows = P._payload_rows(self.root, self.gate, P.PRIOR_PAYLOAD_NAME)
        unresolved = [
            row
            for row in rows
            if row["prior_disposition"] == "ABSTAIN_UNSUPPORTED_ENTITY"
        ]
        self.assertEqual(len(unresolved), 8)
        for row in unresolved:
            self.assertIsNone(row["opening_rating"])

    def test_week_zero_updates_never_change_the_model_definition(self) -> None:
        if self.root is None:
            raise unittest.SkipTest("AGGIE_ANALYTICS_DATA_ROOT is not mounted")
        rows = P._payload_rows(self.root, self.gate, P.UPDATE_PAYLOAD_NAME)
        self.assertTrue(rows)
        for row in rows:
            self.assertFalse(row["hyperparameters_changed"])
            self.assertFalse(row["candidate_selection_changed"])
            if row["applied"]:
                self.assertTrue(row["official_final_capture_retrieved_at_utc"])
            else:
                self.assertTrue(row["not_applied_reason"])


if __name__ == "__main__":
    unittest.main()

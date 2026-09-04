"""Isolated Cycle #27 active-path dependency-trace regressions."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from aggie_analytics.data.cycle27_active_path_dependency_trace import (  # noqa: E402
    BASELINES_RELATIVE,
    C26_DATASET_IDENTITY,
    C26_GATE_IDENTITY,
    CURRENT_CONTEST_HELPER,
    SUCCESSOR_RELATIVE,
    build_trace,
    called_names,
    current_contest_helper_consumed,
    mapping_key_reads,
    parse_module,
    trace_forecast_successor,
)


class ForecastSuccessorConsumptionTests(unittest.TestCase):
    def test_materializer_does_not_call_current_contest_helper(self) -> None:
        tree = parse_module(REPO / SUCCESSOR_RELATIVE)
        self.assertFalse(current_contest_helper_consumed(tree))
        self.assertNotIn(CURRENT_CONTEST_HELPER, called_names(tree))

    def test_ridge_rewrite_reads_margin_not_feature_values(self) -> None:
        tree = parse_module(REPO / SUCCESSOR_RELATIVE)
        ridge = None
        for node in tree.body:
            if getattr(node, "name", None) == "_rewrite_ridge_row":
                ridge = node
        self.assertIsNotNone(ridge)
        keys = mapping_key_reads(ridge, ("row",))
        self.assertIn("expected_margin_home", keys)
        self.assertNotIn("feature_values", keys)
        self.assertNotIn("opening_rating", keys)

    def test_live_trace_records_c24_mutation_not_helper_consumption(self) -> None:
        successor = trace_forecast_successor(REPO)
        self.assertFalse(successor["current_contest_binding_helper_consumed"])
        self.assertEqual(successor["current_contest_execution"], "C24_ROWS_MUTATED")
        self.assertTrue(successor["copies_cycle24_row_then_mutates_probability_interval"])
        self.assertFalse(successor["feature_values_consumed_for_prediction"])
        self.assertFalse(successor["rebuilds_target_features"])
        self.assertFalse(successor["refits_parameters"])


class IsolatedTraceFixtureTests(unittest.TestCase):
    def test_trace_from_copied_modules_in_temp_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest_succ = root / SUCCESSOR_RELATIVE
            dest_base = root / BASELINES_RELATIVE
            dest_succ.parent.mkdir(parents=True, exist_ok=True)
            dest_base.parent.mkdir(parents=True, exist_ok=True)
            dest_succ.write_bytes((REPO / SUCCESSOR_RELATIVE).read_bytes())
            dest_base.write_bytes((REPO / BASELINES_RELATIVE).read_bytes())
            trace = build_trace(repo_root=root, issued_at_utc="2026-09-04T16:45:00Z")
        self.assertEqual(trace["result"], "PASS_CYCLE27_ACTIVE_PATH_DEPENDENCY_TRACE")
        self.assertEqual(
            trace["current_contest_binding"]["live_execution"],
            "CYCLE24_FORECAST_ROWS_COPIED_AND_MUTATED",
        )
        self.assertFalse(trace["current_contest_binding"]["consumed_by_week1_materializer"])
        stages = {item["stage"]: item for item in trace["stages"]}
        self.assertEqual(stages["current_target_features"]["actually_consumed"], [])
        self.assertFalse(stages["current_target_features"]["current_contest_binding_helper_consumed"])
        elo = trace["national_expectation_baselines"]["candidates"]["national_elo"]
        self.assertFalse(elo["opening_ratings_consumed"])
        self.assertEqual(elo["initial_rating"], 1500.0)
        self.assertFalse(
            trace["national_expectation_baselines"]["new_cold_start_average_invented_for_coverage"]
        )
        self.assertEqual(trace["c26_gate_identity_preserved"], C26_GATE_IDENTITY)
        self.assertEqual(trace["c26_dataset_identity_preserved"], C26_DATASET_IDENTITY)
        self.assertIn("expected_margin_home from Cycle #24 predecessor row", stages["executable_prediction"]["actually_consumed"])

    def test_helper_call_in_fixture_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / SUCCESSOR_RELATIVE
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "from aggie_analytics.data.week1_2026_current_contest_binding_successor "
                "import build_current_contest_row\n"
                "def materialize():\n"
                "    return build_current_contest_row(team_key='x', contests=[], "
                "historical_priors={}, current_conference=None, current_subdivision=None, "
                "current_rank=None, rank_admitted=False, "
                "official_2026_finals_known_before_cutoff=None, trust_gate_open=False)\n",
                encoding="utf-8",
            )
            tree = parse_module(path)
            self.assertTrue(current_contest_helper_consumed(tree))


class FrozenC26IdentityTests(unittest.TestCase):
    def test_committed_c26_gate_identities_unchanged_by_trace_source(self) -> None:
        gate = json.loads(
            (
                REPO
                / "artifacts/forecast/week1_2026_game_grain_national_forecast_successor_gate.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(gate["gate_identity"], C26_GATE_IDENTITY)
        self.assertEqual(gate["dataset_identity"], C26_DATASET_IDENTITY)


if __name__ == "__main__":
    unittest.main()

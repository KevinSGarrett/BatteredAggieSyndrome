from __future__ import annotations

import copy
import json
import os
import sys
import unittest
from pathlib import Path

try:
    import numpy as np
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by core-only CI
    raise unittest.SkipTest(
        "national baseline tests require the optional modeling dependencies"
    ) from exc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aggie_analytics.data.national_foundation_reconciliation import (  # noqa: E402
    binding_identity,
)
from aggie_analytics.modeling.national_expectation_baselines import (  # noqa: E402
    CONTRACT_ID,
    FEATURE_SCOPES,
    GATE_RELATIVE,
    PASS_RESULT,
    TAMU_TEAM_ID,
    bootstrap_interval,
    build_design,
    build_peer_cohort,
    build_residual_test,
    calibration_bins,
    calibration_fit,
    compute_gate_identity,
    conference_levels,
    elo_probability,
    elo_ratings,
    evaluate_candidates,
    fit_logistic_l2,
    fit_ridge,
    load_contract,
    rebuild_expected,
    score_predictions,
    validate_artifact,
)

CONTRACT = load_contract(ROOT)


def _row(game: str, team: str, opponent: str, ordinal: int, **overrides):
    row = {
        "canonical_game_id": game,
        "canonical_team_id": team,
        "opponent_canonical_team_id": opponent,
        "season": 2015,
        "week": 1,
        "season_type": "regular",
        "chronological_ordinal": ordinal,
        "partition": "TRAINING",
        "site": "HOME",
        "favorite_state": "EVEN_OR_UNKNOWN",
        "ranking_state": "NO_POLL_SOURCE",
        "data_coverage_class": "COVERAGE_1_OF_4",
        "is_home": True,
        "is_neutral_site": False,
        "prior_games_played": 4,
        "prior_win_rate": 0.5,
        "prior_win_rate_missing": False,
        "prior_points_for_mean": 24.0,
        "prior_points_for_mean_missing": False,
        "prior_points_against_mean": 21.0,
        "prior_points_against_mean_missing": False,
        "prior_margin_mean": 3.0,
        "prior_margin_mean_missing": False,
        "prior_season_win_rate": 0.5,
        "prior_season_win_rate_missing": False,
        "season_to_date_games": 4,
        "season_to_date_win_rate": 0.5,
        "season_to_date_win_rate_missing": False,
        "ap_poll_rank": None,
        "ap_poll_rank_missing": True,
        "coaches_poll_rank": None,
        "coaches_poll_rank_missing": True,
        "rankings_source_available": False,
        "venue_dome": None,
        "venue_dome_missing": True,
        "venue_grass": None,
        "venue_grass_missing": True,
        "venue_elevation_m": None,
        "venue_elevation_m_missing": True,
        "venue_latitude": None,
        "venue_latitude_missing": True,
        "venue_longitude": None,
        "venue_longitude_missing": True,
        "team_conference": "SEC",
        "team_conference_missing": False,
        "team_is_fbs": True,
        "team_is_fbs_missing": False,
        "opponent_prior_games_played": 4,
        "opponent_prior_win_rate": 0.5,
        "opponent_prior_win_rate_missing": False,
        "opponent_prior_margin_mean": 0.0,
        "opponent_prior_margin_mean_missing": False,
        "opponent_prior_season_win_rate": 0.5,
        "opponent_prior_season_win_rate_missing": False,
        "opponent_ap_poll_rank": None,
        "opponent_ap_poll_rank_missing": True,
        "prior_win_rate_differential": 0.0,
        "prior_win_rate_differential_missing": False,
    }
    row.update(overrides)
    return row


def _label(game: str, team: str, ordinal: int, win: bool, margin: int, tie: bool = False):
    return {
        "canonical_game_id": game,
        "canonical_team_id": team,
        "season": 2015,
        "chronological_ordinal": ordinal,
        "partition": "TRAINING",
        "label_win": win,
        "label_tie": tie,
        "label_margin": margin,
    }


class BaselineUnitTests(unittest.TestCase):
    def test_contract_freezes_the_candidate_set_and_blocks_promotion(self) -> None:
        self.assertEqual(CONTRACT["contract_id"], CONTRACT_ID)
        self.assertTrue(CONTRACT["precommitment"]["candidate_set_frozen_before_evaluation"])
        self.assertFalse(CONTRACT["precommitment"]["champion_promotion"])
        self.assertFalse(CONTRACT["precommitment"]["boosting_neural_sequence_or_graph_models"])
        self.assertFalse(CONTRACT["authority"]["champion_or_production_promotion"])
        self.assertFalse(CONTRACT["authority"]["protected_evaluation_admission"])

    def test_every_declared_candidate_is_a_simple_family(self) -> None:
        allowed = {"UNFITTED_REFERENCE", "REGULARIZED_LOGISTIC", "ELO", "RIDGE_MARGIN"}
        families = {candidate["family"] for candidate in CONTRACT["candidates"]}
        self.assertTrue(families <= allowed)
        self.assertGreaterEqual(len(CONTRACT["candidates"]), 4)

    def test_a_contract_that_permits_post_hoc_candidates_is_rejected(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "configs").mkdir()
            tampered = copy.deepcopy(CONTRACT)
            tampered["precommitment"]["post_hoc_candidate_insertion"] = True
            (root / "configs" / "national_expectation_baselines_and_peers_contract.json").write_text(
                json.dumps(tampered), encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                load_contract(root)

    def test_a_contract_that_claims_bas_is_rejected(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "configs").mkdir()
            tampered = copy.deepcopy(CONTRACT)
            tampered["residual_test"]["claims_bas_or_aggie_excess"] = True
            (root / "configs" / "national_expectation_baselines_and_peers_contract.json").write_text(
                json.dumps(tampered), encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                load_contract(root)

    def test_the_prior_scope_never_reaches_the_ranking_or_venue_domains(self) -> None:
        numeric, boolean, use_conference = FEATURE_SCOPES["PRIOR_OUTCOME_DOMAIN_AND_SITE"]
        self.assertNotIn("ap_poll_rank", numeric)
        self.assertNotIn("venue_latitude", numeric)
        self.assertNotIn("team_is_fbs", boolean)
        self.assertFalse(use_conference)

    def test_the_design_matrix_standardizes_inside_the_fold_and_flags_missingness(self) -> None:
        rows = [
            _row("G1", "A", "B", 0, prior_win_rate=0.8),
            _row("G1", "B", "A", 0, prior_win_rate=None, prior_win_rate_missing=True),
        ]
        transforms = {"prior_win_rate": {"mean": 0.5, "stdev": 0.1, "observed": 100}}
        design, columns = build_design(
            rows,
            scope="PRIOR_OUTCOME_DOMAIN_AND_SITE",
            transforms=transforms,
            levels=[],
            indicators=("prior_win_rate_missing",),
        )
        self.assertEqual(design[0, 0], 1.0)
        self.assertAlmostEqual(design[0, 1 + columns.index("prior_win_rate")], 3.0)
        self.assertEqual(design[1, 1 + columns.index("prior_win_rate")], 0.0)
        self.assertEqual(design[1, 1 + columns.index("prior_win_rate_missing")], 1.0)

    def test_a_rare_conference_collapses_into_the_other_bucket(self) -> None:
        training = [_row("G", f"T{index}", "X", index) for index in range(60)]
        training.append(_row("H", "Z", "X", 61, team_conference="Tiny"))
        self.assertEqual(conference_levels(training), ["SEC"])

    def test_the_logistic_solver_recovers_a_known_separation(self) -> None:
        signal = np.linspace(-3.0, 3.0, 400)
        design = np.column_stack([np.ones_like(signal), signal])
        target = (signal > 0).astype(np.float64)
        beta = fit_logistic_l2(design, target, l2_lambda=1.0, iterations=25, tolerance=1e-10)
        self.assertGreater(beta[1], 1.0)
        self.assertLess(abs(beta[0]), 1.0)

    def test_the_ridge_solver_recovers_a_known_slope(self) -> None:
        signal = np.linspace(-2.0, 2.0, 500)
        design = np.column_stack([np.ones_like(signal), signal])
        target = 3.0 * signal + 1.0
        beta = fit_ridge(design, target, l2_lambda=1e-9)
        self.assertAlmostEqual(beta[0], 1.0, places=6)
        self.assertAlmostEqual(beta[1], 3.0, places=6)

    def test_the_ridge_penalty_never_shrinks_the_intercept(self) -> None:
        signal = np.zeros(50)
        design = np.column_stack([np.ones_like(signal), signal])
        beta = fit_ridge(design, np.full(50, 7.0), l2_lambda=1000.0)
        self.assertAlmostEqual(beta[0], 7.0, places=6)

    def test_elo_moves_the_winner_up_and_the_loser_down_by_the_same_amount(self) -> None:
        training = [_row("G1", "A", "B", 0), _row("G1", "B", "A", 0, is_home=False)]
        labels = {
            ("G1", "A"): _label("G1", "A", 0, True, 10),
            ("G1", "B"): _label("G1", "B", 0, False, -10),
        }
        hyper = CONTRACT["candidates"][2]["hyperparameters"]
        ratings = elo_ratings(training, labels, hyperparameters=hyper)
        self.assertGreater(ratings["A"], hyper["initial_rating"])
        self.assertLess(ratings["B"], hyper["initial_rating"])
        self.assertAlmostEqual(
            ratings["A"] - hyper["initial_rating"], hyper["initial_rating"] - ratings["B"]
        )

    def test_elo_treats_a_tie_as_a_half_outcome(self) -> None:
        training = [_row("G1", "A", "B", 0, is_neutral_site=True, is_home=False),
                    _row("G1", "B", "A", 0, is_neutral_site=True, is_home=False)]
        labels = {
            ("G1", "A"): _label("G1", "A", 0, False, 0, tie=True),
            ("G1", "B"): _label("G1", "B", 0, False, 0, tie=True),
        }
        hyper = CONTRACT["candidates"][2]["hyperparameters"]
        ratings = elo_ratings(training, labels, hyperparameters=hyper)
        self.assertAlmostEqual(ratings["A"], hyper["initial_rating"])
        self.assertAlmostEqual(ratings["B"], hyper["initial_rating"])

    def test_elo_gives_the_home_side_the_declared_advantage(self) -> None:
        hyper = CONTRACT["candidates"][2]["hyperparameters"]
        home = elo_probability(_row("G", "A", "B", 0), {}, hyperparameters=hyper)
        away = elo_probability(
            _row("G", "A", "B", 0, is_home=False), {}, hyperparameters=hyper
        )
        neutral = elo_probability(
            _row("G", "A", "B", 0, is_neutral_site=True), {}, hyperparameters=hyper
        )
        self.assertGreater(home, neutral)
        self.assertLess(away, neutral)
        self.assertAlmostEqual(neutral, 0.5)

    def test_a_perfect_forecast_scores_zero_brier(self) -> None:
        outcomes = np.array([1.0, 0.0, 1.0, 0.0])
        scored = score_predictions(
            np.array([1.0, 0.0, 1.0, 0.0]), outcomes, clip=[0.0, 1.0], bin_count=10
        )
        self.assertEqual(scored["brier"], 0.0)
        self.assertEqual(scored["accuracy"], 1.0)

    def test_an_uninformative_forecast_scores_a_quarter_brier(self) -> None:
        outcomes = np.array([1.0, 0.0, 1.0, 0.0])
        scored = score_predictions(
            np.full(4, 0.5), outcomes, clip=[0.001, 0.999], bin_count=10
        )
        self.assertEqual(scored["brier"], 0.25)
        self.assertEqual(scored["accuracy"], 0.5)

    def test_calibration_bins_partition_every_row_exactly_once(self) -> None:
        probabilities = np.linspace(0.0, 1.0, 101)
        outcomes = (probabilities > 0.5).astype(np.float64)
        bins = calibration_bins(probabilities, outcomes, bin_count=10)
        self.assertEqual(sum(entry["rows"] for entry in bins), 101)

    def test_calibration_is_unsupported_for_a_constant_forecast(self) -> None:
        fit = calibration_fit(np.full(50, 0.5), np.tile([0.0, 1.0], 25))
        self.assertFalse(fit["calibration_supported"])
        self.assertIsNone(fit["calibration_slope"])

    def test_a_well_calibrated_forecast_has_a_slope_near_one(self) -> None:
        generator = np.random.default_rng(7)
        probabilities = generator.uniform(0.05, 0.95, 20000)
        outcomes = (generator.uniform(size=20000) < probabilities).astype(np.float64)
        fit = calibration_fit(probabilities, outcomes)
        self.assertAlmostEqual(fit["calibration_slope"], 1.0, delta=0.1)

    def test_the_bootstrap_resamples_whole_games_and_is_seed_stable(self) -> None:
        values = np.array([0.1, 0.9, 0.2, 0.8])
        groups = ["G1", "G1", "G2", "G2"]
        first = bootstrap_interval(values, groups, resamples=200, seed=11)
        second = bootstrap_interval(values, groups, resamples=200, seed=11)
        self.assertEqual(first, second)
        self.assertEqual(first["bootstrap_unit"], "GAME")
        self.assertEqual(first["point_estimate"], 0.5)

    def test_the_peer_rule_declares_the_criteria_it_cannot_measure(self) -> None:
        unavailable = {
            item["criterion_id"] for item in CONTRACT["peer_cohort_rule"]["unavailable_criteria"]
        }
        self.assertIn("recruiting_or_talent_level", unavailable)
        self.assertIn("coaching_transition_frequency", unavailable)
        self.assertFalse(CONTRACT["peer_cohort_rule"]["seeded_from_famous_programs"])

    def test_the_peer_rule_rejects_a_reference_program_it_cannot_profile(self) -> None:
        contract = copy.deepcopy(CONTRACT)
        contract["peer_cohort_rule"]["reference_team"] = "SRC-002:TEAM:DOES-NOT-EXIST"
        with self.assertRaises(ValueError):
            build_peer_cohort(matrix=[], labels=[], contract=contract)

    def test_the_peer_rule_ignores_the_evaluation_season(self) -> None:
        contract = copy.deepcopy(CONTRACT)
        contract["peer_cohort_rule"]["minimum_reference_window_games"] = 1
        contract["peer_cohort_rule"]["cohort_size"] = 1
        contract["peer_cohort_rule"]["reference_team"] = "A"
        matrix = [
            _row("G1", "A", "B", 0, season=2010),
            _row("G1", "B", "A", 0, season=2010, is_home=False),
            _row("G2", "C", "D", 1, season=2023, partition="EVALUATION"),
            _row("G2", "D", "C", 1, season=2023, partition="EVALUATION", is_home=False),
        ]
        labels = [
            _label("G1", "A", 0, True, 7),
            _label("G1", "B", 0, False, -7),
            _label("G2", "C", 1, True, 7),
            _label("G2", "D", 1, False, -7),
        ]
        cohort = build_peer_cohort(matrix=matrix, labels=labels, contract=contract)
        members = {member["canonical_team_id"] for member in cohort["members"]}
        self.assertEqual(members, {"B"})
        self.assertNotIn("C", members)

    def test_the_residual_test_never_places_the_reference_in_its_own_cohort(self) -> None:
        contract = copy.deepcopy(CONTRACT)
        matrix = [
            _row("G1", TAMU_TEAM_ID, "B", 0, season=2023, partition="EVALUATION"),
            _row("G1", "B", TAMU_TEAM_ID, 0, season=2023, partition="EVALUATION", is_home=False),
        ]
        labels = [
            dict(_label("G1", TAMU_TEAM_ID, 0, True, 7), partition="EVALUATION"),
            dict(_label("G1", "B", 0, False, -7), partition="EVALUATION"),
        ]
        probabilities = {
            "prior_only": {("G1", TAMU_TEAM_ID): 0.6, ("G1", "B"): 0.4},
        }
        peer_cohort = {"members": [{"canonical_team_id": "B"}], "reference_team": TAMU_TEAM_ID}
        result = build_residual_test(
            contract=contract,
            matrix=matrix,
            labels=labels,
            probability_index=probabilities,
            peer_cohort=peer_cohort,
        )
        groups = {group["group"]: group for group in result["groups"]}
        self.assertEqual(groups["TEXAS_AM"]["rows"], 1)
        self.assertAlmostEqual(groups["TEXAS_AM"]["mean_residual"], 0.4)
        self.assertTrue(groups["TEXAS_AM"]["sample_is_too_small_for_inference"])
        self.assertFalse(result["baseline_refit_for_this_test"])
        self.assertFalse(result["claims"]["bas_or_aggie_excess"])

    def test_a_fold_that_would_train_on_its_own_evaluation_rows_is_rejected(self) -> None:
        contract = copy.deepcopy(CONTRACT)
        contract["evaluation"]["expected_evaluation_rows"] = 2
        matrix = [
            _row("G1", "A", "B", 0),
            _row("G1", "B", "A", 0, is_home=False),
            _row("G2", "A", "B", 1, partition="EVALUATION"),
            _row("G2", "B", "A", 1, partition="EVALUATION", is_home=False),
        ]
        labels = [
            _label("G1", "A", 0, True, 7),
            _label("G1", "B", 0, False, -7),
            dict(_label("G2", "A", 1, True, 3), partition="EVALUATION"),
            dict(_label("G2", "B", 1, False, -3), partition="EVALUATION"),
        ]
        folds = [
            {
                "fold_id": "FOLD-01",
                "training_max_ordinal_exclusive": 2,
                "evaluation_ordinals": [1],
                "fold_local_transforms": {},
            }
        ]
        with self.assertRaises(ValueError):
            evaluate_candidates(matrix=matrix, labels=labels, folds=folds, contract=contract)


class BaselineMountedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data_root = Path(
            os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
        )
        cls.gate_path = ROOT / GATE_RELATIVE
        if not cls.gate_path.is_file() or not (cls.data_root / "canonical").is_dir():
            raise unittest.SkipTest("the baseline gate or the data root is not mounted")
        cls.gate = json.loads(cls.gate_path.read_text(encoding="utf-8"))
        cls.expected = rebuild_expected(data_root=cls.data_root, repo_root=ROOT)

    def test_the_gate_survives_an_independent_rebuild(self) -> None:
        result = validate_artifact(
            data_root=self.data_root,
            repo_root=ROOT,
            require_rebuild=True,
            expected=self.expected,
        )
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["mode"], "INDEPENDENT_REBUILD")

    def test_the_gate_records_the_declared_development_only_result(self) -> None:
        self.assertEqual(self.gate["result"], PASS_RESULT)
        self.assertIn("NO_CHAMPION", PASS_RESULT)

    def test_the_cohort_is_the_frozen_2023_development_partition(self) -> None:
        cohort = self.gate["cohort"]
        self.assertEqual(cohort["season"], 2023)
        self.assertEqual(cohort["team_rows"], CONTRACT["evaluation"]["expected_evaluation_rows"])
        self.assertEqual(cohort["unique_games"], CONTRACT["evaluation"]["expected_evaluation_games"])
        self.assertEqual(cohort["folds"], CONTRACT["evaluation"]["expected_folds"])
        self.assertEqual(cohort["protected_seasons_excluded"], [2024, 2025])
        self.assertEqual(cohort["prospective_seasons_excluded"], [2026])

    def test_every_predeclared_candidate_was_actually_scored(self) -> None:
        declared = {candidate["candidate_id"] for candidate in CONTRACT["candidates"]}
        scored = {candidate["candidate_id"] for candidate in self.gate["candidates"]}
        self.assertEqual(declared, scored)

    def test_no_candidate_is_promoted_and_none_claims_production(self) -> None:
        for candidate in self.gate["candidates"]:
            self.assertFalse(candidate["promoted"])
            self.assertEqual(candidate["authority"], "DEVELOPMENT_ONLY_UNPROTECTED_CANDIDATE")
        self.assertFalse(self.gate["scientific_nonclaims"]["champion_promoted"])
        self.assertFalse(self.gate["scientific_nonclaims"]["gap_005_resolved"])

    def test_the_uninformative_reference_lands_on_the_theoretical_floor(self) -> None:
        base = next(
            candidate
            for candidate in self.gate["candidates"]
            if candidate["candidate_id"] == "national_base_rate"
        )
        self.assertAlmostEqual(base["brier"], 0.25, places=6)
        self.assertFalse(base["calibration_supported"])

    def test_every_candidate_beats_or_matches_the_uninformative_floor(self) -> None:
        floor = next(
            candidate["brier"]
            for candidate in self.gate["candidates"]
            if candidate["candidate_id"] == "national_base_rate"
        )
        for candidate in self.gate["candidates"]:
            self.assertLessEqual(candidate["brier"], floor + 1e-9)

    def test_each_candidate_reports_a_bootstrap_interval_that_covers_its_estimate(self) -> None:
        for candidate in self.gate["candidates"]:
            interval = candidate["brier_bootstrap"]
            self.assertEqual(interval["resamples"], CONTRACT["evaluation"]["bootstrap_resamples"])
            self.assertLessEqual(interval["percentile_2_5"], candidate["brier"] + 1e-6)
            self.assertGreaterEqual(interval["percentile_97_5"], candidate["brier"] - 1e-6)

    def test_only_the_margin_candidate_reports_margin_error(self) -> None:
        for candidate in self.gate["candidates"]:
            declared = next(
                item
                for item in CONTRACT["candidates"]
                if item["candidate_id"] == candidate["candidate_id"]
            )
            if declared["emits_margin"]:
                self.assertIsNotNone(candidate["margin_mae"])
                self.assertIsNotNone(candidate["margin_rmse"])
            else:
                self.assertIsNone(candidate["margin_mae"])

    def test_calibration_bins_account_for_every_evaluated_row(self) -> None:
        totals: dict[str, int] = {}
        for entry in self.gate["calibration"]:
            totals[entry["candidate_id"]] = totals.get(entry["candidate_id"], 0) + entry["rows"]
        for candidate_id, total in totals.items():
            self.assertEqual(total, self.gate["cohort"]["team_rows"], candidate_id)

    def test_every_declared_slice_dimension_is_present(self) -> None:
        dimensions = {entry["dimension"] for entry in self.gate["slices"]}
        self.assertEqual(dimensions, set(CONTRACT["evaluation"]["slice_dimensions"]))

    def test_small_slices_suppress_their_metrics(self) -> None:
        minimum = CONTRACT["evaluation"]["minimum_slice_rows_for_reported_metric"]
        for entry in self.gate["slices"]:
            if entry["rows"] < minimum:
                self.assertTrue(entry["metric_suppressed_for_small_sample"])
                self.assertIsNone(entry["brier"])
            else:
                self.assertFalse(entry["metric_suppressed_for_small_sample"])
                self.assertIsNotNone(entry["brier"])

    def test_the_national_slice_reproduces_the_headline_metric(self) -> None:
        for candidate in self.gate["candidates"]:
            national = next(
                entry
                for entry in self.gate["slices"]
                if entry["candidate_id"] == candidate["candidate_id"]
                and entry["dimension"] == "national"
            )
            self.assertEqual(national["rows"], self.gate["cohort"]["team_rows"])
            self.assertAlmostEqual(national["brier"], candidate["brier"], places=7)

    def test_the_peer_cohort_is_rule_derived_and_excludes_its_own_reference(self) -> None:
        cohort = self.gate["peer_cohort"]
        self.assertEqual(cohort["reference_team"], TAMU_TEAM_ID)
        self.assertEqual(cohort["cohort_size"], CONTRACT["peer_cohort_rule"]["cohort_size"])
        self.assertFalse(cohort["seeded_from_famous_programs"])
        identifiers = [member["canonical_team_id"] for member in cohort["members"]]
        self.assertNotIn(TAMU_TEAM_ID, identifiers)
        self.assertEqual(len(identifiers), len(set(identifiers)))

    def test_the_peer_cohort_is_ordered_by_its_declared_distance(self) -> None:
        distances = [member["distance"] for member in self.gate["peer_cohort"]["members"]]
        self.assertEqual(distances, sorted(distances))
        self.assertGreater(self.gate["peer_cohort"]["eligible_programs"], 20)

    def test_the_residual_test_reports_a_group_for_every_declared_comparison(self) -> None:
        groups = {group["group"] for group in self.gate["residual_test"]["groups"]}
        self.assertEqual(groups, set(CONTRACT["residual_test"]["comparison_groups"]))

    def test_the_tamu_residual_group_stays_a_pipeline_test(self) -> None:
        tamu = next(
            group
            for group in self.gate["residual_test"]["groups"]
            if group["group"] == "TEXAS_AM"
        )
        self.assertEqual(tamu["rows"], self.gate["cohort"]["tamu_rows"])
        self.assertTrue(tamu["sample_is_too_small_for_inference"])
        self.assertEqual(
            self.gate["residual_test"]["interpretation"], "PIPELINE_EXECUTION_EVIDENCE_ONLY"
        )
        for value in self.gate["residual_test"]["claims"].values():
            self.assertFalse(value)

    def test_the_predecessor_ledger_is_preserved_rather_than_superseded(self) -> None:
        preserved = self.gate["preserved_predecessor_result"]
        self.assertTrue(preserved["predecessor_is_preserved_not_superseded"])
        self.assertTrue(preserved["cross_population_metric_comparison_is_reported_not_authoritative"])
        ledger = json.loads(
            (ROOT / preserved["ledger_relative_path"]).read_text(encoding="utf-8-sig")
        )
        self.assertEqual(ledger["ledger_identity"], preserved["ledger_identity"])
        self.assertEqual(
            {entry["candidate"] for entry in ledger["entries"]}
            - {"prior_only"},
            set(preserved["preserved_negative_candidates"]),
        )

    def test_the_gate_identity_ignores_non_authoritative_metadata(self) -> None:
        self.assertEqual(compute_gate_identity(self.gate), self.gate["gate_identity"])
        self.assertEqual(binding_identity(self.gate, "binding_identity"), self.gate["binding_identity"])


class BaselineMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data_root = Path(
            os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
        )
        cls.gate_path = ROOT / GATE_RELATIVE
        if not cls.gate_path.is_file():
            raise unittest.SkipTest("the baseline gate is not present")
        cls.gate = json.loads(cls.gate_path.read_text(encoding="utf-8"))

    def _forged(self, mutate) -> dict:
        forged = copy.deepcopy(self.gate)
        mutate(forged)
        forged.pop("gate_identity", None)
        forged.pop("binding_identity", None)
        forged["gate_identity"] = compute_gate_identity(forged)
        forged["binding_identity"] = binding_identity(forged, "binding_identity")
        return forged

    def _reject(self, forged: dict) -> None:
        with self.assertRaises(ValueError):
            validate_artifact(
                data_root=self.data_root,
                repo_root=ROOT,
                require_rebuild=False,
                gate=forged,
            )

    def test_a_promoted_champion_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["candidates"][0]["promoted"] = True

        self._reject(self._forged(mutate))

    def test_a_production_authority_upgrade_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["candidates"][0]["authority"] = "PRODUCTION_CHAMPION"

        self._reject(self._forged(mutate))

    def test_opening_protected_evaluation_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["authority"]["protected_evaluation_admission"] = True

        self._reject(self._forged(mutate))

    def test_unsealing_the_protected_lane_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["protected_lane"] = "PROTECTED_LANE_OPEN"

        self._reject(self._forged(mutate))

    def test_a_bas_claim_in_the_residual_test_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["residual_test"]["claims"]["bas_or_aggie_excess"] = True

        self._reject(self._forged(mutate))

    def test_a_tamu_specialization_lift_claim_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["scientific_nonclaims"]["tamu_specialization_lift_claimed"] = True

        self._reject(self._forged(mutate))

    def test_refitting_the_baseline_for_the_residual_test_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["residual_test"]["baseline_refit_for_this_test"] = True

        self._reject(self._forged(mutate))

    def test_a_reputation_seeded_peer_cohort_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["peer_cohort"]["seeded_from_famous_programs"] = True

        self._reject(self._forged(mutate))

    def test_placing_the_reference_program_in_its_own_cohort_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["peer_cohort"]["members"][0]["canonical_team_id"] = gate["peer_cohort"][
                "reference_team"
            ]

        self._reject(self._forged(mutate))

    def test_a_post_hoc_candidate_admission_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["precommitment"]["post_hoc_candidate_insertion"] = True

        self._reject(self._forged(mutate))

    def test_scoring_a_protected_season_row_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["leakage_checks"]["protected_season_row_scored"] = True

        self._reject(self._forged(mutate))

    def test_letting_evaluation_rows_inform_their_own_fit_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["leakage_checks"]["evaluation_rows_influenced_their_own_fit"] = True

        self._reject(self._forged(mutate))

    def test_a_forecast_publication_claim_is_rejected(self) -> None:
        def mutate(gate: dict) -> None:
            gate["scientific_nonclaims"]["forecast_published"] = True

        self._reject(self._forged(mutate))

    def test_an_unsealed_gate_identity_is_rejected(self) -> None:
        forged = copy.deepcopy(self.gate)
        forged["candidates"][0]["brier"] = 0.0
        if not (self.data_root / "canonical").is_dir():
            self.skipTest("the data root is not mounted")
        with self.assertRaises(ValueError):
            validate_artifact(
                data_root=self.data_root, repo_root=ROOT, require_rebuild=True, gate=forged
            )

    def test_an_inflated_metric_cannot_survive_an_independent_rebuild(self) -> None:
        if not (self.data_root / "canonical").is_dir():
            self.skipTest("the data root is not mounted")

        def mutate(gate: dict) -> None:
            gate["candidates"][0]["brier"] = 0.01

        with self.assertRaises(ValueError):
            validate_artifact(
                data_root=self.data_root,
                repo_root=ROOT,
                require_rebuild=True,
                gate=self._forged(mutate),
            )

    def test_a_substituted_payload_hash_is_rejected(self) -> None:
        if not (self.data_root / "canonical").is_dir():
            self.skipTest("the data root is not mounted")

        def mutate(gate: dict) -> None:
            gate["payloads"][0]["sha256"] = "0" * 64

        with self.assertRaises(ValueError):
            validate_artifact(
                data_root=self.data_root,
                repo_root=ROOT,
                require_rebuild=True,
                gate=self._forged(mutate),
            )


if __name__ == "__main__":
    unittest.main()

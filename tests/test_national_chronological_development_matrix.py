from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aggie_analytics.data.national_foundation_reconciliation import (  # noqa: E402
    binding_identity,
    stable_hash,
)
from aggie_analytics.data.national_chronological_development_matrix import (  # noqa: E402
    CONTRACT_ID,
    GATE_RELATIVE,
    NUMERIC_FEATURES,
    PASS_RESULT,
    _assert_matrix_invariants,
    _fold_transforms,
    build_feature_registry,
    build_folds,
    build_matrix,
    build_slices,
    chronological_ordinal,
    compute_gate_identity,
    load_contract,
    rebuild_expected,
    validate_artifact,
)

CONTRACT = load_contract(ROOT)


def _feature(game_id: str, team: str, opponent: str, season: int, week: int, start: str, **overrides):
    row = {
        "canonical_game_id": game_id,
        "canonical_team_id": team,
        "opponent_canonical_team_id": opponent,
        "tier_id": "TIER_2_ACCEPTED_SCOPED_REPLAY",
        "season": season,
        "week": week,
        "season_type": "regular",
        "start_date_utc_text": start,
        "is_home": True,
        "is_neutral_site": False,
        "prior_games_played": 4,
        "prior_win_rate": 0.75,
        "prior_win_rate_missing": False,
        "prior_points_for_mean": 28.0,
        "prior_points_for_mean_missing": False,
        "prior_points_against_mean": 17.0,
        "prior_points_against_mean_missing": False,
        "prior_margin_mean": 11.0,
        "prior_margin_mean_missing": False,
        "prior_season_win_rate": 0.6,
        "prior_season_win_rate_missing": False,
        "season_to_date_games": 4,
        "season_to_date_win_rate": 0.75,
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
        "team_conference": None,
        "team_conference_missing": True,
        "team_is_fbs": None,
        "team_is_fbs_missing": True,
    }
    row.update(overrides)
    return row


def _label(game_id: str, team: str, season: int, win: bool, margin: int = 7):
    return {
        "canonical_game_id": game_id,
        "canonical_team_id": team,
        "tier_id": "TIER_2_ACCEPTED_SCOPED_REPLAY",
        "season": season,
        "points_for": 24 if win else 17,
        "points_against": 17 if win else 24,
        "margin": margin if win else -margin,
        "label_win": win,
        "label_tie": False,
    }


def _tiny_population(seasons=(2022, 2023)):
    features: list[dict] = []
    labels: list[dict] = []
    for index, season in enumerate(seasons):
        for week in (1, 2):
            game = f"G-{season}-{week}"
            start = f"{season}-09-{week:02d}T00:00:00Z"
            features.append(
                _feature(game, "T:1", "T:2", season, week, start, is_home=True, prior_win_rate=0.75)
            )
            features.append(
                _feature(
                    game,
                    "T:2",
                    "T:1",
                    season,
                    week,
                    start,
                    is_home=False,
                    prior_win_rate=0.25,
                    prior_margin_mean=-3.0,
                )
            )
            labels.append(_label(game, "T:1", season, True))
            labels.append(_label(game, "T:2", season, False))
    return features, labels


class DevelopmentMatrixUnitTests(unittest.TestCase):
    def test_contract_keeps_protected_and_promotion_authority_closed(self) -> None:
        self.assertEqual(CONTRACT["contract_id"], CONTRACT_ID)
        for key in (
            "historical_pit_admission",
            "protected_training_admission",
            "protected_evaluation_admission",
            "champion_or_production_promotion",
            "forecast_publication",
        ):
            self.assertFalse(CONTRACT["authority"][key])
        self.assertFalse(CONTRACT["policy"]["globally_fitted_scaling_or_imputation"])
        self.assertFalse(CONTRACT["policy"]["tamu_adapter_or_specialization_feature"])

    def test_chronological_ordinal_orders_by_kickoff_then_week(self) -> None:
        early = {"start_date_utc_text": "2019-09-01T00:00:00Z", "season": 2019, "season_type": "regular", "week": 1}
        late = {"start_date_utc_text": "2019-09-08T00:00:00Z", "season": 2019, "season_type": "regular", "week": 2}
        self.assertLess(chronological_ordinal(early), chronological_ordinal(late))

    def test_matrix_partitions_by_the_declared_evaluation_season(self) -> None:
        features, labels = _tiny_population()
        matrix, label_rows, stats = build_matrix(
            features=features, labels=labels, contract=CONTRACT
        )
        self.assertEqual(len(matrix), 8)
        self.assertEqual(stats["training_rows"], 4)
        self.assertEqual(stats["evaluation_rows"], 4)
        self.assertTrue(all(row["season"] == 2023 for row in matrix if row["partition"] == "EVALUATION"))
        self.assertEqual(len(label_rows), len(matrix))

    def test_favorite_and_underdog_are_complementary(self) -> None:
        features, labels = _tiny_population()
        matrix, _, _ = build_matrix(features=features, labels=labels, contract=CONTRACT)
        for row in matrix:
            expected = "FAVORITE" if row["canonical_team_id"] == "T:1" else "UNDERDOG"
            self.assertEqual(row["favorite_state"], expected)

    def test_missing_prior_evidence_produces_an_even_state_not_a_guess(self) -> None:
        features, labels = _tiny_population()
        for row in features:
            row["prior_win_rate"] = None
            row["prior_win_rate_missing"] = True
        matrix, _, _ = build_matrix(features=features, labels=labels, contract=CONTRACT)
        for row in matrix:
            self.assertEqual(row["favorite_state"], "EVEN_OR_UNKNOWN")
            self.assertIsNone(row["prior_win_rate_differential"])
            self.assertTrue(row["prior_win_rate_differential_missing"])

    def test_an_excluded_protected_season_is_rejected(self) -> None:
        features, labels = _tiny_population(seasons=(2022, 2024))
        with self.assertRaises(ValueError):
            build_matrix(features=features, labels=labels, contract=CONTRACT)

    def test_a_missing_label_is_rejected(self) -> None:
        features, labels = _tiny_population()
        with self.assertRaises(ValueError):
            build_matrix(features=features, labels=labels[:-1], contract=CONTRACT)

    def test_matrix_invariants_reject_a_target_column(self) -> None:
        features, labels = _tiny_population()
        matrix, label_rows, _ = build_matrix(features=features, labels=labels, contract=CONTRACT)
        _assert_matrix_invariants(matrix, label_rows, 2023)
        contaminated = [dict(row, label_win=True) for row in matrix]
        with self.assertRaises(ValueError):
            _assert_matrix_invariants(contaminated, label_rows, 2023)

    def test_folds_expand_and_never_train_past_their_own_evaluation(self) -> None:
        features, labels = _tiny_population()
        matrix, label_rows, _ = build_matrix(features=features, labels=labels, contract=CONTRACT)
        folds = build_folds(matrix=matrix, labels=label_rows, contract=CONTRACT)
        self.assertEqual(len(folds), 2)
        self.assertLess(folds[0]["training_rows"], folds[1]["training_rows"])
        for fold in folds:
            self.assertLessEqual(
                fold["training_max_ordinal_exclusive"], min(fold["evaluation_ordinals"])
            )

    def test_fold_transforms_are_fitted_only_on_their_own_training_partition(self) -> None:
        features, labels = _tiny_population()
        matrix, label_rows, _ = build_matrix(features=features, labels=labels, contract=CONTRACT)
        folds = build_folds(matrix=matrix, labels=label_rows, contract=CONTRACT)
        first = folds[0]
        training = [
            row
            for row in matrix
            if row["chronological_ordinal"] < first["training_max_ordinal_exclusive"]
        ]
        self.assertEqual(
            stable_hash(first["fold_local_transforms"]), stable_hash(_fold_transforms(training))
        )

    def test_a_constant_feature_reports_no_usable_scale(self) -> None:
        rows = [{feature: 1.0 for feature in NUMERIC_FEATURES} for _ in range(5)]
        transforms = _fold_transforms(rows)
        self.assertEqual(transforms["prior_win_rate"]["mean"], 1.0)
        self.assertIsNone(transforms["prior_win_rate"]["stdev"])

    def test_slices_cover_every_declared_dimension(self) -> None:
        features, labels = _tiny_population()
        matrix, label_rows, _ = build_matrix(features=features, labels=labels, contract=CONTRACT)
        slices = build_slices(matrix=matrix, labels=label_rows, contract=CONTRACT)
        dimensions = {item["dimension"] for item in slices}
        self.assertEqual(dimensions, set(CONTRACT["slice_dimensions"]))

    def test_feature_registry_declares_a_missing_indicator_for_optional_features(self) -> None:
        registry = build_feature_registry(CONTRACT)
        by_id = {item["feature_id"]: item for item in registry}
        self.assertIsNone(by_id["prior_games_played"]["missing_indicator"])
        self.assertEqual(by_id["ap_poll_rank"]["missing_indicator"], "ap_poll_rank_missing")
        self.assertTrue(by_id["prior_win_rate"]["fold_local_scaled"])
        self.assertFalse(by_id["team_conference"]["fold_local_scaled"])


class DevelopmentMatrixMountedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data_root = Path(
            os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
        )
        cls.gate_path = ROOT / GATE_RELATIVE
        if not cls.gate_path.is_file() or not (cls.data_root / "canonical").is_dir():
            raise unittest.SkipTest("development matrix gate or data root is not mounted")
        cls.gate = json.loads(cls.gate_path.read_text(encoding="utf-8"))
        cls.expected = rebuild_expected(data_root=cls.data_root, repo_root=ROOT)

    def test_gate_survives_an_independent_rebuild(self) -> None:
        result = validate_artifact(
            data_root=self.data_root,
            repo_root=ROOT,
            require_rebuild=True,
            expected=self.expected,
        )
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["mode"], "INDEPENDENT_REBUILD")

    def test_population_matches_the_declared_chronology(self) -> None:
        chronology = CONTRACT["chronology"]
        population = self.gate["population"]
        self.assertEqual(population["matrix_rows"], chronology["expected_matrix_rows"])
        self.assertEqual(population["evaluation_rows"], chronology["expected_evaluation_rows"])
        self.assertEqual(population["seasons"][1], chronology["development_evaluation_season"])

    def test_protected_and_prospective_seasons_are_absent(self) -> None:
        forbidden = set(CONTRACT["chronology"]["excluded_protected_seasons"]) | set(
            CONTRACT["chronology"]["excluded_prospective_seasons"]
        )
        self.assertNotIn(self.gate["population"]["seasons"][1], forbidden)
        self.assertLess(self.gate["population"]["seasons"][1], min(forbidden))

    def test_folds_are_expanding_and_nonempty(self) -> None:
        folds = self.gate["folds"]
        self.assertGreater(len(folds), 1)
        previous = -1
        for fold in folds:
            self.assertGreater(fold["training_rows"], 0)
            self.assertGreater(fold["evaluation_rows"], 0)
            self.assertGreater(fold["training_rows"], previous)
            previous = fold["training_rows"]

    def test_the_matrix_proves_future_append_invariance(self) -> None:
        proof = self.gate["invariance_proof"]
        self.assertTrue(proof["invariant"])
        self.assertEqual(
            proof["earlier_folds_identity"], proof["earlier_folds_identity_after_truncation"]
        )
        self.assertGreater(proof["earlier_folds_compared"], 0)

    def test_every_fold_transform_is_fold_local(self) -> None:
        identities = {fold["fold_local_transforms_identity"] for fold in self.gate["folds"]}
        self.assertEqual(len(identities), len(self.gate["folds"]))
        for fold in self.gate["folds"]:
            self.assertEqual(
                fold["transform_scope"], "FITTED_ON_THIS_FOLD_TRAINING_PARTITION_ONLY"
            )

    def test_tamu_rows_are_ordinary_national_rows(self) -> None:
        population = self.gate["population"]
        self.assertGreater(population["tamu_rows"], 0)
        self.assertLess(population["tamu_row_share"], 0.02)
        registry = {item["feature_id"] for item in self.gate["feature_registry"]}
        self.assertFalse({feature for feature in registry if "tamu" in feature.lower()})
        self.assertFalse(self.gate["leakage_checks"]["tamu_adapter_present"])

    def test_slices_report_real_evaluation_coverage(self) -> None:
        national = [item for item in self.gate["slices"] if item["dimension"] == "national"]
        self.assertEqual(len(national), 1)
        self.assertEqual(national[0]["rows"], self.gate["population"]["evaluation_rows"])
        for item in self.gate["slices"]:
            self.assertGreater(item["rows"], 0)
            self.assertIsNotNone(item["positive_rate"])

    def test_no_unranked_imputation_and_no_availability_inference(self) -> None:
        checks = self.gate["leakage_checks"]
        self.assertFalse(checks["unranked_imputed_as_a_rank"])
        self.assertFalse(checks["availability_inferred"])
        self.assertFalse(checks["globally_fitted_scaling_or_imputation"])


class DevelopmentMatrixMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data_root = Path(
            os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
        )
        cls.gate_path = ROOT / GATE_RELATIVE
        if not cls.gate_path.is_file() or not (cls.data_root / "canonical").is_dir():
            raise unittest.SkipTest("development matrix gate or data root is not mounted")
        cls.gate = json.loads(cls.gate_path.read_text(encoding="utf-8"))
        cls.expected = rebuild_expected(data_root=cls.data_root, repo_root=ROOT)
        cls.manifest = json.loads(
            (cls.data_root / cls.gate["manifest"]["relative_path"]).read_text(encoding="utf-8")
        )

    def _forged(self, **changes: object) -> dict[str, object]:
        tampered = json.loads(json.dumps(self.gate))
        tampered.update(changes)
        tampered["gate_identity"] = compute_gate_identity(tampered)
        tampered["binding_identity"] = binding_identity(tampered, "binding_identity")
        return tampered

    def _reject(self, gate: dict[str, object], manifest: dict[str, object] | None = None) -> None:
        with self.assertRaises(ValueError):
            validate_artifact(
                data_root=self.data_root,
                repo_root=ROOT,
                require_rebuild=True,
                gate=gate,
                manifest=self.manifest if manifest is None else manifest,
                expected=self.expected,
            )

    def test_rejects_a_globally_fitted_transform(self) -> None:
        checks = dict(self.gate["leakage_checks"])
        checks["globally_fitted_scaling_or_imputation"] = True
        self._reject(self._forged(leakage_checks=checks))

    def test_rejects_an_out_of_fold_transform_scope(self) -> None:
        folds = json.loads(json.dumps(self.gate["folds"]))
        folds[0]["transform_scope"] = "FITTED_ON_THE_FULL_POPULATION"
        self._reject(self._forged(folds=folds))

    def test_rejects_a_fold_that_trains_past_its_own_evaluation(self) -> None:
        folds = json.loads(json.dumps(self.gate["folds"]))
        folds[0]["training_max_ordinal_exclusive"] = max(folds[0]["evaluation_ordinals"]) + 1
        self._reject(self._forged(folds=folds))

    def test_rejects_an_empty_training_partition(self) -> None:
        folds = json.loads(json.dumps(self.gate["folds"]))
        folds[0]["training_rows"] = 0
        self._reject(self._forged(folds=folds))

    def test_rejects_a_protected_season_in_the_population(self) -> None:
        population = json.loads(json.dumps(self.gate["population"]))
        population["seasons"] = [1963, 2024]
        self._reject(self._forged(population=population))

    def test_rejects_a_forged_invariance_proof(self) -> None:
        proof = json.loads(json.dumps(self.gate["invariance_proof"]))
        proof["earlier_folds_identity_after_truncation"] = "0" * 64
        self._reject(self._forged(invariance_proof=proof))

    def test_rejects_a_disclaimed_invariance_proof(self) -> None:
        proof = json.loads(json.dumps(self.gate["invariance_proof"]))
        proof["invariant"] = False
        self._reject(self._forged(invariance_proof=proof))

    def test_rejects_an_inflated_matrix_row_count(self) -> None:
        population = json.loads(json.dumps(self.gate["population"]))
        population["matrix_rows"] = int(population["matrix_rows"]) + 100
        self._reject(self._forged(population=population))

    def test_rejects_a_smuggled_tamu_adapter(self) -> None:
        checks = dict(self.gate["leakage_checks"])
        checks["tamu_adapter_present"] = True
        self._reject(self._forged(leakage_checks=checks))

    def test_rejects_a_disabled_same_game_exclusion(self) -> None:
        checks = dict(self.gate["leakage_checks"])
        checks["same_game_target_outcome_excluded"] = False
        self._reject(self._forged(leakage_checks=checks))

    def test_rejects_forged_slice_counts(self) -> None:
        slices = json.loads(json.dumps(self.gate["slices"]))
        slices[0]["rows"] = int(slices[0]["rows"]) + 5
        self._reject(self._forged(slices=slices))

    def test_rejects_a_false_readiness_claim(self) -> None:
        nonclaims = dict(self.gate["scientific_nonclaims"])
        nonclaims["gap_005_resolved"] = True
        self._reject(self._forged(scientific_nonclaims=nonclaims))

    def test_rejects_an_opened_protected_lane(self) -> None:
        self._reject(self._forged(protected_lane="OPEN_PROTECTED_LANE"))

    def test_rejects_a_substituted_payload_hash(self) -> None:
        manifest = json.loads(json.dumps(self.manifest))
        manifest["payloads"][0]["sha256"] = "0" * 64
        self._reject(self.gate, manifest)

    def test_rejects_coordinated_rehash_tampering(self) -> None:
        manifest = json.loads(json.dumps(self.manifest))
        payloads = json.loads(json.dumps(self.gate["payloads"]))
        for entry in manifest["payloads"] + payloads:
            if entry["name"] == "national_development_matrix_labels.jsonl":
                entry["sha256"] = "1" * 64
                entry["rows"] = int(entry["rows"]) + 2
        manifest["record_hashes"]["labels"] = "2" * 64
        self._reject(self._forged(payloads=payloads), manifest)

    def test_rejects_an_unsealed_identity(self) -> None:
        tampered = json.loads(json.dumps(self.gate))
        tampered["population"]["matrix_rows"] = 1
        self._reject(tampered)

    def test_rejects_a_non_passing_result(self) -> None:
        self.assertEqual(self.gate["result"], PASS_RESULT)
        self._reject(self._forged(result="PASS_NATIONAL_PRODUCTION_MATRIX"))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aggie_analytics.experimentation.development_2023_labeled_replay import (  # noqa: E402
    CONTRACT_RELATIVE,
    CheckpointRejected,
    ProtectedOutcomeDenied,
    assert_feature_surface,
    assert_no_protected_outcomes,
    build_folds,
    derive_membership_proof,
    execute_fold,
    fit_prior_plus,
    fold_membership,
    identity_core,
    load_contract,
    prior_only_probability,
    prove_stale_checkpoint_rejection,
    stable_hash,
    validate_checkpoint,
    verify_protected_registry,
)
from aggie_analytics.validation.protected_split_authority import (  # noqa: E402
    assert_labels_cannot_override_protected_membership,
    sha256_file,
)


def _feature(**overrides: object) -> dict[str, object]:
    row = {
        "row_id": "row-a",
        "target_game_id": "game-a",
        "team_id": "team-a",
        "opponent_id": "team-b",
        "site": "HOME",
        "season": 2023,
        "season_type": "regular",
        "week": 1,
        "cutoff_utc": "2023-08-25T18:30:00Z",
        "target_start_utc": "2023-08-26T18:30:00Z",
        "prior_games": 10,
        "prior_win_rate": 0.6,
        "prior_points_for_mean": 28.0,
        "prior_points_against_mean": 21.0,
        "missingness": 0,
        "epa_mean": 0.05,
        "cold_start": False,
        "play_drive_protected_eligible": False,
    }
    row.update(overrides)
    return row


def _label(**overrides: object) -> dict[str, object]:
    row = {
        "row_id": "row-a",
        "target_game_id": "game-a",
        "team_id": "team-a",
        "season": 2023,
        "result": "WIN",
        "points_for": 31,
        "points_against": 10,
        "margin": 21,
        "label_available_after_utc": "2023-08-26T18:30:00Z",
        "not_a_pregame_feature": True,
        "development_label_only": True,
    }
    row.update(overrides)
    return row


class Development2023LabeledReplayUnitTests(unittest.TestCase):
    def test_contract_authority_is_development_only(self) -> None:
        contract = load_contract(ROOT)
        self.assertTrue(contract["authority"]["development_2023_labeled_evaluation"])
        self.assertFalse(contract["authority"]["pregame_feature_use_of_labels"])
        self.assertFalse(contract["authority"]["protected_evaluation_admission"])
        self.assertFalse(contract["authority"]["champion_or_production_promotion"])
        self.assertEqual(contract["acceptance"]["allowed_seasons"], [2023])
        self.assertEqual(contract["acceptance"]["forbidden_seasons"], [2024, 2025])

    def test_protected_registry_pin_and_label_override_fail_closed(self) -> None:
        contract = load_contract(ROOT)
        digest = verify_protected_registry(ROOT, contract)
        self.assertEqual(digest, contract["input_identities"]["protected_split_registry_sha256"])
        self.assertEqual(
            assert_labels_cannot_override_protected_membership(ROOT, 2024, "DEVELOPMENT_ONLY"),
            "PROTECTED_TEST",
        )
        self.assertEqual(
            assert_labels_cannot_override_protected_membership(
                ROOT, 2025, "DEVELOPMENT_EVALUATION_UNPROTECTED"
            ),
            "PROTECTED_TEST",
        )

    def test_protected_year_insertion_fails_closed(self) -> None:
        with self.assertRaises(ProtectedOutcomeDenied):
            assert_no_protected_outcomes([{"season": 2024}], context="test")
        with self.assertRaises(ProtectedOutcomeDenied):
            assert_no_protected_outcomes([{"season": 2025}], context="test")

    def test_feature_surface_rejects_outcome_columns(self) -> None:
        with self.assertRaises(ValueError):
            assert_feature_surface([{"season": 2023, "result": "WIN"}])
        with self.assertRaises(ValueError):
            assert_feature_surface([{"season": 2023, "points_for": 31}])

    def test_same_game_exclusion_is_derived(self) -> None:
        early = _feature(row_id="row-early", target_game_id="game-early", cutoff_utc="2023-08-20T00:00:00Z", week=0)
        eval_row = _feature()
        labels = {
            "row-early": _label(row_id="row-early", target_game_id="game-early", label_available_after_utc="2023-08-21T00:00:00Z"),
            "row-a": _label(),
        }
        fold = {
            "fold_id": "2023-regular-W01",
            "fold_index": 1,
            "season_type": "regular",
            "week": 1,
            "min_cutoff_utc": "2023-08-25T18:30:00Z",
            "max_cutoff_utc": "2023-08-25T18:30:00Z",
            "rows": [eval_row],
        }
        membership = fold_membership(fold, [early, eval_row], labels)
        self.assertTrue(membership["same_game_excluded"])
        self.assertEqual(membership["train_row_ids"] if False else [row["row_id"] for row in membership["train_rows"]], ["row-early"])
        self.assertEqual(membership["game_id_intersection"], [])
        leaked = fold_membership(
            fold,
            [{**early, "target_game_id": "game-a", "row_id": "row-leak"}],
            {
                **labels,
                "row-leak": _label(row_id="row-leak", target_game_id="game-a", label_available_after_utc="2023-08-21T00:00:00Z"),
            },
        )
        self.assertEqual(leaked["game_id_intersection"], [])
        self.assertEqual(leaked["train_rows"], [])
        self.assertIn("SAME_GAME_EXCLUDED", leaked["excluded_candidates"][0]["reasons"])

    def test_first_fold_identity_or_abstain(self) -> None:
        eval_row = _feature()
        labels = {"row-a": _label()}
        fold = {
            "fold_id": "2023-regular-W01",
            "fold_index": 0,
            "season_type": "regular",
            "week": 1,
            "min_cutoff_utc": "2023-08-25T18:30:00Z",
            "max_cutoff_utc": "2023-08-25T18:30:00Z",
            "rows": [eval_row],
        }
        result = execute_fold(fold, [eval_row], labels)
        self.assertTrue(result["first_fold_no_fit"])
        self.assertEqual(result["train_row_count"], 0)
        self.assertEqual(result["prior_plus_model"]["kind"], "HISTORICAL_ONLY_IDENTITY_OR_ABSTAIN")
        self.assertTrue(result["prior_plus_play_drive"].get("abstained"))
        self.assertAlmostEqual(result["prior_only"]["accuracy"], 1.0)

    def test_incomplete_or_missing_prior_uses_neutral_probability(self) -> None:
        self.assertEqual(prior_only_probability({"prior_win_rate": None}), 0.5)
        self.assertGreater(prior_only_probability({"prior_win_rate": 0.9}), 0.8)

    def test_membership_compares_games_to_games(self) -> None:
        proof = derive_membership_proof(
            [{"row_id": "r1", "target_game_id": "g1"}],
            [{"row_id": "r2", "target_game_id": "g2"}],
        )
        self.assertTrue(proof["same_game_excluded"])
        collided = derive_membership_proof(
            [{"row_id": "r1", "target_game_id": "g1"}],
            [{"row_id": "r2", "target_game_id": "g1"}],
        )
        self.assertEqual(collided["game_id_intersection"], ["g1"])
        self.assertFalse(collided["same_game_excluded"])

    def test_stale_checkpoint_is_rejected_after_rehash(self) -> None:
        fold = {
            "fold_id": "2023-regular-W01",
            "fold_index": 0,
            "min_cutoff_utc": "2023-08-25T18:30:00Z",
        }
        proof = prove_stale_checkpoint_rejection(
            fold, run_identity="run", matrix_identity="matrix", code_identity="code"
        )
        self.assertTrue(proof["pass"])
        with self.assertRaises(CheckpointRejected):
            validate_checkpoint(
                {
                    "schema_version": "aggie.experimentation.development_2023_labeled_checkpoint.v1",
                    "run_identity": "run",
                    "matrix_identity": "matrix",
                    "code_identity": "stale",
                    "fold_id": "2023-regular-W01",
                    "fold_index": 0,
                    "train_cutoff_utc": "2023-08-25T18:30:00Z",
                },
                run_identity="run",
                matrix_identity="matrix",
                code_identity="code",
                fold=fold,
            )

    def test_outer_identity_changes_after_semantic_tamper(self) -> None:
        core = identity_core(
            contract_sha256="a" * 64,
            input_identities={
                "bat523_prior_dataset_identity": "b" * 64,
                "bat523_pregame_prior_rows_sha256": "c" * 64,
                "play_drive_dataset_identity": "d" * 64,
                "play_drive_feature_sha256": "e" * 64,
                "bat565_label_dataset_identity": "f" * 64,
                "bat565_team_outcome_sha256": "1" * 64,
                "protected_split_registry_sha256": "2" * 64,
            },
            record_hashes={"features": "3" * 64, "labels": "4" * 64},
            population={
                "feature_rows": 1820,
                "label_rows": 1820,
                "games": 910,
                "cold_start_rows": 4,
                "seasons": [2023],
            },
            fold_hashes=["5" * 64],
            metrics={"prior_only": {"brier": 0.25}},
        )
        tampered = dict(core)
        tampered["metrics"] = {"prior_only": {"brier": 0.01}}
        self.assertNotEqual(stable_hash(core), stable_hash(tampered))
        removed = dict(core)
        removed["population"] = {**core["population"], "feature_rows": 1819}
        self.assertNotEqual(stable_hash(core), stable_hash(removed))

    def test_folds_are_chronological(self) -> None:
        folds = build_folds(
            [
                _feature(row_id="r2", week=2, cutoff_utc="2023-09-06T23:30:00Z", target_game_id="g2"),
                _feature(row_id="r1", week=1, cutoff_utc="2023-08-25T18:30:00Z", target_game_id="g1"),
            ]
        )
        self.assertEqual([fold["fold_id"] for fold in folds], ["2023-regular-W01", "2023-regular-W02"])
        self.assertEqual(folds[0]["fold_index"], 0)

    def test_prior_plus_fit_uses_only_train_rows(self) -> None:
        train = [_feature(row_id="train", epa_mean=0.2, prior_win_rate=0.4)]
        labels = {"train": _label(row_id="train", result="WIN")}
        model = fit_prior_plus(train, labels)
        self.assertEqual(model["kind"], "FOLD_LOCAL_LINEAR_PROBABILITY_ON_EPA_MEAN_RESIDUAL")
        self.assertEqual(model["train_row_ids"], ["train"])
        empty = fit_prior_plus([], {})
        self.assertEqual(empty["kind"], "HISTORICAL_ONLY_IDENTITY_OR_ABSTAIN")

    def test_contract_file_hash_is_stable_utf8(self) -> None:
        path = ROOT / CONTRACT_RELATIVE
        self.assertTrue(path.is_file())
        self.assertEqual(len(sha256_file(path)), 64)


class Development2023LabeledReplayLiveTests(unittest.TestCase):
    def test_live_rebuild_when_data_root_present(self) -> None:
        data_root = Path(r"C:\BatteredAggieSyndrome.data")
        prior = (
            data_root
            / "features"
            / "historical_known_at"
            / "sha256"
            / "cf732b78db6deff2e2cca51364a18e03219a5ceda88d2f5efa475dad1f7e3fe7"
            / "pregame_prior_rows.parquet"
        )
        if not prior.is_file():
            self.skipTest("external BAT-523 prior payload is not mounted")
        from aggie_analytics.experimentation.development_2023_labeled_replay import (
            rebuild_expected,
            validate_artifact,
        )

        expected = rebuild_expected(data_root=data_root, repo_root=ROOT)
        self.assertEqual(expected["matrix"]["population"]["feature_rows"], 1820)
        self.assertEqual(expected["matrix"]["population"]["games"], 910)
        self.assertEqual(expected["matrix"]["population"]["seasons"], [2023])
        gate = ROOT / "artifacts" / "pit" / "development_walk_forward_2023.json"
        if not gate.is_file():
            self.skipTest("labeled replay gate has not been materialized yet")
        validated = validate_artifact(data_root=data_root, repo_root=ROOT, require_rebuild=True)
        self.assertEqual(validated["result"], "PASS")


if __name__ == "__main__":
    unittest.main()

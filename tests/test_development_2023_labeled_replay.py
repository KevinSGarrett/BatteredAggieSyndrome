from __future__ import annotations

import json
import math
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aggie_analytics.experimentation.development_2023_labeled_replay import (  # noqa: E402
    CONTRACT_RELATIVE,
    CheckpointRejected,
    LabelUnavailable,
    PairProbabilityDenied,
    ProtectedOutcomeDenied,
    SUPERSEDED_KICKOFF_LABEL_IDENTITY,
    assert_feature_surface,
    assert_no_protected_outcomes,
    assert_unique_game_pairing,
    build_folds,
    canonical_game_orientation,
    compute_gate_identity,
    derive_membership_proof,
    execute_fold,
    fit_prior_plus,
    fold_membership,
    identity_core,
    load_contract,
    normalize_pair_probabilities,
    prior_only_probability,
    prove_stale_checkpoint_rejection,
    stable_hash,
    unique_game_eval_rows,
    validate_artifact,
    validate_checkpoint,
    verify_protected_registry,
)
from aggie_analytics.experimentation.development_rankings_walk_forward_2023 import (  # noqa: E402
    normalize_pair_probabilities as rankings_normalize_pair_probabilities,
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
        "label_available_after_utc": "2023-08-27T18:30:00Z",
        "not_a_pregame_feature": True,
        "development_label_only": True,
    }
    row.update(overrides)
    return row


def _pair(
    game_id: str = "game-a",
    *,
    week: int = 1,
    cutoff_utc: str = "2023-08-25T18:30:00Z",
    start_utc: str = "2023-08-26T18:30:00Z",
    available_utc: str = "2023-08-27T18:30:00Z",
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    home = _feature(
        row_id=f"{game_id}-home",
        target_game_id=game_id,
        team_id="team-a",
        opponent_id="team-b",
        site="HOME",
        week=week,
        cutoff_utc=cutoff_utc,
        target_start_utc=start_utc,
    )
    away = _feature(
        row_id=f"{game_id}-away",
        target_game_id=game_id,
        team_id="team-b",
        opponent_id="team-a",
        site="AWAY",
        week=week,
        cutoff_utc=cutoff_utc,
        target_start_utc=start_utc,
        prior_win_rate=0.4,
    )
    labels = {
        f"{game_id}-home": _label(
            row_id=f"{game_id}-home",
            target_game_id=game_id,
            team_id="team-a",
            result="WIN",
            points_for=31,
            points_against=10,
            margin=21,
            label_available_after_utc=available_utc,
        ),
        f"{game_id}-away": _label(
            row_id=f"{game_id}-away",
            target_game_id=game_id,
            team_id="team-b",
            result="LOSS",
            points_for=10,
            points_against=31,
            margin=-21,
            label_available_after_utc=available_utc,
        ),
    }
    return [home, away], labels


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
            "fold_evaluation_cutoff_utc": "2023-08-25T18:30:00Z",
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
        rows, labels = _pair()
        fold = {
            "fold_id": "2023-regular-W01",
            "fold_index": 0,
            "season_type": "regular",
            "week": 1,
            "min_cutoff_utc": "2023-08-25T18:30:00Z",
            "max_cutoff_utc": "2023-08-25T18:30:00Z",
            "fold_evaluation_cutoff_utc": "2023-08-25T18:30:00Z",
            "rows": rows,
        }
        result = execute_fold(fold, rows, labels)
        self.assertTrue(result["first_fold_no_fit"])
        self.assertEqual(result["train_row_count"], 0)
        self.assertEqual(result["eval_unique_games"], 1)
        self.assertEqual(result["prior_plus_model"]["kind"], "HISTORICAL_ONLY_IDENTITY_OR_ABSTAIN")
        self.assertTrue(result["prior_plus_play_drive"].get("abstained"))
        self.assertAlmostEqual(result["prior_only"]["accuracy"], 1.0)
        self.assertEqual(result["unique_game_prior_only"]["rows"], 1)

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
                "unique_games": 910,
                "team_rows": 1820,
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

    def test_lexical_plus00_versus_z_does_not_admit_equal_instant(self) -> None:
        early, labels = _pair(
            "game-early",
            week=1,
            cutoff_utc="2023-09-01T00:00:00Z",
            start_utc="2023-09-02T00:00:00Z",
            available_utc="2023-09-10T00:00:00+00:00",
        )
        later, later_labels = _pair(
            "game-later",
            week=2,
            cutoff_utc="2023-09-10T00:00:00Z",
            start_utc="2023-09-11T00:00:00Z",
            available_utc="2023-09-12T00:00:00Z",
        )
        labels.update(later_labels)
        fold = {
            "fold_id": "2023-regular-W02",
            "fold_index": 1,
            "season_type": "regular",
            "week": 2,
            "min_cutoff_utc": "2023-09-10T00:00:00Z",
            "max_cutoff_utc": "2023-09-10T00:00:00Z",
            "fold_evaluation_cutoff_utc": "2023-09-10T00:00:00Z",
            "rows": later,
        }
        membership = fold_membership(fold, early + later, labels)
        self.assertEqual(membership["train_rows"], [])
        self.assertIn("LABEL_NOT_AVAILABLE_BEFORE_CUTOFF", membership["availability_exclusions"][0]["reasons"])

    def test_availability_strictly_before_fold_cutoff(self) -> None:
        train, train_labels = _pair(
            "game-train",
            week=1,
            cutoff_utc="2023-09-01T00:00:00Z",
            start_utc="2023-09-02T00:00:00Z",
            available_utc="2023-09-03T00:00:00Z",
        )
        boundary, boundary_labels = _pair(
            "game-boundary",
            week=1,
            cutoff_utc="2023-09-07T00:00:00Z",
            start_utc="2023-09-08T00:00:00Z",
            available_utc="2023-09-09T00:00:00Z",
        )
        later, later_labels = _pair(
            "game-later",
            week=2,
            cutoff_utc="2023-09-09T00:00:00Z",
            start_utc="2023-09-10T00:00:00Z",
            available_utc="2023-09-11T00:00:00Z",
        )
        labels = {**train_labels, **boundary_labels, **later_labels}
        fold = {
            "fold_id": "2023-regular-W02",
            "fold_index": 1,
            "season_type": "regular",
            "week": 2,
            "min_cutoff_utc": "2023-09-09T00:00:00Z",
            "max_cutoff_utc": "2023-09-09T00:00:00Z",
            "fold_evaluation_cutoff_utc": "2023-09-09T00:00:00Z",
            "rows": later,
        }
        membership = fold_membership(fold, train + boundary + later, labels)
        self.assertEqual([row["row_id"] for row in membership["train_rows"]], ["game-train-away", "game-train-home"])
        excluded = {item["target_game_id"] for item in membership["availability_exclusions"]}
        self.assertIn("game-boundary", excluded)

    def test_conservative_bound_crossing_next_fold_is_excluded(self) -> None:
        saturday, saturday_labels = _pair(
            "game-sat",
            week=1,
            cutoff_utc="2023-09-08T23:00:00Z",
            start_utc="2023-09-09T23:00:00Z",
            available_utc="2023-09-10T23:00:00Z",
        )
        tuesday, tuesday_labels = _pair(
            "game-tue",
            week=2,
            cutoff_utc="2023-09-10T18:00:00Z",
            start_utc="2023-09-11T18:00:00Z",
            available_utc="2023-09-12T18:00:00Z",
        )
        fold = {
            "fold_id": "2023-regular-W02",
            "fold_index": 1,
            "season_type": "regular",
            "week": 2,
            "min_cutoff_utc": "2023-09-10T18:00:00Z",
            "max_cutoff_utc": "2023-09-10T18:00:00Z",
            "fold_evaluation_cutoff_utc": "2023-09-10T18:00:00Z",
            "rows": tuesday,
        }
        membership = fold_membership(fold, saturday + tuesday, {**saturday_labels, **tuesday_labels})
        self.assertEqual(membership["train_rows"], [])
        self.assertEqual(membership["availability_exclusions"][0]["target_game_id"], "game-sat")

    def test_postponed_game_uses_feature_week_not_start_calendar(self) -> None:
        rows, labels = _pair(
            "game-postponed",
            week=6,
            cutoff_utc="2023-10-06T23:30:00Z",
            start_utc="2023-10-07T23:30:00Z",
            available_utc="2023-10-08T23:30:00Z",
        )
        folds = build_folds(rows)
        self.assertEqual(folds[0]["fold_id"], "2023-regular-W06")
        self.assertEqual(folds[0]["fold_evaluation_cutoff_utc"], "2023-10-06T23:30:00Z")
        membership = fold_membership(folds[0], rows, labels)
        self.assertEqual(membership["train_rows"], [])
        self.assertEqual(len(membership["eval_rows"]), 2)

    def test_kickoff_time_label_is_rejected_for_evaluation(self) -> None:
        rows, labels = _pair(available_utc="2023-08-26T18:30:00Z")
        fold = {
            "fold_id": "2023-regular-W01",
            "fold_index": 0,
            "season_type": "regular",
            "week": 1,
            "min_cutoff_utc": "2023-08-25T18:30:00Z",
            "max_cutoff_utc": "2023-08-25T18:30:00Z",
            "fold_evaluation_cutoff_utc": "2023-08-25T18:30:00Z",
            "rows": rows,
        }
        with self.assertRaises(LabelUnavailable):
            execute_fold(fold, rows, labels)

    def test_unique_game_pairing_rejects_mismatch_and_duplicate(self) -> None:
        rows, labels = _pair()
        pairing = assert_unique_game_pairing(rows, list(labels.values()))
        self.assertEqual(pairing["unique_games"], 1)
        labels[f"{rows[1]['row_id']}"]["result"] = "WIN"
        with self.assertRaises(ValueError):
            assert_unique_game_pairing(rows, list(labels.values()))
        with self.assertRaises(ValueError):
            assert_unique_game_pairing(rows + [rows[0]], list(labels.values()) + [labels[rows[0]["row_id"]]])

    def test_contract_rejects_superseded_kickoff_parent(self) -> None:
        contract = load_contract(ROOT)
        self.assertNotEqual(
            contract["input_identities"]["bat565_label_dataset_identity"],
            SUPERSEDED_KICKOFF_LABEL_IDENTITY,
        )
        self.assertEqual(contract["contract_id"], "BAT-566-2023-LABELED-DEVELOPMENT-REPLAY-V3")
        self.assertEqual(
            contract["label_semantics"]["completion_bound"],
            "CONSERVATIVE_POST_START_ELIGIBILITY_BOUND_NOT_OBSERVED_FINAL_WHISTLE",
        )


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
        self.assertEqual(expected["matrix"]["population"]["unique_games"], 910)
        self.assertEqual(expected["matrix"]["population"]["seasons"], [2023])
        self.assertNotEqual(
            expected["contract"]["input_identities"]["bat565_label_dataset_identity"],
            SUPERSEDED_KICKOFF_LABEL_IDENTITY,
        )
        gate = ROOT / "artifacts" / "pit" / "development_walk_forward_2023.json"
        if not gate.is_file():
            self.skipTest("labeled replay gate has not been materialized yet")
        payload = json.loads(gate.read_text(encoding="utf-8"))
        if payload.get("input_identities", {}).get("bat565_label_dataset_identity") == SUPERSEDED_KICKOFF_LABEL_IDENTITY:
            self.skipTest("corrected BAT-566 identity has not been rematerialized yet")
        validated = validate_artifact(data_root=data_root, repo_root=ROOT, require_rebuild=True)
        self.assertEqual(validated["result"], "PASS")
        self.assertNotEqual(validated["replay_identity"], payload.get("supersession", {}).get("replay_identity"))


class Development2023LabeledReplayMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
        gate_path = ROOT / "artifacts" / "pit" / "development_walk_forward_2023.json"
        label_id = load_contract(ROOT)["input_identities"]["bat565_label_dataset_identity"]
        label_payload = (
            cls.data_root
            / "pit_state"
            / "development_outcomes"
            / "sha256"
            / label_id
            / "team_outcome_observations.parquet"
        )
        if not gate_path.is_file() or not label_payload.is_file():
            raise unittest.SkipTest("external BAT-566 payloads or gate are not mounted")
        try:
            import polars  # noqa: F401
        except ImportError as exc:
            raise unittest.SkipTest("optional data-engineering environment is not installed") from exc
        cls.gate = json.loads(gate_path.read_text(encoding="utf-8"))
        if cls.gate.get("input_identities", {}).get("bat565_label_dataset_identity") == SUPERSEDED_KICKOFF_LABEL_IDENTITY:
            raise unittest.SkipTest("corrected BAT-566 identity has not been rematerialized yet")
        from aggie_analytics.experimentation.development_2023_labeled_replay import rebuild_expected

        cls.expected = rebuild_expected(data_root=cls.data_root, repo_root=ROOT)
        manifest_path = (
            cls.data_root
            / "manifests"
            / "development_2023_matrix"
            / "sha256"
            / cls.expected["matrix_identity"]
            / "development_2023_labeled_replay_manifest.json"
        )
        if not manifest_path.is_file():
            raise unittest.SkipTest("corrected BAT-566 manifest has not been rematerialized yet")
        cls.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    def _mutated_gate(self, **changes: object) -> dict[str, object]:
        tampered = json.loads(json.dumps(self.gate))
        tampered.update(changes)
        tampered["gate_identity"] = compute_gate_identity(tampered)
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

    def test_changed_train_row_count_is_rejected(self) -> None:
        folds = json.loads(json.dumps(self.gate["folds"]))
        folds[1]["train_row_count"] = int(folds[1]["train_row_count"]) + 3
        self._reject(self._mutated_gate(folds=folds))

    def test_changed_fold_membership_is_rejected(self) -> None:
        folds = json.loads(json.dumps(self.gate["folds"]))
        folds[1]["membership"]["train_membership_sha256"] = "a" * 64
        self._reject(self._mutated_gate(folds=folds))

    def test_changed_fold_cutoff_is_rejected(self) -> None:
        folds = json.loads(json.dumps(self.gate["folds"]))
        folds[1]["fold_evaluation_cutoff_utc"] = "2099-01-01T00:00:00Z"
        self._reject(self._mutated_gate(folds=folds))

    def test_changed_same_game_proof_is_rejected(self) -> None:
        folds = json.loads(json.dumps(self.gate["folds"]))
        folds[0]["same_game_excluded"] = False
        self._reject(self._mutated_gate(folds=folds))

    def test_changed_metric_is_rejected(self) -> None:
        metrics = json.loads(json.dumps(self.gate["metrics"]))
        metrics["prior_only"]["brier"] = 0.01
        self._reject(self._mutated_gate(metrics=metrics))

    def test_changed_incremental_result_is_rejected(self) -> None:
        incremental = dict(self.gate["incremental_play_drive_result"])
        incremental["brier_delta_plus_minus_prior"] = -0.5
        self._reject(self._mutated_gate(incremental_play_drive_result=incremental))

    def test_promotion_authority_true_is_rejected(self) -> None:
        authority = dict(self.gate["authority"])
        authority["champion_or_production_promotion"] = True
        self._reject(self._mutated_gate(authority=authority))

    def test_protected_performance_claim_true_is_rejected(self) -> None:
        nonclaims = dict(self.gate["scientific_nonclaims"])
        nonclaims["protected_performance_claimed"] = True
        self._reject(self._mutated_gate(scientific_nonclaims=nonclaims))

    def test_altered_bat565_parent_identity_is_rejected(self) -> None:
        identities = dict(self.gate["input_identities"])
        identities["bat565_label_dataset_identity"] = SUPERSEDED_KICKOFF_LABEL_IDENTITY
        self._reject(self._mutated_gate(input_identities=identities))

    def test_substituted_and_omitted_payload_are_rejected(self) -> None:
        substituted = json.loads(json.dumps(self.manifest))
        substituted["payloads"][0]["sha256"] = "2" * 64
        payloads = json.loads(json.dumps(self.gate["payloads"]))
        payloads[0]["sha256"] = "2" * 64
        self._reject(self._mutated_gate(payloads=payloads), substituted)
        omitted = json.loads(json.dumps(self.manifest))
        omitted["payloads"] = list(self.manifest["payloads"][1:])
        self._reject(self._mutated_gate(), omitted)

    def test_altered_result_and_forged_completion_are_rejected(self) -> None:
        self._reject(self._mutated_gate(result="PASS_PRODUCTION_READY"))
        forged = self._mutated_gate(result="FORGED_DONE", classification="PRODUCTION_CHAMPION")
        self.assertNotEqual(forged["gate_identity"], self.gate["gate_identity"])
        self._reject(forged)


class Development2023PairNormalizationUnitTests(unittest.TestCase):
    def test_complement(self) -> None:
        norm = normalize_pair_probabilities(0.7, 0.3)
        self.assertAlmostEqual(norm["p_a_game"], 0.7)
        self.assertAlmostEqual(norm["p_b_game"], 0.3)
        self.assertAlmostEqual(norm["raw_sum"], 1.0)
        self.assertAlmostEqual(norm["p_a_game"] + norm["p_b_game"], 1.0)
        self.assertLessEqual(norm["complement_error"], 1e-12)

    def test_non_complementary_raw_pair_normalizes_to_0_6_over_1_1(self) -> None:
        norm = normalize_pair_probabilities(0.6, 0.5)
        self.assertEqual(norm["p_a_game"], 0.6 / 1.1)
        self.assertEqual(norm["p_b_game"], 1.0 - (0.6 / 1.1))
        self.assertEqual(norm["raw_sum"], 1.1)
        self.assertEqual(norm["p_a_game"] + norm["p_b_game"], 1.0)

    def test_fail_closed_invalid(self) -> None:
        for left, right in (
            (0.0, 0.5),
            (0.5, 0.0),
            (0.0, 0.0),
            (-0.1, 0.5),
            (0.5, -0.1),
            (math.nan, 0.5),
            (0.5, math.nan),
            (math.inf, 0.5),
            (0.5, math.inf),
        ):
            with self.subTest(left=left, right=right):
                with self.assertRaises(PairProbabilityDenied):
                    normalize_pair_probabilities(left, right)

    def test_team_row_versus_unique_game_are_distinct(self) -> None:
        rows, _labels = _pair()
        rows[1]["prior_win_rate"] = 0.5
        team_probs = [prior_only_probability(row) for row in rows]
        selected = unique_game_eval_rows(rows, prior_only_probability)[0]
        self.assertAlmostEqual(team_probs[0], 0.6)
        self.assertAlmostEqual(team_probs[1], 0.5)
        self.assertAlmostEqual(selected["p_game"], 0.6 / 1.1)
        self.assertNotEqual(selected["p_game"], selected["p_raw"])
        self.assertNotIn(selected["p_game"], team_probs)

    def test_orientation_after_normalize(self) -> None:
        rows, _labels = _pair()
        away, home = rows[1], rows[0]
        away["prior_win_rate"] = 0.6
        home["prior_win_rate"] = 0.5
        selected = unique_game_eval_rows([away, home], prior_only_probability)[0]
        self.assertEqual(selected["site"], "HOME")
        self.assertEqual(selected["row_id"], home["row_id"])
        self.assertAlmostEqual(selected["p_raw"], 0.5)
        self.assertAlmostEqual(selected["p_game"], 0.5 / 1.1)
        oriented_first = canonical_game_orientation([away, home])
        self.assertEqual(oriented_first["row_id"], home["row_id"])
        self.assertNotAlmostEqual(prior_only_probability(oriented_first), selected["p_game"])

    def test_bat568_reuses_same_helper(self) -> None:
        self.assertIs(rankings_normalize_pair_probabilities, normalize_pair_probabilities)

    def test_zero_sum_and_negative_are_rejected(self) -> None:
        with self.assertRaises(PairProbabilityDenied):
            normalize_pair_probabilities(0.0, 0.0)
        with self.assertRaises(PairProbabilityDenied):
            normalize_pair_probabilities(-0.2, 0.2)


if __name__ == "__main__":
    unittest.main()

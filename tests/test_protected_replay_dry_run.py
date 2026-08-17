from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.experimentation.walk_forward import (  # noqa: E402
    CHECKPOINT_SCHEMA,
    DATASET_IDENTITY,
    DEVELOPMENT_SEASON,
    REQUIRED_ACCEPTANCE,
    REQUIRED_PAYLOADS,
    SCHEMA_VERSION,
    CheckpointRejected,
    DevelopmentLabelUnavailable,
    ProtectedOutcomeAccessor,
    ProtectedOutcomeDenied,
    compute_artifact_identity,
    consume_for_bat401,
    derive_membership_proof,
    derive_terminal_state,
    execute_fold,
    fit_fold_local_transform,
    prove_stale_checkpoint_rejection,
    prove_target_game_exclusion,
    try_resolve_data_root,
    validate_checkpoint,
    validate_walk_forward_artifact,
)

ARTIFACT = ROOT / "artifacts" / "pit" / "protected_replay_dry_run.json"


def _row(row_id: str, cutoff: str, game_id: str, week: int, win_rate: float) -> dict[str, object]:
    return {
        "row_id": row_id,
        "target_game_id": game_id,
        "cutoff_utc": cutoff,
        "season": DEVELOPMENT_SEASON,
        "season_type": "regular",
        "week": week,
        "team_id": "team-a",
        "prior_games": 4,
        "prior_win_rate": win_rate,
        "prior_points_for_mean": 24.0,
        "prior_points_against_mean": 17.0,
        "lineage_sha256": "a" * 64,
        "missingness": "NONE",
    }


def _fold(index: int, rows: list[dict[str, object]]) -> dict[str, object]:
    cutoffs = [str(row["cutoff_utc"]) for row in rows]
    return {
        "fold_id": f"2023-regular-W{index + 1:02d}",
        "fold_index": index,
        "season": DEVELOPMENT_SEASON,
        "season_type": "regular",
        "week": index + 1,
        "min_cutoff_utc": min(cutoffs),
        "max_cutoff_utc": max(cutoffs),
        "rows": rows,
    }


class WalkForwardUnitTests(unittest.TestCase):
    def test_protected_accessor_denies_2024_and_2025(self) -> None:
        accessor = ProtectedOutcomeAccessor(
            ROOT,
            [
                {
                    "season": 2024,
                    "canonical_game_id": "g1",
                    "team_id": "t1",
                    "result": "WIN",
                    "points_for": 31,
                    "points_against": 14,
                }
            ],
        )
        with self.assertRaises(ProtectedOutcomeDenied):
            accessor.get_tuning_label(2024, "g1", "t1")
        with self.assertRaises(ProtectedOutcomeDenied):
            accessor.get_tuning_label(2025, "g2", "t2")

    def test_2023_label_absent_from_bat523_is_not_fabricated(self) -> None:
        accessor = ProtectedOutcomeAccessor(ROOT, [])
        with self.assertRaises(DevelopmentLabelUnavailable):
            accessor.get_tuning_label(2023, "g1", "t1")

    def test_fold_local_fitting_uses_only_earlier_rows(self) -> None:
        earlier = [_row("r1", "2023-09-01T00:00:00Z", "g1", 1, 0.25)]
        later = [_row("r2", "2023-09-08T00:00:00Z", "g2", 2, 0.80)]
        accessor = ProtectedOutcomeAccessor(ROOT, [])
        first = execute_fold(_fold(0, earlier), earlier + later, accessor)
        second = execute_fold(_fold(1, later), earlier + later, accessor)
        self.assertEqual(first["transform_kind"], "IDENTITY_NO_PRIOR_FOLD_ROWS")
        self.assertEqual(second["train_row_ids"], ["r1"])
        self.assertNotEqual(first["transform_identity"], second["transform_identity"])
        self.assertNotIn("r2", second["train_row_ids"])

    def test_target_game_row_cannot_enter_training(self) -> None:
        eval_row = _row("r-eval", "2023-09-08T00:00:00Z", "game-x", 2, 0.5)
        injected = _row("injected-same-game-prior", "2010-01-01T00:00:00Z", "game-x", 1, 0.9)
        result = execute_fold(_fold(1, [eval_row]), [injected], ProtectedOutcomeAccessor(ROOT, []))
        self.assertNotIn("injected-same-game-prior", result["train_row_ids"])
        self.assertNotIn("game-x", result["train_game_ids"])
        self.assertEqual(result["membership"]["game_id_intersection"], [])
        self.assertEqual(result["membership"]["row_id_intersection"], [])
        self.assertTrue(result["same_game_excluded"])
        self.assertEqual(result["membership"]["excluded_candidates"][0]["row_id"], "injected-same-game-prior")
        self.assertIn("SAME_GAME_EXCLUDED", result["membership"]["excluded_candidates"][0]["reasons"])

    def test_same_game_excluded_is_derived_from_observed_sets(self) -> None:
        eval_row = _row("r-eval", "2023-09-08T00:00:00Z", "game-x", 2, 0.5)
        earlier = _row("r-train", "2023-09-01T00:00:00Z", "game-y", 1, 0.4)
        result = execute_fold(_fold(1, [eval_row]), [earlier], ProtectedOutcomeAccessor(ROOT, []))
        self.assertTrue(result["same_game_excluded"])
        result["same_game_excluded"] = False
        self.assertFalse(result["same_game_excluded"])
        self.assertEqual(result["membership"]["game_id_intersection"], [])

    def test_target_game_exclusion_compares_games_to_games_and_rows_to_rows(self) -> None:
        eval_row = _row("r-eval", "2023-09-08T00:00:00Z", "game-x", 2, 0.5)
        earlier = _row("r-train", "2023-09-01T00:00:00Z", "game-y", 1, 0.4)
        proof = prove_target_game_exclusion(_fold(1, [eval_row]), [earlier], ProtectedOutcomeAccessor(ROOT, []))
        self.assertTrue(proof["pass"])
        self.assertTrue(proof["injected_row_excluded"])
        self.assertEqual(proof["leaked_game_ids"], [])
        self.assertEqual(proof["leaked_row_ids"], [])
        self.assertNotIn("game-x", proof["train_game_ids"])

    def test_stale_and_future_fitted_checkpoints_are_rejected(self) -> None:
        fold = _fold(0, [_row("r1", "2023-09-01T00:00:00Z", "g1", 1, 0.2)])
        proof = prove_stale_checkpoint_rejection(fold, run_identity="run", code_identity="code")
        self.assertTrue(proof["pass"])
        with self.assertRaises(CheckpointRejected):
            validate_checkpoint(
                {
                    "schema_version": CHECKPOINT_SCHEMA,
                    "run_identity": "run",
                    "dataset_identity": DATASET_IDENTITY,
                    "code_identity": "stale",
                    "fold_id": fold["fold_id"],
                    "fold_index": 0,
                    "train_cutoff_utc": fold["min_cutoff_utc"],
                    "fold_result": {},
                },
                run_identity="run",
                dataset_identity=DATASET_IDENTITY,
                code_identity="code",
                fold=fold,
            )

    def test_membership_proof_derives_same_game_from_game_and_row_sets(self) -> None:
        leaked = derive_membership_proof(
            [{"row_id": "train-1", "target_game_id": "game-x"}],
            [{"row_id": "eval-1", "target_game_id": "game-x"}],
        )
        self.assertEqual(leaked["game_id_intersection"], ["game-x"])
        self.assertFalse(leaked["same_game_excluded"])
        clean = derive_membership_proof(
            [{"row_id": "train-1", "target_game_id": "game-y"}],
            [{"row_id": "eval-1", "target_game_id": "game-x"}],
        )
        self.assertEqual(clean["game_id_intersection"], [])
        self.assertEqual(clean["row_id_intersection"], [])
        self.assertTrue(clean["same_game_excluded"])

    def test_identity_transform_on_empty_history(self) -> None:
        transform = fit_fold_local_transform([], train_cutoff_utc="2023-09-01T00:00:00Z")
        self.assertEqual(transform.kind, "IDENTITY_NO_PRIOR_FOLD_ROWS")
        self.assertEqual(transform.transform_row(_row("r", "2023-09-01T00:00:00Z", "g", 1, 0.4))["prior_win_rate"], 0.4)


class WalkForwardArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    def _rehash(self, payload: dict[str, object]) -> dict[str, object]:
        payload["artifact_identity"] = compute_artifact_identity(payload)
        return payload

    def test_artifact_validates_and_is_consumable_by_bat401(self) -> None:
        validate_walk_forward_artifact(self.payload, ROOT, require_payload_rebuild=bool(try_resolve_data_root(None, ROOT)))
        consumer = consume_for_bat401(self.payload)
        self.assertTrue(consumer["consumable"])
        self.assertTrue(consumer["protected_lane_still_closed"])
        self.assertEqual(self.payload["schema_version"], SCHEMA_VERSION)

    def test_chronological_real_2023_folds(self) -> None:
        folds = self.payload["folds"]
        self.assertGreaterEqual(len(folds), 15)
        self.assertEqual(sum(fold["eval_row_count"] for fold in folds), 1820)
        cutoffs = [fold["min_cutoff_utc"] for fold in folds]
        self.assertEqual(cutoffs, sorted(cutoffs))
        self.assertTrue(all(fold["season"] == 2023 for fold in folds))

    def test_fold_local_transforms_change_with_history(self) -> None:
        identities = [fold["transform_identity"] for fold in self.payload["folds"]]
        self.assertEqual(len(set(identities)), len(identities))
        self.assertEqual(self.payload["folds"][0]["transform_kind"], "IDENTITY_NO_PRIOR_FOLD_ROWS")
        self.assertGreater(self.payload["folds"][1]["train_row_count"], 0)

    def test_protected_outcomes_and_metrics_are_absent(self) -> None:
        self.assertTrue(self.payload["protected_outcomes_inaccessible"])
        self.assertFalse(self.payload["protected_metrics_produced"])
        self.assertEqual(self.payload["protected_evaluation_status"], "CLOSED")
        self.assertIsNone(self.payload["development_metrics"])
        self.assertFalse(self.payload["claims"]["protected_performance"])
        self.assertIn("Protected outcomes were inaccessible", self.payload["historical_filename_note"])

    def test_crash_resume_and_rerun_and_future_append(self) -> None:
        self.assertTrue(self.payload["proofs"]["crash_resume_equivalence"]["pass"])
        self.assertTrue(self.payload["proofs"]["deterministic_full_rerun"]["pass"])
        self.assertTrue(self.payload["proofs"]["future_append_invariance"]["pass"])
        self.assertTrue(self.payload["proofs"]["target_game_exclusion"]["pass"])
        self.assertTrue(self.payload["proofs"]["stale_checkpoint_rejection"]["pass"])

    def test_payload_identities_bind_bat523(self) -> None:
        self.assertEqual(self.payload["dataset_identity"], DATASET_IDENTITY)
        payloads = {row["name"]: row for row in self.payload["input_identities"]["payloads"]}
        for name, spec in REQUIRED_PAYLOADS.items():
            self.assertEqual(payloads[name]["sha256"], spec["sha256"])
            self.assertEqual(payloads[name]["rows"], spec["rows"])

    def test_forged_terminal_authority_is_rejected_after_rehash(self) -> None:
        forged = copy.deepcopy(self.payload)
        forged["status"] = "DONE"
        forged["remaining_blockers"] = ["NONE"]
        forged["downstream_eligibility"]["BAT-401"] = "READY"
        forged["acceptance_matrix"][0]["disposition"] = "FAIL"
        forged["protected_outcomes_inaccessible"] = False
        forged["artifact_identity"] = compute_artifact_identity(forged)
        with self.assertRaises(ValueError):
            validate_walk_forward_artifact(forged, ROOT)

    def test_forged_fold_evidence_is_rejected_after_rehash(self) -> None:
        forged = copy.deepcopy(self.payload)
        forged["folds"][2]["tuning_labels_used"] = ["fabricated-2023-label"]
        forged["artifact_identity"] = compute_artifact_identity(forged)
        with self.assertRaises(ValueError):
            validate_walk_forward_artifact(forged, ROOT)

    def test_acceptance_order_is_required(self) -> None:
        forged = copy.deepcopy(self.payload)
        forged["acceptance_matrix"] = list(reversed(forged["acceptance_matrix"]))
        forged["artifact_identity"] = compute_artifact_identity(forged)
        with self.assertRaises(ValueError):
            validate_walk_forward_artifact(forged, ROOT)
        self.assertEqual(
            [row["criterion"] for row in self.payload["acceptance_matrix"]],
            list(REQUIRED_ACCEPTANCE),
        )

    def test_derive_terminal_state_binds_blockers(self) -> None:
        failed = [{"criterion": name, "disposition": "FAIL" if name == "fold_local_fitting" else "PASS"} for name in REQUIRED_ACCEPTANCE]
        derived = derive_terminal_state(failed)
        self.assertEqual(derived["status"], "BLOCKED")
        self.assertEqual(derived["bat401"], "BLOCKED")
        self.assertIn("ACCEPTANCE_FAILED:fold_local_fitting", derived["remaining_blockers"])

    def test_forged_same_game_excluded_is_rejected_after_rehash(self) -> None:
        forged = self._rehash(copy.deepcopy(self.payload))
        forged["folds"][1]["same_game_excluded"] = False
        self._rehash(forged)
        with self.assertRaises(ValueError):
            validate_walk_forward_artifact(forged, ROOT, require_payload_rebuild=False)

    def test_forged_training_game_id_is_rejected_after_rehash(self) -> None:
        forged = copy.deepcopy(self.payload)
        eval_game = forged["folds"][1]["membership"]["eval"][0]["target_game_id"]
        forged["folds"][1]["membership"]["train"][0]["target_game_id"] = eval_game
        self._rehash(forged)
        with self.assertRaises(ValueError):
            validate_walk_forward_artifact(forged, ROOT, require_payload_rebuild=False)

    def test_forged_train_eval_membership_is_rejected_after_rehash(self) -> None:
        forged = copy.deepcopy(self.payload)
        stolen = copy.deepcopy(forged["folds"][1]["membership"]["eval"][0])
        forged["folds"][1]["membership"]["train"].append(stolen)
        self._rehash(forged)
        with self.assertRaises(ValueError):
            validate_walk_forward_artifact(forged, ROOT, require_payload_rebuild=False)

    def test_forged_cutoff_is_rejected_after_rehash(self) -> None:
        forged = copy.deepcopy(self.payload)
        forged["folds"][1]["min_cutoff_utc"] = "2099-01-01T00:00:00Z"
        self._rehash(forged)
        with self.assertRaises(ValueError):
            validate_walk_forward_artifact(forged, ROOT, require_payload_rebuild=False)

    def test_forged_transform_population_is_rejected_after_rehash(self) -> None:
        forged = copy.deepcopy(self.payload)
        forged["folds"][1]["train_row_count"] = int(forged["folds"][1]["train_row_count"]) + 7
        self._rehash(forged)
        with self.assertRaises(ValueError):
            validate_walk_forward_artifact(forged, ROOT, require_payload_rebuild=False)

    def test_forged_exclusion_evidence_is_rejected_after_rehash(self) -> None:
        forged = copy.deepcopy(self.payload)
        forged["folds"][1]["membership"]["excluded_candidates"] = [
            {"row_id": "forged", "target_game_id": "forged-game", "cutoff_utc": "2010-01-01T00:00:00Z", "reasons": []}
        ]
        self._rehash(forged)
        with self.assertRaises(ValueError):
            validate_walk_forward_artifact(forged, ROOT, require_payload_rebuild=False)

    def test_forged_bounded_identity_summary_is_rejected_after_rehash(self) -> None:
        forged = copy.deepcopy(self.payload)
        forged["folds"][1]["eval_row_ids"]["sha256"] = "0" * 64
        self._rehash(forged)
        with self.assertRaises(ValueError):
            validate_walk_forward_artifact(forged, ROOT, require_payload_rebuild=False)


if __name__ == "__main__":
    unittest.main()

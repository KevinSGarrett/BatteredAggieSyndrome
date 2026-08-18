from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aggie_analytics.experimentation.development_candidate_evidence_ledger import (  # noqa: E402
    ALLOWED_STATES,
    CANDIDATES,
    CONTRACT_ID,
    FORBIDDEN_STATES,
    LEDGER_RELATIVE,
    PASS_CLASSIFICATION,
    PASS_RESULT,
    LedgerValidationDenied,
    compute_fold_definition_identity,
    compute_ledger_identity,
    expected_ledger_document,
    expected_supersession,
    load_contract,
    validate_artifact,
)


def _synthetic_expected() -> dict[str, object]:
    contract = load_contract(ROOT)
    entries = [
        {
            "candidate": "prior_only",
            "state": "CORE_REFERENCE",
            "reason": "PREDECLARED_UNFITTED_PRIOR_REFERENCE",
            "team_row_metrics": {
                "abstained_folds": 0,
                "accuracy": 0.6,
                "brier": 0.25,
                "evaluated_folds": 2,
                "evaluated_rows": 10,
                "log_loss": 0.7,
                "margin_mae": 10.0,
            },
            "unique_game_metrics": {
                "abstained_folds": 0,
                "accuracy": 0.6,
                "brier": 0.26,
                "evaluated_folds": 2,
                "evaluated_rows": 5,
                "log_loss": 0.71,
                "margin_mae": 11.0,
            },
            "brier_delta_vs_prior_only": 0.0,
            "negative_result_preserved": True,
            "metrics_authority": "TEAM_ROW_BRIER",
            "unique_game_metrics_role": "SUPPORTING",
        },
        {
            "candidate": "prior_plus_play_drive",
            "state": "REJECTED_DEVELOPMENT",
            "reason": "PREDECLARED_BRIER_VS_PRIOR_ONLY",
            "team_row_metrics": {
                "abstained_folds": 1,
                "accuracy": 0.5,
                "brier": 0.27,
                "evaluated_folds": 1,
                "evaluated_rows": 8,
                "log_loss": 0.72,
                "margin_mae": 10.0,
            },
            "unique_game_metrics": {
                "abstained_folds": 1,
                "accuracy": 0.5,
                "brier": 0.28,
                "evaluated_folds": 1,
                "evaluated_rows": 4,
                "log_loss": 0.73,
                "margin_mae": 11.0,
            },
            "brier_delta_vs_prior_only": 0.02,
            "negative_result_preserved": True,
            "metrics_authority": "TEAM_ROW_BRIER",
            "unique_game_metrics_role": "SUPPORTING",
        },
        {
            "candidate": "prior_plus_rankings",
            "state": "REJECTED_DEVELOPMENT",
            "reason": "PREDECLARED_BRIER_VS_PRIOR_ONLY",
            "team_row_metrics": {
                "abstained_folds": 1,
                "accuracy": 0.5,
                "brier": 0.28,
                "evaluated_folds": 1,
                "evaluated_rows": 8,
                "log_loss": 0.74,
                "margin_mae": 10.0,
            },
            "unique_game_metrics": {
                "abstained_folds": 1,
                "accuracy": 0.5,
                "brier": 0.29,
                "evaluated_folds": 1,
                "evaluated_rows": 4,
                "log_loss": 0.75,
                "margin_mae": 11.0,
            },
            "brier_delta_vs_prior_only": 0.03,
            "negative_result_preserved": True,
            "metrics_authority": "TEAM_ROW_BRIER",
            "unique_game_metrics_role": "SUPPORTING",
        },
        {
            "candidate": "prior_plus_play_drive_plus_rankings",
            "state": "REJECTED_DEVELOPMENT",
            "reason": "PREDECLARED_BRIER_VS_BOTH_REFERENCES",
            "team_row_metrics": {
                "abstained_folds": 1,
                "accuracy": 0.5,
                "brier": 0.275,
                "evaluated_folds": 1,
                "evaluated_rows": 8,
                "log_loss": 0.73,
                "margin_mae": 10.0,
            },
            "unique_game_metrics": {
                "abstained_folds": 1,
                "accuracy": 0.5,
                "brier": 0.285,
                "evaluated_folds": 1,
                "evaluated_rows": 4,
                "log_loss": 0.74,
                "margin_mae": 11.0,
            },
            "brier_delta_vs_prior_only": 0.025,
            "negative_result_preserved": True,
            "metrics_authority": "TEAM_ROW_BRIER",
            "unique_game_metrics_role": "SUPPORTING",
        },
    ]
    return {
        "contract": contract,
        "parent_identities": {
            "BAT-527_rankings_feature": contract["expected_identities"]["bat527_rankings_feature_identity"],
            "BAT-527_rankings_run": contract["expected_identities"]["bat527_rankings_run_identity"],
            "BAT-527_rankings_state": contract["expected_identities"]["bat527_rankings_state_identity"],
            "BAT-565_label_dataset": contract["expected_identities"]["bat565_label_dataset_identity"],
            "BAT-566_gate": contract["expected_identities"]["bat566_gate_identity"],
            "BAT-566_matrix": contract["expected_identities"]["bat566_matrix_identity"],
            "BAT-566_replay": contract["expected_identities"]["bat566_replay_identity"],
            "BAT-568_gate": contract["expected_identities"]["bat568_gate_identity"],
            "BAT-568_joined_matrix": contract["expected_identities"]["bat568_joined_matrix_identity"],
            "BAT-568_run": contract["expected_identities"]["bat568_run_identity"],
            "protected_split_registry": contract["expected_identities"]["protected_split_registry_sha256"],
        },
        "bound_identities": {
            "bat565_label_dataset_identity": contract["expected_identities"]["bat565_label_dataset_identity"],
            "fold_definition_identity": "d" * 64,
        },
        "fold_definition_identity": "d" * 64,
        "cohort": {
            "fold_count": 16,
            "fold_definition_identity": "d" * 64,
            "protected_seasons_excluded": [2024, 2025],
            "season": 2023,
            "team_rows": 1820,
            "unique_games": 910,
        },
        "coverage": {
            "team_rows": 4,
            "unique_games": 2,
            "eligible_rankings_rows": 2,
            "missing_or_unlisted_rows": 2,
            "unresolved_identity_rows": 0,
        },
        "candidates": list(CANDIDATES),
        "entries": entries,
        "comparison_count": 4,
        "supersession": expected_supersession(contract),
        "code_identity": "c" * 64,
        "any_candidate_improved_brier_vs_prior_only": False,
        "uncertainty_reason": "DEVELOPMENT_ONLY_NO_STATISTICAL_TEST_NO_PROTECTED_REPLICATION",
    }


class DevelopmentCandidateLedgerUnitTests(unittest.TestCase):
    def test_contract_predeclares_four_candidates_and_forbidden_states(self) -> None:
        contract = load_contract(ROOT)
        self.assertEqual(contract["contract_id"], CONTRACT_ID)
        self.assertEqual(contract["new_issue_decision"], "CREATE")
        self.assertEqual(contract["required_candidates"], list(CANDIDATES))
        self.assertEqual(contract["allowed_states"], list(ALLOWED_STATES))
        self.assertEqual(contract["forbidden_states"], list(FORBIDDEN_STATES))
        self.assertFalse(contract["authority"]["protected_evaluation_admission"])
        self.assertFalse(contract["authority"]["champion_or_production_promotion"])
        self.assertFalse(contract["authority"]["production_feature_registry"])

    def test_fold_definition_identity_is_order_and_cutoff_sensitive(self) -> None:
        folds = [
            {
                "eval_row_count": 188,
                "eval_unique_games": 94,
                "first_fold_no_fit": True,
                "fold_evaluation_cutoff_utc": "2023-08-25T18:30:00Z",
                "fold_id": f"2023-regular-W{index:02d}",
                "fold_index": index,
                "max_cutoff_utc": "2023-08-25T18:30:00Z",
                "min_cutoff_utc": "2023-08-25T18:30:00Z",
                "season_type": "regular",
                "train_row_count": 0,
                "train_unique_games": 0,
                "week": index,
            }
            for index in range(1, 17)
        ]
        identity = compute_fold_definition_identity(folds)
        shifted = json.loads(json.dumps(folds))
        shifted[0]["fold_evaluation_cutoff_utc"] = "2023-08-26T18:30:00Z"
        self.assertNotEqual(identity, compute_fold_definition_identity(shifted))
        with self.assertRaises(LedgerValidationDenied):
            compute_fold_definition_identity(folds[:-1])


class DevelopmentCandidateLedgerMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.expected = _synthetic_expected()
        cls.ledger = expected_ledger_document(cls.expected)

    def _mutated(self, **changes: object) -> dict[str, object]:
        tampered = json.loads(json.dumps(self.ledger))
        tampered.update(changes)
        tampered["ledger_identity"] = compute_ledger_identity(tampered)
        return tampered

    def _reject(self, ledger: dict[str, object]) -> None:
        with self.assertRaises(LedgerValidationDenied):
            validate_artifact(repo_root=ROOT, ledger=ledger, expected=self.expected)

    def test_honest_synthetic_ledger_passes(self) -> None:
        validated = validate_artifact(repo_root=ROOT, ledger=self.ledger, expected=self.expected)
        self.assertEqual(validated["result"], "PASS")
        self.assertEqual(self.ledger["result"], PASS_RESULT)
        self.assertEqual(self.ledger["classification"], PASS_CLASSIFICATION)
        self.assertEqual(self.ledger["comparison_count"], 4)
        self.assertEqual(
            self.ledger["supersession"]["prior_ledger_identity"],
            "b24e5fe221d2974c3e6c4791b8a7851da370b99746ebfc8763ee97346043dd43",
        )
        self.assertEqual(self.ledger["supersession"]["ledger_generation"], 2)
        self.assertNotIn("PRODUCTION_CHAMPION", json.dumps(self.ledger["entries"]))

    def test_changed_metrics_are_rejected(self) -> None:
        entries = json.loads(json.dumps(self.ledger["entries"]))
        entries[2]["team_row_metrics"]["brier"] = 0.01
        self._reject(self._mutated(entries=entries))

    def test_changed_cohort_is_rejected(self) -> None:
        cohort = dict(self.ledger["cohort"])
        cohort["unique_games"] = 909
        self._reject(self._mutated(cohort=cohort))

    def test_omitted_negative_result_is_rejected(self) -> None:
        entries = json.loads(json.dumps(self.ledger["entries"]))
        entries[1]["brier_delta_vs_prior_only"] = -0.02
        entries[1]["negative_result_preserved"] = False
        self._reject(self._mutated(entries=entries))

    def test_hidden_candidate_is_rejected(self) -> None:
        self._reject(self._mutated(candidates=list(CANDIDATES)[:-1]))
        self._reject(self._mutated(candidates=list(CANDIDATES) + ["post_hoc"]))

    def test_altered_comparison_count_is_rejected(self) -> None:
        self._reject(self._mutated(comparison_count=3))

    def test_changed_decision_without_reason_is_rejected(self) -> None:
        entries = json.loads(json.dumps(self.ledger["entries"]))
        entries[2]["state"] = "RETAIN_DEVELOPMENT_CANDIDATE"
        entries[2]["reason"] = ""
        self._reject(self._mutated(entries=entries))

    def test_production_or_protected_authority_is_rejected(self) -> None:
        authority = dict(self.ledger["authority"])
        authority["champion_or_production_promotion"] = True
        self._reject(self._mutated(authority=authority))
        entries = json.loads(json.dumps(self.ledger["entries"]))
        entries[2]["state"] = "PRODUCTION_CHAMPION"
        entries[2]["reason"] = "FORGED"
        self._reject(self._mutated(entries=entries))

    def test_missing_supersession_record_is_rejected(self) -> None:
        self._reject(self._mutated(supersession={}))

    def test_forged_completion_after_identity_recompute_is_rejected(self) -> None:
        forged = self._mutated(result="FORGED_DONE", classification="PRODUCTION_CHAMPION")
        self.assertNotEqual(forged["ledger_identity"], self.ledger["ledger_identity"])
        self._reject(forged)


class DevelopmentCandidateLedgerLiveTests(unittest.TestCase):
    def test_committed_ledger_rebuilds_from_source_gates(self) -> None:
        path = ROOT / LEDGER_RELATIVE
        if not path.is_file():
            self.skipTest("development candidate ledger has not been materialized yet")
        validated = validate_artifact(repo_root=ROOT)
        self.assertEqual(validated["result"], "PASS")
        self.assertEqual(validated["comparison_count"], 4)
        ledger = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(ledger["cohort"]["team_rows"], 1820)
        self.assertEqual(ledger["cohort"]["unique_games"], 910)
        self.assertEqual(ledger["cohort"]["fold_count"], 16)
        self.assertEqual(ledger["protected_period_exclusions"], [2024, 2025])
        self.assertFalse(ledger["any_candidate_improved_brier_vs_prior_only"])
        self.assertEqual([entry["candidate"] for entry in ledger["entries"]], list(CANDIDATES))
        self.assertEqual(ledger["entries"][0]["state"], "CORE_REFERENCE")
        self.assertTrue(all(entry["negative_result_preserved"] for entry in ledger["entries"]))
        self.assertTrue(all(entry["state"] in ALLOWED_STATES for entry in ledger["entries"]))
        self.assertFalse(any(entry["state"] in FORBIDDEN_STATES for entry in ledger["entries"]))
        self.assertEqual(ledger["supersession"]["ledger_generation"], 2)
        self.assertEqual(
            ledger["supersession"]["prior_ledger_identity"],
            "b24e5fe221d2974c3e6c4791b8a7851da370b99746ebfc8763ee97346043dd43",
        )
        self.assertTrue(all(entry["unique_game_metrics_role"] == "SUPPORTING" for entry in ledger["entries"]))
        self.assertTrue(all(entry["metrics_authority"] == "TEAM_ROW_BRIER" for entry in ledger["entries"]))


if __name__ == "__main__":
    unittest.main()

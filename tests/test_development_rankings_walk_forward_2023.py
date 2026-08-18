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
    ProtectedOutcomeDenied,
    normalize_pair_probabilities as replay_normalize_pair_probabilities,
)
from aggie_analytics.experimentation.development_rankings_walk_forward_2023 import (  # noqa: E402
    CANDIDATES,
    CONTRACT_ID,
    PASS_CLASSIFICATION,
    PASS_RESULT,
    RankingsJoinDenied,
    compute_gate_identity,
    decide_candidates,
    expected_gate_document,
    expected_parent_identities,
    join_rankings,
    load_contract,
    normalize_pair_probabilities,
    rank_signal,
    validate_artifact,
    validate_ranking_row_semantics,
)


def _synthetic_expected() -> dict[str, object]:
    contract = load_contract(ROOT)
    metrics = {
        "prior_only": {
            "evaluated_rows": 10,
            "evaluated_folds": 2,
            "abstained_folds": 0,
            "accuracy": 0.5,
            "brier": 0.25,
            "log_loss": 0.7,
            "margin_mae": 10.0,
        },
        "prior_plus_play_drive": {
            "evaluated_rows": 8,
            "evaluated_folds": 1,
            "abstained_folds": 1,
            "accuracy": 0.5,
            "brier": 0.26,
            "log_loss": 0.71,
            "margin_mae": 10.0,
        },
        "prior_plus_rankings": {
            "evaluated_rows": 8,
            "evaluated_folds": 1,
            "abstained_folds": 1,
            "accuracy": 0.5,
            "brier": 0.24,
            "log_loss": 0.69,
            "margin_mae": 10.0,
        },
        "prior_plus_play_drive_plus_rankings": {
            "evaluated_rows": 8,
            "evaluated_folds": 1,
            "abstained_folds": 1,
            "accuracy": 0.5,
            "brier": 0.27,
            "log_loss": 0.72,
            "margin_mae": 10.0,
        },
    }
    unique = {f"unique_game_{name}": dict(block) for name, block in metrics.items()}
    coverage = {
        "team_rows": 4,
        "unique_games": 2,
        "ranking_state_counts": {
            "RANKED_NUMERIC": 1,
            "RECEIVING_VOTES": 1,
            "EXPLICITLY_UNRANKED": 0,
            "NOT_LISTED_IN_ELIGIBLE_POLL": 1,
            "NO_ELIGIBLE_POLL": 1,
            "UNRESOLVED_IDENTITY": 0,
        },
        "eligible_rankings_rows": 2,
        "missing_or_unlisted_rows": 2,
        "ranked_numeric_rows": 1,
        "receiving_votes_rows": 1,
        "explicitly_unranked_rows": 0,
        "no_eligible_poll_rows": 1,
        "unresolved_identity_rows": 0,
    }
    return {
        "contract": contract,
        "parent_identities": expected_parent_identities(contract),
        "joined_matrix_identity": "a" * 64,
        "code_identity": "b" * 64,
        "run_identity": "c" * 64,
        "fold_results": [{}, {}],
        "metrics": {**metrics, **unique},
        "comparisons": {
            "predeclared_candidate_count": 4,
            "brier_delta_vs_prior_only": {
                "prior_plus_play_drive": 0.01,
                "prior_plus_rankings": -0.01,
                "prior_plus_play_drive_plus_rankings": 0.02,
            },
            "brier_delta_vs_prior_plus_play_drive": {
                "prior_plus_rankings": -0.02,
                "prior_plus_play_drive_plus_rankings": 0.01,
            },
        },
        "candidate_decisions": decide_candidates(metrics),
        "coverage": coverage,
    }


class DevelopmentRankingsUnitTests(unittest.TestCase):
    def test_contract_predeclares_exactly_four_candidates(self) -> None:
        contract = load_contract(ROOT)
        self.assertEqual(contract["contract_id"], CONTRACT_ID)
        self.assertEqual(contract["new_issue_decision"], "CREATE")
        self.assertEqual(contract["candidates"], list(CANDIDATES))
        self.assertFalse(contract["transforms"]["unranked_as_26"])
        self.assertFalse(contract["authority"]["protected_evaluation_admission"])
        self.assertFalse(contract["authority"]["champion_or_production_promotion"])

    def test_unranked_is_not_encoded_as_26(self) -> None:
        self.assertEqual(rank_signal({"ranking_state": "EXPLICITLY_UNRANKED", "rank": None}), 0.0)
        self.assertEqual(rank_signal({"ranking_state": "NOT_LISTED_IN_ELIGIBLE_POLL", "rank": 26}), 0.0)
        self.assertEqual(rank_signal({"ranking_state": "RANKED_NUMERIC", "rank": 1}), (13.0 - 1.0) / 12.0)

    def test_bat568_reuses_bat566_pair_helper(self) -> None:
        self.assertIs(normalize_pair_probabilities, replay_normalize_pair_probabilities)

    def test_decision_rules_are_predeclared(self) -> None:
        metrics = {
            "prior_only": {"brier": 0.25},
            "prior_plus_play_drive": {"brier": 0.26},
            "prior_plus_rankings": {"brier": 0.24},
            "prior_plus_play_drive_plus_rankings": {"brier": 0.27},
        }
        decisions = decide_candidates(metrics)
        self.assertEqual(decisions["predeclared_candidate_count"], 4)
        self.assertEqual(decisions["decisions"]["prior_only"]["state"], "CORE_REFERENCE")
        self.assertEqual(decisions["decisions"]["prior_plus_play_drive"]["state"], "REJECTED_DEVELOPMENT")
        self.assertEqual(decisions["decisions"]["prior_plus_rankings"]["state"], "RETAIN_DEVELOPMENT_CANDIDATE")
        self.assertEqual(
            decisions["decisions"]["prior_plus_play_drive_plus_rankings"]["state"],
            "REJECTED_DEVELOPMENT",
        )


class DevelopmentRankingsMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
        cls.expected = _synthetic_expected()
        cls.gate = expected_gate_document(cls.expected)

    def _mutated(self, **changes: object) -> dict[str, object]:
        tampered = json.loads(json.dumps(self.gate))
        tampered.update(changes)
        tampered["gate_identity"] = compute_gate_identity(tampered)
        return tampered

    def _reject(self, gate: dict[str, object]) -> None:
        with self.assertRaises(ValueError):
            validate_artifact(
                data_root=self.data_root,
                repo_root=ROOT,
                require_rebuild=True,
                gate=gate,
                expected=self.expected,
            )

    def test_honest_synthetic_gate_passes(self) -> None:
        validated = validate_artifact(
            data_root=self.data_root,
            repo_root=ROOT,
            require_rebuild=True,
            gate=self.gate,
            expected=self.expected,
        )
        self.assertEqual(validated["result"], "PASS")
        self.assertEqual(self.gate["result"], PASS_RESULT)
        self.assertEqual(self.gate["classification"], PASS_CLASSIFICATION)

    def test_changed_metrics_are_rejected(self) -> None:
        metrics = json.loads(json.dumps(self.gate["metrics"]))
        metrics["prior_plus_rankings"]["brier"] = 0.01
        self._reject(self._mutated(metrics=metrics))

    def test_row_substitution_is_rejected(self) -> None:
        coverage = json.loads(json.dumps(self.gate["coverage"]))
        coverage["team_rows"] = int(coverage["team_rows"]) - 1
        self._reject(self._mutated(coverage=coverage))

    def test_candidate_omission_and_addition_are_rejected(self) -> None:
        self._reject(self._mutated(candidates=list(CANDIDATES)[:-1]))
        self._reject(self._mutated(candidates=list(CANDIDATES) + ["post_hoc"]))

    def test_promotion_authority_forgery_is_rejected(self) -> None:
        authority = dict(self.gate["authority"])
        authority["champion_or_production_promotion"] = True
        self._reject(self._mutated(authority=authority))

    def test_forged_completion_after_identity_recompute_is_rejected(self) -> None:
        forged = self._mutated(result="FORGED_DONE", classification="PRODUCTION_CHAMPION")
        self.assertNotEqual(forged["gate_identity"], self.gate["gate_identity"])
        self._reject(forged)

    def test_future_poll_and_protected_outcome_are_rejected(self) -> None:
        feature = {
            "row_id": "row-a",
            "target_game_id": "game-a",
            "team_id": "team-a",
            "season": 2023,
            "cutoff_utc": "2023-09-01T00:00:00Z",
            "target_start_utc": "2023-09-02T00:00:00Z",
        }
        label = {"row_id": "row-a", "result": "WIN", "margin": 7, "label_available_after_utc": "2023-09-03T00:00:00Z"}
        ranking = {
            "target_game_id": "game-a",
            "canonical_team_id": "team-a",
            "season": 2023,
            "rank_state": "RANKED",
            "rank": 4,
            "poll_first_eligible_at_utc": "2023-09-10T00:00:00Z",
            "missingness_disposition": "OBSERVED_SOURCE_ROW",
            "poll_available": True,
            "team_listed_in_poll": True,
        }
        with self.assertRaises(RankingsJoinDenied):
            join_rankings(
                feature_rows=[feature],
                label_rows=[label],
                rankings_rows=[ranking],
                feature_identity="0" * 64,
                feature_payload_sha256="1" * 64,
            )
        protected = dict(feature)
        protected["season"] = 2024
        with self.assertRaises((RankingsJoinDenied, ProtectedOutcomeDenied)):
            join_rankings(
                feature_rows=[protected],
                label_rows=[label],
                rankings_rows=[ranking],
                feature_identity="0" * 64,
                feature_payload_sha256="1" * 64,
            )
        swapped = dict(ranking)
        swapped["canonical_team_id"] = "team-b"
        with self.assertRaises(RankingsJoinDenied):
            join_rankings(
                feature_rows=[feature],
                label_rows=[label],
                rankings_rows=[swapped],
                feature_identity="0" * 64,
                feature_payload_sha256="1" * 64,
            )


def _ranking_fixture(**overrides: object) -> dict[str, object]:
    row = {
        "target_game_id": "game-a",
        "canonical_team_id": "team-a",
        "season": 2023,
        "rank_state": "RANKED",
        "rank": 4,
        "poll_first_eligible_at_utc": "2023-09-01T00:00:00Z",
        "missingness_disposition": "OBSERVED_SOURCE_ROW",
        "poll_available": True,
        "team_listed_in_poll": True,
    }
    row.update(overrides)
    return row


def _join_ranking(**overrides: object) -> None:
    feature = {
        "row_id": "row-a",
        "target_game_id": "game-a",
        "team_id": "team-a",
        "season": 2023,
        "cutoff_utc": "2023-09-10T00:00:00Z",
        "target_start_utc": "2023-09-11T00:00:00Z",
    }
    label = {
        "row_id": "row-a",
        "result": "WIN",
        "margin": 7,
        "label_available_after_utc": "2023-09-12T00:00:00Z",
    }
    join_rankings(
        feature_rows=[feature],
        label_rows=[label],
        rankings_rows=[_ranking_fixture(**overrides)],
        feature_identity="0" * 64,
        feature_payload_sha256="1" * 64,
    )


class DevelopmentRankingsSemanticsTests(unittest.TestCase):
    def _reject(self, **overrides: object) -> None:
        with self.assertRaises(RankingsJoinDenied):
            validate_ranking_row_semantics(_ranking_fixture(**overrides), cutoff_utc="2023-09-10T00:00:00Z")
        with self.assertRaises(RankingsJoinDenied):
            _join_ranking(**overrides)

    def test_rank_zero(self) -> None:
        self._reject(rank=0)

    def test_negative_rank(self) -> None:
        self._reject(rank=-1)

    def test_unranked_as_26(self) -> None:
        self._reject(rank=26)

    def test_rank_above_25(self) -> None:
        self._reject(rank=27)

    def test_fractional_rank(self) -> None:
        self._reject(rank=4.5)

    def test_nan_rank(self) -> None:
        self._reject(rank=math.nan)

    def test_inf_rank(self) -> None:
        self._reject(rank=math.inf)

    def test_rank_on_receiving_votes(self) -> None:
        self._reject(rank_state="RECEIVING_VOTES", rank=12)

    def test_rank_on_not_ranked(self) -> None:
        self._reject(rank_state="NOT_RANKED", rank=12)

    def test_ranked_null_rank(self) -> None:
        self._reject(rank=None)

    def test_ranked_null_eligible_timestamp(self) -> None:
        self._reject(poll_first_eligible_at_utc=None)

    def test_receiving_votes_null_eligible_timestamp(self) -> None:
        self._reject(rank_state="RECEIVING_VOTES", rank=None, poll_first_eligible_at_utc=None)

    def test_explicitly_unranked_null_eligible_timestamp(self) -> None:
        self._reject(rank_state="NOT_RANKED", rank=None, poll_first_eligible_at_utc=None)

    def test_not_listed_null_eligible_timestamp(self) -> None:
        self._reject(
            rank_state="NOT_LISTED_OR_NO_ELIGIBLE_POLL",
            missingness_disposition="TEAM_NOT_LISTED_IN_LATEST_ELIGIBLE_POLL",
            rank=None,
            poll_first_eligible_at_utc=None,
            team_listed_in_poll=False,
        )

    def test_no_eligible_poll_with_timestamp(self) -> None:
        self._reject(
            rank_state="NOT_LISTED_OR_NO_ELIGIBLE_POLL",
            missingness_disposition="NO_POLL_ELIGIBLE_AT_TARGET_CUTOFF",
            rank=None,
            poll_available=False,
            team_listed_in_poll=False,
            poll_first_eligible_at_utc="2023-09-01T00:00:00Z",
        )

    def test_no_poll_with_poll_available_true(self) -> None:
        self._reject(
            rank_state="NOT_LISTED_OR_NO_ELIGIBLE_POLL",
            missingness_disposition="NO_POLL_ELIGIBLE_AT_TARGET_CUTOFF",
            rank=None,
            poll_first_eligible_at_utc=None,
            poll_available=True,
            team_listed_in_poll=False,
        )

    def test_observed_with_poll_available_false(self) -> None:
        self._reject(poll_available=False)

    def test_team_not_listed_with_poll_available_false(self) -> None:
        self._reject(
            rank_state="NOT_LISTED_OR_NO_ELIGIBLE_POLL",
            missingness_disposition="TEAM_NOT_LISTED_IN_LATEST_ELIGIBLE_POLL",
            rank=None,
            poll_available=False,
            team_listed_in_poll=False,
        )

    def test_poll_unavailable_with_timestamp(self) -> None:
        self._reject(
            rank_state="RECEIVING_VOTES",
            rank=None,
            missingness_disposition="",
            poll_available=False,
            poll_first_eligible_at_utc="2023-09-01T00:00:00Z",
        )

    def test_observed_with_team_not_listed_false(self) -> None:
        self._reject(team_listed_in_poll=False)

    def test_team_not_listed_with_team_listed_true(self) -> None:
        self._reject(
            rank_state="NOT_LISTED_OR_NO_ELIGIBLE_POLL",
            missingness_disposition="TEAM_NOT_LISTED_IN_LATEST_ELIGIBLE_POLL",
            rank=None,
            team_listed_in_poll=True,
        )

    def test_no_poll_with_team_listed_true(self) -> None:
        self._reject(
            rank_state="NOT_LISTED_OR_NO_ELIGIBLE_POLL",
            missingness_disposition="NO_POLL_ELIGIBLE_AT_TARGET_CUTOFF",
            rank=None,
            poll_first_eligible_at_utc=None,
            poll_available=False,
            team_listed_in_poll=True,
        )

    def test_rank_without_team_listed(self) -> None:
        self._reject(missingness_disposition="", team_listed_in_poll=False)


class DevelopmentRankingsLiveTests(unittest.TestCase):
    def test_live_rebuild_when_payloads_present(self) -> None:
        data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
        contract = load_contract(ROOT)
        feature = (
            data_root
            / "features"
            / "development_2023_matrix"
            / "sha256"
            / contract["input_identities"]["bat566_matrix_identity"]
            / "development_2023_matrix_features.parquet"
        )
        rankings = (
            data_root
            / "features"
            / "historical_rankings"
            / "sha256"
            / "b165e076222104d71f345cf294d5b177d2c049bf1168b11c29e9cc5690375274"
            / "rankings_pit_features.parquet"
        )
        try:
            import polars  # noqa: F401
        except ImportError:
            self.skipTest("optional data-engineering environment is not mounted")
        if not feature.is_file() or not rankings.is_file():
            self.skipTest("corrected BAT-566 or BAT-527 payloads are not mounted")
        from aggie_analytics.experimentation.development_rankings_walk_forward_2023 import (
            rebuild_expected,
        )

        expected = rebuild_expected(data_root=data_root, repo_root=ROOT)
        self.assertEqual(expected["coverage"]["team_rows"], 1820)
        self.assertEqual(expected["coverage"]["unique_games"], 910)
        self.assertEqual(expected["candidate_decisions"]["predeclared_candidate_count"], 4)
        gate = ROOT / "artifacts" / "pit" / "development_rankings_walk_forward_2023.json"
        if not gate.is_file():
            self.skipTest("rankings walk-forward gate has not been materialized yet")
        validated = validate_artifact(data_root=data_root, repo_root=ROOT, require_rebuild=True)
        self.assertEqual(validated["result"], "PASS")


if __name__ == "__main__":
    unittest.main()

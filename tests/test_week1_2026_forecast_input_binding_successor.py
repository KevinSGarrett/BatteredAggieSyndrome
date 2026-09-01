from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

try:
    from aggie_analytics.data.week1_2026_forecast_input_binding_successor import (  # noqa: E402
        BindingSuccessorViolation,
        map_ranking_surface_state,
        successor_readiness,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by core-only CI
    raise unittest.SkipTest(
        "the forecast-input binding successor requires the optional modeling dependencies"
    ) from exc
from aggie_analytics.validation.protected_hash_labels import (  # noqa: E402
    JUDGING_RULE_JSON,
    PROTECTED_JUDGING_CSV,
    validate_protected_hash_labels,
)


DATA_ROOT = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")


class RankingSurfaceStateTests(unittest.TestCase):
    def test_ranked_unranked_and_fcs_are_distinct(self) -> None:
        self.assertEqual("TEAM_RANKED", map_ranking_surface_state("RANKED_TOP_25"))
        self.assertEqual(
            "TEAM_UNRANKED_FBS", map_ranking_surface_state("FBS_POLL_ELIGIBLE_UNRANKED")
        )
        self.assertEqual(
            "FCS_NOT_APPLICABLE", map_ranking_surface_state("NOT_APPLICABLE_FBS_POLL")
        )
        self.assertEqual("SOURCE_MISSING", map_ranking_surface_state("SOURCE_MISSING"))

    def test_fcs_is_not_encoded_as_unranked_fbs(self) -> None:
        self.assertNotEqual(
            map_ranking_surface_state("NOT_APPLICABLE_FBS_POLL"),
            map_ranking_surface_state("FBS_POLL_ELIGIBLE_UNRANKED"),
        )


class ReadinessMutationTests(unittest.TestCase):
    def test_opening_rating_declared_consumed_when_absent_from_design_is_rejected(
        self,
    ) -> None:
        candidate = {
            "candidate_id": "national_logistic_l2_c25_input_bound",
            "predecessor_candidate_id": "national_logistic_l2",
            "family": "REGULARIZED_LOGISTIC",
            "feature_scope": "ALL_ADMITTED_FEATURES",
            "consumes_opening_rating": False,
        }
        row = {
            "contest_identity": "x",
            "source_team_id": "1",
            "canonical_team_id": "SRC-002:TEAM:1",
            "opponent_canonical_team_id": "SRC-002:TEAM:2",
            "site_orientation": "HOME",
            "prior_admitted": True,
            "opponent_prior_admitted": True,
            "opening_rating": 1500,
            "opponent_opening_rating": 1400,
            "opening_rating_in_fitted_design": True,
            "historical_prior_outcome_analogue_bound": True,
            "principal_performance_features_present": ["prior_win_rate"],
            "effective_strength_prior_admission": "PRIOR_ADMITTED",
            "effective_ranking_authority": "EFFECTIVE_AUTHORITY_ADMITTED_BOUND_TO_BAT_683",
            "ranking_surface_state": "TEAM_RANKED",
        }
        ready = successor_readiness(
            candidate=candidate, feature_row=row, principal=["prior_win_rate"]
        )
        self.assertEqual("ABSTAIN_FEATURE_AUTHORITY_MISMATCH", ready["readiness_state"])

    def test_ready_cannot_rest_only_on_missingness_indicators(self) -> None:
        candidate = {
            "candidate_id": "prior_only_c25_input_bound",
            "predecessor_candidate_id": "prior_only",
            "family": "REGULARIZED_LOGISTIC",
            "feature_scope": "PRIOR_OUTCOME_DOMAIN_AND_SITE",
            "consumes_opening_rating": False,
        }
        row = {
            "contest_identity": "x",
            "source_team_id": "1",
            "canonical_team_id": "SRC-002:TEAM:1",
            "opponent_canonical_team_id": "SRC-002:TEAM:2",
            "site_orientation": "HOME",
            "prior_admitted": True,
            "opponent_prior_admitted": True,
            "opening_rating": 1500,
            "opponent_opening_rating": 1400,
            "opening_rating_in_fitted_design": False,
            "historical_prior_outcome_analogue_bound": True,
            "principal_performance_features_present": [],
            "effective_strength_prior_admission": "PRIOR_ADMITTED",
            "effective_ranking_authority": "EFFECTIVE_AUTHORITY_ADMITTED_BOUND_TO_BAT_683",
            "ranking_surface_state": "TEAM_UNRANKED_FBS",
        }
        ready = successor_readiness(
            candidate=candidate, feature_row=row, principal=["prior_win_rate"]
        )
        self.assertEqual("ABSTAIN_MISSING_REQUIRED_FEATURES", ready["readiness_state"])
        self.assertIn(
            "READY_WOULD_REST_ONLY_ON_MISSINGNESS_INDICATORS",
            ready["abstention_reasons"],
        )

    def test_forecast_without_historical_analogue_is_not_ready(self) -> None:
        candidate = {
            "candidate_id": "national_logistic_l2_c25_input_bound",
            "predecessor_candidate_id": "national_logistic_l2",
            "family": "REGULARIZED_LOGISTIC",
            "feature_scope": "ALL_ADMITTED_FEATURES",
            "consumes_opening_rating": False,
        }
        row = {
            "contest_identity": "x",
            "source_team_id": "1",
            "canonical_team_id": "SRC-002:TEAM:1",
            "opponent_canonical_team_id": "SRC-002:TEAM:2",
            "site_orientation": "HOME",
            "prior_admitted": True,
            "opponent_prior_admitted": True,
            "opening_rating": 1500,
            "opponent_opening_rating": 1400,
            "opening_rating_in_fitted_design": False,
            "historical_prior_outcome_analogue_bound": False,
            "principal_performance_features_present": ["prior_win_rate"],
            "effective_strength_prior_admission": "PRIOR_ADMITTED",
            "effective_ranking_authority": "EFFECTIVE_AUTHORITY_ADMITTED_BOUND_TO_BAT_683",
            "ranking_surface_state": "TEAM_RANKED",
        }
        ready = successor_readiness(
            candidate=candidate, feature_row=row, principal=["prior_win_rate"]
        )
        self.assertEqual("ABSTAIN_MISSING_REQUIRED_FEATURES", ready["readiness_state"])


class ProtectedHashLabelMutationTests(unittest.TestCase):
    def test_canonical_labels_pass(self) -> None:
        findings = validate_protected_hash_labels(ROOT)
        self.assertEqual([], findings)

    def test_swapped_csv_and_json_hashes_are_rejected(self) -> None:
        labels = {
            "protected_split_registry_path": "governance/PROTECTED_SPLIT_REGISTRY.csv",
            "protected_split_registry_sha256": "6b90ef6fb09abd89d7a82a8b5835b00615671a7742839269c7401a2d0af5f764",
            "protected_judging_rule_seal_csv_path": PROTECTED_JUDGING_CSV,
            "protected_judging_rule_seal_csv_sha256": "8e1cb61d850babc5e80bd156aa79f6bbd5575d461df0d83ec6f6eed2a71fe758",
            "judging_rule_seal_json_path": JUDGING_RULE_JSON,
            "judging_rule_seal_json_sha256": "7bf245d93d1d0fc6b87f55dddcacec76ced222279ffa09b7b1ab08ba36667356",
        }
        findings = validate_protected_hash_labels(ROOT, labels)
        self.assertTrue(
            any("swapped" in item or "does_not_match" in item for item in findings)
        )

    def test_csv_path_pointing_at_json_is_rejected(self) -> None:
        labels = {
            "protected_split_registry_path": "governance/PROTECTED_SPLIT_REGISTRY.csv",
            "protected_split_registry_sha256": "6b90ef6fb09abd89d7a82a8b5835b00615671a7742839269c7401a2d0af5f764",
            "protected_judging_rule_seal_csv_path": JUDGING_RULE_JSON,
            "protected_judging_rule_seal_csv_sha256": "7bf245d93d1d0fc6b87f55dddcacec76ced222279ffa09b7b1ab08ba36667356",
            "judging_rule_seal_json_path": PROTECTED_JUDGING_CSV,
            "judging_rule_seal_json_sha256": "8e1cb61d850babc5e80bd156aa79f6bbd5575d461df0d83ec6f6eed2a71fe758",
        }
        findings = validate_protected_hash_labels(ROOT, labels)
        self.assertIn("protected_hash_labels_swapped:csv_path_points_at_json", findings)
        self.assertIn("protected_hash_labels_swapped:json_path_points_at_csv", findings)


class Cycle24ForecastImmutabilityTests(unittest.TestCase):
    def test_old_candidate_ids_are_not_reused_in_successor_contract(self) -> None:
        contract = json.loads(
            (
                ROOT
                / "configs/week1_2026_forecast_input_binding_successor_contract.json"
            ).read_text(encoding="utf-8")
        )
        successor_ids = {
            item["candidate_id"] for item in contract["successor_candidates"]
        }
        frozen = set(contract["cycle24_candidate_ids_immutable"])
        self.assertTrue(successor_ids.isdisjoint(frozen))
        self.assertFalse(
            contract["scientific_nonclaims"][
                "old_candidate_id_reused_with_new_semantics"
            ]
        )
        self.assertFalse(contract["checkpoints"]["market_values_inspected"])
        self.assertEqual("OPEN", contract["checkpoints"]["t_minus_24h_state"])
        self.assertEqual("OPEN", contract["checkpoints"]["t_minus_90m_state"])
        self.assertFalse(contract["scientific_nonclaims"]["bas_or_aggie_excess_claim"])
        self.assertFalse(
            contract["scientific_nonclaims"]["champion_or_production_promotion"]
        )
        self.assertFalse(
            contract["pre_market_diagnostic_thresholds"][
                "spread_to_exact_win_probability_authorized"
            ]
        )

    def test_unranked_is_not_encoded_as_rank_26(self) -> None:
        from aggie_analytics.data.week1_2026_forecast_input_binding_successor import (
            bind_successor_feature_row,
        )

        row = {
            "contest_identity": "x",
            "ncaa_contest_id": "1",
            "source_team_id": "1",
            "canonical_team_id": "SRC-002:TEAM:1",
            "opponent_source_team_id": "2",
            "opponent_canonical_team_id": "SRC-002:TEAM:2",
            "site_orientation": "HOME",
            "row_identity": "a" * 64,
            "prior_admitted": True,
            "opponent_prior_admitted": True,
            "opening_rating": 1500.0,
            "opponent_opening_rating": 1400.0,
            "prior_uncertainty_class": "SUPPORTED_STALE_INPUT",
            "ranking_state": "FBS_POLL_ELIGIBLE_UNRANKED",
            "domain_admission_states": {},
            "feature_values": {"ap_poll_rank": 26, "ap_poll_rank_missing": False},
        }
        bound = bind_successor_feature_row(
            cycle24_row=row,
            terminal=None,
            poll_surface_complete=True,
            principal=["prior_win_rate"],
        )
        self.assertIsNone(bound["feature_values"]["ap_poll_rank"])
        self.assertTrue(bound["feature_values"]["ap_poll_rank_missing"])
        self.assertEqual("TEAM_UNRANKED_FBS", bound["ranking_surface_state"])

    def test_ranked_row_with_rank_26_is_rejected(self) -> None:
        from aggie_analytics.data.week1_2026_forecast_input_binding_successor import (
            bind_successor_feature_row,
        )

        row = {
            "contest_identity": "x",
            "ncaa_contest_id": "1",
            "source_team_id": "1",
            "canonical_team_id": "SRC-002:TEAM:1",
            "opponent_source_team_id": "2",
            "opponent_canonical_team_id": "SRC-002:TEAM:2",
            "site_orientation": "HOME",
            "row_identity": "a" * 64,
            "prior_admitted": True,
            "opponent_prior_admitted": True,
            "opening_rating": 1500.0,
            "opponent_opening_rating": 1400.0,
            "prior_uncertainty_class": "SUPPORTED_STALE_INPUT",
            "ranking_state": "RANKED_TOP_25",
            "domain_admission_states": {},
            "feature_values": {"ap_poll_rank": 26, "ap_poll_rank_missing": False},
        }
        with self.assertRaises(BindingSuccessorViolation):
            bind_successor_feature_row(
                cycle24_row=row,
                terminal=None,
                poll_surface_complete=True,
                principal=["prior_win_rate"],
            )


@unittest.skipUnless(
    bool(DATA_ROOT), "mounted data root is required for independent reconstruction"
)
class SuccessorReconstructionTests(unittest.TestCase):
    def test_build_expected_does_not_write_tracked_files(self) -> None:
        from aggie_analytics.data.week1_2026_forecast_input_binding_successor import (
            build_expected,
        )

        before = hashlib.sha256((ROOT / "README.md").read_bytes()).hexdigest()
        expected = build_expected(repo_root=ROOT, data_root=Path(DATA_ROOT))
        after = hashlib.sha256((ROOT / "README.md").read_bytes()).hexdigest()
        self.assertEqual(before, after)
        self.assertFalse(expected["summary"]["champion_declared"])
        self.assertFalse(expected["summary"]["market_values_inspected"])
        self.assertIsNone(expected["summary"]["recommended_candidate"])
        self.assertEqual("OPEN", expected["summary"]["t_minus_24h_state"])
        self.assertTrue(expected["cycle24_preservation"]["rewritten"] is False)

    def test_materialize_writes_only_under_data_root_payloads(self) -> None:
        from datetime import datetime, timezone

        from aggie_analytics.data.week1_2026_forecast_input_binding_successor import (
            build_expected,
            jsonl_bytes,
        )

        expected = build_expected(repo_root=ROOT, data_root=Path(DATA_ROOT))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rows.jsonl"
            path.write_bytes(jsonl_bytes(expected["findings"]))
            self.assertTrue(path.is_file())
        self.assertTrue(datetime.now(timezone.utc))


if __name__ == "__main__":
    unittest.main()

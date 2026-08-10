import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HistoricalKnownAtRecoveryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(
            (ROOT / "configs" / "historical_known_at_recovery_contract.json").read_text(encoding="utf-8")
        )
        cls.registry = json.loads(
            (ROOT / "jira" / "reconciliation" / "BAT_AUXILIARY_ISSUE_REGISTRY.json").read_text(
                encoding="utf-8"
            )
        )
        cls.evidence = json.loads(
            (
                ROOT
                / "artifacts"
                / "jira_evidence"
                / "POST-TASK-HISTORICAL-KNOWN-AT-RECOVERY-001.json"
            ).read_text(encoding="utf-8")
        )
        cls.gate = json.loads(
            (ROOT / "artifacts" / "pit" / "historical_known_at_replay_gate.json").read_text(
                encoding="utf-8"
            )
        )

    def test_live_unit_identity_and_dependency_are_registered(self) -> None:
        item = next(row for row in self.registry["issues"] if row["jira_key"] == "BAT-523")
        self.assertEqual(item["local_id"], "POST-TASK-HISTORICAL-KNOWN-AT-RECOVERY-001")
        self.assertEqual(item["status"], "In Progress")
        self.assertTrue(item["critical_path"])
        self.assertEqual(self.contract["dependency_contract"]["blocks"], ["BAT-399"])
        self.assertEqual(self.contract["dependency_contract"]["relates_to"], ["BAT-398"])

    def test_recovery_cannot_fabricate_historical_knowledge_time(self) -> None:
        prohibited = set(self.contract["prohibited_substitutions"])
        self.assertIn("retrieval_time_as_historical_known_at", prohibited)
        self.assertIn("model_generated_timestamp", prohibited)
        self.assertFalse(self.evidence["contract"]["fabricated_known_at_permitted"])

    def test_domain_eligibility_is_independent_and_tiered(self) -> None:
        dimensions = set(self.contract["eligibility_dimensions"])
        self.assertIn("domain_and_data_grain", dimensions)
        self.assertIn("historical_known_at_and_point_in_time_eligibility", dimensions)
        self.assertGreaterEqual(len(self.contract["domain_tiers"]), 4)
        self.assertIn("Partial or failed domains remain explicit", " ".join(self.contract["acceptance_criteria"]))

    def test_protected_gate_requires_nonempty_replayable_evidence(self) -> None:
        self.assertEqual(
            self.contract["dependency_contract"]["required_reexecution_order"],
            ["BAT-395", "BAT-396", "BAT-397", "BAT-398"],
        )
        criteria = " ".join(self.contract["acceptance_criteria"])
        self.assertIn("At least one real game and prediction cutoff", criteria)
        self.assertIn("explicitly approves the new matrix", criteria)
        self.assertFalse(self.contract["honesty_boundary"]["historical_population_ready"])

    def test_bulk_artifacts_remain_external_and_openai_has_no_authority(self) -> None:
        storage = self.contract["external_storage"]
        self.assertEqual(storage["data_root"], "<external-data-root>")
        self.assertFalse(storage["bulk_payloads_in_git"])
        self.assertTrue(storage["content_addressed_captures_required"])
        self.assertFalse(self.contract["openai_assistance"]["direct_canonical_or_pit_authority"])

    def test_expanded_scoped_replay_is_validated_and_not_full_history(self) -> None:
        replay = self.contract["latest_validated_replay"]
        self.assertEqual(
            replay["dataset_identity"],
            "cf732b78db6deff2e2cca51364a18e03219a5ceda88d2f5efa475dad1f7e3fe7",
        )
        self.assertEqual(replay["source_seasons"], list(range(2010, 2023)))
        self.assertEqual(replay["accepted_game_outcomes"], 10593)
        self.assertEqual(replay["accepted_team_observations"], 21186)
        self.assertEqual(replay["matrix_rows"], 5528)
        self.assertEqual(replay["matrix_cells"], 22112)
        self.assertEqual(replay["rows_source_missing"], 14)
        self.assertEqual(replay["target_game_outcome_used_rows"], 0)
        self.assertEqual(
            replay["gate_disposition"],
            "APPROVE_EXPANDED_SCOPED_TEAM_OUTCOME_CONTEXT_FOR_PIPELINE_INTEGRATION",
        )
        self.assertEqual(
            replay["full_historical_population_disposition"],
            "BLOCKED_OTHER_DOMAINS_AND_COVERAGE_GATES_INCOMPLETE",
        )
        self.assertEqual(
            replay["preserved_prior_replay"]["dataset_identity"],
            "c8e7cd7bdc7fd0fb68af85756969c35c43ec61fa7cf1aa11f9d83b0a833fe93a",
        )
        self.assertFalse(self.evidence["completion_claim"]["full_historical_population_ready"])
        self.assertFalse(self.evidence["completion_claim"]["protected_model_promotion_eligible"])

    def test_reexecuted_gate_preserves_quarantine_and_scoped_authority(self) -> None:
        gate = self.gate
        self.assertEqual(gate["gate_reexecution"]["BAT-395"]["accepted_game_rows"], 10593)
        self.assertEqual(gate["gate_reexecution"]["BAT-395"]["quarantined_rows"], 570)
        self.assertEqual(gate["gate_reexecution"]["BAT-397"]["rows_source_missing"], 14)
        self.assertEqual(gate["chronological_replay"]["source_seasons"], list(range(2010, 2023)))
        self.assertFalse(gate["chronological_replay"]["target_labels_used"])
        self.assertIn("production_matrix_approval", gate["gate_reexecution"]["BAT-398"])
        self.assertEqual(gate["gate_reexecution"]["BAT-398"]["production_matrix_approval"], "NOT_APPROVED")

    def test_event_detail_play_history_is_validated_candidate_only(self) -> None:
        event = self.contract["latest_validated_event_detail_candidate"]
        self.assertEqual(
            event["dataset_identity"],
            "714a856691a84bac8f822091a98bb8ef68f2473edd1924abd94b8c5045c3cfc5",
        )
        self.assertEqual(event["repository_rows"], 2432416)
        self.assertEqual(event["repository_seasons"], [2004, 2005, 2006, 2007, 2008, 2009, 2010, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2021, 2022])
        self.assertEqual(event["absent_repository_seasons"], [2011, 2020])
        self.assertEqual(event["cross_route_exact_canonical_game_candidates"], 1606094)
        self.assertEqual(event["admission_state"], "CANDIDATE_NOT_ADMITTED")
        self.assertEqual(event["validation_checks_passed"], 29)
        self.assertEqual(event["mutation_controls_passed"], 9)
        self.assertEqual(event["deterministic_payloads_compared"], 17)
        self.assertFalse(self.evidence["completion_claim"]["event_detail_canonical_or_pit_admission"])
        checkpoint = self.gate["parallel_event_detail_checkpoint"]
        self.assertEqual(checkpoint["admission_state"], "CANDIDATE_NOT_ADMITTED")
        self.assertIn("PENDING", checkpoint["gate_disposition"])

    def test_drive_history_is_validated_candidate_only(self) -> None:
        drive = self.contract["latest_validated_drive_detail_candidate"]
        self.assertEqual(
            drive["dataset_identity"],
            "342be676be8a01ce00677a872e06fda73e607b26116ec971f09f5966d21891d0",
        )
        self.assertEqual(drive["repository_drive_rows"], 351990)
        self.assertEqual(drive["source_play_rows"], 2432416)
        self.assertEqual(drive["source_play_rows_without_drive_id"], 1148)
        self.assertEqual(drive["cross_route_exact_canonical_game_candidates"], 336506)
        self.assertEqual(drive["admission_state"], "CANDIDATE_NOT_ADMITTED")
        self.assertEqual(drive["validation_checks_passed"], 30)
        self.assertEqual(drive["mutation_controls_passed"], 9)
        self.assertEqual(drive["deterministic_payloads_compared"], 17)
        self.assertFalse(self.evidence["completion_claim"]["drive_detail_canonical_or_pit_admission"])
        checkpoint = self.gate["parallel_drive_detail_checkpoint"]
        self.assertEqual(checkpoint["quarantined_rows"], 3815)
        self.assertEqual(checkpoint["admission_state"], "CANDIDATE_NOT_ADMITTED")
        self.assertIn("PENDING", checkpoint["gate_disposition"])

    def test_roster_history_is_validated_candidate_only_without_availability_inference(self) -> None:
        roster = self.contract["latest_validated_roster_candidate"]
        self.assertEqual(
            roster["dataset_identity"],
            "17e42ac17f94248213407366ee32e5a09705317d98c3561ee7e93fda6eda8dda",
        )
        self.assertEqual(roster["grain"], "PLAYER_TEAM_SEASON_ROSTER_MEMBERSHIP")
        self.assertEqual(roster["repository_seasons"], list(range(2004, 2023)))
        self.assertEqual(roster["repository_rows"], 206773)
        self.assertEqual(roster["cross_route_exact_canonical_membership_candidates"], 154387)
        self.assertEqual(roster["historical_attribute_drift_rows"], 29313)
        self.assertEqual(roster["validation_checks_passed"], 34)
        self.assertEqual(roster["mutation_controls_passed"], 9)
        self.assertEqual(roster["deterministic_payloads_compared"], 19)
        self.assertIn("NO_NAME_ONLY_MERGE", roster["identity_contract"])
        self.assertEqual(roster["availability_inference"], "NOT_PERMITTED_FROM_ROSTER_MEMBERSHIP_ALONE")
        self.assertEqual(roster["admission_state"], "CANDIDATE_NOT_ADMITTED")
        self.assertFalse(self.evidence["completion_claim"]["roster_canonical_pit_or_availability_admission"])
        checkpoint = self.gate["parallel_roster_checkpoint"]
        self.assertEqual(checkpoint["quarantined_rows"], 7749)
        self.assertFalse(checkpoint["availability_inference"])
        self.assertEqual(checkpoint["admission_state"], "CANDIDATE_NOT_ADMITTED")
        self.assertIn("PENDING", checkpoint["gate_disposition"])

    def test_player_event_metrics_are_bounded_validated_candidates_not_official_box_scores(self) -> None:
        metrics = self.contract["latest_validated_player_event_metric_candidate"]
        self.assertEqual(
            metrics["dataset_identity"],
            "869818c5fe312bafbff5139eadb21153069d974ea7f576f154a58ecb6d888f10",
        )
        self.assertEqual(metrics["repository_seasons"], list(range(2014, 2023)))
        self.assertEqual(metrics["repository_source_rows"], 921136)
        self.assertEqual(metrics["derived_metric_rows"], 354082)
        self.assertEqual(metrics["cross_route_exact_canonical_game_player_team_candidates"], 289897)
        self.assertEqual(metrics["signed_yardage_rows_preserved"], 5595)
        self.assertEqual(metrics["current_reconciliation_captures"], 146)
        self.assertEqual(metrics["validation_checks_passed"], 44)
        self.assertEqual(metrics["mutation_controls_passed"], 9)
        self.assertEqual(metrics["deterministic_payloads_compared"], 9)
        self.assertEqual(len(metrics["metric_scope"]), 6)
        self.assertIn("NOT_CLAIMED", metrics["official_box_score_status"])
        self.assertEqual(metrics["admission_state"], "CANDIDATE_NOT_ADMITTED")
        self.assertFalse(self.evidence["completion_claim"]["player_event_metric_canonical_or_pit_admission"])
        self.assertFalse(self.evidence["completion_claim"]["official_player_box_scores_materialized"])
        checkpoint = self.gate["parallel_player_event_metric_checkpoint"]
        self.assertEqual(checkpoint["quarantined_rows"], 43305)
        self.assertFalse(checkpoint["official_box_score_materialization"])
        self.assertEqual(checkpoint["admission_state"], "CANDIDATE_NOT_ADMITTED")


if __name__ == "__main__":
    unittest.main()

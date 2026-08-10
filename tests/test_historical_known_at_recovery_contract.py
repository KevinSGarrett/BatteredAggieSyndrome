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
        cls.rankings_gate = json.loads(
            (ROOT / "artifacts" / "pit" / "historical_rankings_reconciliation_gate.json").read_text(
                encoding="utf-8"
            )
        )
        cls.team_box_gate = json.loads(
            (ROOT / "artifacts" / "pit" / "historical_team_box_reconciliation_gate.json").read_text(
                encoding="utf-8"
            )
        )
        cls.advanced_game_gate = json.loads(
            (ROOT / "artifacts" / "pit" / "historical_advanced_game_reconciliation_gate.json").read_text(
                encoding="utf-8"
            )
        )
        cls.venue_assignment_gate = json.loads(
            (ROOT / "artifacts" / "pit" / "historical_venue_assignment_reconciliation_gate.json").read_text(
                encoding="utf-8"
            )
        )
        cls.player_box_gate = json.loads(
            (ROOT / "artifacts" / "pit" / "historical_player_box_reconciliation_gate.json").read_text(
                encoding="utf-8"
            )
        )
        cls.weather_gate = json.loads(
            (
                ROOT
                / "artifacts"
                / "pit"
                / "historical_weather_previous_runs_reconciliation_gate.json"
            ).read_text(encoding="utf-8")
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
        self.assertEqual(storage["rankings_raw"], "raw/SRC-063/college_poll_archive/ap/sha256")
        self.assertEqual(storage["rankings_candidate_payloads"], "quarantine/historical_rankings/sha256")
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

    def test_play_enrichment_is_validated_candidate_only_without_player_or_feature_promotion(self) -> None:
        enrichment = self.contract["latest_validated_play_enrichment_candidate"]
        self.assertEqual(
            enrichment["dataset_identity"],
            "7a774ac95cfd0e29bacffd9a4fd164e264b789a1c4df6b674c0325f9f81340c0",
        )
        self.assertEqual(enrichment["repository_seasons"], list(range(2014, 2023)))
        self.assertEqual(enrichment["repository_rows"], 1426487)
        self.assertEqual(enrichment["rows_with_any_position"], 915021)
        self.assertEqual(enrichment["rows_with_any_source_player_id"], 921613)
        self.assertEqual(enrichment["exact_validated_play_link_candidates"], 1176564)
        self.assertEqual(enrichment["canonical_game_play_unreconciled_candidates"], 139932)
        self.assertEqual(enrichment["versioned_repository_source_level_only_candidates"], 83654)
        self.assertEqual(enrichment["quarantined_rows"], 26337)
        self.assertEqual(enrichment["unknown_position_cells"], 19924)
        self.assertEqual(enrichment["validation_checks_passed"], 23)
        self.assertEqual(enrichment["mutation_controls_passed"], 9)
        self.assertEqual(enrichment["deterministic_payloads_compared"], 9)
        self.assertIn("NOT_OFFICIAL_BOX_SCORE", enrichment["metric_authority"])
        self.assertIn("NO_NAME_ONLY", enrichment["player_identity_contract"])
        self.assertEqual(enrichment["admission_state"], "CANDIDATE_NOT_ADMITTED")
        self.assertTrue(self.evidence["completion_claim"]["play_enrichment_candidate_layer_validated"])
        self.assertFalse(
            self.evidence["completion_claim"][
                "play_enrichment_canonical_pit_feature_or_player_identity_admission"
            ]
        )
        checkpoint = self.gate["parallel_play_enrichment_checkpoint"]
        self.assertEqual(checkpoint["quarantined_rows"], 26337)
        self.assertFalse(checkpoint["canonical_player_identity_promotion"])
        self.assertFalse(checkpoint["feature_or_pit_admission"])
        self.assertEqual(checkpoint["admission_state"], "CANDIDATE_NOT_ADMITTED")
        self.assertIn("PENDING", checkpoint["gate_disposition"])

    def test_team_membership_history_is_validated_candidate_only_without_venue_or_pit_promotion(self) -> None:
        membership = self.contract["latest_validated_team_membership_candidate"]
        self.assertEqual(
            membership["dataset_identity"],
            "964daf659f62069eda5b9e264f09dd53892d958d0ebff3780ad836a3d7d42024",
        )
        self.assertEqual(membership["grain"], "TEAM_SEASON")
        self.assertEqual(membership["repository_seasons"], list(range(2001, 2021)))
        self.assertEqual(membership["repository_rows"], 2462)
        self.assertEqual(membership["exact_source_id_canonical_team_candidates"], 2462)
        self.assertEqual(membership["conference_or_division_transitions"], 158)
        self.assertEqual(membership["identical_source_payload_groups"], 4)
        self.assertEqual(membership["validation_checks_passed"], 29)
        self.assertEqual(membership["mutation_controls_passed"], 9)
        self.assertEqual(membership["deterministic_payloads_compared"], 20)
        self.assertIn("NOT_CLAIMED", membership["venue_history_status"])
        self.assertEqual(membership["admission_state"], "CANDIDATE_NOT_ADMITTED")
        self.assertTrue(self.evidence["completion_claim"]["team_membership_candidate_layer_validated"])
        self.assertFalse(self.evidence["completion_claim"]["team_membership_canonical_or_pit_admission"])
        self.assertFalse(self.evidence["completion_claim"]["historical_venue_materialized"])
        checkpoint = self.gate["parallel_team_membership_checkpoint"]
        self.assertEqual(checkpoint["repository_rows"], 2462)
        self.assertEqual(checkpoint["conference_or_division_transitions"], 158)
        self.assertFalse(checkpoint["venue_history_claimed"])
        self.assertFalse(checkpoint["canonical_or_pit_admission"])
        self.assertEqual(checkpoint["admission_state"], "CANDIDATE_NOT_ADMITTED")
        self.assertIn("PENDING", checkpoint["gate_disposition"])

    def test_rankings_history_is_broad_validated_and_candidate_only(self) -> None:
        rankings = self.contract["latest_validated_rankings_candidate"]
        self.assertEqual(
            rankings["normalization_identity"],
            "acad9e20ba70ab7f371fa210431e4adc66243138154683f9a1b71961e0630220",
        )
        self.assertEqual(
            rankings["reconciliation_identity"],
            "28668e9138f9267a0dbe00c60f7cedd8f1fc37b051e2b3c61dde4fd240fb3570",
        )
        self.assertEqual(rankings["source_season_min"], 1936)
        self.assertEqual(rankings["source_season_max"], 2025)
        self.assertEqual(rankings["source_seasons"], 90)
        self.assertEqual(rankings["poll_snapshots"], 1267)
        self.assertEqual(rankings["normalized_rows"], 37064)
        self.assertEqual(rankings["numeric_ranked_rows"], 27611)
        self.assertEqual(rankings["receiving_votes_rows"], 5307)
        self.assertEqual(rankings["not_ranked_rows"], 4146)
        self.assertEqual(rankings["explicit_date_poll_snapshots"], 1101)
        self.assertEqual(rankings["unknown_date_poll_snapshots"], 166)
        self.assertEqual(rankings["exact_high_coverage_unique_reconciliations"], 395)
        self.assertEqual(rankings["low_agreement_quarantined_reconciliations"], 12)
        self.assertEqual(rankings["pre_2001_source_only_polls"], 856)
        self.assertEqual(rankings["validation_checks_passed"], 28)
        self.assertEqual(rankings["mutation_controls_passed"], 14)
        self.assertEqual(rankings["deterministic_payloads_compared"], 92)
        self.assertEqual(rankings["admission_state"], "CANDIDATE_OR_QUARANTINE_NOT_ADMITTED")
        self.assertTrue(self.evidence["completion_claim"]["rankings_candidate_layer_validated"])
        self.assertFalse(self.evidence["completion_claim"]["rankings_canonical_or_pit_admission"])
        checkpoint = self.gate["parallel_rankings_checkpoint"]
        self.assertFalse(checkpoint["canonical_team_admission"])
        self.assertFalse(checkpoint["pit_state_admission"])
        self.assertFalse(checkpoint["training_feature_admission"])
        self.assertIn("PENDING", checkpoint["gate_disposition"])
        self.assertFalse(self.rankings_gate["historical_known_at_gate"]["pit_state_admission"])
        self.assertFalse(self.rankings_gate["scientific_nonclaims"]["gap_002_resolved"])

    def test_college_poll_archive_is_registered_under_private_research_policy(self) -> None:
        acquisition = json.loads(
            (ROOT / "configs" / "source_acquisition_registry.json").read_text(encoding="utf-8")
        )
        rights = json.loads((ROOT / "configs" / "source_rights_registry.json").read_text(encoding="utf-8"))
        source = next(item for item in acquisition["sources"] if item["source_id"] == "SRC-063")
        decision = next(item for item in rights["sources"] if item["source_id"] == "SRC-063")
        self.assertEqual(acquisition["source_count"], len(acquisition["sources"]))
        self.assertEqual(rights["source_count"], len(rights["sources"]))
        self.assertEqual(source["readiness_required"], "READY_PUBLIC_DIRECT_CAPTURE_VALIDATED")
        self.assertEqual(len(source["endpoints"]), 2)
        self.assertEqual(decision["lane_disposition"], "PRIVATE_RESEARCH_ALLOWED")
        self.assertTrue(decision["required_data_outcome_nonblocking"])
        self.assertFalse(decision["raw_export_allowed"])

    def test_team_box_history_is_validated_candidate_only_with_partial_and_side_drift_preserved(self) -> None:
        team_box = self.contract["latest_validated_team_box_candidate"]
        self.assertEqual(
            team_box["dataset_identity"],
            "3edf5fe3cf48c9c1000fcbcc1d3fd674ed0875a7e561997f13d3f8d958b01f5b",
        )
        self.assertEqual(team_box["source_seasons"], list(range(2010, 2026)))
        self.assertEqual(team_box["captured_partitions"], 261)
        self.assertEqual(team_box["distinct_source_games"], 13670)
        self.assertEqual(team_box["candidate_team_rows"], 27340)
        self.assertEqual(team_box["stat_cells"], 812533)
        self.assertEqual(team_box["cross_route_game_side_point_reconciled_rows"], 21168)
        self.assertEqual(team_box["cross_route_side_swap_reconciled_games"], 9)
        self.assertEqual(team_box["cross_route_side_swap_reconciled_rows"], 18)
        self.assertEqual(team_box["current_canonical_capture_exact_match_rows"], 7318)
        self.assertEqual(team_box["current_canonical_capture_conflict_rows"], 0)
        self.assertEqual(team_box["source_level_only_rows"], 642)
        self.assertEqual(team_box["validation_checks_passed"], 47)
        self.assertEqual(team_box["mutation_controls_passed"], 14)
        self.assertEqual(team_box["deterministic_payloads_compared"], 16)
        self.assertIn("UNKNOWN", team_box["historical_known_at_basis"])
        self.assertIn("2020", team_box["partial_season_finding"])
        self.assertEqual(team_box["admission_state"], "CANDIDATE_NOT_ADMITTED")
        self.assertTrue(self.evidence["completion_claim"]["team_box_candidate_layer_validated"])
        self.assertTrue(self.evidence["completion_claim"]["structured_team_box_candidate_materialized"])
        self.assertFalse(
            self.evidence["completion_claim"]["team_box_canonical_pit_feature_or_official_source_admission"]
        )
        self.assertFalse(self.evidence["completion_claim"]["official_team_box_scores_materialized"])
        checkpoint = self.gate["parallel_team_box_checkpoint"]
        self.assertFalse(checkpoint["canonical_team_box_admission"])
        self.assertFalse(checkpoint["pit_state_admission"])
        self.assertFalse(checkpoint["training_feature_admission"])
        self.assertIn("PENDING", checkpoint["gate_disposition"])
        self.assertEqual(self.team_box_gate["reconciliation"]["historical_side_swap_reconciled_games"], 9)
        self.assertFalse(self.team_box_gate["historical_known_at_gate"]["pit_state_admission"])
        self.assertFalse(self.team_box_gate["scientific_nonclaims"]["gap_002_resolved"])

    def test_advanced_game_history_is_reciprocal_validated_and_candidate_only(self) -> None:
        advanced = self.contract["latest_validated_advanced_game_candidate"]
        self.assertEqual(
            advanced["dataset_identity"],
            "8daab70f13294ed69d0692933c210765602dfedb65af499fe48fdd1dfec5adfc",
        )
        self.assertEqual(advanced["source_seasons"], list(range(2001, 2026)))
        self.assertEqual(advanced["captured_partitions"], 25)
        self.assertEqual(advanced["source_rows"], 42190)
        self.assertEqual(advanced["distinct_source_games"], 21095)
        self.assertEqual(advanced["games_with_exactly_two_team_rows"], 21095)
        self.assertEqual(advanced["offense_defense_reciprocal_games"], 21095)
        self.assertEqual(advanced["advanced_leaf_paths"], 56)
        self.assertEqual(advanced["advanced_leaf_cells"], 2362640)
        self.assertEqual(advanced["missing_leaf_cells"], 0)
        self.assertEqual(advanced["team_box_cross_route_outcome_match_rows"], 20996)
        self.assertEqual(advanced["current_canonical_capture_exact_match_rows"], 7310)
        self.assertEqual(advanced["current_canonical_capture_conflict_rows"], 0)
        self.assertEqual(advanced["source_level_only_rows"], 15048)
        self.assertEqual(advanced["validation_checks_passed"], 48)
        self.assertEqual(advanced["mutation_controls_passed"], 14)
        self.assertEqual(advanced["deterministic_payloads_compared"], 25)
        self.assertIn("UNKNOWN", advanced["historical_known_at_basis"])
        self.assertIn("2002", advanced["partial_season_finding"])
        self.assertEqual(advanced["admission_state"], "CANDIDATE_NOT_ADMITTED")
        self.assertTrue(self.evidence["completion_claim"]["advanced_game_candidate_layer_validated"])
        self.assertTrue(self.evidence["completion_claim"]["structured_advanced_game_candidate_materialized"])
        self.assertFalse(
            self.evidence["completion_claim"][
                "advanced_game_canonical_pit_feature_or_protected_use_admission"
            ]
        )
        checkpoint = self.gate["parallel_advanced_game_checkpoint"]
        self.assertFalse(checkpoint["canonical_advanced_stat_admission"])
        self.assertFalse(checkpoint["pit_state_admission"])
        self.assertFalse(checkpoint["training_feature_admission"])
        self.assertFalse(checkpoint["protected_evaluation_admission"])
        self.assertIn("PENDING", checkpoint["gate_disposition"])
        self.assertEqual(self.advanced_game_gate["candidate_layer"]["offense_defense_reciprocal_games"], 21095)
        self.assertFalse(self.advanced_game_gate["historical_known_at_gate"]["pit_state_admission"])
        self.assertFalse(self.advanced_game_gate["scientific_nonclaims"]["gap_002_resolved"])

    def test_venue_assignment_history_preserves_early_absence_and_current_catalog_boundary(self) -> None:
        venue = self.contract["latest_validated_venue_assignment_candidate"]
        self.assertEqual(
            venue["dataset_identity"],
            "34b682b25cff6f98e86bbc2e8f64528edd92ee8bcef09cef4729c301adf8cbee",
        )
        self.assertEqual(venue["source_season_min"], 1963)
        self.assertEqual(venue["source_season_max"], 2025)
        self.assertEqual(venue["source_seasons"], 63)
        self.assertEqual(venue["source_games"], 46954)
        self.assertEqual(venue["venue_catalog_rows"], 844)
        self.assertEqual(venue["games_with_venue_id"], 19669)
        self.assertEqual(venue["catalog_id_linked_games"], 19669)
        self.assertEqual(venue["games_without_venue_evidence"], 27285)
        self.assertEqual(venue["current_capture_venue_exact_match_games"], 3659)
        self.assertEqual(venue["current_capture_venue_conflict_games"], 0)
        self.assertEqual(venue["validation_checks_passed"], 31)
        self.assertEqual(venue["mutation_controls_passed"], 14)
        self.assertEqual(venue["deterministic_payloads_compared"], 63)
        self.assertIn("UNKNOWN", venue["historical_known_at_basis"])
        self.assertIn("NOT_HISTORICALLY_BACKFILLED", venue["catalog_effective_time"])
        self.assertIn("27285", venue["pre_2001_finding"])
        self.assertEqual(venue["admission_state"], "CANDIDATE_NOT_ADMITTED")
        self.assertTrue(self.evidence["completion_claim"]["venue_assignment_candidate_layer_validated"])
        self.assertFalse(
            self.evidence["completion_claim"]["venue_assignment_canonical_pit_feature_or_relocation_admission"]
        )
        self.assertFalse(self.evidence["completion_claim"]["historical_venue_materialized"])
        checkpoint = self.gate["parallel_venue_assignment_checkpoint"]
        self.assertFalse(checkpoint["historical_catalog_effective_time_established"])
        self.assertFalse(checkpoint["canonical_venue_assignment_admission"])
        self.assertFalse(checkpoint["pit_state_admission"])
        self.assertFalse(checkpoint["training_feature_admission"])
        self.assertFalse(checkpoint["relocation_history_admission"])
        self.assertIn("PENDING", checkpoint["gate_disposition"])
        self.assertEqual(self.venue_assignment_gate["coverage"]["season_1963_2000_games_with_venue_evidence"], 0)
        self.assertFalse(
            self.venue_assignment_gate["historical_known_at_gate"]["current_catalog_historical_backfill_allowed"]
        )
        self.assertFalse(self.venue_assignment_gate["scientific_nonclaims"]["gap_002_resolved"])

    def test_player_box_history_is_validated_at_cell_grain_without_identity_or_pit_promotion(self) -> None:
        player_box = self.contract["latest_validated_player_box_candidate"]
        self.assertEqual(
            player_box["dataset_identity"],
            "d866f2ba94b9c19a966e0eaf8326259b5761b64386f9829a95d43b9e2831069d",
        )
        self.assertEqual(player_box["source_season_min"], 2010)
        self.assertEqual(player_box["source_season_max"], 2025)
        self.assertEqual(player_box["source_seasons"], 16)
        self.assertEqual(player_box["source_games"], 13670)
        self.assertEqual(player_box["source_stat_cells"], 5279775)
        self.assertEqual(player_box["distinct_source_player_ids"], 63407)
        self.assertEqual(player_box["missing_player_name_cells"], 246)
        self.assertEqual(player_box["player_label_whitespace_drift_cells"], 47446)
        self.assertEqual(player_box["player_event_metric_exact_cells"], 258886)
        self.assertEqual(player_box["player_event_metric_conflict_cells"], 34006)
        self.assertEqual(player_box["current_game_multiset_exact_games"], 3659)
        self.assertEqual(player_box["current_game_multiset_conflict_games"], 0)
        self.assertEqual(player_box["validation_checks_passed"], 54)
        self.assertEqual(player_box["mutation_controls_passed"], 14)
        self.assertEqual(player_box["deterministic_payloads_compared"], 16)
        self.assertIn("UNKNOWN", player_box["historical_known_at_basis"])
        self.assertIn("NO_NAME_ONLY", player_box["player_identity_basis"])
        self.assertIn("THREE_ONE_TEAM_GAMES", player_box["partial_and_drift_findings"])
        self.assertEqual(player_box["admission_state"], "CANDIDATE_NOT_ADMITTED")
        self.assertTrue(self.evidence["completion_claim"]["player_box_candidate_layer_validated"])
        self.assertTrue(self.evidence["completion_claim"]["structured_player_box_candidate_materialized"])
        self.assertFalse(
            self.evidence["completion_claim"][
                "player_box_canonical_pit_feature_identity_official_source_or_protected_use_admission"
            ]
        )
        self.assertFalse(self.evidence["completion_claim"]["official_player_box_scores_materialized"])
        checkpoint = self.gate["parallel_player_box_checkpoint"]
        self.assertFalse(checkpoint["canonical_player_identity_established"])
        self.assertFalse(checkpoint["official_primary_gamebook_status_established"])
        self.assertFalse(checkpoint["canonical_player_box_admission"])
        self.assertFalse(checkpoint["pit_state_admission"])
        self.assertFalse(checkpoint["training_feature_admission"])
        self.assertFalse(checkpoint["protected_evaluation_admission"])
        self.assertIn("PENDING", checkpoint["gate_disposition"])
        self.assertEqual(self.player_box_gate["coverage"]["games_without_exactly_two_team_rows"], 3)
        self.assertEqual(self.player_box_gate["reconciliation"]["player_event_metric_conflict_cells"], 34006)
        self.assertFalse(self.player_box_gate["historical_known_at_gate"]["name_only_player_identity_merge_allowed"])
        self.assertFalse(self.player_box_gate["scientific_nonclaims"]["gap_002_resolved"])

    def test_weather_previous_runs_preserve_partial_route_and_unknown_pit_boundaries(self) -> None:
        weather = self.contract["latest_validated_weather_previous_runs_candidate"]
        self.assertEqual(
            weather["dataset_identity"],
            "511246db0195b09bba97647dbdb25fb2fcaf464f9899142c7e33b2479796c1cc",
        )
        self.assertEqual(weather["source_season_min"], 2021)
        self.assertEqual(weather["source_season_max"], 2025)
        self.assertEqual(weather["target_games_with_kickoff_and_coordinates"], 4545)
        self.assertEqual(weather["captured_games"], 3346)
        self.assertEqual(weather["source_evidence_gap_games"], 2)
        self.assertEqual(weather["technical_route_gap_games"], 1199)
        self.assertEqual(weather["captured_requests"], 385)
        self.assertEqual(weather["technical_route_gap_requests"], 168)
        self.assertEqual(weather["candidate_cells"], 100380)
        self.assertEqual(weather["non_null_cells"], 29527)
        self.assertEqual(weather["archive_variable_unavailable_cells"], 70853)
        self.assertEqual(weather["validation_checks_passed"], 23)
        self.assertEqual(weather["mutation_controls_passed"], 14)
        self.assertEqual(weather["deterministic_rebuild_checks_passed"], 8)
        self.assertEqual(weather["deterministic_payloads_compared"], 5)
        self.assertIn("UNKNOWN", weather["historical_known_at_basis"])
        self.assertIn("1199", weather["partial_route_finding"])
        self.assertEqual(weather["observed_weather_substitution"], "PROHIBITED")
        self.assertEqual(weather["admission_state"], "CANDIDATE_OR_QUARANTINE_NOT_ADMITTED")
        claim = self.evidence["completion_claim"]
        self.assertTrue(claim["weather_previous_runs_partial_candidate_layer_validated"])
        self.assertFalse(claim["weather_acquisition_complete"])
        self.assertFalse(claim["weather_canonical_pit_feature_or_protected_use_admission"])
        self.assertFalse(claim["observed_weather_substitution_used"])
        checkpoint = self.gate["parallel_weather_previous_runs_checkpoint"]
        self.assertFalse(checkpoint["exact_historical_model_run_initialization_established"])
        self.assertFalse(checkpoint["exact_historical_api_availability_established"])
        self.assertFalse(checkpoint["historical_venue_coordinate_effective_time_established"])
        self.assertFalse(checkpoint["observed_or_reanalysis_weather_substitution_allowed"])
        self.assertFalse(checkpoint["canonical_weather_admission"])
        self.assertFalse(checkpoint["pit_state_admission"])
        self.assertFalse(checkpoint["training_feature_admission"])
        self.assertFalse(checkpoint["protected_evaluation_admission"])
        self.assertIn("PARTIAL_ROUTE", checkpoint["gate_disposition"])
        self.assertEqual(self.weather_gate["candidate_layer"]["captured_games"], 3346)
        self.assertEqual(self.weather_gate["candidate_layer"]["technical_route_gap_games"], 1199)
        self.assertFalse(self.weather_gate["historical_known_at_gate"]["pit_state_admission"])
        self.assertFalse(self.weather_gate["scientific_nonclaims"]["historical_weather_complete"])
        self.assertFalse(self.weather_gate["scientific_nonclaims"]["gap_002_resolved"])


if __name__ == "__main__":
    unittest.main()

"""Cycle #28 adversarial and unit coverage for receipts, calendar, trust, coverage, Gridiron, and cost."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aggie_analytics.cycle28.atomic_receipt import (
    DERIVATIVE_OBSERVATION_RECEIPT,
    SOURCE_ACQUISITION_RECEIPT,
    AtomicReceiptError,
    classify_cycle27_receipt,
    reject_caller_supplied_retrieval_time,
    reject_filesystem_mtime_authority,
    request_identity_sha256,
    write_atomic_source_acquisition,
)
from aggie_analytics.cycle28.assurance import (
    ASSURANCE_LAYERS,
    BLOCKED_ZERO_PIT,
    EMPIRICAL_NOT_ESTABLISHED,
    AssuranceError,
    cross_output_coherent,
    invalidate_descendants,
    reject_lower_layer_promotion,
    require_claim_mapped,
    structural_trust_outcome,
    validator_imports_producer,
)
from aggie_analytics.cycle28.availability import (
    REPORT_EXPECTED_NOT_FOUND,
    AvailabilityError,
    reject_conference_policy_out_of_scope,
    reject_missing_report_as_healthy,
    reject_postgame_participation_as_pregame,
)
from aggie_analytics.cycle28.calendar import (
    DISPOSITION_EARLY,
    DISPOSITION_MISSED,
    CalendarReconciliationError,
    live_owner_identity_match,
    reconcile_washington_state_washington,
    reject_backfill,
    reject_relabel_early_as_t90m,
    reject_sunday_into_monday_fitted_path,
)
from aggie_analytics.cycle28.coaching import (
    ROLE_HEAD_COACH,
    ROLE_OC,
    ROLE_OFFENSE_PLAY_CALLER,
    CoachingError,
    consumption_state,
    reject_am_only_national_staff,
    reject_cfbd_as_coordinator_or_play_caller,
    reject_name_only_auto_admit,
    reject_play_caller_from_coordinator,
)
from aggie_analytics.cycle28.cost import PaidReviewError, admit_paid_review
from aggie_analytics.cycle28.coverage import (
    CoverageError,
    reject_am_only_national,
    reject_denominator_shrink,
    reject_not_yet_audited_collapse,
    require_all_domains,
)
from aggie_analytics.cycle28.decommission import validate_retired_assistive_decommission
from aggie_analytics.cycle28.gridiron import (
    ALLOWED_CLAIM,
    GridironBoundaryError,
    classify_breaking_change,
    load_synthetic_adapter,
    reject_active_checkout_move,
    reject_default_all22_path,
    reject_disconnected_target_created,
    reject_film_auto_admit,
    reject_forbidden_claim,
    reject_incompatible_payload,
    reject_mutable_worktree_as_bom,
    reject_programops_runtime,
    reject_secret_values_in_inventory,
    reject_transfer_as_science,
    reject_unauthorized_transfer,
    require_affected_claim_invalidation,
)
from aggie_analytics.cycle28.scoring import (
    Cycle28ScoringError,
    classify_predecessor_receipts,
    reject_forecast_mutation,
    reject_week1_outcome_tuning,
    require_scored_row_authority,
    terminal_selection,
)
from aggie_analytics.cycle28.topology import (
    TopologyError,
    classify_branch,
    reject_cfip_replacing_bat,
    reject_generic_plan_as_substantive,
    reject_generated_index_as_completeness,
    transfer_conclusion,
)
from aggie_analytics.scientific_reference.cycle28_scoring import (
    IndependentScoringError,
    reject_non_final_score,
    reject_oriented_rows_as_games,
    reject_prekickoff_final,
)


def _source_fields(**overrides: object) -> dict[str, object]:
    fields = {
        "receipt_kind": SOURCE_ACQUISITION_RECEIPT,
        "request_identity_sha256": request_identity_sha256(
            method="GET", uri="https://stats.ncaa.org/contests/livestream_scoreboards"
        ),
        "source_uri": "https://stats.ncaa.org/contests/livestream_scoreboards",
        "route_id": "direct_http",
        "network_response_status": 200,
        "acquisition_started_at_utc": "2026-09-06T20:10:00Z",
        "acquisition_ended_at_utc": "2026-09-06T20:10:01Z",
        "trusted_clock_retrieval_utc": "2026-09-06T20:10:01Z",
        "process_identity": "cycle28-test",
        "transport_is_not_result_authority": False,
    }
    fields.update(overrides)
    return fields


class Cycle28AdversarialTests(unittest.TestCase):
    def test_cycle27_receipt_is_derivative_observation(self) -> None:
        kind = classify_cycle27_receipt(
            {
                "artifact_type": "WEEK1_OFFICIAL_FINAL_ACQUISITION_RECEIPT",
                "pin_field_retrieved_at_is_not_authority": True,
                "retrieved_at_utc": "2026-09-06T00:24:34Z",
            }
        )
        self.assertEqual(kind, DERIVATIVE_OBSERVATION_RECEIPT)

    def test_shared_materialization_timestamp_count(self) -> None:
        payloads = [
            {
                "pin_field_retrieved_at_is_not_authority": True,
                "retrieved_at_utc": "2026-09-06T00:24:34Z",
            }
            for _ in range(290)
        ]
        summary = classify_predecessor_receipts(payloads)
        self.assertEqual(summary["receipt_count"], 290)
        self.assertEqual(summary["shared_materialization_timestamp_count"], 290)
        self.assertEqual(summary["derivative_observation_count"], 290)
        self.assertEqual(summary["source_acquisition_count"], 0)

    def test_caller_supplied_execution_time_rejected(self) -> None:
        with self.assertRaises(AtomicReceiptError):
            reject_caller_supplied_retrieval_time(
                trusted_retrieval_utc="2026-09-06T20:10:01Z",
                caller_execution_time_utc="2026-09-06T00:24:34Z",
            )

    def test_filesystem_mtime_rejected(self) -> None:
        with self.assertRaises(AtomicReceiptError):
            reject_filesystem_mtime_authority(
                "2026-09-06T20:10:01Z", "2026-09-06T20:10:01Z"
            )

    def test_atomic_write_and_missing_request_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = write_atomic_source_acquisition(
                data_root=root,
                raw_relative_dir="raw/official",
                receipt_relative_dir="receipts/official",
                raw_bytes=b"<html>final</html>",
                receipt_fields=_source_fields(),
            )
            self.assertEqual(result["receipt_kind"], SOURCE_ACQUISITION_RECEIPT)
            self.assertTrue((root / result["raw_relative_path"]).is_file())
            self.assertTrue((root / result["receipt_relative_path"]).is_file())
            with self.assertRaises(AtomicReceiptError):
                write_atomic_source_acquisition(
                    data_root=root,
                    raw_relative_dir="raw/official",
                    receipt_relative_dir="receipts/official",
                    raw_bytes=b"<html>final</html>",
                    receipt_fields=_source_fields(request_identity_sha256=""),
                )

    def test_scored_row_requires_receipt_binding(self) -> None:
        with self.assertRaises(Cycle28ScoringError):
            require_scored_row_authority({"ncaa_contest_id": "6607349"})

    def test_prekickoff_and_non_final_rejected(self) -> None:
        with self.assertRaises(IndependentScoringError):
            reject_prekickoff_final("2026-09-06T19:00:00Z", "2026-09-06T20:00:00Z")
        with self.assertRaises(IndependentScoringError):
            reject_non_final_score("IN_PROGRESS")

    def test_conflicting_and_arbitrary_terminal_selection(self) -> None:
        conflict = terminal_selection(
            [
                {
                    "receipt_kind": SOURCE_ACQUISITION_RECEIPT,
                    "final_status": "FINAL",
                    "home_points": 50,
                    "away_points": 0,
                    "winner": "home",
                    "ncaa_contest_id": "6607349",
                    "ordered_participants": ("Missouri St.", "Texas A&M"),
                    "trusted_clock_retrieval_utc": "2026-09-06T04:00:00Z",
                },
                {
                    "receipt_kind": SOURCE_ACQUISITION_RECEIPT,
                    "final_status": "FINAL",
                    "home_points": 49,
                    "away_points": 0,
                    "winner": "home",
                    "ncaa_contest_id": "6607349",
                    "ordered_participants": ("Missouri St.", "Texas A&M"),
                    "trusted_clock_retrieval_utc": "2026-09-06T05:00:00Z",
                },
            ]
        )
        self.assertEqual(conflict, "CONFLICT_QUARANTINED")
        earliest = terminal_selection(
            [
                {
                    "receipt_kind": SOURCE_ACQUISITION_RECEIPT,
                    "final_status": "FINAL",
                    "home_points": 50,
                    "away_points": 0,
                    "winner": "home",
                    "ncaa_contest_id": "6607349",
                    "ordered_participants": ("Missouri St.", "Texas A&M"),
                    "trusted_clock_retrieval_utc": "2026-09-06T05:00:00Z",
                },
                {
                    "receipt_kind": SOURCE_ACQUISITION_RECEIPT,
                    "final_status": "FINAL",
                    "home_points": 50,
                    "away_points": 0,
                    "winner": "home",
                    "ncaa_contest_id": "6607349",
                    "ordered_participants": ("Missouri St.", "Texas A&M"),
                    "trusted_clock_retrieval_utc": "2026-09-06T04:00:00Z",
                },
            ]
        )
        self.assertEqual(earliest["trusted_clock_retrieval_utc"], "2026-09-06T04:00:00Z")

    def test_oriented_rows_are_not_independent_games(self) -> None:
        rows = [
            {"ncaa_contest_id": "1", "orientation": "HOME"},
            {"ncaa_contest_id": "1", "orientation": "AWAY"},
        ]
        self.assertEqual(reject_oriented_rows_as_games(rows), 1)

    def test_forecast_mutation_and_week1_tuning_rejected(self) -> None:
        with self.assertRaises(Cycle28ScoringError):
            reject_forecast_mutation("aaa", "bbb")
        with self.assertRaises(Cycle28ScoringError):
            reject_week1_outcome_tuning(True, False, False)

    def test_washington_conflict_and_early_capture(self) -> None:
        result = reconcile_washington_state_washington(
            now_utc="2026-09-06T20:10:00Z",
            predecessor_clock_text="04:00 AM",
            predecessor_bound_utc="2026-09-06T08:00:00Z",
            official_institutional_kickoff_utc="2026-09-06T20:00:00Z",
            predecessor_t90m_capture_utc="2026-09-06T06:30:00Z",
        )
        self.assertTrue(result["conflict"])
        self.assertEqual(result["real_t90m_disposition"], DISPOSITION_MISSED)
        self.assertEqual(result["predecessor_t90m_capture_disposition"], DISPOSITION_EARLY)
        self.assertFalse(result["real_t90m_was_met"])
        with self.assertRaises(CalendarReconciliationError):
            reject_relabel_early_as_t90m(
                capture_utc="2026-09-06T06:30:00Z",
                claimed_cutoff_utc="2026-09-06T06:30:00Z",
                corrected_cutoff_utc="2026-09-06T18:30:00Z",
            )
        with self.assertRaises(CalendarReconciliationError):
            reject_backfill("2026-09-06T20:10:00Z", "2026-09-06T18:30:00Z", True)
        with self.assertRaises(CalendarReconciliationError):
            reject_sunday_into_monday_fitted_path(
                target_contest_id="6594400",
                feature_update_from_sunday_outcome=True,
                predeclared_update_rule=False,
            )
        self.assertFalse(
            live_owner_identity_match(
                reported={"pid": 1, "executable": "a", "command_line": "x", "creation_utc": "t", "checkpoint": "c", "contest_ids": ["1"], "cutoff_utc": "u"},
                observed={"pid": 1, "executable": "b", "command_line": "x", "creation_utc": "t", "checkpoint": "c", "contest_ids": ["1"], "cutoff_utc": "u"},
            )
        )

    def test_claim_graph_and_layer_promotion(self) -> None:
        with self.assertRaises(AssuranceError):
            require_claim_mapped({"claim_id": "x"}, ("claim_id", "field"))
        results = {layer: "PASS" for layer in ASSURANCE_LAYERS}
        results["metrics_and_denominators"] = "FAIL"
        with self.assertRaises(AssuranceError):
            reject_lower_layer_promotion(results, "STRUCTURAL_CORRECTNESS_VERIFIED_WITHIN_SCOPE")
        self.assertTrue(validator_imports_producer(["aggie_analytics.data.week1_2026_cycle27_official_final_scoring"]))
        self.assertFalse(
            cross_output_coherent(
                probability=0.9,
                margin=-3.0,
                interval=(-1.0, 1.0),
                from_same_distribution=True,
            )
        )
        blocked = structural_trust_outcome(
            proven_pit_training_rows=0,
            every_claim_mapped=True,
            every_layer_passed=True,
            validator_independent=True,
            coherent=True,
        )
        self.assertEqual(blocked["structural_correctness"], BLOCKED_ZERO_PIT)
        self.assertEqual(blocked["empirical_predictive_skill"], EMPIRICAL_NOT_ESTABLISHED)
        self.assertFalse(blocked["scientific_trust_recovered"])
        children = invalidate_descendants("raw", {"raw": ["features"], "features": ["model"]})
        self.assertEqual(children, {"raw", "features", "model"})

    def test_coverage_invariants(self) -> None:
        with self.assertRaises(CoverageError):
            reject_not_yet_audited_collapse("NOT_YET_AUDITED", "SOURCE_ABSENT")
        with self.assertRaises(CoverageError):
            reject_denominator_shrink(
                frozen_denominator=91, reported_denominator=80, source_absent_count=11
            )
        with self.assertRaises(CoverageError):
            reject_am_only_national(2, 2, "national")
        with self.assertRaises(CoverageError):
            require_all_domains([{"domain": "schedules_results"}])

    def test_coaching_and_availability_invariants(self) -> None:
        with self.assertRaises(CoachingError):
            reject_play_caller_from_coordinator("Offensive Coordinator", ROLE_OFFENSE_PLAY_CALLER)
        with self.assertRaises(CoachingError):
            reject_cfbd_as_coordinator_or_play_caller("CFBD", ROLE_OC)
        with self.assertRaises(CoachingError):
            reject_name_only_auto_admit("name_only", "ADMITTED")
        with self.assertRaises(CoachingError):
            reject_am_only_national_staff(
                national_denominator=136, covered_teams=2, label="national"
            )
        self.assertEqual(consumption_state(admitted=False, reasons_pass=()), "CANDIDATE_ONLY_NOT_CONSUMED")
        with self.assertRaises(AvailabilityError):
            reject_missing_report_as_healthy(REPORT_EXPECTED_NOT_FOUND, True)
        with self.assertRaises(AvailabilityError):
            reject_conference_policy_out_of_scope(
                policy_scope="conference_games_only", game_type="nonconference"
            )
        with self.assertRaises(AvailabilityError):
            reject_postgame_participation_as_pregame(True)

    def test_gridiron_boundary(self) -> None:
        with self.assertRaises(GridironBoundaryError):
            reject_default_all22_path(Path(r"C:\All-22"))
        with self.assertRaises(GridironBoundaryError):
            reject_mutable_worktree_as_bom(True, False)
        with self.assertRaises(GridironBoundaryError):
            reject_film_auto_admit(True)
        with self.assertRaises(GridironBoundaryError):
            reject_programops_runtime(True)
        with self.assertRaises(GridironBoundaryError):
            reject_forbidden_claim("GRIDIRON_CORTEX_INTEGRATED")
        with self.assertRaises(GridironBoundaryError):
            reject_incompatible_payload({"snapshot_state": "DRIFTED_NOT_CONSUMABLE"}, adapter_version="1")
        self.assertEqual(
            classify_breaking_change(
                grain_changed=True,
                identity_changed=False,
                time_changed=False,
                units_changed=False,
                missingness_changed=False,
                uncertainty_changed=False,
                rights_changed=False,
                enums_changed=False,
                upstream_label="compatible",
            ),
            "BREAKING_DESPITE_UPSTREAM_LABEL",
        )
        with self.assertRaises(GridironBoundaryError):
            require_affected_claim_invalidation(True, [])
        with tempfile.TemporaryDirectory() as tmp:
            adapter = load_synthetic_adapter(Path(tmp), None)
            self.assertEqual(adapter["claim"], ALLOWED_CLAIM)
        with self.assertRaises(GridironBoundaryError):
            reject_active_checkout_move(
                Path(r"C:\All-22\repos\BatteredAggieSyndrome"),
                Path(r"C:\All-22"),
            )
        with self.assertRaises(GridironBoundaryError):
            reject_disconnected_target_created(True)
        with self.assertRaises(GridironBoundaryError):
            reject_unauthorized_transfer(True, False)
        with self.assertRaises(GridironBoundaryError):
            reject_transfer_as_science("scientific_trust_recovered")
        with self.assertRaises(GridironBoundaryError):
            reject_secret_values_in_inventory({"openai_api_key": "sk-secret"})

    def test_paid_review_controls(self) -> None:
        with self.assertRaises(PaidReviewError):
            admit_paid_review(
                deterministic_passed=False,
                readiness_label_present=True,
                authorized_head_sha="a",
                current_head_sha="a",
                model="gpt-5.3-codex",
                effort="low",
                premium_authorized=False,
                cache_hit=False,
                prior_tuple_paid=False,
                estimated_or_actual_cost_usd=0.4,
                pr_spend_usd=0.0,
                cycle_spend_usd=0.0,
                second_run=False,
                second_run_reason=None,
                retry_loop=False,
                raw_lake_or_secrets_in_prompt=False,
            )
        with self.assertRaises(PaidReviewError):
            admit_paid_review(
                deterministic_passed=True,
                readiness_label_present=True,
                authorized_head_sha="a",
                current_head_sha="a",
                model="gpt-5.6-sol",
                effort="low",
                premium_authorized=False,
                cache_hit=False,
                prior_tuple_paid=False,
                estimated_or_actual_cost_usd=0.4,
                pr_spend_usd=0.0,
                cycle_spend_usd=0.0,
                second_run=False,
                second_run_reason=None,
                retry_loop=False,
                raw_lake_or_secrets_in_prompt=False,
            )
        with self.assertRaises(PaidReviewError):
            admit_paid_review(
                deterministic_passed=True,
                readiness_label_present=True,
                authorized_head_sha="a",
                current_head_sha="a",
                model="gpt-5.3-codex",
                effort="low",
                premium_authorized=False,
                cache_hit=False,
                prior_tuple_paid=True,
                estimated_or_actual_cost_usd=0.4,
                pr_spend_usd=0.0,
                cycle_spend_usd=0.0,
                second_run=False,
                second_run_reason=None,
                retry_loop=False,
                raw_lake_or_secrets_in_prompt=False,
            )
        with self.assertRaises(PaidReviewError):
            admit_paid_review(
                deterministic_passed=True,
                readiness_label_present=True,
                authorized_head_sha="a",
                current_head_sha="a",
                model="gpt-5.3-codex",
                effort="low",
                premium_authorized=False,
                cache_hit=False,
                prior_tuple_paid=False,
                estimated_or_actual_cost_usd=None,
                pr_spend_usd=0.0,
                cycle_spend_usd=0.0,
                second_run=False,
                second_run_reason=None,
                retry_loop=False,
                raw_lake_or_secrets_in_prompt=False,
            )
        with self.assertRaises(PaidReviewError):
            admit_paid_review(
                deterministic_passed=True,
                readiness_label_present=True,
                authorized_head_sha="a",
                current_head_sha="a",
                model="gpt-5.3-codex",
                effort="low",
                premium_authorized=False,
                cache_hit=False,
                prior_tuple_paid=False,
                estimated_or_actual_cost_usd=0.4,
                pr_spend_usd=0.0,
                cycle_spend_usd=0.0,
                second_run=False,
                second_run_reason=None,
                retry_loop=True,
                raw_lake_or_secrets_in_prompt=False,
            )

    def test_topology_and_cfip(self) -> None:
        self.assertEqual(
            classify_branch(
                live_owner=False,
                open_pr=False,
                unique_commits=["cda5101f"],
                merged=False,
                preservation=False,
            ),
            "UNMERGED_UNIQUE_HISTORY",
        )
        with self.assertRaises(TopologyError):
            reject_cfip_replacing_bat(True, False)
        self.assertEqual(
            reject_generic_plan_as_substantive([], 54),
            "PLAN_STRUCTURE_PRESENT_SUBSTANTIVE_BAS_INTEGRATION_INCOMPLETE",
        )
        with self.assertRaises(TopologyError):
            reject_generated_index_as_completeness(True)
        self.assertEqual(transfer_conclusion(False, False), "BAS_REPOSITORY_TRANSFER_PREPARED_NOT_AUTHORIZED")

    def test_protected_years_and_one_game_not_bas(self) -> None:
        self.assertEqual("RETAIN_PROTECTED_LANE_BLOCKED", "RETAIN_PROTECTED_LANE_BLOCKED")
        self.assertNotIn("blind", "2024/2025 historically exposed")
        self.assertNotEqual("BAS", "one A&M result")


if __name__ == "__main__":
    unittest.main()

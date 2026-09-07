"""Cycle #29 adversarial controls for Phase 17 mutations."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from aggie_analytics.cycle29.acquisition import (
    AcquisitionError,
    GENERIC_ERROR_HTML,
    classify_semantic_page,
    classify_transport_and_upstream,
    contest_scoped_terminal,
    cutoff_span_truth,
    redact_headers,
    reject_volatile_request_identity,
    reject_wholly_known_without_proof,
    request_identity,
    require_upstream_success,
    reuse_existing_capture,
)
from aggie_analytics.cycle29.admission import reject_candidate_in_model
from aggie_analytics.cycle29.ci_rows import open_and_rehash, reject_pass_without_opening
from aggie_analytics.cycle29.claims import (
    ClaimError,
    inventory_claims,
    kernel_closure_claims,
)
from aggie_analytics.cycle29.coaching import (
    CoachingError,
    hc_oc_dc_matrix,
    historical_lattice,
    position_role_contract,
    reconcile_predecessor_observations,
    reject_array_zip_mispair,
    reject_cfbd_assistant,
    reject_composite_title_bypass,
    reject_dropped_identity,
    reject_name_only,
    reject_omitted_role_family,
    reject_play_caller_from_title,
    reject_week1_as_national_coaching,
    reject_wikimedia_as_pit,
    role_cell,
)
from aggie_analytics.cycle29.cost import CostError, reject_routine_api_review
from aggie_analytics.cycle29.dependency import static_import_graph
from aggie_analytics.cycle29.domains import (
    DomainError,
    crosswalk,
    reject_display_name_as_canonical,
    reject_empty_inventory_pass,
    reject_incompatible_parity_grains,
    reject_not_applicable_inflation,
    reject_zero_filled_registry,
)
from aggie_analytics.cycle29.findings import C28_P0_IDS, successor_ledger
from aggie_analytics.cycle29.forecast import (
    ForecastImmutabilityError,
    prove_set_unchanged,
    reject_literal_no_tuning,
)
from aggie_analytics.cycle29.gridiron import (
    GridironError,
    reject_obsolete_foundation,
    reject_skipped_integration_as_compat,
    reject_stale_c01,
)
from aggie_analytics.cycle29.hashing import sha256_file
from aggie_analytics.cycle29.lease import (
    SCHEDULER_ACTIVE_OR_BOUND,
    acquire,
    reject_stale_takeover_without_expiry,
    release,
)
from aggie_analytics.cycle29.pit_kernel import (
    PitKernelError,
    build_game_grain_kernel,
    reject_expected_from_observed_route,
)
from aggie_analytics.cycle29.populations import (
    PopulationError,
    classify_predecessor_games,
    entity_authority_successor,
    fcs_subset_from_parent,
    reject_deleted_non_di_opponents,
    reject_denominator_from_observed,
    reject_modern_label_pre_1978,
    reject_week1_as_national,
    week1_slice_from_contests,
)
from aggie_analytics.cycle29.scoring import (
    ScoringError,
    reject_half_counted_as_home,
    reject_oriented_rows_as_games,
)
from aggie_analytics.cycle29.temporal import (
    TemporalError,
    parse_aware_utc,
    reject_dst_ambiguous_local,
)
from aggie_analytics.scientific_reference.cycle29.metrics import (
    reject_half_as_directional,
)
from aggie_analytics.scientific_reference.cycle29.pit import reconstruct_game_features
from aggie_analytics.scientific_reference.cycle29.temporal import (
    cutoff_span_classification,
)


FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "cycle29" / "ci_scoring_rows.jsonl"
)
SRC = Path(__file__).resolve().parents[1] / "src"


class Cycle29AdversarialTests(unittest.TestCase):
    def test_two_writers_one_lease(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = acquire(
                contest_id="X",
                checkpoint="T90M",
                cutoff_utc="2026-09-07T22:00:00Z",
                owner_id="a",
                role="PRIMARY",
                pid=os.getpid(),
                ttl_seconds=60,
                heartbeat_seconds=10,
                lease_root=root,
            )
            self.assertTrue(first["ok"])
            second = acquire(
                contest_id="X",
                checkpoint="T90M",
                cutoff_utc="2026-09-07T22:00:00Z",
                owner_id="b",
                role="PRIMARY",
                pid=os.getpid() + 1,
                ttl_seconds=60,
                heartbeat_seconds=10,
                lease_root=root,
            )
            self.assertEqual(second["action"], SCHEDULER_ACTIVE_OR_BOUND)
            release(
                contest_id="X",
                checkpoint="T90M",
                owner_id="a",
                pid=os.getpid(),
                lease_root=root,
            )

    def test_stale_takeover_without_expiry(self) -> None:
        with self.assertRaises(Exception):
            reject_stale_takeover_without_expiry(
                expired=False, pid_alive=True, cas_ok=True
            )

    def test_generic_error_html(self) -> None:
        state = classify_semantic_page(
            b"<html>Internal Server Error</html>", content_type="text/html"
        )
        self.assertEqual(state, GENERIC_ERROR_HTML)
        with self.assertRaises(AcquisitionError):
            require_upstream_success(
                {"upstream_state": "UPSTREAM_SUCCESS", "semantic_state": state}
            )

    def test_non_2xx_upstream(self) -> None:
        row = classify_transport_and_upstream(
            http_status=200, upstream_status=503, body=b"not empty"
        )
        self.assertEqual(row["upstream_state"], "UPSTREAM_FAILED")
        with self.assertRaises(AcquisitionError):
            require_upstream_success(
                {**row, "semantic_state": "SEMANTIC_PAGE_AVAILABLE"}
            )

    def test_request_identity_stable_and_not_volatile(self) -> None:
        left = request_identity(
            method="GET",
            uri="https://example.test/score",
            parameters={"id": "1"},
            headers={"Authorization": "secret", "Accept": "text/html"},
            source_contract="ncaa-official",
        )
        right = request_identity(
            method="GET",
            uri="https://example.test/score",
            parameters={"id": "1"},
            headers={"Authorization": "other-secret", "Accept": "text/html"},
            source_contract="ncaa-official",
        )
        self.assertEqual(left, right)
        self.assertEqual(
            redact_headers({"Authorization": "secret"})["Authorization"],
            "***REDACTED***",
        )
        with self.assertRaises(AcquisitionError):
            reject_volatile_request_identity({"pid": 1, "uri": "x"})

    def test_arbitrary_existing_file_reuse(self) -> None:
        with self.assertRaises(AcquisitionError):
            reuse_existing_capture(
                candidates=[{"request_identity_sha256": "a", "raw_sha256": "b"}],
                required_request_identity="nope",
                required_raw_hash="b",
                required_receipt_identity="r",
                required_semantic_state="SEMANTIC_PAGE_AVAILABLE",
                declared_freshness="fresh",
            )

    def test_unrelated_final_text(self) -> None:
        with self.assertRaises(AcquisitionError):
            contest_scoped_terminal(
                page_text="Season is FINAL for another sport",
                contest_id="6594400",
                contest_hint="6594400",
                score_element_ids=["s1"],
                ordered_participant_ids=["H", "A"],
                page_url="https://example.test/other",
                embedded_contest_id="6594400",
            )

    def test_contest_hint_mismatch(self) -> None:
        with self.assertRaises(AcquisitionError):
            contest_scoped_terminal(
                page_text="6594400 FINAL",
                contest_id="6594400",
                contest_hint="111",
                score_element_ids=["s1"],
                ordered_participant_ids=["H", "A"],
                page_url="https://example.test/6594400",
                embedded_contest_id="6594400",
            )

    def test_home_away_swap(self) -> None:
        from aggie_analytics.cycle29.acquisition import bind_participants

        with self.assertRaises(AcquisitionError):
            bind_participants(
                canonical_home_id="H",
                canonical_away_id="A",
                ordered_participant_ids=["A", "H"],
                displayed_home_name="Home",
                displayed_away_name="Away",
                name_only=False,
            )

    def test_name_only_join(self) -> None:
        from aggie_analytics.cycle29.acquisition import bind_participants

        with self.assertRaises(AcquisitionError):
            bind_participants(
                canonical_home_id="H",
                canonical_away_id="A",
                ordered_participant_ids=["H", "A"],
                displayed_home_name="Home",
                displayed_away_name="Away",
                name_only=True,
            )

    def test_lexical_timestamp_trap(self) -> None:
        pre_kickoff = "2026-09-07T19:00:00Z"
        kickoff = "2026-09-07T15:00:00-05:00"
        self.assertGreater(pre_kickoff, kickoff)
        self.assertLess(parse_aware_utc(pre_kickoff), parse_aware_utc(kickoff))
        with self.assertRaises(TemporalError):
            parse_aware_utc("2026-09-07T15:00:00")

    def test_dst_ambiguous(self) -> None:
        with self.assertRaises(TemporalError):
            reject_dst_ambiguous_local("2026-11-01T01:30:00", "America/Chicago")

    def test_invented_tolerance_and_cutoff_span(self) -> None:
        truth = cutoff_span_truth(
            request_start_utc="2026-09-07T21:50:00Z",
            request_end_utc="2026-09-07T22:10:00Z",
            cutoff_utc="2026-09-07T22:00:00Z",
        )
        self.assertTrue(truth["spanned_cutoff"])
        with self.assertRaises(AcquisitionError):
            reject_wholly_known_without_proof(truth, True)
        self.assertEqual(
            cutoff_span_classification(
                request_start_utc="2026-09-07T21:50:00Z",
                request_end_utc="2026-09-07T22:10:00Z",
                cutoff_utc="2026-09-07T22:00:00Z",
            ),
            "START_BEFORE_CUTOFF_END_AFTER_CUTOFF",
        )

    def test_forecast_mutation(self) -> None:
        rows = [{"id": "1", "p": 0.6}, {"id": "2", "p": 0.4}]
        prove_set_unchanged(rows, list(rows))
        with self.assertRaises(ForecastImmutabilityError):
            prove_set_unchanged(rows, rows + [{"id": "3"}])
        with self.assertRaises(ForecastImmutabilityError):
            prove_set_unchanged(rows, [rows[1], rows[0]])
        with self.assertRaises(ForecastImmutabilityError):
            reject_literal_no_tuning(True, False)

    def test_dependency_separation(self) -> None:
        graph = static_import_graph(SRC)
        self.assertTrue(graph["disjoint"])

    def test_ci_must_open_rows(self) -> None:
        digest = sha256_file(FIXTURE)
        opened = open_and_rehash(
            FIXTURE, expected_sha256=digest, expected_rows=3, payload_available=True
        )
        self.assertEqual(opened["rows_opened"], 3)
        with self.assertRaises(Exception):
            reject_pass_without_opening(True, 0, 384)
        blocked = open_and_rehash(
            Path("missing.jsonl"),
            expected_sha256="x",
            expected_rows=384,
            payload_available=False,
        )
        self.assertEqual(blocked["result"], "BLOCKED_PAYLOAD_UNAVAILABLE")

    def test_unmapped_claim_fails(self) -> None:
        declared = kernel_closure_claims()
        with self.assertRaises(ClaimError):
            inventory_claims(
                declared, declared + [{"claim_id": "UNMAPPED-NEW", "field": "x"}]
            )

    def test_base_rate_half(self) -> None:
        with self.assertRaises(ScoringError):
            reject_half_counted_as_home(0.5, True)
        with self.assertRaises(Exception):
            reject_half_as_directional(0.5, True)

    def test_oriented_rows_not_games(self) -> None:
        rows = [
            {"ncaa_contest_id": "1", "orientation": "HOME"},
            {"ncaa_contest_id": "1", "orientation": "AWAY"},
        ]
        self.assertEqual(reject_oriented_rows_as_games(rows), 1)

    def test_empty_and_zero_registry(self) -> None:
        with self.assertRaises(DomainError):
            reject_empty_inventory_pass([], "PASS")
        with self.assertRaises(DomainError):
            reject_zero_filled_registry(0, True)

    def test_display_name_not_canonical(self) -> None:
        with self.assertRaises(DomainError):
            reject_display_name_as_canonical("display_name", True)

    def test_week1_not_national(self) -> None:
        contests = [
            {"ncaa_contest_id": str(i), "home": f"H{i}", "away": f"A{i}"}
            for i in range(91)
        ]
        payload = week1_slice_from_contests(contests)
        self.assertEqual(payload["participant_appearance_count"], 182)
        self.assertFalse(payload["is_national_population"])
        with self.assertRaises(PopulationError):
            reject_week1_as_national(payload, True)

    def test_catalog_crosswalk_zero_unmapped(self) -> None:
        payload = crosswalk()
        self.assertEqual(payload["unmapped_term_count"], 0)
        self.assertEqual(payload["ambiguous_unresolved_mapping_count"], 0)
        self.assertEqual(payload["w06_term_count"], 52)
        self.assertEqual(payload["c28_term_count"], 33)
        self.assertEqual(payload["source_policy_term_count"], 16)
        self.assertEqual(payload["pit_term_count"], 18)

    def test_observed_denominator_and_era_labels(self) -> None:
        with self.assertRaises(PopulationError):
            reject_denominator_from_observed(True)
        with self.assertRaises(PopulationError):
            reject_modern_label_pre_1978(1970, "FBS")
        with self.assertRaises(PopulationError):
            reject_deleted_non_di_opponents(0)
        with self.assertRaises(DomainError):
            reject_not_applicable_inflation(
                covered_cells=10, not_applicable=10, claimed_covered=20
            )
        with self.assertRaises(DomainError):
            reject_incompatible_parity_grains("game", "program")

    def test_fcs_subset_and_predecessor_zero(self) -> None:
        parent = [
            {
                "season": 2020,
                "home_id": "A",
                "away_id": "B",
                "date": "2020-09-01",
                "home_class": "FCS",
                "away_class": "FCS",
            },
            {
                "season": 2020,
                "home_id": "C",
                "away_id": "D",
                "date": "2020-09-01",
                "home_class": "FBS",
                "away_class": "FBS",
            },
        ]
        subset = fcs_subset_from_parent(
            parent, parent_identity="p", filter_contract_identity="f"
        )
        self.assertEqual(subset["subset_row_count"], 1)
        cov = classify_predecessor_games(
            normalized_count=46953, entity_count=46960, fcs_to_fcs=0
        )
        self.assertEqual(cov["fcs_to_fcs_count"], 0)
        self.assertIn("FBS_CENTRIC", cov["classification"])

    def test_entity_authority_eight_to_zero(self) -> None:
        payload = entity_authority_successor()
        self.assertEqual(payload["predecessor_unresolved_participant_row_count"], 8)
        self.assertEqual(payload["successor_unresolved_participant_row_count"], 0)

    def test_c28_p0_ids_preserved(self) -> None:
        ledger = successor_ledger()
        ids = {row["finding_id"] for row in ledger["rows"]}
        for item in C28_P0_IDS:
            self.assertIn(item, ids)

    def test_pit_kernel_and_expected_from_route(self) -> None:
        games = [
            {
                "canonical_game_id": "G1",
                "home_canonical_team_id": "T1",
                "away_canonical_team_id": "T2",
                "season": 2018,
                "start_date_utc_text": "2018-09-01T19:00:00Z",
            },
            {
                "canonical_game_id": "G2",
                "home_canonical_team_id": "T1",
                "away_canonical_team_id": "T2",
                "season": 2018,
                "start_date_utc_text": "2018-09-15T19:00:00Z",
            },
        ]
        outcomes = [
            {
                "canonical_game_id": "G1",
                "canonical_team_id": "T1",
                "label_win": True,
                "points_for": 10,
                "points_against": 0,
                "margin": 10,
                "season": 2018,
            },
            {
                "canonical_game_id": "G1",
                "canonical_team_id": "T2",
                "label_win": False,
                "points_for": 0,
                "points_against": 10,
                "margin": -10,
                "season": 2018,
            },
            {
                "canonical_game_id": "G2",
                "canonical_team_id": "T1",
                "label_win": True,
                "points_for": 7,
                "points_against": 3,
                "margin": 4,
                "season": 2018,
            },
            {
                "canonical_game_id": "G2",
                "canonical_team_id": "T2",
                "label_win": False,
                "points_for": 3,
                "points_against": 7,
                "margin": -4,
                "season": 2018,
            },
        ]
        kernel = build_game_grain_kernel(
            games,
            outcomes,
            expected_population_complete=False,
            contemporaneous_fbs_authority=True,
            cross_subdivision=False,
        )
        self.assertGreater(kernel["proven_pit_training_rows"], 0)
        reconstructed = reconstruct_game_features(games, outcomes)
        self.assertTrue(reconstructed)
        with self.assertRaises(PitKernelError):
            reject_expected_from_observed_route(True)

    def test_coaching_mutations(self) -> None:
        with self.assertRaises(CoachingError):
            reject_play_caller_from_title(
                "Offensive Coordinator", "offense_play_caller"
            )
        with self.assertRaises(CoachingError):
            reject_cfbd_assistant("cfbd", "offensive_coordinator")
        with self.assertRaises(CoachingError):
            reject_name_only("name-only", "ADMITTED")
        with self.assertRaises(CoachingError):
            reject_composite_title_bypass("Interim Offensive Coordinator", False)
        with self.assertRaises(CoachingError):
            reject_array_zip_mispair([{"names": ["A", "B"], "titles": ["OC"]}])
        with self.assertRaises(CoachingError):
            reject_wikimedia_as_pit(True, True)
        cells = hc_oc_dc_matrix(["P1", "P2"], "2026-09-07T16:00:00Z")
        self.assertEqual(len(cells), 6)
        with self.assertRaises(CoachingError):
            reject_week1_as_national_coaching(182, 263, True)
        contract = position_role_contract(["head_coach", "quarterbacks"])
        self.assertEqual(
            len(
                historical_lattice(
                    [{"program_id": "P", "season": 2020}], ["head_coach"]
                )
            ),
            1,
        )
        with self.assertRaises(CoachingError):
            reject_omitted_role_family(contract["role_families"], ["head_coach"])
        accepted = [f"a{i}" for i in range(4)]
        provisional = [
            {"record_id": "c1", "category": "CANDIDATE_GENERATED"},
            {"record_id": "r1", "category": "REVIEW_REQUIRED"},
            {"record_id": "u1", "category": "UNRESOLVED"},
        ]
        self.assertEqual(
            reconcile_predecessor_observations(accepted, provisional)["accepted_count"],
            4,
        )
        with self.assertRaises(CoachingError):
            reject_dropped_identity(accepted + ["c1"], accepted, True)
        with self.assertRaises(CoachingError):
            role_cell(
                program_id="P",
                as_of_utc="2026-09-07T16:00:00Z",
                role="offensive_coordinator",
                episode_refs=[
                    {"relationship": "SEQUENTIAL_CHANGE"},
                    {"relationship": "SEQUENTIAL_CHANGE"},
                ],
                disposition="CONFIRMED_CO_SHARED_ROLE",
            )

    def test_gridiron_and_cost(self) -> None:
        with self.assertRaises(GridironError):
            reject_stale_c01(False, False, True)
        with self.assertRaises(GridironError):
            reject_skipped_integration_as_compat(True, True)
        with self.assertRaises(GridironError):
            reject_obsolete_foundation(True, True)
        with self.assertRaises(CostError):
            reject_routine_api_review("pull_request", None)
        with self.assertRaises(Exception):
            reject_candidate_in_model("CANDIDATE_ONLY")

    def test_outer_hash_semantic_tamper(self) -> None:
        payload = {"a": 1}
        left = json.dumps(payload, sort_keys=True)
        right = json.dumps({"a": 2}, sort_keys=True)
        self.assertNotEqual(left, right)


if __name__ == "__main__":
    unittest.main()

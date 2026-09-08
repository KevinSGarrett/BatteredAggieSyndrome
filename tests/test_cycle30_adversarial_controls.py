"""Cycle #30 adversarial controls: every manager/hosted counterexample."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aggie_analytics.cycle30.acquisition import (
    AcquisitionError,
    GENERIC_ERROR_HTML,
    NOT_TERMINAL,
    TERMINAL_STATUS_ESTABLISHED,
    UPSTREAM_FAILED,
    classify_semantic_page,
    classify_transport_and_upstream,
    contest_scoped_terminal,
    bind_actual_upstream,
)
from aggie_analytics.cycle30.admission import prove_coaching_not_modeled
from aggie_analytics.cycle30.claims import (
    ClaimError,
    discover_authority_claims,
    inventory_claims,
    reject_empty_science_pass,
    reject_vacuous_row_count,
)
from aggie_analytics.cycle30.coaching import (
    CoachingError,
    attempt_ledger_count,
    extract_row_bound_staff,
    hc_oc_dc_matrix,
    reject_literal_attempted,
)
from aggie_analytics.cycle30.cost import attestation_check
from aggie_analytics.cycle30.dependency import static_import_graph
from aggie_analytics.cycle30.domains import crosswalk
from aggie_analytics.cycle30.findings import (
    C28_P0_IDS,
    C29_FINDING_IDS,
    successor_ledger,
)
from aggie_analytics.cycle30.pit_kernel import (
    PitKernelError,
    build_game_grain_kernel,
    rebuild_kernel_comparison,
    validate_oriented_outcomes,
    validate_row_authority,
)
from aggie_analytics.cycle30.populations import (
    PopulationError,
    classify_pair_counts,
    reject_synthetic_real_denominator,
)
from aggie_analytics.cycle30.scoring import (
    ScoringError,
    admit_official_final,
    directional_from_probability,
    reject_half_counted_as_home,
)
from aggie_analytics.cycle30.site_context import (
    SITE_NEUTRAL,
    SITE_UNKNOWN,
    classify_site,
    haversine_km,
    ordinary_home_exposure,
    persist_design_row,
    travel_row,
    vincenty_km,
)
from aggie_analytics.cycle30.temporal import (
    TemporalError,
    parse_aware_utc,
    reject_midnight_as_date_only,
    resolve_precision,
)
from aggie_analytics.scientific_reference.cycle30.pit import (
    compare_producer_rows,
    reconstruct_game_features,
)
from aggie_analytics.scientific_reference.cycle30.temporal import (
    reject_midnight_as_date_only as independent_reject_midnight,
)


ROOT = Path(__file__).resolve().parents[1]


def _games_outcomes():
    games = [
        {
            "canonical_game_id": "GAME:A",
            "home_canonical_team_id": "TEAM:1",
            "away_canonical_team_id": "TEAM:2",
            "season": 2018,
            "start_date_utc_text": "2018-09-01T19:00:00Z",
            "date_precision": "INSTANT",
            "home_points": 31,
            "away_points": 10,
            "source_id": "SRC-TEST",
        },
        {
            "canonical_game_id": "GAME:B",
            "home_canonical_team_id": "TEAM:1",
            "away_canonical_team_id": "TEAM:3",
            "season": 2018,
            "start_date_utc_text": "2018-09-08T19:00:00Z",
            "date_precision": "INSTANT",
            "home_points": 24,
            "away_points": 17,
            "source_id": "SRC-TEST",
        },
        {
            "canonical_game_id": "GAME:C",
            "home_canonical_team_id": "TEAM:2",
            "away_canonical_team_id": "TEAM:3",
            "season": 2019,
            "start_date_utc_text": "2019-09-07T19:00:00Z",
            "date_precision": "INSTANT",
            "home_points": 20,
            "away_points": 13,
            "source_id": "SRC-TEST",
        },
    ]
    outcomes = [
        {
            "canonical_game_id": "GAME:A",
            "canonical_team_id": "TEAM:1",
            "label_win": True,
            "points_for": 31,
            "points_against": 10,
            "margin": 21,
            "season": 2018,
        },
        {
            "canonical_game_id": "GAME:A",
            "canonical_team_id": "TEAM:2",
            "label_win": False,
            "points_for": 10,
            "points_against": 31,
            "margin": -21,
            "season": 2018,
        },
        {
            "canonical_game_id": "GAME:B",
            "canonical_team_id": "TEAM:1",
            "label_win": True,
            "points_for": 24,
            "points_against": 17,
            "margin": 7,
            "season": 2018,
        },
        {
            "canonical_game_id": "GAME:B",
            "canonical_team_id": "TEAM:3",
            "label_win": False,
            "points_for": 17,
            "points_against": 24,
            "margin": -7,
            "season": 2018,
        },
        {
            "canonical_game_id": "GAME:C",
            "canonical_team_id": "TEAM:2",
            "label_win": True,
            "points_for": 20,
            "points_against": 13,
            "margin": 7,
            "season": 2019,
        },
        {
            "canonical_game_id": "GAME:C",
            "canonical_team_id": "TEAM:3",
            "label_win": False,
            "points_for": 13,
            "points_against": 20,
            "margin": -7,
            "season": 2019,
        },
    ]
    return games, outcomes


class Cycle30AdversarialTests(unittest.TestCase):
    def test_claim_discovery_fails_undeclared_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp)
            (art / "KNOWN.json").write_text(
                json.dumps({"row_count": 1}), encoding="utf-8"
            )
            (art / "NEW_SCIENTIFIC_CLAIM.json").write_text(
                json.dumps(
                    {"new_proven_row_count": 999, "scientific_status": "VERIFIED"}
                ),
                encoding="utf-8",
            )
            discovered = discover_authority_claims(art)
            declared = [
                {
                    "claim_id": "c1",
                    "artifact_path": "KNOWN.json",
                    "pointer": "/row_count",
                    "row_identity": "",
                    "field": "row_count",
                    "population": "KNOWN.json",
                    "value_class": "integer",
                    "formula": "count",
                    "numerator": 1,
                    "denominator": 1,
                    "source_identities": [],
                    "temporal_authority": "n/a",
                    "producer": "p",
                    "validator": "v",
                    "independent_reference": "r",
                    "dependencies": [],
                    "trust_class": "t",
                }
            ]
            with self.assertRaises(ClaimError):
                inventory_claims(declared, discovered)

    def test_wrong_artifact_same_field_name_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp)
            (art / "ALIEN.json").write_text(
                json.dumps({"row_count": 4}), encoding="utf-8"
            )
            discovered = discover_authority_claims(art)
            declared = [
                {
                    "claim_id": "c1",
                    "artifact_path": "OTHER.json",
                    "pointer": "/row_count",
                    "row_identity": "",
                    "field": "row_count",
                    "population": "OTHER.json",
                    "value_class": "integer",
                    "formula": "count",
                    "numerator": 4,
                    "denominator": 4,
                    "source_identities": [],
                    "temporal_authority": "n/a",
                    "producer": "p",
                    "validator": "v",
                    "independent_reference": "r",
                    "dependencies": [],
                    "trust_class": "t",
                }
            ]
            with self.assertRaises(ClaimError):
                inventory_claims(declared, discovered)

    def test_unreadable_json_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp)
            (art / "BROKEN.json").write_text("{not-json", encoding="utf-8")
            with self.assertRaises(ClaimError):
                discover_authority_claims(art)

    def test_empty_producer_cannot_pass_science(self) -> None:
        with self.assertRaises(ClaimError):
            reject_empty_science_pass(
                mode="SCIENCE",
                producer_modules=[],
                reference_modules=[Path("x.py")],
                bound_row_files=[],
                claimed_row_count=0,
            )

    def test_vacuous_999999_against_empty_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.jsonl"
            path.write_text("", encoding="utf-8")
            with self.assertRaises(ClaimError):
                reject_vacuous_row_count(path, 999999)

    def test_both_teams_win_rejected(self) -> None:
        game = {
            "canonical_game_id": "G1",
            "home_canonical_team_id": "H",
            "away_canonical_team_id": "A",
        }
        outcomes = [
            {
                "canonical_game_id": "G1",
                "canonical_team_id": "H",
                "label_win": True,
                "points_for": 10,
                "points_against": 0,
                "margin": 1000,
            },
            {
                "canonical_game_id": "G1",
                "canonical_team_id": "A",
                "label_win": True,
                "points_for": 0,
                "points_against": 10,
                "margin": 1000,
            },
        ]
        with self.assertRaises(PitKernelError):
            validate_oriented_outcomes(game, outcomes)

    def test_tie_not_silent_home_loss(self) -> None:
        game = {
            "canonical_game_id": "TIE1",
            "home_canonical_team_id": "H",
            "away_canonical_team_id": "A",
        }
        outcomes = [
            {
                "canonical_game_id": "TIE1",
                "canonical_team_id": "H",
                "label_win": False,
                "label_tie": True,
                "points_for": 17,
                "points_against": 17,
                "margin": 0,
            },
            {
                "canonical_game_id": "TIE1",
                "canonical_team_id": "A",
                "label_win": False,
                "label_tie": True,
                "points_for": 17,
                "points_against": 17,
                "margin": 0,
            },
        ]
        validated = validate_oriented_outcomes(game, outcomes)
        self.assertTrue(validated["tie"])
        kernel = build_game_grain_kernel(
            [
                {
                    **game,
                    "season": 2018,
                    "start_date_utc_text": "2018-09-01T19:00:00Z",
                    "date_precision": "INSTANT",
                }
            ],
            [{**row, "season": 2018} for row in outcomes],
            expected_population_complete=False,
        )
        self.assertEqual(kernel["proven_pit_training_rows"], 0)
        self.assertTrue(
            any(
                row["blocker"] == "ABSTAIN_TIE_EXCLUDED_FROM_BINARY_ESTIMAND"
                for row in kernel["blockers"]
            )
        )

    def test_global_authority_flag_is_not_publication_proof(self) -> None:
        class_ = validate_row_authority(
            {
                "source_id": "SRC",
                "effective_utc": "2018-09-01T19:00:00Z",
                "known_at_utc": "2018-09-01T19:00:00Z",
                "receipt_sha256": "abc",
                "classification": "fbs",
                "evidence_class": "FLAG_ONLY",
                "contemporaneous_fbs_authority": True,
            },
            target_cutoff="2018-09-01T19:00:00Z",
        )
        self.assertEqual(class_, "SOURCE_AUTHORITY_UNPROVEN")

    def test_future_publication_rejected(self) -> None:
        with self.assertRaises(PitKernelError):
            validate_row_authority(
                {
                    "source_id": "SRC",
                    "effective_utc": "2018-09-01T19:00:00Z",
                    "known_at_utc": "2018-09-02T00:00:00Z",
                    "receipt_sha256": "abc",
                    "classification": "fbs",
                    "evidence_class": "PUBLICATION",
                    "source_publication_utc": "2018-09-08T00:00:00Z",
                },
                target_cutoff="2018-09-01T19:00:00Z",
            )

    def test_future_append_rebuild_stable(self) -> None:
        games, outcomes = _games_outcomes()
        extra_game = {
            "canonical_game_id": "GAME:D",
            "home_canonical_team_id": "TEAM:1",
            "away_canonical_team_id": "TEAM:2",
            "season": 2020,
            "start_date_utc_text": "2020-09-05T19:00:00Z",
            "date_precision": "INSTANT",
            "home_points": 14,
            "away_points": 7,
            "source_id": "SRC-TEST",
        }
        extra_outcomes = [
            {
                "canonical_game_id": "GAME:D",
                "canonical_team_id": "TEAM:1",
                "label_win": True,
                "points_for": 14,
                "points_against": 7,
                "margin": 7,
                "season": 2020,
            },
            {
                "canonical_game_id": "GAME:D",
                "canonical_team_id": "TEAM:2",
                "label_win": False,
                "points_for": 7,
                "points_against": 14,
                "margin": -7,
                "season": 2020,
            },
        ]
        result = rebuild_kernel_comparison(
            games,
            outcomes,
            [extra_game],
            extra_outcomes,
            expected_population_complete=False,
        )
        self.assertTrue(result["shuffle_stable"])
        self.assertTrue(result["future_append_stable"])

    def test_independent_reconstruction_agrees(self) -> None:
        games, outcomes = _games_outcomes()
        produced = build_game_grain_kernel(
            games, outcomes, expected_population_complete=False
        )
        reconstructed = reconstruct_game_features(games, outcomes)
        compare_producer_rows(
            [*produced["rows"], *produced["retrospective_rows"]], reconstructed
        )

    def test_neighbor_final_is_not_terminal(self) -> None:
        page = "contest 123 2nd quarter adjacent contest 456 Final"
        status = contest_scoped_terminal(
            page_text=page,
            contest_id="123",
            contest_hint="123",
            score_element_ids=["s1"],
            ordered_participant_ids=["H", "A"],
            page_url="https://example.test/contest/123",
            embedded_contest_id="123",
        )
        self.assertEqual(status, NOT_TERMINAL)

    def test_contest_scoped_final_accepted(self) -> None:
        page = '<span id="livestream_status_123" class="livestream_status livestream_game_over">Final</span>'
        status = contest_scoped_terminal(
            page_text=page,
            contest_id="123",
            contest_hint="123",
            score_element_ids=["s1"],
            ordered_participant_ids=["H", "A"],
            page_url="https://example.test/contest/123",
            embedded_contest_id="123",
        )
        self.assertEqual(status, TERMINAL_STATUS_ESTABLISHED)

    def test_provider_200_upstream_500_fails_admission(self) -> None:
        classification = classify_transport_and_upstream(
            http_status=200, upstream_status=500, body=b"<html>ok</html>"
        )
        self.assertEqual(classification["upstream_state"], UPSTREAM_FAILED)
        with self.assertRaises(AcquisitionError):
            bind_actual_upstream(
                http_status=200, upstream_status=500, body=b"<html>ok</html>"
            )

    def test_error_shell_not_success(self) -> None:
        self.assertEqual(
            classify_semantic_page(
                b"<html>Internal Server Error</html>", content_type="text/html"
            ),
            GENERIC_ERROR_HTML,
        )

    def test_pair_counts_derived_home_to_away(self) -> None:
        games = [
            {
                "season": 2013,
                "home_classification": "fbs",
                "away_classification": "fcs",
            },
            {
                "season": 2013,
                "home_classification": "fcs",
                "away_classification": "fbs",
            },
            {"season": 2013, "home_classification": "fbs", "away_classification": None},
            {"season": 2013, "home_classification": None, "away_classification": "fbs"},
            {
                "season": 2013,
                "home_classification": "fbs",
                "away_classification": "fbs",
            },
        ]
        payload = classify_pair_counts(games)
        counts = payload["pair_counts_home_to_away"]
        self.assertEqual(counts["orientation"], "home→away")
        self.assertEqual(counts["fbs→fcs"], 1)
        self.assertEqual(counts["fcs→fbs"], 1)
        self.assertEqual(counts["fbs→null"], 1)
        self.assertEqual(counts["null→fbs"], 1)
        self.assertEqual(counts["fbs→fbs"], 1)

    def test_coach_equal_cardinality_wrong_pairing_rejected(self) -> None:
        with self.assertRaises(CoachingError):
            extract_row_bound_staff(
                [{"names": ["A", "B"], "titles": ["HC", "OC"], "span_id": "x"}]
            )

    def test_row_bound_staff_extracts(self) -> None:
        rows = extract_row_bound_staff(
            [
                {"person": "Jane Doe", "title": "Head Coach", "span_id": "r1"},
                {"person": "John Roe", "title": "Interim OC", "span_id": "r2"},
            ]
        )
        self.assertEqual(rows[1]["interim"], True)

    def test_midnight_not_date_only(self) -> None:
        instant = parse_aware_utc("2020-09-06T00:00:00Z")
        self.assertEqual(
            resolve_precision(declared_precision=None, instant=instant), "UNKNOWN"
        )
        with self.assertRaises(TemporalError):
            reject_midnight_as_date_only(instant, True)
        with self.assertRaises(Exception):
            independent_reject_midnight(instant, True)

    def test_missing_neutral_is_unknown(self) -> None:
        self.assertEqual(
            classify_site(
                official_neutral=None,
                provider_neutral=None,
                missing_annotation=True,
            ),
            SITE_UNKNOWN,
        )
        self.assertIsNone(
            ordinary_home_exposure(
                site_class=SITE_UNKNOWN, orientation_is_designated_home=True
            )
        )

    def test_verified_neutral_masks_ordinary_home(self) -> None:
        self.assertEqual(
            ordinary_home_exposure(
                site_class=SITE_NEUTRAL, orientation_is_designated_home=True
            ),
            0.0,
        )

    def test_travel_missing_coordinates_are_null(self) -> None:
        row = travel_row(
            canonical_game_id="G",
            team_id="T",
            origin_lat=None,
            origin_lon=None,
            venue_lat=44.5013,
            venue_lon=-88.0622,
            origin_class="CAMPUS_PROXY",
            origin_id="ND",
        )
        self.assertIsNone(row["distance_km_haversine"])
        self.assertEqual(row["missing_reason"], "MISSING_COORDINATES")

    def test_lambeau_travel_both_teams(self) -> None:
        # Green Bay, South Bend, Madison campus proxies.
        gb = (44.5013, -88.0622)
        nd = (41.6984, -86.2339)
        uw = (43.0696, -89.4126)
        nd_km = haversine_km(nd[0], nd[1], gb[0], gb[1])
        uw_km = haversine_km(uw[0], uw[1], gb[0], gb[1])
        self.assertGreater(nd_km, 200)
        self.assertGreater(uw_km, 100)
        self.assertLess(abs(nd_km - vincenty_km(nd[0], nd[1], gb[0], gb[1])), 5)

    def test_display_program_ids_rejected(self) -> None:
        with self.assertRaises(CoachingError):
            hc_oc_dc_matrix(["DISPLAY:Texas A&M"], "2026-09-07T16:00:00Z")
        with self.assertRaises(PopulationError):
            reject_synthetic_real_denominator(
                [{"program_id": "P1", "artifact_class": "REAL_EVIDENCE"}]
            )

    def test_attempt_ledger_not_literal(self) -> None:
        ledger = attempt_ledger_count([])
        self.assertFalse(ledger["attempted"])
        with self.assertRaises(CoachingError):
            reject_literal_attempted({"attempted": True}, 0)

    def test_half_probability_not_directional(self) -> None:
        self.assertEqual(directional_from_probability(0.5), "NO_DIRECTION")
        with self.assertRaises(ScoringError):
            reject_half_counted_as_home(0.5, True)

    def test_literal_upstream_success_not_enough(self) -> None:
        with self.assertRaises(ScoringError):
            admit_official_final(
                page_text="Final",
                contest_id="1",
                contest_hint="1",
                score_element_ids=["s"],
                ordered_participant_ids=["H", "A"],
                page_url="https://example.test/1",
                embedded_contest_id="1",
                canonical_home_id="H",
                canonical_away_id="A",
                displayed_home_name="Home",
                displayed_away_name="Away",
                name_only=False,
                home_points=21,
                away_points=14,
                kickoff_utc="2026-09-05T16:00:00Z",
                retrieval_utc="2026-09-05T23:00:00Z",
                http_status=200,
                upstream_status=500,
                body=b"<html>ok</html>",
            )

    def test_one_to_many_domains_not_collapsed(self) -> None:
        payload = crosswalk()
        terms = {
            (row["predecessor_term"], row["canonical_domain_id"])
            for row in payload["mappings"]
            if row["predecessor_catalog"] == "C28_33"
        }
        self.assertIn(("total_team_score", "CURRENT-TOTAL-TEAM-SCORE"), terms)
        self.assertIn(("calibration_ood_uncertainty", "CURRENT-CALIBRATION-OOD"), terms)
        self.assertIn(("bas_residual", "CURRENT-BAS-INFERENCE"), terms)
        self.assertIn(("travel_rest_time_zone", "CURRENT-REST"), terms)
        self.assertIn(("travel_rest_time_zone", "CURRENT-TIMEZONE"), terms)
        self.assertIsNone(payload["ambiguous_unresolved_mapping_count"])

    def test_findings_preserve_ids(self) -> None:
        ledger = successor_ledger()
        ids = {row["finding_id"] for row in ledger["rows"]}
        self.assertTrue(set(C28_P0_IDS).issubset(ids))
        self.assertTrue(set(C29_FINDING_IDS).issubset(ids))

    def test_no_api_attestation_is_not_review(self) -> None:
        payload = attestation_check(
            head_sha="abc", review_identities=[], api_calls=0, scientific_reviews=[]
        )
        self.assertEqual(payload["scientific_review_gate"], "PENDING_BLOCKED")
        self.assertTrue(payload["no_api_attestation_is_not_scientific_review"])

    def test_coaching_not_consumed(self) -> None:
        prove_coaching_not_modeled(
            {"ordinary_home_exposure": 1.0, "coach_tenure": "NOT_CONSUMED"}
        )

    def test_producer_reference_disjoint(self) -> None:
        graph = static_import_graph(ROOT / "src")
        self.assertTrue(graph["disjoint"])
        self.assertGreater(graph["producer_module_count"], 0)
        self.assertGreater(graph["reference_module_count"], 0)

    def test_travel_available_not_consumed_by_default(self) -> None:
        row = persist_design_row(
            canonical_game_id="G",
            ordinary_home_exposure_value=0.0,
            site_class=SITE_NEUTRAL,
            travel_home_km=220.0,
            travel_away_km=130.0,
            consumed_columns=["ordinary_home_exposure"],
        )
        self.assertTrue(row["travel_available"])
        self.assertFalse(row["travel_consumed"])

    def test_empty_science_cannot_pass(self) -> None:
        with self.assertRaises(ClaimError):
            reject_empty_science_pass(
                mode="SCIENCE",
                producer_modules=[],
                reference_modules=[],
                bound_row_files=[],
                claimed_row_count=999999,
            )

    def test_rebuild_future_append_stable(self) -> None:
        games, outcomes = _games_outcomes()
        extra_game = {
            "canonical_game_id": "GAME:D",
            "home_canonical_team_id": "TEAM:4",
            "away_canonical_team_id": "TEAM:5",
            "season": 2019,
            "start_date_utc_text": "2019-11-01T19:00:00Z",
            "date_precision": "INSTANT",
            "home_points": 14,
            "away_points": 7,
            "source_id": "SRC-TEST",
        }
        extra_outcomes = [
            {
                "canonical_game_id": "GAME:D",
                "canonical_team_id": "TEAM:4",
                "label_win": True,
                "points_for": 14,
                "points_against": 7,
                "margin": 7,
                "season": 2019,
            },
            {
                "canonical_game_id": "GAME:D",
                "canonical_team_id": "TEAM:5",
                "label_win": False,
                "points_for": 7,
                "points_against": 14,
                "margin": -7,
                "season": 2019,
            },
        ]
        result = rebuild_kernel_comparison(
            games,
            outcomes,
            [extra_game],
            extra_outcomes,
            expected_population_complete=False,
        )
        self.assertTrue(result["shuffle_stable"])
        self.assertTrue(result["future_append_stable"])


if __name__ == "__main__":
    raise SystemExit(unittest.main())

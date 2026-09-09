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
    match_ncaa_com_contest,
    parse_ncaa_com_scoreboard_contests,
)
from aggie_analytics.cycle30.admission import prove_coaching_not_modeled
from aggie_analytics.cycle30.claims import (
    ClaimError,
    discover_authority_claims,
    inventory_claims,
    reject_empty_science_pass,
    reject_vacuous_row_count,
)
from aggie_analytics.cycle30.availability import (
    AvailabilityError,
    conference_policy,
    extract_candidate_player_rows,
    inventory_availability_policies,
    join_candidates_to_roster,
)
from aggie_analytics.cycle30.coaching import (
    CoachingError,
    attempt_ledger_count,
    extract_official_website_from_wikidata_entity,
    extract_athletics_website_from_wikitext,
    extract_row_bound_staff,
    fill_current_role_matrix,
    hc_oc_dc_matrix,
    historical_season_page_title,
    html_is_not_found_shell,
    html_is_waf_challenge,
    season_title_matches_school,
    match_wikidata_website,
    official_staff_candidate_urls,
    overlay_historical_lattice,
    parse_infobox_college_coach,
    parse_official_staff_html,
    parse_official_staff_json,
    parse_sportradar_coaches,
    parse_wikimedia_infobox,
    expand_source_year_span,
    match_program_to_sportradar_team,
    role_families_from_title,
    role_family_from_title,
    reject_literal_attempted,
    reject_play_caller_from_title,
    reject_personal_contact,
    reject_wikimedia_as_pit,
    select_college_football_wiki_title,
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
    forecast_freeze_authority,
    rebuild_kernel_comparison,
    validate_oriented_outcomes,
    validate_row_authority,
)
from aggie_analytics.cycle30.populations import (
    PopulationError,
    classify_pair_counts,
    ncaa_discontinued_program_census,
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
    venue_from_bowl_note,
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
        origin_only = travel_row(
            canonical_game_id="G",
            team_id="T",
            origin_lat=None,
            origin_lon=None,
            venue_lat=44.5013,
            venue_lon=-88.0622,
            origin_class="CAMPUS_PROXY",
            origin_id="ND",
        )
        self.assertIsNone(origin_only["distance_km_haversine"])
        self.assertEqual(origin_only["missing_reason"], "MISSING_ORIGIN")
        self.assertEqual(origin_only["venue_latitude"], 44.5013)
        venue_only = travel_row(
            canonical_game_id="G",
            team_id="T",
            origin_lat=41.6984,
            origin_lon=-86.2339,
            venue_lat=None,
            venue_lon=None,
            origin_class="CAMPUS_PROXY",
            origin_id="ND",
        )
        self.assertEqual(venue_only["missing_reason"], "MISSING_VENUE")
        self.assertEqual(venue_only["origin_latitude"], 41.6984)
        both = travel_row(
            canonical_game_id="G",
            team_id="T",
            origin_lat=None,
            origin_lon=None,
            venue_lat=None,
            venue_lon=None,
            origin_class="UNKNOWN_TEAM_ORIGIN",
            origin_id=None,
        )
        self.assertEqual(both["missing_reason"], "MISSING_COORDINATES")

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

    def test_remaining_audit_register_requires_exact_sets(self) -> None:
        from aggie_analytics.cycle30.audit_register import (
            AuditRegisterError,
            remaining_audit_register,
            require_unit_fields,
        )

        register = remaining_audit_register(
            head_sha="abc",
            kernel_rows=1,
            proven_pit_rows=0,
            current_n=266,
            parent_games=46953,
            ties=490,
            neutrals=1966,
            official_staff_attempts=0,
            official_staff_not_attempted=266,
        )
        self.assertGreaterEqual(len(register["units"]), 10)
        for unit in register["units"]:
            require_unit_fields(unit)
            self.assertNotEqual(unit["status"], "AUDITED")
        with self.assertRaises(AuditRegisterError):
            require_unit_fields({"id": "x"})
        with self.assertRaises(AuditRegisterError):
            require_unit_fields({**register["units"][0], "status": "AUDITED"})

    def test_raw_to_normalized_semantic_join(self) -> None:
        from aggie_analytics.cycle30.foundation_trace import compare_raw_to_normalized

        raw = {
            "id": 1,
            "homeId": 10,
            "awayId": 20,
            "homePoints": 21,
            "awayPoints": 21,
            "neutralSite": True,
            "startDate": "2013-09-01T00:00:00.000Z",
            "season": 2013,
        }
        canonical = {
            "canonical_game_id": "SRC-002:GAME:1",
            "home_canonical_team_id": "SRC-002:TEAM:10",
            "away_canonical_team_id": "SRC-002:TEAM:20",
            "home_points": 21,
            "away_points": 21,
            "neutral_site": True,
            "start_date_utc_text": "2013-09-01T00:00:00Z",
        }
        result = compare_raw_to_normalized(raw, canonical)
        self.assertTrue(result["tie"])
        self.assertEqual(result["ordinary_home_exposure_if_verified_neutral"], 0)

    def test_game_context_v2_round_trip_and_v1_squeeze(self) -> None:
        from aggie_analytics.cycle30.contracts_v2 import (
            ContractV2Error,
            reject_v1_squeeze,
            round_trip_game_context,
            round_trip_staff_snapshot,
        )

        packet = {
            "canonical_game_id": "G",
            "source_order": ["H", "A"],
            "canonical_home_id": "H",
            "canonical_away_id": "A",
            "designated_home_id": "H",
            "site_class": "NEUTRAL",
            "ordinary_home_exposure_designated_home": 0,
            "unknowns": ["weather"],
        }
        self.assertEqual(round_trip_game_context(packet)["site_class"], "NEUTRAL")
        with self.assertRaises(ContractV2Error):
            reject_v1_squeeze({"canonical_game_id": "G"}, True)
        staff = {
            "program_id": "SRC-002:TEAM:1",
            "as_of_utc": "2026-09-07T16:00:00Z",
            "role": "head_coach",
            "formal_title": "Head Coach",
            "responsibility": "UNKNOWN",
            "episode_refs": [],
            "episode_cardinality": 0,
            "disposition": "NOT_ATTEMPTED",
            "attempt_count": 0,
            "pit_admitted": False,
        }
        round_trip_staff_snapshot(staff)
        with self.assertRaises(ContractV2Error):
            round_trip_staff_snapshot({**staff, "program_id": "DISPLAY:X"})

    def test_wikimedia_infobox_row_bound_and_not_pit(self) -> None:
        text = "| HeadCoach = [[Jane Doe]]\n| off_coach = [[John Roe]]\n"
        rows = parse_wikimedia_infobox(text, revision_id="1", page_title="T")
        self.assertEqual(rows[0]["person"], "Jane Doe")
        self.assertIn("wikimedia:T:1:", rows[0]["span_id"])
        self.assertEqual(rows[1]["role"], "offensive_coordinator")
        reject_wikimedia_as_pit(True, False)
        with self.assertRaises(CoachingError):
            reject_personal_contact("coach@example.com")
        with self.assertRaises(CoachingError):
            parse_wikimedia_infobox(text, revision_id="", page_title="T")
        noisy = (
            "| head_coach = [[Jane Doe]]\n| capacity = 102733\n"
            "| founded = 1894\ncontact 512-555-0100 coach@example.com\n"
        )
        noisy_rows = parse_wikimedia_infobox(noisy, revision_id="1", page_title="T")
        self.assertEqual(noisy_rows[0]["person"], "Jane Doe")
        table = parse_wikimedia_infobox(
            "| [[Tom Matukewicz]] || Head coach\n"
            "| Ricky Coon || Defensive coordinator\n"
            "| Jeromy McDowell || Offensive coordinator/quarterbacks\n"
            "| 1937 || Mid-America Intercollegiate Athletics Association || Abe Stuber || 9-0\n",
            revision_id="9",
            page_title="Southeast Missouri State Redhawks football",
        )
        roles = {row["role"]: row["person"] for row in table}
        self.assertEqual(roles["head_coach"], "Tom Matukewicz")
        self.assertEqual(roles["defensive_coordinator"], "Ricky Coon")
        self.assertEqual(roles["offensive_coordinator"], "Jeromy McDowell")
        colgate = official_staff_candidate_urls(
            "https://gocolgateraiders.com/sports/football"
        )
        self.assertTrue(any("colgateathletics.com" in url for url in colgate))
        ttu = official_staff_candidate_urls(
            "https://www.ttusports.com/sports/fball/index"
        )
        self.assertTrue(any(url.endswith("/sports/fball/coaches") for url in ttu))
        cells = hc_oc_dc_matrix(["SRC-002:TEAM:1"], "2026-09-08T00:00:00Z")
        filled = fill_current_role_matrix(
            cells,
            programs=[{"program_id": "SRC-002:TEAM:1", "display_name": "SEMO"}],
            cfbd_hc_by_school={},
            official_people_by_program={},
            official_attempts_by_program={
                "SRC-002:TEAM:1": {
                    "status": "ATTEMPTED_EMPTY_PARSE",
                    "attempt_count": 1,
                }
            },
            wikimedia_people_by_program={"SRC-002:TEAM:1": table},
        )
        oc = next(row for row in filled if row["role"] == "offensive_coordinator")
        self.assertEqual(oc["disposition"], "CANDIDATE_ONLY")
        self.assertEqual(oc["source"], "WIKIMEDIA")
        self.assertFalse(oc["pit_admitted"])
        tamu = parse_wikimedia_infobox(
            "| head_coach = [[Mike Elko]]\n"
            "| hc_year = 1st\n"
            "| off_coach = [[Collin Klein]]\n"
            "| cooff_coach1 = [[Holmon Wiggins]]\n"
            "| def_coach = [[Jay Bateman]]\n"
            "| codef_coach1 = [[Jordan Peterson (American football)|Jordan Peterson]]\n"
            "|asst_coach=\n"
            "*[[Trooper Taylor]] – Associate head coach/running backs\n"
            "*[[Jay Bateman]] – Defensive coordinator/linebackers\n"
            "*[[Collin Klein]] – Offensive coordinator/quarterbacks\n"
            "*[[Patrick Dougherty]] – Special teams coordinator\n",
            revision_id="75715566",
            page_title="2024 Texas A&M Aggies football team",
        )
        by_role = {(row["role"], row["person"]) for row in tamu}
        self.assertIn(("head_coach", "Mike Elko"), by_role)
        self.assertIn(("offensive_coordinator", "Collin Klein"), by_role)
        self.assertIn(("offensive_coordinator", "Holmon Wiggins"), by_role)
        self.assertIn(("defensive_coordinator", "Jay Bateman"), by_role)
        self.assertIn(("defensive_coordinator", "Jordan Peterson"), by_role)
        self.assertIn(("running_backs", "Trooper Taylor"), by_role)
        self.assertIn(("quarterbacks", "Collin Klein"), by_role)
        self.assertIn(("special_teams_coordinator", "Patrick Dougherty"), by_role)
        self.assertTrue(
            any(
                row["co_role"] == "true" and row["person"] == "Holmon Wiggins"
                for row in tamu
            )
        )
        with self.assertRaises(CoachingError):
            reject_play_caller_from_title(
                "Offensive coordinator/quarterbacks", "offense_play_caller"
            )
        midseason = parse_wikimedia_infobox(
            "| head_coach = [[Jimbo Fisher]]\n"
            "| hc_games = first 10 games\n"
            "| head_coach2 = [[Elijah Robinson]]\n"
            "| hc_games2 = interim; remainder of season\n"
            "| off_coach = [[Bobby Petrino]]\n"
            "| cooff_coach1 = [[James Coley]]\n"
            "| def_coach = [[D. J. Durkin]]\n"
            "| codef_coach1 = [[Elijah Robinson]]\n",
            revision_id="2",
            page_title="2023 Texas A&M Aggies football team",
        )
        fisher = next(row for row in midseason if row["person"] == "Jimbo Fisher")
        robinson_hc = next(
            row
            for row in midseason
            if row["person"] == "Elijah Robinson" and row["role"] == "head_coach"
        )
        robinson_dc = next(
            row
            for row in midseason
            if row["person"] == "Elijah Robinson"
            and row["role"] == "defensive_coordinator"
        )
        self.assertEqual(fisher["interim"], "false")
        self.assertEqual(robinson_hc["interim"], "true")
        self.assertEqual(robinson_dc["co_role"], "true")
        present = expand_source_year_span("2024–present")
        self.assertTrue(present["ongoing"])
        self.assertIsNone(present["end_year"])
        self.assertEqual(present["start_year"], 2024)
        career = parse_infobox_college_coach(
            "| coach_years1 = 2018–2021\n"
            "| coach_team1 = Texas A&M (DC/S)\n"
            "| coach_years2 = 2022–2023\n"
            "| coach_team2 = Duke\n"
            "| coach_years3 = 2024–present\n"
            "| coach_team3 = Texas A&M\n",
            revision_id="9",
            page_title="Mike Elko",
        )
        dc_s = [row for row in career if row["source_year_text"] == "2018–2021"]
        self.assertEqual(
            {row["role"] for row in dc_s}, {"defensive_coordinator", "safeties"}
        )
        duke = next(row for row in career if row["program_raw"] == "Duke")
        self.assertEqual(duke["role"], "UNKNOWN")
        ongoing = next(row for row in career if row["ongoing"] is True)
        self.assertIsNone(ongoing["end_year"])
        self.assertEqual(ongoing["role"], "UNKNOWN")

    def test_availability_inventory_unknown_not_healthy(self) -> None:
        inv = inventory_availability_policies(
            [
                {
                    "program_id": "SRC-002:TEAM:333",
                    "display_name": "Alabama",
                    "conference": "SEC",
                    "classification": "fbs",
                },
                {
                    "program_id": "SRC-002:TEAM:2000",
                    "display_name": "Abilene Christian",
                    "conference": "UAC",
                    "classification": "fcs",
                },
            ]
        )
        self.assertEqual(inv["attempted_official_report_routes"], 0)
        self.assertEqual(inv["rows"][0]["no_report_means"], "UNKNOWN")
        self.assertEqual(inv["rows"][0]["owner"], "BAT-414")
        self.assertTrue(inv["rows"][0]["out_of_fitted_models"])
        self.assertEqual(inv["rows"][1]["policy_status"], "FCS_VARIES_BY_PROGRAM")
        self.assertEqual(
            conference_policy("Pac-12", classification="fbs")["source_id"],
            "SRC-C30-PAC12",
        )
        with self.assertRaises(AvailabilityError):
            inventory_availability_policies([])
        attempted = inventory_availability_policies(
            [
                {
                    "program_id": "SRC-002:TEAM:333",
                    "display_name": "Alabama",
                    "conference": "SEC",
                    "classification": "fbs",
                }
            ],
            route_attempts=[
                {
                    "source_id": "SRC-017",
                    "attempt_count": 1,
                    "receipt_identity": "abc",
                    "disposition": "ATTEMPTED_WITH_EVIDENCE",
                    "http_status": 200,
                    "uri": "https://www.secsports.com/fbreports-archive",
                }
            ],
        )
        self.assertEqual(attempted["attempted_official_report_routes"], 1)
        self.assertEqual(attempted["rows"][0]["disposition"], "ATTEMPTED_WITH_EVIDENCE")
        self.assertFalse(attempted["rows"][0]["player_rows_joined_to_verified_roster"])

    def test_official_staff_html_oc_dc_and_pre1978_membership(self) -> None:
        from aggie_analytics.cycle30.coaching import (
            extract_athletics_website_from_wikitext,
            fill_current_role_matrix,
            hc_oc_dc_matrix,
            parse_official_staff_html,
            role_family_from_title,
        )
        from aggie_analytics.cycle30.populations import (
            PopulationError,
            membership_rows_1963_2012,
            reject_modern_label_pre_1978,
        )

        html = """
        <tr class="staff-directory-table-member-position">
          <td><a href="/staff/mike-elko" class="staff-directory-table-member-position__link--name">Mike Elko</a></td>
          <td class="staff-directory-table-member-position__position">Head Coach</td>
        </tr>
        <tr class="staff-directory-table-member-position">
          <td><a href="/staff/collin-klein" class="staff-directory-table-member-position__link--name">Collin Klein</a></td>
          <td class="staff-directory-table-member-position__position">Offensive Coordinator</td>
        </tr>
        <tr class="staff-directory-table-member-position">
          <td><a href="/staff/def" class="staff-directory-table-member-position__link--name">Jane Doe</a></td>
          <td class="staff-directory-table-member-position__position">Defensive Coordinator</td>
        </tr>
        """
        people = parse_official_staff_html(html, page_url="https://12thman.com/staff")
        roles = {row["role"] for row in people}
        self.assertIn("head_coach", roles)
        self.assertIn("offensive_coordinator", roles)
        self.assertIn("defensive_coordinator", roles)
        presto = parse_official_staff_html(
            """
            <a href="/sports/fball/coaches/Drew_Belcher" class="card-title"
               aria-label="Drew Belcher, Offensive Coordinator, Full Bio">Drew Belcher</a>
            <p class="card-text">Offensive Coordinator</p>
            <a href="/sports/fball/coaches/Bobby_Wilder" class="card-title"
               aria-label="Bobby Wilder, Head Coach, Full Bio">Bobby Wilder</a>
            <p class="card-text">Head Coach</p>
            """,
            page_url="https://www.ttusports.com/sports/fball/coaches",
        )
        self.assertTrue(any(row["person"] == "Bobby Wilder" for row in presto))
        self.assertTrue(any(row["role"] == "head_coach" for row in presto))
        self.assertTrue(any(row["role"] == "offensive_coordinator" for row in presto))
        self.assertIsNone(role_family_from_title("Special Asst. to the Head Coach"))
        umass = parse_official_staff_html(
            """
            <tr class="s-table-body__row s-table-body__row--index-0">
              <td><a href="/sports/football/roster/coaches/joe-harasymiak/2553">
                <span>Joe Harasymiak</span></a></td>
              <td><span>Football Performance Center</span></td>
              <td><span>Head Coach</span></td>
            </tr>
            <tr class="s-table-body__row s-table-body__row--index-1">
              <td><a href="/sports/football/roster/coaches/oc/1">
                <span>Max Warner</span></a></td>
              <td><span>Football Performance Center</span></td>
              <td><span>Offensive Coordinator</span></td>
            </tr>
            """,
            page_url="https://umassathletics.com/sports/football/coaches",
        )
        self.assertTrue(any(row["person"] == "Joe Harasymiak" for row in umass))
        self.assertTrue(any(row["role"] == "head_coach" for row in umass))
        self.assertTrue(any(row["role"] == "offensive_coordinator" for row in umass))
        self.assertFalse(
            any(row["title"] == "Football Performance Center" for row in umass)
        )
        vue = parse_official_staff_html(
            (
                '<a href="/sports/football/roster/coaches/kalen-deboer/1813" class="">'
                '<span class="s-text-paragraph-small-bold">Kalen DeBoer</span></a>'
                "<td><span data-v-a7dc635d>Head Coach</span></td>"
                '<a href="/sports/football/roster/coaches/ryan-grubb/1814">'
                "<span>Ryan Grubb</span></a>"
                "<td><span>Offensive Coordinator</span></td>"
            ),
            page_url="https://rolltide.com/sports/football/coaches",
        )
        self.assertTrue(any(row["role"] == "head_coach" for row in vue))
        self.assertTrue(any(row["role"] == "offensive_coordinator" for row in vue))
        table = parse_official_staff_html(
            """
            <title>Football Coaches - Alabama A&amp;M Athletics</title>
            <tr class="sidearm-coaches-coach">
              <td><img alt="Dennis Alexander"></td>
              <th><a href="/sports/football/roster/coaches/dennis-alexander/998">Dennis Alexander</a></th>
              <td>Co-Offensive Coordinator / Offensive Line</td>
              <td><a href="mailto:x@example.com">x@example.com</a></td>
            </tr>
            <tr class="sidearm-coaches-coach">
              <th><a href="/sports/football/roster/coaches/head/1">Patrice Henry Bazile</a></th>
              <td>Head Coach</td>
            </tr>
            """,
            page_url="http://aamusports.com/sports/football/coaches",
        )
        self.assertTrue(any(row["role"] == "head_coach" for row in table))
        self.assertTrue(any(row["role"] == "offensive_coordinator" for row in table))
        self.assertTrue(
            html_is_not_found_shell("<title>Page Not Found (404) - App State</title>")
        )
        self.assertTrue(
            html_is_not_found_shell("<title>Not Found -  Central Connecticut</title>")
        )
        self.assertTrue(
            html_is_waf_challenge(
                "<title></title><script>window.gokuProps = {};"
                "window.awsWafCookieDomainList = [];</script>"
            )
        )
        self.assertFalse(
            html_is_not_found_shell("<title>Football Coaches - App State</title>")
        )
        self.assertEqual(
            historical_season_page_title("Alabama Crimson Tide football", 2013),
            "2013 Alabama Crimson Tide football team",
        )
        self.assertEqual(
            historical_season_page_title(
                "1960 Yale Bulldogs football team", 2023, school="New Haven"
            ),
            "2023 New Haven football team",
        )
        self.assertEqual(
            historical_season_page_title(
                "Jim Chapman (American football)", 2020, school="Mercyhurst"
            ),
            "2020 Mercyhurst football team",
        )
        self.assertFalse(
            season_title_matches_school("2023 Yale Bulldogs football team", "New Haven")
        )
        self.assertTrue(
            season_title_matches_school("2023 Yale Bulldogs football team", "Yale")
        )
        self.assertTrue(
            season_title_matches_school(
                "2020 Texas A&M–Commerce Lions football team", "East Texas A&M"
            )
        )
        self.assertTrue(
            season_title_matches_school("2014 BYU Cougars football team", "BYU")
        )
        self.assertTrue(
            season_title_matches_school("2014 LSU Tigers football team", "LSU")
        )
        self.assertTrue(
            season_title_matches_school(
                "2014 Arkansas–Pine Bluff Golden Lions football team",
                "Arkansas-Pine Bluff",
            )
        )
        self.assertTrue(
            season_title_matches_school(
                "FIU Panthers football", "Florida International"
            )
        )
        self.assertFalse(
            season_title_matches_school(
                "2014 Northern Arizona Lumberjacks football team", "Arizona State"
            )
        )
        self.assertFalse(
            season_title_matches_school(
                "2014 North Texas Mean Green football team", "Texas State"
            )
        )
        self.assertFalse(
            season_title_matches_school(
                "California Polytechnic State University football team plane crash",
                "Cal Poly",
            )
        )
        overlaid = overlay_historical_lattice(
            [
                {
                    "program_id": "SRC-002:TEAM:1",
                    "season": 2013,
                    "role_family": "head_coach",
                    "evidence_disposition": "NOT_ATTEMPTED",
                }
            ],
            [
                {
                    "program_id": "SRC-002:TEAM:1",
                    "season": 2013,
                    "role": "head_coach",
                    "person": "Nick Saban",
                }
            ],
        )
        self.assertEqual(len(overlaid), 1)
        self.assertEqual(
            overlaid[0]["evidence_disposition"], "RETROSPECTIVE_CANDIDATE_ONLY"
        )
        self.assertFalse(overlaid[0]["pit_admitted"])
        names = extract_candidate_player_rows(
            "<table><tr><td>John Smith</td><td>Available</td></tr></table>",
            source_id="SRC-017",
            uri="https://example.test/reports",
        )
        self.assertEqual(names[0]["disposition"], "CANDIDATE_NOT_JOINED")
        self.assertFalse(names[0]["joined_to_verified_roster"])
        self.assertFalse(names[0]["health_status_inferred"])
        self.assertEqual(role_family_from_title("Assistant Head Coach"), None)
        website = extract_athletics_website_from_wikitext(
            "| WebsiteName = 12thman.com\n| WebsiteURL = https://12thman.com/sports/football\n"
        )
        self.assertEqual(website, "https://12thman.com/sports/football")
        athletics = extract_athletics_website_from_wikitext(
            "| athletics = {{URL|https://gopack.com}}\n"
        )
        self.assertEqual(athletics, "https://gopack.com")
        self.assertIsNone(
            extract_athletics_website_from_wikitext(
                "| website = https://www.sandiegofc.com\n"
            )
        )
        cells = hc_oc_dc_matrix(["SRC-002:TEAM:245"], "2026-09-07T16:00:00Z")
        filled = fill_current_role_matrix(
            cells,
            programs=[
                {
                    "program_id": "SRC-002:TEAM:245",
                    "display_name": "Texas A&M",
                }
            ],
            cfbd_hc_by_school={},
            official_people_by_program={"SRC-002:TEAM:245": people},
            official_attempts_by_program={
                "SRC-002:TEAM:245": {
                    "status": "CAPTURED",
                    "attempt_count": 1,
                    "receipt_identity": "x",
                }
            },
        )
        dispositions = {row["role"]: row["disposition"] for row in filled}
        self.assertEqual(dispositions["offensive_coordinator"], "CONFIRMED_APPOINTMENT")
        self.assertNotEqual(dispositions["offensive_coordinator"], "NOT_ATTEMPTED")
        with self.assertRaises(PopulationError):
            reject_modern_label_pre_1978(1970, "FBS")
        built = membership_rows_1963_2012(
            [
                {
                    "id": 245,
                    "school": "Texas A&M",
                    "classification": "fbs",
                    "source_year": 1970,
                    "conference": None,
                },
                {
                    "id": 245,
                    "school": "Texas A&M",
                    "classification": "fbs",
                    "source_year": 2008,
                    "conference": "Big 12",
                },
            ]
        )
        self.assertIsNone(built["rows"][0]["classification"])
        self.assertTrue(built["rows"][0]["source_classification_is_not_era_proof"])
        self.assertEqual(built["rows"][1]["classification"], "fbs")

    def test_predecessor_payload_mount_is_not_integer_subtraction(self) -> None:
        from aggie_analytics.cycle30.pit_kernel import (
            mount_predecessor_oriented_payload,
        )

        result = mount_predecessor_oriented_payload(
            Path(r"C:\BatteredAggieSyndrome.data")
        )
        if not result["mounted"]:
            self.assertEqual(result["status"], "NOT_MOUNTED")
            return
        self.assertEqual(result["predecessor_oriented_development_rows"], 90198)
        self.assertTrue(result["sha256_matches_declared_gate"])
        self.assertTrue(result["identity_sets_not_invented_from_integer_subtraction"])

    def test_designation_perturbation_travel_not_consumed(self) -> None:
        from aggie_analytics.cycle30.kernel_model import (
            designation_and_venue_perturbations,
            fold_local_fit,
        )

        rows = []
        for season in range(2013, 2024):
            rows.append(
                {
                    "canonical_game_id": f"G{season}",
                    "season": season,
                    "tie": False,
                    "home_win_label": season % 2 == 0,
                    "ordinary_home_exposure": 1 if season % 2 else 0,
                    "home_features": {"pit_prior_margin_mean": 3.0},
                    "away_features": {"pit_prior_margin_mean": 1.0},
                }
            )
        fit = fold_local_fit(rows, candidate="prior_margin_diff_ordinary_home")
        perturbation = designation_and_venue_perturbations(
            rows,
            candidate="prior_margin_diff_ordinary_home",
            weights=fit["weights"],
        )
        self.assertTrue(perturbation["travel_available_is_not_consumed"])
        self.assertEqual(perturbation["venue_change_mean_abs_probability_delta"], 0.0)

    def test_cfbd_presence_delta_is_not_ncaa_census(self) -> None:
        from aggie_analytics.cycle30.populations import cfbd_membership_presence_delta

        delta = cfbd_membership_presence_delta(
            ["SRC-002:TEAM:1"],
            [
                {"program_id": "SRC-002:TEAM:1", "season": 2013},
                {"program_id": "SRC-002:TEAM:9", "season": 2018},
            ],
        )
        self.assertTrue(delta["not_an_ncaa_discontinued_program_census"])
        self.assertEqual(delta["historical_absent_from_2026_n"], 1)

    def test_roster_staff_and_s_table_parsers_and_parent_exclusions(self) -> None:
        from aggie_analytics.cycle30.coaching import parse_official_staff_html
        from aggie_analytics.cycle30.foundation_trace import (
            KNOWN_PARENT_EXCLUSIONS,
            parent_duplicate_conflict_audit,
        )
        from aggie_analytics.cycle30.pit_kernel import (
            compare_kernel_to_predecessor_payload,
        )

        roster = parse_official_staff_html(
            """
            <div class="roster-card roster-staff-members-card-item">
              <a href="/sports/football/roster/season/2026/staff/kenny-dillingham">x</a>
              <a class="roster-card__title-link">Kenny Dillingham</a>
              <span class="roster-card__position">Head Coach</span>
            </div>
            <div class="roster-card">
              <a class="roster-card__title-link">AJ Ia</a>
              <span class="roster-card__position">TE</span>
            </div>
            """,
            page_url="https://thesundevils.com/sports/football/coaches",
        )
        roles = {row["role"] for row in roster}
        self.assertIn("head_coach", roles)
        self.assertFalse(any(row["person"] == "AJ Ia" for row in roster))
        table = parse_official_staff_html(
            """
            <td class="s-table-body_cell"><span>Offensive Coordinator</span></td>
            <td class="s-table-body_cell">
              <a href="/sports/football/roster/coaches/marcus-arroyo/1">
                <span>Marcus Arroyo</span>
              </a>
            </td>
            """,
            page_url="https://calbears.com/sports/football/coaches",
        )
        self.assertTrue(any(row["role"] == "offensive_coordinator" for row in table))
        directory = parse_official_staff_html(
            """
            <tr class="staff-directory-table-member-position staff-directory-table-department__row">
              <td class="staff-directory-table-cell staff-directory-table-member-position__name">
                <div class="staff-directory-table-member-position__name-text">
                  <a href="/staff-directory/frank-reich">Frank Reich</a>
                </div>
              </td>
              <td class="staff-directory-table-cell staff-directory-table-member-position__position">
                Head Coach
              </td>
            </tr>
            <tr class="staff-directory-table-member-position">
              <td class="staff-directory-table-cell staff-directory-table-member-position__name">
                <a href="/staff-directory/oc">Jane Offense</a>
              </td>
              <td class="staff-directory-table-cell staff-directory-table-member-position__position">
                Offensive Coordinator
              </td>
            </tr>
            """,
            page_url="https://gostanford.com/staff-directory/department/football",
        )
        self.assertTrue(any(row["person"] == "Frank Reich" for row in directory))
        self.assertTrue(any(row["role"] == "head_coach" for row in directory))
        self.assertTrue(
            any(row["role"] == "offensive_coordinator" for row in directory)
        )
        self.assertTrue(
            html_is_not_found_shell(
                "<title>Page not found | Arkansas Razorbacks</title>"
            )
        )
        self.assertFalse(
            html_is_not_found_shell(
                "<title>Football Coaches</title> Page Not Found (404) @del @sitename"
            )
        )
        known = KNOWN_PARENT_EXCLUSIONS[312472199]
        self.assertEqual(known["reason"], "KNOWN_PARENT_EXCLUSION")
        self.assertFalse(known["parent_present"])
        audit = parent_duplicate_conflict_audit(
            [
                {
                    "canonical_game_id": "SRC-002:GAME:1",
                    "home_team_source_id": "50",
                    "away_team_source_id": "2634",
                    "start_date_utc_text": "2004-09-25T04:00:00.000Z",
                    "home_points": 21,
                    "away_points": 15,
                    "neutral_site": False,
                },
                {
                    "canonical_game_id": "SRC-002:GAME:2",
                    "home_team_source_id": "50",
                    "away_team_source_id": "2634",
                    "start_date_utc_text": "2004-09-25T19:00:00.000Z",
                    "home_points": 21,
                    "away_points": 15,
                    "neutral_site": True,
                },
            ]
        )
        self.assertEqual(audit["pair_calendar_date_collision_groups"], 1)
        self.assertEqual(audit["site_class_conflict_groups"], 1)
        self.assertEqual(audit["score_conflict_groups"], 0)
        missing = compare_kernel_to_predecessor_payload(
            [], Path("C:/no-such-data-root")
        )
        self.assertEqual(missing["status"], "NOT_MOUNTED")
        self.assertTrue(missing["disagreement_is_not_copied_from_predecessor"])

    def test_forecast_freeze_before_kickoff_is_proven(self) -> None:
        prior = {
            "canonical_game_id": "G2015",
            "home_canonical_team_id": "H",
            "away_canonical_team_id": "A",
            "season": 2015,
            "start_date_utc_text": "2015-09-05T19:00:00Z",
            "date_precision": "INSTANT",
            "home_points": 21,
            "away_points": 14,
            "source_id": "SRC-002",
        }
        target = {
            "canonical_game_id": "G2026",
            "home_canonical_team_id": "H",
            "away_canonical_team_id": "A",
            "season": 2026,
            "start_date_utc_text": "2026-09-05T23:30:00Z",
            "date_precision": "INSTANT",
            "home_points": 24,
            "away_points": 17,
            "source_id": "SRC-002",
        }

        def outcomes(game: dict, home_points: int, away_points: int) -> list[dict]:
            return [
                {
                    "canonical_game_id": game["canonical_game_id"],
                    "canonical_team_id": game["home_canonical_team_id"],
                    "label_win": home_points > away_points,
                    "points_for": home_points,
                    "points_against": away_points,
                    "margin": home_points - away_points,
                    "season": game["season"],
                },
                {
                    "canonical_game_id": game["canonical_game_id"],
                    "canonical_team_id": game["away_canonical_team_id"],
                    "label_win": away_points > home_points,
                    "points_for": away_points,
                    "points_against": home_points,
                    "margin": away_points - home_points,
                    "season": game["season"],
                },
            ]

        freeze = {
            "snapshot_timestamp_utc": "2026-08-31T17:00:00Z",
            "kickoff_bound_utc": "2026-09-05T23:30:00Z",
        }
        authorities = {
            "G2015": {
                "source_id": "SRC-002",
                "effective_utc": prior["start_date_utc_text"],
                "known_at_utc": prior["start_date_utc_text"],
                "receipt_sha256": "UNPROVEN",
                "classification": "UNPROVEN",
                "evidence_class": "CONSERVATIVE_BOUND_NOT_PUBLICATION",
                "allow_retrospective_prior": True,
            },
            "G2026": forecast_freeze_authority(freeze, receipt_sha256="freeze-sha"),
        }
        kernel = build_game_grain_kernel(
            [prior, target],
            [*outcomes(prior, 21, 14), *outcomes(target, 24, 17)],
            expected_population_complete=False,
            authorities=authorities,
            target_cutoff_by_game={
                "G2015": prior["start_date_utc_text"],
                "G2026": target["start_date_utc_text"],
            },
        )
        self.assertGreater(kernel["proven_pit_training_rows"], 0)
        self.assertEqual(kernel["primary_kernel_objective"], "COMPLETE_NONZERO_PROVEN")
        late = forecast_freeze_authority(
            {
                "snapshot_timestamp_utc": "2026-09-06T00:00:00Z",
                "kickoff_bound_utc": "2026-09-05T23:30:00Z",
            },
            receipt_sha256="freeze-sha",
        )
        blocked = build_game_grain_kernel(
            [prior, target],
            [*outcomes(prior, 21, 14), *outcomes(target, 24, 17)],
            expected_population_complete=False,
            authorities={"G2015": authorities["G2015"], "G2026": late},
            target_cutoff_by_game={
                "G2015": prior["start_date_utc_text"],
                "G2026": target["start_date_utc_text"],
            },
        )
        self.assertEqual(blocked["proven_pit_training_rows"], 0)

    def test_ncaa_com_scoreboard_is_contest_scoped(self) -> None:
        page = (
            '{"contestId":6603962,"url":"\\/game\\/6603962",'
            '"gameState":"F","statusCodeDisplay":"Final",'
            '"teams":[{"isHome":false,"seoname":"smu","nameShort":"SMU","score":27},'
            '{"isHome":true,"seoname":"florida-st","nameShort":"Florida St.","score":24}]}'
        )
        contests = parse_ncaa_com_scoreboard_contests(page)
        self.assertEqual(len(contests), 1)
        self.assertEqual(contests[0]["terminal_state"], TERMINAL_STATUS_ESTABLISHED)
        matched = match_ncaa_com_contest(
            contests,
            home_names=("florida st", "florida st.", "florida state"),
            away_names=("smu",),
        )
        self.assertIsNotNone(matched)
        neighbor = parse_ncaa_com_scoreboard_contests(
            "Final somewhere "
            '{"contestId":1,"url":"\\/game\\/1","gameState":"I","statusCodeDisplay":"Live",'
            '"teams":[{"isHome":true,"seoname":"a","nameShort":"A","score":0},'
            '{"isHome":false,"seoname":"b","nameShort":"B","score":0}]}'
        )
        self.assertEqual(neighbor[0]["terminal_state"], NOT_TERMINAL)

    def test_sidearm_football_staff_table_and_json_and_wikidata(self) -> None:
        html = """
        <tr class="sidearm-staff-category" data-category-id="10"><th>Football</th></tr>
        <tr class="sidearm-staff-member" data-category-id="10">
          <td headers="col-staff_title">Head Coach</td>
          <a aria-label='Jeff Faris, Head Coach' href="/sports/football/coaches/jeff-faris">x</a>
        </tr>
        <tr class="sidearm-staff-category" data-category-id="3"><th>Basketball</th></tr>
        <tr class="sidearm-staff-member" data-category-id="3">
          <td headers="col-staff_title">Head Coach</td>
          <a aria-label='Other Sport, Head Coach' href="/sports/mbball/coaches/other">x</a>
        </tr>
        """
        parsed = parse_official_staff_html(
            html, page_url="https://letsgopeay.com/staff.aspx"
        )
        self.assertTrue(any(row["person"] == "Jeff Faris" for row in parsed))
        self.assertFalse(any(row["person"] == "Other Sport" for row in parsed))
        json_rows = parse_official_staff_json(
            {
                "items": [
                    {
                        "firstName": "Jane",
                        "lastName": "Offense",
                        "title": "Offensive Coordinator",
                        "category": {"title": "Football"},
                    }
                ]
            },
            page_url="https://example.com/api/v2/Staff",
        )
        self.assertTrue(
            any(row["role"] == "offensive_coordinator" for row in json_rows)
        )
        website = extract_official_website_from_wikidata_entity(
            {
                "claims": {
                    "P856": [
                        {
                            "mainsnak": {
                                "datavalue": {"value": "https://brownbears.com/"}
                            }
                        }
                    ]
                }
            }
        )
        self.assertEqual(website, "https://brownbears.com/")
        matched = match_wikidata_website(
            "Brown",
            [
                {
                    "itemLabel": "Nathaniel Brown (footballer)",
                    "website": "https://example.net/person",
                },
                {
                    "itemLabel": "Brown Bears football",
                    "website": "https://brownbears.com/",
                },
            ],
        )
        self.assertEqual(matched, "https://brownbears.com/")
        wordpress = parse_official_staff_html(
            """<tr>
            <td><a href="/coache/tim-cramsey/">Tim Cramsey</a></td>
            <td>Offensive Coordinator</td>
            </tr>""",
            page_url="https://arkansasrazorbacks.com/staff-directory?path=football",
        )
        self.assertTrue(any(row["person"] == "Tim Cramsey" for row in wordpress))
        soccer_club = match_wikidata_website(
            "Richmond",
            [
                {
                    "itemLabel": "Richmond Football Club",
                    "website": "https://www.richmondfc.com.au/",
                }
            ],
        )
        self.assertIsNone(soccer_club)
        title = select_college_football_wiki_title(
            [
                {"title": "Nathaniel Brown (footballer)"},
                {"title": "Brown Bears football"},
            ],
            "Brown",
        )
        self.assertEqual(title, "Brown Bears football")
        season_skipped = select_college_football_wiki_title(
            [
                {"title": "1965 NC State Wolfpack football team"},
                {"title": "NC State Wolfpack football"},
            ],
            "NC State",
        )
        self.assertEqual(season_skipped, "NC State Wolfpack football")
        person_rejected = select_college_football_wiki_title(
            [
                {"title": "Jim Chapman (American football)"},
                {"title": "Mercyhurst Lakers football"},
            ],
            "Mercyhurst",
        )
        self.assertEqual(person_rejected, "Mercyhurst Lakers football")
        flames = extract_athletics_website_from_wikitext(
            "| website = https://www.liberty.edu/flames/index.cfm\n"
            "Official site [https://www.libertyflames.com/sports/football Football]\n"
        )
        self.assertEqual(flames, "https://www.libertyflames.com/sports/football")
        sr_people = parse_sportradar_coaches(
            {
                "coaches": [
                    {
                        "id": "9c34ca07-cd05-48dc-ba4e-45b9df6078eb",
                        "full_name": "Kirby Smart",
                        "first_name": "Kirby",
                        "last_name": "Smart",
                        "position": "Head Coach",
                    },
                    {
                        "id": "oc-1",
                        "full_name": "Mike Bobo",
                        "position": "Offensive Coordinator",
                    },
                ]
            },
            team_id="uga",
            page_url="https://api.sportradar.com/ncaafb/example",
        )
        self.assertEqual(sr_people[0]["person"], "Kirby Smart")
        self.assertEqual(sr_people[0]["role"], "head_coach")
        self.assertEqual(sr_people[1]["role"], "offensive_coordinator")
        alabama = match_program_to_sportradar_team(
            "Alabama",
            [
                {
                    "id": "1",
                    "market": "Alabama",
                    "alias": "ALA",
                    "name": "Crimson Tide",
                },
                {
                    "id": "2",
                    "market": "Alabama A&M",
                    "alias": "AAMU",
                    "name": "Bulldogs",
                },
            ],
        )
        self.assertEqual(alabama["id"], "1")
        app_state = match_program_to_sportradar_team(
            "App State",
            [
                {
                    "id": "9",
                    "market": "Appalachian State",
                    "alias": "APP",
                    "name": "Mountaineers",
                }
            ],
        )
        self.assertEqual(app_state["id"], "9")
        stadium = venue_from_bowl_note(
            "AT&T COTTON BOWL",
            {"cotton bowl": {"id": 12, "name": "Cotton Bowl"}},
        )
        self.assertEqual(stadium["id"], 12)

    def test_official_title_abbreviations_map_oc_dc_not_pass_game(self) -> None:
        self.assertEqual(
            role_families_from_title(
                "Associate Head Coach/Off. Coor./Quarterbacks"
            ),
            ("offensive_coordinator",),
        )
        self.assertEqual(
            role_families_from_title("Assistant Coach - Def. Coor./Safeties"),
            ("defensive_coordinator",),
        )
        self.assertEqual(
            role_families_from_title("Assoc. Head Coach/Def. Coordinator/OLB"),
            ("defensive_coordinator",),
        )
        self.assertEqual(role_families_from_title("Assoc. Head Coach"), ())
        self.assertIsNone(role_family_from_title("Assoc. Head Coach"))
        self.assertEqual(
            role_families_from_title(
                "Offensive Pass Game Coordinator/Quarterbacks Coach"
            ),
            (),
        )
        cells = hc_oc_dc_matrix(["SRC-002:TEAM:2230"], "2026-09-07T16:00:00Z")
        filled = fill_current_role_matrix(
            cells,
            programs=[
                {
                    "program_id": "SRC-002:TEAM:2230",
                    "display_name": "Fordham",
                }
            ],
            cfbd_hc_by_school={},
            official_people_by_program={
                "SRC-002:TEAM:2230": [
                    {
                        "person": "Joe Conlin",
                        "title": "Head Football Coach",
                        "role": "head_coach",
                    },
                    {
                        "person": "Art Asselta",
                        "title": "Associate Head Coach/Off. Coor./Quarterbacks",
                        "role": "OTHER_POSITION",
                    },
                    {
                        "person": "James Lenahan",
                        "title": "Assistant Coach - Def. Coor./Safeties",
                        "role": "OTHER_POSITION",
                    },
                ]
            },
            official_attempts_by_program={
                "SRC-002:TEAM:2230": {
                    "status": "CAPTURED",
                    "attempt_count": 1,
                    "receipt_identity": "x",
                }
            },
        )
        by_role = {row["role"]: row for row in filled}
        self.assertEqual(
            by_role["offensive_coordinator"]["disposition"], "CONFIRMED_APPOINTMENT"
        )
        self.assertEqual(
            by_role["defensive_coordinator"]["disposition"], "CONFIRMED_APPOINTMENT"
        )
        self.assertEqual(
            by_role["offensive_coordinator"]["episode_refs"][0]["person"],
            "Art Asselta",
        )
        self.assertEqual(
            by_role["defensive_coordinator"]["episode_refs"][0]["person"],
            "James Lenahan",
        )

    def test_availability_join_is_name_only_not_health(self) -> None:
        candidates = extract_candidate_player_rows(
            "<td>John Smith</td>",
            source_id="SRC-017",
            uri="https://example.test/report",
        )
        self.assertTrue(candidates)
        joined = join_candidates_to_roster(
            candidates,
            [{"full_name": "John Smith", "canonical_person_id": "PERSON:1"}],
        )
        self.assertGreaterEqual(joined["joined_to_verified_roster"], 1)
        self.assertEqual(joined["no_report_means"], "UNKNOWN")
        self.assertTrue(joined["roster_or_participation_is_not_availability"])

    def test_ncaa_discontinued_census_is_not_cfbd_delta(self) -> None:
        census = ncaa_discontinued_program_census(
            ncaa_rows=[{"program_name": "Idaho"}],
            wikipedia_rows=[{"program_name": "Idaho Vandals football"}],
            current_ids=["SRC-002:TEAM:1"],
            cfbd_absent_ids=["SRC-002:TEAM:9"],
        )
        self.assertFalse(census["not_an_ncaa_discontinued_program_census"])
        self.assertEqual(census["ncaa_census_rows"], 1)
        empty = ncaa_discontinued_program_census(
            ncaa_rows=[],
            wikipedia_rows=[{"program_name": "Pacific Tigers football"}],
            current_ids=["SRC-002:TEAM:1"],
            cfbd_absent_ids=["SRC-002:TEAM:9"],
        )
        self.assertTrue(empty["not_an_ncaa_discontinued_program_census"])
        self.assertTrue(empty["cfbd_presence_delta_is_not_this_census"])


if __name__ == "__main__":
    raise SystemExit(unittest.main())

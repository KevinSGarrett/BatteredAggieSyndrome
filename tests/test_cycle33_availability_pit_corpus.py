"""Continuation availability, PIT, corpus-grain, and query repairs."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aggie_analytics.cycle33.availability_cache import (
    cache_path_for_uri,
    extract_status_statements,
    parse_cached_document,
)
from aggie_analytics.cycle33.forecast_inventory import (
    _looks_relevant,
    inspect_forecast_eligibility,
)
from aggie_analytics.cycle33.pit_recompute import (
    producer_proven_without_receipt,
    recompute_pit_population,
)
from aggie_analytics.cycle33.query import StaffQueryError, connect, connect_readonly
from aggie_analytics.cycle33.user_coaches import (
    adjudicate_risk_fragment,
    conservation_checks,
    overlap_program_seasons,
)
from aggie_analytics.scientific_reference.cycle33_pit import reconstruct_pit


class AvailabilityCacheTests(unittest.TestCase):
    def test_file_presence_is_not_http_200(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            uri = "https://example.test/availability"
            path = cache_path_for_uri(uri, root)
            path.write_text(
                "<html><body>availability report<table><tr>"
                "<td>Jane Smith</td></tr></table></body></html>",
                encoding="utf-8",
            )
            parsed = parse_cached_document(path, uri=uri, source_id="SRC-TEST")
            self.assertEqual(parsed["disposition"], "CACHE_HIT_PARSED")
            self.assertIsNone(parsed["http_status"])
            self.assertTrue(parsed["file_existence_is_not_http_200"])
            self.assertEqual(parsed["no_report_means"], "UNKNOWN")
            self.assertFalse(parsed["joined_to_verified_roster"])

    def test_status_statement_requires_player_team_vintage_and_game(self) -> None:
        incomplete = extract_status_statements(
            "Jane Smith - questionable",
            source_id="SRC-TEST",
            uri="https://example.test/report",
        )
        self.assertEqual(incomplete[0]["disposition"], "STATUS_STATEMENT_INCOMPLETE")
        self.assertFalse(incomplete[0]["verified_availability"])
        complete = extract_status_statements(
            "Texas A&M Football Availability Report\n"
            "September 10, 2026 vs Notre Dame\n"
            "Jane Smith - questionable",
            source_id="SRC-TEST",
            uri="https://example.test/report",
        )
        self.assertTrue(complete[0]["bound_complete"])
        self.assertEqual(complete[0]["player"], "Jane Smith")
        self.assertEqual(complete[0]["status_statement"], "questionable")
        self.assertFalse(complete[0]["verified_availability"])
        self.assertFalse(complete[0]["joined_to_verified_roster"])

    def test_js_shell_is_not_a_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "shell.html"
            path.write_text(
                '<html><body><div id="root"></div>'
                + "<script></script>" * 8
                + "</body></html>",
                encoding="utf-8",
            )
            parsed = parse_cached_document(
                path, uri="https://example.test/app", source_id="SRC-TEST"
            )
            self.assertEqual(parsed["page_kind"], "JS_LANDING_SHELL_NOT_REPORT")
            self.assertEqual(parsed["player_rows_extracted"], 0)

    def test_missing_cache_is_not_healthy(self) -> None:
        parsed = parse_cached_document(
            Path("missing-cache.html"),
            uri="https://example.test/missing",
            source_id="SRC-TEST",
        )
        self.assertEqual(parsed["disposition"], "CACHE_MISS_NOT_FETCHED")
        self.assertEqual(parsed["no_report_means"], "UNKNOWN")


class PitRecomputeTests(unittest.TestCase):
    def test_producer_proven_label_without_receipt_is_not_proven(self) -> None:
        rows = [
            {
                "canonical_game_id": "G1",
                "season": 2026,
                "authority_class": "PROVEN_PIT_TRAINING_ROW",
                "row_verdict": "PROVEN_PIT_TRAINING_ROW",
            },
            {
                "canonical_game_id": "G2",
                "season": 2018,
                "authority_class": "RETROSPECTIVE_BOUNDED_CANDIDATE",
            },
        ]
        producer = recompute_pit_population(rows)
        independent = reconstruct_pit(rows)
        self.assertEqual(producer["independently_proven_count"], 0)
        self.assertEqual(independent["independently_proven_count"], 0)
        self.assertGreater(producer["failed_predicate_rows"], 0)
        self.assertIn(
            "PRODUCER_PROVEN_LABEL_WITHOUT_RECEIPT",
            independent["failed_predicate_reason_counts"],
        )
        labels = producer_proven_without_receipt(rows)
        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0]["canonical_game_id"], "G1")
        self.assertFalse(labels[0]["independently_proven"])

    def test_count_is_recomputed_not_hardcoded(self) -> None:
        rows = [
            {
                "canonical_game_id": "G3",
                "season": 2018,
                "source_id": "SRC-TEST",
                "effective_utc": "2018-09-01T18:00:00Z",
                "known_at_utc": "2018-09-01T20:00:00Z",
                "receipt_sha256": "a" * 64,
                "classification": "FEATURE_TIME_AUTHORITY",
                "evidence_class": "FORECAST_FREEZE_RECEIPT",
                "source_publication_utc": "2018-09-01T19:00:00Z",
                "target_cutoff_utc": "2018-09-02T00:00:00Z",
            }
        ]
        independent = reconstruct_pit(rows)
        self.assertEqual(independent["independently_proven_count"], 0)
        self.assertIn(
            "FORECAST_FREEZE_IS_RETROSPECTIVE",
            independent["failed_predicate_reason_counts"],
        )


class CorpusGrainTests(unittest.TestCase):
    def test_conservation_reconstructs_from_rows(self) -> None:
        imported = {
            "file_count": 1,
            "staff_row_count": 1,
            "queue_row_count": 0,
            "physically_present_role_cells": 1,
            "parsed_person_segment_count": 1,
            "emitted_role_assignment_records": 1,
            "distinct_source_role_cell_ids": 1,
            "canonical_people_count": 1,
            "files": [{"relative_path": "a.csv"}],
            "observations": [{"season_cell": "2004"}],
            "queue_rows": [],
            "role_cells": [
                {
                    "observation_id": "OBS1",
                    "role_column": "Head Coach",
                    "person": "A",
                    "person_identity_key": "bob jones",
                }
            ],
        }
        check = conservation_checks(imported)
        self.assertTrue(check["conserved"])
        self.assertTrue(check["grains_are_not_unique_people"])

    def test_expanded_records_are_not_physical_cells(self) -> None:
        imported = {
            "file_count": 1,
            "staff_row_count": 1,
            "queue_row_count": 0,
            "physically_present_role_cells": 1,
            "parsed_person_segment_count": 2,
            "emitted_role_assignment_records": 2,
            "distinct_source_role_cell_ids": 1,
            "canonical_people_count": 2,
            "files": [{"relative_path": "a.csv"}],
            "observations": [{"season_cell": "2004"}],
            "queue_rows": [],
            "role_cells": [
                {
                    "observation_id": "OBS1",
                    "role_column": "Head Coach",
                    "person": "A",
                    "person_identity_key": "a",
                },
                {
                    "observation_id": "OBS1",
                    "role_column": "Head Coach",
                    "person": "B",
                    "person_identity_key": "b",
                },
            ],
        }
        check = conservation_checks(imported)
        self.assertTrue(check["conserved"])
        self.assertEqual(check["reconstructed"]["physically_present_role_cells"], 1)
        self.assertEqual(check["reconstructed"]["emitted_role_assignment_records"], 2)

    def test_fiu_fau_wku_overlap_keys(self) -> None:
        imported = {
            "observations": [
                {
                    "season_cell": "2004",
                    "team": "FIU",
                    "team_id_source": "fiu",
                    "filename_subdivision": "FBS",
                    "source_file": "2004_FBS.csv",
                },
                {
                    "season_cell": "2004",
                    "team": "FIU",
                    "team_id_source": "fiu",
                    "filename_subdivision": "FCS",
                    "source_file": "2004_FCS.csv",
                },
                {
                    "season_cell": "2004",
                    "team": "Florida Atlantic",
                    "team_id_source": "florida_atlantic",
                    "filename_subdivision": "FBS",
                    "source_file": "2004_FBS.csv",
                },
                {
                    "season_cell": "2004",
                    "team": "Florida Atlantic",
                    "team_id_source": "florida_atlantic",
                    "filename_subdivision": "FCS",
                    "source_file": "2004_FCS.csv",
                },
                {
                    "season_cell": "2007",
                    "team": "Western Kentucky",
                    "team_id_source": "western_kentucky",
                    "filename_subdivision": "FBS",
                    "source_file": "2007_FBS.csv",
                },
                {
                    "season_cell": "2007",
                    "team": "Western Kentucky",
                    "team_id_source": "western_kentucky",
                    "filename_subdivision": "FCS",
                    "source_file": "2007_FCS.csv",
                },
            ]
        }
        result = overlap_program_seasons(imported)
        self.assertEqual(result["overlap_count"], 3)
        self.assertTrue(result["all_named_found"])
        self.assertTrue(result["filename_subdivision_is_not_historical_membership"])

    def test_interim_is_positive_control_not_error(self) -> None:
        row = adjudicate_risk_fragment(
            {
                "column": "Head Coach",
                "fragment": (
                    "Bill Lynch — Assistant Head Coach / Offensive Coordinator / "
                    "Temporary Interim Head Coach (medical leave)"
                ),
                "team": "Indiana",
            }
        )
        self.assertEqual(row["adjudication"], "POSITIVE_CONTROL_INTERIM_OR_ACTING")
        self.assertFalse(row["fact_verified"])

    def test_associate_head_coach_is_not_principal_hc(self) -> None:
        row = adjudicate_risk_fragment(
            {
                "column": "Head Coach",
                "fragment": "Dan Enos — Associate Head Coach/Quarterbacks",
                "team": "Alabama",
            }
        )
        self.assertEqual(row["adjudication"], "REJECTED_NOT_PRINCIPAL_FOR_HC_COLUMN")

    def test_associate_hc_abbreviation_is_not_principal(self) -> None:
        row = adjudicate_risk_fragment(
            {
                "column": "Head Coach",
                "fragment": "Tommy Mainord — Associate HC, Pass Game Coordinator",
                "team": "North Texas",
            }
        )
        self.assertEqual(row["adjudication"], "REJECTED_NOT_PRINCIPAL_FOR_HC_COLUMN")

    def test_formal_title_not_established_is_not_principal_dc(self) -> None:
        row = adjudicate_risk_fragment(
            {
                "column": "Defensive Coordinator",
                "fragment": (
                    "Jim Mora — Head Coach / Ran the defense "
                    "(defensive coordinator responsibility; formal title not established)"
                ),
                "team": "UConn",
            }
        )
        self.assertEqual(
            row["adjudication"], "FORMAL_TITLE_NOT_ESTABLISHED_NOT_PRINCIPAL"
        )

    def test_readonly_connect_does_not_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.sqlite"
            with self.assertRaises(StaffQueryError):
                connect_readonly(missing)
            with self.assertRaises(StaffQueryError):
                connect(missing, readonly=True)
            self.assertFalse(missing.exists())

    def test_frozen_boolean_is_not_eligibility_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "forecast.json"
            path.write_text(json.dumps({"frozen": True, "p": 0.6}), encoding="utf-8")
            inspected = inspect_forecast_eligibility(path)
            self.assertFalse(inspected["eligibility_proof_present"])
            self.assertEqual(inspected["eligibility_verdict"], "INELIGIBLE")
            self.assertIn(
                "FROZEN_BOOLEAN_WITHOUT_RECEIPT_SHA256", inspected["failed_predicates"]
            )
            self.assertTrue(inspected["freeze_token_present"])

    def test_inventory_filename_is_not_a_forecast_packet(self) -> None:
        self.assertFalse(_looks_relevant(Path("CYCLE33_FORECAST_FILE_INVENTORY.json")))


if __name__ == "__main__":
    unittest.main()

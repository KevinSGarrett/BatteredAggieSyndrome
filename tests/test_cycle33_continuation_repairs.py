"""Continuation C33C-01–11 repairs. Manager probes are counterexamples, not production code."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aggie_analytics.cycle33.career_identity import (
    employer_evidence_matches,
    join_occupant_to_pages,
    page_identity_key,
)
from aggie_analytics.cycle33.confirmed_spans import (
    ConfirmedSpanError,
    require_locatable_confirmed,
)
from aggie_analytics.cycle33.official_finals import competing_observations
from aggie_analytics.cycle33.query import StaffQueryError, connect_readonly
from aggie_analytics.cycle33.scoring_successor import score_unique_frozen_games
from aggie_analytics.cycle33.span_locate import bind_person_role, locate_person_title
from aggie_analytics.cycle33.user_coaches import parse_csv_records
from aggie_analytics.cycle33.week2 import deadline_disposition


FINAL = {
    "game_state": "F",
    "status_code_display": "final",
    "terminal_state": "TERMINAL_STATUS_ESTABLISHED",
}


class ContinuationSpanTests(unittest.TestCase):
    def test_c33c01_different_table_rows_are_not_confirmed(self) -> None:
        body = (
            "<table><tr><td>Alice Smith</td><td>Head Coach</td></tr>"
            "<tr><td>Bob Jones</td><td>Strength Coach</td></tr></table>"
        )
        with self.assertRaises(ConfirmedSpanError):
            require_locatable_confirmed(body, person="Bob Jones", title="Head Coach")
        found = bind_person_role(body, person="Bob Jones", title="Head Coach")
        self.assertTrue(found["person_record_bound"])
        self.assertFalse(found["role_claim_supported"])
        self.assertFalse(found["locatable"])
        self.assertEqual(found["record_title"], "Strength Coach")
        self.assertTrue(found["contrary_records"])

    def test_c33c02_decoded_offset_is_not_raw_offset(self) -> None:
        body = "<p>&amp; Bob Jones</p><p>Head Coach</p>"
        found = locate_person_title(body, person="& Bob Jones", title="Head Coach")
        self.assertEqual(found["coordinate_system"], "raw_html")
        start = found["body_offset"]
        end = found["body_end_offset"]
        self.assertIsNotNone(start)
        self.assertIsNotNone(end)
        self.assertEqual(body[start:end], found["evidence_text"])
        self.assertNotEqual(
            body[start : start + len("& Bob Jones")],
            "& Bob Jones",
        )
        self.assertIn(
            "&amp;",
            found["evidence_text"]
            or found["person_interval"].get("evidence_text")
            or "",
        )

    def test_c33c03_empty_title_is_name_observation_only(self) -> None:
        with self.assertRaises(ConfirmedSpanError):
            require_locatable_confirmed(
                "<p>Bob Jones</p>", person="Bob Jones", title=""
            )
        found = bind_person_role("<p>Bob Jones</p>", person="Bob Jones", title="")
        self.assertFalse(found["role_claim_supported"])
        self.assertTrue(found["name_observation_only"] or found["reject_reason"])

    def test_same_row_and_interim_and_multi_role_still_confirm(self) -> None:
        html = (
            "<table><tr><td>Keith Patterson</td><td>Head Football Coach</td></tr>"
            "<tr><td>Pat Lee</td>"
            "<td>Interim Offensive Coordinator / Quarterbacks</td></tr></table>"
        )
        hc = require_locatable_confirmed(
            html, person="Keith Patterson", title="Head Coach"
        )
        self.assertTrue(hc["role_claim_supported"])
        oc = require_locatable_confirmed(
            html,
            person="Pat Lee",
            title="Offensive Coordinator",
        )
        self.assertTrue(oc["role_claim_supported"])
        self.assertIn("interim", str(oc["record_title"]).casefold())


class ContinuationCsvTests(unittest.TestCase):
    def test_c33c04_embedded_newline_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.csv"
            path.write_text(
                'Team,Head Coach\nSchool,"Bob Jones\nHead Coach"\n', encoding="utf-8"
            )
            headers, rows, _payload, meta = parse_csv_records(path)
            self.assertEqual(meta["status"], "OK")
            self.assertEqual(rows[0]["Head Coach"], "Bob Jones\nHead Coach")
            self.assertEqual(headers, ["Team", "Head Coach"])

    def test_c33c05_extra_field_is_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.csv"
            path.write_text(
                "Team,Head Coach\nSchool,Bob Jones,EXTRA\n", encoding="utf-8"
            )
            _headers, rows, _payload, meta = parse_csv_records(path)
            self.assertEqual(meta["status"], "QUARANTINED")
            self.assertIn("ROW_WIDTH_MISMATCH", meta["reasons"])
            self.assertEqual(rows, [])

    def test_c33c06_duplicate_header_is_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.csv"
            path.write_text(
                "Team,Head Coach,Head Coach\nSchool,Alice,Bob\n", encoding="utf-8"
            )
            _headers, rows, _payload, meta = parse_csv_records(path)
            self.assertEqual(meta["status"], "QUARANTINED")
            self.assertIn("DUPLICATE_HEADER", meta["reasons"])
            self.assertEqual(rows, [])


class ContinuationFinalsScoringTests(unittest.TestCase):
    def test_c33c07_live_row_is_not_an_admitted_final(self) -> None:
        game = dict(
            ncaa_contest_id="synthetic-game",
            home_name="Home",
            away_name="Away",
            home_points=7,
            away_points=0,
            game_state="live",
        )
        grouped = competing_observations([game])
        self.assertEqual(grouped["admitted_unique_games"], [])
        self.assertEqual(len(grouped["nonfinal_contests"]), 1)

    def test_c33c08_two_candidates_are_order_invariant(self) -> None:
        game = dict(
            ncaa_contest_id="synthetic-game",
            home_name="Home",
            away_name="Away",
            home_points=7,
            away_points=0,
            **FINAL,
        )
        f1 = dict(
            ncaa_contest_id="synthetic-game",
            candidate_id="A",
            frozen=True,
            freeze_receipt_id="FR-A",
            frozen_at_utc="2026-09-10T00:00:00Z",
            forecast_row_id="A1",
            probability_home=0.2,
        )
        f2 = dict(
            ncaa_contest_id="synthetic-game",
            candidate_id="B",
            frozen=True,
            freeze_receipt_id="FR-B",
            frozen_at_utc="2026-09-10T00:00:00Z",
            forecast_row_id="B1",
            probability_home=0.8,
        )
        forward = score_unique_frozen_games([game], forecasts=[f1, f2])
        reverse = score_unique_frozen_games([game], forecasts=[f2, f1])
        self.assertEqual(forward["scored_candidate_checkpoint_rows"], 2)
        self.assertEqual(reverse["scored_candidate_checkpoint_rows"], 2)
        self.assertEqual(forward["scored_unique_frozen_games"], 1)
        self.assertAlmostEqual(forward["brier_mean"], reverse["brier_mean"])
        self.assertNotAlmostEqual(forward["brier_mean"], 0.04)
        self.assertNotAlmostEqual(forward["brier_mean"], 0.64)

    def test_c33c09_boolean_freeze_and_probability_two_are_rejected(self) -> None:
        game = dict(
            ncaa_contest_id="synthetic-game",
            home_name="Home",
            away_name="Away",
            home_points=7,
            away_points=0,
            **FINAL,
        )
        result = score_unique_frozen_games(
            [game],
            forecasts=[
                {
                    "ncaa_contest_id": "synthetic-game",
                    "candidate_id": "A",
                    "frozen": True,
                    "probability_home": 2,
                }
            ],
        )
        self.assertEqual(result["scored_candidate_checkpoint_rows"], 0)
        self.assertGreater(result["excluded_unproven_freeze"], 0)

    def test_lawful_pre_to_final_is_not_a_conflict(self) -> None:
        rows = [
            {
                "ncaa_contest_id": "1",
                "home_name": "A",
                "away_name": "B",
                "home_points": None,
                "away_points": None,
                "game_state": "P",
                "status_code_display": "pre",
            },
            {
                "ncaa_contest_id": "1",
                "home_name": "A",
                "away_name": "B",
                "home_points": 10,
                "away_points": 7,
                **FINAL,
            },
        ]
        grouped = competing_observations(rows)
        self.assertEqual(len(grouped["admitted_unique_games"]), 1)
        self.assertEqual(grouped["quarantined_conflicts"], [])


class ContinuationDeadlineCareerQueryTests(unittest.TestCase):
    def test_c33c10_late_boolean_is_not_forecast_frozen(self) -> None:
        now = datetime(2026, 9, 14, tzinfo=timezone.utc)
        observed = deadline_disposition(
            now=now,
            deadline_utc=(now - timedelta(days=1)).isoformat(),
            evidence_present=True,
            freeze_present=True,
            captured_after_deadline=True,
        )
        self.assertNotEqual(observed, "FORECAST_FROZEN")
        self.assertEqual(observed, "EVIDENCE_CAPTURED_LATE_TRUE_TIMESTAMP")

    def test_c33c11_empty_employer_and_virginia_substring(self) -> None:
        self.assertFalse(employer_evidence_matches("", "Virginia"))
        self.assertFalse(employer_evidence_matches("Virginia", "Virginia Tech"))
        self.assertTrue(employer_evidence_matches("Virginia", "University of Virginia"))
        a = {
            "title": "Coach A",
            "wikimedia_page_id": "1",
            "wikimedia_revision": "100",
            "episodes": [{"program_raw": "Virginia Tech", "sport": "football"}],
        }
        b = {
            "title": "Coach A",
            "wikimedia_page_id": "1",
            "wikimedia_revision": "200",
            "episodes": [{"program_raw": "Virginia Tech", "sport": "football"}],
        }
        self.assertEqual(page_identity_key(a), page_identity_key(b))
        joined = join_occupant_to_pages(
            person="Coach A", employer="Virginia", pages=[a, b]
        )
        self.assertEqual(
            joined["career_join_state"], "FOOTBALL_PAGE_EMPLOYER_UNVERIFIED"
        )
        self.assertEqual(joined["distinct_page_identities"], 1)

    def test_query_connect_does_not_create_missing_database(self) -> None:
        missing = Path(tempfile.gettempdir()) / "bas-c33-no-such-query.sqlite"
        if missing.exists():
            missing.unlink()
        with self.assertRaises(StaffQueryError):
            connect_readonly(missing)
        self.assertFalse(missing.exists())

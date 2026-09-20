"""R35-11 tests for MR34-15: absence is unknown, and Out is not injury."""

from __future__ import annotations

import unittest

from aggie_analytics.cycle35.availability import (
    OUTCOME_BLOCKED,
    OUTCOME_EVIDENCE,
    OUTCOME_POLICY_NO_REPORT,
    REASON_UNKNOWN,
    REPORT_STAGES,
    STATUS_AVAILABLE,
    STATUS_OUT,
    STATUS_QUESTIONABLE,
    STATUS_UNKNOWN,
    AvailabilityError,
    ReportOpportunity,
    normalize_status,
    opportunity_coverage,
    parse_tabular_report,
    summarize,
)

HEADER = (
    "Team\tDate\tOpponent\tNumber\tPlayer\tInitial Status\t"
    "Update 1 Status\tUpdate 2 Status\tGame Day Status"
)
ROW = "Alabama\t9/12/26\tat Kentucky\t#0\tAK Dear\tQuestionable\tQuestionable\tOut\tOut"
DASH_ROW = "Arkansas\t9/19/26\tvs. Georgia\t#29\tBrandon Ford\tQuestionable\tDoubtful\tOut\t-"


class StatusVocabularyTests(unittest.TestCase):
    def test_a_dash_is_published_empty_not_available(self) -> None:
        out = normalize_status("-")
        self.assertEqual(out["status"], STATUS_UNKNOWN)
        self.assertEqual(out["presence"], "PUBLISHED_EMPTY")
        self.assertNotEqual(out["status"], STATUS_AVAILABLE)

    def test_empty_string_is_published_empty(self) -> None:
        self.assertEqual(normalize_status("")["presence"], "PUBLISHED_EMPTY")
        self.assertEqual(normalize_status("   ")["presence"], "PUBLISHED_EMPTY")

    def test_known_vocabulary_maps_and_keeps_the_original(self) -> None:
        out = normalize_status("Questionable")
        self.assertEqual(out["status"], STATUS_QUESTIONABLE)
        self.assertEqual(out["raw_text"], "Questionable")
        self.assertTrue(out["vocabulary_recognized"])

    def test_an_unknown_spelling_stays_unknown_and_flags_itself(self) -> None:
        """Silently mapping an unrecognised string replaces the source's
        meaning with ours."""
        out = normalize_status("Probable-ish?")
        self.assertEqual(out["status"], STATUS_UNKNOWN)
        self.assertFalse(out["vocabulary_recognized"])
        self.assertEqual(out["raw_text"], "Probable-ish?")

    def test_game_time_decision_spellings(self) -> None:
        for spelling in ("Game Time Decision", "game-time decision"):
            self.assertEqual(
                normalize_status(spelling)["status"], "GAME_TIME_DECISION"
            )


class ReportParsingTests(unittest.TestCase):
    def test_every_stage_of_every_row_becomes_an_assertion(self) -> None:
        out = parse_tabular_report("\n".join([HEADER, ROW, DASH_ROW]))
        self.assertEqual(out["player_rows"], 2)
        self.assertEqual(out["assertion_count"], 2 * len(REPORT_STAGES))
        self.assertTrue(out["conservation_holds"])
        self.assertEqual(
            sorted({row["stage"] for row in out["assertions"]}), sorted(REPORT_STAGES)
        )

    def test_the_dash_stage_is_retained_as_its_own_assertion(self) -> None:
        out = parse_tabular_report("\n".join([HEADER, DASH_ROW]))
        game_day = [
            row for row in out["assertions"] if row["stage"] == "game_day_status"
        ][0]
        self.assertEqual(game_day["status"], STATUS_UNKNOWN)
        self.assertEqual(game_day["presence"], "PUBLISHED_EMPTY")
        self.assertEqual(game_day["raw_text"], "-")

    def test_out_does_not_imply_injury(self) -> None:
        out = parse_tabular_report("\n".join([HEADER, ROW]))
        row = [r for r in out["assertions"] if r["status"] == STATUS_OUT][0]
        self.assertEqual(row["reason"], REASON_UNKNOWN)
        self.assertTrue(row["out_does_not_imply_injury"])

    def test_publication_time_is_not_asserted_from_a_contest_date(self) -> None:
        out = parse_tabular_report("\n".join([HEADER, ROW]))
        self.assertFalse(out["publication_time_established"])
        self.assertIsNone(out["assertions"][0]["publication_utc"])

    def test_a_byline_does_not_become_a_publication_time(self) -> None:
        out = parse_tabular_report(
            "\n".join([HEADER, ROW]), page_byline_utc="2026-09-12T10:00:00+00:00"
        )
        row = out["assertions"][0]
        self.assertEqual(row["page_byline_utc"], "2026-09-12T10:00:00+00:00")
        self.assertIsNone(row["publication_utc"])
        self.assertFalse(row["byline_is_not_per_report_publication_time"] is False)

    def test_identities_stay_unresolved_without_official_roster_ids(self) -> None:
        out = parse_tabular_report("\n".join([HEADER, ROW]))
        row = out["assertions"][0]
        self.assertEqual(row["identity_state"], "UNRESOLVED_NAME_AND_JERSEY_ONLY")
        self.assertIsNone(row["canonical_player_id"])

    def test_a_malformed_row_is_recorded_not_dropped_silently(self) -> None:
        out = parse_tabular_report("\n".join([HEADER, ROW, "too\tfew\tcells"]))
        self.assertEqual(out["player_rows"], 1)
        self.assertEqual(len(out["malformed_rows"]), 1)

    def test_an_unexpected_header_is_refused(self) -> None:
        with self.assertRaises(AvailabilityError):
            parse_tabular_report("Team\tPlayer\nAlabama\tSomeone")

    def test_empty_input_is_refused(self) -> None:
        with self.assertRaises(AvailabilityError):
            parse_tabular_report("")


class SummaryTests(unittest.TestCase):
    def test_unknown_is_counted_separately_from_available(self) -> None:
        out = parse_tabular_report("\n".join([HEADER, ROW, DASH_ROW]))
        stats = summarize(out["assertions"])
        self.assertIn(STATUS_UNKNOWN, stats["by_status"])
        self.assertNotIn(STATUS_AVAILABLE, stats["by_status"])
        self.assertTrue(stats["unknown_is_not_available"])
        self.assertTrue(stats["absence_of_a_report_is_not_health"])
        self.assertEqual(stats["by_presence"]["PUBLISHED_EMPTY"], 1)


class OpportunityTests(unittest.TestCase):
    @staticmethod
    def _key(outcome: str, classification: str = "fbs", conference: str = "SEC"):
        return ReportOpportunity(
            program_id="P:" + outcome + classification + conference,
            display_name="X",
            classification=classification,
            conference=conference,
            policy_status="KNOWN_PUBLIC_POLICY",
            outcome=outcome,
        )

    def test_no_report_and_blocked_keys_stay_in_the_denominator(self) -> None:
        coverage = opportunity_coverage(
            [
                self._key(OUTCOME_EVIDENCE),
                self._key(OUTCOME_POLICY_NO_REPORT, "fcs", "MVFC"),
                self._key(OUTCOME_BLOCKED, "fcs", "Big Sky"),
            ]
        )
        self.assertEqual(coverage["key_count"], 3)
        self.assertEqual(coverage["evidence_bearing_keys"], 1)
        self.assertTrue(coverage["denominator_includes_no_report_and_blocked_keys"])

    def test_every_key_declares_that_no_report_means_unknown(self) -> None:
        coverage = opportunity_coverage([self._key(OUTCOME_POLICY_NO_REPORT)])
        self.assertEqual(coverage["keys"][0]["no_report_means"], "UNKNOWN")
        self.assertTrue(coverage["keys"][0]["retained_in_denominator"])


if __name__ == "__main__":
    unittest.main()

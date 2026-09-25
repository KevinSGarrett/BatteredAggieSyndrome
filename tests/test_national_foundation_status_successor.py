"""National foundation structured-status successor regressions."""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from aggie_analytics.data.national_foundation_status_successor import (
    FALSE_QUARANTINE_GAME_ID,
    PREDECESSOR_QUARANTINE_RELATIVE,
    PREDECESSOR_QUARANTINE_SHA256,
    classify_status_successor,
    outcome_result,
    parse_completed_flag,
    restore_false_quarantine,
)


class NationalFoundationStatusSuccessorTests(unittest.TestCase):
    def test_false_quarantine_restore_from_structured_final(self) -> None:
        row = {
            "id": 312472199,
            "notes": "originally postponed then completed",
            "completed": True,
            "homePoints": 41,
            "awayPoints": 9,
            "status": "final",
            "season": 2011,
            "homeTeam": "Howard",
            "awayTeam": "Eastern Michigan",
        }
        classified = classify_status_successor(row)
        self.assertTrue(classified["false_quarantine_corrected"])
        self.assertEqual(
            classified["disposition"], "RESTORE_FALSE_SUBSTRING_QUARANTINE"
        )
        restored = restore_false_quarantine(row)
        self.assertEqual(
            restored["normalized_game"]["canonical_game_id"], FALSE_QUARANTINE_GAME_ID
        )
        self.assertEqual(restored["outcome_label"]["outcome_result"], "HOME_WIN")
        self.assertEqual(restored["outcome_label"]["point_margin_home_minus_away"], 32)
        self.assertFalse(restored["normalized_game"]["pit_feature_eligible"])

    def test_completed_string_false_is_not_truthy(self) -> None:
        self.assertIsNone(parse_completed_flag("false"))
        self.assertIsNone(parse_completed_flag("true"))
        classified = classify_status_successor(
            {
                "canonical_game_id": FALSE_QUARANTINE_GAME_ID,
                "notes": "postponed",
                "completed": "false",
                "homePoints": 41,
                "awayPoints": 9,
                "status": "final",
                "season": 2011,
            }
        )
        self.assertNotEqual(
            classified["disposition"], "RESTORE_FALSE_SUBSTRING_QUARANTINE"
        )
        self.assertEqual(classified["structured_reason"], "completed_flag_unproven")

    def test_structured_postponed_status_stays_quarantined(self) -> None:
        classified = classify_status_successor(
            {
                "id": 1,
                "completed": True,
                "status": "postponed",
                "homePoints": 7,
                "awayPoints": 3,
                "season": 2011,
            }
        )
        self.assertEqual(classified["disposition"], "QUARANTINE_STRUCTURED_NON_FINAL")

    def test_tie_outcome_is_explicit(self) -> None:
        self.assertEqual(outcome_result(17, 17), "TIE")
        self.assertEqual(outcome_result(10, 21), "AWAY_WIN")

    def test_predecessor_quarantine_immutable_when_mounted(self) -> None:
        data_root = Path(r"C:\BatteredAggieSyndrome.data")
        path = data_root / PREDECESSOR_QUARANTINE_RELATIVE
        if not path.is_file():
            self.skipTest("national foundation quarantine payload is not mounted")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(digest, PREDECESSOR_QUARANTINE_SHA256)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from aggie_analytics.cycle30.populations import week1_slice_from_contests


class Cycle30Week1ProgramSliceTests(unittest.TestCase):
    def test_uses_canonical_team_ids_from_contest_rows(self) -> None:
        contests = [
            {
                "ncaa_contest_id": "123",
                "home_canonical_team_id": "SRC-002:TEAM:1",
                "away_canonical_team_id": "SRC-002:TEAM:2",
                "home": None,
                "away": None,
            },
            {
                "ncaa_contest_id": "124",
                "home_canonical_team_id": "SRC-002:TEAM:3",
                "away_canonical_team_id": "SRC-002:TEAM:4",
                "home": None,
                "away": None,
            },
        ]
        payload = week1_slice_from_contests(contests)
        self.assertEqual(payload["identity_class"], "CANONICAL_PROGRAM_ID")
        self.assertEqual(payload["artifact_class"], "REAL_EVIDENCE")
        self.assertEqual(payload["distinct_canonical_program_count_W"], 4)
        self.assertEqual(payload["unresolved_contest_count"], 0)
        self.assertEqual(payload["unresolved_contest_ids"], [])

    def test_falls_back_to_display_when_ids_are_missing(self) -> None:
        contests = [
            {
                "ncaa_contest_id": "200",
                "home": "Team A",
                "away": "Team B",
            }
        ]
        payload = week1_slice_from_contests(contests)
        self.assertEqual(payload["identity_class"], "DISPLAY_NAME_NOT_CANONICAL")
        self.assertEqual(payload["artifact_class"], "BLOCKER_METADATA")
        self.assertEqual(payload["unresolved_contest_count"], 1)
        self.assertEqual(payload["unresolved_contest_ids"], ["200"])
        self.assertIn("DISPLAY:Team A", payload["programs"])
        self.assertIn("DISPLAY:Team B", payload["programs"])


if __name__ == "__main__":
    unittest.main()

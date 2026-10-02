"""R34-06: the one stratification sub-case with zero coverage all session
(true namesake collision -- two distinct real people sharing a confusable
name) is now covered, using a real, verified pair rather than a fabricated
one: Mike White (American football coach, 1936-2025, Cal/Illinois/Raiders
head coach) and Mike White (defensive lineman, b. 1957, Albany State/
Benedict College head coach) -- two unrelated real people, confirmed via
Wikipedia's own "Mike White (American football)" disambiguation page
(fetched this round) to be genuinely distinct individuals, not aliases or
a data-entry duplicate.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.cycle33.career_identity import join_occupant_to_pages  # noqa: E402

PAGE_COACH = {
    "title": "Mike White (American football coach)",
    "episodes": [
        {"program_raw": team, "person": "Mike White", "sport": "football"}
        for team in (
            "California", "Stanford", "California", "Illinois",
            "San Francisco 49ers", "Los Angeles Raiders", "Oakland Raiders",
            "St. Louis Rams", "Kansas City Chiefs",
        )
    ],
}
PAGE_LINEMAN = {
    "title": "Mike White (defensive lineman)",
    "episodes": [
        {"program_raw": team, "person": "Mike White", "sport": "football"}
        for team in (
            "Cincinnati Bengals", "Seattle Seahawks", "Albany State",
            "Albany State", "Albany State", "Albany State", "Benedict College",
        )
    ],
}


class NamesakeCollisionTests(unittest.TestCase):
    def test_each_real_namesake_resolves_individually(self) -> None:
        coach = join_occupant_to_pages(
            person="Mike White", program_display="Illinois", pages=[PAGE_COACH]
        )
        self.assertEqual(coach["career_join_state"], "EVIDENCE_BOUND_CAREER_JOIN")

        lineman = join_occupant_to_pages(
            person="Mike White", program_display="Albany State", pages=[PAGE_LINEMAN]
        )
        self.assertEqual(lineman["career_join_state"], "EVIDENCE_BOUND_CAREER_JOIN")

    def test_genuine_namesake_collision_is_flagged_ambiguous_not_guessed(self) -> None:
        # When both real people's pages are presented together for a bare
        # name query (the realistic shape of a name-only search hitting two
        # distinct namesakes), the join must refuse to silently pick one --
        # this is the actual safety property the "namesake" stratification
        # case in R34-06 exists to exercise.
        result = join_occupant_to_pages(
            person="Mike White", program_display="Illinois",
            pages=[PAGE_COACH, PAGE_LINEMAN],
        )
        self.assertEqual(result["career_join_state"], "AMBIGUOUS_MULTIPLE_FOOTBALL_PAGES")
        self.assertEqual(result["distinct_page_identities"], 2)
        self.assertTrue(result["same_name_only"])


if __name__ == "__main__":
    unittest.main()

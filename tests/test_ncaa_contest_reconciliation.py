from __future__ import annotations

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data.ncaa_contest_reconciliation import normalize_team_name, parse_team_page


class NcaaContestReconciliationTests(unittest.TestCase):
    def test_normalization_is_exact_but_punctuation_stable(self) -> None:
        self.assertEqual(normalize_team_name("Texas A&M"), "texas a and m")
        self.assertEqual(normalize_team_name("San Jos\u00e9 St."), "san jose state")
        self.assertEqual(normalize_team_name("Birmingham-So."), "birmingham southern")

    def test_team_page_parser_preserves_oriented_score_and_ids(self) -> None:
        payload = """
        <div class="card-header"><img class="logo_image" alt="Texas A&M" src="https://x/All_Logos/sm//697.gif"> Texas A&M Aggies</div>
        <tr class="underline_rows">
          <td>09/02/2023</td>
          <td>@<a href="/teams/557111"><img alt="New Mexico" src="x"></a></td>
          <td><a href="/contests/1234567/box_score">W 52-10</a></td>
        </tr>
        """
        page, rows = parse_team_page(payload, team_season_id="557999", raw_sha256="a" * 64)
        self.assertIsNotNone(page)
        self.assertEqual(page["source_team_org_id"], "697")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["contest_id"], "1234567")
        self.assertEqual(rows[0]["source_team_points"], 52)
        self.assertEqual(rows[0]["opponent_points"], 10)
        self.assertTrue(rows[0]["source_team_is_away"])

    def test_unrecognized_owner_fails_closed(self) -> None:
        page, rows = parse_team_page("<html>challenge</html>", team_season_id="1", raw_sha256="b" * 64)
        self.assertIsNone(page)
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()

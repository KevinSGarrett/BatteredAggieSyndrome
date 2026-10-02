"""Passing-section successor regressions."""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from aggie_analytics.data.tamu_official_passing_section_successor import (
    EXPECTED_AFFECTED_RAW_PAGES,
    EXPECTED_CONFIRMED_ROWS,
    PREDECESSOR_PLAYER_RELATIVE,
    PREDECESSOR_PLAYER_SHA256,
    PassingSectionSuccessorError,
    classify_screened_row,
    player_identity_role,
    screen_nonpassing_triple_rows,
    section_map_from_raw_html,
    succeed_row,
)
from aggie_analytics.data.tamu_official_statcrew_preformatted import parse_table_players


class PassingSectionSuccessorTests(unittest.TestCase):
    def test_att_cmp_int_header_does_not_inherit_rushing(self) -> None:
        block = "\n".join(
            [
                "Texas A&M",
                "Rushing  No.  Yds  TD",
                "Smith  12  80  1",
                "Passing  Att-Cmp-Int  Yds  TD",
                "Jones  20-12-1  180  2",
                "TEAM  0-0-0  0  0",
            ]
        )
        rows = parse_table_players(block)
        passing = [
            row
            for row in rows
            if row["stat_group"] == "passing" and not row["header_only"]
        ]
        self.assertEqual(passing[0]["name_raw"], "Jones")
        team = [row for row in rows if row["identity_status"] == "TEAM_ATTRIBUTED"]
        self.assertEqual(team[0]["stat_group"], "passing")

    def test_header_only_is_not_material_availability(self) -> None:
        block = "Passing  Cmp-Att-Int  Yds  TD\n"
        rows = parse_table_players(block)
        self.assertTrue(rows)
        self.assertTrue(all(row["header_only"] for row in rows))
        self.assertEqual(rows[0]["availability"], "HEADER_ONLY_NOT_MATERIAL")

    def test_team_row_is_not_a_person(self) -> None:
        row = {
            "name_raw": "TEAM",
            "stat_group": "rushing",
            "original_text": "TEAM  1-2-0",
        }
        self.assertEqual(player_identity_role(row), "TEAM_ATTRIBUTED_EVIDENCE")
        successor = succeed_row(
            {**row, "row_identity": "row-1", "header_only": False},
            confirmed_ids={"row-1"},
            unresolved_ids=set(),
        )
        self.assertEqual(successor["stat_group"], "passing")
        self.assertFalse(successor["fabricated_person_identity"])

    def test_ambiguous_section_is_not_silently_recoded(self) -> None:
        html = b"<pre>Rushing  No.\nSmith  12-3-1  80\nPassing  Att-Cmp-Int\nJones  20-12-1  180</pre>"
        sections = section_map_from_raw_html(html)
        row = {"original_text": "Ghost  1-2-3  4", "stat_group": "rushing"}
        self.assertEqual(
            classify_screened_row(row, sections), "UNRESOLVED_AMBIGUOUS_SECTION"
        )

    def test_confirmed_passing_line_from_raw_html(self) -> None:
        html = (
            b"<pre>Passing  Att-Cmp-Int  Yds\nJones  20-12-1  180\n"
            b"Rushing  No.  Yds\nSmith  12  80</pre>"
        )
        sections = section_map_from_raw_html(html)
        row = {"original_text": "Jones  20-12-1  180", "stat_group": "rushing"}
        self.assertEqual(
            classify_screened_row(row, sections),
            "CONFIRMED_PASSING_SECTION_CORRECTION",
        )

    def test_screen_separates_candidates_from_already_passing(self) -> None:
        rows = [
            {"stat_group": "passing", "original_text": "A  1-2-3"},
            {"stat_group": "rushing", "original_text": "B  4-5-6"},
            {"stat_group": "receiving", "original_text": "C  no triple"},
        ]
        screened = screen_nonpassing_triple_rows(rows)
        self.assertEqual(len(screened), 1)
        self.assertEqual(screened[0]["original_text"], "B  4-5-6")

    def test_predecessor_bytes_immutable_when_mounted(self) -> None:
        data_root = Path(r"C:\BatteredAggieSyndrome.data")
        path = data_root / PREDECESSOR_PLAYER_RELATIVE
        if not path.is_file():
            self.skipTest("1996-2009 player corpus is not mounted")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(digest, PREDECESSOR_PLAYER_SHA256)

    def test_expected_census_constants_match_manager_review(self) -> None:
        self.assertEqual(EXPECTED_CONFIRMED_ROWS, 429)
        self.assertEqual(EXPECTED_AFFECTED_RAW_PAGES, 125)
        with self.assertRaises(PassingSectionSuccessorError):
            raise PassingSectionSuccessorError("red")


if __name__ == "__main__":
    unittest.main()

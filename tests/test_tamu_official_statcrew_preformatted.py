from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "tests"))

from cycle26_frozen_predecessor import contained_reconstruction  # noqa: E402

from aggie_analytics.data.tamu_official_statcrew_preformatted import (  # noqa: E402
    AuthorityViolation,
    BOX_2007_DATASET_IDENTITY,
    GATE_RELATIVE,
    PRE2010_DATASET_IDENTITY,
    compute_gate_identity,
    lake_is_ready,
    parse_play_by_play,
    parse_player_statistics,
    parse_preformatted_page,
    parse_team_statistics,
    sha256_bytes,
    validate_artifact,
)

DATA_ROOT = Path(
    os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
)
LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and lake_is_ready(
    DATA_ROOT
)
MSU_SHA = "a28f8c250713bab3efa3ee24ab4546c4c1d38d65d0ad64f7b4351e2127121ff9"
MSU_URL = "https://files.12thman.com/history/football/stats/2007-2008/ta01-msu.htm"


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


TEAM_HTML = """
<pre>
Team Statistics (Final)
                                   MSU     TAMU
FIRST DOWNS...................       23       16
  Rushing.....................        5       10
NET YARDS RUSHING.............       99      261
</pre>
"""

PLAYER_HTML = """
<pre>
Individual Statistics (Final)
Montana State
Rushing              No Gain Loss  Net TD Lg  Avg
-------------------------------------------------
D. Crawford          13   52    5   47  0 11  3.6
Isaiah Taito         14   45    3   42  0  9  3.0
Passing              Cmp-Att-Int Yds TD Long Sack
-------------------------------------------------
Jack Rolovich        21-39-0   267  1   16    1
Receiving             No.  Yds   TD Long
----------------------------------------
D. Crawford             5   34    0   12
</pre>
"""

DRIVE_HTML = """
<pre>
Drive Chart (Final)
Team     Qtr Spot Time   Obtained      Spot Time   How Lost      Pl-Yds   TOP
-------------------------------------------------------------------------------------
MSU      1st M30  15:00  Kickoff       M30  09:44  TOUCHDOWN     13-0    5:16
TAMU     1st T30  09:44  Kickoff       T25  07:13  FIELD GOAL     5-30   2:31
Drive Chart (By Quarter)
MSU      1st M30  15:00  Kickoff       M30  09:44  TOUCHDOWN     13-0    5:16
</pre>
"""

PBP_HTML = """
<pre>
Play-by-Play Summary (1st quarter)
Msu 1-10 at Msu30 TAMU ball on TAMU30, Szymanski kickoff 68 yards.
Msu 1-10 at Msu17 Aaron Mason rush for 4 yards.
</pre>
"""

SCORING_ONLY_HTML = """
<pre>
Scoring Summary (Final)
Texas A&M vs Georgia (Dec 28, 2009 at Shreveport, La.)
Scoring Summary:
2nd 02:33 TAMU - McCoy, Jamie 15 yd pass from Johnson, Jerrod
</pre>
"""


class PreformattedParserUnitTests(unittest.TestCase):
    def test_spaced_script_end_tag_is_filtered(self) -> None:
        html = (
            "<script>injected();</script\t\n bar>\n"
            "<pre>\nTeam Statistics (Final)\nFIRST DOWNS................... 23 16\n</pre>\n"
        )
        parsed = parse_preformatted_page(
            html.encode("utf-8"),
            url=MSU_URL,
            source_season=2007,
            raw_sha256=sha256_bytes(html.encode("utf-8")),
        )
        self.assertEqual(parsed["domain_coverage"]["team_statistics"], "PRESENT")
        self.assertTrue(
            all("injected" not in row["stat_raw"] for row in parsed["team_statistics"])
        )

    def test_team_statistics_require_source_labels(self) -> None:
        rows = parse_team_statistics(
            "Team Statistics (Final)\nMSU TAMU\nFIRST DOWNS................... 23 16\nNET YARDS RUSHING............. 99 261\n"
        )
        self.assertGreaterEqual(len(rows), 2)
        self.assertEqual(rows[0]["stat_raw"], "FIRST DOWNS")
        self.assertEqual(rows[0]["visitor_raw"], "23")
        self.assertEqual(rows[0]["home_raw"], "16")

    def test_scoring_summary_alone_is_not_team_statistics(self) -> None:
        parsed = parse_preformatted_page(
            SCORING_ONLY_HTML.encode("utf-8"),
            url="https://files.12thman.com/history/football/stats/2009-2010/ta13-uga.html",
            source_season=2009,
            raw_sha256=sha256_bytes(SCORING_ONLY_HTML.encode("utf-8")),
        )
        self.assertEqual(parsed["domain_coverage"]["team_statistics"], "ABSENT")
        self.assertFalse(parsed["rich_structured"])

    def test_player_rows_are_not_merged_by_name(self) -> None:
        rows = parse_player_statistics(
            "Individual Statistics (Final)\nRushing              No Gain Loss  Net TD Lg  Avg\nD. Crawford          13   52    5   47  0 11  3.6\nReceiving             No.  Yds   TD Long\nD. Crawford             5   34    0   12\n"
        )
        names = [(row["name_raw"], row["stat_group"]) for row in rows]
        self.assertEqual(names.count(("D. Crawford", "rushing")), 1)
        self.assertEqual(names.count(("D. Crawford", "receiving")), 1)

    def test_missing_play_by_play_stays_absent(self) -> None:
        rows = parse_play_by_play(
            "Team Statistics (Final)\nFIRST DOWNS................... 23 16\n"
        )
        self.assertEqual(rows, [])

    def test_ambiguous_team_tables_are_rejected(self) -> None:
        html = TEAM_HTML + TEAM_HTML.replace("23", "99").replace("16", "11")
        parsed = parse_preformatted_page(
            html.encode("utf-8"),
            url="https://files.12thman.com/history/football/stats/2007-2008/ta01-msu.htm",
            source_season=2007,
            raw_sha256=sha256_bytes(html.encode("utf-8")),
        )
        self.assertEqual(parsed["domain_coverage"]["team_statistics"], "ABSENT")
        self.assertTrue(any("ambiguous" in item for item in parsed["warnings"]))

    def test_rows_bind_to_raw_hash_and_url(self) -> None:
        body = (TEAM_HTML + PLAYER_HTML + DRIVE_HTML + PBP_HTML).encode("utf-8")
        parsed = parse_preformatted_page(
            body,
            url=MSU_URL,
            source_season=2007,
            raw_sha256=sha256_bytes(body),
        )
        for domain in (
            "team_statistics",
            "individual_player_statistics",
            "drives",
            "play_by_play",
        ):
            self.assertEqual(parsed["domain_coverage"][domain], "PRESENT")
            self.assertTrue(parsed[domain])
            for index, row in enumerate(parsed[domain]):
                self.assertEqual(row["source_url"], MSU_URL)
                self.assertEqual(row["source_sha256"], sha256_bytes(body))
                self.assertEqual(row["row_order"], index)
                self.assertEqual(row["availability"], "NOT_ESTABLISHED")

    def test_raw_tamper_is_rejected(self) -> None:
        body = TEAM_HTML.encode("utf-8")
        with self.assertRaisesRegex(AuthorityViolation, "changed raw source hash"):
            parse_preformatted_page(
                body + b" ",
                url=MSU_URL,
                source_season=2007,
                raw_sha256=sha256_bytes(body),
            )

    def test_cross_game_rows_do_not_share_urls(self) -> None:
        first = parse_preformatted_page(
            PLAYER_HTML.encode("utf-8"),
            url="https://files.12thman.com/history/football/stats/2007-2008/ta01-msu.htm",
            source_season=2007,
            raw_sha256=sha256_bytes(PLAYER_HTML.encode("utf-8")),
        )
        second = parse_preformatted_page(
            PLAYER_HTML.replace("Montana State", "Penn State").encode("utf-8"),
            url="https://files.12thman.com/history/football/stats/2007-2008/mfb_8523_alamo.html",
            source_season=2007,
            raw_sha256=sha256_bytes(
                PLAYER_HTML.replace("Montana State", "Penn State").encode("utf-8")
            ),
        )
        first_urls = {
            row["source_url"] for row in first["individual_player_statistics"]
        }
        second_urls = {
            row["source_url"] for row in second["individual_player_statistics"]
        }
        self.assertEqual(
            first_urls,
            {"https://files.12thman.com/history/football/stats/2007-2008/ta01-msu.htm"},
        )
        self.assertEqual(
            second_urls,
            {
                "https://files.12thman.com/history/football/stats/2007-2008/mfb_8523_alamo.html"
            },
        )
        self.assertTrue(first_urls.isdisjoint(second_urls))

    def test_participation_is_not_availability(self) -> None:
        html = PLAYER_HTML.replace(
            "</pre>", "Player participation:\nTexas A&M: 1-Johnson, Jerrod\n</pre>"
        )
        parsed = parse_preformatted_page(
            html.encode("utf-8"),
            url=MSU_URL,
            source_season=2007,
            raw_sha256=sha256_bytes(html.encode("utf-8")),
        )
        self.assertFalse(parsed["availability_claim"])
        self.assertTrue(
            all(
                row["availability"] == "NOT_ESTABLISHED"
                for row in parsed["individual_player_statistics"]
            )
        )


class CompactGateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("StatCrew preformatted gate not materialized yet")
        self.gate = json.loads(path.read_text(encoding="utf-8-sig"))

    def test_protected_lane_opened_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, protected_lane="OPEN"),
                require_rebuild=False,
            )

    def test_prior_payload_rewrite_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat586_dataset_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-586"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, upstream_identities=upstream),
                require_rebuild=False,
            )


@unittest.skipUnless(LAKE_READY, "external official 2007-2009 captures are not mounted")
class StatCrewLakeTests(unittest.TestCase):
    def test_committed_gate_reconstructs(self) -> None:
        result = contained_reconstruction(
            self,
            repo_root=REPO_ROOT,
            gate_relative=GATE_RELATIVE,
            call=lambda: validate_artifact(
                repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True
            ),
        )
        if result is None:
            return
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["parsed_games"], 38)
        self.assertEqual(
            result["payload_identity"],
            "ba0820e45938714c144c4accee6637a67812e70dd89e4eb99b0373fc88a91d1d",
        )
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        self.assertEqual(
            gate["gate_identity"],
            "9c3da52dceebd8da0908aa478326196bef2338095a8b5d4c42decaa27df53e16",
        )
        self.assertEqual(gate["counts"]["team_statistics_present_games"], 38)
        self.assertEqual(
            gate["counts"]["individual_player_statistics_present_games"], 38
        )
        self.assertEqual(gate["counts"]["drives_present_games"], 37)
        self.assertEqual(gate["counts"]["play_by_play_present_games"], 37)
        self.assertEqual(gate["counts"]["play_by_play_absent_games"], 1)
        self.assertEqual(
            gate["upstream_identities"]["bat586_dataset_identity"],
            PRE2010_DATASET_IDENTITY,
        )
        self.assertEqual(
            gate["upstream_identities"]["bat589_dataset_identity"],
            BOX_2007_DATASET_IDENTITY,
        )
        msu = next(item for item in gate["games"] if item["url"] == MSU_URL)
        self.assertEqual(msu["source_sha256"], MSU_SHA)
        self.assertEqual(msu["domain_coverage"]["play_by_play"], "ABSENT")
        self.assertEqual(msu["domain_coverage"]["drives"], "ABSENT")
        self.assertEqual(msu["domain_coverage"]["team_statistics"], "PRESENT")


if __name__ == "__main__":
    unittest.main()

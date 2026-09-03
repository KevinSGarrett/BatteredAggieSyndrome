from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_2004_structured_domains import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    PINNED_BAT591_GATE_IDENTITY,
    PINNED_BAT596_GATE_IDENTITY,
    PINNED_BAT601_GATE_IDENTITY,
    PINNED_BAT604_GATE_IDENTITY,
    PINNED_BAT605_GATE_IDENTITY,
    PINNED_TABLE_PARSER_IDENTITY,
    PREFORMATTED_PARSER_IDENTITY,
    compute_gate_identity,
    lake_is_ready,
    validate_artifact,
)
from aggie_analytics.data.tamu_official_historical_boxscores import (  # noqa: E402
    availability_from_participation,
    refuse_name_only_player_merge,
)
from aggie_analytics.data.tamu_official_html_table_classifier import (  # noqa: E402
    PARSER_IDENTITY as TABLE_PARSER_IDENTITY,
    classify_headers,
)
from aggie_analytics.data.tamu_official_statcrew_preformatted import (  # noqa: E402
    parse_preformatted_page,
    sha256_bytes,
)


DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and lake_is_ready(DATA_ROOT)
UTAH_URL = "https://files.12thman.com/history/football/stats/2004-2005/mfb_116_utah.html"
EXPECTED_GATE_IDENTITY = "1b3fb5536ff535b23a910a462857b0c7c1e29f66b3d937e0b1de90e85ac179b6"
EXPECTED_PAYLOAD_IDENTITY = "80ba101dc4699c32eae44e963be627ac1edff00a09e2dd459780f11f6930122c"

TEAM_HTML = """
<pre>
Team Statistics (Final)
                                   UTAH     TAMU
FIRST DOWNS...................       23       16
  Rushing.....................        5       10
NET YARDS RUSHING.............       99      261
</pre>
"""

PLAYER_HTML = """
<pre>
Individual Statistics (Final)
Utah
Rushing              No Gain Loss  Net TD Lg  Avg
-------------------------------------------------
D. Crawford          13   52    5   47  0 11  3.6
Receiving             No.  Yds   TD Long
----------------------------------------
D. Crawford             5   34    0   12
</pre>
"""


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class Official2004StructuredParserUnitTests(unittest.TestCase):
    def test_conflicting_team_blocks_fail_closed(self) -> None:
        html = TEAM_HTML + TEAM_HTML.replace("23", "99").replace("16", "11")
        parsed = parse_preformatted_page(
            html.encode("utf-8"),
            url=UTAH_URL,
            source_season=2004,
            raw_sha256=sha256_bytes(html.encode("utf-8")),
        )
        self.assertEqual(parsed["domain_coverage"]["team_statistics"], "ABSENT")
        self.assertTrue(any("ambiguous" in item for item in parsed["warnings"]))

    def test_reordered_headers_remain_unknown(self) -> None:
        self.assertEqual(classify_headers(["Yds", "RUSHING", "No."]), "unknown")
        self.assertEqual(classify_headers(["Drive Started", "Score by Quarters", "1", "2"]), "unknown")

    def test_empty_headings_remain_unknown(self) -> None:
        self.assertEqual(classify_headers([]), "unknown")
        self.assertEqual(classify_headers(["", "", ""]), "unknown")

    def test_html_table_classifier_identity_is_not_mutated(self) -> None:
        self.assertEqual(TABLE_PARSER_IDENTITY, PINNED_TABLE_PARSER_IDENTITY)
        self.assertEqual(TABLE_PARSER_IDENTITY, "tamu.official.html.table.classifier.v1")

    def test_player_name_merge_is_refused(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "name-only player merge"):
            refuse_name_only_player_merge([{"name_raw": "D. Crawford"}, {"name_raw": "D. Crawford"}])

    def test_participation_does_not_become_availability(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "participation does not establish availability"):
            availability_from_participation({"name_raw": "D. Crawford", "availability": "NOT_ESTABLISHED"})

    def test_source_hash_substitution_fails(self) -> None:
        body = TEAM_HTML.encode("utf-8")
        with self.assertRaisesRegex(AuthorityViolation, "changed raw source hash"):
            parse_preformatted_page(
                body + b" ",
                url=UTAH_URL,
                source_season=2004,
                raw_sha256=sha256_bytes(body),
            )

    def test_rows_bind_and_do_not_promote_availability(self) -> None:
        body = (TEAM_HTML + PLAYER_HTML).encode("utf-8")
        parsed = parse_preformatted_page(
            body,
            url=UTAH_URL,
            source_season=2004,
            raw_sha256=sha256_bytes(body),
        )
        self.assertFalse(parsed["availability_claim"])
        self.assertIsNone(parsed["ncaa_contest_id"])
        names = [(row["name_raw"], row["stat_group"]) for row in parsed["individual_player_statistics"]]
        self.assertEqual(names.count(("D. Crawford", "rushing")), 1)
        self.assertEqual(names.count(("D. Crawford", "receiving")), 1)
        for row in parsed["team_statistics"] + parsed["individual_player_statistics"]:
            self.assertEqual(row["source_url"], UTAH_URL)
            self.assertEqual(row["source_sha256"], sha256_bytes(body))
            self.assertEqual(row["availability"], "NOT_ESTABLISHED")


class Compact2004StructuredDomainGateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("2004 structured-domain gate not materialized yet")
        self.gate = json.loads(path.read_text(encoding="utf-8-sig"))

    def test_protected_lane_opened_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, protected_lane="OPEN"), require_rebuild=False)

    def test_participation_as_availability_fails(self) -> None:
        authority = json.loads(json.dumps(self.gate["authority"]))
        authority["participation_as_availability"] = True
        with self.assertRaisesRegex(AuthorityViolation, "availability"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, authority=authority), require_rebuild=False)

    def test_invented_ncaa_id_fails(self) -> None:
        counts = json.loads(json.dumps(self.gate["counts"]))
        counts["ncaa_contest_ids_created"] = 1
        with self.assertRaisesRegex(AuthorityViolation, "NCAA"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, counts=counts), require_rebuild=False)

    def test_coverage_without_rows_fails(self) -> None:
        counts = json.loads(json.dumps(self.gate["counts"]))
        counts["team_statistics_serialized_rows"] = 0
        counts["team_statistics_present_games"] = 12
        with self.assertRaisesRegex(AuthorityViolation, "serialized"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, counts=counts), require_rebuild=False)

    def test_parser_identity_change_fails(self) -> None:
        games = json.loads(json.dumps(self.gate["games"]))
        games[0]["parser_identity"] = "forged.parser.v9"
        with self.assertRaisesRegex(AuthorityViolation, "parser identity"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, games=games), require_rebuild=False)

    def test_bat601_rewrite_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat601_gate_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-601"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, upstream_identities=upstream), require_rebuild=False)

    def test_classifier_identity_mutation_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["html_table_classifier_identity"] = "forged.classifier.v9"
        with self.assertRaisesRegex(AuthorityViolation, "classifier"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, upstream_identities=upstream), require_rebuild=False)

    def test_forged_completion_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "completion"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION"),
                require_rebuild=False,
            )


@unittest.skipUnless(LAKE_READY, "external BAT-605 captures are not mounted")
class Official2004StructuredDomainReconstructionTests(unittest.TestCase):
    def test_committed_gate_reconstructs(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["gate_identity"], EXPECTED_GATE_IDENTITY)
        self.assertEqual(result["payload_identity"], EXPECTED_PAYLOAD_IDENTITY)
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        self.assertEqual(gate["gate_identity"], EXPECTED_GATE_IDENTITY)
        self.assertEqual(gate["payload_identity"], EXPECTED_PAYLOAD_IDENTITY)
        self.assertEqual(gate["counts"]["parsed_games"], 12)
        self.assertEqual(gate["counts"]["rich_structured_games"], 12)
        self.assertEqual(gate["counts"]["team_statistics_present_games"], 12)
        self.assertEqual(gate["counts"]["individual_player_statistics_present_games"], 12)
        self.assertEqual(gate["counts"]["drives_present_games"], 12)
        self.assertEqual(gate["counts"]["play_by_play_present_games"], 12)
        self.assertEqual(gate["counts"]["serialized_rows_total"], 5747)
        self.assertEqual(gate["counts"]["ncaa_contest_ids_created"], 0)
        self.assertEqual(gate["counts"]["pregame_availability_present"], 0)
        self.assertEqual(gate["counts"]["games_admitted_to_union"], 0)
        self.assertEqual(gate["counts"]["html_tables_classified_pages"], 0)
        self.assertGreater(gate["counts"]["serialized_rows_total"], 0)
        self.assertEqual(gate["upstream_identities"]["bat605_gate_identity"], PINNED_BAT605_GATE_IDENTITY)
        self.assertEqual(gate["upstream_identities"]["bat604_gate_identity"], PINNED_BAT604_GATE_IDENTITY)
        self.assertEqual(gate["upstream_identities"]["bat601_gate_identity"], PINNED_BAT601_GATE_IDENTITY)
        self.assertEqual(gate["upstream_identities"]["bat596_gate_identity"], PINNED_BAT596_GATE_IDENTITY)
        self.assertEqual(gate["upstream_identities"]["bat591_gate_identity"], PINNED_BAT591_GATE_IDENTITY)
        self.assertEqual(gate["upstream_identities"]["html_table_classifier_identity"], PINNED_TABLE_PARSER_IDENTITY)
        self.assertFalse(gate["authority"]["participation_as_availability"])
        self.assertFalse(gate["authority"]["name_only_player_merge"])
        for game in gate["games"]:
            self.assertEqual(game["parser_identity"], PREFORMATTED_PARSER_IDENTITY)
            for domain, flag in game["domain_coverage"].items():
                if flag == "PRESENT":
                    self.assertGreater(game["row_counts"][domain], 0)

    def test_url_substitution_fails(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        games = json.loads(json.dumps(gate["games"]))
        games[0]["url"] = "https://files.12thman.com/history/football/stats/2004-2005/forged.html"
        with self.assertRaisesRegex(AuthorityViolation, "does not match independent reconstruction"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(gate, games=games), require_rebuild=True)

    def test_source_hash_substitution_fails(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        games = json.loads(json.dumps(gate["games"]))
        games[0]["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "does not match independent reconstruction"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(gate, games=games), require_rebuild=True)

    def test_row_insertion_and_removal_fail(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        games = json.loads(json.dumps(gate["games"]))
        games[0]["row_counts"]["team_statistics"] = int(games[0]["row_counts"]["team_statistics"]) + 1
        with self.assertRaisesRegex(AuthorityViolation, "does not match independent reconstruction"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(gate, games=games), require_rebuild=True)
        games2 = json.loads(json.dumps(gate["games"]))
        games2[0]["row_counts"]["play_by_play"] = max(0, int(games2[0]["row_counts"]["play_by_play"]) - 1)
        with self.assertRaisesRegex(AuthorityViolation, "does not match independent reconstruction"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(gate, games=games2), require_rebuild=True)


if __name__ == "__main__":
    unittest.main()

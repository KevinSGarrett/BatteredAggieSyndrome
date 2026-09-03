from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_2005_structured_domains import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    MSU_2007_URL,
    PINNED_BAT591_GATE_IDENTITY,
    PINNED_BAT595_GATE_IDENTITY,
    PINNED_BAT596_GATE_IDENTITY,
    PINNED_BAT600_GATE_IDENTITY,
    TEXAS_2006_URL,
    compute_gate_identity,
    lake_is_ready,
    validate_artifact,
)
from aggie_analytics.data.tamu_official_html_table_classifier import (  # noqa: E402
    classify_headers,
    classify_page,
    extract_tables,
)


DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and lake_is_ready(DATA_ROOT)
EXPECTED_GATE_IDENTITY = "b4964041f1b87392ad61c5781c300531051dc9f1a71dfaf630cbeb25af20f96d"
EXPECTED_PAYLOAD_IDENTITY = "5b5d2b1f28566179d6a04de5bac00ff6aea540227ef01508492476fa17fd9abc"


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class HtmlTableClassifierTests(unittest.TestCase):
    def test_empty_headers_are_unknown_not_play_by_play(self) -> None:
        self.assertEqual(classify_headers([]), "unknown")
        self.assertEqual(classify_headers(["", "", ""]), "unknown")

    def test_observed_headers_classify_domains(self) -> None:
        self.assertEqual(classify_headers(["Team Totals", "TA", "UT"]), "team_statistics")
        self.assertEqual(classify_headers(["RUSHING", "No.", "Gain", "Loss", "Net"]), "individual_player_statistics")
        self.assertEqual(classify_headers(["Score by Quarters", "1", "2", "3", "4", "Score"]), "scoring_summary")
        self.assertEqual(classify_headers(["", "Drive Started", "Drive Ended", "Consumed", ""]), "drives")
        self.assertEqual(classify_headers(["Team Statistics"]), "heading")

    def test_reordered_or_ambiguous_headers_fail_closed(self) -> None:
        self.assertEqual(classify_headers(["Yds", "RUSHING", "No."]), "unknown")
        self.assertEqual(classify_headers(["Drive Started", "Score by Quarters", "1", "2", "3", "4"]), "unknown")

    def test_table_order_is_source_bound(self) -> None:
        first = (
            b"<table><tr><td>Team Totals</td><td>TA</td><td>UT</td></tr>"
            b"<tr><td>First Downs</td><td>1</td><td>2</td></tr></table>"
            b"<table><tr><td>RUSHING</td><td>No.</td><td>Gain</td></tr>"
            b"<tr><td>Player</td><td>3</td><td>4</td></tr></table>"
        )
        swapped = (
            b"<table><tr><td>RUSHING</td><td>No.</td><td>Gain</td></tr>"
            b"<tr><td>Player</td><td>3</td><td>4</td></tr></table>"
            b"<table><tr><td>Team Totals</td><td>TA</td><td>UT</td></tr>"
            b"<tr><td>First Downs</td><td>1</td><td>2</td></tr></table>"
        )
        ordered = extract_tables(first)
        reordered = extract_tables(swapped)
        self.assertEqual([item["table_index"] for item in ordered], [0, 1])
        self.assertEqual(ordered[0]["classification"], "team_statistics")
        self.assertEqual(ordered[1]["classification"], "individual_player_statistics")
        self.assertEqual(reordered[0]["classification"], "individual_player_statistics")
        self.assertEqual(reordered[1]["classification"], "team_statistics")
        self.assertNotEqual(ordered[0]["header_fingerprint"], reordered[0]["header_fingerprint"])

    def test_row_contents_and_hashes_bind_to_source(self) -> None:
        body = (
            b"<table><tr><td>Team Totals</td><td>TA</td><td>UT</td></tr>"
            b"<tr><td>First Downs</td><td>1</td><td>2</td></tr></table>"
        )
        page = classify_page(body, url="https://files.12thman.com/history/football/stats/2006-2007/texas.htm", raw_sha256="a" * 64, source_season=2006)
        self.assertEqual(page["source_sha256"], "a" * 64)
        self.assertTrue(all(row["source_sha256"] == "a" * 64 for row in page["classified_rows"]))
        self.assertEqual(page["classified_rows"][1]["cells"], ["First Downs", "1", "2"])
        changed = classify_page(
            body.replace(b"First Downs", b"Second Downs"),
            url="https://files.12thman.com/history/football/stats/2006-2007/texas.htm",
            raw_sha256="b" * 64,
            source_season=2006,
        )
        self.assertNotEqual(page["rows_identity"], changed["rows_identity"])
        self.assertNotEqual(page["source_sha256"], changed["source_sha256"])


class Compact2005StructuredDomainGateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("2005 structured-domain gate not materialized yet")
        self.gate = json.loads(path.read_text(encoding="utf-8-sig"))

    def test_protected_lane_opened_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, protected_lane="OPEN"), require_rebuild=False)

    def test_bat596_rewrite_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat596_gate_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-596"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, upstream_identities=upstream), require_rebuild=False)

    def test_forged_html_pbp_fails(self) -> None:
        html = json.loads(json.dumps(self.gate["html_table_classifications"]))
        html["texas_2006"]["domain_coverage"]["play_by_play"] = "PRESENT"
        with self.assertRaisesRegex(AuthorityViolation, "play-by-play"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, html_table_classifications=html), require_rebuild=False)

    def test_participation_does_not_become_availability(self) -> None:
        html = json.loads(json.dumps(self.gate["html_table_classifications"]))
        html["texas_2006"]["availability_claim"] = True
        with self.assertRaisesRegex(AuthorityViolation, "availability"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, html_table_classifications=html), require_rebuild=False)


@unittest.skipUnless(LAKE_READY, "external BAT-601 captures are not mounted")
class Official2005StructuredDomainTests(unittest.TestCase):
    def test_committed_gate_reconstructs(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        self.assertEqual(result["result"], "PASS")
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        self.assertEqual(gate["gate_identity"], EXPECTED_GATE_IDENTITY)
        self.assertEqual(gate["payload_identity"], EXPECTED_PAYLOAD_IDENTITY)
        self.assertEqual(gate["counts"]["parsed_games"], 11)
        self.assertEqual(gate["counts"]["rich_structured_games"], 11)
        self.assertEqual(gate["counts"]["team_statistics_present_games"], 11)
        self.assertEqual(gate["counts"]["individual_player_statistics_present_games"], 11)
        self.assertEqual(gate["counts"]["drives_present_games"], 11)
        self.assertEqual(gate["counts"]["play_by_play_present_games"], 11)
        self.assertEqual(gate["counts"]["html_play_by_play_present_pages"], 0)
        self.assertEqual(gate["counts"]["ncaa_contest_ids_created"], 0)
        self.assertEqual(gate["counts"]["pregame_availability_present"], 0)
        self.assertEqual(gate["upstream_identities"]["bat600_gate_identity"], PINNED_BAT600_GATE_IDENTITY)
        self.assertEqual(gate["upstream_identities"]["bat596_gate_identity"], PINNED_BAT596_GATE_IDENTITY)
        self.assertEqual(gate["upstream_identities"]["bat591_gate_identity"], PINNED_BAT591_GATE_IDENTITY)
        self.assertEqual(gate["upstream_identities"]["bat595_gate_identity"], PINNED_BAT595_GATE_IDENTITY)
        texas = gate["html_table_classifications"]["texas_2006"]
        msu = gate["html_table_classifications"]["montana_state_2007"]
        self.assertEqual(texas["url"], TEXAS_2006_URL)
        self.assertEqual(msu["url"], MSU_2007_URL)
        self.assertEqual(texas["domain_coverage"]["play_by_play"], "ABSENT")
        self.assertEqual(msu["domain_coverage"]["play_by_play"], "ABSENT")
        self.assertEqual(texas["domain_coverage"]["participation"], "PRESENT")
        self.assertFalse(texas["availability_claim"])
        self.assertFalse(gate["authority"]["participation_as_availability"])

    def test_html_hash_and_row_identity_tampers_fail(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        html = json.loads(json.dumps(gate["html_table_classifications"]))
        html["texas_2006"]["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "does not match independent reconstruction"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(gate, html_table_classifications=html), require_rebuild=True)
        html_rows = json.loads(json.dumps(gate["html_table_classifications"]))
        swapped = html_rows["texas_2006"]["rows_identity"]
        html_rows["texas_2006"]["rows_identity"] = html_rows["montana_state_2007"]["rows_identity"]
        html_rows["montana_state_2007"]["rows_identity"] = swapped
        with self.assertRaisesRegex(AuthorityViolation, "does not match independent reconstruction"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(gate, html_table_classifications=html_rows), require_rebuild=True)


if __name__ == "__main__":
    unittest.main()

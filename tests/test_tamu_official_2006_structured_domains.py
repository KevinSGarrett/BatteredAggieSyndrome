from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_2006_structured_domains import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    HTML_AUDIT_URL,
    INVENTORY_IDENTITY,
    PINNED_BAT586_GATE_IDENTITY,
    PINNED_BAT589_GATE_IDENTITY,
    PINNED_BAT591_GATE_IDENTITY,
    PINNED_BAT591_PAYLOAD_IDENTITY,
    PINNED_BAT595_ACQUISITION_IDENTITY,
    PINNED_BAT595_DATASET_IDENTITY,
    PINNED_BAT595_GATE_IDENTITY,
    compute_gate_identity,
    lake_is_ready,
    validate_artifact,
)


DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and lake_is_ready(DATA_ROOT)
TEXAS_URL = "https://files.12thman.com/history/football/stats/2006-2007/texas.htm"
EXPECTED_GATE_IDENTITY = "57eb2e0b9e449bef0b7935b89c573bfed79110e53d1de414984e0f781baa97a4"
EXPECTED_PAYLOAD_IDENTITY = "039c773f902cbea6d7c6e361ac10315dfec364e30ebb83003bf3717cd9d1dfea"
EXPECTED_HTML_ROWS_IDENTITY = "579f89802cb1ccb5d10b40728d378baed787ce5699243b23d5d63f4859521f98"


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class Compact2006StructuredDomainGateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("2006 structured-domain gate not materialized yet")
        self.gate = json.loads(path.read_text(encoding="utf-8-sig"))

    def test_committed_counts_and_upstream_identities(self) -> None:
        self.assertEqual(self.gate["gate_identity"], EXPECTED_GATE_IDENTITY)
        self.assertEqual(self.gate["payload_identity"], EXPECTED_PAYLOAD_IDENTITY)
        self.assertEqual(self.gate["inventory_identity"], INVENTORY_IDENTITY)
        self.assertEqual(self.gate["counts"]["parsed_games"], 13)
        self.assertEqual(self.gate["counts"]["rich_structured_games"], 13)
        self.assertEqual(self.gate["counts"]["metadata_only_games"], 0)
        self.assertEqual(self.gate["counts"]["team_statistics_present_games"], 13)
        self.assertEqual(self.gate["counts"]["individual_player_statistics_present_games"], 13)
        self.assertEqual(self.gate["counts"]["drives_present_games"], 12)
        self.assertEqual(self.gate["counts"]["play_by_play_present_games"], 12)
        self.assertEqual(self.gate["counts"]["html_table_audit_rows"], 364)
        self.assertEqual(self.gate["counts"]["html_table_audit_present"], 1)
        self.assertEqual(self.gate["counts"]["ncaa_contest_ids_created"], 0)
        self.assertEqual(self.gate["counts"]["pregame_availability_present"], 0)
        self.assertEqual(self.gate["counts"]["games_admitted_to_union"], 0)
        self.assertEqual(self.gate["html_table_audit"]["url"], HTML_AUDIT_URL)
        self.assertEqual(self.gate["html_table_audit"]["rows_identity"], EXPECTED_HTML_ROWS_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat595_gate_identity"], PINNED_BAT595_GATE_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat595_acquisition_identity"], PINNED_BAT595_ACQUISITION_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat595_dataset_identity"], PINNED_BAT595_DATASET_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat591_gate_identity"], PINNED_BAT591_GATE_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat591_payload_identity"], PINNED_BAT591_PAYLOAD_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat589_gate_identity"], PINNED_BAT589_GATE_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat586_gate_identity"], PINNED_BAT586_GATE_IDENTITY)
        texas = next(game for game in self.gate["games"] if game["url"] == TEXAS_URL)
        self.assertTrue(texas["rich_structured"])
        self.assertEqual(texas["domain_coverage"]["drives"], "ABSENT")
        self.assertEqual(texas["domain_coverage"]["play_by_play"], "ABSENT")

    def test_phase3_boxscore_richness_is_not_rewritten(self) -> None:
        bat595 = json.loads((REPO_ROOT / "artifacts/data_lake/tamu_official_2006_boxscore_gate.json").read_text(encoding="utf-8"))
        self.assertEqual(bat595["gate_identity"], PINNED_BAT595_GATE_IDENTITY)
        self.assertEqual(bat595["counts"]["rich_structured_games"], 1)
        self.assertEqual(bat595["counts"]["metadata_only_games"], 12)

    def test_protected_lane_opened_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, protected_lane="OPEN"), require_rebuild=False)

    def test_retrieval_time_as_known_at_fails(self) -> None:
        authority = json.loads(json.dumps(self.gate["authority"]))
        authority["historical_known_at_from_capture_time"] = True
        with self.assertRaisesRegex(AuthorityViolation, "known-at"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, authority=authority), require_rebuild=False)

    def test_ncaa_contest_ids_fail(self) -> None:
        counts = json.loads(json.dumps(self.gate["counts"]))
        counts["ncaa_contest_ids_created"] = 1
        with self.assertRaisesRegex(AuthorityViolation, "NCAA"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, counts=counts), require_rebuild=False)

    def test_availability_claim_fails(self) -> None:
        counts = json.loads(json.dumps(self.gate["counts"]))
        counts["pregame_availability_present"] = 1
        with self.assertRaisesRegex(AuthorityViolation, "availability"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, counts=counts), require_rebuild=False)

    def test_bat591_rewrite_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat591_gate_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-591"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, upstream_identities=upstream), require_rebuild=False)

    def test_bat595_rewrite_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat595_gate_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-595"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, upstream_identities=upstream), require_rebuild=False)

    def test_html_present_without_rows_fails(self) -> None:
        html = json.loads(json.dumps(self.gate["html_table_audit"]))
        html["html_table_row_count"] = 0
        html["rows_identity"] = ""
        with self.assertRaisesRegex(AuthorityViolation, "HTML-table PRESENT"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, html_table_audit=html), require_rebuild=False)

    def test_forged_completion_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "completion"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION"),
                require_rebuild=False,
            )


@unittest.skipUnless(LAKE_READY, "external BAT-595/BAT-589 captures are not mounted")
class Official2006StructuredDomainReconstructionTests(unittest.TestCase):
    def test_committed_gate_reconstructs(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["parsed_games"], 13)
        self.assertEqual(result["html_table_audit_rows"], 364)
        self.assertEqual(result["gate_identity"], EXPECTED_GATE_IDENTITY)
        self.assertEqual(result["payload_identity"], EXPECTED_PAYLOAD_IDENTITY)


if __name__ == "__main__":
    unittest.main()

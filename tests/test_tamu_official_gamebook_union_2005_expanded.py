from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_gamebook_union_2005_expanded import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    OFFICIAL_2005_EXPECTED,
    PINNED_BAT591_PAYLOAD_IDENTITY,
    PINNED_BAT597_GATE_IDENTITY,
    PINNED_BAT597_UNION_IDENTITY,
    PINNED_BAT600_GATE_IDENTITY,
    PINNED_BAT601_PAYLOAD_IDENTITY,
    PRESERVED_REJECTION_URLS,
    compute_gate_identity,
    lake_is_ready,
    validate_artifact,
)


DATA_ROOT = Path(r"C:\\BatteredAggieSyndrome.data")
LAKE_READY = lake_is_ready(DATA_ROOT)
EXPECTED_GATE_IDENTITY = "d58074fd309da1a6fac386c63d08cd1f150d4ec40d23d5720fa057b18cb35fb8"
EXPECTED_UNION_IDENTITY = "c15f5c33b14ac42322766c3c1be817be67d5b27f29c0cb77b164893980046200"


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class Compact2005ExpandedUnionTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("2005-expanded union gate not materialized yet")
        self.gate = json.loads(path.read_text(encoding="utf-8-sig"))

    def test_committed_counts_and_prior_identities(self) -> None:
        self.assertEqual(self.gate["gate_identity"], EXPECTED_GATE_IDENTITY)
        self.assertEqual(self.gate["union_identity"], EXPECTED_UNION_IDENTITY)
        self.assertEqual(self.gate["prior_union_identity"], PINNED_BAT597_UNION_IDENTITY)
        self.assertEqual(self.gate["prior_union_gate_identity"], PINNED_BAT597_GATE_IDENTITY)
        self.assertEqual(self.gate["counts"]["new_games_added"], OFFICIAL_2005_EXPECTED)
        self.assertEqual(self.gate["counts"]["official_2005_added"], 11)
        self.assertEqual(self.gate["counts"]["prior_250_union_games_preserved"], 250)
        self.assertEqual(self.gate["counts"]["union_captured_games"], 261)
        self.assertEqual(self.gate["counts"]["rich_structured_games"], 248)
        self.assertEqual(self.gate["counts"]["metadata_only_games"], 13)
        self.assertEqual(self.gate["counts"]["scoring_summary_present_games"], 58)
        self.assertEqual(self.gate["counts"]["unmatched_rejected"], 4)
        self.assertEqual(self.gate["counts"]["date_conflicts"], 4)
        self.assertEqual(self.gate["counts"]["season_header_conflicts"], 1)
        self.assertEqual(self.gate["counts"]["matched_strong_tuple"], 54)
        self.assertEqual(self.gate["counts"]["ncaa_contest_ids_created"], 0)
        self.assertEqual(self.gate["coverage_by_season"]["2005"]["official_school_games"], 11)
        self.assertEqual(self.gate["coverage_by_season"]["2005"]["rich_structured_games"], 11)
        self.assertEqual(self.gate["coverage_by_season"]["2005"]["became_rich"], 11)
        self.assertEqual(self.gate["upstream_identities"]["bat597_union_identity"], PINNED_BAT597_UNION_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat601_payload_identity"], PINNED_BAT601_PAYLOAD_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat591_payload_identity"], PINNED_BAT591_PAYLOAD_IDENTITY)
        rejected = {item["url"] for item in self.gate["preserved_rejections"]}
        admitted = {item["url"] for item in self.gate["enriched_official_games"]}
        self.assertEqual(rejected, set(PRESERVED_REJECTION_URLS))
        self.assertTrue(rejected.isdisjoint(admitted))
        self.assertTrue(all(item.get("structured_row_payload_identity") == PINNED_BAT601_PAYLOAD_IDENTITY for item in self.gate["admitted_official_2005_games"]))
        self.assertFalse(any(item.get("availability_claim") for item in self.gate["enriched_official_games"]))
        self.assertFalse(any(item.get("ncaa_contest_id") for item in self.gate["enriched_official_games"]))

    def test_prior_identities_are_not_rewritten(self) -> None:
        bat597 = json.loads((REPO_ROOT / "artifacts/data_lake/tamu_official_gamebook_union_2006_expanded_gate.json").read_text(encoding="utf-8"))
        bat600 = json.loads((REPO_ROOT / "artifacts/data_lake/tamu_official_2005_boxscore_gate.json").read_text(encoding="utf-8"))
        self.assertEqual(bat597["union_identity"], PINNED_BAT597_UNION_IDENTITY)
        self.assertEqual(bat597["gate_identity"], PINNED_BAT597_GATE_IDENTITY)
        self.assertEqual(bat600["gate_identity"], PINNED_BAT600_GATE_IDENTITY)
        self.assertEqual(bat600["counts"]["games_admitted_to_union"], 0)

    def test_protected_lane_opened_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, protected_lane="OPEN"), require_rebuild=False)

    def test_bat597_rewrite_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "BAT-597"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, prior_union_identity="0" * 64), require_rebuild=False)

    def test_forged_completion_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "completion"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION"),
                require_rebuild=False,
            )


@unittest.skipUnless(LAKE_READY, "external BAT-600 2005 payload is not mounted")
class Official2005ExpandedUnionReconstructionTests(unittest.TestCase):
    def test_committed_gate_reconstructs(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["gate_identity"], EXPECTED_GATE_IDENTITY)
        self.assertEqual(result["union_identity"], EXPECTED_UNION_IDENTITY)
        self.assertEqual(result["counts"]["official_2005_added"], 11)
        self.assertEqual(result["counts"]["union_captured_games"], 261)


if __name__ == "__main__":
    unittest.main()

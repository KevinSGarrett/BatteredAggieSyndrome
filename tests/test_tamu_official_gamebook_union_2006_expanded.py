from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_gamebook_union_2006_expanded import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    OFFICIAL_2006_EXPECTED,
    PINNED_BAT591_PAYLOAD_IDENTITY,
    PINNED_BAT592_GATE_IDENTITY,
    PINNED_BAT592_UNION_IDENTITY,
    PINNED_BAT595_GATE_IDENTITY,
    PINNED_BAT596_PAYLOAD_IDENTITY,
    PRESERVED_REJECTION_URLS,
    compute_gate_identity,
    lake_is_ready,
    validate_artifact,
)


DATA_ROOT = Path(r"C:\\BatteredAggieSyndrome.data")
LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and lake_is_ready(DATA_ROOT)
EXPECTED_GATE_IDENTITY = "6a3a276087d3341b3826dec9c58391d54eaa42055149d7d7705e9e1a1d1601ff"
EXPECTED_UNION_IDENTITY = "cd9bd79899bb4c4f0e8d3d7c79482d5146075e4bf51a1bd488597b28607fbe98"


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class Compact2006ExpandedUnionTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("2006-expanded union gate not materialized yet")
        self.gate = json.loads(path.read_text(encoding="utf-8-sig"))

    def test_committed_counts_and_prior_identities(self) -> None:
        self.assertEqual(self.gate["gate_identity"], EXPECTED_GATE_IDENTITY)
        self.assertEqual(self.gate["union_identity"], EXPECTED_UNION_IDENTITY)
        self.assertEqual(self.gate["prior_union_identity"], PINNED_BAT592_UNION_IDENTITY)
        self.assertEqual(self.gate["prior_union_gate_identity"], PINNED_BAT592_GATE_IDENTITY)
        self.assertEqual(self.gate["counts"]["new_games_added"], OFFICIAL_2006_EXPECTED)
        self.assertEqual(self.gate["counts"]["official_2006_added"], 13)
        self.assertEqual(self.gate["counts"]["union_captured_games"], 250)
        self.assertEqual(self.gate["counts"]["rich_structured_games"], 237)
        self.assertEqual(self.gate["counts"]["metadata_only_games"], 13)
        self.assertEqual(self.gate["counts"]["unmatched_rejected"], 4)
        self.assertEqual(self.gate["counts"]["date_conflicts"], 4)
        self.assertEqual(self.gate["counts"]["matched_strong_tuple"], 43)
        self.assertEqual(self.gate["counts"]["ncaa_contest_ids_created"], 0)
        self.assertEqual(self.gate["coverage_by_season"]["2006"]["official_school_games"], 13)
        self.assertEqual(self.gate["coverage_by_season"]["2006"]["rich_structured_games"], 13)
        self.assertEqual(self.gate["coverage_by_season"]["2006"]["became_rich"], 12)
        self.assertEqual(self.gate["upstream_identities"]["bat591_payload_identity"], PINNED_BAT591_PAYLOAD_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat596_payload_identity"], PINNED_BAT596_PAYLOAD_IDENTITY)
        rejected = {item["url"] for item in self.gate["preserved_rejections"]}
        admitted = {item["url"] for item in self.gate["enriched_official_games"]}
        self.assertEqual(rejected, set(PRESERVED_REJECTION_URLS))
        self.assertTrue(rejected.isdisjoint(admitted))

    def test_prior_identities_are_not_rewritten(self) -> None:
        bat592 = json.loads((REPO_ROOT / "artifacts/data_lake/tamu_official_gamebook_union_enriched_gate.json").read_text(encoding="utf-8"))
        bat595 = json.loads((REPO_ROOT / "artifacts/data_lake/tamu_official_2006_boxscore_gate.json").read_text(encoding="utf-8"))
        self.assertEqual(bat592["union_identity"], PINNED_BAT592_UNION_IDENTITY)
        self.assertEqual(bat592["gate_identity"], PINNED_BAT592_GATE_IDENTITY)
        self.assertEqual(bat595["gate_identity"], PINNED_BAT595_GATE_IDENTITY)
        self.assertEqual(bat595["counts"]["rich_structured_games"], 1)
        self.assertEqual(bat595["counts"]["games_admitted_to_union"], 0)

    def test_protected_lane_opened_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, protected_lane="OPEN"), require_rebuild=False)

    def test_bat592_rewrite_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "BAT-592"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, prior_union_identity="0" * 64), require_rebuild=False)

    def test_forged_completion_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "completion"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION"),
                require_rebuild=False,
            )


@unittest.skipUnless(LAKE_READY, "external BAT-595 2006 payload is not mounted")
class Official2006ExpandedUnionReconstructionTests(unittest.TestCase):
    def test_committed_gate_reconstructs(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["gate_identity"], EXPECTED_GATE_IDENTITY)
        self.assertEqual(result["union_identity"], EXPECTED_UNION_IDENTITY)
        self.assertEqual(result["counts"]["official_2006_added"], 13)


if __name__ == "__main__":
    unittest.main()

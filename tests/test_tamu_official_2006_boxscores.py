from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_2006_boxscores import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    INVENTORY_IDENTITY,
    OFFICIAL_2006_INDEX_URL,
    PINNED_BAT589_GATE_IDENTITY,
    compute_gate_identity,
    lake_is_ready,
    load_source_index,
    selected_targets,
    validate_artifact,
)


DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = lake_is_ready(DATA_ROOT)


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class Official2006AllowlistTests(unittest.TestCase):
    def test_source_index_is_the_bat594_allowlist(self) -> None:
        source = load_source_index(REPO_ROOT, DATA_ROOT)
        targets = selected_targets(source)
        self.assertEqual(source["official_index_url"], OFFICIAL_2006_INDEX_URL)
        self.assertEqual(source["inventory_gate"]["inventory_identity"], INVENTORY_IDENTITY)
        self.assertEqual(len(targets), 13)
        self.assertTrue(all(item["season"] == 2006 for item in targets))
        self.assertTrue(all(item["official_index_url"] == OFFICIAL_2006_INDEX_URL for item in targets))
        bat589 = json.loads((REPO_ROOT / "artifacts/data_lake/tamu_official_2007_boxscore_gate.json").read_text(encoding="utf-8"))
        self.assertEqual(bat589["gate_identity"], PINNED_BAT589_GATE_IDENTITY)


class Compact2006BoxscoreGateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("2006 boxscore gate not materialized yet")
        self.gate = json.loads(path.read_text(encoding="utf-8-sig"))

    def test_protected_lane_opened_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, protected_lane="OPEN"), require_rebuild=False)

    def test_inventory_rewrite_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "inventory"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, inventory_identity="0" * 64), require_rebuild=False)

    def test_availability_claim_fails(self) -> None:
        counts = json.loads(json.dumps(self.gate["counts"]))
        counts["pregame_availability_present"] = 1
        with self.assertRaisesRegex(AuthorityViolation, "availability"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, counts=counts), require_rebuild=False)

    def test_retrieval_time_as_known_at_fails(self) -> None:
        authority = json.loads(json.dumps(self.gate["authority"]))
        authority["historical_known_at_from_capture_time"] = True
        with self.assertRaisesRegex(AuthorityViolation, "known-at"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, authority=authority), require_rebuild=False)

    def test_bat589_rewrite_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat589_gate_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-589"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, upstream_identities=upstream), require_rebuild=False)


@unittest.skipUnless(LAKE_READY, "external BAT-595 2006 captures are not mounted")
class Official2006AcquisitionTests(unittest.TestCase):
    def test_committed_gate_reconstructs(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["normalized_games"], 13)
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        self.assertEqual(gate["counts"]["expected_box_urls"], 13)
        self.assertEqual(gate["counts"]["acquired_responses"], 13)
        self.assertEqual(gate["counts"]["rejected_responses"], 0)
        self.assertEqual(gate["counts"]["failures"], 0)
        self.assertEqual(gate["counts"]["ambiguous_pages"], 2)
        self.assertEqual(gate["counts"]["date_conflicts"], 2)
        self.assertEqual(gate["counts"]["rich_structured_games"], 1)
        self.assertEqual(gate["counts"]["metadata_only_games"], 12)
        self.assertEqual(gate["counts"]["scoring_summary_present_games"], 13)
        self.assertEqual(gate["counts"]["ncaa_contest_ids_created"], 0)
        self.assertEqual(gate["counts"]["pregame_availability_present"], 0)
        self.assertEqual(gate["counts"]["games_admitted_to_union"], 0)
        self.assertEqual(gate["acquisition_identity"], "1ed988f759f383b62625d582ac70ee306a36c84d92ccded9f70c9fd11bfed269")
        self.assertEqual(gate["dataset_identity"], "05ac9ce54a107007b433e52d7a52f85d7e20726d9aaf7ca204332a75f88cd697")
        self.assertEqual(gate["games_identity"], "40e37b3ac4a015def27682bc994a6b222567a84ed4745594cd9d56f7ebf0621b")
        self.assertEqual(gate["gate_identity"], "2a9c56a10b14cf5fec4dff1c3cd55d0b4440afdb9520fb308317a9ae59c47ed7")
        self.assertEqual(gate["upstream_identities"]["bat589_gate_identity"], PINNED_BAT589_GATE_IDENTITY)
        self.assertFalse(gate["authority"]["participation_as_availability"])
        self.assertFalse(gate["authority"]["availability_claim"])


if __name__ == "__main__":
    unittest.main()

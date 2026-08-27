from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_2005_boxscores import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    INVENTORY_IDENTITY,
    OFFICIAL_2005_INDEX_URL,
    PINNED_BAT595_GATE_IDENTITY,
    compute_gate_identity,
    lake_is_ready,
    load_source_index,
    selected_targets,
    validate_artifact,
)
from aggie_analytics.data.tamu_official_historical_archive import (  # noqa: E402
    validate_official_url,
)


DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and lake_is_ready(DATA_ROOT)


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class Official2005AllowlistTests(unittest.TestCase):
    def test_source_index_is_the_bat599_allowlist(self) -> None:
        source = load_source_index(REPO_ROOT, DATA_ROOT)
        targets = selected_targets(source)
        self.assertEqual(source["official_index_url"], OFFICIAL_2005_INDEX_URL)
        self.assertEqual(source["inventory_gate"]["inventory_identity"], INVENTORY_IDENTITY)
        self.assertEqual(len(targets), 11)
        self.assertTrue(all(item["season"] == 2005 for item in targets))
        self.assertTrue(all(item["official_index_url"] == OFFICIAL_2005_INDEX_URL for item in targets))
        bat595 = json.loads((REPO_ROOT / "artifacts/data_lake/tamu_official_2006_boxscore_gate.json").read_text(encoding="utf-8"))
        self.assertEqual(bat595["gate_identity"], PINNED_BAT595_GATE_IDENTITY)
        allowed = {item["box_url"] for item in targets}
        self.assertNotIn("https://files.12thman.com/history/football/years/2005.html", allowed)
        with self.assertRaisesRegex(Exception, "nonofficial host"):
            validate_official_url("https://example.com/history/football/stats/2005-2006/guessed.htm")


class Compact2005BoxscoreGateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("2005 boxscore gate not materialized yet")
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

    def test_bat595_rewrite_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat595_gate_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-595"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, upstream_identities=upstream), require_rebuild=False)

    def test_invented_ncaa_ids_fail(self) -> None:
        counts = json.loads(json.dumps(self.gate["counts"]))
        counts["ncaa_contest_ids_created"] = 1
        with self.assertRaisesRegex(AuthorityViolation, "NCAA"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, counts=counts), require_rebuild=False)

    def test_forged_completion_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "completion"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION"),
                require_rebuild=False,
            )

    def test_acquisition_hash_tamper_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "reconstruction"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, acquisition_identity="0" * 64),
                require_rebuild=True,
            )

    def test_membership_count_tamper_fails(self) -> None:
        counts = json.loads(json.dumps(self.gate["counts"]))
        counts["normalized_games"] = 12
        counts["metadata_only_games"] = 12
        with self.assertRaisesRegex(AuthorityViolation, "reconstruction"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, counts=counts), require_rebuild=True)

    def test_ordering_identity_tamper_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "reconstruction"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, games_identity="0" * 64),
                require_rebuild=True,
            )

    def test_richness_forged_fails(self) -> None:
        counts = json.loads(json.dumps(self.gate["counts"]))
        counts["rich_structured_games"] = 11
        counts["metadata_only_games"] = 0
        with self.assertRaisesRegex(AuthorityViolation, "reconstruction"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, counts=counts), require_rebuild=True)


@unittest.skipUnless(LAKE_READY, "external BAT-600 2005 captures are not mounted")
class Official2005AcquisitionTests(unittest.TestCase):
    def test_committed_gate_reconstructs(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["normalized_games"], 11)
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        self.assertEqual(gate["counts"]["expected_box_urls"], 11)
        self.assertEqual(gate["counts"]["acquired_responses"], 11)
        self.assertEqual(gate["counts"]["rejected_responses"], 0)
        self.assertEqual(gate["counts"]["failures"], 0)
        self.assertEqual(gate["counts"]["rich_structured_games"], 0)
        self.assertEqual(gate["counts"]["metadata_only_games"], 11)
        self.assertEqual(gate["counts"]["scoring_summary_present_games"], 11)
        self.assertEqual(gate["counts"]["season_header_conflicts"], 1)
        self.assertEqual(gate["counts"]["ncaa_contest_ids_created"], 0)
        self.assertEqual(gate["counts"]["pregame_availability_present"], 0)
        self.assertEqual(gate["counts"]["games_admitted_to_union"], 0)
        self.assertEqual(gate["acquisition_identity"], "56aa050f4bf12c2e02a93915e03125f6cf782ea5b5cfd8b9bab63d724c3e5b59")
        self.assertEqual(gate["dataset_identity"], "e063378e564a3dcdbb09e42ea63cc0a843e9db8918130ecffd02f796c3805dbb")
        self.assertEqual(gate["games_identity"], "7bb39a7eaad39fa1b1c3ce640c78f309935c307c18d8498e6143cc35009153aa")
        self.assertEqual(gate["gate_identity"], "c999af29522096e4ae3a9cdc558679321095c8cf11247ef1ccd23b3114ee18cc")
        self.assertEqual(gate["upstream_identities"]["bat599_gate_identity"], "17868efadbc5cc6ec04869d194b8b8a205089c3050b069eec3e5ba9c1d25c301")
        self.assertEqual(gate["upstream_identities"]["bat595_gate_identity"], PINNED_BAT595_GATE_IDENTITY)
        self.assertFalse(gate["authority"]["participation_as_availability"])
        self.assertFalse(gate["authority"]["availability_claim"])


if __name__ == "__main__":
    unittest.main()

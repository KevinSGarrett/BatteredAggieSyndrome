from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_2003_boxscores import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    INVENTORY_IDENTITY,
    OFFICIAL_2003_INDEX_URL,
    PINNED_BAT600_GATE_IDENTITY,
    PINNED_BAT604_GATE_IDENTITY,
    PINNED_BAT605_GATE_IDENTITY,
    PINNED_BAT609_BOX_URL_IDENTITY,
    PINNED_BAT609_GATE_IDENTITY,
    compute_gate_identity,
    lake_is_ready,
    load_source_index,
    selected_targets,
    validate_artifact,
)
from aggie_analytics.data.tamu_official_historical_archive import (  # noqa: E402
    validate_official_url,
)
from aggie_analytics.data.tamu_official_historical_boxscores import (  # noqa: E402
    availability_from_participation as shared_availability_from_participation,
    refuse_name_only_player_merge as shared_refuse_name_only_player_merge,
)


DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = lake_is_ready(DATA_ROOT)


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class Official2003AllowlistTests(unittest.TestCase):
    def test_source_index_is_the_reconstructed_bat609_allowlist(self) -> None:
        source = load_source_index(REPO_ROOT, DATA_ROOT)
        targets = selected_targets(source)
        self.assertEqual(source["official_index_url"], OFFICIAL_2003_INDEX_URL)
        self.assertEqual(source["inventory_gate"]["inventory_identity"], INVENTORY_IDENTITY)
        self.assertEqual(source["gate"]["gate_identity"], PINNED_BAT609_GATE_IDENTITY)
        self.assertEqual(source["gate"]["box_url_identity"], PINNED_BAT609_BOX_URL_IDENTITY)
        self.assertEqual(len(targets), len(source["box_score_urls"]))
        self.assertTrue(all(item["season"] == 2003 for item in targets))
        self.assertTrue(all(item["official_index_url"] == OFFICIAL_2003_INDEX_URL for item in targets))
        bat605 = json.loads((REPO_ROOT / "artifacts/data_lake/tamu_official_2004_boxscore_gate.json").read_text(encoding="utf-8"))
        self.assertEqual(bat605["gate_identity"], PINNED_BAT605_GATE_IDENTITY)
        bat600 = json.loads((REPO_ROOT / "artifacts/data_lake/tamu_official_2005_boxscore_gate.json").read_text(encoding="utf-8"))
        self.assertEqual(bat600["gate_identity"], PINNED_BAT600_GATE_IDENTITY)
        bat604 = json.loads((REPO_ROOT / "artifacts/data_lake/tamu_official_2004_season_index_gate.json").read_text(encoding="utf-8"))
        self.assertEqual(bat604["gate_identity"], PINNED_BAT604_GATE_IDENTITY)
        allowed = {item["box_url"] for item in targets}
        self.assertNotIn(OFFICIAL_2003_INDEX_URL, allowed)
        self.assertNotIn("https://files.12thman.com/history/football/years/2004.html", allowed)
        with self.assertRaisesRegex(Exception, "nonofficial host"):
            validate_official_url("https://example.com/history/football/stats/2003-2004/guessed.htm")


class Compact2003BoxscoreGateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("2003 boxscore gate not materialized yet")
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

    def test_bat600_rewrite_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat600_gate_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-600"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, upstream_identities=upstream), require_rebuild=False)

    def test_bat604_rewrite_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat604_gate_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-604"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, upstream_identities=upstream), require_rebuild=False)

    def test_bat609_rewrite_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat609_gate_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-609"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, upstream_identities=upstream), require_rebuild=False)

    def test_bat605_rewrite_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat605_gate_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-605"):
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

    def test_name_only_player_merge_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "name-only player merge"):
            shared_refuse_name_only_player_merge([{"player_name": "A"}, {"player_name": "A"}])

    def test_participation_is_not_availability(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "participation"):
            shared_availability_from_participation({"player_name": "A"})


@unittest.skipUnless(LAKE_READY, "external BAT-610 2003 captures are not mounted")
class Official2003AcquisitionTests(unittest.TestCase):
    def test_committed_gate_reconstructs(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["normalized_games"], 12)
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        self.assertEqual(gate["counts"]["expected_box_urls"], 12)
        self.assertEqual(gate["counts"]["acquired_responses"], 12)
        self.assertEqual(gate["counts"]["rejected_responses"], 0)
        self.assertEqual(gate["counts"]["failures"], 0)
        self.assertEqual(gate["counts"]["ncaa_contest_ids_created"], 0)
        self.assertEqual(gate["counts"]["pregame_availability_present"], 0)
        self.assertEqual(gate["counts"]["games_admitted_to_union"], 0)
        self.assertEqual(gate["counts"]["rich_structured_games"], 0)
        self.assertEqual(gate["counts"]["metadata_only_games"], 12)
        self.assertEqual(gate["counts"]["scoring_summary_present_games"], 12)
        self.assertEqual(gate["counts"]["matched_strong_tuple"], 11)
        self.assertEqual(gate["counts"]["date_conflicts"], 1)
        self.assertEqual(gate["counts"]["ambiguous_pages"], 1)
        self.assertEqual(gate["acquisition_identity"], "f5c0a2824381669501b7bccaeac18ced85f7c14b570d03e56ea4ebb1e4e08ee0")
        self.assertEqual(gate["dataset_identity"], "741f92a8b0d3c19fe7fd51033e9ddfb797052a9da4e63a2115839a4617e2c0c5")
        self.assertEqual(gate["games_identity"], "17a9daed972a0fa91e554b33adeaf5027aefa206188fec949a4450e2f8971772")
        self.assertEqual(gate["gate_identity"], "45329843f7b4683e18c231bbc5c835c7d0e488734d849ea18286d9b098291a13")
        self.assertEqual(gate["selected_seasons"], [2003])
        self.assertEqual(gate["upstream_identities"]["bat609_gate_identity"], PINNED_BAT609_GATE_IDENTITY)
        self.assertEqual(gate["upstream_identities"]["bat605_gate_identity"], PINNED_BAT605_GATE_IDENTITY)
        self.assertEqual(gate["upstream_identities"]["bat604_gate_identity"], PINNED_BAT604_GATE_IDENTITY)
        self.assertEqual(gate["upstream_identities"]["bat600_gate_identity"], PINNED_BAT600_GATE_IDENTITY)
        self.assertFalse(gate["authority"]["participation_as_availability"])
        self.assertFalse(gate["authority"]["availability_claim"])
        self.assertFalse(gate["authority"]["ncaa_contest_identity"])

    def test_acquisition_hash_tamper_fails(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        with self.assertRaisesRegex(AuthorityViolation, "reconstruction"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(gate, acquisition_identity="0" * 64),
                require_rebuild=True,
            )

    def test_membership_count_tamper_fails(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        counts = json.loads(json.dumps(gate["counts"]))
        counts["normalized_games"] = 13
        counts["metadata_only_games"] = 13
        with self.assertRaisesRegex(AuthorityViolation, "reconstruction"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(gate, counts=counts), require_rebuild=True)

    def test_ordering_identity_tamper_fails(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        with self.assertRaisesRegex(AuthorityViolation, "reconstruction"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(gate, games_identity="0" * 64),
                require_rebuild=True,
            )

    def test_richness_forged_fails(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        counts = json.loads(json.dumps(gate["counts"]))
        counts["rich_structured_games"] = int(counts.get("rich_structured_games") or 0) + 1
        counts["metadata_only_games"] = max(0, int(counts.get("metadata_only_games") or 0) - 1)
        with self.assertRaisesRegex(AuthorityViolation, "reconstruction"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(gate, counts=counts), require_rebuild=True)


if __name__ == "__main__":
    unittest.main()

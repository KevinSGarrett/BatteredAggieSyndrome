from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_2001_boxscores import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    INVENTORY_IDENTITY,
    OFFICIAL_2001_INDEX_URL,
    PINNED_BAT600_GATE_IDENTITY,
    PINNED_BAT604_GATE_IDENTITY,
    PINNED_BAT605_GATE_IDENTITY,
    PINNED_BAT613_GATE_IDENTITY,
    PINNED_BAT615_GATE_IDENTITY,
    PINNED_BAT621_BOX_URL_IDENTITY,
    PINNED_BAT621_GATE_IDENTITY,
    compute_code_identity,
    compute_gate_identity,
    compact_official_2001_capture,
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


DATA_ROOT = Path(
    os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
)
LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and lake_is_ready(DATA_ROOT)


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class Official2001AllowlistTests(unittest.TestCase):
    def test_source_index_is_the_reconstructed_bat621_allowlist(self) -> None:
        source = load_source_index(REPO_ROOT, DATA_ROOT)
        targets = selected_targets(source)
        self.assertEqual(source["official_index_url"], OFFICIAL_2001_INDEX_URL)
        self.assertEqual(
            source["inventory_gate"]["inventory_identity"], INVENTORY_IDENTITY
        )
        self.assertEqual(source["gate"]["gate_identity"], PINNED_BAT621_GATE_IDENTITY)
        self.assertEqual(
            source["gate"]["box_url_identity"], PINNED_BAT621_BOX_URL_IDENTITY
        )
        self.assertEqual(len(targets), len(source["box_score_urls"]))
        self.assertEqual(len(targets), 12)
        self.assertTrue(all(item["season"] == 2001 for item in targets))
        self.assertTrue(
            all(
                item["official_index_url"] == OFFICIAL_2001_INDEX_URL
                for item in targets
            )
        )
        bat613 = json.loads(
            (
                REPO_ROOT
                / "artifacts/data_lake/tamu_official_2002_season_index_gate.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(bat613["gate_identity"], PINNED_BAT613_GATE_IDENTITY)
        bat615 = json.loads(
            (
                REPO_ROOT / "artifacts/data_lake/tamu_official_2002_boxscore_gate.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(bat615["gate_identity"], PINNED_BAT615_GATE_IDENTITY)
        bat605 = json.loads(
            (
                REPO_ROOT / "artifacts/data_lake/tamu_official_2004_boxscore_gate.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(bat605["gate_identity"], PINNED_BAT605_GATE_IDENTITY)
        bat600 = json.loads(
            (
                REPO_ROOT / "artifacts/data_lake/tamu_official_2005_boxscore_gate.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(bat600["gate_identity"], PINNED_BAT600_GATE_IDENTITY)
        bat604 = json.loads(
            (
                REPO_ROOT
                / "artifacts/data_lake/tamu_official_2004_season_index_gate.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(bat604["gate_identity"], PINNED_BAT604_GATE_IDENTITY)
        allowed = {item["box_url"] for item in targets}
        self.assertNotIn(OFFICIAL_2001_INDEX_URL, allowed)
        self.assertNotIn(
            "https://files.12thman.com/history/football/years/2002.html", allowed
        )
        self.assertNotIn(
            "https://files.12thman.com/history/football/stats/2002-2003/ta01-la.html",
            allowed,
        )
        with self.assertRaisesRegex(Exception, "nonofficial host"):
            validate_official_url(
                "https://example.com/history/football/stats/2001-2002/guessed.htm"
            )

    def test_missing_response_sha_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "response SHA missing"):
            compact_official_2001_capture(
                {
                    "url": "https://files.12thman.com/history/football/stats/2001-2002/mfb_415_msu.html",
                    "raw_sha256": "a" * 64,
                    "parent_url": OFFICIAL_2001_INDEX_URL,
                    "timestamp": "2026-08-21T00:00:00Z",
                    "status": 200,
                    "content_type": "text/html",
                },
                source_order=1,
            )

    def test_response_file_sha_disagreement_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "disagree"):
            compact_official_2001_capture(
                {
                    "url": "https://files.12thman.com/history/football/stats/2001-2002/mfb_415_msu.html",
                    "raw_sha256": "a" * 64,
                    "response_sha256": "b" * 64,
                    "parent_url": OFFICIAL_2001_INDEX_URL,
                    "timestamp": "2026-08-21T00:00:00Z",
                    "status": 200,
                    "content_type": "text/html",
                },
                source_order=1,
            )


class Compact2001BoxscoreGateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("2001 boxscore gate not materialized yet")
        self.gate = json.loads(path.read_text(encoding="utf-8-sig"))

    def test_protected_lane_opened_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, protected_lane="OPEN"),
                require_rebuild=False,
            )

    def test_inventory_rewrite_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "inventory"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, inventory_identity="0" * 64),
                require_rebuild=False,
            )

    def test_availability_claim_fails(self) -> None:
        counts = json.loads(json.dumps(self.gate["counts"]))
        counts["pregame_availability_present"] = 1
        with self.assertRaisesRegex(AuthorityViolation, "availability"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, counts=counts),
                require_rebuild=False,
            )

    def test_retrieval_time_as_known_at_fails(self) -> None:
        authority = json.loads(json.dumps(self.gate["authority"]))
        authority["historical_known_at_from_capture_time"] = True
        with self.assertRaisesRegex(AuthorityViolation, "known-at"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, authority=authority),
                require_rebuild=False,
            )

    def test_bat600_rewrite_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat600_gate_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-600"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, upstream_identities=upstream),
                require_rebuild=False,
            )

    def test_bat604_rewrite_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat604_gate_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-604"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, upstream_identities=upstream),
                require_rebuild=False,
            )

    def test_bat621_rewrite_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat621_gate_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-621"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, upstream_identities=upstream),
                require_rebuild=False,
            )

    def test_bat615_rewrite_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat615_gate_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-615"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, upstream_identities=upstream),
                require_rebuild=False,
            )

    def test_bat613_rewrite_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat613_gate_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-613"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, upstream_identities=upstream),
                require_rebuild=False,
            )

    def test_stale_code_identity_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "stale code identity"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, validator_code_identity="0" * 64),
                require_rebuild=False,
            )

    def test_bat610_rewrite_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat610_gate_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-610"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, upstream_identities=upstream),
                require_rebuild=False,
            )

    def test_bat605_rewrite_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat605_gate_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-605"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, upstream_identities=upstream),
                require_rebuild=False,
            )

    def test_invented_ncaa_ids_fail(self) -> None:
        counts = json.loads(json.dumps(self.gate["counts"]))
        counts["ncaa_contest_ids_created"] = 1
        with self.assertRaisesRegex(AuthorityViolation, "NCAA"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, counts=counts),
                require_rebuild=False,
            )

    def test_forged_completion_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "completion"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(
                    self.gate,
                    result="FORGED_DONE",
                    classification="PRODUCTION_CHAMPION",
                ),
                require_rebuild=False,
            )

    def test_name_only_player_merge_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "name-only player merge"):
            shared_refuse_name_only_player_merge(
                [{"player_name": "A"}, {"player_name": "A"}]
            )

    def test_participation_is_not_availability(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "participation"):
            shared_availability_from_participation({"player_name": "A"})


@unittest.skipUnless(LAKE_READY, "external BAT-622 2001 captures are not mounted")
class Official2001AcquisitionTests(unittest.TestCase):
    def test_committed_gate_reconstructs(self) -> None:
        result = validate_artifact(
            repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True
        )
        self.assertEqual(result["result"], "PASS")
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        target_games = int(gate["counts"]["target_games_total"])
        self.assertEqual(target_games, 12)
        self.assertEqual(result["normalized_games"], target_games)
        self.assertEqual(gate["counts"]["expected_box_urls"], target_games)
        self.assertEqual(gate["counts"]["acquired_responses"], target_games)
        self.assertEqual(gate["counts"]["rejected_responses"], 0)
        self.assertEqual(gate["counts"]["failures"], 0)
        self.assertEqual(gate["counts"]["ncaa_contest_ids_created"], 0)
        self.assertEqual(gate["counts"]["pregame_availability_present"], 0)
        self.assertEqual(gate["counts"]["games_admitted_to_union"], 0)
        self.assertEqual(gate["counts"]["rich_structured_games"], 0)
        self.assertEqual(gate["counts"]["metadata_only_games"], 12)
        self.assertEqual(gate["counts"]["scoring_summary_present_games"], 12)
        self.assertEqual(gate["counts"]["matched_strong_tuple"], 12)
        self.assertEqual(gate["counts"]["unmatched_strong_tuple"], 0)
        self.assertEqual(gate["counts"]["date_conflicts"], 0)
        self.assertEqual(gate["counts"]["season_header_conflicts"], 0)
        self.assertEqual(gate["counts"]["ambiguous_pages"], 0)
        self.assertEqual(
            gate["acquisition_identity"],
            "26865dfd41b05af43883c5f27236cfb7bf62f25fe8f894d6ffde6dd9ad7b55eb",
        )
        self.assertEqual(
            gate["dataset_identity"],
            "289352b9ddee68d2a137542fbb622dffc76340fb33eb0693a794eb60030e194e",
        )
        self.assertEqual(
            gate["games_identity"],
            "baeffdc0fe09fa0d90438ceaf797515a02d683a9bc81bada702e7128b274d55b",
        )
        self.assertEqual(
            gate["gate_identity"],
            "127bea505729cece69c778255c9090486bb31ad66a014d382df134f027fcef8f",
        )
        self.assertEqual(
            gate["validator_code_identity"],
            "e192137de1da0a711f895e84234ca5a618086650e069ee380088da32800ebbf9",
        )
        self.assertEqual(gate["selected_seasons"], [2001])
        self.assertEqual(gate["jira_key"], "BAT-622")
        self.assertEqual(
            gate["validator_code_identity"], compute_code_identity(REPO_ROOT)
        )
        self.assertEqual(
            gate["upstream_identities"]["bat621_gate_identity"],
            PINNED_BAT621_GATE_IDENTITY,
        )
        self.assertEqual(
            gate["upstream_identities"]["bat615_gate_identity"],
            PINNED_BAT615_GATE_IDENTITY,
        )
        self.assertEqual(
            gate["upstream_identities"]["bat613_gate_identity"],
            PINNED_BAT613_GATE_IDENTITY,
        )
        self.assertEqual(
            gate["upstream_identities"]["bat610_gate_identity"],
            "45329843f7b4683e18c231bbc5c835c7d0e488734d849ea18286d9b098291a13",
        )
        self.assertEqual(
            gate["upstream_identities"]["bat605_gate_identity"],
            PINNED_BAT605_GATE_IDENTITY,
        )
        self.assertEqual(
            gate["upstream_identities"]["bat604_gate_identity"],
            PINNED_BAT604_GATE_IDENTITY,
        )
        self.assertEqual(
            gate["upstream_identities"]["bat600_gate_identity"],
            PINNED_BAT600_GATE_IDENTITY,
        )
        self.assertFalse(gate["authority"]["participation_as_availability"])
        self.assertFalse(gate["authority"]["availability_claim"])
        self.assertFalse(gate["authority"]["ncaa_contest_identity"])
        self.assertEqual(gate["acquisition_identity"], result["acquisition_identity"])
        self.assertEqual(gate["dataset_identity"], result["dataset_identity"])
        self.assertEqual(gate["gate_identity"], result["gate_identity"])
        matched = int(gate["counts"]["matched_strong_tuple"])
        unmatched = int(gate["counts"]["unmatched_strong_tuple"])
        date_conflicts = int(gate["counts"]["date_conflicts"])
        name_only = int(gate["counts"]["name_only_insufficient"])
        self.assertEqual(matched + unmatched + date_conflicts + name_only, target_games)

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
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(gate, counts=counts),
                require_rebuild=True,
            )

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
        counts["rich_structured_games"] = (
            int(counts.get("rich_structured_games") or 0) + 1
        )
        counts["metadata_only_games"] = max(
            0, int(counts.get("metadata_only_games") or 0) - 1
        )
        with self.assertRaisesRegex(AuthorityViolation, "reconstruction"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(gate, counts=counts),
                require_rebuild=True,
            )


if __name__ == "__main__":
    unittest.main()

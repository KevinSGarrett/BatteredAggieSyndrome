from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_2000_boxscores import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    INVENTORY_IDENTITY,
    OFFICIAL_2000_INDEX_URL,
    PINNED_BAT600_GATE_IDENTITY,
    PINNED_BAT604_GATE_IDENTITY,
    PINNED_BAT605_GATE_IDENTITY,
    PINNED_BAT613_GATE_IDENTITY,
    PINNED_BAT615_GATE_IDENTITY,
    PINNED_BAT625_BOX_URL_IDENTITY,
    PINNED_BAT625_GATE_IDENTITY,
    PINNED_BAT622_GATE_IDENTITY,
    compute_code_identity,
    compute_gate_identity,
    compact_official_2000_capture,
    lake_is_ready,
    load_source_index,
    rewrite_2000_numeric_identity_markup,
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
LAKE_READY = lake_is_ready(DATA_ROOT)


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class Official2000AllowlistTests(unittest.TestCase):
    def test_source_index_is_the_reconstructed_bat625_allowlist(self) -> None:
        source = load_source_index(REPO_ROOT, DATA_ROOT)
        targets = selected_targets(source)
        self.assertEqual(source["official_index_url"], OFFICIAL_2000_INDEX_URL)
        self.assertEqual(
            source["inventory_gate"]["inventory_identity"], INVENTORY_IDENTITY
        )
        self.assertEqual(source["gate"]["gate_identity"], PINNED_BAT625_GATE_IDENTITY)
        self.assertEqual(
            source["gate"]["box_url_identity"], PINNED_BAT625_BOX_URL_IDENTITY
        )
        self.assertEqual(len(targets), len(source["box_score_urls"]))
        self.assertEqual(len(targets), 12)
        self.assertTrue(all(item["season"] == 2000 for item in targets))
        self.assertTrue(
            all(
                item["official_index_url"] == OFFICIAL_2000_INDEX_URL
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
        bat622 = json.loads(
            (
                REPO_ROOT / "artifacts/data_lake/tamu_official_2001_boxscore_gate.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(bat622["gate_identity"], PINNED_BAT622_GATE_IDENTITY)
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
        self.assertNotIn(OFFICIAL_2000_INDEX_URL, allowed)
        self.assertNotIn(
            "https://files.12thman.com/history/football/years/2002.html", allowed
        )
        self.assertNotIn(
            "https://files.12thman.com/history/football/stats/2002-2003/ta01-la.html",
            allowed,
        )
        with self.assertRaisesRegex(Exception, "nonofficial host"):
            validate_official_url(
                "https://example.com/history/football/stats/2000-2001/guessed.htm"
            )

    def test_numeric_identity_dates_are_rewritten_without_inventing_urls(self) -> None:
        rewritten = rewrite_2000_numeric_identity_markup(
            "Texas A&amp;M vs Notre Dame (9/2/00 at Notre Dame, Ind.)\n"
            "Date: 9/2/00        Site: Notre Dame, Ind.",
            season=2000,
        )
        self.assertIn("Date: Sep. 2, 2000", rewritten)
        self.assertIn("(Sep. 2, 2000 at Notre Dame, Ind.)", rewritten)
        self.assertNotIn("9/2/00", rewritten)

    def test_missing_response_sha_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "response SHA missing"):
            compact_official_2000_capture(
                {
                    "url": "https://files.12thman.com/history/football/stats/2000-2000/mfb_415_msu.html",
                    "raw_sha256": "a" * 64,
                    "parent_url": OFFICIAL_2000_INDEX_URL,
                    "timestamp": "2026-08-21T00:00:00Z",
                    "status": 200,
                    "content_type": "text/html",
                },
                source_order=1,
            )

    def test_response_file_sha_disagreement_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "disagree"):
            compact_official_2000_capture(
                {
                    "url": "https://files.12thman.com/history/football/stats/2000-2000/mfb_415_msu.html",
                    "raw_sha256": "a" * 64,
                    "response_sha256": "b" * 64,
                    "parent_url": OFFICIAL_2000_INDEX_URL,
                    "timestamp": "2026-08-21T00:00:00Z",
                    "status": 200,
                    "content_type": "text/html",
                },
                source_order=1,
            )


class Compact2000BoxscoreGateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("2000 boxscore gate not materialized yet")
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

    def test_bat625_rewrite_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["bat625_gate_identity"] = "0" * 64
        with self.assertRaisesRegex(AuthorityViolation, "BAT-625"):
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


@unittest.skipUnless(LAKE_READY, "external BAT-626 2000 captures are not mounted")
class Official2000AcquisitionTests(unittest.TestCase):
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
        self.assertEqual(gate["counts"]["matched_strong_tuple"], 9)
        self.assertEqual(gate["counts"]["unmatched_strong_tuple"], 3)
        self.assertEqual(gate["counts"]["date_conflicts"], 0)
        self.assertEqual(gate["counts"]["season_header_conflicts"], 0)
        self.assertEqual(gate["counts"]["ambiguous_pages"], 0)
        self.assertEqual(
            gate["acquisition_identity"],
            "3a8092ce4c2fbf5ffc4b7af572f9a6ba8cdc360dec2cb538d55dbf7b3ed5f926",
        )
        self.assertEqual(
            gate["dataset_identity"],
            "5d37f54a95c6c3846aa392e2efc860bf2e3aeb6e1b3d02fee3d698c4473b733c",
        )
        self.assertEqual(
            gate["games_identity"],
            "e997834aaa8f32685f933e8a1e682cb86b57911405dafad84b5447221aaedf22",
        )
        self.assertEqual(
            gate["gate_identity"],
            "3f7dbc60a7d21359637d04597629a982180d7f97e4d479ad92134567ceec9f8a",
        )
        self.assertEqual(
            gate["validator_code_identity"],
            "833644fc015332971bb3374f2ef8b6a43d8b978f4558cbb4345457714a351255",
        )
        self.assertEqual(gate["selected_seasons"], [2000])
        self.assertEqual(gate["jira_key"], "BAT-626")
        self.assertEqual(
            gate["validator_code_identity"], compute_code_identity(REPO_ROOT)
        )
        self.assertEqual(
            gate["upstream_identities"]["bat625_gate_identity"],
            PINNED_BAT625_GATE_IDENTITY,
        )
        self.assertEqual(
            gate["upstream_identities"]["bat622_gate_identity"],
            PINNED_BAT622_GATE_IDENTITY,
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
        payload = json.loads(
            (
                DATA_ROOT
                / "features/tamu_official_2000_boxscores/sha256"
                / gate["dataset_identity"]
                / "payload.json"
            ).read_text(encoding="utf-8-sig")
        )
        unmatched_urls = {
            game["url"]
            for game in payload["games"]
            if game["canonical_game_match_status"] == "UNMATCHED_STRONG_TUPLE"
        }
        self.assertEqual(
            unmatched_urls,
            {
                "https://files.12thman.com/history/football/stats/2000-2001/mfb_426_nd.html",
                "https://files.12thman.com/history/football/stats/2000-2001/mfb_429_tech.html",
                "https://files.12thman.com/history/football/stats/2000-2001/mfb_432_isu.html",
            },
        )
        notre_dame = next(
            game for game in payload["games"] if game["url"].endswith("mfb_426_nd.html")
        )
        self.assertEqual(
            notre_dame["identity_date_format"], "NUMERIC_MDY_TWO_DIGIT_YEAR"
        )
        self.assertEqual(notre_dame["raw_date"], "9/2/00")
        self.assertEqual(notre_dame["calendar_date"], "2000-09-02")
        self.assertEqual(
            notre_dame["source_sha256"],
            "e91c31f506538a05523bc6f3a7275a9d539c6a4c47ba2324b13793fde9de59a4",
        )
        self.assertEqual(gate["counts"]["games_admitted_to_union"], 0)

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

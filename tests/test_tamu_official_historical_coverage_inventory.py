from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_historical_coverage_inventory import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    compute_gate_identity,
    lake_is_ready,
    reconstruct_inventory,
    validate_artifact,
)


DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = lake_is_ready(DATA_ROOT)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class CompactInventoryGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8"))

    def test_committed_gate_identity_recomputes(self) -> None:
        result = validate_artifact(
            repo_root=REPO_ROOT,
            data_root=DATA_ROOT if LAKE_READY else REPO_ROOT,
            require_rebuild=LAKE_READY,
        )
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["gate_identity"], "f1a5821ad081dce7058848ccc453344f0a2827030959049133b69db15689c851")
        self.assertEqual(result["selected_seasons"], [2009, 2008])

    def test_protected_lane_opened_fails_without_lake(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT if LAKE_READY else REPO_ROOT,
                gate=_mutated(self.gate, protected_lane="OPEN"),
                require_rebuild=False,
            )


@unittest.skipUnless(LAKE_READY, "external BAT-585 inventory payloads are not mounted")
class OfficialCoverageInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = REPO_ROOT
        cls.data_root = DATA_ROOT
        cls.objects = reconstruct_inventory(repo_root=cls.repo_root, data_root=cls.data_root)
        cls.gate = cls.objects["gate"]
        cls.payload = cls.objects["payload"]

    def test_selects_2008_and_2009_from_official_index(self) -> None:
        self.assertEqual(self.gate["selected_seasons"], [2009, 2008])
        selected = {row["season"]: row for row in self.payload["selected_seasons"]}
        self.assertEqual(selected[2009]["official_index_url"], "https://files.12thman.com/history/football/years/2009.html")
        self.assertEqual(selected[2008]["official_index_url"], "https://files.12thman.com/history/football/years/2008.html")
        self.assertEqual(selected[2009]["box_score_link_count"], 13)
        self.assertEqual(selected[2008]["box_score_link_count"], 12)

    def test_does_not_guess_year_urls(self) -> None:
        by_season = {row["season"]: row for row in self.payload["seasons"]}
        self.assertEqual(
            by_season[2018]["official_index_url"],
            "https://files.12thman.com/history/football/history/2018.html",
        )
        self.assertNotEqual(
            by_season[2018]["official_index_url"],
            "https://files.12thman.com/history/football/years/2018.html",
        )

    def test_union_seasons_are_not_selected(self) -> None:
        by_season = {row["season"]: row for row in self.payload["seasons"]}
        self.assertGreater(by_season[2010]["union_game_count"], 0)
        self.assertGreater(by_season[2012]["wmt_game_count"], 0)
        self.assertNotIn(2010, self.gate["selected_seasons"])
        self.assertNotIn(2012, self.gate["selected_seasons"])

    def test_historical_known_at_unresolved(self) -> None:
        self.assertFalse(self.gate["authority"]["historical_known_at_from_capture_time"])
        self.assertTrue(all(row["historical_publication_time"] is None for row in self.payload["seasons"]))

    def test_validate_pass(self) -> None:
        result = validate_artifact(repo_root=self.repo_root, data_root=self.data_root)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["selected_seasons"], [2009, 2008])

    def test_invented_season_fails(self) -> None:
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=self.repo_root,
                data_root=self.data_root,
                gate=_mutated(self.gate, selected_seasons=[2009, 1894]),
            )

    def test_changed_ordering_fails(self) -> None:
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                repo_root=self.repo_root,
                data_root=self.data_root,
                gate=_mutated(self.gate, selected_seasons=[2008, 2009]),
            )

    def test_protected_lane_opened_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(
                repo_root=self.repo_root,
                data_root=self.data_root,
                gate=_mutated(self.gate, protected_lane="OPEN"),
            )

    def test_known_at_forged_fails(self) -> None:
        authority = json.loads(json.dumps(self.gate["authority"]))
        authority["historical_known_at_from_capture_time"] = True
        with self.assertRaisesRegex(AuthorityViolation, "historical known-at"):
            validate_artifact(
                repo_root=self.repo_root,
                data_root=self.data_root,
                gate=_mutated(self.gate, authority=authority),
            )

    def test_forged_completion_after_rehash_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "completion"):
            validate_artifact(
                repo_root=self.repo_root,
                data_root=self.data_root,
                gate=_mutated(self.gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION"),
            )

    def test_validator_does_not_write(self) -> None:
        watched = [
            self.repo_root / GATE_RELATIVE,
            self.data_root
            / "features/tamu_official_historical_coverage_inventory/sha256"
            / self.gate["inventory_identity"]
            / "inventory.json",
            self.data_root / "features/tamu_official_historical_coverage_inventory/season_index_capture_index.json",
            self.data_root
            / "raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive/season_index"
            / "sha256_e343e869a25bedbd9f2ca9e3133f2e09205c612e7f3a19ee638d376547586088.html",
            self.data_root
            / "raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive/season_index"
            / "sha256_f6a5518dceb68098573044dd10c95b39d569f34dd8fb099a1332fcaf99ee2543.html",
        ]
        before = {str(path): _sha256(path) for path in watched if path.is_file()}
        validate_artifact(repo_root=self.repo_root, data_root=self.data_root)
        after = {str(path): _sha256(path) for path in watched if path.is_file()}
        self.assertEqual(before, after)


@unittest.skipUnless(LAKE_READY, "external BAT-585 inventory payloads are not mounted")
class InventoryPayloadMutationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = REPO_ROOT
        self.data_root = DATA_ROOT
        self.objects = reconstruct_inventory(repo_root=self.repo_root, data_root=self.data_root)
        self.payload_path = (
            self.data_root
            / "features/tamu_official_historical_coverage_inventory/sha256"
            / self.objects["gate"]["inventory_identity"]
            / "inventory.json"
        )
        self.original = self.payload_path.read_bytes()

    def tearDown(self) -> None:
        self.payload_path.write_bytes(self.original)

    def _tamper(self, mutator) -> None:
        payload = json.loads(self.original)
        mutator(payload)
        self.payload_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def test_third_party_discovery_url_fails(self) -> None:
        def mutate(payload: dict) -> None:
            payload["seasons"][0]["official_index_url"] = "https://example.com/guessed/2023"
            payload["seasons"][0]["official_host"] = "example.com"

        self._tamper(mutate)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=self.repo_root, data_root=self.data_root)

    def test_guessed_year_url_fails(self) -> None:
        def mutate(payload: dict) -> None:
            for row in payload["seasons"]:
                if row["season"] == 2018:
                    row["official_index_url"] = "https://files.12thman.com/history/football/years/2018.html"

        self._tamper(mutate)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=self.repo_root, data_root=self.data_root)

    def test_union_season_falsely_missing_fails(self) -> None:
        def mutate(payload: dict) -> None:
            for row in payload["seasons"]:
                if row["season"] == 2010:
                    row["union_game_count"] = 0

        self._tamper(mutate)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=self.repo_root, data_root=self.data_root)

    def test_missing_official_discovery_provenance_fails(self) -> None:
        def mutate(payload: dict) -> None:
            payload["seasons"][0]["discovery_source_url"] = "https://example.net/third-party"

        self._tamper(mutate)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(repo_root=self.repo_root, data_root=self.data_root)


if __name__ == "__main__":
    unittest.main()

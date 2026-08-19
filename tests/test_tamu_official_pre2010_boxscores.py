from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_pre2010_boxscores import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    INVENTORY_IDENTITY,
    compute_gate_identity,
    lake_is_ready,
    reconstruct_objects,
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


class CompactPre2010BoxscoreTests(unittest.TestCase):
    def test_committed_gate_identity_recomputes(self) -> None:
        result = validate_artifact(
            repo_root=REPO_ROOT,
            data_root=DATA_ROOT if LAKE_READY else REPO_ROOT,
            require_rebuild=LAKE_READY,
        )
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["gate_identity"], "b98d712cd0e9c6bd3f685de8a8c6305a7fc9bf2f24a02ede4f47d27a3cefa8fa")
        self.assertEqual(result["selected_seasons"], [2009, 2008])


@unittest.skipUnless(LAKE_READY, "external BAT-586 payloads are not mounted")
class Pre2010BoxscoreLakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.objects = reconstruct_objects(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        cls.gate = cls.objects["gate"]

    def test_normalizes_inventory_seasons_only(self) -> None:
        self.assertEqual(self.gate["inventory_identity"], INVENTORY_IDENTITY)
        self.assertEqual(self.gate["counts"]["normalized_games"], 25)
        self.assertEqual(self.gate["counts"]["normalized_games_2009"], 13)
        self.assertEqual(self.gate["counts"]["normalized_games_2008"], 12)
        self.assertEqual(self.gate["counts"]["ncaa_contest_ids_created"], 0)
        self.assertEqual(self.gate["counts"]["date_conflicts"], 2)
        self.assertEqual(self.gate["counts"]["matched_strong_tuple"], 21)

    def test_preserves_conflicts_and_missing_domains(self) -> None:
        self.assertEqual(self.gate["domain_coverage"]["play_by_play"]["present_games"], 0)
        self.assertEqual(self.gate["domain_coverage"]["scores"]["present_games"], 25)
        conflicts = self.objects["payload"]["conflicts"]
        self.assertTrue(any(item["opponent_candidate"] == "Baylor" for item in conflicts))
        self.assertTrue(any(item["opponent_candidate"] == "Texas" for item in conflicts))

    def test_validator_does_not_write(self) -> None:
        watched = [
            REPO_ROOT / GATE_RELATIVE,
            DATA_ROOT / "features/tamu_official_pre2010_boxscores/capture_index.json",
            DATA_ROOT
            / "features/tamu_official_pre2010_boxscores/sha256"
            / self.gate["dataset_identity"]
            / "payload.json",
            DATA_ROOT
            / "raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive/box_scores"
            / "sha256_5ccbb856d14bdbcaeb25b6e47c3d04fdbb609a63fff4299d5b641923d8f1ebdc.html",
        ]
        before = {str(path): _sha256(path) for path in watched if path.is_file()}
        validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        after = {str(path): _sha256(path) for path in watched if path.is_file()}
        self.assertEqual(before, after)

    def test_protected_and_forged_completion_fail(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=_mutated(self.gate, protected_lane="OPEN"))
        with self.assertRaisesRegex(AuthorityViolation, "completion"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION"),
            )


if __name__ == "__main__":
    unittest.main()

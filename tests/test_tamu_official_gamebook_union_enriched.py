from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_gamebook_union_enriched import (  # noqa: E402
    AuthorityViolation,
    CYCLE9_UNION_IDENTITY,
    GATE_RELATIVE,
    PRIOR_226_UNION_IDENTITY,
    PRIOR_237_UNION_IDENTITY,
    STATCREW_PAYLOAD_IDENTITY,
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


class CompactEnrichedUnionTests(unittest.TestCase):
    def test_committed_gate_identity_recomputes(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("enriched-union gate not materialized yet")
        result = validate_artifact(
            repo_root=REPO_ROOT,
            data_root=DATA_ROOT if LAKE_READY else REPO_ROOT,
            require_rebuild=LAKE_READY,
        )
        self.assertEqual(result["result"], "PASS")
        gate = json.loads(path.read_text(encoding="utf-8-sig"))
        self.assertEqual(result["gate_identity"], gate["gate_identity"])
        self.assertEqual(result["union_identity"], gate["union_identity"])


@unittest.skipUnless(LAKE_READY, "external BAT-591/BAT-590 payloads are not mounted")
class EnrichedUnionLakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.objects = reconstruct_objects(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        cls.gate = cls.objects["gate"]

    def test_preserves_prior_identities_and_does_not_admit_rejects(self) -> None:
        self.assertEqual(self.gate["prior_union_identity"], PRIOR_237_UNION_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat587_union_identity"], PRIOR_226_UNION_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["cycle9_union_identity"], CYCLE9_UNION_IDENTITY)
        self.assertEqual(self.gate["upstream_identities"]["bat591_payload_identity"], STATCREW_PAYLOAD_IDENTITY)
        self.assertEqual(self.gate["counts"]["wmt_games_preserved"], 177)
        self.assertEqual(self.gate["counts"]["cycle9_union_games_preserved"], 203)
        self.assertEqual(self.gate["counts"]["prior_226_union_games_preserved"], 226)
        self.assertEqual(self.gate["counts"]["prior_237_union_games_preserved"], 237)
        self.assertEqual(self.gate["counts"]["new_games_added"], 0)
        self.assertEqual(self.gate["counts"]["overlays_applied"], 34)
        self.assertEqual(self.gate["counts"]["overlays_became_rich"], 33)
        self.assertEqual(self.gate["counts"]["union_captured_games"], 237)
        self.assertEqual(self.gate["counts"]["rich_structured_games"], 224)
        self.assertEqual(self.gate["counts"]["metadata_only_games"], 13)
        self.assertEqual(self.gate["counts"]["unmatched_rejected"], 4)
        self.assertEqual(self.gate["counts"]["ncaa_contest_ids_created"], 0)
        rejected = {item["url"] for item in self.gate["preserved_rejections"]}
        admitted = {item["url"] for item in self.gate["enriched_official_games"]}
        self.assertTrue(rejected.isdisjoint(admitted))
        self.assertIn("https://files.12thman.com/history/football/stats/2007-2008/mfb_148_ta04-mia.html", rejected)
        self.assertIn("https://files.12thman.com/history/football/stats/2007-2008/mfb_2158_ta10-ou.html", rejected)

    def test_validator_does_not_write(self) -> None:
        watched = [
            REPO_ROOT / GATE_RELATIVE,
            REPO_ROOT / "artifacts/data_lake/tamu_official_gamebook_union_2007_gate.json",
            DATA_ROOT
            / "features/tamu_official_statcrew_preformatted/sha256"
            / STATCREW_PAYLOAD_IDENTITY
            / "payload.json",
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
        with self.assertRaisesRegex(AuthorityViolation, "237-game union"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, prior_union_identity="0" * 64),
            )


if __name__ == "__main__":
    unittest.main()

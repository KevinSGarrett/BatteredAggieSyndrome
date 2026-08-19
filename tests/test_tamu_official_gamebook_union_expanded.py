from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_gamebook_union_expanded import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    PRIOR_UNION_IDENTITY,
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


class CompactExpandedUnionTests(unittest.TestCase):
    def test_committed_gate_identity_recomputes(self) -> None:
        result = validate_artifact(
            repo_root=REPO_ROOT,
            data_root=DATA_ROOT if LAKE_READY else REPO_ROOT,
            require_rebuild=LAKE_READY,
        )
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["gate_identity"], "77043db845ea4089e7530509b29489c3b76455e6db7eaea299854f316b6febe9")
        self.assertEqual(result["union_identity"], "a5444d7c80baeb25751c8cac2338e86c5ac8746398bd94e61e1c43cb83916f4e")


@unittest.skipUnless(LAKE_READY, "external BAT-586/BAT-587 payloads are not mounted")
class ExpandedUnionLakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.objects = reconstruct_objects(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        cls.gate = cls.objects["gate"]

    def test_preserves_prior_identities_and_admits_matched_only(self) -> None:
        self.assertEqual(self.gate["prior_union_identity"], PRIOR_UNION_IDENTITY)
        self.assertEqual(self.gate["counts"]["wmt_games_preserved"], 177)
        self.assertEqual(self.gate["counts"]["cycle9_official_games_preserved"], 26)
        self.assertEqual(self.gate["counts"]["new_games_added"], 23)
        self.assertEqual(self.gate["counts"]["unmatched_rejected"], 2)
        self.assertEqual(self.gate["counts"]["union_captured_games"], 226)
        self.assertEqual(self.gate["counts"]["rich_structured_games"], 190)
        self.assertEqual(self.gate["counts"]["metadata_only_games"], 36)
        self.assertEqual(self.gate["counts"]["ncaa_contest_ids_created"], 0)
        rejected = {item["opponent_candidate"] for item in self.gate["rejected_pre2010_games"]}
        self.assertEqual(rejected, {"Georgia", "Miami"})

    def test_validator_does_not_write(self) -> None:
        watched = [
            REPO_ROOT / GATE_RELATIVE,
            REPO_ROOT / "artifacts/data_lake/tamu_official_gamebook_union_gate.json",
            DATA_ROOT
            / "features/tamu_official_pre2010_boxscores/sha256"
            / "1858893908f59afc8f6e88fea46764666869d7c809ddf2b3fedbdfcea02b6b59"
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


if __name__ == "__main__":
    unittest.main()

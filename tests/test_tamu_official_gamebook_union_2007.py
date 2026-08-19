from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_gamebook_union_2007 import (  # noqa: E402
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


class CompactOfficial2007UnionTests(unittest.TestCase):
    def test_committed_gate_identity_recomputes(self) -> None:
        result = validate_artifact(
            repo_root=REPO_ROOT,
            data_root=DATA_ROOT if LAKE_READY else REPO_ROOT,
            require_rebuild=LAKE_READY,
        )
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["gate_identity"], "df9cbb5588743881520c986b6b667096596fcf3391b4b7eed0ef02aef326408f")
        self.assertEqual(result["union_identity"], "d7f9ece5a5a79e190dd845bcd04e0d648469486b9f702c943feeb101898c2e31")


@unittest.skipUnless(LAKE_READY, "external BAT-589/BAT-587 payloads are not mounted")
class Official2007UnionLakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.objects = reconstruct_objects(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        cls.gate = cls.objects["gate"]

    def test_preserves_prior_identities_and_admits_matched_only(self) -> None:
        self.assertEqual(self.gate["prior_union_identity"], PRIOR_UNION_IDENTITY)
        self.assertEqual(self.gate["counts"]["wmt_games_preserved"], 177)
        self.assertEqual(self.gate["counts"]["cycle9_official_games_preserved"], 26)
        self.assertEqual(self.gate["counts"]["new_games_added"], 11)
        self.assertEqual(self.gate["counts"]["unmatched_rejected"] + self.gate["counts"]["new_games_added"], 13)
        self.assertEqual(self.gate["counts"]["union_captured_games"], 226 + self.gate["counts"]["new_games_added"])
        self.assertEqual(self.gate["counts"]["ncaa_contest_ids_created"], 0)
        rejected = {item["opponent_candidate"] for item in self.gate["rejected_official_2007_games"]}
        self.assertEqual(rejected, {"Miami Fla", "Oklahoma"})

    def test_validator_does_not_write(self) -> None:
        watched = [
            REPO_ROOT / GATE_RELATIVE,
            REPO_ROOT / "artifacts/data_lake/tamu_official_gamebook_union_gate.json",
            DATA_ROOT
            / "features/tamu_official_2007_boxscores/sha256"
            / "8681c15f48e1335e3e56bca7f146af4dc9c7ce731d077b2923d977e429a8b0c0"
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

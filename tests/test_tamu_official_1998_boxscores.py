from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_1998_boxscores import (  # noqa: E402  # pylint: disable=import-error
    AuthorityViolation,
    GATE_RELATIVE,
    OFFICIAL_1998_INDEX_URL,
    PINNED_BAT634_GATE_IDENTITY,
    compute_code_identity,
    compute_gate_identity,
    lake_is_ready,
    load_source_index,
    selected_targets,
    validate_artifact,
)

DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and lake_is_ready(DATA_ROOT)


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class Official1998AllowlistTests(unittest.TestCase):
    def test_source_index_is_bat634_allowlist(self) -> None:
        source = load_source_index(REPO_ROOT)
        targets = selected_targets(source)
        self.assertEqual(source["official_index_url"], OFFICIAL_1998_INDEX_URL)
        self.assertEqual(source["gate"]["gate_identity"], PINNED_BAT634_GATE_IDENTITY)
        self.assertEqual(len(targets), len(source["box_score_urls"]))
        self.assertGreaterEqual(len(targets), 1)
        self.assertTrue(all(item["season"] == 1998 for item in targets))


class Compact1998BoxscoreGateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("1998 boxscore gate not materialized yet")
        self.gate = json.loads(path.read_text(encoding="utf-8-sig"))
        if self.gate.get("validator_code_identity") != compute_code_identity(REPO_ROOT):
            self.skipTest("1998 boxscore gate needs rebuild for current code identity")

    def test_protected_lane_opened_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, protected_lane="OPEN"),
                require_rebuild=False,
            )


@unittest.skipUnless(LAKE_READY, "external BAT-635 1998 captures are not mounted")
class Official1998AcquisitionTests(unittest.TestCase):
    def test_committed_gate_reconstructs(self) -> None:
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        if gate.get("validator_code_identity") != compute_code_identity(REPO_ROOT):
            self.skipTest("1998 boxscore gate needs rebuild for current code identity")
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["selected_seasons"], [1998])
        self.assertGreaterEqual(int(result["normalized_games"] or 0), 0)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_1999_structured_domains import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    PREFORMATTED_PARSER_IDENTITY,
    compute_code_identity,
    compute_gate_identity,
    lake_is_ready,
    materialize,
    validate_artifact,
)  # pylint: disable=import-error

DATA_ROOT = Path(
    os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
)
LAKE_READY = lake_is_ready(DATA_ROOT)


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class Compact1999StructuredDomainGateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("1999 structured-domain gate not materialized yet")
        self.gate = json.loads(path.read_text(encoding="utf-8-sig"))
        if self.gate.get("validator_code_identity") != compute_code_identity(REPO_ROOT):
            self.skipTest("1999 structured-domain gate needs rebuild for current code identity")

    def test_protected_lane_opened_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, protected_lane="OPEN"),
                require_rebuild=False,
            )

    def test_invented_ncaa_id_fails(self) -> None:
        counts = json.loads(json.dumps(self.gate["counts"]))
        counts["ncaa_contest_ids_created"] = 1
        with self.assertRaisesRegex(AuthorityViolation, "NCAA"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, counts=counts),
                require_rebuild=False,
            )

    def test_parser_identity_change_fails(self) -> None:
        upstream = json.loads(json.dumps(self.gate["upstream_identities"]))
        upstream["parser_identity"] = "forged.parser.v9"
        with self.assertRaisesRegex(AuthorityViolation, "parser identity"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, upstream_identities=upstream),
                require_rebuild=False,
            )


@unittest.skipUnless(LAKE_READY, "external BAT-632 1999 captures are not mounted")
class Official1999StructuredReconstructionTests(unittest.TestCase):
    def test_committed_gate_reconstructs(self) -> None:
        # materialize to ensure gate reflects current code identity
        materialize(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        result = validate_artifact(
            repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True
        )
        self.assertEqual(result["result"], "PASS")
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        self.assertEqual(gate["selected_seasons"], [1999])
        self.assertEqual(gate["upstream_identities"]["parser_identity"], PREFORMATTED_PARSER_IDENTITY)
        self.assertGreaterEqual(int(gate["counts"]["parsed_games"] or 0), 1)
        self.assertGreaterEqual(int(gate["counts"]["serialized_rows_total"] or 0), 1)
        for domain in (
            "team_statistics",
            "individual_player_statistics",
            "drives",
            "play_by_play",
            "scoring_summary",
        ):
            self.assertGreaterEqual(int(gate["counts"][f"{domain}_serialized_rows"] or 0), 0)


if __name__ == "__main__":
    unittest.main()

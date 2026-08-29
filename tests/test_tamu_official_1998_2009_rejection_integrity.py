from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_1998_2009_rejection_integrity import (  # noqa: E402  # pylint: disable=import-error
    ADMITTED_ROW_GAP_URLS,
    CONTRACT_RELATIVE,
    AuthorityViolation,
    GATE_RELATIVE,
    compute_identity,
    load_json,
    reconstruct_objects,
    supersession_material_merge_sha,
    validate_artifact,
)

DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and DATA_ROOT.exists()


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_identity(tampered, "gate_identity")
    return tampered


@unittest.skipUnless(LAKE_READY, "external Cycle #18 data root is not mounted")
class RejectionIntegrityGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Reconstruction only. Materialization stays in the explicit build command
        # so a test run can never rewrite the tracked gate it is checking.
        reconstruct_objects(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        cls.gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))

    def test_gate_reconstructs(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(int(self.gate["complete_rejection_count"]), 40)
        self.assertEqual(int(self.gate["active_rejection_count"]), 17)
        self.assertEqual(int(self.gate["superseded_rejection_count"]), 23)

    def test_protected_lane_open_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "does not match independent reconstruction"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, protected_lane="OPEN"),
            )

    def test_gap_url_relabel_fails(self) -> None:
        bad = _mutated(self.gate, admitted_row_gap_urls=[ADMITTED_ROW_GAP_URLS[0]])
        with self.assertRaisesRegex(AuthorityViolation, "does not match independent reconstruction"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=bad)

    def test_supersession_merge_sha_is_precommitted_not_sampled_from_the_checkout(self) -> None:
        contract = load_json(REPO_ROOT / CONTRACT_RELATIVE)
        declared = supersession_material_merge_sha(contract)
        objects = reconstruct_objects(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        supersessions = objects["payload"]["supersessions"]
        self.assertTrue(supersessions)
        self.assertEqual({row["material_merge_sha"] for row in supersessions}, {declared})

    def test_missing_or_malformed_contract_merge_sha_fails_closed(self) -> None:
        contract = load_json(REPO_ROOT / CONTRACT_RELATIVE)
        uppercased = contract["supersession_material_merge_sha"].upper()
        bad_values = (None, "", "not-a-sha", uppercased, "43a1cc5d", 43)
        for bad_value in bad_values:
            with self.subTest(value=bad_value):
                tampered = dict(contract)
                if bad_value is None:
                    tampered.pop("supersession_material_merge_sha")
                else:
                    tampered["supersession_material_merge_sha"] = bad_value
                with self.assertRaisesRegex(AuthorityViolation, "40-character lowercase hex"):
                    supersession_material_merge_sha(tampered)

    def test_stripped_authority_label_fails_closed(self) -> None:
        contract = load_json(REPO_ROOT / CONTRACT_RELATIVE)
        tampered = dict(contract)
        tampered["supersession_material_merge_sha_authority"] = "SAMPLED_FROM_GIT_HEAD"
        with self.assertRaisesRegex(AuthorityViolation, "authority label missing or altered"):
            supersession_material_merge_sha(tampered)
        tampered.pop("supersession_material_merge_sha_authority")
        with self.assertRaisesRegex(AuthorityViolation, "authority label missing or altered"):
            supersession_material_merge_sha(tampered)

    def test_reconstruction_does_not_read_the_working_checkout_commit(self) -> None:
        """The reproduced ledger identity must not depend on which commit is checked out."""
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
        objects = reconstruct_objects(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        shas = {row["material_merge_sha"] for row in objects["payload"]["supersessions"]}
        self.assertNotIn(head, shas, "reconstruction leaked the checked-out commit into the ledger")
        self.assertEqual(objects["payload"]["ledger_identity"], self.gate["ledger_identity"])
        self.assertEqual(objects["payload"]["gate_identity"], self.gate["gate_identity"])


if __name__ == "__main__":
    unittest.main()

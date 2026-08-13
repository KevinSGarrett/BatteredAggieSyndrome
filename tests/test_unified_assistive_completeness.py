from __future__ import annotations

import unittest
import hashlib
import json
import tempfile
from pathlib import Path

from tools.validate_unified_assistive_completeness import current_inventory, validate_claims


class UnifiedAssistiveCompletenessTests(unittest.TestCase):
    def test_honest_claims_pass(self) -> None:
        states = {"cursor": "PAID_PILOT_AUTHORIZED_ZERO_REAL_AGENTS"}
        claims = {
            "claims": dict(states),
            "fully_operational_claimed": False,
            "sustained_operation_claimed": False,
        }
        self.assertEqual(validate_claims(claims, states), [])

    def test_configuration_cannot_be_called_operational(self) -> None:
        states = {"openrouter": "PAID_PILOT_AUTHORIZED_NOT_EXECUTED"}
        claims = {
            "claims": {"openrouter": "OPERATIONAL"},
            "fully_operational_claimed": True,
            "sustained_operation_claimed": True,
        }
        findings = validate_claims(claims, states)
        self.assertIn("CLAIM_EXCEEDS_OR_CONFLICTS_WITH_EVIDENCE:openrouter", findings)
        self.assertIn("FULL_OPERATIONAL_CLAIM_PREMATURE", findings)
        self.assertIn("SUSTAINED_OPERATION_CLAIM_PREMATURE", findings)

    def test_current_inventory_dereferences_content_addressed_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = root / "snapshot.json"
            payload = {"artifact_type": "UNIFIED_ASSISTIVE_RUNTIME_INVENTORY", "mandatory_acceptance_rows": 204}
            data = json.dumps(payload, sort_keys=True).encode("utf-8")
            snapshot.write_bytes(data)
            pointer = root / "inventory.json"
            pointer.write_text(
                json.dumps(
                    {
                        "artifact_type": "UNIFIED_ASSISTIVE_INVENTORY_POINTER",
                        "snapshot_path": str(snapshot),
                        "snapshot_sha256": hashlib.sha256(data).hexdigest(),
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(payload, current_inventory(pointer))

    def test_current_inventory_rejects_pointer_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = root / "snapshot.json"
            snapshot.write_text("{}", encoding="utf-8")
            pointer = root / "inventory.json"
            pointer.write_text(
                json.dumps(
                    {
                        "artifact_type": "UNIFIED_ASSISTIVE_INVENTORY_POINTER",
                        "snapshot_path": str(snapshot),
                        "snapshot_sha256": "0" * 64,
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "COMPLETENESS_INVENTORY_POINTER_HASH_MISMATCH"):
                current_inventory(pointer)


if __name__ == "__main__":
    unittest.main()

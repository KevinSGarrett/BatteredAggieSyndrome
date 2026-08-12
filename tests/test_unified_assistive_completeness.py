from __future__ import annotations

import unittest

from tools.validate_unified_assistive_completeness import validate_claims


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


if __name__ == "__main__":
    unittest.main()

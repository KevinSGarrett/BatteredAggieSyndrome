from __future__ import annotations

import json
from pathlib import Path
import unittest

from aggie_analytics.data.ncaa_contest_reconciliation_expansion import build_resolved_contract


ROOT = Path(__file__).resolve().parents[1]


class NcaaContestReconciliationExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = json.loads((ROOT / "configs/ncaa_contest_reconciliation_contract.json").read_text(encoding="utf-8"))
        cls.policy = json.loads((ROOT / "configs/ncaa_contest_reconciliation_expansion_policy.json").read_text(encoding="utf-8"))

    def test_resolved_contract_is_season_scoped_and_candidate_only(self) -> None:
        resolved = build_resolved_contract(
            base_contract=self.base,
            policy=self.policy,
            season=2020,
            discovery_relative_path="manifests/discovery.json",
            discovery_sha256="a" * 64,
            discovery_identity="b" * 64,
            wrapper_identities={"policy_sha256": "c" * 64},
        )
        self.assertEqual(resolved["source_contract"]["season"], 2020)
        self.assertEqual(resolved["source_contract"]["outcome_targets"], self.policy["outcome_adapter"]["payload"])
        self.assertFalse(resolved["authority"]["historical_pit_eligible"])
        self.assertFalse(resolved["authority"]["training_eligible"])
        self.assertFalse(resolved["authority"]["protected_evaluation_eligible"])
        self.assertFalse(resolved["authority"]["production_eligible"])

    def test_out_of_policy_season_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            build_resolved_contract(
                base_contract=self.base,
                policy=self.policy,
                season=2009,
                discovery_relative_path="x",
                discovery_sha256="a" * 64,
                discovery_identity="b" * 64,
                wrapper_identities={},
            )


if __name__ == "__main__":
    unittest.main()

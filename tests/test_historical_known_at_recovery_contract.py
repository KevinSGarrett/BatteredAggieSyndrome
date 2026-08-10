import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HistoricalKnownAtRecoveryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(
            (ROOT / "configs" / "historical_known_at_recovery_contract.json").read_text(encoding="utf-8")
        )
        cls.registry = json.loads(
            (ROOT / "jira" / "reconciliation" / "BAT_AUXILIARY_ISSUE_REGISTRY.json").read_text(
                encoding="utf-8"
            )
        )
        cls.evidence = json.loads(
            (
                ROOT
                / "artifacts"
                / "jira_evidence"
                / "POST-TASK-HISTORICAL-KNOWN-AT-RECOVERY-001.json"
            ).read_text(encoding="utf-8")
        )

    def test_live_unit_identity_and_dependency_are_registered(self) -> None:
        item = next(row for row in self.registry["issues"] if row["jira_key"] == "BAT-523")
        self.assertEqual(item["local_id"], "POST-TASK-HISTORICAL-KNOWN-AT-RECOVERY-001")
        self.assertEqual(item["status"], "In Progress")
        self.assertTrue(item["critical_path"])
        self.assertEqual(self.contract["dependency_contract"]["blocks"], ["BAT-399"])
        self.assertEqual(self.contract["dependency_contract"]["relates_to"], ["BAT-398"])

    def test_recovery_cannot_fabricate_historical_knowledge_time(self) -> None:
        prohibited = set(self.contract["prohibited_substitutions"])
        self.assertIn("retrieval_time_as_historical_known_at", prohibited)
        self.assertIn("model_generated_timestamp", prohibited)
        self.assertFalse(self.evidence["contract"]["fabricated_known_at_permitted"])

    def test_domain_eligibility_is_independent_and_tiered(self) -> None:
        dimensions = set(self.contract["eligibility_dimensions"])
        self.assertIn("domain_and_data_grain", dimensions)
        self.assertIn("historical_known_at_and_point_in_time_eligibility", dimensions)
        self.assertGreaterEqual(len(self.contract["domain_tiers"]), 4)
        self.assertIn("Partial or failed domains remain explicit", " ".join(self.contract["acceptance_criteria"]))

    def test_protected_gate_requires_nonempty_replayable_evidence(self) -> None:
        self.assertEqual(
            self.contract["dependency_contract"]["required_reexecution_order"],
            ["BAT-395", "BAT-396", "BAT-397", "BAT-398"],
        )
        criteria = " ".join(self.contract["acceptance_criteria"])
        self.assertIn("At least one real game and prediction cutoff", criteria)
        self.assertIn("explicitly approves the new matrix", criteria)
        self.assertFalse(self.contract["honesty_boundary"]["historical_population_ready"])

    def test_bulk_artifacts_remain_external_and_openai_has_no_authority(self) -> None:
        storage = self.contract["external_storage"]
        self.assertEqual(storage["data_root"], "<external-data-root>")
        self.assertFalse(storage["bulk_payloads_in_git"])
        self.assertTrue(storage["content_addressed_captures_required"])
        self.assertFalse(self.contract["openai_assistance"]["direct_canonical_or_pit_authority"])


if __name__ == "__main__":
    unittest.main()

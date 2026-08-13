from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class UnifiedEnforcementAdoptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads((ROOT / "configs/unified_assistive_policy.json").read_text(encoding="utf-8"))
        cls.registry = json.loads((ROOT / "configs/unified_assistive_acceptance_ownership.json").read_text(encoding="utf-8"))

    def test_exact_package_identities_are_bound(self) -> None:
        package = self.policy["enforcement_package"]
        self.assertEqual(204, package["mandatory_acceptance_rows"])
        self.assertEqual(
            "bd0142e8df4f25bd0b8733221c232cd3009786aad4f393a71154c9f2ade61111",
            package["acceptance_matrix_sha256"],
        )
        self.assertEqual(
            "7e7d927a3e3a3efd43705a4f2dc64ff9e593cde5085fb271a6276bd8194a1813",
            package["master_directive_sha256"],
        )

    def test_every_mandatory_row_has_one_canonical_live_owner(self) -> None:
        rows = self.registry["rows"]
        self.assertEqual(204, len(rows))
        self.assertEqual(204, len({row["id"] for row in rows}))
        for row in rows:
            self.assertTrue(row["mandatory"])
            owner = self.registry["owner_records"][row["primary_local_id"]]
            self.assertEqual(row["primary_jira_key"], owner["jira_key"])
            self.assertTrue(row["exact_acceptance_condition"])
            self.assertTrue(row["required_evidence"])

    def test_openai_rows_use_continuing_operations_owner(self) -> None:
        owners = {(row["primary_local_id"], row["primary_jira_key"]) for row in self.registry["rows"] if row["family"] == "OAI"}
        self.assertEqual({("POST-SUBTASK-168", "BAT-525")}, owners)

    def test_partial_success_vocabulary_is_forbidden(self) -> None:
        semantics = self.policy["result_semantics"]
        self.assertEqual(["PASS", "FAIL", "BLOCKED", "INCOMPLETE"], semantics["allowed"])
        self.assertEqual("PASS", semantics["exit_zero_only_for"])
        self.assertIn("PASS_HONEST_PARTIAL_STATE", semantics["forbidden"])

    def test_campaign_and_soak_floors_cannot_regress(self) -> None:
        minimums = self.policy["execution_minimums"]
        self.assertEqual({"units": 10, "effort_points": 40, "accepted_useful": 6}, minimums["cursor"])
        self.assertEqual(135, minimums["global"]["route_work_assignments"])
        self.assertEqual(450, minimums["global"]["effort_points"])
        self.assertEqual(21, minimums["scheduler_cycles"])
        self.assertEqual(25, minimums["soak_only_units"])
        self.assertEqual(100, minimums["soak_only_effort_points"])

    def test_scheduler_admission_and_claim_boundaries_fail_closed(self) -> None:
        inventory = self.policy["inventory"]
        controller = self.policy["controller"]
        self.assertTrue(inventory["current_pointer_promotion_requires_clean_current_main"])
        self.assertTrue(controller["scheduler_dispatch_required_for_operational_state"])
        self.assertTrue(controller["idle_with_ready_work_must_be_recorded"])
        self.assertEqual(0, controller["no_change_cycle_provider_calls_required"])


if __name__ == "__main__":
    unittest.main()

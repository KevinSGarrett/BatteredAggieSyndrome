from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aggie_analytics.validation.roster_domain_completeness import (  # noqa: E402
    AvailabilityAdmissionDenied,
    PayloadMountRequired,
    decide_admissions,
    identity_core,
    load_contract,
    missing_availability_evidence,
    probe_payloads,
    stable_hash,
)


class RosterDomainCompletenessUnitTests(unittest.TestCase):
    def test_contract_fail_closes_availability_and_new_layer(self) -> None:
        contract = load_contract(ROOT)
        self.assertFalse(contract["authority"]["availability_admission"])
        self.assertFalse(contract["authority"]["new_membership_layer_materialization"])
        self.assertEqual(contract["acceptance"]["tamu_gamebook_availability_rows"], 0)

    def test_absent_payloads_block_new_membership_and_availability(self) -> None:
        admissions = decide_admissions({"mount_state": "ABSENT", "present": 0})
        self.assertEqual(admissions["pregame_availability"], "BLOCKED")
        self.assertEqual(
            admissions["new_development_membership_layer"],
            "NOT_MATERIALIZED_EXISTING_BAT546_ADMISSION_PRESERVED",
        )
        self.assertEqual(
            admissions["season_membership_2004_2022"],
            "PRESERVE_EXISTING_BAT546_DEVELOPMENT_ONLY_ADMISSION",
        )

    def test_mounted_payloads_do_not_silently_rematerialize(self) -> None:
        with self.assertRaises(PayloadMountRequired):
            decide_admissions({"mount_state": "PRESENT", "present": 4})

    def test_missing_availability_evidence_is_explicit(self) -> None:
        codes = {row["code"] for row in missing_availability_evidence()}
        self.assertIn("MEMBERSHIP_IS_NOT_AVAILABILITY", codes)
        self.assertIn("POSTGAME_PARTICIPATION_IS_NOT_PREGAME_AVAILABILITY", codes)
        self.assertIn("GAMEBOOK_AVAILABILITY_ROWS_ZERO_AND_DOMAIN_ABSENT", codes)

    def test_identity_changes_when_availability_is_forged(self) -> None:
        core = identity_core(
            contract_sha256="a" * 64,
            input_identities={"roster_history_dataset_identity": "b" * 64},
            payload_mount_state="ABSENT",
            reconstructed_counts={"roster_history": {"source_rows": 1}},
            admissions={"pregame_availability": "BLOCKED"},
        )
        forged = dict(core)
        forged["availability_admission"] = True
        self.assertNotEqual(stable_hash(core), stable_hash(forged))
        with self.assertRaises(AvailabilityAdmissionDenied):
            raise AvailabilityAdmissionDenied("forged availability")

    def test_probe_reports_absent_expected_paths(self) -> None:
        probe = probe_payloads(Path(r"C:\BatteredAggieSyndrome.data"), ["missing/roster/path"])
        self.assertEqual(probe["mount_state"], "ABSENT")
        self.assertEqual(probe["present"], 0)


class RosterDomainCompletenessLiveTests(unittest.TestCase):
    def test_live_rebuild_when_manifests_present(self) -> None:
        data_root = Path(r"C:\BatteredAggieSyndrome.data")
        roster_manifest = (
            data_root
            / "manifests"
            / "historical_known_at"
            / "sha256"
            / "17e42ac17f94248213407366ee32e5a09705317d98c3561ee7e93fda6eda8dda"
            / "roster_history_reconciliation.json"
        )
        if not roster_manifest.is_file():
            self.skipTest("external roster-history manifest is not mounted")
        from aggie_analytics.validation.roster_domain_completeness import (
            rebuild_expected,
            validate_artifact,
        )

        expected = rebuild_expected(data_root=data_root, repo_root=ROOT)
        self.assertEqual(expected["payload_probe"]["mount_state"], "PARTIAL")
        self.assertEqual(expected["admissions"]["pregame_availability"], "BLOCKED")
        self.assertEqual(
            expected["reconstructed"]["roster_history"]["exact_membership_candidates"],
            154387,
        )
        self.assertEqual(
            expected["reconstructed"]["a_and_m_versus_national"]["tamu_admitted_membership_rows_2004_2022"],
            1326,
        )
        self.assertEqual(expected["reconstructed"]["tamu_gamebook"]["availability_rows"], 0)
        gate = ROOT / "artifacts" / "pit" / "roster_domain_completeness_gate.json"
        if not gate.is_file():
            self.skipTest("roster completeness gate has not been materialized yet")
        validated = validate_artifact(data_root=data_root, repo_root=ROOT, require_rebuild=True)
        self.assertEqual(validated["result"], "PASS")
        self.assertEqual(validated["gate_identity"], expected["gate_identity"])


if __name__ == "__main__":
    unittest.main()

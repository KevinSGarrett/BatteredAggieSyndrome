from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aggie_analytics.validation.roster_domain_completeness import (  # noqa: E402
    CONTRACT_ID,
    EXACT_MEMBERSHIP_FILTER_SPEC,
    PASS_CLASSIFICATION,
    PASS_RESULT,
    PayloadMountRequired,
    RECONSTRUCTED_COUNT_INTERPRETATION,
    SUPERSEDED_GATE_IDENTITY,
    compute_gate_identity,
    decide_admissions,
    derive_admissions_from_evidence,
    derive_authority_from_evidence,
    exact_membership_filter_identity,
    expected_gate_document,
    expected_issue_completion,
    expected_parent_identities,
    expected_scientific_nonclaims,
    load_contract,
    missing_availability_evidence,
    probe_payloads,
    validate_artifact,
)


def _synthetic_expected() -> dict[str, object]:
    contract = load_contract(ROOT)
    reconstructed = {
        "roster_history": {"source_rows": 1, "exact_membership_candidates": 1},
        "existing_membership_admission": {"admitted_rows": 1, "count_source": "PINNED_BAT546_GATE"},
        "post2022": {"source_rows": 1, "historical_known_at_eligible": False},
        "team_membership": {"admitted_rows": 1},
        "tamu_gamebook": {
            "availability_rows": 0,
            "availability_domain_present": False,
            "player_rows": 1,
        },
        "a_and_m_versus_national": {
            "tamu_admitted_membership_rows_2004_2022": 1,
            "count_interpretation": RECONSTRUCTED_COUNT_INTERPRETATION,
            "new_membership_layer_created": False,
        },
    }
    payload_probe = {
        "probed": 4,
        "present": 0,
        "absent": 4,
        "mount_state": "ABSENT",
        "probes": [],
    }
    return {
        "contract": contract,
        "payload_probe": payload_probe,
        "reconstructed": reconstructed,
        "admissions": derive_admissions_from_evidence(payload_probe, reconstructed),
        "authority": derive_authority_from_evidence(contract, reconstructed, payload_probe),
    }


class RosterDomainCompletenessUnitTests(unittest.TestCase):
    def test_contract_fail_closes_availability_and_new_layer(self) -> None:
        contract = load_contract(ROOT)
        self.assertEqual(contract["contract_id"], CONTRACT_ID)
        self.assertFalse(contract["authority"]["availability_admission"])
        self.assertFalse(contract["authority"]["protected_evaluation_admission"])
        self.assertFalse(contract["authority"]["champion_or_production_promotion"])
        self.assertFalse(contract["authority"]["new_membership_layer_materialization"])
        self.assertEqual(contract["acceptance"]["tamu_gamebook_availability_rows"], 0)
        self.assertEqual(contract["exact_membership_filter_spec"], EXACT_MEMBERSHIP_FILTER_SPEC)

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

    def test_parent_identities_are_derived_from_contract(self) -> None:
        contract = load_contract(ROOT)
        parents = expected_parent_identities(contract)
        self.assertEqual(
            parents["BAT-546_admitted_dataset"],
            contract["identities"]["bat546_admitted_dataset_identity"],
        )
        self.assertEqual(
            parents["BAT-547_admitted_dataset"],
            contract["identities"]["bat547_admitted_dataset_identity"],
        )

    def test_probe_reports_absent_expected_paths(self) -> None:
        probe = probe_payloads(Path(r"C:\BatteredAggieSyndrome.data"), ["missing/roster/path"])
        self.assertEqual(probe["mount_state"], "ABSENT")
        self.assertEqual(probe["present"], 0)


class RosterDomainCompletenessMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
        cls.expected = _synthetic_expected()
        cls.gate = expected_gate_document(cls.expected)

    def _mutated_gate(self, **changes: object) -> dict[str, object]:
        tampered = json.loads(json.dumps(self.gate))
        tampered.update(changes)
        tampered["gate_identity"] = compute_gate_identity(tampered)
        return tampered

    def _reject(self, gate: dict[str, object]) -> None:
        with self.assertRaises(ValueError):
            validate_artifact(
                data_root=self.data_root,
                repo_root=ROOT,
                require_rebuild=True,
                gate=gate,
                expected=self.expected,
            )

    def test_honest_synthetic_gate_passes(self) -> None:
        validated = validate_artifact(
            data_root=self.data_root,
            repo_root=ROOT,
            require_rebuild=True,
            gate=self.gate,
            expected=self.expected,
        )
        self.assertEqual(validated["result"], "PASS")
        self.assertEqual(validated["gate_identity"], self.gate["gate_identity"])
        self.assertNotEqual(validated["gate_identity"], SUPERSEDED_GATE_IDENTITY)

    def test_protected_evaluation_admission_true_is_rejected(self) -> None:
        authority = dict(self.gate["authority"])
        authority["protected_evaluation_admission"] = True
        self._reject(self._mutated_gate(authority=authority))

    def test_champion_or_production_promotion_true_is_rejected(self) -> None:
        authority = dict(self.gate["authority"])
        authority["champion_or_production_promotion"] = True
        self._reject(self._mutated_gate(authority=authority))

    def test_protected_performance_claim_true_is_rejected(self) -> None:
        nonclaims = dict(self.gate["scientific_nonclaims"])
        nonclaims["protected_performance_claimed"] = True
        self._reject(self._mutated_gate(scientific_nonclaims=nonclaims))

    def test_pregame_availability_admitted_is_rejected(self) -> None:
        admissions = dict(self.gate["admissions"])
        admissions["pregame_availability"] = "ADMITTED"
        self._reject(self._mutated_gate(admissions=admissions))

    def test_missing_availability_blocker_removed_is_rejected(self) -> None:
        blockers = [code for code in self.gate["remaining_blockers"] if code != "MEMBERSHIP_IS_NOT_AVAILABILITY"]
        self._reject(self._mutated_gate(remaining_blockers=blockers))

    def test_altered_classification_is_rejected(self) -> None:
        self._reject(self._mutated_gate(classification="ROSTER_AVAILABILITY_ADMITTED"))
        self._reject(self._mutated_gate(result="PASS_PRODUCTION_READY"))

    def test_altered_reconstructed_counts_are_rejected(self) -> None:
        reconstructed = json.loads(json.dumps(self.gate["reconstructed"]))
        reconstructed["a_and_m_versus_national"]["tamu_admitted_membership_rows_2004_2022"] = 999999
        self._reject(self._mutated_gate(reconstructed=reconstructed))

    def test_altered_membership_filter_identity_is_rejected(self) -> None:
        self._reject(self._mutated_gate(exact_membership_filter_identity="0" * 64))

    def test_altered_bat546_parent_identity_is_rejected(self) -> None:
        parents = dict(self.gate["parent_identities"])
        parents["BAT-546_admitted_dataset"] = "1" * 64
        self._reject(self._mutated_gate(parent_identities=parents))

    def test_altered_bat547_parent_identity_is_rejected(self) -> None:
        parents = dict(self.gate["parent_identities"])
        parents["BAT-547_admitted_dataset"] = "2" * 64
        self._reject(self._mutated_gate(parent_identities=parents))

    def test_forged_terminal_state_after_identity_recompute_is_rejected(self) -> None:
        forged = self._mutated_gate(
            result="FORGED_DONE",
            classification="PRODUCTION_CHAMPION",
            issue_completion={
                **self.gate["issue_completion"],
                "pregame_availability_still_blocked": False,
            },
        )
        self.assertNotEqual(forged["gate_identity"], self.gate["gate_identity"])
        self.assertEqual(forged["gate_identity"], compute_gate_identity(forged))
        self._reject(forged)

    def test_reconstructed_counts_are_not_a_new_admission_layer(self) -> None:
        self.assertEqual(
            self.gate["reconstructed"]["a_and_m_versus_national"]["count_interpretation"],
            RECONSTRUCTED_COUNT_INTERPRETATION,
        )
        self.assertFalse(self.gate["reconstructed"]["a_and_m_versus_national"]["new_membership_layer_created"])
        self.assertEqual(self.gate["result"], PASS_RESULT)
        self.assertEqual(self.gate["classification"], PASS_CLASSIFICATION)
        self.assertEqual(self.gate["scientific_nonclaims"], expected_scientific_nonclaims())
        self.assertEqual(self.gate["issue_completion"], expected_issue_completion(self.expected["contract"]))
        self.assertEqual(self.gate["exact_membership_filter_identity"], exact_membership_filter_identity())


class RosterDomainCompletenessLiveTests(unittest.TestCase):
    def test_live_rebuild_when_manifests_present(self) -> None:
        data_root = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
        roster_manifest = (
            data_root
            / "manifests"
            / "historical_known_at"
            / "sha256"
            / "17e42ac17f94248213407366ee32e5a09705317d98c3561ee7e93fda6eda8dda"
            / "roster_history_reconciliation.json"
        )
        history_payload = (
            data_root
            / "quarantine"
            / "historical_known_at"
            / "sha256"
            / "17e42ac17f94248213407366ee32e5a09705317d98c3561ee7e93fda6eda8dda"
            / "rosters"
        )
        try:
            import polars  # noqa: F401
        except ImportError:
            self.skipTest("optional data-engineering environment is not mounted")
        if not roster_manifest.is_file() or not history_payload.is_dir():
            self.skipTest("external roster-history manifest or candidate payloads are not mounted")
        from aggie_analytics.validation.roster_domain_completeness import (
            rebuild_expected,
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
        self.assertEqual(
            expected["reconstructed"]["a_and_m_versus_national"]["count_interpretation"],
            RECONSTRUCTED_COUNT_INTERPRETATION,
        )
        self.assertFalse(expected["reconstructed"]["a_and_m_versus_national"]["new_membership_layer_created"])
        self.assertEqual(expected["reconstructed"]["tamu_gamebook"]["availability_rows"], 0)
        self.assertFalse(expected["authority"]["availability_admission"])
        self.assertFalse(expected["authority"]["protected_evaluation_admission"])
        self.assertFalse(expected["authority"]["champion_or_production_promotion"])
        gate = ROOT / "artifacts" / "pit" / "roster_domain_completeness_gate.json"
        if not gate.is_file():
            self.skipTest("roster completeness gate has not been materialized yet")
        validated = validate_artifact(data_root=data_root, repo_root=ROOT, require_rebuild=True)
        self.assertEqual(validated["result"], "PASS")
        self.assertEqual(validated["gate_identity"], expected["gate_identity"])
        self.assertNotEqual(validated["gate_identity"], SUPERSEDED_GATE_IDENTITY)


if __name__ == "__main__":
    unittest.main()

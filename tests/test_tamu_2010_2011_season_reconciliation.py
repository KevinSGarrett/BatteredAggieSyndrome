from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data.tamu_season_reconciliation import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    PASS_CLASSIFICATION,
    PROTECTED_LANE,
    TAMU_SEEDS,
    compute_gate_identity,
    expected_authority,
    expected_nonclaims,
    load_contract,
    load_json,
    validate_artifact,
)

DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


def _validate(gate: dict, *, require_rebuild: bool = False):
    return validate_artifact(
        data_root=DATA_ROOT,
        repo_root=ROOT,
        require_rebuild=require_rebuild,
        gate=gate,
    )


class SeasonReconciliationContractTests(unittest.TestCase):
    def test_contract_is_fail_closed(self) -> None:
        contract = load_contract(ROOT)
        self.assertEqual(TAMU_SEEDS, contract["tamu_seeds"])
        self.assertEqual(PROTECTED_LANE, "RETAIN_PROTECTED_LANE_BLOCKED")
        self.assertTrue(PASS_CLASSIFICATION.endswith("CANDIDATE_ONLY"))
        self.assertFalse(contract["texas_2011_conflict"]["name_only_promotion"])
        self.assertEqual(expected_authority(), contract["authority"])
        self.assertFalse(expected_nonclaims()["name_only_promoted"])

    def test_texas_conflict_stays_unresolved_in_contract(self) -> None:
        conflict = load_contract(ROOT)["texas_2011_conflict"]
        self.assertEqual("2011-11-24", conflict["ncaa_official_date"])
        self.assertEqual("2011-11-25", conflict["sidearm_or_gap_matrix_date"])
        self.assertEqual("UNRESOLVED_NAME_ONLY_NOT_PROMOTED", conflict["disposition"])


class SeasonReconciliationMutationTests(unittest.TestCase):
    def setUp(self) -> None:
        gate_path = ROOT / GATE_RELATIVE
        if not gate_path.is_file():
            self.skipTest("season reconciliation gate is not present")
        self.gate = load_json(gate_path)

    def test_current_gate_validates_without_rebuild(self) -> None:
        result = _validate(self.gate, require_rebuild=False)
        self.assertEqual("PASS", result["result"])
        self.assertEqual("6d1704db9025d556aaf5861ba55a52ce56590820960928f4648f28fa54a7018e", result["gate_identity"])

    def test_changed_source_hash_is_rejected(self) -> None:
        identities = json.loads(json.dumps(self.gate["input_identities"]))
        identities["phase2_gate_identity"] = "00" * 32
        with self.assertRaises(AuthorityViolation):
            _validate(_mutated(self.gate, input_identities=identities))

    def test_changed_season_team_identity_is_rejected(self) -> None:
        seeds = dict(self.gate["tamu_seeds"])
        seeds["2010"] = "000000"
        with self.assertRaises(AuthorityViolation):
            _validate(_mutated(self.gate, tamu_seeds=seeds))

    def test_altered_total_is_rejected(self) -> None:
        counts = json.loads(json.dumps(self.gate["counts"]))
        counts["comparison_rows"] = int(counts["comparison_rows"]) + 1
        with self.assertRaises(AuthorityViolation):
            _validate(_mutated(self.gate, counts=counts))

    def test_dropped_conflict_is_rejected(self) -> None:
        conflict = json.loads(json.dumps(self.gate["texas_2011_conflict"]))
        conflict["resolved"] = True
        with self.assertRaises(AuthorityViolation):
            _validate(_mutated(self.gate, texas_2011_conflict=conflict))

    def test_name_only_promotion_is_rejected(self) -> None:
        conflict = json.loads(json.dumps(self.gate["texas_2011_conflict"]))
        conflict["name_only_promotion"] = True
        with self.assertRaises(AuthorityViolation):
            _validate(_mutated(self.gate, texas_2011_conflict=conflict))

    def test_season_total_as_per_game_official_is_rejected(self) -> None:
        authority = json.loads(json.dumps(self.gate["authority"]))
        authority["season_total_as_per_game_official"] = True
        with self.assertRaises(AuthorityViolation):
            _validate(_mutated(self.gate, authority=authority))

    def test_membership_promoted_to_availability_is_rejected(self) -> None:
        authority = json.loads(json.dumps(self.gate["authority"]))
        authority["membership_as_availability"] = True
        with self.assertRaises(AuthorityViolation):
            _validate(_mutated(self.gate, authority=authority))

    def test_participation_promoted_to_availability_is_rejected(self) -> None:
        authority = json.loads(json.dumps(self.gate["authority"]))
        authority["participation_as_availability"] = True
        with self.assertRaises(AuthorityViolation):
            _validate(_mutated(self.gate, authority=authority))

    def test_fabricated_known_at_is_rejected(self) -> None:
        authority = json.loads(json.dumps(self.gate["authority"]))
        authority["historical_known_at_from_capture_time"] = True
        with self.assertRaises(AuthorityViolation):
            _validate(_mutated(self.gate, authority=authority))

    def test_protected_lane_authority_is_rejected(self) -> None:
        authority = json.loads(json.dumps(self.gate["authority"]))
        authority["protected_outcome_authority"] = True
        with self.assertRaises(AuthorityViolation):
            _validate(_mutated(self.gate, authority=authority))

    def test_forged_completion_after_rehash_is_rejected(self) -> None:
        forged = _mutated(self.gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION")
        with self.assertRaises(AuthorityViolation):
            _validate(forged)

    def test_rebuild_matches_when_lake_present(self) -> None:
        rows = Path(str(self.gate["payload"]["rows"]))
        if not rows.is_file():
            self.skipTest("bulk season reconciliation rows are not on this machine")
        result = _validate(self.gate, require_rebuild=True)
        self.assertEqual("PASS", result["result"])


if __name__ == "__main__":
    unittest.main()

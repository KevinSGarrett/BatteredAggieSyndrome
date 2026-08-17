from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aggie_analytics.validation.protected import classify_season  # noqa: E402
from aggie_analytics.validation.protected_split_authority import (  # noqa: E402
    CONTAMINATION_STATUS,
    assert_current_contract_respects_protected_splits,
    assert_labels_cannot_override_protected_membership,
    is_historical_contaminated_contract,
    protected_role_ignoring_label,
    registry_role_for_season,
    validate_current_contract,
)
from tools.audit_protected_split_exposure import build_audit, validate_audit  # noqa: E402


class ProtectedSplitExposureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original = json.loads(
            (ROOT / "configs/preliminary_unprotected_baseline_contract.json").read_text(encoding="utf-8")
        )
        self.successor = json.loads(
            (ROOT / "configs/preliminary_development_safe_baseline_contract.json").read_text(encoding="utf-8")
        )

    def test_registry_matches_hardcoded_classifier_and_seals_2024_2025(self) -> None:
        for season, expected in (
            (2010, "DEVELOPMENT"),
            (2022, "DEVELOPMENT"),
            (2023, "DEVELOPMENT_SELECTION"),
            (2024, "PROTECTED_TEST"),
            (2025, "PROTECTED_TEST"),
            (2026, "FORWARD_SHADOW"),
        ):
            self.assertEqual(classify_season(season), expected)
            self.assertEqual(registry_role_for_season(ROOT, season)["role"], expected)
        self.assertFalse(registry_role_for_season(ROOT, 2024)["tuning_allowed"])
        self.assertFalse(registry_role_for_season(ROOT, 2025)["threshold_setting_allowed"])
        self.assertEqual(registry_role_for_season(ROOT, 2024)["protected_result_access"], "SEALED_UNTIL_PROTOCOL_AND_ARTIFACT_READY")

    def test_labels_cannot_override_protected_canonical_membership(self) -> None:
        for label in (
            "DEVELOPMENT_TUNE",
            "DEVELOPMENT_EVALUATION_UNPROTECTED",
            "PRELIMINARY_UNPROTECTED",
            "UNPROTECTED",
        ):
            self.assertEqual(protected_role_ignoring_label(ROOT, 2024, label), "PROTECTED_TEST")
            self.assertEqual(protected_role_ignoring_label(ROOT, 2025, label), "PROTECTED_TEST")
            self.assertEqual(assert_labels_cannot_override_protected_membership(ROOT, 2025, label), "PROTECTED_TEST")

    def test_current_successor_contract_is_authoritative_and_safe(self) -> None:
        self.assertFalse(is_historical_contaminated_contract(self.successor))
        assert_current_contract_respects_protected_splits(ROOT, self.successor)
        self.assertEqual(self.successor["split_policy"]["2023"], "DEVELOPMENT_FIT_SELECTION_CALIBRATION")
        self.assertEqual(self.successor["split_policy"]["2024"], "PROTECTED_TEST_INACCESSIBLE")
        self.assertEqual(self.successor["split_policy"]["2025"], "PROTECTED_TEST_INACCESSIBLE")
        self.assertIsNone(self.successor["replacement_protected_period"])

    def test_historical_contaminated_contract_is_preserved_without_authority(self) -> None:
        self.assertTrue(is_historical_contaminated_contract(self.original))
        self.assertEqual(self.original["split_policy"]["2024"], "DEVELOPMENT_TUNE")
        self.assertEqual(self.original["split_policy"]["2025"], "DEVELOPMENT_EVALUATION_UNPROTECTED")
        assert_current_contract_respects_protected_splits(ROOT, self.original)
        self.assertEqual(self.original["contamination"]["status"], CONTAMINATION_STATUS)
        self.assertTrue(self.original["contamination"]["split_labels_retained_without_rewrite"])

    def test_rejects_current_contract_labeling_protected_season_as_development_tune(self) -> None:
        forged = copy.deepcopy(self.successor)
        forged["split_policy"]["2024"] = "DEVELOPMENT_TUNE"
        with self.assertRaisesRegex(ValueError, "SPLIT-PROTECTED"):
            assert_current_contract_respects_protected_splits(ROOT, forged)

    def test_rejects_current_contract_labeling_protected_season_as_unprotected_evaluation(self) -> None:
        forged = copy.deepcopy(self.successor)
        forged["split_policy"]["2025"] = "DEVELOPMENT_EVALUATION_UNPROTECTED"
        errors = validate_current_contract(ROOT, forged)
        self.assertTrue(any("2025" in item and "DEVELOPMENT_EVALUATION_UNPROTECTED" in item for item in errors))

    def test_audit_records_exposed_2024_2025_results_and_revokes_authority(self) -> None:
        payload = build_audit(ROOT)
        validate_audit(payload)
        self.assertGreaterEqual(payload["contradiction_count"], 1)
        self.assertGreaterEqual(payload["exposed_result_count"], 1)
        families = {row.get("family") for row in payload["exposed_results"]}
        self.assertIn("elo_rating", families)
        self.assertIn("model_selection", payload["authority_revoked_for"])
        self.assertFalse(payload["protected_nonclaims"]["historical_metrics_deleted"])
        mutated = copy.deepcopy(payload)
        mutated["classification"] = "CLEAN"
        mutated["artifact_identity"] = __import__(
            "aggie_analytics.validation.protected_split_authority", fromlist=["compute_artifact_identity"]
        ).compute_artifact_identity(mutated)
        with self.assertRaisesRegex(ValueError, "exposure disposition"):
            validate_audit(mutated)


if __name__ == "__main__":
    unittest.main()

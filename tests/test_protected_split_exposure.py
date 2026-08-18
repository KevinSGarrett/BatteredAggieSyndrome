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
    compute_audit_identity,
    is_historical_contaminated_contract,
    protected_role_ignoring_label,
    registry_role_for_season,
    sha256_file,
    validate_current_contract,
)
from tools.audit_protected_split_exposure import (  # noqa: E402
    SCHEMA_VERSION,
    SUPERSEDED_V2_IDENTITY,
    SUPERSESSION_REASON,
    build_audit,
    validate_audit,
)

COMMITTED_AUDIT = ROOT / "artifacts/governance/protected_split_exposure_audit.json"
STALE_V2_AUDIT = ROOT / "tests/fixtures/protected_split_exposure_audit.v2.stale.json"


class ProtectedSplitExposureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.canonical_audit = json.loads(COMMITTED_AUDIT.read_text(encoding="utf-8"))

    def setUp(self) -> None:
        self.original = json.loads(
            (ROOT / "configs/preliminary_unprotected_baseline_contract.json").read_text(encoding="utf-8")
        )
        self.successor = json.loads(
            (ROOT / "configs/preliminary_development_safe_baseline_contract.json").read_text(encoding="utf-8")
        )
        self.play_drive = json.loads(
            (ROOT / "configs/historical_play_drive_pit_aggregate_contract.json").read_text(encoding="utf-8")
        )
        self.play_drive_successor = json.loads(
            (
                ROOT / "configs/historical_play_drive_pit_aggregate_development_safe_contract.json"
            ).read_text(encoding="utf-8")
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
        self.assertEqual(
            registry_role_for_season(ROOT, 2024)["protected_result_access"],
            "SEALED_UNTIL_PROTOCOL_AND_ARTIFACT_READY",
        )

    def test_labels_cannot_override_protected_canonical_membership(self) -> None:
        for label in (
            "DEVELOPMENT_TUNE",
            "DEVELOPMENT_EVALUATION_UNPROTECTED",
            "PRELIMINARY_UNPROTECTED",
            "UNPROTECTED",
            "DEVELOPMENT_ONLY",
        ):
            self.assertEqual(protected_role_ignoring_label(ROOT, 2024, label), "PROTECTED_TEST")
            self.assertEqual(protected_role_ignoring_label(ROOT, 2025, label), "PROTECTED_TEST")
            self.assertEqual(assert_labels_cannot_override_protected_membership(ROOT, 2025, label), "PROTECTED_TEST")

    def test_current_successor_contract_is_authoritative_and_safe(self) -> None:
        self.assertFalse(is_historical_contaminated_contract(self.successor))
        assert_current_contract_respects_protected_splits(
            ROOT, self.successor, relative_path="configs/preliminary_development_safe_baseline_contract.json"
        )
        self.assertEqual(self.successor["split_policy"]["2023"], "DEVELOPMENT_FIT_SELECTION_CALIBRATION")
        self.assertEqual(self.successor["split_policy"]["2024"], "PROTECTED_TEST_INACCESSIBLE")
        self.assertEqual(self.successor["split_policy"]["2025"], "PROTECTED_TEST_INACCESSIBLE")
        self.assertIsNone(self.successor["replacement_protected_period"])

    def test_historical_contaminated_contract_is_preserved_without_authority(self) -> None:
        self.assertTrue(is_historical_contaminated_contract(self.original))
        self.assertEqual(self.original["split_policy"]["2024"], "DEVELOPMENT_TUNE")
        self.assertEqual(self.original["split_policy"]["2025"], "DEVELOPMENT_EVALUATION_UNPROTECTED")
        assert_current_contract_respects_protected_splits(
            ROOT,
            self.original,
            relative_path="configs/preliminary_unprotected_baseline_contract.json",
        )
        self.assertEqual(self.original["contamination"]["status"], CONTAMINATION_STATUS)
        self.assertTrue(self.original["contamination"]["split_labels_retained_without_rewrite"])

    def test_contamination_marker_cannot_self_exempt_a_new_contract(self) -> None:
        forged = {
            "contract_id": "malicious-self-exempt-v1",
            "split_policy": {
                "2024": "DEVELOPMENT_TUNE",
                "2025": "DEVELOPMENT_EVALUATION_UNPROTECTED",
            },
            "contamination": {
                "status": CONTAMINATION_STATUS,
                "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
                "authority_revoked_for": [
                    "model_selection",
                    "feature_selection",
                    "calibration_selection",
                    "threshold_setting",
                    "champion_selection",
                    "promotion",
                    "protected_performance_claims",
                ],
            },
        }
        errors = validate_current_contract(ROOT, forged)
        self.assertTrue(any("self-exempt" in item for item in errors))
        with self.assertRaisesRegex(ValueError, "self-exempt"):
            assert_current_contract_respects_protected_splits(ROOT, forged)

    def test_rejects_current_contract_labeling_protected_season_as_development_tune(self) -> None:
        forged = copy.deepcopy(self.successor)
        forged["split_policy"]["2024"] = "DEVELOPMENT_TUNE"
        with self.assertRaisesRegex(ValueError, "SPLIT-PROTECTED"):
            assert_current_contract_respects_protected_splits(
                ROOT, forged, relative_path="configs/preliminary_development_safe_baseline_contract.json"
            )

    def test_rejects_current_contract_labeling_protected_season_as_unprotected_evaluation(self) -> None:
        forged = copy.deepcopy(self.successor)
        forged["split_policy"]["2025"] = "DEVELOPMENT_EVALUATION_UNPROTECTED"
        errors = validate_current_contract(
            ROOT, forged, relative_path="configs/preliminary_development_safe_baseline_contract.json"
        )
        self.assertTrue(any("2025" in item and "DEVELOPMENT_EVALUATION_UNPROTECTED" in item for item in errors))

    def test_play_drive_successor_is_feature_only_for_protected_seasons(self) -> None:
        assert_current_contract_respects_protected_splits(
            ROOT,
            self.play_drive_successor,
            relative_path="configs/historical_play_drive_pit_aggregate_development_safe_contract.json",
        )
        for season in ("2024", "2025"):
            item = self.play_drive_successor["season_authority"][season]
            self.assertEqual(item["role"], "PROTECTED_FEATURE_ONLY")
            self.assertFalse(item["outcomes_included"])
            self.assertFalse(item["metrics_included"])
            self.assertFalse(item["development_training"])
        self.assertEqual(self.play_drive["source_contract"]["target_seasons"], [2023, 2024, 2025])
        self.assertTrue(self.play_drive["authority"]["development_feature_admission"])

    def test_audit_records_omitted_play_drive_surfaces_and_revokes_authority(self) -> None:
        payload = copy.deepcopy(self.canonical_audit)
        validate_audit(payload, ROOT, expected=self.canonical_audit)
        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        paths = {row["path"] for row in payload["surfaces"]}
        for required in (
            "configs/preliminary_unprotected_baseline_contract.json",
            "configs/historical_play_drive_pit_aggregate_contract.json",
            "configs/historical_play_drive_pit_extension_contract.json",
            "artifacts/pit/historical_play_drive_pit_aggregate_gate.json",
            "artifacts/jira_evidence/POST-SUBTASK-176.json",
            "artifacts/jira_evidence/POST-SUBTASK-183.json",
        ):
            self.assertIn(required, paths)
        self.assertGreaterEqual(payload["contradiction_count"], 1)
        self.assertGreaterEqual(payload["exposed_result_count"], 1)
        self.assertEqual(payload["contradiction_count"], sum(len(row["contradictions"]) for row in payload["surfaces"]))
        self.assertEqual(payload["exposed_result_count"], len(payload["exposed_results"]))
        self.assertEqual(payload["surface_count"], len(payload["surfaces"]))
        families = {row.get("family") for row in payload["exposed_results"]}
        self.assertIn("elo_rating", families)
        self.assertIn("model_selection", payload["authority_revoked_for"])
        self.assertFalse(payload["protected_nonclaims"]["historical_metrics_deleted"])
        self.assertEqual(
            payload["registry_sha256"],
            sha256_file(ROOT / "governance/PROTECTED_SPLIT_REGISTRY.csv"),
        )

    def _rehash(self, payload: dict) -> dict:
        mutated = copy.deepcopy(payload)
        mutated["artifact_identity"] = compute_audit_identity(mutated)
        return mutated

    def test_committed_audit_reconstructs_independently(self) -> None:
        validate_audit(self.canonical_audit, ROOT)
        rebuilt = build_audit(ROOT)
        self.assertEqual(self.canonical_audit["schema_version"], SCHEMA_VERSION)
        self.assertEqual(self.canonical_audit["classification"], CONTAMINATION_STATUS)
        self.assertEqual(
            self.canonical_audit["successor_contract_sha256"],
            sha256_file(ROOT / "configs/preliminary_development_safe_baseline_contract.json"),
        )
        self.assertEqual(self.canonical_audit["artifact_identity"], rebuilt["artifact_identity"])
        self.assertNotEqual(self.canonical_audit["artifact_identity"], SUPERSEDED_V2_IDENTITY)
        self.assertEqual(
            self.canonical_audit["superseded_identities"][0]["artifact_identity"],
            SUPERSEDED_V2_IDENTITY,
        )
        self.assertEqual(
            self.canonical_audit["superseded_identities"][0]["supersession_reason"],
            SUPERSESSION_REASON,
        )

    def test_validate_rejects_forged_empty_surfaces_after_rehash(self) -> None:
        payload = self._rehash(
            {
                **self.canonical_audit,
                "surfaces": [],
                "exposed_results": [],
                "exposed_result_count": 0,
                "contradiction_count": 1,
            }
        )
        with self.assertRaisesRegex(ValueError, "surfaces|exposed historical"):
            validate_audit(payload, ROOT, expected=self.canonical_audit)

    def test_validate_rejects_removed_exposed_result_after_rehash(self) -> None:
        payload = copy.deepcopy(self.canonical_audit)
        mutated = copy.deepcopy(payload)
        mutated["exposed_results"] = mutated["exposed_results"][1:]
        mutated["exposed_result_count"] = len(mutated["exposed_results"])
        mutated["artifact_identity"] = compute_audit_identity(mutated)
        with self.assertRaisesRegex(ValueError, "exposed_results|independent reconstruction"):
            validate_audit(mutated, ROOT, expected=self.canonical_audit)

    def test_validate_rejects_forged_counts_after_rehash(self) -> None:
        payload = copy.deepcopy(self.canonical_audit)
        mutated = copy.deepcopy(payload)
        mutated["contradiction_count"] = 0
        mutated["artifact_identity"] = compute_audit_identity(mutated)
        with self.assertRaisesRegex(ValueError, "contradiction"):
            validate_audit(mutated, ROOT, expected=self.canonical_audit)

    def test_validate_rejects_forged_registry_hash_after_rehash(self) -> None:
        payload = copy.deepcopy(self.canonical_audit)
        mutated = copy.deepcopy(payload)
        mutated["registry_sha256"] = "0" * 64
        mutated["artifact_identity"] = compute_audit_identity(mutated)
        with self.assertRaisesRegex(ValueError, "registry_sha256|independent reconstruction"):
            validate_audit(mutated, ROOT, expected=self.canonical_audit)

    def test_validate_rejects_successor_substitution_after_rehash(self) -> None:
        payload = copy.deepcopy(self.canonical_audit)
        mutated = copy.deepcopy(payload)
        mutated["successor_contract"] = "configs/preliminary_unprotected_baseline_contract.json"
        mutated["artifact_identity"] = compute_audit_identity(mutated)
        with self.assertRaisesRegex(ValueError, "successor_contract|independent reconstruction"):
            validate_audit(mutated, ROOT, expected=self.canonical_audit)

    def test_validate_rejects_incomplete_authority_denials_after_rehash(self) -> None:
        payload = copy.deepcopy(self.canonical_audit)
        mutated = copy.deepcopy(payload)
        mutated["authority_revoked_for"] = ["model_selection"]
        mutated["artifact_identity"] = compute_audit_identity(mutated)
        with self.assertRaisesRegex(ValueError, "authority denials"):
            validate_audit(mutated, ROOT, expected=self.canonical_audit)

    def test_validate_rejects_classification_forged_after_rehash(self) -> None:
        payload = copy.deepcopy(self.canonical_audit)
        mutated = copy.deepcopy(payload)
        mutated["classification"] = "CLEAN"
        mutated["artifact_identity"] = compute_audit_identity(mutated)
        with self.assertRaisesRegex(ValueError, "CLEAN|exposure disposition"):
            validate_audit(mutated)

    def test_omitted_relevant_file_is_discovered(self) -> None:
        extra_path = ROOT / "configs" / "omitted_protected_tune_contract.json"
        extra_path.write_text(
            json.dumps(
                {
                    "contract_id": "omitted-protected-tune-v1",
                    "split_policy": {
                        "2024": "DEVELOPMENT_TUNE",
                        "2025": "DEVELOPMENT_EVALUATION_UNPROTECTED",
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        try:
            rebuilt = build_audit(ROOT)
            self.assertIn("configs/omitted_protected_tune_contract.json", rebuilt["relevant_inventory"])
            self.assertIn(
                "configs/omitted_protected_tune_contract.json",
                [row["path"] for row in rebuilt["surfaces"]],
            )
            with self.assertRaisesRegex(ValueError, "current contracts retain protected development authority"):
                validate_audit(rebuilt, ROOT)
        finally:
            extra_path.unlink(missing_ok=True)

    def test_protected_feature_surface_cannot_gain_outcome_access(self) -> None:
        forged = copy.deepcopy(self.play_drive_successor)
        forged["season_authority"]["2024"]["outcomes_included"] = True
        errors = validate_current_contract(
            ROOT,
            forged,
            relative_path="configs/historical_play_drive_pit_aggregate_development_safe_contract.json",
        )
        self.assertTrue(any("outcomes" in item or "2024" in item for item in errors))

    def test_irrelevant_file_does_not_change_identity(self) -> None:
        extra_path = ROOT / "configs" / "irrelevant_unrelated_scan_noise.json"
        extra_path.write_text('{"note":"no protected seasons"}\n', encoding="utf-8")
        try:
            rebuilt = build_audit(ROOT)
            self.assertEqual(rebuilt["artifact_identity"], self.canonical_audit["artifact_identity"])
            self.assertNotIn("configs/irrelevant_unrelated_scan_noise.json", rebuilt["relevant_inventory"])
            validate_audit(self.canonical_audit, ROOT)
        finally:
            extra_path.unlink(missing_ok=True)

    def test_stale_v2_audit_is_rejected(self) -> None:
        stale = json.loads(STALE_V2_AUDIT.read_text(encoding="utf-8"))
        self.assertEqual(stale["artifact_identity"], SUPERSEDED_V2_IDENTITY)
        with self.assertRaisesRegex(ValueError, "v2 schema|not current authority|unexpected protected-split audit schema"):
            validate_audit(stale, ROOT)

    def test_validate_rejects_missing_superseded_v2_identity(self) -> None:
        mutated = self._rehash({**self.canonical_audit, "superseded_identities": []})
        with self.assertRaisesRegex(ValueError, "missing superseded v2 identity"):
            validate_audit(mutated)

    def test_validate_rejects_v2_identity_as_current(self) -> None:
        mutated = copy.deepcopy(self.canonical_audit)
        mutated["artifact_identity"] = SUPERSEDED_V2_IDENTITY
        with self.assertRaisesRegex(ValueError, "v2 identity is not current authority"):
            validate_audit(mutated)
        stale_schema = self._rehash({**self.canonical_audit, "schema_version": "aggie.governance.protected_split_exposure_audit.v2"})
        with self.assertRaisesRegex(ValueError, "v2 schema is not current authority"):
            validate_audit(stale_schema)

    def test_validate_rejects_omitted_supersession_reason(self) -> None:
        mutated = copy.deepcopy(self.canonical_audit)
        mutated["superseded_identities"] = [
            {
                "artifact_identity": SUPERSEDED_V2_IDENTITY,
                "schema_version": "aggie.governance.protected_split_exposure_audit.v2",
                "preserved_as": "SUPERSEDED_SCHEMA_V2_EVIDENCE",
            }
        ]
        mutated = self._rehash(mutated)
        with self.assertRaisesRegex(ValueError, "omitting supersession_reason"):
            validate_audit(mutated)

    def test_validate_rejects_clean_forgery_with_superseded_v2(self) -> None:
        mutated = self._rehash({**self.canonical_audit, "classification": "CLEAN"})
        self.assertEqual(
            mutated["superseded_identities"][0]["artifact_identity"],
            SUPERSEDED_V2_IDENTITY,
        )
        with self.assertRaisesRegex(ValueError, "CLEAN classification cannot coexist with superseded v2"):
            validate_audit(mutated)


if __name__ == "__main__":
    unittest.main()

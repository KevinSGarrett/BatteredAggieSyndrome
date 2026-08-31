from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.validate_checkout_authority_pins import validate_checkout_authority_pins


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class CheckoutAuthorityPinsTests(unittest.TestCase):
    def _contract(self) -> dict:
        return {
            "schema_version": 1,
            "authority_key_names": ["base_commit", "source_commit", "material_merge_sha", "git_base_commit"],
            "artifacts": [
                {
                    "path": "configs/codex_usage_interlock_change_manifest.json",
                    "identity_field": "manifest_identity",
                    "rules": [
                        {
                            "path": "base_commit",
                            "role": "AUTHORITATIVE_PINNED",
                            "authority_label_path": "work_class",
                            "required_authority_label": "PROJECT_WORK",
                            "must_be_git_ancestor_of_head": True,
                        }
                    ],
                },
                {
                    "path": "configs/unified_assistive_change_routing_binding.json",
                    "rules": [
                        {
                            "path": "source_commit",
                            "role": "AUTHORITATIVE_PINNED",
                            "authority_label_path": "class",
                            "required_authority_label": "PROJECT_WORK",
                            "must_be_git_ancestor_of_head": True,
                        }
                    ],
                },
                {
                    "path": "jira/reconciliation/BAT_AUTHORITY_PROGRESS_COMMENT_LEDGER.json",
                    "rules": [
                        {
                            "path": "comments[].material_merge_sha",
                            "role": "AUTHORITATIVE_PINNED",
                            "authority_label_path": "comments[].evidence_classification",
                            "required_authority_label": "IMMUTABLE_CYCLE_SNAPSHOT",
                            "must_be_git_ancestor_of_head": True,
                        }
                    ],
                },
                {
                    "path": "artifacts/operations/drift_alert_validation.json",
                    "identity_field": "artifact_identity",
                    "rules": [{"path": "producer.git_base_commit", "role": "DIAGNOSTIC_NON_AUTHORITY"}],
                },
            ],
            "cross_artifact_equalities": [
                {
                    "left": "configs/codex_usage_interlock_change_manifest.json::base_commit",
                    "right": "configs/unified_assistive_change_routing_binding.json::source_commit",
                }
            ],
        }

    def _seed_repo(self, root: Path, *, base_commit: str = "a" * 40) -> None:
        manifest = {
            "work_class": "PROJECT_WORK",
            "base_commit": base_commit,
        }
        manifest["manifest_identity"] = "placeholder"
        _write(root / "configs/codex_usage_interlock_change_manifest.json", manifest)
        payload = json.loads((root / "configs/codex_usage_interlock_change_manifest.json").read_text(encoding="utf-8"))
        payload["manifest_identity"] = hashlib.sha256(
            json.dumps({k: v for k, v in payload.items() if k != "manifest_identity"}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        _write(root / "configs/codex_usage_interlock_change_manifest.json", payload)

        _write(
            root / "configs/unified_assistive_change_routing_binding.json",
            {"class": "PROJECT_WORK", "source_commit": base_commit},
        )
        _write(
            root / "jira/reconciliation/BAT_AUTHORITY_PROGRESS_COMMENT_LEDGER.json",
            {
                "schema_version": 2,
                "comments": [
                    {
                        "evidence_classification": "IMMUTABLE_CYCLE_SNAPSHOT",
                        "material_merge_sha": base_commit,
                    }
                ],
            },
        )
        drift = {"producer": {"git_base_commit": base_commit}, "artifact_identity": "placeholder"}
        drift["artifact_identity"] = hashlib.sha256(
            json.dumps({k: v for k, v in drift.items() if k != "artifact_identity"}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        _write(root / "artifacts/operations/drift_alert_validation.json", drift)

    @mock.patch("tools.validate_checkout_authority_pins._is_commit_in_history", return_value=True)
    @mock.patch("tools.validate_checkout_authority_pins._is_ancestor_of_head", return_value=True)
    def test_valid_contract_passes(self, *_mocks: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_repo(root)
            self.assertEqual([], validate_checkout_authority_pins(root, self._contract()))

    @mock.patch("tools.validate_checkout_authority_pins._is_commit_in_history", return_value=False)
    @mock.patch("tools.validate_checkout_authority_pins._is_ancestor_of_head", return_value=False)
    def test_pin_absent_from_history_fails_closed(self, *_mocks: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_repo(root)
            findings = validate_checkout_authority_pins(root, self._contract())
            self.assertTrue(any("absent from git history" in item for item in findings))

    @mock.patch("tools.validate_checkout_authority_pins._is_commit_in_history", return_value=True)
    @mock.patch("tools.validate_checkout_authority_pins._is_ancestor_of_head", return_value=True)
    def test_missing_pin_field_fails(self, *_mocks: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_repo(root)
            _write(root / "configs/codex_usage_interlock_change_manifest.json", {"work_class": "PROJECT_WORK"})
            findings = validate_checkout_authority_pins(root, self._contract())
            self.assertTrue(any("missing declared authority path" in item for item in findings))

    @mock.patch("tools.validate_checkout_authority_pins._is_commit_in_history", return_value=True)
    @mock.patch("tools.validate_checkout_authority_pins._is_ancestor_of_head", return_value=True)
    def test_malformed_pin_fails(self, *_mocks: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_repo(root)
            _write(
                root / "configs/unified_assistive_change_routing_binding.json",
                {"class": "PROJECT_WORK", "source_commit": "not-a-sha"},
            )
            findings = validate_checkout_authority_pins(root, self._contract())
            self.assertTrue(any("must be a 40-hex commit pin" in item for item in findings))

    @mock.patch("tools.validate_checkout_authority_pins._is_commit_in_history", return_value=True)
    @mock.patch("tools.validate_checkout_authority_pins._is_ancestor_of_head", return_value=True)
    def test_missing_authority_label_fails(self, *_mocks: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_repo(root)
            _write(
                root / "configs/unified_assistive_change_routing_binding.json",
                {"source_commit": "a" * 40},
            )
            findings = validate_checkout_authority_pins(root, self._contract())
            self.assertTrue(any("missing authority label" in item for item in findings))

    @mock.patch("tools.validate_checkout_authority_pins._is_commit_in_history", return_value=True)
    @mock.patch("tools.validate_checkout_authority_pins._is_ancestor_of_head", return_value=True)
    def test_cross_artifact_pin_mismatch_fails(self, *_mocks: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_repo(root, base_commit="a" * 40)
            _write(
                root / "configs/unified_assistive_change_routing_binding.json",
                {"class": "PROJECT_WORK", "source_commit": "b" * 40},
            )
            findings = validate_checkout_authority_pins(root, self._contract())
            self.assertTrue(any("cross-artifact checkout pin mismatch" in item for item in findings))

    @mock.patch("tools.validate_checkout_authority_pins._is_commit_in_history", return_value=True)
    @mock.patch("tools.validate_checkout_authority_pins._is_ancestor_of_head", return_value=True)
    def test_undeclared_authority_key_fails(self, *_mocks: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_repo(root)
            payload = json.loads(
                (root / "artifacts/operations/drift_alert_validation.json").read_text(encoding="utf-8")
            )
            payload["producer"]["source_commit"] = "a" * 40
            _write(root / "artifacts/operations/drift_alert_validation.json", payload)
            findings = validate_checkout_authority_pins(root, self._contract())
            self.assertTrue(any("undeclared checkout authority key" in item for item in findings))


if __name__ == "__main__":
    unittest.main()

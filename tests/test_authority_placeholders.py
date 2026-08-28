"""Tests for the authority-placeholder validator."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import validate_authority_placeholders  # noqa: E402


class AuthorityPlaceholderValidatorTests(unittest.TestCase):
    def _write(self, root: Path, relative: str, document: dict) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((json.dumps(document, indent=2) + "\n").encode("utf-8"))

    def test_repository_has_no_authority_placeholders(self) -> None:
        self.assertEqual(validate_authority_placeholders.validate(ROOT), [])

    def test_allowed_stale_fixture_still_contains_a_placeholder(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "stale_placeholder_contract.json"
        self.assertIn("BAT-XXX", fixture.read_text(encoding="utf-8"))
        self.assertIn(
            "tests/fixtures/stale_placeholder_contract.json",
            validate_authority_placeholders.ALLOWED_PLACEHOLDER_PATHS,
        )

    def test_rejects_placeholder_jira_key(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._write(
                root,
                "configs/example_contract.json",
                {"contract_id": "BAT-XXX-EXAMPLE-V1", "jira_key": "BAT-XXX"},
            )
            findings = validate_authority_placeholders.validate(root)
            self.assertTrue(
                any(item.startswith("AUTHORITY_PLACEHOLDER_PRESENT") for item in findings),
                findings,
            )
            self.assertTrue(
                any(item.startswith("AUTHORITY_KEY_PLACEHOLDER") for item in findings),
                findings,
            )

    def test_rejects_malformed_owner_key(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._write(root, "configs/example_contract.json", {"jira_key": "JIRA-1"})
            findings = validate_authority_placeholders.validate(root)
            self.assertTrue(
                any(item.startswith("AUTHORITY_JIRA_KEY_MALFORMED") for item in findings),
                findings,
            )

    def test_accepts_real_owner_and_unset_sentinel(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._write(root, "configs/real_contract.json", {"jira_key": "BAT-649"})
            self._write(
                root,
                "artifacts/pending_evidence.json",
                {"jira_key": "PENDING_LIVE_SYNCHRONIZATION"},
            )
            self.assertEqual(validate_authority_placeholders.validate(root), [])

    def test_excludes_immutable_captured_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._write(root, "jira/snapshots/legacy/STATE.json", {"jira_key": "BAT-XXX"})
            self.assertEqual(validate_authority_placeholders.validate(root), [])


if __name__ == "__main__":
    unittest.main()

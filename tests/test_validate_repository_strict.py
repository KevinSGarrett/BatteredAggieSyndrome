from __future__ import annotations

import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from tools.audit_protected_split_exposure import AUDIT_PATH, validate_audit  # noqa: E402
from tools import validate_repository  # noqa: E402


class ValidateRepositoryStrictTests(unittest.TestCase):
    def test_strict_invokes_validate_audit_on_committed_file(self) -> None:
        committed = json.loads((ROOT / AUDIT_PATH).read_text(encoding="utf-8"))
        stdout = io.StringIO()
        with mock.patch(
            "tools.validate_repository.validate_audit",
            wraps=validate_audit,
        ) as mocked:
            with mock.patch.object(sys, "argv", ["validate_repository.py", "--repo-root", str(ROOT), "--strict"]):
                with mock.patch("sys.stdout", stdout):
                    validate_repository.main()
        mocked.assert_called()
        payload, repo_root = mocked.call_args.args[:2]
        self.assertEqual(payload["artifact_identity"], committed["artifact_identity"])
        self.assertEqual(payload["schema_version"], committed["schema_version"])
        self.assertEqual(repo_root, ROOT)
        self.assertNotIn("protected_split_audit", stdout.getvalue())

    def test_strict_missing_audit_becomes_a_finding(self) -> None:
        stdout = io.StringIO()
        with mock.patch("tools.validate_repository.AUDIT_PATH", Path("missing_protected_split_exposure_audit.json")):
            with mock.patch.object(sys, "argv", ["validate_repository.py", "--repo-root", str(ROOT), "--strict"]):
                with mock.patch("sys.stdout", stdout):
                    exit_code = validate_repository.main()
        self.assertEqual(exit_code, 1)
        self.assertIn("protected_split_audit", stdout.getvalue())
        self.assertIn("missing committed audit", stdout.getvalue())

    def test_strict_validate_audit_error_becomes_a_finding(self) -> None:
        stdout = io.StringIO()
        with mock.patch(
            "tools.validate_repository.validate_audit",
            side_effect=ValueError("forced audit failure"),
        ):
            with mock.patch.object(sys, "argv", ["validate_repository.py", "--repo-root", str(ROOT), "--strict"]):
                with mock.patch("sys.stdout", stdout):
                    exit_code = validate_repository.main()
        self.assertEqual(exit_code, 1)
        self.assertIn("protected_split_audit", stdout.getvalue())
        self.assertIn("forced audit failure", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()

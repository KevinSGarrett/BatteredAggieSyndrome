from __future__ import annotations

import io
import json
import os
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
    def _run_main_fast_strict(self, stdout: io.StringIO) -> int:
        with mock.patch("tools.validate_repository.validate_required_structure", return_value=[]):
            with mock.patch("tools.validate_repository.scan_forbidden", return_value=[]):
                with mock.patch("tools.validate_repository.scan_secrets", return_value=[]):
                    with mock.patch("tools.validate_repository.validate_manifest", return_value=[]):
                        with mock.patch.object(Path, "rglob", return_value=iter(())):
                            with mock.patch.dict(
                                os.environ,
                                {"AGGIE_ANALYTICS_VALIDATE_REPOSITORY_FAST": "1"},
                                clear=False,
                            ):
                                with mock.patch.object(
                                    sys,
                                    "argv",
                                    ["validate_repository.py", "--repo-root", str(ROOT), "--strict"],
                                ):
                                    with mock.patch("sys.stdout", stdout):
                                        return validate_repository.main()

    def test_strict_invokes_validate_audit_on_committed_file(self) -> None:
        committed = json.loads((ROOT / AUDIT_PATH).read_text(encoding="utf-8"))
        stdout = io.StringIO()
        with mock.patch(
            "tools.validate_repository.validate_audit",
            wraps=validate_audit,
        ) as mocked:
            self._run_main_fast_strict(stdout)
        mocked.assert_called()
        payload, repo_root = mocked.call_args.args[:2]
        self.assertEqual(payload["artifact_identity"], committed["artifact_identity"])
        self.assertEqual(payload["schema_version"], committed["schema_version"])
        self.assertEqual(repo_root, ROOT)

    def test_strict_missing_audit_becomes_a_finding(self) -> None:
        stdout = io.StringIO()
        with mock.patch("tools.validate_repository.AUDIT_PATH", Path("missing_protected_split_exposure_audit.json")):
            exit_code = self._run_main_fast_strict(stdout)
        self.assertEqual(exit_code, 1)
        self.assertIn("protected_split_audit", stdout.getvalue())
        self.assertIn("missing committed audit", stdout.getvalue())

    def test_strict_validate_audit_error_becomes_a_finding(self) -> None:
        stdout = io.StringIO()
        with mock.patch(
            "tools.validate_repository.validate_audit",
            side_effect=ValueError("forced audit failure"),
        ):
            exit_code = self._run_main_fast_strict(stdout)
        self.assertEqual(exit_code, 1)
        self.assertIn("protected_split_audit", stdout.getvalue())
        self.assertIn("forced audit failure", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()

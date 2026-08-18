from __future__ import annotations

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
        with mock.patch(
            "tools.audit_protected_split_exposure.validate_audit",
            wraps=validate_audit,
        ) as mocked:
            with mock.patch.object(sys, "argv", ["validate_repository.py", "--repo-root", str(ROOT), "--strict"]):
                exit_code = validate_repository.main()
        self.assertEqual(exit_code, 0)
        mocked.assert_called()
        payload = mocked.call_args.args[0]
        self.assertEqual(payload["artifact_identity"], committed["artifact_identity"])
        self.assertEqual(payload["schema_version"], committed["schema_version"])
        self.assertEqual(mocked.call_args.args[1], ROOT)

    def test_strict_missing_audit_becomes_a_finding(self) -> None:
        with mock.patch("tools.audit_protected_split_exposure.AUDIT_PATH", Path("missing_protected_split_exposure_audit.json")):
            with mock.patch.object(sys, "argv", ["validate_repository.py", "--repo-root", str(ROOT), "--strict"]):
                exit_code = validate_repository.main()
        self.assertEqual(exit_code, 1)

    def test_strict_validate_audit_error_becomes_a_finding(self) -> None:
        with mock.patch(
            "tools.audit_protected_split_exposure.validate_audit",
            side_effect=ValueError("forced audit failure"),
        ):
            with mock.patch.object(sys, "argv", ["validate_repository.py", "--repo-root", str(ROOT), "--strict"]):
                exit_code = validate_repository.main()
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()

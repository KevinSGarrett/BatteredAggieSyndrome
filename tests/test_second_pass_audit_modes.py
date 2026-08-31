from __future__ import annotations

import hashlib
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.validate_jira_control_plane import validate as validate_jira_control_plane  # noqa: E402


def _load_module():
    path = ROOT / "jira/tools/run_second_pass_audit.py"
    tools_path = str(ROOT / "jira/tools")
    if tools_path not in sys.path:
        sys.path.insert(0, tools_path)
    spec = importlib.util.spec_from_file_location("run_second_pass_audit_test_module", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SecondPassAuditModeTests(unittest.TestCase):
    def test_validate_mode_is_read_only(self) -> None:
        module = _load_module()
        checks = {
            key: {"status": "PASS", "detail": "ok", "evidence": []}
            for _, _, key in module.SECTIONS
        }
        metrics = {
            "issue_count": 1,
            "work_packet_count": 1,
            "post_wave_count": 1,
            "atomic_count": 1,
            "aggregate_count": 0,
            "protected_touch_overlap_count": 0,
            "source_reference_count": 0,
            "import": {"issue_rows": 1},
        }
        with mock.patch.object(module, "run_checks", return_value=(checks, [], metrics)):
            with mock.patch.object(module.Path, "write_text", side_effect=AssertionError("write_text called")):
                with mock.patch.object(module, "write_csv", side_effect=AssertionError("write_csv called")):
                    with mock.patch.object(module, "rebuild_file_manifest", side_effect=AssertionError("manifest rebuild called")):
                        with mock.patch.object(sys, "argv", ["run_second_pass_audit.py", "--mode", "validate"]):
                            with self.assertRaises(SystemExit) as raised:
                                module.main()
        self.assertEqual(raised.exception.code, 0)


class SecondPassValidatorPurityTests(unittest.TestCase):
    """Strict repository validation must never rewrite tracked Jira authority.

    ``jira/tools/validate_second_pass.py`` previously ran ``strict_validate`` with
    ``write_reports=True``, so every read-only control-plane validation stamped the
    current wall-clock date into ``jira/validation/SECOND_PASS_AUDIT_RESULTS.json``
    and rebuilt Jira derivatives as a side effect of validating them.
    """

    VALIDATION_DIR = ROOT / "jira" / "validation"

    def _validation_digest(self) -> dict[str, str]:
        digest: dict[str, str] = {}
        for path in sorted(self.VALIDATION_DIR.rglob("*")):
            if path.is_file():
                digest[path.relative_to(ROOT).as_posix()] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
        return digest

    def test_validate_second_pass_defaults_to_read_only(self) -> None:
        source = (ROOT / "jira/tools/validate_second_pass.py").read_text(encoding="utf-8")
        self.assertIn('default="validate"', source)
        self.assertNotIn("write_reports=True", source)

    def test_generator_template_cannot_reintroduce_writing_validator(self) -> None:
        """The emitted validator is regenerated from an embedded template."""
        source = (ROOT / "jira/tools/second_pass_hardening.py").read_text(encoding="utf-8")
        marker = '"validate_second_pass.py": """'
        start = source.index(marker) + len(marker)
        template = source[start : source.index('""",', start)]
        self.assertIn('write_reports=args.mode == "materialize"', template)
        self.assertNotIn("write_reports=True", template)

    def test_control_plane_validator_invokes_read_only_mode(self) -> None:
        source = (ROOT / "tools/validate_jira_control_plane.py").read_text(encoding="utf-8")
        self.assertIn('"--mode", "validate"', source)

    def test_control_plane_validation_leaves_jira_validation_byte_identical(self) -> None:
        before = self._validation_digest()
        findings = validate_jira_control_plane(ROOT)
        self.assertEqual([], findings)
        after = self._validation_digest()
        changed = sorted(
            path for path in before.keys() | after.keys() if before.get(path) != after.get(path)
        )
        self.assertEqual([], changed, f"read-only validation mutated: {changed}")

    def test_repeated_validation_returns_the_same_semantic_result(self) -> None:
        first = validate_jira_control_plane(ROOT)
        second = validate_jira_control_plane(ROOT)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

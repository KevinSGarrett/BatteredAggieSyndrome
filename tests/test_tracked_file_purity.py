from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.validation.tracked_file_purity import (  # noqa: E402
    BASELINE_STALE,
    CREATION,
    DELETION,
    LINE_ENDING_BASELINE_RELATIVE,
    MIXED_ENDINGS,
    MUTATION,
    PurityReport,
    PurityViolation,
    assert_pure,
    canonical_digest,
    line_ending_findings,
    mixed_line_ending_paths,
    read_line_ending_baseline,
    run_and_compare,
    tracked_paths,
)


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class TemporaryRepository:
    """A throwaway git repository, so detector tests never touch the real tree."""

    def __enter__(self) -> Path:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        _git("init", "-q", cwd=root)
        _git("config", "user.email", "purity@test.invalid", cwd=root)
        _git("config", "user.name", "Purity Test", cwd=root)
        (root / "tracked.json").write_bytes(b'{"value": 1}\n')
        (root / "notes.txt").write_bytes(b"alpha\n")
        _git("add", "-A", cwd=root)
        _git("commit", "-q", "-m", "seed", cwd=root)
        self.root = root
        return root

    def __exit__(self, *exc: object) -> None:
        self._tmp.cleanup()


class CanonicalDigestTests(unittest.TestCase):
    def test_crlf_and_lf_text_hash_identically(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lf = Path(td) / "a.json"
            crlf = Path(td) / "b.json"
            lf.write_bytes(b'{"k": 1}\n{"k": 2}\n')
            crlf.write_bytes(b'{"k": 1}\r\n{"k": 2}\r\n')
            self.assertEqual(canonical_digest(lf), canonical_digest(crlf))

    def test_binary_bytes_are_not_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            first = Path(td) / "a.bin"
            second = Path(td) / "b.bin"
            first.write_bytes(b"\x00\r\n\x01")
            second.write_bytes(b"\x00\n\x01")
            self.assertNotEqual(canonical_digest(first), canonical_digest(second))

    def test_a_real_content_change_still_changes_the_digest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "a.json"
            path.write_bytes(b'{"k": 1}\n')
            before = canonical_digest(path)
            path.write_bytes(b'{"k": 2}\n')
            self.assertNotEqual(before, canonical_digest(path))


class DetectorTests(unittest.TestCase):
    def test_a_read_only_command_is_reported_pure(self) -> None:
        with TemporaryRepository() as root:
            report = run_and_compare(
                [sys.executable, "-c", "print('read only')"], repo_root=root
            )
            self.assertTrue(report.pure)
            self.assertEqual(report.exit_code, 0)
            self.assertEqual(report.tracked_file_count, 2)
            assert_pure(report)

    def test_a_command_that_rewrites_a_tracked_file_is_caught(self) -> None:
        with TemporaryRepository() as root:
            report = run_and_compare(
                [
                    sys.executable,
                    "-c",
                    "import pathlib; pathlib.Path('tracked.json').write_bytes(b'{\"value\": 2}\\n')",
                ],
                repo_root=root,
            )
            self.assertFalse(report.pure)
            self.assertEqual(report.mutated, ("tracked.json",))
            self.assertIn(f"{MUTATION}:tracked.json", report.findings())
            with self.assertRaises(PurityViolation):
                assert_pure(report)

    def test_a_line_ending_only_rewrite_of_tracked_text_is_not_a_false_positive(self) -> None:
        with TemporaryRepository() as root:
            report = run_and_compare(
                [
                    sys.executable,
                    "-c",
                    "import pathlib; p=pathlib.Path('tracked.json'); p.write_bytes(p.read_bytes().replace(b'\\n', b'\\r\\n'))",
                ],
                repo_root=root,
            )
            self.assertTrue(report.pure)

    def test_a_command_that_deletes_a_tracked_file_is_caught(self) -> None:
        with TemporaryRepository() as root:
            report = run_and_compare(
                [
                    sys.executable,
                    "-c",
                    "import pathlib; pathlib.Path('notes.txt').unlink()",
                ],
                repo_root=root,
            )
            self.assertFalse(report.pure)
            self.assertEqual(report.deleted, ("notes.txt",))
            self.assertIn(f"{DELETION}:notes.txt", report.findings())

    def test_a_command_that_adds_a_tracked_file_is_caught(self) -> None:
        with TemporaryRepository() as root:
            report = run_and_compare(
                [
                    "git",
                    "-c",
                    "user.email=purity@test.invalid",
                    "-c",
                    "user.name=Purity Test",
                    "commit",
                    "-q",
                    "--allow-empty",
                    "-m",
                    "noop",
                ],
                repo_root=root,
            )
            self.assertTrue(report.pure)

            report = run_and_compare(
                [
                    sys.executable,
                    "-c",
                    "import pathlib, subprocess; pathlib.Path('extra.json').write_bytes(b'{}\\n');"
                    " subprocess.run(['git', 'add', 'extra.json'], check=True)",
                ],
                repo_root=root,
            )
            self.assertIn("extra.json", report.created)
            self.assertIn(f"{CREATION}:extra.json", report.findings())

    def test_a_failing_command_still_yields_a_purity_verdict(self) -> None:
        with TemporaryRepository() as root:
            report = run_and_compare(
                [sys.executable, "-c", "raise SystemExit(3)"], repo_root=root
            )
            self.assertEqual(report.exit_code, 3)
            self.assertTrue(report.pure)

    def test_the_report_serializes_its_verdict(self) -> None:
        report = PurityReport(
            command=("probe",), exit_code=0, tracked_file_count=1, mutated=("a.json",)
        )
        payload = report.as_dict()
        self.assertEqual(payload["result"], "FAIL")
        self.assertEqual(payload["mutated"], ["a.json"])


class LineEndingContractTests(unittest.TestCase):
    def test_a_mixed_ending_file_is_detected(self) -> None:
        with TemporaryRepository() as root:
            (root / "mixed.json").write_bytes(b'{"a": 1}\r\n{"b": 2}\n')
            _git("add", "-A", cwd=root)
            self.assertIn("mixed.json", mixed_line_ending_paths(root))

    def test_a_uniform_file_is_not_detected(self) -> None:
        with TemporaryRepository() as root:
            (root / "crlf.json").write_bytes(b'{"a": 1}\r\n{"b": 2}\r\n')
            _git("add", "-A", cwd=root)
            self.assertNotIn("crlf.json", mixed_line_ending_paths(root))

    def test_a_new_mixed_ending_file_fails_closed_against_the_baseline(self) -> None:
        with TemporaryRepository() as root:
            baseline = root / LINE_ENDING_BASELINE_RELATIVE
            baseline.parent.mkdir(parents=True, exist_ok=True)
            baseline.write_text(
                json.dumps({"mixed_line_ending_paths": []}), encoding="utf-8"
            )
            (root / "mixed.json").write_bytes(b'{"a": 1}\r\n{"b": 2}\n')
            _git("add", "-A", cwd=root)
            self.assertIn(f"{MIXED_ENDINGS}:mixed.json", line_ending_findings(root))

    def test_a_baselined_file_is_tolerated_but_disclosed(self) -> None:
        with TemporaryRepository() as root:
            baseline = root / LINE_ENDING_BASELINE_RELATIVE
            baseline.parent.mkdir(parents=True, exist_ok=True)
            baseline.write_text(
                json.dumps({"mixed_line_ending_paths": ["mixed.json"]}), encoding="utf-8"
            )
            (root / "mixed.json").write_bytes(b'{"a": 1}\r\n{"b": 2}\n')
            _git("add", "-A", cwd=root)
            self.assertEqual(line_ending_findings(root), [])
            self.assertIn("mixed.json", read_line_ending_baseline(root))

    def test_a_baseline_entry_that_was_fixed_is_reported_as_stale(self) -> None:
        with TemporaryRepository() as root:
            baseline = root / LINE_ENDING_BASELINE_RELATIVE
            baseline.parent.mkdir(parents=True, exist_ok=True)
            baseline.write_text(
                json.dumps({"mixed_line_ending_paths": ["notes.txt"]}), encoding="utf-8"
            )
            _git("add", "-A", cwd=root)
            self.assertIn(f"{BASELINE_STALE}:notes.txt", line_ending_findings(root))


class RepositoryContractTests(unittest.TestCase):
    def test_the_committed_baseline_matches_the_repository(self) -> None:
        self.assertEqual(line_ending_findings(REPO_ROOT), [])

    def test_the_repository_reports_a_nonempty_tracked_set(self) -> None:
        self.assertGreater(len(tracked_paths(REPO_ROOT)), 1000)


if __name__ == "__main__":
    unittest.main()

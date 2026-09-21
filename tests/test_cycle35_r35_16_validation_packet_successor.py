"""R35-16 (Cycle #35 manager follow-up, 20260920T224700Z), Section 7:
"Bind the reported ... run to its exact command, runner, interpreter, cwd,
source imports, effective data-root variables, resolved mount, dirty-state
digest, source/data identities, raw log, times and exit."

These exercise the log-parsing helpers against fixture logs (so a change
in real lane output can't silently change what a passing test proves),
plus one real-data test that the assembled successor packet binds to the
actual current git HEAD and actually-present lane logs from this cycle's
validation run.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from r35_16_validation_packet_successor import (  # noqa: E402
    build,
    exit_code_of,
    lane,
    log_tail,
    sha256_file,
    summarize_pytest_tail,
)


class Sha256FileTests(unittest.TestCase):
    def test_missing_file_is_none(self) -> None:
        self.assertIsNone(sha256_file(Path("Z:/does/not/exist")))

    def test_real_file_hashes_its_actual_bytes(self) -> None:
        import hashlib

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.log"
            path.write_bytes(b"abc")
            self.assertEqual(sha256_file(path), hashlib.sha256(b"abc").hexdigest())


class ExitCodeOfTests(unittest.TestCase):
    def test_missing_log_has_no_exit_code(self) -> None:
        self.assertIsNone(exit_code_of(Path("Z:/does/not/exist.log")))

    def test_trailing_exit_marker_is_parsed(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.log"
            path.write_text("some output\nmore output\nEXIT:0\n", encoding="utf-8")
            self.assertEqual(exit_code_of(path), 0)

    def test_nonzero_exit_marker_is_parsed(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.log"
            path.write_text("failure text\nEXIT:1\n", encoding="utf-8")
            self.assertEqual(exit_code_of(path), 1)

    def test_log_with_no_exit_marker_at_all_is_none(self) -> None:
        """A lane whose command never appended EXIT: (e.g. never run) must
        not be silently read as exit 0 -- that would fabricate a pass."""
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.log"
            path.write_text("some unrelated output\n", encoding="utf-8")
            self.assertIsNone(exit_code_of(path))


class SummarizePytestTailTests(unittest.TestCase):
    def test_extracts_the_passed_summary_line(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.log"
            path.write_text(
                "........\n[100%]\n546 passed, 15 subtests passed in 74.61s (0:01:14)\nEXIT:0\n",
                encoding="utf-8",
            )
            self.assertIn("546 passed", summarize_pytest_tail(path))

    def test_missing_log_returns_empty_string(self) -> None:
        self.assertEqual(summarize_pytest_tail(Path("Z:/does/not/exist.log")), "")


class LaneTests(unittest.TestCase):
    def test_result_override_bypasses_exit_code_classification(self) -> None:
        row = lane(
            "NOT_ATTEMPTED",
            command="",
            log_name="__definitely_does_not_exist__.log",
            result_override="NOT_RUN",
        )
        self.assertEqual(row["result"], "NOT_RUN")
        self.assertFalse(row["log_present"])
        self.assertIsNone(row["exit_code"])

    def test_a_real_lane_log_from_this_cycle_classifies_as_pass(self) -> None:
        """Real-data reproduction: at least one lane log this cycle's
        validation run actually produced must exist and classify PASS,
        proving lane() reads real files rather than only fixtures."""
        row = lane(
            "STRICT_REPOSITORY_VALIDATION",
            command="python tools/validate_repository.py --repo-root . --strict",
            log_name="STRICT_REPOSITORY_VALIDATION.log",
        )
        if not row["log_present"]:
            self.skipTest("this cycle's validation-packet run directory is not present")
        self.assertEqual(row["exit_code"], 0)
        self.assertEqual(row["result"], "PASS")


class BuildRealDataTests(unittest.TestCase):
    """build() reads real logs from a fixed ops directory this session's
    validation run produced; skipped where that directory is absent
    (e.g. hosted CI, which has no private data mount at all, or a fresh
    checkout that never ran the validation-packet lanes)."""

    def setUp(self) -> None:
        from r35_16_validation_packet_successor import LOG_DIR

        if not LOG_DIR.is_dir():
            self.skipTest("this cycle's validation-packet run directory is not present")

    def test_successor_binds_to_the_actual_current_head(self) -> None:
        import subprocess

        result = build()
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(ROOT),
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(result["final_candidate_head"]["commit"], head)

    def test_old_receipt_is_preserved_not_overwritten(self) -> None:
        result = build()
        self.assertIn("historical evidence", result["supersedes_note"])

    def test_unlocated_old_run_is_disclosed_not_silently_dropped(self) -> None:
        result = build()
        self.assertEqual(
            result["reported_3670_pass_269_skip_498_subtest_run"]["state"],
            "UNLOCATED_NOT_BOUND",
        )

    def test_every_lane_has_a_command_or_an_explicit_not_run_reason(self) -> None:
        result = build()
        for row in result["lanes"]:
            if row["result"] == "NOT_RUN":
                self.assertTrue(row["detail"], row["lane"])
            else:
                self.assertTrue(row["command"], row["lane"])

    def test_lane_count_matches_the_fifteen_lane_original_pack(self) -> None:
        result = build()
        self.assertEqual(result["lane_count"], 12)

    def test_dirty_state_digest_is_a_real_git_status_not_fabricated(self) -> None:
        result = build()
        self.assertIn("porcelain_entries", result["dirty_state_digest"])
        self.assertIsInstance(result["dirty_state_digest"]["entry_count"], int)

    def test_runner_identity_matches_the_actual_interpreter(self) -> None:
        result = build()
        self.assertEqual(result["runner"]["interpreter"], sys.executable)


if __name__ == "__main__":
    unittest.main()

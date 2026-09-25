"""Cycle #37 - Attempt #2 - ACTUAL_STATE

MF37-04 regressions for :mod:`aggie_analytics.validation.lane_harness`.

Each test names the exact loss it prevents. The two the manager reproduced
are first: distinct fully qualified failures sharing a method name must not
collapse into one identity, and a suite in which every test was skipped must
not be reported as a pass because unittest exited zero.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from aggie_analytics.validation.lane_harness import (  # noqa: E402
    BLOCKED,
    FAIL,
    PASS,
    UNSATISFIED,
    classify,
    parse_unittest,
    reconcile,
    run_lane,
)


# The manager's exact probe input, kept verbatim so this test fails if the
# parser ever regresses to the behaviour that produced the finding.
MANAGER_DUPLICATE_IDENTITY_INPUT = (
    "ERROR: test_shared (suite_alpha.Alpha.test_shared)\n"
    "ERROR: test_shared (suite_beta.Beta.test_shared)\n"
    "Ran 2 tests in 0.01s\n"
    "FAILED (errors=2)\n"
)


class DistinctIdentities(unittest.TestCase):
    def test_same_method_name_in_two_modules_stays_two_failures(self) -> None:
        parsed = parse_unittest(MANAGER_DUPLICATE_IDENTITY_INPUT)
        self.assertEqual(
            parsed["failed_or_errored_identities"],
            ["suite_alpha.Alpha.test_shared", "suite_beta.Beta.test_shared"],
        )
        self.assertEqual(parsed["failed_or_errored_count"], 2)

    def test_parsed_count_agrees_with_the_unittest_summary(self) -> None:
        parsed = parse_unittest(MANAGER_DUPLICATE_IDENTITY_INPUT)
        self.assertTrue(reconcile(parsed)["consistent"], reconcile(parsed))

    def test_a_merged_identity_set_is_reported_as_inconsistent(self) -> None:
        # Simulate the old behaviour to prove the reconciliation would have
        # caught it: one identity parsed against a summary declaring two.
        merged = dict(parse_unittest(MANAGER_DUPLICATE_IDENTITY_INPUT))
        merged["failed_or_errored_count"] = 1
        merged["failed_or_errored_identities"] = ["test_shared"]
        report = reconcile(merged)
        self.assertFalse(report["consistent"])
        self.assertIn("2 failure/error", report["problems"][0])

    def test_module_class_and_method_are_kept_separately(self) -> None:
        row = parse_unittest(
            "FAIL: test_x (pkg.mod.Case.test_x)\nRan 1 test in 0.0s\nFAILED (failures=1)\n"
        )["failed_or_errored"][0]
        self.assertEqual(row["module"], "pkg.mod")
        self.assertEqual(row["class"], "Case")
        self.assertEqual(row["method"], "test_x")

    def test_import_errors_are_identified_not_subtracted(self) -> None:
        parsed = parse_unittest(
            "ERROR: broken_module (unittest.loader._FailedTest.broken_module)\n"
            "Ran 1 test in 0.0s\nFAILED (errors=1)\n"
        )
        self.assertEqual(parsed["failed_or_errored_count"], 1)
        self.assertEqual(
            parsed["import_error_identities"],
            ["unittest.loader._FailedTest.broken_module"],
        )

    def test_subtest_failures_are_distinct_from_their_parent(self) -> None:
        parsed = parse_unittest(
            "FAIL: test_many (pkg.Case.test_many) [i=1]\n"
            "FAIL: test_many (pkg.Case.test_many) [i=2]\n"
            "Ran 1 test in 0.0s\nFAILED (failures=2)\n"
        )
        self.assertEqual(parsed["failed_or_errored_count"], 2)
        self.assertEqual(len(parsed["subtest_identities"]), 2)

    def test_skips_keep_their_qualified_identity_and_reason(self) -> None:
        parsed = parse_unittest(
            "test_a (pkg.Case.test_a) ... skipped 'no privilege'\n"
            "Ran 1 test in 0.0s\nOK (skipped=1)\n"
        )
        self.assertEqual(parsed["skipped"][0]["identity"], "pkg.Case.test_a")
        self.assertEqual(parsed["skipped"][0]["reason"], "no privilege")


class AllSkippedIsNotAPass(unittest.TestCase):
    ALL_SKIPPED = (
        "test_not_executed (test_all_skipped.Skipped.test_not_executed) ... "
        "skipped 'manager negative control'\n"
        "\nRan 1 test in 0.000s\n\nOK (skipped=1)\n"
    )

    def test_exit_zero_with_every_test_skipped_is_unsatisfied(self) -> None:
        outcome = classify(kind="TEST", exit_code=0, parsed=parse_unittest(self.ALL_SKIPPED))
        self.assertEqual(outcome.state, UNSATISFIED)
        self.assertIn("skipped", outcome.reason)

    def test_a_check_lane_may_legitimately_run_no_test(self) -> None:
        self.assertEqual(classify(kind="CHECK", exit_code=0, parsed=None).state, PASS)

    def test_zero_discovered_tests_is_unsatisfied(self) -> None:
        outcome = classify(
            kind="TEST", exit_code=0, parsed=parse_unittest("Ran 0 tests in 0.0s\n\nOK\n")
        )
        self.assertEqual(outcome.state, UNSATISFIED)

    def test_one_executed_test_beside_a_skip_is_a_pass(self) -> None:
        parsed = parse_unittest(
            "test_a (pkg.Case.test_a) ... ok\n"
            "test_b (pkg.Case.test_b) ... skipped 'n/a'\n"
            "Ran 2 tests in 0.0s\n\nOK (skipped=1)\n"
        )
        self.assertEqual(parsed["executed_test_count"], 1)
        self.assertEqual(classify(kind="TEST", exit_code=0, parsed=parsed).state, PASS)

    def test_a_nonzero_exit_is_a_failure_whatever_was_parsed(self) -> None:
        self.assertEqual(classify(kind="TEST", exit_code=1, parsed=None).state, FAIL)

    def test_an_unfinished_command_is_blocked_not_passed(self) -> None:
        self.assertEqual(classify(kind="TEST", exit_code=None, parsed=None).state, BLOCKED)


class RealSubprocessLane(unittest.TestCase):
    """The classification has to hold against a real interpreter, not a string."""

    def _write(self, directory: Path, name: str, body: str) -> None:
        (directory / name).write_text(body, encoding="utf-8")

    def test_a_real_all_skipped_suite_exits_zero_and_is_still_unsatisfied(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            work = Path(raw)
            self._write(
                work,
                "test_all_skipped.py",
                "import unittest\n\n"
                "class Skipped(unittest.TestCase):\n"
                "    @unittest.skip('negative control')\n"
                "    def test_not_executed(self):\n"
                "        raise AssertionError('never reached')\n",
            )
            record = run_lane(
                "all_skipped_control",
                [sys.executable, "-B", "-m", "unittest", "-v", "test_all_skipped"],
                cwd=work,
                log_dir=work / "logs",
                kind="TEST",
            )
        self.assertEqual(record["exit_code"], 0)
        self.assertEqual(record["result"], UNSATISFIED)
        self.assertFalse(record["satisfies_acceptance"])

    def test_two_real_same_named_failures_stay_two(self) -> None:
        body = (
            "import unittest\n\n"
            "class {cls}(unittest.TestCase):\n"
            "    def test_shared(self):\n"
            "        raise AssertionError('{cls}')\n"
        )
        with tempfile.TemporaryDirectory() as raw:
            work = Path(raw)
            self._write(work, "suite_alpha.py", body.format(cls="Alpha"))
            self._write(work, "suite_beta.py", body.format(cls="Beta"))
            record = run_lane(
                "duplicate_name_control",
                [sys.executable, "-B", "-m", "unittest", "-v", "suite_alpha", "suite_beta"],
                cwd=work,
                log_dir=work / "logs",
                kind="TEST",
            )
        self.assertEqual(record["result"], FAIL)
        self.assertEqual(record["unittest"]["failed_or_errored_count"], 2)
        self.assertEqual(
            sorted(record["unittest"]["failed_or_errored_identities"]),
            ["suite_alpha.Alpha.test_shared", "suite_beta.Beta.test_shared"],
        )

    def test_the_raw_log_is_written_before_any_classification(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            work = Path(raw)
            record = run_lane(
                "echo_control",
                [sys.executable, "-B", "-c", "print('hello from the lane')"],
                cwd=work,
                log_dir=work / "logs",
                kind="CHECK",
                parse=False,
            )
            log = Path(record["log_path"])
            self.assertTrue(log.is_file())
            self.assertIn("hello from the lane", log.read_text(encoding="utf-8"))
        self.assertGreater(record["log_bytes"], 0)

    def test_a_command_that_cannot_start_is_blocked_not_passed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            work = Path(raw)
            record = run_lane(
                "missing_binary",
                [str(work / "there-is-no-such-executable.exe")],
                cwd=work,
                log_dir=work / "logs",
                kind="CHECK",
                parse=False,
            )
        self.assertEqual(record["result"], BLOCKED)
        self.assertIsNone(record["exit_code"])


class ExistingConsumerUsesTheRepair(unittest.TestCase):
    """The repair has to reach the tool the cycle actually runs."""

    def test_c36_15_validation_delegates_to_the_shared_harness(self) -> None:
        source = (_REPO_ROOT / "tools" / "cycle36" / "c36_15_validation.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("from aggie_analytics.validation.lane_harness import", source)
        self.assertNotIn('re.compile(r"^(FAIL|ERROR):\\s+(\\S+)"', source)

    def test_c36_15_run_lane_classifies_an_all_skipped_lane_as_unsatisfied(self) -> None:
        spec = _REPO_ROOT / "tools" / "cycle36" / "c36_15_validation.py"
        with tempfile.TemporaryDirectory() as raw:
            work = Path(raw)
            (work / "test_all_skipped.py").write_text(
                "import unittest\n\n"
                "class Skipped(unittest.TestCase):\n"
                "    @unittest.skip('negative control')\n"
                "    def test_not_executed(self):\n"
                "        raise AssertionError('never reached')\n",
                encoding="utf-8",
            )
            script = (
                "import json,sys\n"
                f"sys.path.insert(0, {str(spec.parent)!r})\n"
                "import importlib.util\n"
                f"spec = importlib.util.spec_from_file_location('c36_15', {str(spec)!r})\n"
                "mod = importlib.util.module_from_spec(spec)\n"
                "spec.loader.exec_module(mod)\n"
                "from pathlib import Path\n"
                "rec = mod.run_lane('probe', [sys.executable,'-B','-m','unittest','-v',"
                "'test_all_skipped'], cwd=Path(sys.argv[1]), log_dir=Path(sys.argv[1])/'logs')\n"
                "print(json.dumps({'result': rec['result'], 'exit_code': rec['exit_code']}))\n"
            )
            completed = subprocess.run(
                [sys.executable, "-B", "-c", script, str(work)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = completed.stdout.strip().splitlines()[-1]
        self.assertIn(UNSATISFIED, payload, payload)


if __name__ == "__main__":
    unittest.main()


class PorcelainColumnsAreSignificant(unittest.TestCase):
    """W37R-08: stripping a porcelain line eats the first character of the path.

    ``git status --porcelain=v1`` is column-significant. An unstaged
    modification is ``" M path"`` with a *leading space*, so a helper that
    strips stdout before slicing ``line[3:]`` returns ``ools/...`` instead of
    ``tools/...`` -- and the per-file digest of that first dirty entry then
    resolves to ABSENT. The dirty-tree receipt was silently wrong about which
    file it had hashed.
    """

    def setUp(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "rework_lanes_under_test",
            _REPO_ROOT / "tools" / "cycle37" / "rework_lanes.py",
        )
        self.module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(self.module)

    def test_a_leading_space_status_keeps_the_whole_path(self) -> None:
        rows = self.module.parse_porcelain(" M tools/cycle37/rework_lanes.py\0")
        self.assertEqual(rows, [(" M", "tools/cycle37/rework_lanes.py")])

    def test_every_status_form_keeps_the_whole_path(self) -> None:
        payload = "\0".join(
            [
                " M src/a.py",
                "M  src/b.py",
                "?? tools/c.py",
                "A  tests/d.py",
                "MM src/e.py",
                " D src/f.py",
            ]
        ) + "\0"
        rows = self.module.parse_porcelain(payload)
        self.assertEqual(
            [path for _status, path in rows],
            ["src/a.py", "src/b.py", "tools/c.py", "tests/d.py", "src/e.py", "src/f.py"],
        )
        self.assertEqual([status for status, _ in rows],
                         [" M", "M ", "??", "A ", "MM", " D"])

    def test_an_empty_payload_is_an_empty_list_not_a_blank_row(self) -> None:
        self.assertEqual(self.module.parse_porcelain(""), [])
        self.assertEqual(self.module.parse_porcelain("\0"), [])


class CanonicalWriteWatchTests(unittest.TestCase):
    """W37R-66: a lane's read_only is measured on the canonical trees, never asserted."""

    def setUp(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "rework_lanes_watch_under_test",
            _REPO_ROOT / "tools" / "cycle37" / "rework_lanes.py",
        )
        self.module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(self.module)

    def test_created_rewritten_and_removed_entries_are_each_reported(self) -> None:
        import os

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "features"
            (root / "a").mkdir(parents=True)
            (root / "a" / "kept.json").write_text("{}", encoding="utf-8")
            (root / "a" / "rewritten.json").write_text("{}", encoding="utf-8")
            (root / "a" / "removed.json").write_text("{}", encoding="utf-8")
            before = self.module.canonical_snapshot(Path(tmp), ())
            os.utime(root / "a" / "rewritten.json", ns=(1, 1))
            (root / "a" / "removed.json").unlink()
            (root / "b").mkdir()
            (root / "b" / "created.json").write_text("{}", encoding="utf-8")
            writes = self.module.canonical_writes(before, self.module.canonical_snapshot(Path(tmp), ()))
        created = {row["path"] for row in writes["created"]}
        changed = {row["path"] for row in writes["changed"]}
        self.assertEqual(created, {"features/b", "features/b/created.json"})
        self.assertEqual({row["path"] for row in writes["removed"]}, {"features/a/removed.json"})
        self.assertIn("features/a/rewritten.json", changed)
        self.assertNotIn("features/a/kept.json", changed)
        self.assertEqual(writes["count"], len(writes["created"]) + len(writes["removed"]) + len(writes["changed"]))

    def test_excluded_areas_are_not_measured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "live").mkdir()
            (root / "kept").mkdir()
            before = self.module.canonical_snapshot(root, (root / "live",))
            (root / "live" / "status.json").write_text("{}", encoding="utf-8")
            after = self.module.canonical_snapshot(root, (root / "live",))
        self.assertEqual(self.module.canonical_writes(before, after)["count"], 0)
        self.assertNotIn("live", after)

    def test_an_untouched_tree_reports_no_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "features"
            root.mkdir()
            (root / "x.json").write_text("{}", encoding="utf-8")
            snapshot = self.module.canonical_snapshot(Path(tmp), ())
            self.assertEqual(self.module.canonical_writes(snapshot, self.module.canonical_snapshot(Path(tmp), ()))["count"], 0)


class InProcessLanesLogTheirChecks(unittest.TestCase):
    """W37R-70: START_BINDING and FINAL_PACKET run their raw checks as logged commands."""

    def setUp(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "rework_lanes_logged_checks_under_test",
            _REPO_ROOT / "tools" / "cycle37" / "rework_lanes.py",
        )
        self.module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(self.module)

    def _probe(self, root: Path) -> subprocess.CompletedProcess:
        import os

        env = dict(os.environ, PYTHONPATH=str(_REPO_ROOT / "src"))
        return subprocess.run(
            [sys.executable, "-B", "-c", self.module.MODULE_ORIGIN_PROBE, str(root), "aggie_analytics.atomic_io"],
            capture_output=True, text=True, env=env, check=False,
        )

    def test_a_module_inside_the_root_passes(self) -> None:
        result = self._probe(_REPO_ROOT / "src")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("outside the selected worktree: none", result.stdout)

    def test_a_module_outside_the_root_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self._probe(Path(tmp))
        self.assertEqual(result.returncode, 1)
        self.assertIn("aggie_analytics.atomic_io", result.stdout.splitlines()[-1])

    def test_the_receipt_listing_names_missing_and_present_receipts(self) -> None:
        import json

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "binding.json").write_text(
                json.dumps({"result": "PASS", "source_binding": {"head": "abc"}}), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-B", "-c", self.module.RECEIPT_LISTING, tmp, "binding", "packet"],
                capture_output=True, text=True, check=False,
            )
        lines = result.stdout.splitlines()
        self.assertEqual(result.returncode, 0)
        self.assertTrue(lines[0].startswith("binding PASS abc "))
        self.assertEqual(lines[1], "packet NO_RECEIPT")

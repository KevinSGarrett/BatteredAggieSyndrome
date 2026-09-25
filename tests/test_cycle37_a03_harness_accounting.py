"""Cycle #37 — Attempt #3 — exact import binding and test accounting for the full-suite lanes (MF37A02-05).

Two defects the Attempt #2 manager reproduced:

* the full mounted suite failed to import ``tools`` in ``test_acceptance_governance`` because the lane put
  ``tests`` and ``src`` on the path but not the repository root;
* the final lane's own receipt said ``consistent=false``: the summary declared 17 skips and the parser read 13.

The four skips the parser missed are reproduced here verbatim from that raw log
(``full-final-mounted__full_suite_final.log``): one split across two lines by the test's docstring and three
whose reasons ``repr`` printed in double quotes. The census runner then reconciles text, per-outcome records and
unittest's own counts by identity, and refuses a run that imported source from another checkout.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from aggie_analytics.validation.lane_harness import (  # noqa: E402
    FAIL,
    PASS,
    parse_unittest,
    reconcile,
    reconcile_census,
    run_lane,
)

#: The four skip lines the Attempt #2 parser missed, verbatim from the raw Attempt #2 final log (lines 918-919,
#: 4292, 5880 and 5900), with the summary they were printed under.
MISSED_SKIPS = (
    "test_active_manifest_declares_only_paths_it_owns (test_cycle23_routing_manifest_coverage."
    "Cycle23RoutingManifestCoverageTest.test_active_manifest_declares_only_paths_it_owns)\n"
    "A manifest may declare its own material paths plus process-only paths. ... skipped 'active routing owner "
    "None is not a Cycle #23 owner'\n"
    "test_hypothesis_is_an_explicit_optional_test_dependency (test_open_source_properties.OpenSourcePropertyTests."
    "test_hypothesis_is_an_explicit_optional_test_dependency) ... skipped \"install the 'test' optional "
    "dependency\"\n"
    "test_repository_rejects_symlinked_game_directory (test_w22_product_serving.W22ProductServingTests."
    "test_repository_rejects_symlinked_game_directory) ... skipped \"directory symlinks unavailable: [WinError "
    "1314] A required privilege is not held by the client: 'C:\\\\\\\\Users\\\\\\\\x' -> 'C:\\\\\\\\Users\\\\\\\\y'\"\n"
    "test_recursive_cleanup_rejects_symlink_or_junction_alias (test_w23_operations.W23OperationsTests."
    "test_recursive_cleanup_rejects_symlink_or_junction_alias) ... skipped \"directory symlink unavailable: "
    "[WinError 1314] A required privilege is not held by the client: 'a' -> 'b'\"\n"
    "setUpClass (test_week1_2026_authority_enrichment.MaterializedArtifactTests) ... skipped 'Cycle26 forbids "
    "rematerializing the frozen Week1 schedule identity'\n"
    "\nRan 4 tests in 0.1s\n\nOK (skipped=5)\n"
)


class TheFourMissedSkipsAreParsed(unittest.TestCase):
    def setUp(self) -> None:
        self.parsed = parse_unittest(MISSED_SKIPS)

    def test_every_skip_the_summary_declares_is_parsed_by_identity(self) -> None:
        identities = [row["identity"] for row in self.parsed["skipped"]]
        self.assertEqual(identities, [
            "test_cycle23_routing_manifest_coverage.Cycle23RoutingManifestCoverageTest."
            "test_active_manifest_declares_only_paths_it_owns",
            "test_open_source_properties.OpenSourcePropertyTests.test_hypothesis_is_an_explicit_optional_test_dependency",
            "test_w22_product_serving.W22ProductServingTests.test_repository_rejects_symlinked_game_directory",
            "test_w23_operations.W23OperationsTests.test_recursive_cleanup_rejects_symlink_or_junction_alias",
            "setUpClass (test_week1_2026_authority_enrichment.MaterializedArtifactTests)",
        ])
        self.assertTrue(reconcile(self.parsed)["consistent"], reconcile(self.parsed))

    def test_the_docstring_split_and_double_quoted_reasons_are_recognized(self) -> None:
        rows = self.parsed["skipped"]
        self.assertTrue(rows[0]["docstring_line_between"])
        self.assertEqual(rows[1]["reason"], "install the 'test' optional dependency")
        self.assertIn("WinError 1314", rows[2]["reason"])

    def test_a_fixture_skip_is_not_subtracted_from_executed_tests(self) -> None:
        # Four methods ran (Ran 4); their four skips are whole-method skips. The fixture skip's methods were
        # never counted in "Ran", so subtracting it would under-count by one (Attempt #2 reported 5269, not 5270).
        self.assertEqual(self.parsed["skip_scope_counts"], {"METHOD": 4, "SUBTEST": 0, "FIXTURE": 1})
        self.assertEqual(self.parsed["executed_test_count"], 0)

    def test_the_attempt_two_parser_shape_would_still_be_reported_inconsistent(self) -> None:
        # Keep only the row the old one-line single-quote pattern could match (the fixture line); the four
        # rows it missed are the four MF37A02-05 named. Reconciliation must object.
        old = dict(self.parsed)
        old["skipped"] = [row for row in self.parsed["skipped"]
                          if not row["docstring_line_between"] and "'" not in row["reason"]
                          and "WinError" not in row["reason"]]
        old["skipped_count"] = len(old["skipped"])
        self.assertEqual([row["scope"] for row in old["skipped"]], ["FIXTURE"])
        report = reconcile(old)
        self.assertFalse(report["consistent"])
        self.assertIn("declares 5 skip(s) but 1 were parsed", report["problems"][0])

    def test_a_skipped_subtest_is_its_own_identity(self) -> None:
        parsed = parse_unittest(
            "test_many (pkg.Case.test_many) ... \n"
            "  test_many (pkg.Case.test_many) [case one] (i=1) ... skipped 'not here'\n"
            "ok\n\nRan 1 test in 0.0s\n\nOK (skipped=1)\n")
        self.assertEqual([row["identity"] for row in parsed["skipped"]], ["pkg.Case.test_many [case one] (i=1)"])
        self.assertEqual(parsed["skipped"][0]["scope"], "SUBTEST")
        self.assertEqual(parsed["executed_test_count"], 1)


#: A generated suite that produces every outcome kind unittest has, plus an import failure.
SUITE = {
    "test_census_mixed.py": textwrap.dedent('''
        import unittest

        class Mixed(unittest.TestCase):
            def test_pass(self):
                pass

            def test_fail(self):
                self.assertEqual(1, 2)

            def test_error(self):
                raise RuntimeError("boom")

            @unittest.skip("a reason with 'single' quotes")
            def test_skip_double_quoted(self):
                pass

            def test_skip_with_docstring(self):
                """A docstring line printed between the identity and the outcome."""
                self.skipTest("plain reason")

            def test_subtests(self):
                for i in range(3):
                    with self.subTest(i=i):
                        if i == 1:
                            self.skipTest("skip one subtest")
                        if i == 2:
                            self.assertEqual(i, 0)

            @unittest.expectedFailure
            def test_expected_failure(self):
                self.assertEqual(1, 2)

        class FixtureSkipped(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                raise unittest.SkipTest("class fixture skipped")

            def test_never_runs_a(self):
                pass

            def test_never_runs_b(self):
                pass
    '''),
    "test_census_broken.py": "import a_module_that_does_not_exist\n",
}


def _write_suite(directory: Path) -> None:
    for name, body in SUITE.items():
        (directory / name).write_text(body, encoding="utf-8")


class CensusReconcilesThreeAccounts(unittest.TestCase):
    """A real subprocess run: text parse, per-outcome records and unittest's counts agree by identity."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        work = Path(cls._tmp.name)
        _write_suite(work)
        env = dict(os.environ, PYTHONPATH=str(_REPO_ROOT / "src"), PYTHONDONTWRITEBYTECODE="1")
        cls.record = run_lane(
            "census_mixed",
            [sys.executable, "-B", "-m", "aggie_analytics.validation.unittest_census", "--start-dir", ".",
             "--records", str(work / "records.jsonl"), "--summary", str(work / "summary.json")],
            cwd=work, env=env, log_dir=work / "logs", kind="TEST",
            census=(work / "records.jsonl", work / "summary.json"),
        )
        cls.summary = json.loads((work / "summary.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_the_run_is_red_for_its_real_failures_and_its_accounts_agree(self) -> None:
        self.assertEqual(self.record["result"], FAIL)
        self.assertEqual(self.record["exit_code"], 1)
        census = self.record["census_reconciliation"]
        self.assertTrue(census["consistent"], census["problems"])
        self.assertTrue(self.record["unittest_reconciliation"]["consistent"], self.record["unittest_reconciliation"])

    def test_every_outcome_kind_is_recorded_by_identity(self) -> None:
        census = self.record["census_reconciliation"]
        self.assertEqual(census["import_failures"], ["unittest.loader._FailedTest.test_census_broken"])
        self.assertEqual(census["whole_method_skips"], ["test_census_mixed.Mixed.test_skip_double_quoted",
                                                        "test_census_mixed.Mixed.test_skip_with_docstring"])
        self.assertEqual(census["subtest_skips"], ["test_census_mixed.Mixed.test_subtests (i=1)"])
        self.assertEqual(census["subtest_failures"], ["test_census_mixed.Mixed.test_subtests (i=2)"])
        self.assertEqual([row["id"] for row in census["fixture_outcomes"]],
                         ["setUpClass (test_census_mixed.FixtureSkipped)"])
        self.assertEqual(census["expected_failures"]["records"], 1)

    def test_methods_of_a_skipped_fixture_are_discovered_but_never_ran(self) -> None:
        census = self.record["census_reconciliation"]
        self.assertEqual(census["discovered_but_never_ran"],
                         ["test_census_mixed.FixtureSkipped.test_never_runs_a",
                          "test_census_mixed.FixtureSkipped.test_never_runs_b"])
        self.assertEqual(self.summary["discovered_count"], 10)
        self.assertEqual(self.summary["tests_run"], 8)

    def test_a_dropped_record_is_reported_by_identity(self) -> None:
        records = [json.loads(line) for line in Path(self.summary["records"]).read_text(encoding="utf-8").splitlines()]
        kept = [row for row in records if row["id"] != "test_census_mixed.Mixed.test_skip_double_quoted"]
        report = reconcile_census(self.record["unittest"], self.summary, kept)
        self.assertFalse(report["consistent"])
        self.assertTrue(any("test_skip_double_quoted" in problem for problem in report["problems"]))


class ImportOriginsAreBound(unittest.TestCase):
    """Wrong checkout and wrong ``tools`` origins refuse; the selected checkout's own imports pass."""

    TEST_MODULE = textwrap.dedent('''
        import unittest
        from tools.marker import WHO

        class Origin(unittest.TestCase):
            def test_imported(self):
                self.assertTrue(WHO)
    ''')

    def _checkout(self, root: Path, who: str) -> Path:
        (root / ".git").mkdir(parents=True)
        (root / "tools").mkdir()
        (root / "tools" / "__init__.py").write_text("", encoding="utf-8")
        (root / "tools" / "marker.py").write_text(f"WHO = {who!r}\n", encoding="utf-8")
        (root / "tests").mkdir()
        (root / "tests" / "test_origin.py").write_text(self.TEST_MODULE, encoding="utf-8")
        return root

    def _run(self, selected: Path, python_path: list[Path], work: Path) -> subprocess.CompletedProcess:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                   PYTHONPATH=os.pathsep.join(str(p) for p in python_path + [_REPO_ROOT / "src"]))
        return subprocess.run(
            [sys.executable, "-B", "-m", "aggie_analytics.validation.unittest_census", "--start-dir", ".",
             "--records", str(work / "r.jsonl"), "--summary", str(work / "s.json"), "--selected-root", str(selected)],
            cwd=selected / "tests", env=env, capture_output=True, text=True, timeout=120, check=False)

    def test_the_selected_checkouts_own_tools_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            selected = self._checkout(Path(tmp) / "selected", "selected")
            completed = self._run(selected, [selected], Path(tmp))
            summary = json.loads((Path(tmp) / "s.json").read_text(encoding="utf-8"))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(summary["origin_audit"]["holds"], summary["origin_audit"])
        self.assertTrue(summary["origin_audit"]["key_modules"]["tools"]["inside_selected_root"])

    def test_tools_from_another_checkout_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            selected = self._checkout(Path(tmp) / "selected", "selected")
            other = self._checkout(Path(tmp) / "other", "other")
            completed = self._run(selected, [other, selected], Path(tmp))
            summary = json.loads((Path(tmp) / "s.json").read_text(encoding="utf-8"))
        self.assertEqual(completed.returncode, 3, completed.stderr)
        self.assertFalse(summary["origin_audit"]["holds"])
        self.assertFalse(summary["origin_audit"]["key_modules"]["tools"]["inside_selected_root"])
        self.assertIn("import origin violation", completed.stderr)

    def test_a_missing_repository_root_is_an_import_failure_not_a_silent_skip(self) -> None:
        # The Attempt #2 shape: tests and src on the path, the repository root not. The import error is kept
        # as an error identity; nothing reclassifies it.
        with tempfile.TemporaryDirectory() as tmp:
            selected = self._checkout(Path(tmp) / "selected", "selected")
            completed = self._run(selected, [], Path(tmp))
            records = [json.loads(line) for line in (Path(tmp) / "r.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(completed.returncode, 1)
        self.assertEqual([row["id"] for row in records if row.get("is_import_error")],
                         ["unittest.loader._FailedTest.test_origin"])
        self.assertIn("No module named 'tools'", completed.stderr)


class TheSixGovernanceTestsRunFromTheSelectedSource(unittest.TestCase):
    """MF37A02-05's positive closure, exercised against this checkout's own tools package."""

    def test_acceptance_governance_imports_tools_from_this_checkout_and_runs_six_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                       PYTHONPATH=os.pathsep.join([str(_REPO_ROOT), str(_REPO_ROOT / "src")]))
            completed = subprocess.run(
                [sys.executable, "-B", "-m", "aggie_analytics.validation.unittest_census", "test_acceptance_governance",
                 "--records", str(Path(tmp) / "r.jsonl"), "--summary", str(Path(tmp) / "s.json"),
                 "--selected-root", str(_REPO_ROOT)],
                cwd=_REPO_ROOT / "tests", env=env, capture_output=True, text=True, timeout=300, check=False)
            summary = json.loads((Path(tmp) / "s.json").read_text(encoding="utf-8"))
        self.assertEqual(completed.returncode, 0, completed.stderr[-3000:])
        self.assertEqual(summary["tests_run"], 6)
        self.assertEqual(summary["framework_counts"]["skipped"], 0)
        tools = summary["origin_audit"]["key_modules"]["tools"]
        self.assertTrue(tools["imported"] and tools["inside_selected_root"], tools)


if __name__ == "__main__":
    unittest.main()

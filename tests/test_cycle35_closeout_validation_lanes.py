"""Cycle #35 closeout review (20260921T025300Z), section 1: validation-lane
truth.

Three defects, each with a test here:

* The FULL_SUITE_MOUNTED receipt claimed canonical mounted acceptance from
  a run that never set AGGIE_ANALYTICS_DATA_ROOT. The Family B modules gate
  on `bool(os.environ.get(...)) and DATA_ROOT.exists()`, so directory
  presence alone proves nothing -- with the variable unset the same nine
  tests skip and the command exits 0.
* PRIVATE_DATA_PARTIAL_ROOT was NOT_RUN; the partial and corrupt roots now
  have real fixtures.
* DETERMINISTIC_RELEASE_REPLAY was NOT_RUN; two real builds are now
  compared on full row content.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from r35_18_mounted_lane_receipt import (  # noqa: E402
    ENV_ALLOWLIST,
    build_environment,
    parse_pytest_summary,
    run_probe,
)
from r35_19_private_data_lanes import (  # noqa: E402
    build_corrupt_root,
    build_empty_root,
    build_manifest_missing_root,
    build_partial_root,
    observe,
)
from r35_20_deterministic_release_replay import (  # noqa: E402
    BUILD_CLOCK_COLUMNS,
    diff_profiles,
)

DATA_ROOT = Path(r"C:\BatteredAggieSyndrome.data")


class EnvironmentCaptureTests(unittest.TestCase):
    """The receipt must establish what the subprocess ACTUALLY saw."""

    def test_the_allowlist_holds_no_credential_shaped_names(self) -> None:
        forbidden = ("TOKEN", "SECRET", "KEY", "PASSWORD", "CREDENTIAL", "AUTH")
        for name in ENV_ALLOWLIST:
            for marker in forbidden:
                self.assertNotIn(marker, name.upper())

    def test_setting_the_mount_variable_opens_the_family_b_gate(self) -> None:
        if not DATA_ROOT.is_dir():
            self.skipTest("data root is not mounted on this host")
        probe = run_probe(build_environment(DATA_ROOT, "0"))
        self.assertTrue(probe["probe_succeeded"])
        self.assertTrue(probe["data_root_env_set"])
        self.assertTrue(probe["family_b_skip_gate_open"])

    def test_unsetting_the_mount_variable_closes_the_gate(self) -> None:
        """This is the control the manager used: the same host, the same
        directory on disk, and the gate is CLOSED because the variable is
        absent. Directory presence is not execution."""
        probe = run_probe(build_environment(None, "0"))
        self.assertTrue(probe["probe_succeeded"])
        self.assertFalse(probe["data_root_env_set"])
        self.assertFalse(probe["family_b_skip_gate_open"])

    def test_the_probe_reports_where_modules_were_imported_from(self) -> None:
        probe = run_probe(build_environment(None, "0"))
        imported = probe["imported_module_files"]
        self.assertIn("aggie_analytics", imported)
        self.assertTrue(str(imported["aggie_analytics"]).endswith("__init__.py"))

    def test_only_allowlisted_variables_are_reported(self) -> None:
        probe = run_probe(build_environment(None, "0"))
        self.assertEqual(set(probe["environment_allowlisted"]), set(ENV_ALLOWLIST))


class SkipInventoryParsingTests(unittest.TestCase):
    def test_skip_reasons_are_inventoried_with_counts(self) -> None:
        log = (
            "sssss\n"
            "SKIPPED [1] tests/a.py:10: external Cycle #18 data root is not mounted\n"
            "SKIPPED [1] tests/b.py:20: external Cycle #18 data root is not mounted\n"
            "SKIPPED [1] tests/c.py:30: some other reason\n"
            "3 skipped in 0.20s\n"
        )
        parsed = parse_pytest_summary(log)
        self.assertEqual(parsed["counts"].get("skipped"), 3)
        self.assertEqual(parsed["skips_listed"], 3)
        self.assertEqual(
            parsed["skip_reason_counts"]["external Cycle #18 data root is not mounted"],
            2,
        )

    def test_a_failing_summary_is_parsed_not_read_as_success(self) -> None:
        parsed = parse_pytest_summary("2 failed, 5 passed, 2 errors in 2.30s\n")
        self.assertEqual(parsed["counts"].get("failed"), 2)
        self.assertEqual(parsed["counts"].get("passed"), 5)
        self.assertEqual(parsed["counts"].get("error"), 2)


class PrivateDataLaneFixtureTests(unittest.TestCase):
    """Each readiness state is a distinct fact about the world; none may be
    inferred from another."""

    def test_an_empty_root_is_not_a_missing_manifest(self) -> None:
        with TemporaryDirectory() as tmp:
            empty = observe(build_empty_root(Path(tmp)))
            missing = observe(build_manifest_missing_root(Path(tmp)))
        self.assertEqual(empty["state"], "DATA_ROOT_PRESENT_BUT_EMPTY")
        self.assertEqual(missing["state"], "MANIFEST_MISSING")

    def test_an_unreadable_manifest_is_not_an_absent_one(self) -> None:
        with TemporaryDirectory() as tmp:
            observed = observe(build_corrupt_root(Path(tmp), Path("unused")))
        self.assertEqual(observed["state"], "MANIFEST_UNREADABLE")

    def test_a_partial_root_reports_partial_and_names_what_is_missing(self) -> None:
        from aggie_analytics.experimentation.walk_forward import MANIFEST_RELATIVE

        real_manifest = DATA_ROOT / MANIFEST_RELATIVE
        if not real_manifest.is_file():
            self.skipTest("real replay manifest is not mounted")
        with TemporaryDirectory() as tmp:
            fixture = build_partial_root(Path(tmp), real_manifest)
            observed = observe(fixture["root"])
        self.assertEqual(observed["state"], "PAYLOADS_PARTIALLY_PRESENT")
        self.assertTrue(observed["missing_payloads"])
        self.assertFalse(observed["rebuild_possible"])
        self.assertFalse(fixture["payload_bytes_copied_from_the_lake"])

    def test_the_partial_fixture_never_points_back_at_the_real_lake(self) -> None:
        """A fixture that resolved to real payloads would silently become a
        mounted root and prove nothing."""
        from aggie_analytics.experimentation.walk_forward import MANIFEST_RELATIVE

        real_manifest = DATA_ROOT / MANIFEST_RELATIVE
        if not real_manifest.is_file():
            self.skipTest("real replay manifest is not mounted")
        with TemporaryDirectory() as tmp:
            fixture = build_partial_root(Path(tmp), real_manifest)
            manifest = json.loads(
                (fixture["root"] / MANIFEST_RELATIVE).read_text(encoding="utf-8")
            )
        for row in manifest.get("payloads") or []:
            self.assertTrue(str(row.get("path", "")).startswith("payloads/"))


class ReplayComparisonTests(unittest.TestCase):
    def test_a_changed_scientific_column_is_a_difference(self) -> None:
        first = {
            "row_counts": {"formal_role_assertion": 3},
            "row_identities": {"formal_role_assertion": {"identity_sha256": "aaa"}},
            "source_links": {}, "conflict_dispositions": {},
            "expected_populations": {}, "evidence_layers": {},
        }
        second = json.loads(json.dumps(first))
        second["row_identities"]["formal_role_assertion"]["identity_sha256"] = "bbb"
        out = diff_profiles(first, second)
        self.assertFalse(out["identical"])
        self.assertEqual(out["difference_count"], 1)

    def test_identical_profiles_compare_identical(self) -> None:
        profile = {
            "row_counts": {"conflict": 26},
            "row_identities": {"conflict": {"identity_sha256": "x"}},
            "source_links": {"assertion_support_rows": 1398},
            "conflict_dispositions": {"conflict_rows": 26},
            "expected_populations": {"expected_cell_rows": 36582},
            "evidence_layers": {"LAYER_CANDIDATE": 26},
        }
        out = diff_profiles(profile, json.loads(json.dumps(profile)))
        self.assertTrue(out["identical"])

    def test_a_differing_source_link_count_is_caught(self) -> None:
        first = {
            "row_counts": {}, "row_identities": {},
            "source_links": {"formal_role_assertions_without_support": 0},
            "conflict_dispositions": {}, "expected_populations": {}, "evidence_layers": {},
        }
        second = json.loads(json.dumps(first))
        second["source_links"]["formal_role_assertions_without_support"] = 4
        self.assertFalse(diff_profiles(first, second)["identical"])

    def test_build_clock_columns_are_named_but_never_excluded_from_hashing(self) -> None:
        """The exclusion mechanism in coaching_release stays empty. A clock
        divergence is characterised, not hidden."""
        from aggie_analytics.cycle35.coaching_release import INCIDENTAL_EXCLUDED_COLUMNS

        self.assertEqual(INCIDENTAL_EXCLUDED_COLUMNS, {})
        self.assertIn("adjudication", BUILD_CLOCK_COLUMNS)
        self.assertIn("decided_at_utc", BUILD_CLOCK_COLUMNS["adjudication"])


if __name__ == "__main__":
    unittest.main()

"""Cycle #35 continuation (20260921T055921Z), section 6.

"Reconcile existing scheme, responsibility, career, and user-corpus sources
with the delivered release. A successful private rebuild is not proof the
delivered database contains those rows."

The tests build small databases by hand rather than reading the delivered
release, so they pin the REASONING and not the numbers that happen to be in
one file today. The two that matter most:

* a family supplying nearly every observation while carrying no assertion
  must be reported as carrying none -- counting observations alone hides
  exactly the thing section 6 asks about;
* a coverage artifact written beside a release must never be allowed to
  stand in for the release's own column.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from r35_30_delivered_release_reconciliation import (  # noqa: E402
    adjudication_time,
    compare_to_the_artifact_beside_it,
    differences,
    episode_seasons,
    family_rows,
)

SCHEMA = """
CREATE TABLE source_file (source_file_id TEXT PRIMARY KEY, source_class TEXT);
CREATE TABLE source_observation (observation_id TEXT PRIMARY KEY, source_file_id TEXT);
CREATE TABLE assertion_support (assertion_id TEXT, assertion_table TEXT, observation_id TEXT);
CREATE TABLE scheme_assertion (scheme_id TEXT PRIMARY KEY);
CREATE TABLE responsibility_assertion (responsibility_id TEXT PRIMARY KEY);
CREATE TABLE employment_episode (episode_id TEXT PRIMARY KEY, season TEXT);
CREATE TABLE expected_cell (expected_cell_id TEXT PRIMARY KEY, program_id TEXT,
    season INTEGER, coverage_state TEXT);
CREATE TABLE adjudication (adjudication_id TEXT PRIMARY KEY, decided_at_utc TEXT);
"""


def build(
    *,
    files: list[tuple[str, str]],
    observations: list[tuple[str, str]],
    supports: list[tuple[str, str]],
    episodes: list[tuple[str, str]] | None = None,
    adjudications: list[tuple[str, str]] | None = None,
) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO source_file VALUES (?,?)", files)
    conn.executemany("INSERT INTO source_observation VALUES (?,?)", observations)
    conn.executemany(
        "INSERT INTO assertion_support VALUES (?,?,?)",
        [(a, "formal_role_assertion", o) for a, o in supports],
    )
    conn.executemany(
        "INSERT INTO employment_episode VALUES (?,?)", episodes or []
    )
    conn.executemany(
        "INSERT INTO adjudication VALUES (?,?)", adjudications or []
    )
    return conn


class FamilyAccountingTests(unittest.TestCase):
    def test_a_family_with_many_observations_and_no_assertions_reads_as_zero(self) -> None:
        """The delivered release's actual shape: the user corpus supplies
        99.1% of observations and supports nothing."""

        conn = build(
            files=[("f1", "USER_COMPILED_RESEARCH_OBSERVATION"), ("f2", "OFFICIAL_STAFF_HTML")],
            observations=[("o1", "f1"), ("o2", "f1"), ("o3", "f1"), ("o4", "f2")],
            supports=[("a1", "o4")],
        )
        families = family_rows(conn)
        self.assertEqual(families["user_corpus"]["observations"], 3)
        self.assertEqual(families["user_corpus"]["assertions_supported"], 0)
        self.assertEqual(families["official_staff"]["assertions_supported"], 1)

    def test_an_absent_family_reads_as_zero_not_as_missing(self) -> None:
        conn = build(
            files=[("f2", "OFFICIAL_STAFF_HTML")],
            observations=[("o4", "f2")],
            supports=[("a1", "o4")],
        )
        self.assertEqual(family_rows(conn)["career"]["observations"], 0)
        self.assertEqual(family_rows(conn)["career"]["source_files"], 0)

    def test_empty_domain_tables_are_counted_as_tables(self) -> None:
        conn = build(files=[], observations=[], supports=[])
        families = family_rows(conn)
        self.assertEqual(families["scheme"], {"table": "scheme_assertion", "rows": 0})
        self.assertEqual(
            families["responsibility"],
            {"table": "responsibility_assertion", "rows": 0},
        )


class EpisodeSeasonTests(unittest.TestCase):
    def test_the_literal_string_current_is_not_a_season(self) -> None:
        conn = build(
            files=[], observations=[], supports=[],
            episodes=[("e1", "CURRENT"), ("e2", "CURRENT"), ("e3", "2019")],
        )
        seasons = episode_seasons(conn)
        self.assertEqual(seasons["with_a_numeric_season"], 1)
        self.assertEqual(seasons["without_a_numeric_season"], 2)


class AdjudicationTimeTests(unittest.TestCase):
    def test_one_timestamp_across_every_row_is_reported(self) -> None:
        conn = build(
            files=[], observations=[], supports=[],
            adjudications=[
                ("adj:1", "2026-09-21T03:46:27.223226+00:00"),
                ("adj:2", "2026-09-21T03:46:27.223226+00:00"),
            ],
        )
        stamped = adjudication_time(conn)
        self.assertEqual(stamped["rows"], 2)
        self.assertEqual(stamped["distinct_decided_at_utc_values"], 1)
        self.assertFalse(stamped["has_decision_time_basis_column"])


class ArtifactVersusReleaseTests(unittest.TestCase):
    """An artifact beside a release is not the release."""

    def test_a_disagreement_is_reported_as_a_disagreement(self) -> None:
        import r35_30_delivered_release_reconciliation as module

        with TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "CYCLE35_RELEASE_COVERAGE_BINDING.json"
            artifact.write_text(
                json.dumps({"coverage_states": {"COVERED_BY_CANDIDATE_OBSERVATION_ONLY": 13474}}),
                encoding="utf-8",
            )
            original = module.COVERAGE_BINDING
            module.COVERAGE_BINDING = artifact
            try:
                result = compare_to_the_artifact_beside_it(
                    {"coverage_state_counts": {"EXPECTED_NOT_YET_COVERED": 36582}}
                )
            finally:
                module.COVERAGE_BINDING = original

        self.assertFalse(result["agree"])
        self.assertIn("Only one of them is the release", result["finding"])

    def test_agreement_is_also_reported(self) -> None:
        import r35_30_delivered_release_reconciliation as module

        with TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "CYCLE35_RELEASE_COVERAGE_BINDING.json"
            artifact.write_text(
                json.dumps({"coverage_states": {"EXPECTED_NOT_YET_COVERED": 5}}),
                encoding="utf-8",
            )
            original = module.COVERAGE_BINDING
            module.COVERAGE_BINDING = artifact
            try:
                result = compare_to_the_artifact_beside_it(
                    {"coverage_state_counts": {"EXPECTED_NOT_YET_COVERED": 5}}
                )
            finally:
                module.COVERAGE_BINDING = original

        self.assertTrue(result["agree"])


class DifferenceTests(unittest.TestCase):
    def test_a_repaired_build_is_never_merged_into_the_delivered_one(self) -> None:
        delivered = {
            "families": {"scheme": {"table": "scheme_assertion", "rows": 0}},
            "coverage_as_the_release_states_it": {"season_max": 2023},
            "episode_seasons": {"with_a_numeric_season": 0},
            "adjudication_time": {"rows": 26},
        }
        repaired = {
            "families": {"scheme": {"table": "scheme_assertion", "rows": 0}},
            "coverage_as_the_release_states_it": {"season_max": 2026},
            "episode_seasons": {"with_a_numeric_season": 839},
            "adjudication_time": {"rows": 26},
        }
        found = differences(delivered, repaired)
        dimensions = {d["dimension"] for d in found}
        self.assertEqual(
            dimensions, {"coverage_as_the_release_states_it", "episode_seasons"}
        )
        for entry in found:
            self.assertIn("delivered", entry)
            self.assertIn("repaired", entry)

    def test_identical_profiles_produce_no_difference(self) -> None:
        same = {
            "families": {"scheme": {"rows": 0}},
            "coverage_as_the_release_states_it": {"season_max": 2026},
            "episode_seasons": {"with_a_numeric_season": 1},
            "adjudication_time": {"rows": 26},
        }
        self.assertEqual(differences(same, dict(same)), [])


if __name__ == "__main__":
    unittest.main()

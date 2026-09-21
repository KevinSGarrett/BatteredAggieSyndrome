"""R35-23 (Cycle #35 closeout review, 20260921T025300Z), section 7:
"Publish an immutable rebuilt release and bind both year ranges, full
candidate/verified/conflict layers, expected populations, source locators,
actual schemes/responsibilities and the corrected career tranche. If a
required domain still has no supported rows, retain that evidence gap rather
than inferring facts. Retire neither the original nor revised tranche
denominator without a versioned key reconciliation... Avoid self-referential
hash claims; finalize children before sealing their parent manifest."
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from r35_23_publish_release import (  # noqa: E402
    COVERED_CANDIDATE,
    COVERED_CONFIRMED,
    NOT_COVERED,
    bind_coverage,
    bind_layers,
    numeric_season,
    release_profile,
)

SCHEMA = """
CREATE TABLE source_file (
  source_file_id TEXT PRIMARY KEY, path TEXT, raw_sha256 TEXT,
  decoded_sha256 TEXT, bytes INTEGER, source_class TEXT, rights_state TEXT,
  acquisition_receipt TEXT, source_revision TEXT, retrieved_at_utc TEXT);
CREATE TABLE source_observation (
  observation_id TEXT PRIMARY KEY, source_file_id TEXT, locator TEXT,
  observed_text TEXT, observed_person TEXT, observed_title TEXT,
  observed_program TEXT, observed_season TEXT, parser_identity TEXT,
  evidence_layer TEXT);
CREATE TABLE employment_episode (
  episode_id TEXT PRIMARY KEY, person_id TEXT, program_id TEXT, season TEXT,
  valid_from TEXT, valid_to TEXT, date_precision TEXT, evidence_layer TEXT,
  pit_admitted INTEGER);
CREATE TABLE formal_role_assertion (
  assertion_id TEXT PRIMARY KEY, episode_id TEXT, role_family TEXT,
  exact_title_text TEXT, qualifiers TEXT, principal_role_blocked INTEGER,
  evidence_layer TEXT);
CREATE TABLE expected_cell (
  expected_cell_id TEXT PRIMARY KEY, program_id TEXT, season INTEGER,
  role_family TEXT, era_band TEXT, coverage_state TEXT);
CREATE TABLE conflict (
  conflict_id TEXT PRIMARY KEY, subject_kind TEXT, subject_key TEXT,
  reason TEXT, left_assertion TEXT, right_assertion TEXT);
CREATE TABLE adjudication (
  adjudication_id TEXT PRIMARY KEY, conflict_id TEXT, decision TEXT,
  decided_by TEXT, basis TEXT, decided_at_utc TEXT);
CREATE TABLE responsibility_assertion (assertion_id TEXT PRIMARY KEY);
CREATE TABLE scheme_assertion (assertion_id TEXT PRIMARY KEY);
"""


def build_release(
    path: Path,
    *,
    expected: list[tuple[str, int, str]],
    episodes: list[tuple[str, str, str]] = (),
    observations: list[tuple[str, str, str]] = (),
) -> None:
    """A minimal release with the tables the binding actually reads.

    `episodes` are (program_id, season_text, role_family) at the confirmed
    layer; `observations` are (program_id, season_text, title).
    """

    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    for index, (program_id, season, role_family) in enumerate(expected):
        conn.execute(
            "INSERT INTO expected_cell VALUES (?,?,?,?,?,?)",
            (f"cell{index}", program_id, season, role_family, "FBS_PLUS_FCS",
             "EXPECTED_NOT_YET_COVERED"),
        )
    for index, (program_id, season, role_family) in enumerate(episodes):
        conn.execute(
            "INSERT INTO employment_episode VALUES (?,?,?,?,?,?,?,?,?)",
            (f"ep{index}", f"p{index}", program_id, season, None, None,
             "SEASON_EXACT", "OFFICIAL_PRIMARY_CONFIRMED", 0),
        )
        conn.execute(
            "INSERT INTO formal_role_assertion VALUES (?,?,?,?,?,?,?)",
            (f"a{index}", f"ep{index}", role_family, "Head Coach", "[]", 0,
             "OFFICIAL_PRIMARY_CONFIRMED"),
        )
    for index, (program_id, season, title) in enumerate(observations):
        conn.execute(
            "INSERT INTO source_observation VALUES (?,?,?,?,?,?,?,?,?,?)",
            (f"obs{index}", "f0", f"loc:{index}", "text", "Someone", title,
             program_id, season, "parser", "CANDIDATE_SINGLE_SOURCE"),
        )
    conn.commit()
    conn.close()


class NumericSeasonTests(unittest.TestCase):
    def test_a_four_digit_year_is_a_season(self) -> None:
        self.assertEqual(numeric_season("2018"), 2018)

    def test_current_is_not_a_season(self) -> None:
        """'CURRENT' is the source declining to state a year. Treating it as
        one would date 839 episodes by assumption."""
        for value in ("CURRENT", "", None, "20", "202", "20188", "CURRENT2020"):
            with self.subTest(value=value):
                self.assertIsNone(numeric_season(value))


class CoverageBindingTests(unittest.TestCase):
    def bind(self, **kwargs) -> dict:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.sqlite"
            build_release(path, **kwargs)
            conn = sqlite3.connect(path)
            try:
                return bind_coverage(conn)
            finally:
                conn.close()

    def test_a_confirmed_assertion_with_a_stated_season_covers_its_cell(self) -> None:
        result = self.bind(
            expected=[("PROG", 2018, "head_coach")],
            episodes=[("PROG", "2018", "head_coach")],
        )
        self.assertEqual(result["coverage_states"], {COVERED_CONFIRMED: 1})

    def test_an_episode_with_no_stated_season_covers_nothing(self) -> None:
        """The whole confirmed layer in the real release is in this state.
        Binding it to a cell would invent the season."""
        result = self.bind(
            expected=[("PROG", 2018, "head_coach")],
            episodes=[("PROG", "CURRENT", "head_coach")],
        )
        self.assertEqual(result["coverage_states"], {NOT_COVERED: 1})
        self.assertEqual(result["episode_assertions_without_a_stated_season"], 1)
        self.assertIn("invent", result["confirmed_layer_is_empty_because"])

    def test_a_candidate_observation_never_reaches_the_confirmed_state(self) -> None:
        result = self.bind(
            expected=[("PROG", 2018, "head_coach")],
            observations=[("PROG", "2018", "Head Coach")],
        )
        self.assertEqual(result["coverage_states"], {COVERED_CANDIDATE: 1})

    def test_an_unaddressed_cell_is_distinct_from_a_candidate_only_cell(self) -> None:
        """Collapsing these two would either erase acquisition work or
        invent coverage; they are counted apart."""
        result = self.bind(
            expected=[("PROG", 2018, "head_coach"), ("PROG", 1965, "head_coach")],
            observations=[("PROG", "2018", "Head Coach")],
        )
        self.assertEqual(
            result["coverage_states"], {COVERED_CANDIDATE: 1, NOT_COVERED: 1}
        )

    def test_a_position_coach_title_is_not_forced_into_a_core_family(self) -> None:
        result = self.bind(
            expected=[("PROG", 2018, "head_coach")],
            observations=[("PROG", "2018", "Wide Receivers")],
        )
        self.assertEqual(result["coverage_states"], {NOT_COVERED: 1})
        self.assertEqual(result["observations_mapped_to_a_core_role_family"], 0)
        self.assertEqual(
            result["most_common_titles_outside_the_core_families"][0]["title"],
            "Wide Receivers",
        )

    def test_a_season_that_matches_but_a_program_that_does_not_covers_nothing(
        self,
    ) -> None:
        result = self.bind(
            expected=[("PROG", 2018, "head_coach")],
            observations=[("OTHER", "2018", "Head Coach")],
        )
        self.assertEqual(result["coverage_states"], {NOT_COVERED: 1})

    def test_a_wrong_year_observation_does_not_cover_the_cell(self) -> None:
        result = self.bind(
            expected=[("PROG", 2018, "head_coach")],
            observations=[("PROG", "2019", "Head Coach")],
        )
        self.assertEqual(result["coverage_states"], {NOT_COVERED: 1})


class LayerBindingTests(unittest.TestCase):
    def test_an_empty_required_domain_is_retained_with_a_stated_basis(self) -> None:
        """Zero rows is a retained evidence gap, not a table to drop."""
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.sqlite"
            build_release(path, expected=[])
            conn = sqlite3.connect(path)
            try:
                layers = bind_layers(conn)
            finally:
                conn.close()
        gaps = layers["retained_evidence_gaps"]
        for domain in ("responsibility_assertion", "scheme_assertion"):
            with self.subTest(domain=domain):
                self.assertEqual(gaps[domain]["rows"], 0)
                self.assertTrue(gaps[domain]["basis"].strip())

        # Responsibility is a genuine evidence gap: the cycle33 extractor
        # emits tenure and scheme fields only and sets not_play_calling
        # explicitly, so no acquired source states unit responsibility.
        self.assertEqual(
            gaps["responsibility_assertion"]["disposition"],
            "RETAINED_AS_EVIDENCE_GAP",
        )

        # Scheme is NOT. 9,111 stated scheme claims sit in the cycle33
        # cache; what is missing is a crosswalk from their Wikipedia page
        # titles to canonical program ids. Two empty tables with different
        # causes were sharing one disposition, which is how the false basis
        # went unnoticed.
        scheme = gaps["scheme_assertion"]
        self.assertEqual(
            scheme["disposition"], "BLOCKED_ON_A_MISSING_PROGRAM_CROSSWALK"
        )
        self.assertNotIn("No acquired source states", scheme["basis"])
        self.assertIn("Sources DO state schemes", scheme["basis"])
        self.assertEqual(scheme["reconciliation"], "CYCLE35_SCHEME_INGEST.json")

    def test_both_year_ranges_are_bound_separately(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.sqlite"
            build_release(
                path,
                expected=[],
                observations=[
                    ("P", "2005", "Head Coach"),
                    ("P", "2018", "Head Coach"),
                    ("P", "CURRENT", "Head Coach"),
                ],
            )
            conn = sqlite3.connect(path)
            try:
                layers = bind_layers(conn)
            finally:
                conn.close()
        self.assertEqual(layers["year_ranges"]["2000_2012"]["observations"], 1)
        self.assertEqual(layers["year_ranges"]["2013_2026"]["observations"], 1)
        self.assertEqual(layers["observations_without_a_stated_season"], 1)


class PublishedManifestTests(unittest.TestCase):
    """The tool is run end to end so the sealing order is checked on real
    files rather than asserted about the code that writes them."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = TemporaryDirectory()
        tmp = Path(cls._tmp.name)
        release = tmp / "input.sqlite"
        build_release(
            release,
            expected=[("PROG", 2018, "head_coach")],
            observations=[("PROG", "2018", "Head Coach")],
        )
        cls.out = tmp / "out"
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "cycle35" / "r35_23_publish_release.py"),
                "--release", str(release),
                "--prior-release", str(tmp / "absent.sqlite"),
                "--out-dir", str(cls.out),
            ],
            capture_output=True,
            text=True,
            env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")},
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stderr)
        cls.manifest = json.loads(
            (cls.out / "CYCLE35_PUBLISHED_RELEASE_MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_the_manifest_does_not_carry_its_own_hash(self) -> None:
        own = hashlib.sha256(
            (self.out / "CYCLE35_PUBLISHED_RELEASE_MANIFEST.json").read_bytes()
        ).hexdigest()
        self.assertNotIn(own, json.dumps(self.manifest))

    def test_the_sidecar_carries_the_manifest_hash_and_it_is_correct(self) -> None:
        sidecar = (self.out / "CYCLE35_PUBLISHED_RELEASE_MANIFEST.sha256").read_text(
            encoding="utf-8"
        )
        own = hashlib.sha256(
            (self.out / "CYCLE35_PUBLISHED_RELEASE_MANIFEST.json").read_bytes()
        ).hexdigest()
        self.assertTrue(sidecar.startswith(own))

    def test_every_child_digest_matches_the_file_on_disk(self) -> None:
        """Children are finalized before the parent is sealed, so a recorded
        digest that no longer matches would mean a child was rewritten."""
        self.assertEqual(len(self.manifest["children"]), 4)
        for name, recorded in self.manifest["children"].items():
            with self.subTest(child=name):
                actual = hashlib.sha256((self.out / name).read_bytes()).hexdigest()
                self.assertEqual(recorded["sha256"], actual)

    def test_the_published_database_digest_matches_the_published_copy(self) -> None:
        published = Path(self.manifest["published_release"]["path"])
        self.assertTrue(published.is_file())
        self.assertEqual(
            self.manifest["published_release"]["sha256"],
            hashlib.sha256(published.read_bytes()).hexdigest(),
        )

    def test_publishing_is_not_claimed_to_be_activation_or_acceptance(self) -> None:
        authorization = self.manifest["authorization"]
        self.assertEqual(authorization["status"], "IN_PROGRESS_LOCAL_WORK_REMAINS")
        for forbidden in ("merged", "canonically activated", "scientifically accepted"):
            self.assertIn(forbidden, authorization["published_does_not_mean"])

    def test_an_absent_prior_release_is_reported_not_silently_skipped(self) -> None:
        comparison = json.loads(
            (self.out / "CYCLE35_DELIVERED_RELEASE_COMPARISON.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(comparison["prior_delivered_release"]["present"])
        self.assertIsNone(comparison["finding"])


class CareerTrancheReconciliationTests(unittest.TestCase):
    def test_neither_denominator_is_retired(self) -> None:
        from r35_23_publish_release import CAREER_TRANCHE, bind_career_tranche

        if not CAREER_TRANCHE.is_file():
            self.skipTest("career tranche artifact is not mounted")
        bound = bind_career_tranche()
        self.assertTrue(bound["bound"])
        for key, version in bound["versioned_keys"].items():
            with self.subTest(key=key):
                self.assertFalse(version["retired"])
        # The two key spaces are reconciled by membership, never by adding
        # one count to the other over overlapping employers.
        self.assertIn(
            "set membership",
            bound["key_space_reconciliation"]["arithmetic_addition_forbidden"],
        )
        self.assertGreater(bound["key_space_reconciliation"]["employers_in_both"], 0)


class RealPublishedReleaseTests(unittest.TestCase):
    PUBLISHED = Path(
        r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs"
        r"\20260921T025300Z_closeout_release"
    )

    def setUp(self) -> None:
        if not (self.PUBLISHED / "CYCLE35_PUBLISHED_RELEASE_MANIFEST.json").is_file():
            self.skipTest("the published release is not present")

    def test_the_published_release_carries_both_year_ranges(self) -> None:
        profile = release_profile(
            self.PUBLISHED / "published_release"
            / "CYCLE35_COACHING_RELEASE_PUBLISHED.sqlite"
        )
        self.assertTrue(profile["present"])
        self.assertGreater(profile["observations_2000_2012"], 0)
        self.assertGreater(profile["observations_2013_2026"], 0)

    def test_the_comparison_states_what_the_prior_release_actually_held(self) -> None:
        """The prior delivered release is named, so "was the ledger entry
        stale?" is answered against the right database."""
        comparison = json.loads(
            (self.PUBLISHED / "CYCLE35_DELIVERED_RELEASE_COMPARISON.json").read_text(
                encoding="utf-8"
            )
        )
        if not comparison["prior_delivered_release"]["present"]:
            self.skipTest("the prior delivered release is not mounted")
        self.assertLess(
            comparison["prior_delivered_release"]["observations_2013_2026"],
            comparison["published_rebuild"]["observations_2013_2026"],
        )
        self.assertIn("ACCURATE", comparison["finding"])


if __name__ == "__main__":
    unittest.main()

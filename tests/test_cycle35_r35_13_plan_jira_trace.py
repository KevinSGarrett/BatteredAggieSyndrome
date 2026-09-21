"""R35-13 (Cycle #35 manager follow-up, 20260920T224700Z): "complete the
authorized BAS-local C01 contract/released-package tests... and local/live
Jira reconciliation. Do not self-approve C01... or turn proposal comments
into adoption/convergence claims." No test imported
tools/cycle35/r35_13_plan_jira_trace.py before this file.

These exercise: the evidence-presence check main() performs against a real
run-output directory (fixture, not the live one, so the test is not a
function of whatever files happen to exist today), the sha256_file helper,
and self-consistency of the three hardcoded adjudication tables -- every
PT35_MAPPINGS/MISSING_MAPPINGS/FALSE_POSITIVE_CHALLENGES row has the
fields it's read by and a real disposition, so a malformed row would fail
here instead of silently producing an incomplete packet. Jira handling is
duplicate-audit-only and offline by design (see the module docstring); no
test performs or mocks a live Jira call, since none is authorized this
cycle.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from r35_13_plan_jira_trace import (  # noqa: E402
    EXISTING_OWNERS,
    FALSE_POSITIVE_CHALLENGES,
    MISSING_MAPPINGS,
    PT35_MAPPINGS,
    sha256_file,
)

_ALLOWED_ADJUDICATIONS = {
    "CONFIRMED_AND_ADDRESSED",
    "CONFIRMED_PARTIALLY_ADDRESSED",
    "CONFIRMED_AND_HONOURED_AS_UNMET",
    "CONFIRMED_REMAINS_OPEN",
}


class Sha256FileTests(unittest.TestCase):
    def test_missing_file_returns_none_not_an_error(self) -> None:
        self.assertIsNone(sha256_file(Path("Z:/does/not/exist.json")))

    def test_real_file_hashes_its_actual_bytes(self) -> None:
        import hashlib

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.json"
            path.write_bytes(b"hello")
            self.assertEqual(sha256_file(path), hashlib.sha256(b"hello").hexdigest())


class Pt35MappingsStructureTests(unittest.TestCase):
    """A malformed mapping row would either crash main() or silently
    produce an incomplete adjudication -- checked here as a real
    self-consistency contract, the same discipline applied to
    SESSION_MF35_FIXES elsewhere this cycle."""

    def test_twelve_mappings_each_trace_unique(self) -> None:
        self.assertEqual(len(PT35_MAPPINGS), 12)
        traces = [row["trace"] for row in PT35_MAPPINGS]
        self.assertEqual(len(traces), len(set(traces)))

    def test_every_mapping_has_required_nonempty_fields(self) -> None:
        for row in PT35_MAPPINGS:
            for key in ("trace", "owner_section", "manager_claim", "basis"):
                self.assertTrue(str(row.get(key) or "").strip(), row)
            self.assertTrue(row["requirements"], row["trace"])
            self.assertTrue(row["evidence"], row["trace"])

    def test_every_adjudication_is_a_real_disposition(self) -> None:
        for row in PT35_MAPPINGS:
            self.assertIn(row["adjudication"], _ALLOWED_ADJUDICATIONS, row["trace"])

    def test_evidence_entries_are_plain_filenames_not_paths(self) -> None:
        """main() joins these onto a run_output directory -- an absolute
        or parent-escaping entry would let a mapping point outside the
        declared evidence directory."""
        for row in PT35_MAPPINGS:
            for name in row["evidence"]:
                self.assertNotIn("..", name, row["trace"])
                self.assertFalse(Path(name).is_absolute(), row["trace"])

    def test_pt35_03_no_longer_claims_zero_resolved_player_ids(self) -> None:
        """Regression: this row's basis text used to assert
        'resolved_player_ids = 0', which the Cycle #35 follow-up item 6
        R35-11 fix made false (28 of 92 assertions now resolve a canonical
        player id). A hardcoded claim like this can go stale exactly the
        way the manager's review found other hand-typed notes going stale
        underneath a real fix -- this pins the correction so it cannot
        silently regress back to the disproven text."""
        row = next(r for r in PT35_MAPPINGS if r["trace"] == "PT35-03")
        self.assertIn("28 of 92", row["basis"])
        self.assertEqual(row["adjudication"], "CONFIRMED_PARTIALLY_ADDRESSED")


class MissingMappingsAndChallengesStructureTests(unittest.TestCase):
    def test_missing_mappings_have_required_fields(self) -> None:
        for row in MISSING_MAPPINGS:
            for key in ("trace", "obligation", "why_no_mapping_covered_it", "state"):
                self.assertTrue(str(row.get(key) or "").strip(), row)
            self.assertTrue(row["evidence"])
            self.assertTrue(row["requirements"])

    def test_false_positive_challenges_have_required_fields(self) -> None:
        for row in FALSE_POSITIVE_CHALLENGES:
            for key in ("trace", "challenged_clause", "challenge", "disposition"):
                self.assertTrue(str(row.get(key) or "").strip(), row)

    def test_traces_are_not_duplicated_within_each_table(self) -> None:
        missing_traces = [r["trace"] for r in MISSING_MAPPINGS]
        self.assertEqual(len(missing_traces), len(set(missing_traces)))
        challenge_traces = [r["trace"] for r in FALSE_POSITIVE_CHALLENGES]
        self.assertEqual(len(challenge_traces), len(set(challenge_traces)))


class EvidencePresenceCheckTests(unittest.TestCase):
    """The evidence_all_present computation main() performs, exercised
    directly against a fixture directory rather than whatever the live
    run-output happens to contain today."""

    def _adjudicate(self, run_output: Path) -> list[dict]:
        adjudications = []
        for row in PT35_MAPPINGS:
            evidence = []
            for name in row["evidence"]:
                path = run_output / name
                evidence.append(
                    {"artifact": name, "present": path.is_file(), "sha256": sha256_file(path)}
                )
            adjudications.append(
                {**row, "evidence": evidence, "evidence_all_present": all(e["present"] for e in evidence)}
            )
        return adjudications

    def test_all_evidence_absent_is_reported_not_silently_true(self) -> None:
        with TemporaryDirectory() as tmp:
            adjudications = self._adjudicate(Path(tmp))
        self.assertTrue(adjudications)
        self.assertTrue(all(not row["evidence_all_present"] for row in adjudications))

    def test_real_run_output_evidence_is_all_present(self) -> None:
        """Real-data reproduction: the default run-output directory this
        tool actually reads names files that genuinely exist there right
        now. Skipped where the mounted private run-output directory is not
        present at all (e.g. hosted CI, which has no private data mount) --
        an absent mount is a real, different, and already-disclosed state,
        not the same as evidence being missing from a present mount."""
        from r35_13_plan_jira_trace import RUN_OUTPUT_DEFAULT

        if not RUN_OUTPUT_DEFAULT.is_dir():
            self.skipTest("mounted run-output directory not present")

        adjudications = self._adjudicate(RUN_OUTPUT_DEFAULT)
        missing = [
            (row["trace"], e["artifact"])
            for row in adjudications
            for e in row["evidence"]
            if not e["present"]
        ]
        self.assertEqual(missing, [])


class JiraDisclosureTests(unittest.TestCase):
    """Nothing here performs or mocks a live Jira call -- these check only
    that the module's own offline-audit declarations are internally
    consistent, matching "do not self-approve C01... or turn proposal
    comments into adoption/convergence claims.\""""

    def test_existing_owners_are_nonempty_and_unique(self) -> None:
        self.assertTrue(EXISTING_OWNERS)
        self.assertEqual(len(EXISTING_OWNERS), len(set(EXISTING_OWNERS)))

    def test_bat706_is_among_the_existing_owners_not_recreated(self) -> None:
        """The manager's correction: BAT-706 was already registered: this
        cycle must not 'repair' that by creating a duplicate."""
        self.assertIn("BAT-706", EXISTING_OWNERS)


if __name__ == "__main__":
    unittest.main()

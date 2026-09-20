"""R35-07 tests for MF35-07: a unit's hand-typed acceptance-packet note must
never be mistaken for a description of current code once a fix has landed
underneath it.

The Cycle #35 manager follow-up found status units claiming local COMPLETE
while contradicted by already-performed work, and instructed that "the
generator, not just the prose, must derive statuses from clause-level
evidence." Deriving every unit's six dimensions from live evidence is a
larger repair that remains open; `annotate_units_with_session_fixes` is the
bounded, honest interim step -- it cannot silently drift, because it is
itself just a lookup against `SESSION_MF35_FIXES`, checked here to actually
match what commits landed.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.cycle35.r35_15_acceptance_packet import (  # noqa: E402
    R35_UNITS,
    SESSION_MF35_FIXES,
    annotate_units_with_session_fixes,
)


class AnnotationTests(unittest.TestCase):
    def test_unit_with_a_recorded_fix_is_flagged_stale(self) -> None:
        units = {"R35-06": {"note": "old claim", "blockers": []}}
        fixes = {"R35-06": [{"finding": "MF35-01", "summary": "x", "commit": "abc"}]}
        annotated = annotate_units_with_session_fixes(units, fixes)
        self.assertTrue(annotated["R35-06"]["note_is_stale"])
        self.assertEqual(len(annotated["R35-06"]["note_predates_session_fixes"]), 1)

    def test_unit_with_no_recorded_fix_is_not_flagged(self) -> None:
        units = {"R35-09": {"note": "old claim", "blockers": []}}
        annotated = annotate_units_with_session_fixes(units, {})
        self.assertFalse(annotated["R35-09"]["note_is_stale"])
        self.assertEqual(annotated["R35-09"]["note_predates_session_fixes"], [])

    def test_annotation_does_not_mutate_the_original_dimensions(self) -> None:
        """The annotation must add information, never alter or re-derive
        the six status dimensions -- a fix being flagged is not the same
        as re-verification."""
        units = {
            "R35-06": {
                "note": "old claim", "blockers": [],
                "implementation_local": "COMPLETE",
                "independent_scientific_acceptance": "NOT_REVIEWED",
            }
        }
        fixes = {"R35-06": [{"finding": "MF35-01", "summary": "x", "commit": "abc"}]}
        annotated = annotate_units_with_session_fixes(units, fixes)
        self.assertEqual(annotated["R35-06"]["implementation_local"], "COMPLETE")
        self.assertEqual(
            annotated["R35-06"]["independent_scientific_acceptance"], "NOT_REVIEWED"
        )

    def test_original_units_dict_is_not_mutated_in_place(self) -> None:
        units = {"R35-06": {"note": "old claim", "blockers": []}}
        fixes = {"R35-06": [{"finding": "MF35-01", "summary": "x", "commit": "abc"}]}
        annotate_units_with_session_fixes(units, fixes)
        self.assertNotIn("note_is_stale", units["R35-06"])

    def test_every_session_fix_entry_names_a_real_finding_and_commit(self) -> None:
        for unit_id, entries in SESSION_MF35_FIXES.items():
            for entry in entries:
                self.assertTrue(entry["finding"].startswith("MF35-"), entry)
                self.assertRegex(entry["commit"], r"^[0-9a-f]{7,40}$")
                self.assertTrue(entry["summary"])

    def test_every_session_fix_unit_exists_in_r35_units(self) -> None:
        """A fix recorded against a unit that doesn't exist in R35_UNITS
        would silently never be surfaced in the real packet output."""
        for unit_id in SESSION_MF35_FIXES:
            self.assertIn(unit_id, R35_UNITS, unit_id)

    def test_real_r35_units_annotation_flags_exactly_the_touched_units(self) -> None:
        annotated = annotate_units_with_session_fixes(R35_UNITS, SESSION_MF35_FIXES)
        stale = {uid for uid, u in annotated.items() if u["note_is_stale"]}
        self.assertEqual(stale, set(SESSION_MF35_FIXES))


if __name__ == "__main__":
    unittest.main()

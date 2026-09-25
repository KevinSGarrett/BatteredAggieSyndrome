"""R35-03 (Cycle #35 continuation, 20260921T055921Z), section 4.

"Reconcile the remaining career keys with the original predeclared 48-key
set... Preserve same-name ambiguity, employer/role/time binding, entire
encountered job histories, and evidence tiers."

Rebuilding the release with the career tranche included surfaced a defect the
earlier replay never exposed, because that replay was built without the
tranche: two keys reached `canonical_person` carrying the literal Wikipedia
infobox parameter label `| oc_year =` as a person's name.

K29 (Towson 2007) and K47 (Butler 2009) were both dispositioned
ACCEPTED_SINGLE_SOURCE. In both cached sources the `off_coach` field is
EMPTY, so the extractor ran past it and captured the next parameter's label.
An empty source field is missing evidence, not a person, so the accepted
count of 39 was overstated by two.

The guard is deliberately narrow. It rejects demonstrable extractor residue
and nothing else: a real name never starts with a pipe and never consists of
a bare `parameter =` label. Rejected values are reported with their key and
reason rather than dropped, because "the source field was empty" and "we
failed to parse a name that was there" need different fixes.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from r35_03_build_coaching_release import person_name_is_bindable  # noqa: E402

TRANCHE = (
    Path("C:/BatteredAggieSyndrome.data/ops/cycle35/runs")
    / "20260920T215454Z_mf35_08_era_fix"
    / "implementation_output"
    / "R35_05_CAREER_TRANCHE_FINAL.json"
)


class BindableNameTests(unittest.TestCase):
    def test_the_observed_residue_is_rejected(self) -> None:
        self.assertFalse(person_name_is_bindable("| oc_year ="))

    def test_a_bare_parameter_label_is_rejected_with_or_without_the_pipe(self) -> None:
        for value in ("| oc_year =", "oc_year =", "|off_coach=", "  dc_year  =  "):
            with self.subTest(value=value):
                self.assertFalse(person_name_is_bindable(value))

    def test_empty_and_missing_values_are_rejected(self) -> None:
        for value in (None, "", "   ", "\t\n"):
            with self.subTest(value=repr(value)):
                self.assertFalse(person_name_is_bindable(value))

    def test_wikitext_markup_is_rejected(self) -> None:
        for value in ("{{cite web}}", "[[Bob Smith]]", "Bob Smith | Head Coach"):
            with self.subTest(value=value):
                self.assertFalse(person_name_is_bindable(value))

    def test_real_names_are_not_rejected(self) -> None:
        """The guard must not become a name filter. These are all shapes that
        occur in the real population and every one has to survive."""
        for value in (
            "Bob Smith",
            "Kevin T. Fee",
            "Jean-Luc O'Brien",
            "Deion \"Coach Prime\" Sanders",
            "Aazaar Abdul-Rahim",
            "P.J. Fleck",
            "Ted Roof",
            "A.J. St. John-Meyer Jr.",
            "Jose Ramirez-Nunez",
        ):
            with self.subTest(value=value):
                self.assertTrue(person_name_is_bindable(value))

    def test_a_name_containing_an_equals_sign_is_still_a_name(self) -> None:
        """Only a BARE parameter label is residue. A name is not rejected for
        merely containing the character."""
        self.assertTrue(person_name_is_bindable("Bob Smith = interim"))


class TrancheSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        if not TRANCHE.is_file():
            self.skipTest("the career tranche artifact is not mounted")
        self.payload = json.loads(TRANCHE.read_text(encoding="utf-8"))

    def test_the_two_residue_keys_are_still_present_in_the_source(self) -> None:
        """The source artifact is not edited. The correction happens at
        ingest, so the original evidence of the defect stays readable."""
        residue = [
            a
            for a in self.payload.get("attempts", [])
            if any(not person_name_is_bindable(p) for p in a.get("resolved_people") or [])
        ]
        self.assertEqual({a["key_id"] for a in residue}, {"K29", "K47"})
        for attempt in residue:
            with self.subTest(key=attempt["key_id"]):
                self.assertEqual(attempt["new_disposition"], "ACCEPTED_SINGLE_SOURCE")
                self.assertEqual(attempt["infobox_parameter"], "off_coach")

    def test_every_other_resolved_person_is_bindable(self) -> None:
        """Exactly two keys are affected; the guard is not quietly discarding
        a wider slice of the population."""
        bad = [
            (a["key_id"], p)
            for a in self.payload.get("attempts", [])
            for p in a.get("resolved_people") or []
            if not person_name_is_bindable(p)
        ]
        self.assertEqual(len(bad), 2, f"unexpected rejections: {bad}")

    def test_the_declared_key_count_is_unchanged(self) -> None:
        """The denominator is preserved: the correction moves two keys between
        dispositions, it does not shrink the 48-key set."""
        self.assertEqual(self.payload.get("key_count"), 48)
        self.assertEqual(len(self.payload.get("final_keys") or []), 48)


class RebuiltReleaseTests(unittest.TestCase):
    RELEASE_DIR = (
        Path("C:/BatteredAggieSyndrome.data/ops/cycle35/runs")
        / "20260921T055921Z_implementation"
        / "release_r2"
    )

    def release(self) -> Path | None:
        if not self.RELEASE_DIR.is_dir():
            return None
        found = sorted(self.RELEASE_DIR.glob("*.sqlite"))
        return found[0] if found else None

    def test_no_residue_reaches_canonical_person(self) -> None:
        import sqlite3

        path = self.release()
        if path is None:
            self.skipTest("the rebuilt release is not present")
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            garbled = con.execute(
                "SELECT COUNT(*) FROM canonical_person WHERE canonical_name "
                "LIKE '%oc_year%' OR canonical_name LIKE '|%'"
            ).fetchone()[0]
        finally:
            con.close()
        self.assertEqual(garbled, 0)


if __name__ == "__main__":
    unittest.main()

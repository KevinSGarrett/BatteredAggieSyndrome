"""Cycle #35 continuation (20260921T055921Z), section 4 -- parser recall.

"The independent sample recorded 11 of 34 quarantined rows with locatable
literal name/title evidence that the reparser did not emit. Inspect those
exact raw spans and same-record relationships. Repair generalized parser
behavior where warranted and add adversarial tests. A literal page-wide
match alone still does not justify promotion."

Three causes, each found by looking at the rows the previous repair did NOT
fix, and all three the same underlying mistake: assuming a cell's position
or shape tells you what it holds.

1. The title column comes first. `_table_records` took the first non-empty
   cell as the person, so `_name_like("Head Coach")` failed and the whole
   row was discarded.
2. An email counts as a name. `_name_like("rhuesman@richmond.edu")` is
   True, so a title/name/email row had two candidates and the
   unambiguous-name guard refused it.
3. A social handle counts as a name. "@CoachLocks" has nothing before the
   "@" and no dot after it, so the email pattern misses it.

The guard that refuses a row with two GENUINE names is deliberately not
relaxed. Such a row is undecidable from the row alone, and the tests below
pin that refusal so later work cannot loosen it to make a number move.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle33.span_locate import (  # noqa: E402
    _is_contact_value,
    _table_records,
    bind_person_role,
)


def row(*cells: str) -> str:
    return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


class ContactValueTests(unittest.TestCase):
    def test_contact_columns_are_not_names(self) -> None:
        for value in (
            "rhuesman@richmond.edu",
            "artauber@umd.edu",
            "301-314-7108",
            "(423) 555-0100",
            "+1 423 555 0100",
            "@CoachLocks",
            "@UMDFootball",
        ):
            with self.subTest(value=value):
                self.assertTrue(_is_contact_value(value))

    def test_real_names_are_never_contact_values(self) -> None:
        for value in (
            "Michael Locksley",
            "Russ Huesman",
            "P.J. Fleck",
            "Jean-Luc O'Brien",
            "Aazaar Abdul-Rahim",
            "Ted Monachino",
        ):
            with self.subTest(value=value):
                self.assertFalse(_is_contact_value(value))


class TitleFirstTableTests(unittest.TestCase):
    def test_a_title_first_row_binds(self) -> None:
        records = _table_records(row("Head Coach", "Russ Huesman"))
        self.assertEqual(
            [(r["person"], r["title"]) for r in records],
            [("Russ Huesman", "Head Coach")],
        )

    def test_a_name_first_row_is_unchanged(self) -> None:
        records = _table_records(row("Russ Huesman", "Head Coach"))
        self.assertEqual(
            [(r["person"], r["title"]) for r in records],
            [("Russ Huesman", "Head Coach")],
        )

    def test_the_richmond_shape_binds(self) -> None:
        """title / name / email -- the email must not count as a name."""
        records = _table_records(
            row("Head Coach", "Russ Huesman", "rhuesman@richmond.edu", "")
        )
        self.assertEqual([r["person"] for r in records], ["Russ Huesman"])

    def test_the_maryland_shape_binds(self) -> None:
        """title / blank / name / phone / email / handle."""
        records = _table_records(
            row(
                "Head Coach",
                "",
                "Michael Locksley",
                "301-314-7108",
                "artauber@umd.edu",
                "@CoachLocks",
                "",
            )
        )
        self.assertEqual([r["person"] for r in records], ["Michael Locksley"])


class RefusalTests(unittest.TestCase):
    """What must still NOT bind. These are the adversarial controls."""

    def test_two_genuine_names_in_one_row_refuse(self) -> None:
        """Undecidable from the row alone. Not relaxed to move a number."""
        self.assertEqual(
            _table_records(row("Head Coach", "Russ Huesman", "Jacob Huesman")), []
        )

    def test_a_vacant_row_does_not_bind_a_real_coach(self) -> None:
        """`_table_records` does emit a record for a vacancy -- `_name_like`
        accepts any short token run, so "Vacant" passes, on the name-first
        path as much as on the title-first fallback.

        That is not filtered, and deliberately so: the caller supplies the
        person and asks whether THAT person binds, so a "Vacant" record is
        only reachable if a source claims a coach by that name. No such row
        exists in the corpus. What must hold is the line below -- a vacancy
        never lends its title to a real person.
        """

        html = row("Head Coach", "Vacant", "")
        self.assertEqual([r["person"] for r in _table_records(html)], ["Vacant"])
        result = bind_person_role(html, person="Russ Huesman", title="Head Coach")
        self.assertFalse(result.get("role_claim_supported"))

    def test_a_row_with_no_title_is_not_given_one(self) -> None:
        """The fallback requires a title-like cell. A name beside contact
        detail alone does not manufacture a role."""
        self.assertEqual(
            _table_records(row("2026", "rhuesman@richmond.edu", "@CoachLocks")), []
        )

    def test_a_page_wide_match_does_not_promote(self) -> None:
        """The person appears on the page but not in the staff record. A
        literal match alone never justifies promotion."""
        html = row("Head Coach", "Someone Else") + "<p>Russ Huesman</p>"
        result = bind_person_role(html, person="Russ Huesman", title="Head Coach")
        self.assertFalse(result.get("person_record_bound"))
        self.assertFalse(result.get("role_claim_supported"))
        self.assertEqual(result.get("reject_reason"), "PERSON_NOT_BOUND_TO_STAFF_RECORD")

    def test_a_title_on_a_different_record_is_not_supported(self) -> None:
        html = row("Russ Huesman", "") + row("Head Coach", "Someone Else")
        result = bind_person_role(html, person="Russ Huesman", title="Head Coach")
        self.assertFalse(result.get("role_claim_supported"))


class SameRecordTests(unittest.TestCase):
    def test_person_and_title_come_from_one_row(self) -> None:
        records = _table_records(
            row("Head Coach", "Russ Huesman") + row("Defensive Coordinator", "Ted Monachino")
        )
        pairs = {(r["person"], r["title"]) for r in records}
        self.assertEqual(
            pairs,
            {
                ("Russ Huesman", "Head Coach"),
                ("Ted Monachino", "Defensive Coordinator"),
            },
        )

    def test_intervals_point_at_the_cells_they_name(self) -> None:
        html = row("Head Coach", "Russ Huesman")
        record = _table_records(html)[0]
        self.assertEqual(
            html[record["person_start"] : record["person_end"]], "Russ Huesman"
        )
        self.assertEqual(html[record["title_start"] : record["title_end"]], "Head Coach")


if __name__ == "__main__":
    unittest.main()

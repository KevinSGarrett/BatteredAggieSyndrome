"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-04-AC01: the era horizon is one declared table, not a literal at a call
site.

The delivered population carried an era on every row whose derivative
happened to hold one and no era at all on the 266 rows of 2026, because the
only place the label was written was a literal in the branch that restores
2024 and 2025. These tests pin the table's shape, its boundaries and the
refusal to name an era outside the declared horizon.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle37.national_eras import (  # noqa: E402
    DECLARED_HORIZON,
    DIVISION_I_A_AND_I_AA,
    ERA_TABLE,
    FBS_AND_FCS,
    FIRST_SUBDIVIDED_SEASON,
    OUTSIDE_HORIZON,
    UNIVERSITY_DIVISION,
    UNSPLIT_DIVISION_I,
    check_table,
    era_for_season,
    reconcile,
    subdivision_label_is_era_proof,
)


class TableShapeTests(unittest.TestCase):
    def test_the_table_is_contiguous_and_covers_the_horizon(self) -> None:
        check_table()  # raises on a gap, an overlap or wrong coverage
        low, high = DECLARED_HORIZON
        self.assertEqual(ERA_TABLE[0][0], low)
        self.assertEqual(ERA_TABLE[-1][1], high)

    def test_every_season_in_the_horizon_has_exactly_one_era(self) -> None:
        low, high = DECLARED_HORIZON
        for season in range(low, high + 1):
            with self.subTest(season=season):
                matches = [
                    label for start, end, label in ERA_TABLE if start <= season <= end
                ]
                self.assertEqual(len(matches), 1)
                self.assertEqual(era_for_season(season), matches[0])

    def test_the_labels_are_distinct(self) -> None:
        labels = [label for _, _, label in ERA_TABLE]
        self.assertEqual(len(labels), len(set(labels)))


class BoundaryTests(unittest.TestCase):
    def test_the_university_division_ends_in_1972(self) -> None:
        self.assertEqual(era_for_season(1972), UNIVERSITY_DIVISION)
        self.assertEqual(era_for_season(1973), UNSPLIT_DIVISION_I)

    def test_the_subdivision_begins_in_1978(self) -> None:
        self.assertEqual(era_for_season(1977), UNSPLIT_DIVISION_I)
        self.assertEqual(era_for_season(1978), DIVISION_I_A_AND_I_AA)

    def test_the_renaming_happens_in_2006(self) -> None:
        self.assertEqual(era_for_season(2005), DIVISION_I_A_AND_I_AA)
        self.assertEqual(era_for_season(2006), FBS_AND_FCS)

    def test_2026_is_inside_the_horizon(self) -> None:
        """The season whose 266 rows previously carried no era at all."""

        self.assertEqual(era_for_season(2026), FBS_AND_FCS)
        self.assertNotEqual(era_for_season(2026), OUTSIDE_HORIZON)


class OutsideHorizonTests(unittest.TestCase):
    def test_before_the_horizon_is_refused_not_rounded(self) -> None:
        self.assertEqual(era_for_season(1962), OUTSIDE_HORIZON)

    def test_after_the_horizon_is_refused_not_extended(self) -> None:
        self.assertEqual(era_for_season(2027), OUTSIDE_HORIZON)

    def test_an_unreadable_season_is_outside_rather_than_an_exception(self) -> None:
        for value in (None, "", "next year", object()):
            with self.subTest(value=repr(value)):
                self.assertEqual(era_for_season(value), OUTSIDE_HORIZON)

    def test_a_season_that_arrives_as_a_string_still_resolves(self) -> None:
        self.assertEqual(era_for_season("2020"), FBS_AND_FCS)


class EraProofTests(unittest.TestCase):
    def test_a_subdivision_label_before_1978_is_not_era_proof(self) -> None:
        self.assertFalse(subdivision_label_is_era_proof(1963))
        self.assertFalse(subdivision_label_is_era_proof(FIRST_SUBDIVIDED_SEASON - 1))

    def test_a_subdivision_label_from_1978_is_era_proof(self) -> None:
        self.assertTrue(subdivision_label_is_era_proof(FIRST_SUBDIVIDED_SEASON))
        self.assertTrue(subdivision_label_is_era_proof(2026))

    def test_an_unreadable_season_cannot_be_era_proof(self) -> None:
        self.assertFalse(subdivision_label_is_era_proof(None))


class ReconcileTests(unittest.TestCase):
    def test_an_agreeing_label_is_reported_as_agreeing(self) -> None:
        result = reconcile(1980, DIVISION_I_A_AND_I_AA)
        self.assertEqual(result["state"], "AGREES")

    def test_a_disagreeing_label_is_reported_not_replaced(self) -> None:
        result = reconcile(1980, FBS_AND_FCS)
        self.assertEqual(result["state"], "DISAGREES")
        self.assertEqual(result["declared_era"], FBS_AND_FCS)
        self.assertEqual(result["expected_era"], DIVISION_I_A_AND_I_AA)

    def test_a_missing_label_is_absent_not_a_disagreement(self) -> None:
        for value in (None, "", "None"):
            with self.subTest(value=repr(value)):
                self.assertEqual(reconcile(2026, value)["state"], "ABSENT")

    def test_reconcile_never_returns_the_expected_label_as_the_declared_one(self) -> None:
        result = reconcile(2026, None)
        self.assertIsNone(result["declared_era"])
        self.assertEqual(result["expected_era"], FBS_AND_FCS)


if __name__ == "__main__":
    unittest.main()

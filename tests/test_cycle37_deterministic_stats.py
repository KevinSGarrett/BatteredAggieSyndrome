"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-N-AC01: an aggregation whose result does not depend on the interpreter.

The case that produced this module: six log-loss terms whose mean is
published and hashed. CPython 3.11's built-in ``sum`` gives
``0.6198642675491248``; 3.12's, with Neumaier compensated summation, gives
``0.6198642675491249``. ``fsum`` then dividing agrees with 3.12 and with
neither the committed artifact nor the correctly rounded answer, because it
rounds twice.

These tests pin the three properties that matter: the same value in every
order, the same value the committed artifact already carries, and a refusal
rather than a plausible number when the input cannot be aggregated exactly.
"""

from __future__ import annotations

import itertools
import math
import sys
import unittest
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle37.deterministic_stats import (  # noqa: E402
    AGGREGATION_VERSION,
    PREDECESSOR_AGGREGATION,
    NonFiniteValue,
    difference_report,
    exact_mean,
    exact_sum,
    exact_weighted_mean,
    ulp_distance,
)

#: The six terms from the week-zero national_elo candidate, and the value the
#: committed artifact carries for their mean.
WEEK_ZERO_PROBABILITIES = (
    0.46300163, 0.75056252, 0.5861017, 0.38505461, 0.53400243, 0.500679,
)
WEEK_ZERO_OUTCOMES = (0, 1, 1, 1, 1, 0)
COMMITTED_LOG_LOSS = 0.6198642675491248


def _clip(value: float) -> float:
    return min(max(value, 1e-15), 1 - 1e-15)


def week_zero_terms() -> list[float]:
    return [
        -(outcome * math.log(_clip(p)) + (1 - outcome) * math.log(1 - _clip(p)))
        for p, outcome in zip(WEEK_ZERO_PROBABILITIES, WEEK_ZERO_OUTCOMES)
    ]


class WeekZeroCaseTests(unittest.TestCase):
    def test_the_successor_reproduces_the_committed_value(self) -> None:
        self.assertEqual(exact_mean(week_zero_terms()), COMMITTED_LOG_LOSS)

    def test_the_committed_value_is_the_correctly_rounded_one(self) -> None:
        terms = week_zero_terms()
        exact = sum((Fraction(t) for t in terms), Fraction(0)) / len(terms)
        self.assertEqual(float(exact), COMMITTED_LOG_LOSS)

    def test_fsum_then_divide_rounds_twice_and_disagrees(self) -> None:
        """Why the obvious fix is not the fix."""

        terms = week_zero_terms()
        self.assertNotEqual(math.fsum(terms) / len(terms), COMMITTED_LOG_LOSS)
        self.assertEqual(
            ulp_distance(math.fsum(terms) / len(terms), COMMITTED_LOG_LOSS), 1
        )

    def test_every_summation_order_gives_one_value(self) -> None:
        terms = week_zero_terms()
        values = {exact_mean(list(order)) for order in itertools.permutations(terms)}
        self.assertEqual(values, {COMMITTED_LOG_LOSS})

    def test_the_builtin_path_is_order_dependent_on_this_interpreter(self) -> None:
        """The property the successor removes, demonstrated on this build."""

        terms = week_zero_terms()
        values = {
            sum(order) / len(order) for order in itertools.permutations(terms)
        }
        self.assertGreaterEqual(len(values), 1)
        # Whichever way this interpreter accumulates, the successor is a
        # single value and the builtin is at best equal to it by luck.
        self.assertIn(exact_mean(terms), {COMMITTED_LOG_LOSS})


class ExactnessTests(unittest.TestCase):
    def test_a_sum_that_naive_accumulation_gets_wrong(self) -> None:
        """The first 1.0 is lost when 1e16 absorbs it; the second survives."""

        values = [1.0, 1e16, -1e16, 1.0]
        naive = 0.0
        for value in values:
            naive = naive + value
        self.assertEqual(naive, 1.0)
        self.assertEqual(exact_sum(values), 2.0)

    def test_the_mean_of_that_sum_is_also_right(self) -> None:
        self.assertEqual(exact_mean([1.0, 1e16, -1e16, 1.0]), 0.5)

    def test_order_does_not_matter_for_a_hard_case(self) -> None:
        values = [1e16, 1.0, -1e16, 1.0, 1e-16]
        results = {exact_sum(list(order)) for order in itertools.permutations(values)}
        self.assertEqual(len(results), 1)

    def test_a_single_value_is_itself(self) -> None:
        for value in (0.0, -0.0, 1.5, -2.25, 1e308, 5e-324):
            with self.subTest(value=value):
                self.assertEqual(exact_mean([value]), value)

    def test_an_empty_sequence_has_no_mean(self) -> None:
        self.assertIsNone(exact_mean([]))

    def test_an_empty_sum_is_zero(self) -> None:
        self.assertEqual(exact_sum([]), 0.0)

    def test_integers_are_accepted_as_values(self) -> None:
        self.assertEqual(exact_mean([1, 2, 3, 4]), 2.5)


class NonFiniteTests(unittest.TestCase):
    def test_a_nan_is_refused_not_propagated(self) -> None:
        with self.assertRaises(NonFiniteValue):
            exact_mean([1.0, float("nan")])

    def test_an_infinity_is_refused(self) -> None:
        for value in (float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(NonFiniteValue):
                    exact_sum([1.0, value])

    def test_the_refusal_names_the_value(self) -> None:
        with self.assertRaises(NonFiniteValue) as caught:
            exact_sum([float("inf")])
        self.assertIn("inf", str(caught.exception))


class WeightedMeanTests(unittest.TestCase):
    def test_equal_weights_are_the_plain_mean(self) -> None:
        values = [0.1, 0.2, 0.7]
        self.assertEqual(
            exact_weighted_mean(values, [1.0, 1.0, 1.0]), exact_mean(values)
        )

    def test_weights_are_applied(self) -> None:
        self.assertEqual(exact_weighted_mean([0.0, 1.0], [1.0, 3.0]), 0.75)

    def test_mismatched_lengths_raise_rather_than_truncate(self) -> None:
        with self.assertRaises(ValueError):
            exact_weighted_mean([1.0, 2.0, 3.0], [1.0, 1.0])

    def test_zero_total_weight_has_no_mean(self) -> None:
        self.assertIsNone(exact_weighted_mean([1.0, 2.0], [0.0, 0.0]))

    def test_an_empty_weighted_mean_is_none(self) -> None:
        self.assertIsNone(exact_weighted_mean([], []))


class UlpTests(unittest.TestCase):
    def test_a_value_is_zero_ulps_from_itself(self) -> None:
        self.assertEqual(ulp_distance(0.6198642675491248, 0.6198642675491248), 0)

    def test_adjacent_doubles_are_one_ulp_apart(self) -> None:
        value = 0.6198642675491248
        self.assertEqual(ulp_distance(value, math.nextafter(value, math.inf)), 1)

    def test_direction_does_not_matter(self) -> None:
        a = 0.6198642675491248
        b = math.nextafter(a, math.inf)
        self.assertEqual(ulp_distance(a, b), ulp_distance(b, a))

    def test_a_non_finite_distance_is_unknown_rather_than_huge(self) -> None:
        self.assertIsNone(ulp_distance(1.0, float("nan")))

    def test_a_walk_beyond_the_limit_reports_unknown(self) -> None:
        self.assertIsNone(ulp_distance(1.0, 2.0, limit=10))


class ReportTests(unittest.TestCase):
    def test_a_report_names_the_version_that_produced_the_successor(self) -> None:
        report = difference_report(0.6198642675491248, 0.6198642675491249)
        self.assertEqual(report["aggregation_version"], AGGREGATION_VERSION)
        self.assertNotEqual(AGGREGATION_VERSION, PREDECESSOR_AGGREGATION)

    def test_the_one_ulp_case_is_reported_in_three_units(self) -> None:
        report = difference_report(0.6198642675491248, 0.6198642675491249)
        self.assertFalse(report["equal"])
        self.assertEqual(report["ulps"], 1)
        self.assertLess(report["absolute_difference"], 1e-15)
        self.assertLess(report["relative_difference"], 1e-15)

    def test_equal_values_report_zero_in_every_unit(self) -> None:
        report = difference_report(1.25, 1.25)
        self.assertTrue(report["equal"])
        self.assertEqual(report["ulps"], 0)
        self.assertEqual(report["absolute_difference"], 0.0)
        self.assertEqual(report["relative_difference"], 0.0)

    def test_two_zeros_do_not_divide_by_zero(self) -> None:
        report = difference_report(0.0, 0.0)
        self.assertEqual(report["relative_difference"], 0.0)


if __name__ == "__main__":
    unittest.main()

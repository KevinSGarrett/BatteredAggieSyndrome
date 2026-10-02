"""Cycle #37 - Attempt #2 - ACTUAL_STATE: the numpy-independent fit successor (W37R-17)."""

from __future__ import annotations

import random
import unittest

import numpy as np

from aggie_analytics.cycle37 import deterministic_fit as fit
from aggie_analytics.modeling import national_expectation_baselines as baselines


def _problem(rows: int = 400, width: int = 6, seed: int = 37) -> tuple[list[list[float]], list[float], list[float]]:
    rng = random.Random(seed)
    design = [[1.0] + [rng.gauss(0.0, 1.0) for _ in range(width - 1)] for _ in range(rows)]
    truth = [rng.uniform(-1.0, 1.0) for _ in range(width)]
    margin = [sum(x * b for x, b in zip(row, truth)) + rng.gauss(0.0, 0.5) for row in design]
    outcome = [1.0 if m + rng.gauss(0.0, 1.0) > 0 else 0.0 for m in margin]
    return design, margin, outcome


class DeterministicFitTests(unittest.TestCase):
    """Same arithmetic everywhere: exactly rounded reductions and a fixed-order solve."""

    def test_ridge_agrees_with_the_numpy_estimator(self) -> None:
        design, margin, _ = _problem()
        ours = fit.fit_ridge(design, margin, l2_lambda=1.0)
        theirs = baselines.fit_ridge(np.array(design), np.array(margin), l2_lambda=1.0)
        self.assertLess(max(abs(a - b) for a, b in zip(ours, theirs)), 1e-12)

    def test_logistic_agrees_with_the_numpy_estimator(self) -> None:
        design, _, outcome = _problem()
        kwargs = {"l2_lambda": 1.0, "iterations": 25, "tolerance": 1e-10}
        ours = fit.fit_logistic_l2(design, outcome, **kwargs)
        theirs = baselines.fit_logistic_l2(np.array(design), np.array(outcome), **kwargs)
        self.assertLess(max(abs(a - b) for a, b in zip(ours, theirs)), 1e-10)

    def test_row_order_does_not_change_a_single_bit(self) -> None:
        design, margin, outcome = _problem()
        order = list(range(len(design)))
        random.Random(1).shuffle(order)
        shuffled = [design[i] for i in order]
        self.assertEqual(fit.fit_ridge(design, margin, l2_lambda=1.0),
                         fit.fit_ridge(shuffled, [margin[i] for i in order], l2_lambda=1.0))
        kwargs = {"l2_lambda": 1.0, "iterations": 25, "tolerance": 1e-10}
        self.assertEqual(fit.fit_logistic_l2(design, outcome, **kwargs),
                         fit.fit_logistic_l2(shuffled, [outcome[i] for i in order], **kwargs))

    def test_a_singular_system_is_refused_not_answered_another_way(self) -> None:
        design = [[1.0, 2.0, 4.0], [1.0, 3.0, 6.0], [1.0, 5.0, 10.0]]
        with self.assertRaises(fit.DeterministicFitError):
            fit.fit_ridge(design, [1.0, 2.0, 3.0], l2_lambda=0.0)

    def test_the_intercept_is_not_penalised(self) -> None:
        design = [[1.0, 0.0]] * 50
        beta = fit.fit_ridge(design, [3.0] * 50, l2_lambda=1000.0)
        self.assertEqual(beta[0], 3.0)


if __name__ == "__main__":
    unittest.main()

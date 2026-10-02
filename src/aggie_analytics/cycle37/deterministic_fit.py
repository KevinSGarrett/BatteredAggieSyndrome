"""Cycle #37 - Attempt #2 - ACTUAL_STATE

A versioned, interpreter-invariant successor for the national suite's two
estimators (W37R-17, R37-N-AC01).

``national_expectation_baselines.fit_logistic_l2`` and ``fit_ridge`` reduce
with numpy's BLAS/LAPACK and evaluate ``np.exp``. Their summation order and
vectorised kernels belong to the installed numpy build, so the same inputs can
give different last-place bits under different interpreters' environments,
and an iterative fit amplifies that. This module computes the same estimators
from Python floats only:

* every reduction is ``math.fsum`` -- the exactly rounded sum, independent of
  order, interpreter and platform;
* every other operation is a single IEEE-754 multiply, divide, add or
  subtract in a fixed order, or ``math.exp`` from the platform C library;
* the linear systems are solved by Gaussian elimination with partial pivoting
  in a fixed order.

It mirrors the original arithmetic (the intercept is unpenalised, eta is
clipped to [-30, 30], weights are floored at 1e-9, and Newton stops when the
largest step is below the tolerance). It does not fall back to least squares:
a singular system is refused rather than answered by a different method.

The published modules are not changed. Their committed gates bind the module
bytes, so adopting this successor there re-binds committed artifacts. That is
an owner decision; this module only makes the successor available and
qualifiable.
"""

from __future__ import annotations

import math
from operator import mul
from typing import Sequence

VERSION = "BAS-DETERMINISTIC-FIT-v37.1"


class DeterministicFitError(ValueError):
    """The inputs cannot be fitted by this estimator without changing method."""


def _columns(design: Sequence[Sequence[float]] | object) -> list[list[float]]:
    rows = design.tolist() if hasattr(design, "tolist") else [list(row) for row in design]
    if not rows:
        raise DeterministicFitError("empty design")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise DeterministicFitError("ragged design")
    return [[float(row[j]) for row in rows] for j in range(width)]


def _vector(values: Sequence[float] | object) -> list[float]:
    items = values.tolist() if hasattr(values, "tolist") else list(values)
    return [float(v) for v in items]


def _dot(left: list[float], right: list[float]) -> float:
    return math.fsum(map(mul, left, right))


def solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting, fixed order, no fallback."""

    size = len(vector)
    a = [list(map(float, row)) + [float(vector[i])] for i, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda r: (abs(a[r][column]), -r))
        if a[pivot][column] == 0.0 or not math.isfinite(a[pivot][column]):
            raise DeterministicFitError(f"singular system at column {column}")
        if pivot != column:
            a[column], a[pivot] = a[pivot], a[column]
        head = a[column][column]
        for r in range(column + 1, size):
            factor = a[r][column] / head
            if factor == 0.0:
                continue
            row, source = a[r], a[column]
            for c in range(column, size + 1):
                row[c] = row[c] - factor * source[c]
    solution = [0.0] * size
    for r in range(size - 1, -1, -1):
        known = math.fsum(a[r][c] * solution[c] for c in range(r + 1, size))
        solution[r] = (a[r][size] - known) / a[r][r]
    return solution


def _penalty(width: int, l2_lambda: float) -> list[float]:
    return [0.0] + [float(l2_lambda)] * (width - 1)


def fit_ridge(design, target, *, l2_lambda: float) -> list[float]:
    cols, y = _columns(design), _vector(target)
    width, penalty = len(cols), _penalty(len(cols), l2_lambda)
    left = [[_dot(cols[j], cols[k]) + (penalty[j] if j == k else 0.0) for k in range(width)] for j in range(width)]
    right = [_dot(cols[j], y) for j in range(width)]
    return solve(left, right)


def fit_logistic_l2(design, target, *, l2_lambda: float, iterations: int, tolerance: float) -> list[float]:
    cols, y = _columns(design), _vector(target)
    width, rows = len(cols), len(y)
    penalty = _penalty(width, l2_lambda)
    beta = [0.0] * width
    for _ in range(int(iterations)):
        eta = [math.fsum(cols[j][i] * beta[j] for j in range(width)) for i in range(rows)]
        probability = [1.0 / (1.0 + math.exp(-min(30.0, max(-30.0, e)))) for e in eta]
        weight = [max(p * (1.0 - p), 1e-9) for p in probability]
        residual = [t - p for t, p in zip(y, probability)]
        gradient = [_dot(cols[j], residual) - penalty[j] * beta[j] for j in range(width)]
        weighted = [list(map(mul, cols[j], weight)) for j in range(width)]
        hessian = [[0.0] * width for _ in range(width)]
        for j in range(width):
            for k in range(j, width):
                value = _dot(weighted[j], cols[k])
                hessian[j][k] = value
                hessian[k][j] = value
            hessian[j][j] += penalty[j]
        step = solve(hessian, gradient)
        beta = [b + s for b, s in zip(beta, step)]
        if max(abs(s) for s in step) < tolerance:
            break
    return beta

"""Small named successor fit interface for the national retrospective reference comparison (BAT-423, Cycle #56
TP56-A01 section 3).

The accepted C37 estimators (:mod:`aggie_analytics.cycle37.deterministic_fit`) assume an unpenalized intercept, sum
objectives and a step-size stopping rule. This interface keeps their deterministic primitive -- the fixed-order
Gaussian elimination with partial pivoting, :func:`aggie_analytics.cycle37.deterministic_fit.solve` -- and fits the
frozen TP56 objectives instead:

* zero intercept; every column carries the same L2 penalty ``lambda`` (frozen at 1);
* paired orientation rows, each with weight 1/2, so one canonical game has weight one;
* logistic: ``J(beta) = sum_i w_i * BCE(z_i . beta, y_i) / sum_i w_i + (lambda/2) * sum_j beta_j**2`` minimized by
  Newton steps from zero, each followed by halving backtracking from step one (at most 30 halvings) until the objective
  does not increase; convergence is a gradient infinity norm of at most ``tolerance`` (1e-10) within 100 Newton steps;
  exhausted backtracking or no convergence is a recorded failure, never silently accepted;
* ridge: ``J(beta) = sum_i w_i * (m_i - z_i . beta)**2 / (2 * sum_i w_i) + (lambda/2) * sum_j beta_j**2`` solved from
  its regularized normal equations, with finite coefficients and a normal-equation residual infinity norm of at most
  ``residual_tolerance`` (1e-8) verified.

Every reduction is ``math.fsum`` in a fixed row order; every other operation is one binary64 operation in a fixed
order, ``math.exp``/``math.log1p`` of the pinned CPython; the sigmoid and the cross-entropy are computed in their
numerically stable forms. Nothing here reads data, labels or files: callers pass the rows.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Sequence

from aggie_analytics.cycle37.deterministic_fit import DeterministicFitError, solve

VERSION = "BAS-REFERENCE-FIT-v56.1"
LAMBDA = 1.0
MAX_NEWTON_STEPS = 100
GRADIENT_TOLERANCE = 1e-10
MAX_HALVINGS = 30
RESIDUAL_TOLERANCE = 1e-8


class ReferenceFitError(ValueError):
    """A refused fit input or a recorded fit failure; ``code`` is a stable reason."""

    def __init__(self, code: str, message: str, record: dict[str, Any] | None = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.record = record or {}


@dataclass(frozen=True)
class Row:
    """One weighted oriented design row: the scaled design values, the label and the row weight."""

    values: tuple[float, ...]
    label: float
    weight: float


@dataclass
class FitResult:
    coefficients: list[float]
    state: str
    iterations: int
    objective: float
    gradient_inf_norm: float
    trajectory: list[dict[str, Any]] = field(default_factory=list)
    residual_inf_norm: float | None = None


def sigmoid(eta: float) -> float:
    """The logistic function in its stable form: no overflow for any finite ``eta``."""
    if eta >= 0.0:
        return 1.0 / (1.0 + math.exp(-eta))
    e = math.exp(eta)
    return e / (1.0 + e)


def softplus(t: float) -> float:
    """``log(1 + exp(t))`` in its stable form."""
    if t > 0.0:
        return t + math.log1p(math.exp(-t))
    return math.log1p(math.exp(t))


def bce(eta: float, y: float) -> float:
    """Binary cross-entropy of a linear predictor: ``y * softplus(-eta) + (1 - y) * softplus(eta)``."""
    return y * softplus(-eta) + (1.0 - y) * softplus(eta)


def linear(values: Sequence[float], beta: Sequence[float]) -> float:
    """The linear predictor ``z . beta`` as the exactly rounded sum of the binary64 products (fixed column order)."""
    return math.fsum(v * b for v, b in zip(values, beta))


def _check_rows(rows: Sequence[Row], width: int) -> float:
    if not rows:
        raise ReferenceFitError("FIT_EMPTY", "no training rows")
    for row in rows:
        if len(row.values) != width:
            raise ReferenceFitError("FIT_RAGGED", "design rows differ in width")
        if not all(math.isfinite(v) for v in row.values) or not math.isfinite(row.label) or \
                not (math.isfinite(row.weight) and row.weight > 0.0):
            raise ReferenceFitError("FIT_NONFINITE_INPUT", "a design value, label or weight is not finite/positive")
    return math.fsum(row.weight for row in rows)


def logistic_objective(rows: Sequence[Row], beta: Sequence[float], total_weight: float, l2_lambda: float) -> float:
    data = math.fsum(row.weight * bce(linear(row.values, beta), row.label) for row in rows) / total_weight
    return data + 0.5 * l2_lambda * math.fsum(b * b for b in beta)


def logistic_gradient(rows: Sequence[Row], beta: Sequence[float], total_weight: float, l2_lambda: float
                      ) -> list[float]:
    residual = [(row.weight, sigmoid(linear(row.values, beta)) - row.label) for row in rows]
    return [math.fsum(w * (r * row.values[j]) for (w, r), row in zip(residual, rows)) / total_weight
            + l2_lambda * beta[j] for j in range(len(beta))]


def logistic_hessian(rows: Sequence[Row], beta: Sequence[float], total_weight: float, l2_lambda: float
                     ) -> list[list[float]]:
    width = len(beta)
    curvature = []
    for row in rows:
        eta = linear(row.values, beta)
        curvature.append(row.weight * (sigmoid(eta) * sigmoid(-eta)))
    hessian = [[0.0] * width for _ in range(width)]
    for j in range(width):
        for k in range(j, width):
            value = math.fsum(c * (row.values[j] * row.values[k]) for c, row in zip(curvature, rows)) / total_weight
            if j == k:
                value += l2_lambda
            hessian[j][k] = value
            hessian[k][j] = value
    return hessian


def fit_logistic(rows: Sequence[Row], width: int, *, l2_lambda: float = LAMBDA,
                 max_steps: int = MAX_NEWTON_STEPS, tolerance: float = GRADIENT_TOLERANCE,
                 max_halvings: int = MAX_HALVINGS) -> FitResult:
    """Newton from zero with halving backtracking; a failure raises :class:`ReferenceFitError` carrying the record."""
    total = _check_rows(rows, width)
    beta = [0.0] * width
    objective = logistic_objective(rows, beta, total, l2_lambda)
    trajectory: list[dict[str, Any]] = []
    for step in range(max_steps + 1):
        gradient = logistic_gradient(rows, beta, total, l2_lambda)
        norm = max(abs(g) for g in gradient)
        entry = {"step": step, "objective": repr(objective), "gradient_inf_norm": repr(norm)}
        if not (math.isfinite(objective) and math.isfinite(norm)):
            trajectory.append(entry)
            raise ReferenceFitError("FIT_NONFINITE", "the objective or gradient is not finite",
                                    {"trajectory": trajectory})
        if norm <= tolerance:
            trajectory.append(entry)
            return FitResult(coefficients=beta, state="CONVERGED", iterations=step, objective=objective,
                             gradient_inf_norm=norm, trajectory=trajectory)
        if step == max_steps:
            trajectory.append(entry)
            raise ReferenceFitError("FIT_NOT_CONVERGED", f"gradient {norm!r} after {max_steps} Newton steps",
                                    {"trajectory": trajectory})
        hessian = logistic_hessian(rows, beta, total, l2_lambda)
        try:
            direction = solve(hessian, [-g for g in gradient])
        except DeterministicFitError as exc:
            trajectory.append(entry)
            raise ReferenceFitError("FIT_SINGULAR", str(exc), {"trajectory": trajectory}) from exc
        scale, halvings = 1.0, 0
        candidate = [b + scale * d for b, d in zip(beta, direction)]
        value = logistic_objective(rows, candidate, total, l2_lambda)
        while not value <= objective:
            if halvings == max_halvings:
                entry.update(halvings=halvings, step_scale=repr(scale))
                trajectory.append(entry)
                raise ReferenceFitError("FIT_BACKTRACK_EXHAUSTED",
                                        f"the objective still increased after {max_halvings} halvings",
                                        {"trajectory": trajectory})
            scale = scale / 2.0
            halvings += 1
            candidate = [b + scale * d for b, d in zip(beta, direction)]
            value = logistic_objective(rows, candidate, total, l2_lambda)
        entry.update(halvings=halvings, step_scale=repr(scale))
        trajectory.append(entry)
        beta, objective = candidate, value
    raise AssertionError("unreachable")


def ridge_objective(rows: Sequence[Row], beta: Sequence[float], total_weight: float, l2_lambda: float) -> float:
    data = math.fsum(row.weight * (row.label - linear(row.values, beta)) ** 2 for row in rows) / (2.0 * total_weight)
    return data + 0.5 * l2_lambda * math.fsum(b * b for b in beta)


def ridge_system(rows: Sequence[Row], width: int, total_weight: float, l2_lambda: float
                 ) -> tuple[list[list[float]], list[float]]:
    """The regularized normal equations ``(Z'WZ / sum w + lambda I) beta = Z'Wm / sum w``."""
    left = [[0.0] * width for _ in range(width)]
    for j in range(width):
        for k in range(j, width):
            value = math.fsum(row.weight * (row.values[j] * row.values[k]) for row in rows) / total_weight
            if j == k:
                value += l2_lambda
            left[j][k] = value
            left[k][j] = value
    right = [math.fsum(row.weight * (row.label * row.values[j]) for row in rows) / total_weight for j in range(width)]
    return left, right


def fit_ridge(rows: Sequence[Row], width: int, *, l2_lambda: float = LAMBDA,
              residual_tolerance: float = RESIDUAL_TOLERANCE) -> FitResult:
    total = _check_rows(rows, width)
    left, right = ridge_system(rows, width, total, l2_lambda)
    try:
        beta = solve(left, right)
    except DeterministicFitError as exc:
        raise ReferenceFitError("FIT_SINGULAR", str(exc)) from exc
    if not all(math.isfinite(b) for b in beta):
        raise ReferenceFitError("FIT_NONFINITE", "a ridge coefficient is not finite")
    residual = [math.fsum([*(left[j][k] * beta[k] for k in range(width)), -right[j]]) for j in range(width)]
    norm = max(abs(r) for r in residual)
    objective = ridge_objective(rows, beta, total, l2_lambda)
    if not norm <= residual_tolerance:
        raise ReferenceFitError("FIT_RESIDUAL", f"normal-equation residual {norm!r} exceeds {residual_tolerance!r}",
                                {"residual_inf_norm": repr(norm)})
    return FitResult(coefficients=beta, state="SOLVED", iterations=0, objective=objective, gradient_inf_norm=norm,
                     residual_inf_norm=norm, trajectory=[{"residual_inf_norm": repr(norm),
                                                          "objective": repr(objective)}])

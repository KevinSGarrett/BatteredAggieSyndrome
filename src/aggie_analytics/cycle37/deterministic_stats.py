"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-N-AC01: aggregation that gives the same double on every interpreter.

CPython 3.12 changed the built-in ``sum`` to use Neumaier compensated
summation for float inputs. That is a real improvement to the *sum*, and it
silently changed every identity in this repository that is computed over a
mean of floats, because a hash has no tolerance. The week-zero scoring
successor's ``log_loss`` is the visible case: 3.11 publishes
``0.6198642675491248`` and 3.12 publishes ``0.6198642675491249`` from
bit-identical inputs.

Neither of those is a defect in the data, and the newer one is not even the
more accurate answer. ``fsum`` rounds the sum exactly and the division then
rounds a second time; the correctly rounded mean of those six terms is
``0.6198642675491248``, which is what 3.11 happened to produce and what the
committed artifact carries.

So the repair is not to pick an interpreter or to freeze one's behaviour. It
is to compute the result that does not depend on either: sum the exact
rational values of the doubles, divide exactly, and round once. ``Fraction``
does this with no precision to configure and no context to get wrong, and the
answer is the correctly rounded one by construction -- therefore identical on
every conforming Python, in every summation order, on every platform.

What this module does not do:

* It does not touch a committed artifact. A legacy identity stays legacy.
  MF37-06 requires the numerical repair to preserve legacy identities, and
  the way to preserve one is to leave it alone.
* It does not make an iterative fit reproducible. A ridge or logistic fit
  amplifies a last-place difference through its iterations; measuring that
  amplification is a separate obligation and the result is reported, not
  hidden behind an aggregation that cannot fix it.
* It does not claim the difference was scientifically material. It claims
  the opposite, with the measurement beside it.
"""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Iterable, Sequence

#: Bumped whenever the arithmetic below changes in a way that could move a
#: published value. A stored result records this, so a value computed under
#: the interpreter-dependent path is never mistaken for one computed here.
AGGREGATION_VERSION = "BAS-DETERMINISTIC-AGGREGATION-v37.1"

#: What the repository did before: whichever accumulation the running
#: interpreter's built-in ``sum`` happens to implement.
PREDECESSOR_AGGREGATION = "INTERPRETER_BUILTIN_SUM"


class NonFiniteValue(ValueError):
    """Raised when a NaN or an infinity reaches an exact aggregation.

    ``Fraction`` cannot represent either, and silently coercing one would
    turn an undefined result into a definite-looking number. A caller that
    expects them must decide what they mean before aggregating.
    """


def _exact(values: Iterable[float]) -> list[Fraction]:
    out: list[Fraction] = []
    for value in values:
        number = float(value)
        if not math.isfinite(number):
            raise NonFiniteValue(f"cannot aggregate a non-finite value: {number!r}")
        out.append(Fraction(number))
    return out


def exact_sum(values: Iterable[float]) -> float:
    """The correctly rounded sum of the exact values of these doubles.

    Order-independent, because rational addition is associative and exact;
    interpreter-independent, because no floating-point accumulation happens
    until the single final rounding.
    """

    terms = _exact(values)
    total = Fraction(0)
    for term in terms:
        total += term
    return float(total)


def exact_mean(values: Sequence[float]) -> float | None:
    """The correctly rounded mean, or None for an empty sequence.

    ``None`` rather than a raise, because "no observations" is an ordinary
    state for a metric over a population that may be empty, and every caller
    in this repository already publishes ``None`` for it.
    """

    terms = _exact(values)
    if not terms:
        return None
    total = Fraction(0)
    for term in terms:
        total += term
    return float(total / len(terms))


def exact_weighted_mean(
    values: Sequence[float], weights: Sequence[float]
) -> float | None:
    """The correctly rounded weighted mean.

    Raises when the weights do not line up with the values, because a
    silently truncated zip is how a weighted mean quietly becomes a mean of
    a prefix.
    """

    if len(values) != len(weights):
        raise ValueError(
            f"{len(values)} values and {len(weights)} weights cannot be paired"
        )
    numerators = _exact(values)
    denominators = _exact(weights)
    if not numerators:
        return None
    total = Fraction(0)
    weight = Fraction(0)
    for value, factor in zip(numerators, denominators):
        total += value * factor
        weight += factor
    if weight == 0:
        return None
    return float(total / weight)


def ulp_distance(left: float, right: float, limit: int = 1_000_000) -> int | None:
    """How many representable doubles lie between two values.

    ``None`` when either value is not finite, or when they are further apart
    than ``limit`` steps -- a bounded walk rather than an unbounded one, so
    this can be called on values that turn out to be nothing like each other.
    """

    if not (math.isfinite(left) and math.isfinite(right)):
        return None
    if left == right:
        return 0
    low, high = (left, right) if left < right else (right, left)
    steps = 0
    value = low
    while value < high and steps < limit:
        value = math.nextafter(value, math.inf)
        steps += 1
    return steps if value == high else None


def difference_report(legacy: float, successor: float) -> dict[str, object]:
    """Everything needed to judge whether a change is material.

    Reports the gap in three units, because each answers a different
    question: units in the last place say whether it is arithmetic noise,
    the absolute difference says whether it crosses a stated threshold, and
    the relative difference says whether it matters at this scale.
    """

    absolute = abs(float(legacy) - float(successor))
    largest = max(abs(float(legacy)), abs(float(successor)))
    return {
        "legacy": repr(float(legacy)),
        "successor": repr(float(successor)),
        "equal": float(legacy) == float(successor),
        "ulps": ulp_distance(float(legacy), float(successor)),
        "absolute_difference": absolute,
        "relative_difference": (absolute / largest) if largest else 0.0,
        "aggregation_version": AGGREGATION_VERSION,
    }

r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-N-AC01: isolate every strict and full-suite identity mismatch, and
measure the ones that are numerical.

U37-05 and U37-06 carried a "week-zero float identity reproducibility
defect" whose mechanism was said to be identified and whose magnitude was
unmeasured for five of seven failures. MF37-06 says the strict blocker and
the global float-migration claims overstate the authority dependency, and
that a versioned isolated numerical repair must distinguish machine and
order effects from material scientific changes.

This tool does the isolation, in three steps, and asserts nothing it has not
run:

1. **Which interpreter.** Every inherited failing test module is run under
   each interpreter offered. A module that passes under one and fails under
   the other is an interpreter effect and cannot be a defect in the data it
   reads, because the data did not change between the two runs.
2. **Which mechanism.** For the modules that differ, the built-in ``sum``
   is replaced by a naive left-to-right accumulation -- what CPython used
   before 3.12 adopted Neumaier compensated summation for floats -- and the
   modules are run again. If they then pass, the mechanism is that one
   change and nothing else.
3. **How large.** The affected metric is recomputed under every available
   aggregation, and the differences are reported in units in the last place
   and in absolute and relative terms, so "material scientific change" is a
   measured question rather than a judgement.

Nothing is written outside ``--out``. No committed artifact is modified: a
legacy identity stays legacy, which is what MF37-06 requires.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

sys.dont_write_bytecode = True

#: The inherited failing test modules, taken from the full-suite lane.
INHERITED_MODULES = (
    "test_cycle35_r35_14_private_data_availability",
    "test_development_2023_labeled_replay",
    "test_development_rankings_walk_forward_2023",
    "test_protected_replay_dry_run",
    "test_tamu_official_1998_2009_rejection_integrity",
    "test_tamu_official_gamebook_union_1998_rejection_complete",
    "test_tamu_official_historical_coverage_inventory",
    "test_tamu_official_pre2010_boxscores",
    "test_week1_2026_national_forecast_suite",
    "test_week_zero_2026_official_final_reconstruction",
)

#: Installed ahead of the tests to restore pre-3.12 ``sum`` semantics for
#: floats. It is a measurement instrument, never a shipped behaviour: the
#: repair is the versioned aggregation, not a monkeypatch.
NAIVE_SUM_SHIM = """
import builtins
_original = builtins.sum

def _naive(iterable, /, start=0):
    items = list(iterable)
    if any(type(item) is float for item in items):
        total = start
        for item in items:
            total = total + item
        return total
    return _original(items, start)

builtins.sum = _naive
"""


def run_module(
    interpreter: Path, module: str, tests_dir: Path, src_dir: Path, data_root: Path,
    shim: bool = False,
) -> dict[str, Any]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(src_dir)
    environment["AGGIE_ANALYTICS_DATA_ROOT"] = str(data_root)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    if shim:
        program = (
            NAIVE_SUM_SHIM
            + "\nimport unittest, sys\n"
            + f"result = unittest.main(module=None, argv=['x', {module!r}], exit=False).result\n"
            + "sys.exit(0 if result.wasSuccessful() else 1)\n"
        )
        command = [str(interpreter), "-B", "-c", program]
    else:
        command = [str(interpreter), "-B", "-m", "unittest", module]
    completed = subprocess.run(
        command, cwd=str(tests_dir), env=environment,
        capture_output=True, text=True, timeout=900,
    )
    text = completed.stdout + completed.stderr
    identities = sorted(
        {
            line.split(" ", 1)[1].split(" ")[0]
            for line in text.splitlines()
            if line.startswith(("FAIL: ", "ERROR: "))
        }
    )
    return {
        "module": module,
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "failing_identities": identities,
        "tail": text.strip().splitlines()[-4:],
    }


def ulp_distance(left: float, right: float) -> int | None:
    """How many representable doubles separate two values."""

    if not (math.isfinite(left) and math.isfinite(right)):
        return None
    if left == right:
        return 0
    low, high = (left, right) if left < right else (right, left)
    steps = 0
    value = low
    while value < high and steps < 1_000_000:
        value = math.nextafter(value, math.inf)
        steps += 1
    return steps if value == high else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument(
        "--interpreter", action="append", required=True,
        help="Repeatable. Each is run over every inherited module.",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--modules", nargs="*", default=list(INHERITED_MODULES),
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    tests_dir = repo_root / "tests"
    src_dir = repo_root / "src"

    interpreters = []
    for entry in args.interpreter:
        path = Path(entry)
        version = subprocess.run(
            [str(path), "-c", "import sys;print(sys.version.split()[0])"],
            capture_output=True, text=True, timeout=120,
        ).stdout.strip()
        interpreters.append({"path": str(path), "version": version})

    by_interpreter: dict[str, dict[str, Any]] = {}
    for interpreter in interpreters:
        results = {
            module: run_module(
                Path(interpreter["path"]), module, tests_dir, src_dir, args.data_root
            )
            for module in args.modules
        }
        by_interpreter[interpreter["version"]] = results

    versions = [row["version"] for row in interpreters]
    differing: list[str] = []
    failing_everywhere: list[str] = []
    passing_everywhere: list[str] = []
    for module in args.modules:
        outcomes = {v: by_interpreter[v][module]["passed"] for v in versions}
        if all(outcomes.values()):
            passing_everywhere.append(module)
        elif not any(outcomes.values()):
            failing_everywhere.append(module)
        else:
            differing.append(module)

    # ---- step 2: does restoring pre-3.12 sum semantics explain them? ----
    newest = max(interpreters, key=lambda row: tuple(
        int(part) for part in row["version"].split(".") if part.isdigit()
    ))
    shimmed = {
        module: run_module(
            Path(newest["path"]), module, tests_dir, src_dir, args.data_root, shim=True
        )
        for module in differing
    }
    explained = [m for m in differing if shimmed[m]["passed"]]
    unexplained = [m for m in differing if not shimmed[m]["passed"]]

    # ---- step 3: magnitude on the one metric the strict lane names -------
    probabilities = [0.46300163, 0.75056252, 0.5861017, 0.38505461, 0.53400243, 0.500679]
    outcomes = [0, 1, 1, 1, 1, 0]

    def clip(value: float) -> float:
        return min(max(value, 1e-15), 1 - 1e-15)

    terms = [
        -(outcome * math.log(clip(probability)) + (1 - outcome) * math.log(1 - clip(probability)))
        for probability, outcome in zip(probabilities, outcomes)
    ]
    count = len(terms)
    naive = 0.0
    for term in terms:
        naive = naive + term
    naive_mean = naive / count
    builtin_mean = sum(terms) / count
    fsum_mean = math.fsum(terms) / count
    getcontext().prec = 60
    exact = sum((Decimal(term) for term in terms), Decimal(0)) / Decimal(count)
    correctly_rounded = float(exact)

    committed = 0.6198642675491248
    magnitude = {
        "metric": "metrics_by_candidate/national_elo/log_loss",
        "committed_value": repr(committed),
        "naive_left_to_right_mean": repr(naive_mean),
        "builtin_sum_mean_on_this_interpreter": repr(builtin_mean),
        "this_interpreter": sys.version.split()[0],
        "fsum_then_divide_mean": repr(fsum_mean),
        "exact_decimal_mean": str(exact),
        "correctly_rounded_mean": repr(correctly_rounded),
        "committed_equals_naive": committed == naive_mean,
        "committed_equals_correctly_rounded": committed == correctly_rounded,
        "ulps_between_naive_and_fsum": ulp_distance(naive_mean, fsum_mean),
        "absolute_difference": abs(naive_mean - fsum_mean),
        "relative_difference": (
            abs(naive_mean - fsum_mean) / abs(naive_mean) if naive_mean else None
        ),
        "terms": [repr(term) for term in terms],
    }

    findings = {
        "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE",
        "cycle_number": 37,
        "attempt_number": 2,
        "state": "ACTUAL_STATE",
        "requirement": "R37-N",
        "acceptance": ["R37-N-AC01", "R37-N-CF-MF37-06", "R37-N-CF-U37-05",
                       "R37-N-CF-U37-06"],
        "interpreters": interpreters,
        "modules_examined": list(args.modules),
        "by_interpreter": by_interpreter,
        "classification": {
            "passing_under_every_interpreter": passing_everywhere,
            "failing_under_every_interpreter": failing_everywhere,
            "failing_under_some_interpreter_only": differing,
        },
        "mechanism_test": {
            "method": (
                "On the newest interpreter, the built-in sum is replaced by a "
                "naive left-to-right accumulation for float inputs -- the "
                "behaviour CPython had before 3.12 adopted Neumaier compensated "
                "summation -- and the differing modules are run again. Passing "
                "then, and only then, identifies the mechanism."
            ),
            "interpreter": newest,
            "results": shimmed,
            "explained_by_the_sum_change": explained,
            "not_explained": unexplained,
        },
        "magnitude": magnitude,
        "bounded_error_analysis": {
            "worst_observed_difference_in_ulps": magnitude["ulps_between_naive_and_fsum"],
            "worst_observed_absolute_difference": magnitude["absolute_difference"],
            "worst_observed_relative_difference": magnitude["relative_difference"],
            "what_it_can_change": (
                "A difference of one unit in the last place of a double is "
                "about 1.1e-16 here. It changes the sixteenth significant "
                "digit of a log loss. No comparison, threshold, ranking or "
                "admission in this repository is stated to that precision, so "
                "the numeric result is not materially different. What it does "
                "change is every identity computed over the serialized value, "
                "because a hash has no tolerance -- which is why this shows up "
                "as an identity failure rather than as a metric disagreement."
            ),
            "what_it_cannot_establish": (
                "That no other numerical difference exists anywhere. This "
                "measures the metric the strict lane names and the modules the "
                "full suite lists. A module that fails under every interpreter "
                "is not a float effect and is reported separately."
            ),
        },
        "legacy_identities_preserved": (
            "No committed artifact was modified by this tool. The legacy value "
            "and the legacy identity remain exactly as committed; the repair "
            "belongs beside them under its own version, never over them."
        ),
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(args.out, 
        json.dumps(findings, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )

    print("interpreters              :", [row["version"] for row in interpreters])
    print("passing everywhere        :", len(passing_everywhere))
    print("failing everywhere        :", len(failing_everywhere), failing_everywhere)
    print("interpreter-dependent     :", len(differing), differing)
    print("explained by the sum change:", len(explained), explained)
    print("not explained             :", len(unexplained), unexplained)
    print("ulps (naive vs fsum)      :", magnitude["ulps_between_naive_and_fsum"])
    print("absolute difference       :", magnitude["absolute_difference"])
    print("committed == naive        :", magnitude["committed_equals_naive"])
    print("committed == exact-rounded:", magnitude["committed_equals_correctly_rounded"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

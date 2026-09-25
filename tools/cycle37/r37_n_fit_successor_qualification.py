r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

W37R-17 / R37-N-AC01: qualify the numpy-independent fit successor
(aggie_analytics.cycle37.deterministic_fit) on the national suite's real fit
inputs, under every interpreter offered.

The decomposition (R37_N_FIT_DRIFT_DECOMPOSITION.json) showed that the three
fit calls receive bit-identical design matrices and targets on CPython 3.11.9
and 3.12.10, that the built-in ``sum`` is never called on floats on that path,
and that the same saved inputs give different coefficients under numpy 1.26.4
and 2.2.6. The drift is the numerical library's, so the successor computes the
same estimators without it.

For every saved input set and every interpreter this records the successor's
coefficients (as ``repr``) and reports:

* invariance -- the successor's bits are the same under every interpreter;
* distance -- the largest absolute and relative difference from each numpy
  environment's coefficients;
* published agreement -- whether rounding the successor to the 10 decimals the
  suite publishes reproduces the committed parameter rows, coefficient by
  coefficient;
* committed identities -- which environment, if any, reproduces the gate's
  ``fitted_parameter_identity`` (a hash of the unrounded coefficients);
* accuracy -- how nearly each solution satisfies its optimality condition
  on the same inputs, evaluated exactly. Every double is a dyadic rational,
  so X'X, X'y and X'(y - p) are computed exactly as scaled integer sums and
  the residual is formed in rational arithmetic: for ridge
  (X'X + L)b - X'y, for the L2 logistic fits X'(y - p(b)) - Lb with p(b)
  evaluated once, identically for every solution, with math.exp. No
  library's rounding is favoured.

The published modules and artifacts are not changed; adoption re-binds the
gate and is an owner decision.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKTREE = Path(__file__).resolve().parents[2]
if str(WORKTREE / "src") not in sys.path:
    sys.path.insert(0, str(WORKTREE / "src"))

from aggie_analytics.data.national_foundation_reconciliation import stable_hash
from aggie_analytics import atomic_io as _bas_atomic  # noqa: E402

KEYS = {0: "national_logistic_l2_beta", 1: "prior_only_beta", 2: "ridge_beta"}
CANDIDATES = {"national_logistic_l2_beta": "national_logistic_l2", "prior_only_beta": "prior_only",
              "ridge_beta": "national_margin_ridge"}
PARAMETER_SETS = {"national_logistic_l2_beta": "NATIONAL_LOGISTIC_L2_BETA", "prior_only_beta": "PRIOR_ONLY_BETA",
                  "ridge_beta": "NATIONAL_MARGIN_RIDGE_BETA"}

PROBE = r'''
import json, sys, time
from pathlib import Path
root, inputs, record_path, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
sys.path.insert(0, str(root / "src"))
import numpy as np
from aggie_analytics.cycle37 import deterministic_fit as fit
record = json.loads(record_path.read_text(encoding="utf-8"))
result = {"python": sys.version.split()[0], "numpy_used_only_to_load": np.__version__, "version": fit.VERSION,
          "calls": []}
for call in record["calls"]:
    design = np.load(inputs / f"{call['estimator']}_{call['call']}_design.npy", allow_pickle=False)
    target = np.load(inputs / f"{call['estimator']}_{call['call']}_target.npy", allow_pickle=False)
    started = time.perf_counter()
    beta = getattr(fit, call["estimator"])(design, target, **call["kwargs"])
    result["calls"].append({"call": call["call"], "estimator": call["estimator"], "beta": [repr(v) for v in beta],
                            "seconds": round(time.perf_counter() - started, 1)})
out.write_text(json.dumps(result, indent=1), encoding="utf-8")
'''


def _scaled(values: list[float]) -> tuple[list[int], int]:
    """Exact integers n_i and one shift k with values[i] == n_i / 2**k."""

    ratios = [v.as_integer_ratio() for v in values]
    shift = max(d.bit_length() - 1 for _n, d in ratios)
    return [n << (shift - (d.bit_length() - 1)) for n, d in ratios], shift


def _exact_dot(left: tuple[list[int], int], right: tuple[list[int], int]):
    from fractions import Fraction
    from operator import mul

    return Fraction(sum(map(mul, left[0], right[0])), 1 << (left[1] + right[1]))


def optimality(design, target, estimator: str, kwargs: dict[str, Any], solutions: dict[str, list[str]]) -> dict:
    """Largest absolute optimality residual of each solution, evaluated exactly."""

    import math
    from fractions import Fraction

    cols = [_scaled([float(v) for v in design[:, j].tolist()]) for j in range(design.shape[1])]
    raw = [[float(v) for v in design[:, j].tolist()] for j in range(design.shape[1])]
    y = [float(v) for v in target.tolist()]
    width = len(cols)
    lam = Fraction(float(kwargs["l2_lambda"]))
    penalty = [Fraction(0)] + [lam] * (width - 1)
    out = {}
    if estimator == "fit_ridge":
        target_scaled = _scaled(y)
        gram = [[None] * width for _ in range(width)]
        for j in range(width):
            for k in range(j, width):
                gram[j][k] = gram[k][j] = _exact_dot(cols[j], cols[k])
        right = [_exact_dot(cols[j], target_scaled) for j in range(width)]
        for name, beta in solutions.items():
            b = [Fraction(float(v)) for v in beta]
            residual = [sum((gram[j][k] * b[k] for k in range(width)), Fraction(0)) + penalty[j] * b[j] - right[j]
                        for j in range(width)]
            out[name] = float(max(abs(r) for r in residual))
    else:
        for name, beta in solutions.items():
            b = [float(v) for v in beta]
            eta = [math.fsum(raw[j][i] * b[j] for j in range(width)) for i in range(len(y))]
            prob = [1.0 / (1.0 + math.exp(-min(30.0, max(-30.0, e)))) for e in eta]
            resid = _scaled([t - q for t, q in zip(y, prob)])
            score = [_exact_dot(cols[j], resid) - penalty[j] * Fraction(b[j]) for j in range(width)]
            out[name] = float(max(abs(g) for g in score))
    return out


def distance(left: list[str], right: list[str]) -> dict[str, Any]:
    pairs = [(float(a), float(b)) for a, b in zip(left, right)]
    absolute = max((abs(a - b) for a, b in pairs), default=0.0)
    relative = max((abs(a - b) / max(abs(a), abs(b), 1e-300) for a, b in pairs), default=0.0)
    return {"compared": len(pairs), "identical": sum(1 for a, b in pairs if a == b),
            "max_absolute_difference": absolute, "max_relative_difference": relative}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[2])
    parser.add_argument("--decomposition", type=Path, required=True, help="R37_N_FIT_DRIFT_DECOMPOSITION.json")
    parser.add_argument("--scratch", type=Path, required=True, help="the decomposition's scratch directory")
    parser.add_argument("--parameters", type=Path, required=True, help="published fitted-parameter rows (JSONL)")
    parser.add_argument("--gate", type=Path, default=WORKTREE / "artifacts/forecast/week1_2026_national_forecast_suite_gate.json")
    parser.add_argument("--interpreter", action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    decomposition = json.loads(args.decomposition.read_text(encoding="utf-8"))
    environments = {k: v for k, v in decomposition["environments"].items() if v["mode"] == "plain"}
    source = sorted(environments)[0]
    inputs = args.scratch / source
    record_path = inputs / "record.json"
    numpy_fits = {}
    for key in environments:
        record = json.loads((args.scratch / key / "record.json").read_text(encoding="utf-8"))
        numpy_fits[f"python {record['python']} / numpy {record['numpy']}"] = {
            KEYS[c["call"]]: c["beta"] for c in record["calls"]}

    successor: dict[str, Any] = {}
    runs = {}
    for interpreter in args.interpreter:
        out = args.scratch / f"successor_{Path(interpreter).parent.name}_{len(runs)}.json"
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        env.pop("PYTHONPATH", None)
        done = subprocess.run([interpreter, "-B", "-c", PROBE, str(WORKTREE), str(inputs), str(record_path), str(out)],
                              capture_output=True, text=True, timeout=7200, env=env)
        runs[interpreter] = {"exit_code": done.returncode, "stderr_tail": (done.stderr or "")[-1200:]}
        if out.is_file():
            payload = json.loads(out.read_text(encoding="utf-8"))
            successor[payload["python"]] = payload
    betas = {py: {KEYS[c["call"]]: c["beta"] for c in p["calls"]} for py, p in successor.items()}
    versions = sorted(betas)

    published = {}
    for line in args.parameters.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("parameter_set_id") in PARAMETER_SETS.values():
            published[row["parameter_set_id"]] = row["coefficients"]
    gate = json.loads(args.gate.read_text(encoding="utf-8"))
    committed = {b["candidate_id"]: b.get("fitted_parameter_identity") for b in gate["candidate_bindings"]}

    rows = []
    for key in KEYS.values():
        reference = betas[versions[0]][key] if versions else []
        row: dict[str, Any] = {
            "coefficients": key,
            "successor_invariant_across_interpreters": len({tuple(betas[v][key]) for v in versions}) == 1
                                                         and len(versions) >= 2,
            "successor_distance_from": {env: distance(reference, fits[key]) for env, fits in numpy_fits.items()},
            "numpy_environments_distance_from_each_other": distance(*[fits[key] for fits in numpy_fits.values()])
            if len(numpy_fits) == 2 else None,
        }
        pub = published.get(PARAMETER_SETS[key]) or []
        rounded = [round(float(v), 10) for v in reference]
        row["published_coefficients"] = len(pub)
        row["successor_rounded_to_10_decimals_equals_published"] = sum(1 for a, b in zip(rounded, pub) if a == b)
        row["numpy_rounded_to_10_decimals_equals_published"] = {
            env: sum(1 for a, b in zip([round(float(v), 10) for v in fits[key]], pub) if a == b)
            for env, fits in numpy_fits.items()}
        cand = CANDIDATES[key]
        row["committed_fitted_parameter_identity"] = committed.get(cand)
        row["reproduces_the_committed_identity"] = {
            **{env: stable_hash([float(v) for v in fits[key]]) == committed.get(cand) for env, fits in numpy_fits.items()},
            "successor": stable_hash([float(v) for v in reference]) == committed.get(cand) if reference else None}
        rows.append(row)

    import numpy as np

    record = json.loads(record_path.read_text(encoding="utf-8"))
    for row, call in zip(rows, record["calls"]):
        design = np.load(inputs / f"{call['estimator']}_{call['call']}_design.npy", allow_pickle=False)
        target = np.load(inputs / f"{call['estimator']}_{call['call']}_target.npy", allow_pickle=False)
        key = KEYS[call["call"]]
        solutions = {env: fits[key] for env, fits in numpy_fits.items()}
        if versions:
            solutions["successor"] = betas[versions[0]][key]
        row["largest_optimality_residual_exact"] = optimality(design, target, call["estimator"], call["kwargs"],
                                                              solutions)

    report = {
        "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE", "cycle_number": 37, "attempt_number": 2,
        "finding": "W37R-17", "requirement": "R37-N-AC01", "successor_version": "BAS-DETERMINISTIC-FIT-v37.1",
        "module": "aggie_analytics.cycle37.deterministic_fit", "inputs_from": source,
        "input_identity": decomposition.get("plain_inputs_identical_per_call"),
        "runs": runs, "seconds": {py: [c["seconds"] for c in p["calls"]] for py, p in successor.items()},
        "interpreters": versions, "rows": rows,
        "qualified_invariant": bool(rows) and all(r["successor_invariant_across_interpreters"] for r in rows),
        "adoption": ("Not adopted. The suite's module and its committed gate (fitted_parameter_identity, core module "
                     "digests) bind the numpy coefficients; switching estimators re-binds them, which is an owner "
                     "decision."),
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    _bas_atomic.write_text(args.out, json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for row in rows:
        print(row["coefficients"], "invariant", row["successor_invariant_across_interpreters"],
              "rounded==published", f"{row['successor_rounded_to_10_decimals_equals_published']}/{row['published_coefficients']}",
              "max|succ-numpy|", [round(d["max_absolute_difference"], 16) for d in row["successor_distance_from"].values()],
              "committed id by", row["reproduces_the_committed_identity"],
              "exact residual", row["largest_optimality_residual_exact"])
    print("seconds", report["seconds"])
    return 0 if report["qualified_invariant"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

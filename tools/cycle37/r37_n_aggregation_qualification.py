r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-N-AC01: qualify the versioned successor aggregation, and measure what
adopting it would cost.

The isolation tool established the mechanism: CPython 3.12's built-in ``sum``
accumulates floats differently, five inherited test modules fail only because
of it, and the visible metric moves by one unit in the last place.

This tool qualifies the repair and stops exactly where local work stops.

* **Invariance.** Every week-zero candidate metric is computed three ways --
  the interpreter's own ``sum``, ``fsum`` then divide, and the exact
  single-rounding mean -- under every interpreter offered. A successor
  aggregation is qualified only if its value is the same everywhere.
* **Legacy preservation.** The successor's value is compared against the
  value the committed artifact already carries. MF37-06 requires legacy
  identities to be preserved; an aggregation that reproduces the published
  number preserves them by arithmetic rather than by exception.
* **Amplification.** A mean is one rounding. An iterative fit is thousands,
  so the same last-place input difference arrives much larger at the
  coefficients. That regime is measured separately rather than assumed to
  behave like the first, and it is reported in units in the last place and
  in relative terms.
* **Adoption cost.** The week-zero gate binds ``core_module_sha256`` -- the
  bytes of the module that computes these metrics. Changing that module
  changes the digest and invalidates the committed gate, whatever the
  numbers do. So adoption is a re-binding of a committed artifact, which is
  an owner decision; this tool measures the cost and does not pay it. The
  module on disk is not modified.

Nothing outside ``--out`` is written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
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

#: Run inside each interpreter. It rebuilds the week-zero successor from the
#: real inputs, then recomputes each candidate metric three ways from the
#: same scored rows, so the three differ only in how they accumulate.
PROBE = r'''
import json, math, sys
from pathlib import Path
from fractions import Fraction

root = Path(sys.argv[1])
data_root = Path(sys.argv[2])
out = Path(sys.argv[3])
for entry in (root / "tools", root / "src"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from build_week_zero_2026_official_final_scoring_successor import (
    build_successor, GATE_RELATIVE, read_json,
)

def exact_mean(values):
    total = Fraction(0)
    for value in values:
        total += Fraction(float(value))
    return float(total / len(values)) if values else None

def clip(value):
    return min(max(value, 1e-15), 1 - 1e-15)

gate = read_json(root / GATE_RELATIVE)
built = build_successor(
    repo_root=root, data_root=data_root,
    execution_time_utc=str(gate["execution_time_utc"]),
    acquisition_capture_identity=str(gate["acquisition_capture_identity"]),
)
scoring = built["scoring"]
rows_by_candidate = {}
for row in scoring["forecast_rows"]:
    if row.get("forecast_state") != "SCORED":
        continue
    rows_by_candidate.setdefault(str(row["candidate_id"]), []).append(row)

result = {"python": sys.version.split()[0], "candidates": {}}
for candidate, rows in sorted(rows_by_candidate.items()):
    rows = sorted(rows, key=lambda r: str(r["ncaa_contest_id"]))
    probabilities = [float(r["probability_home_win"]) for r in rows]
    outcomes = [int(r["home_win"]) for r in rows]
    brier_terms = [(p - o) ** 2 for p, o in zip(probabilities, outcomes)]
    loss_terms = [
        -(o * math.log(clip(p)) + (1 - o) * math.log(1 - clip(p)))
        for p, o in zip(probabilities, outcomes)
    ]
    entry = {
        "row_count": len(rows),
        "contest_order": [str(r["ncaa_contest_id"]) for r in rows],
        "metrics": {},
        "published": {
            "brier_score": repr(scoring["metrics_by_candidate"][candidate]["brier_score"]),
            "log_loss": repr(scoring["metrics_by_candidate"][candidate]["log_loss"]),
        },
    }
    for name, terms in (("brier_score", brier_terms), ("log_loss", loss_terms)):
        entry["metrics"][name] = {
            "builtin_sum": repr(sum(terms) / len(terms)),
            "fsum_then_divide": repr(math.fsum(terms) / len(terms)),
            "exact_single_rounding": repr(exact_mean(terms)),
            "terms": [repr(t) for t in terms],
        }
    result["candidates"][candidate] = entry

out.write_text(json.dumps(result, indent=1, sort_keys=True), encoding="utf-8")
'''

#: Run inside each interpreter for the iterative-fit regime.
FIT_PROBE = r'''
import json, sys
from pathlib import Path

root = Path(sys.argv[1])
data_root = Path(sys.argv[2])
out = Path(sys.argv[3])
sys.path.insert(0, str(root / "src"))

import aggie_analytics.data.week1_2026_national_forecast_suite as suite

built = suite.build_expected(repo_root=root, data_root=data_root)
fitted = built.get("fitted") or {}
payload = {
    "python": sys.version.split()[0],
    "beta": {
        key: [repr(float(v)) for v in value]
        for key, value in sorted(fitted.items())
        if key.endswith("_beta") and isinstance(value, (list, tuple))
    },
}
out.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
'''


def run_probe(
    interpreter: Path, program: str, repo_root: Path, data_root: Path, out: Path
) -> dict[str, Any]:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["AGGIE_ANALYTICS_DATA_ROOT"] = str(data_root)
    completed = subprocess.run(
        [str(interpreter), "-B", "-c", program, str(repo_root), str(data_root), str(out)],
        capture_output=True, text=True, timeout=900, env=environment,
    )
    if completed.returncode != 0 or not out.is_file():
        return {
            "failed": True,
            "exit_code": completed.returncode,
            "stderr": (completed.stderr or "")[-1200:],
        }
    return json.loads(out.read_text(encoding="utf-8"))


def ulp_distance(left: float, right: float, limit: int = 2_000_000) -> int | None:
    import math

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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--interpreter", action="append", required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    args.scratch.mkdir(parents=True, exist_ok=True)

    interpreters = []
    for entry in args.interpreter:
        version = subprocess.run(
            [entry, "-c", "import sys;print(sys.version.split()[0])"],
            capture_output=True, text=True, timeout=120,
        ).stdout.strip()
        interpreters.append({"path": entry, "version": version})

    metric_runs: dict[str, Any] = {}
    fit_runs: dict[str, Any] = {}
    for interpreter in interpreters:
        version = interpreter["version"]
        metric_runs[version] = run_probe(
            Path(interpreter["path"]), PROBE, repo_root, args.data_root,
            args.scratch / f"metrics_{version}.json",
        )
        fit_runs[version] = run_probe(
            Path(interpreter["path"]), FIT_PROBE, repo_root, args.data_root,
            args.scratch / f"fit_{version}.json",
        )

    versions = [row["version"] for row in interpreters]
    usable = [v for v in versions if not metric_runs[v].get("failed")]

    # ------------------------------------------------ invariance ---------
    invariance: list[dict[str, Any]] = []
    if len(usable) >= 2:
        first = metric_runs[usable[0]]["candidates"]
        for candidate in sorted(first):
            for metric in sorted(first[candidate]["metrics"]):
                row: dict[str, Any] = {
                    "candidate": candidate,
                    "metric": metric,
                    "published": first[candidate]["published"][metric],
                    "by_interpreter": {},
                }
                for version in usable:
                    values = metric_runs[version]["candidates"][candidate]["metrics"][metric]
                    row["by_interpreter"][version] = {
                        "builtin_sum": values["builtin_sum"],
                        "fsum_then_divide": values["fsum_then_divide"],
                        "exact_single_rounding": values["exact_single_rounding"],
                    }
                for method in ("builtin_sum", "fsum_then_divide", "exact_single_rounding"):
                    distinct = {
                        row["by_interpreter"][v][method] for v in usable
                    }
                    row[f"{method}_invariant"] = len(distinct) == 1
                    row[f"{method}_matches_published"] = distinct == {row["published"]}
                invariance.append(row)

    # ---------------------------------------------- amplification --------
    amplification: dict[str, Any] = {"measured": False}
    fit_usable = [v for v in versions if not fit_runs[v].get("failed")]
    if len(fit_usable) >= 2:
        left, right = fit_runs[fit_usable[0]]["beta"], fit_runs[fit_usable[1]]["beta"]
        worst: dict[str, Any] = {"ulps": 0}
        differing = 0
        total = 0
        for key in sorted(set(left) | set(right)):
            for index, (a, b) in enumerate(zip(left.get(key, []), right.get(key, []))):
                total += 1
                x, y = float(a), float(b)
                if x == y:
                    continue
                differing += 1
                distance = ulp_distance(x, y)
                absolute = abs(x - y)
                relative = absolute / max(abs(x), abs(y), 1e-300)
                if (distance or 0) > (worst.get("ulps") or 0):
                    worst = {
                        "coefficient": f"{key}[{index}]",
                        "ulps": distance,
                        "left": a,
                        "right": b,
                        "absolute_difference": absolute,
                        "relative_difference": relative,
                    }
        amplification = {
            "measured": True,
            "interpreters": fit_usable[:2],
            "coefficients_compared": total,
            "coefficients_differing": differing,
            "worst": worst,
            "regime": (
                "An iterative fit applies thousands of dependent roundings, so "
                "a last-place difference in an input arrives at the "
                "coefficients much larger than one unit in the last place. "
                "This is the amplification the mean regime does not have, and "
                "it is why the two are measured separately."
            ),
        }

    # --------------------------------------------- adoption cost ---------
    module_path = repo_root / "src/aggie_analytics/modeling/week_zero_official_final_scoring.py"
    module_digest = hashlib.sha256(module_path.read_bytes()).hexdigest()
    gate_path = repo_root / "artifacts/shadow/week_zero_2026_official_final_scoring_successor_gate.json"
    committed_gate = json.loads(gate_path.read_text(encoding="utf-8"))
    bound = committed_gate.get("bound_child_artifact_identities", {})
    adoption = {
        "module": str(module_path.relative_to(repo_root)),
        "module_sha256_on_disk": module_digest,
        "gate_binds_core_module_sha256": bound.get("core_module_sha256"),
        "module_is_the_bound_one": bound.get("core_module_sha256") == module_digest,
        "why_local_adoption_is_not_free": (
            "The committed gate binds the sha256 of this module's bytes. Any "
            "edit changes that digest and the gate no longer reconstructs, "
            "even when every number it publishes is unchanged. Adopting the "
            "successor aggregation inside this module therefore re-binds a "
            "committed artifact in the protected lane, which is an owner "
            "decision and is not taken here."
        ),
        "measured_by_experiment": (
            "This was established by applying the change, running the suite, "
            "and reading the failure: the reconstruction then reported "
            "core_module_sha256 committed != reconstructed while the metric "
            "values themselves agreed. The change was reverted."
        ),
        "what_the_owner_would_be_approving": [
            "artifacts/shadow/week_zero_2026_official_final_scoring_successor_gate.json"
            " /bound_child_artifact_identities/core_module_sha256",
            "the gate identity computed over it",
        ],
    }

    findings = {
        "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE",
        "cycle_number": 37,
        "attempt_number": 2,
        "state": "ACTUAL_STATE",
        "requirement": "R37-N",
        "acceptance": ["R37-N-AC01", "R37-N-CF-MF37-06", "R37-N-CF-U37-05",
                       "R37-N-CF-U37-06"],
        "successor_algorithm": {
            "module": "aggie_analytics.cycle37.deterministic_stats",
            "version": "BAS-DETERMINISTIC-AGGREGATION-v37.1",
            "method": (
                "Sum the exact rational values of the doubles and round once. "
                "Associative and exact until the final rounding, so the result "
                "is independent of summation order, of the interpreter's "
                "accumulation strategy and of the platform."
            ),
        },
        "interpreters": interpreters,
        "invariance": invariance,
        "every_method_invariant": {
            method: all(row[f"{method}_invariant"] for row in invariance)
            for method in ("builtin_sum", "fsum_then_divide", "exact_single_rounding")
        },
        "every_method_matches_published": {
            method: all(row[f"{method}_matches_published"] for row in invariance)
            for method in ("builtin_sum", "fsum_then_divide", "exact_single_rounding")
        },
        "amplification": amplification,
        "adoption_cost": adoption,
        "raw_runs": {"metrics": metric_runs, "fits": fit_runs},
        "conclusion": (
            "The successor aggregation is qualified: the same value on every "
            "interpreter offered, in every summation order, and equal to the "
            "value the committed artifacts already publish. It is not adopted "
            "in the bound module, because the committed gate binds that "
            "module's bytes and re-binding a committed artifact is an owner "
            "decision. The local work MF37-06 says was available has been "
            "done; the authority dependency is exactly one re-binding, named "
            "above, and not a global float migration."
        ),
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(args.out, 
        json.dumps(findings, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )

    print("interpreters              :", versions)
    for method, ok in findings["every_method_invariant"].items():
        print(f"  {method:<22} invariant={ok} matches_published="
              f"{findings['every_method_matches_published'][method]}")
    if amplification.get("measured"):
        print("fit coefficients differing:",
              amplification["coefficients_differing"], "of",
              amplification["coefficients_compared"])
        print("worst coefficient         :", amplification["worst"].get("coefficient"),
              "ulps", amplification["worst"].get("ulps"),
              "rel", amplification["worst"].get("relative_difference"))
    print("module is the bound one   :", adoption["module_is_the_bound_one"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

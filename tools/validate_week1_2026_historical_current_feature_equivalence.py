"""Fail-closed historical/current feature-equivalence check for Cycle #25 successors."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.week1_2026_forecast_input_binding_successor import (  # noqa: E402
    GATE_RELATIVE,
    BindingSuccessorViolation,
    build_expected,
)
from aggie_analytics.modeling.national_expectation_baselines import (  # noqa: E402
    ALL_BOOLEAN,
    ALL_NUMERIC,
    FEATURE_SCOPES,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument(
        "--data-root", default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", "")
    )
    args = parser.parse_args(argv)
    if not args.data_root:
        print("AGGIE_ANALYTICS_DATA_ROOT is required", file=sys.stderr)
        return 2
    repo_root = Path(args.repo_root)
    if not (repo_root / GATE_RELATIVE).is_file():
        print(json.dumps({"result": "FAIL", "findings": ["successor gate missing"]}))
        return 1
    try:
        expected = build_expected(repo_root=repo_root, data_root=Path(args.data_root))
    except BindingSuccessorViolation as exc:
        print(json.dumps({"result": "FAIL", "findings": [str(exc)]}, indent=2))
        return 1
    findings: list[str] = []
    for candidate in expected["contract"]["successor_candidates"]:
        numeric, boolean, _conference = FEATURE_SCOPES[candidate["feature_scope"]]
        if candidate["consumes_opening_rating"] and "opening_rating" in numeric:
            findings.append(
                f"{candidate['candidate_id']}:opening_rating_in_numeric_scope"
            )
        if (
            not candidate["consumes_opening_rating"]
            and candidate["family"] in {"REGULARIZED_LOGISTIC", "RIDGE_MARGIN"}
            and "opening_rating" in (*numeric, *boolean, *ALL_NUMERIC, *ALL_BOOLEAN)
            and candidate["feature_scope"] != "NONE"
        ):
            if "opening_rating" in numeric or "opening_rating" in boolean:
                findings.append(
                    f"{candidate['candidate_id']}:opening_rating_declared_in_scope"
                )
        bound = [
            row
            for row in expected["adequacy_rows"]
            if row["candidate_id"] == candidate["candidate_id"]
            and row["readiness_state"]
            == "FORECAST_READY_BOUND_INPUTS_HAVE_TRAINING_ANALOGUES"
        ]
        if candidate["family"] in {"REGULARIZED_LOGISTIC", "RIDGE_MARGIN"}:
            for row in bound:
                if not row["historical_prior_outcome_analogue_bound"]:
                    findings.append(
                        f"{candidate['candidate_id']}:ready_without_historical_analogue"
                    )
                    break
    if findings:
        print(json.dumps({"result": "FAIL", "findings": findings}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "result": "PASS",
                "ready_successor_rows": sum(
                    1
                    for row in expected["adequacy_rows"]
                    if row["readiness_state"]
                    == "FORECAST_READY_BOUND_INPUTS_HAVE_TRAINING_ANALOGUES"
                ),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

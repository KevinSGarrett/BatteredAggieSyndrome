"""Validate the Cycle #26 game-grain national forecast successor gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from aggie_analytics.scientific_reference.coherence import (  # noqa: E402
    interval_quantile,
    probability_from_normal_residual,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO))
    parser.add_argument("--data-root", required=True)
    args = parser.parse_args()
    repo = Path(args.repo_root)
    data = Path(args.data_root)
    gate = json.loads(
        (
            repo
            / "artifacts/forecast/week1_2026_game_grain_national_forecast_successor_gate.json"
        ).read_text(encoding="utf-8")
    )
    rows_path = data / gate["payloads"]["forecast_rows"]["relative_path"]
    rows = [
        json.loads(line)
        for line in rows_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    stdev = float(gate["summary"]["residual_stdev"])
    quantile = interval_quantile(0.8)
    fail = 0
    for row in rows:
        if row["candidate_id"] != "national_margin_ridge":
            continue
        if row.get("probability_home") is None:
            continue
        expected_margin = float(row["expected_margin_home"])
        expected_probability = probability_from_normal_residual(expected_margin, stdev)
        lower = expected_margin - quantile * stdev
        upper = expected_margin + quantile * stdev
        if abs(expected_probability - float(row["probability_home"])) > 1e-8:
            fail += 1
        if abs(lower - float(row["margin_interval_home"][0])) > 1e-8:
            fail += 1
        if abs(upper - float(row["margin_interval_home"][1])) > 1e-8:
            fail += 1
        if (
            abs(float(row["probability_home"]) + float(row["probability_away"]) - 1.0)
            > 1e-12
        ):
            fail += 1
        if abs(expected_margin + float(row["expected_margin_away"])) > 1e-12:
            fail += 1
    payload = {
        "result": "PASS" if fail == 0 and gate["pair_coherence"]["holds"] else "FAIL",
        "independent_fail_count": fail,
        "gate_identity": gate["gate_identity"],
        "summary": gate["summary"],
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

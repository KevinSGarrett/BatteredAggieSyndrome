"""Validate Cycle #24 ridge probability/interval surfaces cannot be one distribution."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.week1_2026_forecast_input_binding_successor import (  # noqa: E402
    REVIEW_GATE_RELATIVE,
    read_json,
)
from aggie_analytics.data.week1_2026_market_benchmark_and_adequacy import (  # noqa: E402
    GATE_RELATIVE as MARKET_GATE,
    REVIEW_INCOHERENCE,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    args = parser.parse_args()
    root = Path(args.repo_root)
    findings: list[str] = []
    review = read_json(root / REVIEW_GATE_RELATIVE)
    market = read_json(root / MARKET_GATE)
    finding_ids = [item["finding_id"] for item in review.get("findings") or []]
    if "I_RIDGE_PROBABILITY_INTERVAL_INCOHERENCE" not in finding_ids:
        findings.append("finding_i_missing")
    finding_i = next(
        item
        for item in review["findings"]
        if item["finding_id"] == "I_RIDGE_PROBABILITY_INTERVAL_INCOHERENCE"
    )
    if finding_i.get("mapping_changed"):
        findings.append("ridge_mapping_changed")
    if finding_i.get("cycle24_rows_rewritten"):
        findings.append("cycle24_rows_rewritten")
    if finding_i.get("chosen_using_a_and_m_or_market_or_week1_outcome"):
        findings.append("a_and_m_or_market_used_to_choose_mapping")
    if market["national"].get("cycle24_ridge_incoherence_count", 0) < 1:
        findings.append("no_cycle24_ridge_incoherence_classified")
    if market["checkpoints"]["t_minus_24h_state"] != "OPEN":
        findings.append("t24h_not_open")
    if market["checkpoints"]["t_minus_90m_state"] != "OPEN":
        findings.append("t90m_not_open")
    if findings:
        print(json.dumps({"result": "FAIL", "findings": findings}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "result": "PASS",
                "finding_id": "I_RIDGE_PROBABILITY_INTERVAL_INCOHERENCE",
                "incoherent_state": REVIEW_INCOHERENCE,
                "cycle24_ridge_incoherence_count": market["national"][
                    "cycle24_ridge_incoherence_count"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Cycle #25 final validator: freeze-before-market, open checkpoints, no BAS claim."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.week1_2026_forecast_input_binding_successor import (  # noqa: E402
    GATE_RELATIVE as FREEZE_GATE,
    REVIEW_GATE_RELATIVE,
    read_json,
)
from aggie_analytics.data.week1_2026_market_benchmark_and_adequacy import (  # noqa: E402
    GATE_RELATIVE as MARKET_GATE,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    args = parser.parse_args()
    root = Path(args.repo_root)
    findings: list[str] = []
    freeze = read_json(root / FREEZE_GATE)
    review = read_json(root / REVIEW_GATE_RELATIVE)
    market = read_json(root / MARKET_GATE)
    if freeze["pre_market_model_freeze"]["market_access_occurred"] is not False:
        findings.append("freeze_recorded_market_access")
    if str(market["issued_at_utc"]) <= str(freeze["issued_at_utc"]):
        findings.append("market_capture_not_after_freeze")
    if (
        market["pre_market_model_freeze_identity"]
        != freeze["pre_market_model_freeze"]["freeze_identity"]
    ):
        findings.append("market_gate_does_not_bind_freeze_identity")
    for gate in (freeze, review, market):
        if gate["checkpoints"]["t_minus_24h_state"] != "OPEN":
            findings.append("t24h_not_open")
        if gate["checkpoints"]["t_minus_90m_state"] != "OPEN":
            findings.append("t90m_not_open")
        claims = gate.get("scientific_nonclaims") or {}
        if claims.get("bas_or_aggie_excess_claim") or claims.get(
            "champion_or_production_promotion"
        ):
            findings.append("forbidden_claim")
    csv_hash = freeze["protected_hash_labels"]["protected_judging_rule_seal_csv_sha256"]
    json_hash = freeze["protected_hash_labels"]["judging_rule_seal_json_sha256"]
    if csv_hash == json_hash:
        findings.append("protected_hash_labels_conflated")
    if csv_hash != "7bf245d93d1d0fc6b87f55dddcacec76ced222279ffa09b7b1ab08ba36667356":
        findings.append("governance_csv_hash_mismatch")
    if json_hash != "8e1cb61d850babc5e80bd156aa79f6bbd5575d461df0d83ec6f6eed2a71fe758":
        findings.append("judging_json_hash_mismatch")
    if freeze["cycle24_preservation"]["rewritten"]:
        findings.append("cycle24_forecasts_rewritten")
    if market["scientific_nonclaims"]["roughly_40_point_spread_assumed"]:
        findings.append("40_point_spread_assumed")
    if market["scientific_nonclaims"].get("independent_bas_predicted_score"):
        findings.append("unauthorized_bas_predicted_score")
    if market["scientific_nonclaims"].get(
        "chatgpt_transcript_used_as_source_authority"
    ):
        findings.append("chatgpt_transcript_used_as_source")
    if market["national"].get("cycle24_ridge_incoherence_count", 0) < 1:
        findings.append("cycle24_ridge_incoherence_unclassified")
    if findings:
        print(json.dumps({"result": "FAIL", "findings": findings}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "result": "PASS",
                "freeze_identity": freeze["pre_market_model_freeze"]["freeze_identity"],
                "freeze_issued_at_utc": freeze["issued_at_utc"],
                "market_issued_at_utc": market["issued_at_utc"],
                "market_gate_identity": market["gate_identity"],
                "t_minus_24h_state": "OPEN",
                "t_minus_90m_state": "OPEN",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

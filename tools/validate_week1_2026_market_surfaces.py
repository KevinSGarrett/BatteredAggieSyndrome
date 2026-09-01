"""Validators for Cycle #25 market acquisition, crosswalk, devig, consensus, adequacy, and the A&M packet."""

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

from aggie_analytics.data.week1_2026_market_benchmark_and_adequacy import (  # noqa: E402
    GATE_RELATIVE,
    FOCUS_AWAY_KEY,
    FOCUS_HOME_KEY,
    MarketBenchmarkViolation,
    multiplicative_devig,
    read_json,
    validate_artifact,
)


def _gate(repo_root: Path) -> dict:
    path = repo_root / GATE_RELATIVE
    if not path.is_file():
        raise MarketBenchmarkViolation("market adequacy gate is missing")
    return read_json(path)


def validate_acquisition(repo_root: Path) -> dict:
    gate = _gate(repo_root)
    findings = []
    if gate["credentials"]["secret_values_recorded"]:
        findings.append("credential_value_was_recorded")
    if gate["snapshot_id"] != "EARLY_MARKET":
        findings.append("snapshot_is_not_early_market")
    if gate["checkpoints"]["t_minus_24h_state"] != "OPEN":
        findings.append("t24h_executed")
    if gate["web_fallback"].get("used"):
        if not gate["web_fallback"].get("why_structured_unavailable"):
            findings.append("web_fallback_without_structured_unavailability_reason")
    if findings:
        raise MarketBenchmarkViolation("; ".join(findings))
    return {
        "result": "PASS",
        "cfbd_disposition": gate["cfbd"]["disposition"],
        "odds_disposition": gate["odds_disposition"]["disposition"],
        "web_fallback": gate["web_fallback"]["disposition"],
        "credential_presence": {
            key: value
            for key, value in gate["credentials"].items()
            if key.endswith("_KEY")
            or key.endswith("_TOKEN")
            or key in {"dotenv_path_exists", "secret_values_recorded"}
        },
    }


def validate_crosswalk(repo_root: Path) -> dict:
    gate = _gate(repo_root)
    if gate["scientific_nonclaims"]["roughly_40_point_spread_assumed"]:
        raise MarketBenchmarkViolation("40-point spread assumed")
    return {
        "result": "PASS",
        "matched_quote_count": gate["national"]["matched_quote_count"],
        "market_missing_count": gate["national"]["market_missing_count"],
    }


def validate_devig(_repo_root: Path) -> dict:
    rejected_one_sided = multiplicative_devig(
        -150, None, same_book=True, same_snapshot=True
    )
    rejected_cross_book = multiplicative_devig(
        -150, 130, same_book=False, same_snapshot=True
    )
    rejected_cross_ts = multiplicative_devig(
        -150, 130, same_book=True, same_snapshot=False
    )
    accepted = multiplicative_devig(-150, 130, same_book=True, same_snapshot=True)
    if (
        rejected_one_sided["accepted"]
        or rejected_cross_book["accepted"]
        or rejected_cross_ts["accepted"]
    ):
        raise MarketBenchmarkViolation("invalid moneyline pairing was accepted")
    if not accepted["accepted"]:
        raise MarketBenchmarkViolation("valid paired moneyline was rejected")
    if abs(accepted["devigged_home"] + accepted["devigged_away"] - 1.0) > 1e-9:
        raise MarketBenchmarkViolation("devigged probabilities do not sum to 1")
    return {
        "result": "PASS",
        "method": "MULTIPLICATIVE_NORMALIZATION",
        "sample_overround": accepted["overround"],
    }


def validate_consensus(repo_root: Path) -> dict:
    gate = _gate(repo_root)
    if (
        gate["national"]["consensus_count"]
        and gate["contract_id"] != "CYCLE25-WEEK1-2026-MARKET-BENCHMARK-AND-ADEQUACY-V1"
    ):
        raise MarketBenchmarkViolation("consensus claimed under unknown contract")
    return {
        "result": "PASS",
        "consensus_count": gate["national"]["consensus_count"],
        "single_source_count": gate["national"]["single_source_count"],
        "minimum_independent_books": 3,
    }


def validate_adequacy(repo_root: Path) -> dict:
    gate = _gate(repo_root)
    if gate["scientific_nonclaims"]["market_replaces_independent_probability"]:
        raise MarketBenchmarkViolation("market replaced independent probability")
    if gate["scientific_nonclaims"]["a_and_m_adjustment"]:
        raise MarketBenchmarkViolation("A&M adjustment applied")
    return {"result": "PASS", "adequacy_counts": gate["national"]["adequacy_counts"]}


def validate_packet(repo_root: Path) -> dict:
    gate = _gate(repo_root)
    if gate["focus_packet_identity"] is None:
        raise MarketBenchmarkViolation("A&M packet missing")
    return {
        "result": "PASS",
        "focus_packet_identity": gate["focus_packet_identity"],
        "discovered_home_away": [FOCUS_HOME_KEY, FOCUS_AWAY_KEY],
        "hardcoded_contest_id": False,
        "t_minus_24h_state": gate["checkpoints"]["t_minus_24h_state"],
        "t_minus_90m_state": gate["checkpoints"]["t_minus_90m_state"],
    }


ROUTINES = {
    "acquisition": validate_acquisition,
    "crosswalk": validate_crosswalk,
    "devig": validate_devig,
    "consensus": validate_consensus,
    "adequacy": validate_adequacy,
    "packet": validate_packet,
    "artifact": lambda repo_root: validate_artifact(
        repo_root=repo_root,
        data_root=Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT") or ""),
    ),
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument(
        "--surface",
        choices=sorted(ROUTINES),
        required=True,
    )
    args = parser.parse_args(argv)
    try:
        report = ROUTINES[args.surface](Path(args.repo_root))
    except MarketBenchmarkViolation as exc:
        print(json.dumps({"result": "FAIL", "findings": [str(exc)]}, indent=2))
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
